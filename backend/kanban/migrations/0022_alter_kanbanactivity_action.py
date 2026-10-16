from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kanban', '0021_board_columns_belong_to_sections'),
    ]

    operations = [
        migrations.AlterField(
            model_name='kanbanactivity',
            name='action',
            field=models.CharField(choices=[('created', 'Utworzono kartę'), ('updated', 'Zaktualizowano kartę'), ('status_changed', 'Zmieniono status'), ('priority_changed', 'Zmieniono priorytet'), ('commented', 'Dodano komentarz'), ('subtask_created', 'Dodano podkartę'), ('attachments_added', 'Dodano załączniki'), ('attachments_deleted', 'Usunięto załączniki')], default='updated', max_length=32),
        ),
    ]
