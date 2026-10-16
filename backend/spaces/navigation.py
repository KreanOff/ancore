"""Personal space shortcuts, always rebuilt from the current access scope."""

from django.db.models import Case, Exists, OuterRef, When

from dashboard.recent import recent_views
from .models import Space
from .services import app_url, space_url, manageable_spaces, visible_spaces


def sidebar_spaces(request, limit=6):
    favorites = Space.favorited_by.through.objects.filter(
        space_id=OuterRef('pk'), user_id=request.user.pk,
    )
    spaces = visible_spaces(request).annotate(is_favorite=Exists(favorites))
    starred = list(spaces.filter(is_favorite=True).order_by('name', 'pk')[:limit])
    recent_ids = list(dict.fromkeys(
        entry['identity'][3] for entry in recent_views(request)
        if entry['identity'][2] == 'spaces.space'
    ))
    recent = spaces.filter(is_favorite=False)
    if recent_ids:
        recent = recent.order_by(Case(
            *(When(pk=pk, then=position) for position, pk in enumerate(recent_ids)),
            default=len(recent_ids),
        ), '-created_at', '-pk')
    else:
        recent = recent.order_by('-created_at', '-pk')
    recent = list(recent[:max(0, limit - len(starred))])
    navigation = [*starred, *recent]
    managed_ids = set(manageable_spaces(request).filter(pk__in=[s.pk for s in navigation]).values_list('pk', flat=True))
    for space in navigation:
        space.url = space_url(request, space)
        space.favorite_url = space.url + 'favorite/'
        space.settings_url = space.url + '?view=settings'
        space.can_manage = space.pk in managed_ids
    return {'navigation_spaces': navigation, 'navigation_starred_spaces': starred, 'navigation_recent_spaces': recent}
