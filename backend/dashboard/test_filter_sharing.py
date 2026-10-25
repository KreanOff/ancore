from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase

from spaces.models import SpaceTask
from spaces.testing import make_space
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import SavedTaskFilter, SavedTaskFilterMembership


class FilterSharingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for key in ['owner', 'creator', 'admin', 'member', 'observer', 'recipient', 'outsider']:
            setattr(cls, key, get_user_model().objects.create_user(username='filter-share-' + key,
                email=key + '@example.test', first_name=key.capitalize(), last_name='Testowa'))
        cls.workspace = create_workplace_for_user(cls.owner, 'Filtry QA')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        for key in ['creator', 'admin', 'member', 'observer', 'recipient']:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=getattr(cls, key))
        cls.item = SavedTaskFilter.objects.create(owner=cls.owner, workplace=cls.workspace,
            created_by=cls.creator, name='Wspólny filtr', visibility='selected')
        for role in ['admin', 'member', 'observer']:
            cls.item.memberships.create(user=getattr(cls, role), role=role)
        cls.public = SavedTaskFilter.objects.create(owner=cls.owner, workplace=cls.workspace,
            created_by=cls.creator, name='Cały Workspace', visibility='workspace')
        cls.foreign = SavedTaskFilter.objects.create(owner=cls.owner, workplace=cls.other,
            created_by=cls.creator, name='Obcy filtr')
        cls.private_space = make_space(user=cls.owner, workplace=cls.workspace, name='Poufna',
            visibility='private', private_owner=cls.owner)
        cls.secret = SpaceTask.objects.create(space=cls.private_space, title='Poufne zadanie', assignee=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Publiczna', visibility='public')
        cls.task = SpaceTask.objects.create(space=cls.space, title='Dostępne zadanie')

    def setUp(self):
        self.login(self.creator)

    def login(self, user, client=None):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix='team/', scoped=True, item=None):
        tail = f'{(item or self.item).pk}/' + suffix
        return scoped_workplace_app_path(self.workspace, 'filters', tail) if scoped else '/filters/' + tail

    def api(self, scoped=True):
        return scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'

    def get(self, suffix='team/', scoped=True, item=None):
        return self.client.get(self.api(scoped), {'url': self.url(suffix, scoped, item)}, follow=True)

    def post(self, values, suffix='team/', scoped=True, item=None):
        return self.client.post(self.api(scoped) + '?' + urlencode({'url': self.url(suffix, scoped, item)}), values)

    def settings(self, **values):
        self.item.refresh_from_db()
        return {'name': self.item.name, 'description': '', 'query': self.item.query,
                'visibility': 'private', 'revision': self.item.revision, **values}

    def test_settings_metadata_has_shared_table_and_no_recipient_multiselect(self):
        for scoped in [False, True]:
            modal = self.get('edit/', scoped).json()['data']['modal']
            fields = {field['name']: field for field in modal['form']['fields']}
            self.assertNotIn('shared_with', fields)
            self.assertEqual([row['value'] for row in fields['visibility']['choices']], ['private', 'workspace'])
            team = modal['filter_team']['data']
            self.assertTrue(team['can_manage'])
            owner = team['members'][0]
            self.assertEqual((owner['id'], owner['role'], owner['can_change']), ('owner', 'owner', False))
            self.assertEqual({row['role'] for row in team['members']}, {'owner', 'admin', 'member', 'observer'})

    def test_share_role_change_remove_and_revision_in_both_routes(self):
        for scoped in [False, True]:
            old = self.item.revision
            result = self.post({'action': 'share', 'email': self.recipient.email, 'role': 'admin'}, scoped=scoped)
            self.assertEqual(result.status_code, 200, result.content)
            self.item.refresh_from_db()
            self.assertEqual((result.json()['previous_revision'], result.json()['revision']), (old, old + 1))
            self.assertEqual(self.item.memberships.get(user=self.recipient).role, 'admin')
            for role in ['member', 'observer']:
                self.assertEqual(self.post({'action': 'role', 'member_id': self.recipient.pk, 'role': role}, scoped=scoped).status_code, 200)
            self.assertEqual(self.post({'action': 'remove', 'member_id': self.recipient.pk}, scoped=scoped).status_code, 200)
            self.item.refresh_from_db()

    def test_admin_can_edit_settings_and_lower_roles_but_not_owner_admins_or_visibility(self):
        self.login(self.admin)
        for scoped in [False, True]:
            modal = self.get('edit/', scoped).json()['data']['modal']
            self.assertTrue(next(field for field in modal['form']['fields'] if field['name'] == 'visibility')['disabled'])
            self.assertEqual(self.post(self.settings(description='Od administratora', visibility='workspace'), 'edit/', scoped).status_code, 200)
            self.item.refresh_from_db()
            self.assertEqual((self.item.visibility, self.item.created_by), ('selected', self.creator))
            self.assertEqual(self.post({'action': 'role', 'member_id': self.member.pk, 'role': 'observer'}, scoped=scoped).status_code, 200)
            for actor in [self.admin, self.creator]:
                self.assertIn(self.post({'action': 'remove', 'member_id': actor.pk}, scoped=scoped).status_code, [403, 404])
            self.assertEqual(self.post({'action': 'share', 'email': self.recipient.email, 'role': 'admin'}, scoped=scoped).status_code, 400)
            self.assertEqual(self.post({}, 'delete/', scoped).status_code, 403)
            self.assertEqual(self.post({'visibility': 'selected', 'shared_with': [self.recipient.pk]}, 'edit/', scoped).status_code, 400)

    def test_member_only_saves_query_and_observer_only_reads(self):
        for role in ['member', 'observer']:
            self.login(getattr(self, role))
            for scoped in [False, True]:
                data = self.get('', scoped).json()['data']['saved_filter']
                self.assertEqual((data['editable'], data['query_editable'], data['deletable']), (False, role == 'member', False))
                self.assertEqual(self.get('edit/', scoped).status_code, 403)
                self.assertEqual(self.post(self.settings(), 'edit/', scoped).status_code, 403)
                self.assertEqual(self.post({}, 'delete/', scoped).status_code, 403)
                self.assertEqual(self.post({'action': 'share', 'email': self.recipient.email, 'role': 'member'}, scoped=scoped).status_code, 403)
                self.assertEqual(self.get('team/candidates/?q=Recipient', scoped).status_code, 403)
                self.item.refresh_from_db()
                result = self.post({'jql': 'priority = high', 'revision': self.item.revision}, 'save/', scoped)
                self.assertEqual(result.status_code, 200 if role == 'member' else 403)
                # Legacy/native writes enforce the same roles.
                self.assertEqual(self.client.post(self.url('edit/', scoped), self.settings()).status_code, 403)

    def test_workspace_is_read_only_and_visibility_toggle_does_not_resurrect_roles(self):
        self.login(self.admin)
        self.assertFalse(self.get(item=self.public).json()['can_manage'])
        self.assertEqual(self.post({'action': 'share', 'email': self.recipient.email, 'role': 'member'}, item=self.public).status_code, 403)
        self.login(self.creator)
        self.assertEqual(self.post(self.settings(visibility='workspace'), 'edit/').status_code, 200)
        self.assertFalse(self.item.memberships.exists())
        self.assertEqual(self.post(self.settings(visibility='private'), 'edit/').status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.visibility, 'private')

    def test_private_share_and_last_recipient_removal(self):
        self.item.shared_with.clear(); self.item.visibility = 'private'; self.item.save()
        self.assertEqual(self.post({'action': 'share', 'email': self.recipient.email, 'role': 'member'}).status_code, 200)
        self.item.refresh_from_db(); self.assertEqual(self.item.visibility, 'selected')
        self.assertEqual(self.post({'action': 'remove', 'member_id': self.recipient.pk}).status_code, 200)
        self.item.refresh_from_db(); self.assertEqual(self.item.visibility, 'private')

    def test_candidates_and_invalid_recipients_are_limited_to_workspace(self):
        for scoped in [False, True]:
            results = self.get('team/candidates/?q=Recipient', scoped).json()['results']
            self.assertEqual([row['email'] for row in results], [self.recipient.email])
            self.assertEqual(self.get('team/candidates/?q=Admin', scoped).json()['results'], [])
            self.assertEqual(self.get('team/candidates/?q=Outsider', scoped).json()['results'], [])
            for email in [self.outsider.email, self.creator.email, self.member.email]:
                self.assertEqual(self.post({'action': 'share', 'email': email, 'role': 'member'}, scoped=scoped).status_code, 400)
            self.assertEqual(self.get(item=self.foreign).status_code, 404)
            self.assertEqual(self.post({'action': 'role', 'member_id': 'invalid', 'role': 'member'}, scoped=scoped).status_code, 404)
            self.assertEqual(self.post({'action': 'invalid'}, scoped=scoped).status_code, 400)

    def test_grant_never_expands_tasks_and_revocation_is_immediate(self):
        self.login(self.member)
        ids = [row['id'] for row in self.get('').json()['data']['items']]
        self.assertNotIn(self.secret.pk, ids)
        self.assertEqual(len(ids), 1)
        self.login(self.creator)
        self.assertEqual(self.post({'action': 'remove', 'member_id': self.member.pk}).status_code, 200)
        self.login(self.member)
        for suffix in ['', 'team/', 'edit/']:
            self.assertEqual(self.get(suffix).status_code, 404)

    def test_disabled_workspace_member_loses_role_permanently(self):
        membership = WorkplaceMembership.objects.get(workplace=self.workspace, user=self.admin)
        membership.is_active = False; membership.save()
        self.assertFalse(self.item.memberships.filter(user=self.admin).exists())
        membership.is_active = True; membership.save()
        self.assertFalse(self.item.memberships.filter(user=self.admin).exists())
        WorkplaceMembership.objects.get(workplace=self.workspace, user=self.member).delete()
        self.assertFalse(self.item.memberships.filter(user=self.member).exists())

    def test_sharing_conflicts_with_stale_settings_and_normal_save_preserves_roles(self):
        values = self.settings(description='Stary szkic')
        self.assertEqual(self.post({'action': 'share', 'email': self.recipient.email, 'role': 'member'}).status_code, 200)
        self.assertEqual(self.post(values, 'edit/').status_code, 400)
        self.assertEqual(self.post(self.settings(description='Aktualny szkic'), 'edit/').status_code, 200)
        self.assertEqual(self.item.memberships.get(user=self.recipient).role, 'member')
        self.assertEqual(self.item.memberships.get(user=self.admin).role, 'admin')

    def test_csrf_methods_create_handoff_and_role_constraint(self):
        client = Client(enforce_csrf_checks=True); self.login(self.creator, client)
        self.assertEqual(client.post(self.url(), {'action': 'remove', 'member_id': self.member.pk}).status_code, 403)
        self.assertEqual(self.client.post(self.url('team/candidates/'), {}).status_code, 405)
        result = self.client.post(self.api() + '?' + urlencode({'url': '/filters/new/'}),
                                 {'name': 'Nowy filtr', 'query': '', 'visibility': 'private'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['filter_modal']['filter_settings'], 'edit')
        self.assertEqual(result.json()['filter_modal']['filter_team']['data']['members'][0]['user_id'], self.creator.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.item.memberships.create(user=self.recipient, role='owner')
