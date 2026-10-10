"""Deliver due in-app reminders when the existing inbox polling checks for updates."""
from django.db.models import Exists, F, OuterRef, Q
from django.utils import timezone

from tasks.access import visible_to
from tasks.models import Task
from workplaces.services import workplaces_for_user
from .models import TaskReminder


def reminders_for_user(user):
    access = Q(user=user, workplace__isnull=True) | Q(
        user_id=F('workplace__owner_id'), workplace__in=workplaces_for_user(user),
    )
    recipient = Q(assignee__isnull=True, visibility='private', private_owner=user) | Q(assignee=user) | Q(assignee__isnull=True, user=user) | Q(
        assignee__isnull=True, section__project__visibility='private', section__project__private_owner=user,
    )
    tasks = visible_to(Task.objects.all(), user).filter(access, recipient, reminder_at__lte=timezone.now()).exclude(status='closed')
    delivered = TaskReminder.objects.filter(
        recipient=user, task_id=OuterRef('pk'), scheduled_at=OuterRef('reminder_at'),
    )
    due = tasks.annotate(delivered=Exists(delivered)).filter(delivered=False)
    batch = []
    for pk, scheduled_at in due.values_list('pk', 'reminder_at').iterator(chunk_size=500):
        batch.append(TaskReminder(task_id=pk, recipient=user, scheduled_at=scheduled_at))
        if len(batch) == 500:
            TaskReminder.objects.bulk_create(batch, ignore_conflicts=True)
            batch = []
    if batch:
        TaskReminder.objects.bulk_create(batch, ignore_conflicts=True)
    # Recheck current source state: completion, rescheduling or revoked membership
    # withdraws a stale reminder, including an already-open inbox action.
    return TaskReminder.objects.filter(
        recipient=user, task__in=tasks, scheduled_at=F('task__reminder_at'),
    )


def space_reminders_for_user(user):
    from spaces.access import visible_to as space_visible_to
    from spaces.models import SpaceTask, SpaceTaskReminder
    recipient = Q(assignee=user) | Q(assignee__isnull=True, visibility='private', private_owner=user) | Q(
        assignee__isnull=True, visibility='public', space__visibility='private', space__private_owner=user) | Q(
        assignee__isnull=True, visibility='public', space__visibility='public', space__user=user)
    tasks = space_visible_to(SpaceTask.objects.all(), user).filter(recipient, reminder_at__lte=timezone.now()).exclude(status='closed')
    delivered = SpaceTaskReminder.objects.filter(recipient=user, task_id=OuterRef('pk'), scheduled_at=OuterRef('reminder_at'))
    due = tasks.annotate(delivered=Exists(delivered)).filter(delivered=False)
    batch = []
    for pk, scheduled in due.values_list('pk', 'reminder_at').iterator(chunk_size=500):
        batch.append(SpaceTaskReminder(task_id=pk, recipient=user, scheduled_at=scheduled))
        if len(batch) == 500:
            SpaceTaskReminder.objects.bulk_create(batch, ignore_conflicts=True)
            batch = []
    if batch:
        SpaceTaskReminder.objects.bulk_create(batch, ignore_conflicts=True)
    return SpaceTaskReminder.objects.filter(recipient=user, task__in=tasks, scheduled_at=F('task__reminder_at'))
