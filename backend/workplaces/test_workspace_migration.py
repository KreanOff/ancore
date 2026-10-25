"""Upgrade populated Workspaces without changing their data or identifiers."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class WorkspaceSystemMigrationTests(TransactionTestCase):
    def test_existing_invitations_receive_distinct_tokens_and_recipient_emails(self):
        executor = MigrationExecutor(connection)
        old_target = [('workplaces', '0001_initial')]
        latest = [('workplaces', '0004_workplaceinvitation_unique_pending_workspace_email')]
        restore_target = executor.loader.graph.leaf_nodes()
        executor.migrate(old_target)
        try:
            old = executor.loader.project_state(old_target).apps
            User = old.get_model('accounts', 'User')
            Workplace = old.get_model('workplaces', 'Workplace')
            Invitation = old.get_model('workplaces', 'WorkplaceInvitation')
            owner = User.objects.create(username='migration-owner', email='migration-owner@example.test')
            recipients = [User.objects.create(username=f'migration-{i}', email=f'migration-{i}@example.test') for i in range(2)]
            workplace = Workplace.objects.create(name='Istniejący Workspace', owner=owner)
            for user in recipients:
                Invitation.objects.create(workplace=workplace, recipient=user, invited_by=owner)
            identity = (workplace.pk, workplace.code, workplace.slug)
            executor = MigrationExecutor(connection); executor.migrate(latest)
            apps = executor.loader.project_state(latest).apps
            invitations = list(apps.get_model('workplaces', 'WorkplaceInvitation').objects.all())
            self.assertEqual(len({invitation.token for invitation in invitations}), 2)
            self.assertEqual({invitation.email for invitation in invitations}, {user.email for user in recipients})
            restored = apps.get_model('workplaces', 'Workplace').objects.get(pk=workplace.pk)
            self.assertEqual((restored.pk, restored.code, restored.slug), identity)
            self.assertEqual(restored.disabled_modules, [])
        finally:
            MigrationExecutor(connection).migrate(restore_target)
