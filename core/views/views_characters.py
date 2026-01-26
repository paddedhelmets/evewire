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
# Character Management Views

@login_required
def characters_list(request: HttpRequest) -> HttpResponse:
    """View showing all linked characters for the current user."""
    from core.models import Character
    from core.eve.models import Corporation

    characters = request.user.characters.all()

    # Build character data with corporation ticker and training info
    characters_data = []
    for char in characters:
        skill_queue = list(char.skill_queue.all())
        current_skill = skill_queue[0] if skill_queue else None

        # Fetch corporation ticker
        corp_ticker = None
        if char.corporation_id:
            try:
                corp = Corporation.objects.get(id=char.corporation_id)
                corp_ticker = corp.ticker
            except Corporation.DoesNotExist:
                pass

        characters_data.append({
            'character': char,
            'corporation_ticker': corp_ticker,
            'training': current_skill,
        })

    return render(request, 'core/characters.html', {
        'characters': characters,
        'characters_data': characters_data,
    })


@login_required
def add_character(request: HttpRequest) -> HttpResponse:
    """Initiate adding a new character via EVE SSO."""
    from core.services import TokenManager

    sso_url = TokenManager.get_sso_login_url()
    return redirect(sso_url)


@login_required
@require_http_methods(['POST'])
def remove_character(request: HttpRequest, character_id: int) -> HttpResponse:
    """Remove a character from the user's account."""
    from core.models import Character
    from django.contrib import messages

    try:
        character = Character.objects.get(id=character_id, user=request.user)
    except Character.DoesNotExist:
        messages.error(request, 'Character not found.')
        return redirect('core:characters')

    # Don't allow removing the last character
    character_count = request.user.characters.count()
    if character_count <= 1:
        messages.error(request, 'You cannot remove your last character.')
        return redirect('core:characters')

    character_name = character.character_name
    character.delete()

    messages.success(request, f'Character "{character_name}" has been removed from your account.')
    return redirect('core:characters')


@login_required
def set_main_character(request: HttpRequest, character_id: int) -> HttpResponse:
    """Set a character as the main character (for display purposes)."""
    from core.models import Character
    from django.contrib import messages

    try:
        character = Character.objects.get(id=character_id, user=request.user)
    except Character.DoesNotExist:
        messages.error(request, 'Character not found.')
        return redirect('core:characters')

    # Update user's first character fields for backward compatibility
    request.user.eve_character_id = character.id
    request.user.eve_character_name = character.character_name
    request.user.corporation_id = character.corporation_id
    request.user.corporation_name = character.corporation_name
    request.user.alliance_id = character.alliance_id
    request.user.alliance_name = character.alliance_name
    request.user.save()

    messages.success(request, f'"{character.character_name}" set as main character.')
    return redirect('core:characters')


# Industry Views

@login_required
def industry_summary(request: HttpRequest) -> HttpResponse:
    """Multi-character industry summary with aggregate stats and jobs table."""
    from core.models import Character
    from django.utils import timezone
    from datetime import timedelta
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    # Get all characters for this user
    characters = request.user.characters.all()

    # Calculate aggregate stats across all pilots
    total_mfg_slots = sum(c.manufacturing_slots for c in characters)
    active_mfg_jobs = sum(c.active_manufacturing_jobs for c in characters)
    mfg_utilization = (active_mfg_jobs / total_mfg_slots * 100) if total_mfg_slots > 0 else 0

    total_science_slots = sum(c.science_slots for c in characters)
    active_science_jobs = sum(c.active_research_jobs for c in characters)
    science_utilization = (active_science_jobs / total_science_slots * 100) if total_science_slots > 0 else 0

    total_reaction_slots = sum(c.reaction_slots for c in characters)
    active_reaction_jobs = sum(c.active_reaction_jobs for c in characters)
    reaction_utilization = (active_reaction_jobs / total_reaction_slots * 100) if total_reaction_slots > 0 else 0

    # Build per-pilot breakdown with percentages
    pilot_stats = []
    for char in characters:
        mfg_pct = (char.active_manufacturing_jobs / char.manufacturing_slots * 100) if char.manufacturing_slots > 0 else 0
        science_pct = (char.active_research_jobs / char.science_slots * 100) if char.science_slots > 0 else 0
        reaction_pct = (char.active_reaction_jobs / char.reaction_slots * 100) if char.reaction_slots > 0 else 0

        pilot_stats.append({
            'character': char,
            'mfg_active': char.active_manufacturing_jobs,
            'mfg_total': char.manufacturing_slots,
            'mfg_pct': mfg_pct,
            'science_active': char.active_research_jobs,
            'science_total': char.science_slots,
            'science_pct': science_pct,
            'reaction_active': char.active_reaction_jobs,
            'reaction_total': char.reaction_slots,
            'reaction_pct': reaction_pct,
        })

    # Get all jobs with filters and pagination
    from core.character.models import IndustryJob
    jobs_qs = IndustryJob.objects.filter(
        character__user=request.user
    ).select_related('character').order_by('end_date')

    # Apply filters
    activity_filter = request.GET.get('activity')
    status_filter = request.GET.get('status')
    character_filter = request.GET.get('character')

    if activity_filter:
        jobs_qs = jobs_qs.filter(activity_id=activity_filter)
    if status_filter:
        jobs_qs = jobs_qs.filter(status=status_filter)
    if character_filter:
        jobs_qs = jobs_qs.filter(character_id=character_filter)

    # Paginate
    paginator = Paginator(jobs_qs, 50)
    page = request.GET.get('page', 1)
    try:
        jobs = paginator.page(page)
    except PageNotAnInteger:
        jobs = paginator.page(1)
    except EmptyPage:
        jobs = paginator.page(paginator.num_pages)

    # Get expiring soon jobs across all pilots (within 1 hour)
    one_hour_from_now = timezone.now() + timedelta(hours=1)
    expiring_jobs = IndustryJob.objects.filter(
        character__user=request.user,
        status=1,
        end_date__lte=one_hour_from_now
    ).select_related('character').order_by('end_date')[:10]

    return render(request, 'core/industry_summary.html', {
        'total_mfg_slots': total_mfg_slots,
        'active_mfg_jobs': active_mfg_jobs,
        'mfg_utilization': mfg_utilization,
        'total_science_slots': total_science_slots,
        'active_science_jobs': active_science_jobs,
        'science_utilization': science_utilization,
        'total_reaction_slots': total_reaction_slots,
        'active_reaction_jobs': active_reaction_jobs,
        'reaction_utilization': reaction_utilization,
        'pilot_stats': pilot_stats,
        'expiring_jobs': expiring_jobs,
        'jobs': jobs,
        'activity_filter': activity_filter,
        'status_filter': status_filter,
        'character_filter': character_filter,
        'characters': characters,
    })


@login_required
def industry_jobs_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View industry jobs with filtering and pagination."""
    from core.models import Character
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    # Get character
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
                'message': 'Character not found',
            }, status=404)

    return render(request, 'core/industry_jobs.html', {
        'character': character,
    })


@login_required
def industry_job_detail(request: HttpRequest, job_id: int) -> HttpResponse:
    """View detailed information about a single industry job."""
    return render(request, 'core/industry_job_detail.html', {
        'job_id': job_id,
    })


@login_required
def industry_jobs(request: HttpRequest, character_id: int) -> HttpResponse:
    """View industry jobs for a specific character."""
    from core.models import Character

    try:
        character = Character.objects.get(id=character_id, user=request.user)
    except Character.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Character not found',
        }, status=404)

    return render(request, 'core/industry_jobs.html', {
        'character': character,
    })

