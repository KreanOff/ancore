"""Backlog planning inside the caller's filtered, visible page."""
import json
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Max

from .access import editable_to
from .models import SpaceTask
from .models import Sprint, WorkItem
from .services import record
from .item_query import order_items


MAX_RANK = 2147483647


def append_planned_items(request, space, items, sprint=None, *, board=False, message_suffix=''):
    """Append in source order under the Space lock, preserving every other row."""
    maximum = WorkItem.objects.filter(space=space).aggregate(value=Max('rank'))['value'] or 0
    for item in items:
        maximum += 100
        if maximum > MAX_RANK:
            raise ValidationError('Brak miejsca na zapis kolejności. Odśwież backlog.')
        old_sprint, old_rank = item.sprint_id, item.rank
        item.sprint, item.in_backlog, item.rank = sprint, sprint is None and not board, maximum
        item.save(update_fields=['sprint', 'in_backlog', 'rank'])
        destination = f'do sprintu „{sprint.name}”' if sprint else 'na tablicę' if board else 'do backlogu'
        record(item, request.user, 'updated', f'przeniósł zadanie {destination}{message_suffix}', {
            'old_sprint_id': old_sprint, 'new_sprint_id': item.sprint_id,
            'old_rank': old_rank, 'new_rank': item.rank,
        })


def bulk_plan_items(request, space, scope):
    """Validate the complete selection before moving anything; caller is atomic."""
    if space.template not in {'scrum', 'kanban'}:
        raise ValidationError('Ta przestrzeń nie korzysta z backlogu.')
    selected = request.POST.getlist('item_ids')
    if not selected or len(selected) > 100 or any(not value.isascii() or not value.isdecimal() or len(value) > 18 for value in selected):
        raise ValidationError('Zaznacz od 1 do 100 zadań na bieżącej stronie.')
    ids = {int(value) for value in selected}
    if len(ids) != len(selected):
        raise ValidationError('Nieprawidłowe zaznaczenie zadań.')
    rows = list(Paginator(order_items(request, scope, 'backlog'), 100).get_page(request.GET.get('page')).object_list)
    items = [item for item in rows if item.pk in ids]
    if len(items) != len(ids):
        raise ValidationError('Zaznaczone zadania nie są już dostępne na tej stronie. Odśwież backlog.')
    allowed = set(editable_to(SpaceTask.objects.filter(pk__in=[item.task_id for item in items]), request.user).values_list('pk', flat=True))
    if any(item.task_id not in allowed for item in items):
        raise PermissionDenied
    try:
        positions = json.loads(request.POST.get('positions', ''))
    except (ValueError, TypeError):
        raise ValidationError('Nieprawidłowe dane planowania. Odśwież backlog.')
    expected = {str(item.pk): [item.sprint_id, item.rank] for item in items}
    if positions != expected:
        raise ValidationError('Położenie zaznaczonych zadań zmieniło się. Odśwież backlog i spróbuj ponownie.')
    destination = request.POST.get('destination', '')
    sprint, board = None, destination == 'board'
    if board and space.template != 'kanban':
        raise ValidationError('W Scrum zadania planuje się w sprintach.')
    if destination != 'board' and destination:
        if space.template != 'scrum' or not destination.isascii() or not destination.isdecimal() or len(destination) > 18:
            raise ValidationError('Nieprawidłowe miejsce docelowe.')
        sprint = Sprint.objects.select_for_update().filter(space=space, pk=int(destination), state__in=['planned', 'active']).first()
        if sprint is None:
            raise ValidationError('Sprint jest niedostępny lub został zakończony. Odśwież backlog.')
    changed = [item for item in items if item.sprint_id != getattr(sprint, 'pk', None) or item.in_backlog != (sprint is None and not board)]
    append_planned_items(request, space, changed, sprint, board=board)
    return len(changed)


def posted_number(request, name, *, optional=False):
    value = request.POST.get(name)
    if optional and value == '':
        return None
    if value is None or not value.isdecimal() or len(value) > 18:
        raise ValidationError('Nieprawidłowe dane przenoszenia zadania.')
    return int(value)


def free_rank(space_id, item_id, previous, following):
    lower = previous.rank + 1 if previous else 0
    upper = following.rank - 1 if following else MAX_RANK
    if lower > upper:
        return None
    preferred = (lower + upper) // 2 if following else min(lower + 99, upper)
    occupied = list(WorkItem.objects.filter(space_id=space_id, rank__gte=lower, rank__lte=upper)
                    .exclude(pk=item_id).order_by('rank').values_list('rank', flat=True))
    for start, end in ((preferred, upper), (lower, preferred - 1)):
        candidate = start
        for rank in occupied:
            if rank < candidate:
                continue
            if rank > candidate:
                break
            candidate += 1
        if candidate <= end:
            return candidate
    return None


def redistribute_ranks(request, item, target_rows, insertion):
    """Rotate only visible slots when adjacent integer ranks leave no gap."""
    ordered = list(target_rows)
    ordered.insert(insertion, item)
    row_ids = [row.pk for row in ordered]
    reserved = set(WorkItem.objects.filter(space_id=item.space_id).exclude(pk__in=row_ids)
                   .values_list('rank', flat=True))
    slots = sorted({row.rank for row in ordered if row.rank not in reserved})
    maximum = WorkItem.objects.filter(space_id=item.space_id).aggregate(value=Max('rank'))['value'] or 0
    while len(slots) < len(ordered):
        maximum += 100
        if maximum > MAX_RANK:
            raise ValidationError('Nie można zmienić kolejności. Odśwież listę i spróbuj ponownie.')
        slots.append(maximum)
    changed = []
    for row, rank in zip(ordered, slots):
        if row.rank != rank:
            row.rank = rank
            changed.append(row)
    other_rows = [row for row in changed if row.pk != item.pk]
    allowed = set(editable_to(SpaceTask.objects.filter(pk__in=[row.task_id for row in other_rows]), request.user)
                  .values_list('pk', flat=True))
    if any(row.task_id not in allowed for row in other_rows):
        raise PermissionDenied
    if other_rows:
        # Planning metadata only: no SpaceTask status/save signals are bypassed.
        WorkItem.objects.bulk_update(other_rows, ['rank'])


def move_backlog_item(request, space, item, scope):
    """Called under the existing owner, Workspace, Space and item write locks."""
    if space.template not in {'scrum', 'kanban'}:
        raise ValidationError('Ta przestrzeń nie korzysta z backlogu.')
    source = posted_number(request, 'source_sprint', optional=True)
    source_rank = posted_number(request, 'source_rank')
    if (posted_number(request, 'space'), source, source_rank) != (item.space_id, item.sprint_id, item.rank):
        raise ValidationError('Zadanie zmieniło położenie. Odśwież backlog i spróbuj ponownie.')
    target_id = posted_number(request, 'sprint', optional=True)
    target = None
    if target_id is not None:
        if space.template != 'scrum':
            raise ValidationError('Sprinty są dostępne wyłącznie w przestrzeni Scrum.')
        target = Sprint.objects.select_for_update().filter(pk=target_id, space=space, state__in=['planned', 'active']).first()
        if target is None:
            raise ValidationError('Sprint jest niedostępny lub został zakończony. Odśwież backlog.')
    before = posted_number(request, 'before', optional=True)
    after = posted_number(request, 'after', optional=True)
    rows = list(Paginator(scope.order_by('rank', 'pk'), 100).get_page(request.GET.get('page')).object_list)
    if not any(row.pk == item.pk for row in rows):
        raise ValidationError('Zadanie nie jest już widoczne na tej stronie backlogu. Odśwież listę.')
    target_rows = [row for row in rows if row.sprint_id == target_id and row.pk != item.pk]
    positions = {row.pk: index for index, row in enumerate(target_rows)}
    if before is not None and before not in positions:
        raise ValidationError('Miejsce upuszczenia jest już niedostępne. Odśwież backlog.')
    insertion = positions[before] if before is not None else len(target_rows)
    expected_after = target_rows[insertion - 1].pk if insertion else None
    if after != expected_after:
        raise ValidationError('Kolejność zadań zmieniła się. Odśwież backlog i spróbuj ponownie.')
    original_rows = [row.pk for row in rows if row.sprint_id == target_id]
    new_rows = [row.pk for row in target_rows]
    new_rows.insert(insertion, item.pk)
    backlog = target_id is None
    if item.sprint_id == target_id and original_rows == new_rows and item.in_backlog == backlog:
        return
    old_sprint, old_rank = item.sprint_id, item.rank
    # Hidden/filtered/closed records can bound an insertion but are never edited.
    full_rows = list(WorkItem.objects.filter(space=space, sprint_id=target_id).exclude(pk=item.pk).only('pk', 'rank').order_by('rank', 'pk'))
    full_positions = {row.pk: index for index, row in enumerate(full_rows)}
    full_index = full_positions[before] if before is not None else full_positions[after] + 1 if after is not None else len(full_rows)
    previous = full_rows[full_index - 1] if full_index else None
    following = full_rows[full_index] if full_index < len(full_rows) else None
    rank = free_rank(space.pk, item.pk, previous, following)
    if rank is None:
        redistribute_ranks(request, item, target_rows, insertion)
    else:
        item.rank = rank
    item.sprint, item.in_backlog = target, backlog
    item.save(update_fields=['sprint', 'in_backlog', 'rank'])
    message = 'zmienił kolejność zadania'
    if old_sprint != target_id:
        message = f'przeniósł zadanie do sprintu „{target.name}”' if target else 'przeniósł zadanie do backlogu'
    record(item, request.user, 'updated', message, {
        'old_sprint_id': old_sprint, 'new_sprint_id': target_id,
        'old_rank': old_rank, 'new_rank': item.rank,
    })
