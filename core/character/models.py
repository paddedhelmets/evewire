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

        Uses implant name heuristic for slot detection.
        For production, you would query dgmTypeAttributes table for 'upgradeCapacity' value.
        """
        from core.eve.models import ItemType

        try:
            item_type = ItemType.objects.get(id=self.type_id)
            name = item_type.name.lower()

            # Attribute implants (slots 1-5)
            # Named by primary attribute they boost
            if 'intelligence' in name or 'logic' in name:
                return 1
            elif 'perception' in name or 'optic' in name:
                return 2
            elif 'charisma' in name or 'social' in name or 'talent' in name:
                return 3
            elif 'willpower' in name or 'clarity' in name or 'command' in name:
                return 4
            elif 'memory' in name or 'cerebral' in name:
                return 5

            # Limited implants (slots 6-10)
            # Named 'Limited X' where X determines slot
            elif 'limited ocular' in name or 'limited δ' in name or 'limited epsilon' in name:
                return 6
            elif 'limited cybernetic' in name or 'limited γ' in name or 'limited gamma' in name:
                return 7
            elif 'limited neural' in name or 'limited β' in name or 'limited beta' in name:
                return 8
            elif 'limited hardwiring' in name or 'limited α' in name or 'limited alpha' in name:
                return 9
            elif 'limited mental' in name or 'limited σ' in name or 'limited sigma' in name:
                return 10

            # Fallback: Check group for implant category
            # Most implants are in group 299 (Cyberimplants)
            # Could further refine by checking type attributes
            return 0

        except ItemType.DoesNotExist:
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
    station_id = models.BigIntegerField()
    system_id = models.IntegerField()
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
    """

    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='skill_plans',
        null=True,
        blank=True,
    )

    # Reference plans are shared templates visible to all users
    is_reference = models.BooleanField(default=False, db_index=True)

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

        Returns dict with:
        - total_entries: total skill entries
        - completed: entries that meet required level
        - in_progress: entries partially trained
        - not_started: entries not started
        - recommended_completed: entries that meet recommended level
        """
        entries = self.get_all_entries()
        character_skills = {s.skill_id: s for s in character.skills.all()}

        total = 0
        completed = 0
        in_progress = 0
        not_started = 0
        recommended_completed = 0

        for entry in entries:
            if not entry.level:
                continue  # Skip entries without required level (recommended-only)

            total += 1
            skill = character_skills.get(entry.skill_id)

            if not skill:
                not_started += 1
            elif skill.skill_level >= entry.level:
                completed += 1
                if entry.recommended_level and skill.skill_level >= entry.recommended_level:
                    recommended_completed += 1
            elif skill.skill_level > 0:
                in_progress += 1
            else:
                not_started += 1

        return {
            'total_entries': total,
            'completed': completed,
            'in_progress': in_progress,
            'not_started': not_started,
            'recommended_completed': recommended_completed,
            'percent_complete': (completed / total * 100) if total > 0 else 0,
        }


class SkillPlanEntry(models.Model):
    """
    A skill requirement within a skill plan.

    Each entry represents a skill with an optional required level
    and recommended level. The recommended level should always be
    higher than the required level.
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

    # Display order for sorting within the plan
    display_order = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('skill plan entry')
        verbose_name_plural = _('skill plan entries')
        ordering = ['skill_plan', 'display_order']
        unique_together = [['skill_plan', 'skill_id']]
        db_table = 'core_skillplanentry'

    def __str__(self) -> str:
        return f"{self.skill_plan.name}: {self.skill_name} -> L{self.level}"

    @property
    def skill_name(self) -> str:
        """Get the skill name from ItemType."""
        from core.eve.models import ItemType
        try:
            return ItemType.objects.get(id=self.skill_id).name
        except ItemType.DoesNotExist:
            return f"Skill {self.skill_id}"

    def clean(self):
        """Validate that recommended_level > level if both are set."""
        from django.core.exceptions import ValidationError

        if self.level and self.recommended_level:
            if self.recommended_level <= self.level:
                raise ValidationError({
                    'recommended_level': 'Recommended level must be greater than required level.'
                })


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
