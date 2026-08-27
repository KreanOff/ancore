from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils.text import slugify


POLISH_CODE_TRANSLATION = str.maketrans({
    'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
    'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z',
})


class Workplace(models.Model):
    name = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=20, blank=True)
    slug = models.SlugField(max_length=160, blank=True)
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
            models.UniqueConstraint(fields=['owner', 'name'], name='unique_workplace_name_per_owner'),
            models.UniqueConstraint(fields=['owner', 'slug'], name='unique_workplace_slug_per_owner'),
            models.UniqueConstraint(
                fields=['owner', 'code'],
                condition=~Q(code=''),
                name='unique_workplace_code_per_owner',
            ),
        ]

    def _base_slug(self):
        return slugify(self.name)[:120] or 'workplace'

    def _unique_slug(self):
        base_slug = self._base_slug()
        candidate = base_slug
        counter = 2
        queryset = Workplace.objects.filter(owner=self.owner, slug=candidate)
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
        while queryset.exists():
            suffix = f'-{counter}'
            candidate = f'{base_slug[:160 - len(suffix)]}{suffix}'
            queryset = Workplace.objects.filter(owner=self.owner, slug=candidate)
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            counter += 1
        return candidate

    def _base_code(self):
        normalized_name = (self.name or '').translate(POLISH_CODE_TRANSLATION)
        return (slugify(normalized_name)[:20] or 'miejsce').upper()

    def _unique_code(self):
        base_code = self._base_code()
        candidate = base_code
        counter = 2
        queryset = Workplace.objects.filter(owner=self.owner, code__iexact=candidate)
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
        while queryset.exists():
            suffix = f'-{counter}'
            candidate = f'{base_code[:20 - len(suffix)]}{suffix}'
            queryset = Workplace.objects.filter(owner=self.owner, code__iexact=candidate)
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            counter += 1
        return candidate

    def save(self, *args, **kwargs):
        self.code = (self.code or '').strip().upper()
        if not self.code:
            self.code = self._unique_code()
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields'] = set(kwargs['update_fields']) | {'code'}
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['workplace__name', 'user__email']
        constraints = [
            models.UniqueConstraint(fields=['workplace', 'user'], name='unique_workplace_membership'),
        ]

    def __str__(self):
        return f'{self.user} - {self.workplace}'


def create_workplace_for_user(user, name, workplace_photo=None, description='', code=''):
    with transaction.atomic():
        workplace_data = {
            'owner': user,
            'name': name,
            'description': description,
            'code': code,
        }
        if workplace_photo:
            workplace_data['workplace_photo'] = workplace_photo
        workplace = Workplace.objects.create(**workplace_data)
        workplace.ensure_owner_membership()
    return workplace
