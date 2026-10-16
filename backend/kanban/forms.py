from django import forms
from django.contrib.auth import get_user_model

from workplaces.services import workplace_people

from contacts.models import Company
from tasks.models import TaskTag
from tasks.forms import DateTimeLocalInput, DATETIME_LOCAL_INPUT_FORMATS, ProjectVisibilitySelect
from .access import editable_to, visible_to
from .models import Kanban, KanbanAttachment, KanbanBoardColumn, KanbanProject, KanbanSection


class LenientModelChoiceField(forms.ModelChoiceField):
    def clean(self, value):
        if value in self.empty_values:
            return None
        try:
            return super().clean(value)
        except forms.ValidationError:
            return None


class TwoDigitNumberInput(forms.NumberInput):
    def format_value(self, value):
        if value in (None, ''):
            return None
        try:
            return f'{int(value):02d}'
        except (TypeError, ValueError):
            return super().format_value(value)


def board_column_status_choices(user=None):
    return list(Kanban.STATUS_CHOICES)


def _filter_workplace(queryset, workplace):
    if workplace is None:
        return queryset
    return queryset.filter(workplace=workplace)


def _crm_user_queryset(user, workplace=None):
    return workplace_people(workplace, user)


def _company_queryset(user, workplace=None):
    if not user:
        return Company.objects.none()
    return _filter_workplace(Company.objects.filter(owner=user), workplace).order_by('name')


def _replace_optional_model_choice(form, field_name, queryset, empty_label):
    if field_name not in form.fields:
        return
    current = form.fields[field_name]
    field_class = forms.ModelChoiceField if field_name in {'assignee', 'responsible_user', 'owner'} else LenientModelChoiceField
    form.fields[field_name] = field_class(
        queryset=queryset,
        required=False,
        label=current.label,
        widget=current.widget,
        empty_label=empty_label,
    )


class DynamicStatusFormMixin:
    def configure_dynamic_status_field(self, user):
        self._dynamic_status_user = user
        if 'due_at' in self.fields:
            self.fields['due_at'].label = 'Termin wykonania'
            self.fields['due_at'].input_formats = DATETIME_LOCAL_INPUT_FORMATS
        if user and 'status' in self.fields:
            self.fields['status'].choices = board_column_status_choices(user)

    def clean_status(self):
        status = self.cleaned_data.get('status')
        if not status:
            return status

        valid_statuses = {value for value, _label in board_column_status_choices(getattr(self, '_dynamic_status_user', None))}
        if status not in valid_statuses:
            raise forms.ValidationError('Nieprawidłowy status.')
        return status


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class KanbanForm(DynamicStatusFormMixin, forms.ModelForm):
    project = forms.ModelChoiceField(
        queryset=KanbanProject.objects.none(),
        required=False,
        label='Przestrzeń robocza',
        widget=forms.Select(attrs={
            'class': 'form-input'
        }),
    )
    parent = forms.ModelChoiceField(
        queryset=Kanban.objects.none(),
        required=False,
        label='Karta',
        widget=forms.Select(attrs={
            'class': 'form-input'
        }),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        viewer = kwargs.pop('viewer', None) or user
        allowed = visible_to if kwargs.pop('read_only', False) else editable_to
        workplace = kwargs.pop('workplace', None)
        project = kwargs.pop('project', None)
        section = kwargs.pop('section', None)
        super().__init__(*args, **kwargs)
        self.configure_dynamic_status_field(user)
        if workplace is None and section is not None:
            workplace = getattr(section.project, 'workplace', None)
        if user:
            projects = _filter_workplace(allowed(KanbanProject.objects.all(), viewer).filter(user=user), workplace)
            sections = allowed(KanbanSection.objects.all(), viewer).filter(project__user=user).select_related('project')
            if workplace is not None:
                sections = sections.filter(project__workplace=workplace)
            parents = Kanban.objects.none()
            if getattr(self.instance, 'parent_id', None):
                parents = allowed(Kanban.objects.all(), viewer).filter(user=user, parent__isnull=True).select_related('section', 'section__project').order_by('task_id')
                if workplace is not None:
                    parents = parents.filter(workplace=workplace)
                if self.instance and self.instance.pk:
                    parents = parents.exclude(pk=self.instance.pk)
            self.fields['project'].queryset = projects
            self.fields['section'].queryset = sections
            self.fields['parent'].queryset = parents
            self.fields['tags'].queryset = _filter_workplace(TaskTag.objects.filter(user=user), workplace)
        current_section = section or getattr(self.instance, 'section', None)
        if current_section:
            self.fields['project'].initial = current_section.project
            self.fields['section'].initial = current_section
        elif project:
            self.fields['project'].initial = project
        self.fields['section'].required = True
        self.fields['section'].label = 'Tablica przestrzeni roboczej'
        self.fields['parent'].required = bool(getattr(self.instance, 'parent_id', None))
        self.fields['tags'].required = False
        self.fields['tags'].label = 'Tagi'
    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')
        project = cleaned_data.get('project')
        section = cleaned_data.get('section')
        if parent:
            cleaned_data['section'] = parent.section
            section = parent.section
            if section:
                cleaned_data['project'] = section.project
                project = section.project
        if section and not project:
            cleaned_data['project'] = section.project
            project = section.project
        if project and section and section.project_id != project.id:
            self.add_error('section', 'Wybierz tablicę z wybranej przestrzeni roboczej.')
        return cleaned_data

    class Meta:
        model = Kanban
        fields = ['title', 'parent', 'section', 'tags', 'description', 'priority', 'status', 'due_at', 'time_spent_hours', 'time_spent_minutes']
        widgets = {
            'due_at': DateTimeLocalInput(attrs={'class': 'form-input tasks-due-input'}),
            'title': forms.TextInput(attrs={
                'placeholder': 'Wprowadź tytuł karty...',
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
                'placeholder': 'Wprowadź opis karty...',
                'rows': 4,
                'class': 'form-input'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-input'
            }),
            'status': forms.Select(attrs={
                'class': 'form-input'
            }),
            'time_spent_hours': TwoDigitNumberInput(attrs={
                'placeholder': '00',
                'class': 'form-input',
                'min': 0,
            }),
            'time_spent_minutes': TwoDigitNumberInput(attrs={
                'placeholder': '00',
                'class': 'form-input',
                'min': 0,
                'max': 59,
            }),
        }


class KanbanAccessForm(forms.ModelForm):
    visibility = forms.ChoiceField(
        choices=[('private', 'Prywatna — wybrane osoby'), ('public', 'Publiczna — cały Workspace')],
        required=False, label='Widoczność',
        widget=ProjectVisibilitySelect(attrs={'class': 'tasks-inline-select'}),
    )

    def __init__(self, *args, **kwargs):
        self.viewer = kwargs.pop('viewer', None)
        super().__init__(*args, **kwargs)
        self.original_visibility = self.instance.visibility
        self.can_manage_access = (not self.instance.pk or self.original_visibility == 'public'
                                  or self.instance.private_owner_id == getattr(self.viewer, 'pk', None))
        kind = 'section' if isinstance(self.instance, KanbanSection) else 'project'
        mode = 'rename' if self.instance.pk or 'Rename' in type(self).__name__ else 'create'
        self.fields['visibility'].widget.attrs['id'] = f'{kind}-{mode}-visibility'
        if kind == 'section' and mode == 'rename':
            for name in ['title', 'description']:
                self.fields[name].widget.attrs['id'] = f'section-rename-{name}'
        if kind == 'section':
            self.fields['visibility'].choices = [('private', 'Prywatna — wybrane osoby'), ('public', 'Publiczna — uczestnicy przestrzeni')]
        if not self.instance.pk:
            self.initial['visibility'] = 'private'

    def clean_visibility(self):
        value = self.cleaned_data.get('visibility') or (self.original_visibility if self.instance.pk else 'private')
        if not self.can_manage_access and value != self.original_visibility:
            raise forms.ValidationError('Tylko właściciel może zmienić widoczność prywatnego elementu.')
        return value

    def clean(self):
        cleaned = super().clean()
        if self.data.get('sharing_present') or self.data.get('shared_with'):
            raise forms.ValidationError('Udostępniaj w zakładce „Członkowie”. Odśwież formularz.')
        return cleaned

    def _save_m2m(self):
        if self.can_manage_access and self.instance.visibility == 'public':
            self.instance.shared_with.clear()

    def save(self, commit=True):
        item = super().save(commit=False)
        if item.visibility == 'private':
            if not item.private_owner_id:
                item.private_owner = self.viewer
        else:
            item.private_owner = None
        if commit:
            item.save()
            self.save_m2m()
        return item


class KanbanProjectBaseForm(KanbanAccessForm):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('viewer', kwargs.get('user'))
        user = kwargs.pop('user', None)
        workplace = kwargs.pop('workplace', None)
        super().__init__(*args, **kwargs)
        if 'company' in self.fields:
            _replace_optional_model_choice(self, 'company', _company_queryset(user, workplace), 'Brak firmy')
            self.fields['company'].widget.attrs['data-ancore-custom-select-search'] = 'true'
            self.fields['company'].widget.attrs['data-ancore-custom-select-search-placeholder'] = 'Szukaj firmy'
        if 'responsible_user' in self.fields:
            _replace_optional_model_choice(self, 'responsible_user', _crm_user_queryset(user, workplace), 'Brak osoby')
            self.fields['responsible_user'].widget.attrs['data-ancore-custom-select-search'] = 'true'
            self.fields['responsible_user'].widget.attrs['data-ancore-custom-select-search-placeholder'] = 'Szukaj osoby'
        for field_name in ('status', 'stage', 'health', 'currency'):
            if field_name in self.fields:
                self.fields[field_name].required = False

    def clean_priority(self):
        return self.cleaned_data.get('priority') or 'none'

    def clean_status(self):
        return self.cleaned_data.get('status') or 'active'

    def clean_stage(self):
        return self.cleaned_data.get('stage') or 'implementation'

    def clean_health(self):
        return self.cleaned_data.get('health') or 'ok'

    def clean_currency(self):
        currency = (self.cleaned_data.get('currency') or '').strip().upper()[:3]
        return currency or 'PLN'


class KanbanProjectForm(KanbanProjectBaseForm):
    section_title = forms.CharField(
        required=False,
        label='Nazwa pierwszej tablicy',
        widget=forms.TextInput(attrs={
            'placeholder': 'Nowa Tablica',
            'class': 'tasks-inline-input',
        }),
    )

    def clean_section_title(self):
        return (self.cleaned_data.get('section_title') or '').strip()

    class Meta:
        model = KanbanProject
        fields = [
            'visibility',
            'name',
            'section_title',
            'description',
            'company',
            'responsible_user',
            'status',
            'stage',
            'health',
            'priority',
            'start_at',
            'due_at',
            'budget_amount',
            'currency',
            'source',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nowa przestrzeń robocza',
                'class': 'tasks-inline-input',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Dodaj opis...',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
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
            'budget_amount': forms.NumberInput(attrs={
                'class': 'tasks-inline-input',
                'min': 0,
                'step': '0.01',
                'placeholder': 'Budżet',
            }),
            'currency': forms.TextInput(attrs={
                'class': 'tasks-inline-input',
                'maxlength': 3,
                'placeholder': 'PLN',
            }),
            'source': forms.TextInput(attrs={
                'class': 'tasks-inline-input',
                'placeholder': 'Źródło przestrzeni',
            }),
        }
        labels = {
            'company': 'Firma',
            'responsible_user': 'Odpowiedzialny',
            'status': 'Status przestrzeni',
            'stage': 'Etap',
            'health': 'Kondycja',
            'priority': 'Priorytet',
            'start_at': 'Start',
            'due_at': 'Termin',
            'budget_amount': 'Budżet',
            'currency': 'Waluta',
            'source': 'Źródło',
        }


class KanbanProjectRenameForm(KanbanProjectBaseForm):
    class Meta:
        model = KanbanProject
        fields = [
            'visibility',
            'name',
            'description',
            'company',
            'responsible_user',
            'status',
            'stage',
            'health',
            'priority',
            'start_at',
            'due_at',
            'budget_amount',
            'currency',
            'source',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nazwa przestrzeni roboczej',
                'class': 'tasks-inline-input',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Dodaj opis...',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
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
            'budget_amount': forms.NumberInput(attrs={
                'class': 'tasks-inline-input',
                'min': 0,
                'step': '0.01',
                'placeholder': 'Budżet',
            }),
            'currency': forms.TextInput(attrs={
                'class': 'tasks-inline-input',
                'maxlength': 3,
                'placeholder': 'PLN',
            }),
            'source': forms.TextInput(attrs={
                'class': 'tasks-inline-input',
                'placeholder': 'Źródło przestrzeni',
            }),
        }
        labels = {
            'company': 'Firma',
            'responsible_user': 'Odpowiedzialny',
            'status': 'Status przestrzeni',
            'stage': 'Etap',
            'health': 'Kondycja',
            'priority': 'Priorytet',
            'start_at': 'Start',
            'due_at': 'Termin',
            'budget_amount': 'Budżet',
            'currency': 'Waluta',
            'source': 'Źródło',
        }


class KanbanSectionForm(KanbanAccessForm):
    class Meta:
        model = KanbanSection
        fields = ['visibility', 'title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Nazwa tablicy',
                'class': 'tasks-inline-input',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Dodaj opis...',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
        }


class KanbanSectionRenameForm(KanbanAccessForm):
    class Meta:
        model = KanbanSection
        fields = ['visibility', 'title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Nazwa tablicy',
                'class': 'tasks-inline-input',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Dodaj opis...',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
        }


class KanbanTagForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        workplace = kwargs.pop('workplace', None)
        super().__init__(*args, **kwargs)
        if user is None:
            user = getattr(self.instance, 'user', None)
        if workplace is None:
            workplace = getattr(self.instance, 'workplace', None)
        related_queryset = TaskTag.objects.none()
        if user:
            related_queryset = _filter_workplace(TaskTag.objects.filter(user=user), workplace)
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
        return (self.cleaned_data.get('name') or '').strip()

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


class KanbanBoardColumnForm(forms.ModelForm):
    class Meta:
        model = KanbanBoardColumn
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Nazwa kolumny',
                'class': 'tasks-inline-input',
            }),
        }

    def clean_title(self):
        return (self.cleaned_data.get('title') or '').strip()


class QuickKanbanForm(forms.ModelForm):
    class Meta:
        model = Kanban
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Dodaj kartę...',
                'class': 'tasks-inline-input',
            }),
        }


class KanbanModalForm(DynamicStatusFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        viewer = kwargs.pop('viewer', None) or user
        workplace = kwargs.pop('workplace', None)
        project = kwargs.pop('project', None)
        section = kwargs.pop('section', None)
        super().__init__(*args, **kwargs)
        self.configure_dynamic_status_field(user)
        if workplace is None and section is not None:
            workplace = getattr(section.project, 'workplace', None)
        if user:
            sections = editable_to(KanbanSection.objects.all(), viewer).filter(project__user=user)
            if workplace is not None:
                sections = sections.filter(project__workplace=workplace)
            if project:
                sections = sections.filter(project=project)
            self.fields['section'].queryset = sections
            self.fields['tags'].queryset = _filter_workplace(TaskTag.objects.filter(user=user), workplace)
        self.fields['section'].required = True
        self.fields['section'].label = 'Tablica przestrzeni roboczej'
        self.fields['tags'].required = False
        self.fields['tags'].label = 'Tagi'
        if section:
            self.fields['section'].initial = section

    class Meta:
        model = Kanban
        fields = ['title', 'section', 'tags', 'description', 'priority', 'status', 'due_at']
        widgets = {
            'due_at': DateTimeLocalInput(attrs={'class': 'tasks-inline-input tasks-due-input'}),
            'title': forms.TextInput(attrs={
                'placeholder': 'Tytuł karty',
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
                'rows': 4,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
            'priority': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'status': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
        }


class SubKanbanModalForm(DynamicStatusFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.configure_dynamic_status_field(user)

    class Meta:
        model = Kanban
        fields = ['title', 'description', 'status']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Tytuł podkarty',
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
        }
