from django.urls import reverse

from .services import scoped_workplace_app_path


SIDEBAR_FAVORITE_DEFINITIONS = (
    {'key': 'for-you', 'label': 'Dla ciebie', 'icon': 'user-round-check', 'app': 'for-you'},
    {'key': 'dashboard', 'label': 'Dashboard', 'icon': 'layout-dashboard', 'route_name': 'home'},
    {'key': 'pulpits', 'label': 'Pulpity', 'icon': 'layout-dashboard', 'app': 'dashboards'},
    {'key': 'spaces', 'label': 'Przestrzenie', 'icon': 'layers', 'app': 'spaces'},
    {'key': 'teams', 'label': 'Zespoły', 'icon': 'users', 'app': 'teams'},
    {'key': 'tasks-all', 'label': 'Wszystkie zadania', 'icon': 'list-checks', 'app': 'spaces', 'suffix': 'items/'},
    {'key': 'tasks-projects', 'label': 'Przestrzenie', 'icon': 'layers', 'app': 'spaces'},
    {'key': 'kanban-spaces', 'label': 'Przestrzenie', 'icon': 'layers', 'app': 'spaces'},
    {'key': 'kanban-boards', 'label': 'Przestrzenie', 'icon': 'layers', 'app': 'spaces'},
    {'key': 'calendar', 'label': 'Kalendarz', 'icon': 'calendar-days', 'app': 'calendar'},
    {'key': 'tags', 'label': 'Tagi', 'icon': 'tag', 'app': 'tasks', 'query': 'view=tags'},
    {'key': 'documents', 'label': 'Dysk', 'icon': 'hard-drive', 'app': 'documents'},
    {'key': 'office', 'label': 'Dokumenty', 'icon': 'file-text', 'app': 'office'},
    {'key': 'resources', 'label': 'Zasoby', 'icon': 'package', 'app': 'resources'},
)

SIDEBAR_FAVORITE_KEYS = frozenset(item['key'] for item in SIDEBAR_FAVORITE_DEFINITIONS)


def sidebar_favorite_catalog(workplace):
    catalog = {}
    for definition in SIDEBAR_FAVORITE_DEFINITIONS:
        item = definition.copy()
        if item.get('route_name'):
            item['url'] = reverse(item['route_name'])
        else:
            item['url'] = scoped_workplace_app_path(
                workplace,
                item['app'],
                item.get('suffix', ''),
                item.get('query', ''),
            )
        catalog[item['key']] = item
    return catalog


def sidebar_favorite_is_active(item_key, request, active_view=''):
    resolver_match = getattr(request, 'resolver_match', None)
    app_name = getattr(resolver_match, 'app_name', '') or ''
    view_name = getattr(resolver_match, 'url_name', '') or ''

    if item_key in {'spaces', 'tasks-projects', 'kanban-spaces', 'kanban-boards'}:
        return app_name in {'spaces', 'workplace_spaces'} and view_name not in {'items', 'manage', 'manage_create', 'manage_edit'}
    if item_key == 'teams':
        return app_name in {'teams', 'workplace_teams'}
    if item_key == 'tasks-all' and app_name in {'spaces', 'workplace_spaces'}:
        return view_name == 'items'

    if item_key == 'for-you':
        return view_name in {'for_you', 'workplace_for_you'}

    if item_key == 'dashboard':
        return view_name == 'home' or getattr(request, 'sidebar_default_pulpit', False)

    if item_key == 'pulpits':
        return app_name in {'pulpits', 'workplace_pulpits'} and not getattr(request, 'sidebar_default_pulpit', False)

    if item_key == 'documents':
        return app_name in {'documents', 'workplace_documents'}

    if item_key == 'office':
        return app_name in {'office', 'workplace_office'}

    if item_key == 'resources':
        return app_name in {'resources', 'workplace_resources'}

    if item_key.startswith('tasks-') or item_key == 'tags':
        if app_name not in {'tasks', 'workplace_tasks', 'kanban', 'workplace_kanban'}:
            return False
        expected_view = {
            'tasks-my': 'unassigned_tasks',
            'tasks-all': ('all_tasks', 'unassigned_tasks'),
            'tasks-projects': ('projects', 'project'),
            'tasks-groups': ('all_groups', 'section'),
            'tags': 'tags',
        }.get(item_key)
        if item_key.startswith('tasks-') and app_name not in {'tasks', 'workplace_tasks'}:
            return False
        return active_view in expected_view if isinstance(expected_view, tuple) else active_view == expected_view

    if item_key.startswith('kanban-'):
        if app_name not in {'kanban', 'workplace_kanban'}:
            return False
        expected_view = {
            'kanban-spaces': ('projects', 'project'),
            'kanban-boards': ('all_groups', 'section'),
        }[item_key]
        return active_view in expected_view

    return item_key == 'calendar' and app_name in {'planner', 'workplace_planner'}


def sidebar_favorites_for_request(request, workplace, favorite_keys):
    catalog = sidebar_favorite_catalog(workplace)
    active_view = request.GET.get('view', '').replace('-', '_') if hasattr(request, 'GET') else ''
    resolver_match = getattr(request, 'resolver_match', None)
    app_name = getattr(resolver_match, 'app_name', '') or ''
    view_name = getattr(resolver_match, 'url_name', '') or ''
    if not active_view and app_name in {'tasks', 'workplace_tasks', 'kanban', 'workplace_kanban'}:
        active_view = 'section' if view_name == 'task_group' else 'projects'
    active_view = getattr(request, 'sidebar_active_view', active_view)
    items = []
    for key in favorite_keys:
        item = catalog.get(key)
        if not item:
            continue
        item['is_active'] = sidebar_favorite_is_active(
            key,
            request,
            active_view=active_view,
        )
        items.append(item)
    return items
