"""Load independent prefixes of the already scoped backlog and open sprints."""
from django.db.models import Case, Count, F, IntegerField, Value, When, Window
from django.db.models.functions import RowNumber

from .list_window import LIST_BATCH_SIZE, group_limit
from .services import space_url


def limit_parameter(sprint_id):
    group = 'backlog' if sprint_id is None else f'sprint_{sprint_id}'
    return f'backlog_limit_{group}'


def backlog_window(request, items):
    """Apply limits after visibility/filters and retain the selected sort order."""
    counts = dict(items.order_by().values_list('sprint_id').annotate(n=Count('pk')))
    if not counts:
        return items.none()
    return items.annotate(_backlog_position=Window(
        expression=RowNumber(), partition_by=[F('sprint_id')], order_by=list(items.query.order_by),
    )).filter(_backlog_position__lte=Case(
        *[When(sprint_id=sprint_id, then=Value(group_limit(request, limit_parameter(sprint_id), total)))
          for sprint_id, total in counts.items()],
        default=Value(0), output_field=IntegerField(),
    ))


def backlog_more_url(request, space, sprint_id, loaded_count, total):
    if loaded_count >= total:
        return ''
    params = request.GET.copy()
    params.pop('page', None)
    params['view'] = 'backlog'
    params[limit_parameter(sprint_id)] = min(loaded_count + LIST_BATCH_SIZE, total)
    return space_url(request, space) + '?' + params.urlencode()
