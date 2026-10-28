"""Task view loading through the real HTML and React page endpoints."""
from datetime import date
from html import unescape
import re
from urllib.parse import parse_qs, urlencode, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import SpaceMembership, SpaceTask, Sprint, WorkItem
from .testing import make_space


class ListWindowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='list-window-owner', email='list-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='list-window-member', email='list-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Lista zadań')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Lista', template='scrum',
                               visibility='private', private_owner=cls.owner)
        SpaceMembership.objects.create(space=cls.space, user=cls.member)
        cls.tasks = {}
        for status, total in [('new', 121), ('in_progress', 21), ('resolved', 20), ('reopened', 1)]:
            cls.tasks[status] = [SpaceTask.objects.create(
                space=cls.space, created_by=cls.owner, title=f'Praca {status} {index:03}', status=status,
                priority='high' if index % 2 == 0 else 'low', assignee=cls.member if index % 3 == 0 else None,
            ) for index in range(total)]
        hidden = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='Praca ukryta',
                                          visibility='private', private_owner=cls.owner, assignee=cls.member)
        child = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='Praca ukryty rodzic', parent=hidden)
        cls.hidden_ids = {hidden.pk, child.pk}
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Druga lista')
        WorkplaceMembership.objects.create(workplace=cls.other_workspace, user=cls.member)
        cls.other_space = make_space(user=cls.owner, workplace=cls.other_workspace, name='Lista', slug=cls.space.slug)
        cls.foreign = SpaceTask.objects.create(space=cls.other_space, created_by=cls.owner, title='Obcy Workspace')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def url(self, scoped=True, **params):
        path = (scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
                if scoped else f'/space/{self.space.slug}/')
        return path + '?' + urlencode({'view': 'list', **params})

    def page(self, url=None, *, scoped=True, **params):
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
        response = self.client.get(api, {'url': url or self.url(scoped, **params)}, follow=True)
        self.assertEqual(response.status_code, 200)
        return response.json()['data']

    def columns(self, data):
        return {column['key']: column for column in data['columns']}

    def group_ids(self, data, status='new'):
        return [item['task_id'] for item in data['items'] if item['status'] == status]

    def test_first_html_and_api_load_twenty_per_status_with_full_visible_counts(self):
        for scoped in (True, False):
            with self.subTest(scoped=scoped):
                response = self.client.get(self.url(scoped), follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.context['page'])
                self.assertEqual(len(response.context['items']), 61)
                for column in response.context['columns']:
                    expected = len(self.tasks.get(column['key'], []))
                    self.assertEqual(column['count'], expected)
                    self.assertEqual(column['loaded_count'], min(20, expected))
                data = self.page(scoped=scoped)
                self.assertIsNone(data['pagination'])
                columns = self.columns(data)
                self.assertEqual((columns['new']['loaded_count'], columns['new']['count']), (20, 121))
                self.assertEqual((columns['in_progress']['loaded_count'], columns['in_progress']['count']), (20, 21))
                self.assertTrue(columns['in_progress']['more_url'])
                self.assertEqual(columns['resolved']['more_url'], '')
                self.assertEqual(columns['closed']['more_url'], '')
                self.assertEqual(columns['closed']['loaded_count'], 0)
                self.assertEqual(data['stats']['all'], 163)
                self.assertFalse(self.hidden_ids.intersection(item['task_id'] for item in data['items']))
                self.assertNotIn(self.foreign.pk, [item['task_id'] for item in data['items']])

    def test_show_more_retains_rows_and_reaches_every_item_beyond_the_old_page_size(self):
        data = self.page(page='99')
        expected = [task.pk for task in self.tasks['new']]
        for loaded in (20, 40, 60, 80, 100, 120, 121):
            with self.subTest(loaded=loaded):
                self.assertEqual(self.group_ids(data), expected[:loaded])
                self.assertEqual(len(self.group_ids(data, 'in_progress')), 20)
                column = self.columns(data)['new']
                self.assertEqual(column['loaded_count'], loaded)
                if loaded == 121:
                    self.assertEqual(column['more_url'], '')
                else:
                    self.assertNotIn('page', parse_qs(urlsplit(column['more_url']).query))
                    data = self.page(column['more_url'])
        self.assertEqual(len(set(self.group_ids(data))), 121)

    def test_final_partial_batch_and_independent_limits_keep_filters_and_sort(self):
        data = self.page(list_limit_new=40, sort='title_desc', q='Praca', page=2)
        target = self.columns(data)['in_progress']['more_url']
        params = parse_qs(urlsplit(target).query)
        self.assertEqual(params, {'view': ['list'], 'list_limit_new': ['40'], 'sort': ['title_desc'],
                                  'q': ['Praca'], 'list_limit_in_progress': ['21']})
        data = self.page(target)
        self.assertEqual(self.group_ids(data), [task.pk for task in reversed(self.tasks['new'])][:40])
        self.assertEqual(self.group_ids(data, 'in_progress'), [task.pk for task in reversed(self.tasks['in_progress'])])
        self.assertEqual(self.columns(data)['in_progress']['more_url'], '')
        next_params = parse_qs(urlsplit(self.columns(data)['new']['more_url']).query)
        self.assertEqual(next_params['list_limit_new'], ['60'])
        self.assertEqual(next_params['list_limit_in_progress'], ['21'])

    def test_counts_and_prefixes_use_combined_filters_and_stable_sort(self):
        data = self.page(priority='high', assignee='me', q='Praca', sort='number_desc')
        for status, tasks in self.tasks.items():
            filtered = [task for index, task in enumerate(tasks) if index % 6 == 0]
            column = self.columns(data)[status]
            self.assertEqual(column['count'], len(filtered))
            self.assertEqual(self.group_ids(data, status), [task.pk for task in reversed(filtered)][:20])
        empty = self.page(q='Brak takiego zadania', list_limit_new=80)
        self.assertEqual(empty['items'], [])
        self.assertTrue(all(column['count'] == 0 and column['more_url'] == '' for column in empty['columns']))

    def test_invalid_and_oversized_limits_are_bounded_by_visible_rows(self):
        for value in ('', '-1', '0', '5', 'abc', '20.5', '９９', '0' * 200):
            with self.subTest(value=value):
                data = self.page(list_limit_new=value, page=2)
                self.assertEqual(self.group_ids(data), [task.pk for task in self.tasks['new'][:20]])
        for value in ('9999999999999999999999999999999', '0' * 200 + '121'):
            with self.subTest(value=value):
                data = self.page(list_limit_new=value)
                self.assertEqual(self.group_ids(data), [task.pk for task in self.tasks['new']])
                self.assertEqual(self.columns(data)['new']['more_url'], '')

    def test_loading_again_rechecks_private_task_parent_and_space_access(self):
        data = self.page()
        target = self.columns(data)['new']['more_url']
        task = self.tasks['new'][0]
        task.visibility, task.private_owner = 'private', self.owner
        task.save(update_fields=['visibility', 'private_owner'])
        data = self.page(target)
        self.assertEqual(self.columns(data)['new']['count'], 120)
        self.assertEqual(self.group_ids(data), [item.pk for item in self.tasks['new'][1:41]])
        SpaceMembership.objects.filter(space=self.space, user=self.member).delete()
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        self.assertEqual(self.client.get(api, {'url': target}).status_code, 404)

    def test_same_slug_in_another_workspace_keeps_its_own_counts(self):
        api = scoped_workplace_app_path(self.other_workspace, 'api', 'v1/page/')
        target = scoped_workplace_app_path(self.other_workspace, 'space', self.other_space.slug + '/')
        response = self.client.get(api, {'url': target + '?view=list&list_limit_new=100'})
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(self.group_ids(data), [self.foreign.pk])
        self.assertEqual(self.columns(data)['new']['count'], 1)

    def test_create_and_task_urls_preserve_expanded_list_context(self):
        data = self.page(list_limit_new=40, list_limit_in_progress=21, sort='number_desc', q='Praca')
        expected = {'view': ['list'], 'list_limit_new': ['40'], 'list_limit_in_progress': ['21'],
                    'sort': ['number_desc'], 'q': ['Praca']}
        self.assertEqual(parse_qs(urlsplit(data['create_item_url']).query), expected)
        for key in ('url', 'edit_url', 'action_url'):
            self.assertEqual(parse_qs(urlsplit(data['items'][0][key]).query), expected)
        response = self.client.post(data['create_item_url'], {'title': 'Praca nowa', 'description': '',
            'priority': 'none', 'work_type': 'task', 'status': 'new'}, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['saved'])
        self.assertEqual(parse_qs(urlsplit(response.json()['url']).query), expected)

    def test_board_loads_every_visible_item_without_pagination_even_with_stale_page(self):
        sprint = Sprint.objects.create(space=self.space, name='Aktywny', state='active',
                                       start_on=date(2026, 10, 1), end_on=date(2026, 10, 31))
        WorkItem.objects.filter(space=self.space).update(sprint=sprint, in_backlog=False)
        expected = {task.pk for tasks in self.tasks.values() for task in tasks}
        for template in ('scrum', 'kanban'):
            self.space.template = template
            self.space.save(update_fields=['template'])
            for scoped in (True, False):
                with self.subTest(template=template, scoped=scoped):
                    data = self.page(scoped=scoped, view='board', page=2, list_limit_new=20)
                    self.assertIsNone(data['pagination'])
                    self.assertEqual({item['task_id'] for item in data['items']}, expected)
                    self.assertEqual(len(data['items']), 163)
                    self.assertEqual(self.columns(data)['new']['count'], 121)
                    self.assertTrue(all('more_url' not in column for column in data['columns']))
                    response = self.client.get(self.url(scoped, view='board', page=99), follow=True)
                    self.assertIsNone(response.context['page'])
                    self.assertEqual({item.task_id for item in response.context['items']}, expected)
                    self.assertContains(response, 'data-work-card', count=163)
                    self.assertNotContains(response, 'work-pagination')

    def test_board_keeps_filters_and_sort_and_has_no_footer_when_empty(self):
        self.space.template = 'kanban'
        self.space.save(update_fields=['template'])
        WorkItem.objects.filter(space=self.space).update(in_backlog=False)
        data = self.page(view='board', page=2, q='Praca new', sort='title_desc')
        self.assertEqual(self.group_ids(data), [task.pk for task in reversed(self.tasks['new'])])
        self.assertEqual(self.columns(data)['new']['count'], 121)
        self.assertTrue(all(item['status'] == 'new' for item in data['items']))
        empty = self.page(view='board', page=2, q='Brak takiego zadania')
        self.assertEqual(empty['items'], [])
        self.assertIsNone(empty['pagination'])
        response = self.client.get(self.url(view='board', page=2, q='Brak takiego zadania'))
        self.assertNotContains(response, 'work-pagination')

    def test_timeline_loads_all_visible_filtered_tasks_without_pagination(self):
        WorkItem.objects.filter(space=self.space).update(start_on=date(2026, 10, 1))
        for scoped in (True, False):
            with self.subTest(scoped=scoped):
                data = self.page(scoped=scoped, view='timeline', list_limit_new=120, page=2)
                self.assertIsNone(data['pagination'])
                self.assertEqual(len(data['items']), 163)
                self.assertEqual(data['stats']['all'], 163)
                self.assertTrue(all('more_url' not in column for column in data['columns']))
                task_ids = [item['task_id'] for item in data['items']]
                self.assertFalse(self.hidden_ids.intersection(task_ids))
                self.assertNotIn(self.foreign.pk, task_ids)
                initial = self.page(scoped=scoped, view='timeline')
                self.assertEqual([item['task_id'] for item in initial['items']], task_ids)
                filtered = self.page(scoped=scoped, view='timeline', page=2, q='Praca new', sort='title_desc')
                self.assertEqual([item['task_id'] for item in filtered['items']], [task.pk for task in reversed(self.tasks['new'])])
                self.assertEqual(self.columns(filtered)['new']['count'], 121)
                self.assertIsNone(filtered['pagination'])
                response = self.client.get(self.url(scoped, view='timeline', page=2), follow=True)
                self.assertIsNone(response.context['page'])
                self.assertEqual(len(response.context['items']), 163)
                self.assertNotContains(response, 'work-pagination')
                self.assertNotContains(response, 'work-timeline-footer')

    def test_html_sort_and_filter_links_restart_groups_without_javascript(self):
        response = self.client.get(self.url(list_limit_new=60, list_limit_in_progress=21,
                                           sort='title_desc', priority='high', q='Praca'))
        html = response.content.decode()
        for label, expected_sort, expected_count in [('Tytuł · rosnąco', 'title_asc', 61), ('Wyczyść', 'title_desc', 121)]:
            with self.subTest(label=label):
                match = re.search(r'href="([^"]+)">' + re.escape(label) + r'</a>', html)
                self.assertIsNotNone(match)
                href = unescape(match.group(1))
                params = parse_qs(urlsplit(href).query)
                self.assertFalse(any(key.startswith('list_limit_') for key in params))
                self.assertEqual(params['sort'], [expected_sort])
                self.assertEqual(params['q'], ['Praca'])
                refreshed = self.client.get(urlsplit(self.url()).path + href)
                self.assertEqual(refreshed.status_code, 200)
                column = next(column for column in refreshed.context['columns'] if column['key'] == 'new')
                self.assertEqual((column['loaded_count'], column['count']), (20, expected_count))

        overview = self.client.get(self.url(view='overview', priority='high', list_limit_new=60))
        match = re.search(r'href="([^"]+)">Wyczyść</a>', overview.content.decode())
        self.assertIsNotNone(match)
        params = parse_qs(urlsplit(unescape(match.group(1))).query)
        self.assertEqual(params, {'view': ['overview']})
