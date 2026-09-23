"""Workspace-scoped snapshots and atomic creation of project structures."""
from django.core.exceptions import ValidationError
from django.db import transaction

from core.task_numbering import lock_task_numbers
from .models import Task, TaskProjectTemplate, TaskSection

SECTION_FIELDS = ('title', 'description', 'priority', 'kind', 'wip_limit', 'order')
TASK_FIELDS = ('title', 'description', 'priority', 'task_type', 'estimated_minutes')


def template_descendants(structure, item_ids):
    """Include descendants at any depth, also terminating for malformed cycles."""
    result = set(item_ids)
    children = {}
    for item in structure.get('tasks', []):
        children.setdefault(item['parent'], []).append(item['id'])
    pending = list(result)
    while pending:
        for child in children.get(pending.pop(), []):
            if child not in result:
                result.add(child)
                pending.append(child)
    return result


def update_template_item(structure, kind, data):
    """Apply validated form data to a locked template snapshot."""
    structure.setdefault('version', 1)
    structure.setdefault('sections', [])
    structure.setdefault('tasks', [])
    key = 'sections' if kind == 'section' else 'tasks'
    items = structure.setdefault(key, [])
    item_id = data.get('item_id')
    fields = SECTION_FIELDS if kind == 'section' else (*TASK_FIELDS, 'section', 'parent')
    if item_id is None:
        counter = f'next_{kind}_id'
        item_id = max(structure.get(counter, 1), max((item['id'] for item in items), default=0) + 1)
        structure[counter] = item_id + 1
        item = {'id': item_id}
        items.append(item)
    else:
        item = next(item for item in items if item['id'] == item_id)
    item.update({field: data[field] for field in fields})
    if kind == 'task':
        descendants = template_descendants(structure, {item_id})
        for child in items:
            if child['id'] in descendants:
                child['section'] = item['section']
    else:
        items.sort(key=lambda entry: (entry['order'], entry['id']))


def delete_template_item(structure, kind, item_id):
    # Keep IDs stable for forms opened before a deletion, including source IDs.
    for entity, key in [('section', 'sections'), ('task', 'tasks')]:
        counter = f'next_{entity}_id'
        structure[counter] = max(structure.get(counter, 1), max((item['id'] for item in structure.get(key, [])), default=0) + 1)
    if kind == 'section':
        structure['sections'] = [item for item in structure['sections'] if item['id'] != item_id]
        task_ids = {item['id'] for item in structure.get('tasks', []) if item['section'] == item_id}
    else:
        task_ids = {item_id}
    removed = template_descendants(structure, task_ids)
    structure['tasks'] = [item for item in structure.get('tasks', []) if item['id'] not in removed]


@transaction.atomic
def save_project_template(project):
    sections = list(project.sections.order_by('order', 'pk'))
    tasks = list(Task.objects.filter(
        section__in=sections, user=project.user, workplace=project.workplace,
    ).order_by('pk'))
    task_ids = {task.pk for task in tasks}
    if any(task.parent_id and task.parent_id not in task_ids for task in tasks):
        raise ValidationError('Projekt zawiera podzadanie spoza swojej struktury.')
    structure = {
        'version': 1,
        'sections': [dict(id=section.pk, **{key: getattr(section, key) for key in SECTION_FIELDS}) for section in sections],
        'tasks': [dict(id=task.pk, section=task.section_id, parent=task.parent_id,
                       **{key: getattr(task, key) for key in TASK_FIELDS}) for task in tasks],
    }
    return TaskProjectTemplate.objects.create(
        user=project.user, workplace=project.workplace, name=project.name, template_name=project.name,
        description=project.description, structure=structure,
    )


def populate_project_from_template(project, template, actor):
    if (project.user_id, project.workplace_id) != (template.user_id, template.workplace_id):
        raise ValidationError('Szablon nie należy do tego Workspace.')
    # Match the owner -> section lock order used by Task.save() and bulk actions.
    with lock_task_numbers(project.user_id):
        sections = {}
        for item in template.structure['sections']:
            sections[item['id']] = TaskSection.objects.create(
                project=project, **{key: item[key] for key in SECTION_FIELDS},
            )
        pending = list(template.structure['tasks'])
        tasks = {}
        while pending:
            remaining = []
            for item in pending:
                if item['parent'] and item['parent'] not in tasks:
                    remaining.append(item)
                    continue
                task = Task(
                    user=project.user, workplace=project.workplace,
                    section=sections[item['section']], parent=tasks.get(item['parent']),
                    **{key: item[key] for key in TASK_FIELDS},
                )
                task._activity_actor = actor
                task.save()
                tasks[item['id']] = task
            if len(remaining) == len(pending):
                raise ValidationError('Szablon zawiera nieprawidłowe powiązania podzadań.')
            pending = remaining
