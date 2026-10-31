import csv
import io
from datetime import date, datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import SpaceMembership, SpaceTask, SpaceTaskMembership, SpaceTaskWorkLog, Sprint, Team, WorkItem
from .reports import safe_csv_cell
from .testing import make_space


@override_settings(TIME_ZONE='Europe/Warsaw')
class SpaceReportsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='reports-owner', email='reports-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='reports-member', email='reports-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Raporty')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Raporty', template='scrum', visibility='private', private_owner=cls.owner)
        SpaceMembership.objects.create(space=cls.space, user=cls.member)
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Inny Workspace')
        WorkplaceMembership.objects.create(workplace=cls.other_workspace, user=cls.member)
        cls.other_space = make_space(user=cls.owner, workplace=cls.other_workspace, name='Inna przestrzeń')
        cls.sprint = Sprint.objects.create(space=cls.space, name='Sprint jeden', start_on=date(2026, 10, 20), end_on=date(2026, 11, 3), state='active')
        cls.foreign_sprint = Sprint.objects.create(space=cls.other_space, name='Prywatna nazwa sprintu', start_on=date(2026, 10, 20), end_on=date(2026, 11, 3))
        cls.team = Team.objects.create(workplace=cls.workspace, owner=cls.owner, name='Zespół raportów')
        cls.team.spaces.add(cls.space)

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()
        self.now = datetime(2026, 10, 30, 12, 0, tzinfo=ZoneInfo('Europe/Warsaw'))
        self.clock = patch('django.utils.timezone.now', return_value=self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def url(self, scoped=True, **query):
        base = scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/') if scoped else f'/space/{self.space.slug}/'
        return base + '?' + urlencode({'view': 'reports', **query})

    def page(self, scoped=True, **query):
        response = self.client.get(scoped_workplace_app_path(self.workspace, 'api', 'v1/page/'), {'url': self.url(scoped, **query)})
        self.assertEqual(response.status_code, 200, response.content[:500])
        return response.json()['data']

    def report(self, **query):
        return self.page(**query)['reports']

    def task(self, title='Zadanie', created=None, **values):
        planning = {key: values.pop(key) for key in ('points', 'sprint', 'team', 'work_type') if key in values}
        task = SpaceTask.objects.create(space=values.pop('space', self.space), created_by=self.owner, title=title, **values)
        if created:
            SpaceTask.objects.filter(pk=task.pk).update(created_at=created)
            task.refresh_from_db()
        if planning:
            WorkItem.objects.filter(pk=task.work_item.pk).update(**planning)
        return task

    def export(self, **query):
        response = self.client.get(self.url(**query, report_export='csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        body = b''.join(response.streaming_content).decode('utf-8-sig')
        return response, list(csv.reader(io.StringIO(body), delimiter=';'))

    def test_snapshot_and_activity_are_separate_and_uncapped(self):
        tasks = SpaceTask.objects.bulk_create([SpaceTask(space=self.space, created_by=self.owner, title=f'Wiersz {i}') for i in range(123)])
        WorkItem.objects.bulk_create([WorkItem(task=task, space=self.space, key=f'{self.space.key}-{index}', number=index, points=2) for index, task in enumerate(tasks, start=1)])
        type(self.space).objects.filter(pk=self.space.pk).update(next_number=124)
        SpaceTask.objects.filter(pk__in=[task.pk for task in tasks]).update(created_at=self.now - timedelta(days=100))
        completed = self.task(status='closed', points=5, sprint=self.sprint)
        overdue = self.task(due_at=self.now - timedelta(days=2), assignee=self.member, points=0, priority='urgent')
        report = self.report(report_period='7', page=99)
        self.assertEqual(report['snapshot'], {'total':125, 'completed':1, 'overdue':1, 'due_soon':0, 'unassigned':123,
                         'points':251, 'completed_points':5, 'unestimated':0, 'open':124, 'completion_percent':0.8})
        self.assertEqual((report['activity']['created'], report['activity']['completed']), (2, 1))
        self.assertEqual(sum(row['count'] for row in report['statuses']), 125)
        self.assertEqual(sum(row['total'] for row in report['workload']), 125)
        self.assertEqual(report['overdue']['items'][0]['key'], overdue.work_item.key)
        self.assertEqual(self.page()['items'], [])
        self.assertIsNone(self.page()['pagination'])
        _, rows = self.export(report_period='7', page=2)
        self.assertEqual(len(rows), 126)
        self.assertIn(completed.work_item.key, {row[0] for row in rows[1:]})

    def test_acl_excludes_private_parent_children_and_other_workspace_everywhere(self):
        public = self.task('Widoczny', status='closed', sprint=self.sprint, points=3)
        hidden = self.task('Sekretny rodzic', visibility='private', private_owner=self.owner, assignee=self.member, sprint=self.sprint, points=50)
        child = self.task('Dziecko sekretnego rodzica', parent=hidden, sprint=self.sprint, points=60)
        private_child = self.task('Sekretne podzadanie', parent=public, visibility='private', private_owner=self.owner, sprint=self.sprint)
        self.task('Inny Workspace', space=self.other_space)
        for task in (public, hidden, child, private_child):
            SpaceTaskWorkLog.objects.create(task=task, author=self.owner, started_at=self.now-timedelta(hours=2), ended_at=self.now-timedelta(hours=1), description='Praca')
        first = self.report()
        self.assertEqual(first['snapshot']['total'], 1)
        self.assertEqual(first['activity']['logged_minutes'], 60)
        self.assertEqual(first['sprints'][0]['total'], 1)
        self.assertEqual(first['sprints'][0]['points'], 3)
        _, rows = self.export()
        self.assertEqual([row[1] for row in rows[1:]], ['Widoczny'])
        SpaceTaskMembership.objects.create(task=hidden, user=self.member)
        self.assertEqual(self.report()['snapshot']['total'], 3)
        SpaceTaskMembership.objects.filter(task=hidden, user=self.member).delete()
        self.assertEqual(self.report()['snapshot']['total'], 1)

    def test_combined_filters_and_csv_have_same_scope(self):
        selected = self.task('Wybrane zadanie', priority='high', assignee=self.member, sprint=self.sprint, team=self.team, points=8)
        self.task('Inny priorytet', priority='low', assignee=self.member, sprint=self.sprint, team=self.team)
        self.task('Bez sprintu', priority='high', assignee=self.member, team=self.team)
        self.task('Bez wykonawcy', priority='high', sprint=self.sprint, team=self.team)
        filters = {'report_sprint':str(self.sprint.pk), 'assignee':'me', 'priority':'high', 'team':str(self.team.pk), 'q':'Wybrane', 'work_type':'task', 'status':selected.work_item.status}
        report = self.report(**filters)
        self.assertEqual(report['snapshot']['total'], 1)
        _, rows = self.export(**filters)
        self.assertEqual([row[0] for row in rows[1:]], [selected.work_item.key])
        for section in ('statuses', 'priorities', 'workload', 'sprints'):
            parsed = parse_qs(urlsplit(report[section][0]['url']).query)
            self.assertEqual(parsed['view'], ['reports'])
            self.assertEqual(parsed['report_sprint'], [str(self.sprint.pk)])
        self.assertEqual(self.report(report_sprint='none')['snapshot']['total'], 1)
        self.assertEqual(self.report(assignee='unassigned')['snapshot']['total'], 1)

    def test_invalid_foreign_sprint_fails_closed_and_period_defaults(self):
        self.task(sprint=self.sprint)
        for value in (str(self.foreign_sprint.pk), '99999999999999999999999999', 'bad', '-1'):
            with self.subTest(value=value):
                report = self.report(report_sprint=value, report_period='invalid')
                self.assertEqual(report['snapshot']['total'], 0)
                self.assertEqual(report['period']['days'], 30)
                self.assertTrue(report['filter_error'])
                self.assertNotIn(self.foreign_sprint.name, str(report))
                self.assertEqual(len(self.export(report_sprint=value)[1]), 1)

    def test_local_midnight_and_reopened_completion_semantics(self):
        start = datetime(2026, 10, 24, tzinfo=ZoneInfo('Europe/Warsaw'))
        self.task('Tuż przed', created=start-timedelta(microseconds=1))
        self.task('Dokładnie od', created=start)
        done = self.task('Zakończone', created=start-timedelta(days=2), status='closed')
        SpaceTask.objects.filter(pk=done.pk).update(completion_date=start)
        self.task('Przyszłość', created=self.now+timedelta(hours=1))
        report = self.report(report_period='7')
        self.assertEqual(report['period']['start_on'], '2026-10-24')
        self.assertEqual(report['activity']['created'], 1)
        self.assertEqual(report['activity']['completed'], 1)
        self.assertEqual(report['trend'][0]['created'], 1)
        self.assertEqual(report['trend'][0]['completed'], 1)
        done.status = 'reopened'
        done.save(update_fields=['status'])
        self.assertEqual(self.report(report_period='7')['activity']['completed'], 0)
        done.status = 'closed'
        done.save(update_fields=['status'])
        self.assertEqual(self.report(report_period='7')['trend'][-1]['completed'], 1)
        self.assertEqual(self.report(report_period='90')['period']['days'], 90)

    def test_time_entries_are_clipped_and_dst_uses_elapsed_time(self):
        task = self.task(assignee=self.member)
        zone = ZoneInfo('Europe/Warsaw')
        intervals = [
            (datetime(2026,10,23,23,30,tzinfo=zone), datetime(2026,10,24,1,30,tzinfo=zone)),
            (datetime(2026,10,25,1,30,tzinfo=zone), datetime(2026,10,25,3,30,tzinfo=zone)),
            (self.now-timedelta(hours=1), self.now+timedelta(hours=2)),
            (self.now+timedelta(hours=3), self.now+timedelta(hours=4)),
        ]
        for start, end in intervals:
            SpaceTaskWorkLog.objects.create(task=task, author=self.owner, started_at=start, ended_at=end, description='Praca')
        report = self.report(report_period='7')
        self.assertEqual(report['activity']['logged_minutes'], 330)  # 90 + 180 across DST + 60 to now.
        self.assertEqual(report['trend'][0]['logged_minutes'], 90)
        self.assertEqual(report['trend'][1]['logged_minutes'], 180)
        self.assertEqual(report['workload'][0]['logged_minutes'], 330)
        self.assertEqual(report['workload'][0]['id'], self.member.pk)

    def test_overdue_has_full_total_top_ten_links_and_closed_excluded(self):
        for index in range(12):
            self.task(f'Zaległe {index}', due_at=self.now-timedelta(days=index+1))
        self.task('Zakończone zaległe', due_at=self.now-timedelta(days=100), status='closed')
        report = self.report()
        self.assertEqual(report['overdue']['total'], 12)
        self.assertEqual(len(report['overdue']['items']), 10)
        self.assertEqual(report['overdue']['items'][0]['days_overdue'], 12)
        self.assertIn('/tasks/', report['overdue']['items'][0]['url'])
        self.assertTrue(report['overdue']['items'][0]['url'].startswith(scoped_workplace_app_path(self.workspace, 'space')))

    def test_sprint_current_points_zero_estimates_and_filtered_scope(self):
        self.task(status='closed', sprint=self.sprint, points=5)
        self.task(sprint=self.sprint, points=0)
        self.task(sprint=self.sprint)
        self.task(points=3)
        report = self.report(report_sprint=str(self.sprint.pk))
        self.assertEqual(report['snapshot']['unestimated'], 1)
        self.assertEqual((report['sprints'][0]['total'], report['sprints'][0]['completed'], report['sprints'][0]['points'], report['sprints'][0]['completed_points']), (3, 1, 5, 5))
        self.assertEqual(report['sprints'][0]['completion_percent'], 33.3)
        self.assertEqual(self.report(report_sprint='none')['sprints'], [])

    def test_formula_text_is_neutralized_and_export_is_private(self):
        self.task('=HYPERLINK("https://example.test")')
        response, rows = self.export()
        self.assertEqual(rows[1][1], '\'=HYPERLINK("https://example.test")')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertIn('attachment', response['Content-Disposition'])
        for value in ('=1+1', '+SUM(A1)', '-1', '@SUM(A1)', '  =1', '\tfoo', '\rfoo', '\nfoo'):
            self.assertTrue(safe_csv_cell(value).startswith("'"))
        self.assertEqual(safe_csv_cell('Zwykły tytuł'), 'Zwykły tytuł')

    def test_empty_and_plain_scoped_routes_have_same_report_and_fallback(self):
        plain, scoped = self.page(False), self.page(True)
        self.assertEqual(plain['reports']['snapshot'], scoped['reports']['snapshot'])
        report = plain['reports']
        self.assertEqual(report['snapshot']['total'], 0)
        self.assertEqual(report['snapshot']['completion_percent'], 0)
        self.assertEqual(report['activity']['logged_minutes'], 0)
        self.assertEqual(len(report['trend']), 30)
        self.assertEqual(report['workload'], [])
        self.assertEqual(report['overdue']['items'], [])
        response = self.client.get(self.url())
        self.assertContains(response, 'Raporty przestrzeni')
        self.assertContains(response, 'Dane dzienne')

    def test_revoked_space_and_workspace_access_blocks_report_and_csv(self):
        self.task()
        SpaceMembership.objects.filter(space=self.space, user=self.member).delete()
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.assertEqual(self.client.get(self.url(report_export='csv')).status_code, 404)
        SpaceMembership.objects.create(space=self.space, user=self.member)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).update(is_active=False)
        self.assertNotEqual(self.client.get(self.url()).status_code, 200)
        self.assertNotEqual(self.client.get(self.url(report_export='csv')).status_code, 200)
