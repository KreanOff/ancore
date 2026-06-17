import secrets

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Company(models.Model):
    name = models.CharField(max_length=160)
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=240, blank=True)
    notes = models.TextField(blank=True)
    company_photo = models.FileField(
        upload_to='company_photos/',
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='companies')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='CompanyMembership', related_name='company_memberships')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'name'],
                name='unique_company_name_per_owner',
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def initials(self):
        words = [word for word in self.name.split() if word]
        initials = ''.join(word[:1] for word in words[:2])
        return initials.upper() or 'F'


class CompanyMembership(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Właściciel'),
        ('admin', 'Administrator'),
        ('member', 'Członek'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company_membership_rows')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['company__name', 'user__email']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'user'],
                name='unique_company_membership',
            ),
        ]

    def __str__(self):
        return f'{self.user} - {self.company}'


class Contact(models.Model):
    STATUS_CHOICES = [
        ('lead', 'Lead'),
        ('active', 'Aktywny'),
        ('customer', 'Klient'),
        ('partner', 'Partner'),
        ('archived', 'Archiwum'),
    ]

    first_name = models.CharField(max_length=80, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=140, blank=True)
    company_record = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='contacts')
    role = models.CharField(max_length=120, blank=True, db_column='position')
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    source = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='lead')
    notes = models.TextField(blank=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contacts', db_column='owner_id')

    class Meta:
        ordering = ['first_name', 'middle_name', 'last_name', 'company']

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        name = ' '.join(
            part.strip()
            for part in [self.first_name, self.middle_name, self.last_name]
            if part and part.strip()
        )
        return name or self.company or f'Kontakt #{self.pk}'

    @property
    def initials(self):
        parts = [self.first_name, self.last_name]
        initials = ''.join((part or '').strip()[:1] for part in parts if (part or '').strip())
        if initials:
            return initials.upper()
        if self.company:
            return self.company[:1].upper()
        return 'K'


class UserContact(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_contacts')
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='added_by_users')
    linked_contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='linked_user_contacts')
    note = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['target_user__first_name', 'target_user__last_name', 'target_user__email']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'target_user'],
                name='unique_user_contact_per_owner',
            ),
        ]

    def __str__(self):
        return f'{self.owner} -> {self.target_user}'


class ContactActivity(models.Model):
    KIND_CHOICES = [
        ('system', 'Historia'),
        ('comment', 'Komentarz'),
    ]

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='contact_activities')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='system')
    action = models.CharField(max_length=60)
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.contact} - {self.action}'


class SharedItem(models.Model):
    PERMISSION_CHOICES = [
        ('view', 'Podgląd'),
        ('edit', 'Edycja'),
    ]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    shared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shared_items_sent')
    shared_with = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shared_items_received')
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='view')
    note = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id', 'shared_by', 'shared_with'],
                name='unique_shared_item_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.content_object} -> {self.shared_with}'


class SharedItemLink(models.Model):
    PERMISSION_CHOICES = SharedItem.PERMISSION_CHOICES

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shared_item_links')
    token = models.CharField(max_length=64, unique=True, blank=True)
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='view')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id', 'created_by'],
                condition=Q(is_active=True),
                name='unique_active_shared_item_link',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_hex(16)
        super().save(*args, **kwargs)

    def deactivate(self):
        if not self.is_active:
            return
        self.is_active = False
        self.deactivated_at = timezone.now()
        self.save(update_fields=['is_active', 'deactivated_at'])

    def __str__(self):
        return f'{self.content_object} link'
