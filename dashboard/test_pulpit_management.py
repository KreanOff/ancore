from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import Dashboard, DashboardGadget, DashboardGroup


class PulpitManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='pulpit-manager', email='manager@example.test')
        cls.member = get_user_model().objects.create_user(username='pulpit-manager-member', email='member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Zarządzanie pulpitami')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.own = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Plan wydania', visibility='private')
        cls.shared = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.member, name='Plan członka', visibility='workspace')
        cls.hidden = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.member, name='Prywatny plan członka')
        cls.foreign = Dashboard.objects.create(owner=cls.owner, workplace=cls.other, created_by=cls.owner, name='Obcy plan')

    def setUp(self):
        self.login(self.owner)

    def login(self, user, client=None):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'dashboards', 'manage/' + suffix)

    def payload(self, **kwargs):
        return {'name': 'Nowy plan', 'description': '', 'visibility': 'private', 'layout': 'equal', **kwargs}

    def test_management_is_separate_from_catalog_in_plain_and_scoped_urls(self):
        for url in ['/dashboards/manage/', self.url()]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'dashboard/pulpits/manage.html')
            self.assertTrue(response.context['pulpits_management_mode'])
            self.assertContains(response, 'data-sidebar-mode="pulpits-management"')
            self.assertContains(response, 'data-sidebar-navigation="workspace" hidden')
            self.assertNotContains(response, 'data-sidebar-navigation="pulpits-management" hidden')
            self.assertContains(response, 'Wróć do poprzedniego widoku')
        response = self.client.get(scoped_workplace_app_path(self.workspace, 'dashboards'))
        self.assertFalse(response.context['pulpits_management_mode'])
        self.assertContains(response, 'data-sidebar-navigation="pulpits-management" hidden')
        self.assertContains(response, self.url())

    def test_only_editable_dashboards_in_current_scope_are_managed(self):
        response = self.client.get(self.url())
        self.assertEqual(list(response.context['page']), [self.own])
        self.login(self.member)
        response = self.client.get(self.url())
        self.assertEqual({item.pk for item in response.context['page']}, {self.shared.pk, self.hidden.pk})
        self.assertEqual(self.client.get(self.url(f'{self.own.pk}/edit/')).status_code, 404)
        self.login(self.owner)
        self.assertEqual(self.client.post(self.url(f'{self.shared.pk}/edit/'), self.payload()).status_code, 403)
        for item in [self.hidden, self.foreign]:
            self.assertEqual(self.client.post(self.url(f'{item.pk}/edit/'), self.payload()).status_code, 404)
            self.assertEqual(self.client.post(self.url(f'{item.pk}/delete/')).status_code, 404)

    def test_search_visibility_star_filters_and_pagination(self):
        self.own.favorited_by.add(self.owner)
        response = self.client.get(self.url(), {'q': 'wydania', 'visibility': 'private', 'favorite': 'starred'})
        self.assertEqual(list(response.context['page']), [self.own])
        for filters in [{'visibility': 'workspace'}, {'favorite': 'unstarred'}, {'q': 'nieznana nazwa'}]:
            response = self.client.get(self.url(), filters)
            self.assertEqual(response.context['page'].paginator.count, 0)
            self.assertContains(response, 'Brak pasujących pulpitów')
        for number in range(31):
            Dashboard.objects.create(owner=self.owner, workplace=self.workspace, created_by=self.owner, name=f'Wydanie {number}')
        response = self.client.get(self.url(), {'q': 'Wydanie', 'visibility': 'private', 'page': 2})
        self.assertEqual(response.context['page'].paginator.count, 31)
        self.assertEqual(len(response.context['page']), 1)
        self.assertContains(response, 'q=Wydanie&amp;visibility=private&amp;page=1')

    def test_create_and_validation_keep_management_and_actual_creator(self):
        self.login(self.member)
        response = self.client.get(self.url('create/'))
        self.assertTemplateUsed(response, 'dashboard/pulpits/manage.html')
        invalid = self.client.post(self.url('create/'), self.payload(name=''))
        self.assertEqual(invalid.status_code, 400)
        self.assertTemplateUsed(invalid, 'dashboard/pulpits/manage.html')
        self.assertTrue(invalid.context['pulpits_management_mode'])
        response = self.client.post(self.url('create/'), self.payload(), HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.json(), {'saved': True, 'url': self.url()})
        dashboard = Dashboard.objects.get(name='Nowy plan')
        self.assertEqual((dashboard.owner, dashboard.created_by, dashboard.workplace), (self.owner, self.member, self.workspace))
        self.assertEqual(dashboard.gadgets.count(), 4)

    def test_edit_copy_groups_and_delete_return_with_filters(self):
        filters = '?q=Plan&visibility=private&favorite=starred&page=2'
        self.own.favorited_by.add(self.owner)
        gadget = DashboardGadget.objects.create(dashboard=self.own, kind='summary')
        response = self.client.get(self.url(f'{self.own.pk}/edit/') + filters)
        self.assertTemplateUsed(response, 'dashboard/pulpits/manage.html')
        self.assertEqual(response.context['modal']['return_url'], self.url() + filters)
        response = self.client.post(self.url(f'{self.own.pk}/edit/') + filters, self.payload(name='Plan po edycji'), HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.json()['url'], self.url() + filters)
        response = self.client.post(self.url(f'{self.own.pk}/copy/') + filters, self.payload(name='Kopia planu'), HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.json()['url'], self.url() + filters)
        self.assertEqual(Dashboard.objects.get(name='Kopia planu').gadgets.count(), 1)
        group = DashboardGroup.objects.create(owner=self.owner, workplace=self.workspace, user=self.owner, name='Grupa')
        response = self.client.post(self.url(f'{self.own.pk}/groups/') + filters, {'groups': [group.pk]}, HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.json()['url'], self.url() + filters)
        self.assertTrue(group.dashboards.filter(pk=self.own.pk).exists())
        response = self.client.post(self.url(f'{self.own.pk}/delete/') + filters, HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.json()['url'], self.url() + filters)
        self.assertFalse(DashboardGadget.objects.filter(pk=gadget.pk).exists())
        self.assertFalse(group.dashboards.exists())

    def test_favorite_preserves_management_filters_and_personal_relation(self):
        target = self.url() + '?visibility=private&q=Plan'
        response = self.client.post(scoped_workplace_app_path(self.workspace, 'dashboards', f'{self.own.pk}/favorite/'), {'next': target}, HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.json()['url'], target)
        self.assertTrue(self.own.favorited_by.filter(pk=self.owner.pk).exists())
        self.assertFalse(self.own.favorited_by.filter(pk=self.member.pk).exists())

    def test_empty_state_login_csrf_and_post_only_delete(self):
        self.assertEqual(Client().get(self.url()).status_code, 302)
        secure = Client(enforce_csrf_checks=True)
        self.login(self.owner, secure)
        self.assertEqual(secure.post(self.url('create/'), self.payload()).status_code, 403)
        self.assertEqual(secure.post(self.url(f'{self.own.pk}/delete/')).status_code, 403)
        self.assertEqual(self.client.get(self.url(f'{self.own.pk}/delete/')).status_code, 405)
        empty = create_workplace_for_user(self.owner, 'Pusty Workspace')
        response = self.client.get(scoped_workplace_app_path(empty, 'dashboards', 'manage/'))
        self.assertContains(response, 'Brak pulpitów do zarządzania')
        self.assertContains(response, 'Utwórz pulpit')
