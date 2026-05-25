from django import forms
from .models import Task, TaskAttachment, TaskProject, TaskSection


def clean_optional_icon(value):
    icon = (value or '').strip()[:8]
    return '' if icon == 'check' else icon


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class TaskForm(forms.ModelForm):
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
        self.fields['section'].required = True
        self.fields['section'].label = 'Grupa projektu'
        if section:
            self.fields['section'].initial = section

    class Meta:
        model = Task
        fields = ['title', 'section', 'description', 'priority', 'status']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Wprowadź tytuł zadania...',
                'class': 'form-input'
            }),
            'section': forms.Select(attrs={
                'class': 'form-input'
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
        }


class TaskProjectForm(forms.ModelForm):
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

    def clean_icon(self):
        return clean_optional_icon(self.cleaned_data.get('icon'))


class TaskProjectRenameForm(forms.ModelForm):
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

    def clean_code(self):
        return (self.cleaned_data.get('code') or '').strip().upper()[:8]

    def clean_icon(self):
        return clean_optional_icon(self.cleaned_data.get('icon'))


class TaskSectionForm(forms.ModelForm):
    class Meta:
        model = TaskSection
        fields = ['title', 'kind', 'icon']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Nazwa grupy',
                'class': 'tasks-inline-input',
            }),
            'kind': forms.Select(attrs={
                'class': 'tasks-inline-select',
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
        fields = ['title', 'kind', 'icon']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Nazwa grupy',
                'class': 'tasks-inline-input',
            }),
            'kind': forms.Select(attrs={
                'class': 'tasks-inline-select',
            }),
            'icon': forms.HiddenInput(attrs={
                'maxlength': 8,
            }),
        }

    def clean_icon(self):
        return clean_optional_icon(self.cleaned_data.get('icon'))


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
        self.fields['section'].required = True
        self.fields['section'].label = 'Grupa projektu'
        if section:
            self.fields['section'].initial = section

    class Meta:
        model = Task
        fields = ['title', 'section', 'description', 'priority', 'status']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Tytuł zadania',
                'class': 'tasks-inline-input',
            }),
            'section': forms.Select(attrs={
                'class': 'tasks-inline-select',
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
