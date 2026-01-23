"""Character views."""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

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


