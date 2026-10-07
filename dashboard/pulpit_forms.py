from django import forms

from spaces.services import visible_spaces
from tasks.models import Task
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
    status = forms.ChoiceField(label='Status', required=False, choices=[('', 'Wszystkie statusy'), *Task.STATUS_CHOICES])
    assignee = forms.ChoiceField(label='Przypisanie', choices=[('all', 'Wszyscy'), ('me', 'Przypisane do oglądającego'), ('unassigned', 'Bez wykonawcy')])
    group_by = forms.ChoiceField(label='Grupowanie statystyk', choices=[('status', 'Status'), ('priority', 'Priorytet'), ('assignee', 'Wykonawca')])
    limit = forms.TypedChoiceField(label='Liczba wyników', coerce=int, choices=[(5, '5'), (10, '10'), (20, '20')])

    class Meta:
        model = DashboardGadget
        fields = ['kind', 'title', 'space', 'status', 'assignee', 'group_by', 'limit']
        widgets = {'kind': GadgetKindSelect}

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['kind'].choices = [('', '---------'), *[(kind, kind.label) for kind in AVAILABLE_GADGET_KINDS]]
        self.catalog = GADGET_CATALOG
        self.fields['space'].queryset = visible_spaces(request)
        self.fields['space'].empty_label = 'Wszystkie dostępne przestrzenie'
        self.fields['space'].label_from_instance = lambda space: space.project.name
        self.fields['title'].help_text = 'Puste pole używa nazwy gadżetu.'
        self.fields['kind'].help_text = 'Przypisane do mnie pokazuje otwarte zadania osoby oglądającej pulpit.'
        self.fields['group_by'].help_text = 'Dotyczy gadżetu „Statystyki zadań”.'
        self.fields['limit'].help_text = 'Liczba widocznych zadań lub wpisów aktywności.'
        if self.instance.space_id and not self.fields['space'].queryset.filter(pk=self.instance.space_id).exists():
            self.fields['space'].help_text = 'Ta przestrzeń jest już niedostępna. Wybierz dostępne źródło danych.'
        style_fields(self)
