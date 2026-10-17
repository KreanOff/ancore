"""Explicit fixtures for the independent Space domain."""
from uuid import uuid4

from .defaults import template_settings
from .models import Space, SpaceConfiguration, SpaceTask


def make_space(**values):
    workplace_id = values.get('workplace_id') or values['workplace'].pk
    template = values.get('template', 'tasks')
    values.setdefault('key', 'S' + uuid4().hex[:10].upper())
    if 'configuration' not in values:
        values['configuration'] = SpaceConfiguration.objects.create(
            workplace_id=workplace_id, name=values['name'], settings=template_settings(template),
        )
    return Space.objects.create(**values)


def make_task(*, user, workplace, space=None, **values):
    """Create current task fixtures with explicit Workspace ownership.

    Children reuse the parent's space. Pass ``space`` when several unrelated
    tasks should share a catalog or a sequence of WorkItem keys.
    """
    if space is None:
        parent = values.get('parent')
        space = parent.space if parent else make_space(
            user=user, workplace=workplace, name='Przestrzeń testowa',
        )
    if space.user_id != user.pk or space.workplace_id != workplace.pk:
        raise ValueError('Task fixture must use its space owner and Workspace.')
    values.setdefault('created_by', user)
    return SpaceTask.objects.create(space=space, **values)
