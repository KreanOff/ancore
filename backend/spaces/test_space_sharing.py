"""Sharing is immediate, Workspace-scoped and preserves private task boundaries."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .access import visible_to
from .models import Space, SpaceMembership, SpaceTask, SpaceTaskMembership
from .testing import make_space


class SpaceSharingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        for key, first, last in [('owner', 'Anna', 'Nowak'), ('admin', 'Piotr', 'Kowalski'),
                                 ('member', 'Ewa', 'Testowa'), ('observer', 'Jan', 'Testowy'),
                                 ('candidate', 'Maria', 'Nowa'), ('outsider', 'Obca', 'Osoba')]:
            setattr(cls, key, users.objects.create_user(username='sharing-' + key,
                email=key + '@example.test', first_name=first, last_name=last))
        cls.workspace = create_workplace_for_user(cls.owner, 'Udostępnianie QA')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        for key in ['admin', 'member', 'observer', 'candidate']:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=getattr(cls, key))
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Prywatna',
                               visibility='private', private_owner=cls.owner)
        for key, role in [('admin', 'admin'), ('member', 'member'), ('observer', 'observer')]:
            SpaceMembership.objects.create(space=cls.space, user=getattr(cls, key), role=role)
        cls.public = make_space(user=cls.owner, workplace=cls.workspace, name='Publiczna')

    def setUp(self):
        self.login(self.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix='team/', scoped=True, space=None):
        tail = (space or self.space).slug + '/' + suffix
        return scoped_workplace_app_path(self.workspace, 'space', tail) if scoped else '/space/' + tail

    def api(self, scoped=True, workspace=None):
        return scoped_workplace_app_path(workspace or self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'

    def post(self, values, scoped=True):
        return self.client.post(self.api(scoped), values, QUERY_STRING='url=' + self.url(scoped=scoped))

    def test_bootstrap_and_api_members_use_shared_contract(self):
        for scoped in [True, False]:
            response = self.client.get(self.api(scoped), {'url': self.url(scoped=scoped)}, follow=True)
            self.assertEqual(response.status_code, 200)
            team = response.json()
            owner = team['members'][0]
            self.assertEqual((owner['id'], owner['role_label'], owner['can_change']), ('owner', 'Właściciel', False))
            self.assertEqual(len(team['members']), 4)
            self.assertTrue(all('email' in row and 'avatar' in row for row in team['members']))
            page = self.client.get(self.api(scoped), {'url': self.url('?view=settings', scoped=scoped)}, follow=True).json()
            self.assertEqual(page['data']['team']['members'], team['members'])
            self.assertEqual(page['data']['team_url'], self.url())

    def test_candidates_search_only_active_unshared_workspace_people(self):
        endpoint = self.url('team/candidates/')
        self.assertEqual(self.client.get(self.api(), {'url': endpoint + '?q=M'}).json()['results'], [])
        result = self.client.get(self.api(), {'url': endpoint + '?q=Maria Nowa'}).json()['results']
        self.assertEqual([person['email'] for person in result], [self.candidate.email])
        for email in [self.owner.email, self.member.email, self.outsider.email]:
            self.assertEqual(self.client.get(self.api(), {'url': endpoint + '?q=' + email}).json()['results'], [])
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.candidate).update(is_active=False)
        self.assertEqual(self.client.get(self.api(), {'url': endpoint + '?q=Maria'}).json()['results'], [])

    def test_share_roles_remove_are_immediate_for_both_url_forms(self):
        for scoped in [True, False]:
            result = self.post({'action': 'share', 'email': self.candidate.email.upper(), 'role': 'observer'}, scoped)
            self.assertEqual(result.status_code, 200)
            member = self.space.memberships.get(user=self.candidate)
            self.assertTrue(visible_to(Space.objects.filter(pk=self.space.pk), self.candidate).exists())
            self.assertEqual(self.post({'action': 'role', 'member_id': member.pk, 'role': 'admin'}, scoped).status_code, 200)
            member.refresh_from_db()
            self.assertEqual(member.role, 'admin')
            self.assertEqual(self.post({'action': 'remove', 'member_id': member.pk}, scoped).status_code, 200)
            self.assertFalse(visible_to(Space.objects.filter(pk=self.space.pk), self.candidate).exists())

    def test_duplicate_and_outside_recipients_never_grant_access(self):
        for email in [self.owner.email, self.member.email, self.outsider.email, 'missing@example.test']:
            self.assertEqual(self.post({'action': 'share', 'email': email, 'role': 'member'}).status_code, 400)
        self.assertEqual(self.space.memberships.count(), 3)

    def test_space_admin_can_manage_members_but_cannot_promote_or_change_admins(self):
        self.login(self.admin)
        roles = self.client.get(self.api(), {'url': self.url()}).json()['share_form']['fields'][1]['choices']
        self.assertEqual({row['value'] for row in roles}, {'member', 'observer'})
        self.assertEqual(self.post({'action': 'share', 'email': self.candidate.email, 'role': 'admin'}).status_code, 400)
        member = self.space.memberships.get(user=self.member)
        self.assertEqual(self.post({'action': 'role', 'member_id': member.pk, 'role': 'observer'}).status_code, 200)
        self.assertEqual(self.post({'action': 'role', 'member_id': member.pk, 'role': 'admin'}).status_code, 403)
        admin = self.space.memberships.get(user=self.admin)
        for action in ['role', 'remove']:
            self.assertEqual(self.post({'action': action, 'member_id': admin.pk, 'role': 'member'}).status_code, 403)

    def test_readers_cannot_manage_and_private_space_is_hidden_from_others(self):
        for person in [self.member, self.observer]:
            self.login(person)
            self.assertFalse(self.client.get(self.api(), {'url': self.url()}).json()['can_manage'])
            self.assertEqual(self.post({'action': 'share', 'email': self.candidate.email, 'role': 'member'}).status_code, 403)
            self.assertEqual(self.client.get(self.api(), {'url': self.url('team/candidates/?q=Maria')}).status_code, 403)
        self.login(self.candidate)
        self.assertEqual(self.client.get(self.api(), {'url': self.url()}).status_code, 404)

    def test_public_space_lists_inherited_people_and_rejects_sharing(self):
        response = self.client.get(self.api(), {'url': self.url(space=self.public)})
        self.assertEqual(len(response.json()['members']), 5)
        self.assertFalse(response.json()['can_manage'])
        self.assertFalse(any(row['can_change'] for row in response.json()['members']))
        result = self.client.post(self.api(), {'action': 'share', 'email': self.candidate.email, 'role': 'member'}, QUERY_STRING='url=' + self.url(space=self.public))
        self.assertEqual(result.status_code, 403)

    def test_removal_cleans_task_grants_and_resharing_does_not_restore_them(self):
        task = SpaceTask.objects.create(space=self.space, title='Prywatne zadanie', created_by=self.owner,
                                        visibility='private', private_owner=self.owner)
        SpaceTaskMembership.objects.create(task=task, user=self.member)
        member = self.space.memberships.get(user=self.member)
        self.assertEqual(self.post({'action': 'remove', 'member_id': member.pk}).status_code, 200)
        self.assertFalse(task.memberships.filter(user=self.member).exists())
        self.assertEqual(self.post({'action': 'share', 'email': self.member.email, 'role': 'member'}).status_code, 200)
        self.assertFalse(visible_to(SpaceTask.objects.filter(pk=task.pk), self.member).exists())

    def test_foreign_ids_malformed_actions_csrf_and_revoked_workspace(self):
        other_space = make_space(user=self.owner, workplace=self.workspace, name='Druga prywatna', visibility='private', private_owner=self.owner)
        foreign = SpaceMembership.objects.create(space=other_space, user=self.candidate)
        for member_id in [foreign.pk, 'owner', 'bad']:
            self.assertEqual(self.post({'action': 'remove', 'member_id': member_id}).status_code, 404)
        self.assertEqual(self.post({'action': 'unknown'}).status_code, 400)
        self.assertEqual(self.client.get(self.api(workspace=self.other), {'url': self.url()}).status_code, 403)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        self.assertEqual(csrf.post(self.api(), {'action': 'share'}, QUERY_STRING='url=' + self.url()).status_code, 403)
        self.login(self.admin)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.admin).update(is_active=False)
        self.assertEqual(self.post({'action': 'share', 'email': self.candidate.email, 'role': 'member'}).status_code, 403)
