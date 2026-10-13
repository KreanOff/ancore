"""Persist card placement inside the caller's visible board page."""
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator

from .backlog import free_rank, posted_number, redistribute_ranks
from .models import WorkItem
from .services import record, set_status, transition_allowed


def move_board_item(request, space, item, scope):
    """Caller holds the Workspace, Space and source item write locks."""
    snapshot = (posted_number(request, 'space'), request.POST.get('source_status'),
                posted_number(request, 'source_sprint', optional=True), posted_number(request, 'source_rank'))
    if snapshot != (space.pk, item.status, item.sprint_id, item.rank):
        raise ValidationError('Zadanie zmieniło położenie. Odśwież tablicę i spróbuj ponownie.')
    target = request.POST.get('status')
    if target not in {status['key'] for status in space.statuses} or not transition_allowed(item, target):
        raise ValidationError('To przejście statusu nie jest dozwolone w tej przestrzeni.')
    rows = list(Paginator(scope.order_by('rank', 'pk'), 100).get_page(request.GET.get('page')).object_list)
    if not any(row.pk == item.pk for row in rows):
        raise ValidationError('Zadanie nie jest już widoczne na tej stronie tablicy. Odśwież listę.')
    target_rows = [row for row in rows if row.status == target and row.pk != item.pk]
    original_rows = [row.pk for row in rows if row.status == target]
    direction = request.POST.get('direction', '')
    if direction:
        if direction not in {'up', 'down'} or target != item.status:
            raise ValidationError('Nieprawidłowa zmiana kolejności zadania.')
        index = original_rows.index(item.pk)
        insertion = index + (-1 if direction == 'up' else 1)
        if not 0 <= insertion <= len(target_rows):
            return
        before = target_rows[insertion].pk if insertion < len(target_rows) else None
        after = target_rows[insertion - 1].pk if insertion else None
    else:
        before = posted_number(request, 'before', optional=True)
        after = posted_number(request, 'after', optional=True)
        positions = {row.pk: index for index, row in enumerate(target_rows)}
        if before is not None and before not in positions:
            raise ValidationError('Miejsce upuszczenia jest już niedostępne. Odśwież tablicę.')
        insertion = positions[before] if before is not None else len(target_rows)
        expected_after = target_rows[insertion - 1].pk if insertion else None
        anchors = (target_rows[insertion] if before is not None else None,
                   target_rows[insertion - 1] if insertion else None)
        ranks = tuple(posted_number(request, name, optional=True) for name in ('before_rank', 'after_rank'))
        if after != expected_after or ranks != tuple(row.rank if row else None for row in anchors):
            raise ValidationError('Kolejność zadań zmieniła się. Odśwież tablicę i spróbuj ponownie.')
    new_rows = [row.pk for row in target_rows]
    new_rows.insert(insertion, item.pk)
    if item.status == target and original_rows == new_rows:
        return

    # Inaccessible, filtered and off-page rows bound the gap but are never edited.
    full_scope = WorkItem.objects.filter(space=space, status=target)
    if space.template == 'scrum':
        full_scope = full_scope.filter(sprint_id=item.sprint_id)
    else:
        full_scope = full_scope.filter(in_backlog=False)
    full_rows = list(full_scope.exclude(pk=item.pk).only('pk', 'rank').order_by('rank', 'pk'))
    full_positions = {row.pk: index for index, row in enumerate(full_rows)}
    full_index = full_positions[before] if before is not None else full_positions[after] + 1 if after is not None else len(full_rows)
    previous = full_rows[full_index - 1] if full_index else None
    following = full_rows[full_index] if full_index < len(full_rows) else None
    old_rank, old_status = item.rank, item.status
    rank = free_rank(space.pk, item.pk, previous, following)
    if rank is None:
        redistribute_ranks(request, item, target_rows, insertion)
    else:
        item.rank = rank
    item.save(update_fields=['rank'])
    # Preserve the existing task save signals, completion dates and status history.
    if old_status != target:
        set_status(request, item, target)
    record(item, request.user, 'updated', 'zmienił kolejność zadania na tablicy', {
        'old_rank': old_rank, 'new_rank': item.rank,
        'old_status': old_status, 'new_status': target,
    })
