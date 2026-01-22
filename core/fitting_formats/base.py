"""
Base classes for fitting format parsers and serializers.

Provides abstract base classes and data structures for all EVE fitting formats.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field


@dataclass
class FittingData:
    """
    Unified fitting data structure for all EVE fitting formats.

    This is the intermediate representation used when converting between
    different formats or importing/exporting to/from the database.
    """

    # Basic info
    name: str
    description: str = ""
    ship_type_id: int = 0
    ship_type_name: str = ""

    # Module slots (list of type_ids, 0 or None for empty slots)
    high_slots: List[int] = field(default_factory=list)
    med_slots: List[int] = field(default_factory=list)
    low_slots: List[int] = field(default_factory=list)
    rig_slots: List[int] = field(default_factory=list)
    subsystem_slots: List[int] = field(default_factory=list)

    # Service slots (for structures)
    services: List[int] = field(default_factory=list)

    # Charges: maps position (global or per-slot) to charge_type_id
    # Format: {slot_type_position: charge_type_id} or {position: charge_type_id}
    charges: Dict[int, int] = field(default_factory=dict)

    # Offline module positions (global positions across all slots)
    offline: List[int] = field(default_factory=list)

    # Drones and fighters: list of (type_id, quantity) tuples
    drones: List[Tuple[int, int]] = field(default_factory=list)

    # Cargo items: list of (type_id, quantity) tuples
    cargo: List[Tuple[int, int]] = field(default_factory=list)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_slot_list(self, slot_type: str) -> List[int]:
        """Get the module list for a given slot type."""
        slot_map = {
            'high': self.high_slots,
            'med': self.med_slots,
            'low': self.low_slots,
            'rig': self.rig_slots,
            'subsystem': self.subsystem_slots,
        }
        return slot_map.get(slot_type, [])

    def set_slot_list(self, slot_type: str, modules: List[int]) -> None:
        """Set the module list for a given slot type."""
        if slot_type == 'high':
            self.high_slots = modules
        elif slot_type == 'med':
            self.med_slots = modules
        elif slot_type == 'low':
            self.low_slots = modules
        elif slot_type == 'rig':
            self.rig_slots = modules
        elif slot_type == 'subsystem':
            self.subsystem_slots = modules

    def total_modules(self) -> int:
        """Count total number of fitted modules (excluding empty slots)."""
        return sum(
            len([m for m in slots if m])
            for slots in [self.high_slots, self.med_slots, self.low_slots,
                         self.rig_slots, self.subsystem_slots]
        )


class FittingParser(ABC):
    """
    Abstract base class for fitting parsers.

    Subclasses implement parsing for specific EVE fitting formats.
    """

    @abstractmethod
    def parse(self, content: str) -> FittingData:
        """
        Parse fitting content into FittingData.

        Args:
            content: Fitting content as string

        Returns:
            FittingData object with parsed fitting data

        Raises:
            InvalidFormatError: If content is not valid for this format
            ItemNotFoundError: If an item cannot be found in the database
        """
        pass

    @abstractmethod
    def validate(self, content: str) -> bool:
        """
        Validate content format without full parsing.

        Args:
            content: Fitting content as string

        Returns:
            True if content appears to be valid for this format
        """
        pass

    def _strip_comments(self, content: str) -> str:
        """
        Remove comments from content (if supported by format).

        Base implementation returns content unchanged.
        """
        return content


class FittingSerializer(ABC):
    """
    Abstract base class for fitting serializers.

    Subclasses implement serialization for specific EVE fitting formats.
    """

    @abstractmethod
    def serialize(self, data: FittingData) -> str:
        """
        Serialize FittingData to format string.

        Args:
            data: FittingData object to serialize

        Returns:
            Fitting content as string in this format
        """
        pass

    def _format_item_name(self, name: str, quantity: int = 1) -> str:
        """
        Format an item name with quantity (for formats that support it).

        Args:
            name: Item name
            quantity: Quantity (default 1, no suffix)

        Returns:
            Formatted string (e.g., "Warrior II x5" or just "Warrior II")
        """
        if quantity > 1:
            return f"{name} x{quantity}"
        return name

    def _format_offline_module(self, name: str, is_offline: bool) -> str:
        """
        Format a module name with offline indicator (if supported).

        Args:
            name: Module name
            is_offline: Whether module is offline

        Returns:
            Formatted string (e.g., "Module Name /offline" or just "Module Name")
        """
        if is_offline:
            return f"{name} /offline"
        return name
