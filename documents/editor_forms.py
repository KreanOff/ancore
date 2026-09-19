from pathlib import Path

from django import forms

from core.upload_validation import validate_attachment_upload
from tasks.models import TaskTag
from .forms import MultipleFileField, MultipleFileInput
from .models import WorkspaceDocument, WorkspaceDocumentFolder
from .rich_text import clean_content

DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.rtf', '.txt', '.xls', '.xlsx', '.csv', '.ppt', '.pptx'}


def validate_document(file):
    validate_attachment_upload(file)
    if Path(file.name).suffix.lower() not in DOCUMENT_EXTENSIONS:
        raise forms.ValidationError('Wybierz dokument, arkusz lub prezentację: PDF, DOC, DOCX, RTF, TXT, XLS, XLSX, CSV, PPT lub PPTX.')
    from .office_service import validate_ooxml
    validate_ooxml(file, Path(file.name).suffix.lstrip('.'))
    return file


class DocumentFilesField(MultipleFileField):
    def clean(self, data, initial=None):
        return [validate_document(file) for file in super().clean(data, initial)]


class OfficeUploadForm(forms.Form):
    files = DocumentFilesField(label='Dokumenty', widget=MultipleFileInput(attrs={
        'class': 'form-input', 'accept': ','.join(sorted(DOCUMENT_EXTENSIONS)),
    }))


class OfficeCreateForm(forms.Form):
    kind = forms.ChoiceField(label='Typ', choices=[('word', 'Dokument — DOCX'), ('cell', 'Arkusz — XLSX'),
                                                  ('slide', 'Prezentacja — PPTX'), ('board', 'Tablica — Board')],
                             widget=forms.Select(attrs={'class': 'form-select tasks-inline-select'}))
    title = forms.CharField(label='Nazwa', max_length=240, widget=forms.TextInput(attrs={'class': 'form-input tasks-inline-input', 'autofocus': True}))


class OfficeFolderForm(forms.ModelForm):
    class Meta:
        model = WorkspaceDocumentFolder
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-input tasks-inline-input'})}

    def __init__(self, *args, owner, workplace, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner, self.workplace, self.parent = owner, workplace, parent

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if name in {'.', '..'} or '/' in name or '\\' in name:
            raise forms.ValidationError('Podaj nazwę folderu bez ukośników.')
        others = WorkspaceDocumentFolder.objects.filter(owner=self.owner, workplace=self.workplace, parent=self.parent, name__iexact=name)
        if self.instance.pk:
            others = others.exclude(pk=self.instance.pk)
        if others.exists():
            raise forms.ValidationError('Folder o tej nazwie już istnieje w tym miejscu.')
        return name


class OfficeDocumentForm(forms.ModelForm):
    revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    replacement = forms.FileField(label='Nowa wersja pliku', required=False, widget=forms.FileInput(attrs={
        'class': 'form-input', 'accept': ','.join(sorted(DOCUMENT_EXTENSIONS)),
    }))

    class Meta:
        model = WorkspaceDocument
        fields = ['title', 'folder', 'tags', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input tasks-inline-input', 'placeholder': 'Nazwa dokumentu'}),
            'folder': forms.Select(attrs={'class': 'form-select tasks-inline-select'}),
            'tags': forms.CheckboxSelectMultiple(),
            'content': forms.Textarea(attrs={'class': 'form-input', 'rows': 20}),
        }

    def __init__(self, *args, owner, workplace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['revision'].initial = self.instance.revision
        self.fields['tags'].queryset = TaskTag.objects.filter(user=owner, workplace=workplace)
        folders = WorkspaceDocumentFolder.objects.filter(owner=owner, workplace=workplace)
        self.fields['folder'].queryset = folders
        self.fields['folder'].empty_label = 'Dokumenty (folder główny)'
        available = {item.pk: item for item in folders}
        def label(item):
            parts, seen = [item.name], {item.pk}
            parent = available.get(item.parent_id)
            while parent and parent.pk not in seen:
                seen.add(parent.pk)
                parts.append(parent.name)
                parent = available.get(parent.parent_id)
            return ' / '.join(reversed(parts))
        self.fields['folder'].label_from_instance = label
        if self.instance.kind != WorkspaceDocument.Kind.TEXT:
            self.fields.pop('content')
        if self.instance.kind != WorkspaceDocument.Kind.FILE:
            self.fields.pop('replacement')

    def clean_content(self):
        return clean_content(self.cleaned_data.get('content', ''))

    def clean_replacement(self):
        file = self.cleaned_data.get('replacement')
        return validate_document(file) if file else None
