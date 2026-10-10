from .services import pending_invitations_for_user, scoped_workplace_app_path, workplaces_for_user
from .models import SidebarFavorite
from .navigation import sidebar_favorites_for_request
from dashboard.models import NotificationState


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
    spaces_management_available = False
    resolver = getattr(request, 'resolver_match', None)
    spaces_management_mode = bool(
        resolver
        and resolver.app_name in {'spaces', 'workplace_spaces'}
        and resolver.url_name in {'manage', 'manage_create', 'manage_edit'}
    )
    pulpits_management_mode = bool(
        resolver and resolver.app_name in {'pulpits', 'workplace_pulpits'}
        and (resolver.url_name in {'manage', 'edit', 'access', 'gadgets', 'gadget_add', 'gadget_edit'} or (resolver.url_name or '').startswith('manage_'))
    )
    pulpit_editor_mode = bool(
        resolver and resolver.app_name in {'pulpits', 'workplace_pulpits'}
        and resolver.url_name in {'edit', 'access', 'gadgets', 'gadget_add', 'gadget_edit',
                                  'manage_edit', 'manage_access', 'manage_gadgets', 'manage_gadget_add', 'manage_gadget_edit'}
    )
    sidebar_mode = 'settings' if resolver and resolver.view_name == 'settings' else (
        'administration' if spaces_management_mode else 'pulpit-editor' if pulpit_editor_mode else 'pulpits-management' if pulpits_management_mode else 'workspace'
    )
    if active_workplace:
        from spaces.services import can_manage_spaces
        from spaces.navigation import sidebar_spaces
        from dashboard.pulpit_navigation import sidebar_dashboards
        space_navigation = sidebar_spaces(request)
        dashboard_navigation = sidebar_dashboards(request)
        request.sidebar_default_pulpit = dashboard_navigation['default_dashboard_is_current']
        spaces_management_available = can_manage_spaces(request)
        workplace_app_urls = {
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
        'spaces_management_available': spaces_management_available,
        'spaces_management_mode': spaces_management_mode,
        'pulpits_management_mode': pulpits_management_mode,
        'pulpit_editor_mode': pulpit_editor_mode,
        'sidebar_mode': sidebar_mode,
        'available_workplaces': user_workplaces,
        'available_workplace_count': len(user_workplaces),
        'workplace_app_urls': workplace_app_urls,
        'sidebar_favorite_keys': sidebar_favorite_keys,
        'sidebar_favorites': sidebar_favorites,
        'pending_workspace_invitation_count': pending_invitations_for_user(user).count(),
        'pending_notification_invitation_count': pending_invitations_for_user(user).exclude(
            pk__in=NotificationState.objects.filter(user=user, is_deleted=True, invitation__isnull=False)
            .values('invitation_id'),
        ).count(),
    }
