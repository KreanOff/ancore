import json
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase

from spaces.testing import make_space
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import Dashboard, DashboardGadget, DashboardMembership
from .pulpit_grid import overlaps, resolved_widgets


class PulpitGridTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='grid-owner', email='grid-owner@example.test')
        cls.member = users.objects.create_user(username='grid-member', email='grid-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Siatka pulpitu')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.dashboard = Dashboard.objects.create(owner=cls.owner, created_by=cls.owner,
            workplace=cls.workspace, name='Siatka', visibility='selected')
        cls.source = make_space(user=cls.owner, workplace=cls.workspace, name='Źródło', key='SRC')
        cls.first = DashboardGadget.objects.create(dashboard=cls.dashboard, title='Moje źródło', space=cls.source,
            assignee='me', column=0)
        cls.second = DashboardGadget.objects.create(dashboard=cls.dashboard, column=1)

    def setUp(self):
        self.login(self.owner)

    def login(self, user, client=None):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def path(self, suffix='', scoped=False):
        if scoped:
            return scoped_workplace_app_path(self.workspace, 'dashboards', f'{self.dashboard.slug}/{suffix}')
        return f'/dashboards/{self.dashboard.slug}/{suffix}'

    def api(self, path):
        return scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') + '?' + urlencode({'url': path})

    def rect(self, identifier, **values):
        return {'id': str(identifier), 'x': 0, 'y': 0, 'w': 6, 'h': 8, **values}

    def save(self, widgets, revision=0, path=None, client=None):
        return (client or self.client).post(path or self.path('arrange/'),
            json.dumps({'revision': revision, 'widgets': widgets}), content_type='application/json')

    def snapshot(self):
        self.dashboard.refresh_from_db()
        return (self.dashboard.revision, list(self.dashboard.gadgets.values()))

    def test_view_and_editor_payload_supply_grid_and_preserve_compatibility_columns(self):
        for scoped in (False, True):
            for suffix in ('', 'gadgets/'):
                response = self.client.get(self.api(self.path(suffix, scoped)))
                self.assertEqual(response.status_code, 200)
                data = response.json()['data']
                self.assertEqual(data['grid']['widgets'], [self.rect(self.first.pk), self.rect(self.second.pk, x=6)])
                self.assertEqual(data['grid']['columns'], 12)
                self.assertEqual(data['grid']['revision'], 0)
                self.assertEqual(data['grid']['save_url'], self.path('arrange/', True))
                self.assertEqual(data['max_gadgets'], 24)
                self.assertTrue(data['gadget_catalog'])
                self.assertTrue(data['columns'][0][0]['edit_url'])
        self.first.refresh_from_db()
        self.assertIsNone(self.first.x, 'Reading old records must not write their derived positions.')

    def test_first_render_positions_cards_on_the_shared_summary_grid(self):
        response = self.client.get(self.path())
        self.assertContains(response, 'work-summary-canvas pulpit-summary-canvas')
        self.assertContains(response, 'grid-column: 7 / span 6; grid-row: 1 / span 8')
        self.assertContains(response, 'css/components/spaces.css')
        self.assertNotContains(response, 'data-pulpit-column=')

    def test_grid_save_atomically_adds_moves_resizes_and_removes_with_configuration_preserved(self):
        response = self.save([self.rect(self.first.pk, x=4, w=8, h=6),
                              self.rect('new-card-1', kind='progress', x=0, y=6, w=4, h=5)])
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['revision'], 1)
        page = data['page']
        self.assertEqual(page['type'], 'pulpit-detail')
        self.assertTrue(page['data']['editing'])
        self.assertEqual(page['data']['grid']['revision'], 1)
        self.first.refresh_from_db()
        self.assertEqual((self.first.title, self.first.space, self.first.assignee), ('Moje źródło', self.source, 'me'))
        self.assertEqual((self.first.x, self.first.y, self.first.w, self.first.h), (4, 0, 8, 6))
        self.assertFalse(DashboardGadget.objects.filter(pk=self.second.pk).exists())
        added = self.dashboard.gadgets.exclude(pk=self.first.pk).get()
        self.assertEqual((added.kind, added.space_id, added.assignee), ('progress', None, 'all'))
        self.assertEqual([item['id'] for item in page['data']['grid']['widgets']], [str(self.first.pk), str(added.pk)])
        self.assertEqual(self.client.get(self.api(self.path())).json()['data']['grid'], page['data']['grid'])

    def test_empty_grid_stays_empty_and_saved_default_never_reseeds(self):
        self.dashboard = Dashboard.objects.get(created_by=self.owner, workplace=self.workspace, is_default=True)
        self.assertEqual(self.save([]).status_code, 200)
        self.assertFalse(self.dashboard.gadgets.exists())
        self.assertContains(self.client.get('/dashboards/default/'), 'Ten pulpit jest pusty.')
        self.assertFalse(self.dashboard.gadgets.exists())

    def test_scoped_api_save_returns_actual_persisted_identifiers(self):
        response = self.save([self.rect('new-api', kind='progress')], path=self.api(self.path('arrange/', True)))
        self.assertEqual(response.status_code, 200)
        data = response.json()['page']['data']
        self.assertEqual(data['grid']['widgets'][0]['id'], str(self.dashboard.gadgets.get().pk))
        self.assertTrue(data['columns'][0][0]['edit_url'].startswith(scoped_workplace_app_path(self.workspace, 'dashboards')))

    def test_invalid_rectangles_ids_kinds_and_overlap_never_write(self):
        valid = self.rect(self.first.pk)
        invalid = [None, {}, 'widgets', [valid, valid],
            [valid, self.rect(self.second.pk, x=5)],
            [self.rect('unknown')], [self.rect('new-missing-kind')],
            [self.rect('new-bad-kind', kind='activity')], [self.rect('new-<script>', kind='progress')],
            [{**valid, 'kind': 'activity'}], [{**valid, 'source': self.source.pk}],
            [{**valid, 'id': self.first.pk}],
            *[[{**valid, field: value}] for field, value in [('x', -1), ('x', True), ('x', 7),
                ('y', -1), ('y', 193), ('w', 3), ('w', 13), ('h', 4), ('h', 17), ('h', 8.0), ('h', '8')]],
            [{key: value for key, value in valid.items() if key != 'h'}]]
        before = self.snapshot()
        for widgets in invalid:
            with self.subTest(widgets=widgets):
                self.assertEqual(self.save(widgets).status_code, 400)
                self.assertEqual(self.snapshot(), before)

    def test_bad_json_and_revision_types_are_rejected_without_writes(self):
        before = self.snapshot()
        for body in ('broken', '[]', 'null', '{}', '{"revision":true,"widgets":[]}',
                     '{"revision":-1,"widgets":[]}', '{"revision":"0","widgets":[]}'):
            with self.subTest(body=body):
                self.assertEqual(self.client.post(self.path('arrange/'), body, content_type='application/json').status_code, 400)
        self.assertEqual(self.snapshot(), before)

    def test_grid_bounds_and_twenty_four_gadget_limit(self):
        boundary = [self.rect(self.first.pk, x=8, y=184, w=4, h=16)]
        self.assertEqual(self.save(boundary).status_code, 200)
        widgets = [self.rect(f'new-{index}', kind='progress', x=index % 3 * 4, y=index // 3 * 5, w=4, h=5)
                   for index in range(25)]
        before = self.snapshot()
        self.assertEqual(self.save(widgets, revision=1).status_code, 400)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.save(widgets[:24], revision=1).status_code, 200)
        self.assertEqual(self.dashboard.gadgets.count(), 24)

    def test_stale_revision_does_not_apply_any_add_delete_or_movement(self):
        self.assertEqual(self.save([self.rect(self.first.pk)]).status_code, 200)
        before = self.snapshot()
        self.assertEqual(self.save([self.rect('new-stale', kind='progress')]).status_code, 409)
        self.assertEqual(self.save([self.rect(self.second.pk)]).status_code, 409)
        self.assertEqual(self.snapshot(), before)

    def test_foreign_gadget_and_workspace_are_rejected(self):
        foreign_dashboard = Dashboard.objects.create(owner=self.owner, created_by=self.owner,
            workplace=self.other, name='Obcy')
        foreign = DashboardGadget.objects.create(dashboard=foreign_dashboard)
        before = self.snapshot()
        self.assertEqual(self.save([self.rect(foreign.pk)]).status_code, 400)
        wrong_workspace = scoped_workplace_app_path(self.other, 'dashboards', f'{self.dashboard.slug}/arrange/')
        self.assertEqual(self.save([], path=wrong_workspace).status_code, 404)
        self.assertTrue(DashboardGadget.objects.filter(pk=foreign.pk).exists())
        self.assertEqual(self.snapshot(), before)

    def test_members_and_admins_can_edit_but_observers_cannot(self):
        membership = DashboardMembership.objects.create(dashboard=self.dashboard, user=self.member, role='member')
        self.login(self.member)
        self.assertEqual(self.save([self.rect(self.first.pk)]).status_code, 200)
        membership.role = 'admin'
        membership.save()
        self.assertEqual(self.save([self.rect(self.first.pk, w=12)], revision=1).status_code, 200)
        membership.role = 'observer'
        membership.save()
        before = self.snapshot()
        self.assertEqual(self.save([], revision=2).status_code, 403)
        data = self.client.get(self.api(self.path())).json()['data']
        self.assertEqual(data['gadget_catalog'], [])
        self.assertEqual(data['columns'][0][0]['edit_url'], '')
        membership.delete()
        self.assertEqual(self.save([], revision=2).status_code, 404)
        self.assertEqual(self.snapshot(), before)

    def test_login_post_and_csrf_guards(self):
        self.assertEqual(self.client.get(self.path('arrange/')).status_code, 405)
        guarded = Client(enforce_csrf_checks=True)
        self.login(self.owner, guarded)
        self.assertEqual(self.save([], client=guarded).status_code, 403)
        self.client.logout()
        self.assertEqual(self.save([]).status_code, 302)

    def test_legacy_arrangement_and_quick_add_preserve_a_nonoverlapping_grid(self):
        response = self.client.post(self.path('arrange/'), json.dumps({'revision': 0, 'layout': 'left',
            'columns': [[self.second.pk, self.first.pk], []]}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.first.refresh_from_db()
        self.assertEqual((self.first.x, self.first.y, self.first.w, self.first.h), (0, 8, 8, 8))
        response = self.client.post(self.path('gadgets/quick-add/'), json.dumps({'revision': 1, 'kind': 'progress'}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        added = self.dashboard.gadgets.get(pk=response.json()['gadget_id'])
        self.assertEqual((added.x, added.y, added.w, added.h), (8, 0, 4, 8))
        self.dashboard.refresh_from_db()
        widgets = resolved_widgets(self.dashboard, list(self.dashboard.gadgets.all()))
        self.assertFalse(any(overlaps(first, second) for index, first in enumerate(widgets) for second in widgets[index + 1:]))


class PulpitGridMigrationTests(TransactionTestCase):
    def test_all_previous_layouts_keep_sources_order_and_sizes_through_migration(self):
        before = [('dashboard', '0007_remove_workspace_invitations')]
        after = [('dashboard', '0008_dashboard_gadget_grid')]
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(before)
            loader = MigrationExecutor(connection).loader
            apps = loader.project_state(list(loader.applied_migrations)).apps
            User = apps.get_model('accounts', 'User')
            Workplace = apps.get_model('workplaces', 'Workplace')
            DashboardModel = apps.get_model('dashboard', 'Dashboard')
            Gadget = apps.get_model('dashboard', 'DashboardGadget')
            owner = User.objects.create(username='grid-migration', email='grid-migration@example.test')
            workspace = Workplace.objects.create(owner_id=owner.pk, name='Migracja siatki',
                code='w_grid_migration', slug='w_grid_migration')
            expected = {}
            layouts = {'single': [12], 'equal': [6, 6], 'left': [8, 4], 'right': [4, 8], 'three': [4, 4, 4]}
            for layout, widths in layouts.items():
                dashboard = DashboardModel.objects.create(owner_id=owner.pk, created_by_id=owner.pk,
                    workplace_id=workspace.pk, name=layout, slug=layout, layout=layout, revision=7)
                for column, width in enumerate(widths):
                    # Sparse old positions remain ordered and are compacted in the new grid.
                    for index, position in enumerate((3, 9)):
                        gadget = Gadget.objects.create(dashboard_id=dashboard.pk, column=column, position=position,
                            title=f'{layout}-{column}-{position}', assignee='me')
                        expected[gadget.pk] = (sum(widths[:column]), index * 8, width, 8)
            original = list(Gadget.objects.order_by('pk').values('id', 'dashboard_id', 'title', 'assignee', 'column', 'position'))
            MigrationExecutor(connection).migrate(after)
            loader = MigrationExecutor(connection).loader
            apps = loader.project_state(list(loader.applied_migrations)).apps
            Gadget = apps.get_model('dashboard', 'DashboardGadget')
            self.assertEqual(list(Gadget.objects.order_by('pk').values('id', 'dashboard_id', 'title', 'assignee', 'column', 'position')), original)
            self.assertEqual({gadget.pk: (gadget.x, gadget.y, gadget.w, gadget.h) for gadget in Gadget.objects.all()}, expected)
            self.assertTrue(all(revision == 7 for revision in apps.get_model('dashboard', 'Dashboard').objects.values_list('revision', flat=True)))
            MigrationExecutor(connection).migrate(before)
            loader = MigrationExecutor(connection).loader
            apps = loader.project_state(list(loader.applied_migrations)).apps
            self.assertEqual(list(apps.get_model('dashboard', 'DashboardGadget').objects.order_by('pk').values(
                'id', 'dashboard_id', 'title', 'assignee', 'column', 'position')), original)
        finally:
            MigrationExecutor(connection).migrate(leaves)
