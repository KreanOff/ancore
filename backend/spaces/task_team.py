"""Independent task access with the shared member table and sharing dialogs."""
from types import SimpleNamespace
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_http_methods
from workplaces.models import Workplace
from workplaces.team_views import InvitationForm
from .access import editable_to, task_people
from .models import Space, SpaceTask, SpaceTaskMembership
from .services import space_url, record


class ShareForm(InvitationForm):
    def __init__(self, *args, task, actor, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.task = task
        self.fields['email'].widget.attrs.update({'id': 'task-team-person-search', 'aria-controls': 'task-team-invite-results', 'aria-describedby': 'task-team-invite-search-status'})
        self.fields['role'].widget.attrs['id'] = 'task-team-invite-role'
        self.fields['role'].choices = [('member', 'Członek'), ('admin', 'Administrator'), ('observer', 'Obserwator')]
        self.fields['role'].help_text = 'Obserwator może tylko przeglądać zadanie i jego zawartość.'
        if task.visibility == 'private' and actor.pk != task.private_owner_id:
            self.fields['role'].choices = [('member', 'Członek'), ('observer', 'Obserwator')]

    def clean_email(self):
        if self.task.visibility != 'private':
            raise forms.ValidationError('Zadanie publiczne dziedziczy dostęp. Najpierw zapisz widoczność „Prywatne”.')
        people = task_people(self.task).filter(email__iexact=self.cleaned_data['email'])
        if people.count() != 1:
            raise forms.ValidationError('Wybierz osobę z dostępem do przestrzeni i zadania nadrzędnego.')
        self.recipient = people.get()
        if self.recipient.pk == self.task.private_owner_id or self.task.memberships.filter(user=self.recipient).exists():
            raise forms.ValidationError('Ta osoba ma już dostęp do zadania.')
        return self.recipient.email


def team_context(request, task):
    from .task_views import manages_task
    can_edit = editable_to(SpaceTask.objects.all(), request.user).filter(pk=task.pk).exists()
    manager = can_edit and manages_task(request, task)
    owner = manager and (task.visibility == 'public' or request.user.pk == task.private_owner_id)
    people = task_people(task)
    if task.visibility == 'private':
        members = list(task.memberships.filter(user__in=people).select_related('user').order_by('role', 'user__email'))
        for member in members:
            member.can_change = manager and (owner or member.role in {'member', 'observer'})
        if task.private_owner_id:
            members.insert(0, SimpleNamespace(user=task.private_owner, user_id=task.private_owner_id, pk='owner', get_role_display='Właściciel', created_at=task.created_at, can_change=False))
    else:
        roles = dict(task.space.memberships.values_list('user_id', 'role'))
        members = [SimpleNamespace(user=person, user_id=person.pk, pk=person.pk, can_change=False,
                   get_role_display='Właściciel' if person.pk == (task.space.private_owner_id or task.space.user_id) else dict(SpaceTaskMembership._meta.get_field('role').choices).get(roles.get(person.pk), 'Dostęp odziedziczony'),
                   created_at=task.created_at if person.pk == task.space.user_id else None) for person in people]
    return {'project': task, 'team_app': 'spaces', 'team_name': task.title, 'team_kind': 'task', 'team_prefix': f'space-task-{task.pk}-',
            'members': members, 'can_manage_team': manager, 'is_team_owner': owner,
            'share_form': ShareForm(task=task, actor=request.user), 'team_url': space_url(request, task.space, f'tasks/{task.work_item.key}/team/')}


def payload(request, task):
    context = team_context(request, task)
    if getattr(request, '_react_api', False):
        from .frontend import task_members_payload
        return task_members_payload(context)
    return {'members': render_to_string('tasks/includes/project_members_panel.html', context, request=request),
            'modals': render_to_string('tasks/includes/project_team_modals.html', context, request=request), 'can_manage': context['can_manage_team']}


@login_required
@require_http_methods(['GET', 'POST'])
def team(request, space_pk, key):
    from .task_views import task_item, manages_task, posted_id
    item = task_item(request, space_pk, key)
    if request.method == 'GET':
        return JsonResponse(payload(request, item.task))
    with transaction.atomic():
        Workplace.objects.select_for_update().get(pk=request.workplace.pk)
        Space.objects.select_for_update().get(pk=item.space_id)
        item = task_item(request, space_pk, key)
        task = SpaceTask.objects.select_for_update().get(pk=item.task_id)
        if not manages_task(request, task) or not editable_to(SpaceTask.objects.all(), request.user).filter(pk=task.pk).exists():
            raise PermissionDenied
        owner = request.user.pk == task.private_owner_id
        action = request.POST.get('action')
        if action == 'share':
            form = ShareForm(request.POST, task=task, actor=request.user)
            if not form.is_valid():
                return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
            SpaceTaskMembership.objects.create(task=task, user=form.recipient, role=form.cleaned_data['role'])
        elif action in {'role', 'remove'}:
            member = get_object_or_404(task.memberships, pk=posted_id(request, 'member_id'))
            if not owner and member.role == 'admin':
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
        record(item, request.user, 'updated', 'zmienił dostęp do zadania')
        return JsonResponse({'ok': True, **payload(request, task)})


@login_required
@require_GET
def candidates(request, space_pk, key):
    from .task_views import task_item, manages_task
    task = task_item(request, space_pk, key).task
    if not manages_task(request, task) or not editable_to(SpaceTask.objects.all(), request.user).filter(pk=task.pk).exists():
        raise PermissionDenied
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': [], 'has_more': False})
    people = task_people(task).exclude(pk=task.private_owner_id).exclude(pk__in=task.memberships.values('user_id'))
    for term in query.split():
        people = people.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(middle_name__icontains=term) | Q(username__icontains=term) | Q(email__icontains=term))
    people = list(people[:11])
    if getattr(request, '_react_api', False):
        from accounts.avatar import account_avatar
        return JsonResponse({'results': [{'email': person.email, 'name': person.get_full_name() or person.username, 'avatar': account_avatar(person)} for person in people[:10]], 'has_more': len(people) > 10})
    return JsonResponse({'results': [{'email': person.email, 'name': person.get_full_name() or person.username,
        'html': render_to_string('workplaces/includes/invitation_person.html', {'person': person})} for person in people[:10]], 'has_more': len(people) > 10})
