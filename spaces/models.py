from django.conf import settings
from django.db import models
from django.db.models import Q
from core.comment_images import comment_image_storage

from .defaults import KINDS, MANAGEMENT, TEMPLATES, template_settings


class SpaceConfiguration(models.Model):
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    shared = models.BooleanField(default=False)
    settings = models.JSONField(default=template_settings)

    def __str__(self):
        return self.name


class Space(models.Model):
    """Configuration of the existing project; its ACL remains authoritative."""
    project = models.OneToOneField('tasks.TaskProject', on_delete=models.CASCADE, related_name='space')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE)
    key = models.CharField(max_length=12)
    kind = models.CharField(max_length=12, choices=KINDS, default='business')
    template = models.CharField(max_length=20, choices=[(k, v['label']) for k, v in TEMPLATES.items()], default='tasks')
    management = models.CharField(max_length=8, choices=MANAGEMENT, default='team')
    configuration = models.ForeignKey(SpaceConfiguration, on_delete=models.RESTRICT, related_name='spaces')
    next_number = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['workplace', 'key'], name='space_key_unique')]

    def __str__(self):
        return self.project.name

    @property
    def statuses(self):
        return self.configuration.settings['statuses']


class Team(models.Model):
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='teams')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_work_teams')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_work_teams')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    photo = models.FileField(upload_to='teams/', storage=comment_image_storage, blank=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='TeamMembership', related_name='work_teams')
    spaces = models.ManyToManyField(Space, blank=True, related_name='teams')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name', 'pk']
        constraints = [models.UniqueConstraint(fields=['workplace', 'name'], name='space_team_name_unique')]

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=[('admin', 'Administrator'), ('member', 'Członek')], default='member')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['team', 'user'], name='space_team_member_unique')]


class Sprint(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='sprints')
    name = models.CharField(max_length=120)
    goal = models.TextField(blank=True)
    start_on = models.DateField()
    end_on = models.DateField()
    state = models.CharField(max_length=10, choices=[('planned', 'Planowany'), ('active', 'Aktywny'), ('closed', 'Zakończony')], default='planned')
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['start_on', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['space'], condition=Q(state='active'), name='space_one_active_sprint'),
            models.CheckConstraint(condition=Q(end_on__gte=models.F('start_on')), name='space_sprint_dates'),
        ]

    def __str__(self):
        return self.name


class WorkItem(models.Model):
    """Planning metadata, never a second copy of a task or its history/files."""
    task = models.OneToOneField('tasks.Task', on_delete=models.CASCADE, related_name='work_item')
    space = models.ForeignKey(Space, on_delete=models.CASCADE, null=True, blank=True, related_name='items')
    key = models.CharField(max_length=32)
    number = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=50, default='new')
    work_type = models.CharField(max_length=40, default='task')
    rank = models.PositiveIntegerField(default=0)
    in_backlog = models.BooleanField(default=False)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    epic = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='epic_items')
    points = models.PositiveIntegerField(null=True, blank=True)
    start_on = models.DateField(null=True, blank=True)
    custom_values = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['rank', 'pk']
        constraints = [models.UniqueConstraint(fields=['space', 'number'], name='space_item_number_unique')]


class LegacyKanbanLink(models.Model):
    kind = models.CharField(max_length=20)
    source_id = models.PositiveBigIntegerField()
    target_id = models.PositiveBigIntegerField()
    space = models.ForeignKey(Space, on_delete=models.SET_NULL, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['kind', 'source_id'], name='space_legacy_kanban_unique')]
