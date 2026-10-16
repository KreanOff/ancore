import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0012_unique_task_project_code_per_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='time_spent_hours',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='time_spent_minutes',
            field=models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(59)]),
        ),
    ]
