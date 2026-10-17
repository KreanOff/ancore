"""Preserve historical group grants and content during migration."""

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from tasks.models import TaskSection


class SectionSharingMigrationTests(TransactionTestCase):
    def test_existing_group_keeps_content_and_inherited_access(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        owner = get_user_model().objects.create_user(username='group-migration', email='migration@groups.test')
        executor.migrate([('tasks', '0057_project_observer')])
        apps = executor.loader.project_state([('tasks', '0057_project_observer')]).apps
        project = apps.get_model('tasks', 'TaskProject').objects.create(user_id=owner.pk, name='Istniejący projekt')
        section = apps.get_model('tasks', 'TaskSection').objects.create(project=project, title='Istniejąca grupa', code='OLD', description='Treść')
        MigrationExecutor(connection).migrate(latest)
        restored = TaskSection.objects.get(pk=section.pk)
        self.assertEqual((restored.visibility, restored.private_owner_id), ('public', None))
        self.assertEqual((restored.title, restored.code, restored.description), ('Istniejąca grupa', 'OLD', 'Treść'))
        self.assertFalse(restored.memberships.exists())
        self.assertFalse(restored.invitations.exists())
