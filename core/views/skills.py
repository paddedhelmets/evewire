"""Skills views."""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger(__name__)


def get_users_character(user):
    """Get user's character (first character if multiple).
    Returns None if user has no characters.
    """
    from core.models import Character
    return Character.objects.filter(user=user).first()


def skills_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """List skills grouped by category, for a specific character.

    Shows ALL available skills with visual distinction for:
    - Not injected (character doesn't have the skill at all)
    - Level 0 with SP (injected but not trained)
    - Trained (level 1-5)

    Query parameters:
        category: Filter to specific skill group name
        show: 'all' (default) or 'trained' (hide untrained)
    """
    from core.character.models import CharacterSkill
    from core.eve.models import ItemType, ItemGroup, ItemCategory, TypeAttribute
    from core.models import Character
    from core.skill_plans import calculate_training_time
    import math

    # Get character - from URL param or user's first character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        character = get_users_character(request.user)
        if not character:
            return render(request, 'core/error.html', {
                'message': 'No characters found. Please add a character first.',
            }, status=404)

    # Get filter parameters
    category_filter = request.GET.get('category', '')
    show_filter = request.GET.get('show', 'all')  # 'all' or 'trained'

    # Get all skills from SDE (skills category = 16)
    skills_category = ItemCategory.objects.filter(name__icontains='skill').first()
    if skills_category:
        all_skill_types = ItemType.objects.filter(
            group_id__in=list(
                ItemGroup.objects.filter(category_id=skills_category.id).values_list('id', flat=True)
            )
        ).select_related()
    else:
        all_skill_types = ItemType.objects.none()

    # Get character's trained skills for lookup
    trained_skills = {
        cs.skill_id: cs
        for cs in CharacterSkill.objects.filter(character=character)
    }

    # EVE attribute ID mapping
    ATTRIBUTE_NAMES = {
        164: 'intelligence',
        165: 'perception',
        166: 'willpower',
        167: 'charisma',
        168: 'memory',
    }

    def calculate_sp_for_level(rank: int, level: int) -> int:
        """Calculate total SP required for a given level."""
        if level == 0:
            return 0
        return int(math.pow(2, (2.5 * level) - 2) * 32 * rank)

    # Build comprehensive skill list
    skills_with_groups = []
    groups_seen = set()

    for skill_type in all_skill_types:
        group = None
        try:
            group = ItemGroup.objects.get(id=skill_type.group_id)
        except ItemGroup.DoesNotExist:
            pass

        if group:
            groups_seen.add(group.id)

        # Check character's status for this skill
        trained_skill = trained_skills.get(skill_type.id)
        if trained_skill:
            # Character has this skill injected
            level = trained_skill.skill_level
            sp = trained_skill.skillpoints_in_skill

            # Determine status
            if level == 0:
                status = 'injected'  # Has SP but level 0
            else:
                status = 'trained'  # Level 1+

            skill_obj = trained_skill
        else:
            # Character doesn't have this skill
            level = 0
            sp = 0
            status = 'not_injected'
            skill_obj = None

        # Get skill rank (attribute 275)
        rank_attr = TypeAttribute.objects.filter(
            type_id=skill_type.id,
            attribute_id=275
        ).first()
        rank = 1
        if rank_attr:
            if rank_attr.value_int is not None:
                rank = int(rank_attr.value_int)
            elif rank_attr.value_float is not None:
                rank = int(rank_attr.value_float)

        # Get primary/secondary attributes
        primary_attr = TypeAttribute.objects.filter(
            type_id=skill_type.id,
            attribute_id=180
        ).first()
        secondary_attr = TypeAttribute.objects.filter(
            type_id=skill_type.id,
            attribute_id=181
        ).first()

        primary_name = ATTRIBUTE_NAMES.get(int(primary_attr.value_int) if primary_attr and primary_attr.value_int else None, 'intelligence')
        secondary_name = ATTRIBUTE_NAMES.get(int(secondary_attr.value_int) if secondary_attr and secondary_attr.value_int else None, 'memory')

        # Calculate SP for current and next level
        sp_for_level = calculate_sp_for_level(rank, level)
        sp_for_next = calculate_sp_for_level(rank, level + 1) if level < 5 else sp_for_level

        # Calculate training time to next level (if not maxed)
        training_time = None
        if level < 5 and status != 'not_injected':
            try:
                training_time = calculate_training_time(character, skill_type.id, level + 1)
            except Exception:
                training_time = None

        skill_data = {
            'skill_id': skill_type.id,
            'skill': skill_obj,  # CharacterSkill object or None
            'name': skill_type.name,
            'group': group,
            'level': level,
            'level_stars': '★' * level + '☆' * (5 - level),
            'group_id': skill_type.group_id,
            'group_name': group.name if group else 'Unknown',
            'training_time': training_time,
            'rank': rank,
            'primary_attr': primary_name,
            'secondary_attr': secondary_name,
            'sp_current': sp,
            'sp_for_level': sp_for_level,
            'sp_for_next': sp_for_next,
            'status': status,
        }

        # Apply filters
        include = True
        if category_filter and skill_data['group_name'] != category_filter:
            include = False
        if show_filter == 'trained' and status == 'not_injected':
            include = False

        if include:
            skills_with_groups.append(skill_data)

    # Sort by group name, then skill name
    skills_with_groups.sort(key=lambda x: (x['group_name'], x['name']))

    # Group by group_name for template
    from collections import defaultdict
    grouped = defaultdict(list)
    for s in skills_with_groups:
        grouped[s['group_name']].append(s)

    # Get all available categories for the filter dropdown
    all_categories = sorted(groups_seen)

    # Get character's trained skill count
    trained_count = len([s for s in skills_with_groups if s['status'] in ('trained', 'injected')])

    return render(request, 'core/skills_list.html', {
        'character': character,
        'skills': skills_with_groups,
        'grouped_skills': dict(grouped),
        'total_skills': len(skills_with_groups),
        'trained_skills': trained_count,
        'untrained_skills': len(skills_with_groups) - trained_count,
        'total_sp': character.total_sp or 0,
        'total_groups': len(grouped),
        'category_filter': category_filter,
        'all_categories': all_categories,
        'show_filter': show_filter,
    })


@login_required
def implants_view(request: HttpRequest) -> HttpResponse:
    """View character implants with slot information."""
    from core.character.models import CharacterImplant
    from core.eve.models import ItemType

    character = get_users_character(request.user)
    if not character:
        return render(request, 'core/error.html', {
            'message': 'No characters found. Please add a character first.',
        }, status=404)

    # Get all implants for this character
    implants_qs = CharacterImplant.objects.filter(character=character).select_related()

    # Group by slot (implants don't have explicit slot field, so we'll need to get it from type)
    # For now, just list all implants with their type names
    implants = []
    for implant in implants_qs:
        try:
            item_type = ItemType.objects.get(id=implant.type_id)
            implants.append({
                'type_id': implant.type_id,
                'name': item_type.name,
                'slot': _get_implant_slot(implant.type_id),
            })
        except ItemType.DoesNotExist:
            implants.append({
                'type_id': implant.type_id,
                'name': f"Type {implant.type_id}",
                'slot': 'Unknown',
            })

    # Check for empty slots (1-10)
    filled_slots = set(imp['slot'] for imp in implants if isinstance(imp['slot'], int))
    all_slots = list(range(1, 11))
    empty_slots = [slot for slot in all_slots if slot not in filled_slots]

    return render(request, 'core/implants.html', {
        'character': character,
        'implants': implants,
        'empty_slots': empty_slots,
        'total_slots': 10,
    })


@login_required
def attributes_view(request: HttpRequest) -> HttpResponse:
    """View character attributes with skill group associations."""
    from core.character.models import CharacterAttributes

    character = get_users_character(request.user)
    if not character:
        return render(request, 'core/error.html', {
            'message': 'No characters found. Please add a character first.',
        }, status=404)

    try:
        attrs = character.attributes
    except CharacterAttributes.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Attributes not found. Please sync your character.',
        }, status=404)

    # Skill group associations with attributes
    skill_groups = {
        'intelligence': ['Electronics', 'Engineering', 'Science', 'Mechanics', 'Drones'],
        'perception': ['Spaceship Command', 'Gunnery', 'Missiles'],
        'charisma': ['Trade', 'Social', 'Leadership', 'Corporation Management'],
        'willpower': ['Command', 'Advanced Industry'],
        'memory': ['Industry', 'Learning'],
    }

    return render(request, 'core/attributes.html', {
        'character': character,
        'attributes': attrs,
        'skill_groups': skill_groups,
    })


def _get_implant_slot(type_id: int) -> int | str:
    """
    Get the implant slot for a given type_id.

    This is a simplified version - in production, you'd look this up from SDE data.
    Implant slots:
    - 1-5: Attribute implants (1=Int, 2=Per, 3=Cha, 4=Wil, 5=Mem)
    - 6-10: Limited implant slots
    """
    # This is a placeholder - you'd implement proper SDE lookup
    # For now, return the slot based on type_id ranges or a lookup table
    from core.eve.models import ItemType

    try:
        item_type = ItemType.objects.get(id=type_id)
        name = item_type.name.lower()

        # Simple heuristic based on name (not perfect, but functional)
        if 'intelligence' in name or 'logic' in name:
            return 1
        elif 'perception' in name or 'optic' in name:
            return 2
        elif 'charisma' in name or 'social' in name:
            return 3
        elif 'willpower' in name or 'command' in name:
            return 4
        elif 'memory' in name or 'cerebral' in name:
            return 5
        elif 'limited' in name:
            # Slot 6-10 are limited implants - for now just return 6
            return 6
        else:
            return 'Unknown'
    except ItemType.DoesNotExist:
        return 'Unknown'