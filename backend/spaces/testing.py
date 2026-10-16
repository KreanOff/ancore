"""Explicit fixtures for the independent Space domain."""
from uuid import uuid4

from .defaults import template_settings
from .models import Space, SpaceConfiguration


def make_space(**values):
    workplace_id = values.get('workplace_id') or values['workplace'].pk
    template = values.get('template', 'tasks')
    values.setdefault('key', 'S' + uuid4().hex[:10].upper())
    if 'configuration' not in values:
        values['configuration'] = SpaceConfiguration.objects.create(
            workplace_id=workplace_id, name=values['name'], settings=template_settings(template),
        )
    return Space.objects.create(**values)
