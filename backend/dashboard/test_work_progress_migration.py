from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from tasks.models import Task
from workplaces.models import create_workplace_for_user


class WorkProgressMigrationTests(TransactionTestCase):
    def test_replaces_old_gadgets_once_and_preserves_dashboards_and_tasks(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [('dashboard', '0009_remove_dashboard_groups')]
        owner = get_user_model().objects.create_user(username='progress-migration', email='progress-migration@example.test')
        member = get_user_model().objects.create_user(username='progress-migration-member', email='progress-member@example.test')
        workplace = create_workplace_for_user(owner, 'Migracja postępu pracy')
        other = create_workplace_for_user(owner, 'Drugi Workspace')
        task = Task.objects.create(user=owner, workplace=workplace, title='Zachowane zadanie', status='closed')
        task_before = Task.objects.values().get(pk=task.pk)
        try:
            executor.migrate(previous)
            old_apps = executor.loader.project_state(previous).apps
            Dashboard = old_apps.get_model('dashboard', 'Dashboard')
            Gadget = old_apps.get_model('dashboard', 'DashboardGadget')
            dashboard = Dashboard.objects.create(owner_id=owner.pk, created_by_id=member.pk, workplace_id=workplace.pk,
                                                 name='Plan', description='Opis', visibility='selected', layout='three', revision=7)
            dashboard.shared_with.add(owner.pk)
            dashboard.favorited_by.add(owner.pk, member.pk)
            empty = Dashboard.objects.create(owner_id=owner.pk, created_by_id=owner.pk, workplace_id=workplace.pk, name='Pusty')
            foreign = Dashboard.objects.create(owner_id=owner.pk, created_by_id=owner.pk, workplace_id=other.pk, name='Drugi')
            retained = Gadget.objects.create(dashboard=dashboard, kind='activity', title='Stary tytuł',
                                              assignee='me', status='closed', group_by='priority', limit=5, column=1, position=2)
            for kind in ['assigned', 'results', 'summary', 'statistics']:
                Gadget.objects.create(dashboard=dashboard, kind=kind, column=2)
            existing = Gadget.objects.create(dashboard=foreign, kind='progress', title='Własny postęp', assignee='me')
            Gadget.objects.create(dashboard=foreign, kind='summary')
            executor = MigrationExecutor(connection)
            target = [('dashboard', '0010_work_progress_gadget')]
            executor.migrate(target)
            new_apps = executor.loader.project_state(target).apps
            NewDashboard = new_apps.get_model('dashboard', 'Dashboard')
            NewGadget = new_apps.get_model('dashboard', 'DashboardGadget')
            saved = NewDashboard.objects.get(pk=dashboard.pk)
            self.assertEqual((saved.name, saved.description, saved.created_by_id, saved.owner_id, saved.workplace_id),
                             ('Plan', 'Opis', member.pk, owner.pk, workplace.pk))
            self.assertEqual((saved.layout, saved.visibility, saved.revision), ('three', 'selected', 8))
            self.assertEqual(list(saved.shared_with.values_list('pk', flat=True)), [owner.pk])
            self.assertEqual(set(saved.favorited_by.values_list('pk', flat=True)), {owner.pk, member.pk})
            gadget = saved.gadgets.get()
            self.assertEqual((gadget.pk, gadget.kind, gadget.column, gadget.position), (retained.pk, 'progress', 1, 2))
            self.assertEqual((gadget.title, gadget.space_id, gadget.assignee), ('', None, 'all'))
            self.assertFalse(NewGadget.objects.filter(dashboard_id=empty.pk).exists())
            self.assertEqual(NewDashboard.objects.get(pk=empty.pk).revision, 0)
            self.assertEqual(NewDashboard.objects.get(pk=foreign.pk).revision, 1)
            self.assertEqual(NewGadget.objects.get(dashboard_id=foreign.pk).pk, existing.pk)
            self.assertEqual(NewGadget.objects.get(pk=existing.pk).title, 'Własny postęp')
            self.assertEqual(Task.objects.values().get(pk=task.pk), task_before)
            migration = __import__('importlib').import_module('dashboard.migrations.0010_work_progress_gadget')
            migration.replace_retired_gadgets(new_apps, connection.schema_editor())
            self.assertEqual(NewDashboard.objects.get(pk=dashboard.pk).revision, 8)
            self.assertEqual(NewGadget.objects.count(), 2)
        finally:
            MigrationExecutor(connection).migrate(latest)
