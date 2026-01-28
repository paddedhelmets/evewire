"""
Background tasks for EVE Online data refresh.

This module contains async tasks that are executed by django-q for
refreshing various EVE data (structures, market prices, etc.).
"""

import logging
import random
import time
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django_q.tasks import async_task

logger = logging.getLogger('evewire')


def refresh_structure(structure_id: int) -> bool:
    """
    Refresh structure data from ESI.

    This is called as a background task by django-q to update
    structure information that has become stale.

    Args:
        structure_id: The structure ID to refresh

    Returns:
        True if successful, False otherwise
    """
    from core.eve.models import Structure
    from core.esi_client import fetch_structure_info

    logger.info(f'Refreshing/creating structure {structure_id}')

    try:
        # Get existing structure, or create a placeholder
        try:
            structure = Structure.objects.get(structure_id=structure_id)
            # Skip refresh if already marked inaccessible (403 = no docking access)
            if structure.last_sync_status == 'inaccessible':
                logger.debug(f'Structure {structure_id} is marked inaccessible, skipping refresh')
                return True
            is_new = False
        except Structure.DoesNotExist:
            # Create placeholder structure - will try to fetch details below
            structure = Structure.objects.create(
                structure_id=structure_id,
                name=f'Unknown Structure {structure_id}',
                owner_id=0,  # Will update when we fetch from ESI
                solar_system_id=0,
                type_id=0,
                last_sync_status='pending',
            )
            is_new = True
            logger.info(f'Created placeholder for new structure {structure_id}')

        # Try to find a character with access to this structure
        # Characters in the same corporation or with docking rights
        from core.models import Character

        # For existing structures, try characters in the owning corp
        # For new structures, try ALL characters (one might have docking rights)
        if is_new or structure.owner_id == 0:
            potential_characters = Character.objects.filter(
                assets_synced_at__isnull=False  # Has synced recently
            )
        else:
            potential_characters = Character.objects.filter(
                corporation_id=structure.owner_id
            )

        data = None
        all_403 = True  # Track if all attempts returned 403

        for character in potential_characters:
            # Get access token for this character
            from core.services import TokenManager
            try:
                token = TokenManager.get_access_token_for_character(character)
                if token:
                    result = fetch_structure_info(structure_id, character_token=token)
                    if result:
                        if result.get('status') == 200:
                            # Success - got structure data
                            data = result['data']
                            break
                        elif result.get('status') == 403:
                            # 403 - no access, but track that we got a response
                            continue  # Try next character
                        else:
                            # Some other status
                            all_403 = False
            except Exception as e:
                logger.debug(f'Token failed for {character.character_name}: {e}')
                continue

        if data:
            # Update structure
            structure.name = data['name']
            structure.solar_system_id = data['solar_system_id']
            structure.owner_id = data.get('owner_id', structure.owner_id)
            structure.position_x = data.get('position', {}).get('x')
            structure.position_y = data.get('position', {}).get('y')
            structure.position_z = data.get('position', {}).get('z')
            structure.type_id = data['type_id']
            structure.last_updated = timezone.now()
            structure.last_sync_status = 'ok'
            structure.last_sync_error = ''
            structure.save()

            logger.info(f'Refreshed structure {structure_id}: {structure.name}')
            return True
        elif all_403:
            # All characters returned 403 - structure exists but no docking access
            structure.last_updated = timezone.now()
            structure.last_sync_status = 'inaccessible'
            structure.last_sync_error = 'No docking access (403 Forbidden)'
            structure.save()

            logger.info(f'Marked structure {structure_id} as inaccessible (no docking access)')
            return True  # Return True because this is expected/permanent
        else:
            # Mark as error but don't delete
            structure.last_updated = timezone.now()
            structure.last_sync_status = 'error'
            structure.last_sync_error = 'Failed to fetch from ESI'
            structure.save()

            logger.warning(f'Failed to refresh structure {structure_id}')
            return False

    except Exception as e:
        logger.error(f'Error refreshing structure {structure_id}: {e}')

        # Try to update error status
        try:
            structure = Structure.objects.get(structure_id=structure_id)
            structure.last_updated = timezone.now()
            structure.last_sync_status = 'error'
            structure.last_sync_error = str(e)
            structure.save()
        except:
            pass

        return False


def refresh_all_stale_structures() -> dict:
    """
    Refresh all structures that are marked as stale.

    This should be called periodically (e.g., weekly via cron/management command).

    Returns:
        Dict with stats:
        - total: Total number of structures checked
        - queued: Number of refresh tasks queued
        - skipped: Number of structures skipped (not stale)
    """
    from core.eve.models import Structure

    stale_structures = Structure.objects.filter(
        last_sync_status='ok'
    ).filter(
        last_updated__lt=timezone.now() - timezone.timedelta(days=7)
    )

    error_structures = Structure.objects.filter(
        last_sync_status='error'
    ).filter(
        last_updated__lt=timezone.now() - timezone.timedelta(hours=1)
    )

    total_stale = stale_structures.count() + error_structures.count()

    queued = 0
    for structure in stale_structures:
        async_task('core.eve.tasks.refresh_structure', structure.structure_id)
        queued += 1

    for structure in error_structures:
        async_task('core.eve.tasks.refresh_structure', structure.structure_id)
        queued += 1

    logger.info(f'Queued {queued} structure refresh tasks ({total_stale} stale structures found)')

    return {
        'total': total_stale,
        'queued': queued,
        'skipped': Structure.objects.count() - total_stale,
    }


# ============================================================================
# CHARACTER REFRESH TASKS
# ============================================================================

def refresh_stale_characters() -> dict:
    """
    Queue background refresh for characters with stale metadata.

    Refreshes: location, wallet, orders, contracts, industry jobs
    Interval: 10 minutes

    Adds random jitter (0-30 seconds) to each task to prevent thundering herd
    when multiple characters are queued simultaneously.
    """
    from core.models import Character
    from django.utils import timezone

    stale_cutoff = timezone.now() - timezone.timedelta(minutes=10)

    # Characters that haven't synced in 10 minutes, or never synced
    stale_characters = list(Character.objects.filter(
        models.Q(last_sync__lt=stale_cutoff) | models.Q(last_sync__isnull=True)
    ))

    queued = 0
    for i, character in enumerate(stale_characters):
        # Add jitter: spread tasks over 0-30 seconds randomly
        # This prevents all characters from hitting ESI simultaneously
        jitter_seconds = random.randint(0, 30)
        scheduled_time = timezone.now() + timedelta(seconds=jitter_seconds)
        async_task(
            'core.eve.tasks._sync_character_metadata',
            character.id,
            schedule=scheduled_time
        )
        queued += 1

    logger.info(f'Character metadata refresh: queued {queued} characters with jitter')
    return {'queued': queued}


def _sync_character_metadata(character_id: int) -> bool:
    """
    Sync character metadata (location, wallet, orders, contracts, industry).

    This is a lighter sync than full character sync - excludes assets and skills.
    """
    from core.models import Character
    from core.services import (
        ESIClient, _sync_location, _sync_wallet, _sync_orders,
        _sync_orders_history, _sync_industry_jobs, _sync_contracts,
        update_character_corporation_info
    )
    from requests.exceptions import HTTPError

    try:
        character = Character.objects.get(id=character_id)
        logger.info(f'Syncing metadata for character {character_id}')

        # Fetch basic character info (includes corporation_id)
        char_info_response = ESIClient.get_character_info(character_id)
        char_info = char_info_response.data
        character.corporation_id = char_info.get('corporation_id')
        character.save(update_fields=['corporation_id'])

        # Update corporation/alliance names
        update_character_corporation_info(character)

        # Location might fail with 401 if scope not granted
        try:
            _sync_location(character)
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                logger.warning(f'Location not available for character {character_id} (missing scope)')
            else:
                raise

        _sync_wallet(character)
        _sync_orders(character)
        _sync_orders_history(character)
        _sync_industry_jobs(character)

        # Contracts might fail with 401 if scope not granted
        try:
            _sync_contracts(character)
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                logger.warning(f'Contracts not available for character {character_id} (missing scope)')
            else:
                raise

        character.last_sync = timezone.now()
        character.last_sync_status = 'success'
        character.last_sync_error = ''
        character.save(update_fields=['last_sync', 'last_sync_status', 'last_sync_error'])

        logger.info(f'Metadata sync complete for character {character_id}')
        return True

    except Exception as e:
        logger.error(f'Failed to sync metadata for character {character_id}: {e}')
        try:
            character = Character.objects.get(id=character_id)
            character.last_sync_status = 'failed'
            character.last_sync_error = str(e)[:500]
            character.save(update_fields=['last_sync_status', 'last_sync_error'])
        except:
            pass
        return False


def refresh_stale_assets() -> dict:
    """
    Queue background refresh for characters with stale assets.

    Assets are cached by ESI for 1 hour, so no point checking more often.
    Interval: 1 hour

    Adds random jitter (0-60 seconds) to spread out asset fetches.
    """
    from core.models import Character
    from django.utils import timezone

    stale_cutoff = timezone.now() - timezone.timedelta(hours=1)

    # Characters that haven't had assets synced in 1 hour, or never synced
    stale_characters = list(Character.objects.filter(
        models.Q(assets_synced_at__lt=stale_cutoff) | models.Q(assets_synced_at__isnull=True)
    ))

    queued = 0
    for character in stale_characters:
        # Assets are heavier, spread over 0-60 seconds
        jitter_seconds = random.randint(0, 60)
        scheduled_time = timezone.now() + timedelta(seconds=jitter_seconds)
        async_task(
            'core.eve.tasks._sync_character_assets',
            character.id,
            schedule=scheduled_time
        )
        queued += 1

    logger.info(f'Asset refresh: queued {queued} characters with jitter')
    return {'queued': queued}


def _sync_character_assets(character_id: int) -> bool:
    """Sync character assets only."""
    from core.models import Character
    from core.services import _sync_assets

    try:
        character = Character.objects.get(id=character_id)
        logger.info(f'Syncing assets for character {character_id}')

        _sync_assets(character)

        logger.info(f'Asset sync complete for character {character_id}')
        return True

    except Exception as e:
        logger.error(f'Failed to sync assets for character {character_id}: {e}')
        return False


def refresh_stale_skills() -> dict:
    """
    Queue background refresh for skills/queue when a skill is ending soon.

    Checks if any character has a skill finishing within 2 hours.
    If so, queues a refresh for that character.

    Interval: 30 minutes (check frequency)

    Adds random jitter (0-20 seconds) to spread out skill fetches.
    """
    from core.models import Character
    from core.character.models import SkillQueueItem
    from django.utils import timezone

    soon_cutoff = timezone.now() + timezone.timedelta(hours=2)
    queued = 0

    for character in Character.objects.all():
        # Check if any skill in queue finishes within 2 hours
        finishing_soon = SkillQueueItem.objects.filter(
            character=character,
            finish_date__lte=soon_cutoff
        ).exists()

        # Also refresh if never synced
        needs_refresh = finishing_soon or not character.skills_synced_at

        if needs_refresh:
            # Skills are light, spread over 0-20 seconds
            jitter_seconds = random.randint(0, 20)
            scheduled_time = timezone.now() + timedelta(seconds=jitter_seconds)
            async_task(
                'core.eve.tasks._sync_character_skills',
                character.id,
                schedule=scheduled_time
            )
            queued += 1

    logger.info(f'Skills refresh: queued {queued} characters with jitter')
    return {'queued': queued}


def _sync_character_skills(character_id: int) -> bool:
    """Sync character skills and skill queue only."""
    from core.models import Character
    from core.services import _sync_skills, _sync_skill_queue, _sync_attributes, _sync_implants

    try:
        character = Character.objects.get(id=character_id)
        logger.info(f'Syncing skills for character {character_id}')

        _sync_skills(character)
        _sync_skill_queue(character)
        _sync_attributes(character)
        _sync_implants(character)

        logger.info(f'Skill sync complete for character {character_id}')
        return True

    except Exception as e:
        logger.error(f'Failed to sync skills for character {character_id}: {e}')
        return False


# ============================================================================
# LIVE UNIVERSE BROWSER - ESI REFRESH TASKS
# ============================================================================

def queue_esi_refresh(task_path: str, *args, jitter_range: tuple = (0, 30), **kwargs):
    """
    Queue an ESI refresh task.

    Note: jitter_range is no longer used as async_task doesn't support scheduling.
    Tasks run immediately.

    Args:
        task_path: Dotted path to the task function (e.g., 'core.eve.tasks.refresh_incursions')
        *args: Arguments to pass to the task
        jitter_range: Ignored (kept for compatibility)
        **kwargs: Keyword arguments to pass to the task

    Returns:
        The task ID from async_task
    """
    return async_task(
        task_path,
        *args,
        **kwargs
    )


def refresh_all_lp_stores() -> dict:
    """
    Discover all loyalty stores by checking corporations with mission agents.

    ESI Endpoint: GET /loyalty/{corporation_id}/offers/
    Returns list of offers for a specific corporation if they have an LP store.

    This should be called periodically (e.g., daily via cron).

    The function queries corporations that have agents from SDE and checks which
    ones have LP stores by attempting to fetch their offers. Corporations with
    404 responses are skipped (no LP store).

    Returns:
        Dict with status and count of queued refreshes
    """
    from core.services import ESIClient
    from core.sde.models import AgtAgents

    client = ESIClient()
    count = 0
    checked = 0

    # Get distinct corporation IDs that have agents (corps with mission agents likely have LP stores)
    # Use set() to ensure deduplication
    agent_corp_ids = set(AgtAgents.objects.values_list('corporation_id', flat=True))

    logger.info(f'Checking {len(agent_corp_ids)} corporations with agents for LP stores')

    for corporation_id in agent_corp_ids:
        checked += 1

        # Try to fetch offers for this corporation
        # ESI returns 404 for corps without LP stores, 200 with empty array for those with no offers
        response = client.get_loyalty_store_offers(corporation_id)

        # ESIResponse stores status in meta.response.status_code
        if response and response.meta.response.status_code == 200:
            # This corporation has an LP store (even if empty)
            queue_esi_refresh(
                'core.eve.tasks.refresh_corporation_lp_store',
                corporation_id,
                jitter_range=(0, 60)
            )
            count += 1

            if count % 50 == 0:
                logger.info(f'Found {count} LP stores so far (checked {checked}/{len(agent_corp_ids)})')

        # Rate limiting - brief sleep between checks
        if checked % 50 == 0:
            time.sleep(1)

    logger.info(f'Queued {count} LP store refresh tasks from {checked} corporations checked')
    return {'status': 'queued', 'count': count}


def refresh_corporation_lp_store(corporation_id: int) -> dict:
    """
    Refresh loyalty store offers for a corporation.

    ESI Endpoint: GET /loyalty/stores/{corporation_id}/offers/

    Args:
        corporation_id: The corporation ID to fetch offers for

    Returns:
        Dict with status and offer count
    """
    from core.services import ESIClient
    from core.eve.models import CorporationLPStoreInfo, LoyaltyStoreOffer

    client = ESIClient()
    response = client.get_loyalty_store_offers(corporation_id)

    if not response or not response.data:
        logger.warning(f'Failed to fetch LP store for corp {corporation_id}')
        return {'status': 'error', 'message': 'ESI request failed', 'corporation_id': corporation_id}

    # Update or create metadata
    lp_info, created = CorporationLPStoreInfo.objects.get_or_create(
        corporation_id=corporation_id,
        defaults={'has_loyalty_store': True}
    )

    # Clear old offers
    LoyaltyStoreOffer.objects.filter(corporation=lp_info).delete()

    # Create new offers
    offers = []
    for offer_data in response.data:
        offer = LoyaltyStoreOffer.from_esi(corporation_id, offer_data)
        offer.corporation_id = lp_info.corporation_id
        offers.append(offer)

    LoyaltyStoreOffer.objects.bulk_create(offers)

    lp_info.total_offers = len(offers)
    lp_info.last_offer_ids = [o.offer_id for o in offers]
    lp_info.save(update_fields=['total_offers', 'last_offer_ids'])
    lp_info.mark_ok()

    logger.info(f'Refreshed LP store for corp {corporation_id}: {len(offers)} offers')
    return {'status': 'ok', 'corporation_id': corporation_id, 'offers': len(offers)}


def refresh_incursions() -> dict:
    """
    Refresh active incursions from ESI.

    ESI Endpoint: GET /incursions/
    Incursions spawn and despawn regularly, so this should be called frequently.

    Returns:
        Dict with status and incursion count
    """
    from core.services import ESIClient
    from core.eve.models import ActiveIncursion

    client = ESIClient()
    response = client.get_incursions()

    if not response or not response.data:
        logger.warning('No incursion data from ESI')
        return {'status': 'error', 'message': 'No data from ESI'}

    # Clear old incursions
    ActiveIncursion.objects.all().delete()

    # Create new records
    incursions = []
    for inc_data in response.data:
        incursions.append(ActiveIncursion(
            incursion_id=f"{inc_data.get('constellation_id')}-{inc_data.get('faction_id')}-{inc_data.get('state')}",
            constellation_id=inc_data.get('constellation_id'),
            constellation_name=inc_data.get('constellation_name', ''),
            faction_id=inc_data.get('faction_id'),
            faction_name=inc_data.get('faction_name', ''),
            state=inc_data.get('state'),
            type_id=inc_data.get('type_id'),
            has_boss=inc_data.get('has_boss', False),
            staged=inc_data.get('staged', False),
        ))

    ActiveIncursion.objects.bulk_create(incursions)

    # Mark all as OK
    for inc in incursions:
        inc.mark_ok()

    logger.info(f'Refreshed incursions: {len(incursions)} active')
    return {'status': 'ok', 'count': len(incursions)}


def refresh_wars(max_war_id: int = None) -> dict:
    """
    Refresh active wars from ESI.

    ESI Endpoint: GET /wars/
    Returns list of war IDs. Use max_war_id for incremental updates.

    This fetches war IDs and queues individual war detail refreshes.

    Args:
        max_war_id: Optional max war ID for incremental updates

    Returns:
        Dict with status and count of queued war detail fetches
    """
    from core.services import ESIClient
    from core.eve.models import ActiveWar

    client = ESIClient()
    response = client.get_wars(max_war_id=max_war_id)

    if not response or not response.data:
        logger.warning('No war data from ESI')
        return {'status': 'error', 'message': 'No data from ESI'}

    # Get war IDs
    war_ids = response.data

    # Mark all existing wars as potentially stale (only on full refresh)
    if max_war_id is None:
        ActiveWar.objects.filter(is_active=True).update(is_active=False, war_status='stale')

    # Queue detail fetches for each war
    for war_id in war_ids:
        queue_esi_refresh(
            'core.eve.tasks.refresh_war_detail',
            war_id,
            jitter_range=(0, 10)
        )

    logger.info(f'Queued {len(war_ids)} war detail refresh tasks')
    return {'status': 'queued', 'count': len(war_ids)}


def refresh_war_detail(war_id: int) -> dict:
    """
    Refresh details for a specific war.

    ESI Endpoint: GET /wars/{war_id}/

    Args:
        war_id: The war ID to fetch details for

    Returns:
        Dict with status and war info
    """
    from core.services import ESIClient
    from core.eve.models import ActiveWar

    client = ESIClient()
    response = client.get_war(war_id)

    if not response or not response.data:
        logger.warning(f'Failed to fetch war {war_id} details')
        return {'status': 'error', 'message': 'ESI request failed', 'war_id': war_id}

    data = response.data

    # Extract ally (aggressor's ally) from data
    ally = data.get('aggressor', {}).get('ally')
    ally_id = ally.get('id') if ally else None
    ally_name = ally.get('name') if ally else ''

    # Extract defender_ally from data
    defender_ally = data.get('defender', {}).get('ally')
    defender_ally_id = defender_ally.get('id') if defender_ally else None
    defender_ally_name = defender_ally.get('name') if defender_ally else ''

    war, created = ActiveWar.objects.update_or_create(
        war_id=war_id,
        defaults={
            'declared': data.get('declared'),
            'started': data.get('started'),
            'finished': data.get('finished'),
            'aggressor_id': data.get('aggressor', {}).get('id'),
            'aggressor_name': data.get('aggressor', {}).get('name', ''),
            'ally_id': ally_id,
            'ally_name': ally_name,
            'defender_id': data.get('defender', {}).get('id'),
            'defender_name': data.get('defender', {}).get('name', ''),
            'defender_ally_id': defender_ally_id,
            'defender_ally_name': defender_ally_name,
            'mutual': data.get('mutual', False),
            'open_for_allies': data.get('open_for_allies', False),
            'prize_ship': data.get('prize_ship'),
            'is_active': data.get('finished') is None,
            'war_status': 'active' if data.get('finished') is None else 'finished',
        }
    )

    war.mark_ok()

    logger.info(f'Refreshed war {war_id} (created: {created})')
    return {'status': 'ok', 'war_id': war_id, 'created': created}


def refresh_sov_map() -> dict:
    """
    Refresh sovereignty map from ESI.

    ESI Endpoint: GET /sovereignty/map/
    Shows which alliance controls each nullsec system.

    Returns:
        Dict with status and system count
    """
    from core.services import ESIClient
    from core.eve.models import SovMapSystem

    client = ESIClient()
    response = client.get_sov_map()

    if not response or not response.data:
        logger.warning('No sov map data from ESI')
        return {'status': 'error', 'message': 'No data from ESI'}

    # Clear old data
    SovMapSystem.objects.all().delete()

    # Create new records
    systems = []
    for sys_data in response.data:
        systems.append(SovMapSystem(
            system_id=sys_data.get('system_id'),
            alliance_id=sys_data.get('alliance_id'),
            corporation_id=sys_data.get('corporation_id'),
            faction_id=sys_data.get('faction_id'),
        ))

    SovMapSystem.objects.bulk_create(systems, batch_size=1000)

    logger.info(f'Refreshed sov map: {len(systems)} systems')
    return {'status': 'ok', 'count': len(systems)}


def refresh_sov_campaigns() -> dict:
    """
    Refresh active sovereignty campaigns from ESI.

    ESI Endpoint: GET /sovereignty/campaigns/
    Shows ongoing structure fights for sovereignty.

    Returns:
        Dict with status and campaign count
    """
    from core.services import ESIClient
    from core.eve.models import SovCampaign

    client = ESIClient()
    response = client.get_sov_campaigns()

    if not response or not response.data:
        logger.warning('No sov campaigns data from ESI')
        return {'status': 'error', 'message': 'No data from ESI'}

    # Clear old campaigns
    SovCampaign.objects.all().delete()

    # Create new records
    campaigns = []
    for camp_data in response.data:
        campaigns.append(SovCampaign(
            campaign_id=camp_data.get('campaign_id'),
            system_id=camp_data.get('solar_system_id'),
            constellation_id=camp_data.get('constellation_id'),
            region_id=None,  # Not provided by ESI, can be looked up from system
            attackers_score=camp_data.get('attackers_score', 0.0),
            defender_id=camp_data.get('defender_id'),
            defender_score=camp_data.get('defender_score', 0.0),
            event_type=camp_data.get('event_type', ''),
            start_time=camp_data.get('start_time'),
            structure_id=camp_data.get('structure_id'),
        ))

    SovCampaign.objects.bulk_create(campaigns)

    logger.info(f'Refreshed sov campaigns: {len(campaigns)} active')
    return {'status': 'ok', 'count': len(campaigns)}


def refresh_fw_stats() -> dict:
    """
    Refresh faction warfare stats from ESI.

    ESI Endpoint: GET /fw/stats/
    Shows kills, victories, and pilot counts for each faction.

    Returns:
        Dict with status and faction count
    """
    from core.services import ESIClient
    from core.eve.models import FactionWarfareStats

    client = ESIClient()
    response = client.get_fw_stats()

    if not response or not response.data:
        logger.warning('No FW stats data from ESI')
        return {'status': 'error', 'message': 'No data from ESI'}

    # Update or create stats for each faction
    count = 0
    for faction_data in response.data:
        stats, created = FactionWarfareStats.objects.update_or_create(
            faction_id=faction_data.get('faction_id'),
            defaults={
                'faction_name': '',  # Would need SDE lookup
                'kills_last_week': faction_data.get('kills', {}).get('last_week', 0),
                'kills_total': faction_data.get('kills', {}).get('total', 0),
                'victory_points_last_week': faction_data.get('victory_points', {}).get('last_week', 0),
                'victory_points_total': faction_data.get('victory_points', {}).get('total', 0),
                'pilots_last_week': 0,  # ESI doesn't provide weekly pilot count
                'pilots_total': faction_data.get('pilots', 0),
                'systems_controlled': faction_data.get('systems_controlled', 0),
            }
        )
        count += 1

    logger.info(f'Refreshed FW stats for {count} factions')
    return {'status': 'ok', 'count': count}


def refresh_fw_systems() -> dict:
    """
    Refresh faction warfare system ownership from ESI.

    ESI Endpoint: GET /fw/systems/
    Shows which faction controls each FW system.

    Returns:
        Dict with status and system count
    """
    from core.services import ESIClient
    from core.eve.models import FactionWarfareSystem

    client = ESIClient()
    response = client.get_fw_systems()

    if not response or not response.data:
        logger.warning('No FW systems data from ESI')
        return {'status': 'error', 'message': 'No data from ESI'}

    # Clear old data
    FactionWarfareSystem.objects.all().delete()

    # Create new records
    systems = []
    for sys_data in response.data:
        systems.append(FactionWarfareSystem(
            system_id=sys_data.get('solar_system_id'),
            faction_id=sys_data.get('faction_id'),
            corporation_id=sys_data.get('corporation_id'),
            solar_system_name=sys_data.get('solar_system_name', ''),
        ))

    FactionWarfareSystem.objects.bulk_create(systems)

    logger.info(f'Refreshed FW systems: {len(systems)} systems')
    return {'status': 'ok', 'count': len(systems)}


def refresh_region_market_summary(region_id: int) -> dict:
    """
    Refresh market summary for a region.

    ESI Endpoint: GET /markets/{region_id}/orders/

    Args:
        region_id: The region ID to fetch market data for

    Returns:
        Dict with status and order counts
    """
    from core.services import ESIClient
    from core.eve.models import RegionMarketSummary

    client = ESIClient()

    # Fetch all pages of orders
    all_orders = []
    page = 1
    while True:
        response = client.get_market_orders(region_id, page=page)
        if not response or not response.data:
            break
        all_orders.extend(response.data)
        if len(response.data) < 1000:  # Less than full page = last page
            break
        page += 1

    # Update or create summary
    summary, created = RegionMarketSummary.objects.get_or_create(
        region_id=region_id,
        defaults={
            'total_orders': len(all_orders),
            'buy_orders': sum(1 for o in all_orders if o.get('is_buy_order')),
            'sell_orders': sum(1 for o in all_orders if not o.get('is_buy_order')),
        }
    )

    # Update existing summary
    if not created:
        summary.total_orders = len(all_orders)
        summary.buy_orders = sum(1 for o in all_orders if o.get('is_buy_order'))
        summary.sell_orders = sum(1 for o in all_orders if not o.get('is_buy_order'))
        summary.last_order_ids = [o.get('order_id') for o in all_orders[:100]]  # Sample for change detection
        summary.save()

    summary.mark_ok()

    logger.info(f'Refreshed market summary for region {region_id}: {len(all_orders)} orders')
    return {'status': 'ok', 'region_id': region_id, 'orders': len(all_orders)}
