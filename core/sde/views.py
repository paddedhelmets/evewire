"""
SDE Browser Views

Read-only views for exploring EVE's Static Data Export.
"""

from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch
from django.db import connection

from core.sde.models import (
    InvTypes, InvGroups, InvCategories, InvMarketGroups, InvMetaGroups, InvMetaTypes,
    DgmAttributeTypes, DgmTypeAttributes,
    MapRegions, MapSolarSystems, MapConstellations,
    ChrFactions, ChrRaces, CrpNPCCorporations,
    StaStations,
    CertCerts, CertSkills, CertMasteries,
    IndustryBlueprints,
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
        item_count=Count('invgroups__invtypes')
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
        item_count=Count('invtypes', filter=Q(invtypes__published=True))
    ).filter(item_count__gt=0).order_by('group_name')

    # Quick link counts
    skills_count = InvTypes.objects.filter(
        group__category_id=16,  # Skills
        published=True
    ).count()

    return render(request, 'core/sde/index.html', {
        'stats': stats,
        'all_categories': all_categories,
        'top_market_groups': top_market_groups,
        'meta_groups': meta_groups,
        'ship_groups': ship_groups,
        'skills_count': skills_count,
    })


def sde_search(request: HttpRequest) -> HttpResponse:
    """Search SDE items."""
    query = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)

    results = []
    total_count = 0

    if query and len(query) >= 2:
        # Search across multiple fields
        results = InvTypes.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).select_related('group', 'group__category').order_by('name')

        total_count = results.count()

        # Paginate
        paginator = Paginator(results, 50)
        results = paginator.get_page(page)

    return render(request, 'core/sde/search.html', {
        'query': query,
        'results': results,
        'total_count': total_count,
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

    # Get attributes for this item
    attributes = DgmTypeAttributes.objects.filter(
        type_id=type_id
    ).select_related('attribute_id')

    # Format attributes with their display names
    formatted_attributes = []
    for attr in attributes:
        value = attr.value_float if attr.value_float is not None else attr.value_int
        try:
            attr_info = attr.attribute_id
            formatted_attributes.append({
                'name': attr_info.display_name or attr_info.attribute_name,
                'value': value,
                'unit': '',  # TODO: Add unit mapping if desired
            })
        except DgmAttributeTypes.DoesNotExist:
            formatted_attributes.append({
                'name': f'Attribute {attr.attribute_id}',
                'value': value,
                'unit': '',
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
    if item.meta_type and item.meta_type.parent_type:
        parent_meta = {
            'type': item.meta_type.parent_type,
            'meta_group': item.meta_type.meta_group,
        }

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
        item_count=Count('invtypes')
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
    ).order_by('station_name')[:20]

    return render(request, 'core/sde/system_detail.html', {
        'system': system,
        'stations': stations,
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
                WHERE t.typeID = ?
            """, [current_id])
            skill_row = cursor.fetchone()
            
            if not skill_row:
                break
            
            cursor.execute("""
                SELECT valueInt FROM evesde_dgmattypeattributes
                WHERE typeID = ? AND attributeID = 182
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
        cursor.execute("""
            SELECT ta.attributeID, at.attributeName, ta.valueInt, ta.valueFloat
            FROM evesde_dgmattypeattributes ta
            JOIN evesde_dgmattributetypes at ON ta.attributeID = at.attributeID
            WHERE ta.typeID = ? AND ta.attributeID IN (%s)
            ORDER BY ta.attributeID
        """ % (ship_id, ','.join(map(str, fitting_attr_ids))), [ship_id])
        
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
    """Compare all variants of an item (meta group comparison)."""
    try:
        base = InvTypes.objects.get(type_id=type_id)
    except InvTypes.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': f'Item {type_id} not found',
        }, status=404)
    
    # Get all variants that reference this as parent
    variants = InvMetaTypes.objects.filter(
        parent_type_id=type_id
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
        type_id=type_id
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

    # Calculate material totals for the quantity
    for material in materials:
        material['total_quantity'] = material['quantity'] * quantity
        if material['base_price']:
            material['total_cost'] = material['base_price'] * material['total_quantity']
            material['single_run_cost'] = material['base_price'] * material['quantity']
        else:
            material['total_cost'] = 0
            material['single_run_cost'] = 0

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
    })
