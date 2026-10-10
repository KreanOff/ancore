import secrets
import string

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import IntegrityError, models, router, transaction
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta


def generate_workplace_code():
    return 'w_' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(26))


class Workplace(models.Model):
    name = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=28, default=generate_workplace_code, editable=False)
    slug = models.SlugField(max_length=160, blank=True, unique=True, editable=False)
    legacy_slug = models.SlugField(max_length=160, blank=True, null=True, unique=True, editable=False)
    avatar = models.CharField(max_length=32, blank=True, default='')
    workplace_photo = models.FileField(
        blank=True,
        upload_to='workplace_photos/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_workplaces',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='WorkplaceMembership',
        related_name='workplaces',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(fields=['code'], name='unique_workplace_code'),
        ]

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_workplace_code()
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields'] = set(kwargs['update_fields']) | {'code'}
        if not self.slug:
            self.slug = self.code
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields'] = set(kwargs['update_fields']) | {'slug'}
        if not self._state.adding:
            return super().save(*args, **kwargs)

        database = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        for attempt in range(5):
            # Old URLs remain reserved, including after a Workspace is renamed.
            if Workplace.objects.using(database).filter(legacy_slug=self.code).exists():
                self.code = self.slug = generate_workplace_code()
                continue
            try:
                with transaction.atomic(using=database):
                    return super().save(*args, **kwargs)
            except IntegrityError as error:
                constraint = getattr(getattr(error.__cause__, 'diag', None), 'constraint_name', None)
                identifier_collision = constraint == 'unique_workplace_code' or (constraint or '').startswith(
                    f'{self._meta.db_table}_slug_',
                )
                if not identifier_collision or attempt == 4:
                    raise
                self.code = self.slug = generate_workplace_code()
        raise IntegrityError('Nie udało się wygenerować unikatowego kodu Workspace.')

    @property
    def initials(self):
        words = [word for word in self.name.split() if word]
        initials = ''.join(word[:1] for word in words[:2])
        return initials.upper() or 'W'

    def ensure_owner_membership(self):
        return WorkplaceMembership.objects.get_or_create(
            workplace=self,
            user=self.owner,
            defaults={'role': WorkplaceMembership.Role.OWNER},
        )

    def __str__(self):
        return self.name


class WorkplaceMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = 'owner', 'Właściciel'
        ADMIN = 'admin', 'Administrator'
        MEMBER = 'member', 'Członek'

    workplace = models.ForeignKey(Workplace, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workplace_memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['workplace__name', 'user__email']
        constraints = [
            models.UniqueConstraint(fields=['workplace', 'user'], name='unique_workplace_membership'),
        ]

    def __str__(self):
        return f'{self.user} - {self.workplace}'


def invitation_expiry():
    return timezone.now() + timedelta(days=7)


class WorkplaceInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Oczekuje'
        ACCEPTED = 'accepted', 'Przyjęte'
        DECLINED = 'declined', 'Odrzucone'
        REVOKED = 'revoked', 'Anulowane'

    workplace = models.ForeignKey(Workplace, on_delete=models.CASCADE, related_name='invitations')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workplace_invitations')
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sent_workplace_invitations')
    role = models.CharField(max_length=20, choices=[('admin', 'Administrator'), ('member', 'Członek')], default='member')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=invitation_expiry)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['workplace', 'recipient'], condition=Q(status='pending'), name='unique_pending_workplace_invite'),
        ]
        ordering = ['-created_at', '-pk']


class SidebarFavorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sidebar_favorites',
    )
    workplace = models.ForeignKey(
        Workplace,
        on_delete=models.CASCADE,
        related_name='sidebar_favorites',
    )
    item_key = models.CharField(max_length=64)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position', 'created_at', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'workplace', 'item_key'],
                name='unique_sidebar_favorite_per_workplace',
            ),
        ]

    def __str__(self):
        return f'{self.user} - {self.workplace} - {self.item_key}'


def create_workplace_for_user(user, name, workplace_photo=None, description='', avatar=''):
    with transaction.atomic():
        workplace_data = {
            'owner': user,
            'name': name,
            'description': description,
            'avatar': avatar,
        }
        if workplace_photo:
            workplace_data['workplace_photo'] = workplace_photo
        workplace = Workplace.objects.create(**workplace_data)
        workplace.ensure_owner_membership()
        SidebarFavorite.objects.create(
            user=user,
            workplace=workplace,
            item_key='dashboard',
        )
    return workplace
