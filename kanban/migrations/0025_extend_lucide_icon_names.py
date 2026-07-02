from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kanban', '0024_random_workspace_codes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='kanbanproject',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AlterField(
            model_name='kanbansection',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
    ]
