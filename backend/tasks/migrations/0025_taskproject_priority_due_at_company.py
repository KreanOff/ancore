import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0003_company_contact_company_record_companymembership_and_more'),
        ('tasks', '0024_extend_lucide_icon_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskproject',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='task_projects', to='contacts.company'),
        ),
        migrations.AddField(
            model_name='taskproject',
            name='due_at',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taskproject',
            name='priority',
            field=models.CharField(blank=True, choices=[('none', 'Brak'), ('low', 'Niski'), ('medium', 'Średni'), ('high', 'Wysoki')], default='none', max_length=10),
        ),
    ]
