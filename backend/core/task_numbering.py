"""Serialize task-number allocation and compaction for each owner."""
from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.db import DEFAULT_DB_ALIAS, transaction


@contextmanager
def lock_task_numbers(user_id, using=None):
    using = using or DEFAULT_DB_ALIAS
    with transaction.atomic(using=using):
        # Lock a row that exists even when this owner has no tasks yet.
        # Always take this lock before section/task locks in numbered writes.
        get_user_model().objects.using(using).select_for_update(no_key=True).only('pk').get(pk=user_id)
        yield


def renumber_tasks(model, user, workplace=None, using=None):
    using = using or DEFAULT_DB_ALIAS
    with lock_task_numbers(user.pk, using=using):
        tasks = model.objects.using(using).filter(user=user).only('pk', 'task_id', 'workplace_id')
        if workplace is not None:
            tasks = tasks.filter(workplace=workplace)
        counters, changed = {}, []
        for task in tasks.order_by('workplace_id', 'task_id', 'pk'):
            number = counters.get(task.workplace_id, 0) + 1
            counters[task.workplace_id] = number
            if task.task_id != number:
                task.task_id = number
                changed.append(task)
        if changed:
            model.objects.using(using).bulk_update(changed, ['task_id'], batch_size=500)
