"""
Abstract base class for character authentication sources.

All authentication backends (ESI SSO, GICE, etc.) must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class CharacterInfo:
    """
    Character information returned by auth sources.

    This is a common format that all auth sources must provide.
    """
    character_id: int
    character_name: str
    corporation_id: Optional[int] = None
    corporation_name: str = ""
    alliance_id: Optional[int] = None
    alliance_name: str = ""
    # Any additional data the source wants to store
    extra: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


@dataclass
class TokenResponse:
    """
    Token response from authentication flow.

    All auth sources must return this format after successful authentication.
    """
    # Core token data
    access_token: str
    refresh_token: Optional[str] = None  # None if using long-lived OIDC tokens
    expires_at: Optional[datetime] = None

    # Character info
    character_info: Optional[CharacterInfo] = None

    # Additional metadata
    scopes: List[str] = None
    extra: Dict[str, Any] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = []
        if self.extra is None:
            self.extra = {}


class CharacterSource(ABC):
    """
    Abstract interface for character authentication sources.

    All authentication backends must implement this interface.
    This allows evewire to support multiple auth methods (ESI SSO, GICE, etc.)
    without coupling core code to any specific implementation.
    """

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique identifier for this auth source (e.g., 'esi_sso', 'gice')."""
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name for this auth source (e.g., 'EVE SSO', 'GICE')."""
        pass

    @abstractmethod
    def get_auth_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Get the URL to initiate authentication flow.

        Args:
            redirect_uri: The callback URL after auth completes
            state: Optional state parameter for CSRF protection

        Returns:
            The full authentication URL to redirect the user to
        """
        pass

    @abstractmethod
    def handle_callback(self, code: str, state: Optional[str] = None,
                       redirect_uri: str = None) -> TokenResponse:
        """
        Handle the callback from auth provider.

        Args:
            code: The authorization code from callback
            state: The state parameter from callback
            redirect_uri: The callback URL (must match auth URL)

        Returns:
            TokenResponse with access token and character info
        """
        pass

    @abstractmethod
    def get_user_characters(self, access_token: str) -> List[CharacterInfo]:
        """
        Get list of characters for the authenticated user.

        For ESI SSO, this returns just the authenticated character.
        For GICE, this returns all pilots linked to the GICE account.

        Args:
            access_token: The access token from authentication

        Returns:
            List of CharacterInfo objects
        """
        pass

    @abstractmethod
    def refresh_access_token(self, character, refresh_token: str = None) -> TokenResponse:
        """
        Refresh an expired access token.

        Args:
            character: The Character model instance
            refresh_token: The refresh token (optional, for sources that use it)

        Returns:
            TokenResponse with new access token
        """
        pass

    @abstractmethod
    def get_access_token(self, character) -> str:
        """
        Get a valid access token for API calls.

        Handles token refresh if needed.

        Args:
            character: The Character model instance

        Returns:
            A valid access token string
        """
        pass

    def get_esi_base_url(self) -> str:
        """
        Get the base URL for ESI API calls.

        Most sources use the official ESI. Some (like GICE) may use a proxy.

        Returns:
            The base URL for ESI calls (e.g., 'https://esi.evetech.net/latest')
        """
        # Default to official ESI
        return "https://esi.evetech.net/latest"

    def get_esi_headers(self, character) -> Dict[str, str]:
        """
        Get headers for ESI API calls.

        Most sources use the standard Authorization header.
        Some (like GICE with a proxy) may add additional headers.

        Args:
            character: The Character model instance

        Returns:
            Dictionary of headers to include in ESI requests
        """
        access_token = self.get_access_token(character)
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def supports_multiple_characters(self) -> bool:
        """
        Whether this source supports fetching multiple characters per auth.

        ESI SSO: False (one character per auth flow)
        GICE: True (returns all pilots for the user)

        Returns:
            True if get_user_characters() can return multiple characters
        """
        return False

    def requires_character_reauth(self) -> bool:
        """
        Whether characters need to be re-authenticated individually.

        ESI SSO: True (each character needs its own SSO flow)
        GICE: False (OIDC token covers all pilots)

        Returns:
            True if each character needs individual auth
        """
        return True
