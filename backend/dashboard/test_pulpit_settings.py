"""Standalone dashboard settings retain their scoped access and native fallback."""
from html.parser import HTMLParser

from django.test import TestCase

from workplaces.models import WorkplaceMembership
from workplaces.services import scoped_workplace_app_path
from .test_pulpit_sharing import PulpitSharingFixture


class SidebarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.visible_navigation = []
        self.active_settings = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'nav' and 'data-sidebar-navigation' in attrs and 'hidden' not in attrs:
            self.visible_navigation.append(attrs['data-sidebar-navigation'])
        if tag == 'a' and attrs.get('aria-current') == 'page' and 'data-pulpit-settings-tab' in attrs:
            self.active_settings.append(attrs['data-pulpit-settings-tab'])


class PulpitSettingsPageTests(PulpitSharingFixture, TestCase):
    def navigation(self, target, scoped=True):
        endpoint = self.api(scoped).replace('/page/', '/navigation/')
        return self.client.get(endpoint, {'url': target}, follow=True)

    def test_native_settings_and_sharing_are_pages_with_the_matching_sidebar(self):
        for scoped in (False, True):
            for suffix, section in [('edit/', 'settings'), ('access/', 'access')]:
                with self.subTest(scoped=scoped, suffix=suffix):
                    response = self.client.get(self.url(suffix, scoped))
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'data-sidebar-navigation="pulpit-settings"')
                    self.assertContains(response, 'data-sidebar-navigation="pulpit-editor" hidden')
                    sidebar_html = SidebarParser()
                    sidebar_html.feed(response.content.decode())
                    self.assertEqual(sidebar_html.visible_navigation, ['pulpit-settings'])
                    self.assertEqual(sidebar_html.active_settings, [section])
                    self.assertContains(response, 'space-settings-page pulpit-settings-page')
                    self.assertContains(response, f'data-pulpit-settings-tab="{section}"')
                    self.assertNotContains(response, 'aria-labelledby="pulpit-modal-title"')
                    self.assertNotContains(response, 'data-pulpit-modal>')
                    sidebar = response.context['pulpit_settings_sidebar']
                    self.assertEqual(sidebar['tab'], section)
                    self.assertEqual([entry['label'] for entry in sidebar['links']], ['Ustawienia', 'Udostępnienia'])
                    if section == 'settings':
                        self.assertContains(response, 'name="description"')
                    else:
                        self.assertContains(response, 'aria-label="Osoby z dostępem do pulpitu"')
                        self.assertContains(response, self.reader.email)

    def test_numeric_and_management_settings_links_preserve_filters_and_return_path(self):
        for scoped in (False, True):
            prefix = scoped_workplace_app_path(self.workspace, 'dashboards') if scoped else '/dashboards/'
            for identifier in (self.dashboard.pk, self.dashboard.slug):
                for suffix, section in [('edit/', 'settings'), ('access/', 'access')]:
                    target = f'{prefix}manage/{identifier}/{suffix}?q=Plan&page=2'
                    response = self.navigation(target, scoped)
                    self.assertEqual(response.status_code, 200)
                    result = response.json()
                    self.assertEqual(result['shell']['mode'], 'pulpit-settings')
                    sidebar = result['shell']['pulpit_settings']
                    self.assertEqual(sidebar['tab'], section)
                    expected_prefix = scoped_workplace_app_path(self.workspace, 'dashboards', f'manage/{self.dashboard.slug}/')
                    self.assertEqual([row['url'] for row in sidebar['links']],
                                     [expected_prefix + part + '?q=Plan&page=2' for part in ('edit/', 'access/')])
                    self.assertEqual(result['page']['data']['return_url'],
                                     scoped_workplace_app_path(self.workspace, 'dashboards') + '?q=Plan&page=2')

    def test_invalid_page_save_retains_values_and_native_form_can_be_resubmitted(self):
        for scoped in (False, True):
            response = self.post({'name': '', 'description': 'Zachowany szkic'}, 'edit/', scoped)
            self.assertEqual(response.status_code, 400)
            page = response.json()['data']
            self.assertEqual(page['settings_sidebar']['tab'], 'settings')
            fields = {field['name']: field for field in page['form']['fields']}
            self.assertTrue(fields['name']['errors'])
            self.assertEqual(fields['description']['value'], 'Zachowany szkic')
            native = self.client.post(self.url('edit/', scoped), {'name': '', 'description': 'Zachowany szkic'})
            self.assertContains(native, 'data-sidebar-navigation="pulpit-settings"', status_code=400)
            self.assertContains(native, 'Zachowany szkic', status_code=400)
            saved = self.client.post(self.url('edit/', scoped), {'name': 'Plan pracy', 'description': 'Zachowany szkic'})
            self.assertEqual(saved.status_code, 302)
            self.assertEqual(saved['Location'], self.url('edit/'))
            self.dashboard.refresh_from_db()
            self.assertEqual(self.dashboard.description, 'Zachowany szkic')
            self.assertEqual(self.dashboard.memberships.get(user=self.reader).role, 'observer')

    def test_native_access_save_stays_in_its_section_with_management_filters(self):
        for scoped in (False, True):
            prefix = scoped_workplace_app_path(self.workspace, 'dashboards') if scoped else '/dashboards/'
            target = f'{prefix}manage/{self.dashboard.slug}/access/?q=Plan&page=2'
            saved = self.client.post(target, {'visibility': 'selected', 'shared_with': [self.reader.pk]})
            self.assertEqual(saved.status_code, 302)
            self.assertEqual(saved['Location'], scoped_workplace_app_path(
                self.workspace, 'dashboards', f'manage/{self.dashboard.slug}/access/') + '?q=Plan&page=2')

    def test_admin_uses_both_pages_without_owner_only_visibility_control(self):
        self.dashboard.memberships.create(user=self.recipient, role='admin')
        self.login(self.recipient)
        for scoped in (False, True):
            for suffix in ('edit/', 'access/'):
                result = self.navigation(self.url(suffix, scoped), scoped)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()['shell']['mode'], 'pulpit-settings')
                self.assertFalse(result.json()['page']['data']['team']['is_owner'])
            settings = self.get('edit/', scoped).json()['data']
            self.assertTrue(next(field for field in settings['form']['fields'] if field['name'] == 'visibility')['disabled'])
            native = self.client.get(self.url('access/', scoped))
            self.assertContains(native, 'aria-label="Osoby z dostępem do pulpitu"')
            self.assertNotContains(native, 'data-pulpit-edit-form')

    def test_observer_and_revoked_admin_cannot_open_or_submit_stale_settings(self):
        membership = self.dashboard.memberships.create(user=self.recipient, role='admin')
        self.login(self.recipient)
        self.assertEqual(self.navigation(self.url('edit/')).status_code, 200)
        membership.role = 'observer'
        membership.save(update_fields=['role'])
        for scoped in (False, True):
            for suffix in ('edit/', 'access/'):
                self.assertEqual(self.navigation(self.url(suffix, scoped), scoped).status_code, 403)
                self.assertEqual(self.post({'name': 'Niedozwolone', 'visibility': 'workspace'}, suffix, scoped).status_code, 403)
        membership.delete()
        self.assertEqual(self.navigation(self.url('edit/')).status_code, 404)
        self.assertEqual(self.post({'name': 'Niedozwolone'}, 'edit/').status_code, 404)

    def test_settings_navigation_does_not_cross_workspace_or_disabled_module(self):
        self.assertEqual(self.navigation(self.url('edit/', dashboard=self.foreign)).status_code, 404)
        self.workspace.disabled_modules = ['dashboards']
        self.workspace.save(update_fields=['disabled_modules'])
        for suffix in ('edit/', 'access/'):
            self.assertEqual(self.navigation(self.url(suffix)).status_code, 404)
        self.workspace.disabled_modules = []
        self.workspace.save(update_fields=['disabled_modules'])
        membership = WorkplaceMembership.objects.get(workplace=self.workspace, user=self.creator)
        membership.is_active = False
        membership.save(update_fields=['is_active'])
        self.assertEqual(self.navigation(self.url('edit/')).status_code, 403)
