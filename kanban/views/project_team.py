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
from kanban.access import visible_to
from kanban.models import KanbanProject, KanbanProjectMembership
from kanban.sharing import project_role, share_candidates


class ProjectShareForm(InvitationForm):
    def __init__(self, *args, project, actor, **kwargs):
        # Reuse Workspace's controls and candidate picker; project roles are independent.
        forms.Form.__init__(self, *args, **kwargs)
        self.project = project
        self.fields['email'].widget.attrs.update({
            'id': 'project-team-person-search', 'aria-controls': 'project-team-invite-results',
            'aria-describedby': 'project-team-invite-search-status',
        })
        self.fields['role'].widget.attrs['id'] = 'project-team-invite-role'
        self.fields['role'].choices = [('member', 'Członek'), ('admin', 'Administrator'), ('observer', 'Obserwator')]
        self.fields['role'].help_text = 'Obserwator może tylko przeglądać przestrzeń i jej zawartość.'
        if project_role(project, actor) != 'owner':
            self.fields['role'].choices = [('member', 'Członek'), ('observer', 'Obserwator')]

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        people = share_candidates(self.project.workplace, None).filter(email__iexact=email)
        if people.count() != 1:
            raise forms.ValidationError('Wybierz aktywną osobę należącą do tego Workspace.')
        self.recipient = people.get()
        if self.recipient.pk == self.project.private_owner_id or self.project.shared_with.filter(pk=self.recipient.pk).exists():
            raise forms.ValidationError('Ta osoba jest już członkiem przestrzeni.')
        return email


def _project(request, project_id, *, lock=False):
    projects = visible_to(KanbanProject.objects.all(), request.user).filter(
        workplace=request.workplace, user=workspace_owner(request),
    )
    if lock:
        if request.workplace:
            Workplace.objects.select_for_update().get(pk=request.workplace.pk)
        projects = projects.select_for_update()
    return get_object_or_404(projects, pk=project_id)


def _posted_id(request, name):
    value = request.POST.get(name, '')
    if not value.isdecimal() or len(value) > 18:
        raise Http404
    return int(value)


def team_payload(request, project, form=None):
    role = project_role(project, request.user)
    can_manage = role in {'owner', 'admin'} and project.workplace_id is not None
    people = share_candidates(project.workplace, request.user)
    if project.visibility == 'public':
        members = [SimpleNamespace(user=person, user_id=person.pk, pk=person.pk,
                    get_role_display='Członek Workspace', created_at=None, can_change=False) for person in people]
    else:
        members = list(project.memberships.filter(user__in=people).select_related('user').order_by('role', 'user__email'))
        for member in members:
            member.can_change = role == 'owner' or (role == 'admin' and member.role in {'member', 'observer'})
        if project.private_owner_id:
            members.insert(0, SimpleNamespace(user=project.private_owner, user_id=project.private_owner_id,
                pk='owner', get_role_display='Właściciel', created_at=project.created_at, can_change=False))
    context = {
        'team_app': 'kanban', 'project': project, 'team_name': project.name, 'team_kind': 'project', 'team_prefix': f'project-{project.pk}-', 'members': members, 'can_manage_team': can_manage, 'is_team_owner': role == 'owner',
        'share_form': form if form is not None else ProjectShareForm(project=project, actor=request.user),
        'team_url': scoped_workplace_app_path(project.workplace, 'kanban', f'projects/{project.pk}/team/') if project.workplace else '',
    }
    return dict(
        members=render_to_string('tasks/includes/project_members_panel.html', context, request=request),
        modals=render_to_string('tasks/includes/project_team_modals.html', context, request=request),
        can_manage=can_manage,
    )


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def project_team(request, project_id):
    if request.method == 'GET':
        return JsonResponse(team_payload(request, _project(request, project_id)))
    with transaction.atomic():
        project = _project(request, project_id, lock=True)
        role = project_role(project, request.user)
        if role not in {'owner', 'admin'} or not project.workplace_id:
            raise PermissionDenied
        action = request.POST.get('action')
        if action == 'share':
            form = ProjectShareForm(request.POST, project=project, actor=request.user)
            if not form.is_valid():
                return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
            KanbanProjectMembership.objects.create(project=project, user=form.recipient, role=form.cleaned_data['role'])
        elif action in {'remove', 'role'}:
            member = get_object_or_404(project.memberships, pk=_posted_id(request, 'member_id'))
            if member.user_id == project.private_owner_id or (role == 'admin' and member.role not in {'member', 'observer'}):
                raise PermissionDenied
            if action == 'remove':
                member.delete()
            elif role == 'owner' and request.POST.get('role') in {'admin', 'member', 'observer'}:
                member.role = request.POST['role']
                member.save(update_fields=['role'])
            else:
                raise PermissionDenied
        else:
            return JsonResponse({'error': 'Nieprawidłowa operacja.'}, status=400)
        return JsonResponse({'ok': True, **team_payload(request, project)})


@login_required
@require_GET
@never_cache
def project_candidates(request, project_id):
    project = _project(request, project_id)
    if project_role(project, request.user) not in {'owner', 'admin'}:
        raise PermissionDenied
    query = (request.GET.get('q') or '').strip()
    if not 2 <= len(query) <= 254:
        return JsonResponse({'results': [], 'has_more': False})
    people = share_candidates(project.workplace, request.user).exclude(email='').exclude(pk=project.private_owner_id).exclude(
        pk__in=project.shared_with.values('pk'),
    )
    for term in query.split():
        people = people.filter(Q(first_name__icontains=term) | Q(middle_name__icontains=term) |
            Q(last_name__icontains=term) | Q(username__icontains=term) | Q(email__icontains=term))
    people = list(people[:11])
    return JsonResponse({'results': [{'email': person.email, 'name': person.get_full_name() or person.username,
        'html': render_to_string('workplaces/includes/invitation_person.html', {'person': person})} for person in people[:10]],
        'has_more': len(people) > 10})
