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
from django.views.decorators.http import require_GET

from accounts.avatar import account_avatar
from accounts.views import _switch_account_context
from contacts.models import Company, Contact
from documents.models import Document, DocumentLibrary, Folder, WorkspaceDocument
from kanban.models import Kanban, KanbanActivity, KanbanProject, KanbanSection
from planner.models import CalendarEvent
from tasks.models import Task, TaskActivity, TaskProject, TaskSection, TaskTag
from workplaces.services import scoped_workplace_app_path, workplaces_for_user
from .overview import dashboard_overview


DASHBOARD_NOTIFICATION_LIMIT = 12
GLOBAL_SEARCH_QUERY_LIMIT = 120


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
        'kanban': reverse('kanban:tasks'),
        'contacts': reverse('contacts:contacts'),
        'calendar': reverse('planner:index'),
        'documents': reverse('documents:library'),
        'office': reverse('office:index'),
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
    rows = list(queryset)
    return {
        'key': key,
        'label': label,
        'icon': icon,
        'results': [serializer(row) for row in rows],
        'has_more': False,
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
    kanban_url = _workspace_app_url(workplace, 'kanban')
    contacts_url = _workspace_app_url(workplace, 'contacts')
    calendar_url = _workspace_app_url(workplace, 'calendar')
    entries = (
        ('Dashboard', 'Strona główna i podsumowanie', reverse('home'), 'layout-dashboard', 'dashboard start podsumowanie'),
        ('Moje zadania', 'Zadania przypisane do Ciebie', _search_url(tasks_url, view='my-tasks'), 'user-round-check', 'tasks moje zadania'),
        ('Wszystkie zadania', 'Pełna lista zadań', _search_url(tasks_url, view='all-tasks'), 'list-checks', 'tasks lista'),
        ('Projekty', 'Projekty w bieżącym Workspace', tasks_url, 'folders', 'tasks projekty'),
        ('Kanban', 'Przestrzenie i tablice Kanban', kanban_url, 'kanban', 'karty tablice przestrzenie'),
        ('Kontakty', 'Osoby zapisane w aplikacji', contacts_url, 'contact', 'osoby klienci'),
        ('Firmy', 'Baza firm i organizacji', f'{contacts_url}companies/', 'building-2', 'organizacje companies'),
        ('Kalendarz', 'Wydarzenia i terminy', calendar_url, 'calendar-days', 'wydarzenia terminy'),
        ('Tagi', 'Wspólne oznaczenia', _search_url(tasks_url, view='tags'), 'tag', 'etykiety labels'),
        ('Dysk', 'Dyski, foldery i pliki', _workspace_app_url(workplace, 'documents'), 'hard-drive', 'dysk dyski pliki foldery dokumenty biblioteka'),
        ('Dokumenty', 'Tworzenie, edycja i przechowywanie dokumentów', _workspace_app_url(workplace, 'office'), 'file-text', 'dokumenty edytor tekst pisanie'),
        ('Workspace', 'Miejsca pracy i ich ustawienia', reverse('workplaces:workplaces'), 'briefcase', 'miejsca pracy'),
        ('Powiadomienia', 'Ostatnia aktywność', reverse('notifications'), 'bell', 'aktywność historia'),
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


@login_required
@require_GET
def global_search(request):
    query = (request.GET.get('q') or '').strip()[:GLOBAL_SEARCH_QUERY_LIMIT]
    if len(query) < 2:
        return JsonResponse({
            'query': query,
            'groups': [],
            'total': 0,
            'minimum_query_length': 2,
        })

    user = request.user
    workplace = getattr(request, 'workplace', None)
    tasks_url = _workspace_app_url(workplace, 'tasks')
    kanban_url = _workspace_app_url(workplace, 'kanban')
    contacts_url = _workspace_app_url(workplace, 'contacts')
    calendar_url = _workspace_app_url(workplace, 'calendar')
    numeric_query = int(query) if query.isdigit() else None

    task_filter = (
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(blocked_reason__icontains=query)
        | Q(section__title__icontains=query)
        | Q(section__project__name__icontains=query)
        | Q(tags__name__icontains=query)
        | Q(activities__message__icontains=query)
    )
    kanban_card_filter = (
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(section__title__icontains=query)
        | Q(section__project__name__icontains=query)
        | Q(tags__name__icontains=query)
        | Q(activities__message__icontains=query)
    )
    if numeric_query is not None:
        task_filter |= Q(task_id=numeric_query)
        kanban_card_filter |= Q(task_id=numeric_query)

    task_queryset = Task.objects.filter(user=user).filter(task_filter)
    project_queryset = TaskProject.objects.filter(user=user).filter(
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
    section_queryset = TaskSection.objects.filter(project__user=user).filter(
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
    kanban_project_queryset = KanbanProject.objects.filter(user=user).filter(
        Q(name__icontains=query)
        | Q(description__icontains=query)
        | Q(code__icontains=query)
        | Q(source__icontains=query)
        | Q(company__name__icontains=query)
        | Q(project_notes__message__icontains=query)
    )
    kanban_section_queryset = KanbanSection.objects.filter(project__user=user).filter(
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(project__name__icontains=query)
    )
    kanban_card_queryset = Kanban.objects.filter(user=user).filter(kanban_card_filter)
    contact_queryset = Contact.objects.filter(user=user).filter(
        Q(first_name__icontains=query)
        | Q(middle_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(company__icontains=query)
        | Q(company_record__name__icontains=query)
        | Q(role__icontains=query)
        | Q(email__icontains=query)
        | Q(phone__icontains=query)
        | Q(source__icontains=query)
        | Q(notes__icontains=query)
        | Q(activities__message__icontains=query)
    )
    company_queryset = Company.objects.filter(owner=user).filter(
        Q(name__icontains=query)
        | Q(website__icontains=query)
        | Q(email__icontains=query)
        | Q(phone__icontains=query)
        | Q(address__icontains=query)
        | Q(notes__icontains=query)
    )
    event_queryset = CalendarEvent.objects.filter(user=user).filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    )

    if workplace is not None:
        task_queryset = task_queryset.filter(workplace=workplace)
        project_queryset = project_queryset.filter(workplace=workplace)
        section_queryset = section_queryset.filter(project__workplace=workplace)
        tag_queryset = tag_queryset.filter(workplace=workplace)
        kanban_project_queryset = kanban_project_queryset.filter(workplace=workplace)
        kanban_section_queryset = kanban_section_queryset.filter(project__workplace=workplace)
        kanban_card_queryset = kanban_card_queryset.filter(workplace=workplace)
        contact_queryset = contact_queryset.filter(workplace=workplace)
        company_queryset = company_queryset.filter(workplace=workplace)
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
                f'{tasks_url}{"view-subtask" if task.parent_id else "view-task"}/{task.task_id}/',
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
            'Projekty',
            'folders',
            _ranked_search_queryset(
                project_queryset.select_related('company', 'responsible_user').distinct(),
                'name',
                query,
            ).order_by('_global_search_rank', 'name', 'id'),
            lambda project: _global_search_result(
                project.name,
                'Projekt',
                _search_url(tasks_url, project=project.id),
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
            'kanban-projects',
            'Przestrzenie Kanban',
            'kanban',
            _ranked_search_queryset(
                kanban_project_queryset.select_related('company').distinct(),
                'name',
                query,
            ).order_by('_global_search_rank', 'name', 'id'),
            lambda project: _global_search_result(
                project.name,
                'Przestrzeń Kanban',
                _search_url(kanban_url, project=project.id),
                '',
                ' · '.join(part for part in (project.code, project.company.name if project.company_id else '') if part),
            ),
        ),
        _global_search_group(
            'kanban-boards',
            'Tablice Kanban',
            'columns-3',
            _ranked_search_queryset(
                kanban_section_queryset.select_related('project').distinct(),
                'title',
                query,
            ).order_by('_global_search_rank', 'project__name', 'order', 'id'),
            lambda section: _global_search_result(
                section.title,
                'Tablica Kanban',
                f'{kanban_url}groups/{section.id}/',
                '',
                section.project.name,
            ),
        ),
        _global_search_group(
            'kanban-cards',
            'Karty Kanban',
            'square-kanban',
            _ranked_search_queryset(
                kanban_card_queryset.select_related('section', 'section__project', 'parent').distinct(),
                'title',
                query,
            ).order_by('_global_search_rank', '-created_at', '-id'),
            lambda card: _global_search_result(
                card.title,
                'Podkarta' if card.parent_id else 'Karta Kanban',
                f'{kanban_url}{"view-subtask" if card.parent_id else "view-task"}/{card.task_id}/',
                '',
                ' · '.join(part for part in (
                    f'#{card.task_id}',
                    card.section.project.name if card.section_id else '',
                    card.section.title if card.section_id else '',
                ) if part),
            ),
        ),
        _global_search_group(
            'contacts',
            'Kontakty',
            'contact',
            _ranked_search_queryset(
                contact_queryset.select_related('company_record').distinct(),
                'first_name',
                query,
            ).order_by('_global_search_rank', 'first_name', 'middle_name', 'last_name', 'id'),
            lambda contact: _global_search_result(
                contact.display_name,
                'Kontakt',
                f'{contacts_url}view-contact/{contact.id}/',
                'contact-round',
                ' · '.join(part for part in (
                    contact.role,
                    contact.company_record.name if contact.company_record_id else contact.company,
                    contact.email,
                ) if part),
            ),
        ),
        _global_search_group(
            'companies',
            'Firmy',
            'building-2',
            _ranked_search_queryset(company_queryset.distinct(), 'name', query).order_by('_global_search_rank', 'name', 'id'),
            lambda company: _global_search_result(
                company.name,
                'Firma',
                f'{contacts_url}companies/{company.id}/',
                'building-2',
                ' · '.join(part for part in (company.email, company.phone, company.website) if part),
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
            workplaces_for_user(user).filter(
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
    office_url = _workspace_app_url(workplace, 'office')
    groups.extend((
        _global_search_group(
            'office-documents', 'Dokumenty', 'file-text',
            WorkspaceDocument.objects.filter(owner=user, workplace=workplace, deleted_at__isnull=True).filter(
                Q(title__icontains=query) | Q(filename__icontains=query)
            ).select_related('folder'),
            lambda item: _global_search_result(item.title, 'Dokument',
                f'{office_url}{item.pk}/' + ('editor/' if item.has_full_editor else ('preview/' if item.kind == WorkspaceDocument.Kind.FILE else '')),
                'file-text', item.folder.name if item.folder else 'Dokumenty', new_tab=bool(item.office_type)),
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
                | Q(description__icontains=query) | Q(tags__name__icontains=query)
            ).select_related('folder', 'library').distinct(),
            lambda item: _global_search_result(item.title, 'Plik', f'{documents_url}{item.pk}/preview/', item.icon,
                                                ' / '.join(part for part in (item.library.name, item.folder.name if item.folder else '') if part)),
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


def _actor_label(actor):
    if not actor:
        return 'System'
    return actor.get_full_name() or actor.get_username()


def _display_label(value, fallback='Zmiana'):
    if not value:
        return fallback
    value = str(value)
    return f'{value[:1].upper()}{value[1:]}'


def _activity_action_message(activity):
    if activity.kind == 'comment':
        return 'dodał komentarz'
    return activity.message or activity.get_action_display().lower()


def _detail_line(label, value='', from_label='', to_label=''):
    return {
        'label': label,
        'value': value,
        'from_label': from_label,
        'to_label': to_label,
    }


def _activity_detail_lines(activity, subitem_label):
    metadata = activity.metadata or {}
    detail_lines = []

    for change in metadata.get('changes') or []:
        detail_lines.append(_detail_line(
            _display_label(change.get('field')),
            from_label=change.get('from_label') or '',
            to_label=change.get('to_label') or '',
        ))

    if detail_lines:
        return detail_lines

    if metadata.get('from_label') or metadata.get('to_label'):
        return [_detail_line(
            'Zmiana',
            from_label=metadata.get('from_label') or '',
            to_label=metadata.get('to_label') or '',
        )]

    if metadata.get('fields'):
        return [_detail_line('Zmienione pola', value=', '.join(metadata.get('fields') or []))]

    if activity.kind == 'comment' and activity.message:
        return [_detail_line('Komentarz', value=activity.message)]

    if activity.action == 'created' and metadata.get('title'):
        return [_detail_line('Tytuł', value=metadata.get('title'))]

    if 'count' in metadata:
        return [_detail_line('Liczba', value=metadata.get('count'))]

    if metadata.get('subtask_title'):
        return [_detail_line(subitem_label, value=metadata.get('subtask_title'))]

    return []


def _activity_location(task, source_label, object_label):
    location_parts = [source_label, f'{object_label} #{task.task_id}', task.title]
    section = task.section
    if section:
        project = section.project
        if project:
            location_parts.append(project.name)
        location_parts.append(section.title)

    column = getattr(task, 'column', None)
    if column:
        location_parts.append(column.title)

    return ' · '.join(part for part in location_parts if part)


def _activity_notification(activity, app_name, source_label, object_label, subitem_label):
    task = activity.task
    route_name = 'view-subtask' if task.parent_id else 'view-task'

    return {
        'source': app_name,
        'source_label': source_label,
        'object_label': object_label,
        'object_id': task.task_id,
        'title': task.title,
        'actor_label': _actor_label(activity.actor),
        'actor_avatar': account_avatar(activity.actor),
        'action_message': _activity_action_message(activity),
        'detail_lines': _activity_detail_lines(activity, subitem_label),
        'location_label': _activity_location(task, source_label, object_label),
        'created_at': activity.created_at,
        'sort_key': (activity.created_at, activity.id),
        'url': _workspace_app_url(task.workplace, app_name, f'{route_name}/{task.task_id}/?task_pk={task.pk}'),
    }


def _dashboard_notifications(user):
    task_activities = TaskActivity.objects.filter(
        task__user=user,
    ).select_related(
        'task',
        'task__section',
        'task__section__project',
        'actor',
    ).order_by('-created_at', '-id')[:DASHBOARD_NOTIFICATION_LIMIT]
    kanban_activities = KanbanActivity.objects.filter(
        task__user=user,
    ).select_related(
        'task',
        'task__section',
        'task__section__project',
        'task__column',
        'actor',
    ).order_by('-created_at', '-id')[:DASHBOARD_NOTIFICATION_LIMIT]

    notifications = [
        _activity_notification(activity, 'tasks', 'Tasks', 'Zadanie', 'Podzadanie')
        for activity in task_activities
    ] + [
        _activity_notification(activity, 'kanban', 'Kanban', 'Karta', 'Podkarta')
        for activity in kanban_activities
    ]

    return sorted(
        notifications,
        key=lambda notification: notification['sort_key'],
        reverse=True,
    )[:DASHBOARD_NOTIFICATION_LIMIT]


@login_required
def settings(request):
    return render(request, 'dashboard/settings.html', {
        'current_account_avatar': account_avatar(request.user),
        'switch_accounts': _switch_account_context(request),
        'settings_timezone': timezone.get_current_timezone_name(),
    })


@login_required
@require_GET
def home(request):
    workplace = getattr(request, 'workplace', None)
    if workplace is None:
        return redirect('workplaces:workplaces')
    response = render(request, 'dashboard/home.html', dashboard_overview(
        request.user, workplace, request.GET.get('focus'),
    ))
    response['Cache-Control'] = 'no-store'
    return response


@login_required
@require_GET
def notifications(request):
    dashboard_notifications = _dashboard_notifications(request.user)
    context = {
        'dashboard_notifications': dashboard_notifications,
        'dashboard_notification_count': len(dashboard_notifications),
    }
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = JsonResponse({
            'count': context['dashboard_notification_count'],
            'html': render_to_string(
                'dashboard/includes/notification_list.html',
                context,
                request=request,
            ),
        })
        response['Cache-Control'] = 'no-store'
        return response

    return render(request, 'dashboard/notifications.html', context)
