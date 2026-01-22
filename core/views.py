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
from django.db import models

logger = logging.getLogger('evewire')


def get_users_character(user):
    """Get user's character (first character if multiple).
    Returns None if user has no characters.
    """
    from core.models import Character
    return Character.objects.filter(user=user).first()


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
        user = AuthService.handle_callback(code, request_user=request_user, reauth_char_id=reauth_char_id)

        # If not already logged in, login the user
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

    # Pre-filter data that templates can't handle
    root_assets = character.assets.filter(parent__isnull=True)

    return render(request, 'core/character_detail.html', {
        'character': character,
        'root_assets': root_assets,
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


# Skill Plan Views

@login_required
def skill_plan_list(request: HttpRequest) -> HttpResponse:
    """List all skill plans for the current user plus reference plans."""
    from core.character.models import SkillPlan

    user_plans = SkillPlan.objects.filter(owner=request.user, parent__isnull=True, is_reference=False)
    reference_plans = SkillPlan.objects.filter(parent__isnull=True, is_reference=True)

    return render(request, 'core/skill_plan_list.html', {
        'user_plans': user_plans,
        'reference_plans': reference_plans,
    })


@login_required
def skill_plan_detail(request: HttpRequest, plan_id: int) -> HttpResponse:
    """Show a single skill plan with progress for the user's character."""
    from core.character.models import SkillPlan
    from core.models import Character

    try:
        plan = SkillPlan.objects.get(id=plan_id)
    except SkillPlan.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Skill plan not found',
        }, status=404)

    # Get user's character
    character = get_users_character(request.user)

    # Get progress if character exists
    progress = None
    character_skills = {}
    if character:
        progress = plan.get_progress_for_character(character)
        character_skills = {s.skill_id: s for s in character.skills.all()}

    # Get entries with character skill status
    entries = []
    for entry in plan.entries.all():
        skill = character_skills.get(entry.skill_id)
        status = 'unknown'
        current_level = 0

        if skill:
            current_level = skill.skill_level
            if entry.level and current_level >= entry.level:
                status = 'completed'
            elif entry.recommended_level and current_level >= entry.recommended_level:
                status = 'recommended'
            elif current_level > 0:
                status = 'in_progress'
            else:
                status = 'not_started'
        elif entry.level:
            status = 'not_started'

        entries.append({
            'entry': entry,
            'current_level': current_level,
            'status': status,
        })

    return render(request, 'core/skill_plan_detail.html', {
        'plan': plan,
        'entries': entries,
        'progress': progress,
        'character': character,
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
def skills_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """List skills grouped by category, for a specific character."""
    from core.character.models import CharacterSkill
    from core.eve.models import ItemType, ItemGroup
    from core.models import Character

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

    # Get all skills for this character
    skills_qs = CharacterSkill.objects.filter(character=character).select_related()

    # Build a list of all skills with group info
    skills_with_groups = []
    group_ids_seen = set()

    for skill in skills_qs:
        try:
            item_type = ItemType.objects.get(id=skill.skill_id)
            group = None
            if item_type.group_id:
                group = ItemGroup.objects.filter(id=item_type.group_id).first()
                if group:
                    group_ids_seen.add(group.id)

            skills_with_groups.append({
                'skill': skill,
                'name': item_type.name,
                'group': group,
                'level_stars': '★' * skill.skill_level + '☆' * (5 - skill.skill_level),
                'group_id': item_type.group_id,
                'group_name': group.name if group else 'Unknown',
            })
        except ItemType.DoesNotExist:
            skills_with_groups.append({
                'skill': skill,
                'name': f'Skill {skill.skill_id}',
                'group': None,
                'level_stars': '★' * skill.skill_level + '☆' * (5 - skill.skill_level),
                'group_id': None,
                'group_name': 'Unknown',
            })

    # Sort by group name, then skill name
    skills_with_groups.sort(key=lambda x: (x['group_name'], x['name']))

    # Group by group_name for template
    from collections import defaultdict
    grouped = defaultdict(list)
    for s in skills_with_groups:
        grouped[s['group_name']].append(s)

    return render(request, 'core/skills_list.html', {
        'character': character,
        'skills': skills_with_groups,
        'grouped_skills': dict(grouped),
        'total_skills': skills_qs.count(),
        'total_sp': character.total_sp or 0,
        'total_groups': len(grouped),
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


# Wallet Views

@login_required
def wallet_journal(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View wallet journal entries with pagination and filtering."""
    from core.models import Character
    from core.character.models import WalletJournalEntry
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from datetime import datetime, timedelta

    # Get character - either specified or user's character
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

    # Get filter parameters
    ref_type_filter = request.GET.get('ref_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Build queryset
    entries_qs = WalletJournalEntry.objects.filter(character=character)

    # Apply ref_type filter
    if ref_type_filter:
        entries_qs = entries_qs.filter(ref_type=ref_type_filter)

    # Apply date range filter
    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            entries_qs = entries_qs.filter(date__gte=date_from_dt)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
            # Include the entire end date
            date_to_dt = date_to_dt + timedelta(days=1)
            entries_qs = entries_qs.filter(date__lt=date_to_dt)
        except ValueError:
            pass

    # Get distinct ref_types for filter dropdown
    all_ref_types = WalletJournalEntry.objects.filter(
        character=character
    ).values_list('ref_type', flat=True).distinct().order_by('ref_type')

    # Pagination
    page = request.GET.get('page', 1)
    per_page = 50
    paginator = Paginator(entries_qs, per_page)

    try:
        entries = paginator.page(page)
    except PageNotAnInteger:
        entries = paginator.page(1)
    except EmptyPage:
        entries = paginator.page(paginator.num_pages)

    # Get current balance from latest entry
    current_balance = entries_qs.order_by('-date').first()
    if current_balance:
        current_balance = current_balance.balance
    else:
        current_balance = character.wallet_balance

    return render(request, 'core/wallet_journal.html', {
        'character': character,
        'entries': entries,
        'ref_types': all_ref_types,
        'ref_type_filter': ref_type_filter,
        'date_from': date_from,
        'date_to': date_to,
        'current_balance': current_balance,
    })


@login_required
def wallet_transactions(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View wallet transaction history."""
    from core.models import Character
    from core.character.models import WalletTransaction
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from datetime import datetime, timedelta

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

    # Get filter parameters
    buy_sell_filter = request.GET.get('type', '')  # 'buy', 'sell', or ''
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Build queryset
    transactions_qs = WalletTransaction.objects.filter(character=character)

    # Apply buy/sell filter
    if buy_sell_filter == 'buy':
        transactions_qs = transactions_qs.filter(is_buy=True)
    elif buy_sell_filter == 'sell':
        transactions_qs = transactions_qs.filter(is_buy=False)

    # Apply date range filter
    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            transactions_qs = transactions_qs.filter(date__gte=date_from_dt)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_dt = date_to_dt + timedelta(days=1)
            transactions_qs = transactions_qs.filter(date__lt=date_to_dt)
        except ValueError:
            pass

    # Pagination
    page = request.GET.get('page', 1)
    per_page = 50
    paginator = Paginator(transactions_qs, per_page)

    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)

    return render(request, 'core/wallet_transactions.html', {
        'character': character,
        'transactions': transactions,
        'buy_sell_filter': buy_sell_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def wallet_balance(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View wallet balance history and statistics."""
    from core.models import Character
    from core.character.models import WalletJournalEntry
    from django.db.models import Max, Min, Sum, Count
    from django.db.models.functions import TruncDate
    from datetime import datetime, timedelta
    from collections import defaultdict
    import json

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

    # Get current balance from latest journal entry or character field
    latest_entry = WalletJournalEntry.objects.filter(
        character=character
    ).order_by('-date').first()

    current_balance = latest_entry.balance if latest_entry else character.wallet_balance

    # Get balance history for the last 30 days (for chart)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    balance_history = WalletJournalEntry.objects.filter(
        character=character,
        date__gte=thirty_days_ago
    ).order_by('date')

    # Get daily balance snapshots
    daily_balances = []
    if balance_history.exists():
        # Group by date and get the last balance entry for each day
        date_balances = defaultdict(list)
        for entry in balance_history:
            date_key = entry.date.date()
            date_balances[date_key].append(entry.balance)

        # Take the last balance of each day
        for date, balances in sorted(date_balances.items()):
            daily_balances.append({
                'date': date.isoformat(),
                'balance': float(balances[-1]) if balances else 0,
            })

    # Calculate statistics
    all_entries = WalletJournalEntry.objects.filter(character=character)

    # Get date range of available data
    date_range = all_entries.aggregate(
        earliest=Min('date'),
        latest=Max('date')
    )

    # Calculate 24h and 7d changes
    now = timezone.now()
    one_day_ago = now - timedelta(days=1)
    seven_days_ago = now - timedelta(days=7)

    # Get balance at different time points
    balance_24h_ago = all_entries.filter(date__lte=one_day_ago).order_by('-date').first()
    balance_7d_ago = all_entries.filter(date__lte=seven_days_ago).order_by('-date').first()

    balance_24h = balance_24h_ago.balance if balance_24h_ago else 0
    balance_7d = balance_7d_ago.balance if balance_7d_ago else 0

    change_24h = float(current_balance or 0) - float(balance_24h)
    change_7d = float(current_balance or 0) - float(balance_7d)
    percent_24h = (change_24h / float(balance_24h) * 100) if balance_24h else 0
    percent_7d = (change_7d / float(balance_7d) * 100) if balance_7d else 0

    return render(request, 'core/wallet_balance.html', {
        'character': character,
        'current_balance': float(current_balance or 0),
        'balance_history_json': json.dumps(daily_balances),
        'change_24h': change_24h,
        'change_7d': change_7d,
        'percent_24h': percent_24h,
        'percent_7d': percent_7d,
        'date_from': date_range['earliest'],
        'date_to': date_range['latest'],
    })


@login_required
def wallet_summary(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View income/expense summary aggregated by ref_type."""
    from core.models import Character
    from core.character.models import WalletJournalEntry
    from django.db.models import Sum, Count
    from datetime import datetime, timedelta
    from collections import defaultdict
    from django.utils import timezone

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

    # Get time range parameters (default to last 30 days)
    days = request.GET.get('days', '30')
    try:
        days = int(days)
    except ValueError:
        days = 30

    since = timezone.now() - timedelta(days=days)

    # Aggregate by ref_type
    summary = WalletJournalEntry.objects.filter(
        character=character,
        date__gte=since
    ).values('ref_type').annotate(
        total_income=Sum('amount', filter=models.Q(amount__gt=0)),
        total_expense=Sum('amount', filter=models.Q(amount__lt=0)),
        entry_count=Count('entry_id')
    ).order_by('-total_income')

    # Calculate totals
    income_total = 0
    expense_total = 0
    grand_total = 0

    for item in summary:
        income = float(item['total_income'] or 0)
        expense = abs(float(item['total_expense'] or 0))
        item['income'] = income
        item['expense'] = expense
        item['net'] = income - expense
        income_total += income
        expense_total += expense

    grand_total = income_total - expense_total

    # Get top transaction types by volume
    top_by_income = sorted(summary, key=lambda x: x['income'], reverse=True)[:5]
    top_by_expense = sorted(summary, key=lambda x: x['expense'], reverse=True)[:5]

    return render(request, 'core/wallet_summary.html', {
        'character': character,
        'summary': summary,
        'income_total': income_total,
        'expense_total': expense_total,
        'grand_total': grand_total,
        'days': days,
        'top_by_income': top_by_income,
        'top_by_expense': top_by_expense,
    })


# Market Orders Views

@login_required
def market_orders(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View market orders with filtering and pagination."""
    from core.models import Character
    from core.character.models import MarketOrder
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    # Get character - either specified or user's character
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

    # Get filter parameters
    order_type = request.GET.get('type', '')  # 'buy', 'sell', or ''
    state_filter = request.GET.get('state', '')  # 'open', 'closed', 'expired', 'cancelled', ''

    # Build queryset
    orders_qs = MarketOrder.objects.filter(character=character)

    # Apply buy/sell filter
    if order_type == 'buy':
        orders_qs = orders_qs.filter(is_buy_order=True)
    elif order_type == 'sell':
        orders_qs = orders_qs.filter(is_buy_order=False)

    # Apply state filter
    if state_filter:
        orders_qs = orders_qs.filter(state=state_filter)

    # Order by issued date (newest first)
    orders_qs = orders_qs.order_by('-issued')

    # Pagination
    page = request.GET.get('page', 1)
    per_page = 50
    paginator = Paginator(orders_qs, per_page)

    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    # Calculate order totals
    buy_total = MarketOrder.objects.filter(
        character=character, is_buy_order=True, state='open'
    ).count()
    sell_total = MarketOrder.objects.filter(
        character=character, is_buy_order=False, state='open'
    ).count()

    return render(request, 'core/market_orders.html', {
        'character': character,
        'orders': orders,
        'order_type': order_type,
        'state_filter': state_filter,
        'buy_total': buy_total,
        'sell_total': sell_total,
    })


@login_required
def market_orders_history(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View historical market orders (closed, expired, cancelled) with filtering and pagination."""
    from core.models import Character
    from core.character.models import MarketOrderHistory
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    # Get character - either specified or user's character
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

    # Get filter parameters
    order_type = request.GET.get('type', '')  # 'buy', 'sell', or ''
    state_filter = request.GET.get('state', '')  # 'closed', 'expired', 'cancelled', ''

    # Build queryset
    orders_qs = MarketOrderHistory.objects.filter(character=character)

    # Apply buy/sell filter
    if order_type == 'buy':
        orders_qs = orders_qs.filter(is_buy_order=True)
    elif order_type == 'sell':
        orders_qs = orders_qs.filter(is_buy_order=False)

    # Apply state filter
    if state_filter:
        orders_qs = orders_qs.filter(state=state_filter)

    # Order by issued date (newest first)
    orders_qs = orders_qs.order_by('-issued')

    # Pagination
    page = request.GET.get('page', 1)
    per_page = 50
    paginator = Paginator(orders_qs, per_page)

    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    return render(request, 'core/market_orders_history.html', {
        'character': character,
        'orders': orders,
        'order_type': order_type,
        'state_filter': state_filter,
    })


# Trade Analysis Views

@login_required
def trade_overview(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """Trade overview showing profit/loss summary and top items."""
    from core.models import Character
    from core.trade.services import TradeAnalyzer
    from core.trade.models import Campaign
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

    # Get timeframe filter
    timeframe = request.GET.get('timeframe', 'all')
    campaign_id = request.GET.get('campaign')
    year = request.GET.get('year')
    month = request.GET.get('month')

    summaries = []
    start_date = None
    end_date = None
    timeframe_label = "All Time"

    if campaign_id:
        # Use campaign date range
        try:
            campaign = Campaign.objects.get(id=campaign_id, user=request.user)
            summaries = TradeAnalyzer.analyze_campaign(campaign)
            start_date = campaign.start_date
            end_date = campaign.end_date
            timeframe_label = campaign.title
        except Campaign.DoesNotExist:
            pass
    elif year and month:
        # Use specific month
        start_date = timezone.datetime(int(year), int(month), 1).replace(tzinfo=timezone.utc)
        if int(month) == 12:
            end_date = timezone.datetime(int(year) + 1, 1, 1).replace(tzinfo=timezone.utc) - timedelta(seconds=1)
        else:
            end_date = timezone.datetime(int(year), int(month) + 1, 1).replace(tzinfo=timezone.utc) - timedelta(seconds=1)
        summaries = TradeAnalyzer.analyze_timeframe(character, start_date, end_date)
        timeframe_label = f"{year}-{month.zfill(2)}"
    elif timeframe == '30d':
        start_date = timezone.now() - timedelta(days=30)
        end_date = timezone.now()
        summaries = TradeAnalyzer.analyze_timeframe(character, start_date, end_date)
        timeframe_label = "Last 30 Days"
    elif timeframe == '90d':
        start_date = timezone.now() - timedelta(days=90)
        end_date = timezone.now()
        summaries = TradeAnalyzer.analyze_timeframe(character, start_date, end_date)
        timeframe_label = "Last 90 Days"
    elif timeframe == '12m':
        start_date = timezone.now() - timedelta(days=365)
        end_date = timezone.now()
        summaries = TradeAnalyzer.analyze_timeframe(character, start_date, end_date)
        timeframe_label = "Last 12 Months"
    else:
        # All time - use overview stats for efficiency
        stats = TradeAnalyzer.get_overview_stats(character)
        summaries = TradeAnalyzer.analyze_timeframe(
            character,
            start_date=timezone.datetime(2000, 1, 1).replace(tzinfo=timezone.utc),
            end_date=timezone.now()
        )

    # Calculate overview stats
    total_buy = sum(s.buy_total for s in summaries)
    total_sell = sum(s.sell_total for s in summaries)
    net_balance = total_sell - total_buy

    # Get top items
    top_profitable = [s for s in summaries if s.balance > 0][:10]
    top_losses = [s for s in summaries if s.balance < 0][:10]
    top_volume = sorted(summaries, key=lambda x: x.buy_total + x.sell_total, reverse=True)[:10]

    # Get available campaigns and months
    campaigns = Campaign.objects.filter(user=request.user).order_by('-start_date')
    monthly_summaries = TradeAnalyzer.get_monthly_summaries(character)

    return render(request, 'core/trade_overview.html', {
        'character': character,
        'summaries': summaries,
        'total_buy': total_buy,
        'total_sell': total_sell,
        'net_balance': net_balance,
        'top_profitable': top_profitable,
        'top_losses': top_losses,
        'top_volume': top_volume,
        'campaigns': campaigns,
        'monthly_summaries': monthly_summaries,
        'timeframe': timeframe,
        'timeframe_label': timeframe_label,
        'campaign_id': campaign_id,
    })


@login_required
def trade_item_detail(request: HttpRequest, character_id: int, type_id: int) -> HttpResponse:
    """Detailed view for a single item's trading history."""
    from core.models import Character
    from core.character.models import WalletTransaction
    from core.eve.models import ItemType
    from django.utils import timezone
    from datetime import timedelta

    # Get character
    try:
        character = Character.objects.get(id=character_id, user=request.user)
    except Character.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Character not found',
        }, status=404)

    # Get timeframe filter
    timeframe = request.GET.get('timeframe', 'all')
    campaign_id = request.GET.get('campaign')
    year = request.GET.get('year')
    month = request.GET.get('month')

    # Build date range
    if campaign_id:
        from core.trade.models import Campaign
        try:
            campaign = Campaign.objects.get(id=campaign_id, user=request.user)
            start_date = campaign.start_date
            end_date = campaign.end_date
        except Campaign.DoesNotExist:
            start_date = None
            end_date = None
    elif year and month:
        start_date = timezone.datetime(int(year), int(month), 1).replace(tzinfo=timezone.utc)
        if int(month) == 12:
            end_date = timezone.datetime(int(year) + 1, 1, 1).replace(tzinfo=timezone.utc) - timedelta(seconds=1)
        else:
            end_date = timezone.datetime(int(year), int(month) + 1, 1).replace(tzinfo=timezone.utc) - timedelta(seconds=1)
    elif timeframe == '30d':
        start_date = timezone.now() - timedelta(days=30)
        end_date = timezone.now()
    elif timeframe == '90d':
        start_date = timezone.now() - timedelta(days=90)
        end_date = timezone.now()
    elif timeframe == '12m':
        start_date = timezone.now() - timedelta(days=365)
        end_date = timezone.now()
    else:
        start_date = None
        end_date = None

    # Get transactions for this item
    transactions = WalletTransaction.objects.filter(
        character=character,
        type_id=type_id
    )

    if start_date and end_date:
        transactions = transactions.filter(date__range=(start_date, end_date))

    transactions = transactions.order_by('-date')

    # Calculate statistics
    buys = transactions.filter(is_buy=True)
    sells = transactions.filter(is_buy=False)

    buy_count = buys.count()
    sell_count = sells.count()

    buy_quantity = sum(t.quantity for t in buys)
    sell_quantity = sum(t.quantity for t in sells)

    buy_total = sum(t.quantity * t.unit_price for t in buys)
    sell_total = sum(t.quantity * t.unit_price for t in sells)

    buy_avg = buy_total / buy_quantity if buy_quantity > 0 else 0
    sell_avg = sell_total / sell_quantity if sell_quantity > 0 else 0

    balance = sell_total - buy_total
    diff = buy_quantity - sell_quantity  # Unsold stock

    profit_per_unit = sell_avg - buy_avg
    profit_pct = (profit_per_unit / buy_avg * 100) if buy_avg > 0 else 0
    projected = balance + (diff * sell_avg)

    # Get item info
    try:
        item = ItemType.objects.get(id=type_id)
        item_name = item.name
    except ItemType.DoesNotExist:
        item_name = f"Type {type_id}"

    return render(request, 'core/trade_item_detail.html', {
        'character': character,
        'type_id': type_id,
        'item_name': item_name,
        'transactions': transactions,
        'buy_count': buy_count,
        'sell_count': sell_count,
        'buy_quantity': buy_quantity,
        'sell_quantity': sell_quantity,
        'buy_total': buy_total,
        'sell_total': sell_total,
        'buy_avg': buy_avg,
        'sell_avg': sell_avg,
        'balance': balance,
        'diff': diff,
        'profit_per_unit': profit_per_unit,
        'profit_pct': profit_pct,
        'projected': projected,
        'timeframe': timeframe,
        'campaign_id': campaign_id,
    })


# Trade Campaign CRUD Views

@login_required
def campaign_list(request: HttpRequest) -> HttpResponse:
    """List all trade campaigns for the current user."""
    from core.trade.models import Campaign

    campaigns = Campaign.objects.filter(user=request.user).order_by('-start_date')

    return render(request, 'core/campaign_list.html', {
        'campaigns': campaigns,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def campaign_create(request: HttpRequest) -> HttpResponse:
    """Create a new trade campaign."""
    from core.trade.models import Campaign
    from core.models import Character
    from django.contrib import messages

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        character_ids = request.POST.getlist('characters')

        if not title or not start_date or not end_date:
            messages.error(request, 'Title, start date, and end date are required.')
            return render(request, 'core/campaign_form.html', {
                'characters': Character.objects.filter(user=request.user),
            })

        from django.utils.dateparse import parse_datetime
        try:
            start = parse_datetime(start_date)
            end = parse_datetime(end_date)
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return render(request, 'core/campaign_form.html', {
                'characters': Character.objects.filter(user=request.user),
            })

        # Generate slug from title
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')

        campaign = Campaign.objects.create(
            user=request.user,
            title=title,
            slug=slug,
            description=description,
            start_date=start,
            end_date=end,
        )

        # Add characters if specified
        if character_ids:
            campaign.characters.set(character_ids)

        messages.success(request, f'Campaign "{title}" created successfully.')
        return redirect('core:campaign_detail', campaign_id=campaign.id)

    return render(request, 'core/campaign_form.html', {
        'characters': Character.objects.filter(user=request.user),
    })


@login_required
def campaign_detail(request: HttpRequest, campaign_id: int) -> HttpResponse:
    """View a single campaign with details."""
    from core.trade.models import Campaign

    try:
        campaign = Campaign.objects.get(id=campaign_id, user=request.user)
    except Campaign.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Campaign not found.',
        }, status=404)

    return render(request, 'core/campaign_detail.html', {
        'campaign': campaign,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def campaign_edit(request: HttpRequest, campaign_id: int) -> HttpResponse:
    """Edit an existing campaign."""
    from core.trade.models import Campaign
    from core.models import Character
    from django.contrib import messages

    try:
        campaign = Campaign.objects.get(id=campaign_id, user=request.user)
    except Campaign.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Campaign not found.',
        }, status=404)

    if request.method == 'POST':
        campaign.title = request.POST.get('title', campaign.title)
        campaign.description = request.POST.get('description', '')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        character_ids = request.POST.getlist('characters')

        from django.utils.dateparse import parse_datetime
        if start_date:
            try:
                campaign.start_date = parse_datetime(start_date)
            except ValueError:
                pass

        if end_date:
            try:
                campaign.end_date = parse_datetime(end_date)
            except ValueError:
                pass

        campaign.save()

        if character_ids:
            campaign.characters.set(character_ids)
        else:
            campaign.characters.clear()

        messages.success(request, f'Campaign "{campaign.title}" updated successfully.')
        return redirect('core:campaign_detail', campaign_id=campaign.id)

    return render(request, 'core/campaign_form.html', {
        'campaign': campaign,
        'characters': Character.objects.filter(user=request.user),
        'selected_characters': list(campaign.characters.values_list('id', flat=True)),
    })


@login_required
@require_http_methods(['POST'])
def campaign_delete(request: HttpRequest, campaign_id: int) -> HttpResponse:
    """Delete a campaign."""
    from core.trade.models import Campaign
    from django.contrib import messages

    try:
        campaign = Campaign.objects.get(id=campaign_id, user=request.user)
    except Campaign.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Campaign not found.',
        }, status=404)

    title = campaign.title
    campaign.delete()
    messages.success(request, f'Campaign "{title}" deleted successfully.')
    return redirect('core:campaign_list')


# Contracts Views

@login_required
def contracts_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View contracts with filtering and pagination."""
    from core.models import Character
    from core.character.models import Contract
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    # Get character - either specified or user's character
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

    # Get filter parameters
    contract_type = request.GET.get('type', '')  # 'item_exchange', 'auction', 'courier', 'loan', or ''
    status_filter = request.GET.get('status', '')  # 'outstanding', 'in_progress', etc.
    availability_filter = request.GET.get('availability', '')  # 'public', 'personal', 'corporation', 'alliance'

    # Build queryset
    contracts_qs = Contract.objects.filter(character=character)

    # Apply type filter
    if contract_type:
        contracts_qs = contracts_qs.filter(type=contract_type)

    # Apply status filter
    if status_filter:
        contracts_qs = contracts_qs.filter(status=status_filter)

    # Apply availability filter
    if availability_filter:
        contracts_qs = contracts_qs.filter(availability=availability_filter)

    # Order by issued date (newest first)
    contracts_qs = contracts_qs.order_by('-date_issued')

    # Pagination
    page = request.GET.get('page', 1)
    per_page = 50
    paginator = Paginator(contracts_qs, per_page)

    try:
        contracts = paginator.page(page)
    except PageNotAnInteger:
        contracts = paginator.page(1)
    except EmptyPage:
        contracts = paginator.page(paginator.num_pages)

    # Calculate contract counts by status
    outstanding_count = Contract.objects.filter(
        character=character, status='outstanding'
    ).count()
    in_progress_count = Contract.objects.filter(
        character=character, status='in_progress'
    ).count()
    completed_count = Contract.objects.filter(
        character=character, status__in=('finished_issuer', 'finished_contractor', 'finished')
    ).count()

    return render(request, 'core/contracts.html', {
        'character': character,
        'contracts': contracts,
        'contract_type': contract_type,
        'status_filter': status_filter,
        'availability_filter': availability_filter,
        'outstanding_count': outstanding_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
    })


# Asset Views

@login_required
def assets_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View character assets with hierarchical tree display."""
    from core.models import Character
    from core.character.models import CharacterAsset
    from core.eve.models import ItemType
    from collections import defaultdict

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

    # Get all assets for this character
    all_assets = CharacterAsset.objects.filter(character=character).select_related()

    # Build asset lookup map
    asset_map = {asset.item_id: asset for asset in all_assets}

    # Get top-level assets (no parent) and build hierarchy
    root_assets = []
    location_groups = defaultdict(list)

    for asset in all_assets:
        if not asset.parent_id:
            # Top-level asset
            location_key = (asset.location_id, asset.location_type)
            location_groups[location_key].append(asset)
        else:
            # Child asset - will be rendered via parent's descendants
            pass

    # Sort locations by name
    sorted_locations = sorted(
        location_groups.items(),
        key=lambda x: x[0][1] + str(x[0][0])  # Sort by location_type then location_id
    )

    return render(request, 'core/assets_list.html', {
        'character': character,
        'location_groups': sorted_locations,
        'total_assets': all_assets.count(),
    })


@login_required
def assets_summary(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View asset summary with per-location aggregates."""
    from core.models import Character
    from core.character.models import CharacterAsset
    from core.eve.models import ItemType
    from django.db.models import Sum, Count, Q
    from collections import defaultdict
    from decimal import Decimal

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

    # Get top-level assets only (no parent) to avoid double-counting nested items
    assets_qs = CharacterAsset.objects.filter(
        character=character,
        parent=None
    ).select_related('type')

    # Aggregate by location
    location_data = defaultdict(lambda: {
        'total_items': 0,
        'total_quantity': 0,
        'total_volume': Decimal('0.0'),
        'total_value': Decimal('0.0'),
    })

    for asset in assets_qs:
        key = (asset.location_type, asset.location_id)
        item_type = asset.type

        # Count each asset item (including quantity)
        quantity = asset.quantity
        location_data[key]['total_items'] += 1
        location_data[key]['total_quantity'] += quantity

        # Calculate volume (item volume * quantity)
        if item_type and item_type.volume:
            location_data[key]['total_volume'] += Decimal(str(item_type.volume)) * quantity

        # Calculate value (use sell_price if available, otherwise base_price)
        price = item_type.sell_price if item_type and item_type.sell_price else (item_type.base_price if item_type else None)
        if price:
            location_data[key]['total_value'] += price * quantity

    # Build location list with names
    locations = []
    for (loc_type, loc_id), data in sorted(location_data.items()):
        # Get location name
        if loc_type == 'station':
            from core.eve.models import Station
            try:
                loc_name = Station.objects.get(id=loc_id).name
            except Station.DoesNotExist:
                loc_name = f"Station {loc_id}"
        elif loc_type == 'solar_system':
            from core.eve.models import SolarSystem
            try:
                loc_name = SolarSystem.objects.get(id=loc_id).name
            except SolarSystem.DoesNotExist:
                loc_name = f"System {loc_id}"
        elif loc_type == 'structure':
            loc_name = f"Structure {loc_id}"
        else:
            loc_name = f"{loc_type.title()} {loc_id}"

        locations.append({
            'location_type': loc_type,
            'location_id': loc_id,
            'location_name': loc_name,
            'total_items': data['total_items'],
            'total_volume': data['total_volume'],
            'total_value': data['total_value'],
        })

    # Calculate overall totals
    total_items = sum(loc['total_items'] for loc in locations)
    total_value = sum(loc['total_value'] for loc in locations)
    total_volume = sum(loc['total_volume'] for loc in locations)

    return render(request, 'core/assets_summary.html', {
        'character': character,
        'locations': locations,
        'total_items': total_items,
        'total_value': total_value,
        'total_volume': total_volume,
    })


@login_required
def contract_detail(request: HttpRequest, contract_id: int) -> HttpResponse:
    """View a single contract with its items."""
    from core.models import Character
    from core.character.models import Contract, ContractItem

    try:
        contract = Contract.objects.get(contract_id=contract_id)
    except Contract.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Contract not found',
        }, status=404)

    # Verify ownership
    if contract.character.user != request.user:
        return render(request, 'core/error.html', {
            'message': 'Access denied',
        }, status=403)

    # Get contract items
    items = contract.items.all()

    # Calculate item statistics
    included_items = [item for item in items if item.is_included]
    requested_items = [item for item in items if not item.is_included]

    return render(request, 'core/contract_detail.html', {
        'contract': contract,
        'items': items,
        'included_items': included_items,
        'requested_items': requested_items,
    })


@login_required
def fitted_ships(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View fitted ships extracted from assets."""
    from core.models import Character
    from core.doctrines.services import AssetFitExtractor
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
        character = get_users_character(request.user)
        if not character:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)

    # Extract fitted ships
    extractor = AssetFitExtractor()
    ships = extractor.extract_ships(character)

    # Enrich with item names and location details
    enriched_ships = []
    for ship in ships:
        # Get module names
        high_module_names = []
        for type_id in ship.high_slots:
            try:
                high_module_names.append(ItemType.objects.get(id=type_id).name)
            except ItemType.DoesNotExist:
                high_module_names.append(f"Module {type_id}")

        med_module_names = []
        for type_id in ship.med_slots:
            try:
                med_module_names.append(ItemType.objects.get(id=type_id).name)
            except ItemType.DoesNotExist:
                med_module_names.append(f"Module {type_id}")

        low_module_names = []
        for type_id in ship.low_slots:
            try:
                low_module_names.append(ItemType.objects.get(id=type_id).name)
            except ItemType.DoesNotExist:
                low_module_names.append(f"Module {type_id}")

        rig_module_names = []
        for type_id in ship.rig_slots:
            try:
                rig_module_names.append(ItemType.objects.get(id=type_id).name)
            except ItemType.DoesNotExist:
                rig_module_names.append(f"Module {type_id}")

        # Get location name
        location_name = f"{ship.location_type.title()} {ship.location_id}"
        if ship.location_type == 'station':
            try:
                from core.eve.models import Station
                location_name = Station.objects.get(id=ship.location_id).name
            except Station.DoesNotExist:
                pass
        elif ship.location_type == 'solar_system':
            try:
                from core.eve.models import SolarSystem
                location_name = SolarSystem.objects.get(id=ship.location_id).name
            except SolarSystem.DoesNotExist:
                pass

        enriched_ships.append({
            'asset_id': ship.asset_id,
            'ship_name': ship.ship_name,
            'ship_type_id': ship.ship_type_id,
            'location_name': location_name,
            'location_type': ship.location_type,
            'high_slots': ship.high_slots,
            'high_slot_names': high_module_names,
            'high_slot_count': len(ship.high_slots),
            'med_slots': ship.med_slots,
            'med_slot_names': med_module_names,
            'med_slot_count': len(ship.med_slots),
            'low_slots': ship.low_slots,
            'low_slot_names': low_module_names,
            'low_slot_count': len(ship.low_slots),
            'rig_slots': ship.rig_slots,
            'rig_slot_names': rig_module_names,
            'rig_slot_count': len(ship.rig_slots),
            'subsystem_slots': ship.subsystem_slots,
            'subsystem_slot_count': len(ship.subsystem_slots),
            'cargo_count': len(ship.cargo),
            'drone_bay_count': len(ship.drone_bay),
            'fighter_bay_count': len(ship.fighter_bay),
        })

    return render(request, 'core/fitted_ships.html', {
        'character': character,
        'ships': enriched_ships,
        'total_ships': len(ships),
    })


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

    return render(request, 'core/industry_summary.html', {
        'character': character,
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


# CSV Export Views

@login_required
def assets_export(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """Export character assets to CSV."""
    from core.models import Character
    from core.character.models import CharacterAsset
    from core.eve.models import ItemType
    import csv

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

    # Get all assets for this character
    assets_qs = CharacterAsset.objects.filter(character=character).select_related('type')

    # Apply filters from query string
    location_type = request.GET.get('location_type', '')
    if location_type:
        assets_qs = assets_qs.filter(location_type=location_type)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f"{character.character_name}_assets.csv"
    filename = filename.replace(' ', '_').replace('/', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Write header
    writer.writerow([
        'Item ID',
        'Item Name',
        'Type ID',
        'Quantity',
        'Location ID',
        'Location Type',
        'Location Flag',
        'Is Singleton',
        'Is Blueprint Copy',
        'Estimated Value (ISK)',
    ])

    # Write data rows
    for asset in assets_qs:
        item_type = asset.type
        item_name = item_type.name if item_type else f"Type {asset.type_id}"

        # Calculate estimated value
        if item_type and item_type.sell_price:
            value = float(item_type.sell_price) * asset.quantity
        elif item_type and item_type.base_price:
            value = float(item_type.base_price) * asset.quantity
        else:
            value = 0.0

        writer.writerow([
            asset.item_id,
            item_name,
            asset.type_id,
            asset.quantity,
            asset.location_id or '',
            asset.location_type,
            asset.location_flag,
            'Yes' if asset.is_singleton else 'No',
            'Yes' if asset.is_blueprint_copy else 'No',
            f'{value:.2f}',
        ])

    return response


@login_required
def contracts_export(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """Export character contracts to CSV."""
    from core.models import Character
    from core.character.models import Contract
    import csv

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

    # Get all contracts for this character
    contracts_qs = Contract.objects.filter(character=character)

    # Apply filters from query string
    contract_type = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    availability_filter = request.GET.get('availability', '')

    if contract_type:
        contracts_qs = contracts_qs.filter(type=contract_type)
    if status_filter:
        contracts_qs = contracts_qs.filter(status=status_filter)
    if availability_filter:
        contracts_qs = contracts_qs.filter(availability=availability_filter)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f"{character.character_name}_contracts.csv"
    filename = filename.replace(' ', '_').replace('/', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Write header
    writer.writerow([
        'Contract ID',
        'Type',
        'Status',
        'Title',
        'Availability',
        'Date Issued',
        'Date Expires',
        'Date Completed',
        'Issuer ID',
        'Assignee ID',
        'Acceptor ID',
        'Price (ISK)',
        'Reward (ISK)',
        'Collateral (ISK)',
        'Buyout (ISK)',
        'Volume (m3)',
        'Items Count',
        'Total Value (ISK)',
    ])

    # Write data rows
    for contract in contracts_qs:
        writer.writerow([
            contract.contract_id,
            contract.type_name,
            contract.status_name,
            contract.title,
            contract.availability_name,
            contract.date_issued.strftime('%Y-%m-%d %H:%M:%S') if contract.date_issued else '',
            contract.date_expired.strftime('%Y-%m-%d %H:%M:%S') if contract.date_expired else '',
            contract.date_completed.strftime('%Y-%m-%d %H:%M:%S') if contract.date_completed else '',
            contract.issuer_id,
            contract.assignee_id or '',
            contract.acceptor_id or '',
            f'{float(contract.price):.2f}' if contract.price else '0.00',
            f'{float(contract.reward):.2f}' if contract.reward else '0.00',
            f'{float(contract.collateral):.2f}' if contract.collateral else '0.00',
            f'{float(contract.buyout):.2f}' if contract.buyout else '0.00',
            f'{contract.volume:.2f}' if contract.volume else '0.00',
            contract.items_count,
            f'{contract.total_value:.2f}',
        ])

    return response


@login_required
def industry_jobs_export(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """Export character industry jobs to CSV."""
    from core.models import Character
    from core.character.models import IndustryJob
    import csv

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

    # Get all industry jobs for this character
    jobs_qs = IndustryJob.objects.filter(character=character)

    # Apply filters from query string
    activity_id = request.GET.get('activity', '')
    status_filter = request.GET.get('status', '')

    if activity_id:
        jobs_qs = jobs_qs.filter(activity_id=activity_id)
    if status_filter:
        jobs_qs = jobs_qs.filter(status=status_filter)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f"{character.character_name}_industry_jobs.csv"
    filename = filename.replace(' ', '_').replace('/', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Write header
    writer.writerow([
        'Job ID',
        'Activity',
        'Status',
        'Blueprint Type ID',
        'Blueprint Name',
        'Product Type ID',
        'Product Name',
        'Station ID',
        'Solar System ID',
        'Start Date',
        'End Date',
        'Completed Date',
        'Runs',
        'Cost (ISK)',
        'Probability (%)',
        'Attempts',
        'Success',
        'Progress (%)',
    ])

    # Write data rows
    for job in jobs_qs:
        writer.writerow([
            job.job_id,
            job.activity_name,
            job.status_name,
            job.blueprint_type_id,
            job.blueprint_type_name,
            job.product_type_id or '',
            job.product_name,
            job.station_id,
            job.solar_system_id,
            job.start_date.strftime('%Y-%m-%d %H:%M:%S') if job.start_date else '',
            job.end_date.strftime('%Y-%m-%d %H:%M:%S') if job.end_date else '',
            job.completed_date.strftime('%Y-%m-%d %H:%M:%S') if job.completed_date else '',
            job.runs,
            f'{float(job.cost):.2f}' if job.cost else '0.00',
            f'{job.probability:.1f}' if job.probability is not None else '',
            job.attempts or '',
            'Yes' if job.success else ('No' if job.success is not None else ''),
            f'{job.progress_percent:.1f}' if job.progress_percent else '0.0',
        ])

    return response


@login_required
def blueprints_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View blueprint library with BPO/BPC distinction and filtering."""
    from core.models import Character
    from core.character.models import CharacterAsset
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from collections import defaultdict

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

    # Get filter parameters
    bp_type_filter = request.GET.get('type', '')  # 'BPO', 'BPC', or ''
    search_query = request.GET.get('search', '')
    location_filter = request.GET.get('location', '')

    # Get all blueprint assets for this character
    # Note: filter by checking type_id against blueprints in the SDE
    from core.eve.models import ItemType
    blueprint_type_ids = ItemType.objects.filter(category_id=9).values_list('id', flat=True)

    # Build base queryset
    blueprints_qs = CharacterAsset.objects.filter(
        character=character,
        type_id__in=blueprint_type_ids
    )

    # Apply type filter
    if bp_type_filter == 'BPO':
        # BPO: is_blueprint_copy = False
        blueprints_qs = blueprints_qs.filter(is_blueprint_copy=False)
    elif bp_type_filter == 'BPC':
        # BPC: is_blueprint_copy = True
        blueprints_qs = blueprints_qs.filter(is_blueprint_copy=True)

    # Apply location filter
    if location_filter:
        if location_filter == 'station':
            blueprints_qs = blueprints_qs.filter(location_type='station')
        elif location_filter == 'structure':
            blueprints_qs = blueprints_qs.filter(location_type='structure')
        elif location_filter == 'solar_system':
            blueprints_qs = blueprints_qs.filter(location_type='solar_system')

    # Apply search filter (need to filter by type_id from matching ItemType names)
    if search_query:
        matching_type_ids = ItemType.objects.filter(
            id__in=blueprint_type_ids,
            name__icontains=search_query
        ).values_list('id', flat=True)
        blueprints_qs = blueprints_qs.filter(type_id__in=matching_type_ids)

    # Get all matching blueprints and sort in Python (since we can't order by type__name without FK)
    all_blueprints = list(blueprints_qs)

    # Sort by type name (fetch names for sorting)
    if all_blueprints:
        type_ids = [bp.type_id for bp in all_blueprints]
        type_names = dict(ItemType.objects.filter(
            id__in=type_ids
        ).values_list('id', 'name'))
        for bp in all_blueprints:
            bp._cached_type_name = type_names.get(bp.type_id, f"Type {bp.type_id}")
        all_blueprints.sort(key=lambda x: x._cached_type_name)

    # Pagination
    page = request.GET.get('page', 1)
    per_page = 50
    paginator = Paginator(all_blueprints, per_page)

    try:
        blueprints = paginator.page(page)
    except PageNotAnInteger:
        blueprints = paginator.page(1)
    except EmptyPage:
        blueprints = paginator.page(paginator.num_pages)

    # Calculate blueprint counts
    base_qs = CharacterAsset.objects.filter(
        character=character,
        type_id__in=blueprint_type_ids
    )
    bpo_count = base_qs.filter(is_blueprint_copy=False).count()
    bpc_count = base_qs.filter(is_blueprint_copy=True).count()

    return render(request, 'core/blueprints_list.html', {
        'character': character,
        'blueprints': blueprints,
        'bp_type_filter': bp_type_filter,
        'search_query': search_query,
        'location_filter': location_filter,
        'bpo_count': bpo_count,
        'bpc_count': bpc_count,
        'total_blueprints': bpo_count + bpc_count,
    })


# ============================================================================
# FITTINGS VIEWS
# ============================================================================

@login_required
def fittings_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View all fittings with filtering."""
    from core.models import Character
    from core.doctrines.models import Fitting
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

    # Build base queryset
    fittings_qs = Fitting.objects.active()

    # Apply ship type filter
    if ship_type_filter:
        fittings_qs = fittings_qs.filter(ship_type_id=ship_type_filter)

    # Apply tag filter (JSON field query)
    if tag_filter:
        # Filter by JSON tags field - check if tag exists in the tags dict
        fittings_qs = [f for f in fittings_qs if tag_filter in f.tags]

    # Apply search filter
    if search_query:
        fittings_qs = fittings_qs.filter(name__icontains=search_query)

    # Prefetch related data
    fittings_qs = fittings_qs.select_related()

    # Get all ship types for filter dropdown
    ship_types = ItemType.objects.filter(category_id=6).order_by('name')

    # Get all unique tags from active fittings
    all_tags = set()
    for fitting in Fitting.objects.active():
        all_tags.update(fitting.tags.keys())

    return render(request, 'core/fittings_list.html', {
        'character': character,
        'fittings': fittings_qs,
        'ship_types': ship_types,
        'ship_type_filter': ship_type_filter,
        'search_query': search_query,
        'tag_filter': tag_filter,
        'all_tags': sorted(all_tags),
    })


@login_required
def fitting_detail(request: HttpRequest, fitting_id: int) -> HttpResponse:
    """View fitting details with module layout."""
    from core.doctrines.models import Fitting, FittingMatch
    from core.models import Character

    try:
        fitting = Fitting.objects.get(id=fitting_id)
    except Fitting.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Fitting not found',
        }, status=404)

    # Get slots
    slots = fitting.get_slots()

    # Get matching assets for current user's characters
    matching_assets = []
    if request.user.is_authenticated:
        for character in request.user.characters.all():
            matches = FittingMatch.objects.filter(
                character=character,
                fitting=fitting,
                is_match=True
            ).select_related('character')
            matching_assets.extend(matches)

    return render(request, 'core/fitting_detail.html', {
        'fitting': fitting,
        'slots': slots,
        'matching_assets': matching_assets,
    })


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
        # Find matching fittings for this ship type
        ship_fittings = Fitting.objects.active().filter(ship_type_id=ship.ship_type_id)
        
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
