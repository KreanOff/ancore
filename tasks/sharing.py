"""Sharing within an existing Workspace, independent of legacy public links."""
from django.db.models import F, Q
from django.utils import timezone

from workplaces.services import workplace_people
from .access import editable_to, visible_to
from .models import TaskProject, TaskProjectInvitation


def share_candidates(workplace, viewer):
    people = workplace_people(workplace, viewer)
    if workplace is None:
        return people.none()
    return people.filter(Q(pk=workplace.owner_id) | Q(
        workplace_memberships__workplace=workplace,
        workplace_memberships__is_active=True,
        workplace_memberships__role__in=['admin', 'member'],
    )).distinct()


def project_role(project, viewer):
    if project.visibility != 'private' or not visible_to(TaskProject.objects.all(), viewer).filter(pk=project.pk).exists():
        return ''
    if project.private_owner_id == viewer.pk:
        return 'owner'
    return project.memberships.filter(user=viewer).values_list('role', flat=True).first() or ''


def pending_project_invitations(user):
    from workplaces.services import workplaces_for_user
    if not user or not user.is_authenticated or not user.is_active:
        return TaskProjectInvitation.objects.none()
    return TaskProjectInvitation.objects.filter(
        recipient=user, status='pending', expires_at__gt=timezone.now(),
        project__visibility='private', project__private_owner__isnull=False,
        project__workplace__in=workplaces_for_user(user),
        project__user_id=F('project__workplace__owner_id'),
    )


def project_access_data(workplace, viewer):
    from workplaces.services import scoped_workplace_app_path
    from django.urls import reverse
    projects = visible_to(TaskProject.objects.filter(workplace=workplace), viewer).only(
        'pk', 'visibility', 'private_owner_id',
    )
    editable_ids = set(editable_to(projects, viewer).values_list('pk', flat=True))
    base = scoped_workplace_app_path(workplace, 'tasks') if workplace else reverse('tasks:tasks')
    return {str(project.pk): {
        'canEdit': project.pk in editable_ids,
        'canManage': project.visibility == 'public' or project.private_owner_id == viewer.pk,
        'teamUrl': f'{base}projects/{project.pk}/team/',
    } for project in projects}
