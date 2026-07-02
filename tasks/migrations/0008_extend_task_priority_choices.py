from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0007_allow_blank_task_icons'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='priority',
            field=models.CharField(
                choices=[
                    ('none', 'Brak priorytetu'),
                    ('low', 'Niski'),
                    ('medium', 'Średni'),
                    ('high', 'Wysoki'),
                    ('urgent', 'Pilny'),
                ],
                default='medium',
                max_length=10,
            ),
        ),
    ]
