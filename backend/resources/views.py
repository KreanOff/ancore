from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from workplaces.services import scoped_workplace_app_path, workspace_owner
from .forms import ResourceForm
from .models import Resource


SORT_OPTIONS = [('name', 'Nazwa A–Z'), ('-name', 'Nazwa Z–A'), ('-created_at', 'Najnowsze'), ('expires_on', 'Termin ważności')]


def _scope(request):
    return Resource.objects.filter(owner=workspace_owner(request), workplace=request.workplace)


def _base_url(request):
    return scoped_workplace_app_path(request.workplace, 'resources') if request.workplace else reverse('resources:index')


def _params(request):
    params = {key: request.GET.get(key, '').strip() for key in ('q', 'kind', 'status', 'assignee', 'sort', 'page_size', 'page')}
    params['q'] = params['q'][:120]
    return {key: value for key, value in params.items() if value}


def _url(base, params):
    return base + ('?' + urlencode(params) if params else '')


def _context(request):
    params = _params(request)
    queryset = _scope(request).select_related('assigned_to')
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
    base = _base_url(request)
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
        'resources': rows, 'resources_url': base, 'list_url': _url(base, params), 'create_url': f'{base}create/{suffix}',
        'query': query, 'filters': filters, 'has_filters': bool(query or kind or status or assignee),
        'sort': sort, 'sort_label': dict(SORT_OPTIONS)[sort], 'sort_options': SORT_OPTIONS,
        'today': timezone.localdate(),
        'resource_window': {
            'page': page.number, 'total_pages': page.paginator.num_pages, 'page_size': size,
            'page_size_options': [25, 50, 100], 'summary': summary, 'compact_summary': summary,
            'has_previous': page.has_previous(), 'has_next': page.has_next(),
            'previous_url': _url(base, {**params, 'page': page.number - 1}) if page.has_previous() else '',
            'next_url': _url(base, {**params, 'page': page.number + 1}) if page.has_next() else '',
        },
    }


@login_required
@require_GET
def index(request):
    return render(request, 'resources/index.html', _context(request))


@login_required
@require_http_methods(['GET', 'POST'])
def edit(request, pk=None):
    owner = workspace_owner(request)
    item = get_object_or_404(_scope(request), pk=pk) if pk else Resource(owner=owner, workplace=request.workplace, created_by=request.user)
    form = ResourceForm(request.POST if request.method == 'POST' else None, instance=item, workplace=request.workplace)
    ajax = request.headers.get('X-Resource-Modal') == 'true'
    list_url = _url(_base_url(request), _params(request))
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                resource = form.save(commit=False)
                resource.updated_by = request.user
                resource.save()
        except IntegrityError as error:
            if getattr(error.__cause__, 'diag', None) and error.__cause__.diag.constraint_name == 'resource_inventory_unique':
                form.add_error('inventory_number', 'Zasób o tym numerze ewidencyjnym już istnieje w tym Workspace.')
            else:
                raise
        else:
            if ajax:
                return JsonResponse({'saved': True, 'url': list_url})
            messages.success(request, 'Zasób zapisany.')
            return redirect(list_url)
    modal = {'form': form, 'title': 'Edytuj zasób' if pk else 'Dodaj zasób', 'action': request.get_full_path(), 'return_url': list_url}
    if ajax:
        return JsonResponse({'html': render_to_string('resources/form.html', {'modal': modal}, request=request)}, status=400 if request.method == 'POST' else 200)
    context = _context(request)
    context['modal'] = modal
    return render(request, 'resources/index.html', context, status=400 if request.method == 'POST' else 200)


@login_required
@require_POST
def delete(request, pk):
    item = get_object_or_404(_scope(request), pk=pk)
    item.delete()
    url = _url(_base_url(request), _params(request))
    if request.headers.get('X-Resource-Modal') == 'true':
        return JsonResponse({'saved': True, 'url': url})
    messages.success(request, 'Zasób usunięty.')
    return redirect(url)
