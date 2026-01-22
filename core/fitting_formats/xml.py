"""
XML format parser and serializer for EVE fittings.

This is the official CCP XML format used by EVE Online's
in-game fitting export/import feature.

Example:
    <?xml version="1.0" ?>
    <fittings>
        <fitting name="New Vexor">
            <shipType value="Vexor"/>
            <description value=""/>
            <hardware slot="low slot 0" type="Damage Control II"/>
            <hardware qty="5" slot="cargo" type="Warrior II"/>
        </fitting>
    </fittings>
"""

import xml.etree.ElementTree as ET
from typing import List
from .base import FittingParser, FittingSerializer, FittingData
from .exceptions import InvalidFormatError, ItemNotFoundError
from .utils import (
    resolve_item_name,
    get_item_name,
    normalize_slot_type,
    parse_slot_position,
    detect_ship_type,
)


class XMLParser(FittingParser):
    """
    Parser for EVE XML format.

    XML format structure:
    <fittings>
        <fitting name="...">
            <shipType value="..." />
            <description value="..." />
            <hardware slot="..." type="..." />
            <hardware slot="..." qty="..." type="..." />
        </fitting>
    </fittings>
    """

    def parse(self, content: str) -> FittingData:
        """Parse XML format content into FittingData."""
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            raise InvalidFormatError(f"Invalid XML: {e}")

        # Handle both <fittings> root and direct <fitting>
        if root.tag == 'fittings':
            fitting_elems = root.findall('fitting')
            if not fitting_elems:
                raise InvalidFormatError("No fitting elements found in XML")
            # Parse first fitting (TODO: handle multiple fittings)
            fitting_elem = fitting_elems[0]
        elif root.tag == 'fitting':
            fitting_elem = root
        else:
            raise InvalidFormatError(f"Unknown root element: {root.tag}")

        # Get fitting name
        fitting_name = fitting_elem.get('name', 'Unnamed Fit')

        # Get ship type
        ship_type_elem = fitting_elem.find('shipType')
        if ship_type_elem is None:
            raise InvalidFormatError("Missing shipType element")

        ship_name = ship_type_elem.get('value')
        if not ship_name:
            # Try typeid attribute
            ship_type_id = ship_type_elem.get('typeid')
            if ship_type_id:
                ship_type_id = int(ship_type_id)
                ship_name = get_item_name(ship_type_id)
            else:
                raise InvalidFormatError("shipType missing value attribute")

        ship_type_id = detect_ship_type(ship_name)
        if not ship_type_id:
            raise ItemNotFoundError(ship_name, search_type="ship")

        # Get description
        description_elem = fitting_elem.find('description')
        description = ""
        if description_elem is not None:
            description = description_elem.get('value', '')

        data = FittingData(
            name=fitting_name,
            description=description,
            ship_type_id=ship_type_id,
            ship_type_name=ship_name,
        )

        # Parse hardware elements (modules, drones, cargo)
        for hardware in fitting_elem.findall('hardware'):
            slot = hardware.get('slot', '')
            type_name = hardware.get('type', '')
            qty_str = hardware.get('qty', '1')

            if not type_name:
                continue

            # Resolve item name
            type_id = resolve_item_name(type_name)
            if not type_id:
                # Skip unknown items
                continue

            quantity = int(qty_str) if qty_str.isdigit() else 1

            # Determine slot type from slot attribute
            slot_type = normalize_slot_type(slot)

            if slot_type == 'cargo' or 'cargo' in slot.lower():
                # Cargo item
                data.cargo.append((type_id, quantity))
            elif slot_type in ('low', 'med', 'high', 'rig', 'subsystem'):
                # Module
                position = parse_slot_position(slot)
                slot_list = data.get_slot_list(slot_type)

                # Extend list if needed
                while len(slot_list) <= position:
                    slot_list.append(0)

                slot_list[position] = type_id
                data.set_slot_list(slot_type, slot_list)
            else:
                # Unknown slot, might be drone bay
                data.drones.append((type_id, quantity))

        return data

    def validate(self, content: str) -> bool:
        """Validate XML format."""
        try:
            root = ET.fromstring(content)
            # Must have fittings or fitting root
            return root.tag in ('fittings', 'fitting')
        except ET.ParseError:
            return False


class XMLSerializer(FittingSerializer):
    """
    Serializer for EVE XML format.

    Outputs XML compatible with EVE Online's in-game import.
    """

    def serialize(self, data: FittingData) -> str:
        """Serialize FittingData to XML format string."""
        # Create root element
        fittings = ET.Element('fittings')

        # Create fitting element
        fitting = ET.SubElement(fittings, 'fitting')
        fitting.set('name', data.name)

        # Add description
        description = ET.SubElement(fitting, 'description')
        description.set('value', data.description)

        # Add ship type
        ship_type = ET.SubElement(fitting, 'shipType')
        ship_type.set('value', data.ship_type_name)

        # Add hardware elements
        slot_types = [
            ('low', data.low_slots),
            ('med', data.med_slots),
            ('high', data.high_slots),
            ('rig', data.rig_slots),
            ('subsystem', data.subsystem_slots),
        ]

        for slot_type, slots in slot_types:
            for position, type_id in enumerate(slots):
                if not type_id:
                    continue

                item_name = get_item_name(type_id)
                slot_name = f"{slot_type}_slot_{position}"

                hardware = ET.SubElement(fitting, 'hardware')
                hardware.set('slot', slot_name)
                hardware.set('type', item_name)

        # Add drones
        for drone_type_id, quantity in data.drones:
            drone_name = get_item_name(drone_type_id)

            hardware = ET.SubElement(fitting, 'hardware')
            hardware.set('slot', 'drone bay')
            hardware.set('type', drone_name)
            hardware.set('qty', str(quantity))

        # Add cargo
        for item_type_id, quantity in data.cargo:
            item_name = get_item_name(item_type_id)

            hardware = ET.SubElement(fitting, 'hardware')
            hardware.set('slot', 'cargo')
            hardware.set('type', item_name)
            hardware.set('qty', str(quantity))

        # Generate XML string
        xml_str = ET.tostring(fittings, encoding='unicode')

        # Add XML declaration
        return '<?xml version="1.0" ?>\n' + xml_str
