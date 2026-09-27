"""Read-only summary of the owner's current Workspace."""

from datetime import datetime, time, timedelta
from urllib.parse import urlencode

from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.utils import timezone

from tasks.access import visible_to
from kanban.models import Kanban
from planner.models import CalendarEvent
from tasks.models import Task, TaskProject
from workplaces.services import scoped_workplace_app_path


OVERVIEW_LIMIT = 6


def dashboard_overview(user, workplace, focus='deadlines', viewer=None):
    now = timezone.now()
    today = timezone.localdate(now)
    start = timezone.make_aware(datetime.combine(today, time.min))
    end = timezone.make_aware(datetime.combine(today + timedelta(days=7), time.min))
    week_start = timezone.make_aware(datetime.combine(today - timedelta(days=6), time.min))
    focus = focus if focus in {'deadlines', 'priority', 'kanban'} else 'deadlines'
    tasks = visible_to(Task.objects.all(), viewer or user).filter(user=user, workplace=workplace, parent__isnull=True)
    cards = Kanban.objects.filter(user=user, workplace=workplace, parent__isnull=True)
    tasks_url = scoped_workplace_app_path(workplace, 'tasks')
    kanban_url = scoped_workplace_app_path(workplace, 'kanban')
    calendar_url = scoped_workplace_app_path(workplace, 'calendar')

    totals = {'total': 0, 'open': 0, 'priority': 0, 'closed_week': 0}
    statuses = {key: 0 for key, _label in Task.STATUS_CHOICES}
    for queryset in (tasks, cards):
        counts = queryset.aggregate(
            total=Count('pk'),
            open=Count('pk', filter=~Q(status='closed')),
            priority=Count('pk', filter=~Q(status='closed') & Q(priority__in=['urgent', 'high'])),
            closed_week=Count('pk', filter=Q(status='closed', completion_date__gte=week_start, completion_date__lte=now)),
        )
        for key, value in counts.items():
            totals[key] += value
        for row in queryset.values('status').annotate(count=Count('pk')):
            if row['status'] in statuses:
                statuses[row['status']] += row['count']
    totals['overdue'] = tasks.exclude(status='closed').filter(due_at__lt=now).count()

    priority_order = Case(
        When(priority='urgent', then=Value(0)),
        When(priority='high', then=Value(1)),
        When(priority='medium', then=Value(2)),
        When(priority='low', then=Value(3)),
        default=Value(4), output_field=IntegerField(),
    )
    open_tasks = tasks.exclude(status='closed').select_related('section__project')
    open_cards = cards.exclude(status='closed').select_related('section__project')
    if focus == 'kanban':
        selected = open_cards.order_by(priority_order, '-created_at', '-pk')
    elif focus == 'priority':
        selected = open_tasks.filter(priority__in=['urgent', 'high']).order_by(
            priority_order, F('due_at').asc(nulls_last=True), 'pk',
        )
    else:
        selected = open_tasks.filter(due_at__lt=end).order_by('due_at', 'pk')

    items = []
    for item in selected[:OVERVIEW_LIMIT]:
        app = 'kanban' if focus == 'kanban' else 'tasks'
        due = getattr(item, 'due_at', None)
        source = 'Kanban' if app == 'kanban' else 'Zadania'
        location = f'{source} · Bez grupy'
        if item.section_id:
            project = item.section.project
            if project.user_id == user.pk and project.workplace_id == workplace.pk:
                location = f'{project.name} · {item.section.title}'
        items.append({
            'object': item,
            'url': scoped_workplace_app_path(workplace, app, f'view-task/{item.task_id}/'),
            'location': location,
            'due_at': due,
            'overdue': bool(due and due < now),
            'due_today': bool(due and timezone.localdate(due) == today),
        })

    events = CalendarEvent.objects.filter(
        user=user, workplace=workplace, start__lt=end,
    ).filter(Q(end__gt=now) | Q(all_day=True, end__gt=start)).order_by('start', 'pk')
    event_count = events.count()
    agenda = [
        {'object': event, 'url': f'{calendar_url}?{urlencode({"event": event.pk})}'}
        for event in events[:4]
    ]

    # Linked tasks must satisfy the same ownership and Workspace rules.
    project_task_scope = Q(
        sections__tasks__user=user, sections__tasks__workplace=workplace,
        sections__tasks__parent__isnull=True,
    )
    projects = visible_to(TaskProject.objects.all(), viewer or user).filter(user=user, workplace=workplace).exclude(
        status__in=['completed', 'cancelled'],
    ).annotate(
        item_count=Count('sections__tasks', filter=project_task_scope),
        closed_count=Count('sections__tasks', filter=project_task_scope & Q(sections__tasks__status='closed')),
    ).order_by(F('due_at').asc(nulls_last=True), '-created_at', '-pk')
    project_count = projects.count()
    project_rows = []
    for project in projects[:4]:
        project_rows.append({
            'object': project,
            'percent': round(project.closed_count * 100 / project.item_count) if project.item_count else 0,
            'url': f'{tasks_url}?{urlencode({"project": project.pk})}',
        })

    return {
        'dashboard_today': today,
        'dashboard_totals': totals,
        'dashboard_focus': focus,
        'dashboard_items': items,
        'dashboard_item_count': selected.count(),
        'dashboard_statuses': [
            {'key': key, 'label': label, 'count': statuses[key]}
            for key, label in Task.STATUS_CHOICES
        ],
        'dashboard_completed_percent': round(statuses['closed'] * 100 / totals['total']) if totals['total'] else 0,
        'dashboard_closed_count': statuses['closed'],
        'dashboard_events': agenda,
        'dashboard_event_count': event_count,
        'dashboard_projects': project_rows,
        'dashboard_project_count': project_count,
        'dashboard_tasks_url': f'{tasks_url}?view=all-tasks',
        'dashboard_projects_url': tasks_url,
        'dashboard_kanban_url': f'{kanban_url}?view=all-tasks',
        'dashboard_calendar_url': f'{calendar_url}?date={today.isoformat()}',
    }
