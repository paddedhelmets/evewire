"""
Exceptions for fitting format parsing and serialization.
"""


class FittingFormatError(Exception):
    """Base exception for fitting format errors."""

    pass


class InvalidFormatError(FittingFormatError):
    """Raised when fitting content is not in a valid format."""

    pass


class ItemNotFoundError(FittingFormatError):
    """Raised when an item type cannot be found in the database."""

    def __init__(self, identifier: str, search_type: str = "name"):
        self.identifier = identifier
        self.search_type = search_type
        super().__init__(f"Item not found: {search_type}='{identifier}'")


class SlotMappingError(FittingFormatError):
    """Raised when a slot cannot be mapped to a slot type."""

    pass


class FormatDetectionError(FittingFormatError):
    """Raised when format auto-detection fails."""

    pass
