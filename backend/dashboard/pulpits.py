"""Saved dashboards; sharing their configuration never grants data access."""
from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery

from spaces.services import visible_items, visible_spaces
from spaces.access import visible_to
from spaces.models import SpaceTask
from workplaces.services import scoped_workplace_app_path, workspace_owner
from .models import Dashboard, DashboardGadget, DashboardMembership
from .filters import visible_filters
from .filter_search import QueryError, apply_query

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
    ).annotate(_viewer_role=Subquery(DashboardMembership.objects.filter(
        dashboard_id=OuterRef('pk'), user=request.user).values('role')[:1])).distinct()


def dashboard_role(request, dashboard):
    if dashboard.created_by_id == request.user.pk:
        return 'owner'
    if dashboard.visibility == Dashboard.Visibility.SELECTED:
        role = getattr(dashboard, '_viewer_role', None)
        if role is None:
            role = dashboard.memberships.filter(user=request.user).values_list('role', flat=True).first()
        return role if role in DashboardMembership.Role.values else ''
    return 'observer' if dashboard.visibility == Dashboard.Visibility.WORKSPACE else ''


def can_edit_dashboard(request, dashboard):
    return dashboard_role(request, dashboard) in {'owner', 'admin', 'member'}


def can_manage_dashboard(request, dashboard):
    return dashboard_role(request, dashboard) in {'owner', 'admin'}


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
    return app_url(request, 'default/' if personal_default else f'{dashboard.slug}/')


def decorate_dashboard(request, dashboard):
    dashboard.url = dashboard_url(request, dashboard)
    dashboard.edit_url = app_url(request, f'{dashboard.slug}/edit/')
    dashboard.access_url = app_url(request, f'{dashboard.slug}/access/')
    dashboard.gadgets_url = app_url(request, f'{dashboard.slug}/gadgets/')
    dashboard.delete_url = app_url(request, f'{dashboard.slug}/delete/')
    dashboard.favorite_url = app_url(request, f'{dashboard.slug}/favorite/')
    dashboard.can_edit = can_edit_dashboard(request, dashboard)
    dashboard.can_manage = can_manage_dashboard(request, dashboard)
    dashboard.can_delete = dashboard.created_by_id == request.user.pk and not dashboard.is_default
    if not hasattr(dashboard, 'is_favorite'):
        dashboard.is_favorite = dashboard.favorited_by.filter(pk=request.user.pk).exists()
    return dashboard


def decorate_gadget(request, gadget):
    gadget.icon = GADGET_ICONS.get(gadget.kind, 'layout-dashboard')
    gadget.edit_url = app_url(request, f'{gadget.dashboard.slug}/gadgets/{gadget.pk}/edit/')
    gadget.delete_url = app_url(request, f'{gadget.dashboard.slug}/gadgets/{gadget.pk}/delete/')
    return gadget


def dashboard_data_scope(request, dashboard, tasks, spaces):
    """Resolve defaults against the current viewer; unavailable sources never widen scope."""
    if dashboard.data_scope == Dashboard.DataScope.SPACES:
        selected = set(dashboard.scope_spaces.values_list('pk', flat=True)) & spaces
        return tasks.filter(space_id__in=selected), 'Zadania w wybranych Przestrzeniach pulpitu', not selected
    if dashboard.data_scope == Dashboard.DataScope.FILTER:
        source = visible_filters(request).filter(pk=dashboard.scope_filter_id).first()
        if source is not None:
            try:
                items, _ = apply_query(request, visible_items(request), source.query)
                return tasks.filter(work_item__in=items.values('pk')), f'Zadania z filtra {source.name}', False
            except QueryError:
                pass
        return tasks.none(), '', True
    return tasks, 'Zadania we wszystkich przestrzeniach Workspace', False


def gadget_data(request, gadget, tasks, spaces, scope=None):
    data = {'gadget': gadget, 'unavailable': False}
    # Match the existing Dashboard's progress card: count main tasks once.
    tasks = tasks.filter(parent__isnull=True)
    caption = 'Zadania we wszystkich przestrzeniach Workspace'
    if gadget.space_id:
        if gadget.space_id not in spaces:
            data['unavailable'] = True
            return data
        tasks = tasks.filter(work_item__space_id=gadget.space_id)
        caption = f'Zadania w przestrzeni {gadget.space.name}'
    else:
        tasks, caption, unavailable = scope or dashboard_data_scope(request, gadget.dashboard, tasks, spaces)
        if unavailable:
            data['unavailable'] = True
            return data
        tasks = tasks.filter(parent__isnull=True)
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
        'statuses': [{'key': key, 'label': label, 'count': counts.get(key, 0)} for key, label in SpaceTask.STATUS_CHOICES],
        'caption': caption,
    })
    return data


def detail_context(request, dashboard):
    decorate_dashboard(request, dashboard)
    tasks = visible_to(SpaceTask.objects.filter(space__user=workspace_owner(request), space__workplace=request.workplace), request.user)
    spaces = set(visible_spaces(request).values_list('pk', flat=True))
    scope = dashboard_data_scope(request, dashboard, tasks, spaces)
    columns = [[] for _ in range(dashboard.column_count)]
    for gadget in dashboard.gadgets.select_related('space'):
        decorate_gadget(request, gadget)
        columns[min(gadget.column, dashboard.column_count - 1)].append(gadget_data(request, gadget, tasks, spaces, scope))
    return {'dashboard': dashboard, 'columns': columns, 'dashboards_url': app_url(request),
            'layout_choices': Dashboard.Layout.choices,
            'add_gadget_url': app_url(request, f'{dashboard.slug}/gadgets/add/'),
            'arrange_url': app_url(request, f'{dashboard.slug}/arrange/')}
