"""
Core views for evewire.
"""

import logging
from datetime import timedelta, datetime, timezone as dt_timezone
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.db import models
from django.utils import timezone
from core.views import get_users_character

logger = logging.getLogger('evewire')
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
    """Multi-pilot wallet transaction history view."""
    from core.models import Character
    from core.character.models import WalletTransaction
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from datetime import datetime, timedelta

    # Get all characters for this user
    characters = request.user.characters.all()

    # Get filter parameters
    buy_sell_filter = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    character_filter = request.GET.get('character')

    # Build queryset across all pilots
    transactions_qs = WalletTransaction.objects.filter(character__user=request.user)

    # Apply character filter if selected
    if character_filter:
        transactions_qs = transactions_qs.filter(character_id=character_filter)

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

    # Order by date (newest first)
    transactions_qs = transactions_qs.select_related('character').order_by('-date')

    # Pagination
    paginator = Paginator(transactions_qs, 50)
    page = request.GET.get('page', 1)
    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)

    return render(request, 'core/wallet_transactions.html', {
        'transactions': transactions,
        'buy_sell_filter': buy_sell_filter,
        'date_from': date_from,
        'date_to': date_to,
        'character_filter': character_filter,
        'characters': characters,
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
    """Multi-pilot income/expense summary with aggregate stats and journal table."""
    from core.models import Character
    from core.character.models import WalletJournalEntry
    from django.db.models import Sum, Count, Q
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from datetime import datetime, timedelta
    from collections import defaultdict
    from django.utils import timezone

    # Get all characters for this user
    characters = request.user.characters.all()

    # Get time range parameters (default to last 30 days)
    days = request.GET.get('days', '30')
    try:
        days = int(days)
    except ValueError:
        days = 30

    since = timezone.now() - timedelta(days=days)

    # Get character filter
    character_filter = request.GET.get('character')

    # Aggregate by ref_type across all pilots
    summary_qs = WalletJournalEntry.objects.filter(
        character__user=request.user,
        date__gte=since
    )

    # Apply character filter if selected
    if character_filter:
        summary_qs = summary_qs.filter(character_id=character_filter)

    summary = summary_qs.values('ref_type').annotate(
        total_income=Sum('amount', filter=Q(amount__gt=0)),
        total_expense=Sum('amount', filter=Q(amount__lt=0)),
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

    # Build per-pilot breakdown
    pilot_stats = []
    for char in characters:
        char_income = WalletJournalEntry.objects.filter(
            character=char,
            date__gte=since,
            amount__gt=0
        ).aggregate(total=Sum('amount'))['total'] or 0

        char_expense = abs(WalletJournalEntry.objects.filter(
            character=char,
            date__gte=since,
            amount__lt=0
        ).aggregate(total=Sum('amount'))['total'] or 0)

        char_net = float(char_income) - float(char_expense)

        # Calculate current wallet balance
        latest_entry = WalletJournalEntry.objects.filter(
            character=char
        ).order_by('-date').first()

        current_balance = float(latest_entry.balance) if latest_entry else float(char.wallet_balance or 0)

        pilot_stats.append({
            'character': char,
            'income': float(char_income),
            'expense': float(char_expense),
            'net': char_net,
            'balance': current_balance,
        })

    # Get all journal entries with pagination
    journal_qs = WalletJournalEntry.objects.filter(
        character__user=request.user,
        date__gte=since
    ).select_related('character').order_by('-date')

    # Apply character filter
    if character_filter:
        journal_qs = journal_qs.filter(character_id=character_filter)

    # Paginate
    paginator = Paginator(journal_qs, 50)
    page = request.GET.get('page', 1)
    try:
        entries = paginator.page(page)
    except PageNotAnInteger:
        entries = paginator.page(1)
    except EmptyPage:
        entries = paginator.page(paginator.num_pages)

    return render(request, 'core/wallet_summary.html', {
        'summary': summary,
        'income_total': income_total,
        'expense_total': expense_total,
        'grand_total': grand_total,
        'days': days,
        'top_by_income': top_by_income,
        'top_by_expense': top_by_expense,
        'pilot_stats': pilot_stats,
        'entries': entries,
        'character_filter': character_filter,
        'characters': characters,
    })


# Market Orders Views

@login_required
def market_orders(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """Multi-pilot market orders view with aggregate stats and orders table."""
    from core.models import Character
    from core.character.models import MarketOrder
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models import Sum

    # Get all characters for this user
    characters = request.user.characters.all()

    # Get filter parameters
    order_type = request.GET.get('type', '')
    state_filter = request.GET.get('state', '')
    character_filter = request.GET.get('character')

    # Build queryset across all pilots
    orders_qs = MarketOrder.objects.filter(character__user=request.user)

    # Apply character filter if selected
    if character_filter:
        orders_qs = orders_qs.filter(character_id=character_filter)

    # Apply buy/sell filter
    if order_type == 'buy':
        orders_qs = orders_qs.filter(is_buy_order=True)
    elif order_type == 'sell':
        orders_qs = orders_qs.filter(is_buy_order=False)

    # Apply state filter
    if state_filter:
        orders_qs = orders_qs.filter(state=state_filter)

    # Order by issued date (newest first)
    orders_qs = orders_qs.select_related('character').order_by('-issued')

    # Pagination
    paginator = Paginator(orders_qs, 50)
    page = request.GET.get('page', 1)
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    # Calculate aggregate stats across all pilots
    total_buy_orders = sum(
        MarketOrder.objects.filter(
            character=char, is_buy_order=True, state='open'
        ).count() for char in characters
    )
    total_sell_orders = sum(
        MarketOrder.objects.filter(
            character=char, is_buy_order=False, state='open'
        ).count() for char in characters
    )

    # Calculate total escrowed ISK across all buy orders
    total_escrow = sum(
        MarketOrder.objects.filter(
            character=char, is_buy_order=True, state='open'
        ).aggregate(total=Sum('escrow'))['total'] or 0 for char in characters
    )

    # Build per-pilot breakdown
    pilot_stats = []
    for char in characters:
        buy_count = MarketOrder.objects.filter(
            character=char, is_buy_order=True, state='open'
        ).count()
        sell_count = MarketOrder.objects.filter(
            character=char, is_buy_order=False, state='open'
        ).count()
        escrow = MarketOrder.objects.filter(
            character=char, is_buy_order=True, state='open'
        ).aggregate(total=Sum('escrow'))['total'] or 0

        pilot_stats.append({
            'character': char,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'escrow': float(escrow),
            'total_orders': buy_count + sell_count,
        })

    return render(request, 'core/market_orders.html', {
        'orders': orders,
        'order_type': order_type,
        'state_filter': state_filter,
        'character_filter': character_filter,
        'total_buy_orders': total_buy_orders,
        'total_sell_orders': total_sell_orders,
        'total_escrow': total_escrow,
        'pilot_stats': pilot_stats,
        'characters': characters,
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
    """Multi-pilot trade overview showing profit/loss summary and top items."""
    from core.models import Character
    from core.trade.services import TradeAnalyzer
    from core.trade.models import Campaign
    from django.utils import timezone
    from datetime import timedelta

    # Get all characters for this user
    characters = request.user.characters.all()

    # Get timeframe filter
    timeframe = request.GET.get('timeframe', 'all')
    campaign_id = request.GET.get('campaign')
    year = request.GET.get('year')
    month = request.GET.get('month')
    character_filter = request.GET.get('character')

    # Determine date range
    start_date = None
    end_date = None
    timeframe_label = "All Time"

    if campaign_id:
        # Use campaign date range
        try:
            campaign = Campaign.objects.get(id=campaign_id, user=request.user)
            start_date = campaign.start_date
            end_date = campaign.end_date
            timeframe_label = campaign.title
        except Campaign.DoesNotExist:
            pass
    elif year and month:
        # Use specific month
        start_date = datetime(int(year), int(month), 1).replace(tzinfo=dt_timezone.utc)
        if int(month) == 12:
            end_date = datetime(int(year) + 1, 1, 1).replace(tzinfo=dt_timezone.utc) - timedelta(seconds=1)
        else:
            end_date = datetime(int(year), int(month) + 1, 1).replace(tzinfo=dt_timezone.utc) - timedelta(seconds=1)
        timeframe_label = f"{year}-{month.zfill(2)}"
    elif timeframe == '30d':
        start_date = timezone.now() - timedelta(days=30)
        end_date = timezone.now()
        timeframe_label = "Last 30 Days"
    elif timeframe == '90d':
        start_date = timezone.now() - timedelta(days=90)
        end_date = timezone.now()
        timeframe_label = "Last 90 Days"
    elif timeframe == '12m':
        start_date = timezone.now() - timedelta(days=365)
        end_date = timezone.now()
        timeframe_label = "Last 12 Months"
    else:
        # All time
        start_date = datetime(2000, 1, 1).replace(tzinfo=dt_timezone.utc)
        end_date = timezone.now()

    # Aggregate summaries across all characters (or filtered character)
    all_summaries = []
    chars_to_analyze = characters

    if character_filter:
        try:
            filtered_char = characters.get(id=character_filter)
            chars_to_analyze = [filtered_char]
        except Character.DoesNotExist:
            chars_to_analyze = []

    for char in chars_to_analyze:
        char_summaries = TradeAnalyzer.analyze_timeframe(char, start_date, end_date)
        all_summaries.extend(char_summaries)

    # Calculate overview stats
    total_buy = sum(s.buy_total for s in all_summaries)
    total_sell = sum(s.sell_total for s in all_summaries)
    net_balance = total_sell - total_buy

    # Get top items
    top_profitable = sorted((s for s in all_summaries if s.balance > 0), key=lambda x: x.balance, reverse=True)[:10]
    top_losses = sorted((s for s in all_summaries if s.balance < 0), key=lambda x: x.balance)[:10]
    top_volume = sorted(all_summaries, key=lambda x: x.buy_total + x.sell_total, reverse=True)[:10]

    # Build per-pilot breakdown
    pilot_stats = []
    for char in characters:
        char_summaries = TradeAnalyzer.analyze_timeframe(char, start_date, end_date)
        char_buy = sum(s.buy_total for s in char_summaries)
        char_sell = sum(s.sell_total for s in char_summaries)
        char_net = char_sell - char_buy
        char_count = len(char_summaries)

        pilot_stats.append({
            'character': char,
            'buy_total': char_buy,
            'sell_total': char_sell,
            'net': char_net,
            'items_traded': char_count,
        })

    # Get available campaigns
    campaigns = Campaign.objects.filter(user=request.user).order_by('-start_date')

    return render(request, 'core/trade_overview.html', {
        'summaries': all_summaries,
        'total_buy': total_buy,
        'total_sell': total_sell,
        'net_balance': net_balance,
        'top_profitable': top_profitable,
        'top_losses': top_losses,
        'top_volume': top_volume,
        'campaigns': campaigns,
        'timeframe': timeframe,
        'timeframe_label': timeframe_label,
        'campaign_id': campaign_id,
        'character_filter': character_filter,
        'pilot_stats': pilot_stats,
        'characters': characters,
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
        start_date = datetime(int(year), int(month), 1).replace(tzinfo=dt_timezone.utc)
        if int(month) == 12:
            end_date = datetime(int(year) + 1, 1, 1).replace(tzinfo=dt_timezone.utc) - timedelta(seconds=1)
        else:
            end_date = datetime(int(year), int(month) + 1, 1).replace(tzinfo=dt_timezone.utc) - timedelta(seconds=1)
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
    """Multi-pilot contracts view with aggregate stats and contracts table."""
    from core.models import Character
    from core.character.models import Contract
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    # Get all characters for this user
    characters = request.user.characters.all()

    # Get filter parameters
    contract_type = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    availability_filter = request.GET.get('availability', '')
    character_filter = request.GET.get('character')

    # Build queryset across all pilots
    contracts_qs = Contract.objects.filter(character__user=request.user)

    # Apply character filter if selected
    if character_filter:
        contracts_qs = contracts_qs.filter(character_id=character_filter)

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
    contracts_qs = contracts_qs.select_related('character').order_by('-date_issued')

    # Pagination
    paginator = Paginator(contracts_qs, 50)
    page = request.GET.get('page', 1)
    try:
        contracts = paginator.page(page)
    except PageNotAnInteger:
        contracts = paginator.page(1)
    except EmptyPage:
        contracts = paginator.page(paginator.num_pages)

    # Calculate aggregate stats across all pilots
    total_outstanding = sum(
        Contract.objects.filter(
            character=char, status='outstanding'
        ).count() for char in characters
    )
    total_in_progress = sum(
        Contract.objects.filter(
            character=char, status='in_progress'
        ).count() for char in characters
    )
    total_completed = sum(
        Contract.objects.filter(
            character=char, status__in=('finished_issuer', 'finished_contractor', 'finished')
        ).count() for char in characters
    )

    # Build per-pilot breakdown
    pilot_stats = []
    for char in characters:
        outstanding = Contract.objects.filter(
            character=char, status='outstanding'
        ).count()
        in_progress = Contract.objects.filter(
            character=char, status='in_progress'
        ).count()
        completed = Contract.objects.filter(
            character=char, status__in=('finished_issuer', 'finished_contractor', 'finished')
        ).count()

        pilot_stats.append({
            'character': char,
            'outstanding': outstanding,
            'in_progress': in_progress,
            'completed': completed,
            'total': outstanding + in_progress + completed,
        })

    return render(request, 'core/contracts.html', {
        'contracts': contracts,
        'contract_type': contract_type,
        'status_filter': status_filter,
        'availability_filter': availability_filter,
        'character_filter': character_filter,
        'total_outstanding': total_outstanding,
        'total_in_progress': total_in_progress,
        'total_completed': total_completed,
        'pilot_stats': pilot_stats,
        'characters': characters,
    })

