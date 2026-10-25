"""Explicit account membership, authorized independently of the active Workspace."""
import uuid

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Case, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django import forms
from accounts.avatar import account_avatar
from accounts.models import PUBLIC_USERNAME_RE, normalize_public_username

from .models import Workplace, WorkplaceMembership
from .services import can_manage_team, workplace_role, workplaces_for_user, workplace_management_url


class TeamRoleSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        icon = {'member': 'user-round', 'admin': 'shield-check', 'observer': 'eye'}.get(str(value))
        if icon:
            option['attrs']['data-ancore-option-icon'] = icon
        return option


class AddMemberForm(forms.Form):
    user_id = forms.CharField(
        label='ID konta Ancore', max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'off'}),
        help_text='Wpisz ID Ancore, np. @jan.nowak, lub wybierz konto z podpowiedzi.',
    )
    role = forms.ChoiceField(label='Rola', choices=[('member', 'Członek'), ('admin', 'Administrator'), ('guest', 'Gość — tylko odczyt')], widget=TeamRoleSelect(attrs={'class': 'form-select'}))

    def __init__(self, *args, workplace, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.workplace = workplace
        self.actor_is_owner = workplace.owner_id == actor.pk
        if workplace.owner_id != actor.pk:
            self.fields['role'].choices = [('member', 'Członek'), ('guest', 'Gość — tylko odczyt')]

    def clean_user_id(self):
        identity = self.cleaned_data['user_id'].strip()
        users = get_user_model().objects.filter(is_active=True).exclude(pk=self.workplace.owner_id)
        if identity.isascii() and identity.isdecimal() and len(identity) <= 18:
            users = users.filter(pk=int(identity))
        else:
            username = normalize_public_username(identity)
            if not PUBLIC_USERNAME_RE.fullmatch(username):
                raise forms.ValidationError('Wybierz istniejące, aktywne konto Ancore.')
            users = users.filter(username__iexact=username)
        try:
            person = users.get()
        except (get_user_model().DoesNotExist, get_user_model().MultipleObjectsReturned):
            raise forms.ValidationError('Wybierz istniejące, aktywne konto Ancore.')
        membership = self.workplace.memberships.filter(user=person).first()
        if membership and not self.actor_is_owner and membership.role in {'admin', 'owner'}:
            raise forms.ValidationError('Tylko właściciel może zarządzać dostępem administratora.')
        if membership and membership.is_active:
            raise forms.ValidationError('Ta osoba jest już członkiem Workspace.')
        return person


@login_required
@require_GET
@never_cache
def member_candidates(request, workplace_id):
    """Account directory suggestions for managers of the explicitly chosen team."""
    workplace = get_object_or_404(workplaces_for_user(request.user), pk=workplace_id)
    if not can_manage_team(request.user, workplace):
        raise PermissionDenied
    query = (request.GET.get('q') or '').strip()
    if len(query) < 2 or len(query) > 254:
        return JsonResponse({'results': [], 'has_more': False})
    users = (get_user_model().objects.filter(is_active=True).exclude(email='')
             .exclude(pk=workplace.owner_id)
             .exclude(pk__in=workplace.memberships.filter(is_active=True).values('user_id')))
    if workplace.owner_id != request.user.pk:
        users = users.exclude(pk__in=workplace.memberships.filter(role__in=['admin', 'owner']).values('user_id'))
    for term in query.split():
        users = users.filter(
            Q(first_name__icontains=term) | Q(middle_name__icontains=term)
            | Q(last_name__icontains=term) | Q(username__icontains=term)
            | Q(email__icontains=term)
        )
    matches = list(users.order_by(
        Case(When(email__iexact=query, then=Value(0)), default=Value(1)),
        'first_name', 'middle_name', 'last_name', 'email',
    )[:11])
    results = [{
        'id': str(user.pk), 'email': user.email,
        'name': user.get_full_name() or user.username,
        **({'avatar': account_avatar(user)} if getattr(request, '_react_api', False) else
           {'html': render_to_string('workplaces/includes/invitation_person.html', {'person': user})}),
    } for user in matches[:10]]
    return JsonResponse({'results': results, 'has_more': len(matches) > 10})


@login_required
@require_http_methods(['GET', 'POST'])
def team(request, workplace_id):
    workplace = get_object_or_404(workplaces_for_user(request.user), pk=workplace_id)
    if request.method == 'GET':
        return redirect(workplace_management_url(workplace, request.GET.get('view')))
    with transaction.atomic():
        workplace = get_object_or_404(Workplace.objects.select_for_update(), pk=workplace_id)
        if not can_manage_team(request.user, workplace):
            raise PermissionDenied
        form = AddMemberForm(request.POST, workplace=workplace, actor=request.user)
        if form.is_valid():
            # The manager chooses an account identity; an email string never grants access.
            person = get_object_or_404(get_user_model().objects.select_for_update(), pk=form.cleaned_data['user_id'].pk, is_active=True)
            membership, created = WorkplaceMembership.objects.get_or_create(
                workplace=workplace, user=person, defaults={'role': form.cleaned_data['role']},
            )
            if not created:
                membership.role, membership.is_active = form.cleaned_data['role'], True
                membership.save(update_fields=['role', 'is_active'])
            messages.success(request, 'Osoba została dodana do Workspace.')
            return redirect(workplace_management_url(workplace))
    from .views import render_workplaces
    return render_workplaces(request, team_workplace=workplace, add_form=form)


def team_context(request, workplace, add_form=None):
    """Read one accessible team's details for the shared management screen."""
    members = list(workplace.memberships.filter(is_active=True).select_related('user').order_by('role', 'user__email'))
    members.sort(key=lambda member: (member.user_id != workplace.owner_id, member.role != 'admin', member.user.email))
    role = workplace_role(request.user, workplace)
    from .invitations import InviteLinkForm
    from django.utils import timezone
    for member in members:
        member.can_change = member.user_id != workplace.owner_id and (
            role == 'owner' or (role == 'admin' and member.role in {'member', 'guest'})
        )
    return {
        'team_workplace': workplace, 'members': members,
        'add_form': add_form if add_form is not None else AddMemberForm(workplace=workplace, actor=request.user),
        'can_manage_team': role in {'owner', 'admin'}, 'is_team_owner': role == 'owner',
        'link_form': InviteLinkForm() if role in {'owner', 'admin'} else None,
        'invite_links': workplace.invite_links.filter(revoked_at__isnull=True, expires_at__gt=timezone.now()).order_by('-pk') if role in {'owner', 'admin'} else [],
    }


def _invalidate_office_sessions(workplace):
    # A coauthor's callback can persist changes made by another participant.
    from documents.models import Document, WorkspaceDocument
    for model in (Document, WorkspaceDocument):
        model.objects.filter(owner=workplace.owner, workplace=workplace).update(office_key=uuid.uuid4())


@login_required
@require_POST
def member_update(request, workplace_id, member_id):
    with transaction.atomic():
        workplace = get_object_or_404(Workplace.objects.select_for_update(), pk=workplace_id)
        role = workplace_role(request.user, workplace)
        member = get_object_or_404(WorkplaceMembership, pk=member_id, workplace=workplace)
        if member.user_id == workplace.owner_id or role not in {'owner', 'admin'} or (role == 'admin' and member.role not in {'member', 'guest'}):
            raise PermissionDenied
        action = request.POST.get('action')
        if action == 'remove':
            member.delete()
            # End existing shared editor sessions too: a coauthor's old callback
            # URL could otherwise keep a removed user's editing session alive.
            _invalidate_office_sessions(workplace)
            messages.success(request, 'Dostęp odebrany. Dane zespołu pozostały w Workspace.')
        elif action == 'role' and role == 'owner' and request.POST.get('role') in {'admin', 'member', 'guest'}:
            new_role = request.POST['role']
            loses_write_access = (
                member.is_active and member.role != WorkplaceMembership.Role.GUEST
                and new_role == WorkplaceMembership.Role.GUEST
            )
            member.role = new_role
            member.save(update_fields=['role'])
            if loses_write_access:
                _invalidate_office_sessions(workplace)
            messages.success(request, 'Rola zmieniona.')
        else:
            raise PermissionDenied
    return redirect(workplace_management_url(workplace))
