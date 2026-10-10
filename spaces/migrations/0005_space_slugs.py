from django.db import migrations, models
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    Space = apps.get_model('spaces', 'Space')
    database = schema_editor.connection.alias
    used = {}
    for space in Space.objects.using(database).select_related('project').order_by('pk').iterator():
        occupied = used.setdefault(space.workplace_id, set())
        base = slugify(space.project.name.translate(str.maketrans({'ł': 'l', 'Ł': 'L'}))) or 'przestrzen'
        if base.isdecimal():
            base = 'przestrzen-' + base
        base = base[:170].rstrip('-')
        candidate = base
        number = 2
        while candidate in occupied:
            suffix = f'-{number}'
            candidate = base[:170 - len(suffix)].rstrip('-') + suffix
            number += 1
        occupied.add(candidate)
        Space.objects.using(database).filter(pk=space.pk).update(slug=candidate)


class Migration(migrations.Migration):
    dependencies = [('spaces', '0004_issue_types')]
    operations = [
        migrations.AddField(
            model_name='space', name='slug',
            field=models.SlugField(default='', editable=False, max_length=170), preserve_default=False,
        ),
        migrations.RunPython(populate_slugs, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='space',
            constraint=models.UniqueConstraint(fields=('workplace', 'slug'), name='space_workspace_slug'),
        ),
    ]
