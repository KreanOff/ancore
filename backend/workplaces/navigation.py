from django.urls import reverse

from .services import scoped_workplace_app_path


SIDEBAR_FAVORITE_DEFINITIONS = (
    {'key': 'for-you', 'label': 'Dla ciebie', 'icon': 'user-round-check', 'app': 'for-you'},
    {'key': 'dashboard', 'label': 'Dashboard', 'icon': 'layout-dashboard', 'route_name': 'home'},
    {'key': 'pulpits', 'label': 'Pulpity', 'icon': 'layout-dashboard', 'app': 'dashboards'},
    {'key': 'filters', 'label': 'Filtry', 'icon': 'filter', 'app': 'filters'},
    {'key': 'spaces', 'label': 'Przestrzenie', 'icon': 'layers', 'app': 'spaces'},
    {'key': 'teams', 'label': 'Zespoły', 'icon': 'users', 'app': 'teams'},
    {'key': 'tasks-projects', 'label': 'Przestrzenie', 'icon': 'layers', 'app': 'spaces'},
    {'key': 'kanban-spaces', 'label': 'Przestrzenie', 'icon': 'layers', 'app': 'spaces'},
    {'key': 'kanban-boards', 'label': 'Przestrzenie', 'icon': 'layers', 'app': 'spaces'},
    {'key': 'calendar', 'label': 'Kalendarz', 'icon': 'calendar-days', 'app': 'calendar'},
    {'key': 'documents', 'label': 'Dysk', 'icon': 'hard-drive', 'app': 'documents'},
    {'key': 'office', 'label': 'Dokumenty', 'icon': 'file-text', 'app': 'office'},
    {'key': 'resources', 'label': 'Zasoby', 'icon': 'package', 'app': 'resources'},
)

SIDEBAR_FAVORITE_KEYS = frozenset(item['key'] for item in SIDEBAR_FAVORITE_DEFINITIONS)


def sidebar_favorite_catalog(workplace):
    from .policy import module_enabled
    catalog = {}
    for definition in SIDEBAR_FAVORITE_DEFINITIONS:
        if not module_enabled(workplace, definition.get('app', '')):
            continue
        item = definition.copy()
        if item.get('route_name'):
            item['url'] = reverse(item['route_name'])
        else:
            item['url'] = scoped_workplace_app_path(
                workplace,
                item['app'],
                item.get('suffix', ''),
                item.get('query', ''),
            ) if workplace else '/' + item['app'] + '/'
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
    if item_key == 'filters':
        return app_name in {'filters', 'workplace_filters'}

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

    return item_key == 'calendar' and app_name in {'planner', 'workplace_planner'}


def sidebar_favorites_for_request(request, workplace, favorite_keys):
    catalog = sidebar_favorite_catalog(workplace)
    active_view = request.GET.get('view', '').replace('-', '_') if hasattr(request, 'GET') else ''
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
