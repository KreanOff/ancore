from django.db import migrations, models


def backfill_sidebar_favorite_positions(apps, schema_editor):
    SidebarFavorite = apps.get_model('workplaces', 'SidebarFavorite')
    owner_pairs = (
        SidebarFavorite.objects.order_by()
        .values_list('user_id', 'workplace_id')
        .distinct()
    )
    for user_id, workplace_id in owner_pairs.iterator():
        favorites = list(
            SidebarFavorite.objects.filter(user_id=user_id, workplace_id=workplace_id)
            .order_by('created_at', 'id')
        )
        for position, favorite in enumerate(favorites):
            favorite.position = position
        SidebarFavorite.objects.bulk_update(favorites, ['position'])


class Migration(migrations.Migration):

    dependencies = [
        ('workplaces', '0006_sidebarfavorite'),
    ]

    operations = [
        migrations.AddField(
            model_name='sidebarfavorite',
            name='position',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(backfill_sidebar_favorite_positions, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='sidebarfavorite',
            options={'ordering': ['position', 'created_at', 'id']},
        ),
    ]
