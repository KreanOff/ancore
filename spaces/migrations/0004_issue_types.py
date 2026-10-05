from django.db import migrations


def add_issue_types(apps, schema_editor):
    Configuration = apps.get_model('spaces', 'SpaceConfiguration')
    types = [('task', 'Zadanie'), ('bug', 'Błąd'), ('story', 'Historyjka'), ('epic', 'Epik')]
    for config in Configuration.objects.using(schema_editor.connection.alias).all().iterator():
        settings = config.settings
        existing = {row['key'] for row in settings.get('types', [])}
        missing = [{'key': key, 'label': label} for key, label in types if key not in existing]
        if missing:
            config.settings = {**settings, 'types': [*settings.get('types', []), *missing]}
            config.save(update_fields=['settings'])


class Migration(migrations.Migration):
    dependencies = [('spaces', '0003_space_avatar_space_avatar_photo')]
    # Preserve configured types on rollback: tasks may already use the added keys.
    operations = [migrations.RunPython(add_issue_types, migrations.RunPython.noop)]
