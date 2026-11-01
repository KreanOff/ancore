import json
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


class PulpitBulkSharingTests(PulpitSharingFixture, TestCase):
    def test_owner_changes_selected_roles_in_one_revision_on_both_routes(self):
        self.dashboard.memberships.create(user=self.recipient, role='member')
        for scoped, role in [(False, 'admin'), (True, 'observer')]:
            response = self.post({'action': 'role', 'member_ids': [self.reader.pk, self.recipient.pk,
                self.reader.pk], 'role': role}, scoped=scoped)
            self.assertEqual(response.status_code, 200, response.content)
            self.assertTrue(response.json()['ok'])
            self.assertEqual(set(self.dashboard.memberships.values_list('role', flat=True)), {role})
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 2)
        self.assertEqual(self.dashboard.created_by, self.creator)

    def test_removing_selected_people_updates_visibility_and_revokes_access(self):
        for scoped in [False, True]:
            self.dashboard.memberships.get_or_create(user=self.reader)
            self.dashboard.memberships.create(user=self.recipient, role='member')
            self.dashboard.visibility = 'selected'
            self.dashboard.save(update_fields=['visibility'])
            response = self.post({'action': 'remove', 'member_ids': [self.reader.pk, self.recipient.pk]}, scoped=scoped)
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json()['visibility'], 'private')
            self.assertEqual([member['id'] for member in response.json()['members']], ['owner'])
            self.assertFalse(self.dashboard.memberships.exists())
            self.login(self.recipient)
            self.assertEqual(self.get('', scoped).status_code, 404)
            self.login(self.creator)
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 2)

    def test_missing_foreign_malformed_and_owner_ids_reject_the_entire_selection(self):
        self.foreign.memberships.create(user=self.recipient, role='member')
        for scoped in [False, True]:
            for action in ['role', 'remove']:
                for invalid in [self.creator.pk, self.recipient.pk, self.outsider.pk, 'owner', 'invalid', '-1', '9' * 100]:
                    with self.subTest(scoped=scoped, action=action, invalid=invalid):
                        result = self.post({'action': action, 'member_ids': [self.reader.pk, invalid],
                            'role': 'admin'}, scoped=scoped)
                        self.assertEqual(result.status_code, 404)
                        self.assertEqual(self.dashboard.memberships.get(user=self.reader).role, 'observer')
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 0)
        self.assertEqual(self.foreign.memberships.get(user=self.recipient).role, 'member')

    def test_inactive_person_and_empty_selection_do_not_change_other_members(self):
        self.dashboard.memberships.create(user=self.recipient, role='member')
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.recipient).update(is_active=False)
        for action in ['role', 'remove']:
            self.assertEqual(self.post({'action': action, 'role': 'admin'}).status_code, 400)
            result = self.post({'action': action, 'member_ids': [self.reader.pk, self.recipient.pk], 'role': 'admin'})
            self.assertEqual(result.status_code, 404)
            self.assertEqual(self.dashboard.memberships.get(user=self.reader).role, 'observer')
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 0)

    def test_invalid_role_rejects_the_entire_selection(self):
        self.dashboard.memberships.create(user=self.recipient, role='member')
        for role in ['', 'owner', 'invalid']:
            result = self.post({'action': 'role', 'member_ids': [self.reader.pk, self.recipient.pk], 'role': role})
            self.assertEqual(result.status_code, 403)
            self.assertEqual(self.dashboard.memberships.get(user=self.reader).role, 'observer')
            self.assertEqual(self.dashboard.memberships.get(user=self.recipient).role, 'member')
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 0)

    def test_admin_cannot_include_an_admin_or_promote_any_selected_person(self):
        self.dashboard.memberships.create(user=self.recipient, role='admin')
        self.dashboard.memberships.create(user=self.owner, role='member')
        self.login(self.recipient)
        for scoped in [False, True]:
            for action in ['role', 'remove']:
                result = self.post({'action': action, 'member_ids': [self.reader.pk, self.recipient.pk],
                    'role': 'member'}, scoped=scoped)
                self.assertEqual(result.status_code, 403)
                self.assertEqual(self.dashboard.memberships.get(user=self.reader).role, 'observer')
            self.assertEqual(self.post({'action': 'role', 'member_ids': [self.reader.pk, self.owner.pk],
                'role': 'admin'}, scoped=scoped).status_code, 403)
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 0)
        self.assertEqual(self.dashboard.memberships.get(user=self.owner).role, 'member')

    def test_admin_can_change_and_remove_selected_lower_roles_on_both_routes(self):
        self.dashboard.memberships.create(user=self.recipient, role='admin')
        self.login(self.recipient)
        for scoped in [False, True]:
            self.dashboard.memberships.get_or_create(user=self.reader)
            self.dashboard.memberships.create(user=self.owner, role='member')
            values = {'member_ids': [self.reader.pk, self.owner.pk]}
            self.assertEqual(self.post({'action': 'role', 'role': 'member', **values}, scoped=scoped).status_code, 200)
            self.assertEqual(set(self.dashboard.memberships.exclude(user=self.recipient).values_list('role', flat=True)), {'member'})
            self.assertEqual(self.post({'action': 'remove', **values}, scoped=scoped).status_code, 200)
            self.assertEqual(list(self.dashboard.memberships.values_list('user_id', flat=True)), [self.recipient.pk])
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.visibility, self.dashboard.revision), ('selected', 4))

    def test_member_observer_and_foreign_workspace_cannot_use_toolbar_actions(self):
        self.dashboard.memberships.create(user=self.recipient, role='member')
        for person in [self.recipient, self.reader]:
            self.login(person)
            for scoped in [False, True]:
                for action in ['role', 'remove', 'visibility']:
                    result = self.post({'action': action, 'member_ids': [self.reader.pk], 'role': 'member',
                        'visibility': 'workspace'}, scoped=scoped)
                    self.assertEqual(result.status_code, 403)
        self.login(self.creator)
        self.assertEqual(self.post({'action': 'visibility', 'visibility': 'workspace'}, dashboard=self.foreign).status_code, 404)
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.visibility, self.dashboard.revision), ('selected', 0))

    def test_visibility_preserves_private_roles_and_public_switch_clears_them(self):
        for scoped in [False, True]:
            self.dashboard.visibility = 'selected'
            self.dashboard.save(update_fields=['visibility'])
            self.dashboard.memberships.update_or_create(user=self.reader, defaults={'role': 'admin'})
            response = self.post({'action': 'visibility', 'visibility': 'private'}, scoped=scoped)
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json()['visibility'], 'selected')
            self.assertTrue(response.json()['can_change_visibility'])
            self.assertEqual(self.dashboard.memberships.get(user=self.reader).role, 'admin')
            response = self.post({'action': 'visibility', 'visibility': 'workspace'}, scoped=scoped)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['visibility'], 'workspace')
            self.assertTrue(response.json()['can_change_visibility'])
            self.assertFalse(response.json()['can_manage'])
            self.assertFalse(self.dashboard.memberships.exists())
            self.assertEqual(self.post({'action': 'visibility', 'visibility': 'private'}, scoped=scoped).status_code, 200)
            self.dashboard.refresh_from_db()
            self.assertEqual(self.dashboard.visibility, 'private')
            self.assertFalse(self.dashboard.memberships.exists())
        self.assertEqual((self.dashboard.revision, self.dashboard.name, self.dashboard.description),
                         (6, 'Prywatny pulpit', 'Opis'))

    def test_only_creator_changes_visibility_and_invalid_values_do_not_modify_grants(self):
        self.dashboard.memberships.create(user=self.recipient, role='admin')
        self.login(self.recipient)
        self.assertFalse(self.get().json()['can_change_visibility'])
        for scoped in [False, True]:
            self.assertEqual(self.post({'action': 'visibility', 'visibility': 'workspace'}, scoped=scoped).status_code, 403)
        self.login(self.creator)
        for visibility in ['', 'selected', 'public', 'invalid']:
            self.assertEqual(self.post({'action': 'visibility', 'visibility': visibility}).status_code, 400)
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.visibility, self.dashboard.revision), ('selected', 0))
        self.assertEqual(self.dashboard.memberships.count(), 2)

    def test_workspace_inherited_people_cannot_be_changed_or_removed_in_bulk(self):
        for scoped in [False, True]:
            for action in ['role', 'remove']:
                result = self.post({'action': action, 'member_ids': [self.reader.pk, self.recipient.pk],
                    'role': 'member'}, scoped=scoped, dashboard=self.public)
                self.assertEqual(result.status_code, 403)
        self.public.refresh_from_db()
        self.assertEqual((self.public.visibility, self.public.revision), ('workspace', 0))

    def test_private_visibility_does_not_restore_stale_grants(self):
        self.dashboard.visibility = 'private'
        self.dashboard.save(update_fields=['visibility'])
        response = self.post({'action': 'visibility', 'visibility': 'private'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['visibility'], 'private')
        self.assertFalse(self.dashboard.memberships.exists())

    def test_native_team_endpoint_accepts_bulk_form_and_visibility_with_csrf_protection(self):
        self.dashboard.memberships.create(user=self.recipient, role='member')
        response = self.client.post(self.url(), {'action': 'role', 'member_ids': [self.reader.pk, self.recipient.pk], 'role': 'admin'})
        self.assertEqual(response.status_code, 200)
        csrf = Client(enforce_csrf_checks=True)
        self.login(self.creator, csrf)
        for values in [{'action': 'remove', 'member_ids': [self.reader.pk, self.recipient.pk]},
                       {'action': 'visibility', 'visibility': 'workspace'}]:
            self.assertEqual(csrf.post(self.url(), values).status_code, 403)
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.visibility, self.dashboard.revision), ('selected', 1))


class PulpitAccessDraftTests(PulpitSharingFixture, TestCase):
    def save_draft(self, rows, scoped=True, dashboard=None, **values):
        dashboard = dashboard or self.dashboard
        dashboard.refresh_from_db()
        return self.post({'action': 'save', 'revision': dashboard.revision,
            'visibility': 'private', 'members': json.dumps(rows), **values},
            scoped=scoped, dashboard=dashboard)

    def member(self, person, role='member'):
        return {'user_id': person.pk, 'role': role}

    def test_owner_saves_roles_additions_removals_and_visibility_together_on_both_routes(self):
        for scoped in [False, True]:
            self.dashboard.memberships.update_or_create(user=self.reader, defaults={'role': 'observer'})
            original = self.dashboard.memberships.get(user=self.reader)
            response = self.save_draft([self.member(self.reader, 'admin'), self.member(self.recipient)], scoped=scoped)
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json()['visibility'], 'selected')
            self.assertEqual(self.dashboard.memberships.get(user=self.reader).created_at, original.created_at)
            self.assertEqual(self.dashboard.memberships.get(user=self.reader).pk, original.pk)
            self.assertEqual(dict(self.dashboard.memberships.values_list('user_id', 'role')),
                             {self.reader.pk: 'admin', self.recipient.pk: 'member'})
            response = self.save_draft([self.member(self.recipient, 'observer')], scoped=scoped)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(dict(self.dashboard.memberships.values_list('user_id', 'role')), {self.recipient.pk: 'observer'})
            response = self.save_draft([], scoped=scoped)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['visibility'], 'private')
            self.assertFalse(self.dashboard.memberships.exists())
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.revision, self.dashboard.created_by, self.dashboard.owner,
            self.dashboard.name, self.dashboard.description), (6, self.creator, self.owner, 'Prywatny pulpit', 'Opis'))

    def test_public_save_clears_grants_and_private_save_does_not_restore_them(self):
        for scoped in [False, True]:
            self.dashboard.memberships.create(user=self.recipient, role='admin')
            response = self.save_draft([self.member(self.recipient, 'admin')], scoped=scoped, visibility='workspace')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['visibility'], 'workspace')
            self.assertFalse(self.dashboard.memberships.exists())
            response = self.save_draft([], scoped=scoped)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['visibility'], 'private')
            self.assertFalse(self.dashboard.memberships.exists())

    def test_private_draft_can_add_a_person_directly_from_public_visibility(self):
        for scoped in [False, True]:
            response = self.save_draft([self.member(self.recipient, 'admin')], scoped=scoped, dashboard=self.public)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['visibility'], 'selected')
            self.assertEqual(list(self.public.memberships.values_list('user_id', 'role')), [(self.recipient.pk, 'admin')])
            self.assertEqual(self.save_draft([], scoped=scoped, dashboard=self.public, visibility='workspace').status_code, 200)

    def test_revision_is_required_and_conflicts_do_not_change_existing_access(self):
        current = self.get().json()
        self.assertEqual(current['revision'], 0)
        self.assertEqual(self.post({'action': 'role', 'member_id': self.reader.pk, 'role': 'admin'}).status_code, 200)
        for scoped in [False, True]:
            response = self.save_draft([], scoped=scoped, revision=current['revision'], visibility='workspace')
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response['Cache-Control'], 'no-store')
            self.assertEqual(self.dashboard.memberships.get(user=self.reader).role, 'admin')
        self.assertEqual(self.post({'action': 'save', 'visibility': 'private', 'members': '[]'}).status_code, 400)
        for revision in ['', '-1', 'bad', '1.5']:
            self.assertEqual(self.save_draft([], revision=revision).status_code, 400)
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.revision, self.dashboard.visibility), (1, 'selected'))
        self.assertEqual(self.get().json()['revision'], 1)

    def test_malformed_lists_ids_and_roles_leave_all_access_unchanged(self):
        invalid_rows = [None, {}, '', [None], [self.member(self.reader), self.member(self.reader)],
            [{'user_id': str(self.reader.pk), 'role': 'member'}], [{'user_id': True, 'role': 'member'}],
            [{'user_id': -1, 'role': 'member'}], [{'user_id': 2 ** 63, 'role': 'member'}],
            [self.member(self.reader, 'owner')], [self.member(self.reader, {})],
            [{'user_id': self.reader.pk}], [{**self.member(self.reader), 'extra': 'unexpected'}],
            [self.member(self.recipient), self.member(self.creator)],
            [self.member(self.recipient), self.member(self.outsider)]]
        for rows in invalid_rows:
            with self.subTest(rows=rows):
                response = self.save_draft(rows, visibility='workspace')
                self.assertEqual(response.status_code, 400)
                self.assertEqual(list(self.dashboard.memberships.values_list('user_id', 'role')), [(self.reader.pk, 'observer')])
        self.assertEqual(self.save_draft([], members='not JSON').status_code, 400)
        for visibility in ['', 'selected', 'public', 'bad']:
            self.assertEqual(self.save_draft([], visibility=visibility).status_code, 400)
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.revision, self.dashboard.visibility), (0, 'selected'))

    def test_inactive_candidate_invalidates_entire_draft_even_if_other_role_is_valid(self):
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.recipient).update(is_active=False)
        response = self.save_draft([self.member(self.reader, 'admin'), self.member(self.recipient)])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.dashboard.memberships.get(user=self.reader).role, 'observer')
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 0)

    def test_admin_can_save_lower_roles_while_preserving_all_administrators(self):
        self.dashboard.memberships.create(user=self.recipient, role='admin')
        self.login(self.recipient)
        for scoped in [False, True]:
            response = self.save_draft([self.member(self.recipient, 'admin'), self.member(self.reader, 'member'),
                self.member(self.owner, 'observer')], scoped=scoped)
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(self.dashboard.memberships.get(user=self.reader).role, 'member')
            self.assertEqual(self.dashboard.memberships.get(user=self.owner).role, 'observer')
            response = self.save_draft([self.member(self.recipient, 'admin')], scoped=scoped)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(list(self.dashboard.memberships.values_list('user_id', 'role')), [(self.recipient.pk, 'admin')])
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 4)

    def test_admin_cannot_remove_demote_or_add_admins_or_change_visibility(self):
        self.dashboard.memberships.create(user=self.recipient, role='admin')
        self.dashboard.memberships.filter(user=self.reader).update(role='admin')
        self.dashboard.memberships.create(user=self.owner, role='member')
        self.login(self.recipient)
        valid = [self.member(self.recipient, 'admin'), self.member(self.reader, 'admin')]
        invalid = [[], [self.member(self.recipient, 'admin')], [self.member(self.reader, 'admin')],
                   [self.member(self.recipient, 'admin'), self.member(self.reader, 'observer')],
                   [*valid, self.member(self.owner, 'admin')]]
        for scoped in [False, True]:
            for rows in invalid:
                self.assertEqual(self.save_draft(rows, scoped=scoped).status_code, 403)
            self.assertEqual(self.save_draft(valid, scoped=scoped, visibility='workspace').status_code, 403)
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.revision, self.dashboard.visibility), (0, 'selected'))
        self.assertEqual(dict(self.dashboard.memberships.values_list('user_id', 'role')),
                         {self.recipient.pk: 'admin', self.reader.pk: 'admin', self.owner.pk: 'member'})

    def test_admin_preserves_inactive_protected_grants_outside_snapshot_owner_can_clear_them(self):
        self.dashboard.memberships.create(user=self.recipient, role='admin')
        self.dashboard.memberships.filter(user=self.reader).update(role='admin')
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.recipient).update(is_active=False)
        self.login(self.reader)
        self.assertEqual({member['user_id'] for member in self.get().json()['members']}, {self.creator.pk, self.reader.pk})
        response = self.save_draft([self.member(self.reader, 'admin')])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.dashboard.memberships.get(user=self.recipient).role, 'admin')
        self.assertEqual(self.save_draft([self.member(self.reader, 'admin'), self.member(self.recipient, 'admin')]).status_code, 400)
        self.login(self.creator)
        self.assertEqual(self.save_draft([]).status_code, 200)
        self.assertFalse(self.dashboard.memberships.exists())

    def test_member_observer_foreign_workspace_and_revoked_manager_cannot_save(self):
        self.dashboard.memberships.create(user=self.recipient, role='member')
        for person in [self.recipient, self.reader]:
            self.login(person)
            for scoped in [False, True]:
                self.assertEqual(self.save_draft([], scoped=scoped).status_code, 403)
        self.login(self.creator)
        self.assertEqual(self.save_draft([], dashboard=self.foreign).status_code, 404)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.creator).update(is_active=False)
        self.assertEqual(self.save_draft([]).status_code, 403)
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 0)

    def test_draft_candidates_include_existing_people_on_private_and_public_dashboards(self):
        for scoped in [False, True]:
            for dashboard in [self.dashboard, self.public]:
                for person in [self.reader, self.recipient]:
                    result = self.get('team/candidates/?draft=1&q=' + person.email, scoped=scoped, dashboard=dashboard)
                    self.assertEqual(result.status_code, 200)
                    self.assertEqual([(row['id'], row['user_id'], row['email']) for row in result.json()['results']],
                                     [(person.pk, person.pk, person.email)])
                self.assertEqual(self.get('team/candidates/?draft=1&q=' + self.creator.email,
                                         scoped=scoped, dashboard=dashboard).json()['results'], [])
        self.assertEqual(self.get('team/candidates/?q=' + self.reader.email).json()['results'], [])
        self.assertEqual(self.get('team/candidates/?q=' + self.reader.email, dashboard=self.public).status_code, 403)

    def test_draft_candidates_still_require_manage_and_active_workspace_people(self):
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.recipient).update(is_active=False)
        for person in [self.recipient, self.outsider]:
            self.assertEqual(self.get('team/candidates/?draft=1&q=' + person.email).json()['results'], [])
        self.login(self.reader)
        for dashboard in [self.dashboard, self.public]:
            self.assertEqual(self.get('team/candidates/?draft=1&q=Maria', dashboard=dashboard).status_code, 403)

    def test_native_draft_save_requires_csrf_and_serializes_current_revision(self):
        values = {'action': 'save', 'revision': 0, 'visibility': 'private',
                  'members': json.dumps([self.member(self.recipient)])}
        csrf = Client(enforce_csrf_checks=True)
        self.login(self.creator, csrf)
        self.assertEqual(csrf.post(self.url(), values).status_code, 403)
        response = self.client.post(self.url(), values)
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()['revision'], response.json()['visibility']), (1, 'selected'))
        self.assertEqual(list(self.dashboard.memberships.values_list('user_id', 'role')), [(self.recipient.pk, 'member')])
