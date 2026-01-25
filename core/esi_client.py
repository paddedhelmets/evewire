"""
ESI (EVE Swagger Interface) API client functions.

This module provides functions for fetching data from EVE Online's ESI API.
It handles authentication, rate limiting, and error handling.
"""

import logging
import requests
from typing import Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger('evewire')

# ESI base URL
ESI_BASE_URL = "https://esi.evetech.net/latest"
ESI_DATASOURCE = "tranquility"  # TQ server


def fetch_structure_info(structure_id: int, character_token: str = None) -> Optional[Dict[str, Any]]:
    """
    Fetch structure information from ESI.

    ESI Endpoint: GET /universe/structures/{structure_id}/
    Docs: https://esi.evetech.net/latest/#/Universe/get_universe_structures_structure_id

    Note: This requires the character to have access to the structure
    (either in the same corporation or with docking rights). It also
    requires the esi-universe.read_structures.v1 scope.

    Args:
        structure_id: The structure ID
        character_token: Optional character access token for structures
                         that require authentication (most do)

    Returns:
        Structure data dict with keys:
        - name: Structure name
        - owner_id: Corporation ID that owns the structure
        - solar_system_id: Solar system where structure is located
        - position: Dict with x, y, z coordinates
        - type_id: Item type ID of the structure

        Returns None if fetch fails.
    """
    url = f"{ESI_BASE_URL}/universe/structures/{structure_id}/"

    headers = {
        'Accept': 'application/json',
        'User-Agent': f'evewire (GitHub: paddedhelmets/evewire)',
    }

    # Add token if provided (required for most structures)
    if character_token:
        headers['Authorization'] = f'Bearer {character_token}'

    params = {
        'datasource': ESI_DATASOURCE,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            logger.info(f'Fetched structure {structure_id}: {data.get("name")}')
            return data

        elif response.status_code == 403:
            # Forbidden - character doesn't have access
            logger.warning(f'Access denied to structure {structure_id} (403)')
            return None

        elif response.status_code == 404:
            # Not found - structure may have been destroyed
            logger.warning(f'Structure {structure_id} not found (404)')
            return None

        else:
            logger.error(f'Failed to fetch structure {structure_id}: {response.status_code} {response.text}')
            return None

    except requests.Timeout:
        logger.error(f'Timeout fetching structure {structure_id}')
        return None
    except Exception as e:
        logger.error(f'Error fetching structure {structure_id}: {e}')
        return None


def fetch_with_token_retry(structure_id: int, characters) -> Optional[Dict[str, Any]]:
    """
    Fetch structure info, trying multiple character tokens until one works.

    Different characters may have different structure access (different
    corporations, docking rights, etc.). This function tries tokens from
    multiple characters until it finds one that can access the structure.

    Args:
        structure_id: The structure ID
        characters: QuerySet of Character objects to try tokens from

    Returns:
        Structure data dict, or None if no character can access it
    """
    for character in characters:
        # Get a valid access token for this character
        from core.services import TokenManager

        try:
            token = TokenManager.get_access_token(character)
            if not token:
                continue

            data = fetch_structure_info(structure_id, character_token=token)
            if data:
                return data

        except Exception as e:
            logger.warning(f'Failed to fetch structure {structure_id} with character {character.character_name}: {e}')
            continue

    logger.error(f'No character could access structure {structure_id}')
    return None


def ensure_structure_data(structure_id: int, user=None) -> Optional['Structure']:
    """
    Ensure structure data exists in the database.

    This is the main method to use when you need structure info. It:
    1. Checks if structure is already cached
    2. If not, fetches from ESI
    3. Stores in database for future use

    Args:
        structure_id: The structure ID
        user: Optional user to get character tokens from

    Returns:
        Structure object, or None if fetching failed
    """
    from core.eve.models import Structure

    # Try cache first
    try:
        structure = Structure.objects.get(structure_id=structure_id)

        # Check if stale (older than 7 days, or 1 hour for errors)
        if structure.is_stale():
            # Queue background refresh
            queue_structure_refresh(structure_id)

        return structure

    except Structure.DoesNotExist:
        pass

    # Fetch from ESI
    # Try tokens from user's characters
    if user:
        characters = user.characters.all()
        data = fetch_with_token_retry(structure_id, characters)
    else:
        # Try without token (public structures only - very rare)
        data = fetch_structure_info(structure_id)

    if not data:
        # Could not fetch - return None
        # Caller should handle this (show "Structure {id}" as fallback)
        return None

    # Create structure in database
    structure = Structure.objects.create(
        structure_id=structure_id,
        name=data['name'],
        owner_id=data['owner_id'],
        solar_system_id=data['solar_system_id'],
        position_x=data.get('position', {}).get('x'),
        position_y=data.get('position', {}).get('y'),
        position_z=data.get('position', {}).get('z'),
        type_id=data['type_id'],
        last_sync_status='ok',
    )

    logger.info(f'Cached new structure: {structure.name} ({structure_id})')
    return structure


def queue_structure_refresh(structure_id: int):
    """
    Queue a background task to refresh structure data.

    Uses django-q for async execution.
    """
    try:
        from django_q.tasks import async_task

        async_task(
            'core.eve.tasks.refresh_structure',
            structure_id,
            group='structure_refresh',
        )
    except Exception as e:
        logger.warning(f'Failed to queue structure refresh for {structure_id}: {e}')
