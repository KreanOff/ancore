import unicodedata
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import redirect
from core.frontend import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.views.decorators.http import require_GET, require_POST

from workplaces.services import workspace_owner

from accounts.avatar import account_avatar
from documents.models import Document, DocumentLibrary, Folder, WorkspaceDocument
from planner.models import CalendarEvent
from resources.models import Resource
from spaces.avatars import space_avatar
from workplaces.services import scoped_workplace_app_path, workplaces_for_user
from workplaces.templatetags.workplace_avatar import workplace_avatar
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
        'calendar': reverse('planner:index'),
        'documents': reverse('documents:library'),
        'office': reverse('office:index'),
        'resources': reverse('resources:index'),
        'dashboards': reverse('pulpits:index'),
        'spaces': reverse('spaces:index'),
        'space': '/space/',
    }
    base_url = fallback_urls[app_label]
    return f'{base_url}{suffix.lstrip("/")}' if suffix else base_url


def _global_search_result(title, type_label, url, icon, meta='', eyebrow='', *, new_tab=False, avatar=None):
    result = {
        'title': str(title or '').strip(),
        'type': type_label,
        'url': url,
        'icon': icon,
        'meta': str(meta or '').strip(),
        'eyebrow': str(eyebrow or '').strip(),
        'new_tab': new_tab,
    }
    if avatar is not None:
        result['avatar'] = avatar
    return result


def _global_search_group(key, label, icon, queryset, serializer):
    rows = list(queryset[:GLOBAL_SEARCH_GROUP_LIMIT + 1])
    return {
        'key': key,
        'label': label,
        'icon': icon,
        'results': [serializer(row) for row in rows[:GLOBAL_SEARCH_GROUP_LIMIT]],
        'has_more': len(rows) > GLOBAL_SEARCH_GROUP_LIMIT,
    }


def _ranked_search_queryset(queryset, field_name, query, *, key_field=None):
    exact = Q(**{f'{field_name}__iexact': query})
    prefix = Q(**{f'{field_name}__istartswith': query})
    fragment = Q(**{f'{field_name}__icontains': query})
    ranks = []
    if key_field:
        ranks.append(When(**{f'{key_field}__iexact': query}, then=Value(0)))
        prefix |= Q(**{f'{key_field}__istartswith': query})
        fragment |= Q(**{f'{key_field}__icontains': query})
    offset = len(ranks)
    ranks.extend([
        When(exact, then=Value(offset)),
        When(prefix, then=Value(offset + 1)),
        When(fragment, then=Value(offset + 2)),
    ])
    return queryset.annotate(
        _global_search_rank=Case(
            *ranks,
            default=Value(offset + 3),
            output_field=IntegerField(),
        )
    )


def _navigation_search_results(query, workplace):
    tasks_url = _workspace_app_url(workplace, 'filters', 'search/')
    calendar_url = _workspace_app_url(workplace, 'calendar')
    entries = (
        ('Dla ciebie', 'Twoje zadania, ulubione i ostatnia praca', scoped_workplace_app_path(workplace, 'for-you') if workplace else reverse('for_you'), 'user-round-check', 'dla ciebie for you przypisane ostatnie'),
        ('Dashboard', 'Strona główna i podsumowanie', reverse('home'), 'layout-dashboard', 'dashboard start podsumowanie'),
        ('Pulpity', 'Własne pulpity i gadżety zespołu', _workspace_app_url(workplace, 'dashboards'), 'layout-dashboard', 'pulpity dashboard gadzety'),
        ('Moje zadania', 'Zadania przypisane do Ciebie', _search_url(tasks_url, basic='1', sort='created_desc', assignee='me'), 'user-round-check', 'tasks moje zadania'),
        ('Wyszukaj zadania', 'Wyszukiwanie zadań w Filtrach', tasks_url, 'search', 'tasks lista wszystkie zadania'),
        ('Przestrzenie', 'Przestrzenie w bieżącym Workspace', _workspace_app_url(workplace, 'spaces'), 'folders', 'przestrzenie projekty kanban scrum'),
        ('Zespoły', 'Osoby i ich zespoły', _workspace_app_url(workplace, 'teams'), 'users', 'zespoly osoby teams'),
        ('Kalendarz', 'Wydarzenia i terminy', calendar_url, 'calendar-days', 'wydarzenia terminy'),
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
    results = {}
    from spaces.models import Space, SpaceTask
    from spaces.services import visible_spaces, visible_items, task_url, space_url
    ids = [entry['identity'][3] for entry in entries if entry['identity'][2] == Space._meta.label_lower]
    for obj in visible_spaces(request).filter(pk__in=ids):
        results[(Space._meta.label_lower, obj.pk)] = _global_search_result(obj.name, 'Przestrzeń', space_url(request, obj), 'layers', obj.key, avatar=space_avatar(obj))
    ids = [entry['identity'][3] for entry in entries if entry['identity'][2] == SpaceTask._meta.label_lower]
    for item in visible_items(request).filter(task_id__in=ids):
        results[(SpaceTask._meta.label_lower, item.task_id)] = _global_search_result(item.task.title, 'Podzadanie' if item.task.parent_id else 'Zadanie', task_url(request, item.task), item.type_icon, f'{item.key} · {item.space.name}')
    return [results[tuple(entry['identity'][2:])] for entry in entries
            if tuple(entry['identity'][2:]) in results][:GLOBAL_SEARCH_RECENT_LIMIT]


@login_required
@require_GET
def global_search(request):
    query = (request.GET.get('q') or '').strip()[:GLOBAL_SEARCH_QUERY_LIMIT]
    if not query and request.GET.get('recent') == '1':
        recent = _recent_search_results(request)
        from workplaces.policy import module_enabled, module_for_path
        recent = [item for item in recent if module_enabled(request.workplace, module_for_path(item['url']))]
        response = JsonResponse({
            'query': '', 'recent': True, 'total': len(recent), 'truncated': False,
            'groups': [{'key': 'recent', 'label': 'Ostatnio oglądane', 'icon': 'clock',
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
    calendar_url = _workspace_app_url(workplace, 'calendar')
    from tasks.tagging import visible_tags
    tag_queryset = visible_tags(request).select_related('space').filter(
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

    from spaces.services import visible_items, visible_spaces, task_url, space_url
    groups.extend([
        _global_search_group('space_tasks', 'Zadania przestrzeni', 'list-checks',
            _ranked_search_queryset(
                visible_items(request).filter(Q(task__title__icontains=query) | Q(key__icontains=query) | Q(task__description__icontains=query) | Q(task__activities__message__icontains=query)).distinct(),
                'task__title', query, key_field='key',
            ).order_by('_global_search_rank', '-task__created_at', '-pk'),
            lambda item: _global_search_result(item.task.title, 'Podzadanie' if item.task.parent_id else 'Zadanie', task_url(request, item.task), item.type_icon, f'{item.key} · {item.space.name}')),
        _global_search_group('spaces', 'Przestrzenie', 'layers',
            _ranked_search_queryset(
                visible_spaces(request).filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(key__icontains=query)),
                'name', query, key_field='key',
            ).order_by('_global_search_rank', 'name', 'pk'),
            lambda space: _global_search_result(space.name, 'Przestrzeń', space_url(request, space), 'layers', space.key, avatar=space_avatar(space))),
    ])

    groups.extend((
        _global_search_group(
            'tags',
            'Tagi',
            'tag',
            _ranked_search_queryset(tag_queryset.distinct(), 'name', query).order_by('_global_search_rank', 'name', 'id'),
            lambda tag: _global_search_result(
                tag.name,
                'Tag',
                _search_url(_workspace_app_url(workplace, 'space', f'{tag.space.slug}/'), view='tags', q=tag.name),
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
                avatar=workplace_avatar(item),
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
        lambda item: _global_search_result(item.name, 'Zasób', f'{resources_url}{item.pk}/', item.icon,
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
    from workplaces.policy import module_enabled, module_for_path
    for group in groups:
        group['results'] = [item for item in group['results'] if module_enabled(workplace, module_for_path(item['url']))]
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
    from core.list_window import window_page, window_url
    from spaces.frontend import space_payload
    from spaces.services import app_url, decorate_directory_spaces, space_url, visible_spaces
    from workplaces.policy import module_enabled, read_only

    category = 'spaces' if request.GET.get('section') == 'spaces' else 'all'
    spaces_enabled = bool(request.workplace and module_enabled(request.workplace, 'spaces'))
    can_write = spaces_enabled and not read_only(request)
    query = request.GET.get('q', '').strip()[:120] if category == 'spaces' else ''
    spaces_page = None
    if category == 'spaces':
        spaces = visible_spaces(request).order_by('name', 'pk') if spaces_enabled else []
        if query and spaces_enabled:
            spaces = spaces.filter(Q(name__icontains=query) | Q(key__icontains=query) | Q(description__icontains=query))
        spaces_page = window_page(spaces, request)
        spaces_page.object_list = decorate_directory_spaces(request, spaces_page.object_list)
    settings_spaces = []
    for space in spaces_page or []:
        row = space_payload(space)
        can_manage = can_write and row['can_manage']
        settings_spaces.append({
            **{key: row[key] for key in ('id', 'name', 'avatar', 'key', 'description', 'kind_label', 'template_label', 'item_count')},
            'url': row['settings_url'], 'can_manage': can_manage,
            'edit_url': row['settings_url'] if can_manage else '',
            'delete_url': space_url(request, space, 'delete/') if can_manage else '',
        })
    return render(request, 'dashboard/settings.html', {
        'current_account_avatar': account_avatar(request.user),
        'settings_category': category,
        'settings_title': 'Przestrzenie' if category == 'spaces' else 'Ustawienia',
        'settings_query': query,
        'settings_spaces_enabled': spaces_enabled,
        'settings_spaces_url': reverse('settings') + '?section=spaces',
        'settings_create_url': app_url(request, 'create/?return_to=settings') if can_write else '',
        'settings_spaces': settings_spaces,
        'settings_spaces_page': spaces_page,
        'settings_spaces_next': window_url(request, spaces_page) if spaces_page is not None else '',
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
    is_panel_request = getattr(request, '_react_api', False) or (request.headers.get('X-Requested-With') == 'XMLHttpRequest'
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
    if getattr(request, '_react_api', False):
        from .notification_frontend import notification_payload
        response = JsonResponse({**summary, **notification_payload(request.user, context)})
        response['Cache-Control'] = 'no-store'
        return response
    response = JsonResponse({
        **summary,
        'count': len(context['dashboard_notifications']),
        'total': context['dashboard_notification_count'],
        'filtered_unread_count': context['filtered_unread_count'],
        'deletable_count': context['deletable_count'],
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
