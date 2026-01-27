"""
Character data models from ESI.

These models store cached ESI data for characters, including skills, assets,
wallet, and market orders.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey
from django.core.exceptions import ObjectDoesNotExist


class AnnotatedCountProperty:
    """
    A descriptor that supports both QuerySet annotation and direct property access.

    When used with .annotate(name=Count('field')), the annotated value is stored
    on the instance and returned. When accessed without annotation, it falls back
    to computing the value dynamically.

    This allows:
    - Efficient counting via annotation in queries
    - Lazy computation when annotation isn't present
    - Transparent access in both templates and code
    """
    def __init__(self, field_name: str):
        self.field_name = field_name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        # Check if annotated value exists on instance
        annotated_value = instance.__dict__.get(f'_{self.field_name}_annotated')
        if annotated_value is not None:
            return annotated_value

        # Fall back to dynamic computation
        # For child_count, count related children
        if self.field_name == 'child_count':
            # Use the related manager's count() method
            # This is efficient for MPTT models
            try:
                return instance.children.count()
            except ObjectDoesNotExist:
                return 0

        raise AttributeError(f"'{type(instance).__name__}' object has no attribute '{self.field_name}'")

    def __set__(self, instance, value):
        # Store annotated value with a private name
        instance.__dict__[f'_{self.field_name}_annotated'] = value


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
    training_start_time = models.DateTimeField(null=True, blank=True)
    finish_date = models.DateTimeField(null=True, blank=True)

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
    def level_roman(self) -> str:
        """Get the target level as Roman numeral."""
        roman_numerals = ['I', 'II', 'III', 'IV', 'V']
        if 1 <= self.finish_level <= 5:
            return roman_numerals[self.finish_level - 1]
        return str(self.finish_level)

    @property
    def is_completed(self) -> bool:
        """Check if this skill has finished training."""
        if not self.finish_date:
            return False  # No finish date means not actively training
        from django.utils import timezone
        return self.finish_date <= timezone.now()

    @property
    def progress_percent(self) -> float:
        """Calculate training progress percentage."""
        from django.utils import timezone

        if not self.finish_date or not self.training_start_time:
            return 0.0  # Can't calculate progress without both dates

        total = self.level_end_sp - self.level_start_sp
        if total == 0:
            return 100.0

        elapsed = timezone.now() - self.training_start_time
        elapsed_seconds = elapsed.total_seconds()
        total_seconds = (self.finish_date - self.training_start_time).total_seconds()

        if total_seconds <= 0:
            return 100.0

        return min(100.0, max(0.0, (elapsed_seconds / total_seconds) * 100))

    @property
    def time_remaining(self):
        """Get remaining time as formatted string (e.g., '12h45m')."""
        from django.utils import timezone

        if not self.finish_date:
            return "Not training"

        remaining = self.finish_date - timezone.now()

        if remaining.total_seconds() <= 0:
            return "0m"

        total_seconds = int(remaining.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h{minutes}m"
        else:
            return f"{minutes}m"

    @property
    def sp_per_hour(self) -> int:
        """
        Calculate SP per hour training rate from character attributes.

        Formula: (primary_attribute + 0.5 * secondary_attribute) SP per minute
        Converts to SP/hour for display.
        """
        from core.eve.models import TypeAttribute

        # Attribute IDs for skill primary/secondary attributes (from SDE)
        PRIMARY_ATTR_ID = 180
        SECONDARY_ATTR_ID = 181

        # Character attribute IDs (these match the values in TypeAttribute for skills)
        CHARISMA_ATTR_ID = 164
        INTELLIGENCE_ATTR_ID = 165
        MEMORY_ATTR_ID = 166
        PERCEPTION_ATTR_ID = 167
        WILLPOWER_ATTR_ID = 168

        try:
            # Get the character's attributes
            attrs = self.character.attributes
        except CharacterAttributes.DoesNotExist:
            return 0

        # Get primary and secondary attribute IDs for this skill
        primary_attr = TypeAttribute.objects.filter(
            type_id=self.skill_id,
            attribute_id=PRIMARY_ATTR_ID
        ).values_list('value_float', flat=True).first()

        secondary_attr = TypeAttribute.objects.filter(
            type_id=self.skill_id,
            attribute_id=SECONDARY_ATTR_ID
        ).values_list('value_float', flat=True).first()

        if not primary_attr or not secondary_attr:
            return 0

        # Map attribute ID to character attribute value
        attr_map = {
            CHARISMA_ATTR_ID: attrs.charisma,
            INTELLIGENCE_ATTR_ID: attrs.intelligence,
            MEMORY_ATTR_ID: attrs.memory,
            PERCEPTION_ATTR_ID: attrs.perception,
            WILLPOWER_ATTR_ID: attrs.willpower,
        }

        primary_value = attr_map.get(primary_attr, 0)
        secondary_value = attr_map.get(secondary_attr, 0)

        # SP per minute = primary + 0.5 * secondary
        sp_per_minute = primary_value + (0.5 * secondary_value)

        # Convert to SP per hour
        return int(sp_per_minute * 60)


class CharacterAttributes(models.Model):
    """
    Character attributes (affect skill training speed).

    From ESI: GET /characters/{character_id}/attributes/

    Attributes:
    - intelligence: Primary for Electronics, Engineering, Science, Mechanics
    - perception: Primary for Spaceship Command, Gunnery, Missiles
    - charisma: Primary for Trade, Social, Leadership, Corporation Management
    - willpower: Primary for Command, Advanced Industry
    - memory: Primary for Industry, Drones, Learning
    """

    character = models.OneToOneField(
        'core.Character',
        on_delete=models.CASCADE,
        related_name='attributes'
    )

    # Attribute values (base + bonuses from implants/boosters)
    intelligence = models.SmallIntegerField(default=20)
    perception = models.SmallIntegerField(default=20)
    charisma = models.SmallIntegerField(default=20)
    willpower = models.SmallIntegerField(default=20)
    memory = models.SmallIntegerField(default=20)

    # Any additional bonuses from implants/boosters
    bonus_remap_available = models.IntegerField(default=0)

    # Cache metadata
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('character attributes')
        verbose_name_plural = _('character attributes')

    def __str__(self) -> str:
        return f"{self.character.name} Attributes"

    @property
    def primary_secondary_pairs(self) -> dict:
        """
        Get common skill training attribute pairs.

        Returns mapping of skill categories to (primary, secondary) attributes.
        """
        return {
            'electronics': ('intelligence', 'memory'),
            'engineering': ('intelligence', 'memory'),
            'science': ('intelligence', 'memory'),
            'mechanics': ('intelligence', 'memory'),
            'spaceship_command': ('perception', 'willpower'),
            'gunnery': ('perception', 'willpower'),
            'missiles': ('perception', 'willpower'),
            'trade': ('charisma', 'intelligence'),
            'social': ('charisma', 'intelligence'),
            'leadership': ('charisma', 'willpower'),
            'corporation_management': ('charisma', 'memory'),
            'industry': ('memory', 'intelligence'),
            'drones': ('memory', 'perception'),
            'resource_processing': ('memory', 'intelligence'),
            'advanced_industry': ('willpower', 'intelligence'),
        }


class CharacterImplant(models.Model):
    """
    An implant installed in a character.

    From ESI: GET /characters/{character_id}/implants/

    Implants occupy slots 1-10 (head) and affect attributes or provide bonuses.
    """

    character = models.ForeignKey(
        'core.Character',
        on_delete=models.CASCADE,
        related_name='implants'
    )

    # ESI implant fields
    type_id = models.IntegerField(db_index=True)  # FK to ItemType

    # Cache metadata
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('character implant')
        verbose_name_plural = _('character implants')
        unique_together = [['character', 'type_id']]
        ordering = ['character', 'type_id']

    def __str__(self) -> str:
        return f"{self.character.name}: {self.type_name}"

    @property
    def type_name(self) -> str:
        """Get the implant type name from ItemType."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.type_id).name
        except ItemType.DoesNotExist:
            return f"Implant {self.type_id}"

    @property
    def slot(self) -> int:
        """
        Determine implant slot (1-10) based on type attributes.

        Implant slots in EVE:
        - Slots 1-5: Attribute implants (Int, Per, Cha, Wil, Mem)
        - Slots 6-10: Limited implants (Ocular, Cybernetic, Neural, Hardwiring, Mental)

        Queries the SDE dgmTypeAttributes table for 'upgradeCapacity' (attribute 331)
        which contains the implant slot number directly from CCP's data.
        """
        from core.eve.models import TypeAttribute

        try:
            # Attribute 331 is 'upgradeCapacity' which contains implant slot
            attr = TypeAttribute.objects.get(type_id=self.type_id, attribute_id=331)
            slot = int(attr.value_int or attr.value_float or 0)
            return slot if 1 <= slot <= 10 else 0
        except TypeAttribute.DoesNotExist:
            return 0


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

    # Annotated count property (supports both annotation and direct access)
    child_count = AnnotatedCountProperty('child_count')

    class Meta:
        verbose_name = _('character asset')
        verbose_name_plural = _('character assets')
        ordering = ['character', 'location_id', 'location_flag']

    def __str__(self) -> str:
        return f"{self.character.name}: {self.type_name} x{self.quantity}"

    @property
    def type_name(self) -> str:
        """Get the item type name from ItemType.

        Uses cached type if available (set by views to avoid N+1 queries).
        """
        # Check if view pre-fetched and cached the type
        if hasattr(self, '_cached_type'):
            return self._cached_type.name

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
        """Get human-readable location name.

        Uses cached location name if available (set by views to avoid N+1 queries).
        """
        # Check if view pre-fetched and cached the location name
        if hasattr(self, '_cached_location_name'):
            return self._cached_location_name

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
        elif self.location_type == 'item':
            # location_id is the item_id of the parent container/ship
            # Look up the parent asset to get its name
            try:
                parent = CharacterAsset.objects.get(item_id=self.location_id, character=self.character)
                return parent.type_name
            except CharacterAsset.DoesNotExist:
                return f"Item {self.location_id}"
        else:
            return "Unknown location"

    def is_blueprint(self) -> bool:
        """
        Check if this asset is a blueprint.

        Uses the is_blueprint_copy field from ESI.
        If is_blueprint_copy is False, it could be a BPO or non-blueprint.
        """
        # Check if item category is Blueprint
        from core.eve.models import ItemCategory
        try:
            item = ItemType.objects.get(id=self.type_id)
            # Blueprint category ID is typically 9 in EVE SDE
            if item.category_id == 9:
                return True
        except ItemType.DoesNotExist:
            pass
        return False

    def blueprint_type(self) -> str | None:
        """
        Determine blueprint type: 'BPO' (original), 'BPC' (copy), or None.

        BPO: is_blueprint_copy = False and item is a blueprint
        BPC: is_blueprint_copy = True

        Note: ESI provides is_blueprint_copy boolean.
        For additional detection, raw_quantity can be used:
        - raw_quantity == -1 or 0: BPO
        - raw_quantity < -1: BPC (runs remaining = abs(raw_quantity))
        """
        if not self.is_blueprint():
            return None

        if self.is_blueprint_copy:
            return 'BPC'
        else:
            return 'BPO'

    def get_value(self) -> float:
        """
        Calculate the value of this asset.

        BPO: Use base_price from ItemType
        BPC: Value is 0 (copies have minimal intrinsic value)
        Normal items: Use sell_price from ItemType

        Returns value in ISK.
        """
        from core.eve.models import ItemType

        try:
            item = ItemType.objects.get(id=self.type_id)
            bp_type = self.blueprint_type()

            if bp_type == 'BPO':
                # Use NPC base price for blueprint originals
                return float(item.base_price or 0)
            elif bp_type == 'BPC':
                # Blueprint copies have minimal intrinsic value
                return 0.0
            else:
                # Normal items use sell price
                return float(item.sell_price or 0) * self.quantity
        except ItemType.DoesNotExist:
            return 0.0


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

    @property
    def type_name(self) -> str:
        """Get the item type name from ItemType."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.type_id).name
        except ItemType.DoesNotExist:
            return f"Type {self.type_id}"

    @property
    def location_name(self) -> str:
        """Get human-readable location name for the transaction.

        Location IDs can be:
        - Stations (60000000-64000000 range): Look up in Station model
        - Structures (1 trillion+): No static data, display as "Structure {id}"
        """
        from core.eve.models import Station

        # Station IDs are typically in the 60M-64M range
        if 60000000 <= self.location_id < 65000000:
            try:
                return Station.objects.get(id=self.location_id).name
            except Station.DoesNotExist:
                return f"Station {self.location_id}"

        # Structure IDs are 1 trillion+
        if self.location_id >= 1000000000000:
            return f"Structure {self.location_id}"

        return f"Location {self.location_id}"


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
    station_id = models.BigIntegerField(null=True, blank=True)
    system_id = models.IntegerField(null=True, blank=True)
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


class MarketOrderHistory(models.Model):
    """
    A historical market order (closed, expired, or cancelled).

    From ESI: GET /characters/{character_id}/orders/history/

    This stores orders that are no longer active but were once open.
    Unlike MarketOrder, these are historical records and don't change.
    """

    character = models.ForeignKey(
        'core.Character',
        on_delete=models.CASCADE,
        related_name='market_order_history'
    )

    # ESI fields (same as MarketOrder)
    order_id = models.BigIntegerField(primary_key=True)
    is_buy_order = models.BooleanField(default=False)
    type_id = models.IntegerField(db_index=True)  # FK to ItemType
    region_id = models.IntegerField(db_index=True)
    station_id = models.BigIntegerField(null=True, blank=True)
    system_id = models.IntegerField(null=True, blank=True)
    volume_remain = models.IntegerField()
    volume_total = models.IntegerField()
    min_volume = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    issued = models.DateTimeField()
    duration = models.IntegerField()  # Days
    range = models.CharField(max_length=20)  # station, region, solar_system, X jumps
    state = models.CharField(max_length=20)  # closed, expired, cancelled
    escrow = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    # Cache metadata
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('market order history')
        verbose_name_plural = _('market order history')
        ordering = ['-issued']

    def __str__(self) -> str:
        action = "BUY" if self.is_buy_order else "SELL"
        return f"{self.character.name}: {action} {self.volume_remain}/{self.volume_total} Type {self.type_id} @ {self.price} [{self.state}]"

    @property
    def type_name(self) -> str:
        """Get the item type name from ItemType."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.type_id).name
        except ItemType.DoesNotExist:
            return f"Type {self.type_id}"

    @property
    def expires_at(self) -> timezone.datetime:
        """Calculate when this order expired."""
        from django.utils import timezone
        return self.issued + timezone.timedelta(days=self.duration)

    @property
    def fill_percent(self) -> float:
        """Calculate how much of the order was filled."""
        if self.volume_total == 0:
            return 0.0
        return ((self.volume_total - self.volume_remain) / self.volume_total) * 100


class SkillPlan(models.Model):
    """
    A skill plan - a collection of skill requirements.

    Skill plans can be hierarchical (parent/child) and represent
    goals like "Fly Loki" or "Max Industrialist". Each plan contains
    skill entries with required and recommended levels.

    Ownership model (matches Fittings):
    - owner=None: Global plan visible to all users (e.g., reference templates)
    - owner=<user>: Private plan only visible to that user
    """

    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)

    # Owner: null = global/shared, set = user-private
    owner = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='skill_plans',
        null=True,
        blank=True,
        help_text="User who owns this plan (null = global/shared plan)",
    )

    # Active/inactive flag for soft deletion
    is_active = models.BooleanField(default=True, db_index=True)

    # Hierarchical structure - allow sub-plans
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    # Display order for sorting
    display_order = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('skill plan')
        verbose_name_plural = _('skill plans')
        ordering = ['display_order', 'name']
        db_table = 'core_skillplan'

    def __str__(self) -> str:
        return self.name

    def get_all_entries(self):
        """Get all entries from this plan and all parent plans."""
        from core.character.models import SkillPlanEntry

        # Start with this plan's entries
        entry_ids = list(self.entries.values_list('id', flat=True))

        # Add entries from parent plans
        parent = self.parent
        while parent:
            entry_ids.extend(parent.entries.values_list('id', flat=True))
            parent = parent.parent

        return SkillPlanEntry.objects.filter(id__in=entry_ids)

    def get_progress_for_character(self, character):
        """
        Calculate progress for a character against this plan.

        SP-based calculation: sums total SP required vs current SP in plan skills.

        Each level entry is counted separately - importing "Amarr Battleship 1",
        "Amarr Battleship 2", "Amarr Battleship 3" creates 3 entries, and the
        SP required for all three levels is summed.

        Returns dict with:
        - Primary entries (user-added goals):
          - primary_total: total primary entries
          - primary_completed: primary entries that meet required level
          - primary_in_progress: primary entries partially trained
          - primary_not_started: primary entries not started
          - primary_percent_complete: percentage of primary entries completed
          - primary_sp_total: total SP required for primary entries
          - primary_sp_completed: SP already trained towards primary entries

        - Prerequisite entries (auto-added required skills):
          - prereq_total: total prerequisite entries
          - prereq_completed: prerequisite entries that meet required level
          - prereq_in_progress: prerequisite entries partially trained
          - prereq_not_started: prerequisite entries not started
          - prereq_percent_complete: percentage of prerequisite entries completed
          - prereq_sp_total: total SP required for prerequisite entries
          - prereq_sp_completed: SP already trained towards prerequisite entries
          - prereq_complete: True if all prerequisites are met (for hiding prereq bar)

        - Legacy compatibility (totals including both)
          - total_entries: total entries (primary + prereq)
          - completed: completed entries (primary + prereq)
          - percent_complete: overall completion percentage
        """
        import math
        from core.eve.models import TypeAttribute, ItemType

        entries = self.get_all_entries()
        character_skills = {s.skill_id: s for s in character.skills.all()}

        # SP calculation constants
        SP_multiplier = 32 ** 0.5

        def sp_for_level(level: int, rank: int) -> int:
            """Calculate SP required for a given skill level."""
            if level == 0:
                return 0
            base = 250 * rank
            geometric_sum = (SP_multiplier ** level - 1) / (SP_multiplier - 1)
            return int(base * geometric_sum)

        # Primary entries tracking
        primary_total = 0
        primary_completed = 0
        primary_in_progress = 0
        primary_not_started = 0
        primary_sp_total = 0
        primary_sp_completed = 0

        # Prerequisite entries tracking
        prereq_total = 0
        prereq_completed = 0
        prereq_in_progress = 0
        prereq_not_started = 0
        prereq_sp_total = 0
        prereq_sp_completed = 0

        for entry in entries:
            if not entry.level:
                continue  # Skip entries without required level (recommended-only)

            skill = character_skills.get(entry.skill_id)

            # Get skill rank for SP calculation (from TypeAttribute attribute_id 275)
            try:
                rank_attr = TypeAttribute.objects.get(type_id=entry.skill_id, attribute_id=275)
                if rank_attr.value_int is not None:
                    rank = rank_attr.value_int
                elif rank_attr.value_float is not None:
                    rank = int(rank_attr.value_float)
                else:
                    rank = 1
            except TypeAttribute.DoesNotExist:
                rank = 1

            target_sp = sp_for_level(entry.level, rank)

            if not skill:
                # Skill not injected
                current_sp = 0
                trained_level = 0
            else:
                current_sp = skill.skillpoints_in_skill
                trained_level = skill.trained_skill_level

            if entry.is_prerequisite:
                # Prerequisite entry tracking
                prereq_total += 1
                prereq_sp_total += target_sp

                if trained_level >= entry.level:
                    prereq_completed += 1
                    prereq_sp_completed += target_sp
                elif trained_level > 0:
                    prereq_in_progress += 1
                    prereq_sp_completed += current_sp
                else:
                    prereq_not_started += 1
            else:
                # Primary entry tracking
                primary_total += 1
                primary_sp_total += target_sp

                if trained_level >= entry.level:
                    primary_completed += 1
                    primary_sp_completed += target_sp
                elif trained_level > 0:
                    primary_in_progress += 1
                    primary_sp_completed += current_sp
                else:
                    primary_not_started += 1

        prereq_complete = (prereq_completed == prereq_total) if prereq_total > 0 else True

        return {
            # Primary entries (user goals)
            'primary_total': primary_total,
            'primary_completed': primary_completed,
            'primary_in_progress': primary_in_progress,
            'primary_not_started': primary_not_started,
            'primary_percent_complete': (primary_completed / primary_total * 100) if primary_total > 0 else 0,
            'primary_sp_total': primary_sp_total,
            'primary_sp_completed': primary_sp_completed,
            'primary_sp_remaining': primary_sp_total - primary_sp_completed,

            # Prerequisite entries (auto-added)
            'prereq_total': prereq_total,
            'prereq_completed': prereq_completed,
            'prereq_in_progress': prereq_in_progress,
            'prereq_not_started': prereq_not_started,
            'prereq_percent_complete': (prereq_completed / prereq_total * 100) if prereq_total > 0 else 0,
            'prereq_sp_total': prereq_sp_total,
            'prereq_sp_completed': prereq_sp_completed,
            'prereq_sp_remaining': prereq_sp_total - prereq_sp_completed,
            'prereq_complete': prereq_complete,

            # Legacy compatibility (totals including both)
            'total_entries': primary_total + prereq_total,
            'completed': primary_completed + prereq_completed,
            'percent_complete': ((primary_completed + prereq_completed) / (primary_total + prereq_total) * 100) if (primary_total + prereq_total) > 0 else 0,
        }

    def ensure_prerequisites(self) -> None:
        """
        Ensure all prerequisite skills for primary entries are present in the plan.

        This method:
        1. Identifies all prerequisite skills for primary (non-prerequisite) entries
        2. Adds missing prerequisites as is_prerequisite=True entries
        3. Removes prerequisite entries that are no longer needed (nothing depends on them)

        Should be called after modifying primary entries in a plan.
        """
        from core.eve.models import TypeAttribute
        from django.db.models import Max

        # Get all primary entries (user-added goals, not prerequisites)
        primary_entries = list(self.entries.filter(is_prerequisite=False))
        # Check all existing entries (both primary and prereq) to avoid duplicates
        existing_entries = set(self.entries.values_list('skill_id', 'level'))

        # Map of skill attribute IDs to their corresponding level attribute IDs
        skill_attribute_map = {
            182: 277,
            183: 278,
            184: 279,
            1285: 1286,
            1289: 1287,
            1290: 1289,  # Note: SDE quirk
        }

        # Collect all required prerequisites using BFS
        required_prereqs = set()  # (skill_id, level) tuples
        skill_ids_to_process = [(e.skill_id, e.level or 0) for e in primary_entries]
        processed = set()

        while skill_ids_to_process:
            skill_id, target_level = skill_ids_to_process.pop(0)

            if (skill_id, target_level) in processed:
                continue
            processed.add((skill_id, target_level))

            # Get prerequisites for this skill
            skill_attrs = TypeAttribute.objects.filter(
                type_id=skill_id,
                attribute_id__in=skill_attribute_map.keys()
            )

            for skill_attr in skill_attrs:
                attr_id = skill_attr.attribute_id
                prereq_skill_id = int(skill_attr.value_float) if skill_attr.value_float else None

                if not prereq_skill_id:
                    continue

                # Get required level
                level_attr_id = skill_attribute_map.get(attr_id)
                if not level_attr_id:
                    continue

                try:
                    level_obj = TypeAttribute.objects.get(
                        type_id=skill_id,
                        attribute_id=level_attr_id
                    )
                    required_level = int(level_obj.value_float) if level_obj.value_float else 1
                except TypeAttribute.DoesNotExist:
                    required_level = 1

                prereq_key = (prereq_skill_id, required_level)

                # Add to required prerequisites
                if prereq_key not in required_prereqs:
                    required_prereqs.add(prereq_key)
                    # Recursively process this prerequisite's prerequisites
                    skill_ids_to_process.append((prereq_skill_id, required_level))

        # Add missing prerequisite entries (all levels 1 through N)
        max_display_order = self.entries.aggregate(max_order=Max('display_order'))['max_order'] or 0
        entries_to_create = []

        for skill_id, max_level in required_prereqs:
            # Add all levels 1 through max_level for correct SP calculation
            for level in range(1, max_level + 1):
                if (skill_id, level) not in existing_entries:
                    max_display_order += 1
                    entries_to_create.append(
                        SkillPlanEntry(
                            skill_plan=self,
                            skill_id=skill_id,
                            level=level,
                            is_prerequisite=True,
                            display_order=max_display_order
                        )
                    )

        if entries_to_create:
            SkillPlanEntry.objects.bulk_create(entries_to_create)

        # Remove orphaned prerequisite entries (no longer needed)
        # Get all skills that are either primary entries or required by primary entries
        all_required_skill_ids = set(entry.skill_id for entry in primary_entries)
        all_required_skill_ids.update(skill_id for skill_id, _ in required_prereqs)

        # Delete prerequisite entries for skills that are no longer needed
        self.entries.filter(
            is_prerequisite=True
        ).exclude(
            skill_id__in=list(all_required_skill_ids)
        ).delete()

    def reorder_by_prerequisites(self) -> None:
        """
        Reorder all skill entries in this plan based on prerequisite tree.

        Uses topological sort to ensure prerequisites come before the skills
        that require them. Updates display_order for all entries.

        This should be called whenever skills are added to a plan to maintain
        proper training order.
        """
        from collections import defaultdict, deque
        from core.eve.models import TypeAttribute

        # Get all entries for this plan
        entries = list(self.entries.all())
        if not entries:
            return

        # Map of skill attribute IDs to their corresponding level attribute IDs
        skill_attribute_map = {
            182: 277,
            183: 278,
            184: 279,
            1285: 1286,
            1289: 1287,
            1290: 1289,
        }

        # Build prerequisite graph: for each (skill_id, level), list its (prereq_skill_id, prereq_level)
        def get_prerequisites_for_skill_level(skill_id: int, target_level: int) -> list:
            """Get list of (skill_id, level) prerequisites for a skill level."""
            prereqs = []
            # Get all prerequisite attributes for this skill
            skill_attrs = TypeAttribute.objects.filter(
                type_id=skill_id,
                attribute_id__in=skill_attribute_map.keys()
            )

            for skill_attr in skill_attrs:
                prereq_skill_id = int(skill_attr.value_float) if skill_attr.value_float else None
                if not prereq_skill_id:
                    continue

                # Get the required level from the corresponding level attribute
                level_attr_id = skill_attribute_map.get(skill_attr.attribute_id)
                if not level_attr_id:
                    continue

                try:
                    level_obj = TypeAttribute.objects.get(
                        type_id=skill_id,
                        attribute_id=level_attr_id
                    )
                    required_level = int(level_obj.value_float) if level_obj.value_float else 0
                except TypeAttribute.DoesNotExist:
                    required_level = 1

                # Only include if prerequisite level <= our target level
                if required_level <= target_level:
                    prereqs.append((prereq_skill_id, required_level))

            return prereqs

        # Build entry_map first: (skill_id, level) -> entry
        # Must be complete before building the graph
        entry_map = {}
        for entry in entries:
            if entry.level:
                key = (entry.skill_id, entry.level)
                entry_map[key] = entry

        # Build prerequisite graph: prereq_key -> list of dependent keys
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        # Build graph by checking each entry's prerequisites
        for entry in entries:
            if not entry.level:
                continue
            key = (entry.skill_id, entry.level)

            # Get prerequisites for this skill level
            prereqs = get_prerequisites_for_skill_level(entry.skill_id, entry.level)

            for prereq_skill_id, prereq_level in prereqs:
                prereq_key = (prereq_skill_id, prereq_level)
                # Only create edge if prerequisite is also in the plan
                if prereq_key in entry_map:
                    graph[prereq_key].append(key)
                    in_degree[key] += 1

        # Track entries that have no prerequisites in the plan (start nodes)
        for entry in entries:
            if entry.level:
                key = (entry.skill_id, entry.level)
                if key not in in_degree:
                    in_degree[key] = 0

        # Topological sort using Kahn's algorithm
        queue = deque([k for k in in_degree if in_degree[k] == 0])
        sorted_order = []

        while queue:
            key = queue.popleft()
            if key in entry_map:
                sorted_order.append(entry_map[key])

            for dependent in graph[key]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Handle any remaining entries (cycles or orphans) - append at end
        processed = set(e.id for e in sorted_order)
        for entry in entries:
            if entry.id not in processed:
                sorted_order.append(entry)

        # Update display_order
        for idx, entry in enumerate(sorted_order):
            entry.display_order = idx
            entry.save(update_fields=['display_order'])


class SkillPlanEntry(models.Model):
    """
    A skill requirement within a skill plan.

    Each entry represents a skill with an optional required level
    and recommended level. The recommended level should always be
    higher than the required level.

    Two taxa of entries:
    - Primary entries (is_prerequisite=False): User-added goals, counted in total SP
    - Prerequisite entries (is_prerequisite=True): Auto-added required skills, not exported
    """

    skill_plan = models.ForeignKey(
        SkillPlan,
        on_delete=models.CASCADE,
        related_name='entries'
    )

    skill_id = models.IntegerField(db_index=True)  # FK to ItemType

    # Required level (1-5) - must be met for plan completion
    level = models.SmallIntegerField(null=True, blank=True)

    # Recommended level (1-5) - optional, higher than required
    recommended_level = models.SmallIntegerField(null=True, blank=True)

    # Whether this entry is a prerequisite (auto-added) vs primary goal (user-added)
    is_prerequisite = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this is an auto-added prerequisite skill, False if user-added goal"
    )

    # Display order for sorting within the plan
    display_order = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('skill plan entry')
        verbose_name_plural = _('skill plan entries')
        ordering = ['skill_plan', 'display_order']
        unique_together = [['skill_plan', 'skill_id', 'level']]
        db_table = 'core_skillplanentry'

    def __str__(self) -> str:
        prereq_prefix = "📦 " if self.is_prerequisite else ""
        return f"{prereq_prefix}{self.skill_plan.name}: {self.skill_name} -> L{self.level}"

    @property
    def skill_name(self) -> str:
        """Get the skill name from ItemType."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.skill_id).name
        except ItemType.DoesNotExist:
            return f"Skill {self.skill_id}"

    @property
    def level_roman(self) -> str:
        """Get level as Roman numeral (I, II, III, IV, V)."""
        roman_numerals = ['I', 'II', 'III', 'IV', 'V']
        if self.level and 1 <= self.level <= 5:
            return roman_numerals[self.level - 1]
        return ''

    def clean(self):
        """Validate that recommended_level > level if both are set."""
        from django.core.exceptions import ValidationError

        if self.level and self.recommended_level:
            if self.recommended_level <= self.level:
                raise ValidationError({
                    'recommended_level': 'Recommended level must be greater than required level.'
                })


class SkillPlanIgnore(models.Model):
    """
    User's ignored global skill plans.

    Allows users to hide global/shared plans they don't want to see
    without deleting them (since they don't own them).
    """

    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='ignored_skill_plans',
    )

    plan = models.ForeignKey(
        SkillPlan,
        on_delete=models.CASCADE,
        related_name='ignored_by',
    )

    class Meta:
        verbose_name = _('skill plan ignore')
        verbose_name_plural = _('skill plan ignores')
        unique_together = [['user', 'plan']]
        db_table = 'core_skillplanignore'

    def __str__(self) -> str:
        return f"{self.user.username} ignores {self.plan.name}"


class IndustryJob(models.Model):
    """
    An industry job for a character.

    From ESI: GET /characters/{character_id}/industry/jobs/

    Industry Activity Types:
    - 1: Manufacturing
    - 2: Researching Technology (TE)
    - 3: Researching Technology (TE - legacy)
    - 4: Researching Material Efficiency (ME)
    - 5: Copying
    - 6: Duplicating (legacy)
    - 7: Reverse Engineering
    - 8: Invention

    Job Status Values:
    - 1: active
    - 2: paused
    - 102: cancelled
    - 104: delivered
    - 105: failed
    - 999: unknown
    """

    character = models.ForeignKey(
        'core.Character',
        on_delete=models.CASCADE,
        related_name='industry_jobs'
    )

    # ESI job fields
    job_id = models.BigIntegerField(primary_key=True)

    # Job status and activity
    activity_id = models.SmallIntegerField(db_index=True)
    status = models.SmallIntegerField(db_index=True)  # 1=active, 2=paused, 102=cancelled, etc.

    # Blueprint info
    blueprint_id = models.BigIntegerField(db_index=True)
    blueprint_type_id = models.IntegerField(db_index=True)  # FK to ItemType
    blueprint_location_id = models.BigIntegerField(null=True, blank=True)

    # Output product (for manufacturing/invention)
    product_type_id = models.IntegerField(null=True, blank=True, db_index=True)  # FK to ItemType

    # Location
    station_id = models.BigIntegerField(db_index=True)
    solar_system_id = models.IntegerField(db_index=True)

    # Timing
    start_date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField(db_index=True)
    pause_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    completed_character_id = models.IntegerField(null=True, blank=True)

    # Job details
    runs = models.IntegerField()
    cost = models.DecimalField(max_digits=20, decimal_places=2)

    # Invention-specific fields
    probability = models.FloatField(null=True, blank=True)
    attempts = models.SmallIntegerField(null=True, blank=True)
    success = models.BooleanField(null=True, blank=True)

    # Cache metadata
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('industry job')
        verbose_name_plural = _('industry jobs')
        ordering = ['-start_date']

    def __str__(self) -> str:
        return f"{self.character.name}: {self.activity_name} - {self.product_name}"

    @property
    def activity_name(self) -> str:
        """Get human-readable activity name."""
        ACTIVITY_NAMES = {
            1: 'Manufacturing',
            2: 'TE Research',
            3: 'TE Research',
            4: 'ME Research',
            5: 'Copying',
            6: 'Duplicating',
            7: 'Reverse Engineering',
            8: 'Invention',
        }
        return ACTIVITY_NAMES.get(self.activity_id, f'Activity {self.activity_id}')

    @property
    def status_name(self) -> str:
        """Get human-readable status name."""
        STATUS_NAMES = {
            1: 'active',
            2: 'paused',
            102: 'cancelled',
            104: 'delivered',
            105: 'failed',
            999: 'unknown',
        }
        return STATUS_NAMES.get(self.status, f'status_{self.status}')

    @property
    def blueprint_type_name(self) -> str:
        """Get the blueprint type name from ItemType."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.blueprint_type_id).name
        except ItemType.DoesNotExist:
            return f"BPO {self.blueprint_type_id}"

    @property
    def product_name(self) -> str:
        """Get the product type name from ItemType."""
        if not self.product_type_id:
            return self.blueprint_type_name

        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.product_type_id).name
        except ItemType.DoesNotExist:
            return f"Product {self.product_type_id}"

    @property
    def is_active(self) -> bool:
        """Check if this job is currently active."""
        from django.utils import timezone
        return self.status == 1 and self.end_date > timezone.now()

    @property
    def is_completed(self) -> bool:
        """Check if this job has completed."""
        return self.status == 104  # delivered

    @property
    def progress_percent(self) -> float:
        """Calculate job progress percentage."""
        from django.utils import timezone

        if self.status != 1:  # Not active
            if self.status == 104:
                return 100.0
            return 0.0

        now = timezone.now()
        if now >= self.end_date:
            return 100.0
        if now <= self.start_date:
            return 0.0

        total_seconds = (self.end_date - self.start_date).total_seconds()
        elapsed_seconds = (now - self.start_date).total_seconds()

        if total_seconds <= 0:
            return 0.0

        return min(100.0, max(0.0, (elapsed_seconds / total_seconds) * 100))

    @property
    def time_remaining(self):
        """Get remaining time as timedelta."""
        from django.utils import timezone
        remaining = self.end_date - timezone.now()
        return remaining if remaining.total_seconds() > 0 else timezone.timedelta(0)

    @property
    def is_expiring_soon(self) -> bool:
        """Check if this active job will complete within 1 hour."""
        from django.utils import timezone
        if self.status != 1:  # Not active
            return False
        remaining = self.end_date - timezone.now()
        return remaining.total_seconds() <= 3600  # 1 hour


class Contract(models.Model):
    """
    A contract for a character.

    From ESI: GET /characters/{character_id}/contracts/

    Contract Types:
    - item_exchange: Exchange items and/or ISK
    - auction: Auction with buyout option
    - courier: Courier contract (move items)
    - loan: Loan contract

    Contract Status:
    - outstanding: Available to be accepted
    - in_progress: Accepted, in progress
    - finished_issuer: Completed, awaiting issuer completion
    - finished_contractor: Completed, awaiting contractor completion
    - finished: Fully completed
    - cancelled: Cancelled by issuer
    - rejected: Rejected by contractor
    - failed: Failed (e.g., courier contract expired)

    Availability:
    - public: Public contract
    - personal: Personal contract
    - corporation: Corporation contract
    - alliance: Alliance contract
    """

    character = models.ForeignKey(
        'core.Character',
        on_delete=models.CASCADE,
        related_name='contracts'
    )

    # ESI contract fields
    contract_id = models.BigIntegerField(primary_key=True)
    type = models.CharField(max_length=20)  # item_exchange, auction, courier, loan
    status = models.CharField(max_length=25, db_index=True)  # outstanding, in_progress, finished, etc.
    title = models.CharField(max_length=255, blank=True)

    for_corporation = models.BooleanField(default=False)
    availability = models.CharField(max_length=20)  # public, personal, corporation, alliance

    date_issued = models.DateTimeField(db_index=True)
    date_expired = models.DateTimeField(db_index=True)
    date_accepted = models.DateTimeField(null=True, blank=True)
    date_completed = models.DateTimeField(null=True, blank=True)

    issuer_id = models.IntegerField(db_index=True)
    issuer_corporation_id = models.IntegerField()
    assignee_id = models.IntegerField(null=True, blank=True)
    acceptor_id = models.IntegerField(null=True, blank=True)

    days_to_complete = models.IntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    reward = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    collateral = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    buyout = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    volume = models.FloatField(null=True, blank=True)

    # Cache metadata
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('contract')
        verbose_name_plural = _('contracts')
        ordering = ['-date_issued']

    def __str__(self) -> str:
        return f"{self.character.name}: {self.type} contract {self.contract_id} [{self.status}]"

    @property
    def type_name(self) -> str:
        """Get human-readable type name."""
        TYPE_NAMES = {
            'item_exchange': 'Item Exchange',
            'auction': 'Auction',
            'courier': 'Courier',
            'loan': 'Loan',
        }
        return TYPE_NAMES.get(self.type, f'Type {self.type}')

    @property
    def status_name(self) -> str:
        """Get human-readable status name."""
        STATUS_NAMES = {
            'outstanding': 'Outstanding',
            'in_progress': 'In Progress',
            'finished_issuer': 'Finished (Issuer)',
            'finished_contractor': 'Finished (Contractor)',
            'finished': 'Completed',
            'cancelled': 'Cancelled',
            'rejected': 'Rejected',
            'failed': 'Failed',
        }
        return STATUS_NAMES.get(self.status, self.status.replace('_', ' ').title())

    @property
    def availability_name(self) -> str:
        """Get human-readable availability name."""
        AVAILABILITY_NAMES = {
            'public': 'Public',
            'personal': 'Personal',
            'corporation': 'Corporation',
            'alliance': 'Alliance',
        }
        return AVAILABILITY_NAMES.get(self.availability, self.availability.title())

    @property
    def is_active(self) -> bool:
        """Check if this contract is active (outstanding or in_progress)."""
        return self.status in ('outstanding', 'in_progress')

    @property
    def is_completed(self) -> bool:
        """Check if this contract is completed."""
        return self.status in ('finished_issuer', 'finished_contractor', 'finished')

    @property
    def is_failed(self) -> bool:
        """Check if this contract failed."""
        return self.status in ('cancelled', 'rejected', 'failed')

    @property
    def is_expired(self) -> bool:
        """Check if this contract has expired."""
        from django.utils import timezone
        return self.date_expired <= timezone.now()

    @property
    def expires_soon(self) -> bool:
        """Check if this contract expires within 24 hours."""
        from django.utils import timezone
        if not self.is_active:
            return False
        remaining = self.date_expired - timezone.now()
        return remaining.total_seconds() <= 86400  # 24 hours

    @property
    def total_value(self) -> float:
        """Get total value of contract (price + reward + collateral + buyout)."""
        total = 0.0
        if self.price:
            total += float(self.price)
        if self.reward:
            total += float(self.reward)
        if self.collateral:
            total += float(self.collateral)
        if self.buyout:
            total += float(self.buyout)
        return total

    @property
    def items_count(self) -> int:
        """Get number of items in this contract."""
        return self.items.count()

    @property
    def included_items_value(self) -> float:
        """Get total estimated market value of included items (what you receive)."""
        return sum(
            item.item_value
            for item in self.items.filter(is_included=True)
        )

    @property
    def requested_items_value(self) -> float:
        """Get total estimated market value of requested items (what you provide)."""
        return sum(
            item.item_value
            for item in self.items.filter(is_included=False)
        )

    @property
    def contract_price_paid(self) -> float:
        """Get the total ISK paid for this contract (price - reward for issuer)."""
        price = float(self.price) if self.price else 0.0
        reward = float(self.reward) if self.reward else 0.0
        return price - reward

    @property
    def profit_loss(self) -> float:
        """
        Calculate profit/loss for completed item_exchange contracts.

        For the issuer (owner):
        - Received value = requested_items_value + price_paid
        - Given value = included_items_value + reward
        - Profit = Received value - Given value

        For the contractor (acceptor):
        - Received value = included_items_value + reward
        - Given value = requested_items_value + price_paid
        - Profit = Received value - Given value

        Returns None for non-item_exchange or non-completed contracts.
        """
        if self.type != 'item_exchange' or not self.is_completed:
            return None

        # Calculate value received vs given
        # Positive means profit, negative means loss
        received = self.requested_items_value + self.contract_price_paid
        given = self.included_items_value + (float(self.reward) if self.reward else 0.0)
        return received - given

    @property
    def profit_pct(self) -> float:
        """Calculate profit percentage. Returns None if not applicable."""
        profit = self.profit_loss
        if profit is None:
            return None

        cost = self.included_items_value + (float(self.reward) if self.reward else 0.0)
        if cost == 0:
            return None
        return (profit / cost) * 100


class ContractItem(models.Model):
    """
    An item in a contract.

    From ESI: GET /characters/{character_id}/contracts/{contract_id}/items/
    """

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='items'
    )

    # ESI item fields
    item_id = models.BigIntegerField(db_index=True)
    type_id = models.IntegerField(db_index=True)  # FK to ItemType
    quantity = models.IntegerField(default=1)
    is_included = models.BooleanField(default=True)
    is_singleton = models.BooleanField(default=False)
    raw_quantity = models.IntegerField(null=True, blank=True)

    # Cache metadata
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('contract item')
        verbose_name_plural = _('contract items')
        unique_together = [['contract', 'item_id']]
        ordering = ['contract', 'type_id']

    def __str__(self) -> str:
        return f"{self.contract.contract_id}: {self.type_name} x{self.quantity}"

    @property
    def type_name(self) -> str:
        """Get the item type name from ItemType."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.type_id).name
        except ItemType.DoesNotExist:
            return f"Type {self.type_id}"

    @property
    def item_value(self) -> float:
        """Get the estimated market value of this item (quantity * sell_price)."""
        from core.eve.models import ItemType
        try:
            item_type = ItemType.objects.get(id=self.type_id)
            price = float(item_type.sell_price) if item_type.sell_price else 0.0
            return float(self.quantity) * price
        except ItemType.DoesNotExist:
            return 0.0
