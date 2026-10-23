import json

from django.db import IntegrityError, transaction
from django.test import TestCase

from workplaces.models import WorkplaceMembership
from .models import DashboardGadget
from .test_pulpit_sharing import PulpitSharingFixture


class PulpitRoleTests(PulpitSharingFixture, TestCase):
    """Exercise role grants against every class of dashboard write, not only UI flags."""

    def make_role(self, role):
        return self.dashboard.memberships.create(user=self.recipient, role=role)

    def post_json(self, suffix, values, scoped=True):
        from urllib.parse import urlencode
        return self.client.post(self.api(scoped) + '?' + urlencode({'url': self.url(suffix, scoped)}),
                                json.dumps(values), content_type='application/json')

    def test_owner_can_grant_and_change_all_three_roles_in_both_routes(self):
        for scoped in [False, True]:
            self.assertEqual(self.post({'action': 'share', 'email': self.recipient.email, 'role': 'admin'}, scoped=scoped).status_code, 200)
            for role in ['member', 'observer', 'admin']:
                result = self.post({'action': 'role', 'member_id': self.recipient.pk, 'role': role}, scoped=scoped)
                self.assertEqual(result.status_code, 200)
                row = next(row for row in result.json()['members'] if row['user_id'] == self.recipient.pk)
                self.assertEqual(row['role'], role)
                self.assertEqual(self.dashboard.memberships.get(user=self.recipient).role, role)
            self.assertEqual(self.post({'action': 'remove', 'member_id': self.recipient.pk}, scoped=scoped).status_code, 200)

    def test_admin_manages_settings_and_lower_roles_without_changing_ownership(self):
        self.make_role('admin')
        self.login(self.recipient)
        for scoped in [False, True]:
            fields = self.get('edit/', scoped).json()['data']['form']['fields']
            self.assertTrue(next(field for field in fields if field['name'] == 'visibility')['disabled'])
            result = self.post({'name': 'Zmieniony przez administratora', 'description': 'Opis administratora',
                                'visibility': 'workspace'}, 'edit/', scoped)
            self.assertEqual(result.status_code, 200)
            self.dashboard.refresh_from_db()
            self.assertEqual((self.dashboard.created_by, self.dashboard.owner, self.dashboard.visibility),
                             (self.creator, self.owner, 'selected'))
            self.assertEqual(self.dashboard.description, 'Opis administratora')
            self.assertEqual(self.post({'action': 'role', 'member_id': self.reader.pk, 'role': 'member'}, scoped=scoped).status_code, 200)
            self.assertEqual(self.post({'action': 'role', 'member_id': self.reader.pk, 'role': 'observer'}, scoped=scoped).status_code, 200)
            self.assertEqual(self.post({'action': 'role', 'member_id': self.reader.pk, 'role': 'admin'}, scoped=scoped).status_code, 403)
            self.assertEqual(self.post({'visibility': 'private'}, 'access/', scoped).status_code, 403)
            self.assertEqual(self.post({}, 'delete/', scoped).status_code, 403)

    def test_admin_cannot_promote_self_change_other_admins_or_remove_owner(self):
        self.make_role('admin')
        self.dashboard.memberships.filter(user=self.reader).update(role='admin')
        self.login(self.recipient)
        data = self.get().json()
        self.assertTrue(data['can_manage'])
        self.assertFalse(any(row['can_change'] for row in data['members']))
        role = next(field for field in data['share_form']['fields'] if field['name'] == 'role')
        self.assertEqual([choice['value'] for choice in role['choices']], ['member', 'observer'])
        for user in [self.recipient, self.reader]:
            for action in ['role', 'remove']:
                self.assertEqual(self.post({'action': action, 'member_id': user.pk, 'role': 'observer'}).status_code, 403)
        self.assertEqual(self.post({'action': 'remove', 'member_id': self.creator.pk}).status_code, 404)
        self.assertEqual(self.post({'action': 'share', 'email': self.owner.email, 'role': 'admin'}).status_code, 400)
        self.assertEqual(self.post({'action': 'share', 'email': self.owner.email, 'role': 'member'}).status_code, 200)
        self.assertEqual(self.post({'action': 'remove', 'member_id': self.owner.pk}).status_code, 200)

    def test_member_edits_gadgets_and_layout_but_not_settings_sharing_or_dashboard_delete(self):
        self.make_role('member')
        self.login(self.recipient)
        for scoped in [True, False]:
            data = self.get('', scoped).json()['data']['dashboard']
            self.assertEqual((data['editable'], data['manageable'], data['deletable']), (True, False, False))
            self.assertEqual(self.get('gadgets/', scoped).status_code, 200)
            result = self.post({'kind': 'progress', 'title': 'Od członka', 'assignee': 'all'}, 'gadgets/add/', scoped)
            self.assertEqual(result.status_code, 200)
            gadget = self.dashboard.gadgets.latest('pk')
            self.assertEqual(self.post({'kind': 'progress', 'title': 'Zmieniony', 'assignee': 'me'},
                                       f'gadgets/{gadget.pk}/edit/', scoped).status_code, 200)
            self.dashboard.refresh_from_db()
            columns = [[item.pk for item in self.dashboard.gadgets.order_by('pk')]]
            self.assertEqual(self.post_json('arrange/', {'layout': 'single', 'columns': columns,
                'revision': self.dashboard.revision}, scoped).status_code, 200)
            self.assertEqual(self.post({}, f'gadgets/{gadget.pk}/delete/', scoped).status_code, 200)
            for suffix in ['edit/', 'access/']:
                self.assertEqual(self.get(suffix, scoped).status_code, 403)
                self.assertEqual(self.post({'name': 'Nie wolno', 'visibility': 'workspace'}, suffix, scoped).status_code, 403)
            self.assertEqual(self.post({}, 'delete/', scoped).status_code, 403)
            self.assertEqual(self.post({'action': 'role', 'member_id': self.reader.pk, 'role': 'admin'}, scoped=scoped).status_code, 403)
            self.assertEqual(self.get('team/candidates/?q=Jan', scoped).status_code, 403)

    def test_observer_cannot_write_even_through_old_or_structured_endpoints(self):
        self.make_role('observer')
        gadget = DashboardGadget.objects.create(dashboard=self.dashboard, kind='progress')
        self.login(self.recipient)
        self.assertEqual(self.get('').status_code, 200)
        for suffix, values in [
            ('gadgets/add/', {'kind': 'progress', 'assignee': 'all'}),
            (f'gadgets/{gadget.pk}/edit/', {'kind': 'progress', 'assignee': 'all'}),
            (f'gadgets/{gadget.pk}/delete/', {}), ('edit/', {'name': 'Niedozwolona'}),
            ('access/', {'visibility': 'workspace'}), ('delete/', {}),
        ]:
            self.assertEqual(self.post(values, suffix).status_code, 403)
        for suffix, values in [('gadgets/quick-add/', {'kind': 'progress', 'revision': 0}),
                               ('arrange/', {'layout': 'single', 'columns': [[gadget.pk]], 'revision': 0})]:
            self.assertEqual(self.post_json(suffix, values).status_code, 403)
        self.assertTrue(self.dashboard.gadgets.filter(pk=gadget.pk).exists())

    def test_demotion_and_removal_revoke_current_write_access_immediately(self):
        self.make_role('member')
        self.login(self.recipient)
        self.assertEqual(self.get('gadgets/').status_code, 200)
        self.login(self.creator)
        self.assertEqual(self.post({'action': 'role', 'member_id': self.recipient.pk, 'role': 'observer'}).status_code, 200)
        self.login(self.recipient)
        self.assertEqual(self.post({'kind': 'progress', 'assignee': 'all'}, 'gadgets/add/').status_code, 403)
        self.login(self.creator)
        self.assertEqual(self.post({'action': 'remove', 'member_id': self.recipient.pk}).status_code, 200)
        self.login(self.recipient)
        self.assertEqual(self.get('').status_code, 404)

    def test_workspace_revocation_clears_roles_and_rejoining_does_not_restore_them(self):
        self.make_role('admin')
        membership = WorkplaceMembership.objects.get(workplace=self.workspace, user=self.recipient)
        membership.is_active = False
        membership.save()
        self.assertFalse(self.dashboard.memberships.filter(user=self.recipient).exists())
        membership.is_active = True
        membership.save()
        self.login(self.recipient)
        self.assertEqual(self.get('').status_code, 404)
        self.login(self.creator)
        self.assertEqual(self.post({'action': 'share', 'email': self.recipient.email, 'role': 'member'}).status_code, 200)
        membership.delete()
        self.assertFalse(self.dashboard.memberships.filter(user=self.recipient).exists())

    def test_legacy_m2m_and_bulk_form_preserve_existing_roles_and_add_observers(self):
        self.make_role('admin')
        self.assertEqual(self.post({'visibility': 'selected', 'shared_with': [self.reader.pk, self.recipient.pk]}, 'access/').status_code, 200)
        self.assertEqual(self.dashboard.memberships.get(user=self.recipient).role, 'admin')
        self.dashboard.shared_with.remove(self.recipient)
        self.dashboard.shared_with.add(self.recipient)
        self.assertEqual(self.dashboard.memberships.get(user=self.recipient).role, 'observer')
        self.assertEqual(self.post({'name': 'Plan', 'visibility': 'workspace'}, 'edit/').status_code, 200)
        self.assertFalse(self.dashboard.memberships.exists())

    def test_role_and_unique_pair_have_database_constraints(self):
        self.make_role('member')
        with transaction.atomic(), self.assertRaises(IntegrityError):
            self.dashboard.memberships.create(user=self.recipient, role='observer')
        with transaction.atomic(), self.assertRaises(IntegrityError):
            self.dashboard.memberships.filter(user=self.recipient).update(role='owner')

    def test_member_role_does_not_reveal_private_sources_or_offer_them_for_gadgets(self):
        from spaces.testing import make_space
        hidden = make_space(user=self.owner, workplace=self.workspace, name='Tajne źródło',
                            visibility='private', private_owner=self.owner)
        DashboardGadget.objects.create(dashboard=self.dashboard, kind='progress', space=hidden)
        self.make_role('member')
        self.login(self.recipient)
        data = self.get('').json()['data']
        self.assertTrue(data['columns'][0][0]['unavailable'])
        self.assertNotIn('Tajne źródło', str(data))
        form = self.get('gadgets/add/').json()['data']['modal']['form']
        sources = next(field for field in form['fields'] if field['name'] == 'space')['choices']
        self.assertNotIn(str(hidden.pk), [option['value'] for option in sources])
        self.assertEqual(self.post({'kind': 'progress', 'space': hidden.pk, 'assignee': 'all'}, 'gadgets/add/').status_code, 400)
