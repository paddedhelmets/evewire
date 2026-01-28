"""
SDE Browser Views

Read-only views for exploring EVE's Static Data Export.
"""

from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch, Avg, Min, Max
from django.db import connection
from django.db import models

from core.sde.models import (
    InvTypes, InvGroups, InvCategories, InvMarketGroups, InvMetaGroups, InvMetaTypes,
    DgmAttributeTypes, DgmTypeAttributes,
    MapRegions, MapSolarSystems, MapConstellations, MapSolarSystemJumps,
    ChrFactions, ChrRaces, CrpNPCCorporations,
    StaStations,
    CertCerts, CertSkills, CertMasteries,
    IndustryBlueprints,
    AgtAgents, AgtAgentTypes, InvNames,
    IndustryActivity, IndustryActivityMaterials, IndustryActivityProducts, IndustryActivitySkills,
    RamTypeRequirements,
)


def sde_index(request: HttpRequest) -> HttpResponse:
    """SDE Browser homepage."""
    # Get some stats
    stats = {
        'total_items': InvTypes.objects.count(),
        'total_ships': InvTypes.objects.filter(group__category_id=6).count(),
        'total_modules': InvTypes.objects.filter(group__category_id=7).count(),
        'total_systems': MapSolarSystems.objects.count(),
        'total_regions': MapRegions.objects.count(),
    }

    # Get all published categories with item counts
    all_categories = InvCategories.objects.filter(
        published=True
    ).annotate(
        item_count=Count('groups__types', filter=Q(groups__types__published=True))
    ).order_by('-item_count')

    # Get top-level market groups
    top_market_groups = InvMarketGroups.objects.filter(
        parent_group_id__isnull=True
    ).annotate(
        item_count=Count('types', filter=Q(types__published=True))
    ).order_by('market_group_name')

    # Get meta groups with counts
    meta_groups = InvMetaGroups.objects.annotate(
        item_count=Count('types')
    ).order_by('meta_group_id')

    # Get ship classes (popular groups from Ship category)
    ship_groups = InvGroups.objects.filter(
        category_id=6,  # Ships
        published=True
    ).annotate(
        item_count=Count('types', filter=Q(types__published=True))
    ).filter(item_count__gt=0).order_by('group_name')

    # Quick link counts
    skills_count = InvTypes.objects.filter(
        group__category_id=16,  # Skills
        published=True
    ).count()

    # Get certificates
    certificates_count = CertCerts.objects.count()
    # Get a sample of certificates to display
    certificates = CertCerts.objects.all().order_by('name')[:20]

    # Universe stats
    factions_count = ChrFactions.objects.count()
    corporations_count = CrpNPCCorporations.objects.count()
    agents_count = AgtAgents.objects.count()

    return render(request, 'core/sde/index.html', {
        'stats': stats,
        'all_categories': all_categories,
        'top_market_groups': top_market_groups,
        'meta_groups': meta_groups,
        'ship_groups': ship_groups,
        'skills_count': skills_count,
        'certificates_count': certificates_count,
        'certificates': certificates,
        'factions_count': factions_count,
        'corporations_count': corporations_count,
        'agents_count': agents_count,
    })


def sde_search(request: HttpRequest) -> HttpResponse:
    """Search SDE items with filters and sorting."""
    query = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)

    # Get filter parameters
    category_id = request.GET.get('category', '')
    meta_group_id = request.GET.get('meta_group', '')
    sort_by = request.GET.get('sort', 'name')

    results = []
    total_count = 0
    active_filters = {}

    # Build the base queryset with filters
    queryset = InvTypes.objects.all().select_related(
        'group', 'group__category', 'meta_type__meta_group'
    )

    # Apply search query
    if query and len(query) >= 2:
        queryset = queryset.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
        active_filters['query'] = query
    elif not query:
        # If no query, still show results but apply filters only
        pass
    else:
        # Query is too short
        queryset = queryset.none()

    # Apply category filter
    if category_id:
        queryset = queryset.filter(group__category_id=category_id)
        try:
            category = InvCategories.objects.get(category_id=category_id)
            active_filters['category'] = category
        except InvCategories.DoesNotExist:
            pass

    # Apply meta group filter
    if meta_group_id:
        queryset = queryset.filter(meta_type__meta_group_id=meta_group_id)
        try:
            meta_group = InvMetaGroups.objects.get(meta_group_id=meta_group_id)
            active_filters['meta_group'] = meta_group
        except InvMetaGroups.DoesNotExist:
            pass

    # Apply sorting
    sort_options = {
        'name': 'name',
        'name_desc': '-name',
        'price': 'base_price',
        'price_desc': '-base_price',
        'volume': 'volume',
        'volume_desc': '-volume',
    }

    if sort_by in sort_options:
        queryset = queryset.order_by(sort_options[sort_by])
    else:
        queryset = queryset.order_by('name')

    # Count total results before pagination
    total_count = queryset.count()

    # Paginate
    paginator = Paginator(queryset, 50)
    results = paginator.get_page(page)

    # Get filter options
    # Top 20 categories by item count
    categories = InvCategories.objects.filter(
        published=True
    ).annotate(
        item_count=Count('groups__types', filter=Q(groups__types__published=True))
    ).filter(item_count__gt=0).order_by('-item_count')[:20]

    # All meta groups
    meta_groups = InvMetaGroups.objects.annotate(
        item_count=Count('types')
    ).filter(item_count__gt=0).order_by('meta_group_id')

    return render(request, 'core/sde/search.html', {
        'query': query,
        'results': results,
        'total_count': total_count,
        'categories': categories,
        'meta_groups': meta_groups,
        'active_filters': active_filters,
        'selected_category': category_id,
        'selected_meta_group': meta_group_id,
        'selected_sort': sort_by,
        'sort_options': {
            'name': 'Name (A-Z)',
            'name_desc': 'Name (Z-A)',
            'price': 'Price (Low to High)',
            'price_desc': 'Price (High to Low)',
            'volume': 'Volume (Low to High)',
            'volume_desc': 'Volume (High to Low)',
        },
    })


def sde_item_detail(request: HttpRequest, type_id: int) -> HttpResponse:
    """Detail page for a single item type."""
    try:
        item = InvTypes.objects.select_related(
            'group', 'group__category', 'market_group', 'meta_type'
        ).get(type_id=type_id)
    except InvTypes.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Item {type_id} not found',
        }, status=404)

    # Get attributes for this item using raw SQL (ORM has issues with this table)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ta.attributeID, at.attributeName, at.displayName, ta.valueInt, ta.valueFloat
            FROM evesde_dgmtypeattributes ta
            JOIN evesde_dgmattributetypes at ON ta.attributeID = at.attributeID
            WHERE ta.typeID = %s
            ORDER BY at.attributeName
        """, [type_id])
        attr_rows = cursor.fetchall()

    # Format attributes with their display names
    formatted_attributes = []
    for attr_id, attr_name, display_name, val_int, val_float in attr_rows:
        value = val_float if val_float is not None else val_int
        formatted_attributes.append({
            'name': display_name or attr_name,
            'value': value,
            'unit': '',  # TODO: Add unit mapping if desired
        })

    # Get related items (same group, excluding self)
    related = InvTypes.objects.filter(
        group_id=item.group_id,
        published=True
    ).exclude(type_id=item.type_id)[:10]

    # Get variant information
    parent_meta = None  # If this item is a variant, this is the parent info
    variants_by_group = {}  # If this item is a parent, these are its variants

    # Check if this item is a variant (has InvMetaTypes pointing to it as type)
    try:
        if item.meta_type and item.meta_type.parent_type:
            parent_meta = {
                'type': item.meta_type.parent_type,
                'meta_group': item.meta_type.meta_group,
            }
    except InvMetaTypes.DoesNotExist:
        pass  # Item has no meta_type

    # Check if this item has variants (is a parent_type in InvMetaTypes)
    variants = InvMetaTypes.objects.filter(
        parent_type_id=type_id
    ).select_related('type', 'meta_group').order_by('meta_group__meta_group_id', 'type__name')

    # Group variants by meta group
    for variant in variants:
        group_name = variant.meta_group.meta_group_name
        if group_name not in variants_by_group:
            variants_by_group[group_name] = []
        variants_by_group[group_name].append(variant.type)

    return render(request, 'core/sde/item_detail.html', {
        'item': item,
        'attributes': formatted_attributes,
        'related': related,
        'parent_meta': parent_meta,
        'variants_by_group': variants_by_group,
    })


def sde_category_detail(request: HttpRequest, category_id: int) -> HttpResponse:
    """Detail page for a category (shows all groups in it)."""
    try:
        category = InvCategories.objects.get(category_id=category_id)
    except InvCategories.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Category {category_id} not found',
        }, status=404)

    # Get groups in this category with item counts
    groups = InvGroups.objects.filter(
        category_id=category_id,
        published=True
    ).annotate(
        item_count=Count('types')
    ).order_by('group_name')

    return render(request, 'core/sde/category_detail.html', {
        'category': category,
        'groups': groups,
    })


def sde_group_detail(request: HttpRequest, group_id: int) -> HttpResponse:
    """Detail page for a group (shows all items in it)."""
    try:
        group = InvGroups.objects.select_related('category').get(group_id=group_id)
    except InvGroups.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Group {group_id} not found',
        }, status=404)

    # Get items in this group
    items = InvTypes.objects.filter(
        group_id=group_id,
        published=True
    ).order_by('name')

    # Paginate
    page = request.GET.get('page', 1)
    paginator = Paginator(items, 50)
    items_page = paginator.get_page(page)

    return render(request, 'core/sde/group_detail.html', {
        'group': group,
        'items': items_page,
    })


def sde_system_detail(request: HttpRequest, system_id: int) -> HttpResponse:
    """Detail page for a solar system."""
    try:
        system = MapSolarSystems.objects.select_related(
            'region', 'constellation', 'faction'
        ).get(system_id=system_id)
    except MapSolarSystems.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'System {system_id} not found',
        }, status=404)

    # Get stations in this system
    stations = StaStations.objects.filter(
        solar_system_id=system_id
    ).select_related('corporation').order_by('station_name')[:20]

    # Get celestial objects in this system using MapDenormalize
    # Group IDs: 6=Sun, 7=Planet, 8=Moon, 9=Asteroid Belt, 10=Stargate
    from core.sde.models import MapDenormalize

    # Get stargates for connections
    stargates = MapDenormalize.objects.filter(
        solar_system_id=system_id,
        group_id=10  # Stargate
    ).order_by('item_name')

    # Get planets
    planets = MapDenormalize.objects.filter(
        solar_system_id=system_id,
        group_id=7  # Planet
    ).order_by('celestial_index')

    # Get asteroid belts
    belts = MapDenormalize.objects.filter(
        solar_system_id=system_id,
        group_id=9  # Asteroid Belt
    ).order_by('celestial_index')[:20]

    # Get moons (limited to avoid overwhelming pages)
    moons = MapDenormalize.objects.filter(
        solar_system_id=system_id,
        group_id=8  # Moon
    ).order_by('celestial_index')[:50]

    return render(request, 'core/sde/system_detail.html', {
        'system': system,
        'stations': stations,
        'stargates': stargates,
        'planets': planets,
        'belts': belts,
        'moons': moons,
        'stargate_count': stargates.count(),
        'planet_count': planets.count(),
        'belt_count': belts.count(),
        'moon_count': moons.count(),
    })


def sde_region_detail(request: HttpRequest, region_id: int) -> HttpResponse:
    """Detail page for a region."""
    try:
        region = MapRegions.objects.select_related('faction').get(region_id=region_id)
    except MapRegions.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Region {region_id} not found',
        }, status=404)

    # Get constellations in this region
    constellations = MapConstellations.objects.filter(
        region_id=region_id
    ).order_by('constellation_name')

    return render(request, 'core/sde/region_detail.html', {
        'region': region,
        'constellations': constellations,
    })


def sde_constellation_detail(request: HttpRequest, constellation_id: int) -> HttpResponse:
    """Detail page for a constellation."""
    try:
        constellation = MapConstellations.objects.select_related(
            'region', 'region__faction'
        ).get(constellation_id=constellation_id)
    except MapConstellations.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Constellation {constellation_id} not found',
        }, status=404)

    # Get systems in this constellation
    systems = MapSolarSystems.objects.filter(
        constellation_id=constellation_id
    ).select_related('region', 'constellation').order_by('system_name')

    # Count statistics
    system_count = systems.count()

    # Calculate security status (average of systems in constellation)
    security_data = systems.aggregate(
        avg_security=models.Avg('security'),
        min_security=models.Min('security'),
        max_security=models.Max('security'),
    )

    return render(request, 'core/sde/constellation_detail.html', {
        'constellation': constellation,
        'systems': systems,
        'system_count': system_count,
        'security_avg': security_data['avg_security'],
        'security_min': security_data['min_security'],
        'security_max': security_data['max_security'],
    })


def sde_station_detail(request: HttpRequest, station_id: int) -> HttpResponse:
    """Detail page for a station."""
    try:
        station = StaStations.objects.select_related(
            'station_type',
            'corporation',
            'solar_system',
            'solar_system__constellation',
            'solar_system__constellation__region',
            'region'
        ).get(station_id=station_id)
    except StaStations.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Station {station_id} not found',
        }, status=404)

    # Get other stations in the same system
    nearby_stations = StaStations.objects.filter(
        solar_system_id=station.solar_system_id
    ).exclude(station_id=station_id)[:10]

    return render(request, 'core/sde/station_detail.html', {
        'station': station,
        'nearby_stations': nearby_stations,
    })


# ============================================================================
# Enhanced SDE Views with Relationships
# ============================================================================

def get_skill_prereqs_sql(skill_id: int):
    """Get prerequisite chain using raw SQL for performance."""
    prereqs = []
    current_id = skill_id
    visited = set()

    with connection.cursor() as cursor:
        while current_id and current_id not in visited:
            visited.add(current_id)
            cursor.execute("""
                SELECT t.typeID, t.typeName, g.groupName, t.description
                FROM evesde_invtypes t
                LEFT JOIN evesde_invgroups g ON t.groupID = g.groupID
                WHERE t.typeID = %s
            """, [current_id])
            skill_row = cursor.fetchone()

            if not skill_row:
                break

            cursor.execute("""
                SELECT valueInt FROM evesde_dgmtypeattributes
                WHERE typeID = %s AND attributeID = 182
            """, [current_id])
            prereq_row = cursor.fetchone()
            
            prereqs.insert(0, {
                'type_id': skill_row[0],
                'name': skill_row[1],
                'group': skill_row[2],
                'description': skill_row[3],
            })
            
            if prereq_row and prereq_row[0]:
                current_id = prereq_row[0]
            else:
                break
    
    return prereqs


def get_ship_fitting(ship_id: int) -> dict:
    """Get all fitting attributes for a ship, with correct slot mapping."""
    # Critical: attributes 12/13/14 are low/med/hi slots (NOT what SDE names them)
    fitting_attr_ids = [
        12, 13, 14, 970, 1169,  # Slots (charge=low, powerToSpeed=med, speedFactor=hi)
        7, 26, 965,            # Resources
        65, 64,                # Hardpoints
        232, 1086,             # Drones
        414, 30,               # Capacitor
        212, 214, 6,           # Tank
        20, 40, 516,           # Mobility
    ]

    with connection.cursor() as cursor:
        attr_ids_str = ','.join(map(str, fitting_attr_ids))
        # Use %s placeholders and format the query directly
        query = """
            SELECT ta.attributeID, at.attributeName, ta.valueInt, ta.valueFloat
            FROM evesde_dgmtypeattributes ta
            JOIN evesde_dgmattributetypes at ON ta.attributeID = at.attributeID
            WHERE ta.typeID = %s AND ta.attributeID IN (%s)
            ORDER BY ta.attributeID
        """ % (ship_id, attr_ids_str)
        cursor.execute(query)
        
        # Map to friendly names (correcting for SDE mislabeling)
        attr_map = {
            12: 'lowSlots', 13: 'medSlots', 14: 'hiSlots',
            970: 'rigSlots', 1169: 'subSystemSlot',
            7: 'powerOutput', 26: 'cpu', 965: 'upgradeCapacity',
            65: 'turretSlotsLeft', 64: 'launcherSlotsLeft',
            232: 'droneCapacity', 1086: 'droneBandwidth',
            414: 'capacitorCapacity', 30: 'rechargeRate',
            212: 'shieldCapacity', 214: 'armorHP', 6: 'structureHP',
            20: 'maxVelocity', 40: 'agility', 516: 'warpSpeedMultiplier',
        }
        
        fitting = {}
        for attr_id, sde_name, val_int, val_float in cursor.fetchall():
            value = val_int if val_int is not None else val_float
            friendly_name = attr_map.get(attr_id, sde_name)
            fitting[friendly_name] = value
        
        return fitting


def sde_skill_detail(request: HttpRequest, skill_id: int) -> HttpResponse:
    """Detail page for a skill with prerequisites and certificates."""
    try:
        skill = InvTypes.objects.select_related(
            'group', 'group__category'
        ).get(type_id=skill_id, published=True)
    except InvTypes.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Skill {skill_id} not found',
        }, status=404)
    
    # Check if this is actually a skill (category 16)
    if skill.group.category_id != 16:
        return render(request, 'core/error.html', {
            'message': f'Item {skill_id} is not a skill',
        }, status=400)
    
    # Get prerequisite chain
    prerequisites = get_skill_prereqs_sql(skill_id)
    
    # Get skills that require this skill (reverse lookup)
    required_by = []
    prereq_attrs = DgmTypeAttributes.objects.filter(
        attribute_id=182,
        value_int=skill_id
    ).select_related('type')[:50]  # Limit to prevent huge pages
    
    for attr in prereq_attrs:
        try:
            requires_skill = InvTypes.objects.get(
                type_id=attr.type_id,
                published=True,
                group__category_id=16  # Only skills
            )
            required_by.append({
                'skill': requires_skill,
                'group': requires_skill.group.group_name
            })
        except InvTypes.DoesNotExist:
            pass
    
    # Get related certificates
    cert_skills = CertSkills.objects.filter(
        skill_id=skill_id
    ).select_related('cert')
    
    certificates = []
    for cert_skill in cert_skills:
        certificates.append({
            'certificate': cert_skill.cert,
            'required_level': cert_skill.skill_level,
            'cert_level': cert_skill.cert_level_int
        })
    
    # Get skill attributes
    skill_attrs = DgmTypeAttributes.objects.filter(
        type_id=skill_id
    ).select_related('attribute')
    
    attributes = {}
    for attr in skill_attrs:
        value = attr.value_float if attr.value_float is not None else attr.value_int
        attributes[attr.attribute.attribute_name] = value
    
    return render(request, 'core/sde/skill_detail.html', {
        'skill': skill,
        'prerequisites': prerequisites,
        'required_by': required_by,
        'certificates': certificates,
        'attributes': attributes,
        'total_prereqs': len(prerequisites) - 1 if prerequisites else 0,
        'total_unlocks': len(required_by),
        'total_certs': len(certificates),
    })


def sde_variant_comparison(request: HttpRequest, type_id: int) -> HttpResponse:
    """Compare all variants of an item (meta group comparison).

    For modules (category 7 = Module, 8 = Charge, 32 = Subsystem):
    Shows fitting requirements, combat stats, and other key attributes.

    For other items:
    Shows general variant information with tier grouping.
    """
    try:
        base = InvTypes.objects.select_related('group', 'group__category').get(type_id=type_id)
    except InvTypes.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Item {type_id} not found',
        }, status=404)

    # Check if this is a module (category 7 = Module, 8 = Charge, 32 = Subsystem)
    is_module = base.group.category_id in [7, 8, 32]

    if is_module:
        return _module_comparison(request, base)
    else:
        return _general_variant_comparison(request, base)


def _get_module_attributes(type_id: int) -> dict:
    """Extract module-relevant attributes for comparison."""
    attrs = {}

    with connection.cursor() as cursor:
        # Key attribute IDs for modules
        fitting_queries = [
            ('cpu', 50),          # cpu
            ('power', 11),        # power
            ('capacitor', 856),   # capacitorNeed
        ]

        for name, attr_id in fitting_queries:
            cursor.execute("""
                SELECT valueInt, valueFloat
                FROM evesde_dgmtypeattributes
                WHERE typeID = ? AND attributeID = ?
            """, [type_id, attr_id])
            row = cursor.fetchone()
            if row:
                value = row[1] if row[1] is not None else row[0]
                if value is not None:
                    attrs[name] = float(value)

        # Combat-related attributes (will vary by module type)
        combat_queries = [
            ('damage', 64),              # damage multiplier
            ('rof', 506),                # speed multiplier (rate of fire)
            ('range', 54),               # max range
            ('falloff', 158),            # falloff
            ('tracking', 160),           # tracking speed
            ('shield_boost', 74),        # shield boost amount
            ('armor_repair', 88),        # armor repair amount
            ('capacitor_boost', 87),     # capacitor bonus
        ]

        for name, attr_id in combat_queries:
            cursor.execute("""
                SELECT valueInt, valueFloat
                FROM evesde_dgmtypeattributes
                WHERE typeID = ? AND attributeID = ?
            """, [type_id, attr_id])
            row = cursor.fetchone()
            if row:
                value = row[1] if row[1] is not None else row[0]
                if value is not None:
                    attrs[name] = float(value)

    return attrs


def _module_comparison(request: HttpRequest, base: InvTypes) -> HttpResponse:
    """Render module-specific comparison view."""
    from django.conf import settings
    original_debug = settings.DEBUG
    settings.DEBUG = False

    try:
        # Get base item attributes
        base_attrs = _get_module_attributes(base.type_id)

        # Get all variants
        variants_qs = InvMetaTypes.objects.filter(
            parent_type_id=base.type_id
        ).select_related('type', 'meta_group').order_by('meta_group__meta_group_id', 'type__name')

        # Build variant data with attributes
        variants_data = []
        for v in variants_qs:
            variant_attrs = _get_module_attributes(v.type_id)
            variants_data.append({
                'item': v.type,
                'meta': v,
                'attrs': variant_attrs,
            })

        # Determine which combat stats are relevant (appear in any variant)
        all_attrs = set(base_attrs.keys())
        for v in variants_data:
            all_attrs.update(v['attrs'].keys())

        # Define combat stats with labels and whether higher is better
        combat_stat_defs = {
            'damage': {'label': 'Damage', 'high_is_good': True},
            'rof': {'label': 'ROF', 'high_is_good': False},  # Lower ROF is better
            'range': {'label': 'Range', 'high_is_good': True},
            'falloff': {'label': 'Falloff', 'high_is_good': True},
            'tracking': {'label': 'Tracking', 'high_is_good': True},
            'shield_boost': {'label': 'Shield Boost', 'high_is_good': True},
            'armor_repair': {'label': 'Armor Rep', 'high_is_good': True},
            'capacitor_boost': {'label': 'Cap Boost', 'high_is_good': True},
        }

        # Filter to only stats that appear in our items
        combat_stats = []
        for attr_name in ['damage', 'rof', 'range', 'falloff', 'tracking',
                         'shield_boost', 'armor_repair', 'capacitor_boost']:
            if attr_name in all_attrs:
                combat_stats.append({
                    'attr_name': attr_name,
                    **combat_stat_defs[attr_name]
                })

        return render(request, 'core/sde/module_comparison.html', {
            'base': base,
            'base_attrs': base_attrs,
            'variants': variants_data,
            'combat_stats': combat_stats,
            'all_items': [base] + [v['item'] for v in variants_data],
        })

    finally:
        settings.DEBUG = original_debug


def _general_variant_comparison(request: HttpRequest, base: InvTypes) -> HttpResponse:
    """Render general variant comparison view (for non-modules)."""
    # Get all variants that reference this as parent
    variants = InvMetaTypes.objects.filter(
        parent_type_id=base.type_id
    ).select_related('type', 'meta_group').order_by('meta_group__meta_group_id')

    # Group by tier for display
    tiers = {}
    for v in variants:
        tier = v.meta_group.meta_group_name
        if tier not in tiers:
            tiers[tier] = []
        tiers[tier].append({
            'variant': v,
            'item': v.type,
        })

    # Also get attributes for the base item for comparison
    base_attrs = DgmTypeAttributes.objects.filter(
        type_id=base.type_id
    ).select_related('attribute')[:20]  # Limit for performance

    base_attributes = {}
    for attr in base_attrs:
        value = attr.value_float if attr.value_float is not None else attr.value_int
        base_attributes[attr.attribute.attribute_name] = value

    return render(request, 'core/sde/variant_comparison.html', {
        'base': base,
        'tiers': tiers,
        'base_attributes': base_attributes,
        'total_variants': variants.count(),
    })


def sde_market_group_detail(request: HttpRequest, group_id: int) -> HttpResponse:
    """Detail page for a market group (shows hierarchy and items)."""
    try:
        market_group = InvMarketGroups.objects.get(market_group_id=group_id)
    except InvMarketGroups.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Market Group {group_id} not found',
        }, status=404)

    # Build breadcrumb trail
    breadcrumb = []
    current = market_group
    while current:
        breadcrumb.insert(0, current)
        # Get parent
        if current.parent_group_id:
            try:
                current = InvMarketGroups.objects.get(market_group_id=current.parent_group_id)
            except InvMarketGroups.DoesNotExist:
                break
        else:
            break

    # Get child market groups
    child_groups = InvMarketGroups.objects.filter(
        parent_group_id=group_id
    ).order_by('market_group_name')

    # Get items in this market group
    items = InvTypes.objects.filter(
        market_group_id=group_id,
        published=True
    ).select_related('group').order_by('name')

    # Paginate items
    page = request.GET.get('page', 1)
    paginator = Paginator(items, 50)
    items_page = paginator.get_page(page)

    return render(request, 'core/sde/market_group_detail.html', {
        'market_group': market_group,
        'breadcrumb': breadcrumb,
        'child_groups': child_groups,
        'items': items_page,
    })


def get_ship_mastery_data(ship_id: int) -> dict:
    """
    Get mastery certificate data for a ship.

    Returns a dictionary with mastery levels (1-5) as keys,
    each containing a list of required certificates with their skills.
    """
    mastery_data = {}

    # Get all mastery levels for this ship
    masteries = CertMasteries.objects.filter(
        type_id=ship_id
    ).select_related('cert').order_by('mastery_level')

    # Group by mastery level
    for mastery in masteries:
        level = mastery.mastery_level
        if level not in mastery_data:
            mastery_data[level] = []

        # Get certificate details
        cert = mastery.cert

        # Get skills required for this certificate
        cert_skills = CertSkills.objects.filter(
            cert_id=cert.cert_id
        ).select_related('skill')

        skills = []
        for cert_skill in cert_skills:
            try:
                skill_type = InvTypes.objects.get(type_id=cert_skill.skill_id)
                skills.append({
                    'skill': skill_type,
                    'required_level': cert_skill.skill_level,
                    'cert_level': cert_skill.cert_level_int,
                })
            except InvTypes.DoesNotExist:
                pass

        mastery_data[level].append({
            'certificate': cert,
            'skills': skills,
        })

    return mastery_data


def sde_ship_detail(request: HttpRequest, ship_id: int) -> HttpResponse:
    """
    Detail page for a ship with mastery certificates.

    Shows:
    - Ship information and fitting stats
    - Required skills to fly
    - Mastery certificates (levels 1-5)
    - Variants and related ships
    """
    # Get the ship item
    try:
        ship = InvTypes.objects.select_related(
            'group', 'group__category', 'market_group', 'race', 'meta_type', 'meta_type__meta_group'
        ).get(type_id=ship_id, published=True)
    except InvTypes.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Ship {ship_id} not found',
        }, status=404)

    # Verify this is a ship (category 6)
    if ship.group.category_id != 6:
        return render(request, 'core/error.html', {
            'message': f'Item {ship_id} is not a ship',
        }, status=400)

    # Get fitting attributes
    fitting = get_ship_fitting(ship_id)

    # Calculate capacitor regeneration rate (capacity / rechargeRate * 5)
    # EVE formula: (capacity / rechargeRate) * 5 = GJ/s
    if fitting.get('capacitorCapacity') and fitting.get('rechargeRate'):
        fitting['capacitorRegen'] = fitting['capacitorCapacity'] / fitting['rechargeRate'] * 5
    else:
        fitting['capacitorRegen'] = None

    # Get mastery certificate data
    mastery_data = get_ship_mastery_data(ship_id)

    # Get required skills (from attributes)
    required_skills = []
    with connection.cursor() as cursor:
        # Required skills are stored in attributes 182, 183, 184, 277, 278, 279, 1289, 1290
        req_attr_ids = [182, 183, 184, 277, 278, 279, 1289, 1290]
        placeholders = ','.join(str(x) for x in req_attr_ids)

        cursor.execute("""
            SELECT ta.attributeID, ta.valueInt, t.typeName, t.typeID, g.groupName
            FROM evesde_dgmtypeattributes ta
            JOIN evesde_invtypes t ON ta.valueInt = t.typeID
            JOIN evesde_invgroups g ON t.groupID = g.groupID
            WHERE ta.typeID = %s AND ta.attributeID IN (%s)
            ORDER BY ta.attributeID
        """ % (ship_id, placeholders))

        skill_attr_map = {
            182: 1, 183: 2, 184: 3, 277: 4, 278: 5, 279: 6,
            1289: 1, 1290: 2  # Secondary skills
        }

        for attr_id, skill_type_id, skill_name, type_id, group_name in cursor.fetchall():
            required_level = skill_attr_map.get(attr_id, 1)
            required_skills.append({
                'type_id': type_id,
                'name': skill_name,
                'required_level': required_level,
                'group': group_name,
            })

    # Get variants (ships that have this ship as parent)
    variants = InvMetaTypes.objects.filter(
        parent_type_id=ship_id
    ).select_related('type', 'meta_group').order_by('meta_group__meta_group_id')

    # Get related ships (same group, excluding self)
    related_ships = InvTypes.objects.filter(
        group_id=ship.group_id,
        published=True
    ).exclude(type_id=ship_id)[:10]

    return render(request, 'core/sde/ship_detail.html', {
        'ship': ship,
        'fitting': fitting,
        'required_skills': required_skills,
        'mastery_data': mastery_data,
        'variants': variants,
        'related_ships': related_ships,
    })


def sde_blueprint_detail(request: HttpRequest, blueprint_id: int) -> HttpResponse:
    """
    Detail page for a blueprint with manufacturing calculator.

    Shows:
    - Blueprint information
    - Product it manufactures
    - Manufacturing materials required
    - Skills required
    - Production limits and time
    """
    # Get the blueprint item
    try:
        blueprint = InvTypes.objects.select_related(
            'group', 'group__category'
        ).get(type_id=blueprint_id, published=True)
    except InvTypes.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Blueprint {blueprint_id} not found',
        }, status=404)

    # Verify this is a blueprint (category 9)
    if blueprint.group.category_id != 9:
        return render(request, 'core/error.html', {
            'message': f'Item {blueprint_id} is not a blueprint',
        }, status=400)

    # Find the product this blueprint manufactures
    # Blueprints are named "XXX Blueprint", so we strip " Blueprint" to find the product
    product_name = blueprint.name.replace(' Blueprint', '')

    product = None
    try:
        product = InvTypes.objects.select_related(
            'group', 'group__category'
        ).get(name=product_name, published=True)
    except InvTypes.DoesNotExist:
        # Some blueprints may not follow the naming convention
        pass

    # Get blueprint industry metadata
    blueprint_meta = None
    try:
        blueprint_meta = IndustryBlueprints.objects.get(type_id=blueprint_id)
    except IndustryBlueprints.DoesNotExist:
        pass

    # Get manufacturing materials (from the product, not the blueprint)
    materials = []
    material_groups = {}
    total_materials_count = 0

    if product:
        # Use raw SQL to get materials (InvTypeMaterials doesn't have a proper PK)
        from django.conf import settings
        original_debug = settings.DEBUG
        settings.DEBUG = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT m.materialTypeID, t.typeName, g.groupName, m.quantity, t.volume, t.basePrice
                    FROM evesde_invtypematerials m
                    JOIN evesde_invtypes t ON m.materialTypeID = t.typeID
                    JOIN evesde_invgroups g ON t.groupID = g.groupID
                    WHERE m.typeID = ?
                    ORDER BY g.groupName, t.typeName
                """, [product.type_id])

                for row in cursor.fetchall():
                    mat_id, mat_name, group_name, quantity, volume, base_price = row

                    material = {
                        'type_id': mat_id,
                        'name': mat_name,
                        'group': group_name,
                        'quantity': quantity,
                        'volume': volume,
                        'base_price': base_price,
                    }
                    materials.append(material)

                    # Group by material category
                    if group_name not in material_groups:
                        material_groups[group_name] = []
                    material_groups[group_name].append(material)

                    total_materials_count += 1
        finally:
            settings.DEBUG = original_debug

    # Calculate estimated manufacturing cost (sum of base prices)
    estimated_cost = sum(
        m['quantity'] * (m['base_price'] or 0)
        for m in materials
    )

    # Get blueprint attributes (manufacturing time, research times, etc.)
    blueprint_attributes = {}
    from django.conf import settings
    original_debug = settings.DEBUG
    settings.DEBUG = False
    try:
        with connection.cursor() as cursor:
            # Industry-related attribute IDs
            industry_attr_ids = [33, 128, 727, 728, 1318, 1319, 1320,
                                1321, 1322, 1323, 1324, 1325, 1326, 1327, 1328]

            placeholders = ','.join(str(x) for x in industry_attr_ids)
            cursor.execute("""
                SELECT ta.attributeID, at.attributeName, ta.valueInt, ta.valueFloat, at.displayName
                FROM dgmTypeAttributes ta
                JOIN dgmAttributeTypes at ON ta.attributeID = at.attributeID
                WHERE ta.typeID = ? AND ta.attributeID IN (""" + placeholders + """)
                ORDER BY ta.attributeID
            """, [blueprint_id])

            for attr_id, attr_name, val_int, val_float, display_name in cursor.fetchall():
                value = val_float if val_float is not None else val_int
                blueprint_attributes[attr_id] = {
                    'name': display_name or attr_name,
                    'value': value,
                    'attribute_id': attr_id,
                    'formatted_value': format_time(value) if attr_id in [1318, 1321, 1323, 1325, 1327] else value,
                }
    finally:
        settings.DEBUG = original_debug

    # Get related blueprints (same group)
    related_blueprints = InvTypes.objects.filter(
        group_id=blueprint.group_id,
        published=True
    ).exclude(type_id=blueprint_id)[:10]

    # Get quantity for manufacturing calculator
    quantity = int(request.GET.get('qty', 1))
    if quantity < 1:
        quantity = 1
    if quantity > 1000:
        quantity = 1000

    # Check if invention is possible (T2 blueprint check)
    is_t2_blueprint = False
    invention_info = None

    # Tech 2 items typically have techLevel attribute = 2
    if 128 in blueprint_attributes:
        tech_level = blueprint_attributes[128]['value']
        is_t2_blueprint = tech_level == 2

    # Get blueprints that could invent this blueprint (T1 version)
    if is_t2_blueprint:
        # Try to find T1 version by removing "II" and adding "I"
        t1_product_name = product_name.replace(' II', ' I') if product else None
        if t1_product_name:
            try:
                t1_product = InvTypes.objects.get(name=t1_product_name, published=True)
                t1_blueprint_name = f"{t1_product_name} Blueprint"
                try:
                    t1_blueprint = InvTypes.objects.get(name=t1_blueprint_name, published=True)
                    invention_info = {
                        't1_blueprint': t1_blueprint,
                        't1_product': t1_product,
                    }
                except InvTypes.DoesNotExist:
                    pass
            except InvTypes.DoesNotExist:
                pass

    # Calculate total costs for the requested quantity
    total_estimated_cost = estimated_cost * quantity

    # Calculate material totals for the quantity and enhanced cost data
    total_material_volume = 0
    for material in materials:
        material['total_quantity'] = material['quantity'] * quantity
        if material['base_price']:
            material['total_cost'] = material['base_price'] * material['total_quantity']
            material['single_run_cost'] = material['base_price'] * material['quantity']
            material['cost_percentage'] = (material['total_cost'] / total_estimated_cost * 100) if total_estimated_cost > 0 else 0
        else:
            material['total_cost'] = 0
            material['single_run_cost'] = 0
            material['cost_percentage'] = 0

        # Calculate volume (quantity * volume per unit)
        if material['volume']:
            material['total_volume'] = material['volume'] * material['total_quantity']
            total_material_volume += material['total_volume']
        else:
            material['total_volume'] = 0

    # Get top 5 most expensive materials
    most_expensive_materials = sorted(
        [m for m in materials if m['base_price']],
        key=lambda x: x['total_cost'],
        reverse=True
    )[:5]

    # Calculate cost per unit
    cost_per_unit = total_estimated_cost / quantity if quantity > 0 else 0

    # Build shopping list grouped by category
    shopping_list_by_category = {}
    for group_name, group_materials in material_groups.items():
        shopping_items = []
        for material in group_materials:
            shopping_items.append({
                'name': material['name'],
                'quantity': material['total_quantity'],
                'quantity_formatted': f"{material['total_quantity']:,.0f}",
                'type_id': material['type_id'],
            })
        shopping_list_by_category[group_name] = shopping_items

    # Build plain text shopping list for copy/paste
    shopping_list_text = []
    shopping_list_text.append(f"Shopping List for {quantity}x {product.name if product else blueprint.name}")
    shopping_list_text.append("=" * 60)
    for group_name in sorted(shopping_list_by_category.keys()):
        shopping_list_text.append(f"\n[{group_name}]")
        for item in shopping_list_by_category[group_name]:
            shopping_list_text.append(f"  {item['name']} x {item['quantity_formatted']}")
    shopping_list_text.append(f"\nTotal Materials: {len(materials)} types")
    shopping_list_text.append(f"Total Volume: {total_material_volume:,.2f} m³")
    if total_estimated_cost > 0:
        shopping_list_text.append(f"Estimated Cost: {total_estimated_cost:,.2f} ISK")
    shopping_list_plain = "\n".join(shopping_list_text)

    # Format time attributes (seconds to human-readable)
    def format_time(seconds):
        if not seconds:
            return None
        hours = seconds / 3600
        if hours < 1:
            return f"{int(seconds / 60)}m"
        elif hours < 24:
            return f"{int(hours)}h {int((hours % 1) * 60)}m"
        else:
            days = int(hours / 24)
            return f"{days}d {int((hours % 24) * 60)}h"

    return render(request, 'core/sde/blueprint_detail.html', {
        'blueprint': blueprint,
        'product': product,
        'blueprint_meta': blueprint_meta,
        'materials': materials,
        'material_groups': material_groups,
        'total_materials_count': total_materials_count,
        'estimated_cost': estimated_cost,
        'total_estimated_cost': total_estimated_cost,
        'blueprint_attributes': blueprint_attributes,
        'related_blueprints': related_blueprints,
        'quantity': quantity,
        'is_t2_blueprint': is_t2_blueprint,
        'invention_info': invention_info,
        'format_time': format_time,
        # Enhanced cost and shopping list data
        'most_expensive_materials': most_expensive_materials,
        'total_material_volume': total_material_volume,
        'cost_per_unit': cost_per_unit,
        'shopping_list_by_category': shopping_list_by_category,
        'shopping_list_plain': shopping_list_plain,
    })


def sde_certificate_detail(request: HttpRequest, cert_id: int) -> HttpResponse:
    """
    Detail page for a certificate.

    Shows:
    - Certificate name and description
    - Required skills for each level (0-4)
    - Ships that require this certificate for mastery
    """
    try:
        certificate = CertCerts.objects.get(cert_id=cert_id)
    except CertCerts.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Certificate {cert_id} not found',
        }, status=404)

    # Get skill requirements for all levels, grouped by level
    # Use raw SQL to avoid Django model issues with composite keys
    skill_requirements = {}
    from django.conf import settings
    original_debug = settings.DEBUG
    settings.DEBUG = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT cs.certLevelInt, cs.skillLevel, cs.certLevelText,
                       t.typeID, t.typeName, g.groupName, t.description
                FROM evesde_certskills cs
                JOIN evesde_invtypes t ON cs.skillID = t.typeID
                JOIN evesde_invgroups g ON t.groupID = g.groupID
                WHERE cs.certID = ?
                ORDER BY cs.certLevelInt, t.typeName
            """, [cert_id])

            for row in cursor.fetchall():
                cert_level, skill_level, level_text, skill_id, skill_name, group_name, description = row
                level = int(cert_level)
                if level not in skill_requirements:
                    skill_requirements[level] = []
                skill_requirements[level].append({
                    'skill_id': skill_id,
                    'name': skill_name,
                    'group': group_name,
                    'description': description,
                    'required_level': skill_level,
                    'level_text': level_text,
                })
    finally:
        settings.DEBUG = original_debug

    # Get mastery information (ships that require this certificate)
    mastery_ships = {}
    settings.DEBUG = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT cm.masteryLevel, t.typeID, t.typeName, g.groupName
                FROM evesde_certmasteries cm
                JOIN evesde_invtypes t ON cm.typeID = t.typeID
                JOIN evesde_invgroups g ON t.groupID = g.groupID
                WHERE cm.certID = ? AND t.published = 1
                ORDER BY cm.masteryLevel, g.groupName, t.typeName
            """, [cert_id])

            for row in cursor.fetchall():
                mastery_level, ship_id, ship_name, group_name = row
                level = int(mastery_level)
                if level not in mastery_ships:
                    mastery_ships[level] = []
                mastery_ships[level].append({
                    'type_id': ship_id,
                    'name': ship_name,
                    'group': group_name,
                })
    finally:
        settings.DEBUG = original_debug

    # Level names for display
    level_names = {
        0: 'Basic',
        1: 'Standard',
        2: 'Improved',
        3: 'Advanced',
        4: 'Elite',
    }

    # Count total requirements and masteries
    total_skill_reqs = sum(len(reqs) for reqs in skill_requirements.values())
    total_mastery_ships = sum(len(ships) for ships in mastery_ships.values())

    return render(request, 'core/sde/certificate_detail.html', {
        'certificate': certificate,
        'skill_requirements': skill_requirements,
        'mastery_ships': mastery_ships,
        'level_names': level_names,
        'total_skill_reqs': total_skill_reqs,
        'total_mastery_ships': total_mastery_ships,
        'cert_levels': [0, 1, 2, 3, 4],
    })


# ============================================================================
# Agents & NPC Browser
# ============================================================================

def sde_faction_list(request: HttpRequest) -> HttpResponse:
    """List all factions."""
    factions = ChrFactions.objects.all().order_by('faction_name')

    # Count corporations per faction
    faction_stats = {}
    for faction in factions:
        corp_count = CrpNPCCorporations.objects.filter(faction_id=faction.faction_id).count()
        faction_stats[faction.faction_id] = {
            'corporation_count': corp_count,
        }

    return render(request, 'core/sde/faction_list.html', {
        'factions': factions,
        'faction_stats': faction_stats,
    })


def sde_faction_detail(request: HttpRequest, faction_id: int) -> HttpResponse:
    """Detail page for a faction."""
    try:
        faction = ChrFactions.objects.get(faction_id=faction_id)
    except ChrFactions.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Faction {faction_id} not found',
        }, status=404)

    # Get member corporations
    corporations = CrpNPCCorporations.objects.filter(
        faction_id=faction_id
    ).order_by('corporation_id')

    # Get corporation names from InvNames
    corp_list = []
    for corp in corporations:
        try:
            name_obj = InvNames.objects.get(item_id=corp.corporation_id)
            corp_name = name_obj.item_name
        except InvNames.DoesNotExist:
            corp_name = f'Corporation {corp.corporation_id}'

        # Count agents for this corporation
        agent_count = AgtAgents.objects.filter(corporation_id=corp.corporation_id).count()

        corp_list.append({
            'corporation': corp,
            'name': corp_name,
            'agent_count': agent_count,
        })

    # Get solar systems controlled by this faction
    controlled_systems = MapSolarSystems.objects.filter(
        faction_id=faction_id
    ).order_by('system_name')[:20]

    # Get militia corporation if applicable
    militia_corp = None
    militia_corp_name = None
    if faction.militia_corporation_id:
        try:
            militia_corp = CrpNPCCorporations.objects.get(
                corporation_id=faction.militia_corporation_id
            )
            militia_name_obj = InvNames.objects.get(item_id=militia_corp.corporation_id)
            militia_corp_name = militia_name_obj.item_name
        except (CrpNPCCorporations.DoesNotExist, InvNames.DoesNotExist):
            pass

    return render(request, 'core/sde/faction_detail.html', {
        'faction': faction,
        'corporations': corp_list,
        'controlled_systems': controlled_systems,
        'militia_corp': militia_corp,
        'militia_corp_name': militia_corp_name,
    })


def sde_corporation_detail(request: HttpRequest, corporation_id: int) -> HttpResponse:
    """Detail page for an NPC corporation."""
    try:
        corporation = CrpNPCCorporations.objects.get(corporation_id=corporation_id)
    except CrpNPCCorporations.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Corporation {corporation_id} not found',
        }, status=404)

    # Get corporation name from InvNames
    try:
        name_obj = InvNames.objects.get(item_id=corporation_id)
        corporation_name = name_obj.item_name
    except InvNames.DoesNotExist:
        corporation_name = f'Corporation {corporation_id}'

    # Get faction
    faction = None
    if corporation.faction_id:
        try:
            faction = ChrFactions.objects.get(faction_id=corporation.faction_id)
        except ChrFactions.DoesNotExist:
            pass

    # Get agents employed by this corporation
    agents = AgtAgents.objects.filter(
        corporation_id=corporation_id
    ).order_by('-level', 'agent_id')

    # Get agent details with location info
    agent_list = []
    for agent in agents[:50]:  # Limit to 50 agents
        # Get agent type
        agent_type = None
        if agent.agent_type_id:
            try:
                agent_type = AgtAgentTypes.objects.get(agent_type_id=agent.agent_type_id)
            except AgtAgentTypes.DoesNotExist:
                pass

        # Get station info
        station = None
        system = None
        if agent.location_id:
            try:
                station = StaStations.objects.get(station_id=agent.location_id)
                system = station.solar_system
            except StaStations.DoesNotExist:
                pass

        agent_list.append({
            'agent': agent,
            'agent_type': agent_type,
            'station': station,
            'system': system,
        })

    # Get stations owned by this corporation
    stations = StaStations.objects.filter(
        corporation_id=corporation_id
    ).select_related('solar_system', 'region').order_by('station_name')[:20]

    return render(request, 'core/sde/corporation_detail.html', {
        'corporation': corporation,
        'corporation_name': corporation_name,
        'faction': faction,
        'agents': agent_list,
        'stations': stations,
    })


def sde_agent_detail(request: HttpRequest, agent_id: int) -> HttpResponse:
    """Detail page for an agent."""
    try:
        agent = AgtAgents.objects.get(agent_id=agent_id)
    except AgtAgents.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Agent {agent_id} not found',
        }, status=404)

    # Get corporation info
    corporation = None
    corporation_name = None
    faction = None
    if agent.corporation_id:
        try:
            corporation = CrpNPCCorporations.objects.get(
                corporation_id=agent.corporation_id
            )
            # Get corporation name
            name_obj = InvNames.objects.get(item_id=agent.corporation_id)
            corporation_name = name_obj.item_name

            # Get faction
            if corporation.faction_id:
                faction = ChrFactions.objects.get(faction_id=corporation.faction_id)
        except (CrpNPCCorporations.DoesNotExist, InvNames.DoesNotExist, ChrFactions.DoesNotExist):
            pass

    # Get agent type
    agent_type = None
    if agent.agent_type_id:
        try:
            agent_type = AgtAgentTypes.objects.get(agent_type_id=agent.agent_type_id)
        except AgtAgentTypes.DoesNotExist:
            pass

    # Get station/location info
    station = None
    system = None
    region = None
    if agent.location_id:
        try:
            station = StaStations.objects.select_related(
                'solar_system', 'solar_system__region', 'solar_system__constellation'
            ).get(station_id=agent.location_id)
            system = station.solar_system
            region = system.region
        except StaStations.DoesNotExist:
            pass

    # Get division info (from CrpActivities)
    division_name = None
    if agent.division_id:
        from core.sde.models import CrpActivities
        try:
            division = CrpActivities.objects.get(activity_id=agent.division_id)
            division_name = division.activity_name
        except CrpActivities.DoesNotExist:
            pass

    return render(request, 'core/sde/agent_detail.html', {
        'agent': agent,
        'corporation': corporation,
        'corporation_name': corporation_name,
        'faction': faction,
        'agent_type': agent_type,
        'station': station,
        'system': system,
        'region': region,
        'division_name': division_name,
    })


def sde_industry_activities(request: HttpRequest) -> HttpResponse:
    """
    Industry activity browser showing blueprints by activity type.

    Activity Types:
    - 1: Manufacturing (building items)
    - 3: Time Efficiency Research (TE research)
    - 4: Material Efficiency Research (ME research)
    - 5: Invention (T2/T3 invention)
    - 8: Reactions (moon gas, polymer reactions)

    Shows:
    - Activity type tabs
    - Blueprints that support each activity
    - Product outputs
    - Material requirements
    - Skill requirements
    """
    # Get selected activity type from query params
    selected_activity = request.GET.get('activity', '1')

    # Activity type definitions
    ACTIVITY_TYPES = {
        '1': {'name': 'Manufacturing', 'icon': '🏭', 'description': 'Build items from blueprints'},
        '3': {'name': 'TE Research', 'icon': '⏱️', 'description': 'Reduce manufacturing time'},
        '4': {'name': 'ME Research', 'icon': '📉', 'description': 'Reduce material requirements'},
        '5': {'name': 'Invention', 'icon': '💡', 'description': 'Create T2/T3 blueprint copies'},
        '8': {'name': 'Reactions', 'icon': '⚗️', 'description': 'Moon gas and polymer reactions'},
    }

    activity_info = ACTIVITY_TYPES.get(selected_activity, ACTIVITY_TYPES['1'])
    activity_id = int(selected_activity)

    # Get blueprints that support this activity
    # Blueprints are in category 9
    blueprints_with_activity = []

    # Use raw SQL for better performance with composite key tables
    from django.conf import settings
    original_debug = settings.DEBUG
    settings.DEBUG = False

    try:
        with connection.cursor() as cursor:
            # Get all blueprints that have this activity
            cursor.execute("""
                SELECT DISTINCT
                    ia.typeID,
                    t.typeName,
                    t.description,
                    g.groupName,
                    ia.time,
                    ib.maxProductionLimit
                FROM evesde_industryactivity ia
                JOIN evesde_invtypes t ON ia.typeID = t.typeID
                JOIN evesde_invgroups g ON t.groupID = g.groupID
                LEFT JOIN evesde_industryblueprints ib ON ia.typeID = ib.typeID
                WHERE ia.activityID = ?
                    AND t.published = 1
                    AND g.categoryID = 9
                ORDER BY g.groupName, t.typeName
                LIMIT 500
            """, [activity_id])

            blueprint_rows = cursor.fetchall()

            # For each blueprint, get products and materials
            for bp_row in blueprint_rows:
                bp_type_id, bp_name, bp_desc, group_name, time_val, max_limit = bp_row

                # Get product for this activity
                cursor.execute("""
                    SELECT iap.productTypeID, t.typeName, iap.quantity
                    FROM evesde_industryactivityproducts iap
                    JOIN evesde_invtypes t ON iap.productTypeID = t.typeID
                    WHERE iap.typeID = ? AND iap.activityID = ?
                """, [bp_type_id, activity_id])

                product_row = cursor.fetchone()
                product = None
                if product_row:
                    product = {
                        'type_id': product_row[0],
                        'name': product_row[1],
                        'quantity': product_row[2],
                    }

                # Get top 5 materials for this activity
                cursor.execute("""
                    SELECT iam.materialTypeID, t.typeName, g.groupName, iam.quantity
                    FROM evesde_industryactivitymaterials iam
                    JOIN evesde_invtypes t ON iam.materialTypeID = t.typeID
                    JOIN evesde_invgroups g ON t.groupID = g.groupID
                    WHERE iam.typeID = ? AND iam.activityID = ?
                    ORDER BY iam.quantity DESC
                    LIMIT 5
                """, [bp_type_id, activity_id])

                material_rows = cursor.fetchall()
                materials = []
                for mat_row in material_rows:
                    materials.append({
                        'type_id': mat_row[0],
                        'name': mat_row[1],
                        'group': mat_row[2],
                        'quantity': mat_row[3],
                    })

                # Get skill requirements
                cursor.execute("""
                    SELECT ias.skillID, t.typeName, g.groupName, ias.level
                    FROM evesde_industryactivityskills ias
                    JOIN evesde_invtypes t ON ias.skillID = t.typeID
                    JOIN evesde_invgroups g ON t.groupID = g.groupID
                    WHERE ias.typeID = ? AND ias.activityID = ?
                    ORDER BY ias.level DESC, t.typeName
                """, [bp_type_id, activity_id])

                skill_rows = cursor.fetchall()
                skills = []
                for skill_row in skill_rows:
                    skills.append({
                        'type_id': skill_row[0],
                        'name': skill_row[1],
                        'group': skill_row[2],
                        'level': skill_row[3],
                    })

                blueprints_with_activity.append({
                    'type_id': bp_type_id,
                    'name': bp_name,
                    'description': bp_desc,
                    'group': group_name,
                    'time': time_val,
                    'max_production_limit': max_limit,
                    'product': product,
                    'materials': materials,
                    'skills': skills,
                })
    finally:
        settings.DEBUG = original_debug

    # Get activity counts for the tabs
    activity_counts = {}
    for act_id_key in ACTIVITY_TYPES.keys():
        try:
            count = IndustryActivity.objects.filter(
                activity_id=int(act_id_key),
                type__group__category_id=9,
                type__published=True
            ).count()
            activity_counts[act_id_key] = count
        except:
            activity_counts[act_id_key] = 0

    return render(request, 'core/sde/industry_activity.html', {
        'activity_types': ACTIVITY_TYPES,
        'selected_activity': selected_activity,
        'activity_info': activity_info,
        'activity_id': activity_id,
        'blueprints': blueprints_with_activity,
        'activity_counts': activity_counts,
        'total_blueprints': len(blueprints_with_activity),
    })


# ============================================================================
# Route Planner
# ============================================================================

def sde_route_planner(request: HttpRequest) -> HttpResponse:
    """
    Route planner for finding paths between solar systems.

    Supports three route types:
    - shortest: Minimum number of jumps (BFS)
    - safest: Prefers highsec, penalizes lowsec/nullsec (weighted Dijkstra)
    - fastest: Considers security and avoids dangerous space (weighted Dijkstra)

    Uses raw SQL for efficient graph traversal.
    """
    origin_id = request.GET.get('origin_id')
    destination_id = request.GET.get('destination_id')
    route_type = request.GET.get('route_type', 'shortest')

    route = []
    error = None
    origin_system = None
    destination_system = None
    total_jumps = 0
    estimated_time = None
    route_stats = {}

    if origin_id and destination_id:
        try:
            origin_id = int(origin_id)
            destination_id = int(destination_id)

            # Get origin and destination systems
            origin_system = MapSolarSystems.objects.select_related(
                'region', 'constellation'
            ).get(system_id=origin_id)

            destination_system = MapSolarSystems.objects.select_related(
                'region', 'constellation'
            ).get(system_id=destination_id)

            # Calculate route
            if origin_id == destination_id:
                route = [origin_system]
                total_jumps = 0
            else:
                route = find_route(origin_id, destination_id, route_type)
                if route:
                    total_jumps = len(route) - 1
                    # Estimated time: ~1 minute per jump in highsec, ~2 min in lowsec, ~3 min in nullsec
                    base_time = sum(1 if sys.security >= 0.45 else 2 if sys.security >= 0.05 else 3 for sys in route)
                    estimated_time = f"{base_time} minutes"

                    # Calculate route statistics
                    security_counts = {'highsec': 0, 'lowsec': 0, 'nullsec': 0, 'wormhole': 0}
                    region_changes = 0
                    constellation_changes = 0
                    last_region = route[0].region_id
                    last_constellation = route[0].constellation_id

                    for sys in route:
                        if sys.security >= 0.45:
                            security_counts['highsec'] += 1
                        elif sys.security >= 0.05:
                            security_counts['lowsec'] += 1
                        elif sys.security >= 0:
                            security_counts['nullsec'] += 1
                        else:
                            security_counts['wormhole'] += 1

                        if sys.region_id != last_region:
                            region_changes += 1
                            last_region = sys.region_id
                        if sys.constellation_id != last_constellation:
                            constellation_changes += 1
                            last_constellation = sys.constellation_id

                    route_stats = {
                        'security_counts': security_counts,
                        'region_changes': region_changes,
                        'constellation_changes': constellation_changes,
                    }
                else:
                    error = "No route found between these systems. They may be in disconnected areas of space (e.g., wormhole space)."

        except MapSolarSystems.DoesNotExist:
            error = "One or both systems not found."
        except ValueError:
            error = "Invalid system ID."
        except Exception as e:
            error = f"Error calculating route: {str(e)}"

    return render(request, 'core/sde/route_planner.html', {
        'origin_system': origin_system,
        'destination_system': destination_system,
        'route': route,
        'route_type': route_type,
        'total_jumps': total_jumps,
        'estimated_time': estimated_time,
        'error': error,
        'route_stats': route_stats,
    })


def find_route(origin_id: int, destination_id: int, route_type: str) -> list:
    """
    Find a route between two solar systems using graph traversal.

    Args:
        origin_id: Starting system ID
        destination_id: Target system ID
        route_type: 'shortest', 'safest', or 'fastest'

    Returns:
        List of MapSolarSystems objects representing the route, or empty list if no route found.
    """
    # Security weights for different route types
    # Returns weight multiplier based on security status
    def get_weight(security: float) -> float:
        if route_type == 'shortest':
            return 1.0  # All jumps equal weight
        elif route_type == 'safest':
            # Heavily penalize dangerous space
            if security >= 0.45:  # Highsec
                return 1.0
            elif security >= 0.05:  # Lowsec
                return 5.0
            elif security >= 0:  # Nullsec
                return 10.0
            else:  # Wormhole
                return 20.0
        else:  # fastest
            # Moderate penalty for dangerous space (assumes cautious travel)
            if security >= 0.45:  # Highsec
                return 1.0
            elif security >= 0.05:  # Lowsec
                return 2.0
            elif security >= 0:  # Nullsec
                return 3.0
            else:  # Wormhole
                return 5.0

    # Use raw SQL for efficient graph traversal
    # Dijkstra's algorithm with weighted edges
    from django.conf import settings
    original_debug = settings.DEBUG
    settings.DEBUG = False

    try:
        with connection.cursor() as cursor:
            # First, check if the jump table exists
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='evesde_mapsolarsystemjumps'
            """)
            jump_table_exists = cursor.fetchone() is not None

            if not jump_table_exists:
                # Fallback: Create a simple mock graph based on region/constellation adjacency
                # This is a simplified version that doesn't use actual stargate connections
                cursor.execute("""
                    SELECT
                        s1.solarSystemID,
                        s2.solarSystemID,
                        s2.security
                    FROM evesde_mapsolarsystems s1
                    CROSS JOIN evesde_mapsolarsystems s2
                    WHERE s1.solarSystemID != s2.solarSystemID
                        AND (
                            -- Same constellation (likely connected)
                            (s1.constellationID = s2.constellationID AND s1.solarSystemID < s2.solarSystemID)
                            OR
                            -- Adjacent constellations in same region
                            (s1.regionID = s2.regionID AND s1.constellationID != s2.constellationID
                             AND s1.solarSystemID < s2.solarSystemID
                             AND ABS(s1.security - s2.security) < 0.5)
                        )
                    LIMIT 10000
                """)

                # Build graph: {system_id: [(neighbor_id, weight), ...]}
                graph = {}

                for from_id, to_id, security in cursor.fetchall():
                    if from_id not in graph:
                        graph[from_id] = []
                    weight = get_weight(security or 0.0)
                    graph[from_id].append((to_id, weight))
            else:
                # Build adjacency list with security weights from actual jump table
                cursor.execute("""
                    SELECT
                        fromSolarSystemID,
                        toSolarSystemID,
                        s.security
                    FROM evesde_mapsolarsystemjumps j
                    JOIN evesde_mapsolarsystems s ON j.toSolarSystemID = s.solarSystemID
                """)

                # Build graph: {system_id: [(neighbor_id, weight), ...]}
                graph = {}
                system_security = {}

                for from_id, to_id, security in cursor.fetchall():
                    if from_id not in graph:
                        graph[from_id] = []
                    weight = get_weight(security or 0.0)
                    graph[from_id].append((to_id, weight))
                    system_security[to_id] = security or 0.0

            # Dijkstra's algorithm
            import heapq

            # Priority queue: (total_weight, current_system, path)
            pq = [(0, origin_id, [origin_id])]
            visited = set()
            max_iterations = 10000  # Prevent infinite loops
            iterations = 0

            while pq and iterations < max_iterations:
                iterations += 1
                total_weight, current, path = heapq.heappop(pq)

                if current in visited:
                    continue
                visited.add(current)

                if current == destination_id:
                    # Found destination! Build the route
                    route_systems = MapSolarSystems.objects.filter(
                        system_id__in=path
                    ).select_related('region', 'constellation')

                    # Maintain path order
                    system_map = {sys.system_id: sys for sys in route_systems}
                    return [system_map[sid] for sid in path if sid in system_map]

                if current not in graph:
                    continue

                for neighbor, weight in graph[current]:
                    if neighbor not in visited and len(path) < 50:  # Limit route depth
                        heapq.heappush(pq, (total_weight + weight, neighbor, path + [neighbor]))

            # No route found
            return []

    finally:
        settings.DEBUG = original_debug


def sde_skills_directory(request: HttpRequest) -> HttpResponse:
    """
    Comprehensive skills directory and overview page.

    Shows:
    - All skill groups with item counts
    - Attribute breakdown (primary/secondary attribute distribution)
    - Skill rank distribution (how many rank 1, rank 2, etc.)
    - Search/filter by name, attribute, rank
    - Sort options
    """
    # Get filter parameters
    search_query = request.GET.get('q', '').strip()
    primary_attr = request.GET.get('primary', '')
    secondary_attr = request.GET.get('secondary', '')
    rank_filter = request.GET.get('rank', '')
    sort_by = request.GET.get('sort', 'group')

    # EVE attribute IDs and names
    ATTRIBUTE_IDS = {
        'intelligence': 180,
        'perception': 181,
        'charisma': 182,
        'willpower': 183,
        'memory': 184,
    }

    ATTRIBUTE_NAMES = {
        'intelligence': 'Intelligence',
        'perception': 'Perception',
        'charisma': 'Charisma',
        'willpower': 'Willpower',
        'memory': 'Memory',
    }

    # Base queryset for skills (category 16)
    skills_queryset = InvTypes.objects.filter(
        group__category_id=16,
        published=True
    ).select_related('group')

    # Apply search filter
    if search_query and len(search_query) >= 2:
        skills_queryset = skills_queryset.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Get skill data with attributes using raw SQL for performance
    skills_data = []
    from django.conf import settings
    original_debug = settings.DEBUG
    settings.DEBUG = False

    try:
        with connection.cursor() as cursor:
            # Build the query with filters
            sql_query = """
                SELECT
                    t.typeID, t.typeName, t.description,
                    g.groupID, g.groupName,
                    COALESCE(ta1.valueInt, 0) as primaryAttribute,
                    COALESCE(ta2.valueInt, 0) as secondaryAttribute,
                    COALESCE(ta3.valueInt, 1) as skillRank
                FROM evesde_invtypes t
                JOIN evesde_invgroups g ON t.groupID = g.groupID
                LEFT JOIN evesde_dgmtypeattributes ta1 ON t.typeID = ta1.typeID AND ta1.attributeID = 180
                LEFT JOIN evesde_dgmtypeattributes ta2 ON t.typeID = ta2.typeID AND ta2.attributeID = 181
                LEFT JOIN evesde_dgmtypeattributes ta3 ON t.typeID = ta3.typeID AND ta3.attributeID = 275
                WHERE g.categoryID = 16 AND t.published = 1
            """
            params = []

            # Apply search filter in SQL
            if search_query and len(search_query) >= 2:
                sql_query += " AND (t.typeName LIKE ? OR t.description LIKE ?)"
                params.extend([f'%{search_query}%', f'%{search_query}%'])

            # Apply attribute filters
            if primary_attr and primary_attr in ATTRIBUTE_IDS:
                sql_query += " AND ta1.valueInt = ?"
                params.append(ATTRIBUTE_IDS[primary_attr])

            if secondary_attr and secondary_attr in ATTRIBUTE_IDS:
                sql_query += " AND ta2.valueInt = ?"
                params.append(ATTRIBUTE_IDS[secondary_attr])

            if rank_filter:
                try:
                    rank_val = int(rank_filter)
                    sql_query += " AND ta3.valueInt = ?"
                    params.append(rank_val)
                except ValueError:
                    pass

            # Apply sorting
            sort_options = {
                'name': 't.typeName ASC',
                'name_desc': 't.typeName DESC',
                'group': 'g.groupName, t.typeName',
                'rank': 'ta3.valueInt, t.typeName',
                'rank_desc': 'ta3.valueInt DESC, t.typeName',
            }

            order_by = sort_options.get(sort_by, 'g.groupName, t.typeName')
            sql_query += f" ORDER BY {order_by}"

            cursor.execute(sql_query, params)

            for row in cursor.fetchall():
                (type_id, name, description, group_id, group_name,
                 primary_val, secondary_val, rank_val) = row

                # Map attribute values to names
                attr_map = {
                    180: 'intelligence',
                    181: 'perception',
                    182: 'charisma',
                    183: 'willpower',
                    184: 'memory',
                }

                primary = attr_map.get(primary_val, 'intelligence')
                secondary = attr_map.get(secondary_val, 'memory')
                rank = int(rank_val) if rank_val else 1

                skills_data.append({
                    'type_id': type_id,
                    'name': name,
                    'description': description,
                    'group_id': group_id,
                    'group_name': group_name,
                    'primary': primary,
                    'secondary': secondary,
                    'rank': rank,
                })
    finally:
        settings.DEBUG = original_debug

    # Get all skill groups with counts (for group filter/sidebar)
    all_skill_groups = InvGroups.objects.filter(
        category_id=16,
        published=True
    ).annotate(
        skill_count=Count('types', filter=Q(types__published=True))
    ).filter(skill_count__gt=0).order_by('group_name')

    # Calculate attribute distributions
    primary_dist = {}
    secondary_dist = {}

    for skill in skills_data:
        p = skill['primary']
        s = skill['secondary']
        primary_dist[p] = primary_dist.get(p, 0) + 1
        secondary_dist[s] = secondary_dist.get(s, 0) + 1

    # Calculate rank distribution
    rank_dist = {}
    for skill in skills_data:
        r = skill['rank']
        rank_dist[r] = rank_dist.get(r, 0) + 1

    # Group skills by group for display
    skills_by_group = {}
    for skill in skills_data:
        group = skill['group_name']
        if group not in skills_by_group:
            skills_by_group[group] = []
        skills_by_group[group].append(skill)

    return render(request, 'core/sde/skills_directory.html', {
        'skills_by_group': skills_by_group,
        'all_skill_groups': all_skill_groups,
        'total_skills': len(skills_data),
        'total_groups': len(skills_by_group),
        'primary_distribution': primary_dist,
        'secondary_distribution': secondary_dist,
        'rank_distribution': rank_dist,
        'attribute_names': ATTRIBUTE_NAMES,
        'search_query': search_query,
        'primary_attr': primary_attr,
        'secondary_attr': secondary_attr,
        'rank_filter': rank_filter,
        'sort_by': sort_by,
        'has_filters': bool(search_query or primary_attr or secondary_attr or rank_filter),
    })


def sde_sitemap(request: HttpRequest) -> HttpResponse:
    """
    Comprehensive sitemap/overview page for SDE browser.

    Shows:
    - All categories with item counts
    - Top 50 groups by item count
    - All market groups with hierarchy
    - All meta groups
    - All factions
    - Special pages (Skills Directory, Route Planner, Industry Activities)
    - Statistics overview
    """
    # Get overall statistics
    stats = {
        'total_items': InvTypes.objects.filter(published=True).count(),
        'total_groups': InvGroups.objects.filter(published=True).count(),
        'total_categories': InvCategories.objects.filter(published=True).count(),
        'total_systems': MapSolarSystems.objects.count(),
        'total_regions': MapRegions.objects.count(),
        'total_constellations': MapConstellations.objects.count(),
        'total_factions': ChrFactions.objects.count(),
        'total_corporations': CrpNPCCorporations.objects.count(),
        'total_agents': AgtAgents.objects.count(),
        'total_stations': StaStations.objects.count(),
        'total_certificates': CertCerts.objects.count(),
        'total_blueprints': IndustryBlueprints.objects.count(),
    }

    # Get all categories with counts
    from django.conf import settings
    original_debug = settings.DEBUG
    settings.DEBUG = False

    try:
        with connection.cursor() as cursor:
            # Categories with item counts
            cursor.execute("""
                SELECT c.categoryID, c.categoryName, COUNT(DISTINCT t.typeID) as item_count
                FROM evesde_invcategories c
                LEFT JOIN evesde_invgroups g ON c.categoryID = g.categoryID
                LEFT JOIN evesde_invtypes t ON g.groupID = t.groupID AND t.published = 1
                WHERE c.published = 1
                GROUP BY c.categoryID, c.categoryName
                ORDER BY c.categoryName
            """)
            categories = [{'id': row[0], 'name': row[1], 'count': row[2]} for row in cursor.fetchall()]

            # Top 50 groups by item count
            cursor.execute("""
                SELECT g.groupID, g.groupName, c.categoryName, COUNT(DISTINCT t.typeID) as item_count
                FROM evesde_invgroups g
                JOIN evesde_invcategories c ON g.categoryID = c.categoryID
                LEFT JOIN evesde_invtypes t ON g.groupID = t.groupID AND t.published = 1
                WHERE g.published = 1 AND c.published = 1
                GROUP BY g.groupID, g.groupName, c.categoryName
                HAVING item_count > 0
                ORDER BY item_count DESC, g.groupName
                LIMIT 50
            """)
            top_groups = [{'id': row[0], 'name': row[1], 'category': row[2], 'count': row[3]} for row in cursor.fetchall()]

            # All market groups (top-level only with counts)
            cursor.execute("""
                SELECT mg.marketGroupID, mg.marketGroupName,
                       COUNT(DISTINCT t.typeID) as item_count,
                       (SELECT COUNT(*) FROM evesde_invmarketgroups WHERE parentGroupID = mg.marketGroupID) as child_count
                FROM evesde_invmarketgroups mg
                LEFT JOIN evesde_invtypes t ON mg.marketGroupID = t.marketGroupID AND t.published = 1
                WHERE mg.parentGroupID IS NULL
                GROUP BY mg.marketGroupID, mg.marketGroupName
                ORDER BY mg.marketGroupName
            """)
            market_groups = [{'id': row[0], 'name': row[1], 'count': row[2], 'child_count': row[3]} for row in cursor.fetchall()]

            # All meta groups with counts
            cursor.execute("""
                SELECT mg.metaGroupID, mg.metaGroupName, COUNT(DISTINCT mt.typeID) as item_count
                FROM evesde_invmetagroups mg
                LEFT JOIN evesde_invmetatypes mt ON mg.metaGroupID = mt.metaGroupID
                GROUP BY mg.metaGroupID, mg.metaGroupName
                ORDER BY mg.metaGroupID
            """)
            meta_groups = [{'id': row[0], 'name': row[1], 'count': row[2]} for row in cursor.fetchall()]

            # All factions with corporation counts
            cursor.execute("""
                SELECT f.factionID, f.factionName,
                       (SELECT COUNT(*) FROM evesde_crpnpccorporations WHERE factionID = f.factionID) as corp_count,
                       (SELECT COUNT(*) FROM evesde_chrfactions WHERE factionID = f.factionID) as system_count
                FROM evesde_chrfactions f
                ORDER BY f.factionName
            """)
            factions = [{'id': row[0], 'name': row[1], 'corp_count': row[2], 'system_count': row[3]} for row in cursor.fetchall()]

            # Ship classes (groups from Ship category)
            cursor.execute("""
                SELECT g.groupID, g.groupName, COUNT(DISTINCT t.typeID) as item_count
                FROM evesde_invgroups g
                JOIN evesde_invcategories c ON g.categoryID = c.categoryID
                LEFT JOIN evesde_invtypes t ON g.groupID = t.groupID AND t.published = 1
                WHERE c.categoryID = 6 AND g.published = 1
                GROUP BY g.groupID, g.groupName
                HAVING item_count > 0
                ORDER BY g.groupName
            """)
            ship_classes = [{'id': row[0], 'name': row[1], 'count': row[2]} for row in cursor.fetchall()]

            # Skill groups
            cursor.execute("""
                SELECT g.groupID, g.groupName, COUNT(DISTINCT t.typeID) as item_count
                FROM evesde_invgroups g
                LEFT JOIN evesde_invtypes t ON g.groupID = t.groupID AND t.published = 1
                WHERE g.categoryID = 16 AND g.published = 1
                GROUP BY g.groupID, g.groupName
                HAVING item_count > 0
                ORDER BY g.groupName
            """)
            skill_groups = [{'id': row[0], 'name': row[1], 'count': row[2]} for row in cursor.fetchall()]

            # Sample regions for sitemap (first 20 alphabetically)
            cursor.execute("""
                SELECT r.regionID, r.regionName, r.x, r.y, r.z, f.factionName
                FROM evesde_mapregions r
                LEFT JOIN evesde_chrfactions f ON r.factionID = f.factionID
                ORDER BY r.regionName
                LIMIT 20
            """)
            sample_regions = [{
                'region_id': row[0],
                'region_name': row[1],
                'x': row[2],
                'y': row[3],
                'z': row[4],
                'faction_name': row[5]
            } for row in cursor.fetchall()]

    finally:
        settings.DEBUG = original_debug

    return render(request, 'core/sde/sitemap.html', {
        'stats': stats,
        'categories': categories,
        'top_groups': top_groups,
        'market_groups': market_groups,
        'meta_groups': meta_groups,
        'factions': factions,
        'ship_classes': ship_classes,
        'skill_groups': skill_groups,
        'sample_regions': sample_regions,
        'total_categories': len(categories),
        'total_top_groups': len(top_groups),
        'total_market_groups': len(market_groups),
        'total_meta_groups': len(meta_groups),
        'total_factions': len(factions),
        'total_ship_classes': len(ship_classes),
        'total_skill_groups': len(skill_groups),
    })


def sde_ship_fittings(request: HttpRequest, ship_id: int) -> HttpResponse:
    """
    Browser for modules that can fit on a ship.

    Shows:
    - Ship fitting limits (slots, PG, CPU, calibration)
    - Modules grouped by slot type (hi/med/low/rig)
    - Fitting requirements (PG, CPU, calibration)
    - Filter by meta group
    - Module stats relevant to each slot type
    """
    # Get the ship
    try:
        ship = InvTypes.objects.select_related(
            'group', 'group__category'
        ).get(type_id=ship_id, published=True)
    except InvTypes.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Ship {ship_id} not found',
        }, status=404)

    # Verify this is a ship
    if ship.group.category_id != 6:
        return render(request, 'core/error.html', {
            'message': f'Item {ship_id} is not a ship',
        }, status=400)

    # Get ship fitting limits
    fitting = get_ship_fitting(ship_id)

    # Get filters from request
    slot_type = request.GET.get('slot', 'all')  # all, hi, med, low, rig
    meta_group_id = request.GET.get('meta', '')
    max_pg = request.GET.get('max_pg', '')
    max_cpu = request.GET.get('max_cpu', '')

    # Define slot attribute mappings
    # Attribute IDs: 12=low, 13=med, 14=hi, 970=rig
    SLOT_ATTRS = {
        'low': 12,
        'med': 13,
        'hi': 14,
        'rig': 970,
    }

    SLOT_NAMES = {
        'low': 'Low Slot',
        'med': 'Medium Slot',
        'hi': 'High Slot',
        'rig': 'Rig Slot',
    }

    # Module categories (7=Module, 8=Charge, 32=Subsystem)
    MODULE_CATEGORIES = [7, 8, 32]

    # Get all modules with their fitting requirements
    modules_data = []
    from django.conf import settings
    original_debug = settings.DEBUG
    settings.DEBUG = False

    try:
        with connection.cursor() as cursor:
            # Build query for modules with fitting requirements
            sql_query = """
                SELECT DISTINCT
                    t.typeID, t.typeName, t.description, t.basePrice, t.volume,
                    g.groupID, g.groupName,
                    c.categoryID, c.categoryName,
                    mt.metaGroupID,
                    COALESCE(ta_cpu.valueFloat, ta_cpu.valueInt) as cpu_req,
                    COALESCE(ta_pg.valueFloat, ta_pg.valueInt) as pg_req,
                    COALESCE(ta_cap.valueFloat, ta_cap.valueInt) as cap_req,
                    COALESCE(ta_cal.valueFloat, ta_cal.valueInt) as cal_req,
                    ta_slot.valueInt as slot_attr_id
                FROM evesde_invtypes t
                JOIN evesde_invgroups g ON t.groupID = g.groupID
                JOIN evesde_invcategories c ON g.categoryID = c.categoryID
                LEFT JOIN evesde_invmetatypes mt ON t.typeID = mt.typeID
                LEFT JOIN evesde_dgmtypeattributes ta_cpu ON t.typeID = ta_cpu.typeID AND ta_cpu.attributeID = 50
                LEFT JOIN evesde_dgmtypeattributes ta_pg ON t.typeID = ta_pg.typeID AND ta_pg.attributeID = 11
                LEFT JOIN evesde_dgmtypeattributes ta_cap ON t.typeID = ta_cap.typeID AND ta_cap.attributeID = 856
                LEFT JOIN evesde_dgmtypeattributes ta_cal ON t.typeID = ta_cal.typeID AND ta_cal.attributeID = 1132
                LEFT JOIN evesde_dgmtypeattributes ta_slot ON t.typeID = ta_slot.typeID AND ta_slot.attributeID IN (12, 13, 14, 970)
                WHERE c.categoryID IN (7, 8, 32)
                    AND t.published = 1
            """
            params = []

            # Filter by slot type
            if slot_type in SLOT_ATTRS:
                sql_query += " AND ta_slot.attributeID = ?"
                params.append(SLOT_ATTRS[slot_type])

            # Filter by meta group
            if meta_group_id:
                try:
                    meta_id = int(meta_group_id)
                    sql_query += " AND mt.metaGroupID = ?"
                    params.append(meta_id)
                except ValueError:
                    pass

            # Filter by PG (must be <= ship's PG if specified)
            if max_pg and fitting.get('powerOutput'):
                try:
                    pg_limit = float(max_pg)
                    sql_query += " AND (ta_pg.valueFloat <= ? OR ta_pg.valueInt <= ? OR ta_pg.valueFloat IS NULL)"
                    params.extend([pg_limit, pg_limit])
                except ValueError:
                    pass

            # Filter by CPU (must be <= ship's CPU if specified)
            if max_cpu and fitting.get('cpu'):
                try:
                    cpu_limit = float(max_cpu)
                    sql_query += " AND (ta_cpu.valueFloat <= ? OR ta_cpu.valueInt <= ? OR ta_cpu.valueFloat IS NULL)"
                    params.extend([cpu_limit, cpu_limit])
                except ValueError:
                    pass

            sql_query += " ORDER BY g.groupName, t.typeName LIMIT 500"

            cursor.execute(sql_query, params)

            for row in cursor.fetchall():
                (type_id, name, description, base_price, volume,
                 group_id, group_name, category_id, category_name,
                 meta_group_id, cpu_req, pg_req, cap_req, cal_req, slot_attr_id) = row

                # Determine slot type from attribute
                module_slot = None
                if slot_attr_id == 12:
                    module_slot = 'low'
                elif slot_attr_id == 13:
                    module_slot = 'med'
                elif slot_attr_id == 14:
                    module_slot = 'hi'
                elif slot_attr_id == 970:
                    module_slot = 'rig'

                modules_data.append({
                    'type_id': type_id,
                    'name': name,
                    'description': description,
                    'group_name': group_name,
                    'category_name': category_name,
                    'meta_group_id': meta_group_id,
                    'cpu': cpu_req,
                    'pg': pg_req,
                    'cap': cap_req,
                    'calibration': cal_req,
                    'slot': module_slot,
                    'fits_pg': pg_req is None or pg_req <= fitting.get('powerOutput', float('inf')) if fitting.get('powerOutput') else True,
                    'fits_cpu': cpu_req is None or cpu_req <= fitting.get('cpu', float('inf')) if fitting.get('cpu') else True,
                    'fits_cal': cal_req is None or cal_req <= fitting.get('upgradeCapacity', float('inf')) if fitting.get('upgradeCapacity') else True,
                })
    finally:
        settings.DEBUG = original_debug

    # Group modules by slot type and group
    modules_by_slot = {}
    for module in modules_data:
        slot = module['slot'] or 'other'
        if slot not in modules_by_slot:
            modules_by_slot[slot] = {}
        group = module['group_name']
        if group not in modules_by_slot[slot]:
            modules_by_slot[slot][group] = []
        modules_by_slot[slot][group].append(module)

    # Get all meta groups for filter
    meta_groups = InvMetaGroups.objects.all().order_by('meta_group_id')

    # Calculate fitting stats
    total_modules = len(modules_data)
    fitting_stats = {
        'total': total_modules,
        'fits_all': sum(1 for m in modules_data if m['fits_pg'] and m['fits_cpu'] and m['fits_cal']),
        'fits_pg': sum(1 for m in modules_data if m['fits_pg']),
        'fits_cpu': sum(1 for m in modules_data if m['fits_cpu']),
        'fits_cal': sum(1 for m in modules_data if m['fits_cal']),
    }

    return render(request, 'core/sde/ship_fittings.html', {
        'ship': ship,
        'fitting': fitting,
        'modules_by_slot': modules_by_slot,
        'meta_groups': meta_groups,
        'slot_type': slot_type,
        'meta_group_id': meta_group_id,
        'max_pg': max_pg,
        'max_cpu': max_cpu,
        'slot_names': SLOT_NAMES,
        'fitting_stats': fitting_stats,
        'total_modules': total_modules,
    })
