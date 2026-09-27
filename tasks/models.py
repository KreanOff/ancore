from datetime import UTC

from django.db import models, transaction
from django.db.models import F, Max, Q
from django.contrib.postgres.indexes import GinIndex
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.apps import apps
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.text import slugify
import os
import secrets
import string

from core.task_numbering import lock_task_numbers, renumber_tasks
from core.comment_images import CommentImage, delete_comment_image_file
from workplaces.models import invitation_expiry


BASE36_ALPHABET = string.digits + string.ascii_uppercase


PROJECT_FIELD_OPTION_DEFAULTS = {
    'status': [
        ('planned', 'Planowany', '#EEE8FF'),
        ('active', 'Aktywny', '#DFEFFF'),
        ('on_hold', 'Wstrzymany', '#FFEBC9'),
        ('completed', 'Zakończony', '#DFF1E7'),
        ('cancelled', 'Anulowany', '#E9ECF0'),
    ],
    'stage': [
        ('lead', 'Lead', '#F5E3F7'),
        ('offer', 'Oferta', '#FFE5D1'),
        ('contract', 'Umowa', '#E6E4FF'),
        ('implementation', 'Realizacja', '#DFF2F4'),
        ('support', 'Utrzymanie', '#DFF1E7'),
        ('internal', 'Wewnętrzny', '#E7EBF1'),
    ],
    'health': [
        ('ok', 'OK', '#DFF1E7'),
        ('at_risk', 'Zagrożony', '#FFEBC9'),
        ('delayed', 'Opóźniony', '#FFE0DC'),
    ],
    'source': [],
}


def format_base36(value, width=5):
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        number = 0
    if number <= 0:
        return ''

    digits = []
    while number:
        number, remainder = divmod(number, 36)
        digits.append(BASE36_ALPHABET[remainder])
    return ''.join(reversed(digits)).rjust(width, '0')


def parse_hierarchy_code_number(value, prefix):
    value = (value or '').strip().upper()
    if not value:
        return None

    token = value
    prefixed = f'{prefix}-'
    if '/' in token:
        token = next((part for part in reversed(token.split('/')) if part.startswith(prefixed)), token)
    if token.startswith(prefixed):
        token = token[len(prefixed):]

    if not token or any(character not in BASE36_ALPHABET for character in token):
        return None
    return int(token, 36)


def _add_update_field(kwargs, field_name):
    update_fields = kwargs.get('update_fields')
    if update_fields is None:
        return
    kwargs['update_fields'] = set(update_fields) | {field_name}


class TaskProject(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Publiczny'
        PRIVATE = 'private', 'Prywatny'

    visibility = models.CharField(max_length=7, choices=Visibility.choices, default=Visibility.PUBLIC)
    private_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='private_task_projects', editable=False,
    )
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='shared_task_projects', through='TaskProjectMembership',
    )

    PRIORITY_CHOICES = [
        ('none', 'Brak'),
        ('low', 'Niski'),
        ('medium', 'Średni'),
        ('high', 'Wysoki'),
        ('urgent', 'Pilny'),
    ]

    STATUS_CHOICES = [
        ('planned', 'Planowany'),
        ('active', 'Aktywny'),
        ('on_hold', 'Wstrzymany'),
        ('completed', 'Zakończony'),
        ('cancelled', 'Anulowany'),
    ]

    STAGE_CHOICES = [
        ('lead', 'Lead'),
        ('offer', 'Oferta'),
        ('contract', 'Umowa'),
        ('implementation', 'Realizacja'),
        ('support', 'Utrzymanie'),
        ('internal', 'Wewnętrzny'),
    ]

    HEALTH_CHOICES = [
        ('ok', 'OK'),
        ('at_risk', 'Zagrożony'),
        ('delayed', 'Opóźniony'),
    ]

    CODE_PREFIX = 'P'
    CODE_LENGTH = 8
    CODE_ALPHABET = BASE36_ALPHABET

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=20, blank=True)
    next_section_code_number = models.PositiveIntegerField(default=1, editable=False)
    # Legacy storage only; entity icons are no longer displayed or editable.
    icon = models.CharField(max_length=64, blank=True, default='', editable=False)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='none', blank=True)
    status = models.CharField(max_length=20, default='active')
    stage = models.CharField(max_length=20, default='implementation')
    health = models.CharField(max_length=20, default='ok')
    start_at = models.DateField(null=True, blank=True)
    due_at = models.DateField(null=True, blank=True)
    use_custom_deadline_rules = models.BooleanField(default=False)
    budget_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='PLN', blank=True)
    source = models.CharField(max_length=120, blank=True)
    company = models.ForeignKey('contacts.Company', on_delete=models.SET_NULL, related_name='task_projects', null=True, blank=True)
    responsible_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='responsible_task_projects', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_projects')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='task_projects', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['code'], condition=~Q(code=''), name='unique_task_project_code'),
        ]
        indexes = [
            models.Index(fields=['user', 'name', 'id'], name='taskproj_user_name_id_idx'),
            models.Index(fields=['user', 'priority', 'name', 'id'], name='taskproj_user_prio_name_idx'),
            GinIndex(fields=['name'], name='taskproj_name_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['description'], name='taskproj_desc_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['code'], name='taskproj_code_trgm_idx', opclasses=['gin_trgm_ops']),
        ]

    def _code_scope_models(self):
        code_models = [self.__class__]
        for app_label, model_name in (('tasks', 'TaskProject'), ('kanban', 'KanbanProject')):
            try:
                model = apps.get_model(app_label, model_name)
            except LookupError:
                continue
            if model not in code_models:
                code_models.append(model)
        return code_models

    def _code_exists(self, candidate):
        for model in self._code_scope_models():
            queryset = model.objects.filter(code=candidate)
            if model is self.__class__ and self.pk:
                queryset = queryset.exclude(pk=self.pk)
            if queryset.exists():
                return True
        return False

    def _generate_unique_code(self):
        while True:
            body = ''.join(secrets.choice(self.CODE_ALPHABET) for _ in range(self.CODE_LENGTH))
            candidate = f'{self.CODE_PREFIX}-{body}'
            if not self._code_exists(candidate):
                return candidate

    def save(self, *args, **kwargs):
        self.code = (self.code or '').strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def _field_option_display(self, field_type):
        labels = getattr(self, '_project_field_option_labels', {})
        value = getattr(self, field_type, '')
        if value in labels.get(field_type, {}):
            return labels[field_type][value]
        return dict((option_value, label) for option_value, label, _color in PROJECT_FIELD_OPTION_DEFAULTS[field_type]).get(value, value)

    def get_status_display(self):
        return self._field_option_display('status')

    def get_stage_display(self):
        return self._field_option_display('stage')

    def get_health_display(self):
        return self._field_option_display('health')


class TaskProjectMembership(models.Model):
    project = models.ForeignKey(TaskProject, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[('admin', 'Administrator'), ('member', 'Członek'), ('observer', 'Obserwator')], default='member')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['project', 'user'], name='unique_task_project_member')]


class TaskProjectInvitation(models.Model):
    project = models.ForeignKey(TaskProject, on_delete=models.CASCADE, related_name='invitations')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_invitations')
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sent_project_invitations')
    role = models.CharField(max_length=20, choices=[('admin', 'Administrator'), ('member', 'Członek'), ('observer', 'Obserwator')], default='member')
    status = models.CharField(max_length=20, choices=[('pending', 'Oczekuje'), ('accepted', 'Przyjęte'), ('declined', 'Odrzucone'), ('revoked', 'Anulowane')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=invitation_expiry)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [models.UniqueConstraint(fields=['project', 'recipient'], condition=Q(status='pending'), name='unique_pending_project_invite')]


class TaskProjectTemplate(models.Model):
    """A reusable snapshot; deleting or editing the source project does not change it."""

    visibility = models.CharField(max_length=7, choices=TaskProject.Visibility.choices, default=TaskProject.Visibility.PUBLIC)
    private_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='private_task_project_templates', editable=False,
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=120)
    template_name = models.CharField('Nazwa szablonu', max_length=120, default='')
    description = models.TextField(blank=True)
    structure = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['template_name', 'pk']

    def __str__(self):
        return self.template_name or self.name


class TaskProjectDeadlineRule(models.Model):
    DEFAULTS = ((2, '#FFE0DC'), (16, '#FFEBC9'), (30, '#DFF1E7'))

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, null=True, blank=True)
    project = models.ForeignKey(
        TaskProject, on_delete=models.CASCADE, related_name='deadline_rules', null=True, blank=True,
    )
    days = models.PositiveIntegerField(
        'Liczba dni', validators=[MinValueValidator(0), MaxValueValidator(36500)],
    )
    color = models.CharField(
        'Kolor', max_length=7, default='#DFF1E7',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Podaj kolor w formacie #RRGGBB.')],
    )
    # Retain deleted rows so removing all rules does not restore the defaults.
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['days', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'workplace', 'days'],
                condition=Q(workplace__isnull=False, project__isnull=True, is_active=True),
                name='unique_project_deadline_scope',
            ),
            models.UniqueConstraint(
                fields=['owner', 'days'],
                condition=Q(workplace__isnull=True, project__isnull=True, is_active=True),
                name='unique_project_deadline_personal',
            ),
            models.UniqueConstraint(
                fields=['project', 'days'],
                condition=Q(project__isnull=False, is_active=True),
                name='unique_project_deadline_override',
            ),
        ]

    @classmethod
    def for_scope(cls, owner, workplace=None, project=None):
        return cls.objects.filter(owner=owner, workplace=workplace, project=project)

    @classmethod
    def active_for_scope(cls, owner, workplace=None):
        scoped = cls.for_scope(owner, workplace)
        if not scoped.exists():
            cls.objects.bulk_create([
                cls(owner=owner, workplace=workplace, days=days, color=color)
                for days, color in cls.DEFAULTS
            ], ignore_conflicts=True)
        return scoped.filter(is_active=True)

    @staticmethod
    def color_for_date(due_at, rules, today=None):
        if due_at is None:
            return ''
        days_left = (due_at - (today if today is not None else timezone.localdate())).days
        rule = next((rule for rule in sorted(rules, key=lambda rule: rule.days) if days_left <= rule.days), None)
        return rule.color if rule else ''


class TaskProjectFieldOption(models.Model):
    FIELD_STATUS = 'status'
    FIELD_STAGE = 'stage'
    FIELD_HEALTH = 'health'
    FIELD_SOURCE = 'source'
    FIELD_CHOICES = [
        (FIELD_STATUS, 'Status projektu'),
        (FIELD_STAGE, 'Etap'),
        (FIELD_HEALTH, 'Kondycja'),
        (FIELD_SOURCE, 'Źródło'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_project_field_options',
    )
    workplace = models.ForeignKey(
        'workplaces.Workplace',
        on_delete=models.CASCADE,
        related_name='task_project_field_options',
        null=True,
        blank=True,
    )
    field_type = models.CharField(max_length=10, choices=FIELD_CHOICES)
    value = models.SlugField(max_length=20)
    label = models.CharField(max_length=120)
    color = models.CharField(
        max_length=7,
        default='#DFEFFF',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Podaj kolor w formacie #RRGGBB.')],
    )
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['field_type', 'position', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'workplace', 'field_type', 'value'],
                condition=Q(workplace__isnull=False),
                name='unique_project_field_option_scope',
            ),
            models.UniqueConstraint(
                fields=['owner', 'field_type', 'value'],
                condition=Q(workplace__isnull=True),
                name='unique_project_field_option_no_workplace',
            ),
        ]
        indexes = [
            models.Index(
                fields=['owner', 'workplace', 'field_type', 'is_active', 'position'],
                name='taskproj_option_scope_idx',
            ),
        ]

    def __str__(self):
        return f'{self.get_field_type_display()}: {self.label}'

    def save(self, *args, **kwargs):
        self.label = (self.label or '').strip()
        self.color = (self.color or '#DFEFFF').upper()
        with transaction.atomic():
            old_label = None
            update_fields = kwargs.get('update_fields')
            if self.pk and self.field_type == self.FIELD_SOURCE and (update_fields is None or 'label' in update_fields):
                old_label = type(self).objects.select_for_update().values_list('label', flat=True).get(pk=self.pk)
            super().save(*args, **kwargs)
            if old_label is not None and old_label != self.label:
                TaskProject.objects.filter(
                    user_id=self.owner_id, workplace_id=self.workplace_id, source=old_label,
                ).update(source=self.label)

    @property
    def project_value(self):
        # Sources retain their text storage so existing searches and imports keep working.
        return self.label if self.field_type == self.FIELD_SOURCE else self.value

    @classmethod
    def for_scope(cls, owner, workplace=None):
        return cls.objects.filter(owner=owner, workplace=workplace)

    @classmethod
    def ensure_defaults(cls, owner, workplace=None):
        scoped = cls.for_scope(owner, workplace)
        existing_fields = set(scoped.values_list('field_type', flat=True).distinct())
        options = []
        for field_type, defaults in PROJECT_FIELD_OPTION_DEFAULTS.items():
            if field_type in existing_fields:
                continue
            options.extend(
                cls(
                    owner=owner,
                    workplace=workplace,
                    field_type=field_type,
                    value=value,
                    label=label,
                    color=color,
                    position=position,
                )
                for position, (value, label, color) in enumerate(defaults)
            )
        cls.objects.bulk_create(options, ignore_conflicts=True)

    @classmethod
    def active_for_scope(cls, owner, workplace=None):
        cls.ensure_defaults(owner, workplace)
        return cls.for_scope(owner, workplace).filter(is_active=True).order_by('field_type', 'position', 'id')

    @classmethod
    def unique_value_for_label(cls, owner, workplace, field_type, label):
        base = slugify(label).replace('-', '_')[:20] or 'wartosc'
        existing_values = set(
            cls.for_scope(owner, workplace)
            .filter(field_type=field_type)
            .values_list('value', flat=True)
        )
        candidate = base
        suffix = 2
        while candidate in existing_values:
            suffix_text = f'_{suffix}'
            candidate = f'{base[:20 - len(suffix_text)]}{suffix_text}'
            suffix += 1
        return candidate

    @property
    def is_used(self):
        if self.field_type not in dict(self.FIELD_CHOICES):
            return False
        return TaskProject.objects.filter(
            user=self.owner,
            workplace=self.workplace,
            **{self.field_type: self.project_value},
        ).exists()


class TaskProjectNote(models.Model):
    project = models.ForeignKey(TaskProject, on_delete=models.CASCADE, related_name='project_notes')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='task_project_notes',
        null=True,
        blank=True,
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['project', 'created_at', 'id'], name='taskproj_note_project_idx'),
            models.Index(fields=['author', 'created_at'], name='taskproj_note_author_idx'),
        ]

    def __str__(self):
        return f'{self.project} - {self.author or "System"}'


class TaskSection(models.Model):
    PRIORITY_CHOICES = TaskProject.PRIORITY_CHOICES
    CODE_PREFIX = 'G'
    CODE_WIDTH = 5

    STATUS_CHOICES = [
        ('open', 'Otwarta'),
        ('in_progress', 'W trakcie'),
        ('ready', 'Gotowa'),
        ('blocked', 'Zablokowana'),
        ('closed', 'Zamknięta'),
    ]

    KIND_CHOICES = [
        ('issues', 'Kwestie'),
        ('components', 'Komponenty'),
        ('milestones', 'Kamienie milowe'),
        ('templates', 'Szablony'),
        ('custom', 'Własne'),
    ]

    project = models.ForeignKey(TaskProject, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=20, blank=True)
    code_number = models.PositiveIntegerField(default=0, editable=False)
    next_task_code_number = models.PositiveIntegerField(default=1, editable=False)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='none', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='issues')
    # Legacy storage only; entity icons are no longer displayed or editable.
    icon = models.CharField(max_length=64, blank=True, default='', editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='owned_task_sections', null=True, blank=True)
    due_at = models.DateField(null=True, blank=True)
    wip_limit = models.PositiveIntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['project', 'order', 'created_at'], name='tasksec_project_order_idx'),
            models.Index(fields=['project', 'code_number'], name='tasksec_project_code_idx'),
            models.Index(fields=['project', 'code'], name='tasksec_project_code_txt_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'code_number'],
                condition=Q(code_number__gt=0),
                name='unique_task_section_code_per_project',
            ),
            models.UniqueConstraint(
                fields=['project', 'code'],
                condition=~Q(code=''),
                name='unique_task_section_manual_code',
            ),
        ]

    def _claim_next_code_number(self):
        if not self.project_id:
            return 0
        with transaction.atomic():
            project = TaskProject.objects.select_for_update().only('id', 'next_section_code_number').get(pk=self.project_id)
            next_number = project.next_section_code_number or 1
            TaskProject.objects.filter(pk=project.pk).update(next_section_code_number=F('next_section_code_number') + 1)
        return next_number

    def save(self, *args, **kwargs):
        original_project_id = None
        if self.pk:
            original_project_id = TaskSection.objects.filter(pk=self.pk).values_list('project_id', flat=True).first()

        self.code = (self.code or '').strip().upper()
        if self.project_id and (not self.pk or not self.code_number or original_project_id != self.project_id):
            self.code_number = self._claim_next_code_number()
            _add_update_field(kwargs, 'code_number')
        super().save(*args, **kwargs)

    @property
    def full_code(self):
        if not self.project_id or not self.code:
            return ''
        if self.project.code:
            return f'{self.project.code}/{self.code}'
        return self.code

    def __str__(self):
        return f'{self.project.name} / {self.title}'


class TaskSectionNote(models.Model):
    section = models.ForeignKey(TaskSection, on_delete=models.CASCADE, related_name='section_notes')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='task_section_notes',
        null=True,
        blank=True,
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['section', 'created_at', 'id'], name='tasksec_note_section_idx'),
            models.Index(fields=['author', 'created_at'], name='tasksec_note_author_idx'),
        ]

    def __str__(self):
        return f'{self.section} - {self.author or "System"}'


class TaskTag(models.Model):
    CODE_PREFIX = 'T'
    CODE_LENGTH = 8
    CODE_ALPHABET = BASE36_ALPHABET
    CATEGORY_CHOICES = [
        ('general', 'Ogólny'),
        ('priority', 'Priorytet'),
        ('area', 'Obszar'),
        ('client', 'Klient'),
        ('stage', 'Etap'),
        ('risk', 'Ryzyko'),
        ('work_type', 'Typ pracy'),
    ]
    PRIORITY_CHOICES = [
        ('none', 'Brak'),
        ('low', 'Niski'),
        ('medium', 'Średni'),
        ('high', 'Wysoki'),
        ('urgent', 'Krytyczny'),
    ]
    SCOPE_CHOICES = [
        ('tasks', 'Zadania'),
        ('projects', 'Projekty'),
        ('clients', 'Klienci'),
        ('documents', 'Dokumenty'),
        ('all', 'Wszystko'),
    ]
    STATUS_CHOICES = [
        ('active', 'Aktywny'),
        ('archived', 'Archiwalny'),
    ]
    ICON_CHOICES = [
        ('tag', 'Tag'),
        ('flag', 'Flaga'),
        ('alert-triangle', 'Ryzyko'),
        ('briefcase', 'Praca'),
        ('building-2', 'Firma'),
        ('clock', 'Czas'),
        ('layers', 'Etap'),
        ('shield-alert', 'Blokada'),
        ('user-round', 'Osoba'),
        ('workflow', 'Proces'),
    ]

    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=20, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    color = models.CharField(max_length=7, default='#64748b', blank=True)
    icon = models.CharField(max_length=32, choices=ICON_CHOICES, default='tag', blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='none', blank=True)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default='tasks')
    owner_label = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    usage_notes = models.TextField(blank=True)
    automation_rules = models.TextField(blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_tags')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='task_tags', null=True, blank=True)
    related_tags = models.ManyToManyField('self', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'workplace', 'name'], name='unique_task_tag_per_workplace'),
            models.UniqueConstraint(fields=['code'], name='unique_task_tag_code'),
        ]

    def _code_scope_models(self):
        code_models = [self.__class__]
        for app_label, model_name in (('tasks', 'TaskTag'), ('kanban', 'KanbanTag')):
            try:
                model = apps.get_model(app_label, model_name)
            except LookupError:
                continue
            if model not in code_models:
                code_models.append(model)
        return code_models

    def _code_exists(self, candidate):
        for model in self._code_scope_models():
            queryset = model.objects.filter(code=candidate)
            if model is self.__class__ and self.pk:
                queryset = queryset.exclude(pk=self.pk)
            if queryset.exists():
                return True
        return False

    def _generate_unique_code(self):
        while True:
            body = ''.join(secrets.choice(self.CODE_ALPHABET) for _ in range(self.CODE_LENGTH))
            candidate = f'{self.CODE_PREFIX}-{body}'
            if not self._code_exists(candidate):
                return candidate

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_unique_code()
        self.code = self.code.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TaskTagNote(models.Model):
    tag = models.ForeignKey(TaskTag, on_delete=models.CASCADE, related_name='tag_notes')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='task_tag_notes',
        null=True,
        blank=True,
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['tag', 'created_at', 'id'], name='tasktag_note_tag_idx'),
            models.Index(fields=['author', 'created_at'], name='tasktag_note_author_idx'),
        ]

    def __str__(self):
        return f'{self.tag} - {self.author or "System"}'


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('none', 'Brak priorytetu'),
        ('low', 'Niski'),
        ('medium', 'Średni'),
        ('high', 'Wysoki'),
        ('urgent', 'Pilny'),
    ]

    STATUS_CHOICES = [
        ('new', 'Nowe'),
        ('in_progress', 'Realizowane'),
        ('resolved', 'Rozwiązane'),
        ('closed', 'Zamknięte'),
        ('reopened', 'Ponownie otwarte'),
    ]

    TASK_TYPE_CHOICES = [
        ('general', 'Ogólne'),
        ('call', 'Telefon'),
        ('email', 'E-mail'),
        ('meeting', 'Spotkanie'),
        ('offer', 'Oferta'),
        ('invoice', 'Faktura'),
        ('complaint', 'Reklamacja'),
        ('onboarding', 'Onboarding'),
        ('internal', 'Wewnętrzne'),
    ]

    task_id = models.PositiveIntegerField(default=0)
    code_number = models.PositiveIntegerField(default=0, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    reminder_at = models.DateTimeField(null=True, blank=True)
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    time_spent_hours = models.PositiveIntegerField(null=True, blank=True)
    time_spent_minutes = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(59)])
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, default='general')
    blocked_reason = models.TextField(blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='assigned_tasks', null=True, blank=True)
    section = models.ForeignKey(TaskSection, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    tags = models.ManyToManyField(TaskTag, related_name='tasks', blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='subtasks', null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['section', 'parent', 'created_at'], name='task_section_parent_idx'),
            models.Index(fields=['user', 'task_id'], name='task_user_task_id_idx'),
            models.Index(fields=['user', 'workplace', 'task_id'], name='task_user_workspace_id_idx'),
            models.Index(fields=['section', 'code_number'], name='task_section_code_idx'),
            models.Index(fields=['user', 'assignee', 'status'], name='task_user_assignee_status_idx'),
            models.Index(fields=['user', 'task_type', 'status'], name='task_user_type_status_idx'),
            models.Index(fields=['user', 'reminder_at'], name='task_user_reminder_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'workplace', 'task_id'],
                name='unique_tasks_number_per_workspace',
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.UniqueConstraint(
                fields=['section', 'code_number'],
                condition=Q(section__isnull=False, code_number__gt=0),
                name='unique_task_code_per_section',
            ),
        ]

    def _claim_next_code_number(self):
        if not self.section_id:
            return 0
        with transaction.atomic():
            section = TaskSection.objects.select_for_update().only('id', 'next_task_code_number').get(pk=self.section_id)
            next_number = section.next_task_code_number or 1
            TaskSection.objects.filter(pk=section.pk).update(next_task_code_number=F('next_task_code_number') + 1)
        return next_number

    def save(self, *args, **kwargs):
        with lock_task_numbers(self.user_id, using=kwargs.get('using') or self._state.db):
            from django.utils import timezone

            # Get original status and the current number while holding the owner lock.
            original_task = None
            if self.pk:
                try:
                    original_task = Task.objects.get(pk=self.pk)
                    self.task_id = original_task.task_id
                    original_status = original_task.status
                    original_section_id = original_task.section_id
                except Task.DoesNotExist:
                    original_status = None
                    original_section_id = None
            else:
                original_status = None
                original_section_id = None

            # Set completion_date when status changes to 'closed'
            if self.status == 'closed' and original_status != 'closed':
                self.completion_date = timezone.now()
                self.is_completed = True
            elif self.status != 'closed' and original_status == 'closed':
                self.completion_date = None
                self.is_completed = False

            if self.section_id and (not self.pk or not self.code_number or original_section_id != self.section_id):
                self.code_number = self._claim_next_code_number()
                _add_update_field(kwargs, 'code_number')
            elif not self.section_id and self.code_number:
                self.code_number = 0
                _add_update_field(kwargs, 'code_number')

            if self.section_id:
                section_workplace_id = self.section.project.workplace_id
                if self.workplace_id != section_workplace_id:
                    self.workplace_id = section_workplace_id
                    _add_update_field(kwargs, 'workplace')

            if not self.pk or self.task_id == 0 or (original_task and original_task.workplace_id != self.workplace_id):
                task_scope = Task.objects.filter(user_id=self.user_id, workplace_id=self.workplace_id)
                max_task_id = task_scope.aggregate(Max('task_id'))['task_id__max'] or 0
                self.task_id = max_task_id + 1
                if kwargs.get('update_fields') is not None:
                    kwargs['update_fields'] = set(kwargs['update_fields']) | {'task_id'}
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        using = kwargs.get('using') or self._state.db
        with lock_task_numbers(self.user_id, using=using):
            user, workplace = self.user, self.workplace
            result = super().delete(*args, **kwargs)
            renumber_tasks(type(self), user, workplace, using=using)
            return result

    @classmethod
    def _renumber_user_tasks(cls, user, workplace=None):
        renumber_tasks(cls, user, workplace)

    def __str__(self):
        return self.title

    @property
    def code(self):
        return str(self.task_id) if self.task_id else ''

    @property
    def full_code(self):
        return self.code

    def _activity_datetime(self, value):
        if not value:
            return ''
        return date_format(timezone.localtime(value), 'd.m.Y H:i')

    def _activity_time_spent(self):
        hours = self.time_spent_hours or 0
        minutes = self.time_spent_minutes or 0
        if not hours and not minutes:
            return '00:00'
        return f'{hours:02d}:{minutes:02d}'

    @property
    def has_time_spent(self):
        return bool((self.time_spent_hours or 0) or (self.time_spent_minutes or 0))

    @property
    def time_spent_label(self):
        return self._activity_time_spent()

    @property
    def due_urgency(self):
        if not self.due_at:
            return 'none'

        seconds_left = (self.due_at - timezone.now()).total_seconds()
        if seconds_left <= 24 * 60 * 60:
            return 'red'
        if seconds_left <= 3 * 24 * 60 * 60:
            return 'yellow'
        return 'green'

    def get_file_extension(self):
        """Return file extension for icon selection"""
        if self.attachments.exists():
            first_attachment = self.attachments.first()
            return os.path.splitext(first_attachment.file.name)[1].lower()
        return ''


class TaskWorkLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='work_logs')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='task_work_logs')
    started_at = models.DateTimeField('Data i godzina rozpoczęcia')
    ended_at = models.DateTimeField('Data i godzina zakończenia')
    description = models.TextField('Opis', max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at', '-pk']
        indexes = [models.Index(fields=['task', '-started_at', '-id'], name='task_worklog_order_idx')]
        constraints = [models.CheckConstraint(condition=Q(ended_at__gt=F('started_at')), name='task_worklog_positive_time')]

    @property
    def duration_minutes(self):
        return int((self.ended_at.astimezone(UTC) - self.started_at.astimezone(UTC)).total_seconds() // 60)

    def __str__(self):
        return f'{self.task} — {self.duration_minutes} min'


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.PositiveIntegerField(default=0)  # Size in bytes

    def save(self, *args, **kwargs):
        if self.file:
            # Set filename from the uploaded file
            self.filename = os.path.basename(self.file.name)
            # Set file size
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def get_file_extension(self):
        """Return file extension for icon selection"""
        return os.path.splitext(self.filename)[1].lower()

    def is_image(self):
        """Check if the file is an image"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        return self.get_file_extension() in image_extensions

    def is_pdf(self):
        """Check if the file is a PDF"""
        return self.get_file_extension() == '.pdf'

    def get_type_class(self):
        """Return CSS class based on file type"""
        ext = self.get_file_extension()
        if self.is_image(): return 'image'
        if ext == '.pdf': return 'pdf'
        if ext in ['.doc', '.docx', '.xls', '.xlsx', '.txt', '.rtf']: return 'document'
        if ext in ['.zip', '.rar', '.7z', '.tar', '.gz']: return 'archive'
        return 'default'

    def get_type_label(self):
        """Return text label for the icon badge"""
        ext = self.get_file_extension()
        if self.is_image(): return 'IMG'
        if ext == '.pdf': return 'PDF'
        if ext in ['.doc', '.docx', '.xls', '.xlsx', '.txt', '.rtf']: return 'DOC'
        if ext in ['.zip', '.rar', '.7z', '.tar', '.gz']: return 'ZIP'
        return 'FILE'

    def get_formatted_size(self):
        """Return human-readable file size"""
        size = float(self.file_size)
        if size == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        return f"{size:.1f} {size_names[i]}"

    def __str__(self):
        return f"{self.filename} - {self.task.title}"


class TaskActivity(models.Model):
    KIND_CHOICES = [
        ('system', 'Historia'),
        ('comment', 'Komentarz'),
    ]

    ACTION_CHOICES = [
        ('created', 'Utworzono zadanie'),
        ('updated', 'Zaktualizowano zadanie'),
        ('status_changed', 'Zmieniono status'),
        ('priority_changed', 'Zmieniono priorytet'),
        ('commented', 'Dodano komentarz'),
        ('subtask_created', 'Dodano podzadanie'),
        ('attachments_added', 'Dodano załączniki'),
        ('attachments_deleted', 'Usunięto załączniki'),
        ('work_log_added', 'Dodano wpis czasu'),
        ('work_log_updated', 'Zmieniono wpis czasu'),
        ('work_log_deleted', 'Usunięto wpis czasu'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='task_activities', null=True, blank=True)
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default='system')
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, default='updated')
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'{self.get_action_display()} - {self.task}'


class TaskCommentImage(CommentImage):
    activity = models.ForeignKey(TaskActivity, on_delete=models.CASCADE, related_name='images')


post_delete.connect(delete_comment_image_file, sender=TaskCommentImage)


@receiver(post_delete, sender=TaskAttachment)
def auto_delete_file_on_delete(sender, instance, using, **kwargs):
    """Keep the file if the surrounding deletion is rolled back."""
    if instance.file:
        storage, name = instance.file.storage, instance.file.name
        transaction.on_commit(lambda: storage.delete(name), using=using, robust=True)


@receiver(post_save, sender=Task)
def create_task_activity_on_create(sender, instance, created, **kwargs):
    if created:
        TaskActivity.objects.create(
            task=instance,
            actor=getattr(instance, '_activity_actor', instance.user),
            kind='system',
            action='created',
            message='utworzył zadanie',
            metadata={'title': instance.title},
        )
