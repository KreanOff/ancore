from django.db import models
from django.db.models import Max
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.apps import apps
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.utils.formats import date_format
import os
import secrets
import string
import re


class TaskProject(models.Model):
    PRIORITY_CHOICES = [
        ('none', 'Brak'),
        ('low', 'Niski'),
        ('medium', 'Średni'),
        ('high', 'Wysoki'),
    ]

    CODE_LETTERS = string.ascii_uppercase
    CODE_DIGITS = string.digits

    ICON_COLORS = [
        {'background': '#ADD8E6', 'foreground': '#1f2328'},
        {'background': '#eaf7ef', 'foreground': '#16803f'},
        {'background': '#fff1df', 'foreground': '#c25a00'},
        {'background': '#f0eaff', 'foreground': '#7c3aed'},
        {'background': '#e8f8f6', 'foreground': '#0f766e'},
        {'background': '#ffeaf0', 'foreground': '#be185d'},
        {'background': '#f4f0e8', 'foreground': '#8b5e22'},
        {'background': '#edf1f7', 'foreground': '#475569'},
    ]

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=20, blank=True)
    icon = models.CharField(max_length=64, blank=True, default='')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='none', blank=True)
    due_at = models.DateField(null=True, blank=True)
    company = models.ForeignKey('contacts.Company', on_delete=models.SET_NULL, related_name='task_projects', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_projects')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['code'], name='unique_task_project_code'),
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

    def _generate_unique_code(self):
        existing_codes = set()
        for model in self._code_scope_models():
            queryset = model.objects.all()
            if model is self.__class__:
                queryset = queryset.exclude(pk=self.pk)
            existing_codes.update(queryset.values_list('code', flat=True))

        while True:
            letters = ''.join(secrets.choice(self.CODE_LETTERS) for _ in range(3))
            first_digits = ''.join(secrets.choice(self.CODE_DIGITS) for _ in range(4))
            second_digits = ''.join(secrets.choice(self.CODE_DIGITS) for _ in range(3))
            candidate = f'{letters}-{first_digits}-{second_digits}'
            if candidate not in existing_codes:
                return candidate

    def save(self, *args, **kwargs):
        if not self.pk or not self.code:
            self.code = self._generate_unique_code()
        self.code = self.code.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def icon_color(self):
        index_source = self.pk or 1
        return self.ICON_COLORS[(index_source - 1) % len(self.ICON_COLORS)]


class TaskSection(models.Model):
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
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='issues')
    icon = models.CharField(max_length=64, blank=True, default='')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'{self.project.name} / {self.title}'


class TaskTag(models.Model):
    CODE_PREFIX = 'TAG'
    CODE_NUMBER_WIDTH = 3

    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=20, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_tags')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_task_tag_per_user'),
            models.UniqueConstraint(fields=['user', 'code'], name='unique_task_tag_code_per_user'),
        ]

    def _generate_unique_code(self):
        year = timezone.localtime(self.created_at).year if self.created_at else timezone.localtime().year
        code_prefix = f'{self.CODE_PREFIX}-{year}-'
        existing_codes = list(
            TaskTag.objects.filter(user=self.user)
            .exclude(pk=self.pk)
            .values_list('code', flat=True)
        )
        highest_number = 0
        code_pattern = re.compile(rf'^{re.escape(code_prefix)}(\d+)$')

        for code in existing_codes:
            match = code_pattern.match(code or '')
            if match:
                highest_number = max(highest_number, int(match.group(1)))

        next_number = highest_number + 1
        while True:
            candidate = f'{code_prefix}{next_number:0{self.CODE_NUMBER_WIDTH}d}'
            if candidate not in existing_codes:
                return candidate
            next_number += 1

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_unique_code()
        self.code = self.code.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


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

    task_id = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    time_spent_hours = models.PositiveIntegerField(null=True, blank=True)
    time_spent_minutes = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(59)])
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    section = models.ForeignKey(TaskSection, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    tags = models.ManyToManyField(TaskTag, related_name='tasks', blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='subtasks', null=True, blank=True)

    def save(self, *args, **kwargs):
        from django.utils import timezone
        
        # Get original status if this is an update
        if self.pk:
            try:
                original_task = Task.objects.get(pk=self.pk)
                original_status = original_task.status
            except Task.DoesNotExist:
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
            
        if not self.pk or self.task_id == 0:
            # Get the highest task_id for this user
            max_task_id = Task.objects.filter(user=self.user).aggregate(Max('task_id'))['task_id__max'] or 0
            self.task_id = max_task_id + 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        # Renumber remaining tasks for this user
        self._renumber_user_tasks(user)

    @classmethod
    def _renumber_user_tasks(cls, user):
        """Renumber tasks sequentially starting from 1 for a specific user"""
        tasks = cls.objects.filter(user=user).order_by('task_id')
        for index, task in enumerate(tasks, 1):
            if task.task_id != index:
                task.task_id = index
                task.save(update_fields=['task_id'])

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
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
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


@receiver(post_delete, sender=TaskAttachment)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding TaskAttachment object is deleted.
    """
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)


@receiver(post_save, sender=Task)
def create_task_activity_on_create(sender, instance, created, **kwargs):
    if created:
        TaskActivity.objects.create(
            task=instance,
            actor=instance.user,
            kind='system',
            action='created',
            message='utworzył zadanie',
            metadata={'title': instance.title},
        )
