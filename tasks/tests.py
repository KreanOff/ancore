import json
import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from .models import Task, TaskProject, TaskSection, TaskTag


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
            'description': 'Opis projektu',
            'code': 'PT',
            'icon': '☆',
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt testowy')
        section = TaskSection.objects.get(project=project)

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.description, 'Opis projektu')
        self.assertEqual(project.icon, '☆')
        self.assertEqual(section.title, 'Nowa Grupa')
        self.assertEqual(section.kind, 'custom')
        self.assertEqual(section.icon, '')
        self.assertEqual(section.order, 0)

    def test_create_project_generates_code_when_form_omits_it(self):
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt bez kodu',
            'description': '',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt bez kodu')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertRegex(project.code, r'^[A-Z2-9]{8}$')
        self.assertEqual(project.icon, '')

    def test_create_project_retries_random_code_when_generated_code_is_taken(self):
        TaskProject.objects.create(user=self.user, name='Projekt pierwszy', code='ABCDEFGH')

        with patch('tasks.models.secrets.choice', side_effect=list('ABCDEFGHABCDEFGJ')):
            response = self.client.post(reverse('tasks:tasks'), {
                'action': 'create_project',
                'name': 'Projekt drugi',
                'description': '',
                'icon': '',
            })

        project = TaskProject.objects.get(user=self.user, name='Projekt drugi')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.code, 'ABCDEFGJ')

    def test_create_project_rejects_duplicate_code_for_same_user(self):
        TaskProject.objects.create(user=self.user, name='Pierwszy projekt', code='ABC')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Drugi projekt',
            'description': '',
            'code': 'abc',
            'icon': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taki kod projektu już istnieje.')
        self.assertFalse(TaskProject.objects.filter(user=self.user, name='Drugi projekt').exists())

    def test_create_project_allows_same_code_for_different_users(self):
        other_user = get_user_model().objects.create_user(username='other-user', password='test-pass-123')
        TaskProject.objects.create(user=other_user, name='Projekt innej osoby', code='ABC')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Mój projekt',
            'description': '',
            'code': 'abc',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Mój projekt')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.code, 'ABC')

    def test_project_icons_get_different_badge_colors(self):
        first = TaskProject.objects.create(user=self.user, name='Pierwszy')
        second = TaskProject.objects.create(user=self.user, name='Drugi')

        self.assertEqual(first.icon, '')
        self.assertEqual(second.icon, '')
        self.assertNotEqual(first.icon_color, second.icon_color)

    def test_projects_list_only_renders_added_icons_next_to_name(self):
        TaskProject.objects.create(user=self.user, name='Projekt z ikoną', code='PZI', icon='☆')
        TaskProject.objects.create(user=self.user, name='Projekt bez ikony', code='PBI', icon='')

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(
            response,
            '<span class="tasks-project-row-icon" aria-hidden="true"',
            count=1,
        )
        self.assertContains(response, '<span>Projekt z ikoną</span>', html=True)
        self.assertContains(response, '<span>Projekt bez ikony</span>', html=True)

    def test_project_group_rows_do_not_render_group_type_label(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        TaskSection.objects.create(project=project, title='Frontend')

        response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")

        self.assertNotContains(
            response,
            '<span class="status-indicator status-label-plain">Grupa</span>',
            html=True,
        )

    def test_all_groups_view_lists_tags(self):
        frontend = TaskTag.objects.create(user=self.user, name='Frontend', description='Prace po stronie UI')
        backend = TaskTag.objects.create(user=self.user, name='Backend')
        project = TaskProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        section = TaskSection.objects.create(project=project, title='Grupa')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie frontendowe')
        task.tags.add(frontend)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")

        self.assertContains(response, 'Tagi')
        self.assertContains(response, 'Frontend')
        self.assertContains(response, 'Prace po stronie UI')
        self.assertContains(response, 'Brak opisu')
        self.assertContains(response, 'Backend')
        self.assertContains(response, '1 zadań')
        self.assertContains(response, '0 zadań')

    def test_all_groups_link_shows_tag_count(self):
        TaskTag.objects.create(user=self.user, name='Frontend')
        TaskTag.objects.create(user=self.user, name='Backend')

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'Tagi')
        self.assertContains(response, '<span class="tasks-rail-count">2</span>', html=True)

    def test_create_tag_from_tasks_page(self):
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_tag',
            'name': 'Design',
            'description': 'Makiety i decyzje wizualne',
        })

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=all-groups")
        self.assertTrue(TaskTag.objects.filter(
            user=self.user,
            name='Design',
            description='Makiety i decyzje wizualne',
        ).exists())

    def test_delete_tag_from_tasks_page(self):
        tag = TaskTag.objects.create(user=self.user, name='Design')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_tag',
            'tag_id': tag.id,
        })

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=all-groups")
        self.assertFalse(TaskTag.objects.filter(id=tag.id).exists())

    def test_edit_tag_from_tasks_page(self):
        tag = TaskTag.objects.create(user=self.user, name='Design', description='Stary opis')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_tag',
            'tag_id': tag.id,
            'name': 'UI',
            'description': 'Nowy opis',
        })

        tag.refresh_from_db()

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=all-groups")
        self.assertEqual(tag.name, 'UI')
        self.assertEqual(tag.description, 'Nowy opis')

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
        tags_response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")

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

    def test_my_tasks_view_is_available_from_secondary_navigation(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        Task.objects.create(user=self.user, section=section, title='Moje zadanie testowe')

        response = self.client.get(f"{reverse('tasks:tasks')}?view=my-tasks")

        self.assertContains(response, 'Moje Zadania')
        self.assertContains(response, 'Moje zadanie testowe')
        self.assertContains(
            response,
            f'<a href="{reverse("tasks:tasks")}?view=my-tasks" class="tasks-rail-link is-active">',
        )

    def test_edit_project_updates_details(self):
        project = TaskProject.objects.create(user=self.user, name='Stara nazwa', description='Stary opis', code='OLD')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Nowa nazwa',
            'description': 'Nowy opis',
            'code': 'new',
            'icon': '🚀',
        })

        project.refresh_from_db()

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.name, 'Nowa nazwa')
        self.assertEqual(project.description, 'Nowy opis')
        self.assertEqual(project.icon, '🚀')
        self.assertEqual(project.code, 'NEW')

    def test_edit_project_can_remove_icon(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ', icon='🚀')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Projekt',
            'description': '',
            'code': 'PRJ',
            'icon': '',
        })

        project.refresh_from_db()

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.icon, '')

    def test_edit_project_rejects_duplicate_code_for_same_user(self):
        TaskProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        project = TaskProject.objects.create(user=self.user, name='Drugi projekt', code='TWO')

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
        self.assertEqual(project.code, 'TWO')

    def test_create_section_saves_description(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_section',
            'project_id': project.id,
            'title': 'Frontend',
            'description': 'Prace nad widokami',
            'icon': '☆',
        })

        section = TaskSection.objects.get(project=project, title='Frontend')

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(section.description, 'Prace nad widokami')
        self.assertEqual(section.icon, '☆')

    def test_edit_section_updates_description(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend', description='Stary opis')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_section',
            'section_id': section.id,
            'title': 'API',
            'description': 'Nowy opis',
            'icon': '',
        })

        section.refresh_from_db()

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(section.title, 'API')
        self.assertEqual(section.description, 'Nowy opis')

    def test_bulk_update_status_runs_task_completion_logic(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        first_task = Task.objects.create(user=self.user, section=section, title='Pierwsze zadanie')
        second_task = Task.objects.create(user=self.user, section=section, title='Drugie zadanie')

        response = self.client.post(
            reverse('tasks:bulk_update_status'),
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
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(
            reverse('tasks:bulk_update_status'),
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
