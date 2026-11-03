from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('spaces', '0005_kanban_flow')]

    operations = [
        migrations.AlterField(
            model_name='spacetask',
            name='task_type',
            field=models.CharField(default='general', max_length=20),
        ),
        migrations.AddField(
            model_name='spacetask',
            name='task_group',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
    ]
