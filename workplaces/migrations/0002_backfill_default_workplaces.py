from django.db import migrations


DEFAULT_WORKPLACE_NAME = 'Moje workplace'


def backfill_default_workplaces(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Workplace = apps.get_model('workplaces', 'Workplace')
    WorkplaceMembership = apps.get_model('workplaces', 'WorkplaceMembership')

    models_by_owner_field = [
        ('tasks', 'TaskProject', 'user'),
        ('tasks', 'TaskTag', 'user'),
        ('tasks', 'Task', 'user'),
        ('kanban', 'KanbanProject', 'user'),
        ('kanban', 'KanbanTag', 'user'),
        ('kanban', 'Kanban', 'user'),
        ('contacts', 'Company', 'owner'),
        ('contacts', 'Contact', 'user'),
        ('contacts', 'UserContact', 'owner'),
        ('planner', 'CalendarEvent', 'user'),
    ]

    for user in User.objects.all().iterator():
        workplace, _created = Workplace.objects.get_or_create(
            owner_id=user.pk,
            name=DEFAULT_WORKPLACE_NAME,
            defaults={'slug': f'moje-workplace-{user.pk}'},
        )
        if not workplace.slug:
            workplace.slug = f'moje-workplace-{user.pk}'
            workplace.save(update_fields=['slug'])

        WorkplaceMembership.objects.get_or_create(
            workplace_id=workplace.pk,
            user_id=user.pk,
            defaults={'role': 'owner'},
        )

        for app_label, model_name, owner_field in models_by_owner_field:
            model = apps.get_model(app_label, model_name)
            model.objects.filter(
                **{f'{owner_field}_id': user.pk, 'workplace__isnull': True},
            ).update(workplace_id=workplace.pk)


class Migration(migrations.Migration):

    dependencies = [
        ('workplaces', '0001_initial'),
        ('tasks', '0034_remove_tasktag_unique_task_tag_per_user_and_more'),
        ('kanban', '0027_remove_kanbantag_unique_kanban_tag_per_user_and_more'),
        ('contacts', '0008_remove_company_unique_company_name_per_owner_and_more'),
        ('planner', '0002_calendarevent_workplace'),
    ]

    operations = [
        migrations.RunPython(backfill_default_workplaces, migrations.RunPython.noop),
    ]
