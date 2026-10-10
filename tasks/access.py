"""Project, group and task privacy within the existing owner/Workspace scope.

Always pass the actual reader, never workspace_owner(request). Keep managers
unfiltered: numbering, migrations and maintenance must see all stored records.
Subqueries avoid adding nullable joins to rows locked with select_for_update().
"""
from django.db.models import F, Func, JSONField, Q
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
    """Visible data excluding observed resources and their entire task trees."""
    if queryset.model._meta.app_label == 'spaces':
        from spaces.access import editable_to as space_editable_to
        return space_editable_to(queryset, viewer)
    if queryset.model._meta.app_label == 'kanban':
        from kanban.access import editable_to as kanban_editable_to
        return kanban_editable_to(queryset, viewer)
    from .models import Task, TaskProject, TaskSection

    queryset = visible_to(queryset, viewer)
    if queryset.model._meta.app_label != 'tasks' or not getattr(viewer, 'is_authenticated', False):
        return queryset
    readonly_projects = TaskProject.objects.filter(
        visibility='private', memberships__user=viewer, memberships__role='observer',
    ).exclude(private_owner=viewer).order_by()
    readonly_sections = TaskSection.objects.filter(
        visibility='private', memberships__user=viewer, memberships__role='observer',
    ).exclude(private_owner=viewer).order_by()
    readonly_tasks = Task.objects.filter(
        visibility='private', memberships__user=viewer, memberships__role='observer',
    ).exclude(private_owner=viewer).order_by()
    model_name = queryset.model._meta.model_name
    if model_name == 'taskproject':
        return queryset.exclude(pk__in=readonly_projects.values('pk'))
    if model_name == 'taskprojectnote':
        return queryset.exclude(project__in=readonly_projects)
    if model_name == 'tasksection':
        return queryset.exclude(project__in=readonly_projects).exclude(pk__in=readonly_sections)
    if model_name == 'tasksectionnote':
        return queryset.exclude(section__project__in=readonly_projects).exclude(section__in=readonly_sections)
    paths = {
        'task': 'pk', 'taskattachment': 'task_id', 'taskactivity': 'task_id',
        'taskworklog': 'task_id', 'taskcommentimage': 'activity__task_id',
    }
    if model_name in paths:
        roots = Task.objects.filter(Q(section__project__in=readonly_projects) | Q(section__in=readonly_sections) | Q(pk__in=readonly_tasks))
        return queryset.exclude(**{paths[model_name] + '__in': task_tree_ids(roots)})
    return queryset


def require_editable(queryset, viewer):
    """Reject a whole operation before writing, including mixed bulk selections."""
    from django.core.exceptions import PermissionDenied

    if queryset.exclude(pk__in=editable_to(queryset.model.objects.all(), viewer)).exists():
        raise PermissionDenied('Masz dostęp tylko do odczytu tego projektu, grupy lub zadania.')


def visible_to(queryset, viewer):
    if queryset.model._meta.app_label == 'spaces':
        from spaces.access import visible_to as space_visible_to
        return space_visible_to(queryset, viewer)
    if queryset.model._meta.app_label == 'kanban':
        from kanban.access import visible_to as kanban_visible_to
        return kanban_visible_to(queryset, viewer)
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
    projects = TaskProject.objects.filter(scope, project_privacy, space_archived=False).order_by()
    from spaces.models import Space
    projects = projects.exclude(pk__in=Space.objects.exclude(project_id=None).values('project_id'))
    if model is TaskProject:
        return queryset.filter(pk__in=projects.values('pk'))
    if model is TaskProjectTemplate:
        return queryset.filter(pk__in=TaskProjectTemplate.objects.filter(scope, privacy).values('pk'))
    section_privacy = privacy | Q(visibility='private', private_owner__isnull=False, shared_with=viewer)
    sections = TaskSection.objects.filter(section_privacy, project__in=projects).order_by()
    if model is TaskSection:
        return queryset.filter(pk__in=sections.values('pk'))
    # Preserve legacy orphan/foreign-link handling for public projects. Their
    # task owner and Workspace remain authoritative; private links fail closed.
    task_sections = TaskSection.objects.filter(
        section_privacy, Q(project__visibility='public') | Q(project__in=projects),
        project__space_archived=False, project__space__isnull=True,
    ).order_by()
    task_privacy = privacy | Q(visibility='private', private_owner__isnull=False, shared_with=viewer)
    allowed_tasks = Task.objects.filter(task_privacy).order_by().values('pk')
    hidden_roots = Task.objects.filter(
        (Q(section__isnull=False) & ~Q(section__in=task_sections)) | ~Q(pk__in=allowed_tasks)
    )
    tasks = Task.objects.filter(scope, space_archived=False).exclude(work_item__task__isnull=False).exclude(pk__in=task_tree_ids(hidden_roots)).order_by()
    paths = {
        'task': 'pk', 'taskattachment': 'task_id', 'taskactivity': 'task_id',
        'taskworklog': 'task_id', 'taskcommentimage': 'activity__task_id',
    }
    if model._meta.model_name in paths:
        result = queryset.filter(**{paths[model._meta.model_name] + '__in': tasks.values('pk')})
        if model._meta.model_name == 'taskactivity':
            # Parent history must not reveal a private child's title or activity.
            visible_ids = tasks.annotate(json_pk=Func(F('pk'), function='to_jsonb', output_field=JSONField())).values('json_pk')
            result = result.filter(~Q(metadata__has_key='subtask_pk') | Q(metadata__subtask_pk__in=visible_ids))
        return result
    if model._meta.model_name == 'taskprojectnote':
        return queryset.filter(project__in=projects)
    if model._meta.model_name == 'tasksectionnote':
        return queryset.filter(section__in=sections)
    return queryset
