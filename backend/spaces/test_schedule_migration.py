"""Upgrade existing planning dates without shifting their local calendar day."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from workplaces.models import create_workplace_for_user
from .models import SpaceTask, WorkItem
from .testing import make_space


@override_settings(TIME_ZONE='Europe/Warsaw')
class ScheduleMigrationTests(TransactionTestCase):
    def test_existing_dates_nulls_and_identity_survive_forward_and_reverse(self):
        owner = get_user_model().objects.create_user(username='schedule-migration', email='schedule-migration@example.test')
        workplace = create_workplace_for_user(owner, 'Migracja dat')
        space = make_space(user=owner, workplace=workplace, name='Zachowany harmonogram')
        tasks = [SpaceTask.objects.create(space=space, created_by=owner, title=title)
                 for title in ('Zima', 'Lato', 'Brak daty')]
        ids = [task.work_item.pk for task in tasks]
        identity = list(WorkItem.objects.filter(pk__in=ids).order_by('pk').values_list('pk', 'task_id', 'space_id', 'key', 'number'))
        old_target = [('spaces', '0003_space_dashboard_layout')]
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(old_target)
            old_items = executor.loader.project_state(old_target).apps.get_model('spaces', 'WorkItem')
            dates = [date(2026, 1, 10), date(2026, 7, 10), None]
            for pk, start_on in zip(ids, dates):
                old_items.objects.filter(pk=pk).update(start_on=start_on)
            # An unrelated active timezone must not change migration semantics.
            with timezone.override('UTC'):
                MigrationExecutor(connection).migrate(latest)
            rows = list(WorkItem.objects.filter(pk__in=ids).order_by('pk'))
            self.assertEqual([(row.pk, row.task_id, row.space_id, row.key, row.number) for row in rows], identity)
            for row, day, offset in zip(rows[:2], dates[:2], (3600, 7200)):
                local = timezone.localtime(row.start_at, ZoneInfo('Europe/Warsaw'))
                self.assertEqual(local.date(), day)
                self.assertEqual(local.time(), time())
                self.assertEqual(local.utcoffset().total_seconds(), offset)
            self.assertIsNone(rows[2].start_at)
            late = datetime(2026, 7, 12, 0, 30, tzinfo=ZoneInfo('Europe/Warsaw'))
            WorkItem.objects.filter(pk=ids[1]).update(start_at=late)
            with timezone.override('UTC'):
                MigrationExecutor(connection).migrate(old_target)
            self.assertEqual(list(old_items.objects.filter(pk__in=ids).order_by('pk').values_list('start_on', flat=True)),
                             [dates[0], date(2026, 7, 12), None])
            MigrationExecutor(connection).migrate(latest)
            self.assertEqual(timezone.localtime(WorkItem.objects.get(pk=ids[1]).start_at).date(), date(2026, 7, 12))
        finally:
            MigrationExecutor(connection).migrate(latest)
