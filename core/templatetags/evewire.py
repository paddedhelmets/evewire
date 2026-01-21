"""
Custom template filters for evewire.
"""

from django import template

register = template.Library()


@register.filter
def multiply(value, arg):
    """Multiply value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''


@register.filter
def divide(value, arg):
    """Divide value by arg."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return ''


@register.filter
def percentage(value):
    """Convert decimal to percentage string."""
    try:
        return f"{float(value) * 100:.1f}%"
    except (ValueError, TypeError):
        return ''


@register.filter
def format_is(value):
    """Format number as ISK (with thousand separators)."""
    try:
        return "{:,.2f}".format(float(value))
    except (ValueError, TypeError):
        return ''


@register.filter
def format_timedelta(value):
    """Format a timedelta as a human-readable string (e.g., '2d 4h 30m')."""
    if not value or not hasattr(value, 'total_seconds'):
        return ''

    total_seconds = int(value.total_seconds())
    if total_seconds <= 0:
        return 'Complete'

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f'{days}d')
    if hours > 0:
        parts.append(f'{hours}h')
    if minutes > 0 or not parts:
        parts.append(f'{minutes}m')

    return ' '.join(parts)
