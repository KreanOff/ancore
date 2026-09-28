"""Workspace-scoped mentions and subscriptions for both task modules."""
import json
import re

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from kanban.models import Kanban, KanbanActivity, KanbanProject
from tasks.access import visible_to
from tasks.models import Task, TaskActivity, TaskProject
from workplaces.services import workplace_people, scoped_workplace_app_path, workspace_owner
from .models import ActivityInterest, ObjectFollow


OBJECTS = {
    ('tasks', 'task'): (Task, 'task'),
    ('tasks', 'project'): (TaskProject, 'task_project'),
    ('kanban', 'task'): (Kanban, 'kanban'),
    ('kanban', 'project'): (KanbanProject, 'kanban_project'),
}


def mention_handle(username):
    """Public Ancore IDs already include @; older usernames may omit it."""
    return username if username.startswith('@') else f'@{username}'


def mention_label(person):
    name = ' '.join(person.get_full_name().split())
    return f'@{name}' if name else mention_handle(person.username)


def mention_choices(task):
    return [
        {'id': person.pk, 'username': person.username, 'email': person.email,
         'mention': mention_label(person), 'label': person.get_full_name() or person.username}
        for person in mention_people(task)
    ]


def _validated_mentions(message, entries, people):
    """Resolve selected names by ID, never by a potentially duplicated display name."""
    if not isinstance(entries, list):
        return []
    people_by_id = {person.pk: person for person in people}
    valid = []
    for entry in entries[:100]:
        if not isinstance(entry, dict):
            continue
        user_id, start, end = (entry.get(key) for key in ('user_id', 'start', 'end'))
        if any(type(value) is not int for value in (user_id, start, end)):
            continue
        person = people_by_id.get(user_id)
        if not person or not 0 <= start < end <= len(message):
            continue
        label = mention_label(person)
        if message[start:end] != label:
            continue
        if start and re.match(r'[\w@.+-]', message[start - 1]):
            continue
        if re.match(r'[\w@+-]|\.\w', message[end:]):
            continue
        if any(start < other['end'] and end > other['start'] for other in valid):
            continue
        valid.append({'user_id': user_id, 'start': start, 'end': end, 'text': label})
    return valid


def comment_mention_metadata(task, raw_comment, raw_mentions):
    # Browsers submit textarea newlines as CRLF; offsets use Unicode code points.
    comment = raw_comment.replace('\r\n', '\n')
    leading = len(comment) - len(comment.lstrip())
    try:
        entries = json.loads(raw_mentions) if raw_mentions and len(raw_mentions) <= 65536 else []
    except (ValueError, TypeError):
        entries = []
    if isinstance(entries, list):
        entries = [dict(entry, start=entry['start'] - leading, end=entry['end'] - leading)
                   for entry in entries[:100] if isinstance(entry, dict)
                   and type(entry.get('start')) is int and type(entry.get('end')) is int]
    return {'mentions': _validated_mentions(comment.strip(), entries, mention_people(task))}


def mention_people(task):
    people = workplace_people(task.workplace, task.user)
    if task.workplace_id:
        people = people.filter(Q(pk=task.workplace.owner_id) | Q(
            workplace_memberships__workplace=task.workplace,
            workplace_memberships__is_active=True,
            workplace_memberships__role__in=['admin', 'member'],
        )).distinct()
    if isinstance(task, Task):
        current, seen = task, set()
        while current is not None and current.pk not in seen:
            seen.add(current.pk)
            resources = [current]
            if current.section_id:
                resources.extend([current.section, current.section.project])
            for resource in resources:
                if resource.visibility == 'private':
                    people = (people.filter(Q(pk=resource.private_owner_id) | Q(pk__in=resource.shared_with.values('pk')))
                              if resource.private_owner_id else people.none())
            current = current.parent if current.parent_id else None
    return people


def follow_context(user, obj, app, kind):
    if obj is None:
        return {}
    field = OBJECTS[app, kind][1]
    suffix = f'follow/{kind}/{obj.pk}/'
    url = (scoped_workplace_app_path(obj.workplace, app, suffix)
           if obj.workplace_id else reverse(f'{app}:tasks') + suffix)
    return {'follow_url': url, 'is_following': ObjectFollow.objects.filter(user=user, **{field: obj}).exists()}


@login_required
@require_POST
def follow_object(request, app, kind, object_id):
    if (app, kind) not in OBJECTS:
        raise Http404
    model, field = OBJECTS[app, kind]
    obj = get_object_or_404(visible_to(model.objects.all(), request.user), pk=object_id, user=workspace_owner(request), workplace=request.workplace)
    following = request.POST.get('following')
    if following not in {'true', 'false'}:
        return JsonResponse({'message': 'Nieprawidłowy stan obserwowania.'}, status=400)
    if following == 'true':
        ObjectFollow.objects.get_or_create(user=request.user, **{field: obj})
    else:
        ObjectFollow.objects.filter(user=request.user, **{field: obj}).delete()
    return JsonResponse({'following': following == 'true'})


@receiver(post_save, sender=TaskActivity)
@receiver(post_save, sender=KanbanActivity)
def deliver_activity_interest(sender, instance, created, raw=False, **kwargs):
    if not created or raw:
        return
    task = instance.task
    if task.workplace_id and task.user_id != task.workplace.owner_id:
        return
    app = 'tasks' if sender is TaskActivity else 'kanban'
    field = OBJECTS[app, 'task'][1]
    project_field = OBJECTS[app, 'project'][1]
    scope = Q(**{field: task})
    if task.section_id and task.section.project_id:
        scope |= Q(**{project_field + '_id': task.section.project_id})
    people = mention_people(task).exclude(pk=instance.actor_id)
    followers = set(ObjectFollow.objects.filter(scope, user__in=people).values_list('user_id', flat=True))
    mentions = set()
    if instance.kind == 'comment' and '@' in instance.message:
        selected = _validated_mentions(instance.message, (instance.metadata or {}).get('mentions', []), mention_people(task))
        mentions.update(entry['user_id'] for entry in selected if entry['user_id'] != instance.actor_id)
        # Selected names must not accidentally match another person's legacy login.
        legacy_text = list(instance.message)
        for entry in selected:
            legacy_text[entry['start']:entry['end']] = ' ' * (entry['end'] - entry['start'])
        legacy_text = ''.join(legacy_text)
        for user_id, username in people.values_list('pk', 'username'):
            # Exact handles, including Unicode/dots/email-style usernames; never an email substring.
            if re.search(r'(?<![\w@.+-])' + re.escape(mention_handle(username)) + r'(?![\w@+-]|\.\w)', legacy_text):
                mentions.add(user_id)
    activity_field = 'task_activity' if app == 'tasks' else 'kanban_activity'
    with transaction.atomic():
        ActivityInterest.objects.bulk_create([
            ActivityInterest(user_id=pk, **{activity_field: instance}, mentioned=pk in mentions, followed=pk in followers)
            for pk in mentions | followers
        ])
