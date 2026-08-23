from django import forms
from django.conf import settings

from core.upload_validation import validate_image_upload
from .models import Workplace


WORKPLACE_PHOTO_MAX_SIZE = getattr(settings, 'MAX_WORKPLACE_PHOTO_SIZE', 5 * 1024 * 1024)


class WorkplaceForm(forms.ModelForm):
    workplace_photo = forms.FileField(
        label='Logo miejsca pracy',
        required=False,
        widget=forms.FileInput(attrs={
            'accept': '.png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp',
            'class': 'workplace-edit-modal__file-input',
        }),
    )
    workplace_photo_remove = forms.CharField(
        label='Usuń zdjęcie',
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Workplace
        fields = ['workplace_photo', 'name']
        error_messages = {
            'name': {
                'required': 'Wpisz nazwę miejsca pracy.',
                'max_length': 'Nazwa miejsca pracy może mieć maksymalnie 140 znaków.',
            },
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'np. Studio projektowe',
                'class': 'workplace-create-modal__name-input',
                'autocomplete': 'off',
                'data-workplace-name-input': True,
                'aria-describedby': 'workplace-create-name-hint workplace-create-name-counter',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = ' '.join((self.cleaned_data.get('name') or '').split())
        if not name:
            raise forms.ValidationError('Wpisz nazwę miejsca pracy.')

        if self.user is not None:
            duplicate_workplaces = Workplace.objects.filter(owner=self.user, name__iexact=name)
            if self.instance.pk:
                duplicate_workplaces = duplicate_workplaces.exclude(pk=self.instance.pk)
            if duplicate_workplaces.exists():
                raise forms.ValidationError('Masz już miejsce pracy o takiej nazwie.')

        return name

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
