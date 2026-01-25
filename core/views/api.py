"""
API views for evewire.

Provides JSON endpoints for AJAX interactions.
"""

import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.core.paginator import Paginator

logger = logging.getLogger('evewire')


@login_required
@require_http_methods(['GET'])
def api_asset_children(request, asset_id: int) -> JsonResponse:
    """
    API endpoint to fetch children of an asset.

    Returns JSON with immediate children only (lazy-loading).

    Query parameters:
    - character_id: Filter by specific character (optional)
    - pilot_filter: Comma-separated character IDs for account-wide view (optional)
    - page: Page number for pagination (default: 1)
    - per_page: Items per page (default: 50, max: 200)

    Returns:
    {
        "success": true,
        "children": [
            {
                "item_id": 123456789,
                "type_id": 34,
                "type_name": "Tritanium",
                "quantity": 1000000,
                "location_flag": "Hangar",
                "location_name": "Jita IV - Moon 4 - Caldari Navy Assembly Plant",
                "is_singleton": false,
                "is_blueprint_copy": false,
                "has_children": true,
                "child_count": 5,
                "character_id": 90000001,
                "character_name": "Kazanir"
            },
            ...
        ],
        "total": 42,
        "page": 1,
        "per_page": 50,
        "has_next": true
    }
    """
    from core.character.models import CharacterAsset
    from core.models import Character

    # Get pagination parameters
    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 50)), 200)  # Max 200 per page

    # Build cache key
    cache_key = f'assets:children:{asset_id}'
    pilot_filter = request.GET.get('pilot_filter', '')
    if pilot_filter:
        # Sort pilot IDs for consistent cache key
        pilot_ids = ','.join(sorted(pilot_filter.split(',')))
        cache_key += f':pilots:{pilot_ids}'

    # Try cache first
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.debug(f'Cache hit for {cache_key}')
        return JsonResponse(cached_data)

    # Get the parent asset
    try:
        parent_asset = CharacterAsset.objects.get(item_id=asset_id)
    except CharacterAsset.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Asset not found'
        }, status=404)

    # Verify ownership
    if parent_asset.character.user != request.user:
        return JsonResponse({
            'success': False,
            'error': 'Access denied'
        }, status=403)

    # Build query for children
    children_query = CharacterAsset.objects.filter(parent=parent_asset)

    # Apply pilot filter if provided
    if pilot_filter:
        pilot_ids = [int(pid) for pid in pilot_filter.split(',') if pid.isdigit()]
        if pilot_ids:
            children_query = children_query.filter(character_id__in=pilot_ids)
    elif request.GET.get('character_id'):
        # Single character filter
        character_id = int(request.GET.get('character_id'))
        children_query = children_query.filter(character_id=character_id)

    # Annotate with child counts
    children_query = children_query.annotate(
        child_count=Count('children')
    )

    # Select related for efficiency
    children_query = children_query.select_related('character')

    # Get total count for pagination
    total = children_query.count()

    # Paginate
    paginator = Paginator(children_query, per_page)
    page_obj = paginator.get_page(page)

    # Get the actual children from this page
    children = list(page_obj)

    # Bulk-fetch ItemTypes to avoid N+1 queries
    type_ids = set(child.type_id for child in children)
    item_types = {}
    if type_ids:
        from core.eve.models import ItemType
        item_types = {
            item.id: item
            for item in ItemType.objects.filter(id__in=type_ids)
        }

    # Bulk-fetch location data (Station and SolarSystem)
    location_ids = set(child.location_id for child in children if child.location_id)
    station_names = {}
    system_names = {}

    if location_ids:
        # Fetch stations
        try:
            from core.eve.models import Station
            station_names = {
                s.id: s.name
                for s in Station.objects.filter(id__in=location_ids)
            }
        except Exception:
            pass

        # Fetch solar systems
        try:
            from core.eve.models import SolarSystem
            system_names = {
                s.id: s.name
                for s in SolarSystem.objects.filter(id__in=location_ids)
            }
        except Exception:
            pass

    # Build response data
    children_data = []
    for child in children:
        # Get type name (using pre-fetched data)
        type_name = item_types.get(child.type_id)
        if type_name:
            type_name = type_name.name
        else:
            type_name = f"Type {child.type_id}"

        # Get location name (using pre-fetched data)
        location_name = None
        if child.location_id in station_names:
            location_name = station_names[child.location_id]
        elif child.location_id in system_names:
            location_name = system_names[child.location_id]
        elif child.location_type == 'structure':
            location_name = f"Structure {child.location_id}"
        else:
            location_name = f"Location {child.location_id} ({child.location_type})"

        children_data.append({
            'item_id': child.item_id,
            'type_id': child.type_id,
            'type_name': type_name,
            'quantity': child.quantity,
            'location_flag': child.location_flag,
            'location_name': location_name,
            'is_singleton': child.is_singleton,
            'is_blueprint_copy': child.is_blueprint_copy,
            'has_children': child.child_count > 0,
            'child_count': child.child_count,
            'character_id': child.character_id,
            'character_name': child.character.character_name,
            'level': child.level,  # MPTT level for indentation
        })

    response_data = {
        'success': True,
        'children': children_data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'num_pages': paginator.num_pages,
    }

    # Cache for 2-5 minutes
    cache.set(cache_key, response_data, timeout=180)  # 3 minutes

    return JsonResponse(response_data)


@login_required
@require_http_methods(['GET'])
def api_asset_tree(request, character_id: int = None) -> JsonResponse:
    """
    API endpoint to fetch root-level assets for a character or account-wide.

    Returns only top-level assets (parent=None) with child counts.
    Use this to build the initial tree view, then call api_asset_children
    to load deeper levels.

    Query parameters:
    - location_id: Filter by location (optional)
    - pilot_filter: Comma-separated character IDs (optional, for account-wide)

    Returns:
    {
        "success": true,
        "assets": [...],
        "total": 42,
        "location_groups": [
            {
                "location_id": 60003760,
                "location_type": "station",
                "assets": [...]
            }
        ]
    }
    """
    from core.character.models import CharacterAsset
    from core.models import Character
    from collections import defaultdict

    # Get character(s)
    pilot_filter = request.GET.get('pilot_filter', '')

    if pilot_filter:
        # Account-wide view with pilot filter
        pilot_ids = [int(pid) for pid in pilot_filter.split(',') if pid.isdigit()]
        characters = Character.objects.filter(
            id__in=pilot_ids,
            user=request.user
        )
        if not characters:
            return JsonResponse({'success': False, 'error': 'No characters found'}, status=404)
    elif character_id:
        # Single character view
        try:
            character = Character.objects.get(id=character_id, user=request.user)
            characters = [character]
        except Character.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    else:
        # Account-wide view, all characters
        characters = Character.objects.filter(user=request.user)

    # Build cache key
    cache_key = f'assets:tree:{request.user.id}'
    if character_id:
        cache_key += f':char:{character_id}'
    if pilot_filter:
        pilot_ids = ','.join(sorted(pilot_filter.split(',')))
        cache_key += f':pilots:{pilot_ids}'

    location_filter = request.GET.get('location', '')
    if location_filter:
        cache_key += f':loc:{location_filter}'

    # Try cache
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.debug(f'Cache hit for {cache_key}')
        return JsonResponse(cached_data)

    # Query root-level assets only
    assets_query = CharacterAsset.objects.filter(
        character__in=characters,
        parent=None  # Only root-level
    )

    # Apply location filter
    if location_filter:
        try:
            location_id = int(location_filter)
            assets_query = assets_query.filter(location_id=location_id)
        except (ValueError, TypeError):
            pass

    # Annotate with child counts
    assets_query = assets_query.annotate(
        child_count=Count('children')
    ).select_related('character')

    # Fetch assets
    assets = list(assets_query)

    # Group by location
    location_groups = defaultdict(list)
    for asset in assets:
        key = (asset.location_id, asset.location_type)
        location_groups[key].append(asset)

    # Build response
    response_data = {
        'success': True,
        'assets': [
            {
                'item_id': asset.item_id,
                'type_id': asset.type_id,
                'type_name': asset.type_name,
                'quantity': asset.quantity,
                'location_flag': asset.location_flag,
                'location_name': asset.location_name,
                'is_singleton': asset.is_singleton,
                'is_blueprint_copy': asset.is_blueprint_copy,
                'has_children': asset.child_count > 0,
                'child_count': asset.child_count,
                'character_id': asset.character_id,
                'character_name': asset.character.character_name,
                'level': asset.level,
                'location_id': asset.location_id,
                'location_type': asset.location_type,
            }
            for asset in assets
        ],
        'total': len(assets),
        'location_groups': [
            {
                'location_id': loc_id,
                'location_type': loc_type,
                'asset_count': len(loc_assets),
            }
            for (loc_id, loc_type), loc_assets in sorted(
                location_groups.items(),
                key=lambda x: x[0][1] + str(x[0][0])
            )
        ],
    }

    # Cache for 5-15 minutes (use 10 as default)
    cache.set(cache_key, response_data, timeout=600)

    return JsonResponse(response_data)


@login_required
@require_http_methods(['POST'])
def api_assets_invalidate_cache(request) -> JsonResponse:
    """
    Invalidate asset cache for the current user.

    Call this after asset sync to refresh cached data.

    Body:
    {
        "character_id": 123  # Optional, specific character
    }
    """
    from django.core.cache import cache

    character_id = request.POST.get('character_id')

    # Clear all asset-related caches for this user
    # In production, you might want to use cache.delete_pattern() if using Redis
    # For now, we'll just clear specific keys we know about

    keys_to_delete = []

    # Root tree cache
    if character_id:
        keys_to_delete.append(f'assets:tree:{request.user.id}:char:{character_id}')
    else:
        # Clear all character-specific caches for this user
        # Note: This is inefficient for Memcache, better with Redis
        from core.models import Character
        characters = Character.objects.filter(user=request.user)
        for char in characters:
            keys_to_delete.append(f'assets:tree:{request.user.id}:char:{char.id}')

    # Delete the keys
    for key in keys_to_delete:
        cache.delete(key)

    logger.info(f'Invalidated {len(keys_to_delete)} cache entries for user {request.user.id}')

    return JsonResponse({
        'success': True,
        'invalidated': len(keys_to_delete),
    })
