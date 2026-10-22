"""Settings entry points share a modal without broadening Space permissions."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from spaces.models import SpaceMembership
from spaces.testing import make_space
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class SpaceSettingsFrontendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='settings-owner', email='settings-owner@example.test')
        cls.admin = users.objects.create_user(username='settings-admin', email='settings-admin@example.test')
        cls.observer = users.objects.create_user(username='settings-observer', email='settings-observer@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Ustawienia')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        for person in (cls.admin, cls.observer):
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=person)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Prywatna', visibility='private', private_owner=cls.owner)
        cls.admin_membership = SpaceMembership.objects.create(space=cls.space, user=cls.admin, role='admin')
        SpaceMembership.objects.create(space=cls.space, user=cls.observer, role='observer')

    def page(self, suffix='', scoped=True, **kwargs):
        base = f'/space/{self.space.slug}/'
        if scoped:
            base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
        return self.client.get(api, {'url': base + suffix}, follow=True, **kwargs)

    def test_edit_avatar_and_members_open_matching_tab_in_same_space(self):
        self.client.force_login(self.owner)
        for scoped in (True, False):
            for suffix, tab in [('edit/', 'main'), ('avatar/', 'avatar'), ('members/', 'members')]:
                with self.subTest(scoped=scoped, suffix=suffix):
                    response = self.page(suffix, scoped=scoped)
                    self.assertEqual(response.status_code, 200)
                    data = response.json()['data']
                    self.assertEqual(data['space_settings']['tab'], tab)
                    self.assertTrue(data['space_settings']['space_url'].endswith(f'/space/{self.space.slug}/'))
                    self.assertIn('fields', data['form'])

    def test_validation_keeps_modal_and_tab_with_submitted_values(self):
        self.client.force_login(self.owner)
        base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        response = self.client.post(api + '?url=' + base + 'edit/', {'name': ' ', 'description': 'Zachowany szkic', 'visibility': 'private'})
        self.assertEqual(response.status_code, 400)
        data = response.json()['data']
        self.assertEqual(data['space_settings']['tab'], 'main')
        fields = {field['name']: field for field in data['form']['fields']}
        self.assertTrue(fields['name']['errors'])
        self.assertEqual(fields['description']['value'], 'Zachowany szkic')

    def test_member_actions_respect_private_owner_and_admin_roles(self):
        for person, removable in [(self.owner, True), (self.admin, False), (self.observer, False)]:
            self.client.force_login(person)
            response = self.page('?view=settings')
            self.assertEqual(response.status_code, 200)
            data = response.json()['data']
            member = next(row for row in data['members'] if row['id'] == self.admin_membership.pk)
            self.assertEqual(member['can_remove'], removable)
            self.assertEqual(data['can_manage'], person != self.observer)

    def test_observer_cannot_load_editable_settings(self):
        self.client.force_login(self.observer)
        for suffix in ('edit/', 'avatar/', 'members/', 'configuration/'):
            self.assertEqual(self.page(suffix).status_code, 403)

    def test_other_workspace_cannot_load_modal(self):
        self.client.force_login(self.owner)
        api = scoped_workplace_app_path(self.other, 'api', 'v1/page/')
        for suffix in ('edit/', 'avatar/', 'members/', 'configuration/'):
            target = scoped_workplace_app_path(self.other, 'space', self.space.slug + '/' + suffix)
            self.assertEqual(self.client.get(api, {'url': target}).status_code, 404)

    def test_edit_exposes_shared_avatar_control_without_changing_creation(self):
        self.client.force_login(self.owner)
        form = self.page('edit/').json()['data']['form']
        self.assertTrue(form['inline_avatar'])
        self.assertEqual(len(form['avatars']), 30)
        self.assertIn('preset_class', form['automatic_avatar'])
        self.assertIn('avatar_photo_crop', {field['name'] for field in form['fields']})
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        target = scoped_workplace_app_path(self.workspace, 'spaces', 'create/')
        create_form = self.client.get(api, {'url': target}).json()['data']['form']
        self.assertNotIn('inline_avatar', create_form)
        self.assertNotIn('avatar', {field['name'] for field in create_form['fields']})
