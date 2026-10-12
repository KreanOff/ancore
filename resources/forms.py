from django import forms

from accounts.widgets import UserSelect
from workplaces.services import workplace_people
from .models import Resource


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['name', 'kind', 'inventory_number', 'serial_number', 'status', 'assigned_to', 'location', 'purchased_on', 'expires_on', 'notes']
        widgets = {
            'assigned_to': UserSelect,
            'purchased_on': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'expires_on': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, workplace, **kwargs):
        super().__init__(*args, **kwargs)
        self.workplace = workplace
        people = workplace_people(workplace)
        # Former assignees remain recorded, but cannot be selected for a new assignment.
        self.fields['assigned_to'].queryset = people
        self.fields['assigned_to'].empty_label = 'Nieprzypisany'
        self.fields['assigned_to'].label_from_instance = lambda user: user.get_full_name() or user.email
        if self.instance.assigned_to_id and not people.filter(pk=self.instance.assigned_to_id).exists():
            self.initial['assigned_to'] = None
            self.fields['assigned_to'].help_text = 'Poprzednia osoba nie należy już do aktywnego zespołu. Wybierz inną osobę lub pozostaw zasób nieprzypisany.'
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-input'
        self.fields['name'].widget.attrs['placeholder'] = 'np. Laptop biurowy'
        self.fields['inventory_number'].help_text = 'Opcjonalny, unikalny w tym Workspace.'

    def clean_inventory_number(self):
        number = self.cleaned_data['inventory_number'].strip()
        duplicates = Resource.objects.filter(workplace=self.workplace, inventory_number__iexact=number)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if number and duplicates.exists():
            raise forms.ValidationError('Zasób o tym numerze ewidencyjnym już istnieje w tym Workspace.')
        return number

    def clean(self):
        data = super().clean()
        start, end = data.get('purchased_on'), data.get('expires_on')
        if start and end and end < start:
            self.add_error('expires_on', 'Termin ważności nie może być wcześniejszy niż data zakupu.')
        return data
