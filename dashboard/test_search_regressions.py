from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from dashboard.recent import RECENT_SESSION_KEY
from dashboard.views import GLOBAL_SEARCH_GROUP_LIMIT, GLOBAL_SEARCH_RECENT_LIMIT
from kanban.models import Kanban
from tasks.models import Task, TaskProject, TaskSection
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
        for model, group_key in [(Task, 'tasks')]:
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
            TaskProject.objects.create(user=self.owner, workplace=self.team, name=f'Limit probe {index}')
        Task.objects.create(user=self.owner, workplace=self.team, title='Limit probe')
        with CaptureQueriesContext(connection) as queries:
            payload = self.search('Limit probe').json()
        self.assertTrue(payload['truncated'])
        self.assertEqual(payload['total'], 2 * GLOBAL_SEARCH_GROUP_LIMIT)
        for key in ['tasks', 'projects']:
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

    def remember(self, *objects):
        session = self.client.session
        session[RECENT_SESSION_KEY] = [
            {'identity': [self.member.pk, self.team.pk, obj._meta.label_lower, obj.pk],
             'at': timezone.now().isoformat()} for obj in objects
        ]
        session.save()

    def recent(self):
        response = self.client.get(reverse('global_search'), {'recent': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'no-store')
        return response.json()

    def test_recent_is_explicit_empty_and_requires_login(self):
        self.assertEqual(self.recent()['groups'], [])
        task = Task.objects.create(user=self.owner, workplace=self.team, title='Recently opened')
        self.remember(task)
        self.assertEqual(self.search('').json()['groups'], [])
        self.assertEqual(self.search('R').json()['groups'], [])
        self.client.logout()
        self.assertEqual(self.client.get(reverse('global_search'), {'recent': '1'}).status_code, 302)

    def test_recent_preserves_order_limits_results_and_resolves_current_titles_and_numbers(self):
        tasks = [Task.objects.create(user=self.owner, workplace=self.team, title=f'Recent {index}')
                 for index in range(GLOBAL_SEARCH_RECENT_LIMIT + 2)]
        self.remember(*reversed(tasks))
        tasks[-1].title = 'Renamed recently'
        tasks[-1].save()
        tasks[0].delete()
        payload = self.recent()
        self.assertEqual(payload['total'], GLOBAL_SEARCH_RECENT_LIMIT)
        rows = payload['groups'][0]['results']
        self.assertEqual([row['title'] for row in rows], [task.title for task in reversed(tasks[-GLOBAL_SEARCH_RECENT_LIMIT:])])
        self.assertEqual(parse_qs(urlsplit(rows[0]['url']).query)['task_pk'], [str(tasks[-1].pk)])
        self.assertEqual(self.client.get(rows[0]['url']).context['task'].pk, tasks[-1].pk)

    def test_recent_rechecks_parent_privacy_deletion_and_workspace_membership(self):
        project = TaskProject.objects.create(user=self.owner, workplace=self.team, name='Recent project')
        section = TaskSection.objects.create(project=project, title='Recent group')
        task = Task.objects.create(user=self.owner, workplace=self.team, section=section, title='Recent task')
        parent = Task.objects.create(user=self.owner, workplace=self.team, title='Private parent',
                                     visibility='private', private_owner=self.owner)
        child = Task.objects.create(user=self.owner, workplace=self.team, parent=parent, title='Hidden child')
        card = Kanban.objects.create(user=self.owner, workplace=self.team, title='Recent card')
        self.remember(project, section, task, child, card)
        self.assertEqual(self.recent()['total'], 3)
        project.visibility, project.private_owner = 'private', self.owner
        project.save()
        self.assertEqual(self.recent()['groups'], [])
        card.delete()
        self.assertEqual(self.recent()['total'], 0)
        self.membership.delete()
        self.assertEqual(self.recent()['total'], 0)

    def test_recent_never_trusts_session_ids_as_workspace_or_account_access(self):
        visible = Task.objects.create(user=self.owner, workplace=self.team, title='Visible')
        foreign = Task.objects.create(user=self.owner, workplace=self.private, title='Foreign Workspace')
        other_owner = Task.objects.create(user=self.member, workplace=self.team, title='Foreign owner')
        self.remember(visible, foreign, other_owner)
        self.assertEqual([row['title'] for row in self.recent()['groups'][0]['results']], [visible.title])
        session = self.client.session
        session[RECENT_SESSION_KEY][0]['identity'][0] = self.owner.pk
        session.save()
        self.assertEqual(self.recent()['groups'], [])

    def test_recent_task_metadata_does_not_expose_foreign_legacy_group(self):
        project = TaskProject.objects.create(user=self.owner, workplace=self.private, name='Foreign project')
        section = TaskSection.objects.create(project=project, title='Foreign group')
        task = Task.objects.create(user=self.owner, workplace=self.team, title='Legacy link')
        # Simulate an old inconsistent relation without today's save normalization.
        Task.objects.filter(pk=task.pk).update(section=section)
        self.remember(task)
        rows = self.recent()['groups'][0]['results']
        self.assertEqual(rows[0]['meta'], f'#{task.task_id}')

    def test_recent_records_current_space_views_and_rechecks_revoked_access(self):
        project = TaskProject.objects.create(user=self.owner, workplace=self.team, name='Opened space')
        for url in (f'/spaces/{project.space.pk}/', f'/workplaces/{self.team.slug}/spaces/{project.space.pk}/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
                rows = self.recent()['groups'][0]['results']
                self.assertEqual(rows[0]['title'], project.name)
                self.assertEqual(rows[0]['url'], f'/workplaces/{self.team.slug}/spaces/{project.space.pk}/')
        self.assertEqual(self.recent()['total'], 1)
        project.visibility, project.private_owner = 'private', self.owner
        project.save()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.recent()['total'], 0)

    def test_recent_records_real_base_and_scoped_visits_with_subtask_links(self):
        parent = Task.objects.create(user=self.owner, workplace=self.team, title='Parent recent')
        child = Task.objects.create(user=self.owner, workplace=self.team, parent=parent, title='Child recent')
        for prefix in ('/tasks/', f'/workplaces/{self.team.slug}/tasks/'):
            with self.subTest(prefix=prefix):
                response = self.client.get(f'{prefix}view-subtask/{child.task_id}/', {'task_pk': child.pk})
                self.assertEqual(response.status_code, 200)
                row = self.recent()['groups'][0]['results'][0]
                self.assertEqual(row['title'], child.title)
                self.assertEqual(row['type'], 'Podzadanie')
                self.assertIn('/view-subtask/', row['url'])
                self.assertEqual(self.client.get(row['url']).context['task'].pk, child.pk)
