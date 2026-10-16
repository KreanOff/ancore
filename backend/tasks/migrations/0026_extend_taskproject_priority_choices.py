from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0025_taskproject_priority_due_at_company'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskproject',
            name='priority',
            field=models.CharField(blank=True, choices=[('none', 'Brak'), ('low', 'Niski'), ('medium', 'Średni'), ('high', 'Wysoki'), ('urgent', 'Pilny')], default='none', max_length=10),
        ),
    ]
