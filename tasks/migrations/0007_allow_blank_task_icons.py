from django.db import migrations, models


def clear_default_section_icons(apps, schema_editor):
    TaskSection = apps.get_model('tasks', 'TaskSection')
    TaskSection.objects.filter(icon__in=['check', '☑️']).update(icon='')


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0006_tasksection_icon'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskproject',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=8),
        ),
        migrations.AlterField(
            model_name='tasksection',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=8),
        ),
        migrations.RunPython(clear_default_section_icons, migrations.RunPython.noop),
    ]
