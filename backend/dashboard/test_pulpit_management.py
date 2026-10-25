from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import Dashboard, DashboardGadget


class PulpitManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='pulpit-manager', email='manager@example.test')
        cls.member = get_user_model().objects.create_user(username='pulpit-manager-member', email='member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Zarządzanie pulpitami')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        cls.default_dashboard = Dashboard.objects.get(workplace=cls.workspace, created_by=cls.owner, is_default=True)
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

    def test_retired_management_redirects_to_catalog_in_plain_and_scoped_urls(self):
        catalog = scoped_workplace_app_path(self.workspace, 'dashboards')
        for url in ['/dashboards/manage/', self.url()]:
            with self.subTest(url=url):
                response = self.client.get(url, {'q': 'Plan', 'visibility': 'private', 'page': 2})
                self.assertRedirects(response, catalog + '?q=Plan&visibility=private&page=2')
        response = self.client.get(catalog)
        self.assertFalse(response.context['pulpits_management_mode'])
        self.assertContains(response, 'data-sidebar-mode="workspace"')
        self.assertNotContains(response, 'Zarządzaj pulpitami')
        self.assertNotContains(response, 'data-sidebar-navigation="pulpits-management"')
        self.assertNotContains(response, self.url())
        self.assertContains(response, f'data-pulpit-directory-row="{self.own.pk}"')
        self.assertContains(response, f'data-pulpit-directory-row="{self.shared.pk}"')
        settings = self.client.get('/settings/')
        self.assertNotContains(settings, 'Zarządzaj pulpitami')
        self.assertNotContains(settings, self.url())

    def test_redirect_uses_visible_catalog_and_legacy_edits_keep_creator_checks(self):
        response = self.client.get(self.url(), follow=True)
        self.assertEqual(list(response.context['page']), [self.shared, self.own, self.default_dashboard])
        self.login(self.member)
        response = self.client.get(self.url(), follow=True)
        self.assertEqual({item.pk for item in response.context['page']}, {self.shared.pk, self.hidden.pk})
        self.assertEqual(self.client.get(self.url(f'{self.own.slug}/edit/')).status_code, 404)
        self.login(self.owner)
        self.assertEqual(self.client.post(self.url(f'{self.shared.slug}/edit/'), self.payload()).status_code, 403)
        for item in [self.hidden, self.foreign]:
            self.assertEqual(self.client.post(self.url(f'{item.slug}/edit/'), self.payload()).status_code, 404)
            self.assertEqual(self.client.post(self.url(f'{item.slug}/delete/')).status_code, 404)

    def test_redirect_keeps_search_visibility_and_pagination(self):
        response = self.client.get(self.url(), {'q': 'wydania', 'visibility': 'private'}, follow=True)
        self.assertEqual(list(response.context['page']), [self.own])
        response = self.client.get(self.url(), {'q': 'nieznana nazwa'}, follow=True)
        self.assertContains(response, 'Brak pasujących pulpitów')
        for number in range(31):
            Dashboard.objects.create(owner=self.owner, workplace=self.workspace, created_by=self.owner, name=f'Wydanie {number}')
        response = self.client.get(self.url(), {'q': 'Wydanie', 'visibility': 'private', 'page': 2}, follow=True)
        self.assertEqual(response.context['page'].paginator.count, 31)
        self.assertEqual(len(response.context['page']), 1)
        self.assertContains(response, 'q=Wydanie&amp;visibility=private&amp;page=1')

    def test_gadget_editor_and_mutations_keep_management_filters(self):
        filters = '?q=Plan&visibility=private&favorite=starred&page=2'
        values = {'kind': 'progress', 'title': '', 'assignee': 'all'}
        for prefix in ['/dashboards/', scoped_workplace_app_path(self.workspace, 'dashboards')]:
            with self.subTest(prefix=prefix):
                base = f'{prefix}manage/{self.own.slug}/gadgets/'
                scoped = scoped_workplace_app_path(self.workspace, 'dashboards')
                target = f'{scoped}manage/{self.own.slug}/gadgets/' + filters
                response = self.client.get(base + filters)
                self.assertTrue(response.context['pulpits_management_mode'])
                self.assertEqual(response.context['return_url'], scoped + filters)
                self.assertEqual(response.context['editor_url'], target)
                self.assertEqual(response.context['settings_url'], f'{scoped}manage/{self.own.slug}/edit/' + filters)
                form = self.client.get(base + 'add/' + filters)
                self.assertTemplateUsed(form, 'dashboard/pulpits/gadgets.html')
                added = self.client.post(base + 'add/' + filters, values, HTTP_X_PULPIT_MODAL='true')
                self.assertEqual(added.json(), {'saved': True, 'url': target})
                gadget = self.own.gadgets.get()
                editor = self.client.get(base + filters)
                data = editor.context['columns'][0][0]['gadget']
                self.assertEqual(data.edit_url, f'{scoped}manage/{self.own.slug}/gadgets/{gadget.pk}/edit/' + filters)
                self.assertEqual(data.delete_url, f'{scoped}manage/{self.own.slug}/gadgets/{gadget.pk}/delete/' + filters)
                deleted = self.client.post(data.delete_url, HTTP_X_PULPIT_MODAL='true')
                self.assertEqual(deleted.json(), {'saved': True, 'url': target})

    def test_create_and_validation_keep_management_and_actual_creator(self):
        self.login(self.member)
        response = self.client.get(self.url('create/'))
        self.assertTemplateUsed(response, 'dashboard/pulpits/index.html')
        invalid = self.client.post(self.url('create/'), self.payload(name=''))
        self.assertEqual(invalid.status_code, 400)
        self.assertTemplateUsed(invalid, 'dashboard/pulpits/index.html')
        self.assertFalse(invalid.context['pulpits_management_mode'])
        response = self.client.post(self.url('create/'), self.payload(), HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.json(), {'saved': True, 'url': scoped_workplace_app_path(self.workspace, 'dashboards')})
        dashboard = Dashboard.objects.get(name='Nowy plan')
        self.assertEqual((dashboard.owner, dashboard.created_by, dashboard.workplace), (self.owner, self.member, self.workspace))
        self.assertEqual(dashboard.gadgets.count(), 0)

    def test_edit_and_delete_return_with_filters(self):
        filters = '?q=Plan&visibility=private&favorite=starred&page=2'
        self.own.favorited_by.add(self.owner)
        gadget = DashboardGadget.objects.create(dashboard=self.own, kind='progress')
        response = self.client.get(self.url(f'{self.own.slug}/edit/') + filters)
        self.assertTemplateUsed(response, 'dashboard/pulpits/edit.html')
        self.assertEqual(response.context['return_url'], scoped_workplace_app_path(self.workspace, 'dashboards') + filters)
        response = self.client.post(self.url(f'{self.own.slug}/edit/') + filters, self.payload(name='Plan po edycji'), HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.json()['url'], scoped_workplace_app_path(self.workspace, 'dashboards') + filters)
        response = self.client.post(self.url(f'{self.own.slug}/delete/') + filters, HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.json()['url'], scoped_workplace_app_path(self.workspace, 'dashboards') + filters)
        self.assertFalse(DashboardGadget.objects.filter(pk=gadget.pk).exists())

    def test_settings_are_a_page_with_editor_sidebar_and_validation_in_both_url_scopes(self):
        for prefix in ['/dashboards/', scoped_workplace_app_path(self.workspace, 'dashboards')]:
            for management in [False, True]:
                suffix = f'manage/{self.own.slug}/edit/' if management else f'{self.own.slug}/edit/'
                url = prefix + suffix + '?q=Plan&visibility=private'
                response = self.client.get(url)
                self.assertTemplateUsed(response, 'dashboard/pulpits/edit.html')
                self.assertTrue(response.context['pulpits_management_mode'])
                self.assertContains(response, 'data-sidebar-mode="pulpit-editor"')
                self.assertContains(response, 'data-sidebar-navigation="workspace" hidden')
                self.assertContains(response, 'data-pulpit-edit-form')
                self.assertNotContains(response, 'data-pulpit-modal>')
                self.assertContains(response, 'value="Plan wydania"')
                invalid = self.client.post(url, self.payload(name='', description='Zachowany szkic'))
                self.assertEqual(invalid.status_code, 400)
                self.assertTemplateUsed(invalid, 'dashboard/pulpits/edit.html')
                self.assertIn('name', invalid.context['form'].errors)
                self.assertContains(invalid, 'data-pulpit-unsaved="true"', status_code=400)
                self.assertEqual(invalid.context['form']['description'].value(), 'Zachowany szkic')
                self.assertTrue(invalid.context['pulpits_management_mode'])
                self.own.refresh_from_db()
                self.assertEqual(self.own.visibility, 'private')

    def test_delete_invalidates_dashboard_return_paths_in_both_url_scopes(self):
        scoped = scoped_workplace_app_path(self.workspace, 'dashboards')
        filters = '?q=Usuwany&visibility=private&favorite=starred&page=2'
        for prefix in ['/dashboards/', scoped]:
            for management in [False, True]:
                with self.subTest(prefix=prefix, management=management):
                    dashboard = Dashboard.objects.create(
                        owner=self.owner, workplace=self.workspace, created_by=self.owner, name='Usuwany pulpit',
                    )
                    pk = dashboard.pk
                    gadget = DashboardGadget.objects.create(dashboard=dashboard, kind='progress')
                    dashboard.favorited_by.add(self.owner)
                    url = prefix + ('manage/' if management else '') + f'{pk}/delete/' + filters
                    response = self.client.post(url, HTTP_X_PULPIT_MODAL='true')
                    self.assertEqual(response.status_code, 200)
                    result = response.json()
                    target = scoped + (filters if management else '')
                    self.assertEqual(result['url'], target)
                    self.assertEqual(set(result['invalidated_return_paths']), {
                        f'/dashboards/{pk}/', f'/dashboards/manage/{pk}/',
                        f'{scoped}{pk}/', f'{scoped}manage/{pk}/',
                        f'/dashboards/{dashboard.slug}/', f'/dashboards/manage/{dashboard.slug}/',
                        f'{scoped}{dashboard.slug}/', f'{scoped}manage/{dashboard.slug}/',
                    })
                    self.assertFalse(Dashboard.objects.filter(pk=pk).exists())
                    self.assertFalse(DashboardGadget.objects.filter(pk=gadget.pk).exists())
                    self.assertTrue(Dashboard.objects.filter(pk=self.own.pk).exists())
                    self.assertEqual(self.client.get(target).status_code, 200)
                    self.assertEqual(self.client.get(f'{scoped}{pk}/').status_code, 404)

    def test_rejected_delete_does_not_invalidate_return_paths(self):
        for dashboard, status in [(self.shared, 403), (self.hidden, 404), (self.foreign, 404)]:
            response = self.client.post(self.url(f'{dashboard.slug}/delete/'), HTTP_X_PULPIT_MODAL='true')
            self.assertEqual(response.status_code, status)
            self.assertNotContains(response, 'invalidated_return_paths', status_code=status)
            self.assertTrue(Dashboard.objects.filter(pk=dashboard.pk).exists())

    def test_settings_save_and_cancel_preserve_destination_layout_and_access(self):
        gadget = DashboardGadget.objects.create(dashboard=self.own, kind='progress', column=1)
        filters = '?q=Plan&visibility=private'
        for management in [False, True]:
            prefix = scoped_workplace_app_path(self.workspace, 'dashboards')
            url = prefix + (f'manage/{self.own.slug}/edit/' if management else f'{self.own.slug}/edit/') + filters
            target = scoped_workplace_app_path(self.workspace, 'dashboards') + filters if management else prefix + f'{self.own.slug}/'
            response = self.client.get(url)
            self.assertEqual(response.context['return_url'], target)
            revision = self.own.revision
            response = self.client.post(url, self.payload(name='Plan po zapisie', visibility='private', shared_with=[self.member.pk], layout='single'))
            self.assertRedirects(response, target)
            self.own.refresh_from_db()
            gadget.refresh_from_db()
            self.assertEqual((self.own.name, self.own.layout, self.own.revision, gadget.column), ('Plan po zapisie', 'equal', revision + 1, 1))
            self.assertFalse(self.own.shared_with.exists())
            self.assertEqual(self.own.visibility, 'private')

    def test_favorite_preserves_management_filters_and_personal_relation(self):
        target = self.url() + '?visibility=private&q=Plan'
        response = self.client.post(scoped_workplace_app_path(self.workspace, 'dashboards', f'{self.own.slug}/favorite/'), {'next': target}, HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.json()['url'], target)
        self.assertTrue(self.own.favorited_by.filter(pk=self.owner.pk).exists())
        self.assertFalse(self.own.favorited_by.filter(pk=self.member.pk).exists())

    def test_empty_state_login_csrf_and_post_only_delete(self):
        self.assertEqual(Client().get(self.url()).status_code, 302)
        secure = Client(enforce_csrf_checks=True)
        self.login(self.owner, secure)
        self.assertEqual(secure.post(self.url('create/'), self.payload()).status_code, 403)
        self.assertEqual(secure.post(self.url(f'{self.own.slug}/delete/')).status_code, 403)
        self.assertEqual(self.client.get(self.url(f'{self.own.slug}/delete/')).status_code, 405)
        empty = create_workplace_for_user(self.owner, 'Pusty Workspace')
        # The owner's initialized default is private; a new member still has an empty catalog.
        WorkplaceMembership.objects.create(workplace=empty, user=self.member)
        self.login(self.member)
        response = self.client.get(scoped_workplace_app_path(empty, 'dashboards', 'manage/'), follow=True)
        self.assertContains(response, 'Brak pulpitów')
        self.assertContains(response, 'Utwórz pulpit')
        self.assertTrue(Dashboard.objects.filter(workplace=empty, created_by=self.owner, is_default=True).exists())
