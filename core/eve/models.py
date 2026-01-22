"""
EVE Online reference data models.

These models are populated from the SDE (Static Data Export) and provide
reference data for items, locations, factions, corporations, and alliances.

For MVP, we import only the data needed for the application. Full SDE can be
imported separately for system-wide reference.
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

    id = models.BigIntegerField(primary_key=True)  # typeID
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    group_id = models.IntegerField(db_index=True, null=True)  # FK to invGroups
    mass = models.FloatField(null=True, blank=True)
    volume = models.FloatField(null=True, blank=True)
    capacity = models.FloatField(null=True, blank=True)
    portion_size = models.IntegerField(null=True, blank=True)
    published = models.BooleanField(default=True)

    objects = ItemTypeManager()

    class Meta:
        verbose_name = _('item type')
        verbose_name_plural = _('item types')
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    @property
    def category_id(self) -> int | None:
        """Get category_id from group (derived relationship)."""
        if self.group_id:
            from core.eve.models import ItemGroup
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

    id = models.BigIntegerField(primary_key=True)  # solarSystemID
    name = models.CharField(max_length=255, db_index=True)
    constellation_id = models.IntegerField(null=True, blank=True)
    region_id = models.IntegerField(db_index=True, null=True)
    security_class = models.CharField(max_length=10, blank=True)  # e.g., "1.0", "0.5", "0.0"
    security = models.FloatField(null=True, blank=True)
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    z = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = _('solar system')
        verbose_name_plural = _('solar systems')
        ordering = ['name']

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

    id = models.BigIntegerField(primary_key=True)  # stationID
    name = models.CharField(max_length=255)
    solar_system_id = models.IntegerField(db_index=True)
    corporation_id = models.IntegerField(null=True, blank=True)
    region_id = models.IntegerField(null=True, blank=True)
    type_id = models.IntegerField(null=True, blank=True)  # FK to ItemType
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    z = models.FloatField(null=True, blank=True)
    is_conquerable = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('station')
        verbose_name_plural = _('stations')
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Region(models.Model):
    """
    EVE Online region (from mapRegions table in SDE).
    """

    id = models.BigIntegerField(primary_key=True)  # regionID
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = _('region')
        verbose_name_plural = _('regions')
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Faction(models.Model):
    """
    EVE Online faction (from chrFactions table in SDE).
    """

    id = models.BigIntegerField(primary_key=True)  # factionID
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    solar_system_id = models.IntegerField(null=True, blank=True)
    corporation_id = models.IntegerField(null=True, blank=True)
    is_unique = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('faction')
        verbose_name_plural = _('factions')
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Corporation(models.Model):
    """
    EVE Online corporation (from crpNPCCorps table in SDE for NPCs).

    Note: Player corporations are fetched from ESI, not SDE.
    This model stores basic corporation info for both NPC and player corps.
    """

    id = models.BigIntegerField(primary_key=True)  # corporationID
    name = models.CharField(max_length=255, db_index=True)
    ticker = models.CharField(max_length=10, blank=True)
    faction_id = models.IntegerField(null=True, blank=True)
    is_npc = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('corporation')
        verbose_name_plural = _('corporations')
        ordering = ['name']

    def __str__(self) -> str:
        return f"{self.name} [{self.ticker}]"


class Alliance(models.Model):
    """
    EVE Online alliance.

    Note: Alliances are not in the SDE - they are player-created and must be
    fetched from ESI. This model caches alliance information.
    """

    id = models.BigIntegerField(primary_key=True)  # allianceID
    name = models.CharField(max_length=255, db_index=True)
    ticker = models.CharField(max_length=10, blank=True)
    creator_corporation_id = models.IntegerField(null=True, blank=True)
    creator_id = models.IntegerField(null=True, blank=True)
    date_founded = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = _('alliance')
        verbose_name_plural = _('alliances')
        ordering = ['name']

    def __str__(self) -> str:
        return f"{self.name} [{self.ticker}]"


class ItemGroup(models.Model):
    """
    EVE Online item group (from invGroups table in SDE).

    Groups categorize item types (e.g., "Frigates", "Lasers", "Skills").
    """

    id = models.IntegerField(primary_key=True)  # groupID
    name = models.CharField(max_length=255)
    category_id = models.IntegerField(db_index=True, null=True)  # FK to invCategories
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

    id = models.IntegerField(primary_key=True)  # categoryID
    name = models.CharField(max_length=255)
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

    id = models.IntegerField(primary_key=True)  # attributeID
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    default_value = models.FloatField(null=True, blank=True)
    published = models.BooleanField(default=True)
    display_name = models.CharField(max_length=255, blank=True)
    icon_id = models.IntegerField(null=True, blank=True)
    unit_id = models.IntegerField(null=True, blank=True)
    stackable = models.BooleanField(default=True)
    high_is_good = models.BooleanField(default=True)

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
    type_id = models.IntegerField(db_index=True)  # FK to ItemType
    attribute_id = models.IntegerField(db_index=True)  # FK to AttributeType
    value_int = models.IntegerField(null=True, blank=True)
    value_float = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = _('type attribute')
        verbose_name_plural = _('type attributes')
        unique_together = [['type_id', 'attribute_id']]
        ordering = ['type_id', 'attribute_id']
        db_table = 'core_typeattribute'

    def __str__(self) -> str:
        from core.eve.models import ItemType
        try:
            item = ItemType.objects.get(id=self.type_id)
            return f"{item.name}: attr_{self.attribute_id} = {self.value_int or self.value_float}"
        except ItemType.DoesNotExist:
            return f"Type {self.type_id}: attr_{self.attribute_id} = {self.value_int or self.value_float}"
