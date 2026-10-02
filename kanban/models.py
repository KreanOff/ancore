from django.db import models, transaction
from django.db.models import Max
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.apps import apps
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.utils.formats import date_format
from tasks.models import TaskTag, TaskTagNote
import os
import secrets
import string

from core.task_numbering import lock_task_numbers, renumber_tasks
from core.comment_images import CommentImage, delete_comment_image_file


BASE36_ALPHABET = string.digits + string.ascii_uppercase
KanbanTag = TaskTag
KanbanTagNote = TaskTagNote


class KanbanProject(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Publiczna'
        PRIVATE = 'private', 'Prywatna'

    visibility = models.CharField(max_length=7, choices=Visibility.choices, default=Visibility.PUBLIC)
    private_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='private_kanban_projects', editable=False,
    )
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='shared_kanban_projects', through='KanbanProjectMembership',
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
    # Legacy storage only; entity icons are no longer displayed or editable.
    icon = models.CharField(max_length=64, blank=True, default='', editable=False)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='none', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='implementation')
    health = models.CharField(max_length=20, choices=HEALTH_CHOICES, default='ok')
    start_at = models.DateField(null=True, blank=True)
    due_at = models.DateField(null=True, blank=True)
    budget_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='PLN', blank=True)
    source = models.CharField(max_length=120, blank=True)
    company = models.ForeignKey('contacts.Company', on_delete=models.SET_NULL, related_name='kanban_projects', null=True, blank=True)
    responsible_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='responsible_kanban_projects', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='kanban_projects')
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='favorite_kanban_projects')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='kanban_projects', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['code'], name='unique_kanban_project_code'),
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
        if not self.pk or not self.code:
            self.code = self._generate_unique_code()
        self.code = self.code.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class KanbanProjectNote(models.Model):
    project = models.ForeignKey(KanbanProject, on_delete=models.CASCADE, related_name='project_notes')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='kanban_project_notes',
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
            models.Index(fields=['project', 'created_at', 'id'], name='kanbanproj_note_project_idx'),
            models.Index(fields=['author', 'created_at'], name='kanbanproj_note_author_idx'),
        ]

    def __str__(self):
        return f'{self.project} - {self.author or "System"}'


class KanbanSection(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Publiczna'
        PRIVATE = 'private', 'Prywatna'

    visibility = models.CharField(max_length=7, choices=Visibility.choices, default=Visibility.PUBLIC)
    private_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='private_kanban_sections', editable=False,
    )
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='shared_kanban_sections', through='KanbanSectionMembership',
    )

    KIND_CHOICES = [
        ('issues', 'Kwestie'),
        ('components', 'Komponenty'),
        ('milestones', 'Kamienie milowe'),
        ('templates', 'Szablony'),
        ('custom', 'Własne'),
    ]

    project = models.ForeignKey(KanbanProject, on_delete=models.CASCADE, related_name='sections')
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='favorite_kanban_sections')
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='issues')
    # Legacy storage only; entity icons are no longer displayed or editable.
    icon = models.CharField(max_length=64, blank=True, default='', editable=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'{self.project.name} / {self.title}'


class KanbanBoardColumn(models.Model):
    section = models.ForeignKey(KanbanSection, on_delete=models.CASCADE, related_name='columns')
    title = models.CharField(max_length=80)
    order = models.PositiveIntegerField(default=0)
    is_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    @classmethod
    def ensure_defaults_for_section(cls, section):
        return

    def __str__(self):
        return self.title


class Kanban(models.Model):
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

    task_id = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='new')
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    time_spent_hours = models.PositiveIntegerField(null=True, blank=True)
    time_spent_minutes = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(59)])
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='kanban_items')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='kanban_items', null=True, blank=True)
    section = models.ForeignKey(KanbanSection, on_delete=models.SET_NULL, related_name='tasks', null=True, blank=True)
    column = models.ForeignKey(KanbanBoardColumn, on_delete=models.SET_NULL, related_name='cards', null=True, blank=True)
    tags = models.ManyToManyField(TaskTag, related_name='kanban_cards', blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='subtasks', null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'workplace', 'task_id'],
                name='unique_kanban_number_per_workspace',
                deferrable=models.Deferrable.DEFERRED,
            ),
        ]

    def save(self, *args, **kwargs):
        with lock_task_numbers(self.user_id, using=kwargs.get('using') or self._state.db):
            from django.utils import timezone

            # Get original status and the current number while holding the owner lock.
            original_task = None
            if self.pk:
                try:
                    original_task = Kanban.objects.get(pk=self.pk)
                    self.task_id = original_task.task_id
                    original_status = original_task.status
                except Kanban.DoesNotExist:
                    original_status = None
            else:
                original_status = None

            # Set completion_date when status changes to 'closed'
            if self.status == 'closed' and original_status != 'closed':
                self.completion_date = timezone.now()
                self.is_completed = True
            elif self.status != 'closed' and original_status == 'closed':
                self.completion_date = None
                self.is_completed = False

            if self.section_id:
                if self.column_id and self.column.section_id != self.section_id:
                    self.column = None
                section_workplace_id = self.section.project.workplace_id
                if self.workplace_id != section_workplace_id:
                    self.workplace_id = section_workplace_id
                    update_fields = kwargs.get('update_fields')
                    if update_fields is not None:
                        kwargs['update_fields'] = set(update_fields) | {'workplace'}
            else:
                self.column = None

            if not self.pk or self.task_id == 0 or (original_task and original_task.workplace_id != self.workplace_id):
                task_scope = Kanban.objects.filter(user_id=self.user_id, workplace_id=self.workplace_id)
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

    def get_file_extension(self):
        """Return file extension for icon selection"""
        if self.attachments.exists():
            first_attachment = self.attachments.first()
            return os.path.splitext(first_attachment.file.name)[1].lower()
        return ''

class KanbanAttachment(models.Model):
    task = models.ForeignKey(Kanban, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='kanban_attachments/')
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


class KanbanActivity(models.Model):
    KIND_CHOICES = [
        ('system', 'Historia'),
        ('comment', 'Komentarz'),
    ]

    ACTION_CHOICES = [
        ('created', 'Utworzono kartę'),
        ('updated', 'Zaktualizowano kartę'),
        ('status_changed', 'Zmieniono status'),
        ('priority_changed', 'Zmieniono priorytet'),
        ('commented', 'Dodano komentarz'),
        ('subtask_created', 'Dodano podkartę'),
        ('attachments_added', 'Dodano załączniki'),
        ('attachments_deleted', 'Usunięto załączniki'),
    ]

    task = models.ForeignKey(Kanban, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='kanban_activities', null=True, blank=True)
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default='system')
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, default='updated')
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'{self.get_action_display()} - {self.task}'


class KanbanCommentImage(CommentImage):
    activity = models.ForeignKey(KanbanActivity, on_delete=models.CASCADE, related_name='images')


post_delete.connect(delete_comment_image_file, sender=KanbanCommentImage)


@receiver(post_delete, sender=KanbanAttachment)
def auto_delete_file_on_delete(sender, instance, using, **kwargs):
    """Keep the file if the surrounding deletion is rolled back."""
    if instance.file:
        storage, name = instance.file.storage, instance.file.name
        transaction.on_commit(lambda: storage.delete(name), using=using, robust=True)


@receiver(post_save, sender=Kanban)
def create_task_activity_on_create(sender, instance, created, **kwargs):
    if created:
        KanbanActivity.objects.create(
            task=instance,
            actor=getattr(instance, '_activity_actor', instance.user),
            kind='system',
            action='created',
            message='utworzył kartę',
            metadata={'title': instance.title},
        )


class KanbanProjectMembership(models.Model):
    project = models.ForeignKey(KanbanProject, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[('admin', 'Administrator'), ('member', 'Członek'), ('observer', 'Obserwator')], default='member')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['project', 'user'], name='unique_kanban_project_member')]


class KanbanSectionMembership(models.Model):
    section = models.ForeignKey(KanbanSection, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[('admin', 'Administrator'), ('member', 'Członek'), ('observer', 'Obserwator')], default='member')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['section', 'user'], name='unique_kanban_section_member')]
