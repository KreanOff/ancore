"""Forms for snapshot data; they never save live projects, groups or tasks."""
from django import forms

from .models import Task, TaskProjectTemplate, TaskSection
from .project_templates import SECTION_FIELDS, TASK_FIELDS, template_descendants


def style_fields(form):
    for field in form.fields.values():
        field.widget.attrs['class'] = 'tasks-inline-select' if isinstance(field.widget, forms.Select) else 'tasks-inline-input'
        if isinstance(field.widget, forms.Textarea):
            field.widget.attrs.update(rows=3, **{'class': 'tasks-inline-input tasks-modal-textarea'})


class TemplateDetailsForm(forms.ModelForm):
    class Meta:
        model = TaskProjectTemplate
        fields = ('template_name', 'name', 'description')
        labels = {'name': 'Nazwa projektu', 'description': 'Opis projektu'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class TemplateSectionForm(forms.ModelForm):
    item_id = forms.IntegerField(required=False, min_value=1, widget=forms.HiddenInput)

    class Meta:
        model = TaskSection
        fields = SECTION_FIELDS
        labels = {'title': 'Nazwa grupy', 'description': 'Opis', 'priority': 'Priorytet',
                  'kind': 'Typ grupy', 'wip_limit': 'Limit WIP', 'order': 'Kolejność'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_priority(self):
        return self.cleaned_data.get('priority') or 'none'


class TemplateTaskForm(forms.ModelForm):
    item_id = forms.IntegerField(required=False, min_value=1, widget=forms.HiddenInput)
    section = forms.TypedChoiceField(label='Grupa', coerce=int)
    parent = forms.TypedChoiceField(label='Zadanie nadrzędne', coerce=int, empty_value=None, required=False)

    class Meta:
        model = Task
        fields = TASK_FIELDS
        labels = {'title': 'Tytuł', 'description': 'Opis', 'priority': 'Priorytet',
                  'task_type': 'Typ zadania'}

    def __init__(self, *args, structure, **kwargs):
        super().__init__(*args, **kwargs)
        self.structure = structure
        self.fields['section'].choices = [('', 'Wybierz grupę')] + [(s['id'], s['title']) for s in structure.get('sections', [])]
        self.fields['parent'].choices = [('', 'Brak — zadanie główne')] + [(t['id'], t['title']) for t in structure.get('tasks', [])]
        self.order_fields(['title', 'section', 'parent', 'description', 'priority', 'task_type', 'item_id'])
        style_fields(self)

    def clean(self):
        data = super().clean()
        item_id, parent_id = data.get('item_id'), data.get('parent')
        if parent_id and item_id and parent_id in template_descendants(self.structure, {item_id}):
            self.add_error('parent', 'Zadanie nie może być podzadaniem siebie ani swojego podzadania.')
        if parent_id:
            parent = next(t for t in self.structure['tasks'] if t['id'] == parent_id)
            if data.get('section') != parent['section']:
                self.add_error('section', 'Podzadanie musi należeć do tej samej grupy co zadanie nadrzędne.')
        return data
