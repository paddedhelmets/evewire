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
def isk_format(value):
    """Format number as ISK with suffix (K, M, B)."""
    try:
        amount = float(value)
        if abs(amount) >= 1_000_000_000:
            return f"{amount / 1_000_000_000:,.2f} B ISK"
        elif abs(amount) >= 1_000_000:
            return f"{amount / 1_000_000:,.2f} M ISK"
        elif abs(amount) >= 1_000:
            return f"{amount / 1_000:,.2f} K ISK"
        else:
            return f"{amount:,.2f} ISK"
    except (ValueError, TypeError):
        return ''


@register.filter
def replace_underscore(value):
    """Replace underscores with spaces in strings."""
    try:
        return str(value).replace('_', ' ').title()
    except (ValueError, TypeError):
        return value
