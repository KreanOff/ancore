"""Dashboard access drafts and legacy immediate sharing operations."""
import json

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, Http404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods
from types import SimpleNamespace

from accounts.avatar import account_avatar
from core.frontend import form_payload
from workplaces.models import Workplace
from workplaces.services import workplace_people
from workplaces.team_views import TeamRoleSelect
from .models import Dashboard, DashboardMembership
from .pulpits import app_url, can_manage_dashboard


class ShareForm(forms.Form):
    email = forms.EmailField(label='Osoba lub adres e-mail konta Ancore')
    role = forms.ChoiceField(label='Rola', choices=DashboardMembership.Role.choices, initial='member',
                             widget=TeamRoleSelect(attrs={'class': 'form-select'}),
                             help_text='Administrator zarządza ustawieniami i dostępem, członek edytuje gadżety i układ, a obserwator tylko przegląda pulpit.')

    def __init__(self, *args, dashboard, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.dashboard = dashboard
        if actor.pk != dashboard.created_by_id:
            self.fields['role'].choices = [('member', 'Członek'), ('observer', 'Obserwator')]

    def clean_email(self):
        if self.dashboard.visibility == Dashboard.Visibility.WORKSPACE:
            raise forms.ValidationError('Pulpit jest dostępny dla całego Workspace. Najpierw zapisz widoczność „Prywatny — wybrane osoby”.')
        people = workplace_people(self.dashboard.workplace).filter(email__iexact=self.cleaned_data['email'])
        if people.count() != 1:
            raise forms.ValidationError('Wybierz aktywnego członka bieżącego Workspace.')
        self.recipient = people.get()
        if self.recipient.pk == self.dashboard.created_by_id or (self.dashboard.visibility == Dashboard.Visibility.SELECTED and self.dashboard.shared_with.filter(pk=self.recipient.pk).exists()):
            raise forms.ValidationError('Ta osoba ma już dostęp do pulpitu.')
        return self.recipient.email


def payload(request, dashboard):
    creator = dashboard.created_by_id == request.user.pk
    manager = can_manage_dashboard(request, dashboard)
    inherited = dashboard.visibility == Dashboard.Visibility.WORKSPACE
    people = workplace_people(dashboard.workplace)
    if inherited:
        recipients = [SimpleNamespace(user=person, user_id=person.pk, role='observer', created_at=None)
                      for person in people.exclude(pk=dashboard.created_by_id)]
    elif dashboard.visibility == Dashboard.Visibility.SELECTED:
        recipients = dashboard.memberships.filter(user__in=people).exclude(user_id=dashboard.created_by_id).select_related('user').order_by('role', 'user__email')
    else:
        recipients = []
    members = [{
        'id': member.user_id, 'user_id': member.user_id,
        'name': member.user.get_full_name() or member.user.email or member.user.username,
        'email': member.user.email, 'avatar': account_avatar(member.user),
        'role': member.role, 'role_label': 'Dostęp z Workspace' if inherited else member.get_role_display(),
        'created_at': member.created_at.isoformat() if member.created_at else None,
        'can_change': manager and not inherited and (creator or member.role != 'admin'),
    } for member in recipients]
    person = dashboard.created_by
    members.insert(0, {
        'id': 'owner', 'user_id': person.pk, 'name': person.get_full_name() or person.email or person.username,
        'email': person.email, 'avatar': account_avatar(person), 'role': 'owner', 'role_label': 'Właściciel',
        'created_at': dashboard.created_at.isoformat(), 'can_change': False,
    })
    return {'name': dashboard.name, 'can_manage': manager and not inherited, 'is_owner': creator,
            'can_change_visibility': creator and manager, 'members': members,
            'share_form': form_payload(ShareForm(dashboard=dashboard, actor=request.user)),
            'visibility': dashboard.visibility, 'revision': dashboard.revision}


def team_url(request, dashboard):
    return app_url(request, f'{dashboard.slug}/team/')


def apply_access_draft(request, dashboard):
    """Validate a complete access draft while the workspace/dashboard locks are held."""
    try:
        revision = int(request.POST.get('revision', ''))
        if revision < 0:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Nieprawidłowa wersja ustawień dostępu.'}, status=400)
    if revision != dashboard.revision:
        return JsonResponse({'error': 'Pulpit zmieniono w innym oknie. Odśwież dane przed zapisaniem dostępu.'}, status=409)
    visibility = request.POST.get('visibility')
    if visibility not in {Dashboard.Visibility.PRIVATE, Dashboard.Visibility.WORKSPACE}:
        return JsonResponse({'error': 'Wybierz prawidłową widoczność pulpitu.'}, status=400)
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
                    or user_id == dashboard.created_by_id or user_id in desired
                    or role not in DashboardMembership.Role.values):
                raise ValueError
            desired[user_id] = role
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Nieprawidłowa lista osób lub ról. Właściciel pulpitu pozostaje bez zmian.'}, status=400)

    current = {member.user_id: member for member in dashboard.memberships.all()}
    admins = {user_id for user_id, member in current.items() if member.role == DashboardMembership.Role.ADMIN}
    active_ids = set(workplace_people(dashboard.workplace).filter(pk__in=set(desired) | admins).values_list('pk', flat=True))
    if not set(desired).issubset(active_ids):
        return JsonResponse({'error': 'Wybierz wyłącznie aktywnych członków bieżącego Workspace.'}, status=400)
    preserved = set()
    if dashboard.created_by_id != request.user.pk:
        if visibility != Dashboard.Visibility.PRIVATE:
            raise PermissionDenied
        if any(desired.get(user_id) != DashboardMembership.Role.ADMIN for user_id in admins & active_ids):
            raise PermissionDenied
        if any(role == DashboardMembership.Role.ADMIN and user_id not in admins for user_id, role in desired.items()):
            raise PermissionDenied
        # The client cannot see inactive grants. Omission must not let an admin
        # remove a protected administrator that was outside its active snapshot.
        preserved = admins - active_ids

    if visibility == Dashboard.Visibility.WORKSPACE:
        dashboard.shared_with.clear()
        dashboard.visibility = Dashboard.Visibility.WORKSPACE
    else:
        dashboard.memberships.exclude(user_id__in=set(desired) | preserved).delete()
        for user_id, role in desired.items():
            member = current.get(user_id)
            if member is None:
                dashboard.memberships.create(user_id=user_id, role=role)
            elif member.role != role:
                member.role = role
                member.save(update_fields=['role'])
        dashboard.visibility = Dashboard.Visibility.SELECTED if desired else Dashboard.Visibility.PRIVATE
    return None


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def team(request, pk):
    from .pulpit_views import get_dashboard
    dashboard = get_dashboard(request, pk, manage=request.method == 'POST')
    if request.method == 'GET':
        return JsonResponse(payload(request, dashboard))
    with transaction.atomic():
        Workplace.objects.select_for_update().get(pk=request.workplace.pk)
        dashboard = get_dashboard(request, pk, manage=True, lock=True)
        action = request.POST.get('action')
        creator = dashboard.created_by_id == request.user.pk
        if action == 'save':
            error = apply_access_draft(request, dashboard)
            if error is not None:
                return error
        elif action == 'visibility':
            if not creator:
                raise PermissionDenied
            visibility = request.POST.get('visibility')
            if visibility not in {Dashboard.Visibility.PRIVATE, Dashboard.Visibility.WORKSPACE}:
                return JsonResponse({'error': 'Wybierz prawidłową widoczność pulpitu.'}, status=400)
            if visibility == Dashboard.Visibility.WORKSPACE:
                dashboard.shared_with.clear()
                dashboard.visibility = Dashboard.Visibility.WORKSPACE
            elif dashboard.visibility == Dashboard.Visibility.SELECTED and dashboard.shared_with.exists():
                dashboard.visibility = Dashboard.Visibility.SELECTED
            else:
                # Grants outside selected visibility are stale, never restore them.
                dashboard.shared_with.clear()
                dashboard.visibility = Dashboard.Visibility.PRIVATE
        elif dashboard.visibility == Dashboard.Visibility.WORKSPACE:
            raise PermissionDenied
        elif action == 'share':
            form = ShareForm(request.POST, dashboard=dashboard, actor=request.user)
            if not form.is_valid():
                return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
            if dashboard.visibility == Dashboard.Visibility.PRIVATE:
                dashboard.shared_with.clear()
            dashboard.memberships.create(user=form.recipient, role=form.cleaned_data['role'])
            dashboard.visibility = Dashboard.Visibility.SELECTED
        elif action in {'remove', 'role'}:
            values = request.POST.getlist('member_ids') if 'member_ids' in request.POST else request.POST.getlist('member_id')
            if not values:
                return JsonResponse({'error': 'Zaznacz co najmniej jedną osobę.'}, status=400)
            try:
                member_ids = {int(value) for value in values}
                if any(not 0 < member_id < 2 ** 63 for member_id in member_ids):
                    raise ValueError
            except (ValueError, TypeError):
                raise Http404
            members = list(dashboard.memberships.filter(user_id__in=member_ids,
                user__in=workplace_people(dashboard.workplace)).exclude(user_id=dashboard.created_by_id))
            if len(members) != len(member_ids):
                raise Http404
            if not creator and any(member.role == 'admin' for member in members):
                raise PermissionDenied
            role = request.POST.get('role')
            if action == 'role' and role not in ({'admin', 'member', 'observer'} if creator else {'member', 'observer'}):
                raise PermissionDenied
            # Validate every selected person before changing any of the grants.
            if action == 'remove':
                dashboard.memberships.filter(pk__in=[member.pk for member in members]).delete()
                if not dashboard.shared_with.exists():
                    dashboard.visibility = Dashboard.Visibility.PRIVATE
            else:
                for member in members:
                    member.role = role
                    member.save(update_fields=['role'])
        else:
            return JsonResponse({'error': 'Nieprawidłowa operacja.'}, status=400)
        dashboard.revision += 1
        dashboard.save(update_fields=['visibility', 'revision', 'updated_at'])
        return JsonResponse({'ok': True, **payload(request, dashboard)})


@login_required
@never_cache
@require_GET
def candidates(request, pk):
    from .pulpit_views import get_dashboard
    dashboard = get_dashboard(request, pk, manage=True)
    draft = request.GET.get('draft') == '1'
    if dashboard.visibility == Dashboard.Visibility.WORKSPACE and not draft:
        raise PermissionDenied
    query = request.GET.get('q', '').strip()
    if len(query) < 2 or len(query) > 254:
        return JsonResponse({'results': [], 'has_more': False})
    people = workplace_people(dashboard.workplace).exclude(email='').exclude(pk=dashboard.created_by_id)
    if dashboard.visibility == Dashboard.Visibility.SELECTED and not draft:
        people = people.exclude(pk__in=dashboard.shared_with.values('pk'))
    for term in query.split():
        people = people.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term)
            | Q(middle_name__icontains=term) | Q(username__icontains=term) | Q(email__icontains=term))
    people = list(people.order_by('first_name', 'last_name', 'email')[:11])
    return JsonResponse({'results': [{'id': person.pk, 'user_id': person.pk,
        'email': person.email, 'name': person.get_full_name() or person.username,
        'avatar': account_avatar(person)} for person in people[:10]], 'has_more': len(people) > 10})
