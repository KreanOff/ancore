"""Typed account data. Credentials and switcher authentication hashes stay server-side."""
from django.contrib.auth import get_user_model
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone

from core.frontend import form_payload
from .avatar import account_avatar


def _form(form):
    schema = form_payload(form)
    for field, bound in zip(schema['fields'], form):
        # PasswordInput.format_value alone does not implement render_value=False.
        if field['type'] == 'password':
            field['value'] = ''
        for key in ('autocomplete', 'spellcheck'):
            if key in bound.field.widget.attrs:
                field['attrs'][key] = str(bound.field.widget.attrs[key])
    return schema


def _auth_page(context, mode, title):
    return {'type': 'account-auth', 'title': title, 'api_url': reverse('accounts-api'), 'data': {
        'mode': mode, 'form': _form(context['form']),
        'urls': {name: reverse(name) for name in ('login', 'register', 'profile', 'home', 'add_account')},
        'logo': static('img/logo-ancore.png'),
    }}


def login_page(request, context):
    return _auth_page(context, 'login', 'Logowanie')


def register_page(request, context):
    return _auth_page(context, 'register', 'Rejestracja')


def add_account_page(request, context):
    return _auth_page(context, 'add', 'Dodaj konto')


def _date(value):
    return timezone.localtime(value).strftime('%d.%m.%Y, %H:%M') if value else 'Brak danych'


def profile_page(request, context):
    # A bound ModelForm can mutate its instance before validation succeeds.
    # The summary always shows persisted data; only the editor shows the draft.
    user = get_user_model().objects.get(pk=request.user.pk)
    context['form'].current_avatar = account_avatar(user)
    schema = _form(context['form'])
    schema.update(automatic_avatar=context['form'].automatic_avatar, current_avatar=account_avatar(user))
    return {'type': 'account-profile', 'title': 'Profil', 'api_url': reverse('accounts-api'), 'data': {
        'user': {
            'name': user.get_full_name() or user.email, 'first_name': user.first_name,
            'middle_name': user.middle_name, 'last_name': user.last_name, 'email': user.email,
            'username': user.username, 'phone_number': user.phone_number,
            'job_title': user.job_title, 'bio': user.bio, 'avatar': account_avatar(user),
            'presence_status': user.presence_status,
            'active': user.is_active,
            'role': 'Administrator' if user.is_superuser else 'Pracownik' if user.is_staff else 'Użytkownik',
            'joined': _date(user.date_joined), 'last_login': _date(user.last_login),
        },
        'form': schema,
        'accounts': [{
            'id': str(entry['user'].pk), 'name': entry['user'].get_full_name() or entry['user'].email,
            'email': entry['user'].email, 'username': entry['user'].username,
            'current': entry['is_current'], 'avatar': entry['avatar'],
            'presence_status': entry['user'].presence_status,
            'presence_label': entry['user'].get_presence_status_display(),
        } for entry in context['switch_accounts']],
        'urls': {name: reverse(name) for name in (
            'profile', 'add_account', 'update_presence_status', 'switch_account', 'remove_account', 'logout',
        )},
    }}
