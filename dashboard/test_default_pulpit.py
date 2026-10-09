import json

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase

from tasks.models import Task, TaskProject, TaskSection
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from workplaces.navigation import sidebar_favorite_is_active
from .models import Dashboard, DashboardGadget


class DefaultPulpitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='default-owner', email='default-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='default-member', email='default-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Pulpit domyślny')
        cls.other = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)

    def setUp(self):
        self.login(self.owner)

    def login(self, user, workspace=None, client=None):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = (workspace or self.workspace).pk
        session.save()

    def url(self, suffix='', workspace=None):
        return scoped_workplace_app_path(workspace or self.workspace, 'dashboards', suffix)

    def default(self):
        return self.client.get('/').context['dashboard']

    def test_home_and_plain_scoped_default_reuse_saved_dashboard(self):
        ordinary = Dashboard.objects.create(owner=self.owner, created_by=self.owner, workplace=self.workspace,
                                            name='Pulpit domyślny')
        dashboard = self.default()
        gadget = dashboard.gadgets.get()
        self.assertEqual((dashboard.owner, dashboard.created_by, dashboard.workplace),
                         (self.owner, self.owner, self.workspace))
        self.assertEqual((dashboard.visibility, gadget.kind), ('private', 'progress'))
        self.assertNotEqual(ordinary.pk, dashboard.pk)
        for path in ['/', '/dashboards/default/', self.url('default/')]:
            response = self.client.get(path, follow=True, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(response.context['dashboard'].pk, dashboard.pk)
            self.assertEqual(response['Cache-Control'], 'no-store')
            self.assertContains(response, 'Edytuj pulpit')
            self.assertNotContains(response, 'data-pulpit-drag')
            self.assertTrue(response.context['default_dashboard_is_current'])
            self.assertTrue(sidebar_favorite_is_active('dashboard', response.wsgi_request))
            self.assertFalse(sidebar_favorite_is_active('pulpits', response.wsgi_request))
            self.assertEqual(response.context['default_dashboard_url'], self.url('default/'))
        self.assertEqual(Dashboard.objects.filter(is_default=True).count(), 1)
        self.assertEqual(dashboard.gadgets.count(), 1)

    def test_default_is_personal_and_workspace_scoped(self):
        owner_dashboard = self.default()
        self.login(self.member)
        member_dashboard = self.default()
        self.assertEqual(member_dashboard.owner, self.owner)
        self.assertEqual(member_dashboard.created_by, self.member)
        self.assertNotEqual(member_dashboard.pk, owner_dashboard.pk)
        self.assertEqual(self.client.get(self.url(f'{owner_dashboard.pk}/gadgets/')).status_code, 404)
        self.login(self.owner, self.other)
        other_dashboard = self.default()
        self.assertEqual(other_dashboard.workplace, self.other)
        self.assertNotEqual(other_dashboard.pk, owner_dashboard.pk)
        self.assertEqual(self.client.post(self.url(f'{owner_dashboard.pk}/arrange/', self.other),
                                         '{}', content_type='application/json').status_code, 404)
        self.assertEqual(self.client.get(self.url('default/')).context['dashboard'].pk, owner_dashboard.pk)

    def test_common_editor_saves_layout_gadgets_filters_and_empty_state(self):
        dashboard = self.default()
        for prefix in ['/dashboards/', self.url()]:
            root = f'{prefix}{dashboard.pk}/'
            response = self.client.get(root + 'gadgets/')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['editing_gadgets'])
            self.assertEqual([entry['label'] for entry in response.context['pulpit_editor_navigation']],
                             ['Gadżety i układ', 'Dostępy', 'Ustawienia'])
            dashboard.refresh_from_db()
            response = self.client.post(root + 'gadgets/quick-add/', json.dumps({
                'kind': 'progress', 'revision': dashboard.revision,
            }), content_type='application/json')
            self.assertEqual(response.status_code, 200)
            added = DashboardGadget.objects.get(pk=response.json()['gadget_id'])
            self.assertEqual(self.client.post(root + f'gadgets/{added.pk}/edit/', {
                'kind': 'progress', 'title': 'Moje zadania', 'assignee': 'me',
            }).status_code, 302)
            for layout in Dashboard.Layout.values:
                dashboard.refresh_from_db()
                count = 1 if layout == 'single' else 3 if layout == 'three' else 2
                columns = [list(dashboard.gadgets.values_list('pk', flat=True))] + [[] for _ in range(count - 1)]
                response = self.client.post(root + 'arrange/', json.dumps({
                    'layout': layout, 'revision': dashboard.revision, 'columns': columns,
                }), content_type='application/json')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.default().layout, layout)
            for gadget in dashboard.gadgets.all():
                self.assertEqual(self.client.post(root + f'gadgets/{gadget.pk}/delete/').status_code, 302)
            for _ in range(2):
                response = self.client.get('/')
                self.assertContains(response, 'Ten pulpit jest pusty.')
                self.assertFalse(response.context['dashboard'].gadgets.exists())

    def test_settings_access_catalog_and_navigation_use_same_default(self):
        dashboard = self.default()
        self.assertEqual(self.client.post(self.url(f'{dashboard.pk}/edit/'), {
            'name': 'Mój start', 'description': 'Osobisty układ',
        }).url, self.url('default/'))
        self.assertEqual(self.client.post(self.url(f'{dashboard.pk}/access/'), {
            'visibility': 'selected', 'shared_with': [self.member.pk],
        }).url, self.url('default/'))
        self.assertContains(self.client.get('/'), 'Mój start')
        dashboard.favorited_by.add(self.owner)
        self.client.get(self.url(f'{dashboard.pk}/'))
        response = self.client.get(self.url('manage/'))
        self.assertIn(dashboard.pk, [row.pk for row in response.context['page']])
        self.assertNotIn(dashboard.pk, [row.pk for row in response.context['navigation_starred_dashboards']])
        self.assertNotIn(dashboard.pk, [row.pk for row in response.context['navigation_recent_dashboards']])
        self.login(self.member)
        shared = self.client.get(self.url(f'{dashboard.pk}/'))
        self.assertEqual(shared.status_code, 200)
        self.assertNotContains(shared, 'Edytuj pulpit')
        self.assertFalse(shared.context['default_dashboard_is_current'])
        self.assertEqual(self.client.get(self.url(f'{dashboard.pk}/gadgets/')).status_code, 403)
        self.assertNotEqual(self.default().pk, dashboard.pk)
        self.login(self.owner)
        self.client.post(self.url(f'{dashboard.pk}/access/'), {'visibility': 'private'})
        self.login(self.member)
        self.assertEqual(self.client.get(self.url(f'{dashboard.pk}/')).status_code, 404)

    def test_default_filters_data_for_viewer_without_granting_access(self):
        Task.objects.create(user=self.owner, workplace=self.workspace, title='Wspólne zadanie')
        project = TaskProject.objects.create(user=self.owner, workplace=self.workspace, name='Prywatne',
                                             visibility='private', private_owner=self.owner)
        section = TaskSection.objects.create(project=project, title='Grupa')
        Task.objects.create(user=self.owner, workplace=self.workspace, title='Ukryte', section=section,
                            assignee=self.member)
        self.login(self.member)
        response = self.client.get('/')
        self.assertEqual(response.context['columns'][0][0]['count'], 1)
        self.assertEqual(response.context['columns'][0][0]['closed_count'], 0)
        self.assertNotContains(response, 'Prywatne')
        self.assertNotContains(response, 'Ukryte')

    def test_default_cannot_be_deleted_and_unique_constraint_protects_initialization(self):
        dashboard = self.default()
        for prefix in ['/dashboards/', self.url()]:
            for management in ['', 'manage/']:
                response = self.client.post(f'{prefix}{management}{dashboard.pk}/delete/')
                self.assertEqual(response.status_code, 403)
        self.assertTrue(Dashboard.objects.filter(pk=dashboard.pk).exists())
        self.assertNotContains(self.client.get('/'), 'Usuń pulpit')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Dashboard.objects.create(owner=self.owner, created_by=self.owner, workplace=self.workspace,
                                     name='Drugi domyślny', is_default=True)

    def test_login_get_only_csrf_and_revoked_workspace_membership(self):
        dashboard = self.default()
        secure = Client(enforce_csrf_checks=True)
        self.login(self.owner, client=secure)
        self.assertEqual(secure.post(self.url(f'{dashboard.pk}/arrange/'), '{}',
                                     content_type='application/json').status_code, 403)
        self.assertEqual(self.client.post(self.url('default/')).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(self.url('default/')).status_code, 302)
        self.login(self.member)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).delete()
        self.assertEqual(self.client.get(self.url('default/')).url, '/workplaces/')
