from django.db import migrations


def archive_sources(apps, schema_editor):
    db = schema_editor.connection.alias
    projects = apps.get_model('spaces', 'Space').objects.using(db).exclude(project_id=None).values('project_id')
    tasks = apps.get_model('spaces', 'WorkItem').objects.using(db).filter(task__isnull=False).exclude(legacy_task_id=None).values('legacy_task_id')
    apps.get_model('tasks', 'TaskProject').objects.using(db).filter(pk__in=projects).update(space_archived=True)
    apps.get_model('tasks', 'Task').objects.using(db).filter(pk__in=tasks).update(space_archived=True)


class Migration(migrations.Migration):
    dependencies = [('spaces', '0006_independent_space_tasks'), ('tasks', '0066_task_space_archived_taskproject_space_archived')]
    operations = [migrations.RunPython(archive_sources, migrations.RunPython.noop)]
