import importlib
import re
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from .models import Task, TaskActivity, TaskProject, TaskSection, TaskTag


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


class LegacyTaskModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='task-user',
            email='task-user@example.com',
            first_name='Task',
            last_name='User',
            password='test-pass-123',
        )
        self.client.force_login(self.user)

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

    def test_create_tag_avoids_existing_base36_tag_code(self):
        TaskTag.objects.create(user=self.user, name='Design', code='T-COLLIDE1')
        with patch('tasks.models.secrets.choice', side_effect=list('COLLIDE1BACKEND1')):
            tag = TaskTag.objects.create(user=self.user, name='Backend')
        self.assertEqual(tag.code, 'T-BACKEND1')

    def test_task_due_urgency_uses_time_remaining(self):
        now = timezone.now()

        self.assertEqual(Task(due_at=None).due_urgency, 'none')
        self.assertEqual(Task(due_at=now + timedelta(days=8)).due_urgency, 'green')
        self.assertEqual(Task(due_at=now + timedelta(days=5)).due_urgency, 'green')
        self.assertEqual(Task(due_at=now + timedelta(days=2)).due_urgency, 'yellow')
        self.assertEqual(Task(due_at=now + timedelta(hours=2)).due_urgency, 'red')
        self.assertEqual(Task(due_at=now - timedelta(minutes=1)).due_urgency, 'red')

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
