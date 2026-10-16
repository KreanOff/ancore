"""Readable dashboard identifiers, unique within a Workspace."""
from django.utils.text import slugify
from django.urls.converters import SlugConverter


RESERVED_SLUGS = {'default', 'manage', 'create', 'search', 'groups'}
SLUG_MAX_LENGTH = 170


class DashboardSlugConverter(SlugConverter):
    def to_python(self, value):
        if value in RESERVED_SLUGS or value.isdecimal():
            raise ValueError
        return value

    def to_url(self, value):
        return self.to_python(str(value))


def unique_dashboard_slug(queryset, name):
    base = slugify(name.translate(str.maketrans({'ł': 'l', 'Ł': 'L'}))) or 'pulpit'
    if base in RESERVED_SLUGS or base.isdecimal():
        base = 'pulpit-' + base
    base = base[:SLUG_MAX_LENGTH].rstrip('-')
    candidate = base
    number = 2
    while queryset.filter(slug=candidate).exists():
        suffix = f'-{number}'
        candidate = base[:SLUG_MAX_LENGTH - len(suffix)].rstrip('-') + suffix
        number += 1
    return candidate
