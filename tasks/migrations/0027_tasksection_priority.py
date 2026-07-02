from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0026_extend_taskproject_priority_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='tasksection',
            name='priority',
            field=models.CharField(
                blank=True,
                choices=[
                    ('none', 'Brak'),
                    ('low', 'Niski'),
                    ('medium', 'Średni'),
                    ('high', 'Wysoki'),
                    ('urgent', 'Pilny'),
                ],
                default='none',
                max_length=10,
            ),
        ),
    ]
