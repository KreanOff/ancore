"""Calendar dates for timeline planning, using the task's existing schedule."""
from datetime import date, datetime, time, timezone as datetime_timezone

from django import forms
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


def local_end(task):
    return timezone.localtime(task.due_at).date() if task.due_at else None


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


def posted_source_due(data):
    if 'source_due_at' not in data:
        raise ValidationError('Prześlij poprzedni termin zadania.')
    value = data['source_due_at']
    if not value:
        return None
    try:
        parsed = parse_datetime(value)
    except (TypeError, ValueError):
        parsed = None
    if parsed is None or timezone.is_naive(parsed):
        raise ValidationError('Nieprawidłowy poprzedni termin zadania. Odśwież oś czasu.')
    return parsed


def serialized_precision(value):
    # DjangoJSONEncoder serializes timestamps to milliseconds.
    return value.replace(microsecond=value.microsecond // 1000 * 1000) if value else None


def scheduled_due(task, end_on):
    if end_on is None:
        return None
    if end_on == local_end(task):
        return task.due_at
    old = timezone.localtime(task.due_at) if task.due_at else None
    clock = old.time() if old else time(23, 59)
    # DateTimeField rejects nonexistent/ambiguous wall times at DST changes.
    try:
        result = forms.DateTimeField().clean(datetime.combine(end_on, clock))
        result.astimezone(datetime_timezone.utc)
        return result
    except OverflowError:
        raise ValidationError('Termin z tą godziną jest poza obsługiwanym zakresem dat.')
    except ValidationError:
        raise ValidationError('Godzina terminu nie istnieje lub jest niejednoznaczna w wybranym dniu. Ustaw termin w edycji zadania.')


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
        start_on = posted_date(request.POST, 'start_on')
        end_on = posted_date(request.POST, 'end_on')
        source_start = posted_date(request.POST, 'source_start_on')
        source_due = posted_source_due(request.POST)
        if start_on and end_on and end_on < start_on:
            raise ValidationError('Termin nie może być wcześniejszy niż rozpoczęcie.')
        with transaction.atomic():
            if request.workplace:
                Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            Space.objects.select_for_update().get(pk=space.pk)
            task = SpaceTask.objects.select_for_update().get(pk=item.task_id)
            item = WorkItem.objects.select_for_update().get(pk=item.pk)
            require_editable(SpaceTask.objects.filter(pk=task.pk), request.user)
            # Recheck both the active Workspace and private parents after waiting.
            get_object_or_404(visible_items(request), pk=item.pk, space=space)
            if (source_start != item.start_on
                    or serialized_precision(source_due) != serialized_precision(task.due_at)):
                return error_response('Daty zadania zostały zmienione. Odśwież oś czasu i spróbuj ponownie.', 409)
            due_at = scheduled_due(task, end_on)
            old_start, old_due = item.start_on, task.due_at
            changes = []
            if old_start != start_on:
                item.start_on = start_on
                item.save(update_fields=['start_on'])
                changes.append({'field': 'planowane rozpoczęcie',
                                'from_label': date_format(old_start, 'd.m.Y') if old_start else '—',
                                'to_label': date_format(start_on, 'd.m.Y') if start_on else '—'})
            if old_due != due_at:
                task.due_at = due_at
                task._activity_actor = request.user
                task.save(update_fields=['due_at'])
                changes.append({'field': 'termin wykonania',
                                'from_label': date_format(timezone.localtime(old_due), 'd.m.Y H:i') if old_due else '—',
                                'to_label': date_format(timezone.localtime(due_at), 'd.m.Y H:i') if due_at else '—'})
            if changes:
                item.task = task
                record(item, request.user, 'updated', 'zmienił daty zadania na osi czasu', {
                    'fields': [change['field'] for change in changes], 'changes': changes,
                })
    except ValidationError as error:
        return error_response(' '.join(error.messages))
    return JsonResponse({'saved': True, 'changed': bool(changes), 'start_on': item.start_on,
                         'end_on': local_end(task), 'due_at': task.due_at, 'due_urgency': task.due_urgency})
