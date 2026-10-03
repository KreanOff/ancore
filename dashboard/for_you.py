"""Personal shortcuts built from existing, access-filtered Workspace data."""

from datetime import datetime, timedelta

from django.core.paginator import Paginator
from django.db.models import F, Max, Q
from django.utils import timezone

from kanban.models import Kanban, KanbanProject, KanbanSection
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
    'starred': ('Twoje ulubione w jednym miejscu', 'Oznacz gwiazdką zadanie, projekt, grupę, przestrzeń Kanban lub tablicę, aby łatwo do nich wrócić.'),
    'worked': ('Tutaj znajdziesz swoją ostatnią pracę', 'Zadania i karty pojawią się po dodaniu komentarza, utworzeniu lub zmianie przez Ciebie.'),
    'viewed': ('Wróć do oglądanych elementów', 'Otwieraj zadania, projekty, grupy lub tablice. Ostatnio oglądane zapisujemy w bieżącej sesji przeglądarki.'),
}
CAPTIONS = {
    'recommended': 'Twoje otwarte zadania: zaległe, z terminem w najbliższych 7 dniach oraz z wysokim lub pilnym priorytetem.',
    'assigned': 'Otwarte zadania i podzadania, których jesteś wykonawcą.',
    'starred': 'Zadania, projekty, grupy, przestrzenie Kanban i tablice oznaczone przez Ciebie gwiazdką.',
    'worked': 'Twoje ostatnio utworzone, zmienione lub skomentowane zadania i karty Kanban.',
    'viewed': 'Ostatnio otwierane elementy w bieżącej sesji przeglądarki.',
}


def _row(obj, workplace, now):
    app = obj._meta.app_label
    base = scoped_workplace_app_path(workplace, app)
    is_task = isinstance(obj, (Task, Kanban))
    is_project = isinstance(obj, (TaskProject, KanbanProject))
    labels = {Task: ('Zadanie', 'list-checks'), Kanban: ('Karta Kanban', 'kanban'),
              TaskProject: ('Projekt', 'briefcase-business'), TaskSection: ('Grupa', 'layers-3'),
              KanbanProject: ('Przestrzeń Kanban', 'folders'), KanbanSection: ('Tablica', 'kanban')}
    label, icon = labels[type(obj)]
    location = label
    if is_task:
        detail = 'view-subtask' if obj.parent_id else 'view-task'
        url = f'{base}{detail}/{obj.task_id}/?task_pk={obj.pk}'
        if (obj.section_id and obj.section.project.user_id == workplace.owner_id
                and obj.section.project.workplace_id == workplace.pk):
            location += f' · {obj.section.project.name} · {obj.section.title}'
    elif is_project:
        url = f'{base}?project={obj.pk}'
    else:
        url = f'{base}groups/{obj.pk}/'
        location += f' · {obj.project.name}'
    due = obj.due_at if is_task else None
    return {
        'object': obj, 'title': obj.title if not is_project else obj.name,
        'url': url, 'location': location, 'icon': icon, 'is_task': is_task,
        'due_at': due, 'overdue': bool(due and due < now and obj.status != 'closed'),
        'identity': (obj._meta.label_lower, obj.pk),
    }


def for_you_context(request):
    owner = workspace_owner(request)
    viewer, workplace = request.user, request.workplace
    now = timezone.now()
    tab = request.GET.get('tab', 'recommended')
    if tab not in dict(TABS):
        tab = 'recommended'
    base_url = scoped_workplace_app_path(workplace, 'for-you')
    scopes = {}
    for model in (Task, Kanban, TaskProject, KanbanProject, TaskSection, KanbanSection):
        query = visible_to(model.objects.all(), viewer)
        if model in (TaskSection, KanbanSection):
            query = query.filter(project__user=owner, project__workplace=workplace).select_related('project')
        else:
            query = query.filter(user=owner, workplace=workplace)
            if model in (Task, Kanban):
                query = query.select_related('section__project')
        scopes[model] = query

    assigned = scopes[Task].filter(assignee=viewer).exclude(status='closed')
    assigned_count = assigned.count()
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
        recent = recent_views(request)
        recent_by_id = {tuple(entry['identity'][2:]): entry['at'] for entry in recent}
        for model, query in scopes.items():
            if tab == 'starred':
                if model is Kanban:
                    continue  # Cards do not have personal favorites.
                field = 'name' if model in (TaskProject, KanbanProject) else 'title'
                query = query.filter(favorited_by=viewer).order_by(field, 'pk')
            elif tab == 'worked':
                if model not in (Task, Kanban):
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

    projects = scopes[TaskProject].exclude(status__in=['completed', 'cancelled']).annotate(
        personal_activity_at=Max('sections__tasks__activities__created_at', filter=Q(
            sections__tasks__in=scopes[Task], sections__tasks__activities__actor=viewer,
        )),
    ).filter(Q(favorited_by=viewer) | Q(personal_activity_at__isnull=False)).distinct().order_by(
        F('personal_activity_at').desc(nulls_last=True), '-created_at', '-pk',
    )
    return {
        'for_you_tab': tab, 'for_you_caption': CAPTIONS[tab],
        'for_you_tabs': [{'key': key, 'label': label, 'url': f'{base_url}?tab={key}'} for key, label in TABS],
        'for_you_rows': rows, 'for_you_page': page,
        'for_you_previous': f'{base_url}?tab={tab}&page={page.number - 1}' if page.has_previous() else '',
        'for_you_next': f'{base_url}?tab={tab}&page={page.number + 1}' if page.has_next() else '',
        'for_you_empty': EMPTY_STATES[tab], 'for_you_assigned_count': assigned_count,
        'for_you_projects': [_row(obj, workplace, now) for obj in projects[:4]],
        'for_you_projects_url': scoped_workplace_app_path(workplace, 'tasks'),
    }
