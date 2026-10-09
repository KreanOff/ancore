"""Save user edits and move descendants through the existing Task.save hooks."""
from django.core.exceptions import PermissionDenied

from core.task_numbering import lock_task_numbers
from workplaces.models import Workplace
from .access import require_editable, task_tree_ids
from .models import Task, TaskActivity, TaskSection


def require_movable_task_tree(task, viewer):
    roots = Task.objects.filter(pk=task.pk)
    tree = Task.objects.filter(pk__in=task_tree_ids(roots))
    require_editable(tree, viewer)


def save_task_tree(task, actor):
    """Move a task and its full tree atomically; preserve numbering and metadata."""
    with lock_task_numbers(task.user_id):
        if task.workplace_id:
            Workplace.objects.select_for_update().get(pk=task.workplace_id)
        roots = Task.objects.filter(pk=task.pk)
        original = roots.only('section_id').first() if task.pk else None
        descendants = []
        if original:
            require_editable(roots, actor)
            if original.section_id != task.section_id:
                require_movable_task_tree(task, actor)
                if task.section_id:
                    target = TaskSection.objects.filter(pk=task.section_id)
                    require_editable(target, actor)
                    if not target.filter(project__user_id=task.user_id, project__workplace_id=task.workplace_id).exists():
                        raise PermissionDenied('Grupa musi należeć do tego samego Workspace.')
                descendants = list(Task.objects.filter(
                    pk__in=task_tree_ids(roots),
                ).exclude(pk=task.pk).select_for_update(of=('self',)).select_related('section__project').order_by('pk'))
        task.save()
        for child in descendants:
            if child.section_id == task.section_id:
                continue
            previous_label = child.section.title if child.section_id else '—'
            child.section = task.section
            child._activity_actor = actor
            child.save(update_fields=['section', 'workplace'])
            TaskActivity.objects.create(
                task=child, actor=actor, action='updated', message='przeniósł podzadanie razem z zadaniem nadrzędnym',
                metadata={'fields': ['grupa'], 'changes': [{
                    'field': 'grupa', 'from_label': previous_label,
                    'to_label': task.section.title if task.section_id else '—',
                }]},
            )
        return task
