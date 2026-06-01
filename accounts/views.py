from django.conf import settings
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import UserProfileForm, UserRegistrationForm

SWITCH_ACCOUNTS_SESSION_KEY = 'switch_account_user_ids'
AVATAR_COLOR_CLASSES = [
    'profile-avatar--blue',
    'profile-avatar--teal',
    'profile-avatar--green',
    'profile-avatar--violet',
    'profile-avatar--rose',
    'profile-avatar--amber',
]


class AccountLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        request.session.pop(SWITCH_ACCOUNTS_SESSION_KEY, None)
        return super().post(request, *args, **kwargs)


def _normalized_account_ids(request):
    account_ids = request.session.get(SWITCH_ACCOUNTS_SESSION_KEY, [])
    current_id = str(request.user.pk)
    normalized = []

    for account_id in [current_id, *account_ids]:
        account_id = str(account_id)
        if account_id not in normalized:
            normalized.append(account_id)

    return normalized


def _save_account_ids(request, account_ids):
    normalized = []
    for account_id in account_ids:
        account_id = str(account_id)
        if account_id not in normalized:
            normalized.append(account_id)

    request.session[SWITCH_ACCOUNTS_SESSION_KEY] = normalized
    request.session.modified = True
    return normalized


def _login_preserving_switcher(request, user, account_ids):
    backend = settings.AUTHENTICATION_BACKENDS[0]
    auth_login(request, user, backend=backend)
    _save_account_ids(request, [user.pk, *account_ids])


def _account_avatar(user, color_index=None):
    first_initial = (user.first_name or '').strip()[:1]
    last_initial = (user.last_name or '').strip()[:1]
    initials = f'{first_initial}{last_initial}'.upper()

    if not initials:
        initials = (user.email or user.username or '?').strip()[:1].upper()

    if color_index is None:
        color_basis = str(user.pk or user.email or user.username or initials)
        color_index = sum(ord(char) for char in color_basis)

    return {
        'initials': initials,
        'color_class': AVATAR_COLOR_CLASSES[color_index % len(AVATAR_COLOR_CLASSES)],
    }


def _switch_account_context(request):
    user_model = get_user_model()
    account_ids = _normalized_account_ids(request)
    users = user_model.objects.filter(pk__in=account_ids)
    users_by_id = {str(user.pk): user for user in users}

    switch_accounts = []
    for color_index, account_id in enumerate(account_ids):
        if account_id not in users_by_id:
            continue

        switch_accounts.append({
            'user': users_by_id[account_id],
            'is_current': account_id == str(request.user.pk),
            'avatar': _account_avatar(users_by_id[account_id], color_index),
        })

    return switch_accounts


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Konto zostało utworzone pomyślnie! Możesz się teraz zalogować.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil został zaktualizowany.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)

    _save_account_ids(request, _normalized_account_ids(request))
    return render(request, 'accounts/profile.html', {
        'form': form,
        'current_account_avatar': _account_avatar(request.user, 0),
        'switch_accounts': _switch_account_context(request),
    })


@login_required
def add_account(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            account_ids = _normalized_account_ids(request)
            _login_preserving_switcher(request, user, account_ids)
            messages.success(request, f'Konto {user.email} zostało dodane.')
            return redirect('profile')
    else:
        form = AuthenticationForm(request)

    return render(request, 'accounts/add_account.html', {'form': form})


@login_required
@require_POST
def switch_account(request):
    account_ids = _normalized_account_ids(request)
    target_id = str(request.POST.get('user_id', ''))

    if target_id not in account_ids:
        messages.error(request, 'To konto nie jest dodane do przełącznika.')
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
        messages.error(request, 'To konto nie jest dodane do przełącznika.')
        return redirect('profile')

    remaining_ids = [account_id for account_id in account_ids if account_id != target_id]
    if not remaining_ids:
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
