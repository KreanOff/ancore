from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class PresenceStatus(models.TextChoices):
        ACTIVE = 'active', 'Aktywny'
        INACTIVE = 'inactive', 'Nieaktywny'
        RECENTLY_SEEN = 'recently_seen', 'Był ostatnio'
        OUT_OF_OFFICE = 'out_of_office', 'Poza biurem'
        BUSY = 'busy', 'Zajęty'
        DO_NOT_DISTURB = 'do_not_disturb', 'Nie przeszkadzać'

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    presence_status = models.CharField(
        max_length=20,
        choices=PresenceStatus.choices,
        default=PresenceStatus.ACTIVE,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    @property
    def presence_status_class(self):
        return f'presence-{self.presence_status}'

    def __str__(self):
        return self.email
