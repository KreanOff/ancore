from datetime import date, timedelta
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import SpaceTask, Sprint
from .testing import make_space


class ItemQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='query-owner', email='query-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='query-member', email='query-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Sortowanie i filtry')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Zadania', template='scrum')
        cls.tasks = [SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title=title, priority=priority,
                                            assignee=cls.member if index % 2 else None,
                                            due_at=timezone.now() + timedelta(days=index) if index else None)
                     for index, (title, priority) in enumerate(zip(('Zebra', 'alpha', 'Beta', 'Delta', 'Gamma'),
                                                                  ('none', 'low', 'medium', 'high', 'urgent')))]
        for index, task in enumerate(cls.tasks):
            item = task.work_item
            item.start_on = date(2026, 10, 1) + timedelta(days=index)
            item.points = 5 - index
            item.save(update_fields=['start_on', 'points'])
        cls.private = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='AAA prywatne',
                                              visibility='private', private_owner=cls.owner, assignee=cls.member)
        other = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        foreign = make_space(user=cls.owner, workplace=other, name='Inny zakres')
        SpaceTask.objects.create(space=foreign, created_by=cls.owner, title='AAA obce')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, plain=False):
        suffix = f'{self.space.slug}/'
        return f'/space/{suffix}' if plain else scoped_workplace_app_path(self.workspace, 'space', suffix)

    def rows(self, **params):
        response = self.client.get(self.url(), {'view': 'list', **params})
        self.assertEqual(response.status_code, 200)
        return [row.task_id for row in response.context['items']]

    def test_sorting_on_plain_and_scoped_routes_preserves_acl_and_numeric_key_order(self):
        for plain in (False, True):
            response = self.client.get(self.url(plain), {'view': 'list', 'sort': 'title_asc'}, follow=True)
            self.assertEqual([row.task_id for row in response.context['items']],
                             [self.tasks[index].pk for index in (1, 2, 3, 4, 0)])
            self.assertNotContains(response, self.private.title)
        self.assertEqual(self.rows(sort='number_desc'), [task.pk for task in reversed(self.tasks)])
        self.assertEqual(self.rows(sort='priority_desc'), [task.pk for task in reversed(self.tasks)])

    def test_dates_nulls_points_and_invalid_sort(self):
        self.assertEqual(self.rows(sort='due_asc'), [task.pk for task in self.tasks[1:] + self.tasks[:1]])
        self.assertEqual(self.rows(sort='due_desc'), [task.pk for task in list(reversed(self.tasks[1:])) + self.tasks[:1]])
        self.assertEqual(self.rows(sort='points_asc'), [task.pk for task in reversed(self.tasks)])
        self.assertEqual(self.rows(sort='start_desc'), [task.pk for task in reversed(self.tasks)])
        self.assertEqual(self.rows(sort='created_asc'), [task.pk for task in self.tasks])
        self.assertEqual(self.rows(sort='task__private_owner__email'), self.rows())

    def test_filters_combine_with_sort_and_api_reports_current_settings(self):
        target = self.url() + '?view=list&sort=title_desc&assignee=me&priority=high&q=Delta'
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        response = self.client.get(api, {'url': target})
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual([row['task_id'] for row in data['items']], [self.tasks[3].pk])
        self.assertEqual(data['sort']['value'], 'title_desc')
        self.assertFalse(data['sort']['manual'])
        self.assertEqual(data['filters']['assignee'], 'me')
        self.assertNotIn(self.private.title, json.dumps(data))

    def test_custom_sort_cannot_reorder_manual_ranks(self):
        item = self.tasks[0].work_item
        url = scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/tasks/{item.key}/action/')
        for action in ('up', 'down', 'position', 'plan'):
            response = self.client.post(url + '?sort=title_asc', {'action': action}, HTTP_X_WORK_ACTION='true')
            self.assertEqual(response.status_code, 400)
        item.refresh_from_db()
        self.assertEqual(item.rank, self.tasks[0].work_item.rank)

    def test_sorted_pagination_and_bulk_planning_use_the_same_visible_page(self):
        for index in range(100):
            SpaceTask.objects.create(space=self.space, created_by=self.owner, title=f'Zadanie {index:03}')
        last = SpaceTask.objects.create(space=self.space, created_by=self.owner, title='AAA pierwsze po sortowaniu').work_item
        params = {'view': 'backlog', 'sort': 'title_asc'}
        first = self.client.get(self.url(), params)
        second = self.client.get(self.url(), {**params, 'page': 2})
        self.assertEqual(first.context['items'][0].pk, last.pk)
        self.assertEqual(first.context['page'].paginator.count, 106)
        first_ids = {row.pk for row in first.context['items']}
        second_ids = {row.pk for row in second.context['items']}
        self.assertFalse(first_ids & second_ids)
        numbered = self.client.get(self.url(), {'view': 'backlog', 'sort': 'number_desc'})
        self.assertEqual([row.number for row in numbered.context['items']], list(range(last.number, last.number - 100, -1)))
        sprint = Sprint.objects.create(space=self.space, name='Plan', start_on=date(2026, 10, 1), end_on=date(2026, 10, 14))
        response = self.client.post(first.context['bulk_plan_url'], {
            'item_ids': [str(last.pk)], 'destination': str(sprint.pk),
            'positions': json.dumps({str(last.pk): [last.sprint_id, last.rank]}),
        }, HTTP_X_WORK_ACTION='true')
        self.assertEqual(response.status_code, 200)
        last.refresh_from_db()
        self.assertEqual(last.sprint_id, sprint.pk)
        outside = second.context['items'][0]
        response = self.client.post(first.context['bulk_plan_url'], {
            'item_ids': [str(outside.pk)], 'destination': str(sprint.pk),
            'positions': json.dumps({str(outside.pk): [outside.sprint_id, outside.rank]}),
        }, HTTP_X_WORK_ACTION='true')
        self.assertEqual(response.status_code, 400)
