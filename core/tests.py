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
            ('kanban', 'projects', '', 'Kanban', 'Przestrzenie robocze'),
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

    def test_tasks_sidebar_links_follow_expected_order(self):
        request = SimpleNamespace(
            resolver_match=SimpleNamespace(app_name='tasks', view_name=''),
            user=AnonymousUser(),
        )
        html = render_to_string('core/base.html', {
            'request': request,
            'workplace_app_urls': {},
            'active_view': 'projects',
            'active_contact_status': '',
        })

        subnav_start = html.index('id="sidebar-tasks-subnav"')
        subnav_end = html.index('</div>', subnav_start)
        subnav_html = html[subnav_start:subnav_end]
        positions = [
            subnav_html.index(f'<span>{label}</span>')
            for label in (
                'Wszystkie projekty',
                'Wszystkie grupy',
                'Wszystkie zadania',
                'Moje zadania',
            )
        ]

        self.assertEqual(positions, sorted(positions))

    def test_tasks_sidebar_uses_project_and_group_directory_icons(self):
        request = SimpleNamespace(
            resolver_match=SimpleNamespace(app_name='tasks', view_name=''),
            user=AnonymousUser(),
        )
        html = render_to_string('core/base.html', {
            'request': request,
            'workplace_app_urls': {},
            'active_view': 'projects',
            'active_contact_status': '',
        })

        subnav_start = html.index('id="sidebar-tasks-subnav"')
        subnav_end = html.index('</div>', subnav_start)
        subnav_html = html[subnav_start:subnav_end]

        self.assertIn('data-icon="briefcase-business"', subnav_html)
        self.assertIn('data-icon="layers-3"', subnav_html)
        self.assertNotIn('data-icon="folders"', subnav_html)
        self.assertNotIn('data-icon="folder-open"', subnav_html)

        favorite_icons = {
            item['key']: item['icon']
            for item in SIDEBAR_FAVORITE_DEFINITIONS
        }
        self.assertEqual(favorite_icons['tasks-projects'], 'briefcase-business')
        self.assertEqual(favorite_icons['tasks-groups'], 'layers-3')

    def test_contacts_sidebar_does_not_include_people_search(self):
        request = SimpleNamespace(
            resolver_match=SimpleNamespace(app_name='contacts', view_name=''),
            user=AnonymousUser(),
        )
        html = render_to_string('core/base.html', {
            'request': request,
            'workplace_app_urls': {},
            'active_view': '',
            'active_contact_status': 'users',
        })

        contacts_subnav_start = html.index('id="sidebar-contacts-subnav"')
        contacts_subnav_end = html.index('</div>', contacts_subnav_start)
        contacts_subnav_html = html[contacts_subnav_start:contacts_subnav_end]

        self.assertNotIn('Szukaj osób', contacts_subnav_html)
        self.assertNotIn('contacts-people', contacts_subnav_html)
        self.assertIn('>Kontakty</span>', contacts_subnav_html)
        self.assertIn('>Firmy</span>', contacts_subnav_html)
        self.assertIn('>Goście</span>', contacts_subnav_html)

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
        tasks_position = html.index('data-sidebar-group="tasks"')

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
        collapse_group_position = html.index('class="sidebar-view-switcher sidebar-view-switcher--collapse"')
        collapse_position = html.index('data-sidebar-collapse-toggle')
        navigation_position = html.index('class="sidebar-navigation"')

        self.assertLess(header_position, controls_position)
        self.assertLess(controls_position, switcher_position)
        self.assertLess(switcher_position, search_position)
        self.assertLess(search_position, collapse_group_position)
        self.assertLess(collapse_group_position, collapse_position)
        self.assertLess(collapse_position, navigation_position)
        switcher_end = html.index('</div>', switcher_position)
        switcher_html = html[switcher_position:switcher_end]
        collapse_group_end = html.index('</div>', collapse_group_position)
        collapse_group_html = html[collapse_group_position:collapse_group_end]

        self.assertIn('aria-label="Widok domyślny, powiadomienia i wyszukiwanie"', html)
        self.assertEqual(switcher_html.count('class="sidebar-view-switcher__item'), 3)
        self.assertIn('data-icon="house"', html[switcher_position:])
        self.assertIn('data-icon="bell"', html[switcher_position:])
        self.assertIn('data-icon="search"', switcher_html)
        self.assertIn('aria-label="Widok domyślny"', html[switcher_position:])
        self.assertIn('data-sidebar-default-view', switcher_html)
        self.assertIn('aria-label="Powiadomienia"', html[switcher_position:])
        self.assertIn('aria-label="Wyszukaj w Ancore"', switcher_html)
        self.assertIn('href="/notifications/"', html[switcher_position:])
        self.assertIn('data-notifications-toggle', html[switcher_position:])
        self.assertIn('aria-controls="notifications-panel"', html[switcher_position:])
        self.assertIn('role="group" aria-label="Sterowanie paskiem bocznym"', collapse_group_html)
        self.assertEqual(collapse_group_html.count('class="sidebar-view-switcher__item'), 1)
        self.assertIn('class="sidebar-view-switcher__item sidebar-collapse-toggle"', collapse_group_html)
        self.assertIn('id="notifications-panel"', html)
        self.assertIn('data-notifications-url="/notifications/"', html)
        self.assertIn('Zamknij powiadomienia', html)
        self.assertNotIn('disabled', html[switcher_position:navigation_position])

    def test_sidebar_view_switcher_uses_turquoise_active_state(self):
        css_path = finders.find('css/style.css')

        self.assertIsNotNone(css_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()

        self.assertIn(
            '.sidebar-view-switcher__item.is-active {\n'
            '    --app-text-color: var(--text-primary);\n\n'
            '    background: color-mix(in srgb, var(--system-accent) 15%, #ffffff);\n'
            '    color: var(--app-text-color);\n'
            '}',
            css,
        )
        self.assertIn('.sidebar-view-switcher__item:not(.sidebar-collapse-toggle):not(.is-active):hover {', css)
        self.assertIn('.sidebar-view-switcher {\n    width: 106px;\n    height: 42px;', css)
        self.assertIn(
            '.sidebar-view-switcher--collapse {\n'
            '    width: 42px;\n'
            '    justify-content: center;',
            css,
        )
        self.assertIn(
            '.sidebar-view-switcher--collapse .sidebar-view-switcher__item {\n'
            '    width: 32px;\n'
            '    flex-basis: 32px;\n'
            '}',
            css,
        )
        self.assertIn(
            '.sidebar-view-switcher.sidebar-view-switcher--collapse .sidebar-collapse-toggle:hover,\n'
            '.sidebar-view-switcher.sidebar-view-switcher--collapse .sidebar-collapse-toggle[aria-expanded="true"] {\n'
            '    border-color: transparent;\n'
            '    background: transparent;',
            css,
        )
        self.assertIn(
            '.sidebar-collapse-toggle svg {\n'
            '    width: var(--sidebar-icon-size);\n'
            '    height: var(--sidebar-icon-size);\n'
            '}',
            css,
        )
        self.assertIn(
            '.sidebar.is-searching .sidebar-view-switcher:not(.sidebar-view-switcher--collapse) {',
            css,
        )
        self.assertIn(
            'html.sidebar-collapsed .sidebar-view-switcher:not(.sidebar-view-switcher--collapse) {',
            css,
        )

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
        self.assertIn('data-icon="chevron-left"', html)
        self.assertIn('data-icon="chevron-right"', html)

    def test_collapsed_sidebar_keeps_all_navigation_actions_available(self):
        request = SimpleNamespace(
            resolver_match=SimpleNamespace(app_name='', view_name='', url_name=''),
            user=AnonymousUser(),
        )
        html = render_to_string('core/base.html', {
            'request': request,
            'workplace_app_urls': {},
            'active_view': '',
            'active_contact_status': '',
        })

        for label in ('Dashboard', 'Kalendarz', 'Tagi'):
            with self.subTest(label=label):
                link_html = self._sidebar_link_html(html, label)
                self.assertIn(f'aria-label="{label}"', link_html)
                self.assertIn(f'title="{label}"', link_html)

        for group_name in ('Zadania', 'Kanban', 'Kontakty'):
            with self.subTest(group=group_name):
                self.assertIn(f'data-sidebar-group-label="{group_name}"', html)

        self.assertIn('id="sidebar-collapsed-flyout"', html)
        self.assertIn('data-sidebar-collapsed-flyout-title', html)
        self.assertIn('data-sidebar-collapsed-flyout-links', html)
        self.assertIn('data-sidebar-collapsed-flyout-close', html)

        css_path = finders.find('css/style.css')
        js_path = finders.find('js/layout.js')
        self.assertIsNotNone(css_path)
        self.assertIsNotNone(js_path)

        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()
        with open(js_path, encoding='utf-8') as js_file:
            js = js_file.read()

        self.assertIn(
            'html.sidebar-collapsed .sidebar-view-switcher:not(.sidebar-view-switcher--collapse) {\n'
            '        height: 106px;\n'
            '        display: inline-flex;',
            css,
        )
        self.assertIn('        gap: 0;', css)
        self.assertIn(
            'html.sidebar-collapsed .sidebar-view-switcher__item {\n'
            '        width: 32px;\n'
            '        height: 32px;\n'
            '        flex: 0 0 32px;\n'
            '        padding: 0;\n'
            '        border: 0;\n'
            '        border-radius: 999px;\n'
            '        background: transparent;',
            css,
        )
        self.assertIn(
            'html.sidebar-collapsed .sidebar-view-switcher {\n'
            '        width: 42px;\n'
            '        height: 42px;\n'
            '        padding: 3px;\n'
            '        border: 2px solid #e9eaec;\n'
            '        border-radius: 21px;\n'
            '        background: #ffffff;',
            css,
        )
        self.assertIn(
            'html.sidebar-collapsed .sidebar-view-switcher__item.is-active {\n'
            '        background: color-mix(in srgb, var(--system-accent) 15%, #ffffff);',
            css,
        )
        self.assertIn(
            'html.sidebar-collapsed .sidebar-view-switcher__item:not(.sidebar-collapse-toggle):not(.is-active):hover {',
            css,
        )
        self.assertIn(
            'html.sidebar-collapsed .sidebar-view-switcher--collapse .sidebar-view-switcher__item {\n'
            '        width: 32px;\n'
            '        flex-basis: 32px;',
            css,
        )
        self.assertIn(
            'html.sidebar-collapsed .sidebar-menu-section--favorites {\n'
            '        display: block;',
            css,
        )
        self.assertIn('html.sidebar-collapsed .sidebar-workspace-switcher {', css)
        self.assertIn(
            'html.sidebar-collapsed .sidebar-workspace-toggle,\n'
            '    html.sidebar-collapsed .sidebar .logo {\n'
            '        gap: 0;',
            css,
        )
        self.assertIn(
            'html.sidebar-collapsed .sidebar-header {\n'
            '        justify-content: flex-start;\n'
            '        padding-inline: var(--sidebar-rail-gutter);',
            css,
        )
        self.assertIn('html.sidebar-is-collapsing .sidebar-workspace-toggle {', css)
        self.assertIn(
            'html.sidebar-collapsed .sidebar-workspace-avatar {\n'
            '        width: var(--sidebar-avatar-size);\n'
            '        height: var(--sidebar-avatar-size);\n'
            '        flex-basis: var(--sidebar-avatar-size);',
            css,
        )
        self.assertIn(
            'html.sidebar-collapsed .sidebar .sidebar-footer .nav-link .sidebar-profile-avatar {\n'
            '        width: var(--sidebar-avatar-size);\n'
            '        height: var(--sidebar-avatar-size);\n'
            '        flex-basis: var(--sidebar-avatar-size);',
            css,
        )
        self.assertIn('function openCollapsedSidebarFlyout(group, focusFirstLink) {', js)
        self.assertIn('if (isSidebarCollapsedMode()) {', js)
        self.assertIn('--sidebar-compact-control-size: 42px;', css)
        self.assertIn('--sidebar-compact-item-height: 36px;', css)
        self.assertIn(
            'html.sidebar-collapsed .sidebar-favorites-list {\n'
            '        gap: 0.125rem;',
            css,
        )
        self.assertIn(
            'min-height: var(--sidebar-compact-item-height);\n'
            '        height: var(--sidebar-compact-item-height);',
            css,
        )
        self.assertIn(
            '.sidebar,\n'
            '.sidebar-collapsed-flyout {\n'
            '    --sidebar-icon-size: 18px;\n'
            '}',
            css,
        )
        self.assertIn('--sidebar-avatar-size: 39px;', css)
        self.assertIn(
            '.sidebar-workspace-toggle {\n'
            '    width: 100%;\n'
            '    min-width: 0;\n'
            '    height: 42px;',
            css,
        )
        self.assertIn(
            '    gap: 0.55rem;\n'
            '    padding: 0 0.35rem 0 var(--sidebar-avatar-inset);\n'
            '    border-radius: 8px;',
            css,
        )
        self.assertIn('padding: 0.625rem var(--sidebar-rail-gutter);', css)
        self.assertIn('--sidebar-rail-gutter: calc(', css)
        self.assertIn('--sidebar-icon-inset: calc(', css)
        self.assertIn('--sidebar-avatar-inset: calc(', css)
        self.assertIn(
            '.sidebar .sidebar-primary-link {\n'
            '    min-height: var(--sidebar-compact-item-height);\n'
            '    height: var(--sidebar-compact-item-height);',
            css,
        )
        self.assertIn(
            '.sidebar-favorite-link {\n'
            '    min-height: var(--sidebar-compact-item-height);\n'
            '    height: var(--sidebar-compact-item-height);',
            css,
        )
        self.assertIn(
            'html.sidebar-collapsed .sidebar .sidebar-primary-link,\n'
            '    html.sidebar-collapsed .sidebar .sidebar-footer .nav-link {\n'
            '        width: 100%;\n'
            '        min-width: 0;',
            css,
        )
        self.assertIn(
            'html.sidebar-is-expanding .sidebar :is(\n'
            '        .nav-label,\n'
            '        .sidebar-workspace-name,\n'
            '        .sidebar-brand-name,\n'
            '        .sidebar-workspace-chevron\n'
            '    ) {',
            css,
        )
        self.assertIn(
            '.sidebar .sidebar-footer .nav-link--profile {\n'
            '    min-height: var(--sidebar-compact-control-size);\n'
            '    height: var(--sidebar-compact-control-size);',
            css,
        )
        self.assertIn('margin-inline: var(--sidebar-rail-gutter);', css)
        self.assertNotIn('--sidebar-compact-avatar-size:', css)
        self.assertIn('background: #eceef1;', css)

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
                self.assertIn('width: var(--sidebar-icon-size);', selector_css)
                self.assertIn('height: var(--sidebar-icon-size);', selector_css)

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
