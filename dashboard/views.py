from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.avatar import account_avatar
from accounts.views import _switch_account_context
from kanban.models import KanbanActivity
from tasks.models import TaskActivity


DASHBOARD_NOTIFICATION_LIMIT = 12


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
        'url': reverse(f'{app_name}:{route_name}', args=[task.task_id]),
    }


def _dashboard_notifications(user):
    task_activities = TaskActivity.objects.filter(
        task__user=user,
    ).select_related(
        'task',
        'task__section',
        'task__section__project',
        'actor',
    ).order_by('-created_at', '-id')[:DASHBOARD_NOTIFICATION_LIMIT]
    kanban_activities = KanbanActivity.objects.filter(
        task__user=user,
    ).select_related(
        'task',
        'task__section',
        'task__section__project',
        'task__column',
        'actor',
    ).order_by('-created_at', '-id')[:DASHBOARD_NOTIFICATION_LIMIT]

    notifications = [
        _activity_notification(activity, 'tasks', 'Tasks', 'Zadanie', 'Podzadanie')
        for activity in task_activities
    ] + [
        _activity_notification(activity, 'kanban', 'Kanban', 'Karta', 'Podkarta')
        for activity in kanban_activities
    ]

    return sorted(
        notifications,
        key=lambda notification: notification['sort_key'],
        reverse=True,
    )[:DASHBOARD_NOTIFICATION_LIMIT]


@login_required
def settings(request):
    return render(request, 'dashboard/settings.html', {
        'current_account_avatar': account_avatar(request.user),
        'switch_accounts': _switch_account_context(request),
    })


@login_required
def home(request):
    return redirect('workplaces:workplaces')
