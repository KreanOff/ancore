"""Team directories and workload summaries within the viewer's live ACL."""
from datetime import timedelta
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, Exists, F, OuterRef, Q
from django.utils import timezone

from accounts.avatar import account_avatar
from workplaces.policy import read_only
from workplaces.services import can_manage_team, workplace_people
from .models import TeamMembership
from .services import app_url, manage_team, space_url, teams_for, visible_items, visible_spaces
from .summary import materialized_summary_items


def administrators(request, team):
    # A Workspace guest cannot administer a team, even with an older team role.
    people = workplace_people(request.workplace).filter(
        Q(pk=request.workplace.owner_id) | Q(pk__in=request.workplace.memberships.filter(
            is_active=True, role__in={'admin', 'member'},
        ).values('user_id')),
    )
    return team.memberships.filter(role='admin', user__in=people)


def directory_context(request):
    query = request.GET.get('q', '').strip()[:120]
    tab = request.GET.get('tab', 'all')
    tab = tab if tab in {'all', 'mine', 'managed'} else 'all'
    sort = request.GET.get('sort', 'name')
    sort = sort if sort in {'name', 'newest', 'members'} else 'name'
    own = TeamMembership.objects.filter(team_id=OuterRef('pk'), user=request.user)
    teams = teams_for(request).annotate(
        is_member=Exists(own), is_admin=Exists(own.filter(role='admin')),
        member_count=Count('memberships', filter=Q(memberships__user__in=workplace_people(request.workplace))),
    )
    if query:
        teams = teams.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if tab == 'mine':
        teams = teams.filter(is_member=True)
    if tab == 'managed':
        if read_only(request):
            teams = teams.none()
        elif not can_manage_team(request.user, request.workplace):
            teams = teams.filter(is_admin=True)
    ordering = {'name': ('name', 'pk'), 'newest': ('-created_at', '-pk'), 'members': ('-member_count', 'name', 'pk')}
    page = Paginator(teams.order_by(*ordering[sort]), 24).get_page(request.GET.get('page'))
    ids = [team.pk for team in page]
    work = materialized_summary_items(visible_items(request).filter(team_id__in=ids))
    counts = {row['team_id']: row['count'] for row in work.exclude(task__status='closed').order_by().values('team_id').annotate(count=Count('pk'))}
    spaces = {row['teams']: row['count'] for row in visible_spaces(request).filter(teams__in=ids).order_by().values('teams').annotate(count=Count('pk', distinct=True))}
    for team in page:
        team.url = app_url(request, f'{team.pk}/', 'teams')
        team.photo_url = team.url + 'photo/' if team.photo else ''
        team.open_count = counts.get(team.pk, 0)
        team.space_count = spaces.get(team.pk, 0)
    base = app_url(request, app='teams')
    return {
        'page': page, 'query': query, 'tab': tab, 'sort': sort,
        'create_url': '' if read_only(request) else base + 'create/',
        'tabs': [{'key': key, 'label': label, 'url': base + '?' + urlencode({'tab': key, 'q': query, 'sort': sort})}
                 for key, label in [('all', 'Wszystkie zespoły'), ('mine', 'Moje zespoły'), ('managed', 'Zarządzane przeze mnie')]],
    }


def detail_context(request, team):
    base = app_url(request, f'{team.pk}/', 'teams')
    view = request.GET.get('view', 'overview')
    view = view if view in {'overview', 'work', 'members', 'spaces'} else 'overview'
    query = request.GET.get('q', '').strip()[:120]
    scope = request.GET.get('scope', 'all')
    scope = scope if scope in {'all', 'open', 'closed', 'overdue', 'due', 'blocked', 'unassigned'} else 'all'
    role = request.GET.get('role', '')
    role = role if role in {'admin', 'member'} else ''
    assignee = request.GET.get('assignee', '')
    if assignee not in {'me', 'unassigned'} and not (assignee.isascii() and assignee.isdecimal() and len(assignee) < 19):
        assignee = ''
    now = timezone.now()
    visible = visible_items(request).filter(team=team)
    summary_items = materialized_summary_items(visible)
    open_filter = ~Q(task__status='closed')
    overdue = open_filter & Q(task__due_at__lt=now)
    due = open_filter & Q(task__due_at__gte=now, task__due_at__lte=now + timedelta(days=7))
    counts = summary_items.aggregate(
        total=Count('pk'), open=Count('pk', filter=open_filter),
        closed=Count('pk', filter=Q(task__status='closed')),
        overdue=Count('pk', filter=overdue), due=Count('pk', filter=due),
        blocked=Count('pk', filter=open_filter & Q(task__blocked_at__isnull=False)),
        unassigned=Count('pk', filter=open_filter & Q(task__assignee__isnull=True)),
    )
    people = workplace_people(request.workplace)
    members = team.memberships.filter(user__in=people).select_related('user').order_by('role', 'user__first_name', 'user__last_name', 'user__email', 'pk')
    member_count = members.count()
    admin_ids = set(administrators(request, team).values_list('pk', flat=True))
    can_manage = manage_team(request, team)
    spaces = visible_spaces(request).filter(teams=team)
    space_count = spaces.count()
    page = None
    items = visible.none()
    workload = []
    if view == 'overview':
        items = visible.exclude(task__status='closed').order_by(F('task__due_at').asc(nulls_last=True), 'pk')[:8]
        loads = summary_items.exclude(task__status='closed').order_by().values(
            'task__assignee_id', 'task__assignee__first_name', 'task__assignee__middle_name', 'task__assignee__last_name', 'task__assignee__email',
        ).annotate(count=Count('pk'), overdue=Count('pk', filter=overdue)).order_by('-count', 'task__assignee_id')[:8]
        for row in loads:
            person_id = row['task__assignee_id']
            workload.append({
                'name': (' '.join(filter(None, [row['task__assignee__first_name'], row['task__assignee__middle_name'], row['task__assignee__last_name']])) or row['task__assignee__email']) if person_id else 'Bez wykonawcy',
                'count': row['count'], 'overdue': row['overdue'],
                'url': base + '?' + urlencode({'view': 'work', 'scope': 'open', 'assignee': person_id or 'unassigned'}),
            })
    elif view == 'work':
        items = visible
        filters = {'open': open_filter, 'closed': Q(task__status='closed'), 'overdue': overdue, 'due': due,
                   'blocked': open_filter & Q(task__blocked_at__isnull=False), 'unassigned': open_filter & Q(task__assignee__isnull=True)}
        if scope in filters:
            items = items.filter(filters[scope])
        if query:
            items = items.filter(Q(task__title__icontains=query) | Q(key__icontains=query))
        if assignee == 'me':
            items = items.filter(task__assignee=request.user)
        elif assignee == 'unassigned':
            items = items.filter(task__assignee__isnull=True)
        elif assignee:
            items = items.filter(task__assignee_id=int(assignee))
        page = Paginator(items.order_by(F('task__due_at').asc(nulls_last=True), 'pk'), 30).get_page(request.GET.get('page'))
        items = page.object_list
    elif view == 'members':
        for term in query.split():
            members = members.filter(Q(user__first_name__icontains=term) | Q(user__middle_name__icontains=term)
                                     | Q(user__last_name__icontains=term) | Q(user__email__icontains=term)
                                     | Q(user__username__icontains=term.lstrip('@')))
        if role:
            members = members.filter(role=role)
        page = Paginator(members, 30).get_page(request.GET.get('page'))
        members = page.object_list
    elif view == 'spaces':
        if query:
            spaces = spaces.filter(Q(name__icontains=query) | Q(key__icontains=query))
        page = Paginator(spaces.order_by('name', 'pk'), 24).get_page(request.GET.get('page'))
        spaces = page.object_list
    member_rows = []
    if view == 'members':
        for member in members:
            member_rows.append({
                'id': member.pk, 'user_id': member.user_id,
                'name': member.user.get_full_name() or member.user.email, 'email': member.user.email,
                'avatar': account_avatar(member.user), 'role': member.role, 'role_label': member.get_role_display(),
                'can_change': can_manage and not (member.pk in admin_ids and len(admin_ids) == 1),
                'edit_url': base + f'members/{member.pk}/edit/',
                'remove_url': base + f'members/{member.pk}/remove/',
            })
    space_rows = list(spaces) if view == 'spaces' else []
    for space in space_rows:
        space.url = space_url(request, space)
    return {
        'team': team, 'team_url': base, 'view': view, 'query': query, 'scope': scope, 'role_filter': role,
        'assignee_filter': assignee, 'page': page, 'items': items, 'member_rows': member_rows,
        'members': members if view == 'members' else [], 'member_count': member_count,
        'spaces': space_rows, 'space_count': space_count, 'counts': counts, 'workload': workload,
        'can_manage': can_manage, 'edit_url': base + 'edit/', 'delete_url': base + 'delete/',
        'member_url': base + 'members/', 'photo_url': base + 'photo/' if team.photo else '',
        'progress': round(counts['closed'] * 100 / counts['total']) if counts['total'] else 0,
        'tabs': [{'key': key, 'label': label, 'url': base + '?view=' + key, 'count': count}
                 for key, label, count in [('overview', 'Podsumowanie', None), ('work', 'Zadania', counts['total']),
                                           ('members', 'Członkowie', member_count), ('spaces', 'Przestrzenie', space_count)]],
    }
