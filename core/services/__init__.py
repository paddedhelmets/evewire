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
    def get_assets(cls, character) -> ESIResponse:
        """Get character assets."""
        return cls.get(f'/characters/{character.id}/assets/', character)

    @classmethod
    def get_orders(cls, character) -> ESIResponse:
        """Get character market orders."""
        return cls.get(f'/characters/{character.id}/orders/', character)

    @classmethod
    def get_wallet_journal(cls, character, page: int = 1) -> ESIResponse:
        """Get character wallet journal."""
        return cls.get(f'/characters/{character.id}/wallet/journal/', character, page=page)

    @classmethod
    def get_wallet_transactions(cls, character, page: int = 1) -> ESIResponse:
        """Get character wallet transactions."""
        return cls.get(f'/characters/{character.id}/wallet/transactions/', character, page=page)

    @classmethod
    def get_industry_jobs(cls, character) -> ESIResponse:
        """Get character industry jobs."""
        return cls.get(f'/characters/{character.id}/industry/jobs/', character)

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


# Sync functions for character data

def sync_character_data(character) -> bool:
    """Sync all character data from ESI."""
    from core.models import SyncStatus

    try:
        character.last_sync_status = SyncStatus.IN_PROGRESS
        character.save(update_fields=['last_sync_status'])

        _sync_skills(character)
        _sync_skill_queue(character)
        _sync_attributes(character)
        _sync_implants(character)
        _sync_wallet(character)
        _sync_assets(character)
        _sync_orders(character)
        _sync_industry_jobs(character)

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
            level_start_sp=queue_item['level_start_sp'],
            level_end_sp=queue_item['level_end_sp'],
            training_start_time=queue_item['start_time'],
            finish_date=queue_item['finish_date'],
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

    response = ESIClient.get_assets(character)
    assets_data = response.data

    # Delete old assets
    CharacterAsset.objects.filter(character=character).delete()

    # Build asset tree
    # ESI returns flat list with parent relationship via is_singleton/item_id
    # We need to build the MPTT tree
    assets_by_id = {item['item_id']: item for item in assets_data}

    # First pass: create all assets without parent
    for item_data in assets_data:
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
    for item_data in assets_data:
        item_id = item_data['item_id']
        # Check if this item has a location_id that points to another item
        # (items inside containers/ships have location_id = parent item_id)
        location_id = item_data.get('location_id')
        location_type = item_data.get('location_type')

        if location_type == 'other' and location_id in assets_by_id:
            # This item is inside another item
            try:
                asset = CharacterAsset.objects.get(item_id=item_id)
                parent = CharacterAsset.objects.get(item_id=location_id)
                asset.parent = parent
                asset.save(update_fields=['parent'])
            except CharacterAsset.DoesNotExist:
                pass

    character.assets_synced_at = timezone.now()
    character.save(update_fields=['assets_synced_at'])


def _sync_orders(character) -> None:
    """Sync character market orders from ESI."""
    from core.character.models import MarketOrder

    response = ESIClient.get_orders(character)
    orders_data = response.data

    # Delete old orders
    MarketOrder.objects.filter(character=character).delete()

    # Insert new orders
    for order_data in orders_data:
        MarketOrder.objects.create(
            character=character,
            order_id=order_data['order_id'],
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
            state=order_data.get('state', ''),
            escrow=order_data.get('escrow', 0),
        )

    character.orders_synced_at = timezone.now()
    character.save(update_fields=['orders_synced_at'])


def _sync_industry_jobs(character) -> None:
    """Sync character industry jobs from ESI."""
    from core.character.models import IndustryJob

    response = ESIClient.get_industry_jobs(character)
    jobs_data = response.data

    # Get existing job IDs for this character
    existing_job_ids = set(
        IndustryJob.objects.filter(character=character).values_list('job_id', flat=True)
    )
    incoming_job_ids = {job['job_id'] for job in jobs_data}

    # Delete jobs that are no longer returned (completed/failed/cancelled beyond retention)
    jobs_to_delete = existing_job_ids - incoming_job_ids
    if jobs_to_delete:
        IndustryJob.objects.filter(character=character, job_id__in=jobs_to_delete).delete()

    # Upsert jobs
    for job_data in jobs_data:
        IndustryJob.objects.update_or_create(
            character=character,
            job_id=job_data['job_id'],
            defaults={
                'activity_id': job_data.get('activity_id'),
                'status': job_data.get('status', 999),
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
            }
        )

    character.industry_jobs_synced_at = timezone.now()
    character.save(update_fields=['industry_jobs_synced_at'])
