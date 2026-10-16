"""Readable space identifiers, allocated once within a Workspace."""
from django.utils.text import slugify


SLUG_MAX_LENGTH = 170


def unique_space_slug(queryset, name):
    base = slugify(name.translate(str.maketrans({'ł': 'l', 'Ł': 'L'}))) or 'przestrzen'
    if base.isdecimal():
        base = 'przestrzen-' + base
    base = base[:SLUG_MAX_LENGTH].rstrip('-')
    candidate = base
    number = 2
    while queryset.filter(slug=candidate).exists():
        suffix = f'-{number}'
        candidate = base[:SLUG_MAX_LENGTH - len(suffix)].rstrip('-') + suffix
        number += 1
    return candidate
