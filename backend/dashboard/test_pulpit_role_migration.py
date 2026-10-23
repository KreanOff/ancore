from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class PulpitRoleMigrationTests(TransactionTestCase):
    def test_existing_table_relation_ids_and_recipients_survive_forward_and_reverse(self):
        before = [('dashboard', '0004_dashboard_emoji_library')]
        after = [('dashboard', '0005_dashboard_membership_roles')]
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(before)
            apps = executor.loader.project_state(before).apps
            User = apps.get_model('accounts', 'User')
            Workplace = apps.get_model('workplaces', 'Workplace')
            Dashboard = apps.get_model('dashboard', 'Dashboard')
            owner = User.objects.create(username='role-migration-owner', email='owner-role-migration@example.test')
            reader = User.objects.create(username='role-migration-reader', email='reader-role-migration@example.test')
            workspace = Workplace.objects.create(owner_id=owner.pk, name='Migracja ról',
                                                 code='w_role_migration', slug='w_role_migration')
            dashboard = Dashboard.objects.create(owner_id=owner.pk, created_by_id=owner.pk,
                workplace_id=workspace.pk, name='Pulpit przed migracją', slug='migration-dashboard', visibility='selected')
            dashboard.shared_with.add(reader)
            old_rows = list(Dashboard.shared_with.through.objects.values('id', 'dashboard_id', 'user_id'))
            with connection.cursor() as cursor:
                cursor.execute("SELECT 'dashboard_dashboard_shared_with'::regclass::oid")
                table_oid = cursor.fetchone()[0]
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            apps = executor.loader.project_state(after).apps
            Membership = apps.get_model('dashboard', 'DashboardMembership')
            self.assertEqual(list(Membership.objects.values('id', 'dashboard_id', 'user_id')), old_rows)
            row = Membership.objects.get()
            self.assertEqual(row.role, 'observer')
            self.assertIsNone(row.created_at)
            # A process still running the old M2M model can safely add a reader.
            another = User.objects.create(username='old-writer-reader', email='old-writer-reader@example.test')
            dashboard.shared_with.add(another)
            self.assertEqual(Membership.objects.get(user_id=another.pk).role, 'observer')
            old_rows = list(Membership.objects.order_by('id').values('id', 'dashboard_id', 'user_id'))
            self.assertEqual(list(apps.get_model('dashboard', 'Dashboard').objects.get(pk=dashboard.pk)
                                  .shared_with.order_by('pk').values_list('pk', flat=True)), [reader.pk, another.pk])
            executor = MigrationExecutor(connection)
            executor.migrate(before)
            apps = executor.loader.project_state(before).apps
            self.assertEqual(list(apps.get_model('dashboard', 'Dashboard').shared_with.through.objects
                                  .order_by('id').values('id', 'dashboard_id', 'user_id')), old_rows)
            with connection.cursor() as cursor:
                cursor.execute("SELECT 'dashboard_dashboard_shared_with'::regclass::oid")
                self.assertEqual(cursor.fetchone()[0], table_oid)
        finally:
            MigrationExecutor(connection).migrate(leaves)
