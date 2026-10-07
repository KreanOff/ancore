import json
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.utils.http import url_has_allowed_host_and_scheme

from workplaces.services import workspace_owner
from accounts.avatar import account_avatar
from spaces.services import visible_spaces
from tasks.access import visible_to
from tasks.models import Task
from .models import Dashboard, DashboardGadget
from .pulpit_forms import DashboardAccessForm, DashboardForm, DashboardSettingsForm, GadgetForm
from .pulpits import (GADGET_CATALOG, MAX_GADGETS, app_url, decorate_dashboard, decorate_gadget,
                      detail_context, gadget_data, visible_dashboards)
from .recent import remember_view


def get_dashboard(request, pk, edit=False, lock=False):
    queryset = visible_dashboards(request)
    if lock:
        # Lock the base table, avoiding DISTINCT / M2M joins in FOR UPDATE.
        queryset = Dashboard.objects.filter(pk__in=queryset.values('pk')).select_for_update()
    dashboard = get_object_or_404(queryset, pk=pk)
    if edit and dashboard.created_by_id != request.user.pk:
        raise PermissionDenied('Tylko twórca może zmieniać pulpit.')
    return dashboard


def index_context(request):
    tab = request.GET.get('tab', 'favorites')
    if tab not in {'favorites', 'mine', 'all'}:
        tab = 'favorites'
    query = request.GET.get('q', '').strip()[:120]
    queryset = visible_dashboards(request).select_related('created_by').annotate(gadget_count=Count('gadgets', distinct=True))
    if tab == 'favorites':
        queryset = queryset.filter(favorited_by=request.user)
    elif tab == 'mine':
        queryset = queryset.filter(created_by=request.user)
    if query:
        queryset = queryset.filter(Q(name__icontains=query) | Q(description__icontains=query))
    page = Paginator(queryset.order_by('name', 'pk'), 25).get_page(request.GET.get('page'))
    rows = [decorate_dashboard(request, row) for row in page]
    base = app_url(request)
    filters = {'q': query}
    return {'dashboards': rows, 'page': page, 'tab': tab, 'query': query, 'dashboards_url': base,
            'create_url': app_url(request, 'create/'),
            'tabs': [{'key': key, 'label': label, 'url': base + '?' + urlencode({'tab': key, **filters})} for key, label in [('favorites', 'Ulubione'), ('mine', 'Moje'), ('all', 'Wszystkie')]],
            'previous_url': base + '?' + urlencode({'tab': tab, **filters, 'page': page.number - 1}),
            'next_url': base + '?' + urlencode({'tab': tab, **filters, 'page': page.number + 1})}


@login_required
@require_GET
def index(request):
    return render(request, 'dashboard/pulpits/index.html', index_context(request))


def management_url(request, suffix=''):
    filters = {key: request.GET[key] for key in ['q', 'visibility', 'favorite', 'page'] if request.GET.get(key)}
    return app_url(request, 'manage/' + suffix) + ('?' + urlencode(filters) if filters else '')


def management_context(request):
    query = request.GET.get('q', '').strip()[:120]
    visibility = request.GET.get('visibility', '')
    favorite_filter = request.GET.get('favorite', '')
    favorites = Dashboard.favorited_by.through.objects.filter(dashboard_id=OuterRef('pk'), user_id=request.user.pk)
    queryset = visible_dashboards(request).filter(created_by=request.user).select_related('created_by').annotate(
        gadget_count=Count('gadgets', distinct=True), is_favorite=Exists(favorites),
    )
    if query:
        queryset = queryset.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if visibility in Dashboard.Visibility.values:
        queryset = queryset.filter(visibility=visibility)
    else:
        visibility = ''
    if favorite_filter in {'starred', 'unstarred'}:
        queryset = queryset.filter(is_favorite=favorite_filter == 'starred')
    else:
        favorite_filter = ''
    page = Paginator(queryset.order_by('name', 'pk'), 30).get_page(request.GET.get('page'))
    for dashboard in page:
        decorate_dashboard(request, dashboard)
        dashboard.creator_avatar = account_avatar(dashboard.created_by)
        dashboard.edit_url = management_url(request, f'{dashboard.pk}/edit/')
        dashboard.access_url = management_url(request, f'{dashboard.pk}/access/')
        dashboard.gadgets_url = management_url(request, f'{dashboard.pk}/gadgets/')
        dashboard.copy_url = management_url(request, f'{dashboard.pk}/copy/')
        dashboard.delete_url = management_url(request, f'{dashboard.pk}/delete/')
    return {'page': page, 'query': query, 'visibility_filter': visibility, 'favorite_filter': favorite_filter,
            'visibility_choices': Dashboard.Visibility.choices, 'management_url': app_url(request, 'manage/'),
            'return_url': management_url(request), 'create_url': management_url(request, 'create/')}


@login_required
@require_GET
def manage(request):
    return render(request, 'dashboard/pulpits/manage.html', management_context(request))


@login_required
@require_GET
def detail(request, pk):
    dashboard = get_dashboard(request, pk)
    remember_view(request, dashboard)
    return render(request, 'dashboard/pulpits/detail.html', detail_context(request, dashboard))


def editor_navigation_context(request, dashboard, section, management=False):
    decorate_dashboard(request, dashboard)
    sections = [
        {'key': 'gadgets', 'suffix': 'gadgets/', 'label': 'Gadżety i układ', 'icon': 'layout-dashboard'},
        {'key': 'access', 'suffix': 'access/', 'label': 'Dostępy', 'icon': 'users'},
        {'key': 'settings', 'suffix': 'edit/', 'label': 'Ustawienia', 'icon': 'settings'},
    ]
    for entry in sections:
        suffix = f'{dashboard.pk}/' + entry.pop('suffix')
        entry['url'] = management_url(request, suffix) if management else app_url(request, suffix)
        entry['active'] = entry['key'] == section
    return {
        'dashboard': dashboard, 'pulpit_editor_navigation': sections,
        'section_title': next(entry['label'] for entry in sections if entry['active']),
        'editor_url': sections[0]['url'], 'access_url': sections[1]['url'], 'settings_url': sections[2]['url'],
        'return_url': management_url(request) if management else dashboard.url,
    }


def editor_context(request, dashboard, management=False):
    context = detail_context(request, dashboard)
    context.update(editor_navigation_context(request, dashboard, 'gadgets', management))
    context.update({
        'editing_gadgets': True,
        'add_gadget_url': management_url(request, f'{dashboard.pk}/gadgets/add/') if management else context['add_gadget_url'],
        'gadget_count': dashboard.gadgets.count(), 'max_gadgets': MAX_GADGETS,
        'gadget_catalog': GADGET_CATALOG,
        'quick_add_url': management_url(request, f'{dashboard.pk}/gadgets/quick-add/') if management else app_url(request, f'{dashboard.pk}/gadgets/quick-add/'),
    })
    if management:
        for column in context['columns']:
            for data in column:
                gadget = data['gadget']
                gadget.edit_url = management_url(request, f'{dashboard.pk}/gadgets/{gadget.pk}/edit/')
                gadget.delete_url = management_url(request, f'{dashboard.pk}/gadgets/{gadget.pk}/delete/')
    return context


@login_required
@require_GET
def gadgets(request, pk, management=False):
    dashboard = get_dashboard(request, pk, edit=True)
    return render(request, 'dashboard/pulpits/gadgets.html', editor_context(request, dashboard, management))


def form_response(request, form, title, return_url, dashboard=None, gadget=False, status=200, management=False):
    modal = {'form': form, 'title': title, 'action': request.get_full_path(), 'return_url': return_url, 'gadget': gadget}
    if request.headers.get('X-Pulpit-Modal') == 'true':
        return JsonResponse({'html': render_to_string('dashboard/pulpits/form.html', {'modal': modal}, request=request)}, status=status)
    if gadget:
        context = editor_context(request, dashboard, management)
        template = 'dashboard/pulpits/gadgets.html'
    elif management:
        context = management_context(request)
        template = 'dashboard/pulpits/manage.html'
    elif dashboard:
        context = detail_context(request, dashboard)
        template = 'dashboard/pulpits/detail.html'
    else:
        context = index_context(request)
        template = 'dashboard/pulpits/index.html'
    context['modal'] = modal
    context['return_url'] = return_url
    return render(request, template, context, status=status)


def saved_response(request, url):
    if request.headers.get('X-Pulpit-Modal') == 'true':
        return JsonResponse({'saved': True, 'url': url})
    return redirect(url)


@login_required
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def edit(request, pk=None, copy=False, management=False):
    source = get_dashboard(request, pk, edit=not copy, lock=request.method == 'POST') if pk else None
    item = Dashboard(owner=workspace_owner(request), workplace=request.workplace, created_by=request.user) if not source or copy else source
    initial = {field: getattr(source, field) for field in ['name', 'description', 'layout']} if copy else None
    if copy:
        initial['name'] = f'Kopia: {source.name}'[:150]
    editing_settings = source is not None and not copy
    form_type = DashboardSettingsForm if editing_settings else DashboardForm
    form = form_type(request.POST if request.method == 'POST' else None, instance=item, initial=initial,
                     **({} if editing_settings else {'request': request}))
    if request.method == 'POST' and form.is_valid():
        dashboard = form.save(commit=False)
        dashboard.revision += 1
        dashboard.save()
        form.save_m2m()
        if not editing_settings:
            dashboard.favorited_by.add(request.user)
            if copy:
                for gadget in source.gadgets.all():
                    gadget.pk = None
                    gadget.dashboard = dashboard
                    gadget.column = min(gadget.column, dashboard.column_count - 1)
                    gadget.save()
        return saved_response(request, management_url(request) if management else app_url(request, f'{dashboard.pk}/'))
    if source and not copy:
        return render(request, 'dashboard/pulpits/edit.html', {
            **editor_navigation_context(request, source, 'settings', management),
            'form': form, 'action': request.get_full_path(),
        }, status=400 if request.method == 'POST' else 200)
    return form_response(request, form, 'Kopiuj pulpit' if copy else 'Edytuj pulpit' if pk else 'Utwórz pulpit',
                         management_url(request) if management else app_url(request, f'{source.pk}/') if source else app_url(request), source,
                         status=400 if request.method == 'POST' else 200, management=management)


@login_required
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def access(request, pk, management=False):
    dashboard = get_dashboard(request, pk, edit=True, lock=request.method == 'POST')
    form = DashboardAccessForm(request.POST if request.method == 'POST' else None, instance=dashboard, request=request)
    if request.method == 'POST' and form.is_valid():
        dashboard = form.save(commit=False)
        dashboard.revision += 1
        dashboard.save()
        form.save_m2m()
        return saved_response(request, management_url(request) if management else app_url(request, f'{dashboard.pk}/'))
    return render(request, 'dashboard/pulpits/edit.html', {
        **editor_navigation_context(request, dashboard, 'access', management),
        'form': form, 'action': request.get_full_path(),
    }, status=400 if request.method == 'POST' else 200)


@login_required
@require_POST
@transaction.atomic
def delete(request, pk, management=False):
    get_dashboard(request, pk, edit=True, lock=True).delete()
    return saved_response(request, management_url(request) if management else app_url(request))


@login_required
@require_POST
@transaction.atomic
def favorite(request, pk):
    dashboard = get_dashboard(request, pk, lock=True)
    if dashboard.favorited_by.filter(pk=request.user.pk).exists():
        dashboard.favorited_by.remove(request.user)
    else:
        dashboard.favorited_by.add(request.user)
    if request.headers.get('X-Pulpit-Navigation') == 'true':
        return JsonResponse({'saved': True})
    return_url = request.POST.get('next', '')
    if return_url and url_has_allowed_host_and_scheme(return_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return saved_response(request, return_url)
    target = app_url(request, f'{pk}/') if request.POST.get('detail') else app_url(request)
    if not request.POST.get('detail'):
        tab = request.POST.get('tab', 'favorites')
        tab = tab if tab in {'favorites', 'mine', 'all'} else 'favorites'
        target += '?' + urlencode({'tab': tab, 'q': request.POST.get('q', '').strip()[:120]})
    return saved_response(request, target)


@login_required
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def gadget_edit(request, pk, gadget_pk=None, management=False):
    dashboard = get_dashboard(request, pk, edit=True, lock=request.method == 'POST')
    gadget = get_object_or_404(dashboard.gadgets, pk=gadget_pk) if gadget_pk else DashboardGadget(dashboard=dashboard)
    form = GadgetForm(request.POST if request.method == 'POST' else None, instance=gadget, request=request)
    if request.method == 'POST' and form.is_valid():
        if not gadget_pk and dashboard.gadgets.count() >= MAX_GADGETS:
            form.add_error(None, f'Pulpit może zawierać maksymalnie {MAX_GADGETS} gadżety.')
        else:
            gadget = form.save(commit=False)
            if not gadget_pk:
                gadget.position = dashboard.gadgets.count()
            gadget.save()
            dashboard.revision += 1
            dashboard.save(update_fields=['revision', 'updated_at'])
            return saved_response(request, management_url(request, f'{pk}/gadgets/') if management else app_url(request, f'{pk}/gadgets/'))
    return form_response(request, form, 'Edytuj gadżet' if gadget_pk else 'Dodaj gadżet',
                         management_url(request, f'{pk}/gadgets/') if management else app_url(request, f'{pk}/gadgets/'), dashboard, True,
                         status=400 if request.method == 'POST' else 200, management=management)


@login_required
@require_POST
@transaction.atomic
def gadget_delete(request, pk, gadget_pk, management=False):
    dashboard = get_dashboard(request, pk, edit=True, lock=True)
    get_object_or_404(dashboard.gadgets, pk=gadget_pk).delete()
    dashboard.revision += 1
    dashboard.save(update_fields=['revision', 'updated_at'])
    return saved_response(request, management_url(request, f'{pk}/gadgets/') if management else app_url(request, f'{pk}/gadgets/'))


@login_required
@require_POST
@transaction.atomic
def gadget_quick_add(request, pk, management=False):
    """Add safe defaults without closing the catalog; guard concurrent editors."""
    dashboard = get_dashboard(request, pk, edit=True, lock=True)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict) or type(payload.get('revision')) is not int:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Nieprawidłowe dane gadżetu.'}, status=400)
    if payload['revision'] != dashboard.revision:
        return JsonResponse({'error': 'Pulpit zmieniono w innym oknie. Odśwież stronę przed dodaniem gadżetu.'}, status=409)
    if dashboard.gadgets.count() >= MAX_GADGETS:
        return JsonResponse({'error': f'Pulpit może zawierać maksymalnie {MAX_GADGETS} gadżety.'}, status=400)
    form = GadgetForm({'kind': payload.get('kind'), 'title': '', 'status': '', 'assignee': 'all',
                       'group_by': 'status', 'limit': 10}, request=request, instance=DashboardGadget(dashboard=dashboard))
    if not form.is_valid():
        return JsonResponse({'error': 'Wybierz dostępny rodzaj gadżetu.'}, status=400)
    # Balance new gadgets across the actual persisted columns.
    counts = [dashboard.gadgets.filter(column=column).count() for column in range(dashboard.column_count)]
    column = min(range(dashboard.column_count), key=counts.__getitem__)
    gadget = form.save(commit=False)
    gadget.column = column
    last = dashboard.gadgets.filter(column=column).order_by('-position').first()
    gadget.position = last.position + 1 if last else 0
    gadget.save()
    dashboard.revision += 1
    dashboard.save(update_fields=['revision', 'updated_at'])
    decorate_gadget(request, gadget)
    if management:
        gadget.edit_url = management_url(request, f'{pk}/gadgets/{gadget.pk}/edit/')
        gadget.delete_url = management_url(request, f'{pk}/gadgets/{gadget.pk}/delete/')
    tasks = visible_to(Task.objects.filter(user=workspace_owner(request), workplace=request.workplace), request.user)
    data = gadget_data(request, gadget, tasks, set(visible_spaces(request).values_list('pk', flat=True)))
    html = render_to_string('dashboard/pulpits/gadget.html', {'data': data, 'editing_gadgets': True}, request=request)
    return JsonResponse({'saved': True, 'html': html, 'revision': dashboard.revision, 'column': column,
                         'gadget_count': dashboard.gadgets.count(), 'gadget_id': gadget.pk})


@login_required
@require_POST
@transaction.atomic
def arrange(request, pk):
    dashboard = get_dashboard(request, pk, edit=True, lock=True)
    try:
        payload = json.loads(request.body)
        layout, columns, revision = payload['layout'], payload['columns'], payload['revision']
        if layout not in Dashboard.Layout.values or not isinstance(columns, list) or type(revision) is not int:
            raise ValueError
        count = 1 if layout == 'single' else 3 if layout == 'three' else 2
        if len(columns) != count or any(not isinstance(column, list) for column in columns):
            raise ValueError
        ids = [pk for column in columns for pk in column]
        if any(type(pk) is not int for pk in ids) or len(ids) != len(set(ids)) or set(ids) != set(dashboard.gadgets.values_list('pk', flat=True)):
            raise ValueError
    except (ValueError, KeyError, TypeError):
        return JsonResponse({'error': 'Nieprawidłowy układ pulpitu.'}, status=400)
    if revision != dashboard.revision:
        return JsonResponse({'error': 'Pulpit zmieniono w innym oknie. Odśwież stronę przed kolejną zmianą.'}, status=409)
    for column, gadgets in enumerate(columns):
        for position, gadget_pk in enumerate(gadgets):
            dashboard.gadgets.filter(pk=gadget_pk).update(column=column, position=position)
    dashboard.layout = layout
    dashboard.revision += 1
    dashboard.save(update_fields=['layout', 'revision', 'updated_at'])
    return JsonResponse({'saved': True, 'revision': dashboard.revision})
