"""A task owner is protected even when an old redundant membership exists."""
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .access import visible_to
from .models import SpaceTask, SpaceTaskMembership
from .testing import make_space


class TaskOwnerMembershipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        for name in ('owner', 'admin', 'child_owner', 'recipient'):
            setattr(cls, name, users.objects.create_user(username='owner-grant-' + name,
                                                       email=name + '@example.test'))
        cls.workspace = create_workplace_for_user(cls.owner, 'Ochrona właściciela')
        for user in (cls.admin, cls.child_owner, cls.recipient):
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=user)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Publiczna')
        cls.task = SpaceTask.objects.create(space=cls.space, title='Prywatny rodzic', created_by=cls.owner,
                                           visibility='private', private_owner=cls.owner)
        SpaceTaskMembership.objects.create(task=cls.task, user=cls.admin, role='admin')
        SpaceTaskMembership.objects.create(task=cls.task, user=cls.child_owner)
        cls.child = SpaceTask.objects.create(space=cls.space, parent=cls.task, title='Ukryte podzadanie',
                                            created_by=cls.child_owner, visibility='private', private_owner=cls.child_owner)
        SpaceTaskMembership.objects.create(task=cls.child, user=cls.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def target(self, suffix, scoped):
        tail = f'{self.space.slug}/tasks/{self.task.work_item.key}/{suffix}'
        return scoped_workplace_app_path(self.workspace, 'space', tail) if scoped else '/space/' + tail

    def request_url(self, suffix, scoped, api):
        target = self.target(suffix, scoped)
        if not api:
            return target
        endpoint = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
        return endpoint + '?' + urlencode({'url': target})

    def routes(self):
        return ((scoped, api) for scoped in (False, True) for api in (False, True))

    def assert_child_grant(self):
        self.assertTrue(SpaceTaskMembership.objects.filter(task=self.child, user=self.owner).exists())
        self.assertTrue(visible_to(SpaceTask.objects.filter(pk=self.child.pk), self.owner).exists())
        self.assertFalse(visible_to(SpaceTask.objects.filter(pk=self.child.pk), self.admin).exists())

    def test_legacy_cannot_add_or_change_owner_membership(self):
        for actor in (self.admin, self.owner):
            self.login(actor)
            for scoped, api in self.routes():
                with self.subTest(actor=actor.pk, scoped=scoped, api=api):
                    url = self.request_url('members/', scoped, api)
                    data = {'visibility': 'private', 'person': self.owner.pk, 'role': 'observer'}
                    self.assertEqual(self.client.post(url, data).status_code, 400)
                    self.assertFalse(self.task.memberships.filter(user=self.owner).exists())
                    redundant = SpaceTaskMembership.objects.create(task=self.task, user=self.owner, role='member')
                    self.assertEqual(self.client.post(url, data).status_code, 400)
                    redundant.refresh_from_db()
                    self.assertEqual(redundant.role, 'member')
                    self.assert_child_grant()
                    redundant.delete()

    def test_legacy_cannot_remove_existing_owner_membership(self):
        redundant = SpaceTaskMembership.objects.create(task=self.task, user=self.owner, role='observer')
        for actor in (self.admin, self.owner):
            self.login(actor)
            for scoped, api in self.routes():
                with self.subTest(actor=actor.pk, scoped=scoped, api=api):
                    response = self.client.post(self.request_url('members/', scoped, api), {
                        'visibility': 'private', 'role': 'member', 'remove_member': redundant.pk,
                    })
                    self.assertEqual(response.status_code, 403)
                    self.assertTrue(self.task.memberships.filter(pk=redundant.pk).exists())
                    self.assert_child_grant()

    def test_team_cannot_share_change_or_remove_owner_membership(self):
        redundant = SpaceTaskMembership.objects.create(task=self.task, user=self.owner, role='member')
        for actor in (self.admin, self.owner):
            self.login(actor)
            for scoped, api in self.routes():
                with self.subTest(actor=actor.pk, scoped=scoped, api=api):
                    url = self.request_url('team/', scoped, api)
                    response = self.client.post(url, {'action': 'share', 'email': self.owner.email, 'role': 'member'})
                    self.assertEqual(response.status_code, 400)
                    for action in ('role', 'remove'):
                        response = self.client.post(url, {'action': action, 'member_id': redundant.pk, 'role': 'observer'})
                        self.assertEqual(response.status_code, 403)
                    redundant.refresh_from_db()
                    self.assertEqual(redundant.role, 'member')
                    self.assert_child_grant()

    def test_owner_has_one_protected_row_with_redundant_membership(self):
        SpaceTaskMembership.objects.create(task=self.task, user=self.owner, role='member')
        self.login(self.admin)
        for scoped in (False, True):
            response = self.client.get(self.request_url('team/', scoped, api=True))
            self.assertEqual(response.status_code, 200)
            rows = [row for row in response.json()['members'] if row['user_id'] == self.owner.pk]
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0]['id'], rows[0]['role_label'], rows[0]['can_change']), ('owner', 'Właściciel', False))

    def test_deleting_redundant_owner_membership_preserves_private_descendant_access(self):
        redundant = SpaceTaskMembership.objects.create(task=self.task, user=self.owner)
        redundant.delete()
        self.assert_child_grant()

    def test_privatizing_public_task_cannot_create_membership_for_new_owner(self):
        self.task.visibility, self.task.private_owner = 'public', None
        self.task.save()
        self.login(self.owner)
        for scoped, api in self.routes():
            with self.subTest(scoped=scoped, api=api):
                response = self.client.post(self.request_url('members/', scoped, api), {
                    'visibility': 'private', 'person': self.owner.pk, 'role': 'member',
                })
                self.assertEqual(response.status_code, 400)
                self.task.refresh_from_db()
                self.assertEqual(self.task.visibility, 'public')
                self.assertFalse(self.task.memberships.filter(user=self.owner).exists())

    def test_publication_cleans_redundant_record_without_revoking_child_grant(self):
        self.login(self.owner)
        for scoped, api in self.routes():
            with self.subTest(scoped=scoped, api=api):
                SpaceTaskMembership.objects.create(task=self.task, user=self.owner)
                response = self.client.post(self.request_url('members/', scoped, api), {
                    'visibility': 'public', 'role': 'member',
                })
                self.assertEqual(response.status_code, 200 if api else 302)
                self.task.refresh_from_db()
                self.assertEqual(self.task.visibility, 'public')
                self.assertFalse(self.task.memberships.exists())
                self.assertTrue(visible_to(SpaceTask.objects.filter(pk=self.child.pk), self.owner).exists())
                self.task.visibility, self.task.private_owner = 'private', self.owner
                self.task.save()

    def test_admin_still_manages_regular_members_in_both_endpoints(self):
        self.login(self.admin)
        for scoped, api in self.routes():
            with self.subTest(scoped=scoped, api=api):
                legacy = self.request_url('members/', scoped, api)
                team = self.request_url('team/', scoped, api)
                response = self.client.post(legacy, {'visibility': 'private', 'person': self.recipient.pk, 'role': 'member'})
                self.assertEqual(response.status_code, 200 if api else 302)
                member = self.task.memberships.get(user=self.recipient)
                response = self.client.post(team, {'action': 'role', 'member_id': member.pk, 'role': 'observer'})
                self.assertEqual(response.status_code, 200)
                member.refresh_from_db()
                self.assertEqual(member.role, 'observer')
                self.assertEqual(self.client.post(team, {'action': 'remove', 'member_id': member.pk}).status_code, 200)
                self.assertFalse(self.task.memberships.filter(user=self.recipient).exists())
                response = self.client.post(team, {'action': 'share', 'email': self.recipient.email, 'role': 'member'})
                self.assertEqual(response.status_code, 200)
                member = self.task.memberships.get(user=self.recipient)
                response = self.client.post(legacy, {'visibility': 'private', 'role': 'member', 'remove_member': member.pk})
                self.assertEqual(response.status_code, 200 if api else 302)
                self.assertFalse(self.task.memberships.filter(user=self.recipient).exists())
