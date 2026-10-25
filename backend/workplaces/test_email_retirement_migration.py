"""Retire email invitations without changing existing access or business data."""
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from dashboard.models import NotificationState
from documents.models import WorkspaceDocument
from spaces.testing import make_task
from .models import WorkplaceInviteLink, WorkplaceMembership, create_workplace_for_user


class EmailInvitationRetirementMigrationTests(TransactionTestCase):
    def test_preserves_members_and_content_removes_receipts_and_revokes_domain_links(self):
        users = get_user_model()
        owner = users.objects.create_user(username='retire-owner', email='retire-owner@example.test')
        member = users.objects.create_user(username='retire-member', email='retire-member@example.test')
        workspace = create_workplace_for_user(owner, 'Zachowane dane')
        membership = WorkplaceMembership.objects.create(workplace=workspace, user=member, role='admin')
        task = make_task(user=owner, workplace=workspace, title='Zachowane zadanie')
        comment = task.activities.create(actor=owner, kind='comment', action='commented', message='Komentarz')
        receipt = NotificationState.objects.create(user=member, space_activity=comment, is_read=False)
        document = WorkspaceDocument.objects.create(owner=owner, workplace=workspace, title='Tekst', content='<p>Treść</p>')
        identity = (workspace.pk, workspace.code, workspace.slug)
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [('workplaces', '0004_workplaceinvitation_unique_pending_workspace_email'),
                    ('dashboard', '0006_saved_filter_membership_roles')]
        executor.migrate(previous)
        try:
            old = executor.loader.project_state(previous).apps
            invitation = old.get_model('workplaces', 'WorkplaceInvitation').objects.create(
                workplace_id=workspace.pk, email='not-a-member@example.test', invited_by_id=owner.pk,
            )
            email_receipt = old.get_model('dashboard', 'NotificationState').objects.create(
                user_id=owner.pk, invitation=invitation,
            )
            links = old.get_model('workplaces', 'WorkplaceInviteLink')
            unrestricted = links.objects.create(workplace_id=workspace.pk)
            restricted = links.objects.create(workplace_id=workspace.pk, email_domain='company.example')
            MigrationExecutor(connection).migrate(latest)

            workspace.refresh_from_db()
            membership.refresh_from_db()
            document.refresh_from_db()
            receipt.refresh_from_db()
            self.assertEqual((workspace.pk, workspace.code, workspace.slug), identity)
            self.assertEqual((membership.user_id, membership.role, membership.is_active), (member.pk, 'admin', True))
            self.assertEqual(document.content, '<p>Treść</p>')
            self.assertFalse(receipt.is_read)
            self.assertEqual(task.activities.get(pk=comment.pk).message, 'Komentarz')
            self.assertFalse(NotificationState.objects.filter(pk=email_receipt.pk).exists())
            self.assertEqual(WorkplaceMembership.objects.filter(workplace=workspace).count(), 2)
            self.assertIsNone(WorkplaceInviteLink.objects.get(pk=unrestricted.pk).revoked_at)
            self.assertIsNotNone(WorkplaceInviteLink.objects.get(pk=restricted.pk).revoked_at)
            self.assertNotIn('workplaces_workplaceinvitation', connection.introspection.table_names())
            with self.assertRaises(LookupError):
                apps.get_model('workplaces', 'WorkplaceInvitation')
        finally:
            MigrationExecutor(connection).migrate(latest)
