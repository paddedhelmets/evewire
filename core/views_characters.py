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
# Character Management Views

@login_required
def characters_list(request: HttpRequest) -> HttpResponse:
    """View showing all linked characters for the current user."""
    from core.models import Character

    characters = request.user.characters.all()

    return render(request, 'core/characters.html', {
        'characters': characters,
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
def industry_summary(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View industry summary across all characters or a specific character."""
    from core.models import Character
    from django.utils import timezone
    from datetime import timedelta

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

    # Get expiring soon jobs (within 1 hour)
    one_hour_from_now = timezone.now() + timedelta(hours=1)
    expiring_jobs = character.industry_jobs.filter(
        status=1,
        end_date__lte=one_hour_from_now
    ).order_by('end_date')[:10]

    return render(request, 'core/industry_summary.html', {
        'character': character,
        'expiring_jobs': expiring_jobs,
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

