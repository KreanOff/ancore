from datetime import date, datetime, time, timedelta
import json
import re
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from spaces.defaults import configuration_name_color
from spaces.models import SpaceMembership, SpaceTask, SpaceTaskMembership
from spaces.testing import make_space
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import CalendarEvent


@override_settings(TIME_ZONE='Europe/Warsaw')
class TodaySidebarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='sidebar-owner', email='sidebar-owner@example.test')
        cls.member = users.objects.create_user(username='sidebar-member', email='sidebar-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Panel dnia')
        cls.other = create_workplace_for_user(cls.owner, 'Inny panel')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Praca')
        cls.today = date(2026, 11, 12)

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()
        self.today_patch = patch('planner.sidebar.timezone.localdate', return_value=self.today)
        self.today_patch.start()
        self.addCleanup(self.today_patch.stop)

    def url(self, app='calendar', suffix='sidebar/', workspace=None):
        return scoped_workplace_app_path(workspace or self.workspace, app, suffix)

    def task(self, **values):
        return SpaceTask.objects.create(**{
            'space': self.space, 'created_by': self.owner, 'title': 'Dzisiejsze zadanie',
            'due_at': timezone.make_aware(datetime.combine(self.today, time(9))),
            **values,
        })

    def event(self, **values):
        start = timezone.make_aware(datetime.combine(self.today, time(9)))
        return CalendarEvent.objects.create(**{
            'user': self.owner, 'workplace': self.workspace, 'title': 'Dzisiejsze wydarzenie',
            'start': start, 'end': start + timedelta(hours=1), **values,
        })

    def api(self, target=None, *, client=None):
        return (client or self.client).get(self.url('api', 'v1/page/'), {'url': target or self.url()})

    def test_endpoint_returns_current_date_timezone_and_empty_task_window(self):
        response = self.api()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'no-store')
        payload = response.json()
        self.assertEqual(payload['status'], 'success')
        self.assertEqual(payload['today'], self.today.isoformat())
        self.assertEqual(payload['time_zone'], 'Europe/Warsaw')
        self.assertTrue(payload['tasks_enabled'])
        self.assertEqual(payload['entries'], [])
        self.assertEqual(payload['groups'], [])
        self.assertEqual(payload['pagination']['count'], 0)
        self.assertFalse(payload['pagination']['has_next'])

    def test_today_tasks_include_unassigned_and_other_assignees_with_stable_links(self):
        unassigned = self.task(title='Bez wykonawcy')
        assigned = self.task(title='Inny wykonawca', assignee=self.owner)
        parent = self.task(due_at=None)
        child = self.task(title='Podzadanie', parent=parent)
        payload = self.api().json()
        self.assertEqual([item['id'] for item in payload['entries']], [f'tasks:{task.pk}' for task in (unassigned, assigned, child)])
        row = payload['entries'][0]
        self.assertEqual(row['subtitle'], f'{unassigned.work_item.key} · {self.space.name}')
        self.assertEqual(row['key'], unassigned.work_item.key)
        self.assertEqual(row['space_id'], self.space.pk)
        self.assertEqual(row['space_name'], self.space.name)
        self.assertEqual(row['priority'], unassigned.priority)
        self.assertEqual(row['priority_label'], unassigned.get_priority_display())
        self.assertEqual(row['status'], unassigned.status)
        self.assertEqual(row['source'], 'tasks')
        self.assertEqual(row['color'], '')
        self.assertEqual(row['time_label'], '09:00')
        self.assertEqual(row['starts_at'], '2026-11-12T09:00:00+01:00')
        self.assertIn(f'/space/{self.space.slug}/tasks/{unassigned.work_item.key}/', row['url'])
        child_response = self.client.get(payload['entries'][2]['url'], follow=True)
        self.assertEqual(child_response.status_code, 200)
        self.assertEqual(child_response.context['task'].pk, parent.pk)
        self.assertEqual(child_response.context['task_tab'], 'subtasks')

    def test_task_appearance_uses_configured_status_without_changing_category(self):
        task = self.task(priority='high', status='in_progress')
        item = task.work_item
        config = self.space.configuration
        definition = next(row for row in config.settings['statuses'] if row['key'] == item.status)
        definition.update(label='Weryfikacja', color='#A153CC')
        config.save(update_fields=['settings'])

        row, = self.api().json()['entries']
        self.assertEqual(row['priority'], 'high')
        self.assertEqual(row['priority_label'], task.get_priority_display())
        self.assertEqual(row['status'], 'in_progress')
        self.assertEqual(row['status_label'], 'Weryfikacja')
        self.assertEqual(row['status_color'], '#a153cc')

        definition['color'] = ''
        config.save(update_fields=['settings'])
        row, = self.api().json()['entries']
        self.assertEqual(row['status_color'], configuration_name_color('statuses', definition))
        task.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(task.status, 'in_progress')
        self.assertEqual(item.status, definition['key'])

    def test_list_respects_workspace_private_space_task_and_parent_access(self):
        visible = self.task()
        other_space = make_space(user=self.owner, workplace=self.other, name='Poza Workspace')
        self.task(space=other_space)
        private_space = make_space(user=self.owner, workplace=self.workspace, name='Prywatna przestrzeń',
                                   visibility='private', private_owner=self.owner)
        hidden_space_task = self.task(space=private_space, assignee=self.member)
        hidden_task = self.task(visibility='private', private_owner=self.owner, assignee=self.member)
        child = self.task(parent=hidden_task)
        SpaceTaskMembership.objects.create(task=child, user=self.member)
        payload = self.api().json()
        self.assertEqual([item['id'] for item in payload['entries']], [f'tasks:{visible.pk}'])
        self.assertEqual(payload['groups'], [{
            'id': f'space:{self.space.pk}', 'label': self.space.name, 'entries': payload['entries'],
        }])

        SpaceMembership.objects.create(space=private_space, user=self.member, role='observer')
        SpaceTaskMembership.objects.create(task=hidden_task, user=self.member, role='observer')
        self.assertCountEqual([item['id'] for item in self.api().json()['entries']],
                              [f'tasks:{task.pk}' for task in (visible, hidden_space_task, hidden_task, child)])

    def test_only_open_tasks_with_today_deadlines_are_included(self):
        midnight = timezone.make_aware(datetime.combine(self.today, time.min))
        included = [self.task(due_at=midnight), self.task(due_at=midnight + timedelta(hours=23, minutes=59))]
        for values in ({'due_at': None}, {'due_at': midnight - timedelta(seconds=1)},
                       {'due_at': midnight + timedelta(days=1)}, {'status': 'closed'}):
            self.task(**values)
        self.assertEqual([item['id'] for item in self.api().json()['entries']], [f'tasks:{item.pk}' for item in included])

    def test_warsaw_day_boundaries_include_both_dst_changes(self):
        for today, first, last in (
            (date(2026, 3, 29), '2026-03-28T23:00:00+00:00', '2026-03-29T21:59:59+00:00'),
            (date(2026, 10, 25), '2026-10-24T22:00:00+00:00', '2026-10-25T22:59:59+00:00'),
        ):
            with self.subTest(today=today), patch('planner.sidebar.timezone.localdate', return_value=today):
                first, last = datetime.fromisoformat(first), datetime.fromisoformat(last)
                included = [self.task(due_at=first), self.task(due_at=last)]
                self.task(due_at=first - timedelta(seconds=1))
                self.task(due_at=last + timedelta(seconds=1))
                self.assertEqual([item['id'] for item in self.api().json()['entries']],
                                 [f'tasks:{item.pk}' for item in included])

    def test_task_window_loads_twenty_then_all_without_main_page_limit_collisions(self):
        tasks = [self.task(title=f'Zadanie {index}') for index in range(23)]
        first = self.api(self.url() + '?limit=100&page=50').json()
        self.assertEqual([item['id'] for item in first['entries']], [f'tasks:{task.pk}' for task in tasks[:20]])
        self.assertEqual(first['pagination']['count'], 23)
        self.assertEqual(first['pagination']['end'], 20)
        self.assertEqual(first['pagination']['next_url'], self.url() + '?sidebar_task_limit=23')
        last = self.api(first['pagination']['next_url']).json()
        self.assertEqual([item['id'] for item in last['entries']], [f'tasks:{task.pk}' for task in tasks])
        self.assertFalse(last['pagination']['has_next'])
        self.assertEqual(last['pagination']['next_url'], '')
        for value in ('-1', 'not-a-number', '0'):
            with self.subTest(value=value):
                self.assertEqual(len(self.api(self.url() + '?sidebar_task_limit=' + value).json()['entries']), 20)

    def test_normal_scoped_and_api_routes_keep_workspace_and_revoked_access(self):
        task = self.task()
        for url in (reverse('planner:sidebar'), self.url()):
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['today'], self.today.isoformat())
                self.assertEqual([item['id'] for item in response.json()['entries']], [f'tasks:{task.pk}'])
        self.assertEqual(self.api(self.url(workspace=self.other)).status_code, 403)
        self.membership.delete()
        self.assertEqual(self.api().status_code, 403)

    def test_endpoint_requires_session_is_read_only_and_handles_disabled_modules(self):
        self.task()
        event = self.event()
        self.assertEqual(self.api(client=Client()).status_code, 401)
        response = self.client.post(self.url('api', 'v1/page/') + '?' + urlencode({'url': self.url()}), {})
        self.assertEqual(response.status_code, 405)
        self.workspace.disabled_modules = ['spaces']
        self.workspace.save(update_fields=['disabled_modules'])
        response = self.api()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['tasks_enabled'])
        self.assertEqual([item['id'] for item in response.json()['entries']], [f'events:{event.pk}'])
        self.assertEqual(response.json()['groups'], [{
            'id': 'events', 'label': 'Kalendarz', 'entries': response.json()['entries'],
        }])
        self.workspace.disabled_modules = ['calendar']
        self.workspace.save(update_fields=['disabled_modules'])
        self.assertEqual(self.api().status_code, 404)

    def test_guest_can_read_visible_today_tasks(self):
        task = self.task()
        event = self.event()
        self.membership.role = 'guest'
        self.membership.save(update_fields=['role'])
        payload = self.api().json()
        self.assertEqual(payload['today'], self.today.isoformat())
        self.assertEqual([item['id'] for item in payload['entries']], [f'events:{event.pk}', f'tasks:{task.pk}'])

    def test_first_render_keeps_mini_calendar_and_adds_today_tasks(self):
        task = self.task(title='Zadanie widoczne w panelu')
        response = self.client.get(self.url('spaces', ''), {'q': 'praca', 'sidebar_month': '2027-01'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-today-sidebar')
        self.assertContains(response, 'Plan na dziś')
        self.assertContains(response, task.title)
        self.assertContains(response, task.work_item.key)
        self.assertNotContains(response, 'today-sidebar__header')
        self.assertNotContains(response, 'Otwórz kalendarz')
        self.assertContains(response, 'styczeń 2027')
        self.assertContains(response, '?date=2027-01-01')
        self.assertContains(response, 'q=praca&amp;sidebar_month=2026-12')
        self.assertContains(response, 'q=praca&amp;sidebar_month=2026-11')

    def test_first_render_more_keeps_current_page_filters_and_calendar_month(self):
        for index in range(23):
            self.task(title=f'Panel {index}')
        url = self.url('spaces', '')
        response = self.client.get(url, {'q': 'praca', 'sidebar_month': '2027-01', 'limit': 40})
        self.assertContains(response, 'class="today-sidebar__task"', count=20)
        self.assertContains(response, 'q=praca&amp;sidebar_month=2027-01&amp;limit=40&amp;sidebar_task_limit=23')
        response = self.client.get(url, {'sidebar_task_limit': 23})
        self.assertContains(response, 'class="today-sidebar__task"', count=23)

    def test_shell_bootstrap_keeps_task_window_when_react_reloads_first_render(self):
        for index in range(24):
            self.task(title=f'Panel {index}')
        for params in ({'sidebar_task_limit': '24'}, {'sidebar_task_page': '2'},
                       {'sidebar_task_limit': '24', 'sidebar_task_page': '2'}):
            with self.subTest(params=params):
                response = self.client.get(self.url('spaces', ''), {
                    'q': 'praca', 'sidebar_month': '2027-01', 'limit': 40, 'page': 3, **params,
                })
                self.assertContains(response, 'class="today-sidebar__task"', count=24)
                script = re.search(r'<script[^>]+id="ancore-global-panels-data"[^>]*>(.*?)</script>',
                                   response.content.decode(), re.S)
                self.assertIsNotNone(script)
                url = json.loads(script.group(1))['shell']['sidebar_url']
                self.assertEqual(url, self.url() + '?' + urlencode(params))
                payload = self.api(url).json()
                self.assertEqual(len(payload['entries']), 24)
                self.assertEqual(payload['pagination']['end'], 24)

    def test_sidebar_url_encodes_only_its_task_window_parameters(self):
        response = self.client.get(self.url('spaces', ''), {
            'sidebar_task_limit': '24&limit=99', 'sidebar_task_page': '2#ignored', 'limit': 40,
        })
        script = re.search(r'<script[^>]+id="ancore-global-panels-data"[^>]*>(.*?)</script>',
                           response.content.decode(), re.S)
        self.assertIsNotNone(script)
        url = json.loads(script.group(1))['shell']['sidebar_url']
        self.assertEqual(url, self.url() + '?sidebar_task_limit=24%26limit%3D99&sidebar_task_page=2%23ignored')

    def test_first_render_empty_plan_and_events_with_disabled_spaces(self):
        response = self.client.get(self.url('spaces', ''))
        self.assertContains(response, 'Brak zadań i wydarzeń na dziś.')
        self.workspace.disabled_modules = ['spaces']
        self.workspace.save(update_fields=['disabled_modules'])
        event = self.event(title='Wydarzenie bez modułu Przestrzeni', color='#A153CC')
        self.task(title='Zadanie wyłączonego modułu')
        response = self.client.get(self.url('resources', ''))
        self.assertContains(response, 'data-today-sidebar')
        self.assertContains(response, 'Plan na dziś')
        self.assertContains(response, event.title)
        self.assertContains(response, 'background-color: #a153cc')
        self.assertNotContains(response, 'Zadanie wyłączonego modułu')
        self.assertNotContains(response, 'Brak zadań i wydarzeń na dziś.')

    def test_mixed_agenda_has_all_day_first_then_chronological_tasks_and_events(self):
        midnight = timezone.make_aware(datetime.combine(self.today, time.min))
        early_task = self.task(due_at=midnight, pk=987654)
        timed = self.event(start=midnight + timedelta(hours=9), color='#A153CC', pk=987654)
        all_day = self.event(start=midnight, end=midnight + timedelta(hours=23, minutes=59),
                             all_day=True, color='blue')
        continuing = self.event(start=midnight - timedelta(hours=1), end=midnight + timedelta(hours=1))
        later_task = self.task(due_at=timed.start)
        payload = self.api().json()
        self.assertEqual([entry['id'] for entry in payload['entries']], [
            f'events:{all_day.pk}', f'events:{continuing.pk}', f'tasks:{early_task.pk}',
            f'events:{timed.pk}', f'tasks:{later_task.pk}',
        ])
        self.assertEqual(len({entry['id'] for entry in payload['entries']}), 5)
        day_entry, continuing_entry, task_entry, event_entry, _ = payload['entries']
        self.assertEqual(day_entry['time_label'], 'Cały dzień')
        self.assertEqual(day_entry['color'], '#4f7edb')
        self.assertEqual(continuing_entry['time_label'], '11.11, 23:00')
        self.assertEqual(task_entry['subtitle'], f'{early_task.work_item.key} · {self.space.name}')
        self.assertEqual(task_entry['color'], '')
        self.assertEqual(event_entry['color'], '#a153cc')
        self.assertEqual(event_entry['subtitle'], 'Kalendarz')
        self.assertEqual(event_entry['source'], 'events')
        self.assertEqual(event_entry['url'], self.url('calendar', '') + f'?event={timed.pk}')
        response = self.client.get(event_entry['url'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['calendar_config']['initialEventId'], timed.pk)

    def test_event_overlap_excludes_end_midnight_and_includes_today_points_and_all_day(self):
        for today, first, last in (
            (self.today, '2026-11-11T23:00:00+00:00', '2026-11-12T22:59:59+00:00'),
            (date(2026, 3, 29), '2026-03-28T23:00:00+00:00', '2026-03-29T21:59:59+00:00'),
            (date(2026, 10, 25), '2026-10-24T22:00:00+00:00', '2026-10-25T22:59:59+00:00'),
        ):
            with self.subTest(today=today), patch('planner.sidebar.timezone.localdate', return_value=today):
                first, last = datetime.fromisoformat(first), datetime.fromisoformat(last)
                point = self.event(start=first, end=first)
                ending = self.event(start=last, end=last)
                spanning = self.event(start=first - timedelta(days=1), end=last + timedelta(days=1))
                all_day = self.event(start=first, end=last, all_day=True)
                self.event(start=first - timedelta(hours=1), end=first)
                self.event(start=first - timedelta(seconds=1), end=first - timedelta(seconds=1))
                self.event(start=last + timedelta(seconds=1), end=last + timedelta(seconds=1))
                self.assertEqual([entry['id'] for entry in self.api().json()['entries']],
                                 [f'events:{event.pk}' for event in (all_day, spanning, point, ending)])

    def test_mixed_entries_order_repeated_dst_hours_by_actual_instant(self):
        with patch('planner.sidebar.timezone.localdate', return_value=date(2026, 10, 25)):
            event = self.event(start=datetime.fromisoformat('2026-10-25T00:45:00+00:00'),
                               end=datetime.fromisoformat('2026-10-25T01:00:00+00:00'))
            task = self.task(due_at=datetime.fromisoformat('2026-10-25T01:15:00+00:00'))
            entries = self.api().json()['entries']
            self.assertEqual([entry['id'] for entry in entries], [f'events:{event.pk}', f'tasks:{task.pk}'])
            self.assertEqual([entry['time_label'] for entry in entries], ['02:45', '02:15'])
            self.assertTrue(entries[0]['starts_at'].endswith('+02:00'))
            self.assertTrue(entries[1]['starts_at'].endswith('+01:00'))

    def test_event_feed_keeps_workspace_and_owner_scope_and_safe_colors(self):
        visible = self.event(color='green')
        invalid = self.event(color='bad;--x:1')
        self.event(workplace=self.other, title='Inny Workspace')
        self.event(user=self.member, title='Nieprawidłowy właściciel danych')
        payload = self.api().json()
        self.assertEqual([entry['id'] for entry in payload['entries']], [f'events:{visible.pk}', f'events:{invalid.pk}'])
        self.assertEqual([entry['color'] for entry in payload['entries']], ['#43a36a', CalendarEvent.DEFAULT_COLOR])

    def test_mixed_window_fetches_bounded_sources_and_loads_all_entries_without_duplicates(self):
        midnight = timezone.make_aware(datetime.combine(self.today, time.min))
        expected = []
        for index in range(12):
            event = self.event(start=midnight + timedelta(minutes=2 * index),
                               end=midnight + timedelta(minutes=2 * index + 1))
            task = self.task(due_at=midnight + timedelta(minutes=2 * index + 1))
            expected.extend([f'events:{event.pk}', f'tasks:{task.pk}'])
        with CaptureQueriesContext(connection) as queries:
            first = self.api().json()
        self.assertEqual([entry['id'] for entry in first['entries']], expected[:20])
        self.assertEqual(first['pagination']['count'], 24)
        self.assertEqual([group['id'] for group in first['groups']], [f'space:{self.space.pk}', 'events'])
        self.assertEqual([len(group['entries']) for group in first['groups']], [10, 10])
        for table in ('planner_calendarevent', 'spaces_workitem'):
            reads = [query['sql'] for query in queries if f'FROM "{table}"' in query['sql']
                     and 'COUNT(' not in query['sql']]
            self.assertEqual(len(reads), 1, reads)
            self.assertIn('LIMIT 20', reads[0])
        last = self.api(first['pagination']['next_url']).json()
        ids = [entry['id'] for entry in last['entries']]
        self.assertEqual(ids, expected)
        self.assertEqual(len(set(ids)), 24)
        self.assertFalse(last['pagination']['has_next'])
        self.assertEqual([len(group['entries']) for group in last['groups']], [12, 12])
        for before, after in zip(first['groups'], last['groups']):
            self.assertEqual(before['id'], after['id'])
            self.assertEqual(before['entries'], after['entries'][:len(before['entries'])])

    def test_groups_keep_space_identity_and_first_task_order_with_calendar_last(self):
        duplicate = make_space(user=self.owner, workplace=self.workspace, name=self.space.name)
        calendar_space = make_space(user=self.owner, workplace=self.workspace, name='Kalendarz')
        make_space(user=self.owner, workplace=self.workspace, name='Bez dzisiejszych zadań')
        midnight = timezone.make_aware(datetime.combine(self.today, time.min))
        event = self.event(start=midnight, end=midnight + timedelta(days=1), all_day=True)
        second_space_first = self.task(space=duplicate, due_at=midnight + timedelta(hours=8))
        first_space_task = self.task(due_at=midnight + timedelta(hours=9))
        second_space_later = self.task(space=duplicate, due_at=midnight + timedelta(hours=10))
        calendar_task = self.task(space=calendar_space, due_at=midnight + timedelta(hours=11))
        payload = self.api().json()
        groups = payload['groups']
        self.assertEqual([group['id'] for group in groups], [
            f'space:{duplicate.pk}', f'space:{self.space.pk}', f'space:{calendar_space.pk}', 'events',
        ])
        self.assertEqual([group['label'] for group in groups], [self.space.name, self.space.name, 'Kalendarz', 'Kalendarz'])
        self.assertEqual([[entry['id'] for entry in group['entries']] for group in groups], [
            [f'tasks:{second_space_first.pk}', f'tasks:{second_space_later.pk}'],
            [f'tasks:{first_space_task.pk}'], [f'tasks:{calendar_task.pk}'], [f'events:{event.pk}'],
        ])
        self.assertCountEqual([entry for group in groups for entry in group['entries']], payload['entries'])

    def test_groups_do_not_expose_tasks_outside_the_loaded_shared_window(self):
        midnight = timezone.make_aware(datetime.combine(self.today, time.min))
        for index in range(20):
            self.event(start=midnight + timedelta(minutes=index), end=midnight + timedelta(minutes=index + 1))
        task = self.task(due_at=midnight + timedelta(hours=9))
        first = self.api().json()
        self.assertEqual(first['pagination']['count'], 21)
        self.assertEqual(first['groups'], [{'id': 'events', 'label': 'Kalendarz', 'entries': first['entries']}])
        self.assertEqual(len(first['groups'][0]['entries']), 20)

        last = self.api(first['pagination']['next_url']).json()
        self.assertEqual([group['id'] for group in last['groups']], [f'space:{self.space.pk}', 'events'])
        self.assertEqual([entry['id'] for entry in last['groups'][0]['entries']], [f'tasks:{task.pk}'])
        self.assertEqual(last['groups'][1], first['groups'][0])
        self.assertFalse(last['pagination']['has_next'])

    def test_first_render_combines_events_and_tasks_in_the_same_plan(self):
        event = self.event(title='Wspólne wydarzenie', color='#2563eb')
        task = self.task(title='Wspólne zadanie')
        for url in (self.url('calendar', ''), self.url('spaces', '')):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'class="today-sidebar__tasks"', count=1)
                self.assertContains(response, 'class="today-sidebar__task"', count=2)
                self.assertContains(response, 'Plan na dziś')
                self.assertContains(response, event.title)
                self.assertContains(response, task.title)
                self.assertContains(response, 'background-color: #2563eb')
                self.assertContains(response, self.url('calendar', '') + f'?event={event.pk}')
                self.assertContains(response, f'{task.work_item.key} · {self.space.name}')

    def test_calendar_uses_one_common_sidebar_on_normal_and_scoped_routes(self):
        tasks = [self.task(title=f'Wspólny panel {index}') for index in range(23)]
        self.task(title='Prywatne zadanie', visibility='private', private_owner=self.owner)
        self.task(title='Zakończone zadanie', status='closed')
        other_space = make_space(user=self.owner, workplace=self.other, name='Inny Workspace')
        self.task(title='Zadanie innego Workspace', space=other_space)
        for url in (reverse('planner:index'), self.url('calendar', '')):
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-today-sidebar', count=1)
                self.assertContains(response, 'class="today-sidebar__calendar"', count=1)
                self.assertContains(response, 'class="today-sidebar__task"', count=20)
                self.assertContains(response, 'Plan na dziś')
                self.assertNotContains(response, 'Plan dnia')
                self.assertNotContains(response, 'id="calendar-agenda"')
                self.assertNotContains(response, 'Prywatne zadanie')
                self.assertNotContains(response, 'Zakończone zadanie')
                self.assertNotContains(response, 'Zadanie innego Workspace')
                script = re.search(r'<script[^>]+id="ancore-global-panels-data"[^>]*>(.*?)</script>',
                                   response.content.decode(), re.S)
                self.assertIsNotNone(script)
                sidebar = json.loads(script.group(1))['shell']['sidebar_url']
                self.assertEqual(sidebar, self.url())
                payload = self.api(sidebar).json()
                self.assertEqual([item['id'] for item in payload['entries']], [f'tasks:{task.pk}' for task in tasks[:20]])
                self.assertEqual(payload['pagination']['count'], 23)
                payload = self.api(payload['pagination']['next_url']).json()
                self.assertEqual([item['id'] for item in payload['entries']], [f'tasks:{task.pk}' for task in tasks])
                response = self.client.get(url, {'date': '2027-01-02', 'sidebar_task_limit': 23}, follow=True)
                self.assertContains(response, 'data-today-sidebar', count=1)
                self.assertContains(response, 'class="today-sidebar__task"', count=23)
                self.assertContains(response, '"sidebar_url": "' + self.url() + '?sidebar_task_limit=23"')

    def test_task_sidebar_has_no_default_panel_or_data_url(self):
        task = self.task()
        for url in (reverse('spaces:task_detail', kwargs={'space_pk': self.space.slug, 'key': task.work_item.key}),
                    self.url('space', f'{self.space.slug}/tasks/{task.work_item.key}/')):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'data-today-sidebar')
                self.assertContains(response, '"sidebar_url": ""')

    def test_drive_directory_replaces_today_sidebar_but_office_keeps_it(self):
        for url in ('/documents/', self.url('documents', ''), self.url('documents', '') + '?view=all'):
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertContains(response, 'data-documents-sidebar', count=1)
                self.assertNotContains(response, 'data-today-sidebar')
                self.assertContains(response, '"sidebar_url": ""')
        response = self.client.get(self.url('office', ''))
        self.assertContains(response, 'data-today-sidebar', count=1)
        self.assertNotContains(response, 'data-documents-sidebar')
        self.assertContains(response, '"sidebar_url": "' + self.url() + '"')

    def test_disabled_calendar_first_render(self):
        response = self.client.get(self.url('spaces', ''))
        self.assertContains(response, 'data-today-sidebar')
        self.assertContains(response, self.url())
        self.workspace.disabled_modules = ['calendar']
        self.workspace.save(update_fields=['disabled_modules'])
        response = self.client.get(self.url('spaces', ''))
        self.assertNotContains(response, 'data-today-sidebar')
        self.assertContains(response, '"sidebar_url": ""')
