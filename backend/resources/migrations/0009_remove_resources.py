from django.db import migrations


def remove_permissions(apps, schema_editor):
    permission = apps.get_model('auth', 'Permission')
    permission.objects.using(schema_editor.connection.alias).filter(
        content_type__app_label='resources',
        content_type__model__in=('resource', 'resourceactivity', 'resourcecategory'),
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('resources', '0008_resource_activity_operations'),
    ]

    operations = [
        migrations.DeleteModel(name='ResourceActivity'),
        migrations.DeleteModel(name='ResourceCategory'),
        migrations.DeleteModel(name='Resource'),
        # Some local databases predate the managed custom category table.
        migrations.RunSQL('DROP TABLE IF EXISTS resources_resourcecategory', migrations.RunSQL.noop),
        migrations.RunPython(remove_permissions, migrations.RunPython.noop),
    ]
