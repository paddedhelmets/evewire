"""
Core app for evewire.

Re-exports all views from split modules for backward compatibility.
"""

# Import all view modules explicitly
from core import (
    views,
    views_skills,
    views_econ,
    views_assets,
    views_characters,
    views_exports,
    views_fittings,
)

# Re-export all view functions for backward compatibility with URLs
def _export_views(module):
    """Export all callable attributes from a module as globals."""
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if callable(attr) and not attr_name.startswith('_'):
            globals()[attr_name] = attr

_export_views(views)
_export_views(views_skills)
_export_views(views_econ)
_export_views(views_assets)
_export_views(views_characters)
_export_views(views_exports)
_export_views(views_fittings)
