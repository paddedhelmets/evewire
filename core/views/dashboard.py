"""Dashboard views."""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Main dashboard showing user's characters with aggregated stats."""
    from core.models import Character
    from django.contrib import messages
    from django.db.models import Sum, Q

    # Get all characters for this user
    characters = request.user.characters.select_related().all()

    # Redirect to characters list if user has no characters
    if not characters.exists():
        messages.info(request, 'Please add a character to get started.')
        return redirect('core:characters')

    # Calculate aggregated stats
    total_wallet = characters.aggregate(
        total=Sum('wallet_balance')
    )['total'] or 0

    total_sp = characters.aggregate(
        total=Sum('total_sp')
    )['total'] or 0

    # Count active skill queues across all characters
    active_skill_queues = sum(
        char.skill_queue.count() for char in characters
    )

    # Count total active market orders
    total_orders = sum(
        char.market_orders.count() for char in characters
    )

    # Calculate aggregated industry slots
    total_manufacturing_slots = sum(char.manufacturing_slots for char in characters)
    total_active_manufacturing = sum(char.active_manufacturing_jobs for char in characters)
    total_science_slots = sum(char.science_slots for char in characters)
    total_active_science = sum(char.active_research_jobs for char in characters)
    total_reaction_slots = sum(char.reaction_slots for char in characters)
    total_active_reactions = sum(char.active_reaction_jobs for char in characters)

    # Calculate utilization percentages
    manufacturing_utilization = (total_active_manufacturing / total_manufacturing_slots * 100) if total_manufacturing_slots > 0 else 0
    science_utilization = (total_active_science / total_science_slots * 100) if total_science_slots > 0 else 0
    reaction_utilization = (total_active_reactions / total_reaction_slots * 100) if total_reaction_slots > 0 else 0

    # Build character data with skill queue info
    characters_data = []
    for char in characters:
        skill_queue = list(char.skill_queue.all())
        current_skill = skill_queue[0] if skill_queue else None
        queue_count = len(skill_queue)

        characters_data.append({
            'character': char,
            'current_skill': current_skill,
            'queue_count': queue_count,
            'orders_count': char.market_orders.count(),
        })

    return render(request, 'core/dashboard.html', {
        'characters': characters_data,
        'total_wallet': total_wallet,
        'total_sp': total_sp,
        'active_skill_queues': active_skill_queues,
        'total_orders': total_orders,
        'characters_count': characters.count(),
        'industry_slots': {
            'manufacturing': {'slots': total_manufacturing_slots, 'active': total_active_manufacturing, 'utilization': manufacturing_utilization},
            'science': {'slots': total_science_slots, 'active': total_active_science, 'utilization': science_utilization},
            'reactions': {'slots': total_reaction_slots, 'active': total_active_reactions, 'utilization': reaction_utilization},
        },
    })


@login_required
def character_detail(request: HttpRequest, character_id: int) -> HttpResponse:
    """Detailed view of a single character."""
    from core.models import Character
    from core.character.models import CharacterSkill
    from core.eve.models import ItemType, ItemGroup
    from collections import defaultdict

    try:
        character = Character.objects.get(id=character_id, user=request.user)
    except Character.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Character not found',
        }, status=404)

    # Pre-filter data that templates can't handle
    root_assets = character.assets.filter(parent__isnull=True)

    # Build skill group summaries
    skill_groups = defaultdict(lambda: {'count': 0, 'total_level': 0, 'max_level': 0})
    for skill in character.skills.all():
        try:
            item_type = ItemType.objects.get(id=skill.skill_id)
            group = None
            if item_type.group_id:
                group = ItemGroup.objects.filter(id=item_type.group_id).first()
            if group:
                skill_groups[group.name]['count'] += 1
                skill_groups[group.name]['total_level'] += skill.skill_level
                skill_groups[group.name]['max_level'] = max(skill_groups[group.name]['max_level'], skill.skill_level)
        except ItemType.DoesNotExist:
            pass

    # Sort by group name and convert to list for template
    skill_groups_list = [
        {'name': name, **data}
        for name, data in sorted(skill_groups.items())
    ]

    return render(request, 'core/character_detail.html', {
        'character': character,
        'root_assets': root_assets,
        'skill_groups': skill_groups_list,
        'total_skill_groups': len(skill_groups_list),
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
        return redirect('core:dashboard')

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


@login_required
@require_http_methods(['GET', 'POST'])
def reauthenticate_character(request: HttpRequest, character_id: int) -> HttpResponse:
    """Re-authenticate a character through EVE SSO (fixes broken tokens/scopes)."""
    from core.models import Character
    from core.services import TokenManager
    from django.contrib import messages

    try:
        character = Character.objects.get(id=character_id, user=request.user)
    except Character.DoesNotExist:
        messages.error(request, 'Character not found.')
        return redirect('core:characters')

    # Store character ID in session for OAuth callback
    request.session['reauth_character_id'] = character.id

    # Generate SSO login URL
    sso_url = TokenManager.get_sso_login_url()
    return redirect(sso_url)

