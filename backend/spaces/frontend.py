import json

from django.templatetags.static import static
from django.utils.html import strip_tags
from django.utils import timezone

from core.frontend import form_payload, pagination_payload
from .avatars import space_avatar
from .defaults import ISSUE_TYPE_ICONS, classification_label, status_appearance


def space_payload(space):
    base = getattr(space, 'url', '')
    return {'id': space.pk, 'slug': space.slug, 'name': space.name, 'key': space.key,
            'description': strip_tags(space.description), 'kind': space.kind, 'kind_label': space.get_kind_display(),
            'template': space.template, 'template_label': space.get_template_display(),
            'management': space.management, 'management_label': space.get_management_display(),
            'visibility': space.visibility, 'avatar': space_avatar(space),
            'url': base, 'settings_url': getattr(space, 'settings_url', base + '?view=settings'),
            'edit_url': getattr(space, 'edit_url', base + 'edit/'),
            'favorite_url': getattr(space, 'favorite_url', base + 'favorite/'),
            'configuration_url': getattr(space, 'configuration_url', ''),
            'favorite': getattr(space, 'favorite', False), 'can_manage': getattr(space, 'can_manage', False),
            'item_count': getattr(space, 'item_count', 0)}


def modal_payload(modal):
    return {'title': modal['title'], 'action': modal['action'], 'return_url': modal['return_url'], 'form': form_payload(modal['form']),
            **({'space_settings': modal['space_settings']} if modal.get('space_settings') else {})}


def form_page(request, context):
    return {'type': 'form', 'title': context['modal']['title'], 'data': modal_payload(context['modal'])}


def directory_page(request, context):
    base = context['spaces_url']
    return {'type': 'space-directory', 'title': 'Przestrzenie', 'data': {
        'results': [space_payload(space) for space in context['page']],
        'base_url': base, 'spaces_url': context['spaces_url'], 'create_url': context['create_url'],
        'query': context['query'], 'tab': context['tab'], 'kind': context.get('kind') or '',
        'pagination': pagination_payload(request, context['page'], base),
        'illustration': static('img/empty-states/spaces-empty.webp'),
        'modal': modal_payload(context['modal']) if context.get('modal') else None,
    }}


def item_payload(item):
    from accounts.avatar import account_avatar
    task = item.task
    return {
        'id': item.pk, 'task_id': task.pk, 'key': item.key, 'title': task.title,
        'url': item.url, 'edit_url': item.edit_url, 'action_url': item.action_url,
        'block_url': getattr(item, 'block_url', ''),
        'update_dates_url': item.update_dates_url,
        'editable': item.editable, 'rank': item.rank, 'sprint_id': item.sprint_id,
        'status': item.status, 'status_label': item.status_label, 'status_color': item.status_color,
        'category': task.status, 'status_order': item.status_order, 'transitions': item.transitions,
        'priority': task.priority, 'priority_label': task.get_priority_display(),
        'task_type': task.task_type, 'task_type_label': classification_label(item.space.configuration.settings, 'categories', task.task_type),
        'task_group': task.task_group, 'task_group_label': classification_label(item.space.configuration.settings, 'groups', task.task_group),
        'work_type': item.work_type, 'type_label': item.type_label, 'type_icon': item.type_icon, 'type_color': item.type_color,
        'points': item.points, 'in_backlog': item.in_backlog,
        'assignee': {'label': task.assignee.get_full_name() or task.assignee.email, 'avatar': account_avatar(task.assignee)} if task.assignee else None,
        'team': item.team.name if item.team_id else '', 'tags_count': item.tags_count,
        'attachments_count': item.attachments_count, 'due_at': task.due_at, 'due_urgency': task.due_urgency,
        'start_at': item.start_at,
        'blocked': {
            'reason': task.blocked_reason, 'at': task.blocked_at,
            'by': (task.blocked_by.get_full_name() or task.blocked_by.email) if task.blocked_by else None,
            'responsible': {'id': task.blocked_responsible_id,
                'label': task.blocked_responsible.get_full_name() or task.blocked_responsible.email} if task.blocked_responsible else None,
        } if task.blocked_at else None,
        'blocked_revision': task.blocked_revision,
        'flow': {'started_at': item.flow_started_at, 'stage_entered_at': item.status_entered_at,
                 'finished_at': item.flow_finished_at},
        'start_on': timezone.localtime(item.start_at).date() if item.start_at else None,
        'end_on': timezone.localtime(task.due_at).date() if task.due_at else None,
        'timeline': {key: getattr(item, 'timeline_' + key, None) for key in ('start', 'end', 'left', 'width')},
    }


def sprint_payload(sprint):
    return {
        'id': sprint.pk, 'name': sprint.name, 'goal': sprint.goal, 'state': sprint.state,
        'state_label': sprint.get_state_display(), 'start_on': sprint.start_on, 'end_on': sprint.end_on,
        **{key: getattr(sprint, key, '') for key in ('action_url', 'edit_url', 'start_url', 'complete_url', 'create_item_url')},
        'planning': getattr(sprint, 'planning', {}),
        'visible_count': getattr(sprint, 'visible_count', 0), 'finished_count': getattr(sprint, 'finished_count', 0),
        **({'loaded_count': sprint.loaded_count, 'more_url': sprint.more_url} if hasattr(sprint, 'loaded_count') else {}),
    }


def detail_page(request, context):
    from accounts.avatar import account_avatar
    from .item_query import item_sort
    from .space_team import payload as space_team_payload
    space = context['space']
    space.url = context['space_url']
    data = {
        'space': space_payload(space), 'view': context['view'], 'navigation': context['navigation'],
        **{key: context.get(key, '') for key in ('can_manage', 'can_configure', 'can_edit', 'create_item_url',
            'sprint_create_url', 'edit_url', 'configuration_url', 'member_url', 'bulk_plan_url', 'backlog_create_url')},
        'configuration': {'name': space.configuration.name, 'shared': space.configuration.shared},
        'summary': {**context['summary'], 'statuses': [status_appearance(s) for s in context['summary']['statuses']]} if context.get('summary') else None,
        'reports': {**context['reports'], 'statuses': [status_appearance(s) for s in context['reports']['statuses']]} if context.get('reports') else None,
        'items': [item_payload(item) for item in context.get('items', [])],
        'stats': context.get('stats'), 'status_counts': [status_appearance(s) for s in context.get('status_counts', [])],
        'columns': [status_appearance({key: value for key, value in column.items() if key != 'items'}) for column in context.get('columns', [])],
        'sprints': [sprint_payload(sprint) for sprint in context.get('sprints', [])],
        'active_sprint': sprint_payload(context['active_sprint']) if context.get('active_sprint') else None,
        'backlog_totals': context.get('backlog_totals'), 'timeline': context.get('timeline'),
        'backlog_loaded_count': context.get('backlog_loaded_count', 0), 'backlog_more_url': context.get('backlog_more_url', ''),
        'pagination': pagination_payload(request, context.get('page')),
        'filters': {key: request.GET.get(key, '') for key in ('q', 'work_type', 'assignee', 'team', 'status', 'priority', 'summary', 'blocked')},
        'summary_filter_label': context.get('summary_filter_label', ''),
        'sort': item_sort(request, context['view']),
        'type_icons': {row['key']: row['icon'] for row in context.get('type_options', [])},
        'type_colors': {row['key']: row['color'] for row in context.get('type_options', [])},
        'filter_options': {
            'work_type': [['', 'Wszystkie typy']] + [[row['key'], row['label']] for row in context.get('type_options', [])],
            'assignee': [['', 'Wszyscy wykonawcy'], ['me', 'Przypisane do mnie'], ['unassigned', 'Nieprzypisane']] + [[str(person.pk), person.get_full_name() or person.email] for person in context.get('assignee_options', [])],
            'status': [['', 'Wszystkie statusy']] + [[row['key'], row['label']] for row in space.statuses],
            'priority': [['', 'Wszystkie priorytety']] + [list(row) for row in context.get('priority_options', [])],
            'team': [['', 'Wszystkie zespoły']] + [[str(team.pk), team.name] for team in context.get('space_teams', [])],
            'blocked': [['', 'Wszystkie zadania'], ['yes', 'Zablokowane'], ['no', 'Bez blokady']],
        },
        'members': [{'id': member.pk, 'name': member.user.get_full_name() or member.user.email,
                     'avatar': account_avatar(member.user), 'role': member.get_role_display(),
                     'can_remove': context['can_manage'] and member.user_id != space.private_owner_id and (member.role != 'admin' or space.private_owner_id == request.user.pk),
                     'remove_url': context['member_url'] + f'{member.pk}/remove/'} for member in context.get('members', [])],
        'private_owner': (space.private_owner.get_full_name() or space.private_owner.email) if space.private_owner else '',
        'team': space_team_payload(request, space), 'team_url': context['space_url'] + 'team/',
        'modal': modal_payload(context['modal']) if context.get('modal') else None,
    }
    return {'type': 'space-detail', 'title': f'Ustawienia przestrzeni · {space.name}' if context['view'] == 'settings' else space.name, 'data': data}


def configuration_page(request, context):
    config = context['config']
    section = context['configuration_section']
    title = next(group['title'] for group in context['sets'] if group['key'] == section)
    return {'type': 'space-configuration', 'title': title, 'data': {
        'name': config.name, 'shared': config.shared, 'spaces_count': config.spaces.count(),
        'space_url': context['space_url'], 'revision': context['revision'], 'errors': context['errors'],
        'section': section, 'workflow_view': context['workflow_view'], 'editor': context.get('editor'),
        'type_icon_defaults': ISSUE_TYPE_ICONS,
        'sets': [{'key': group['key'], 'title': group['title'], 'management': form_payload(group['formset'].management_form),
                  'errors': list(group['formset'].non_form_errors()),
                  'forms': [form_payload(form) for form in group['formset']]} for group in context['sets']],
    }}


def task_members_payload(context):
    from accounts.avatar import account_avatar
    return {'can_manage': context['can_manage_team'], 'is_owner': context['is_team_owner'],
            'share_form': form_payload(context['share_form']),
            'members': [{'id': member.pk, 'user_id': member.user_id,
                'name': member.user.get_full_name() or member.user.email or member.user.username,
                'email': member.user.email, 'avatar': account_avatar(member.user),
                'role': getattr(member, 'role', ''), 'role_label': member.get_role_display() if callable(member.get_role_display) else member.get_role_display,
                'created_at': member.created_at, 'can_change': member.can_change} for member in context['members']]}


def file_payload(file):
    return {'id': file.pk, 'name': file.filename, 'size': file.get_formatted_size(),
            'type_class': file.get_type_class(), 'image': file.is_image(), 'url': file.get_url()}


def activity_payload(activity):
    from accounts.avatar import account_avatar
    metadata = activity.metadata or {}
    return {'id': activity.pk, 'kind': activity.kind, 'action': activity.action,
            'message': activity.message, 'created_at': activity.created_at,
            'actor': (activity.actor.get_full_name() or activity.actor.username) if activity.actor else 'System',
            'avatar': account_avatar(activity.actor),
            'metadata': {key: metadata[key] for key in ('changes', 'from_label', 'to_label', 'old_status_label', 'new_status_label', 'fields', 'title', 'count', 'subtask_title') if key in metadata},
            'files': [file_payload(file) for file in activity.images.all()] if activity.kind == 'comment' else []}


def task_page(request, context):
    from accounts.avatar import account_avatar
    from .views import decorate_items
    from .workflow import block_responsible_people
    task, item = context['task'], context['item']
    decorate_items(request, [item])
    return {'type': 'space-task', 'title': f'{item.key} · {task.title}', 'data': {
        'item': item_payload(item), 'space': {'id': item.space_id, 'name': item.space.name, 'template': item.space.template, 'url': context['space_url']},
        'form': form_payload(context['form']), 'error': context['error'], 'can_edit': context['can_edit_task'],
        'can_manage': context['can_manage_task'], 'favorite': context['is_favorite'],
        'block_responsible_options': [{'id': person.pk, 'label': person.get_full_name() or person.email}
            for person in block_responsible_people(task)] if context['can_edit_task'] else [],
        'back_url': context['back_url'], 'tabs': context['task_tabs'], 'tab': context['task_tab'],
        'edit_url': context['task_edit_url'], 'member_url': context['member_edit_url'], 'team_url': context['team_url'],
        'status': context['detail_status'], 'statuses': [status_appearance(s) for s in context['space'].statuses],
        'created_at': task.created_at, 'completion_date': task.completion_date,
        'created_by': {'name': task.created_by.get_full_name() or task.created_by.email, 'avatar': account_avatar(task.created_by)} if task.created_by else None,
        'visibility': task.visibility, 'comments': [activity_payload(activity) for activity in context['comments']],
        'history': [activity_payload(activity) for activity in context['history']],
        'files': [file_payload(file) for file in context['files']],
        'children': [item_payload(child) for group in context['subtask_status_groups'] for child in group['tasks']],
        'log_form': form_payload(context['log_form']), 'subtask_form': form_payload(context['subtask_form']),
        'work_log': {'total_minutes': context['work_log_total_minutes'], 'total_label': context['work_log_total_label'],
            'count': context['work_log_page'].paginator.count, 'page': context['work_log_page'].number,
            'pages': context['work_log_page'].paginator.num_pages, 'previous': context['work_log_previous_url'], 'next': context['work_log_next_url'],
            'results': [{'id': entry.pk, 'author': (entry.author.get_full_name() or entry.author.username) if entry.author else 'Usunięte konto',
                'avatar': account_avatar(entry.author), 'duration_minutes': entry.duration_minutes,
                'started_at': entry.started_at, 'ended_at': entry.ended_at, 'description': entry.description,
                'form_values': json.loads(entry.form_values)} for entry in context['work_log_page']]},
        'team': task_members_payload(context), 'mentions': context['mention_people'],
        'attachment_accept': context['comment_attachment_accept'], 'attachment_limit': context['comment_image_limit'],
        'attachment_max_size': context['comment_image_max_size'], 'comment_draft': context['comment_draft'],
    }}


def teams_page(request, context):
    return {'type': 'teams', 'title': 'Zespoły', 'data': {
        'url': context['teams_url'], 'query': context['query'], 'tab': context['tab'], 'create_url': context['create_url'],
        'pagination': pagination_payload(request, context['page']),
        'teams': [{'id': team.pk, 'name': team.name, 'description': team.description, 'photo_url': team.photo_url,
                   'url': team.url, 'member_count': team.member_count} for team in context['page']],
    }}


def team_page(request, context):
    from accounts.avatar import account_avatar
    team = context['team']
    return {'type': 'team', 'title': team.name, 'data': {
        'id': team.pk, 'name': team.name, 'description': team.description, 'url': context['team_url'],
        'photo_url': context['photo_url'], 'edit_url': context['edit_url'], 'member_url': context['member_url'],
        'can_manage': context['can_manage'], 'spaces': [space_payload(space) for space in context['spaces']],
        'members': [{'id': member.pk, 'name': member.user.get_full_name() or member.user.email,
                     'avatar': account_avatar(member.user), 'role': member.get_role_display(),
                     'remove_url': context['member_url'] + f'{member.pk}/remove/'} for member in context['members']],
        'items': [item_payload(item) for item in context['items']],
        'pagination': pagination_payload(request, context['page']),
    }}
