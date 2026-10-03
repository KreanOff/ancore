"""Workspace scope and inherited Kanban privacy; always use the actual viewer."""
from django.core.exceptions import PermissionDenied
from django.db import connections
from django.db.models import F, Func, JSONField, Q
from django.db.models.expressions import RawSQL

from workplaces.services import workplaces_for_user


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
    from .models import Kanban, KanbanProject, KanbanSection
    if queryset.model._meta.app_label != 'kanban':
        return queryset
    if not viewer or not viewer.is_authenticated or not viewer.is_active:
        return queryset.none()
    scope = Q(user=viewer, workplace__isnull=True) | Q(
        user_id=F('workplace__owner_id'), workplace__in=workplaces_for_user(viewer),
    )
    privacy = Q(visibility='public') | Q(visibility='private', private_owner=viewer) | Q(
        visibility='private', private_owner__isnull=False, shared_with=viewer,
    )
    from spaces.models import LegacyKanbanLink
    projects = KanbanProject.objects.filter(scope, privacy).exclude(
        pk__in=LegacyKanbanLink.objects.filter(kind='project').values('source_id'),
    ).order_by()
    sections = KanbanSection.objects.filter(privacy, project__in=projects).order_by()
    name = queryset.model._meta.model_name
    if name == 'kanbanproject':
        return queryset.filter(pk__in=projects.values('pk'))
    if name == 'kanbanprojectnote':
        return queryset.filter(project__in=projects)
    if name == 'kanbansection':
        return queryset.filter(pk__in=sections.values('pk'))
    if name == 'kanbanboardcolumn':
        return queryset.filter(section__in=sections)
    paths = {'kanban': 'pk', 'kanbanattachment': 'task_id',
             'kanbanactivity': 'task_id', 'kanbancommentimage': 'activity__task_id'}
    if name in paths:
        # An ancestor's hidden board also hides malformed legacy descendants.
        hidden = Kanban.objects.filter(
            ~scope | (Q(section__isnull=False) & ~Q(section__in=sections)),
        )
        cards = Kanban.objects.filter(scope).exclude(pk__in=card_tree_ids(hidden)).exclude(
            pk__in=LegacyKanbanLink.objects.filter(kind='task').values('source_id'),
        ).order_by()
        result = queryset.filter(**{paths[name] + '__in': cards.values('pk')})
        if name == 'kanbanactivity':
            ids = cards.annotate(json_pk=Func(F('pk'), function='to_jsonb', output_field=JSONField())).values('json_pk')
            result = result.filter(~Q(action='subtask_created') | Q(metadata__subtask_pk__in=ids))
        return result
    return queryset


def editable_to(queryset, viewer):
    from .models import Kanban, KanbanProject, KanbanSection
    queryset = visible_to(queryset, viewer)
    if not viewer or not viewer.is_authenticated:
        return queryset.none()
    projects = KanbanProject.objects.filter(
        visibility='private', memberships__user=viewer, memberships__role='observer',
    ).exclude(private_owner=viewer).order_by()
    sections = KanbanSection.objects.filter(
        visibility='private', memberships__user=viewer, memberships__role='observer',
    ).exclude(private_owner=viewer).order_by()
    name = queryset.model._meta.model_name
    if name == 'kanbanproject':
        return queryset.exclude(pk__in=projects.values('pk'))
    if name == 'kanbanprojectnote':
        return queryset.exclude(project__in=projects)
    if name == 'kanbansection':
        return queryset.exclude(project__in=projects).exclude(pk__in=sections.values('pk'))
    if name == 'kanbanboardcolumn':
        return queryset.exclude(section__project__in=projects).exclude(section__in=sections)
    paths = {'kanban': 'pk', 'kanbanattachment': 'task_id',
             'kanbanactivity': 'task_id', 'kanbancommentimage': 'activity__task_id'}
    if name in paths:
        roots = Kanban.objects.filter(Q(section__project__in=projects) | Q(section__in=sections))
        return queryset.exclude(**{paths[name] + '__in': card_tree_ids(roots)})
    return queryset


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
