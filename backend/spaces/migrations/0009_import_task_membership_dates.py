from django.db import migrations


def import_dates(apps, schema_editor):
    Item = apps.get_model('spaces', 'WorkItem')
    Member = apps.get_model('spaces', 'SpaceTaskMembership')
    LegacyMember = apps.get_model('tasks', 'TaskMembership')
    db = schema_editor.connection.alias
    for item in Item.objects.using(db).filter(task__isnull=False, legacy_task__isnull=False).iterator(chunk_size=500):
        for source in LegacyMember.objects.using(db).filter(task_id=item.legacy_task_id).iterator():
            Member.objects.using(db).filter(task_id=item.task_id, user_id=source.user_id).update(created_at=source.created_at)


class Migration(migrations.Migration):
    dependencies = [('spaces', '0008_spacetask_reminder_at_spacetask_task_type_and_more')]
    operations = [migrations.RunPython(import_dates, migrations.RunPython.noop)]
