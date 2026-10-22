from django import forms

from accounts.widgets import UserSelectMultiple
from core.widgets import EmojiPickerInput, VisualSelect
from spaces.services import visible_spaces
from spaces.widgets import SpaceSelect, SpaceSelectMultiple
from workplaces.services import workplace_people
from .models import Dashboard, DashboardGadget
from .filters import visible_filters
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
        widgets = {'visibility': DashboardVisibilitySelect, 'shared_with': UserSelectMultiple}

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


PREFERENCE_FIELDS = ['icon', 'data_scope', 'scope_spaces', 'scope_filter', 'refresh_interval']
PREFERENCE_WIDGETS = {
    'icon': EmojiPickerInput,
    'data_scope': VisualSelect(visuals={
        Dashboard.DataScope.WORKSPACE: {'icon': 'building-2'},
        Dashboard.DataScope.SPACES: {'icon': 'layers'},
        Dashboard.DataScope.FILTER: {'icon': 'filter'},
    }),
    'scope_spaces': SpaceSelectMultiple(attrs={'data-ancore-custom-select-icon': 'layers'}),
    'scope_filter': VisualSelect(attrs={'data-ancore-custom-select-icon': 'filter'}, visuals={}),
    'refresh_interval': VisualSelect(visuals={
        str(value): {'icon': 'circle-slash' if value == 0 else 'refresh-cw'}
        for value in Dashboard.RefreshInterval.values
    }),
}


def configure_preferences(form, request):
    form.fields['scope_spaces'].queryset = visible_spaces(request)
    form.fields['scope_spaces'].label_from_instance = lambda space: space.name
    form.fields['scope_filter'].queryset = visible_filters(request)
    form.fields['scope_filter'].empty_label = 'Wybierz filtr'
    form.fields['data_scope'].help_text = 'Domyślne źródło danych dla gadżetów bez własnej Przestrzeni. Dostęp zależy od uprawnień oglądającego.'
    form.fields['refresh_interval'].help_text = 'Odświeża otwarty podgląd pulpitu. Wstrzymane podczas edycji i w nieaktywnej karcie.'
    for name in ('icon', 'data_scope', 'refresh_interval'):
        form.fields[name].required = False
        if name != 'icon':
            form.fields[name].choices = type(form.instance)._meta.get_field(name).choices
    style_fields(form)


class DashboardPreferencesMixin:
    def clean(self):
        data = super().clean()
        # Older clients submit only name/description. Keep their existing preferences.
        for name in ('icon', 'data_scope', 'refresh_interval'):
            if data.get(name) in (None, '') and name not in self.errors:
                data[name] = getattr(self.instance, name)
        if self.instance.pk and 'data_scope' not in self.data:
            data['scope_spaces'] = self.instance.scope_spaces.all()
            data['scope_filter'] = self.instance.scope_filter
        elif data.get('data_scope') == Dashboard.DataScope.SPACES:
            if not data.get('scope_spaces'):
                self.add_error('scope_spaces', 'Wybierz co najmniej jedną Przestrzeń.')
            data['scope_filter'] = None
        elif data.get('data_scope') == Dashboard.DataScope.FILTER:
            if not data.get('scope_filter'):
                self.add_error('scope_filter', 'Wybierz zapisany filtr.')
            data['scope_spaces'] = self.fields['scope_spaces'].queryset.none()
        else:
            data['scope_spaces'] = self.fields['scope_spaces'].queryset.none()
            data['scope_filter'] = None
        return data


class DashboardForm(DashboardPreferencesMixin, DashboardAccessForm):
    class Meta(DashboardAccessForm.Meta):
        fields = ['name', 'description', *PREFERENCE_FIELDS, 'visibility', 'shared_with', 'layout']
        widgets = {
            **DashboardAccessForm.Meta.widgets,
            **PREFERENCE_WIDGETS,
            'description': forms.Textarea(attrs={'rows': 3}),
            'layout': DashboardLayoutSelect,
        }

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, request=request, **kwargs)
        configure_preferences(self, request)


class DashboardSettingsForm(DashboardPreferencesMixin, forms.ModelForm):
    class Meta:
        model = Dashboard
        fields = ['name', 'description', *PREFERENCE_FIELDS]
        widgets = {**PREFERENCE_WIDGETS, 'description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        configure_preferences(self, request)


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
        widgets = {'kind': GadgetKindSelect, 'space': SpaceSelect}

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['kind'].choices = [('', '---------'), *[(kind, kind.label) for kind in AVAILABLE_GADGET_KINDS]]
        self.catalog = GADGET_CATALOG
        self.fields['space'].queryset = visible_spaces(request)
        self.fields['space'].empty_label = 'Zakres danych pulpitu'
        self.fields['space'].help_text = 'Puste pole używa zakresu danych pulpitu. Wybrana Przestrzeń zastępuje ten zakres.'
        self.fields['space'].label_from_instance = lambda space: space.name
        self.fields['title'].help_text = 'Puste pole używa nazwy gadżetu.'
        self.fields['kind'].help_text = 'Postęp pracy pokazuje odsetek zamkniętych zadań i liczby zadań według statusu.'
        if self.instance.space_id and not self.fields['space'].queryset.filter(pk=self.instance.space_id).exists():
            self.fields['space'].help_text = 'Ta przestrzeń jest już niedostępna. Wybierz dostępne źródło danych.'
        style_fields(self)
