"""
Trade analysis services.

Service for aggregating and analyzing wallet transaction data
to calculate profit/loss, inventory turnover, and trading performance.
"""

from dataclasses import dataclass
from decimal import Decimal
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import timedelta

from core.character.models import WalletTransaction
from core.trade.models import Campaign


@dataclass
class ItemTradeSummary:
    """
    Aggregated trade statistics for a single item type.

    Represents buy/sell totals, profit calculations, and inventory tracking
    for a specific item within a time period.
    """
    type_id: int
    type_name: str

    # Buys
    buy_quantity: int
    buy_total: Decimal
    buy_avg: Decimal

    # Sells
    sell_quantity: int
    sell_total: Decimal
    sell_avg: Decimal

    # Results
    balance: Decimal  # sell_total - buy_total
    diff: int  # buy_quantity - sell_quantity (unsold stock)

    # Projections
    projected: Decimal  # balance + (diff * sell_avg)
    profit_per_unit: Decimal  # sell_avg - buy_avg
    profit_pct: float  # (profit_per_unit / buy_avg) * 100


class TradeAnalyzer:
    """
    Service for analyzing wallet transaction data.

    Aggregates transactions by item type and calculates profit/loss,
    inventory turnover, and trading performance metrics.
    """

    @staticmethod
    def analyze_timeframe(character, start_date, end_date):
        """
        Analyze transactions for a character within a date range.

        Args:
            character: Character instance to analyze
            start_date: DateTime - start of analysis period
            end_date: DateTime - end of analysis period

        Returns:
            List of ItemTradeSummary objects, one per item type traded
        """
        from core.eve.models import ItemType

        # Get all transactions in date range
        transactions = WalletTransaction.objects.filter(
            character=character,
            date__range=(start_date, end_date)
        ).select_related()

        # Get all unique type_ids in the range
        type_ids = transactions.values_list('type_id', flat=True).distinct()

        summaries = []
        for type_id in type_ids:
            item_txns = transactions.filter(type_id=type_id)

            buys = item_txns.filter(is_buy=True)
            sells = item_txns.filter(is_buy=False)

            # Calculate buy totals
            buy_agg = buys.aggregate(
                buy_quantity=Sum('quantity'),
                buy_total=Sum(models.ExpressionWrapper(
                    models.F('quantity') * models.F('unit_price'),
                    output_field=models.DecimalField()
                ))
            )
            buy_quantity = buy_agg['buy_quantity'] or 0
            buy_total = buy_agg['buy_total'] or Decimal('0')
            buy_avg = buy_total / buy_quantity if buy_quantity > 0 else Decimal('0')

            # Calculate sell totals
            sell_agg = sells.aggregate(
                sell_quantity=Sum('quantity'),
                sell_total=Sum(models.ExpressionWrapper(
                    models.F('quantity') * models.F('unit_price'),
                    output_field=models.DecimalField()
                ))
            )
            sell_quantity = sell_agg['sell_quantity'] or 0
            sell_total = sell_agg['sell_total'] or Decimal('0')
            sell_avg = sell_total / sell_quantity if sell_quantity > 0 else Decimal('0')

            # Calculate results
            balance = sell_total - buy_total
            diff = buy_quantity - sell_quantity  # Unsold stock

            # Projections
            projected = balance + (diff * sell_avg) if sell_avg else balance
            profit_per_unit = sell_avg - buy_avg
            profit_pct = float((profit_per_unit / buy_avg) * 100) if buy_avg > 0 else 0.0

            # Get type name
            try:
                type_name = ItemType.objects.get(id=type_id).name
            except ItemType.DoesNotExist:
                type_name = f"Type {type_id}"

            summaries.append(ItemTradeSummary(
                type_id=type_id,
                type_name=type_name,
                buy_quantity=buy_quantity,
                buy_total=buy_total,
                buy_avg=buy_avg,
                sell_quantity=sell_quantity,
                sell_total=sell_total,
                sell_avg=sell_avg,
                balance=balance,
                diff=diff,
                projected=projected,
                profit_per_unit=profit_per_unit,
                profit_pct=profit_pct,
            ))

        # Sort by balance (profit) descending
        summaries.sort(key=lambda x: x.balance, reverse=True)
        return summaries

    @staticmethod
    def analyze_campaign(campaign: Campaign):
        """
        Analyze transactions for a campaign.

        Args:
            campaign: Campaign instance with date range and optional character filters

        Returns:
            List of ItemTradeSummary objects
        """
        transactions = campaign.get_transactions()

        if not transactions.exists():
            return []

        # Get all unique type_ids
        type_ids = transactions.values_list('type_id', flat=True).distinct()

        summaries = []
        from core.eve.models import ItemType
        from django.db import models as django_models

        for type_id in type_ids:
            item_txns = transactions.filter(type_id=type_id)

            buys = item_txns.filter(is_buy=True)
            sells = item_txns.filter(is_buy=False)

            # Calculate buy totals
            buy_agg = buys.aggregate(
                buy_quantity=Sum('quantity'),
                buy_total=Sum(django_models.ExpressionWrapper(
                    django_models.F('quantity') * django_models.F('unit_price'),
                    output_field=django_models.DecimalField()
                ))
            )
            buy_quantity = buy_agg['buy_quantity'] or 0
            buy_total = buy_agg['buy_total'] or Decimal('0')
            buy_avg = buy_total / buy_quantity if buy_quantity > 0 else Decimal('0')

            # Calculate sell totals
            sell_agg = sells.aggregate(
                sell_quantity=Sum('quantity'),
                sell_total=Sum(django_models.ExpressionWrapper(
                    django_models.F('quantity') * django_models.F('unit_price'),
                    output_field=django_models.DecimalField()
                ))
            )
            sell_quantity = sell_agg['sell_quantity'] or 0
            sell_total = sell_agg['sell_total'] or Decimal('0')
            sell_avg = sell_total / sell_quantity if sell_quantity > 0 else Decimal('0')

            # Calculate results
            balance = sell_total - buy_total
            diff = buy_quantity - sell_quantity

            # Projections
            projected = balance + (diff * sell_avg) if sell_avg else balance
            profit_per_unit = sell_avg - buy_avg
            profit_pct = float((profit_per_unit / buy_avg) * 100) if buy_avg > 0 else 0.0

            # Get type name
            try:
                type_name = ItemType.objects.get(id=type_id).name
            except ItemType.DoesNotExist:
                type_name = f"Type {type_id}"

            summaries.append(ItemTradeSummary(
                type_id=type_id,
                type_name=type_name,
                buy_quantity=buy_quantity,
                buy_total=buy_total,
                buy_avg=buy_avg,
                sell_quantity=sell_quantity,
                sell_total=sell_total,
                sell_avg=sell_avg,
                balance=balance,
                diff=diff,
                projected=projected,
                profit_per_unit=profit_per_unit,
                profit_pct=profit_pct,
            ))

        # Sort by balance (profit) descending
        summaries.sort(key=lambda x: x.balance, reverse=True)
        return summaries

    @staticmethod
    def get_monthly_summaries(character):
        """
        Get monthly trade summaries for a character.

        Detects all months with transaction activity and returns
        summaries for each month.

        Args:
            character: Character instance

        Returns:
            List of tuples: (year, month, list of ItemTradeSummary)
        """
        # Get all transaction dates for this character
        dates = WalletTransaction.objects.filter(
            character=character
        ).values_list('date', flat=True).distinct().order_by('date')

        if not dates:
            return []

        # Extract unique (year, month) tuples
        year_months = set((d.year, d.month) for d in dates)

        summaries = []
        for year, month in sorted(year_months):
            # Calculate date range for this month
            start_date = timezone.datetime(year, month, 1).replace(tzinfo=timezone.utc)
            if month == 12:
                end_date = timezone.datetime(year + 1, 1, 1).replace(tzinfo=timezone.utc) - timedelta(seconds=1)
            else:
                end_date = timezone.datetime(year, month + 1, 1).replace(tzinfo=timezone.utc) - timedelta(seconds=1)

            # Analyze this month
            monthly_data = TradeAnalyzer.analyze_timeframe(character, start_date, end_date)
            summaries.append((year, month, monthly_data))

        return summaries

    @staticmethod
    def get_overview_stats(character, start_date=None, end_date=None):
        """
        Get overview statistics for a character's trading.

        Args:
            character: Character instance
            start_date: Optional start date (defaults to all time)
            end_date: Optional end date (defaults to now)

        Returns:
            Dict with overall trading statistics
        """
        qs = WalletTransaction.objects.filter(character=character)

        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        if not qs.exists():
            return {
                'total_buy_volume': Decimal('0'),
                'total_sell_volume': Decimal('0'),
                'net_balance': Decimal('0'),
                'total_transactions': 0,
                'unique_items': 0,
            }

        from django.db import models as django_models

        # Calculate totals
        buys = qs.filter(is_buy=True)
        sells = qs.filter(is_buy=False)

        buy_agg = buys.aggregate(
            total=Sum(django_models.ExpressionWrapper(
                django_models.F('quantity') * django_models.F('unit_price'),
                output_field=django_models.DecimalField()
            ))
        )
        total_buy_volume = buy_agg['total'] or Decimal('0')

        sell_agg = sells.aggregate(
            total=Sum(django_models.ExpressionWrapper(
                django_models.F('quantity') * django_models.F('unit_price'),
                output_field=django_models.DecimalField()
            ))
        )
        total_sell_volume = sell_agg['total'] or Decimal('0')

        net_balance = total_sell_volume - total_buy_volume

        return {
            'total_buy_volume': total_buy_volume,
            'total_sell_volume': total_sell_volume,
            'net_balance': net_balance,
            'total_transactions': qs.count(),
            'unique_items': qs.values('type_id').distinct().count(),
        }


# Import for use in aggregation
from django.db import models
