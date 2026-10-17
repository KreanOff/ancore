from datetime import timedelta

from django.contrib.auth import get_user_model
from spaces.testing import make_space, make_task
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from legacy.contacts.models import Company
from dashboard.views import _dashboard_notifications
from kanban.models import Kanban
from planner.models import CalendarEvent
from tasks.models import Task, TaskProject, TaskSection, TaskTag
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
        menu = response.content.decode().split('data-sidebar-navigation="settings"', 1)[1].split('</nav>', 1)[0]
        for label in ['Zarządzaj przestrzeniami', 'Zarządzaj pulpitami', 'Zarządzaj filtrami']:
            self.assertNotIn(label, menu)
        self.assertContains(response, f'href="{reverse("settings")}#account"')
        self.assertContains(response, 'Ustawienia Ancore')
        self.assertNotContains(response, 'settings/project-fields/')
        self.assertNotContains(response, 'Wartości pól projektu')
        self.assertContains(response, 'data-sticky-note-toggle')
        self.assertNotContains(response, 'sidebar-sticker-toggle')
        self.assertContains(response, 'id="app-sticky-note"')
        self.assertContains(response, 'data-sticky-note-resize')
        self.assertNotContains(response, 'src="/static/js/sticky-note.js?v=')
        self.assertContains(response, 'ancore-global-panels-data')
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
        self.assertContains(response, 'Postęp pracy')
        self.assertContains(response, 'Edytuj pulpit')
        self.assertTrue(response.context['dashboard'].is_default)
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
        user = get_user_model().objects.create_user(username='notifications-panel-user', email='notifications-panel@example.test')
        workplace = create_workplace_for_user(user, 'Panel')
        task = make_task(user=user, workplace=workplace, title='Powiadomienie w panelu')
        task.activities.create(actor=user, kind='comment', action='commented', message='Komentarz w panelu')
        self.client.force_login(user)
        response = self.client.get(reverse('notifications'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['count'], 1)
        self.assertEqual(payload['count'], payload['html'].count('data-notification-item'))
        self.assertIn(task.title, payload['html'])
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_dashboard_notifications_include_spaces_and_omit_historical_work(self):
        user = get_user_model().objects.create_user(username='dashboard-user', email='dashboard@example.test')
        other = get_user_model().objects.create_user(username='other-dashboard', email='other-dashboard@example.test')
        workplace = create_workplace_for_user(user, 'Pulpit')
        task = make_task(user=user, workplace=workplace, title='Zadanie Przestrzeni')
        task.activities.create(actor=user, kind='comment', action='commented', message='Komentarz')
        for model in (Task, Kanban):
            historical = model.objects.create(user=user, workplace=workplace, title='Historyczne zadanie')
            historical.activities.create(actor=user, kind='comment', action='commented', message='Wycofany komentarz')
        foreign = make_task(user=other, workplace=create_workplace_for_user(other, 'Obcy'), title='Niedostępne')
        foreign.activities.create(actor=other, kind='comment', action='commented')
        notifications = _dashboard_notifications(user)
        self.assertEqual(len(notifications), 1)
        notification = notifications[0]
        self.assertEqual(notification['source'], 'spaces')
        self.assertEqual(notification['title'], task.title)
        self.assertEqual(notification['actor_label'], user.get_full_name() or user.get_username())
        self.assertEqual(notification['url'], scoped_workplace_app_path(workplace, 'space', f'{task.space.slug}/tasks/{task.work_item.key}/?view=list'))
        self.assertIn(task.title, notification['location_label'])


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
        self.workplace = create_workplace_for_user(self.user, 'Studio Apollo')
        self.other_workplace = create_workplace_for_user(self.user, 'Archiwum')
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

    def test_global_search_finds_current_entities_and_omits_historical_work(self):
        space = make_space(user=self.user, workplace=self.workplace, name='Apollo space')
        task = make_task(user=self.user, workplace=self.workplace, space=space, title='Przygotuj prezentację Apollo')
        TaskTag.objects.create(user=self.user, workplace=self.workplace, space=space, name='Apollo VIP')
        project = TaskProject.objects.create(user=self.user, workplace=self.workplace, name='Historyczny Apollo')
        section = TaskSection.objects.create(project=project, title='Historyczna grupa Apollo')
        Task.objects.create(user=self.user, workplace=self.workplace, section=section, title='Historyczne zadanie Apollo')
        Company.objects.create(owner=self.user, workplace=self.workplace, name='Historyczna firma Apollo')
        Kanban.objects.create(user=self.user, workplace=self.workplace, title='Historyczna karta Apollo')
        event = CalendarEvent.objects.create(user=self.user, workplace=self.workplace, title='Spotkanie Apollo',
            start=timezone.now()+timedelta(days=2), end=timezone.now()+timedelta(days=2, hours=1))
        response = self.client.get(reverse('global_search'), {'q': 'Apollo'})
        self.assertEqual(response.status_code, 200)
        groups = self._results_by_group(response)
        self.assertTrue({'spaces', 'space_tasks', 'tags', 'calendar', 'workplaces'} <= groups.keys())
        self.assertFalse({'tasks', 'projects', 'groups', 'kanban-cards', 'contacts', 'companies'} & groups.keys())
        self.assertEqual(groups['space_tasks'][0]['url'], scoped_workplace_app_path(self.workplace, 'space', f'{space.slug}/tasks/{task.work_item.key}/?view=list'))
        calendar = self.client.get(groups['calendar'][0]['url'])
        self.assertEqual(calendar.context['calendar_config']['initialEventId'], event.pk)
        self.assertEqual(calendar.context['calendar_config']['initialDay'], timezone.localtime(event.start).day)
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_global_search_is_scoped_to_active_workplace_and_owner(self):
        make_task(
            user=self.user,
            workplace=self.other_workplace,
            title='Sekret Apollo z archiwum',
        )
        make_task(
            user=self.other_user,
            workplace=self.foreign_workplace,
            title='Obcy sekret Apollo',
        )
        visible = make_task(
            user=self.user,
            workplace=self.workplace,
            title='Widoczny Apollo',
        )

        response = self.client.get(reverse('global_search'), {'q': 'Apollo'})

        groups = self._results_by_group(response)
        task_titles = [result['title'] for result in groups['space_tasks']]
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
            make_task(
                user=self.user,
                workplace=self.workplace,
                title=title,
            )

        response = self.client.get(reverse('global_search'), {'q': 'Przygotować'})

        payload = response.json()
        task_group = next(group for group in payload['groups'] if group['key'] == 'space_tasks')
        self.assertCountEqual(
            [result['title'] for result in task_group['results']],
            matching_titles,
        )
        self.assertEqual(len(task_group['results']), len(matching_titles))
        self.assertFalse(task_group['has_more'])
        self.assertFalse(payload['truncated'])
