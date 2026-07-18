import json
import re
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import Kanban, KanbanActivity, KanbanAttachment, KanbanBoardColumn, KanbanProject, KanbanSection, KanbanTag, KanbanTagNote


class KanbanProjectCreationTests(TestCase):
    PROJECT_CODE_PATTERN = r'^P-[0-9A-Z]{8}$'

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='task-user',
            email='task-user@example.com',
            first_name='Kanban',
            last_name='User',
            password='test-pass-123',
        )
        self.client.force_login(self.user)

    def test_create_project_adds_default_group(self):
        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'create_project',
            'name': 'Projekt testowy',
            'section_title': 'Sprint Q3',
            'description': 'Opis projektu',
            'code': 'PT',
            'icon': 'star',
        })

        project = KanbanProject.objects.get(user=self.user, name='Projekt testowy')
        section = KanbanSection.objects.get(project=project)

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?project={project.id}")
        self.assertEqual(project.description, 'Opis projektu')
        self.assertEqual(project.icon, '')
        self.assertNotEqual(project.code, 'PT')
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertEqual(section.title, 'Sprint Q3')
        self.assertEqual(section.kind, 'custom')
        self.assertEqual(section.icon, '')
        self.assertEqual(section.order, 0)

    def test_create_project_uses_default_board_name_when_board_name_is_empty(self):
        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'create_project',
            'name': 'Przestrzeń z domyślną tablicą',
            'section_title': '   ',
            'description': '',
            'icon': '',
        })

        project = KanbanProject.objects.get(user=self.user, name='Przestrzeń z domyślną tablicą')
        section = KanbanSection.objects.get(project=project)

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?project={project.id}")
        self.assertEqual(section.title, 'Nowa Tablica')

    def test_create_project_generates_code_when_form_omits_it(self):
        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'create_project',
            'name': 'Projekt bez kodu',
            'description': '',
            'icon': '',
        })

        project = KanbanProject.objects.get(user=self.user, name='Projekt bez kodu')

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?project={project.id}")
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertEqual(project.icon, '')

    def test_create_project_generates_unique_random_code(self):
        first = KanbanProject.objects.create(user=self.user, name='Projekt pierwszy')

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'create_project',
            'name': 'Projekt drugi',
            'description': '',
            'icon': '',
        })

        project = KanbanProject.objects.get(user=self.user, name='Projekt drugi')

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?project={project.id}")
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertNotEqual(project.code, first.code)

    def test_project_code_generation_does_not_load_all_project_codes(self):
        for index in range(20):
            KanbanProject.objects.create(user=self.user, name=f'Istniejący {index}', code=f'OLD-{index:03d}')

        with patch('kanban.models.secrets.choice', side_effect=list('KBN12345')):
            with CaptureQueriesContext(connection) as queries:
                project = KanbanProject.objects.create(user=self.user, name='Nowy projekt')

        select_sql = ' '.join(query['sql'] for query in queries if query['sql'].startswith('SELECT'))
        self.assertEqual(project.code, 'P-KBN12345')
        self.assertIn('"kanban_kanbanproject"."code" =', select_sql)
        self.assertNotIn('SELECT "kanban_kanbanproject"."code"', select_sql)
        self.assertLessEqual(len(queries), 4)

    def test_project_codes_are_unique_across_users(self):
        other_user = get_user_model().objects.create_user(username='other-user', password='test-pass-123')
        other_project = KanbanProject.objects.create(user=other_user, name='Projekt innej osoby')

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'create_project',
            'name': 'Mój projekt',
            'description': '',
            'icon': '',
        })

        project = KanbanProject.objects.get(user=self.user, name='Mój projekt')

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?project={project.id}")
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertNotEqual(project.code, other_project.code)

    def test_project_codes_avoid_task_project_codes(self):
        from tasks.models import TaskProject

        task_project = TaskProject.objects.create(user=self.user, name='Projekt z modułu zadań')

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'create_project',
            'name': 'Moja przestrzeń',
            'description': '',
            'icon': '',
        })

        project = KanbanProject.objects.get(user=self.user, name='Moja przestrzeń')

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?project={project.id}")
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertNotEqual(project.code, task_project.code)

    def test_project_icons_get_different_badge_colors(self):
        first = KanbanProject.objects.create(user=self.user, name='Pierwszy')
        second = KanbanProject.objects.create(user=self.user, name='Drugi')

        self.assertEqual(first.icon, '')
        self.assertEqual(second.icon, '')
        self.assertNotEqual(first.icon_color, second.icon_color)

    def test_projects_list_only_renders_added_icons_next_to_name(self):
        KanbanProject.objects.create(user=self.user, name='Projekt z ikoną', code='PZI', icon='star')
        KanbanProject.objects.create(user=self.user, name='Projekt bez ikony', code='PBI', icon='')

        response = self.client.get(reverse('kanban:tasks'))

        self.assertContains(
            response,
            '<span class="tasks-project-row-icon" aria-hidden="true"',
            count=1,
        )
        self.assertContains(response, '<span>Projekt z ikoną</span>', html=True)
        self.assertContains(response, '<span>Projekt bez ikony</span>', html=True)

    def test_workspace_and_board_icon_pickers_are_not_rendered(self):
        response = self.client.get(reverse('kanban:tasks'))

        self.assertNotContains(response, 'data-project-icon-picker')
        self.assertNotContains(response, 'Ikona przestrzeni roboczej')
        self.assertNotContains(response, 'Ikona tablicy')

    def test_project_group_rows_do_not_render_group_type_label(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        KanbanSection.objects.create(project=project, title='Frontend')

        response = self.client.get(f"{reverse('kanban:tasks')}?project={project.id}")

        self.assertNotContains(
            response,
            '<span class="status-indicator status-label-plain">Tablica</span>',
            html=True,
        )

    def test_all_groups_view_lists_boards(self):
        first_project = KanbanProject.objects.create(user=self.user, name='Pierwsza przestrzeń', code='ONE')
        second_project = KanbanProject.objects.create(user=self.user, name='Druga przestrzeń', code='TWO')
        KanbanSection.objects.create(project=first_project, title='Frontend', description='Prace po stronie UI')
        KanbanSection.objects.create(project=second_project, title='Backend')

        response = self.client.get(f"{reverse('kanban:tasks')}?view=all-groups")

        self.assertContains(response, 'Wszystkie tablice')
        self.assertContains(response, 'Frontend')
        self.assertContains(response, 'Prace po stronie UI')
        self.assertContains(response, 'Backend')
        self.assertContains(response, 'Pierwsza przestrzeń')
        self.assertContains(response, 'Druga przestrzeń')
        self.assertContains(response, first_project.code)
        self.assertContains(response, second_project.code)

    def test_all_groups_link_shows_board_count(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        KanbanSection.objects.create(project=project, title='Frontend')
        KanbanSection.objects.create(project=project, title='Backend')
        KanbanTag.objects.create(user=self.user, name='Design')

        response = self.client.get(reverse('kanban:tasks'))

        self.assertContains(response, 'Wszystkie tablice')
        self.assertContains(response, '<span class="tasks-rail-count">2</span>', html=True)

    def test_tags_view_lists_tags(self):
        frontend = KanbanTag.objects.create(
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
            usage_notes='Używaj przy kartach interfejsu.',
            automation_rules='Dodaj przy kanale frontend.',
        )
        backend = KanbanTag.objects.create(user=self.user, name='Backend')
        frontend.related_tags.add(backend)
        KanbanTagNote.objects.create(tag=frontend, author=self.user, message='Moja notatka tagu')
        project = KanbanProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        section = KanbanSection.objects.create(project=project, title='Tablica')
        task = Kanban.objects.create(user=self.user, section=section, title='Zadanie frontendowe')
        task.tags.add(frontend)

        response = self.client.get(f"{reverse('kanban:tasks')}?view=tags")
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
            'data-column="task_count">KARTY',
            'data-column="created_at">DATA',
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
        self.assertContains(response, 'id="project-info-modal"')
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
        self.assertContains(response, 'Używaj przy kartach interfejsu.')
        self.assertContains(response, 'Dodaj przy kanale frontend.')
        self.assertContains(response, 'Brak opisu')
        self.assertContains(response, 'Backend')
        self.assertContains(response, frontend.code)
        self.assertContains(response, backend.code)
        self.assertContains(response, '1 kart')
        self.assertContains(response, '0 kart')
        self.assertContains(response, 'data-server-pagination="true"')
        self.assertContains(response, 'Na stronie')
        self.assertContains(response, 'tagów')

    def test_tags_view_renders_only_server_side_window(self):
        for index in range(60):
            KanbanTag.objects.create(
                user=self.user,
                name=f'Tag {index:03d}',
                description=f'Opis tagu {index:03d}',
            )

        response = self.client.get(f"{reverse('kanban:tasks')}?view=tags")
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
        self.assertIn('data-project-page-url="/kanban/?view=tags&amp;page_size=50&amp;page=2"', html)
        self.assertIn('aria-current="page">1</button>', html)

        response = self.client.get(f"{reverse('kanban:tasks')}?view=tags&page_size=50&page=2")
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
        self.assertIn('data-project-page-url="/kanban/?view=tags&amp;page_size=50"', html)

        response = self.client.get(f"{reverse('kanban:tasks')}?view=tags&page_size=10")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-tag-sheet__row', count=10)
        self.assertIn('Tag 000', table_html)
        self.assertNotIn('Tag 010', table_html)
        self.assertIn('data-project-page="6"', html)

    def test_tags_link_shows_tag_count(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        KanbanSection.objects.create(project=project, title='Frontend')
        KanbanTag.objects.create(user=self.user, name='Frontend')
        KanbanTag.objects.create(user=self.user, name='Backend')

        response = self.client.get(reverse('kanban:tasks'))

        self.assertContains(response, 'Tagi')
        self.assertContains(response, '<span class="tasks-rail-count">2</span>', html=True)

    def test_create_tag_from_tasks_page(self):
        related = KanbanTag.objects.create(user=self.user, name='Backend')
        response = self.client.post(reverse('kanban:tasks'), {
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

        tag = KanbanTag.objects.get(user=self.user, name='Design')

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?view=tags")
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
        KanbanTag.objects.create(user=self.user, name='Design', code='T-COLLIDE1')

        with patch('kanban.models.secrets.choice', side_effect=list('COLLIDE1KANBAN01')):
            response = self.client.post(reverse('kanban:tasks'), {
                'action': 'create_tag',
                'name': 'Backend',
                'description': '',
            })

        tag = KanbanTag.objects.get(user=self.user, name='Backend')

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?view=tags")
        self.assertEqual(tag.code, 'T-KANBAN01')

    def test_delete_tag_from_tasks_page(self):
        tag = KanbanTag.objects.create(user=self.user, name='Design')

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'delete_tag',
            'tag_id': tag.id,
        })

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?view=tags")
        self.assertFalse(KanbanTag.objects.filter(id=tag.id).exists())

    def test_tag_note_actions_add_edit_and_delete_own_notes(self):
        tag = KanbanTag.objects.create(
            user=self.user,
            name='Design',
            description='Opis tagu',
            status='active',
        )
        old_code = tag.code

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'add_tag_note',
            'tag_id': tag.id,
            'message': '  Nowa notatka tagu  ',
        })

        tag.refresh_from_db()
        self.assertRedirects(response, reverse('kanban:tasks'))
        note = KanbanTagNote.objects.get(tag=tag)
        self.assertEqual(tag.name, 'Design')
        self.assertEqual(tag.description, 'Opis tagu')
        self.assertEqual(tag.status, 'active')
        self.assertEqual(tag.code, old_code)
        self.assertEqual(note.author, self.user)
        self.assertEqual(note.message, 'Nowa notatka tagu')

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'edit_tag_note',
            'tag_id': tag.id,
            'note_id': note.id,
            'message': '  Poprawiona notatka tagu  ',
        })

        note.refresh_from_db()
        self.assertRedirects(response, reverse('kanban:tasks'))
        self.assertEqual(note.message, 'Poprawiona notatka tagu')

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'delete_tag_note',
            'tag_id': tag.id,
            'note_id': note.id,
        })

        self.assertRedirects(response, reverse('kanban:tasks'))
        self.assertFalse(KanbanTagNote.objects.filter(id=note.id).exists())

    def test_edit_tag_from_tasks_page(self):
        tag = KanbanTag.objects.create(user=self.user, name='Design', description='Stary opis')
        related = KanbanTag.objects.create(user=self.user, name='Backend')
        old_code = tag.code

        response = self.client.post(reverse('kanban:tasks'), {
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
            'automation_rules': 'Dodaj przy typie karty UI.',
            'related_tags': [related.id],
            'code': 'NEW',
        })

        tag.refresh_from_db()

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?view=tags")
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
        self.assertEqual(tag.automation_rules, 'Dodaj przy typie karty UI.')
        self.assertEqual(list(tag.related_tags.all()), [related])
        self.assertEqual(tag.code, old_code)

    def test_more_options_render_edit_and_delete_actions_for_list_views(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        Kanban.objects.create(user=self.user, section=section, title='Zadanie')
        KanbanTag.objects.create(user=self.user, name='Design')

        section_response = self.client.get(reverse('kanban:task_group', args=[section.id]))
        project_response = self.client.get(f"{reverse('kanban:tasks')}?project={project.id}")
        all_tasks_response = self.client.get(f"{reverse('kanban:tasks')}?view=all-tasks")
        my_tasks_response = self.client.get(f"{reverse('kanban:tasks')}?view=my-tasks")
        projects_response = self.client.get(reverse('kanban:tasks'))
        boards_response = self.client.get(f"{reverse('kanban:tasks')}?view=all-groups")
        tags_response = self.client.get(f"{reverse('kanban:tasks')}?view=tags")

        self.assertContains(section_response, 'id="delete-selected-task-menu-btn"')
        self.assertContains(section_response, 'id="edit-selected-task-menu-btn"')
        self.assertContains(project_response, 'id="delete-selected-section-menu-btn"')
        self.assertContains(project_response, 'id="edit-selected-section-menu-btn"')
        self.assertContains(all_tasks_response, 'id="delete-selected-task-menu-btn"')
        self.assertContains(all_tasks_response, 'id="edit-selected-task-menu-btn"')
        self.assertContains(my_tasks_response, 'id="delete-selected-task-menu-btn"')
        self.assertContains(my_tasks_response, 'id="edit-selected-task-menu-btn"')
        self.assertContains(projects_response, 'id="delete-selected-project-menu-btn"')
        self.assertContains(projects_response, 'id="edit-selected-project-menu-btn"')
        self.assertContains(boards_response, 'id="delete-selected-section-menu-btn"')
        self.assertContains(boards_response, 'id="edit-selected-section-menu-btn"')
        self.assertNotContains(boards_response, 'id="delete-selected-tag-menu-btn"')
        self.assertNotContains(boards_response, 'id="edit-selected-tag-menu-btn"')
        self.assertContains(tags_response, 'id="delete-selected-tag-menu-btn"')
        self.assertContains(tags_response, 'id="edit-selected-tag-menu-btn"')

    def test_reorder_board_columns_updates_order(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        first = KanbanBoardColumn.objects.create(section=section, title='Do zrobienia', order=0)
        second = KanbanBoardColumn.objects.create(section=section, title='W toku', order=1)
        third = KanbanBoardColumn.objects.create(section=section, title='Gotowe', order=2)

        response = self.client.post(
            reverse('kanban:reorder_board_columns', args=[section.id]),
            data=json.dumps({'column_ids': [third.id, first.id, second.id]}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(KanbanBoardColumn.objects.filter(section=section).values_list('id', 'order')),
            [(third.id, 0), (first.id, 1), (second.id, 2)],
        )

    def test_reorder_board_columns_rejects_columns_outside_section(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        other_section = KanbanSection.objects.create(project=project, title='Backend')
        first = KanbanBoardColumn.objects.create(section=section, title='Do zrobienia', order=0)
        second = KanbanBoardColumn.objects.create(section=section, title='W toku', order=1)
        outside = KanbanBoardColumn.objects.create(section=other_section, title='Obca', order=0)

        response = self.client.post(
            reverse('kanban:reorder_board_columns', args=[section.id]),
            data=json.dumps({'column_ids': [outside.id, first.id, second.id]}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            list(KanbanBoardColumn.objects.filter(section=section).values_list('id', 'order')),
            [(first.id, 0), (second.id, 1)],
        )

    def test_create_task_modal_assigns_existing_tags(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        tag = KanbanTag.objects.create(user=self.user, name='Pilne')

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'title': 'Zadanie z tagiem',
            'section': section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'tags': [tag.id],
        })

        task = Kanban.objects.get(user=self.user, title='Zadanie z tagiem')

        self.assertRedirects(response, reverse('kanban:task_group', args=[section.id]))
        self.assertEqual(list(task.tags.all()), [tag])

    def test_create_task_modal_uses_posted_kanban_column(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        column = KanbanBoardColumn.objects.create(
            section=section,
            title='Review',
            order=3,
        )

        response = self.client.post(reverse('kanban:task_group', args=[section.id]), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'title': 'Karta w review',
            'section': section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'column_id': column.id,
        })

        task = Kanban.objects.get(user=self.user, title='Karta w review')

        self.assertRedirects(response, reverse('kanban:task_group', args=[section.id]))
        self.assertEqual(task.status, 'new')
        self.assertEqual(task.column, column)

    def test_legacy_quick_create_uses_posted_kanban_column(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        column = KanbanBoardColumn.objects.create(
            section=section,
            title='Review',
            order=3,
        )

        response = self.client.post(reverse('kanban:task_group', args=[section.id]), {
            'action': 'create_task',
            'section_id': section.id,
            'title': 'Szybka karta',
            'column_id': column.id,
        })

        task = Kanban.objects.get(user=self.user, title='Szybka karta')

        self.assertRedirects(response, reverse('kanban:task_group', args=[section.id]))
        self.assertEqual(task.status, 'new')
        self.assertEqual(task.column, column)

    def test_kanban_board_starts_without_default_columns(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')

        response = self.client.get(reverse('kanban:task_group', args=[section.id]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(KanbanBoardColumn.objects.filter(section=section).exists())
        self.assertContains(response, 'Dodaj kolumnę')

    def test_create_custom_kanban_column(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')

        response = self.client.post(reverse('kanban:task_group', args=[section.id]), {
            'action': 'create_board_column',
            'title': 'Do sprawdzenia',
        })

        column = KanbanBoardColumn.objects.get(section=section, title='Do sprawdzenia')

        self.assertRedirects(
            response,
            f"{reverse('kanban:task_group', args=[section.id])}?focus_column={column.id}",
        )
        self.assertEqual(column.order, 0)

    def test_create_custom_kanban_column_uses_last_order(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        KanbanBoardColumn.objects.create(section=section, title='Backlog', order=0)
        KanbanBoardColumn.objects.create(section=section, title='Review', order=8)

        self.client.post(reverse('kanban:task_group', args=[section.id]), {
            'action': 'create_board_column',
            'title': 'Done-ish',
        })

        column = KanbanBoardColumn.objects.get(section=section, title='Done-ish')
        self.assertEqual(column.order, 9)

    def test_delete_kanban_column_deletes_cards_in_that_column(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        backlog = KanbanBoardColumn.objects.create(section=section, title='Backlog', order=0)
        review = KanbanBoardColumn.objects.create(section=section, title='Review', order=1)
        done = KanbanBoardColumn.objects.create(section=section, title='Done', order=2)
        deleted_card = Kanban.objects.create(user=self.user, section=section, column=review, title='Do usunięcia')
        remaining_card = Kanban.objects.create(user=self.user, section=section, column=backlog, title='Zostaje')

        response = self.client.post(reverse('kanban:task_group', args=[section.id]), {
            'action': 'delete_board_column',
            'column_id': review.id,
        })

        backlog.refresh_from_db()
        done.refresh_from_db()

        self.assertRedirects(response, reverse('kanban:task_group', args=[section.id]))
        self.assertFalse(KanbanBoardColumn.objects.filter(id=review.id).exists())
        self.assertFalse(Kanban.objects.filter(id=deleted_card.id).exists())
        self.assertTrue(Kanban.objects.filter(id=remaining_card.id, column=backlog).exists())
        self.assertEqual(backlog.order, 0)
        self.assertEqual(done.order, 1)

    def test_drag_update_changes_column_without_changing_status(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        task = Kanban.objects.create(user=self.user, section=section, title='Zadanie')
        column = KanbanBoardColumn.objects.create(
            section=section,
            title='Review',
            order=3,
        )

        response = self.client.post(
            reverse('kanban:update_task_status', args=[task.task_id]),
            data=json.dumps({'column_id': column.id}),
            content_type='application/json',
        )

        task.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(task.status, 'new')
        self.assertEqual(task.column, column)

    def test_create_subtask_from_task_detail(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        task = Kanban.objects.create(user=self.user, section=section, title='Zadanie główne')

        response = self.client.post(reverse('kanban:view-task', args=[task.task_id]), {
            'action': 'create_subtask_modal',
            'title': 'Pierwsze podzadanie',
            'description': 'Opis podzadania',
            'status': 'in_progress',
        })

        subtask = Kanban.objects.get(user=self.user, title='Pierwsze podzadanie')

        self.assertRedirects(response, reverse('kanban:view-task', args=[task.task_id]))
        self.assertEqual(subtask.parent, task)
        self.assertEqual(subtask.section, section)
        self.assertEqual(subtask.description, 'Opis podzadania')
        self.assertEqual(subtask.priority, 'medium')
        self.assertEqual(subtask.status, 'in_progress')
        self.assertEqual(list(subtask.tags.all()), [])

        detail_response = self.client.get(reverse('kanban:view-task', args=[task.task_id]))
        subtask_detail_response = self.client.get(reverse('kanban:view-subtask', args=[subtask.task_id]))
        list_response = self.client.get(reverse('kanban:task_group', args=[section.id]))

        self.assertContains(detail_response, 'Pierwsze podzadanie')
        self.assertContains(detail_response, 'Opis podzadania')
        self.assertContains(detail_response, 'Realizowane')
        self.assertContains(detail_response, 'tasks-issue-row--compact')
        self.assertContains(detail_response, reverse('kanban:view-subtask', args=[subtask.task_id]))
        self.assertNotContains(detail_response, '<span>Karta</span>', html=True)
        self.assertContains(subtask_detail_response, '<label for="id_parent">Karta</label>', html=True)
        self.assertContains(subtask_detail_response, 'Zadanie główne')
        subtask_detail_html = subtask_detail_response.content.decode()
        project_label_position = subtask_detail_html.index('<label for="id_project">Przestrzeń robocza</label>')
        section_label_position = subtask_detail_html.index('<label for="id_section">Tablica</label>')
        parent_label_position = subtask_detail_html.index('<label for="id_parent">Karta</label>')
        self.assertLess(project_label_position, section_label_position)
        self.assertLess(section_label_position, parent_label_position)
        self.assertContains(subtask_detail_response, f'href="{reverse("kanban:view-task", args=[task.task_id])}"')
        self.assertContains(subtask_detail_response, 'aria-label="Wróć do karty"')
        self.assertNotRegex(
            subtask_detail_response.content.decode(),
            rf'<a\s+href="{re.escape(reverse("kanban:view-task", args=[task.task_id]))}"[^>]*data-history-back',
        )
        self.assertNotContains(subtask_detail_response, f'{project.code}-{task.task_id}')
        self.assertNotContains(detail_response, f'{project.code}-{subtask.task_id}')
        self.assertNotContains(list_response, 'Pierwsze podzadanie')

    def test_task_detail_sidebar_shows_project_code(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        task = Kanban.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.get(reverse('kanban:view-task', args=[task.task_id]))
        content = response.content.decode()

        self.assertContains(response, '<span>Kod przestrzeni</span>', html=True)
        self.assertContains(response, f'<strong class="tasks-issue-muted">{project.code}</strong>', html=True)
        self.assertLess(content.index('<label for="id_tags">Tagi</label>'), content.index('<span>Kod przestrzeni</span>'))
        self.assertLess(content.index('<span>Kod przestrzeni</span>'), content.index('<span>Utworzył</span>'))

    def test_subtask_detail_can_change_parent_task(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        first_section = KanbanSection.objects.create(project=project, title='Frontend')
        second_section = KanbanSection.objects.create(project=project, title='Backend')
        first_parent = Kanban.objects.create(user=self.user, section=first_section, title='Zadanie frontendowe')
        second_parent = Kanban.objects.create(user=self.user, section=second_section, title='Zadanie backendowe')
        subtask = Kanban.objects.create(user=self.user, section=first_section, parent=first_parent, title='Podzadanie')

        response = self.client.post(reverse('kanban:view-subtask', args=[subtask.task_id]), {
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

        self.assertRedirects(response, reverse('kanban:view-subtask', args=[subtask.task_id]))
        self.assertEqual(subtask.parent, second_parent)
        self.assertEqual(subtask.section, second_section)

    def test_subtask_detail_does_not_allow_adding_attachments(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        parent = Kanban.objects.create(user=self.user, section=section, title='Zadanie główne')
        subtask = Kanban.objects.create(user=self.user, section=section, parent=parent, title='Podzadanie')

        detail_response = self.client.get(reverse('kanban:view-subtask', args=[subtask.task_id]))

        self.assertNotContains(detail_response, 'Dodaj załącznik')
        self.assertNotContains(detail_response, 'name="attachments"')

        response = self.client.post(reverse('kanban:view-subtask', args=[subtask.task_id]), {
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

        self.assertRedirects(response, reverse('kanban:view-subtask', args=[subtask.task_id]))
        self.assertFalse(KanbanAttachment.objects.filter(task=subtask).exists())

    def test_task_detail_rejects_spoofed_attachment_content(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        task = Kanban.objects.create(user=self.user, section=section, title='Zadanie')

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse('kanban:view-task', args=[task.task_id]), {
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
            self.assertFalse(KanbanAttachment.objects.filter(task=task).exists())

    def test_task_attachment_download_requires_owner(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        task = Kanban.objects.create(user=self.user, section=section, title='Zadanie')
        other_user = get_user_model().objects.create_user(
            username='other-user',
            email='other@example.com',
            first_name='Other',
            last_name='User',
            password='test-pass-123',
        )

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            attachment = KanbanAttachment.objects.create(
                task=task,
                file=SimpleUploadedFile('notatka.txt', b'tresc', content_type='text/plain'),
            )

            response = self.client.get(reverse('kanban:download_attachment', args=[attachment.id]))
            self.assertEqual(response.status_code, 200)
            self.assertIn('attachment;', response['Content-Disposition'])
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

            self.client.force_login(other_user)
            response = self.client.get(reverse('kanban:download_attachment', args=[attachment.id]))
            self.assertEqual(response.status_code, 404)

    def test_task_activity_comment_is_saved_from_detail_view(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        task = Kanban.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(reverse('kanban:view-task', args=[task.task_id]), {
            'action': 'add_activity_comment',
            'activity_comment': 'To jest wiadomość w czacie.',
        })

        activity = KanbanActivity.objects.get(task=task, kind='comment')

        self.assertRedirects(response, reverse('kanban:view-task', args=[task.task_id]))
        self.assertEqual(activity.actor, self.user)
        self.assertEqual(activity.action, 'commented')
        self.assertEqual(activity.message, 'To jest wiadomość w czacie.')

        detail_response = self.client.get(reverse('kanban:view-task', args=[task.task_id]))
        self.assertContains(detail_response, 'Aktywność')
        self.assertContains(detail_response, 'Tylko czat')
        self.assertContains(detail_response, 'Tylko historia')
        self.assertContains(detail_response, 'To jest wiadomość w czacie.')

    def test_task_activity_feed_shows_newest_items_first(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        task = Kanban.objects.create(user=self.user, section=section, title='Zadanie')
        KanbanActivity.objects.create(task=task, actor=self.user, kind='comment', action='commented', message='Starsza wiadomość')
        KanbanActivity.objects.create(task=task, actor=self.user, kind='comment', action='commented', message='Nowsza wiadomość')

        response = self.client.get(reverse('kanban:view-task', args=[task.task_id]))
        content = response.content.decode()

        self.assertLess(content.index('Nowsza wiadomość'), content.index('Starsza wiadomość'))

    def test_detail_update_records_multiple_field_changes_as_one_activity(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Backend')
        task = Kanban.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(reverse('kanban:view-task', args=[task.task_id]), {
            'title': 'Zadanie po zmianach',
            'parent': '',
            'section': section.id,
            'description': 'Nowy opis',
            'priority': 'high',
            'status': 'in_progress',
            'time_spent_hours': 1,
            'time_spent_minutes': 15,
        })

        activities = KanbanActivity.objects.filter(task=task).exclude(action='created')
        activity = activities.get()

        self.assertRedirects(response, reverse('kanban:view-task', args=[task.task_id]))
        self.assertEqual(activity.action, 'updated')
        self.assertEqual(activity.message, 'zaktualizował kartę')
        self.assertEqual(activity.metadata['fields'], ['status', 'priorytet', 'tytuł', 'opis', 'czas pracy'])
        self.assertEqual(activity.metadata['changes'][0]['from_label'], 'Nowe')
        self.assertEqual(activity.metadata['changes'][0]['to_label'], 'Realizowane')
        self.assertEqual(activity.metadata['changes'][1]['from_label'], 'Średni')
        self.assertEqual(activity.metadata['changes'][1]['to_label'], 'Wysoki')

    def test_detail_shows_saved_time_spent_with_delete_action(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Backend')
        task = Kanban.objects.create(
            user=self.user,
            section=section,
            title='Zadanie',
            time_spent_hours=2,
            time_spent_minutes=5,
        )

        response = self.client.get(reverse('kanban:view-task', args=[task.task_id]))

        self.assertContains(response, '02:05')
        self.assertContains(response, 'name="action" value="clear_time_spent"')

    def test_clear_time_spent_action_removes_time_and_records_activity(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Backend')
        task = Kanban.objects.create(
            user=self.user,
            section=section,
            title='Zadanie',
            time_spent_hours=2,
            time_spent_minutes=5,
        )

        response = self.client.post(reverse('kanban:view-task', args=[task.task_id]), {
            'action': 'clear_time_spent',
        })

        task.refresh_from_db()
        activity = KanbanActivity.objects.filter(task=task).exclude(action='created').get()

        self.assertRedirects(response, reverse('kanban:view-task', args=[task.task_id]))
        self.assertIsNone(task.time_spent_hours)
        self.assertIsNone(task.time_spent_minutes)
        self.assertEqual(activity.metadata['fields'], ['czas pracy'])
        self.assertEqual(activity.metadata['changes'][0]['from_label'], '02:05')
        self.assertEqual(activity.metadata['changes'][0]['to_label'], '00:00')

    def test_update_task_status_records_activity(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Backend')
        task = Kanban.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(
            reverse('kanban:update_task_status', args=[task.task_id]),
            data=json.dumps({'status': 'in_progress'}),
            content_type='application/json',
        )

        activity = KanbanActivity.objects.filter(task=task, action='status_changed').latest('id')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(activity.actor, self.user)
        self.assertEqual(activity.metadata['from_label'], 'Nowe')
        self.assertEqual(activity.metadata['to_label'], 'Realizowane')

    def test_my_tasks_view_does_not_show_removed_secondary_navigation_labels(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Frontend')
        Kanban.objects.create(user=self.user, section=section, title='Moje zadanie testowe')

        response = self.client.get(f"{reverse('kanban:tasks')}?view=my-tasks")

        self.assertNotContains(response, 'Moje karty')
        self.assertNotContains(response, 'Wszystkie karty')
        self.assertContains(response, 'Moje zadanie testowe')

    def test_edit_project_updates_details_without_changing_code_or_icon(self):
        project = KanbanProject.objects.create(user=self.user, name='Stara nazwa', description='Stary opis', code='OLD')
        old_code = project.code

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Nowa nazwa',
            'description': 'Nowy opis',
            'code': 'new',
            'icon': 'rocket',
        })

        project.refresh_from_db()

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?project={project.id}")
        self.assertEqual(project.name, 'Nowa nazwa')
        self.assertEqual(project.description, 'Nowy opis')
        self.assertEqual(project.icon, '')
        self.assertEqual(project.code, old_code)

    def test_edit_project_ignores_icon_field(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ', icon='rocket')

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Projekt',
            'description': '',
            'code': 'PRJ',
            'icon': '',
        })

        project.refresh_from_db()

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?project={project.id}")
        self.assertEqual(project.icon, 'rocket')

    def test_edit_project_ignores_posted_code(self):
        KanbanProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        project = KanbanProject.objects.create(user=self.user, name='Drugi projekt', code='TWO')
        old_code = project.code

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Drugi projekt',
            'description': '',
            'code': 'one',
            'icon': '',
        })

        project.refresh_from_db()

        self.assertRedirects(response, f"{reverse('kanban:tasks')}?project={project.id}")
        self.assertEqual(project.code, old_code)

    def test_create_section_saves_description(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'create_section',
            'project_id': project.id,
            'title': 'Frontend',
            'description': 'Prace nad widokami',
            'icon': 'star',
        })

        section = KanbanSection.objects.get(project=project, title='Frontend')

        self.assertRedirects(response, reverse('kanban:task_group', args=[section.id]))
        self.assertEqual(section.description, 'Prace nad widokami')
        self.assertEqual(section.icon, '')

    def test_edit_section_updates_description(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Backend', description='Stary opis')

        response = self.client.post(reverse('kanban:tasks'), {
            'action': 'edit_section',
            'section_id': section.id,
            'title': 'API',
            'description': 'Nowy opis',
            'icon': '',
        })

        section.refresh_from_db()

        self.assertRedirects(response, reverse('kanban:task_group', args=[section.id]))
        self.assertEqual(section.title, 'API')
        self.assertEqual(section.description, 'Nowy opis')

    def test_bulk_update_status_runs_task_completion_logic(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Backend')
        first_task = Kanban.objects.create(user=self.user, section=section, title='Pierwsze zadanie')
        second_task = Kanban.objects.create(user=self.user, section=section, title='Drugie zadanie')

        response = self.client.post(
            reverse('kanban:bulk_update_status'),
            data=json.dumps({
                'task_ids': [first_task.task_id, second_task.task_id],
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

    def test_bulk_update_status_rejects_invalid_status(self):
        project = KanbanProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = KanbanSection.objects.create(project=project, title='Backend')
        task = Kanban.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(
            reverse('kanban:bulk_update_status'),
            data=json.dumps({
                'task_ids': [task.task_id],
                'status': 'nie-ma-takiego',
            }),
            content_type='application/json',
        )

        task.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['message'], 'Nieprawidłowy status')
        self.assertEqual(task.status, 'new')
