"""
SDE Browser Views

Read-only views for exploring EVE's Static Data Export.
"""

from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch

from core.sde.models import (
    InvTypes, InvGroups, InvCategories, InvMarketGroups, InvMetaGroups,
    DgmAttributeTypes, DgmTypeAttributes,
    MapRegions, MapSolarSystems, MapConstellations,
    ChrFactions, ChrRaces, CrpNPCCorporations,
    StaStations,
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

    # Get top categories by item count
    top_categories = InvCategories.objects.annotate(
        item_count=Count('invgroups__invtypes')
    ).order_by('-item_count')[:10]

    return render(request, 'core/sde/index.html', {
        'stats': stats,
        'top_categories': top_categories,
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
            'group', 'group__category', 'market_group'
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

    return render(request, 'core/sde/item_detail.html', {
        'item': item,
        'attributes': formatted_attributes,
        'related': related,
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
