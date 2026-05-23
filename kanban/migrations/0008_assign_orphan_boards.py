from django.conf import settings
from django.db import migrations


def assign_orphan_boards(apps, schema_editor):
    Workspace = apps.get_model('kanban', 'Workspace')
    KanbanBoard = apps.get_model('kanban', 'KanbanBoard')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))

    for user in User.objects.all():
        orphans = KanbanBoard.objects.filter(user_id=user.pk, workspace__isnull=True)
        if not orphans.exists():
            continue
        workspace = Workspace.objects.filter(user_id=user.pk).order_by('created_at').first()
        if workspace is None:
            workspace = Workspace.objects.create(name='Moja Przestrzeń', user_id=user.pk)
        orphans.update(workspace_id=workspace.pk)


class Migration(migrations.Migration):

    dependencies = [
        ('kanban', '0007_kanbanboard_custom_background'),
    ]

    operations = [
        migrations.RunPython(assign_orphan_boards, migrations.RunPython.noop),
    ]
