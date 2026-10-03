from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from core.task_numbering import lock_task_numbers
from tasks.access import editable_to, visible_to
from tasks.models import Task, TaskActivity, TaskProject, TaskSection
from workplaces.services import can_manage_team, scoped_workplace_app_path, workplace_people, workspace_owner
from .defaults import template_settings
from .models import Space, SpaceConfiguration, Sprint, Team, WorkItem


def app_url(request, suffix='', app='spaces'):
    if request.workplace:
        return scoped_workplace_app_path(request.workplace, app, suffix)
    return f'/{app}/{suffix}'


def visible_spaces(request):
    projects = visible_to(TaskProject.objects.filter(user=workspace_owner(request), workplace=request.workplace), request.user)
    return Space.objects.filter(project__in=projects).select_related('project', 'configuration', 'workplace')


def visible_items(request):
    tasks = visible_to(Task.objects.filter(user=workspace_owner(request), workplace=request.workplace), request.user)
    return WorkItem.objects.filter(task__in=tasks).select_related('task', 'task__assignee', 'space__project', 'space__configuration', 'team', 'sprint')


def teams_for(request):
    return Team.objects.filter(owner=workspace_owner(request), workplace=request.workplace)


def manage_space(request, space):
    project = space.project
    if project.visibility == 'private':
        return project.private_owner_id == request.user.pk or project.memberships.filter(user=request.user, role='admin').exists()
    return can_manage_team(request.user, request.workplace) or project.responsible_user_id == request.user.pk


def manage_configuration(request, space):
    return can_manage_team(request.user, request.workplace) if space.configuration.shared else manage_space(request, space)


def manage_team(request, team):
    return can_manage_team(request.user, request.workplace) or team.memberships.filter(user=request.user, role='admin').exists()


@transaction.atomic
def ensure_space(project):
    found = Space.objects.filter(project=project).first()
    if found:
        return found
    if not project.workplace_id:
        return None
    # The project row serializes creation from concurrent task saves.
    TaskProject.objects.select_for_update().get(pk=project.pk)
    found = Space.objects.filter(project=project).first()
    if found:
        return found
    config = SpaceConfiguration.objects.create(workplace=project.workplace, name=project.name, settings=template_settings())
    key = f'P{project.pk}'
    while Space.objects.filter(workplace=project.workplace, key=key).exists():
        key = f'P{project.pk}X' if not key.endswith('X') else key + 'X'
    return Space.objects.create(project=project, workplace=project.workplace, key=key, configuration=config)


@transaction.atomic
def ensure_work_item(task):
    project = task.section.project if task.section_id else None
    space = ensure_space(project) if project and (project.user_id, project.workplace_id) == (task.user_id, task.workplace_id) else None
    item = WorkItem.objects.filter(task=task).first()
    if item and item.space_id == getattr(space, 'pk', None):
        if space:
            statuses = {status['key']: status for status in space.statuses}
            current = statuses.get(item.status)
            if not current or current['category'] != task.status:
                target = next((s for s in space.statuses if s['category'] == task.status and (not current or s['key'] in current['transitions'])), None)
                if target:
                    WorkItem.objects.filter(pk=item.pk).update(status=target['key'])
                    item.status = target['key']
        return item
    if space:
        space = Space.objects.select_for_update().get(pk=space.pk)
        number = space.next_number
        space.next_number += 1
        space.save(update_fields=['next_number'])
        status = next((s['key'] for s in space.statuses if s['category'] == task.status), 'new')
        values = dict(space=space, number=number, key=f'{space.key}-{number}', rank=number * 100, status=status, work_type=space.configuration.settings['types'][0]['key'])
    else:
        values = dict(space=None, number=0, key=f'TASK-{task.pk}', rank=task.pk, status=task.status)
    if item:
        # Moving to another space resets only planning relations, not task content.
        values.update(sprint=None, epic=None, team=None, work_type=space.configuration.settings['types'][0]['key'] if space else 'task')
        values['key'] = item.key
        WorkItem.objects.filter(pk=item.pk).update(**values)
        item.refresh_from_db()
        return item
    return WorkItem.objects.create(task=task, **values)


def task_url(request, task):
    name = 'view-subtask' if task.parent_id else 'view-task'
    return app_url(request, f'{name}/{task.task_id}/?task_pk={task.pk}', 'tasks')


def record(item, actor, action, message, metadata=None):
    return TaskActivity.objects.create(task=item.task, actor=actor, action=action, message=message, metadata=metadata or {})


def transition_allowed(item, target):
    if item.status == target:
        return True
    current = next((s for s in item.space.statuses if s['key'] == item.status), None)
    return bool(current and target in current['transitions'])


def category_transition_allowed(task, target):
    if not task.pk:
        return True
    item = WorkItem.objects.filter(task=task, space__isnull=False).select_related('space__configuration').first()
    if not item:
        return True
    current = next((s for s in item.space.statuses if s['key'] == item.status), None)
    if not current or current['category'] == target:
        return True
    return any(s['category'] == target and s['key'] in current['transitions'] for s in item.space.statuses)


def set_status(request, item, target):
    with lock_task_numbers(item.task.user_id):
        task = editable_to(Task.objects.all(), request.user).select_for_update().get(pk=item.task_id)
        item = WorkItem.objects.select_for_update(of=('self',)).select_related('space__configuration').get(pk=item.pk)
        statuses = {s['key']: s for s in item.space.statuses}
        if target not in statuses or not transition_allowed(item, target):
            raise ValidationError('To przejście statusu nie jest dozwolone w tej przestrzeni.')
        if item.status == target:
            return
        previous = item.status
        # Update metadata first so the task save signal observes the selected status.
        item.status = target
        item.save(update_fields=['status'])
        task.status = statuses[target]['category']
        task.save(update_fields=['status', 'is_completed', 'completion_date'])
        item.task = task
        record(item, request.user, 'status_changed', 'zmienił status', {
            'old_status': previous, 'new_status': target,
            'old_status_label': statuses.get(previous, {}).get('label', previous),
            'new_status_label': statuses[target]['label'],
        })


def default_section(space):
    section = space.project.sections.filter(visibility='public').order_by('pk').first()
    if section is None:
        section = TaskSection.objects.create(project=space.project, title='Zadania', visibility='public')
    return section


def update_sprint(request, sprint, action):
    with lock_task_numbers(sprint.space.project.user_id):
        Space.objects.select_for_update().get(pk=sprint.space_id)
        sprint = Sprint.objects.select_for_update().get(pk=sprint.pk)
        if not manage_space(request, sprint.space):
            raise PermissionDenied
        if action == 'start':
            if sprint.state != 'planned' or Sprint.objects.filter(space=sprint.space, state='active').exists():
                raise ValidationError('W przestrzeni może trwać jeden sprint. Wybierz sprint planowany.')
            sprint.state = 'active'
        elif action == 'close':
            if sprint.state != 'active':
                raise ValidationError('Możesz zakończyć tylko aktywny sprint.')
            items = sprint.items.select_related('task')
            allowed = editable_to(Task.objects.all(), request.user)
            if items.exclude(task__in=allowed).exists():
                raise ValidationError('Sprint zawiera zadania, których nie możesz zmieniać.')
            done = list(items.filter(task__status='closed').values('task_id', 'points'))
            sprint.result = {'completed': done, 'total': items.count(), 'finished': len(done)}
            for item in items.exclude(task__status='closed'):
                item.sprint = None
                item.in_backlog = True
                item.save(update_fields=['sprint', 'in_backlog'])
                record(item, request.user, 'updated', f'przeniósł zadanie do backlogu po zakończeniu sprintu „{sprint.name}”')
            sprint.state = 'closed'
            sprint.completed_at = timezone.now()
        else:
            raise ValidationError('Nieprawidłowa operacja sprintu.')
        sprint.save()
