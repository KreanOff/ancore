from django import forms
from django.contrib.auth import get_user_model

from accounts.models import normalize_public_username
from .models import Company, Contact, SharedItem


class ContactForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = False
        self.fields['company_record'].queryset = Company.objects.none()
        if user is not None:
            self.fields['company_record'].queryset = Company.objects.filter(owner=user)

    def _validate_required_identity(self, cleaned_data):
        first_name = (cleaned_data.get('first_name') or '').strip()
        company = (cleaned_data.get('company') or '').strip()
        company_record = cleaned_data.get('company_record')
        if not first_name and not company and not company_record:
            self.add_error('first_name', 'Podaj imię albo firmę.')

    def clean(self):
        cleaned_data = super().clean()
        self._validate_required_identity(cleaned_data)
        return cleaned_data

    def save(self, commit=True):
        contact = super().save(commit=False)
        if contact.company_record and not contact.company:
            contact.company = contact.company_record.name
        if commit:
            contact.save()
            self.save_m2m()
        return contact

    class Meta:
        model = Contact
        fields = [
            'first_name',
            'last_name',
            'company',
            'company_record',
            'role',
            'email',
            'phone',
            'source',
            'last_contacted_at',
            'notes',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'placeholder': 'Imię',
                'class': 'form-input',
            }),
            'last_name': forms.TextInput(attrs={
                'placeholder': 'Nazwisko',
                'class': 'form-input',
            }),
            'company': forms.TextInput(attrs={
                'placeholder': 'Firma',
                'class': 'form-input',
            }),
            'company_record': forms.Select(attrs={
                'class': 'form-input',
            }),
            'role': forms.TextInput(attrs={
                'placeholder': 'Stanowisko',
                'class': 'form-input',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'email@firma.pl',
                'class': 'form-input',
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': '+48 000 000 000',
                'class': 'form-input',
            }),
            'source': forms.TextInput(attrs={
                'placeholder': 'Źródło kontaktu',
                'class': 'form-input',
            }),
            'last_contacted_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-input',
            }),
            'notes': forms.Textarea(attrs={
                'placeholder': 'Notatki, kontekst rozmów, ustalenia...',
                'rows': 8,
                'class': 'form-input',
            }),
        }

    def clean_first_name(self):
        return (self.cleaned_data.get('first_name') or '').strip()

    def clean_last_name(self):
        return (self.cleaned_data.get('last_name') or '').strip()

    def clean_company(self):
        return (self.cleaned_data.get('company') or '').strip()


class ContactModalForm(ContactForm):
    ancore_login = forms.CharField(
        required=False,
        label='Login Ancore',
        widget=forms.TextInput(attrs={
            'placeholder': '@login.ancore',
            'class': 'tasks-inline-input',
            'autocomplete': 'off',
            'data-ancore-login-input': '',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ancore_user = None
        text_fields = [
            'ancore_login',
            'first_name',
            'last_name',
            'company',
            'role',
            'email',
            'phone',
            'source',
            'last_contacted_at',
        ]
        select_fields = ['company_record']

        for name in text_fields:
            self.fields[name].widget.attrs['class'] = 'tasks-inline-input'
        for name in select_fields:
            self.fields[name].widget.attrs['class'] = 'tasks-inline-select'

        self.fields['first_name'].widget.attrs['placeholder'] = 'Imię'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Nazwisko'
        self.fields['notes'].widget.attrs.update({
            'class': 'tasks-inline-input tasks-modal-textarea',
            'rows': 4,
        })

    def _lookup_ancore_user(self, login):
        normalized_login = normalize_public_username(login)
        if not normalized_login:
            return None
        users = get_user_model().objects.filter(is_active=True, username__iexact=normalized_login)
        if self.user is not None:
            users = users.exclude(pk=self.user.pk)
        return users.first()

    def clean_ancore_login(self):
        return normalize_public_username(self.cleaned_data.get('ancore_login'))

    def clean(self):
        cleaned_data = forms.ModelForm.clean(self)
        ancore_login = cleaned_data.get('ancore_login')

        if ancore_login:
            self.ancore_user = self._lookup_ancore_user(ancore_login)
            if self.ancore_user is None:
                self.add_error('ancore_login', 'Nie znaleziono użytkownika z takim Loginem Ancore.')
            else:
                cleaned_data['first_name'] = cleaned_data.get('first_name') or self.ancore_user.first_name
                cleaned_data['last_name'] = cleaned_data.get('last_name') or self.ancore_user.last_name
                cleaned_data['email'] = cleaned_data.get('email') or self.ancore_user.email
                cleaned_data['phone'] = cleaned_data.get('phone') or self.ancore_user.phone_number
                cleaned_data['role'] = cleaned_data.get('role') or self.ancore_user.job_title
                cleaned_data['source'] = cleaned_data.get('source') or 'Użytkownik aplikacji'

        self._validate_required_identity(cleaned_data)
        return cleaned_data

    def save(self, commit=True):
        contact = super().save(commit=False)
        if self.ancore_user is not None:
            contact.status = 'active'
        if commit:
            contact.save()
            self.save_m2m()
        return contact


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'website', 'email', 'phone', 'address', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nazwa firmy',
                'class': 'form-input',
            }),
            'website': forms.URLInput(attrs={
                'placeholder': 'https://firma.pl',
                'class': 'form-input',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'kontakt@firma.pl',
                'class': 'form-input',
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': '+48 000 000 000',
                'class': 'form-input',
            }),
            'address': forms.TextInput(attrs={
                'placeholder': 'Adres',
                'class': 'form-input',
            }),
            'notes': forms.Textarea(attrs={
                'placeholder': 'Notatki o firmie, kontekst, ustalenia...',
                'rows': 8,
                'class': 'form-input',
            }),
        }

    def clean_name(self):
        return (self.cleaned_data.get('name') or '').strip()


class CompanyModalForm(CompanyForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ['name', 'website', 'email', 'phone', 'address']:
            self.fields[name].widget.attrs['class'] = 'tasks-inline-input'
        self.fields['notes'].widget.attrs.update({
            'class': 'tasks-inline-input tasks-modal-textarea',
            'rows': 4,
        })


class ShareItemForm(forms.ModelForm):
    shared_with = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        label='Udostępnij użytkownikowi',
        widget=forms.Select(attrs={'class': 'form-input'}),
    )

    class Meta:
        model = SharedItem
        fields = ['shared_with', 'permission', 'note']
        widgets = {
            'permission': forms.Select(attrs={'class': 'form-input'}),
            'note': forms.TextInput(attrs={
                'placeholder': 'Krótka wiadomość opcjonalnie',
                'class': 'form-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        users = get_user_model().objects.filter(is_active=True)
        if user is not None:
            users = users.exclude(pk=user.pk)
        self.fields['shared_with'].queryset = users.order_by('first_name', 'last_name', 'email')

    def clean_note(self):
        return (self.cleaned_data.get('note') or '').strip()
