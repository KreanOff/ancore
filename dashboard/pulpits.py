"""Saved dashboards; sharing their configuration never grants data access."""
from django.db.models import Count, F, Q
from django.utils import timezone

from spaces.services import visible_spaces
from tasks.access import visible_to
from tasks.models import Task, TaskActivity
from workplaces.services import scoped_workplace_app_path, workspace_owner
from .models import Dashboard, DashboardGadget, DashboardGroup

MAX_GADGETS = 24


def app_url(request, suffix=''):
    return scoped_workplace_app_path(request.workplace, 'dashboards', suffix) if request.workplace else f'/dashboards/{suffix}'


def visible_dashboards(request):
    return Dashboard.objects.filter(owner=workspace_owner(request), workplace=request.workplace).filter(
        Q(created_by=request.user) | Q(visibility='workspace') | Q(visibility='selected', shared_with=request.user),
    ).distinct()


def personal_groups(request):
    return DashboardGroup.objects.filter(owner=workspace_owner(request), workplace=request.workplace, user=request.user)


def decorate_dashboard(request, dashboard):
    dashboard.url = app_url(request, f'{dashboard.pk}/')
    dashboard.edit_url = app_url(request, f'{dashboard.pk}/edit/')
    dashboard.copy_url = app_url(request, f'{dashboard.pk}/copy/')
    dashboard.delete_url = app_url(request, f'{dashboard.pk}/delete/')
    dashboard.favorite_url = app_url(request, f'{dashboard.pk}/favorite/')
    dashboard.groups_url = app_url(request, f'{dashboard.pk}/groups/')
    dashboard.can_edit = dashboard.created_by_id == request.user.pk
    if not hasattr(dashboard, 'is_favorite'):
        dashboard.is_favorite = dashboard.favorited_by.filter(pk=request.user.pk).exists()
    return dashboard


def task_url(request, task):
    base = scoped_workplace_app_path(request.workplace, 'tasks')
    return f'{base}view-task/{task.task_id}/?task_pk={task.pk}'


def gadget_data(request, gadget, tasks, spaces):
    data = {'gadget': gadget, 'rows': [], 'unavailable': False}
    if gadget.space_id:
        if gadget.space_id not in spaces:
            data['unavailable'] = True
            return data
        tasks = tasks.filter(work_item__space_id=gadget.space_id)
    if gadget.status:
        tasks = tasks.filter(status=gadget.status)
    if gadget.assignee == 'me' or gadget.kind == DashboardGadget.Kind.ASSIGNED:
        tasks = tasks.filter(assignee=request.user)
    elif gadget.assignee == 'unassigned':
        tasks = tasks.filter(assignee__isnull=True)
    if gadget.kind == DashboardGadget.Kind.ASSIGNED:
        tasks = tasks.exclude(status='closed')
    data['count'] = tasks.count()
    if gadget.kind == DashboardGadget.Kind.SUMMARY:
        data['totals'] = tasks.aggregate(
            total=Count('pk'), open=Count('pk', filter=~Q(status='closed')),
            closed=Count('pk', filter=Q(status='closed')),
            overdue=Count('pk', filter=~Q(status='closed') & Q(due_at__lt=timezone.now())),
        )
    elif gadget.kind == DashboardGadget.Kind.STATISTICS:
        group = gadget.group_by if gadget.group_by in {'status', 'priority', 'assignee'} else 'status'
        fields = ['assignee_id', 'assignee__first_name', 'assignee__last_name', 'assignee__email'] if group == 'assignee' else [group]
        labels = dict(Task.STATUS_CHOICES if group == 'status' else Task.PRIORITY_CHOICES)
        for row in tasks.order_by().values(*fields).annotate(count=Count('pk')).order_by('-count', *fields)[:20]:
            label = labels.get(row.get(group), row.get(group, ''))
            if group == 'assignee':
                label = (' '.join(filter(None, [row['assignee__first_name'], row['assignee__last_name']])).strip() or row['assignee__email']) if row['assignee_id'] else 'Bez wykonawcy'
            data['rows'].append({'label': label, 'count': row['count'], 'percent': round(100 * row['count'] / data['count'])})
    elif gadget.kind == DashboardGadget.Kind.ACTIVITY:
        activity = visible_to(TaskActivity.objects.filter(task__in=tasks), request.user).select_related('task', 'actor').order_by('-created_at', '-pk')
        data['count'] = activity.count()
        for row in activity[:gadget.limit]:
            data['rows'].append({'title': row.task.title, 'url': task_url(request, row.task), 'action': row.get_action_display(), 'actor': row.actor.get_full_name() or row.actor.email if row.actor else 'System', 'date': row.created_at})
    else:
        for task in tasks.select_related('assignee', 'work_item').order_by(F('due_at').asc(nulls_last=True), '-created_at', '-pk')[:gadget.limit]:
            data['rows'].append({'task': task, 'url': task_url(request, task), 'key': task.work_item.key if hasattr(task, 'work_item') else f'TASK-{task.pk}', 'overdue': bool(task.due_at and task.due_at < timezone.now() and task.status != 'closed')})
    return data


def detail_context(request, dashboard):
    decorate_dashboard(request, dashboard)
    tasks = visible_to(Task.objects.filter(user=workspace_owner(request), workplace=request.workplace), request.user)
    spaces = set(visible_spaces(request).values_list('pk', flat=True))
    columns = [[] for _ in range(dashboard.column_count)]
    for gadget in dashboard.gadgets.all():
        gadget.edit_url = app_url(request, f'{dashboard.pk}/gadgets/{gadget.pk}/edit/')
        gadget.delete_url = app_url(request, f'{dashboard.pk}/gadgets/{gadget.pk}/delete/')
        columns[min(gadget.column, dashboard.column_count - 1)].append(gadget_data(request, gadget, tasks, spaces))
    return {'dashboard': dashboard, 'columns': columns, 'dashboards_url': app_url(request),
            'layout_choices': Dashboard.Layout.choices,
            'add_gadget_url': app_url(request, f'{dashboard.pk}/gadgets/add/'),
            'arrange_url': app_url(request, f'{dashboard.pk}/arrange/')}
