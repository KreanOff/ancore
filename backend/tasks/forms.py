"""Forms for tags in the current Space domain."""
from django import forms

from .models import TaskTag


class TaskTagForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        workplace = kwargs.pop('workplace', None)
        space = kwargs.pop('space', None)
        super().__init__(*args, **kwargs)
        self.instance.space = space or getattr(self.instance, 'space', None)
        self.instance.user = user or getattr(self.instance, 'user', None)
        self.instance.workplace = workplace or getattr(self.instance, 'workplace', None)
        if user is None:
            user = getattr(self.instance, 'user', None)
        if workplace is None:
            workplace = getattr(self.instance, 'workplace', None)
        related_queryset = TaskTag.objects.none()
        if user:
            from .tagging import tags_in_scope
            related_queryset = tags_in_scope(user, workplace, self.instance.space)
            if self.instance and self.instance.pk:
                related_queryset = related_queryset.exclude(pk=self.instance.pk)
        self.fields['related_tags'].queryset = related_queryset.order_by('name', 'id')
        self.fields['related_tags'].required = False
        self.fields['related_tags'].label = 'Powiązane tagi'
        for field_name in ('category', 'color', 'icon', 'priority', 'scope', 'status'):
            self.fields[field_name].required = False

    class Meta:
        model = TaskTag
        fields = [
            'name',
            'description',
            'category',
            'color',
            'icon',
            'priority',
            'scope',
            'owner_label',
            'status',
            'usage_notes',
            'automation_rules',
            'related_tags',
        ]
        labels = {
            'category': 'Typ tagu',
            'color': 'Kolor',
            'icon': 'Ikona',
            'priority': 'Priorytet',
            'scope': 'Zakres',
            'owner_label': 'Właściciel / dział',
            'status': 'Status',
            'usage_notes': 'Opis użycia',
            'automation_rules': 'Reguły automatyczne',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nazwa tagu',
                'class': 'tasks-inline-input',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Dodaj opis...',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
            'category': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'color': forms.TextInput(attrs={
                'placeholder': '#64748b',
                'class': 'tasks-inline-input',
            }),
            'icon': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'priority': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'scope': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'owner_label': forms.TextInput(attrs={
                'placeholder': 'np. IT, sprzedaż, administracja',
                'class': 'tasks-inline-input',
            }),
            'status': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'usage_notes': forms.Textarea(attrs={
                'placeholder': 'Kiedy używać tego tagu...',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
            'automation_rules': forms.Textarea(attrs={
                'placeholder': 'np. dodaj, gdy termin jest dzisiaj',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
            'related_tags': forms.SelectMultiple(attrs={
                'class': 'tasks-inline-select',
                'size': 4,
                'data-ancore-custom-select-search': 'true',
                'data-ancore-custom-select-search-placeholder': 'Szukaj tagów',
            }),
        }

    def clean_name(self):
        from .tagging import tags_in_scope
        name = (self.cleaned_data.get('name') or '').strip()
        if tags_in_scope(self.instance.user, self.instance.workplace, self.instance.space).filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Taki tag już istnieje.')
        return name

    def clean_color(self):
        value = (self.cleaned_data.get('color') or '#64748b').strip()
        if not value.startswith('#'):
            value = f'#{value}'
        value = value.lower()
        hex_value = value[1:]
        if len(hex_value) != 6 or any(character not in '0123456789abcdef' for character in hex_value):
            raise forms.ValidationError('Podaj kolor w formacie #RRGGBB.')
        return value

    def clean_icon(self):
        return self.cleaned_data.get('icon') or 'tag'

    def clean_category(self):
        return self.cleaned_data.get('category') or 'general'

    def clean_priority(self):
        return self.cleaned_data.get('priority') or 'none'

    def clean_scope(self):
        return self.cleaned_data.get('scope') or 'tasks'

    def clean_status(self):
        return self.cleaned_data.get('status') or 'active'
