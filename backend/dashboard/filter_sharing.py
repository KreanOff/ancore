"""Saved filter sharing with the shared member table and person picker."""
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
from .models import SavedTaskFilter, SavedTaskFilterMembership
from .filters import filter_url, can_manage_filter


class ShareForm(forms.Form):
    email = forms.EmailField(label='Osoba lub adres e-mail konta Ancore')
    role = forms.ChoiceField(label='Rola', choices=SavedTaskFilterMembership.Role.choices, initial='member',
                             widget=TeamRoleSelect(attrs={'class': 'form-select'}),
                             help_text='Administrator zarządza ustawieniami i dostępem, członek zapisuje warunki wyszukiwania, a obserwator tylko korzysta z filtra.')

    def __init__(self, *args, saved_filter, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved_filter = saved_filter
        if actor.pk != saved_filter.created_by_id:
            self.fields['role'].choices = [('member', 'Członek'), ('observer', 'Obserwator')]

    def clean_email(self):
        if self.saved_filter.visibility == SavedTaskFilter.Visibility.WORKSPACE:
            raise forms.ValidationError('Filtr jest dostępny dla całego Workspace. Najpierw zapisz widoczność „Prywatny — wybrane osoby”.')
        people = workplace_people(self.saved_filter.workplace).filter(email__iexact=self.cleaned_data['email'])
        if people.count() != 1:
            raise forms.ValidationError('Wybierz aktywnego członka bieżącego Workspace.')
        self.recipient = people.get()
        if self.recipient.pk == self.saved_filter.created_by_id or (self.saved_filter.visibility == SavedTaskFilter.Visibility.SELECTED and self.saved_filter.shared_with.filter(pk=self.recipient.pk).exists()):
            raise forms.ValidationError('Ta osoba ma już dostęp do filtra.')
        return self.recipient.email


def payload(request, saved_filter):
    creator = saved_filter.created_by_id == request.user.pk
    manager = can_manage_filter(request, saved_filter)
    inherited = saved_filter.visibility == SavedTaskFilter.Visibility.WORKSPACE
    people = workplace_people(saved_filter.workplace)
    if inherited:
        recipients = [SimpleNamespace(user=person, user_id=person.pk, role='observer', created_at=None)
                      for person in people.exclude(pk=saved_filter.created_by_id)]
    elif saved_filter.visibility == SavedTaskFilter.Visibility.SELECTED:
        recipients = saved_filter.memberships.filter(user__in=people).exclude(user_id=saved_filter.created_by_id).select_related('user').order_by('role', 'user__email')
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
    person = saved_filter.created_by
    members.insert(0, {
        'id': 'owner', 'user_id': person.pk, 'name': person.get_full_name() or person.email or person.username,
        'email': person.email, 'avatar': account_avatar(person), 'role': 'owner', 'role_label': 'Właściciel',
        'created_at': saved_filter.created_at.isoformat(), 'can_change': False,
    })
    return {'name': saved_filter.name, 'can_manage': manager and not inherited, 'is_owner': creator, 'members': members,
            'share_form': form_payload(ShareForm(saved_filter=saved_filter, actor=request.user)), 'visibility': saved_filter.visibility, 'revision': saved_filter.revision}


def team_url(request, saved_filter):
    return filter_url(request, f'{saved_filter.pk}/team/')


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def team(request, pk):
    from .filter_views import get_filter
    saved_filter = get_filter(request, pk, editable=request.method == 'POST')
    if request.method == 'GET':
        return JsonResponse(payload(request, saved_filter))
    with transaction.atomic():
        Workplace.objects.select_for_update().get(pk=request.workplace.pk)
        saved_filter = get_filter(request, pk, editable=True, lock=True)
        if saved_filter.visibility == SavedTaskFilter.Visibility.WORKSPACE:
            raise PermissionDenied
        previous_revision = saved_filter.revision
        action = request.POST.get('action')
        if action == 'share':
            form = ShareForm(request.POST, saved_filter=saved_filter, actor=request.user)
            if not form.is_valid():
                return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
            if saved_filter.visibility == SavedTaskFilter.Visibility.PRIVATE:
                saved_filter.shared_with.clear()
            saved_filter.memberships.create(user=form.recipient, role=form.cleaned_data['role'])
            saved_filter.visibility = SavedTaskFilter.Visibility.SELECTED
        elif action in {'remove', 'role'}:
            try:
                member_id = int(request.POST.get('member_id', ''))
                if not 0 < member_id < 2 ** 63:
                    raise ValueError
            except (ValueError, TypeError):
                raise Http404
            member = saved_filter.memberships.filter(user_id=member_id).exclude(user_id=saved_filter.created_by_id).first()
            if member is None:
                raise Http404
            creator = saved_filter.created_by_id == request.user.pk
            if not creator and member.role == 'admin':
                raise PermissionDenied
            if action == 'remove':
                member.delete()
                if not saved_filter.shared_with.exists():
                    saved_filter.visibility = SavedTaskFilter.Visibility.PRIVATE
            elif request.POST.get('role') in ({'admin', 'member', 'observer'} if creator else {'member', 'observer'}):
                member.role = request.POST['role']
                member.save(update_fields=['role'])
            else:
                raise PermissionDenied
        else:
            return JsonResponse({'error': 'Nieprawidłowa operacja.'}, status=400)
        saved_filter.revision += 1
        saved_filter.save(update_fields=['visibility', 'revision', 'updated_at'])
        return JsonResponse({'ok': True, 'previous_revision': previous_revision, **payload(request, saved_filter)})


@login_required
@never_cache
@require_GET
def candidates(request, pk):
    from .filter_views import get_filter
    saved_filter = get_filter(request, pk, editable=True)
    if saved_filter.visibility == SavedTaskFilter.Visibility.WORKSPACE:
        raise PermissionDenied
    query = request.GET.get('q', '').strip()
    if len(query) < 2 or len(query) > 254:
        return JsonResponse({'results': [], 'has_more': False})
    people = workplace_people(saved_filter.workplace).exclude(email='').exclude(pk=saved_filter.created_by_id)
    if saved_filter.visibility == SavedTaskFilter.Visibility.SELECTED:
        people = people.exclude(pk__in=saved_filter.shared_with.values('pk'))
    for term in query.split():
        people = people.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term)
            | Q(middle_name__icontains=term) | Q(username__icontains=term) | Q(email__icontains=term))
    people = list(people.order_by('first_name', 'last_name', 'email')[:11])
    return JsonResponse({'results': [{'email': person.email, 'name': person.get_full_name() or person.username,
        'avatar': account_avatar(person)} for person in people[:10]], 'has_more': len(people) > 10})
