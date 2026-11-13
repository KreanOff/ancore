from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


event_color_validator = RegexValidator(
    regex=r'\A(?:#[0-9a-fA-F]{6}|red|blue|green|amber|slate)\Z',
    message='Podaj kolor w formacie #RRGGBB.',
)


class CalendarEvent(models.Model):
    DEFAULT_COLOR = '#e04f63'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='calendar_events',
    )
    workplace = models.ForeignKey(
        'workplaces.Workplace',
        on_delete=models.CASCADE,
        related_name='calendar_events',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    color = models.CharField(max_length=10, default=DEFAULT_COLOR, validators=[event_color_validator])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start']

    def __str__(self):
        return self.title
