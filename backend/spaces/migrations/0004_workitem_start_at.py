"""Preserve existing planning dates as local midnight, independently of DB timezone."""
from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import migrations, models


def copy_start_dates(apps, schema_editor):
    items = apps.get_model('spaces', 'WorkItem').objects.using(schema_editor.connection.alias)
    zone = ZoneInfo(settings.TIME_ZONE)
    for item in items.exclude(start_on=None).iterator(chunk_size=1000):
        items.filter(pk=item.pk).update(start_at=datetime.combine(item.start_on, time(), tzinfo=zone))


def restore_start_dates(apps, schema_editor):
    items = apps.get_model('spaces', 'WorkItem').objects.using(schema_editor.connection.alias)
    zone = ZoneInfo(settings.TIME_ZONE)
    for item in items.exclude(start_at=None).iterator(chunk_size=1000):
        items.filter(pk=item.pk).update(start_on=item.start_at.astimezone(zone).date())


class Migration(migrations.Migration):
    dependencies = [('spaces', '0003_space_dashboard_layout')]
    operations = [
        migrations.AddField(model_name='workitem', name='start_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.RunPython(copy_start_dates, restore_start_dates),
        migrations.RemoveField(model_name='workitem', name='start_on'),
    ]
