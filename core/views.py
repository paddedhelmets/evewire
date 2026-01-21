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
    try:
        character = Character.objects.get(user=request.user)
    except Character.DoesNotExist:
        character = None

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
def skills_list(request: HttpRequest) -> HttpResponse:
    """List all skills with search and filtering."""
    from core.character.models import CharacterSkill
    from core.models import Character
    from core.eve.models import ItemType

    # Get user's character
    try:
        character = Character.objects.get(user=request.user)
    except Character.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Character not found. Please log in again.',
        }, status=404)

    # Get search/filter parameters
    search = request.GET.get('search', '')
    group_id = request.GET.get('group', '')
    min_level = request.GET.get('min_level', '')

    # Start with all character skills
    skills_qs = CharacterSkill.objects.filter(character=character).select_related()

    # Apply filters
    if search:
        # Search by skill name
        skill_ids = ItemType.objects.filter(name__icontains=search).values_list('id', flat=True)
        skills_qs = skills_qs.filter(skill_id__in=skill_ids)

    if group_id:
        # Filter by group (need to implement this properly with SDE data)
        # For now, skip this filter
        pass

    if min_level:
        try:
            min_level = int(min_level)
            skills_qs = skills_qs.filter(skill_level__gte=min_level)
        except ValueError:
            pass

    skills = skills_qs.order_by('-skill_level', 'skill_id')

    return render(request, 'core/skills_list.html', {
        'character': character,
        'skills': skills,
        'search': search,
        'group': group_id,
        'min_level': min_level,
    })


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
        try:
            character = Character.objects.get(user=request.user)
        except Character.DoesNotExist:
            pass

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
        try:
            character = Character.objects.get(user=request.user)
        except Character.DoesNotExist:
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
        try:
            character = Character.objects.get(user=request.user)
        except Character.DoesNotExist:
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
        try:
            character = Character.objects.get(user=request.user)
        except Character.DoesNotExist:
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
        try:
            character = Character.objects.get(user=request.user)
        except Character.DoesNotExist:
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
        try:
            character = Character.objects.get(user=request.user)
        except Character.DoesNotExist:
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
        try:
            character = Character.objects.get(user=request.user)
        except Character.DoesNotExist:
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
