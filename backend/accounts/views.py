import json

from django.conf import settings
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.crypto import constant_time_compare
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from core.api import api_error
from core.frontend import render
from .avatar import account_avatar as _account_avatar
from .forms import UserProfileForm, UserRegistrationForm
from .presence import mark_user_inactive, mark_user_seen

SWITCH_ACCOUNTS_SESSION_KEY = 'switch_account_user_ids'
SWITCH_ACCOUNTS_HASHES_KEY = 'switch_account_auth_hashes'


class AccountLoginView(LoginView):
    template_name = 'accounts/login.html'

    def render_to_response(self, context, **response_kwargs):
        if getattr(self.request, '_react_api', False) and context['form'].errors:
            response_kwargs['status'] = 400
        return render(self.request, self.template_name, context, **response_kwargs)

    def get_redirect_url(self):
        # Every login opens the same landing page, including requests with next.
        return ''


class AccountLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            mark_user_inactive(request.user)
        request.session.pop(SWITCH_ACCOUNTS_SESSION_KEY, None)
        request.session.pop(SWITCH_ACCOUNTS_HASHES_KEY, None)
        return super().post(request, *args, **kwargs)


def _normalized_account_ids(request):
    account_ids = request.session.get(SWITCH_ACCOUNTS_SESSION_KEY, [])
    current_id = str(request.user.pk)
    hashes = request.session.get(SWITCH_ACCOUNTS_HASHES_KEY, {})
    # A legacy list of IDs alone is not proof of a still-valid login.
    users = get_user_model().objects.filter(pk__in=account_ids, is_active=True)
    valid_ids = {
        str(user.pk) for user in users
        if isinstance(hashes.get(str(user.pk)), str)
        and constant_time_compare(hashes[str(user.pk)], user.get_session_auth_hash())
    }
    return list(dict.fromkeys([current_id, *(
        str(account_id) for account_id in account_ids if str(account_id) in valid_ids
    )]))


def _save_account_ids(request, account_ids):
    normalized = []
    for account_id in account_ids:
        account_id = str(account_id)
        if account_id not in normalized:
            normalized.append(account_id)

    request.session[SWITCH_ACCOUNTS_SESSION_KEY] = normalized
    hashes = request.session.get(SWITCH_ACCOUNTS_HASHES_KEY, {}).copy()
    hashes[str(request.user.pk)] = request.user.get_session_auth_hash()
    request.session[SWITCH_ACCOUNTS_HASHES_KEY] = {
        key: value for key, value in hashes.items() if key in normalized
    }
    request.session.modified = True
    return normalized


def _login_preserving_switcher(request, user, account_ids, *, authenticated=False):
    backend = settings.AUTHENTICATION_BACKENDS[0]
    hashes = request.session.get(SWITCH_ACCOUNTS_HASHES_KEY, {}).copy()
    if not authenticated and user.pk != request.user.pk:
        stored_hash = hashes.get(str(user.pk))
        if not isinstance(stored_hash, str) or not constant_time_compare(stored_hash, user.get_session_auth_hash()):
            raise PermissionDenied('Dodaj konto ponownie, podając aktualne hasło.')
    if request.user.is_authenticated:
        hashes[str(request.user.pk)] = request.user.get_session_auth_hash()
    if request.user.is_authenticated and request.user.pk != user.pk:
        mark_user_inactive(request.user)
    auth_login(request, user, backend=backend)
    # auth_login flushes the session when changing users.
    request.session[SWITCH_ACCOUNTS_HASHES_KEY] = hashes
    mark_user_seen(user, force=True)
    _save_account_ids(request, [user.pk, *account_ids])


def _switch_account_context(request):
    user_model = get_user_model()
    account_ids = _normalized_account_ids(request)
    users = user_model.objects.filter(pk__in=account_ids)
    users_by_id = {str(user.pk): user for user in users}

    switch_accounts = []
    for account_id in account_ids:
        if account_id not in users_by_id:
            continue

        switch_accounts.append({
            'user': users_by_id[account_id],
            'is_current': account_id == str(request.user.pk),
            'avatar': _account_avatar(users_by_id[account_id]),
        })

    return switch_accounts


def _presence_status_options(form):
    selected_value = form['presence_status'].value()
    choice_values = [value for value, _label in form.fields['presence_status'].choices]

    if selected_value not in choice_values and choice_values:
        selected_value = choice_values[0]

    return [
        {
            'value': value,
            'label': label,
            'is_selected': value == selected_value,
        }
        for value, label in form.fields['presence_status'].choices
    ]


def _save_user_form(form):
    # Validation and INSERT/UPDATE can race with another account request.
    try:
        with transaction.atomic():
            form.save()
    except IntegrityError as error:
        constraint = getattr(getattr(error.__cause__, 'diag', None), 'constraint_name', '')
        if constraint not in {'accounts_user_email_key', 'accounts_user_email_ci_unique'}:
            raise
        form.add_error('email', 'Ten adres email jest już używany.')
        return False
    return True


@never_cache
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid() and _save_user_form(form):
            messages.success(request, 'Konto zostało utworzone pomyślnie! Możesz się teraz zalogować.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form},
                  status=400 if getattr(request, '_react_api', False) and form.errors else 200)


@login_required
@never_cache
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid() and _save_user_form(form):
            messages.success(request, 'Profil został zaktualizowany.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)

    _save_account_ids(request, _normalized_account_ids(request))
    return render(request, 'accounts/profile.html', {
        'form': form,
        'current_account_avatar': _account_avatar(request.user),
        'presence_status_options': _presence_status_options(form),
        'switch_accounts': _switch_account_context(request),
    }, status=400 if getattr(request, '_react_api', False) and form.errors else 200)


@login_required
@require_POST
def update_presence_status(request):
    user_model = get_user_model()
    presence_status = request.POST.get('presence_status', '')
    valid_presence_statuses = {
        value
        for value, _label in user_model.PresenceStatus.choices
    }

    if presence_status not in valid_presence_statuses:
        if getattr(request, '_react_api', False):
            return api_error('Nieprawidłowy status użytkownika.', 400)
        messages.error(request, 'Nieprawidłowy status użytkownika.')
        return redirect('profile')

    if presence_status == user_model.PresenceStatus.ACTIVE:
        mark_user_seen(request.user, force=True)
    elif presence_status == user_model.PresenceStatus.INACTIVE:
        mark_user_inactive(request.user, force=True)
    else:
        request.user.presence_status = presence_status
        request.user.save(update_fields=['presence_status'])

    messages.success(request, 'Status został zaktualizowany.')
    return redirect('profile')


@login_required
@never_cache
def add_account(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            account_ids = _normalized_account_ids(request)
            _login_preserving_switcher(request, user, account_ids, authenticated=True)
            messages.success(request, f'Konto {user.email} zostało dodane.')
            return redirect('profile')
    else:
        form = AuthenticationForm(request)

    return render(request, 'accounts/add_account.html', {'form': form},
                  status=400 if getattr(request, '_react_api', False) and form.errors else 200)


@login_required
@require_POST
def switch_account(request):
    account_ids = _normalized_account_ids(request)
    target_id = str(request.POST.get('user_id', ''))

    if target_id not in account_ids:
        _save_account_ids(request, account_ids)
        if getattr(request, '_react_api', False):
            return api_error('Dodaj konto ponownie, podając aktualne hasło.', 403)
        messages.error(request, 'Dodaj konto ponownie, podając aktualne hasło.')
        return redirect('profile')

    user = get_object_or_404(get_user_model(), pk=target_id, is_active=True)
    _login_preserving_switcher(request, user, account_ids)
    messages.success(request, f'Przełączono na konto {user.email}.')
    return redirect('profile')


@login_required
@require_POST
def remove_account(request):
    account_ids = _normalized_account_ids(request)
    target_id = str(request.POST.get('user_id', ''))

    if target_id not in account_ids:
        if getattr(request, '_react_api', False):
            return api_error('To konto nie jest dodane do przełącznika.', 400)
        messages.error(request, 'To konto nie jest dodane do przełącznika.')
        return redirect('profile')

    remaining_ids = [account_id for account_id in account_ids if account_id != target_id]
    if not remaining_ids:
        if getattr(request, '_react_api', False):
            return api_error('Nie można usunąć jedynego aktywnego konta z przełącznika.', 400)
        messages.error(request, 'Nie można usunąć jedynego aktywnego konta z przełącznika.')
        _save_account_ids(request, account_ids)
        return redirect('profile')

    if target_id == str(request.user.pk):
        user = get_object_or_404(get_user_model(), pk=remaining_ids[0], is_active=True)
        _login_preserving_switcher(request, user, remaining_ids)
        messages.success(request, f'Usunięto konto i przełączono na {user.email}.')
    else:
        _save_account_ids(request, remaining_ids)
        messages.success(request, 'Konto zostało usunięte z przełącznika.')

    return redirect('profile')


@login_required
@require_POST
def presence_ping(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}

    is_active = payload.get('active', True) is not False
    if is_active:
        presence_status = mark_user_seen(request.user, force=True)
    else:
        presence_status = mark_user_inactive(request.user)

    return JsonResponse({
        'status': 'success',
        'presence_status': presence_status,
        'presence_status_display': request.user.get_presence_status_display(),
    })
