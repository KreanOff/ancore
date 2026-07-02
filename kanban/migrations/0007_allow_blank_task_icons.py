from django.db import migrations, models


def clear_default_section_icons(apps, schema_editor):
    KanbanSection = apps.get_model('kanban', 'KanbanSection')
    KanbanSection.objects.filter(icon__in=['check', '☑️']).update(icon='')


class Migration(migrations.Migration):

    dependencies = [
        ('kanban', '0006_tasksection_icon'),
    ]

    operations = [
        migrations.AlterField(
            model_name='kanbanproject',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=8),
        ),
        migrations.AlterField(
            model_name='kanbansection',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=8),
        ),
        migrations.RunPython(clear_default_section_icons, migrations.RunPython.noop),
    ]
