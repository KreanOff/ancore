"""Saved dashboards; sharing their configuration never grants data access."""
from django.db import transaction
from django.db.models import Count, Q

from spaces.services import visible_spaces
from tasks.access import visible_to
from tasks.models import Task
from workplaces.services import scoped_workplace_app_path, workspace_owner
from .models import Dashboard, DashboardGadget

MAX_GADGETS = 24
AVAILABLE_GADGET_KINDS = tuple(DashboardGadget.Kind)
GADGET_ICONS = {
    DashboardGadget.Kind.PROGRESS: 'chart-no-axes-combined',
}
GADGET_CATALOG = [
    {'kind': 'progress', 'name': 'Postęp pracy', 'category': 'charts', 'category_label': 'Statystyki',
     'description': 'Odsetek zamkniętych zadań, pasek postępu i liczby zadań w każdym statusie.'},
]
for entry in GADGET_CATALOG:
    entry['icon'] = GADGET_ICONS[entry['kind']]


def app_url(request, suffix=''):
    return scoped_workplace_app_path(request.workplace, 'dashboards', suffix) if request.workplace else f'/dashboards/{suffix}'


def visible_dashboards(request):
    return Dashboard.objects.filter(owner=workspace_owner(request), workplace=request.workplace).filter(
        Q(created_by=request.user) | Q(visibility='workspace') | Q(visibility='selected', shared_with=request.user),
    ).distinct()


@transaction.atomic
def default_dashboard(request):
    dashboard, created = Dashboard.objects.get_or_create(
        owner=workspace_owner(request), workplace=request.workplace,
        created_by=request.user, is_default=True,
        defaults={'name': 'Pulpit domyślny'},
    )
    if created:
        DashboardGadget.objects.create(dashboard=dashboard, kind=DashboardGadget.Kind.PROGRESS)
    return dashboard


def dashboard_url(request, dashboard):
    personal_default = dashboard.is_default and dashboard.created_by_id == request.user.pk
    return app_url(request, 'default/' if personal_default else f'{dashboard.pk}/')


def decorate_dashboard(request, dashboard):
    dashboard.url = dashboard_url(request, dashboard)
    dashboard.edit_url = app_url(request, f'{dashboard.pk}/edit/')
    dashboard.access_url = app_url(request, f'{dashboard.pk}/access/')
    dashboard.gadgets_url = app_url(request, f'{dashboard.pk}/gadgets/')
    dashboard.delete_url = app_url(request, f'{dashboard.pk}/delete/')
    dashboard.favorite_url = app_url(request, f'{dashboard.pk}/favorite/')
    dashboard.can_edit = dashboard.created_by_id == request.user.pk
    if not hasattr(dashboard, 'is_favorite'):
        dashboard.is_favorite = dashboard.favorited_by.filter(pk=request.user.pk).exists()
    return dashboard


def decorate_gadget(request, gadget):
    gadget.icon = GADGET_ICONS.get(gadget.kind, 'layout-dashboard')
    gadget.edit_url = app_url(request, f'{gadget.dashboard_id}/gadgets/{gadget.pk}/edit/')
    gadget.delete_url = app_url(request, f'{gadget.dashboard_id}/gadgets/{gadget.pk}/delete/')
    return gadget


def gadget_data(request, gadget, tasks, spaces):
    data = {'gadget': gadget, 'unavailable': False}
    # Match the existing Dashboard's progress card: count main tasks once.
    tasks = tasks.filter(parent__isnull=True)
    caption = 'Zadania we wszystkich przestrzeniach Workspace'
    if gadget.space_id:
        if gadget.space_id not in spaces:
            data['unavailable'] = True
            return data
        tasks = tasks.filter(work_item__space_id=gadget.space_id)
        caption = f'Zadania w przestrzeni {gadget.space.project.name}'
    if gadget.assignee == 'me':
        tasks = tasks.filter(assignee=request.user)
        caption += ' · Przypisane do oglądającego'
    elif gadget.assignee == 'unassigned':
        tasks = tasks.filter(assignee__isnull=True)
        caption += ' · Bez wykonawcy'
    counts = dict(tasks.order_by().values('status').annotate(count=Count('pk')).values_list('status', 'count'))
    total = sum(counts.values())
    closed = counts.get('closed', 0)
    data.update({
        'count': total, 'closed_count': closed, 'percent': round(100 * closed / total) if total else 0,
        'statuses': [{'key': key, 'label': label, 'count': counts.get(key, 0)} for key, label in Task.STATUS_CHOICES],
        'caption': caption,
    })
    return data


def detail_context(request, dashboard):
    decorate_dashboard(request, dashboard)
    tasks = visible_to(Task.objects.filter(user=workspace_owner(request), workplace=request.workplace), request.user)
    spaces = set(visible_spaces(request).values_list('pk', flat=True))
    columns = [[] for _ in range(dashboard.column_count)]
    for gadget in dashboard.gadgets.select_related('space__project'):
        decorate_gadget(request, gadget)
        columns[min(gadget.column, dashboard.column_count - 1)].append(gadget_data(request, gadget, tasks, spaces))
    return {'dashboard': dashboard, 'columns': columns, 'dashboards_url': app_url(request),
            'layout_choices': Dashboard.Layout.choices,
            'add_gadget_url': app_url(request, f'{dashboard.pk}/gadgets/add/'),
            'arrange_url': app_url(request, f'{dashboard.pk}/arrange/')}
