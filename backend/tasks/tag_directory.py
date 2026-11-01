"""Filtering, sorting and incremental loading of the Space tag directory."""
import unicodedata

from django.db.models import Case, Count, IntegerField, Prefetch, Q, Value, When

from workplaces.services import workspace_owner
from .models import TaskTag, TaskTagNote


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


def _tag_sort_value(value):
    return value if value in TAG_SORT_OPTION_MAP else TAG_DEFAULT_SORT


def _choice_rank_case(field_name, choices):
    return Case(
        *[When(**{field_name: value}, then=Value(index)) for index, (value, _label) in enumerate(choices)],
        default=Value(len(choices)),
        output_field=IntegerField(),
    )


def _tag_filter_queryset(
    user,
    query='',
    priority='',
    status='',
    category='',
    scope='',
    owner='',
    workplace=None,
    space=None,
):
    from tasks.tagging import tags_in_scope
    queryset = tags_in_scope(user, workplace, space)
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


def _tag_filter_options(user, workplace=None, space=None):
    from tasks.tagging import tags_in_scope
    queryset = tags_in_scope(user, workplace, space)
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


def tag_window_for_request(request, space):
    from spaces.list_window import LIST_BATCH_SIZE, group_limit
    from spaces.services import space_url, visible_items

    workplace = getattr(request, 'workplace', None)
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
        space=space,
    )
    queryset = queryset.annotate(total_tasks=Count('space_tasks', filter=Q(space_tasks__pk__in=visible_items(request).filter(task__parent__isnull=True).values('task_id')), distinct=True))
    queryset = _tag_sort_queryset(queryset, sort)
    total_tags = queryset.count()
    limit = group_limit(request, 'tags_limit', total_tags)

    tags = list(
        queryset.prefetch_related('related_tags')[:limit]
    )
    for tag in tags:
        related_tags = list(tag.related_tags.all())
        tag.related_tag_ids = ','.join(str(related_tag.id) for related_tag in related_tags)
        tag.related_tags_label = ', '.join(related_tag.name for related_tag in related_tags) or 'Brak powiązań'

    loaded_count = len(tags)
    more_url = ''
    if loaded_count < total_tags:
        params = request.GET.copy()
        params.pop('page', None)
        params.pop('page_size', None)
        params['view'] = 'tags'
        params['tags_limit'] = min(loaded_count + LIST_BATCH_SIZE, total_tags)
        more_url = space_url(request, space) + '?' + params.urlencode()

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
        'filters': _tag_filter_options(workspace_owner(request), workplace=workplace, space=space),
        'total_tags': total_tags,
        'loaded_count': loaded_count,
        'more_url': more_url,
    }
