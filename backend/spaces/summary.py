"""Read-only space summary and drill-downs over the viewer's visible work items."""

from datetime import timedelta
from math import cos, pi, sin
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.exceptions import EmptyResultSet
from django.db.models import Count, Q
from django.db.models.expressions import RawSQL
from django.utils import timezone

from accounts.avatar import account_avatar
from .models import SpaceTask, SpaceTaskActivity
from .defaults import issue_type_icon
from .access import visible_to
from .services import app_url, space_url, task_url


SUMMARY_SCOPES = {
    'completed': 'Zakończone w ostatnich 7 dniach',
    'updated': 'Zaktualizowane w ostatnich 7 dniach',
    'created': 'Utworzone w ostatnich 7 dniach',
    'due': 'Z terminem w najbliższych 7 dniach',
    'recent': 'Otwarte i zakończone w ostatnich 14 dniach',
    'open': 'Otwarte zadania',
}


def status_arc_path(start_percent, percent):
    """Clockwise SVG centerline; the donut's parent rotates it by -90 degrees."""
    if percent <= 0:
        return ''

    def point(position):
        angle = (position % 100) * 2 * pi / 100
        coordinates = (50 + 40 * cos(angle), 50 + 40 * sin(angle))
        return ' '.join(f'{value:.8f}'.rstrip('0').rstrip('.') for value in coordinates)

    start = point(start_percent)
    if percent >= 100:
        # An SVG arc with coincident endpoints is empty. Two semicircles form
        # the full ring while retaining the same open-path stroke behavior.
        opposite = point(start_percent + 50)
        return f'M {start} A 40 40 0 0 1 {opposite} A 40 40 0 0 1 {start}'
    end = point(start_percent + percent)
    return f'M {start} A 40 40 0 {1 if percent > 50 else 0} 1 {end}'


def summary_scope(items, scope, now):
    week_start = now - timedelta(days=7)
    if scope == 'completed':
        return items.filter(task__status='closed', task__completion_date__gte=week_start, task__completion_date__lte=now)
    if scope == 'updated':
        changed = SpaceTaskActivity.objects.filter(created_at__gte=week_start, created_at__lte=now).exclude(action='created')
        return items.filter(task_id__in=changed.values('task_id'))
    if scope == 'created':
        return items.filter(task__created_at__gte=week_start, task__created_at__lte=now)
    if scope == 'due':
        return items.exclude(task__status='closed').filter(task__due_at__gte=now, task__due_at__lte=now + timedelta(days=7))
    if scope == 'recent':
        return items.filter(~Q(task__status='closed') | Q(task__completion_date__gte=now - timedelta(days=14), task__completion_date__lte=now))
    if scope == 'open':
        return items.exclude(task__status='closed')
    return items


def filter_summary_items(request, space, items, now):
    """Validate drill-down parameters; filtering never broadens the input ACL."""
    status = request.GET.get('status', '')
    status = status if status in {row['key'] for row in space.statuses} else ''
    priority = request.GET.get('priority', '')
    priority = priority if priority in dict(SpaceTask.PRIORITY_CHOICES) else ''
    scope = request.GET.get('summary', '')
    scope = scope if scope in SUMMARY_SCOPES else ''
    assignee = request.GET.get('assignee', '')
    if assignee == 'me':
        items = items.filter(task__assignee=request.user)
    elif assignee == 'unassigned':
        items = items.filter(task__assignee__isnull=True)
    elif assignee.isdecimal() and len(assignee) < 19:
        items = items.filter(task__assignee_id=int(assignee))
    else:
        assignee = ''
    if status:
        items = items.filter(status=status)
    if priority:
        items = items.filter(task__priority=priority)
    return summary_scope(items, scope, now), {
        'status_filter': status, 'priority_filter': priority, 'assignee_filter': assignee,
        'summary_filter': scope, 'summary_filter_label': SUMMARY_SCOPES.get(scope, ''),
    }


def materialized_summary_items(items):
    """Keep the ACL/filter query separate from grouped summary joins.

    Flattening the nested permission subqueries into an assignee aggregation
    can make PostgreSQL choose deeply nested loops from stale row estimates.
    The materialized IDs are still selected by the original queryset, in the
    same statement and snapshot as each aggregate.
    """
    if items.query.is_empty():
        return items
    try:
        sql, params = items.order_by().values('pk').query.get_compiler(using=items.db).as_sql()
    except EmptyResultSet:
        return items.none()
    scope = RawSQL(
        f'WITH summary_items AS MATERIALIZED ({sql}) SELECT "pk" FROM summary_items', params,
    )
    return items.model.objects.using(items.db).filter(pk__in=scope).select_related('task', 'space')


def space_summary(request, space, items, now=None):
    now = now or timezone.now()
    items = materialized_summary_items(items)
    base = space_url(request, space)
    # Preserve the existing space filters when following a chart or counter.
    params = {key: request.GET[key] for key in ('q', 'work_type', 'group', 'team', 'assignee', 'status', 'priority') if request.GET.get(key)}

    def list_url(**filters):
        return base + '?' + urlencode({**params, 'view': 'list', **filters})

    metrics = []
    for key, label, icon in (
        ('completed', 'Zakończone', 'circle-check'),
        ('updated', 'Zaktualizowane', 'refresh-cw'),
        ('created', 'Utworzone', 'plus'),
        ('due', 'Zbliżające się terminy', 'calendar-days'),
    ):
        metrics.append({'key': key, 'label': label, 'icon': icon, 'count': summary_scope(items, key, now).count(), 'url': list_url(summary=key)})

    current = summary_scope(items, 'recent', now)
    counts = dict(current.order_by().values_list('status').annotate(count=Count('pk')))
    status_total = sum(counts.values())
    statuses, offset = [], 0
    for status in space.statuses:
        count = counts.get(status['key'], 0)
        percent = count * 100 / status_total if status_total else 0
        statuses.append({**status, 'count': count, 'percent': round(percent),
                         'arc': f'{percent:.4f}', 'gap': f'{100 - percent:.4f}', 'offset': f'{-offset:.4f}',
                         'path': status_arc_path(offset, percent),
                         'url': list_url(summary='recent', status=status['key'])})
        offset += percent

    open_items = summary_scope(items, 'open', now)
    open_total = open_items.count()
    priority_counts = dict(open_items.order_by().values_list('task__priority').annotate(count=Count('pk')))
    maximum = max(priority_counts.values(), default=1) or 1
    magnitude = 10 ** (len(str(maximum)) - 1)
    priority_axis_max = next(step * magnitude for step in (1, 2, 4, 5, 10) if step * magnitude >= maximum)
    priorities = [{'key': key, 'label': label, 'count': priority_counts.get(key, 0),
                   'height': f'{priority_counts.get(key, 0) * 100 / priority_axis_max:.4f}',
                   'url': list_url(summary='open', priority=key)}
                  for key, label in reversed(SpaceTask.PRIORITY_CHOICES)]

    total = items.count()
    type_counts = dict(items.order_by().values_list('work_type').annotate(count=Count('pk')))
    types = [{**row, 'icon': issue_type_icon(row['key']), 'count': type_counts.get(row['key'], 0),
              'percent': round(type_counts.get(row['key'], 0) * 100 / total) if total else 0,
              'url': list_url(work_type=row['key'])}
             for row in space.configuration.settings['types']]

    workload_counts = list(open_items.order_by().values('task__assignee_id').annotate(count=Count('pk')).order_by('-count', 'task__assignee_id'))
    people = get_user_model().objects.in_bulk([row['task__assignee_id'] for row in workload_counts if row['task__assignee_id']])
    workload = []
    for row in workload_counts:
        user = people.get(row['task__assignee_id'])
        workload.append({'label': (user.get_full_name() or user.email) if user else 'Nieprzypisane',
                         'avatar': account_avatar(user) if user else None, 'count': row['count'],
                         'percent': round(row['count'] * 100 / open_total) if open_total else 0,
                         'url': list_url(summary='open', assignee=user.pk if user else 'unassigned')})

    activities = visible_to(SpaceTaskActivity.objects.all(), request.user).filter(task_id__in=items.order_by().values('task_id'), created_at__lte=now).select_related('actor', 'task__work_item').order_by('-created_at', '-pk')[:8]
    activity_rows = [{'actor': (activity.actor.get_full_name() or activity.actor.email) if activity.actor else 'System',
                      'avatar': account_avatar(activity.actor), 'action': activity.get_action_display(),
                      'created_at': activity.created_at, 'key': activity.task.work_item.key,
                      'title': activity.task.title, 'url': task_url(request, activity.task)} for activity in activities]

    epics = []
    if space.kind == 'software':
        epic_items = list(items.filter(work_type='epic').order_by('rank', 'pk'))
        child_counts = {row['epic_id']: row for row in items.filter(epic_id__in=[item.pk for item in epic_items]).order_by().values('epic_id').annotate(
            total=Count('pk'), closed=Count('pk', filter=Q(task__status='closed')),
        )}
        for item in epic_items:
            counts = child_counts.get(item.pk, {'total': 0, 'closed': 0})
            epics.append({'key': item.key, 'title': item.task.title, 'url': task_url(request, item.task),
                          **counts, 'percent': round(counts['closed'] * 100 / counts['total']) if counts['total'] else 0})

    return {'metrics': metrics, 'statuses': statuses, 'status_total': status_total,
            'priorities': priorities, 'priority_axis': {'max': priority_axis_max, 'middle': priority_axis_max / 2},
            'types': types, 'workload': workload,
            'activities': activity_rows, 'epics': epics, 'total': total, 'open_total': open_total,
            'list_url': list_url()}
