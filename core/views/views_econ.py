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
        start_date = datetime(int(year), int(month), 1).replace(tzinfo=dt_timezone.utc)
        if int(month) == 12:
            end_date = datetime(int(year) + 1, 1, 1).replace(tzinfo=dt_timezone.utc) - timedelta(seconds=1)
        else:
            end_date = datetime(int(year), int(month) + 1, 1).replace(tzinfo=dt_timezone.utc) - timedelta(seconds=1)
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
            start_date=datetime(2000, 1, 1).replace(tzinfo=dt_timezone.utc),
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

