from datetime import timedelta
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q
from django.http import Http404
from django.urls import reverse
from django.utils import timezone

from workplaces.services import scoped_workplace_app_path, workspace_owner
from .models import Resource, ResourceActivity


SORT_OPTIONS = [('name', 'Nazwa A–Z'), ('-name', 'Nazwa Z–A'), ('-created_at', 'Najnowsze'), ('-updated_at', 'Ostatnio zmienione'), ('expires_on', 'Termin ważności'), ('return_due_on', 'Termin zwrotu')]
DEADLINE_OPTIONS = [('expired', 'Ważność: po terminie'), ('soon', 'Ważność: najbliższe 30 dni'), ('attention', 'Ważność: do 30 dni lub po terminie'), ('return_overdue', 'Zwrot: po terminie'), ('return_soon', 'Zwrot: najbliższe 7 dni'), ('no_expiry', 'Bez terminu ważności')]


def resource_scope(request):
    return Resource.objects.filter(owner=workspace_owner(request), workplace=request.workplace)


def resource_base_url(request):
    return scoped_workplace_app_path(request.workplace, 'resources') if request.workplace else reverse('resources:index')


def resource_params(request):
    params = {key: request.GET.get(key, '').strip() for key in ('q', 'kind', 'status', 'assignee', 'deadline', 'sort', 'page_size', 'page')}
    params['q'] = params['q'][:120]
    for key, allowed in [('kind', Resource.Kind.values), ('status', Resource.Status.values), ('assignee', ['me', 'unassigned']), ('deadline', dict(DEADLINE_OPTIONS))]:
        if params[key] not in allowed:
            params[key] = ''
    return {key: value for key, value in params.items() if value}


def directory_url(base, params):
    return base + ('?' + urlencode(params) if params else '')


def filtered_resources(request, params=None):
    params = resource_params(request) if params is None else params
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
    today = timezone.localdate()
    deadline = params.get('deadline', '')
    if deadline == 'no_expiry':
        queryset = queryset.filter(expires_on__isnull=True)
    elif deadline:
        queryset = queryset.exclude(status=Resource.Status.RETIRED)
        if deadline == 'expired':
            queryset = queryset.filter(expires_on__lt=today)
        elif deadline == 'soon':
            queryset = queryset.filter(expires_on__range=(today, today + timedelta(days=30)))
        elif deadline == 'attention':
            queryset = queryset.filter(expires_on__lte=today + timedelta(days=30))
        elif deadline == 'return_overdue':
            queryset = queryset.filter(status=Resource.Status.IN_USE, return_due_on__lt=today)
        elif deadline == 'return_soon':
            queryset = queryset.filter(status=Resource.Status.IN_USE, return_due_on__range=(today, today + timedelta(days=7)))
    sort = params.get('sort', 'name')
    if sort not in dict(SORT_OPTIONS):
        sort = 'name'
    order = F(sort).asc(nulls_last=True) if sort in {'expires_on', 'return_due_on'} else sort
    return queryset.order_by(order, 'pk')


def resource_summary(request):
    today = timezone.localdate()
    active = ~Q(status=Resource.Status.RETIRED)
    return resource_scope(request).aggregate(
        total=Count('pk'), available=Count('pk', filter=Q(status=Resource.Status.AVAILABLE)),
        in_use=Count('pk', filter=Q(status=Resource.Status.IN_USE)),
        maintenance=Count('pk', filter=Q(status=Resource.Status.MAINTENANCE)),
        attention=Count('pk', filter=active & Q(expires_on__lte=today + timedelta(days=30))),
        return_overdue=Count('pk', filter=Q(status=Resource.Status.IN_USE, return_due_on__lt=today)),
    )


def directory_context(request):
    params = resource_params(request)
    queryset = filtered_resources(request, params)
    query, kind, status, assignee, deadline = (params.get(key, '') for key in ('q', 'kind', 'status', 'assignee', 'deadline'))
    sort = params.get('sort', 'name')
    if sort not in dict(SORT_OPTIONS):
        sort = 'name'
    size = int(params.get('page_size', '25')) if params.get('page_size') in {'25', '50', '100'} else 25
    page = Paginator(queryset, size).get_page(params.get('page', 1))
    for key, value in [('page', page.number), ('page_size', size), ('sort', sort)]:
        if key in params:
            params[key] = str(value)
    base = resource_base_url(request)
    suffix = '?' + urlencode(params) if params else ''
    rows = list(page.object_list)
    for item in rows:
        item.edit_url = f'{base}{item.pk}/edit/{suffix}'
        item.delete_url = f'{base}{item.pk}/delete/{suffix}'
        item.detail_url = f'{base}{item.pk}/{suffix}'
    summary = f'{page.start_index()}–{page.end_index()} z {page.paginator.count}' if page.paginator.count else '0 z 0'
    filters = [
        {'name': 'kind', 'label': 'Typ', 'icon': 'package', 'value': kind, 'options': Resource.Kind.choices},
        {'name': 'status', 'label': 'Status', 'icon': 'circle-check', 'value': status, 'options': Resource.Status.choices},
        {'name': 'assignee', 'label': 'Przypisanie', 'icon': 'user-round', 'value': assignee, 'options': [('me', 'Przypisane do mnie'), ('unassigned', 'Nieprzypisane')]},
        {'name': 'deadline', 'label': 'Terminy', 'icon': 'calendar-clock', 'value': deadline, 'options': DEADLINE_OPTIONS},
    ]
    for item in filters:
        item['selected_label'] = dict(item['options']).get(item['value'], '')
    return {
        'resources': rows, 'resources_url': base, 'list_url': directory_url(base, params), 'create_url': f'{base}create/{suffix}',
        'query': query, 'filters': filters, 'has_filters': bool(query or kind or status or assignee or deadline),
        'resource_summary': resource_summary(request), 'export_url': f'{base}api/v1/export/{suffix}',
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


def resource_snapshot(resource):
    from .forms import ResourceForm
    values = {}
    for name in ResourceForm.Meta.fields:
        value = getattr(resource, name)
        if name == 'assigned_to':
            value = (value.get_full_name() or value.email) if value else ''
        elif name in {'kind', 'status'}:
            value = getattr(resource, f'get_{name}_display')()
        elif hasattr(value, 'isoformat'):
            value = value.isoformat()
        values[name] = {'value': resource.assigned_to_id if name == 'assigned_to' else str(value or ''), 'label': str(value or '')}
    return values


def record_activity(resource, actor, before, action, note=''):
    after = resource_snapshot(resource)
    changes = [
        {'field': name, 'label': str(Resource._meta.get_field(name).verbose_name), 'before': value['label'], 'after': after[name]['label']}
        for name, value in (before or {}).items() if value['value'] != after[name]['value']
    ]
    if before is not None and not changes and not note:
        return
    ResourceActivity.objects.create(resource=resource, actor=actor, actor_name=actor.get_full_name() or actor.email, action=action, changes=changes, note=note)


def save_resource_form(form, actor, revision=None):
    """Share validation, author attribution and race handling between HTML and API."""
    try:
        with transaction.atomic():
            previous = None
            if form.instance.pk:
                previous = Resource.objects.select_for_update().filter(pk=form.instance.pk, owner_id=form.instance.owner_id, workplace_id=form.instance.workplace_id).first()
                if previous is None:
                    raise Http404
                if revision and previous.updated_at.isoformat() != revision:
                    form.add_error(None, 'Ten zasób zmieniła inna osoba. Zamknij formularz i otwórz go ponownie, aby wczytać aktualne dane.')
                    return False
            before = resource_snapshot(previous) if previous else None
            if not form.is_valid():
                return False
            resource = form.save(commit=False)
            resource.updated_by = actor
            resource.save()
            record_activity(resource, actor, before, 'updated' if previous else 'created')
    except IntegrityError as error:
        if getattr(error.__cause__, 'diag', None) and error.__cause__.diag.constraint_name == 'resource_inventory_unique':
            form.add_error('inventory_number', 'Zasób o tym numerze ewidencyjnym już istnieje w tym Workspace.')
        else:
            raise
        return False
    return True
