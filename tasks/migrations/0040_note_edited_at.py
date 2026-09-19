from datetime import timedelta

from django.db import migrations, models


def backfill_edited_at(apps, schema_editor):
    for model_name in ('TaskProjectNote', 'TaskSectionNote', 'TaskTagNote'):
        note_model = apps.get_model('tasks', model_name)
        for note in note_model.objects.all().iterator():
            if note.updated_at - note.created_at >= timedelta(milliseconds=1):
                note_model.objects.filter(pk=note.pk).update(edited_at=note.updated_at)


def clear_edited_at(apps, schema_editor):
    for model_name in ('TaskProjectNote', 'TaskSectionNote', 'TaskTagNote'):
        apps.get_model('tasks', model_name).objects.update(edited_at=None)


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0039_remove_taskproject_unique_task_project_code_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskprojectnote',
            name='edited_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tasksectionnote',
            name='edited_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tasktagnote',
            name='edited_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_edited_at, clear_edited_at),
    ]
