"""Space sharing using the same member table and role controls as tasks."""
from types import SimpleNamespace

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_http_methods

from accounts.avatar import account_avatar
from workplaces.models import Workplace
from workplaces.services import workplace_people
from workplaces.team_views import InvitationForm
from .models import Space, SpaceMembership
from .services import manage_space


class ShareForm(InvitationForm):
    def __init__(self, *args, space, actor, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.space = space
        self.fields['role'].choices = list(SpaceMembership._meta.get_field('role').choices)
        self.fields['role'].help_text = 'Obserwator może tylko przeglądać przestrzeń i jej zawartość.'
        if actor.pk != space.private_owner_id:
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
    manager = manage_space(request, space)
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
        members = [SimpleNamespace(user=person, user_id=person.pk, pk=person.pk, role='', can_change=False,
                   get_role_display='Właściciel' if person.pk == space.user_id else 'Dostęp z Workspace',
                   created_at=space.created_at if person.pk == space.user_id else None) for person in people]
    return {'members': members, 'can_manage_team': manager and space.visibility == 'private',
            'is_team_owner': owner, 'share_form': ShareForm(space=space, actor=request.user)}


def payload(request, space):
    from .frontend import task_members_payload
    return task_members_payload(team_context(request, space))


@login_required
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
        if not manage_space(request, space) or space.visibility != 'private':
            raise PermissionDenied
        action = request.POST.get('action')
        if action == 'share':
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
@require_GET
def candidates(request, pk):
    from .views import space_object
    space = space_object(request, pk)
    if not manage_space(request, space) or space.visibility != 'private':
        raise PermissionDenied
    query = request.GET.get('q', '').strip()
    if len(query) < 2 or len(query) > 254:
        return JsonResponse({'results': [], 'has_more': False})
    people = workplace_people(space.workplace).exclude(email='').exclude(pk=space.private_owner_id).exclude(pk__in=space.memberships.values('user_id'))
    for term in query.split():
        people = people.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term)
            | Q(middle_name__icontains=term) | Q(username__icontains=term) | Q(email__icontains=term))
    people = list(people.order_by('first_name', 'last_name', 'email')[:11])
    return JsonResponse({'results': [{'email': person.email, 'name': person.get_full_name() or person.username,
        'avatar': account_avatar(person)} for person in people[:10]], 'has_more': len(people) > 10})
