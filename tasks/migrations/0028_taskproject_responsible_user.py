import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tasks', '0027_tasksection_priority'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskproject',
            name='responsible_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='responsible_task_projects', to=settings.AUTH_USER_MODEL),
        ),
    ]
