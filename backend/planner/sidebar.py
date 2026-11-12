"""Current date and the default shell calendar."""
import calendar
from datetime import date, timedelta

from django.utils import timezone
from django.utils.formats import date_format

from workplaces.policy import module_enabled
from workplaces.services import scoped_workplace_app_path


def sidebar_url(request, mode='workspace'):
    workplace = getattr(request, 'workplace', None)
    match = request.resolver_match
    if not workplace or not module_enabled(workplace, 'calendar') or mode == 'pulpit-editor':
        return ''
    if match and (match.func.__module__, match.func.__name__) in {
        ('planner.views', 'index'), ('spaces.task_views', 'detail'),
    }:
        return ''
    return scoped_workplace_app_path(workplace, 'calendar', 'sidebar/')


def today_sidebar_payload(request):
    return {
        'status': 'success', 'today': timezone.localdate().isoformat(),
        'time_zone': timezone.get_current_timezone_name(),
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
    return {
        'sidebar': payload, 'sidebar_days': days, 'sidebar_month_label': date_format(month, 'F Y').lower(),
        'sidebar_previous_url': current_url(sidebar_month=previous.strftime('%Y-%m')),
        'sidebar_next_url': current_url(sidebar_month=following.strftime('%Y-%m')),
        'sidebar_today_url': current_url(sidebar_month=today.strftime('%Y-%m')),
    }
