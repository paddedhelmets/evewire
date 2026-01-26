"""
EVE Online reference data models.

These models are populated from the SDE (Static Data Export) and provide
reference data for items, locations, factions, corporations, and alliances.

Models use SDE column names via db_column for direct compatibility.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


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
    last_sync_status = models.CharField(max_length=20, default='pending')  # pending, ok, error
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
