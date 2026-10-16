"""Add planning metadata and import Kanban without deleting source records/files.

Historical models only. Old primary keys are mapped for bookmarks and downloads.
Run atomically: a failed import leaves all previous records and permissions intact.
"""
from django.db import migrations
from django.db.models import Max


def initial_settings():
    keys = ['new', 'in_progress', 'resolved', 'closed', 'reopened']
    labels = ['Do zrobienia', 'W toku', 'Do sprawdzenia', 'Gotowe', 'Ponownie otwarte']
    return {'statuses': [dict(key=k, label=l, category=k, transitions=[v for v in keys if v != k]) for k, l in zip(keys, labels)], 'types': [{'key': 'task', 'label': 'Zadanie'}], 'fields': []}


def forwards(apps, schema_editor):
    db = schema_editor.connection.alias
    def model(app, name):
        return apps.get_model(app, name)
    Project, Section, Task = [model('tasks', name) for name in ('TaskProject', 'TaskSection', 'Task')]
    Space, Config, Item, Link = [model('spaces', name) for name in ('Space', 'SpaceConfiguration', 'WorkItem', 'LegacyKanbanLink')]
    KProject, KSection, Card = [model('kanban', name) for name in ('KanbanProject', 'KanbanSection', 'Kanban')]
    spaces, sections, tasks, activities = {}, {}, {}, {}
    counters = {}

    def scope_number(task):
        scope = (task.user_id, task.workplace_id)
        if scope not in counters:
            counters[scope] = Task.objects.using(db).filter(user_id=scope[0], workplace_id=scope[1]).aggregate(n=Max('task_id'))['n'] or 0
        counters[scope] += 1
        return counters[scope]

    def space_for(project, template='tasks'):
        if project.pk in spaces:
            return spaces[project.pk]
        if not project.workplace_id:
            return None
        config = Config.objects.using(db).create(workplace_id=project.workplace_id, name=project.name, settings=initial_settings())
        space = Space.objects.using(db).create(project_id=project.pk, workplace_id=project.workplace_id, key=f'P{project.pk}', kind='software' if template == 'kanban' else 'business', template=template, configuration=config)
        spaces[project.pk] = space
        return space

    def item_for(task, space, status=None):
        number = space.next_number if space else 0
        if space:
            space.next_number += 1
        return Item.objects.using(db).create(task_id=task.pk, space_id=space.pk if space else None, key=f'{space.key}-{number}' if space else f'TASK-{task.pk}', number=number, rank=number * 100 if space else task.pk, status=status or task.status)

    def link(kind, source, target, space):
        Link.objects.using(db).create(kind=kind, source_id=source, target_id=target, space_id=space.pk if space else None)

    def copy_fields(source, target, exclude=()):
        available = {f.attname for f in target._meta.concrete_fields}
        return {f.attname: getattr(source, f.attname) for f in source._meta.concrete_fields if f.attname in available and f.attname not in {'id', *exclude}}

    for project in Project.objects.using(db).all().iterator():
        space_for(project)
    for task in Task.objects.using(db).select_related('section').all().iterator():
        space = spaces.get(task.section.project_id) if task.section_id else None
        if space and (space.project.user_id, space.workplace_id) != (task.user_id, task.workplace_id):
            space = None
        item_for(task, space)

    imported_spaces = {}
    for source in KProject.objects.using(db).all().iterator():
        if not source.workplace_id:
            # No Workspace means no shared-space context yet; leave old access intact.
            continue
        values = copy_fields(source, Project)
        if values.get('code') and Project.objects.using(db).filter(code=values['code']).exists():
            values['code'] = ''
        project = Project.objects.using(db).create(**values)
        Project.objects.using(db).filter(pk=project.pk).update(created_at=source.created_at)
        project.favorited_by.set(source.favorited_by.all())
        space = space_for(project, 'kanban')
        imported_spaces[source.pk] = space
        link('project', source.pk, project.pk, space)
        for member in model('kanban', 'KanbanProjectMembership').objects.using(db).filter(project=source):
            model('tasks', 'TaskProjectMembership').objects.using(db).create(project=project, user_id=member.user_id, role=member.role)
        for note in model('kanban', 'KanbanProjectNote').objects.using(db).filter(project=source):
            values = copy_fields(note, model('tasks', 'TaskProjectNote'), ('project_id',))
            copied = model('tasks', 'TaskProjectNote').objects.using(db).create(project=project, **values)
            dates = {key: values[key] for key in ('created_at', 'edited_at') if key in values}
            if dates:
                model('tasks', 'TaskProjectNote').objects.using(db).filter(pk=copied.pk).update(**dates)
    for source in KSection.objects.using(db).all().iterator():
        space = imported_spaces.get(source.project_id)
        if not space:
            continue
        values = copy_fields(source, Section, ('project_id',))
        section = Section.objects.using(db).create(project_id=space.project_id, **values)
        Section.objects.using(db).filter(pk=section.pk).update(created_at=source.created_at)
        section.favorited_by.set(source.favorited_by.all())
        sections[source.pk] = section
        link('section', source.pk, section.pk, space)
        for member in model('kanban', 'KanbanSectionMembership').objects.using(db).filter(section=source):
            model('tasks', 'TaskSectionMembership').objects.using(db).create(section=section, user_id=member.user_id, role=member.role)

    source_cards = list(Card.objects.using(db).select_related('column').all())
    for source in source_cards:
        if source.section_id and source.section_id not in sections:
            continue
        section = sections.get(source.section_id)
        space = spaces.get(section.project_id) if section else None
        values = copy_fields(source, Task, ('section_id', 'parent_id', 'task_id'))
        values.update(section_id=section.pk if section else None, task_id=scope_number(source), visibility='public')
        task = Task.objects.using(db).create(**values)
        Task.objects.using(db).filter(pk=task.pk).update(created_at=source.created_at)
        task.tags.set(source.tags.all())
        tasks[source.pk] = task
        status = source.status
        if source.column_id and space:
            # Preserve both the old column and its independent completion status.
            status = f'column_{source.column_id}_{source.status}'
            settings = space.configuration.settings
            if not any(s['key'] == status for s in settings['statuses']):
                settings['statuses'].append(dict(key=status, label=f'{source.column.title} · {dict(Task._meta.get_field("status").choices).get(source.status, source.status)}', category=source.status, transitions=[]))
        item_for(task, space, status)
        link('task', source.pk, task.pk, space)
    for source in source_cards:
        if source.pk in tasks and source.parent_id in tasks:
            Task.objects.using(db).filter(pk=tasks[source.pk].pk).update(parent_id=tasks[source.parent_id].pk)

    Activity = model('tasks', 'TaskActivity')
    for source in model('kanban', 'KanbanActivity').objects.using(db).all().iterator():
        task = tasks.get(source.task_id)
        if not task:
            continue
        values = copy_fields(source, Activity, ('task_id',))
        metadata = dict(values.get('metadata') or {})
        old_child = metadata.get('subtask_pk')
        if old_child in tasks:
            metadata['subtask_pk'] = tasks[old_child].pk
        values['metadata'] = metadata
        activity = Activity.objects.using(db).create(task=task, **values)
        Activity.objects.using(db).filter(pk=activity.pk).update(created_at=source.created_at)
        activities[source.pk] = activity.pk
        link('activity', source.pk, activity.pk, spaces.get(task.section.project_id) if task.section_id else None)
    for source_name, target_name, kind in [('KanbanAttachment', 'TaskAttachment', 'attachment'), ('KanbanCommentImage', 'TaskCommentImage', 'comment')]:
        Target = model('tasks', target_name)
        for source in model('kanban', source_name).objects.using(db).all().iterator():
            if kind == 'attachment':
                task = tasks.get(source.task_id)
                if not task:
                    continue
                values = copy_fields(source, Target, ('task_id',))
                values['task_id'] = task.pk
            else:
                if source.activity_id not in activities:
                    continue
                values = copy_fields(source, Target, ('activity_id',))
                values['activity_id'] = activities[source.activity_id]
                task = Activity.objects.using(db).get(pk=values['activity_id']).task
            target = Target.objects.using(db).create(**values)
            if kind == 'attachment':
                Target.objects.using(db).filter(pk=target.pk).update(uploaded_at=source.uploaded_at)
            link(kind, source.pk, target.pk, spaces.get(task.section.project_id) if task.section_id else None)
    for space in spaces.values():
        Space.objects.using(db).filter(pk=space.pk).update(next_number=space.next_number)
        settings = space.configuration.settings
        keys = [s['key'] for s in settings['statuses']]
        for status in settings['statuses']:
            status['transitions'] = [key for key in keys if key != status['key']]
        Config.objects.using(db).filter(pk=space.configuration_id).update(settings=settings)

    for name in ('NotificationState', 'ActivityInterest'):
        Model = model('dashboard', name)
        for old, new in activities.items():
            Model.objects.using(db).filter(kanban_activity_id=old).update(kanban_activity_id=None, task_activity_id=new)
    Follow = model('dashboard', 'ObjectFollow')
    for old, task in tasks.items():
        Follow.objects.using(db).filter(kanban_id=old).update(kanban_id=None, task_id=task.pk)
    for old, space in imported_spaces.items():
        Follow.objects.using(db).filter(kanban_project_id=old).update(kanban_project_id=None, task_project_id=space.project_id)


class Migration(migrations.Migration):
    dependencies = [('spaces', '0001_initial'), ('kanban', '0039_sharing'), ('dashboard', '0006_section_sharing')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
