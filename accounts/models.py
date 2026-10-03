import re

from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.functions import Lower
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify

from .avatar_presets import AVATARS


PUBLIC_USERNAME_RE = re.compile(r'^@[a-z0-9][a-z0-9._-]{2,148}$')


class User(AbstractUser):
    class PresenceStatus(models.TextChoices):
        ACTIVE = 'active', 'Aktywny'
        INACTIVE = 'inactive', 'Nieaktywny'
        OUT_OF_OFFICE = 'out_of_office', 'Poza biurem'
        BUSY = 'busy', 'Zajęty'
        DO_NOT_DISTURB = 'do_not_disturb', 'Nie przeszkadzać'

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    middle_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150)
    avatar = models.CharField(max_length=32, blank=True, choices=AVATARS)
    profile_photo = models.FileField(
        upload_to='profile_photos/',
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    phone_number = models.CharField(max_length=32, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    presence_status = models.CharField(
        max_length=20,
        choices=PresenceStatus.choices,
        default=PresenceStatus.INACTIVE,
    )
    last_seen_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(Lower('email'), name='accounts_user_email_ci_unique'),
        ]

    @property
    def presence_status_class(self):
        return f'presence-{self.presence_status}'

    def get_full_name(self):
        return ' '.join(
            part.strip()
            for part in [self.first_name, self.middle_name, self.last_name]
            if part and part.strip()
        )

    def __str__(self):
        return self.email


def normalize_public_username(value):
    normalized = (value or '').strip().lower()
    normalized = ''.join(normalized.split())
    if normalized and not normalized.startswith('@'):
        normalized = f'@{normalized}'
    return normalized


def default_public_username(first_name='', last_name='', email=''):
    name_parts = [slugify(first_name or ''), slugify(last_name or '')]
    base = '.'.join(part for part in name_parts if part)

    if not base and email:
        email_local_part = email.split('@', 1)[0].replace('.', ' ')
        base = slugify(email_local_part).replace('-', '.')

    return normalize_public_username(base or 'uzytkownik')


def _sanitize_public_username(value):
    username = normalize_public_username(value)
    stem = username[1:] if username.startswith('@') else username
    stem = re.sub(r'[^a-z0-9._-]+', '', stem).strip('._-')
    if 0 < len(stem) < 3:
        stem = f'{stem}user'[:3]
    return f'@{stem or "uzytkownik"}'


def unique_public_username(base_username, exclude_pk=None):
    username = _sanitize_public_username(base_username)
    stem = username[1:150]
    counter = 1

    while True:
        suffix = '' if counter == 1 else str(counter)
        max_stem_length = 149 - len(suffix)
        candidate = f'@{stem[:max_stem_length]}{suffix}'
        users = User.objects.filter(username__iexact=candidate)

        if exclude_pk is not None:
            users = users.exclude(pk=exclude_pk)

        if not users.exists():
            return candidate

        counter += 1
