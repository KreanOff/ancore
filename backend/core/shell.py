"""Explicit data contract for the React application shell and navigation."""
import json

from django.conf import settings
from django.contrib.messages import get_messages
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.templatetags.static import static
from django.urls import reverse

from accounts.avatar import account_avatar
from spaces.avatars import space_avatar
from workplaces.context_processors import current_workplace
from workplaces.navigation import sidebar_favorite_catalog, sidebar_favorite_is_active
from workplaces.templatetags.workplace_avatar import workplace_avatar
from workplaces.services import scoped_workplace_app_path


def build_id():
    return json.loads((settings.BASE_DIR / 'static/frontend/manifest.json').read_text())['main']


def favorite_items(request, workplace):
    from workplaces.models import SidebarFavorite
    catalog = sidebar_favorite_catalog(workplace)
    keys = SidebarFavorite.objects.filter(user=request.user, workplace=workplace).values_list('item_key', flat=True)
    return [dict(catalog[key], is_active=sidebar_favorite_is_active(key, request)) for key in keys if key in catalog]


def shell_payload(request, context=None):
    data = dict(context) if context and 'available_workplaces' in context else {**current_workplace(request), **(context or {})}
    workplace = request.workplace
    resolver = request.resolver_match
    app, view = resolver.app_name, resolver.url_name
    urls = data.get('workplace_app_urls', {})
    mode = data.get('sidebar_mode', 'workspace')
    if mode == 'pulpit-editor':
        mode = 'workspace'
    if app == 'workplaces':
        mode = 'workplaces'
    active_space = data.get('space')
    def space_row(item):
        return {'id': str(item.pk), 'name': item.name, 'url': item.url, 'avatar': space_avatar(item),
                'active': bool(active_space and active_space.pk == item.pk), 'favorite': bool(item.is_favorite),
                'favorite_url': item.favorite_url, 'settings_url': item.settings_url,
                'description': f'Przestrzeń {item.get_kind_display().lower()}', 'detail': item.get_management_display()}
    def pulpit_row(item):
        actions = [('Gadżety i układ', 'layout-dashboard', 'gadgets_url')] if item.can_edit else []
        if item.can_manage:
            actions += [('Ustawienia', 'settings', 'edit_url')]
        return {'id': str(item.pk), 'name': item.name, 'url': item.url, 'active': bool(item.is_current),
                'icon': item.icon, 'emoji': item.icon_emoji, 'emoji_art': item.icon_emoji_art,
                'favorite': bool(item.is_favorite), 'favorite_url': item.favorite_url,
                'actions': [{'label': label, 'icon': icon, 'url': getattr(item, field)} for label, icon, field in actions]}
    def filter_row(item):
        return {'id': str(item.pk), 'name': item.name, 'url': item.url, 'active': bool(item.current),
                'favorite': bool(item.favorite), 'favorite_url': item.favorite_url,
                'actions': [{'label': 'Ustawienia filtra i dostępy', 'icon': 'settings', 'url': item.edit_url}] if item.editable else []}
    collections = []
    for key, label, icon, url_key, namespace, search, starred, recent, serializer in (
        ('pulpits', 'Pulpity', 'layout-dashboard', 'dashboards', 'pulpits:index', 'search/', 'navigation_starred_dashboards', 'navigation_recent_dashboards', pulpit_row),
        ('spaces', 'Przestrzenie', 'layers', 'spaces', 'spaces:index', 'search/', 'navigation_starred_spaces', 'navigation_recent_spaces', space_row),
        ('filters', 'Filtry', 'filter', 'filters', 'filters:index', 'lookup/', 'navigation_starred_filters', 'navigation_recent_filters', filter_row),
    ):
        base = urls.get(url_key, reverse(namespace))
        collections.append({'key': key, 'label': label, 'icon': icon, 'url': base,
                            'directory_url': base + ('?tab=all' if key == 'filters' else ''), 'search_url': base + search,
                            'create_url': base + ('new/' if key == 'filters' else 'create/'),
                            'task_search_url': base + 'search/' if key == 'filters' else '',
                            'starred': [serializer(item) for item in data.get(starred, [])],
                            'recent': [serializer(item) for item in data.get(recent, [])]})
    catalog = sidebar_favorite_catalog(workplace)
    links = {key: {**item, 'is_active': sidebar_favorite_is_active(key, request)} for key, item in catalog.items()}
    from workplaces.policy import module_enabled, read_only
    links = {key: item for key, item in links.items() if module_enabled(workplace, item.get('app', ''))}
    collections = [item for item in collections if module_enabled(workplace, {'pulpits': 'dashboards'}.get(item['key'], item['key']))]
    for item in collections:
        if read_only(request):
            item['create_url'] = ''
            for row in item['starred'] + item['recent']:
                row['settings_url'] = ''
                row['actions'] = []
    return {
        'account_id': str(request.user.pk), 'workplace_id': str(workplace.pk) if workplace else '',
        'read_only': read_only(request), 'disabled_modules': workplace.disabled_modules if workplace else [],
        'mode': mode, 'url': request.get_full_path(),
        'space_settings': data.get('space_settings_sidebar'),
        'pulpit_settings': data.get('pulpit_settings_sidebar'),
        'navigation_url': scoped_workplace_app_path(workplace, 'api', 'v1/navigation/') if workplace else reverse('react-navigation'),
        'refresh_url': scoped_workplace_app_path(workplace, 'api', 'v1/shell/') if workplace else reverse('react-shell'), 'build_id': build_id(),
        'workplaces': [{'id': str(item.pk), 'name': item.name, 'avatar': workplace_avatar(item),
                        'switch_url': reverse('workplaces:switch', args=[item.pk])} for item in data['available_workplaces']],
        'profile': {'name': request.user.get_full_name() or request.user.username, 'avatar': account_avatar(request.user),
                    'url': reverse('profile'), 'active': resolver.view_name == 'profile'},
        'settings_url': reverse('settings'), 'settings_active': mode in {'space-settings', 'pulpit-settings'} or resolver.view_name == 'settings' or app == 'workplaces' or data.get('pulpits_management_mode', False),
        'workplaces_url': reverse('workplaces:workplaces'), 'links': links,
        'favorites': favorite_items(request, workplace) if workplace else [],
        'favorite_toggle_url': reverse('workplaces:toggle-sidebar-favorite', args=[workplace.pk]) if workplace else '',
        'favorite_reorder_url': reverse('workplaces:reorder-sidebar-favorites', args=[workplace.pk]) if workplace else '',
        'collections': collections, 'default_pulpit_url': data.get('default_dashboard_url', reverse('home')),
        'default_pulpit_icon': data.get('default_dashboard_icon', 'layout-dashboard'),
        'default_pulpit_emoji': data.get('default_dashboard_emoji', 'layout-dashboard'),
        'default_pulpit_emoji_art': data.get('default_dashboard_emoji_art'),
        'default_pulpit_active': bool(data.get('default_dashboard_is_current')),
        'filter_search_active': app in {'filters', 'workplace_filters'} and view == 'search',
        'editor': {'title': getattr(data.get('dashboard'), 'name', 'Edycja pulpitu'),
                   'return_url': data.get('return_url') or urls.get('dashboards', reverse('pulpits:index')),
                   'links': data.get('pulpit_editor_navigation', [])},
    }


def messages_payload(request):
    return [{'message': str(item), 'type': item.tags or 'info'} for item in get_messages(request)]


def page_styles(page):
    # Keep the existing cascade order; no legacy module controller is loaded on navigation.
    names = ['components/documents.css', 'components/resources.css', 'components/spaces.css']
    kind = page['type']
    if kind.startswith('pulpit') or kind == 'for-you':
        names += ['components/dashboard.css', 'components/pulpits.css']
    if kind.startswith('filter') or kind == 'form':
        names += ['components/task-filters.css', 'components/pulpits.css']
    if kind == 'settings':
        names += ['components/settings.css']
    if kind == 'workspace-directory' or kind.startswith(('space-', 'pulpit', 'filter')) or kind == 'form':
        names += ['components/workplace-team.css']
    if kind.startswith(('document', 'office')):
        names += ['components/office.css']
    return [static('css/' + name) + '?v=' + str((settings.BASE_DIR / 'static/css' / name).stat().st_mtime_ns) for name in names]


def navigation_response(request, page, context=None, status=200):
    page['styles'] = page_styles(page)
    return JsonResponse({'page': page, 'shell': shell_payload(request, context),
                         'csrf_token': get_token(request), 'messages': messages_payload(request)}, status=status)
