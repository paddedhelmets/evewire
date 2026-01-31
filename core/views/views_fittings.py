"""
Core views for evewire.
"""

import logging
import math
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.db import models
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger('evewire')
# ============================================================================
# FITTINGS VIEWS
# ============================================================================

@login_required
def fittings_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View all fittings with filtering."""
    from core.models import Character
    from core.doctrines.models import Fitting, FittingIgnore
    from core.eve.models import ItemType

    # Get character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        character = None

    # Get filter parameters
    ship_type_filter = request.GET.get('ship_type', '')
    search_query = request.GET.get('search', '')
    tag_filter = request.GET.get('tag', '')
    show_hidden = request.GET.get('show_hidden') == '1'
    show_system = request.GET.get('show_system') == '1'  # Default is true (checked)

    # Build base queryset
    if show_hidden:
        # Show only ignored global fittings
        ignored_ids = FittingIgnore.objects.filter(
            user=request.user
        ).values_list('fitting_id', flat=True)
        fittings_qs = Fitting.objects.filter(
            id__in=ignored_ids,
            is_active=True
        )
    else:
        # Show user's fittings + global fittings (not ignored)
        fittings_qs = Fitting.objects.for_user(request.user).active()

    # Filter out system fittings if show_system is false
    if not show_system and not show_hidden:
        # Get user's pinned fittings (including system ones they pinned)
        pinned_ids = Fitting.objects.filter(
            is_pinned=True,
            owner=None,  # System/global fittings
        ).values_list('id', flat=True)

        # Exclude system/global fittings unless pinned
        fittings_qs = fittings_qs.filter(
            Q(owner__isnull=False) | Q(id__in=pinned_ids)
        )

    # Apply ship type filter
    if ship_type_filter:
        fittings_qs = fittings_qs.filter(ship_type_id=ship_type_filter)

    # Apply search filter (must do this before tag filter since tag filter creates a list)
    if search_query:
        fittings_qs = fittings_qs.filter(name__icontains=search_query)

    # Apply tag filter (JSON field query) - must do last as it creates a list
    if tag_filter:
        # Filter by JSON tags field - check if tag exists in the tags dict
        fittings_qs = [f for f in fittings_qs if tag_filter in f.tags]

    # Prefetch related data (skip if already a list from tag filter)
    if not tag_filter:
        fittings_qs = fittings_qs.select_related()

    # Get all ship types for filter dropdown (category 6 = Ships in EVE SDE)
    from core.eve.models import ItemGroup
    ship_group_ids = ItemGroup.objects.filter(category_id=6, published=True).values_list('id', flat=True)
    ship_types = ItemType.objects.filter(group_id__in=ship_group_ids, published=True).order_by('name')

    # Get all unique tags from active fittings
    all_tags = set()
    for fitting in Fitting.objects.active():
        all_tags.update(fitting.tags.keys())

    # Get all user's characters for match display
    all_characters = list(request.user.characters.all()) if request.user.is_authenticated else []

    # Build fittings list with metadata
    from core.doctrines.models import FittingIgnore
    fittings_with_matches = []

    # Get IDs of fittings ignored by this user
    ignored_ids = set(
        FittingIgnore.objects.filter(
            user=request.user
        ).values_list('fitting_id', flat=True)
    ) if request.user.is_authenticated else set()

    for fitting in fittings_qs:
        fittings_with_matches.append({
            'fitting': fitting,
            'match_count': 0,  # Removed: use JIT on detail page instead
            'matches_by_character': {},
            'is_global': fitting.owner is None,
            'is_ignored': fitting.id in ignored_ids,
        })

    # Sort: pinned first, then by name
    fittings_with_matches.sort(key=lambda x: (not x['fitting'].is_pinned, x['fitting'].name))

    return render(request, 'core/fittings_list.html', {
        'character': character,
        'fittings_with_matches': fittings_with_matches,
        'ship_types': ship_types,
        'ship_type_filter': ship_type_filter,
        'search_query': search_query,
        'tag_filter': tag_filter,
        'all_tags': sorted(all_tags),
        'all_characters': all_characters,
        'show_hidden': show_hidden,
        'show_system': show_system,
    })


@login_required
def fitting_detail(request: HttpRequest, fitting_id: int) -> HttpResponse:
    """View fitting details with module layout and fleet readiness.

    Matches are calculated JIT (just-in-time) rather than cached.
    """
    from core.doctrines.models import Fitting
    from core.doctrines.services import AssetFitExtractor
    from core.character.models import CharacterAsset
    from core.models import Character
    from core.eve.models import ItemType, Station, SolarSystem

    try:
        fitting = Fitting.objects.get(id=fitting_id)
    except Fitting.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Fitting not found',
        }, status=404)

    # Get slots
    slots = fitting.get_slots()

    # Get fitting requirements (module type IDs)
    fitting_modules = set()
    for entry in fitting.entries.all():
        fitting_modules.add(entry.module_type_id)

    # Get ALL matching assets for current user's characters (JIT calculation)
    matching_assets = []
    character_readiness = []

    if request.user.is_authenticated:
        # Extract fitted ships for all characters
        extractor = AssetFitExtractor()
        all_fitted_ships = {}
        for character in request.user.characters.all():
            ships = extractor.extract_ships(character)
            all_fitted_ships.update({ship.asset_id: (character, ship) for ship in ships})

        # Get all assets of this ship type for location info
        ship_assets = CharacterAsset.objects.filter(
            character__in=request.user.characters.all(),
            type_id=fitting.ship_type_id
        ).select_related('character')

        # Process each ship asset
        for asset in ship_assets:
            char = asset.character

            # Calculate readiness JIT
            if asset.is_singleton:
                fitted_ship_data = all_fitted_ships.get(asset.item_id)
                if fitted_ship_data:
                    _, fitted_ship = fitted_ship_data
                    fitted_modules = fitted_ship.get_fitted_modules()
                    missing_modules = fitting_modules - fitted_modules
                    if not missing_modules:
                        match_score = 1.0
                        readiness_status = "ready"
                        missing_module_ids = []
                    else:
                        match_score = (len(fitting_modules) - len(missing_modules)) / len(fitting_modules)
                        readiness_status = "partial"
                        missing_module_ids = list(missing_modules)
                else:
                    match_score = 0.0
                    readiness_status = "none"
                    missing_module_ids = list(fitting_modules)
            else:
                # Packaged ship
                match_score = 0.0
                readiness_status = "none"
                missing_module_ids = list(fitting_modules)

            # Get asset location
            asset_location = asset.location_name if hasattr(asset, 'location_name') else "Unknown"
            asset_location_type = asset.location_type

            # Resolve missing module IDs to names
            missing_module_names = []
            for module_id in missing_module_ids:
                try:
                    module = ItemType.objects.get(id=module_id)
                    missing_module_names.append(module.name)
                except ItemType.DoesNotExist:
                    missing_module_names.append(f"Module {module_id}")

            # Build match-like object for template compatibility
            matching_assets.append({
                'match': type('Match', (), {
                    'asset_id': asset.item_id,
                    'character': char,
                    'is_match': match_score >= 1.0,
                    'match_score': match_score,
                })(),
                'asset_location': asset_location,
                'asset_location_type': asset_location_type,
                'missing_module_names': missing_module_names,
                'match_percent': match_score * 100,
            })

        # Build character readiness summary
        character_best_matches = {}
        for ma in matching_assets:
            char = ma['match'].character
            if char.id not in character_best_matches:
                character_best_matches[char.id] = ma
            else:
                if ma['match'].match_score > character_best_matches[char.id]['match'].match_score:
                    character_best_matches[char.id] = ma

        for char in request.user.characters.all():
            best = character_best_matches.get(char.id)
            if best:
                if best['match'].match_score >= 1.0:
                    readiness_status = "ready"
                elif best['match'].match_score > 0:
                    readiness_status = "partial"
                else:
                    readiness_status = "none"
            else:
                readiness_status = "none"

            character_readiness.append({
                'character': char,
                'readiness_status': readiness_status,
                'best_match': best['match'] if best else None,
            })

    # Calculate readiness summary
    total_characters = len(character_readiness)
    ready_characters = sum(1 for cr in character_readiness if cr['readiness_status'] == 'ready')
    partial_characters = sum(1 for cr in character_readiness if cr['readiness_status'] == 'partial')
    none_characters = total_characters - ready_characters - partial_characters

    return render(request, 'core/fitting_detail.html', {
        'fitting': fitting,
        'slots': slots,
        'matching_assets': matching_assets,
        'character_readiness': character_readiness,
        'readiness_summary': {
            'total': total_characters,
            'ready': ready_characters,
            'partial': partial_characters,
            'none': none_characters,
            'ready_percent': (ready_characters / total_characters * 100) if total_characters > 0 else 0,
        },
    })


@login_required
def fitting_skill_plans(request: HttpRequest, fitting_id: int) -> HttpResponse:
    """View the ephemerally generated skill plan for a fitting."""
    from core.doctrines.models import Fitting
    from core.character.models import SkillPlan, SkillPlanEntry
    from core.models import Character
    from core.skill_plans import (
        extract_fitting_skills,
        expand_prerequisites,
        order_skills_by_prerequisites,
        calculate_fitting_plan_progress,
    )
    from core.eve.models import ItemType, TypeAttribute

    try:
        fitting = Fitting.objects.get(id=fitting_id)
    except Fitting.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Fitting not found',
        }, status=404)

    # Step 1: Extract primary skills from fitting
    primary_skills = extract_fitting_skills(fitting)

    if not primary_skills:
        return render(request, 'core/error.html', {
            'message': 'This fitting has no skill requirements.',
        }, status=400)

    # Step 2: Expand with all prerequisites and intermediate levels
    all_skills = expand_prerequisites(primary_skills)

    # Step 3: Order by prerequisites
    ordered_skills = order_skills_by_prerequisites(all_skills)

    # Step 4: Pre-fetch all skill data in bulk to avoid N+1 queries
    all_skill_ids = {skill_id for skill_id, _ in all_skills}

    # Bulk fetch all ItemType records for skill names
    item_types = {
        it.id: it
        for it in ItemType.objects.filter(id__in=all_skill_ids)
    }

    # Bulk fetch all skill rank attributes (attribute_id 275 = Training time multiplier)
    rank_attrs = {
        ta.type_id: ta
        for ta in TypeAttribute.objects.filter(
            type_id__in=all_skill_ids,
            attribute_id=275
        )
    }

    # Build SP lookup function using pre-fetched data
    def get_sp_for_level(skill_id: int, level: int) -> int:
        """Get total SP needed for a skill level."""
        if level == 0:
            return 0

        rank_attr = rank_attrs.get(skill_id)
        if rank_attr:
            rank = rank_attr.value_int if rank_attr.value_int else int(rank_attr.value_float or 1)
        else:
            rank = 1

        # EVE SP formula: 250 * rank * 32^((L-1)/2)
        return int(250 * rank * math.pow(32, (level - 1) / 2))

    # Step 5: Calculate pilot progress with pre-fetched character skills
    characters = Character.objects.filter(
        user=request.user
    ).prefetch_related(
        'skills'  # Prefetch all character skills
    ).order_by('character_name')

    pilot_progress = []

    for character in characters:
        progress = calculate_fitting_plan_progress(
            character, primary_skills, all_skills,
            skill_rank_map=rank_attrs  # Pass pre-fetched rank data
        )
        pilot_progress.append({
            'character': character,
            'progress': progress,
        })

    # Step 6: Find overlapping plans (user's + global)
    # Get all plans with prefetched entries
    user_plans = SkillPlan.objects.filter(
        owner=request.user
    ).prefetch_related('entries')
    global_plans = SkillPlan.objects.filter(
        owner__isnull=True,
        is_active=True
    ).prefetch_related('entries')
    all_plans = list(user_plans) + list(global_plans)

    # Calculate total SP needed for fitting
    fitting_total_sp = sum(get_sp_for_level(sid, lvl) for sid, lvl in all_skills)

    # Calculate overlap for each plan
    plan_overlaps = []
    for plan in all_plans:
        # Get all skill IDs and levels from this plan (using prefetched entries)
        plan_skills = set(
            (entry.skill_id, entry.level)
            for entry in plan.entries.all()
            if entry.level
        )

        # Calculate skill count overlap
        covered = all_skills & plan_skills
        total = len(all_skills)
        covered_count = len(covered)

        # Calculate SP overlap
        covered_sp = sum(get_sp_for_level(sid, lvl) for sid, lvl in covered)
        sp_coverage_percent = (covered_sp / fitting_total_sp * 100) if fitting_total_sp > 0 else 0

        # Only show plans with meaningful coverage (>0%)
        if sp_coverage_percent > 0:
            plan_overlaps.append({
                'plan': plan,
                'sp_coverage_percent': sp_coverage_percent,
                'covered_sp': covered_sp,
                'total_sp': fitting_total_sp,
                'covered_count': covered_count,
                'total_count': total,
                'missing': all_skills - plan_skills,
            })

    # Sort by SP coverage percent (highest first)
    plan_overlaps.sort(key=lambda x: x['sp_coverage_percent'], reverse=True)

    # Build skill list for template (using pre-fetched ItemType data)
    skill_list = []
    for skill_id, level in ordered_skills:
        skill_type = item_types.get(skill_id)
        skill_name = skill_type.name if skill_type else f"Skill {skill_id}"

        # Determine if this is a primary skill (from fitting) or prerequisite
        is_prerequisite = (skill_id, level) not in primary_skills

        skill_list.append({
            'skill_id': skill_id,
            'skill_name': skill_name,
            'level': level,
            'level_roman': ['I', 'II', 'III', 'IV', 'V'][level - 1] if 1 <= level <= 5 else '',
            'is_prerequisite': is_prerequisite,
        })

    return render(request, 'core/fitting_skill_plans.html', {
        'fitting': fitting,
        'skill_list': skill_list,
        'primary_skill_count': len(primary_skills),
        'total_skill_count': len(all_skills),
        'pilot_progress': pilot_progress,
        'plan_overlaps': plan_overlaps,
    })


@login_required
@require_http_methods(['POST'])
def fitting_adopt_plan(request: HttpRequest, fitting_id: int) -> HttpResponse:
    """Adopt the fitting's skill plan as a real SkillPlan."""
    from core.doctrines.models import Fitting
    from core.character.models import SkillPlan, SkillPlanEntry
    from core.skill_plans import (
        extract_fitting_skills,
        expand_prerequisites,
    )
    from django.contrib import messages

    try:
        fitting = Fitting.objects.get(id=fitting_id)
    except Fitting.DoesNotExist:
        messages.error(request, 'Fitting not found.')
        return redirect('core:fittings_list')

    # Extract and expand skills
    primary_skills = extract_fitting_skills(fitting)
    all_skills = expand_prerequisites(primary_skills)

    # Get display order
    from django.db.models import Max
    max_order = SkillPlan.objects.filter(
        owner=request.user,
        parent__isnull=True
    ).aggregate(max_order=Max('display_order'))['max_order'] or 0

    # Create the skill plan
    plan = SkillPlan.objects.create(
        name=f"Skill Plan: {fitting.name}",
        description=f"Skills required to fly {fitting.name} effectively.",
        owner=request.user,
        display_order=max_order + 1,
    )

    # Bulk create all skill entries (much faster than individual creates)
    entries_to_create = []
    for display_order, (skill_id, level) in enumerate(sorted(all_skills), start=1):
        # Determine if this is a primary skill or prerequisite
        is_prereq = (skill_id, level) not in primary_skills

        entries_to_create.append(SkillPlanEntry(
            skill_plan=plan,
            skill_id=skill_id,
            level=level,
            is_prerequisite=is_prereq,
            display_order=display_order,
        ))

    SkillPlanEntry.objects.bulk_create(entries_to_create, batch_size=500)

    # Run prerequisite expansion (idempotent, ensures consistency)
    plan.ensure_prerequisites()

    # Reorder by prerequisites
    plan.reorder_by_prerequisites()

    messages.success(request, f'Created skill plan "{plan.name}" with {all_skills.__len__()} skills.')
    return redirect('core:skill_plan_detail', plan_id=plan.id)


@login_required
@require_http_methods(['POST'])
def fitting_ignore_toggle(request: HttpRequest, fitting_id: int) -> HttpResponse:
    """Toggle ignore status for a global fitting."""
    from core.doctrines.models import Fitting, FittingIgnore
    from django.http import JsonResponse

    try:
        fitting = Fitting.objects.get(id=fitting_id)
    except Fitting.DoesNotExist:
        return JsonResponse({'error': 'Fitting not found'}, status=404)

    # Can only ignore global fittings
    if fitting.owner is not None:
        return JsonResponse({'error': 'Can only ignore global fittings, not user-owned ones'}, status=400)

    # Toggle ignore status
    ignore, created = FittingIgnore.objects.get_or_create(
        user=request.user,
        fitting=fitting,
    )

    if not created:
        # Already exists, so remove it (unignore)
        ignore.delete()
        return JsonResponse({'status': 'unignored', 'message': f'Unignored {fitting.name}'})

    return JsonResponse({'status': 'ignored', 'message': f'Ignored {fitting.name}'})


@login_required
@require_http_methods(["POST"])
def fitting_pin_toggle(request: HttpRequest, fitting_id: int) -> HttpResponse:
    """Toggle pinned status for a fitting."""
    from core.doctrines.models import Fitting
    from django.http import JsonResponse

    try:
        fitting = Fitting.objects.get(id=fitting_id)
    except Fitting.DoesNotExist:
        return JsonResponse({'error': 'Fitting not found'}, status=404)

    # Toggle pinned status
    fitting.is_pinned = not fitting.is_pinned
    fitting.save()

    status = 'pinned' if fitting.is_pinned else 'unpinned'
    return JsonResponse({'status': status, 'is_pinned': fitting.is_pinned, 'message': f'{status.capitalize()} {fitting.name}'})


@login_required
def fitting_matches(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View asset matching results - show which ships match which fittings."""
    from core.models import Character
    from core.doctrines.services import AssetFitExtractor, FittingMatcher
    from core.doctrines.models import Fitting

    # Get character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        # Use first character if none specified
        try:
            character = request.user.characters.first()
            if not character:
                return render(request, 'core/error.html', {
                    'message': 'No characters found. Please add a character first.',
                }, status=404)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'No characters found. Please add a character first.',
            }, status=404)

    # Extract fitted ships and match against fittings
    extractor = AssetFitExtractor()
    matcher = FittingMatcher(extractor)
    
    fitted_ships = extractor.extract_ships(character)
    matches = []
    
    for ship in fitted_ships:
        # Find matching fittings for this ship type (user's fittings + global fittings)
        ship_fittings = Fitting.objects.for_user(request.user).active().filter(ship_type_id=ship.ship_type_id)
        
        for fitting in ship_fittings:
            match_result = matcher._match_ship_to_fitting(ship, fitting)
            if match_result:
                matches.append(match_result)
    
    # Sort by match score descending
    matches.sort(key=lambda m: m['score'], reverse=True)

    # Get all characters for filter dropdown
    characters = request.user.characters.all() if request.user.is_authenticated else []

    return render(request, 'core/fitting_matches.html', {
        'character': character,
        'characters': characters,
        'matches': matches,
        'fitted_ships_count': len(fitted_ships),
    })


@login_required
def shopping_lists_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View shopping lists for fitting fulfillment."""
    from core.models import Character
    from core.doctrines.models import ShoppingList

    # Get character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        # Use first character if none specified
        try:
            character = request.user.characters.first()
            if not character:
                return render(request, 'core/error.html', {
                    'message': 'No characters found. Please add a character first.',
                }, status=404)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'No characters found. Please add a character first.',
            }, status=404)

    # Get filter parameters
    status_filter = request.GET.get('status', '')

    # Build base queryset
    lists_qs = ShoppingList.objects.filter(character=character)

    # Apply status filter
    if status_filter:
        lists_qs = lists_qs.filter(status=status_filter)

    # Order by created date (newest first)
    lists_qs = lists_qs.order_by('-created_at')

    # Get all characters for filter dropdown
    characters = request.user.characters.all() if request.user.is_authenticated else []

    # Calculate counts by status
    all_lists = ShoppingList.objects.filter(character=character)
    pending_count = all_lists.filter(status='pending').count()
    partial_count = all_lists.filter(status='partial').count()
    complete_count = all_lists.filter(status='complete').count()

    return render(request, 'core/shopping_lists_list.html', {
        'character': character,
        'characters': characters,
        'shopping_lists': lists_qs,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'partial_count': partial_count,
        'complete_count': complete_count,
    })


@login_required
def shopping_list_detail(request: HttpRequest, list_id: int) -> HttpResponse:
    """View shopping list details."""
    from core.models import Character
    from core.doctrines.models import ShoppingList
    from core.eve.models import ItemType

    try:
        shopping_list = ShoppingList.objects.get(id=list_id)
    except ShoppingList.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Shopping list not found',
        }, status=404)

    # Check ownership
    if shopping_list.character.user != request.user:
        return render(request, 'core/error.html', {
            'message': 'Access denied',
        }, status=403)

    # Get item details for items_to_buy
    items_to_buy = []
    if shopping_list.items_to_buy:
        for type_id, quantity in shopping_list.items_to_buy.items():
            try:
                item_type = ItemType.objects.get(id=type_id)
                items_to_buy.append({
                    'type_id': type_id,
                    'name': item_type.name,
                    'quantity': quantity,
                })
            except ItemType.DoesNotExist:
                items_to_buy.append({
                    'type_id': type_id,
                    'name': f'Unknown Type {type_id}',
                    'quantity': quantity,
                })

    # Sort by name
    items_to_buy.sort(key=lambda x: x['name'])

    return render(request, 'core/shopping_list_detail.html', {
        'shopping_list': shopping_list,
        'items_to_buy': items_to_buy,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def fitting_import(request: HttpRequest) -> HttpResponse:
    """Import a fitting from EFT/DNA/XML/Markdown format."""
    from core.fitting_formats import FittingImporter, detect_format, FormatDetectionError
    from core.fitting_formats.exceptions import FittingFormatError

    if request.method == 'GET':
        return render(request, 'core/fitting_import.html', {
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })

    # Handle POST import
    content = request.POST.get('content', '')
    format_name = request.POST.get('format', '')
    auto_detect = request.POST.get('auto_detect') == 'on'

    if not content:
        return render(request, 'core/fitting_import.html', {
            'error': 'Please paste fitting content',
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })

    try:
        # Import fitting
        fitting = FittingImporter.import_from_string(
            content,
            format_name=format_name if not auto_detect else None,
            auto_detect=auto_detect,
            owner=request.user,
        )

        return render(request, 'core/fitting_import.html', {
            'success': True,
            'fitting': fitting,
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })

    except FormatDetectionError as e:
        return render(request, 'core/fitting_import.html', {
            'error': f'Could not detect format: {e}',
            'content': content,
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })
    except FittingFormatError as e:
        return render(request, 'core/fitting_import.html', {
            'error': f'Import failed: {e}',
            'content': content,
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })


@login_required
def fitting_export(request: HttpRequest, fitting_id: int, format: str) -> HttpResponse:
    """Export a fitting to EFT/DNA/XML format."""
    from django.http import FileResponse
    from core.doctrines.models import Fitting
    from core.fitting_formats import FittingExporter, FittingFormatError
    import io

    # Validate format
    if format not in ('eft', 'dna', 'xml'):
        return render(request, 'core/error.html', {
            'message': f'Invalid format: {format}',
        }, status=400)

    try:
        fitting = Fitting.objects.get(id=fitting_id)
    except Fitting.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Fitting not found',
        }, status=404)

    try:
        # Export fitting
        content = FittingExporter.export_to_string(fitting, format)

        # Create response with appropriate content type and filename
        filename = f"{fitting.name.replace('/', '-')}.{format}"
        if format == 'eft':
            content_type = 'text/plain'
        elif format == 'dna':
            content_type = 'text/plain'
        elif format == 'xml':
            content_type = 'application/xml'
        else:
            content_type = 'text/plain'

        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except FittingFormatError as e:
        return render(request, 'core/error.html', {
            'message': f'Export failed: {e}',
        }, status=500)


@login_required
@require_http_methods(['GET', 'POST'])
def fitting_bulk_import(request: HttpRequest) -> HttpResponse:
    """Bulk import fittings from a file."""
    from core.fitting_formats import FittingImporter, detect_format, FormatDetectionError
    from core.fitting_formats.exceptions import FittingFormatError
    import re

    if request.method == 'GET':
        return render(request, 'core/fitting_bulk_import.html', {
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })

    # Handle POST import
    uploaded_file = request.FILES.get('file')
    format_name = request.POST.get('format', '')
    auto_detect = request.POST.get('auto_detect') == 'on'

    if not uploaded_file:
        return render(request, 'core/fitting_bulk_import.html', {
            'error': 'Please upload a file',
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })

    try:
        content = uploaded_file.read().decode('utf-8')
    except UnicodeDecodeError:
        return render(request, 'core/fitting_bulk_import.html', {
            'error': 'File encoding error. Please upload a UTF-8 text file.',
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })

    # Import fittings
    imported = []
    errors = []

    # For EFT format, split by [Ship, Name] headers
    if format_name == 'eft' or (auto_detect and '[' in content and ']' in content and '#' not in content.split('\n')[0]):
        # Split by fitting headers
        pattern = r'\[([^,\]]+),\s*([^\]]+)\]'
        parts = re.split(pattern, content)

        for i in range(1, len(parts), 3):
            if i + 2 >= len(parts):
                break
            ship_name = parts[i].strip()
            fitting_name = parts[i + 1].strip()
            fitting_content = f'[{ship_name}, {fitting_name}]'

            # Add remaining content until next header or end
            j = i + 2
            while j < len(parts) and not parts[j].startswith('['):
                fitting_content += parts[j]
                j += 1

            try:
                fitting = FittingImporter.import_from_string(
                    fitting_content,
                    format_name='eft',
                    auto_detect=False,
                    owner=request.user,
                )
                imported.append(fitting)
            except FittingFormatError as e:
                errors.append(f'{fitting_name}: {e}')

    # For XML with multiple fittings
    elif format_name == 'xml' or (auto_detect and content.strip().startswith('<')):
        # XML can contain multiple fittings
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)

            fitting_elems = root.findall('.//fitting')
            if not fitting_elems:
                # Try direct parsing of single fitting
                fitting = FittingImporter.import_from_string(
                    content,
                    format_name='xml',
                    auto_detect=False,
                    owner=request.user,
                )
                imported.append(fitting)
            else:
                for fitting_elem in fitting_elems:
                    fitting_xml = ET.tostring(fitting_elem, encoding='unicode')
                    try:
                        fitting = FittingImporter.import_from_string(
                            f'<fittings>{fitting_xml}</fittings>',
                            format_name='xml',
                            auto_detect=False,
                            owner=request.user,
                        )
                        imported.append(fitting)
                    except FittingFormatError as e:
                        fitting_name = fitting_elem.get('name', 'Unknown')
                        errors.append(f'{fitting_name}: {e}')
        except Exception as e:
            errors.append(f'XML parsing error: {e}')

    else:
        # Single fitting (Markdown, DNA, or single EFT)
        try:
            fitting = FittingImporter.import_from_string(
                content,
                format_name=format_name if not auto_detect else None,
                auto_detect=auto_detect,
                owner=request.user,
            )
            imported.append(fitting)
        except FittingFormatError as e:
            errors.append(str(e))

    return render(request, 'core/fitting_bulk_import.html', {
        'success': True if imported else False,
        'imported': imported,
        'errors': errors,
        'formats': [
            {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
            {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
            {'name': 'XML', 'description': 'CCP official XML format'},
            {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
        ],
    })


@login_required
def fitting_readiness_browser(request: HttpRequest, fitting_id: int) -> HttpResponse:
    """
    Fleet readiness browser for a specific fitting.

    Shows all hulls of this ship type across all characters with their
    readiness status in a proper asset tree structure.

    Matches are calculated JIT (just-in-time) rather than cached.
    """
    from core.doctrines.models import Fitting
    from core.doctrines.services import AssetFitExtractor
    from core.character.models import CharacterAsset
    from core.models import Character
    from core.eve.models import ItemType, Station, SolarSystem, Structure
    from collections import defaultdict

    try:
        fitting = Fitting.objects.get(id=fitting_id)
    except Fitting.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Fitting not found',
        }, status=404)

    # Get all user's characters
    characters = list(request.user.characters.all())

    # Get fitting requirements (module type IDs)
    fitting_modules = set()
    for entry in fitting.entries.all():
        fitting_modules.add(entry.module_type_id)

    # Extract all fitted ships for all characters (JIT)
    extractor = AssetFitExtractor()
    all_fitted_ships = {}
    for character in characters:
        ships = extractor.extract_ships(character)
        all_fitted_ships.update({ship.asset_id: ship for ship in ships})

    # Build tree structure: character -> root_location -> location_tree
    location_trees = defaultdict(lambda: defaultdict(list))

    # Get ALL assets of this ship type
    ship_assets = CharacterAsset.objects.filter(
        character__in=characters,
        type_id=fitting.ship_type_id
    ).select_related('character')

    # Group by character and build location chain for each ship
    for asset in ship_assets:
        char = asset.character

        # Walk up the parent chain to build the full location path
        current = asset
        path_assets = []
        while current is not None:
            path_assets.append(current)
            current = current.parent
        path_assets.reverse()

        # Build location path for display
        location_path = []
        for path_asset in path_assets[:-1]:  # All except the ship itself
            if path_asset.location_type == 'item':
                location_path.append(path_asset.type_name or f"Item {path_asset.type_id}")
            else:
                try:
                    if path_asset.location_type == 'station':
                        loc = Station.objects.get(id=path_asset.location_id)
                        location_path.append(loc.name or f"Station {path_asset.location_id}")
                    elif path_asset.location_type == 'solar_system':
                        loc = SolarSystem.objects.get(id=path_asset.location_id)
                        location_path.append(loc.name or f"System {path_asset.location_id}")
                    elif path_asset.location_type == 'structure':
                        loc = Structure.objects.get(id=path_asset.location_id)
                        location_path.append(loc.name or f"Structure {path_asset.location_id}")
                    else:
                        location_path.append(f"{path_asset.location_type.title()} {path_asset.location_id}")
                except:
                    location_path.append(f"Location {path_asset.location_id}")

        location_key = tuple(location_path) if location_path else ("Unknown",)

        # Calculate readiness JIT
        if asset.is_singleton:
            fitted_ship = all_fitted_ships.get(asset.item_id)
            if fitted_ship:
                fitted_modules = fitted_ship.get_fitted_modules()
                missing_modules = list(fitting_modules - fitted_modules)
                if not missing_modules:
                    readiness = 'ready'
                    readiness_percent = 100
                else:
                    readiness = 'partial'
                    readiness_percent = int((len(fitting_modules) - len(missing_modules)) / len(fitting_modules) * 100)
            else:
                # Assembled ship but couldn't extract fit (empty or error)
                readiness = 'empty'
                readiness_percent = 0
                missing_modules = list(fitting_modules)
        else:
            readiness = 'packaged'
            readiness_percent = 0
            missing_modules = list(fitting_modules)

        location_trees[char][location_key].append({
            'asset': asset,
            'readiness': readiness,
            'readiness_percent': readiness_percent,
            'missing_modules': missing_modules,
            'path_assets': path_assets,
        })

    # Sort location keys for display
    def sort_key(char_loc_tuple):
        char, loc_path = char_loc_tuple
        # Handle None values in location path
        safe_path = [str(p) if p is not None else "Unknown" for p in loc_path]
        loc_str = " → ".join(safe_path)
        return (char.character_name, loc_str)

    # Flatten for template rendering
    all_ships = []
    for char, locations in sorted(location_trees.items(), key=lambda x: x[0].character_name):
        for location_path, ships in sorted(locations.items()):
            # For fitting matches, show only the ROOT location (hangar/station),
            # not the full path with intermediate ship containers
            # location_path is ordered from immediate parent to root
            root_location = location_path[-1] if location_path else "Unknown"
            all_ships.append({
                'character': char,
                'location_path': list(location_path),  # Full path for debugging
                'location_string': root_location,  # Just root for display
                'ships': ships,
            })

    # Handle shopping list generation
    shopping_list_text = None
    owned_assets = None

    if request.method == 'POST':
        selected_asset_ids = request.POST.getlist('selected_assets')
        selected_asset_ids = [int(aid) for aid in selected_asset_ids if aid.isdigit()]

        if selected_asset_ids:
            # Generate shopping list
            from collections import Counter
            shopping_modules = Counter()

            # Re-query to get selected assets with readiness info
            for ship_list in all_ships:
                for ship_info in ship_list['ships']:
                    if ship_info['asset'].item_id in selected_asset_ids:
                        for module_id in ship_info['missing_modules']:
                            shopping_modules[module_id] += 1
                        # Add hull for packaged/empty ships
                        if ship_info['readiness'] in ('packaged', 'empty'):
                            shopping_modules[fitting.ship_type_id] += 1

            # Generate plain text
            shopping_list_lines = []
            for module_id, quantity in sorted(shopping_modules.items(), key=lambda x: x[1], reverse=True):
                try:
                    item_type = ItemType.objects.get(id=module_id)
                    shopping_list_lines.append(f"{quantity}× {item_type.name}")
                except ItemType.DoesNotExist:
                    shopping_list_lines.append(f"{quantity}× Module {module_id}")

            shopping_list_text = '\n'.join(shopping_list_lines)

            # Find owned assets (excluding fitted modules)
            module_type_ids = list(shopping_modules.keys())
            owned_assets = CharacterAsset.objects.filter(
                character__in=characters,
                type_id__in=module_type_ids
            ).exclude(
                # Exclude fitted modules (items with Slot in location_flag)
                location_flag__icontains='Slot'
            ).select_related('character').order_by('character__character_name', 'type_id')

            # Pre-fetch location names for all assets using their root location
            # This shows where the item actually is (hangar/station), not parent container
            from core.eve.models import Station, SolarSystem, Structure
            stations = {}
            solar_systems = {}
            structures = {}
            for asset in owned_assets:
                # Get root location safely - handle corrupted MPTT trees
                try:
                    root = asset.get_root()
                except:
                    # Fallback: get the highest-level ancestor
                    root = asset.get_ancestors(ascending=True).first() or asset

                # Cache the location for display
                if root.location_type == 'station':
                    if root.location_id not in stations:
                        try:
                            stations[root.location_id] = Station.objects.get(id=root.location_id).name
                        except Station.DoesNotExist:
                            stations[root.location_id] = f"Station {root.location_id}"
                    asset._cached_location_name = stations[root.location_id]
                elif root.location_type == 'solar_system':
                    if root.location_id not in solar_systems:
                        try:
                            solar_systems[root.location_id] = SolarSystem.objects.get(id=root.location_id).name
                        except SolarSystem.DoesNotExist:
                            solar_systems[root.location_id] = f"System {root.location_id}"
                    asset._cached_location_name = solar_systems[root.location_id]
                elif root.location_type == 'structure':
                    if root.location_id not in structures:
                        try:
                            structures[root.location_id] = Structure.objects.get(id=root.location_id).name
                        except Structure.DoesNotExist:
                            structures[root.location_id] = f"Structure {root.location_id}"
                    asset._cached_location_name = structures[root.location_id]
                else:
                    asset._cached_location_name = f"{root.location_type.title()} {root.location_id}"

    # Calculate summary stats from JIT data
    ready_count = 0
    partial_count = 0
    zero_count = 0
    packaged_count = 0

    for ship_list in all_ships:
        for ship_info in ship_list['ships']:
            if ship_info['readiness'] == 'ready':
                ready_count += 1
            elif ship_info['readiness'] == 'partial':
                partial_count += 1
            elif ship_info['readiness'] == 'empty':
                zero_count += 1
            elif ship_info['readiness'] == 'packaged':
                packaged_count += 1

    return render(request, 'core/fitting_readiness_browser.html', {
        'fitting': fitting,
        'location_trees': all_ships,
        'total_assets': ship_assets.count(),
        'ready_count': ready_count,
        'partial_count': partial_count,
        'zero_count': zero_count,
        'packaged_count': packaged_count,
        'shopping_list_text': shopping_list_text,
        'owned_assets': owned_assets,
    })

