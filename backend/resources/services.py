from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from workplaces.services import scoped_workplace_app_path, workspace_owner
from .models import Resource


SORT_OPTIONS = [('name', 'Nazwa A–Z'), ('-name', 'Nazwa Z–A'), ('-created_at', 'Najnowsze'), ('expires_on', 'Termin ważności')]


def resource_scope(request):
    return Resource.objects.filter(owner=workspace_owner(request), workplace=request.workplace)


def resource_base_url(request):
    return scoped_workplace_app_path(request.workplace, 'resources') if request.workplace else reverse('resources:index')


def resource_params(request):
    params = {key: request.GET.get(key, '').strip() for key in ('q', 'kind', 'status', 'assignee', 'sort', 'page_size', 'page')}
    params['q'] = params['q'][:120]
    return {key: value for key, value in params.items() if value}


def directory_url(base, params):
    return base + ('?' + urlencode(params) if params else '')


def directory_context(request):
    params = resource_params(request)
    queryset = resource_scope(request).select_related('assigned_to')
    query = params.get('q', '')
    if query:
        queryset = queryset.filter(Q(name__icontains=query) | Q(inventory_number__icontains=query) | Q(serial_number__icontains=query) | Q(location__icontains=query) | Q(notes__icontains=query))
    kind, status = params.get('kind', ''), params.get('status', '')
    if kind in Resource.Kind.values:
        queryset = queryset.filter(kind=kind)
    if status in Resource.Status.values:
        queryset = queryset.filter(status=status)
    assignee = params.get('assignee', '')
    if assignee == 'me':
        queryset = queryset.filter(assigned_to=request.user)
    elif assignee == 'unassigned':
        queryset = queryset.filter(assigned_to__isnull=True)
    sort = params.get('sort', 'name')
    if sort not in dict(SORT_OPTIONS):
        sort = 'name'
    size = int(params.get('page_size', '25')) if params.get('page_size') in {'25', '50', '100'} else 25
    page = Paginator(queryset.order_by(sort, 'pk'), size).get_page(params.get('page', 1))
    base = resource_base_url(request)
    suffix = '?' + urlencode(params) if params else ''
    rows = list(page.object_list)
    for item in rows:
        item.edit_url = f'{base}{item.pk}/edit/{suffix}'
        item.delete_url = f'{base}{item.pk}/delete/{suffix}'
    summary = f'{page.start_index()}–{page.end_index()} z {page.paginator.count}' if page.paginator.count else '0 z 0'
    filters = [
        {'name': 'kind', 'label': 'Typ', 'icon': 'package', 'value': kind, 'options': Resource.Kind.choices},
        {'name': 'status', 'label': 'Status', 'icon': 'circle-check', 'value': status, 'options': Resource.Status.choices},
        {'name': 'assignee', 'label': 'Przypisanie', 'icon': 'user-round', 'value': assignee, 'options': [('me', 'Przypisane do mnie'), ('unassigned', 'Nieprzypisane')]},
    ]
    for item in filters:
        item['selected_label'] = dict(item['options']).get(item['value'], '')
    return {
        'resources': rows, 'resources_url': base, 'list_url': directory_url(base, params), 'create_url': f'{base}create/{suffix}',
        'query': query, 'filters': filters, 'has_filters': bool(query or kind or status or assignee),
        'sort': sort, 'sort_label': dict(SORT_OPTIONS)[sort], 'sort_options': SORT_OPTIONS,
        'today': timezone.localdate(),
        'resource_window': {
            'page': page.number, 'total_pages': page.paginator.num_pages, 'page_size': size,
            'page_size_options': [25, 50, 100], 'summary': summary, 'compact_summary': summary,
            'has_previous': page.has_previous(), 'has_next': page.has_next(),
            'previous_url': directory_url(base, {**params, 'page': page.number - 1}) if page.has_previous() else '',
            'next_url': directory_url(base, {**params, 'page': page.number + 1}) if page.has_next() else '',
        },
    }


def save_resource_form(form, actor):
    """Share validation, author attribution and race handling between HTML and API."""
    if not form.is_valid():
        return False
    try:
        with transaction.atomic():
            resource = form.save(commit=False)
            resource.updated_by = actor
            resource.save()
    except IntegrityError as error:
        if getattr(error.__cause__, 'diag', None) and error.__cause__.diag.constraint_name == 'resource_inventory_unique':
            form.add_error('inventory_number', 'Zasób o tym numerze ewidencyjnym już istnieje w tym Workspace.')
        else:
            raise
        return False
    return True
