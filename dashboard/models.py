from django.conf import settings
from django.db import models


class TaskReminder(models.Model):
    """One personal delivery per task, recipient and scheduled reminder time."""

    task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    scheduled_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=['task', 'recipient', 'scheduled_at'], name='unique_task_reminder_delivery',
        )]


class NotificationState(models.Model):
    """Personal inbox state; source records remain the authority for access/content."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task_activity = models.ForeignKey('tasks.TaskActivity', null=True, blank=True, on_delete=models.CASCADE)
    kanban_activity = models.ForeignKey('kanban.KanbanActivity', null=True, blank=True, on_delete=models.CASCADE)
    invitation = models.ForeignKey('workplaces.WorkplaceInvitation', null=True, blank=True, on_delete=models.CASCADE)
    reminder = models.ForeignKey(TaskReminder, null=True, blank=True, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(task_activity__isnull=False, kanban_activity__isnull=True, invitation__isnull=True, reminder__isnull=True)
                    | models.Q(task_activity__isnull=True, kanban_activity__isnull=False, invitation__isnull=True, reminder__isnull=True)
                    | models.Q(task_activity__isnull=True, kanban_activity__isnull=True, invitation__isnull=False, reminder__isnull=True)
                    | models.Q(task_activity__isnull=True, kanban_activity__isnull=True, invitation__isnull=True, reminder__isnull=False)
                ),
                name='notification_exactly_one_source',
            ),
            models.UniqueConstraint(fields=['user', 'task_activity'], name='notification_user_task_unique'),
            models.UniqueConstraint(fields=['user', 'kanban_activity'], name='notification_user_kanban_unique'),
            models.UniqueConstraint(fields=['user', 'invitation'], name='notification_user_invite_unique'),
            models.UniqueConstraint(fields=['user', 'reminder'], name='notification_user_reminder_unique'),
        ]
