"""Shared time-entry validation, independent of the task domain."""
from datetime import UTC, timedelta
from django import forms
from django.utils import timezone


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, attrs=None, format=None):
        super().__init__(attrs=attrs, format=format or "%Y-%m-%dT%H:%M")


class TimeLogForm(forms.ModelForm):
    hours = forms.IntegerField(label='Godziny', min_value=0, required=False,
                               widget=forms.NumberInput(attrs={'class': 'form-input', 'step': 1}))
    minutes = forms.IntegerField(label='Minuty', min_value=0, max_value=59, required=False,
                                 widget=forms.NumberInput(attrs={'class': 'form-input', 'step': 1}))
    calculation_mode = forms.ChoiceField(choices=[('interval', 'Przedział czasu'), ('duration', 'Czas poświęcony')],
                                        required=False, initial='interval', widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['started_at'].required = False
        self.fields['ended_at'].required = False
        if self.is_bound:
            self.data = self.data.copy()
            # Only the last edited side is authoritative. Ignore stale derived values.
            if self.data.get(self.add_prefix('calculation_mode')) == 'duration':
                self.data[self.add_prefix('started_at')] = ''
            else:
                self.data[self.add_prefix('hours')] = ''
                self.data[self.add_prefix('minutes')] = ''
        elif self.instance.pk:
            self.initial['hours'], self.initial['minutes'] = divmod(self.instance.duration_minutes, 60)

    class Meta:
        fields = ['started_at', 'ended_at', 'description']
        widgets = {
            'started_at': DateTimeLocalInput(attrs={'class': 'form-input', 'step': 60}),
            'ended_at': DateTimeLocalInput(attrs={'class': 'form-input', 'step': 60}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Opisz wykonaną pracę…'}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('started_at'), cleaned.get('ended_at')
        mode = cleaned.get('calculation_mode') or 'interval'
        if mode == 'duration':
            if end is None and 'ended_at' not in self.errors:
                end = timezone.now().replace(second=0, microsecond=0)
                cleaned['ended_at'] = end
                self.data[self.add_prefix('ended_at')] = timezone.localtime(end).strftime('%Y-%m-%dT%H:%M')
            if 'hours' not in self.errors and 'minutes' not in self.errors:
                minutes = (cleaned.get('hours') or 0) * 60 + (cleaned.get('minutes') or 0)
                if minutes <= 0:
                    self.add_error('minutes', 'Podaj czas poświęcony większy od zera.')
                elif end:
                    try:
                        start = end.astimezone(UTC) - timedelta(minutes=minutes)
                        cleaned['started_at'] = start
                        self.data[self.add_prefix('started_at')] = timezone.localtime(start).strftime('%Y-%m-%dT%H:%M')
                    except (OverflowError, ValueError):
                        self.add_error('hours', 'Podany czas poświęcony jest zbyt długi.')
        else:
            for name in ('started_at', 'ended_at'):
                if cleaned.get(name) is None and name not in self.errors:
                    self.add_error(name, 'To pole jest wymagane.')
            if start and end and end > start:
                total = int((end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() // 60)
                cleaned['hours'], cleaned['minutes'] = divmod(total, 60)
                for name in ('hours', 'minutes'):
                    self.data[self.add_prefix(name)] = cleaned[name]
        for name in ('started_at', 'ended_at'):
            value = cleaned.get(name)
            if value and (value.second or value.microsecond):
                self.add_error(name, 'Podaj czas z dokładnością do pełnej minuty.')
        if start and end and end <= start:
            self.add_error('ended_at', 'Zakończenie musi być późniejsze niż rozpoczęcie.')
        return cleaned

