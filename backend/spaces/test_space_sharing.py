"""Access drafts and immediate sharing preserve Workspace and task boundaries."""
import json

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
        self.assertTrue(response.json()['can_manage'])
        self.assertTrue(response.json()['can_change_visibility'])
        self.assertEqual(next(row for row in response.json()['members'] if row['id'] == 'owner')['role'], 'owner')
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

    def access_data(self, space=None, scoped=True):
        return self.client.get(self.api(scoped), {'url': self.url(space=space, scoped=scoped)}, follow=True).json()

    def save_access(self, members, *, space=None, scoped=True, visibility='private', revision=None):
        return self.client.post(self.api(scoped), {
            'action': 'save', 'visibility': visibility,
            'revision': revision if revision is not None else self.access_data(space, scoped)['revision'],
            'members': json.dumps(members),
        }, QUERY_STRING='url=' + self.url(space=space, scoped=scoped))

    def test_draft_save_applies_roles_additions_removals_together_for_both_urls(self):
        task = SpaceTask.objects.create(space=self.space, title='Prywatne zadanie', created_by=self.owner,
                                       visibility='private', private_owner=self.owner)
        SpaceTaskMembership.objects.create(task=task, user=self.member)
        for scoped in [True, False]:
            before = self.access_data(scoped=scoped)
            self.assertEqual(before['visibility'], 'private')
            self.assertTrue(before['can_change_visibility'])
            self.assertEqual(len(before['revision']), 64)
            # Reading the draft and candidates never changes existing grants.
            original = list(self.space.memberships.values_list('user_id', 'role'))
            endpoint = self.url('team/candidates/?draft=1&q=Ewa', scoped=scoped)
            candidate = self.client.get(self.api(scoped), {'url': endpoint}, follow=True).json()['results'][0]
            self.assertEqual((candidate['id'], candidate['user_id']), (self.member.pk, self.member.pk))
            self.assertEqual(list(self.space.memberships.values_list('user_id', 'role')), original)
            rows = [{'user_id': self.admin.pk, 'role': 'admin'},
                    {'user_id': self.observer.pk, 'role': 'member'},
                    {'user_id': self.candidate.pk, 'role': 'observer'}]
            response = self.save_access(rows, scoped=scoped, revision=before['revision'])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(dict(self.space.memberships.values_list('user_id', 'role')),
                             {self.admin.pk: 'admin', self.observer.pk: 'member', self.candidate.pk: 'observer'})
            self.assertFalse(task.memberships.filter(user=self.member).exists())
            self.assertTrue(visible_to(Space.objects.filter(pk=self.space.pk), self.candidate).exists())
            self.assertFalse(visible_to(Space.objects.filter(pk=self.space.pk), self.member).exists())
        # Readding access to the space does not restore a revoked private task grant.
        self.assertEqual(self.post({'action': 'share', 'email': self.member.email, 'role': 'member'}).status_code, 200)
        self.assertFalse(task.memberships.filter(user=self.member).exists())

    def test_draft_visibility_round_trip_clears_grants_and_keeps_private_task_grants(self):
        task = SpaceTask.objects.create(space=self.space, title='Prywatne zadanie', created_by=self.owner,
                                       visibility='private', private_owner=self.owner)
        SpaceTaskMembership.objects.create(task=task, user=self.member)
        initial_revision = self.access_data()['revision']
        response = self.save_access([], visibility='public', revision=initial_revision)
        self.assertEqual(response.status_code, 200)
        self.space.refresh_from_db()
        self.assertEqual(self.space.visibility, 'public')
        self.assertIsNone(self.space.private_owner_id)
        self.assertFalse(self.space.memberships.exists())
        self.assertTrue(task.memberships.filter(user=self.member).exists())
        self.assertTrue(visible_to(SpaceTask.objects.filter(pk=task.pk), self.member).exists())
        self.assertNotEqual(response.json()['revision'], initial_revision)
        self.assertEqual(self.save_access([], visibility='private').status_code, 200)
        self.space.refresh_from_db()
        self.assertEqual(self.space.private_owner_id, self.owner.pk)
        self.assertFalse(self.space.memberships.exists())
        self.assertFalse(visible_to(Space.objects.filter(pk=self.space.pk), self.member).exists())

    def test_public_manager_becomes_private_owner_and_can_share_with_workspace_owner(self):
        self.public.responsible_user = self.member
        self.public.save(update_fields=['responsible_user'])
        self.login(self.member)
        before = self.access_data(self.public)
        self.assertTrue(before['can_change_visibility'])
        self.assertTrue(before['can_manage'])
        self.assertEqual(before['private_owner']['user_id'], self.member.pk)
        self.assertEqual({choice['value'] for choice in before['share_form']['fields'][1]['choices']},
                         {'admin', 'member', 'observer'})
        endpoint = self.url('team/candidates/?draft=1&q=Anna', space=self.public)
        self.assertEqual(self.client.get(self.api(), {'url': endpoint}).json()['results'][0]['id'], self.owner.pk)
        endpoint = self.url('team/candidates/?draft=1&q=Ewa', space=self.public)
        self.assertEqual(self.client.get(self.api(), {'url': endpoint}).json()['results'], [])
        response = self.save_access([{'user_id': self.owner.pk, 'role': 'observer'}], space=self.public)
        self.assertEqual(response.status_code, 200)
        self.public.refresh_from_db()
        self.assertEqual(self.public.private_owner_id, self.member.pk)
        self.assertEqual(response.json()['members'][0]['user_id'], self.member.pk)
        self.assertEqual(self.public.memberships.get(user=self.owner).role, 'observer')
        self.assertTrue(response.json()['is_owner'])

    def test_privatization_keeps_private_task_grants_for_selected_people(self):
        task = SpaceTask.objects.create(space=self.public, title='Prywatne zadanie', created_by=self.owner,
                                       visibility='private', private_owner=self.owner)
        grant = SpaceTaskMembership.objects.create(task=task, user=self.member)
        excluded = SpaceTaskMembership.objects.create(task=task, user=self.candidate)
        # Legacy grants on a public space do not govern its current access.
        SpaceMembership.objects.create(space=self.public, user=self.member, role='observer')
        SpaceMembership.objects.create(space=self.public, user=self.candidate, role='admin')
        response = self.save_access([{'user_id': self.member.pk, 'role': 'member'}], space=self.public)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(task.memberships.filter(pk=grant.pk).exists())
        self.assertFalse(task.memberships.filter(pk=excluded.pk).exists())
        self.assertTrue(visible_to(SpaceTask.objects.filter(pk=task.pk), self.member).exists())
        self.assertEqual(dict(self.public.memberships.values_list('user_id', 'role')), {self.member.pk: 'member'})

    def test_stale_revision_detects_immediate_and_legacy_membership_changes(self):
        before = self.access_data()
        member = self.space.memberships.get(user=self.member)
        self.assertEqual(self.post({'action': 'role', 'member_id': member.pk, 'role': 'observer'}).status_code, 200)
        response = self.save_access([], revision=before['revision'])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.space.memberships.count(), 3)
        before = self.access_data()
        member.refresh_from_db()
        member.role = 'member'
        member.save(update_fields=['role'])
        self.assertEqual(self.save_access([], revision=before['revision']).status_code, 409)
        self.assertEqual(self.save_access([], revision='bad').status_code, 400)

    def test_invalid_drafts_never_partially_apply_visibility_or_members(self):
        before = self.access_data()
        original = dict(self.space.memberships.values_list('user_id', 'role'))
        candidate = {'user_id': self.candidate.pk, 'role': 'member'}
        invalid = [None, {}, [True], [candidate, candidate],
                   [candidate, {'user_id': self.owner.pk, 'role': 'member'}],
                   [candidate, {'user_id': self.outsider.pk, 'role': 'observer'}],
                   [{'user_id': self.candidate.pk, 'role': 'owner'}],
                   [{'user_id': str(self.candidate.pk), 'role': 'member'}],
                   [{'user_id': True, 'role': 'member'}],
                   [{'user_id': 2 ** 63, 'role': 'member'}],
                   [{'user_id': self.candidate.pk, 'role': []}],
                   [{'user_id': self.candidate.pk, 'role': 'member', 'id': 1}]]
        for rows in invalid:
            with self.subTest(rows=rows):
                self.assertEqual(self.save_access(rows, revision=before['revision']).status_code, 400)
                self.assertEqual(dict(self.space.memberships.values_list('user_id', 'role')), original)
                self.assertEqual(self.access_data()['revision'], before['revision'])
        self.assertEqual(self.save_access([candidate], visibility='public').status_code, 400)
        self.assertEqual(self.save_access([], visibility='workspace').status_code, 400)
        self.space.refresh_from_db()
        self.assertEqual(self.space.visibility, 'private')

    def test_admin_drafts_preserve_admins_and_cannot_change_visibility_or_promote(self):
        self.login(self.admin)
        before = self.access_data()
        self.assertFalse(before['can_change_visibility'])
        admin = {'user_id': self.admin.pk, 'role': 'admin'}
        for rows in [[], [{'user_id': self.admin.pk, 'role': 'member'}],
                     [admin, {'user_id': self.member.pk, 'role': 'admin'}]]:
            self.assertEqual(self.save_access(rows).status_code, 403)
        self.assertEqual(self.save_access([], visibility='public').status_code, 403)
        response = self.save_access([admin, {'user_id': self.candidate.pk, 'role': 'observer'}])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(dict(self.space.memberships.values_list('user_id', 'role')),
                         {self.admin.pk: 'admin', self.candidate.pk: 'observer'})

    def test_draft_protects_redundant_owner_and_inactive_admin_grants(self):
        redundant = SpaceMembership.objects.create(space=self.space, user=self.owner, role='admin')
        task = SpaceTask.objects.create(space=self.space, title='Prywatne zadanie', created_by=self.owner,
                                       visibility='private', private_owner=self.owner)
        SpaceTaskMembership.objects.create(task=task, user=self.owner)
        SpaceMembership.objects.create(space=self.space, user=self.candidate, role='admin')
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.candidate).update(is_active=False)
        self.login(self.admin)
        self.assertEqual(self.save_access([{'user_id': self.admin.pk, 'role': 'admin'}]).status_code, 200)
        self.assertTrue(self.space.memberships.filter(pk=redundant.pk).exists())
        self.assertTrue(self.space.memberships.filter(user=self.candidate, role='admin').exists())
        self.assertTrue(task.memberships.filter(user=self.owner).exists())

    def test_drafts_reject_inactive_recipients_and_readers_with_live_permissions(self):
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.candidate).update(is_active=False)
        self.assertEqual(self.save_access([{'user_id': self.candidate.pk, 'role': 'member'}]).status_code, 400)
        revision = self.access_data()['revision']
        for person in [self.member, self.observer]:
            self.login(person)
            self.assertEqual(self.save_access([], revision=revision).status_code, 403)
            endpoint = self.url('team/candidates/?draft=1&q=Anna', space=self.public)
            self.assertEqual(self.client.get(self.api(), {'url': endpoint}).status_code, 403)
        self.login(self.admin)
        self.space.memberships.filter(user=self.admin).delete()
        self.assertEqual(self.save_access([], revision=revision).status_code, 404)

    def test_publication_reports_lost_management_for_private_owner_without_public_role(self):
        self.space.private_owner = self.candidate
        self.space.save(update_fields=['private_owner'])
        self.login(self.candidate)
        response = self.save_access([], visibility='public')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['can_manage'])
        self.assertFalse(response.json()['can_change_visibility'])

    def test_guest_has_no_access_editor_capabilities_even_when_space_admin(self):
        membership = WorkplaceMembership.objects.get(workplace=self.workspace, user=self.admin)
        membership.role = 'guest'
        membership.save(update_fields=['role'])
        self.public.responsible_user = self.admin
        self.public.save(update_fields=['responsible_user'])
        self.login(self.admin)
        for space in [self.space, self.public]:
            response = self.client.get(self.api(), {'url': self.url('?view=settings', space=space)})
            self.assertEqual(response.status_code, 200)
            team = response.json()['data']['team']
            self.assertFalse(team['can_manage'])
            self.assertFalse(team['can_configure'])
            self.assertFalse(team['can_change_visibility'])
            self.assertNotIn('private_owner', team)
            endpoint = self.url('team/candidates/?draft=1&q=Anna', space=space)
            self.assertEqual(self.client.get(self.api(), {'url': endpoint}).status_code, 403)
            self.assertEqual(self.save_access([], space=space, revision=team['revision']).status_code, 403)

    def test_direct_urls_save_the_same_draft_and_preserve_csrf_checks(self):
        for scoped in [True, False]:
            response = self.client.post(self.url(scoped=scoped), {
                'action': 'save', 'visibility': 'private',
                'revision': self.access_data(scoped=scoped)['revision'],
                'members': json.dumps([{'user_id': self.candidate.pk, 'role': 'member'}]),
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['visibility'], 'private')
            self.assertEqual(list(self.space.memberships.values_list('user_id', flat=True)), [self.candidate.pk])
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        response = csrf.post(self.url(), {'action': 'save', 'visibility': 'public',
                                         'revision': self.access_data()['revision'], 'members': '[]'})
        self.assertEqual(response.status_code, 403)
        self.space.refresh_from_db()
        self.assertEqual(self.space.visibility, 'private')
