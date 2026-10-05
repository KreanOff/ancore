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
    spaces_management_available = False
    resolver = getattr(request, 'resolver_match', None)
    spaces_management_mode = bool(
        resolver
        and resolver.app_name in {'spaces', 'workplace_spaces'}
        and resolver.url_name in {'manage', 'manage_create', 'manage_edit'}
    )
    sidebar_mode = 'settings' if resolver and resolver.view_name == 'settings' else (
        'administration' if spaces_management_mode else 'workspace'
    )
    if active_workplace:
        from spaces.services import can_manage_spaces
        from spaces.navigation import sidebar_spaces
        space_navigation = sidebar_spaces(request)
        spaces_management_available = can_manage_spaces(request)
        workplace_app_urls = {
            'spaces': scoped_workplace_app_path(active_workplace, 'spaces'),
            'teams': scoped_workplace_app_path(active_workplace, 'teams'),
            'for_you': scoped_workplace_app_path(active_workplace, 'for-you'),
            'tasks': scoped_workplace_app_path(active_workplace, 'tasks'),
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
        'spaces_management_available': spaces_management_available,
        'spaces_management_mode': spaces_management_mode,
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
