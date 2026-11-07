"""Bounded cumulative windows over already scoped, ordered results."""
from django.core.paginator import Page, Paginator
from django.http import QueryDict


LIST_BATCH_SIZE = 20


def _limit(value, total, multiplier=1):
    value = str(value or '')
    if not value.isascii() or not value.isdecimal():
        return min(LIST_BATCH_SIZE, total)
    value = value.lstrip('0') or '0'
    # Clamp before int() so arbitrarily long input never reaches conversion.
    if len(value) > len(str(total)):
        return total
    return min(max(int(value) * multiplier, LIST_BATCH_SIZE), total)


class WindowPage(Page):
    def __init__(self, object_list, limit, paginator, limit_parameter, page_parameter):
        super().__init__(object_list, max(1, (limit + LIST_BATCH_SIZE - 1) // LIST_BATCH_SIZE), paginator)
        self.limit = limit
        self.limit_parameter = limit_parameter
        self.page_parameter = page_parameter

    def start_index(self):
        return 1 if self.paginator.count else 0

    def end_index(self):
        return self.limit

    def has_previous(self):
        return False

    def has_next(self):
        return self.limit < self.paginator.count


def window_page(items, request, *, limit_parameter='limit', page_parameter='page', parameters=None):
    """Return the first N results; old page=2 means a cumulative window of 40."""
    params = request.GET if parameters is None else parameters
    paginator = Paginator(items, LIST_BATCH_SIZE)
    total = paginator.count
    limit = (_limit(params.get(limit_parameter), total) if limit_parameter in params
             else _limit(params.get(page_parameter), total, LIST_BATCH_SIZE))
    return WindowPage(items[:limit], limit, paginator, limit_parameter, page_parameter)


def window_url(request, page, base=None, extra=None, parameters=None):
    if not page.has_next():
        return ''
    if parameters is None:
        params = request.GET.copy()
    elif isinstance(parameters, QueryDict):
        params = parameters.copy()
    else:
        params = QueryDict('', mutable=True)
        params.update(parameters)
    params.pop(page.page_parameter, None)
    params.pop('page_size', None)
    if extra:
        for key, value in extra.items():
            params[key] = value
    params[page.limit_parameter] = min(page.limit + LIST_BATCH_SIZE, page.paginator.count)
    return (base or request.path) + '?' + params.urlencode()


def window_payload(request, page, base=None, extra=None, parameters=None):
    count, end = page.paginator.count, page.end_index()
    summary = f'{end} z {count}'
    return {
        'page': page.number, 'total_pages': page.paginator.num_pages,
        'page_size': LIST_BATCH_SIZE, 'page_size_options': [],
        'count': count, 'start': page.start_index(), 'end': end,
        'limit': page.limit, 'has_previous': False, 'has_next': page.has_next(),
        'previous_url': '', 'next_url': window_url(request, page, base, extra, parameters),
        'summary': summary, 'compact_summary': summary,
    }
