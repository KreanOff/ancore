from django.conf import settings
from django.db import models


class Dashboard(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Prywatny'
        SELECTED = 'selected', 'Wybrane osoby'
        WORKSPACE = 'workspace', 'Cały Workspace'

    class Layout(models.TextChoices):
        SINGLE = 'single', 'Jedna kolumna'
        EQUAL = 'equal', 'Dwie równe kolumny'
        LEFT = 'left', 'Szersza lewa kolumna'
        RIGHT = 'right', 'Szersza prawa kolumna'
        THREE = 'three', 'Trzy kolumny'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workspace_dashboards')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='dashboards')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_dashboards')
    name = models.CharField('Nazwa', max_length=150)
    description = models.TextField('Opis', blank=True, max_length=2000)
    visibility = models.CharField('Widoczność', max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE)
    shared_with = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='shared_dashboards')
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='favorite_dashboards')
    layout = models.CharField('Układ', max_length=6, choices=Layout.choices, default=Layout.EQUAL)
    revision = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'pk']
        indexes = [models.Index(fields=['owner', 'workplace'], name='dashboard_workspace_idx')]

    @property
    def column_count(self):
        return 1 if self.layout == self.Layout.SINGLE else 3 if self.layout == self.Layout.THREE else 2

    def __str__(self):
        return self.name


class DashboardGadget(models.Model):
    class Kind(models.TextChoices):
        ASSIGNED = 'assigned', 'Przypisane do mnie'
        RESULTS = 'results', 'Wyniki filtra'
        SUMMARY = 'summary', 'Podsumowanie zadań'
        STATISTICS = 'statistics', 'Statystyki zadań'
        ACTIVITY = 'activity', 'Ostatnia aktywność'

    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='gadgets')
    kind = models.CharField('Gadżet', max_length=12, choices=Kind.choices)
    title = models.CharField('Tytuł', max_length=150, blank=True)
    space = models.ForeignKey('spaces.Space', on_delete=models.CASCADE, null=True, blank=True, verbose_name='Przestrzeń')
    status = models.CharField('Status', max_length=20, blank=True)
    assignee = models.CharField('Przypisanie', max_length=10, default='all')
    group_by = models.CharField('Grupowanie statystyk', max_length=10, default='status')
    limit = models.PositiveSmallIntegerField('Liczba wyników', default=10)
    column = models.PositiveSmallIntegerField(default=0)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['column', 'position', 'pk']
        constraints = [models.CheckConstraint(condition=models.Q(column__lte=2), name='dashboard_gadget_column')]

    @property
    def label(self):
        return self.title or self.get_kind_display()


class ObjectFollow(models.Model):
    """Personal subscription; access still comes exclusively from Workspace."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task = models.ForeignKey('tasks.Task', null=True, blank=True, on_delete=models.CASCADE)
    kanban = models.ForeignKey('kanban.Kanban', null=True, blank=True, on_delete=models.CASCADE)
    task_project = models.ForeignKey('tasks.TaskProject', null=True, blank=True, on_delete=models.CASCADE)
    kanban_project = models.ForeignKey('kanban.KanbanProject', null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(
                models.Q(task__isnull=False, kanban__isnull=True, task_project__isnull=True, kanban_project__isnull=True)
                | models.Q(task__isnull=True, kanban__isnull=False, task_project__isnull=True, kanban_project__isnull=True)
                | models.Q(task__isnull=True, kanban__isnull=True, task_project__isnull=False, kanban_project__isnull=True)
                | models.Q(task__isnull=True, kanban__isnull=True, task_project__isnull=True, kanban_project__isnull=False)
            ), name='follow_exactly_one_object'),
            models.UniqueConstraint(fields=['user', 'task'], name='follow_user_task_unique'),
            models.UniqueConstraint(fields=['user', 'kanban'], name='follow_user_kanban_unique'),
            models.UniqueConstraint(fields=['user', 'task_project'], name='follow_user_project_unique'),
            models.UniqueConstraint(fields=['user', 'kanban_project'], name='follow_user_kproject_unique'),
        ]


class ActivityInterest(models.Model):
    """Why an existing activity was delivered; one inbox entry even for both reasons."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task_activity = models.ForeignKey('tasks.TaskActivity', null=True, blank=True, on_delete=models.CASCADE)
    kanban_activity = models.ForeignKey('kanban.KanbanActivity', null=True, blank=True, on_delete=models.CASCADE)
    mentioned = models.BooleanField(default=False)
    followed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(
                models.Q(task_activity__isnull=False, kanban_activity__isnull=True)
                | models.Q(task_activity__isnull=True, kanban_activity__isnull=False)
            ), name='interest_exactly_one_activity'),
            models.UniqueConstraint(fields=['user', 'task_activity'], name='interest_user_task_unique'),
            models.UniqueConstraint(fields=['user', 'kanban_activity'], name='interest_user_kanban_unique'),
        ]


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
    section_invitation = models.ForeignKey('tasks.TaskSectionInvitation', null=True, blank=True, on_delete=models.CASCADE)
    project_invitation = models.ForeignKey('tasks.TaskProjectInvitation', null=True, blank=True, on_delete=models.CASCADE)
    reminder = models.ForeignKey(TaskReminder, null=True, blank=True, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(task_activity__isnull=False, kanban_activity__isnull=True, invitation__isnull=True, reminder__isnull=True, project_invitation__isnull=True, section_invitation__isnull=True)
                    | models.Q(task_activity__isnull=True, kanban_activity__isnull=False, invitation__isnull=True, reminder__isnull=True, project_invitation__isnull=True, section_invitation__isnull=True)
                    | models.Q(task_activity__isnull=True, kanban_activity__isnull=True, invitation__isnull=False, reminder__isnull=True, project_invitation__isnull=True, section_invitation__isnull=True)
                    | models.Q(task_activity__isnull=True, kanban_activity__isnull=True, invitation__isnull=True, reminder__isnull=False, project_invitation__isnull=True, section_invitation__isnull=True)
                    | models.Q(task_activity__isnull=True, kanban_activity__isnull=True, invitation__isnull=True, reminder__isnull=True, project_invitation__isnull=False, section_invitation__isnull=True)
                    | models.Q(task_activity__isnull=True, kanban_activity__isnull=True, invitation__isnull=True, reminder__isnull=True, project_invitation__isnull=True, section_invitation__isnull=False)
                ),
                name='notification_exactly_one_source',
            ),
            models.UniqueConstraint(fields=['user', 'task_activity'], name='notification_user_task_unique'),
            models.UniqueConstraint(fields=['user', 'kanban_activity'], name='notification_user_kanban_unique'),
            models.UniqueConstraint(fields=['user', 'invitation'], name='notification_user_invite_unique'),
            models.UniqueConstraint(fields=['user', 'section_invitation'], name='notification_user_section_invite_unique'),
            models.UniqueConstraint(fields=['user', 'project_invitation'], name='notification_user_project_invite_unique'),
            models.UniqueConstraint(fields=['user', 'reminder'], name='notification_user_reminder_unique'),
        ]
