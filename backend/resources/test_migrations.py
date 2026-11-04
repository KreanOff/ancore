from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ResourceLifecycleMigrationTests(TransactionTestCase):
    def test_existing_inventory_survives_without_fabricated_history(self):
        executor = MigrationExecutor(connection)
        current = executor.loader.graph.leaf_nodes()
        before = [target for target in current if target[0] != 'resources'] + [('resources', '0001_initial')]
        try:
            executor.migrate(before)
            apps = executor.loader.project_state(before).apps
            User = apps.get_model('accounts', 'User')
            Workplace = apps.get_model('workplaces', 'Workplace')
            Resource = apps.get_model('resources', 'Resource')
            user = User.objects.create(username='migration-resources', email='migration-resources@example.test')
            workplace = Workplace.objects.create(owner=user, name='Migracja zasobów', slug='migration-resources')
            resource = Resource.objects.create(owner=user, workplace=workplace, name='Istniejący laptop', status='in_use', assigned_to=user, inventory_number='OLD-01', notes='Zachowaj')
            executor = MigrationExecutor(connection)
            executor.migrate(current)
            apps = executor.loader.project_state(current).apps
            restored = apps.get_model('resources', 'Resource').objects.get(pk=resource.pk)
            self.assertEqual((restored.name, restored.notes, restored.inventory_number, restored.assigned_to_id, restored.status), ('Istniejący laptop', 'Zachowaj', 'OLD-01', user.pk, 'in_use'))
            self.assertIsNone(restored.return_due_on)
            self.assertFalse(apps.get_model('resources', 'ResourceActivity').objects.exists())
        finally:
            MigrationExecutor(connection).migrate(current)
