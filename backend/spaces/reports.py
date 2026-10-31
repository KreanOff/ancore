"""Read-only reports from the complete, already authorized space task scope.

Period activity uses local calendar days. Completion dates are the latest
completion of tasks still closed, not an immutable history of transitions.
"""
import csv
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import StreamingHttpResponse
from django.utils import timezone

from accounts.avatar import account_avatar
from .models import SpaceTask, SpaceTaskWorkLog
from .services import space_url, task_url
from .summary import materialized_summary_items


REPORT_PERIODS = (7, 30, 90)
REPORT_FILTERS = ('q', 'work_type', 'team', 'assignee', 'status', 'priority', 'summary')


def report_scope(request, space, items):
    """An invalid or foreign sprint fails closed, without revealing its name."""
    value = request.GET.get('report_sprint', 'all') or 'all'
    if value == 'all':
        return items, value, ''
    if value == 'none':
        return items.filter(sprint__isnull=True), value, ''
    if value.isdecimal() and len(value) < 19 and space.sprints.filter(pk=int(value)).exists():
        return items.filter(sprint_id=int(value)), str(int(value)), ''
    return items.none(), value[:100], 'Wybrany sprint jest niedostępny. Wybierz sprint z listy lub wyczyść filtry.'


def period_window(request, now):
    raw = request.GET.get('report_period', '30')
    days = int(raw) if raw in {str(period) for period in REPORT_PERIODS} else 30
    today = timezone.localdate(now)
    start_on = today - timedelta(days=days - 1)
    start = timezone.make_aware(datetime.combine(start_on, time.min), timezone.get_current_timezone())
    return days, start_on, today, start


def minutes_label(minutes):
    hours, minutes = divmod(int(minutes), 60)
    return f'{hours} godz. {minutes} min' if hours else f'{minutes} min'


def percent(value, total):
    return round(value * 100 / total, 1) if total else 0


def report_url(request, space, **changes):
    params = {key: request.GET[key] for key in (*REPORT_FILTERS, 'report_period', 'report_sprint') if request.GET.get(key)}
    params.update(view='reports', **changes)
    return space_url(request, space) + '?' + urlencode({key: value for key, value in params.items() if value != ''})


def space_reports(request, space, items, now=None):
    now = now or timezone.now()
    items, sprint_filter, error = report_scope(request, space, items)
    items = materialized_summary_items(items)
    days, start_on, today, start = period_window(request, now)
    closed = Q(task__status='closed')
    overdue = Q(task__due_at__lt=now) & ~closed
    snapshot = items.aggregate(
        total=Count('pk'), completed=Count('pk', filter=closed), overdue=Count('pk', filter=overdue),
        due_soon=Count('pk', filter=Q(task__due_at__gte=now, task__due_at__lte=now + timedelta(days=7)) & ~closed),
        unassigned=Count('pk', filter=Q(task__assignee__isnull=True) & ~closed),
        point_total=Sum('points', default=0), completed_points=Sum('points', filter=closed, default=0),
        unestimated=Count('pk', filter=Q(points__isnull=True) & ~closed),
    )
    snapshot['points'] = snapshot.pop('point_total')
    snapshot.update(open=snapshot['total'] - snapshot['completed'], completion_percent=percent(snapshot['completed'], snapshot['total']))
    trend = {start_on + timedelta(days=index): {'date': (start_on + timedelta(days=index)).isoformat(),
             'label': (start_on + timedelta(days=index)).strftime('%d.%m'), 'created': 0, 'completed': 0, 'logged_minutes': 0}
             for index in range(days)}
    for field, key in (('task__created_at', 'created'), ('task__completion_date', 'completed')):
        dated = items.filter(**{field + '__gte': start, field + '__lte': now})
        if key == 'completed':
            dated = dated.filter(closed)
        for row in dated.order_by().annotate(day=TruncDate(field)).values('day').annotate(count=Count('pk')):
            trend[row['day']][key] = row['count']
    # Select overlapping entries, clipping future hours and period boundaries.
    # Calendar days use the user's timezone; elapsed time uses UTC across DST.
    logs = SpaceTaskWorkLog.objects.filter(task_id__in=items.order_by().values('task_id'), started_at__lt=now, ended_at__gt=start)
    logged_by_assignee = defaultdict(int)
    current_zone = timezone.get_current_timezone()
    for entry in logs.order_by().values('started_at', 'ended_at', 'task__assignee_id').iterator(chunk_size=1000):
        cursor, end = max(entry['started_at'], start), min(entry['ended_at'], now)
        while cursor < end:
            day = timezone.localdate(cursor)
            midnight = timezone.make_aware(datetime.combine(day + timedelta(days=1), time.min), current_zone)
            segment_end = min(end, midnight)
            value = int((segment_end.astimezone(UTC) - cursor.astimezone(UTC)).total_seconds() // 60)
            trend[day]['logged_minutes'] += value
            logged_by_assignee[entry['task__assignee_id']] += value
            cursor = segment_end
    activity = {key: sum(row[key] for row in trend.values()) for key in ('created', 'completed', 'logged_minutes')}
    activity['logged_label'] = minutes_label(activity['logged_minutes'])

    counts = dict(items.order_by().values('status').annotate(count=Count('pk')).values_list('status', 'count'))
    known = {status['key'] for status in space.statuses}
    definitions = [*space.statuses, *({'key': key, 'label': key, 'category': 'new', 'color': ''} for key in counts if key not in known)]
    statuses = [{**status, 'color': status.get('color', ''), 'count': counts.get(status['key'], 0),
                 'percent': percent(counts.get(status['key'], 0), snapshot['total']),
                 'url': report_url(request, space, status=status['key'])} for status in definitions]
    priority_counts = dict(items.exclude(closed).order_by().values('task__priority').annotate(count=Count('pk')).values_list('task__priority', 'count'))
    priorities = [{'key': key, 'label': label, 'count': priority_counts.get(key, 0),
                   'percent': percent(priority_counts.get(key, 0), snapshot['open']),
                   'url': report_url(request, space, priority=key)} for key, label in reversed(SpaceTask.PRIORITY_CHOICES)]

    workloads = list(items.order_by().values('task__assignee_id').annotate(
        total=Count('pk'), completed=Count('pk', filter=closed), overdue=Count('pk', filter=overdue),
        points=Sum('points', filter=~closed, default=0),
    ).order_by('-total', 'task__assignee_id'))
    people = get_user_model().objects.in_bulk([row['task__assignee_id'] for row in workloads if row['task__assignee_id']])
    workload = []
    for row in workloads:
        pk = row.pop('task__assignee_id')
        person = people.get(pk)
        minutes = logged_by_assignee[pk]
        workload.append({**row, 'id': pk, 'label': (person.get_full_name() or person.email or person.username) if person else 'Nieprzypisane',
                         'avatar': account_avatar(person) if person else None, 'open': row['total'] - row['completed'],
                         'logged_minutes': minutes, 'logged_label': minutes_label(minutes),
                         'url': report_url(request, space, assignee=pk if pk else 'unassigned')})

    sprint_counts = {row.pop('sprint_id'): row for row in items.order_by().values('sprint_id').annotate(
        total=Count('pk'), completed=Count('pk', filter=closed), point_total=Sum('points', default=0),
        completed_points=Sum('points', filter=closed, default=0),
    )}
    for counts in sprint_counts.values():
        counts['points'] = counts.pop('point_total')
    sprints = list(space.sprints.all())
    sprints.sort(key=lambda sprint: (sprint.state != 'active', sprint.state == 'closed', -sprint.start_on.toordinal(), -sprint.pk))
    sprint_rows = []
    for sprint in sprints:
        if sprint_filter != 'all' and sprint_filter != str(sprint.pk):
            continue
        count = sprint_counts.get(sprint.pk, {'total': 0, 'completed': 0, 'points': 0, 'completed_points': 0})
        sprint_rows.append({**count, 'id': sprint.pk, 'name': sprint.name, 'state': sprint.state, 'state_label': sprint.get_state_display(),
                            'start_on': sprint.start_on.isoformat(), 'end_on': sprint.end_on.isoformat(),
                            'open': count['total'] - count['completed'], 'completion_percent': percent(count['completed'], count['total']),
                            'url': report_url(request, space, report_sprint=sprint.pk)})
    status_labels = {row['key']: row['label'] for row in definitions}
    overdue_rows = []
    for item in items.filter(overdue).select_related('task__assignee', 'task__work_item', 'space').order_by('task__due_at', 'pk')[:10]:
        task = item.task
        overdue_rows.append({'id': item.pk, 'key': item.key, 'title': task.title, 'url': task_url(request, task),
                             'due_at': task.due_at.isoformat(), 'days_overdue': (today - timezone.localdate(task.due_at)).days,
                             'priority': task.priority, 'priority_label': task.get_priority_display(),
                             'assignee': (task.assignee.get_full_name() or task.assignee.email or task.assignee.username) if task.assignee_id else 'Nieprzypisane',
                             'status_label': status_labels.get(item.status, item.status)})
    return {
        'period': {'days': days, 'start_on': start_on.isoformat(), 'end_on': today.isoformat(), 'label': f'{start_on:%d.%m.%Y} – {today:%d.%m.%Y}'},
        'filters': {'report_period': str(days), 'report_sprint': sprint_filter}, 'filter_error': error,
        'sprint_options': [{'value': 'all', 'label': 'Wszystkie sprinty'}, {'value': 'none', 'label': 'Bez sprintu'}] +
                          [{'value': str(sprint.pk), 'label': f'{sprint.name} · {sprint.get_state_display()}'} for sprint in sprints],
        'snapshot': snapshot, 'activity': activity, 'trend': list(trend.values()), 'statuses': statuses, 'priorities': priorities,
        'workload': workload, 'sprints': sprint_rows, 'overdue': {'total': snapshot['overdue'], 'items': overdue_rows},
        'export_url': report_url(request, space, report_export='csv'), 'reset_url': space_url(request, space) + '?view=reports',
        'generated_at': now.isoformat(),
    }


def safe_csv_cell(value):
    """Quoted CSV alone does not stop spreadsheet formulas in user text."""
    value = str(value) if value is not None else ''
    if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')):
        return "'" + value
    return value


class _CSVBuffer:
    def write(self, value):
        return value


def report_csv(request, space, items):
    items, _selected, _error = report_scope(request, space, items)
    statuses = {row['key']: row['label'] for row in space.statuses}
    writer = csv.writer(_CSVBuffer(), delimiter=';')

    def rows():
        yield '\ufeff'
        yield writer.writerow(['Klucz', 'Tytuł', 'Status', 'Priorytet', 'Wykonawca', 'Zespół', 'Sprint', 'Punkty',
                               'Utworzono', 'Termin', 'Ostatnie zakończenie'])
        for item in items.select_related('task__assignee', 'team', 'sprint').order_by('number', 'pk').iterator(chunk_size=1000):
            task = item.task
            values = [item.key, task.title, statuses.get(item.status, item.status), task.get_priority_display(),
                      (task.assignee.get_full_name() or task.assignee.email or task.assignee.username) if task.assignee_id else '',
                      item.team.name if item.team_id else '', item.sprint.name if item.sprint_id else '', item.points,
                      timezone.localtime(task.created_at).isoformat(), timezone.localtime(task.due_at).isoformat() if task.due_at else '',
                      timezone.localtime(task.completion_date).isoformat() if task.status == 'closed' and task.completion_date else '']
            yield writer.writerow([safe_csv_cell(value) for value in values])

    response = StreamingHttpResponse(rows(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="raport-przestrzeni-{space.pk}-{timezone.localdate().isoformat()}.csv"'
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
