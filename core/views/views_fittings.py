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

    # Build fittings_with_matches list
    from core.doctrines.models import FittingMatch, FittingIgnore
    fittings_with_matches = []

    # Get IDs of fittings ignored by this user
    ignored_ids = set(
        FittingIgnore.objects.filter(
            user=request.user
        ).values_list('fitting_id', flat=True)
    ) if request.user.is_authenticated else set()

    for fitting in fittings_qs:
        # Get match counts for this fitting across all user's characters
        matches = FittingMatch.objects.filter(
            fitting=fitting,
            character__in=all_characters,
            is_match=True
        ) if all_characters else []

        match_count = matches.count()
        matches_by_character = {}
        for match in matches:
            matches_by_character[match.character_id] = matches_by_character.get(match.character_id, 0) + 1

        fittings_with_matches.append({
            'fitting': fitting,
            'match_count': match_count,
            'matches_by_character': matches_by_character,
            'is_global': fitting.owner is None,  # Global fittings can be ignored
            'is_ignored': fitting.id in ignored_ids,
        })

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
    })


@login_required
def fitting_detail(request: HttpRequest, fitting_id: int) -> HttpResponse:
    """View fitting details with module layout and fleet readiness."""
    from core.doctrines.models import Fitting, FittingMatch
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

    # Get ALL matching assets for current user's characters (not just perfect matches)
    matching_assets = []
    character_readiness = []  # For readiness summary

    if request.user.is_authenticated:
        for character in request.user.characters.all():
            # Get all matches for this character (partial + perfect)
            matches = FittingMatch.objects.filter(
                character=character,
                fitting=fitting
            ).select_related('character').order_by('-match_score')

            # Get character's current location
            char_location = character.location_name if hasattr(character, 'location_name') else "Unknown"

            # Build readiness info for this character
            best_match = matches.first() if matches.exists() else None
            if best_match and best_match.match_score >= 1.0:
                readiness_status = "ready"
            elif best_match and best_match.match_score > 0:
                readiness_status = "partial"
            else:
                readiness_status = "none"

            character_readiness.append({
                'character': character,
                'readiness_status': readiness_status,
                'best_match': best_match,
            })

            # Enrich each match with location info and module names
            for match in matches:
                # Get asset location from CharacterAsset
                try:
                    from core.character.models import CharacterAsset
                    asset = CharacterAsset.objects.get(item_id=match.asset_id)
                    asset_location = asset.location_name if hasattr(asset, 'location_name') else "Unknown"
                    asset_location_type = asset.location_type
                except CharacterAsset.DoesNotExist:
                    asset_location = "Unknown"
                    asset_location_type = "unknown"

                # Resolve missing module IDs to names
                missing_module_names = []
                if match.missing_modules:
                    for module_id in match.missing_modules:
                        try:
                            module = ItemType.objects.get(id=module_id)
                            missing_module_names.append(module.name)
                        except ItemType.DoesNotExist:
                            missing_module_names.append(f"Module {module_id}")

                matching_assets.append({
                    'match': match,
                    'asset_location': asset_location,
                    'asset_location_type': asset_location_type,
                    'missing_module_names': missing_module_names,
                    'match_percent': match.match_score * 100,
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
    from core.eve.models import ItemType

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

    # Step 4: Calculate pilot progress
    characters = Character.objects.filter(user=request.user).order_by('character_name')
    pilot_progress = []

    for character in characters:
        progress = calculate_fitting_plan_progress(character, primary_skills, all_skills)
        pilot_progress.append({
            'character': character,
            'progress': progress,
        })

    # Step 5: Find overlapping plans (user's + global)
    # Get all plans the user can see
    user_plans = SkillPlan.objects.filter(owner=request.user)
    global_plans = SkillPlan.objects.filter(owner__isnull=True, is_active=True)
    all_plans = list(user_plans) + list(global_plans)

    # Calculate total SP for the fitting's skill set
    def get_sp_for_level(skill_id: int, level: int) -> int:
        """Get total SP needed for a skill level."""
        import math
        from core.eve.models import TypeAttribute

        try:
            rank_attr = TypeAttribute.objects.get(type_id=skill_id, attribute_id=275)
            rank = rank_attr.value_int if rank_attr.value_int else int(rank_attr.value_float or 1)
        except TypeAttribute.DoesNotExist:
            rank = 1

        return int(math.pow(2, (2.5 * level) - 2) * 32 * rank)

    # Calculate total SP needed for fitting
    fitting_total_sp = sum(get_sp_for_level(sid, lvl) for sid, lvl in all_skills)

    # Calculate overlap for each plan
    plan_overlaps = []
    for plan in all_plans:
        # Get all skill IDs and levels from this plan
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

    # Build skill list for template (similar to skill_plan_detail entries)
    skill_list = []
    for skill_id, level in ordered_skills:
        try:
            skill_type = ItemType.objects.get(id=skill_id)
            skill_name = skill_type.name
        except ItemType.DoesNotExist:
            skill_name = f"Skill {skill_id}"

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
    from core.character.models import SkillPlan
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

    # Add all skills as entries
    max_entry_order = 0
    for skill_id, level in sorted(all_skills):
        # Determine if this is a primary skill or prerequisite
        is_prereq = (skill_id, level) not in primary_skills

        SkillPlanEntry.objects.create(
            skill_plan=plan,
            skill_id=skill_id,
            level=level,
            is_prerequisite=is_prereq,
            display_order=max_entry_order + 1,
        )
        max_entry_order += 1

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
                    'base_price': float(item_type.base_price or 0),
                    'total_value': float(item_type.base_price or 0) * quantity,
                })
            except ItemType.DoesNotExist:
                items_to_buy.append({
                    'type_id': type_id,
                    'name': f'Unknown Type {type_id}',
                    'quantity': quantity,
                    'base_price': 0,
                    'total_value': 0,
                })

    # Sort by total value descending
    items_to_buy.sort(key=lambda x: x['total_value'], reverse=True)

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
def fleet_readiness(request: HttpRequest) -> HttpResponse:
    """Show fleet readiness dashboard for all tracked fittings."""
    from core.doctrines.models import Fitting, FittingMatch
    from core.models import Character
    from core.eve.models import ItemType

    # Get all tracked fittings (or all active if none tracked)
    tracked_fittings = Fitting.objects.filter(is_tracked=True)
    if not tracked_fittings.exists():
        # Fallback to active fittings if nothing is tracked
        tracked_fittings = Fitting.objects.filter(is_active=True)

    # Calculate readiness for each fitting
    fitting_readiness = []
    for fitting in tracked_fittings:
        # Get readiness summary across all user's characters
        characters_ready = 0
        characters_partial = 0
        characters_total = 0
        matches_data = []
        missing_modules_counts = {}  # {module_id: count} for common gaps

        for character in request.user.characters.all():
            characters_total += 1

            # Get all matches for this character/fitting
            matches = FittingMatch.objects.filter(
                character=character,
                fitting=fitting
            ).order_by('-match_score')

            best_match = matches.first()
            if best_match and best_match.match_score >= 1.0:
                characters_ready += 1
            elif best_match and best_match.match_score > 0:
                characters_partial += 1

            # Count missing modules for common gaps analysis
            for match in matches:
                for module_id in match.missing_modules:
                    missing_modules_counts[module_id] = missing_modules_counts.get(module_id, 0) + 1

            matches_data.append({
                'character': character,
                'best_match': best_match,
                'match_percent': (best_match.match_score * 100) if best_match else 0,
            })

        # Calculate readiness percentage
        readiness_percent = (characters_ready / characters_total * 100) if characters_total > 0 else 0

        # Get top 5 most common missing modules
        sorted_missing = sorted(missing_modules_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_missing = []
        for module_id, count in sorted_missing:
            try:
                module = ItemType.objects.get(id=module_id)
                top_missing.append({
                    'name': module.name,
                    'count': count,
                })
            except ItemType.DoesNotExist:
                top_missing.append({
                    'name': f"Module {module_id}",
                    'count': count,
                })

        fitting_readiness.append({
            'fitting': fitting,
            'characters_ready': characters_ready,
            'characters_partial': characters_partial,
            'characters_total': characters_total,
            'readiness_percent': readiness_percent,
            'matches_data': matches_data,
            'top_missing': top_missing,
        })

    # Sort by readiness percent (highest first), then by name
    fitting_readiness.sort(key=lambda x: (-x['readiness_percent'], x['fitting'].name))

    return render(request, 'core/fleet_readiness.html', {
        'fitting_readiness': fitting_readiness,
        'total_fittings': len(fitting_readiness),
    })
