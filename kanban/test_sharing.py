"""Preserve compatibility of the historical Kanban schema."""
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from .models import KanbanProject, KanbanSection


class KanbanSharingMigrationTests(TransactionTestCase):
    def test_existing_spaces_boards_and_content_remain_public(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        owner = get_user_model().objects.create_user(username='kanban-migration', email='migration@kanban-sharing.test')
        executor.migrate([('spaces', None), ('kanban', '0038_directory_favorites')])
        executor = MigrationExecutor(connection)
        apps = executor.loader.project_state(list(executor.loader.applied_migrations)).apps
        project = apps.get_model('kanban', 'KanbanProject').objects.create(user_id=owner.pk, name='Istniejąca przestrzeń', code='OLD')
        board = apps.get_model('kanban', 'KanbanSection').objects.create(project=project, title='Istniejąca tablica', description='Treść')
        project.favorited_by.add(owner.pk)
        MigrationExecutor(connection).migrate(latest)
        restored = KanbanProject.objects.get(pk=project.pk)
        restored_board = KanbanSection.objects.get(pk=board.pk)
        self.assertEqual((restored.visibility, restored.private_owner_id), ('public', None))
        self.assertEqual((restored_board.visibility, restored_board.private_owner_id), ('public', None))
        self.assertEqual(restored_board.description, 'Treść')
        self.assertTrue(restored.favorited_by.filter(pk=owner.pk).exists())
        self.assertFalse(restored.memberships.exists())
