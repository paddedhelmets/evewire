"""
Character data models from ESI.

These models store cached ESI data for characters, including skills, assets,
wallet, and market orders.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey


class CharacterSkill(models.Model):
    """
    A trained skill for a character.

    From ESI: GET /characters/{character_id}/skills/
    """

    character = models.ForeignKey(
        'core.Character',
        on_delete=models.CASCADE,
        related_name='skills'
    )
    skill_id = models.IntegerField(db_index=True)  # FK to ItemType
    skill_level = models.SmallIntegerField(default=0)  # 0-5
    skillpoints_in_skill = models.IntegerField(default=0)
    trained_skill_level = models.SmallIntegerField(default=0)  # 0-5

    # Cache metadata
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('character skill')
        verbose_name_plural = _('character skills')
        unique_together = [['character', 'skill_id']]
        ordering = ['skill_id']

    def __str__(self) -> str:
        return f"{self.character.name}: Skill {self.skill_id} -> L{self.skill_level}"

    @property
    def skill_name(self) -> str:
        """Get the skill name from ItemType."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.skill_id).name
        except ItemType.DoesNotExist:
            return f"Skill {self.skill_id}"


class SkillQueueItem(models.Model):
    """
    A skill in the training queue.

    From ESI: GET /characters/{character_id}/skillqueue/
    """

    character = models.ForeignKey(
        'core.Character',
        on_delete=models.CASCADE,
        related_name='skill_queue'
    )
    queue_position = models.IntegerField()
    skill_id = models.IntegerField(db_index=True)  # FK to ItemType
    finish_level = models.SmallIntegerField()  # Target level (1-5)
    level_start_sp = models.IntegerField()
    level_end_sp = models.IntegerField()
    training_start_time = models.DateTimeField()
    finish_date = models.DateTimeField()

    # Cache metadata
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('skill queue item')
        verbose_name_plural = _('skill queue items')
        unique_together = [['character', 'queue_position']]
        ordering = ['character', 'queue_position']

    def __str__(self) -> str:
        return f"{self.character.name}: Skill {self.skill_id} -> L{self.finish_level}"

    @property
    def skill_name(self) -> str:
        """Get the skill name from ItemType."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.skill_id).name
        except ItemType.DoesNotExist:
            return f"Skill {self.skill_id}"

    @property
    def is_completed(self) -> bool:
        """Check if this skill has finished training."""
        from django.utils import timezone
        return self.finish_date <= timezone.now()

    @property
    def progress_percent(self) -> float:
        """Calculate training progress percentage."""
        from django.utils import timezone
        total = self.level_end_sp - self.level_start_sp
        if total == 0:
            return 100.0

        elapsed = timezone.now() - self.training_start_time
        elapsed_seconds = elapsed.total_seconds()
        total_seconds = (self.finish_date - self.training_start_time).total_seconds()

        if total_seconds <= 0:
            return 100.0

        return min(100.0, max(0.0, (elapsed_seconds / total_seconds) * 100))


class CharacterAsset(MPTTModel):
    """
    An asset owned by a character.

    From ESI: GET /characters/{character_id}/assets/

    Assets form a hierarchical tree (e.g., ship in hangar, modules in ship).
    Uses django-mptt for efficient tree queries.

    Item fields from swagger spec:
    - is_blueprint_copy: boolean
    - is_singleton: boolean
    - item_id: integer (PK)
    - location_flag: string (88 enum values)
    - location_id: integer
    - location_type: string (4 enum values: station, solar_system, structure, other)
    - quantity: integer
    - type_id: integer (FK to ItemType)
    """

    character = models.ForeignKey(
        'core.Character',
        on_delete=models.CASCADE,
        related_name='assets'
    )

    # ESI asset fields
    item_id = models.BigIntegerField(primary_key=True)
    type_id = models.IntegerField(db_index=True)  # FK to ItemType
    quantity = models.IntegerField(default=1)
    location_id = models.BigIntegerField(null=True, blank=True)  # FK to Station/Structure/System
    location_type = models.CharField(max_length=20, blank=True)  # station, solar_system, structure, other
    location_flag = models.CharField(max_length=50, blank=True)  # Hangar, Cargo, etc.
    is_singleton = models.BooleanField(default=False)
    is_blueprint_copy = models.BooleanField(default=False)

    # Tree structure (MPTT fields are auto-added)
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    # Cache metadata
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('character asset')
        verbose_name_plural = _('character assets')
        ordering = ['character', 'location_id', 'location_flag']

    def __str__(self) -> str:
        return f"{self.character.name}: {self.type_name} x{self.quantity}"

    @property
    def type_name(self) -> str:
        """Get the item type name from ItemType."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.type_id).name
        except ItemType.DoesNotExist:
            return f"Type {self.type_id}"

    @property
    def total_quantity(self) -> int:
        """Get total quantity including all children."""
        if self.is_leaf_node():
            return self.quantity
        return sum(child.quantity for child in self.get_descendants())

    @property
    def location_name(self) -> str:
        """Get human-readable location name."""
        from core.eve.models import Station, SolarSystem

        if self.location_type == 'station':
            try:
                return Station.objects.get(id=self.location_id).name
            except Station.DoesNotExist:
                return f"Station {self.location_id}"
        elif self.location_type == 'solar_system':
            try:
                return SolarSystem.objects.get(id=self.location_id).name
            except SolarSystem.DoesNotExist:
                return f"System {self.location_id}"
        elif self.location_type == 'structure':
            return f"Structure {self.location_id}"
        else:
            return "Unknown location"


class WalletJournalEntry(models.Model):
    """
    A wallet journal entry.

    From ESI: GET /characters/{character_id}/wallet/journal/
    """

    character = models.ForeignKey(
        'core.Character',
        on_delete=models.CASCADE,
        related_name='wallet_journal'
    )

    # ESI fields
    entry_id = models.BigIntegerField(primary_key=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    balance = models.DecimalField(max_digits=20, decimal_places=2)
    date = models.DateTimeField(db_index=True)
    description = models.TextField(blank=True)
    first_party_id = models.IntegerField(null=True, blank=True)  # ID of the other party
    reason = models.TextField(blank=True)
    ref_type = models.CharField(max_length=50)  # Transaction type
    tax = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    tax_receiver_id = models.IntegerField(null=True, blank=True)

    # Cache metadata
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('wallet journal entry')
        verbose_name_plural = _('wallet journal entries')
        ordering = ['-date']

    def __str__(self) -> str:
        return f"{self.character.name}: {self.ref_type} {self.amount} ISK"


class WalletTransaction(models.Model):
    """
    A wallet transaction (buy or sell order).

    From ESI: GET /characters/{character_id}/wallet/transactions/
    """

    character = models.ForeignKey(
        'core.Character',
        on_delete=models.CASCADE,
        related_name='wallet_transactions'
    )

    # ESI fields
    transaction_id = models.BigIntegerField(primary_key=True)
    date = models.DateTimeField(db_index=True)
    is_buy = models.BooleanField(default=True)
    is_personal = models.BooleanField(default=False)
    journal_ref_id = models.BigIntegerField(null=True, blank=True)
    location_id = models.BigIntegerField()
    quantity = models.IntegerField()
    type_id = models.IntegerField(db_index=True)  # FK to ItemType
    unit_price = models.DecimalField(max_digits=20, decimal_places=2)

    # Cache metadata
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('wallet transaction')
        verbose_name_plural = _('wallet transactions')
        ordering = ['-date']

    def __str__(self) -> str:
        action = "BUY" if self.is_buy else "SELL"
        return f"{self.character.name}: {action} {self.quantity}x Type {self.type_id} @ {self.unit_price}"

    @property
    def total_value(self) -> float:
        """Calculate total transaction value."""
        return float(self.quantity) * float(self.unit_price)


class MarketOrder(models.Model):
    """
    A market order (buy or sell).

    From ESI: GET /characters/{character_id}/orders/
    """

    character = models.ForeignKey(
        'core.Character',
        on_delete=models.CASCADE,
        related_name='market_orders'
    )

    # ESI fields
    order_id = models.BigIntegerField(primary_key=True)
    is_buy_order = models.BooleanField(default=False)
    type_id = models.IntegerField(db_index=True)  # FK to ItemType
    region_id = models.IntegerField(db_index=True)
    station_id = models.BigIntegerField()
    system_id = models.IntegerField()
    volume_remain = models.IntegerField()
    volume_total = models.IntegerField()
    min_volume = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    issued = models.DateTimeField()
    duration = models.IntegerField()  # Days
    range = models.CharField(max_length=20)  # station, region, solar_system, X jumps
    state = models.CharField(max_length=20)  # open, closed, expired, cancelled, partially_filled
    escrow = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    # Cache metadata
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('market order')
        verbose_name_plural = _('market orders')
        ordering = ['-issued']

    def __str__(self) -> str:
        action = "BUY" if self.is_buy_order else "SELL"
        return f"{self.character.name}: {action} {self.volume_remain}/{self.volume_total} Type {self.type_id} @ {self.price}"

    @property
    def type_name(self) -> str:
        """Get the item type name from ItemType."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.type_id).name
        except ItemType.DoesNotExist:
            return f"Type {self.type_id}"

    @property
    def is_open(self) -> bool:
        """Check if this order is still open."""
        return self.state == 'open'

    @property
    def is_expired(self) -> bool:
        """Check if this order has expired."""
        from django.utils import timezone
        expiry = self.issued + timezone.timedelta(days=self.duration)
        return expiry <= timezone.now()

    @property
    def expires_at(self) -> timezone.datetime:
        """Calculate when this order expires."""
        from django.utils import timezone
        return self.issued + timezone.timedelta(days=self.duration)

    @property
    def fill_percent(self) -> float:
        """Calculate how much of the order has been filled."""
        if self.volume_total == 0:
            return 0.0
        return ((self.volume_total - self.volume_remain) / self.volume_total) * 100
