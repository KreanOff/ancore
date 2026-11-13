from datetime import timedelta

from django.contrib.auth import get_user_model
from spaces.testing import make_space, make_task
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.views import _dashboard_notifications
from planner.models import CalendarEvent
from tasks.models import TaskTag
from workplaces.models import WorkplaceMembership, create_workplace_for_user
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
        if not user.owned_workplaces.exists():
            create_workplace_for_user(user, 'Testowy Workspace')
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
        self.assertIn(f'href="{reverse("workplaces:workplaces")}"', menu)
        self.assertIn('data-settings-category="all" aria-current="page"', menu)
        self.assertNotIn('data-settings-category="workspace" aria-current="page"', menu)
        self.assertNotIn(f'href="{reverse("settings")}#workspace"', menu)
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
        self.assertNotContains(response, '/accounts/profile/add-account/')
        self.assertNotContains(response, 'Dodaj konto')
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
        if not user.owned_workplaces.exists():
            create_workplace_for_user(user, 'Testowy Workspace')
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
        if not user.owned_workplaces.exists():
            create_workplace_for_user(user, 'Testowy Workspace')
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
        if not user.owned_workplaces.exists():
            create_workplace_for_user(user, 'Testowy Workspace')
        self.client.force_login(user)

        response = self.client.get(reverse('notifications'))

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)

    def test_notifications_view_returns_panel_content_for_ajax_request(self):
        user = get_user_model().objects.create_user(username='notifications-panel-user', email='notifications-panel@example.test')
        workplace = create_workplace_for_user(user, 'Panel')
        task = make_task(user=user, workplace=workplace, title='Powiadomienie w panelu')
        task.activities.create(actor=user, kind='comment', action='commented', message='Komentarz w panelu')
        if not user.owned_workplaces.exists():
            create_workplace_for_user(user, 'Testowy Workspace')
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


class SettingsSpacesCategoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='space-settings-owner', email='space-settings-owner@example.test')
        cls.member = users.objects.create_user(username='space-settings-member', email='space-settings-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Workspace ustawień przestrzeni')
        cls.other = create_workplace_for_user(cls.owner, 'Drugi Workspace ustawień')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.spaces = [make_space(user=cls.owner, workplace=cls.workspace, name=f'Przestrzeń {i:02d}', visibility='public') for i in range(25)]
        cls.hidden = make_space(user=cls.owner, workplace=cls.workspace, name='Ukryta przestrzeń', visibility='private', private_owner=cls.owner)
        cls.foreign = make_space(user=cls.owner, workplace=cls.other, name='Przestrzeń innego Workspace', visibility='public')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def api(self, target, scoped=True):
        endpoint = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
        return self.client.get(endpoint, {'url': target})

    def test_general_settings_have_only_a_shortcut_without_loading_space_rows(self):
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.context['settings_category'], 'all')
        self.assertEqual(response.context['settings_spaces'], [])
        self.assertIsNone(response.context['settings_spaces_page'])
        self.assertContains(response, 'settings-spaces-shortcut-title')
        self.assertNotContains(response, 'id="settings-spaces-title"')
        data = self.api(reverse('settings')).json()['data']
        self.assertEqual(data['category'], 'all')
        self.assertEqual(data['spaces'], [])
        self.assertIsNone(data['pagination'])
        shortcut = next(row for row in data['rows'] if row['category'] == 'spaces')
        self.assertEqual(shortcut['url'], reverse('settings') + '?section=spaces')
        self.assertEqual(data['settings_spaces_url'], shortcut['url'])

    def test_space_category_has_a_cumulative_twenty_item_window_and_keeps_the_section(self):
        target = reverse('settings') + '?section=spaces'
        response = self.client.get(target)
        self.assertEqual(response.context['settings_category'], 'spaces')
        self.assertEqual(len(response.context['settings_spaces']), 20)
        self.assertEqual(response.context['settings_spaces_page'].paginator.count, 25)
        self.assertContains(response, 'data-settings-category="spaces" aria-current="page"')
        self.assertNotContains(response, 'data-settings-category="all" aria-current="page"')
        self.assertNotContains(response, 'data-settings-account-summary')
        self.assertContains(response, 'Pokaż więcej')
        self.assertEqual(response.context['settings_spaces_next'], target + '&limit=25')
        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                payload = self.api(target, scoped=scoped).json()
                self.assertEqual(payload['title'], 'Przestrzenie')
                data = payload['data']
                self.assertEqual(data['category'], 'spaces')
                self.assertEqual([row['name'] for row in data['spaces']], [space.name for space in self.spaces[:20]])
                self.assertEqual(data['pagination']['count'], 25)
                self.assertEqual(data['pagination']['next'], target + '&limit=25')
                more = self.api(data['pagination']['next'], scoped=scoped).json()['data']
                self.assertEqual([row['name'] for row in more['spaces']], [space.name for space in self.spaces])
                self.assertEqual(more['spaces'][:20], data['spaces'])
                self.assertEqual(more['pagination']['next'], '')
                self.assertEqual(more['pagination']['end'], 25)

    def test_space_category_excludes_private_and_other_workspace_data(self):
        response = self.api(reverse('settings') + '?section=spaces&limit=100')
        data = response.json()['data']
        self.assertEqual(len(data['spaces']), 25)
        self.assertNotContains(response, self.hidden.slug)
        self.assertNotContains(response, self.foreign.slug)
        self.assertTrue(all(row['url'].startswith(scoped_workplace_app_path(self.workspace, 'space')) for row in data['spaces']))
        self.assertTrue(all(row['url'].endswith('/?view=settings') for row in data['spaces']))
        self.assertEqual(self.client.session['active_workplace_id'], self.workspace.pk)

    def test_disabled_module_has_no_shortcut_or_data_even_for_direct_category_url(self):
        self.workspace.disabled_modules = ['spaces']
        self.workspace.save(update_fields=['disabled_modules'])
        response = self.client.get(reverse('settings') + '?section=spaces')
        self.assertEqual(response.context['settings_spaces'], [])
        self.assertContains(response, 'Brak dostępnych przestrzeni w tym Workspace.')
        self.assertNotContains(response, 'data-settings-category="spaces"')
        section = response.content.decode().split('data-settings-spaces-directory', 1)[1].split('id="app-notifications"', 1)[0]
        self.assertNotIn('Pokaż więcej', section)
        data = self.api(reverse('settings') + '?section=spaces').json()['data']
        self.assertEqual(data['spaces'], [])
        self.assertEqual(data['pagination']['count'], 0)
        general = self.api(reverse('settings')).json()['data']
        self.assertFalse(any(row['category'] == 'spaces' for row in general['rows']))


    def test_directory_rows_use_real_space_fields_and_only_visible_task_counts(self):
        space = self.spaces[0]
        space.description = '<p>Opis <strong>przestrzeni</strong></p>'
        space.save(update_fields=['description'])
        make_task(user=self.owner, workplace=self.workspace, space=space, title='Dostępne zadanie')
        hidden = make_task(user=self.owner, workplace=self.workspace, space=space, title='Prywatne zadanie', visibility='private', private_owner=self.owner)
        make_task(user=self.owner, workplace=self.workspace, space=space, title='Dziecko prywatnego zadania', parent=hidden)
        target = reverse('settings') + '?section=spaces&q=' + space.key
        row = self.api(target).json()['data']['spaces'][0]
        self.assertEqual(set(row), {'id', 'name', 'url', 'avatar', 'key', 'description', 'kind_label', 'template_label', 'item_count', 'can_manage', 'edit_url', 'delete_url'})
        self.assertEqual((row['id'], row['name'], row['key']), (space.pk, space.name, space.key))
        self.assertEqual(row['description'], 'Opis przestrzeni')
        self.assertEqual(row['kind_label'], space.get_kind_display())
        self.assertEqual(row['template_label'], space.get_template_display())
        self.assertIn('preset_class', row['avatar'])
        self.assertEqual(row['item_count'], 1)
        response = self.client.get(target)
        self.assertContains(response, 'settings-spaces-sheet')
        self.assertContains(response, 'app-data-table')
        self.assertContains(response, 'data-settings-spaces-search')
        self.assertNotContains(response, 'class="icon-credit"')
        self.assertNotContains(response, 'Wybierz przestrzeń, aby otworzyć')
        header = response.content.decode().split('role="table" aria-label="Lista przestrzeni"', 1)[1].split('role="rowgroup"', 1)[0]
        positions = [header.index(f'data-column="{column}"') for column in ('select', 'name', 'key', 'description', 'kind', 'template', 'tasks_count')]
        self.assertEqual(positions, sorted(positions))

    def test_search_filters_all_visible_spaces_before_the_twenty_item_window(self):
        from urllib.parse import urlencode
        last = self.spaces[-1]
        last.description = '<p>Unikatowy szukany opis</p>'
        last.save(update_fields=['description'])
        self.hidden.description = last.description
        self.hidden.save(update_fields=['description'])
        self.foreign.description = last.description
        self.foreign.save(update_fields=['description'])
        for query in (last.name.lower(), last.key.lower(), 'szukany opis'):
            with self.subTest(query=query):
                target = reverse('settings') + '?' + urlencode({'section': 'spaces', 'q': query})
                data = self.api(target).json()['data']
                self.assertEqual(data['query'], query)
                self.assertEqual([row['id'] for row in data['spaces']], [last.pk])
                self.assertEqual(data['pagination']['count'], 1)
                self.assertEqual(data['pagination']['next'], '')
        missing = self.client.get(reverse('settings'), {'section': 'spaces', 'q': 'nieistniejąca wartość'})
        self.assertEqual(missing.context['settings_spaces'], [])
        self.assertContains(missing, 'Nie znaleziono przestrzeni.')
        self.assertContains(missing, 'value="nieistniejąca wartość"')

    def test_load_more_preserves_search_and_section_and_keeps_existing_rows(self):
        from urllib.parse import parse_qs, urlencode, urlsplit
        target = reverse('settings') + '?' + urlencode({'section': 'spaces', 'q': 'Przestrzeń'})
        data = self.api(target).json()['data']
        self.assertEqual(len(data['spaces']), 20)
        next_url = data['pagination']['next']
        self.assertEqual(parse_qs(urlsplit(next_url).query), {'section': ['spaces'], 'q': ['Przestrzeń'], 'limit': ['25']})
        more = self.api(next_url).json()['data']
        self.assertEqual(more['spaces'][:20], data['spaces'])
        self.assertEqual(len(more['spaces']), 25)
        self.assertEqual(more['query'], 'Przestrzeń')
        self.assertEqual(more['pagination']['next'], '')
