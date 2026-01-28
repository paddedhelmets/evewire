"""
EVE Online reference data models.

These models are populated from the SDE (Static Data Export) and provide
reference data for items, locations, factions, corporations, and alliances.

Models use SDE column names via db_column for direct compatibility.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta


class ItemTypeManager(models.Manager):
    """Manager for ItemType queries."""

    def get_by_name(self, name: str):
        """Get an item type by name."""
        return self.get_queryset().filter(name__iexact=name).first()

    def search(self, query: str, group_id: int = None):
        """Search for item types by name."""
        qs = self.get_queryset().filter(name__icontains=query)
        if group_id:
            qs = qs.filter(group_id=group_id)
        return qs


class ItemType(models.Model):
    """
    EVE Online item type (from invTypes table in SDE).

    Represents all types of items in EVE: ships, modules, ammo, materials, etc.
    """

    id = models.BigIntegerField(primary_key=True, db_column='typeID')
    name = models.CharField(max_length=255, db_index=True, db_column='typeName')
    description = models.TextField(blank=True)
    group_id = models.IntegerField(db_index=True, null=True, db_column='groupID')
    mass = models.FloatField(null=True, blank=True)
    volume = models.FloatField(null=True, blank=True)
    capacity = models.FloatField(null=True, blank=True)
    portion_size = models.IntegerField(null=True, blank=True, db_column='portionSize')
    published = models.BooleanField(default=True)

    objects = ItemTypeManager()

    class Meta:
        verbose_name = _('item type')
        verbose_name_plural = _('item types')
        ordering = ['name']
        db_table = 'core_itemtype'

    def __str__(self) -> str:
        return self.name

    @property
    def category_id(self) -> int | None:
        """Get category_id from group (derived relationship)."""
        if self.group_id:
            try:
                group = ItemGroup.objects.get(id=self.group_id)
                return group.category_id
            except ItemGroup.DoesNotExist:
                pass
        return None

    @property
    def is_ship(self) -> bool:
        """Check if this item type is a ship."""
        return self.category_id == 6  # Ships category

    @property
    def is_module(self) -> bool:
        """Check if this item type is a module."""
        return self.category_id == 7  # Modules category


class SolarSystem(models.Model):
    """
    EVE Online solar system (from mapSolarSystems table in SDE).
    """

    id = models.BigIntegerField(primary_key=True, db_column='solarSystemID')
    name = models.CharField(max_length=255, db_index=True, db_column='solarSystemName')
    constellation_id = models.IntegerField(null=True, blank=True, db_column='constellationID')
    region_id = models.IntegerField(db_index=True, null=True, db_column='regionID')
    security_class = models.CharField(max_length=10, blank=True, db_column='securityClass')
    security = models.FloatField(null=True, blank=True)
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    z = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = _('solar system')
        verbose_name_plural = _('solar systems')
        ordering = ['name']
        db_table = 'core_solarsystem'

    def __str__(self) -> str:
        return self.name

    @property
    def security_status(self) -> str:
        """Return formatted security status."""
        if self.security is None:
            return "Unknown"
        if self.security >= 0.5:
            return "Highsec"
        elif self.security > 0:
            return "Lowsec"
        else:
            return "Nullsec"


class Station(models.Model):
    """
    EVE Online station (from staStations table in SDE).
    """

    id = models.BigIntegerField(primary_key=True, db_column='stationID')
    name = models.CharField(max_length=255, db_column='stationName')
    solar_system_id = models.IntegerField(db_index=True, db_column='solarSystemID')
    corporation_id = models.IntegerField(null=True, blank=True, db_column='corporationID')
    region_id = models.IntegerField(null=True, blank=True, db_column='regionID')
    type_id = models.IntegerField(null=True, blank=True, db_column='stationTypeID')
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    z = models.FloatField(null=True, blank=True)
    security = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = _('station')
        verbose_name_plural = _('stations')
        ordering = ['name']
        db_table = 'core_station'

    def __str__(self) -> str:
        return self.name


class Region(models.Model):
    """
    EVE Online region (from mapRegions table in SDE).
    """

    id = models.BigIntegerField(primary_key=True, db_column='regionID')
    name = models.CharField(max_length=255, db_column='regionName')

    class Meta:
        verbose_name = _('region')
        verbose_name_plural = _('regions')
        ordering = ['name']
        db_table = 'core_region'

    def __str__(self) -> str:
        return self.name


class Faction(models.Model):
    """
    EVE Online faction (from chrFactions table in SDE).
    """

    id = models.BigIntegerField(primary_key=True, db_column='factionID')
    name = models.CharField(max_length=255, db_column='factionName')
    description = models.TextField(blank=True)
    solar_system_id = models.IntegerField(null=True, blank=True, db_column='solarSystemID')
    corporation_id = models.IntegerField(null=True, blank=True, db_column='corporationID')

    class Meta:
        verbose_name = _('faction')
        verbose_name_plural = _('factions')
        ordering = ['name']
        db_table = 'core_faction'

    def __str__(self) -> str:
        return self.name


class Corporation(models.Model):
    """
    EVE Online corporation (from crpNPCCorps table in SDE for NPCs).

    Note: Player corporations are fetched from ESI, not SDE.
    This model stores basic corporation info for both NPC and player corps.
    """

    id = models.BigIntegerField(primary_key=True, db_column='corporationID')
    name = models.CharField(max_length=255, db_index=True)
    ticker = models.CharField(max_length=10, blank=True)
    faction_id = models.IntegerField(null=True, blank=True, db_column='factionID')
    is_npc = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('corporation')
        verbose_name_plural = _('corporations')
        ordering = ['name']
        db_table = 'core_corporation'

    def __str__(self) -> str:
        return f"{self.name} [{self.ticker}]"


class Alliance(models.Model):
    """
    EVE Online alliance.

    Note: Alliances are not in the SDE - they are player-created and must be
    fetched from ESI. This model caches alliance information.
    """

    id = models.BigIntegerField(primary_key=True, db_column='allianceID')
    name = models.CharField(max_length=255, db_index=True)
    ticker = models.CharField(max_length=10, blank=True)
    creator_corporation_id = models.IntegerField(null=True, blank=True, db_column='creatorCorporationID')
    creator_id = models.IntegerField(null=True, blank=True, db_column='creatorID')
    date_founded = models.DateField(null=True, blank=True, db_column='startDate')

    class Meta:
        verbose_name = _('alliance')
        verbose_name_plural = _('alliances')
        ordering = ['name']
        db_table = 'core_alliance'

    def __str__(self) -> str:
        return f"{self.name} [{self.ticker}]"


class ItemGroup(models.Model):
    """
    EVE Online item group (from invGroups table in SDE).

    Groups categorize item types (e.g., "Frigates", "Lasers", "Skills").
    """

    id = models.IntegerField(primary_key=True, db_column='groupID')
    name = models.CharField(max_length=255, db_column='groupName')
    category_id = models.IntegerField(db_index=True, null=True, db_column='categoryID')
    published = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('item group')
        verbose_name_plural = _('item groups')
        ordering = ['name']
        db_table = 'core_itemgroup'

    def __str__(self) -> str:
        return self.name


class ItemCategory(models.Model):
    """
    EVE Online item category (from invCategories table in SDE).

    Categories are the top-level classification (e.g., "Ships", "Modules", "Skills").
    """

    id = models.IntegerField(primary_key=True, db_column='categoryID')
    name = models.CharField(max_length=255, db_column='categoryName')
    published = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('item category')
        verbose_name_plural = _('item categories')
        ordering = ['name']
        db_table = 'core_itemcategory'

    def __str__(self) -> str:
        return self.name


class AttributeType(models.Model):
    """
    EVE Online attribute type definition (from dgmAttributeTypes table in SDE).

    Defines what attributes exist and their properties.
    """

    id = models.IntegerField(primary_key=True, db_column='attributeID')
    name = models.CharField(max_length=255, db_column='attributeName')
    description = models.TextField(blank=True)
    default_value = models.FloatField(null=True, blank=True, db_column='defaultValue')
    published = models.BooleanField(default=True)
    display_name = models.CharField(max_length=255, blank=True, db_column='displayName')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconID')
    unit_id = models.IntegerField(null=True, blank=True, db_column='unitID')
    stackable = models.BooleanField(default=True)
    high_is_good = models.BooleanField(default=True, db_column='highIsGood')

    class Meta:
        verbose_name = _('attribute type')
        verbose_name_plural = _('attribute types')
        ordering = ['name']
        db_table = 'core_attributetype'

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"


class TypeAttribute(models.Model):
    """
    EVE Online type attribute (from dgmTypeAttributes table in SDE).

    Stores attribute values for item types. This is how skill prerequisites
    and other item properties are stored.
    """

    id = models.BigAutoField(primary_key=True)
    type_id = models.IntegerField(db_index=True, db_column='typeID')
    attribute_id = models.IntegerField(db_index=True, db_column='attributeID')
    value_int = models.IntegerField(null=True, blank=True, db_column='valueInt')
    value_float = models.FloatField(null=True, blank=True, db_column='valueFloat')

    class Meta:
        verbose_name = _('type attribute')
        verbose_name_plural = _('type attributes')
        unique_together = [['type_id', 'attribute_id']]
        ordering = ['type_id', 'attribute_id']
        db_table = 'core_typeattribute'

    def __str__(self) -> str:
        try:
            item = ItemType.objects.get(id=self.type_id)
            return f"{item.name}: attr_{self.attribute_id} = {self.value_int or self.value_float}"
        except ItemType.DoesNotExist:
            return f"Type {self.type_id}: attr_{self.attribute_id} = {self.value_int or self.value_float}"


class ESICachedMixin(models.Model):
    """
    Mixin for models caching ESI data with staleness tracking.

    Provides common fields and methods for tracking when data was fetched
    from ESI and whether it needs to be refreshed.
    """
    first_seen = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('ok', 'OK'),
            ('error', 'Error'),
            ('stale', 'Stale'),
        ],
        default='pending'
    )
    last_sync_error = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True

    def is_stale(self, max_age_seconds=3600) -> bool:
        """
        Check if cached data is stale.

        Args:
            max_age_seconds: Maximum age in seconds before data is considered stale (default: 1 hour)

        Returns:
            True if data is stale and should be refreshed
        """
        if self.last_sync_status == 'error':
            # Errors are stale after 1 hour (retry quickly)
            return self.last_updated < timezone.now() - timedelta(hours=1)
        return self.last_updated < timezone.now() - timedelta(seconds=max_age_seconds)

    def mark_ok(self):
        """Mark sync as successful."""
        self.last_sync_status = 'ok'
        self.last_sync_error = None
        self.save(update_fields=['last_updated', 'last_sync_status', 'last_sync_error'])

    def mark_error(self, error: str):
        """Mark sync as failed with error message."""
        self.last_sync_status = 'error'
        self.last_sync_error = error
        self.save(update_fields=['last_updated', 'last_sync_status', 'last_sync_error'])

    def mark_stale(self):
        """Mark data as stale (needs refresh)."""
        self.last_sync_status = 'stale'
        self.save(update_fields=['last_updated', 'last_sync_status'])


class Structure(models.Model):
    """
    A player-owned structure in EVE (Citadel, Engineering Complex, etc.).

    Cached from ESI: GET /universe/structures/{structure_id}/

    Structures are NOT in the SDE - they're dynamic player-owned entities.
    This model caches their data to avoid excessive ESI calls.

    Structures are created lazily when first encountered in assets/jobs/etc.
    """
    structure_id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    owner_id = models.IntegerField(db_index=True, help_text='Corporation ID that owns the structure')
    solar_system_id = models.IntegerField(db_index=True)
    position_x = models.FloatField(null=True, blank=True)
    position_y = models.FloatField(null=True, blank=True)
    position_z = models.FloatField(null=True, blank=True)
    type_id = models.IntegerField(db_index=True, help_text='ItemType ID of the structure')

    # Metadata
    first_seen = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_sync_status = models.CharField(max_length=20, default='pending')  # pending, ok, error, inaccessible
    last_sync_error = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Player Structure')
        verbose_name_plural = _('Player Structures')
        ordering = ['name']
        db_table = 'core_structure'

    def __str__(self) -> str:
        return f"{self.name} ({self.structure_id})"

    def is_stale(self) -> bool:
        """
        Check if cached data is stale.

        - Errors are stale after 1 hour (retry quickly)
        - Inaccessible structures (403, no docking access) are never retried
        - Normal data is stale after 7 days
        """
        from django.utils import timezone

        # Inaccessible structures are permanent - never retry
        if self.last_sync_status == 'inaccessible':
            return False

        if self.last_sync_status == 'error':
            return (timezone.now() - self.last_updated).total_seconds() > 3600

        return (timezone.now() - self.last_updated).total_seconds() > 604800  # 7 days


# ============================================================================
# Live Universe Browser - ESI Cache Models
# ============================================================================

class CorporationLPStoreInfo(ESICachedMixin, models.Model):
    """
    Metadata about loyalty point stores from ESI.

    ESI Endpoint: GET /loyalty/stores/
    Cached to track which corporations have LP stores and offer counts.
    """
    corporation_id = models.BigIntegerField(primary_key=True)
    has_loyalty_store = models.BooleanField(default=False)
    total_offers = models.IntegerField(default=0)
    last_offer_ids = models.JSONField(default=list, help_text='For change detection')

    class Meta:
        db_table = 'eve_corporation_lp_store_info'
        verbose_name = _('LP Store Info')
        verbose_name_plural = _('LP Store Infos')
        indexes = [
            models.Index(fields=['has_loyalty_store']),
            models.Index(fields=['last_updated']),
        ]

    def __str__(self) -> str:
        return f"Corp {self.corporation_id}: {self.total_offers} offers"


class LoyaltyStoreOffer(models.Model):
    """
    Individual loyalty point store offers from ESI.

    ESI Endpoint: GET /loyalty/stores/{corporation_id}/offers/
    Cached to avoid repeated ESI calls for store browsing.

    Note: offer_id is NOT globally unique - it's unique per corporation.
    The primary key is an auto-increment id, with a unique constraint on
    (corporation_id, offer_id) together.
    """
    id = models.BigAutoField(primary_key=True)
    offer_id = models.BigIntegerField()
    corporation = models.ForeignKey(
        CorporationLPStoreInfo,
        on_delete=models.CASCADE,
        related_name='offers',
        db_column='corporation_id'
    )
    type_id = models.IntegerField(db_index=True, help_text='Links to SDE InvTypes')
    offer_name = models.TextField(blank=True)
    loyalty_points = models.IntegerField()
    isk_cost = models.BigIntegerField(default=0)
    ak_cost = models.BigIntegerField(default=0, help_text='Alternative currency cost (e.g., PLEX)')
    required_items = models.JSONField(default=list, help_text='Required items for exchange')
    required_standing = models.FloatField(default=0)  # NOTE: ESI does not currently provide this field
    quantity = models.IntegerField(default=1)
    cached_at = models.DateTimeField(auto_now_add=True)

    # Link to SDE (populated in view)
    item_type = None

    class Meta:
        db_table = 'eve_loyalty_store_offers'
        verbose_name = _('LP Store Offer')
        verbose_name_plural = _('LP Store Offers')
        constraints = [
            models.UniqueConstraint(
                fields=['corporation', 'offer_id'],
                name='unique_corp_offer'
            )
        ]
        indexes = [
            models.Index(fields=['corporation', 'cached_at']),
            models.Index(fields=['type_id']),
            models.Index(fields=['cached_at']),
        ]

    def __str__(self) -> str:
        return f"Offer {self.offer_id} (corp {self.corporation_id}): {self.loyalty_points} LP"

    @classmethod
    def from_esi(cls, corporation_id: int, offer_data: dict) -> 'LoyaltyStoreOffer':
        """Create offer from ESI response data."""
        return cls(
            offer_id=offer_data.get('offer_id'),
            corporation_id=corporation_id,
            type_id=offer_data.get('type_id'),
            loyalty_points=offer_data.get('lp_cost', 0),  # ESI uses 'lp_cost'
            isk_cost=offer_data.get('isk_cost', 0),
            ak_cost=offer_data.get('ak_cost', 0),  # Alternative currency (PLEX)
            required_items=offer_data.get('required_items', []),  # Required items for exchange
            required_standing=offer_data.get('required_standing', 0),  # NOTE: ESI doesn't currently provide this
            quantity=offer_data.get('quantity', 1),
        )


class RegionMarketSummary(ESICachedMixin, models.Model):
    """
    Cached market summary for a region from ESI.

    ESI Endpoint: GET /markets/{region_id}/orders/
    Tracks order counts and activity for regional markets.
    """
    region_id = models.IntegerField(primary_key=True)
    total_orders = models.IntegerField(default=0)
    buy_orders = models.IntegerField(default=0)
    sell_orders = models.IntegerField(default=0)
    last_order_ids = models.JSONField(default=list, help_text='Sample of order IDs for change detection')

    class Meta:
        db_table = 'eve_region_market_summary'
        verbose_name = _('Region Market Summary')
        verbose_name_plural = _('Region Market Summaries')
        indexes = [
            models.Index(fields=['-total_orders']),
            models.Index(fields=['last_updated']),
        ]

    def __str__(self) -> str:
        return f"Region {self.region_id}: {self.total_orders} orders"


class ActiveIncursion(ESICachedMixin, models.Model):
    """
    Active incursion from ESI.

    ESI Endpoint: GET /incursions/
    Incursions are dynamic events that spawn and despawn regularly.
    """
    incursion_id = models.CharField(max_length=100, primary_key=True)
    constellation_id = models.IntegerField(db_index=True)
    constellation_name = models.TextField()
    faction_id = models.IntegerField(db_index=True)
    faction_name = models.TextField()
    state = models.TextField(db_index=True, help_text='"mobilizing", "established", "withdrawing"')
    type_id = models.IntegerField(blank=True, null=True, help_text='Incursion type (optional)')
    has_boss = models.BooleanField(default=False)
    staged = models.BooleanField(default=False)

    # SDE links (populated in view)
    constellation = None
    faction = None

    class Meta:
        db_table = 'eve_active_incursions'
        verbose_name = _('Active Incursion')
        verbose_name_plural = _('Active Incursions')
        indexes = [
            models.Index(fields=['state', '-last_updated']),
            models.Index(fields=['faction_id']),
        ]
        ordering = ['-last_updated']

    def __str__(self) -> str:
        return f"Incursion in {self.constellation_name} ({self.state})"


class ActiveWar(ESICachedMixin, models.Model):
    """
    Active war from ESI.

    ESI Endpoint: GET /wars/{war_id}/
    Wars are declared by entities and can last for varying durations.
    """
    war_id = models.BigIntegerField(primary_key=True)
    declared = models.DateTimeField(db_index=True)
    started = models.DateTimeField(blank=True, null=True)
    finished = models.DateTimeField(blank=True, null=True)
    aggressor_id = models.IntegerField(db_index=True)
    aggressor_name = models.TextField()
    ally_id = models.IntegerField(blank=True, null=True)
    ally_name = models.TextField(blank=True, null=True)
    defender_id = models.IntegerField(db_index=True)
    defender_name = models.TextField()
    defender_ally_id = models.IntegerField(blank=True, null=True)
    defender_ally_name = models.TextField(blank=True, null=True)
    mutual = models.BooleanField(default=False)
    open_for_allies = models.BooleanField(default=False)
    prize_ship = models.BigIntegerField(blank=True, null=True)

    # War status
    is_active = models.BooleanField(default=True, db_index=True)
    war_status = models.TextField(default='active', help_text='active, finished, retracted')

    class Meta:
        db_table = 'eve_active_wars'
        verbose_name = _('Active War')
        verbose_name_plural = _('Active Wars')
        indexes = [
            models.Index(fields=['is_active', '-declared']),
            models.Index(fields=['aggressor_id']),
            models.Index(fields=['defender_id']),
        ]
        ordering = ['-declared']

    def __str__(self) -> str:
        return f"War {self.war_id}: {self.aggressor_name} vs {self.defender_name}"


class SovMapSystem(models.Model):
    """
    Sovereignty map by system from ESI.

    ESI Endpoint: GET /sovereignty/map/
    Shows which alliance controls which nullsec systems.
    """
    system_id = models.IntegerField(primary_key=True)
    alliance_id = models.IntegerField(null=True, blank=True, db_index=True)
    corporation_id = models.IntegerField(null=True, blank=True)
    faction_id = models.IntegerField(null=True, blank=True, db_index=True)

    # Metadata
    first_seen = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    # SDE links (populated in view)
    solar_system = None
    alliance = None
    faction = None

    class Meta:
        db_table = 'eve_sov_map_system'
        verbose_name = _('Sov System')
        verbose_name_plural = _('Sov Systems')
        indexes = [
            models.Index(fields=['alliance_id']),
            models.Index(fields=['faction_id']),
            models.Index(fields=['-last_updated']),
        ]

    def __str__(self) -> str:
        owner = self.alliance_id or self.faction_id or 'None'
        return f"System {self.system_id}: Owner {owner}"


class SovCampaign(models.Model):
    """
    Active sovereignty campaigns from ESI.

    ESI Endpoint: GET /sovereignty/campaigns/
    Shows ongoing structure fights for sovereignty.
    """
    campaign_id = models.BigIntegerField(primary_key=True)
    system_id = models.IntegerField(db_index=True, help_text='solar_system_id from ESI')
    constellation_id = models.IntegerField()
    region_id = models.IntegerField(blank=True, null=True, help_text='Not provided by ESI, can be looked up')

    # Score (ESI uses "attackers_score" and "defender_score")
    attackers_score = models.FloatField(default=0.0)
    defender_id = models.IntegerField(db_index=True)
    defender_score = models.FloatField(default=0.0)

    # Campaign details
    event_type = models.TextField(blank=True, default='', help_text='ihub_defense, tcu_defense, etc.')
    start_time = models.DateTimeField(db_index=True)

    # Structure being fought
    structure_id = models.BigIntegerField(blank=True, null=True, help_text='The structure ID being contested')

    # Metadata
    first_seen = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    # SDE links (populated in view)
    solar_system = None
    constellation = None
    region = None
    defender = None

    class Meta:
        db_table = 'eve_sov_campaigns'
        verbose_name = _('Sov Campaign')
        verbose_name_plural = _('Sov Campaigns')
        indexes = [
            models.Index(fields=['system_id']),
            models.Index(fields=['defender_id']),
            models.Index(fields=['start_time']),
            models.Index(fields=['event_type']),
        ]
        ordering = ['-start_time']

    def __str__(self) -> str:
        return f"Campaign {self.campaign_id}: {self.event_type} in {self.system_id}"


class FactionWarfareSystem(models.Model):
    """
    Faction warfare system ownership from ESI.

    ESI Endpoint: GET /fw/systems/
    Shows which faction controls each FW system.
    """
    system_id = models.IntegerField(primary_key=True)
    faction_id = models.IntegerField(null=True, blank=True, db_index=True)
    corporation_id = models.IntegerField(null=True, blank=True)
    solar_system_name = models.TextField()

    # Metadata
    first_seen = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    # SDE links (populated in view)
    solar_system = None
    faction = None

    class Meta:
        db_table = 'eve_fw_systems'
        verbose_name = _('FW System')
        verbose_name_plural = _('FW Systems')
        indexes = [
            models.Index(fields=['faction_id']),
            models.Index(fields=['-last_updated']),
        ]
        ordering = ['solar_system_name']

    def __str__(self) -> str:
        return f"FW System {self.solar_system_name}: Faction {self.faction_id}"


class FactionWarfareStats(models.Model):
    """
    Faction warfare stats from ESI.

    ESI Endpoint: GET /fw/stats/
    Shows kills, victories, and pilot counts for each faction.
    """
    faction_id = models.IntegerField(primary_key=True)
    faction_name = models.TextField()

    # Combat stats
    kills_last_week = models.IntegerField(default=0)
    kills_total = models.IntegerField(default=0)
    victory_points_last_week = models.IntegerField(default=0)
    victory_points_total = models.IntegerField(default=0)

    # Pilots
    pilots_last_week = models.IntegerField(default=0)
    pilots_total = models.IntegerField(default=0)

    # Systems controlled
    systems_controlled = models.IntegerField(default=0)

    # Metadata
    first_seen = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    # SDE links (populated in view)
    faction = None

    class Meta:
        db_table = 'eve_fw_stats'
        verbose_name = _('FW Stats')
        verbose_name_plural = _('FW Stats')
        ordering = ['-victory_points_last_week']

    def __str__(self) -> str:
        return f"FW {self.faction_name}: {self.victory_points_last_week} VP"
