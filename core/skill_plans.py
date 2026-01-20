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
        """
        # TODO: Implement from dgmTypeAttributes when SDE is imported
        # For now, return empty list
        return []

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

    Returns dict with:
    - total_seconds: estimated training time in seconds
    - sp_needed: SP needed for target level
    - sp_current: Current SP in skill (0 if not trained)
    """
    # TODO: Implement actual SP calculation based on character attributes
    # This requires the skill's rank and character's attributes
    # For now, return placeholder

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

    # SP needed formula (simplified - needs rank from SDE)
    # SP to train level L = 2^((2.5 * L) - 2) * 250 * rank
    # For now, return placeholder
    return {
        'total_seconds': 0,
        'sp_needed': 0,
        'sp_current': current_sp,
        'current_level': current_level,
    }


# Import models for aggregate functions
from django.db import models
