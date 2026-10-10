"""Access to independent spaces and their task trees, within live Workspace scope."""
from django.core.exceptions import PermissionDenied
from django.db import connections
from django.db.models import F, Func, JSONField, Q
from django.db.models.expressions import RawSQL

from workplaces.services import workplaces_for_user
from .models import Space, SpaceTask


def spaces_for(viewer):
    if not viewer or not viewer.is_authenticated or not viewer.is_active:
        return Space.objects.none()
    return Space.objects.filter(
        Q(visibility='public') | Q(private_owner=viewer) | Q(visibility='private', private_owner__isnull=False, memberships__user=viewer),
        user_id=F('workplace__owner_id'), workplace__in=workplaces_for_user(viewer),
    ).distinct()


def editable_spaces(viewer):
    observed = Space.objects.filter(visibility='private', memberships__user=viewer, memberships__role='observer').exclude(private_owner=viewer)
    return spaces_for(viewer).exclude(pk__in=observed.values('pk'))


def tree_ids(roots):
    sql, params = roots.order_by().values('pk').query.get_compiler(using=roots.db).as_sql()
    table = connections[roots.db].ops.quote_name(SpaceTask._meta.db_table)
    return RawSQL(f'WITH RECURSIVE tree(id) AS (({sql}) UNION SELECT child.id FROM {table} child JOIN tree parent ON child.parent_id=parent.id) SELECT id FROM tree', params)


def visible_to(queryset, viewer):
    if queryset.model is Space:
        return queryset.filter(pk__in=spaces_for(viewer).values('pk'))
    if not viewer or not viewer.is_authenticated or not viewer.is_active:
        return queryset.none()
    allowed = SpaceTask.objects.filter(Q(visibility='public') | Q(private_owner=viewer) | Q(visibility='private', memberships__user=viewer)).values('pk')
    hidden = SpaceTask.objects.exclude(pk__in=allowed)
    tasks = SpaceTask.objects.filter(
        space__in=spaces_for(viewer), work_item__space_id=F('space_id'),
    ).exclude(pk__in=tree_ids(hidden))
    path = 'pk' if queryset.model is SpaceTask else 'task_id'
    result = queryset.filter(**{path + '__in': tasks.values('pk')})
    if queryset.model._meta.model_name == 'spacetaskactivity':
        ids = tasks.annotate(json_pk=Func(F('pk'), function='to_jsonb', output_field=JSONField())).values('json_pk')
        result = result.filter(~Q(metadata__has_key='subtask_pk') | Q(metadata__subtask_pk__in=ids))
    return result


def editable_to(queryset, viewer):
    if queryset.model is Space:
        return queryset.filter(pk__in=editable_spaces(viewer).values('pk'))
    queryset = visible_to(queryset, viewer)
    if not viewer or not viewer.is_authenticated:
        return queryset.none()
    observed = SpaceTask.objects.filter(visibility='private', memberships__user=viewer, memberships__role='observer').exclude(private_owner=viewer)
    roots = SpaceTask.objects.filter(Q(pk__in=observed) | ~Q(space__in=editable_spaces(viewer)))
    path = 'pk' if queryset.model is SpaceTask else 'task_id'
    return queryset.exclude(**{path + '__in': tree_ids(roots)})


def require_editable(queryset, viewer):
    if queryset.exclude(pk__in=editable_to(queryset.model.objects.all(), viewer)).exists():
        raise PermissionDenied('Masz dostęp tylko do odczytu tego zadania lub przestrzeni.')


def task_people(task):
    """Active Workspace people who already have access to the space and every parent."""
    from workplaces.services import workplace_people
    people = workplace_people(task.space.workplace)
    if task.space.visibility == 'private':
        people = people.filter(Q(pk=task.space.private_owner_id) | Q(pk__in=task.space.memberships.values('user_id')))
    parent, visited = task.parent, set()
    while parent and parent.pk not in visited:
        visited.add(parent.pk)
        if parent.visibility == 'private':
            people = people.filter(Q(pk=parent.private_owner_id) | Q(pk__in=parent.memberships.values('user_id')))
        parent = parent.parent
    return people
