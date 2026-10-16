from django.db.models import Case, Exists, OuterRef, Q, When

from spaces.services import app_url
from workplaces.services import workspace_owner
from .models import SavedTaskFilter
from .recent import recent_views


def filter_url(request, suffix=''):
    return app_url(request, suffix, 'filters')


def visible_filters(request):
    return SavedTaskFilter.objects.filter(owner=workspace_owner(request), workplace=request.workplace).filter(
        Q(created_by=request.user) | Q(visibility='workspace') | Q(visibility='selected', shared_with=request.user),
    ).distinct()


def decorate_filter(request, item, favorites=None):
    item.url = filter_url(request, f'{item.pk}/')
    item.edit_url = item.url + 'edit/'
    item.favorite_url = item.url + 'favorite/'
    item.delete_url = item.url + 'delete/'
    item.editable = item.created_by_id == request.user.pk
    item.favorite = item.pk in favorites if favorites is not None else item.favorited_by.filter(pk=request.user.pk).exists()
    return item


def sidebar_filters(request, limit=6):
    favorites = SavedTaskFilter.favorited_by.through.objects.filter(
        savedtaskfilter_id=OuterRef('pk'), user_id=request.user.pk,
    )
    filters = visible_filters(request).annotate(is_favorite=Exists(favorites))
    starred = list(filters.filter(is_favorite=True).order_by('name', 'pk')[:limit])
    recent_ids = list(dict.fromkeys(
        entry['identity'][3] for entry in recent_views(request)
        if entry['identity'][2] == 'dashboard.savedtaskfilter'
    ))
    recent = filters.filter(is_favorite=False)
    if recent_ids:
        recent = recent.order_by(Case(
            *(When(pk=pk, then=position) for position, pk in enumerate(recent_ids)),
            default=len(recent_ids),
        ), '-created_at', '-pk')
    else:
        recent = recent.order_by('-created_at', '-pk')
    recent = list(recent[:max(0, limit - len(starred))])
    resolver = getattr(request, 'resolver_match', None)
    current = resolver.kwargs.get('pk') if resolver and resolver.app_name in {'filters', 'workplace_filters'} else None
    for item in [*starred, *recent]:
        decorate_filter(request, item, {item.pk} if item.is_favorite else set())
        item.current = item.pk == current
    return {'navigation_starred_filters': starred, 'navigation_recent_filters': recent}
