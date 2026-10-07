from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

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
        cls.gadget = DashboardGadget.objects.create(dashboard=cls.dashboard, kind='summary')
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
                               f'{self.dashboard.pk}/groups/', f'manage/{self.dashboard.pk}/groups/']:
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
            for suffix in ['', f'{self.dashboard.pk}/', 'manage/', f'{self.dashboard.pk}/edit/', f'{self.dashboard.pk}/gadgets/']:
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
            self.assertTrue(all('group=' not in tab['url'] for tab in response.context['tabs']))
            self.assertNotContains(response, 'name="group"')
            self.assertNotContains(response, self.private.name)
            self.assertNotContains(response, self.foreign.name)
            self.assertContains(response, 'sidebar-spaces-more active')


class PulpitGroupRemovalMigrationTests(TransactionTestCase):
    def test_migration_removes_only_groups_and_preserves_dashboard_configuration(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [('dashboard', '0008_dashboardgroup')]
        owner = get_user_model().objects.create_user(username='group-migration-owner', email='group-migration@example.test')
        member = get_user_model().objects.create_user(username='group-migration-member', email='group-migration-member@example.test')
        workspace = create_workplace_for_user(owner, 'Migracja pulpitów')
        other = create_workplace_for_user(owner, 'Drugi Workspace migracji')
        try:
            executor.migrate(previous)
            old_apps = executor.loader.project_state(previous).apps
            OldDashboard = old_apps.get_model('dashboard', 'Dashboard')
            OldGadget = old_apps.get_model('dashboard', 'DashboardGadget')
            OldGroup = old_apps.get_model('dashboard', 'DashboardGroup')
            dashboard = OldDashboard.objects.create(owner_id=owner.pk, workplace_id=workspace.pk, created_by_id=member.pk,
                                                    name='Zachowany', description='Opis', visibility='selected', layout='three', revision=7)
            foreign = OldDashboard.objects.create(owner_id=owner.pk, workplace_id=other.pk, created_by_id=owner.pk, name='Drugi pulpit')
            dashboard.shared_with.add(owner.pk)
            dashboard.favorited_by.add(owner.pk, member.pk)
            OldGadget.objects.create(dashboard=dashboard, kind='statistics', title='Statusy', status='new',
                                     assignee='me', group_by='priority', limit=20, column=2, position=3)
            OldGadget.objects.create(dashboard=foreign, kind='assigned', column=1)
            for user in [owner, member]:
                group = OldGroup.objects.create(owner_id=owner.pk, workplace_id=workspace.pk, user_id=user.pk, name='Osobista grupa')
                group.dashboards.add(dashboard)
            snapshots = list(Dashboard.objects.order_by('pk').values())
            gadgets = list(DashboardGadget.objects.order_by('pk').values())
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            self.assertEqual(list(Dashboard.objects.order_by('pk').values()), snapshots)
            self.assertEqual(list(DashboardGadget.objects.order_by('pk').values()), gadgets)
            saved = Dashboard.objects.get(pk=dashboard.pk)
            self.assertEqual(list(saved.shared_with.values_list('pk', flat=True)), [owner.pk])
            self.assertEqual(set(saved.favorited_by.values_list('pk', flat=True)), {owner.pk, member.pk})
            tables = connection.introspection.table_names()
            self.assertNotIn('dashboard_dashboardgroup', tables)
            self.assertNotIn('dashboard_dashboardgroup_dashboards', tables)
            with self.assertRaises(LookupError):
                executor.loader.project_state(latest).apps.get_model('dashboard', 'DashboardGroup')
        finally:
            MigrationExecutor(connection).migrate(latest)
