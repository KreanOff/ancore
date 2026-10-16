from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


DEFAULT_OPTIONS = {
    'status': [
        ('planned', 'Planowany', '#EEE8FF'),
        ('active', 'Aktywny', '#DFEFFF'),
        ('on_hold', 'Wstrzymany', '#FFEBC9'),
        ('completed', 'Zakończony', '#DFF1E7'),
        ('cancelled', 'Anulowany', '#E9ECF0'),
    ],
    'stage': [
        ('lead', 'Lead', '#F5E3F7'),
        ('offer', 'Oferta', '#FFE5D1'),
        ('contract', 'Umowa', '#E6E4FF'),
        ('implementation', 'Realizacja', '#DFF2F4'),
        ('support', 'Utrzymanie', '#DFF1E7'),
        ('internal', 'Wewnętrzny', '#E7EBF1'),
    ],
    'health': [
        ('ok', 'OK', '#DFF1E7'),
        ('at_risk', 'Zagrożony', '#FFEBC9'),
        ('delayed', 'Opóźniony', '#FFE0DC'),
    ],
}


def create_default_options(apps, schema_editor):
    task_project = apps.get_model('tasks', 'TaskProject')
    field_option = apps.get_model('tasks', 'TaskProjectFieldOption')
    scopes = task_project.objects.order_by().values_list('user_id', 'workplace_id').distinct()
    options = []
    for owner_id, workplace_id in scopes.iterator():
        for field_type, defaults in DEFAULT_OPTIONS.items():
            options.extend(
                field_option(
                    owner_id=owner_id,
                    workplace_id=workplace_id,
                    field_type=field_type,
                    value=value,
                    label=label,
                    color=color,
                    position=position,
                )
                for position, (value, label, color) in enumerate(defaults)
            )
    field_option.objects.bulk_create(options, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0040_note_edited_at'),
        ('workplaces', '0003_workplace_workplace_photo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskproject',
            name='health',
            field=models.CharField(default='ok', max_length=20),
        ),
        migrations.AlterField(
            model_name='taskproject',
            name='stage',
            field=models.CharField(default='implementation', max_length=20),
        ),
        migrations.AlterField(
            model_name='taskproject',
            name='status',
            field=models.CharField(default='active', max_length=20),
        ),
        migrations.CreateModel(
            name='TaskProjectFieldOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_type', models.CharField(choices=[('status', 'Status projektu'), ('stage', 'Etap'), ('health', 'Kondycja')], max_length=10)),
                ('value', models.SlugField(max_length=20)),
                ('label', models.CharField(max_length=60)),
                ('color', models.CharField(default='#DFEFFF', max_length=7, validators=[django.core.validators.RegexValidator('^#[0-9A-Fa-f]{6}$', 'Podaj kolor w formacie #RRGGBB.')])),
                ('position', models.PositiveSmallIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_project_field_options', to=settings.AUTH_USER_MODEL)),
                ('workplace', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='task_project_field_options', to='workplaces.workplace')),
            ],
            options={
                'ordering': ['field_type', 'position', 'id'],
                'indexes': [models.Index(fields=['owner', 'workplace', 'field_type', 'is_active', 'position'], name='taskproj_option_scope_idx')],
                'constraints': [
                    models.UniqueConstraint(condition=models.Q(('workplace__isnull', False)), fields=('owner', 'workplace', 'field_type', 'value'), name='unique_project_field_option_scope'),
                    models.UniqueConstraint(condition=models.Q(('workplace__isnull', True)), fields=('owner', 'field_type', 'value'), name='unique_project_field_option_no_workplace'),
                ],
            },
        ),
        migrations.RunPython(create_default_options, migrations.RunPython.noop),
    ]
