from django.contrib.auth import get_user_model
from django.test import TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import Dashboard, DashboardGadget


class PulpitGroupRetirementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='group-retirement-owner', email='group-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='group-retirement-member', email='group-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Pulpity bez grup')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.dashboard = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Wydanie', visibility='workspace', revision=4)
        cls.private = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Prywatny')
        cls.foreign = Dashboard.objects.create(owner=cls.owner, workplace=cls.other, created_by=cls.owner, name='Obcy', visibility='workspace')
        cls.gadget = DashboardGadget.objects.create(dashboard=cls.dashboard, kind='progress')
        cls.dashboard.favorited_by.add(cls.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def prefixes(self):
        return ['/dashboards/', scoped_workplace_app_path(self.workspace, 'dashboards')]

    def test_retired_get_and_post_routes_cannot_change_dashboards(self):
        for viewer in [self.owner, self.member]:
            self.login(viewer)
            for prefix in self.prefixes():
                for suffix in ['groups/', 'groups/create/', 'groups/1/edit/', 'groups/1/delete/',
                               f'{self.dashboard.slug}/groups/', f'manage/{self.dashboard.slug}/groups/']:
                    for method in ['get', 'post']:
                        with self.subTest(viewer=viewer.pk, prefix=prefix, suffix=suffix, method=method):
                            response = getattr(self.client, method)(prefix + suffix, {'name': 'Grupa', 'groups': [1], 'dashboards': [self.dashboard.pk]})
                            self.assertEqual(response.status_code, 404)
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.name, self.dashboard.revision), ('Wydanie', 4))
        self.assertTrue(DashboardGadget.objects.filter(pk=self.gadget.pk).exists())
        self.assertTrue(self.dashboard.favorited_by.filter(pk=self.owner.pk).exists())

    def test_group_actions_are_absent_from_catalog_detail_editor_and_management(self):
        self.login(self.owner)
        for prefix in self.prefixes():
            for suffix in ['', f'{self.dashboard.slug}/', 'manage/', f'{self.dashboard.slug}/edit/', f'{self.dashboard.slug}/gadgets/']:
                with self.subTest(prefix=prefix, suffix=suffix):
                    response = self.client.get(prefix + suffix)
                    self.assertEqual(response.status_code, 200)
                    for text in ['Grupy pulpitów', 'Utwórz grupę pulpitów', 'Przypisz do grup', 'data-sidebar-pulpit-group=', '/groups/']:
                        self.assertNotContains(response, text)
                    self.assertContains(response, 'Zarządzaj pulpitami')
                    self.assertContains(response, 'Utwórz pulpit')

    def test_legacy_group_filter_is_ignored_without_widening_dashboard_access(self):
        self.login(self.member)
        for prefix in self.prefixes():
            response = self.client.get(prefix, {'tab': 'all', 'group': 999999})
            self.assertEqual(response.status_code, 200)
            self.assertEqual([item.pk for item in response.context['dashboards']], [self.dashboard.pk])
            self.assertTrue(all('group=' not in response.context[key] for key in ['previous_url', 'next_url']))
            self.assertNotContains(response, 'name="group"')
            self.assertNotContains(response, f'data-pulpit-directory-row="{self.private.pk}"')
            self.assertNotContains(response, self.foreign.name)
            self.assertContains(response, 'data-sidebar-picker-toggle="pulpits"')
