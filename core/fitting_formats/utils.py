"""
Utility functions for fitting format parsing and serialization.

Provides name resolution, slot type mapping, and format detection helpers.
"""

import logging
from typing import Optional, Dict, List
from functools import lru_cache

logger = logging.getLogger(__name__)


# ESI location flag constants (from services.py)
SLOT_FLAGS = {
    'low': list(range(11, 19)),      # LoSlot0-7
    'med': list(range(19, 27)),      # MedSlot0-7
    'high': list(range(27, 35)),     # HiSlot0-7
    'rig': list(range(92, 95)) + [266],  # RigSlot0-3
    'subsystem': list(range(125, 129)),  # SubSystem0-3
}

# Reverse mapping
FLAG_TO_SLOT = {}
for slot_type, flags in SLOT_FLAGS.items():
    for flag in flags:
        FLAG_TO_SLOT[flag] = slot_type


# EFT slot name patterns
EFT_SLOT_PATTERNS = {
    'low': ['low', 'low slot', 'lo'],
    'med': ['med', 'medium', 'mid', 'med slot', 'medium slot'],
    'high': ['high', 'hi', 'high slot', 'hi slot'],
    'rig': ['rig', 'rig slot'],
    'subsystem': ['subsystem', 'sub system', 'subsystem slot'],
    'service': ['service', 'service slot'],
}


@lru_cache(maxsize=10000)
def resolve_item_name(name: str) -> Optional[int]:
    """
    Resolve an item name to its type ID.

    Uses ItemType table with case-insensitive matching.

    Args:
        name: Item name (can be localized)

    Returns:
        Type ID if found, None otherwise
    """
    from core.eve.models import ItemType

    try:
        item = ItemType.objects.filter(name__iexact=name.strip()).first()
        if item:
            return item.id
    except Exception as e:
        logger.warning(f"Error resolving item name '{name}': {e}")

    return None


def get_item_name(type_id: int) -> str:
    """
    Get the name for an item type ID.

    Args:
        type_id: Item type ID

    Returns:
        Item name, or f"Type {type_id}" if not found
    """
    from core.eve.models import ItemType

    try:
        item = ItemType.objects.get(id=type_id)
        return item.name
    except ItemType.DoesNotExist:
        return f"Type {type_id}"


def normalize_slot_type(slot_str: str) -> Optional[str]:
    """
    Normalize a slot string to internal slot type.

    Handles various naming conventions from EFT, DNA, XML formats.

    Args:
        slot_str: Slot string (e.g., "low slot 0", "hi slot 1", "medslot 2")

    Returns:
        Normalized slot type ('low', 'med', 'high', 'rig', 'subsystem', 'service')
        or None if not recognized
    """
    slot_str_lower = slot_str.lower().strip()

    for slot_type, patterns in EFT_SLOT_PATTERNS.items():
        for pattern in patterns:
            if pattern in slot_str_lower:
                return slot_type

    return None


def parse_slot_position(slot_str: str) -> Optional[int]:
    """
    Extract position from a slot string.

    Args:
        slot_str: Slot string (e.g., "low slot 0", "hi slot 1")

    Returns:
        Position as integer, or None if not found
    """
    import re

    # Look for trailing number
    match = re.search(r'(\d+)', slot_str)
    if match:
        return int(match.group(1))

    return None


def detect_ship_type(name: str) -> Optional[int]:
    """
    Attempt to resolve a ship name to type ID.

    More lenient than general item resolution - specifically looks for
    items in the ship category (category 6).

    Args:
        name: Ship name

    Returns:
        Type ID if found, None otherwise
    """
    from core.eve.models import ItemType

    try:
        item = ItemType.objects.filter(
            name__iexact=name.strip(),
            category_id=6  # Ships category
        ).first()
        if item:
            return item.id
    except Exception as e:
        logger.warning(f"Error resolving ship name '{name}': {e}")

    return None


def slot_type_to_eft_name(slot_type: str) -> str:
    """
    Convert internal slot type to EFT format name.

    Args:
        slot_type: Internal slot type ('low', 'med', 'high', 'rig', 'subsystem')

    Returns:
        EFT format slot name (capitalized)
    """
    eft_names = {
        'low': 'Low Slot',
        'med': 'Med Slot',
        'high': 'High Slot',
        'rig': 'Rig Slot',
        'subsystem': 'Subsystem Slot',
        'service': 'Service Slot',
    }
    return eft_names.get(slot_type, slot_type.title())


def eft_name_to_slot_type(eft_name: str) -> Optional[str]:
    """
    Convert EFT format slot name to internal slot type.

    Args:
        eft_name: EFT slot name (e.g., "Low Slot", "Hi Slot", "medslot")

    Returns:
        Internal slot type or None if not recognized
    """
    return normalize_slot_type(eft_name)


def get_slot_count(slot_type: str) -> int:
    """
    Get maximum number of slots for a given slot type.

    Based on ESI flag ranges.

    Args:
        slot_type: Slot type ('low', 'med', 'high', 'rig', 'subsystem')

    Returns:
        Maximum slot count
    """
    return len(SLOT_FLAGS.get(slot_type, []))


def clear_caches() -> None:
    """Clear all LRU caches (useful for testing)."""
    resolve_item_name.cache_clear()
