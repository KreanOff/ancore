import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import Dashboard, DashboardGadget


class GadgetCatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='catalog-owner', email='catalog@example.test')
        cls.member = get_user_model().objects.create_user(username='catalog-member', email='member@example.test')
        cls.workplace = create_workplace_for_user(cls.owner, 'Katalog gadżetów')
        cls.other = create_workplace_for_user(cls.owner, 'Inny zespół')
        WorkplaceMembership.objects.create(workplace=cls.workplace, user=cls.member)
        cls.dashboard = Dashboard.objects.create(owner=cls.owner, created_by=cls.owner, workplace=cls.workplace,
                                                 name='Pulpit', visibility='workspace', layout='three')

    def setUp(self):
        self.login(self.owner)

    def login(self, user, client=None):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workplace.pk
        session.save()

    def add(self, kind='progress', revision=0, path=None, client=None):
        return (client or self.client).post(path or f'/dashboards/{self.dashboard.slug}/gadgets/quick-add/',
                                           json.dumps({'kind': kind, 'revision': revision}), content_type='application/json')

    def test_quick_add_progress_balances_columns_and_returns_real_gadgets(self):
        self.assertEqual(DashboardGadget.Kind.values, ['progress'])
        for revision in range(5):
            kind = 'progress'
            response = self.add(kind, revision)
            self.assertEqual(response.status_code, 200)
            result = response.json()
            gadget = DashboardGadget.objects.get(pk=result['gadget_id'])
            self.assertEqual(gadget.kind, kind)
            self.assertEqual(gadget.column, revision % 3)
            self.assertEqual((result['revision'], result['gadget_count']), (revision + 1, revision + 1))
            self.assertIn(f'data-pulpit-gadget="{gadget.pk}"', result['html'])
            self.assertIn('data-pulpit-drag', result['html'])
            self.assertEqual(gadget.assignee, 'all')
            self.assertIn('Zamknięte: 0 z 0', result['html'])
            self.assertIn('dashboard-overview-statuses', result['html'])
        editor = self.client.get(f'/dashboards/{self.dashboard.slug}/gadgets/')
        self.assertContains(editor, 'data-pulpit-catalog-item', count=1)
        self.assertContains(editor, 'data-pulpit-quick-add="progress"', count=1)
        for kind in ['assigned', 'results', 'summary', 'statistics', 'activity']:
            self.assertNotContains(editor, f'data-pulpit-quick-add="{kind}"')
            self.assertEqual(self.add(kind, revision=5).status_code, 400)

    def test_stale_revision_rejects_repeated_add_without_creating_duplicates(self):
        self.assertEqual(self.add().status_code, 200)
        response = self.add(revision=0)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.dashboard.gadgets.count(), 1)
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 1)

    def test_invalid_payloads_and_limit_leave_configuration_unchanged(self):
        path = f'/dashboards/{self.dashboard.slug}/gadgets/quick-add/'
        for body in ['broken', '[]', 'null', '{}', '{"revision":true}', '{"revision":"0"}']:
            self.assertEqual(self.client.post(path, body, content_type='application/json').status_code, 400)
        self.assertEqual(self.add(kind='foreign').status_code, 400)
        self.assertFalse(self.dashboard.gadgets.exists())
        DashboardGadget.objects.bulk_create([DashboardGadget(dashboard=self.dashboard, kind='progress') for _ in range(24)])
        response = self.add()
        self.assertEqual(response.status_code, 400)
        self.assertIn('maksymalnie 24', response.json()['error'])
        self.assertEqual(self.dashboard.gadgets.count(), 24)
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 0)

    def test_creator_workspace_csrf_and_method_guards(self):
        path = f'/dashboards/{self.dashboard.slug}/gadgets/quick-add/'
        self.assertEqual(self.client.get(path).status_code, 405)
        guarded = Client(enforce_csrf_checks=True)
        self.login(self.owner, guarded)
        self.assertEqual(self.add(client=guarded).status_code, 403)
        self.login(self.member)
        self.assertEqual(self.add().status_code, 403)
        self.login(self.owner)
        foreign_path = scoped_workplace_app_path(self.other, 'dashboards', f'{self.dashboard.slug}/gadgets/quick-add/')
        self.assertEqual(self.add(path=foreign_path).status_code, 404)
        self.client.logout()
        self.assertEqual(self.add().status_code, 302)
        self.assertFalse(self.dashboard.gadgets.exists())

    def test_scoped_and_management_urls_keep_configuration_links(self):
        prefix = scoped_workplace_app_path(self.workplace, 'dashboards')
        path = f'{prefix}manage/{self.dashboard.slug}/gadgets/quick-add/?q=Plan&favorite=starred'
        response = self.add(path=path)
        self.assertEqual(response.status_code, 200)
        gadget = self.dashboard.gadgets.get()
        self.assertIn(f'{prefix}manage/{self.dashboard.slug}/gadgets/{gadget.pk}/edit/?q=Plan&amp;favorite=starred', response.json()['html'])
        self.assertNotIn('/dashboards/None/', response.json()['html'])
