"""
Core views for evewire.

Includes authentication, dashboard, and character views.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse
from django.urls import reverse

logger = logging.getLogger('evewire')


def index(request: HttpRequest) -> HttpResponse:
    """Landing page - show login button or redirect to dashboard."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/index.html')


@require_http_methods(['GET', 'POST'])
def login_view(request: HttpRequest) -> HttpResponse:
    """Initiate EVE SSO login flow."""
    from core.services import TokenManager

    if request.user.is_authenticated:
        return redirect('dashboard')

    sso_url = TokenManager.get_sso_login_url()
    return redirect(sso_url)


def oauth_callback(request: HttpRequest) -> HttpResponse:
    """Handle EVE SSO OAuth callback."""
    from core.services import AuthService

    code = request.GET.get('code')
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')

    if error:
        logger.error(f'OAuth error: {error} - {error_description}')
        return render(request, 'core/auth_error.html', {
            'error': error,
            'error_description': error_description,
        })

    if not code:
        logger.error('OAuth callback missing code parameter')
        return render(request, 'core/auth_error.html', {
            'error': 'Missing authorization code',
        })

    try:
        user = AuthService.handle_callback(code)
        login(request, user)
        logger.info(f'User {user.eve_character_name} logged in via SSO')
        return redirect('dashboard')

    except Exception as e:
        logger.error(f'Failed to handle OAuth callback: {e}')
        return render(request, 'core/auth_error.html', {
            'error': 'Authentication failed',
            'error_description': str(e),
        })


@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    """Log out the current user."""
    logger.info(f'User {request.user.eve_character_name} logged out')
    logout(request)
    return redirect('index')


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Main dashboard showing user's characters."""
    from core.models import Character
    from django.contrib import messages

    # For MVP, user has 1:1 character relationship
    try:
        character = Character.objects.get(user=request.user)
    except Character.DoesNotExist:
        # Attempt to create character from user's SSO data
        try:
            character = Character.objects.create(
                id=request.user.eve_character_id,
                user=request.user
            )
            messages.info(request, 'Character profile created. Please sync your data.')
        except Exception as e:
            logger.error(f'Failed to create character for user {request.user.id}: {e}')
            messages.error(request, 'Could not load character profile. Please try logging in again.')
            character = None

    return render(request, 'core/dashboard.html', {
        'character': character,
    })


@login_required
def character_detail(request: HttpRequest, character_id: int) -> HttpResponse:
    """Detailed view of a single character."""
    from core.models import Character

    try:
        character = Character.objects.get(id=character_id, user=request.user)
    except Character.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Character not found',
        }, status=404)

    return render(request, 'core/character_detail.html', {
        'character': character,
    })


@login_required
@require_http_methods(['POST'])
def toggle_theme(request: HttpRequest) -> HttpResponse:
    """Toggle between light and dark theme."""
    from django.contrib import messages

    current_theme = request.user.settings.get('theme', 'light')
    new_theme = 'dark' if current_theme == 'light' else 'light'
    request.user.settings['theme'] = new_theme
    request.user.save(update_fields=['settings'])

    messages.success(request, f'Theme changed to {new_theme} mode.')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@login_required
@require_http_methods(['POST'])
def sync_character(request: HttpRequest, character_id: int) -> HttpResponse:
    """Trigger a manual sync of character data from ESI."""
    from core.models import Character
    from django.contrib import messages
    from django_q.tasks import async_task

    try:
        character = Character.objects.get(id=character_id, user=request.user)
    except Character.DoesNotExist:
        messages.error(request, 'Character not found.')
        return redirect('dashboard')

    # Update sync status
    character.last_sync_status = 'pending'
    character.last_sync_error = ''
    character.save(update_fields=['last_sync_status', 'last_sync_error'])

    # Queue the sync task
    try:
        async_task('core.services.sync_character_data', character)
        messages.success(request, 'Character sync started. Data will be updated shortly.')
    except Exception as e:
        logger.error(f'Failed to queue sync task for character {character_id}: {e}')
        character.last_sync_status = 'failed'
        character.last_sync_error = str(e)
        character.save(update_fields=['last_sync_status', 'last_sync_error'])
        messages.error(request, f'Failed to start sync: {e}')

    # Redirect back to the page we came from
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('character_detail', character_id=character_id)
