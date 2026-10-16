from pathlib import Path

from django import forms

from core.upload_validation import validate_attachment_upload
from .forms import MultipleFileField, MultipleFileInput
from .models import WorkspaceDocument
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
                                                  ('slide', 'Prezentacja — PPTX'), ('pdf', 'PDF'),
                                                  ('form', 'Formularz PDF'), ('board', 'Tablica — Board')],
                             widget=forms.Select(attrs={'class': 'form-select tasks-inline-select'}))
    title = forms.CharField(label='Nazwa', max_length=240, widget=forms.TextInput(attrs={'class': 'form-input tasks-inline-input', 'autofocus': True}))


class OfficeRenameForm(forms.Form):
    title = forms.CharField(label='Nazwa pliku', max_length=255,
                            error_messages={'required': 'Podaj nazwę pliku.'})


class OfficeTemplateForm(forms.Form):
    template = forms.ModelChoiceField(label='Szablon', queryset=WorkspaceDocument.objects.none(),
                                     widget=forms.Select(attrs={'class': 'form-select tasks-inline-select'}))
    title = forms.CharField(label='Nazwa nowego dokumentu', max_length=240,
                            widget=forms.TextInput(attrs={'class': 'form-input tasks-inline-input', 'autofocus': True}))

    def __init__(self, *args, owner, workplace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['template'].queryset = WorkspaceDocument.objects.filter(
            owner=owner, workplace=workplace, is_template=True, deleted_at__isnull=True,
            kind=WorkspaceDocument.Kind.FILE,
        ).order_by('title', 'pk')

    def clean_template(self):
        item = self.cleaned_data['template']
        if not item.office_type:
            raise forms.ValidationError('Szablon musi być plikiem DOCX, XLSX, PPTX lub PDF.')
        return item


class OfficeDocumentForm(forms.ModelForm):
    revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    replacement = forms.FileField(label='Nowa wersja pliku', required=False, widget=forms.FileInput(attrs={
        'class': 'form-input', 'accept': ','.join(sorted(DOCUMENT_EXTENSIONS)),
    }))

    class Meta:
        model = WorkspaceDocument
        fields = ['title', 'content', 'is_template']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input tasks-inline-input', 'placeholder': 'Nazwa dokumentu'}),
            'content': forms.Textarea(attrs={'class': 'form-input', 'rows': 20}),
        }

    def __init__(self, *args, owner, workplace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['revision'].initial = self.instance.revision
        if self.instance.kind != WorkspaceDocument.Kind.TEXT:
            self.fields.pop('content')
        if self.instance.kind != WorkspaceDocument.Kind.FILE:
            self.fields.pop('replacement')
        if not self.instance.office_type:
            self.fields.pop('is_template')

    def clean_content(self):
        return clean_content(self.cleaned_data.get('content', ''))

    def clean_replacement(self):
        file = self.cleaned_data.get('replacement')
        return validate_document(file) if file else None
