"""
Core views for evewire.
"""

import logging
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.db import models
from django.utils import timezone
from core.views import get_users_character


logger = logging.getLogger(__name__)
# Skill Plan Views

@login_required
def skill_plan_list(request: HttpRequest) -> HttpResponse:
    """List all skill plans for the current user plus reference plans."""
    from core.character.models import SkillPlan
    from django.db.models import Prefetch, Count

    # Prefetch entries to avoid N+1 queries
    user_plans = SkillPlan.objects.filter(
        owner=request.user, parent__isnull=True, is_reference=False
    ).prefetch_related('entries').annotate(entry_count=Count('entries'))

    reference_plans = SkillPlan.objects.filter(
        parent__isnull=True, is_reference=True
    ).prefetch_related('entries').annotate(entry_count=Count('entries'))

    return render(request, 'core/skill_plan_list.html', {
        'user_plans': user_plans,
        'reference_plans': reference_plans,
    })


@login_required
def skill_plan_detail(request: HttpRequest, plan_id: int) -> HttpResponse:
    """Show a single skill plan with progress for all user's characters."""
    from core.character.models import SkillPlan
    from core.models import Character
    from core.skill_plans import calculate_training_time

    try:
        plan = SkillPlan.objects.get(id=plan_id)
    except SkillPlan.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Skill plan not found',
        }, status=404)

    # Get all user's characters
    characters = Character.objects.filter(user=request.user).order_by('character_name')

    # Calculate progress for each character
    pilot_progress = []
    for char in characters:
        progress = plan.get_progress_for_character(char)
        percent_complete = 0
        if progress['total_entries'] > 0:
            percent_complete = (progress['completed'] / progress['total_entries']) * 100

        # Calculate remaining training time
        character_skills = {s.skill_id: s for s in char.skills.all()}
        total_training_seconds = 0

        for entry in plan.entries.all():
            target_level = entry.level or entry.recommended_level
            if target_level:
                skill = character_skills.get(entry.skill_id)
                current_level = skill.skill_level if skill else 0
                if current_level < target_level:
                    try:
                        training_time = calculate_training_time(char, entry.skill_id, target_level)
                        total_training_seconds += training_time['total_seconds']
                    except Exception:
                        pass

        pilot_progress.append({
            'character': char,
            'progress': progress,
            'percent_complete': percent_complete,
            'total_training_seconds': total_training_seconds,
        })

    # Sort by percent complete descending
    pilot_progress.sort(key=lambda x: x['percent_complete'], reverse=True)

    # Count completed pilots
    completed_pilots = sum(1 for p in pilot_progress if p['progress']['completed'] >= p['progress']['total_entries'])
    total_pilots = len(pilot_progress)

    # Get all skills organized by group for the Add Skill dropdown
    from core.eve.models import ItemType, ItemGroup
    from collections import defaultdict

    # Get all skill groups (category 16)
    skill_group_ids = ItemGroup.objects.filter(
        category_id=16,
        published=True
    ).values_list('id', flat=True)

    # Get all skills in those groups
    skills_by_group = defaultdict(list)
    skills = ItemType.objects.filter(
        published=True,
        group_id__in=skill_group_ids
    ).order_by('name')

    # Get group names for display
    groups = {g.id: g.name for g in ItemGroup.objects.filter(id__in=skill_group_ids)}

    for skill in skills:
        group_name = groups.get(skill.group_id, 'Unknown')
        skills_by_group[group_name].append(skill)

    # Sort groups and skills within groups
    skills_by_group_dict = dict(sorted(skills_by_group.items()))
    for group_name in skills_by_group_dict:
        skills_by_group_dict[group_name] = sorted(skills_by_group_dict[group_name], key=lambda s: s.name)

    return render(request, 'core/skill_plan_detail.html', {
        'plan': plan,
        'entries': plan.entries.all().order_by('display_order'),
        'pilot_progress': pilot_progress,
        'completed_pilots': completed_pilots,
        'total_pilots': total_pilots,
        'skills_by_group': skills_by_group_dict,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def skill_plan_create(request: HttpRequest) -> HttpResponse:
    """Create a new skill plan."""
    from core.character.models import SkillPlan
    from django.contrib import messages

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')

        if not name:
            messages.error(request, 'Plan name is required.')
            return render(request, 'core/skill_plan_form.html', {
                'mode': 'create',
            })

        # Get display order
        max_order = SkillPlan.objects.filter(
            owner=request.user,
            parent__isnull=True
        ).aggregate(max_order=models.Max('display_order'))['max_order'] or 0

        plan = SkillPlan.objects.create(
            name=name,
            description=description,
            owner=request.user,
            display_order=max_order + 1,
        )

        messages.success(request, f'Skill plan "{name}" created.')
        return redirect('core:skill_plan_detail', plan_id=plan.id)

    return render(request, 'core/skill_plan_form.html', {
        'mode': 'create',
    })


@login_required
@require_http_methods(['GET', 'POST'])
def skill_plan_edit(request: HttpRequest, plan_id: int) -> HttpResponse:
    """Edit an existing skill plan."""
    from core.character.models import SkillPlan
    from django.contrib import messages

    try:
        plan = SkillPlan.objects.get(id=plan_id, owner=request.user)
    except SkillPlan.DoesNotExist:
        messages.error(request, 'Skill plan not found.')
        return redirect('core:skill_plan_list')

    if request.method == 'POST':
        plan.name = request.POST.get('name', plan.name)
        plan.description = request.POST.get('description', plan.description)
        plan.save()

        messages.success(request, 'Skill plan updated.')
        return redirect('core:skill_plan_detail', plan_id=plan.id)

    return render(request, 'core/skill_plan_form.html', {
        'mode': 'edit',
        'plan': plan,
    })


@login_required
@require_http_methods(['POST'])
def skill_plan_delete(request: HttpRequest, plan_id: int) -> HttpResponse:
    """Delete a skill plan."""
    from core.character.models import SkillPlan
    from django.contrib import messages

    try:
        plan = SkillPlan.objects.get(id=plan_id, owner=request.user)
    except SkillPlan.DoesNotExist:
        messages.error(request, 'Skill plan not found.')
        return redirect('core:skill_plan_list')

    plan_name = plan.name
    plan.delete()

    messages.success(request, f'Skill plan "{plan_name}" deleted.')
    return redirect('core:skill_plan_list')


@login_required
@require_http_methods(['POST'])
def skill_plan_add_skill(request: HttpRequest, plan_id: int) -> HttpResponse:
    """Add a skill to a skill plan."""
    from core.character.models import SkillPlan, SkillPlanEntry
    from core.eve.models import ItemType
    from django.contrib import messages

    try:
        plan = SkillPlan.objects.get(id=plan_id, owner=request.user)
    except SkillPlan.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Skill plan not found',
        }, status=404)

    skill_id = request.POST.get('skill_id')
    level = request.POST.get('level')
    recommended_level = request.POST.get('recommended_level')

    if not skill_id:
        messages.error(request, 'Skill is required.')
        return redirect('core:skill_plan_detail', plan_id=plan.id)

    # Validate skill exists
    try:
        ItemType.objects.get(id=skill_id)
    except ItemType.DoesNotExist:
        messages.error(request, 'Invalid skill.')
        return redirect('core:skill_plan_detail', plan_id=plan.id)

    # Validate levels
    if level:
        try:
            level = int(level)
            if not 1 <= level <= 5:
                raise ValueError()
        except (ValueError, TypeError):
            messages.error(request, 'Level must be between 1 and 5.')
            return redirect('core:skill_plan_detail', plan_id=plan.id)

    if recommended_level:
        try:
            recommended_level = int(recommended_level)
            if not 1 <= recommended_level <= 5:
                raise ValueError()
        except (ValueError, TypeError):
            messages.error(request, 'Recommended level must be between 1 and 5.')
            return redirect('core:skill_plan_detail', plan_id=plan.id)

    # Check if skill already in plan
    if SkillPlanEntry.objects.filter(skill_plan=plan, skill_id=skill_id).exists():
        messages.error(request, 'Skill already in plan.')
        return redirect('core:skill_plan_detail', plan_id=plan.id)

    # Get display order
    max_order = SkillPlanEntry.objects.filter(
        skill_plan=plan
    ).aggregate(max_order=models.Max('display_order'))['max_order'] or 0

    SkillPlanEntry.objects.create(
        skill_plan=plan,
        skill_id=skill_id,
        level=level,
        recommended_level=recommended_level,
        display_order=max_order + 1,
    )

    messages.success(request, 'Skill added to plan.')
    return redirect('core:skill_plan_detail', plan_id=plan.id)


@login_required
def skill_search(request: HttpRequest) -> JsonResponse:
    """Search for skills by name (autocomplete).

    Only returns actual skills (category 16), not all item types.
    Results include group name for better organization.
    """
    from core.eve.models import ItemType, ItemGroup

    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse({'results': []})

    # Search ItemType by name, limited to skills (category 16 = Skills)
    # Join with ItemGroup to filter by category
    skills = ItemType.objects.filter(
        name__icontains=query,
        published=True,
        group__category_id=16,  # Skills category
        group__published=True
    ).values('id', 'name', 'group_id')[:30]

    # Get group names for the skills
    group_ids = list(set(s['group_id'] for s in skills if s['group_id']))
    groups = {}
    if group_ids:
        for group in ItemGroup.objects.filter(id__in=group_ids):
            groups[group.id] = group.name

    results = [
        {
            'id': str(s['id']),
            'name': s['name'],
            'text': f"{s['name']}",
            'group': groups.get(s['group_id'], 'Unknown'),
        }
        for s in skills
    ]

    return JsonResponse({'results': results})


@login_required
@require_http_methods(['POST'])
def skill_plan_remove_skill(request: HttpRequest, plan_id: int, entry_id: int) -> HttpResponse:
    """Remove a skill from a skill plan."""
    from core.character.models import SkillPlan, SkillPlanEntry
    from django.contrib import messages

    try:
        plan = SkillPlan.objects.get(id=plan_id, owner=request.user)
        entry = SkillPlanEntry.objects.get(id=entry_id, skill_plan=plan)
    except (SkillPlan.DoesNotExist, SkillPlanEntry.DoesNotExist):
        messages.error(request, 'Skill plan or entry not found.')
        return redirect('core:skill_plan_list')

    entry.delete()
    messages.success(request, 'Skill removed from plan.')
    return redirect('core:skill_plan_detail', plan_id=plan.id)


@login_required
@require_http_methods(['POST'])
def skill_plan_import_skills(request: HttpRequest, plan_id: int) -> HttpResponse:
    """Import skills from clipboard text to a skill plan.

    Format: One skill per line: SKILL_NAME LEVEL
    Level can be 1-5 or I-V (Roman numerals optional).
    Example: "Amarr Battleship V" or "Amarr Battleship 5"
    """
    from core.character.models import SkillPlan, SkillPlanEntry
    from core.eve.models import ItemType
    from django.contrib import messages
    import re

    try:
        plan = SkillPlan.objects.get(id=plan_id, owner=request.user)
    except SkillPlan.DoesNotExist:
        messages.error(request, 'Skill plan not found.')
        return redirect('core:skill_plan_list')

    skills_text = request.POST.get('skills', '')
    if not skills_text.strip():
        messages.error(request, 'No skills to import.')
        return redirect('core:skill_plan_detail', plan_id=plan.id)

    # Roman numeral mapping
    roman_to_int = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5}

    # Parse skills: each line is "SKILL_NAME LEVEL"
    lines = skills_text.strip().split('\n')
    added_count = 0
    skipped_count = 0
    not_found = []

    # Get current skills in plan
    existing_skill_ids = set(
        SkillPlanEntry.objects.filter(skill_plan=plan).values_list('skill_id', flat=True)
    )

    # Get max display order
    max_order = SkillPlanEntry.objects.filter(
        skill_plan=plan
    ).aggregate(max_order=models.Max('display_order'))['max_order'] or 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Split by last space to separate skill name from level
        # This handles skill names with spaces like "Amarr Battleship"
        parts = line.rsplit(' ', 1)
        if len(parts) != 2:
            skipped_count += 1
            continue

        skill_name, level_str = parts
        level_str = level_str.strip().lower()

        # Parse level: 1-5 or I-V (roman)
        if level_str.isdigit() and 1 <= int(level_str) <= 5:
            level = int(level_str)
        elif level_str in roman_to_int:
            level = roman_to_int[level_str]
        else:
            skipped_count += 1
            continue

        # Find skill by name (case-insensitive, exact match preferred)
        skill = ItemType.objects.filter(name__iexact=skill_name, published=True).first()
        if not skill:
            # Try partial match
            skill = ItemType.objects.filter(name__icontains=skill_name, published=True).first()

        if not skill:
            not_found.append(skill_name)
            continue

        # Skip if already in plan
        if skill.id in existing_skill_ids:
            skipped_count += 1
            continue

        # Add to plan
        SkillPlanEntry.objects.create(
            skill_plan=plan,
            skill=skill,
            level=level,
            display_order=max_order + added_count + 1,
        )
        existing_skill_ids.add(skill.id)
        added_count += 1

    # Build result message
    if added_count > 0:
        msg = f'Added {added_count} skill(s) to plan.'
        if skipped_count > 0:
            msg += f' Skipped {skipped_count} invalid line(s).'
        if not_found:
            msg += f' {len(not_found)} skill(s) not found.'
        messages.success(request, msg)
    else:
        if not_found:
            messages.error(request, f'No skills added. Skills not found: {", ".join(not_found[:5])}{"..." if len(not_found) > 5 else ""}')
        else:
            messages.error(request, 'No valid skills found to import.')

    return redirect('core:skill_plan_detail', plan_id=plan.id)


@login_required
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


# Skill Plan Import/Export Views

@login_required
def skill_plan_export(request: HttpRequest, plan_id: int) -> HttpResponse:
    """Export a skill plan to EVE XML format."""
    from core.character.models import SkillPlan
    from core.models import Character
    from core.skill_plans import SkillPlanExporter

    try:
        plan = SkillPlan.objects.get(id=plan_id, owner=request.user)
    except SkillPlan.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Skill plan not found.',
        }, status=404)

    # Get options
    include_prereqs = request.GET.get('prereqs', '1') == '1'
    include_known = request.GET.get('known', '0') == '1'

    # Get user's character for checking known skills
    character = None
    if not include_known:
        character = get_users_character(request.user)

    # Generate XML
    xml_content = SkillPlanExporter.export_to_xml(
        plan,
        character=character,
        include_prereqs=include_prereqs,
        include_known=include_known,
    )

    # Create response
    response = HttpResponse(xml_content, content_type='application/xml')
    filename = f"{plan.name}.xml"
    filename = filename.replace(' ', '_').replace('/', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_http_methods(['GET', 'POST'])
def skill_plan_import(request: HttpRequest) -> HttpResponse:
    """Import a skill plan from EVE XML format."""
    from core.skill_plans import SkillPlanImporter
    from django.contrib import messages

    if request.method == 'POST':
        xml_file = request.FILES.get('xml_file')
        plan_name = request.POST.get('name', '')

        if not xml_file:
            messages.error(request, 'Please select an XML file to import.')
            return render(request, 'core/skill_plan_import.html')

        try:
            xml_content = xml_file.read().decode('utf-8')
            plan = SkillPlanImporter.import_from_xml(
                xml_content,
                owner=request.user,
                name=plan_name or None,
            )
            messages.success(request, f'Skill plan "{plan.name}" imported successfully.')
            return redirect('core:skill_plan_detail', plan_id=plan.id)

        except Exception as e:
            messages.error(request, f'Failed to import skill plan: {e}')
            logger.error(f'Skill plan import failed: {e}')
            return render(request, 'core/skill_plan_import.html')

    return render(request, 'core/skill_plan_import.html')

