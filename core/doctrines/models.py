"""
Fitting specification models.

Stores canonical fittings from clustering analysis and provides
services for matching against character assets.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from typing import List, Dict, Optional


class FittingQuerySet(models.QuerySet):
    """Custom QuerySet for Fitting model."""

    def for_ship_type(self, ship_type_id: int):
        """Get fittings for a specific ship type."""
        return self.filter(ship_type_id=ship_type_id)

    def active(self):
        """Get active fittings."""
        return self.filter(is_active=True)

    def for_user(self, user):
        """
        Get fittings visible to a user.

        Returns:
            User's own fittings (owner=user) + global fittings (owner=None)
            that the user hasn't ignored.
        """
        from django.db.models import Q

        # Get IDs of fittings ignored by this user
        ignored_ids = FittingIgnore.objects.filter(
            user=user
        ).values_list('fitting_id', flat=True)

        # User's own fittings + global fittings, excluding ignored
        return self.filter(
            Q(owner=user) | Q(owner__isnull=True)
        ).exclude(
            id__in=ignored_ids
        )


class FittingManager(models.Manager):
    """Manager for Fitting queries."""

    def get_queryset(self):
        return FittingQuerySet(model=self.model, using=self._db)

    def for_ship_type(self, ship_type_id: int):
        """Get fittings for a specific ship type."""
        return self.get_queryset().for_ship_type(ship_type_id)

    def active(self):
        """Get active fittings."""
        return self.get_queryset().active()

    def for_user(self, user):
        """
        Get fittings visible to a user.

        Returns:
            User's own fittings (owner=user) + global fittings (owner=None)
            that the user hasn't ignored.
        """
        return self.get_queryset().for_user(user)


class Fitting(models.Model):
    """
    A ship fitting specification.

    Represents a canonical fitting extracted from zkillboard clustering,
    or a manually defined ship fitting.

    Ownership model:
    - owner=None: Global fitting available to all users (e.g., career_research imports)
    - owner=<user>: Private fitting only visible to that user
    """

    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)

    # Owner: null = global/shared, set = user-private
    owner = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='own_fittings',
        null=True,
        blank=True,
        help_text="User who owns this fitting (null = global/shared fitting)",
    )

    # Ship hull
    ship_type_id = models.IntegerField(db_index=True)  # FK to ItemType

    # Metadata from clustering (optional)
    cluster_id = models.IntegerField(null=True, blank=True)
    fit_count = models.IntegerField(null=True, blank=True, help_text="Number of fits in this cluster")
    avg_similarity = models.FloatField(null=True, blank=True)

    # Fitting management
    is_active = models.BooleanField(default=True, help_text="Whether this fitting is currently in use")
    is_pinned = models.BooleanField(default=False, db_index=True, help_text="Whether this fitting is pinned to the top of the list")
    tags = models.JSONField(default=dict, blank=True, help_text="User-defined tags (e.g., {'role': 'logi', 'tier': '1'})")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FittingManager()

    class Meta:
        verbose_name = _('fitting')
        verbose_name_plural = _('fittings')
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['ship_type_id', 'cluster_id'],
                condition=models.Q(cluster_id__isnull=False),
                name='unique_cluster_per_ship'
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.ship_type_name})"

    @property
    def ship_type_name(self) -> str:
        """Get ship type name."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.ship_type_id).name
        except ItemType.DoesNotExist:
            return f"Type {self.ship_type_id}"

    def get_slots(self) -> Dict[str, List[int]]:
        """
        Get all module slots as a dict.

        Returns:
            {
                'high_slots': [type_id, ...],
                'med_slots': [type_id, ...],
                'low_slots': [type_id, ...],
                'rig_slots': [type_id, ...],
                'subsystem_slots': [type_id, ...],
            }
        """
        slots = {
            'high_slots': [],
            'med_slots': [],
            'low_slots': [],
            'rig_slots': [],
            'subsystem_slots': [],
        }

        for entry in self.entries.all():
            if entry.slot_type == 'high':
                slots['high_slots'].append(entry.module_type_id)
            elif entry.slot_type == 'med':
                slots['med_slots'].append(entry.module_type_id)
            elif entry.slot_type == 'low':
                slots['low_slots'].append(entry.module_type_id)
            elif entry.slot_type == 'rig':
                slots['rig_slots'].append(entry.module_type_id)
            elif entry.slot_type == 'subsystem':
                slots['subsystem_slots'].append(entry.module_type_id)

        return slots


class FittingEntry(models.Model):
    """
    A single module entry in a fitting.

    Represents one slot position in the fitting specification.
    """

    SLOT_TYPES = [
        ('high', 'High Slot'),
        ('med', 'Medium Slot'),
        ('low', 'Low Slot'),
        ('rig', 'Rig Slot'),
        ('subsystem', 'Subsystem Slot'),
    ]

    fitting = models.ForeignKey(
        Fitting,
        on_delete=models.CASCADE,
        related_name='entries',
    )

    slot_type = models.CharField(max_length=20, choices=SLOT_TYPES)
    position = models.IntegerField(help_text="Position within the slot type (0-indexed)")

    module_type_id = models.IntegerField(db_index=True, help_text="ItemType ID for the module")

    # Module state
    is_offline = models.BooleanField(default=False, help_text="Whether this module is fitted offline")

    # Metadata from clustering
    usage_count = models.IntegerField(null=True, blank=True, help_text="How many fits had this module")
    usage_percentage = models.FloatField(null=True, blank=True, help_text="Percentage of fits with this module")

    class Meta:
        verbose_name = _('fitting entry')
        verbose_name_plural = _('fitting entries')
        ordering = ['fitting', 'slot_type', 'position']
        unique_together = [['fitting', 'slot_type', 'position']]

    def __str__(self) -> str:
        return f"{self.fitting.name}: {self.slot_type} slot {self.position}"

    @property
    def module_name(self) -> str:
        """Get module type name."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.module_type_id).name
        except ItemType.DoesNotExist:
            return f"Module {self.module_type_id}"


class ShoppingList(models.Model):
    """
    A shopping list for fitting fulfillment.

    Represents items needed to fulfill N copies of a fitting at a location.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Fulfilled'),
        ('complete', 'Complete'),
        ('expired', 'Expired'),
    ]

    character = models.ForeignKey(
        'core.Character',
        on_delete=models.CASCADE,
        related_name='shopping_lists',
    )

    fitting = models.ForeignKey(
        Fitting,
        on_delete=models.CASCADE,
        related_name='shopping_lists',
    )

    quantity = models.IntegerField(default=1, help_text="Number of ships to fit out")

    # Target location
    location_id = models.BigIntegerField(db_index=True, help_text="Station/structure ID")
    location_type = models.CharField(max_length=20, help_text="station, structure, or solar_system")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Cached results
    total_cost = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    items_to_buy = models.JSONField(default=dict, help_text="{type_id: quantity_needed}")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('shopping list')
        verbose_name_plural = _('shopping lists')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['character', 'status']),
            models.Index(fields=['location_id', 'status']),
        ]

    def __str__(self) -> str:
        return f"{self.character.name}: {self.quantity}x {self.fitting.name} at {self.location_id}"


class FittingCharge(models.Model):
    """
    Ammunition or charge loaded in a module slot.

    Represents ammo, scripts, or other consumables loaded into modules.
    """

    fitting = models.ForeignKey(
        Fitting,
        on_delete=models.CASCADE,
        related_name='charges',
    )

    fitting_entry = models.ForeignKey(
        'FittingEntry',
        on_delete=models.CASCADE,
        related_name='charges',
        null=True,
        blank=True,
        help_text="The module this charge is loaded into (optional, can be derived from position)",
    )

    charge_type_id = models.IntegerField(
        db_index=True,
        help_text="ItemType ID for the charge",
    )

    quantity = models.IntegerField(
        default=1,
        help_text="Quantity of charges (for cargo/bay storage)",
    )

    class Meta:
        verbose_name = _('fitting charge')
        verbose_name_plural = _('fitting charges')
        db_table = 'core_fittingcharge'
        ordering = ['fitting', 'fitting_entry']
        indexes = [
            models.Index(fields=['fitting', 'fitting_entry']),
        ]

    def __str__(self) -> str:
        return f"{self.fitting.name}: Charge {self.charge_type_id}"

    @property
    def charge_name(self) -> str:
        """Get charge type name."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.charge_type_id).name
        except ItemType.DoesNotExist:
            return f"Charge {self.charge_type_id}"


class FittingDrone(models.Model):
    """
    Drone or fighter in a fitting.

    Represents drones in the drone bay or fighters in the fighter bay.
    """

    DRONE_BAY = 'drone'
    FIGHTER_BAY = 'fighter'

    BAY_TYPES = [
        (DRONE_BAY, 'Drone Bay'),
        (FIGHTER_BAY, 'Fighter Bay'),
    ]

    fitting = models.ForeignKey(
        Fitting,
        on_delete=models.CASCADE,
        related_name='drones',
    )

    drone_type_id = models.IntegerField(
        db_index=True,
        help_text="ItemType ID for the drone/fighter",
    )

    bay_type = models.CharField(
        max_length=10,
        choices=BAY_TYPES,
        default=DRONE_BAY,
        help_text="Which bay this drone is in",
    )

    quantity = models.IntegerField(
        help_text="Quantity of this drone in bay",
    )

    class Meta:
        verbose_name = _('fitting drone')
        verbose_name_plural = _('fitting drones')
        db_table = 'core_fittingdrone'
        ordering = ['fitting', 'bay_type', 'drone_type_id']
        indexes = [
            models.Index(fields=['fitting', 'bay_type']),
        ]

    def __str__(self) -> str:
        return f"{self.fitting.name}: {self.bay_type} {self.drone_type_id} x{self.quantity}"

    @property
    def drone_name(self) -> str:
        """Get drone type name."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.drone_type_id).name
        except ItemType.DoesNotExist:
            return f"Drone {self.drone_type_id}"


class FittingCargoItem(models.Model):
    """
    Item stored in cargo hold.

    Represents items to be carried in the ship's cargo.
    """

    fitting = models.ForeignKey(
        Fitting,
        on_delete=models.CASCADE,
        related_name='cargo_items',
    )

    item_type_id = models.IntegerField(
        db_index=True,
        help_text="ItemType ID for the cargo item",
    )

    quantity = models.IntegerField(
        help_text="Quantity of this item",
    )

    class Meta:
        verbose_name = _('fitting cargo item')
        verbose_name_plural = _('fitting cargo items')
        db_table = 'core_fittingcargoitem'
        ordering = ['fitting', 'item_type_id']

    def __str__(self) -> str:
        return f"{self.fitting.name}: Cargo {self.item_type_id} x{self.quantity}"

    @property
    def item_name(self) -> str:
        """Get item type name."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.item_type_id).name
        except ItemType.DoesNotExist:
            return f"Item {self.item_type_id}"


class FittingService(models.Model):
    """
    Service module for structure fittings.

    Represents service modules fitted to Upwell structures.
    """

    fitting = models.ForeignKey(
        Fitting,
        on_delete=models.CASCADE,
        related_name='services',
    )

    service_type_id = models.IntegerField(
        db_index=True,
        help_text="ItemType ID for the service module",
    )

    position = models.IntegerField(
        help_text="Service slot position (0-indexed)",
    )

    class Meta:
        verbose_name = _('fitting service')
        verbose_name_plural = _('fitting services')
        db_table = 'core_fittingservice'
        ordering = ['fitting', 'position']
        unique_together = [['fitting', 'position']]

    def __str__(self) -> str:
        return f"{self.fitting.name}: Service slot {self.position}"

    @property
    def service_name(self) -> str:
        """Get service type name."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.service_type_id).name
        except ItemType.DoesNotExist:
            return f"Service {self.service_type_id}"


class FittingIgnore(models.Model):
    """
    User's ignored global fittings.

    Allows users to hide global/shared fittings they don't want to see
    without deleting them (since they don't own them).
    """

    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='ignored_fittings',
    )

    fitting = models.ForeignKey(
        Fitting,
        on_delete=models.CASCADE,
        related_name='ignored_by',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('fitting ignore')
        verbose_name_plural = _('fitting ignores')
        db_table = 'core_fittingignore'
        unique_together = [['user', 'fitting']]
        indexes = [
            models.Index(fields=['user', 'fitting']),
        ]

    def __str__(self) -> str:
        return f"{self.user.username}: {self.fitting.name}"
