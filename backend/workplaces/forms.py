import uuid

from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from core.avatars import AVATARS, AVATAR_CHOICES, preset_avatar
from core.upload_validation import validate_image_crop, validate_image_upload
from .models import Workplace
from .policy import MODULES
from .templatetags.workplace_avatar import workplace_avatar


WORKPLACE_PHOTO_MAX_SIZE = getattr(settings, 'MAX_WORKPLACE_PHOTO_SIZE', 5 * 1024 * 1024)

MODULE_DETAILS = {
    'spaces': {'icon': 'layers', 'description': 'Organizuj pracę w przestrzeniach i zarządzaj zadaniami.'},
    'teams': {'icon': 'users', 'description': 'Twórz zespoły i zarządzaj ich członkami.'},
    'calendar': {'icon': 'calendar', 'description': 'Planuj wydarzenia i przeglądaj terminy zadań.'},
    'documents': {'icon': 'hard-drive', 'description': 'Przechowuj pliki i porządkuj je w folderach.'},
    'office': {'icon': 'file-text', 'description': 'Twórz i edytuj dokumenty, arkusze oraz prezentacje.'},
    'resources': {'icon': 'package', 'description': 'Prowadź ewidencję sprzętu, licencji i narzędzi.'},
    'dashboards': {'icon': 'layout-dashboard', 'description': 'Śledź postęp pracy i przeglądaj dane na pulpitach.'},
    'filters': {'icon': 'filter', 'description': 'Wyszukuj zadania i zapisuj własne zestawy filtrów.'},
}


class WorkplaceModuleSelect(forms.CheckboxSelectMultiple):
    template_name = 'workplaces/widgets/module_select.html'
    option_template_name = 'workplaces/widgets/module_option.html'

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        option.update(MODULE_DETAILS.get(str(value), {}))
        option['attrs']['role'] = 'switch'
        if option['attrs'].get('id'):
            option['attrs']['aria-labelledby'] = option['attrs']['id'] + '-label'
            option['attrs']['aria-describedby'] = option['attrs']['id'] + '-description'
        return option


class RegistrationWorkspaceForm(forms.Form):
    name = forms.CharField(
        label='Nazwa Workspace', required=True,
        max_length=Workplace._meta.get_field('name').max_length,
        error_messages={'required': 'Wpisz nazwę Workspace.', 'max_length': 'Nazwa Workspace może mieć maksymalnie 140 znaków.'},
        widget=forms.TextInput(attrs={
            'class': 'form-input', 'id': 'workspace-name', 'autocomplete': 'organization',
        }),
    )

    def clean_name(self):
        return ' '.join((self.cleaned_data.get('name') or '').split())


class WorkplaceForm(forms.ModelForm):
    enabled_modules = forms.MultipleChoiceField(
        label='Włączone moduły', choices=MODULES, required=False,
        widget=WorkplaceModuleSelect, help_text='Wyłączenie modułu zachowuje jego dane.',
    )
    avatar = forms.ChoiceField(
        label='Awatar Workspace', choices=AVATAR_CHOICES, required=False, widget=forms.RadioSelect,
    )
    workplace_photo = forms.FileField(
        label='Logo miejsca pracy',
        required=False,
        widget=forms.FileInput(attrs={
            'accept': '.png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp',
            'class': 'profile-photo-input',
            'hidden': True,
        }),
    )
    workplace_photo_crop = forms.CharField(
        label='Przycięte logo',
        required=False,
        widget=forms.HiddenInput(attrs={
            'class': 'profile-photo-crop-input',
            'data-profile-photo-crop-input': True,
        }),
    )
    workplace_photo_remove = forms.CharField(
        label='Usuń zdjęcie',
        required=False,
        widget=forms.HiddenInput(attrs={
            'data-profile-photo-remove-input': True,
        }),
    )

    class Meta:
        model = Workplace
        fields = ['avatar', 'workplace_photo', 'name', 'description']
        error_messages = {
            'name': {
                'required': 'Wpisz nazwę miejsca pracy.',
                'max_length': 'Nazwa miejsca pracy może mieć maksymalnie 140 znaków.',
            },
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nazwa miejsca pracy',
                'class': 'tasks-inline-input workplace-create-modal__name-input workplace-create-modal__text-input',
                'autocomplete': 'off',
                'data-workplace-name-input': True,
                'aria-describedby': 'workplace-create-name-hint workplace-create-name-counter',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Dodaj krótki opis miejsca pracy…',
                'class': 'tasks-inline-input tasks-modal-textarea workplace-create-modal__text-input workplace-create-modal__textarea',
                'rows': 3,
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.initial['avatar'] = 'upload' if self.instance.workplace_photo else self.instance.avatar or 'auto'
        self.avatar_options = [preset_avatar(key) for key, _ in AVATARS]
        self.automatic_avatar = preset_avatar(seed=self.instance.pk or 0)
        self.current_avatar = workplace_avatar(self.instance)
        self.original_photo = self.instance.workplace_photo.name
        self.initial['enabled_modules'] = [key for key, _ in MODULES if key not in self.instance.disabled_modules]

    def clean_avatar(self):
        # Older clients can still submit only the existing photo/settings fields.
        if 'avatar' not in self.data:
            if self.data.get('workplace_photo_remove') == '1':
                return 'auto'
            if self.files.get('workplace_photo') or self.data.get('workplace_photo_crop'):
                return 'upload'
            return self.initial['avatar']
        return self.cleaned_data.get('avatar') or 'auto'

    def clean(self):
        data = super().clean()
        self.avatar_mode = data.get('avatar', 'auto')
        if self.avatar_mode == 'upload':
            if (not data.get('workplace_photo') and not data.get('workplace_photo_crop')
                    and not self.original_photo and not self.errors.get('workplace_photo')
                    and not self.errors.get('workplace_photo_crop')):
                self.add_error('workplace_photo', 'Wybierz obraz do przesłania.')
        else:
            data['workplace_photo'] = None
        data['avatar'] = self.avatar_mode if self.avatar_mode not in {'auto', 'upload'} else ''
        return data

    def clean_name(self):
        name = ' '.join((self.cleaned_data.get('name') or '').split())
        if not name:
            raise forms.ValidationError('Wpisz nazwę miejsca pracy.')

        return name

    def clean_description(self):
        return (self.cleaned_data.get('description') or '').strip()

    def clean_enabled_modules(self):
        if 'modules_submitted' not in self.data and 'enabled_modules' not in self.data:
            return self.initial['enabled_modules']
        return self.cleaned_data['enabled_modules']

    def clean_workplace_photo(self):
        if 'avatar' in self.data and self.data.get('avatar') != 'upload':
            return None
        workplace_photo = self.cleaned_data.get('workplace_photo')

        if not workplace_photo:
            return workplace_photo

        return validate_image_upload(workplace_photo, WORKPLACE_PHOTO_MAX_SIZE)

    def clean_workplace_photo_crop(self):
        if 'avatar' in self.data and self.data.get('avatar') != 'upload':
            return None
        return validate_image_crop(
            self.cleaned_data.get('workplace_photo_crop'), WORKPLACE_PHOTO_MAX_SIZE,
            error_message='Nie udało się odczytać przyciętego logo.',
        )

    def clean_workplace_photo_remove(self):
        return (self.cleaned_data.get('workplace_photo_remove') or '').strip() == '1'

    def save(self, commit=True):
        workplace = super().save(commit=False)
        workplace.disabled_modules = [key for key, _ in MODULES if key not in self.cleaned_data['enabled_modules']]
        self.apply_photo(workplace, commit=False)

        if commit:
            with transaction.atomic():
                workplace.save()
                self.cleanup_previous_photo(workplace)

        return workplace

    def cleanup_previous_photo(self, workplace):
        old_name = self.original_photo
        if old_name and old_name != workplace.workplace_photo.name:
            storage = workplace._meta.get_field('workplace_photo').storage

            def cleanup():
                if not Workplace.objects.filter(workplace_photo=old_name).exists():
                    storage.delete(old_name)
            transaction.on_commit(cleanup, robust=True)

    def apply_photo(self, workplace, commit=True):
        photo_crop = self.cleaned_data.get('workplace_photo_crop')

        if self.avatar_mode != 'upload':
            workplace.workplace_photo = ''
            photo_crop = None
        elif self.cleaned_data.get('workplace_photo_remove') and not photo_crop:
            workplace.workplace_photo = ''

        if photo_crop:
            filename = f'workplace_{workplace.pk or "new"}_{uuid.uuid4().hex}.{photo_crop["extension"]}'
            workplace.workplace_photo.save(filename, ContentFile(photo_crop['content']), save=False)

        if commit:
            workplace.save()

        return workplace
