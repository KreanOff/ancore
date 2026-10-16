"""Personal Kanban catalogs, after Workspace and visibility filtering."""
from django.db.models import Exists, OuterRef, Q

from tasks.directory import DIRECTORY_TABS, directory_tabs
from workplaces.services import scoped_workplace_app_path


def directory_tab(request):
    value = request.GET.get('tab', 'private')
    return value if value in dict(DIRECTORY_TABS) else 'private'


def directory_queryset(queryset, viewer, tab):
    """Call only after restricting the queryset to its Workspace and owner."""
    favorites = queryset.model.objects.filter(pk=OuterRef('pk'), favorited_by=viewer)
    queryset = queryset.annotate(is_favorite=Exists(favorites))
    if tab == 'favorites':
        return queryset.filter(is_favorite=True)
    private = Q(visibility='private', private_owner=viewer)
    public = Q(visibility='public')
    if queryset.model._meta.model_name == 'kanbansection':
        private |= Q(visibility='public', project__visibility='private', project__private_owner=viewer)
        public &= Q(project__visibility='public')
    if tab == 'private':
        return queryset.filter(private)
    if tab == 'public':
        return queryset.filter(public)
    return queryset.exclude(private).exclude(public)


def decorate_favorites(items, request, kind):
    for item in items:
        item.favorite_url = scoped_workplace_app_path(
            request.workplace, 'kanban', f'favorites/{kind}/{item.pk}/',
        )
