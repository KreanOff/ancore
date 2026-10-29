"""Calendar dates for timeline planning, using the task's existing schedule."""
from datetime import date, time, timezone as datetime_timezone

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.formats import date_format
from django.views.decorators.http import require_POST

from workplaces.models import Workplace
from .access import require_editable
from .models import Space, SpaceTask, WorkItem
from .services import record, visible_items
from .schedule import ScheduleDateTimeField, local_date, move_to_date, validate_range


def local_end(task):
    return local_date(task.due_at)


def posted_date(data, name):
    value = data.get(name)
    if value is None or not isinstance(value, str):
        raise ValidationError('Prześlij komplet dat zadania i ich poprzednich wartości.')
    if not value:
        return None
    try:
        result = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError('Podaj prawidłową datę w formacie RRRR-MM-DD.')
    if result.isoformat() != value:
        raise ValidationError('Podaj prawidłową datę w formacie RRRR-MM-DD.')
    return result


def posted_source(data, name):
    if name not in data:
        raise ValidationError('Prześlij poprzednią datę i godzinę zadania.')
    value = data[name]
    if not value:
        return None
    try:
        parsed = parse_datetime(value)
        if parsed is None or timezone.is_naive(parsed):
            raise ValueError
        parsed.astimezone(datetime_timezone.utc)
    except (TypeError, ValueError, OverflowError):
        raise ValidationError('Nieprawidłowa poprzednia data zadania. Odśwież oś czasu.')
    return parsed


def serialized_precision(value):
    # DjangoJSONEncoder serializes timestamps to milliseconds. Normalize zones
    # before equality so the two occurrences of a repeated DST hour differ.
    return value.astimezone(datetime_timezone.utc).replace(microsecond=value.microsecond // 1000 * 1000) if value else None


def posted_datetime(data, name, previous):
    value = data.get(name)
    if value is None or not isinstance(value, str):
        raise ValidationError('Prześlij komplet dat i godzin zadania.')
    # The dialog displays minutes. Do not erase seconds on an untouched field.
    if previous and value == timezone.localtime(previous).strftime('%Y-%m-%dT%H:%M'):
        return previous
    return ScheduleDateTimeField(required=False).clean(value)


def datetime_label(value):
    return date_format(timezone.localtime(value), 'd.m.Y H:i') if value else '—'


def error_response(message, status=400):
    return JsonResponse({'error': message, 'message': message}, status=status)


@login_required
@require_POST
def update_dates(request, space_pk, key):
    from .views import space_object

    space = space_object(request, space_pk)
    item = get_object_or_404(visible_items(request), space=space, key=key)
    require_editable(SpaceTask.objects.filter(pk=item.task_id), request.user)
    try:
        explicit_times = 'start_at' in request.POST or 'due_at' in request.POST
        if not explicit_times:
            start_on = posted_date(request.POST, 'start_on')
            end_on = posted_date(request.POST, 'end_on')
        source_start = posted_source(request.POST, 'source_start_at')
        source_due = posted_source(request.POST, 'source_due_at')
        with transaction.atomic():
            if request.workplace:
                Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            Space.objects.select_for_update().get(pk=space.pk)
            task = SpaceTask.objects.select_for_update().get(pk=item.task_id)
            item = WorkItem.objects.select_for_update().get(pk=item.pk)
            require_editable(SpaceTask.objects.filter(pk=task.pk), request.user)
            # Recheck both the active Workspace and private parents after waiting.
            get_object_or_404(visible_items(request), pk=item.pk, space=space)
            if (serialized_precision(source_start) != serialized_precision(item.start_at)
                    or serialized_precision(source_due) != serialized_precision(task.due_at)):
                return error_response('Daty zadania zostały zmienione. Odśwież oś czasu i spróbuj ponownie.', 409)
            if explicit_times:
                start_at = posted_datetime(request.POST, 'start_at', item.start_at)
                due_at = posted_datetime(request.POST, 'due_at', task.due_at)
            else:
                start_at = move_to_date(item.start_at, start_on)
                due_at = move_to_date(task.due_at, end_on, time(23, 59))
            validate_range(start_at, due_at)
            old_start, old_due = item.start_at, task.due_at
            changes = []
            if old_start != start_at:
                item.start_at = start_at
                item.save(update_fields=['start_at'])
                changes.append({'field': 'planowane rozpoczęcie',
                                'from_label': datetime_label(old_start),
                                'to_label': datetime_label(start_at)})
            if old_due != due_at:
                task.due_at = due_at
                task._activity_actor = request.user
                task.save(update_fields=['due_at'])
                changes.append({'field': 'termin wykonania',
                                'from_label': datetime_label(old_due),
                                'to_label': datetime_label(due_at)})
            if changes:
                item.task = task
                record(item, request.user, 'updated', 'zmienił daty zadania na osi czasu', {
                    'fields': [change['field'] for change in changes], 'changes': changes,
                })
    except ValidationError as error:
        return error_response(' '.join(error.messages))
    return JsonResponse({'saved': True, 'changed': bool(changes), 'start_at': item.start_at, 'start_on': local_date(item.start_at),
                         'end_on': local_end(task), 'due_at': task.due_at, 'due_urgency': task.due_urgency})
