from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from kanban.models import Kanban
from tasks.models import Task, TaskActivity


class DashboardViewTests(TestCase):
    def test_settings_requires_login(self):
        response = self.client.get(reverse('settings'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_settings_renders_settings_sections(self):
        user = get_user_model().objects.create_user(
            username='settings-user',
            email='settings-user@example.com',
            password='test-pass-123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('settings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ustawienia Ancore')
        self.assertContains(response, f'href="{reverse("settings")}"')
        self.assertContains(response, 'href="/admin/"')
        self.assertContains(response, reverse('profile'))
        self.assertContains(response, 'Profil użytkownika')
        self.assertContains(response, 'Konta w sesji')
        self.assertContains(response, 'Bezpieczeństwo')
        self.assertContains(response, 'Powiadomienia')
        self.assertContains(response, 'Wygląd')
        self.assertContains(response, 'Język i region')
        self.assertContains(response, 'Dane i eksport')
        self.assertContains(response, 'Integracje')
        self.assertContains(response, 'Pomoc')
        self.assertContains(response, reverse('logout'))

    def test_home_renders_for_authenticated_user(self):
        user = get_user_model().objects.create_user(
            username='dashboard-user',
            email='dashboard-user@example.com',
            profile_photo='profile_photos/dashboard-user.webp',
            password='test-pass-123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Centrum pracy')
        self.assertContains(response, reverse('tasks:tasks'))

    def test_home_rail_lists_task_and_kanban_notifications(self):
        user = get_user_model().objects.create_user(
            username='dashboard-user',
            email='dashboard-user@example.com',
            password='test-pass-123',
        )
        user.profile_photo = 'profile_photos/dashboard-user.webp'
        user.save(update_fields=['profile_photo'])
        other_user = get_user_model().objects.create_user(
            username='other-dashboard-user',
            email='other-dashboard-user@example.com',
            password='test-pass-123',
        )
        task = Task.objects.create(user=user, title='Zadanie z Tasks')
        TaskActivity.objects.create(
            task=task,
            actor=user,
            action='updated',
            message='zaktualizował zadanie',
            metadata={
                'changes': [{
                    'field': 'status',
                    'from_label': 'Ponownie otwarte',
                    'to_label': 'Rozwiązane',
                }],
            },
        )
        kanban_card = Kanban.objects.create(user=user, title='Karta z Kanban')
        Task.objects.create(user=other_user, title='Zadanie innej osoby')
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Powiadomienia')
        self.assertContains(response, 'dashboard-notification--tasks')
        self.assertContains(response, 'dashboard-notification--kanban')
        self.assertContains(response, 'dashboard-notification-avatar')
        self.assertContains(response, '/media/profile_photos/dashboard-user.webp')
        self.assertContains(response, 'dashboard-user')
        self.assertContains(response, 'utworzył zadanie')
        self.assertContains(response, 'utworzył kartę')
        self.assertContains(response, 'Gdzie:')
        self.assertContains(response, 'Tytuł:')
        self.assertContains(response, 'Status:')
        self.assertContains(response, 'Ponownie otwarte')
        self.assertContains(response, 'Rozwiązane')
        self.assertContains(response, 'Zadanie z Tasks')
        self.assertContains(response, 'Karta z Kanban')
        self.assertContains(response, reverse('tasks:view-task', args=[task.task_id]))
        self.assertContains(response, reverse('kanban:view-task', args=[kanban_card.task_id]))
        self.assertNotContains(response, 'Zadanie innej osoby')
        self.assertNotContains(response, 'dashboard-rail-nav tasks-rail-nav')
