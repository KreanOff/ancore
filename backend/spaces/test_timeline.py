from datetime import date, datetime, time
import json
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import SpaceMembership, SpaceTask, SpaceTaskMembership, WorkItem
from .testing import make_space


@override_settings(TIME_ZONE='Europe/Warsaw')
class TimelineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='timeline-owner', email='timeline-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='timeline-member', email='timeline-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Timeline')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Timeline',
                               visibility='private', private_owner=cls.owner)
        SpaceMembership.objects.create(space=cls.space, user=cls.member, role='member')
        cls.task = SpaceTask.objects.create(created_by=cls.owner, space=cls.space, title='Zaplanowane',
            due_at=datetime(2026, 10, 23, 16, 37, 12, 987654, tzinfo=ZoneInfo('Europe/Warsaw')))
        cls.item = cls.task.work_item
        cls.item.start_on = date(2026, 10, 20)
        cls.item.save(update_fields=['start_on'])
        cls.unscheduled = SpaceTask.objects.create(created_by=cls.owner, space=cls.space, title='Bez planu')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix='', scoped=True):
        tail = f'{self.space.slug}/{suffix}'
        return scoped_workplace_app_path(self.workspace, 'space', tail) if scoped else '/space/' + tail

    def data(self, item=None, **changes):
        item = item or self.item
        item.refresh_from_db()
        item.task.refresh_from_db()
        values = {'start_on': '2026-10-27', 'end_on': '2026-10-30',
                  'source_start_on': item.start_on.isoformat() if item.start_on else '',
                  'source_due_at': json.loads(json.dumps(item.task.due_at, cls=DjangoJSONEncoder)) or ''}
        return {**values, **changes}

    def post(self, data=None, *, item=None, scoped=True, api=False):
        item = item or self.item
        target = self.url(f'tasks/{item.key}/dates/', scoped)
        if api:
            target = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') + '?' + urlencode({'url': target})
        return self.client.post(target, data if data is not None else self.data(item))

    def page(self, scoped=True, **query):
        target = self.url('?' + urlencode({'view': 'timeline', **query}), scoped)
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        response = self.client.get(api, {'url': target})
        self.assertEqual(response.status_code, 200)
        return response.json()['data']

    def test_includes_unscheduled_dates_status_and_scoped_update_url(self):
        for scoped in (True, False):
            with self.subTest(scoped=scoped):
                payload = self.page(scoped)
                self.assertIsNone(payload['pagination'])
                self.assertEqual(len(payload['items']), 2)
                rows = {row['task_id']: row for row in payload['items']}
                self.assertEqual(rows[self.task.pk]['end_on'], '2026-10-23')
                self.assertEqual(rows[self.task.pk]['start_on'], '2026-10-20')
                self.assertEqual(rows[self.task.pk]['update_dates_url'], self.url(f'tasks/{self.item.key}/dates/'))
                self.assertEqual(rows[self.unscheduled.pk]['timeline']['start'], None)
                self.assertEqual(rows[self.unscheduled.pk]['end_on'], None)
                self.assertTrue(rows[self.unscheduled.pk]['editable'])
                self.assertTrue(payload['timeline']['today'])

    def test_filters_sort_and_empty_results_remain_available(self):
        self.assertEqual([row['title'] for row in self.page(sort='title_asc')['items']], ['Bez planu', 'Zaplanowane'])
        self.assertEqual([row['task_id'] for row in self.page(q='Bez planu')['items']], [self.unscheduled.pk])
        self.assertEqual(self.page(q='Nieistniejące')['items'], [])
        self.assertEqual(self.page(status='closed')['items'], [])
        self.assertIsNone(self.page(status='closed')['pagination'])

    def test_all_unscheduled_tasks_are_loaded_and_old_page_parameter_is_ignored(self):
        tasks = SpaceTask.objects.bulk_create([
            SpaceTask(created_by=self.owner, space=self.space, title=f'Bez dat {index:03}') for index in range(101)
        ])
        WorkItem.objects.bulk_create([
            WorkItem(task=task, space=self.space, key=f'{self.space.key}-{index}', number=index, rank=index * 100)
            for index, task in enumerate(tasks, start=3)
        ])
        first, second = self.page(), self.page(page=2)
        self.assertIsNone(first['pagination'])
        self.assertIsNone(second['pagination'])
        self.assertEqual((len(first['items']), len(second['items'])), (103, 103))
        self.assertEqual([row['id'] for row in first['items']], [row['id'] for row in second['items']])

    def test_move_preserves_local_clock_across_dst_and_records_actual_actor(self):
        original = (self.task.title, self.task.status, self.task.is_completed, self.task.completion_date,
                    self.item.rank, self.item.sprint_id, self.item.in_backlog)
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(self.item.start_on, date(2026, 10, 27))
        self.assertEqual(timezone.localtime(self.task.due_at).time(), time(16, 37, 12, 987654))
        self.assertEqual(self.task.due_at.utcoffset().total_seconds(), 0)  # Database UTC.
        self.assertEqual(timezone.localtime(self.task.due_at).utcoffset().total_seconds(), 3600)
        self.assertEqual((self.task.title, self.task.status, self.task.is_completed, self.task.completion_date,
                          self.item.rank, self.item.sprint_id, self.item.in_backlog), original)
        self.assertTrue(response.json()['changed'])
        self.assertEqual(response.json()['due_urgency'], self.task.due_urgency)
        activity = self.task.activities.order_by('-pk').first()
        self.assertEqual(activity.actor_id, self.member.pk)
        self.assertEqual(activity.metadata['fields'], ['planowane rozpoczęcie', 'termin wykonania'])

    def test_create_partial_dates_clear_dates_and_plain_scoped_api_routes(self):
        item = self.unscheduled.work_item
        for scoped, api, start, end in [(False, False, '2026-11-02', ''), (True, True, '', '2026-11-05'),
                                        (False, True, '2026-11-02', '2026-11-05'), (True, False, '', '')]:
            with self.subTest(scoped=scoped, api=api, start=start, end=end):
                response = self.post(self.data(item, start_on=start, end_on=end), item=item, scoped=scoped, api=api)
                self.assertEqual(response.status_code, 200)
                item.refresh_from_db()
                item.task.refresh_from_db()
                self.assertEqual(item.start_on.isoformat() if item.start_on else '', start)
                self.assertEqual(timezone.localtime(item.task.due_at).date().isoformat() if item.task.due_at else '', end)
                if end:
                    self.assertEqual(timezone.localtime(item.task.due_at).time(), time(23, 59))

    def test_noop_and_closed_task_keep_completion_and_history(self):
        self.task.status = 'closed'
        self.task.save(update_fields=['status'])
        finished = self.task.completion_date
        count = self.task.activities.count()
        response = self.post(self.data(start_on='2026-10-20', end_on='2026-10-23'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['changed'])
        self.assertEqual(self.task.activities.count(), count)
        self.assertEqual(self.post().status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'closed')
        self.assertEqual(self.task.completion_date, finished)

    def test_invalid_dates_snapshot_and_missing_fields_do_not_write(self):
        invalid = [{'start_on': '2026-02-30'}, {'end_on': '2026-02-29'}, {'start_on': '20261027'},
                   {'start_on': '2026-W44-2'}, {'end_on': '2026-10-26'}, {'source_start_on': 'junk'},
                   {'source_due_at': '2026-10-23'}, {'source_due_at': 'not-a-date'}]
        for changes in invalid:
            with self.subTest(changes=changes):
                response = self.post(self.data(**changes))
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.json()['message'])
        for field in self.data():
            data = self.data()
            del data[field]
            self.assertEqual(self.post(data).status_code, 400)
        self.item.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.item.start_on, date(2026, 10, 20))
        self.assertEqual(timezone.localtime(self.task.due_at).date(), date(2026, 10, 23))
        self.assertEqual(self.task.activities.count(), 1)

    def test_stale_dates_are_conflicts_and_do_not_overwrite(self):
        for field, stale in [('source_start_on', ''), ('source_due_at', ''), ('source_due_at', '2026-10-23T14:36:12Z')]:
            response = self.post(self.data(**{field: stale}))
            self.assertEqual(response.status_code, 409)
            self.assertTrue(response.json()['message'])
        self.item.refresh_from_db()
        self.assertEqual(self.item.start_on, date(2026, 10, 20))
        self.assertEqual(self.task.activities.count(), 1)

    def test_ignores_unrelated_fields_without_changing_their_values(self):
        response = self.post(self.data(title='Injected', status='closed', assignee=str(self.member.pk), rank='1', in_backlog='true'))
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual((self.task.title, self.task.status, self.task.assignee_id, self.item.rank, self.item.in_backlog),
                         ('Zaplanowane', 'new', None, 100, False))

    def test_observer_and_workspace_guest_cannot_write(self):
        grant = SpaceMembership.objects.get(space=self.space, user=self.member)
        grant.role = 'observer'
        grant.save(update_fields=['role'])
        self.assertEqual(self.post(api=True).status_code, 403)
        self.assertFalse(next(row for row in self.page()['items'] if row['id'] == self.item.pk)['editable'])
        grant.role = 'admin'
        grant.save(update_fields=['role'])
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).update(role='guest')
        self.assertEqual(self.post(api=True).status_code, 403)
        self.assertEqual(self.task.activities.count(), 1)

    def test_private_parent_and_other_workspace_stay_hidden(self):
        self.task.visibility, self.task.private_owner = 'private', self.owner
        self.task.save(update_fields=['visibility', 'private_owner'])
        child = SpaceTask.objects.create(created_by=self.owner, space=self.space, parent=self.task, title='Hidden child')
        SpaceTaskMembership.objects.create(task=child, user=self.member, role='admin')
        self.assertEqual(self.post(item=child.work_item, api=True).status_code, 404)
        self.assertEqual([row['task_id'] for row in self.page()['items']], [self.unscheduled.pk])
        other = create_workplace_for_user(self.owner, 'Other timeline')
        WorkplaceMembership.objects.create(workplace=other, user=self.member)
        api = scoped_workplace_app_path(other, 'api', 'v1/page/')
        target = self.url(f'tasks/{self.item.key}/dates/')
        response = self.client.post(api + '?' + urlencode({'url': target}), self.data())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.task.activities.count(), 1)

    def test_dst_nonexistent_clock_rejects_whole_edit(self):
        self.task.due_at = datetime(2026, 3, 28, 2, 30, tzinfo=ZoneInfo('Europe/Warsaw'))
        self.task.save(update_fields=['due_at'])
        response = self.post(self.data(start_on='2026-03-27', end_on='2026-03-29'))
        self.assertEqual(response.status_code, 400)
        self.item.refresh_from_db()
        self.assertEqual(self.item.start_on, date(2026, 10, 20))

    def test_latest_supported_date_does_not_overflow_page_range(self):
        WorkItem.objects.filter(space=self.space).update(start_on=date.max)
        SpaceTask.objects.filter(space=self.space).update(due_at=None)
        payload = self.page()
        self.assertEqual(payload['timeline']['start'], '9999-12-31')
        self.assertEqual(payload['timeline']['end'], '9999-12-31')

    def test_earliest_date_rejects_utc_overflow_before_any_write(self):
        self.task.due_at = datetime(2026, 10, 23, 0, 0, tzinfo=ZoneInfo('Europe/Warsaw'))
        self.task.save(update_fields=['due_at'])
        response = self.post(self.data(start_on='0001-01-01', end_on='0001-01-01'))
        self.assertEqual(response.status_code, 400)
        self.item.refresh_from_db()
        self.assertEqual(self.item.start_on, date(2026, 10, 20))

    def test_html_shows_unscheduled_task_with_assignee_and_edit_link(self):
        response = self.client.get(self.url('?view=timeline'))
        for text in ('Bez planu', 'Nie ustawiono', 'Wykonawca', self.unscheduled.work_item.key):
            self.assertContains(response, text)
        self.assertContains(response, f'tasks/{self.unscheduled.work_item.key}/edit/')
        self.assertNotContains(response, 'work-pagination')
        self.assertNotContains(response, 'work-timeline-footer')

    def test_endpoint_requires_post_and_csrf(self):
        target = self.url(f'tasks/{self.item.key}/dates/')
        self.assertEqual(self.client.get(target).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        self.assertEqual(client.post(target, self.data()).status_code, 403)
