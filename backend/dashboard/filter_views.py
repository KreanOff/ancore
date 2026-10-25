from urllib.parse import urlencode, urlsplit

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect
from core.frontend import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from spaces.services import visible_items
from spaces.views import decorate_items
from workplaces.services import workspace_owner
from .filter_forms import BasicTaskSearchForm, SavedTaskFilterForm, FilterSettingsForm
from .filter_search import Compiler, QueryError, apply_query, basic_query, parse_query
from .filters import can_edit_filter_query, can_manage_filter, decorate_filter, filter_url, visible_filters
from .models import SavedTaskFilter
from .recent import remember_view


def get_filter(request, pk, editable=False, lock=False):
    queryset = visible_filters(request)
    if lock:
        queryset = SavedTaskFilter.objects.filter(pk__in=queryset.values('pk')).select_for_update()
    item = get_object_or_404(queryset, pk=pk)
    if editable and not can_manage_filter(request, item):
        raise PermissionDenied
    return decorate_filter(request, item)


def directory_url(request, query=None):
    query = request.GET if query is None else query
    tab = query.get('tab', 'mine')
    params = {'tab': tab if tab in {'favorites', 'mine', 'shared', 'all'} else 'mine'}
    params.update({key: query[key] for key in ['q', 'page'] if query.get(key)})
    return filter_url(request) + '?' + urlencode(params)


def catalog_context(request, default_tab='favorites'):
    tab = request.GET.get('tab', default_tab)
    if tab not in {'favorites', 'mine', 'shared', 'all'}:
        tab = default_tab
    query = request.GET.get('q', '').strip()[:120]
    filters = visible_filters(request).select_related('created_by')
    if tab == 'favorites':
        filters = filters.filter(favorited_by=request.user)
    elif tab == 'mine':
        filters = filters.filter(created_by=request.user)
    elif tab == 'shared':
        filters = filters.exclude(created_by=request.user)
    if query:
        filters = filters.filter(Q(name__icontains=query) | Q(description__icontains=query))
    page = Paginator(filters.order_by('name', 'pk'), 30).get_page(request.GET.get('page'))
    rows = list(page.object_list)
    favorites = set(visible_filters(request).filter(favorited_by=request.user, pk__in=[row.pk for row in rows]).values_list('pk', flat=True))
    rows = [decorate_filter(request, row, favorites) for row in rows]
    return {'filters': rows, 'page': page,
            'tab': tab, 'query': query, 'filters_url': filter_url(request), 'search_url': filter_url(request, 'search/'),
            'list_url': request.get_full_path()}


def search_context(request, item=None):
    source = request.GET.get('jql', item.query if item else '').strip()
    error = ''
    mode = request.GET.get('mode', '')
    form = BasicTaskSearchForm(request=request, prefix=None)
    if request.GET.get('basic') == '1':
        form = BasicTaskSearchForm(request.GET, request=request)
        if form.is_valid():
            source = basic_query(form.cleaned_data)
        else:
            error = 'Popraw wybrane kryteria wyszukiwania.'
        mode = 'basic'
    items = visible_items(request)
    parsed = None
    try:
        items, parsed = apply_query(request, items, source)
    except QueryError as exception:
        error = str(exception)
    if error:
        items = items.none()
    basic = parsed.basic() if parsed else None
    basic_available = basic is not None
    if basic_available and request.GET.get('basic') != '1':
        # Values written by hand may use names; only offer lossless conversion.
        normalized = BasicTaskSearchForm(basic, request=request)
        basic_available = normalized.is_valid()
        if basic_available:
            form = BasicTaskSearchForm(initial=basic, request=request)
    mode = mode if mode in {'basic', 'advanced'} else 'basic' if basic_available else 'advanced'
    if mode == 'basic' and not basic_available and request.GET.get('basic') != '1':
        mode = 'advanced'
    page = Paginator(items, 50).get_page(request.GET.get('page'))
    base = item.url if item else filter_url(request, 'search/')
    encoded = urlencode({'jql': source})
    return {'saved_filter': item, 'items': decorate_items(request, page.object_list), 'page': page,
            'search_form': form, 'jql': source, 'search_error': error, 'mode': mode,
            'basic_available': basic_available, 'changed': bool(item and source != item.query),
            'search_url': base, 'filters_url': filter_url(request),
            'list_url': base + '?' + encoded + '&mode=' + mode,
            'clear_url': base + '?jql=&mode=basic',
            'save_as_url': filter_url(request, 'new/') + '?' + encoded,
            'basic_url': base + '?' + encoded + '&mode=basic',
            'advanced_url': base + '?' + encoded + '&mode=advanced',
            'can_save': not error}


@login_required
@require_GET
def index(request):
    return render(request, 'dashboard/filters/index.html', catalog_context(request))


@login_required
@require_GET
def manage(request):
    target = directory_url(request)
    if getattr(request, '_react_api', False):
        return JsonResponse({'redirect': target})
    return redirect(target)


@login_required
@require_GET
def search(request, pk=None):
    item = get_filter(request, pk) if pk else None
    if item:
        remember_view(request, item)
    context = search_context(request, item)
    response = render(request, 'dashboard/filters/search.html', context)
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
@require_GET
def lookup(request):
    query = request.GET.get('q', '').strip()[:120]
    results = list(visible_filters(request).filter(
        Q(name__icontains=query) | Q(description__icontains=query),
    ).order_by('name', 'pk')[:21]) if query else []
    if getattr(request, '_react_api', False):
        rows = [decorate_filter(request, item, set()) for item in results[:20]]
        return JsonResponse({'results': [{'id': str(item.pk), 'name': item.name, 'url': item.url,
                                         'detail': item.get_visibility_display()} for item in rows],
                             'count': len(rows), 'has_more': len(results) > 20})
    response = JsonResponse({
        'html': render_to_string('dashboard/filters/search_results.html', {
            'results': [decorate_filter(request, item, set()) for item in results[:20]],
            'has_more': len(results) > 20,
        }),
        'count': min(len(results), 20),
    })
    response['Cache-Control'] = 'private, no-store'
    return response


def mutation_response(request, url, saved=True):
    if request.headers.get('X-Filter-Modal') == 'true':
        return JsonResponse({'saved': saved, 'url': url})
    return redirect(url)


def return_url(request, fallback=None):
    value = request.POST.get('return_to', '')
    base = filter_url(request)
    try:
        parts = urlsplit(value)
    except ValueError:
        return fallback or base
    if not parts.scheme and not parts.netloc and parts.path.startswith((base, '/filters/')):
        if parts.path in {base + 'manage/', '/filters/manage/'}:
            return directory_url(request, QueryDict(parts.query))
        return value
    return fallback or base


@login_required
@require_http_methods(['GET', 'POST'])
def edit(request, pk=None, management=False):
    catalog = catalog_context(request, default_tab='mine') if management else None
    if catalog is not None:
        catalog['list_url'] = directory_url(request)
    with transaction.atomic():
        item = get_filter(request, pk, editable=True, lock=request.method == 'POST') if pk else None
        legacy = request.method == 'POST' and not getattr(request, '_react_api', False) and (not item or item.created_by_id == request.user.pk)
        form_type = SavedTaskFilterForm if legacy else FilterSettingsForm
        form = form_type(request.POST if request.method == 'POST' else None, request=request, instance=item,
                                   initial={'query': request.GET.get('jql', item.query if item else '')})
        if request.method == 'POST' and form.is_valid():
            if item and form.cleaned_data.get('revision') != item.revision:
                form.add_error(None, 'Filtr został zmieniony w innym oknie. Otwórz go ponownie przed zapisem.')
            else:
                saved = form.save(commit=False)
                if not item:
                    saved.owner = workspace_owner(request)
                    saved.workplace = request.workplace
                    saved.created_by = request.user
                saved.revision += 1
                saved.save()
                form.save_m2m()
                if saved.visibility != SavedTaskFilter.Visibility.SELECTED:
                    saved.shared_with.clear()
                if not item:
                    saved.favorited_by.add(request.user)
                target = return_url(request, catalog['list_url']) if management else filter_url(request, f'{saved.pk}/')
                if item and getattr(request, '_react_api', False):
                    from .filter_frontend import filter_form_payload
                    return JsonResponse({'redirect': target, 'form': filter_form_payload(
                        FilterSettingsForm(request=request, instance=saved))})
                if not item and getattr(request, '_react_api', False):
                    from .filter_frontend import modal_payload
                    return JsonResponse({'redirect': target, 'filter_modal': modal_payload(request, {
                        'list_url': target, 'modal': {'title': 'Ustawienia filtra',
                            'action': filter_url(request, f'{saved.pk}/edit/'),
                            'form': FilterSettingsForm(request=request, instance=saved)},
                    })})
                return mutation_response(request, target)
    modal = {'form': form, 'title': 'Ustawienia filtra' if item else 'Zapisz filtr', 'action': request.get_full_path()}
    context = catalog if management else search_context(request, item)
    context['modal'] = modal
    status = 400 if request.method == 'POST' else 200
    if request.headers.get('X-Filter-Modal') == 'true':
        return JsonResponse({'html': render_to_string('dashboard/filters/form.html', context, request=request)}, status=status)
    return render(request, 'dashboard/filters/index.html' if management else 'dashboard/filters/search.html', context, status=status)


@login_required
@require_POST
def save_query(request, pk):
    source = request.POST.get('jql', '').strip()
    with transaction.atomic():
        item = get_filter(request, pk, lock=True)
        if not can_edit_filter_query(request, item):
            raise PermissionDenied
        try:
            Compiler(request).expression(parse_query(source).expression)
        except QueryError as error:
            return JsonResponse({'error': str(error)}, status=400)
        if request.POST.get('revision') != str(item.revision):
            return JsonResponse({'error': 'Filtr został zmieniony w innym oknie. Odśwież go przed zapisem.'}, status=409)
        item.query = source
        item.revision += 1
        item.save(update_fields=['query', 'revision', 'updated_at'])
    return mutation_response(request, item.url)


@login_required
@require_POST
def favorite(request, pk):
    with transaction.atomic():
        item = get_filter(request, pk, lock=True)
        if item.favorite:
            item.favorited_by.remove(request.user)
        else:
            item.favorited_by.add(request.user)
    if request.headers.get('X-Filter-Navigation') == 'true':
        return JsonResponse({'saved': True})
    return mutation_response(request, return_url(request, item.url))


@login_required
@require_POST
def delete(request, pk):
    with transaction.atomic():
        item = get_filter(request, pk, editable=True, lock=True)
        if item.created_by_id != request.user.pk:
            raise PermissionDenied
        item.delete()
    messages.success(request, 'Filtr został usunięty.')
    return mutation_response(request, return_url(request, filter_url(request, '?tab=mine')))
