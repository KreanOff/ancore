import base64
import binascii
import uuid

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from core.upload_validation import validate_image_bytes, validate_image_upload
from .avatar import avatar_color_seed
from .avatar_presets import AVATARS, AVATAR_CHOICES, preset_avatar
from .models import (
    PUBLIC_USERNAME_RE,
    User,
    default_public_username,
    normalize_public_username,
    unique_public_username,
)


PROFILE_PHOTO_MAX_SIZE = getattr(settings, 'MAX_PROFILE_PHOTO_SIZE', 5 * 1024 * 1024)
PROFILE_BANNER_MAX_SIZE = 5 * 1024 * 1024


class UserRegistrationForm(UserCreationForm):
    _input_attrs = {'class': 'form-input'}

    first_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        **{'id': 'first-name', 'autocomplete': 'given-name'},
        **_input_attrs,
    }))
    middle_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={
        **{'id': 'middle-name', 'autocomplete': 'additional-name'},
        **_input_attrs,
    }))
    last_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        **{'id': 'last-name', 'autocomplete': 'family-name'},
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
        })
        self.fields['password2'].widget.attrs.update({
            'autocomplete': 'new-password',
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
        base_username = default_public_username(user.first_name, user.last_name, user.email)
        for attempt in range(5):
            user.username = unique_public_username(base_username)
            if not commit:
                break
            try:
                # A savepoint allows a fresh lookup after a concurrent INSERT,
                # including when the caller already owns a transaction.
                with transaction.atomic():
                    user.save()
            except IntegrityError as error:
                constraint = getattr(getattr(error.__cause__, 'diag', None), 'constraint_name', '')
                if constraint != 'accounts_user_username_key' or attempt == 4:
                    raise
            else:
                break
        return user


class UserBannerForm(forms.ModelForm):
    crop_defaults = {'profile_banner_x': 50, 'profile_banner_y': 50, 'profile_banner_zoom': 1}

    profile_banner = forms.FileField(
        label='Baner profilu', required=False,
        help_text='JPG, PNG lub WebP, maksymalnie 5 MB.',
        widget=forms.FileInput(attrs={
            'accept': '.png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp',
            'class': 'form-input',
        }),
    )
    remove_banner = forms.BooleanField(label='Przywróć domyślny baner', required=False)
    profile_banner_x = forms.FloatField(
        label='Pozycja pozioma (%)', required=False, min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': 'any'}),
    )
    profile_banner_y = forms.FloatField(
        label='Pozycja pionowa (%)', required=False, min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': 'any'}),
    )
    profile_banner_zoom = forms.FloatField(
        label='Powiększenie', required=False, min_value=1, max_value=3,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': 'any'}),
    )

    class Meta:
        model = User
        fields = ('profile_banner', 'profile_banner_x', 'profile_banner_y', 'profile_banner_zoom')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_banner = self.instance.profile_banner.name
        self.original_crop = {name: getattr(self.instance, name) for name in self.crop_defaults}

    def clean_profile_banner(self):
        upload = self.files.get('profile_banner')
        if upload:
            validate_image_upload(upload, PROFILE_BANNER_MAX_SIZE)
        return self.cleaned_data.get('profile_banner')

    def clean(self):
        data = super().clean()
        upload = self.files.get('profile_banner')
        remove = data.get('remove_banner') and not upload
        self.submitted_crop = {
            name for name in self.crop_defaults
            if self.data.get(self.add_prefix(name)) not in self.fields[name].empty_values
        }
        if not upload and not remove and not (self.original_banner and self.submitted_crop):
            self.add_error('profile_banner', 'Wybierz obraz, zmień kadr własnego banera lub przywróć domyślny baner.')
        for name, default in self.crop_defaults.items():
            if name in self.errors:
                continue
            if remove:
                data[name] = default
            elif data.get(name) is None:
                data[name] = default if upload else self.original_crop[name]
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.files.get('profile_banner') and not user.profile_banner._committed:
            # Every upload gets a new URL, even after deleting a previous banner.
            extension = user.profile_banner.name.rsplit('.', 1)[-1].lower()
            user.profile_banner.name = f'banner_{uuid.uuid4().hex}.{extension}'
        elif self.cleaned_data.get('remove_banner') and not self.files.get('profile_banner'):
            user.profile_banner = ''
        if commit:
            with transaction.atomic():
                # Serialize replacements and leave unrelated profile fields intact.
                previous = User.objects.select_for_update().only(*self._meta.fields).get(pk=user.pk)
                old_name = previous.profile_banner.name
                replaces_file = bool(self.files.get('profile_banner') or self.cleaned_data.get('remove_banner'))
                if replaces_file:
                    update_fields = self._meta.fields
                else:
                    if not old_name or old_name != self.original_banner:
                        raise forms.ValidationError('Baner został zmieniony. Odśwież profil i ponownie ustaw kadr.')
                    update_fields = self.submitted_crop
                    for name in self.crop_defaults.keys() - self.submitted_crop:
                        setattr(user, name, getattr(previous, name))
                user.save(update_fields=update_fields)
                if replaces_file and old_name and old_name != user.profile_banner.name:
                    storage = user._meta.get_field('profile_banner').storage

                    def cleanup():
                        if not User.objects.filter(profile_banner=old_name).exists():
                            storage.delete(old_name)
                    transaction.on_commit(cleanup, robust=True)
        return user


class UserProfileForm(forms.ModelForm):
    _input_attrs = {'class': 'form-input'}
    _profile_input_attrs = {'class': 'form-input profile-field-input'}

    avatar = forms.ChoiceField(
        label='Awatar użytkownika', choices=AVATAR_CHOICES, required=False, widget=forms.RadioSelect,
    )

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
        'accept': '.png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp',
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
            'avatar',
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_photo = self.instance.profile_photo.name
        self.initial['avatar'] = 'upload' if self.original_photo else self.instance.avatar or 'auto'
        self.avatar_options = [preset_avatar(key) for key, _ in AVATARS]
        self.automatic_avatar = preset_avatar(seed=avatar_color_seed(self.instance))
        self.avatar_art_class = 'user-avatar-art'

    def clean_avatar(self):
        # Preserve existing selections when older clients only edit profile fields.
        if 'avatar' not in self.data:
            if self.data.get('profile_photo_crop') or self.files.get('profile_photo'):
                return 'upload'
            if self.data.get('profile_photo_remove') == '1':
                return 'auto'
            return self.initial['avatar']
        return self.cleaned_data.get('avatar') or 'auto'

    def clean(self):
        data = super().clean()
        self.avatar_mode = data.get('avatar', 'auto')
        if self.avatar_mode == 'upload':
            if (not data.get('profile_photo') and not data.get('profile_photo_crop')
                    and not self.original_photo and not self.errors.get('profile_photo')
                    and not self.errors.get('profile_photo_crop')):
                self.add_error('profile_photo', 'Wybierz obraz do przesłania.')
        else:
            data['profile_photo'] = None
        data['avatar'] = self.avatar_mode if self.avatar_mode not in {'auto', 'upload'} else ''
        return data

    def clean_profile_photo_crop(self):
        if 'avatar' in self.data and self.data.get('avatar') != 'upload':
            return None
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
        if 'avatar' in self.data and self.data.get('avatar') != 'upload':
            return None
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

        if self.avatar_mode != 'upload':
            user.profile_photo = ''
            photo_crop = None
        elif self.cleaned_data.get('profile_photo_remove') and not photo_crop:
            user.profile_photo = ''

        if photo_crop:
            filename = f'profile_{user.pk or "new"}_{uuid.uuid4().hex}.{photo_crop["extension"]}'
            user.profile_photo.save(filename, ContentFile(photo_crop['content']), save=False)

        if commit:
            with transaction.atomic():
                user.save(update_fields=self._meta.fields if user.pk else None)
                old_name = self.original_photo
                if old_name and old_name != user.profile_photo.name:
                    storage = user._meta.get_field('profile_photo').storage

                    def cleanup():
                        if not User.objects.filter(profile_photo=old_name).exists():
                            storage.delete(old_name)
                    transaction.on_commit(cleanup, robust=True)

        return user
