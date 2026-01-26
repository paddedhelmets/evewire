"""
EFT (EVE Fitting Tool) format parser and serializer.

EFT format is a human-readable text format used by EVE Online's
in-game fitting window and many third-party tools.

EFT Format Structure:
1. First line: [ShipName, FittingName]
2. Low slot modules (one per line)
3. Empty line separator
4. Medium slot modules
5. Empty line separator
6. High slot modules
7. Empty line separator
8. Rigs
9. Empty line separator (optional)
10. Subsystems (for T3 ships)
11. Two empty lines
12. Drones/fighters (with xN suffix for quantity)
13. Cargo items (with xN suffix for quantity)

Module suffixes:
- /offline - Module is offline
- xN - Quantity (for drones, cargo)

Empty slots: [Empty X Slot] notation (valid on import, not exported)
"""

import re
from typing import List, Dict, Tuple, Optional

from .base import FittingParser, FittingSerializer, FittingData
from .exceptions import InvalidFormatError, ItemNotFoundError
from .utils import (
    resolve_item_name,
    get_item_name,
    detect_ship_type,
    is_charge_type,
)


class EFTParser(FittingParser):
    """Parser for EFT (EVE Fitting Tool) format."""

    # Patterns
    HEADER_PATTERN = re.compile(r'^\[([^,\]]+),\s*([^\]]+)\]')
    EMPTY_SLOT_PATTERN = re.compile(r'\[Empty\s+(\w+)\s+Slot\]', re.IGNORECASE)
    QUANTITY_PATTERN = re.compile(r'\s+x(\d+)$')
    OFFLINE_PATTERN = re.compile(r'\s*/offline$', re.IGNORECASE)

    # Section order in EFT format
    SECTIONS = ['low', 'med', 'high', 'rig', 'subsystem']

    def parse(self, content: str) -> FittingData:
        """Parse EFT format content into FittingData."""
        lines = [line.rstrip() for line in content.strip().split('\n')]

        if not lines:
            raise InvalidFormatError("Empty EFT content")

        # Parse header
        header_line = lines[0].strip()
        header_match = self.HEADER_PATTERN.match(header_line)
        if not header_match:
            raise InvalidFormatError(
                f"Invalid EFT header: '{header_line}'. "
                "Expected format: [ShipName, FittingName]"
            )

        ship_name = header_match.group(1).strip()
        fitting_name = header_match.group(2).strip()

        # Resolve ship type
        ship_type_id = detect_ship_type(ship_name)
        if not ship_type_id:
            raise ItemNotFoundError(ship_name, search_type="ship")

        # Initialize data
        data = FittingData(
            name=fitting_name,
            ship_type_id=ship_type_id,
            ship_type_name=ship_name,
            description="",
        )

        # Split content by empty lines to find sections
        sections = []
        current_section = []
        consecutive_empty_lines = 0

        for line in lines[1:]:
            line = line.strip()
            if not line:
                consecutive_empty_lines += 1
                if current_section:
                    sections.append(current_section)
                    current_section = []

                # Two consecutive empty lines marks transition to drones/cargo
                if consecutive_empty_lines >= 2:
                    # Rest is drones and cargo
                    remaining_lines = lines[lines.index(line) + 1:]
                    self._parse_drones_and_cargo(remaining_lines, data)
                    break
            else:
                consecutive_empty_lines = 0  # Reset when we see content
                current_section.append(line)

        # Add last section if present
        if current_section:
            sections.append(current_section)

        # Map sections to slot types based on order
        # EFT format: low -> med -> high -> rig -> subsystem
        for i, section in enumerate(sections):
            if i >= len(self.SECTIONS):
                break

            slot_type = self.SECTIONS[i]
            for line in section:
                self._parse_module_line(line, data, slot_type)

        return data

    def _parse_drones_and_cargo(self, lines: List[str], data: FittingData):
        """Parse drones and cargo from remaining lines."""
        in_cargo = False

        for line in lines:
            line = line.strip()
            if not line:
                # Empty line between drones and cargo
                in_cargo = True
                continue

            # Check for offline suffix (not applicable to drones/cargo but strip it)
            is_offline = bool(self.OFFLINE_PATTERN.search(line))
            if is_offline:
                line = self.OFFLINE_PATTERN.sub('', line).strip()

            # Check for quantity suffix
            quantity_match = self.QUANTITY_PATTERN.search(line)
            quantity = 1
            if quantity_match:
                quantity = int(quantity_match.group(1))
                line = self.QUANTITY_PATTERN.sub('', line).strip()

            # Resolve item name
            type_id = resolve_item_name(line)
            if not type_id:
                # Skip unknown items
                continue

            if in_cargo:
                data.cargo.append((type_id, quantity))
            else:
                data.drones.append((type_id, quantity))

    def _parse_module_line(self, line: str, data: FittingData, slot_type: str):
        """Parse a module line and add it to the appropriate slot list."""
        # Check for empty slot notation
        empty_match = self.EMPTY_SLOT_PATTERN.match(line)
        if empty_match:
            # Empty slot, add 0 to the list
            slot_list = data.get_slot_list(slot_type)
            slot_list.append(0)
            data.set_slot_list(slot_type, slot_list)
            return

        # Check for offline suffix
        is_offline = bool(self.OFFLINE_PATTERN.search(line))
        if is_offline:
            line = self.OFFLINE_PATTERN.sub('', line).strip()

        # Resolve item name to type ID
        type_id = resolve_item_name(line)
        if not type_id:
            raise ItemNotFoundError(line)

        # Check if this is a charge (ammo, crystal, missile, etc.)
        # Charges are listed after the module that uses them
        if is_charge_type(type_id):
            # Get the current slot list to find the previous module
            slot_list = data.get_slot_list(slot_type)

            # Count actual modules (non-zero entries) to find the last real module
            module_count = sum(1 for x in slot_list if x != 0)

            if module_count == 0:
                # No module yet to associate charge with - skip
                return

            # Find the most recently added module (first non-zero from the end)
            for i in range(len(slot_list) - 1, -1, -1):
                if slot_list[i] != 0:
                    # Found the most recent module
                    # Calculate global position of this module
                    global_pos = sum(len(data.get_slot_list(s)) for s in self.SECTIONS[:self.SECTIONS.index(slot_type)])
                    global_pos += i
                    # Store the charge for this position
                    data.charges[global_pos] = type_id
                    return
            # No module found - skip the charge
            return

        # Add to slot list
        slot_list = data.get_slot_list(slot_type)
        slot_list.append(type_id)
        data.set_slot_list(slot_type, slot_list)

        # Track offline state (using global position)
        if is_offline:
            total_modules = sum(len(data.get_slot_list(s)) for s in self.SECTIONS[:self.SECTIONS.index(slot_type)])
            data.offline.append(total_modules + len(slot_list) - 1)

    def validate(self, content: str) -> bool:
        """Validate EFT format."""
        lines = content.strip().split('\n')
        if not lines:
            return False

        # Must have valid header
        header_line = lines[0].strip()
        return bool(self.HEADER_PATTERN.match(header_line))


class EFTSerializer(FittingSerializer):
    """Serializer for EFT format."""

    def serialize(self, data: FittingData) -> str:
        """Serialize FittingData to EFT format string."""
        lines = []

        # Header: [ShipName, FittingName]
        ship_name = data.ship_type_name or f"Type {data.ship_type_id}"
        lines.append(f"[{ship_name}, {data.name}]")

        # Track global position for offline module detection
        global_pos = 0

        # Low slots
        if data.low_slots:
            lines.extend(self._serialize_slots(data.low_slots, data.offline, 'low', global_pos))
            global_pos += len(data.low_slots)
            lines.append("")  # Empty line separator

        # Med slots
        if data.med_slots:
            lines.extend(self._serialize_slots(data.med_slots, data.offline, 'med', global_pos))
            global_pos += len(data.med_slots)
            lines.append("")  # Empty line separator

        # High slots
        if data.high_slots:
            lines.extend(self._serialize_slots(data.high_slots, data.offline, 'high', global_pos))
            global_pos += len(data.high_slots)
            lines.append("")  # Empty line separator

        # Rigs
        if data.rig_slots:
            lines.extend(self._serialize_slots(data.rig_slots, [], 'rig', global_pos))
            global_pos += len(data.rig_slots)
            lines.append("")  # Empty line separator

        # Subsystems
        if data.subsystem_slots:
            lines.extend(self._serialize_slots(data.subsystem_slots, [], 'subsystem', global_pos))
            global_pos += len(data.subsystem_slots)
            lines.append("")  # Empty line separator

        # Drones
        if data.drones:
            lines.append("")  # Extra empty line before drones
            for drone_type_id, quantity in data.drones:
                drone_name = get_item_name(drone_type_id)
                if quantity > 1:
                    lines.append(f"{drone_name} x{quantity}")
                else:
                    lines.append(drone_name)

        # Cargo
        if data.cargo:
            lines.append("")  # Empty line separator before cargo
            for item_type_id, quantity in data.cargo:
                item_name = get_item_name(item_type_id)
                if quantity > 1:
                    lines.append(f"{item_name} x{quantity}")
                else:
                    lines.append(item_name)

        return '\n'.join(lines)

    def _serialize_slots(
        self,
        slots: List[int],
        offline: List[int],
        slot_type: str,
        global_position: int = 0,
    ) -> List[str]:
        """Serialize a list of slot modules."""
        lines = []
        for position, type_id in enumerate(slots):
            if type_id:
                module_name = get_item_name(type_id)
                global_pos = global_position + position
                if global_pos in offline:
                    module_name = f"{module_name} /offline"
                lines.append(module_name)
        return lines
