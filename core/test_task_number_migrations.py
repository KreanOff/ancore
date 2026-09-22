from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class TaskNumberMigrationTests(TransactionTestCase):
    def test_existing_duplicates_are_repaired_without_changing_identity_or_relations(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [node for node in latest if node[0] not in {'tasks', 'kanban', 'dashboard'}] + [
            ('tasks', '0046_project_source_options'), ('kanban', '0033_retire_entity_icons'), ('dashboard', None),
        ]
        executor.migrate(previous)
        try:
            apps = executor.loader.project_state([node for node in previous if node[1] is not None]).apps
            user = apps.get_model(settings.AUTH_USER_MODEL).objects.create(username='migration-owner', email='migration@example.test')
            workplace_model = apps.get_model('workplaces', 'Workplace')
            first = workplace_model.objects.create(owner=user, name='First', slug='first')
            second = workplace_model.objects.create(owner=user, name='Second', slug='second')
            identities = {}
            for app, model_name in [('tasks', 'Task'), ('kanban', 'Kanban')]:
                model = apps.get_model(app, model_name)
                parent = model.objects.create(user=user, workplace=first, task_id=7, title='Parent')
                child = model.objects.create(user=user, workplace=first, task_id=7, title='Child', parent=parent)
                other = model.objects.create(user=user, workplace=second, task_id=7, title='Other')
                legacy = model.objects.create(user=user, task_id=7, title='Legacy')
                identities[(app, model_name)] = (parent.pk, child.pk, other.pk, legacy.pk)

            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            apps = executor.loader.project_state(latest).apps
            for (app, model_name), keys in identities.items():
                model = apps.get_model(app, model_name)
                records = [model.objects.get(pk=key) for key in keys]
                self.assertEqual([record.task_id for record in records], [1, 2, 1, 1])
                self.assertEqual([record.title for record in records], ['Parent', 'Child', 'Other', 'Legacy'])
                self.assertEqual(records[1].parent_id, records[0].pk)
        finally:
            MigrationExecutor(connection).migrate(latest)
