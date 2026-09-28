import importlib
import json
import re
import tempfile
from datetime import date, datetime, timedelta, timezone as datetime_timezone
from pathlib import Path
from unittest.mock import patch

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.contenttypes.models import ContentType
from django.contrib.staticfiles import finders
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.models import Case, Count, IntegerField, Value, When
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.urls import reverse

from contacts.models import Company, SharedItem
from .models import Task, TaskActivity, TaskAttachment, TaskProject, TaskProjectFieldOption, TaskProjectNote, TaskSection, TaskSectionNote, TaskTag, TaskTagNote


class TaskProjectControlStyleTests(SimpleTestCase):
    def test_checked_project_row_uses_turquoise_highlight(self):
        css_path = finders.find('css/components/tasks.css')
        theme_path = finders.find('css/theme/elestio.css')

        self.assertIsNotNone(css_path)
        self.assertIsNotNone(theme_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()
        with open(theme_path, encoding='utf-8') as theme_file:
            theme = theme_file.read()

        checked_row_rule = re.search(
            r'\.tasks-project-sheet \.tasks-directory-list '
            r'\.tasks-directory-row\.checked,.*?'
            r'\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(checked_row_rule)
        self.assertIn(
            'background: rgba(var(--system-accent-rgb), 0.08);',
            checked_row_rule.group('body'),
        )
        self.assertIn(
            'border-color: rgba(var(--system-accent-rgb), 0.24);',
            checked_row_rule.group('body'),
        )

        theme_checked_row_rule = re.search(
            r'\.tasks-directory-board \.tasks-directory-list '
            r'\.tasks-directory-row:is\(\.checked, :has\(\.tasks-row-checkbox:checked\)\),.*?'
            r'\{(?P<body>[^}]*)\}',
            theme,
            re.DOTALL,
        )
        self.assertIsNotNone(theme_checked_row_rule)
        self.assertIn(
            'background: color-mix(in srgb, var(--system-accent) 8%, #ffffff);',
            theme_checked_row_rule.group('body'),
        )
        self.assertIn(
            'border-color: var(--contacts-directory-column-separator, var(--tasks-directory-column-separator, #edf0f3));',
            theme_checked_row_rule.group('body'),
        )

        checked_accent_rule = re.search(
            r'\.tasks-directory-board:is\(\.tasks-project-sheet, \.tasks-tag-sheet\) '
            r'\.tasks-directory-list \.tasks-directory-row:is\('
            r'\.checked, :has\(\.tasks-row-checkbox:checked\)\)::after '
            r'\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(checked_accent_rule)
        self.assertIn('opacity: 1;', checked_accent_rule.group('body'))

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

    def test_tags_directory_uses_the_same_compact_grid_as_projects(self):
        tasks_css_path = finders.find('css/components/tasks.css')

        self.assertIsNotNone(tasks_css_path)
        with open(tasks_css_path, encoding='utf-8') as css_file:
            tasks_css = css_file.read()

        tag_grid_position = tasks_css.index('.tasks-directory-board.tasks-tag-sheet {', tasks_css.index('/* Keep project directory rows'))
        tag_grid_css = tasks_css[tag_grid_position:]
        self.assertRegex(
            tag_grid_css,
            r'(?s)\.tasks-directory-board\.tasks-tag-sheet \{'
            r'.*?--tasks-directory-column-separator:\s*#edf0f3;'
            r'.*?--tasks-project-row-height:\s*35px;',
        )
        self.assertRegex(
            tag_grid_css,
            r'(?s)\.tasks-directory-board\.tasks-tag-sheet \.tasks-directory-header \{'
            r'.*?min-height:\s*35px;'
            r'.*?border-bottom-color:\s*var\(--tasks-directory-column-separator\);',
        )
        self.assertRegex(
            tag_grid_css,
            r'(?s)@media \(min-width: 768px\) and \(max-width: 1180px\) \{'
            r'.*?\.tasks-directory-board\.tasks-tag-sheet \{'
            r'.*?--tasks-directory-tag-name-width:\s*220px;'
            r'.*?--tasks-directory-tag-code-width:\s*132px;',
        )

    def test_task_detail_header_template_shows_only_current_task_title(self):
        template_path = Path(__file__).resolve().parent / 'templates/tasks/view_task.html'
        with template_path.open(encoding='utf-8') as template_file:
            template = template_file.read()

        breadcrumb = re.search(
            r'<div class="tasks-issue-breadcrumb">(?P<body>.*?)'
            r'\n\s*</div>\n\n\s*<div class="tasks-issue-actions">',
            template,
            re.DOTALL,
        )

        self.assertIsNotNone(breadcrumb)
        breadcrumb_html = breadcrumb.group('body')
        self.assertIn('{{ task.title }}', breadcrumb_html)
        self.assertNotIn('task.section', breadcrumb_html)
        self.assertNotIn('task.parent.title', breadcrumb_html)
        self.assertNotIn('tasks-issue-chevron', breadcrumb_html)

    def test_project_note_create_updates_only_notes_thread(self):
        js_path = finders.find('js/tasks.js')

        self.assertIsNotNone(js_path)
        with open(js_path, encoding='utf-8') as js_file:
            javascript = js_file.read()

        submit_handler = re.search(
            r"projectNotesForm\.addEventListener\('submit', async event => \{"
            r"(?P<body>.*?)"
            r"\n        \}\);\n    \}\n\n    projectNotesModal\?\.addEventListener\('click'",
            javascript,
            re.DOTALL,
        )
        self.assertIsNotNone(submit_handler)
        handler_body = submit_handler.group('body')
        self.assertIn('event.preventDefault();', handler_body)
        self.assertIn("projectNotesForm.getAttribute('action') || window.location.href", handler_body)
        self.assertNotIn('projectNotesForm.action', handler_body)
        self.assertIn('await fetch(', handler_body)
        self.assertIn("'Accept': 'application/json'", handler_body)
        self.assertIn('await response.json()', handler_body)
        self.assertIn('appendProjectNote(payload.note_html, projectId)', handler_body)
        self.assertIn('syncProjectNotesIndicator(projectId)', handler_body)
        self.assertNotIn('location.reload', handler_body)

        indicator_sync = re.search(
            r'function syncProjectNotesIndicator\(projectId\) \{(?P<body>.*?)\n    \}',
            javascript,
            re.DOTALL,
        )
        self.assertIsNotNone(indicator_sync)
        self.assertIn("window.AncoreIcons.create('file-text')", indicator_sync.group('body'))
        self.assertIn("currentIcon.replaceWith(populatedIcon)", indicator_sync.group('body'))

    def test_note_edit_updates_modal_without_page_reload(self):
        js_path = finders.find('js/tasks.js')

        self.assertIsNotNone(js_path)
        with open(js_path, encoding='utf-8') as js_file:
            javascript = js_file.read()

        edit_handler = re.search(
            r'async function submitNoteEdit\(form, config\) \{(?P<body>.*?)\n    \}',
            javascript,
            re.DOTALL,
        )
        self.assertIsNotNone(edit_handler)
        handler_body = edit_handler.group('body')
        self.assertIn("form.getAttribute('action') || window.location.href", handler_body)
        self.assertIn("'X-Requested-With': 'XMLHttpRequest'", handler_body)
        self.assertIn("'Accept': 'application/json'", handler_body)
        self.assertIn('body: new FormData(form)', handler_body)
        self.assertIn('updateEditedNote(item, form, payload, config.messageSelector)', handler_body)
        self.assertNotIn('location.reload', handler_body)

        for selector in (
            "formSelector: '[data-project-note-edit-form]'",
            "formSelector: '[data-section-note-edit-form]'",
            "formSelector: '[data-tag-note-edit-form]'",
        ):
            self.assertIn(selector, javascript)

    def test_project_notes_icon_is_teal_when_notes_exist(self):
        css_path = finders.find('css/components/tasks.css')

        self.assertIsNotNone(css_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()

        populated_notes_rule = re.search(
            r'\.tasks-project-sheet__notes-button\.has-notes\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(populated_notes_rule)
        self.assertIn('--app-text-color: #0f8f8f;', populated_notes_rule.group('body'))
        self.assertIn('color: #0f8f8f !important;', populated_notes_rule.group('body'))

        populated_notes_icon_rule = re.search(
            r'\.tasks-project-sheet__notes-button\.has-notes svg\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(populated_notes_icon_rule)
        self.assertIn('color: #0f8f8f;', populated_notes_icon_rule.group('body'))
        self.assertIn('stroke-width: 2.5;', populated_notes_icon_rule.group('body'))

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

    def test_project_modal_custom_selects_keep_visible_control_styles(self):
        css_path = finders.find('css/components/tasks.css')

        self.assertIsNotNone(css_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()

        project_fields_rule = re.search(
            r'#project-create-form \.tasks-project-create-fields,[^{]*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(project_fields_rule)
        self.assertIn('--tasks-detail-control-border: #dfe3e8;', project_fields_rule.group('body'))
        self.assertIn('--tasks-detail-control-height: 38px;', project_fields_rule.group('body'))
        self.assertIn('--tasks-detail-control-highlight-border: #b8bec8;', project_fields_rule.group('body'))
        self.assertIn(
            '--tasks-detail-control-highlight-shadow: 0 0 0 2px rgba(107, 114, 128, 0.1);',
            project_fields_rule.group('body'),
        )
        self.assertIn(
            '#project-create-form .tasks-project-create-fields .ancore-custom-select__caret',
            css,
        )
        self.assertIn('#project-create-form [data-project-priority-caret]', css)
        self.assertIn(
            '#project-create-form [data-inline-select-dropdown].is-open [data-project-priority-caret]',
            css,
        )

        visible_caret_selectors = [
            '#section-create-form .tasks-project-create-fields .ancore-custom-select__caret,',
            '#tag-create-form .tasks-tag-fields .ancore-custom-select__caret',
            '#issue-create-form .tasks-issue-chip-picker .tasks-picker-chip > i[data-icon="chevron-down"],',
            '#issue-create-form .tasks-issue-dropdown-button::after',
        ]
        for selector in visible_caret_selectors:
            rule = re.search(
                rf'{re.escape(selector)}[^{{]*\{{(?P<body>[^}}]*)\}}',
                css,
                re.DOTALL,
            )
            self.assertIsNotNone(rule, selector)
            self.assertIn('display: block;', rule.group('body'), selector)

        project_priority_highlight_rule = re.search(
            r'#project-create-form \.tasks-project-create-fields '
            r'\.tasks-issue-dropdown-button:hover,[^{]*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(project_priority_highlight_rule)
        self.assertIn(
            'border-color: var(--tasks-detail-control-highlight-border);',
            project_priority_highlight_rule.group('body'),
        )
        self.assertIn(
            'box-shadow: var(--tasks-detail-control-highlight-shadow);',
            project_priority_highlight_rule.group('body'),
        )

        scoped_control_rules = {
            'section-create-form': (
                r'#section-create-form \.tasks-project-create-fields,[^{]*'
                r'\{(?P<body>[^}]*)\}'
            ),
            'tag-create-form': (
                r'#tag-create-form \.tasks-tag-fields '
                r'\{\s*(?P<body>--issue-create-control-height:[^}]*)\}'
            ),
            'issue-create-form': (
                r'#issue-create-form \.tasks-issue-fields '
                r'\{\s*(?P<body>--issue-create-control-height:[^}]*)\}'
            ),
        }
        for form_selector, pattern in scoped_control_rules.items():
            form_rule = re.search(
                pattern,
                css,
                re.DOTALL,
            )
            self.assertIsNotNone(form_rule, form_selector)
            self.assertIn(
                '--tasks-detail-control-highlight-border: #b8bec8;',
                form_rule.group('body'),
                form_selector,
            )
            self.assertIn(
                '--tasks-detail-control-highlight-shadow: 0 0 0 2px rgba(107, 114, 128, 0.1);',
                form_rule.group('body'),
                form_selector,
            )

        tag_select_highlight_rule = re.search(
            r'#tag-create-form \.tasks-tag-fields '
            r'\.ancore-custom-select__button:hover,[^{]*'
            r'\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(tag_select_highlight_rule)
        self.assertIn(
            'box-shadow: var(--tasks-detail-control-highlight-shadow);',
            tag_select_highlight_rule.group('body'),
        )

    def test_project_page_size_toolbar_uses_compact_dropdown(self):
        css_path = finders.find('css/components/tasks.css')

        self.assertIsNotNone(css_path)
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()

        control_rule = re.search(
            r'\.tasks-project-pagination__size-control--toolbar\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(control_rule)
        self.assertIn('--dropdown-menu-width: 132px;', control_rule.group('body'))
        self.assertIn('height: 28px;', control_rule.group('body'))

        toolbar_rule = re.search(
            r'\.tasks-project-pagination--toolbar\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(toolbar_rule)
        self.assertIn('gap: 0;', toolbar_rule.group('body'))
        self.assertIn('border: 1px solid #dfe3e8;', toolbar_rule.group('body'))
        self.assertIn('border-radius: 6px;', toolbar_rule.group('body'))

        toggle_rule = re.search(
            r'\.tasks-project-pagination__size-button--toolbar\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(toggle_rule)
        self.assertIn('width: 132px;', toggle_rule.group('body'))
        self.assertIn('height: 28px;', toggle_rule.group('body'))
        self.assertIn('border: 0;', toggle_rule.group('body'))
        self.assertIn('border-left: 1px solid #dfe3e8;', toggle_rule.group('body'))

        pages_rule = re.search(
            r'\.tasks-project-pagination__pages\.tasks-project-pagination__pages--toolbar\s*'
            r'\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(pages_rule)
        self.assertIn('height: 28px;', pages_rule.group('body'))
        self.assertIn('gap: 0;', pages_rule.group('body'))
        self.assertIn('border: 0;', pages_rule.group('body'))

        value_rule = re.search(
            r'\.tasks-project-pagination__size-value\s*'
            r'\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(value_rule)
        self.assertIn('overflow: hidden;', value_rule.group('body'))
        self.assertIn('white-space: nowrap;', value_rule.group('body'))

        project_filterbar_rule = re.search(
            r'\.tasks-filterbar\.tasks-filterbar--project-directory\s*'
            r'\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(project_filterbar_rule)
        self.assertIn(
            'grid-template-columns: minmax(0, 1fr) auto;',
            project_filterbar_rule.group('body'),
        )

        empty_center_rule = re.search(
            r'\.tasks-filterbar--project-directory '
            r'\.tasks-filterbar-center:empty\s*\{(?P<body>[^}]*)\}',
            css,
            re.DOTALL,
        )
        self.assertIsNotNone(empty_center_rule)
        self.assertIn('display: none;', empty_center_rule.group('body'))


class TaskProjectCreationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='task-user',
            email='task-user@example.com',
            first_name='Task',
            last_name='User',
            password='test-pass-123',
        )
        self.client.force_login(self.user)

    def test_create_project_adds_default_group(self):
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt testowy',
            'section_title': 'Plan wdrożenia',
            'section_code': 'wd',
            'description': 'Opis projektu',
            'code': 'PT',
            'icon': 'star',
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt testowy')
        section = TaskSection.objects.get(project=project)

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.description, 'Opis projektu')
        self.assertIsNone(project.responsible_user)
        self.assertEqual(project.icon, '')
        self.assertEqual(project.code, 'PT')
        self.assertEqual(section.title, 'Plan wdrożenia')
        self.assertEqual(section.code, 'WD')
        self.assertEqual(section.kind, 'custom')
        self.assertEqual(section.icon, '')
        self.assertEqual(section.order, 0)
        self.assertEqual(section.full_code, f'{project.code}/{section.code}')

    def test_create_project_saves_client_and_responsible_fields(self):
        company = Company.objects.create(owner=self.user, name='Ancore Labs')
        responsible_user = get_user_model().objects.create_user(
            username='responsible-user',
            email='responsible@example.com',
            first_name='Anna',
            last_name='Projektowa',
            password='test-pass-123',
        )
        from workplaces.models import WorkplaceMembership
        from workplaces.services import ensure_default_workplace
        WorkplaceMembership.objects.create(workplace=ensure_default_workplace(self.user), user=responsible_user, role='member')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt z metadanymi',
            'section_title': 'Plan',
            'description': '',
            'priority': 'urgent',
            'due_at': '2026-07-15',
            'company': company.id,
            'responsible_user': responsible_user.id,
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt z metadanymi')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.priority, 'urgent')
        self.assertEqual(project.due_at, date(2026, 7, 15))
        self.assertEqual(project.company, company)
        self.assertEqual(project.responsible_user, responsible_user)

    def test_create_project_modal_shows_project_parameters(self):
        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        modal_start = html.index('id="project-modal"')
        modal_end = html.index('id="project-rename-modal"', modal_start)
        modal_html = html[modal_start:modal_end]

        self.assertContains(response, 'Parametry projektu')
        self.assertContains(response, 'Pierwsza grupa')
        self.assertContains(response, 'aria-label="Wybierz priorytet projektu"')
        self.assertContains(response, 'data-inline-priority-icon')
        self.assertContains(response, 'data-project-priority-caret')
        self.assertContains(response, 'data-inline-select-value="urgent"')
        self.assertContains(response, 'Pilny')
        self.assertContains(response, 'Firma')
        self.assertContains(response, 'data-ancore-custom-select-search="true"')
        self.assertContains(response, 'data-ancore-custom-select-search-placeholder="Szukaj firmy"')
        self.assertContains(response, 'Odpowiedzialny')
        self.assertContains(response, 'data-ancore-custom-select-search-placeholder="Szukaj osoby"')
        self.assertContains(response, 'Status projektu')
        self.assertContains(response, 'Etap')
        self.assertContains(response, 'Kondycja')
        self.assertNotIn('Budżet', modal_html)
        self.assertNotIn('Waluta', modal_html)
        self.assertNotIn('name="budget_amount"', modal_html)
        self.assertNotIn('name="currency"', modal_html)
        self.assertNotContains(response, 'Klient / firma')
        self.assertContains(response, 'Kod projektu')
        self.assertContains(response, 'name="code"')
        self.assertContains(response, 'Kod pierwszej grupy')
        self.assertContains(response, 'name="section_code"')
        self.assertNotContains(response, 'Automatyczny')
        self.assertNotContains(response, 'data-responsible-select-url')
        self.assertNotContains(response, 'Szukaj lub wpisz ID Ancore')

    def test_project_field_settings_seed_defaults_and_render_settings_page(self):
        response = self.client.get(reverse('project_field_settings'))

        self.assertEqual(TaskProjectFieldOption.objects.filter(owner=self.user, is_active=True).count(), 14)
        self.assertNotContains(response, 'data-open-project-field-settings')
        self.assertNotContains(response, 'id="project-field-settings-modal"')
        self.assertTemplateUsed(response, 'dashboard/project_field_settings.html')
        self.assertContains(response, 'Wartości pól projektu')
        self.assertContains(response, 'Status projektu')
        self.assertContains(response, 'Etap')
        self.assertContains(response, 'Kondycja')
        self.assertContains(response, 'name="action" value="create_project_field_option"', count=4)
        self.assertContains(response, 'type="color"')

        projects_response = self.client.get(reverse('tasks:tasks'))
        self.assertNotContains(projects_response, 'data-open-project-field-settings')
        self.assertNotContains(projects_response, 'id="project-field-settings-modal"')
        self.assertRedirects(
            self.client.get(reverse('tasks:tasks'), {'field_settings': '1'}),
            reverse('project_field_settings'),
        )

    def test_custom_project_field_option_can_be_created_and_used_by_project(self):
        create_option_response = self.client.post(reverse('project_field_settings'), {
            'action': 'create_project_field_option',
            'field_type': 'status',
            'label': 'W trakcie QA',
            'color': '#123456',
        })

        option = TaskProjectFieldOption.objects.get(
            owner=self.user,
            field_type='status',
            label='W trakcie QA',
        )
        self.assertRedirects(
            create_option_response,
            reverse('project_field_settings'),
            fetch_redirect_response=False,
        )
        self.assertEqual(option.color, '#123456')

        create_project_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt jakości',
            'section_title': 'Testy',
            'status': option.value,
            'stage': 'implementation',
            'health': 'ok',
        })
        project = TaskProject.objects.get(user=self.user, name='Projekt jakości')

        self.assertRedirects(
            create_project_response,
            f'{reverse("tasks:tasks")}?project={project.id}',
            fetch_redirect_response=False,
        )
        self.assertEqual(project.status, option.value)

        projects_response = self.client.get(reverse('tasks:tasks'))
        self.assertContains(projects_response, 'W trakcie QA')
        self.assertContains(projects_response, '--tasks-project-highlight-bg: #123456;')

    def test_project_field_option_can_be_renamed_and_recolored(self):
        self.client.get(reverse('project_field_settings'))
        option = TaskProjectFieldOption.objects.get(owner=self.user, field_type='health', value='at_risk')

        response = self.client.post(reverse('project_field_settings'), {
            'action': 'update_project_field_option',
            'option_id': option.id,
            'label': 'Wymaga uwagi',
            'color': '#AABBCC',
        })

        option.refresh_from_db()
        self.assertRedirects(
            response,
            reverse('project_field_settings'),
            fetch_redirect_response=False,
        )
        self.assertEqual(option.label, 'Wymaga uwagi')
        self.assertEqual(option.color, '#AABBCC')

    def test_project_field_option_deletion_is_blocked_while_in_use(self):
        self.client.get(reverse('project_field_settings'))
        used_option = TaskProjectFieldOption.objects.get(owner=self.user, field_type='status', value='active')
        unused_option = TaskProjectFieldOption.objects.get(owner=self.user, field_type='status', value='cancelled')
        TaskProject.objects.create(user=self.user, name='Aktywny projekt', status=used_option.value)

        blocked_response = self.client.post(reverse('project_field_settings'), {
            'action': 'delete_project_field_option',
            'option_id': used_option.id,
            'label': used_option.label,
            'color': used_option.color,
        })
        used_option.refresh_from_db()

        self.assertRedirects(
            blocked_response,
            reverse('project_field_settings'),
            fetch_redirect_response=False,
        )
        self.assertTrue(used_option.is_active)

        delete_response = self.client.post(reverse('project_field_settings'), {
            'action': 'delete_project_field_option',
            'option_id': unused_option.id,
            'label': unused_option.label,
            'color': unused_option.color,
        })
        unused_option.refresh_from_db()

        self.assertRedirects(
            delete_response,
            reverse('project_field_settings'),
            fetch_redirect_response=False,
        )
        self.assertFalse(unused_option.is_active)

    def test_edit_project_updates_responsible_field(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', responsible_user=self.user)
        target = get_user_model().objects.create_user(
            username='@outside-contact',
            email='outside@example.com',
            first_name='Osoba',
            last_name='Spoza Kontaktow',
            password='test-pass-123',
        )

        from workplaces.models import WorkplaceMembership
        from workplaces.services import ensure_default_workplace
        WorkplaceMembership.objects.create(workplace=ensure_default_workplace(self.user), user=target, role='member')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Projekt',
            'description': '',
            'priority': 'none',
            'due_at': '',
            'company': '',
            'responsible_user': target.id,
        })

        project.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(project.responsible_user, target)

        response = self.client.get(reverse('tasks:tasks'))
        self.assertContains(response, 'Osoba Spoza Kontaktow')
        self.assertContains(response, 'data-project-responsible-user-id')
        self.assertNotContains(response, 'tasks-responsible-select__avatar')

    def test_projects_search_field_is_in_right_toolbar_and_keeps_filter_form(self):
        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        topbar_start = html.index('class="tasks-topbar')
        topbar_end = html.index('</header>', topbar_start)
        topbar_html = html[topbar_start:topbar_end]
        filterbar_start = html.index('class="tasks-filterbar-right', topbar_end)
        filterbar_end = html.index('data-project-pagination', filterbar_start)
        filterbar_html = html[filterbar_start:filterbar_end]

        self.assertNotIn('tasks-titlebar-search', topbar_html)
        self.assertNotIn('id="filter-search"', topbar_html)
        self.assertIn('<form hidden', topbar_html)
        self.assertIn('data-project-search-form', topbar_html)
        self.assertNotIn('data-filter-search-submit', topbar_html)
        self.assertIn('class="tasks-search-field tasks-project-search"', filterbar_html)
        self.assertNotIn('data-project-search-toggle', filterbar_html)
        self.assertNotIn('projects-search-panel', filterbar_html)
        self.assertIn('id="filter-search"', filterbar_html)
        self.assertIn('form="projects-search-form"', filterbar_html)

    def test_projects_view_uses_unified_filter_builder(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'data-project-filter-builder')
        self.assertContains(response, 'data-project-filter-field="priority"')
        self.assertContains(response, 'data-project-filter-detail="priority"')
        self.assertNotContains(response, 'data-priority-filter-menu')
        self.assertNotContains(response, 'data-status-filter-menu')

    def test_sort_button_exposes_mutable_icon(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'data-task-sort')
        self.assertContains(response, 'data-sort-direction="asc"')
        self.assertContains(response, 'data-icon="arrow-up-narrow-wide"')
        self.assertContains(response, 'data-task-sort-icon')

    def test_projects_view_renders_server_filter_and_sort_controls(self):
        company = Company.objects.create(owner=self.user, name='Acme CRM')
        TaskProject.objects.create(
            user=self.user,
            name='Projekt CRM',
            status='planned',
            stage='offer',
            health='at_risk',
            company=company,
            responsible_user=self.user,
        )
        TaskProject.objects.create(user=self.user, name='Projekt bez firmy')

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'data-project-sort-menu')
        self.assertContains(response, 'data-project-sort-field="priority"')
        self.assertContains(response, 'data-project-sort-direction-choice="desc"')
        self.assertContains(response, 'data-project-filter-builder')
        self.assertContains(response, 'data-project-filter-detail="status"')
        self.assertContains(response, 'data-project-filter-detail="stage"')
        self.assertContains(response, 'data-project-filter-detail="health"')
        self.assertContains(response, 'data-project-filter-detail="company"')
        self.assertContains(response, 'data-project-filter-detail="responsible"')
        self.assertContains(response, 'data-project-filter-detail="name"')
        self.assertContains(response, 'data-project-text-filter-operator-toggle')
        self.assertContains(response, 'data-project-text-filter-operator-list')
        self.assertContains(response, 'data-project-text-filter-operator-option="not_contains"')
        self.assertNotContains(response, '<select data-project-text-filter-operator=')
        self.assertContains(response, 'data-project-filter-input="company"')
        self.assertContains(response, 'placeholder="Szukaj wartości"', count=2)
        self.assertContains(response, 'placeholder="Szukaj pola"')
        self.assertContains(response, 'placeholder="Szukaj pola sortowania"')
        self.assertContains(response, 'data-project-choice-filter-value="none"')
        self.assertContains(response, 'Acme CRM')
        self.assertContains(response, 'Task User')
        self.assertContains(response, 'tasks-project-value-badge--status-planned')
        self.assertContains(response, 'tasks-project-value-badge--status-active')
        self.assertContains(response, 'tasks-project-value-badge--stage-offer')
        self.assertContains(response, 'tasks-project-value-badge--stage-implementation')
        self.assertContains(response, 'tasks-project-value-badge--health-at_risk')
        self.assertContains(response, 'tasks-project-value-badge--health-ok')

    def test_projects_view_filters_searches_and_sorts_on_server(self):
        company = Company.objects.create(owner=self.user, name='Acme CRM')
        responsible = get_user_model().objects.create_user(
            username='project-owner',
            email='owner@example.com',
            first_name='Anna',
            last_name='Kowalska',
            password='test-pass-123',
        )
        matching = TaskProject.objects.create(
            user=self.user,
            name='Oferta CRM',
            code='P-CRM0001',
            status='active',
            stage='offer',
            health='at_risk',
            priority='high',
            company=company,
            responsible_user=responsible,
        )
        TaskProject.objects.create(
            user=self.user,
            name='Projekt wewnętrzny',
            code='P-INT0001',
            status='planned',
            stage='internal',
            health='ok',
            priority='none',
        )

        response = self.client.get(
            reverse('tasks:tasks'),
            {
                'q': 'aktywny',
                'status': 'active',
                'stage': 'offer',
                'health': 'at_risk',
                'company': company.id,
                'responsible': responsible.id,
                'priority': 'high',
            },
        )
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-project-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-project-row tasks-directory-row', count=1)
        self.assertIn(matching.name, table_html)
        self.assertNotIn('Projekt wewnętrzny', table_html)
        self.assertContains(response, 'value="active" data-project-filter-input="status"')
        self.assertContains(response, 'Status:</strong> Aktywny')
        self.assertContains(response, 'Etap:</strong> Oferta')
        self.assertContains(response, 'Kondycja:</strong> Zagrożony')

    def test_projects_view_supports_field_specific_text_operators(self):
        matching = TaskProject.objects.create(
            user=self.user,
            name='Migracja CRM',
            code='P-CRM0001',
            description='Integracja danych klienta',
            source='Polecenie',
        )
        TaskProject.objects.create(
            user=self.user,
            name='Strona firmowa',
            code='P-WEB0001',
            description='',
            source='Formularz',
        )

        response = self.client.get(reverse('tasks:tasks'), {
            'name': 'crm',
            'description': 'archiwum',
            'description_op': 'not_contains',
            'source': 'pole',
        })
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-project-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertIn(matching.name, table_html)
        self.assertNotIn('Strona firmowa', table_html)
        self.assertContains(response, 'name="description_op" value="not_contains"')
        self.assertContains(response, 'Nazwa:</strong> zawiera „crm”')
        self.assertContains(response, 'Opis:</strong> nie zawiera „archiwum”')
        self.assertContains(response, 'Źródło:</strong> zawiera „pole”')

        empty_response = self.client.get(reverse('tasks:tasks'), {'description_op': 'is_empty'})
        empty_html = empty_response.content.decode()
        table_start = empty_html.index('class="tasks-issue-list tasks-project-list')
        table_end = empty_html.index('</section>', table_start)
        table_html = empty_html[table_start:table_end]
        self.assertIn('Strona firmowa', table_html)
        self.assertNotIn(matching.name, table_html)
        self.assertContains(empty_response, 'Opis:</strong> jest puste')

    def test_projects_view_supports_both_sort_directions_for_each_field(self):
        first = TaskProject.objects.create(user=self.user, name='Alfa', code='P-AAA0001', source='A')
        last = TaskProject.objects.create(user=self.user, name='Zeta', code='P-ZZZ0001', source='Z')

        sort_fields = (
            'name',
            'code',
            'description',
            'priority',
            'start_at',
            'due_at',
            'company',
            'responsible',
            'status',
            'stage',
            'health',
            'source',
            'created',
            'activity',
        )
        for field in sort_fields:
            for direction in ('asc', 'desc'):
                with self.subTest(field=field, direction=direction):
                    sort_response = self.client.get(
                        reverse('tasks:tasks'),
                        {'sort': f'{field}_{direction}'},
                    )
                    self.assertEqual(sort_response.status_code, 200)
                    self.assertContains(sort_response, f'data-current-sort-field="{field}"')
                    self.assertContains(sort_response, f'data-current-sort-direction="{direction}"')

        response = self.client.get(reverse('tasks:tasks'), {'sort': 'code_desc'})
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-project-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertLess(table_html.index(last.name), table_html.index(first.name))
        self.assertContains(response, 'data-current-sort-field="code"')
        self.assertContains(response, 'data-current-sort-direction="desc"')
        self.assertContains(response, 'Sortowanie: Kod Z-A')

    def test_projects_view_sort_preserves_query_params_in_pagination(self):
        low = TaskProject.objects.create(user=self.user, name='Niski projekt', priority='low')
        urgent = TaskProject.objects.create(user=self.user, name='Pilny projekt', priority='urgent')
        for index in range(55):
            TaskProject.objects.create(
                user=self.user,
                name=f'Projekt testowy {index:03d}',
                priority='low',
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?sort=priority_desc&page_size=50")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-project-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertLess(table_html.index(urgent.name), table_html.index(low.name))
        self.assertContains(response, 'Sortowanie: Priorytet')
        self.assertContains(response, '<span class="tasks-project-sort-current">Priorytet</span>', html=True)
        self.assertContains(response, 'data-project-page-url="/tasks/?sort=priority_desc&amp;page_size=50&amp;page=2"')

    def test_task_create_modal_does_not_render_removed_task_fields(self):
        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        form_start = html.index('id="issue-create-form"')
        form_end = html.index('</form>', form_start)
        form_html = html[form_start:form_end]

        self.assertNotIn('name="company"', form_html)
        self.assertNotIn('name="contact"', form_html)
        self.assertNotIn('name="contact_channel"', form_html)
        self.assertNotIn('name="is_billable"', form_html)

    def test_all_groups_view_uses_unified_filter_builder(self):
        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")

        self.assertContains(response, 'data-project-filter-builder')
        self.assertContains(response, 'data-project-filter-field="priority"')
        self.assertContains(response, 'data-project-filter-detail="priority"')
        self.assertContains(response, 'placeholder="Szukaj pola"')
        self.assertNotContains(response, 'data-priority-filter-menu')
        self.assertNotContains(response, 'data-status-filter-menu')

    def test_all_groups_view_renders_server_filter_and_sort_controls(self):
        owner = get_user_model().objects.create_user(
            username='group-owner',
            email='group-owner@example.com',
            first_name='Olga',
            last_name='Grupowa',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt grupowy', code='GRP')
        TaskSection.objects.create(
            project=project,
            title='Frontend',
            status='ready',
            kind='milestones',
            owner=owner,
        )
        TaskSection.objects.create(project=project, title='Bez osoby')

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")

        self.assertContains(response, 'data-project-sort-menu')
        self.assertContains(response, 'data-project-sort-value="priority_desc"')
        self.assertContains(response, 'data-project-filter-field="status"')
        self.assertContains(response, 'data-project-filter-field="kind"')
        self.assertContains(response, 'data-project-filter-field="group_project"')
        self.assertContains(response, 'data-project-filter-field="owner"')
        self.assertContains(response, 'data-project-filter-detail="status"')
        self.assertContains(response, 'data-project-filter-detail="kind"')
        self.assertContains(response, 'data-project-filter-detail="group_project"')
        self.assertContains(response, 'data-project-filter-detail="owner"')
        self.assertContains(response, 'data-project-filter-input="group_project"')
        self.assertContains(response, 'placeholder="Szukaj wartości"', count=2)
        self.assertContains(response, 'data-project-choice-filter-empty', count=5)
        self.assertContains(response, 'Projekt grupowy')
        self.assertContains(response, 'Olga Grupowa')
        self.assertContains(response, 'data-project-choice-filter-value="none"')

    def test_all_groups_view_filters_searches_and_sorts_on_server(self):
        owner = get_user_model().objects.create_user(
            username='group-owner',
            email='group-owner@example.com',
            first_name='Olga',
            last_name='Grupowa',
            password='test-pass-123',
        )
        matching_project = TaskProject.objects.create(user=self.user, name='Projekt CRM', code='CRM')
        other_project = TaskProject.objects.create(user=self.user, name='Projekt wewnętrzny', code='INT')
        matching = TaskSection.objects.create(
            project=matching_project,
            title='Kamień CRM',
            description='Gotowy etap wdrożenia',
            status='ready',
            kind='milestones',
            priority='urgent',
            owner=owner,
        )
        TaskSection.objects.create(
            project=other_project,
            title='Backend',
            status='open',
            kind='issues',
            priority='none',
        )

        response = self.client.get(
            reverse('tasks:tasks'),
            {
                'view': 'all-groups',
                'q': 'gotowa',
                'status': 'ready',
                'kind': 'milestones',
                'group_project': matching_project.id,
                'owner': owner.id,
                'priority': 'urgent',
            },
        )
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=1)
        self.assertIn(matching.title, table_html)
        self.assertNotIn('Backend', table_html)
        self.assertContains(response, 'value="ready" data-project-filter-input="status"')
        self.assertContains(response, '<span><strong>Status:</strong> Gotowa</span>', html=True)
        self.assertContains(response, '<span><strong>Typ:</strong> Kamienie milowe</span>', html=True)
        self.assertContains(response, '<span><strong>Projekt:</strong> Projekt CRM</span>', html=True)
        self.assertContains(response, '<span><strong>Odpowiedzialny:</strong> Olga Grupowa</span>', html=True)

    def test_all_groups_view_sort_preserves_query_params_in_pagination(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt grup', code='GRP')
        low = TaskSection.objects.create(project=project, title='Niska grupa', priority='low')
        urgent = TaskSection.objects.create(project=project, title='Pilna grupa', priority='urgent')
        for index in range(55):
            TaskSection.objects.create(
                project=project,
                title=f'Grupa testowa {index:03d}',
                priority='low',
                order=index,
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups&sort=priority_desc&page_size=50")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertLess(table_html.index(urgent.title), table_html.index(low.title))
        self.assertContains(response, 'Sortowanie: Priorytet')
        self.assertContains(response, '<span class="tasks-project-sort-current">Priorytet</span>', html=True)
        self.assertContains(response, 'data-project-page-url="/tasks/?view=all-groups&amp;sort=priority_desc&amp;page_size=50&amp;page=2"')

    def test_tags_view_renders_server_filter_controls(self):
        TaskTag.objects.create(user=self.user, name='Tag właściciela', owner_label='Zespół CRM')
        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags")

        self.assertContains(response, 'data-project-filter-menu="status"')
        self.assertContains(response, 'data-project-filter-menu="category"')
        self.assertContains(response, 'data-project-filter-menu="scope"')
        self.assertContains(response, 'data-project-filter-menu="owner"')
        self.assertContains(response, 'data-project-filter-menu="priority"')
        self.assertContains(response, 'name="status" value="" data-project-filter-input="status"')
        self.assertContains(response, 'name="category" value="" data-project-filter-input="category"')
        self.assertContains(response, 'name="scope" value="" data-project-filter-input="scope"')
        self.assertContains(response, 'name="owner" value="" data-project-filter-input="owner"')
        self.assertContains(response, 'name="priority" value="" data-project-filter-input="priority"')
        self.assertContains(response, 'placeholder="Szukaj właściciela"')
        self.assertContains(response, 'Zespół CRM')
        self.assertNotContains(response, 'data-status-filter-menu')
        self.assertNotContains(response, 'data-priority-filter-menu')

    def test_tags_view_filters_on_server(self):
        matching = TaskTag.objects.create(
            user=self.user,
            name='Ryzyko klienta',
            description='Pilny temat wdrożenia',
            category='risk',
            priority='urgent',
            scope='clients',
            owner_label='Zespół CRM',
            status='archived',
        )
        TaskTag.objects.create(
            user=self.user,
            name='Tag ogólny',
            description='Inny temat',
            category='general',
            priority='low',
            scope='tasks',
            owner_label='Zespół Support',
            status='active',
        )

        response = self.client.get(
            reverse('tasks:tasks'),
            {
                'view': 'tags',
                'q': 'ryzyko',
                'status': 'archived',
                'category': 'risk',
                'scope': 'clients',
                'owner': 'Zespół CRM',
                'priority': 'urgent',
            },
        )
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-tag-sheet__row', count=1)
        self.assertIn(matching.name, table_html)
        self.assertNotIn('Tag ogólny', table_html)
        self.assertContains(response, 'Status: Archiwalny')
        self.assertContains(response, 'Typ: Ryzyko')
        self.assertContains(response, 'Zakres: Klienci')
        self.assertContains(response, 'Właściciel: Zespół CRM')
        self.assertContains(response, 'Priorytet: Krytyczny')

    def test_tags_view_renders_server_sort_controls(self):
        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags")

        self.assertContains(response, 'data-project-sort-menu')
        self.assertContains(response, 'data-project-default-sort="name_asc"')
        self.assertContains(response, 'aria-label="Sortowanie tagów"')
        self.assertContains(response, 'name="sort" value="" data-project-sort-input')
        self.assertContains(response, 'data-project-sort-value="name_desc"')
        self.assertContains(response, 'data-project-sort-value="priority_desc"')
        self.assertContains(response, 'data-project-sort-value="task_count_desc"')
        self.assertContains(response, 'data-project-sort-value="related_desc"')

    def test_tags_view_sorts_by_priority_and_preserves_query_params_in_pagination(self):
        low = TaskTag.objects.create(user=self.user, name='Niski tag', priority='low')
        urgent = TaskTag.objects.create(user=self.user, name='Pilny tag', priority='urgent')
        for index in range(55):
            TaskTag.objects.create(
                user=self.user,
                name=f'Tag testowy {index:03d}',
                priority='low',
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags&sort=priority_desc&page_size=50")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertLess(table_html.index(urgent.name), table_html.index(low.name))
        self.assertContains(response, 'Sortowanie: Priorytet')
        self.assertContains(response, '<span class="tasks-project-sort-current">Priorytet</span>', html=True)
        self.assertContains(response, 'data-project-page-url="/tasks/?view=tags&amp;sort=priority_desc&amp;page_size=50&amp;page=2"')

    def test_tags_view_sorts_by_task_count(self):
        busy = TaskTag.objects.create(user=self.user, name='Aktywny tag')
        quiet = TaskTag.objects.create(user=self.user, name='Cichy tag')
        for index in range(2):
            task = Task.objects.create(user=self.user, title=f'Zadanie aktywne {index}')
            task.tags.add(busy)
        task = Task.objects.create(user=self.user, title='Zadanie ciche')
        task.tags.add(quiet)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags&sort=task_count_desc")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertLess(table_html.index(busy.name), table_html.index(quiet.name))
        self.assertContains(response, 'Sortowanie: Najwięcej zadań')
        self.assertContains(response, '2 zadań')

    def test_projects_priority_column_uses_priority_icons(self):
        project = TaskProject.objects.create(user=self.user, name='Pilny projekt', priority='urgent')

        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        row_start = html.index(f'data-project-id="{project.id}"')
        row_end = html.index('</article>', row_start)
        row_html = html[row_start:row_end]

        self.assertIn('data-column="priority"', row_html)
        self.assertIn('tasks-row-priority priority-urgent', row_html)
        self.assertIn('data-icon="circle-alert"', row_html)
        self.assertNotIn('tasks-project-priority-dot', row_html)

    @patch('tasks.views.tasks.timezone.localdate', return_value=date(2026, 7, 10))
    def test_projects_list_highlights_priority_due_date_and_source(self, _localdate):
        overdue = TaskProject.objects.create(
            user=self.user,
            name='Projekt po terminie',
            priority='urgent',
            due_at=date(2026, 7, 9),
            source='Polecenie',
        )
        soon = TaskProject.objects.create(
            user=self.user,
            name='Projekt z bliskim terminem',
            priority='medium',
            due_at=date(2026, 7, 17),
        )
        scheduled = TaskProject.objects.create(
            user=self.user,
            name='Projekt zaplanowany',
            priority='low',
            due_at=date(2026, 7, 18),
        )
        completed = TaskProject.objects.create(
            user=self.user,
            name='Projekt zakończony',
            status='completed',
            due_at=date(2026, 7, 1),
        )
        cancelled = TaskProject.objects.create(
            user=self.user,
            name='Projekt anulowany',
            status='cancelled',
            due_at=date(2026, 7, 1),
        )

        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-project-list tasks-directory-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        def project_row(project):
            row_start = table_html.index(f'data-project-id="{project.id}"')
            row_end = table_html.index('</article>', row_start)
            return table_html[row_start:row_end]

        overdue_row = project_row(overdue)
        self.assertIn('tasks-project-value-badge--priority-urgent', overdue_row)
        self.assertIn('tasks-project-value-badge--due-overdue', overdue_row)
        self.assertIn('tasks-project-value-badge--source', overdue_row)
        self.assertIn('Polecenie', overdue_row)
        self.assertIn('tasks-project-value-badge--due-soon', project_row(soon))
        self.assertIn('tasks-project-value-badge--due-scheduled', project_row(scheduled))
        self.assertIn('tasks-project-value-badge--due-completed', project_row(completed))
        self.assertIn('tasks-project-value-badge--due-inactive', project_row(cancelled))

    @patch('tasks.views.tasks.timezone.localdate', return_value=date(2026, 7, 10))
    def test_groups_list_highlights_status_kind_priority_and_due_date(self, _localdate):
        project = TaskProject.objects.create(user=self.user, name='Projekt grup')
        blocked = TaskSection.objects.create(
            project=project,
            title='Grupa zablokowana',
            status='blocked',
            kind='milestones',
            priority='urgent',
            due_at=date(2026, 7, 9),
        )
        closed = TaskSection.objects.create(
            project=project,
            title='Grupa zamknięta',
            status='closed',
            due_at=date(2026, 7, 1),
        )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        def group_row(section):
            row_value = f'data-section-id="{section.id}"'
            row_marker = table_html.index(row_value)
            row_start = table_html.rfind('<article', 0, row_marker)
            row_end = table_html.index('</article>', row_marker)
            return table_html[row_start:row_end]

        blocked_row = group_row(blocked)
        self.assertIn('tasks-project-value-badge--group-status-blocked', blocked_row)
        self.assertIn('tasks-project-value-badge--group-kind-milestones', blocked_row)
        self.assertIn('tasks-project-value-badge--priority-urgent', blocked_row)
        self.assertIn('tasks-project-value-badge--due-overdue', blocked_row)
        self.assertIn('tasks-project-value-badge--due-completed', group_row(closed))

    def test_tags_list_highlights_category_priority_scope_and_status(self):
        tag = TaskTag.objects.create(
            user=self.user,
            name='Tag ryzyka',
            category='risk',
            color='#3b82f6',
            icon='layers',
            priority='high',
            scope='projects',
            status='archived',
        )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]
        row_marker = table_html.index(f'data-tag-id="{tag.id}"')
        row_start = table_html.rfind('<article', 0, row_marker)
        row_end = table_html.index('</article>', row_marker)
        row_html = table_html[row_start:row_end]

        self.assertIn('tasks-project-value-badge--tag-category-risk', row_html)
        self.assertIn('tasks-project-value-badge--tag-visual', row_html)
        self.assertIn('style="--tag-color: #3b82f6;"', row_html)
        self.assertIn('data-icon="layers"', row_html)
        self.assertIn('tasks-project-value-badge--priority-high', row_html)
        self.assertIn('tasks-project-value-badge--tag-scope-projects', row_html)
        self.assertIn('tasks-project-value-badge--tag-status-archived', row_html)
        self.assertNotIn('tasks-tag-color-swatch', row_html)

    def test_group_priority_is_rendered_independently_from_project_priority(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt pilny', priority='urgent')
        section = TaskSection.objects.create(project=project, title='Grupa bez priorytetu', priority='none')

        project_response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")
        all_groups_response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")

        for response in (project_response, all_groups_response):
            html = response.content.decode()
            row_start = html.index(f'data-section-id="{section.id}"')
            row_end = html.index('</article>', row_start)
            row_html = html[row_start:row_end]

            self.assertIn('data-column="priority"', row_html)
            self.assertIn('tasks-row-priority priority-none', row_html)
            self.assertNotIn('tasks-row-priority priority-urgent', row_html)
            self.assertNotIn('Pilny', row_html)

    def test_groups_priority_column_uses_section_priority_icons(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', priority='none')
        section = TaskSection.objects.create(project=project, title='Pilna grupa', priority='urgent')

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")
        html = response.content.decode()
        row_start = html.index(f'data-section-id="{section.id}"')
        row_end = html.index('</article>', row_start)
        row_html = html[row_start:row_end]

        self.assertIn('data-column="priority"', row_html)
        self.assertIn('tasks-row-priority priority-urgent', row_html)
        self.assertIn('data-icon="circle-alert"', row_html)
        self.assertIn('Pilny', row_html)

    def test_edit_project_modal_uses_issue_modal_layout(self):
        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        modal_start = html.index('id="project-rename-modal"')
        modal_end = html.index('id="project-notes-modal"', modal_start)
        modal_html = html[modal_start:modal_end]

        self.assertIn('tasks-project-edit-modal', modal_html)
        self.assertIn('tasks-issue-modal__dialog', modal_html)
        self.assertIn('tasks-issue-modal__header', modal_html)
        self.assertIn('tasks-issue-modal__body', modal_html)
        self.assertIn('tasks-issue-modal__footer', modal_html)
        self.assertIn('Parametry projektu', modal_html)
        self.assertIn('aria-label="Wybierz priorytet projektu"', modal_html)
        self.assertIn('data-inline-priority-icon', modal_html)
        self.assertIn('data-project-priority-caret', modal_html)
        self.assertIn('<label for="project-rename-name">Nazwa projektu</label>', modal_html)

    def test_edit_project_modal_matches_create_project_field_layout(self):
        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        modal_start = html.index('id="project-rename-modal"')
        modal_end = html.index('id="project-notes-modal"', modal_start)
        modal_html = html[modal_start:modal_end]

        self.assertIn(
            'class="u-sr-only" id="project-rename-parameters-title"',
            modal_html,
        )

        field_classes = [
            'tasks-project-create-field--code',
            'tasks-project-create-field--company',
            'tasks-project-create-field--responsible',
            'tasks-project-create-field--status',
            'tasks-project-create-field--stage',
            'tasks-project-create-field--health',
            'tasks-project-create-field--priority',
            'tasks-project-create-field--source',
            'tasks-project-create-field--start',
            'tasks-project-create-field--due',
        ]
        field_positions = [modal_html.index(field_class) for field_class in field_classes]

        self.assertEqual(field_positions, sorted(field_positions))
        self.assertNotIn('Budżet', modal_html)
        self.assertNotIn('Waluta', modal_html)
        self.assertNotIn('name="budget_amount"', modal_html)
        self.assertNotIn('name="currency"', modal_html)

    def test_create_project_uses_default_group_name_when_group_name_is_empty(self):
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt z domyślną grupą',
            'section_title': '   ',
            'description': '',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt z domyślną grupą')
        section = TaskSection.objects.get(project=project)

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(section.title, 'Nowa Grupa')

    def test_create_project_leaves_code_blank_when_form_omits_it(self):
        first_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt bez kodu',
            'description': '',
            'icon': '',
        })
        second_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Drugi projekt bez kodu',
            'description': '',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt bez kodu')
        second_project = TaskProject.objects.get(user=self.user, name='Drugi projekt bez kodu')
        section = TaskSection.objects.get(project=project)

        self.assertRedirects(first_response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertRedirects(second_response, f"{reverse('tasks:tasks')}?project={second_project.id}")
        self.assertEqual(project.code, '')
        self.assertEqual(second_project.code, '')
        self.assertEqual(section.code, '')
        self.assertEqual(section.full_code, '')
        self.assertEqual(project.icon, '')

    def test_create_project_rejects_duplicate_manual_code(self):
        TaskProject.objects.create(user=self.user, name='Projekt pierwszy', code='ABC')
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt drugi',
            'description': '',
            'code': 'abc',
            'icon': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taki kod projektu już istnieje.')
        self.assertFalse(TaskProject.objects.filter(user=self.user, name='Projekt drugi').exists())

    def test_project_codes_are_unique_across_users_when_provided(self):
        other_user = get_user_model().objects.create_user(username='other-user', password='test-pass-123')
        TaskProject.objects.create(user=other_user, name='Projekt innej osoby', code='GLOBAL')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Mój projekt',
            'description': '',
            'code': 'global',
            'icon': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taki kod projektu już istnieje.')
        self.assertFalse(TaskProject.objects.filter(user=self.user, name='Mój projekt').exists())

    def test_project_codes_avoid_workspace_codes(self):
        from kanban.models import KanbanProject

        workspace = KanbanProject.objects.create(user=self.user, name='Przestrzeń robocza')
        KanbanProject.objects.filter(pk=workspace.pk).update(code='SPACE')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Mój projekt',
            'description': '',
            'code': 'space',
            'icon': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taki kod projektu już istnieje.')
        self.assertFalse(TaskProject.objects.filter(user=self.user, name='Mój projekt').exists())

    def test_group_codes_keep_hierarchy_and_task_codes_use_task_id(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='P-8K3FQ2A9')
        first_section = TaskSection.objects.create(project=project, title='Frontend', code='FE')
        second_section = TaskSection.objects.create(project=project, title='Backend', code='BE')
        first_task = Task.objects.create(user=self.user, section=first_section, title='Pierwsze zadanie')
        second_task = Task.objects.create(user=self.user, section=first_section, title='Drugie zadanie')
        other_group_task = Task.objects.create(user=self.user, section=second_section, title='Zadanie backendowe')

        self.assertEqual(first_section.code, 'FE')
        self.assertEqual(second_section.code, 'BE')
        self.assertEqual(first_section.full_code, f'{project.code}/FE')
        self.assertEqual(first_task.code, '1')
        self.assertEqual(second_task.code, '2')
        self.assertEqual(other_group_task.code, '3')
        self.assertEqual(first_task.full_code, '1')
        self.assertEqual(other_group_task.full_code, '3')

    def test_legacy_entity_icons_are_not_editable(self):
        for model in (TaskProject, TaskSection):
            with self.subTest(model=model.__name__):
                self.assertFalse(model._meta.get_field('icon').editable)

    def test_legacy_icons_are_absent_from_project_group_and_task_views(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt bez ikon', icon='rocket')
        section = TaskSection.objects.create(project=project, title='Grupa bez ikon', icon='flask-conical')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie bez ikon')
        urls = (
            reverse('tasks:tasks'),
            f"{reverse('tasks:tasks')}?project={project.id}",
            reverse('tasks:task_group', args=[section.id]),
            reverse('tasks:view-task', args=[task.task_id]),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                for marker in (
                    'tasks-project-badge', 'tasks-issue-crumb-icon',
                    'data-project-icon', 'data-section-icon', 'data-picker-icon',
                    'data-task-detail-option-icon', 'data-icon="rocket"',
                    'data-icon="flask-conical"', 'projectIcon', 'sectionIcon', 'projectColor',
                ):
                    self.assertNotContains(response, marker)

    def test_projects_list_does_not_render_icons_next_to_names(self):
        company = Company.objects.create(owner=self.user, name='Acme CRM')
        project = TaskProject.objects.create(
            user=self.user,
            name='Projekt z ikoną',
            description='Opis projektu',
            code='PZI',
            icon='star',
            priority='high',
            due_at=date(2026, 7, 15),
            company=company,
            responsible_user=self.user,
        )
        other_user = get_user_model().objects.create_user(username='project-note-other', password='test-pass-123')
        TaskProjectNote.objects.create(project=project, author=self.user, message='Moja notatka projektu')
        TaskProjectNote.objects.create(project=project, author=other_user, message='Cudza notatka projektu')
        TaskProject.objects.create(user=self.user, name='Projekt bez ikony', code='PBI', icon='')
        section = TaskSection.objects.create(project=project, title='Plan')
        Task.objects.create(user=self.user, section=section, title='Gotowe zadanie', status='closed')
        Task.objects.create(user=self.user, section=section, title='Otwarte zadanie', status='new')
        TaskProject.objects.filter(pk=project.pk).update(
            created_at=datetime(2026, 6, 7, 12, 0, tzinfo=datetime_timezone.utc)
        )

        response = self.client.get(reverse('tasks:tasks'))

        self.assertNotContains(response, 'tasks-project-row-icon')
        self.assertNotContains(response, 'tasks-project-row-icon--fallback')
        self.assertContains(response, '<span class="tasks-row-title-text">Projekt z ikoną</span>', html=True)
        self.assertContains(response, '<span class="tasks-row-title-text">Projekt bez ikony</span>', html=True)
        self.assertContains(response, 'KOD PROJEKTU')
        self.assertContains(response, 'OPIS')
        self.assertContains(response, 'FIRMA')
        self.assertContains(response, 'ODPOWIEDZIALNY')
        self.assertContains(response, 'STATUS')
        self.assertContains(response, 'ETAP')
        self.assertContains(response, 'KONDYCJA')
        self.assertContains(response, 'POSTĘP')
        self.assertContains(response, 'START')
        self.assertContains(response, 'TERMIN')
        self.assertNotContains(response, 'data-column="budget"')
        self.assertContains(response, 'ŹRÓDŁO')
        self.assertContains(response, 'GRUPY')
        self.assertContains(response, 'ZADANIA')
        self.assertContains(response, 'PRIORYTET')
        self.assertContains(response, 'OSTATNIA AKTYWNOŚĆ')
        self.assertNotContains(response, 'KLIENT / FIRMA')
        self.assertNotContains(response, 'ODPOWIEDZIALNY ZA PROJEKT')
        self.assertContains(response, 'aria-label="Edytuj projekt"')
        self.assertContains(response, 'aria-label="Informacje o projekcie"')
        self.assertContains(response, 'aria-label="Notatki projektu"')
        self.assertContains(response, 'Informacje o projekcie')
        self.assertContains(response, 'id="info-selected-project-menu-btn"')
        self.assertContains(response, 'id="notes-selected-project-menu-btn"')
        self.assertContains(response, 'data-open-project-info', count=2)
        self.assertContains(response, 'data-project-notes-icon data-icon="file-text"')
        self.assertContains(response, 'data-project-notes-icon data-icon="file-plus-2"')
        self.assertContains(response, 'data-open-project-notes', count=2)
        self.assertContains(
            response,
            f'class="tasks-project-sheet__edit-button tasks-project-sheet__notes-button has-notes" title="Notatki projektu — zawiera notatkę" aria-label="Notatki projektu {project.name}, zawiera notatkę"',
        )
        self.assertContains(
            response,
            'class="tasks-project-sheet__edit-button tasks-project-sheet__notes-button" title="Notatki projektu" aria-label="Notatki projektu Projekt bez ikony"',
        )
        self.assertContains(response, 'id="project-info-modal"')
        self.assertContains(response, 'id="project-notes-modal"')
        self.assertContains(response, 'name="action" value="add_project_note"')
        self.assertContains(response, 'name="action" value="edit_project_note"')
        self.assertContains(response, 'name="action" value="delete_project_note"')
        self.assertContains(response, 'data-project-notes-message')
        self.assertContains(response, 'tasks-project-notes-list')
        self.assertContains(response, 'tasks-project-notes-compose__input')
        self.assertContains(response, 'tasks-project-note--owned')
        self.assertNotContains(response, 'tasks-project-note--mine')
        self.assertContains(response, 'Moja notatka projektu')
        self.assertContains(response, 'Cudza notatka projektu')
        self.assertContains(response, 'data-project-pagination')
        self.assertContains(response, 'tasks-project-pagination__size-control--toolbar')
        self.assertNotContains(response, 'tasks-project-page-size-menu')
        self.assertNotContains(response, '>Projektów na stronie<')
        self.assertContains(response, 'data-project-page-size-dropdown')
        self.assertContains(response, 'data-project-page-size-toggle')
        self.assertContains(response, 'data-project-page-size')
        self.assertContains(response, 'data-project-page-prev')
        self.assertContains(response, 'data-project-page-next')
        self.assertContains(response, 'tasks-project-pagination__summary--compact')
        for page_size in (10, 25, 50, 100, 150, 200):
            self.assertContains(response, f'data-project-page-size-value="{page_size}"')
        content = response.content.decode()
        expected_columns = [
            'data-column="action" aria-label="Edytuj projekt"',
            'data-column="info" aria-label="Informacje o projekcie"',
            'data-column="notes" aria-label="Notatki projektu"',
            'data-column="project_code">KOD PROJEKTU',
            'data-column="project">PROJEKT',
            'data-column="description">OPIS',
            'data-column="priority">PRIORYTET',
            'data-column="start_at">START',
            'data-column="due_at">TERMIN',
            'data-column="company">FIRMA',
            'data-column="responsible_user">ODPOWIEDZIALNY',
            'data-column="project_status">STATUS',
            'data-column="stage">ETAP',
            'data-column="health">KONDYCJA',
            'data-column="progress">POSTĘP',
            'data-column="source">ŹRÓDŁO',
            'data-column="sections_count">GRUPY',
            'data-column="tasks_count">ZADANIA',
            'data-column="last_activity">OSTATNIA AKTYWNOŚĆ',
            'data-column="created_at">DATA UTWORZENIA',
        ]
        expected_header_icons = [
            ('project_code', 'KOD PROJEKTU', 'hash'),
            ('project', 'PROJEKT', 'briefcase-business'),
            ('description', 'OPIS', 'align-left'),
            ('priority', 'PRIORYTET', 'flag'),
            ('start_at', 'START', 'calendar-range'),
            ('due_at', 'TERMIN', 'calendar-clock'),
            ('company', 'FIRMA', 'building-2'),
            ('responsible_user', 'ODPOWIEDZIALNY', 'user-round'),
            ('project_status', 'STATUS', 'circle-dot'),
            ('stage', 'ETAP', 'milestone'),
            ('health', 'KONDYCJA', 'heart-pulse'),
            ('progress', 'POSTĘP', 'chart-no-axes-column-increasing'),
            ('source', 'ŹRÓDŁO', 'route'),
            ('sections_count', 'GRUPY', 'layers-3'),
            ('tasks_count', 'ZADANIA', 'list-checks'),
            ('last_activity', 'OSTATNIA AKTYWNOŚĆ', 'activity'),
            ('created_at', 'DATA UTWORZENIA', 'calendar-days'),
        ]
        for column, label, icon in expected_header_icons:
            self.assertContains(
                response,
                f'data-column="{column}">{label}<i data-icon="{icon}" aria-hidden="true"></i>',
            )
        column_positions = [content.index(column) for column in expected_columns]
        self.assertEqual(column_positions, sorted(column_positions))
        self.assertEqual(content.count('data-project-note-edit-toggle'), 1)
        self.assertEqual(content.count('name="action" value="delete_project_note"'), 1)
        self.assertContains(response, project.code)
        self.assertContains(response, 'Opis projektu')
        self.assertContains(response, 'Brak opisu')
        self.assertContains(response, '50%')
        self.assertContains(response, '1/2')
        self.assertContains(response, 'Wysoki')
        self.assertContains(response, '15.07.2026')
        self.assertContains(response, 'Acme CRM')
        self.assertContains(response, 'tasks-project-progress-fill')
        self.assertContains(response, 'data-project-priority="high"')
        self.assertContains(response, 'data-project-due-at="2026-07-15"')
        self.assertContains(response, f'data-project-company-id="{company.id}"')
        self.assertContains(response, f'data-project-responsible-user-id="{self.user.id}"')
        self.assertContains(response, 'DATA UTWORZENIA')
        self.assertContains(
            response,
            'data-column="created_at" title="Data utworzenia">07.06.2026 14:00</span>',
        )
        self.assertNotContains(response, '7 cze')
        self.assertContains(response, 'Brak osoby')

    def test_projects_list_shows_group_and_task_totals(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt z licznikami')
        first_section = TaskSection.objects.create(project=project, title='Planowanie')
        second_section = TaskSection.objects.create(project=project, title='Realizacja')
        third_section = TaskSection.objects.create(project=project, title='Odbiór')
        Task.objects.create(user=self.user, section=first_section, title='Analiza')
        Task.objects.create(user=self.user, section=first_section, title='Makiety')
        Task.objects.create(user=self.user, section=second_section, title='Wdrożenie')
        Task.objects.create(user=self.user, section=third_section, title='Akceptacja')

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(
            response,
            '<span class="tasks-project-sheet__count tasks-directory-sheet__cell tasks-project-sheet__cell" data-column="sections_count">3 grupy</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="tasks-project-sheet__count tasks-directory-sheet__cell tasks-project-sheet__cell" data-column="tasks_count">4 zadania</span>',
            html=True,
        )

    def test_project_count_labels_use_polish_plural_forms(self):
        from tasks.views.tasks import _polish_count_label

        self.assertEqual(_polish_count_label(1, 'grupa', 'grupy', 'grup'), '1 grupa')
        self.assertEqual(_polish_count_label(5, 'grupa', 'grupy', 'grup'), '5 grup')
        self.assertEqual(_polish_count_label(12, 'zadanie', 'zadania', 'zadań'), '12 zadań')
        self.assertEqual(_polish_count_label(22, 'zadanie', 'zadania', 'zadań'), '22 zadania')

    def test_projects_view_query_count_does_not_grow_with_task_volume(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt')
        section = TaskSection.objects.create(project=project, title='Plan')
        Task.objects.create(user=self.user, section=section, title='Pierwsze zadanie')

        with CaptureQueriesContext(connection) as baseline_queries:
            response = self.client.get(reverse('tasks:tasks'))

        self.assertEqual(response.status_code, 200)

        for index in range(12):
            Task.objects.create(
                user=self.user,
                section=section,
                title=f'Dodatkowe zadanie {index}',
                status='closed' if index % 2 else 'new',
            )

        with CaptureQueriesContext(connection) as expanded_queries:
            response = self.client.get(reverse('tasks:tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(expanded_queries), len(baseline_queries) + 1)

    def test_paginated_status_groups_batch_status_counts(self):
        from tasks.views.tasks import _status_groups_for_tasks

        project = TaskProject.objects.create(user=self.user, name='Projekt')
        section = TaskSection.objects.create(project=project, title='Plan')
        for index, status in enumerate(('new', 'new', 'in_progress', 'closed'), start=1):
            Task.objects.create(
                user=self.user,
                section=section,
                title=f'Zadanie {index}',
                status=status,
            )

        request = RequestFactory().get(f"{reverse('tasks:tasks')}?view=all-tasks")
        request.user = self.user
        queryset = Task.objects.filter(user=self.user, parent__isnull=True).annotate(
            is_closed_sort=Case(
                When(status='closed', then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            tags_total=Count('tags', distinct=True),
            attachments_total=Count('attachments', distinct=True),
        ).order_by('is_closed_sort', 'task_id')

        with CaptureQueriesContext(connection) as queries:
            groups = _status_groups_for_tasks(
                queryset,
                self.user,
                request=request,
                base_url=reverse('tasks:tasks'),
                paginate=True,
            )

        sql_statements = [query['sql'] for query in queries]
        per_status_count_queries = [
            sql for sql in sql_statements
            if sql.startswith('SELECT COUNT') and '"tasks_task"."status" =' in sql
        ]
        grouped_status_count_queries = [
            sql for sql in sql_statements
            if sql.startswith('SELECT "tasks_task"."status"') and 'COUNT' in sql
        ]
        counts_by_status = {group['status']: group['count'] for group in groups}

        self.assertEqual(counts_by_status['new'], 2)
        self.assertEqual(counts_by_status['in_progress'], 1)
        self.assertEqual(counts_by_status['closed'], 1)
        self.assertEqual(per_status_count_queries, [])
        self.assertEqual(len(grouped_status_count_queries), 1)

    def test_projects_view_renders_only_server_side_window(self):
        for index in range(60):
            project = TaskProject.objects.create(
                user=self.user,
                name=f'Projekt {index:03d}',
                code=f'PRJ-{index:04d}-000',
            )
            TaskSection.objects.create(project=project, title='Plan')

        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-server-pagination="true"')
        self.assertContains(response, 'tasks-project-row tasks-directory-row', count=50)
        self.assertContains(response, 'Projekt 000')
        self.assertContains(response, 'Projekt 049')
        self.assertNotContains(response, 'Projekt 050')
        self.assertContains(response, 'data-project-page-next')
        self.assertContains(response, 'Pokazano 1-50 z 60 projektów')
        self.assertIn('data-project-pagination-summary>1-50 z 60</span>', html)
        self.assertContains(response, 'tasks-project-pagination__size-control--toolbar')
        self.assertContains(response, 'tasks-project-pagination__size-button--toolbar')
        self.assertNotContains(response, 'tasks-project-page-size-menu')
        self.assertNotContains(response, '>Projektów na stronie<')
        self.assertContains(response, 'data-project-page-size-dropdown')
        self.assertContains(response, 'data-project-page-size-toggle')
        self.assertContains(response, 'data-project-page-size-label>50</strong>')
        self.assertContains(response, '<span>/ stronę</span>', html=True)
        for page_size in (10, 25, 50, 100, 150, 200):
            self.assertContains(response, f'data-project-page-size-value="{page_size}"')
        self.assertIn('data-project-page-url="/tasks/?page_size=50&amp;page=2"', html)
        self.assertNotIn('&amp;after=', html)
        filterbar_start = html.index('class="tasks-filterbar tasks-filterbar--directory tasks-filterbar--project-directory"')
        sort_start = html.index('class="tasks-filter-dropdown tasks-project-sort-builder"')
        pagination_start = html.index('class="tasks-project-pagination tasks-project-pagination--toolbar"')
        page_size_start = html.index('tasks-project-pagination__size-control--toolbar')
        table_start = html.index('class="tasks-table-wrap tasks-board')
        right_group_start = html.index('<div class="tasks-filterbar-right">', filterbar_start)
        self.assertLess(filterbar_start, pagination_start)
        self.assertLess(sort_start, pagination_start)
        self.assertLess(pagination_start, page_size_start)
        self.assertLess(right_group_start, pagination_start)
        self.assertLess(page_size_start, table_start)
        self.assertLess(pagination_start, table_start)
        self.assertNotIn('data-project-pagination-pages', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?page_size=50&page=2")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-project-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-project-row tasks-directory-row', count=10)
        self.assertIn('Projekt 050', table_html)
        self.assertIn('Projekt 059', table_html)
        self.assertNotIn('Projekt 049', table_html)
        self.assertContains(response, 'Pokazano 51-60 z 60 projektów')
        self.assertIn('data-project-page-url="/tasks/?page_size=50"', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?page_size=10")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-project-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-project-row tasks-directory-row', count=10)
        self.assertIn('Projekt 000', table_html)
        self.assertNotIn('Projekt 010', table_html)
        self.assertIn('data-project-page-url="/tasks/?page_size=10&amp;page=2"', html)

    def test_all_groups_view_renders_only_server_side_window(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt grup', code='GRP')
        for index in range(60):
            TaskSection.objects.create(
                project=project,
                title=f'Grupa {index:03d}',
                order=index,
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-server-pagination="true"')
        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=50)
        self.assertIn('Grupa 000', table_html)
        self.assertIn('Grupa 049', table_html)
        self.assertNotIn('Grupa 050', table_html)
        self.assertContains(response, 'Na stronie')
        self.assertContains(response, 'grup')
        self.assertContains(response, 'Pokazano 1-50 z 60 grup')
        self.assertIn('data-project-page-url="/tasks/?view=all-groups&amp;page_size=50&amp;page=2"', html)
        self.assertIn('aria-current="page">1</button>', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups&page_size=50&page=2")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=10)
        self.assertIn('Grupa 050', table_html)
        self.assertIn('Grupa 059', table_html)
        self.assertNotIn('Grupa 049', table_html)
        self.assertContains(response, 'Pokazano 51-60 z 60 grup')
        self.assertIn('aria-current="page">2</button>', html)
        self.assertIn('data-project-page-url="/tasks/?view=all-groups&amp;page_size=50"', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups&page_size=10")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=10)
        self.assertIn('Grupa 000', table_html)
        self.assertNotIn('Grupa 010', table_html)
        self.assertIn('data-project-page="6"', html)

    def test_project_view_paginates_project_groups(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt z grupami', code='PZG')
        for index in range(60):
            TaskSection.objects.create(
                project=project,
                title=f'Grupa projektu {index:03d}',
                order=index,
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-server-pagination="true"')
        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=50)
        self.assertIn('Grupa projektu 000', table_html)
        self.assertIn('Grupa projektu 049', table_html)
        self.assertNotIn('Grupa projektu 050', table_html)
        self.assertContains(response, 'Na stronie')
        self.assertContains(response, 'grup')
        self.assertContains(response, 'Pokazano 1-50 z 60 grup')
        self.assertIn(
            f'data-project-page-url="/tasks/?project={project.id}&amp;page_size=50&amp;page=2"',
            html,
        )
        self.assertIn('aria-current="page">1</button>', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}&page_size=50&page=2")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=10)
        self.assertIn('Grupa projektu 050', table_html)
        self.assertIn('Grupa projektu 059', table_html)
        self.assertNotIn('Grupa projektu 049', table_html)
        self.assertContains(response, 'Pokazano 51-60 z 60 grup')
        self.assertIn('aria-current="page">2</button>', html)
        self.assertIn(
            f'data-project-page-url="/tasks/?project={project.id}&amp;page_size=50"',
            html,
        )

        response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}&page_size=10")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=10)
        self.assertIn('Grupa projektu 000', table_html)
        self.assertNotIn('Grupa projektu 010', table_html)
        self.assertIn('data-project-page="6"', html)

    def test_all_tasks_view_paginates_the_directory_with_status_headings(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt zadań', code='TSK')
        section = TaskSection.objects.create(project=project, title='Plan')
        for index in range(72):
            Task.objects.create(user=self.user, section=section,
                                title=f'Zadanie {index:03d}',
                                status='new' if index < 60 else 'in_progress')

        url = reverse('tasks:tasks')
        response = self.client.get(f'{url}?view=all-tasks&sort=title_asc')
        self.assertContains(response, 'task-row tasks-issue-row', count=62)
        self.assertContains(response, 'Pokazano 1-62 z 72 zadań')
        self.assertContains(response, 'Zadanie 049')
        self.assertNotContains(response, 'Zadanie 050')
        self.assertNotContains(response, 'data-task-status-pagination')
        self.assertTrue(response.context['task_window']['has_next'])

        response = self.client.get(response.context['task_window']['next_url'])
        self.assertContains(response, 'task-row tasks-issue-row', count=10)
        self.assertContains(response, 'Pokazano 63-72 z 72 zadań')
        self.assertContains(response, 'id="all-tasks-new"')
        self.assertNotContains(response, 'id="all-tasks-in_progress"')
        self.assertContains(response, 'Zadanie 050')
        self.assertContains(response, 'Zadanie 059')
        self.assertNotContains(response, 'Zadanie 071')
        self.assertNotContains(response, 'Zadanie 049')
        self.assertFalse(response.context['task_window']['has_next'])

        response = self.client.get(f'{url}?view=all-tasks&page_size=10&page=999')
        self.assertContains(response, 'task-row tasks-issue-row', count=10)
        self.assertEqual(response.context['task_window']['page'], 6)
        response = self.client.get(f'{url}?view=all-tasks&q=missing')
        self.assertContains(response, '0 z 0')
        self.assertFalse(response.context['task_window']['has_previous'])
        self.assertFalse(response.context['task_window']['has_next'])

    def test_all_tasks_view_renders_server_search_sort_and_filter_controls(self):
        assignee = get_user_model().objects.create_user(
            username='alpha-owner',
            first_name='Adam',
            last_name='Nowak',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt Alpha', code='ALP')
        section = TaskSection.objects.create(project=project, title='Wdrożenie')
        Task.objects.create(
            user=self.user,
            section=section,
            title='Zadanie Alpha',
            assignee=assignee,
        )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-tasks")

        self.assertContains(response, 'data-server-directory-filters="true"')
        self.assertContains(response, 'data-project-sort-menu')
        self.assertContains(response, 'data-project-default-sort="task_id_asc"')
        self.assertContains(response, 'aria-label="Sortowanie zadań"')
        self.assertNotContains(response, 'tasks-sort-button__label')
        self.assertContains(response, 'id="filter-status"')
        self.assertContains(response, 'name="task_project"')
        self.assertContains(response, 'name="task_section"')
        self.assertContains(response, 'name="task_assignee"')
        self.assertContains(response, 'name="task_type"')
        self.assertContains(response, 'name="task_due"')
        self.assertContains(response, 'data-project-filter-menu="task_project"')
        self.assertContains(response, 'data-project-filter-menu="task_section"')
        self.assertContains(response, 'data-project-filter-menu="task_assignee"')
        self.assertContains(response, 'data-project-filter-menu="task_type"')
        self.assertContains(response, 'data-project-filter-menu="task_due"')
        self.assertContains(response, 'data-project-filter-search', count=3)
        self.assertContains(response, 'Szukaj projektu')
        self.assertContains(response, 'Szukaj grupy')
        self.assertContains(response, 'Szukaj osoby')

    def test_all_tasks_view_filters_searches_sorts_and_preserves_pagination_params(self):
        assignee = get_user_model().objects.create_user(
            username='alpha-assignee',
            first_name='Adam',
            last_name='Nowak',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt Alpha', code='ALP')
        section = TaskSection.objects.create(project=project, title='Wdrożenie')
        due_at = timezone.now() - timedelta(days=1)
        for index in range(30):
            Task.objects.create(
                user=self.user,
                section=section,
                title=f'Alpha telefon {index:03d}',
                status='new',
                priority='high',
                task_type='call',
                due_at=due_at,
                assignee=assignee,
            )
        Task.objects.create(
            user=self.user,
            section=section,
            title='Alpha realizowane ukryte',
            status='in_progress',
            priority='high',
            task_type='call',
            due_at=due_at,
            assignee=assignee,
        )
        Task.objects.create(
            user=self.user,
            section=section,
            title='Beta ukryte',
            status='new',
            priority='low',
            task_type='call',
            due_at=due_at,
            assignee=assignee,
        )

        response = self.client.get(
            f"{reverse('tasks:tasks')}?view=all-tasks&q=Alpha&priority=high&status=new"
            f"&task_project={project.id}&task_section={section.id}&task_assignee={assignee.id}"
            f"&task_type=call&task_due=overdue&sort=title_desc&page_size=25"
        )
        html = response.content.decode()
        new_start = html.index('id="all-tasks-new"')
        new_end = html.index('</section>', new_start)
        new_html = html[new_start:new_end]

        self.assertContains(response, 'task-row tasks-issue-row', count=25)
        self.assertIn('Alpha telefon 029', new_html)
        self.assertIn('Alpha telefon 005', new_html)
        self.assertNotIn('Alpha telefon 004', new_html)
        self.assertNotIn('Alpha realizowane ukryte', html)
        self.assertNotIn('Beta ukryte', html)
        self.assertIn('id="all-tasks-new"', html)
        self.assertNotIn('id="all-tasks-in_progress"', html)
        self.assertIn('page=2', html)
        self.assertIn('q=Alpha', html)
        self.assertIn('priority=high', html)
        self.assertIn('status=new', html)
        self.assertIn(f'task_project={project.id}', html)
        self.assertIn(f'task_section={section.id}', html)
        self.assertIn(f'task_assignee={assignee.id}', html)
        self.assertIn('task_type=call', html)
        self.assertIn('task_due=overdue', html)
        self.assertIn('sort=title_desc', html)
        self.assertContains(response, '<span class="tasks-project-sort-current">Zadanie Z-A</span>', html=True)
        self.assertContains(response, 'Projekt: Projekt Alpha')
        self.assertContains(response, 'Grupa: Wdrożenie (Projekt Alpha)')
        self.assertContains(response, 'Odpowiedzialny: Adam Nowak')
        self.assertContains(response, 'Typ: Telefon')
        self.assertContains(response, 'Termin: Po terminie')

    def test_task_rows_render_only_task_title_in_title_cell(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt zadań', code='TSK')
        section = TaskSection.objects.create(project=project, title='Plan')
        assignee = get_user_model().objects.create_user(
            username='assignee-user',
            first_name='Adam',
            last_name='Mickiewicz',
            password='test-pass-123',
        )
        task = Task.objects.create(
            user=self.user,
            section=section,
            title='Zadanie bez widocznego typu',
            assignee=assignee,
        )

        response = self.client.get(reverse('tasks:task_group', args=[section.id]))
        html = response.content.decode()
        task_marker = f'data-task-id="{task.task_id}"'
        marker_index = html.index(task_marker)
        row_start = html.rfind('<article', 0, marker_index)
        row_end = html.index('</article>', row_start)
        row_html = html[row_start:row_end]

        self.assertIn('Zadanie bez widocznego typu', row_html)
        self.assertNotIn('<span>Ogólne</span>', row_html)
        self.assertNotIn('tasks-row-assignee-meta', row_html)
        self.assertNotIn('<span>Adam Mickiewicz</span>', row_html)

    def test_group_view_header_links_back_to_project(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt nadrzędny', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Nazwa grupy')

        response = self.client.get(reverse('tasks:task_group', args=[section.id]))
        html = response.content.decode()
        header_start = html.index('<header class="tasks-topbar">')
        header_end = html.index('</header>', header_start)
        header_html = html[header_start:header_end]

        self.assertIn('<span>Nazwa grupy</span>', header_html)
        self.assertIn(
            f'href="{reverse("tasks:tasks")}?project={project.id}" class="tasks-issue-close"',
            header_html,
        )
        self.assertIn('aria-label="Wróć do projektu"', header_html)
        self.assertIn('data-icon="arrow-left"', header_html)
        self.assertNotIn('Projekt nadrzędny', header_html)
        self.assertNotIn('tasks-topbar-title-separator', header_html)

    def test_group_task_view_uses_group_url_for_status_pagination(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt grupy', code='GRP')
        section = TaskSection.objects.create(project=project, title='Sprint')
        for index in range(55):
            Task.objects.create(
                user=self.user,
                section=section,
                title=f'Zadanie grupy {index:03d}',
                status='new',
            )

        group_url = reverse('tasks:task_group', args=[section.id])
        response = self.client.get(group_url)
        html = response.content.decode()

        self.assertContains(response, 'task-row tasks-issue-row', count=25)
        self.assertIn('Zadanie grupy 024', html)
        self.assertNotIn('Zadanie grupy 025', html)
        self.assertContains(response, 'Pokazano 1-25 z 55 zadań')
        self.assertIn(
            f'data-task-status-page-url="{group_url}?task_new_page_size=25&amp;task_new_page=2"',
            html,
        )

        response = self.client.get(f"{group_url}?task_new_page_size=50&task_new_page=2")
        html = response.content.decode()

        self.assertContains(response, 'task-row tasks-issue-row', count=5)
        self.assertIn('Zadanie grupy 050', html)
        self.assertIn('Zadanie grupy 054', html)
        self.assertNotIn('Zadanie grupy 049', html)
        self.assertContains(response, 'Pokazano 51-55 z 55 zadań')

    def test_project_create_modal_uses_large_task_style_layout(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'tasks-project-create-modal')
        self.assertContains(response, 'tasks-project-create-modal__body')
        self.assertContains(response, 'tasks-project-create-fields')
        self.assertContains(response, 'Utwórz projekt')

    def test_section_create_modal_uses_task_style_field_layout(self):
        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        modal_start = html.index('id="section-create-modal"')
        modal_end = html.index('id="section-rename-modal"', modal_start)
        modal_html = html[modal_start:modal_end]

        self.assertIn('id="section-create-form"', modal_html)
        self.assertIn('class="u-sr-only" id="section-create-parameters-title"', modal_html)
        expected_fields = [
            'tasks-section-create-field--kind',
            'tasks-section-create-field--status',
            'tasks-section-create-field--owner',
            'tasks-section-create-field--priority',
            'tasks-section-create-field--due',
            'tasks-section-create-field--wip',
        ]
        for field_class in expected_fields:
            self.assertIn(field_class, modal_html)
        self.assertIn('data-ancore-custom-select-search-placeholder="Szukaj osoby"', modal_html)

    def test_directory_headers_offer_contextual_creation_actions(self):
        for query, label, control in [('', 'Dodaj projekt', 'project-modal'),
                                      ('?view=all-groups', 'Dodaj grupę', 'section-create-modal'),
                                      ('?view=all-tasks', 'Dodaj zadanie', 'issue-modal'),
                                      ('?view=tags', 'Dodaj tag', 'tag-modal')]:
            with self.subTest(view=query):
                response = self.client.get(reverse('tasks:tasks') + query)
                html = response.content.decode()
                start = html.index('<header class="tasks-topbar')
                header = html[start:html.index('</header>', start)]
                self.assertIn(f'aria-label="{label}"', header)
                self.assertIn(f'aria-controls="{control}"', header)
                self.assertNotContains(response, 'id="create-menu-panel"')

    def test_project_and_group_icon_pickers_are_not_rendered(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertNotContains(response, 'data-project-icon-picker')
        self.assertNotContains(response, 'Ikona projektu')
        self.assertNotContains(response, 'Ikona grupy')

    def test_projects_view_renders_column_manager(self):
        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()

        self.assertContains(response, 'data-directory-column-manager')
        self.assertContains(response, 'data-directory-column-manager-toggle')
        self.assertContains(response, 'data-directory-column-manager-list')
        self.assertContains(response, 'data-directory-column-manager-search')
        self.assertContains(response, 'data-directory-column-manager-save')
        self.assertContains(response, 'data-directory-column-manager-cancel')
        self.assertContains(response, 'Zarządzaj tabelą')
        self.assertContains(response, 'Kolumny tabeli')
        self.assertLess(
            html.index('data-directory-column-manager hidden'),
            html.index('data-project-filter-builder'),
        )

    def test_project_group_rows_do_not_render_group_type_label(self):
        company = Company.objects.create(owner=self.user, name='Acme CRM')
        project = TaskProject.objects.create(
            user=self.user,
            name='Projekt',
            code='PRJ',
            priority='high',
            due_at=date(2026, 7, 15),
            company=company,
        )
        section = TaskSection.objects.create(project=project, title='Frontend', description='Prace po stronie UI', code='FE')
        TaskSectionNote.objects.create(section=section, author=self.user, message='Moja notatka grupy')
        Task.objects.create(user=self.user, section=section, title='Zadanie ukończone', status='closed')
        Task.objects.create(user=self.user, section=section, title='Zadanie otwarte')
        TaskSection.objects.filter(pk=section.pk).update(
            created_at=datetime(2026, 6, 7, 12, 0, tzinfo=datetime_timezone.utc)
        )

        response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")

        self.assertNotContains(
            response,
            '<span class="status-indicator status-label-plain">Grupa</span>',
            html=True,
        )
        self.assertContains(
            response,
            f'<a href="{reverse("tasks:tasks")}" class="tasks-issue-close" title="Wróć do wszystkich projektów" aria-label="Wróć do wszystkich projektów" data-projects-back-link>',
        )
        self.assertContains(response, 'tasks-titlebar-left tasks-issue-breadcrumb tasks-project-breadcrumb')
        self.assertContains(response, '<span class="tasks-issue-divider" aria-hidden="true"></span>')
        self.assertNotContains(response, 'class="tasks-issue-crumb-icon"')
        self.assertNotContains(response, 'data-icon="briefcase-business" data-icon-fallback="folder"')
        self.assertContains(response, 'tasks-project-sheet--selectable')
        self.assertContains(response, 'tasks-section-sheet')
        self.assertContains(response, 'data-directory-column-manager')
        self.assertContains(response, 'data-directory-column-manager-toggle')
        self.assertContains(response, 'Zarządzaj tabelą')
        self.assertContains(response, 'data-project-filter-field="priority"')
        self.assertNotContains(response, 'data-status-filter-menu')
        self.assertContains(response, 'KOD GRUPY')
        self.assertContains(response, 'STATUS')
        self.assertContains(response, 'TYP')
        self.assertContains(response, 'POSTĘP')
        self.assertContains(response, 'TERMIN')
        self.assertContains(response, 'LIMIT WIP')
        self.assertContains(response, 'ZADANIA')
        self.assertContains(response, 'PRIORYTET')
        self.assertContains(response, 'OSTATNIA AKTYWNOŚĆ')
        self.assertNotContains(response, 'KLIENT / FIRMA')
        self.assertContains(response, 'data-column="action"', count=2)
        self.assertContains(response, 'data-column="action" aria-label="Edytuj grupę"')
        self.assertContains(response, 'data-column="info"', count=2)
        self.assertContains(response, 'data-column="info" aria-label="Informacje o grupie"')
        self.assertContains(response, 'data-column="notes"', count=2)
        self.assertContains(response, 'data-column="notes" aria-label="Notatki grupy"')
        self.assertContains(response, 'data-open-section-info')
        self.assertContains(response, 'data-open-section-notes')
        self.assertContains(response, 'data-open-section-rename')
        self.assertContains(response, 'aria-label="Edytuj grupę Frontend"')
        self.assertContains(response, 'aria-label="Informacje o grupie Frontend"')
        self.assertContains(response, 'aria-label="Notatki grupy Frontend, zawiera notatkę"')
        self.assertContains(response, 'id="section-notes-modal"')
        self.assertContains(response, 'name="action" value="add_section_note"')
        self.assertContains(response, 'name="action" value="edit_section_note"')
        self.assertContains(response, 'name="action" value="delete_section_note"')
        self.assertContains(response, 'Moja notatka grupy')
        self.assertContains(response, 'data-section-notes-message')
        self.assertContains(response, 'data-section-note-edit-toggle')
        self.assertContains(response, f'data-section-id="{section.id}"')
        content = response.content.decode()
        expected_columns = [
            'data-column="action" aria-label="Edytuj grupę"',
            'data-column="info" aria-label="Informacje o grupie"',
            'data-column="notes" aria-label="Notatki grupy"',
            'data-column="section">GRUPA',
            'data-column="project_code">KOD GRUPY',
            'data-column="section_status">STATUS',
            'data-column="section_kind">TYP',
            'data-column="description">OPIS',
            'data-column="progress">POSTĘP',
            'data-column="due_at">TERMIN',
            'data-column="wip_limit">LIMIT WIP',
            'data-column="tasks_count">ZADANIA',
            'data-column="priority">PRIORYTET',
            'data-column="last_activity">OSTATNIA AKTYWNOŚĆ',
            'data-column="created_at">DATA UTWORZENIA',
        ]
        column_positions = [content.index(column) for column in expected_columns]
        self.assertEqual(column_positions, sorted(column_positions))
        self.assertContains(response, 'data-column="project_code"', count=2)
        self.assertContains(response, section.full_code)
        self.assertNotContains(response, 'data-column="company"')
        self.assertContains(response, 'Prace po stronie UI')
        self.assertContains(response, '50%')
        self.assertContains(response, '1/2')
        self.assertContains(response, 'Wysoki')
        self.assertContains(response, '15.07.2026')
        self.assertContains(response, 'Acme CRM')
        self.assertContains(
            response,
            'data-column="created_at" title="Data utworzenia">07.06.2026 14:00</span>',
        )
        self.assertNotContains(
            response,
            '<div class="tasks-directory-members-menu tasks-directory-sheet__cell tasks-project-sheet__cell" data-column="members" data-directory-members-menu>',
        )

    def test_view_task_uses_profile_photo_for_user_avatars(self):
        self.user.profile_photo = 'profile_photos/task-user.webp'
        self.user.save(update_fields=['profile_photo'])
        task = Task.objects.create(user=self.user, title='Zadanie z avatarem')
        TaskActivity.objects.create(task=task, actor=self.user, action='commented', message='Komentarz')

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/media/profile_photos/task-user.webp')

    def test_delete_project_removes_related_tasks_and_renumbers_remaining_tasks(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt do usunięcia', code='DEL')
        section = TaskSection.objects.create(project=project, title='Frontend')
        parent = Task.objects.create(user=self.user, section=section, title='Zadanie projektu')
        subtask = Task.objects.create(user=self.user, section=section, parent=parent, title='Podzadanie projektu')
        TaskActivity.objects.create(task=parent, actor=self.user, action='commented', message='Komentarz')
        TaskAttachment.objects.create(
            task=parent,
            file=SimpleUploadedFile('notatka.txt', b'tresc', content_type='text/plain'),
        )
        remaining_project = TaskProject.objects.create(user=self.user, name='Projekt zostaje', code='STAY')
        remaining_section = TaskSection.objects.create(project=remaining_project, title='Backend')
        remaining_task = Task.objects.create(user=self.user, section=remaining_section, title='Zadanie zostaje')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_project',
            'project_id': project.id,
        })

        remaining_task.refresh_from_db()
        messages = [message.message for message in get_messages(response.wsgi_request)]

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(TaskProject.objects.filter(id=project.id).exists())
        self.assertFalse(TaskSection.objects.filter(id=section.id).exists())
        self.assertFalse(Task.objects.filter(id__in=[parent.id, subtask.id]).exists())
        self.assertFalse(TaskActivity.objects.filter(task_id=parent.id).exists())
        self.assertFalse(TaskAttachment.objects.filter(task_id=parent.id).exists())
        self.assertEqual(remaining_task.task_id, 1)
        self.assertEqual(messages, ['Projekt usunięty razem z zadaniami.'])

    def test_bulk_delete_projects_removes_related_tasks_and_renumbers_remaining_tasks(self):
        first_project = TaskProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        first_section = TaskSection.objects.create(project=first_project, title='Frontend')
        second_project = TaskProject.objects.create(user=self.user, name='Drugi projekt', code='TWO')
        second_section = TaskSection.objects.create(project=second_project, title='Backend')
        first_task = Task.objects.create(user=self.user, section=first_section, title='Pierwsze zadanie')
        second_task = Task.objects.create(user=self.user, section=second_section, title='Drugie zadanie')
        remaining_project = TaskProject.objects.create(user=self.user, name='Projekt zostaje', code='STAY')
        remaining_section = TaskSection.objects.create(project=remaining_project, title='QA')
        remaining_task = Task.objects.create(user=self.user, section=remaining_section, title='Zadanie zostaje')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_project',
            'project_ids': [first_project.id, second_project.id],
        })

        remaining_task.refresh_from_db()
        messages = [message.message for message in get_messages(response.wsgi_request)]

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(TaskProject.objects.filter(id__in=[first_project.id, second_project.id]).exists())
        self.assertFalse(Task.objects.filter(id__in=[first_task.id, second_task.id]).exists())
        self.assertEqual(remaining_task.task_id, 1)
        self.assertEqual(messages, ['Usunięto 2 projekty razem z zadaniami.'])

    def test_all_groups_view_lists_sections(self):
        first_project = TaskProject.objects.create(
            user=self.user,
            name='Pierwszy projekt',
            code='ONE',
            start_at=date(2026, 5, 4),
            status='planned',
            stage='offer',
            health='at_risk',
            source='Polecenie klienta',
        )
        second_project = TaskProject.objects.create(user=self.user, name='Drugi projekt', code='TWO')
        frontend = TaskSection.objects.create(project=first_project, title='Frontend', description='Prace po stronie UI', code='FE')
        TaskSectionNote.objects.create(section=frontend, author=self.user, message='Notatka Frontendu')
        backend = TaskSection.objects.create(project=second_project, title='Backend', code='BE')
        Task.objects.create(user=self.user, section=frontend, title='Zadanie frontendowe')
        TaskSection.objects.filter(pk=frontend.pk).update(
            created_at=datetime(2026, 6, 7, 12, 0, tzinfo=datetime_timezone.utc)
        )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")

        self.assertContains(response, 'Wszystkie grupy')
        self.assertContains(response, 'title="Dodaj grupę"')
        self.assertContains(response, 'data-open-section-create')
        self.assertContains(response, 'data-section-create-project-select')
        self.assertContains(response, 'data-ancore-custom-select-search-placeholder="Szukaj projektu"')
        self.assertContains(response, 'Wybierz projekt')
        self.assertContains(response, 'tasks-directory-header')
        self.assertContains(response, 'tasks-section-sheet')
        self.assertContains(response, 'tasks-all-groups-sheet')
        self.assertContains(response, 'data-directory-column-manager')
        self.assertContains(response, 'data-directory-column-manager-toggle')
        self.assertContains(response, 'KOD GRUPY')
        self.assertContains(response, 'POSTĘP')
        self.assertContains(response, 'TERMIN')
        self.assertContains(response, 'data-column="action"', count=3)
        self.assertContains(response, 'data-column="action" aria-label="Edytuj grupę"')
        self.assertContains(response, 'data-column="info"', count=3)
        self.assertContains(response, 'data-column="info" aria-label="Informacje o grupie"')
        self.assertContains(response, 'data-column="notes"', count=3)
        self.assertContains(response, 'data-column="notes" aria-label="Notatki grupy"')
        self.assertContains(response, 'data-open-section-info', count=2)
        self.assertContains(response, 'data-open-section-notes', count=2)
        self.assertContains(response, 'data-open-section-rename', count=2)
        self.assertContains(response, 'data-section-notes-icon data-icon="file-text"')
        self.assertContains(response, 'data-section-notes-icon data-icon="file-plus-2"')
        self.assertContains(
            response,
            f'class="tasks-project-sheet__edit-button tasks-project-sheet__notes-button has-notes" title="Notatki grupy — zawiera notatkę" aria-label="Notatki grupy {frontend.title}, zawiera notatkę"',
        )
        self.assertContains(
            response,
            f'class="tasks-project-sheet__edit-button tasks-project-sheet__notes-button" title="Notatki grupy" aria-label="Notatki grupy {backend.title}"',
        )
        self.assertContains(response, 'id="section-notes-modal"')
        self.assertContains(response, 'name="action" value="add_section_note"')
        self.assertContains(response, 'name="action" value="edit_section_note"')
        self.assertContains(response, 'name="action" value="delete_section_note"')
        self.assertContains(response, 'Notatka Frontendu')
        self.assertContains(response, f'data-section-id="{frontend.id}"')
        self.assertContains(response, 'data-column="priority"', count=3)
        self.assertContains(response, 'OSTATNIA AKTYWNOŚĆ')
        self.assertNotContains(response, 'WŁAŚCICIEL')
        content = response.content.decode()
        expected_columns = [
            'data-column="action" aria-label="Edytuj grupę"',
            'data-column="info" aria-label="Informacje o grupie"',
            'data-column="notes" aria-label="Notatki grupy"',
            'data-column="project_code">KOD GRUPY',
            'data-column="section">GRUPA',
            'data-column="description">OPIS',
            'data-column="progress">POSTĘP',
            'data-column="due_at">TERMIN',
            'data-column="tasks_count">ZADANIA',
            'data-column="priority">PRIORYTET',
            'data-column="last_activity">OSTATNIA AKTYWNOŚĆ',
            'data-column="project_name">PROJEKT',
            'data-column="start_at">START',
            'data-column="project_status">STATUS',
            'data-column="stage">ETAP',
            'data-column="health">KONDYCJA',
            'data-column="source">ŹRÓDŁO',
            'data-column="created_at">DATA UTWORZENIA',
        ]
        column_positions = [content.index(column) for column in expected_columns]
        self.assertEqual(column_positions, sorted(column_positions))
        self.assertContains(response, 'data-column="project_code"', count=3)
        self.assertContains(response, 'data-column="progress"', count=3)
        self.assertContains(response, 'data-column="project_name"', count=3)
        self.assertContains(response, 'data-column="start_at"', count=3)
        self.assertContains(response, 'data-column="project_status"', count=3)
        self.assertContains(response, 'data-column="stage"', count=3)
        self.assertContains(response, 'data-column="health"', count=3)
        self.assertContains(response, 'data-column="source"', count=3)
        self.assertContains(response, 'ODPOWIEDZIALNY ZA GRUPĘ')
        self.assertContains(response, 'DATA UTWORZENIA')
        self.assertContains(response, 'Frontend')
        self.assertContains(response, frontend.full_code)
        self.assertContains(response, 'Prace po stronie UI')
        self.assertContains(response, 'Backend')
        self.assertContains(response, 'Drugi projekt')
        self.assertContains(response, first_project.code)
        self.assertContains(response, second_project.code)
        self.assertContains(response, '04.05.2026')
        self.assertContains(response, 'Planowany')
        self.assertContains(response, 'Oferta')
        self.assertContains(response, 'Zagrożony')
        self.assertContains(response, 'Polecenie klienta')
        self.assertContains(response, 'Brak startu')
        self.assertContains(response, 'Brak źródła')
        self.assertContains(response, '0/1')
        self.assertContains(response, '0/0')
        self.assertContains(response, '0%')
        self.assertContains(response, 'Brak terminu')
        self.assertContains(response, 'Brak')
        self.assertContains(response, 'Pracownik', count=2)
        self.assertNotContains(
            response,
            '<div class="tasks-directory-members-menu tasks-directory-sheet__cell tasks-project-sheet__cell" data-column="members" data-directory-members-menu>',
        )
        self.assertContains(response, 'data-select-all-target="sections"')
        self.assertContains(
            response,
            'data-column="created_at" title="Data utworzenia">07.06.2026 14:00</span>',
        )
        self.assertNotContains(response, '7 cze')
        self.assertNotContains(response, 'tasks-section-row-icon')
        self.assertNotContains(response, 'MEMBERS')
        self.assertNotContains(response, 'DEFAULT ASSIGNEE FOR ISSUES')
        self.assertNotContains(response, 'Employee')

    def test_flat_navigation_shows_projects_and_tags(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        TaskSection.objects.create(project=project, title='Frontend')
        TaskSection.objects.create(project=project, title='Backend')
        TaskTag.objects.create(user=self.user, name='Design')

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'Wszystkie projekty')
        self.assertContains(response, 'Wszystkie grupy')
        self.assertContains(response, 'Tagi')
        self.assertContains(response, 'tasks-directory-header')
        self.assertContains(response, 'data-select-all-target="projects"')
        self.assertContains(response, 'aria-label="Zaznacz projekt Projekt"')
        self.assertNotContains(response, 'Moje grupy')

    def test_tags_view_lists_tags(self):
        frontend = TaskTag.objects.create(
            user=self.user,
            name='Frontend',
            description='Prace po stronie UI',
            category='area',
            color='#1d4ed8',
            icon='flag',
            priority='high',
            scope='projects',
            owner_label='IT',
            status='active',
            usage_notes='Używaj przy pracach interfejsu.',
            automation_rules='Dodaj przy kanale frontend.',
        )
        backend = TaskTag.objects.create(user=self.user, name='Backend')
        frontend.related_tags.add(backend)
        TaskTagNote.objects.create(tag=frontend, author=self.user, message='Moja notatka tagu')
        TaskTag.objects.filter(pk=frontend.pk).update(
            created_at=datetime(2026, 6, 7, 12, 0, tzinfo=datetime_timezone.utc)
        )
        project = TaskProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        section = TaskSection.objects.create(project=project, title='Grupa')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie frontendowe')
        task.tags.add(frontend)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags")
        html = response.content.decode()

        self.assertContains(response, 'Tagi')
        self.assertContains(response, 'tasks-spreadsheet-sheet')
        self.assertContains(response, 'KOD TAGU')
        self.assertContains(response, 'NAZWA TAGU')
        self.assertContains(response, 'data-directory-column-manager')
        self.assertContains(response, 'data-directory-column-manager-toggle')
        self.assertContains(response, 'data-directory-column-manager-list')
        self.assertContains(response, 'data-directory-column-manager-search')
        self.assertContains(response, 'data-directory-column-manager-save')
        self.assertContains(response, 'data-directory-column-manager-cancel')
        self.assertContains(response, 'Zarządzaj tabelą')
        self.assertContains(response, 'data-ancore-custom-select-search-placeholder="Szukaj tagów"')
        self.assertContains(response, 'data-column-label="Edytuj"')
        self.assertContains(response, 'data-column-label="Informacje"')
        self.assertContains(response, 'data-column-label="Notatki"')
        expected_columns = [
            'data-column="action" aria-label="Edytuj tag"',
            'data-column="info" aria-label="Informacje o tagu"',
            'data-column="notes" aria-label="Notatki tagu"',
            'data-column="tag_name">NAZWA TAGU',
            'data-column="tag_code">KOD TAGU',
            'data-column="tag_type">TYP',
            'data-column="tag_visual">KOLOR / IKONA',
            'data-column="priority">PRIORYTET',
            'data-column="scope">ZAKRES',
            'data-column="owner">WŁAŚCICIEL',
            'data-column="status">STATUS',
            'data-column="description">OPIS',
            'data-column="usage_notes">UŻYCIE',
            'data-column="automation">AUTOMATYKA',
            'data-column="related_tags">POWIĄZANE',
            'data-column="task_count">ZADANIA',
            'data-column="created_at">DATA UTWORZENIA',
        ]
        column_positions = [html.index(column) for column in expected_columns]
        self.assertEqual(column_positions, sorted(column_positions))
        self.assertContains(response, 'data-column="action"', count=3)
        self.assertContains(response, 'data-column="action" aria-label="Edytuj tag"')
        self.assertContains(response, 'data-column="info"', count=3)
        self.assertContains(response, 'data-column="info" aria-label="Informacje o tagu"')
        self.assertContains(response, 'data-column="notes"', count=3)
        self.assertContains(response, 'data-column="notes" aria-label="Notatki tagu"')
        self.assertContains(response, 'tasks-directory-sheet__cell tasks-project-sheet__cell tasks-tag-sheet__cell" data-column="action"')
        self.assertContains(response, 'tasks-directory-sheet__cell tasks-project-sheet__cell tasks-tag-sheet__cell" data-column="info"')
        self.assertContains(response, 'tasks-directory-sheet__cell tasks-project-sheet__cell tasks-tag-sheet__cell" data-column="notes"')
        self.assertContains(response, 'tasks-project-sheet__action tasks-directory-sheet__cell tasks-project-sheet__cell tasks-tag-sheet__cell" data-column="action"')
        self.assertContains(response, 'tasks-project-sheet__info tasks-directory-sheet__cell tasks-project-sheet__cell tasks-tag-sheet__cell" data-column="info"')
        self.assertContains(response, 'tasks-project-sheet__notes tasks-directory-sheet__cell tasks-project-sheet__cell tasks-tag-sheet__cell" data-column="notes"')
        self.assertContains(response, 'data-open-tag-edit', count=2)
        self.assertContains(response, 'data-open-tag-info', count=2)
        self.assertContains(response, 'data-open-tag-notes', count=2)
        self.assertContains(response, 'aria-label="Edytuj tag Frontend"')
        self.assertContains(response, 'aria-label="Informacje o tagu Frontend"')
        self.assertContains(response, 'aria-label="Notatki tagu Frontend"')
        self.assertContains(response, 'id="tag-notes-modal"')
        self.assertContains(response, 'name="action" value="add_tag_note"')
        self.assertContains(response, 'name="action" value="edit_tag_note"')
        self.assertContains(response, 'name="action" value="delete_tag_note"')
        self.assertContains(response, 'Moja notatka tagu')
        self.assertContains(response, 'data-tag-notes-message')
        self.assertContains(response, 'data-tag-note-edit-toggle')
        self.assertContains(response, 'data-column="tag_code"', count=3)
        self.assertContains(response, 'data-column="tag_name"', count=3)
        frontend_row_start = html.index(f'data-tag-id="{frontend.id}"')
        self.assertLess(
            html.index('data-column="action"', frontend_row_start),
            html.index('data-column="info"', frontend_row_start),
        )
        self.assertLess(
            html.index('data-column="info"', frontend_row_start),
            html.index('data-column="notes"', frontend_row_start),
        )
        self.assertLess(
            html.index('data-column="notes"', frontend_row_start),
            html.index('data-column="tag_name"', frontend_row_start),
        )
        self.assertLess(
            html.index('data-column="tag_name"', frontend_row_start),
            html.index('data-column="tag_code"', frontend_row_start),
        )
        self.assertContains(response, 'Frontend')
        self.assertContains(response, 'Prace po stronie UI')
        self.assertContains(response, 'Obszar')
        self.assertContains(response, '#1d4ed8')
        self.assertContains(response, 'Flaga')
        self.assertContains(response, 'Wysoki')
        self.assertContains(response, 'Projekty')
        self.assertContains(response, 'IT')
        self.assertContains(response, 'Aktywny')
        self.assertContains(response, 'Używaj przy pracach interfejsu.')
        self.assertContains(response, 'Dodaj przy kanale frontend.')
        self.assertContains(response, 'Backend')
        self.assertContains(response, 'Brak opisu')
        self.assertContains(response, frontend.code)
        self.assertContains(response, backend.code)
        self.assertContains(response, '1 zadań')
        self.assertContains(response, '0 zadań')
        self.assertContains(
            response,
            'data-column="created_at" title="Data utworzenia">07.06.2026 14:00</span>',
        )
        self.assertNotContains(response, '7 cze')

    def test_tags_view_renders_only_server_side_window(self):
        for index in range(60):
            TaskTag.objects.create(
                user=self.user,
                name=f'Tag {index:03d}',
                description=f'Opis tagu {index:03d}',
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-server-pagination="true"')
        self.assertContains(response, 'tasks-tag-sheet__row', count=50)
        self.assertIn('Tag 000', table_html)
        self.assertIn('Tag 049', table_html)
        self.assertNotIn('Tag 050', table_html)
        self.assertContains(response, 'Na stronie')
        self.assertContains(response, 'tagów')
        self.assertContains(response, 'Pokazano 1-50 z 60 tagów')
        self.assertIn('data-project-page-url="/tasks/?view=tags&amp;page_size=50&amp;page=2"', html)
        self.assertIn('aria-current="page">1</button>', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags&page_size=50&page=2")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-tag-sheet__row', count=10)
        self.assertIn('Tag 050', table_html)
        self.assertIn('Tag 059', table_html)
        self.assertNotIn('Tag 049', table_html)
        self.assertContains(response, 'Pokazano 51-60 z 60 tagów')
        self.assertIn('aria-current="page">2</button>', html)
        self.assertIn('data-project-page-url="/tasks/?view=tags&amp;page_size=50"', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags&page_size=10")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-tag-sheet__row', count=10)
        self.assertIn('Tag 000', table_html)
        self.assertNotIn('Tag 010', table_html)
        self.assertIn('data-project-page="6"', html)

    def test_tags_link_is_rendered(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        TaskSection.objects.create(project=project, title='Frontend')
        TaskTag.objects.create(user=self.user, name='Frontend')
        TaskTag.objects.create(user=self.user, name='Backend')

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'Tagi')
        self.assertContains(response, f'href="/workplaces/{response.wsgi_request.workplace.slug}/tasks/?view=tags"')

    def test_create_tag_from_tasks_page(self):
        related = TaskTag.objects.create(user=self.user, name='Backend')
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_tag',
            'name': 'Design',
            'description': 'Makiety i decyzje wizualne',
            'category': 'work_type',
            'color': '#22c55e',
            'icon': 'briefcase',
            'priority': 'medium',
            'scope': 'tasks',
            'owner_label': 'Design',
            'status': 'active',
            'usage_notes': 'Używać dla makiet i UI.',
            'automation_rules': 'Dodaj po imporcie briefu.',
            'related_tags': [related.id],
            'code': 'DES',
        })

        tag = TaskTag.objects.get(user=self.user, name='Design')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=tags")
        self.assertEqual(tag.description, 'Makiety i decyzje wizualne')
        self.assertEqual(tag.category, 'work_type')
        self.assertEqual(tag.color, '#22c55e')
        self.assertEqual(tag.icon, 'briefcase')
        self.assertEqual(tag.priority, 'medium')
        self.assertEqual(tag.scope, 'tasks')
        self.assertEqual(tag.owner_label, 'Design')
        self.assertEqual(tag.status, 'active')
        self.assertEqual(tag.usage_notes, 'Używać dla makiet i UI.')
        self.assertEqual(tag.automation_rules, 'Dodaj po imporcie briefu.')
        self.assertEqual(list(tag.related_tags.all()), [related])
        self.assertNotEqual(tag.code, 'DES')
        self.assertRegex(tag.code, r'^T-[0-9A-Z]{8}$')

    def test_create_tag_avoids_existing_base36_tag_code(self):
        TaskTag.objects.create(user=self.user, name='Design', code='T-COLLIDE1')

        with patch('tasks.models.secrets.choice', side_effect=list('COLLIDE1BACKEND1')):
            response = self.client.post(reverse('tasks:tasks'), {
                'action': 'create_tag',
                'name': 'Backend',
                'description': '',
            })

        tag = TaskTag.objects.get(user=self.user, name='Backend')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=tags")
        self.assertEqual(tag.code, 'T-BACKEND1')

    def test_delete_tag_from_tasks_page(self):
        tag = TaskTag.objects.create(user=self.user, name='Design')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_tag',
            'tag_id': tag.id,
        })

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=tags")
        self.assertFalse(TaskTag.objects.filter(id=tag.id).exists())

    def test_tag_note_actions_add_edit_and_delete_own_notes(self):
        tag = TaskTag.objects.create(
            user=self.user,
            name='Design',
            description='Opis tagu',
            status='active',
        )
        old_code = tag.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'add_tag_note',
            'tag_id': tag.id,
            'message': '  Nowa notatka tagu  ',
        })

        tag.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        note = TaskTagNote.objects.get(tag=tag)
        self.assertEqual(tag.name, 'Design')
        self.assertEqual(tag.description, 'Opis tagu')
        self.assertEqual(tag.status, 'active')
        self.assertEqual(tag.code, old_code)
        self.assertEqual(note.author, self.user)
        self.assertEqual(note.message, 'Nowa notatka tagu')
        self.assertIsNone(note.edited_at)

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_tag_note',
            'tag_id': tag.id,
            'note_id': note.id,
            'message': '  Poprawiona notatka tagu  ',
        })

        note.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(note.message, 'Poprawiona notatka tagu')
        self.assertIsNotNone(note.edited_at)

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_tag_note',
            'tag_id': tag.id,
            'note_id': note.id,
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(TaskTagNote.objects.filter(id=note.id).exists())

    def test_tag_note_actions_only_allow_author_to_change_note(self):
        other_user = get_user_model().objects.create_user(username='tag-note-owner', password='test-pass-123')
        tag = TaskTag.objects.create(user=self.user, name='Design')
        note = TaskTagNote.objects.create(tag=tag, author=other_user, message='Cudza notatka tagu')

        edit_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_tag_note',
            'tag_id': tag.id,
            'note_id': note.id,
            'message': 'Nie moje',
        })
        delete_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_tag_note',
            'tag_id': tag.id,
            'note_id': note.id,
        })

        note.refresh_from_db()
        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(note.message, 'Cudza notatka tagu')

    def test_edit_tag_from_tasks_page(self):
        tag = TaskTag.objects.create(user=self.user, name='Design', description='Stary opis')
        related = TaskTag.objects.create(user=self.user, name='Backend')
        old_code = tag.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_tag',
            'tag_id': tag.id,
            'name': 'UI',
            'description': 'Nowy opis',
            'category': 'area',
            'color': '#0f766e',
            'icon': 'layers',
            'priority': 'high',
            'scope': 'projects',
            'owner_label': 'Produkt',
            'status': 'archived',
            'usage_notes': 'Stosować przy zmianach UI.',
            'automation_rules': 'Dodaj przy typie zadania UI.',
            'related_tags': [related.id],
            'code': 'NEW',
        })

        tag.refresh_from_db()

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=tags")
        self.assertEqual(tag.name, 'UI')
        self.assertEqual(tag.description, 'Nowy opis')
        self.assertEqual(tag.category, 'area')
        self.assertEqual(tag.color, '#0f766e')
        self.assertEqual(tag.icon, 'layers')
        self.assertEqual(tag.priority, 'high')
        self.assertEqual(tag.scope, 'projects')
        self.assertEqual(tag.owner_label, 'Produkt')
        self.assertEqual(tag.status, 'archived')
        self.assertEqual(tag.usage_notes, 'Stosować przy zmianach UI.')
        self.assertEqual(tag.automation_rules, 'Dodaj przy typie zadania UI.')
        self.assertEqual(list(tag.related_tags.all()), [related])
        self.assertEqual(tag.code, old_code)

    def test_more_options_render_edit_and_delete_actions_for_list_views(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        Task.objects.create(user=self.user, section=section, title='Zadanie')
        TaskTag.objects.create(user=self.user, name='Design')

        section_response = self.client.get(reverse('tasks:task_group', args=[section.id]))
        project_response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")
        all_tasks_response = self.client.get(f"{reverse('tasks:tasks')}?view=all-tasks")
        my_tasks_response = self.client.get(f"{reverse('tasks:tasks')}?view=my-tasks")
        projects_response = self.client.get(reverse('tasks:tasks'))
        groups_response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")
        tags_response = self.client.get(f"{reverse('tasks:tasks')}?view=tags")

        self.assertContains(section_response, 'id="delete-selected-task-menu-btn"')
        self.assertContains(section_response, 'id="edit-selected-task-menu-btn"')
        self.assertContains(project_response, 'id="delete-selected-section-menu-btn"')
        self.assertContains(project_response, 'id="edit-selected-section-menu-btn"')
        self.assertContains(project_response, 'id="info-selected-section-menu-btn"')
        self.assertContains(project_response, 'id="notes-selected-section-menu-btn"')
        self.assertContains(project_response, 'Informacje o grupie')
        self.assertContains(project_response, 'Notatki grupy')
        self.assertContains(all_tasks_response, 'id="delete-selected-task-menu-btn"')
        self.assertContains(all_tasks_response, 'id="edit-selected-task-menu-btn"')
        self.assertContains(my_tasks_response, 'id="delete-selected-task-menu-btn"')
        self.assertContains(my_tasks_response, 'id="edit-selected-task-menu-btn"')
        self.assertContains(projects_response, 'id="delete-selected-project-menu-btn"')
        self.assertContains(projects_response, 'class="tasks-project-delete-button tasks-project-delete-button--separated"')
        self.assertContains(projects_response, 'id="edit-selected-project-menu-btn"')
        self.assertNotContains(projects_response, 'id="edit-selected-project-bar-btn"')
        self.assertContains(projects_response, 'data-select-all-target="projects"')
        self.assertContains(projects_response, 'aria-label="Zaznacz projekt Projekt"')
        self.assertContains(groups_response, 'id="delete-selected-section-menu-btn"')
        self.assertContains(groups_response, 'id="edit-selected-section-menu-btn"')
        self.assertContains(groups_response, 'id="info-selected-section-menu-btn"')
        self.assertContains(groups_response, 'id="notes-selected-section-menu-btn"')
        self.assertContains(groups_response, 'data-select-all-target="sections"')
        self.assertNotContains(groups_response, 'id="delete-selected-tag-menu-btn"')
        self.assertNotContains(groups_response, 'id="edit-selected-tag-menu-btn"')
        self.assertContains(tags_response, 'id="delete-selected-tag-menu-btn"')
        self.assertContains(tags_response, 'id="edit-selected-tag-menu-btn"')

    def test_create_task_modal_assigns_existing_tags(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        tag = TaskTag.objects.create(user=self.user, name='Pilne')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'title': 'Zadanie z tagiem',
            'section': section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'tags': [tag.id],
        })

        task = Task.objects.get(user=self.user, title='Zadanie z tagiem')

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(list(task.tags.all()), [tag])

    def test_create_task_modal_places_tags_before_assignee(self):
        response = self.client.get(reverse('tasks:tasks'))
        content = response.content.decode()

        self.assertLess(
            content.index('tasks-issue-field--tags'),
            content.index('tasks-issue-field--assignee'),
        )
        self.assertLess(
            content.index('tasks-issue-field--assignee'),
            content.index('tasks-issue-field--due'),
        )

    def test_create_task_modal_saves_due_at(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'title': 'Zadanie z terminem',
            'section': section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'due_at': '2026-06-12T14:30',
        })

        task = Task.objects.get(user=self.user, title='Zadanie z terminem')

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(timezone.localtime(task.due_at).strftime('%Y-%m-%dT%H:%M'), '2026-06-12T14:30')

    def test_create_task_modal_ignores_retired_split_estimated_time(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'title': 'Zadanie z estymacją',
            'section': section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'estimated_hours': '2',
            'estimated_minutes_part': '15',
        })

        task = Task.objects.get(user=self.user, title='Zadanie z estymacją')

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertIsNone(task.estimated_minutes)

    def test_create_task_modal_ignores_retired_estimated_time_fields(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'title': 'Zadanie z jednym polem estymacji',
            'section': section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'estimated_duration': '2 godz. 15 min.',
            'estimated_minutes': '135',
        })

        task = Task.objects.get(user=self.user, title='Zadanie z jednym polem estymacji')

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertIsNone(task.estimated_minutes)

    def test_task_due_urgency_uses_time_remaining(self):
        now = timezone.now()

        self.assertEqual(Task(due_at=None).due_urgency, 'none')
        self.assertEqual(Task(due_at=now + timedelta(days=8)).due_urgency, 'green')
        self.assertEqual(Task(due_at=now + timedelta(days=5)).due_urgency, 'green')
        self.assertEqual(Task(due_at=now + timedelta(days=2)).due_urgency, 'yellow')
        self.assertEqual(Task(due_at=now + timedelta(hours=2)).due_urgency, 'red')
        self.assertEqual(Task(due_at=now - timedelta(minutes=1)).due_urgency, 'red')

    def test_create_subtask_from_task_detail(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie główne')

        response = self.client.post(reverse('tasks:view-task', args=[task.task_id]), {
            'action': 'create_subtask_modal',
            'title': 'Pierwsze podzadanie',
            'description': 'Opis podzadania',
            'status': 'in_progress',
        })

        subtask = Task.objects.get(user=self.user, title='Pierwsze podzadanie')

        self.assertRedirects(response, reverse('tasks:view-task', args=[task.task_id]))
        self.assertEqual(subtask.parent, task)
        self.assertEqual(subtask.section, section)
        self.assertEqual(subtask.description, 'Opis podzadania')
        self.assertEqual(subtask.priority, 'medium')
        self.assertEqual(subtask.status, 'in_progress')
        self.assertEqual(list(subtask.tags.all()), [])

        detail_response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))
        subtask_detail_response = self.client.get(reverse('tasks:view-subtask', args=[subtask.task_id]))
        list_response = self.client.get(reverse('tasks:task_group', args=[section.id]))

        self.assertContains(detail_response, 'Pierwsze podzadanie')
        self.assertContains(detail_response, 'Opis podzadania')
        self.assertContains(detail_response, 'Realizowane')
        self.assertContains(detail_response, 'tasks-issue-row--compact')
        self.assertContains(detail_response, reverse('tasks:view-subtask', args=[subtask.task_id]))
        self.assertNotContains(detail_response, '<span>Zadanie</span>', html=True)
        self.assertContains(subtask_detail_response, '<label for="id_parent">Zadanie</label>', html=True)
        self.assertContains(subtask_detail_response, 'Zadanie główne')
        subtask_detail_html = subtask_detail_response.content.decode()
        project_label_position = subtask_detail_html.index('<label for="id_project">Projekt</label>')
        section_label_position = subtask_detail_html.index('<label for="id_section">Grupa</label>')
        parent_label_position = subtask_detail_html.index('<label for="id_parent">Zadanie</label>')
        self.assertLess(project_label_position, section_label_position)
        self.assertLess(section_label_position, parent_label_position)
        self.assertContains(subtask_detail_response, f'href="{reverse("tasks:view-task", args=[task.task_id])}"')
        self.assertContains(subtask_detail_response, 'aria-label="Wróć do zadania"')
        self.assertNotRegex(
            subtask_detail_response.content.decode(),
            rf'<a\s+href="{re.escape(reverse("tasks:view-task", args=[task.task_id]))}"[^>]*data-history-back',
        )
        self.assertNotContains(subtask_detail_response, f'{project.code}-{task.task_id}')
        self.assertNotContains(detail_response, f'{project.code}-{subtask.task_id}')
        self.assertNotContains(list_response, 'Pierwsze podzadanie')

    def test_task_detail_sidebar_shows_task_id(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))
        content = response.content.decode()

        self.assertContains(response, '<span>ID zadania</span>', html=True)
        self.assertContains(
            response,
            f'<span class="tasks-issue-code__value" data-task-code-value>{task.code}</span>',
            html=True,
        )
        self.assertContains(response, f'data-task-code-copy="{task.code}"')
        self.assertNotContains(response, 'data-task-code-short')
        self.assertNotContains(response, 'data-task-code-full')
        self.assertNotContains(response, 'data-task-code-toggle')
        self.assertContains(response, 'data-icon="copy"')
        self.assertLess(content.index('<label for="id_tags">Tagi</label>'), content.index('<span>ID zadania</span>'))
        self.assertLess(content.index('<span>ID zadania</span>'), content.index('<span>Utworzył</span>'))

    def test_task_model_and_detail_remove_crm_and_billable_fields(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(
            user=self.user,
            section=section,
            title='Zadanie',
        )

        detail_response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))

        task_field_names = {field.name for field in Task._meta.get_fields()}
        self.assertTrue({'company', 'contact', 'contact_channel', 'is_billable'}.isdisjoint(task_field_names))
        self.assertNotContains(detail_response, 'name="company"')
        self.assertNotContains(detail_response, 'name="contact"')
        self.assertNotContains(detail_response, 'name="contact_channel"')
        self.assertNotContains(detail_response, 'name="is_billable"')

    def test_removed_task_field_migration_scrubs_activity_history(self):
        task = Task.objects.create(user=self.user, title='Zadanie')
        mixed_activity = TaskActivity.objects.create(
            task=task,
            actor=self.user,
            action='updated',
            message='zaktualizował zadanie',
            metadata={
                'fields': ['firma', 'status'],
                'changes': [
                    {'field': 'firma', 'from_label': 'A', 'to_label': 'B'},
                    {'field': 'status', 'from_label': 'Nowe', 'to_label': 'Zamknięte'},
                ],
            },
        )
        removed_only_activity = TaskActivity.objects.create(
            task=task,
            actor=self.user,
            action='updated',
            message='zaktualizował zadanie',
            metadata={
                'fields': ['fakturowalne'],
                'changes': [
                    {'field': 'fakturowalne', 'from_label': 'Nie', 'to_label': 'Tak'},
                ],
            },
        )
        migration = importlib.import_module(
            'tasks.migrations.0042_remove_task_task_user_company_status_idx_and_more'
        )

        migration.scrub_removed_task_fields_from_activity(django_apps, None)

        mixed_activity.refresh_from_db()
        self.assertEqual(mixed_activity.metadata['fields'], ['status'])
        self.assertEqual(mixed_activity.metadata['changes'], [
            {'field': 'status', 'from_label': 'Nowe', 'to_label': 'Zamknięte'},
        ])
        self.assertFalse(TaskActivity.objects.filter(pk=removed_only_activity.pk).exists())

    def test_subtask_detail_can_change_parent_task(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        first_section = TaskSection.objects.create(project=project, title='Frontend')
        second_section = TaskSection.objects.create(project=project, title='Backend')
        first_parent = Task.objects.create(user=self.user, section=first_section, title='Zadanie frontendowe')
        second_parent = Task.objects.create(user=self.user, section=second_section, title='Zadanie backendowe')
        subtask = Task.objects.create(user=self.user, section=first_section, parent=first_parent, title='Podzadanie')

        response = self.client.post(reverse('tasks:view-subtask', args=[subtask.task_id]), {
            'title': 'Podzadanie',
            'parent': second_parent.id,
            'project': project.id,
            'section': first_section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'time_spent_hours': '',
            'time_spent_minutes': '',
        })

        subtask.refresh_from_db()

        self.assertRedirects(response, reverse('tasks:view-subtask', args=[subtask.task_id]))
        self.assertEqual(subtask.parent, second_parent)
        self.assertEqual(subtask.section, second_section)

    def test_subtask_detail_does_not_allow_adding_attachments(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        parent = Task.objects.create(user=self.user, section=section, title='Zadanie główne')
        subtask = Task.objects.create(user=self.user, section=section, parent=parent, title='Podzadanie')

        detail_response = self.client.get(reverse('tasks:view-subtask', args=[subtask.task_id]))

        self.assertNotContains(detail_response, 'Dodaj załącznik')
        self.assertNotContains(detail_response, 'name="attachments"')

        response = self.client.post(reverse('tasks:view-subtask', args=[subtask.task_id]), {
            'title': 'Podzadanie',
            'parent': parent.id,
            'project': project.id,
            'section': section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'time_spent_hours': '',
            'time_spent_minutes': '',
            'attachments': SimpleUploadedFile('notatka.txt', b'tresc', content_type='text/plain'),
        })

        self.assertRedirects(response, reverse('tasks:view-subtask', args=[subtask.task_id]))
        self.assertFalse(TaskAttachment.objects.filter(task=subtask).exists())

    def test_task_detail_rejects_spoofed_attachment_content(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse('tasks:view-task', args=[task.task_id]), {
                'title': 'Zadanie',
                'parent': '',
                'section': section.id,
                'description': '',
                'priority': 'medium',
                'status': 'new',
                'time_spent_hours': '',
                'time_spent_minutes': '',
                'attachments': SimpleUploadedFile(
                    'payload.png',
                    b'<svg><script>alert(1)</script></svg>',
                    content_type='image/png',
                ),
            })

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Załącznik ma nieprawidłową zawartość.')
            self.assertFalse(TaskAttachment.objects.filter(task=task).exists())

    def test_task_attachment_download_requires_owner(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')
        other_user = get_user_model().objects.create_user(
            username='other-user',
            email='other@example.com',
            first_name='Other',
            last_name='User',
            password='test-pass-123',
        )

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            attachment = TaskAttachment.objects.create(
                task=task,
                file=SimpleUploadedFile('notatka.txt', b'tresc', content_type='text/plain'),
            )

            response = self.client.get(reverse('tasks:download_attachment', args=[attachment.id]))
            self.assertEqual(response.status_code, 200)
            self.assertIn('attachment;', response['Content-Disposition'])
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

            self.client.force_login(other_user)
            response = self.client.get(reverse('tasks:download_attachment', args=[attachment.id]))
            self.assertEqual(response.status_code, 404)

    def test_task_activity_comment_is_saved_from_detail_view(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(reverse('tasks:view-task', args=[task.task_id]), {
            'action': 'add_activity_comment',
            'activity_comment': 'To jest wiadomość w czacie.',
        })

        activity = TaskActivity.objects.get(task=task, kind='comment')

        self.assertRedirects(response, reverse('tasks:view-task', args=[task.task_id]))
        self.assertEqual(activity.actor, self.user)
        self.assertEqual(activity.action, 'commented')
        self.assertEqual(activity.message, 'To jest wiadomość w czacie.')

        detail_response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))
        self.assertContains(detail_response, 'Czat zadania')
        self.assertContains(detail_response, 'data-task-tab="history"')
        self.assertNotContains(detail_response, 'data-activity-dropdown')
        self.assertContains(detail_response, 'To jest wiadomość w czacie.')

    def test_task_activity_feed_shows_newest_items_first(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')
        TaskActivity.objects.create(task=task, actor=self.user, kind='comment', action='commented', message='Starsza wiadomość')
        TaskActivity.objects.create(task=task, actor=self.user, kind='comment', action='commented', message='Nowsza wiadomość')

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))
        content = response.content.decode()

        self.assertLess(content.index('Nowsza wiadomość'), content.index('Starsza wiadomość'))

    def test_detail_update_records_multiple_field_changes_as_one_activity(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(reverse('tasks:view-task', args=[task.task_id]), {
            'title': 'Zadanie po zmianach',
            'parent': '',
            'section': section.id,
            'description': 'Nowy opis',
            'priority': 'high',
            'status': 'in_progress',
            'due_at': '2026-06-15T09:45',
            'time_spent_hours': 1,
            'time_spent_minutes': 15,
        })

        activities = TaskActivity.objects.filter(task=task).exclude(action='created')
        activity = activities.get()

        self.assertRedirects(response, reverse('tasks:view-task', args=[task.task_id]))
        self.assertEqual(activity.action, 'updated')
        self.assertEqual(activity.message, 'zaktualizował zadanie')
        self.assertEqual(activity.metadata['fields'], ['status', 'priorytet', 'tytuł', 'opis', 'termin wykonania'])
        self.assertEqual(activity.metadata['changes'][0]['from_label'], 'Nowe')
        self.assertEqual(activity.metadata['changes'][0]['to_label'], 'Realizowane')
        self.assertEqual(activity.metadata['changes'][1]['from_label'], 'Średni')
        self.assertEqual(activity.metadata['changes'][1]['to_label'], 'Wysoki')
        self.assertEqual(activity.metadata['changes'][4]['to_label'], '15.06.2026 09:45')

    def test_task_detail_uses_manual_save_button_without_autosave(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))

        self.assertContains(response, 'class="tasks-issue-save"')
        self.assertContains(response, 'data-task-save')
        self.assertContains(response, 'saveTaskDetail()')
        self.assertNotContains(response, 'data-task-autosave-status')
        self.assertNotContains(response, "formData.set('autosave', '1')")
        self.assertNotContains(response, 'queueTaskDetailAutosave')

    def test_detail_manual_save_returns_json_and_records_activity(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(
            reverse('tasks:view-task', args=[task.task_id]),
            {
                'title': 'Zadanie po zapisaniu',
                'parent': '',
                'section': section.id,
                'description': 'Opis zapisany ręcznie',
                'priority': 'high',
                'status': 'in_progress',
                'due_at': '',
                'time_spent_hours': '',
                'time_spent_minutes': '',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        task.refresh_from_db()
        activity = TaskActivity.objects.filter(task=task).exclude(action='created').get()

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['status'], 'success')
        self.assertEqual(payload['message'], 'Zapisano.')
        self.assertEqual(payload['task']['title'], 'Zadanie po zapisaniu')
        self.assertIn('data-activity-kind="history"', payload['activity_html'])
        self.assertIn('zaktualizował zadanie', payload['activity_html'])
        self.assertEqual(task.title, 'Zadanie po zapisaniu')
        self.assertEqual(task.priority, 'high')
        self.assertEqual(activity.action, 'updated')

    def test_detail_manual_save_returns_validation_errors_as_json(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(
            reverse('tasks:view-task', args=[task.task_id]),
            {
                'title': '',
                'parent': '',
                'section': section.id,
                'description': '',
                'priority': 'high',
                'status': 'in_progress',
                'due_at': '',
                'time_spent_hours': '',
                'time_spent_minutes': '',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        task.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
        self.assertIn('Tytuł', response.json()['message'])
        self.assertEqual(task.title, 'Zadanie')

    def test_task_forms_omit_retired_detail_controls(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(
            user=self.user,
            section=section,
            title='Zadanie',
            time_spent_hours=2,
            time_spent_minutes=5,
            blocked_reason='Historyczny powód',
        )

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))

        self.assertNotContains(response, 'Powód blokady')
        self.assertNotContains(response, 'Czas pracy')
        self.assertNotContains(response, 'Historia statusu:')
        self.assertNotContains(response, 'data-task-clear-time')
        self.assertNotContains(response, 'Szacowany czas')
        self.assertContains(response, 'Historia zadania')

        create_response = self.client.get(reverse('tasks:tasks'))
        self.assertNotContains(create_response, 'name="blocked_reason"')
        self.assertNotContains(create_response, 'Szacowany czas')

    def test_retired_clear_time_action_preserves_saved_time(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(
            user=self.user,
            section=section,
            title='Zadanie',
            time_spent_hours=2,
            time_spent_minutes=5,
        )

        response = self.client.post(reverse('tasks:view-task', args=[task.task_id]), {
            'action': 'clear_time_spent',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        task.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(task.time_spent_hours, 2)
        self.assertEqual(task.time_spent_minutes, 5)
        self.assertFalse(task.activities.exclude(action='created').exists())

    def test_detail_save_preserves_retired_fields_and_ignores_submitted_values(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(
            user=self.user, section=section, title='Zadanie',
            time_spent_hours=2, time_spent_minutes=5, blocked_reason='Historyczny powód',
            estimated_minutes=45,
        )
        plain_url = reverse('tasks:view-task', args=[task.task_id])
        detail = self.client.get(plain_url)
        scoped_url = f'/workplaces/{detail.wsgi_request.workplace.slug}/tasks/view-task/{task.task_id}/'

        for url in (plain_url, scoped_url):
            for retired_values in ({}, {'time_spent_hours': 99, 'time_spent_minutes': 10, 'blocked_reason': 'Nowy powód', 'estimated_minutes': 99}):
                with self.subTest(url=url, submitted=bool(retired_values)):
                    response = self.client.post(url, {
                        'task_pk': task.pk,
                        'title': 'Zmieniony tytuł',
                        'section': section.pk,
                        'priority': 'high',
                        'status': 'closed',
                        **retired_values,
                    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                    self.assertEqual(response.status_code, 200)
                    task.refresh_from_db()
                    self.assertEqual(task.title, 'Zmieniony tytuł')
                    self.assertTrue(task.is_completed)
                    self.assertIsNotNone(task.completion_date)
                    self.assertEqual(task.blocked_reason, 'Historyczny powód')
                    self.assertEqual(task.time_spent_hours, 2)
                    self.assertEqual(task.time_spent_minutes, 5)
                    self.assertEqual(task.estimated_minutes, 45)

    def test_update_task_status_records_activity(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(
            reverse('tasks:update_task_status', args=[task.task_id]),
            data=json.dumps({'task_pk': task.pk, 'status': 'in_progress'}),
            content_type='application/json',
        )

        activity = TaskActivity.objects.filter(task=task, action='status_changed').latest('id')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(activity.actor, self.user)
        self.assertEqual(activity.metadata['from_label'], 'Nowe')
        self.assertEqual(activity.metadata['to_label'], 'Realizowane')

    def test_my_tasks_view_is_available_from_secondary_navigation(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        Task.objects.create(user=self.user, section=section, title='Moje zadanie testowe', assignee=self.user)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=my-tasks")

        self.assertContains(response, 'Moje zadania')
        self.assertContains(response, 'Moje zadanie testowe')
        self.assertRegex(response.content.decode(),
                         r'<a[^>]+class="nav-link sidebar-subnav-link active"[^>]+data-sidebar-source-item="tasks-my"')

    def test_main_navigation_groups_tasks_and_hides_disabled_sharing(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'Moje zadania')
        self.assertContains(response, 'Wszystkie zadania')
        self.assertContains(response, 'Wszystkie projekty')
        self.assertContains(response, 'Wszystkie grupy')
        self.assertContains(response, 'Tagi')
        self.assertContains(response, 'id="sidebar-tasks-subnav"')
        self.assertNotContains(response, 'Udostępnione zadania')
        self.assertNotContains(response, 'Udostępnione grupy')
        self.assertNotContains(response, 'Udostępnione projekty')
        self.assertNotContains(response, 'Moje grupy')
        self.assertContains(response, 'data-sidebar-group="tasks"')
        self.assertNotContains(response, 'data-rail-nav-group-toggle')

        all_tasks_response = self.client.get(f"{reverse('tasks:tasks')}?view=all-tasks")

        self.assertRegex(all_tasks_response.content.decode(),
                         r'<a[^>]+class="nav-link sidebar-subnav-link active"[^>]+data-sidebar-source-item="tasks-all"')

    def test_edit_project_updates_details_and_manual_code_without_changing_icon(self):
        company = Company.objects.create(owner=self.user, name='Firma projektowa')
        project = TaskProject.objects.create(user=self.user, name='Stara nazwa', description='Stary opis', code='OLD')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Nowa nazwa',
            'description': 'Nowy opis',
            'code': 'new',
            'icon': 'rocket',
            'priority': 'medium',
            'due_at': '2026-08-20',
            'company': company.id,
        })

        project.refresh_from_db()

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(project.name, 'Nowa nazwa')
        self.assertEqual(project.description, 'Nowy opis')
        self.assertEqual(project.priority, 'medium')
        self.assertEqual(project.due_at, date(2026, 8, 20))
        self.assertEqual(project.company, company)
        self.assertEqual(project.icon, '')
        self.assertEqual(project.code, 'NEW')

    def test_project_note_actions_add_edit_and_delete_own_notes(self):
        project = TaskProject.objects.create(
            user=self.user,
            name='Projekt notatek',
            description='Opis projektu',
            code='NOTE',
            status='active',
        )
        old_code = project.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'add_project_note',
            'project_id': project.id,
            'message': '  Nowa notatka projektu  ',
        })

        project.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        note = TaskProjectNote.objects.get(project=project)
        self.assertEqual(project.name, 'Projekt notatek')
        self.assertEqual(project.description, 'Opis projektu')
        self.assertEqual(project.status, 'active')
        self.assertEqual(project.code, old_code)
        self.assertEqual(note.author, self.user)
        self.assertEqual(note.message, 'Nowa notatka projektu')
        self.assertIsNone(note.edited_at)

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project_note',
            'project_id': project.id,
            'note_id': note.id,
            'message': '  Poprawiona notatka  ',
        })

        note.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(note.message, 'Poprawiona notatka')
        self.assertIsNotNone(note.edited_at)

        page_response = self.client.get(reverse('tasks:tasks'))
        self.assertContains(page_response, '| Edytowano:')
        self.assertContains(
            page_response,
            timezone.localtime(note.edited_at).strftime('%d.%m.%Y, %H:%M'),
        )

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_project_note',
            'project_id': project.id,
            'note_id': note.id,
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(TaskProjectNote.objects.filter(id=note.id).exists())

    def test_project_note_ajax_create_returns_rendered_note_without_redirect(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt AJAX')

        response = self.client.post(
            reverse('tasks:tasks'),
            {
                'action': 'add_project_note',
                'project_id': project.id,
                'message': 'Notatka bez przeładowania',
                'next': f"{reverse('tasks:tasks')}?view=projects",
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'success')
        self.assertIn('data-project-note-item', payload['note_html'])
        self.assertIn('Notatka bez przeładowania', payload['note_html'])
        self.assertIn('data-project-note-edit-form', payload['note_html'])
        self.assertNotIn('Edytowano:', payload['note_html'])
        self.assertEqual(TaskProjectNote.objects.filter(project=project).count(), 1)

    def test_note_ajax_edits_return_updated_data_without_redirect(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt AJAX')
        section = TaskSection.objects.create(project=project, title='Grupa AJAX')
        tag = TaskTag.objects.create(user=self.user, name='Tag AJAX')
        cases = (
            (
                'edit_project_note',
                {'project_id': project.id},
                TaskProjectNote.objects.create(project=project, author=self.user, message='Stara treść'),
            ),
            (
                'edit_section_note',
                {'section_id': section.id},
                TaskSectionNote.objects.create(section=section, author=self.user, message='Stara treść'),
            ),
            (
                'edit_tag_note',
                {'tag_id': tag.id},
                TaskTagNote.objects.create(tag=tag, author=self.user, message='Stara treść'),
            ),
        )

        for action, parent_data, note in cases:
            with self.subTest(action=action):
                response = self.client.post(
                    reverse('tasks:tasks'),
                    {
                        'action': action,
                        'note_id': note.id,
                        'message': '  Nowa treść bez przeładowania  ',
                        **parent_data,
                    },
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                    HTTP_ACCEPT='application/json',
                )

                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload['status'], 'success')
                self.assertEqual(payload['note']['message'], 'Nowa treść bez przeładowania')
                self.assertRegex(payload['note']['edited_at_label'], r'^\d{2}\.\d{2}\.\d{4}, \d{2}:\d{2}$')
                self.assertIn('T', payload['note']['edited_at'])
                note.refresh_from_db()
                self.assertEqual(note.message, 'Nowa treść bez przeładowania')
                self.assertIsNotNone(note.edited_at)

    def test_project_note_actions_only_allow_author_to_change_note(self):
        other_user = get_user_model().objects.create_user(username='note-owner', password='test-pass-123')
        project = TaskProject.objects.create(user=self.user, name='Projekt notatek', code='NOTE')
        note = TaskProjectNote.objects.create(project=project, author=other_user, message='Cudza notatka')

        edit_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project_note',
            'project_id': project.id,
            'note_id': note.id,
            'message': 'Nie moje',
        })
        delete_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_project_note',
            'project_id': project.id,
            'note_id': note.id,
        })

        note.refresh_from_db()
        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(note.message, 'Cudza notatka')

    def test_section_note_actions_add_edit_and_delete_own_notes(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt grup', code='GRP')
        section = TaskSection.objects.create(
            project=project,
            title='Grupa notatek',
            description='Opis grupy',
            status='open',
        )
        old_code = section.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'add_section_note',
            'section_id': section.id,
            'message': '  Nowa notatka grupy  ',
        })

        section.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        note = TaskSectionNote.objects.get(section=section)
        self.assertEqual(section.title, 'Grupa notatek')
        self.assertEqual(section.description, 'Opis grupy')
        self.assertEqual(section.status, 'open')
        self.assertEqual(section.code, old_code)
        self.assertEqual(note.author, self.user)
        self.assertEqual(note.message, 'Nowa notatka grupy')
        self.assertIsNone(note.edited_at)

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_section_note',
            'section_id': section.id,
            'note_id': note.id,
            'message': '  Poprawiona notatka grupy  ',
        })

        note.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(note.message, 'Poprawiona notatka grupy')
        self.assertIsNotNone(note.edited_at)

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_section_note',
            'section_id': section.id,
            'note_id': note.id,
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(TaskSectionNote.objects.filter(id=note.id).exists())

    def test_section_note_actions_only_allow_author_to_change_note(self):
        other_user = get_user_model().objects.create_user(username='section-note-owner', password='test-pass-123')
        project = TaskProject.objects.create(user=self.user, name='Projekt grup', code='GRP')
        section = TaskSection.objects.create(project=project, title='Grupa')
        note = TaskSectionNote.objects.create(section=section, author=other_user, message='Cudza notatka grupy')

        edit_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_section_note',
            'section_id': section.id,
            'note_id': note.id,
            'message': 'Nie moje',
        })
        delete_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_section_note',
            'section_id': section.id,
            'note_id': note.id,
        })

        note.refresh_from_db()
        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(note.message, 'Cudza notatka grupy')

    def test_edit_project_ignores_icon_field(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ', icon='rocket')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Projekt',
            'description': '',
            'code': 'PRJ',
            'icon': '',
        })

        project.refresh_from_db()

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(project.icon, 'rocket')

    def test_edit_project_rejects_duplicate_posted_code(self):
        TaskProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        project = TaskProject.objects.create(user=self.user, name='Drugi projekt', code='TWO')
        old_code = project.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Drugi projekt',
            'description': '',
            'code': 'one',
            'icon': '',
        })

        project.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taki kod projektu już istnieje.')
        self.assertEqual(project.code, old_code)

    def test_create_section_saves_description(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_section',
            'project_id': project.id,
            'title': 'Frontend',
            'description': 'Prace nad widokami',
            'code': 'fe',
            'priority': 'high',
            'icon': 'star',
        })

        section = TaskSection.objects.get(project=project, title='Frontend')

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(section.description, 'Prace nad widokami')
        self.assertEqual(section.code, 'FE')
        self.assertEqual(section.priority, 'high')
        self.assertEqual(section.icon, '')

    def test_edit_section_updates_description_priority_and_code(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend', description='Stary opis', code='BE', priority='low')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_section',
            'section_id': section.id,
            'title': 'API',
            'description': 'Nowy opis',
            'code': 'api',
            'priority': 'urgent',
            'icon': '',
        })

        section.refresh_from_db()

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(section.title, 'API')
        self.assertEqual(section.description, 'Nowy opis')
        self.assertEqual(section.code, 'API')
        self.assertEqual(section.priority, 'urgent')

    def test_edit_section_rejects_duplicate_code_in_same_project(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        TaskSection.objects.create(project=project, title='Frontend', code='FE')
        section = TaskSection.objects.create(project=project, title='Backend', code='BE')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_section',
            'section_id': section.id,
            'title': 'Backend',
            'description': '',
            'code': 'fe',
        })

        section.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taki kod grupy już istnieje w tym projekcie.')
        self.assertEqual(section.code, 'BE')

    def test_bulk_delete_sections_from_all_groups_view(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        first_section = TaskSection.objects.create(project=project, title='Frontend')
        second_section = TaskSection.objects.create(project=project, title='Backend')
        remaining_section = TaskSection.objects.create(project=project, title='QA')
        first_task = Task.objects.create(user=self.user, section=first_section, title='Pierwsze zadanie')
        second_task = Task.objects.create(user=self.user, section=second_section, title='Drugie zadanie')
        remaining_task = Task.objects.create(user=self.user, section=remaining_section, title='Zadanie zostaje')

        response = self.client.post(f"{reverse('tasks:tasks')}?view=all-groups", {
            'action': 'delete_section',
            'section_ids': [first_section.id, second_section.id],
        })

        remaining_task.refresh_from_db()
        messages = [message.message for message in get_messages(response.wsgi_request)]

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=all-groups")
        self.assertFalse(TaskSection.objects.filter(id__in=[first_section.id, second_section.id]).exists())
        self.assertFalse(Task.objects.filter(id__in=[first_task.id, second_task.id]).exists())
        self.assertTrue(TaskSection.objects.filter(id=remaining_section.id).exists())
        self.assertEqual(remaining_task.task_id, 1)
        self.assertEqual(messages, ['Usunięto 2 grupy razem z zadaniami.'])

    def test_bulk_update_status_runs_task_completion_logic(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        first_task = Task.objects.create(user=self.user, section=section, title='Pierwsze zadanie')
        second_task = Task.objects.create(user=self.user, section=section, title='Drugie zadanie')

        response = self.client.post(
            reverse('tasks:bulk_update_status'),
            data=json.dumps({
                'task_pks': [first_task.pk, second_task.pk],
                'status': 'closed',
            }),
            content_type='application/json',
        )

        first_task.refresh_from_db()
        second_task.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['updated_count'], 2)
        self.assertTrue(first_task.is_completed)
        self.assertTrue(second_task.is_completed)
        self.assertIsNotNone(first_task.completion_date)
        self.assertIsNotNone(second_task.completion_date)

    def test_bulk_update_status_preserves_completion_and_records_each_change(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        tasks = [
            Task.objects.create(user=self.user, section=section, title=f'Zadanie {index}')
            for index in range(5)
        ]
        already_closed = Task.objects.create(
            user=self.user,
            section=section,
            title='Zamknięte wcześniej',
            status='closed',
        )
        original_completion_date = timezone.now() - timedelta(days=2)
        Task.objects.filter(pk=already_closed.pk).update(completion_date=original_completion_date)

        response = self.client.post(
            reverse('tasks:bulk_update_status'),
            data=json.dumps({
                'task_pks': [task.pk for task in [*tasks, already_closed]],
                'status': 'closed',
            }),
            content_type='application/json',
        )

        already_closed.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['updated_count'], 6)
        self.assertEqual(already_closed.completion_date, original_completion_date)
        self.assertFalse(already_closed.activities.filter(action='status_changed').exists())
        for task in tasks:
            task.refresh_from_db()
            self.assertEqual(task.status, 'closed')
            self.assertTrue(task.is_completed)
            self.assertIsNotNone(task.completion_date)
            activity = task.activities.get(action='status_changed')
            self.assertEqual(activity.actor_id, self.user.pk)
            self.assertEqual(activity.metadata['from_label'], 'Nowe')
            self.assertEqual(activity.metadata['to_label'], 'Zamknięte')

    def test_bulk_update_status_rejects_invalid_status(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(
            reverse('tasks:bulk_update_status'),
            data=json.dumps({
                'task_pks': [task.pk],
                'status': 'nie-ma-takiego',
            }),
            content_type='application/json',
        )

        task.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['message'], 'Nieprawidłowy status')
        self.assertEqual(task.status, 'new')
