"""Tags and tag notes belonging to current Spaces."""
import secrets
import string

from django.conf import settings
from django.db import models

BASE36_ALPHABET = string.digits + string.ascii_uppercase


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
    space = models.ForeignKey('spaces.Space', on_delete=models.CASCADE, related_name='tags', null=True, blank=True)
    related_tags = models.ManyToManyField('self', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'workplace', 'name'], condition=models.Q(space__isnull=True), name='unique_task_tag_per_workplace'),
            models.UniqueConstraint(fields=['space', 'name'], condition=models.Q(space__isnull=False), name='unique_task_tag_per_space'),
            models.UniqueConstraint(fields=['code'], name='unique_task_tag_code'),
        ]

    def _code_exists(self, candidate):
        return type(self).objects.filter(code=candidate).exclude(pk=self.pk).exists()

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
