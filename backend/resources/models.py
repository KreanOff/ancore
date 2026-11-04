from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class Resource(models.Model):
    class Kind(models.TextChoices):
        EQUIPMENT = 'equipment', 'Sprzęt'
        LICENSE = 'license', 'Licencja'
        TOOL = 'tool', 'Narzędzie'

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Dostępny'
        IN_USE = 'in_use', 'W użyciu'
        MAINTENANCE = 'maintenance', 'W serwisie'
        RETIRED = 'retired', 'Wycofany'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_resources')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='resources')
    name = models.CharField('Nazwa', max_length=200)
    kind = models.CharField('Typ', max_length=20, choices=Kind.choices, default=Kind.EQUIPMENT)
    inventory_number = models.CharField('Numer ewidencyjny', max_length=80, blank=True)
    serial_number = models.CharField('Numer seryjny', max_length=120, blank=True)
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Osoba odpowiedzialna', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_resources')
    location = models.CharField('Lokalizacja', max_length=200, blank=True)
    purchased_on = models.DateField('Data zakupu', null=True, blank=True)
    expires_on = models.DateField('Termin ważności / gwarancji', null=True, blank=True)
    return_due_on = models.DateField('Planowany zwrot', null=True, blank=True)
    notes = models.TextField('Notatki', max_length=10000, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_resources')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='updated_resources')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'pk']
        verbose_name = 'Zasób'
        verbose_name_plural = 'Zasoby'
        constraints = [
            models.UniqueConstraint(Lower('inventory_number'), 'workplace', condition=~models.Q(inventory_number=''), name='resource_inventory_unique'),
            models.CheckConstraint(condition=models.Q(kind__in=['equipment', 'license', 'tool']), name='resource_valid_kind'),
            models.CheckConstraint(condition=models.Q(status__in=['available', 'in_use', 'maintenance', 'retired']), name='resource_valid_status'),
            models.CheckConstraint(condition=models.Q(purchased_on__isnull=True) | models.Q(expires_on__isnull=True) | models.Q(expires_on__gte=models.F('purchased_on')), name='resource_valid_dates'),
            models.CheckConstraint(condition=models.Q(return_due_on__isnull=True) | models.Q(status='in_use'), name='resource_return_in_use'),
        ]
        indexes = [models.Index(fields=['owner', 'workplace', 'status'], name='resource_scope_status')]

    @property
    def icon(self):
        return {self.Kind.EQUIPMENT: 'laptop', self.Kind.LICENSE: 'key-round', self.Kind.TOOL: 'wrench'}.get(self.kind, 'package')

    def __str__(self):
        return self.name


class ResourceActivity(models.Model):
    class Action(models.TextChoices):
        CREATED = 'created', 'Dodano zasób'
        UPDATED = 'updated', 'Zmieniono dane'
        HANDOVER = 'handover', 'Przekazano zasób'
        RETURN = 'return', 'Przyjęto zwrot'
        STATUS = 'status', 'Zmieniono status'
        LOCATION = 'location', 'Zmieniono lokalizację'
        NOTE = 'note', 'Dodano notatkę'

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='resource_activities')
    actor_name = models.CharField(max_length=500)
    action = models.CharField(max_length=20, choices=Action.choices)
    changes = models.JSONField(default=list)
    note = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        indexes = [models.Index(fields=['resource', '-created_at', '-id'], name='resource_activity_recent')]
