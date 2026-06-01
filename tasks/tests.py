import json
import re

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Task, TaskActivity, TaskAttachment, TaskProject, TaskSection, TaskTag


class TaskProjectCreationTests(TestCase):
    PROJECT_CODE_PATTERN = r'^[A-Z]{3}-\d{4}-\d{3}$'

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
        self.assertNotEqual(project.code, 'PT')
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
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
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertEqual(project.icon, '')

    def test_create_project_generates_unique_random_code(self):
        first = TaskProject.objects.create(user=self.user, name='Projekt pierwszy')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt drugi',
            'description': '',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt drugi')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertNotEqual(project.code, first.code)

    def test_project_codes_are_unique_across_users(self):
        other_user = get_user_model().objects.create_user(username='other-user', password='test-pass-123')
        other_project = TaskProject.objects.create(user=other_user, name='Projekt innej osoby')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Mój projekt',
            'description': '',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Mój projekt')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertNotEqual(project.code, other_project.code)

    def test_project_codes_avoid_workspace_codes(self):
        from kanban.models import KanbanProject

        workspace = KanbanProject.objects.create(user=self.user, name='Przestrzeń robocza')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Mój projekt',
            'description': '',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Mój projekt')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertNotEqual(project.code, workspace.code)

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
        self.assertContains(response, frontend.code)
        self.assertContains(response, backend.code)
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
            'code': 'DES',
        })

        tag = TaskTag.objects.get(user=self.user, name='Design')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=all-groups")
        self.assertEqual(tag.description, 'Makiety i decyzje wizualne')
        self.assertNotEqual(tag.code, 'DES')
        self.assertRegex(tag.code, r'^TAG-\d{4}-001$')

    def test_create_tag_uses_next_tag_number_for_current_year(self):
        first = TaskTag.objects.create(user=self.user, name='Design')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_tag',
            'name': 'Backend',
            'description': '',
        })

        tag = TaskTag.objects.get(user=self.user, name='Backend')
        prefix = first.code.rsplit('-', 1)[0]

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=all-groups")
        self.assertEqual(tag.code, f'{prefix}-002')

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
        old_code = tag.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_tag',
            'tag_id': tag.id,
            'name': 'UI',
            'description': 'Nowy opis',
            'code': 'NEW',
        })

        tag.refresh_from_db()

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=all-groups")
        self.assertEqual(tag.name, 'UI')
        self.assertEqual(tag.description, 'Nowy opis')
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

    def test_task_detail_sidebar_shows_project_code(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))
        content = response.content.decode()

        self.assertContains(response, '<span>Kod projektu</span>', html=True)
        self.assertContains(response, f'<strong class="tasks-issue-muted">{project.code}</strong>', html=True)
        self.assertLess(content.index('<label for="id_tags">Tagi</label>'), content.index('<span>Kod projektu</span>'))
        self.assertLess(content.index('<span>Kod projektu</span>'), content.index('<span>Utworzył</span>'))

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
        self.assertContains(detail_response, 'Aktywność')
        self.assertContains(detail_response, 'Tylko czat')
        self.assertContains(detail_response, 'Tylko historia')
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
            'time_spent_hours': 1,
            'time_spent_minutes': 15,
        })

        activities = TaskActivity.objects.filter(task=task).exclude(action='created')
        activity = activities.get()

        self.assertRedirects(response, reverse('tasks:view-task', args=[task.task_id]))
        self.assertEqual(activity.action, 'updated')
        self.assertEqual(activity.message, 'zaktualizował zadanie')
        self.assertEqual(activity.metadata['fields'], ['status', 'priorytet', 'tytuł', 'opis', 'czas pracy'])
        self.assertEqual(activity.metadata['changes'][0]['from_label'], 'Nowe')
        self.assertEqual(activity.metadata['changes'][0]['to_label'], 'Realizowane')
        self.assertEqual(activity.metadata['changes'][1]['from_label'], 'Średni')
        self.assertEqual(activity.metadata['changes'][1]['to_label'], 'Wysoki')

    def test_update_task_status_records_activity(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(
            reverse('tasks:update_task_status', args=[task.task_id]),
            data=json.dumps({'status': 'in_progress'}),
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
        Task.objects.create(user=self.user, section=section, title='Moje zadanie testowe')

        response = self.client.get(f"{reverse('tasks:tasks')}?view=my-tasks")

        self.assertContains(response, 'Moje Zadania')
        self.assertContains(response, 'Moje zadanie testowe')
        self.assertContains(
            response,
            f'<a href="{reverse("tasks:tasks")}?view=my-tasks" class="tasks-rail-link is-active">',
        )

    def test_edit_project_updates_details_without_changing_code(self):
        project = TaskProject.objects.create(user=self.user, name='Stara nazwa', description='Stary opis', code='OLD')
        old_code = project.code

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
        self.assertEqual(project.code, old_code)

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

    def test_edit_project_ignores_posted_code(self):
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

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.code, old_code)

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
