"""
Trade analysis models.

Campaign models for custom date range filtering and trade performance analysis.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import User, Character


class Campaign(models.Model):
    """
    User-defined trade analysis campaign.

    Campaigns allow users to define custom date ranges for analyzing
    their trading performance. Transactions can be filtered by campaign
    to calculate profit/loss for specific trading periods.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trade_campaigns'
    )
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    # Date range
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    # Filter by character (optional)
    characters = models.ManyToManyField(
        Character,
        blank=True,
        related_name='trade_campaigns',
        help_text=_('Specific characters to include in this campaign. Leave empty for all.')
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('trade campaign')
        verbose_name_plural = _('trade campaigns')
        ordering = ['-start_date']
        db_table = 'core_trade_campaign'

    def __str__(self) -> str:
        return self.title

    def get_transactions(self):
        """
        Get all wallet transactions for this campaign's date range.

        Filters by:
        - Date range (start_date to end_date)
        - Characters (if specified)
        """
        from core.character.models import WalletTransaction

        qs = WalletTransaction.objects.filter(
            date__range=(self.start_date, self.end_date)
        )

        if self.characters.exists():
            qs = qs.filter(character__in=self.characters.all())

        return qs.select_related('character')
