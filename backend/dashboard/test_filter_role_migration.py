from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class FilterRoleMigrationTests(TransactionTestCase):
    def test_existing_table_relation_ids_and_recipients_survive_forward_and_reverse(self):
        before = [('dashboard', '0005_dashboard_membership_roles')]
        after = [('dashboard', '0006_saved_filter_membership_roles')]
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(before)
            # Other apps retain newer columns; historical fixtures must match the full applied schema.
            loader = MigrationExecutor(connection).loader
            apps = loader.project_state(list(loader.applied_migrations)).apps
            User = apps.get_model('accounts', 'User')
            Workplace = apps.get_model('workplaces', 'Workplace')
            SavedTaskFilter = apps.get_model('dashboard', 'SavedTaskFilter')
            owner = User.objects.create(username='role-migration-owner', email='owner-role-migration@example.test')
            reader = User.objects.create(username='role-migration-reader', email='reader-role-migration@example.test')
            workspace = Workplace.objects.create(owner_id=owner.pk, name='Migracja ról',
                                                 code='w_role_migration', slug='w_role_migration')
            saved_filter = SavedTaskFilter.objects.create(owner_id=owner.pk, created_by_id=owner.pk,
                workplace_id=workspace.pk, name='Filtr przed migracją', visibility='selected')
            saved_filter.shared_with.add(reader)
            old_rows = list(SavedTaskFilter.shared_with.through.objects.values('id', 'savedtaskfilter_id', 'user_id'))
            with connection.cursor() as cursor:
                cursor.execute("SELECT 'dashboard_savedtaskfilter_shared_with'::regclass::oid")
                table_oid = cursor.fetchone()[0]
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            loader = MigrationExecutor(connection).loader
            apps = loader.project_state(list(loader.applied_migrations)).apps
            Membership = apps.get_model('dashboard', 'SavedTaskFilterMembership')
            self.assertEqual(list(Membership.objects.values('id', 'savedtaskfilter_id', 'user_id')), old_rows)
            row = Membership.objects.get()
            self.assertEqual(row.role, 'observer')
            self.assertIsNone(row.created_at)
            # A process still running the old M2M model can safely add a reader.
            another = User.objects.create(username='old-writer-reader', email='old-writer-reader@example.test')
            saved_filter.shared_with.add(another)
            self.assertEqual(Membership.objects.get(user_id=another.pk).role, 'observer')
            old_rows = list(Membership.objects.order_by('id').values('id', 'savedtaskfilter_id', 'user_id'))
            self.assertEqual(list(apps.get_model('dashboard', 'SavedTaskFilter').objects.get(pk=saved_filter.pk)
                                  .shared_with.order_by('pk').values_list('pk', flat=True)), [reader.pk, another.pk])
            executor = MigrationExecutor(connection)
            executor.migrate(before)
            loader = MigrationExecutor(connection).loader
            apps = loader.project_state(list(loader.applied_migrations)).apps
            self.assertEqual(list(apps.get_model('dashboard', 'SavedTaskFilter').shared_with.through.objects
                                  .order_by('id').values('id', 'savedtaskfilter_id', 'user_id')), old_rows)
            with connection.cursor() as cursor:
                cursor.execute("SELECT 'dashboard_savedtaskfilter_shared_with'::regclass::oid")
                self.assertEqual(cursor.fetchone()[0], table_oid)
        finally:
            MigrationExecutor(connection).migrate(leaves)
