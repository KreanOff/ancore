from django.conf import settings
from django.db import models


class CalendarEvent(models.Model):
    COLOR_CHOICES = [
        ('red', 'Czerwony'),
        ('blue', 'Niebieski'),
        ('green', 'Zielony'),
        ('amber', 'Bursztynowy'),
        ('slate', 'Szary'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='calendar_events',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default='red')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start']

    def __str__(self):
        return self.title
