from .services import pending_invitations_for_user, scoped_workplace_app_path, workplaces_for_user
from .models import SidebarFavorite
from .navigation import sidebar_favorites_for_request
from dashboard.models import NotificationState
from tasks.sharing import pending_project_invitations


def current_workplace(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    user_workplaces = list(workplaces_for_user(user))
    active_workplace = getattr(request, 'workplace', None)
    workplace_app_urls = {}
    sidebar_favorite_keys = []
    sidebar_favorites = []
    if active_workplace:
        workplace_app_urls = {
            'tasks': scoped_workplace_app_path(active_workplace, 'tasks'),
            'kanban': scoped_workplace_app_path(active_workplace, 'kanban'),
            'contacts': scoped_workplace_app_path(active_workplace, 'contacts'),
            'calendar': scoped_workplace_app_path(active_workplace, 'calendar'),
            'documents': scoped_workplace_app_path(active_workplace, 'documents'),
            'office': scoped_workplace_app_path(active_workplace, 'office'),
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
        'available_workplaces': user_workplaces,
        'available_workplace_count': len(user_workplaces),
        'workplace_app_urls': workplace_app_urls,
        'sidebar_favorite_keys': sidebar_favorite_keys,
        'sidebar_favorites': sidebar_favorites,
        'pending_workspace_invitation_count': pending_invitations_for_user(user).count(),
        'pending_notification_invitation_count': pending_invitations_for_user(user).exclude(
            pk__in=NotificationState.objects.filter(user=user, is_deleted=True, invitation__isnull=False)
            .values('invitation_id'),
        ).count() + pending_project_invitations(user).exclude(
            pk__in=NotificationState.objects.filter(user=user, is_deleted=True, project_invitation__isnull=False)
            .values('project_invitation_id'),
        ).count(),
    }
