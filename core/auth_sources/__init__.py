"""
Pluggable Authentication Sources for evewire.

This module provides an abstraction layer for different authentication backends:
- EVE SSO (ESI) - default, included in public repo
- GICE (Imperium) - private, separate repo

Each auth source implements the CharacterSource interface and can:
- Authenticate users via OAuth/OIDC
- Fetch user's character list
- Provide tokens for ESI API calls (direct or proxied)
"""

from typing import Dict, List, Optional, Type
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Import implementations
from core.auth_sources.base import CharacterSource, CharacterInfo, TokenResponse
from core.auth_sources.esi_sso import ESISSOCharacterSource


def get_available_sources() -> Dict[str, Type[CharacterSource]]:
    """
    Get all available character sources.

    Returns a dict of source_id -> source_class.

    Private sources (like GICE) are loaded dynamically if configured.
    """
    sources = {
        'esi_sso': ESISSOCharacterSource,
    }

    # Dynamically load private sources if configured
    # Private sources are registered in settings.AUTH_SOURCE_CLASSES
    if hasattr(settings, 'AUTH_SOURCE_CLASSES'):
        for source_id, source_class_path in settings.AUTH_SOURCE_CLASSES.items():
            if source_id not in sources:
                try:
                    module_path, class_name = source_class_path.rsplit('.', 1)
                    import importlib
                    module = importlib.import_module(module_path)
                    source_class = getattr(module, class_name)
                    sources[source_id] = source_class
                except (ImportError, AttributeError) as e:
                    raise ImproperlyConfigured(
                        f"Cannot load auth source '{source_id}' from {source_class_path}: {e}"
                    )

    return sources


def get_source(source_id: Optional[str] = None) -> CharacterSource:
    """
    Get an instantiated character source.

    Args:
        source_id: The source identifier (e.g., 'esi_sso', 'gice').
                   If None, returns the default source.

    Returns:
        An instantiated CharacterSource

    Raises:
        ImproperlyConfigured: If the source is not found
    """
    sources = get_available_sources()

    if source_id is None:
        # Get default source from settings or fall back to ESI SSO
        source_id = getattr(settings, 'DEFAULT_AUTH_SOURCE', 'esi_sso')

    if source_id not in sources:
        available = ', '.join(sources.keys())
        raise ImproperlyConfigured(
            f"Unknown auth source '{source_id}'. Available: {available}"
        )

    return sources[source_id]()


def get_default_source() -> CharacterSource:
    """Get the default character source for the site."""
    return get_source(None)


__all__ = [
    'CharacterSource',
    'CharacterInfo',
    'TokenResponse',
    'get_available_sources',
    'get_source',
    'get_default_source',
]
