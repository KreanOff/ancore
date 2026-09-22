import base64
import binascii
import uuid

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.core.files.base import ContentFile
from core.upload_validation import validate_image_bytes, validate_image_upload
from .models import (
    PUBLIC_USERNAME_RE,
    User,
    default_public_username,
    normalize_public_username,
    unique_public_username,
)


PROFILE_PHOTO_MAX_SIZE = getattr(settings, 'MAX_PROFILE_PHOTO_SIZE', 5 * 1024 * 1024)


class UserRegistrationForm(UserCreationForm):
    _input_attrs = {'class': 'form-input'}

    first_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        **{'placeholder': 'Anna', 'id': 'first-name', 'autocomplete': 'given-name'},
        **_input_attrs,
    }))
    middle_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={
        **{'placeholder': 'Maria (opcjonalnie)', 'id': 'middle-name', 'autocomplete': 'additional-name'},
        **_input_attrs,
    }))
    last_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        **{'placeholder': 'Kowalska', 'id': 'last-name', 'autocomplete': 'family-name'},
        **_input_attrs,
    }))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        **{'placeholder': 'email@firma.pl', 'id': 'email', 'autocomplete': 'email'},
        **_input_attrs,
    }))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'middle_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-input')
        self.fields['password1'].widget.attrs.update({
            'autocomplete': 'new-password',
            'placeholder': 'Wpisz hasło',
        })
        self.fields['password2'].widget.attrs.update({
            'autocomplete': 'new-password',
            'placeholder': 'Powtórz hasło',
        })

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ten adres email jest już używany.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.middle_name = self.cleaned_data.get('middle_name', '')
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.username = unique_public_username(
            default_public_username(user.first_name, user.last_name, user.email)
        )
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    _input_attrs = {'class': 'form-input'}
    _profile_input_attrs = {'class': 'form-input profile-field-input'}

    first_name = forms.CharField(label='Imię', max_length=150, required=True, widget=forms.TextInput(attrs={
        **{'placeholder': 'Imię'},
        **_input_attrs,
    }))
    middle_name = forms.CharField(label='Drugie imię', max_length=150, required=False, widget=forms.TextInput(attrs={
        **{'placeholder': 'Drugie imię', 'autocomplete': 'additional-name'},
        **_input_attrs,
    }))
    last_name = forms.CharField(label='Nazwisko', max_length=150, required=True, widget=forms.TextInput(attrs={
        **{'placeholder': 'Nazwisko'},
        **_input_attrs,
    }))
    email = forms.EmailField(label='Email', required=True, widget=forms.EmailInput(attrs={
        **{'placeholder': 'Adres email', 'autocomplete': 'email'},
        **_input_attrs,
    }))
    username = forms.CharField(label='ID Ancore', max_length=150, required=True, widget=forms.TextInput(attrs={
        **{'placeholder': '@imie.nazwisko', 'autocomplete': 'off', 'spellcheck': 'false'},
        **_profile_input_attrs,
    }))
    profile_photo = forms.FileField(label='Zdjęcie użytkownika', required=False, widget=forms.FileInput(attrs={
        'accept': 'image/*',
        'class': 'profile-photo-input',
        'hidden': True,
    }))
    profile_photo_crop = forms.CharField(
        label='Przycięte zdjęcie',
        required=False,
        widget=forms.HiddenInput(attrs={
            'class': 'profile-photo-crop-input',
            'data-profile-photo-crop-input': True,
        }),
    )
    profile_photo_remove = forms.CharField(
        label='Usuń zdjęcie',
        required=False,
        widget=forms.HiddenInput(attrs={
            'data-profile-photo-remove-input': True,
        }),
    )
    phone_number = forms.CharField(label='Numer telefonu', max_length=32, required=False, widget=forms.TextInput(attrs={
        **{'placeholder': '+48 123 456 789', 'autocomplete': 'tel'},
        **_profile_input_attrs,
    }))
    job_title = forms.CharField(label='Stanowisko', max_length=120, required=False, widget=forms.TextInput(attrs={
        **{'placeholder': 'Stanowisko', 'autocomplete': 'organization-title'},
        **_profile_input_attrs,
    }))
    bio = forms.CharField(label='Bio', required=False, widget=forms.Textarea(attrs={
        **{'placeholder': 'Krótki opis użytkownika', 'rows': 4},
        **_profile_input_attrs,
    }))
    presence_status = forms.ChoiceField(
        label='Status',
        choices=User.PresenceStatus.choices,
        required=True,
        widget=forms.Select(attrs={
            **{'aria-label': 'Status użytkownika'},
            **{'class': 'form-input profile-status-source'},
        }),
    )

    class Meta:
        model = User
        fields = (
            'profile_photo',
            'first_name',
            'middle_name',
            'last_name',
            'email',
            'username',
            'phone_number',
            'job_title',
            'bio',
            'presence_status',
        )

    def clean_profile_photo_crop(self):
        crop_data = (self.cleaned_data.get('profile_photo_crop') or '').strip()

        if not crop_data:
            return None

        header, separator, encoded = crop_data.partition(',')
        if not separator or not header.startswith('data:') or not header.endswith(';base64'):
            raise forms.ValidationError('Nie udało się odczytać przyciętego zdjęcia.')

        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            raise forms.ValidationError('Nie udało się odczytać przyciętego zdjęcia.')

        content_type = header[5:-7].lower()
        extension = validate_image_bytes(content, content_type, PROFILE_PHOTO_MAX_SIZE)

        return {
            'content': content,
            'extension': extension,
        }

    def clean_profile_photo(self):
        profile_photo = self.cleaned_data.get('profile_photo')

        if not profile_photo:
            return profile_photo

        return validate_image_upload(profile_photo, PROFILE_PHOTO_MAX_SIZE)

    def clean_profile_photo_remove(self):
        return (self.cleaned_data.get('profile_photo_remove') or '').strip() == '1'

    def clean_email(self):
        email = self.cleaned_data['email']
        exists = User.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists()
        if exists:
            raise forms.ValidationError('Ten adres email jest już używany.')
        return email

    def clean_username(self):
        username = normalize_public_username(self.cleaned_data['username'])

        if not PUBLIC_USERNAME_RE.fullmatch(username):
            raise forms.ValidationError(
                'ID Ancore musi zaczynać się od @ i mieć minimum 3 znaki: litery, cyfry, kropki, podkreślenia albo myślniki.'
            )

        exists = User.objects.exclude(pk=self.instance.pk).filter(username__iexact=username).exists()
        if exists:
            raise forms.ValidationError('To ID Ancore jest już zajęte.')

        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        photo_crop = self.cleaned_data.get('profile_photo_crop')

        if self.cleaned_data.get('profile_photo_remove') and not photo_crop:
            user.profile_photo.delete(save=False)

        if photo_crop:
            filename = f'profile_{user.pk or "new"}_{uuid.uuid4().hex}.{photo_crop["extension"]}'
            user.profile_photo.save(filename, ContentFile(photo_crop['content']), save=False)

        if commit:
            user.save()

        return user
