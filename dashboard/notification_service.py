"""Permission-scoped inbox of comments, invitations and personal reminders."""
from datetime import datetime, timedelta
from itertools import islice

from django.core import signing
from django.db import transaction
from django.db.models import BooleanField, Case, Exists, F, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Coalesce
from django.http import Http404
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from tasks.access import visible_to
from accounts.avatar import account_avatar
from kanban.models import KanbanActivity
from tasks.models import TaskActivity
from workplaces.services import pending_invitations_for_user, scoped_workplace_app_path, workplaces_for_user
from .models import ActivityInterest, NotificationState
from .reminders import reminders_for_user

DASHBOARD_NOTIFICATION_LIMIT = 12
INVITATION_SOURCES = {'workplace'}
SOURCES = {'workplace': 'invitation', 'tasks': 'task_activity', 'kanban': 'kanban_activity', 'reminders': 'reminder'}
VIEWS = {'all', 'unread', 'invitations', 'reminders', 'mentions', 'following', 'archived'}
SIGNING_SALT = 'dashboard.notifications.v1'


def _workspace_app_url(workplace, app_name, suffix):
    if workplace:
        return scoped_workplace_app_path(workplace, app_name, suffix=suffix)
    return reverse(f'{app_name}:tasks') + suffix


def _actor_label(actor):
    if not actor:
        return 'System'
    return actor.get_full_name() or actor.get_username()


def _display_label(value, fallback='Zmiana'):
    if not value:
        return fallback
    value = str(value)
    return f'{value[:1].upper()}{value[1:]}'


def _activity_action_message(activity):
    if activity.kind == 'comment':
        return 'dodał komentarz'
    return activity.message or activity.get_action_display().lower()


def _detail_line(label, value='', from_label='', to_label=''):
    return {
        'label': label,
        'value': value,
        'from_label': from_label,
        'to_label': to_label,
    }


def _activity_detail_lines(activity, subitem_label):
    metadata = activity.metadata or {}
    detail_lines = []

    for change in metadata.get('changes') or []:
        detail_lines.append(_detail_line(
            _display_label(change.get('field')),
            from_label=change.get('from_label') or '',
            to_label=change.get('to_label') or '',
        ))

    if detail_lines:
        return detail_lines

    if metadata.get('from_label') or metadata.get('to_label'):
        return [_detail_line(
            'Zmiana',
            from_label=metadata.get('from_label') or '',
            to_label=metadata.get('to_label') or '',
        )]

    if metadata.get('fields'):
        return [_detail_line('Zmienione pola', value=', '.join(metadata.get('fields') or []))]

    if activity.kind == 'comment' and activity.message:
        return [_detail_line('Komentarz', value=activity.message)]

    if activity.action == 'created' and metadata.get('title'):
        return [_detail_line('Tytuł', value=metadata.get('title'))]

    if 'count' in metadata:
        return [_detail_line('Liczba', value=metadata.get('count'))]

    if metadata.get('subtask_title'):
        return [_detail_line(subitem_label, value=metadata.get('subtask_title'))]

    return []


def _activity_location(task, source_label, object_label):
    location_parts = [source_label, f'{object_label} #{task.task_id}', task.title]
    section = task.section
    if section:
        project = section.project
        if project:
            location_parts.append(project.name)
        location_parts.append(section.title)

    column = getattr(task, 'column', None)
    if column:
        location_parts.append(column.title)

    return ' · '.join(part for part in location_parts if part)


def _activity_notification(activity, app_name, source_label, object_label, subitem_label):
    task = activity.task
    route_name = 'view-subtask' if task.parent_id else 'view-task'

    return {
        'source': app_name,
        'source_label': source_label,
        'object_label': object_label,
        'object_id': task.task_id,
        'title': task.title,
        'actor_label': _actor_label(activity.actor),
        'actor_avatar': account_avatar(activity.actor),
        'action_message': _activity_action_message(activity),
        'detail_lines': _activity_detail_lines(activity, subitem_label),
        'location_label': _activity_location(task, source_label, object_label),
        'created_at': activity.created_at,
        'sort_key': (activity.created_at, activity.id),
        'url': _workspace_app_url(task.workplace, app_name, f'{route_name}/{task.task_id}/?task_pk={task.pk}'),
    }


def notification_filters(user, params):
    view = params.get('view', 'all')
    if view not in VIEWS:
        raise ValueError('Nieprawidłowy filtr powiadomień.')
    workspace = str(params.get('workspace') or '')
    if workspace:
        if not workspace.isdecimal() or len(workspace) > 18:
            raise Http404
        if not workplaces_for_user(user).filter(pk=int(workspace)).exists():
            raise Http404
    return {'view': view, 'workspace': workspace}


def notification_sources(user, workspace='', *, include_deleted=False):
    access = (
        Q(task__user=user, task__workplace__isnull=True)
        | Q(task__user_id=F('task__workplace__owner_id'), task__workplace__in=workplaces_for_user(user))
    )
    sources = {
        'workplace': pending_invitations_for_user(user),
        # System activity remains in object history, never in the inbox.
        'tasks': visible_to(TaskActivity.objects.filter(kind='comment'), user).filter(access),
        'kanban': KanbanActivity.objects.none(),  # Historical IDs stay valid but never expose retired records.
        'reminders': reminders_for_user(user),
    }
    for source, queryset in sources.items():
        if source in {'tasks', 'kanban'}:
            interest = ActivityInterest.objects.filter(user=user, **{SOURCES[source]: OuterRef('pk')})
            queryset = queryset.annotate(
                inbox_mentioned=Exists(interest.filter(mentioned=True)),
                inbox_followed=Exists(interest.filter(followed=True)),
            )
        if workspace:
            field = 'workplace_id' if source == 'workplace' else 'task__workplace_id'
            queryset = queryset.filter(**{field: workspace})
        state = NotificationState.objects.filter(user=user, **{SOURCES[source]: OuterRef('pk')})
        default_read = Value(False) if source in INVITATION_SOURCES | {'reminders'} else Case(
            When(actor_id=user.pk, then=Value(True)), default=Value(False), output_field=BooleanField(),
        )
        sources[source] = queryset.annotate(
            inbox_read=Coalesce(Subquery(state.values('is_read')[:1]), default_read),
            inbox_archived=Coalesce(Subquery(state.values('is_archived')[:1]), Value(False)),
            inbox_deleted=Coalesce(Subquery(state.values('is_deleted')[:1]), Value(False)),
        )
        if not include_deleted:
            sources[source] = sources[source].filter(inbox_deleted=False)
    return sources


def filtered_sources(user, filters, asof=None, sources=None):
    view = filters['view']
    if sources is None:
        sources = notification_sources(user, filters['workspace'])
    for source, queryset in sources.items():
        if view in {'mentions', 'following'}:
            if source not in {'tasks', 'kanban'}:
                continue
            queryset = queryset.filter(**{'inbox_mentioned' if view == 'mentions' else 'inbox_followed': True})
        if view == 'invitations' and source not in INVITATION_SOURCES:
            continue
        if view == 'reminders' and source != 'reminders':
            continue
        if view == 'archived' and source in INVITATION_SOURCES:
            continue
        queryset = queryset.filter(inbox_archived=(view == 'archived'))
        if view == 'unread':
            queryset = queryset.filter(inbox_read=False)
        if asof:
            queryset = queryset.filter(created_at__lte=asof)
        yield source, queryset


def notification_summary(user):
    sources = notification_sources(user)
    unread = sum(qs.filter(inbox_read=False, inbox_archived=False).count() for qs in sources.values())
    pending = sum(sources[source].count() for source in INVITATION_SOURCES)
    # A signature lets the UI announce new items even when the unread count stays equal.
    latest = [qs.order_by('-created_at', '-pk').values_list('pk', flat=True).first() for qs in sources.values()]
    return {'unread_count': unread, 'pending_invitation_count': pending, 'revision': latest}


def _token_data(token, user):
    try:
        data = signing.loads(token, salt=SIGNING_SALT, max_age=86400)
        if data['user'] != user.pk:
            raise ValueError
        data['asof'] = datetime.fromisoformat(data['asof'])
        if timezone.is_naive(data['asof']):
            raise ValueError
        data['filters'] = notification_filters(user, data['filters'])
        return data
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        raise ValueError('Lista wygasła. Odśwież powiadomienia i spróbuj ponownie.') from None


def _sort_key(source, row):
    return (0 if source in INVITATION_SOURCES else 1, -row.created_at.timestamp(), -row.pk, source)


def _serialize(source, row):
    if source in INVITATION_SOURCES:
        workplace = row.workplace
        name = workplace.name
        item = {
            'source': source, 'source_label': 'Workspace', 'is_invitation': True, 'object_id': row.pk,
            'title': name, 'actor_label': _actor_label(row.invited_by),
            'actor_avatar': account_avatar(row.invited_by),
            'action_message': 'zaprasza Cię do Workspace',
            'detail_lines': [
                _detail_line('Rola', value=row.get_role_display()),
                _detail_line('Ważne do', value=date_format(timezone.localtime(row.expires_at), 'd.m.Y')),
            ],
            'location_label': name, 'created_at': row.created_at,
            'url': reverse('workplaces:workplaces') + f'?invitation={row.pk}',
            'action_label': 'Przyjmij lub odrzuć zaproszenie',
        }
        item['group_label'] = 'Wymagają Twojej decyzji'
        item['event_label'] = 'Zaproszenie'
    elif source == 'reminders':
        task = row.task
        workplace = task.workplace
        route = 'view-subtask' if task.parent_id else 'view-task'
        item = {
            'source': source, 'source_label': 'Zadania', 'object_id': task.task_id,
            'title': task.title, 'actor_label': 'Ancore', 'actor_avatar': account_avatar(None),
            'action_message': 'przypomina o zadaniu', 'event_label': 'Przypomnienie',
            'detail_lines': [_detail_line('Termin', value=date_format(timezone.localtime(task.due_at), 'd.m.Y H:i'))] if task.due_at else [],
            'location_label': _activity_location(task, 'Zadania', 'Zadanie'),
            'created_at': row.created_at, 'group_label': 'Przypomnienia',
            'url': _workspace_app_url(workplace, 'tasks', f'{route}/{task.task_id}/?task_pk={task.pk}'),
        }
    else:
        labels = ('Zadania', 'Zadanie', 'Podzadanie') if source == 'tasks' else ('Kanban', 'Karta', 'Podkarta')
        item = _activity_notification(row, source, *labels)
        workplace = row.task.workplace
        local_date = timezone.localdate(row.created_at)
        today = timezone.localdate()
        item['group_label'] = ('Dzisiaj' if local_date == today else 'Wczoraj' if local_date == today - timedelta(days=1)
                               else date_format(local_date, 'd E Y'))
        item['event_label'] = 'Komentarz' if row.kind == 'comment' else row.get_action_display()
        if row.inbox_mentioned:
            item['event_label'] = 'Wzmianka'
            item['action_message'] = 'wspomina o Tobie w komentarzu'
        elif row.inbox_followed:
            item['event_label'] = 'Obserwowane · ' + item['event_label']
    item.update(key=f'{source}:{row.pk}', is_read=row.inbox_read, is_archived=row.inbox_archived,
                workplace_label=workplace.name if workplace else 'Osobiste',
                full_date=date_format(timezone.localtime(row.created_at), 'd.m.Y, H:i'))
    return item


def notification_page(user, filters, cursor=''):
    sources = notification_sources(user, filters['workspace'])
    data = {'user': user.pk, 'asof': timezone.now().isoformat(), 'filters': filters}
    anchor = None
    if cursor:
        decoded = _token_data(cursor, user)
        if decoded['filters'] != filters:
            raise ValueError('Filtry zostały zmienione. Odśwież listę.')
        data['asof'] = decoded['asof'].isoformat()
        anchor = decoded.get('anchor')
    asof = datetime.fromisoformat(data['asof'])
    candidates = []
    total = unread = 0
    for source, queryset in filtered_sources(user, filters, asof, sources=sources):
        total += queryset.count()
        unread += queryset.filter(inbox_read=False).count()
        if anchor:
            rank = 0 if source in INVITATION_SOURCES else 1
            if rank < anchor[0]:
                continue
            if rank == anchor[0]:
                created = datetime.fromisoformat(anchor[1])
                older = Q(created_at__lt=created) | Q(created_at=created, pk__lt=anchor[2])
                if source > anchor[3]:
                    older |= Q(created_at=created, pk=anchor[2])
                queryset = queryset.filter(older)
        relations = ['workplace', 'invited_by'] if source in INVITATION_SOURCES else [
            'task', 'task__workplace', 'task__section', 'task__section__project', 'actor',
        ]
        if source == 'kanban':
            relations.append('task__column')
        if source == 'reminders':
            relations.remove('actor')
        rows = queryset.select_related(*relations).order_by('-created_at', '-pk')[:DASHBOARD_NOTIFICATION_LIMIT + 1]
        candidates.extend((source, row) for row in rows)
    candidates.sort(key=lambda pair: _sort_key(*pair))
    visible = candidates[:DASHBOARD_NOTIFICATION_LIMIT]
    snapshot = signing.dumps(data, salt=SIGNING_SALT, compress=True)
    next_cursor = ''
    if len(candidates) > DASHBOARD_NOTIFICATION_LIMIT:
        source, row = visible[-1]
        data['anchor'] = [0 if source in INVITATION_SOURCES else 1, row.created_at.isoformat(), row.pk, source]
        next_cursor = signing.dumps(data, salt=SIGNING_SALT, compress=True)
    items = [_serialize(source, row) for source, row in visible]
    return {'dashboard_notifications': items, 'dashboard_notification_count': total,
            'filtered_unread_count': unread, 'notification_filters': filters,
            'snapshot': snapshot, 'next_cursor': next_cursor}


def _dashboard_notifications(user):
    return notification_page(user, {'view': 'all', 'workspace': ''})['dashboard_notifications']


@transaction.atomic
def change_notification_state(user, params):
    action = params.get('action')
    if action in {'read_all', 'delete_all'}:
        data = _token_data(params.get('snapshot', ''), user)
        values = {'is_read': True}
        if action == 'delete_all':
            values['is_deleted'] = True
        for source, queryset in filtered_sources(user, data['filters'], data['asof']):
            field = SOURCES[source]
            if action == 'read_all':
                queryset = queryset.filter(inbox_read=False)
            ids = queryset.order_by('pk').values_list('pk', flat=True).iterator(chunk_size=500)
            while batch := list(islice(ids, 500)):
                NotificationState.objects.bulk_create(
                    [NotificationState(user=user, **{field + '_id': pk}, **values) for pk in batch],
                    update_conflicts=True, unique_fields=['user', field], update_fields=list(values),
                )
        return
    if action not in {'read', 'unread', 'archive', 'restore', 'delete'}:
        raise ValueError('Nieprawidłowa akcja powiadomienia.')
    source, _, pk = str(params.get('key', '')).partition(':')
    if source not in SOURCES or not pk.isdecimal() or len(pk) > 18:
        raise Http404
    row = notification_sources(user, include_deleted=(action == 'delete'))[source].filter(pk=int(pk)).first()
    if row is None:
        raise Http404
    if source in INVITATION_SOURCES and action in {'archive', 'restore'}:
        raise ValueError('Oczekujące zaproszenie wymaga przyjęcia lub odrzucenia.')
    values = {'is_read': action == 'read'} if action in {'read', 'unread'} else {'is_archived': action == 'archive'}
    if action == 'archive':
        values['is_read'] = True
    elif action == 'delete':
        values = {'is_read': True, 'is_deleted': True}
    NotificationState.objects.update_or_create(user=user, **{SOURCES[source]: row}, defaults=values)
