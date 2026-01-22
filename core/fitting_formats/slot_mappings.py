"""
EVE Slot Type Mappings

Maps EVE item groups to slot types for fitting format import.

This mapping is derived from EVE SDE data - modules are assigned to slot types
based on their group membership, not individual attributes.

For complete mapping, the groups can be fetched from ESI:
- /universe/categories/7/ - lists all module groups
- /universe/groups/{group_id}/ - gets group details

Known slot-type attributes on ships:
- 12: lowSlots
- 13: medSlots
- 14: hiSlots
- 1137: rigSlots
- 1314-1318: subsystem slots (T3 cruisers)
"""

# Category IDs
CATEGORY_MODULES = 7
CATEGORY_RIGS = 18
CATEGORY_SUBSYSTEMS = 32
CATEGORY_DRONES = 18
CATEGORY_CHARGES = 8

# Key module groups mapped to slot types (partial - should be expanded from SDE)
GROUP_TO_SLOT = {
    # High slots - Weapons
    53: 'high',   # Energy Weapon (lasers)
    55: 'high',   # Hybrid Weapon (rails/blasters)
    56: 'high',   # Projectile Weapon (projectiles)
    58: 'high',   # Missile Launcher

    # High slots - Engineering
    324: 'high',  # Cloaking Device
    2594: 'high', # Micro Warp Drive
    340: 'high',  # Afterburner

    # High slots - Support
    485: 'high',  # Tractor Beam
    894: 'high',  # Remote Sensor Booster

    # Medium slots - Shield
    47: 'med',    # Shield Extender
    75: 'med',    # Shield Hardener
    211: 'med',   # Projected ECCM

    # Medium slots - Capacitor
    50: 'med',    # Capacitor Recharger
    49: 'med',    # Capacitor Battery

    # Medium slots - Targeting
    52: 'med',    # Tracking Computer
    57: 'med',    # Sensor Booster
    224: 'med',   # Warp Core Stabilizer

    # Low slots - Armor
    373: 'low',   # Armor Repairer
    893: 'low',   # Hull Mods (damage control)

    # Low slots - Hull
    263: 'low',   # Armor Reinforcer (1600mm plates, etc)
    1248: 'low',  # Hull Upgrades (damage control, expanders)

    # Low slots - Engineering
    254: 'low',   # Power Diagnostic System
    255: 'low',   # Reactor Control
    256: 'low',   # Auxiliary Power Core
}


def get_slot_type_for_group(group_id: int) -> str | None:
    """
    Get the slot type for an item group.

    Args:
        group_id: EVE item group ID

    Returns:
        Slot type ('low', 'med', 'high', 'rig', 'subsystem') or None
    """
    return GROUP_TO_SLOT.get(group_id)


def get_slot_type_for_type(type_id: int) -> str | None:
    """
    Get the slot type for an item type by looking up its group.

    Uses proper relationship query: item_type.group.category_id

    Args:
        type_id: EVE item type ID

    Returns:
        Slot type ('low', 'med', 'high', 'rig', 'subsystem') or None
    """
    from core.eve.models import ItemType

    try:
        item_type = ItemType.objects.get(id=type_id)
        if item_type.group_id:
            # Try group mapping first
            slot = get_slot_type_for_group(item_type.group_id)
            if slot:
                return slot

            # Fall back to category-based heuristics
            if hasattr(item_type, 'category_id'):
                cat_id = item_type.category_id
            elif hasattr(item_type.group, 'category_id'):
                cat_id = item_type.group.category_id
            else:
                return None

            if cat_id == CATEGORY_RIGS:
                return 'rig'
            elif cat_id == CATEGORY_SUBSYSTEMS:
                return 'subsystem'
    except ItemType.DoesNotExist:
        pass

    return None
