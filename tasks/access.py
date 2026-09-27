"""Explicit project privacy, in addition to the existing owner/Workspace scope.

Always pass the actual reader, never workspace_owner(request). Keep managers
unfiltered: numbering, migrations and maintenance must see all stored records.
Subqueries avoid adding nullable joins to rows locked with select_for_update().
"""
from django.db.models import F, Q
from django.db.models.expressions import RawSQL

from workplaces.services import workplaces_for_user


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
    """Visible data excluding observer projects and their entire task trees."""
    from .models import Task, TaskProject

    queryset = visible_to(queryset, viewer)
    if queryset.model._meta.app_label != 'tasks' or not getattr(viewer, 'is_authenticated', False):
        return queryset
    readonly_projects = TaskProject.objects.filter(
        visibility='private', memberships__user=viewer, memberships__role='observer',
    ).exclude(private_owner=viewer).order_by()
    model_name = queryset.model._meta.model_name
    if model_name == 'taskproject':
        return queryset.exclude(pk__in=readonly_projects.values('pk'))
    if model_name in {'tasksection', 'taskprojectnote'}:
        return queryset.exclude(project__in=readonly_projects)
    if model_name == 'tasksectionnote':
        return queryset.exclude(section__project__in=readonly_projects)
    paths = {
        'task': 'pk', 'taskattachment': 'task_id', 'taskactivity': 'task_id',
        'taskworklog': 'task_id', 'taskcommentimage': 'activity__task_id',
    }
    if model_name in paths:
        roots = Task.objects.filter(section__project__in=readonly_projects)
        return queryset.exclude(**{paths[model_name] + '__in': task_tree_ids(roots)})
    return queryset


def require_editable(queryset, viewer):
    """Reject a whole operation before writing, including mixed bulk selections."""
    from django.core.exceptions import PermissionDenied

    if queryset.exclude(pk__in=editable_to(queryset.model.objects.all(), viewer)).exists():
        raise PermissionDenied('Masz dostęp tylko do odczytu tego projektu.')


def visible_to(queryset, viewer):
    from .models import Task, TaskProject, TaskProjectTemplate, TaskSection

    model = queryset.model
    if model._meta.app_label != 'tasks':
        return queryset
    if not viewer or not getattr(viewer, 'is_authenticated', False) or not viewer.is_active:
        return queryset.none()
    scope = Q(user=viewer, workplace__isnull=True) | Q(
        user_id=F('workplace__owner_id'), workplace__in=workplaces_for_user(viewer),
    )
    privacy = Q(visibility='public') | Q(visibility='private', private_owner=viewer)
    project_privacy = privacy | Q(visibility='private', private_owner__isnull=False, shared_with=viewer)
    projects = TaskProject.objects.filter(scope, project_privacy).order_by()
    if model is TaskProject:
        return queryset.filter(pk__in=projects.values('pk'))
    if model is TaskProjectTemplate:
        return queryset.filter(pk__in=TaskProjectTemplate.objects.filter(scope, privacy).values('pk'))
    sections = TaskSection.objects.filter(project__in=projects).order_by()
    if model is TaskSection:
        return queryset.filter(pk__in=sections.values('pk'))
    # Preserve legacy orphan/foreign-link handling for public projects. Their
    # task owner and Workspace remain authoritative; private links fail closed.
    task_sections = TaskSection.objects.filter(
        Q(project__visibility='public') | Q(project__in=projects),
    ).order_by()
    hidden_roots = Task.objects.filter(section__isnull=False).exclude(section__in=task_sections)
    tasks = Task.objects.filter(scope).exclude(pk__in=task_tree_ids(hidden_roots)).order_by()
    paths = {
        'task': 'pk', 'taskattachment': 'task_id', 'taskactivity': 'task_id',
        'taskworklog': 'task_id', 'taskcommentimage': 'activity__task_id',
    }
    if model._meta.model_name in paths:
        return queryset.filter(**{paths[model._meta.model_name] + '__in': tasks.values('pk')})
    if model._meta.model_name == 'taskprojectnote':
        return queryset.filter(project__in=projects)
    if model._meta.model_name == 'tasksectionnote':
        return queryset.filter(section__in=sections)
    return queryset
