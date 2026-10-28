from .testing import make_space
from datetime import timedelta
from html import unescape
from math import hypot, sqrt
import re
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from .models import SpaceDashboardLayout, SpaceTask, SpaceTaskActivity, SpaceTaskMembership, Space, SpaceMembership, Team
from .summary import status_arc_path
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class StatusArcGeometryTests(SimpleTestCase):
    @staticmethod
    def endpoints(path):
        commands = path.split(' A ')
        start = tuple(float(value) for value in commands[0][2:].split())
        end = tuple(float(value) for value in commands[-1].split()[-2:])
        return start, end

    def test_zero_share_has_no_path(self):
        self.assertEqual(status_arc_path(0, 0), '')
        self.assertEqual(status_arc_path(75, 0), '')

    def test_final_quarter_ends_exactly_at_the_first_segment_seam(self):
        self.assertEqual(status_arc_path(75, 25), 'M 50 10 A 40 40 0 0 1 90 50')
        self.assertEqual(self.endpoints(status_arc_path(75, 25))[1], self.endpoints(status_arc_path(0, 25))[0])
        self.assertNotIn('Z', status_arc_path(75, 25))

    def test_majority_share_uses_the_large_clockwise_arc(self):
        self.assertEqual(status_arc_path(0, 75), 'M 90 50 A 40 40 0 1 1 50 10')
        self.assertEqual(status_arc_path(25, 50), 'M 50 90 A 40 40 0 0 1 50 10')

    def test_full_share_is_two_nonempty_semicircles(self):
        self.assertEqual(status_arc_path(0, 100), 'M 90 50 A 40 40 0 0 1 10 50 A 40 40 0 0 1 90 50')
        self.assertEqual(status_arc_path(25, 100), 'M 50 90 A 40 40 0 0 1 50 10 A 40 40 0 0 1 50 90')
        start, end = self.endpoints(status_arc_path(0, 100))
        self.assertEqual(start, end)

    def test_fractional_share_keeps_points_on_the_circle(self):
        start, end = self.endpoints(status_arc_path(12.5, 12.5))
        self.assertAlmostEqual(start[0], 50 + 20 * sqrt(2), places=7)
        self.assertAlmostEqual(start[1], 50 + 20 * sqrt(2), places=7)
        self.assertEqual(end, (50, 90))
        self.assertAlmostEqual(hypot(start[0] - 50, start[1] - 50), 40, places=7)

    def test_fractional_segments_share_identical_boundaries_without_wrap_dashes(self):
        offset = 0
        paths = []
        for count in (1, 3, 2, 1):
            percent = count * 100 / 7
            paths.append(status_arc_path(offset, percent))
            offset += percent
        for previous, following in zip(paths, paths[1:]):
            self.assertEqual(self.endpoints(previous)[1], self.endpoints(following)[0])
        self.assertEqual(self.endpoints(paths[-1])[1], self.endpoints(paths[0])[0])
        self.assertTrue(all(path.count(' A ') == 1 for path in paths))


class SpaceSummaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username='summary-owner', email='summary-owner@example.test', first_name='Anna')
        cls.member = User.objects.create_user(username='summary-member', email='summary-member@example.test', first_name='Jan')
        cls.other = User.objects.create_user(username='summary-other', email='summary-other@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Podsumowanie')
        cls.second = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy Workspace')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member, role='member')
        cls.project = make_space(user=cls.owner, workplace=cls.workspace, name='Produkt', visibility='private', private_owner=cls.owner)
        SpaceMembership.objects.create(space=cls.project, user=cls.member, role='observer')
        cls.space = cls.project
        config = cls.space.configuration
        config.settings['statuses'].insert(2, {'key': 'review', 'label': 'Weryfikacja', 'category': 'in_progress', 'transitions': ['closed']})
        config.save()
        cls.section = cls.project

    def setUp(self):
        self.now = timezone.now()
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def task(self, **kwargs):
        task = SpaceTask.objects.create(created_by=self.owner, space=self.section, title='Zadanie', **kwargs)
        SpaceTask.objects.filter(pk=task.pk).update(created_at=self.now - timedelta(days=30))
        task.activities.update(created_at=self.now - timedelta(days=30))
        return task

    def url(self, query=''):
        return scoped_workplace_app_path(self.workspace, 'spaces', f'{self.space.pk}/') + query

    def response(self, url=None):
        with patch('spaces.views.timezone.now', return_value=self.now):
            return self.client.get(url or self.url(), follow=True)

    def overview_url(self, filters=None, scoped=True):
        base = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/') if scoped else f'/space/{self.space.slug}/'
        return base + ('?' + urlencode(filters) if filters else '')

    def page_data(self, filters=None, scoped=True):
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
        with patch('spaces.views.timezone.now', return_value=self.now):
            response = self.client.get(api, {'url': self.overview_url(filters, scoped)})
        self.assertEqual(response.status_code, 200)
        return response.json()['data']

    def filter_fixture(self):
        first_team = Team.objects.create(owner=self.owner, workplace=self.workspace, name='Pierwszy zespół')
        second_team = Team.objects.create(owner=self.owner, workplace=self.workspace, name='Drugi zespół')
        first_team.spaces.add(self.space)
        second_team.spaces.add(self.space)
        selected = self.task(status='in_progress', priority='urgent', assignee=self.member, due_at=self.now + timedelta(days=1))
        other = self.task(status='closed', priority='low')
        hidden = self.task(status='in_progress', priority='urgent', assignee=self.member,
                           due_at=self.now + timedelta(days=1), visibility='private', private_owner=self.owner)
        self.task(assignee=self.other, visibility='private', private_owner=self.owner)
        for task in (selected, hidden):
            SpaceTask.objects.filter(pk=task.pk).update(title='Zadanie wybrane', created_at=self.now - timedelta(days=1))
            type(task.work_item).objects.filter(pk=task.work_item.pk).update(work_type='bug', status='review', team=first_team)
            activity = SpaceTaskActivity.objects.create(task=task, actor=self.member, action='updated')
            SpaceTaskActivity.objects.filter(pk=activity.pk).update(created_at=self.now - timedelta(hours=1))
        SpaceTask.objects.filter(pk=other.pk).update(title='Zadanie pozostałe', completion_date=self.now - timedelta(days=1))
        type(other.work_item).objects.filter(pk=other.work_item.pk).update(team=second_team)
        return selected, first_team, second_team

    def test_common_overview_filters_scope_counters_charts_and_activity(self):
        selected, team, _ = self.filter_fixture()
        filters = [
            {'work_type': 'bug'}, {'assignee': 'me'}, {'assignee': str(self.member.pk)},
            {'status': 'review'}, {'priority': 'urgent'}, {'team': str(team.pk)}, {'q': 'wybrane'},
            {'work_type': 'bug', 'assignee': 'me', 'status': 'review', 'priority': 'urgent', 'team': str(team.pk)},
        ]
        for scoped in (False, True):
            for values in filters:
                with self.subTest(scoped=scoped, filters=values):
                    summary = self.response(self.overview_url(values, scoped)).context['summary']
                    self.assertEqual((summary['total'], summary['open_total'], summary['status_total']), (1, 1, 1))
                    self.assertEqual({row['key']: row['count'] for row in summary['metrics']},
                                     {'completed': 0, 'updated': 1, 'created': 1, 'due': 1})
                    self.assertEqual({row['key']: row['count'] for row in summary['statuses']}['review'], 1)
                    self.assertEqual({row['key']: row['count'] for row in summary['types']}['bug'], 1)
                    self.assertEqual({row['key']: row['count'] for row in summary['priorities']}['urgent'], 1)
                    self.assertEqual([(row['label'], row['count']) for row in summary['workload']], [('Jan', 1)])
                    self.assertEqual({row['key'] for row in summary['activities']}, {selected.work_item.key})
            unassigned = self.response(self.overview_url({'assignee': 'unassigned'}, scoped)).context['summary']
            self.assertEqual((unassigned['total'], unassigned['open_total']), (1, 0))
            self.assertEqual({row['key']: row['count'] for row in unassigned['metrics']}['completed'], 1)

    def test_overview_filter_menu_matches_task_list_with_visible_options(self):
        _, first_team, second_team = self.filter_fixture()
        foreign_team = Team.objects.create(owner=self.owner, workplace=self.second, name='Inny Workspace')
        for scoped in (False, True):
            for filters in ({}, {'work_type': 'bug', 'assignee': 'me', 'status': 'review', 'priority': 'urgent', 'team': str(first_team.pk)}):
                with self.subTest(scoped=scoped, filters=filters):
                    overview = self.page_data(filters, scoped)
                    task_list = self.page_data({**filters, 'view': 'list'}, scoped)
                    self.assertEqual(overview['filter_options'], task_list['filter_options'])
                    self.assertEqual(overview['filters'], task_list['filters'])
                    options = overview['filter_options']
                    self.assertIn(['bug', 'Błąd'], options['work_type'])
                    self.assertIn([str(self.member.pk), 'Jan'], options['assignee'])
                    self.assertNotIn(str(self.other.pk), {value for value, _ in options['assignee']})
                    self.assertIn(['review', 'Weryfikacja'], options['status'])
                    self.assertEqual(len(options['priority']), len(SpaceTask.PRIORITY_CHOICES) + 1)
                    self.assertEqual({value for value, _ in options['team']}, {'', str(first_team.pk), str(second_team.pk)})
                    self.assertNotIn(str(foreign_team.pk), {value for value, _ in options['team']})
                    html = self.response(self.overview_url(filters, scoped))
                    self.assertContains(html, '<span>Filtrowanie</span>')
                    self.assertContains(html, 'name="work_type"')
                    self.assertContains(html, 'name="assignee"')
                    self.assertContains(html, 'name="status"')
                    self.assertContains(html, 'name="priority"')
                    self.assertContains(html, 'name="team"')
                    self.assertNotContains(html, 'tasks-project-sort-builder')
                    self.assertEqual(html.context['item_filter_count'], len(filters))

    def test_filtered_drilldowns_and_clear_keep_other_filters_and_access_scope(self):
        selected, team, _ = self.filter_fixture()
        filters = {'view': 'overview', 'q': 'Zadanie', 'work_type': 'bug', 'assignee': 'me',
                   'status': 'review', 'priority': 'urgent', 'team': str(team.pk), 'summary': 'due', 'page': '2'}
        for scoped in (False, True):
            response = self.response(self.overview_url(filters, scoped))
            summary = response.context['summary']
            links = [*summary['metrics'], *[row for group in ('statuses', 'priorities', 'types', 'workload')
                                          for row in summary[group] if row['count']]]
            for row in links:
                with self.subTest(scoped=scoped, drilldown=row['url']):
                    result = self.response(row['url'])
                    self.assertEqual(result.status_code, 200)
                    self.assertEqual(result.context['page'].paginator.count, row['count'])
                    self.assertTrue(all(item.task_id == selected.pk for item in result.context['page']))
                    params = parse_qs(urlsplit(row['url']).query)
                    for key in ('q', 'work_type', 'team', 'status', 'priority'):
                        self.assertEqual(params[key], [filters[key]])
                    self.assertIn(params['assignee'][0], ('me', str(self.member.pk)))
                    self.assertNotIn('page', params)
            clear = re.search(r'class="tasks-project-query-panel__clear" href="([^"]+)">Wyczyść', response.content.decode())
            self.assertIsNotNone(clear)
            clear_url = urljoin(self.overview_url(filters, scoped), unescape(clear.group(1)))
            self.assertEqual(parse_qs(urlsplit(clear_url).query), {'view': ['overview'], 'q': ['Zadanie']})
            cleared = self.response(clear_url)
            self.assertEqual(cleared.context['summary']['total'], 2)
            self.assertEqual(cleared.context['item_filter_count'], 0)

    def test_empty_filter_result_and_clearing_leave_personal_layout_unchanged(self):
        self.filter_fixture()
        widgets = [{'id': 'statuses', 'x': 4, 'y': 7, 'w': 8, 'h': 6}]
        layout = SpaceDashboardLayout.objects.create(space=self.space, user=self.member, widgets=widgets, revision=7)
        for filters, total in (({'status': 'review', 'assignee': 'unassigned'}, 0), ({'team': '9999999'}, 0), ({}, 2)):
            data = self.page_data(filters)
            self.assertEqual(data['summary']['total'], total)
            self.assertEqual(data['summary']['dashboard']['widgets'], widgets)
            self.assertEqual(data['summary']['dashboard']['revision'], 7)
            self.assertTrue(data['filter_options']['work_type'])
        layout.refresh_from_db()
        self.assertEqual((layout.widgets, layout.revision), (widgets, 7))

    def test_recent_counters_use_dates_and_count_each_updated_task_once(self):
        created = self.task()
        SpaceTask.objects.filter(pk=created.pk).update(created_at=self.now - timedelta(days=1))
        closed = self.task(status='closed')
        SpaceTask.objects.filter(pk=closed.pk).update(completion_date=self.now - timedelta(days=2))
        old = self.task(status='closed')
        SpaceTask.objects.filter(pk=old.pk).update(completion_date=self.now - timedelta(days=20))
        updated = self.task()
        for action in ('updated', 'commented', 'status_changed'):
            activity = SpaceTaskActivity.objects.create(task=updated, actor=self.member, action=action)
            SpaceTaskActivity.objects.filter(pk=activity.pk).update(created_at=self.now - timedelta(days=1))
        self.task(due_at=self.now + timedelta(days=1))
        self.task(due_at=self.now - timedelta(seconds=1))
        self.task(due_at=self.now + timedelta(days=8))
        self.task(status='closed', due_at=self.now + timedelta(days=1))
        metrics = {row['key']: row['count'] for row in self.response().context['summary']['metrics']}
        self.assertEqual(metrics, {'completed': 1, 'updated': 1, 'created': 1, 'due': 1})

    def test_time_boundaries_and_reopened_tasks(self):
        reopened = self.task(status='reopened')
        SpaceTask.objects.filter(pk=reopened.pk).update(completion_date=self.now - timedelta(days=1))
        boundary = self.task(status='closed')
        SpaceTask.objects.filter(pk=boundary.pk).update(completion_date=self.now - timedelta(days=7), created_at=self.now - timedelta(days=7))
        for due in (self.now, self.now + timedelta(days=7), self.now + timedelta(days=7, seconds=1)):
            self.task(due_at=due)
        future = self.task(status='closed')
        SpaceTask.objects.filter(pk=future.pk).update(completion_date=self.now + timedelta(days=1), created_at=self.now + timedelta(days=1))
        metrics = {row['key']: row['count'] for row in self.response().context['summary']['metrics']}
        self.assertEqual(metrics, {'completed': 1, 'updated': 0, 'created': 1, 'due': 2})

    def test_statuses_keep_custom_names_and_omit_old_closed_tasks(self):
        self.task(status='in_progress')
        review = self.task(status='in_progress')
        type(review.work_item).objects.filter(task=review).update(status='review')
        recent = self.task(status='closed')
        SpaceTask.objects.filter(pk=recent.pk).update(completion_date=self.now - timedelta(days=14))
        old = self.task(status='closed')
        SpaceTask.objects.filter(pk=old.pk).update(completion_date=self.now - timedelta(days=14, seconds=1))
        summary = self.response().context['summary']
        counts = {row['key']: row['count'] for row in summary['statuses']}
        self.assertEqual(summary['status_total'], 3)
        self.assertEqual(counts['in_progress'], 1)
        self.assertEqual(counts['review'], 1)
        self.assertEqual(counts['closed'], 1)
        self.assertAlmostEqual(sum(float(row['arc']) for row in summary['statuses']), 100, places=3)

    def test_status_paths_render_exact_filtered_arcs_and_keep_legacy_fields(self):
        for status in ('new', 'in_progress', 'reopened'):
            self.task(status=status)
        response = self.response()
        statuses = response.context['summary']['statuses']
        paths = [row['path'] for row in statuses if row['count']]
        self.assertEqual(len(paths), 3)
        self.assertTrue(all(row['path'] == '' for row in statuses if not row['count']))
        for previous, following in zip(paths, paths[1:]):
            self.assertEqual(StatusArcGeometryTests.endpoints(previous)[1], StatusArcGeometryTests.endpoints(following)[0])
        self.assertEqual(StatusArcGeometryTests.endpoints(paths[-1])[1], (90, 50))
        for row in statuses:
            self.assertTrue({'arc', 'gap', 'offset', 'path'} <= row.keys())
            if row['count']:
                self.assertContains(response, f'd="{row["path"]}"')
        self.assertNotContains(response, 'stroke-dasharray=')
        filtered = self.response(self.overview_url({'status': 'new'})).context['summary']['statuses']
        full = next(row['path'] for row in filtered if row['count'])
        self.assertEqual(full.count(' A '), 2)

    def test_priority_type_and_workload_totals_include_all_pages_and_subtasks(self):
        parent = self.task(priority='high', assignee=self.member)
        self.task(parent=parent, priority='urgent', assignee=self.member)
        for _ in range(103):
            self.task(priority='none')
        self.task(status='closed', priority='urgent', assignee=self.owner)
        # Even on a reused connection with stale planner statistics, this
        # small catalog must not turn a grouped ACL query into a minute of work.
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '2s'")
        summary = self.response(self.url('?page=2')).context['summary']
        self.assertEqual(summary['total'], 106)
        self.assertEqual(summary['open_total'], 105)
        self.assertEqual(sum(row['count'] for row in summary['types']), 106)
        self.assertEqual({row['key']: row['count'] for row in summary['priorities']}['urgent'], 1)
        self.assertEqual({row['label']: row['count'] for row in summary['workload']}, {'Nieprzypisane': 103, 'Jan': 2})
        self.assertNotIn('Anna', [row['label'] for row in summary['workload']])

    def test_priority_chart_uses_a_shared_zero_based_scale(self):
        empty = self.response().context['summary']
        self.assertEqual(empty['priority_axis'], {'max': 1, 'middle': 0.5})
        self.assertTrue(all(float(row['height']) == 0 for row in empty['priorities']))
        self.task(priority='low')
        single = self.response().context['summary']
        self.assertEqual(single['priority_axis'], {'max': 1, 'middle': 0.5})
        for _ in range(4):
            self.task(priority='medium')
        self.task(priority='urgent', status='closed')
        summary = self.response().context['summary']
        self.assertEqual(summary['priority_axis'], {'max': 4, 'middle': 2})
        heights = {row['key']: float(row['height']) for row in summary['priorities']}
        self.assertEqual(heights, {'urgent': 0, 'high': 0, 'medium': 100, 'low': 25, 'none': 0})
        for _ in range(5):
            self.task(priority='medium')
        scaled = self.response().context['summary']
        self.assertEqual(scaled['priority_axis'], {'max': 10, 'middle': 5})
        self.assertEqual(float(next(row['height'] for row in scaled['priorities'] if row['key'] == 'medium')), 90)

    def test_summary_and_activity_respect_task_section_parent_and_workspace_access(self):
        visible = self.task()
        hidden = self.task(visibility='private', private_owner=self.owner, assignee=self.member)
        self.task(parent=hidden)
        private_section = make_space(user=self.owner, workplace=self.workspace, name='Poufna przestrzeń', visibility='private', private_owner=self.owner)
        SpaceTask.objects.create(created_by=self.owner, space=private_section, title='Poufne zadanie')
        for owner, workspace in ((self.owner, self.second), (self.other, self.foreign)):
            project = make_space(user=owner, workplace=workspace, name='Inny zakres')
            section = project
            SpaceTask.objects.create(created_by=owner, space=section, title='Obce zadanie', assignee=self.member)
        activity = SpaceTaskActivity.objects.create(task=visible, actor=self.member, action='updated')
        SpaceTaskActivity.objects.filter(pk=activity.pk).update(created_at=self.now - timedelta(seconds=1))
        SpaceTaskActivity.objects.create(task=hidden, actor=self.owner, action='updated')
        response = self.response()
        summary = response.context['summary']
        self.assertEqual(summary['total'], 1)
        self.assertEqual({row['label']: row['count'] for row in summary['workload']}, {'Nieprzypisane': 1})
        self.assertEqual([row['key'] for row in summary['activities']], [visible.work_item.key, visible.work_item.key])
        self.assertEqual(summary['activities'][0]['actor'], 'Jan')
        self.assertIn(f'/tasks/{visible.work_item.key}/', summary['activities'][0]['url'])
        SpaceTaskMembership.objects.create(task=hidden, user=self.member, role='observer')
        shared = self.response().context['summary']
        self.assertEqual(shared['total'], 3)
        self.assertEqual({row['label']: row['count'] for row in shared['workload']}, {'Nieprzypisane': 2, 'Jan': 1})
        SpaceTaskMembership.objects.filter(task=hidden, user=self.member).delete()
        self.assertEqual(self.response().context['summary']['total'], 1)
        SpaceMembership.objects.filter(space=self.project, user=self.member).delete()
        self.assertEqual(self.response().status_code, 404)

    def test_drill_downs_match_counts_and_preserve_filters(self):
        task = self.task(priority='urgent', assignee=self.member, due_at=self.now + timedelta(days=1))
        SpaceTask.objects.filter(pk=task.pk).update(created_at=self.now - timedelta(days=1))
        summary = self.response().context['summary']
        links = [*summary['metrics'], *summary['statuses'], *summary['priorities'], *summary['types'], *summary['workload']]
        for row in links:
            with self.subTest(url=row['url']):
                response = self.response(row['url'])
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['page'].paginator.count, row['count'])
        filtered = self.response(self.url('?q=Zadanie&assignee=me')).context['summary']
        self.assertIn('q=Zadanie', filtered['priorities'][0]['url'])
        self.assertIn('assignee=me', filtered['priorities'][0]['url'])
        response = self.response(summary['metrics'][3]['url'] + '&q=Zadanie&work_type=task')
        self.assertContains(response, 'name="summary" value="due"')
        self.assertContains(response, 'Usuń filtr')

    def test_empty_summary_and_invalid_filters_render_safely(self):
        for url in (self.url(), f'/spaces/{self.space.pk}/', self.url('?view=invalid'), self.url('?status=bad&priority=bad&summary=bad&assignee=99999999999999999999999')):
            response = self.response(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['summary']['total'], 0)
            self.assertContains(response, 'Przegląd statusów')
            self.assertContains(response, 'Brak aktywności')
            self.assertNotContains(response, 'work-pagination')
        self.client.logout()
        self.assertEqual(self.client.get(self.url()).status_code, 302)

    def test_activity_order_limit_system_actor_and_escaping(self):
        task = self.task()
        task.title = '<script>alert("task")</script>'
        task.save()
        for number in range(10):
            activity = SpaceTaskActivity.objects.create(task=task, actor=None, action='commented', message='<script>secret</script>')
            SpaceTaskActivity.objects.filter(pk=activity.pk).update(created_at=self.now - timedelta(minutes=number))
        response = self.response()
        rows = response.context['summary']['activities']
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[0]['actor'], 'System')
        self.assertTrue(all(a['created_at'] >= b['created_at'] for a, b in zip(rows, rows[1:])))
        self.assertContains(response, '&lt;script&gt;alert')
        self.assertNotContains(response, '<script>secret</script>')

    def test_epic_progress_counts_only_visible_children(self):
        self.space.kind = 'software'
        self.space.save()
        epic = self.task()
        type(epic.work_item).objects.filter(task=epic).update(work_type='epic')
        open_task = self.task()
        closed = self.task(status='closed')
        hidden = self.task(status='closed', visibility='private', private_owner=self.owner)
        type(epic.work_item).objects.filter(task__in=[open_task, closed, hidden]).update(epic=epic.work_item)
        rows = self.response().context['summary']['epics']
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['total'], rows[0]['closed'], rows[0]['percent']), (2, 1, 50))
        self.assertIn(f'/tasks/{epic.work_item.key}/', rows[0]['url'])
        SpaceTaskMembership.objects.create(task=hidden, user=self.member, role='observer')
        self.assertEqual(self.response().context['summary']['epics'][0]['total'], 3)
        self.space.kind = 'business'
        self.space.save()
        self.assertEqual(self.response().context['summary']['epics'], [])
