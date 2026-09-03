from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from .upload_validation import validate_attachment_upload, validate_image_upload


class UploadValidationTests(SimpleTestCase):
    def test_accepts_plain_text_attachment(self):
        uploaded_file = SimpleUploadedFile('notatka.txt', b'tresc', content_type='text/plain')

        self.assertIs(validate_attachment_upload(uploaded_file), uploaded_file)

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

    def test_active_subnav_does_not_activate_primary_link(self):
        cases = (
            ('tasks', 'projects', '', 'Zadania', 'Wszystkie projekty'),
            ('kanban', 'projects', '', 'Kanban', 'Wszystkie przestrzenie'),
            ('contacts', '', 'all', 'Kontakty', 'Kontakty'),
        )

        for app_name, active_view, contact_status, primary_label, subnav_label in cases:
            with self.subTest(app_name=app_name):
                request = SimpleNamespace(
                    resolver_match=SimpleNamespace(app_name=app_name, view_name=''),
                    user=AnonymousUser(),
                )
                html = render_to_string('core/base.html', {
                    'request': request,
                    'workplace_app_urls': {},
                    'active_view': active_view,
                    'active_contact_status': contact_status,
                })

                primary_button = self._sidebar_button_html(html, primary_label)
                if app_name == 'contacts':
                    subnav_marker = '<span>Kontakty</span>'
                    subnav_start = html.index('class="sidebar-subnav"', html.index('id="sidebar-contacts-title"'))
                    subnav_label_start = html.index(subnav_marker, subnav_start)
                    subnav_link_start = html.rfind('<a ', subnav_start, subnav_label_start)
                    subnav_link_end = html.index('>', subnav_link_start) + 1
                    subnav_link = html[subnav_link_start:subnav_link_end]
                else:
                    subnav_link = self._sidebar_link_html(html, subnav_label)

                self.assertNotIn(' active', primary_button)
                self.assertIn(' active', subnav_link)

    def test_sidebar_groups_have_accessible_collapse_controls(self):
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

        self.assertEqual(html.count('data-sidebar-group-toggle'), 3)
        for group_key, group_name in (
            ('tasks', 'Zadania'),
            ('kanban', 'Kanban'),
            ('contacts', 'Kontakty'),
        ):
            with self.subTest(group=group_key):
                self.assertIn(f'data-sidebar-group="{group_key}"', html)
                self.assertIn(f'aria-controls="sidebar-{group_key}-subnav"', html)
                self.assertIn(f'aria-label="Zwiń sekcję {group_name}"', html)
                self.assertIn(f'id="sidebar-{group_key}-subnav"', html)
                button_html = self._sidebar_button_html(html, group_name)
                self.assertIn('sidebar-primary-link sidebar-group-toggle', button_html)
                self.assertNotIn('href=', button_html)

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

        favorites_position = html.index('id="sidebar-favorites-title">Favorites</h2>')
        remove_dropzone_position = html.index('data-sidebar-favorites-remove-dropzone')
        workspace_position = html.index('id="sidebar-workspace-title">Workspace</h2>')
        tasks_position = html.index('data-sidebar-group="tasks"')

        self.assertLess(remove_dropzone_position, favorites_position)
        self.assertLess(favorites_position, workspace_position)
        self.assertLess(workspace_position, tasks_position)
        self.assertIn('Przeciągnij tutaj elementy menu', html)
        self.assertIn('data-sidebar-favorites-dropzone', html)
        self.assertIn('data-sidebar-favorites-remove-dropzone', html)
        self.assertIn('Usuń z Favorites', html)
        self.assertNotIn('data-sidebar-workspace-dropzone', html)

    def test_sidebar_view_switcher_is_below_workspace_header(self):
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

        header_position = html.index('class="sidebar-header"')
        controls_position = html.index('class="sidebar-view-controls"')
        switcher_position = html.index('data-sidebar-view-switcher')
        search_position = html.index('data-global-search-toggle')
        collapse_position = html.index('data-sidebar-collapse-toggle')
        navigation_position = html.index('class="sidebar-navigation"')

        self.assertLess(header_position, controls_position)
        self.assertLess(controls_position, switcher_position)
        self.assertLess(switcher_position, search_position)
        self.assertLess(search_position, collapse_position)
        self.assertLess(collapse_position, navigation_position)
        self.assertIn('aria-label="Widok domyślny i powiadomienia"', html)
        self.assertIn('data-lucide="house"', html[switcher_position:])
        self.assertIn('data-lucide="bell"', html[switcher_position:])
        self.assertIn('aria-label="Widok domyślny"', html[switcher_position:])
        self.assertIn('aria-label="Powiadomienia"', html[switcher_position:])
        self.assertIn('href="/notifications/"', html[switcher_position:])
        self.assertIn('data-notifications-toggle', html[switcher_position:])
        self.assertIn('aria-controls="notifications-panel"', html[switcher_position:])
        self.assertIn('id="notifications-panel"', html)
        self.assertIn('data-notifications-url="/notifications/"', html)
        self.assertIn('Zamknij powiadomienia', html)
        self.assertNotIn('disabled', html[switcher_position:navigation_position])

    def test_tags_is_a_single_standalone_link_below_calendar(self):
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

        calendar_position = html.index('>Kalendarz</span>')
        tags_position = html.index('>Tagi</span>')
        tags_link = self._sidebar_link_html(html, 'Tagi')

        self.assertEqual(html.count('>Tagi</span>'), 1)
        self.assertLess(calendar_position, tags_position)
        self.assertIn('href="/tasks/?view=tags"', tags_link)
        self.assertIn('sidebar-primary-link--standalone', tags_link)

    def test_tags_standalone_link_is_active_on_shared_tags_views(self):
        for app_name in ('tasks', 'workplace_tasks', 'kanban', 'workplace_kanban'):
            with self.subTest(app_name=app_name):
                request = SimpleNamespace(
                    resolver_match=SimpleNamespace(app_name=app_name, view_name=''),
                    user=AnonymousUser(),
                )
                html = render_to_string('core/base.html', {
                    'request': request,
                    'workplace_app_urls': {},
                    'active_view': 'tags',
                    'active_contact_status': '',
                })

                self.assertIn(' active', self._sidebar_link_html(html, 'Tagi'))

    def test_sidebar_header_has_global_search_and_collapse_controls(self):
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

        self.assertIn('data-global-search-toggle', html)
        self.assertIn('id="global-search-panel"', html)
        self.assertIn('data-search-url="/global-search/"', html)
        self.assertIn('aria-modal="true"', html)
        self.assertIn('Szukaj zadań, osób, projektów…', html)
        self.assertNotIn('id="sidebar-quick-search"', html)
        self.assertIn('data-sidebar-collapse-toggle', html)
        self.assertIn('data-lucide="panel-left-close"', html)

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

    def test_sidebar_footer_does_not_include_workspace_link(self):
        request = SimpleNamespace(
            resolver_match=SimpleNamespace(app_name='', view_name=''),
            user=SimpleNamespace(
                is_authenticated=True,
                first_name='Anna',
                last_name='Kowalska',
            ),
        )
        html = render_to_string('core/base.html', {
            'request': request,
            'workplace_app_urls': {},
            'active_view': '',
            'active_contact_status': '',
        })

        footer_start = html.index('class="sidebar-footer"')
        footer_end = html.index('class="sidebar-resizer"', footer_start)
        footer_html = html[footer_start:footer_end]

        self.assertNotIn('nav-link--workplace', footer_html)
        self.assertNotIn('>Workspace</span>', footer_html)
        self.assertIn('>Sticker</span>', footer_html)
        self.assertIn('>Ustawienia</span>', footer_html)
        self.assertIn('>Anna Kowalska</span>', footer_html)
        self.assertNotIn('Profil użytkownika', footer_html)
