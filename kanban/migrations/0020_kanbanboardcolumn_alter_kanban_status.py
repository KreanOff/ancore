from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('kanban', '0019_tasktag_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='KanbanBoardColumn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=80)),
                ('status_code', models.CharField(blank=True, max_length=50)),
                ('status_values', models.JSONField(blank=True, default=list)),
                ('order', models.PositiveIntegerField(default=0)),
                ('is_done', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kanban_board_columns', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['order', 'created_at'],
            },
        ),
        migrations.AlterField(
            model_name='kanban',
            name='status',
            field=models.CharField(choices=[('new', 'Nowe'), ('in_progress', 'Realizowane'), ('resolved', 'Rozwiązane'), ('closed', 'Zamknięte'), ('reopened', 'Ponownie otwarte')], default='new', max_length=50),
        ),
        migrations.AddConstraint(
            model_name='kanbanboardcolumn',
            constraint=models.UniqueConstraint(fields=('user', 'status_code'), name='unique_kanban_board_column_status_per_user'),
        ),
    ]
