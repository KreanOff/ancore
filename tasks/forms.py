from django import forms
from .models import Task, TaskAttachment, TaskProject, TaskSection, TaskTag


class TwoDigitNumberInput(forms.NumberInput):
    def format_value(self, value):
        if value in (None, ''):
            return None
        try:
            return f'{int(value):02d}'
        except (TypeError, ValueError):
            return super().format_value(value)


def clean_optional_icon(value):
    icon = (value or '').strip()[:8]
    return '' if icon == 'check' else icon


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


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
        project = kwargs.pop('project', None)
        section = kwargs.pop('section', None)
        super().__init__(*args, **kwargs)
        if user:
            projects = TaskProject.objects.filter(user=user).prefetch_related('sections')
            sections = TaskSection.objects.filter(project__user=user).select_related('project')
            parents = Task.objects.none()
            if getattr(self.instance, 'parent_id', None):
                parents = Task.objects.filter(user=user, parent__isnull=True).select_related('section', 'section__project').order_by('task_id')
                if self.instance and self.instance.pk:
                    parents = parents.exclude(pk=self.instance.pk)
            self.fields['project'].queryset = projects
            self.fields['section'].queryset = sections
            self.fields['parent'].queryset = parents
            self.fields['tags'].queryset = TaskTag.objects.filter(user=user)
        current_section = section or getattr(self.instance, 'section', None)
        if current_section:
            self.fields['project'].initial = current_section.project
            self.fields['section'].initial = current_section
        elif project:
            self.fields['project'].initial = project
        self.fields['section'].required = True
        self.fields['section'].label = 'Grupa projektu'
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
            self.add_error('section', 'Wybierz grupę z wybranego projektu.')
        return cleaned_data

    class Meta:
        model = Task
        fields = ['title', 'parent', 'section', 'tags', 'description', 'priority', 'status', 'time_spent_hours', 'time_spent_minutes']
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


class TaskProjectBaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip().upper()[:8]
        if not code or not self.user:
            return code

        duplicate_codes = TaskProject.objects.filter(user=self.user, code=code)
        if self.instance and self.instance.pk:
            duplicate_codes = duplicate_codes.exclude(pk=self.instance.pk)
        if duplicate_codes.exists():
            raise forms.ValidationError('Taki kod projektu już istnieje.')
        return code

    def clean_icon(self):
        return clean_optional_icon(self.cleaned_data.get('icon'))


class TaskProjectForm(TaskProjectBaseForm):
    class Meta:
        model = TaskProject
        fields = ['name', 'description', 'code', 'icon']
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
                'placeholder': 'TSK',
                'class': 'tasks-inline-input tasks-inline-code',
                'maxlength': 8,
            }),
            'icon': forms.HiddenInput(attrs={
                'maxlength': 8,
            }),
        }


class TaskProjectRenameForm(TaskProjectBaseForm):
    class Meta:
        model = TaskProject
        fields = ['name', 'description', 'code', 'icon']
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
                'placeholder': 'TSK',
                'class': 'tasks-inline-input tasks-inline-code',
                'maxlength': 8,
            }),
            'icon': forms.HiddenInput(attrs={
                'maxlength': 8,
            }),
        }


class TaskSectionForm(forms.ModelForm):
    class Meta:
        model = TaskSection
        fields = ['title', 'description', 'icon']
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
            'icon': forms.HiddenInput(attrs={
                'maxlength': 8,
            }),
        }

    def clean_icon(self):
        return clean_optional_icon(self.cleaned_data.get('icon'))


class TaskSectionRenameForm(forms.ModelForm):
    class Meta:
        model = TaskSection
        fields = ['title', 'description', 'icon']
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
            'icon': forms.HiddenInput(attrs={
                'maxlength': 8,
            }),
        }

    def clean_icon(self):
        return clean_optional_icon(self.cleaned_data.get('icon'))


class TaskTagForm(forms.ModelForm):
    class Meta:
        model = TaskTag
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
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        project = kwargs.pop('project', None)
        section = kwargs.pop('section', None)
        super().__init__(*args, **kwargs)
        if user:
            sections = TaskSection.objects.filter(project__user=user)
            if project:
                sections = sections.filter(project=project)
            self.fields['section'].queryset = sections
            self.fields['tags'].queryset = TaskTag.objects.filter(user=user)
        self.fields['section'].required = True
        self.fields['section'].label = 'Grupa projektu'
        self.fields['tags'].required = False
        self.fields['tags'].label = 'Tagi'
        if section:
            self.fields['section'].initial = section

    class Meta:
        model = Task
        fields = ['title', 'section', 'tags', 'description', 'priority', 'status']
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
            'priority': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'status': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
        }


class SubTaskModalForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'status']
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
        }
