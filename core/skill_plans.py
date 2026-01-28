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

            # Skip auto-added prerequisite entries - EVE client handles these via include_prereqs
            if entry.is_prerequisite:
                continue

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
        )

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
                        'is_prerequisite': False,  # Imported skills are primary entries
                    }
                )

        # Auto-add all prerequisites for the imported skills
        plan.ensure_prerequisites()

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


def get_prerequisites_for_skill(skill_id: int, target_level: int) -> List[Dict]:
    """
    Get all prerequisites for a skill at a specific level.

    Returns a list of prerequisite dicts with skill info and whether
    they're already satisfied based on current character skills.

    Args:
        skill_id: The skill to check prerequisites for
        target_level: The level being trained to

    Returns:
        List of dicts with keys: skill_id, skill_name, required_level,
                                current_level, is_met, type (direct/recursive)
    """
    from core.character.models import CharacterSkill

    # Start with direct prerequisites
    direct_prereqs = SkillPlanExporter._get_prerequisites(skill_id)

    # Build full prerequisite tree
    all_prereqs = []
    visited = set()

    def add_prereq_recursive(prereq_skill_id: int, required_level: int, depth: int) -> None:
        """Recursively build prerequisite tree."""
        if prereq_skill_id in visited:
            return
        visited.add(prereq_skill_id)

        # Get skill info
        try:
            skill = ItemType.objects.get(id=prereq_skill_id)
            skill_name = skill.name
        except ItemType.DoesNotExist:
            skill_name = f"Skill {prereq_skill_id}"

        # Get current character level (will be 0 if not trained)
        # This is populated later by the view
        current_level = 0  # Placeholder

        prereq_info = {
            'skill_id': prereq_skill_id,
            'skill_name': skill_name,
            'required_level': required_level,
            'current_level': current_level,  # To be filled by caller
            'is_met': current_level >= required_level,  # To be updated by caller
            'type': 'direct' if depth == 0 else 'recursive',
            'depth': depth,
        }
        all_prereqs.append(prereq_info)

        # Get this skill's prerequisites recursively
        if depth < 5:  # Limit recursion depth
            sub_prereqs = SkillPlanExporter._get_prerequisites(prereq_skill_id)
            for sub_prereq in sub_prereqs:
                add_prereq_recursive(
                    sub_prereq['skill_required'],
                    sub_prereq['skill_level'],
                    depth + 1
                )

    for prereq in direct_prereqs:
        add_prereq_recursive(prereq['skill_required'], prereq['skill_level'], 0)

    return all_prereqs


def check_prerequisites_met(character, skill_id: int, target_level: int,
                            character_skills: Dict) -> Dict:
    """
    Check if all prerequisites are met for training a skill.

    Args:
        character: The character to check skills for
        skill_id: The skill to check
        target_level: The level being trained to
        character_skills: Dict of {skill_id: CharacterSkill} for the character

    Returns:
        Dict with keys:
            - all_met: bool - whether all prerequisites are met
            - unmet: list of prerequisite dicts that aren't met
            - total: int - total number of prerequisites
            - met_count: int - number of prerequisites that are met
    """
    prereqs = get_prerequisites_for_skill(skill_id, target_level)

    # Populate current levels from character skills
    for prereq in prereqs:
        char_skill = character_skills.get(prereq['skill_id'])
        prereq['current_level'] = char_skill.skill_level if char_skill else 0
        prereq['is_met'] = prereq['current_level'] >= prereq['required_level']

    unmet = [p for p in prereqs if not p['is_met']]
    all_met = len(unmet) == 0

    return {
        'all_met': all_met,
        'unmet': unmet,
        'total': len(prereqs),
        'met_count': len([p for p in prereqs if p['is_met']]),
        'all_prereqs': prereqs,
    }


def get_trainable_status(character, skill_id: int, target_level: int,
                         character_skills: Dict) -> str:
    """
    Determine if a skill is trainable now or blocked by prerequisites.

    Returns status string: 'trainable', 'blocked', or 'in_progress'

    Args:
        character: The character
        skill_id: The skill to check
        target_level: Target level
        character_skills: Dict of {skill_id: CharacterSkill}

    Returns:
        'trainable': Prerequisites met, can start training immediately
        'blocked': Prerequisites not met
        'in_progress': Already training or at target level
    """
    # Check current skill level
    char_skill = character_skills.get(skill_id)
    current_level = char_skill.skill_level if char_skill else 0

    if current_level >= target_level:
        return 'in_progress'

    # Check prerequisites
    prereq_check = check_prerequisites_met(character, skill_id, target_level, character_skills)

    if prereq_check['all_met']:
        return 'trainable'
    else:
        return 'blocked'


def extract_fitting_skills(fitting) -> Set[tuple[int, int]]:
    """
    Extract all required skills from a fitting.

    Collects skills required by:
    - The ship type itself
    - All fitted modules (high/med/low/rig/subsystem slots)

    Returns set of (skill_id, required_level) tuples.

    Args:
        fitting: Fitting object with slots attribute

    Returns:
        Set of (skill_id, level) tuples representing required skills
    """
    from core.eve.models import TypeAttribute

    required_skills = set()

    # Skill attribute map (same as in _get_prerequisites)
    skill_attribute_map = {
        182: 277,
        183: 278,
        184: 279,
        1285: 1286,
        1289: 1287,
        1290: 1289,
    }

    # Collect all item type IDs from the fitting
    item_type_ids = []

    # Add ship type
    if fitting.ship_type_id:
        item_type_ids.append(fitting.ship_type_id)

    # Add all modules from slots
    try:
        slots = fitting.get_slots()
        for slot_name in ['high_slots', 'med_slots', 'low_slots', 'rig_slots', 'subsystem_slots']:
            slot_items = slots.get(slot_name, [])
            if slot_items:
                item_type_ids.extend([mid for mid in slot_items if mid])
    except Exception:
        # If get_slots() fails, skip module processing
        pass

    # Get prerequisite skills for each item
    for item_type_id in item_type_ids:
        # Get all prerequisite attributes for this item
        skill_attrs = TypeAttribute.objects.filter(
            type_id=item_type_id,
            attribute_id__in=skill_attribute_map.keys()
        )

        for skill_attr in skill_attrs:
            prereq_skill_id = int(skill_attr.value_float) if skill_attr.value_float else None
            if not prereq_skill_id:
                continue

            # Get required level
            level_attr_id = skill_attribute_map.get(skill_attr.attribute_id)
            if not level_attr_id:
                continue

            try:
                level_obj = TypeAttribute.objects.get(
                    type_id=item_type_id,
                    attribute_id=level_attr_id
                )
                required_level = int(level_obj.value_float) if level_obj.value_float else 1
            except TypeAttribute.DoesNotExist:
                required_level = 1

            required_skills.add((prereq_skill_id, required_level))

    return required_skills


def expand_prerequisites(primary_skills: Set[tuple[int, int]]) -> Set[tuple[int, int]]:
    """
    Expand primary skills with all prerequisites and intermediate levels.

    Takes a set of (skill_id, level) primary skills and expands to include:
    - All intermediate levels (1 through N-1) for each skill
    - All prerequisite skills at their required levels
    - All intermediate levels for prerequisite skills
    - Recursive prerequisites

    This is the in-memory equivalent of SkillPlan.ensure_prerequisites().

    Args:
        primary_skills: Set of (skill_id, level) tuples

    Returns:
        Set of (skill_id, level) tuples including all prereqs and intermediate levels
    """
    from collections import deque

    # Use BFS to collect all prerequisites
    all_skills = set()
    queue = deque()

    # Start with primary skills, adding intermediate levels
    for skill_id, max_level in primary_skills:
        # Add all levels 1 through max_level
        for level in range(1, max_level + 1):
            all_skills.add((skill_id, level))
        # Enqueue for prerequisite discovery
        queue.append((skill_id, max_level))

    # BFS for prerequisites
    while queue:
        skill_id, target_level = queue.popleft()

        # Get prerequisites for this skill
        prereqs = SkillPlanExporter._get_prerequisites(skill_id)

        for prereq_dict in prereqs:
            prereq_skill_id = prereq_dict['skill_required']
            required_level = prereq_dict['skill_level']

            # Only include if prerequisite level <= our target level
            if required_level <= target_level:
                # Add all intermediate levels for this prerequisite
                for level in range(1, required_level + 1):
                    key = (prereq_skill_id, level)
                    if key not in all_skills:
                        all_skills.add(key)
                        # Recursively find this prerequisite's prerequisites
                        queue.append((prereq_skill_id, required_level))

    return all_skills


def order_skills_by_prerequisites(skills: Set[tuple[int, int]]) -> list[tuple[int, int]]:
    """
    Order skills by prerequisite dependencies using topological sort.

    This is the in-memory equivalent of SkillPlan.reorder_by_prerequisites().

    Args:
        skills: Set of (skill_id, level) tuples

    Returns:
        List of (skill_id, level) tuples in training order
    """
    from collections import defaultdict, deque

    if not skills:
        return []

    # Build entry map and graph
    entry_map = {key: key for key in skills}
    graph = defaultdict(list)
    in_degree = defaultdict(int)

    # Build graph with implicit level prerequisites
    for skill_id, level in skills:
        key = (skill_id, level)

        # Add implicit level prerequisite: level N-1 -> level N
        if level > 1:
            prev_level_key = (skill_id, level - 1)
            if prev_level_key in entry_map:
                graph[prev_level_key].append(key)
                in_degree[key] += 1

        # Get SDE prerequisites
        prereqs = SkillPlanExporter._get_prerequisites(skill_id)
        for prereq_dict in prereqs:
            prereq_skill_id = prereq_dict['skill_required']
            prereq_level = prereq_dict['skill_level']

            # Only include if prereq level <= our level
            if prereq_level <= level:
                prereq_key = (prereq_skill_id, prereq_level)
                if prereq_key in entry_map:
                    graph[prereq_key].append(key)
                    in_degree[key] += 1

    # Track entries with no prerequisites
    for key in skills:
        if key not in in_degree:
            in_degree[key] = 0

    # Topological sort (Kahn's algorithm)
    queue = deque([k for k in in_degree if in_degree[k] == 0])
    sorted_order = []

    while queue:
        key = queue.popleft()
        sorted_order.append(key)

        for dependent in graph[key]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    # Add any remaining (cycles or orphans)
    processed = set(sorted_order)
    for key in skills:
        if key not in processed:
            sorted_order.append(key)

    return sorted_order


def calculate_fitting_plan_progress(character, primary_skills: Set[tuple[int, int]], all_skills: Set[tuple[int, int]]) -> dict:
    """
    Calculate character progress against a set of skills.

    This is the in-memory equivalent of the skill plan progress calculation.
    Returns progress metrics similar to SkillPlan.get_pilot_progress().

    Args:
        character: Character object
        primary_skills: Set of (skill_id, level) tuples for primary goals (from fitting)
        all_skills: Set of (skill_id, level) tuples including all prerequisites

    Returns:
        Dict with progress metrics:
        - primary_sp_completed: SP completed for primary goals
        - primary_sp_total: Total SP needed for primary goals
        - primary_percent_complete: Percentage complete
        - prereq_sp_completed: SP completed for prerequisites
        - prereq_sp_total: Total SP needed for prerequisites
        - prereq_percent_complete: Percentage complete
        - prereq_complete: bool - whether all prereqs are met
        - total_training_seconds: Estimated training time remaining
    """
    from core.character.models import CharacterSkill
    from core.eve.models import TypeAttribute

    # Get character's skills as a dict for quick lookup
    char_skills = {
        cs.skill_id: cs
        for cs in CharacterSkill.objects.filter(character=character)
    }

    # Calculate SP for each skill level
    def get_sp_for_level(skill_id: int, level: int) -> int:
        """Get total SP needed for a skill level."""
        import math

        # Get skill rank
        try:
            rank_attr = TypeAttribute.objects.get(type_id=skill_id, attribute_id=275)
            rank = rank_attr.value_int if rank_attr.value_int else int(rank_attr.value_float or 1)
        except TypeAttribute.DoesNotExist:
            rank = 1

        # SP formula: 2^((2.5 * level) - 2) * 32 * rank
        return int(math.pow(2, (2.5 * level) - 2) * 32 * rank)

    # Calculate prerequisite skills (all_skills minus primary_skills)
    prereq_skills = all_skills - primary_skills

    # Calculate progress for primary skills
    primary_sp_completed = 0
    primary_sp_total = 0
    total_training_seconds = 0

    for skill_id, level in primary_skills:
        sp_needed = get_sp_for_level(skill_id, level)

        # Check what character has
        char_skill = char_skills.get(skill_id)
        if char_skill:
            sp_completed = min(char_skill.skillpoints_in_skill, sp_needed)
            current_level = char_skill.skill_level
        else:
            sp_completed = 0
            current_level = 0

        primary_sp_completed += sp_completed
        primary_sp_total += sp_needed

        # Calculate remaining training time (simplified - assumes avg attributes)
        if current_level < level:
            # Rough estimate: 1000 SP per minute (very approximate)
            sp_remaining = sp_needed - sp_completed
            total_training_seconds += (sp_remaining / 1000) * 60

    primary_percent_complete = (primary_sp_completed / primary_sp_total * 100) if primary_sp_total > 0 else 0

    # Calculate progress for prerequisite skills
    prereq_sp_completed = 0
    prereq_sp_total = 0

    for skill_id, level in prereq_skills:
        sp_needed = get_sp_for_level(skill_id, level)

        # Check what character has
        char_skill = char_skills.get(skill_id)
        if char_skill:
            sp_completed = min(char_skill.skillpoints_in_skill, sp_needed)
        else:
            sp_completed = 0

        prereq_sp_completed += sp_completed
        prereq_sp_total += sp_needed

        # Add training time for prereqs too
        if char_skill and char_skill.skill_level < level:
            sp_remaining = sp_needed - sp_completed
            total_training_seconds += (sp_remaining / 1000) * 60
        elif not char_skill:
            total_training_seconds += (sp_needed / 1000) * 60

    prereq_percent_complete = (prereq_sp_completed / prereq_sp_total * 100) if prereq_sp_total > 0 else 0
    prereq_complete = prereq_percent_complete >= 99.9  # Allow for rounding

    return {
        'primary_sp_completed': primary_sp_completed,
        'primary_sp_total': primary_sp_total,
        'primary_percent_complete': primary_percent_complete,
        'prereq_sp_completed': prereq_sp_completed,
        'prereq_sp_total': prereq_sp_total,
        'prereq_percent_complete': prereq_percent_complete,
        'prereq_complete': prereq_complete,
        'total_training_seconds': total_training_seconds,
    }


# Import models for aggregate functions
from django.db import models
