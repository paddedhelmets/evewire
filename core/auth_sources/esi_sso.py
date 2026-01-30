"""
EVE SSO (ESI) authentication source implementation.

This implements the CharacterSource interface for standard EVE SSO authentication.
"""

import logging
import secrets
import requests
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from core.auth_sources.base import (
    CharacterSource,
    CharacterInfo,
    TokenResponse,
)

logger = logging.getLogger('evewire')


class ESISSOCharacterSource(CharacterSource):
    """
    EVE SSO authentication source using ESI (EVE Swagger Interface).

    This is the default authentication method for evewire.
    Each character requires individual SSO authentication.
    """

    @property
    def source_id(self) -> str:
        return "esi_sso"

    @property
    def source_name(self) -> str:
        return "EVE SSO"

    def get_auth_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Get the EVE SSO login URL.

        Args:
            redirect_uri: The callback URL after auth completes
            state: Optional state parameter for CSRF protection

        Returns:
            The full EVE SSO authentication URL
        """
        from core.models import EveScope

        # Generate state if not provided (CSRF protection)
        if not state:
            state = ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                           for _ in range(16))

        params = {
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'client_id': settings.EVE_CLIENT_ID,
            'scope': ' '.join(EveScope.mvp_scopes()),
            'state': state,
        }

        login_url = getattr(settings, 'EVE_SSO_LOGIN_URL',
                           'https://login.eveonline.com/v2/oauth/authorize')
        return f'{login_url}?{urllib.parse.urlencode(params)}'

    def handle_callback(self, code: str, state: Optional[str] = None,
                       redirect_uri: str = None) -> TokenResponse:
        """
        Handle the EVE SSO OAuth callback.

        Args:
            code: The authorization code from callback
            state: The state parameter from callback (unused but kept for interface)
            redirect_uri: The callback URL (must match auth URL)

        Returns:
            TokenResponse with access token and character info
        """
        if redirect_uri is None:
            redirect_uri = settings.EVE_CALLBACK_URL

        # Exchange code for tokens
        token_url = getattr(settings, 'EVE_SSO_TOKEN_URL',
                           'https://login.eveonline.com/v2/oauth/token')
        response = requests.post(
            token_url,
            data={
                'grant_type': 'authorization_code',
                'code': code,
            },
            auth=(settings.EVE_CLIENT_ID, settings.EVE_CLIENT_SECRET),
            timeout=10,
        )
        response.raise_for_status()
        token_data = response.json()

        # Get character info from verify endpoint
        verify_url = getattr(settings, 'EVE_SSO_VERIFY_URL',
                            'https://login.eveonline.com/v2/oauth/verify')
        verify_response = requests.get(
            verify_url,
            headers={'Authorization': f"Bearer {token_data['access_token']}"},
            timeout=10,
        )
        verify_response.raise_for_status()
        character_data = verify_response.json()

        # Get character details from ESI
        character_info = self._fetch_character_details(
            character_data['CharacterID'],
            token_data['access_token']
        )

        # Calculate expiration
        expires_at = None
        if 'expires_in' in token_data:
            expires_at = timezone.now() + timedelta(seconds=token_data['expires_in'])

        return TokenResponse(
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token'),
            expires_at=expires_at,
            character_info=character_info,
            scopes=character_data.get('Scopes', '').split(),
            extra={
                'owner': character_data.get('Owner'),
                'token_type': token_data.get('token_type'),
            }
        )

    def get_user_characters(self, access_token: str) -> List[CharacterInfo]:
        """
        Get list of characters for the authenticated user.

        For ESI SSO, this returns just the authenticated character.
        Each character requires a separate SSO authentication flow.

        Args:
            access_token: The access token from authentication

        Returns:
            List containing a single CharacterInfo
        """
        # Verify character identity
        verify_url = getattr(settings, 'EVE_SSO_VERIFY_URL',
                            'https://login.eveonline.com/v2/oauth/verify')
        response = requests.get(
            verify_url,
            headers={'Authorization': f"Bearer {access_token}"},
            timeout=10,
        )
        response.raise_for_status()
        character_data = response.json()

        character_info = self._fetch_character_details(
            character_data['CharacterID'],
            access_token
        )

        return [character_info]

    def _fetch_character_details(self, character_id: int, access_token: str) -> CharacterInfo:
        """
        Fetch detailed character information from ESI.

        Args:
            character_id: The EVE character ID
            access_token: Access token for ESI requests

        Returns:
            CharacterInfo with corporation and alliance data
        """
        esi_base = getattr(settings, 'ESI_BASE_URL', 'https://esi.evetech.net/latest')

        # Get character public data
        response = requests.get(
            f'{esi_base}/characters/{character_id}/',
            timeout=10,
        )
        response.raise_for_status()
        char_data = response.json()

        # Get corporation info
        corp_id = char_data.get('corporation_id')
        corp_name = ""
        alliance_id = char_data.get('alliance_id')
        alliance_name = ""

        if corp_id:
            response = requests.get(
                f'{esi_base}/corporations/{corp_id}/',
                timeout=10,
            )
            response.raise_for_status()
            corp_data = response.json()
            corp_name = corp_data.get('name', '')

        if alliance_id:
            response = requests.get(
                f'{esi_base}/alliances/{alliance_id}/',
                timeout=10,
            )
            response.raise_for_status()
            alliance_data = response.json()
            alliance_name = alliance_data.get('name', '')

        return CharacterInfo(
            character_id=character_id,
            character_name=char_data.get('name', ''),
            corporation_id=corp_id,
            corporation_name=corp_name,
            alliance_id=alliance_id,
            alliance_name=alliance_name,
        )

    def refresh_access_token(self, character, refresh_token: str = None) -> TokenResponse:
        """
        Refresh an expired access token using refresh token.

        Args:
            character: The Character model instance
            refresh_token: The refresh token (optional, will get from character if not provided)

        Returns:
            TokenResponse with new access token
        """
        if refresh_token is None:
            refresh_token = character.get_refresh_token()

        if not refresh_token:
            raise ValueError(f"No refresh token available for character {character.id}")

        token_url = getattr(settings, 'EVE_SSO_TOKEN_URL',
                           'https://login.eveonline.com/v2/oauth/token')
        response = requests.post(
            token_url,
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
            },
            auth=(settings.EVE_CLIENT_ID, settings.EVE_CLIENT_SECRET),
            timeout=10,
        )
        response.raise_for_status()
        token_data = response.json()

        # Calculate expiration
        expires_at = None
        if 'expires_in' in token_data:
            expires_at = timezone.now() + timedelta(seconds=token_data['expires_in'])

        return TokenResponse(
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token'),  # May be a new refresh token
            expires_at=expires_at,
        )

    def get_access_token(self, character) -> str:
        """
        Get a valid access token for API calls.

        Handles token refresh if needed.

        Args:
            character: The Character model instance

        Returns:
            A valid access token string
        """
        cache_key = f'access_token:character:{character.id}:esi_sso'

        # Check cache first
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Check if token needs refresh
        if character.needs_token_refresh():
            token_response = self.refresh_access_token(character)

            # Update character with new tokens
            character.set_refresh_token(token_response.refresh_token)
            character.token_expires = token_response.expires_at
            character.save(update_fields=['refresh_token', 'token_expires'])

            access_token = token_response.access_token
        else:
            # Get from character's stored token
            access_token = character.get_access_token()

        # Cache the access token
        if character.token_expires:
            timeout = max(1, int((character.token_expires - timezone.now()).total_seconds() * 0.9))
            cache.set(cache_key, access_token, timeout=timeout)

        return access_token

    def supports_multiple_characters(self) -> bool:
        """ESI SSO requires individual auth per character."""
        return False

    def requires_character_reauth(self) -> bool:
        """Each character needs its own SSO flow."""
        return True
