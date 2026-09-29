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
    if tab == 'unassigned' and queryset.model is Task:
        return queryset.filter(section__isnull=True)
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


def directory_tabs(request, selected, *, include_unassigned=False):
    params = request.GET.copy()
    params.pop('page', None)
    tabs = []
    choices = DIRECTORY_TABS + (('unassigned', 'Nieprzydzielone'),) if include_unassigned else DIRECTORY_TABS
    for value, label in choices:
        if include_unassigned:
            params['view'] = 'unassigned-tasks' if value == 'unassigned' else 'all-tasks'
        if value == 'unassigned':
            params.pop('tab', None)
            params.pop('task_project', None)
            params.pop('task_section', None)
        else:
            params['tab'] = value
        tabs.append({'value': value, 'label': label, 'active': value == selected,
                     'url': f'{request.path}?{params.urlencode()}'})
    return tabs


def decorate_favorites(items, request, kind):
    for item in items:
        item.favorite_url = scoped_workplace_app_path(
            request.workplace, 'tasks', f'favorites/{kind}/{item.pk}/',
        )
