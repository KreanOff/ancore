from random import choice

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse
from core.task_numbering import lock_task_numbers, renumber_tasks

from .models import SidebarFavorite, Workplace, WorkplaceInvitation, WorkplaceMembership


ACTIVE_WORKPLACE_SESSION_KEY = 'active_workplace_id'
WORKPLACE_URL_SCOPE_SESSION_KEY = 'workspace_url_scope_enabled'
DEFAULT_WORKPLACE_NAMES = (
    'Biuro Latających Pierogów',
    'Sztab Kofeinowych Pingwinów',
    'Baza Turboślimaków',
    'Królestwo Zaginionych Długopisów',
    'Departament Dzielnych Kapibar',
    'Fabryka Genialnych Wymówek',
    'Centrum Dowodzenia Chomików',
    'Agencja Kosmicznych Ogórków',
    'Pracownia Tańczących Ziemniaków',
    'Klub Bardzo Zajętych Kotów',
    'Bunkier Ostatniego Ciastka',
    'Akademia Drzemek Strategicznych',
    'Liga Nieustraszonych Naleśników',
    'Biuro Spraw Prawie Pilnych',
    'Sztab Gumowych Kaczek',
    'Baza Tajnych Skarpetek',
    'Królestwo Wiecznej Przerwy',
    'Departament Kawy i Chaosu',
    'Fabryka Pomysłów z Kosmosu',
    'Centrum Dowodzenia Kanapek',
    'Agencja Sprytnych Leniwców',
    'Pracownia Mruczących Silników',
    'Klub Wędrujących Kubków',
    'Bunkier Zapomnianych Haseł',
)
SCOPED_WORKPLACE_APPS = {'tasks', 'kanban', 'calendar', 'documents', 'office', 'resources', 'for-you', 'spaces', 'space', 'teams', 'dashboards', 'filters'}


def workplace_management_url(workplace, view='members'):
    """Management selection never changes the active business-data Workspace."""
    url = f'{reverse("workplaces:workplaces")}?workspace={workplace.pk}'
    if view == 'received':
        view = 'workspaces'
    if view in {'invitations', 'workspaces'}:
        url += f'&view={view}'
    return url


def pending_invitations_for_user(user):
    """Incoming invitations are visible before membership, across Workspaces."""
    if not user or not getattr(user, 'is_authenticated', False) or not user.is_active:
        return WorkplaceInvitation.objects.none()
    return WorkplaceInvitation.objects.filter(
        recipient=user, status=WorkplaceInvitation.Status.PENDING,
        expires_at__gt=timezone.now(),
    )


def workplaces_for_user(user):
    if not user or not getattr(user, 'is_authenticated', False) or not user.is_active:
        return Workplace.objects.none()
    return (
        Workplace.objects
        .filter(Q(owner=user) | Q(pk__in=WorkplaceMembership.objects.filter(
            user=user, is_active=True, role__in=['admin', 'member'],
        ).values('workplace_id')))
        .select_related('owner')
        .distinct()
        .order_by('name', 'id')
    )


def workplace_role(user, workplace):
    if not user or not user.is_authenticated or not user.is_active or not workplace:
        return ''
    if workplace.owner_id == user.pk:
        return WorkplaceMembership.Role.OWNER
    role = workplace.memberships.filter(user=user, is_active=True).values_list('role', flat=True).first()
    return role if role in {'admin', 'member'} else ''


def can_manage_team(user, workplace):
    return workplace_role(user, workplace) in {'owner', 'admin'}


def workspace_owner(request):
    """Storage principal for team data; request.user remains the actual actor.

    Existing owner + Workspace constraints and numbering stay intact. Joining a
    Workspace grants access to its owner's data in that Workspace only.
    Project privacy is an additional filter based on request.user.
    """
    workplace = getattr(request, 'workplace', None)
    if workplace is None:
        return request.user
    key = (request.user.pk, workplace.pk)
    if getattr(request, '_workspace_owner_key', None) != key:
        if not workplace_role(request.user, workplace):
            raise PermissionDenied
        request._workspace_owner_key = key
        request._workspace_owner = workplace.owner
    return request._workspace_owner


def workplace_people(workplace, user=None):
    users = get_user_model().objects.filter(is_active=True)
    if workplace is None:
        return users.filter(pk=getattr(user, 'pk', None))
    return users.filter(
        Q(pk=workplace.owner_id) | Q(workplace_memberships__workplace=workplace, workplace_memberships__is_active=True),
    ).distinct().order_by('first_name', 'last_name', 'email')


def ensure_default_workplace(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None

    existing = workplaces_for_user(user).first()
    if existing:
        return existing

    with transaction.atomic():
        # Serialize first visits: random names no longer provide a shared lookup key.
        get_user_model().objects.select_for_update().get(pk=user.pk)
        existing = workplaces_for_user(user).first()
        if existing:
            return existing

        workplace = Workplace.objects.create(
            owner=user,
            name=choice(DEFAULT_WORKPLACE_NAMES),
        )
        WorkplaceMembership.objects.get_or_create(
            workplace=workplace,
            user=user,
            defaults={'role': WorkplaceMembership.Role.OWNER},
        )
        SidebarFavorite.objects.get_or_create(
            workplace=workplace,
            user=user,
            item_key='dashboard',
        )
    return workplace


def set_active_workplace(request, workplace):
    request.session[ACTIVE_WORKPLACE_SESSION_KEY] = workplace.pk
    request.session.modified = True
    request.workplace = workplace
    backfill_legacy_records_for_workplace(request.user, workplace)
    return workplace


def backfill_legacy_records_for_workplace(user, workplace):
    if not user or not getattr(user, 'is_authenticated', False) or workplace is None:
        return
    # A member's old personal records must never move into another team's space.
    if workplace.owner_id != user.pk:
        return

    models_by_owner_field = [
        ('tasks', 'TaskProject', 'user'),
        ('tasks', 'Task', 'user'),
        ('kanban', 'KanbanProject', 'user'),
        ('kanban', 'Kanban', 'user'),
        ('contacts', 'Company', 'owner'),
        ('contacts', 'Contact', 'user'),
        ('contacts', 'UserContact', 'owner'),
        ('planner', 'CalendarEvent', 'user'),
    ]

    for app_label, model_name, owner_field in models_by_owner_field:
        model = apps.get_model(app_label, model_name)
        legacy = model.objects.filter(
            **{f'{owner_field}_id': user.pk, 'workplace__isnull': True},
        )
        if model_name in {'Task', 'Kanban'}:
            if legacy.exists():
                with lock_task_numbers(user.pk):
                    if legacy.update(workplace_id=workplace.pk):
                        renumber_tasks(model, user, workplace)
        else:
            legacy.update(workplace_id=workplace.pk)


def enable_workspace_url_scope(request):
    request.session[WORKPLACE_URL_SCOPE_SESSION_KEY] = True
    request.session.modified = True


def workspace_url_scope_enabled(request):
    return bool(request.session.get(WORKPLACE_URL_SCOPE_SESSION_KEY))


def scoped_workplace_app_path(workplace, app_label='tasks', suffix='', query_string=''):
    app_label = app_label if app_label in SCOPED_WORKPLACE_APPS else 'tasks'
    clean_suffix = (suffix or '').lstrip('/')
    path = f'/workplaces/{workplace.slug}/{app_label}/'
    if clean_suffix:
        path = f'{path}{clean_suffix}'
    if query_string:
        path = f'{path}?{query_string.lstrip("?")}'
    return path


def legacy_app_path_to_scoped(workplace, path_info, query_string=''):
    clean_path = (path_info or '').lstrip('/')
    app_label, separator, suffix = clean_path.partition('/')
    if app_label not in SCOPED_WORKPLACE_APPS:
        return None
    return scoped_workplace_app_path(workplace, app_label, suffix if separator else '', query_string)


def get_active_workplace(request):
    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return None

    workplace_id = request.session.get(ACTIVE_WORKPLACE_SESSION_KEY)
    if workplace_id:
        workplace = workplaces_for_user(user).filter(pk=workplace_id).first()
        if workplace:
            request.workplace = workplace
            backfill_legacy_records_for_workplace(user, workplace)
            return workplace

    workplace = ensure_default_workplace(user)
    if workplace:
        set_active_workplace(request, workplace)
    return workplace
