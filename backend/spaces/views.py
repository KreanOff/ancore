from urllib.parse import urlencode
from datetime import date, timedelta
import hashlib
import json
import logging
import mimetypes

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Q, Sum
from django.forms import formset_factory
from django.http import FileResponse, Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from core.frontend import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from dashboard.recent import remember_view
from .access import editable_to, require_editable, visible_to
from .models import SpaceTask, SpaceMembership
from workplaces.models import Workplace
from workplaces.services import workplace_people, workspace_owner
from .avatars import save_space_avatar
from .backlog import bulk_plan_items, move_backlog_item
from .backlog_window import backlog_more_url, backlog_window
from .board import move_board_item
from .defaults import TEMPLATES, issue_type_icon, template_settings
from .dashboard import dashboard_payload
from .forms import CustomFieldForm, ItemForm, MemberForm, SpaceAvatarForm, SpaceForm, SprintCloseForm, SprintForm, StatusForm, TypeForm
from .models import Space, SpaceConfiguration, Sprint, WorkItem
from .services import app_url, can_manage_spaces, decorate_directory_spaces, manage_configuration, manage_space, record, set_status, space_url, task_url, teams_for, transition_allowed, update_sprint, visible_items, visible_spaces
from .summary import filter_summary_items, space_summary
from .item_query import item_sort, order_items
from .list_window import list_url, list_window, more_url


def space_object(request, pk):
    lookup = {'pk': pk} if isinstance(pk, int) else {'slug': pk}
    return get_object_or_404(visible_spaces(request), **lookup)


def base_context(request):
    return {'spaces_url': app_url(request), 'teams_url': app_url(request, app='teams')}


def decorate_items(request, items):
    result = list(items)
    editable_ids = set(editable_to(SpaceTask.objects.filter(pk__in=[i.task_id for i in result]), request.user).values_list('pk', flat=True))
    counts = {row['pk']: row for row in SpaceTask.objects.filter(pk__in=[i.task_id for i in result]).annotate(
        tags_total=Count('tags', distinct=True), attachments_total=Count('attachments', distinct=True),
    ).values('pk', 'tags_total', 'attachments_total')}
    for item in result:
        item.url = task_url(request, item.task)
        item.edit_url = space_url(request, item.space, f'tasks/{item.key}/edit/')
        item.action_url = space_url(request, item.space, f'tasks/{item.key}/action/')
        item.update_dates_url = space_url(request, item.space, f'tasks/{item.key}/dates/')
        if request.GET:
            item.action_url += '?' + request.GET.urlencode()
            item.edit_url += '?' + request.GET.urlencode()
        item.editable = item.task_id in editable_ids and item.space_id is not None
        settings = item.space.configuration.settings if item.space_id else template_settings()
        item.status_label = next((s['label'] for s in settings['statuses'] if s['key'] == item.status), item.task.get_status_display())
        item.type_label = item.get_work_type_display()
        item.transitions = [s for s in settings['statuses'] if s['key'] != item.status and item.space_id and transition_allowed(item, s['key'])]
        item.status_order = next((n for n, s in enumerate(settings['statuses']) if s['key'] == item.status), 0)
        item.tags_count = counts[item.task_id]['tags_total']
        item.attachments_count = counts[item.task_id]['attachments_total']
    return result


def issue_type_filters(request, space=None):
    configurations = [space.configuration.settings] if space else [
        template_settings(),
        *visible_spaces(request).values_list('configuration__settings', flat=True),
    ]
    options = {}
    for config in configurations:
        for row in config['types']:
            options.setdefault(row['key'], {**row, 'icon': issue_type_icon(row['key'])})
    return list(options.values()), request.GET.get('work_type', '').strip()[:40]


def index_context(request):
    query = request.GET.get('q', '').strip()[:120]
    tab = request.GET.get('tab', 'all')
    spaces = visible_spaces(request)
    if query:
        spaces = spaces.filter(Q(name__icontains=query) | Q(key__icontains=query))
    if tab == 'favorites':
        spaces = spaces.filter(favorited_by=request.user)
    elif tab == 'private':
        spaces = spaces.filter(visibility='private')
    kind = request.GET.get('kind')
    if kind in {'software', 'business', 'service'}:
        spaces = spaces.filter(kind=kind)
    page = Paginator(spaces.order_by('name', 'pk'), 30).get_page(request.GET.get('page'))
    page.object_list = decorate_directory_spaces(request, page.object_list)
    return {**base_context(request), 'page': page, 'query': query, 'tab': tab, 'kind': kind, 'create_url': app_url(request, 'create/'), 'templates': TEMPLATES}


def directory_url(request):
    filters = {key: request.GET[key] for key in ['q', 'kind', 'tab', 'page'] if request.GET.get(key)}
    return app_url(request) + ('?' + urlencode(filters) if filters else '')


@login_required
@require_GET
def index(request):
    return render(request, 'spaces/index.html', index_context(request))


@login_required
@require_GET
def manage(request):
    target = directory_url(request)
    if getattr(request, '_react_api', False):
        return JsonResponse({'redirect': target})
    return redirect(target)


@login_required
@require_GET
def search(request):
    query = request.GET.get('q', '').strip()[:120]
    results = list(visible_spaces(request).filter(
        Q(name__icontains=query) | Q(key__icontains=query),
    ).order_by('name', 'pk')[:21]) if query else []
    has_more = len(results) > 20
    results = results[:20]
    for space in results:
        space.url = space_url(request, space)
    if getattr(request, '_react_api', False):
        from spaces.avatars import space_avatar
        return JsonResponse({'results': [{'id': str(item.pk), 'name': item.name, 'url': item.url,
                                         'avatar': space_avatar(item), 'detail': f'{item.get_kind_display()} · {item.get_management_display()}'} for item in results],
                             'count': len(results), 'has_more': has_more})
    response = JsonResponse({
        'html': render_to_string('spaces/search_results.html', {'results': results, 'has_more': has_more}),
        'count': len(results),
    })
    response['Cache-Control'] = 'private, no-store'
    return response


def filtered_space_items(request, space, items, now):
    """Shared filter scope for displayed rows and backlog reordering."""
    query = request.GET.get('q', '').strip()[:120]
    if query:
        items = items.filter(Q(task__title__icontains=query) | Q(key__icontains=query))
    work_type = request.GET.get('work_type', '').strip()[:40]
    if work_type:
        items = items.filter(work_type=work_type)
    for parameter, lookup in (('team', 'team_id'),):
        value = request.GET.get(parameter, '')
        if value.isdecimal() and len(value) < 19:
            items = items.filter(**{lookup: int(value)})
    return filter_summary_items(request, space, items, now)


def items_for_view(space, items, view, active_sprint=None):
    if view == 'board':
        if space.template == 'scrum':
            return items.filter(sprint=active_sprint) if active_sprint else items.none()
        return items.filter(in_backlog=False)
    if view == 'backlog':
        items = items.exclude(task__status='closed').filter(Q(sprint__isnull=True) | ~Q(sprint__state='closed'))
        if space.template == 'kanban':
            items = items.filter(in_backlog=True)
    return items


def backlog_url(request, space, suffix=''):
    params = request.GET.copy()
    params.pop('planning_sprint', None)
    params.pop('page', None)
    params['view'] = 'backlog'
    return space_url(request, space, suffix + '?') + params.urlencode()


def planning_totals(items):
    totals = items.aggregate(total=Count('pk'), point_total=Sum('points', default=0),
                           finished=Count('pk', filter=Q(task__status='closed')),
                           finished_points=Sum('points', filter=Q(task__status='closed'), default=0),
                           unestimated=Count('pk', filter=Q(points__isnull=True) & ~Q(task__status='closed')))
    totals['points'] = totals.pop('point_total')
    return totals


def detail_context(request, space, view):
    allowed_views = {'overview', 'board', 'list', 'timeline', 'reports', 'tags', 'settings'}
    if space.template in {'kanban', 'scrum'}:
        allowed_views.add('backlog')
    if view not in allowed_views:
        view = 'overview'
    base = space_url(request, space)
    navigation = [
        ('overview', 'Podsumowanie', 'layout-dashboard'),
        ('list', 'Lista zadań', 'list-checks'),
        ('board', 'Aktywny sprint' if space.template == 'scrum' else 'Tablica', 'kanban'),
    ]
    if 'backlog' in allowed_views:
        navigation.insert(1, ('backlog', 'Backlog', 'layers'))
    if space.kind == 'service':
        navigation[1] = ('list', 'Kolejka zgłoszeń', 'list-checks')
    navigation += [
        ('timeline', 'Oś czasu', 'calendar-range'),
        ('reports', 'Raporty', 'chart-no-axes-combined'),
        ('tags', 'Tagi', 'tag'),
        ('settings', 'Ustawienia przestrzeni', 'settings'),
    ]
    query = request.GET.get('q', '').strip()[:120]
    items = visible_items(request).filter(space=space)
    assignee_options = get_user_model().objects.filter(pk__in=items.order_by().values('task__assignee_id')).order_by('first_name', 'last_name', 'pk')
    space_teams = list(teams_for(request).filter(spaces=space))
    for team_option in space_teams:
        team_option.select_photo_url = app_url(request, f'{team_option.pk}/photo/', 'teams') if team_option.photo else ''
    type_options, type_filter = issue_type_filters(request, space)
    team = request.GET.get('team', '')
    now = timezone.now()
    items, summary_filters = filtered_space_items(request, space, items, now)
    item_query_params = request.GET.copy()
    for key in list(item_query_params):
        if key.startswith(('list_limit_', 'backlog_limit_')):
            item_query_params.pop(key)
    filter_context = {
        **summary_filters, 'query': query, 'assignee_options': assignee_options,
        'item_query_params': item_query_params,
        'priority_options': SpaceTask.PRIORITY_CHOICES, 'space_teams': space_teams,
        'team_filter': team, 'type_options': type_options, 'type_filter': type_filter,
        'item_filter_count': sum(bool(value) for value in (
            type_filter, team, *[summary_filters[key] for key in ('assignee_filter', 'status_filter', 'priority_filter', 'summary_filter')],
        )),
    }
    if view in {'overview', 'tags'}:
        return {
            **base_context(request), 'space': space, 'space_url': base, 'view': view,
            'navigation': [{'key': k, 'label': l, 'icon': icon, 'url': base + ('?view=' + k if k != 'overview' else '')} for k, l, icon in navigation],
            'can_manage': manage_space(request, space),
            'can_edit': editable_to(Space.objects.filter(pk=space.pk), request.user).exists(),
            'create_item_url': base + 'items/create/',
            **({**filter_context, 'summary': {**space_summary(request, space, items, now), 'dashboard': dashboard_payload(request, space)}} if view == 'overview' else {}),
        }
    active_sprint = space.sprints.filter(state='active').first()
    all_items = items
    items = items_for_view(space, items, view, active_sprint)
    items = order_items(request, items, view)
    counts = dict(all_items.order_by().values_list('status').annotate(n=Count('pk')))
    column_counts = counts if view == 'list' else dict(items.order_by().values_list('status').annotate(n=Count('pk')))
    if view == 'list':
        page = None
        rows = decorate_items(request, list_window(request, space, items, column_counts))
    elif view in {'board', 'timeline'}:
        page = None
        rows = decorate_items(request, items)
    elif view == 'backlog':
        page = None
        rows = decorate_items(request, backlog_window(request, items))
    else:
        page = Paginator(items, 100).get_page(request.GET.get('page'))
        rows = decorate_items(request, page.object_list)
    timeline = None
    if view == 'timeline':
        dates = []
        for item in rows:
            due = timezone.localtime(item.task.due_at).date() if item.task.due_at else None
            item.timeline_start = timezone.localtime(item.start_at).date() if item.start_at else due
            item.timeline_end = max(item.timeline_start, due or item.timeline_start) if item.timeline_start else None
            if item.timeline_start:
                dates.extend([item.timeline_start, item.timeline_end])
        start, end = (min(dates), max(dates)) if dates else (timezone.localdate(), timezone.localdate() + timedelta(days=27))
        duration = min(max((end - start).days + 1, 7), (date.max - start).days + 1)
        timeline = {'start': start, 'end': start + timedelta(days=duration - 1), 'today': timezone.localdate()}
        for item in rows:
            if not item.timeline_start:
                continue
            item.timeline_left = str(round((item.timeline_start - start).days / duration * 100, 2))
            item.timeline_width = str(round(max((item.timeline_end - item.timeline_start).days + 1, 1) / duration * 100, 2))
    columns = [{**s, 'items': [i for i in rows if i.status == s['key']], 'count': column_counts.get(s['key'], 0)} for s in space.statuses]
    if view == 'list':
        for column in columns:
            column['loaded_count'] = len(column['items'])
            column['more_url'] = more_url(request, space, column['key'], column['loaded_count'], column['count'])
    sprint_totals = {row['sprint_id']: row for row in all_items.order_by().values('sprint_id').annotate(
        total=Count('pk'), point_total=Sum('points', default=0),
        finished=Count('pk', filter=Q(task__status='closed')),
        finished_points=Sum('points', filter=Q(task__status='closed'), default=0),
        unestimated=Count('pk', filter=Q(points__isnull=True) & ~Q(task__status='closed')),
    )}
    for totals in sprint_totals.values():
        totals['points'] = totals.pop('point_total')
    sprints = list(space.sprints.exclude(state='closed') if view == 'backlog' else space.sprints.all())
    sprints.sort(key=lambda sprint: (sprint.state != 'active', sprint.start_on, sprint.pk))
    for sprint in sprints:
        sprint.action_url = backlog_url(request, space, f'sprints/{sprint.pk}/action/')
        sprint.edit_url = backlog_url(request, space, f'sprints/{sprint.pk}/edit/')
        sprint.start_url = backlog_url(request, space, f'sprints/{sprint.pk}/start/')
        sprint.complete_url = backlog_url(request, space, f'sprints/{sprint.pk}/complete/')
        sprint.create_item_url = backlog_url(request, space, 'items/create/') + f'&planning_sprint={sprint.pk}'
        sprint.visible_items = [i for i in rows if i.sprint_id == sprint.pk]
        sprint.planning = sprint_totals.get(sprint.pk, {'total': 0, 'points': 0, 'finished': 0, 'finished_points': 0, 'unestimated': 0})
        sprint.visible_count = sprint.planning['total']
        sprint.finished_count = sprint.planning['finished']
        sprint.open_count = sprint.visible_count - sprint.finished_count
        if view == 'backlog':
            sprint.loaded_count = len(sprint.visible_items)
            sprint.more_url = backlog_more_url(request, space, sprint.pk, sprint.loaded_count, sprint.open_count)
    backlog_context = {'backlog_totals': planning_totals(items.filter(sprint__isnull=True)),
                       'bulk_plan_url': backlog_url(request, space, 'backlog/plan/'),
                       'backlog_create_url': backlog_url(request, space, 'items/create/')} if view == 'backlog' else {}
    if view == 'backlog':
        backlog_context['backlog_loaded_count'] = sum(item.sprint_id is None for item in rows)
        backlog_context['backlog_more_url'] = backlog_more_url(
            request, space, None, backlog_context['backlog_loaded_count'], backlog_context['backlog_totals']['total'])
    sort = item_sort(request, view)
    toolbar_context = {'item_sort': sort, 'can_reorder': sort['manual']}
    create_item_url = (backlog_url(request, space, 'items/create/') if view == 'backlog'
                       else list_url(request, space, 'items/create/') if view == 'list'
                       else base + 'items/create/')
    stats = {'all': all_items.count(), 'closed': all_items.filter(task__status='closed').count(), 'overdue': all_items.filter(task__due_at__lt=now).exclude(task__status='closed').count(), 'points': all_items.aggregate(n=Sum('points'))['n'] or 0}
    return {**base_context(request), **filter_context, **backlog_context, **toolbar_context,
            'space': space, 'space_url': base, 'timeline': timeline, 'view': view,
            'navigation': [{'key': k, 'label': label, 'icon': icon, 'url': base + ('?view=' + k if k != 'overview' else '')} for k, label, icon in navigation],
            'page': page, 'items': rows, 'columns': columns, 'stats': stats,
            'status_counts': [{**status, 'count': counts.get(status['key'], 0)} for status in space.statuses],
            'active_sprint': active_sprint, 'sprints': sprints, 'backlog_items': [item for item in rows if not item.sprint_id],
            'can_manage': manage_space(request, space), 'can_configure': manage_configuration(request, space),
            'can_edit': editable_to(Space.objects.filter(pk=space.pk), request.user).exists(),
            'create_item_url': create_item_url,
            'sprint_create_url': backlog_url(request, space, 'sprints/create/'), 'edit_url': base + 'edit/',
            'configuration_url': base + 'configuration/', 'member_url': base + 'members/',
            'members': space.memberships.filter(user__in=workplace_people(request.workplace)).select_related('user')}


@login_required
@require_http_methods(['GET', 'HEAD', 'POST'])
def detail(request, pk):
    space = space_object(request, pk)
    if isinstance(pk, int) and request.method in {'GET', 'HEAD'}:
        query = request.META.get('QUERY_STRING', '')
        return redirect(space_url(request, space) + (f'?{query}' if query else ''))
    remember_view(request, space)
    if request.GET.get('view') == 'tags':
        from tasks.forms import TaskTagForm
        from tasks.tagging import tag_action
        from tasks.tag_directory import tag_window_for_request, TAG_SORT_OPTIONS, TAG_DEFAULT_SORT
        context = detail_context(request, space, 'tags')
        window = tag_window_for_request(request, space=space)
        context.update({
            'active_view': 'tags', 'tag_window': window, 'tags': window['tags'],
            'can_edit_tags': context['can_edit'], 'tag_query': window['query'],
            'tag_filter_options': window['filters'], 'tag_sort_options': TAG_SORT_OPTIONS,
            'tag_default_sort': TAG_DEFAULT_SORT,
            'tag_form': TaskTagForm(user=workspace_owner(request), workplace=request.workplace, space=space),
        })
        context.update({f'tag_{key}_filter': window[key] for key in ('priority', 'status', 'category', 'scope', 'owner')})
        context.update({f'tag_{key}': window[key] for key in ('sort', 'sort_param', 'sort_label', 'sort_direction')})
        if request.method == 'POST':
            result = tag_action(request, space=space)
            if not isinstance(result, dict):
                return result
            context.update(result)
        status = 400 if getattr(request, '_react_api', False) and context.get('tag_modal_open') else 200
        return render(request, 'spaces/tags.html', context, status=status)
    if request.method == 'POST':
        raise Http404
    return render(request, 'spaces/detail.html', detail_context(request, space, request.GET.get('view', 'overview')))


@login_required
@require_GET
def retired_all_items(request):
    """Keep bookmarks to the removed directory working through Filters."""
    criteria = {}
    for old_name, new_name, limit in (('q', 'q', 120), ('work_type', 'type', 40)):
        value = request.GET.get(old_name, '').strip()[:limit]
        if value:
            criteria[new_name] = value
    if request.GET.get('assignee') == 'me':
        criteria['assignee'] = 'me'
    if request.GET.get('page'):
        criteria['page'] = request.GET['page']
    target = app_url(request, 'search/', app='filters')
    if criteria:
        target += '?' + urlencode({'basic': '1', 'mode': 'basic', 'sort': 'created_desc', **criteria})
    return redirect(target)


def dialog_response(request, form, title, return_url, saved=False, directory=False, background_space=None, settings_space=None, settings_tab='main'):
    if saved:
        if request.headers.get('X-Work-Modal') == 'true':
            return JsonResponse({'saved': True, 'url': return_url})
        return redirect(return_url)
    modal = {'form': form, 'title': title, 'action': request.get_full_path(), 'return_url': return_url}
    if settings_space:
        modal['space_settings'] = {'space_url': space_url(request, settings_space), 'tab': settings_tab}
    context = {**base_context(request), 'modal': modal}
    status = 400 if request.method == 'POST' else 200
    if getattr(request, '_react_api', False):
        return render(request, 'spaces/form_page.html', context, status=status)
    if request.headers.get('X-Work-Modal') == 'true':
        return JsonResponse({'html': render_to_string('spaces/form.html', context, request=request)}, status=status)
    if directory:
        context.update(index_context(request))
        modal['directory_url'] = return_url
        return render(request, 'spaces/index.html', context, status=status)
    if background_space:
        context.update(detail_context(request, background_space, 'backlog'))
        modal['directory_url'] = return_url
        return render(request, 'spaces/detail.html', context, status=status)
    return render(request, 'spaces/form_page.html', context, status=status)


@login_required
@require_http_methods(['GET', 'POST'])
def edit(request, pk=None, management=False):
    if management and not can_manage_spaces(request):
        raise PermissionDenied
    space = space_object(request, pk) if pk else None
    if space and not manage_space(request, space):
        raise PermissionDenied
    form = SpaceForm(request.POST if request.method == 'POST' else None, request.FILES or None, request=request, space=space)
    url = directory_url(request) if management else space_url(request, space, '?view=settings') if pk else app_url(request)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        saved_file = None
        try:
            with transaction.atomic():
                if space is not None:
                    Workplace.objects.select_for_update().get(pk=request.workplace.pk)
                if space is None:
                    config = data.get('configuration') or SpaceConfiguration.objects.create(
                        workplace=request.workplace, name=data['name'], shared=data['management'] == 'company', settings=template_settings(data['template']))
                    space = Space(user=workspace_owner(request), workplace=request.workplace, responsible_user=request.user, configuration=config)
                    for name in ('name', 'description', 'key', 'kind', 'template', 'management', 'visibility'):
                        setattr(space, name, data[name])
                    space.private_owner = request.user if space.visibility == 'private' else None
                    space.save()
                else:
                    space = get_object_or_404(visible_spaces(request).select_for_update(of=('self',)), pk=space.pk)
                    if not manage_space(request, space):
                        raise PermissionDenied
                    visibility_changed = space.visibility != data['visibility']
                    space.name, space.description, space.visibility = data['name'], data['description'], data['visibility']
                    if visibility_changed:
                        space.private_owner = request.user if space.visibility == 'private' else None
                    if 'avatar' in request.POST or data.get('avatar_photo') or data.get('avatar_photo_remove'):
                        saved_file = save_space_avatar(space, data)
                    else:
                        space.save()
                    if visibility_changed:
                        space.memberships.all().delete()
                url = directory_url(request) if management else space_url(request, space)
        except ValidationError as error:
            form.add_error('avatar_photo', error)
        except Exception as error:
            if saved_file:
                saved_file[0].delete(saved_file[1])
            if not isinstance(error, IntegrityError):
                raise
            form.add_error('key', 'Ten klucz został właśnie zajęty. Wybierz inny.')
        else:
            return dialog_response(request, form, '', url, saved=True)
    return dialog_response(request, form, 'Ustawienia przestrzeni' if pk else 'Utwórz przestrzeń', url, directory=pk is None or management, settings_space=space if pk else None)


@login_required
@require_http_methods(['GET', 'POST'])
def avatar_edit(request, pk):
    space = space_object(request, pk)
    if not manage_space(request, space):
        raise PermissionDenied
    form = SpaceAvatarForm(request.POST if request.method == 'POST' else None, request.FILES or None, space=space)
    url = space_url(request, space)
    if request.method == 'POST' and form.is_valid():
        saved_file = None
        try:
            with transaction.atomic():
                Workplace.objects.select_for_update().get(pk=request.workplace.pk)
                space = get_object_or_404(visible_spaces(request).select_for_update(of=('self',)), pk=space.pk)
                if not manage_space(request, space):
                    raise PermissionDenied
                saved_file = save_space_avatar(space, form.cleaned_data)
        except ValidationError as error:
            form.add_error('avatar_photo', error)
        except Exception:
            if saved_file:
                try:
                    saved_file[0].delete(saved_file[1])
                except OSError:
                    logging.getLogger(__name__).exception('Failed to clean up a space avatar after rollback')
            raise
        if not form.errors:
            return dialog_response(request, form, '', url, saved=True)
    return dialog_response(request, form, 'Wybierz awatar', url, settings_space=space, settings_tab='avatar')


@login_required
@require_GET
def avatar_photo(request, pk):
    space = space_object(request, pk)
    if not space.avatar_photo:
        raise Http404
    try:
        photo = space.avatar_photo.open('rb')
    except FileNotFoundError:
        raise Http404
    response = FileResponse(photo, content_type=mimetypes.guess_type(space.avatar_photo.name)[0] or 'application/octet-stream')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
@require_POST
def favorite(request, pk):
    space = space_object(request, pk)
    if space.favorited_by.filter(pk=request.user.pk).exists():
        space.favorited_by.remove(request.user)
    else:
        space.favorited_by.add(request.user)
    if request.headers.get('X-Space-Navigation') == 'true':
        return JsonResponse({'saved': True})
    return_url = request.POST.get('next', '')
    if return_url and url_has_allowed_host_and_scheme(return_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(return_url)
    return redirect(app_url(request))


@login_required
@require_http_methods(['GET', 'POST'])
def item_edit(request, pk=None, space_pk=None, key=None):
    if key:
        space = space_object(request, space_pk)
        pk = get_object_or_404(visible_items(request), space=space, key=key).pk
    item = get_object_or_404(visible_items(request), pk=pk) if pk else None
    space = space_object(request, item.space_id if item else space_pk)
    if item:
        if not editable_to(SpaceTask.objects.filter(pk=item.task_id), request.user).exists():
            raise PermissionDenied
    elif not editable_to(Space.objects.filter(pk=space.pk), request.user).exists():
        raise PermissionDenied
    form = ItemForm(request.POST if request.method == 'POST' else None, request=request, space=space, item=item)
    in_planning = request.GET.get('view') == 'backlog' and space.template in {'scrum', 'kanban'}
    if not item and in_planning:
        form.initial['in_backlog'] = True
        if request.GET.get('planning_sprint'):
            if space.template != 'scrum':
                raise Http404
            sprint_id = request.GET['planning_sprint']
            if not sprint_id.isascii() or not sprint_id.isdecimal() or len(sprint_id) > 18:
                raise Http404
            sprint = get_object_or_404(space.sprints.filter(state__in=['planned', 'active']), pk=int(sprint_id))
            form.initial.update(sprint=sprint, in_backlog=False)
    url = (backlog_url(request, space) if in_planning else task_url(request, item.task) if key
           else list_url(request, space) if request.GET.get('view') == 'list'
           else space_url(request, space, '?view=list'))
    if request.method == 'POST':
        with transaction.atomic():
            if request.workplace:
                Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            Space.objects.select_for_update().get(pk=space.pk)
            if item:
                require_editable(SpaceTask.objects.filter(pk=item.task_id), request.user)
                item = get_object_or_404(visible_items(request), pk=item.pk, space=space)
            else:
                require_editable(Space.objects.filter(pk=space.pk), request.user)
            space = space_object(request, space.pk)
            form = ItemForm(request.POST, request=request, space=space, item=item)
            if not form.is_valid():
                return dialog_response(request, form, f'Edytuj {item.key}' if item else 'Utwórz zadanie', url, background_space=space if in_planning else None)
            data = form.cleaned_data
            task = SpaceTask.objects.select_for_update().get(pk=item.task_id) if item else SpaceTask(space=space, created_by=request.user, visibility='public')
            for name in ('title', 'description', 'priority', 'assignee', 'due_at', 'task_type', 'reminder_at'):
                setattr(task, name, data[name] or ('general' if name == 'task_type' else data[name]))
            task._activity_actor = request.user
            task.save()
            task.tags.set(data['tags'])
            item = WorkItem.objects.select_for_update().get(task=task)
            old_type, old_type_label = item.work_type, item.get_work_type_display()
            for name in ('work_type', 'team', 'sprint', 'epic', 'points', 'start_at', 'in_backlog'):
                if name in data:
                    setattr(item, name, data[name])
            item.custom_values = {f['key']: str(data['custom_' + f['key']]) if data.get('custom_' + f['key']) is not None else '' for f in space.configuration.settings.get('fields', [])}
            item.save()
            if pk:
                metadata = {'fields': ['typ zgłoszenia'], 'changes': [{
                    'field': 'typ zgłoszenia', 'from_label': old_type_label,
                    'to_label': item.get_work_type_display(),
                }]} if old_type != item.work_type else {}
                record(item, request.user, 'updated', 'zaktualizował zadanie w przestrzeni', metadata)
        return dialog_response(request, form, '', url, saved=True)
    return dialog_response(request, form, f'Edytuj {item.key}' if item else 'Utwórz zadanie', url, background_space=space if in_planning else None)


@login_required
@require_POST
def backlog_plan(request, pk):
    space = space_object(request, pk)
    try:
        with transaction.atomic():
            if request.workplace:
                Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            Space.objects.select_for_update().get(pk=space.pk)
            space = space_object(request, space.pk)
            scope, _ = filtered_space_items(request, space, visible_items(request).filter(space=space), timezone.now())
            changed = bulk_plan_items(request, space, items_for_view(space, scope, 'backlog'))
    except ValidationError as error:
        if getattr(request, '_react_api', False) or request.headers.get('X-Work-Action') == 'true':
            return JsonResponse({'error': ' '.join(error.messages)}, status=400)
        messages.error(request, ' '.join(error.messages))
        return redirect(backlog_url(request, space))
    if getattr(request, '_react_api', False) or request.headers.get('X-Work-Action') == 'true':
        return JsonResponse({'saved': True, 'changed': changed, 'url': backlog_url(request, space)})
    return redirect(backlog_url(request, space))


@login_required
@require_POST
def item_action(request, pk=None, space_pk=None, key=None):
    if key:
        space = space_object(request, space_pk)
        pk = get_object_or_404(visible_items(request), space=space, key=key).pk
    item = get_object_or_404(visible_items(request), pk=pk)
    if not item.space_id or not editable_to(SpaceTask.objects.filter(pk=item.task_id), request.user).exists():
        raise PermissionDenied
    try:
        with transaction.atomic():
            if request.workplace:
                Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            Space.objects.select_for_update().get(pk=item.space_id)
            SpaceTask.objects.select_for_update().get(pk=item.task_id)
            item = WorkItem.objects.select_for_update().get(pk=item.pk)
            require_editable(SpaceTask.objects.filter(pk=item.task_id), request.user)
            action = request.POST.get('action')
            if action in {'position', 'plan', 'up', 'down'} and not item_sort(request)['manual']:
                raise ValidationError('Wybierz rosnącą kolejność ręczną, aby przestawiać zadania.')
            if action == 'status':
                set_status(request, item, request.POST.get('status'))
            elif action == 'position':
                space = space_object(request, item.space_id)
                candidates, _ = filtered_space_items(request, space, visible_items(request).filter(space=space), timezone.now())
                active_sprint = space.sprints.filter(state='active').first()
                move_board_item(request, space, item, items_for_view(space, candidates, 'board', active_sprint))
            elif action in {'backlog', 'board'}:
                item.in_backlog = action == 'backlog'
                item.sprint = None
                item.save(update_fields=['in_backlog', 'sprint'])
                record(item, request.user, 'updated', 'przeniósł zadanie do backlogu' if item.in_backlog else 'przeniósł zadanie na tablicę')
            elif action == 'plan':
                Space.objects.select_for_update().get(pk=item.space_id)
                space = space_object(request, item.space_id)
                candidates, _ = filtered_space_items(request, space, visible_items(request).filter(space=space), timezone.now())
                candidates = items_for_view(space, candidates, 'backlog')
                move_backlog_item(request, space, item, candidates)
            elif action in {'up', 'down'}:
                Space.objects.select_for_update().get(pk=item.space_id)
                space = space_object(request, item.space_id)
                candidates, _ = filtered_space_items(request, space, visible_items(request).filter(space=space), timezone.now())
                candidates = items_for_view(space, candidates, 'backlog').filter(sprint_id=item.sprint_id)
                ordered = list(backlog_window(request, candidates.order_by('rank', 'pk')))
                index = next((i for i, row in enumerate(ordered) if row.pk == item.pk), None)
                if index is None:
                    raise ValidationError('Zadanie nie jest już widoczne w tym backlogu. Odśwież listę.')
                target = index + (-1 if action == 'up' else 1)
                if 0 <= target < len(ordered):
                    other = ordered[target]
                    if not editable_to(SpaceTask.objects.filter(pk=other.task_id), request.user).exists():
                        raise PermissionDenied
                    if item.rank == other.rank:
                        raise ValidationError('Zadania mają tę samą kolejność. Przenieś zadanie do innego sprintu i wróć do planowania.')
                    item.rank, other.rank = other.rank, item.rank
                    WorkItem.objects.bulk_update([item, other], ['rank'])
                    record(item, request.user, 'updated', 'zmienił kolejność zadania')
            else:
                return HttpResponseBadRequest('Nieprawidłowa operacja.')
    except ValidationError as error:
        if getattr(request, '_react_api', False) or request.headers.get('X-Work-Action') == 'true':
            return JsonResponse({'error': ' '.join(error.messages)}, status=400)
        messages.error(request, ' '.join(error.messages))
    params = request.GET.copy()
    params['view'] = request.POST.get('return_view') if request.POST.get('return_view') in {'list', 'board', 'backlog', 'timeline'} else 'board'
    if params['view'] == 'backlog':
        params.pop('page', None)
    url = space_url(request, item.space, '?') + params.urlencode()
    if getattr(request, '_react_api', False) or request.headers.get('X-Work-Action') == 'true':
        return JsonResponse({'saved': True, 'url': url})
    return redirect(url)


@login_required
@require_http_methods(['GET', 'POST'])
def sprint_create(request, pk):
    space = space_object(request, pk)
    if space.template != 'scrum' or not manage_space(request, space):
        raise PermissionDenied
    today = timezone.localdate()
    last_end = space.sprints.exclude(state='closed').aggregate(value=Max('end_on'))['value']
    start = max(today, last_end + timedelta(days=1)) if last_end else today
    form = SprintForm(request.POST if request.method == 'POST' else None, initial={
        'name': f'Sprint {space.sprints.count() + 1}', 'start_on': start, 'end_on': start + timedelta(days=13),
    })
    url = backlog_url(request, space)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            if request.workplace:
                Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            space = space_object(request, space.pk)
            if not manage_space(request, space):
                raise PermissionDenied
            Sprint.objects.create(space=space, **form.cleaned_data)
        return dialog_response(request, form, '', url, saved=True)
    form.submit_label = 'Utwórz sprint'
    return dialog_response(request, form, 'Utwórz sprint', url, background_space=space)


@login_required
@require_http_methods(['GET', 'POST'])
def sprint_plan(request, pk, sprint_pk, operation='edit'):
    space = space_object(request, pk)
    if space.template != 'scrum' or not manage_space(request, space):
        raise PermissionDenied
    sprint = get_object_or_404(space.sprints.exclude(state='closed'), pk=sprint_pk)
    title = {'edit': 'Edytuj sprint', 'start': 'Rozpocznij sprint', 'complete': 'Zakończ sprint'}[operation]
    def build_form(current):
        data = request.POST if request.method == 'POST' else None
        if operation == 'complete':
            form = SprintCloseForm(data, space=space, sprint=current)
        else:
            form = SprintForm(data, initial={name: getattr(current, name) for name in ('name', 'goal', 'start_on', 'end_on')})
            form.submit_label = 'Rozpocznij sprint' if operation == 'start' else 'Zapisz'
        form.planning_summary = planning_totals(visible_items(request).filter(space=space, sprint=current))
        form.sprint_name = current.name
        return form
    form = build_form(sprint)
    url = backlog_url(request, space)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                if request.workplace:
                    Workplace.objects.select_for_update().get(pk=request.workplace.pk)
                Space.objects.select_for_update().get(pk=space.pk)
                space = space_object(request, space.pk)
                if not manage_space(request, space):
                    raise PermissionDenied
                sprint = get_object_or_404(space.sprints.select_for_update(), pk=sprint.pk)
                form = build_form(sprint)
                if sprint.state == 'closed':
                    raise ValidationError('Sprint został już zakończony. Odśwież backlog.')
                if form.is_valid():
                    if operation == 'complete':
                        update_sprint(request, sprint, 'close', form.cleaned_data['destination'])
                    else:
                        for name, value in form.cleaned_data.items():
                            setattr(sprint, name, value)
                        sprint.save()
                        if operation == 'start':
                            update_sprint(request, sprint, 'start')
                    return dialog_response(request, form, '', url, saved=True)
        except ValidationError as error:
            form.add_error(None, error)
    return dialog_response(request, form, title, url, background_space=space)


@login_required
@require_POST
def sprint_action(request, pk, sprint_pk):
    space = space_object(request, pk)
    sprint = get_object_or_404(Sprint, pk=sprint_pk, space=space)
    try:
        update_sprint(request, sprint, request.POST.get('action'))
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    return redirect(backlog_url(request, space))


@login_required
@require_http_methods(['GET', 'POST'])
def members(request, pk):
    space = space_object(request, pk)
    if not manage_space(request, space) or space.visibility != 'private':
        raise PermissionDenied
    form = MemberForm(request.POST if request.method == 'POST' else None, request=request)
    owner = space.private_owner_id == request.user.pk
    if not owner:
        form.fields['role'].choices = [('member', 'Członek'), ('observer', 'Obserwator')]
    url = space_url(request, space, '?view=settings')
    if request.method == 'POST' and form.is_valid():
        from workplaces.models import Workplace
        with transaction.atomic():
            Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            space = Space.objects.select_for_update().get(pk=space.pk)
            project = space
            if not manage_space(request, space):
                raise PermissionDenied
            person = form.cleaned_data['person']
            previous = project.memberships.filter(user=person).first()
            if person.pk == project.private_owner_id or (previous and previous.role == 'admin' and not owner):
                form.add_error('person', 'Nie możesz zmienić roli tej osoby.')
            elif not workplace_people(request.workplace).filter(pk=person.pk).exists():
                form.add_error('person', 'Ta osoba nie należy już do Workspace.')
            else:
                SpaceMembership.objects.update_or_create(space=space, user=person, defaults={'role': form.cleaned_data['role']})
                return dialog_response(request, form, '', url, saved=True)
    return dialog_response(request, form, 'Udostępnij przestrzeń / zmień rolę', url, settings_space=space, settings_tab='members')


@login_required
@require_POST
def remove_member(request, pk, member_pk):
    space = space_object(request, pk)
    if not manage_space(request, space):
        raise PermissionDenied
    with transaction.atomic():
        space = Space.objects.select_for_update().get(pk=space.pk)
        if not manage_space(request, space):
            raise PermissionDenied
        member = get_object_or_404(space.memberships, pk=member_pk)
        if member.user_id == space.private_owner_id or (member.role == 'admin' and space.private_owner_id != request.user.pk):
            raise PermissionDenied
        member.delete()
    return redirect(space_url(request, space, '?view=settings'))


@login_required
@require_http_methods(['GET', 'POST'])
def configuration(request, pk):
    space = space_object(request, pk)
    if not manage_configuration(request, space):
        raise PermissionDenied
    config = space.configuration
    data = request.POST if request.method == 'POST' else None
    StatusSet = formset_factory(StatusForm, extra=1, can_delete=True, max_num=40, validate_max=True)
    TypeSet = formset_factory(TypeForm, extra=1, can_delete=True, max_num=30, validate_max=True)
    FieldSet = formset_factory(CustomFieldForm, extra=1, can_delete=True, max_num=30, validate_max=True)
    sets = [StatusSet(data, initial=config.settings['statuses'], prefix='statuses', form_kwargs={'statuses': config.settings['statuses']}), TypeSet(data, initial=config.settings['types'], prefix='types'), FieldSet(data, initial=config.settings.get('fields', []), prefix='fields')]
    revision = hashlib.sha256(json.dumps(config.settings, sort_keys=True).encode()).hexdigest()
    errors = []
    if request.method == 'POST' and all([formset.is_valid() for formset in sets]):
        settings = {key: [{k: v for k, v in form.cleaned_data.items() if k != 'DELETE'} for form in formset if form.cleaned_data and not form.cleaned_data.get('DELETE')] for key, formset in zip(('statuses', 'types', 'fields'), sets)}
        for key, rows in settings.items():
            if len({row['key'] for row in rows}) != len(rows):
                errors.append('Klucze w każdej sekcji muszą być unikalne.')
        keys = {row['key'] for row in settings['statuses']}
        if {row['category'] for row in settings['statuses']} != set(dict(SpaceTask.STATUS_CHOICES)):
            errors.append('Zachowaj co najmniej jeden status dla każdego stanu zadania.')
        if not settings['types']:
            errors.append('Przestrzeń musi mieć co najmniej jeden typ zgłoszenia.')
        for row in settings['statuses']:
            if any(key not in keys for key in row['transitions']):
                errors.append('Usuń przejścia prowadzące do usuniętego statusu.')
        with transaction.atomic():
            # Match task writes: Workspace -> every affected Space -> configuration.
            # Shared configurations also govern spaces outside the editor's ACL.
            Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            list(Space.objects.filter(configuration=config).order_by('pk').select_for_update().values_list('pk', flat=True))
            space = space_object(request, pk)
            if not manage_configuration(request, space):
                raise PermissionDenied
            config = SpaceConfiguration.objects.select_for_update().get(pk=config.pk)
            current_revision = hashlib.sha256(json.dumps(config.settings, sort_keys=True).encode()).hexdigest()
            if request.POST.get('revision') != current_revision:
                errors.append('Konfiguracja zmieniła się od otwarcia formularza. Odśwież stronę przed zapisem.')
            items = WorkItem.objects.filter(space__configuration=config)
            old_categories = {s['key']: s['category'] for s in config.settings['statuses']}
            used = set(items.values_list('status', flat=True))
            if not used.issubset(keys):
                errors.append('Nie można usunąć statusu używanego przez zadania.')
            if any(row['key'] in used and old_categories.get(row['key']) != row['category'] for row in settings['statuses']):
                errors.append('Najpierw przenieś zadania przed zmianą stanu ich statusu.')
            if items.exclude(work_type__in=[row['key'] for row in settings['types']]).exists():
                errors.append('Nie można usunąć typu używanego przez zadania.')
            if not errors:
                config.settings = settings
                config.save(update_fields=['settings'])
                messages.success(request, 'Konfiguracja została zapisana.')
                return redirect(space_url(request, space, '?view=settings'))
    return render(request, 'spaces/configuration.html', {**base_context(request), 'space': space, 'space_url': space_url(request, space), 'config': config, 'revision': revision, 'sets': [{'title': title, 'formset': formset} for title, formset in zip(('Statusy i przejścia', 'Typy zgłoszeń', 'Pola dodatkowe'), sets)], 'errors': errors}, status=400 if data else 200)
