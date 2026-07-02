from django import forms
from .models import Kanban, KanbanAttachment, KanbanBoardColumn, KanbanProject, KanbanSection, KanbanTag


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


class DynamicStatusFormMixin:
    def configure_dynamic_status_field(self, user):
        self._dynamic_status_user = user
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
        workplace = kwargs.pop('workplace', None)
        project = kwargs.pop('project', None)
        section = kwargs.pop('section', None)
        super().__init__(*args, **kwargs)
        self.configure_dynamic_status_field(user)
        if workplace is None and section is not None:
            workplace = getattr(section.project, 'workplace', None)
        if user:
            projects = _filter_workplace(KanbanProject.objects.filter(user=user), workplace).prefetch_related('sections')
            sections = KanbanSection.objects.filter(project__user=user).select_related('project')
            if workplace is not None:
                sections = sections.filter(project__workplace=workplace)
            parents = Kanban.objects.none()
            if getattr(self.instance, 'parent_id', None):
                parents = Kanban.objects.filter(user=user, parent__isnull=True).select_related('section', 'section__project').order_by('task_id')
                if workplace is not None:
                    parents = parents.filter(workplace=workplace)
                if self.instance and self.instance.pk:
                    parents = parents.exclude(pk=self.instance.pk)
            self.fields['project'].queryset = projects
            self.fields['section'].queryset = sections
            self.fields['parent'].queryset = parents
            self.fields['tags'].queryset = _filter_workplace(KanbanTag.objects.filter(user=user), workplace)
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
        fields = ['title', 'parent', 'section', 'tags', 'description', 'priority', 'status', 'time_spent_hours', 'time_spent_minutes']
        widgets = {
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


class KanbanProjectBaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        kwargs.pop('user', None)
        super().__init__(*args, **kwargs)


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
        fields = ['name', 'section_title', 'description']
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
        }


class KanbanProjectRenameForm(KanbanProjectBaseForm):
    class Meta:
        model = KanbanProject
        fields = ['name', 'description']
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
        }


class KanbanSectionForm(forms.ModelForm):
    class Meta:
        model = KanbanSection
        fields = ['title', 'description']
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


class KanbanSectionRenameForm(forms.ModelForm):
    class Meta:
        model = KanbanSection
        fields = ['title', 'description']
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
    class Meta:
        model = KanbanTag
        fields = ['name', 'description']
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
        }

    def clean_name(self):
        return (self.cleaned_data.get('name') or '').strip()


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
        workplace = kwargs.pop('workplace', None)
        project = kwargs.pop('project', None)
        section = kwargs.pop('section', None)
        super().__init__(*args, **kwargs)
        self.configure_dynamic_status_field(user)
        if workplace is None and section is not None:
            workplace = getattr(section.project, 'workplace', None)
        if user:
            sections = KanbanSection.objects.filter(project__user=user)
            if workplace is not None:
                sections = sections.filter(project__workplace=workplace)
            if project:
                sections = sections.filter(project=project)
            self.fields['section'].queryset = sections
            self.fields['tags'].queryset = _filter_workplace(KanbanTag.objects.filter(user=user), workplace)
        self.fields['section'].required = True
        self.fields['section'].label = 'Tablica przestrzeni roboczej'
        self.fields['tags'].required = False
        self.fields['tags'].label = 'Tagi'
        if section:
            self.fields['section'].initial = section

    class Meta:
        model = Kanban
        fields = ['title', 'section', 'tags', 'description', 'priority', 'status']
        widgets = {
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
