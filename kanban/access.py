"""Keep historical Kanban records inaccessible through current application helpers."""
from django.core.exceptions import PermissionDenied
from django.db import connections
from django.db.models.expressions import RawSQL


def card_tree_ids(roots):
    from .models import Kanban
    connection = connections[roots.db]
    sql, params = roots.order_by().values('pk').query.get_compiler(using=roots.db).as_sql()
    table = connection.ops.quote_name(Kanban._meta.db_table)
    return RawSQL(
        f'WITH RECURSIVE card_tree(id) AS (({sql}) UNION '
        f'SELECT child.id FROM {table} child JOIN card_tree parent ON child.parent_id = parent.id) '
        'SELECT id FROM card_tree', params,
    )


def visible_to(queryset, viewer):
    """Historical rows are kept in storage, never exposed as active work."""
    return queryset.none() if queryset.model._meta.app_label == 'kanban' else queryset


def editable_to(queryset, viewer):
    return visible_to(queryset, viewer)


def require_editable(queryset, viewer):
    if queryset.exclude(pk__in=editable_to(queryset.model.objects.all(), viewer)).exists():
        raise PermissionDenied('Masz dostęp tylko do odczytu lub nie masz dostępu do tego elementu Kanban.')


def require_deletable(queryset, viewer):
    from .models import Kanban, KanbanProject, KanbanSection
    require_editable(queryset, viewer)
    if queryset.model is KanbanProject:
        sections = KanbanSection.objects.filter(project__in=queryset)
        require_editable(sections, viewer)
        roots = Kanban.objects.filter(section__in=sections)
    elif queryset.model is KanbanSection:
        roots = Kanban.objects.filter(section__in=queryset)
    else:
        roots = queryset
    require_editable(Kanban.objects.filter(pk__in=card_tree_ids(roots)), viewer)
