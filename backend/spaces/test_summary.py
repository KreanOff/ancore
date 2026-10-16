from .testing import make_space
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import SpaceTask, SpaceTaskActivity, SpaceTaskMembership, Space, SpaceMembership
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


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

    def test_priority_type_and_workload_totals_include_all_pages_and_subtasks(self):
        parent = self.task(priority='high', assignee=self.member)
        self.task(parent=parent, priority='urgent', assignee=self.member)
        for _ in range(103):
            self.task(priority='none')
        self.task(status='closed', priority='urgent', assignee=self.owner)
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
        self.assertEqual([row['key'] for row in summary['activities']], [visible.work_item.key, visible.work_item.key])
        self.assertEqual(summary['activities'][0]['actor'], 'Jan')
        self.assertIn(f'/tasks/{visible.work_item.key}/', summary['activities'][0]['url'])
        SpaceTaskMembership.objects.create(task=hidden, user=self.member, role='observer')
        self.assertEqual(self.response().context['summary']['total'], 3)
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
