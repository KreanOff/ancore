from django.db import migrations


class Migration(migrations.Migration):
    """Restore the dependency referenced by the project-notes migration."""

    dependencies = [
        ('kanban', '0028_prepare_shared_task_tags'),
    ]

    operations = []
