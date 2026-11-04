from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import strip_tags

from accounts.avatar import account_avatar
from spaces.templatetags.space_ui import space_avatar
from workplaces.services import scoped_workplace_app_path


def _space(space, request):
    return {'id': space.pk, 'name': space.name, 'key': space.key, 'kind': space.get_kind_display(),
            'avatar': space_avatar(space), 'url': scoped_workplace_app_path(request.workplace, 'space', f'{space.slug}/'),
            'count': getattr(space, 'item_count', 0), 'description': strip_tags(space.description)}


def _row(row, request):
    task = row['object'] if row['is_task'] else None
    result = {key: row.get(key) for key in ('title', 'url', 'location', 'icon', 'is_task', 'key', 'status_label', 'overdue')}
    for field in ('due_at', 'recent_at'):
        value = row.get(field)
        result[field] = value.isoformat() if value else None
    result['space'] = _space(row['space'], request) if row.get('space') else None
    if task:
        result['task'] = {'status': task.status, 'priority': task.priority, 'type_label': row['task_row']['type_label'],
                          'type_icon': row['task_row']['type_icon'], 'type_color': row['task_row']['type_color'], 'tags_count': row['task_row']['tags_count'],
                          'attachments_count': row['task_row']['attachments_count'], 'due_urgency': task.due_urgency}
    return result


def for_you_page(request, context):
    groups = []
    for block in context['for_you_groups']:
        groups.append({'date_group': block['date_group'],
            'task_groups': [{**{key: group[key] for key in ('category', 'label', 'order')},
                             'items': [_row(row, request) for row in group['items']]} for group in block['task_groups']],
            'spaces': [_space(space, request) for space in block['spaces']],
            'other_rows': [_row(row, request) for row in block['other_rows']]})
    return {'type': 'for-you', 'title': 'Dla ciebie', 'data': {
        'tab': context['for_you_tab'], 'tabs': context['for_you_tabs'], 'groups': groups,
        'projects': [_row(row, request) for row in context['for_you_projects']],
        'projects_url': context['for_you_projects_url'], 'assigned_count': context['for_you_assigned_count'],
        'empty': context['for_you_empty'], 'illustration': static(context['for_you_empty_illustration']),
        'spaces_illustration': static('img/empty-states/spaces-empty.webp'),
        'filtered': context['for_you_filtered'], 'clear_url': context['for_you_clear_url'],
        'previous': context['for_you_previous'], 'next': context['for_you_next'],
    }}


def settings_page(request, context):
    rows = [
        {'category': 'account', 'url': reverse('profile'), 'icon': 'circle-user-round', 'title': 'Profil użytkownika', 'description': 'Dane osobowe, zdjęcie i status dostępności.'},
        {'category': 'workspace', 'url': reverse('workplaces:workplaces'), 'icon': 'folder', 'title': 'Zarządzaj Workspace', 'description': 'Wszystkie Workspace, ich ustawienia, członkowie i linki do dołączenia.'},
    ]
    if request.user.is_staff:
        rows.append({'category': 'workspace', 'url': reverse('admin:index'), 'icon': 'shield-check', 'title': 'Panel administracyjny', 'description': 'Zarządzaj systemem i dostępem użytkowników.'})
    return {'type': 'settings', 'title': 'Ustawienia', 'data': {
        'user': {'name': request.user.get_full_name() or request.user.username, 'email': request.user.email, 'avatar': account_avatar(request.user)},
        'profile_url': reverse('profile'), 'logout_url': reverse('logout'), 'rows': rows,
        'spaces': context.get('settings_spaces', []),
    }}
