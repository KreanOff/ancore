from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from core.frontend import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from workplaces.services import workspace_owner

from .forms import CalendarEventForm
from .models import CalendarEvent
from workplaces.services import scoped_workplace_app_path


def _active_workplace(request):
    return getattr(request, 'workplace', None)


def _filter_workplace(queryset, workplace):
    if workplace is None:
        return queryset
    return queryset.filter(workplace=workplace)


def _event_payload(event):
    return {
        'id': event.id,
        'title': event.title,
        'description': event.description,
        'start': timezone.localtime(event.start).isoformat(),
        'end': timezone.localtime(event.end).isoformat(),
        'all_day': event.all_day,
        'color': event.color,
        'source': 'events',
    }


def _parse_range_param(value):
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.endswith('Z'):
        cleaned = cleaned[:-1] + '+00:00'
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    tz = timezone.get_current_timezone()
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, tz)
    return parsed.astimezone(tz)


@login_required
def index(request):
    from django.middleware.csrf import get_token

    initial_event = None
    event_id = request.GET.get('event')
    if event_id and event_id.isdigit():
        initial_event = _filter_workplace(
            CalendarEvent.objects.filter(user=workspace_owner(request), pk=int(event_id)),
            _active_workplace(request),
        ).first()

    now = timezone.localtime(initial_event.start) if initial_event else timezone.localtime()
    requested_date = request.GET.get('date')
    if initial_event is None and requested_date:
        try:
            parsed_date = date.fromisoformat(requested_date)
        except ValueError:
            parsed_date = None
        if parsed_date is not None:
            now = timezone.make_aware(datetime.combine(parsed_date, datetime.min.time()))

    return render(request, 'planner/index.html', {
        'calendar_config': {
            'csrfToken': get_token(request),
            'urls': {
                'events': scoped_workplace_app_path(request.workplace, 'calendar', 'events/'),
                'create': scoped_workplace_app_path(request.workplace, 'calendar', 'events/create/'),
                'update': scoped_workplace_app_path(request.workplace, 'calendar', 'events/__ID__/update/'),
                'delete': scoped_workplace_app_path(request.workplace, 'calendar', 'events/__ID__/delete/'),
            },
            'initialYear': now.year,
            'initialMonth': now.month,
            'initialDay': now.day,
            'initialEventId': initial_event.id if initial_event else None,
        },
    })


@login_required
@require_GET
def events_list(request):
    start = _parse_range_param(request.GET.get('start'))
    end = _parse_range_param(request.GET.get('end'))
    if not start or not end or start > end or end - start > timedelta(days=370):
        return JsonResponse({'status': 'error', 'message': 'Podaj prawidłowy zakres dat, nie dłuższy niż rok.'}, status=400)

    events = _filter_workplace(CalendarEvent.objects.filter(
        user=workspace_owner(request),
        start__lte=end,
        end__gte=start,
    ), _active_workplace(request))
    payload = [_event_payload(event) for event in events]
    from spaces.services import visible_items, task_url
    for item in visible_items(request).filter(task__due_at__gte=start, task__due_at__lte=end).exclude(task__status='closed'):
        due = timezone.localtime(item.task.due_at).isoformat()
        payload.append({'id': f'space_tasks:{item.task_id}', 'source': 'tasks', 'title': f'{item.key} · {item.task.title}',
                        'description': item.task.description, 'start': due, 'end': due, 'all_day': False, 'color': 'blue',
                        'status': item.task.status, 'url': task_url(request, item.task)})
    response = JsonResponse({
        'status': 'success',
        'events': sorted(payload, key=lambda item: (item['start'], str(item['id']))),
    })
    response['Cache-Control'] = 'no-store'
    return response


@login_required
@require_POST
def create_event(request):
    form = CalendarEventForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    event = form.save(commit=False)
    event.user = workspace_owner(request)
    event.workplace = _active_workplace(request)
    event.save()
    return JsonResponse({'status': 'success', 'event': _event_payload(event)})


@login_required
@require_POST
def update_event(request, event_id):
    event = get_object_or_404(_filter_workplace(CalendarEvent.objects.filter(user=workspace_owner(request)), _active_workplace(request)), id=event_id)
    form = CalendarEventForm(request.POST, instance=event)
    if not form.is_valid():
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    event = form.save()
    return JsonResponse({'status': 'success', 'event': _event_payload(event)})


@login_required
@require_POST
def delete_event(request, event_id):
    event = get_object_or_404(_filter_workplace(CalendarEvent.objects.filter(user=workspace_owner(request)), _active_workplace(request)), id=event_id)
    event.delete()
    return JsonResponse({'status': 'success'})
