"""Deliver due in-app reminders when the existing inbox polling checks for updates."""
from django.db.models import Exists, F, OuterRef, Q
from django.utils import timezone

from .models import TaskReminder


def reminders_for_user(user):
    """Historical deliveries are retained but never delivered or shown."""
    return TaskReminder.objects.none()


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
