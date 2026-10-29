"""Shared task schedule validation and local calendar projections."""
from datetime import datetime, time, timezone as datetime_timezone

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone


class ScheduleDateTimeField(forms.DateTimeField):
    def to_python(self, value):
        if isinstance(value, str) and value.strip() and ':' not in value:
            raise ValidationError('Podaj datę i godzinę.')
        result = super().to_python(value)
        if result is not None:
            try:
                result.astimezone(datetime_timezone.utc)
                timezone.localtime(result)
            except (OverflowError, ValueError):
                raise ValidationError('Data i godzina są poza obsługiwanym zakresem.')
        return result


def local_date(value):
    return timezone.localtime(value).date() if value else None


def validate_range(start_at, due_at):
    if start_at and due_at and start_at.astimezone(datetime_timezone.utc) > due_at.astimezone(datetime_timezone.utc):
        raise ValidationError('Termin nie może być wcześniejszy niż rozpoczęcie.')


def move_to_date(value, day, default_clock=time()):
    """Change calendar day, retaining the original wall time and its precision."""
    if day is None:
        return None
    if day == local_date(value):
        return value
    clock = timezone.localtime(value).time() if value else default_clock
    return ScheduleDateTimeField().clean(datetime.combine(day, clock))
