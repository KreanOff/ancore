"""Personal shortcuts built from existing, access-filtered Workspace data."""

from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Case, DateTimeField, Exists, F, Max, OuterRef, Q, Value, When
from django.db.models.functions import Greatest
from django.utils import timezone

from tasks.access import visible_to
from tasks.models import Task, TaskProject, TaskSection
from workplaces.services import scoped_workplace_app_path, workspace_owner

from .recent import recent_views

PAGE_SIZE = 25
TABS = (
    ('recommended', 'Polecane'),
    ('assigned', 'Przypisane do mnie'),
    ('starred', 'Ulubione'),
    ('worked', 'Ostatnia praca'),
    ('viewed', 'Ostatnio oglądane'),
)
EMPTY_STATES = {
    'recommended': ('Jesteś na bieżąco', 'Nie masz otwartych zadań z terminem na najbliższe 7 dni ani z wysokim lub pilnym priorytetem.'),
    'assigned': ('Brak przypisanych zadań', 'Tutaj pojawią się otwarte zadania i podzadania, których jesteś wykonawcą.'),
    'starred': ('Twoje ulubione w jednym miejscu', 'Oznacz gwiazdką przestrzeń, grupę lub zadanie, aby łatwo do nich wrócić.'),
    'worked': ('Tutaj znajdziesz swoją ostatnią pracę', 'Zadania pojawią się po dodaniu komentarza, utworzeniu lub zmianie przez Ciebie.'),
    'viewed': ('Wróć do oglądanych elementów', 'Otwieraj przestrzenie, grupy i zadania. Ostatnio oglądane zapisujemy w bieżącej sesji przeglądarki.'),
}
CAPTIONS = {
    'recommended': 'Twoje otwarte zadania: zaległe, z terminem w najbliższych 7 dniach oraz z wysokim lub pilnym priorytetem.',
    'assigned': 'Otwarte zadania i podzadania, których jesteś wykonawcą.',
    'starred': 'Przestrzenie, grupy i zadania oznaczone przez Ciebie gwiazdką.',
    'worked': 'Twoje ostatnio utworzone, zmienione lub skomentowane zadania.',
    'viewed': 'Ostatnio otwierane elementy w bieżącej sesji przeglądarki.',
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
    if is_task:
        detail = 'view-subtask' if obj.parent_id else 'view-task'
        url = f'{base}{detail}/{obj.task_id}/?task_pk={obj.pk}'
        if (obj.section_id and obj.section.project.user_id == workplace.owner_id
                and obj.section.project.workplace_id == workplace.pk):
            location += f' · {obj.section.project.name} · {obj.section.title}'
        status_label = obj.get_status_display()
        key = f'#{obj.task_id}'
        item = getattr(obj, 'work_item', None) if isinstance(obj, Task) else None
        if item and item.space_id is None:
            key = item.key
        elif (item and obj.section_id and item.space.project_id == obj.section.project_id
              and item.space.workplace_id == workplace.pk
              and obj.section.project.user_id == workplace.owner_id
              and obj.section.project.workplace_id == workplace.pk):
            key = item.key
            status_label = next((s['label'] for s in item.space.statuses if s['key'] == item.status), status_label)
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
        'due_at': due, 'overdue': bool(due and due < now and obj.status != 'closed'),
        'identity': (obj._meta.label_lower, obj.pk),
    }


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
    if tab not in dict(TABS):
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
                query = query.select_related('section__project')
            if model is Task:
                query = query.select_related('work_item__space__configuration')
            elif model is TaskProject:
                query = query.select_related('space')
        scopes[model] = query

    assigned_count = scopes[Task].filter(assignee=viewer).exclude(status='closed').count()
    projects = _project_shortcuts(scopes, viewer, workplace, now, recent)
    spaces = list(scopes[TaskProject].filter(space__isnull=False).order_by('name', 'pk'))
    scopes = {model: _filter_scope(query, model, search, space_filter, scopes[TaskProject])
              for model, query in scopes.items()}
    assigned = scopes[Task].filter(assignee=viewer).exclude(status='closed')
    # Keep pagination in SQL for assignments. Other tabs merge several models;
    # only each source's first N rows can contribute to the first N merged rows.
    if tab in {'assigned', 'recommended'}:
        query = assigned
        if tab == 'recommended':
            query = query.filter(Q(due_at__lte=now + timedelta(days=7)) | Q(priority__in=['urgent', 'high']))
        query = query.order_by(F('due_at').asc(nulls_last=True), '-created_at', '-pk')
        page = Paginator(query, PAGE_SIZE).get_page(request.GET.get('page'))
        rows = [_row(obj, workplace, now) for obj in page]
    else:
        sources = []
        recent_by_id = recent
        for model, query in scopes.items():
            if tab == 'starred':
                field = 'name' if model is TaskProject else 'title'
                query = query.filter(favorited_by=viewer).order_by(field, 'pk')
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

        total = sum(query.count() for query in sources)
        # A numeric range lets Paginator validate even a huge/invalid page before queries.
        page = Paginator(range(total), PAGE_SIZE).get_page(request.GET.get('page'))
        candidates = []
        for query in sources:
            batch = query if tab == 'viewed' else query[:page.end_index()]
            for obj in batch:
                row = _row(obj, workplace, now)
                if tab == 'viewed':
                    row['recent_at'] = datetime.fromisoformat(recent_by_id[row['identity']])
                elif tab == 'worked':
                    row['recent_at'] = obj.personal_activity_at
                candidates.append(row)
        if tab == 'starred':
            # Group by kind, preserving each source's database title ordering.
            candidates.sort(key=lambda row: (row['object']._meta.label_lower,))
        else:
            candidates.sort(key=lambda row: (row['recent_at'], row['identity']), reverse=True)
        rows = candidates[(page.number - 1) * PAGE_SIZE:page.end_index()]

    for row in rows:
        if row.get('recent_at'):
            age = (timezone.localdate(now) - timezone.localdate(row['recent_at'])).days
            row['date_group'] = 'Dzisiaj' if age <= 0 else 'Wczoraj' if age == 1 else 'Ostatnie 7 dni' if age < 7 else 'Wcześniej'
    return {
        'for_you_tab': tab, 'for_you_caption': CAPTIONS[tab],
        'for_you_tabs': [{'key': key, 'label': label, 'url': page_url(tab=key)} for key, label in TABS],
        'for_you_rows': rows, 'for_you_page': page,
        'for_you_previous': page_url(page=page.number - 1) if page.has_previous() else '',
        'for_you_next': page_url(page=page.number + 1) if page.has_next() else '',
        'for_you_empty': EMPTY_STATES[tab], 'for_you_assigned_count': assigned_count,
        'for_you_projects': projects, 'for_you_spaces': spaces,
        'for_you_search': search, 'for_you_space': space_filter,
        'for_you_space_unavailable': bool(space_filter and all(str(project.space.pk) != space_filter for project in spaces)),
        'for_you_filtered': bool(search or space_filter), 'for_you_url': base_url,
        'for_you_clear_url': f'{base_url}?{urlencode({"tab": tab})}',
        'for_you_projects_url': scoped_workplace_app_path(workplace, 'spaces'),
        'for_you_tasks_url': scoped_workplace_app_path(workplace, 'spaces', 'items/', 'assignee=me'),
    }
