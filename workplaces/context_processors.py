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
    if active_workplace:
        workplace_app_urls = {
            'tasks': scoped_workplace_app_path(active_workplace, 'tasks'),
            'kanban': scoped_workplace_app_path(active_workplace, 'kanban'),
            'contacts': scoped_workplace_app_path(active_workplace, 'contacts'),
            'calendar': scoped_workplace_app_path(active_workplace, 'calendar'),
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
    }
