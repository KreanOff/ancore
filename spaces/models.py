from django.conf import settings
from django.db import models, router, transaction
from django.db.models import Q
from core.comment_images import comment_image_storage

from .defaults import KINDS, MANAGEMENT, TEMPLATES, issue_type_icon, template_settings
from .avatars import avatar_upload_path
from .identifiers import SLUG_MAX_LENGTH, unique_space_slug


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
    slug = models.SlugField(max_length=SLUG_MAX_LENGTH, editable=False)
    kind = models.CharField(max_length=12, choices=KINDS, default='business')
    template = models.CharField(max_length=20, choices=[(k, v['label']) for k, v in TEMPLATES.items()], default='tasks')
    management = models.CharField(max_length=8, choices=MANAGEMENT, default='team')
    configuration = models.ForeignKey(SpaceConfiguration, on_delete=models.RESTRICT, related_name='spaces')
    next_number = models.PositiveIntegerField(default=1)
    avatar = models.CharField(max_length=32, blank=True, default='')
    avatar_photo = models.FileField(upload_to=avatar_upload_path, storage=comment_image_storage, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['workplace', 'key'], name='space_key_unique'),
            models.UniqueConstraint(fields=['workplace', 'slug'], name='space_workspace_slug'),
        ]

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if self.slug or (update_fields is not None and not update_fields):
            return super().save(*args, **kwargs)
        database = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=database):
            from workplaces.models import Workplace
            Workplace.objects.using(database).select_for_update().get(pk=self.workplace_id)
            siblings = type(self).objects.using(database).filter(workplace_id=self.workplace_id).exclude(pk=self.pk)
            self.slug = unique_space_slug(siblings, self.project.name)
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'slug'}
            return super().save(*args, **kwargs)

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

    def get_work_type_display(self):
        settings = self.space.configuration.settings if self.space_id else template_settings()
        return next((row['label'] for row in settings['types'] if row['key'] == self.work_type), self.work_type)

    @property
    def type_icon(self):
        return issue_type_icon(self.work_type)

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
