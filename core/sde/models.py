"""
SDE Browser Models

These are read-only, managed=False models that mirror the EVE SDE tables.
Table names use evesde_ prefix to distinguish from Evewire's core_* tables.

These models are NOT managed by Django migrations.
Schema is maintained by the import_sde_browser management command.

Usage:
    from core.sde.models import InvTypes, InvGroups

    ship = InvTypes.objects.get(id=23857)  # Vexor
    cruisers = InvGroups.objects.get(id=287)  # Cruiser
"""

from django.db import models


# ============================================================================
# Items & Hierarchy
# ============================================================================

class InvTypes(models.Model):
    """
    EVE SDE: invTypes table

    All item types in EVE - ships, modules, ammo, materials, etc.
    """
    type_id = models.BigIntegerField(primary_key=True, db_column='typeID')
    name = models.CharField(max_length=255, db_index=True, db_column='typeName')
    description = models.TextField(blank=True, db_column='description')
    group_id = models.IntegerField(db_index=True, db_column='groupID')
    mass = models.FloatField(null=True, blank=True, db_column='mass')
    volume = models.FloatField(null=True, blank=True, db_column='volume')
    capacity = models.FloatField(null=True, blank=True, db_column='capacity')
    portion_size = models.IntegerField(null=True, blank=True, db_column='portionSize')
    race_id = models.IntegerField(null=True, blank=True, db_column='raceID')
    base_price = models.FloatField(null=True, blank=True, db_column='basePrice')
    published = models.BooleanField(db_column='published')
    market_group_id = models.IntegerField(null=True, blank=True, db_column='marketGroupID')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconID')
    sound_id = models.IntegerField(null=True, blank=True, db_column='soundID')
    graphic_id = models.IntegerField(null=True, blank=True, db_column='graphicID')

    class Meta:
        db_table = 'evesde_invtypes'
        managed = False
        verbose_name = 'Item Type'
        verbose_name_plural = 'Item Types'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_ship(self):
        """Check if this is a ship (category 6)."""
        try:
            return self.group.category_id == 6
        except InvGroups.DoesNotExist:
            return False

    @property
    def is_module(self):
        """Check if this is a module (category 7)."""
        try:
            return self.group.category_id == 7
        except InvGroups.DoesNotExist:
            return False


class InvGroups(models.Model):
    """
    EVE SDE: invGroups table

    Item groups - categories of similar items (e.g., Cruisers, Laser Turrets)
    """
    group_id = models.IntegerField(primary_key=True, db_column='groupID')
    category_id = models.IntegerField(db_index=True, db_column='categoryID')
    group_name = models.CharField(max_length=255, db_column='groupName')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconID')
    use_base_price = models.BooleanField(db_column='useBasePrice')
    anchored = models.BooleanField(db_column='anchored')
    anchorable = models.BooleanField(db_column='anchorable')
    fittable_non_singleton = models.BooleanField(db_column='fittableNonSingleton')
    published = models.BooleanField(db_column='published')

    class Meta:
        db_table = 'evesde_invgroups'
        managed = False
        verbose_name = 'Item Group'
        verbose_name_plural = 'Item Groups'
        ordering = ['group_name']

    def __str__(self):
        return self.group_name


class InvCategories(models.Model):
    """
    EVE SDE: invCategories table

    Top-level item categories (e.g., Ships, Modules, Materials)
    """
    category_id = models.IntegerField(primary_key=True, db_column='categoryID')
    category_name = models.CharField(max_length=255, db_column='categoryName')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconID')
    published = models.BooleanField(db_column='published')

    class Meta:
        db_table = 'evesde_invcategories'
        managed = False
        verbose_name = 'Item Category'
        verbose_name_plural = 'Item Categories'
        ordering = ['category_name']

    def __str__(self):
        return self.category_name


class InvMarketGroups(models.Model):
    """
    EVE SDE: invMarketGroups table

    Market group hierarchy for buy/sell orders
    """
    market_group_id = models.IntegerField(primary_key=True, db_column='marketGroupID')
    parent_group_id = models.IntegerField(null=True, blank=True, db_column='parentGroupID')
    market_group_name = models.CharField(max_length=255, db_column='marketGroupName')
    description = models.TextField(blank=True, db_column='description')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconID')
    has_types = models.BooleanField(db_column='hasTypes')

    class Meta:
        db_table = 'evesde_invmarketgroups'
        managed = False
        verbose_name = 'Market Group'
        verbose_name_plural = 'Market Groups'
        ordering = ['market_group_name']

    def __str__(self):
        return self.market_group_name


class InvMetaGroups(models.Model):
    """
    EVE SDE: invMetaGroups table

    Meta groups define item rarity/tech level
    """
    meta_group_id = models.IntegerField(primary_key=True, db_column='metaGroupID')
    meta_group_name = models.CharField(max_length=255, db_column='metaGroupName')
    description = models.TextField(blank=True, db_column='description')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconID')

    class Meta:
        db_table = 'evesde_invmetagroups'
        managed = False
        verbose_name = 'Meta Group'
        verbose_name_plural = 'Meta Groups'
        ordering = ['meta_group_id']

    def __str__(self):
        return self.meta_group_name


# ============================================================================
# Attributes (Dogma)
# ============================================================================

class DgmAttributeTypes(models.Model):
    """
    EVE SDE: dgmAttributeTypes table

    Definitions of all item attributes (speed, damage, etc.)
    """
    attribute_id = models.IntegerField(primary_key=True, db_column='attributeID')
    attribute_name = models.CharField(max_length=255, db_column='attributeName')
    default_value = models.FloatField(null=True, blank=True, db_column='defaultValue')
    published = models.BooleanField(db_column='published')
    display_name = models.CharField(max_length=255, blank=True, db_column='displayName')
    stackable = models.BooleanField(null=True, blank=True, db_column='stackable')
    high_is_good = models.BooleanField(null=True, blank=True, db_column='highIsGood')
    category_id = models.IntegerField(null=True, blank=True, db_column='categoryID')

    class Meta:
        db_table = 'evesde_dgmattributetypes'
        managed = False
        verbose_name = 'Attribute Type'
        verbose_name_plural = 'Attribute Types'
        ordering = ['attribute_name']

    def __str__(self):
        return self.attribute_name


class DgmTypeAttributes(models.Model):
    """
    EVE SDE: dgmTypeAttributes table

    Actual attribute values for each item type
    """
    type_id = models.IntegerField(db_index=True, db_column='typeID')
    attribute_id = models.IntegerField(db_index=True, db_column='attributeID')
    value_int = models.IntegerField(null=True, blank=True, db_column='valueInt')
    value_float = models.FloatField(null=True, blank=True, db_column='valueFloat')

    class Meta:
        db_table = 'evesde_dgmatypeattributes'
        managed = False
        verbose_name = 'Type Attribute'
        verbose_name_plural = 'Type Attributes'
        # Note: SDE uses composite key (typeID, attributeID)
        # Django doesn't support composite PKs well, so we treat as unkeyed


# ============================================================================
# Universe / Map
# ============================================================================

class MapRegions(models.Model):
    """
    EVE SDE: mapRegions table

    EVE regions
    """
    region_id = models.IntegerField(primary_key=True, db_column='regionID')
    region_name = models.CharField(max_length=255, db_column='regionName')
    faction_id = models.IntegerField(null=True, blank=True, db_column='factionID')
    radius = models.FloatField(null=True, blank=True, db_column='radius')

    class Meta:
        db_table = 'evesde_mapregions'
        managed = False
        verbose_name = 'Region'
        verbose_name_plural = 'Regions'
        ordering = ['region_name']

    def __str__(self):
        return self.region_name


class MapConstellations(models.Model):
    """
    EVE SDE: mapConstellations table

    EVE constellations (groups of solar systems)
    """
    constellation_id = models.IntegerField(primary_key=True, db_column='constellationID')
    region_id = models.IntegerField(db_index=True, db_column='regionID')
    constellation_name = models.CharField(max_length=255, db_column='constellationName')
    x = models.FloatField(null=True, blank=True, db_column='x')
    y = models.FloatField(null=True, blank=True, db_column='y')
    z = models.FloatField(null=True, blank=True, db_column='z')
    x_min = models.FloatField(null=True, blank=True, db_column='xMin')
    x_max = models.FloatField(null=True, blank=True, db_column='xMax')
    y_min = models.FloatField(null=True, blank=True, db_column='yMin')
    y_max = models.FloatField(null=True, blank=True, db_column='yMax')
    z_min = models.FloatField(null=True, blank=True, db_column='zMin')
    z_max = models.FloatField(null=True, blank=True, db_column='zMax')
    faction_id = models.IntegerField(null=True, blank=True, db_column='factionID')
    radius = models.FloatField(null=True, blank=True, db_column='radius')

    class Meta:
        db_table = 'evesde_mapconstellations'
        managed = False
        verbose_name = 'Constellation'
        verbose_name_plural = 'Constellations'
        ordering = ['constellation_name']

    def __str__(self):
        return self.constellation_name


class MapSolarSystems(models.Model):
    """
    EVE SDE: mapSolarSystems table

    Individual solar systems
    """
    system_id = models.IntegerField(primary_key=True, db_column='solarSystemID')
    region_id = models.IntegerField(db_index=True, db_column='regionID')
    constellation_id = models.IntegerField(db_index=True, db_column='constellationID')
    system_name = models.CharField(max_length=255, db_index=True, db_column='solarSystemName')
    x = models.FloatField(null=True, blank=True, db_column='x')
    y = models.FloatField(null=True, blank=True, db_column='y')
    z = models.FloatField(null=True, blank=True, db_column='z')
    x_min = models.FloatField(null=True, blank=True, db_column='xMin')
    x_max = models.FloatField(null=True, blank=True, db_column='xMax')
    y_min = models.FloatField(null=True, blank=True, db_column='yMin')
    y_max = models.FloatField(null=True, blank=True, db_column='yMax')
    z_min = models.FloatField(null=True, blank=True, db_column='zMin')
    z_max = models.FloatField(null=True, blank=True, db_column='zMax')
    luminosity = models.FloatField(null=True, blank=True, db_column='luminosity')
    border = models.BooleanField(null=True, blank=True, db_column='border')
    fringe = models.BooleanField(null=True, blank=True, db_column='fringe')
    corridor = models.BooleanField(null=True, blank=True, db_column='corridor')
    hub = models.BooleanField(null=True, blank=True, db_column='hub')
    international = models.BooleanField(null=True, blank=True, db_column='international')
    regional = models.BooleanField(null=True, blank=True, db_column='regional')
    constellation = models.BooleanField(null=True, blank=True, db_column='constellation')
    security = models.FloatField(null=True, blank=True, db_column='security')
    faction_id = models.IntegerField(null=True, blank=True, db_column='factionID')
    radius = models.FloatField(null=True, blank=True, db_column='radius')
    sun_type_id = models.IntegerField(null=True, blank=True, db_column='solarSystemTypeID')
    security_class = models.CharField(max_length=10, blank=True, db_column='securityClass')

    class Meta:
        db_table = 'evesde_mapsolarsystems'
        managed = False
        verbose_name = 'Solar System'
        verbose_name_plural = 'Solar Systems'
        ordering = ['system_name']

    def __str__(self):
        return self.system_name

    @property
    def security_status(self):
        """Return formatted security status (e.g., '0.5', '1.0', '-1.0')."""
        if self.security is None:
            return 'Unknown'
        if self.security >= 0.45:
            return f'{self.security:.1f}'
        return f'{self.security:.1f}'


# ============================================================================
# Stations
# ============================================================================

class StaStations(models.Model):
    """
    EVE SDE: staStations table

    Stations where players can dock
    """
    station_id = models.IntegerField(primary_key=True, db_column='stationID')
    security = models.FloatField(null=True, blank=True, db_column='security')
    docking_cost_per_volume = models.FloatField(null=True, blank=True, db_column='dockingCostPerVolume')
    max_ship_volume_dockable = models.FloatField(null=True, blank=True, db_column='maxShipVolumeDockable')
    office_rental_cost = models.IntegerField(null=True, blank=True, db_column='officeRentalCost')
    operation_id = models.IntegerField(null=True, blank=True, db_column='operationID')
    station_type_id = models.IntegerField(null=True, blank=True, db_column='stationTypeID')
    corporation_id = models.IntegerField(null=True, blank=True, db_column='corporationID')
    solar_system_id = models.IntegerField(db_index=True, db_column='solarSystemID')
    constellation_id = models.IntegerField(null=True, blank=True, db_column='constellationID')
    region_id = models.IntegerField(null=True, blank=True, db_column='regionID')
    station_name = models.CharField(max_length=255, db_column='stationName')
    x = models.FloatField(null=True, blank=True, db_column='x')
    y = models.FloatField(null=True, blank=True, db_column='y')
    z = models.FloatField(null=True, blank=True, db_column='z')
    reprocessing_efficiency = models.FloatField(null=True, blank=True, db_column='reprocessingEfficiency')
    reprocessing_stations_take = models.FloatField(null=True, blank=True, db_column='reprocessingStationsTake')
    reprocessing_hanger_flag = models.IntegerField(null=True, blank=True, db_column='reprocessingHangerFlag')

    class Meta:
        db_table = 'evesde_stastations'
        managed = False
        verbose_name = 'Station'
        verbose_name_plural = 'Stations'
        ordering = ['station_name']

    def __str__(self):
        return self.station_name


# ============================================================================
# Corporations & Factions
# ============================================================================

class ChrFactions(models.Model):
    """
    EVE SDE: chrFactions table

    Major factions in EVE
    """
    faction_id = models.IntegerField(primary_key=True, db_column='factionID')
    faction_name = models.CharField(max_length=255, db_column='factionName')
    description = models.TextField(blank=True, db_column='description')
    race_ids = models.TextField(blank=True, db_column='raceIDs')
    solar_system_id = models.IntegerField(null=True, blank=True, db_column='solarSystemID')
    corporation_id = models.IntegerField(null=True, blank=True, db_column='corporationID')
    size_factor = models.FloatField(null=True, blank=True, db_column='sizeFactor')
    station_count = models.IntegerField(null=True, blank=True, db_column='stationCount')
    station_system_count = models.IntegerField(null=True, blank=True, db_column='stationSystemCount')
    militia_corporation_id = models.IntegerField(null=True, blank=True, db_column='militiaCorporationID')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconID')

    class Meta:
        db_table = 'evesde_chrfactions'
        managed = False
        verbose_name = 'Faction'
        verbose_name_plural = 'Factions'
        ordering = ['faction_name']

    def __str__(self):
        return self.faction_name


class ChrRaces(models.Model):
    """
    EVE SDE: chrRaces table

    Playable races
    """
    race_id = models.IntegerField(primary_key=True, db_column='raceID')
    race_name = models.CharField(max_length=255, db_column='raceName')
    description = models.TextField(blank=True, db_column='description')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconID')
    short_description = models.CharField(max_length=255, blank=True, db_column='shortDescription')

    class Meta:
        db_table = 'evesde_chrraces'
        managed = False
        verbose_name = 'Race'
        verbose_name_plural = 'Races'
        ordering = ['race_name']

    def __str__(self):
        return self.race_name


class CrpNPCCorporations(models.Model):
    """
    EVE SDE: crpNPCCorporations table

    NPC corporations
    """
    corporation_id = models.IntegerField(primary_key=True, db_column='corporationID')
    corporation_name = models.CharField(max_length=255, db_column='corporationName')
    description = models.TextField(blank=True, db_column='description')
    ticker = models.CharField(max_length=10, blank=True, db_column='ticker')
    ceo_id = models.IntegerField(null=True, blank=True, db_column='ceoID')
    station_id = models.IntegerField(null=True, blank=True, db_column='stationID')
    system_id = models.IntegerField(null=True, blank=True, db_column='solarSystemID')
    race_id = models.IntegerField(null=True, blank=True, db_column='raceID')
    alliance_id = models.IntegerField(null=True, blank=True, db_column='allianceID')
    tax_rate = models.FloatField(null=True, blank=True, db_column='taxRate')
    faction_id = models.IntegerField(null=True, blank=True, db_column='factionID')
    size_factor = models.FloatField(null=True, blank=True, db_column='sizeFactor')
    extent = models.CharField(max_length=255, blank=True, db_column='extent')
    friend_id = models.IntegerField(null=True, blank=True, db_column='friendID')
    enemy_id = models.IntegerField(null=True, blank=True, db_column='enemyID')
    public = models.BooleanField(null=True, blank=True, db_column='public')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconID')

    class Meta:
        db_table = 'evesde_crpnpccorporations'
        managed = False
        verbose_name = 'NPC Corporation'
        verbose_name_plural = 'NPC Corporations'
        ordering = ['corporation_name']

    def __str__(self):
        return self.corporation_name


# ============================================================================
# Additional Items & Variants
# ============================================================================

class InvMetaTypes(models.Model):
    """
    EVE SDE: invMetaTypes table

    Item variants (Tech II, faction, deadspace, etc.) - links to base items
    """
    type_id = models.IntegerField(primary_key=True, db_column='typeID')
    parent_type_id = models.IntegerField(null=True, blank=True, db_column='parentTypeID')
    meta_group_id = models.IntegerField(db_index=True, db_column='metaGroupID')

    class Meta:
        db_table = 'evesde_invmetatypes'
        managed = False
        verbose_name = 'Meta Type'
        verbose_name_plural = 'Meta Types'
        ordering = ['type_id']

    def __str__(self):
        try:
            return f'{self.parent_type.name} ({self.meta_group.meta_group_name})'
        except:
            return f'Type {self.type_id}'


# ============================================================================
# Assets / Graphics
# ============================================================================

class EveIcons(models.Model):
    """
    EVE SDE: eveIcons table

    Icon files for items, ships, stations, etc.
    """
    icon_id = models.IntegerField(primary_key=True, db_column='iconID')
    icon_file = models.CharField(max_length=500, blank=True, db_column='iconFile')
    description = models.TextField(blank=True, db_column='description')

    class Meta:
        db_table = 'evesde_eveicons'
        managed = False
        verbose_name = 'Icon'
        verbose_name_plural = 'Icons'
        ordering = ['icon_id']

    def __str__(self):
        return self.description or f'Icon {self.icon_id}'


class EveGraphics(models.Model):
    """
    EVE SDE: eveGraphics table

    Graphics references for item models
    """
    graphic_id = models.IntegerField(primary_key=True, db_column='graphicID')
    # Note: schema may vary - check actual SDE
    url = models.CharField(max_length=500, blank=True, db_column='url')

    class Meta:
        db_table = 'evesde_evegraphics'
        managed = False
        verbose_name = 'Graphic'
        verbose_name_plural = 'Graphics'
        ordering = ['graphic_id']

    def __str__(self):
        return f'Graphic {self.graphic_id}'


# ============================================================================
# Station Types and Services
# ============================================================================

class StaOperationServices(models.Model):
    """
    EVE SDE: staOperationServices table

    Services available at stations (repair, market, cloning, etc.)
    """
    operation_id = models.IntegerField(primary_key=True, db_column='operationID')
    service_id = models.IntegerField(db_index=True, db_column='serviceID')

    class Meta:
        db_table = 'evesde_staoperationservices'
        managed = False
        verbose_name = 'Station Operation Service'
        verbose_name_plural = 'Station Operation Services'
        ordering = ['operation_id']

    def __str__(self):
        return f'Operation {self.operation_id} - Service {self.service_id}'


class StaOperationTypes(models.Model):
    """
    EVE SDE: staOperationTypes table

    Operation type definitions
    """
    operation_id = models.IntegerField(primary_key=True, db_column='operationID')
    operation_name = models.CharField(max_length=255, blank=True, db_column='operationName')
    description = models.TextField(blank=True, db_column='description')

    class Meta:
        db_table = 'evesde_staoperationtypes'
        managed = False
        verbose_name = 'Station Operation Type'
        verbose_name_plural = 'Station Operation Types'
        ordering = ['operation_id']

    def __str__(self):
        return self.operation_name or f'Operation {self.operation_id}'


class StaStationTypes(models.Model):
    """
    EVE SDE: staStationTypes table

    Station type definitions
    """
    station_type_id = models.IntegerField(primary_key=True, db_column='stationTypeID')
    station_name = models.CharField(max_length=255, blank=True, db_column='stationTypeName')
    description = models.TextField(blank=True, db_column='description')
    dock_entry_x = models.FloatField(null=True, blank=True, db_column='dockEntryX')
    dock_entry_y = models.FloatField(null=True, blank=True, db_column='dockEntryY')
    dock_entry_z = models.FloatField(null=True, blank=True, db_column='dockEntryZ')
    dock_orientation_x = models.FloatField(null=True, blank=True, db_column='dockOrientationX')
    dock_orientation_y = models.FloatField(null=True, blank=True, db_column='dockOrientationY')
    dock_orientation_z = models.FloatField(null=True, blank=True, db_column='dockOrientationZ')
    office_slots = models.IntegerField(null=True, blank=True, db_column='officeSlots')
    reprocessing_efficiency = models.FloatField(null=True, blank=True, db_column='reprocessingEfficiency')

    class Meta:
        db_table = 'evesde_stastationtypes'
        managed = False
        verbose_name = 'Station Type'
        verbose_name_plural = 'Station Types'
        ordering = ['station_name']

    def __str__(self):
        return self.station_name or f'Station Type {self.station_type_id}'

