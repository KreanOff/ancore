from django import forms

from accounts.avatar import account_avatar
from accounts.widgets import UserSelectMultiple
from core.widgets import VisualSelectMultiple
from spaces.defaults import issue_type_icon
from spaces.models import SpaceTask
from spaces.services import app_url, teams_for, visible_spaces
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
        visuals = {
            'space': {str(space.pk): {'template': 'spaces/avatar.html', 'context': {'space': space}} for space in spaces},
            'type': {}, 'status': {},
            'priority': {key: {'template': 'core/includes/select_priority.html', 'context': {'priority': key}}
                         for key, _ in SpaceTask.PRIORITY_CHOICES},
        }
        for field, key in [('status', 'statuses'), ('type', 'types')]:
            choices = {}
            for space in spaces:
                for row in space.configuration.settings.get(key, []):
                    choices.setdefault(row['key'], row['label'])
                    visuals[field].setdefault(row['key'],
                        {'icon': issue_type_icon(row['key'])} if field == 'type' else
                        {'template': 'core/includes/select_status.html', 'context': {'category': row['category']}})
            self.fields[field].choices = list(choices.items())
        people = list(workplace_people(request.workplace, request.user))
        self.fields['assignee'].choices = [('me', 'Przypisane do mnie'), ('unassigned', 'Nieprzypisane'), *[
            (str(person.pk), person.get_full_name() or person.email)
            for person in people
        ]]
        visuals['assignee'] = {str(person.pk): {
            'template': 'accounts/includes/user_avatar.html',
            'context': {'avatar': account_avatar(person), 'avatar_class': 'tasks-issue-mini-avatar'},
        } for person in people}
        visuals['assignee']['me'] = {
            'template': 'accounts/includes/user_avatar.html',
            'context': {'avatar': account_avatar(request.user), 'avatar_class': 'tasks-issue-mini-avatar'},
        }
        visuals['assignee']['unassigned'] = {'icon': 'user-round'}
        self.fields['tag'].choices = [(str(tag.pk), f'{tag.name} ({tag.space.key})') for tag in TaskTag.objects.filter(
            user=request.workplace.owner, workplace=request.workplace, space_id__in=[space.pk for space in spaces],
        ).select_related('space').order_by('name', 'pk')]
        teams = list(teams_for(request).order_by('name', 'pk'))
        self.fields['team'].choices = [(str(team.pk), team.name) for team in teams]
        visuals['team'] = {str(team.pk): {
            'template': 'spaces/team_avatar.html',
            'context': {'photo_url': app_url(request, f'{team.pk}/photo/', 'teams') if team.photo else ''},
        } for team in teams}
        for name, options in visuals.items():
            self.fields[name].widget = VisualSelectMultiple(choices=self.fields[name].choices, visuals=options)
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
                   'query': forms.Textarea(attrs={'rows': 3}), 'visibility': DashboardVisibilitySelect,
                   'shared_with': UserSelectMultiple}

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        if 'shared_with' in self.fields:
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
        if 'shared_with' not in self.fields:
            return data
        if data.get('visibility') == SavedTaskFilter.Visibility.SELECTED and not data.get('shared_with'):
            self.add_error('shared_with', 'Wybierz co najmniej jedną osobę.')
        elif data.get('visibility') != SavedTaskFilter.Visibility.SELECTED:
            data['shared_with'] = self.fields['shared_with'].queryset.none()
        return data


class FilterSettingsForm(SavedTaskFilterForm):
    class Meta(SavedTaskFilterForm.Meta):
        fields = ['name', 'description', 'query', 'visibility']

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, request=request, **kwargs)
        self.fields['visibility'].choices = [
            ('private', 'Prywatny — wybrane osoby'), ('workspace', 'Cały Workspace'),
        ]
        self.fields['visibility'].required = False
        self.fields['visibility'].disabled = bool(self.instance.pk and self.instance.created_by_id != request.user.pk)
        self.fields['visibility'].help_text = 'Osobami i rolami zarządzaj w zakładce „Udostępnienia”. Widoczność zmienia właściciel filtra.'
        if self.instance.visibility == SavedTaskFilter.Visibility.SELECTED:
            self.initial['visibility'] = 'private'

    def clean_visibility(self):
        value = self.cleaned_data.get('visibility')
        if not value:
            return self.instance.visibility
        if value == 'private' and self.instance.pk and self.instance.shared_with.exists():
            return SavedTaskFilter.Visibility.SELECTED
        return value
