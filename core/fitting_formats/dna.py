"""
DNA (Fitting DNA) format parser and serializer.

DNA is a compact format used for sharing fits in EVE chat.
It uses type IDs and is very space-efficient.

Example:
    626:12058;1:25606;1::5973;5:11928;2:

Format: SHIP:HIGHS:MEDS:LOWS:RIGS::DRONES
- Each section is type_id:count pairs separated by colons
- Three colons (::) separate modules from drones/cargo
- Underscore suffix indicates unfitted module
"""

from typing import List
from .base import FittingParser, FittingSerializer, FittingData
from .exceptions import InvalidFormatError, ItemNotFoundError
from .utils import get_item_name


class DNAParser(FittingParser):
    """
    Parser for DNA format.

    DNA format structure:
    SHIP_ID:HIGHS:MEDS:LOWS:RIGS::CHARGES

    Each section contains type_id:count pairs separated by colons.
    """

    def parse(self, content: str) -> FittingData:
        """Parse DNA format content into FittingData."""
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
            ship_type_id = int(ship_id_str.rstrip('_'))
        except ValueError:
            raise InvalidFormatError(f"Invalid DNA format: invalid ship ID '{ship_id_str}'")

        data = FittingData(
            name=f"DNA Fit {ship_type_id}",
            ship_type_id=ship_type_id,
            ship_type_name=get_item_name(ship_type_id),
        )

        # Parse module slots
        # DNA format is compact and doesn't explicitly mark slot boundaries
        # We need to infer slot types from item attributes
        # For now, this is a simplified implementation

        # Parse remaining segments as modules
        # TODO: Implement proper slot type detection using dgmTypeAttributes
        for segment in module_segments[1:]:
            if not segment:
                continue

            # Parse type_id:count or type_id;count
            if ';' in segment:
                type_id_str, count_str = segment.split(';', 1)
            else:
                # Look for trailing number
                import re
                match = re.match(r'(\d+)[_;](\d+)', segment)
                if match:
                    type_id_str, count_str = match.groups()
                else:
                    # Just a type ID, count is 1
                    type_id_str = segment.rstrip('_')
                    count_str = '1'

            try:
                type_id = int(type_id_str)
                count = int(count_str)
            except ValueError:
                continue

            # For now, add to high slots (TODO: proper slot detection)
            for _ in range(count):
                data.high_slots.append(type_id)

        # Parse drone/cargo section (if present)
        if len(parts) > 1 and parts[1]:
            drone_part = parts[1]
            drone_segments = drone_part.split(':')

            for segment in drone_segments:
                if not segment:
                    continue

                if ';' in segment:
                    type_id_str, count_str = segment.split(';', 1)
                else:
                    match = segment.rsplit(';', 1) if ';' in segment else [segment, '1']
                    if len(match) == 2:
                        type_id_str, count_str = match
                    else:
                        type_id_str = segment
                        count_str = '1'

                try:
                    type_id = int(type_id_str)
                    count = int(count_str)
                except ValueError:
                    continue

                data.drones.append((type_id, count))

        return data

    def validate(self, content: str) -> bool:
        """Validate DNA format."""
        # Must have :: separator
        if '::' not in content:
            return False

        # Must have : separated segments with numbers
        parts = content.split('::')
        module_part = parts[0]

        # Check if first segment looks like a ship ID
        segments = module_part.split(':')
        if not segments or not segments[0].isdigit():
            return False

        return True


class DNASerializer(FittingSerializer):
    """
    Serializer for DNA format.

    Outputs compact DNA format suitable for chat links.
    """

    def serialize(self, data: FittingData) -> str:
        """Serialize FittingData to DNA format string."""
        parts = []

        # Ship ID
        parts.append(str(data.ship_type_id))

        # Modules (simplified - just type_ids with ;1 suffix)
        # TODO: Proper formatting with slot position tracking
        for type_id in data.high_slots + data.med_slots + data.low_slots + data.rig_slots:
            if type_id:
                parts.append(f"{type_id};1")

        # Empty slots count for subsystems (if ship has them)
        if data.subsystem_slots:
            for _ in range(5 - len(data.subsystem_slots)):  # T3s have 5 subsystem slots
                parts.append('')

        # Separator
        module_str = ':'.join(parts)

        # Drones
        drone_parts = []
        for drone_type_id, quantity in data.drones:
            drone_parts.append(f"{drone_type_id};{quantity}")
        drone_str = ':'.join(drone_parts)

        return f"{module_str}::{drone_str}"
