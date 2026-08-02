from django import forms
from django.conf import settings

from core.upload_validation import validate_image_upload
from .models import Workplace


WORKPLACE_PHOTO_MAX_SIZE = getattr(settings, 'MAX_WORKPLACE_PHOTO_SIZE', 5 * 1024 * 1024)


class WorkplaceForm(forms.ModelForm):
    workplace_photo = forms.FileField(label='Zdjęcie miejsca pracy', required=False, widget=forms.FileInput(attrs={
        'accept': 'image/*',
        'class': 'form-input workplace-settings__photo-input',
    }))
    workplace_photo_remove = forms.CharField(
        label='Usuń zdjęcie',
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Workplace
        fields = ['workplace_photo', 'name']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nazwa miejsca pracy',
                'class': 'tasks-inline-input',
                'autocomplete': 'off',
            }),
        }

    def clean_name(self):
        return (self.cleaned_data.get('name') or '').strip()

    def clean_workplace_photo(self):
        workplace_photo = self.cleaned_data.get('workplace_photo')

        if not workplace_photo:
            return workplace_photo

        return validate_image_upload(workplace_photo, WORKPLACE_PHOTO_MAX_SIZE)

    def clean_workplace_photo_remove(self):
        return (self.cleaned_data.get('workplace_photo_remove') or '').strip() == '1'

    def save(self, commit=True):
        workplace = super().save(commit=False)

        if self.cleaned_data.get('workplace_photo_remove') and not self.cleaned_data.get('workplace_photo'):
            workplace.workplace_photo.delete(save=False)

        if commit:
            workplace.save()

        return workplace
