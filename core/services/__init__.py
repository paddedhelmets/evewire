"""
Core services for evewire.

Includes EVE SSO authentication, ESI client, and token management.
"""

import logging
import requests
from datetime import timedelta
from typing import Optional
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger('evewire')


class TokenManager:
    """Manage EVE SSO OAuth2 tokens."""

    @staticmethod
    def get_access_token(user) -> Optional[str]:
        """Get a valid access token for the user."""
        cache_key = f'access_token:{user.id}'

        cached = cache.get(cache_key)
        if cached:
            return cached

        refresh_token = user.get_refresh_token()
        if not refresh_token:
            logger.warning(f'No refresh token for user {user.id}')
            return None

        try:
            token_data = TokenManager._refresh_token(refresh_token)
            access_token = token_data.get('access_token')

            expires_in = token_data.get('expires_in', 1200)
            cache_timeout = int(expires_in * 0.9)
            cache.set(cache_key, access_token, timeout=cache_timeout)

            user.token_expires = timezone.now() + timedelta(seconds=expires_in)
            user.save(update_fields=['token_expires'])

            return access_token

        except Exception as e:
            logger.error(f'Token refresh failed for user {user.id}: {e}')
            return None

    @staticmethod
    def _refresh_token(refresh_token: str) -> dict:
        """Exchange refresh token for new access token."""
        response = requests.post(
            settings.EVE_SSO_TOKEN_URL,
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
            },
            auth=(settings.EVE_CLIENT_ID, settings.EVE_CLIENT_SECRET),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def exchange_code_for_token(code: str) -> dict:
        """Exchange OAuth authorization code for tokens."""
        response = requests.post(
            settings.EVE_SSO_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': code,
            },
            auth=(settings.EVE_CLIENT_ID, settings.EVE_CLIENT_SECRET),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def verify_character(access_token: str) -> dict:
        """Verify a character's identity using their access token."""
        response = requests.get(
            settings.EVE_SSO_VERIFY_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_sso_login_url(state: Optional[str] = None) -> str:
        """Generate the EVE SSO login URL."""
        from core.models import EveScope

        params = {
            'response_type': 'code',
            'redirect_uri': settings.EVE_CALLBACK_URL,
            'client_id': settings.EVE_CLIENT_ID,
            'scope': ' '.join(EveScope.mvp_scopes()),
        }

        if state:
            params['state'] = state

        import urllib.parse
        return f'{settings.EVE_SSO_LOGIN_URL}?{urllib.parse.urlencode(params)}'


class ESIClient:
    """Client for EVE Swagger Interface (ESI) API."""

    BASE_URL = settings.ESI_BASE_URL
    DEFAULT_DATASOURCE = settings.ESI_DATASOURCE

    @classmethod
    def get(cls, endpoint: str, character, **kwargs) -> dict:
        """Make an authenticated GET request to ESI."""
        access_token = character.get_access_token()
        if not access_token:
            raise ValueError('No access token available')

        url = f'{cls.BASE_URL}{endpoint}'
        params = {'datasource': cls.DEFAULT_DATASOURCE, **kwargs}
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
        }

        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        remaining = response.headers.get('X-Esi-Error-Limit-Remain', 'unknown')
        logger.debug(f'ESI rate limit remaining: {remaining}')

        return response.json()

    @classmethod
    def get_public(cls, endpoint: str, **kwargs) -> dict:
        """Make an unauthenticated GET request to ESI."""
        url = f'{cls.BASE_URL}{endpoint}'
        params = {'datasource': cls.DEFAULT_DATASOURCE, **kwargs}
        headers = {'Accept': 'application/json'}

        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    @classmethod
    def get_character_info(cls, character_id: int) -> dict:
        """Get public character information."""
        return cls.get_public(f'/characters/{character_id}/')

    @classmethod
    def get_character_portrait(cls, character_id: int) -> dict:
        """Get character portrait URLs."""
        return cls.get_public(f'/characters/{character_id}/portrait/')

    @classmethod
    def get_skills(cls, character) -> dict:
        """Get character skills."""
        return cls.get(f'/characters/{character.id}/skills/', character)

    @classmethod
    def get_skill_queue(cls, character) -> list:
        """Get character skill queue."""
        return cls.get(f'/characters/{character.id}/skillqueue/', character)

    @classmethod
    def get_wallet_balance(cls, character) -> float:
        """Get character wallet balance."""
        return cls.get(f'/characters/{character.id}/wallet/', character)

    @classmethod
    def get_assets(cls, character) -> list:
        """Get character assets."""
        return cls.get(f'/characters/{character.id}/assets/', character)

    @classmethod
    def get_orders(cls, character) -> list:
        """Get character market orders."""
        return cls.get(f'/characters/{character.id}/orders/', character)

    @classmethod
    def get_corporation_info(cls, corporation_id: int) -> dict:
        """Get public corporation information."""
        return cls.get_public(f'/corporations/{corporation_id}/')

    @classmethod
    def get_alliance_info(cls, alliance_id: int) -> dict:
        """Get public alliance information."""
        return cls.get_public(f'/alliances/{alliance_id}/')


class AuthService:
    """Service for handling EVE SSO authentication flow."""

    @staticmethod
    def handle_callback(code: str):
        """Handle EVE SSO OAuth callback."""
        from core.models import User, Character, AuditLog

        try:
            token_data = TokenManager.exchange_code_for_token(code)
        except requests.RequestException as e:
            logger.error(f'Token exchange failed: {e}')
            raise ValueError('Failed to exchange authorization code for tokens')

        access_token = token_data.get('access_token')
        try:
            character_data = TokenManager.verify_character(access_token)
        except requests.RequestException as e:
            logger.error(f'Character verification failed: {e}')
            raise ValueError('Failed to verify character identity')

        character_id = character_data['CharacterID']
        character_name = character_data['CharacterName']

        user, created = User.objects.get_or_create(
            eve_character_id=character_id,
            defaults={
                'eve_character_name': character_name,
                'corporation_id': character_data.get('CorporationID'),
            }
        )

        refresh_token = token_data.get('refresh_token')
        if refresh_token:
            user.set_refresh_token(refresh_token)

        expires_in = token_data.get('expires_in', 1200)
        user.token_expires = timezone.now() + timedelta(seconds=expires_in)
        user.last_login = timezone.now()
        user.save()

        Character.objects.get_or_create(id=character_id, defaults={'user': user})

        AuditLog.log(
            user,
            action='login' if not created else 'register',
            character_id=character_id,
            character_name=character_name,
        )

        logger.info(f'User {"created" if created else "logged in"}: {character_name} ({character_id})')
        return user


def sync_character_data(character) -> bool:
    """Sync all character data from ESI."""
    from core.models import SyncStatus

    try:
        character.last_sync_status = SyncStatus.IN_PROGRESS
        character.save(update_fields=['last_sync_status'])

        _sync_skills(character)
        _sync_skill_queue(character)
        _sync_wallet(character)
        _sync_assets(character)
        _sync_orders(character)

        character.last_sync_status = SyncStatus.SUCCESS
        character.last_sync_error = ''
        character.last_sync = timezone.now()
        character.save(update_fields=['last_sync_status', 'last_sync_error', 'last_sync'])

        logger.info(f'Sync completed for character {character.id}')
        return True

    except Exception as e:
        character.last_sync_status = SyncStatus.FAILED
        character.last_sync_error = str(e)[:500]
        character.save(update_fields=['last_sync_status', 'last_sync_error'])

        logger.error(f'Sync failed for character {character.id}: {e}')
        return False


def _sync_skills(character) -> None:
    """Sync character skills from ESI."""
    data = ESIClient.get_skills(character)
    character.skills_data = data
    character.skills_synced_at = timezone.now()
    character.save(update_fields=['skills_data', 'skills_synced_at'])


def _sync_skill_queue(character) -> None:
    """Sync character skill queue from ESI."""
    data = ESIClient.get_skill_queue(character)
    character.skill_queue_data = data
    character.skill_queue_synced_at = timezone.now()
    character.save(update_fields=['skill_queue_data', 'skill_queue_synced_at'])


def _sync_wallet(character) -> None:
    """Sync character wallet balance from ESI."""
    balance = ESIClient.get_wallet_balance(character)
    character.wallet_balance = balance
    character.wallet_synced_at = timezone.now()
    character.save(update_fields=['wallet_balance', 'wallet_synced_at'])


def _sync_assets(character) -> None:
    """Sync character assets from ESI."""
    data = ESIClient.get_assets(character)
    character.assets_data = data
    character.assets_synced_at = timezone.now()
    character.save(update_fields=['assets_data', 'assets_synced_at'])


def _sync_orders(character) -> None:
    """Sync character market orders from ESI."""
    data = ESIClient.get_orders(character)
    character.orders_data = data
    character.orders_synced_at = timezone.now()
    character.save(update_fields=['orders_data', 'orders_synced_at'])
