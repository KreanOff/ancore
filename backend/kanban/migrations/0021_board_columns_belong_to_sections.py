import django.db.models.deletion
from django.db import migrations, models


DEFAULT_COLUMNS = [
    {'title': 'Zaległości', 'order': 0, 'is_done': False},
    {'title': 'Wszystko', 'order': 1, 'is_done': False},
    {'title': 'Zrobione', 'order': 2, 'is_done': True},
]
VALID_STATUSES = {'new', 'in_progress', 'resolved', 'closed', 'reopened'}


def migrate_section_columns(apps, schema_editor):
    Kanban = apps.get_model('kanban', 'Kanban')
    KanbanBoardColumn = apps.get_model('kanban', 'KanbanBoardColumn')
    KanbanSection = apps.get_model('kanban', 'KanbanSection')

    KanbanBoardColumn.objects.all().delete()

    for section in KanbanSection.objects.all():
        columns = [
            KanbanBoardColumn.objects.create(section=section, user_id=section.project.user_id, **definition)
            for definition in DEFAULT_COLUMNS
        ]
        for task in Kanban.objects.filter(section=section):
            if task.status not in VALID_STATUSES:
                task.status = 'new'
            if task.status == 'closed':
                task.column = columns[2]
            elif task.status in ('in_progress', 'resolved'):
                task.column = columns[1]
            else:
                task.column = columns[0]
            task.save(update_fields=['column', 'status'])

    Kanban.objects.exclude(status__in=VALID_STATUSES).update(status='new')


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('kanban', '0020_kanbanboardcolumn_alter_kanban_status'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='kanbanboardcolumn',
            name='unique_kanban_board_column_status_per_user',
        ),
        migrations.AddField(
            model_name='kanbanboardcolumn',
            name='section',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='columns', to='kanban.kanbansection'),
        ),
        migrations.AddField(
            model_name='kanban',
            name='column',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cards', to='kanban.kanbanboardcolumn'),
        ),
        migrations.RunPython(migrate_section_columns, noop_reverse),
        migrations.RemoveField(
            model_name='kanbanboardcolumn',
            name='status_code',
        ),
        migrations.RemoveField(
            model_name='kanbanboardcolumn',
            name='status_values',
        ),
        migrations.RemoveField(
            model_name='kanbanboardcolumn',
            name='user',
        ),
        migrations.AlterField(
            model_name='kanbanboardcolumn',
            name='section',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='columns', to='kanban.kanbansection'),
        ),
    ]
