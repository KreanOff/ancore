from datetime import date
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from spaces.models import SpaceTask
from spaces.testing import make_space
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


@override_settings(TIME_ZONE='Europe/Warsaw')
class TodaySidebarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='sidebar-owner', email='sidebar-owner@example.test')
        cls.member = users.objects.create_user(username='sidebar-member', email='sidebar-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Panel dnia')
        cls.other = create_workplace_for_user(cls.owner, 'Inny panel')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Praca')
        cls.today = date(2026, 11, 12)

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()
        self.today_patch = patch('planner.sidebar.timezone.localdate', return_value=self.today)
        self.today_patch.start()
        self.addCleanup(self.today_patch.stop)

    def url(self, app='calendar', suffix='sidebar/', workspace=None):
        return scoped_workplace_app_path(workspace or self.workspace, app, suffix)

    def task(self, **values):
        return SpaceTask.objects.create(**{
            'space': self.space, 'created_by': self.owner, 'title': 'Dzisiejsze zadanie',
            **values,
        })

    def api(self, target=None, *, client=None):
        return (client or self.client).get(self.url('api', 'v1/page/'), {'url': target or self.url()})

    def test_endpoint_returns_only_current_date_and_timezone(self):
        response = self.api()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response.json(), {
            'status': 'success', 'today': self.today.isoformat(), 'time_zone': 'Europe/Warsaw',
        })

    def test_normal_scoped_and_api_routes_keep_workspace_and_revoked_access(self):
        for url in (reverse('planner:sidebar'), self.url()):
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['today'], self.today.isoformat())
        self.assertEqual(self.api(self.url(workspace=self.other)).status_code, 403)
        self.membership.delete()
        self.assertEqual(self.api().status_code, 403)

    def test_endpoint_requires_session_is_read_only_and_handles_disabled_modules(self):
        self.assertEqual(self.api(client=Client()).status_code, 401)
        response = self.client.post(self.url('api', 'v1/page/') + '?' + urlencode({'url': self.url()}), {})
        self.assertEqual(response.status_code, 405)
        self.workspace.disabled_modules = ['spaces']
        self.workspace.save(update_fields=['disabled_modules'])
        self.assertEqual(self.api().status_code, 200)
        self.workspace.disabled_modules = ['calendar']
        self.workspace.save(update_fields=['disabled_modules'])
        self.assertEqual(self.api().status_code, 404)

    def test_guest_can_read_calendar_date(self):
        self.membership.role = 'guest'
        self.membership.save(update_fields=['role'])
        self.assertEqual(self.api().json()['today'], self.today.isoformat())

    def test_first_render_has_only_mini_calendar_and_month_navigation(self):
        response = self.client.get(self.url('spaces', ''), {'q': 'praca', 'sidebar_month': '2027-01'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-today-sidebar')
        self.assertNotContains(response, 'Zadania na dziś')
        self.assertNotContains(response, 'today-sidebar__header')
        self.assertNotContains(response, 'Otwórz kalendarz')
        self.assertContains(response, 'styczeń 2027')
        self.assertContains(response, '?date=2027-01-01')
        self.assertContains(response, 'q=praca&amp;sidebar_month=2026-12')
        self.assertContains(response, 'q=praca&amp;sidebar_month=2026-11')

    def test_custom_calendar_and_task_sidebar_have_no_default_panel_or_data_url(self):
        task = self.task()
        for url in (self.url('calendar', ''), self.url('space', f'{self.space.slug}/tasks/{task.work_item.key}/')):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'data-today-sidebar')
                self.assertContains(response, '"sidebar_url": ""')

    def test_disabled_calendar_first_render(self):
        response = self.client.get(self.url('spaces', ''))
        self.assertContains(response, 'data-today-sidebar')
        self.assertContains(response, self.url())
        self.workspace.disabled_modules = ['calendar']
        self.workspace.save(update_fields=['disabled_modules'])
        response = self.client.get(self.url('spaces', ''))
        self.assertNotContains(response, 'data-today-sidebar')
        self.assertContains(response, '"sidebar_url": ""')
