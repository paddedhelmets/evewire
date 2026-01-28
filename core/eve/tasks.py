"""
Background tasks for EVE Online data refresh.

This module contains async tasks that are executed by django-q for
refreshing various EVE data (structures, market prices, etc.).
"""

import logging
import random
import time
from django.db import models
from django.utils import timezone
from django_q.tasks import async_task, schedule

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
        async_task(
            'core.eve.tasks._sync_character_metadata',
            character.id,
            schedule=schedule('now').later(seconds=jitter_seconds)
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
        async_task(
            'core.eve.tasks._sync_character_assets',
            character.id,
            schedule=schedule('now').later(seconds=jitter_seconds)
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
            async_task(
                'core.eve.tasks._sync_character_skills',
                character.id,
                schedule=schedule('now').later(seconds=jitter_seconds)
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
