from django import forms

from spaces.services import visible_spaces
from workplaces.services import workplace_people
from .models import Dashboard, DashboardGadget
from .pulpits import AVAILABLE_GADGET_KINDS, GADGET_CATALOG, GADGET_ICONS


def style_fields(form):
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-input'


class DashboardVisibilitySelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        icon = {
            Dashboard.Visibility.PRIVATE: 'lock',
            Dashboard.Visibility.SELECTED: 'users',
            Dashboard.Visibility.WORKSPACE: 'building-2',
        }.get(value)
        if icon:
            option['attrs']['data-ancore-option-icon'] = icon
        return option


class DashboardLayoutSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value in Dashboard.Layout.values:
            field_id = (attrs or {}).get('id', name)
            option['attrs']['data-ancore-option-preview'] = f'{field_id}_preview_{value}'
        return option


class DashboardAccessForm(forms.ModelForm):
    class Meta:
        model = Dashboard
        fields = ['visibility', 'shared_with']
        labels = {'shared_with': 'Osoby z dostępem'}
        widgets = {'visibility': DashboardVisibilitySelect}

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['shared_with'].queryset = workplace_people(request.workplace, request.user).exclude(pk=request.user.pk)
        self.fields['shared_with'].label_from_instance = lambda user: user.get_full_name() or user.email
        self.fields['shared_with'].help_text = 'Wybierz osoby dla widoczności „Wybrane osoby”. Dostęp do danych nadal zależy od ich uprawnień.'
        self.fields['visibility'].help_text = 'Tylko twórca może zmieniać pulpit i jego gadżety.'
        style_fields(self)

    def clean(self):
        data = super().clean()
        if data.get('visibility') == Dashboard.Visibility.SELECTED and not data.get('shared_with'):
            self.add_error('shared_with', 'Wybierz co najmniej jedną osobę.')
        elif data.get('visibility') != Dashboard.Visibility.SELECTED:
            data['shared_with'] = self.fields['shared_with'].queryset.none()
        return data


class DashboardForm(DashboardAccessForm):
    class Meta(DashboardAccessForm.Meta):
        fields = ['name', 'description', 'visibility', 'shared_with', 'layout']
        widgets = {
            **DashboardAccessForm.Meta.widgets,
            'description': forms.Textarea(attrs={'rows': 3}),
            'layout': DashboardLayoutSelect,
        }


class DashboardSettingsForm(forms.ModelForm):
    class Meta:
        model = Dashboard
        fields = ['name', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class GadgetKindSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value in GADGET_ICONS:
            option['attrs']['data-ancore-option-icon'] = GADGET_ICONS[value]
        return option


class GadgetForm(forms.ModelForm):
    assignee = forms.ChoiceField(label='Przypisanie', choices=[('all', 'Wszyscy'), ('me', 'Przypisane do oglądającego'), ('unassigned', 'Bez wykonawcy')])

    class Meta:
        model = DashboardGadget
        fields = ['kind', 'title', 'space', 'assignee']
        widgets = {'kind': GadgetKindSelect}

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['kind'].choices = [('', '---------'), *[(kind, kind.label) for kind in AVAILABLE_GADGET_KINDS]]
        self.catalog = GADGET_CATALOG
        self.fields['space'].queryset = visible_spaces(request)
        self.fields['space'].empty_label = 'Wszystkie dostępne przestrzenie'
        self.fields['space'].label_from_instance = lambda space: space.name
        self.fields['title'].help_text = 'Puste pole używa nazwy gadżetu.'
        self.fields['kind'].help_text = 'Postęp pracy pokazuje odsetek zamkniętych zadań i liczby zadań według statusu.'
        if self.instance.space_id and not self.fields['space'].queryset.filter(pk=self.instance.space_id).exists():
            self.fields['space'].help_text = 'Ta przestrzeń jest już niedostępna. Wybierz dostępne źródło danych.'
        style_fields(self)
