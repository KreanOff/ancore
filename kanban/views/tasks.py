import logging
import json
import unicodedata
from urllib.parse import urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Max, Prefetch, Q, Value, When
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
from core.upload_validation import attachment_download_response, validate_attachment_upload
from tasks.models import TaskTag, TaskTagNote
from ..models import Kanban, KanbanActivity, KanbanAttachment, KanbanBoardColumn, KanbanProject, KanbanProjectNote, KanbanSection
from ..forms import QuickKanbanForm, SubKanbanModalForm, KanbanBoardColumnForm, KanbanForm, KanbanModalForm, KanbanProjectForm, KanbanProjectRenameForm, KanbanSectionForm, KanbanSectionRenameForm, KanbanTagForm


logger = logging.getLogger(__name__)

PROJECT_PAGE_SIZE_OPTIONS = (10, 25, 50, 100, 150, 200)
PROJECT_DEFAULT_PAGE_SIZE = 50
PROJECT_DEFAULT_SORT = 'name_asc'
PROJECT_SORT_OPTIONS = (
    {'value': 'name_asc', 'label': 'Przestrzeń A-Z', 'icon': 'arrow-up-a-z', 'direction': 'asc'},
    {'value': 'name_desc', 'label': 'Przestrzeń Z-A', 'icon': 'arrow-down-z-a', 'direction': 'desc'},
    {'value': 'code_asc', 'label': 'Kod A-Z', 'icon': 'arrow-up-a-z', 'direction': 'asc'},
    {'value': 'company_asc', 'label': 'Firma A-Z', 'icon': 'building-2', 'direction': 'asc'},
    {'value': 'responsible_asc', 'label': 'Odpowiedzialny', 'icon': 'circle-user-round', 'direction': 'asc'},
    {'value': 'status_asc', 'label': 'Status', 'icon': 'circle-dot', 'direction': 'asc'},
    {'value': 'priority_desc', 'label': 'Priorytet', 'icon': 'chart-no-axes-column-increasing', 'direction': 'desc'},
    {'value': 'due_at_asc', 'label': 'Najbliższy termin', 'icon': 'calendar-clock', 'direction': 'asc'},
    {'value': 'sections_desc', 'label': 'Najwięcej tablic', 'icon': 'kanban', 'direction': 'desc'},
    {'value': 'cards_desc', 'label': 'Najwięcej kart', 'icon': 'list-checks', 'direction': 'desc'},
    {'value': 'created_desc', 'label': 'Najnowsze', 'icon': 'calendar-plus', 'direction': 'desc'},
    {'value': 'activity_desc', 'label': 'Ostatnia aktywność', 'icon': 'activity', 'direction': 'desc'},
)
PROJECT_SORT_OPTION_MAP = {option['value']: option for option in PROJECT_SORT_OPTIONS}
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


def _active_workplace(request):
    return getattr(request, 'workplace', None)


def _filter_workplace(queryset, workplace, field_name='workplace'):
    if workplace is None:
        return queryset
    return queryset.filter(**{field_name: workplace})


def _normalize_query_label(value):
    normalized = unicodedata.normalize('NFKD', str(value or '').casefold())
    return ''.join(
        char
        for char in normalized
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


def _tag_sort_value(value):
    return value if value in TAG_SORT_OPTION_MAP else TAG_DEFAULT_SORT


def _choice_rank_case(field_name, choices):
    return Case(
        *[When(**{field_name: value}, then=Value(index)) for index, (value, _label) in enumerate(choices)],
        default=Value(len(choices)),
        output_field=IntegerField(),
    )


def _project_sort_value(value):
    return value if value in PROJECT_SORT_OPTION_MAP else PROJECT_DEFAULT_SORT


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


def _projects_url(params, base_url=None):
    cleaned_params = {
        key: value
        for key, value in params.items()
        if value not in (None, '')
    }
    query_string = urlencode(cleaned_params)
    base_url = base_url or reverse('kanban:tasks')
    return f'{base_url}?{query_string}' if query_string else base_url


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


def _kanban_next_url(request):
    fallback = reverse('kanban:tasks')
    next_url = (request.POST.get('next') or '').strip()
    if next_url == fallback or next_url.startswith(f'{fallback}?') or next_url.startswith('/kanban/'):
        return next_url
    return fallback


def _attachment_validation_errors(files):
    errors = []
    for uploaded_file in files:
        try:
            validate_attachment_upload(uploaded_file)
        except ValidationError as error:
            errors.extend(error.messages)
    return errors


def _status_groups_for_tasks(tasks):
    tasks_by_status = {status: [] for status, _label in Kanban.STATUS_CHOICES}
    for task in tasks:
        tasks_by_status.setdefault(task.status, []).append(task)
    return [
        {
            'status': status,
            'label': label,
            'tasks': tasks_by_status.get(status, []),
            'count': len(tasks_by_status.get(status, [])),
        }
        for status, label in Kanban.STATUS_CHOICES
    ]


def _board_columns_for_section(section):
    return list(KanbanBoardColumn.objects.filter(section=section))


def _status_labels_for_user(user):
    return dict(Kanban.STATUS_CHOICES)


def _status_filter_options_for_user(user):
    return Kanban.STATUS_CHOICES


def _valid_statuses_for_user(user):
    return {choice for choice, _label in Kanban.STATUS_CHOICES}


def _ensure_task_columns(section, tasks):
    columns = _board_columns_for_section(section)
    fallback = columns[0] if columns else None
    for task in tasks:
        if fallback and (not task.column_id or task.column.section_id != section.id):
            task.column = fallback
            task.save(update_fields=['column'])
    return columns


def _task_board_columns(section, tasks):
    task_list = list(tasks)
    column_definitions = _ensure_task_columns(section, task_list)
    columns = []

    for definition in column_definitions:
        column_tasks = [task for task in task_list if task.column_id == definition.id]
        columns.append({
            'id': definition.id,
            'key': definition.id,
            'title': definition.title,
            'section': definition.section,
            'is_done': definition.is_done,
            'tasks': column_tasks,
            'count': len(column_tasks),
        })

    return columns


def _all_task_board_columns(user, tasks, workplace=None):
    task_list = list(tasks)
    for section in _filter_workplace(KanbanSection.objects.filter(project__user=user), workplace, field_name='project__workplace'):
        _ensure_task_columns(section, [task for task in task_list if task.section_id == section.id])

    columns = []
    assigned_task_ids = set()
    column_definitions = KanbanBoardColumn.objects.filter(section__project__user=user).select_related('section', 'section__project')
    column_definitions = _filter_workplace(column_definitions, workplace, field_name='section__project__workplace')
    for definition in column_definitions:
        column_tasks = [task for task in task_list if task.column_id == definition.id]
        if not column_tasks:
            continue
        assigned_task_ids.update(task.id for task in column_tasks)
        columns.append({
            'id': definition.id,
            'key': definition.id,
            'title': f'{definition.section.title} / {definition.title}',
            'section': definition.section,
            'is_done': definition.is_done,
            'tasks': column_tasks,
            'count': len(column_tasks),
        })
    sections_by_id = {
        section.id: section
        for section in _filter_workplace(
            KanbanSection.objects.filter(project__user=user).select_related('project'),
            workplace,
            field_name='project__workplace',
        )
    }
    for section_id, section in sections_by_id.items():
        column_tasks = [
            task for task in task_list
            if task.section_id == section_id and not task.column_id and task.id not in assigned_task_ids
        ]
        if not column_tasks:
            continue
        columns.append({
            'id': '',
            'key': f'unassigned-{section.id}',
            'title': f'{section.title} / Bez kolumny',
            'section': section,
            'is_done': False,
            'is_virtual': True,
            'tasks': column_tasks,
            'count': len(column_tasks),
        })
    return columns


def _decorate_status_groups(projects, orphan_tasks):
    for project in projects:
        project_tasks = []
        for section in project.sections.all():
            section_tasks = list(section.tasks.all())
            section.status_groups = _status_groups_for_tasks(section_tasks)
            project_tasks.extend(section_tasks)
        project.status_groups = _status_groups_for_tasks(project_tasks)
    return _status_groups_for_tasks(list(orphan_tasks))


def _sections_for_projects(projects):
    return [section for project in projects for section in project.sections.all()]


def _posted_ids(request, plural_name, singular_name):
    ids = request.POST.getlist(plural_name)
    if not ids:
        ids = [request.POST.get(singular_name)]
    return [item for item in ids if item]


def _project_card_filter(user, workplace):
    card_filter = Q(sections__tasks__user=user, sections__tasks__parent__isnull=True)
    card_filter &= (
        Q(sections__tasks__workplace=workplace)
        if workplace is not None else Q(sections__tasks__workplace__isnull=True)
    )
    return card_filter


def _project_directory_queryset(user, workplace=None):
    card_filter = _project_card_filter(user, workplace)
    return _filter_workplace(KanbanProject.objects.filter(user=user), workplace).select_related('company', 'responsible_user').annotate(
        sections_count=Count('sections', distinct=True),
        cards_total_count=Count('sections__tasks', filter=card_filter, distinct=True),
        cards_closed_count=Count('sections__tasks', filter=card_filter & Q(sections__tasks__status='closed'), distinct=True),
        last_activity_at=Max('sections__tasks__activities__created_at'),
        last_card_at=Max('sections__tasks__created_at'),
    ).prefetch_related(
        Prefetch(
            'project_notes',
            queryset=KanbanProjectNote.objects.select_related('author').order_by('created_at', 'id'),
        ),
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
    queryset = _project_directory_queryset(user, workplace=workplace)
    query = (query or '').strip()
    if query:
        priority_matches = _choice_values_matching_query(KanbanProject.PRIORITY_CHOICES, query)
        status_matches = _choice_values_matching_query(KanbanProject.STATUS_CHOICES, query)
        stage_matches = _choice_values_matching_query(KanbanProject.STAGE_CHOICES, query)
        health_matches = _choice_values_matching_query(KanbanProject.HEALTH_CHOICES, query)
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
    if priority in {value for value, _label in KanbanProject.PRIORITY_CHOICES}:
        queryset = queryset.filter(priority=priority)
    if status in {value for value, _label in KanbanProject.STATUS_CHOICES}:
        queryset = queryset.filter(status=status)
    if stage in {value for value, _label in KanbanProject.STAGE_CHOICES}:
        queryset = queryset.filter(stage=stage)
    if health in {value for value, _label in KanbanProject.HEALTH_CHOICES}:
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
            status_sort_rank=_choice_rank_case('status', KanbanProject.STATUS_CHOICES)
        ).order_by('status_sort_rank', 'name', 'id')
    if sort_value == 'priority_desc':
        return queryset.annotate(
            priority_sort_rank=_choice_rank_case('priority', KanbanProject.PRIORITY_CHOICES)
        ).order_by('-priority_sort_rank', 'name', 'id')
    if sort_value == 'due_at_asc':
        return queryset.annotate(
            due_empty_sort=Case(
                When(due_at__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('due_empty_sort', 'due_at', 'name', 'id')
    if sort_value == 'sections_desc':
        return queryset.order_by('-sections_count', 'name', 'id')
    if sort_value == 'cards_desc':
        return queryset.order_by('-cards_total_count', 'name', 'id')
    if sort_value == 'activity_desc':
        return queryset.order_by('-last_activity_at', '-last_card_at', 'name', 'id')
    if sort_value == 'created_desc':
        return queryset.order_by('-created_at', 'name', 'id')
    return queryset.order_by('name', 'id')


def _project_filter_options(user, workplace=None):
    queryset = _filter_workplace(
        KanbanProject.objects.filter(user=user),
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
        'statuses': _choice_options(KanbanProject.STATUS_CHOICES),
        'stages': _choice_options(KanbanProject.STAGE_CHOICES),
        'healths': _choice_options(KanbanProject.HEALTH_CHOICES),
        'companies': companies,
        'responsible_users': responsible_users,
    }


def _empty_project_filter_options():
    return {
        'statuses': _choice_options(KanbanProject.STATUS_CHOICES),
        'stages': _choice_options(KanbanProject.STAGE_CHOICES),
        'healths': _choice_options(KanbanProject.HEALTH_CHOICES),
        'companies': [],
        'responsible_users': [],
    }


def _kanban_project_count_label(value, singular, plural):
    count = int(value or 0)
    label = singular if count == 1 else plural
    return f'{count} {label}'


def _decorate_project_directory_metrics(projects):
    today = timezone.localdate()
    for project in projects:
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

        total_cards = int(getattr(project, 'cards_total_count', 0) or 0)
        closed_cards = int(getattr(project, 'cards_closed_count', 0) or 0)
        progress_percent = round((closed_cards / total_cards) * 100) if total_cards else 0
        project.progress_percent = progress_percent
        project.cards_count_label = _kanban_project_count_label(total_cards, 'karta', 'kart')
        project.sections_count_label = _kanban_project_count_label(getattr(project, 'sections_count', 0), 'tablica', 'tablic')
        project.last_activity_display_at = getattr(project, 'last_activity_at', None) or getattr(project, 'last_card_at', None)
    return projects


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
    queryset = _project_sort_queryset(
        _project_filter_queryset(
            request.user,
            query=query,
            priority=priority,
            status=status,
            stage=stage,
            health=health,
            company=company,
            responsible=responsible,
            workplace=workplace,
        ),
        sort,
    )
    total_projects = queryset.count()
    total_pages = max(1, (total_projects + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size
    projects = list(queryset[offset:offset + page_size])
    _decorate_project_directory_metrics(projects)

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
        summary = 'Brak przestrzeni'
    else:
        first_visible = offset + 1
        last_visible = offset + len(projects)
        summary = f'Pokazano {first_visible}-{last_visible} z {total_projects} przestrzeni'

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


def _section_filter_queryset(user, query='', workplace=None):
    queryset = _filter_workplace(
        KanbanSection.objects.filter(project__user=user),
        workplace,
        field_name='project__workplace',
    ).select_related('project')
    query = (query or '').strip()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(project__name__icontains=query)
            | Q(project__description__icontains=query)
            | Q(project__code__icontains=query)
        )
    return queryset.order_by('project__name', 'project_id', 'order', 'created_at', 'id')


def _section_window_for_request(request):
    page_size = _project_page_size(request)
    requested_page = _project_page_number(request)
    query = (request.GET.get('q') or '').strip()
    queryset = _section_filter_queryset(request.user, query=query, workplace=_active_workplace(request))
    total_sections = queryset.count()
    total_pages = max(1, (total_sections + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size
    sections = list(queryset[offset:offset + page_size])

    base_params = {
        'view': 'all-groups',
        'q': query,
        'page_size': page_size,
    }
    has_previous = current_page > 1 and total_sections > 0
    has_next = current_page < total_pages and total_sections > 0
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
        summary = 'Brak tablic'
    else:
        first_visible = offset + 1
        last_visible = offset + len(sections)
        summary = f'Pokazano {first_visible}-{last_visible} z {total_sections} tablic'

    return {
        'sections': sections,
        'query': query,
        'page': current_page,
        'total_pages': total_pages,
        'total_sections': total_sections,
        'page_size': page_size,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'page_items': _project_page_items(current_page, total_pages, base_params) if total_sections else [],
        'has_previous': has_previous,
        'has_next': has_next,
        'previous_url': previous_url,
        'next_url': next_url,
        'summary': summary,
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
        queryset = queryset.filter(owner_label=owner)
    return queryset.prefetch_related(
        'related_tags',
        Prefetch(
            'tag_notes',
            queryset=TaskTagNote.objects.select_related('author').order_by('created_at', 'id'),
        ),
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


def _tag_card_count_filter(user, workplace):
    card_filter = Q(kanban_cards__user=user, kanban_cards__parent__isnull=True)
    card_filter &= (
        Q(kanban_cards__workplace=workplace)
        if workplace is not None else Q(kanban_cards__workplace__isnull=True)
    )
    return card_filter


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
        request.user,
        query=query,
        priority=priority,
        status=status,
        category=category,
        scope=scope,
        owner=owner,
        workplace=workplace,
    ).annotate(
        total_tasks=Count(
            'kanban_cards',
            filter=_tag_card_count_filter(request.user, workplace),
            distinct=True,
        )
    )
    queryset = _tag_sort_queryset(queryset, sort)
    total_tags = queryset.count()
    total_pages = max(1, (total_tags + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size

    tags = list(queryset[offset:offset + page_size])
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
        'filters': _tag_filter_options(request.user, workplace=workplace),
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


def _section_accent(section):
    if not section:
        return 'blue'

    accent_names = ['blue', 'teal', 'violet', 'green']
    section_ids = list(section.project.sections.order_by('order', 'created_at').values_list('id', flat=True))

    try:
        section_index = section_ids.index(section.id)
    except ValueError:
        section_index = 0

    return accent_names[section_index % len(accent_names)]


def _tasks_navigation_context(user, active_section=None, active_view=None, workplace=None):
    tasks_qs = _filter_workplace(Kanban.objects.filter(user=user, parent__isnull=True), workplace).select_related('section', 'section__project', 'column').prefetch_related('tags').annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('is_closed_sort', 'task_id')

    projects = list(_filter_workplace(KanbanProject.objects.filter(user=user), workplace).annotate(
        total_tasks=Count('sections__tasks', filter=Q(sections__tasks__user=user, sections__tasks__workplace=workplace, sections__tasks__parent__isnull=True))
    ).prefetch_related(
        Prefetch(
            'project_notes',
            queryset=KanbanProjectNote.objects.select_related('author').order_by('created_at', 'id'),
        ),
        Prefetch('sections', queryset=_filter_workplace(KanbanSection.objects.all(), workplace, field_name='project__workplace').prefetch_related(
            Prefetch('tasks', queryset=tasks_qs)
        ))
    ))

    active_project = active_section.project if active_section else None
    if active_section:
        for project in projects:
            if project.id != active_section.project_id:
                continue
            active_project = project
            active_section = next((section for section in project.sections.all() if section.id == active_section.id), active_section)
            break

    if active_view is None:
        active_view = 'section' if active_section else 'projects'

    if active_section:
        can_create_issue = True
    elif active_project:
        can_create_issue = active_project.sections.exists()
    else:
        can_create_issue = _filter_workplace(KanbanSection.objects.filter(project__user=user), workplace, field_name='project__workplace').exists()

    return {
        'projects': projects,
        'active_project': active_project,
        'active_section': active_section,
        'active_section_accent': _section_accent(active_section),
        'active_view': active_view,
        'tasks': tasks_qs,
        'total_task_count': tasks_qs.count(),
        'total_group_count': len(_sections_for_projects(projects)),
        'tags': _filter_workplace(TaskTag.objects.filter(user=user), workplace).annotate(total_tasks=Count('kanban_cards', filter=Q(kanban_cards__user=user, kanban_cards__workplace=workplace, kanban_cards__parent__isnull=True))),
        'total_tag_count': _filter_workplace(TaskTag.objects.filter(user=user), workplace).count(),
        'can_create_issue': can_create_issue,
    }


def _set_task_status(task, status, user=None):
    user = user or task.user
    if status not in _valid_statuses_for_user(user):
        return False
    task.status = status
    task.save()
    return True


def _set_task_column(task, column_id, user=None):
    user = user or task.user
    column = KanbanBoardColumn.objects.filter(
        id=column_id,
        section=task.section,
        section__project__user=user,
    ).first()
    if not column:
        return False
    task.column = column
    task.save(update_fields=['column'])
    return True


def _record_task_activity(task, actor, action, message='', kind='system', metadata=None):
    return KanbanActivity.objects.create(
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
        'section_id': task.section_id,
        'section_label': section.title if section else '',
        'project_id': project.id if project else None,
        'project_label': project.name if project else '',
        'parent_id': task.parent_id,
        'time_spent_hours': task.time_spent_hours,
        'time_spent_minutes': task.time_spent_minutes,
        'completion_date': task.completion_date,
        'tags': set(task.tags.values_list('id', flat=True)),
        'tag_labels': list(task.tags.order_by('name').values_list('name', flat=True)),
    }


def _task_change_activities(task, before):
    status_labels = _status_labels_for_user(task.user)
    priority_labels = dict(Kanban.PRIORITY_CHOICES)
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
        add_change('status', status_labels.get(before['status'], before['status']), status_labels.get(task.status, task.get_status_display()))
    if before['priority'] != task.priority:
        add_change('priorytet', priority_labels.get(before['priority'], before['priority']), task.get_priority_display())
    if before['title'] != task.title:
        add_change('tytuł', before['title'], task.title)
    if before['description'] != task.description:
        add_change('opis', before['description'], task.description)
    if before['project_id'] != (task.section.project_id if task.section_id else None):
        add_change('przestrzeń robocza', before['project_label'], task.section.project.name if task.section_id else '')
    if before['section_id'] != task.section_id:
        add_change('tablica', before['section_label'], task.section.title if task.section_id else '')
    if before['parent_id'] != task.parent_id:
        add_change('karta nadrzędna', before['parent_id'], task.parent_id)
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
            'message': 'zaktualizował kartę',
            'metadata': {
                'fields': changed_fields,
                'changes': detailed_changes,
            },
        }]
    return []


@login_required
def tasks(request):
    return _tasks_page(request)


@login_required
def task_group(request, section_id):
    active_section = get_object_or_404(
        _filter_workplace(KanbanSection.objects.filter(project__user=request.user), _active_workplace(request), field_name='project__workplace'),
        id=section_id,
    )
    return _tasks_page(request, active_section=active_section)


def _tasks_page(request, active_section=None):
    workplace = _active_workplace(request)
    project_form = KanbanProjectForm(user=request.user, workplace=workplace)
    section_form = KanbanSectionForm()
    tag_form = KanbanTagForm(user=request.user, workplace=workplace)
    board_column_form = KanbanBoardColumnForm()
    all_tasks_view = request.GET.get('view') == 'all-tasks' and not active_section
    my_tasks_view = request.GET.get('view') == 'my-tasks' and not active_section
    all_groups_view = request.GET.get('view') == 'all-groups' and not active_section
    tags_view = request.GET.get('view') == 'tags' and not active_section
    active_project_id = request.POST.get('project_id') if request.method == 'POST' else request.GET.get('project')
    if all_tasks_view or my_tasks_view or all_groups_view or tags_view:
        active_project_id = None
    if active_section:
        active_project_id = active_section.project_id
    active_project_for_form = None
    if active_project_id:
        active_project_for_form = _filter_workplace(KanbanProject.objects.filter(id=active_project_id, user=request.user), workplace).first()
    task_modal_form = KanbanModalForm(user=request.user, workplace=workplace, project=active_project_for_form, section=active_section)
    project_modal_open = False
    project_rename_modal_open = False
    project_rename_form = KanbanProjectRenameForm(user=request.user, workplace=workplace)
    project_rename_project_id = ''
    section_create_modal_open = False
    section_create_project_id = active_project_id or ''
    section_rename_modal_open = False
    section_rename_form = KanbanSectionRenameForm()
    section_rename_section_id = ''
    task_modal_open = False
    tag_modal_open = False
    tag_edit_mode = False
    tag_edit_tag_id = ''

    if request.method == 'POST':
        action = request.POST.get('action')

        def current_board_redirect(focus_column_id=None):
            if active_section:
                url = reverse('kanban:task_group', args=[active_section.id])
                if focus_column_id:
                    url = f"{url}?focus_column={focus_column_id}"
                return redirect(url)
            if all_tasks_view:
                return redirect(f"{reverse('kanban:tasks')}?view=all-tasks")
            if my_tasks_view:
                return redirect(f"{reverse('kanban:tasks')}?view=my-tasks")
            return redirect('kanban:tasks')

        if action == 'create_project':
            project_form = KanbanProjectForm(request.POST, user=request.user, workplace=workplace)
            if project_form.is_valid():
                with transaction.atomic():
                    project = project_form.save(commit=False)
                    project.user = request.user
                    project.workplace = workplace
                    project.save()
                    section_title = project_form.cleaned_data.get('section_title') or 'Nowa Tablica'
                    section = KanbanSection.objects.create(
                        project=project,
                        title=section_title,
                        kind='custom',
                        order=0,
                    )
                messages.success(request, 'Przestrzeń robocza dodana.')
                return redirect(f"{reverse('kanban:tasks')}?project={project.id}")
            project_modal_open = True
            messages.error(request, 'Nie udało się dodać przestrzeni roboczej.')

        if action == 'delete_project':
            project_ids = _posted_ids(request, 'project_ids', 'project_id')
            projects_to_delete = _filter_workplace(KanbanProject.objects.filter(id__in=project_ids, user=request.user), workplace)
            if not projects_to_delete.exists():
                get_object_or_404(_filter_workplace(KanbanProject.objects.filter(user=request.user), workplace), id=request.POST.get('project_id'))
            project_count = projects_to_delete.count()
            task_count = _filter_workplace(Kanban.objects.filter(section__project_id__in=project_ids, user=request.user), workplace).count()
            projects_to_delete.delete()
            if project_count == 1:
                if task_count:
                    messages.success(request, 'Przestrzeń robocza usunięta. Karty przeniesiono do sekcji „Bez przestrzeni roboczej”.')
                else:
                    messages.success(request, 'Przestrzeń robocza usunięta.')
            else:
                messages.success(request, f'Usunięto przestrzenie ({project_count}).')
            return redirect('kanban:tasks')

        if action in ('edit_project', 'rename_project'):
            project = get_object_or_404(_filter_workplace(KanbanProject.objects.filter(user=request.user), workplace), id=request.POST.get('project_id'))
            project_rename_form = KanbanProjectRenameForm(request.POST, instance=project, user=request.user, workplace=workplace)
            if project_rename_form.is_valid():
                project_rename_form.save()
                messages.success(request, 'Przestrzeń robocza zaktualizowana.')
                return redirect(f"{reverse('kanban:tasks')}?project={project.id}")
            project_rename_modal_open = True
            project_rename_project_id = project.id
            active_project_for_form = project
            messages.error(request, 'Nie udało się zaktualizować przestrzeni roboczej.')

        if action in ('add_project_note', 'update_project_notes'):
            project = get_object_or_404(
                _filter_workplace(KanbanProject.objects.filter(user=request.user), workplace),
                id=request.POST.get('project_id'),
            )
            message = (request.POST.get('message') or request.POST.get('description') or '').strip()
            is_ajax_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if message:
                note = KanbanProjectNote.objects.create(project=project, author=request.user, message=message)
                if is_ajax_request:
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Notatka dodana.',
                        'note_html': render_to_string(
                            'tasks/includes/project_note_item.html',
                            {
                                'note': note,
                                'project': project,
                                'next_url': _kanban_next_url(request),
                            },
                            request=request,
                        ),
                    })
                messages.success(request, 'Notatka dodana.')
            else:
                if is_ajax_request:
                    return JsonResponse({'status': 'error', 'message': 'Wpisz treść notatki.'}, status=400)
                messages.error(request, 'Wpisz treść notatki.')
            return redirect(_kanban_next_url(request))

        if action == 'edit_project_note':
            note_queryset = _filter_workplace(
                KanbanProjectNote.objects.filter(author=request.user, project__user=request.user),
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
            return redirect(_kanban_next_url(request))

        if action == 'delete_project_note':
            note_queryset = _filter_workplace(
                KanbanProjectNote.objects.filter(author=request.user, project__user=request.user),
                workplace,
                field_name='project__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), project_id=request.POST.get('project_id'))
            note.delete()
            messages.success(request, 'Notatka usunięta.')
            return redirect(_kanban_next_url(request))

        if action == 'create_section':
            project = get_object_or_404(_filter_workplace(KanbanProject.objects.filter(user=request.user), workplace), id=request.POST.get('project_id'))
            section_form = KanbanSectionForm(request.POST)
            if section_form.is_valid():
                section = section_form.save(commit=False)
                section.project = project
                section.order = project.sections.count()
                section.save()
                messages.success(request, 'Tablica dodana.')
                return redirect('kanban:task_group', section_id=section.id)
            section_create_modal_open = True
            section_create_project_id = project.id
            messages.error(request, 'Nie udało się dodać tablicy.')

        if action == 'create_tag':
            tag_form = KanbanTagForm(request.POST, user=request.user, workplace=workplace)
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
                    return redirect(f"{reverse('kanban:tasks')}?view=tags")
            tag_modal_open = True
            messages.error(request, 'Nie udało się dodać tagu.')

        if action == 'edit_tag':
            tag = get_object_or_404(_filter_workplace(TaskTag.objects.filter(user=request.user), workplace), id=request.POST.get('tag_id'))
            tag_form = KanbanTagForm(request.POST, instance=tag, user=request.user, workplace=workplace)
            if tag_form.is_valid():
                tag_name = tag_form.cleaned_data['name']
                if _filter_workplace(TaskTag.objects.filter(user=request.user, name__iexact=tag_name), workplace).exclude(pk=tag.pk).exists():
                    tag_form.add_error('name', 'Taki tag już istnieje.')
                else:
                    tag_form.save()
                    messages.success(request, 'Tag zaktualizowany.')
                    return redirect(f"{reverse('kanban:tasks')}?view=tags")
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
            return redirect(_kanban_next_url(request))

        if action == 'edit_tag_note':
            note_queryset = _filter_workplace(
                TaskTagNote.objects.filter(author=request.user, tag__user=request.user),
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
            return redirect(_kanban_next_url(request))

        if action == 'delete_tag_note':
            note_queryset = _filter_workplace(
                TaskTagNote.objects.filter(author=request.user, tag__user=request.user),
                workplace,
                field_name='tag__workplace',
            )
            note = get_object_or_404(note_queryset, id=request.POST.get('note_id'), tag_id=request.POST.get('tag_id'))
            note.delete()
            messages.success(request, 'Notatka usunięta.')
            return redirect(_kanban_next_url(request))

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
            return redirect(f"{reverse('kanban:tasks')}?view=tags")

        if action == 'create_board_column':
            if not active_section:
                messages.error(request, 'Wybierz tablicę, żeby dodać kolumnę.')
                return current_board_redirect()
            board_column_form = KanbanBoardColumnForm(request.POST)
            if board_column_form.is_valid():
                column = board_column_form.save(commit=False)
                column.section = active_section
                last_order = KanbanBoardColumn.objects.filter(section=active_section).aggregate(Max('order'))['order__max']
                column.order = (last_order + 1) if last_order is not None else 0
                column.save()
                messages.success(request, 'Kolumna dodana.')
                return current_board_redirect(focus_column_id=column.id)
            messages.error(request, 'Nie udało się dodać kolumny.')

        if action == 'rename_board_column':
            column = get_object_or_404(
                _filter_workplace(KanbanBoardColumn.objects.filter(section__project__user=request.user), workplace, field_name='section__project__workplace'),
                id=request.POST.get('column_id'),
            )
            title = (request.POST.get('title') or '').strip()
            if title:
                column.title = title
                column.save(update_fields=['title'])
                messages.success(request, 'Kolumna zaktualizowana.')
                return current_board_redirect()
            messages.error(request, 'Nazwa kolumny nie może być pusta.')

        if action == 'delete_board_column':
            column = get_object_or_404(
                _filter_workplace(KanbanBoardColumn.objects.filter(section__project__user=request.user), workplace, field_name='section__project__workplace'),
                id=request.POST.get('column_id'),
            )
            section = column.section
            if not KanbanBoardColumn.objects.filter(section=section).exclude(id=column.id).exists():
                messages.error(request, 'Kanban musi mieć przynajmniej jedną kolumnę.')
                return current_board_redirect()
            _filter_workplace(Kanban.objects.filter(user=request.user, section=section, column=column), workplace).delete()
            column.delete()
            for order, remaining_column in enumerate(KanbanBoardColumn.objects.filter(section=section)):
                if remaining_column.order != order:
                    remaining_column.order = order
                    remaining_column.save(update_fields=['order'])
            messages.success(request, 'Kolumna usunięta.')
            return current_board_redirect()

        if action in ('edit_section', 'rename_section'):
            section = get_object_or_404(
                _filter_workplace(KanbanSection.objects.filter(project__user=request.user), workplace, field_name='project__workplace'),
                id=request.POST.get('section_id'),
            )
            section_rename_form = KanbanSectionRenameForm(request.POST, instance=section)
            if section_rename_form.is_valid():
                section_rename_form.save()
                messages.success(request, 'Tablica zaktualizowana.')
                if all_groups_view:
                    return redirect(f"{reverse('kanban:tasks')}?view=all-groups")
                return redirect('kanban:task_group', section_id=section.id)
            section_rename_modal_open = True
            section_rename_section_id = section.id
            active_section = section
            active_project_for_form = section.project
            messages.error(request, 'Nie udało się zaktualizować tablicy.')

        if action == 'delete_section':
            section = get_object_or_404(
                _filter_workplace(KanbanSection.objects.filter(project__user=request.user), workplace, field_name='project__workplace'),
                id=request.POST.get('section_id'),
            )
            project_id = section.project_id
            task_count = _filter_workplace(Kanban.objects.filter(section=section, user=request.user), workplace).count()
            section.delete()
            if task_count:
                messages.success(request, 'Tablica usunięta. Karty przeniesiono do sekcji „Bez przestrzeni roboczej”.')
            else:
                messages.success(request, 'Tablica usunięta.')
            if all_groups_view:
                return redirect(f"{reverse('kanban:tasks')}?view=all-groups")
            return redirect(f"{reverse('kanban:tasks')}?project={project_id}")

        if action == 'create_task':
            section = get_object_or_404(
                _filter_workplace(KanbanSection.objects.filter(project__user=request.user), workplace, field_name='project__workplace'),
                id=request.POST.get('section_id'),
            )
            form = QuickKanbanForm(request.POST)
            if form.is_valid():
                column = KanbanBoardColumn.objects.filter(id=request.POST.get('column_id'), section=section).first()
                if not column:
                    messages.error(request, 'Najpierw dodaj kolumnę, a potem utwórz kartę.')
                    return redirect('kanban:task_group', section_id=section.id)
                task = form.save(commit=False)
                task.user = request.user
                task.section = section
                task.column = column
                task.workplace = workplace
                task.save()
                messages.success(request, 'Karta dodana.')
                return redirect('kanban:task_group', section_id=section.id)
            messages.error(request, 'Nie udało się dodać karty.')

        if action == 'create_task_modal':
            project = None
            project_id = request.POST.get('project_id')
            if project_id:
                project = get_object_or_404(_filter_workplace(KanbanProject.objects.filter(user=request.user), workplace), id=project_id)
            task_modal_form = KanbanModalForm(request.POST, user=request.user, workplace=workplace, project=project, section=active_section)
            if task_modal_form.is_valid():
                task = task_modal_form.save(commit=False)
                task.user = request.user
                task.workplace = workplace
                column = KanbanBoardColumn.objects.filter(
                    id=request.POST.get('column_id'),
                    section=task.section,
                    section__project__user=request.user,
                ).first()
                if column:
                    task.column = column
                task.save()
                task_modal_form.save_m2m()
                task.activities.filter(action='created').update(metadata={'title': task.title})
                messages.success(request, 'Karta dodana.')
                return redirect('kanban:task_group', section_id=task.section_id)
            task_modal_open = True
            messages.error(request, 'Nie udało się dodać karty.')

    tasks_qs = _filter_workplace(Kanban.objects.filter(user=request.user, parent__isnull=True), workplace).select_related('section', 'section__project', 'column').prefetch_related('tags').annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('is_closed_sort', 'task_id')

    projects = list(_filter_workplace(KanbanProject.objects.filter(user=request.user), workplace).annotate(
        total_tasks=Count('sections__tasks', filter=Q(sections__tasks__user=request.user, sections__tasks__workplace=workplace, sections__tasks__parent__isnull=True))
    ).prefetch_related(
        Prefetch(
            'project_notes',
            queryset=KanbanProjectNote.objects.select_related('author').order_by('created_at', 'id'),
        ),
        Prefetch('sections', queryset=_filter_workplace(KanbanSection.objects.all(), workplace, field_name='project__workplace').prefetch_related(
            Prefetch('tasks', queryset=tasks_qs)
        ))
    ))

    active_project = active_section.project if active_section else None
    if active_section:
        for project in projects:
            if project.id != active_section.project_id:
                continue
            active_project = project
            active_section = next((section for section in project.sections.all() if section.id == active_section.id), active_section)
            break

    active_project_id = request.GET.get('project') if not active_section else str(active_section.project_id)
    if active_project_id and not active_project:
        active_project = next((project for project in projects if str(project.id) == active_project_id), None)

    orphan_tasks = tasks_qs.filter(section__isnull=True)
    orphan_status_groups = _decorate_status_groups(projects, orphan_tasks)
    all_status_groups = _status_groups_for_tasks(list(tasks_qs))
    all_task_board_columns = _all_task_board_columns(request.user, tasks_qs, workplace=workplace)
    all_sections = _sections_for_projects(projects)
    total_tag_count = _filter_workplace(TaskTag.objects.filter(user=request.user), workplace).count()
    if active_section:
        can_create_issue = True
    elif active_project:
        can_create_issue = active_project.sections.exists()
    else:
        can_create_issue = _filter_workplace(KanbanSection.objects.filter(project__user=request.user), workplace, field_name='project__workplace').exists()

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
    section_window = _section_window_for_request(request) if active_view == 'all_groups' else {
        'sections': [],
        'query': '',
        'page': 1,
        'total_pages': 1,
        'total_sections': len(all_sections),
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
        'total_tags': total_tag_count,
        'page_size': PROJECT_DEFAULT_PAGE_SIZE,
        'page_size_options': PROJECT_PAGE_SIZE_OPTIONS,
        'page_items': [],
        'has_previous': False,
        'has_next': False,
        'previous_url': '',
        'next_url': '',
        'summary': '',
    }
    tags = tag_window['tags'] if active_view == 'tags' else TaskTag.objects.none()

    context = {
        'projects': projects,
        'active_project': active_project,
        'active_section': active_section,
        'active_section_accent': _section_accent(active_section),
        'active_view': active_view,
        'visible_sections': [active_section] if active_section else [],
        'task_board_columns': _task_board_columns(active_section, active_section.tasks.select_related('column').all()) if active_section else [],
        'all_task_board_columns': all_task_board_columns,
        'orphan_tasks': orphan_tasks,
        'orphan_status_groups': orphan_status_groups,
        'all_status_groups': all_status_groups,
        'all_sections': section_window['sections'] if active_view == 'all_groups' else all_sections,
        'tasks': tasks_qs,
        'total_task_count': tasks_qs.count(),
        'total_group_count': section_window['total_sections'] if active_view == 'all_groups' else len(all_sections),
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
        'section_window': section_window,
        'section_query': section_window['query'],
        'tags': tags,
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
        'total_tag_count': total_tag_count,
        'project_form': project_form,
        'project_rename_form': project_rename_form,
        'project_rename_project_id': project_rename_project_id,
        'section_form': section_form,
        'tag_form': tag_form,
        'board_column_form': board_column_form,
        'status_filter_options': _status_filter_options_for_user(request.user),
        'section_create_modal_open': section_create_modal_open,
        'section_create_project_id': section_create_project_id,
        'section_rename_form': section_rename_form,
        'section_rename_section_id': section_rename_section_id,
        'section_rename_modal_open': section_rename_modal_open,
        'task_modal_form': task_modal_form,
        'quick_task_form': QuickKanbanForm(),
        'project_modal_open': project_modal_open,
        'project_rename_modal_open': project_rename_modal_open,
        'task_modal_open': task_modal_open,
        'tag_modal_open': tag_modal_open,
        'tag_edit_mode': tag_edit_mode,
        'tag_edit_tag_id': tag_edit_tag_id,
        'can_create_issue': can_create_issue,
    }
    return render(request, 'kanban/tasks.html', context)

@login_required
@require_POST
def reorder_board_columns(request, section_id):
    section = get_object_or_404(
        _filter_workplace(KanbanSection.objects.filter(project__user=request.user), _active_workplace(request), field_name='project__workplace'),
        id=section_id,
    )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowe dane'}, status=400)

    column_ids = data.get('column_ids')
    if not isinstance(column_ids, list):
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa kolejność kolumn'}, status=400)

    try:
        ordered_ids = [int(column_id) for column_id in column_ids]
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa kolejność kolumn'}, status=400)

    existing_columns = list(KanbanBoardColumn.objects.filter(section=section))
    existing_ids = [column.id for column in existing_columns]
    if len(ordered_ids) != len(set(ordered_ids)) or set(ordered_ids) != set(existing_ids):
        return JsonResponse({'status': 'error', 'message': 'Kolumny nie należą do tej tablicy'}, status=400)

    columns_by_id = {column.id: column for column in existing_columns}
    with transaction.atomic():
        for order, column_id in enumerate(ordered_ids):
            column = columns_by_id[column_id]
            if column.order != order:
                column.order = order
                column.save(update_fields=['order'])

    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def update_task_status(request, task_id):
    try:
        workplace = _active_workplace(request)
        task = _filter_workplace(Kanban.objects.filter(user=request.user), workplace).get(task_id=task_id)
        data = json.loads(request.body)
        status = data.get('status')
        column_id = data.get('column_id')
        previous_status = task.status
        status_labels = _status_labels_for_user(request.user)

        if column_id:
            if not _set_task_column(task, column_id, request.user):
                return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa kolumna'}, status=400)
        elif status:
            if not _set_task_status(task, status, request.user):
                return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy status'}, status=400)
        else:
            is_completed = data.get('is_completed', False)
            _set_task_status(task, 'closed' if is_completed else 'reopened', request.user)

        if previous_status != task.status:
            _record_task_activity(
                task,
                request.user,
                'status_changed',
                'zmienił status',
                metadata={
                    'from_label': status_labels.get(previous_status, previous_status),
                    'to_label': status_labels.get(task.status, task.get_status_display()),
                    'changes': [{
                        'field': 'status',
                        'from_label': status_labels.get(previous_status, previous_status),
                        'to_label': status_labels.get(task.status, task.get_status_display()),
                    }],
                },
            )
        
        return JsonResponse({
            'status': 'success',
            'new_status_display': status_labels.get(task.status, task.get_status_display()),
            'new_status_code': task.status,
            'new_column_id': task.column_id,
        })
    except Kanban.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Karta nie znaleziona'}, status=404)

@login_required
@require_POST
def delete_task(request, task_id):
    try:
        task = _filter_workplace(Kanban.objects.filter(user=request.user), _active_workplace(request)).get(task_id=task_id)
        task.delete()
        return JsonResponse({'status': 'success', 'message': 'Karta usunięta pomyślnie'})
    except Kanban.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Karta nie znaleziona'}, status=404)

@login_required
@require_POST
def delete_attachment(request, attachment_id):
    try:
        attachment = get_object_or_404(
            _filter_workplace(KanbanAttachment.objects.filter(task__user=request.user), _active_workplace(request), field_name='task__workplace'),
            id=attachment_id,
        )
        attachment.delete()
        return JsonResponse({'status': 'success', 'message': 'Załącznik usunięty pomyślnie'})
    except KanbanAttachment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Załącznik nie znaleziony'}, status=404)


@login_required
def download_attachment(request, attachment_id):
    attachment = get_object_or_404(
        _filter_workplace(
            KanbanAttachment.objects.select_related('task'),
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
            return JsonResponse({'status': 'error', 'message': 'Nie podano ID kart'}, status=400)
        
        user = request.user
        workplace = _active_workplace(request)
        deleted_count = _filter_workplace(Kanban.objects.filter(task_id__in=task_ids, user=user), workplace).delete()[0]
        Kanban._renumber_user_tasks(user, workplace)
        
        return JsonResponse({
            'status': 'success', 
            'message': f'{deleted_count} {"kart" if deleted_count != 1 else "karta"} usuniętych pomyślnie',
            'deleted_count': deleted_count
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy JSON'}, status=400)
    except Exception:
        logger.exception('Failed to delete kanban cards')
        return JsonResponse({'status': 'error', 'message': 'Nie udało się usunąć kart.'}, status=500)

@login_required
@require_POST
def bulk_update_status(request):
    try:
        data = json.loads(request.body)
        task_ids = data.get('task_ids', [])
        status = data.get('status', 'closed')
        
        if not task_ids:
            return JsonResponse({'status': 'error', 'message': 'Nie podano ID kart'}, status=400)
        user = request.user
        workplace = _active_workplace(request)
        if status not in _valid_statuses_for_user(user):
            return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy status'}, status=400)
        
        tasks_to_update = _filter_workplace(Kanban.objects.filter(task_id__in=task_ids, user=user), workplace)
        updated_count = 0
        for task in tasks_to_update:
            _set_task_status(task, status, user)
            updated_count += 1
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Zaktualizowano {updated_count} {"kart" if updated_count != 1 else "kartę"}',
            'updated_count': updated_count
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy JSON'}, status=400)
    except Exception:
        logger.exception('Failed to bulk update kanban status')
        return JsonResponse({'status': 'error', 'message': 'Nie udało się zaktualizować kart.'}, status=500)

def _task_detail_response(request, task_id):
    workplace = _active_workplace(request)
    task = get_object_or_404(
        _filter_workplace(Kanban.objects.select_related('section', 'section__project', 'column', 'parent'), workplace).prefetch_related(
            Prefetch(
                'subtasks',
                queryset=_filter_workplace(Kanban.objects.select_related('section', 'section__project'), workplace).prefetch_related('tags', 'attachments').order_by('task_id'),
            ),
            Prefetch(
                'activities',
                queryset=KanbanActivity.objects.select_related('actor').order_by('created_at', 'id'),
            ),
        ),
        task_id=task_id,
        user=request.user,
    )
    subtask_status_groups = _status_groups_for_tasks(list(task.subtasks.all()))
    can_add_attachments = not task.parent_id
    form = KanbanForm(instance=task, user=request.user, workplace=workplace)
    task_modal_form = SubKanbanModalForm(user=request.user)
    task_modal_open = False

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_subtask_modal':
            task_modal_form = SubKanbanModalForm(request.POST, user=request.user)
            if task_modal_form.is_valid():
                subtask = task_modal_form.save(commit=False)
                subtask.user = request.user
                subtask.parent = task
                subtask.section = task.section
                subtask.workplace = workplace
                subtask.save()
                _record_task_activity(
                    task,
                    request.user,
                    'subtask_created',
                    'dodał podkartę',
                    metadata={
                        'subtask_title': subtask.title,
                        'subtask_task_id': subtask.task_id,
                    },
                )
                messages.success(request, 'Podkarta dodana.')
                return redirect('kanban:view-task', task_id=task.task_id)
            task_modal_open = True
            messages.error(request, 'Nie udało się dodać podkarty.')
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
            detail_route = 'kanban:view-subtask' if task.parent_id else 'kanban:view-task'
            return redirect(detail_route, task_id=task.task_id)
        elif action == 'clear_time_spent':
            if task.has_time_spent:
                before = _task_activity_snapshot(task)
                task.time_spent_hours = None
                task.time_spent_minutes = None
                task.save(update_fields=['time_spent_hours', 'time_spent_minutes'])

                for change in _task_change_activities(task, before):
                    _record_task_activity(
                        task,
                        request.user,
                        change['action'],
                        change['message'],
                        metadata=change['metadata'],
                    )
                messages.success(request, 'Czas pracy usunięty.')
            else:
                messages.info(request, 'Brak czasu pracy do usunięcia.')
            detail_route = 'kanban:view-subtask' if task.parent_id else 'kanban:view-task'
            return redirect(detail_route, task_id=task.task_id)
        else:
            files = request.FILES.getlist('attachments') if can_add_attachments else []
            file_errors = _attachment_validation_errors(files)
            before = _task_activity_snapshot(task)
            form = KanbanForm(request.POST, request.FILES, instance=task, user=request.user, workplace=workplace)
            if form.is_valid() and not file_errors:
                form.save()

                # Handle staged attachment deletions
                deleted_attachments = request.POST.get('deleted_attachments', '')
                deleted_count = 0
                if deleted_attachments:
                    attachment_ids = [int(aid) for aid in deleted_attachments.split(',') if aid.isdigit()]
                    attachments_to_delete = KanbanAttachment.objects.filter(id__in=attachment_ids, task=task)
                    deleted_count = attachments_to_delete.count()
                    attachments_to_delete.delete()

                # Handle new file attachments
                for file in files:
                    KanbanAttachment.objects.create(
                        task=task,
                        file=file
                    )

                for change in _task_change_activities(task, before):
                    _record_task_activity(
                        task,
                        request.user,
                        change['action'],
                        change['message'],
                        metadata=change['metadata'],
                    )
                if files:
                    _record_task_activity(
                        task,
                        request.user,
                        'attachments_added',
                        'dodał załączniki',
                        metadata={'count': len(files)},
                    )
                if deleted_count:
                    _record_task_activity(
                        task,
                        request.user,
                        'attachments_deleted',
                        'usunął załączniki',
                        metadata={'count': deleted_count},
                    )

                messages.success(request, 'Karta zaktualizowana pomyślnie.')
                detail_route = 'kanban:view-subtask' if task.parent_id else 'kanban:view-task'
                return redirect(detail_route, task_id=task.task_id)
            else:
                for error in file_errors:
                    messages.error(request, error)
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
    else:
        form = KanbanForm(instance=task, user=request.user, workplace=workplace)

    context = {
        'form': form,
        'task_modal_form': task_modal_form,
        'task_modal_open': task_modal_open,
        'task': task,
        'can_add_attachments': can_add_attachments,
        'activity_items': task.activities.order_by('-created_at', '-id'),
        'subtask_status_groups': subtask_status_groups,
        **_tasks_navigation_context(
            request.user,
            active_section=task.section,
            active_view='section' if task.section_id else 'all_tasks',
            workplace=workplace,
        ),
    }
    return render(request, 'kanban/view_task.html', context)


@login_required
def view_task(request, task_id):
    return _task_detail_response(request, task_id)

@login_required
def view_subtask(request, task_id):
    return _task_detail_response(request, task_id)
