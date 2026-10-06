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
from .models import Dashboard, DashboardGadget, DashboardGroup
from .pulpit_forms import DashboardForm, GadgetForm, DashboardGroupForm, DashboardGroupsForm
from .pulpits import MAX_GADGETS, app_url, decorate_dashboard, detail_context, personal_groups, visible_dashboards
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
    group = get_object_or_404(personal_groups(request), pk=request.GET['group']) if request.GET.get('group', '').isdigit() else None
    if group:
        queryset = queryset.filter(personal_groups=group)
    if tab == 'favorites':
        queryset = queryset.filter(favorited_by=request.user)
    elif tab == 'mine':
        queryset = queryset.filter(created_by=request.user)
    if query:
        queryset = queryset.filter(Q(name__icontains=query) | Q(description__icontains=query))
    page = Paginator(queryset.order_by('name', 'pk'), 25).get_page(request.GET.get('page'))
    rows = [decorate_dashboard(request, row) for row in page]
    base = app_url(request)
    filters = {'q': query, **({'group': group.pk} if group else {})}
    return {'dashboards': rows, 'page': page, 'tab': tab, 'query': query, 'group': group, 'dashboards_url': base,
            'create_url': app_url(request, 'create/'),
            'groups_url': app_url(request, 'groups/'),
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
        dashboard.copy_url = management_url(request, f'{dashboard.pk}/copy/')
        dashboard.groups_url = management_url(request, f'{dashboard.pk}/groups/')
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


def form_response(request, form, title, return_url, dashboard=None, gadget=False, status=200, management=False):
    modal = {'form': form, 'title': title, 'action': request.get_full_path(), 'return_url': return_url, 'gadget': gadget}
    if request.headers.get('X-Pulpit-Modal') == 'true':
        return JsonResponse({'html': render_to_string('dashboard/pulpits/form.html', {'modal': modal}, request=request)}, status=status)
    context = management_context(request) if management else detail_context(request, dashboard) if dashboard else index_context(request)
    context['modal'] = modal
    context['return_url'] = return_url
    template = 'dashboard/pulpits/manage.html' if management else 'dashboard/pulpits/detail.html' if dashboard else 'dashboard/pulpits/index.html'
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
    form = DashboardForm(request.POST if request.method == 'POST' else None, instance=item, initial=initial, request=request)
    if request.method == 'POST' and form.is_valid():
        dashboard = form.save(commit=False)
        dashboard.revision += 1
        dashboard.save()
        form.save_m2m()
        if source and not copy:
            dashboard.gadgets.filter(column__gte=dashboard.column_count).update(column=dashboard.column_count - 1)
        else:
            dashboard.favorited_by.add(request.user)
            if copy:
                for gadget in source.gadgets.all():
                    gadget.pk = None
                    gadget.dashboard = dashboard
                    gadget.column = min(gadget.column, dashboard.column_count - 1)
                    gadget.save()
            else:
                for position, (kind, column) in enumerate([('assigned', 0), ('summary', 1), ('activity', 0), ('statistics', 1)]):
                    DashboardGadget.objects.create(dashboard=dashboard, kind=kind, column=min(column, dashboard.column_count - 1), position=position)
        return saved_response(request, management_url(request) if management else app_url(request, f'{dashboard.pk}/'))
    return form_response(request, form, 'Kopiuj pulpit' if copy else 'Edytuj pulpit' if pk else 'Utwórz pulpit',
                         management_url(request) if management else app_url(request, f'{source.pk}/') if source else app_url(request), source,
                         status=400 if request.method == 'POST' else 200, management=management)


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


def group_context(request):
    groups = list(personal_groups(request).annotate(dashboard_count=Count('dashboards', filter=Q(dashboards__in=visible_dashboards(request)), distinct=True)))
    for group in groups:
        group.url = app_url(request) + '?' + urlencode({'tab': 'all', 'group': group.pk})
        group.edit_url = app_url(request, f'groups/{group.pk}/edit/')
        group.delete_url = app_url(request, f'groups/{group.pk}/delete/')
    return {'groups': groups, 'dashboards_url': app_url(request), 'groups_url': app_url(request, 'groups/'),
            'create_group_url': app_url(request, 'groups/create/')}


@login_required
@require_GET
def groups(request):
    return render(request, 'dashboard/pulpits/groups.html', group_context(request))


@login_required
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def group_edit(request, pk=None):
    queryset = personal_groups(request)
    if request.method == 'POST':
        queryset = queryset.select_for_update()
    group = get_object_or_404(queryset, pk=pk) if pk else DashboardGroup(owner=workspace_owner(request), workplace=request.workplace, user=request.user)
    form = DashboardGroupForm(request.POST if request.method == 'POST' else None, instance=group, request=request)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return saved_response(request, app_url(request, 'groups/'))
    modal = {'form': form, 'title': 'Edytuj grupę pulpitów' if pk else 'Utwórz grupę pulpitów', 'action': request.get_full_path(),
             'return_url': app_url(request, 'groups/')}
    status = 400 if request.method == 'POST' else 200
    if request.headers.get('X-Pulpit-Modal') == 'true':
        return JsonResponse({'html': render_to_string('dashboard/pulpits/form.html', {'modal': modal}, request=request)}, status=status)
    return render(request, 'dashboard/pulpits/groups.html', {**group_context(request), 'modal': modal}, status=status)


@login_required
@require_POST
@transaction.atomic
def group_delete(request, pk):
    get_object_or_404(personal_groups(request).select_for_update(), pk=pk).delete()
    return saved_response(request, app_url(request, 'groups/'))


@login_required
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def dashboard_groups(request, pk, management=False):
    dashboard = get_dashboard(request, pk)
    form = DashboardGroupsForm(request.POST if request.method == 'POST' else None, request=request, dashboard=dashboard)
    if request.method == 'POST' and form.is_valid():
        available = personal_groups(request).select_for_update()
        # Personal organization is independent of the creator's configuration.
        for group in available:
            if group in form.cleaned_data['groups']:
                group.dashboards.add(dashboard)
            else:
                group.dashboards.remove(dashboard)
        return saved_response(request, management_url(request) if management else app_url(request, f'{pk}/'))
    return form_response(request, form, 'Przypisz pulpit do grup', management_url(request) if management else app_url(request, f'{pk}/'), dashboard,
                         status=400 if request.method == 'POST' else 200, management=management)


@login_required
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def gadget_edit(request, pk, gadget_pk=None):
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
            return saved_response(request, app_url(request, f'{pk}/'))
    return form_response(request, form, 'Edytuj gadżet' if gadget_pk else 'Dodaj gadżet', app_url(request, f'{pk}/'), dashboard, True,
                         status=400 if request.method == 'POST' else 200)


@login_required
@require_POST
@transaction.atomic
def gadget_delete(request, pk, gadget_pk):
    dashboard = get_dashboard(request, pk, edit=True, lock=True)
    get_object_or_404(dashboard.gadgets, pk=gadget_pk).delete()
    dashboard.revision += 1
    dashboard.save(update_fields=['revision', 'updated_at'])
    return saved_response(request, app_url(request, f'{pk}/'))


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
