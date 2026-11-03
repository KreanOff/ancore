from datetime import UTC
from django.conf import settings
from django.db import models, router, transaction
from django.db.models import Q
from django.utils import timezone
from core.comment_images import comment_image_storage, AttachmentPresentation

from .defaults import KINDS, MANAGEMENT, TEMPLATES, TASK_CATEGORY_CHOICES, classification_label, classification_options, configuration_name_color, issue_type_icon, template_settings
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
    """Independent workspace space."""
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_spaces')
    responsible_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='responsible_spaces')
    visibility = models.CharField(max_length=7, choices=[('public', 'Publiczna'), ('private', 'Prywatna')], default='public')
    private_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='private_spaces')
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='favorite_spaces', blank=True)
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
            self.slug = unique_space_slug(siblings, self.name)
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'slug'}
            return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def statuses(self):
        return self.configuration.settings['statuses']


class SpaceMembership(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[('admin', 'Administrator'), ('member', 'Członek'), ('observer', 'Obserwator')], default='member')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['space', 'user'], name='space_member_unique')]


class SpaceDashboardLayout(models.Model):
    """Personal arrangement of a Space's summary widgets."""
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='dashboard_layouts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='space_dashboard_layouts')
    widgets = models.JSONField(default=list, blank=True)
    revision = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['space', 'user'], name='space_dashboard_layout_user')]


class SpaceTask(models.Model):
    """Task content owned by a space, without a legacy project or group."""
    PRIORITY_CHOICES = [('none', 'Brak priorytetu'), ('low', 'Niski'), ('medium', 'Średni'), ('high', 'Wysoki'), ('urgent', 'Pilny')]
    STATUS_CHOICES = [('new', 'Nowe'), ('in_progress', 'Realizowane'), ('resolved', 'Rozwiązane'), ('closed', 'Zamknięte'), ('reopened', 'Ponownie otwarte')]
    TASK_TYPE_CHOICES = TASK_CATEGORY_CHOICES
    task_type = models.CharField(max_length=20, default='general')
    task_group = models.CharField(max_length=40, blank=True, default='')
    reminder_at = models.DateTimeField(null=True, blank=True)
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    is_completed = models.BooleanField(default=False)
    completion_date = models.DateTimeField(null=True, blank=True)
    blocked_reason = models.TextField(blank=True)
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='blocked_space_tasks')
    blocked_responsible = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='space_task_blockers')
    blocked_revision = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_space_tasks')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_space_tasks')
    due_at = models.DateTimeField(null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subtasks')
    tags = models.ManyToManyField('tasks.TaskTag', related_name='space_tasks', blank=True)
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='favorite_space_tasks', blank=True)
    visibility = models.CharField(max_length=7, choices=[('public', 'Przestrzeń'), ('private', 'Wybrane osoby')], default='public')
    private_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='private_space_tasks')

    def __str__(self):
        return self.title

    def get_task_type_display(self):
        return classification_label(self.space.configuration.settings, 'categories', self.task_type)

    def get_task_group_display(self):
        return classification_label(self.space.configuration.settings, 'groups', self.task_group)

    def save(self, *args, **kwargs):
        if self._state.adding:
            from .workflow import initial_status
            selected = initial_status(self.space, self.status, getattr(self, '_initial_status', None))
            self.status, self._initial_status = selected['category'], selected['key']
        self.is_completed = self.status == 'closed'
        self.completion_date = (self.completion_date or timezone.now()) if self.is_completed else None
        if kwargs.get('update_fields'):
            kwargs['update_fields'] = set(kwargs['update_fields']) | {'is_completed', 'completion_date'}
        with transaction.atomic():
            locked_space = Space.objects.select_for_update(of=('self',)).select_related('configuration').get(pk=self.space_id)
            if self._state.adding:
                # A task can be created from an older in-memory Space. Resolve
                # its default only after serializing with dictionary writes.
                self.space = locked_space
                categories = classification_options(locked_space.configuration.settings, 'categories')
                if self.task_type == 'general' and categories and not any(row['key'] == 'general' for row in categories):
                    self.task_type = categories[0]['key']
            from django.core.exceptions import ValidationError
            if self.pk and type(self).objects.filter(pk=self.pk).exclude(space_id=self.space_id).exists():
                raise ValidationError('Zadanie musi pozostać w swojej przestrzeni.')
            if self.parent_id and not type(self).objects.filter(pk=self.parent_id, space_id=self.space_id).exists():
                raise ValidationError('Podzadanie musi należeć do przestrzeni rodzica.')
            parent_id = self.parent_id
            visited = {self.pk} if self.pk else set()
            while parent_id:
                if parent_id in visited:
                    raise ValidationError('Zadania nie mogą tworzyć cyklu podzadań.')
                visited.add(parent_id)
                parent_id = type(self).objects.filter(pk=parent_id).values_list('parent_id', flat=True).first()
            super().save(*args, **kwargs)

    @property
    def due_urgency(self):
        return 'overdue' if self.due_at and self.due_at < timezone.now() and not self.is_completed else 'normal'


class SpaceTaskMembership(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    task = models.ForeignKey(SpaceTask, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=SpaceMembership._meta.get_field('role').choices, default='member')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['task', 'user'], name='space_task_member_unique')]


class SpaceTaskActivity(models.Model):
    task = models.ForeignKey(SpaceTask, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=12, choices=[('system', 'Historia'), ('comment', 'Komentarz')], default='system')
    action = models.CharField(max_length=32, default='updated')
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']

    def get_action_display(self):
        return {'created': 'Utworzono zadanie', 'updated': 'Zaktualizowano zadanie', 'status_changed': 'Zmieniono status', 'commented': 'Dodano komentarz'}.get(self.action, self.message)


class SpaceTaskFile(AttachmentPresentation, models.Model):
    task = models.ForeignKey(SpaceTask, on_delete=models.CASCADE, related_name='attachments')
    activity = models.ForeignKey(SpaceTaskActivity, on_delete=models.CASCADE, null=True, blank=True, related_name='images')
    file = models.FileField(upload_to='space_task_files/', storage=comment_image_storage)
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)


    def get_url(self):
        from workplaces.services import scoped_workplace_app_path
        return scoped_workplace_app_path(self.task.space.workplace, 'space', f'{self.task.space.slug}/tasks/{self.task.work_item.key}/files/{self.pk}/')


class SpaceTaskReminder(models.Model):
    task = models.ForeignKey(SpaceTask, on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    scheduled_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["task", "recipient", "scheduled_at"], name="space_reminder_delivery_unique")]


class SpaceTaskWorkLog(models.Model):
    task = models.ForeignKey(SpaceTask, on_delete=models.CASCADE, related_name='work_logs')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    started_at = models.DateTimeField('Data i godzina rozpoczęcia')
    ended_at = models.DateTimeField('Data i godzina zakończenia')
    description = models.TextField('Opis', max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at', '-pk']
        constraints = [models.CheckConstraint(condition=Q(ended_at__gt=models.F('started_at')), name='space_worklog_positive_time')]


    @property
    def duration_minutes(self):
        return int((self.ended_at.astimezone(UTC) - self.started_at.astimezone(UTC)).total_seconds() // 60)


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
    """Planning and stable space key for an independent SpaceTask."""
    task = models.OneToOneField(SpaceTask, on_delete=models.CASCADE, related_name='work_item', null=True, blank=True)
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
    start_at = models.DateTimeField(null=True, blank=True)
    custom_values = models.JSONField(default=dict, blank=True)
    status_entered_at = models.DateTimeField(null=True, blank=True)
    flow_started_at = models.DateTimeField(null=True, blank=True)
    flow_finished_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        from .workflow import update_flow_times, validate_placement
        with transaction.atomic():
            if self.space_id:
                self.space = Space.objects.select_for_update(of=('self',)).select_related('configuration').get(pk=self.space_id)
            if self.task_id and not SpaceTask.objects.filter(pk=self.task_id, space_id=self.space_id).exists():
                raise ValidationError('Planowanie musi należeć do przestrzeni zadania.')
            original = type(self).objects.filter(pk=self.pk).values(
                'space_id', 'task_id', 'key', 'number', 'status', 'in_backlog',
                'status_entered_at', 'flow_started_at', 'flow_finished_at').first() if self.pk else None
            if original and original['task_id'] and any(original[name] != getattr(self, name) for name in ('space_id', 'task_id', 'key', 'number')):
                raise ValidationError('Klucz i przestrzeń zadania są stałe.')
            if self.space_id and self.task_id:
                if original:
                    # update_fields writes only the named values. A stale rank
                    # object must never invent a status transition or old times.
                    for name in ('status', 'in_backlog'):
                        if kwargs.get('update_fields') and name not in kwargs['update_fields']:
                            setattr(self, name, original[name])
                    for name in ('status_entered_at', 'flow_started_at', 'flow_finished_at'):
                        setattr(self, name, original[name])
                validate_placement(self, original)
                update_flow_times(self, original)
                if kwargs.get('update_fields'):
                    kwargs['update_fields'] = set(kwargs['update_fields']) | {'status_entered_at', 'flow_started_at', 'flow_finished_at'}
            return super().save(*args, **kwargs)

    def get_work_type_display(self):
        settings = self.space.configuration.settings if self.space_id else template_settings()
        return next((row['label'] for row in settings['types'] if row['key'] == self.work_type), self.work_type)

    @property
    def type_color(self):
        types = self.space.configuration.settings.get('types', []) if self.space_id else []
        definition = next((row for row in types if row['key'] == self.work_type), {'key': self.work_type})
        return configuration_name_color('types', definition)

    @property
    def type_icon(self):
        types = self.space.configuration.settings.get('types', []) if self.space_id else []
        configured = next((row.get('icon') for row in types if row['key'] == self.work_type), None)
        return issue_type_icon(self.work_type, configured)

    class Meta:
        ordering = ['rank', 'pk']
        constraints = [models.UniqueConstraint(fields=['space', 'number'], name='space_item_number_unique')]
