from django.db import migrations
from django.db.models import Q


def remove_retired_modules(apps, schema_editor):
    alias = schema_editor.connection.alias
    retired = ('resources', 'teams')
    favorites = apps.get_model('workplaces', 'SidebarFavorite').objects.using(alias)
    favorites.filter(item_key__in=retired).delete()

    workplaces = apps.get_model('workplaces', 'Workplace').objects.using(alias)
    affected = workplaces.filter(
        Q(disabled_modules__contains=['resources']) | Q(disabled_modules__contains=['teams'])
    ).only('disabled_modules')
    for workplace in affected.iterator():
        disabled = [key for key in workplace.disabled_modules if key not in retired]
        workplaces.filter(pk=workplace.pk).update(disabled_modules=disabled)


class Migration(migrations.Migration):
    dependencies = [
        ('workplaces', '0005_remove_email_invitations'),
    ]

    operations = [
        migrations.RunPython(remove_retired_modules, migrations.RunPython.noop),
    ]
