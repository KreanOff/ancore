"""Backlog group loading through the HTML and React endpoints."""
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


class BacklogWindowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='backlog-window-owner', email='backlog-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='backlog-window-member', email='backlog-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Backlog')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Backlog', template='scrum',
                               visibility='private', private_owner=cls.owner)
        SpaceMembership.objects.create(space=cls.space, user=cls.member)
        cls.active, cls.planned, cls.finished, cls.closed = [Sprint.objects.create(
            space=cls.space, name=name, state=state, start_on=date(2026, 10, 1), end_on=date(2026, 10, 31),
        ) for name, state in [('Aktywny', 'active'), ('Planowany', 'planned'), ('Ukończone zadania', 'planned'), ('Zakończony', 'closed')]]
        cls.tasks = {}
        for sprint, total in [(None, 121), (cls.active, 21), (cls.planned, 3), (cls.finished, 2), (cls.closed, 1)]:
            cls.tasks[getattr(sprint, 'pk', None)] = tasks = [SpaceTask.objects.create(
                space=cls.space, created_by=cls.owner, title=f'Praca {index:03}',
                status='closed' if sprint == cls.finished else 'new',
                priority='high' if index % 2 == 0 else 'low', assignee=cls.member if index % 3 == 0 else None,
            ) for index in range(total)]
            WorkItem.objects.filter(task__in=tasks).update(sprint=sprint, in_backlog=sprint is None)
        hidden = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='Praca ukryta',
                                         visibility='private', private_owner=cls.owner, assignee=cls.member)
        child = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='Praca ukryty rodzic', parent=hidden)
        cls.hidden_ids = {hidden.pk, child.pk}
        WorkItem.objects.filter(task_id__in=cls.hidden_ids).update(rank=0)
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Drugi backlog')
        WorkplaceMembership.objects.create(workplace=cls.other_workspace, user=cls.member)
        other = make_space(user=cls.owner, workplace=cls.other_workspace, name='Backlog', slug=cls.space.slug)
        cls.foreign = SpaceTask.objects.create(space=other, created_by=cls.owner, title='Obcy Workspace')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def url(self, scoped=True, **params):
        path = (scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
                if scoped else f'/space/{self.space.slug}/')
        return path + '?' + urlencode({'view': 'backlog', **params})

    def page(self, url=None, *, scoped=True, **params):
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
        response = self.client.get(api, {'url': url or self.url(scoped, **params)}, follow=True)
        self.assertEqual(response.status_code, 200)
        return response.json()['data']

    def group_ids(self, data, sprint=None):
        return [item['task_id'] for item in data['items'] if item['sprint_id'] == getattr(sprint, 'pk', None)]

    def sprint_data(self, data, sprint):
        return next(row for row in data['sprints'] if row['id'] == sprint.pk)

    def test_html_and_api_load_twenty_per_group_after_acl_without_pagination(self):
        for scoped in (True, False):
            with self.subTest(scoped=scoped):
                data = self.page(scoped=scoped, page=99)
                self.assertIsNone(data['pagination'])
                self.assertEqual((data['backlog_loaded_count'], data['backlog_totals']['total']), (20, 121))
                active = self.sprint_data(data, self.active)
                self.assertEqual((active['loaded_count'], active['planning']['total']), (20, 21))
                self.assertTrue(active['more_url'])
                planned = self.sprint_data(data, self.planned)
                self.assertEqual((planned['loaded_count'], planned['more_url']), (3, ''))
                finished = self.sprint_data(data, self.finished)
                self.assertEqual((finished['loaded_count'], finished['more_url']), (0, ''))
                self.assertEqual((finished['planning']['total'], finished['planning']['finished']), (2, 2))
                self.assertNotIn(self.closed.pk, [sprint['id'] for sprint in data['sprints']])
                self.assertEqual(self.group_ids(data), [task.pk for task in self.tasks[None][:20]])
                self.assertFalse(self.hidden_ids.intersection(item['task_id'] for item in data['items']))
                self.assertNotIn(self.foreign.pk, [item['task_id'] for item in data['items']])
                response = self.client.get(self.url(scoped, page=99), follow=True)
                self.assertIsNone(response.context['page'])
                self.assertEqual(len(response.context['items']), 43)
                self.assertNotContains(response, 'work-pagination')
                self.assertNotContains(response, 'Zadania znajdują się na innej stronie wyników.')

    def test_more_retains_existing_rows_and_reaches_all_items_beyond_one_hundred(self):
        data = self.page(page=2)
        for loaded in (20, 40, 60, 80, 100, 120, 121):
            with self.subTest(loaded=loaded):
                self.assertEqual(data['backlog_loaded_count'], loaded)
                self.assertEqual(self.group_ids(data), [task.pk for task in self.tasks[None][:loaded]])
                self.assertEqual(len(self.group_ids(data, self.active)), 20)
                if loaded == 121:
                    self.assertEqual(data['backlog_more_url'], '')
                else:
                    self.assertNotIn('page', parse_qs(urlsplit(data['backlog_more_url']).query))
                    data = self.page(data['backlog_more_url'])
        self.assertEqual(len(set(self.group_ids(data))), 121)

    def test_group_limits_are_independent_and_links_preserve_scope_filters_and_sort(self):
        for scoped in (True, False):
            with self.subTest(scoped=scoped):
                data = self.page(scoped=scoped, backlog_limit_backlog=40, q='Praca', sort='title_desc', page=2)
                target = self.sprint_data(data, self.active)['more_url']
                self.assertEqual(urlsplit(target).path, urlsplit(self.url()).path)
                self.assertEqual(parse_qs(urlsplit(target).query), {
                    'view': ['backlog'], 'backlog_limit_backlog': ['40'], 'q': ['Praca'], 'sort': ['title_desc'],
                    f'backlog_limit_sprint_{self.active.pk}': ['21'],
                })
                expanded = self.page(target, scoped=scoped)
                self.assertEqual(self.group_ids(expanded), [task.pk for task in reversed(self.tasks[None])][:40])
                self.assertEqual(self.group_ids(expanded, self.active), [task.pk for task in reversed(self.tasks[self.active.pk])])
                self.assertEqual(self.sprint_data(expanded, self.active)['more_url'], '')
                again = self.page(expanded['backlog_more_url'], scoped=scoped)
                self.assertEqual(again['backlog_loaded_count'], 60)
                self.assertEqual(self.sprint_data(again, self.active)['loaded_count'], 21)

    def test_filters_apply_before_group_counts_and_limits(self):
        data = self.page(q='Praca', priority='high', assignee='me', sort='title_desc')
        expected = [task.pk for index, task in reversed(list(enumerate(self.tasks[None]))) if index % 6 == 0]
        self.assertEqual(data['backlog_totals']['total'], 21)
        self.assertEqual(self.group_ids(data), expected[:20])
        expanded = self.page(data['backlog_more_url'])
        self.assertEqual(self.group_ids(expanded), expected)
        self.assertEqual(self.sprint_data(expanded, self.active)['loaded_count'], 4)
        self.assertEqual(expanded['backlog_more_url'], '')
        empty = self.page(q='Nieistniejący wynik', backlog_limit_backlog=1000)
        self.assertEqual(empty['items'], [])
        self.assertEqual(empty['backlog_loaded_count'], 0)
        self.assertEqual(empty['backlog_more_url'], '')
        self.assertEqual(empty['backlog_totals']['total'], 0)

    def test_malformed_and_huge_limits_are_bounded_by_visible_group_total(self):
        for value, expected in [('', 20), ('bad', 20), ('-10', 20), ('1.5', 20), ('١٠٠', 20),
                                ('0', 20), ('19', 20), ('40', 40), ('00040', 40), ('9' * 5000, 121)]:
            with self.subTest(value=value[:20]):
                data = self.page(backlog_limit_backlog=value, page=2)
                self.assertEqual(data['backlog_loaded_count'], expected)
                self.assertEqual(len(self.group_ids(data, self.active)), 20)
        data = self.page(**{f'backlog_limit_sprint_{self.active.pk}': '9' * 5000})
        self.assertEqual(self.sprint_data(data, self.active)['loaded_count'], 21)
        self.assertEqual(data['backlog_loaded_count'], 20)

    def test_kanban_does_not_load_board_items(self):
        self.space.template = 'kanban'
        self.space.save(update_fields=['template'])
        WorkItem.objects.filter(task=self.tasks[None][0]).update(in_backlog=False)
        data = self.page(backlog_limit_backlog=9999)
        self.assertEqual(data['backlog_totals']['total'], 120)
        self.assertEqual(self.group_ids(data), [task.pk for task in self.tasks[None][1:]])
        self.assertEqual(len(data['items']), 120)

    def test_revoked_membership_cannot_expand_groups(self):
        SpaceMembership.objects.filter(space=self.space, user=self.member).delete()
        for scoped in (True, False):
            api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
            response = self.client.get(api, {'url': self.url(scoped, backlog_limit_backlog=9999)}, follow=True)
            self.assertEqual(response.status_code, 404)

    def test_sort_and_filter_links_reset_both_sets_of_limits(self):
        response = self.client.get(self.url(backlog_limit_backlog=60, list_limit_new=60,
                                           **{f'backlog_limit_sprint_{self.active.pk}': 21},
                                           sort='title_desc', priority='high', q='Praca'))
        for label in ('Tytuł · rosnąco', 'Wyczyść'):
            match = re.search(r'href="([^"]+)">' + re.escape(label) + r'</a>', response.content.decode())
            self.assertIsNotNone(match)
            params = parse_qs(urlsplit(unescape(match.group(1))).query)
            self.assertFalse(any(key.startswith(('backlog_limit_', 'list_limit_')) for key in params))
            self.assertEqual(params['q'], ['Praca'])

    def test_create_and_planning_urls_keep_loaded_groups_without_stale_page(self):
        data = self.page(backlog_limit_backlog=40, page=2, q='Praca',
                         **{f'backlog_limit_sprint_{self.active.pk}': 21})
        expected = {'view': ['backlog'], 'backlog_limit_backlog': ['40'], 'q': ['Praca'],
                    f'backlog_limit_sprint_{self.active.pk}': ['21']}
        for key in ('create_item_url', 'backlog_create_url', 'bulk_plan_url', 'sprint_create_url'):
            self.assertEqual(parse_qs(urlsplit(data[key]).query), expected)
