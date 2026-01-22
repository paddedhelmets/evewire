"""
EVE Fitting Format Import/Export Module

Provides unified API for importing/exporting EVE Online fittings in multiple formats:
- EFT (EVE Fitting Tool) - Human-readable text format
- DNA - Compact type_id format
- XML - CCP's official XML format

Usage:
    from core.fitting_formats import FittingImporter, FittingExporter, detect_format

    # Import
    fitting = FittingImporter.import_from_string(eft_content, format_name='eft')

    # Auto-detect format
    fitting = FittingImporter.import_from_string(content)

    # Export
    eft_string = FittingExporter.export_to_string(fitting, format_name='eft')

    # Detect format
    format_name = detect_format(content)
"""

from typing import Dict, Type, Optional

from .base import FittingData, FittingParser, FittingSerializer
from .exceptions import (
    FittingFormatError,
    InvalidFormatError,
    ItemNotFoundError,
    SlotMappingError,
    FormatDetectionError,
)
from .utils import (
    resolve_item_name,
    get_item_name,
    normalize_slot_type,
    parse_slot_position,
    detect_ship_type,
    slot_type_to_eft_name,
    eft_name_to_slot_type,
    clear_caches,
)


# Format registry: maps format name to (parser_class, serializer_class) tuple
# Import format classes lazily to avoid circular imports
_FORMATS: Dict[str, tuple] = {
    'eft': None,  # Will be populated on first use
    'dna': None,
    'xml': None,
}


def _get_format_classes(format_name: str) -> tuple:
    """
    Get parser and serializer classes for a format.

    Imports classes lazily to avoid circular dependencies.
    """
    if _FORMATS[format_name] is None:
        if format_name == 'eft':
            from .eft import EFTParser, EFTSerializer
            _FORMATS['eft'] = (EFTParser, EFTSerializer)
        elif format_name == 'dna':
            from .dna import DNAParser, DNASerializer
            _FORMATS['dna'] = (DNAParser, DNASerializer)
        elif format_name == 'xml':
            from .xml import XMLParser, XMLSerializer
            _FORMATS['xml'] = (XMLParser, XMLSerializer)
        else:
            raise FittingFormatError(f"Unknown format: {format_name}")

    return _FORMATS[format_name]


def get_parser(format_name: str) -> Type[FittingParser]:
    """
    Get parser class for a format.

    Args:
        format_name: Format name ('eft', 'dna', 'xml')

    Returns:
        Parser class for the format

    Raises:
        FittingFormatError: If format is unknown
    """
    parser_class, _ = _get_format_classes(format_name)
    return parser_class


def get_serializer(format_name: str) -> Type[FittingSerializer]:
    """
    Get serializer class for a format.

    Args:
        format_name: Format name ('eft', 'dna', 'xml')

    Returns:
        Serializer class for the format

    Raises:
        FittingFormatError: If format is unknown
    """
    _, serializer_class = _get_format_classes(format_name)
    return serializer_class


def detect_format(content: str) -> str:
    """
    Auto-detect fitting format from content.

    Args:
        content: Fitting content as string

    Returns:
        Format name ('eft', 'dna', or 'xml')

    Raises:
        FormatDetectionError: If format cannot be determined
    """
    content = content.strip()

    # XML: starts with <?xml or <fittings
    if content.startswith('<?xml') or content.startswith('<fittings'):
        return 'xml'

    # DNA: contains type_id:count; pattern with :: separator
    # Check for DNA-specific patterns: ship_id:slot1;count:slot2;count:::
    if ':' in content and ';' in content:
        # DNA format typically has :: separating modules from drones/cargo
        if '::' in content:
            return 'dna'
        # Also check if it looks like DNA (short segments with numbers)
        parts = content.split(':')
        if len(parts) > 2 and all(
            all(c.isdigit() or c in ';_' for c in part)
            for part in parts[:3] if part
        ):
            return 'dna'

    # EFT: starts with [Ship, Name] or [Ship,Name]
    first_line = content.split('\n')[0].strip()
    if first_line.startswith('[') and ']' in first_line and ',' in first_line:
        return 'eft'

    # Check for EFT-like content (module names on separate lines)
    # If we see recognizable module names, assume EFT
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    if len(lines) > 1:
        # First line might be the header, check if rest look like modules
        for line in lines[1:10]:  # Check first few lines
            # Skip empty lines and sections
            if not line or line.startswith('['):
                continue
            # If line looks like an item name (has spaces, no special chars)
            if ' ' in line and not any(c in line for c in ':;<>{}'):
                return 'eft'

    raise FormatDetectionError(
        "Could not auto-detect format. Please specify format explicitly."
    )


class FittingImporter:
    """
    Unified fitting import service.

    Provides format-agnostic API for importing fittings from EVE formats.
    """

    @staticmethod
    def import_from_string(
        content: str,
        format_name: Optional[str] = None,
        auto_detect: bool = True,
    ):
        """
        Import a fitting from string content.

        Args:
            content: Fitting content (EFT, DNA, or XML)
            format_name: Format ('eft', 'dna', 'xml'), or None to auto-detect
            auto_detect: Whether to auto-detect format if not specified

        Returns:
            Created Fitting model instance

        Raises:
            FittingFormatError: If format is invalid or detection fails
            ItemNotFoundError: If item type not found in SDE
        """
        from core.doctrines.models import Fitting

        if auto_detect and not format_name:
            format_name = detect_format(content)

        parser_class = get_parser(format_name)
        parser = parser_class()

        # Parse content into FittingData
        data = parser.parse(content)

        # Convert FittingData to Fitting model
        return FittingImporter._create_fitting(data)

    @staticmethod
    def _create_fitting(data: FittingData):
        """
        Create Fitting model from FittingData.

        Args:
            data: FittingData instance

        Returns:
            Created Fitting model with all related objects
        """
        from core.doctrines.models import (
            Fitting,
            FittingEntry,
            FittingCharge,
            FittingDrone,
            FittingCargoItem,
            FittingService,
        )
        from django.db import transaction

        with transaction.atomic():
            # Create fitting
            fitting = Fitting.objects.create(
                name=data.name,
                description=data.description,
                ship_type_id=data.ship_type_id,
                tags=data.metadata.get('tags', {}),
            )

            # Create module entries
            slot_map = {
                'high': data.high_slots,
                'med': data.med_slots,
                'low': data.low_slots,
                'rig': data.rig_slots,
                'subsystem': data.subsystem_slots,
            }

            position_map = {}  # Track global positions for offline/charge mapping

            for slot_type, modules in slot_map.items():
                for position, type_id in enumerate(modules):
                    if type_id:  # Skip empty slots (0 or None)
                        # Check if this position is offline
                        is_offline = position in data.offline

                        entry = FittingEntry.objects.create(
                            fitting=fitting,
                            slot_type=slot_type,
                            position=position,
                            module_type_id=type_id,
                            is_offline=is_offline,
                        )

                        # Track position for charge lookup
                        global_pos = len(position_map)
                        position_map[global_pos] = entry

                        # Add charge if exists for this position
                        if global_pos in data.charges:
                            FittingCharge.objects.create(
                                fitting=fitting,
                                fitting_entry=entry,
                                charge_type_id=data.charges[global_pos],
                                quantity=1,
                            )

            # Create drones
            for drone_type_id, quantity in data.drones:
                # Determine bay type from category if possible
                # For now, default to drone bay
                FittingDrone.objects.create(
                    fitting=fitting,
                    drone_type_id=drone_type_id,
                    bay_type='drone',
                    quantity=quantity,
                )

            # Create cargo items
            for item_type_id, quantity in data.cargo:
                FittingCargoItem.objects.create(
                    fitting=fitting,
                    item_type_id=item_type_id,
                    quantity=quantity,
                )

            # Create services
            for position, service_type_id in enumerate(data.services):
                FittingService.objects.create(
                    fitting=fitting,
                    service_type_id=service_type_id,
                    position=position,
                )

        return fitting


class FittingExporter:
    """
    Unified fitting export service.

    Provides format-agnostic API for exporting fittings to EVE formats.
    """

    @staticmethod
    def export_to_string(fitting, format_name: str) -> str:
        """
        Export a fitting to specified format.

        Args:
            fitting: Fitting model instance
            format_name: Format ('eft', 'dna', 'xml')

        Returns:
            Fitting content as string

        Raises:
            FittingFormatError: If format is unknown
        """
        serializer_class = get_serializer(format_name)
        serializer = serializer_class()

        # Convert Fitting to FittingData
        data = FittingExporter._fitting_to_data(fitting)

        # Serialize to format
        return serializer.serialize(data)

    @staticmethod
    def _fitting_to_data(fitting) -> FittingData:
        """
        Convert Fitting model to FittingData.

        Args:
            fitting: Fitting model instance

        Returns:
            FittingData instance
        """
        from core.doctrines.models import (
            FittingEntry,
            FittingCharge,
            FittingDrone,
            FittingCargoItem,
            FittingService,
        )

        # Get modules by slot
        entries = fitting.entries.all().order_by('slot_type', 'position')

        high_slots = []
        med_slots = []
        low_slots = []
        rig_slots = []
        subsystem_slots = []
        charges = {}
        offline = []

        position_map = {}  # Maps (slot_type, position) to global position

        global_pos = 0
        for slot_type in ['low', 'med', 'high', 'rig', 'subsystem']:
            slot_entries = [e for e in entries if e.slot_type == slot_type]
            slot_list = []

            for entry in slot_entries:
                # Extend list if needed for position
                while len(slot_list) <= entry.position:
                    slot_list.append(0)  # Empty slot

                slot_list[entry.position] = entry.module_type_id

                # Track position for charge/offline mapping
                position_map[(slot_type, entry.position)] = global_pos

                if entry.is_offline:
                    offline.append(global_pos)

                # Get charge for this entry
                charge = entry.charges.first()
                if charge:
                    charges[global_pos] = charge.charge_type_id

                global_pos += 1

            # Assign to appropriate slot list
            if slot_type == 'high':
                high_slots = slot_list
            elif slot_type == 'med':
                med_slots = slot_list
            elif slot_type == 'low':
                low_slots = slot_list
            elif slot_type == 'rig':
                rig_slots = slot_list
            elif slot_type == 'subsystem':
                subsystem_slots = slot_list

        # Get drones
        drones = [(d.drone_type_id, d.quantity) for d in fitting.drones.all()]

        # Get cargo
        cargo = [(c.item_type_id, c.quantity) for c in fitting.cargo_items.all()]

        # Get services
        services = [s.service_type_id for s in fitting.services.all()]

        return FittingData(
            name=fitting.name,
            description=fitting.description,
            ship_type_id=fitting.ship_type_id,
            ship_type_name=fitting.ship_type_name,
            high_slots=high_slots,
            med_slots=med_slots,
            low_slots=low_slots,
            rig_slots=rig_slots,
            subsystem_slots=subsystem_slots,
            charges=charges,
            offline=offline,
            drones=drones,
            cargo=cargo,
            services=services,
            metadata={'tags': fitting.tags},
        )


__all__ = [
    # Public API
    'FittingImporter',
    'FittingExporter',
    'detect_format',
    # Data structures
    'FittingData',
    'FittingParser',
    'FittingSerializer',
    # Exceptions
    'FittingFormatError',
    'InvalidFormatError',
    'ItemNotFoundError',
    'SlotMappingError',
    'FormatDetectionError',
    # Utilities
    'resolve_item_name',
    'get_item_name',
    'normalize_slot_type',
    'parse_slot_position',
    'detect_ship_type',
    'slot_type_to_eft_name',
    'eft_name_to_slot_type',
    'clear_caches',
    # Format parsers/serializers (available but typically used via service API)
    'EFTParser',
    'EFTSerializer',
    'DNAParser',
    'DNASerializer',
    'XMLParser',
    'XMLSerializer',
]
