import re
from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


class SharedTaskStyleTests(SimpleTestCase):

    def test_project_filter_and_sort_text_matches_description_size(self):
        css_path = finders.find('css/components/tasks.css')

        self.assertIsNotNone(css_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()

        selectors = (
            r'\.tasks-project-query-trigger',
            r'\.tasks-project-query-panel',
            r'\.tasks-project-query-search input',
            r'\.tasks-project-filter-choice',
            r'\.tasks-project-sort-directions button',
            r'\.tasks-project-row-description,\s*\.tasks-section-row-description',
        )
        for selector in selectors:
            with self.subTest(selector=selector):
                rule = re.search(rf'{selector}\s*\{{(?P<body>[^}}]*)\}}', css, re.DOTALL)
                self.assertIsNotNone(rule)
                self.assertIn('font-size: var(--font-size-sm);', rule.group('body'))

    def test_project_sort_fields_stay_inside_a_scrollable_panel_region(self):
        css_path = finders.find('css/components/tasks.css')

        self.assertIsNotNone(css_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()

        open_panel_rule = re.search(
            r'\.tasks-project-sort-builder\.is-open > '
            r'\.tasks-project-sort-panel\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(open_panel_rule)
        self.assertIn('display: flex;', open_panel_rule.group('body'))
        self.assertIn('flex-direction: column;', open_panel_rule.group('body'))

        field_list_rule = re.search(
            r'\.tasks-project-sort-panel \.tasks-project-sort-field-list\s*'
            r'\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(field_list_rule)
        self.assertIn('min-height: 0;', field_list_rule.group('body'))
        self.assertIn('flex: 1 1 auto;', field_list_rule.group('body'))
        self.assertIn('overflow-y: auto;', field_list_rule.group('body'))

        search_rule = re.search(
            r'\.tasks-project-query-search\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(search_rule)
        self.assertIn(
            'flex: 0 0 var(--dropdown-control-height);',
            search_rule.group('body'),
        )

    def test_project_utility_column_tracks_match_fixed_css_width(self):
        js_path = finders.find('js/tasks.js')

        self.assertIsNotNone(js_path)
        with open(js_path, encoding='utf-8') as js_file:
            javascript = js_file.read()

        project_widths = re.search(
            r'const projectColumnDefaultWidths = \{(?P<body>.*?)\n\s*\};',
            javascript,
            re.DOTALL,
        )
        self.assertIsNotNone(project_widths)
        for column in ('select', 'menu', 'action', 'info', 'notes'):
            self.assertRegex(project_widths.group('body'), rf'\b{column}:\s*40,')

    def test_saved_directory_widths_are_limited_to_wide_desktop(self):
        js_path = finders.find('js/tasks.js')

        self.assertIsNotNone(js_path)
        with open(js_path, encoding='utf-8') as js_file:
            javascript = js_file.read()

        self.assertIn("window.matchMedia('(min-width: 1181px)')", javascript)
        self.assertNotIn("window.matchMedia('(min-width: 901px)')", javascript)

    def test_directory_column_reorder_uses_visible_drop_placeholder(self):
        js_path = finders.find('js/tasks.js')
        css_path = finders.find('css/components/tasks.css')

        self.assertIsNotNone(js_path)
        self.assertIsNotNone(css_path)
        with open(js_path, encoding='utf-8') as js_file:
            javascript = js_file.read()
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()

        self.assertIn("placeholder.className = 'tasks-directory-column-placeholder';", javascript)
        self.assertIn('positionColumnDragPlaceholder(event.clientY);', javascript)
        self.assertIn('list.insertBefore(item, placeholder);', javascript)
        self.assertIn('function handleColumnPointerMove(event) {', javascript)
        self.assertIn('moveColumnDragPreview(event.clientX, event.clientY);', javascript)

        placeholder_rule = re.search(
            r'\.tasks-directory-column-placeholder\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(placeholder_rule)
        self.assertIn('border-top: 2px dashed var(--system-accent);', placeholder_rule.group('body'))

    def test_tablet_breakpoints_keep_desktop_table_structure(self):
        tasks_css_path = finders.find('css/components/tasks.css')
        responsive_css_path = finders.find('css/layout/responsive.css')

        self.assertIsNotNone(tasks_css_path)
        self.assertIsNotNone(responsive_css_path)

        with open(tasks_css_path, encoding='utf-8') as css_file:
            tasks_css = css_file.read()
        with open(responsive_css_path, encoding='utf-8') as css_file:
            responsive_css = css_file.read()

        self.assertIn('@media (min-width: 768px) and (max-width: 1180px)', tasks_css)
        self.assertNotIn('@media (max-width: 900px)', tasks_css)
        self.assertRegex(
            tasks_css,
            r'(?s)@media \(min-width: 768px\) and \(max-width: 1180px\) \{'
            r'.*?\.tasks-topbar \{\s*height: auto;',
        )
        fixed_grid_position = tasks_css.index('/* Keep project directory rows and columns fixed;')
        tablet_grid_position = tasks_css.index('/* Tablet keeps the spreadsheet model,')
        self.assertGreater(tablet_grid_position, fixed_grid_position)
        fixed_grid_css = tasks_css[fixed_grid_position:tablet_grid_position]
        project_grid = re.search(
            r'\.tasks-directory-board\.tasks-project-sheet--selectable \{'
            r'(?P<body>.*?)\n\}',
            fixed_grid_css,
            re.DOTALL,
        )
        self.assertIsNotNone(project_grid)
        expected_tracks = (
            '--tasks-project-code-width',
            '--tasks-directory-name-width',
            '--tasks-project-description-width',
            '--tasks-project-priority-width',
            '--tasks-project-start-width',
            '--tasks-project-due-width',
            '--tasks-project-company-width',
            '--tasks-project-responsible-width',
        )
        track_positions = [project_grid.group('body').index(track) for track in expected_tracks]
        self.assertEqual(track_positions, sorted(track_positions))

        all_groups_grid = re.search(
            r'\.tasks-directory-board\.tasks-all-groups-sheet'
            r'\.tasks-section-sheet\.tasks-project-sheet--selectable \{'
            r'(?P<body>.*?)\n\}',
            fixed_grid_css,
            re.DOTALL,
        )
        self.assertIsNotNone(all_groups_grid)
        all_groups_tracks = re.findall(r'var\((--[^)]+)\)', all_groups_grid.group('body'))
        self.assertEqual(len(all_groups_tracks), 20)
        self.assertEqual(
            all_groups_tracks[-7:],
            [
                '--tasks-project-start-width',
                '--tasks-project-status-width',
                '--tasks-project-stage-width',
                '--tasks-project-health-width',
                '--tasks-project-source-width',
                '--tasks-directory-assignee-width',
                '--tasks-directory-date-width',
            ],
        )
        self.assertIn('@media (min-width: 768px) and (max-width: 1180px)', responsive_css)
        self.assertNotIn('@media (min-width: 769px)', responsive_css)

    def test_narrow_project_grid_keeps_utility_columns_aligned(self):
        tasks_css_path = finders.find('css/components/tasks.css')

        self.assertIsNotNone(tasks_css_path)
        with open(tasks_css_path, encoding='utf-8') as css_file:
            tasks_css = css_file.read()

        fixed_grid_position = tasks_css.index('/* Keep project directory rows and columns fixed;')
        tablet_grid_position = tasks_css.index('/* Tablet keeps the spreadsheet model,', fixed_grid_position)
        narrow_grid_position = tasks_css.index('@media (max-width: 767px)', tablet_grid_position)
        narrow_grid_css = tasks_css[narrow_grid_position:tasks_css.index('.tasks-section-card-grid', narrow_grid_position)]
        project_grid = re.search(
            r'\.tasks-directory-board\.tasks-project-sheet--selectable \.tasks-directory-header,'
            r'\s*\.tasks-directory-board\.tasks-project-sheet--selectable '
            r'\.tasks-directory-list \.tasks-directory-row \{'
            r'(?P<body>.*?)\n\s*\}',
            narrow_grid_css,
            re.DOTALL,
        )

        self.assertIsNotNone(project_grid)
        self.assertEqual(
            re.findall(r'var\((--[^,)]+)', project_grid.group('body')),
            [
                '--tasks-directory-select-width',
                '--tasks-project-menu-column',
                '--tasks-project-action-width',
                '--tasks-project-info-width',
                '--tasks-project-notes-width',
                '--tasks-project-code-width',
                '--tasks-directory-name-width',
                '--tasks-project-description-width',
                '--tasks-project-priority-width',
                '--tasks-project-start-width',
                '--tasks-project-due-width',
                '--tasks-project-company-width',
                '--tasks-project-responsible-width',
                '--tasks-project-status-width',
                '--tasks-project-stage-width',
                '--tasks-project-health-width',
                '--tasks-project-progress-width',
                '--tasks-project-source-width',
                '--tasks-project-count-width',
                '--tasks-project-count-width',
                '--tasks-project-activity-width',
                '--tasks-directory-date-width',
            ],
        )
        self.assertNotIn('> [data-column="action"]', narrow_grid_css)
        self.assertNotIn('> [data-column="info"]', narrow_grid_css)
        self.assertNotIn('> [data-column="notes"]', narrow_grid_css)

    def test_task_detail_header_template_shows_only_current_task_title(self):
        template_path = Path(__file__).resolve().parents[1] / 'spaces/templates/spaces/task_detail.html'
        with template_path.open(encoding='utf-8') as template_file:
            template = template_file.read()

        breadcrumb = re.search(
            r'<div class="tasks-issue-breadcrumb">(?P<body>.*?)'
            r'\n\s*</div>\n\s*</header>',
            template,
            re.DOTALL,
        )

        self.assertIsNotNone(breadcrumb)
        breadcrumb_html = breadcrumb.group('body')
        self.assertIn('{{ task.title }}', breadcrumb_html)
        self.assertNotIn('task.section', breadcrumb_html)
        self.assertNotIn('task.parent.title', breadcrumb_html)
        self.assertNotIn('tasks-issue-chevron', breadcrumb_html)

    def test_note_author_name_is_bold_despite_global_weight_reset(self):
        css_path = finders.find('css/components/tasks.css')

        self.assertIsNotNone(css_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()
        author_name_rule = re.search(
            r'\.tasks-project-note__meta strong\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(author_name_rule)
        self.assertIn('font-weight: 700 !important;', author_name_rule.group('body'))

    def test_project_note_icon_has_no_border_or_background(self):
        css_path = finders.find('css/components/tasks.css')

        self.assertIsNotNone(css_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()
        note_icon_rule = re.search(
            r'\.tasks-project-note__icon\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(note_icon_rule)
        self.assertIn('border: 0;', note_icon_rule.group('body'))
        self.assertIn('background: transparent;', note_icon_rule.group('body'))

    def test_project_note_edit_input_has_no_border(self):
        css_path = finders.find('css/components/tasks.css')

        self.assertIsNotNone(css_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()
        edit_input_rule = re.search(
            r'\.tasks-project-note__edit-input\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(edit_input_rule)
        self.assertIn('border: 0;', edit_input_rule.group('body'))

    def test_task_detail_header_is_exactly_45_pixels_tall(self):
        css_path = finders.find('css/components/tasks.css')

        self.assertIsNotNone(css_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()

        header_rule = re.search(
            r'\.tasks-issue-header\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(header_rule)
        self.assertIn('height: 45px;', header_rule.group('body'))
        self.assertIn('min-height: 45px;', header_rule.group('body'))
