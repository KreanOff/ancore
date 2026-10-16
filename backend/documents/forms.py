from pathlib import Path

from django import forms

from core.upload_validation import (
    ATTACHMENT_ALLOWED_EXTENSIONS, validate_attachment_upload,
)
from .models import Document, DocumentLibrary, Folder, icon_color_validator


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else [data]
        cleaned = [super(MultipleFileField, self).clean(item, initial) for item in files]
        if len(cleaned) > 20:
            raise forms.ValidationError('Prześlij jednocześnie maksymalnie 20 plików.')
        return [validate_attachment_upload(item) for item in cleaned]


class UploadForm(forms.Form):
    files = MultipleFileField(label='Pliki', widget=MultipleFileInput(attrs={
        'class': 'form-input',
        'accept': ','.join(sorted(ATTACHMENT_ALLOWED_EXTENSIONS)),
    }))

    def clean_files(self):
        from .office_service import validate_ooxml
        files = self.cleaned_data['files']
        for file in files:
            validate_ooxml(file, Path(file.name).suffix.lstrip('.'))
        return files


class IconColorForm(forms.ModelForm):
    color = forms.CharField(label='Kolor ikony', max_length=7, required=False,
        validators=[icon_color_validator], widget=forms.TextInput(attrs={
            'type': 'color', 'class': 'documents-color-input', 'data-document-color-input': '',
        }))
    color_icon_template = 'documents/includes/folder_icon.html'

    @property
    def default_color(self):
        return self.instance._meta.get_field('color').get_default()

    @property
    def preview_color(self):
        value = self['color'].value() or self.default_color
        try:
            icon_color_validator(value)
        except forms.ValidationError:
            return self.default_color
        return value.lower()

    def clean_color(self):
        # Older forms may omit this field; keep the saved color on a name-only edit.
        return (self.cleaned_data.get('color') or self.instance.color or self.default_color).lower()


class LibraryForm(IconColorForm):
    color_icon_template = 'documents/includes/drive_icon.html'

    class Meta:
        model = DocumentLibrary
        fields = ['name', 'color', 'description']
        labels = {'name': 'Nazwa dysku'}
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input tasks-inline-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }

    def __init__(self, *args, owner, workplace, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner, self.workplace = owner, workplace

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        duplicates = DocumentLibrary.objects.filter(owner=self.owner, workplace=self.workplace, name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('Dysk o tej nazwie już istnieje w tym Workspace.')
        return name


class FolderForm(IconColorForm):
    class Meta:
        model = Folder
        fields = ['name', 'color']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-input tasks-inline-input'})}

    def __init__(self, *args, owner, workplace, library, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner, self.workplace, self.parent = owner, workplace, parent
        self.library = library

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not name or name in {'.', '..'} or '/' in name or '\\' in name:
            raise forms.ValidationError('Podaj nazwę folderu bez ukośników.')
        duplicates = Folder.objects.filter(owner=self.owner, workplace=self.workplace, library=self.library, parent=self.parent, name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('Folder o tej nazwie już istnieje w tym miejscu.')
        return name


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'description', 'folder']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input tasks-inline-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'folder': forms.Select(attrs={'class': 'form-select tasks-inline-select'}),
        }
        labels = {'title': 'Nazwa pliku', 'folder': 'Folder'}

    def __init__(self, *args, owner, workplace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(owner=owner, workplace=workplace, library=self.instance.library)
        self.fields['folder'].empty_label = f'{self.instance.library.name} (folder główny)'
        folders = {folder.pk: folder for folder in self.fields['folder'].queryset}

        def folder_label(folder):
            parts = [folder.name]
            parent = folders.get(folder.parent_id)
            while parent:
                parts.append(parent.name)
                parent = folders.get(parent.parent_id)
            return ' / '.join(reversed(parts))

        self.fields['folder'].label_from_instance = folder_label
