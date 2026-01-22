"""
DNA (Fitting DNA) format parser and serializer.

DNA is a compact format used for sharing fits in EVE chat.
It uses type IDs and is very space-efficient.

Example:
    626:12058;1:25606;1::5973;5:11928;2:

Format: SHIP:HIGHS:MEDS:LOWS:RIGS:SUBSYSTEMS::DRONES:CARGO
- Each section is type_id:count pairs separated by colons
- Three colons (::) separate modules from drones/cargo
- Underscore suffix indicates unfitted module
- Empty sections between colons represent empty slot positions
"""

import re
from typing import List, Tuple
from .base import FittingParser, FittingSerializer, FittingData
from .exceptions import InvalidFormatError
from .utils import get_item_name
from .slot_mappings import get_slot_type_for_type


class DNAParser(FittingParser):
    """
    Parser for DNA format.

    DNA format structure:
    SHIP_ID:HIGHS:MEDS:LOWS:RIGS:SUBSYSTEMS::DRONES:CARGO

    The format is position-dependent:
    - First segment after ship: high slots (in position order)
    - Second segment: medium slots
    - Third segment: low slots
    - Fourth segment: rig slots
    - Fifth segment: subsystem slots
    - After :: drones and cargo

    However, EVE's actual DNA format is more complex and uses
    the slot type from item attributes, not position. We use
    the GROUP_TO_SLOT mapping to determine slot types.
    """

    def parse(self, content: str) -> FittingData:
        """Parse DNA format content into FittingData."""
        # Strip whitespace
        content = content.strip()

        # Split by :: to separate modules from drones/cargo
        parts = content.split('::')

        if len(parts) < 2:
            raise InvalidFormatError("Invalid DNA format: missing :: separator")

        # Parse module section
        module_part = parts[0]
        module_segments = module_part.split(':')

        if not module_segments:
            raise InvalidFormatError("Invalid DNA format: empty module section")

        # First segment is ship
        ship_id_str = module_segments[0]
        if not ship_id_str:
            raise InvalidFormatError("Invalid DNA format: missing ship ID")

        try:
            # Remove trailing underscore if present (indicates something special)
            ship_type_id = int(ship_id_str.rstrip('_'))
        except ValueError:
            raise InvalidFormatError(f"Invalid DNA format: invalid ship ID '{ship_id_str}'")

        data = FittingData(
            name=f"DNA Fit {ship_type_id}",
            ship_type_id=ship_type_id,
            ship_type_name=get_item_name(ship_type_id),
        )

        # Parse remaining segments as modules
        # Use GROUP_TO_SLOT to determine slot type for each module
        for segment in module_segments[1:]:
            if not segment:
                continue

            # Parse type_id:count or type_id;count or type_id(count)
            type_id, count = self._parse_dna_segment(segment)
            if type_id is None:
                continue

            # Determine slot type from item group
            slot_type = get_slot_type_for_type(type_id)

            # Add to appropriate slot list
            if slot_type == 'high':
                for _ in range(count):
                    data.high_slots.append(type_id)
            elif slot_type == 'med':
                for _ in range(count):
                    data.med_slots.append(type_id)
            elif slot_type == 'low':
                for _ in range(count):
                    data.low_slots.append(type_id)
            elif slot_type == 'rig':
                for _ in range(count):
                    data.rig_slots.append(type_id)
            elif slot_type == 'subsystem':
                for _ in range(count):
                    data.subsystem_slots.append(type_id)
            else:
                # Unknown slot type, default to low for compatibility
                data.low_slots.append(type_id)

        # Parse drone/cargo section (if present)
        if len(parts) > 1 and parts[1]:
            drone_cargo_part = parts[1]
            drone_cargo_segments = drone_cargo_part.split(':')

            for segment in drone_cargo_segments:
                if not segment:
                    continue

                type_id, count = self._parse_dna_segment(segment)
                if type_id is None:
                    continue

                # Default to drones - cargo detection would require category check
                data.drones.append((type_id, count))

        return data

    def _parse_dna_segment(self, segment: str) -> Tuple[int | None, int]:
        """
        Parse a DNA segment into type_id and count.

        Handles various formats:
        - type_id:count
        - type_id;count
        - type_id(count)
        - type_id (implicit count=1)
        """
        segment = segment.strip()
        if not segment:
            return None, 0

        # Try type_id:count first
        if ':' in segment:
            parts = segment.split(':', 1)
            if len(parts) == 2 and parts[0].strip():
                try:
                    return int(parts[0].strip()), int(parts[1].strip())
                except ValueError:
                    pass

        # Try type_id;count
        if ';' in segment:
            parts = segment.split(';', 1)
            if len(parts) == 2 and parts[0].strip():
                try:
                    return int(parts[0].strip()), int(parts[1].strip())
                except ValueError:
                    pass

        # Try type_id(count)
        match = re.match(r'(\d+)\((\d+)\)', segment)
        if match:
            try:
                return int(match.group(1)), int(match.group(2))
            except ValueError:
                pass

        # Just a type ID
        try:
            type_id = int(segment.rstrip('_'))
            return type_id, 1
        except ValueError:
            return None, 0

    def validate(self, content: str) -> bool:
        """Validate DNA format."""
        content = content.strip()

        # Must have :: separator
        if '::' not in content:
            return False

        # Must have : separated segments with numbers
        parts = content.split('::')
        module_part = parts[0]

        # Check if first segment looks like a ship ID
        segments = module_part.split(':')
        if not segments or not segments[0].strip().isdigit():
            return False

        return True


class DNASerializer(FittingSerializer):
    """
    Serializer for DNA format.

    Outputs compact DNA format suitable for chat links.

    Format: SHIP:HIGHS:MEDS:LOWS:RIGS:SUBSYSTEMS::DRONES:CARGO
    """

    def serialize(self, data: FittingData) -> str:
        """Serialize FittingData to DNA format string."""
        parts = []

        # Ship ID
        parts.append(str(data.ship_type_id))

        # Modules by slot type
        # DNA format order: high, med, low, rig, subsystem
        slot_lists = [
            data.high_slots,
            data.med_slots,
            data.low_slots,
            data.rig_slots,
            data.subsystem_slots,
        ]

        for slot_list in slot_lists:
            if slot_list:
                # Each module as type_id;1 (or count duplicates)
                for type_id in slot_list:
                    if type_id:
                        parts.append(f"{type_id};1")
            else:
                # Empty slot section - add empty segment
                parts.append('')

        # Separator between modules and drones/cargo
        module_str = ':'.join(parts)

        # Drones
        drone_parts = []
        for drone_type_id, quantity in data.drones:
            drone_parts.append(f"{drone_type_id};{quantity}")

        # Cargo
        for item_type_id, quantity in data.cargo:
            drone_parts.append(f"{item_type_id};{quantity}")

        drone_str = ':'.join(drone_parts) if drone_parts else ''

        return f"{module_str}::{drone_str}"
