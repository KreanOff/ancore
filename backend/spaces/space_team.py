"""Space access drafts and compatible immediate member operations."""
import hashlib
import json
from types import SimpleNamespace

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from accounts.avatar import account_avatar
from workplaces.models import Workplace
from workplaces.policy import read_only
from workplaces.services import workplace_people
from workplaces.team_views import TeamRoleSelect
from .models import Space, SpaceMembership
from .services import manage_configuration, manage_space


class ShareForm(forms.Form):
    email = forms.EmailField(label='Konto Ancore', widget=forms.TextInput(attrs={
        'class': 'form-input', 'autocomplete': 'off', 'spellcheck': 'false',
        'placeholder': 'Wpisz imię, nazwisko, ID Ancore lub e-mail',
        'data-team-invite-search': '', 'role': 'combobox', 'aria-autocomplete': 'list',
        'aria-expanded': 'false', 'aria-controls': 'team-invite-results',
        'aria-describedby': 'team-invite-search-status',
    }))
    role = forms.ChoiceField(label='Rola', choices=SpaceMembership._meta.get_field('role').choices,
                             widget=TeamRoleSelect(attrs={'class': 'form-select'}))

    def __init__(self, *args, space, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.space = space
        self.fields['role'].choices = list(SpaceMembership._meta.get_field('role').choices)
        self.fields['role'].help_text = 'Obserwator może tylko przeglądać przestrzeń i jej zawartość.'
        if space.visibility == 'private' and actor.pk != space.private_owner_id:
            self.fields['role'].choices = [('member', 'Członek'), ('observer', 'Obserwator')]

    def clean_email(self):
        if self.space.visibility != 'private':
            raise forms.ValidationError('Przestrzeń publiczna jest dostępna dla całego Workspace. Najpierw zapisz widoczność „Prywatna”.')
        people = workplace_people(self.space.workplace).filter(email__iexact=self.cleaned_data['email'])
        if people.count() != 1:
            raise forms.ValidationError('Wybierz aktywnego członka bieżącego Workspace.')
        self.recipient = people.get()
        if self.recipient.pk == self.space.private_owner_id or self.space.memberships.filter(user=self.recipient).exists():
            raise forms.ValidationError('Ta osoba ma już dostęp do przestrzeni.')
        return self.recipient.email


def team_context(request, space):
    manager = manage_space(request, space) and not read_only(request)
    owner = manager and request.user.pk == space.private_owner_id
    people = workplace_people(space.workplace)
    if space.visibility == 'private':
        members = list(space.memberships.filter(user__in=people).exclude(user_id=space.private_owner_id)
                       .select_related('user').order_by('role', 'user__email'))
        for member in members:
            member.can_change = manager and (owner or member.role in {'member', 'observer'})
            member.created_at = None
        if space.private_owner_id:
            members.insert(0, SimpleNamespace(user=space.private_owner, user_id=space.private_owner_id,
                pk='owner', role='owner', get_role_display='Właściciel', created_at=space.created_at, can_change=False))
    else:
        members = [SimpleNamespace(user=person, user_id=person.pk,
                   pk='owner' if person.pk == space.user_id else person.pk,
                   role='owner' if person.pk == space.user_id else 'member', can_change=False,
                   get_role_display='Właściciel' if person.pk == space.user_id else 'Dostęp z Workspace',
                   created_at=space.created_at if person.pk == space.user_id else None) for person in people]
        members.sort(key=lambda member: member.role != 'owner')
    return {'members': members, 'can_manage_team': manager and space.visibility == 'private',
            'is_team_owner': owner, 'share_form': ShareForm(space=space, actor=request.user)}


def access_revision(space):
    """Include legacy edits and membership changes without adding a second counter."""
    values = [space.visibility, space.private_owner_id, space.responsible_user_id,
              list(space.memberships.order_by('pk').values_list('pk', 'user_id', 'role'))]
    return hashlib.sha256(json.dumps(values, separators=(',', ':')).encode()).hexdigest()


def payload(request, space):
    from .frontend import task_members_payload
    result = task_members_payload(team_context(request, space))
    manager = manage_space(request, space) and not read_only(request)
    result.update(name=space.name, visibility=space.visibility, revision=access_revision(space),
                  can_manage=manager,
                  can_configure=manage_configuration(request, space) and not read_only(request),
                  can_change_visibility=manager and (space.visibility == 'public' or result['is_owner']))
    # A public space has no private owner. Its manager becomes the owner when
    # making it private, exactly as in the existing settings form.
    if space.visibility == 'public' and manager:
        person = request.user
        result['private_owner'] = {
            'id': 'owner', 'user_id': person.pk,
            'name': person.get_full_name() or person.email or person.username,
            'email': person.email, 'avatar': account_avatar(person),
            'role': 'owner', 'role_label': 'Właściciel',
            'created_at': space.created_at, 'can_change': False,
        }
    return result


def apply_access_draft(request, space):
    """Validate the whole draft before writing under the Workspace/Space locks."""
    revision = request.POST.get('revision', '')
    if len(revision) != 64 or any(character not in '0123456789abcdef' for character in revision):
        return JsonResponse({'error': 'Nieprawidłowa wersja ustawień dostępu.'}, status=400)
    if revision != access_revision(space):
        return JsonResponse({'error': 'Przestrzeń zmieniono w innym oknie. Odśwież dane przed zapisaniem dostępu.'}, status=409)
    visibility = request.POST.get('visibility')
    if visibility not in {'private', 'public'}:
        return JsonResponse({'error': 'Wybierz prawidłową widoczność przestrzeni.'}, status=400)
    owner_id = space.private_owner_id if space.visibility == 'private' else request.user.pk
    if space.visibility == 'private' and request.user.pk != owner_id and visibility != 'private':
        raise PermissionDenied
    try:
        rows = json.loads(request.POST.get('members', ''))
        if not isinstance(rows, list):
            raise ValueError
        desired = {}
        for row in rows:
            if not isinstance(row, dict) or set(row) != {'user_id', 'role'}:
                raise ValueError
            user_id, role = row['user_id'], row['role']
            if (type(user_id) is not int or not 0 < user_id < 2 ** 63
                    or user_id == owner_id or user_id in desired
                    or role not in {'admin', 'member', 'observer'}):
                raise ValueError
            desired[user_id] = role
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Nieprawidłowa lista osób lub ról. Właściciel przestrzeni pozostaje bez zmian.'}, status=400)
    if visibility == 'public' and desired:
        return JsonResponse({'error': 'Przestrzeń publiczna korzysta z dostępu całego Workspace.'}, status=400)

    current = {member.user_id: member for member in space.memberships.all()}
    admins = {user_id for user_id, member in current.items() if member.role == 'admin' and user_id != owner_id}
    active_ids = set(workplace_people(space.workplace).filter(pk__in=set(desired) | admins).values_list('pk', flat=True))
    if not set(desired).issubset(active_ids):
        return JsonResponse({'error': 'Wybierz wyłącznie aktywnych członków bieżącego Workspace.'}, status=400)
    preserved = {owner_id}
    if space.visibility == 'private' and request.user.pk != owner_id:
        if any(desired.get(user_id) != 'admin' for user_id in admins & active_ids):
            raise PermissionDenied
        if any(role == 'admin' and user_id not in admins for user_id, role in desired.items()):
            raise PermissionDenied
        # Hidden, inactive administrator grants are protected from an admin too.
        preserved |= admins - active_ids

    previous_visibility = space.visibility
    if visibility == 'public':
        # Save inheritance first so removing direct grants does not revoke
        # independent private task grants that still have their parent access.
        space.visibility = 'public'
        space.private_owner = None
        space.save(update_fields=['visibility', 'private_owner'])
        space.memberships.all().delete()
    else:
        if previous_visibility == 'public':
            space.visibility = 'private'
            space.private_owner = request.user
            space.save(update_fields=['visibility', 'private_owner'])
        # Only the explicitly selected people retain grants. Deleting omitted
        # memberships after privatization also invokes the existing task cleanup,
        # without briefly revoking private tasks from people in this draft.
        space.memberships.exclude(user_id__in=set(desired) | preserved).delete()
        for user_id, role in desired.items():
            member = current.get(user_id)
            if member is None:
                space.memberships.create(user_id=user_id, role=role)
            elif member.role != role:
                member.role = role
                member.save(update_fields=['role'])
    return None


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def team(request, pk):
    from .views import space_object
    from .task_views import posted_id
    space = space_object(request, pk)
    if request.method == 'GET':
        return JsonResponse(payload(request, space))
    with transaction.atomic():
        Workplace.objects.select_for_update().get(pk=request.workplace.pk)
        space_object(request, pk)
        space = Space.objects.select_for_update().get(pk=space.pk)
        if not manage_space(request, space) or read_only(request):
            raise PermissionDenied
        action = request.POST.get('action')
        if action == 'save':
            error = apply_access_draft(request, space)
            if error is not None:
                return error
        elif space.visibility != 'private':
            raise PermissionDenied
        elif action == 'share':
            form = ShareForm(request.POST, space=space, actor=request.user)
            if not form.is_valid():
                return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
            SpaceMembership.objects.create(space=space, user=form.recipient, role=form.cleaned_data['role'])
        elif action in {'role', 'remove'}:
            member = get_object_or_404(space.memberships, pk=posted_id(request, 'member_id'))
            owner = request.user.pk == space.private_owner_id
            if member.user_id == space.private_owner_id or (not owner and member.role == 'admin'):
                raise PermissionDenied
            if action == 'remove':
                member.delete()
            elif request.POST.get('role') in ({'admin', 'member', 'observer'} if owner else {'member', 'observer'}):
                member.role = request.POST['role']
                member.save(update_fields=['role'])
            else:
                raise PermissionDenied
        else:
            return JsonResponse({'error': 'Nieprawidłowa operacja.'}, status=400)
        return JsonResponse({'ok': True, **payload(request, space)})


@login_required
@never_cache
@require_GET
def candidates(request, pk):
    from .views import space_object
    space = space_object(request, pk)
    draft = request.GET.get('draft') == '1'
    if read_only(request) or not manage_space(request, space) or (space.visibility != 'private' and not draft):
        raise PermissionDenied
    query = request.GET.get('q', '').strip()
    if len(query) < 2 or len(query) > 254:
        return JsonResponse({'results': [], 'has_more': False})
    owner_id = space.private_owner_id if space.visibility == 'private' else request.user.pk
    people = workplace_people(space.workplace).exclude(email='').exclude(pk=owner_id)
    if not draft:
        people = people.exclude(pk__in=space.memberships.values('user_id'))
    for term in query.split():
        people = people.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term)
            | Q(middle_name__icontains=term) | Q(username__icontains=term) | Q(email__icontains=term))
    people = list(people.order_by('first_name', 'last_name', 'email')[:11])
    return JsonResponse({'results': [{'id': person.pk, 'user_id': person.pk,
        'email': person.email, 'name': person.get_full_name() or person.username,
        'avatar': account_avatar(person)} for person in people[:10]], 'has_more': len(people) > 10})
