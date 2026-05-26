from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Task, TaskProject, TaskSection


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
        self.assertEqual(project.code, 'PRO')
        self.assertEqual(project.icon, '')

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

    def test_all_groups_view_lists_groups_from_every_project(self):
        first_project = TaskProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        second_project = TaskProject.objects.create(user=self.user, name='Drugi projekt', code='TWO')
        frontend = TaskSection.objects.create(project=first_project, title='Frontend')
        backend = TaskSection.objects.create(project=second_project, title='Backend')
        Task.objects.create(user=self.user, section=frontend, title='Zadanie frontendowe')

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")

        self.assertContains(response, 'Tagi')
        self.assertContains(response, 'Frontend')
        self.assertContains(response, 'Backend')
        self.assertContains(response, 'Pierwszy projekt')
        self.assertContains(response, 'Drugi projekt')
        self.assertContains(response, '1 zadań')
        self.assertContains(response, '0 zadań')
        self.assertContains(
            response,
            f'<a href="{reverse("tasks:task_group", args=[backend.id])}"',
        )

    def test_all_groups_link_shows_group_count(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        TaskSection.objects.create(project=project, title='Frontend')
        TaskSection.objects.create(project=project, title='Backend')

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'Tagi')
        self.assertContains(response, '<span class="tasks-rail-count">2</span>', html=True)

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
