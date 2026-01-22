"""
Skill Plan services for prerequisite resolution and import/export.

Based on the Imperium skill-checker reference implementation.
"""

import logging
from typing import List, Dict, Set, Optional, Any
from django.utils import timezone
from xml.etree import ElementTree as ET
from xml.dom import minidom

from core.character.models import SkillPlan, SkillPlanEntry, CharacterSkill
from core.eve.models import ItemType

logger = logging.getLogger('evewire')


class SkillPlanExporter:
    """Export skill plans to EVE XML format (compatible with in-game skill planner)."""

    @staticmethod
    def export_to_xml(skill_plan: SkillPlan, character=None, include_prereqs=True,
                      include_known=False) -> str:
        """
        Export a skill plan to EVE XML format.

        Args:
            skill_plan: The skill plan to export
            character: Optional character to check current skills
            include_prereqs: If True, include all prerequisite skills
            include_known: If True, include skills the character already knows

        Returns:
            XML string compatible with EVE in-game skill planner
        """
        # Get all entries from this plan and parent plans
        entries = list(skill_plan.entries.all())
        parent = skill_plan.parent
        while parent:
            entries.extend(list(parent.entries.all()))
            parent = parent.parent

        # Build skill list with prerequisites
        plan_skills = {}  # skill_id -> (level, skill_name, prereqs)

        for entry in entries:
            if not entry.level:
                continue  # Skip recommended-only entries for export

            skill_id = entry.skill_id
            level = entry.level

            # Skip if character already has this level
            if character and not include_known:
                try:
                    char_skill = CharacterSkill.objects.get(
                        character=character,
                        skill_id=skill_id
                    )
                    if char_skill.skill_level >= level:
                        continue
                except CharacterSkill.DoesNotExist:
                    pass

            # Get skill info
            try:
                item_type = ItemType.objects.get(id=skill_id)
                skill_name = item_type.name
                prereqs = SkillPlanExporter._get_prerequisites(skill_id)
            except ItemType.DoesNotExist:
                skill_name = f"Skill {skill_id}"
                prereqs = []

            # Add to plan
            if skill_id in plan_skills:
                # Keep the highest level
                if level > plan_skills[skill_id][0]:
                    plan_skills[skill_id] = (level, skill_name, prereqs)
            else:
                plan_skills[skill_id] = (level, skill_name, prereqs)

            # Add prerequisites if requested
            if include_prereqs:
                SkillPlanExporter._add_prereqs_recursive(
                    plan_skills, prereqs, level, character, include_known
                )

        # Build XML
        root = ET.Element('plan')
        root.set('xmlns:xsd', 'http://www.w3.org/2001/XMLSchema')
        root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        root.set('name', skill_plan.name)
        root.set('owner', 'evewire')

        sorting = ET.SubElement(root, 'sorting')
        sorting.set('criteria', 'None')
        sorting.set('order', 'None')
        sorting.set('groupByPriority', 'false')

        for skill_id, (level, skill_name, _) in sorted(plan_skills.items()):
            entry_elem = ET.SubElement(root, 'entry')
            entry_elem.set('skillID', str(skill_id))
            entry_elem.set('skill', skill_name)
            entry_elem.set('level', str(level))
            entry_elem.set('priority', '3')
            entry_elem.set('type', 'Planned')

            notes = ET.SubElement(entry_elem, 'notes')
            notes.text = skill_name

        # Pretty print XML
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="\t")

    @staticmethod
    def _get_prerequisites(skill_id: int) -> List[Dict[str, int]]:
        """
        Get prerequisites for a skill from SDE data.

        Returns list of (skill_required, skill_level) tuples.

        Skill prerequisite attributes:
        - 182, 183, 184, 1285, 1289, 1290 - skill type IDs
        - 277, 278, 279, 1286, 1287 - corresponding skill levels
        """
        from core.eve.models import TypeAttribute

        # Map of skill attribute IDs to their corresponding level attribute IDs
        # attributeID -> levelAttributeID
        skill_attribute_map = {
            182: 277,  # primary skill required -> primary skill level
            183: 278,  # secondary skill required -> secondary skill level
            184: 279,  # etc.
            1285: 1286,
            1289: 1287,
            1290: 1289,  # Note: this appears to be an error in SDE, should be 1288
        }

        prerequisites = []

        # Get all skill prerequisite attributes for this skill
        skill_attrs = TypeAttribute.objects.filter(
            type_id=skill_id,
            attribute_id__in=skill_attribute_map.keys()
        ).select_related('attribute_id')

        for skill_attr in skill_attrs:
            attr_id = skill_attr.attribute_id
            skill_type_id = int(skill_attr.value_float) if skill_attr.value_float else None

            if not skill_type_id:
                continue

            # Get the required level from the corresponding level attribute
            level_attr_id = skill_attribute_map.get(attr_id)
            if not level_attr_id:
                continue

            try:
                level_obj = TypeAttribute.objects.get(
                    type_id=skill_id,
                    attribute_id=level_attr_id
                )
                required_level = int(level_obj.value_float) if level_obj.value_float else 0
            except TypeAttribute.DoesNotExist:
                required_level = 1  # Default to level 1 if not specified

            prerequisites.append({
                'skill_required': skill_type_id,
                'skill_level': required_level,
            })

        return prerequisites

    @staticmethod
    def _add_prereqs_recursive(plan_skills: Dict, prereqs: List, target_level: int,
                               character=None, include_known=False,
                               visited: Optional[Set] = None) -> None:
        """Recursively add prerequisites to the plan."""
        if visited is None:
            visited = set()

        for prereq in prereqs:
            skill_id = prereq['skill_required']
            required_level = prereq['skill_level']

            if skill_id in visited:
                continue
            visited.add(skill_id)

            # Skip if character already has this
            if character and not include_known:
                try:
                    char_skill = CharacterSkill.objects.get(
                        character=character,
                        skill_id=skill_id
                    )
                    if char_skill.skill_level >= required_level:
                        continue
                except CharacterSkill.DoesNotExist:
                    pass

            # Get skill info
            try:
                item_type = ItemType.objects.get(id=skill_id)
                skill_name = item_type.name
                skill_prereqs = SkillPlanExporter._get_prerequisites(skill_id)
            except ItemType.DoesNotExist:
                skill_name = f"Skill {skill_id}"
                skill_prereqs = []

            # Add if not present or higher level
            if skill_id not in plan_skills or required_level > plan_skills[skill_id][0]:
                plan_skills[skill_id] = (required_level, skill_name, skill_prereqs)

            # Recurse
            SkillPlanExporter._add_prereqs_recursive(
                plan_skills, skill_prereqs, required_level, character, include_known, visited
            )


class SkillPlanImporter:
    """Import skill plans from EVE XML format."""

    @staticmethod
    def import_from_xml(xml_content: str, owner, name: Optional[str] = None,
                        description: Optional[str] = None) -> SkillPlan:
        """
        Import a skill plan from EVE XML format.

        Args:
            xml_content: XML string from EVE skill planner
            owner: User who will own the imported plan
            name: Optional name (defaults to plan name from XML)
            description: Optional description

        Returns:
            The created SkillPlan
        """
        root = ET.fromstring(xml_content)

        # Get plan name from XML
        plan_name = name or root.get('name', 'Imported Plan')

        # Get display order
        max_order = SkillPlan.objects.filter(
            owner=owner,
            parent__isnull=True
        ).aggregate(max_order=models.Max('display_order'))['max_order'] or 0

        # Create the plan
        plan = SkillPlan.objects.create(
            name=plan_name,
            description=description or f"Imported from EVE XML on {timezone.now().date()}",
            owner=owner,
            display_order=max_order + 1,
        )

        # Parse entries
        for entry_elem in root.findall('entry'):
            skill_id = int(entry_elem.get('skillID'))
            level = int(entry_elem.get('level', 0))

            if level > 0:
                # Check if skill exists
                try:
                    ItemType.objects.get(id=skill_id)
                except ItemType.DoesNotExist:
                    logger.warning(f"Skill {skill_id} not found in SDE, skipping")
                    continue

                # Get display order for this plan
                max_entry_order = SkillPlanEntry.objects.filter(
                    skill_plan=plan
                ).aggregate(max_order=models.Max('display_order'))['max_order'] or 0

                # Create entry (avoid duplicates)
                SkillPlanEntry.objects.get_or_create(
                    skill_plan=plan,
                    skill_id=skill_id,
                    defaults={
                        'level': level,
                        'display_order': max_entry_order + 1,
                    }
                )

        return plan


def calculate_training_time(character, skill_id: int, target_level: int) -> Dict[str, Any]:
    """
    Calculate training time for a skill to reach target level.

    Uses EVE Online skill training formula:
    - SP per minute = primary_attribute + (secondary_attribute / 2)
    - SP needed for level L = 2^((2.5 * L) - 2) * 32 * rank

    Returns dict with:
    - total_seconds: estimated training time in seconds
    - sp_needed: SP needed for target level
    - sp_current: Current SP in skill (0 if not trained)
    - current_level: Current trained level
    - sp_per_minute: Skill points earned per minute
    """
    from core.character.models import CharacterAttributes
    from core.eve.models import ItemType
    import math

    # Get current skill status
    try:
        char_skill = CharacterSkill.objects.get(
            character=character,
            skill_id=skill_id
        )
        current_level = char_skill.skill_level
        current_sp = char_skill.skillpoints_in_skill
    except CharacterSkill.DoesNotExist:
        current_level = 0
        current_sp = 0

    # Get character attributes
    try:
        attrs = character.attributes
    except CharacterAttributes.DoesNotExist:
        # Default attributes if not synced
        attrs = None

    # Get skill rank from SDE (TypeAttribute table)
    skill_rank = _get_skill_rank(skill_id)

    # Get skill primary/secondary attributes from SDE
    primary_attr_name, secondary_attr_name = _get_skill_attributes(skill_id)

    # Calculate SP per minute
    if attrs:
        primary_value = getattr(attrs, primary_attr_name, 20)
        secondary_value = getattr(attrs, secondary_attr_name, 20)
        sp_per_minute = primary_value + (secondary_value / 2)
    else:
        sp_per_minute = 20 + (20 / 2)  # Default: both attributes at 20

    # Calculate SP needed for each level from current to target
    total_sp_needed = 0
    for level in range(current_level + 1, target_level + 1):
        level_sp = math.pow(2, (2.5 * level) - 2) * 32 * skill_rank
        total_sp_needed += level_sp

    # SP already earned towards current level
    sp_at_current_level_start = 0
    if current_level > 0:
        sp_at_current_level_start = math.pow(2, (2.5 * current_level) - 2) * 32 * skill_rank

    sp_remaining = max(0, total_sp_needed - (current_sp - sp_at_current_level_start))

    # Calculate time
    if sp_per_minute > 0:
        total_seconds = int((sp_remaining / sp_per_minute) * 60)
    else:
        total_seconds = 0

    return {
        'total_seconds': total_seconds,
        'sp_needed': int(total_sp_needed),
        'sp_remaining': int(sp_remaining),
        'sp_current': current_sp,
        'current_level': current_level,
        'sp_per_minute': round(sp_per_minute, 2),
        'skill_rank': skill_rank,
    }


def _get_skill_rank(skill_id: int) -> int:
    """
    Get the rank (multiplier) for a skill.

    Rank determines how many SP are needed to train the skill.
    Most skills have rank 1, but some have higher ranks.

    Looks up from SDE TypeAttribute table:
    - Attribute ID 275 = Training time multiplier (skill rank)
    """
    from core.eve.models import TypeAttribute

    try:
        rank_attr = TypeAttribute.objects.get(
            type_id=skill_id,
            attribute_id=275  # Training time multiplier
        )
        # Rank is stored as value_int
        if rank_attr.value_int is not None:
            return rank_attr.value_int
        # Fallback to value_float if value_int is None
        if rank_attr.value_float is not None:
            return int(rank_attr.value_float)
    except TypeAttribute.DoesNotExist:
        pass

    # Default to rank 1 if not found
    return 1


def _get_skill_attributes(skill_id: int) -> tuple[str, str]:
    """
    Get the primary and secondary attributes for a skill.

    Returns tuple of (primary_attribute_name, secondary_attribute_name).

    Looks up from SDE TypeAttribute table:
    - Attribute ID 180 = Primary attribute
    - Attribute ID 181 = Secondary attribute

    EVE attribute ID mapping:
    - 164 = intelligence
    - 165 = perception
    - 166 = willpower
    - 167 = charisma
    - 168 = memory
    """
    from core.eve.models import TypeAttribute

    # Map EVE attribute IDs to character attribute field names
    ATTRIBUTE_MAP = {
        164: 'intelligence',
        165: 'perception',
        166: 'willpower',
        167: 'charisma',
        168: 'memory',
    }

    # Get primary attribute
    primary_attr = 'intelligence'  # default
    try:
        primary_attr_obj = TypeAttribute.objects.get(
            type_id=skill_id,
            attribute_id=180  # Primary attribute
        )
        primary_attr_id = int(primary_attr_obj.value_int) if primary_attr_obj.value_int else None
        if primary_attr_id and primary_attr_id in ATTRIBUTE_MAP:
            primary_attr = ATTRIBUTE_MAP[primary_attr_id]
    except TypeAttribute.DoesNotExist:
        pass

    # Get secondary attribute
    secondary_attr = 'memory'  # default
    try:
        secondary_attr_obj = TypeAttribute.objects.get(
            type_id=skill_id,
            attribute_id=181  # Secondary attribute
        )
        secondary_attr_id = int(secondary_attr_obj.value_int) if secondary_attr_obj.value_int else None
        if secondary_attr_id and secondary_attr_id in ATTRIBUTE_MAP:
            secondary_attr = ATTRIBUTE_MAP[secondary_attr_id]
    except TypeAttribute.DoesNotExist:
        pass

    return (primary_attr, secondary_attr)


# Import models for aggregate functions
from django.db import models
