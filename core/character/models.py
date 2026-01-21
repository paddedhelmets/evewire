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

        This is a simplified version - full implementation would use SDE data.
        For now, returns 0 (unknown) and can be enhanced later.
        """
        # TODO: Parse from dgmTypeAttributes in SDE
        # Slot 1-5: Attribute implants (INT, PER, CHA, WIL, MEM)
        # Slot 6: Limited Ocular
        # Slot 7: Limited Cybernetic
        # Slot 8: Limited Neural
        # Slot 9: Limited Hardwiring
        # Slot 10: Limited Mental
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
