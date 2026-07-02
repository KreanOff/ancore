from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0023_alter_task_section_cascade'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskproject',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AlterField(
            model_name='tasksection',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
    ]
