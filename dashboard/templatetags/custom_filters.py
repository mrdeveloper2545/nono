from django import template

register = template.Library()

@register.filter
def commafy(value):
    """Convert a number to a string with commas as thousands separators."""
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value
    return '{:,}'.format(value)