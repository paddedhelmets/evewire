"""
Custom template filters for mathematical operations.
"""

from django import template

register = template.Library()


@register.filter
def div(value, arg):
    """Divide value by arg."""
    try:
        return float(value) / float(arg) if float(arg) != 0 else 0
    except (ValueError, ZeroDivisionError):
        return 0


@register.filter
def mul(value, arg):
    """Multiply value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
