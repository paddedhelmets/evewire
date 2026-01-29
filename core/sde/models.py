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
    type_id = models.BigIntegerField(primary_key=True, db_column='typeid')
    name = models.CharField(max_length=255, db_index=True, db_column='typename')
    description = models.TextField(blank=True, db_column='description')
    group = models.ForeignKey('InvGroups', on_delete=models.DO_NOTHING, db_column='groupid', related_name='types')
    mass = models.FloatField(null=True, blank=True, db_column='mass')
    volume = models.FloatField(null=True, blank=True, db_column='volume')
    capacity = models.FloatField(null=True, blank=True, db_column='capacity')
    portion_size = models.IntegerField(null=True, blank=True, db_column='portionsize')
    race = models.ForeignKey('ChrRaces', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='raceid', related_name='types')
    base_price = models.FloatField(null=True, blank=True, db_column='baseprice')
    published = models.BooleanField(db_column='published')
    market_group = models.ForeignKey('InvMarketGroups', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='marketgroupid', related_name='types')
    icon = models.ForeignKey('EveIcons', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='iconid', related_name='types')
    sound_id = models.IntegerField(null=True, blank=True, db_column='soundid')
    graphic = models.ForeignKey('EveGraphics', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='graphicid', related_name='types')

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
        return self.group.category_id == 6 if self.group else False

    @property
    def is_module(self):
        """Check if this is a module (category 7)."""
        return self.group.category_id == 7 if self.group else False


class InvGroups(models.Model):
    """
    EVE SDE: invGroups table

    Item groups - categories of similar items (e.g., Cruisers, Laser Turrets)
    """
    group_id = models.IntegerField(primary_key=True, db_column='groupid')
    category = models.ForeignKey('InvCategories', on_delete=models.DO_NOTHING, db_column='categoryid', related_name='groups')
    group_name = models.CharField(max_length=255, db_column='groupname')
    icon = models.ForeignKey('EveIcons', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='iconid', related_name='groups')
    use_base_price = models.BooleanField(db_column='usebaseprice')
    anchored = models.BooleanField(db_column='anchored')
    anchorable = models.BooleanField(db_column='anchorable')
    fittable_non_singleton = models.BooleanField(db_column='fittablenonsingleton')
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
    category_id = models.IntegerField(primary_key=True, db_column='categoryid')
    category_name = models.CharField(max_length=255, db_column='categoryname')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconid')
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
    market_group_id = models.IntegerField(primary_key=True, db_column='marketgroupid')
    parent_group_id = models.IntegerField(null=True, blank=True, db_column='parentgroupid')
    market_group_name = models.CharField(max_length=255, db_column='marketgroupname')
    description = models.TextField(blank=True, db_column='description')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconid')
    has_types = models.BooleanField(db_column='hastypes')

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
    meta_group_id = models.IntegerField(primary_key=True, db_column='metagroupid')
    meta_group_name = models.CharField(max_length=255, db_column='metagroupname')
    description = models.TextField(blank=True, db_column='description')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconid')

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
    attribute_id = models.IntegerField(primary_key=True, db_column='attributeid')
    attribute_name = models.CharField(max_length=255, db_column='attributename')
    default_value = models.FloatField(null=True, blank=True, db_column='defaultvalue')
    published = models.BooleanField(db_column='published')
    display_name = models.CharField(max_length=255, blank=True, db_column='displayname')
    stackable = models.BooleanField(null=True, blank=True, db_column='stackable')
    high_is_good = models.BooleanField(null=True, blank=True, db_column='highisgood')
    category_id = models.IntegerField(null=True, blank=True, db_column='categoryid')

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
    # Primary key: Django requires one, using the id column from the database
    id = models.AutoField(primary_key=True, db_column='id')
    type = models.ForeignKey('InvTypes', on_delete=models.DO_NOTHING, db_column='typeid', related_name='attributes')
    attribute = models.ForeignKey('DgmAttributeTypes', on_delete=models.DO_NOTHING, db_column='attributeid', related_name='type_attributes')
    value_int = models.IntegerField(null=True, blank=True, db_column='valueint')
    value_float = models.FloatField(null=True, blank=True, db_column='valuefloat')

    class Meta:
        db_table = 'evesde_dgmtypeattributes'
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
    region_id = models.IntegerField(primary_key=True, db_column='regionid')
    region_name = models.CharField(max_length=255, db_column='regionname')
    faction_id = models.IntegerField(null=True, blank=True, db_column='factionid')
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
    constellation_id = models.IntegerField(primary_key=True, db_column='constellationid')
    region = models.ForeignKey('MapRegions', on_delete=models.DO_NOTHING, db_column='regionid', related_name='constellations')
    constellation_name = models.CharField(max_length=255, db_column='constellationname')
    x = models.FloatField(null=True, blank=True, db_column='x_coord')
    y = models.FloatField(null=True, blank=True, db_column='y_coord')
    z = models.FloatField(null=True, blank=True, db_column='z_coord')
    x_min = models.FloatField(null=True, blank=True, db_column='xmin_coord')
    x_max = models.FloatField(null=True, blank=True, db_column='xmax_coord')
    y_min = models.FloatField(null=True, blank=True, db_column='ymin_coord')
    y_max = models.FloatField(null=True, blank=True, db_column='ymax_coord')
    z_min = models.FloatField(null=True, blank=True, db_column='zmin_coord')
    z_max = models.FloatField(null=True, blank=True, db_column='zmax_coord')
    faction = models.ForeignKey('ChrFactions', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='factionid', related_name='constellations')
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
    system_id = models.IntegerField(primary_key=True, db_column='solarsystemid')
    region = models.ForeignKey('MapRegions', on_delete=models.DO_NOTHING, db_column='regionid', related_name='systems')
    constellation = models.ForeignKey('MapConstellations', on_delete=models.DO_NOTHING, db_column='constellationid', related_name='systems')
    system_name = models.CharField(max_length=255, db_index=True, db_column='solarsystemname')
    x = models.FloatField(null=True, blank=True, db_column='x_coord')
    y = models.FloatField(null=True, blank=True, db_column='y_coord')
    z = models.FloatField(null=True, blank=True, db_column='z_coord')
    x_min = models.FloatField(null=True, blank=True, db_column='xmin_coord')
    x_max = models.FloatField(null=True, blank=True, db_column='xmax_coord')
    y_min = models.FloatField(null=True, blank=True, db_column='ymin_coord')
    y_max = models.FloatField(null=True, blank=True, db_column='ymax_coord')
    z_min = models.FloatField(null=True, blank=True, db_column='zmin_coord')
    z_max = models.FloatField(null=True, blank=True, db_column='zmax_coord')
    luminosity = models.FloatField(null=True, blank=True, db_column='luminosity')
    border = models.BooleanField(null=True, blank=True, db_column='border')
    fringe = models.BooleanField(null=True, blank=True, db_column='fringe')
    corridor = models.BooleanField(null=True, blank=True, db_column='corridor')
    hub = models.BooleanField(null=True, blank=True, db_column='hub')
    international = models.BooleanField(null=True, blank=True, db_column='international')
    regional = models.BooleanField(null=True, blank=True, db_column='regional')
    is_constellation = models.BooleanField(null=True, blank=True, db_column='constellation')
    security = models.FloatField(null=True, blank=True, db_column='security')
    faction = models.ForeignKey('ChrFactions', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='factionid', related_name='systems')
    radius = models.FloatField(null=True, blank=True, db_column='radius')
    sun_type = models.ForeignKey('InvTypes', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='suntypeid', related_name='star_systems')
    security_class = models.CharField(max_length=10, blank=True, db_column='securityclass')

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
    station_id = models.IntegerField(primary_key=True, db_column='stationid')
    security = models.FloatField(null=True, blank=True, db_column='security')
    docking_cost_per_volume = models.FloatField(null=True, blank=True, db_column='dockingcostpervolume')
    max_ship_volume_dockable = models.FloatField(null=True, blank=True, db_column='maxshipvolumedockable')
    office_rental_cost = models.IntegerField(null=True, blank=True, db_column='officerentalcost')
    operation_id = models.IntegerField(null=True, blank=True, db_column='operationid')
    station_type = models.ForeignKey('InvTypes', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='stationtypeid', related_name='stations_of_type')
    corporation = models.ForeignKey('CrpNPCCorporations', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='corporationid', related_name='stations')
    solar_system = models.ForeignKey('MapSolarSystems', on_delete=models.DO_NOTHING, db_column='solarsystemid', related_name='stations')
    constellation = models.ForeignKey('MapConstellations', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='constellationid', related_name='stations')
    region = models.ForeignKey('MapRegions', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='regionid', related_name='stations')
    station_name = models.CharField(max_length=255, db_column='stationname')
    x = models.FloatField(null=True, blank=True, db_column='x_coord')
    y = models.FloatField(null=True, blank=True, db_column='y_coord')
    z = models.FloatField(null=True, blank=True, db_column='z_coord')
    reprocessing_efficiency = models.FloatField(null=True, blank=True, db_column='reprocessingefficiency')
    reprocessing_stations_take = models.FloatField(null=True, blank=True, db_column='reprocessingstationstake')
    reprocessing_hanger_flag = models.IntegerField(null=True, blank=True, db_column='reprocessinghangarflag')

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
    faction_id = models.IntegerField(primary_key=True, db_column='factionid')
    faction_name = models.CharField(max_length=255, db_column='factionname')
    description = models.TextField(blank=True, db_column='description')
    race_ids = models.TextField(blank=True, db_column='raceids')
    solar_system_id = models.IntegerField(null=True, blank=True, db_column='solarsystemid')
    corporation_id = models.IntegerField(null=True, blank=True, db_column='corporationid')
    size_factor = models.FloatField(null=True, blank=True, db_column='sizefactor')
    station_count = models.IntegerField(null=True, blank=True, db_column='stationcount')
    station_system_count = models.IntegerField(null=True, blank=True, db_column='stationsystemcount')
    militia_corporation_id = models.IntegerField(null=True, blank=True, db_column='militiacorporationid')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconid')

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
    race_id = models.IntegerField(primary_key=True, db_column='raceid')
    race_name = models.CharField(max_length=255, db_column='racename')
    description = models.TextField(blank=True, db_column='description')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconid')
    short_description = models.CharField(max_length=255, blank=True, db_column='shortdescription')

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
    Note: corporation names are stored in InvNames table, not here
    """
    corporation_id = models.IntegerField(primary_key=True, db_column='corporationid')
    size = models.CharField(max_length=1, blank=True, db_column='size')
    extent = models.CharField(max_length=1, blank=True, db_column='extent')
    solar_system_id = models.IntegerField(null=True, blank=True, db_column='solarsystemid')
    investor_id1 = models.IntegerField(null=True, blank=True, db_column='investorid1')
    investor_shares1 = models.IntegerField(null=True, blank=True, db_column='investorshares1')
    investor_id2 = models.IntegerField(null=True, blank=True, db_column='investorid2')
    investor_shares2 = models.IntegerField(null=True, blank=True, db_column='investorshares2')
    investor_id3 = models.IntegerField(null=True, blank=True, db_column='investorid3')
    investor_shares3 = models.IntegerField(null=True, blank=True, db_column='investorshares3')
    investor_id4 = models.IntegerField(null=True, blank=True, db_column='investorid4')
    investor_shares4 = models.IntegerField(null=True, blank=True, db_column='investorshares4')
    friend_id = models.IntegerField(null=True, blank=True, db_column='friendid')
    enemy_id = models.IntegerField(null=True, blank=True, db_column='enemyid')
    public_shares = models.IntegerField(null=True, blank=True, db_column='publicshares')
    initial_price = models.IntegerField(null=True, blank=True, db_column='initialprice')
    min_security = models.FloatField(null=True, blank=True, db_column='minsecurity')
    scattered = models.BooleanField(null=True, blank=True, db_column='scattered')
    fringe = models.BooleanField(null=True, blank=True, db_column='fringe')
    corridor = models.BooleanField(null=True, blank=True, db_column='corridor')
    hub = models.BooleanField(null=True, blank=True, db_column='hub')
    border = models.BooleanField(null=True, blank=True, db_column='border')
    faction = models.ForeignKey('ChrFactions', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='factionid', related_name='+')
    size_factor = models.FloatField(null=True, blank=True, db_column='sizefactor')
    station_count = models.IntegerField(null=True, blank=True, db_column='stationcount')
    station_system_count = models.IntegerField(null=True, blank=True, db_column='stationsystemcount')
    description = models.TextField(blank=True, db_column='description')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconid')

    class Meta:
        db_table = 'evesde_crpnpccorporations'
        managed = False
        verbose_name = 'NPC Corporation'
        verbose_name_plural = 'NPC Corporations'
        ordering = ['corporation_id']

    def __str__(self):
        return f'Corporation {self.corporation_id}'

    @property
    def name(self):
        """Get corporation name from InvNames table."""
        try:
            name_obj = InvNames.objects.get(item_id=self.corporation_id)
            return name_obj.item_name
        except InvNames.DoesNotExist:
            return f'Corporation {self.corporation_id}'


# ============================================================================
# Additional Items & Variants
# ============================================================================

class InvMetaTypes(models.Model):
    """
    EVE SDE: invMetaTypes table

    Item variants (Tech II, faction, deadspace, etc.) - links to base items
    """
    type = models.OneToOneField('InvTypes', on_delete=models.DO_NOTHING, primary_key=True, db_column='typeid', related_name='meta_type')
    parent_type = models.ForeignKey('InvTypes', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='parenttypeid', related_name='variant_types')
    meta_group = models.ForeignKey('InvMetaGroups', on_delete=models.DO_NOTHING, db_column='metagroupid', related_name='types')

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
    icon_id = models.IntegerField(primary_key=True, db_column='iconid')
    icon_file = models.CharField(max_length=500, blank=True, db_column='iconfile')
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
    graphic_id = models.IntegerField(primary_key=True, db_column='graphicid')
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
# Additional Items & Variants (Level 2)
# ============================================================================

class InvNames(models.Model):
    """
    EVE SDE: invNames table

    Localized item names for various entities
    """
    item_id = models.IntegerField(primary_key=True, db_column='itemid')
    item_name = models.CharField(max_length=200, db_column='itemname')

    class Meta:
        db_table = 'evesde_invnames'
        managed = False
        verbose_name = 'Item Name'
        verbose_name_plural = 'Item Names'
        ordering = ['item_name']

    def __str__(self):
        return self.item_name


class InvFlags(models.Model):
    """
    EVE SDE: invFlags table

    Item flags (slots, hangars, etc.)
    """
    flag_id = models.IntegerField(primary_key=True, db_column='flagid')
    flag_name = models.CharField(max_length=200, blank=True, db_column='flagname')
    flag_text = models.CharField(max_length=100, blank=True, db_column='flagtext')
    order_id = models.IntegerField(null=True, blank=True, db_column='orderid')

    class Meta:
        db_table = 'evesde_invflags'
        managed = False
        verbose_name = 'Item Flag'
        verbose_name_plural = 'Item Flags'
        ordering = ['order_id', 'flag_id']

    def __str__(self):
        return self.flag_text or self.flag_name or f'Flag {self.flag_id}'


class InvContrabandTypes(models.Model):
    """
    EVE SDE: invContrabandTypes table

    Contraband types by faction
    """
    faction_id = models.IntegerField(db_column='factionid')
    type_id = models.IntegerField(db_column='typeid')
    standing_loss = models.FloatField(null=True, blank=True, db_column='standingloss')
    confiscate_min_sec = models.FloatField(null=True, blank=True, db_column='confiscateminsec')
    fine_by_value = models.FloatField(null=True, blank=True, db_column='finebyvalue')
    attack_min_sec = models.FloatField(null=True, blank=True, db_column='attackminsec')

    class Meta:
        db_table = 'evesde_invcontrabandtypes'
        managed = False
        verbose_name = 'Contraband Type'
        verbose_name_plural = 'Contraband Types'
        # Note: SDE uses composite key (factionID, typeID)


class InvTypeMaterials(models.Model):
    """
    EVE SDE: invTypeMaterials table

    Materials required for manufacturing (reprocessing)
    """
    type_id = models.IntegerField(db_index=True, db_column='typeid')
    material_type_id = models.IntegerField(db_index=True, db_column='materialtypeid')
    quantity = models.IntegerField(db_column='quantity')

    class Meta:
        db_table = 'evesde_invtypematerials'
        managed = False
        verbose_name = 'Type Material'
        verbose_name_plural = 'Type Materials'
        # Note: SDE uses composite key (typeID, materialTypeID)


# ============================================================================
# Additional Graphics (Level 2)
# ============================================================================

class EveUnits(models.Model):
    """
    EVE SDE: eveUnits table

    Measurement units for attributes (e.g., "mm", "m³", "%")
    """
    unit_id = models.IntegerField(primary_key=True, db_column='unitid')
    unit_name = models.CharField(max_length=100, blank=True, db_column='unitname')
    display_name = models.CharField(max_length=50, blank=True, db_column='displayname')
    description = models.CharField(max_length=1000, blank=True, db_column='description')

    class Meta:
        db_table = 'evesde_eveunits'
        managed = False
        verbose_name = 'Unit'
        verbose_name_plural = 'Units'
        ordering = ['unit_id']

    def __str__(self):
        return self.display_name or self.unit_name or f'Unit {self.unit_id}'


# ============================================================================
# Additional Attributes (Level 2)
# ============================================================================

class DgmAttributeCategories(models.Model):
    """
    EVE SDE: dgmAttributeCategories table

    Attribute categories for grouping attributes
    """
    category_id = models.IntegerField(primary_key=True, db_column='categoryid')
    category_name = models.CharField(max_length=50, blank=True, db_column='categoryname')
    category_description = models.CharField(max_length=200, blank=True, db_column='categorydescription')

    class Meta:
        db_table = 'evesde_dgmattributecategories'
        managed = False
        verbose_name = 'Attribute Category'
        verbose_name_plural = 'Attribute Categories'
        ordering = ['category_name']

    def __str__(self):
        return self.category_name or f'Category {self.category_id}'


class DgmEffects(models.Model):
    """
    EVE SDE: dgmEffects table

    Effect definitions (module activation, passive effects, etc.)
    """
    effect_id = models.IntegerField(primary_key=True, db_column='effectid')
    effect_name = models.CharField(max_length=400, blank=True, db_column='effectname')
    effect_category = models.IntegerField(null=True, blank=True, db_column='effectcategory')
    pre_expression = models.IntegerField(null=True, blank=True, db_column='preexpression')
    post_expression = models.IntegerField(null=True, blank=True, db_column='postexpression')
    description = models.CharField(max_length=1000, blank=True, db_column='description')
    guid = models.CharField(max_length=60, blank=True, db_column='guid')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconid')
    is_offensive = models.BooleanField(null=True, blank=True, db_column='isoffensive')
    is_assistance = models.BooleanField(null=True, blank=True, db_column='isassistance')
    duration_attribute_id = models.IntegerField(null=True, blank=True, db_column='durationattributeid')
    tracking_speed_attribute_id = models.IntegerField(null=True, blank=True, db_column='trackingspeedattributeid')
    discharge_attribute_id = models.IntegerField(null=True, blank=True, db_column='dischargeattributeid')
    range_attribute_id = models.IntegerField(null=True, blank=True, db_column='rangeattributeid')
    falloff_attribute_id = models.IntegerField(null=True, blank=True, db_column='falloffattributeid')
    disallow_auto_repeat = models.BooleanField(null=True, blank=True, db_column='disallowautorepeat')
    published = models.BooleanField(null=True, blank=True, db_column='published')
    display_name = models.CharField(max_length=100, blank=True, db_column='displayname')
    is_warp_safe = models.BooleanField(null=True, blank=True, db_column='iswarpsafe')
    range_chance = models.BooleanField(null=True, blank=True, db_column='rangechance')
    electronic_chance = models.BooleanField(null=True, blank=True, db_column='electronicchance')
    propagation_chance = models.BooleanField(null=True, blank=True, db_column='propagationchance')

    class Meta:
        db_table = 'evesde_dgmeffects'
        managed = False
        verbose_name = 'Effect'
        verbose_name_plural = 'Effects'
        ordering = ['effect_name']

    def __str__(self):
        return self.effect_name or f'Effect {self.effect_id}'


class DgmTypeEffects(models.Model):
    """
    EVE SDE: dgmTypeEffects table

    Effects applied to item types
    """
    type_id = models.IntegerField(db_index=True, db_column='typeid')
    effect_id = models.IntegerField(db_index=True, db_column='effectid')
    is_default = models.BooleanField(null=True, blank=True, db_column='isdefault')

    class Meta:
        db_table = 'evesde_dgmtypeeffects'
        managed = False
        verbose_name = 'Type Effect'
        verbose_name_plural = 'Type Effects'
        # Note: SDE uses composite key (typeID, effectID)


# ============================================================================
# Character Creation (Level 2)
# ============================================================================

class ChrAncestries(models.Model):
    """
    EVE SDE: chrAncestries table

    Character ancestry options (during character creation)
    """
    ancestry_id = models.IntegerField(primary_key=True, db_column='ancestryid')
    ancestry_name = models.CharField(max_length=100, blank=True, db_column='ancestryname')
    bloodline_id = models.IntegerField(null=True, blank=True, db_column='bloodlineid')
    description = models.CharField(max_length=1000, blank=True, db_column='description')
    perception = models.IntegerField(null=True, blank=True, db_column='perception')
    willpower = models.IntegerField(null=True, blank=True, db_column='willpower')
    charisma = models.IntegerField(null=True, blank=True, db_column='charisma')
    memory = models.IntegerField(null=True, blank=True, db_column='memory')
    intelligence = models.IntegerField(null=True, blank=True, db_column='intelligence')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconid')
    short_description = models.CharField(max_length=500, blank=True, db_column='shortdescription')

    class Meta:
        db_table = 'evesde_chrancestries'
        managed = False
        verbose_name = 'Ancestry'
        verbose_name_plural = 'Ancestries'
        ordering = ['ancestry_name']

    def __str__(self):
        return self.ancestry_name or f'Ancestry {self.ancestry_id}'


class ChrBloodlines(models.Model):
    """
    EVE SDE: chrBloodlines table

    Character bloodlines
    """
    bloodline_id = models.IntegerField(primary_key=True, db_column='bloodlineid')
    bloodline_name = models.CharField(max_length=100, blank=True, db_column='bloodlinename')
    race_id = models.IntegerField(null=True, blank=True, db_column='raceid')
    description = models.CharField(max_length=1000, blank=True, db_column='description')
    male_description = models.CharField(max_length=1000, blank=True, db_column='maledescription')
    female_description = models.CharField(max_length=1000, blank=True, db_column='femaledescription')
    ship_type_id = models.IntegerField(null=True, blank=True, db_column='shiptypeid')
    corporation_id = models.IntegerField(null=True, blank=True, db_column='corporationid')
    perception = models.IntegerField(null=True, blank=True, db_column='perception')
    willpower = models.IntegerField(null=True, blank=True, db_column='willpower')
    charisma = models.IntegerField(null=True, blank=True, db_column='charisma')
    memory = models.IntegerField(null=True, blank=True, db_column='memory')
    intelligence = models.IntegerField(null=True, blank=True, db_column='intelligence')
    icon_id = models.IntegerField(null=True, blank=True, db_column='iconid')
    short_description = models.CharField(max_length=500, blank=True, db_column='shortdescription')
    short_male_description = models.CharField(max_length=500, blank=True, db_column='shortmaledescription')
    short_female_description = models.CharField(max_length=500, blank=True, db_column='shortfemaledescription')

    class Meta:
        db_table = 'evesde_chrbloodlines'
        managed = False
        verbose_name = 'Bloodline'
        verbose_name_plural = 'Bloodlines'
        ordering = ['bloodline_name']

    def __str__(self):
        return self.bloodline_name or f'Bloodline {self.bloodline_id}'


# ============================================================================
# Certificates (Level 2)
# ============================================================================

class CertCerts(models.Model):
    """
    EVE SDE: certCerts table

    Certificate definitions
    """
    cert_id = models.IntegerField(primary_key=True, db_column='certid')
    description = models.TextField(blank=True, db_column='description')
    group_id = models.IntegerField(null=True, blank=True, db_column='groupid')
    name = models.CharField(max_length=255, blank=True, db_column='name')

    class Meta:
        db_table = 'evesde_certcerts'
        managed = False
        verbose_name = 'Certificate'
        verbose_name_plural = 'Certificates'
        ordering = ['name']

    def __str__(self):
        return self.name or f'Certificate {self.cert_id}'


class CertSkills(models.Model):
    """
    EVE SDE: certSkills table

    Certificate skill requirements
    """
    id = models.AutoField(primary_key=True, db_column='id')  # Django requires a PK, using auto-increment
    cert = models.ForeignKey('CertCerts', on_delete=models.DO_NOTHING, db_column='certid', related_name='skill_requirements')
    skill = models.ForeignKey('InvTypes', on_delete=models.DO_NOTHING, db_column='skillid', related_name='certificate_requirements')
    cert_level_int = models.IntegerField(null=True, blank=True, db_column='certlevelint')
    skill_level = models.IntegerField(null=True, blank=True, db_column='skilllevel')
    cert_level_text = models.CharField(max_length=8, blank=True, db_column='certleveltext')

    class Meta:
        db_table = 'evesde_certskills'
        managed = False
        verbose_name = 'Certificate Skill'
        verbose_name_plural = 'Certificate Skills'


class CertMasteries(models.Model):
    """
    EVE SDE: certMasteries table

    Certificate mastery levels
    Note: This table has no primary key in the database.
    We create a synthetic primary key from (type, mastery_level, cert) tuple.
    """
    # Use a composite primary key approach - Django needs a PK, so we create a unique field
    # that combines the three columns. Since this is read-only (managed=False), we can
    # use AutoField with db_column set to None to prevent it from being queried.
    id = models.BigAutoField(primary_key=True)
    type = models.ForeignKey('InvTypes', on_delete=models.DO_NOTHING, db_column='typeid', related_name='mastery_certificates')
    mastery_level = models.IntegerField(null=True, blank=True, db_column='masterylevel')
    cert = models.ForeignKey('CertCerts', on_delete=models.DO_NOTHING, db_column='certid', related_name='masteries')

    class Meta:
        db_table = 'evesde_certmasteries'
        managed = False
        verbose_name = 'Certificate Mastery'
        verbose_name_plural = 'Certificate Masteries'


# ============================================================================
# Agents (Level 3)
# ============================================================================

class AgtAgents(models.Model):
    """
    EVE SDE: agtAgents table

    NPC agents for missions
    """
    agent_id = models.IntegerField(primary_key=True, db_column='agentid')
    division_id = models.IntegerField(null=True, blank=True, db_column='divisionid')
    corporation_id = models.IntegerField(null=True, blank=True, db_index=True, db_column='corporationid')
    location_id = models.IntegerField(null=True, blank=True, db_index=True, db_column='locationid')
    level = models.IntegerField(null=True, blank=True, db_column='level')
    quality = models.IntegerField(null=True, blank=True, db_column='quality')
    agent_type_id = models.IntegerField(null=True, blank=True, db_column='agenttypeid')
    is_locator = models.BooleanField(null=True, blank=True, db_column='islocator')

    class Meta:
        db_table = 'evesde_agtagents'
        managed = False
        verbose_name = 'Agent'
        verbose_name_plural = 'Agents'
        ordering = ['agent_id']

    def __str__(self):
        return f'Agent {self.agent_id}'


class AgtAgentTypes(models.Model):
    """
    EVE SDE: agtAgentTypes table

    Agent type definitions
    """
    agent_type_id = models.IntegerField(primary_key=True, db_column='agenttypeid')
    agent_type = models.CharField(max_length=50, blank=True, db_column='agenttype')

    class Meta:
        db_table = 'evesde_agtagenttypes'
        managed = False
        verbose_name = 'Agent Type'
        verbose_name_plural = 'Agent Types'
        ordering = ['agent_type']

    def __str__(self):
        return self.agent_type or f'Agent Type {self.agent_type_id}'


class AgtAgentsInSpace(models.Model):
    """
    EVE SDE: agtAgentsInSpace table

    Mission agents located in space (not at stations)
    """
    agent_id = models.IntegerField(primary_key=True, db_column='agentid')
    dungeon_id = models.IntegerField(null=True, blank=True, db_column='dungeonid')
    solar_system_id = models.IntegerField(null=True, blank=True, db_index=True, db_column='solarsystemid')
    spawn_point_id = models.IntegerField(null=True, blank=True, db_column='spawnpointid')
    type_id = models.IntegerField(null=True, blank=True, db_column='typeid')

    class Meta:
        db_table = 'evesde_agtagentsinspace'
        managed = False
        verbose_name = 'Agent in Space'
        verbose_name_plural = 'Agents in Space'
        ordering = ['agent_id']

    def __str__(self):
        return f'In-Space Agent {self.agent_id}'


class AgtResearchAgents(models.Model):
    """
    EVE SDE: agtResearchAgents table

    Research agents for skill point research
    """
    agent_id = models.IntegerField(db_column='agentid')
    type_id = models.IntegerField(db_index=True, db_column='typeid')

    class Meta:
        db_table = 'evesde_agtresearchagents'
        managed = False
        verbose_name = 'Research Agent'
        verbose_name_plural = 'Research Agents'
        # Note: SDE uses composite key (agentID, typeID)

    def __str__(self):
        return f'Research Agent {self.agent_id}'


# ============================================================================
# Industry / Blueprints (Level 3)
# ============================================================================

class IndustryBlueprints(models.Model):
    """
    EVE SDE: industryBlueprints table

    Blueprint metadata
    """
    type_id = models.IntegerField(primary_key=True, db_column='typeid')
    max_production_limit = models.IntegerField(null=True, blank=True, db_column='maxproductionlimit')

    class Meta:
        db_table = 'evesde_industryblueprints'
        managed = False
        verbose_name = 'Blueprint'
        verbose_name_plural = 'Blueprints'
        ordering = ['type_id']

    def __str__(self):
        try:
            return f'Blueprint: {self.type.name}'
        except InvTypes.DoesNotExist:
            return f'Blueprint {self.type_id}'


# ============================================================================
# Corporation Activities (Level 2)
# ============================================================================

class CrpActivities(models.Model):
    """
    EVE SDE: crpActivities table

    Corporation activity types
    """
    activity_id = models.IntegerField(primary_key=True, db_column='activityid')
    activity_name = models.CharField(max_length=100, blank=True, db_column='activityname')
    description = models.CharField(max_length=1000, blank=True, db_column='description')

    class Meta:
        db_table = 'evesde_crpactivities'
        managed = False
        verbose_name = 'Corporation Activity'
        verbose_name_plural = 'Corporation Activities'
        ordering = ['activity_name']

    def __str__(self):
        return self.activity_name or f'Activity {self.activity_id}'


# ============================================================================
# Control Towers (POS) (Level 3)
# ============================================================================

class InvControlTowerResources(models.Model):
    """
    EVE SDE: invControlTowerResources table

    POS fuel and resource requirements
    """
    # Composite key workaround: use controlTowerTypeID as primary key
    # This allows queries but note that multiple rows may have the same PK
    control_tower_type_id = models.IntegerField(primary_key=True, db_column='controltowertypeid')
    resource_type_id = models.IntegerField(db_column='resourcetypeid')
    purpose = models.IntegerField(null=True, blank=True, db_column='purpose')
    quantity = models.IntegerField(null=True, blank=True, db_column='quantity')
    min_security_level = models.FloatField(null=True, blank=True, db_column='minsecuritylevel')
    faction_id = models.IntegerField(null=True, blank=True, db_column='factionid')

    class Meta:
        db_table = 'evesde_invcontroltowerresources'
        managed = False
        verbose_name = 'Control Tower Resource'
        verbose_name_plural = 'Control Tower Resources'
        # Note: SDE uses composite key (controlTowerTypeID, resourceTypeID)


# ============================================================================
# Additional Map Data (Level 2)
# ============================================================================

class MapDenormalize(models.Model):
    """
    EVE SDE: mapDenormalize table

    Denormalized map data for easy querying (celestial objects)
    """
    item_id = models.IntegerField(primary_key=True, db_column='itemid')
    type_id = models.IntegerField(null=True, blank=True, db_index=True, db_column='typeid')
    group_id = models.IntegerField(null=True, blank=True, db_column='groupid')
    solar_system_id = models.IntegerField(null=True, blank=True, db_index=True, db_column='solarsystemid')
    constellation_id = models.IntegerField(null=True, blank=True, db_index=True, db_column='constellationid')
    region_id = models.IntegerField(null=True, blank=True, db_index=True, db_column='regionid')
    orbit_id = models.IntegerField(null=True, blank=True, db_index=True, db_column='orbitid')
    x = models.FloatField(null=True, blank=True, db_column='x_coord')
    y = models.FloatField(null=True, blank=True, db_column='y_coord')
    z = models.FloatField(null=True, blank=True, db_column='z_coord')
    radius = models.FloatField(null=True, blank=True, db_column='radius')
    item_name = models.CharField(max_length=100, blank=True, db_column='itemname')
    security = models.FloatField(null=True, blank=True, db_column='security')
    celestial_index = models.IntegerField(null=True, blank=True, db_column='celestialindex')
    orbit_index = models.IntegerField(null=True, blank=True, db_column='orbitindex')

    class Meta:
        db_table = 'evesde_mapdenormalize'
        managed = False
        verbose_name = 'Celestial Object'
        verbose_name_plural = 'Celestial Objects'
        ordering = ['solar_system_id', 'celestial_index']

    def __str__(self):
        return self.item_name or f'Celestial {self.item_id}'


class MapLandmarks(models.Model):
    """
    EVE SDE: mapLandmarks table

    Landmarks in space
    """
    landmark_id = models.IntegerField(primary_key=True, db_column='landmarkid')
    landmark_name = models.CharField(max_length=100, blank=True, db_column='landmarkname')
    description = models.TextField(blank=True, db_column='description')
    location_id = models.IntegerField(null=True, blank=True, db_column='locationid')
    x = models.FloatField(null=True, blank=True, db_column='x')
    y = models.FloatField(null=True, blank=True, db_column='y')
    z = models.FloatField(null=True, blank=True, db_column='z')

    class Meta:
        db_table = 'evesde_maplandmarks'
        managed = False
        verbose_name = 'Landmark'
        verbose_name_plural = 'Landmarks'
        ordering = ['landmark_name']

    def __str__(self):
        return self.landmark_name or f'Landmark {self.landmark_id}'


# ============================================================================
# Planet Interaction (Level 3)
# ============================================================================

class PlanetSchematics(models.Model):
    """
    EVE SDE: planetSchematics table

    Planet interaction schematic definitions
    """
    schematic_id = models.IntegerField(primary_key=True, db_column='schematicid')
    schematic_name = models.CharField(max_length=255, blank=True, db_column='schematicname')
    cycle_time = models.IntegerField(null=True, blank=True, db_column='cycletime')

    class Meta:
        db_table = 'evesde_planetschematics'
        managed = False
        verbose_name = 'Planet Schematic'
        verbose_name_plural = 'Planet Schematics'
        ordering = ['schematic_name']

    def __str__(self):
        return self.schematic_name or f'Schematic {self.schematic_id}'


class PlanetSchematicsPinMap(models.Model):
    """
    EVE SDE: planetSchematicsPinMap table

    Planet pin mappings for schematics
    """
    schematic_id = models.IntegerField(db_index=True, db_column='schematicid')
    pin_type_id = models.IntegerField(db_index=True, db_column='pintypeid')

    class Meta:
        db_table = 'evesde_planetschematicspinmap'
        managed = False
        verbose_name = 'Planet Schematic Pin'
        verbose_name_plural = 'Planet Schematic Pins'
        # Note: SDE uses composite key (schematicID, pinTypeID)


class PlanetSchematicsTypeMap(models.Model):
    """
    EVE SDE: planetSchematicsTypeMap table

    Planet type mappings for schematics (inputs/outputs)
    """
    schematic_id = models.IntegerField(db_index=True, db_column='schematicid')
    type_id = models.IntegerField(db_index=True, db_column='typeid')
    quantity = models.BooleanField(null=True, blank=True, db_column='quantity')  # Is output?
    is_input = models.BooleanField(null=True, blank=True, db_column='isinput')

    class Meta:
        db_table = 'evesde_planetschematicstypemap'
        managed = False
        verbose_name = 'Planet Schematic Type'
        verbose_name_plural = 'Planet Schematic Types'
        # Note: SDE uses composite key


# ============================================================================
# SKIN System (Level 3)
# ============================================================================

class SkinLicense(models.Model):
    """
    EVE SDE: skinLicense table

    SKIN license definitions
    """
    license_id = models.IntegerField(primary_key=True, db_column='licenseid')
    type_id = models.IntegerField(null=True, blank=True, db_column='typeid')
    skin_id = models.IntegerField(null=True, blank=True, db_column='skinid')

    class Meta:
        db_table = 'evesde_skinlicense'
        managed = False
        verbose_name = 'SKIN License'
        verbose_name_plural = 'SKIN Licenses'
        ordering = ['license_id']

    def __str__(self):
        return f'SKIN License {self.license_id}'


class SkinMaterials(models.Model):
    """
    EVE SDE: skinMaterials table

    SKIN material definitions
    """
    skin_material_id = models.IntegerField(primary_key=True, db_column='skinmaterialid')
    display_name = models.CharField(max_length=100, blank=True, db_column='displayname')
    skin_material = models.CharField(max_length=100, blank=True, db_column='skinmaterial')

    class Meta:
        db_table = 'evesde_skinmaterials'
        managed = False
        verbose_name = 'SKIN Material'
        verbose_name_plural = 'SKIN Materials'
        ordering = ['display_name']

    def __str__(self):
        return self.display_name or f'SKIN Material {self.skin_material_id}'


class SkinShip(models.Model):
    """
    EVE SDE: skinShip table

    SKIN to ship bindings
    """
    skin_id = models.IntegerField(primary_key=True, db_column='skinid')
    type_id = models.IntegerField(null=True, blank=True, db_column='typeid')

    class Meta:
        db_table = 'evesde_skinship'
        managed = False
        verbose_name = 'Ship SKIN'
        verbose_name_plural = 'Ship SKINs'
        ordering = ['skin_id']

    def __str__(self):
        return f'Ship SKIN {self.skin_id}'


# ============================================================================
# Translations (Level 3)
# ============================================================================

class TrnTranslations(models.Model):
    """
    EVE SDE: trnTranslations table

    Translated strings for localization
    """
    tc_id = models.IntegerField(db_index=True, db_column='tcid')
    key_id = models.IntegerField(db_index=True, db_column='keyid')
    language_id = models.CharField(max_length=5, db_index=True, db_column='languageid')
    text = models.TextField(db_column='text')

    class Meta:
        db_table = 'evesde_trntranslations'
        managed = False
        verbose_name = 'Translation'
        verbose_name_plural = 'Translations'
        # Note: SDE uses composite key (tcID, keyID, languageID)


# ============================================================================
# Industry Activities (Level 3)
# ============================================================================

class IndustryActivity(models.Model):
    """
    EVE SDE: industryActivity table

    Activity types for industry (manufacturing, research, invention, etc.)
    """
    type_id = models.IntegerField(db_index=True, db_column='typeid')
    activity_id = models.IntegerField(db_index=True, db_column='activityid')
    time = models.IntegerField(null=True, blank=True, db_column='time')

    class Meta:
        db_table = 'evesde_industryactivity'
        managed = False
        verbose_name = 'Industry Activity'
        verbose_name_plural = 'Industry Activities'
        # Note: SDE uses composite key (typeID, activityID)

    def __str__(self):
        return f'Type {self.type_id} - Activity {self.activity_id}'


class IndustryActivityMaterials(models.Model):
    """
    EVE SDE: industryActivityMaterials table

    Material requirements for industry activities
    """
    type_id = models.IntegerField(db_index=True, db_column='typeid')
    activity_id = models.IntegerField(db_index=True, db_column='activityid')
    material_type_id = models.IntegerField(db_index=True, db_column='materialtypeid')
    quantity = models.IntegerField(db_column='quantity')

    class Meta:
        db_table = 'evesde_industryactivitymaterials'
        managed = False
        verbose_name = 'Industry Activity Material'
        verbose_name_plural = 'Industry Activity Materials'
        # Note: SDE uses composite key (typeID, activityID, materialTypeID)

    def __str__(self):
        return f'Type {self.type_id} - Activity {self.activity_id} - Material {self.material_type_id}'


class IndustryActivityProducts(models.Model):
    """
    EVE SDE: industryActivityProducts table

    Products output by industry activities
    """
    type_id = models.IntegerField(db_index=True, db_column='typeid')
    activity_id = models.IntegerField(db_index=True, db_column='activityid')
    product_type_id = models.IntegerField(db_index=True, db_column='producttypeid')
    quantity = models.IntegerField(db_column='quantity')

    class Meta:
        db_table = 'evesde_industryactivityproducts'
        managed = False
        verbose_name = 'Industry Activity Product'
        verbose_name_plural = 'Industry Activity Products'
        # Note: SDE uses composite key (typeID, activityID, productTypeID)

    def __str__(self):
        return f'Type {self.type_id} - Activity {self.activity_id} - Product {self.product_type_id}'


class IndustryActivitySkills(models.Model):
    """
    EVE SDE: industryActivitySkills table

    Skill requirements for industry activities
    """
    type_id = models.IntegerField(db_index=True, db_column='typeid')
    activity_id = models.IntegerField(db_index=True, db_column='activityid')
    skill_id = models.IntegerField(db_index=True, db_column='skillid')
    level = models.IntegerField(db_column='level')

    class Meta:
        db_table = 'evesde_industryactivityskills'
        managed = False
        verbose_name = 'Industry Activity Skill'
        verbose_name_plural = 'Industry Activity Skills'
        # Note: SDE uses composite key (typeID, activityID, skillID)

    def __str__(self):
        return f'Type {self.type_id} - Activity {self.activity_id} - Skill {self.skill_id}'


class RamTypeRequirements(models.Model):
    """
    EVE SDE: ramTypeRequirements table

    Additional requirements for industry activities (items, skills)
    """
    type_id = models.IntegerField(db_index=True, db_column='typeid')
    activity_id = models.IntegerField(db_index=True, db_column='activityid')
    required_type_id = models.IntegerField(db_index=True, db_column='requiredtypeid')
    quantity = models.IntegerField(db_column='quantity')
    damage_per_job = models.FloatField(null=True, blank=True, db_column='damageperjob')
    recycle = models.BooleanField(null=True, blank=True, db_column='recycle')

    class Meta:
        db_table = 'evesde_ramtyperequirements'
        managed = False
        verbose_name = 'RAM Type Requirement'
        verbose_name_plural = 'RAM Type Requirements'
        # Note: SDE uses composite key (typeID, activityID, requiredTypeID)

    def __str__(self):
        return f'Type {self.type_id} - Activity {self.activity_id} - Required {self.required_type_id}'


# ============================================================================
# System Connections (Level 1)
# ============================================================================

class MapSolarSystemJumps(models.Model):
    """
    EVE SDE: mapSolarSystemJumps table

    Stargate connections between solar systems.
    Each row represents a direct connection from one system to another.
    """
    from_region = models.ForeignKey('MapRegions', on_delete=models.DO_NOTHING, db_column='fromregionid', related_name='outgoing_jumps')
    from_constellation = models.ForeignKey('MapConstellations', on_delete=models.DO_NOTHING, db_column='fromconstellationid', related_name='outgoing_jumps')
    from_system = models.ForeignKey('MapSolarSystems', on_delete=models.DO_NOTHING, db_column='fromsolarsystemid', related_name='outgoing_jumps')
    to_region = models.ForeignKey('MapRegions', on_delete=models.DO_NOTHING, db_column='toregionid', related_name='incoming_jumps')
    to_constellation = models.ForeignKey('MapConstellations', on_delete=models.DO_NOTHING, db_column='toconstellationid', related_name='incoming_jumps')
    to_system = models.ForeignKey('MapSolarSystems', on_delete=models.DO_NOTHING, db_column='tosolarsystemid', related_name='incoming_jumps')

    class Meta:
        db_table = 'evesde_mapsolarsystemjumps'
        managed = False
        verbose_name = 'System Jump'
        verbose_name_plural = 'System Jumps'

    def __str__(self):
        return f'{self.from_system.system_name} -> {self.to_system.system_name}'

