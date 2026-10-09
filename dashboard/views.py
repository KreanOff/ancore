import unicodedata
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.views.decorators.http import require_GET, require_POST

from tasks.access import visible_to
from workplaces.services import workspace_owner

from accounts.avatar import account_avatar
from accounts.views import _switch_account_context
from documents.models import Document, DocumentLibrary, Folder, WorkspaceDocument
from planner.models import CalendarEvent
from resources.models import Resource
from tasks.models import Task, TaskProject, TaskSection, TaskTag
from workplaces.services import scoped_workplace_app_path, workplaces_for_user
from .pulpit_views import default as default_pulpit
from .for_you import for_you_context
from .recent import recent_views
from .notification_service import DASHBOARD_NOTIFICATION_LIMIT, _dashboard_notifications
from .notification_service import change_notification_state, notification_filters, notification_page, notification_summary


GLOBAL_SEARCH_QUERY_LIMIT = 120
GLOBAL_SEARCH_GROUP_LIMIT = 20
GLOBAL_SEARCH_RECENT_LIMIT = 8


def _normalized_search_text(value):
    normalized = unicodedata.normalize('NFKD', str(value or '').casefold())
    return ''.join(character for character in normalized if unicodedata.category(character) != 'Mn').strip()


def _search_url(base_url, **params):
    query_string = urlencode({key: value for key, value in params.items() if value not in (None, '')})
    return f'{base_url}?{query_string}' if query_string else base_url


def _workspace_app_url(workplace, app_label, suffix=''):
    if workplace is not None:
        return scoped_workplace_app_path(workplace, app_label, suffix=suffix)

    fallback_urls = {
        'tasks': reverse('tasks:tasks'),
        'calendar': reverse('planner:index'),
        'documents': reverse('documents:library'),
        'office': reverse('office:index'),
        'resources': reverse('resources:index'),
        'dashboards': reverse('pulpits:index'),
    }
    base_url = fallback_urls[app_label]
    return f'{base_url}{suffix.lstrip("/")}' if suffix else base_url


def _global_search_result(title, type_label, url, icon, meta='', eyebrow='', *, new_tab=False):
    return {
        'title': str(title or '').strip(),
        'type': type_label,
        'url': url,
        'icon': icon,
        'meta': str(meta or '').strip(),
        'eyebrow': str(eyebrow or '').strip(),
        'new_tab': new_tab,
    }


def _global_search_group(key, label, icon, queryset, serializer):
    rows = list(queryset[:GLOBAL_SEARCH_GROUP_LIMIT + 1])
    return {
        'key': key,
        'label': label,
        'icon': icon,
        'results': [serializer(row) for row in rows[:GLOBAL_SEARCH_GROUP_LIMIT]],
        'has_more': len(rows) > GLOBAL_SEARCH_GROUP_LIMIT,
    }


def _ranked_search_queryset(queryset, field_name, query):
    return queryset.annotate(
        _global_search_rank=Case(
            When(**{f'{field_name}__iexact': query}, then=Value(0)),
            When(**{f'{field_name}__istartswith': query}, then=Value(1)),
            When(**{f'{field_name}__icontains': query}, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    )


def _navigation_search_results(query, workplace):
    tasks_url = _workspace_app_url(workplace, 'tasks')
    calendar_url = _workspace_app_url(workplace, 'calendar')
    entries = (
        ('Dla ciebie', 'Twoje zadania, ulubione i ostatnia praca', scoped_workplace_app_path(workplace, 'for-you') if workplace else reverse('for_you'), 'user-round-check', 'dla ciebie for you przypisane ostatnie'),
        ('Dashboard', 'Strona główna i podsumowanie', reverse('home'), 'layout-dashboard', 'dashboard start podsumowanie'),
        ('Pulpity', 'Własne pulpity i gadżety zespołu', _workspace_app_url(workplace, 'dashboards'), 'layout-dashboard', 'pulpity dashboard gadzety'),
        ('Moje zadania', 'Zadania przypisane do Ciebie', _search_url(tasks_url, view='my-tasks'), 'user-round-check', 'tasks moje zadania'),
        ('Wszystkie zadania', 'Pełna lista zadań', _search_url(tasks_url, view='all-tasks'), 'list-checks', 'tasks lista'),
        ('Przestrzenie', 'Przestrzenie w bieżącym Workspace', _workspace_app_url(workplace, 'spaces'), 'folders', 'przestrzenie projekty kanban scrum'),
        ('Zespoły', 'Osoby i ich zespoły', _workspace_app_url(workplace, 'teams'), 'users', 'zespoly osoby teams'),
        ('Kalendarz', 'Wydarzenia i terminy', calendar_url, 'calendar-days', 'wydarzenia terminy'),
        ('Tagi', 'Wspólne oznaczenia', _search_url(tasks_url, view='tags'), 'tag', 'etykiety labels'),
        ('Dysk', 'Dyski, foldery i pliki', _workspace_app_url(workplace, 'documents'), 'hard-drive', 'dysk dyski pliki foldery dokumenty biblioteka'),
        ('Dokumenty', 'Tworzenie, edycja i przechowywanie dokumentów', _workspace_app_url(workplace, 'office'), 'file-text', 'dokumenty edytor tekst pisanie'),
        ('Zasoby', 'Sprzęt, licencje i narzędzia', _workspace_app_url(workplace, 'resources'), 'package', 'ewidencja wyposażenie zasoby'),
        ('Workspace', 'Miejsca pracy i ich ustawienia', reverse('workplaces:workplaces'), 'briefcase', 'miejsca pracy'),
        ('Ustawienia Ancore', 'Konfiguracja aplikacji', reverse('settings'), 'settings', 'preferencje konfiguracja'),
        ('Profil użytkownika', 'Dane konta i status', reverse('profile'), 'circle-user-round', 'konto użytkownik'),
    )
    normalized_query = _normalized_search_text(query)
    results = []
    for title, meta, url, icon, keywords in entries:
        haystack = _normalized_search_text(f'{title} {meta} {keywords}')
        if normalized_query in haystack:
            results.append(_global_search_result(title, 'Nawigacja', url, icon, meta))
    return results


def _recent_search_results(request):
    """Resolve session IDs against today's Workspace and visibility rules."""
    workplace = getattr(request, 'workplace', None)
    if workplace is None:
        return []
    entries = recent_views(request)
    owner = workspace_owner(request)
    results = {}
    kinds = (
        (Task, 'Zadanie', 'list-checks'),
        (TaskProject, 'Przestrzeń', 'folders'),
        (TaskSection, 'Grupa', 'layers-3'),
    )
    for model, label, icon in kinds:
        ids = [entry['identity'][3] for entry in entries if entry['identity'][2] == model._meta.label_lower]
        if not ids:
            continue
        query = visible_to(model.objects.filter(pk__in=ids), request.user)
        is_task = model is Task
        is_project = model is TaskProject
        if is_task or is_project:
            query = query.filter(user=owner, workplace=workplace)
            if is_task:
                query = query.select_related('section__project', 'parent')
            elif model is TaskProject:
                query = query.select_related('space')
        else:
            query = query.filter(project__user=owner, project__workplace=workplace).select_related('project')
        base = _workspace_app_url(workplace, model._meta.app_label)
        for obj in query:
            meta = ''
            type_label = label
            if is_task:
                detail = 'view-subtask' if obj.parent_id else 'view-task'
                url = _search_url(f'{base}{detail}/{obj.task_id}/', task_pk=obj.pk)
                type_label = 'Podzadanie' if model is Task and obj.parent_id else label
                meta = f'#{obj.task_id}'
                if (obj.section_id and obj.section.project.user_id == owner.pk
                        and obj.section.project.workplace_id == workplace.pk):
                    meta += f' · {obj.section.project.name} · {obj.section.title}'
            elif is_project:
                url = (_workspace_app_url(workplace, 'spaces', f'{obj.space.pk}/')
                       if model is TaskProject and hasattr(obj, 'space') else _search_url(base, project=obj.pk))
                meta = obj.code
            else:
                url = f'{base}groups/{obj.pk}/'
                meta = obj.project.name
            results[(model._meta.label_lower, obj.pk)] = _global_search_result(
                obj.name if is_project else obj.title, type_label, url, icon, meta,
            )
    return [results[tuple(entry['identity'][2:])] for entry in entries
            if tuple(entry['identity'][2:]) in results][:GLOBAL_SEARCH_RECENT_LIMIT]


@login_required
@require_GET
def global_search(request):
    query = (request.GET.get('q') or '').strip()[:GLOBAL_SEARCH_QUERY_LIMIT]
    if not query and request.GET.get('recent') == '1':
        recent = _recent_search_results(request)
        response = JsonResponse({
            'query': '', 'recent': True, 'total': len(recent), 'truncated': False,
            'groups': [{'key': 'recent', 'label': 'Ostatnio oglądane', 'icon': 'history',
                        'results': recent, 'has_more': False}] if recent else [],
        })
        response['Cache-Control'] = 'no-store'
        return response
    if len(query) < 2:
        return JsonResponse({
            'query': query,
            'groups': [],
            'total': 0,
            'minimum_query_length': 2,
        })

    user = workspace_owner(request)
    workplace = getattr(request, 'workplace', None)
    tasks_url = _workspace_app_url(workplace, 'tasks')
    calendar_url = _workspace_app_url(workplace, 'calendar')
    numeric_query = int(query) if query.isdecimal() else None

    task_filter = (
        Q(title__icontains=query)
        | Q(work_item__key__icontains=query)
        | Q(description__icontains=query)
        | Q(blocked_reason__icontains=query)
        | Q(section__title__icontains=query)
        | Q(section__project__name__icontains=query)
        | Q(tags__name__icontains=query)
        | Q(activities__message__icontains=query)
    )
    if numeric_query is not None:
        task_filter |= Q(task_id=numeric_query)

    task_queryset = visible_to(Task.objects.all(), request.user).filter(user=user).filter(task_filter)
    project_queryset = visible_to(TaskProject.objects.all(), request.user).filter(user=user).filter(
        Q(name__icontains=query)
        | Q(description__icontains=query)
        | Q(code__icontains=query)
        | Q(source__icontains=query)
        | Q(company__name__icontains=query)
        | Q(responsible_user__first_name__icontains=query)
        | Q(responsible_user__middle_name__icontains=query)
        | Q(responsible_user__last_name__icontains=query)
        | Q(responsible_user__email__icontains=query)
        | Q(project_notes__message__icontains=query)
    )
    section_queryset = visible_to(TaskSection.objects.all(), request.user).filter(project__user=user).filter(
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(code__icontains=query)
        | Q(project__name__icontains=query)
        | Q(project__code__icontains=query)
        | Q(section_notes__message__icontains=query)
    )
    tag_queryset = TaskTag.objects.filter(user=user).filter(
        Q(name__icontains=query)
        | Q(description__icontains=query)
        | Q(code__icontains=query)
        | Q(owner_label__icontains=query)
        | Q(usage_notes__icontains=query)
        | Q(automation_rules__icontains=query)
        | Q(tag_notes__message__icontains=query)
    )
    event_queryset = CalendarEvent.objects.filter(user=user).filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    )

    if workplace is not None:
        task_queryset = task_queryset.filter(workplace=workplace)
        project_queryset = project_queryset.filter(workplace=workplace)
        section_queryset = section_queryset.filter(project__workplace=workplace)
        tag_queryset = tag_queryset.filter(workplace=workplace)
        event_queryset = event_queryset.filter(workplace=workplace)

    navigation_results = _navigation_search_results(query, workplace)
    groups = []
    if navigation_results:
        groups.append({
            'key': 'navigation',
            'label': 'Nawigacja',
            'icon': 'compass',
            'results': navigation_results,
            'has_more': False,
        })

    groups.extend((
        _global_search_group(
            'tasks',
            'Zadania',
            'list-todo',
            _ranked_search_queryset(
                task_queryset.select_related('section', 'section__project', 'parent').distinct(),
                'title',
                query,
            ).order_by('_global_search_rank', '-created_at', '-id'),
            lambda task: _global_search_result(
                task.title,
                'Podzadanie' if task.parent_id else 'Zadanie',
                _search_url(f'{tasks_url}{"view-subtask" if task.parent_id else "view-task"}/{task.task_id}/', task_pk=task.pk),
                '',
                ' · '.join(part for part in (
                    f'#{task.task_id}',
                    task.section.project.name if task.section_id else '',
                    task.section.title if task.section_id else '',
                ) if part),
            ),
        ),
        _global_search_group(
            'projects',
            'Przestrzenie',
            'folders',
            _ranked_search_queryset(
                project_queryset.select_related('company', 'responsible_user').distinct(),
                'name',
                query,
            ).order_by('_global_search_rank', 'name', 'id'),
            lambda project: _global_search_result(
                project.name,
                'Przestrzeń',
                _workspace_app_url(workplace, 'spaces') + f'{project.space.pk}/' if hasattr(project, 'space') else _search_url(tasks_url, project=project.id),
                '',
                ' · '.join(part for part in (project.code, project.company.name if project.company_id else '') if part),
            ),
        ),
        _global_search_group(
            'groups',
            'Grupy',
            'folder-open',
            _ranked_search_queryset(
                section_queryset.select_related('project').distinct(),
                'title',
                query,
            ).order_by('_global_search_rank', 'project__name', 'order', 'id'),
            lambda section: _global_search_result(
                section.title,
                'Grupa',
                f'{tasks_url}groups/{section.id}/',
                '',
                ' · '.join(part for part in (section.project.name, section.full_code) if part),
            ),
        ),
        _global_search_group(
            'tags',
            'Tagi',
            'tag',
            _ranked_search_queryset(tag_queryset.distinct(), 'name', query).order_by('_global_search_rank', 'name', 'id'),
            lambda tag: _global_search_result(
                tag.name,
                'Tag',
                _search_url(tasks_url, view='tags', q=tag.name),
                tag.icon or 'tag',
                ' · '.join(part for part in (tag.code, tag.get_category_display()) if part),
            ),
        ),
        _global_search_group(
            'calendar',
            'Kalendarz',
            'calendar-days',
            _ranked_search_queryset(event_queryset, 'title', query).order_by('_global_search_rank', 'start', 'id'),
            lambda event: _global_search_result(
                event.title,
                'Wydarzenie',
                _search_url(calendar_url, event=event.id, date=timezone.localtime(event.start).date().isoformat()),
                'calendar-clock',
                date_format(timezone.localtime(event.start), 'd.m.Y, H:i'),
            ),
        ),
        _global_search_group(
            'workplaces',
            'Workspace',
            'briefcase',
            workplaces_for_user(request.user).filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(code__icontains=query)
            ).order_by('name', 'id'),
            lambda item: _global_search_result(
                item.name,
                'Workspace',
                reverse('workplaces:workplace-home', args=[item.slug]),
                'briefcase-business',
                ' · '.join(part for part in (item.code, item.description) if part),
                'Bieżący' if workplace is not None and item.id == workplace.id else '',
            ),
        ),
    ))

    documents_url = _workspace_app_url(workplace, 'documents')
    resources_url = _workspace_app_url(workplace, 'resources')
    groups.append(_global_search_group(
        'resources', 'Zasoby', 'package',
        _ranked_search_queryset(Resource.objects.filter(owner=user, workplace=workplace).filter(
            Q(name__icontains=query) | Q(inventory_number__icontains=query)
            | Q(serial_number__icontains=query) | Q(location__icontains=query) | Q(notes__icontains=query)
        ), 'name', query).order_by('_global_search_rank', 'name', 'pk'),
        lambda item: _global_search_result(item.name, 'Zasób', f'{resources_url}{item.pk}/edit/', item.icon,
            ' · '.join(part for part in (item.inventory_number, item.get_kind_display(), item.get_status_display()) if part)),
    ))
    office_url = _workspace_app_url(workplace, 'office')
    groups.extend((
        _global_search_group(
            'office-documents', 'Dokumenty', 'file-text',
            WorkspaceDocument.objects.filter(owner=user, workplace=workplace, deleted_at__isnull=True).filter(
                Q(title__icontains=query) | Q(filename__icontains=query)
            ),
            lambda item: _global_search_result(item.title, 'Dokument',
                f'{office_url}{item.pk}/' + ('editor/' if item.has_full_editor else ('preview/' if item.kind == WorkspaceDocument.Kind.FILE else '')),
                'file-text', 'Dokumenty', new_tab=item.has_full_editor),
        ),
        _global_search_group(
            'document-libraries', 'Dyski', 'hard-drive',
            DocumentLibrary.objects.filter(owner=user, workplace=workplace).filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            ),
            lambda item: _global_search_result(item.name, 'Dysk',
                                                _search_url(documents_url, library=item.pk), 'hard-drive', item.description),
        ),
        _global_search_group(
            'documents', 'Pliki', 'files',
            Document.objects.filter(owner=user, workplace=workplace, deleted_at__isnull=True).filter(
                Q(title__icontains=query) | Q(filename__icontains=query)
                | Q(description__icontains=query)
            ).select_related('folder', 'library').distinct(),
            lambda item: _global_search_result(item.title, 'Plik',
                f'{documents_url}{item.pk}/' + ('editor/' if item.office_type else 'preview/'), item.icon,
                ' / '.join(part for part in (item.library.name, item.folder.name if item.folder else '') if part),
                new_tab=bool(item.office_type)),
        ),
        _global_search_group(
            'document-folders', 'Foldery', 'folder',
            Folder.objects.filter(owner=user, workplace=workplace, name__icontains=query).select_related('library'),
            lambda item: _global_search_result(item.name, 'Folder', _search_url(documents_url, library=item.library_id, folder=item.pk), 'folder', item.library.name),
        ),
    ))
    groups = [group for group in groups if group['results']]
    response = JsonResponse({
        'query': query,
        'groups': groups,
        'total': sum(len(group['results']) for group in groups),
        'truncated': any(group['has_more'] for group in groups),
        'workspace': workplace.name if workplace is not None else '',
    })
    response['Cache-Control'] = 'no-store'
    return response


@login_required
def settings(request):
    return render(request, 'dashboard/settings.html', {
        'current_account_avatar': account_avatar(request.user),
        'switch_accounts': _switch_account_context(request),
    })


@login_required
@require_GET
def for_you(request):
    if getattr(request, 'workplace', None) is None:
        return redirect('workplaces:workplaces')
    response = render(request, 'dashboard/for_you.html', for_you_context(request))
    response['Cache-Control'] = 'no-store'
    return response


@login_required
@require_GET
def home(request):
    return default_pulpit(request)


@login_required
@require_GET
def notifications(request):
    is_panel_request = (request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                        and 'text/html' not in request.headers.get('Accept', ''))
    if request.GET.get('summary') != '1' and not is_panel_request:
        return redirect('home')
    summary = notification_summary(request.user)
    if request.GET.get('summary') == '1':
        response = JsonResponse(summary)
        response['Cache-Control'] = 'no-store'
        return response
    try:
        context = notification_page(request.user, notification_filters(request.user, request.GET), request.GET.get('cursor', ''))
    except ValueError as error:
        return JsonResponse({'error': str(error)}, status=400)
    context.update(summary)
    response = JsonResponse({
        **summary,
        'count': len(context['dashboard_notifications']),
        'total': context['dashboard_notification_count'],
        'filtered_unread_count': context['filtered_unread_count'],
        'snapshot': context['snapshot'],
        'next_cursor': context['next_cursor'],
        'html': render_to_string(
            'dashboard/includes/notification_list.html',
            context,
            request=request,
        ),
    })
    response['Cache-Control'] = 'no-store'
    return response


@login_required
@require_POST
def notification_action(request):
    try:
        change_notification_state(request.user, request.POST)
    except ValueError as error:
        return JsonResponse({'error': str(error)}, status=400)
    response = JsonResponse({'ok': True, **notification_summary(request.user)})
    response['Cache-Control'] = 'no-store'
    return response
