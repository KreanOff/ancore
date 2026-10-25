from .services import scoped_workplace_app_path, workplaces_for_user
from .models import SidebarFavorite
from .navigation import sidebar_favorites_for_request


def current_workplace(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    user_workplaces = list(workplaces_for_user(user))
    active_workplace = getattr(request, 'workplace', None)
    workplace_app_urls = {}
    sidebar_favorite_keys = []
    sidebar_favorites = []
    space_navigation = {'navigation_spaces': [], 'navigation_starred_spaces': [], 'navigation_recent_spaces': []}
    dashboard_navigation = {'navigation_starred_dashboards': [], 'navigation_recent_dashboards': []}
    filter_navigation = {'navigation_starred_filters': [], 'navigation_recent_filters': []}
    resolver = getattr(request, 'resolver_match', None)
    pulpit_editor_mode = bool(
        resolver and resolver.app_name in {'pulpits', 'workplace_pulpits'}
        and resolver.url_name in {'edit', 'access', 'gadgets', 'gadget_add', 'gadget_edit',
                                  'manage_edit', 'manage_access', 'manage_gadgets', 'manage_gadget_add', 'manage_gadget_edit'}
    )
    pulpits_management_mode = pulpit_editor_mode
    sidebar_mode = 'settings' if resolver and resolver.view_name == 'settings' else (
        'pulpit-editor' if pulpit_editor_mode else 'workspace'
    )
    if active_workplace:
        from spaces.navigation import sidebar_spaces
        from dashboard.pulpit_navigation import sidebar_dashboards
        from dashboard.filters import sidebar_filters
        space_navigation = sidebar_spaces(request)
        dashboard_navigation = sidebar_dashboards(request)
        filter_navigation = sidebar_filters(request)
        request.sidebar_default_pulpit = dashboard_navigation['default_dashboard_is_current']
        workplace_app_urls = {
            'filters': scoped_workplace_app_path(active_workplace, 'filters'),
            'dashboards': scoped_workplace_app_path(active_workplace, 'dashboards'),
            'spaces': scoped_workplace_app_path(active_workplace, 'spaces'),
            'teams': scoped_workplace_app_path(active_workplace, 'teams'),
            'for_you': scoped_workplace_app_path(active_workplace, 'for-you'),
            'calendar': scoped_workplace_app_path(active_workplace, 'calendar'),
            'documents': scoped_workplace_app_path(active_workplace, 'documents'),
            'office': scoped_workplace_app_path(active_workplace, 'office'),
            'resources': scoped_workplace_app_path(active_workplace, 'resources'),
        }
        sidebar_favorite_keys = list(
            SidebarFavorite.objects.filter(user=user, workplace=active_workplace)
            .values_list('item_key', flat=True)
        )
        sidebar_favorites = sidebar_favorites_for_request(
            request,
            active_workplace,
            sidebar_favorite_keys,
        )

    return {
        'current_workplace': active_workplace,
        **space_navigation,
        **dashboard_navigation,
        **filter_navigation,
        'pulpits_management_mode': pulpits_management_mode,
        'pulpit_editor_mode': pulpit_editor_mode,
        'sidebar_mode': sidebar_mode,
        'available_workplaces': user_workplaces,
        'available_workplace_count': len(user_workplaces),
        'workplace_app_urls': workplace_app_urls,
        'sidebar_favorite_keys': sidebar_favorite_keys,
        'sidebar_favorites': sidebar_favorites,
    }
