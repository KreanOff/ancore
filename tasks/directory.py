"""Personal directory views; callers must first apply Workspace and visible_to."""
from django.db.models import Exists, OuterRef, Q

from workplaces.services import scoped_workplace_app_path

from .models import Task, TaskProject


DIRECTORY_TABS = (
    ('private', 'Prywatne'),
    ('shared', 'Udostępnione'),
    ('public', 'Publiczne'),
    ('favorites', 'Ulubione'),
)


def directory_tab(request):
    value = request.GET.get('tab', 'private')
    return value if value in dict(DIRECTORY_TABS) else 'private'


def directory_queryset(queryset, viewer, tab):
    favorites = queryset.model.objects.filter(pk=OuterRef('pk'), favorited_by=viewer)
    queryset = queryset.annotate(is_favorite=Exists(favorites))
    if tab == 'favorites':
        return queryset.filter(is_favorite=True)
    private = Q(visibility='private', private_owner=viewer)
    public = Q(visibility='public')
    if queryset.model is Task:
        # The task directory lists roots only. Public tasks inherit their group
        # and project audience; tasks without a group use their own visibility.
        private |= Q(visibility='public', section__visibility='private', section__private_owner=viewer)
        private |= Q(visibility='public', section__visibility='public',
                     section__project__visibility='private', section__project__private_owner=viewer)
        public &= Q(section__isnull=True) | Q(section__visibility='public', section__project__visibility='public')
    elif queryset.model is not TaskProject:
        # Public groups inherit the project's audience; private groups narrow it.
        private |= Q(visibility='public', project__visibility='private', project__private_owner=viewer)
        public &= Q(project__visibility='public')
    if tab == 'private':
        return queryset.filter(private)
    if tab == 'public':
        return queryset.filter(public)
    return queryset.exclude(private).exclude(public)


def directory_tabs(request, selected):
    params = request.GET.copy()
    params.pop('page', None)
    tabs = []
    for value, label in DIRECTORY_TABS:
        params['tab'] = value
        tabs.append({'value': value, 'label': label, 'active': value == selected,
                     'url': f'{request.path}?{params.urlencode()}'})
    return tabs


def decorate_favorites(items, request, kind):
    for item in items:
        item.favorite_url = scoped_workplace_app_path(
            request.workplace, 'tasks', f'favorites/{kind}/{item.pk}/',
        )
