"""Compatibility helpers for historical work and the independent Space domain."""
from django.db.models.expressions import RawSQL


def task_tree_ids(roots):
    """Include every descendant, even in legacy trees spanning project groups."""
    from django.db import connections
    from .models import Task

    connection = connections[roots.db]
    seed_sql, params = roots.order_by().values('pk').query.get_compiler(using=roots.db).as_sql()
    table = connection.ops.quote_name(Task._meta.db_table)
    # UNION (not UNION ALL) also terminates for malformed legacy cycles.
    return RawSQL(
        f'WITH RECURSIVE task_tree(id) AS (({seed_sql}) UNION '
        f'SELECT child.id FROM {table} child JOIN task_tree parent ON child.parent_id = parent.id) '
        'SELECT id FROM task_tree', params,
    )


def require_deletable_tasks(roots, viewer):
    """A cascade must never delete a hidden or read-only descendant."""
    from django.core.exceptions import PermissionDenied
    from .models import Task

    descendants = Task.objects.filter(pk__in=task_tree_ids(roots))
    if descendants.exclude(pk__in=editable_to(Task.objects.all(), viewer)).exists():
        raise PermissionDenied('Nie można usunąć elementu zawierającego niedostępne podzadania.')


def editable_to(queryset, viewer):
    """Only the current Space domain can expose editable work."""
    if queryset.model._meta.app_label == 'spaces':
        from spaces.access import editable_to as space_editable_to
        return space_editable_to(queryset, viewer)
    return visible_to(queryset, viewer)


def require_editable(queryset, viewer):
    from django.core.exceptions import PermissionDenied
    if queryset.exclude(pk__in=editable_to(queryset.model.objects.all(), viewer)).exists():
        raise PermissionDenied('Ten element jest archiwalny lub nie masz dostępu do jego edycji.')


def visible_to(queryset, viewer):
    """Historical work is never exposed through current application helpers.

    TaskTag and TaskTagNote remain in Space views, which apply current Space
    ACLs through tasks.tagging.visible_tags and tag_action.
    """
    if queryset.model._meta.app_label == 'spaces':
        from spaces.access import visible_to as space_visible_to
        return space_visible_to(queryset, viewer)
    if queryset.model._meta.app_label == 'kanban':
        from kanban.access import visible_to as kanban_visible_to
        return kanban_visible_to(queryset, viewer)
    if queryset.model._meta.app_label == 'tasks':
        if queryset.model._meta.model_name not in {'tasktag', 'tasktagnote'}:
            return queryset.none()
        if not viewer or not getattr(viewer, 'is_authenticated', False) or not viewer.is_active:
            return queryset.none()
    return queryset
