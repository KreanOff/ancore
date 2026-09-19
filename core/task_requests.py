"""Stable task identities for mutation requests (display numbers can change)."""
from django.http import Http404


def task_detail_lookup(request, task_id):
    value = request.POST.get('task_pk') or request.GET.get('task_pk')
    if value is None:
        return {'task_id': task_id}
    try:
        primary_key = int(value)
        if primary_key <= 0:
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        raise Http404('Nieprawidłowy identyfikator rekordu.')
    return {'pk': primary_key}


def task_primary_keys(data, *, many=False):
    if not isinstance(data, dict):
        raise ValueError('Nieprawidłowe dane zadania.')
    values = data.get('task_pks') if many else [data.get('task_pk')]
    if not isinstance(values, list) or not values:
        raise ValueError('Odśwież stronę i ponów operację — brakuje identyfikatora rekordu.')
    if any(type(value) is not int or value <= 0 for value in values):
        raise ValueError('Nieprawidłowy identyfikator rekordu. Odśwież stronę.')
    return list(dict.fromkeys(values))
