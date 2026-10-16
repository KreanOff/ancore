"""Sharing within an existing Workspace, independent of legacy public links."""
from django.db.models import Q

from workplaces.services import workplace_people
from .access import editable_to, visible_to
from .models import Task, TaskProject, TaskSection


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


def section_candidates(section):
    people = share_candidates(section.project.workplace, None)
    if section.project.visibility == 'private':
        if not section.project.private_owner_id:
            return people.none()
        people = people.filter(Q(pk=section.project.private_owner_id) | Q(pk__in=section.project.shared_with.values('pk')))
    return people


def section_role(section, viewer):
    if section.visibility != 'private' or not visible_to(TaskSection.objects.all(), viewer).filter(pk=section.pk).exists():
        return ''
    if section.private_owner_id == viewer.pk:
        return 'owner'
    return section.memberships.filter(user=viewer).values_list('role', flat=True).first() or ''


def section_access_data(workplace, viewer):
    from workplaces.services import scoped_workplace_app_path
    from django.urls import reverse
    sections = visible_to(TaskSection.objects.filter(project__workplace=workplace), viewer).only(
        'pk', 'visibility', 'private_owner_id',
    )
    editable_ids = set(editable_to(sections, viewer).values_list('pk', flat=True))
    base = scoped_workplace_app_path(workplace, 'tasks') if workplace else reverse('tasks:tasks')
    return {str(section.pk): {
        'visibility': section.visibility,
        'canEdit': section.pk in editable_ids,
        'canManage': section.pk in editable_ids and (section.visibility == 'public' or section.private_owner_id == viewer.pk),
        'teamUrl': f'{base}groups/{section.pk}/team/',
    } for section in sections}


def task_candidates(task):
    """Intersect Workspace, group/project and every ancestor's privacy."""
    people = share_candidates(task.workplace, None)
    current, seen = task, set()
    while current:
        if current.pk in seen:
            return people.none()
        seen.add(current.pk)
        if current.workplace_id != task.workplace_id or current.user_id != task.user_id:
            return people.none()
        if current.section_id:
            for resource in [current.section.project, current.section]:
                if resource.visibility == 'private':
                    if not resource.private_owner_id:
                        return people.none()
                    people = people.filter(Q(pk=resource.private_owner_id) | Q(pk__in=resource.shared_with.values('pk')))
        if current.pk != task.pk and current.visibility == 'private':
            if not current.private_owner_id:
                return people.none()
            people = people.filter(Q(pk=current.private_owner_id) | Q(pk__in=current.shared_with.values('pk')))
        current = current.parent if current.parent_id else None
    return people


def task_role(task, viewer):
    if task.visibility != 'private' or not visible_to(Task.objects.all(), viewer).filter(pk=task.pk).exists():
        return ''
    if task.private_owner_id == viewer.pk:
        return 'owner'
    return task.memberships.filter(user=viewer).values_list('role', flat=True).first() or ''
