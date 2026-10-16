"""Save task edits without changing their existing location."""
from django.core.exceptions import PermissionDenied

from core.task_numbering import lock_task_numbers
from workplaces.models import Workplace
from .access import require_editable
from .models import Task


def save_task_edit(task, actor):
    """Keep the saved group, numbering and metadata when editing a task."""
    with lock_task_numbers(task.user_id):
        if task.workplace_id:
            Workplace.objects.select_for_update().get(pk=task.workplace_id)
        roots = Task.objects.filter(pk=task.pk)
        original = roots.select_for_update().only('section_id', 'parent_id').first() if task.pk else None
        if original:
            require_editable(roots, actor)
            if original.section_id != task.section_id:
                raise PermissionDenied('Nie można zmieniać przestrzeni ani grupy istniejącego zadania.')
            if original.parent_id != task.parent_id and task.parent_id:
                if not Task.objects.filter(pk=task.parent_id, section_id=original.section_id).exists():
                    raise PermissionDenied('Zadanie nadrzędne musi należeć do tej samej grupy.')
        task.save()
        return task
