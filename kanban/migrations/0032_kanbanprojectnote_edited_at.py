from datetime import timedelta

from django.db import migrations, models


def backfill_edited_at(apps, schema_editor):
    note_model = apps.get_model('kanban', 'KanbanProjectNote')
    for note in note_model.objects.all().iterator():
        if note.updated_at - note.created_at >= timedelta(milliseconds=1):
            note_model.objects.filter(pk=note.pk).update(edited_at=note.updated_at)


def clear_edited_at(apps, schema_editor):
    apps.get_model('kanban', 'KanbanProjectNote').objects.update(edited_at=None)


class Migration(migrations.Migration):

    dependencies = [
        ('kanban', '0031_remove_kanbantag_unique_kanban_tag_code_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='kanbanprojectnote',
            name='edited_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_edited_at, clear_edited_at),
    ]
