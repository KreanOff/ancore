from django.urls import reverse

from .services import scoped_workplace_app_path


SIDEBAR_FAVORITE_DEFINITIONS = (
    {'key': 'dashboard', 'label': 'Dashboard', 'icon': 'layout-dashboard', 'route_name': 'home'},
    # Preserve the saved sidebar preference key when replacing the menu entry.
    {'key': 'tasks-my', 'label': 'Zadania nieprzydzielone', 'icon': 'user-round-check', 'app': 'tasks', 'query': 'view=unassigned-tasks'},
    {'key': 'tasks-all', 'label': 'Zadania', 'icon': 'list-checks', 'app': 'tasks', 'query': 'view=all-tasks'},
    {'key': 'tasks-projects', 'label': 'Projekty', 'icon': 'briefcase-business', 'app': 'tasks'},
    {'key': 'tasks-groups', 'label': 'Grupy', 'icon': 'layers-3', 'app': 'tasks', 'query': 'view=all-groups'},
    {'key': 'kanban-spaces', 'label': 'Przestrzenie robocze', 'icon': 'folders', 'app': 'kanban'},
    {'key': 'kanban-boards', 'label': 'Tablice', 'icon': 'kanban', 'app': 'kanban', 'query': 'view=all-groups'},
    {'key': 'contacts-all', 'label': 'Kontakty', 'icon': 'users', 'app': 'contacts'},
    {'key': 'contacts-companies', 'label': 'Firmy', 'icon': 'building-2', 'app': 'contacts', 'suffix': 'companies/'},
    {'key': 'contacts-guests', 'label': 'Goście', 'icon': 'user-round-alert', 'app': 'contacts', 'suffix': 'guests/'},
    {'key': 'calendar', 'label': 'Kalendarz', 'icon': 'calendar-days', 'app': 'calendar'},
    {'key': 'tags', 'label': 'Tagi', 'icon': 'tag', 'app': 'tasks', 'query': 'view=tags'},
    {'key': 'documents', 'label': 'Dysk', 'icon': 'hard-drive', 'app': 'documents'},
    {'key': 'office', 'label': 'Dokumenty', 'icon': 'file-text', 'app': 'office'},
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


def sidebar_favorite_is_active(item_key, request, active_view='', active_contact_status=''):
    resolver_match = getattr(request, 'resolver_match', None)
    app_name = getattr(resolver_match, 'app_name', '') or ''
    view_name = getattr(resolver_match, 'url_name', '') or ''

    if item_key == 'dashboard':
        return view_name == 'home'

    if item_key == 'documents':
        return app_name in {'documents', 'workplace_documents'}

    if item_key == 'office':
        return app_name in {'office', 'workplace_office'}

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

    if item_key.startswith('contacts-'):
        if app_name not in {'contacts', 'workplace_contacts'}:
            return False
        expected_status = {
            'contacts-all': 'all',
            'contacts-companies': 'companies',
            'contacts-guests': 'guests',
        }[item_key]
        return active_contact_status == expected_status

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
    contact_status_by_view = {
        'user-directory': 'users',
        'contacts': 'all',
        'view-contact': 'all',
        'companies': 'companies',
        'view-company': 'companies',
        'guests': 'guests',
    }
    active_contact_status = getattr(
        request,
        'sidebar_active_contact_status',
        contact_status_by_view.get(view_name, ''),
    )

    items = []
    for key in favorite_keys:
        item = catalog.get(key)
        if not item:
            continue
        item['is_active'] = sidebar_favorite_is_active(
            key,
            request,
            active_view=active_view,
            active_contact_status=active_contact_status,
        )
        items.append(item)
    return items
