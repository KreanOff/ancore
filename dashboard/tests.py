from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from contacts.models import Company, Contact
from dashboard.views import _dashboard_notifications
from kanban.models import Kanban, KanbanProject, KanbanSection
from planner.models import CalendarEvent
from tasks.models import Task, TaskActivity, TaskProject, TaskSection, TaskTag
from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class DashboardViewTests(TestCase):
    def test_settings_requires_login(self):
        for route in ('settings',):
            for method in ('get', 'post'):
                with self.subTest(route=route, method=method):
                    response = getattr(self.client, method)(reverse(route))
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
        self.assertEqual(response.context['sidebar_mode'], 'settings')
        self.assertContains(response, 'data-sidebar-mode="settings"')
        self.assertContains(response, 'data-sidebar-navigation="workspace" hidden')
        self.assertNotContains(response, 'data-sidebar-navigation="settings" hidden')
        self.assertNotContains(response, 'class="settings-navigation"')
        self.assertContains(response, f'href="{reverse("settings")}#account"')
        self.assertContains(response, 'Ustawienia Ancore')
        self.assertNotContains(response, 'settings/project-fields/')
        self.assertNotContains(response, 'Wartości pól projektu')
        self.assertContains(response, 'data-sticky-note-toggle')
        self.assertNotContains(response, 'sidebar-sticker-toggle')
        self.assertContains(response, 'id="app-sticky-note"')
        self.assertContains(response, 'data-sticky-note-resize')
        self.assertContains(response, 'src="/static/js/sticky-note.js?v=')
        self.assertNotContains(response, 'href="/admin/"')
        self.assertContains(response, reverse('profile'))
        self.assertContains(response, 'Profil użytkownika')
        self.assertContains(response, reverse('add_account'))
        self.assertContains(response, 'Dodaj konto')
        self.assertNotContains(response, 'Konta w sesji')
        self.assertContains(response, 'Sesja')
        self.assertContains(response, f'action="{reverse("logout")}"')
        self.assertContains(response, 'Wyloguj się')
        self.assertContains(response, reverse('workplaces:workplaces'))
        self.assertContains(response, 'Zarządzaj Workspace')
        self.assertNotContains(response, 'Zespół i zaproszenia')
        self.assertContains(response, 'Konto i dostęp')
        self.assertContains(response, 'Powiadomienia')
        self.assertNotContains(response, 'Preferencje')
        self.assertNotContains(response, 'data-settings-group="preferences"')
        self.assertNotContains(response, 'data-settings-sidebar-switch')
        self.assertNotContains(response, 'data-settings-notifications')
        self.assertNotContains(response, 'Zwinięte menu boczne')
        self.assertNotContains(response, 'Język i region')
        self.assertNotContains(response, 'Szukaj ustawień')
        self.assertNotContains(response, 'Wkrótce')

    def test_settings_admin_link_is_visible_to_staff(self):
        user = get_user_model().objects.create_user(
            username='settings-admin', email='settings-admin@example.com',
            password='test-pass-123', is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('settings'))

        self.assertContains(response, f'href="{reverse("admin:index")}"')
        self.assertContains(response, 'Panel administracyjny')

    def test_home_renders_workspace_dashboard(self):
        user = get_user_model().objects.create_user(
            username='dashboard-user',
            email='dashboard-user@example.com',
            profile_photo='profile_photos/dashboard-user.webp',
            password='test-pass-123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/home.html')
        self.assertEqual(response.context['sidebar_mode'], 'workspace')
        self.assertContains(response, 'data-sidebar-navigation="settings" hidden')
        self.assertContains(response, 'Brak nadchodzących terminów')
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_retired_notifications_page_redirects_home(self):
        user = get_user_model().objects.create_user(
            username='notifications-user',
            email='notifications-user@example.com',
            password='test-pass-123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('notifications'))

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)

    def test_notifications_view_returns_panel_content_for_ajax_request(self):
        user = get_user_model().objects.create_user(
            username='notifications-panel-user',
            email='notifications-panel-user@example.com',
            password='test-pass-123',
        )
        TaskActivity.objects.create(
            task=Task.objects.create(user=user, title='Powiadomienie w panelu'),
            actor=user,
            kind='comment',
            action='commented',
            message='Komentarz w panelu',
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse('notifications'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload['count'], 1)
        self.assertEqual(payload['count'], payload['html'].count('data-notification-item'))
        self.assertIn('Powiadomienie w panelu', payload['html'])
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_dashboard_notifications_include_tasks_and_omit_legacy_kanban(self):
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
            kind='comment',
            action='commented',
            message='Komentarz do zadania',
        )
        kanban_card = Kanban.objects.create(user=user, title='Karta z Kanban')
        kanban_card.activities.create(actor=user, kind='comment', action='commented', message='Komentarz do karty')
        foreign = Task.objects.create(user=other_user, title='Zadanie innej osoby')
        foreign.activities.create(actor=other_user, kind='comment', action='commented', message='Obcy komentarz')

        notifications = _dashboard_notifications(user)
        task_notification = next(
            notification
            for notification in notifications
            if notification['source'] == 'tasks' and notification['object_id'] == task.task_id
        )

        self.assertEqual(task_notification['source'], 'tasks')
        self.assertEqual(task_notification['source_label'], 'Zadania')
        self.assertEqual(task_notification['actor_label'], user.get_username())
        self.assertEqual(task_notification['title'], 'Zadanie z Tasks')
        self.assertEqual(task_notification['url'], reverse('tasks:view-task', args=[task.task_id]) + f'?task_pk={task.pk}')
        self.assertIn('Zadanie z Tasks', task_notification['location_label'])

        self.assertFalse(any(item['source'] == 'kanban' for item in notifications))
        self.assertNotIn('Zadanie innej osoby', [notification['title'] for notification in notifications])


class GlobalSearchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='@search.owner',
            email='search-owner@example.com',
            password='test-pass-123',
            first_name='Anna',
            last_name='Nowak',
        )
        self.other_user = get_user_model().objects.create_user(
            username='@search.other',
            email='search-other@example.com',
            password='test-pass-123',
        )
        self.workplace = create_workplace_for_user(self.user, 'Studio Apollo', code='APOLLO')
        self.other_workplace = create_workplace_for_user(self.user, 'Archiwum', code='ARCH')
        self.foreign_workplace = create_workplace_for_user(self.other_user, 'Obce Apollo')
        session = self.client.session
        session['active_workplace_id'] = self.workplace.pk
        session.save()
        self.client.force_login(self.user)

    @staticmethod
    def _results_by_group(response):
        return {
            group['key']: group['results']
            for group in response.json()['groups']
        }

    def test_global_search_requires_login_and_short_query_is_not_executed(self):
        self.client.logout()

        response = self.client.get(reverse('global_search'), {'q': 'Apollo'})

        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(reverse('global_search'), {'q': 'A'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['groups'], [])
        self.assertEqual(response.json()['minimum_query_length'], 2)

    def test_global_search_finds_entities_across_current_workplace(self):
        company = Company.objects.create(
            owner=self.user,
            workplace=self.workplace,
            name='Apollo Partners',
            email='hello@apollo.example.com',
        )
        Contact.objects.create(
            user=self.user,
            workplace=self.workplace,
            first_name='Apolonia',
            last_name='Lis',
            company_record=company,
        )
        task_project = TaskProject.objects.create(
            user=self.user,
            workplace=self.workplace,
            name='Projekt Apollo',
            code='P-APOLLO',
            icon='rocket',
        )
        task_section = TaskSection.objects.create(project=task_project, title='Wdrożenie Apollo', icon='star')
        task = Task.objects.create(
            user=self.user,
            workplace=self.workplace,
            section=task_section,
            title='Przygotuj prezentację Apollo',
        )
        TaskTag.objects.create(
            user=self.user,
            workplace=self.workplace,
            name='Apollo VIP',
        )
        kanban_project = KanbanProject.objects.create(
            user=self.user,
            workplace=self.workplace,
            name='Apollo Delivery',
            icon='rocket',
        )
        kanban_section = KanbanSection.objects.create(project=kanban_project, title='Apollo Board', icon='star')
        card = Kanban.objects.create(
            user=self.user,
            workplace=self.workplace,
            section=kanban_section,
            title='Apollo card',
        )
        event = CalendarEvent.objects.create(
            user=self.user,
            workplace=self.workplace,
            title='Spotkanie Apollo',
            start=timezone.now() + timedelta(days=2),
            end=timezone.now() + timedelta(days=2, hours=1),
        )

        response = self.client.get(reverse('global_search'), {'q': 'Apollo'})

        self.assertEqual(response.status_code, 200)
        groups = self._results_by_group(response)
        self.assertIn('tasks', groups)
        self.assertIn('projects', groups)
        self.assertIn('groups', groups)
        self.assertIn('tags', groups)
        self.assertNotIn('kanban-projects', groups)
        self.assertNotIn('kanban-boards', groups)
        self.assertNotIn('kanban-cards', groups)
        self.assertNotIn('contacts', groups)
        self.assertNotIn('companies', groups)
        self.assertIn('calendar', groups)
        self.assertIn('workplaces', groups)
        for key in ('tasks', 'projects', 'groups'):
            with self.subTest(group=key):
                self.assertTrue(all(result['icon'] == '' for result in groups[key]))
        self.assertEqual(groups['tasks'][0]['url'], f'{scoped_workplace_app_path(self.workplace, "tasks")}view-task/{task.task_id}/?task_pk={task.pk}')
        self.assertIn(f'event={event.id}', groups['calendar'][0]['url'])
        calendar_response = self.client.get(groups['calendar'][0]['url'])
        self.assertEqual(calendar_response.context['calendar_config']['initialEventId'], event.id)
        self.assertEqual(calendar_response.context['calendar_config']['initialDay'], timezone.localtime(event.start).day)
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_global_search_is_scoped_to_active_workplace_and_owner(self):
        Task.objects.create(
            user=self.user,
            workplace=self.other_workplace,
            title='Sekret Apollo z archiwum',
        )
        Task.objects.create(
            user=self.other_user,
            workplace=self.foreign_workplace,
            title='Obcy sekret Apollo',
        )
        visible = Task.objects.create(
            user=self.user,
            workplace=self.workplace,
            title='Widoczny Apollo',
        )

        response = self.client.get(reverse('global_search'), {'q': 'Apollo'})

        groups = self._results_by_group(response)
        task_titles = [result['title'] for result in groups['tasks']]
        self.assertEqual(task_titles, [visible.title])
        all_titles = [
            result['title']
            for group in response.json()['groups']
            for result in group['results']
        ]
        self.assertNotIn('Sekret Apollo z archiwum', all_titles)
        self.assertNotIn('Obcy sekret Apollo', all_titles)

    def test_global_search_includes_application_navigation(self):
        response = self.client.get(reverse('global_search'), {'q': 'kalendarz'})

        groups = self._results_by_group(response)
        calendar_result = next(result for result in groups['navigation'] if result['title'] == 'Kalendarz')
        self.assertEqual(calendar_result['url'], scoped_workplace_app_path(self.workplace, 'calendar'))

    def test_global_search_returns_all_matches_below_limit(self):
        matching_titles = [f'Przygotować materiał {index:02d}' for index in range(12)]
        for title in matching_titles:
            Task.objects.create(
                user=self.user,
                workplace=self.workplace,
                title=title,
            )

        response = self.client.get(reverse('global_search'), {'q': 'Przygotować'})

        payload = response.json()
        task_group = next(group for group in payload['groups'] if group['key'] == 'tasks')
        self.assertCountEqual(
            [result['title'] for result in task_group['results']],
            matching_titles,
        )
        self.assertEqual(len(task_group['results']), len(matching_titles))
        self.assertFalse(task_group['has_more'])
        self.assertFalse(payload['truncated'])
