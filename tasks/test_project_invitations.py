from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.notification_service import change_notification_state, notification_page, notification_summary
from tasks.access import visible_to
from tasks.models import TaskProject, TaskProjectMembership, TaskProjectInvitation
from tasks.sharing import pending_project_invitations
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class ProjectInvitationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner, cls.admin, cls.member, cls.other = [User.objects.create_user(username=name, email=f'{name}@project.test')
            for name in ['owner', 'admin', 'member', 'other']]
        cls.workspace = create_workplace_for_user(cls.owner, 'Zaproszenia projektowe')
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        for person in [cls.admin, cls.member]:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=person)
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, visibility='private', private_owner=cls.owner, name='Projekt do zaproszenia')
        cls.admin_membership = TaskProjectMembership.objects.create(project=cls.project, user=cls.admin, role='admin')

    def setUp(self):
        self.login(self.owner)

    def login(self, person):
        self.client.force_login(person)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'tasks', suffix)

    def team(self, **params):
        return self.client.post(self.url(f'projects/{self.project.pk}/team/'), params)

    def invite(self, role='member'):
        self.assertEqual(self.team(action='invite', email=self.member.email.upper(), role=role).status_code, 200)
        return self.project.invitations.get(status='pending')

    def respond(self, invitation, action='accept'):
        return self.client.post(self.url(f'project-invitations/{invitation.pk}/respond/'), {'action': action})

    def test_invitation_is_recipient_only_and_does_not_grant_access_until_accepted(self):
        invitation = self.invite()
        self.assertFalse(visible_to(TaskProject.objects.all(), self.member).filter(pk=self.project.pk).exists())
        self.assertEqual(self.respond(invitation).status_code, 404)
        self.login(self.member)
        self.assertEqual(self.client.get(self.url(f'project-invitations/{invitation.pk}/respond/')).status_code, 405)
        self.assertEqual(self.client.get(self.url(), {'project_invitation': invitation.pk}).status_code, 200)
        self.assertFalse(self.project.shared_with.filter(pk=self.member.pk).exists())
        self.assertEqual(self.respond(invitation).status_code, 302)
        self.assertTrue(visible_to(TaskProject.objects.all(), self.member).filter(pk=self.project.pk).exists())
        self.assertEqual(self.respond(invitation).status_code, 404)
        self.assertEqual(self.project.memberships.get(user=self.member).role, 'member')

    def test_candidates_are_only_active_workspace_people_not_existing_or_pending_members(self):
        endpoint = self.url(f'projects/{self.project.pk}/team/candidates/')
        self.assertEqual(self.client.get(endpoint, {'q': 'm'}).json()['results'], [])
        response = self.client.get(endpoint, {'q': 'project.test'})
        self.assertEqual([row['email'] for row in response.json()['results']], [self.member.email])
        self.assertIn('no-store', response['Cache-Control'])
        self.invite()
        self.assertEqual(self.client.get(endpoint, {'q': 'member'}).json()['results'], [])
        self.login(self.member)
        self.assertEqual(self.client.get(endpoint, {'q': 'owner'}).status_code, 404)

    def test_invalid_recipients_duplicates_roles_and_stale_membership_fail(self):
        for email in [self.other.email, self.owner.email, self.admin.email, 'bad', 'missing@project.test']:
            self.assertEqual(self.team(action='invite', email=email, role='member').status_code, 400)
        self.assertEqual(self.team(action='invite', email=self.member.email, role='owner').status_code, 400)
        self.invite()
        self.assertEqual(self.team(action='invite', email=self.member.email, role='member').status_code, 400)
        self.project.invitations.all().delete()
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).delete()
        self.assertEqual(self.team(action='invite', email=self.member.email, role='member').status_code, 400)

    def test_expired_declined_and_cancelled_invitations_cannot_be_accepted(self):
        for state in ['expired', 'declined', 'revoked']:
            self.login(self.owner)
            invitation = self.invite()
            if state == 'expired':
                invitation.expires_at = timezone.now() - timedelta(seconds=1)
                invitation.save(update_fields=['expires_at'])
            elif state == 'revoked':
                self.assertEqual(self.team(action='cancel', invitation_id=invitation.pk).status_code, 200)
            self.login(self.member)
            if state == 'declined':
                self.assertEqual(self.respond(invitation, 'decline').status_code, 302)
            self.assertEqual(self.respond(invitation).status_code, 404)
            self.assertFalse(self.project.shared_with.filter(pk=self.member.pk).exists())
            self.project.invitations.all().delete()

    def test_project_admin_has_workspace_style_limits_and_owner_can_change_roles(self):
        self.login(self.admin)
        self.assertEqual(self.team(action='invite', email=self.member.email, role='admin').status_code, 400)
        invitation = self.invite()
        self.login(self.member)
        self.respond(invitation)
        membership = self.project.memberships.get(user=self.member)
        self.assertEqual(self.team(action='remove', member_id=self.admin_membership.pk).status_code, 403)
        self.login(self.admin)
        self.assertEqual(self.team(action='role', member_id=membership.pk, role='admin').status_code, 403)
        self.assertEqual(self.team(action='remove', member_id=self.admin_membership.pk).status_code, 403)
        self.login(self.owner)
        self.assertEqual(self.team(action='role', member_id=membership.pk, role='admin').status_code, 200)
        self.assertEqual(self.project.memberships.get(pk=membership.pk).role, 'admin')
        self.assertEqual(self.team(action='role', member_id=membership.pk, role='member').status_code, 200)
        self.login(self.admin)
        self.assertEqual(self.team(action='remove', member_id=membership.pk).status_code, 200)
        self.assertFalse(visible_to(TaskProject.objects.all(), self.member).filter(pk=self.project.pk).exists())

    def test_admin_cannot_cancel_admin_invitation_or_publish_project(self):
        invitation = self.invite('admin')
        self.login(self.admin)
        self.assertEqual(self.team(action='cancel', invitation_id=invitation.pk).status_code, 403)
        response = self.client.post(self.url(), {'action': 'edit_project', 'project_id': self.project.pk, 'name': self.project.name, 'visibility': 'public'})
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.visibility, 'private')

    def test_member_only_sees_member_table_and_cannot_invite(self):
        self.project.shared_with.add(self.member)
        self.login(self.member)
        payload = self.client.get(self.url(f'projects/{self.project.pk}/team/')).json()
        self.assertFalse(payload['can_manage'])
        self.assertEqual(payload['invitations'], '')
        self.assertEqual(payload['modals'].strip(), '')
        self.assertNotIn('data-project-team-action', payload['members'])
        self.assertEqual(self.team(action='invite', email=self.other.email, role='member').status_code, 403)

    def test_workspace_revocation_cancels_pending_and_rejoining_does_not_restore_it(self):
        invitation = self.invite()
        member = WorkplaceMembership.objects.get(workplace=self.workspace, user=self.member)
        member.is_active = False
        member.save(update_fields=['is_active'])
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'revoked')
        member.is_active = True
        member.save(update_fields=['is_active'])
        self.login(self.member)
        self.assertEqual(self.respond(invitation).status_code, 404)

    def test_publication_cancels_pending_and_prevents_new_invitations(self):
        invitation = self.invite()
        response = self.client.post(self.url(), {'action': 'edit_project', 'project_id': self.project.pk, 'name': self.project.name, 'visibility': 'public'})
        self.assertEqual(response.status_code, 302)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'revoked')
        self.assertEqual(self.team(action='invite', email=self.member.email, role='member').status_code, 403)
        self.assertFalse(self.project.memberships.exists())

    def test_notifications_share_invitation_count_filter_and_personal_read_state(self):
        invitation = self.invite()
        summary = notification_summary(self.member)
        self.assertEqual(summary['pending_invitation_count'], 1)
        self.assertEqual(notification_summary(self.admin)['pending_invitation_count'], 0)
        page = notification_page(self.member, {'view': 'invitations', 'workspace': str(self.workspace.pk)})
        item = page['dashboard_notifications'][0]
        self.assertEqual(item['key'], f'project:{invitation.pk}')
        self.assertIn('project_invitation=', item['url'])
        change_notification_state(self.member, {'action': 'read', 'key': item['key']})
        self.assertTrue(notification_page(self.member, {'view': 'all', 'workspace': ''})['dashboard_notifications'][0]['is_read'])
        self.assertEqual(notification_summary(self.member)['pending_invitation_count'], 1)
        self.assertFalse(self.project.shared_with.filter(pk=self.member.pk).exists())
        with self.assertRaises(ValueError):
            change_notification_state(self.member, {'action': 'archive', 'key': item['key']})
        self.login(self.member)
        self.respond(invitation)
        self.assertEqual(notification_summary(self.member)['pending_invitation_count'], 0)

    def test_invalid_foreign_ids_wrong_workspace_and_csrf_do_not_mutate(self):
        invitation = self.invite()
        for value in ['owner', '-1', '99999999999999999999999']:
            self.assertEqual(self.team(action='remove', member_id=value).status_code, 404)
        self.assertEqual(self.team(action='cancel', invitation_id=9999999).status_code, 404)
        wrong = scoped_workplace_app_path(self.other_workspace, 'tasks', f'projects/{self.project.pk}/team/')
        self.assertEqual(self.client.get(wrong).status_code, 404)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url(f'projects/{self.project.pk}/team/'), {'action': 'cancel', 'invitation_id': invitation.pk}).status_code, 403)
        self.assertEqual(self.client.get(self.url(), {'project_invitation': 'invalid'}).status_code, 302)


class ProjectMembershipMigrationTests(TransactionTestCase):
    def test_existing_grants_survive_migration_as_members(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        owner = get_user_model().objects.create_user(username='migration-project-owner', email='migration-owner@project.test')
        person = get_user_model().objects.create_user(username='migration-project-member', email='migration-member@project.test')
        executor.migrate([('tasks', '0055_project_sharing')])
        apps = executor.loader.project_state([('tasks', '0055_project_sharing')]).apps
        Project = apps.get_model('tasks', 'TaskProject')
        project = Project.objects.create(user_id=owner.pk, name='Existing grant', visibility='private', private_owner_id=owner.pk)
        project.shared_with.add(person.pk)
        MigrationExecutor(connection).migrate(latest)
        membership = TaskProjectMembership.objects.get(project_id=project.pk, user_id=person.pk)
        self.assertEqual(membership.role, 'member')
        self.assertTrue(TaskProject.objects.get(pk=project.pk).shared_with.filter(pk=person.pk).exists())
