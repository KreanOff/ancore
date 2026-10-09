import secrets

from django.db import migrations


TAG_FIELDS = ('name', 'description', 'category', 'color', 'icon', 'priority', 'scope',
              'owner_label', 'status', 'usage_notes', 'automation_rules', 'user_id', 'workplace_id')
NOTE_FIELDS = ('author_id', 'message', 'created_at', 'updated_at', 'edited_at')


def copy_space_tags(apps, schema_editor):
    Tag = apps.get_model('tasks', 'TaskTag')
    Note = apps.get_model('tasks', 'TaskTagNote')
    Task = apps.get_model('tasks', 'Task')
    Space = apps.get_model('spaces', 'Space')
    alias = schema_editor.connection.alias
    tags, notes, links = Tag.objects.using(alias), Note.objects.using(alias), Task.tags.through.objects.using(alias)
    for space in Space.objects.using(alias).select_related('project').iterator():
        task_ids = Task.objects.using(alias).filter(section__project_id=space.project_id).values('pk')
        sources = tags.filter(user_id=space.project.user_id, workplace_id=space.workplace_id, space__isnull=True)
        pending = set(links.filter(task_id__in=task_ids).values_list('tasktag_id', flat=True))
        copies = {}
        while pending:
            source = sources.filter(pk=pending.pop()).first()
            if source is None or source.pk in copies:
                continue
            while True:
                code = 'T-' + ''.join(secrets.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
                if not tags.filter(code=code).exists():
                    break
            copy = tags.create(space_id=space.pk, code=code, **{field: getattr(source, field) for field in TAG_FIELDS})
            tags.filter(pk=copy.pk).update(created_at=source.created_at)
            copies[source.pk] = copy.pk
            for note in notes.filter(tag_id=source.pk):
                copied_note = notes.create(tag_id=copy.pk, **{field: getattr(note, field) for field in NOTE_FIELDS})
                notes.filter(pk=copied_note.pk).update(created_at=note.created_at, updated_at=note.updated_at)
            pending.update(source.related_tags.using(alias).exclude(pk__in=copies).values_list('pk', flat=True))
        for source_id, copy_id in copies.items():
            links.filter(task_id__in=task_ids, tasktag_id=source_id).update(tasktag_id=copy_id)
            copy = tags.get(pk=copy_id)
            related = sources.get(pk=source_id).related_tags.using(alias).values_list('pk', flat=True)
            copy.related_tags.set([copies[pk] for pk in related if pk in copies])


def restore_legacy_tags(apps, schema_editor):
    Tag = apps.get_model('tasks', 'TaskTag')
    Note = apps.get_model('tasks', 'TaskTagNote')
    Task = apps.get_model('tasks', 'Task')
    alias = schema_editor.connection.alias
    tags, notes, links = Tag.objects.using(alias), Note.objects.using(alias), Task.tags.through.objects.using(alias)
    copies = list(tags.filter(space__isnull=False))
    mapping = {}
    for copy in copies:
        original = tags.filter(space__isnull=True, user_id=copy.user_id, workplace_id=copy.workplace_id, name=copy.name).first()
        if original is None:
            original = tags.create(code=copy.code + '-L', **{field: getattr(copy, field) for field in TAG_FIELDS})
            tags.filter(pk=original.pk).update(created_at=copy.created_at)
        mapping[copy.pk] = original.pk
        for link in links.filter(tasktag_id=copy.pk).iterator():
            links.get_or_create(task_id=link.task_id, tasktag_id=original.pk)
        for note in notes.filter(tag_id=copy.pk):
            if not notes.filter(tag_id=original.pk, author_id=note.author_id, message=note.message, created_at=note.created_at).exists():
                saved = notes.create(tag_id=original.pk, **{field: getattr(note, field) for field in NOTE_FIELDS})
                notes.filter(pk=saved.pk).update(created_at=note.created_at, updated_at=note.updated_at)
    for copy in copies:
        original = tags.get(pk=mapping[copy.pk])
        original.related_tags.add(*[mapping[pk] for pk in copy.related_tags.using(alias).values_list('pk', flat=True) if pk in mapping and mapping[pk] != original.pk])
    tags.filter(pk__in=mapping).delete()


class Migration(migrations.Migration):
    dependencies = [('tasks', '0064_space_tags')]
    operations = [migrations.RunPython(copy_space_tags, restore_legacy_tags)]
