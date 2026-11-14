import codecs
from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from workplaces.navigation import SIDEBAR_FAVORITE_DEFINITIONS

from .upload_validation import validate_attachment_upload, validate_image_upload


class UploadValidationTests(SimpleTestCase):
    def test_accepts_plain_text_attachment(self):
        uploaded_file = SimpleUploadedFile('notatka.txt', b'tresc', content_type='text/plain')

        self.assertIs(validate_attachment_upload(uploaded_file), uploaded_file)

    def test_accepts_utf8_and_bom_marked_utf16_text_attachments(self):
        text = 'Nazwa;Opis\r\nPrzykład;Zażółć gęślą jaźń 🙂\r\n'
        contents = [text.encode('utf-8'), text.encode('utf-8-sig'),
                    codecs.BOM_UTF16_LE + text.encode('utf-16-le'),
                    codecs.BOM_UTF16_BE + text.encode('utf-16-be')]
        for extension in ('txt', 'csv'):
            for content in contents:
                with self.subTest(extension=extension, prefix=content[:4]):
                    uploaded = SimpleUploadedFile(f'example.{extension}', content)
                    uploaded.seek(7)
                    self.assertIs(validate_attachment_upload(uploaded), uploaded)
                    self.assertEqual(uploaded.tell(), 7)

    def test_rejects_binary_null_and_incomplete_text_attachments(self):
        contents = [b'text\x00content', b'\xff\xfe\x00\x00', b'\xff\xff\xff\xff',
                    b'\xff\xfea', b'\xff\xfe\x00\xd8', b'\xfe\xff\xd8\x00',
                    b'incomplete\xc4', b'invalid\xc4a']
        for extension in ('txt', 'csv'):
            for content in contents:
                with self.subTest(extension=extension, content=content):
                    with self.assertRaises(ValidationError):
                        validate_attachment_upload(SimpleUploadedFile(f'example.{extension}', content))

    def test_text_sample_may_end_inside_a_character(self):
        contents = [b'a' * 4095 + 'ż'.encode('utf-8') + b'end',
                    codecs.BOM_UTF16_LE + ('a' * 2046 + '🙂end').encode('utf-16-le'),
                    codecs.BOM_UTF16_BE + ('a' * 2046 + '🙂end').encode('utf-16-be')]
        for content in contents:
            with self.subTest(prefix=content[:4]):
                uploaded = SimpleUploadedFile('example.txt', content)
                self.assertIs(validate_attachment_upload(uploaded), uploaded)

    def test_rejects_disallowed_svg_attachment(self):
        uploaded_file = SimpleUploadedFile(
            'payload.svg',
            b'<svg><script>alert(1)</script></svg>',
            content_type='image/svg+xml',
        )

        with self.assertRaises(ValidationError):
            validate_attachment_upload(uploaded_file)

    def test_rejects_spoofed_image_upload(self):
        uploaded_file = SimpleUploadedFile(
            'avatar.png',
            b'<svg><script>alert(1)</script></svg>',
            content_type='image/png',
        )

        with self.assertRaises(ValidationError):
            validate_image_upload(uploaded_file)


class SidebarActiveStateTests(SimpleTestCase):
    @staticmethod
    def _sidebar_link_html(html, label):
        label_start = html.index(f'>{label}</span>')
        link_start = html.rfind('<a ', 0, label_start)
        link_end = html.index('>', link_start) + 1
        return html[link_start:link_end]

    @staticmethod
    def _sidebar_button_html(html, label):
        label_start = html.index(f'>{label}</span>')
        button_start = html.rfind('<button ', 0, label_start)
        button_end = html.index('>', button_start) + 1
        return html[button_start:button_end]

    def test_sidebar_groups_have_accessible_collapse_controls(self):
        request = SimpleNamespace(resolver_match=SimpleNamespace(app_name='', view_name=''), user=AnonymousUser())
        html = render_to_string('core/base.html', {'request': request})
        self.assertEqual(html.count('data-sidebar-group-toggle'), 3)
        for group_key, group_name in (('spaces', 'Przestrzenie'), ('pulpits', 'Pulpity'), ('filters', 'Filtry')):
            with self.subTest(group=group_key):
                self.assertIn(f'data-sidebar-group="{group_key}"', html)
                self.assertIn(f'aria-controls="sidebar-{group_key}-subnav"', html)
                self.assertIn(f'aria-label="Zwiń sekcję {group_name}"', html)
                self.assertIn('sidebar-primary-link sidebar-group-toggle', self._sidebar_button_html(html, group_name))

    def test_retired_task_directories_are_absent_from_sidebar(self):
        request = SimpleNamespace(resolver_match=SimpleNamespace(app_name='filters', url_name='search'), user=AnonymousUser(), GET={})
        html = render_to_string('core/base.html', {'request': request})
        for label in ('Projekty', 'Grupy', 'Zadania', 'Ulubione projekty', 'Szablony projektów', 'Starsze widoki', 'Wszystkie zadania'):
            self.assertNotIn(f'>{label}</span>', html)
        self.assertNotIn('data-sidebar-group="legacy"', html)
        self.assertNotIn('href="/tasks/', html)
        self.assertNotIn('data-sidebar-source-item="tasks-all"', html)
        self.assertIn(' active', self._sidebar_link_html(html, 'Wyszukaj zadania'))
        favorites = {item['key']: item for item in SIDEBAR_FAVORITE_DEFINITIONS}
        self.assertEqual(favorites['tasks-projects']['app'], 'spaces')
        self.assertNotIn('tasks-all', favorites)
        self.assertNotIn('tasks-groups', favorites)
        self.assertNotIn('tasks-my', favorites)

    def test_retired_contact_directories_are_absent_from_sidebar(self):
        request = SimpleNamespace(
            resolver_match=SimpleNamespace(app_name='tasks', url_name='tasks'),
            user=AnonymousUser(),
            GET={},
        )
        html = render_to_string('core/base.html', {'request': request})
        for label in ('Kontakty', 'Firmy', 'Użytkownicy', 'Goście'):
            self.assertNotIn(f'>{label}</span>', html)
        self.assertNotIn('/contacts/', html)
        for label in ('Przestrzenie', 'Wyszukaj zadania', 'Zespoły'):
            self.assertIn(f'>{label}</span>', html)

    def test_sidebar_has_favorites_and_workspace_sections(self):
        request = SimpleNamespace(
            resolver_match=SimpleNamespace(app_name='', view_name=''),
            user=AnonymousUser(),
        )
        html = render_to_string('core/base.html', {
            'request': request,
            'workplace_app_urls': {},
            'active_view': '',
            'active_contact_status': '',
        })

        favorites_section_position = html.index('data-sidebar-favorites-dropzone')
        favorites_position = html.index('id="sidebar-favorites-title"')
        favorites_content_position = html.index('id="sidebar-favorites-content"')
        remove_dropzone_position = html.index('data-sidebar-favorites-remove-dropzone')
        workspace_position = html.index('id="sidebar-workspace-title">Workspace</h2>')
        tasks_position = html.index('data-sidebar-group="spaces"')

        self.assertLess(favorites_position, favorites_content_position)
        self.assertLess(favorites_content_position, remove_dropzone_position)
        self.assertLess(remove_dropzone_position, workspace_position)
        self.assertLess(workspace_position, tasks_position)
        self.assertIn('Przeciągnij tutaj elementy menu', html)
        self.assertIn('data-sidebar-favorites-dropzone', html)
        self.assertIn('data-sidebar-favorites-toggle', html)
        self.assertIn('aria-controls="sidebar-favorites-content"', html)
        self.assertIn('aria-expanded="true"', html[favorites_section_position:workspace_position])
        self.assertIn('id="sidebar-favorites-content"', html)
        self.assertIn('data-sidebar-favorites-remove-dropzone', html)
        self.assertIn('Usuń z Favorites', html)
        self.assertNotIn('data-sidebar-workspace-dropzone', html)

    def test_global_tools_are_in_topbar_and_sidebar_has_no_home_button(self):
        request = SimpleNamespace(
            resolver_match=SimpleNamespace(app_name='', view_name=''),
            user=AnonymousUser(),
        )
        html = render_to_string('core/base.html', {'request': request, 'workplace_app_urls': {}})
        topbar = html[html.index('<header class="app-topbar"'):html.index('<aside class="sidebar"')]
        sidebar = html[html.index('<aside class="sidebar"'):html.index('id="sidebar-collapsed-flyout"')]

        for marker in ('data-global-search-input', 'data-notifications-toggle',
                       'data-sticky-note-toggle', 'aria-label="Ustawienia Ancore"', 'title="Profil użytkownika"'):
            with self.subTest(control=marker):
                self.assertIn(marker, topbar)
                self.assertNotIn(marker, sidebar)
                self.assertEqual(html.count(marker), 1)
        self.assertNotIn('data-sidebar-default-view', html)
        self.assertNotIn('class="sidebar-view-controls"', sidebar)
        for side, marker in (('left', 'data-sidebar-collapse-toggle'), ('right', 'data-right-sidebar-toggle')):
            with self.subTest(panel=side):
                self.assertNotIn(marker, topbar)
                self.assertEqual(html.count(marker), 1)
                self.assertIn(f'class="sidebar-edge-toggle {side}-sidebar-edge-toggle"', html)
                self.assertNotIn(f'data-icon="panel-{side}"', html)
        self.assertNotIn('class="mobile-sidebar-toggle"', html)
        self.assertIn('data-sticky-note-toggle', topbar.split('class="app-topbar__actions"', 1)[1])
        self.assertIn('aria-controls="app-sticky-note"', topbar)
        self.assertIn('data-notifications-url="/notifications/"', html)
        self.assertIn('aria-controls="global-search-panel"', topbar)
        self.assertIn('aria-controls="notifications-panel"', topbar)

    def test_topbar_search_controls_existing_panel_and_sidebar_can_collapse(self):
        request = SimpleNamespace(
            resolver_match=SimpleNamespace(app_name='', view_name=''),
            user=AnonymousUser(),
        )
        html = render_to_string('core/base.html', {
            'request': request,
            'workplace_app_urls': {},
            'active_view': '',
            'active_contact_status': '',
        })

        self.assertIn('data-global-search-input', html)
        self.assertIn('id="global-search-panel"', html)
        self.assertIn('data-search-url="/global-search/"', html)
        self.assertIn('role="combobox" aria-label="Globalne wyszukiwanie"', html)
        self.assertIn('aria-haspopup="dialog"', html)
        self.assertIn('Szukaj zadań, przestrzeni, dokumentów…', html)
        self.assertNotIn('id="sidebar-quick-search"', html)
        self.assertIn('data-sidebar-collapse-toggle', html)
        self.assertIn('class="sidebar-edge-toggle left-sidebar-edge-toggle"', html)
        self.assertNotIn('class="sidebar-collapse-icon', html)

    def test_collapsed_sidebar_keeps_current_navigation_actions_available(self):
        request = SimpleNamespace(resolver_match=SimpleNamespace(app_name='', view_name='', url_name=''), user=AnonymousUser())
        html = render_to_string('core/base.html', {'request': request})
        for label in ('Kalendarz', 'Dysk', 'Dokumenty', 'Zasoby'):
            with self.subTest(label=label):
                link_html = self._sidebar_link_html(html, label)
                self.assertIn(f'aria-label="{label}"', link_html)
                self.assertIn(f'title="{label}"', link_html)
        for group_name in ('Przestrzenie', 'Pulpity'):
            self.assertIn(f'data-sidebar-group-label="{group_name}"', html)
        for marker in ('id="sidebar-collapsed-flyout"', 'data-sidebar-collapsed-flyout-title', 'data-sidebar-collapsed-flyout-links', 'data-sidebar-collapsed-flyout-close'):
            self.assertIn(marker, html)
        self.assertNotIn('data-sidebar-group="legacy"', html)

    def test_sidebar_navigation_icons_share_one_size_in_both_modes(self):
        css_path = finders.find('css/style.css')

        self.assertIsNotNone(css_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()

        self.assertIn('--sidebar-icon-size: 18px;', css)
        self.assertIn(
            '.sidebar .nav-icon {\n'
            '    --nav-icon-size: var(--sidebar-icon-size);\n'
            '    --nav-icon-optical-scale: 1;\n'
            '}',
            css,
        )
        for selector in (
            '.sidebar-view-switcher__item svg',
            '.sidebar-favorite-icon svg',
            '.sidebar-subnav-icon svg',
        ):
            with self.subTest(selector=selector):
                selector_start = css.index(f'{selector} {{')
                selector_end = css.index('}', selector_start)
                selector_css = css[selector_start:selector_end]
                token = '--sidebar-subnav-icon-size' if selector == '.sidebar-subnav-icon svg' else '--sidebar-icon-size'
                self.assertIn(f'width: var({token});', selector_css)
                self.assertIn(f'height: var({token});', selector_css)

        self.assertIn(
            'html.sidebar-collapsed .sidebar-favorite-icon,\n'
            '    html.sidebar-collapsed .sidebar-favorite-icon svg {\n'
            '        width: var(--sidebar-icon-size);\n'
            '        height: var(--sidebar-icon-size);',
            css,
        )

    def test_sidebar_subnav_labels_stay_on_one_line(self):
        css_path = finders.find('css/style.css')

        self.assertIsNotNone(css_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()

        selector = '.sidebar .sidebar-subnav-link > span:not(.sidebar-subnav-icon)'
        selector_start = css.index(f'{selector} {{')
        selector_end = css.index('}', selector_start)
        selector_css = css[selector_start:selector_end]

        self.assertIn('min-width: 0;', selector_css)
        self.assertIn('overflow: hidden;', selector_css)
        self.assertIn('text-overflow: ellipsis;', selector_css)
        self.assertIn('white-space: nowrap;', selector_css)

        link_selector_start = css.index('.sidebar .sidebar-subnav-link {')
        link_selector_end = css.index('}', link_selector_start)
        link_selector_css = css[link_selector_start:link_selector_end]
        self.assertIn('padding: 0 0.35rem 0 0.65rem;', link_selector_css)

    def test_sidebar_has_accessible_resize_control(self):
        request = SimpleNamespace(
            resolver_match=SimpleNamespace(app_name='', view_name=''),
            user=AnonymousUser(),
        )
        html = render_to_string('core/base.html', {
            'request': request,
            'workplace_app_urls': {},
            'active_view': '',
            'active_contact_status': '',
        })

        self.assertIn('data-sidebar-resizer', html)
        self.assertIn('role="separator"', html)
        self.assertIn('aria-orientation="vertical"', html)
        self.assertIn('aria-label="Zmień szerokość menu bocznego"', html)
        self.assertIn('aria-valuemin="220"', html)
        self.assertIn('aria-valuemax="420"', html)
        self.assertIn('tabindex="0"', html)

    def test_sidebar_has_no_empty_footer_after_tools_move_to_topbar(self):
        request = SimpleNamespace(resolver_match=SimpleNamespace(app_name='', view_name=''), user=AnonymousUser())
        html = render_to_string('core/base.html', {'request': request, 'workplace_app_urls': {}, 'active_view': '', 'active_contact_status': ''})
        sidebar = html[html.index('<aside class="sidebar"'):html.index('id="sidebar-collapsed-flyout"')]
        self.assertNotIn('class="sidebar-footer"', sidebar)
        self.assertIn('data-sidebar-resizer', sidebar)
