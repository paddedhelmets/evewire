"""
Core views for evewire.
"""

import logging
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.db import models
from django.utils import timezone
from core.views import get_users_character


logger = logging.getLogger(__name__)
# Asset Views

@login_required
def assets_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """
    View character assets with layered hierarchical tree display.

    Tree structure (evething-style):
    - Level 1: Locations (stations/structures/systems) - loaded initially
    - Level 2: Top-level assets at location - loaded when location expanded
    - Level 3+: Container contents - loaded when container expanded
    """
    from core.models import Character
    from core.character.models import CharacterAsset
    from core.eve.models import ItemType, Station, SolarSystem
    from collections import defaultdict
    from django.db.models import Count, Q

    all_characters = request.user.characters.all()

    # Get location filter (only for true structures: station/structure/system)
    location_filter = request.GET.get('location', '')

    # Get pilot filter
    pilot_filter = request.GET.getlist('pilots')
    pilot_filter_ints = [int(pid) for pid in pilot_filter if pid.isdigit()]

    # Get search query
    search_query = request.GET.get('search', '').strip()

    # Determine character(s) to query
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
            characters = [character]
            is_account_wide = False
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        characters = list(all_characters)
        is_account_wide = True
        character = None

    # Apply pilot filter if specified
    if pilot_filter_ints:
        characters = [c for c in characters if c.id in pilot_filter_ints]

    # Build query for root-level assets (parent=None)
    assets_query = CharacterAsset.objects.filter(
        character__in=characters,
        parent=None
    )

    # Apply location filter if specified (only for true structure types)
    if location_filter:
        try:
            location_id = int(location_filter)
            # Only filter by location if it's a true structure type
            assets_query = assets_query.filter(
                location_id=location_id,
                location_type__in=['station', 'solar_system', 'structure']
            )
        except (ValueError, TypeError):
            pass

    # Group assets by location to get unique locations
    location_groups = defaultdict(lambda: {'count': 0})

    for asset in assets_query:
        # Only count assets at true structure locations
        if asset.location_type in ['station', 'solar_system', 'structure']:
            key = (asset.location_id, asset.location_type)
            location_groups[key]['count'] += 1

    # Fetch location names
    location_ids = set(loc_id for (loc_id, loc_type) in location_groups.keys() if loc_id)
    station_names = {}
    system_names = {}
    structure_names = {}

    if location_ids:
        # Fetch stations from SDE
        try:
            station_names = {
                s.id: s.name
                for s in Station.objects.filter(id__in=location_ids)
            }
        except Exception:
            pass

        # Fetch solar systems from SDE
        try:
            system_names = {
                s.id: s.name
                for s in SolarSystem.objects.filter(id__in=location_ids)
            }
        except Exception:
            pass

    # Fetch structure data from cache or ESI
    structure_ids = set(loc_id for (loc_id, loc_type) in location_groups.keys()
                       if loc_type == 'structure' and loc_id)
    if structure_ids:
        from core.esi_client import ensure_structure_data
        for structure_id in structure_ids:
            structure = ensure_structure_data(structure_id, user=request.user)
            if structure:
                structure_names[structure_id] = structure.name
            else:
                structure_names[structure_id] = f"Structure {structure_id}"

    # Build location list for template
    locations = []
    for (loc_id, loc_type), data in sorted(location_groups.items()):
        if loc_type == 'station':
            location_name = station_names.get(loc_id, f"Station {loc_id}")
        elif loc_type == 'solar_system':
            location_name = system_names.get(loc_id, f"System {loc_id}")
        elif loc_type == 'structure':
            location_name = structure_names.get(loc_id, f"Structure {loc_id}")
        else:
            location_name = f"{loc_type.title()} {loc_id}"

        locations.append({
            'location_id': loc_id,
            'location_type': loc_type,
            'location_name': location_name,
            'asset_count': data['count'],
        })

    # Sort by location name
    locations.sort(key=lambda x: x['location_name'])

    # Build available locations for filter dropdown (only true structures)
    available_locations = []
    for loc in locations:
        available_locations.append({
            'id': loc['location_id'],
            'name': loc['location_name'],
            'type': loc['location_type'],
        })

    return render(request, 'core/assets_list.html', {
        'character': character,
        'locations': locations,
        'total_locations': len(locations),
        'location_filter': location_filter,
        'available_locations': available_locations,
        'is_account_wide': is_account_wide,
        'all_characters': all_characters,
        'pilot_filter': pilot_filter_ints,
        'search_query': search_query,
    })


@login_required
def assets_summary(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View asset summary with per-location aggregates."""
    from core.models import Character
    from core.character.models import CharacterAsset
    from core.eve.models import ItemType
    from django.db.models import Sum, Count, Q
    from collections import defaultdict
    from decimal import Decimal

    # Get character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        character = get_users_character(request.user)
        if not character:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)

    # Get top-level assets only (no parent) to avoid double-counting nested items
    assets_qs = CharacterAsset.objects.filter(
        character=character,
        parent=None
    ).select_related('type')

    # Aggregate by location
    location_data = defaultdict(lambda: {
        'total_items': 0,
        'total_quantity': 0,
        'total_volume': Decimal('0.0'),
        'total_value': Decimal('0.0'),
    })

    for asset in assets_qs:
        key = (asset.location_type, asset.location_id)
        item_type = asset.type

        # Count each asset item (including quantity)
        quantity = asset.quantity
        location_data[key]['total_items'] += 1
        location_data[key]['total_quantity'] += quantity

        # Calculate volume (item volume * quantity)
        if item_type and item_type.volume:
            location_data[key]['total_volume'] += Decimal(str(item_type.volume)) * quantity

        # Calculate value (use sell_price if available, otherwise base_price)
        price = item_type.sell_price if item_type and item_type.sell_price else (item_type.base_price if item_type else None)
        if price:
            location_data[key]['total_value'] += price * quantity

    # Build location list with names
    locations = []
    for (loc_type, loc_id), data in sorted(location_data.items()):
        # Get location name
        if loc_type == 'station':
            from core.eve.models import Station
            try:
                loc_name = Station.objects.get(id=loc_id).name
            except Station.DoesNotExist:
                loc_name = f"Station {loc_id}"
        elif loc_type == 'solar_system':
            from core.eve.models import SolarSystem
            try:
                loc_name = SolarSystem.objects.get(id=loc_id).name
            except SolarSystem.DoesNotExist:
                loc_name = f"System {loc_id}"
        elif loc_type == 'structure':
            loc_name = f"Structure {loc_id}"
        else:
            loc_name = f"{loc_type.title()} {loc_id}"

        locations.append({
            'location_type': loc_type,
            'location_id': loc_id,
            'location_name': loc_name,
            'total_items': data['total_items'],
            'total_volume': data['total_volume'],
            'total_value': data['total_value'],
        })

    # Calculate overall totals
    total_items = sum(loc['total_items'] for loc in locations)
    total_value = sum(loc['total_value'] for loc in locations)
    total_volume = sum(loc['total_volume'] for loc in locations)

    return render(request, 'core/assets_summary.html', {
        'character': character,
        'locations': locations,
        'total_items': total_items,
        'total_value': total_value,
        'total_volume': total_volume,
    })


@login_required
def contract_detail(request: HttpRequest, contract_id: int) -> HttpResponse:
    """View a single contract with its items."""
    from core.models import Character
    from core.character.models import Contract, ContractItem

    try:
        contract = Contract.objects.get(contract_id=contract_id)
    except Contract.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Contract not found',
        }, status=404)

    # Verify ownership
    if contract.character.user != request.user:
        return render(request, 'core/error.html', {
            'message': 'Access denied',
        }, status=403)

    # Get contract items
    items = contract.items.all()

    # Calculate item statistics
    included_items = [item for item in items if item.is_included]
    requested_items = [item for item in items if not item.is_included]

    return render(request, 'core/contract_detail.html', {
        'contract': contract,
        'items': items,
        'included_items': included_items,
        'requested_items': requested_items,
    })


@login_required
def fitted_ships(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View fitted ships extracted from assets."""
    from core.models import Character
    from core.doctrines.services import AssetFitExtractor
    from core.eve.models import ItemType

    # Get character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        character = get_users_character(request.user)
        if not character:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)

    # Extract fitted ships
    extractor = AssetFitExtractor()
    ships = extractor.extract_ships(character)

    # Enrich with item names and location details
    enriched_ships = []
    for ship in ships:
        # Get module names
        high_module_names = []
        for type_id in ship.high_slots:
            try:
                high_module_names.append(ItemType.objects.get(id=type_id).name)
            except ItemType.DoesNotExist:
                high_module_names.append(f"Module {type_id}")

        med_module_names = []
        for type_id in ship.med_slots:
            try:
                med_module_names.append(ItemType.objects.get(id=type_id).name)
            except ItemType.DoesNotExist:
                med_module_names.append(f"Module {type_id}")

        low_module_names = []
        for type_id in ship.low_slots:
            try:
                low_module_names.append(ItemType.objects.get(id=type_id).name)
            except ItemType.DoesNotExist:
                low_module_names.append(f"Module {type_id}")

        rig_module_names = []
        for type_id in ship.rig_slots:
            try:
                rig_module_names.append(ItemType.objects.get(id=type_id).name)
            except ItemType.DoesNotExist:
                rig_module_names.append(f"Module {type_id}")

        # Get location name
        location_name = f"{ship.location_type.title()} {ship.location_id}"
        if ship.location_type == 'station':
            try:
                from core.eve.models import Station
                location_name = Station.objects.get(id=ship.location_id).name
            except Station.DoesNotExist:
                pass
        elif ship.location_type == 'solar_system':
            try:
                from core.eve.models import SolarSystem
                location_name = SolarSystem.objects.get(id=ship.location_id).name
            except SolarSystem.DoesNotExist:
                pass

        enriched_ships.append({
            'asset_id': ship.asset_id,
            'ship_name': ship.ship_name,
            'ship_type_id': ship.ship_type_id,
            'location_name': location_name,
            'location_type': ship.location_type,
            'high_slots': ship.high_slots,
            'high_slot_names': high_module_names,
            'high_slot_count': len(ship.high_slots),
            'med_slots': ship.med_slots,
            'med_slot_names': med_module_names,
            'med_slot_count': len(ship.med_slots),
            'low_slots': ship.low_slots,
            'low_slot_names': low_module_names,
            'low_slot_count': len(ship.low_slots),
            'rig_slots': ship.rig_slots,
            'rig_slot_names': rig_module_names,
            'rig_slot_count': len(ship.rig_slots),
            'subsystem_slots': ship.subsystem_slots,
            'subsystem_slot_count': len(ship.subsystem_slots),
            'cargo_count': len(ship.cargo),
            'drone_bay_count': len(ship.drone_bay),
            'fighter_bay_count': len(ship.fighter_bay),
        })

    return render(request, 'core/fitted_ships.html', {
        'character': character,
        'ships': enriched_ships,
        'total_ships': len(ships),
    })

