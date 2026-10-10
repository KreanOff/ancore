from django.db import migrations, models
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    Dashboard = apps.get_model('dashboard', 'Dashboard')
    used = {}
    for dashboard in Dashboard.objects.using(schema_editor.connection.alias).order_by('pk').iterator():
        occupied = used.setdefault(dashboard.workplace_id, set())
        base = slugify(dashboard.name.translate(str.maketrans({'ł': 'l', 'Ł': 'L'}))) or 'pulpit'
        if base in {'default', 'manage', 'create', 'search', 'groups'} or base.isdecimal():
            base = 'pulpit-' + base
        base = base[:170].rstrip('-')
        candidate = base
        number = 2
        while candidate in occupied:
            suffix = f'-{number}'
            candidate = base[:170 - len(suffix)].rstrip('-') + suffix
            number += 1
        occupied.add(candidate)
        Dashboard.objects.using(schema_editor.connection.alias).filter(pk=dashboard.pk).update(slug=candidate)


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0011_default_dashboard')]
    operations = [
        migrations.AddField(
            model_name='dashboard', name='slug',
            field=models.SlugField(default='', editable=False, max_length=170), preserve_default=False,
        ),
        migrations.RunPython(populate_slugs, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='dashboard',
            constraint=models.UniqueConstraint(fields=('workplace', 'slug'), name='dashboard_workspace_slug'),
        ),
    ]
