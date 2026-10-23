from django.conf import settings
from django.db import models, router, transaction
from django.utils import timezone
from core.emoji import emoji_payload, validate_emoji

from .identifiers import SLUG_MAX_LENGTH, unique_dashboard_slug


class SavedTaskFilter(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Prywatny'
        SELECTED = 'selected', 'Wybrane osoby'
        WORKSPACE = 'workspace', 'Cały Workspace'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workspace_task_filters')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='task_filters')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_task_filters')
    name = models.CharField('Nazwa', max_length=150)
    description = models.TextField('Opis', blank=True, max_length=2000)
    query = models.TextField('Warunki wyszukiwania', blank=True, max_length=4000)
    visibility = models.CharField('Widoczność', max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE)
    shared_with = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='shared_task_filters')
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='favorite_task_filters')
    revision = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'pk']
        indexes = [models.Index(fields=['owner', 'workplace'], name='task_filter_workspace_idx')]

    def __str__(self):
        return self.name


class Dashboard(models.Model):
    class Icon(models.TextChoices):
        DASHBOARD = 'layout-dashboard', 'Pulpit'
        CHART = 'chart-no-axes-combined', 'Wykres'
        PEOPLE = 'users', 'Zespół'
        SPACES = 'layers', 'Przestrzenie'
        CALENDAR = 'calendar-days', 'Kalendarz'
        FOLDER = 'folder', 'Folder'
        STAR = 'star', 'Gwiazdka'
        DOCUMENT = 'file-text', 'Dokument'

        @property
        def emoji(self):
            return emoji_payload(self.value)['value']

    class DataScope(models.TextChoices):
        WORKSPACE = 'workspace', 'Cały Workspace'
        SPACES = 'spaces', 'Wybrane Przestrzenie'
        FILTER = 'filter', 'Zapisany filtr'

    class RefreshInterval(models.IntegerChoices):
        OFF = 0, 'Wyłączone'
        MINUTE = 60, 'Co minutę'
        FIVE_MINUTES = 300, 'Co 5 minut'
        FIFTEEN_MINUTES = 900, 'Co 15 minut'

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
    slug = models.SlugField(max_length=SLUG_MAX_LENGTH, editable=False)
    description = models.TextField('Opis', blank=True, max_length=2000)
    icon = models.CharField('Ikona', max_length=32, validators=[validate_emoji], default=Icon.DASHBOARD)
    data_scope = models.CharField('Zakres danych', max_length=12, choices=DataScope.choices, default=DataScope.WORKSPACE)
    scope_spaces = models.ManyToManyField('spaces.Space', blank=True, related_name='scoped_dashboards', verbose_name='Przestrzenie')
    scope_filter = models.ForeignKey(SavedTaskFilter, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='scoped_dashboards', verbose_name='Zapisany filtr')
    refresh_interval = models.PositiveSmallIntegerField('Automatyczne odświeżanie', choices=RefreshInterval.choices, default=RefreshInterval.OFF)
    visibility = models.CharField('Widoczność', max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE)
    shared_with = models.ManyToManyField(settings.AUTH_USER_MODEL, through='DashboardMembership', blank=True, related_name='shared_dashboards')
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='favorite_dashboards')
    layout = models.CharField('Układ', max_length=6, choices=Layout.choices, default=Layout.EQUAL)
    revision = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'pk']
        indexes = [models.Index(fields=['owner', 'workplace'], name='dashboard_workspace_idx')]
        constraints = [
            models.UniqueConstraint(fields=['workplace', 'slug'], name='dashboard_workspace_slug'),
            models.UniqueConstraint(
                fields=['created_by', 'workplace'], condition=models.Q(is_default=True),
                name='dashboard_default_per_user',
            ),
        ]

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if self.slug or (update_fields is not None and not update_fields):
            return super().save(*args, **kwargs)
        database = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=database):
            from workplaces.models import Workplace
            # Serialize allocation across creators, including duplicate names.
            Workplace.objects.using(database).select_for_update().get(pk=self.workplace_id)
            siblings = type(self).objects.using(database).filter(workplace_id=self.workplace_id).exclude(pk=self.pk)
            self.slug = unique_dashboard_slug(siblings, self.name)
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'slug'}
            return super().save(*args, **kwargs)

    @property
    def icon_emoji(self):
        return emoji_payload(self.icon)['value']

    @property
    def icon_emoji_art(self):
        return emoji_payload(self.icon)['art']

    @property
    def column_count(self):
        return 1 if self.layout == self.Layout.SINGLE else 3 if self.layout == self.Layout.THREE else 2

    def __str__(self):
        return self.name


class DashboardMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        MEMBER = 'member', 'Członek'
        OBSERVER = 'observer', 'Obserwator'

    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OBSERVER, db_default=Role.OBSERVER)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    class Meta:
        # Retain the existing M2M table, relation IDs and unique pair constraint.
        db_table = 'dashboard_dashboard_shared_with'
        unique_together = [('dashboard', 'user')]
        constraints = [models.CheckConstraint(condition=models.Q(role__in=['admin', 'member', 'observer']),
                                              name='dashboard_member_role_valid')]


class DashboardGadget(models.Model):
    class Kind(models.TextChoices):
        PROGRESS = 'progress', 'Postęp pracy'

    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='gadgets')
    kind = models.CharField('Gadżet', max_length=12, choices=Kind.choices, default=Kind.PROGRESS)
    title = models.CharField('Tytuł', max_length=150, blank=True)
    space = models.ForeignKey('spaces.Space', on_delete=models.CASCADE, null=True, blank=True, verbose_name='Przestrzeń')
    assignee = models.CharField('Przypisanie', max_length=10, default='all')
    column = models.PositiveSmallIntegerField(default=0)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['column', 'position', 'pk']
        constraints = [models.CheckConstraint(condition=models.Q(column__lte=2), name='dashboard_gadget_column')]

    @property
    def label(self):
        return self.title or self.get_kind_display()


class NotificationState(models.Model):
    """Personal inbox state; source records remain the authority for access/content."""

    space_activity = models.ForeignKey('spaces.SpaceTaskActivity', null=True, blank=True, on_delete=models.CASCADE)
    space_reminder = models.ForeignKey('spaces.SpaceTaskReminder', null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    invitation = models.ForeignKey('workplaces.WorkplaceInvitation', null=True, blank=True, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(
                models.Q(space_activity__isnull=False, space_reminder__isnull=True, invitation__isnull=True)
                | models.Q(space_activity__isnull=True, space_reminder__isnull=False, invitation__isnull=True)
                | models.Q(space_activity__isnull=True, space_reminder__isnull=True, invitation__isnull=False)
            ), name='notification_exactly_one_source'),
            models.UniqueConstraint(fields=['user', 'invitation'], name='notification_user_invite_unique'),
            models.UniqueConstraint(fields=['user', 'space_activity'], name='notification_user_space_activity_unique'),
            models.UniqueConstraint(fields=['user', 'space_reminder'], name='notification_user_space_reminder_unique'),
        ]
