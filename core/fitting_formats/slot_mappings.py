"""
EVE Slot Type Mappings

Maps EVE item groups to slot types for fitting format import.

This mapping is derived from EVE SDE data - modules are assigned to slot types
based on their group membership.

Generated from SDE: core_itemgroup table (categoryID = 7 = Modules)

For complete/recent mappings, regenerate with SQL queries against core_itemgroup.
"""

# Category IDs
CATEGORY_MODULES = 7
CATEGORY_RIGS = 18  # Note: Rigs as items, not modules
CATEGORY_SUBSYSTEMS = 32
CATEGORY_DRONES = 18
CATEGORY_CHARGES = 8

# Generated GROUP_TO_SLOT mapping from SDE data
GROUP_TO_SLOT = {
    # HIGH SLOTS
    49: 'high',   # Survey Scanner
    53: 'high',   # Energy Weapon
    55: 'high',   # Hybrid Weapon
    56: 'high',   # Missile Launcher
    74: 'high',   # Hybrid Weapon
    77: 'high',   # Shield Hardener
    308: 'high',   # Countermeasure Launcher
    324: 'high',   # Assault Frigate
    340: 'high',   # Secure Cargo Container
    472: 'high',   # System Scanner
    475: 'high',   # Microwarpdrive
    481: 'high',   # Scan Probe Launcher
    485: 'high',   # Dreadnought
    650: 'high',   # Tractor Beam
    842: 'high',   # Burst Projectors
    878: 'high',   # Cloak Enhancements
    894: 'high',   # Heavy Interdiction Cruiser
    1122: 'high',   # Salvager
    1226: 'high',   # Survey Probe Launcher
    4060: 'high',   # Vorton Projector
    4067: 'high',   # Vorton Projector Upgrade
    4807: 'high',   # Breacher Pod Launchers

    # MEDIUM SLOTS
    38: 'med',    # Shield Extender
    40: 'med',    # Shield Booster
    43: 'med',    # Capacitor Recharger
    47: 'med',    # Cargo Scanner
    52: 'med',    # Warp Scrambler
    57: 'med',    # Gyrostabilizer
    59: 'med',    # Stasis Web
    65: 'med',    # Target Painter
    76: 'med',    # Capacitor Booster
    77: 'med',    # Shield Hardener
    82: 'med',    # Passive Targeting System
    201: 'med',    # ECM
    209: 'med',    # Remote Tracking Computer
    210: 'med',    # Signal Amplifier
    211: 'med',    # Tracking Enhancer
    212: 'med',    # Sensor Booster
    213: 'med',    # Tracking Computer
    223: 'med',    # Sensor Booster Blueprint
    281: 'med',    # Frozen
    290: 'med',    # Remote Sensor Booster
    295: 'med',    # Shield Resistance Amplifier
    321: 'med',    # Shield Disruptor
    338: 'med',    # Shield Boost Amplifier
    379: 'med',    # Target Painter
    646: 'med',    # Drone Tracking Modules
    899: 'med',    # Warp Disrupt Field Generator
    1292: 'med',    # Drone Tracking Enhancer
    1697: 'med',    # Ancillary Remote Shield Booster
    1700: 'med',    # Flex Shield Hardener
    1706: 'med',    # Capital Sensor Array

    # LOW SLOTS
    60: 'low',    # Damage Control
    61: 'low',    # Capacitor Battery
    62: 'low',    # Armor Repair Unit
    63: 'low',    # Hull Repair Unit
    96: 'low',    # Automated Targeting System
    98: 'low',    # Armor Coating
    209: 'low',    # Remote Tracking Computer
    211: 'low',    # Tracking Enhancer
    213: 'low',    # Tracking Computer
    295: 'low',    # Shield Resistance Amplifier
    325: 'low',    # Remote Armor Repairer
    326: 'low',    # Energized Armor Membrane
    328: 'low',    # Armor Hardener
    329: 'low',    # Armor Plate
    339: 'low',    # Auxiliary Power Core
    357: 'low',    # DroneBayExpander
    367: 'low',    # Ballistic Control System
    766: 'low',    # Power Diagnostic System
    767: 'low',    # Capacitor Power Relay
    769: 'low',    # Reactor Control Unit

    # RIGS (category 7, module groups with "Rig" in name)
    773: 'rig',   # Rig Armor
    774: 'rig',   # Rig Shield
    775: 'rig',   # Rig Energy Weapon
    776: 'rig',   # Rig Hybrid Weapon
    777: 'rig',   # Rig Launcher
    778: 'rig',   # Rig Drones
    779: 'rig',   # Rig Core
    781: 'rig',   # Rig Core
    782: 'rig',   # Rig Navigation
    786: 'rig',   # Rig Electronic Systems
    796: 'rig',   # Rig Electronic Systems (updated)
    896: 'rig',   # Rig Security Transponder
    904: 'rig',   # Rig Mining
    1232: 'rig',   # Rig Resource Processing
    1233: 'rig',   # Rig Scanning
    1234: 'rig',   # Rig Targeting
    1308: 'rig',   # Rig Anchor
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

    Note: ItemType doesn't have a ForeignKey to ItemGroup, so we need
    to manually query ItemGroup to get category_id for fallback logic.

    Args:
        type_id: EVE item type ID

    Returns:
        Slot type ('low', 'med', 'high', 'rig', 'subsystem') or None
    """
    from core.eve.models import ItemType, ItemGroup

    try:
        item_type = ItemType.objects.get(id=type_id)
        if item_type.group_id:
            # Try group mapping first
            slot = get_slot_type_for_group(item_type.group_id)
            if slot:
                return slot

            # Fall back to category-based heuristics
            # Note: ItemType doesn't have FK to ItemGroup, must query manually
            try:
                group = ItemGroup.objects.get(id=item_type.group_id)
                cat_id = group.category_id
            except ItemGroup.DoesNotExist:
                return None

            if cat_id == CATEGORY_RIGS:
                return 'rig'
            elif cat_id == CATEGORY_SUBSYSTEMS:
                return 'subsystem'
    except ItemType.DoesNotExist:
        pass

    return None
