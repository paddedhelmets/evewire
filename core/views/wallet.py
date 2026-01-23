"""Wallet views."""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger(__name__)


def get_users_character(user):
    """Get user's character (first character if multiple).
    Returns None if user has no characters.
    """
    from core.models import Character
    return Character.objects.filter(user=user).first()


# Wallet Views

@login_required
def wallet_journal(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View wallet journal entries with pagination and filtering."""
    from core.models import Character
    from core.character.models import WalletJournalEntry
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from datetime import datetime, timedelta

    # Get all user's characters for pilot filter
    all_characters = list(Character.objects.filter(user=request.user).order_by('character_name'))

    if not all_characters:
        return render(request, 'core/error.html', {
            'message': 'No characters found',
        }, status=404)

    # Get character - either specified or user's first character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
        is_account_wide = False
    else:
        # Account-wide view - show all characters
        character = None
        is_account_wide = True

    # Get filter parameters
    pilot_filter = request.GET.getlist('pilots', [])  # Multi-select for account-wide
    ref_type_filter = request.GET.get('ref_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Build queryset
    if is_account_wide:
        # Filter by selected pilots, or show all if none selected
        if pilot_filter:
            pilot_ids = [int(pid) for pid in pilot_filter if pid.isdigit()]
            entries_qs = WalletJournalEntry.objects.filter(character_id__in=pilot_ids)
        else:
            entries_qs = WalletJournalEntry.objects.filter(character__user=request.user)
    else:
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
    if is_account_wide:
        if pilot_filter:
            pilot_ids = [int(pid) for pid in pilot_filter if pid.isdigit()]
            all_ref_types = WalletJournalEntry.objects.filter(
                character_id__in=pilot_ids
            ).values_list('ref_type', flat=True).distinct().order_by('ref_type')
        else:
            all_ref_types = WalletJournalEntry.objects.filter(
                character__user=request.user
            ).values_list('ref_type', flat=True).distinct().order_by('ref_type')
    else:
        all_ref_types = WalletJournalEntry.objects.filter(
            character=character
        ).values_list('ref_type', flat=True).distinct().order_by('ref_type')

    # Order by date descending
    entries_qs = entries_qs.order_by('-date')

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

    # Calculate summary stats for account-wide view
    summary = None
    if is_account_wide:
        total_entries = entries_qs.count()
        # Calculate total income/expense
        from django.db.models import Sum
        income = entries_qs.filter(amount__gt=0).aggregate(total=Sum('amount'))['total'] or 0
        expense = entries_qs.filter(amount__lt=0).aggregate(total=Sum('amount'))['total'] or 0
        summary = {
            'total_entries': total_entries,
            'income': income,
            'expense': abs(expense),
            'net': income + expense,
        }
    else:
        # Get current balance from latest entry for single character
        current_balance = entries_qs.order_by('-date').first()
        if current_balance:
            current_balance = current_balance.balance
        else:
            current_balance = character.wallet_balance

    return render(request, 'core/wallet_journal.html', {
        'character': character,
        'all_characters': all_characters,
        'is_account_wide': is_account_wide,
        'entries': entries,
        'ref_types': all_ref_types,
        'ref_type_filter': ref_type_filter,
        'date_from': date_from,
        'date_to': date_to,
        'pilot_filter': pilot_filter,
        'summary': summary,
        'current_balance': current_balance if not is_account_wide else None,
    })


@login_required
def wallet_transactions(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View wallet transaction history."""
    from core.models import Character
    from core.character.models import WalletTransaction
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from datetime import datetime, timedelta

    # Get all user's characters for pilot filter
    all_characters = list(Character.objects.filter(user=request.user).order_by('character_name'))

    if not all_characters:
        return render(request, 'core/error.html', {
            'message': 'No characters found',
        }, status=404)

    # Get character - either specified or user's first character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
        is_account_wide = False
    else:
        # Account-wide view - show all characters
        character = None
        is_account_wide = True

    # Get filter parameters
    pilot_filter = request.GET.getlist('pilots', [])  # Multi-select for account-wide
    buy_sell_filter = request.GET.get('type', '')  # 'buy', 'sell', or ''
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Build queryset
    if is_account_wide:
        # Filter by selected pilots, or show all if none selected
        if pilot_filter:
            pilot_ids = [int(pid) for pid in pilot_filter if pid.isdigit()]
            transactions_qs = WalletTransaction.objects.filter(character_id__in=pilot_ids)
        else:
            transactions_qs = WalletTransaction.objects.filter(character__user=request.user)
    else:
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

    # Order by date descending
    transactions_qs = transactions_qs.order_by('-date')

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

    # Calculate summary stats for account-wide view
    summary = None
    if is_account_wide:
        total_transactions = transactions_qs.count()
        # Calculate totals
        from django.db.models import Sum
        buy_total = transactions_qs.filter(is_buy=True).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        sell_total = transactions_qs.filter(is_buy=False).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        summary = {
            'total_transactions': total_transactions,
            'buy_quantity': buy_total,
            'sell_quantity': sell_total,
        }

    return render(request, 'core/wallet_transactions.html', {
        'character': character,
        'all_characters': all_characters,
        'is_account_wide': is_account_wide,
        'transactions': transactions,
        'buy_sell_filter': buy_sell_filter,
        'date_from': date_from,
        'date_to': date_to,
        'pilot_filter': pilot_filter,
        'summary': summary,
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

