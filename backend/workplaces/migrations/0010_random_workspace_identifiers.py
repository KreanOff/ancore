import secrets
import string

from django.db import migrations, models

import workplaces.models


def assign_random_identifiers(apps, schema_editor):
    Workplace = apps.get_model('workplaces', 'Workplace')
    database = schema_editor.connection.alias
    workplaces = Workplace.objects.using(database)
    reserved = set(workplaces.values_list('slug', flat=True))
    alphabet = string.ascii_lowercase + string.digits
    for workplace in workplaces.order_by('pk').iterator():
        code = 'w_' + ''.join(secrets.choice(alphabet) for _ in range(26))
        while code in reserved:
            code = 'w_' + ''.join(secrets.choice(alphabet) for _ in range(26))
        reserved.add(code)
        workplaces.filter(pk=workplace.pk).update(
            code=code, slug=code, legacy_slug=workplace.slug or None,
        )


class Migration(migrations.Migration):
    dependencies = [('workplaces', '0009_workplace_avatar')]

    operations = [
        migrations.RemoveConstraint(model_name='workplace', name='unique_workplace_name_per_owner'),
        migrations.RemoveConstraint(model_name='workplace', name='unique_workplace_slug_per_owner'),
        migrations.RemoveConstraint(model_name='workplace', name='unique_workplace_code_per_owner'),
        migrations.AddField(
            model_name='workplace', name='legacy_slug',
            field=models.SlugField(blank=True, editable=False, max_length=160, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='workplace', name='code',
            field=models.CharField(default=workplaces.models.generate_workplace_code, editable=False, max_length=28),
        ),
        migrations.AlterField(
            model_name='workplace', name='slug',
            field=models.SlugField(blank=True, editable=False, max_length=160, unique=True),
        ),
        migrations.RunPython(assign_random_identifiers, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='workplace',
            constraint=models.UniqueConstraint(fields=('code',), name='unique_workplace_code'),
        ),
    ]
