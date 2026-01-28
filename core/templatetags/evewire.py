"""
Custom template filters for evewire.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def add(value, arg):
    """Add arg to value."""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return ''


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


@register.filter
def format_duration(seconds):
    """Format seconds as a human-readable duration string (e.g., '2d 4h 30m')."""
    try:
        total_seconds = int(seconds)
    except (ValueError, TypeError):
        return ''

    if total_seconds <= 0:
        return '0m'

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


@register.filter
def commas(value):
    """Format number with thousand separators."""
    try:
        return "{:,}".format(int(float(value)))
    except (ValueError, TypeError):
        return ''


@register.filter
def module_name(type_id):
    """Get item type name for a module type_id."""
    try:
        from core.eve.models import ItemType
        item = ItemType.objects.get(id=int(type_id))
        return item.name
    except (ItemType.DoesNotExist, ValueError, TypeError):
        return f"Module {type_id}"


@register.filter
def reverse(value):
    """Reverse a list or queryset."""
    try:
        return list(value)[::-1]
    except (TypeError, AttributeError):
        return value


@register.filter
def dictsortreversed(value, arg):
    """Sort a list of dictionaries by a key in reverse order."""
    try:
        return sorted(value, key=lambda x: str(x.get(arg, '')), reverse=True)
    except (TypeError, AttributeError):
        return value


@register.filter
def selectattr(value, arg):
    """Select items from a list/queryset where an attribute is truthy.

    Usage:
        items|selectattr:"is_open"    # Items where is_open is truthy
    """
    try:
        items = list(value)
        return [item for item in items if getattr(item, arg, None)]
    except (TypeError, AttributeError):
        return value


@register.filter
def equal(value, arg):
    """Check if an attribute value equals arg.
    Intended to be chained after selectattr for the first item's attribute.

    Usage:
        items|selectattr:"attr"|equal:"value"    # First item's attr == "value"
    """
    try:
        items = list(value)
        if not items:
            return []
        attr = getattr(items[0], list(items[0].__dict__.keys())[0] if hasattr(items[0], '__dict__') else arg, None)
        return items if attr == arg else []
    except (TypeError, AttributeError):
        return value


@register.filter
def list_filter(value):
    """Convert a queryset/iterable to a list. Jinja2 compatibility.

    Note: Registered as 'list_filter' to avoid shadowing Python built-in,
    but template should use 'list_filter' instead of 'list'.
    """
    try:
        return list(value)
    except (TypeError, AttributeError):
        return value


# Also register as 'list' for template compatibility
list_filter = register.filter('list', list_filter)


@register.filter
def markdown(value):
    """Render markdown text to HTML."""
    try:
        import markdown as md
        return mark_safe(md.markdown(str(value), extensions=['extra', 'codehilite', 'nl2br', 'tables']))
    except Exception:
        return value


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key. Returns None if key doesn't exist."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


# Also register as 'lookup' for easier use in templates
lookup = register.filter('lookup', get_item)


@register.simple_tag
def meta_badge_class(meta_group_id):
    """Return the CSS class for a meta group badge."""
    meta_classes = {
        1: 'meta-tech-1',      # Tech I
        2: 'meta-tech-2',      # Tech II
        3: 'meta-storyline',   # Storyline
        4: 'meta-faction',     # Faction
        5: 'meta-officer',     # Officer
        6: 'meta-deadspace',   # Deadspace
        14: 'meta-abyssal',    # Abyssal
    }
    return meta_classes.get(meta_group_id, 'meta-default')


@register.simple_tag
def meta_badge_name(meta_group_id):
    """Return the display name for a meta group."""
    meta_names = {
        1: 'Tech I',
        2: 'Tech II',
        3: 'Storyline',
        4: 'Faction',
        5: 'Officer',
        6: 'Deadspace',
        14: 'Abyssal',
    }
    return meta_names.get(meta_group_id, 'Unknown')


@register.filter
def highlight(text, query):
    """Highlight search query terms in text."""
    if not query or not text:
        return text

    import re
    # Escape special regex characters in the query
    escaped_query = re.escape(str(query))
    # Create a pattern that matches the query (case-insensitive)
    pattern = re.compile(f'({escaped_query})', re.IGNORECASE)
    # Wrap matches in a span with highlight class
    highlighted = pattern.sub(r'<span class="highlight">\1</span>', str(text))
    return mark_safe(highlighted)


@register.filter
def slice_start(value, length):
    """Get first N characters of a string."""
    try:
        return str(value)[:int(length)]
    except (ValueError, TypeError):
        return value
