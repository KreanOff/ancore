from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.http import Http404
from django.test import Client, TestCase, TransactionTestCase

from dashboard.notification_service import change_notification_state, notification_page, notification_summary
from tasks.access import visible_to
from tasks.models import TaskProject, TaskProjectMembership, TaskProjectInvitation
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class ProjectTeamTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner, cls.admin, cls.member, cls.other = [User.objects.create_user(username=name, email=f'{name}@project.test')
            for name in ['owner', 'admin', 'member', 'other']]
        cls.workspace = create_workplace_for_user(cls.owner, 'Udostępnienia projektowe')
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        for person in [cls.admin, cls.member]:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=person)
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, visibility='private', private_owner=cls.owner, name='Projekt udostępniany')
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

    def share(self, role='member'):
        response = self.team(action='share', email=self.member.email.upper(), role=role)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.member.email, response.json()['members'])
        return self.project.memberships.get(user=self.member)

    def legacy_invitation(self):
        return TaskProjectInvitation.objects.create(project=self.project, recipient=self.member, invited_by=self.owner)

    def test_sharing_grants_immediate_access_without_invitation_or_notification(self):
        self.assertFalse(visible_to(TaskProject.objects.all(), self.member).filter(pk=self.project.pk).exists())
        self.share()
        self.assertFalse(self.project.invitations.exists())
        self.assertEqual(notification_summary(self.member)['pending_invitation_count'], 0)
        self.login(self.member)
        self.assertTrue(visible_to(TaskProject.objects.all(), self.member).filter(pk=self.project.pk).exists())
        for base in [self.url(), '/tasks/']:
            response = self.client.get(base, {'view': 'all-projects'}, follow=True)
            self.assertContains(response, self.project.name)
            self.assertNotContains(response, 'id="project-tab-invitations"')
        self.assertEqual(self.project.memberships.get(user=self.member).role, 'member')

    def test_candidates_exclude_existing_members_but_allow_legacy_pending_recipients(self):
        endpoint = self.url(f'projects/{self.project.pk}/team/candidates/')
        self.assertEqual(self.client.get(endpoint, {'q': 'm'}).json()['results'], [])
        invitation = self.legacy_invitation()
        response = self.client.get(endpoint, {'q': 'project.test'})
        self.assertEqual([row['email'] for row in response.json()['results']], [self.member.email])
        self.assertIn('no-store', response['Cache-Control'])
        self.share()
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'revoked')
        self.assertEqual(self.client.get(endpoint, {'q': 'member'}).json()['results'], [])
        self.login(self.member)
        self.assertEqual(self.client.get(endpoint, {'q': 'owner'}).status_code, 403)

    def test_invalid_recipients_duplicates_roles_and_stale_membership_fail(self):
        for email in [self.other.email, self.owner.email, self.admin.email, 'bad', 'missing@project.test']:
            self.assertEqual(self.team(action='share', email=email, role='member').status_code, 400)
        self.assertEqual(self.team(action='share', email=self.member.email, role='owner').status_code, 400)
        self.share()
        self.assertEqual(self.team(action='share', email=self.member.email, role='member').status_code, 400)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).delete()
        self.assertEqual(self.team(action='share', email=self.member.email, role='member').status_code, 400)

    def test_old_invitation_actions_and_response_urls_cannot_grant_access(self):
        invitation = self.legacy_invitation()
        for action in ['invite', 'cancel']:
            self.assertEqual(self.team(action=action, email=self.member.email, role='member', invitation_id=invitation.pk).status_code, 400)
        self.login(self.member)
        for base in [self.url(), '/tasks/']:
            self.assertEqual(self.client.post(base + f'project-invitations/{invitation.pk}/respond/', {'action': 'accept'}).status_code, 404)
        self.assertFalse(self.project.shared_with.filter(pk=self.member.pk).exists())
        self.assertEqual(notification_summary(self.member)['pending_invitation_count'], 0)
        self.assertEqual(notification_page(self.member, {'view': 'invitations', 'workspace': ''})['dashboard_notifications'], [])
        with self.assertRaises(Http404):
            change_notification_state(self.member, {'action': 'read', 'key': f'project:{invitation.pk}'})

    def test_project_admin_limits_and_owner_can_change_roles(self):
        self.login(self.admin)
        self.assertEqual(self.team(action='share', email=self.member.email, role='admin').status_code, 400)
        membership = self.share()
        self.login(self.member)
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

    def test_admin_cannot_remove_admin_or_publish_project(self):
        membership = self.share('admin')
        self.login(self.admin)
        self.assertEqual(self.team(action='remove', member_id=membership.pk).status_code, 403)
        response = self.client.post(self.url(), {'action': 'edit_project', 'project_id': self.project.pk, 'name': self.project.name, 'visibility': 'public'})
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.visibility, 'private')

    def test_member_only_sees_member_table_and_cannot_share(self):
        self.share()
        self.login(self.member)
        payload = self.client.get(self.url(f'projects/{self.project.pk}/team/')).json()
        self.assertFalse(payload['can_manage'])
        self.assertNotIn('invitations', payload)
        self.assertEqual(payload['modals'].strip(), '')
        self.assertNotIn('data-project-team-action', payload['members'])
        self.assertEqual(self.team(action='share', email=self.other.email, role='member').status_code, 403)

    def test_workspace_revocation_removes_access_and_rejoining_does_not_restore_it(self):
        self.share()
        invitation = self.legacy_invitation()
        member = WorkplaceMembership.objects.get(workplace=self.workspace, user=self.member)
        member.is_active = False
        member.save(update_fields=['is_active'])
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'revoked')
        member.is_active = True
        member.save(update_fields=['is_active'])
        self.assertFalse(visible_to(TaskProject.objects.all(), self.member).filter(pk=self.project.pk).exists())

    def test_publication_clears_members_and_legacy_pending_invitations(self):
        self.share()
        invitation = self.legacy_invitation()
        response = self.client.post(self.url(), {'action': 'edit_project', 'project_id': self.project.pk, 'name': self.project.name, 'visibility': 'public'})
        self.assertEqual(response.status_code, 302)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'revoked')
        self.assertEqual(self.team(action='share', email=self.member.email, role='member').status_code, 403)
        self.assertFalse(self.project.memberships.exists())

    def test_invalid_foreign_ids_wrong_workspace_and_csrf_do_not_mutate(self):
        for value in ['owner', '-1', '99999999999999999999999']:
            self.assertEqual(self.team(action='remove', member_id=value).status_code, 404)
        self.assertEqual(self.team(action='remove', member_id=9999999).status_code, 404)
        wrong = scoped_workplace_app_path(self.other_workspace, 'tasks', f'projects/{self.project.pk}/team/')
        self.assertEqual(self.client.get(wrong).status_code, 404)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url(f'projects/{self.project.pk}/team/'), {'action': 'share', 'email': self.member.email, 'role': 'member'}).status_code, 403)
        self.assertFalse(self.project.shared_with.filter(pk=self.member.pk).exists())


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
