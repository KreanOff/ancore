import json
import logging
import unicodedata
from collections import defaultdict
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Max, Prefetch, Q, Value, When
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
from accounts.avatar import account_avatar
from accounts.models import normalize_public_username
from contacts.models import SharedItem, SharedItemLink, UserContact
from core.upload_validation import attachment_download_response, validate_attachment_upload
from ..models import Task, TaskActivity, TaskAttachment, TaskProject, TaskProjectNote, TaskSection, TaskSectionNote, TaskTag, TaskTagNote, parse_hierarchy_code_number
from ..forms import QuickTaskForm, SubTaskModalForm, TaskForm, TaskModalForm, TaskProjectForm, TaskProjectRenameForm, TaskSectionForm, TaskSectionRenameForm, TaskTagForm


logger = logging.getLogger(__name__)

PROJECT_PAGE_SIZE_OPTIONS = (10, 25, 50, 100, 150, 200)
PROJECT_DEFAULT_PAGE_SIZE = 50
PROJECT_NAVIGATION_LIMIT = 50
TASK_PAGE_SIZE_OPTIONS = PROJECT_PAGE_SIZE_OPTIONS
TASK_DEFAULT_PAGE_SIZE = 25
PROJECT_DEFAULT_SORT = 'name_asc'
PROJECT_SORT_OPTIONS = (
    {'value': 'name_asc', 'label': 'Projekt A-Z', 'icon': 'arrow-up-a-z', 'direction': 'asc'},
    {'value': 'name_desc', 'label': 'Projekt Z-A', 'icon': 'arrow-down-z-a', 'direction': 'desc'},
    {'value': 'code_asc', 'label': 'Kod A-Z', 'icon': 'arrow-up-a-z', 'direction': 'asc'},
    {'value': 'company_asc', 'label': 'Firma A-Z', 'icon': 'building-2', 'direction': 'asc'},
    {'value': 'responsible_asc', 'label': 'Odpowiedzialny', 'icon': 'circle-user-round', 'direction': 'asc'},
    {'value': 'status_asc', 'label': 'Status', 'icon': 'circle-dot', 'direction': 'asc'},
    {'value': 'priority_desc', 'label': 'Priorytet', 'icon': 'chart-no-axes-column-increasing', 'direction': 'desc'},
    {'value': 'due_at_asc', 'label': 'Najbliższy termin', 'icon': 'calendar-clock', 'direction': 'asc'},
    {'value': 'created_desc', 'label': 'Najnowsze', 'icon': 'clock-3', 'direction': 'desc'},
    {'value': 'activity_desc', 'label': 'Ostatnia aktywność', 'icon': 'activity', 'direction': 'desc'},
)
PROJECT_SORT_OPTION_MAP = {option['value']: option for option in PROJECT_SORT_OPTIONS}
GROUP_DEFAULT_SORT = 'project_asc'
GROUP_SORT_OPTIONS = (
    {'value': 'project_asc', 'label': 'Projekt A-Z', 'icon': 'folder-kanban', 'direction': 'asc'},
    {'value': 'title_asc', 'label': 'Grupa A-Z', 'icon': 'arrow-up-a-z', 'direction': 'asc'},
    {'value': 'title_desc', 'label': 'Grupa Z-A', 'icon': 'arrow-down-z-a', 'direction': 'desc'},
    {'value': 'code_asc', 'label': 'Kod grupy', 'icon': 'hash', 'direction': 'asc'},
    {'value': 'status_asc', 'label': 'Status', 'icon': 'circle-dot', 'direction': 'asc'},
    {'value': 'kind_asc', 'label': 'Typ', 'icon': 'layers-3', 'direction': 'asc'},
    {'value': 'priority_desc', 'label': 'Priorytet', 'icon': 'chart-no-axes-column-increasing', 'direction': 'desc'},
    {'value': 'owner_asc', 'label': 'Odpowiedzialny', 'icon': 'circle-user-round', 'direction': 'asc'},
    {'value': 'due_at_asc', 'label': 'Najbliższy termin', 'icon': 'calendar-clock', 'direction': 'asc'},
    {'value': 'created_desc', 'label': 'Najnowsze', 'icon': 'clock-3', 'direction': 'desc'},
    {'value': 'activity_desc', 'label': 'Ostatnia aktywność', 'icon': 'activity', 'direction': 'desc'},
)
GROUP_SORT_OPTION_MAP = {option['value']: option for option in GROUP_SORT_OPTIONS}
TASK_DEFAULT_SORT = 'task_id_asc'
TASK_SORT_OPTIONS = (
    {'value': 'task_id_asc', 'label': 'Kolejność', 'icon': 'list-ordered', 'direction': 'asc'},
    {'value': 'task_id_desc', 'label': 'Najnowsze ID', 'icon': 'arrow-down-wide-narrow', 'direction': 'desc'},
    {'value': 'title_asc', 'label': 'Zadanie A-Z', 'icon': 'arrow-up-a-z', 'direction': 'asc'},
    {'value': 'title_desc', 'label': 'Zadanie Z-A', 'icon': 'arrow-down-z-a', 'direction': 'desc'},
    {'value': 'priority_desc', 'label': 'Priorytet', 'icon': 'chart-no-axes-column-increasing', 'direction': 'desc'},
    {'value': 'project_asc', 'label': 'Projekt A-Z', 'icon': 'folder-kanban', 'direction': 'asc'},
    {'value': 'section_asc', 'label': 'Grupa A-Z', 'icon': 'layers-3', 'direction': 'asc'},
    {'value': 'assignee_asc', 'label': 'Odpowiedzialny', 'icon': 'circle-user-round', 'direction': 'asc'},
    {'value': 'company_asc', 'label': 'Firma A-Z', 'icon': 'building-2', 'direction': 'asc'},
    {'value': 'type_asc', 'label': 'Typ', 'icon': 'list-filter', 'direction': 'asc'},
    {'value': 'due_at_asc', 'label': 'Najbliższy termin', 'icon': 'calendar-clock', 'direction': 'asc'},
    {'value': 'created_desc', 'label': 'Najnowsze', 'icon': 'clock-3', 'direction': 'desc'},
    {'value': 'activity_desc', 'label': 'Ostatnia aktywność', 'icon': 'activity', 'direction': 'desc'},
)
TASK_SORT_OPTION_MAP = {option['value']: option for option in TASK_SORT_OPTIONS}
TASK_DUE_FILTER_OPTIONS = (
    {'value': 'overdue', 'label': 'Po terminie'},
    {'value': 'today', 'label': 'Dzisiaj'},
    {'value': 'week', 'label': 'Ten tydzień'},
    {'value': 'none', 'label': 'Brak terminu'},
)


def _active_workplace(request):
    return getattr(request, 'workplace', None)


def _filter_workplace(queryset, workplace, field_name='workplace'):
    if workplace is None:
        return queryset
    return queryset.filter(**{field_name: workplace})


def _attachment_validation_errors(files):
    errors = []
    for uploaded_file in files:
        try:
            validate_attachment_upload(uploaded_file)
        except ValidationError as error:
            errors.extend(error.messages)
    return errors


def _mark_task_row_access(tasks, user):
    if not user or not getattr(user, 'is_authenticated', False):
        return tasks

    for task in tasks:
        if not task:
            continue
        task.can_manage = task.user_id == user.id
        task.can_edit = task.can_manage
        task.shared_view_url = ''
        task.tags_render_count = getattr(task, 'tags_total', None)
        if task.tags_render_count is None:
            task.tags_render_count = task.tags.count()
        task.attachments_render_count = getattr(task, 'attachments_total', None)
        if task.attachments_render_count is None:
            task.attachments_render_count = task.attachments.count()
    return tasks


def _task_status_page_param(status):
    return f'task_{status}_page'


def _task_status_page_size_param(status):
    return f'task_{status}_page_size'


def _task_status_page_size(request, status):
    if request is None:
        return TASK_DEFAULT_PAGE_SIZE

    try:
        page_size = int(request.GET.get(_task_status_page_size_param(status)) or TASK_DEFAULT_PAGE_SIZE)
    except (TypeError, ValueError):
        return TASK_DEFAULT_PAGE_SIZE
    return page_size if page_size in TASK_PAGE_SIZE_OPTIONS else TASK_DEFAULT_PAGE_SIZE


def _task_status_page_number(request, status):
    if request is None:
        return 1

    try:
        page_number = int(request.GET.get(_task_status_page_param(status)) or 1)
    except (TypeError, ValueError):
        return 1
    return max(page_number, 1)


def _request_query_params(request):
    if request is None:
        return {}
    return {key: value for key, value in request.GET.items()}


def _paginated_status_group_for_tasks(tasks, status, label, user=None, request=None, base_url=None, total_tasks=None):
    page_param = _task_status_page_param(status)
    page_size_param = _task_status_page_size_param(status)
    page_size = _task_status_page_size(request, status)
    requested_page = _task_status_page_number(request, status)
    status_queryset = tasks.filter(status=status)
    if total_tasks is None:
        total_tasks = status_queryset.count()
    total_pages = max(1, (total_tasks + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size
    status_tasks = list(status_queryset[offset:offset + page_size]) if total_tasks else []
    _mark_task_row_access(status_tasks, user)

    base_params = _request_query_params(request)
    base_params[page_size_param] = page_size
    has_previous = current_page > 1 and total_tasks > 0
    has_next = current_page < total_pages and total_tasks > 0
    previous_url = ''
    next_url = ''
    if has_previous:
        previous_page_params = {**base_params, page_param: current_page - 1}
        if current_page - 1 == 1:
            previous_page_params.pop(page_param, None)
        previous_url = _projects_url(previous_page_params, base_url=base_url)
    if has_next:
        next_url = _projects_url({**base_params, page_param: current_page + 1}, base_url=base_url)

    if not status_tasks:
        summary = 'Brak zadań'
    else:
        first_visible = offset + 1
        last_visible = offset + len(status_tasks)
        summary = f'Pokazano {first_visible}-{last_visible} z {total_tasks} zadań'

    page_size_items = []
    for option in TASK_PAGE_SIZE_OPTIONS:
        page_size_params = {**base_params, page_size_param: option}
        page_size_params.pop(page_param, None)
        page_size_items.append({
            'size': option,
            'url': _projects_url(page_size_params, base_url=base_url),
            'is_current': page_size == option,
        })

    return {
        'status': status,
        'label': label,
        'tasks': status_tasks,
        'count': total_tasks,
        'page': current_page,
        'total_pages': total_pages,
        'page_size': page_size,
        'page_size_options': TASK_PAGE_SIZE_OPTIONS,
        'page_size_items': page_size_items,
        'page_items': _project_page_items(
            current_page,
            total_pages,
            base_params,
            page_param=page_param,
            base_url=base_url,
        ) if total_tasks else [],
        'has_previous': has_previous,
        'has_next': has_next,
        'previous_url': previous_url,
        'next_url': next_url,
        'summary': summary,
    }


def _status_groups_for_tasks(tasks, user=None, request=None, base_url=None, paginate=False):
    if paginate and request is not None and hasattr(tasks, 'filter'):
        task_ids = tasks.order_by().values('pk')
        status_counts = {
            row['status']: row['total']
            for row in (
                tasks.model.objects
                .filter(pk__in=task_ids)
                .values('status')
                .annotate(total=Count('pk'))
            )
        }
        return [
            _paginated_status_group_for_tasks(
                tasks,
                status,
                label,
                user=user,
                request=request,
                base_url=base_url,
                total_tasks=status_counts.get(status, 0),
            )
            for status, label in Task.STATUS_CHOICES
        ]

    task_list = list(tasks)
    _mark_task_row_access(task_list, user)
    tasks_by_status = {status: [] for status, _label in Task.STATUS_CHOICES}
    for task in task_list:
        tasks_by_status.setdefault(task.status, []).append(task)
    return [
        {
            'status': status,
            'label': label,
            'tasks': tasks_by_status.get(status, []),
            'count': len(tasks_by_status.get(status, [])),
        }
        for status, label in Task.STATUS_CHOICES
    ]


def _decorate_status_groups(projects, orphan_tasks, user=None):
    for project in projects:
        project_tasks = []
        for section in project.sections.all():
            section_tasks = list(section.tasks.all())
            section.status_groups = _status_groups_for_tasks(section_tasks, user)
            project_tasks.extend(section_tasks)
        project.status_groups = _status_groups_for_tasks(project_tasks, user)
    return _status_groups_for_tasks(orphan_tasks, user)


def _sections_for_projects(projects):
    return [section for project in projects for section in project.sections.all()]


def _user_display_name(user):
    return user.get_full_name() or user.email or user.username


SHARE_PERMISSION_LABELS = {
    'owner': 'Właściciel',
    'view': 'Może przeglądać',
    'edit': 'Może przeglądać i edytować',
}
SHARE_PERMISSION_RANK = {
    'view': 1,
    'edit': 2,
}


def _normalize_share_permission(permission):
    return 'edit' if permission == 'edit' else 'view'


def _share_permission_label(permission):
    return SHARE_PERMISSION_LABELS.get(permission, SHARE_PERMISSION_LABELS['view'])


def _best_share_permission(permissions):
    best_permission = ''
    best_rank = 0
    for permission in permissions:
        normalized = _normalize_share_permission(permission)
        rank = SHARE_PERMISSION_RANK.get(normalized, 0)
        if rank > best_rank:
            best_permission = normalized
            best_rank = rank
    return best_permission


def _share_permission_from_request(request):
    return _normalize_share_permission((request.POST.get('permission') or '').strip())


def _received_share_permission(user, obj):
    return ''


def _direct_outgoing_share_exists(user, model, object_id):
    return False


def _outgoing_share_exists(user, obj):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if isinstance(obj, TaskProject):
        if obj.user_id != user.id:
            return False
        return _direct_outgoing_share_exists(user, TaskProject, obj.id)
    if isinstance(obj, TaskSection):
        if obj.project.user_id != user.id:
            return False
        return (
            _direct_outgoing_share_exists(user, TaskSection, obj.id)
            or _direct_outgoing_share_exists(user, TaskProject, obj.project_id)
        )
    if isinstance(obj, Task):
        if obj.user_id != user.id:
            return False
        return (
            _direct_outgoing_share_exists(user, Task, obj.id)
            or (obj.parent_id and _direct_outgoing_share_exists(user, Task, obj.parent_id))
            or (
                obj.section_id
                and (
                    _direct_outgoing_share_exists(user, TaskSection, obj.section_id)
                    or _direct_outgoing_share_exists(user, TaskProject, obj.section.project_id)
                )
            )
        )
    return False


def _clear_share_access_badge(item):
    item.has_shared_access_badge = False
    item.is_shared_with_current_user = False
    item.shared_access_kind = ''
    item.shared_access_permission = ''
    item.shared_access_icon = ''
    item.shared_access_title = ''


def _mark_share_access_badge(item, user):
    permission = _received_share_permission(user, item)
    if permission in SHARE_PERMISSION_RANK:
        item.has_shared_access_badge = True
        item.is_shared_with_current_user = True
        item.shared_access_kind = 'incoming'
        item.shared_access_permission = permission
        item.shared_access_icon = 'share-2'
        item.shared_access_title = f'Udostępnione dla Ciebie: {_share_permission_label(permission)}'
        return item
    if _outgoing_share_exists(user, item):
        item.has_shared_access_badge = True
        item.is_shared_with_current_user = False
        item.shared_access_kind = 'outgoing'
        item.shared_access_permission = 'outgoing'
        item.shared_access_icon = 'send'
        item.shared_access_title = 'Udostępnione przez Ciebie'
        return item
    _clear_share_access_badge(item)
    return item


def _mark_share_access_badges(items, user):
    for item in items:
        if item:
            _mark_share_access_badge(item, user)
    return items


def _task_shared_ids(user, model, permission=None):
    return []


def _direct_share_permission(user, model, object_id):
    return ''


def _user_project_permission(user, project):
    if project.user_id == user.id:
        return 'owner'
    return ''


def _user_section_permission(user, section):
    if section.project.user_id == user.id:
        return 'owner'
    return ''


def _user_task_permission(user, task):
    if task.user_id == user.id:
        return 'owner'
    return ''


def _user_can_edit_task(user, task):
    return _user_task_permission(user, task) in ('owner', 'edit')


def _user_can_create_task_in_section(user, section):
    if not user or not getattr(user, 'is_authenticated', False) or not section:
        return False
    return _user_section_permission(user, section) in ('owner', 'edit')


def _editable_sections_queryset(user, workplace=None):
    if not user or not getattr(user, 'is_authenticated', False):
        return TaskSection.objects.none()
    queryset = TaskSection.objects.filter(project__user=user).select_related('project', 'project__user').distinct()
    return _filter_workplace(queryset, workplace, field_name='project__workplace')


def _task_creation_project_for_user(user, project_id, workplace=None):
    if not project_id:
        return None
    return (
        TaskProject.objects.filter(id=project_id, sections__in=_editable_sections_queryset(user, workplace))
        .distinct()
        .first()
    )


def _user_can_create_issue(user, active_project=None, active_section=None, workplace=None):
    editable_sections = _editable_sections_queryset(user, workplace)
    if active_section:
        return editable_sections.filter(pk=active_section.pk).exists()
    if active_project:
        return editable_sections.filter(project=active_project).exists()
    return editable_sections.exists()


def _task_share_owner(obj):
    if isinstance(obj, TaskProject):
        return obj.user
    if isinstance(obj, TaskSection):
        return obj.project.user
    if isinstance(obj, Task):
        return obj.user
    return None


def _task_share_label(obj):
    if isinstance(obj, TaskProject):
        return obj.name
    if isinstance(obj, TaskSection):
        return obj.title
    if isinstance(obj, Task):
        return obj.title
    return str(obj)


def _task_share_type_label(obj):
    if isinstance(obj, TaskProject):
        return 'Projekt'
    if isinstance(obj, TaskSection):
        return 'Grupa'
    if isinstance(obj, Task):
        return 'Zadanie'
    return 'Element'


def _task_share_object_url(obj):
    if isinstance(obj, TaskProject):
        return f"{reverse('tasks:tasks')}?view=shared-projects"
    if isinstance(obj, TaskSection):
        return reverse('tasks:task_group', args=[obj.id])
    if isinstance(obj, Task):
        return reverse('tasks:view-task', args=[obj.task_id])
    return reverse('tasks:tasks')


def _user_can_access_project(user, project):
    return project.user_id == user.id


def _user_can_access_section(user, section):
    return section.project.user_id == user.id


def _user_can_access_task(user, task):
    return task.user_id == user.id


def _task_access_filter(user, workplace=None):
    task_filter = Q(user=user)
    if workplace is not None:
        task_filter &= Q(workplace=workplace)
    return task_filter


def _owned_share_object(user, object_type, object_id, workplace=None):
    if object_type == 'project':
        return get_object_or_404(_filter_workplace(TaskProject.objects.filter(user=user), workplace), id=object_id)
    if object_type == 'section':
        return get_object_or_404(_filter_workplace(TaskSection.objects.filter(project__user=user), workplace, field_name='project__workplace'), id=object_id)
    if object_type == 'task':
        return get_object_or_404(_filter_workplace(Task.objects.select_related('section', 'section__project').filter(user=user), workplace), id=object_id)
    raise PermissionDenied


def _share_link_url(request, link):
    return request.build_absolute_uri(reverse('tasks:accept-share-link', args=[link.token]))


def _decorate_share_links(request, items):
    for item in [item for item in items if item]:
        item.share_link_url = ''
        item.share_link_permission = ''


def _shared_tasks_queryset(user):
    return Task.objects.none()


def _shared_sections_queryset(user):
    return TaskSection.objects.none()


def _mark_project_permissions(projects, user):
    for project in projects:
        _clear_share_access_badge(project)
        project.can_manage = project.user_id == user.id
        project.can_share = False
        project.can_edit = project.can_manage
        project.has_editable_sections = False
        for section in project.sections.all():
            _clear_share_access_badge(section)
            section.can_manage = project.can_manage
            section.can_share = False
            section.can_edit = section.can_manage
            if section.can_edit:
                project.has_editable_sections = True
    return projects


def _project_page_size(request):
    try:
        page_size = int(request.GET.get('page_size') or PROJECT_DEFAULT_PAGE_SIZE)
    except (TypeError, ValueError):
        return PROJECT_DEFAULT_PAGE_SIZE
    return page_size if page_size in PROJECT_PAGE_SIZE_OPTIONS else PROJECT_DEFAULT_PAGE_SIZE


def _project_page_number(request):
    try:
        page_number = int(request.GET.get('page') or 1)
    except (TypeError, ValueError):
        return 1
    return max(page_number, 1)


def _project_page_items(current_page, total_pages, base_params, page_param='page', base_url=None):
    if total_pages < 1:
        return []

    if total_pages <= 7:
        page_numbers = list(range(1, total_pages + 1))
    elif current_page <= 4:
        page_numbers = [1, 2, 3, 4, 5, total_pages]
    elif current_page >= total_pages - 3:
        page_numbers = [1, *range(total_pages - 4, total_pages + 1)]
    else:
        page_numbers = [1, current_page - 1, current_page, current_page + 1, total_pages]

    items = []
    previous_page = None
    for page_number in page_numbers:
        if previous_page and page_number - previous_page > 1:
            items.append({'is_ellipsis': True})
        page_params = {**base_params, page_param: page_number}
        if page_number == 1:
            page_params.pop(page_param, None)
        items.append({
            'page': page_number,
            'url': _projects_url(page_params, base_url=base_url),
            'is_current': page_number == current_page,
        })
        previous_page = page_number
    return items


def _projects_url(params, base_url=None):
    cleaned_params = {
        key: value
        for key, value in params.items()
        if value not in (None, '')
    }
    query_string = urlencode(cleaned_params)
    base_url = base_url or reverse('tasks:tasks')
    return f'{base_url}?{query_string}' if query_string else base_url


def _normalize_query_label(value):
    return ''.join(
        char for char in unicodedata.normalize('NFD', str(value or '').lower())
        if unicodedata.category(char) != 'Mn'
    ).strip()


def _choice_options(choices):
    return [{'value': value, 'label': label} for value, label in choices]


def _choice_values_matching_query(choices, query):
    normalized_query = _normalize_query_label(query)
    if not normalized_query:
        return []
    return [
        value
        for value, label in choices
        if normalized_query in _normalize_query_label(value)
        or normalized_query in _normalize_query_label(label)
    ]


def _integer_filter_value(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _project_sort_value(value):
    return value if value in PROJECT_SORT_OPTION_MAP else PROJECT_DEFAULT_SORT


def _group_sort_value(value):
    return value if value in GROUP_SORT_OPTION_MAP else GROUP_DEFAULT_SORT


def _task_sort_value(value):
    return value if value in TASK_SORT_OPTION_MAP else TASK_DEFAULT_SORT


def _choice_rank_case(field_name, choices):
    return Case(
        *[When(**{field_name: value}, then=Value(index)) for index, (value, _label) in enumerate(choices)],
        default=Value(len(choices)),
        output_field=IntegerField(),
    )


def _project_filter_queryset(
    user,
    query='',
    priority='',
    status='',
    stage='',
    health='',
    company='',
    responsible='',
    workplace=None,
):
    queryset = _filter_workplace(TaskProject.objects.filter(user=user), workplace)
    query = (query or '').strip()
    if query:
        priority_matches = _choice_values_matching_query(TaskProject.PRIORITY_CHOICES, query)
        status_matches = _choice_values_matching_query(TaskProject.STATUS_CHOICES, query)
        stage_matches = _choice_values_matching_query(TaskProject.STAGE_CHOICES, query)
        health_matches = _choice_values_matching_query(TaskProject.HEALTH_CHOICES, query)
        query_filter = (
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(code__icontains=query)
            | Q(status__icontains=query)
            | Q(stage__icontains=query)
            | Q(health__icontains=query)
            | Q(source__icontains=query)
            | Q(company__name__icontains=query)
            | Q(responsible_user__first_name__icontains=query)
            | Q(responsible_user__middle_name__icontains=query)
            | Q(responsible_user__last_name__icontains=query)
            | Q(responsible_user__email__icontains=query)
            | Q(responsible_user__username__icontains=query)
        )
        if priority_matches:
            query_filter |= Q(priority__in=priority_matches)
        if status_matches:
            query_filter |= Q(status__in=status_matches)
        if stage_matches:
            query_filter |= Q(stage__in=stage_matches)
        if health_matches:
            query_filter |= Q(health__in=health_matches)
        queryset = queryset.filter(query_filter)
    if priority in {value for value, _label in TaskProject.PRIORITY_CHOICES}:
        queryset = queryset.filter(priority=priority)
    if status in {value for value, _label in TaskProject.STATUS_CHOICES}:
        queryset = queryset.filter(status=status)
    if stage in {value for value, _label in TaskProject.STAGE_CHOICES}:
        queryset = queryset.filter(stage=stage)
    if health in {value for value, _label in TaskProject.HEALTH_CHOICES}:
        queryset = queryset.filter(health=health)
    if company == 'none':
        queryset = queryset.filter(company__isnull=True)
    elif company_id := _integer_filter_value(company):
        queryset = queryset.filter(company_id=company_id)
    if responsible == 'none':
        queryset = queryset.filter(responsible_user__isnull=True)
    elif responsible_id := _integer_filter_value(responsible):
        queryset = queryset.filter(responsible_user_id=responsible_id)
    return queryset


def _project_sort_queryset(queryset, sort_value):
    sort_value = _project_sort_value(sort_value)
    if sort_value == 'name_desc':
        return queryset.order_by('-name', 'id')
    if sort_value == 'code_asc':
        return queryset.order_by('code', 'name', 'id')
    if sort_value == 'company_asc':
        return queryset.annotate(
            company_empty_sort=Case(
                When(company__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('company_empty_sort', 'company__name', 'name', 'id')
    if sort_value == 'responsible_asc':
        return queryset.annotate(
            responsible_empty_sort=Case(
                When(responsible_user__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by(
            'responsible_empty_sort',
            'responsible_user__last_name',
            'responsible_user__first_name',
            'responsible_user__username',
            'name',
            'id',
        )
    if sort_value == 'status_asc':
        return queryset.annotate(
            status_sort_rank=_choice_rank_case('status', TaskProject.STATUS_CHOICES)
        ).order_by('status_sort_rank', 'name', 'id')
    if sort_value == 'priority_desc':
        return queryset.annotate(
            priority_sort_rank=_choice_rank_case('priority', TaskProject.PRIORITY_CHOICES)
        ).order_by('-priority_sort_rank', 'name', 'id')
    if sort_value == 'due_at_asc':
        return queryset.annotate(
            due_empty_sort=Case(
                When(due_at__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('due_empty_sort', 'due_at', 'name', 'id')
    if sort_value == 'created_desc':
        return queryset.order_by('-created_at', 'name', 'id')
    if sort_value == 'activity_desc':
        return queryset.annotate(
            last_task_created_sort=Max('sections__tasks__created_at'),
            last_activity_sort=Max('sections__tasks__activities__created_at'),
        ).order_by('-last_activity_sort', '-last_task_created_sort', '-created_at', 'name', 'id')
    return queryset.order_by('name', 'id')


def _project_filter_options(user, workplace=None):
    queryset = _filter_workplace(
        TaskProject.objects.filter(user=user),
        workplace,
    ).select_related('company', 'responsible_user')
    companies = [
        {'value': str(row['company_id']), 'label': row['company__name']}
        for row in queryset.filter(company__isnull=False)
        .values('company_id', 'company__name')
        .distinct()
        .order_by('company__name', 'company_id')
    ]
    responsible_users = []
    for row in (
        queryset.filter(responsible_user__isnull=False)
        .values(
            'responsible_user_id',
            'responsible_user__first_name',
            'responsible_user__last_name',
            'responsible_user__username',
        )
        .distinct()
        .order_by('responsible_user__last_name', 'responsible_user__first_name', 'responsible_user__username')
    ):
        full_name = ' '.join(
            part for part in (
                row['responsible_user__first_name'],
                row['responsible_user__last_name'],
            )
            if part
        ).strip()
        responsible_users.append({
            'value': str(row['responsible_user_id']),
            'label': full_name or row['responsible_user__username'],
        })

    if queryset.filter(company__isnull=True).exists():
        companies.insert(0, {'value': 'none', 'label': 'Brak firmy'})
    if queryset.filter(responsible_user__isnull=True).exists():
        responsible_users.insert(0, {'value': 'none', 'label': 'Brak osoby'})

    return {
        'statuses': _choice_options(TaskProject.STATUS_CHOICES),
        'stages': _choice_options(TaskProject.STAGE_CHOICES),
        'healths': _choice_options(TaskProject.HEALTH_CHOICES),
        'companies': companies,
        'responsible_users': responsible_users,
    }


def _empty_project_filter_options():
    return {
        'statuses': _choice_options(TaskProject.STATUS_CHOICES),
        'stages': _choice_options(TaskProject.STAGE_CHOICES),
        'healths': _choice_options(TaskProject.HEALTH_CHOICES),
        'companies': [],
        'responsible_users': [],
    }


def _group_filter_queryset(
    user,
    query='',
    priority='',
    status='',
    kind='',
    project_filter='',
    owner='',
    workplace=None,
):
    queryset = TaskSection.objects.filter(project__user=user).select_related('project', 'project__user', 'owner')
    queryset = _filter_workplace(queryset, workplace, field_name='project__workplace')
    query = (query or '').strip()
    if query:
        group_code_number = parse_hierarchy_code_number(query, TaskSection.CODE_PREFIX)
        priority_matches = _choice_values_matching_query(TaskSection.PRIORITY_CHOICES, query)
        status_matches = _choice_values_matching_query(TaskSection.STATUS_CHOICES, query)
        kind_matches = _choice_values_matching_query(TaskSection.KIND_CHOICES, query)
        query_filter = (
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(project__name__icontains=query)
            | Q(project__code__icontains=query)
            | Q(status__icontains=query)
            | Q(kind__icontains=query)
            | Q(owner__first_name__icontains=query)
            | Q(owner__middle_name__icontains=query)
            | Q(owner__last_name__icontains=query)
            | Q(owner__email__icontains=query)
            | Q(owner__username__icontains=query)
        )
        if group_code_number:
            query_filter |= Q(code_number=group_code_number)
        if priority_matches:
            query_filter |= Q(priority__in=priority_matches)
        if status_matches:
            query_filter |= Q(status__in=status_matches)
        if kind_matches:
            query_filter |= Q(kind__in=kind_matches)
        queryset = queryset.filter(query_filter)
    if priority in {value for value, _label in TaskSection.PRIORITY_CHOICES}:
        queryset = queryset.filter(priority=priority)
    if status in {value for value, _label in TaskSection.STATUS_CHOICES}:
        queryset = queryset.filter(status=status)
    if kind in {value for value, _label in TaskSection.KIND_CHOICES}:
        queryset = queryset.filter(kind=kind)
    if project_id := _integer_filter_value(project_filter):
        queryset = queryset.filter(project_id=project_id)
    if owner == 'none':
        queryset = queryset.filter(owner__isnull=True)
    elif owner_id := _integer_filter_value(owner):
        queryset = queryset.filter(owner_id=owner_id)
    return queryset.prefetch_related(
        Prefetch(
            'section_notes',
            queryset=TaskSectionNote.objects.select_related('author').order_by('created_at', 'id'),
        )
    )


def _group_sort_queryset(queryset, sort_value):
    sort_value = _group_sort_value(sort_value)
    if sort_value == 'title_asc':
        return queryset.order_by('title', 'id')
    if sort_value == 'title_desc':
        return queryset.order_by('-title', 'id')
    if sort_value == 'code_asc':
        return queryset.order_by('project__code', 'code_number', 'title', 'id')
    if sort_value == 'status_asc':
        return queryset.annotate(
            status_sort_rank=_choice_rank_case('status', TaskSection.STATUS_CHOICES)
        ).order_by('status_sort_rank', 'project__name', 'order', 'id')
    if sort_value == 'kind_asc':
        return queryset.annotate(
            kind_sort_rank=_choice_rank_case('kind', TaskSection.KIND_CHOICES)
        ).order_by('kind_sort_rank', 'project__name', 'order', 'id')
    if sort_value == 'priority_desc':
        return queryset.annotate(
            priority_sort_rank=_choice_rank_case('priority', TaskSection.PRIORITY_CHOICES)
        ).order_by('-priority_sort_rank', 'project__name', 'order', 'id')
    if sort_value == 'owner_asc':
        return queryset.annotate(
            owner_empty_sort=Case(
                When(owner__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by(
            'owner_empty_sort',
            'owner__last_name',
            'owner__first_name',
            'owner__username',
            'project__name',
            'order',
            'id',
        )
    if sort_value == 'due_at_asc':
        return queryset.annotate(
            due_empty_sort=Case(
                When(due_at__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('due_empty_sort', 'due_at', 'project__name', 'order', 'id')
    if sort_value == 'created_desc':
        return queryset.order_by('-created_at', 'project__name', 'order', 'id')
    if sort_value == 'activity_desc':
        return queryset.annotate(
            last_task_created_sort=Max('tasks__created_at'),
            last_activity_sort=Max('tasks__activities__created_at'),
        ).order_by('-last_activity_sort', '-last_task_created_sort', '-created_at', 'project__name', 'order', 'id')
    return queryset.order_by('project__name', 'order', 'created_at', 'id')


def _group_filter_options(user, workplace=None):
    queryset = TaskSection.objects.filter(project__user=user).select_related('project', 'owner')
    queryset = _filter_workplace(queryset, workplace, field_name='project__workplace')
    projects = [
        {'value': str(row['project_id']), 'label': row['project__name']}
        for row in queryset.values('project_id', 'project__name')
        .distinct()
        .order_by('project__name', 'project_id')
    ]
    owners = []
    for row in (
        queryset.filter(owner__isnull=False)
        .values('owner_id', 'owner__first_name', 'owner__last_name', 'owner__username')
        .distinct()
        .order_by('owner__last_name', 'owner__first_name', 'owner__username')
    ):
        full_name = ' '.join(
            part for part in (
                row['owner__first_name'],
                row['owner__last_name'],
            )
            if part
        ).strip()
        owners.append({
            'value': str(row['owner_id']),
            'label': full_name or row['owner__username'],
        })

    if queryset.filter(owner__isnull=True).exists():
        owners.insert(0, {'value': 'none', 'label': 'Brak osoby'})

    return {
        'statuses': _choice_options(TaskSection.STATUS_CHOICES),
        'kinds': _choice_options(TaskSection.KIND_CHOICES),
        'projects': projects,
        'owners': owners,
    }


def _empty_group_filter_options():
    return {
        'statuses': _choice_options(TaskSection.STATUS_CHOICES),
        'kinds': _choice_options(TaskSection.KIND_CHOICES),
        'projects': [],
        'owners': [],
    }


def _task_filter_queryset(
    queryset,
    query='',
    priority='',
    status='',
    project_filter='',
    section='',
    assignee='',
    company='',
    task_type='',
    due='',
):
    query = (query or '').strip()
    if query:
        task_code_number = parse_hierarchy_code_number(query, Task.CODE_PREFIX)
        section_code_number = parse_hierarchy_code_number(query, TaskSection.CODE_PREFIX)
        task_id = _integer_filter_value(query)
        priority_matches = _choice_values_matching_query(Task.PRIORITY_CHOICES, query)
        status_matches = _choice_values_matching_query(Task.STATUS_CHOICES, query)
        type_matches = _choice_values_matching_query(Task.TASK_TYPE_CHOICES, query)
        channel_matches = _choice_values_matching_query(Task.CONTACT_CHANNEL_CHOICES, query)
        query_filter = (
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(section__title__icontains=query)
            | Q(section__description__icontains=query)
            | Q(section__project__name__icontains=query)
            | Q(section__project__code__icontains=query)
            | Q(company__name__icontains=query)
            | Q(contact__first_name__icontains=query)
            | Q(contact__middle_name__icontains=query)
            | Q(contact__last_name__icontains=query)
            | Q(contact__company__icontains=query)
            | Q(contact__email__icontains=query)
            | Q(assignee__first_name__icontains=query)
            | Q(assignee__middle_name__icontains=query)
            | Q(assignee__last_name__icontains=query)
            | Q(assignee__email__icontains=query)
            | Q(assignee__username__icontains=query)
            | Q(tags__name__icontains=query)
            | Q(tags__code__icontains=query)
        )
        if task_id:
            query_filter |= Q(task_id=task_id)
        if task_code_number:
            query_filter |= Q(code_number=task_code_number)
        if section_code_number:
            query_filter |= Q(section__code_number=section_code_number)
        if priority_matches:
            query_filter |= Q(priority__in=priority_matches)
        if status_matches:
            query_filter |= Q(status__in=status_matches)
        if type_matches:
            query_filter |= Q(task_type__in=type_matches)
        if channel_matches:
            query_filter |= Q(contact_channel__in=channel_matches)
        queryset = queryset.filter(query_filter).distinct()
    if priority in {value for value, _label in Task.PRIORITY_CHOICES}:
        queryset = queryset.filter(priority=priority)
    if status in {value for value, _label in Task.STATUS_CHOICES}:
        queryset = queryset.filter(status=status)
    if project_id := _integer_filter_value(project_filter):
        queryset = queryset.filter(section__project_id=project_id)
    if section_id := _integer_filter_value(section):
        queryset = queryset.filter(section_id=section_id)
    if assignee == 'none':
        queryset = queryset.filter(assignee__isnull=True)
    elif assignee_id := _integer_filter_value(assignee):
        queryset = queryset.filter(assignee_id=assignee_id)
    if company == 'none':
        queryset = queryset.filter(company__isnull=True)
    elif company_id := _integer_filter_value(company):
        queryset = queryset.filter(company_id=company_id)
    if task_type in {value for value, _label in Task.TASK_TYPE_CHOICES}:
        queryset = queryset.filter(task_type=task_type)
    today = timezone.localdate()
    if due == 'overdue':
        queryset = queryset.filter(due_at__date__lt=today).exclude(status='closed')
    elif due == 'today':
        queryset = queryset.filter(due_at__date=today)
    elif due == 'week':
        queryset = queryset.filter(due_at__date__range=(today, today + timedelta(days=6)))
    elif due == 'none':
        queryset = queryset.filter(due_at__isnull=True)
    return queryset


def _task_sort_queryset(queryset, sort_value):
    sort_value = _task_sort_value(sort_value)
    if sort_value == 'task_id_desc':
        return queryset.order_by('-task_id', '-created_at', '-id')
    if sort_value == 'title_asc':
        return queryset.order_by('title', 'task_id', 'id')
    if sort_value == 'title_desc':
        return queryset.order_by('-title', 'task_id', 'id')
    if sort_value == 'priority_desc':
        return queryset.annotate(
            task_priority_sort_rank=_choice_rank_case('priority', Task.PRIORITY_CHOICES)
        ).order_by('-task_priority_sort_rank', 'task_id', 'id')
    if sort_value == 'project_asc':
        return queryset.order_by('section__project__name', 'section__order', 'task_id', 'id')
    if sort_value == 'section_asc':
        return queryset.order_by('section__title', 'section__project__name', 'task_id', 'id')
    if sort_value == 'assignee_asc':
        return queryset.annotate(
            task_assignee_empty_sort=Case(
                When(assignee__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by(
            'task_assignee_empty_sort',
            'assignee__last_name',
            'assignee__first_name',
            'assignee__username',
            'task_id',
            'id',
        )
    if sort_value == 'company_asc':
        return queryset.annotate(
            task_company_empty_sort=Case(
                When(company__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('task_company_empty_sort', 'company__name', 'task_id', 'id')
    if sort_value == 'type_asc':
        return queryset.annotate(
            task_type_sort_rank=_choice_rank_case('task_type', Task.TASK_TYPE_CHOICES)
        ).order_by('task_type_sort_rank', 'task_id', 'id')
    if sort_value == 'due_at_asc':
        return queryset.annotate(
            task_due_empty_sort=Case(
                When(due_at__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('task_due_empty_sort', 'due_at', 'task_id', 'id')
    if sort_value == 'created_desc':
        return queryset.order_by('-created_at', '-id')
    if sort_value == 'activity_desc':
        return queryset.annotate(
            task_last_activity_sort=Max('activities__created_at'),
        ).order_by('-task_last_activity_sort', '-created_at', '-id')
    return queryset.order_by('is_closed_sort', 'task_id', 'id')


def _task_filter_options(user, workplace=None):
    queryset = _filter_workplace(
        Task.objects.filter(user=user, parent__isnull=True),
        workplace,
    ).select_related('section', 'section__project', 'assignee', 'company')
    projects = [
        {'value': str(row['section__project_id']), 'label': row['section__project__name']}
        for row in queryset.filter(section__project__isnull=False)
        .values('section__project_id', 'section__project__name')
        .distinct()
        .order_by('section__project__name', 'section__project_id')
    ]
    sections = [
        {
            'value': str(row['section_id']),
            'label': f"{row['section__title']} ({row['section__project__name']})",
        }
        for row in queryset.filter(section__isnull=False)
        .values('section_id', 'section__title', 'section__project__name')
        .distinct()
        .order_by('section__project__name', 'section__title', 'section_id')
    ]
    assignees = []
    for row in (
        queryset.filter(assignee__isnull=False)
        .values('assignee_id', 'assignee__first_name', 'assignee__last_name', 'assignee__username')
        .distinct()
        .order_by('assignee__last_name', 'assignee__first_name', 'assignee__username')
    ):
        full_name = ' '.join(
            part for part in (
                row['assignee__first_name'],
                row['assignee__last_name'],
            )
            if part
        ).strip()
        assignees.append({
            'value': str(row['assignee_id']),
            'label': full_name or row['assignee__username'],
        })
    companies = [
        {'value': str(row['company_id']), 'label': row['company__name']}
        for row in queryset.filter(company__isnull=False)
        .values('company_id', 'company__name')
        .distinct()
        .order_by('company__name', 'company_id')
    ]

    if queryset.filter(assignee__isnull=True).exists():
        assignees.insert(0, {'value': 'none', 'label': 'Brak osoby'})
    if queryset.filter(company__isnull=True).exists():
        companies.insert(0, {'value': 'none', 'label': 'Brak firmy'})

    return {
        'statuses': _choice_options(Task.STATUS_CHOICES),
        'priorities': _choice_options(Task.PRIORITY_CHOICES),
        'types': _choice_options(Task.TASK_TYPE_CHOICES),
        'due': TASK_DUE_FILTER_OPTIONS,
        'projects': projects,
        'sections': sections,
        'assignees': assignees,
        'companies': companies,
    }


def _task_window_for_request(request, queryset):
    workplace = _active_workplace(request)
    query = (request.GET.get('q') or '').strip()
    priority = (request.GET.get('priority') or '').strip()
    status = (request.GET.get('status') or '').strip()
    project_filter = (request.GET.get('task_project') or '').strip()
    section = (request.GET.get('task_section') or '').strip()
    assignee = (request.GET.get('task_assignee') or '').strip()
    company = (request.GET.get('task_company') or '').strip()
    task_type = (request.GET.get('task_type') or '').strip()
    due = (request.GET.get('task_due') or '').strip()
    sort = _task_sort_value((request.GET.get('sort') or '').strip())
    queryset = _task_filter_queryset(
        queryset,
        query=query,
        priority=priority,
        status=status,
        project_filter=project_filter,
        section=section,
        assignee=assignee,
        company=company,
        task_type=task_type,
        due=due,
    )
    queryset = _task_sort_queryset(queryset, sort)
    active_filters = any((
        query,
        priority,
        status,
        project_filter,
        section,
        assignee,
        company,
        task_type,
        due,
        sort != TASK_DEFAULT_SORT,
    ))
    return {
        'queryset': queryset,
        'query': query,
        'priority': priority,
        'status': status,
        'project_filter': project_filter,
        'section': section,
        'assignee': assignee,
        'company': company,
        'task_type': task_type,
        'due': due,
        'sort': sort,
        'sort_param': '' if sort == TASK_DEFAULT_SORT else sort,
        'sort_label': TASK_SORT_OPTION_MAP[sort]['label'],
        'sort_direction': TASK_SORT_OPTION_MAP[sort]['direction'],
        'filters': _task_filter_options(request.user, workplace=workplace),
        'total_tasks': queryset.count(),
        'has_active_filters': active_filters,
    }


def _tag_filter_queryset(user, query='', workplace=None):
    queryset = _filter_workplace(TaskTag.objects.filter(user=user), workplace)
    query = (query or '').strip()
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(code__icontains=query)
            | Q(owner_label__icontains=query)
            | Q(usage_notes__icontains=query)
            | Q(automation_rules__icontains=query)
        )
    return queryset.prefetch_related(
        Prefetch(
            'tag_notes',
            queryset=TaskTagNote.objects.select_related('author').order_by('created_at', 'id'),
        )
    )


def _projects_for_user(user, tasks_queryset=None, project_queryset=None, order_by=('name', 'id'), limit=None, offset=0, workplace=None):
    projects_filter = Q(user=user)
    if workplace is not None:
        projects_filter &= Q(workplace=workplace)
    sections_queryset = TaskSection.objects.select_related('project', 'project__user', 'owner')
    sections_queryset = _filter_workplace(sections_queryset, workplace, field_name='project__workplace')
    if tasks_queryset is not None:
        sections_queryset = sections_queryset.prefetch_related(
            Prefetch('tasks', queryset=tasks_queryset)
        )

    queryset = (
        (project_queryset if project_queryset is not None else TaskProject.objects.filter(projects_filter))
        .distinct()
        .select_related('user', 'company', 'responsible_user')
        .annotate(
            total_tasks=Count(
                'sections__tasks',
                filter=Q(sections__tasks__parent__isnull=True),
            )
        )
        .prefetch_related(
            Prefetch(
                'sections',
                queryset=sections_queryset,
            ),
            Prefetch(
                'project_notes',
                queryset=TaskProjectNote.objects.select_related('author').order_by('created_at', 'id'),
            ),
        )
    )
    if order_by:
        queryset = queryset.order_by(*order_by)
    if limit is not None:
        queryset = queryset[offset:offset + limit]
    projects = list(queryset)
    return _mark_project_permissions(projects, user)


def _project_for_user(user, project_id, workplace=None):
    if not project_id:
        return None
    projects = _projects_for_user(
        user,
        project_queryset=_filter_workplace(TaskProject.objects.filter(user=user, id=project_id), workplace),
        order_by=None,
        limit=1,
        workplace=workplace,
    )
    return projects[0] if projects else None


def _project_window_for_request(request):
    workplace = _active_workplace(request)
    page_size = _project_page_size(request)
    requested_page = _project_page_number(request)
    query = (request.GET.get('q') or '').strip()
    priority = (request.GET.get('priority') or '').strip()
    status = (request.GET.get('status') or '').strip()
    stage = (request.GET.get('stage') or '').strip()
    health = (request.GET.get('health') or '').strip()
    company = (request.GET.get('company') or '').strip()
    responsible = (request.GET.get('responsible') or '').strip()
    sort = _project_sort_value((request.GET.get('sort') or '').strip())
    queryset = _project_filter_queryset(
        request.user,
        query=query,
        priority=priority,
        status=status,
        stage=stage,
        health=health,
        company=company,
        responsible=responsible,
        workplace=workplace,
    )
    queryset = _project_sort_queryset(queryset, sort)
    total_projects = queryset.count()
    total_pages = max(1, (total_projects + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size

    projects = _projects_for_user(
        request.user,
        project_queryset=queryset,
        order_by=None,
        limit=page_size,
        offset=offset,
        workplace=workplace,
    )

    _decorate_project_directory_metrics(projects)
    _decorate_directory_members(projects, current_user=request.user)

    base_params = {
        'q': query,
        'priority': priority,
        'status': status,
        'stage': stage,
        'health': health,
        'company': company,
        'responsible': responsible,
        'sort': '' if sort == PROJECT_DEFAULT_SORT else sort,
        'page_size': page_size,
    }
    has_previous = current_page > 1 and total_projects > 0
    has_next = current_page < total_pages and total_projects > 0
    previous_url = ''
    next_url = ''
    if has_previous:
        previous_page_params = {**base_params, 'page': current_page - 1}
        if current_page - 1 == 1:
            previous_page_params.pop('page', None)
        previous_url = _projects_url(previous_page_params)
    if has_next:
        next_url = _projects_url({**base_params, 'page': current_page + 1})

    if not projects:
        summary = 'Brak projektów'
    else:
        first_visible = offset + 1
        last_visible = offset + len(projects)
        summary = f'Pokazano {first_visible}-{last_visible} z {total_projects} projektów'

    return {
        'projects': projects,
        'query': query,
        'priority': priority,
        'status': status,
        'stage': stage,
        'health': health,
        'company': company,
        'responsible': responsible,
        'sort': sort,
        'sort_param': '' if sort == PROJECT_DEFAULT_SORT else sort,
        'sort_label': PROJECT_SORT_OPTION_MAP[sort]['label'],
        'sort_direction': PROJECT_SORT_OPTION_MAP[sort]['direction'],
        'filters': _project_filter_options(request.user, workplace=workplace),
        'page': current_page,
        'total_pages': total_pages,
        'total_projects': total_projects,
        'page_size': page_size,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'page_items': _project_page_items(current_page, total_pages, base_params) if total_projects else [],
        'has_previous': has_previous,
        'has_next': has_next,
        'previous_url': previous_url,
        'next_url': next_url,
        'summary': summary,
    }


def _group_window_for_request(request):
    workplace = _active_workplace(request)
    page_size = _project_page_size(request)
    requested_page = _project_page_number(request)
    query = (request.GET.get('q') or '').strip()
    priority = (request.GET.get('priority') or '').strip()
    status = (request.GET.get('status') or '').strip()
    kind = (request.GET.get('kind') or '').strip()
    project_filter = (request.GET.get('group_project') or '').strip()
    owner = (request.GET.get('owner') or '').strip()
    sort = _group_sort_value((request.GET.get('sort') or '').strip())
    queryset = _group_filter_queryset(
        request.user,
        query=query,
        priority=priority,
        status=status,
        kind=kind,
        project_filter=project_filter,
        owner=owner,
        workplace=workplace,
    )
    queryset = _group_sort_queryset(queryset, sort)
    total_groups = queryset.count()
    total_pages = max(1, (total_groups + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size

    sections = list(queryset[offset:offset + page_size])
    _decorate_group_directory_rows(sections, current_user=request.user)

    base_params = {
        'view': 'all-groups',
        'q': query,
        'priority': priority,
        'status': status,
        'kind': kind,
        'group_project': project_filter,
        'owner': owner,
        'sort': '' if sort == GROUP_DEFAULT_SORT else sort,
        'page_size': page_size,
    }
    has_previous = current_page > 1 and total_groups > 0
    has_next = current_page < total_pages and total_groups > 0
    previous_url = ''
    next_url = ''
    if has_previous:
        previous_page_params = {**base_params, 'page': current_page - 1}
        if current_page - 1 == 1:
            previous_page_params.pop('page', None)
        previous_url = _projects_url(previous_page_params)
    if has_next:
        next_url = _projects_url({**base_params, 'page': current_page + 1})

    if not sections:
        summary = 'Brak grup'
    else:
        first_visible = offset + 1
        last_visible = offset + len(sections)
        summary = f'Pokazano {first_visible}-{last_visible} z {total_groups} grup'

    return {
        'sections': sections,
        'query': query,
        'priority': priority,
        'status': status,
        'kind': kind,
        'project_filter': project_filter,
        'owner': owner,
        'sort': sort,
        'sort_param': '' if sort == GROUP_DEFAULT_SORT else sort,
        'sort_label': GROUP_SORT_OPTION_MAP[sort]['label'],
        'sort_direction': GROUP_SORT_OPTION_MAP[sort]['direction'],
        'filters': _group_filter_options(request.user, workplace=workplace),
        'page': current_page,
        'total_pages': total_pages,
        'total_groups': total_groups,
        'page_size': page_size,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'page_items': _project_page_items(current_page, total_pages, base_params) if total_groups else [],
        'has_previous': has_previous,
        'has_next': has_next,
        'previous_url': previous_url,
        'next_url': next_url,
        'summary': summary,
    }


def _project_section_window_for_request(request, project):
    page_size = _project_page_size(request)
    requested_page = _project_page_number(request)
    query = (request.GET.get('q') or '').strip()
    priority = (request.GET.get('priority') or '').strip()
    queryset = _filter_workplace(
        TaskSection.objects.filter(project=project).select_related('project', 'project__user', 'owner'),
        _active_workplace(request),
        field_name='project__workplace',
    ).prefetch_related(
        Prefetch(
            'section_notes',
            queryset=TaskSectionNote.objects.select_related('author').order_by('created_at', 'id'),
        )
    )
    if query:
        group_code_number = parse_hierarchy_code_number(query, TaskSection.CODE_PREFIX)
        query_filter = (
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(project__name__icontains=query)
            | Q(project__code__icontains=query)
        )
        if group_code_number:
            query_filter |= Q(code_number=group_code_number)
        queryset = queryset.filter(
            query_filter
        )
    if priority in {value for value, _label in TaskSection.PRIORITY_CHOICES}:
        queryset = queryset.filter(priority=priority)

    total_groups = queryset.count()
    total_pages = max(1, (total_groups + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size

    sections = list(queryset.order_by('order', 'created_at', 'id')[offset:offset + page_size])
    _decorate_group_directory_rows(sections, current_user=request.user)

    base_params = {
        'project': project.id,
        'q': query,
        'priority': priority,
        'page_size': page_size,
    }
    has_previous = current_page > 1 and total_groups > 0
    has_next = current_page < total_pages and total_groups > 0
    previous_url = ''
    next_url = ''
    if has_previous:
        previous_page_params = {**base_params, 'page': current_page - 1}
        if current_page - 1 == 1:
            previous_page_params.pop('page', None)
        previous_url = _projects_url(previous_page_params)
    if has_next:
        next_url = _projects_url({**base_params, 'page': current_page + 1})

    if not sections:
        summary = 'Brak grup'
    else:
        first_visible = offset + 1
        last_visible = offset + len(sections)
        summary = f'Pokazano {first_visible}-{last_visible} z {total_groups} grup'

    return {
        'sections': sections,
        'query': query,
        'priority': priority,
        'page': current_page,
        'total_pages': total_pages,
        'total_groups': total_groups,
        'page_size': page_size,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'page_items': _project_page_items(current_page, total_pages, base_params) if total_groups else [],
        'has_previous': has_previous,
        'has_next': has_next,
        'previous_url': previous_url,
        'next_url': next_url,
        'summary': summary,
    }


def _tag_window_for_request(request):
    workplace = _active_workplace(request)
    page_size = _project_page_size(request)
    requested_page = _project_page_number(request)
    query = (request.GET.get('q') or '').strip()
    queryset = _tag_filter_queryset(request.user, query=query, workplace=workplace)
    total_tags = queryset.count()
    total_pages = max(1, (total_tags + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size

    tags = list(
        queryset.prefetch_related('related_tags').annotate(
            total_tasks=Count(
                'tasks',
                filter=Q(tasks__user=request.user, tasks__workplace=workplace, tasks__parent__isnull=True),
            )
        ).order_by('name', 'id')[offset:offset + page_size]
    )
    for tag in tags:
        related_tags = list(tag.related_tags.all())
        tag.related_tag_ids = ','.join(str(related_tag.id) for related_tag in related_tags)
        tag.related_tags_label = ', '.join(related_tag.name for related_tag in related_tags) or 'Brak powiązań'

    base_params = {
        'view': 'tags',
        'q': query,
        'page_size': page_size,
    }
    has_previous = current_page > 1 and total_tags > 0
    has_next = current_page < total_pages and total_tags > 0
    previous_url = ''
    next_url = ''
    if has_previous:
        previous_page_params = {**base_params, 'page': current_page - 1}
        if current_page - 1 == 1:
            previous_page_params.pop('page', None)
        previous_url = _projects_url(previous_page_params)
    if has_next:
        next_url = _projects_url({**base_params, 'page': current_page + 1})

    if not tags:
        summary = 'Brak tagów'
    else:
        first_visible = offset + 1
        last_visible = offset + len(tags)
        summary = f'Pokazano {first_visible}-{last_visible} z {total_tags} tagów'

    return {
        'tags': tags,
        'query': query,
        'page': current_page,
        'total_pages': total_pages,
        'total_tags': total_tags,
        'page_size': page_size,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'page_items': _project_page_items(current_page, total_pages, base_params) if total_tags else [],
        'has_previous': has_previous,
        'has_next': has_next,
        'previous_url': previous_url,
        'next_url': next_url,
        'summary': summary,
    }


def _navigation_projects_for_user(user, active_project=None, workplace=None):
    projects = _projects_for_user(user, limit=PROJECT_NAVIGATION_LIMIT, workplace=workplace)
    if active_project and all(project.id != active_project.id for project in projects):
        projects = [active_project, *projects]
    return projects


def _navigation_project_ids_for_user(user, active_project=None, workplace=None):
    project_ids = list(
        _filter_workplace(TaskProject.objects.filter(user=user), workplace)
        .order_by('name', 'id')
        .values_list('id', flat=True)[:PROJECT_NAVIGATION_LIMIT]
    )
    if active_project and active_project.id not in project_ids:
        project_ids.insert(0, active_project.id)
    return project_ids


def _task_modal_picker_options(projects):
    options = []
    for project in projects:
        sections = [
            {
                'sectionId': str(section.id),
                'sectionProjectId': str(project.id),
                'sectionTitle': section.title,
                'sectionIcon': section.icon or '',
            }
            for section in project.sections.all()
            if getattr(section, 'can_edit', False)
        ]
        if not (getattr(project, 'can_edit', False) or getattr(project, 'has_editable_sections', False) or sections):
            continue

        icon_color = getattr(project, 'icon_color', None)
        options.append({
            'projectId': str(project.id),
            'projectName': project.name,
            'projectIcon': project.icon or '',
            'projectColor': getattr(icon_color, 'foreground', ''),
            'defaultSectionId': '',
            'sections': sections,
        })
    return options


def _decorate_project_directory_metrics(projects):
    if not projects:
        return

    section_ids = []
    for project in projects:
        for section in project.sections.all():
            section_ids.append(section.id)

    metrics_by_section = {}
    if section_ids:
        metrics_by_section = {
            row['section_id']: row
            for row in (
                Task.objects.filter(section_id__in=section_ids, parent__isnull=True)
                .values('section_id')
                .annotate(
                    total_tasks=Count('id', distinct=True),
                    completed_tasks=Count(
                        'id',
                        filter=Q(is_completed=True) | Q(status='closed'),
                        distinct=True,
                    ),
                    last_task_created=Max('created_at'),
                    last_activity=Max('activities__created_at'),
                )
            )
        }

    for project in projects:
        last_activity_candidates = [project.created_at]
        project_total_tasks = 0
        project_completed_tasks = 0

        for section in project.sections.all():
            section_metrics = metrics_by_section.get(section.id, {})
            section_total_tasks = section_metrics.get('total_tasks') or 0
            section_completed_tasks = section_metrics.get('completed_tasks') or 0
            if section_total_tasks:
                section_progress_percent = round((section_completed_tasks / section_total_tasks) * 100)
            else:
                section_progress_percent = 0

            section_activity_candidates = [section.created_at]
            section_activity_candidates.extend([
                section_metrics.get('last_task_created'),
                section_metrics.get('last_activity'),
            ])

            section.tasks_total_count = section_total_tasks
            section.tasks_completed_count = section_completed_tasks
            section.tasks_count_label = f'{section_completed_tasks}/{section_total_tasks}'
            section.progress_percent = section_progress_percent
            section.last_activity_at = max(
                (value for value in section_activity_candidates if value),
                default=section.created_at,
            )
            project_total_tasks += section_total_tasks
            project_completed_tasks += section_completed_tasks
            last_activity_candidates.append(section.last_activity_at)

        if project_total_tasks:
            project_progress_percent = round((project_completed_tasks / project_total_tasks) * 100)
        else:
            project_progress_percent = 0

        project.tasks_total_count = project_total_tasks
        project.tasks_completed_count = project_completed_tasks
        project.tasks_count_label = f'{project_completed_tasks}/{project_total_tasks}'
        project.progress_percent = project_progress_percent
        project.last_activity_at = max(
            (value for value in last_activity_candidates if value),
            default=project.created_at,
        )


def _decorate_group_directory_rows(sections, current_user=None):
    if not sections:
        return

    section_ids = [section.id for section in sections]
    metrics_by_section = {
        row['section_id']: row
        for row in (
            Task.objects.filter(section_id__in=section_ids, parent__isnull=True)
            .values('section_id')
            .annotate(
                total_tasks=Count('id', distinct=True),
                completed_tasks=Count(
                    'id',
                    filter=Q(is_completed=True) | Q(status='closed'),
                    distinct=True,
                ),
                last_task_created=Max('created_at'),
                last_activity=Max('activities__created_at'),
            )
        )
    }

    for section in sections:
        project = section.project
        can_manage_project = project.user_id == getattr(current_user, 'id', None)
        project.can_manage = can_manage_project
        project.can_share = False
        project.can_edit = can_manage_project
        _clear_share_access_badge(section)
        section.can_manage = can_manage_project
        section.can_share = False
        section.can_edit = can_manage_project

        section_metrics = metrics_by_section.get(section.id, {})
        total_tasks = section_metrics.get('total_tasks') or 0
        completed_tasks = section_metrics.get('completed_tasks') or 0
        progress_percent = round((completed_tasks / total_tasks) * 100) if total_tasks else 0
        activity_candidates = [
            section.created_at,
            section_metrics.get('last_task_created'),
            section_metrics.get('last_activity'),
        ]

        section.tasks_total_count = total_tasks
        section.tasks_completed_count = completed_tasks
        section.tasks_count_label = f'{completed_tasks}/{total_tasks}'
        section.progress_percent = progress_percent
        section.last_activity_at = max(
            (value for value in activity_candidates if value),
            default=section.created_at,
        )


def _shared_users_by_object(content_type, object_ids):
    return defaultdict(list)


def _directory_member_payload(entries):
    members = []
    seen_user_ids = set()
    for entry in entries:
        if isinstance(entry, dict):
            user = entry.get('user')
            role = entry.get('role', 'Członek')
            permission = entry.get('permission', '')
            permission_label = entry.get('permission_label') or (_share_permission_label(permission) if permission else role)
        else:
            user = entry
            role = 'Członek'
            permission = ''
            permission_label = role
        if not user or user.pk in seen_user_ids:
            continue
        seen_user_ids.add(user.pk)
        members.append({
            'avatar': account_avatar(user),
            'label': _user_display_name(user),
            'role': role,
            'permission': permission,
            'permission_label': permission_label,
            'username': user.username,
            'email': user.email,
            'user_id': user.pk,
            'can_remove': entry.get('can_remove', False) if isinstance(entry, dict) else False,
            'can_update_permission': entry.get('can_update_permission', entry.get('can_remove', False)) if isinstance(entry, dict) else False,
            'remove_action': entry.get('remove_action', '') if isinstance(entry, dict) else '',
            'permission_action': entry.get('permission_action', '') if isinstance(entry, dict) else '',
            'remove_project_id': entry.get('remove_project_id', '') if isinstance(entry, dict) else '',
            'remove_section_id': entry.get('remove_section_id', '') if isinstance(entry, dict) else '',
            'remove_task_id': entry.get('remove_task_id', '') if isinstance(entry, dict) else '',
            'remove_label': entry.get('remove_label', 'Przestań udostępniać') if isinstance(entry, dict) else 'Przestań udostępniać',
        })

    if not members:
        return {
            'members': [],
            'visible_members': [],
            'label': '',
            'shared_count': 0,
            'title': '',
        }

    shared_count = 0
    label = members[0]['label']

    return {
        'members': members,
        'visible_members': members[:3],
        'label': label,
        'shared_count': shared_count,
        'title': ', '.join(member['label'] for member in members),
    }


def _assign_directory_members(item, users):
    payload = _directory_member_payload(users)
    item.directory_members = payload['members']
    item.directory_visible_members = payload['visible_members']
    item.directory_member_label = payload['label']
    item.directory_shared_count = payload['shared_count']
    item.directory_member_title = payload['title']


def _decorate_directory_members(projects, current_user=None):
    if not projects:
        return

    for project in projects:
        can_manage_project = project.user_id == getattr(current_user, 'id', None)
        project.can_manage = can_manage_project
        project.can_share = False
        project.can_edit = can_manage_project
        project.has_editable_sections = False
        _assign_directory_members(
            project,
            [
                {'user': project.user, 'role': 'Właściciel', 'permission': 'owner'},
            ],
        )
        for section in project.sections.all():
            section.can_manage = can_manage_project
            section.can_share = False
            section.can_edit = can_manage_project
            if section.can_edit:
                project.has_editable_sections = True
            _assign_directory_members(
                section,
                [
                    {'user': project.user, 'role': 'Właściciel', 'permission': 'owner'},
                ],
            )


def _decorate_task_directory_members(tasks, current_user=None):
    task_list = [task for task in tasks if task]
    if not task_list:
        return

    for task in task_list:
        can_manage_task = task.user_id == getattr(current_user, 'id', None)
        task.can_manage = can_manage_task
        task.can_share = False
        task.can_edit = can_manage_task
        entries = [{'user': task.user, 'role': 'Właściciel', 'permission': 'owner'}]
        _assign_directory_members(task, entries)


def _contact_matches_query(user, query):
    query_normalized = query.casefold()
    direct_matches = get_user_model().objects.filter(
        is_active=True,
        added_by_users__owner=user,
    ).exclude(pk=user.pk).filter(
        Q(first_name__icontains=query)
        | Q(middle_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(email__icontains=query)
        | Q(username__icontains=query)
    )
    contacts = list(direct_matches.distinct())

    for user_contact in UserContact.objects.filter(
        owner=user,
        target_user__is_active=True,
    ).exclude(target_user_id=user.pk).select_related('target_user', 'linked_contact'):
        target = user_contact.target_user
        linked_contact = user_contact.linked_contact
        haystack = [
            _user_display_name(target),
            target.get_full_name(),
            target.email,
            target.username,
        ]
        if linked_contact:
            haystack.extend([
                linked_contact.display_name,
                linked_contact.first_name,
                linked_contact.middle_name,
                linked_contact.last_name,
                linked_contact.email,
                linked_contact.company,
            ])
        if any(query_normalized in (value or '').casefold() for value in haystack):
            contacts.append(target)

    unique_contacts = []
    seen_user_ids = set()
    for contact in contacts:
        if contact.pk in seen_user_ids:
            continue
        seen_user_ids.add(contact.pk)
        unique_contacts.append(contact)
    return unique_contacts


def _user_name_matches_query(user, query):
    if '@' in query:
        return []

    terms = [term.strip() for term in query.split() if term.strip()]
    if not terms:
        return []

    name_filters = Q()
    for term in terms:
        name_filters &= (
            Q(first_name__icontains=term)
            | Q(middle_name__icontains=term)
            | Q(last_name__icontains=term)
        )

    return list(
        get_user_model().objects.filter(is_active=True)
        .exclude(pk=user.pk)
        .filter(name_filters)
        .order_by('first_name', 'last_name', 'email')[:25]
    )


def _share_user_options(user):
    options = []
    user_contacts = list(UserContact.objects.filter(
        owner=user,
        target_user__is_active=True,
    ).exclude(target_user_id=user.pk).select_related(
        'target_user',
        'linked_contact',
        'linked_contact__company_record',
    ))
    user_contacts_by_target = {
        user_contact.target_user_id: user_contact
        for user_contact in user_contacts
    }
    users = list(
        get_user_model().objects.filter(is_active=True)
        .exclude(pk=user.pk)
        .order_by('first_name', 'middle_name', 'last_name', 'email', 'username')
    )
    user_options = []
    seen_user_ids = set()
    for contact in user_contacts:
        if contact.target_user_id in seen_user_ids:
            continue
        seen_user_ids.add(contact.target_user_id)
        user_options.append(contact.target_user)
    for target in users:
        if target.pk in seen_user_ids:
            continue
        seen_user_ids.add(target.pk)
        user_options.append(target)

    for target in user_options:
        user_contact = user_contacts_by_target.get(target.pk)
        linked_contact = user_contact.linked_contact if user_contact else None
        source_label = 'Kontakt' if user_contact else 'Użytkownik aplikacji'
        linked_contact_name = ''
        if linked_contact:
            linked_contact_name = ' '.join(
                part.strip()
                for part in [linked_contact.first_name, linked_contact.middle_name, linked_contact.last_name]
                if part and part.strip()
            )
        label = linked_contact_name or target.get_full_name() or target.email or target.username
        first_name = (linked_contact.first_name if linked_contact and linked_contact.first_name else target.first_name)
        middle_name = (linked_contact.middle_name if linked_contact and linked_contact.middle_name else target.middle_name)
        last_name = (linked_contact.last_name if linked_contact and linked_contact.last_name else target.last_name)
        search_label = ' '.join(
            part.strip()
            for part in [
                first_name,
                middle_name,
                last_name,
                label,
                target.get_full_name(),
                target.email,
                target.username,
                source_label,
                linked_contact.email if linked_contact else '',
                linked_contact.company if linked_contact else '',
            ]
            if part and part.strip()
        )
        options.append({
            'value': target.username,
            'label': label,
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'email': target.email,
            'ancore_label': target.username,
            'search_label': search_label,
            'source_label': source_label,
            'added_at': user_contact.created_at if user_contact else None,
            'avatar': account_avatar(target),
        })
    return options


def _tasks_next_url(request):
    fallback = reverse('tasks:tasks')
    next_url = (request.POST.get('next') or '').strip()
    if next_url == fallback or next_url.startswith(f'{fallback}?') or next_url.startswith('/tasks/'):
        return next_url
    return fallback


def _resolve_share_target(user, query):
    query = (query or '').strip()
    if not query:
        return None, 'Wpisz ID Ancore.'

    user_model = get_user_model()
    candidates = user_model.objects.filter(is_active=True).exclude(pk=user.pk)
    exact_filters = Q(username__iexact=query) | Q(username__iexact=normalize_public_username(query))

    exact_user = candidates.filter(exact_filters).first()
    if exact_user:
        return exact_user, ''

    return None, 'Nie znaleziono aktywnego użytkownika po ID Ancore.'


def _share_query_from_request(request):
    ancore_id = (request.POST.get('member_query') or '').strip()
    if ancore_id:
        return ancore_id
    return ' '.join(
        value for value in [
            (request.POST.get('member_first_name') or '').strip(),
            (request.POST.get('member_last_name') or '').strip(),
        ]
        if value
    )


def _split_share_queries(value):
    return [
        query.strip()
        for query in (value or '').replace(',', '\n').replace(':', '\n').splitlines()
        if query.strip() and query.strip() != '@'
    ]


def _share_queries_from_request(request):
    queries = []
    for value in request.POST.getlist('member_queries'):
        queries.extend(_split_share_queries(value))
    queries.extend(_split_share_queries(_share_query_from_request(request)))

    unique_queries = []
    seen_queries = set()
    for query in queries:
        query_key = query.casefold()
        if query_key in seen_queries:
            continue
        seen_queries.add(query_key)
        unique_queries.append(query)
    return unique_queries


def _share_task_directory_object(request, obj):
    queries = _share_queries_from_request(request)
    if not queries:
        messages.error(request, 'Wpisz ID Ancore.')
        return

    permission = _share_permission_from_request(request)
    content_type = ContentType.objects.get_for_model(obj.__class__)

    for query in queries:
        target_user, error = _resolve_share_target(request.user, query)
        if error:
            messages.error(request, error)
            continue

        if target_user == _task_share_owner(obj):
            messages.info(request, 'Ta osoba jest już właścicielem.')
            continue

        share = SharedItem.objects.filter(
            content_type=content_type,
            object_id=obj.pk,
            shared_by=request.user,
            shared_with=target_user,
        ).first()
        if share:
            if share.permission != permission:
                share.permission = permission
                share.save(update_fields=['permission'])
                messages.success(request, f'Zmieniono poziom dostępu: {_user_display_name(target_user)}.')
            else:
                messages.info(request, f'{_user_display_name(target_user)} już jest na liście.')
            continue

        SharedItem.objects.create(
            content_type=content_type,
            object_id=obj.pk,
            shared_by=request.user,
            shared_with=target_user,
            permission=permission,
        )
        messages.success(request, f'Dodano: {_user_display_name(target_user)}.')


def _unshare_task_directory_object(request, obj):
    target_user = get_user_model().objects.filter(pk=request.POST.get('member_id')).first()
    if not target_user:
        messages.error(request, 'Nie znaleziono użytkownika.')
        return

    deleted_count, _ = SharedItem.objects.filter(
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=obj.pk,
        shared_by=request.user,
        shared_with=target_user,
    ).delete()

    if deleted_count:
        messages.success(request, f'Przestano udostępniać: {_user_display_name(target_user)}.')
    else:
        messages.info(request, 'Ta osoba nie ma już dostępu z tego miejsca.')


def _unshare_task_directory_object_for_current_user(request, model, object_id):
    share = get_object_or_404(
        SharedItem,
        content_type=ContentType.objects.get_for_model(model),
        object_id=object_id,
        shared_with=request.user,
    )
    share.delete()
    messages.success(request, 'Przestano udostępniać to dla Ciebie.')


def _update_share_task_directory_permission(request, obj, add_message=True):
    def add_flash(kind, message):
        if add_message:
            getattr(messages, kind)(request, message)

    target_user = get_user_model().objects.filter(pk=request.POST.get('member_id')).first()
    if not target_user:
        message = 'Nie znaleziono użytkownika.'
        add_flash('error', message)
        return {'status': 'error', 'message': message, 'http_status': 404}

    permission = _share_permission_from_request(request)
    share = SharedItem.objects.filter(
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=obj.pk,
        shared_by=request.user,
        shared_with=target_user,
    ).first()

    if not share:
        message = 'Ta osoba nie ma dostępu z tego miejsca.'
        add_flash('info', message)
        return {'status': 'error', 'message': message, 'http_status': 404}

    if share.permission == permission:
        message = f'{_user_display_name(target_user)} już ma ten poziom dostępu.'
        add_flash('info', message)
        return {
            'status': 'success',
            'changed': False,
            'message': message,
            'permission': permission,
            'permission_label': _share_permission_label(permission),
        }

    share.permission = permission
    share.save(update_fields=['permission'])
    message = f'Zmieniono poziom dostępu: {_user_display_name(target_user)}.'
    add_flash('success', message)
    return {
        'status': 'success',
        'changed': True,
        'message': message,
        'permission': permission,
        'permission_label': _share_permission_label(permission),
    }


def _share_permission_result_response(result):
    payload = {key: value for key, value in result.items() if key != 'http_status'}
    return JsonResponse(payload, status=result.get('http_status', 200))


def _posted_ids(request, plural_name, singular_name):
    ids = request.POST.getlist(plural_name)
    if not ids:
        ids = [request.POST.get(singular_name)]
    return [item for item in ids if item]


def _tasks_navigation_context(user, active_section=None, active_view=None, workplace=None):
    tasks_qs = _filter_workplace(
        Task.objects.filter(user=user, parent__isnull=True),
        workplace,
    ).select_related('section', 'section__project', 'assignee', 'company', 'contact').prefetch_related('tags').annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        tags_total=Count('tags', distinct=True),
        attachments_total=Count('attachments', distinct=True),
    ).order_by('is_closed_sort', 'task_id')

    active_project = _project_for_user(user, active_section.project_id, workplace=workplace) if active_section else None
    if active_section:
        active_section = next((section for section in active_project.sections.all() if section.id == active_section.id), active_section)

    if active_view is None:
        active_view = 'section' if active_section else 'projects'

    navigation_projects = _navigation_projects_for_user(user, active_project=active_project, workplace=workplace)
    _decorate_project_directory_metrics(navigation_projects)
    _decorate_directory_members(navigation_projects, current_user=user)

    can_create_issue = _user_can_create_issue(
        user,
        active_project=active_project,
        active_section=active_section,
        workplace=workplace,
    )

    return {
        'projects': navigation_projects,
        'navigation_projects': navigation_projects,
        'project_options': navigation_projects,
        'active_project': active_project,
        'active_section': active_section,
        'active_view': active_view,
        'tasks': tasks_qs,
        'total_task_count': tasks_qs.count(),
        'total_group_count': len(_sections_for_projects(navigation_projects)),
        'tags': _filter_workplace(TaskTag.objects.filter(user=user), workplace).annotate(
            total_tasks=Count('tasks', filter=Q(tasks__user=user, tasks__workplace=workplace, tasks__parent__isnull=True))
        ),
        'total_tag_count': _filter_workplace(TaskTag.objects.filter(user=user), workplace).count(),
        'shared_task_count': 0,
        'shared_group_count': 0,
        'shared_project_count': 0,
        'can_create_issue': can_create_issue,
    }


def _set_task_status(task, status):
    valid_statuses = {choice for choice, _label in Task.STATUS_CHOICES}
    if status not in valid_statuses:
        return False
    task.status = status
    task.save()
    return True


def _record_task_activity(task, actor, action, message='', kind='system', metadata=None):
    return TaskActivity.objects.create(
        task=task,
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        kind=kind,
        action=action,
        message=message,
        metadata=metadata or {},
    )


def _task_activity_snapshot(task):
    section = task.section
    project = section.project if section else None
    return {
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'task_type': task.task_type,
        'contact_channel': task.contact_channel,
        'section_id': task.section_id,
        'section_label': section.title if section else '',
        'project_id': project.id if project else None,
        'project_label': project.name if project else '',
        'parent_id': task.parent_id,
        'assignee_id': task.assignee_id,
        'assignee_label': _user_display_name(task.assignee) if task.assignee_id else '',
        'company_id': task.company_id,
        'company_label': task.company.name if task.company_id else '',
        'contact_id': task.contact_id,
        'contact_label': task.contact.display_name if task.contact_id else '',
        'due_at': task.due_at,
        'reminder_at': task.reminder_at,
        'estimated_minutes': task.estimated_minutes,
        'is_billable': task.is_billable,
        'blocked_reason': task.blocked_reason,
        'time_spent_hours': task.time_spent_hours,
        'time_spent_minutes': task.time_spent_minutes,
        'completion_date': task.completion_date,
        'tags': set(task.tags.values_list('id', flat=True)),
        'tag_labels': list(task.tags.order_by('name').values_list('name', flat=True)),
    }


def _task_change_activities(task, before):
    status_labels = dict(Task.STATUS_CHOICES)
    priority_labels = dict(Task.PRIORITY_CHOICES)
    task_type_labels = dict(Task.TASK_TYPE_CHOICES)
    contact_channel_labels = dict(Task.CONTACT_CHANNEL_CHOICES)
    changed_fields = []
    detailed_changes = []

    def normalize_change_value(value):
        if hasattr(value, 'tzinfo'):
            return task._activity_datetime(value)
        if value in (None, ''):
            return '—'
        return str(value)

    def add_change(field_label, from_label, to_label):
        changed_fields.append(field_label)
        detailed_changes.append({
            'field': field_label,
            'from_label': normalize_change_value(from_label),
            'to_label': normalize_change_value(to_label),
        })

    if before['status'] != task.status:
        add_change('status', status_labels.get(before['status'], before['status']), task.get_status_display())
    if before['priority'] != task.priority:
        add_change('priorytet', priority_labels.get(before['priority'], before['priority']), task.get_priority_display())
    if before['task_type'] != task.task_type:
        add_change('typ zadania', task_type_labels.get(before['task_type'], before['task_type']), task.get_task_type_display())
    if before['contact_channel'] != task.contact_channel:
        add_change('kanał kontaktu', contact_channel_labels.get(before['contact_channel'], before['contact_channel']), task.get_contact_channel_display())
    if before['title'] != task.title:
        add_change('tytuł', before['title'], task.title)
    if before['description'] != task.description:
        add_change('opis', before['description'], task.description)
    if before['project_id'] != (task.section.project_id if task.section_id else None):
        add_change('projekt', before['project_label'], task.section.project.name if task.section_id else '')
    if before['section_id'] != task.section_id:
        add_change('grupa', before['section_label'], task.section.title if task.section_id else '')
    if before['parent_id'] != task.parent_id:
        add_change('zadanie nadrzędne', before['parent_id'], task.parent_id)
    if before['assignee_id'] != task.assignee_id:
        add_change('przypisane do', before['assignee_label'], _user_display_name(task.assignee) if task.assignee_id else '')
    if before['company_id'] != task.company_id:
        add_change('firma', before['company_label'], task.company.name if task.company_id else '')
    if before['contact_id'] != task.contact_id:
        add_change('kontakt', before['contact_label'], task.contact.display_name if task.contact_id else '')
    if before['due_at'] != task.due_at:
        add_change('termin wykonania', before['due_at'], task.due_at)
    if before['reminder_at'] != task.reminder_at:
        add_change('przypomnienie', before['reminder_at'], task.reminder_at)
    if before['estimated_minutes'] != task.estimated_minutes:
        add_change('szacowany czas', before['estimated_minutes'], task.estimated_minutes)
    if before['is_billable'] != task.is_billable:
        add_change('fakturowalne', 'Tak' if before['is_billable'] else 'Nie', 'Tak' if task.is_billable else 'Nie')
    if before['blocked_reason'] != task.blocked_reason:
        add_change('powód blokady', before['blocked_reason'], task.blocked_reason)
    if (
        before['time_spent_hours'] != task.time_spent_hours
        or before['time_spent_minutes'] != task.time_spent_minutes
    ):
        previous_time = f"{before['time_spent_hours'] or 0:02d}:{before['time_spent_minutes'] or 0:02d}"
        add_change('czas pracy', previous_time, task._activity_time_spent())
    if before['completion_date'] != task.completion_date:
        add_change('zamknięto', before['completion_date'], task._activity_datetime(task.completion_date))
    if before['tags'] != set(task.tags.values_list('id', flat=True)):
        add_change('tagi', ', '.join(before['tag_labels']), ', '.join(task.tags.order_by('name').values_list('name', flat=True)))

    changed_fields = list(dict.fromkeys(changed_fields))
    if changed_fields:
        return [{
            'action': 'updated',
            'message': 'zaktualizował zadanie',
            'metadata': {
                'fields': changed_fields,
                'changes': detailed_changes,
            },
        }]
    return []


def _is_ajax_request(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('autosave') == '1'


def _form_error_messages(form):
    messages_list = []
    for field_name, errors in form.errors.items():
        field = form.fields.get(field_name)
        label = field.label if field else 'Formularz'
        for error in errors:
            messages_list.append(f'{label}: {error}')
    return messages_list


def _task_detail_payload(task):
    return {
        'title': task.title,
        'status': task.status,
        'status_label': task.get_status_display(),
        'priority': task.priority,
        'priority_label': task.get_priority_display(),
        'due_urgency': task.due_urgency,
        'completion_date': task._activity_datetime(task.completion_date) if task.completion_date else '',
        'time_spent_label': task.time_spent_label,
        'has_time_spent': task.has_time_spent,
    }


def _task_activity_html(activities):
    ordered_activities = sorted(activities, key=lambda activity: activity.id or 0, reverse=True)
    return ''.join(
        render_to_string('tasks/includes/task_activity_item.html', {'item': activity})
        for activity in ordered_activities
    )


def _redirect_to_task_detail(task, user):
    detail_route = 'tasks:view-subtask' if task.parent_id else 'tasks:view-task'
    return redirect(detail_route, task_id=task.task_id)


@login_required
def tasks(request):
    return _tasks_page(request)


@login_required
def task_group(request, section_id):
    active_section = get_object_or_404(
        _filter_workplace(
            TaskSection.objects.select_related('project', 'project__user'),
            _active_workplace(request),
            field_name='project__workplace',
        ),
        id=section_id,
    )
    if not _user_can_access_section(request.user, active_section):
        raise PermissionDenied
    return _tasks_page(request, active_section=active_section)


def _tasks_page(request, active_section=None):
    workplace = _active_workplace(request)
    project_form = TaskProjectForm(user=request.user, workplace=workplace)
    section_form = TaskSectionForm(user=request.user)
    tag_form = TaskTagForm(user=request.user, workplace=workplace)
    all_tasks_view = request.GET.get('view') == 'all-tasks' and not active_section
    my_tasks_view = request.GET.get('view') == 'my-tasks' and not active_section
    all_groups_view = request.GET.get('view') == 'all-groups' and not active_section
    tags_view = request.GET.get('view') == 'tags' and not active_section
    shared_tasks_view = False
    shared_groups_view = False
    shared_projects_view = False
    active_project_id = request.POST.get('project_id') if request.method == 'POST' else request.GET.get('project')
    if (
        all_tasks_view
        or my_tasks_view
        or all_groups_view
        or tags_view
        or shared_tasks_view
        or shared_groups_view
        or shared_projects_view
    ):
        active_project_id = None
    if active_section:
        active_project_id = active_section.project_id
    active_project_for_form = _task_creation_project_for_user(request.user, active_project_id, workplace=workplace)
    project_option_ids_for_form = _navigation_project_ids_for_user(
        request.user,
        active_project=active_project_for_form,
        workplace=workplace,
    )
    task_modal_sections = _editable_sections_queryset(request.user, workplace)
    if active_project_for_form:
        task_modal_sections = task_modal_sections.filter(project=active_project_for_form)
    else:
        task_modal_sections = task_modal_sections.filter(project_id__in=project_option_ids_for_form)
    task_modal_form = TaskModalForm(
        user=request.user,
        workplace=workplace,
        project=active_project_for_form,
        section=active_section,
        sections_queryset=task_modal_sections,
    )
    project_modal_open = False
    project_rename_modal_open = False
    project_rename_form = TaskProjectRenameForm(user=request.user, workplace=workplace)
    project_rename_project_id = ''
    section_create_modal_open = False
    section_create_project_id = active_project_id or ''
    section_rename_modal_open = False
    section_rename_form = TaskSectionRenameForm(user=request.user)
    section_rename_section_id = ''
    task_modal_open = False
    tag_modal_open = False
    tag_edit_mode = False
    tag_edit_tag_id = ''

    if request.method == 'POST':
        action = request.POST.get('action')
        is_ajax = _is_ajax_request(request)

        if action == 'create_project':
            project_form = TaskProjectForm(request.POST, user=request.user, workplace=workplace)
            if project_form.is_valid():
                with transaction.atomic():
                    project = project_form.save(commit=False)
                    project.user = request.user
                    project.workplace = workplace
                    project.save()
                    section_title = project_form.cleaned_data.get('section_title') or 'Nowa Grupa'
                    TaskSection.objects.create(
                        project=project,
                        title=section_title,
                        kind='custom',
                        order=0,
                    )
                messages.success(request, 'Projekt dodany.')
                return redirect(f"{reverse('tasks:tasks')}?project={project.id}")
            project_modal_open = True
            messages.error(request, 'Nie udało się dodać projektu.')

        if action == 'delete_project':
            project_ids = _posted_ids(request, 'project_ids', 'project_id')
            projects_to_delete = _filter_workplace(TaskProject.objects.filter(id__in=project_ids, user=request.user), workplace)
            if not projects_to_delete.exists():
                get_object_or_404(_filter_workplace(TaskProject.objects.filter(user=request.user), workplace), id=request.POST.get('project_id'))
            project_count = projects_to_delete.count()
            task_count = _filter_workplace(Task.objects.filter(section__project__in=projects_to_delete, user=request.user), workplace).count()
            with transaction.atomic():
                projects_to_delete.delete()
                Task._renumber_user_tasks(request.user, workplace)
            if project_count == 1 and task_count:
                messages.success(request, 'Projekt usunięty razem z zadaniami.')
            elif project_count == 1:
                messages.success(request, 'Projekt usunięty.')
            elif task_count:
                messages.success(request, f'Usunięto {project_count} projekty razem z zadaniami.')
            else:
                messages.success(request, f'Usunięto {project_count} projekty.')
            return redirect('tasks:tasks')

        if action in ('edit_project', 'rename_project'):
            project = get_object_or_404(_filter_workplace(TaskProject.objects.filter(user=request.user), workplace), id=request.POST.get('project_id'))
            project_rename_form = TaskProjectRenameForm(request.POST, instance=project, user=request.user, workplace=workplace)
            if project_rename_form.is_valid():
                project_rename_form.save()
                messages.success(request, 'Projekt zaktualizowany.')
                return redirect('tasks:tasks')
            project_rename_modal_open = True
            project_rename_project_id = project.id
            active_project_for_form = project
            messages.error(request, 'Nie udało się zaktualizować projektu.')

        if action in ('add_project_note', 'update_project_notes'):
            project = get_object_or_404(_filter_workplace(TaskProject.objects.filter(user=request.user), workplace), id=request.POST.get('project_id'))
            message = (request.POST.get('message') or request.POST.get('description') or '').strip()
            if message:
                TaskProjectNote.objects.create(project=project, author=request.user, message=message)
                messages.success(request, 'Notatka dodana.')
            else:
                messages.error(request, 'Wpisz treść notatki.')
            return redirect(_tasks_next_url(request))

        if action == 'edit_project_note':
            note_queryset = _filter_workplace(
                TaskProjectNote.objects.filter(author=request.user, project__user=request.user),
                workplace,
                field_name='project__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), project_id=request.POST.get('project_id'))
            message = (request.POST.get('message') or '').strip()
            if message:
                note.message = message
                note.save(update_fields=['message', 'updated_at'])
                messages.success(request, 'Notatka zaktualizowana.')
            else:
                messages.error(request, 'Wpisz treść notatki.')
            return redirect(_tasks_next_url(request))

        if action == 'delete_project_note':
            note_queryset = _filter_workplace(
                TaskProjectNote.objects.filter(author=request.user, project__user=request.user),
                workplace,
                field_name='project__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), project_id=request.POST.get('project_id'))
            note.delete()
            messages.success(request, 'Notatka usunięta.')
            return redirect(_tasks_next_url(request))

        if action in ('add_section_note', 'update_section_notes'):
            section = get_object_or_404(
                _filter_workplace(
                    TaskSection.objects.filter(project__user=request.user),
                    workplace,
                    field_name='project__workplace',
                ),
                id=request.POST.get('section_id'),
            )
            message = (request.POST.get('message') or request.POST.get('description') or '').strip()
            if message:
                TaskSectionNote.objects.create(section=section, author=request.user, message=message)
                messages.success(request, 'Notatka dodana.')
            else:
                messages.error(request, 'Wpisz treść notatki.')
            return redirect(_tasks_next_url(request))

        if action == 'edit_section_note':
            note_queryset = _filter_workplace(
                TaskSectionNote.objects.filter(author=request.user, section__project__user=request.user),
                workplace,
                field_name='section__project__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), section_id=request.POST.get('section_id'))
            message = (request.POST.get('message') or '').strip()
            if message:
                note.message = message
                note.save(update_fields=['message', 'updated_at'])
                messages.success(request, 'Notatka zaktualizowana.')
            else:
                messages.error(request, 'Wpisz treść notatki.')
            return redirect(_tasks_next_url(request))

        if action == 'delete_section_note':
            note_queryset = _filter_workplace(
                TaskSectionNote.objects.filter(author=request.user, section__project__user=request.user),
                workplace,
                field_name='section__project__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), section_id=request.POST.get('section_id'))
            note.delete()
            messages.success(request, 'Notatka usunięta.')
            return redirect(_tasks_next_url(request))

        if action == 'create_section':
            project = get_object_or_404(_filter_workplace(TaskProject.objects.filter(user=request.user), workplace), id=request.POST.get('project_id'))
            section_form = TaskSectionForm(request.POST, user=request.user)
            if section_form.is_valid():
                section = section_form.save(commit=False)
                section.project = project
                section.order = project.sections.count()
                section.save()
                messages.success(request, 'Grupa dodana.')
                return redirect('tasks:task_group', section_id=section.id)
            section_create_modal_open = True
            section_create_project_id = project.id
            messages.error(request, 'Nie udało się dodać grupy.')

        if action == 'create_tag':
            tag_form = TaskTagForm(request.POST, user=request.user, workplace=workplace)
            if tag_form.is_valid():
                tag_name = tag_form.cleaned_data['name']
                if _filter_workplace(TaskTag.objects.filter(user=request.user, name__iexact=tag_name), workplace).exists():
                    tag_form.add_error('name', 'Taki tag już istnieje.')
                else:
                    tag = tag_form.save(commit=False)
                    tag.user = request.user
                    tag.workplace = workplace
                    tag.save()
                    tag_form.save_m2m()
                    messages.success(request, 'Tag dodany.')
                    return redirect(f"{reverse('tasks:tasks')}?view=tags")
            tag_modal_open = True
            messages.error(request, 'Nie udało się dodać tagu.')

        if action == 'edit_tag':
            tag = get_object_or_404(_filter_workplace(TaskTag.objects.filter(user=request.user), workplace), id=request.POST.get('tag_id'))
            tag_form = TaskTagForm(request.POST, instance=tag, user=request.user, workplace=workplace)
            if tag_form.is_valid():
                tag_name = tag_form.cleaned_data['name']
                if _filter_workplace(TaskTag.objects.filter(user=request.user, name__iexact=tag_name), workplace).exclude(pk=tag.pk).exists():
                    tag_form.add_error('name', 'Taki tag już istnieje.')
                else:
                    tag_form.save()
                    messages.success(request, 'Tag zaktualizowany.')
                    return redirect(f"{reverse('tasks:tasks')}?view=tags")
            tag_modal_open = True
            tag_edit_mode = True
            tag_edit_tag_id = tag.id
            messages.error(request, 'Nie udało się zaktualizować tagu.')

        if action in ('add_tag_note', 'update_tag_notes'):
            tag = get_object_or_404(
                _filter_workplace(TaskTag.objects.filter(user=request.user), workplace),
                id=request.POST.get('tag_id'),
            )
            message = (request.POST.get('message') or request.POST.get('description') or '').strip()
            if message:
                TaskTagNote.objects.create(tag=tag, author=request.user, message=message)
                messages.success(request, 'Notatka dodana.')
            else:
                messages.error(request, 'Wpisz treść notatki.')
            return redirect(_tasks_next_url(request))

        if action == 'edit_tag_note':
            note_queryset = _filter_workplace(
                TaskTagNote.objects.filter(author=request.user, tag__user=request.user),
                workplace,
                field_name='tag__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), tag_id=request.POST.get('tag_id'))
            message = (request.POST.get('message') or '').strip()
            if message:
                note.message = message
                note.save(update_fields=['message', 'updated_at'])
                messages.success(request, 'Notatka zaktualizowana.')
            else:
                messages.error(request, 'Wpisz treść notatki.')
            return redirect(_tasks_next_url(request))

        if action == 'delete_tag_note':
            note_queryset = _filter_workplace(
                TaskTagNote.objects.filter(author=request.user, tag__user=request.user),
                workplace,
                field_name='tag__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), tag_id=request.POST.get('tag_id'))
            note.delete()
            messages.success(request, 'Notatka usunięta.')
            return redirect(_tasks_next_url(request))

        if action == 'delete_tag':
            tag_ids = _posted_ids(request, 'tag_ids', 'tag_id')
            tags_to_delete = _filter_workplace(TaskTag.objects.filter(id__in=tag_ids, user=request.user), workplace)
            if not tags_to_delete.exists():
                get_object_or_404(_filter_workplace(TaskTag.objects.filter(user=request.user), workplace), id=request.POST.get('tag_id'))
            tag_count = tags_to_delete.count()
            tags_to_delete.delete()
            if tag_count == 1:
                messages.success(request, 'Tag usunięty.')
            else:
                messages.success(request, f'Usunięto tagi ({tag_count}).')
            return redirect(f"{reverse('tasks:tasks')}?view=tags")

        if action in ('edit_section', 'rename_section'):
            section = get_object_or_404(
                _filter_workplace(TaskSection.objects.filter(project__user=request.user), workplace, field_name='project__workplace'),
                id=request.POST.get('section_id'),
            )
            section_rename_form = TaskSectionRenameForm(request.POST, instance=section, user=request.user)
            if section_rename_form.is_valid():
                section_rename_form.save()
                messages.success(request, 'Grupa zaktualizowana.')
                if all_groups_view:
                    return redirect(f"{reverse('tasks:tasks')}?view=all-groups")
                return redirect('tasks:task_group', section_id=section.id)
            section_rename_modal_open = True
            section_rename_section_id = section.id
            active_section = section
            active_project_for_form = section.project
            messages.error(request, 'Nie udało się zaktualizować grupy.')

        if action == 'delete_section':
            section_ids = _posted_ids(request, 'section_ids', 'section_id')
            sections_to_delete = _filter_workplace(
                TaskSection.objects.filter(id__in=section_ids, project__user=request.user),
                workplace,
                field_name='project__workplace',
            )
            if not sections_to_delete.exists():
                get_object_or_404(
                    _filter_workplace(TaskSection.objects.filter(project__user=request.user), workplace, field_name='project__workplace'),
                    id=request.POST.get('section_id'),
                )
            section_count = sections_to_delete.count()
            project_id = sections_to_delete.values_list('project_id', flat=True).first()
            task_count = _filter_workplace(Task.objects.filter(section__in=sections_to_delete, user=request.user), workplace).count()
            with transaction.atomic():
                sections_to_delete.delete()
                Task._renumber_user_tasks(request.user, workplace)
            if section_count == 1 and task_count:
                messages.success(request, 'Grupa usunięta razem z zadaniami.')
            elif section_count == 1:
                messages.success(request, 'Grupa usunięta.')
            elif task_count:
                messages.success(request, f'Usunięto {section_count} grupy razem z zadaniami.')
            else:
                messages.success(request, f'Usunięto {section_count} grupy.')
            if all_groups_view:
                return redirect(f"{reverse('tasks:tasks')}?view=all-groups")
            return redirect(f"{reverse('tasks:tasks')}?project={project_id}")

        if action == 'create_task':
            section = get_object_or_404(
                _filter_workplace(
                    TaskSection.objects.select_related('project', 'project__user'),
                    workplace,
                    field_name='project__workplace',
                ),
                id=request.POST.get('section_id'),
            )
            if not _user_can_create_task_in_section(request.user, section):
                raise PermissionDenied
            form = QuickTaskForm(request.POST)
            if form.is_valid():
                task = form.save(commit=False)
                task.user = section.project.user
                task.section = section
                task.workplace = workplace
                task.save()
                messages.success(request, 'Zadanie dodane.')
                return redirect('tasks:task_group', section_id=section.id)
            messages.error(request, 'Nie udało się dodać zadania.')

        if action == 'create_task_modal':
            project = None
            project_id = request.POST.get('project_id')
            if project_id:
                project = _task_creation_project_for_user(request.user, project_id, workplace=workplace)
                if not project:
                    raise PermissionDenied
            task_modal_sections = _editable_sections_queryset(request.user, workplace)
            if project:
                task_modal_sections = task_modal_sections.filter(project=project)
            task_modal_form = TaskModalForm(
                request.POST,
                user=request.user,
                workplace=workplace,
                project=project,
                section=active_section,
                sections_queryset=task_modal_sections,
            )
            if task_modal_form.is_valid():
                task = task_modal_form.save(commit=False)
                if not _user_can_create_task_in_section(request.user, task.section):
                    raise PermissionDenied
                task.user = task.section.project.user
                task.workplace = workplace
                task.save()
                task_modal_form.save_m2m()
                task.activities.filter(action='created').update(metadata={'title': task.title})
                messages.success(request, 'Zadanie dodane.')
                return redirect('tasks:task_group', section_id=task.section_id)
            task_modal_open = True
            messages.error(request, 'Nie udało się dodać zadania.')

    tasks_qs = _filter_workplace(
        Task.objects.filter(user=request.user, parent__isnull=True),
        workplace,
    ).select_related('section', 'section__project', 'assignee', 'company', 'contact').prefetch_related('tags').annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        tags_total=Count('tags', distinct=True),
        attachments_total=Count('attachments', distinct=True),
    ).order_by('is_closed_sort', 'task_id')

    active_project_id = str(active_section.project_id) if active_section else active_project_id
    active_project = _project_for_user(request.user, active_project_id, workplace=workplace) if active_project_id else None
    if active_section and active_project:
        active_section = next((section for section in active_project.sections.all() if section.id == active_section.id), active_section)

    if active_section:
        active_view = 'section'
    elif active_project:
        active_view = 'project'
    elif all_groups_view:
        active_view = 'all_groups'
    elif tags_view:
        active_view = 'tags'
    elif my_tasks_view:
        active_view = 'my_tasks'
    elif all_tasks_view:
        active_view = 'all_tasks'
    else:
        active_view = 'projects'

    project_window = _project_window_for_request(request) if active_view == 'projects' else {
        'projects': [],
        'query': '',
        'priority': '',
        'status': '',
        'stage': '',
        'health': '',
        'company': '',
        'responsible': '',
        'sort': PROJECT_DEFAULT_SORT,
        'sort_param': '',
        'sort_label': PROJECT_SORT_OPTION_MAP[PROJECT_DEFAULT_SORT]['label'],
        'sort_direction': PROJECT_SORT_OPTION_MAP[PROJECT_DEFAULT_SORT]['direction'],
        'filters': _empty_project_filter_options(),
        'page': 1,
        'total_pages': 1,
        'total_projects': 0,
        'page_size': PROJECT_DEFAULT_PAGE_SIZE,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'page_items': [],
        'has_previous': False,
        'has_next': False,
        'previous_url': '',
        'next_url': '',
        'summary': '',
    }
    group_window = _group_window_for_request(request) if active_view == 'all_groups' else {
        'sections': [],
        'query': '',
        'priority': '',
        'status': '',
        'kind': '',
        'project_filter': '',
        'owner': '',
        'sort': GROUP_DEFAULT_SORT,
        'sort_param': '',
        'sort_label': GROUP_SORT_OPTION_MAP[GROUP_DEFAULT_SORT]['label'],
        'sort_direction': GROUP_SORT_OPTION_MAP[GROUP_DEFAULT_SORT]['direction'],
        'filters': _empty_group_filter_options(),
        'page': 1,
        'total_pages': 1,
        'total_groups': 0,
        'page_size': PROJECT_DEFAULT_PAGE_SIZE,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'page_items': [],
        'has_previous': False,
        'has_next': False,
        'previous_url': '',
        'next_url': '',
        'summary': '',
    }
    project_section_window = _project_section_window_for_request(request, active_project) if active_view == 'project' and active_project else {
        'sections': [],
        'query': '',
        'priority': '',
        'page': 1,
        'total_pages': 1,
        'total_groups': 0,
        'page_size': PROJECT_DEFAULT_PAGE_SIZE,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'page_items': [],
        'has_previous': False,
        'has_next': False,
        'previous_url': '',
        'next_url': '',
        'summary': '',
    }
    tag_window = _tag_window_for_request(request) if active_view == 'tags' else {
        'tags': [],
        'query': '',
        'page': 1,
        'total_pages': 1,
        'total_tags': 0,
        'page_size': PROJECT_DEFAULT_PAGE_SIZE,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'page_items': [],
        'has_previous': False,
        'has_next': False,
        'previous_url': '',
        'next_url': '',
        'summary': '',
    }
    task_window = _task_window_for_request(request, tasks_qs) if active_view in ('all_tasks', 'my_tasks') else {
        'queryset': tasks_qs,
        'query': '',
        'priority': '',
        'status': '',
        'project_filter': '',
        'section': '',
        'assignee': '',
        'company': '',
        'task_type': '',
        'due': '',
        'sort': TASK_DEFAULT_SORT,
        'sort_param': '',
        'sort_label': TASK_SORT_OPTION_MAP[TASK_DEFAULT_SORT]['label'],
        'sort_direction': TASK_SORT_OPTION_MAP[TASK_DEFAULT_SORT]['direction'],
        'filters': {
            'statuses': _choice_options(Task.STATUS_CHOICES),
            'priorities': _choice_options(Task.PRIORITY_CHOICES),
            'types': _choice_options(Task.TASK_TYPE_CHOICES),
            'due': TASK_DUE_FILTER_OPTIONS,
            'projects': [],
            'sections': [],
            'assignees': [],
            'companies': [],
        },
        'total_tasks': 0,
        'has_active_filters': False,
    }
    projects = project_window['projects']
    navigation_projects = _navigation_projects_for_user(request.user, active_project=active_project, workplace=workplace)
    if active_project:
        navigation_active_project = next((project for project in navigation_projects if project.id == active_project.id), None)
        if navigation_active_project:
            active_project = navigation_active_project
            if active_section:
                active_section = next((section for section in active_project.sections.all() if section.id == active_section.id), active_section)
    if active_project_for_form and (not active_project or active_project_for_form.id != active_project.id):
        project_options = _navigation_projects_for_user(
            request.user,
            active_project=active_project_for_form,
            workplace=workplace,
        )
    else:
        project_options = navigation_projects
    _decorate_project_directory_metrics(navigation_projects)
    _decorate_directory_members(navigation_projects, current_user=request.user)
    if project_options is not navigation_projects:
        _decorate_project_directory_metrics(project_options)
        _decorate_directory_members(project_options, current_user=request.user)

    orphan_tasks = []
    orphan_status_groups = []
    all_status_groups = []
    if active_section:
        active_section.status_groups = _status_groups_for_tasks(
            tasks_qs.filter(section_id=active_section.id),
            request.user,
            request=request,
            base_url=request.path,
            paginate=True,
        )
    elif all_tasks_view or my_tasks_view:
        all_status_groups = _status_groups_for_tasks(
            task_window['queryset'],
            request.user,
            request=request,
            base_url=request.path,
            paginate=True,
        )
    all_sections = group_window['sections'] if active_view == 'all_groups' else []
    shared_projects = []
    shared_sections = []
    shared_tasks = []
    shared_status_groups = []
    _decorate_share_links(request, [*projects, *all_sections])
    tags = tag_window['tags'] if active_view == 'tags' else TaskTag.objects.none()
    total_task_count = task_window['total_tasks'] if (all_tasks_view or my_tasks_view) else 0
    can_create_issue = _user_can_create_issue(
        request.user,
        active_project=active_project,
        active_section=active_section,
        workplace=workplace,
    )
    project_sections = project_section_window['sections'] if active_view == 'project' else []

    context = {
        'projects': projects,
        'navigation_projects': navigation_projects,
        'project_options': project_options,
        'issue_picker_options': _task_modal_picker_options(project_options),
        'project_window': project_window,
        'project_query': project_window['query'],
        'project_priority_filter': project_window['priority'],
        'project_status_filter': project_window['status'],
        'project_stage_filter': project_window['stage'],
        'project_health_filter': project_window['health'],
        'project_company_filter': project_window['company'],
        'project_responsible_filter': project_window['responsible'],
        'project_filter_options': project_window['filters'],
        'project_sort_options': PROJECT_SORT_OPTIONS,
        'project_sort': project_window['sort'],
        'project_sort_param': project_window['sort_param'],
        'project_sort_label': project_window['sort_label'],
        'project_sort_direction': project_window['sort_direction'],
        'project_default_sort': PROJECT_DEFAULT_SORT,
        'group_window': group_window,
        'group_query': group_window['query'],
        'group_priority_filter': group_window['priority'],
        'group_status_filter': group_window['status'],
        'group_kind_filter': group_window['kind'],
        'group_project_filter': group_window['project_filter'],
        'group_owner_filter': group_window['owner'],
        'group_filter_options': group_window['filters'],
        'group_sort_options': GROUP_SORT_OPTIONS,
        'group_sort': group_window['sort'],
        'group_sort_param': group_window['sort_param'],
        'group_sort_label': group_window['sort_label'],
        'group_sort_direction': group_window['sort_direction'],
        'group_default_sort': GROUP_DEFAULT_SORT,
        'project_section_window': project_section_window,
        'project_sections': project_sections,
        'project_section_query': project_section_window['query'],
        'project_section_priority_filter': project_section_window['priority'],
        'tag_window': tag_window,
        'tag_query': tag_window['query'],
        'task_window': task_window,
        'task_query': task_window['query'],
        'task_priority_filter': task_window['priority'],
        'task_status_filter': task_window['status'],
        'task_project_filter': task_window['project_filter'],
        'task_section_filter': task_window['section'],
        'task_assignee_filter': task_window['assignee'],
        'task_company_filter': task_window['company'],
        'task_type_filter': task_window['task_type'],
        'task_due_filter': task_window['due'],
        'task_filter_options': task_window['filters'],
        'task_sort_options': TASK_SORT_OPTIONS,
        'task_sort': task_window['sort'],
        'task_sort_param': task_window['sort_param'],
        'task_sort_label': task_window['sort_label'],
        'task_sort_direction': task_window['sort_direction'],
        'task_default_sort': TASK_DEFAULT_SORT,
        'task_has_active_filters': task_window['has_active_filters'],
        'active_project': active_project,
        'active_section': active_section,
        'active_view': active_view,
        'visible_sections': [active_section] if active_section else [],
        'orphan_tasks': orphan_tasks,
        'orphan_status_groups': orphan_status_groups,
        'all_status_groups': all_status_groups,
        'shared_status_groups': shared_status_groups,
        'all_sections': all_sections,
        'shared_projects': shared_projects,
        'shared_sections': shared_sections,
        'shared_tasks': shared_tasks,
        'tasks': tasks_qs,
        'total_task_count': total_task_count,
        'total_group_count': (
            group_window['total_groups']
            if active_view == 'all_groups'
            else project_section_window['total_groups']
            if active_view == 'project'
            else len(_sections_for_projects(navigation_projects))
        ),
        'tags': tags,
        'total_tag_count': tag_window['total_tags'],
        'shared_task_count': len(shared_tasks),
        'shared_group_count': len(shared_sections),
        'shared_project_count': len(shared_projects),
        'tasks_return_path': request.get_full_path(),
        'project_form': project_form,
        'project_rename_form': project_rename_form,
        'project_rename_project_id': project_rename_project_id,
        'section_form': section_form,
        'tag_form': tag_form,
        'section_create_modal_open': section_create_modal_open,
        'section_create_project_id': section_create_project_id,
        'section_create_uses_project_select': (
            all_groups_view
            or active_project is None
            or not getattr(active_project, 'can_manage', False)
        ),
        'section_rename_form': section_rename_form,
        'section_rename_section_id': section_rename_section_id,
        'section_rename_modal_open': section_rename_modal_open,
        'task_modal_form': task_modal_form,
        'quick_task_form': QuickTaskForm(),
        'project_modal_open': project_modal_open,
        'project_rename_modal_open': project_rename_modal_open,
        'task_modal_open': task_modal_open,
        'tag_modal_open': tag_modal_open,
        'tag_edit_mode': tag_edit_mode,
        'tag_edit_tag_id': tag_edit_tag_id,
        'can_create_issue': can_create_issue,
    }
    return render(request, 'tasks/tasks.html', context)


@login_required
@require_POST
def create_share_link(request):
    obj = _owned_share_object(
        request.user,
        (request.POST.get('object_type') or '').strip(),
        request.POST.get('object_id'),
        workplace=_active_workplace(request),
    )
    permission = _share_permission_from_request(request)
    link, created = SharedItemLink.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=obj.pk,
        created_by=request.user,
        is_active=True,
        defaults={'permission': permission},
    )
    permission_updated = False
    if not created and link.permission != permission:
        link.permission = permission
        link.save(update_fields=['permission'])
        permission_updated = True
    return JsonResponse({
        'status': 'success',
        'created': created,
        'permission_updated': permission_updated,
        'permission': link.permission,
        'permission_label': _share_permission_label(link.permission),
        'url': _share_link_url(request, link),
    })


@login_required
@require_POST
def revoke_share_link(request):
    obj = _owned_share_object(
        request.user,
        (request.POST.get('object_type') or '').strip(),
        request.POST.get('object_id'),
        workplace=_active_workplace(request),
    )
    updated_count = SharedItemLink.objects.filter(
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=obj.pk,
        created_by=request.user,
        is_active=True,
    ).update(is_active=False, deactivated_at=timezone.now())

    return JsonResponse({
        'status': 'success',
        'revoked': bool(updated_count),
    })


@login_required
def accept_share_link(request, token):
    link = SharedItemLink.objects.select_related('content_type', 'created_by').filter(token=token).first()
    if not link:
        messages.error(request, 'Ten link udostępniania nie istnieje albo został przepisany niepoprawnie.')
        return redirect('tasks:tasks')
    if not link.is_active:
        messages.error(request, 'Ten link udostępniania został wyłączony.')
        return redirect('tasks:tasks')

    obj = link.content_object
    if not obj:
        messages.error(request, 'Ten link udostępniania nie prowadzi już do żadnego elementu.')
        return redirect('tasks:tasks')

    owner = _task_share_owner(obj)
    if owner == request.user:
        messages.info(request, 'To jest Twój element.')
    else:
        SharedItem.objects.update_or_create(
            content_type=link.content_type,
            object_id=link.object_id,
            shared_by=link.created_by,
            shared_with=request.user,
            defaults={'permission': link.permission},
        )
        messages.success(request, f'Dodano dostęp: {_task_share_type_label(obj).lower()} „{_task_share_label(obj)}”.')

    return redirect(_task_share_object_url(obj))


@login_required
@require_POST
def update_task_status(request, task_id):
    try:
        workplace = _active_workplace(request)
        data = json.loads(request.body)
        task_pk = data.get('task_pk')
        if task_pk:
            task = Task.objects.select_related('section', 'section__project').filter(
                _task_access_filter(request.user, workplace),
                pk=task_pk,
            ).first()
            if not task:
                return JsonResponse({'status': 'error', 'message': 'Zadanie nie znalezione'}, status=404)
            if task.task_id != task_id:
                return JsonResponse({'status': 'error', 'message': 'Nieprawidłowe zadanie'}, status=400)
        else:
            task = _filter_workplace(Task.objects.filter(user=request.user), workplace).get(task_id=task_id)
        if not _user_can_edit_task(request.user, task):
            return JsonResponse({'status': 'error', 'message': 'Brak uprawnień do edycji zadania'}, status=403)
        status = data.get('status')
        previous_status = task.status

        if status:
            if not _set_task_status(task, status):
                return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy status'}, status=400)
        else:
            is_completed = data.get('is_completed', False)
            _set_task_status(task, 'closed' if is_completed else 'reopened')

        if previous_status != task.status:
            status_labels = dict(Task.STATUS_CHOICES)
            _record_task_activity(
                task,
                request.user,
                'status_changed',
                'zmienił status',
                metadata={
                    'from_label': status_labels.get(previous_status, previous_status),
                    'to_label': task.get_status_display(),
                    'changes': [{
                        'field': 'status',
                        'from_label': status_labels.get(previous_status, previous_status),
                        'to_label': task.get_status_display(),
                    }],
                },
            )
        
        return JsonResponse({
            'status': 'success',
            'new_status_display': task.get_status_display(),
            'new_status_code': task.status
        })
    except Task.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Zadanie nie znalezione'}, status=404)

@login_required
@require_POST
def delete_task(request, task_id):
    try:
        task = _filter_workplace(Task.objects.filter(user=request.user), _active_workplace(request)).get(task_id=task_id)
        task.delete()
        return JsonResponse({'status': 'success', 'message': 'Zadanie usunięte pomyślnie'})
    except Task.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Zadanie nie znalezione'}, status=404)

@login_required
@require_POST
def delete_attachment(request, attachment_id):
    try:
        attachment = get_object_or_404(
            _filter_workplace(
                TaskAttachment.objects.select_related('task', 'task__section', 'task__section__project'),
                _active_workplace(request),
                field_name='task__workplace',
            ),
            id=attachment_id,
        )
        if not _user_can_edit_task(request.user, attachment.task):
            return JsonResponse({'status': 'error', 'message': 'Brak uprawnień do edycji zadania'}, status=403)
        attachment.delete()
        return JsonResponse({'status': 'success', 'message': 'Załącznik usunięty pomyślnie'})
    except TaskAttachment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Załącznik nie znaleziony'}, status=404)


@login_required
def download_attachment(request, attachment_id):
    attachment = get_object_or_404(
        _filter_workplace(
            TaskAttachment.objects.select_related('task'),
            _active_workplace(request),
            field_name='task__workplace',
        ).filter(task__user=request.user),
        id=attachment_id,
    )
    return attachment_download_response(attachment)


@login_required
@require_POST
def delete_tasks(request):
    try:
        data = json.loads(request.body)
        task_ids = data.get('task_ids', [])
        
        if not task_ids:
            return JsonResponse({'status': 'error', 'message': 'Nie podano ID zadań'}, status=400)
        
        user = request.user
        workplace = _active_workplace(request)
        deleted_count = _filter_workplace(Task.objects.filter(task_id__in=task_ids, user=user), workplace).delete()[0]
        Task._renumber_user_tasks(user, workplace)
        
        return JsonResponse({
            'status': 'success', 
            'message': f'{deleted_count} {"zadań" if deleted_count != 1 else "zadanie"} usuniętych pomyślnie',
            'deleted_count': deleted_count
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy JSON'}, status=400)
    except Exception:
        logger.exception('Failed to delete tasks')
        return JsonResponse({'status': 'error', 'message': 'Nie udało się usunąć zadań.'}, status=500)

@login_required
@require_POST
def bulk_update_status(request):
    try:
        data = json.loads(request.body)
        task_ids = data.get('task_ids', [])
        status = data.get('status', 'closed')
        
        if not task_ids:
            return JsonResponse({'status': 'error', 'message': 'Nie podano ID zadań'}, status=400)
        valid_statuses = {choice for choice, _label in Task.STATUS_CHOICES}
        if status not in valid_statuses:
            return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy status'}, status=400)
        
        user = request.user
        workplace = _active_workplace(request)
        tasks_to_update = _filter_workplace(Task.objects.filter(task_id__in=task_ids, user=user), workplace)
        matched_tasks = list(tasks_to_update.values('id', 'status'))
        updated_count = len(matched_tasks)
        task_pks = [task['id'] for task in matched_tasks]
        if task_pks:
            update_queryset = Task.objects.filter(pk__in=task_pks)
            if status == 'closed':
                now = timezone.now()
                newly_closed_pks = [task['id'] for task in matched_tasks if task['status'] != 'closed']
                already_closed_pks = [task['id'] for task in matched_tasks if task['status'] == 'closed']
                if newly_closed_pks:
                    Task.objects.filter(pk__in=newly_closed_pks).update(
                        status=status,
                        is_completed=True,
                        completion_date=now,
                    )
                if already_closed_pks:
                    Task.objects.filter(pk__in=already_closed_pks).update(
                        status=status,
                        is_completed=True,
                    )
            else:
                update_queryset.update(
                    status=status,
                    is_completed=False,
                    completion_date=None,
                )
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Zaktualizowano {updated_count} {"zadań" if updated_count != 1 else "zadanie"}',
            'updated_count': updated_count
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy JSON'}, status=400)
    except Exception:
        logger.exception('Failed to bulk update task status')
        return JsonResponse({'status': 'error', 'message': 'Nie udało się zaktualizować zadań.'}, status=500)

def _task_detail_response(request, task_id=None, task_pk=None):
    workplace = _active_workplace(request)
    task_queryset = _filter_workplace(
        Task.objects.select_related('section', 'section__project', 'section__project__user', 'parent', 'assignee', 'company', 'contact'),
        workplace,
    ).prefetch_related(
        Prefetch(
            'subtasks',
            queryset=_filter_workplace(
                Task.objects.select_related('section', 'section__project', 'assignee', 'company', 'contact'),
                workplace,
            ).prefetch_related('tags', 'attachments').order_by('task_id'),
        ),
        Prefetch(
            'activities',
            queryset=TaskActivity.objects.select_related('actor').order_by('created_at', 'id'),
        ),
    )
    if task_pk is not None:
        raise PermissionDenied
    task = get_object_or_404(task_queryset, task_id=task_id, user=request.user)

    can_manage_task = task.user_id == request.user.id
    can_edit_task = _user_can_edit_task(request.user, task)
    subtask_status_groups = _status_groups_for_tasks(task.subtasks.all(), request.user)
    can_add_attachments = can_edit_task and not task.parent_id
    form = TaskForm(instance=task, user=task.user, workplace=workplace)
    task_modal_form = SubTaskModalForm()
    task_modal_open = False
    _decorate_task_directory_members([task], current_user=request.user)

    if request.method == 'POST':
        is_ajax = _is_ajax_request(request)
        action = request.POST.get('action')
        if action == 'create_subtask_modal':
            if not can_edit_task:
                raise PermissionDenied
            task_modal_form = SubTaskModalForm(request.POST)
            if task_modal_form.is_valid():
                subtask = task_modal_form.save(commit=False)
                subtask.user = task.user
                subtask.parent = task
                subtask.section = task.section
                subtask.workplace = workplace
                subtask.save()
                _record_task_activity(
                    task,
                    request.user,
                    'subtask_created',
                    'dodał podzadanie',
                    metadata={
                        'subtask_title': subtask.title,
                        'subtask_task_id': subtask.task_id,
                    },
                )
                messages.success(request, 'Podzadanie dodane.')
                return _redirect_to_task_detail(task, request.user)
            task_modal_open = True
            messages.error(request, 'Nie udało się dodać podzadania.')
        elif action == 'add_activity_comment':
            comment = (request.POST.get('activity_comment') or '').strip()
            if comment:
                _record_task_activity(
                    task,
                    request.user,
                    'commented',
                    comment,
                    kind='comment',
                )
                messages.success(request, 'Komentarz dodany.')
            else:
                messages.error(request, 'Wpisz treść komentarza.')
            return _redirect_to_task_detail(task, request.user)
        elif action == 'clear_time_spent':
            if not can_edit_task:
                raise PermissionDenied
            if task.has_time_spent:
                before = _task_activity_snapshot(task)
                task.time_spent_hours = None
                task.time_spent_minutes = None
                task.save(update_fields=['time_spent_hours', 'time_spent_minutes'])

                change_activities = _task_change_activities(task, before)
                recorded_activities = []
                for change in change_activities:
                    recorded_activities.append(
                        _record_task_activity(
                            task,
                            request.user,
                            change['action'],
                            change['message'],
                            metadata=change['metadata'],
                        )
                    )
                message = 'Czas pracy usunięty.'
                if is_ajax:
                    return JsonResponse({
                        'status': 'success',
                        'message': message,
                        'task': _task_detail_payload(task),
                        'activity_html': _task_activity_html(recorded_activities),
                    })
                messages.success(request, message)
            else:
                message = 'Brak czasu pracy do usunięcia.'
                if is_ajax:
                    return JsonResponse({
                        'status': 'success',
                        'message': message,
                        'task': _task_detail_payload(task),
                    })
                messages.info(request, message)
            return _redirect_to_task_detail(task, request.user)
        else:
            if not can_edit_task:
                raise PermissionDenied
            files = request.FILES.getlist('attachments') if can_add_attachments else []
            file_errors = _attachment_validation_errors(files)
            before = _task_activity_snapshot(task)
            form = TaskForm(request.POST, request.FILES, instance=task, user=task.user, workplace=workplace)
            if form.is_valid() and not file_errors:
                form.save()
                recorded_activities = []

                # Handle staged attachment deletions
                deleted_attachments = request.POST.get('deleted_attachments', '')
                deleted_count = 0
                if deleted_attachments:
                    attachment_ids = [int(aid) for aid in deleted_attachments.split(',') if aid.isdigit()]
                    attachments_to_delete = TaskAttachment.objects.filter(id__in=attachment_ids, task=task)
                    deleted_count = attachments_to_delete.count()
                    attachments_to_delete.delete()

                # Handle new file attachments
                for file in files:
                    TaskAttachment.objects.create(
                        task=task,
                        file=file
                    )

                change_activities = _task_change_activities(task, before)
                for change in change_activities:
                    recorded_activities.append(
                        _record_task_activity(
                            task,
                            request.user,
                            change['action'],
                            change['message'],
                            metadata=change['metadata'],
                        )
                    )
                if files:
                    recorded_activities.append(
                        _record_task_activity(
                            task,
                            request.user,
                            'attachments_added',
                            'dodał załączniki',
                            metadata={'count': len(files)},
                        )
                    )
                if deleted_count:
                    recorded_activities.append(
                        _record_task_activity(
                            task,
                            request.user,
                            'attachments_deleted',
                            'usunął załączniki',
                            metadata={'count': deleted_count},
                        )
                    )

                if is_ajax:
                    task.refresh_from_db()
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Zapisano automatycznie.',
                        'task': _task_detail_payload(task),
                        'changed_fields': [
                            field
                            for change in change_activities
                            for field in change.get('metadata', {}).get('fields', [])
                        ],
                        'attachments_added': len(files),
                        'attachments_deleted': deleted_count,
                        'activity_html': _task_activity_html(recorded_activities),
                    })

                messages.success(request, 'Zadanie zaktualizowane pomyślnie.')
                return _redirect_to_task_detail(task, request.user)
            else:
                if is_ajax:
                    error_messages = [*file_errors, *_form_error_messages(form)]
                    return JsonResponse({
                        'status': 'error',
                        'message': error_messages[0] if error_messages else 'Nie udało się zapisać zmian.',
                        'errors': error_messages,
                    }, status=400)
                for error in file_errors:
                    messages.error(request, error)
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
    else:
        form = TaskForm(instance=task, user=task.user, workplace=workplace)

    if not can_edit_task:
        for field in form.fields.values():
            field.disabled = True

    context = {
        'form': form,
        'task_modal_form': task_modal_form,
        'task_modal_open': task_modal_open,
        'task': task,
        'can_manage_task': can_manage_task,
        'can_edit_task': can_edit_task,
        'can_share_task': False,
        'can_add_attachments': can_add_attachments,
        'activity_items': task.activities.order_by('-created_at', '-id'),
        'subtask_status_groups': subtask_status_groups,
        'tasks_return_path': request.get_full_path(),
        **_tasks_navigation_context(
            request.user,
            active_section=task.section,
            active_view='section' if task.section_id else 'all_tasks',
            workplace=workplace,
        ),
    }
    return render(request, 'tasks/view_task.html', context)


@login_required
def view_task(request, task_id):
    return _task_detail_response(request, task_id)

@login_required
def view_subtask(request, task_id):
    return _task_detail_response(request, task_id)
