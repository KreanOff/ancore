import re

from django import forms
from django.contrib.auth import get_user_model

from contacts.models import Company, Contact
from .models import Task, TaskAttachment, TaskProject, TaskSection, TaskTag


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


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = 'datetime-local'

    def __init__(self, attrs=None, format=None):
        super().__init__(attrs=attrs, format=format or '%Y-%m-%dT%H:%M')


def _format_estimated_duration(total_minutes):
    if total_minutes in (None, ''):
        return ''
    try:
        total_minutes = int(total_minutes)
    except (TypeError, ValueError):
        return ''
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f'{hours} godz. {minutes} min.'
    if hours:
        return f'{hours} godz.'
    return f'{minutes} min.' if minutes else ''


def _parse_estimated_duration(value):
    text = (value or '').strip().lower()
    if not text:
        return None

    clock_match = re.fullmatch(r'(\d+)\s*[:.]\s*(\d{1,2})', text)
    if clock_match:
        hours = int(clock_match.group(1))
        minutes = int(clock_match.group(2))
        if minutes > 59:
            return None
        return hours * 60 + minutes

    hours = 0
    minutes = 0
    matched = False
    for amount, unit in re.findall(r'(\d+(?:[,.]\d+)?)\s*(godz\.?|godzina|godziny|godzin|h|min\.?|minuta|minuty|minut|m)(?=\s|$)', text):
        matched = True
        number = float(amount.replace(',', '.'))
        if unit.startswith(('godz', 'h')):
            hours += int(number)
            minutes += round((number - int(number)) * 60)
        else:
            minutes += int(number)

    if matched:
        return hours * 60 + minutes
    return None


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


DATETIME_LOCAL_INPUT_FORMATS = ['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S']


def _crm_user_queryset(user):
    if not user:
        return get_user_model().objects.none()
    return (
        get_user_model().objects.filter(is_active=True)
        .distinct()
        .order_by('first_name', 'middle_name', 'last_name', 'email', 'username')
    )


def _filter_workplace(queryset, workplace):
    if workplace is None:
        return queryset
    return queryset.filter(workplace=workplace)


def _company_queryset(user, workplace=None):
    if not user:
        return Company.objects.none()
    return _filter_workplace(Company.objects.filter(owner=user), workplace).order_by('name')


def _contact_queryset(user, workplace=None):
    if not user:
        return Contact.objects.none()
    return _filter_workplace(Contact.objects.filter(user=user), workplace).order_by('first_name', 'middle_name', 'last_name', 'company', 'id')


def _replace_optional_model_choice(form, field_name, queryset, empty_label):
    if field_name not in form.fields:
        return
    current = form.fields[field_name]
    form.fields[field_name] = LenientModelChoiceField(
        queryset=queryset,
        required=False,
        label=current.label,
        widget=current.widget,
        help_text=current.help_text,
        empty_label=empty_label,
    )


class TaskForm(forms.ModelForm):
    project = forms.ModelChoiceField(
        queryset=TaskProject.objects.none(),
        required=False,
        label='Projekt',
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
        workplace = kwargs.pop('workplace', None)
        project = kwargs.pop('project', None)
        section = kwargs.pop('section', None)
        super().__init__(*args, **kwargs)
        if workplace is None and section is not None:
            workplace = getattr(section.project, 'workplace', None)
        if user:
            projects = _filter_workplace(TaskProject.objects.filter(user=user), workplace).prefetch_related('sections')
            sections = TaskSection.objects.filter(project__user=user).select_related('project')
            if workplace is not None:
                sections = sections.filter(project__workplace=workplace)
            parents = Task.objects.none()
            if getattr(self.instance, 'parent_id', None):
                parents = Task.objects.filter(user=user, parent__isnull=True).select_related('section', 'section__project').order_by('task_id')
                if workplace is not None:
                    parents = parents.filter(workplace=workplace)
                if self.instance and self.instance.pk:
                    parents = parents.exclude(pk=self.instance.pk)
            self.fields['project'].queryset = projects
            self.fields['section'].queryset = sections
            self.fields['parent'].queryset = parents
            self.fields['tags'].queryset = _filter_workplace(TaskTag.objects.filter(user=user), workplace)
            _replace_optional_model_choice(self, 'assignee', _crm_user_queryset(user), 'Brak osoby')
            _replace_optional_model_choice(self, 'company', _company_queryset(user, workplace), 'Brak firmy')
            _replace_optional_model_choice(self, 'contact', _contact_queryset(user, workplace), 'Brak kontaktu')
        else:
            _replace_optional_model_choice(self, 'assignee', get_user_model().objects.none(), 'Brak osoby')
            _replace_optional_model_choice(self, 'company', Company.objects.none(), 'Brak firmy')
            _replace_optional_model_choice(self, 'contact', Contact.objects.none(), 'Brak kontaktu')
        current_section = section or getattr(self.instance, 'section', None)
        if current_section:
            self.fields['project'].initial = current_section.project
            self.fields['section'].initial = current_section
        elif project:
            self.fields['project'].initial = project
        self.fields['section'].required = True
        self.fields['section'].label = 'Grupa projektu'
        self.fields['parent'].required = bool(getattr(self.instance, 'parent_id', None))
        self.fields['title'].label = 'Tytuł'
        self.fields['description'].label = 'Opis'
        self.fields['tags'].required = False
        self.fields['tags'].label = 'Tagi'
        self.fields['due_at'].label = 'Termin wykonania'
        self.fields['due_at'].input_formats = DATETIME_LOCAL_INPUT_FORMATS
        self.fields['reminder_at'].label = 'Przypomnienie'
        self.fields['reminder_at'].input_formats = DATETIME_LOCAL_INPUT_FORMATS
        self.fields['estimated_minutes'].label = 'Szacowany czas'
        self.fields['is_billable'].label = 'Fakturowalne'
        self.fields['blocked_reason'].label = 'Powód blokady'
        self.fields['assignee'].label = 'Przypisane do'
        self.fields['company'].label = 'Firma'
        self.fields['contact'].label = 'Kontakt'
        self.fields['task_type'].label = 'Typ zadania'
        self.fields['contact_channel'].label = 'Kanał kontaktu'
        self.fields['task_type'].required = False
        self.fields['contact_channel'].required = False

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
            self.add_error('section', 'Wybierz grupę z wybranego projektu.')
        return cleaned_data

    def clean_task_type(self):
        return self.cleaned_data.get('task_type') or 'general'

    def clean_contact_channel(self):
        return self.cleaned_data.get('contact_channel') or 'none'

    class Meta:
        model = Task
        fields = [
            'title',
            'parent',
            'section',
            'tags',
            'description',
            'task_type',
            'contact_channel',
            'company',
            'contact',
            'assignee',
            'priority',
            'status',
            'due_at',
            'reminder_at',
            'estimated_minutes',
            'is_billable',
            'blocked_reason',
            'time_spent_hours',
            'time_spent_minutes',
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
            'contact_channel': forms.Select(attrs={
                'class': 'form-input'
            }),
            'company': forms.Select(attrs={
                'class': 'form-input'
            }),
            'contact': forms.Select(attrs={
                'class': 'form-input'
            }),
            'assignee': forms.Select(attrs={
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
            'estimated_minutes': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 0,
                'placeholder': 'np. 60',
            }),
            'is_billable': forms.CheckboxInput(attrs={
                'class': 'tasks-inline-checkbox',
            }),
            'blocked_reason': forms.Textarea(attrs={
                'placeholder': 'Dlaczego zadanie jest zablokowane?',
                'rows': 3,
                'class': 'form-input tasks-modal-textarea',
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


class TaskProjectBaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        workplace = kwargs.pop('workplace', None)
        super().__init__(*args, **kwargs)
        if 'company' in self.fields:
            _replace_optional_model_choice(self, 'company', _company_queryset(user, workplace), 'Brak firmy')
        if 'responsible_user' in self.fields:
            _replace_optional_model_choice(self, 'responsible_user', _crm_user_queryset(user), 'Brak osoby')
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


class TaskProjectForm(TaskProjectBaseForm):
    section_title = forms.CharField(
        required=False,
        label='Nazwa grupy',
        widget=forms.TextInput(attrs={
            'placeholder': 'Nowa Grupa',
            'class': 'tasks-inline-input',
        }),
    )

    def clean_section_title(self):
        return (self.cleaned_data.get('section_title') or '').strip()

    class Meta:
        model = TaskProject
        fields = [
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
                'placeholder': 'Nowy projekt',
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
                'placeholder': 'Źródło projektu',
            }),
        }
        labels = {
            'company': 'Firma',
            'responsible_user': 'Odpowiedzialny',
            'status': 'Status projektu',
            'stage': 'Etap',
            'health': 'Kondycja',
            'priority': 'Priorytet',
            'start_at': 'Start',
            'due_at': 'Termin',
            'budget_amount': 'Budżet',
            'currency': 'Waluta',
            'source': 'Źródło',
        }


class TaskProjectRenameForm(TaskProjectBaseForm):
    class Meta:
        model = TaskProject
        fields = [
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
                'placeholder': 'Nazwa projektu',
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
                'placeholder': 'Źródło projektu',
            }),
        }
        labels = {
            'company': 'Firma',
            'responsible_user': 'Odpowiedzialny',
            'status': 'Status projektu',
            'stage': 'Etap',
            'health': 'Kondycja',
            'priority': 'Priorytet',
            'start_at': 'Start',
            'due_at': 'Termin',
            'budget_amount': 'Budżet',
            'currency': 'Waluta',
            'source': 'Źródło',
        }


class TaskSectionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        _replace_optional_model_choice(self, 'owner', _crm_user_queryset(user), 'Brak osoby')
        self.fields['kind'].required = False
        self.fields['status'].required = False

    def clean_priority(self):
        return self.cleaned_data.get('priority') or 'none'

    def clean_kind(self):
        return self.cleaned_data.get('kind') or 'issues'

    def clean_status(self):
        return self.cleaned_data.get('status') or 'open'

    class Meta:
        model = TaskSection
        fields = ['title', 'description', 'kind', 'status', 'owner', 'priority', 'due_at', 'wip_limit']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Nazwa grupy',
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
            'kind': 'Typ grupy',
            'status': 'Status grupy',
            'owner': 'Odpowiedzialny',
            'priority': 'Priorytet',
            'due_at': 'Termin',
            'wip_limit': 'Limit WIP',
        }


class TaskSectionRenameForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        _replace_optional_model_choice(self, 'owner', _crm_user_queryset(user), 'Brak osoby')
        self.fields['kind'].required = False
        self.fields['status'].required = False

    def clean_priority(self):
        return self.cleaned_data.get('priority') or 'none'

    def clean_kind(self):
        return self.cleaned_data.get('kind') or 'issues'

    def clean_status(self):
        return self.cleaned_data.get('status') or 'open'

    class Meta:
        model = TaskSection
        fields = ['title', 'description', 'kind', 'status', 'owner', 'priority', 'due_at', 'wip_limit']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Nazwa grupy',
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


class TaskModalForm(forms.ModelForm):
    estimated_duration = forms.CharField(
        required=False,
        label='Szacowany czas',
        widget=forms.TextInput(attrs={
            'class': 'tasks-inline-input tasks-estimate-duration-input',
            'placeholder': '0 godz. 0 min.',
            'autocomplete': 'off',
            'inputmode': 'text',
        }),
    )
    estimated_hours = forms.IntegerField(
        required=False,
        min_value=0,
        label='Godziny',
        widget=forms.NumberInput(attrs={
            'class': 'tasks-inline-input',
            'min': 0,
            'placeholder': '0',
            'inputmode': 'numeric',
        }),
    )
    estimated_minutes_part = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=59,
        label='Minuty',
        widget=forms.NumberInput(attrs={
            'class': 'tasks-inline-input',
            'min': 0,
            'max': 59,
            'placeholder': '0',
            'inputmode': 'numeric',
        }),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        workplace = kwargs.pop('workplace', None)
        project = kwargs.pop('project', None)
        section = kwargs.pop('section', None)
        sections_queryset = kwargs.pop('sections_queryset', None)
        super().__init__(*args, **kwargs)
        if workplace is None and section is not None:
            workplace = getattr(section.project, 'workplace', None)
        if sections_queryset is not None:
            sections = sections_queryset
            if project:
                sections = sections.filter(project=project)
            self.fields['section'].queryset = sections
        elif user:
            sections = TaskSection.objects.filter(project__user=user)
            if workplace is not None:
                sections = sections.filter(project__workplace=workplace)
            if project:
                sections = sections.filter(project=project)
            self.fields['section'].queryset = sections
        if user:
            self.fields['tags'].queryset = _filter_workplace(TaskTag.objects.filter(user=user), workplace)
            _replace_optional_model_choice(self, 'assignee', _crm_user_queryset(user), 'Brak osoby')
            _replace_optional_model_choice(self, 'company', _company_queryset(user, workplace), 'Brak firmy')
            _replace_optional_model_choice(self, 'contact', _contact_queryset(user, workplace), 'Brak kontaktu')
        else:
            _replace_optional_model_choice(self, 'assignee', get_user_model().objects.none(), 'Brak osoby')
            _replace_optional_model_choice(self, 'company', Company.objects.none(), 'Brak firmy')
            _replace_optional_model_choice(self, 'contact', Contact.objects.none(), 'Brak kontaktu')
        self.fields['section'].required = True
        self.fields['section'].label = 'Grupa projektu'
        self.fields['tags'].required = False
        self.fields['tags'].label = 'Tagi'
        self.fields['due_at'].label = 'Termin wykonania'
        self.fields['due_at'].input_formats = DATETIME_LOCAL_INPUT_FORMATS
        self.fields['reminder_at'].label = 'Przypomnienie'
        self.fields['reminder_at'].input_formats = DATETIME_LOCAL_INPUT_FORMATS
        self.fields['estimated_minutes'].label = 'Szacowany czas'
        self.fields['is_billable'].label = 'Fakturowalne'
        self.fields['blocked_reason'].label = 'Powód blokady'
        self.fields['assignee'].label = 'Przypisane do'
        self.fields['company'].label = 'Firma'
        self.fields['contact'].label = 'Kontakt'
        self.fields['task_type'].label = 'Typ zadania'
        self.fields['contact_channel'].label = 'Kanał kontaktu'
        self.fields['task_type'].required = False
        self.fields['contact_channel'].required = False
        if section:
            self.fields['section'].initial = section
        if not self.is_bound and not getattr(self.instance, 'pk', None) and 'is_billable' not in self.initial:
            self.fields['is_billable'].initial = True
        estimated_minutes = self.initial.get('estimated_minutes', getattr(self.instance, 'estimated_minutes', None))
        if not self.is_bound and estimated_minutes:
            self.fields['estimated_duration'].initial = _format_estimated_duration(estimated_minutes)
            self.fields['estimated_hours'].initial = estimated_minutes // 60
            self.fields['estimated_minutes_part'].initial = estimated_minutes % 60

    def clean_task_type(self):
        return self.cleaned_data.get('task_type') or 'general'

    def clean_contact_channel(self):
        return self.cleaned_data.get('contact_channel') or 'none'

    def clean(self):
        cleaned_data = super().clean()
        duration = cleaned_data.get('estimated_duration')
        hours = cleaned_data.get('estimated_hours')
        minutes = cleaned_data.get('estimated_minutes_part')
        has_split_estimate = hours is not None or minutes is not None
        if duration:
            parsed_duration = _parse_estimated_duration(duration)
            if parsed_duration is None:
                self.add_error('estimated_duration', 'Wpisz czas w formacie 2 godz. 15 min. albo 2:15.')
            else:
                cleaned_data['estimated_minutes'] = parsed_duration
        elif has_split_estimate:
            cleaned_data['estimated_minutes'] = (hours or 0) * 60 + (minutes or 0)
        return cleaned_data

    class Meta:
        model = Task
        fields = [
            'title',
            'section',
            'tags',
            'description',
            'task_type',
            'contact_channel',
            'company',
            'contact',
            'assignee',
            'priority',
            'status',
            'due_at',
            'reminder_at',
            'estimated_minutes',
            'is_billable',
            'blocked_reason',
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
                'rows': 4,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
            'task_type': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'contact_channel': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'company': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'contact': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'assignee': forms.Select(attrs={
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
            'estimated_minutes': forms.HiddenInput(),
            'is_billable': forms.CheckboxInput(attrs={
                'class': 'tasks-inline-checkbox',
            }),
            'blocked_reason': forms.Textarea(attrs={
                'placeholder': 'Dlaczego zadanie jest zablokowane?',
                'rows': 3,
                'class': 'tasks-inline-input tasks-modal-textarea',
            }),
        }


class SubTaskModalForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_at'].label = 'Termin wykonania'
        self.fields['due_at'].input_formats = DATETIME_LOCAL_INPUT_FORMATS

    class Meta:
        model = Task
        fields = ['title', 'description', 'status', 'due_at']
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
