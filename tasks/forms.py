from datetime import UTC, timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.utils import timezone

from accounts.widgets import UserChoiceField, UserSelect
from tasks.access import editable_to, visible_to
from tasks.hierarchy import save_task_edit
from workplaces.services import workplace_people

from contacts.models import Company
from .models import (
    Task,
    TaskAttachment,
    TaskProject,
    TaskProjectTemplate,
    TaskSection,
    TaskTag,
    TaskWorkLog,
)


class LenientModelChoiceField(forms.ModelChoiceField):
    def clean(self, value):
        if value in self.empty_values:
            return None
        try:
            return super().clean(value)
        except forms.ValidationError:
            return None


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = 'datetime-local'

    def __init__(self, attrs=None, format=None):
        super().__init__(attrs=attrs, format=format or '%Y-%m-%dT%H:%M')


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


DATETIME_LOCAL_INPUT_FORMATS = ['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S']


def _crm_user_queryset(user, workplace=None):
    return workplace_people(workplace, user)


def _filter_workplace(queryset, workplace):
    if workplace is None:
        return queryset
    return queryset.filter(workplace=workplace)


def _company_queryset(user, workplace=None):
    if not user:
        return Company.objects.none()
    return _filter_workplace(Company.objects.filter(owner=user), workplace).order_by('name')


def _replace_optional_model_choice(form, field_name, queryset, empty_label):
    if field_name not in form.fields:
        return
    current = form.fields[field_name]
    if field_name == 'assignee':
        field_class = UserChoiceField
    elif field_name in {'responsible_user', 'owner'}:
        field_class = forms.ModelChoiceField
    else:
        field_class = LenientModelChoiceField
    form.fields[field_name] = field_class(
        queryset=queryset,
        required=False,
        label=current.label,
        widget=current.widget,
        help_text=current.help_text,
        empty_label=empty_label,
    )


def _normalize_optional_code(value):
    return (value or '').strip().upper()


class ProjectVisibilitySelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        icon = {'private': 'lock', 'public': 'users'}.get(value)
        if icon:
            option['attrs']['data-ancore-option-icon'] = icon
        return option


class TaskAccessForm(forms.ModelForm):
    visibility = forms.ChoiceField(
        choices=[('private', 'Prywatne — wybrane osoby'), ('public', 'Publiczne — dostęp odziedziczony')],
        required=False, label='Widoczność',
        widget=ProjectVisibilitySelect(attrs={'class': 'tasks-inline-select'}),
    )

    def __init__(self, *args, **kwargs):
        self.viewer = kwargs.pop('viewer', None)
        super().__init__(*args, **kwargs)
        self.original_visibility = self.instance.visibility
        self.can_manage_access = (not self.instance.pk or self.instance.visibility == 'public'
                                  or self.instance.private_owner_id == getattr(self.viewer, 'pk', None))
        self.fields['visibility'].widget.attrs['id'] = 'task-visibility' if self.instance.pk else 'task-create-visibility'
        if not self.instance.pk:
            self.initial['visibility'] = 'private'

    def clean_visibility(self):
        value = self.cleaned_data.get('visibility') or (self.original_visibility if self.instance.pk else 'private')
        if not self.can_manage_access and value != self.original_visibility:
            raise forms.ValidationError('Tylko właściciel prywatnego zadania może zmienić widoczność.')
        return value

    def clean(self):
        cleaned = super().clean()
        if self.data.get('sharing_present') or self.data.get('shared_with'):
            raise forms.ValidationError('Udostępniaj w zakładce „Członkowie”. Odśwież formularz.')
        return cleaned

    def _save_m2m(self):
        super()._save_m2m()
        if self.can_manage_access and self.instance.visibility == 'public':
            self.instance.shared_with.clear()

    def save(self, commit=True):
        task = super().save(commit=False)
        if task.visibility == 'private':
            # A deleted private owner must never be replaced by a regular member.
            if not task.pk or self.original_visibility == 'public':
                task.private_owner = self.viewer
        else:
            task.private_owner = None
        if commit:
            if task.pk and self.viewer:
                save_task_edit(task, self.viewer)
            else:
                task.save()
            self.save_m2m()
        return task


class TaskForm(TaskAccessForm):
    work_type = forms.ChoiceField(label='Typ zgłoszenia', required=False)
    project = forms.ModelChoiceField(
        queryset=TaskProject.objects.none(),
        required=False,
        label='Przestrzeń',
        widget=forms.Select(attrs={
            'class': 'form-input'
        }),
    )
    parent = forms.ModelChoiceField(
        queryset=Task.objects.none(),
        required=False,
        label='Zadanie',
        widget=forms.Select(attrs={
            'class': 'form-input'
        }),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        viewer = kwargs.pop('viewer', None) or user
        workplace = kwargs.pop('workplace', None)
        project = kwargs.pop('project', None)
        section = kwargs.pop('section', None)
        read_only = kwargs.pop('read_only', False)
        relation_scope = visible_to if read_only else editable_to
        super().__init__(*args, viewer=viewer, **kwargs)
        if workplace is None and section is not None:
            workplace = getattr(section.project, 'workplace', None)
        if user:
            projects = _filter_workplace(relation_scope(TaskProject.objects.all(), viewer).filter(user=user), workplace).prefetch_related(Prefetch('sections', queryset=relation_scope(TaskSection.objects.all(), viewer)))
            sections = relation_scope(TaskSection.objects.all(), viewer).filter(project__user=user).select_related('project')
            if workplace is not None:
                sections = sections.filter(project__workplace=workplace)
            parents = Task.objects.none()
            if getattr(self.instance, 'parent_id', None):
                parents = relation_scope(Task.objects.all(), viewer).filter(user=user, parent__isnull=True, section_id=self.instance.section_id).order_by('task_id')
                if workplace is not None:
                    parents = parents.filter(workplace=workplace)
                if self.instance and self.instance.pk:
                    parents = parents.exclude(pk=self.instance.pk)
            self.fields['project'].queryset = projects
            self.fields['section'].queryset = sections
            self.fields['parent'].queryset = parents
            from .tagging import form_tags
            self.fields['tags'].queryset = form_tags(self, user, workplace, project, section)
            _replace_optional_model_choice(self, 'assignee', _crm_user_queryset(user, workplace), 'Brak osoby')
        else:
            _replace_optional_model_choice(self, 'assignee', get_user_model().objects.none(), 'Brak osoby')
        current_section = section or getattr(self.instance, 'section', None)
        if current_section:
            self.fields['project'].initial = current_section.project
            self.fields['section'].initial = current_section
        elif project:
            self.fields['project'].initial = project
        self.fields['section'].required = False
        self.fields['section'].label = 'Grupa przestrzeni'
        self.fields['parent'].required = bool(getattr(self.instance, 'parent_id', None))
        self.fields['title'].label = 'Tytuł'
        self.fields['description'].label = 'Opis'
        self.fields['tags'].required = False
        self.fields['tags'].label = 'Tagi'
        self.fields['due_at'].label = 'Termin wykonania'
        self.fields['due_at'].input_formats = DATETIME_LOCAL_INPUT_FORMATS
        self.fields['reminder_at'].label = 'Przypomnienie'
        self.fields['reminder_at'].widget.attrs['title'] = 'Powiadomienie w aplikacji dla wykonawcy, a bez wykonawcy — właściciela prywatnego zadania, projektu lub Workspace.'
        self.fields['reminder_at'].input_formats = DATETIME_LOCAL_INPUT_FORMATS
        self.fields['assignee'].label = 'Przypisane do'
        self.fields['task_type'].label = 'Kategoria zadania'
        self.fields['task_type'].required = False
        from spaces.defaults import template_settings
        from spaces.models import WorkItem
        from spaces.widgets import IssueTypeSelect
        self.issue_item = WorkItem.objects.filter(task=self.instance).select_related('space__configuration').first() if self.instance.pk else None
        type_section = current_section
        if self.is_bound and not self.instance.pk:
            section_value = self.data.get(self.add_prefix('section'), '')
            type_section = sections.filter(pk=int(section_value)).first() if section_value.isdecimal() and len(section_value) < 19 and user else None
            parent_value = self.data.get(self.add_prefix('parent'), '')
            if parent_value.isdecimal() and len(parent_value) < 19:
                type_parent = self.fields['parent'].queryset.filter(pk=int(parent_value)).first()
                if type_parent:
                    type_section = type_parent.section
        type_space = getattr(type_section.project, 'space', None) if type_section else None
        config = type_space.configuration.settings if type_space else template_settings()
        self.fields['work_type'].widget = IssueTypeSelect(attrs={'class': 'form-input'})
        self.fields['work_type'].choices = [(row['key'], row['label']) for row in config['types']]
        self.initial['work_type'] = self.issue_item.work_type if self.issue_item else config['types'][0]['key']
        if self.instance.pk:
            del self.fields['project']
            del self.fields['section']

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')
        if self.instance.pk and cleaned_data.get('status'):
            from spaces.services import category_transition_allowed
            if not category_transition_allowed(self.instance, cleaned_data['status']):
                self.add_error('status', 'To przejście statusu nie jest dozwolone w przestrzeni.')
        project = cleaned_data.get('project')
        section = self.instance.section if self.instance.pk else cleaned_data.get('section')
        if parent and not self.instance.pk:
            cleaned_data['section'] = parent.section
            section = parent.section
            if section:
                cleaned_data['project'] = section.project
                project = section.project
        if section and not project and not self.instance.pk:
            cleaned_data['project'] = section.project
            project = section.project
        if project and section and section.project_id != project.id:
            self.add_error('section', 'Wybierz grupę z wybranego projektu.')
        if project and not section and 'section' not in self.errors:
            self.add_error('section', 'Wybierz grupę z wybranego projektu lub usuń wybór projektu.')
        work_type = cleaned_data.get('work_type')
        if self.issue_item and work_type:
            if self.issue_item.epic_items.exists() and work_type != 'epic':
                self.add_error('work_type', 'Najpierw odłącz zadania należące do tego epika.')
            if work_type == 'epic' and self.issue_item.epic_id:
                self.add_error('work_type', 'Najpierw odłącz zadanie od epika w „Planowanie i zespół”.')
        return cleaned_data

    def _save_m2m(self):
        super()._save_m2m()
        if self.cleaned_data.get('work_type'):
            from spaces.models import WorkItem
            item = WorkItem.objects.select_for_update().get(task=self.instance)
            item.work_type = self.cleaned_data['work_type']
            item.save(update_fields=['work_type'])
            self.instance._state.fields_cache.pop('work_item', None)

    def clean_task_type(self):
        return self.cleaned_data.get('task_type') or 'general'

    class Meta:
        model = Task
        fields = [
            'title',
            'visibility',
            'parent',
            'section',
            'tags',
            'description',
            'task_type',
            'assignee',
            'priority',
            'status',
            'due_at',
            'reminder_at',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Wprowadź tytuł zadania...',
                'class': 'form-input'
            }),
            'section': forms.Select(attrs={
                'class': 'form-input'
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'form-input tasks-tag-select',
                'size': 4,
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Wprowadź opis zadania...',
                'rows': 4,
                'class': 'form-input'
            }),
            'task_type': forms.Select(attrs={
                'class': 'form-input'
            }),
            'assignee': UserSelect(attrs={
                'class': 'form-input'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-input'
            }),
            'status': forms.Select(attrs={
                'class': 'form-input'
            }),
            'due_at': DateTimeLocalInput(attrs={
                'class': 'form-input tasks-due-input',
            }),
            'reminder_at': DateTimeLocalInput(attrs={
                'class': 'form-input',
            }),
        }


class TaskWorkLogForm(forms.ModelForm):
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
        model = TaskWorkLog
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


class TaskProjectBaseForm(forms.ModelForm):
    visibility = forms.ChoiceField(
        choices=[('private', 'Prywatny — wybrane osoby'), ('public', 'Publiczny — cały Workspace')], required=False, label='Widoczność',
        widget=ProjectVisibilitySelect(attrs={'class': 'tasks-inline-select'}),
    )
    def clean_visibility(self):
        # An older open form must not accidentally publish a private project.
        default = self.instance.visibility if self.instance.pk else TaskProject.Visibility.PRIVATE
        value = self.cleaned_data.get('visibility') or default
        if not self.can_manage_access and value != self.instance.visibility:
            raise forms.ValidationError('Tylko właściciel prywatnego projektu może zmienić widoczność.')
        return value

    def clean(self):
        cleaned = super().clean()
        if self.data.get('sharing_present') or self.data.get('shared_with'):
            raise forms.ValidationError('Udostępniaj w zakładce „Członkowie”. Odśwież formularz.')
        return cleaned

    def _save_m2m(self):
        if self.can_manage_access and self.instance.visibility == 'public':
            self.instance.shared_with.clear()
            self.instance.invitations.filter(status='pending').update(status='revoked')

    def save(self, commit=True):
        project = super().save(commit=False)
        if project.visibility == TaskProject.Visibility.PRIVATE:
            if not project.private_owner_id:
                project.private_owner = self.viewer
        else:
            project.private_owner = None
        if commit:
            project.save()
            self.save_m2m()
        return project

    source = forms.CharField(
        required=False,
        max_length=120,
        label='Źródło',
        widget=forms.Select(attrs={
            'class': 'tasks-inline-select',
            'data-ancore-custom-select-search': 'true',
            'data-ancore-custom-select-search-placeholder': 'Wpisz własne źródło lub szukaj',
            'data-ancore-custom-select-allow-custom': 'true',
            'data-ancore-custom-select-max-length': '120',
            'data-ancore-custom-select-placement': 'auto',
        }),
    )
    status = forms.ChoiceField(
        required=False,
        label='Status projektu',
        widget=forms.Select(attrs={'class': 'tasks-inline-select'}),
    )
    stage = forms.ChoiceField(
        required=False,
        label='Etap',
        widget=forms.Select(attrs={'class': 'tasks-inline-select'}),
    )
    health = forms.ChoiceField(
        required=False,
        label='Kondycja',
        widget=forms.Select(attrs={'class': 'tasks-inline-select'}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        viewer = kwargs.pop('viewer', None) or user
        workplace = kwargs.pop('workplace', None)
        super().__init__(*args, **kwargs)
        self.viewer = viewer
        self.can_manage_access = (not self.instance.pk or self.instance.visibility == 'public'
                                  or self.instance.private_owner_id == getattr(viewer, 'pk', None))
        if "visibility" in self.fields:
            self.fields["visibility"].widget.attrs["id"] = (
                "project-rename-visibility" if isinstance(self, TaskProjectRenameForm) else "project-create-visibility"
            )
        if 'company' in self.fields:
            _replace_optional_model_choice(self, 'company', _company_queryset(user, workplace), 'Brak firmy')
            self.fields['company'].widget.attrs['data-ancore-custom-select-search'] = 'true'
            self.fields['company'].widget.attrs['data-ancore-custom-select-search-placeholder'] = 'Szukaj firmy'
        if 'responsible_user' in self.fields:
            _replace_optional_model_choice(self, 'responsible_user', _crm_user_queryset(user, workplace), 'Brak osoby')
            self.fields['responsible_user'].widget.attrs['data-ancore-custom-select-search'] = 'true'
            self.fields['responsible_user'].widget.attrs['data-ancore-custom-select-search-placeholder'] = 'Szukaj osoby'
        option_choices = {
            'status': list(TaskProject.STATUS_CHOICES),
            'stage': list(TaskProject.STAGE_CHOICES),
            'health': list(TaskProject.HEALTH_CHOICES),
        }
        # Preserve historical values in the shared edit modal without a settings dictionary.
        if user:
            projects = visible_to(TaskProject.objects.all(), viewer).filter(user=user, workplace=workplace)
            for name, choices in option_choices.items():
                known = {value for value, _label in choices}
                choices.extend((value, value) for value in projects.exclude(**{name: ''})
                               .order_by(name).values_list(name, flat=True).distinct() if value not in known)
        for name, choices in option_choices.items():
            value = getattr(self.instance, name, '')
            if self.instance.pk and value and value not in {key for key, _label in choices}:
                choices.append((value, value))
        if 'source' in self.fields:
            sources = option_choices.get('source', [])
            known_sources = {value for value, _label in sources}
            # Include legacy/imported text values in the shared edit modal as well.
            if user:
                legacy_sources = (
                    visible_to(TaskProject.objects.all(), viewer).filter(user=user, workplace=workplace)
                    .exclude(source='').order_by('source').values_list('source', flat=True).distinct()
                )
                sources = sources + [(value, value) for value in legacy_sources if value not in known_sources]
            elif self.instance and self.instance.source and self.instance.source not in known_sources:
                sources = sources + [(self.instance.source, self.instance.source)]
            if self.is_bound:
                submitted_source = (self.data.get(self.add_prefix('source')) or '').strip()
                if submitted_source and submitted_source not in {value for value, _label in sources}:
                    sources.append((submitted_source, submitted_source))
            self.fields['source'].widget.choices = [('', 'Brak źródła'), *sources]
        self._project_field_defaults = {}
        for field_name in ('status', 'stage', 'health'):
            if field_name in self.fields:
                self.fields[field_name].required = False
                self.fields[field_name].choices = option_choices.get(field_name, [])
                self.fields[field_name].widget.choices = self.fields[field_name].choices
                available_values = [value for value, _label in self.fields[field_name].choices]
                model_default = TaskProject._meta.get_field(field_name).default
                field_default = model_default if model_default in available_values else (available_values[0] if available_values else '')
                self._project_field_defaults[field_name] = field_default
                if not self.is_bound and not getattr(self.instance, 'pk', None):
                    self.initial[field_name] = field_default

    def clean_code(self):
        code = _normalize_optional_code(self.cleaned_data.get('code'))
        if not code:
            return ''

        instance = self.instance or self._meta.model()
        for model in instance._code_scope_models():
            queryset = model.objects.filter(code=code)
            if model is self._meta.model and self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Taki kod projektu już istnieje.')
        return code

    def clean_priority(self):
        return self.cleaned_data.get('priority') or 'none'

    def clean_status(self):
        return self.cleaned_data.get('status') or self._project_field_defaults.get('status') or 'active'

    def clean_stage(self):
        return self.cleaned_data.get('stage') or self._project_field_defaults.get('stage') or 'implementation'

    def clean_health(self):
        return self.cleaned_data.get('health') or self._project_field_defaults.get('health') or 'ok'


class TaskProjectTemplateNameForm(forms.ModelForm):
    class Meta:
        model = TaskProjectTemplate
        fields = ('template_name',)
        widgets = {
            'template_name': forms.TextInput(attrs={
                'class': 'tasks-inline-input', 'id': 'project-template-rename-name',
                'placeholder': 'Nazwa szablonu',
            }),
        }


class TaskProjectForm(TaskProjectBaseForm):
    template = forms.ModelChoiceField(
        queryset=TaskProjectTemplate.objects.none(), required=False, label='Szablon projektu',
        empty_label='Bez szablonu',
        widget=forms.Select(attrs={'class': 'tasks-inline-select', 'data-project-template-select': '',
                                   'data-ancore-custom-select-search': 'true'}),
    )

    def __init__(self, *args, **kwargs):
        user, workplace = kwargs.get('user'), kwargs.get('workplace')
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial['visibility'] = TaskProject.Visibility.PRIVATE
        if user:
            self.fields['template'].queryset = visible_to(TaskProjectTemplate.objects.all(), self.viewer).filter(user=user, workplace=workplace)

    section_title = forms.CharField(
        required=False,
        label='Nazwa grupy',
        widget=forms.TextInput(attrs={
            'placeholder': 'Nowa Grupa',
            'class': 'tasks-inline-input',
        }),
    )
    section_code = forms.CharField(
        required=False,
        label='Kod pierwszej grupy',
        max_length=20,
        widget=forms.TextInput(attrs={
            'id': 'project-create-section-code',
            'placeholder': 'Kod grupy',
            'class': 'tasks-inline-input',
            'maxlength': 20,
        }),
    )

    def clean_section_title(self):
        return (self.cleaned_data.get('section_title') or '').strip()

    def clean_section_code(self):
        return _normalize_optional_code(self.cleaned_data.get('section_code'))

    class Meta:
        model = TaskProject
        fields = [
            'name',
            'visibility',
            'template',
            'code',
            'section_title',
            'section_code',
            'description',
            'company',
            'responsible_user',
            'status',
            'stage',
            'health',
            'priority',
            'start_at',
            'due_at',
            'source',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nowy projekt',
                'class': 'tasks-inline-input',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Dodaj opis...',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
            'code': forms.TextInput(attrs={
                'id': 'project-create-code',
                'placeholder': 'Kod projektu',
                'class': 'tasks-inline-input',
                'maxlength': 20,
            }),
            'priority': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'company': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'responsible_user': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'status': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'stage': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'health': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'start_at': forms.DateInput(format='%Y-%m-%d', attrs={
                'type': 'date',
                'class': 'tasks-inline-input',
            }),
            'due_at': forms.DateInput(format='%Y-%m-%d', attrs={
                'type': 'date',
                'class': 'tasks-inline-input',
            }),
        }
        labels = {
            'code': 'Kod projektu',
            'company': 'Firma',
            'responsible_user': 'Odpowiedzialny',
            'status': 'Status projektu',
            'stage': 'Etap',
            'health': 'Kondycja',
            'priority': 'Priorytet',
            'start_at': 'Start',
            'due_at': 'Termin',
            'source': 'Źródło',
        }


class TaskProjectRenameForm(TaskProjectBaseForm):
    class Meta:
        model = TaskProject
        fields = [
            'name',
            'visibility',
            'code',
            'description',
            'company',
            'responsible_user',
            'status',
            'stage',
            'health',
            'priority',
            'start_at',
            'due_at',
            'source',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nazwa projektu',
                'class': 'tasks-inline-input',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Dodaj opis...',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
            'code': forms.TextInput(attrs={
                'id': 'project-rename-code-field',
                'placeholder': 'Kod projektu',
                'class': 'tasks-inline-input',
                'maxlength': 20,
            }),
            'priority': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'company': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'responsible_user': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'status': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'stage': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'health': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'start_at': forms.DateInput(format='%Y-%m-%d', attrs={
                'type': 'date',
                'class': 'tasks-inline-input',
            }),
            'due_at': forms.DateInput(format='%Y-%m-%d', attrs={
                'type': 'date',
                'class': 'tasks-inline-input',
            }),
        }
        labels = {
            'code': 'Kod projektu',
            'company': 'Firma',
            'responsible_user': 'Odpowiedzialny',
            'status': 'Status projektu',
            'stage': 'Etap',
            'health': 'Kondycja',
            'priority': 'Priorytet',
            'start_at': 'Start',
            'due_at': 'Termin',
            'source': 'Źródło',
        }


class TaskSectionAccessForm(forms.ModelForm):
    visibility = forms.ChoiceField(
        choices=[('private', 'Prywatna — wybrane osoby'), ('public', 'Publiczna — uczestnicy projektu')],
        required=False, label='Widoczność',
        widget=ProjectVisibilitySelect(attrs={'class': 'tasks-inline-select'}),
    )

    def __init__(self, *args, **kwargs):
        self.viewer = kwargs.pop('viewer', None) or kwargs.get('user')
        super().__init__(*args, **kwargs)
        self.can_manage_access = (not self.instance.pk or self.instance.visibility == 'public'
                                  or self.instance.private_owner_id == getattr(self.viewer, 'pk', None))
        self.fields['visibility'].widget.attrs['id'] = (
            'section-rename-visibility' if self.instance.pk or isinstance(self, TaskSectionRenameForm)
            else 'section-create-visibility'
        )
        if not self.instance.pk:
            self.initial['visibility'] = 'private'

    def clean_visibility(self):
        value = self.cleaned_data.get('visibility') or (self.instance.visibility if self.instance.pk else 'private')
        if not self.can_manage_access and value != self.instance.visibility:
            raise forms.ValidationError('Tylko właściciel prywatnej grupy może zmienić widoczność.')
        return value

    def clean(self):
        cleaned = super().clean()
        if self.data.get('sharing_present') or self.data.get('shared_with'):
            raise forms.ValidationError('Udostępniaj w zakładce „Członkowie”. Odśwież formularz.')
        return cleaned

    def _save_m2m(self):
        if self.can_manage_access and self.instance.visibility == 'public':
            self.instance.shared_with.clear()
            self.instance.invitations.filter(status='pending').update(status='revoked')

    def save(self, commit=True):
        section = super().save(commit=False)
        if section.visibility == 'private':
            if not section.private_owner_id:
                section.private_owner = self.viewer
        else:
            section.private_owner = None
        if commit:
            section.save()
            self.save_m2m()
        return section


class TaskSectionForm(TaskSectionAccessForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        kwargs.setdefault('viewer', user)
        self.project_for_validation = kwargs.pop('project', None)
        workplace = kwargs.pop('workplace', None)
        super().__init__(*args, **kwargs)
        if self.project_for_validation is None:
            self.project_for_validation = getattr(self.instance, 'project', None)
        workplace = workplace or getattr(self.project_for_validation, 'workplace', None)
        _replace_optional_model_choice(self, 'owner', _crm_user_queryset(user, workplace), 'Brak osoby')
        self.fields['owner'].widget.attrs['data-ancore-custom-select-search'] = 'true'
        self.fields['owner'].widget.attrs['data-ancore-custom-select-search-placeholder'] = 'Szukaj osoby'
        self.fields['kind'].required = False
        self.fields['status'].required = False

    def clean_code(self):
        code = _normalize_optional_code(self.cleaned_data.get('code'))
        if not code:
            return ''

        project = self.project_for_validation
        if project:
            queryset = TaskSection.objects.filter(project=project, code=code)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Taki kod grupy już istnieje w tym projekcie.')
        return code

    def clean_priority(self):
        return self.cleaned_data.get('priority') or 'none'

    def clean_kind(self):
        return self.cleaned_data.get('kind') or 'issues'

    def clean_status(self):
        return self.cleaned_data.get('status') or 'open'

    class Meta:
        model = TaskSection
        fields = ['visibility', 'title', 'code', 'description', 'kind', 'status', 'owner', 'priority', 'due_at', 'wip_limit']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Nazwa grupy',
                'class': 'tasks-inline-input',
            }),
            'code': forms.TextInput(attrs={
                'id': 'section-create-code',
                'placeholder': 'Kod grupy',
                'class': 'tasks-inline-input',
                'maxlength': 20,
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Dodaj opis...',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
            'priority': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'kind': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'status': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'owner': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'due_at': forms.DateInput(format='%Y-%m-%d', attrs={
                'type': 'date',
                'class': 'tasks-inline-input',
            }),
            'wip_limit': forms.NumberInput(attrs={
                'class': 'tasks-inline-input',
                'min': 0,
                'placeholder': 'Limit WIP',
            }),
        }
        labels = {
            'code': 'Kod grupy',
            'kind': 'Typ grupy',
            'status': 'Status grupy',
            'owner': 'Odpowiedzialny',
            'priority': 'Priorytet',
            'due_at': 'Termin',
            'wip_limit': 'Limit WIP',
        }


class TaskSectionRenameForm(TaskSectionAccessForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        kwargs.setdefault('viewer', user)
        self.project_for_validation = kwargs.pop('project', None)
        workplace = kwargs.pop('workplace', None)
        super().__init__(*args, **kwargs)
        if self.project_for_validation is None:
            self.project_for_validation = getattr(self.instance, 'project', None)
        workplace = workplace or getattr(self.project_for_validation, 'workplace', None)
        _replace_optional_model_choice(self, 'owner', _crm_user_queryset(user, workplace), 'Brak osoby')
        self.fields['owner'].widget.attrs['data-ancore-custom-select-search'] = 'true'
        self.fields['owner'].widget.attrs['data-ancore-custom-select-search-placeholder'] = 'Szukaj osoby'
        self.fields['kind'].required = False
        self.fields['status'].required = False

    def clean_code(self):
        code = _normalize_optional_code(self.cleaned_data.get('code'))
        if not code:
            return ''

        project = self.project_for_validation
        if project:
            queryset = TaskSection.objects.filter(project=project, code=code)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Taki kod grupy już istnieje w tym projekcie.')
        return code

    def clean_priority(self):
        return self.cleaned_data.get('priority') or 'none'

    def clean_kind(self):
        return self.cleaned_data.get('kind') or 'issues'

    def clean_status(self):
        return self.cleaned_data.get('status') or 'open'

    class Meta:
        model = TaskSection
        fields = ['visibility', 'title', 'code', 'description', 'kind', 'status', 'owner', 'priority', 'due_at', 'wip_limit']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Nazwa grupy',
                'class': 'tasks-inline-input',
            }),
            'code': forms.TextInput(attrs={
                'id': 'section-rename-code-field',
                'placeholder': 'Kod grupy',
                'class': 'tasks-inline-input',
                'maxlength': 20,
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Dodaj opis...',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
            'priority': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'kind': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'status': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'owner': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'due_at': forms.DateInput(format='%Y-%m-%d', attrs={
                'type': 'date',
                'class': 'tasks-inline-input',
            }),
            'wip_limit': forms.NumberInput(attrs={
                'class': 'tasks-inline-input',
                'min': 0,
                'placeholder': 'Limit WIP',
            }),
        }
        labels = {
            'code': 'Kod grupy',
            'kind': 'Typ grupy',
            'status': 'Status grupy',
            'owner': 'Odpowiedzialny',
            'priority': 'Priorytet',
            'due_at': 'Termin',
            'wip_limit': 'Limit WIP',
        }


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


class QuickTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Dodaj zadanie...',
                'class': 'tasks-inline-input',
            }),
        }


class TaskModalForm(TaskAccessForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        viewer = kwargs.pop('viewer', None) or user
        workplace = kwargs.pop('workplace', None)
        project = kwargs.pop('project', None)
        self.project = project
        section = kwargs.pop('section', None)
        sections_queryset = kwargs.pop('sections_queryset', None)
        super().__init__(*args, viewer=viewer, **kwargs)
        if workplace is None and section is not None:
            workplace = getattr(section.project, 'workplace', None)
        if sections_queryset is not None:
            sections = editable_to(sections_queryset, viewer)
            if project:
                sections = sections.filter(project=project)
            self.fields['section'].queryset = sections
        elif user:
            sections = editable_to(TaskSection.objects.all(), viewer).filter(project__user=user)
            if workplace is not None:
                sections = sections.filter(project__workplace=workplace)
            if project:
                sections = sections.filter(project=project)
            self.fields['section'].queryset = sections
        if user:
            from .tagging import form_tags
            self.fields['tags'].queryset = form_tags(self, user, workplace, project, section)
            _replace_optional_model_choice(self, 'assignee', _crm_user_queryset(user, workplace), 'Brak osoby')
        else:
            _replace_optional_model_choice(self, 'assignee', get_user_model().objects.none(), 'Brak osoby')
        self.fields['section'].required = False
        self.fields['section'].label = 'Grupa przestrzeni'
        self.fields['tags'].required = False
        self.fields['tags'].label = 'Tagi'
        self.fields['due_at'].label = 'Termin wykonania'
        self.fields['due_at'].input_formats = DATETIME_LOCAL_INPUT_FORMATS
        self.fields['reminder_at'].label = 'Przypomnienie'
        self.fields['reminder_at'].widget.attrs['title'] = 'Powiadomienie w aplikacji dla wykonawcy, a bez wykonawcy — właściciela prywatnego zadania, projektu lub Workspace.'
        self.fields['reminder_at'].input_formats = DATETIME_LOCAL_INPUT_FORMATS
        self.fields['assignee'].label = 'Przypisane do'
        self.fields['task_type'].label = 'Typ zadania'
        self.fields['task_type'].required = False
        if section:
            self.fields['section'].initial = section

    def clean(self):
        cleaned_data = super().clean()
        if self.project and not cleaned_data.get('section') and 'section' not in self.errors:
            self.add_error('section', 'Wybierz grupę z wybranego projektu lub usuń wybór projektu.')
        return cleaned_data

    def clean_task_type(self):
        return self.cleaned_data.get('task_type') or 'general'

    class Meta:
        model = Task
        fields = [
            'title',
            'visibility',
            'section',
            'tags',
            'description',
            'task_type',
            'assignee',
            'priority',
            'status',
            'due_at',
            'reminder_at',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Tytuł zadania',
                'class': 'tasks-inline-input',
            }),
            'section': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'tasks-inline-select tasks-tag-select',
                'size': 4,
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Dodaj opis...',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
            'task_type': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'assignee': UserSelect(attrs={
                'class': 'tasks-inline-select',
            }),
            'priority': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'status': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'due_at': DateTimeLocalInput(attrs={
                'class': 'tasks-inline-input tasks-due-input',
            }),
            'reminder_at': DateTimeLocalInput(attrs={
                'class': 'tasks-inline-input',
            }),
        }


class SubTaskModalForm(TaskAccessForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_at'].label = 'Termin wykonania'
        self.fields['due_at'].input_formats = DATETIME_LOCAL_INPUT_FORMATS

    class Meta:
        model = Task
        fields = ['title', 'visibility', 'description', 'status', 'due_at']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Tytuł podzadania',
                'class': 'tasks-inline-input',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Dodaj opis...',
                'rows': 4,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
            'status': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'due_at': DateTimeLocalInput(attrs={
                'class': 'tasks-inline-input tasks-due-input',
            }),
        }
