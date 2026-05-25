from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import TaskProject, TaskSection


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
