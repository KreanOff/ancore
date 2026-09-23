from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from contacts.models import Company
from dashboard.views import GLOBAL_SEARCH_GROUP_LIMIT
from kanban.models import Kanban
from tasks.models import Task
from workplaces.models import WorkplaceMembership, create_workplace_for_user


class GlobalSearchRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='search-owner', email='search-owner@example.test')
        cls.member = users.objects.create_user(username='search-member', email='search-member@example.test')
        cls.team = create_workplace_for_user(cls.owner, 'Search shared workspace')
        cls.private = create_workplace_for_user(cls.owner, 'Search confidential workspace')
        cls.private.description = 'Confidential description'
        cls.private.save(update_fields=['description'])
        cls.personal = create_workplace_for_user(cls.member, 'Search personal workspace')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.team, user=cls.member, role='member')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.team.pk
        session.save()

    def search(self, query):
        response = self.client.get(reverse('global_search'), {'q': query})
        self.assertEqual(response.status_code, 200)
        return response

    def test_workspace_results_follow_viewer_memberships_not_data_owner(self):
        response = self.search('Search')
        group = next(group for group in response.json()['groups'] if group['key'] == 'workplaces')
        self.assertCountEqual([row['title'] for row in group['results']], [self.team.name, self.personal.name])
        self.assertNotContains(response, self.private.name)
        self.assertNotContains(response, self.private.description)
        self.assertNotContains(response, self.private.slug)

    def test_revoked_membership_removes_workspace_and_business_results(self):
        Task.objects.create(user=self.owner, workplace=self.team, title='Search shared task')
        self.membership.delete()
        response = self.search('Search')
        titles = [row['title'] for group in response.json()['groups'] for row in group['results']]
        self.assertIn(self.personal.name, titles)
        self.assertNotIn(self.team.name, titles)
        self.assertNotIn(self.private.name, titles)
        self.assertNotIn('Search shared task', titles)

    def test_task_and_subtask_links_survive_renumbering_and_never_retarget_deleted_records(self):
        for model, group_key in [(Task, 'tasks'), (Kanban, 'kanban-cards')]:
            for is_child in (False, True):
                with self.subTest(model=model.__name__, child=is_child):
                    first = model.objects.create(user=self.owner, workplace=self.team, title='Earlier item')
                    parent = model.objects.create(user=self.owner, workplace=self.team, title='Parent') if is_child else None
                    selected = model.objects.create(user=self.owner, workplace=self.team, parent=parent,
                                                    title=f'Search target {model.__name__} {is_child}')
                    model.objects.create(user=self.owner, workplace=self.team, parent=parent, title='Later item')
                    group = next(group for group in self.search(selected.title).json()['groups'] if group['key'] == group_key)
                    link = group['results'][0]['url']
                    self.assertEqual(parse_qs(urlsplit(link).query)['task_pk'], [str(selected.pk)])
                    self.assertIn('/view-subtask/' if is_child else '/view-task/', link)
                    first.delete()
                    response = self.client.get(link)
                    self.assertEqual(response.context['task'].pk, selected.pk)
                    selected.delete()
                    self.assertEqual(self.client.get(link).status_code, 404)

    def test_unicode_and_oversized_numeric_queries_are_safe(self):
        item = Task.objects.create(user=self.owner, workplace=self.team, title='Area ²²')
        for query in ['²²', '①①', '9' * 120, '٠١']:
            with self.subTest(query=query):
                response = self.search(query)
                if query in ['²²', '٠١']:
                    self.assertIn(item.title, [row['title'] for group in response.json()['groups'] for row in group['results']])

    def test_each_group_is_limited_in_sql_and_exact_matches_stay_first(self):
        for index in range(GLOBAL_SEARCH_GROUP_LIMIT + 3):
            Task.objects.create(user=self.owner, workplace=self.team, title=f'Limit probe {index}')
            Company.objects.create(owner=self.owner, workplace=self.team, name=f'Limit probe {index}')
        Task.objects.create(user=self.owner, workplace=self.team, title='Limit probe')
        with CaptureQueriesContext(connection) as queries:
            payload = self.search('Limit probe').json()
        self.assertTrue(payload['truncated'])
        self.assertEqual(payload['total'], 2 * GLOBAL_SEARCH_GROUP_LIMIT)
        for key in ['tasks', 'companies']:
            group = next(group for group in payload['groups'] if group['key'] == key)
            self.assertEqual(len(group['results']), GLOBAL_SEARCH_GROUP_LIMIT)
            self.assertTrue(group['has_more'])
        self.assertEqual(next(group for group in payload['groups'] if group['key'] == 'tasks')['results'][0]['title'], 'Limit probe')
        search_sql = [query['sql'] for query in queries if '_global_search_rank' in query['sql']]
        self.assertTrue(search_sql)
        self.assertTrue(all(f'LIMIT {GLOBAL_SEARCH_GROUP_LIMIT + 1}' in sql for sql in search_sql))

    def test_exact_limit_is_not_reported_as_truncated(self):
        for index in range(GLOBAL_SEARCH_GROUP_LIMIT):
            Task.objects.create(user=self.owner, workplace=self.team, title=f'Boundary probe {index}')
        payload = self.search('Boundary probe').json()
        self.assertEqual(payload['total'], GLOBAL_SEARCH_GROUP_LIMIT)
        self.assertFalse(payload['truncated'])
        self.assertFalse(payload['groups'][0]['has_more'])
