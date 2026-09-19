from django.apps import apps
from django.db import transaction
from core.task_numbering import lock_task_numbers, renumber_tasks

from .models import SidebarFavorite, Workplace, WorkplaceMembership


ACTIVE_WORKPLACE_SESSION_KEY = 'active_workplace_id'
WORKPLACE_URL_SCOPE_SESSION_KEY = 'workspace_url_scope_enabled'
DEFAULT_WORKPLACE_NAME = 'Moje miejsce pracy'
SCOPED_WORKPLACE_APPS = {'tasks', 'kanban', 'contacts', 'calendar', 'documents', 'office'}


def workplaces_for_user(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return Workplace.objects.none()
    return (
        Workplace.objects
        .filter(owner=user)
        .select_related('owner')
        .distinct()
        .order_by('name', 'id')
    )


def ensure_default_workplace(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None

    existing = workplaces_for_user(user).first()
    if existing:
        return existing

    with transaction.atomic():
        workplace, _created = Workplace.objects.get_or_create(
            owner=user,
            name=DEFAULT_WORKPLACE_NAME,
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

    models_by_owner_field = [
        ('tasks', 'TaskProject', 'user'),
        ('tasks', 'TaskTag', 'user'),
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
