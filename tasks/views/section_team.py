"""Immediate sharing with eligible members of the current Workspace."""
from types import SimpleNamespace

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from workplaces.models import Workplace
from workplaces.services import scoped_workplace_app_path, workspace_owner
from workplaces.team_views import InvitationForm
from tasks.access import editable_to, visible_to
from tasks.models import TaskSection, TaskSectionMembership
from tasks.sharing import section_role, section_candidates as eligible_people


class SectionShareForm(InvitationForm):
    def __init__(self, *args, section, actor, **kwargs):
        # Reuse Workspace's controls and candidate picker; section roles are independent.
        forms.Form.__init__(self, *args, **kwargs)
        self.section = section
        self.fields['email'].widget.attrs.update({
            'id': 'section-team-person-search', 'aria-controls': 'section-team-invite-results',
            'aria-describedby': 'section-team-invite-search-status',
        })
        self.fields['role'].widget.attrs['id'] = 'section-team-invite-role'
        self.fields['role'].choices = [('member', 'Członek'), ('admin', 'Administrator'), ('observer', 'Obserwator')]
        self.fields['role'].help_text = 'Obserwator może tylko przeglądać grupę i jej zawartość.'
        if section_role(section, actor) != 'owner':
            self.fields['role'].choices = [('member', 'Członek'), ('observer', 'Obserwator')]

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        people = eligible_people(self.section).filter(email__iexact=email)
        if people.count() != 1:
            raise forms.ValidationError('Wybierz aktywną osobę należącą do tego Workspace.')
        self.recipient = people.get()
        if self.recipient.pk == self.section.private_owner_id or self.section.shared_with.filter(pk=self.recipient.pk).exists():
            raise forms.ValidationError('Ta osoba jest już członkiem grupy.')
        return email


def _section(request, section_id, *, lock=False):
    sections = visible_to(TaskSection.objects.all(), request.user).filter(
        project__workplace=request.workplace, project__user=workspace_owner(request),
    )
    if lock:
        if request.workplace:
            Workplace.objects.select_for_update().get(pk=request.workplace.pk)
        sections = sections.select_for_update()
    return get_object_or_404(sections, pk=section_id)


def _posted_id(request, name):
    value = request.POST.get(name, '')
    if not value.isdecimal() or len(value) > 18:
        raise Http404
    return int(value)


def team_payload(request, section, form=None):
    role = section_role(section, request.user)
    can_edit = editable_to(TaskSection.objects.all(), request.user).filter(pk=section.pk).exists()
    can_manage = can_edit and role in {'owner', 'admin'} and section.project.workplace_id is not None
    people = eligible_people(section)
    if section.visibility == 'public':
        members = [SimpleNamespace(user=person, user_id=person.pk, pk=person.pk,
                    get_role_display='Uczestnik projektu', created_at=None, can_change=False) for person in people]
    else:
        members = list(section.memberships.filter(user__in=people).select_related('user').order_by('role', 'user__email'))
        for member in members:
            member.can_change = can_edit and (role == 'owner' or (role == 'admin' and member.role in {'member', 'observer'}))
        if section.private_owner_id:
            members.insert(0, SimpleNamespace(user=section.private_owner, user_id=section.private_owner_id,
                pk='owner', get_role_display='Właściciel', created_at=section.created_at, can_change=False))
    context = {
        'project': section, 'team_name': section.title, 'team_kind': 'section', 'team_prefix': f'section-{section.pk}-', 'members': members, 'can_manage_team': can_manage, 'is_team_owner': can_edit and role == 'owner',
        'share_form': form if form is not None else SectionShareForm(section=section, actor=request.user),
        'team_url': scoped_workplace_app_path(section.project.workplace, 'tasks', f'groups/{section.pk}/team/') if section.project.workplace else '',
    }
    return dict(
        members=render_to_string('tasks/includes/project_members_panel.html', context, request=request),
        modals=render_to_string('tasks/includes/project_team_modals.html', context, request=request),
        can_manage=can_manage,
    )


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def section_team(request, section_id):
    if request.method == 'GET':
        return JsonResponse(team_payload(request, _section(request, section_id)))
    with transaction.atomic():
        section = _section(request, section_id, lock=True)
        role = section_role(section, request.user)
        if role not in {'owner', 'admin'} or not section.project.workplace_id or not editable_to(TaskSection.objects.all(), request.user).filter(pk=section.pk).exists():
            raise PermissionDenied
        action = request.POST.get('action')
        if action == 'share':
            form = SectionShareForm(request.POST, section=section, actor=request.user)
            if not form.is_valid():
                return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
            section.invitations.filter(recipient=form.recipient, status='pending').update(status='revoked')
            TaskSectionMembership.objects.create(section=section, user=form.recipient, role=form.cleaned_data['role'])
        elif action in {'remove', 'role'}:
            member = get_object_or_404(section.memberships, pk=_posted_id(request, 'member_id'))
            if member.user_id == section.private_owner_id or (role == 'admin' and member.role not in {'member', 'observer'}):
                raise PermissionDenied
            if action == 'remove':
                section.invitations.filter(recipient=member.user, status='pending').update(status='revoked')
                member.delete()
            elif role == 'owner' and request.POST.get('role') in {'admin', 'member', 'observer'}:
                member.role = request.POST['role']
                member.save(update_fields=['role'])
            else:
                raise PermissionDenied
        else:
            return JsonResponse({'error': 'Nieprawidłowa operacja.'}, status=400)
        return JsonResponse({'ok': True, **team_payload(request, section)})


@login_required
@require_GET
@never_cache
def section_candidates(request, section_id):
    section = _section(request, section_id)
    if section_role(section, request.user) not in {'owner', 'admin'} or not editable_to(TaskSection.objects.all(), request.user).filter(pk=section.pk).exists():
        raise PermissionDenied
    query = (request.GET.get('q') or '').strip()
    if not 2 <= len(query) <= 254:
        return JsonResponse({'results': [], 'has_more': False})
    people = eligible_people(section).exclude(email='').exclude(pk=section.private_owner_id).exclude(
        pk__in=section.shared_with.values('pk'),
    )
    for term in query.split():
        people = people.filter(Q(first_name__icontains=term) | Q(middle_name__icontains=term) |
            Q(last_name__icontains=term) | Q(username__icontains=term) | Q(email__icontains=term))
    people = list(people[:11])
    return JsonResponse({'results': [{'email': person.email, 'name': person.get_full_name() or person.username,
        'html': render_to_string('workplaces/includes/invitation_person.html', {'person': person})} for person in people[:10]],
        'has_more': len(people) > 10})
