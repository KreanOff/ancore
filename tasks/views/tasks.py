import json
import logging
import unicodedata
from collections import defaultdict
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Case, Count, F, IntegerField, Max, Prefetch, Q, Sum, Value, When
from django.http import Http404, JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages

from dashboard.collaboration import follow_context, mention_choices
from tasks.access import editable_to, require_editable, visible_to, require_deletable_tasks
from tasks.directory import decorate_favorites, directory_queryset, directory_tab, directory_tabs
from tasks.views.task_team import team_payload as _task_team_payload
from tasks.sharing import project_access_data, section_access_data
from workplaces.models import Workplace
from workplaces.services import workspace_owner, scoped_workplace_app_path
from accounts.avatar import account_avatar
from accounts.models import normalize_public_username
from contacts.models import SharedItem, SharedItemLink, UserContact
from core.task_numbering import lock_task_numbers
from core.task_requests import task_detail_lookup, task_primary_keys
from core.upload_validation import (
    DEFAULT_ATTACHMENT_MAX_SIZE, MAX_COMMENT_ATTACHMENTS, ATTACHMENT_ALLOWED_EXTENSIONS,
    attachment_download_response, validate_attachment_upload,
)
from core.comment_images import save_comment, comment_image_response
from ..models import (
    PROJECT_FIELD_OPTION_DEFAULTS,
    Task,
    TaskActivity,
    TaskAttachment,
    TaskCommentImage,
    TaskProject,
    TaskProjectTemplate,
    TaskProjectDeadlineRule,
    TaskProjectFieldOption,
    TaskProjectNote,
    TaskSection,
    TaskSectionNote,
    TaskTag,
    TaskTagNote,
    TaskWorkLog,
    parse_hierarchy_code_number,
)
from ..forms import (
    QuickTaskForm,
    SubTaskModalForm,
    TaskForm,
    TaskModalForm,
    TaskProjectForm,
    TaskProjectRenameForm,
    TaskSectionForm,
    TaskSectionRenameForm,
    TaskTagForm,
    TaskWorkLogForm,
)


from ..project_templates import populate_project_from_template, save_project_template

logger = logging.getLogger(__name__)

PROJECT_PAGE_SIZE_OPTIONS = (10, 25, 50, 100, 150, 200)
PROJECT_DEFAULT_PAGE_SIZE = 50
PROJECT_NAVIGATION_LIMIT = 50
TASK_PAGE_SIZE_OPTIONS = PROJECT_PAGE_SIZE_OPTIONS
TASK_DEFAULT_PAGE_SIZE = 25
PROJECT_DEFAULT_SORT = 'name_asc'
PROJECT_SORT_FIELDS = (
    {'value': 'name', 'label': 'Nazwa projektu', 'icon': 'briefcase-business'},
    {'value': 'code', 'label': 'Kod projektu', 'icon': 'hash'},
    {'value': 'description', 'label': 'Opis', 'icon': 'align-left'},
    {'value': 'priority', 'label': 'Priorytet', 'icon': 'chart-no-axes-column-increasing'},
    {'value': 'start_at', 'label': 'Data rozpoczęcia', 'icon': 'calendar-range'},
    {'value': 'due_at', 'label': 'Termin', 'icon': 'calendar-clock'},
    {'value': 'company', 'label': 'Firma', 'icon': 'building-2'},
    {'value': 'responsible', 'label': 'Odpowiedzialny', 'icon': 'circle-user-round'},
    {'value': 'status', 'label': 'Status', 'icon': 'circle-dot'},
    {'value': 'stage', 'label': 'Etap', 'icon': 'milestone'},
    {'value': 'health', 'label': 'Kondycja', 'icon': 'heart-pulse'},
    {'value': 'source', 'label': 'Źródło', 'icon': 'waypoints'},
    {'value': 'created', 'label': 'Data utworzenia', 'icon': 'calendar-plus-2'},
    {'value': 'activity', 'label': 'Ostatnia aktywność', 'icon': 'activity'},
)
PROJECT_SORT_OPTIONS = (
    {'value': 'name_asc', 'label': 'Projekt A-Z', 'icon': 'arrow-up-a-z', 'direction': 'asc', 'field': 'name'},
    {'value': 'name_desc', 'label': 'Projekt Z-A', 'icon': 'arrow-down-z-a', 'direction': 'desc', 'field': 'name'},
    {'value': 'code_asc', 'label': 'Kod A-Z', 'icon': 'arrow-up-a-z', 'direction': 'asc'},
    {'value': 'code_desc', 'label': 'Kod Z-A', 'icon': 'arrow-down-z-a', 'direction': 'desc'},
    {'value': 'description_asc', 'label': 'Opis A-Z', 'icon': 'align-left', 'direction': 'asc'},
    {'value': 'description_desc', 'label': 'Opis Z-A', 'icon': 'align-left', 'direction': 'desc'},
    {'value': 'company_asc', 'label': 'Firma A-Z', 'icon': 'building-2', 'direction': 'asc'},
    {'value': 'company_desc', 'label': 'Firma Z-A', 'icon': 'building-2', 'direction': 'desc'},
    {'value': 'responsible_asc', 'label': 'Odpowiedzialny A-Z', 'icon': 'circle-user-round', 'direction': 'asc'},
    {'value': 'responsible_desc', 'label': 'Odpowiedzialny Z-A', 'icon': 'circle-user-round', 'direction': 'desc'},
    {'value': 'status_asc', 'label': 'Status rosnąco', 'icon': 'circle-dot', 'direction': 'asc'},
    {'value': 'status_desc', 'label': 'Status malejąco', 'icon': 'circle-dot', 'direction': 'desc'},
    {'value': 'stage_asc', 'label': 'Etap rosnąco', 'icon': 'milestone', 'direction': 'asc'},
    {'value': 'stage_desc', 'label': 'Etap malejąco', 'icon': 'milestone', 'direction': 'desc'},
    {'value': 'health_asc', 'label': 'Kondycja rosnąco', 'icon': 'heart-pulse', 'direction': 'asc'},
    {'value': 'health_desc', 'label': 'Kondycja malejąco', 'icon': 'heart-pulse', 'direction': 'desc'},
    {'value': 'priority_asc', 'label': 'Priorytet rosnąco', 'icon': 'chart-no-axes-column-increasing', 'direction': 'asc'},
    {'value': 'priority_desc', 'label': 'Priorytet', 'icon': 'chart-no-axes-column-increasing', 'direction': 'desc'},
    {'value': 'start_at_asc', 'label': 'Najwcześniejszy start', 'icon': 'calendar-range', 'direction': 'asc'},
    {'value': 'start_at_desc', 'label': 'Najpóźniejszy start', 'icon': 'calendar-range', 'direction': 'desc'},
    {'value': 'due_at_asc', 'label': 'Najbliższy termin', 'icon': 'calendar-clock', 'direction': 'asc'},
    {'value': 'due_at_desc', 'label': 'Najdalszy termin', 'icon': 'calendar-clock', 'direction': 'desc'},
    {'value': 'source_asc', 'label': 'Źródło A-Z', 'icon': 'waypoints', 'direction': 'asc'},
    {'value': 'source_desc', 'label': 'Źródło Z-A', 'icon': 'waypoints', 'direction': 'desc'},
    {'value': 'created_asc', 'label': 'Najstarsze', 'icon': 'clock-3', 'direction': 'asc'},
    {'value': 'created_desc', 'label': 'Najnowsze', 'icon': 'clock-3', 'direction': 'desc'},
    {'value': 'activity_asc', 'label': 'Najdawniejsza aktywność', 'icon': 'activity', 'direction': 'asc'},
    {'value': 'activity_desc', 'label': 'Ostatnia aktywność', 'icon': 'activity', 'direction': 'desc'},
)
PROJECT_SORT_OPTION_MAP = {option['value']: option for option in PROJECT_SORT_OPTIONS}
PROJECT_TEXT_FILTER_OPERATORS = (
    {'value': 'contains', 'label': 'zawiera'},
    {'value': 'not_contains', 'label': 'nie zawiera'},
    {'value': 'is_empty', 'label': 'jest puste'},
    {'value': 'is_not_empty', 'label': 'nie jest puste'},
)
PROJECT_TEXT_FILTER_OPERATOR_MAP = {
    option['value']: option['label']
    for option in PROJECT_TEXT_FILTER_OPERATORS
}
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
    {'value': 'type_asc', 'label': 'Typ', 'icon': 'list-filter', 'direction': 'asc'},
    {'value': 'due_at_asc', 'label': 'Najbliższy termin', 'icon': 'calendar-clock', 'direction': 'asc'},
    {'value': 'created_desc', 'label': 'Najnowsze', 'icon': 'clock-3', 'direction': 'desc'},
    {'value': 'activity_desc', 'label': 'Ostatnia aktywność', 'icon': 'activity', 'direction': 'desc'},
)
TASK_SORT_OPTION_MAP = {option['value']: option for option in TASK_SORT_OPTIONS}
TAG_DEFAULT_SORT = 'name_asc'
TAG_SORT_OPTIONS = (
    {'value': 'name_asc', 'label': 'Nazwa A-Z', 'icon': 'arrow-up-a-z', 'direction': 'asc'},
    {'value': 'name_desc', 'label': 'Nazwa Z-A', 'icon': 'arrow-down-z-a', 'direction': 'desc'},
    {'value': 'code_asc', 'label': 'Kod A-Z', 'icon': 'hash', 'direction': 'asc'},
    {'value': 'code_desc', 'label': 'Kod Z-A', 'icon': 'hash', 'direction': 'desc'},
    {'value': 'category_asc', 'label': 'Typ', 'icon': 'list-filter', 'direction': 'asc'},
    {'value': 'visual_asc', 'label': 'Kolor i ikona', 'icon': 'palette', 'direction': 'asc'},
    {'value': 'priority_desc', 'label': 'Priorytet', 'icon': 'chart-no-axes-column-increasing', 'direction': 'desc'},
    {'value': 'scope_asc', 'label': 'Zakres', 'icon': 'target', 'direction': 'asc'},
    {'value': 'owner_asc', 'label': 'Właściciel', 'icon': 'circle-user-round', 'direction': 'asc'},
    {'value': 'status_asc', 'label': 'Status', 'icon': 'circle-dot', 'direction': 'asc'},
    {'value': 'related_desc', 'label': 'Najwięcej powiązań', 'icon': 'network', 'direction': 'desc'},
    {'value': 'task_count_desc', 'label': 'Najwięcej zadań', 'icon': 'list-checks', 'direction': 'desc'},
    {'value': 'created_desc', 'label': 'Najnowsze', 'icon': 'clock-3', 'direction': 'desc'},
)
TAG_SORT_OPTION_MAP = {option['value']: option for option in TAG_SORT_OPTIONS}
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


def _mark_task_row_access(tasks, user, viewer=None):
    if not user or not getattr(user, 'is_authenticated', False):
        return tasks

    editable_ids = set(editable_to(Task.objects.filter(pk__in=[task.pk for task in tasks if task]), viewer or user).values_list('pk', flat=True))
    for task in tasks:
        if not task:
            continue
        task.can_manage = task.user_id == user.id and task.pk in editable_ids
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
    _mark_task_row_access(status_tasks, user, viewer=request.user if request else user)

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
        compact_summary = '0 z 0'
    else:
        first_visible = offset + 1
        last_visible = offset + len(status_tasks)
        summary = f'Pokazano {first_visible}-{last_visible} z {total_tasks} zadań'
        compact_summary = f'{first_visible}-{last_visible} z {total_tasks}'

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
        'compact_summary': compact_summary,
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
    _mark_task_row_access(task_list, user, viewer=request.user if request else user)
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


def _user_can_edit_task(user, task, viewer=None):
    return _user_task_permission(user, task) in ('owner', 'edit') and editable_to(Task.objects.all(), viewer or user).filter(pk=task.pk).exists()


def _user_can_create_task_in_section(user, section):
    if not user or not getattr(user, 'is_authenticated', False) or not section:
        return False
    return _user_section_permission(user, section) in ('owner', 'edit')


def _editable_sections_queryset(user, workplace=None, viewer=None):
    if not user or not getattr(user, 'is_authenticated', False):
        return TaskSection.objects.none()
    queryset = editable_to(TaskSection.objects.all(), viewer or user).filter(project__user=user).select_related('project', 'project__user').distinct()
    return _filter_workplace(queryset, workplace, field_name='project__workplace')


def _task_creation_project_for_user(user, project_id, workplace=None, viewer=None):
    if not project_id:
        return None
    return (
        visible_to(TaskProject.objects.all(), viewer or user).filter(id=project_id, sections__in=_editable_sections_queryset(user, workplace, viewer=viewer or user))
        .distinct()
        .first()
    )


def _user_can_create_issue(user, active_project=None, active_section=None, workplace=None, viewer=None):
    editable_sections = _editable_sections_queryset(user, workplace, viewer=viewer or user)
    if active_section:
        return editable_sections.filter(pk=active_section.pk).exists()
    if active_project:
        return editable_sections.filter(project=active_project).exists()
    return bool(user and getattr(user, 'is_authenticated', False))


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


def _owned_share_object(user, object_type, object_id, workplace=None, viewer=None):
    if object_type == 'project':
        return get_object_or_404(_filter_workplace(visible_to(TaskProject.objects.all(), viewer or user).filter(user=user), workplace), id=object_id)
    if object_type == 'section':
        return get_object_or_404(_filter_workplace(visible_to(TaskSection.objects.all(), viewer or user).filter(project__user=user), workplace, field_name='project__workplace'), id=object_id)
    if object_type == 'task':
        return get_object_or_404(_filter_workplace(visible_to(Task.objects.all(), viewer or user).select_related('section', 'section__project').filter(user=user), workplace), id=object_id)
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


def _mark_project_permissions(projects, user, viewer=None):
    editable_ids = set(editable_to(TaskProject.objects.filter(pk__in=[project.pk for project in projects]), viewer or user).values_list('pk', flat=True))
    section_ids = [section.pk for project in projects for section in project.sections.all()]
    editable_sections = set(editable_to(TaskSection.objects.filter(pk__in=section_ids), viewer or user).values_list('pk', flat=True))
    for project in projects:
        _clear_share_access_badge(project)
        project.can_manage = project.user_id == user.id and project.pk in editable_ids
        project.can_share = False
        project.can_edit = project.can_manage
        project.has_editable_sections = False
        for section in project.sections.all():
            _clear_share_access_badge(section)
            section.can_manage = project.can_manage and section.pk in editable_sections
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


def _project_field_configuration(user, workplace=None, viewer=None):
    options = list(TaskProjectFieldOption.active_for_scope(user, workplace))
    choices = {field_type: [] for field_type, _label in TaskProjectFieldOption.FIELD_CHOICES}
    labels = {field_type: {} for field_type in choices}
    colors = {field_type: {} for field_type in choices}
    for option in options:
        choices[option.field_type].append((option.project_value, option.label))
        labels[option.field_type][option.project_value] = option.label
        colors[option.field_type][option.project_value] = option.color

    scoped_projects = visible_to(TaskProject.objects.all(), viewer or user).filter(user=user, workplace=workplace)
    used_values = {
        field_type: set(scoped_projects.values_list(field_type, flat=True).distinct())
        for field_type in choices
    }
    for option in options:
        option.in_use = option.project_value in used_values[option.field_type]

    group_copy = {
        'status': ('Status projektu', 'Określa bieżący stan projektu.'),
        'stage': ('Etap', 'Opisuje fazę realizacji projektu.'),
        'health': ('Kondycja', 'Sygnalizuje ryzyko i ogólną kondycję projektu.'),
        'source': ('Źródło', 'Dodaj gotowe źródła projektów i wybierz ich kolory.'),
    }
    groups = []
    for field_type, _field_label in TaskProjectFieldOption.FIELD_CHOICES:
        label, description = group_copy[field_type]
        groups.append({
            'field_type': field_type,
            'label': label,
            'description': description,
            'max_length': 120 if field_type == TaskProjectFieldOption.FIELD_SOURCE else 60,
            'options': [option for option in options if option.field_type == field_type],
        })

    return {
        'options': options,
        'choices': choices,
        'labels': labels,
        'colors': colors,
        'groups': groups,
        'deadline_rules': list(TaskProjectDeadlineRule.active_for_scope(user, workplace)),
    }


def _decorate_project_field_values(projects, field_configuration):
    if not projects:
        return
    labels = field_configuration['labels']
    colors = field_configuration['colors']
    deadline_rules = field_configuration.get('deadline_rules', [])
    custom_rules = {
        project.pk: [] for project in projects if project.use_custom_deadline_rules
    }
    if custom_rules:
        for rule in TaskProjectDeadlineRule.objects.filter(project_id__in=custom_rules, is_active=True):
            custom_rules[rule.project_id].append(rule)
    today = timezone.localdate()
    default_colors = {
        field_type: {value: color for value, _label, color in defaults}
        for field_type, defaults in PROJECT_FIELD_OPTION_DEFAULTS.items()
    }
    for project in projects:
        project._project_field_option_labels = labels
        project.source_color = colors.get('source', {}).get(project.source, '')
        project.due_color = ''
        project.due_description = ''
        if project.due_at:
            days_left = (project.due_at - today).days
            if days_left < 0:
                project.due_description = f'Po terminie: {abs(days_left)} dni'
            elif days_left == 0:
                project.due_description = 'Termin dzisiaj'
            else:
                project.due_description = f'Dni do terminu: {days_left}'
            if project.status not in ('completed', 'cancelled'):
                rules = custom_rules.get(project.pk, deadline_rules)
                project.due_color = TaskProjectDeadlineRule.color_for_date(project.due_at, rules, today) or '#DFEFFF'
        for field_type in ('status', 'stage', 'health'):
            value = getattr(project, field_type, '')
            setattr(
                project,
                f'{field_type}_color',
                colors.get(field_type, {}).get(value, default_colors.get(field_type, {}).get(value, '#E9ECF0')),
            )


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


def _project_text_filter_operator(value):
    return value if value in PROJECT_TEXT_FILTER_OPERATOR_MAP else 'contains'


def _project_text_filter_is_active(value, operator):
    return bool((value or '').strip()) or operator in {'is_empty', 'is_not_empty'}


def _apply_project_text_filter(queryset, field_name, value, operator):
    operator = _project_text_filter_operator(operator)
    value = (value or '').strip()
    if operator == 'is_empty':
        return queryset.filter(Q(**{field_name: ''}) | Q(**{f'{field_name}__isnull': True}))
    if operator == 'is_not_empty':
        return queryset.exclude(Q(**{field_name: ''}) | Q(**{f'{field_name}__isnull': True}))
    if not value:
        return queryset
    lookup = {f'{field_name}__icontains': value}
    return queryset.exclude(**lookup) if operator == 'not_contains' else queryset.filter(**lookup)


def _group_sort_value(value):
    return value if value in GROUP_SORT_OPTION_MAP else GROUP_DEFAULT_SORT


def _task_sort_value(value):
    return value if value in TASK_SORT_OPTION_MAP else TASK_DEFAULT_SORT


def _tag_sort_value(value):
    return value if value in TAG_SORT_OPTION_MAP else TAG_DEFAULT_SORT


def _choice_rank_case(field_name, choices):
    return Case(
        *[When(**{field_name: value}, then=Value(index)) for index, (value, _label) in enumerate(choices)],
        default=Value(len(choices)),
        output_field=IntegerField(),
    )


def _project_filter_queryset(
    user,
    query='',
    name='',
    name_operator='contains',
    code='',
    code_operator='contains',
    description='',
    description_operator='contains',
    source='',
    source_operator='contains',
    priority='',
    status='',
    stage='',
    health='',
    company='',
    responsible='',
    workplace=None,
    project_choices=None,
    viewer=None,
):
    project_choices = project_choices or {
        'status': TaskProject.STATUS_CHOICES,
        'stage': TaskProject.STAGE_CHOICES,
        'health': TaskProject.HEALTH_CHOICES,
    }
    queryset = _filter_workplace(visible_to(TaskProject.objects.all(), viewer or user).filter(user=user), workplace)
    query = (query or '').strip()
    if query:
        priority_matches = _choice_values_matching_query(TaskProject.PRIORITY_CHOICES, query)
        status_matches = _choice_values_matching_query(project_choices['status'], query)
        stage_matches = _choice_values_matching_query(project_choices['stage'], query)
        health_matches = _choice_values_matching_query(project_choices['health'], query)
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
    queryset = _apply_project_text_filter(queryset, 'name', name, name_operator)
    queryset = _apply_project_text_filter(queryset, 'code', code, code_operator)
    queryset = _apply_project_text_filter(queryset, 'description', description, description_operator)
    queryset = _apply_project_text_filter(queryset, 'source', source, source_operator)
    if priority in {value for value, _label in TaskProject.PRIORITY_CHOICES}:
        queryset = queryset.filter(priority=priority)
    if status in {value for value, _label in project_choices['status']}:
        queryset = queryset.filter(status=status)
    if stage in {value for value, _label in project_choices['stage']}:
        queryset = queryset.filter(stage=stage)
    if health in {value for value, _label in project_choices['health']}:
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


def _project_sort_queryset(queryset, sort_value, project_choices=None, viewer=None):
    sort_value = _project_sort_value(sort_value)
    project_choices = project_choices or {
        'status': TaskProject.STATUS_CHOICES,
        'stage': TaskProject.STAGE_CHOICES,
        'health': TaskProject.HEALTH_CHOICES,
    }
    field_name, direction = sort_value.rsplit('_', 1)
    descending = direction == 'desc'
    prefix = '-' if descending else ''

    if field_name == 'name':
        return queryset.order_by(f'{prefix}name', 'id')
    if field_name in {'code', 'description', 'source'}:
        empty_alias = f'project_{field_name}_empty_sort'
        return queryset.annotate(
            **{
                empty_alias: Case(
                    When(**{field_name: ''}, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            }
        ).order_by(empty_alias, f'{prefix}{field_name}', f'{prefix}name', 'id')
    if field_name == 'company':
        return queryset.annotate(
            project_company_empty_sort=Case(
                When(company__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('project_company_empty_sort', f'{prefix}company__name', f'{prefix}name', 'id')
    if field_name == 'responsible':
        return queryset.annotate(
            project_responsible_empty_sort=Case(
                When(responsible_user__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by(
            'project_responsible_empty_sort',
            f'{prefix}responsible_user__last_name',
            f'{prefix}responsible_user__first_name',
            f'{prefix}responsible_user__username',
            f'{prefix}name',
            'id',
        )
    if field_name in {'status', 'stage', 'health'}:
        rank_alias = f'project_{field_name}_sort_rank'
        return queryset.annotate(
            **{rank_alias: _choice_rank_case(field_name, project_choices[field_name])}
        ).order_by(f'{prefix}{rank_alias}', 'name', 'id')
    if field_name == 'priority':
        return queryset.annotate(
            project_priority_sort_rank=_choice_rank_case('priority', TaskProject.PRIORITY_CHOICES)
        ).order_by(f'{prefix}project_priority_sort_rank', 'name', 'id')
    if field_name in {'start_at', 'due_at'}:
        empty_alias = f'project_{field_name}_empty_sort'
        return queryset.annotate(
            **{
                empty_alias: Case(
                    When(**{f'{field_name}__isnull': True}, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            }
        ).order_by(empty_alias, f'{prefix}{field_name}', 'name', 'id')
    if field_name == 'created':
        return queryset.order_by(f'{prefix}created_at', f'{prefix}name', 'id')
    if field_name == 'activity':
        activity_order = (
            F('project_last_activity_sort').desc(nulls_last=True)
            if descending
            else F('project_last_activity_sort').asc(nulls_last=True)
        )
        task_created_order = (
            F('project_last_task_created_sort').desc(nulls_last=True)
            if descending
            else F('project_last_task_created_sort').asc(nulls_last=True)
        )
        return queryset.annotate(
            project_last_task_created_sort=Max('sections__tasks__created_at', filter=Q(sections__tasks__in=visible_to(Task.objects.all(), viewer))),
            project_last_activity_sort=Max('sections__tasks__activities__created_at', filter=Q(sections__tasks__activities__in=visible_to(TaskActivity.objects.all(), viewer))),
        ).order_by(activity_order, task_created_order, f'{prefix}created_at', 'name', 'id')
    return queryset.order_by('name', 'id')


def _project_filter_options(user, workplace=None, project_choices=None, viewer=None):
    project_choices = project_choices or {
        'status': TaskProject.STATUS_CHOICES,
        'stage': TaskProject.STAGE_CHOICES,
        'health': TaskProject.HEALTH_CHOICES,
    }
    queryset = _filter_workplace(
        visible_to(TaskProject.objects.all(), viewer or user).filter(user=user),
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
        'statuses': _choice_options(project_choices['status']),
        'stages': _choice_options(project_choices['stage']),
        'healths': _choice_options(project_choices['health']),
        'companies': companies,
        'responsible_users': responsible_users,
    }


def _empty_project_filter_options(project_choices=None):
    project_choices = project_choices or {
        'status': TaskProject.STATUS_CHOICES,
        'stage': TaskProject.STAGE_CHOICES,
        'health': TaskProject.HEALTH_CHOICES,
    }
    return {
        'statuses': _choice_options(project_choices['status']),
        'stages': _choice_options(project_choices['stage']),
        'healths': _choice_options(project_choices['health']),
        'companies': [],
        'responsible_users': [],
    }


def _project_active_filters(
    *,
    name,
    name_operator,
    code,
    code_operator,
    description,
    description_operator,
    source,
    source_operator,
    priority,
    status,
    stage,
    health,
    company,
    responsible,
    project_choices,
    filter_options,
):
    active_filters = []
    text_filters = (
        ('name', 'name_op', 'Nazwa', 'briefcase-business', name, name_operator),
        ('code', 'code_op', 'Kod', 'hash', code, code_operator),
        ('description', 'description_op', 'Opis', 'align-left', description, description_operator),
        ('source', 'source_op', 'Źródło', 'waypoints', source, source_operator),
    )
    for param, operator_param, label, icon, value, operator in text_filters:
        if not _project_text_filter_is_active(value, operator):
            continue
        operator_label = PROJECT_TEXT_FILTER_OPERATOR_MAP[operator]
        value_label = operator_label
        if operator not in {'is_empty', 'is_not_empty'}:
            value_label = f'{operator_label} „{value}”'
        active_filters.append({
            'param': param,
            'operator_param': operator_param,
            'label': label,
            'value_label': value_label,
            'icon': icon,
        })

    exact_filters = (
        ('priority', 'Priorytet', 'chart-no-axes-column-increasing', priority, _choice_options(TaskProject.PRIORITY_CHOICES)),
        ('status', 'Status', 'circle-dot', status, _choice_options(project_choices['status'])),
        ('stage', 'Etap', 'milestone', stage, _choice_options(project_choices['stage'])),
        ('health', 'Kondycja', 'heart-pulse', health, _choice_options(project_choices['health'])),
        ('company', 'Firma', 'building-2', company, filter_options['companies']),
        ('responsible', 'Odpowiedzialny', 'circle-user-round', responsible, filter_options['responsible_users']),
    )
    for param, label, icon, value, options in exact_filters:
        if not value:
            continue
        option_label = next((option['label'] for option in options if option['value'] == value), value)
        active_filters.append({
            'param': param,
            'operator_param': '',
            'label': label,
            'value_label': option_label,
            'icon': icon,
        })
    return active_filters


def _group_filter_queryset(
    user,
    query='',
    priority='',
    status='',
    kind='',
    project_filter='',
    owner='',
    workplace=None,
    viewer=None,
):
    queryset = visible_to(TaskSection.objects.all(), viewer or user).filter(project__user=user).select_related('project', 'project__user', 'owner')
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
            | Q(code__icontains=query)
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
            queryset=visible_to(TaskSectionNote.objects.all(), viewer or user).select_related('author').order_by('created_at', 'id'),
        )
    )


def _group_sort_queryset(queryset, sort_value, viewer=None):
    sort_value = _group_sort_value(sort_value)
    if sort_value == 'title_asc':
        return queryset.order_by('title', 'id')
    if sort_value == 'title_desc':
        return queryset.order_by('-title', 'id')
    if sort_value == 'code_asc':
        return queryset.order_by('project__code', 'code', 'title', 'id')
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
            last_task_created_sort=Max('tasks__created_at', filter=Q(tasks__in=visible_to(Task.objects.all(), viewer))),
            last_activity_sort=Max('tasks__activities__created_at', filter=Q(tasks__activities__in=visible_to(TaskActivity.objects.all(), viewer))),
        ).order_by('-last_activity_sort', '-last_task_created_sort', '-created_at', 'project__name', 'order', 'id')
    return queryset.order_by('project__name', 'order', 'created_at', 'id')


def _group_filter_options(user, workplace=None, project=None, viewer=None):
    queryset = visible_to(TaskSection.objects.all(), viewer or user).filter(project__user=user).select_related('project', 'owner')
    queryset = _filter_workplace(queryset, workplace, field_name='project__workplace')
    if project is not None:
        queryset = queryset.filter(project=project)
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


def _group_active_filters(*, priority, status, kind, project_filter, owner, filter_options):
    active_filters = []
    exact_filters = (
        ('status', 'Status', 'circle-dot', status, filter_options['statuses']),
        ('kind', 'Typ', 'layers-3', kind, filter_options['kinds']),
        ('group_project', 'Projekt', 'folder-kanban', project_filter, filter_options['projects']),
        ('owner', 'Odpowiedzialny', 'circle-user-round', owner, filter_options['owners']),
        ('priority', 'Priorytet', 'chart-no-axes-column-increasing', priority, _choice_options(TaskSection.PRIORITY_CHOICES)),
    )
    for param, label, icon, value, options in exact_filters:
        if not value:
            continue
        option_label = next((option['label'] for option in options if option['value'] == value), value)
        active_filters.append({
            'param': param,
            'label': label,
            'value_label': option_label,
            'icon': icon,
        })
    return active_filters


def _task_filter_queryset(
    queryset,
    query='',
    priority='',
    status='',
    project_filter='',
    section='',
    assignee='',
    task_type='',
    due='',
):
    query = (query or '').strip()
    if query:
        section_code_number = parse_hierarchy_code_number(query, TaskSection.CODE_PREFIX)
        task_id = _integer_filter_value(query)
        priority_matches = _choice_values_matching_query(Task.PRIORITY_CHOICES, query)
        status_matches = _choice_values_matching_query(Task.STATUS_CHOICES, query)
        type_matches = _choice_values_matching_query(Task.TASK_TYPE_CHOICES, query)
        query_filter = (
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(section__title__icontains=query)
            | Q(section__description__icontains=query)
            | Q(section__code__icontains=query)
            | Q(section__project__name__icontains=query)
            | Q(section__project__code__icontains=query)
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
        if section_code_number:
            query_filter |= Q(section__code_number=section_code_number)
        if priority_matches:
            query_filter |= Q(priority__in=priority_matches)
        if status_matches:
            query_filter |= Q(status__in=status_matches)
        if type_matches:
            query_filter |= Q(task_type__in=type_matches)
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


def _task_filter_options(user, workplace=None, viewer=None):
    queryset = _filter_workplace(
        visible_to(Task.objects.all(), viewer or user).filter(user=user, parent__isnull=True),
        workplace,
    ).select_related('section', 'section__project', 'assignee')
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
    if queryset.filter(assignee__isnull=True).exists():
        assignees.insert(0, {'value': 'none', 'label': 'Brak osoby'})

    return {
        'statuses': _choice_options(Task.STATUS_CHOICES),
        'priorities': _choice_options(Task.PRIORITY_CHOICES),
        'types': _choice_options(Task.TASK_TYPE_CHOICES),
        'due': TASK_DUE_FILTER_OPTIONS,
        'projects': projects,
        'sections': sections,
        'assignees': assignees,
    }


def _task_window_for_request(request, queryset):
    workplace = _active_workplace(request)
    query = (request.GET.get('q') or '').strip()
    priority = (request.GET.get('priority') or '').strip()
    status = (request.GET.get('status') or '').strip()
    project_filter = (request.GET.get('task_project') or '').strip()
    section = (request.GET.get('task_section') or '').strip()
    assignee = (request.GET.get('task_assignee') or '').strip()
    if request.GET.get('view') == 'unassigned-tasks':
        project_filter = ''
        section = ''
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
        task_type,
        due,
        sort != TASK_DEFAULT_SORT,
    ))
    # Count and slice each status separately: the toolbar limit applies to every
    # status, while its page buttons advance the same window in all statuses.
    status_counts = {
        row['status']: row['total']
        for row in (
            visible_to(Task.objects.all(), request.user).filter(pk__in=queryset.order_by().values('pk'))
            .values('status').annotate(total=Count('pk'))
        )
    }
    total_tasks = sum(status_counts.values())
    page_size = _project_page_size(request)
    largest_status_count = max(status_counts.values(), default=0)
    total_pages = max(1, (largest_status_count + page_size - 1) // page_size)
    current_page = min(_project_page_number(request), total_pages)
    offset = (current_page - 1) * page_size
    page_tasks = []
    for task_status, _label in Task.STATUS_CHOICES:
        if status_counts.get(task_status, 0) > offset:
            page_tasks.extend(queryset.filter(status=task_status)[offset:offset + page_size])
    base_params = _request_query_params(request)
    # Status-specific pages belong to the group view, not the combined directory.
    for task_status, _label in Task.STATUS_CHOICES:
        base_params.pop(_task_status_page_param(task_status), None)
        base_params.pop(_task_status_page_size_param(task_status), None)
    base_params.update(page_size=page_size)
    base_params.pop('page', None)
    has_previous = current_page > 1
    has_next = current_page < total_pages
    preceding_tasks = sum(min(offset, count) for count in status_counts.values())
    compact_summary = f'{preceding_tasks + 1}-{preceding_tasks + len(page_tasks)} z {total_tasks}' if total_tasks else '0 z 0'
    return {
        'queryset': page_tasks,
        'page': current_page,
        'page_size': page_size,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'total_pages': total_pages,
        'has_previous': has_previous,
        'has_next': has_next,
        'previous_url': _projects_url({**base_params, 'page': current_page - 1}, base_url=request.path) if has_previous else '',
        'next_url': _projects_url({**base_params, 'page': current_page + 1}, base_url=request.path) if has_next else '',
        'summary': f'Pokazano {compact_summary} zadań' if total_tasks else 'Brak zadań',
        'compact_summary': compact_summary,
        'query': query,
        'priority': priority,
        'status': status,
        'project_filter': project_filter,
        'section': section,
        'assignee': assignee,
        'task_type': task_type,
        'due': due,
        'sort': sort,
        'sort_param': '' if sort == TASK_DEFAULT_SORT else sort,
        'sort_label': TASK_SORT_OPTION_MAP[sort]['label'],
        'sort_direction': TASK_SORT_OPTION_MAP[sort]['direction'],
        'filters': _task_filter_options(workspace_owner(request), workplace=workplace, viewer=request.user),
        'total_tasks': total_tasks,
        'has_active_filters': active_filters,
    }


def _tag_filter_queryset(
    user,
    query='',
    priority='',
    status='',
    category='',
    scope='',
    owner='',
    workplace=None,
):
    queryset = _filter_workplace(TaskTag.objects.filter(user=user), workplace)
    query = (query or '').strip()
    if query:
        priority_matches = _choice_values_matching_query(TaskTag.PRIORITY_CHOICES, query)
        status_matches = _choice_values_matching_query(TaskTag.STATUS_CHOICES, query)
        category_matches = _choice_values_matching_query(TaskTag.CATEGORY_CHOICES, query)
        scope_matches = _choice_values_matching_query(TaskTag.SCOPE_CHOICES, query)
        icon_matches = _choice_values_matching_query(TaskTag.ICON_CHOICES, query)
        query_filter = (
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(code__icontains=query)
            | Q(owner_label__icontains=query)
            | Q(usage_notes__icontains=query)
            | Q(automation_rules__icontains=query)
        )
        if priority_matches:
            query_filter |= Q(priority__in=priority_matches)
        if status_matches:
            query_filter |= Q(status__in=status_matches)
        if category_matches:
            query_filter |= Q(category__in=category_matches)
        if scope_matches:
            query_filter |= Q(scope__in=scope_matches)
        if icon_matches:
            query_filter |= Q(icon__in=icon_matches)
        queryset = queryset.filter(query_filter)
    if priority in {value for value, _label in TaskTag.PRIORITY_CHOICES}:
        queryset = queryset.filter(priority=priority)
    if status in {value for value, _label in TaskTag.STATUS_CHOICES}:
        queryset = queryset.filter(status=status)
    if category in {value for value, _label in TaskTag.CATEGORY_CHOICES}:
        queryset = queryset.filter(category=category)
    if scope in {value for value, _label in TaskTag.SCOPE_CHOICES}:
        queryset = queryset.filter(scope=scope)
    if owner == 'none':
        queryset = queryset.filter(owner_label='')
    elif owner:
        queryset = queryset.filter(
            owner_label=owner
        )
    return queryset.prefetch_related(
        Prefetch(
            'tag_notes',
            queryset=TaskTagNote.objects.select_related('author').order_by('created_at', 'id'),
        )
    )


def _tag_filter_options(user, workplace=None):
    queryset = _filter_workplace(TaskTag.objects.filter(user=user), workplace)
    owners = [
        {'value': row['owner_label'], 'label': row['owner_label']}
        for row in queryset.exclude(owner_label='')
        .values('owner_label')
        .distinct()
        .order_by('owner_label')
    ]
    if queryset.filter(owner_label='').exists():
        owners.insert(0, {'value': 'none', 'label': 'Brak właściciela'})

    return {
        'priorities': _choice_options(TaskTag.PRIORITY_CHOICES),
        'statuses': _choice_options(TaskTag.STATUS_CHOICES),
        'categories': _choice_options(TaskTag.CATEGORY_CHOICES),
        'scopes': _choice_options(TaskTag.SCOPE_CHOICES),
        'owners': owners,
    }


def _empty_tag_filter_options():
    return {
        'priorities': _choice_options(TaskTag.PRIORITY_CHOICES),
        'statuses': _choice_options(TaskTag.STATUS_CHOICES),
        'categories': _choice_options(TaskTag.CATEGORY_CHOICES),
        'scopes': _choice_options(TaskTag.SCOPE_CHOICES),
        'owners': [],
    }


def _tag_task_count_filter(user, workplace, viewer=None):
    task_filter = Q(tasks__pk__in=visible_to(Task.objects.all(), viewer or user), tasks__user=user, tasks__parent__isnull=True)
    task_filter &= Q(tasks__workplace=workplace) if workplace is not None else Q(tasks__workplace__isnull=True)
    return task_filter


def _tag_sort_queryset(queryset, sort_value):
    sort_value = _tag_sort_value(sort_value)
    if sort_value == 'name_desc':
        return queryset.order_by('-name', 'id')
    if sort_value == 'code_asc':
        return queryset.order_by('code', 'name', 'id')
    if sort_value == 'code_desc':
        return queryset.order_by('-code', 'name', 'id')
    if sort_value == 'category_asc':
        return queryset.annotate(
            tag_category_sort_rank=_choice_rank_case('category', TaskTag.CATEGORY_CHOICES)
        ).order_by('tag_category_sort_rank', 'name', 'id')
    if sort_value == 'visual_asc':
        return queryset.order_by('color', 'icon', 'name', 'id')
    if sort_value == 'priority_desc':
        return queryset.annotate(
            tag_priority_sort_rank=_choice_rank_case('priority', TaskTag.PRIORITY_CHOICES)
        ).order_by('-tag_priority_sort_rank', 'name', 'id')
    if sort_value == 'scope_asc':
        return queryset.annotate(
            tag_scope_sort_rank=_choice_rank_case('scope', TaskTag.SCOPE_CHOICES)
        ).order_by('tag_scope_sort_rank', 'name', 'id')
    if sort_value == 'owner_asc':
        return queryset.annotate(
            tag_owner_empty_sort=Case(
                When(owner_label='', then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('tag_owner_empty_sort', 'owner_label', 'name', 'id')
    if sort_value == 'status_asc':
        return queryset.annotate(
            tag_status_sort_rank=_choice_rank_case('status', TaskTag.STATUS_CHOICES)
        ).order_by('tag_status_sort_rank', 'name', 'id')
    if sort_value == 'related_desc':
        return queryset.annotate(
            related_tags_sort=Count('related_tags', distinct=True)
        ).order_by('-related_tags_sort', 'name', 'id')
    if sort_value == 'task_count_desc':
        return queryset.order_by('-total_tasks', 'name', 'id')
    if sort_value == 'created_desc':
        return queryset.order_by('-created_at', 'name', 'id')
    return queryset.order_by('name', 'id')


def _projects_for_user(user, tasks_queryset=None, project_queryset=None, order_by=('name', 'id'), limit=None, offset=0, workplace=None, viewer=None):
    projects_filter = Q(user=user)
    if workplace is not None:
        projects_filter &= Q(workplace=workplace)
    sections_queryset = visible_to(TaskSection.objects.all(), viewer or user).select_related('project', 'project__user', 'owner')
    sections_queryset = _filter_workplace(sections_queryset, workplace, field_name='project__workplace')
    if tasks_queryset is not None:
        sections_queryset = sections_queryset.prefetch_related(
            Prefetch('tasks', queryset=tasks_queryset)
        )

    queryset = (
        (project_queryset if project_queryset is not None else visible_to(TaskProject.objects.all(), viewer or user).filter(projects_filter))
        .distinct()
        .select_related('user', 'company', 'responsible_user')
        .annotate(
            total_tasks=Count(
                'sections__tasks',
                filter=Q(sections__tasks__parent__isnull=True, sections__tasks__in=visible_to(Task.objects.all(), viewer or user)),
            )
        )
        .prefetch_related(
            Prefetch(
                'sections',
                queryset=sections_queryset,
            ),
            Prefetch(
                'project_notes',
                queryset=visible_to(TaskProjectNote.objects.all(), viewer or user).select_related('author').order_by('created_at', 'id'),
            ),
        )
    )
    if order_by:
        queryset = queryset.order_by(*order_by)
    if limit is not None:
        queryset = queryset[offset:offset + limit]
    projects = list(queryset)
    return _mark_project_permissions(projects, user, viewer=viewer or user)


def _project_for_user(user, project_id, workplace=None, viewer=None):
    if not project_id:
        return None
    projects = _projects_for_user(
        user,
        project_queryset=_filter_workplace(visible_to(TaskProject.objects.all(), viewer or user).filter(user=user, id=project_id), workplace),
        order_by=None,
        limit=1,
        workplace=workplace,
        viewer=viewer or user,
    )
    return projects[0] if projects else None


def _project_window_for_request(request, field_configuration=None):
    workplace = _active_workplace(request)
    tab = directory_tab(request)
    field_configuration = field_configuration or _project_field_configuration(workspace_owner(request), workplace, viewer=request.user)
    project_choices = field_configuration['choices']
    page_size = _project_page_size(request)
    requested_page = _project_page_number(request)
    query = (request.GET.get('q') or '').strip()
    name = (request.GET.get('name') or '').strip()
    name_operator = _project_text_filter_operator((request.GET.get('name_op') or '').strip())
    code = (request.GET.get('code') or '').strip()
    code_operator = _project_text_filter_operator((request.GET.get('code_op') or '').strip())
    description = (request.GET.get('description') or '').strip()
    description_operator = _project_text_filter_operator((request.GET.get('description_op') or '').strip())
    source = (request.GET.get('source') or '').strip()
    source_operator = _project_text_filter_operator((request.GET.get('source_op') or '').strip())
    priority = (request.GET.get('priority') or '').strip()
    status = (request.GET.get('status') or '').strip()
    stage = (request.GET.get('stage') or '').strip()
    health = (request.GET.get('health') or '').strip()
    company = (request.GET.get('company') or '').strip()
    responsible = (request.GET.get('responsible') or '').strip()
    sort = _project_sort_value((request.GET.get('sort') or '').strip())
    queryset = _project_filter_queryset(
        workspace_owner(request),
        query=query,
        name=name,
        name_operator=name_operator,
        code=code,
        code_operator=code_operator,
        description=description,
        description_operator=description_operator,
        source=source,
        source_operator=source_operator,
        priority=priority,
        status=status,
        stage=stage,
        health=health,
        company=company,
        responsible=responsible,
        workplace=workplace,
        project_choices=project_choices,
        viewer=request.user,
    )
    queryset = directory_queryset(queryset, request.user, tab)
    queryset = _project_sort_queryset(queryset, sort, project_choices=project_choices, viewer=request.user)
    total_projects = queryset.count()
    total_pages = max(1, (total_projects + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size

    projects = _projects_for_user(
        workspace_owner(request),
        project_queryset=queryset,
        order_by=None,
        limit=page_size,
        offset=offset,
        workplace=workplace,
        viewer=request.user,
    )

    _decorate_project_directory_metrics(projects, viewer=request.user)
    decorate_favorites(projects, request, 'project')
    _decorate_project_field_values(projects, field_configuration)
    _decorate_directory_members(projects, current_user=workspace_owner(request), viewer=request.user)

    filter_options = _project_filter_options(
        workspace_owner(request),
        workplace=workplace,
        project_choices=project_choices,
        viewer=request.user,
    )
    active_filters = _project_active_filters(
        name=name,
        name_operator=name_operator,
        code=code,
        code_operator=code_operator,
        description=description,
        description_operator=description_operator,
        source=source,
        source_operator=source_operator,
        priority=priority,
        status=status,
        stage=stage,
        health=health,
        company=company,
        responsible=responsible,
        project_choices=project_choices,
        filter_options=filter_options,
    )

    base_params = {
        'tab': tab,
        'q': query,
        'name': name,
        'name_op': name_operator if _project_text_filter_is_active(name, name_operator) and name_operator != 'contains' else '',
        'code': code,
        'code_op': code_operator if _project_text_filter_is_active(code, code_operator) and code_operator != 'contains' else '',
        'description': description,
        'description_op': description_operator if _project_text_filter_is_active(description, description_operator) and description_operator != 'contains' else '',
        'source': source,
        'source_op': source_operator if _project_text_filter_is_active(source, source_operator) and source_operator != 'contains' else '',
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
        previous_url = _projects_url(previous_page_params, base_url=request.path)
    if has_next:
        next_url = _projects_url({**base_params, 'page': current_page + 1}, base_url=request.path)

    first_visible = 0
    last_visible = 0
    if not projects:
        summary = 'Brak projektów'
    else:
        first_visible = offset + 1
        last_visible = offset + len(projects)
        summary = f'Pokazano {first_visible}-{last_visible} z {total_projects} projektów'

    return {
        'projects': projects,
        'tab': tab,
        'query': query,
        'name': name,
        'name_operator': name_operator,
        'name_operator_param': base_params['name_op'],
        'code': code,
        'code_operator': code_operator,
        'code_operator_param': base_params['code_op'],
        'description': description,
        'description_operator': description_operator,
        'description_operator_param': base_params['description_op'],
        'source': source,
        'source_operator': source_operator,
        'source_operator_param': base_params['source_op'],
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
        'sort_field': sort.rsplit('_', 1)[0],
        'filters': filter_options,
        'active_filters': active_filters,
        'active_filter_count': len(active_filters),
        'has_active_filters': bool(active_filters),
        'page': current_page,
        'total_pages': total_pages,
        'total_projects': total_projects,
        'page_size': page_size,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'page_items': _project_page_items(current_page, total_pages, base_params, base_url=request.path) if total_projects else [],
        'has_previous': has_previous,
        'has_next': has_next,
        'previous_url': previous_url,
        'next_url': next_url,
        'summary': summary,
        'compact_summary': f'{first_visible}-{last_visible} z {total_projects}',
    }


def _group_window_for_request(request, field_configuration=None, project=None):
    workplace = _active_workplace(request)
    tab = directory_tab(request) if project is None else None
    page_size = _project_page_size(request)
    requested_page = _project_page_number(request)
    query = (request.GET.get('q') or '').strip()
    priority = (request.GET.get('priority') or '').strip()
    status = (request.GET.get('status') or '').strip()
    kind = (request.GET.get('kind') or '').strip()
    project_filter = '' if project is not None else (request.GET.get('group_project') or '').strip()
    owner = (request.GET.get('owner') or '').strip()
    sort = _group_sort_value((request.GET.get('sort') or '').strip())
    queryset = _group_filter_queryset(
        workspace_owner(request),
        query=query,
        priority=priority,
        status=status,
        kind=kind,
        project_filter=project_filter,
        owner=owner,
        workplace=workplace,
        viewer=request.user,
    )
    if project is not None:
        queryset = queryset.filter(project=project)
    else:
        queryset = directory_queryset(queryset, request.user, tab)
    queryset = _group_sort_queryset(queryset, sort, viewer=request.user)
    total_groups = queryset.count()
    total_pages = max(1, (total_groups + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size

    sections = list(queryset[offset:offset + page_size])
    if project is None:
        decorate_favorites(sections, request, 'section')
    _decorate_group_directory_rows(sections, current_user=workspace_owner(request), viewer=request.user)
    if field_configuration:
        _decorate_project_field_values(
            [section.project for section in sections],
            field_configuration,
        )

    base_params = {
        **({'project': project.id} if project is not None else {'view': 'all-groups'}),
        'tab': tab,
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
        previous_url = _projects_url(previous_page_params, base_url=request.path)
    if has_next:
        next_url = _projects_url({**base_params, 'page': current_page + 1}, base_url=request.path)

    if not sections:
        summary = 'Brak grup'
        compact_summary = '0 z 0'
    else:
        first_visible = offset + 1
        last_visible = offset + len(sections)
        summary = f'Pokazano {first_visible}-{last_visible} z {total_groups} grup'
        compact_summary = f'{first_visible}-{last_visible} z {total_groups}'

    filter_options = _group_filter_options(workspace_owner(request), workplace=workplace, project=project, viewer=request.user)
    active_filters = _group_active_filters(
        priority=priority,
        status=status,
        kind=kind,
        project_filter=project_filter,
        owner=owner,
        filter_options=filter_options,
    )

    return {
        'sections': sections,
        'tab': tab,
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
        'filters': filter_options,
        'active_filters': active_filters,
        'active_filter_count': len(active_filters),
        'has_active_filters': bool(active_filters),
        'page': current_page,
        'total_pages': total_pages,
        'total_groups': total_groups,
        'page_size': page_size,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'page_items': _project_page_items(current_page, total_pages, base_params, base_url=request.path) if total_groups else [],
        'has_previous': has_previous,
        'has_next': has_next,
        'previous_url': previous_url,
        'next_url': next_url,
        'summary': summary,
        'compact_summary': compact_summary,
    }


def _tag_window_for_request(request):
    workplace = _active_workplace(request)
    page_size = _project_page_size(request)
    requested_page = _project_page_number(request)
    query = (request.GET.get('q') or '').strip()
    priority = (request.GET.get('priority') or '').strip()
    status = (request.GET.get('status') or '').strip()
    category = (request.GET.get('category') or '').strip()
    scope = (request.GET.get('scope') or '').strip()
    owner = (request.GET.get('owner') or '').strip()
    sort = _tag_sort_value((request.GET.get('sort') or '').strip())
    queryset = _tag_filter_queryset(
        workspace_owner(request),
        query=query,
        priority=priority,
        status=status,
        category=category,
        scope=scope,
        owner=owner,
        workplace=workplace,
    ).annotate(
        total_tasks=Count(
            'tasks',
            filter=_tag_task_count_filter(workspace_owner(request), workplace, viewer=request.user),
            distinct=True,
        )
    )
    queryset = _tag_sort_queryset(queryset, sort)
    total_tags = queryset.count()
    total_pages = max(1, (total_tags + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size

    tags = list(
        queryset.prefetch_related('related_tags')[offset:offset + page_size]
    )
    for tag in tags:
        related_tags = list(tag.related_tags.all())
        tag.related_tag_ids = ','.join(str(related_tag.id) for related_tag in related_tags)
        tag.related_tags_label = ', '.join(related_tag.name for related_tag in related_tags) or 'Brak powiązań'

    base_params = {
        'view': 'tags',
        'q': query,
        'priority': priority,
        'status': status,
        'category': category,
        'scope': scope,
        'owner': owner,
        'sort': '' if sort == TAG_DEFAULT_SORT else sort,
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
        'priority': priority,
        'status': status,
        'category': category,
        'scope': scope,
        'owner': owner,
        'sort': sort,
        'sort_param': '' if sort == TAG_DEFAULT_SORT else sort,
        'sort_label': TAG_SORT_OPTION_MAP[sort]['label'],
        'sort_direction': TAG_SORT_OPTION_MAP[sort]['direction'],
        'filters': _tag_filter_options(workspace_owner(request), workplace=workplace),
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
        'compact_summary': f'{offset + 1}-{offset + len(tags)} z {total_tags}' if tags else '0 z 0',
    }


def _navigation_projects_for_user(user, active_project=None, workplace=None, viewer=None):
    projects = _projects_for_user(user, limit=PROJECT_NAVIGATION_LIMIT, workplace=workplace, viewer=viewer or user)
    if active_project and all(project.id != active_project.id for project in projects):
        projects = [active_project, *projects]
    return projects


def _navigation_project_ids_for_user(user, active_project=None, workplace=None, viewer=None):
    project_ids = list(
        _filter_workplace(visible_to(TaskProject.objects.all(), viewer or user).filter(user=user), workplace)
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
            }
            for section in project.sections.all()
            if getattr(section, 'can_edit', False)
        ]
        if not (getattr(project, 'can_edit', False) or getattr(project, 'has_editable_sections', False) or sections):
            continue

        options.append({
            'projectId': str(project.id),
            'projectName': project.name,
            'defaultSectionId': '',
            'sections': sections,
        })
    return options


def _polish_count_label(value, singular, paucal, plural):
    count = int(value or 0)
    last_digit = count % 10
    last_two_digits = count % 100
    if count == 1:
        label = singular
    elif 2 <= last_digit <= 4 and not 12 <= last_two_digits <= 14:
        label = paucal
    else:
        label = plural
    return f'{count} {label}'


def _decorate_project_directory_metrics(projects, viewer=None):
    if not projects:
        return

    today = timezone.localdate()
    section_ids = []
    for project in projects:
        for section in project.sections.all():
            section_ids.append(section.id)

    metrics_by_section = {}
    if section_ids:
        metrics_by_section = {
            row['section_id']: row
            for row in (
                visible_to(Task.objects.all(), viewer).filter(section_id__in=section_ids, parent__isnull=True)
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
        project.groups_total_count = len(project.sections.all())
        project.groups_count_label = _polish_count_label(project.groups_total_count, 'grupa', 'grupy', 'grup')
        if not project.due_at:
            project.due_highlight = 'none'
        elif project.status == 'completed':
            project.due_highlight = 'completed'
        elif project.status == 'cancelled':
            project.due_highlight = 'inactive'
        else:
            days_until_due = (project.due_at - today).days
            if days_until_due < 0:
                project.due_highlight = 'overdue'
            elif days_until_due <= 7:
                project.due_highlight = 'soon'
            else:
                project.due_highlight = 'scheduled'

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
        project.tasks_total_count_label = _polish_count_label(project_total_tasks, 'zadanie', 'zadania', 'zadań')
        project.progress_percent = project_progress_percent
        project.last_activity_at = max(
            (value for value in last_activity_candidates if value),
            default=project.created_at,
        )


def _decorate_group_directory_rows(sections, current_user=None, viewer=None):
    if not sections:
        return

    today = timezone.localdate()
    section_ids = [section.id for section in sections]
    editable_ids = set(editable_to(TaskSection.objects.filter(pk__in=section_ids), viewer or current_user).values_list('pk', flat=True))
    metrics_by_section = {
        row['section_id']: row
        for row in (
            visible_to(Task.objects.all(), viewer or current_user).filter(section_id__in=section_ids, parent__isnull=True)
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
        if not section.due_at:
            section.due_highlight = 'none'
        elif section.status == 'closed':
            section.due_highlight = 'completed'
        else:
            days_until_due = (section.due_at - today).days
            if days_until_due < 0:
                section.due_highlight = 'overdue'
            elif days_until_due <= 7:
                section.due_highlight = 'soon'
            else:
                section.due_highlight = 'scheduled'

        project = section.project
        can_manage_project = project.user_id == getattr(current_user, 'id', None) and section.pk in editable_ids
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


def _decorate_directory_members(projects, current_user=None, viewer=None):
    if not projects:
        return

    editable_ids = set(editable_to(TaskProject.objects.filter(pk__in=[project.pk for project in projects]), viewer or current_user).values_list('pk', flat=True))
    section_ids = [section.pk for project in projects for section in project.sections.all()]
    editable_sections = set(editable_to(TaskSection.objects.filter(pk__in=section_ids), viewer or current_user).values_list('pk', flat=True))
    for project in projects:
        can_manage_project = project.user_id == getattr(current_user, 'id', None) and project.pk in editable_ids
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
            section.can_manage = can_manage_project and section.pk in editable_sections
            section.can_share = False
            section.can_edit = section.can_manage
            if section.can_edit:
                project.has_editable_sections = True
            _assign_directory_members(
                section,
                [
                    {'user': project.user, 'role': 'Właściciel', 'permission': 'owner'},
                ],
            )


def _decorate_task_directory_members(tasks, current_user=None, viewer=None):
    task_list = [task for task in tasks if task]
    if not task_list:
        return

    editable_ids = set(editable_to(Task.objects.filter(pk__in=[task.pk for task in task_list]), viewer or current_user).values_list('pk', flat=True))
    for task in task_list:
        can_manage_task = task.user_id == getattr(current_user, 'id', None) and task.pk in editable_ids
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


def _tasks_navigation_context(user, active_section=None, active_view=None, workplace=None, viewer=None):
    tasks_qs = _filter_workplace(
        visible_to(Task.objects.all(), viewer or user).filter(user=user, parent__isnull=True),
        workplace,
    ).select_related('section', 'section__project', 'assignee').prefetch_related('tags').annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        tags_total=Count('tags', distinct=True),
        attachments_total=Count('attachments', distinct=True),
    ).order_by('is_closed_sort', 'task_id')

    active_project = _project_for_user(user, active_section.project_id, workplace=workplace, viewer=viewer or user) if active_section else None
    if active_section:
        active_section = next((section for section in active_project.sections.all() if section.id == active_section.id), active_section)

    if active_view is None:
        active_view = 'section' if active_section else 'projects'

    navigation_projects = _navigation_projects_for_user(user, active_project=active_project, workplace=workplace, viewer=viewer or user)
    _decorate_project_directory_metrics(navigation_projects, viewer=viewer or user)
    _decorate_directory_members(navigation_projects, current_user=user, viewer=viewer or user)

    can_create_issue = _user_can_create_issue(
        user,
        active_project=active_project,
        active_section=active_section,
        workplace=workplace,
        viewer=viewer or user,
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
            total_tasks=Count('tasks', filter=_tag_task_count_filter(user, workplace, viewer=viewer))
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
    task.save(update_fields=['status', 'is_completed', 'completion_date'])
    return True


@transaction.atomic
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
        'visibility': task.visibility,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'task_type': task.task_type,
        'section_id': task.section_id,
        'section_label': section.title if section else '',
        'project_id': project.id if project else None,
        'project_label': project.name if project else '',
        'parent_id': task.parent_id,
        'assignee_id': task.assignee_id,
        'assignee_label': _user_display_name(task.assignee) if task.assignee_id else '',
        'due_at': task.due_at,
        'reminder_at': task.reminder_at,
        'completion_date': task.completion_date,
        'tags': set(task.tags.values_list('id', flat=True)),
        'tag_labels': list(task.tags.order_by('name').values_list('name', flat=True)),
    }


def _task_change_activities(task, before):
    status_labels = dict(Task.STATUS_CHOICES)
    priority_labels = dict(Task.PRIORITY_CHOICES)
    task_type_labels = dict(Task.TASK_TYPE_CHOICES)
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

    if before['visibility'] != task.visibility:
        add_change('widoczność', {'public': 'Publiczne', 'private': 'Prywatne'}[before['visibility']], {'public': 'Publiczne', 'private': 'Prywatne'}[task.visibility])
    if before['status'] != task.status:
        add_change('status', status_labels.get(before['status'], before['status']), task.get_status_display())
    if before['priority'] != task.priority:
        add_change('priorytet', priority_labels.get(before['priority'], before['priority']), task.get_priority_display())
    if before['task_type'] != task.task_type:
        add_change('typ zadania', task_type_labels.get(before['task_type'], before['task_type']), task.get_task_type_display())
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
    if before['due_at'] != task.due_at:
        add_change('termin wykonania', before['due_at'], task.due_at)
    if before['reminder_at'] != task.reminder_at:
        add_change('przypomnienie', before['reminder_at'], task.reminder_at)
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
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


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
    if request.method == 'GET' and request.GET.get('field_settings') == '1':
        return redirect('project_field_settings')
    return _tasks_page(request)


@login_required
def task_group(request, section_id):
    active_section = get_object_or_404(
        _filter_workplace(
            visible_to(TaskSection.objects.all(), request.user).select_related('project', 'project__user'),
            _active_workplace(request),
            field_name='project__workplace',
        ),
        id=section_id,
    )
    if not _user_can_access_section(workspace_owner(request), active_section):
        raise PermissionDenied
    return _tasks_page(request, active_section=active_section)


def _tasks_page(request, active_section=None):
    workplace = _active_workplace(request)
    if request.method == 'POST' and request.POST.get('action') == 'save_project_template':
        project_id = request.POST.get('project_id', '')
        if not project_id.isdecimal() or len(project_id) > 18:
            raise Http404
        project = get_object_or_404(
            editable_to(TaskProject.objects.all(), request.user), user=workspace_owner(request), workplace=workplace, pk=int(project_id),
        )
        try:
            save_project_template(project, request.user)
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, 'Szablon projektu zapisany.')
        return redirect(scoped_workplace_app_path(workplace, 'tasks', 'templates/'))

    project_field_configuration = _project_field_configuration(workspace_owner(request), workplace, viewer=request.user)
    project_form = TaskProjectForm(
        user=workspace_owner(request),
        workplace=workplace,
        field_options=project_field_configuration['options'],
        viewer=request.user,
    )
    section_form = TaskSectionForm(user=workspace_owner(request), workplace=workplace, viewer=request.user)
    tag_form = TaskTagForm(user=workspace_owner(request), workplace=workplace)
    all_tasks_view = request.GET.get('view') == 'all-tasks' and not active_section
    my_tasks_view = request.GET.get('view') == 'my-tasks' and not active_section
    unassigned_tasks_view = request.GET.get('view') == 'unassigned-tasks' and not active_section
    all_groups_view = request.GET.get('view') == 'all-groups' and not active_section
    tags_view = request.GET.get('view') == 'tags' and not active_section
    shared_tasks_view = False
    shared_groups_view = False
    shared_projects_view = False
    active_project_id = request.POST.get('project_id') if request.method == 'POST' else request.GET.get('project')
    if (
        all_tasks_view
        or my_tasks_view
        or unassigned_tasks_view
        or all_groups_view
        or tags_view
        or shared_tasks_view
        or shared_groups_view
        or shared_projects_view
    ):
        active_project_id = None
    if active_section:
        active_project_id = active_section.project_id
    active_project_for_form = _task_creation_project_for_user(workspace_owner(request), active_project_id, workplace=workplace, viewer=request.user)
    project_option_ids_for_form = _navigation_project_ids_for_user(
        workspace_owner(request),
        active_project=active_project_for_form,
        workplace=workplace,
        viewer=request.user,
    )
    task_modal_sections = _editable_sections_queryset(workspace_owner(request), workplace, viewer=request.user)
    task_modal_sections = task_modal_sections.filter(project_id__in=project_option_ids_for_form)
    task_modal_form = TaskModalForm(
        user=workspace_owner(request),
        workplace=workplace,
        sections_queryset=task_modal_sections,
        viewer=request.user,
    )
    project_modal_open = False
    if request.method == 'GET' and request.GET.get('template'):
        template_id = request.GET['template']
        if not template_id.isdecimal() or len(template_id) > 18:
            raise Http404
        selected_template = get_object_or_404(
            visible_to(TaskProjectTemplate.objects.all(), request.user), user=workspace_owner(request), workplace=workplace,
            pk=int(template_id),
        )
        project_form.initial.update(template=selected_template.pk, name=selected_template.name,
                                    description=selected_template.description)
        project_modal_open = True
    project_rename_modal_open = False
    project_rename_form = TaskProjectRenameForm(
        user=workspace_owner(request),
        workplace=workplace,
        field_options=project_field_configuration['options'],
        viewer=request.user,
    )
    project_rename_project_id = ''
    section_create_modal_open = False
    section_create_project_id = active_project_id or ''
    section_rename_modal_open = False
    section_rename_form = TaskSectionRenameForm(user=workspace_owner(request), workplace=workplace, viewer=request.user)
    section_rename_section_id = ''
    task_modal_open = False
    tag_modal_open = False
    tag_edit_mode = False
    tag_edit_tag_id = ''

    if request.method == 'POST':
        action = request.POST.get('action')
        is_ajax = _is_ajax_request(request)

        if action == 'create_project':
            project_form = TaskProjectForm(
                request.POST,
                user=workspace_owner(request),
                workplace=workplace,
                field_options=project_field_configuration['options'],
                viewer=request.user,
            )
            with transaction.atomic():
                if workplace:
                    Workplace.objects.select_for_update().get(pk=workplace.pk)
                if project_form.is_valid():
                    with transaction.atomic():
                        project = project_form.save(commit=False)
                        project.user = workspace_owner(request)
                        project.workplace = workplace
                        project.save()
                        project_form.save_m2m()
                        template = project_form.cleaned_data.get('template')
                        if template:
                            populate_project_from_template(project, template, request.user)
                        else:
                            section_title = project_form.cleaned_data.get('section_title') or 'Nowa Grupa'
                            section_code = project_form.cleaned_data.get('section_code') or ''
                            TaskSection.objects.create(
                                project=project, title=section_title, code=section_code,
                                kind='custom', order=0,
                            )
                    messages.success(request, 'Projekt dodany.')
                    project_base_url = (scoped_workplace_app_path(workplace, 'tasks')
                                        if request.resolver_match.namespace == 'workplace_tasks' else reverse('tasks:tasks'))
                    return redirect(f'{project_base_url}?project={project.id}')
            project_modal_open = True
            messages.error(request, 'Nie udało się dodać projektu.')

        if action == 'delete_project':
            project_ids = _posted_ids(request, 'project_ids', 'project_id')
            projects_to_delete = _filter_workplace(visible_to(TaskProject.objects.all(), request.user).filter(id__in=project_ids, user=workspace_owner(request)), workplace)
            require_editable(projects_to_delete, request.user)
            if not projects_to_delete.exists():
                get_object_or_404(_filter_workplace(editable_to(TaskProject.objects.all(), request.user).filter(user=workspace_owner(request)), workplace), id=request.POST.get('project_id'))
            project_count = projects_to_delete.count()
            task_count = _filter_workplace(visible_to(Task.objects.all(), request.user).filter(section__project__in=projects_to_delete, user=workspace_owner(request)), workplace).count()
            with lock_task_numbers(workspace_owner(request).pk):
                require_deletable_tasks(Task.objects.filter(section__project__in=projects_to_delete), request.user)
                require_editable(TaskSection.objects.filter(project__in=projects_to_delete), request.user)
                projects_to_delete.delete()
                Task._renumber_user_tasks(workspace_owner(request), workplace)
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
            with transaction.atomic():
                if workplace:
                    Workplace.objects.select_for_update().get(pk=workplace.pk)
                project = get_object_or_404(_filter_workplace(editable_to(TaskProject.objects.select_for_update(), request.user).filter(user=workspace_owner(request)), workplace), id=request.POST.get('project_id'))
                project_rename_form = TaskProjectRenameForm(
                    request.POST,
                    instance=project,
                    user=workspace_owner(request),
                    workplace=workplace,
                    field_options=project_field_configuration['options'],
                    viewer=request.user,
                )
                if project_rename_form.is_valid():
                    project_rename_form.save()
                    messages.success(request, 'Projekt zaktualizowany.')
                    return redirect('tasks:tasks')
            project_rename_modal_open = True
            project_rename_project_id = project.id
            active_project_for_form = project
            messages.error(request, 'Nie udało się zaktualizować projektu.')

        if action in ('add_project_note', 'update_project_notes'):
            project = get_object_or_404(_filter_workplace(editable_to(TaskProject.objects.all(), request.user).filter(user=workspace_owner(request)), workplace), id=request.POST.get('project_id'))
            message = (request.POST.get('message') or request.POST.get('description') or '').strip()
            is_ajax_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if message:
                note = TaskProjectNote.objects.create(project=project, author=request.user, message=message)
                if is_ajax_request:
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Notatka dodana.',
                        'note_html': render_to_string(
                            'tasks/includes/project_note_item.html',
                            {
                                'note': note,
                                'project': project,
                                'next_url': _tasks_next_url(request),
                            },
                            request=request,
                        ),
                    })
                messages.success(request, 'Notatka dodana.')
            else:
                if is_ajax_request:
                    return JsonResponse({'status': 'error', 'message': 'Wpisz treść notatki.'}, status=400)
                messages.error(request, 'Wpisz treść notatki.')
            return redirect(_tasks_next_url(request))

        if action == 'edit_project_note':
            note_queryset = _filter_workplace(
                editable_to(TaskProjectNote.objects.all(), request.user).filter(author=request.user, project__user=workspace_owner(request)),
                workplace,
                field_name='project__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), project_id=request.POST.get('project_id'))
            message = (request.POST.get('message') or '').strip()
            is_ajax_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if message:
                note.message = message
                note.edited_at = timezone.now()
                note.save(update_fields=['message', 'updated_at', 'edited_at'])
                if is_ajax_request:
                    edited_at = timezone.localtime(note.edited_at)
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Notatka zaktualizowana.',
                        'note': {
                            'message': note.message,
                            'edited_at': edited_at.isoformat(),
                            'edited_at_label': edited_at.strftime('%d.%m.%Y, %H:%M'),
                        },
                    })
                messages.success(request, 'Notatka zaktualizowana.')
            else:
                if is_ajax_request:
                    return JsonResponse({'status': 'error', 'message': 'Wpisz treść notatki.'}, status=400)
                messages.error(request, 'Wpisz treść notatki.')
            return redirect(_tasks_next_url(request))

        if action == 'delete_project_note':
            note_queryset = _filter_workplace(
                editable_to(TaskProjectNote.objects.all(), request.user).filter(author=request.user, project__user=workspace_owner(request)),
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
                    editable_to(TaskSection.objects.all(), request.user).filter(project__user=workspace_owner(request)),
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
                editable_to(TaskSectionNote.objects.all(), request.user).filter(author=request.user, section__project__user=workspace_owner(request)),
                workplace,
                field_name='section__project__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), section_id=request.POST.get('section_id'))
            message = (request.POST.get('message') or '').strip()
            is_ajax_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if message:
                note.message = message
                note.edited_at = timezone.now()
                note.save(update_fields=['message', 'updated_at', 'edited_at'])
                if is_ajax_request:
                    edited_at = timezone.localtime(note.edited_at)
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Notatka zaktualizowana.',
                        'note': {
                            'message': note.message,
                            'edited_at': edited_at.isoformat(),
                            'edited_at_label': edited_at.strftime('%d.%m.%Y, %H:%M'),
                        },
                    })
                messages.success(request, 'Notatka zaktualizowana.')
            else:
                if is_ajax_request:
                    return JsonResponse({'status': 'error', 'message': 'Wpisz treść notatki.'}, status=400)
                messages.error(request, 'Wpisz treść notatki.')
            return redirect(_tasks_next_url(request))

        if action == 'delete_section_note':
            note_queryset = _filter_workplace(
                editable_to(TaskSectionNote.objects.all(), request.user).filter(author=request.user, section__project__user=workspace_owner(request)),
                workplace,
                field_name='section__project__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), section_id=request.POST.get('section_id'))
            note.delete()
            messages.success(request, 'Notatka usunięta.')
            return redirect(_tasks_next_url(request))

        if action == 'create_section':
            project = get_object_or_404(_filter_workplace(editable_to(TaskProject.objects.all(), request.user).filter(user=workspace_owner(request)), workplace), id=request.POST.get('project_id'))
            section_form = TaskSectionForm(request.POST, user=workspace_owner(request), project=project, viewer=request.user)
            if section_form.is_valid():
                section = section_form.save(commit=False)
                section.project = project
                section.order = project.sections.count()
                section.save()
                section_form.save_m2m()
                messages.success(request, 'Grupa dodana.')
                return redirect('tasks:task_group', section_id=section.id)
            section_create_modal_open = True
            section_create_project_id = project.id
            messages.error(request, 'Nie udało się dodać grupy.')

        if action == 'create_tag':
            tag_form = TaskTagForm(request.POST, user=workspace_owner(request), workplace=workplace)
            if tag_form.is_valid():
                tag_name = tag_form.cleaned_data['name']
                if _filter_workplace(TaskTag.objects.filter(user=workspace_owner(request), name__iexact=tag_name), workplace).exists():
                    tag_form.add_error('name', 'Taki tag już istnieje.')
                else:
                    tag = tag_form.save(commit=False)
                    tag.user = workspace_owner(request)
                    tag.workplace = workplace
                    tag.save()
                    tag_form.save_m2m()
                    messages.success(request, 'Tag dodany.')
                    return redirect(f"{reverse('tasks:tasks')}?view=tags")
            tag_modal_open = True
            messages.error(request, 'Nie udało się dodać tagu.')

        if action == 'edit_tag':
            tag = get_object_or_404(_filter_workplace(TaskTag.objects.filter(user=workspace_owner(request)), workplace), id=request.POST.get('tag_id'))
            tag_form = TaskTagForm(request.POST, instance=tag, user=workspace_owner(request), workplace=workplace)
            if tag_form.is_valid():
                tag_name = tag_form.cleaned_data['name']
                if _filter_workplace(TaskTag.objects.filter(user=workspace_owner(request), name__iexact=tag_name), workplace).exclude(pk=tag.pk).exists():
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
                _filter_workplace(TaskTag.objects.filter(user=workspace_owner(request)), workplace),
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
                TaskTagNote.objects.filter(author=request.user, tag__user=workspace_owner(request)),
                workplace,
                field_name='tag__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), tag_id=request.POST.get('tag_id'))
            message = (request.POST.get('message') or '').strip()
            is_ajax_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if message:
                note.message = message
                note.edited_at = timezone.now()
                note.save(update_fields=['message', 'updated_at', 'edited_at'])
                if is_ajax_request:
                    edited_at = timezone.localtime(note.edited_at)
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Notatka zaktualizowana.',
                        'note': {
                            'message': note.message,
                            'edited_at': edited_at.isoformat(),
                            'edited_at_label': edited_at.strftime('%d.%m.%Y, %H:%M'),
                        },
                    })
                messages.success(request, 'Notatka zaktualizowana.')
            else:
                if is_ajax_request:
                    return JsonResponse({'status': 'error', 'message': 'Wpisz treść notatki.'}, status=400)
                messages.error(request, 'Wpisz treść notatki.')
            return redirect(_tasks_next_url(request))

        if action == 'delete_tag_note':
            note_queryset = _filter_workplace(
                TaskTagNote.objects.filter(author=request.user, tag__user=workspace_owner(request)),
                workplace,
                field_name='tag__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), tag_id=request.POST.get('tag_id'))
            note.delete()
            messages.success(request, 'Notatka usunięta.')
            return redirect(_tasks_next_url(request))

        if action == 'delete_tag':
            tag_ids = _posted_ids(request, 'tag_ids', 'tag_id')
            tags_to_delete = _filter_workplace(TaskTag.objects.filter(id__in=tag_ids, user=workspace_owner(request)), workplace)
            if not tags_to_delete.exists():
                get_object_or_404(_filter_workplace(TaskTag.objects.filter(user=workspace_owner(request)), workplace), id=request.POST.get('tag_id'))
            tag_count = tags_to_delete.count()
            tags_to_delete.delete()
            if tag_count == 1:
                messages.success(request, 'Tag usunięty.')
            else:
                messages.success(request, f'Usunięto tagi ({tag_count}).')
            return redirect(f"{reverse('tasks:tasks')}?view=tags")

        if action in ('edit_section', 'rename_section'):
            with transaction.atomic():
                if workplace:
                    Workplace.objects.select_for_update().get(pk=workplace.pk)
                section = get_object_or_404(
                    _filter_workplace(editable_to(TaskSection.objects.select_for_update(), request.user).filter(project__user=workspace_owner(request)), workplace, field_name='project__workplace'),
                    id=request.POST.get('section_id'),
                )
                section_rename_form = TaskSectionRenameForm(request.POST, instance=section, user=workspace_owner(request), project=section.project, viewer=request.user)
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
                visible_to(TaskSection.objects.all(), request.user).filter(id__in=section_ids, project__user=workspace_owner(request)),
                workplace,
                field_name='project__workplace',
            )
            require_editable(sections_to_delete, request.user)
            if not sections_to_delete.exists():
                get_object_or_404(
                    _filter_workplace(editable_to(TaskSection.objects.all(), request.user).filter(project__user=workspace_owner(request)), workplace, field_name='project__workplace'),
                    id=request.POST.get('section_id'),
                )
            section_count = sections_to_delete.count()
            project_id = sections_to_delete.values_list('project_id', flat=True).first()
            task_count = _filter_workplace(visible_to(Task.objects.all(), request.user).filter(section__in=sections_to_delete, user=workspace_owner(request)), workplace).count()
            with lock_task_numbers(workspace_owner(request).pk):
                require_deletable_tasks(Task.objects.filter(section__in=sections_to_delete), request.user)
                sections_to_delete.delete()
                Task._renumber_user_tasks(workspace_owner(request), workplace)
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
                    editable_to(TaskSection.objects.all(), request.user).select_related('project', 'project__user'),
                    workplace,
                    field_name='project__workplace',
                ),
                id=request.POST.get('section_id'),
            )
            if not _user_can_create_task_in_section(workspace_owner(request), section):
                raise PermissionDenied
            form = QuickTaskForm(request.POST)
            if form.is_valid():
                task = form.save(commit=False)
                task.user = section.project.user
                task.section = section
                task.workplace = workplace
                task.visibility = 'private'
                task.private_owner = request.user
                task._activity_actor = request.user
                task.save()
                messages.success(request, 'Zadanie dodane.')
                return redirect('tasks:task_group', section_id=section.id)
            messages.error(request, 'Nie udało się dodać zadania.')

        if action == 'create_task_modal':
            project = None
            project_id = request.POST.get('project_id')
            if project_id:
                project = _task_creation_project_for_user(workspace_owner(request), project_id, workplace=workplace, viewer=request.user)
                if not project:
                    raise PermissionDenied
            task_modal_sections = _editable_sections_queryset(workspace_owner(request), workplace, viewer=request.user)
            if project:
                task_modal_sections = task_modal_sections.filter(project=project)
            task_modal_form = TaskModalForm(
                request.POST,
                user=workspace_owner(request),
                workplace=workplace,
                project=project,
                sections_queryset=task_modal_sections,
                viewer=request.user,
            )
            if task_modal_form.is_valid():
                task = task_modal_form.save(commit=False)
                if task.section_id and not _user_can_create_task_in_section(workspace_owner(request), task.section):
                    raise PermissionDenied
                task.user = workspace_owner(request)
                task.workplace = workplace
                task._activity_actor = request.user
                task.save()
                task_modal_form.save_m2m()
                task.activities.filter(action='created').update(metadata={'title': task.title})
                messages.success(request, 'Zadanie dodane.')
                if task.section_id:
                    return redirect('tasks:task_group', section_id=task.section_id)
                tasks_url = (scoped_workplace_app_path(workplace, 'tasks')
                             if request.resolver_match.namespace == 'workplace_tasks' else reverse('tasks:tasks'))
                return redirect(f'{tasks_url}?view=unassigned-tasks')
            task_modal_open = True
            messages.error(request, 'Nie udało się dodać zadania.')

    tasks_qs = _filter_workplace(
        visible_to(Task.objects.all(), request.user).filter(user=workspace_owner(request), parent__isnull=True),
        workplace,
    ).select_related('section', 'section__project', 'assignee').prefetch_related('tags').annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        tags_total=Count('tags', distinct=True),
        attachments_total=Count('attachments', distinct=True),
    ).order_by('is_closed_sort', 'task_id')

    active_project_id = str(active_section.project_id) if active_section else active_project_id
    active_project = _project_for_user(workspace_owner(request), active_project_id, workplace=workplace, viewer=request.user) if active_project_id else None
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
    elif unassigned_tasks_view:
        active_view = 'unassigned_tasks'
    elif all_tasks_view:
        active_view = 'all_tasks'
    else:
        active_view = 'projects'

    if my_tasks_view:
        tasks_qs = tasks_qs.filter(assignee=request.user)
    elif unassigned_tasks_view:
        tasks_qs = tasks_qs.filter(section__isnull=True)
    if active_view == 'all_tasks':
        tasks_qs = directory_queryset(tasks_qs, request.user, directory_tab(request))

    project_window = _project_window_for_request(
        request,
        field_configuration=project_field_configuration,
    ) if active_view == 'projects' else {
        'projects': [],
        'query': '',
        'name': '',
        'name_operator': 'contains',
        'name_operator_param': '',
        'code': '',
        'code_operator': 'contains',
        'code_operator_param': '',
        'description': '',
        'description_operator': 'contains',
        'description_operator_param': '',
        'source': '',
        'source_operator': 'contains',
        'source_operator_param': '',
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
        'sort_field': 'name',
        'filters': _empty_project_filter_options(project_field_configuration['choices']),
        'active_filters': [],
        'active_filter_count': 0,
        'has_active_filters': False,
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
    group_window = _group_window_for_request(
        request,
        field_configuration=project_field_configuration,
        project=active_project if active_view == 'project' else None,
    ) if active_view in {'all_groups', 'project'} else {
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
        'active_filters': [],
        'active_filter_count': 0,
        'has_active_filters': False,
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
    project_section_window = group_window if active_view == 'project' and active_project else {
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
        'priority': '',
        'status': '',
        'category': '',
        'scope': '',
        'owner': '',
        'sort': TAG_DEFAULT_SORT,
        'sort_param': '',
        'sort_label': TAG_SORT_OPTION_MAP[TAG_DEFAULT_SORT]['label'],
        'sort_direction': TAG_SORT_OPTION_MAP[TAG_DEFAULT_SORT]['direction'],
        'filters': _empty_tag_filter_options(),
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
    task_window = _task_window_for_request(request, tasks_qs) if active_view in ('all_tasks', 'my_tasks', 'unassigned_tasks') else {
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
    navigation_projects = _navigation_projects_for_user(workspace_owner(request), active_project=active_project, workplace=workplace, viewer=request.user)
    if active_project:
        navigation_active_project = next((project for project in navigation_projects if project.id == active_project.id), None)
        if navigation_active_project:
            active_project = navigation_active_project
            if active_section:
                active_section = next((section for section in active_project.sections.all() if section.id == active_section.id), active_section)
    if active_project_for_form and (not active_project or active_project_for_form.id != active_project.id):
        project_options = _navigation_projects_for_user(
            workspace_owner(request),
            active_project=active_project_for_form,
            workplace=workplace,
            viewer=request.user,
        )
    else:
        project_options = navigation_projects
    _decorate_project_directory_metrics(navigation_projects, viewer=request.user)
    _decorate_project_field_values(navigation_projects, project_field_configuration)
    _decorate_directory_members(navigation_projects, current_user=workspace_owner(request), viewer=request.user)
    if project_options is not navigation_projects:
        _decorate_project_directory_metrics(project_options, viewer=request.user)
        _decorate_project_field_values(project_options, project_field_configuration)
        _decorate_directory_members(project_options, current_user=workspace_owner(request), viewer=request.user)

    orphan_tasks = []
    orphan_status_groups = []
    all_status_groups = []
    if active_section:
        active_section.status_groups = _status_groups_for_tasks(
            tasks_qs.filter(section_id=active_section.id),
            workspace_owner(request),
            request=request,
            base_url=request.path,
            paginate=True,
        )
    elif all_tasks_view or my_tasks_view or unassigned_tasks_view:
        if active_view == 'all_tasks':
            decorate_favorites(task_window['queryset'], request, 'task')
        all_status_groups = _status_groups_for_tasks(
            task_window['queryset'],
            workspace_owner(request),
            request=request,
        )
    all_sections = group_window['sections'] if active_view == 'all_groups' else []
    shared_projects = []
    shared_sections = []
    shared_tasks = []
    shared_status_groups = []
    _decorate_share_links(request, [*projects, *all_sections])
    tags = tag_window['tags'] if active_view == 'tags' else TaskTag.objects.none()
    total_task_count = task_window['total_tasks'] if (all_tasks_view or my_tasks_view or unassigned_tasks_view) else 0
    can_create_issue = _user_can_create_issue(
        workspace_owner(request),
        active_project=active_project,
        active_section=active_section,
        workplace=workplace,
        viewer=request.user,
    )
    project_sections = project_section_window['sections'] if active_view == 'project' else []

    context = {
        'projects': projects,
        'navigation_projects': navigation_projects,
        'project_options': project_options,
        'issue_picker_options': _task_modal_picker_options(project_options),
        'issue_project_id': request.POST.get('project_id', '') if task_modal_open else '',
        'project_window': project_window,
        'project_query': project_window['query'],
        'project_name_filter': project_window['name'],
        'project_name_operator': project_window['name_operator'],
        'project_name_operator_param': project_window['name_operator_param'],
        'project_code_filter': project_window['code'],
        'project_code_operator': project_window['code_operator'],
        'project_code_operator_param': project_window['code_operator_param'],
        'project_description_filter': project_window['description'],
        'project_description_operator': project_window['description_operator'],
        'project_description_operator_param': project_window['description_operator_param'],
        'project_source_filter': project_window['source'],
        'project_source_operator': project_window['source_operator'],
        'project_source_operator_param': project_window['source_operator_param'],
        'project_priority_filter': project_window['priority'],
        'project_status_filter': project_window['status'],
        'project_stage_filter': project_window['stage'],
        'project_health_filter': project_window['health'],
        'project_company_filter': project_window['company'],
        'project_responsible_filter': project_window['responsible'],
        'project_filter_options': project_window['filters'],
        'project_priority_options': _choice_options(TaskProject.PRIORITY_CHOICES),
        'project_active_filters': project_window['active_filters'],
        'project_active_filter_count': project_window['active_filter_count'],
        'project_has_active_filters': project_window['has_active_filters'],
        'project_text_filter_operators': PROJECT_TEXT_FILTER_OPERATORS,
        'project_sort_fields': PROJECT_SORT_FIELDS,
        'project_sort_options': PROJECT_SORT_OPTIONS,
        'project_sort': project_window['sort'],
        'project_sort_field': project_window['sort_field'],
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
        'group_active_filters': group_window['active_filters'],
        'group_active_filter_count': group_window['active_filter_count'],
        'group_has_active_filters': group_window['has_active_filters'],
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
        'tag_priority_filter': tag_window['priority'],
        'tag_status_filter': tag_window['status'],
        'tag_category_filter': tag_window['category'],
        'tag_scope_filter': tag_window['scope'],
        'tag_owner_filter': tag_window['owner'],
        'tag_filter_options': tag_window['filters'],
        'tag_sort_options': TAG_SORT_OPTIONS,
        'tag_sort': tag_window['sort'],
        'tag_sort_param': tag_window['sort_param'],
        'tag_sort_label': tag_window['sort_label'],
        'tag_sort_direction': tag_window['sort_direction'],
        'tag_default_sort': TAG_DEFAULT_SORT,
        'task_window': task_window,
        'task_query': task_window['query'],
        'task_priority_filter': task_window['priority'],
        'task_status_filter': task_window['status'],
        'task_project_filter': task_window['project_filter'],
        'task_section_filter': task_window['section'],
        'task_assignee_filter': task_window['assignee'],
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
        'project_access_data': project_access_data(workplace, request.user),
        'section_access_data': section_access_data(workplace, request.user),
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
    context.update(follow_context(request.user, active_project, 'tasks', 'project'))
    if active_view in {'projects', 'all_groups', 'all_tasks'}:
        context['directory_tab'] = directory_tab(request)
        context['directory_tabs'] = directory_tabs(request, context['directory_tab'])
    return render(request, 'tasks/tasks.html', context)


@login_required
@require_POST
def create_share_link(request):
    obj = _owned_share_object(
        request.user,
        (request.POST.get('object_type') or '').strip(),
        request.POST.get('object_id'),
        workplace=_active_workplace(request),
        viewer=request.user,
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
        viewer=request.user,
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
        task_pk = task_primary_keys(data)[0]
        user = workspace_owner(request)
        with lock_task_numbers(user.pk):
            task = _filter_workplace(editable_to(Task.objects.all(), request.user).filter(user=user), workplace).select_for_update().get(pk=task_pk)
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
    except (ValueError, TypeError) as error:
        return JsonResponse({'status': 'error', 'message': str(error)}, status=400)

@login_required
@require_POST
def delete_task(request, task_id):
    try:
        task_pk = task_primary_keys(json.loads(request.body))[0]
        with lock_task_numbers(workspace_owner(request).pk):
            task = _filter_workplace(editable_to(Task.objects.all(), request.user).filter(user=workspace_owner(request)), _active_workplace(request)).get(pk=task_pk)
            require_deletable_tasks(Task.objects.filter(pk=task.pk), request.user)
            task.delete()
        return JsonResponse({'status': 'success', 'message': 'Zadanie usunięte pomyślnie'})
    except Task.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Zadanie nie znalezione'}, status=404)
    except (ValueError, TypeError) as error:
        return JsonResponse({'status': 'error', 'message': str(error)}, status=400)

@login_required
@require_POST
def delete_attachment(request, attachment_id):
    try:
        attachment = get_object_or_404(
            _filter_workplace(
                editable_to(TaskAttachment.objects.all(), request.user).select_related('task', 'task__section', 'task__section__project'),
                _active_workplace(request),
                field_name='task__workplace',
            ),
            id=attachment_id,
        )
        if not _user_can_edit_task(workspace_owner(request), attachment.task, viewer=request.user):
            return JsonResponse({'status': 'error', 'message': 'Brak uprawnień do edycji zadania'}, status=403)
        attachment.delete()
        return JsonResponse({'status': 'success', 'message': 'Załącznik usunięty pomyślnie'})
    except TaskAttachment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Załącznik nie znaleziony'}, status=404)


@login_required
def download_attachment(request, attachment_id):
    attachment = get_object_or_404(
        _filter_workplace(
            visible_to(TaskAttachment.objects.all(), request.user).select_related('task'),
            _active_workplace(request),
            field_name='task__workplace',
        ).filter(task__user=workspace_owner(request)),
        id=attachment_id,
    )
    return attachment_download_response(attachment)


@login_required
@require_POST
def delete_tasks(request):
    try:
        data = json.loads(request.body)
        task_pks = task_primary_keys(data, many=True)

        user = workspace_owner(request)
        workplace = _active_workplace(request)
        with lock_task_numbers(user.pk):
            tasks_to_delete = _filter_workplace(visible_to(Task.objects.all(), request.user).filter(pk__in=task_pks, user=user), workplace)
            require_editable(tasks_to_delete, request.user)
            require_deletable_tasks(tasks_to_delete, request.user)
            deleted_count = tasks_to_delete.delete()[0]
            Task._renumber_user_tasks(user, workplace)

        return JsonResponse({
            'status': 'success', 
            'message': f'{deleted_count} {"zadań" if deleted_count != 1 else "zadanie"} usuniętych pomyślnie',
            'deleted_count': deleted_count
        })
    except (ValueError, TypeError) as error:
        return JsonResponse({'status': 'error', 'message': str(error)}, status=400)
    except PermissionDenied as error:
        return JsonResponse({'status': 'error', 'message': str(error)}, status=403)
    except Exception:
        logger.exception('Failed to delete tasks')
        return JsonResponse({'status': 'error', 'message': 'Nie udało się usunąć zadań.'}, status=500)

@login_required
@require_POST
def bulk_update_status(request):
    try:
        data = json.loads(request.body)
        task_pks = task_primary_keys(data, many=True)
        status = data.get('status', 'closed')
        
        valid_statuses = {choice for choice, _label in Task.STATUS_CHOICES}
        if status not in valid_statuses:
            return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy status'}, status=400)
        
        user = workspace_owner(request)
        workplace = _active_workplace(request)
        tasks_to_update = _filter_workplace(visible_to(Task.objects.all(), request.user).filter(pk__in=task_pks, user=user), workplace)
        updated_count = 0
        with lock_task_numbers(user.pk):
            require_editable(tasks_to_update, request.user)
            for task in tasks_to_update.select_for_update():
                previous_status = task.status
                _set_task_status(task, status)
                updated_count += 1
                if previous_status != status:
                    labels = dict(Task.STATUS_CHOICES)
                    _record_task_activity(task, request.user, 'status_changed', 'zmienił status', metadata={
                        'from_label': labels.get(previous_status, previous_status),
                        'to_label': labels[status],
                        'changes': [{'field': 'status', 'from_label': labels.get(previous_status, previous_status), 'to_label': labels[status]}],
                    })

        return JsonResponse({
            'status': 'success', 
            'message': f'Zaktualizowano {updated_count} {"zadań" if updated_count != 1 else "zadanie"}',
            'updated_count': updated_count
        })
    except (ValueError, TypeError) as error:
        return JsonResponse({'status': 'error', 'message': str(error)}, status=400)
    except PermissionDenied as error:
        return JsonResponse({'status': 'error', 'message': str(error)}, status=403)
    except Exception:
        logger.exception('Failed to bulk update task status')
        return JsonResponse({'status': 'error', 'message': 'Nie udało się zaktualizować zadań.'}, status=500)


def _task_work_log_url(task, page=1):
    route = 'view-subtask' if task.parent_id else 'view-task'
    return scoped_workplace_app_path(task.workplace, 'tasks', f'{route}/{task.task_id}/',
                                    urlencode({'task_pk': task.pk, 'tab': 'work-log', 'work_log_page': page}))


def _task_work_log_context(request, task):
    entries = task.work_logs.select_related('author')
    duration = entries.aggregate(total=Sum(F('ended_at') - F('started_at')))['total'] or timedelta()
    total_minutes = int(duration.total_seconds() // 60)
    page = Paginator(entries, 25).get_page(request.POST.get('work_log_page') or request.GET.get('work_log_page'))
    for entry in page:
        entry.form_values = json.dumps({
            'id': entry.pk,
            'duration_minutes': entry.duration_minutes,
            'started_at': timezone.localtime(entry.started_at).strftime('%Y-%m-%dT%H:%M'),
            'ended_at': timezone.localtime(entry.ended_at).strftime('%Y-%m-%dT%H:%M'),
            'description': entry.description,
        })
    return {
        'work_log_page': page,
        'work_log_total_minutes': total_minutes,
        'work_log_total_label': f'{total_minutes // 60} godz. {total_minutes % 60:02d} min',
        'work_log_previous_url': _task_work_log_url(task, page.previous_page_number()) if page.has_previous() else '',
        'work_log_next_url': _task_work_log_url(task, page.next_page_number()) if page.has_next() else '',
    }


@transaction.atomic
def _save_task_work_log(request, task):
    action = request.POST['action']
    if not request.POST.get('task_pk'):
        return JsonResponse({'status': 'error', 'message': 'Odśwież stronę i ponów operację — brakuje identyfikatora zadania.'}, status=400)
    entry = None
    if action != 'add_work_log':
        try:
            entry_id = int(request.POST.get('work_log_id', ''))
        except (ValueError, TypeError, OverflowError):
            raise Http404
        entry = get_object_or_404(visible_to(TaskWorkLog.objects.all(), request.user).select_for_update(), task=task, pk=entry_id)
    form = TaskWorkLogForm(request.POST, instance=entry, prefix='worklog')
    if action != 'delete_work_log' and not form.is_valid():
        if _is_ajax_request(request):
            return JsonResponse({
                'status': 'error', 'message': 'Sprawdź dane wpisu.',
                'form_html': render_to_string('tasks/includes/work_log_fields.html', {'work_log_form': form}, request=request),
            }, status=400)
        return form

    if action == 'delete_work_log':
        minutes = entry.duration_minutes
        entry_id = entry.pk
        entry.delete()
        activity_action, message = 'work_log_deleted', 'usunął wpis czasu'
    else:
        entry = form.save(commit=False)
        if action == 'add_work_log':
            entry.task, entry.author = task, request.user
        entry.save()
        minutes, entry_id = entry.duration_minutes, entry.pk
        activity_action, message = ('work_log_added', 'dodał wpis czasu') if action == 'add_work_log' else ('work_log_updated', 'zmienił wpis czasu')
    activity = _record_task_activity(task, request.user, activity_action, f'{message} ({minutes} min)',
                                     metadata={'work_log_id': entry_id, 'minutes': minutes})
    if _is_ajax_request(request):
        context = {'task': task, 'can_edit_task': True, **_task_work_log_context(request, task)}
        return JsonResponse({
            'status': 'success', 'message': 'Usunięto wpis.' if action == 'delete_work_log' else 'Zapisano wpis.',
            'work_log_html': render_to_string('tasks/includes/work_log_list.html', context, request=request),
            'activity_html': _task_activity_html([activity]),
        })
    return redirect(_task_work_log_url(task))


def _task_detail_response(request, task_id=None, task_pk=None):
    if request.method == 'POST':
        with lock_task_numbers(workspace_owner(request).pk):
            if request.workplace:
                Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            return _task_detail(request, task_id, task_pk, lock=True)
    return _task_detail(request, task_id, task_pk)


def _task_detail(request, task_id=None, task_pk=None, *, lock=False):
    workplace = _active_workplace(request)
    task_queryset = _filter_workplace(
        visible_to(Task.objects.all(), request.user).select_related('section', 'section__project', 'section__project__user', 'parent', 'assignee'),
        workplace,
    ).prefetch_related(
        Prefetch(
            'subtasks',
            queryset=_filter_workplace(
                visible_to(Task.objects.all(), request.user).select_related('section', 'section__project', 'assignee'),
                workplace,
            ).prefetch_related('tags', 'attachments').order_by('task_id'),
        ),
        Prefetch(
            'activities',
            queryset=visible_to(TaskActivity.objects.all(), request.user).select_related('actor').prefetch_related('images').order_by('-created_at', '-id'),
        ),
    )
    if task_pk is not None:
        raise PermissionDenied
    if lock:
        task_queryset = task_queryset.select_for_update(of=('self',))
    task = get_object_or_404(task_queryset, user=workspace_owner(request), **task_detail_lookup(request, task_id))

    can_edit_task = _user_can_edit_task(workspace_owner(request), task, viewer=request.user)
    can_manage_task = can_edit_task
    subtask_status_groups = _status_groups_for_tasks(task.subtasks.all(), workspace_owner(request), request=request)
    can_add_attachments = can_edit_task and not task.parent_id
    form = TaskForm(instance=task, user=task.user, workplace=workplace, viewer=request.user, read_only=not can_edit_task)
    task_modal_form = SubTaskModalForm(viewer=request.user)
    task_modal_open = False
    comment_errors = []
    work_log_form = TaskWorkLogForm(prefix='worklog')
    work_log_modal_open = False
    active_tab = request.GET.get('tab', 'main')
    if active_tab not in {'main', 'subtasks', 'work-log', 'history', 'members'} or (active_tab == 'subtasks' and task.parent_id):
        active_tab = 'main'
    _decorate_task_directory_members([task], current_user=workspace_owner(request), viewer=request.user)

    if request.method == 'POST':
        if not can_edit_task:
            raise PermissionDenied('Masz dostęp tylko do odczytu tego projektu.')
        is_ajax = _is_ajax_request(request)
        action = request.POST.get('action')
        if action in {'add_work_log', 'edit_work_log', 'delete_work_log'}:
            if not can_edit_task:
                raise PermissionDenied
            result = _save_task_work_log(request, task)
            if not isinstance(result, TaskWorkLogForm):
                return result
            work_log_form = result
            work_log_modal_open = True
            active_tab = 'work-log'
        elif action == 'create_subtask_modal':
            if not can_edit_task:
                raise PermissionDenied
            task_modal_form = SubTaskModalForm(request.POST, viewer=request.user)
            if task_modal_form.is_valid():
                subtask = task_modal_form.save(commit=False)
                subtask.user = task.user
                subtask.parent = task
                subtask.section = task.section
                subtask.workplace = workplace
                subtask._activity_actor = request.user
                subtask.save()
                _record_task_activity(
                    task,
                    request.user,
                    'subtask_created',
                    'dodał podzadanie',
                    metadata={
                        'subtask_title': subtask.title,
                        'subtask_task_id': subtask.task_id,
                        'subtask_pk': subtask.pk,
                    },
                )
                messages.success(request, 'Podzadanie dodane.')
                detail_redirect = _redirect_to_task_detail(task, workspace_owner(request))
                detail_redirect['Location'] += '?' + urlencode({'task_pk': task.pk, 'tab': 'subtasks'})
                return detail_redirect
            active_tab = 'subtasks' if not task.parent_id else 'main'
            task_modal_open = True
            messages.error(request, 'Nie udało się dodać podzadania.')
        elif action == 'add_activity_comment':
            try:
                activity = save_comment(request, task, TaskCommentImage, _record_task_activity)
            except ValidationError as error:
                comment_errors = error.messages
                active_tab = 'main'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': ' '.join(comment_errors)}, status=400)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'activity_html': render_to_string(
                        'tasks/includes/task_activity_item.html', {'item': activity}, request=request,
                    )})
                messages.success(request, 'Komentarz dodany.')
                return _redirect_to_task_detail(task, workspace_owner(request))
        else:
            if not can_edit_task:
                raise PermissionDenied
            files = request.FILES.getlist('attachments') if can_add_attachments else []
            file_errors = _attachment_validation_errors(files)
            before = _task_activity_snapshot(task)
            form = TaskForm(request.POST, request.FILES, instance=task, user=task.user, workplace=workplace, viewer=request.user)
            if form.is_valid() and not file_errors:
                form.save()
                recorded_activities = []

                # Handle staged attachment deletions
                deleted_attachments = request.POST.get('deleted_attachments', '')
                deleted_count = 0
                if deleted_attachments:
                    attachment_ids = [int(aid) for aid in deleted_attachments.split(',') if aid.isdigit()]
                    attachments_to_delete = visible_to(TaskAttachment.objects.all(), request.user).filter(id__in=attachment_ids, task=task)
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
                        'message': 'Zapisano.',
                        'task': _task_detail_payload(task),
                        'team': _task_team_payload(request, task),
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
                return _redirect_to_task_detail(task, workspace_owner(request))
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
                active_tab = 'main'
    else:
        form = TaskForm(instance=task, user=task.user, workplace=workplace, viewer=request.user, read_only=not can_edit_task)

    if not form.can_manage_access:
        form.fields['visibility'].disabled = True
    if not can_edit_task:
        for field in form.fields.values():
            field.disabled = True

    activity_items = list(task.activities.all())
    context = {
        'form': form,
        'work_log_form': work_log_form,
        'work_log_modal_open': work_log_modal_open,
        'active_task_tab': active_tab,
        'work_log_url': _task_work_log_url(task),
        **_task_work_log_context(request, task),
        'task_modal_form': task_modal_form,
        'task_modal_open': task_modal_open,
        'task': task,
        'can_manage_task': can_manage_task,
        'can_edit_task': can_edit_task,
        'task_team_url': scoped_workplace_app_path(workplace, 'tasks', f'items/{task.pk}/team/') if workplace else reverse('tasks:task_team', args=[task.pk]),
        'can_add_attachments': can_add_attachments,
        'comment_errors': comment_errors,
        'comment_draft': request.POST.get('activity_comment', '') if comment_errors else '',
        'comment_mentions': request.POST.get('activity_mentions', '[]') if comment_errors else '[]',
        'comment_image_limit': MAX_COMMENT_ATTACHMENTS,
        'comment_attachment_accept': ','.join(sorted(ATTACHMENT_ALLOWED_EXTENSIONS)),
        'comment_image_max_size': getattr(settings, 'MAX_ATTACHMENT_SIZE', DEFAULT_ATTACHMENT_MAX_SIZE),
        'comment_items': [item for item in activity_items if item.kind == 'comment'],
        'history_items': [item for item in activity_items if item.kind != 'comment'],
        'subtask_status_groups': subtask_status_groups,
        'tasks_return_path': request.get_full_path(),
        **_tasks_navigation_context(
            workspace_owner(request),
            active_section=task.section,
            active_view='section' if task.section_id else 'all_tasks',
            workplace=workplace,
            viewer=request.user,
        ),
    }
    context.update(follow_context(request.user, task, 'tasks', 'task'))
    context['mention_people'] = mention_choices(task)
    return render(request, 'tasks/view_task.html', context)


@login_required
def view_task(request, task_id):
    return _task_detail_response(request, task_id)

@login_required
def view_subtask(request, task_id):
    return _task_detail_response(request, task_id)


@login_required
def comment_image(request, image_id):
    return comment_image_response(request, TaskCommentImage, image_id)
