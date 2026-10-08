"""Personal shortcuts built from existing, access-filtered Workspace data."""

from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Case, Count, DateTimeField, Exists, F, Max, OuterRef, Q, Value, When
from django.db.models.functions import Greatest
from django.utils import timezone

from spaces.defaults import issue_type_icon, template_settings
from spaces.services import decorate_directory_spaces
from tasks.access import visible_to
from tasks.models import Task, TaskProject, TaskSection
from workplaces.services import scoped_workplace_app_path, workspace_owner

from .recent import recent_views

RESULT_LIMIT = 20
VIEWED_PAGE_SIZE = 25
TABS = (
    ('recommended', 'Polecane', 'sparkles'),
    ('assigned', 'Przypisane do mnie', 'user-round-check'),
    ('starred', 'Ulubione', 'star'),
    ('worked', 'Ostatnia praca', 'clock'),
    ('viewed', 'Ostatnio oglądane', 'eye'),
)
EMPTY_STATES = {
    'recommended': ('Jesteś na bieżąco', 'Nie masz otwartych zadań z terminem na najbliższe 7 dni ani z wysokim lub pilnym priorytetem.'),
    'assigned': ('Brak przypisanych zadań', 'Tutaj pojawią się otwarte zadania i podzadania, których jesteś wykonawcą.'),
    'starred': ('Twoje ulubione w jednym miejscu', 'Oznacz gwiazdką przestrzeń, grupę lub zadanie, aby łatwo do nich wrócić.'),
    'worked': ('Tutaj znajdziesz swoją ostatnią pracę', 'Zadania pojawią się po dodaniu komentarza, utworzeniu lub zmianie przez Ciebie.'),
    'viewed': ('Wróć do oglądanych elementów', 'Tutaj pojawią się przestrzenie, grupy i zadania otwarte przez Ciebie w ostatnich 7 dniach w bieżącej sesji przeglądarki.'),
}
EMPTY_ILLUSTRATIONS = {
    'recommended': 'img/empty-states/for-you-tasks-empty.webp',
    'assigned': 'img/empty-states/for-you-assigned-empty.webp',
    'starred': 'img/empty-states/for-you-starred-empty.webp',
    'worked': 'img/empty-states/for-you-worked-empty.webp',
    'viewed': 'img/empty-states/for-you-viewed-empty.webp',
}


def _row(obj, workplace, now):
    app = obj._meta.app_label
    base = scoped_workplace_app_path(workplace, app)
    is_task = isinstance(obj, Task)
    is_project = isinstance(obj, TaskProject)
    labels = {Task: ('Zadanie', 'list-checks'),
              TaskProject: ('Przestrzeń', 'folders'), TaskSection: ('Grupa', 'layers-3')}
    label, icon = labels[type(obj)]
    location = label
    key, status_label, space = '', '', None
    task_row = None
    if is_task:
        status_order = next((n for n, (key, _) in enumerate(Task.STATUS_CHOICES) if key == obj.status), 0)
        detail = 'view-subtask' if obj.parent_id else 'view-task'
        url = f'{base}{detail}/{obj.task_id}/?task_pk={obj.pk}'
        if (obj.section_id and obj.section.project.user_id == workplace.owner_id
                and obj.section.project.workplace_id == workplace.pk):
            location += f' · {obj.section.project.name} · {obj.section.title}'
        status_label = obj.get_status_display()
        key = f'#{obj.task_id}'
        item = getattr(obj, 'work_item', None) if isinstance(obj, Task) else None
        row_item = None
        if item and item.space_id is None:
            key = item.key
            row_item = item
        elif (item and obj.section_id and item.space.project_id == obj.section.project_id
              and item.space.workplace_id == workplace.pk
              and obj.section.project.user_id == workplace.owner_id
              and obj.section.project.workplace_id == workplace.pk):
            key = item.key
            row_item = item
        if row_item:
            statuses = row_item.space.statuses if row_item.space_id else template_settings()['statuses']
            status_order, status_label = next(
                ((n, s['label']) for n, s in enumerate(statuses) if s['key'] == row_item.status),
                (status_order, status_label),
            )
        type_label = row_item.get_work_type_display() if row_item else 'Zadanie'
        task_row = {
            'pk': row_item.pk if row_item else obj.pk,
            'task': obj, 'url': url, 'key': key, 'status_label': status_label, 'status_order': status_order,
            'space': row_item.space if row_item else None,
            'type_label': type_label, 'get_work_type_display': type_label,
            'type_icon': row_item.type_icon if row_item else issue_type_icon('task'),
        }
    elif is_project:
        space = getattr(obj, 'space', None) if isinstance(obj, TaskProject) else None
        url = scoped_workplace_app_path(workplace, 'spaces', f'{space.pk}/') if space else f'{base}?project={obj.pk}'
        key = space.key if space else obj.code
    else:
        url = f'{base}groups/{obj.pk}/'
        location += f' · {obj.project.name}'
    due = obj.due_at if is_task else None
    return {
        'object': obj, 'title': obj.title if not is_project else obj.name,
        'url': url, 'location': location, 'icon': icon, 'is_task': is_task,
        'key': key, 'status_label': status_label, 'space': space,
        'task_row': task_row,
        'due_at': due, 'overdue': bool(due and due < now and obj.status != 'closed'),
        'identity': (obj._meta.label_lower, obj.pk),
    }


def _decorate_task_rows(rows):
    task_ids = [row['object'].pk for row in rows if row['is_task']]
    if not task_ids:
        return
    counts = {row['pk']: row for row in Task.objects.filter(pk__in=task_ids).annotate(
        tags_total=Count('tags', distinct=True), attachments_total=Count('attachments', distinct=True),
    ).values('pk', 'tags_total', 'attachments_total')}
    for row in rows:
        if row['is_task']:
            totals = counts[row['object'].pk]
            row['task_row'].update(tags_count=totals['tags_total'], attachments_count=totals['attachments_total'])


def _group_rows(rows):
    """Group only the displayed rows, retaining date buckets and custom status names."""
    blocks = {}
    for row in rows:
        date_group = row.get('date_group', '')
        block = blocks.setdefault(date_group, {'date_group': date_group, 'task_groups': {}, 'spaces': [], 'other_rows': []})
        if not row['is_task']:
            if row['space']:
                block['spaces'].append(row['space'])
            else:
                block['other_rows'].append(row)
            continue
        task_row = row['task_row']
        key = (row['object'].status, task_row['status_label'])
        group = block['task_groups'].setdefault(key, {
            'category': key[0], 'label': key[1], 'order': task_row['status_order'], 'items': [],
        })
        group['items'].append(row)
    for block in blocks.values():
        block['task_groups'] = sorted(block['task_groups'].values(), key=lambda group: group['order'])
    return list(blocks.values())


def _project_shortcuts(scopes, viewer, workplace, now, recent):
    viewed = {pk: datetime.fromisoformat(at) for (label, pk), at in recent.items()
              if label == TaskProject._meta.label_lower}
    viewed_at = Case(*[When(pk=pk, then=Value(at)) for pk, at in viewed.items()],
                     default=Value(None), output_field=DateTimeField())
    projects = scopes[TaskProject].exclude(status__in=['completed', 'cancelled']).annotate(
        personal_activity_at=Max('sections__tasks__activities__created_at', filter=Q(
            sections__tasks__in=scopes[Task], sections__tasks__activities__actor=viewer,
        )),
        is_starred=Exists(TaskProject.favorited_by.through.objects.filter(
            taskproject_id=OuterRef('pk'), user_id=viewer.pk,
        )),
        last_used_at=Greatest('personal_activity_at', viewed_at),
    ).filter(Q(is_starred=True) | Q(last_used_at__isnull=False)).order_by(
        '-is_starred', F('last_used_at').desc(nulls_last=True), '-created_at', '-pk',
    )
    return [_row(project, workplace, now) for project in projects[:4]]


def _filter_scope(query, model, search, space, projects):
    if search:
        field = 'name' if model is TaskProject else 'title'
        condition = Q(**{f'{field}__icontains': search})
        if model is Task:
            condition |= Q(work_item__key__icontains=search)
        query = query.filter(condition)
    if space:
        selected = projects.filter(space__pk=space) if space.isascii() and space.isdecimal() and len(space) < 19 else projects.none()
        if model is Task:
            query = query.filter(section__project__in=selected)
        elif model is TaskSection:
            query = query.filter(project__in=selected)
        elif model is TaskProject:
            query = query.filter(pk__in=selected)
        else:
            query = query.none()
    return query


def for_you_context(request):
    owner = workspace_owner(request)
    viewer, workplace = request.user, request.workplace
    now = timezone.now()
    tab = request.GET.get('tab', 'recommended')
    if tab not in {key for key, _, _ in TABS}:
        tab = 'recommended'
    base_url = scoped_workplace_app_path(workplace, 'for-you')
    search = request.GET.get('q', '').strip()[:120]
    space_filter = request.GET.get('space', '').strip()[:40]
    recent = {tuple(entry['identity'][2:]): entry['at'] for entry in recent_views(request)}

    def page_url(**values):
        params = {'tab': tab, 'q': search, 'space': space_filter, **values}
        return f'{base_url}?{urlencode({k: v for k, v in params.items() if v})}'

    scopes = {}
    for model in (Task, TaskProject, TaskSection):
        query = visible_to(model.objects.all(), viewer)
        if model is TaskSection:
            query = query.filter(project__user=owner, project__workplace=workplace).select_related('project')
        else:
            query = query.filter(user=owner, workplace=workplace)
            if model is Task:
                query = query.select_related('section__project', 'assignee')
            if model is Task:
                query = query.select_related('work_item__space__configuration', 'work_item__space__project')
            elif model is TaskProject:
                query = query.select_related('space')
        scopes[model] = query

    assigned_count = scopes[Task].filter(assignee=viewer).exclude(status='closed').count()
    projects = _project_shortcuts(scopes, viewer, workplace, now, recent)
    scopes = {model: _filter_scope(query, model, search, space_filter, scopes[TaskProject])
              for model, query in scopes.items()}
    assigned = scopes[Task].filter(assignee=viewer).exclude(status='closed')
    page = None
    # Limit each source in SQL before merging its newest rows.
    if tab in {'assigned', 'recommended'}:
        query = assigned
        if tab == 'recommended':
            query = query.filter(Q(due_at__lte=now + timedelta(days=7)) | Q(priority__in=['urgent', 'high']))
        query = query.order_by('-created_at', '-pk')[:RESULT_LIMIT]
        rows = [_row(obj, workplace, now) for obj in query]
    else:
        sources = []
        recent_by_id = recent
        if tab == 'viewed':
            cutoff = now - timedelta(days=7)
            recent_by_id = {identity: at for identity, at in recent.items()
                            if cutoff <= datetime.fromisoformat(at) <= now}
        for model, query in scopes.items():
            if tab == 'starred':
                query = query.filter(favorited_by=viewer).order_by('-created_at', '-pk')
            elif tab == 'worked':
                if model is not Task:
                    continue
                query = query.annotate(personal_activity_at=Max(
                    'activities__created_at', filter=Q(activities__actor=viewer),
                )).filter(personal_activity_at__isnull=False).order_by('-personal_activity_at', '-pk')
            else:
                ids = [pk for (label, pk) in recent_by_id if label == model._meta.label_lower]
                query = query.filter(pk__in=ids)
            sources.append(query)

        if tab == 'viewed':
            total = sum(query.count() for query in sources)
            page = Paginator(range(total), VIEWED_PAGE_SIZE).get_page(request.GET.get('page'))
        candidates = []
        for query in sources:
            batch = query if tab == 'viewed' else query[:RESULT_LIMIT]
            for obj in batch:
                row = _row(obj, workplace, now)
                if tab == 'viewed':
                    row['recent_at'] = datetime.fromisoformat(recent_by_id[row['identity']])
                elif tab == 'worked':
                    row['recent_at'] = obj.personal_activity_at
                candidates.append(row)
        if tab == 'starred':
            candidates.sort(key=lambda row: (row['object'].created_at, row['identity']), reverse=True)
        else:
            candidates.sort(key=lambda row: (row['recent_at'], row['identity']), reverse=True)
        rows = (candidates[(page.number - 1) * VIEWED_PAGE_SIZE:page.end_index()]
                if tab == 'viewed' else candidates[:RESULT_LIMIT])

    _decorate_task_rows(rows)
    decorate_directory_spaces(request, [row['space'] for row in rows if row['space']])
    for row in rows:
        if row.get('recent_at'):
            age = (timezone.localdate(now) - timezone.localdate(row['recent_at'])).days
            row['date_group'] = 'Dzisiaj' if age <= 0 else 'Wczoraj' if age == 1 else 'Ostatnie 7 dni' if tab == 'viewed' or age < 7 else 'Wcześniej'
    return {
        'for_you_tab': tab,
        'for_you_tabs': [{'key': key, 'label': label, 'icon': icon, 'url': page_url(tab=key)} for key, label, icon in TABS],
        'for_you_rows': rows, 'for_you_groups': _group_rows(rows), 'for_you_page': page,
        'for_you_previous': page_url(page=page.number - 1) if page and page.has_previous() else '',
        'for_you_next': page_url(page=page.number + 1) if page and page.has_next() else '',
        'for_you_empty': EMPTY_STATES[tab], 'for_you_assigned_count': assigned_count,
        'for_you_empty_illustration': EMPTY_ILLUSTRATIONS[tab],
        'for_you_projects': projects,
        'for_you_filtered': bool(search or space_filter),
        'for_you_clear_url': f'{base_url}?{urlencode({"tab": tab})}',
        'for_you_projects_url': scoped_workplace_app_path(workplace, 'spaces'),
        'for_you_tasks_url': scoped_workplace_app_path(workplace, 'spaces', 'items/', 'assignee=me'),
    }
