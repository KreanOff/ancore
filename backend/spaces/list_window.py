"""Load a bounded prefix of each status from an already scoped, sorted list."""
from django.db.models import Case, F, IntegerField, Value, When, Window
from django.db.models.functions import RowNumber

from .services import space_url


LIST_BATCH_SIZE = 20


def status_limit(request, key, total):
    return group_limit(request, f'list_limit_{key}', total)


def group_limit(request, parameter, total):
    value = request.GET.get(parameter, '')
    if not value.isascii() or not value.isdecimal():
        return min(LIST_BATCH_SIZE, total)
    # Clamp before converting arbitrary input to int; every existing row remains
    # reachable, including groups larger than a fixed safety cap would allow.
    value = value.lstrip('0') or '0'
    if len(value) > len(str(total)):
        return total
    return min(max(int(value), LIST_BATCH_SIZE), total)


def list_window(request, space, items, counts):
    """Apply limits in SQL after visibility/filters and preserve display ordering."""
    limits = {status['key']: status_limit(request, status['key'], counts.get(status['key'], 0))
              for status in space.statuses}
    return items.annotate(_list_position=Window(
        expression=RowNumber(), partition_by=[F('status')], order_by=list(items.query.order_by),
    )).filter(_list_position__lte=Case(
        *[When(status=key, then=Value(limit)) for key, limit in limits.items()],
        default=Value(0), output_field=IntegerField(),
    ))


def more_url(request, space, key, loaded_count, total):
    if loaded_count >= total:
        return ''
    params = request.GET.copy()
    params.pop('page', None)
    params['view'] = 'list'
    params[f'list_limit_{key}'] = min(loaded_count + LIST_BATCH_SIZE, total)
    return space_url(request, space) + '?' + params.urlencode()


def list_url(request, space, suffix=''):
    params = request.GET.copy()
    params.pop('page', None)
    params['view'] = 'list'
    return space_url(request, space, suffix) + '?' + params.urlencode()
