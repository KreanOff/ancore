"""Settings entry points share a page without broadening Space permissions."""
from copy import deepcopy
from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase

from spaces.defaults import ISSUE_TYPE_ICONS
from spaces.models import SpaceMembership
from spaces.testing import make_space
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class SpaceSettingsFrontendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='settings-owner', email='settings-owner@example.test')
        cls.admin = users.objects.create_user(username='settings-admin', email='settings-admin@example.test')
        cls.observer = users.objects.create_user(username='settings-observer', email='settings-observer@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Ustawienia')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        for person in (cls.admin, cls.observer):
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=person)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Prywatna', visibility='private', private_owner=cls.owner)
        cls.admin_membership = SpaceMembership.objects.create(space=cls.space, user=cls.admin, role='admin')
        SpaceMembership.objects.create(space=cls.space, user=cls.observer, role='observer')

    def page(self, suffix='', scoped=True, **kwargs):
        base = f'/space/{self.space.slug}/'
        if scoped:
            base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
        return self.client.get(api, {'url': base + suffix}, follow=True, **kwargs)

    def test_edit_avatar_and_members_open_matching_tab_in_same_space(self):
        self.client.force_login(self.owner)
        for scoped in (True, False):
            for suffix, tab in [('edit/', 'main'), ('avatar/', 'avatar'), ('members/', 'members')]:
                with self.subTest(scoped=scoped, suffix=suffix):
                    response = self.page(suffix, scoped=scoped)
                    self.assertEqual(response.status_code, 200)
                    data = response.json()['data']
                    self.assertEqual(data['space_settings']['tab'], tab)
                    self.assertTrue(data['space_settings']['space_url'].endswith(f'/space/{self.space.slug}/'))
                    self.assertIn('fields', data['form'])

    def test_validation_keeps_section_with_submitted_values(self):
        self.client.force_login(self.owner)
        base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        response = self.client.post(api + '?url=' + base + 'edit/', {'name': ' ', 'description': 'Zachowany szkic', 'visibility': 'private'})
        self.assertEqual(response.status_code, 400)
        data = response.json()['data']
        self.assertEqual(data['space_settings']['tab'], 'main')
        fields = {field['name']: field for field in data['form']['fields']}
        self.assertTrue(fields['name']['errors'])
        self.assertEqual(fields['description']['value'], 'Zachowany szkic')

    def test_member_actions_respect_private_owner_and_admin_roles(self):
        for person, removable in [(self.owner, True), (self.admin, False), (self.observer, False)]:
            self.client.force_login(person)
            response = self.page('?view=settings')
            self.assertEqual(response.status_code, 200)
            data = response.json()['data']
            member = next(row for row in data['members'] if row['id'] == self.admin_membership.pk)
            self.assertEqual(member['can_remove'], removable)
            self.assertEqual(data['can_manage'], person != self.observer)

    def test_observer_cannot_load_editable_settings(self):
        self.client.force_login(self.observer)
        for suffix in ('edit/', 'avatar/', 'members/', 'configuration/'):
            self.assertEqual(self.page(suffix).status_code, 403)

    def test_other_workspace_cannot_load_settings(self):
        self.client.force_login(self.owner)
        api = scoped_workplace_app_path(self.other, 'api', 'v1/page/')
        for suffix in ('edit/', 'avatar/', 'members/', 'configuration/'):
            target = scoped_workplace_app_path(self.other, 'space', self.space.slug + '/' + suffix)
            self.assertEqual(self.client.get(api, {'url': target}).status_code, 404)

    def test_edit_exposes_shared_avatar_control_without_changing_creation(self):
        self.client.force_login(self.owner)
        form = self.page('edit/').json()['data']['form']
        self.assertTrue(form['inline_avatar'])
        self.assertEqual(len(form['avatars']), 30)
        self.assertIn('preset_class', form['automatic_avatar'])
        self.assertIn('avatar_photo_crop', {field['name'] for field in form['fields']})
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        target = scoped_workplace_app_path(self.workspace, 'spaces', 'create/')
        create_form = self.client.get(api, {'url': target}).json()['data']['form']
        self.assertNotIn('inline_avatar', create_form)
        self.assertNotIn('avatar', {field['name'] for field in create_form['fields']})

    def test_navigation_uses_page_sidebar_for_every_settings_entry(self):
        self.client.force_login(self.owner)
        for scoped in (True, False):
            base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/') if scoped else f'/space/{self.space.slug}/'
            api = scoped_workplace_app_path(self.workspace, 'api', 'v1/navigation/') if scoped else '/api/v1/navigation/'
            for suffix, tab in [('?view=settings', 'main'), ('edit/', 'main'), ('avatar/', 'main'), ('members/', 'members'),
                                ('configuration/', 'types'), ('configuration/?section=configuration', 'types'),
                                ('configuration/?section=types', 'types'), ('configuration/?section=statuses', 'statuses'),
                                ('configuration/?section=fields', 'types')]:
                with self.subTest(scoped=scoped, suffix=suffix):
                    response = self.client.get(api, {'url': base + suffix}, follow=True)
                    self.assertEqual(response.status_code, 200)
                    shell = response.json()['shell']
                    self.assertEqual(shell['mode'], 'space-settings')
                    self.assertTrue(shell['settings_active'])
                    self.assertEqual(shell['space_settings']['tab'], tab)
                    self.assertEqual([link['key'] for link in shell['space_settings']['links']], ['main', 'members', 'types', 'statuses'])
                    self.assertTrue(all(f'/space/{self.space.slug}/?view=settings#' in link['url'] for link in shell['space_settings']['links']))

    def test_observer_sidebar_has_only_readable_sections(self):
        self.client.force_login(self.observer)
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/navigation/')
        target = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/?view=settings')
        payload = self.client.get(api, {'url': target}).json()
        self.assertEqual([link['key'] for link in payload['shell']['space_settings']['links']], ['main', 'members'])
        self.assertFalse(payload['page']['data']['team']['can_manage'])

    def test_settings_center_lists_only_visible_spaces_in_active_workspace(self):
        hidden = make_space(user=self.owner, workplace=self.workspace, name='Ukryta', visibility='private', private_owner=self.owner)
        foreign = make_space(user=self.owner, workplace=self.other, name='Inny Workspace')
        self.client.force_login(self.observer)
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        response = self.client.get(api, {'url': '/settings/'})
        self.assertEqual(response.status_code, 200)
        spaces = response.json()['data']['spaces']
        self.assertEqual([row['name'] for row in spaces], [self.space.name])
        self.assertTrue(spaces[0]['url'].startswith(scoped_workplace_app_path(self.workspace, 'space')))
        SpaceMembership.objects.filter(space=self.space, user=self.observer).delete()
        self.assertEqual(self.client.get(api, {'url': '/settings/'}).json()['data']['spaces'], [])
        self.assertNotContains(response, hidden.slug)
        self.assertNotContains(response, foreign.slug)

    def test_direct_edit_bootstrap_has_page_sidebar_without_settings_overlay(self):
        self.client.force_login(self.owner)
        target = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/edit/')
        response = self.client.get(target)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-sidebar-navigation="space-settings"')
        self.assertNotContains(response, 'data-work-modal>')
        self.assertNotContains(response, 'aria-labelledby="work-modal-title"')

    def test_guest_with_space_admin_role_gets_only_readable_settings_sections(self):
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.admin).update(role='guest')
        self.client.force_login(self.admin)
        base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/navigation/')
        response = self.client.get(api, {'url': base + '?view=settings'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['page']['read_only'])
        self.assertFalse(payload['page']['data']['can_manage'])
        self.assertFalse(payload['page']['data']['can_configure'])
        self.assertEqual([link['key'] for link in payload['shell']['space_settings']['links']], ['main', 'members'])
        self.assertEqual(self.client.get(api, {'url': base + 'configuration/'}).status_code, 403)

    def test_disabled_spaces_are_absent_from_settings_center_and_cannot_be_opened(self):
        self.workspace.disabled_modules = ['spaces']
        self.workspace.save(update_fields=['disabled_modules'])
        self.client.force_login(self.owner)
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        response = self.client.get(api, {'url': '/settings/'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['spaces'], [])
        target = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/?view=settings')
        self.assertEqual(self.client.get(api, {'url': target}).status_code, 404)

    def test_legacy_form_transport_remains_json_while_page_api_ignores_modal_headers(self):
        self.client.force_login(self.owner)
        base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        values = {'name': '', 'description': 'Zachowany szkic', 'visibility': 'private'}
        legacy = self.client.post(base + 'edit/', values, HTTP_X_WORK_MODAL='true')
        self.assertEqual(legacy.status_code, 400)
        self.assertIn('role="alert"', legacy.json()['html'])
        response = self.client.post(api + '?url=' + base + 'edit/', values, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('html', response.json())
        self.assertEqual(response.json()['data']['space_settings']['tab'], 'main')

    def test_revoked_membership_blocks_stale_settings_forms_and_navigation(self):
        self.client.force_login(self.admin)
        base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        self.assertEqual(self.client.get(api, {'url': base + 'edit/'}).status_code, 200)
        self.admin_membership.delete()
        response = self.client.post(api + '?url=' + base + 'edit/', {
            'name': 'Niedozwolona zmiana', 'description': '', 'visibility': 'private',
        })
        self.assertEqual(response.status_code, 404)
        navigation = scoped_workplace_app_path(self.workspace, 'api', 'v1/navigation/')
        self.assertEqual(self.client.get(navigation, {'url': base + '?view=settings'}).status_code, 404)
        self.space.refresh_from_db()
        self.assertEqual(self.space.name, 'Prywatna')

    def test_settings_first_render_contains_native_forms_without_overlay(self):
        self.client.force_login(self.owner)
        for scoped in (True, False):
            base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/') if scoped else f'/space/{self.space.slug}/'
            for suffix, fields in [
                ('?view=settings', ('name', 'description', 'visibility', 'avatar', 'avatar_photo')),
                ('edit/', ('name', 'description', 'visibility', 'avatar', 'avatar_photo')),
                ('avatar/', ('avatar', 'avatar_photo', 'avatar_photo_crop')),
                ('members/', ('person', 'role')),
            ]:
                with self.subTest(scoped=scoped, suffix=suffix):
                    response = self.client.get(base + suffix, follow=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'data-sidebar-navigation="space-settings"')
                    self.assertContains(response, 'Ustawienia przestrzeni · Prywatna')
                    self.assertNotContains(response, 'aria-labelledby="work-modal-title"')
                    self.assertNotContains(response, 'aria-label="Widoki przestrzeni"')
                    for field in fields:
                        self.assertContains(response, f'name="{field}"')

    def test_native_settings_validation_preserves_values_and_can_be_resubmitted(self):
        self.client.force_login(self.owner)
        base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
        invalid = self.client.post(base + 'edit/', {'name': '', 'description': 'Szkic bez JavaScriptu', 'visibility': 'private'})
        self.assertEqual(invalid.status_code, 400)
        self.assertContains(invalid, 'data-space-settings-form', status_code=400)
        self.assertContains(invalid, 'Szkic bez JavaScriptu', status_code=400)
        self.assertContains(invalid, 'role="alert"', status_code=400)
        response = self.client.post(base + 'edit/', {
            'name': 'Nazwa po zapisie', 'description': 'Szkic bez JavaScriptu', 'visibility': 'private', 'avatar': 'rocket',
        })
        self.assertRedirects(response, base)
        self.space.refresh_from_db()
        self.assertEqual(self.space.name, 'Nazwa po zapisie')
        self.assertEqual(self.space.description, 'Szkic bez JavaScriptu')
        self.assertEqual(self.space.avatar, 'rocket')

    def test_native_sharing_section_is_readable_without_management_access(self):
        self.client.force_login(self.observer)
        base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
        main = self.client.get(base + '?view=settings')
        self.assertNotContains(main, 'data-space-settings-form')
        self.assertContains(main, '?view=settings&amp;section=members#members')
        response = self.client.get(base + '?view=settings&section=members')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Członkowie przestrzeni"')
        self.assertContains(response, self.owner.email)
        self.assertContains(response, self.admin.email)
        self.assertContains(response, self.observer.email)
        self.assertContains(response, 'class="tasks-filter-button" disabled><i data-icon="log-out"')
        self.assertNotContains(response, f'action="{base}members/')
        self.assertNotContains(response, 'data-space-settings-form')
        self.assertEqual(response.context['space_settings_sidebar']['tab'], 'members')

    def test_native_sharing_actions_follow_space_roles(self):
        self.client.force_login(self.admin)
        base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
        response = self.client.get(base + '?view=settings&section=members')
        observer_membership = SpaceMembership.objects.get(space=self.space, user=self.observer)
        self.assertContains(response, f'action="{base}members/{observer_membership.pk}/remove/"')
        self.assertNotContains(response, f'action="{base}members/{self.admin_membership.pk}/remove/"')
        self.assertNotContains(response, f'action="{base}members/owner/remove/"')

    def configuration_values(self, data):
        values = {'revision': data['revision']}
        for group in data['sets']:
            for form in [group['management'], *group['forms']]:
                for field in form['fields']:
                    if field['type'] == 'checkbox':
                        if field['checked']:
                            values[field['name']] = 'on'
                    elif field.get('multiple') and not field['value']:
                        continue
                    else:
                        values[field['name']] = field['value'] or ''
        return values

    def configuration_modal_values(self, response):
        """Read browser-submitted inputs from a type editor and its hidden formsets."""
        values = QueryDict('', mutable=True)

        class Inputs(HTMLParser):
            active = False

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'form':
                    self.active = 'tasks-modal__form' in attrs.get('class', '').split()
                if tag != 'input' or not self.active or not attrs.get('name'):
                    return
                if attrs.get('type') in {'checkbox', 'radio'} and 'checked' not in attrs:
                    return
                if 'disabled' not in attrs:
                    default = 'on' if attrs.get('type') in {'checkbox', 'radio'} else ''
                    values.appendlist(attrs['name'], attrs.get('value', default))

            def handle_endtag(self, tag):
                if tag == 'form':
                    self.active = False

        Inputs().feed(response.content.decode())
        return values

    def test_configuration_lists_show_saved_values_and_api_keeps_all_formsets(self):
        self.client.force_login(self.owner)
        for scoped in (True, False):
            base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/') if scoped else f'/space/{self.space.slug}/'
            api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
            for selected in ('types', 'statuses', 'fields', 'configuration', 'unknown',
                             'fields&remove=0', '&edit=0'):
                with self.subTest(scoped=scoped, selected=selected):
                    target = base + 'configuration/?section=' + selected
                    section = 'statuses' if selected == 'statuses' else 'types'
                    page = self.client.get(api, {'url': target}, follow=True).json()
                    data = page['data']
                    self.assertEqual(data['section'], section)
                    self.assertEqual(data['type_icon_defaults'], ISSUE_TYPE_ICONS)
                    self.assertIsNone(data['editor'])
                    self.assertEqual([group['key'] for group in data['sets']], ['statuses', 'types', 'fields'])
                    self.assertEqual(page['title'], next(group['title'] for group in data['sets'] if group['key'] == section))
                    response = self.client.get(target, follow=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotContains(response, 'class="tasks-modal__form"')
                    self.assertContains(response, f'data-configuration-section="{section}">')
                    for key in ('statuses', 'types', 'fields'):
                        self.assertNotContains(response, f'name="{key}-TOTAL_FORMS"')
                        if key != section:
                            self.assertNotContains(response, f'data-configuration-section="{key}"')
                    if section == 'statuses':
                        self.assertContains(response, 'aria-label="Proces pracy — etapy"')
                        self.assertContains(response, 'work-flow-native-node')
                        self.assertContains(response, 'Dalej:')
                        self.assertNotContains(response, 'role="table"')
                    else:
                        self.assertContains(response, 'role="table"')
                    self.assertNotContains(response, 'Zapisz konfigurację')

    def test_native_configuration_error_keeps_removed_sections_closed(self):
        self.client.force_login(self.owner)
        target = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/configuration/?section=types')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        values = self.configuration_values(self.client.get(api, {'url': target}).json()['data'])
        values['statuses-0-label'] = ''
        values['types-0-label'] = 'Zachowany typ zgłoszenia'
        response = self.client.post(target, values)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context['configuration_section'], 'types')
        self.assertEqual(response.context['editor'], {'section': 'types', 'index': 0, 'remove': False})
        self.assertTrue(response.context['sets'][0]['formset'].forms[0].errors['label'])
        self.assertContains(response, 'Zachowany typ zgłoszenia', status_code=400)
        self.assertTrue(response.context['errors'])
        self.assertContains(response, 'data-configuration-section="types">', status_code=400)
        for key in ('statuses', 'fields'):
            self.assertNotContains(response, f'data-configuration-section="{key}"', status_code=400)
        del values['statuses-TOTAL_FORMS']
        invalid = self.client.post(api, values, QUERY_STRING='url=' + target)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()['data']['section'], 'types')
        self.assertTrue(any('statuses-TOTAL_FORMS' in error for error in invalid.json()['data']['errors']))

    def test_native_type_editor_preserves_hidden_transitions_and_checkbox_values(self):
        self.client.force_login(self.owner)
        config = self.space.configuration
        config.settings['fields'] = [
            {'key': 'estimate', 'label': 'Estymacja', 'type': 'number', 'required': True},
            {'key': 'notes', 'label': 'Uwagi', 'type': 'text', 'required': False},
        ]
        config.save(update_fields=['settings'])
        before = deepcopy(config.settings)
        for scoped in (True, False):
            base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/') if scoped else f'/space/{self.space.slug}/'
            response = self.client.get(base + 'configuration/?section=types&edit=0', follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['editor'], {'section': 'types', 'index': 0, 'remove': False})
            values = self.configuration_modal_values(response)
            self.assertEqual(values['fields-0-required'], 'on')
            self.assertNotIn('fields-1-required', values)
            self.assertFalse(any(name.endswith('-DELETE') for name in values))
            self.assertEqual(values.getlist('statuses-0-transitions'), before['statuses'][0]['transitions'])
            values['types-0-label'] = 'Zmieniony typ'
            save_url = response.context['configuration_url']
            saved = self.client.post(save_url, dict(values.lists()))
            self.assertRedirects(saved, save_url + '#types', fetch_redirect_response=False)
            config.refresh_from_db()
            before['types'][0]['label'] = 'Zmieniony typ'
            self.assertEqual(config.settings, before)

    def test_native_type_editor_uses_settings_layout_and_one_control_per_field(self):
        self.client.force_login(self.owner)
        for scoped in (True, False):
            with self.subTest(scoped=scoped):
                base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/') if scoped else f'/space/{self.space.slug}/'
                response = self.client.get(base + 'configuration/?section=types&edit=0', follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['editor_type_icon'], 'square-check')
                self.assertContains(response, 'app-form-avatar-layout work-type-form')
                self.assertContains(response, 'aria-label="Zmień ikonę typu">Zmień</summary>')
                self.assertNotContains(response, '<details class="work-type-icon-native" open>')
                for name in ('icon', 'label', 'description', 'key'):
                    self.assertContains(response, f'name="types-0-{name}"', count=1)
                self.assertNotContains(response, 'name="types-0-visibility"')
                content = response.content.decode()
                self.assertLess(content.index('name="types-0-label"'), content.index('name="types-0-description"'))
                self.assertLess(content.index('name="types-0-description"'), content.index('name="types-0-key"'))
                removed = self.client.get(base + 'configuration/?section=types&remove=0', follow=True)
                self.assertContains(removed, 'Czy na pewno chcesz usunąć')
                self.assertNotContains(removed, 'work-type-icon-native')

    def test_native_type_editor_keeps_bound_preview_and_reveals_invalid_icon(self):
        self.client.force_login(self.owner)
        target = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/configuration/?section=types')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        before = deepcopy(self.space.configuration.settings)
        values = self.configuration_values(self.client.get(api, {'url': target}).json()['data'])
        values.update({'types-0-label': '', 'types-0-description': 'Niezapisany opis', 'types-0-icon': 'target'})
        response = self.client.post(target, values)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context['editor_type_icon'], 'target')
        self.assertContains(response, 'Niezapisany opis', status_code=400)
        self.assertContains(response, 'name="types-0-icon"', count=1, status_code=400)
        values['types-0-icon'] = '<svg onload="alert(1)">'
        response = self.client.post(target, values)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context['editor_type_icon'], 'square-check')
        self.assertContains(response, '<details class="work-type-icon-native" open>', status_code=400)
        self.assertContains(response, 'id="id_types-0-icon_error"', status_code=400)
        self.assertNotContains(response, 'data-icon="<svg', status_code=400)
        self.space.configuration.refresh_from_db()
        self.assertEqual(self.space.configuration.settings, before)

    def test_native_type_add_and_remove_change_only_the_requested_row(self):
        self.client.force_login(self.owner)
        base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
        original = deepcopy(self.space.configuration.settings)
        index = len(original['types'])
        response = self.client.get(base + f'configuration/?section=types&edit={index}')
        self.assertEqual(response.status_code, 200)
        values = self.configuration_modal_values(response)
        values[f'types-{index}-key'] = 'review'
        values[f'types-{index}-label'] = 'Przegląd'
        saved = self.client.post(base + 'configuration/?section=types', dict(values.lists()))
        self.assertEqual(saved.status_code, 302)
        self.space.configuration.refresh_from_db()
        self.assertEqual(self.space.configuration.settings['types'], original['types'] + [{'key': 'review', 'label': 'Przegląd'}])
        response = self.client.get(base + f'configuration/?section=types&remove={index}')
        values = self.configuration_modal_values(response)
        self.assertEqual([name for name in values if name.endswith('-DELETE')], [f'types-{index}-DELETE'])
        self.assertEqual(values[f'types-{index}-DELETE'], 'on')
        removed = self.client.post(base + 'configuration/?section=types', dict(values.lists()))
        self.assertEqual(removed.status_code, 302)
        self.space.configuration.refresh_from_db()
        self.assertEqual(self.space.configuration.settings, original)

    def test_configuration_modal_rejection_keeps_stale_revision_on_every_retry(self):
        self.client.force_login(self.owner)
        target = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/configuration/?section=types')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        values = self.configuration_modal_values(self.client.get(target + '&edit=0'))
        stale_revision = values['revision']
        config = self.space.configuration
        config.settings['types'][0]['label'] = 'Równoległa zmiana'
        config.save(update_fields=['settings'])
        values['types-0-label'] = 'Szkic ze starej wersji'
        for _ in range(2):
            response = self.client.post(target, dict(values.lists()))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.context['revision'], stale_revision)
            values = self.configuration_modal_values(response)
            self.assertEqual(values['revision'], stale_revision)
            self.assertEqual(values['types-0-label'], 'Szkic ze starej wersji')
            self.assertContains(response, 'Konfiguracja zmieniła się', status_code=400)
        response = self.client.post(api, dict(values.lists()), QUERY_STRING='url=' + target)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['data']['revision'], stale_revision)
        self.assertEqual(response.json()['data']['editor'], {'section': 'types', 'index': 0, 'remove': False})
        config.refresh_from_db()
        self.assertEqual(config.settings['types'][0]['label'], 'Równoległa zmiana')

    def test_configuration_section_save_is_atomic_for_all_groups_and_rejects_stale_revision(self):
        self.client.force_login(self.owner)
        target = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/configuration/?section=fields')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        values = self.configuration_values(self.client.get(api, {'url': target}).json()['data'])
        values.update({'statuses-0-label': 'Nowy status', 'types-0-label': 'Nowy typ',
                       'fields-0-key': 'details', 'fields-0-label': 'Dodatkowy opis', 'fields-0-type': 'text'})
        response = self.client.post(api, values, QUERY_STRING='url=' + target)
        self.assertEqual(response.status_code, 200)
        self.assertIn('redirect', response.json())
        self.space.configuration.refresh_from_db()
        saved = self.space.configuration.settings
        self.assertEqual(saved['statuses'][0]['label'], 'Nowy status')
        self.assertEqual(saved['types'][0]['label'], 'Nowy typ')
        self.assertEqual(saved['fields'][0]['key'], 'details')
        values['types-0-label'] = 'Zmiana ze starej wersji'
        stale = self.client.post(api, values, QUERY_STRING='url=' + target)
        self.assertEqual(stale.status_code, 400)
        self.assertEqual(stale.json()['data']['section'], 'types')
        self.assertTrue(stale.json()['data']['errors'])
        self.space.configuration.refresh_from_db()
        self.assertEqual(self.space.configuration.settings, saved)

    def test_type_icon_and_description_round_trip_without_changing_other_configuration(self):
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()
        config = self.space.configuration
        config.settings['types'][1].update(icon='lightbulb', description='Zachowany opis drugiego typu')
        config.save()
        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/') if scoped else f'/space/{self.space.slug}/'
                api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
                target = base + 'configuration/?section=types'
                data = self.client.get(api, {'url': target}).json()['data']
                type_set = next(group for group in data['sets'] if group['key'] == 'types')
                fields = {field['field_name']: field for field in type_set['forms'][0]['fields']}
                self.assertEqual(fields['icon']['type'], 'select')
                choices = {choice['value']: choice for choice in fields['icon']['choices']}
                self.assertEqual(choices['']['icon'], 'square-check')
                self.assertEqual(choices['target']['icon'], 'target')
                self.assertEqual(fields['description']['type'], 'textarea')
                custom_set = next(group for group in data['sets'] if group['key'] == 'fields')
                self.assertFalse({'icon', 'description'} & {field['field_name'] for field in custom_set['forms'][0]['fields']})
                before = deepcopy(config.settings)
                values = self.configuration_values(data)
                values.update({'types-0-icon': 'target', 'types-0-description': 'Planowanie celów zespołu'})
                response = self.client.post(api, values, QUERY_STRING='url=' + target)
                self.assertEqual(response.status_code, 200)
                config.refresh_from_db()
                expected = deepcopy(before)
                expected['types'][0].update(icon='target', description='Planowanie celów zespołu')
                self.assertEqual(config.settings, expected)
                response = self.client.get(target)
                group = next(group for group in response.context['sets'] if group['key'] == 'types')
                self.assertEqual([header['key'] for header in group['headers']], ['key', 'label', 'description'])
                self.assertEqual(group['rows'][0]['cells'][1], {
                    'key': 'label', 'value': expected['types'][0]['label'], 'icon': 'target', 'icon_label': 'Cel',
                })
                self.assertNotContains(response, 'data-column="icon"')
                self.assertContains(response, 'Planowanie celów zespołu')

                values = self.configuration_values(self.client.get(api, {'url': target}).json()['data'])
                values = {name: value for name, value in values.items()
                          if not (name.startswith('types-') and name.endswith(('-icon', '-description')))}
                values['types-0-label'] = 'Zapis starszego klienta'
                self.assertEqual(self.client.post(target, values).status_code, 302)
                config.refresh_from_db()
                expected['types'][0]['label'] = 'Zapis starszego klienta'
                self.assertEqual(config.settings, expected)

                values = self.configuration_values(self.client.get(api, {'url': target}).json()['data'])
                values.update({'types-0-icon': '', 'types-0-description': ''})
                self.assertEqual(self.client.post(api, values, QUERY_STRING='url=' + target).status_code, 200)
                config.refresh_from_db()
                expected['types'][0].pop('icon')
                expected['types'][0].pop('description')
                self.assertEqual(config.settings, expected)

    def test_type_metadata_validation_keeps_draft_and_saved_configuration(self):
        self.client.force_login(self.owner)
        config = self.space.configuration
        before = deepcopy(config.settings)
        target = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/configuration/?section=types')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        for invalid in ({'types-0-icon': '<svg onload="alert(1)">'}, {'types-0-description': 'x' * 501}):
            values = self.configuration_values(self.client.get(api, {'url': target}).json()['data'])
            values.update({'types-0-icon': 'target', 'types-0-description': 'Niezapisany opis', **invalid})
            response = self.client.post(api, values, QUERY_STRING='url=' + target)
            self.assertEqual(response.status_code, 400)
            data = response.json()['data']
            self.assertEqual(data['revision'], values['revision'])
            form = next(group for group in data['sets'] if group['key'] == 'types')['forms'][0]
            fields = {field['name']: field for field in form['fields']}
            invalid_name = next(iter(invalid))
            self.assertTrue(fields[invalid_name]['errors'])
            self.assertEqual(fields['types-0-description']['value'], values['types-0-description'])
            config.refresh_from_db()
            self.assertEqual(config.settings, before)
