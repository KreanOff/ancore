from django.db import migrations


def remove_permissions(apps, schema_editor):
    permission = apps.get_model('auth', 'Permission')
    permission.objects.using(schema_editor.connection.alias).filter(
        content_type__app_label='spaces',
        content_type__model__in=('team', 'teammembership'),
    ).delete()


class Migration(migrations.Migration):
    dependencies = [('spaces', '0006_task_classification')]

    operations = [
        migrations.RemoveField(model_name='workitem', name='team'),
        migrations.RemoveField(model_name='team', name='members'),
        migrations.DeleteModel(name='TeamMembership'),
        migrations.DeleteModel(name='Team'),
        migrations.RunPython(remove_permissions, migrations.RunPython.noop),
    ]
