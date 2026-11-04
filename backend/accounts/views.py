import json

from django.conf import settings
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.cache import never_cache
from core.api import api_error
from core.frontend import render
from workplaces.forms import RegistrationWorkspaceForm
from workplaces.models import create_workplace_for_user
from workplaces.services import default_workplace_for_user, workplaces_for_user, set_active_workplace, enable_workspace_url_scope, scoped_workplace_app_path
from .avatar import account_avatar as _account_avatar
from .forms import UserBannerForm, UserProfileForm, UserRegistrationForm
from .presence import mark_user_inactive, mark_user_seen


class AccountLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def render_to_response(self, context, **response_kwargs):
        if getattr(self.request, '_react_api', False) and context['form'].errors:
            response_kwargs['status'] = 400
        return render(self.request, self.template_name, context, **response_kwargs)

    def get_redirect_url(self):
        # Every login opens the same landing page, including requests with next.
        return ''

    def get_success_url(self):
        from workplaces.invitations import pending_join_url
        invitation = pending_join_url(self.request)
        if invitation:
            return invitation
        default_workplace = default_workplace_for_user(self.request.user)
        if default_workplace:
            set_active_workplace(self.request, default_workplace)
            enable_workspace_url_scope(self.request)
            return scoped_workplace_app_path(default_workplace, 'for-you')
        if not workplaces_for_user(self.request.user).exists():
            return reverse('register_workspace')
        return super().get_success_url()


class AccountLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            mark_user_inactive(request.user)
        return super().post(request, *args, **kwargs)


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
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                if _save_user_form(form):
                    from workplaces.invitations import pending_join_url
                    invitation = pending_join_url(request)
                    auth_login(request, form.instance, backend=settings.AUTHENTICATION_BACKENDS[0])
                    if invitation:
                        request.session['workspace_join_url'] = invitation
                    return redirect(invitation or reverse('register_workspace'))
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form},
                  status=400 if getattr(request, '_react_api', False) and form.errors else 200)


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def register_workspace(request):
    user_workplaces = workplaces_for_user(request.user)
    workplace = user_workplaces.first()
    create_another = request.POST.get('create_another') == '1'
    if request.method == 'POST' and workplace and not create_another:
        return redirect(scoped_workplace_app_path(workplace, 'for-you'))
    form = RegistrationWorkspaceForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            workplace = workplaces_for_user(request.user).first()
            if workplace is None or create_another:
                workplace = create_workplace_for_user(request.user, form.cleaned_data['name'])
        set_active_workplace(request, workplace)
        enable_workspace_url_scope(request)
        messages.success(request, 'Workspace jest gotowy.')
        return redirect(scoped_workplace_app_path(workplace, 'for-you'))

    return render(request, 'accounts/register_workspace.html', {
        'form': form,
        'workspaces': user_workplaces,
    }, status=400 if getattr(request, '_react_api', False) and form.errors else 200)


@never_cache
@login_required
@require_http_methods(['GET'])
def select_workspace(request):
    return render(request, 'accounts/select_workspace.html', {
        'workspaces': workplaces_for_user(request.user),
    })


def _profile_context(request, *, form=None, banner_form=None):
    if form is None:
        form = UserProfileForm(instance=request.user)
    return {
        'form': form,
        'banner_form': banner_form if banner_form is not None else UserBannerForm(instance=request.user),
        'current_account_avatar': _account_avatar(request.user),
        'presence_status_options': _presence_status_options(form),
    }


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

    return render(request, 'accounts/profile.html', _profile_context(request, form=form),
                  status=400 if getattr(request, '_react_api', False) and form.errors else 200)


@login_required
@never_cache
@require_POST
def update_profile_banner(request):
    form = UserBannerForm(request.POST, request.FILES, instance=request.user)
    if form.is_valid():
        try:
            form.save()
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Baner profilu został zaktualizowany.')
            return redirect('profile')
    return render(request, 'accounts/profile.html', _profile_context(request, banner_form=form), status=400)


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
        # An explicit selection clears a manual status; heartbeat preserves it.
        request.user.presence_status = user_model.PresenceStatus.ACTIVE
        mark_user_seen(request.user, force=True)
    elif presence_status == user_model.PresenceStatus.INACTIVE:
        mark_user_inactive(request.user, force=True)
    else:
        request.user.presence_status = presence_status
        request.user.save(update_fields=['presence_status'])

    messages.success(request, 'Status został zaktualizowany.')
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
