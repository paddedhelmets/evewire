"""
Core services for evewire.

Includes EVE SSO authentication, ESI client with compatibility date support,
and token management.
"""

import logging
import requests
from datetime import timedelta, datetime
from typing import Optional, Any
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger('evewire')


class ESIMeta:
    """Metadata from ESI response headers."""

    def __init__(self, response: requests.Response):
        self.response = response
        self.remaining_error_limit = int(response.headers.get('X-Esi-Error-Limit-Remain', 0))
        self.error_limit_reset = response.headers.get('X-Esi-Error-Limit-Reset', '')
        self.expires = self._parse_expires()
        self.cache_control = response.headers.get('Cache-Control', '')

    def _parse_expires(self) -> Optional[datetime]:
        """Parse the Expires header into a datetime."""
        expires_str = self.response.headers.get('Expires', '')
        if not expires_str:
            return None
        try:
            # Parse RFC 2822 date format
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(expires_str)
        except Exception:
            logger.warning(f'Failed to parse Expires header: {expires_str}')
            return None

    @property
    def cache_expires_at(self) -> Optional[datetime]:
        """Get the cache expiry timestamp."""
        return self.expires

    @property
    def max_age_seconds(self) -> int:
        """Get the max-age from Cache-Control header."""
        if not self.cache_control:
            return 3600  # Default 1 hour

        for directive in self.cache_control.split(','):
            directive = directive.strip()
            if directive.startswith('max-age='):
                return int(directive.split('=')[1])

        return 3600  # Default 1 hour

    def is_stale(self) -> bool:
        """Check if the cached data would be stale now."""
        if not self.expires:
            return True
        return timezone.now() >= self.expires


class ESIResponse:
    """ESI response with metadata."""

    def __init__(self, data: Any, meta: ESIMeta):
        self.data = data
        self.meta = meta


class TokenManager:
    """Manage EVE SSO OAuth2 tokens."""

    @staticmethod
    def get_access_token(user) -> Optional[str]:
        """Get a valid access token for the user (uses first character)."""
        from core.models import Character
        try:
            character = user.characters.first()
            if character:
                return TokenManager.get_access_token_for_character(character)
        except Exception as e:
            logger.error(f'Failed to get access token for user {user.id}: {e}')
        return None

    @staticmethod
    def get_access_token_for_character(character) -> Optional[str]:
        """Get a valid access token for a specific character."""
        cache_key = f'access_token:character:{character.id}'

        cached = cache.get(cache_key)
        if cached:
            return cached

        refresh_token = character.get_refresh_token()
        if not refresh_token:
            logger.warning(f'No refresh token for character {character.id}')
            return None

        try:
            token_data = TokenManager._refresh_token(refresh_token)
            access_token = token_data.get('access_token')

            expires_in = token_data.get('expires_in', 1200)
            cache_timeout = int(expires_in * 0.9)
            cache.set(cache_key, access_token, timeout=cache_timeout)

            character.token_expires = timezone.now() + timedelta(seconds=expires_in)
            character.save(update_fields=['token_expires'])

            return access_token

        except Exception as e:
            logger.error(f'Token refresh failed for character {character.id}: {e}')
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
        import string
        import secrets

        # Always generate a state if not provided (CSRF protection)
        if not state:
            state = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

        params = {
            'response_type': 'code',
            'redirect_uri': settings.EVE_CALLBACK_URL,
            'client_id': settings.EVE_CLIENT_ID,
            'scope': ' '.join(EveScope.mvp_scopes()),
            'state': state,
        }

        import urllib.parse
        return f'{settings.EVE_SSO_LOGIN_URL}?{urllib.parse.urlencode(params)}'


class ESIClient:
    """
    Client for EVE Swagger Interface (ESI) API.

    Supports compatibility date versioning and returns response metadata
    for cache-aware syncing.
    """

    BASE_URL = settings.ESI_BASE_URL
    DEFAULT_DATASOURCE = settings.ESI_DATASOURCE
    COMPATIBILITY_DATE = settings.ESI_COMPATIBILITY_DATE

    @classmethod
    def _get_headers(cls, access_token: str = None) -> dict:
        """Build request headers with compatibility date."""
        headers = {
            'Accept': 'application/json',
            'X-Compatibility-Date': cls.COMPATIBILITY_DATE,
        }

        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'

        return headers

    @classmethod
    def get(cls, endpoint: str, character, **kwargs) -> ESIResponse:
        """Make an authenticated GET request to ESI."""
        access_token = character.get_access_token()
        if not access_token:
            raise ValueError('No access token available')

        url = f'{cls.BASE_URL}{endpoint}'
        params = {'datasource': cls.DEFAULT_DATASOURCE, **kwargs}
        headers = cls._get_headers(access_token)

        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        meta = ESIMeta(response)
        data = response.json()

        logger.debug(f'ESI GET {endpoint}: rate limit remaining={meta.remaining_error_limit}')

        return ESIResponse(data, meta)

    @classmethod
    def get_public(cls, endpoint: str, **kwargs) -> ESIResponse:
        """Make an unauthenticated GET request to ESI."""
        url = f'{cls.BASE_URL}{endpoint}'
        params = {'datasource': cls.DEFAULT_DATASOURCE, **kwargs}
        headers = cls._get_headers()

        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        meta = ESIMeta(response)
        data = response.json()

        return ESIResponse(data, meta)

    # Character endpoints

    @classmethod
    def get_character_info(cls, character_id: int) -> ESIResponse:
        """Get public character information."""
        return cls.get_public(f'/characters/{character_id}/')

    @classmethod
    def get_character_portrait(cls, character_id: int) -> ESIResponse:
        """Get character portrait URLs."""
        return cls.get_public(f'/characters/{character_id}/portrait/')

    @classmethod
    def get_location(cls, character) -> ESIResponse:
        """Get character's current location.

        ESI Endpoint: GET /characters/{character_id}/location/
        Scope: esi-location.read_location.v1

        Returns location data with solar_system_id and optionally station_id or structure_id.
        """
        return cls.get(f'/characters/{character.id}/location/', character)

    @classmethod
    def get_skills(cls, character) -> ESIResponse:
        """Get character skills."""
        return cls.get(f'/characters/{character.id}/skills/', character)

    @classmethod
    def get_skill_queue(cls, character) -> ESIResponse:
        """Get character skill queue."""
        return cls.get(f'/characters/{character.id}/skillqueue/', character)

    @classmethod
    def get_attributes(cls, character) -> ESIResponse:
        """Get character attributes."""
        return cls.get(f'/characters/{character.id}/attributes/', character)

    @classmethod
    def get_implants(cls, character) -> ESIResponse:
        """Get character implants."""
        return cls.get(f'/characters/{character.id}/implants/', character)

    @classmethod
    def get_wallet_balance(cls, character) -> ESIResponse:
        """Get character wallet balance."""
        return cls.get(f'/characters/{character.id}/wallet/', character)

    @classmethod
    def get_assets(cls, character, page: int = 1) -> ESIResponse:
        """Get character assets."""
        return cls.get(f'/characters/{character.id}/assets/', character, page=page)

    @classmethod
    def get_orders(cls, character, page: int = 1) -> ESIResponse:
        """Get character market orders."""
        return cls.get(f'/characters/{character.id}/orders/', character, page=page)

    @classmethod
    def get_orders_history(cls, character, page: int = 1) -> ESIResponse:
        """Get character market order history (closed/expired/cancelled orders)."""
        return cls.get(f'/characters/{character.id}/orders/history/', character, page=page)

    @classmethod
    def get_wallet_journal(cls, character, page: int = 1) -> ESIResponse:
        """Get character wallet journal."""
        return cls.get(f'/characters/{character.id}/wallet/journal/', character, page=page)

    @classmethod
    def get_wallet_transactions(cls, character, page: int = 1) -> ESIResponse:
        """Get character wallet transactions."""
        return cls.get(f'/characters/{character.id}/wallet/transactions/', character, page=page)

    @classmethod
    def get_industry_jobs(cls, character, page: int = 1) -> ESIResponse:
        """Get character industry jobs."""
        return cls.get(f'/characters/{character.id}/industry/jobs/', character, page=page)

    @classmethod
    def get_contracts(cls, character, page: int = 1) -> ESIResponse:
        """Get character contracts."""
        return cls.get(f'/characters/{character.id}/contracts/', character, page=page)

    @classmethod
    def get_contract_items(cls, character, contract_id: int) -> ESIResponse:
        """Get items in a specific contract."""
        return cls.get(f'/characters/{character.id}/contracts/{contract_id}/items/', character)

    # Public reference endpoints

    @classmethod
    def get_corporation_info(cls, corporation_id: int) -> ESIResponse:
        """Get public corporation information."""
        return cls.get_public(f'/corporations/{corporation_id}/')

    @classmethod
    def get_alliance_info(cls, alliance_id: int) -> ESIResponse:
        """Get public alliance information."""
        return cls.get_public(f'/alliances/{alliance_id}/')

    @classmethod
    def get_solar_system_info(cls, system_id: int) -> ESIResponse:
        """Get solar system information."""
        return cls.get_public(f'/universe/systems/{system_id}/')

    @classmethod
    def get_station_info(cls, station_id: int) -> ESIResponse:
        """Get station information."""
        return cls.get_public(f'/universe/stations/{station_id}/')

    @classmethod
    def get_type_info(cls, type_id: int) -> ESIResponse:
        """Get item type information."""
        return cls.get_public(f'/universe/types/{type_id}/')


class AuthService:
    """Service for handling EVE SSO authentication flow."""

    # Return status codes for handle_callback
    SUCCESS = 'success'
    ACCOUNT_CLAIM_REQUIRED = 'account_claim_required'
    SUCCESS_WITH_WARNING = 'success_with_warning'
    NEW_USER = 'new_user'

    @staticmethod
    @transaction.atomic
    def handle_callback(code: str, request_user=None, reauth_char_id=None, request=None):
        """
        Handle EVE SSO OAuth callback.

        If request_user is provided (user already logged in), adds the character
        to their existing account. Otherwise, creates a new user or logs in
        to existing user with that character.

        If reauth_char_id is provided, this is a re-authentication flow to fix
        broken tokens/scopes. Only updates that specific character.
        """
        from core.models import User, Character, AuditLog, SyncStatus

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
        corporation_id = character_data.get('CorporationID')
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in', 1200)

        # Check if this character already exists
        existing_character = Character.objects.filter(id=character_id).first()

        user = None
        created = False
        character_added = False

        if reauth_char_id:
            # Re-authentication flow - verify character matches
            if character_id != reauth_char_id:
                raise ValueError(f'Character mismatch: expected {reauth_char_id}, got {character_id}')

            if not existing_character:
                raise ValueError(f'Character {character_id} not found')

            # Verify the logged-in user owns this character
            if request_user and existing_character.user != request_user:
                raise ValueError('You do not own this character')

            # Update the character's token and reset sync status
            existing_character.set_refresh_token(refresh_token)
            existing_character.token_expires = timezone.now() + timedelta(seconds=expires_in)
            existing_character.character_name = character_name
            existing_character.corporation_id = corporation_id
            existing_character.last_sync_status = SyncStatus.PENDING
            existing_character.last_sync_error = ''
            existing_character.save()
            character = existing_character
            user = existing_character.user

            # Fetch corporation/alliance names from ESI
            update_character_corporation_info(character)

            logger.info(f'Re-authenticated character {character_id}')

        elif request_user:
            # User is already logged in - add character to their account
            user = request_user

            if existing_character and existing_character.user != user:
                # Character belongs to another user - not allowed
                raise ValueError(f'This character is already linked to another account')

            if existing_character:
                # Update existing character's token
                existing_character.set_refresh_token(refresh_token)
                existing_character.token_expires = timezone.now() + timedelta(seconds=expires_in)
                existing_character.character_name = character_name
                existing_character.corporation_id = corporation_id
                existing_character.save()
                character = existing_character

                # Fetch corporation/alliance names from ESI
                update_character_corporation_info(character)
            else:
                # Create new character for this user (use get_or_create for race condition safety)
                character, char_created = Character.objects.get_or_create(
                    id=character_id,
                    defaults={
                        'user': user,
                        'character_name': character_name,
                        'corporation_id': corporation_id,
                    }
                )
                character.set_refresh_token(refresh_token)
                character.token_expires = timezone.now() + timedelta(seconds=expires_in)
                character.save()
                if char_created:
                    character_added = True

                # Fetch corporation/alliance names from ESI
                update_character_corporation_info(character)

        else:
            # Not logged in - this is initial login
            if existing_character:
                # Character already exists - check for account claiming
                user = existing_character.user
                # Update token
                existing_character.set_refresh_token(refresh_token)
                existing_character.token_expires = timezone.now() + timedelta(seconds=expires_in)
                existing_character.character_name = character_name
                existing_character.corporation_id = corporation_id
                existing_character.save()
                character = existing_character
                created = False

                # Fetch corporation/alliance names from ESI
                update_character_corporation_info(character)

                # Check if account has email for account recovery
                if user.email and user.email_verified:
                    # Store claiming flow in session for UI to handle
                    if request:
                        request.session['found_account_user_id'] = str(user.id)
                        request.session['pending_character_data'] = {
                            'id': character_id,
                            'name': character_name,
                            'corporation_id': corporation_id,
                            'token': refresh_token,
                            'expires_in': expires_in,
                        }
                    # Return special status to trigger claiming UI
                    return AuthService.ACCOUNT_CLAIM_REQUIRED, user
                else:
                    # No email - log in but warn user about ephemeral account
                    # This is SUCCESS_WITH_WARNING to show warning banner
                    return AuthService.SUCCESS_WITH_WARNING, user
            else:
                # Create new user with this character
                user = User(username=User.objects.generate_username())
                user.last_login = timezone.now()
                user.save()

                # Create character (use get_or_create for race condition safety)
                character, char_created = Character.objects.get_or_create(
                    id=character_id,
                    defaults={
                        'user': user,
                        'character_name': character_name,
                        'corporation_id': corporation_id,
                    }
                )
                character.set_refresh_token(refresh_token)
                character.token_expires = timezone.now() + timedelta(seconds=expires_in)
                character.save()

                # Fetch corporation/alliance names from ESI
                update_character_corporation_info(character)

                # Update user's first character fields for backward compatibility
                user.eve_character_id = character_id
                user.eve_character_name = character_name
                user.corporation_id = corporation_id
                user.corporation_name = character.corporation_name
                user.alliance_id = character.alliance_id
                user.alliance_name = character.alliance_name
                user.save()
                created = True

                # Return NEW_USER status to show email prompt
                return AuthService.NEW_USER, user

        # Log the action
        if character_added:
            action = 'character_added'
        elif created:
            action = 'register'
        else:
            action = 'login'

        AuditLog.log(
            user,
            action=action,
            character_id=character_id,
            character_name=character_name,
        )

        logger.info(f'User action: {action} - {character_name} ({character_id})')
        return AuthService.SUCCESS, user


def update_character_corporation_info(character) -> bool:
    """
    Update character's corporation and alliance names from ESI.

    Fetches public corporation and alliance information to populate the
    corporation_name and alliance_name fields. Called during authentication
    and sync to keep names current.

    Args:
        character: Character instance with corporation_id set

    Returns:
        True if successful, False otherwise
    """
    if not character.corporation_id:
        return False

    try:
        # Fetch corporation info
        corp_response = ESIClient.get_corporation_info(character.corporation_id)
        corp_data = corp_response.data

        corporation_name = corp_data.get('name', '')
        alliance_id = corp_data.get('alliance_id')

        # Fetch alliance info if applicable
        alliance_name = ''
        if alliance_id:
            try:
                alliance_response = ESIClient.get_alliance_info(alliance_id)
                alliance_data = alliance_response.data
                alliance_name = alliance_data.get('name', '')
            except Exception as e:
                logger.warning(f'Failed to fetch alliance {alliance_id} info: {e}')

        # Update character
        character.corporation_name = corporation_name
        character.alliance_id = alliance_id
        character.alliance_name = alliance_name
        character.save(update_fields=['corporation_name', 'alliance_id', 'alliance_name'])

        logger.debug(f'Updated corp info for {character.character_name}: {corporation_name}, {alliance_name or "No alliance"}')
        return True

    except Exception as e:
        logger.warning(f'Failed to fetch corporation {character.corporation_id} info: {e}')
        return False


# Sync functions for character data

def sync_character_data(character) -> bool:
    """Sync all character data from ESI.

    Args:
        character: Character object (will be refreshed from DB to avoid stale data)
    """
    from core.models import SyncStatus, Character
    from requests.exceptions import HTTPError

    # Refresh character from database to avoid issues with serialized objects
    character = Character.objects.get(id=character.id)

    try:
        character.last_sync_status = SyncStatus.IN_PROGRESS
        character.save(update_fields=['last_sync_status'])

        # First, fetch and update basic character info (corporation_id may have changed)
        char_info_response = ESIClient.get_character_info(character.id)
        char_info = char_info_response.data
        character.corporation_id = char_info.get('corporation_id')
        character.save(update_fields=['corporation_id'])

        _sync_skills(character)
        _sync_skill_queue(character)
        _sync_attributes(character)
        _sync_implants(character)

        # Location might fail with 401 if scope not granted - handle gracefully
        try:
            _sync_location(character)
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                logger.warning(f'Location not available for character {character.id} (missing scope)')
            else:
                raise

        _sync_wallet(character)
        _sync_assets(character)
        _sync_orders(character)
        _sync_orders_history(character)
        _sync_industry_jobs(character)

        # Contracts might fail with 401 if scope not granted - handle gracefully
        try:
            _sync_contracts(character)
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                logger.warning(f'Contracts not available for character {character.id} (missing scope)')
            else:
                raise

        # Update corporation/alliance names (can change over time)
        update_character_corporation_info(character)

        character.last_sync_status = SyncStatus.SUCCESS
        character.last_sync_error = ''
        character.last_sync = timezone.now()
        character.save(update_fields=['last_sync_status', 'last_sync_error', 'last_sync'])

        logger.info(f'Sync completed for character {character.id}')
        return True

    except HTTPError as e:
        # Check for 401 Unauthorized - indicates invalid/missing scopes or broken refresh token
        if e.response is not None and e.response.status_code == 401:
            character.last_sync_status = SyncStatus.NEEDS_REAUTH
            character.last_sync_error = 'Authentication failed. Please re-authorize this character through EVE SSO.'
            character.save(update_fields=['last_sync_status', 'last_sync_error'])
            logger.warning(f'Character {character.id} needs re-authentication: {e}')
        else:
            character.last_sync_status = SyncStatus.FAILED
            character.last_sync_error = str(e)[:500]
            character.save(update_fields=['last_sync_status', 'last_sync_error'])
            logger.error(f'Sync failed for character {character.id}: {e}')
        return False
    except Exception as e:
        character.last_sync_status = SyncStatus.FAILED
        character.last_sync_error = str(e)[:500]
        character.save(update_fields=['last_sync_status', 'last_sync_error'])

        import traceback
        logger.error(f'Sync failed for character {character.id}: {e}\n{traceback.format_exc()}')
        return False


def _sync_skills(character) -> None:
    """Sync character skills from ESI."""
    from core.character.models import CharacterSkill

    response = ESIClient.get_skills(character)
    skills_data = response.data

    # Update total SP cache
    character.total_sp = skills_data.get('total_sp', 0)
    character.skills_synced_at = timezone.now()
    character.save(update_fields=['total_sp', 'skills_synced_at'])

    # Update individual skills
    for skill_info in skills_data.get('skills', []):
        CharacterSkill.objects.update_or_create(
            character=character,
            skill_id=skill_info['skill_id'],
            defaults={
                'skill_level': skill_info['trained_skill_level'],
                'skillpoints_in_skill': skill_info['skillpoints_in_skill'],
                'trained_skill_level': skill_info['trained_skill_level'],
            }
        )


def _sync_skill_queue(character) -> None:
    """Sync character skill queue from ESI."""
    from core.character.models import SkillQueueItem

    response = ESIClient.get_skill_queue(character)
    queue_data = response.data

    # Clear old queue
    SkillQueueItem.objects.filter(character=character).delete()

    # Insert new queue items
    for i, queue_item in enumerate(queue_data):
        SkillQueueItem.objects.create(
            character=character,
            queue_position=i,
            skill_id=queue_item['skill_id'],
            finish_level=queue_item['finished_level'],
            level_start_sp=queue_item.get('level_start_sp', 0),
            level_end_sp=queue_item.get('level_end_sp', 0),
            training_start_time=queue_item.get('start_date'),
            finish_date=queue_item.get('finish_date'),
        )


def _sync_attributes(character) -> None:
    """Sync character attributes from ESI."""
    from core.character.models import CharacterAttributes

    response = ESIClient.get_attributes(character)
    attrs_data = response.data

    CharacterAttributes.objects.update_or_create(
        character=character,
        defaults={
            'intelligence': attrs_data.get('intelligence', 20),
            'perception': attrs_data.get('perception', 20),
            'charisma': attrs_data.get('charisma', 20),
            'willpower': attrs_data.get('willpower', 20),
            'memory': attrs_data.get('memory', 20),
            'bonus_remap_available': attrs_data.get('bonus_remaps', 0),
        }
    )


def _sync_implants(character) -> None:
    """Sync character implants from ESI."""
    from core.character.models import CharacterImplant

    response = ESIClient.get_implants(character)
    implants_data = response.data

    # Clear old implants
    CharacterImplant.objects.filter(character=character).delete()

    # Insert new implants
    for implant_type_id in implants_data:
        CharacterImplant.objects.create(
            character=character,
            type_id=implant_type_id,
        )


def _sync_wallet(character) -> None:
    """Sync character wallet data from ESI (balance, journal, transactions)."""
    # Sync balance
    response = ESIClient.get_wallet_balance(character)
    balance = response.data

    character.wallet_balance = balance
    character.wallet_synced_at = timezone.now()
    character.save(update_fields=['wallet_balance', 'wallet_synced_at'])

    # Sync journal with fromID walking
    _sync_wallet_journal(character)

    # Sync transactions with fromID walking
    _sync_wallet_transactions(character)


def _sync_location(character) -> None:
    """Sync character location from ESI.

    ESI Endpoint: GET /characters/{character_id}/location/
    Scope: esi-location.read_location.v1

    Returns solar_system_id and optionally station_id or structure_id.
    """
    from core.eve.models import SolarSystem

    response = ESIClient.get_location(character)
    location_data = response.data

    character.solar_system_id = location_data.get('solar_system_id')
    character.station_id = location_data.get('station_id')
    character.structure_id = location_data.get('structure_id')
    character.location_synced_at = timezone.now()
    character.save(update_fields=['solar_system_id', 'station_id', 'structure_id', 'location_synced_at'])


def _sync_wallet_journal(character) -> None:
    """
    Sync character wallet journal from ESI with fromID walking.

    ESI pagination pattern:
    - First request: no from_id parameter (returns newest entries)
    - Subsequent requests: from_id = entry_id - 1 of the oldest entry from previous page
    - Max entries per page: 2560
    - Stop when we get entries we already have
    """
    from core.character.models import WalletJournalEntry

    # Get the oldest entry_id we already have (for duplicate detection)
    oldest_existing = WalletJournalEntry.objects.filter(
        character=character
    ).order_by('entry_id').first()

    # Track entries we've seen to avoid duplicates within this sync
    seen_entry_ids = set()
    entries_to_create = []

    from_id = None
    total_fetched = 0
    max_pages = 100  # Safety limit to prevent infinite loops

    for page_num in range(max_pages):
        params = {}
        if from_id is not None:
            params['from_id'] = from_id

        try:
            response = ESIClient.get(
                f'/characters/{character.id}/wallet/journal/',
                character,
                **params
            )
        except Exception as e:
            logger.error(f'Failed to fetch wallet journal page {page_num} for character {character.id}: {e}')
            break

        entries = response.data
        if not entries:
            break

        # Process entries
        page_new_entries = 0
        for entry_data in entries:
            entry_id = entry_data['id']

            # Skip if we've already seen this entry (duplicate within sync)
            if entry_id in seen_entry_ids:
                continue

            # Skip if we already have this entry in database (from previous sync)
            if oldest_existing and entry_id <= oldest_existing.entry_id:
                continue

            seen_entry_ids.add(entry_id)
            page_new_entries += 1

            entries_to_create.append(entry_data)

        # Update from_id for next page (walk backward)
        # ESI returns entries sorted by date descending (newest first)
        # To get older entries, use from_id = oldest_entry_id - 1
        oldest_entry_id = min(e['id'] for e in entries)
        from_id = oldest_entry_id - 1

        total_fetched += len(entries)

        # Stop if we didn't get any new entries on this page
        if page_new_entries == 0:
            logger.info(f'Wallet journal sync for character {character.id}: no new entries on page {page_num}, stopping')
            break

        # ESI returns empty list when we've reached the beginning
        if len(entries) < 10:  # Heuristic: last page typically has few entries
            # Continue one more time to be sure, but we're likely at the end
            pass

    # Create all new entries
    if entries_to_create:
        created = 0
        for entry_data in entries_to_create:
            try:
                WalletJournalEntry.objects.create(
                    character=character,
                    entry_id=entry_data['id'],
                    amount=entry_data.get('amount', 0),
                    balance=entry_data.get('balance', 0),
                    date=entry_data.get('date'),
                    description=entry_data.get('description', ''),
                    first_party_id=entry_data.get('first_party_id'),
                    reason=entry_data.get('reason', ''),
                    ref_type=entry_data.get('ref_type', ''),
                    tax=entry_data.get('tax'),
                    tax_receiver_id=entry_data.get('tax_receiver_id'),
                )
                created += 1
            except Exception as e:
                # Handle duplicate entry_id errors
                logger.debug(f'Skipping duplicate journal entry {entry_data.get("id")}: {e}')

        logger.info(f'Wallet journal sync for character {character.id}: created {created} entries across {total_fetched} fetched')


def _sync_wallet_transactions(character) -> None:
    """
    Sync character wallet transactions from ESI with fromID walking.

    ESI pagination pattern:
    - First request: no from_id parameter (returns newest transactions)
    - Subsequent requests: from_id = transaction_id - 1 of the oldest transaction from previous page
    - Max entries per page: 2560
    - Stop when we get transactions we already have
    """
    from core.character.models import WalletTransaction

    # Get the oldest transaction_id we already have
    oldest_existing = WalletTransaction.objects.filter(
        character=character
    ).order_by('transaction_id').first()

    # Track transactions we've seen
    seen_transaction_ids = set()
    transactions_to_create = []

    from_id = None
    total_fetched = 0
    max_pages = 100

    for page_num in range(max_pages):
        params = {}
        if from_id is not None:
            params['from_id'] = from_id

        try:
            response = ESIClient.get(
                f'/characters/{character.id}/wallet/transactions/',
                character,
                **params
            )
        except Exception as e:
            logger.error(f'Failed to fetch wallet transactions page {page_num} for character {character.id}: {e}')
            break

        transactions = response.data
        if not transactions:
            break

        # Process transactions
        page_new_transactions = 0
        for tx_data in transactions:
            transaction_id = tx_data['transaction_id']

            if transaction_id in seen_transaction_ids:
                continue

            if oldest_existing and transaction_id <= oldest_existing.transaction_id:
                continue

            seen_transaction_ids.add(transaction_id)
            page_new_transactions += 1

            transactions_to_create.append(tx_data)

        # Update from_id for next page
        oldest_transaction_id = min(t['transaction_id'] for t in transactions)
        from_id = oldest_transaction_id - 1

        total_fetched += len(transactions)

        # Stop if no new entries
        if page_new_transactions == 0:
            logger.info(f'Wallet transactions sync for character {character.id}: no new transactions on page {page_num}, stopping')
            break

        if len(transactions) < 10:
            pass

    # Create all new transactions
    if transactions_to_create:
        created = 0
        for tx_data in transactions_to_create:
            try:
                WalletTransaction.objects.create(
                    character=character,
                    transaction_id=tx_data['transaction_id'],
                    date=tx_data.get('date'),
                    is_buy=tx_data.get('is_buy', True),
                    is_personal=tx_data.get('is_personal', False),
                    journal_ref_id=tx_data.get('journal_ref_id'),
                    location_id=tx_data.get('location_id'),
                    quantity=tx_data.get('quantity', 0),
                    type_id=tx_data.get('type_id'),
                    unit_price=tx_data.get('unit_price', 0),
                )
                created += 1
            except Exception as e:
                logger.debug(f'Skipping duplicate transaction {tx_data.get("transaction_id")}: {e}')

        logger.info(f'Wallet transactions sync for character {character.id}: created {created} transactions across {total_fetched} fetched')



def _sync_assets(character) -> None:
    """Sync character assets from ESI."""
    from core.character.models import CharacterAsset

    # Fetch all pages of assets
    all_assets_data = []
    page = 1

    while True:
        response = ESIClient.get_assets(character, page=page)
        assets_data = response.data

        if not assets_data:
            break

        all_assets_data.extend(assets_data)

        # ESI returns empty array when no more pages
        if len(assets_data) < 1000:
            break

        page += 1

    logger.info(f'Fetched {len(all_assets_data)} assets across {page} pages for character {character.id}')

    # Delete old assets
    CharacterAsset.objects.filter(character=character).delete()

    # Build asset tree
    # ESI returns flat list with parent relationship via is_singleton/item_id
    # We need to build the MPTT tree
    assets_by_id = {item['item_id']: item for item in all_assets_data}

    # First pass: create all assets without parent
    for item_data in all_assets_data:
        CharacterAsset.objects.create(
            character=character,
            item_id=item_data['item_id'],
            type_id=item_data['type_id'],
            quantity=item_data.get('quantity', 1),
            location_id=item_data.get('location_id'),
            location_type=item_data.get('location_type', ''),
            location_flag=item_data.get('location_flag', ''),
            is_singleton=item_data.get('is_singleton', False),
            is_blueprint_copy=item_data.get('is_blueprint_copy', False),
        )

    # Second pass: set parent relationships
    for item_data in all_assets_data:
        item_id = item_data['item_id']
        # Check if this item has a location_id that points to another item
        # (items inside containers/ships have location_id = parent item_id)
        location_id = item_data.get('location_id')
        location_type = item_data.get('location_type')

        if location_type == 'item' and location_id in assets_by_id:
            # This item is inside another item (container, ship, etc.)
            try:
                asset = CharacterAsset.objects.get(item_id=item_id)
                parent = CharacterAsset.objects.get(item_id=location_id)
                asset.parent = parent
                asset.save(update_fields=['parent'])
            except CharacterAsset.DoesNotExist:
                pass

    # Queue structure refresh jobs for any unknown structure location_ids
    # This handles citadels/structures that are corp-owned but contain character assets
    _queue_structure_refreshes(character, assets_by_id)

    character.assets_synced_at = timezone.now()
    character.save(update_fields=['assets_synced_at'])


def _queue_structure_refreshes(character, assets_by_id: dict) -> None:
    """
    Queue structure refresh tasks for unknown structure location_ids.

    When assets have location_type='structure' or location_type='item' with
    a location_id that's not in our asset list, those IDs likely point to
    player-owned structures (citadels, starbases, etc.) that are corp-owned
    but contain character assets.

    This function queues background tasks to fetch and create those structures.
    """
    from core.character.models import CharacterAsset
    from core.eve.models import Structure, Station
    from django_q.tasks import async_task

    # Collect all unique location_ids from assets that might be structures
    potential_structure_ids = set()

    for item_data in assets_by_id.values():
        location_id = item_data.get('location_id')
        location_type = item_data.get('location_type')

        if not location_id:
            continue

        # location_type='structure' is definitely a structure
        if location_type == 'structure':
            potential_structure_ids.add(location_id)
        # location_type='item' with location_id not in assets_by_id might be a structure
        elif location_type == 'item' and location_id not in assets_by_id:
            potential_structure_ids.add(location_id)

    if not potential_structure_ids:
        return

    # Filter out IDs we already have as structures or stations
    existing_structure_ids = set(Structure.objects.filter(
        structure_id__in=potential_structure_ids
    ).values_list('structure_id', flat=True))

    existing_station_ids = set(Station.objects.filter(
        id__in=potential_structure_ids
    ).values_list('id', flat=True))

    # Also filter out structures already marked as inaccessible (no docking access)
    inaccessible_structure_ids = set(Structure.objects.filter(
        structure_id__in=potential_structure_ids,
        last_sync_status='inaccessible'
    ).values_list('structure_id', flat=True))

    # IDs that need to be fetched
    new_structure_ids = potential_structure_ids - existing_structure_ids - existing_station_ids - inaccessible_structure_ids

    if new_structure_ids:
        logger.info(f'Queueing {len(new_structure_ids)} structure refresh tasks for character {character.id}')
        for structure_id in new_structure_ids:
            async_task('core.eve.tasks.refresh_structure', structure_id)


def _sync_orders(character) -> None:
    """
    Sync character market orders from ESI.

    Handles:
    - Pagination across multiple pages
    - State transitions with logging
    - Order state transitions (open -> closed/expired/cancelled)
    """
    from core.character.models import MarketOrder

    # Fetch all pages of orders
    all_orders_data = []
    page = 1

    while True:
        response = ESIClient.get_orders(character, page=page)
        orders_data = response.data

        if not orders_data:
            break

        all_orders_data.extend(orders_data)

        # ESI returns empty array when no more pages
        if len(orders_data) < 1000:
            break

        page += 1

    # Get existing orders for this character
    existing_orders = {
        order.order_id: order
        for order in MarketOrder.objects.filter(character=character)
    }
    existing_order_ids = set(existing_orders.keys())
    incoming_order_ids = {order['order_id'] for order in all_orders_data}

    # Track seen order IDs
    seen_order_ids = set()

    # Process incoming orders
    for order_data in all_orders_data:
        order_id = order_data['order_id']
        seen_order_ids.add(order_id)
        new_state = order_data.get('state', 'unknown')

        # Check if this is an existing order with state change
        if order_id in existing_orders:
            existing_order = existing_orders[order_id]
            old_state = existing_order.state

            # Log state change
            if old_state != new_state:
                logger.info(
                    f'Market order {order_id} state change: '
                    f'{old_state} -> {new_state} '
                    f'(character: {character.id})'
                )

            # Update order data
            for field, value in {
                'is_buy_order': order_data.get('is_buy_order', False),
                'type_id': order_data['type_id'],
                'region_id': order_data.get('region_id'),
                'station_id': order_data.get('station_id'),
                'system_id': order_data.get('system_id'),
                'volume_remain': order_data.get('volume_remain', 0),
                'volume_total': order_data.get('volume_total', 0),
                'min_volume': order_data.get('min_volume', 1),
                'price': order_data.get('price', 0),
                'issued': order_data.get('issued'),
                'duration': order_data.get('duration', 0),
                'range': order_data.get('range', ''),
                'state': new_state,
                'escrow': order_data.get('escrow', 0),
            }.items():
                setattr(existing_order, field, value)

            existing_order.save()
        else:
            # Create new order
            MarketOrder.objects.create(
                character=character,
                order_id=order_id,
                is_buy_order=order_data.get('is_buy_order', False),
                type_id=order_data['type_id'],
                region_id=order_data.get('region_id'),
                station_id=order_data.get('station_id'),
                system_id=order_data.get('system_id'),
                volume_remain=order_data.get('volume_remain', 0),
                volume_total=order_data.get('volume_total', 0),
                min_volume=order_data.get('min_volume', 1),
                price=order_data.get('price', 0),
                issued=order_data.get('issued'),
                duration=order_data.get('duration', 0),
                range=order_data.get('range', ''),
                state=new_state,
                escrow=order_data.get('escrow', 0),
            )

    # Orders not seen in this sync are no longer active (deleted/closed)
    # Keep them in DB but they won't appear in active queries
    deleted_order_ids = existing_order_ids - seen_order_ids
    if deleted_order_ids:
        logger.debug(
            f'{len(deleted_order_ids)} market orders no longer active '
            f'(character: {character.id})'
        )
        # Optionally update state of these orders to 'closed'
        MarketOrder.objects.filter(
            character=character,
            order_id__in=deleted_order_ids,
            state='open'
        ).update(state='closed')

    character.orders_synced_at = timezone.now()
    character.save(update_fields=['orders_synced_at'])


def _sync_orders_history(character) -> None:
    """
    Sync character market order history from ESI.

    Handles:
    - Pagination across multiple pages
    - Closed, expired, and cancelled orders
    - Historical data (up to 1 year retention)
    """
    from core.character.models import MarketOrderHistory

    # Fetch all pages of order history
    all_orders_data = []
    page = 1

    while True:
        response = ESIClient.get_orders_history(character, page=page)
        orders_data = response.data

        if not orders_data:
            break

        all_orders_data.extend(orders_data)

        # ESI returns empty array when no more pages
        if len(orders_data) < 1000:
            break

        page += 1

    # Get existing order history for this character
    existing_orders = {
        order.order_id: order
        for order in MarketOrderHistory.objects.filter(character=character)
    }
    existing_order_ids = set(existing_orders.keys())
    incoming_order_ids = {order['order_id'] for order in all_orders_data}

    # Process incoming orders
    for order_data in all_orders_data:
        order_id = order_data['order_id']

        # Check if this is an existing order
        if order_id in existing_orders:
            # Skip - history doesn't change
            continue
        else:
            # Create new historical order
            MarketOrderHistory.objects.create(
                character=character,
                order_id=order_id,
                is_buy_order=order_data.get('is_buy_order', False),
                type_id=order_data['type_id'],
                region_id=order_data.get('region_id'),
                station_id=order_data.get('station_id'),
                system_id=order_data.get('system_id'),
                volume_remain=order_data.get('volume_remain', 0),
                volume_total=order_data.get('volume_total', 0),
                min_volume=order_data.get('min_volume', 1),
                price=order_data.get('price', 0),
                issued=order_data.get('issued'),
                duration=order_data.get('duration', 0),
                range=order_data.get('range', ''),
                state=order_data.get('state', 'unknown'),
                escrow=order_data.get('escrow', 0),
            )

    logger.debug(
        f'Synced {len(all_orders_data)} historical orders '
        f'(character: {character.id})'
    )


def _sync_industry_jobs(character) -> None:
    """
    Sync character industry jobs from ESI.

    Handles:
    - Pagination across multiple pages
    - State transitions with logging
    - Stale job handling (jobs past end_date + 90 days marked as unknown)
    - Blueprint lookup error handling
    """
    from core.character.models import IndustryJob

    # Fetch all pages of jobs
    all_jobs_data = []
    page = 1

    while True:
        response = ESIClient.get_industry_jobs(character, page=page)
        jobs_data = response.data

        if not jobs_data:
            break

        all_jobs_data.extend(jobs_data)

        # ESI returns empty array when no more pages
        if len(jobs_data) < 1000:  # ESI max page size is typically 1000
            break

        page += 1

    # Get existing jobs for this character
    existing_jobs = {
        job.job_id: job
        for job in IndustryJob.objects.filter(character=character)
    }
    existing_job_ids = set(existing_jobs.keys())
    incoming_job_ids = {job['job_id'] for job in all_jobs_data}

    # Track seen job IDs for stale job handling
    seen_job_ids = set()

    # Process incoming jobs
    for job_data in all_jobs_data:
        job_id = job_data['job_id']
        seen_job_ids.add(job_id)
        new_status = job_data.get('status', 999)

        # Check if this is an existing job with status change
        if job_id in existing_jobs:
            existing_job = existing_jobs[job_id]
            old_status = existing_job.status

            # Update if status changed
            if old_status != new_status:
                logger.info(
                    f'Industry job {job_id} status change: '
                    f'{old_status} -> {new_status} '
                    f'(character: {character.id})'
                )

            # Update job data
            for field, value in {
                'activity_id': job_data.get('activity_id'),
                'status': new_status,
                'blueprint_id': job_data.get('blueprint_id'),
                'blueprint_type_id': job_data.get('blueprint_type_id'),
                'blueprint_location_id': job_data.get('blueprint_location_id'),
                'product_type_id': job_data.get('product_type_id'),
                'station_id': job_data.get('station_id'),
                'solar_system_id': job_data.get('solar_system_id'),
                'start_date': job_data.get('start_date'),
                'end_date': job_data.get('end_date'),
                'pause_date': job_data.get('pause_date'),
                'completed_date': job_data.get('completed_date'),
                'completed_character_id': job_data.get('completed_character_id'),
                'runs': job_data.get('runs', 1),
                'cost': job_data.get('cost', 0),
                'probability': job_data.get('probability'),
                'attempts': job_data.get('attempts'),
                'success': job_data.get('success'),
            }.items():
                setattr(existing_job, field, value)

            existing_job.save()
        else:
            # Create new job
            IndustryJob.objects.create(
                character=character,
                job_id=job_id,
                activity_id=job_data.get('activity_id'),
                status=new_status,
                blueprint_id=job_data.get('blueprint_id'),
                blueprint_type_id=job_data.get('blueprint_type_id'),
                blueprint_location_id=job_data.get('blueprint_location_id'),
                product_type_id=job_data.get('product_type_id'),
                station_id=job_data.get('station_id'),
                solar_system_id=job_data.get('solar_system_id'),
                start_date=job_data.get('start_date'),
                end_date=job_data.get('end_date'),
                pause_date=job_data.get('pause_date'),
                completed_date=job_data.get('completed_date'),
                completed_character_id=job_data.get('completed_character_id'),
                runs=job_data.get('runs', 1),
                cost=job_data.get('cost', 0),
                probability=job_data.get('probability'),
                attempts=job_data.get('attempts'),
                success=job_data.get('success'),
            )

    # Stale job handling: Mark active jobs past end_date + 90 days as unknown (999)
    stale_threshold = timezone.now() - timezone.timedelta(days=90)
    stale_jobs = IndustryJob.objects.filter(
        character=character,
        status=1,  # active
        end_date__lt=stale_threshold,
    ).exclude(job_id__in=seen_job_ids)

    stale_count = stale_jobs.update(status=999)
    if stale_count > 0:
        logger.info(
            f'Marked {stale_count} stale industry jobs as unknown '
            f'(character: {character.id})'
        )

    # Delete jobs that are no longer returned and are not stale
    # (completed/failed/cancelled jobs beyond ESI retention)
    jobs_to_delete = existing_job_ids - seen_job_ids
    if jobs_to_delete:
        IndustryJob.objects.filter(
            character=character,
            job_id__in=jobs_to_delete
        ).delete()

    character.industry_jobs_synced_at = timezone.now()
    character.save(update_fields=['industry_jobs_synced_at'])


def _sync_contracts(character) -> None:
    """
    Sync character contracts from ESI.

    Handles:
    - Pagination across multiple pages
    - Status transitions with logging
    - Contract items sync for each contract
    """
    from core.character.models import Contract, ContractItem

    # Fetch all pages of contracts
    all_contracts_data = []
    page = 1

    while True:
        response = ESIClient.get_contracts(character, page=page)
        contracts_data = response.data

        if not contracts_data:
            break

        all_contracts_data.extend(contracts_data)

        # ESI returns empty array when no more pages
        if len(contracts_data) < 1000:
            break

        page += 1

    # Get existing contracts for this character
    existing_contracts = {
        contract.contract_id: contract
        for contract in Contract.objects.filter(character=character)
    }
    existing_contract_ids = set(existing_contracts.keys())
    incoming_contract_ids = {contract['contract_id'] for contract in all_contracts_data}

    # Track seen contract IDs
    seen_contract_ids = set()

    # Process incoming contracts
    for contract_data in all_contracts_data:
        contract_id = contract_data['contract_id']
        seen_contract_ids.add(contract_id)
        new_status = contract_data.get('status', 'unknown')

        # Check if this is an existing contract with status change
        if contract_id in existing_contracts:
            existing_contract = existing_contracts[contract_id]
            old_status = existing_contract.status

            # Log status change
            if old_status != new_status:
                logger.info(
                    f'Contract {contract_id} status change: '
                    f'{old_status} -> {new_status} '
                    f'(character: {character.id})'
                )

            # Update contract data
            for field, value in {
                'type': contract_data.get('type'),
                'status': new_status,
                'title': contract_data.get('title', ''),
                'for_corporation': contract_data.get('for_corporation', False),
                'availability': contract_data.get('availability'),
                'date_issued': contract_data.get('date_issued'),
                'date_expired': contract_data.get('date_expired'),
                'date_accepted': contract_data.get('date_accepted'),
                'date_completed': contract_data.get('date_completed'),
                'issuer_id': contract_data.get('issuer_id'),
                'issuer_corporation_id': contract_data.get('issuer_corporation_id'),
                'assignee_id': contract_data.get('assignee_id'),
                'acceptor_id': contract_data.get('acceptor_id'),
                'days_to_complete': contract_data.get('days_to_complete'),
                'price': contract_data.get('price'),
                'reward': contract_data.get('reward'),
                'collateral': contract_data.get('collateral'),
                'buyout': contract_data.get('buyout'),
                'volume': contract_data.get('volume'),
            }.items():
                setattr(existing_contract, field, value)

            existing_contract.save()

            # Sync contract items for active contracts
            if existing_contract.is_active:
                _sync_contract_items(character, existing_contract)
        else:
            # Create new contract
            new_contract = Contract.objects.create(
                character=character,
                contract_id=contract_id,
                type=contract_data.get('type'),
                status=new_status,
                title=contract_data.get('title', ''),
                for_corporation=contract_data.get('for_corporation', False),
                availability=contract_data.get('availability'),
                date_issued=contract_data.get('date_issued'),
                date_expired=contract_data.get('date_expired'),
                date_accepted=contract_data.get('date_accepted'),
                date_completed=contract_data.get('date_completed'),
                issuer_id=contract_data.get('issuer_id'),
                issuer_corporation_id=contract_data.get('issuer_corporation_id'),
                assignee_id=contract_data.get('assignee_id'),
                acceptor_id=contract_data.get('acceptor_id'),
                days_to_complete=contract_data.get('days_to_complete'),
                price=contract_data.get('price'),
                reward=contract_data.get('reward'),
                collateral=contract_data.get('collateral'),
                buyout=contract_data.get('buyout'),
                volume=contract_data.get('volume'),
            )

            # Sync contract items for active contracts
            if new_contract.is_active:
                _sync_contract_items(character, new_contract)

    # Delete contracts that are no longer returned
    # (ESI retains completed contracts for ~30 days, after which they're gone)
    contracts_to_delete = existing_contract_ids - seen_contract_ids
    if contracts_to_delete:
        Contract.objects.filter(
            character=character,
            contract_id__in=contracts_to_delete
        ).delete()

    character.contracts_synced_at = timezone.now()
    character.save(update_fields=['contracts_synced_at'])


def _sync_contract_items(character, contract) -> None:
    """
    Sync items for a specific contract from ESI.

    Only fetches items for contracts where items are relevant
    (item_exchange, auction, courier contracts).
    """
    from core.character.models import ContractItem

    # Skip contracts that don't have items
    if contract.type == 'loan':
        return

    try:
        response = ESIClient.get_contract_items(character, contract.contract_id)
        items_data = response.data
    except Exception as e:
        logger.warning(
            f'Failed to fetch items for contract {contract.contract_id}: {e}'
        )
        return

    if not items_data:
        return

    # Get existing items for this contract
    existing_items = {
        item.item_id: item
        for item in ContractItem.objects.filter(contract=contract)
    }
    existing_item_ids = set(existing_items.keys())
    incoming_item_ids = {item['item_id'] for item in items_data}

    # Process incoming items
    for item_data in items_data:
        item_id = item_data['item_id']

        if item_id in existing_items:
            # Update existing item
            existing_item = existing_items[item_id]
            for field, value in {
                'type_id': item_data['type_id'],
                'quantity': item_data.get('quantity', 1),
                'is_included': item_data.get('is_included', True),
                'is_singleton': item_data.get('is_singleton', False),
                'raw_quantity': item_data.get('raw_quantity'),
            }.items():
                setattr(existing_item, field, value)
            existing_item.save()
        else:
            # Create new item
            ContractItem.objects.create(
                contract=contract,
                item_id=item_id,
                type_id=item_data['type_id'],
                quantity=item_data.get('quantity', 1),
                is_included=item_data.get('is_included', True),
                is_singleton=item_data.get('is_singleton', False),
                raw_quantity=item_data.get('raw_quantity'),
            )

    # Delete items no longer in contract
    items_to_delete = existing_item_ids - incoming_item_ids
    if items_to_delete:
        ContractItem.objects.filter(
            contract=contract,
            item_id__in=items_to_delete
        ).delete()


def sync_character_location(character_id: int) -> bool:
    """
    Sync a single character's location from ESI.

    This is designed to be called via django-q for background processing.
    It's lightweight and can be called frequently (e.g., on page load).

    Args:
        character_id: Character ID to sync location for

    Returns:
        True if successful, False otherwise
    """
    from core.models import Character, SyncStatus
    from requests.exceptions import HTTPError

    try:
        character = Character.objects.get(id=character_id)
    except Character.DoesNotExist:
        logger.warning(f'Character {character_id} not found for location sync')
        return False

    try:
        _sync_location(character)
        logger.debug(f'Location synced for character {character_id}')
        return True

    except HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            logger.warning(f'Location sync failed for character {character_id}: missing scope')
        else:
            logger.error(f'Location sync failed for character {character_id}: {e}')
        return False

    except Exception as e:
        logger.error(f'Location sync failed for character {character_id}: {e}')
        return False
