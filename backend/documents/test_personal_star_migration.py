"""Preserve former shared stars for their recorded owner on an existing database."""
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user


class PersonalDocumentStarMigrationTests(TransactionTestCase):
    def test_forward_preserves_only_owner_stars_and_reverse_uses_only_owner_preferences(self):
        users = get_user_model()
        owner = users.objects.create_user(username='migrate-stars-owner', email='migrate-stars-owner@example.test')
        member = users.objects.create_user(username='migrate-stars-member', email='migrate-stars-member@example.test')
        guest = users.objects.create_user(username='migrate-stars-guest', email='migrate-stars-guest@example.test')
        workspace = create_workplace_for_user(owner, 'Zachowane gwiazdki')
        WorkplaceMembership.objects.create(workplace=workspace, user=member)
        WorkplaceMembership.objects.create(workplace=workspace, user=guest, role='guest')
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [('documents', '0002_initial')]
        executor.migrate(previous)
        try:
            old = executor.loader.project_state(previous).apps
            library = old.get_model('documents', 'DocumentLibrary').objects.create(
                owner_id=owner.pk, workplace_id=workspace.pk, name='Zachowany dysk',
            )
            retired_folder = old.get_model('documents', 'WorkspaceDocumentFolder').objects.create(
                owner_id=owner.pk, workplace_id=workspace.pk, name='Dawny folder', is_starred=True,
            )
            cases = []
            for model_name in ('Document', 'Folder', 'WorkspaceDocument'):
                model = old.get_model('documents', model_name)
                extra = {'library_id': library.pk} if model_name in {'Document', 'Folder'} else {'content': '<p>Zachowana treść</p>'}
                label = 'name' if model_name == 'Folder' else 'title'
                for starred in (False, True):
                    item = model.objects.create(owner_id=owner.pk, workplace_id=workspace.pk,
                                                is_starred=starred, **{label: f'{model_name} {starred}', **extra})
                    before = {field.attname: getattr(item, field.attname) for field in model._meta.concrete_fields if field.name != 'is_starred'}
                    cases.append((model_name, item.pk, starred, before))

            MigrationExecutor(connection).migrate(latest)
            new = MigrationExecutor(connection).loader.project_state(latest).apps
            for model_name, pk, starred, before in cases:
                item = new.get_model('documents', model_name).objects.get(pk=pk)
                self.assertEqual(list(item.favorited_by.values_list('pk', flat=True)), [owner.pk] if starred else [])
                self.assertEqual({key: getattr(item, key) for key in before}, before)
                self.assertFalse(item.favorited_by.filter(pk__in=[member.pk, guest.pk]).exists())
                if not starred:
                    # Another person's new star must not become a shared flag on rollback.
                    item.favorited_by.add(member.pk, guest.pk)
            self.assertTrue(new.get_model('documents', 'WorkspaceDocumentFolder').objects.get(pk=retired_folder.pk).is_starred)

            MigrationExecutor(connection).migrate(previous)
            restored = MigrationExecutor(connection).loader.project_state(previous).apps
            for model_name, pk, starred, before in cases:
                item = restored.get_model('documents', model_name).objects.get(pk=pk)
                self.assertEqual(item.is_starred, starred)
                self.assertEqual({key: getattr(item, key) for key in before}, before)
        finally:
            MigrationExecutor(connection).migrate(latest)
