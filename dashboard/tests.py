from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.views import _dashboard_notifications
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
        self.assertContains(response, 'data-sticky-note-toggle')
        self.assertContains(response, 'sidebar-sticker-toggle')
        self.assertContains(response, 'id="app-sticky-note"')
        self.assertContains(response, 'data-sticky-note-resize')
        self.assertContains(response, 'sticky-note.js?v=20260707-sticker-close-fix')
        self.assertNotContains(response, 'Przegląd')
        self.assertContains(response, 'href="/admin/"')
        self.assertContains(response, reverse('profile'))
        self.assertContains(response, 'Profil użytkownika')
        self.assertContains(response, reverse('add_account'))
        self.assertContains(response, 'Dodaj konto')
        self.assertNotContains(response, 'Konta w sesji')
        self.assertContains(response, 'Sesja')
        self.assertContains(response, f'action="{reverse("logout")}"')
        self.assertContains(response, 'Wyloguj się')
        self.assertContains(response, 'Bezpieczeństwo')
        self.assertContains(response, 'Powiadomienia')
        self.assertContains(response, 'Wygląd')
        self.assertContains(response, 'Język i region')
        self.assertContains(response, 'Dane i eksport')
        self.assertContains(response, 'Integracje')
        self.assertContains(response, 'Pomoc')
        content = response.content.decode()
        self.assertLess(content.index('</nav>'), content.index('profile-rail-actions'))
        self.assertLess(content.index('Pomoc'), content.index('Dodaj konto'))
        self.assertLess(content.index('Dodaj konto'), content.index('Wyloguj się'))

    def test_home_redirects_authenticated_user_to_workplaces(self):
        user = get_user_model().objects.create_user(
            username='dashboard-user',
            email='dashboard-user@example.com',
            profile_photo='profile_photos/dashboard-user.webp',
            password='test-pass-123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('workplaces:workplaces'))

    def test_dashboard_notifications_include_task_and_kanban_activity(self):
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

        notifications = _dashboard_notifications(user)
        task_notification = next(
            notification
            for notification in notifications
            if notification['object_id'] == task.task_id
            and any(line['label'] == 'Status' for line in notification['detail_lines'])
        )
        kanban_notification = next(notification for notification in notifications if notification['object_id'] == kanban_card.task_id)

        self.assertEqual(task_notification['source'], 'tasks')
        self.assertEqual(task_notification['source_label'], 'Tasks')
        self.assertEqual(task_notification['actor_label'], user.get_username())
        self.assertEqual(task_notification['title'], 'Zadanie z Tasks')
        self.assertEqual(task_notification['url'], reverse('tasks:view-task', args=[task.task_id]))
        self.assertIn('Zadanie z Tasks', task_notification['location_label'])

        self.assertEqual(kanban_notification['source'], 'kanban')
        self.assertEqual(kanban_notification['source_label'], 'Kanban')
        self.assertEqual(kanban_notification['actor_label'], user.get_username())
        self.assertEqual(kanban_notification['title'], 'Karta z Kanban')
        self.assertEqual(kanban_notification['url'], reverse('kanban:view-task', args=[kanban_card.task_id]))
        self.assertNotIn('Zadanie innej osoby', [notification['title'] for notification in notifications])
