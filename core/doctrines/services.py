"""
Fitting services for asset matching and shopping lists.

Provides:
- AssetFitExtractor: Extract fitted ship configurations from assets
- FittingMatcher: Match assets against fitting specifications
- ShoppingListGenerator: Generate buy lists for fitting fulfillment
- LocationCapacity: Calculate available space at locations
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass
from django.db import transaction
from django.utils import timezone

from core.eve.models import ItemType
from core.character.models import CharacterAsset

logger = logging.getLogger('evewire')


# ESI location flag constants
SLOT_FLAGS = {
    'low': list(range(11, 19)),      # LoSlot0-7
    'med': list(range(19, 27)),      # MedSlot0-7
    'high': list(range(27, 35)),     # HiSlot0-7
    'rig': list(range(92, 95)) + [266],  # RigSlot0-3
    'subsystem': list(range(125, 129)),  # SubSystem0-3
}

FLAG_TO_SLOT = {}
for slot_type, flags in SLOT_FLAGS.items():
    for flag in flags:
        FLAG_TO_SLOT[flag] = slot_type

# String flag mapping (ESI v2+ returns string flags like 'HiSlot0')
STRING_FLAG_TO_SLOT = {}
STRING_FLAG_TO_SLOT.update({f'HiSlot{i}': ('high', i) for i in range(8)})
STRING_FLAG_TO_SLOT.update({f'MedSlot{i}': ('med', i) for i in range(8)})
STRING_FLAG_TO_SLOT.update({f'LoSlot{i}': ('low', i) for i in range(8)})
STRING_FLAG_TO_SLOT.update({f'RigSlot{i}': ('rig', i) for i in range(4)})
STRING_FLAG_TO_SLOT.update({f'SubSlot{i}': ('subsystem', i) for i in range(5)})


@dataclass
class FittedShip:
    """A fitted ship extracted from asset tree."""
    asset_id: int
    ship_type_id: int
    ship_name: str
    location_id: Optional[int]
    location_type: str
    # Fitted modules by slot
    high_slots: List[int]
    med_slots: List[int]
    low_slots: List[int]
    rig_slots: List[int]
    subsystem_slots: List[int]
    # Other contents
    cargo: List[Tuple[int, int]]  # (type_id, quantity)
    drone_bay: List[Tuple[int, int]]
    fighter_bay: List[Tuple[int, int]]

    def get_fitted_modules(self) -> Set[int]:
        """Get set of all fitted module type IDs."""
        modules = set()
        modules.update(self.high_slots)
        modules.update(self.med_slots)
        modules.update(self.low_slots)
        modules.update(self.rig_slots)
        modules.update(self.subsystem_slots)
        return modules

    def to_dict(self) -> dict:
        """Convert to dict for comparison."""
        return {
            'ship_type_id': self.ship_type_id,
            'high_slots': self.high_slots,
            'med_slots': self.med_slots,
            'low_slots': self.low_slots,
            'rig_slots': self.rig_slots,
            'subsystem_slots': self.subsystem_slots,
        }


class AssetFitExtractor:
    """
    Extract fitted ship configurations from character assets.

    Traverses the MPTT asset tree to find ships with fitted modules.
    """

    def extract_ships(self, character) -> List[FittedShip]:
        """
        Extract all fitted ships from character assets.

        Args:
            character: Character model instance

        Returns:
            List of FittedShip objects
        """
        ships = []

        # Get all ship-type assets (category 6 = Ships, filter through ItemGroup)
        from core.eve.models import ItemGroup
        ship_group_ids = ItemGroup.objects.filter(category_id=6, published=True).values_list('id', flat=True)
        ship_type_ids = ItemType.objects.filter(group_id__in=ship_group_ids, published=True).values_list('id', flat=True)

        ship_assets = CharacterAsset.objects.filter(
            character=character,
            type_id__in=ship_type_ids
        )

        for ship_asset in ship_assets:
            fitted_ship = self._extract_ship_fit(ship_asset)
            if fitted_ship:
                ships.append(fitted_ship)

        logger.info(f"Extracted {len(ships)} fitted ships for character {character.id}")
        return ships

    def _extract_ship_fit(self, ship_asset: CharacterAsset) -> Optional[FittedShip]:
        """
        Extract fit from a single ship asset.

        Args:
            ship_asset: CharacterAsset for the ship

        Returns:
            FittedShip or None if not a fitted ship
        """
        # Get direct children (fitted modules and contents)
        children = CharacterAsset.objects.filter(parent=ship_asset)

        # Initialize slot arrays
        high_slots = [None] * 8
        med_slots = [None] * 8
        low_slots = [None] * 8
        rig_slots = [None] * 4
        subsystem_slots = [None] * 4
        cargo = []
        drone_bay = []
        fighter_bay = []

        for child in children:
            # Parse location_flag to get slot position
            # ESI returns flags as integers (legacy) or strings (v2+)
            flag = child.location_flag

            # Try integer flag first (legacy ESI)
            slot_type = None
            slot_index = None

            try:
                flag_int = int(flag)
                # Integer flag handling
                if flag_int in FLAG_TO_SLOT:
                    slot_type = FLAG_TO_SLOT[flag_int]

                    if slot_type == 'high' and flag_int - 27 < 8:
                        high_slots[flag_int - 27] = child.type_id
                    elif slot_type == 'med' and flag_int - 19 < 8:
                        med_slots[flag_int - 19] = child.type_id
                    elif slot_type == 'low' and flag_int - 11 < 8:
                        low_slots[flag_int - 11] = child.type_id
                    elif slot_type == 'rig':
                        if flag_int == 92:
                            rig_slots[0] = child.type_id
                        elif flag_int == 93:
                            rig_slots[1] = child.type_id
                        elif flag_int == 94:
                            rig_slots[2] = child.type_id
                        elif flag_int == 266:
                            rig_slots[3] = child.type_id
                    elif slot_type == 'subsystem':
                        subsystem_slots[flag_int - 125] = child.type_id
                elif flag_int == 4:  # Cargo
                    cargo.append((child.type_id, child.quantity))
                elif flag_int == 87:  # DroneBay
                    drone_bay.append((child.type_id, child.quantity))
                elif flag_int == 158:  # FighterBay
                    fighter_bay.append((child.type_id, child.quantity))
            except (ValueError, TypeError):
                # String flag handling (ESI v2+)
                if flag in STRING_FLAG_TO_SLOT:
                    slot_type, slot_index = STRING_FLAG_TO_SLOT[flag]
                    if slot_type == 'high' and slot_index < 8:
                        high_slots[slot_index] = child.type_id
                    elif slot_type == 'med' and slot_index < 8:
                        med_slots[slot_index] = child.type_id
                    elif slot_type == 'low' and slot_index < 8:
                        low_slots[slot_index] = child.type_id
                    elif slot_type == 'rig' and slot_index < 4:
                        rig_slots[slot_index] = child.type_id
                    elif slot_type == 'subsystem' and slot_index < 5:
                        subsystem_slots[slot_index] = child.type_id
                elif flag == 'Cargo':
                    cargo.append((child.type_id, child.quantity))
                elif flag == 'DroneBay':
                    drone_bay.append((child.type_id, child.quantity))
                elif flag == 'FighterBay':
                    fighter_bay.append((child.type_id, child.quantity))

        # Get ship type name
        try:
            ship_name = ItemType.objects.get(id=ship_asset.type_id).name
        except ItemType.DoesNotExist:
            ship_name = f"Ship {ship_asset.type_id}"

        return FittedShip(
            asset_id=ship_asset.item_id,
            ship_type_id=ship_asset.type_id,
            ship_name=ship_name,
            location_id=ship_asset.location_id,
            location_type=ship_asset.location_type,
            high_slots=[m for m in high_slots if m is not None],
            med_slots=[m for m in med_slots if m is not None],
            low_slots=[m for m in low_slots if m is not None],
            rig_slots=[m for m in rig_slots if m is not None],
            subsystem_slots=[m for m in subsystem_slots if m is not None],
            cargo=cargo,
            drone_bay=drone_bay,
            fighter_bay=fighter_bay,
        )


class FittingMatcher:
    """
    Match assets against fitting specifications.

    Compares fitted ships to fitting requirements and calculates match scores.
    """

    def __init__(self, extractor: AssetFitExtractor = None):
        self.extractor = extractor or AssetFitExtractor()

    def match_character_assets(self, character, fitting=None) -> List[Dict]:
        """
        Match all character assets against fittings.

        Args:
            character: Character model instance
            fitting: Optional Fitting to filter by

        Returns:
            List of match dicts with asset, fitting, score, missing modules
        """
        matches = []

        # Extract all fitted ships
        ships = self.extractor.extract_ships(character)

        # Get fittings to match against
        from core.doctrines.models import Fitting
        if fitting:
            fittings = [fitting]
        else:
            fittings = Fitting.objects.active()

        # Match each ship against each fitting
        for ship in ships:
            for doc in fittings:
                if doc.ship_type_id == ship.ship_type_id:
                    match_result = self._match_ship_to_fitting(ship, doc)
                    if match_result:
                        matches.append(match_result)

        # Sort by match score descending
        matches.sort(key=lambda m: m['score'], reverse=True)

        logger.info(f"Found {len(matches)} matches for character {character.id}")
        return matches

    def _match_ship_to_fitting(self, ship: FittedShip, fitting) -> Optional[Dict]:
        """
        Match a single ship against a fitting.

        Returns:
            Dict with asset, fitting, score, missing_modules
        """
        # Get fitting required modules
        required = self._get_required_modules(fitting)

        # Get ship fitted modules
        fitted = ship.get_fitted_modules()

        # Calculate match score
        missing = required - fitted
        extra = fitted - required

        if not required:
            score = 0.0
        elif len(missing) == 0:
            score = 1.0
        else:
            score = (len(required) - len(missing)) / len(required)

        return {
            'asset_id': ship.asset_id,
            'ship_name': ship.ship_name,
            'ship_type_id': ship.ship_type_id,
            'location_id': ship.location_id,
            'location_type': ship.location_type,
            'fitting': fitting,
            'fitting_name': fitting.name,
            'score': score,
            'is_match': len(missing) == 0,
            'missing_modules': list(missing),
            'extra_modules': list(extra),
        }

    def _get_required_modules(self, fitting) -> Set[int]:
        """Get set of required module type IDs for a fitting."""
        modules = set()
        for entry in fitting.entries.all():
            modules.add(entry.module_type_id)
        return modules


class ShoppingListGenerator:
    """
    Generate shopping lists for fitting fulfillment.

    Calculates what items need to be bought at a location to fit N ships
    according to a fitting.
    """

    def __init__(self, matcher: FittingMatcher = None):
        self.matcher = matcher or FittingMatcher()

    def generate_for_location(
        self,
        character,
        location_id: int,
        location_type: str,
        quantity: int,
        fitting,
    ) -> Dict:
        """
        Generate a shopping list for fitting ships at a location.

        Args:
            character: Character to generate list for
            location_id: Station/structure ID
            location_type: 'station' or 'structure'
            quantity: Number of ships to fit
            fitting: Fitting to fulfill

        Returns:
            Dict with items_to_buy, available_assets, total_cost
        """
        # Get all assets at this location
        assets_at_location = self._get_assets_at_location(
            character, location_id, location_type
        )

        # Get fitting requirements
        requirements = self._get_fitting_requirements(fitting)

        # Calculate what's needed
        items_needed = self._calculate_requirements(
            requirements, quantity, assets_at_location
        )

        # Calculate costs
        total_cost = self._calculate_cost(items_needed)

        return {
            'character': character,
            'fitting': fitting,
            'location_id': location_id,
            'location_type': location_type,
            'quantity': quantity,
            'items_to_buy': items_needed,
            'available_assets': assets_at_location,
            'total_cost': total_cost,
        }

    def _get_assets_at_location(
        self, character, location_id: int, location_type: str
    ) -> Dict[int, int]:
        """
        Get all assets at a location by type ID.

        Returns:
            Dict mapping type_id -> quantity available
        """
        assets = CharacterAsset.objects.filter(
            character=character,
            location_id=location_id,
            location_type=location_type,
        )

        counts = defaultdict(int)
        for asset in assets:
            # For singleton items (assembled ships), count as 1
            # For stackable items, use quantity
            if asset.is_singleton:
                counts[asset.type_id] += 1
            else:
                counts[asset.type_id] += asset.quantity

        return dict(counts)

    def _get_fitting_requirements(self, fitting) -> Dict[int, int]:
        """
        Get module requirements for one ship.

        Returns:
            Dict mapping type_id -> quantity needed (usually 1)
        """
        requirements = defaultdict(int)

        # Add ship hull
        requirements[fitting.ship_type_id] += 1

        # Add all modules
        for entry in fitting.entries.all():
            requirements[entry.module_type_id] += 1

        return dict(requirements)

    def _calculate_requirements(
        self,
        single_ship_requirements: Dict[int, int],
        quantity: int,
        available_assets: Dict[int, int],
    ) -> Dict[int, int]:
        """
        Calculate total items needed to fit N ships.

        Returns:
            Dict mapping type_id -> quantity to buy
        """
        # Scale requirements by quantity
        total_needed = {
            type_id: count * quantity
            for type_id, count in single_ship_requirements.items()
        }

        # Subtract what's available
        items_to_buy = {}
        for type_id, needed in total_needed.items():
            available = available_assets.get(type_id, 0)
            if needed > available:
                items_to_buy[type_id] = needed - available

        return items_to_buy

    def _calculate_cost(self, items_to_buy: Dict[int, int]) -> float:
        """Calculate total cost of shopping list using SDE base prices."""
        total = 0.0

        for type_id, quantity in items_to_buy.items():
            try:
                item = ItemType.objects.get(id=type_id)
                price = float(item.base_price or 0)
                total += price * quantity
            except ItemType.DoesNotExist:
                pass

        return total


class LocationCapacity:
    """
    Calculate capacity available at locations and containers.

    EVE capacity rules:
    - Station hangars: INFINITE
    - Citadel/structure hangars: INFINITE (citadels function like stations)
    - Containers: finite (detect from item type capacity attribute)
    - Ship cargo/holds: finite (detect from ship type capacity attributes)

    We only report finite capacity when directly detectable from the item itself.
    """

    def get_container_capacity(self, asset: CharacterAsset) -> Dict:
        """
        Get capacity of a container (ship cargo, station container, etc.).

        Args:
            asset: CharacterAsset for the container

        Returns:
            Dict with available_volume, used_volume, total_volume, can_fit_more
        """
        try:
            item_type = ItemType.objects.get(id=asset.type_id)
        except ItemType.DoesNotExist:
            return {
                'asset_id': asset.item_id,
                'type_id': asset.type_id,
                'available_volume': 0,
                'used_volume': 0,
                'total_volume': 0,
                'can_fit_more': False,
            }

        # Get total capacity from item type
        # For ships, this is the cargo capacity
        # For containers, this is the internal volume
        total_volume = float(item_type.capacity or 0)

        # Calculate used volume from children
        used_volume = 0.0
        for child in asset.children.all():
            try:
                child_type = ItemType.objects.get(id=child.type_id)
                volume = float(child_type.volume or 0)
                if child.is_singleton:
                    used_volume += volume
                else:
                    used_volume += volume * child.quantity
            except ItemType.DoesNotExist:
                pass

        return {
            'asset_id': asset.item_id,
            'type_id': asset.type_id,
            'type_name': item_type.name,
            'available_volume': max(0, total_volume - used_volume),
            'used_volume': used_volume,
            'total_volume': total_volume,
            'can_fit_more': used_volume < total_volume,
        }

    def get_location_capacity(
        self, character, location_id: int, location_type: str
    ) -> Dict:
        """
        Get capacity at a location (for items NOT in containers).

        Args:
            character: Character to check for
            location_id: Station/structure ID
            location_type: 'station', 'structure', or 'solar_system'

        Returns:
            Dict with location info - no volume/capacity data since
            station/structure hangars are infinite to the player
        """
        # Station and citadel hangars are infinite for players
        # We don't report volume/capacity since it's not meaningful
        location_names = {
            'station': 'Station Hangar',
            'structure': 'Citadel Hangar',
            'solar_system': 'Solar System',
        }

        return {
            'location_id': location_id,
            'location_type': location_type,
            'location_name': location_names.get(location_type, f'{location_type.title()} {location_id}'),
            'is_infinite': True,
        }

    def can_fit_ships(
        self,
        character,
        location_id: int,
        location_type: str,
        ship_type_id: int,
        quantity: int,
    ) -> bool:
        """
        Check if location can fit N assembled ships.

        Args:
            character: Character to check for
            location_id: Station/structure ID
            location_type: 'station' or 'structure'
            ship_type_id: Ship type to fit
            quantity: Number of ships

        Returns:
            True if ships can fit (always True for stations/structures)
        """
        # Station and citadel hangars have infinite capacity
        if location_type in ('station', 'structure'):
            return True

        # For solar systems (items in space), check actual capacity
        # This is rare but possible (jettisoned cans, ship cargo, etc.)
        return True  # Default to True for now

    def find_available_space(
        self,
        character,
        location_id: int,
        location_type: str,
        required_volume: float,
    ) -> List[Dict]:
        """
        Find containers with available space at a location.

        Args:
            character: Character to check for
            location_id: Station/structure ID
            location_type: 'station' or 'structure'
            required_volume: Volume needed

        Returns:
            List of locations/containers with space, with infinite locations first
        """
        result = []

        # Location hangar (station or citadel) is always an option
        location_info = self.get_location_capacity(character, location_id, location_type)
        result.append({
            'type': 'location',
            'location_id': location_id,
            'location_type': location_type,
            'name': location_info['location_name'],
            'is_infinite': True,
        })

        # Check containers at this location
        containers = CharacterAsset.objects.filter(
            character=character,
            location_id=location_id,
            location_type=location_type,
            parent__isnull=True,  # Top-level containers only
        ).exclude(
            type_id__in=ItemType.objects.filter(
                category_id=6  # Exclude ships themselves
            ).values_list('id', flat=True)
        )

        for container in containers:
            cap = self.get_container_capacity(container)
            if cap['total_volume'] > 0:  # Only include actual containers
                result.append({
                    'type': 'container',
                    'asset_id': container.item_id,
                    'name': cap['type_name'],
                    'available_volume': cap['available_volume'],
                    'total_volume': cap['total_volume'],
                    'can_fit': cap['available_volume'] >= required_volume,
                })

        return result
