from django.db import migrations, models


def preserve_column_layouts(apps, schema_editor):
    Dashboard = apps.get_model('dashboard', 'Dashboard')
    Gadget = apps.get_model('dashboard', 'DashboardGadget')
    database = schema_editor.connection.alias
    widths_by_layout = {'single': (12,), 'equal': (6, 6), 'left': (8, 4), 'right': (4, 8), 'three': (4, 4, 4)}
    for dashboard in Dashboard.objects.using(database).iterator():
        widths = widths_by_layout[dashboard.layout]
        counts = [0] * len(widths)
        for gadget in Gadget.objects.using(database).filter(dashboard_id=dashboard.pk).order_by('column', 'position', 'pk'):
            column = min(gadget.column, len(widths) - 1)
            Gadget.objects.using(database).filter(pk=gadget.pk).update(
                x=sum(widths[:column]), y=counts[column] * 8, w=widths[column], h=8)
            counts[column] += 1


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0007_remove_workspace_invitations')]
    operations = [
        migrations.AddField(model_name='dashboardgadget', name=field,
                            field=models.PositiveSmallIntegerField(blank=True, null=True))
        for field in ('x', 'y', 'w', 'h')
    ] + [migrations.RunPython(preserve_column_layouts, migrations.RunPython.noop)]
