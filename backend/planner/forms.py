from django import forms
from django.utils import timezone

from .models import CalendarEvent, event_color_validator

_INPUT_ATTRS = {'class': 'form-input'}
_DATETIME_FORMATS = [
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
]


class CalendarEventForm(forms.ModelForm):
    color = forms.CharField(
        label='Kolor', max_length=7, required=False, validators=[event_color_validator],
        widget=forms.TextInput(attrs={
            **_INPUT_ATTRS, 'placeholder': CalendarEvent.DEFAULT_COLOR,
            'autocomplete': 'off', 'spellcheck': 'false',
        }),
    )

    class Meta:
        model = CalendarEvent
        fields = ['title', 'description', 'start', 'end', 'all_day', 'color']
        widgets = {
            'title': forms.TextInput(attrs={**_INPUT_ATTRS, 'placeholder': 'Tytuł wydarzenia'}),
            'description': forms.Textarea(attrs={
                **_INPUT_ATTRS,
                'rows': 3,
                'placeholder': 'Opis (opcjonalnie)',
            }),
            'start': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={**_INPUT_ATTRS, 'type': 'datetime-local'},
            ),
            'end': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={**_INPUT_ATTRS, 'type': 'datetime-local'},
            ),
            'all_day': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('start', 'end'):
            self.fields[name].input_formats = _DATETIME_FORMATS

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start')
        end = cleaned.get('end')
        if start and end and end < start:
            raise forms.ValidationError('Data zakończenia nie może być wcześniejsza niż data rozpoczęcia.')
        return cleaned

    def clean_color(self):
        return (self.cleaned_data.get('color') or CalendarEvent.DEFAULT_COLOR).lower()

    def save(self, commit=True):
        event = super().save(commit=False)
        if event.all_day:
            start = timezone.localtime(event.start)
            end = timezone.localtime(event.end)
            event.start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            event.end = end.replace(hour=23, minute=59, second=59, microsecond=0)
        if commit:
            event.save()
        return event
