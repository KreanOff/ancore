"""Current date, mini calendar and today's visible agenda in the default shell."""
import calendar
from datetime import date, datetime, time, timedelta
import re
from urllib.parse import urlencode

from django.db.models import F, Q
from django.utils import timezone
from django.utils.formats import date_format

from core.list_window import window_page, window_payload
from workplaces.policy import module_enabled
from workplaces.services import scoped_workplace_app_path, workspace_owner

from .models import CalendarEvent


def _event_color(value):
    value = str(value or '').strip().lower()
    if re.fullmatch(r'#[0-9a-f]{6}', value):
        return value
    return {
        'red': CalendarEvent.DEFAULT_COLOR, 'blue': '#4f7edb', 'green': '#43a36a',
        'amber': '#d79a35', 'slate': '#7b8493',
    }.get(value, CalendarEvent.DEFAULT_COLOR)


def sidebar_url(request, mode='workspace'):
    workplace = getattr(request, 'workplace', None)
    match = request.resolver_match
    if not workplace or not module_enabled(workplace, 'calendar') or mode == 'pulpit-editor':
        return ''
    if match:
        module, view = match.func.__module__, match.func.__name__
        if (module, view) == ('spaces.task_views', 'detail'):
            return ''
        if module == 'documents.views' and view in {
            'library', 'library_create', 'library_edit', 'upload', 'folder_create',
            'folder_edit', 'detail', 'preview',
        }:
            return ''
    url = scoped_workplace_app_path(workplace, 'calendar', 'sidebar/')
    params = {name: request.GET[name] for name in ('sidebar_task_limit', 'sidebar_task_page') if name in request.GET}
    return url + '?' + urlencode(params) if params else url


def today_sidebar_payload(request):
    from spaces.services import task_url, visible_items

    today = timezone.localdate()
    workplace = getattr(request, 'workplace', None)
    zone = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(today, time.min), zone)
    end = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min), zone)
    tasks_enabled = bool(workplace and module_enabled(workplace, 'spaces'))
    items = []
    if tasks_enabled:
        items = visible_items(request).filter(
            task__due_at__gte=start, task__due_at__lt=end,
        ).exclude(task__status='closed').order_by('task__due_at', 'task_id')
    events = CalendarEvent.objects.none()
    if workplace:
        events = CalendarEvent.objects.filter(
            user=workspace_owner(request), workplace=workplace, start__lt=end,
        ).filter(Q(end__gt=start) | Q(end=F('start'), start__gte=start)).order_by('-all_day', 'start', 'pk')

    # Count the combined feed without materializing it. Each sorted source can
    # contribute at most N rows to the first N entries of their merged window.
    total = (items.count() if tasks_enabled else 0) + events.count()
    page = window_page(range(total), request, limit_parameter='sidebar_task_limit', page_parameter='sidebar_task_page')
    entries = []
    calendar_url = scoped_workplace_app_path(workplace, 'calendar')
    for event in events[:page.limit]:
        begins = timezone.localtime(event.start)
        time_label = ('Cały dzień' if event.all_day else begins.strftime(
            '%d.%m, %H:%M' if begins.date() < today else '%H:%M',
        ))
        entries.append(((not event.all_day, event.start.timestamp(), 'events', event.pk), {
            'id': f'events:{event.pk}', 'source': 'events', 'title': event.title,
            'url': calendar_url + '?' + urlencode({'event': event.pk}),
            'subtitle': 'Kalendarz', 'time_label': time_label, 'starts_at': begins.isoformat(),
            'color': _event_color(event.color),
        }))
    for item in items[:page.limit]:
        due = timezone.localtime(item.task.due_at)
        entries.append(((True, item.task.due_at.timestamp(), 'tasks', item.task_id), {
            'id': f'tasks:{item.task_id}', 'source': 'tasks', 'title': item.task.title,
            'url': task_url(request, item.task), 'subtitle': f'{item.key} · {item.space.name}',
            'time_label': due.strftime('%H:%M'), 'starts_at': due.isoformat(), 'color': '',
        }))
    entries = [entry for _, entry in sorted(entries, key=lambda row: row[0])[:page.limit]]
    pagination = window_payload(
        request, page, base=scoped_workplace_app_path(workplace, 'calendar', 'sidebar/'),
        parameters={'sidebar_task_limit': page.limit},
    )
    return {
        'status': 'success', 'today': today.isoformat(),
        'time_zone': timezone.get_current_timezone_name(),
        'tasks_enabled': tasks_enabled, 'entries': entries, 'pagination': pagination,
    }


def sidebar_template_context(request):
    """Only called by the default block during the first Django render."""
    payload = today_sidebar_payload(request)
    today = date.fromisoformat(payload['today'])
    month = today.replace(day=1)
    try:
        requested_month = date.fromisoformat(request.GET.get('sidebar_month', '') + '-01')
    except ValueError:
        pass
    else:
        # Keep previous/next month links inside Python's supported date range.
        if 2 <= requested_month.year <= 9998:
            month = requested_month
    calendar_url = scoped_workplace_app_path(request.workplace, 'calendar')
    days = []
    for day in calendar.Calendar(firstweekday=0).itermonthdates(month.year, month.month):
        days.append({
            'number': day.day, 'date': day.isoformat(), 'label': date_format(day, 'l, j E Y'),
            'url': calendar_url + '?date=' + day.isoformat(),
            'today': day == today, 'outside': day.month != month.month,
        })
    def current_url(**values):
        query = request.GET.copy()
        for key, value in values.items():
            query[key] = value
        return request.path + '?' + query.urlencode()
    previous = (month - timedelta(days=1)).replace(day=1)
    following = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    pagination = payload['pagination']
    tasks_next_url = current_url(sidebar_task_limit=min(
        pagination['limit'] + pagination['page_size'], pagination['count'],
    )) if pagination['has_next'] else ''
    return {
        'sidebar': payload, 'sidebar_days': days, 'sidebar_month_label': date_format(month, 'F Y').lower(),
        'sidebar_previous_url': current_url(sidebar_month=previous.strftime('%Y-%m')),
        'sidebar_next_url': current_url(sidebar_month=following.strftime('%Y-%m')),
        'sidebar_today_url': current_url(sidebar_month=today.strftime('%Y-%m')),
        'sidebar_tasks_next_url': tasks_next_url,
    }
