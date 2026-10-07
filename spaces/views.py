from urllib.parse import urlencode
from datetime import timedelta
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
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from core.task_numbering import lock_task_numbers
from accounts.avatar import account_avatar
from dashboard.recent import remember_view
from tasks.access import editable_to, visible_to
from tasks.models import Task, TaskProject, TaskProjectMembership
from workplaces.models import Workplace
from workplaces.services import workplace_people, workspace_owner
from .avatars import delete_avatar_after_commit
from .defaults import TEMPLATES, issue_type_icon, template_settings
from .forms import CustomFieldForm, ItemForm, MemberForm, SpaceAvatarForm, SpaceForm, SprintForm, StatusForm, TypeForm
from .models import Space, SpaceConfiguration, Sprint, WorkItem
from .services import app_url, can_manage_spaces, default_section, ensure_space, ensure_work_item, manageable_spaces, manage_configuration, manage_space, record, set_status, task_url, teams_for, transition_allowed, update_sprint, visible_items, visible_spaces
from .summary import filter_summary_items, space_summary


def space_object(request, pk):
    return get_object_or_404(visible_spaces(request), pk=pk)


def base_context(request):
    return {'spaces_url': app_url(request), 'spaces_manage_url': app_url(request, 'manage/'), 'teams_url': app_url(request, app='teams'), 'all_items_url': app_url(request, 'items/')}


def decorate_items(request, items):
    result = list(items)
    editable_ids = set(editable_to(Task.objects.filter(pk__in=[i.task_id for i in result]), request.user).values_list('pk', flat=True))
    counts = {row['pk']: row for row in Task.objects.filter(pk__in=[i.task_id for i in result]).annotate(
        tags_total=Count('tags', distinct=True), attachments_total=Count('attachments', distinct=True),
    ).values('pk', 'tags_total', 'attachments_total')}
    for item in result:
        item.url = task_url(request, item.task)
        item.edit_url = app_url(request, f'items/{item.pk}/edit/')
        item.action_url = app_url(request, f'items/{item.pk}/action/')
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


def index_context(request, management=False):
    # Covers projects created by old integrations via bulk_create, too.
    for project in visible_to(TaskProject.objects.filter(user=workspace_owner(request), workplace=request.workplace, space__isnull=True), request.user):
        ensure_space(project)
    query = request.GET.get('q', '').strip()[:120]
    tab = request.GET.get('tab', 'all')
    spaces = manageable_spaces(request) if management else visible_spaces(request)
    if query:
        spaces = spaces.filter(Q(project__name__icontains=query) | Q(key__icontains=query))
    if not management and tab == 'favorites':
        spaces = spaces.filter(project__favorited_by=request.user)
    elif not management and tab == 'private':
        spaces = spaces.filter(project__visibility='private')
    kind = request.GET.get('kind')
    if kind in {'software', 'business', 'service'}:
        spaces = spaces.filter(kind=kind)
    management_filter = request.GET.get('management', '')
    if management and management_filter in {'team', 'company'}:
        spaces = spaces.filter(management=management_filter)
    if management:
        spaces = spaces.select_related('project__responsible_user', 'project__private_owner', 'project__user')
    page = Paginator(spaces.order_by('project__name', 'pk'), 30).get_page(request.GET.get('page'))
    favorites = set(TaskProject.objects.filter(favorited_by=request.user).values_list('pk', flat=True))
    counts = {row['space_id']: row['count'] for row in visible_items(request).filter(space__in=page.object_list).values('space_id').annotate(count=Count('pk'))}
    activity = {row['space_id']: row['last_activity'] for row in visible_items(request).filter(space__in=page.object_list).values('space_id').annotate(last_activity=Max('task__activities__created_at'))} if management else {}
    managed_ids = set(manageable_spaces(request).filter(pk__in=page.object_list).values_list('pk', flat=True)) if not management else set()
    for space in page:
        space.url = app_url(request, f'{space.pk}/')
        space.favorite_url = app_url(request, f'{space.pk}/favorite/')
        space.favorite = space.project_id in favorites
        space.item_count = counts.get(space.pk, 0)
        space.settings_url = space.url + '?view=settings'
        space.can_manage = management or space.pk in managed_ids
        space.edit_url = app_url(request, f'{space.pk}/edit/')
        if management:
            space.edit_url = app_url(request, f'manage/{space.pk}/edit/')
            space.configuration_url = app_url(request, f'{space.pk}/configuration/') if manage_configuration(request, space) else ''
            space.leader = space.project.responsible_user or space.project.private_owner or space.project.user
            space.leader_avatar = account_avatar(space.leader)
            space.last_activity = activity.get(space.pk)
    return {**base_context(request), 'page': page, 'query': query, 'tab': tab, 'kind': kind, 'management_filter': management_filter, 'create_url': app_url(request, 'manage/create/' if management else 'create/'), 'templates': TEMPLATES}


@login_required
@require_GET
def index(request):
    return render(request, 'spaces/index.html', index_context(request))


@login_required
@require_GET
def manage(request):
    if not can_manage_spaces(request):
        raise PermissionDenied
    return render(request, 'spaces/manage.html', index_context(request, management=True))


@login_required
@require_GET
def search(request):
    query = request.GET.get('q', '').strip()[:120]
    results = list(visible_spaces(request).filter(
        Q(project__name__icontains=query) | Q(key__icontains=query),
    ).order_by('project__name', 'pk')[:21]) if query else []
    has_more = len(results) > 20
    results = results[:20]
    for space in results:
        space.url = app_url(request, f'{space.pk}/')
    response = JsonResponse({
        'html': render_to_string('spaces/search_results.html', {'results': results, 'has_more': has_more}),
        'count': len(results),
    })
    response['Cache-Control'] = 'private, no-store'
    return response


def detail_context(request, space, view):
    allowed_views = {'overview', 'board', 'list', 'timeline', 'reports', 'settings'}
    if space.template in {'kanban', 'scrum'}:
        allowed_views.add('backlog')
    if view not in allowed_views:
        view = 'overview'
    base = app_url(request, f'{space.pk}/')
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
        ('settings', 'Ustawienia przestrzeni', 'settings'),
    ]
    query = request.GET.get('q', '').strip()[:120]
    items = visible_items(request).filter(space=space)
    assignee_options = get_user_model().objects.filter(pk__in=items.order_by().values('task__assignee_id')).order_by('first_name', 'last_name', 'pk')
    type_options, type_filter = issue_type_filters(request, space)
    if type_filter:
        items = items.filter(work_type=type_filter)
    group = request.GET.get('group', '')
    if group.isdecimal() and len(group) < 19:
        items = items.filter(task__section_id=int(group))
    if query:
        items = items.filter(Q(task__title__icontains=query) | Q(key__icontains=query))
    team = request.GET.get('team', '')
    if team.isdecimal() and len(team) < 19:
        items = items.filter(team_id=int(team))
    now = timezone.now()
    items, summary_filters = filter_summary_items(request, space, items, now)
    if view == 'overview':
        return {
            **base_context(request), 'space': space, 'space_url': base, 'view': view,
            'navigation': [{'key': k, 'label': l, 'icon': icon, 'url': base + ('?view=' + k if k != 'overview' else '')} for k, l, icon in navigation],
            'can_manage': manage_space(request, space),
            'can_edit': editable_to(TaskProject.objects.filter(pk=space.project_id), request.user).exists(),
            'create_item_url': base + 'items/create/', 'summary': space_summary(request, space, items, now),
        }
    active_sprint = space.sprints.filter(state='active').first()
    all_items = items
    if view == 'board':
        items = items.filter(sprint=active_sprint) if space.template == 'scrum' and active_sprint else items.filter(in_backlog=False)
        if space.template == 'scrum' and not active_sprint:
            items = items.none()
    if view == 'backlog':
        items = items.exclude(task__status='closed').filter(Q(sprint__isnull=True) | ~Q(sprint__state='closed'))
        if space.template == 'kanban':
            items = items.filter(in_backlog=True)
    if view == 'timeline':
        items = items.filter(Q(start_on__isnull=False) | Q(task__due_at__isnull=False)).order_by('start_on', 'task__due_at', 'pk')
    else:
        items = items.order_by('rank', 'pk')
    page = Paginator(items, 100).get_page(request.GET.get('page'))
    rows = decorate_items(request, page.object_list)
    timeline = None
    if view == 'timeline' and rows:
        dates = []
        for item in rows:
            due = timezone.localtime(item.task.due_at).date() if item.task.due_at else None
            item.timeline_start = item.start_on or due
            item.timeline_end = max(item.timeline_start, due or item.timeline_start)
            dates.extend([item.timeline_start, item.timeline_end])
        start, end = min(dates), max(dates)
        duration = max((end - start).days + 1, 7)
        timeline = {'start': start, 'end': start + timedelta(days=duration - 1)}
        for item in rows:
            item.timeline_left = str(round((item.timeline_start - start).days / duration * 100, 2))
            item.timeline_width = str(round(max((item.timeline_end - item.timeline_start).days + 1, 1) / duration * 100, 2))
    counts = dict(all_items.order_by().values_list('status').annotate(n=Count('pk')))
    column_counts = dict(items.order_by().values_list('status').annotate(n=Count('pk')))
    columns = [{**s, 'items': [i for i in rows if i.status == s['key']], 'count': column_counts.get(s['key'], 0)} for s in space.statuses]
    sprints = list(space.sprints.all())
    for sprint in sprints:
        sprint.action_url = base + f'sprints/{sprint.pk}/action/'
        sprint.visible_items = [i for i in rows if i.sprint_id == sprint.pk]
        sprint.visible_count = all_items.filter(sprint=sprint).count()
        sprint.finished_count = all_items.filter(sprint=sprint, task__status='closed').count()
    stats = {'all': all_items.count(), 'closed': all_items.filter(task__status='closed').count(), 'overdue': all_items.filter(task__due_at__lt=now).exclude(task__status='closed').count(), 'points': all_items.aggregate(n=Sum('points'))['n'] or 0}
    return {**base_context(request), **summary_filters, 'assignee_options': assignee_options, 'priority_options': Task.PRIORITY_CHOICES, 'space': space, 'space_url': base, 'timeline': timeline, 'view': view, 'navigation': [{'key': k, 'label': l, 'icon': icon, 'url': base + ('?view=' + k if k != 'overview' else '')} for k, l, icon in navigation], 'page': page, 'items': rows, 'columns': columns, 'query': query, 'stats': stats, 'status_counts': [{**s, 'count': counts.get(s['key'], 0)} for s in space.statuses], 'active_sprint': active_sprint, 'sprints': sprints, 'backlog_items': [i for i in rows if not i.sprint_id], 'can_manage': manage_space(request, space), 'can_configure': manage_configuration(request, space), 'can_edit': editable_to(TaskProject.objects.filter(pk=space.project_id), request.user).exists(), 'create_item_url': base + 'items/create/', 'sprint_create_url': base + 'sprints/create/', 'edit_url': base + 'edit/', 'configuration_url': base + 'configuration/', 'member_url': base + 'members/', 'members': space.project.memberships.filter(user__in=workplace_people(request.workplace)).select_related('user'), 'space_teams': teams_for(request).filter(spaces=space), 'team_filter': team, 'group_filter': group if group.isdecimal() and len(group) < 19 else '', 'type_options': type_options, 'type_filter': type_filter}


@login_required
@require_GET
def detail(request, pk):
    space = space_object(request, pk)
    remember_view(request, space.project)
    return render(request, 'spaces/detail.html', detail_context(request, space, request.GET.get('view', 'overview')))


@login_required
@require_GET
def all_items(request):
    tasks_without_metadata = visible_to(Task.objects.filter(user=workspace_owner(request), workplace=request.workplace, work_item__isnull=True), request.user)
    for task in tasks_without_metadata:
        ensure_work_item(task)
    items = visible_items(request)
    type_options, type_filter = issue_type_filters(request)
    if type_filter:
        items = items.filter(work_type=type_filter)
    query = request.GET.get('q', '').strip()[:120]
    if query:
        items = items.filter(Q(key__icontains=query) | Q(task__title__icontains=query))
    if request.GET.get('assignee') == 'me':
        items = items.filter(task__assignee=request.user)
    page = Paginator(items.order_by('-task__created_at', '-pk'), 50).get_page(request.GET.get('page'))
    return render(request, 'spaces/items.html', {**base_context(request), 'items': decorate_items(request, page.object_list), 'page': page, 'query': query, 'assignee_filter': request.GET.get('assignee', ''), 'type_options': type_options, 'type_filter': type_filter})


def dialog_response(request, form, title, return_url, saved=False, directory=False, management=False):
    if saved:
        if request.headers.get('X-Work-Modal') == 'true':
            return JsonResponse({'saved': True, 'url': return_url})
        return redirect(return_url)
    modal = {'form': form, 'title': title, 'action': request.get_full_path(), 'return_url': return_url}
    context = {**base_context(request), 'modal': modal}
    status = 400 if request.method == 'POST' else 200
    if request.headers.get('X-Work-Modal') == 'true':
        return JsonResponse({'html': render_to_string('spaces/form.html', context, request=request)}, status=status)
    if directory:
        context.update(index_context(request, management=management))
        modal['directory_url'] = return_url
        return render(request, 'spaces/manage.html' if management else 'spaces/index.html', context, status=status)
    return render(request, 'spaces/form_page.html', context, status=status)


@login_required
@require_http_methods(['GET', 'POST'])
def edit(request, pk=None, management=False):
    if management and not can_manage_spaces(request):
        raise PermissionDenied
    space = space_object(request, pk) if pk else None
    if space and not manage_space(request, space):
        raise PermissionDenied
    form = SpaceForm(request.POST if request.method == 'POST' else None, request=request, space=space)
    url = app_url(request, 'manage/') if management else app_url(request, f'{pk}/?view=settings') if pk else app_url(request)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        try:
            with transaction.atomic():
                if space is None:
                    project = TaskProject.objects.create(name=data['name'], description=data['description'], user=workspace_owner(request), workplace=request.workplace, visibility=data['visibility'], private_owner=request.user if data['visibility'] == 'private' else None, responsible_user=request.user)
                    space = Space.objects.select_for_update().get(project=project)
                    config = data.get('configuration') or space.configuration
                    if not data.get('configuration'):
                        config.shared = data['management'] == 'company'
                        config.settings = template_settings(data['template'])
                        config.save()
                    space.key, space.kind, space.template, space.management, space.configuration = data['key'], data['kind'], data['template'], data['management'], config
                    space.save()
                    default_section(space)
                else:
                    project = TaskProject.objects.select_for_update().get(pk=space.project_id)
                    project.name, project.description = data['name'], data['description']
                    visibility_changed = project.visibility != data['visibility']
                    if visibility_changed:
                        project.visibility = data['visibility']
                        project.private_owner = request.user if project.visibility == 'private' else None
                    project.save()
                    if visibility_changed:
                        project.memberships.all().delete()
                url = app_url(request, 'manage/' if management else f'{space.pk}/')
        except IntegrityError:
            form.add_error('key', 'Ten klucz został właśnie zajęty. Wybierz inny.')
        else:
            return dialog_response(request, form, '', url, saved=True)
    return dialog_response(request, form, 'Ustawienia przestrzeni' if pk else 'Utwórz przestrzeń', url, directory=pk is None or management, management=management)


@login_required
@require_http_methods(['GET', 'POST'])
def avatar_edit(request, pk):
    space = space_object(request, pk)
    if not manage_space(request, space):
        raise PermissionDenied
    form = SpaceAvatarForm(request.POST if request.method == 'POST' else None, request.FILES or None, space=space)
    url = app_url(request, f'{pk}/')
    if request.method == 'POST' and form.is_valid():
        saved_file = None
        try:
            with transaction.atomic():
                Workplace.objects.select_for_update().get(pk=request.workplace.pk)
                TaskProject.objects.select_for_update().get(pk=space.project_id)
                space = get_object_or_404(visible_spaces(request).select_for_update(of=('self',)), pk=pk)
                if not manage_space(request, space):
                    raise PermissionDenied
                old_photo, storage = space.avatar_photo.name, space.avatar_photo.storage
                uploaded = form.cleaned_data.get('avatar_photo')
                choice = form.cleaned_data['avatar']
                if uploaded:
                    space.avatar_photo.save(uploaded.name, uploaded, save=False)
                    saved_file = (storage, space.avatar_photo.name)
                elif choice != 'upload':
                    space.avatar_photo = ''
                elif not old_photo:
                    form.add_error('avatar_photo', 'Obraz został usunięty. Wybierz go ponownie.')
                if not form.errors:
                    if choice != 'upload':
                        space.avatar = '' if choice == 'auto' else choice
                    space.save(update_fields=['avatar', 'avatar_photo'])
                    if old_photo != space.avatar_photo.name:
                        delete_avatar_after_commit(storage, old_photo)
        except Exception:
            if saved_file:
                try:
                    saved_file[0].delete(saved_file[1])
                except OSError:
                    logging.getLogger(__name__).exception('Failed to clean up a space avatar after rollback')
            raise
        if not form.errors:
            return dialog_response(request, form, '', url, saved=True)
    return dialog_response(request, form, 'Wybierz awatar', url)


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
    if space.project.favorited_by.filter(pk=request.user.pk).exists():
        space.project.favorited_by.remove(request.user)
    else:
        space.project.favorited_by.add(request.user)
    if request.headers.get('X-Space-Navigation') == 'true':
        return JsonResponse({'saved': True})
    return_url = request.POST.get('next', '')
    if return_url and url_has_allowed_host_and_scheme(return_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(return_url)
    return redirect(app_url(request, 'manage/' if request.POST.get('directory') == 'manage' else ''))


@login_required
@require_http_methods(['GET', 'POST'])
def item_edit(request, pk=None, space_pk=None):
    item = get_object_or_404(visible_items(request), pk=pk) if pk else None
    space = space_object(request, item.space_id if item else space_pk)
    if item:
        if not editable_to(Task.objects.filter(pk=item.task_id), request.user).exists():
            raise PermissionDenied
    elif not editable_to(TaskProject.objects.filter(pk=space.project_id), request.user).exists():
        raise PermissionDenied
    form = ItemForm(request.POST if request.method == 'POST' else None, request=request, space=space, item=item)
    url = app_url(request, f'{space.pk}/?view=list')
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        with lock_task_numbers(space.project.user_id):
            task = Task.objects.select_for_update().get(pk=item.task_id) if item else Task(user=workspace_owner(request), workplace=request.workplace, visibility='public')
            for name in ('title', 'description', 'priority', 'assignee', 'due_at'):
                setattr(task, name, data[name])
            task.section = data.get('section') or default_section(space)
            task._activity_actor = request.user
            task.save()
            item = WorkItem.objects.select_for_update().get(task=task)
            old_type, old_type_label = item.work_type, item.get_work_type_display()
            for name in ('work_type', 'team', 'sprint', 'epic', 'points', 'start_on', 'in_backlog'):
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
    return dialog_response(request, form, f'Edytuj {item.key}' if item else 'Utwórz zadanie', url)


@login_required
@require_POST
def item_action(request, pk):
    item = get_object_or_404(visible_items(request), pk=pk)
    if not item.space_id or not editable_to(Task.objects.filter(pk=item.task_id), request.user).exists():
        raise PermissionDenied
    try:
        with lock_task_numbers(item.task.user_id):
            item = WorkItem.objects.select_for_update().get(pk=item.pk)
            action = request.POST.get('action')
            if action == 'status':
                set_status(request, item, request.POST.get('status'))
            elif action in {'backlog', 'board'}:
                item.in_backlog = action == 'backlog'
                item.sprint = None
                item.save(update_fields=['in_backlog', 'sprint'])
                record(item, request.user, 'updated', 'przeniósł zadanie do backlogu' if item.in_backlog else 'przeniósł zadanie na tablicę')
            elif action in {'up', 'down'}:
                Space.objects.select_for_update().get(pk=item.space_id)
                ordered = list(visible_items(request).filter(space_id=item.space_id, sprint_id=item.sprint_id).order_by('rank', 'pk'))
                index = next(i for i, row in enumerate(ordered) if row.pk == item.pk)
                target = index + (-1 if action == 'up' else 1)
                if 0 <= target < len(ordered):
                    other = ordered[target]
                    if not editable_to(Task.objects.filter(pk=other.task_id), request.user).exists():
                        raise PermissionDenied
                    if item.rank == other.rank:
                        raise ValidationError('Zadania mają tę samą kolejność. Przenieś zadanie do innego sprintu i wróć do planowania.')
                    item.rank, other.rank = other.rank, item.rank
                    WorkItem.objects.bulk_update([item, other], ['rank'])
                    record(item, request.user, 'updated', 'zmienił kolejność zadania')
            else:
                return HttpResponseBadRequest('Nieprawidłowa operacja.')
    except ValidationError as error:
        if request.headers.get('X-Work-Action') == 'true':
            return JsonResponse({'error': ' '.join(error.messages)}, status=400)
        messages.error(request, ' '.join(error.messages))
    url = app_url(request, f'{item.space_id}/?view=' + ('backlog' if request.POST.get('return_view') == 'backlog' else 'board'))
    if request.headers.get('X-Work-Action') == 'true':
        return JsonResponse({'saved': True, 'url': url})
    return redirect(url)


@login_required
@require_http_methods(['GET', 'POST'])
def sprint_create(request, pk):
    space = space_object(request, pk)
    if space.template != 'scrum' or not manage_space(request, space):
        raise PermissionDenied
    form = SprintForm(request.POST if request.method == 'POST' else None)
    url = app_url(request, f'{pk}/?view=backlog')
    if request.method == 'POST' and form.is_valid():
        Sprint.objects.create(space=space, **form.cleaned_data)
        return dialog_response(request, form, '', url, saved=True)
    return dialog_response(request, form, 'Utwórz sprint', url)


@login_required
@require_POST
def sprint_action(request, pk, sprint_pk):
    space = space_object(request, pk)
    sprint = get_object_or_404(Sprint, pk=sprint_pk, space=space)
    try:
        update_sprint(request, sprint, request.POST.get('action'))
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    return redirect(app_url(request, f'{pk}/?view=backlog'))


@login_required
@require_http_methods(['GET', 'POST'])
def members(request, pk):
    space = space_object(request, pk)
    if not manage_space(request, space) or space.project.visibility != 'private':
        raise PermissionDenied
    form = MemberForm(request.POST if request.method == 'POST' else None, request=request)
    owner = space.project.private_owner_id == request.user.pk
    if not owner:
        form.fields['role'].choices = [('member', 'Członek'), ('observer', 'Obserwator')]
    url = app_url(request, f'{pk}/?view=settings')
    if request.method == 'POST' and form.is_valid():
        from workplaces.models import Workplace
        with transaction.atomic():
            Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            project = TaskProject.objects.select_for_update().get(pk=space.project_id)
            space.project = project
            if not manage_space(request, space):
                raise PermissionDenied
            person = form.cleaned_data['person']
            previous = project.memberships.filter(user=person).first()
            if person.pk == project.private_owner_id or (previous and previous.role == 'admin' and not owner):
                form.add_error('person', 'Nie możesz zmienić roli tej osoby.')
            elif not workplace_people(request.workplace).filter(pk=person.pk).exists():
                form.add_error('person', 'Ta osoba nie należy już do Workspace.')
            else:
                TaskProjectMembership.objects.update_or_create(project=project, user=person, defaults={'role': form.cleaned_data['role']})
                return dialog_response(request, form, '', url, saved=True)
    return dialog_response(request, form, 'Udostępnij przestrzeń / zmień rolę', url)


@login_required
@require_POST
def remove_member(request, pk, member_pk):
    space = space_object(request, pk)
    if not manage_space(request, space):
        raise PermissionDenied
    with transaction.atomic():
        space.project = TaskProject.objects.select_for_update().get(pk=space.project_id)
        if not manage_space(request, space):
            raise PermissionDenied
        member = get_object_or_404(space.project.memberships, pk=member_pk)
        if member.user_id == space.project.private_owner_id or (member.role == 'admin' and space.project.private_owner_id != request.user.pk):
            raise PermissionDenied
        member.delete()
    return redirect(app_url(request, f'{pk}/?view=settings'))


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
        if {row['category'] for row in settings['statuses']} != set(dict(Task.STATUS_CHOICES)):
            errors.append('Zachowaj co najmniej jeden status dla każdego stanu zadania.')
        if not settings['types']:
            errors.append('Przestrzeń musi mieć co najmniej jeden typ zgłoszenia.')
        for row in settings['statuses']:
            if any(key not in keys for key in row['transitions']):
                errors.append('Usuń przejścia prowadzące do usuniętego statusu.')
        with lock_task_numbers(space.project.user_id):
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
                return redirect(app_url(request, f'{pk}/?view=settings'))
    return render(request, 'spaces/configuration.html', {**base_context(request), 'space': space, 'space_url': app_url(request, f'{pk}/'), 'config': config, 'revision': revision, 'sets': [{'title': title, 'formset': formset} for title, formset in zip(('Statusy i przejścia', 'Typy zgłoszeń', 'Pola dodatkowe'), sets)], 'errors': errors}, status=400 if data else 200)
