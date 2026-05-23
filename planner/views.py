from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import CalendarEventForm
from .models import CalendarEvent


def _event_payload(event):
    return {
        'id': event.id,
        'title': event.title,
        'description': event.description,
        'start': timezone.localtime(event.start).isoformat(),
        'end': timezone.localtime(event.end).isoformat(),
        'all_day': event.all_day,
        'color': event.color,
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
    from django.urls import reverse

    now = timezone.localtime()
    return render(request, 'planner/index.html', {
        'calendar_config': {
            'csrfToken': get_token(request),
            'urls': {
                'events': reverse('planner:events'),
                'create': reverse('planner:create_event'),
                'update': reverse('planner:update_event', kwargs={'event_id': 0}).replace('/0/', '/__ID__/'),
                'delete': reverse('planner:delete_event', kwargs={'event_id': 0}).replace('/0/', '/__ID__/'),
            },
            'initialYear': now.year,
            'initialMonth': now.month,
        },
    })


@login_required
@require_GET
def events_list(request):
    start = _parse_range_param(request.GET.get('start'))
    end = _parse_range_param(request.GET.get('end'))
    if not start or not end:
        return JsonResponse({'status': 'error', 'message': 'Zakres dat jest wymagany.'}, status=400)

    events = CalendarEvent.objects.filter(
        user=request.user,
        start__lte=end,
        end__gte=start,
    )
    return JsonResponse({
        'status': 'success',
        'events': [_event_payload(event) for event in events],
    })


@login_required
@require_POST
def create_event(request):
    form = CalendarEventForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    event = form.save(commit=False)
    event.user = request.user
    event.save()
    return JsonResponse({'status': 'success', 'event': _event_payload(event)})


@login_required
@require_POST
def update_event(request, event_id):
    event = get_object_or_404(CalendarEvent, id=event_id, user=request.user)
    form = CalendarEventForm(request.POST, instance=event)
    if not form.is_valid():
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    event = form.save()
    return JsonResponse({'status': 'success', 'event': _event_payload(event)})


@login_required
@require_POST
def delete_event(request, event_id):
    event = get_object_or_404(CalendarEvent, id=event_id, user=request.user)
    event.delete()
    return JsonResponse({'status': 'success'})
