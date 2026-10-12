from django import forms

from spaces.models import SpaceTask
from spaces.services import teams_for, visible_spaces
from tasks.models import TaskTag
from workplaces.services import workplace_people
from .filter_search import BASIC_SORTS, Compiler, QueryError, parse_query
from .models import SavedTaskFilter
from .pulpit_forms import DashboardVisibilitySelect, style_fields


class BasicTaskSearchForm(forms.Form):
    q = forms.CharField(label='Szukaj zadań', required=False, max_length=120,
                        widget=forms.TextInput(attrs={'placeholder': 'Szukaj zadań'}))
    space = forms.MultipleChoiceField(label='Przestrzeń', required=False)
    type = forms.MultipleChoiceField(label='Typ zgłoszenia', required=False)
    status = forms.MultipleChoiceField(label='Status', required=False)
    priority = forms.MultipleChoiceField(label='Priorytet', required=False, choices=SpaceTask.PRIORITY_CHOICES)
    assignee = forms.MultipleChoiceField(label='Wykonawca', required=False)
    tag = forms.MultipleChoiceField(label='Tagi', required=False)
    team = forms.MultipleChoiceField(label='Zespół', required=False)
    sort = forms.ChoiceField(label='Sortowanie', choices=list(BASIC_SORTS.items()), initial='created_desc')

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        spaces = list(visible_spaces(request).order_by('name', 'pk'))
        self.fields['space'].choices = [(str(space.pk), f'{space.name} ({space.key})') for space in spaces]
        for field, key in [('status', 'statuses'), ('type', 'types')]:
            choices = {}
            for space in spaces:
                for row in space.configuration.settings.get(key, []):
                    choices.setdefault(row['key'], row['label'])
            self.fields[field].choices = list(choices.items())
        self.fields['assignee'].choices = [('me', 'Przypisane do mnie'), ('unassigned', 'Nieprzypisane'), *[
            (str(person.pk), person.get_full_name() or person.email)
            for person in workplace_people(request.workplace, request.user)
        ]]
        self.fields['tag'].choices = [(str(tag.pk), f'{tag.name} ({tag.space.key})') for tag in TaskTag.objects.filter(
            user=request.workplace.owner, workplace=request.workplace, space_id__in=[space.pk for space in spaces],
        ).select_related('space').order_by('name', 'pk')]
        self.fields['team'].choices = [(str(team.pk), team.name) for team in teams_for(request).order_by('name', 'pk')]
        style_fields(self)
        for name, field in self.fields.items():
            field.widget.attrs['aria-label'] = field.label
            if isinstance(field, forms.MultipleChoiceField):
                field.widget.attrs['data-ancore-custom-select-empty-label'] = field.label


class SavedTaskFilterForm(forms.ModelForm):
    revision = forms.IntegerField(required=False, min_value=0, widget=forms.HiddenInput)

    class Meta:
        model = SavedTaskFilter
        fields = ['name', 'description', 'visibility', 'shared_with', 'query']
        labels = {'shared_with': 'Osoby z dostępem'}
        widgets = {'description': forms.Textarea(attrs={'rows': 2}),
                   'query': forms.Textarea(attrs={'rows': 3}), 'visibility': DashboardVisibilitySelect}

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.fields['shared_with'].queryset = workplace_people(request.workplace, request.user).exclude(pk=request.user.pk)
        self.fields['shared_with'].label_from_instance = lambda person: person.get_full_name() or person.email
        self.fields['visibility'].help_text = 'Udostępnienie filtra zachowuje uprawnienia odbiorców do przestrzeni i zadań.'
        self.fields['query'].help_text = 'Puste warunki pokazują wszystkie dostępne zadania.'
        self.initial['revision'] = self.instance.revision
        style_fields(self)

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not name:
            raise forms.ValidationError('Podaj nazwę filtra.')
        return name

    def clean_query(self):
        source = self.cleaned_data['query'].strip()
        try:
            Compiler(self.request).expression(parse_query(source).expression)
        except QueryError as error:
            raise forms.ValidationError(str(error)) from error
        return source

    def clean(self):
        data = super().clean()
        if data.get('visibility') == SavedTaskFilter.Visibility.SELECTED and not data.get('shared_with'):
            self.add_error('shared_with', 'Wybierz co najmniej jedną osobę.')
        elif data.get('visibility') != SavedTaskFilter.Visibility.SELECTED:
            data['shared_with'] = self.fields['shared_with'].queryset.none()
        return data
