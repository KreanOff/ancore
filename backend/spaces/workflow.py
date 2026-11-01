"""Shared Kanban admission, flow snapshots and blockers.

Placement writes run under the Space lock (and HTTP writers also lock the
Workspace). Capacity always includes private cards; presentation never does.
"""
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.utils import timezone

from .defaults import status_flow_stage


def initial_status(space, category='new', key=None):
    statuses = space.statuses
    if key is not None:
        selected = next((row for row in statuses if row['key'] == key), None)
        if selected is None:
            raise ValidationError('Wybrany status jest już niedostępny. Odśwież formularz.')
        return selected
    queue = next((row for row in statuses if status_flow_stage(row) == 'queue'), statuses[0])
    if category == 'new':
        return queue
    return next((row for row in statuses if row['category'] == category), None) or queue


def assert_snapshot(item, data, *, blocked=False):
    """Optional fields keep old callers compatible; current clients send all."""
    if 'source_status' in data and data['source_status'] != item.status:
        raise ValidationError('Zadanie zmieniło status. Odśwież widok i spróbuj ponownie.', code='conflict')
    if 'source_in_backlog' in data:
        value = data['source_in_backlog']
        if value not in {'true', 'false'} or (value == 'true') != item.in_backlog:
            raise ValidationError('Zadanie zmieniło miejsce planowania. Odśwież widok i spróbuj ponownie.', code='conflict')
    if blocked and 'source_blocked_revision' in data and str(item.task.blocked_revision) != data['source_blocked_revision']:
        raise ValidationError('Blokada zadania zmieniła się. Odśwież widok i spróbuj ponownie.', code='conflict')


def validate_placement(item, previous=None):
    """Enforce on WorkItem.save, including forms and batch planning."""
    from .models import WorkItem
    definitions = {row['key']: row for row in item.space.statuses}
    target = definitions.get(item.status)
    if target is None:
        raise ValidationError('Wybrany status jest już niedostępny. Odśwież formularz.')
    if item.in_backlog and target['category'] == 'closed':
        raise ValidationError('Zakończonego zadania nie można umieścić w backlogu. Najpierw otwórz je ponownie.')
    limit = target.get('wip_limit')
    if item.in_backlog or status_flow_stage(target) != 'active' or not limit:
        return
    # Reordering/editing work already occupying this column needs no new slot.
    if previous and previous['status'] == item.status and not previous['in_backlog']:
        return
    occupied = WorkItem.objects.filter(space_id=item.space_id, status=item.status, in_backlog=False).exclude(
        pk=item.pk).exclude(task__status='closed').count()
    if occupied >= limit:
        raise ValidationError('Nie można przyjąć zadania do tej kolumny: osiągnięto limit WIP. Zakończ lub przenieś bieżącą pracę.', code='wip_limit')


def update_flow_times(item, previous=None):
    """Only record observed events; do not invent historical dates on migration."""
    definitions = {row['key']: row for row in item.space.statuses}
    stage = status_flow_stage(definitions[item.status])
    old_stage = status_flow_stage(definitions[previous['status']]) if previous and previous['status'] in definitions else None
    changed = not previous or previous['status'] != item.status
    entered = not previous or previous['in_backlog'] and not item.in_backlog
    now = timezone.now()
    if changed:
        item.status_entered_at = now
    if stage == 'active' and not item.in_backlog and (entered or changed and old_stage != 'active') and not item.flow_started_at:
        item.flow_started_at = now
    if stage == 'done' and changed and old_stage != 'done':
        item.flow_finished_at = now
    elif stage != 'done':
        item.flow_finished_at = None


def flow_snapshot(item):
    status = next(row for row in item.space.statuses if row['key'] == item.status)
    return {'status': item.status, 'category': status['category'], 'stage': status_flow_stage(status),
            'in_backlog': item.in_backlog, 'at': timezone.now().isoformat(),
            'status_entered_at': item.status_entered_at.isoformat() if item.status_entered_at else None,
            'started_at': item.flow_started_at.isoformat() if item.flow_started_at else None,
            'finished_at': item.flow_finished_at.isoformat() if item.flow_finished_at else None}


def board_wip(space, viewer):
    """Unfiltered counts visible to this viewer; never expose hidden capacity."""
    from .access import visible_to
    from .models import SpaceTask, WorkItem
    tasks = visible_to(SpaceTask.objects.filter(space=space), viewer)
    counts = dict(WorkItem.objects.filter(space=space, task__in=tasks, in_backlog=False).exclude(
        task__status='closed').values('status').annotate(total=Count('pk')).values_list('status', 'total'))
    result = {}
    for status in space.statuses:
        stage = status_flow_stage(status)
        limit = status.get('wip_limit') if stage == 'active' else None
        count = counts.get(status['key'], 0)
        result[status['key']] = {'flow_stage': stage, 'wip_limit': limit, 'wip_count': count,
                                 'wip_full': bool(limit and count >= limit), 'policy': status.get('policy', '')}
    return result


def block_responsible_people(task):
    from .access import task_people
    people = task_people(task)
    if task.visibility == 'private':
        people = people.filter(Q(pk=task.private_owner_id) | Q(pk__in=task.memberships.values('user_id')))
    return people


def set_block(request, item, *, clear=False):
    """Caller holds the Workspace, Space and task locks and has rechecked ACL."""
    from .services import record
    task = item.task
    assert_snapshot(item, request.POST, blocked=True)
    before = {'reason': task.blocked_reason, 'at': task.blocked_at.isoformat() if task.blocked_at else None,
              'responsible_id': task.blocked_responsible_id}
    if clear:
        if task.blocked_at is None:
            return
        task.blocked_reason, task.blocked_at, task.blocked_by, task.blocked_responsible = '', None, None, None
    else:
        reason = request.POST.get('blocked_reason', '').strip()
        if not reason or len(reason) > 2000:
            raise ValidationError('Podaj powód blokady (od 1 do 2000 znaków).')
        people = block_responsible_people(task)
        raw = request.POST.get('blocked_responsible', '')
        if raw:
            if not raw.isascii() or not raw.isdecimal() or len(raw) > 18:
                raise ValidationError('Wybierz dostępną osobę odpowiedzialną za usunięcie blokady.')
            responsible = people.filter(pk=int(raw)).first()
            if responsible is None:
                raise ValidationError('Wybierz dostępną osobę odpowiedzialną za usunięcie blokady.')
        else:
            responsible = people.filter(pk=task.assignee_id).first() if task.assignee_id else None
        if task.blocked_at and task.blocked_reason == reason and task.blocked_responsible_id == getattr(responsible, 'pk', None):
            return
        task.blocked_reason, task.blocked_responsible = reason, responsible
        task.blocked_at = task.blocked_at or timezone.now()
        task.blocked_by = request.user
    task.blocked_revision += 1
    task.save(update_fields=['blocked_reason', 'blocked_at', 'blocked_by', 'blocked_responsible', 'blocked_revision'])
    record(item, request.user, 'unblocked' if clear else 'blocked', 'usunął blokadę zadania' if clear else 'zablokował zadanie', {
        'before': before, 'reason': task.blocked_reason, 'responsible_id': task.blocked_responsible_id,
        'flow': flow_snapshot(item),
    })
