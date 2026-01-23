"""Market views."""

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


@login_required
def market_orders(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View market orders with filtering and pagination."""
    from core.models import Character
    from core.character.models import MarketOrder
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

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
    order_type = request.GET.get('type', '')  # 'buy', 'sell', or ''
    state_filter = request.GET.get('state', '')  # 'open', 'closed', 'expired', 'cancelled', ''

    # Build queryset
    if is_account_wide:
        # Filter by selected pilots, or show all if none selected
        if pilot_filter:
            pilot_ids = [int(pid) for pid in pilot_filter if pid.isdigit()]
            orders_qs = MarketOrder.objects.filter(character_id__in=pilot_ids)
        else:
            orders_qs = MarketOrder.objects.filter(character__user=request.user)
    else:
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

    # Calculate summary stats for account-wide view
    slot_utilization = None
    if is_account_wide:
        # Build slot utilization by pilot
        slot_utilization = []
        for char in all_characters:
            if pilot_filter and char.id not in [int(pid) for pid in pilot_filter if pid.isdigit()]:
                continue
            orders_count = char.market_orders.filter(state='open').count()
            utilization = (orders_count / char.market_order_slots * 100) if char.market_order_slots > 0 else 0
            slot_utilization.append({
                'character': char,
                'orders_count': orders_count,
                'slots_total': char.market_order_slots,
                'utilization': utilization,
            })
    else:
        # Calculate order totals for single character
        buy_total = MarketOrder.objects.filter(
            character=character, is_buy_order=True, state='open'
        ).count()
        sell_total = MarketOrder.objects.filter(
            character=character, is_buy_order=False, state='open'
        ).count()

    return render(request, 'core/market_orders.html', {
        'character': character,
        'all_characters': all_characters,
        'is_account_wide': is_account_wide,
        'orders': orders,
        'order_type': order_type,
        'state_filter': state_filter,
        'pilot_filter': pilot_filter,
        'slot_utilization': slot_utilization,
        'buy_total': buy_total if not is_account_wide else None,
        'sell_total': sell_total if not is_account_wide else None,
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


