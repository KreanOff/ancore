import re

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.utils import timezone

from accounts.widgets import UserChoiceField
from core.upload_validation import validate_image_upload
from tasks.access import editable_to
from tasks.models import Task, TaskSection, TaskTag
from tasks.hierarchy import require_movable_task_tree
from workplaces.services import can_manage_team, workplace_people, workspace_owner
from .defaults import KINDS, MANAGEMENT, TEMPLATES
from .avatars import AVATARS, AVATAR_CHOICES, preset_avatar, space_avatar
from .models import Space, SpaceConfiguration, Sprint, Team, WorkItem
from .services import teams_for, visible_items, visible_spaces
from .widgets import IssueTypeSelect


class StyledForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style()

    def style(self):
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-input'
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'tasks-row-checkbox'


class SpaceAvatarForm(StyledForm):
    avatar = forms.ChoiceField(label='Awatar przestrzeni', choices=AVATAR_CHOICES, widget=forms.RadioSelect)
    avatar_photo = forms.FileField(
        label='Własny obraz', required=False,
        widget=forms.FileInput(attrs={'accept': 'image/png,image/jpeg,image/webp', 'data-space-avatar-file': ''}),
        validators=[validate_image_upload],
    )
    compact = True

    def __init__(self, *args, space, **kwargs):
        self.space = space
        kwargs['initial'] = {'avatar': 'upload' if space.avatar_photo else space.avatar or 'auto'}
        super().__init__(*args, **kwargs)
        self.current_avatar = space_avatar(space)
        self.avatar_options = [preset_avatar(key) for key, _ in AVATARS]

    def clean(self):
        data = super().clean()
        if data.get('avatar') == 'upload' and not data.get('avatar_photo') and not self.space.avatar_photo and not self.errors.get('avatar_photo'):
            self.add_error('avatar_photo', 'Wybierz obraz do przesłania.')
        return data


class SpaceForm(StyledForm):
    name = forms.CharField(label='Nazwa przestrzeni', max_length=120)
    key = forms.RegexField(label='Klucz przestrzeni', regex=r'^[A-Z][A-Z0-9]{1,11}$', max_length=12, help_text='2–12 wielkich liter lub cyfr, np. ANC. Oznaczenia zadań: ANC-1, ANC-2.')
    description = forms.CharField(label='Opis', required=False, widget=forms.Textarea(attrs={'rows': 3}))
    kind = forms.ChoiceField(label='Rodzaj przestrzeni', choices=KINDS)
    template = forms.ChoiceField(label='Szablon', choices=[(k, v['label']) for k, v in TEMPLATES.items()])
    management = forms.ChoiceField(label='Sposób zarządzania', choices=MANAGEMENT)
    configuration = forms.ModelChoiceField(label='Wspólna konfiguracja', queryset=SpaceConfiguration.objects.none(), required=False, empty_label='Utwórz nową konfigurację')
    visibility = forms.ChoiceField(label='Widoczność', choices=[('private', 'Prywatna — wybrane osoby'), ('public', 'Publiczna — cały Workspace')])

    def __init__(self, *args, request, space=None, **kwargs):
        self.request, self.space = request, space
        if space:
            kwargs['initial'] = {'name': space.project.name, 'description': space.project.description, 'key': space.key, 'kind': space.kind, 'template': space.template, 'management': space.management, 'configuration': space.configuration_id if space.configuration.shared else None, 'visibility': space.project.visibility}
        super().__init__(*args, **kwargs)
        if not space:
            self.template_options = [
                {'key': key, **template, 'kind_label': dict(KINDS)[template['kind']]}
                for key, template in TEMPLATES.items()
            ]
            self.selected_template = next(
                (template for template in self.template_options if template['key'] == self['template'].value()),
                None,
            )
            self.fields['kind'].widget = forms.HiddenInput()
            self.fields['template'].widget = forms.HiddenInput()
        self.fields['configuration'].queryset = SpaceConfiguration.objects.filter(workplace=request.workplace, shared=True)
        if not space and not can_manage_team(request.user, request.workplace):
            self.fields['management'].choices = [MANAGEMENT[0]]
            self.fields['configuration'].queryset = SpaceConfiguration.objects.none()
        if space:
            # Changing templates/configuration requires an explicit migration of active work.
            for field in ('key', 'kind', 'template', 'management', 'configuration'):
                self.fields[field].disabled = True
            if space.project.visibility == 'private' and space.project.private_owner_id != request.user.pk:
                self.fields['visibility'].disabled = True

    def clean(self):
        data = super().clean()
        if self.space:
            return data
        key = data.get('key')
        if key and Space.objects.filter(workplace=self.request.workplace, key=key).exists():
            self.add_error('key', 'Ten klucz jest już używany w tym Workspace.')
        if data.get('template') in TEMPLATES and data.get('kind') != TEMPLATES[data['template']]['kind']:
            self.add_error('template', 'Wybierz szablon pasujący do rodzaju przestrzeni.')
        if data.get('management') == 'team' and data.get('configuration'):
            self.add_error('configuration', 'Przestrzeń zespołu ma niezależną konfigurację.')
        return data


class ItemForm(StyledForm):
    title = forms.CharField(label='Tytuł', max_length=255)
    description = forms.CharField(label='Opis', required=False, widget=forms.Textarea(attrs={'rows': 3}))
    work_type = forms.ChoiceField(label='Typ zgłoszenia', widget=IssueTypeSelect)
    priority = forms.ChoiceField(label='Priorytet', choices=Task.PRIORITY_CHOICES, initial='medium')
    tags = forms.ModelMultipleChoiceField(label='Tagi', queryset=TaskTag.objects.none(), required=False, widget=forms.SelectMultiple(attrs={
        'data-ancore-custom-select-search': 'true', 'data-ancore-custom-select-search-placeholder': 'Szukaj tagów',
    }))
    assignee = UserChoiceField(label='Wykonawca', queryset=None, required=False, empty_label='Brak osoby')
    team = forms.ModelChoiceField(label='Zespół', queryset=Team.objects.none(), required=False)
    section = forms.ModelChoiceField(label='Grupa', queryset=TaskSection.objects.none(), required=False, empty_label='Domyślna grupa przestrzeni')
    in_backlog = forms.BooleanField(label='Umieść w backlogu', required=False)
    sprint = forms.ModelChoiceField(label='Sprint', queryset=Sprint.objects.none(), required=False)
    epic = forms.ModelChoiceField(label='Epik', queryset=WorkItem.objects.none(), required=False)
    points = forms.IntegerField(label='Estymacja (punkty)', min_value=0, max_value=10000, required=False)
    start_on = forms.DateField(label='Planowane rozpoczęcie', required=False, widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    due_at = forms.DateTimeField(label='Termin wykonania', required=False, widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}))

    def __init__(self, *args, request, space, item=None, **kwargs):
        self.request, self.space, self.item = request, space, item
        if item:
            kwargs['initial'] = {**{key: getattr(item, key) for key in ('work_type', 'team', 'sprint', 'epic', 'points', 'in_backlog', 'start_on')}, **{key: getattr(item.task, key) for key in ('title', 'description', 'priority', 'assignee', 'section', 'due_at')}}
        super().__init__(*args, **kwargs)
        config = space.configuration.settings
        from tasks.tagging import tags_in_scope
        self.fields['tags'].queryset = tags_in_scope(workspace_owner(request), request.workplace, space)
        if item:
            self.initial['tags'] = item.task.tags.all()
        self.fields['work_type'].choices = [(t['key'], t['label']) for t in config['types']]
        self.fields['assignee'].queryset = workplace_people(request.workplace)
        self.fields['team'].queryset = teams_for(request).filter(spaces=space)
        self.fields['section'].queryset = editable_to(TaskSection.objects.filter(project=space.project), request.user)
        self.fields['sprint'].queryset = Sprint.objects.filter(space=space).filter(~Q(state='closed') | Q(pk=getattr(item, 'sprint_id', None)))
        self.fields['epic'].queryset = visible_items(request).filter(space=space, work_type='epic').exclude(pk=getattr(item, 'pk', None))
        self.fields['epic'].label_from_instance = lambda epic: f'{epic.key} · {epic.task.title}'
        if space.template != 'scrum':
            del self.fields['sprint']
            del self.fields['points']
        if not any(t['key'] == 'epic' for t in config['types']):
            del self.fields['epic']
        if space.template not in {'scrum', 'kanban'}:
            del self.fields['in_backlog']
        for field in config.get('fields', []):
            field_class = {'text': forms.CharField, 'number': forms.DecimalField, 'date': forms.DateField}[field['type']]
            options = {'label': field['label'], 'required': field.get('required', False)}
            if field['type'] == 'date':
                options['widget'] = forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
            self.fields['custom_' + field['key']] = field_class(**options)
            if item:
                self.initial['custom_' + field['key']] = item.custom_values.get(field['key'])
        self.style()

    def clean(self):
        data = super().clean()
        if data.get('sprint'):
            data['in_backlog'] = False
        if data.get('work_type') == 'epic' and data.get('epic'):
            self.add_error('epic', 'Epik nie może należeć do innego epika.')
        if self.item and self.item.epic_items.exists() and data.get('work_type') != 'epic':
            self.add_error('work_type', 'Najpierw odłącz zadania należące do tego epika.')
        if data.get('start_on') and data.get('due_at') and data['start_on'] > timezone.localtime(data['due_at']).date():
            self.add_error('due_at', 'Termin nie może być wcześniejszy niż rozpoczęcie.')
        if self.item and self.item.task.parent_id:
            data['section'] = self.item.task.parent.section
        if self.item and data.get('section') and self.item.task.section_id != data['section'].pk:
            try:
                require_movable_task_tree(self.item.task, self.request.user)
            except PermissionDenied:
                self.add_error('section', 'Nie można przenieść zadania z niedostępnymi lub obserwowanymi podzadaniami.')
        return data


class SprintForm(StyledForm):
    name = forms.CharField(label='Nazwa sprintu', max_length=120)
    goal = forms.CharField(label='Cel sprintu', required=False, widget=forms.Textarea(attrs={'rows': 3}))
    start_on = forms.DateField(label='Początek', widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    end_on = forms.DateField(label='Koniec', widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        if data.get('start_on') and data.get('end_on') and data['end_on'] < data['start_on']:
            self.add_error('end_on', 'Koniec nie może być wcześniejszy niż początek.')
        return data


class TeamForm(StyledForm):
    name = forms.CharField(label='Nazwa zespołu', max_length=120)
    description = forms.CharField(label='Opis', required=False, widget=forms.Textarea(attrs={'rows': 3}))
    photo = forms.FileField(label='Zdjęcie zespołu', required=False)
    spaces = forms.ModelMultipleChoiceField(label='Powiązane przestrzenie', queryset=Space.objects.none(), required=False, widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, request, team=None, **kwargs):
        self.request, self.team = request, team
        if team:
            kwargs['initial'] = {'name': team.name, 'description': team.description, 'spaces': team.spaces.all()}
        super().__init__(*args, **kwargs)
        self.fields['spaces'].queryset = visible_spaces(request)

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if teams_for(self.request).filter(name__iexact=name).exclude(pk=getattr(self.team, 'pk', None)).exists():
            raise ValidationError('Zespół o tej nazwie już istnieje.')
        return name

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            validate_image_upload(photo)
        return photo


class MemberForm(StyledForm):
    person = forms.ModelChoiceField(label='Osoba', queryset=None)
    role = forms.ChoiceField(label='Rola', choices=[('member', 'Członek'), ('admin', 'Administrator'), ('observer', 'Obserwator')])

    def __init__(self, *args, request, team=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['person'].queryset = workplace_people(request.workplace)
        self.fields['person'].label_from_instance = lambda user: user.get_full_name() or user.email
        if team:
            self.fields['role'].choices = self.fields['role'].choices[:2]


class StatusForm(StyledForm):
    key = forms.RegexField(label='Klucz', regex=r'^[a-z][a-z0-9_]{0,39}$', max_length=40)
    label = forms.CharField(label='Nazwa statusu', max_length=80)
    category = forms.ChoiceField(label='Stan zadania', choices=Task.STATUS_CHOICES, initial='new')
    transitions = forms.MultipleChoiceField(label='Dozwolone przejścia', required=False)

    def __init__(self, *args, statuses, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transitions'].choices = [(s['key'], s['label']) for s in statuses]


class TypeForm(StyledForm):
    key = forms.RegexField(label='Klucz typu', regex=r'^[a-z][a-z0-9_]{0,39}$', max_length=40)
    label = forms.CharField(label='Nazwa typu', max_length=80)


class CustomFieldForm(TypeForm):
    type = forms.ChoiceField(label='Rodzaj pola', choices=[('text', 'Tekst'), ('number', 'Liczba'), ('date', 'Data')], initial='text')
    required = forms.BooleanField(label='Wymagane', required=False)
