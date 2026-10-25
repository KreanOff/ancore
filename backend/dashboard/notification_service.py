"""Permission-scoped inbox of comments and personal reminders."""
from datetime import datetime
from itertools import islice

from django.core import signing
from django.db import transaction
from django.db.models import BooleanField, Case, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Coalesce
from django.http import Http404
from django.utils import timezone
from django.utils.formats import date_format

from accounts.avatar import account_avatar
from workplaces.services import scoped_workplace_app_path, workplaces_for_user
from .models import NotificationState
from .reminders import space_reminders_for_user
from spaces.models import SpaceTaskActivity
from spaces.access import visible_to as space_visible_to

DASHBOARD_NOTIFICATION_LIMIT = 12
SOURCES = {'spaces': 'space_activity', 'space-reminders': 'space_reminder'}
VIEWS = {'all', 'unread', 'reminders', 'mentions', 'following', 'archived'}
SIGNING_SALT = 'dashboard.notifications.v1'


def _actor_label(actor):
    if not actor:
        return 'System'
    return actor.get_full_name() or actor.get_username()


def _display_label(value, fallback='Zmiana'):
    if not value:
        return fallback
    value = str(value)
    return f'{value[:1].upper()}{value[1:]}'


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
    sources = {
        'space-reminders': space_reminders_for_user(user),
        'spaces': space_visible_to(SpaceTaskActivity.objects.filter(kind='comment'), user),
    }
    for source, queryset in sources.items():
        if source == 'spaces':
            queryset = queryset.annotate(inbox_mentioned=Case(When(Q(metadata__mentions__contains=[{'user_id': user.pk}]) & ~Q(actor_id=user.pk), then=Value(True)), default=Value(False), output_field=BooleanField()), inbox_followed=Value(False, output_field=BooleanField()))
        if workspace:
            queryset = queryset.filter(task__space__workplace_id=workspace)
        state = NotificationState.objects.filter(user=user, **{SOURCES[source]: OuterRef('pk')})
        default_read = Value(False) if source == 'space-reminders' else Case(
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
            if source != 'spaces':
                continue
            queryset = queryset.filter(**{'inbox_mentioned' if view == 'mentions' else 'inbox_followed': True})
        if view == 'reminders' and source != 'space-reminders':
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
    # A signature lets the UI announce new items even when the unread count stays equal.
    latest = [qs.order_by('-created_at', '-pk').values_list('pk', flat=True).first() for qs in sources.values()]
    return {'unread_count': unread, 'revision': latest}


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
    return (-row.created_at.timestamp(), -row.pk, source)


def _serialize(source, row):
    if source in {'spaces', 'space-reminders'}:
        from spaces.services import space_url
        task = row.task
        workplace = task.space.workplace
        key = task.work_item.key
        reminder = source == 'space-reminders'
        item = {'source': source, 'source_label': 'Zadania przestrzeni', 'object_label': 'Zadanie', 'object_id': key,
                'title': task.title, 'actor_label': 'Ancore' if reminder else _actor_label(row.actor),
                'actor_avatar': account_avatar(None if reminder else row.actor), 'action_message': 'przypomina o zadaniu' if reminder else 'dodał komentarz',
                'detail_lines': ([_detail_line('Termin', value=date_format(timezone.localtime(task.due_at), 'd.m.Y H:i'))] if task.due_at else []) if reminder else _activity_detail_lines(row, 'Podzadanie'),
                'location_label': f'{task.space.name} · {key} · {task.title}', 'created_at': row.created_at,
                'url': scoped_workplace_app_path(workplace, 'space', f'{task.space.slug}/tasks/{key}/?view=list'),
                'group_label': 'Przypomnienia' if reminder else ('Dzisiaj' if timezone.localdate(row.created_at) == timezone.localdate() else date_format(timezone.localdate(row.created_at), 'd E Y')),
                'event_label': 'Przypomnienie' if reminder else 'Komentarz'}
        if not reminder and row.inbox_mentioned:
            item['event_label'], item['action_message'] = 'Wzmianka', 'wspomina o Tobie w komentarzu'
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
    total = unread = deletable = 0
    for source, queryset in filtered_sources(user, filters, asof, sources=sources):
        count = queryset.count()
        total += count
        deletable += count
        unread += queryset.filter(inbox_read=False).count()
        if anchor:
            rank = 1
            if rank < anchor[0]:
                continue
            if rank == anchor[0]:
                created = datetime.fromisoformat(anchor[1])
                older = Q(created_at__lt=created) | Q(created_at=created, pk__lt=anchor[2])
                if source > anchor[3]:
                    older |= Q(created_at=created, pk=anchor[2])
                queryset = queryset.filter(older)
        relations = [
            'task__space__workplace', 'task__work_item',
        ] + (['actor'] if source == 'spaces' else [])
        rows = queryset.select_related(*relations).order_by('-created_at', '-pk')[:DASHBOARD_NOTIFICATION_LIMIT + 1]
        candidates.extend((source, row) for row in rows)
    candidates.sort(key=lambda pair: _sort_key(*pair))
    visible = candidates[:DASHBOARD_NOTIFICATION_LIMIT]
    snapshot = signing.dumps(data, salt=SIGNING_SALT, compress=True)
    next_cursor = ''
    if len(candidates) > DASHBOARD_NOTIFICATION_LIMIT:
        source, row = visible[-1]
        data['anchor'] = [1, row.created_at.isoformat(), row.pk, source]
        next_cursor = signing.dumps(data, salt=SIGNING_SALT, compress=True)
    items = [_serialize(source, row) for source, row in visible]
    return {'dashboard_notifications': items, 'dashboard_notification_count': total,
            'filtered_unread_count': unread, 'deletable_count': deletable, 'notification_filters': filters,
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
    values = {'is_read': action == 'read'} if action in {'read', 'unread'} else {'is_archived': action == 'archive'}
    if action == 'archive':
        values['is_read'] = True
    elif action == 'delete':
        values = {'is_read': True, 'is_deleted': True}
    NotificationState.objects.update_or_create(user=user, **{SOURCES[source]: row}, defaults=values)
