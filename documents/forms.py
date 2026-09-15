from django import forms

from core.upload_validation import ATTACHMENT_ALLOWED_EXTENSIONS, validate_attachment_upload
from tasks.models import TaskTag
from .models import Document, DocumentLibrary, Folder


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
        'accept': ','.join(sorted(ATTACHMENT_ALLOWED_EXTENSIONS)),
    }))


class LibraryForm(forms.ModelForm):
    class Meta:
        model = DocumentLibrary
        fields = ['name', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, owner, workplace, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner, self.workplace = owner, workplace

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        duplicates = DocumentLibrary.objects.filter(owner=self.owner, workplace=self.workplace, name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('Biblioteka o tej nazwie już istnieje w tym Workspace.')
        return name


class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ['name']

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
        fields = ['title', 'description', 'folder', 'tags']
        widgets = {'description': forms.Textarea(attrs={'rows': 3}), 'tags': forms.CheckboxSelectMultiple}
        labels = {'folder': 'Folder'}

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
        self.fields['tags'].queryset = TaskTag.objects.filter(user=owner, workplace=workplace)
