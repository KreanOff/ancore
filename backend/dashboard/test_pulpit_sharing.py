from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Dashboard


class PulpitSharingFixture:
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        for key, first, last in [('owner', 'Anna', 'Właściciel'), ('creator', 'Piotr', 'Twórca'),
                                 ('recipient', 'Maria', 'Nowa'), ('reader', 'Jan', 'Odbiorca'),
                                 ('outsider', 'Obca', 'Osoba')]:
            setattr(cls, key, users.objects.create_user(username='dashboard-sharing-' + key,
                email=key + '@example.test', first_name=first, last_name=last))
        cls.workspace = create_workplace_for_user(cls.owner, 'Udostępnianie Pulpitów')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        for key in ['creator', 'recipient', 'reader']:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=getattr(cls, key))
        cls.dashboard = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace,
            created_by=cls.creator, name='Prywatny pulpit', description='Opis', visibility='selected')
        cls.dashboard.shared_with.add(cls.reader)
        cls.public = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace,
            created_by=cls.creator, name='Publiczny pulpit', visibility='workspace')
        cls.foreign = Dashboard.objects.create(owner=cls.owner, workplace=cls.other,
            created_by=cls.owner, name='Obcy pulpit')

    def setUp(self):
        self.login(self.creator)

    def login(self, person, client=None):
        client = client or self.client
        client.force_login(person)
        session = client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix='team/', scoped=True, dashboard=None):
        tail = (dashboard or self.dashboard).slug + '/' + suffix
        return scoped_workplace_app_path(self.workspace, 'dashboards', tail) if scoped else '/dashboards/' + tail

    def api(self, scoped=True):
        return scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'

    def get(self, suffix='team/', scoped=True, dashboard=None):
        return self.client.get(self.api(scoped), {'url': self.url(suffix, scoped, dashboard)}, follow=True)

    def post(self, data, suffix='team/', scoped=True, dashboard=None):
        return self.client.post(self.api(scoped) + '?' + urlencode({'url': self.url(suffix, scoped, dashboard)}), data)

class PulpitSharingTests(PulpitSharingFixture, TestCase):
    def test_bootstrap_uses_shared_table_and_protects_creator(self):
        for scoped in [True, False]:
            response = self.get(scoped=scoped)
            self.assertEqual(response.status_code, 200, response.content[:500])
            team = response.json()
            self.assertEqual((team['can_manage'], team['is_owner'], team['visibility']), (True, True, 'selected'))
            creator, reader = team['members']
            self.assertEqual((creator['id'], creator['user_id'], creator['role_label'], creator['can_change']),
                             ('owner', self.creator.pk, 'Właściciel', False))
            self.assertEqual((reader['id'], reader['role'], reader['can_change']),
                             (self.reader.pk, 'observer', True))
            self.assertIsNotNone(reader['created_at'])
            self.assertTrue(all('email' in row and 'avatar' in row for row in team['members']))
            role = next(field for field in team['share_form']['fields'] if field['name'] == 'role')
            self.assertEqual((role['value'], [choice['value'] for choice in role['choices']]),
                             (['member'], ['admin', 'member', 'observer']))
            for section in ['access/', 'edit/']:
                data = self.get(section, scoped).json()['data']
                self.assertEqual(data['team'], team)
                self.assertEqual(data['team_url'], self.url())

    def test_candidates_only_include_active_unshared_workspace_people(self):
        self.assertEqual(self.get('team/candidates/?q=M').json()['results'], [])
        result = self.get('team/candidates/?q=Maria Nowa').json()['results']
        self.assertEqual([person['email'] for person in result], [self.recipient.email])
        for text in [self.creator.email, self.reader.email, self.outsider.email, 'q' * 255]:
            self.assertEqual(self.get('team/candidates/?q=' + text).json()['results'], [])
        for text in [self.recipient.username, self.recipient.email.upper()]:
            self.assertEqual(self.get('team/candidates/?q=' + text).json()['results'][0]['email'], self.recipient.email)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.recipient).update(is_active=False)
        self.assertEqual(self.get('team/candidates/?q=Maria').json()['results'], [])

    def test_share_and_revoke_take_effect_immediately_for_both_urls(self):
        for scoped in [True, False]:
            result = self.post({'action': 'share', 'email': self.recipient.email.upper(), 'role': 'observer'}, scoped=scoped)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result['Cache-Control'], 'no-store')
            self.assertEqual(len(result.json()['members']), 3)
            self.login(self.recipient)
            self.assertEqual(self.get('', scoped).status_code, 200)
            for suffix in ['edit/', 'access/', 'gadgets/']:
                self.assertEqual(self.get(suffix, scoped).status_code, 403)
            self.login(self.creator)
            self.assertEqual(self.post({'action': 'remove', 'member_id': self.recipient.pk}, scoped=scoped).status_code, 200)
            self.login(self.recipient)
            self.assertEqual(self.get('', scoped).status_code, 404)
            self.login(self.creator)
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.created_by, self.dashboard.revision), (self.creator, 4))

    def test_new_private_share_and_last_removal_change_visibility(self):
        self.dashboard.shared_with.clear()
        self.dashboard.visibility = 'private'
        self.dashboard.save()
        self.assertEqual(self.post({'action': 'share', 'email': self.recipient.email, 'role': 'observer'}).status_code, 200)
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.visibility, 'selected')
        self.assertEqual(self.post({'action': 'remove', 'member_id': self.recipient.pk}).status_code, 200)
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.visibility, 'private')
        self.assertEqual(len(self.get().json()['members']), 1)

    def test_duplicate_foreign_inactive_and_invalid_roles_do_not_grant_access(self):
        for email in [self.creator.email, self.reader.email, self.outsider.email, 'missing@example.test']:
            self.assertEqual(self.post({'action': 'share', 'email': email, 'role': 'observer'}).status_code, 400)
        for role in ['owner', 'invalid', '']:
            self.assertEqual(self.post({'action': 'share', 'email': self.recipient.email, 'role': role}).status_code, 400)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.recipient).update(is_active=False)
        self.assertEqual(self.post({'action': 'share', 'email': self.recipient.email, 'role': 'observer'}).status_code, 400)
        self.assertEqual(list(self.dashboard.shared_with.all()), [self.reader])
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 0)

    def test_workspace_owner_and_readers_cannot_manage_another_creators_dashboard(self):
        for person in [self.reader, self.owner]:
            self.login(person)
            if person == self.owner:
                self.assertEqual(self.get().status_code, 404)
            else:
                self.assertFalse(self.get().json()['can_manage'])
            self.assertIn(self.post({'action': 'remove', 'member_id': self.reader.pk}).status_code, [403, 404])
            self.assertIn(self.get('team/candidates/?q=Maria').status_code, [403, 404])

    def test_workspace_visibility_lists_inherited_people_and_blocks_individual_actions(self):
        data = self.get(dashboard=self.public).json()
        self.assertEqual(len(data['members']), 4)
        self.assertFalse(data['can_manage'])
        self.assertFalse(any(member['can_change'] for member in data['members']))
        for action in ['share', 'remove']:
            self.assertEqual(self.post({'action': action, 'email': self.recipient.email, 'role': 'observer',
                'member_id': self.reader.pk}, dashboard=self.public).status_code, 403)
        self.assertEqual(self.get('team/candidates/?q=Maria', dashboard=self.public).status_code, 403)

    def test_settings_visibility_preserves_grants_and_workspace_switch_clears_them(self):
        fields = self.get('edit/').json()['data']['form']['fields']
        visibility = next(field for field in fields if field['name'] == 'visibility')
        self.assertEqual(visibility['value'], ['private'])
        self.assertEqual([choice['value'] for choice in visibility['choices']], ['private', 'workspace'])
        for data in [{'name': 'Plan', 'description': ''}, {'name': 'Plan', 'visibility': 'private'}]:
            self.assertEqual(self.post(data, 'edit/').status_code, 200)
            self.dashboard.refresh_from_db()
            self.assertEqual(self.dashboard.visibility, 'selected')
            self.assertTrue(self.dashboard.shared_with.filter(pk=self.reader.pk).exists())
        self.assertEqual(self.post({'name': 'Plan', 'visibility': 'workspace'}, 'edit/').status_code, 200)
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.visibility, 'workspace')
        self.assertFalse(self.dashboard.shared_with.exists())
        self.assertEqual(self.post({'name': 'Plan', 'visibility': 'private'}, 'edit/').status_code, 200)
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.visibility, 'private')

    def test_stale_private_grants_are_not_listed_or_restored(self):
        self.dashboard.visibility = 'private'
        self.dashboard.save()
        self.assertEqual(len(self.get().json()['members']), 1)
        self.assertEqual(self.post({'action': 'share', 'email': self.recipient.email, 'role': 'observer'}).status_code, 200)
        self.assertEqual(list(self.dashboard.shared_with.all()), [self.recipient])

    def test_malformed_ids_foreign_workspace_csrf_methods_and_revoked_membership(self):
        for member_id in [self.creator.pk, self.recipient.pk, 'owner', 'bad', '-1', '9' * 100]:
            self.assertEqual(self.post({'action': 'remove', 'member_id': member_id}).status_code, 404)
        self.assertEqual(self.post({'action': 'unknown', 'member_id': self.reader.pk, 'role': 'admin'}).status_code, 400)
        self.assertEqual(self.get(dashboard=self.foreign).status_code, 404)
        self.assertEqual(self.client.get(scoped_workplace_app_path(self.other, 'api', 'v1/page/'), {'url': self.url()}).status_code, 403)
        self.assertEqual(self.client.put(self.url()).status_code, 405)
        csrf = Client(enforce_csrf_checks=True)
        self.login(self.creator, csrf)
        self.assertEqual(csrf.post(self.url(), {'action': 'share'}).status_code, 403)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.creator).update(is_active=False)
        self.assertEqual(self.post({'action': 'share', 'email': self.recipient.email, 'role': 'observer'}).status_code, 403)

    def test_inactive_shared_person_is_excluded_and_has_no_access(self):
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.reader).update(is_active=False)
        self.assertEqual(len(self.get().json()['members']), 1)
        self.login(self.reader)
        self.assertEqual(self.get('').status_code, 403)
