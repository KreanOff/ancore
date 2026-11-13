import re
from copy import deepcopy

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Q
from django.utils import timezone

from accounts.widgets import UserChoiceField
from core.upload_validation import validate_image_crop, validate_image_upload
from core.widgets import VisualSelect
from .access import editable_to
from tasks.models import TaskTag
from core.work_logs import TimeLogForm
from .models import SpaceTask, SpaceTaskWorkLog
from workplaces.services import can_manage_team, workplace_people, workspace_owner
from .defaults import FLOW_STAGES, KINDS, MANAGEMENT, TEMPLATES, ISSUE_TYPE_ICON_CHOICES, STATUS_ICON_CHOICES, classification_options, configuration_name_color, issue_type_icon, status_flow_stage, status_icon
from .avatars import AVATARS, AVATAR_CHOICES, preset_avatar, space_avatar
from .models import Space, SpaceConfiguration, Sprint, Team, WorkItem
from .services import teams_for, transition_allowed, visible_items, visible_spaces
from .schedule import ScheduleDateTimeField, validate_range
from .widgets import IssueTypeSelect, TaskVisibilitySelect, TeamSelect


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
    avatar_photo_crop = forms.CharField(label='Przycięty awatar', required=False, widget=forms.HiddenInput)
    avatar_photo_remove = forms.CharField(label='Usuń obraz', required=False, widget=forms.HiddenInput)

    def __init__(self, *args, space=None, **kwargs):
        self.space = space
        if space:
            kwargs.setdefault('initial', {}).update(avatar='upload' if space.avatar_photo else space.avatar or 'auto')
        super().__init__(*args, **kwargs)
        if space:
            self.current_avatar = space_avatar(space)
            self.automatic_avatar = preset_avatar(seed=space.pk)
            self.avatar_options = [preset_avatar(key) for key, _ in AVATARS]
        else:
            for name in ('avatar', 'avatar_photo', 'avatar_photo_crop', 'avatar_photo_remove'):
                self.fields.pop(name, None)

    def clean_avatar_photo_crop(self):
        return validate_image_crop(self.cleaned_data.get('avatar_photo_crop'))

    def clean(self):
        data = super().clean()
        if not self.space:
            return data
        crop = data.get('avatar_photo_crop')
        if crop:
            data['avatar_photo'] = ContentFile(crop['content'], name='avatar.' + crop['extension'])
        if data.get('avatar_photo'):
            data['avatar'] = 'upload'
        elif data.get('avatar_photo_remove') and data.get('avatar') == 'upload':
            data['avatar'] = 'auto'
        if data.get('avatar') == 'upload' and not data.get('avatar_photo') and not self.space.avatar_photo and not self.errors.get('avatar_photo'):
            self.add_error('avatar_photo', 'Wybierz obraz do przesłania.')
        return data


class SpaceForm(SpaceAvatarForm):
    compact = False
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
            kwargs['initial'] = {'name': space.name, 'description': space.description, 'key': space.key, 'kind': space.kind, 'template': space.template, 'management': space.management, 'configuration': space.configuration_id if space.configuration.shared else None, 'visibility': space.visibility}
        super().__init__(*args, space=space, **kwargs)
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
            self.inline_avatar = True
            self.fields['avatar'].required = False
            # Changing templates/configuration requires an explicit migration of active work.
            for field in ('key', 'kind', 'template', 'management', 'configuration'):
                self.fields[field].disabled = True
            if space.visibility == 'private' and space.private_owner_id != request.user.pk:
                self.fields['visibility'].disabled = True

    def clean_avatar(self):
        if 'avatar' not in self.data:
            return self.initial.get('avatar', 'auto')
        return self.cleaned_data.get('avatar') or 'auto'

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


class SpaceDeleteForm(StyledForm):
    name = forms.CharField(label='Nazwa przestrzeni', max_length=120)
    compact = True
    submit_label = 'Usuń przestrzeń'

    def __init__(self, *args, space, **kwargs):
        self.space = space
        super().__init__(*args, **kwargs)
        self.fields['name'].help_text = f'Wpisz „{space.name}”, aby potwierdzić.'
        self.confirmation_message = (
            f'Usunięcie przestrzeni „{space.name}” trwale usunie jej zadania, podzadania, historię, '
            'załączniki, sprinty, tagi, udostępnienia i powiązane gadżety. '
            'Tej operacji nie można cofnąć.'
        )

    def clean_name(self):
        if self.cleaned_data['name'] != self.space.name:
            raise ValidationError('Wpisz dokładną nazwę przestrzeni.')
        return self.cleaned_data['name']


class ItemForm(StyledForm):
    editable_subtask_status = True
    title = forms.CharField(label='Tytuł', max_length=255)
    description = forms.CharField(label='Opis', required=False, widget=forms.Textarea(attrs={'rows': 3}))
    work_type = forms.ChoiceField(label='Typ zgłoszenia', widget=IssueTypeSelect)
    priority = forms.ChoiceField(label='Priorytet', choices=SpaceTask.PRIORITY_CHOICES, initial='medium')
    tags = forms.ModelMultipleChoiceField(label='Tagi', queryset=TaskTag.objects.none(), required=False, widget=forms.SelectMultiple(attrs={
        'data-ancore-custom-select-search': 'true', 'data-ancore-custom-select-search-placeholder': 'Szukaj tagów',
    }))
    assignee = UserChoiceField(label='Wykonawca', queryset=None, required=False, empty_label='Brak osoby')
    team = forms.ModelChoiceField(label='Zespół', queryset=Team.objects.none(), required=False, widget=TeamSelect)
    in_backlog = forms.BooleanField(label='Umieść w backlogu', required=False)
    sprint = forms.ModelChoiceField(label='Sprint', queryset=Sprint.objects.none(), required=False)
    epic = forms.ModelChoiceField(label='Epik', queryset=WorkItem.objects.none(), required=False)
    points = forms.IntegerField(label='Estymacja (punkty)', min_value=0, max_value=10000, required=False)
    start_at = ScheduleDateTimeField(label='Data rozpoczęcia', required=False, widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}))
    task_type = forms.ChoiceField(label='Kategoria', required=False, initial='general')
    task_group = forms.ChoiceField(label='Grupa', required=False)
    reminder_at = forms.DateTimeField(label='Przypomnienie', required=False, widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local', 'title': 'Powiadomienie w aplikacji dla wykonawcy, a bez wykonawcy — właściciela zadania lub przestrzeni.'}))
    due_at = ScheduleDateTimeField(label='Termin zakończenia', required=False, widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}))

    def __init__(self, *args, request, space, item=None, initial_status=None, **kwargs):
        self.request, self.space, self.item = request, space, item
        if item:
            kwargs['initial'] = {**{key: getattr(item, key) for key in ('work_type', 'team', 'sprint', 'epic', 'points', 'in_backlog', 'start_at')}, **{key: getattr(item.task, key) for key in ('title', 'description', 'priority', 'assignee', 'due_at', 'task_type', 'task_group', 'reminder_at')}}
            if item.task.parent_id:
                kwargs.setdefault('auto_id', f'subtask-{item.pk}-%s')
        super().__init__(*args, **kwargs)
        config = space.configuration.settings
        for name, section in (('task_type', 'categories'), ('task_group', 'groups')):
            options = classification_options(config, section)
            self.fields[name].choices = ([('', 'Brak grupy')] if name == 'task_group' else []) + [(row['key'], row['label']) for row in options]
        categories = dict(self.fields['task_type'].choices)
        self.default_task_type = 'general' if 'general' in categories else next(iter(categories), 'general')
        if not item:
            self.initial['task_type'] = self.default_task_type
        if item:
            for name, value in (('source_status', item.status), ('source_in_backlog', str(item.in_backlog).lower())):
                self.fields[name] = forms.CharField(required=False, widget=forms.HiddenInput)
                self.initial[name] = value
        if not item and initial_status is not None:
            choices = [(status['key'], status['label']) for status in space.statuses]
            self.fields['status'] = forms.ChoiceField(label='Status', choices=choices, widget=VisualSelect(visuals={
                status['key']: {'template': 'core/includes/select_status.html', 'context': {'category': status['category'], 'color': configuration_name_color('statuses', status)}}
                for status in space.statuses
            }))
            default_status = next((status['key'] for status in space.statuses if status_flow_stage(status) == 'queue'), space.statuses[0]['key'])
            self.initial['status'] = initial_status if initial_status in dict(choices) else default_status
            self.order_fields(['title', 'description', 'status'])
        if item and item.task.parent_id and self.editable_subtask_status:
            self.fields['status'] = forms.ChoiceField(label='Status', required=False, choices=[
                (status['key'], status['label']) for status in space.statuses
                if transition_allowed(item, status['key'])
            ])
            self.initial['status'] = item.status
            self.order_fields(['title', 'description', 'status'])
        from tasks.tagging import tags_in_scope
        self.fields['tags'].queryset = tags_in_scope(workspace_owner(request), request.workplace, space)
        if item:
            self.initial['tags'] = item.task.tags.all()
        self.fields['work_type'].choices = [(t['key'], t['label']) for t in config['types']]
        self.fields['work_type'].widget.type_icons = {t['key']: t.get('icon') for t in config['types']}
        self.fields['work_type'].widget.type_colors = {t['key']: configuration_name_color('types', t) for t in config['types']}
        self.fields['assignee'].queryset = workplace_people(request.workplace)
        self.fields['team'].queryset = teams_for(request).filter(spaces=space).select_related('workplace')
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

    def clean_status(self):
        # Older edit forms did not submit status; keep their current value.
        return self.cleaned_data.get('status') or self.item.status

    def clean_task_type(self):
        return self.cleaned_data.get('task_type') or (self.item.task.task_type if self.item else self.default_task_type)

    def clean_task_group(self):
        if self.item and self.add_prefix('task_group') not in self.data:
            return self.item.task.task_group
        return self.cleaned_data.get('task_group') or ''

    def clean(self):
        data = super().clean()
        if data.get('sprint'):
            data['in_backlog'] = False
        if data.get('work_type') == 'epic' and data.get('epic'):
            self.add_error('epic', 'Epik nie może należeć do innego epika.')
        if self.item and self.item.epic_items.exists() and data.get('work_type') != 'epic':
            self.add_error('work_type', 'Najpierw odłącz zadania należące do tego epika.')
        try:
            validate_range(data.get('start_at'), data.get('due_at'))
        except ValidationError as error:
            self.add_error('due_at', error)
        return data


class DetailForm(ItemForm):
    """Issue properties and schedule with unchanged planning values preserved."""
    editable_subtask_status = False
    visibility = forms.ChoiceField(label='Widoczność', required=False, choices=[('private', 'Prywatne — wybrane osoby'), ('public', 'Publiczne — dostęp odziedziczony')], widget=TaskVisibilitySelect)

    def __init__(self, *args, changed_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .services import manage_space
        task = self.item.task
        self.initial['visibility'] = task.visibility
        owner = task.private_owner_id == self.request.user.pk if task.visibility == 'private' else manage_space(self.request, self.space)
        self.fields['visibility'].disabled = not owner
        # Values omitted by autosave come from the locked task, never from POST.
        # They may no longer be selectable (e.g. a former assignee or private epic).
        self.unchanged_relations = {
            name: self.initial.get(name) for name, field in self.fields.items()
            if changed_fields is not None and name not in changed_fields
            and isinstance(field, forms.ModelChoiceField)
        }
        self.complete_fields = self.fields

    def full_clean(self):
        self.fields = {name: field for name, field in self.complete_fields.items()
                       if name not in self.unchanged_relations}
        try:
            super().full_clean()
        finally:
            self.fields = self.complete_fields

    def clean(self):
        # Restore the schema before cross-field validation can add field errors.
        self.fields = self.complete_fields
        self.cleaned_data.update(self.unchanged_relations)
        return super().clean()

    def clean_visibility(self):
        return self.cleaned_data.get('visibility') or self.item.task.visibility

class SubtaskForm(ItemForm):
    """Shared subtask properties, independent of the space's planning template."""
    field_order = ('title', 'description', 'status', 'priority', 'assignee', 'work_type', 'start_at', 'due_at', 'points')
    visibility = forms.ChoiceField(label='Widoczność', required=False, choices=[('public', 'Publiczne — dostęp odziedziczony'), ('private', 'Prywatne — wybrane osoby')], initial='private', widget=forms.HiddenInput)
    status = forms.ChoiceField(label='Status')

    def __init__(self, *args, request, space, item=None, **kwargs):
        super().__init__(*args, request=request, space=space, item=item, **kwargs)
        # ItemForm only exposes points for Scrum; subtasks use the same field
        # and validation in every template.
        if 'points' not in self.fields:
            self.fields['points'] = deepcopy(ItemForm.base_fields['points'])
        names = (*self.field_order, 'visibility') if item is None else (*self.field_order, 'source_status', 'source_in_backlog')
        self.fields = {name: self.fields[name] for name in names}
        if item is None:
            self.fields['status'].choices = [(status['key'], status['label']) for status in space.statuses]
            self.fields['status'].initial = next((status['key'] for status in space.statuses if status_flow_stage(status) == 'queue'), space.statuses[0]['key'])
            self.fields['work_type'].initial = space.configuration.settings['types'][0]['key']
            if self.is_bound:
                # Older modal callers only sent the original subtask fields.
                # Missing new choices retain defaults; explicit empty/invalid
                # choices still go through the normal field validation.
                self.data = self.data.copy()
                for name in ('priority', 'work_type'):
                    self.data.setdefault(self.add_prefix(name), self.fields[name].initial)
        visuals = {
            'status': {status['key']: {'template': 'core/includes/select_status.html', 'context': {'category': status['category'], 'color': configuration_name_color('statuses', status)}}
                       for status in space.statuses},
            'priority': {key: {'template': 'core/includes/select_priority.html', 'context': {'priority': key}}
                         for key, _ in SpaceTask.PRIORITY_CHOICES},
        }
        for name, options in visuals.items():
            self.fields[name].widget = VisualSelect(choices=self.fields[name].choices, visuals=options)
        self.fields['assignee'].widget.attrs['data-ancore-custom-select-icon'] = 'user-round'
        self.style()

    def clean_visibility(self):
        return self.cleaned_data.get('visibility') or 'private'

    def clean(self):
        data = super().clean()
        # The existing epic relation is not edited by this form. Keep it while
        # enforcing the same no-nested-epic rule as the full task form.
        if self.item and self.item.epic_id and data.get('work_type') == 'epic':
            self.add_error('work_type', 'Epik nie może należeć do innego epika.')
        return data


class WorkLogForm(TimeLogForm):
    class Meta(TimeLogForm.Meta):
        model = SpaceTaskWorkLog


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


class SprintCloseForm(StyledForm):
    destination = forms.ModelChoiceField(label='Przenieś niezakończone zadania do', queryset=Sprint.objects.none(), required=False, empty_label='Backlog')
    compact = True
    submit_label = 'Zakończ sprint'

    def __init__(self, *args, space, sprint, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['destination'].queryset = space.sprints.filter(state='planned').exclude(pk=sprint.pk)
        self.fields['destination'].help_text = 'Zakończone zadania pozostaną w tym sprincie. Statusy zadań nie zmienią się.'


class TeamForm(StyledForm):
    name = forms.CharField(label='Nazwa zespołu', max_length=120)
    description = forms.CharField(label='Opis', required=False, widget=forms.Textarea(attrs={'rows': 3}))
    photo = forms.FileField(label='Zdjęcie zespołu', required=False)
    remove_photo = forms.BooleanField(label='Usuń zdjęcie zespołu', required=False)
    spaces = forms.ModelMultipleChoiceField(label='Powiązane przestrzenie', queryset=Space.objects.none(), required=False, widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, request, team=None, **kwargs):
        self.request, self.team = request, team
        if team:
            kwargs['initial'] = {'name': team.name, 'description': team.description, 'spaces': team.spaces.filter(pk__in=visible_spaces(request))}
        super().__init__(*args, **kwargs)
        self.fields['spaces'].queryset = visible_spaces(request)
        self.fields['spaces'].help_text = 'Powiązanie przestrzeni nie zmienia uprawnień jej członków.'
        self.fields['photo'].widget.attrs['accept'] = 'image/png,image/jpeg,image/webp'
        if not team or not team.photo:
            self.fields.pop('remove_photo')

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

    def clean(self):
        data = super().clean()
        if data.get('photo') and data.get('remove_photo'):
            self.add_error('remove_photo', 'Wybierz nowe zdjęcie albo usuń obecne.')
        return data


class TeamDeleteForm(StyledForm):
    name = forms.CharField(label='Nazwa zespołu', max_length=120)
    compact = True
    submit_label = 'Usuń zespół'

    def __init__(self, *args, team, **kwargs):
        self.team = team
        super().__init__(*args, **kwargs)
        self.fields['name'].help_text = f'Wpisz „{team.name}”, aby potwierdzić. Zadania i przestrzenie pozostaną; usunięte zostanie ich powiązanie z zespołem.'

    def clean_name(self):
        if self.cleaned_data['name'] != self.team.name:
            raise ValidationError('Wpisz dokładną nazwę zespołu.')
        return self.cleaned_data['name']


class MemberForm(StyledForm):
    person = forms.ModelChoiceField(label='Osoba', queryset=None)
    role = forms.ChoiceField(label='Rola', choices=[('member', 'Członek'), ('admin', 'Administrator'), ('observer', 'Obserwator')])

    def __init__(self, *args, request, team=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['person'].queryset = workplace_people(request.workplace)
        self.fields['person'].label_from_instance = lambda user: user.get_full_name() or user.email
        if team:
            self.fields['role'].choices = self.fields['role'].choices[:2]
            self.fields['person'].empty_label = 'Wybierz osobę'


class ConfigurationColorField(forms.CharField):
    def __init__(self):
        super().__init__(label='Kolor nazwy', required=False, max_length=7,
                         help_text='Wybierz kolor lub wpisz #RRGGBB. Puste pole przywraca kolor domyślny.',
                         widget=forms.TextInput(attrs={'pattern': '#?[0-9a-fA-F]{6}'}))

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return ''
        if not re.fullmatch(r'#?[0-9a-fA-F]{6}', value):
            raise forms.ValidationError('Podaj kolor w formacie #RRGGBB.')
        return '#' + value.lstrip('#').lower()


class StatusForm(StyledForm):
    key = forms.RegexField(label='Klucz', regex=r'^[a-z][a-z0-9_]{0,39}$', max_length=40,
                           help_text='Małe litery, cyfry i podkreślenia; pierwszym znakiem musi być litera. Klucza etapu używanego przez zadania nie można zmienić.',
                           widget=forms.TextInput(attrs={'pattern': '[a-z][a-z0-9_]{0,39}'}))
    label = forms.CharField(label='Nazwa etapu', max_length=80)
    color = ConfigurationColorField()
    category = forms.ChoiceField(label='Stan zadania', choices=SpaceTask.STATUS_CHOICES, initial='in_progress')
    flow_stage = forms.ChoiceField(label='Etap przepływu', choices=FLOW_STAGES, initial='active',
                                  help_text='Kolejka jest przed rozpoczęciem pracy; praca w toku trwa do zakończenia.')
    wip_limit = forms.IntegerField(label='Limit pracy w toku (WIP)', required=False, min_value=1,
                                  help_text='Maksymalna liczba zadań w tej kolumnie całej Przestrzeni. Puste pole oznacza brak limitu.')
    policy = forms.CharField(label='Zasady wejścia i wyjścia', required=False, max_length=1000,
                             widget=forms.Textarea(attrs={'rows': 3}))
    icon = forms.ChoiceField(label='Ikona', required=False,
                             choices=[('', 'Domyślna dla etapu'), *STATUS_ICON_CHOICES],
                             widget=VisualSelect)
    transitions = forms.MultipleChoiceField(label='Dozwolone przejścia', required=False)
    position_x = forms.IntegerField(label='Położenie poziome etapu', required=False, min_value=-1000000, max_value=1000000,
                                    widget=forms.HiddenInput)
    position_y = forms.IntegerField(label='Położenie pionowe etapu', required=False, min_value=-1000000, max_value=1000000,
                                    widget=forms.HiddenInput)

    def __init__(self, *args, statuses, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial = dict(self.initial)
        self.fields['transitions'].choices = [(s['key'], s['label']) for s in statuses]
        if self.initial:
            self.initial.setdefault('flow_stage', status_flow_stage(self.initial))
            position = self.initial.get('position') or {}
            self.initial.update(position_x=position.get('x'), position_y=position.get('y'))
        saved = self.initial
        if self.is_bound:
            # Full formset submissions from older clients must retain metadata.
            self.data = self.data.copy()
            key = self.data.get(self.add_prefix('key'))
            saved = next((status for status in statuses if status['key'] == key and 'category' in status), self.initial)
            for name in ('category', 'flow_stage', 'wip_limit', 'policy', 'icon', 'color'):
                if self.add_prefix(name) not in self.data:
                    fallback = ('in_progress' if name == 'category' else
                                status_flow_stage({'category': self.data.get(self.add_prefix('category')), **saved})
                                if name == 'flow_stage' else '')
                    self.data[self.add_prefix(name)] = saved.get(name, fallback) or ''
            for axis in ('x', 'y'):
                name = self.add_prefix('position_' + axis)
                if name not in self.data:
                    self.data[name] = (saved.get('position') or {}).get(axis, '')
        # A previously saved type icon may stay on its own stage. It is not
        # offered to other stages or accepted as a new status icon.
        saved_icon = saved.get('icon')
        legacy_label = dict(ISSUE_TYPE_ICON_CHOICES).get(saved_icon) if isinstance(saved_icon, str) else None
        if legacy_label:
            self.fields['icon'].choices = [*self.fields['icon'].choices,
                                           (saved_icon, f'Dotychczasowa ikona: {legacy_label}')]
        category = self['category'].value()
        self.fields['color'].widget.attrs['placeholder'] = configuration_name_color('statuses', {'category': category})
        self.fields['icon'].widget.visuals = {
            '': {'icon': status_icon({'category': category})},
            **{icon: {'icon': icon} for icon, _ in self.fields['icon'].choices if icon},
        }
        if legacy_label:
            self.fields['icon'].widget.visuals[saved_icon]['preserve_only'] = True
        if self['flow_stage'].value() != 'active':
            self.fields['wip_limit'].widget.attrs['readonly'] = True
            self.fields['wip_limit'].help_text = 'Limit WIP jest dostępny wyłącznie dla etapów pracy w toku.'

    def clean(self):
        data = super().clean()
        category, stage = data.get('category'), data.get('flow_stage')
        if category and stage and (category == 'closed') != (stage == 'done'):
            self.add_error('flow_stage', 'Etap „Zakończone” wymaga stanu „Zamknięte”, a pozostałe stany wymagają kolejki lub pracy w toku.')
        if data.get('wip_limit') is not None and stage != 'active':
            self.add_error('wip_limit', 'Limit WIP można ustawić wyłącznie dla pracy w toku.')
        x, y = data.pop('position_x', None), data.pop('position_y', None)
        if (x is None) != (y is None):
            self.add_error(None, 'Położenie etapu wymaga obu współrzędnych tablicy.')
        elif x is not None:
            data['position'] = {'x': x, 'y': y}
        if not data.get('icon'):
            data.pop('icon', None)
        if not data.get('color'):
            data.pop('color', None)
        return data


class ConfigurationLabelForm(StyledForm):
    key = forms.RegexField(label='Klucz typu', regex=r'^[a-z][a-z0-9_]{0,39}$', max_length=40)
    label = forms.CharField(label='Nazwa typu', max_length=80)


class TypeForm(ConfigurationLabelForm):
    color = ConfigurationColorField()
    icon = forms.ChoiceField(label='Ikona', required=False,
                             choices=[('', 'Domyślna dla typu'), *ISSUE_TYPE_ICON_CHOICES],
                             widget=VisualSelect)
    description = forms.CharField(label='Opis', required=False, max_length=500,
                                  widget=forms.Textarea(attrs={'rows': 3}),
                                  help_text='Wyjaśnij, kiedy używać tego typu zgłoszenia.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            # Older clients still submit only key/label. Explicit empty values
            # clear metadata; an omitted field keeps its previously saved value.
            self.data = self.data.copy()
            for name in ('icon', 'description', 'color'):
                if self.add_prefix(name) not in self.data and name in self.initial:
                    self.data[self.add_prefix(name)] = self.initial[name]
        key = self.data.get(self.add_prefix('key'), '') if self.is_bound else self.initial.get('key', '')
        self.fields['color'].widget.attrs['placeholder'] = configuration_name_color('types', {'key': key})
        self.fields['icon'].widget.visuals = {
            '': {'icon': issue_type_icon(key)},
            **{icon: {'icon': icon} for icon, _ in ISSUE_TYPE_ICON_CHOICES},
        }

    def clean(self):
        data = super().clean()
        # Keep old JSON rows unchanged when their optional metadata is empty.
        for name in ('icon', 'description', 'color'):
            if not data.get(name):
                data.pop(name, None)
        return data


class ClassificationForm(ConfigurationLabelForm):
    subject = 'grupy'
    description = forms.CharField(label='Opis', required=False, max_length=500,
                                  widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['key'].label = f'Klucz {self.subject}'
        self.fields['label'].label = f'Nazwa {self.subject}'
        self.fields['description'].help_text = f'Wyjaśnij, kiedy używać tej {self.subject}.'
        if self.is_bound and self.add_prefix('description') not in self.data and 'description' in self.initial:
            self.data = self.data.copy()
            self.data[self.add_prefix('description')] = self.initial['description']

    def clean(self):
        data = super().clean()
        if not data.get('description'):
            data.pop('description', None)
        # Appearance is no longer edited or displayed for classifications.
        # Keep earlier metadata in storage without accepting new appearance input.
        for name in ('icon', 'color'):
            if name in self.initial:
                data[name] = self.initial[name]
        return data


class CategoryForm(ClassificationForm):
    subject = 'kategorii'
    key = forms.RegexField(label='Klucz kategorii', regex=r'^[a-z][a-z0-9_]{0,19}$', max_length=20)


class GroupForm(ClassificationForm):
    pass


class CustomFieldForm(ConfigurationLabelForm):
    type = forms.ChoiceField(label='Rodzaj pola', choices=[('text', 'Tekst'), ('number', 'Liczba'), ('date', 'Data')], initial='text')
    required = forms.BooleanField(label='Wymagane', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['key'].label = 'Klucz pola'
        self.fields['label'].label = 'Nazwa pola'
