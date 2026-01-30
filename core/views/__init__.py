"""
Core views for evewire.

Includes authentication, dashboard, and character views.
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


def get_users_character(user):
    """Get user's first-registered character (lowest id).
    Returns None if user has no characters.
    """
    from core.models import Character
    return Character.objects.filter(user=user).order_by('id').first()


def index(request: HttpRequest) -> HttpResponse:
    """Landing page - show login button or redirect to dashboard."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return render(request, 'core/index.html')


@require_http_methods(['GET', 'POST'])
def login_view(request: HttpRequest) -> HttpResponse:
    """Initiate EVE SSO login flow."""
    from core.services import TokenManager

    if request.user.is_authenticated:
        return redirect('core:dashboard')

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
        # Check if this is a re-authentication flow
        reauth_char_id = request.session.pop('reauth_character_id', None)

        # Pass request.user if logged in (for adding character to existing account)
        request_user = request.user if request.user.is_authenticated else None
        status, user = AuthService.handle_callback(code, request_user=request_user, reauth_char_id=reauth_char_id, request=request)

        # Handle different authentication status codes
        if status == AuthService.ACCOUNT_CLAIM_REQUIRED:
            # Character exists on another account with email - show claiming page
            return redirect('core:account_claim')

        elif status == AuthService.SUCCESS_WITH_WARNING:
            # Logged in but account has no email - show warning
            messages.warning(request, 'Your account does not have a verified email. You may lose access if you log out. Consider adding email in settings.')
            if not request_user:
                login(request, user)
            return redirect('core:characters')

        elif status == AuthService.NEW_USER:
            # New user created - log in and show email prompt
            login(request, user)
            return redirect('core:email_prompt')

        # Normal login or character added
        if not request_user:
            login(request, user)

        logger.info(f'User {user.display_name} logged in via SSO')
        return redirect('core:characters')

    except Exception as e:
        logger.error(f'Failed to handle OAuth callback: {e}')
        return render(request, 'core/auth_error.html', {
            'error': 'Authentication failed',
            'error_description': str(e),
        })


@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    """Log out the current user."""
    logger.info(f'User {request.user.display_name} logged out')
    logout(request)
    return redirect('core:index')


def account_claim_page(request: HttpRequest) -> HttpResponse:
    """Show options when character is already linked to another account."""
    from core.models import User
    from django.contrib import messages

    user_id = request.session.get('found_account_user_id')
    if not user_id:
        messages.error(request, 'Account claiming session expired. Please try logging in again.')
        return redirect('core:login')

    try:
        owner_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Account not found.')
        return redirect('core:login')

    if request.method == 'POST':
        choice = request.POST.get('choice')

        if choice == 'send_email':
            # Send magic link to registered email
            from core.email_verification import send_verification_email
            send_verification_email(owner_user, request)
            return render(request, 'core/email_sent.html', {
                'email': owner_user.email,
            })

        elif choice == 'create_new':
            # User opts to create new account - warn them heavily
            # This is a destructive action - they'll lose access to the original account
            request.session['confirm_new_account'] = True
            return render(request, 'core/confirm_new_account.html', {
                'character_id': request.session.get('pending_character_data', {}).get('id'),
                'character_name': request.session.get('pending_character_data', {}).get('name'),
            })

    # Check if this is a confirmation of new account creation
    if request.session.get('confirm_new_account') and request.method == 'POST':
        if request.POST.get('confirm') == 'yes':
            # User confirmed - create new account (WARNING: this creates duplicate character situation)
            # TODO: This should be handled better in the future
            # For now, we'll re-trigger the OAuth flow which will create a new account
            # The original character will still exist in the old account
            request.session.pop('confirm_new_account', None)
            messages.warning(request, 'Creating a new account. The original account still exists - you may want to merge them later.')
            # Redirect to login to start fresh
            return redirect('core:login')

    return render(request, 'core/account_claim.html', {
        'owner_user': owner_user,
        'has_email': bool(owner_user.email),
        'email_masked': f"{owner_user.email[:3]}...{owner_user.email.split('@')[1][-3:]}" if owner_user.email else None,
    })


@login_required
def email_prompt_page(request: HttpRequest) -> HttpResponse:
    """Prompt user to add email for account recovery (optional but encouraged)."""
    from django.contrib import messages
    from django.shortcuts import redirect

    # If user already has an email, redirect to profile page
    if request.user.email:
        messages.info(request, 'You already have an email configured. Remove it first to add a different one.')
        return redirect('core:user_profile')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, 'Please enter a valid email address.')
        else:
            # Check if email is already used by another account
            from core.models import User
            existing_user = User.objects.filter(email=email).exclude(id=request.user.id).first()
            if existing_user:
                messages.error(request, 'This email is already associated with another account.')
            else:
                # Update user's email
                request.user.email = email
                request.user.email_verified = False  # Require verification
                request.user.save()

                # Send verification email
                from core.email_verification import send_verification_email
                send_verification_email(request.user, request)

                return render(request, 'core/email_sent.html', {
                    'email': email,
                })

    return render(request, 'core/email_prompt.html')


def verify_email_login(request: HttpRequest, token: str) -> HttpResponse:
    """Handle magic link from email verification."""
    from django.contrib import messages
    from core.email_verification import verify_email_token

    user = verify_email_token(token)
    if user:
        login(request, user)
        messages.success(request, f'Welcome back, {user.display_name}!')
        logger.info(f'User {user.display_name} logged in via email magic link')
        return redirect('core:dashboard')
    else:
        messages.error(request, 'Invalid or expired login link. Please request a new one.')
        return redirect('core:login')


@login_required
def user_profile(request: HttpRequest) -> HttpResponse:
    """User profile page - show email status and account settings."""
    from django.contrib import messages

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_email':
            email = request.POST.get('email', '').strip()
            from core.models import User

            # Check if email is already used by another account
            existing_user = User.objects.filter(email=email).exclude(id=request.user.id).first()
            if existing_user:
                messages.error(request, 'This email is already associated with another account.')
            else:
                request.user.email = email
                request.user.email_verified = False
                request.user.save()

                # Send verification email
                from core.email_verification import send_verification_email
                send_verification_email(request.user, request)

                messages.success(request, 'Email updated. Please check your inbox for a verification link.')
                return redirect('core:user_profile')

        elif action == 'resend_verification':
            if request.user.email:
                from core.email_verification import send_verification_email
                send_verification_email(request.user, request)
                messages.success(request, 'Verification email sent. Please check your inbox.')
            else:
                messages.error(request, 'No email address configured.')

        elif action == 'remove_email':
            request.user.email = None
            request.user.email_verified = False
            request.user.save()
            messages.success(request, 'Email removed from your account.')

        return redirect('core:user_profile')

    # Mask email for display
    email_masked = None
    if request.user.email:
        email_parts = request.user.email.split('@')
        if len(email_parts) == 2:
            email_masked = f"{email_parts[0][0]}{'*' * (len(email_parts[0]) - 1)}@{email_parts[1]}"

    return render(request, 'core/user_profile.html', {
        'email': request.user.email,
        'email_masked': email_masked,
        'email_verified': request.user.email_verified,
    })


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

    # Count characters with active skill queues (training in progress)
    active_skill_queues = sum(
        1 for char in characters if char.skill_queue.filter(finish_date__gt=timezone.now()).exists()
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

    # Build character data with skill queue info and corporation ticker
    from core.eve.models import Corporation

    characters_data = []
    for char in characters:
        # Get first skill in queue (actively training or next up)
        current_skill = char.skill_queue.order_by('queue_position').first()
        queue_count = char.skill_queue.count()

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

    # Queue location sync for all characters (fast endpoint, can be called frequently)
    from django_q.tasks import async_task
    for char in characters:
        async_task('core.services.sync_character_location', char.id, group='location_sync')


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
def character_overview(request: HttpRequest, character_id: int) -> HttpResponse:
    """Character overview page with quick stats grid."""
    from core.models import Character
    from core.character.models import CharacterSkill, SkillQueueEntry

    try:
        character = Character.objects.get(id=character_id, user=request.user)
    except Character.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Character not found',
        }, status=404)

    # Get currently training skill
    current_skill = character.queue.filter(finish_date__gt=timezone.now()).order_by('finish_date').first()

    # Count assets
    assets_count = character.assets.count()

    # Count fittings that match this character's skills
    fittings_count = 0  # TODO: Implement fitting match logic

    return render(request, 'core/character_overview.html', {
        'character': character,
        'current_skill': current_skill,
        'assets_count': assets_count,
        'fittings_count': fittings_count,
    })


@login_required
def character_skills_page(request: HttpRequest, character_id: int) -> HttpResponse:
    """Character skills page with expandable skill groups."""
    import logging
    from core.models import Character
    from core.eve.models import ItemType, ItemGroup
    from collections import defaultdict

    logger = logging.getLogger('evewire')

    try:
        character = Character.objects.get(id=character_id, user=request.user)
    except Character.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Character not found',
        }, status=404)

    # Get all skills with their item types in one query
    skills = list(character.skills.select_related().all())
    skill_ids = [s.skill_id for s in skills]

    # Bulk fetch all ItemTypes
    item_types = ItemType.objects.filter(id__in=skill_ids)
    item_types_list = list(item_types)

    # Get unique group IDs and bulk fetch ItemGroups
    group_ids = set(it.group_id for it in item_types_list if it.group_id)
    item_groups = ItemGroup.objects.filter(id__in=group_ids)
    item_groups_dict = {g.id: g for g in list(item_groups)}

    # Build a lookup dict for item types
    item_types_dict = {it.id: it for it in item_types_list}

    # Build skill groups
    skill_groups = defaultdict(list)

    for skill in skills:
        item_type = item_types_dict.get(skill.skill_id)
        if item_type and item_type.group_id:
            group = item_groups_dict.get(item_type.group_id)
            if group:
                skill_groups[group.name].append({
                    'skill': skill,
                    'type': item_type,
                    'rank': getattr(item_type, 'rank', 0) or 0,
                })

    # Sort groups and skills within groups
    sorted_groups = []
    for group_name in sorted(skill_groups.keys()):
        skills_list = sorted(skill_groups[group_name], key=lambda x: x['type'].name)
        sorted_groups.append({'name': group_name, 'skills': skills_list})

    return render(request, 'core/character_skills.html', {
        'character': character,
        'skill_groups': sorted_groups,
    })


@login_required
def character_queue_page(request: HttpRequest, character_id: int) -> HttpResponse:
    """Character training queue page with progress visualization."""
    from core.models import Character
    from core.character.models import SkillQueueEntry

    try:
        character = Character.objects.get(id=character_id, user=request.user)
    except Character.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Character not found',
        }, status=404)

    queue_entries = character.queue.filter(finish_date__gt=timezone.now()).order_by('finish_date')

    return render(request, 'core/character_queue.html', {
        'character': character,
        'queue_entries': queue_entries,
    })


@login_required
def character_plans_page(request: HttpRequest, character_id: int) -> HttpResponse:
    """Character skill plans page with progress bars."""
    from core.models import Character
    from core.character.models import SkillPlan

    try:
        character = Character.objects.get(id=character_id, user=request.user)
    except Character.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Character not found',
        }, status=404)

    # Get all plans (user's + global)
    user_plans = SkillPlan.objects.filter(owner=request.user, parent__isnull=True, is_active=True)
    global_plans = SkillPlan.objects.filter(owner__isnull=True, parent__isnull=True, is_active=True)

    # Add progress for each plan
    def enrich_plans(plans):
        enriched = []
        for plan in plans:
            progress = plan.get_progress_for_character(character)
            enriched.append({
                'plan': plan,
                'progress': progress,
            })
        return enriched

    return render(request, 'core/character_plans.html', {
        'character': character,
        'user_plans': enrich_plans(user_plans),
        'global_plans': enrich_plans(global_plans),
    })


@login_required
@require_http_methods(['POST'])
def toggle_theme(request: HttpRequest) -> HttpResponse:
    """Set theme directly or cycle through themes if no theme specified.

    POST parameters:
    - theme: Optional specific theme ('light', 'dark', 'solarized-light', 'solarized-dark')
    If no theme is provided, cycles to next theme.
    """
    from django.contrib import messages

    themes = ['light', 'dark', 'solarized-light', 'solarized-dark']
    user_settings = request.user.settings or {}
    current_theme = user_settings.get('theme', 'light')

    # Check if a specific theme was requested
    requested_theme = request.POST.get('theme')

    if requested_theme and requested_theme in themes:
        new_theme = requested_theme
    else:
        # Cycle to next theme (backwards compatible)
        try:
            current_index = themes.index(current_theme)
            new_theme = themes[(current_index + 1) % len(themes)]
        except ValueError:
            new_theme = 'light'

    # Ensure settings dict exists before assignment
    if request.user.settings is None:
        request.user.settings = {}
    request.user.settings['theme'] = new_theme
    request.user.save(update_fields=['settings'])

    # Friendly theme names
    theme_names = {
        'light': 'Light',
        'dark': 'Dark',
        'solarized-light': 'Solarized Light',
        'solarized-dark': 'Solarized Dark',
    }

    messages.success(request, f'Theme changed to {theme_names.get(new_theme, new_theme)}.')
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect(reverse('core:dashboard'))


@login_required
@require_http_methods(['POST'])
def sync_character(request: HttpRequest, character_id: int) -> HttpResponse:
    """Trigger a manual sync of character data from ESI."""
    from core.models import Character
    from django.contrib import messages
    from django_q.tasks import async_task

    logger.info(f'=== SYNC CHARACTER VIEW CALLED === character_id={character_id}, user={request.user}, method={request.method}')

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
        async_task('core.services.sync_character_data', character.id)
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


# Re-export views from split modules
from core.views.views_skills import *
from core.views.views_econ import *
from core.views.views_assets import *
from core.views.views_characters import *
from core.views.views_exports import *
from core.views.views_fittings import *

# API views (not re-exported, accessed via core.views.api)
from core.views import api
