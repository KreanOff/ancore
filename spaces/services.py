from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone
from django.http import QueryDict

from .access import editable_to, visible_to
from .models import SpaceTask, SpaceTaskActivity
from workplaces.services import can_manage_team, scoped_workplace_app_path, workplace_people, workspace_owner
from .defaults import template_settings
from .models import Space, SpaceConfiguration, Sprint, Team, WorkItem


def app_url(request, suffix='', app='spaces'):
    if request.workplace:
        return scoped_workplace_app_path(request.workplace, app, suffix)
    return f'/{app}/{suffix}'


def space_url(request, space, suffix=''):
    return app_url(request, f'{space.slug}/{suffix}', 'space')


def visible_spaces(request):
    return visible_to(Space.objects.filter(user=workspace_owner(request), workplace=request.workplace), request.user).select_related('configuration', 'workplace')


def manageable_spaces(request):
    """The visible subset governed by the same rules as manage_space."""
    private = Q(visibility='private') & (
        Q(private_owner=request.user)
        | Q(memberships__user=request.user, memberships__role='admin')
    )
    public = Q(visibility='public')
    if not can_manage_team(request.user, request.workplace):
        public &= Q(responsible_user=request.user)
    return visible_spaces(request).filter(private | public).distinct()


def can_manage_spaces(request):
    return can_manage_team(request.user, request.workplace) or manageable_spaces(request).exists()


def visible_items(request):
    tasks = visible_to(SpaceTask.objects.filter(space__user=workspace_owner(request), space__workplace=request.workplace), request.user)
    return WorkItem.objects.filter(task__in=tasks).select_related('task', 'task__assignee', 'space', 'space__configuration', 'team', 'sprint')


def decorate_directory_spaces(request, spaces):
    """Prepare already visible spaces for the shared directory table."""
    spaces = list(spaces)
    if not spaces:
        return spaces
    space_ids = [space.pk for space in spaces]
    favorites = set(Space.objects.filter(pk__in=space_ids, favorited_by=request.user).values_list('pk', flat=True))
    counts = {row['space_id']: row['count'] for row in visible_items(request).filter(
        space_id__in=space_ids,
    ).values('space_id').annotate(count=Count('pk'))}
    managed_ids = set(manageable_spaces(request).filter(pk__in=space_ids).values_list('pk', flat=True))
    for space in spaces:
        space.url = space_url(request, space)
        space.favorite_url = space_url(request, space, 'favorite/')
        space.favorite = space.pk in favorites
        space.item_count = counts.get(space.pk, 0)
        space.settings_url = space.url + '?view=settings'
        space.can_manage = space.pk in managed_ids
        space.edit_url = space_url(request, space, 'edit/')
    return spaces


def teams_for(request):
    return Team.objects.filter(owner=workspace_owner(request), workplace=request.workplace)


def manage_space(request, space):
    project = space
    if project.visibility == 'private':
        return project.private_owner_id == request.user.pk or project.memberships.filter(user=request.user, role='admin').exists()
    return can_manage_team(request.user, request.workplace) or project.responsible_user_id == request.user.pk


def manage_configuration(request, space):
    return can_manage_team(request.user, request.workplace) if space.configuration.shared else manage_space(request, space)


def manage_team(request, team):
    return can_manage_team(request.user, request.workplace) or team.memberships.filter(user=request.user, role='admin').exists()


def task_url(request, task):
    if isinstance(task, SpaceTask):
        item = task.work_item
    else:
        item = WorkItem.objects.filter(legacy_task=task, task__isnull=False).select_related('space').first()
        if item is None:
            name = 'view-subtask' if task.parent_id else 'view-task'
            return app_url(request, f'{name}/{task.task_id}/?task_pk={task.pk}', 'tasks')
    match = getattr(request, 'resolver_match', None)
    params = request.GET.copy() if match and match.app_name in {'spaces', 'workplace_spaces'} else QueryDict(mutable=True)
    params.pop('task_pk', None)
    params.pop('tab', None)
    params['view'] = params.get('view') if params.get('view') in {'list', 'board', 'backlog', 'timeline', 'overview', 'reports'} else 'list'
    return space_url(request, item.space, f'tasks/{item.key}/?') + params.urlencode()


@transaction.atomic
def create_work_item(task):
    space = Space.objects.select_for_update().get(pk=task.space_id)
    number = space.next_number
    maximum = WorkItem.objects.filter(space=space).aggregate(value=Max('rank'))['value'] or 0
    rank = max(number * 100, maximum + 100)
    from .backlog import MAX_RANK
    if rank > MAX_RANK:
        raise ValidationError('Brak miejsca na zapis kolejności zadania. Odśwież backlog.')
    space.next_number += 1
    space.save(update_fields=['next_number'])
    status = next(s['key'] for s in space.statuses if s['category'] == task.status)
    return WorkItem.objects.create(task=task, space=space, number=number, key=f'{space.key}-{number}', rank=rank, status=status, work_type=space.configuration.settings['types'][0]['key'])


def record(item, actor, action, message, metadata=None):
    return SpaceTaskActivity.objects.create(task=item.task, actor=actor, action=action, message=message, metadata=metadata or {})


def transition_allowed(item, target):
    if item.status == target:
        return True
    current = next((s for s in item.space.statuses if s['key'] == item.status), None)
    return bool(current and target in current['transitions'])


def set_status(request, item, target):
    with transaction.atomic():
        from workplaces.models import Workplace
        Workplace.objects.select_for_update().get(pk=request.workplace.pk)
        Space.objects.select_for_update().get(pk=item.space_id)
        task = editable_to(SpaceTask.objects.all(), request.user).select_for_update().get(pk=item.task_id)
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
            'from_label': statuses.get(previous, {}).get('label', previous),
            'to_label': statuses[target]['label'],
            'old_status_label': statuses.get(previous, {}).get('label', previous),
            'new_status_label': statuses[target]['label'],
        })


def update_sprint(request, sprint, action, destination=None):
    with transaction.atomic():
        from workplaces.models import Workplace
        if request.workplace:
            Workplace.objects.select_for_update().get(pk=request.workplace.pk)
        Space.objects.select_for_update().get(pk=sprint.space_id)
        space = visible_spaces(request).filter(pk=sprint.space_id).first()
        if space is None:
            raise PermissionDenied
        sprint = Sprint.objects.select_for_update().get(pk=sprint.pk, space=space)
        if space.template != 'scrum':
            raise ValidationError('Sprinty są dostępne wyłącznie w przestrzeni Scrum.')
        if not manage_space(request, sprint.space):
            raise PermissionDenied
        if action == 'start':
            if sprint.state != 'planned' or Sprint.objects.filter(space=sprint.space, state='active').exists():
                raise ValidationError('W przestrzeni może trwać jeden sprint. Wybierz sprint planowany.')
            if not sprint.items.exists():
                raise ValidationError('Dodaj zadania do sprintu przed jego rozpoczęciem.')
            sprint.state = 'active'
        elif action == 'close':
            if sprint.state != 'active':
                raise ValidationError('Możesz zakończyć tylko aktywny sprint.')
            items = sprint.items.select_related('task').order_by('rank', 'pk')
            allowed = editable_to(SpaceTask.objects.all(), request.user)
            if items.exclude(task__in=allowed).exists():
                raise ValidationError('Sprint zawiera zadania, których nie możesz zmieniać.')
            done = list(items.filter(task__status='closed').values('task_id', 'points'))
            target = None
            if destination is not None:
                target = Sprint.objects.select_for_update().filter(pk=destination.pk, space=space, state='planned').exclude(pk=sprint.pk).first()
                if target is None:
                    raise ValidationError('Sprint docelowy jest już niedostępny. Wybierz backlog lub sprint planowany.')
            unfinished = list(items.exclude(task__status='closed'))
            sprint.result = {'completed': done, 'total': items.count(), 'finished': len(done),
                             'points': sum(item.points or 0 for item in items),
                             'finished_points': sum(item['points'] or 0 for item in done),
                             'carried': len(unfinished), 'destination_id': getattr(target, 'pk', None)}
            from .backlog import append_planned_items
            append_planned_items(request, space, unfinished, target, message_suffix=f' po zakończeniu sprintu „{sprint.name}”')
            sprint.state = 'closed'
            sprint.completed_at = timezone.now()
        else:
            raise ValidationError('Nieprawidłowa operacja sprintu.')
        sprint.save()
