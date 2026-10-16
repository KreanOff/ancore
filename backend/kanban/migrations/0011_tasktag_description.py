from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kanban', '0010_tasktag_task_tags_tasktag_unique_task_tag_per_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='kanbantag',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
