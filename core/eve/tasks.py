"""
Background tasks for EVE Online data refresh.

This module contains async tasks that are executed by django-q for
refreshing various EVE data (structures, market prices, etc.).
"""

import logging
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

    logger.info(f'Refreshing structure {structure_id}')

    try:
        # Get existing structure
        try:
            structure = Structure.objects.get(structure_id=structure_id)
        except Structure.DoesNotExist:
            logger.warning(f'Structure {structure_id} no longer exists in DB, skipping refresh')
            return False

        # Try to find a character with access to this structure
        # Characters in the same corporation or with docking rights
        from core.models import Character

        potential_characters = Character.objects.filter(
            corporation_id=structure.owner_id
        )

        data = None
        for character in potential_characters:
            # Get access token
            from core.services import TokenManager
            try:
                token = TokenManager.get_access_token(character)
                if token:
                    data = fetch_structure_info(structure_id, character_token=token)
                    if data:
                        break
            except Exception as e:
                logger.debug(f'Token failed for {character.character_name}: {e}')
                continue

        if not data:
            # Try without token (unlikely to work for structures)
            data = fetch_structure_info(structure_id)

        if data:
            # Update structure
            structure.name = data['name']
            structure.solar_system_id = data['solar_system_id']
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
