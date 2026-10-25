"""Explicit inbox contract; filtering, snapshots and actions stay in the service."""
from django.utils import timezone
from django.utils.text import Truncator

from workplaces.services import workplaces_for_user
from workplaces.templatetags.workplace_avatar import workplace_avatar


def notification_payload(user, context):
    items = []
    for item in context['dashboard_notifications']:
        items.append({
            **{key: item.get(key, '') for key in (
                'key', 'title', 'url', 'actor_label', 'actor_avatar', 'action_message',
                'workplace_label', 'source_label', 'object_id', 'location_label',
                'group_label', 'event_label', 'full_date', 'action_label',
            )},
            'is_read': bool(item.get('is_read')), 'is_archived': bool(item.get('is_archived')),
            'created_at': item['created_at'].isoformat(),
            'time': timezone.localtime(item['created_at']).strftime('%H:%M'),
            'details': [{
                'label': detail.get('label', ''), 'from_label': detail.get('from_label', ''),
                'text': str(Truncator(detail.get('to_label') or detail.get('value') or '').chars(240)),
            } for detail in item.get('detail_lines', [])[:3]],
        })
    return {
        'items': items, 'count': len(items), 'total': context['dashboard_notification_count'],
        'filtered_unread_count': context['filtered_unread_count'],
        'deletable_count': context['deletable_count'],
        'snapshot': context['snapshot'], 'next_cursor': context['next_cursor'],
        'filters': context['notification_filters'],
        'workplaces': [{'id': str(workplace.pk), 'name': workplace.name, 'avatar': workplace_avatar(workplace)}
                       for workplace in workplaces_for_user(user)],
    }
