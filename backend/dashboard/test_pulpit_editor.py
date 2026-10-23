from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import Dashboard, DashboardGadget


class PulpitEditorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='editor-owner', email='editor-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='editor-member', email='editor-member@example.test')
        cls.outsider = get_user_model().objects.create_user(username='editor-outsider', email='editor-outsider@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Edycja pulpitów')
        cls.other = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.dashboard = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner,
                                                 name='Przegląd zespołu', description='Opis', visibility='workspace', layout='three')
        cls.foreign = Dashboard.objects.create(owner=cls.owner, workplace=cls.other, created_by=cls.owner, name='Obcy pulpit', visibility='workspace')
        cls.gadget = DashboardGadget.objects.create(dashboard=cls.dashboard, kind='progress', column=2)

    def setUp(self):
        self.login(self.owner)

    def login(self, user, client=None):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def prefixes(self):
        return ['/dashboards/', scoped_workplace_app_path(self.workspace, 'dashboards')]

    def test_retired_management_opens_catalog_and_each_editor_section_has_its_own_sidebar(self):
        scoped = scoped_workplace_app_path(self.workspace, 'dashboards')
        for prefix in self.prefixes():
            response = self.client.get(prefix + 'manage/', {'q': 'Przegląd', 'visibility': 'workspace'}, follow=True)
            self.assertContains(response, f'href="{scoped}{self.dashboard.slug}/" title="{self.dashboard.name}"')
            self.assertFalse(response.context['pulpit_editor_mode'])
            for management in [False, True]:
                for suffix, key in [('gadgets/', 'gadgets'), ('access/', 'access'), ('edit/', 'settings')]:
                    path = prefix + ('manage/' if management else '') + f'{self.dashboard.slug}/' + suffix
                    with self.subTest(path=path):
                        response = self.client.get(path, follow=True)
                        self.assertEqual(response.status_code, 200)
                        self.assertTrue(response.context['pulpit_editor_mode'])
                        self.assertContains(response, 'data-sidebar-mode="pulpit-editor"')
                        self.assertContains(response, 'data-sidebar-navigation="settings" hidden')
                        self.assertNotContains(response, 'data-sidebar-navigation="pulpit-editor" hidden')
                        sections = response.context['pulpit_editor_navigation']
                        self.assertEqual([entry['label'] for entry in sections], ['Gadżety i układ', 'Ustawienia', 'Udostępnienia'])
                        self.assertEqual([entry['key'] for entry in sections if entry['active']], [key])
                        self.assertContains(response, f'aria-current="page" data-pulpit-editor-section="{key}"')
                        self.assertNotContains(response, 'notifications-tabs work-tabs pulpit-tabs')
                        self.assertNotContains(response, 'Ustawienia i dostęp')

    def test_settings_and_access_forms_save_only_their_fields(self):
        for prefix in self.prefixes():
            for management in [False, True]:
                root = prefix + ('manage/' if management else '') + f'{self.dashboard.slug}/'
                response = self.client.get(root + 'edit/')
                self.assertEqual(list(response.context['form'].fields),
                                 ['name', 'description', 'icon', 'data_scope', 'scope_spaces', 'scope_filter', 'refresh_interval', 'visibility'])
                response = self.client.get(root + 'access/')
                self.assertEqual(list(response.context['form'].fields), ['visibility', 'shared_with'])
                self.dashboard.refresh_from_db()
                revision = self.dashboard.revision
                response = self.client.post(root + 'access/', {'visibility': 'selected', 'shared_with': [self.member.pk],
                                                              'name': 'Nadpisana nazwa', 'layout': 'single'})
                self.assertEqual(response.status_code, 302)
                self.dashboard.refresh_from_db()
                self.assertEqual((self.dashboard.name, self.dashboard.layout, self.dashboard.visibility), ('Przegląd zespołu', 'three', 'selected'))
                self.assertEqual(list(self.dashboard.shared_with.all()), [self.member])
                response = self.client.post(root + 'edit/', {'name': 'Przegląd zespołu', 'description': 'Nowy opis',
                                                            'shared_with': [self.outsider.pk], 'layout': 'single'})
                self.assertEqual(response.status_code, 302)
                self.dashboard.refresh_from_db()
                self.gadget.refresh_from_db()
                self.assertEqual((self.dashboard.description, self.dashboard.layout, self.gadget.column), ('Nowy opis', 'three', 2))
                self.assertEqual(self.dashboard.visibility, 'selected')
                self.assertEqual(list(self.dashboard.shared_with.all()), [self.member])
                self.assertEqual(self.dashboard.revision, revision + 2)

    def test_invalid_access_keeps_editor_navigation_and_does_not_save_configuration(self):
        for prefix in self.prefixes():
            url = prefix + f'manage/{self.dashboard.slug}/access/?q=Przegl%C4%85d&visibility=workspace'
            for data in [{'visibility': 'selected'}, {'visibility': 'selected', 'shared_with': [self.outsider.pk]}, {'visibility': 'forged'}]:
                with self.subTest(prefix=prefix, data=data):
                    response = self.client.post(url, data)
                    self.assertEqual(response.status_code, 400)
                    self.assertContains(response, 'data-sidebar-mode="pulpit-editor"', status_code=400)
                    self.assertContains(response, 'aria-current="page" data-pulpit-editor-section="access"', status_code=400)
                    self.assertContains(response, 'data-pulpit-unsaved="true"', status_code=400)
                    self.assertTrue(response.context['form'].errors)
                    self.dashboard.refresh_from_db()
                    self.assertEqual((self.dashboard.visibility, self.dashboard.revision), ('workspace', 0))
                    self.assertFalse(self.dashboard.shared_with.exists())

    def test_access_private_clears_only_sharing_and_preserves_stars_gadgets_and_settings(self):
        self.dashboard.shared_with.add(self.member)
        self.dashboard.favorited_by.add(self.member)
        response = self.client.post(self.prefixes()[1] + f'{self.dashboard.slug}/access/', {'visibility': 'private', 'shared_with': [self.member.pk]})
        self.assertEqual(response.status_code, 302)
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.name, self.dashboard.description, self.dashboard.layout, self.dashboard.visibility),
                         ('Przegląd zespołu', 'Opis', 'three', 'private'))
        self.assertFalse(self.dashboard.shared_with.exists())
        self.assertTrue(self.dashboard.favorited_by.filter(pk=self.member.pk).exists())
        self.assertTrue(self.dashboard.gadgets.filter(pk=self.gadget.pk).exists())
        self.login(self.member)
        self.assertEqual(self.client.get(self.prefixes()[1] + f'{self.dashboard.slug}/').status_code, 404)

    def test_access_requires_creator_workspace_login_and_csrf(self):
        secure = Client(enforce_csrf_checks=True)
        self.login(self.owner, secure)
        for prefix in self.prefixes():
            for management in [False, True]:
                path = prefix + ('manage/' if management else '') + f'{self.dashboard.slug}/access/'
                self.assertEqual(Client().get(path).status_code, 302)
                self.assertEqual(secure.post(path, {'visibility': 'workspace'}).status_code, 403)
                self.login(self.member)
                self.assertEqual(self.client.get(path).status_code, 403)
                self.assertEqual(self.client.post(path, {'visibility': 'private'}).status_code, 403)
                self.login(self.owner)
                foreign = prefix + ('manage/' if management else '') + f'{self.foreign.slug}/access/'
                self.assertEqual(self.client.get(foreign).status_code, 404)
                self.assertEqual(self.client.post(foreign, {'visibility': 'workspace'}).status_code, 404)

    def test_management_section_links_and_save_keep_catalog_filters(self):
        filters = '?q=Przegl%C4%85d&visibility=workspace&favorite=starred&page=2'
        scoped = scoped_workplace_app_path(self.workspace, 'dashboards')
        for prefix in self.prefixes():
            for suffix in ['gadgets/', 'access/', 'edit/']:
                url = prefix + f'manage/{self.dashboard.slug}/' + suffix + filters
                response = self.client.get(url)
                self.assertEqual(response.context['return_url'], scoped + filters)
                self.assertEqual([entry['url'] for entry in response.context['pulpit_editor_navigation']],
                                 [scoped + f'manage/{self.dashboard.slug}/' + section + filters for section in ['gadgets/', 'edit/', 'access/']])
                if suffix == 'access/':
                    saved = self.client.post(url, {'visibility': 'workspace'}, HTTP_X_PULPIT_MODAL='true')
                    self.assertEqual(saved.json(), {'saved': True, 'url': scoped + filters})

    def test_direct_gadget_modal_keeps_selected_dashboard_sidebar(self):
        for prefix in self.prefixes():
            response = self.client.get(prefix + f'manage/{self.dashboard.slug}/gadgets/{self.gadget.pk}/edit/')
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'dashboard/pulpits/gadgets.html')
            self.assertContains(response, 'aria-current="page" data-pulpit-editor-section="gadgets"')
            self.assertContains(response, self.dashboard.name)
