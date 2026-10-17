"""Workspace-scoped mentions in current Space task comments."""
import json
import re

from django.db.models import Q


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
    from spaces.access import task_people
    people = task_people(task)
    if task.visibility == 'private':
        people = people.filter(Q(pk=task.private_owner_id) | Q(pk__in=task.memberships.values('user_id')))
    return people.filter(Q(pk=task.space.workplace.owner_id) | Q(
        workplace_memberships__workplace=task.space.workplace,
        workplace_memberships__is_active=True,
        workplace_memberships__role__in=['admin', 'member'],
    )).distinct()
