import base64
import json
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import InMemoryStorage
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from dashboard.recent import RECENT_SESSION_KEY
from dashboard.views import GLOBAL_SEARCH_GROUP_LIMIT, GLOBAL_SEARCH_RECENT_LIMIT
from spaces.avatars import space_avatar
from spaces.models import Space, SpaceTask, SpaceTaskActivity
from spaces.testing import make_space, make_task
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from workplaces.templatetags.workplace_avatar import workplace_avatar


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


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
        cls.space = make_space(user=cls.owner, workplace=cls.team, name='Praca')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.team.pk
        session.save()

    def search(self, query, *, scoped=False):
        if scoped:
            response = self.client.get(
                scoped_workplace_app_path(self.team, 'api', 'v1/page/'),
                {'url': reverse('global_search') + '?' + urlencode({'q': query})},
            )
        else:
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
        make_task(user=self.owner, workplace=self.team, space=self.space, title='Search shared task')
        self.membership.delete()
        response = self.search('Search')
        titles = [row['title'] for group in response.json()['groups'] for row in group['results']]
        self.assertIn(self.personal.name, titles)
        self.assertNotIn(self.team.name, titles)
        self.assertNotIn(self.private.name, titles)
        self.assertNotIn('Search shared task', titles)

    def test_task_and_subtask_links_survive_renumbering_and_never_retarget_deleted_records(self):
        for model, group_key in [(SpaceTask, 'space_tasks')]:
            for is_child in (False, True):
                with self.subTest(model=model.__name__, child=is_child):
                    first = make_task(user=self.owner, workplace=self.team, space=self.space, title='Earlier item')
                    parent = make_task(user=self.owner, workplace=self.team, space=self.space, title='Parent') if is_child else None
                    selected = make_task(user=self.owner, workplace=self.team, space=self.space, parent=parent,
                                                    title=f'Search target {model.__name__} {is_child}')
                    make_task(user=self.owner, workplace=self.team, space=self.space, parent=parent, title='Later item')
                    group = next(group for group in self.search(selected.title).json()['groups'] if group['key'] == group_key)
                    link = group['results'][0]['url']
                    self.assertIn(f'/tasks/{selected.work_item.key}/', link)
                    first.delete()
                    response = self.client.get(link, follow=True)
                    self.assertEqual(response.context['task'].pk, parent.pk if is_child else selected.pk)
                    if is_child:
                        self.assertEqual(response.context['task_tab'], 'subtasks')
                        self.assertContains(response, selected.title)
                    selected.delete()
                    self.assertEqual(self.client.get(link).status_code, 404)

    def test_unicode_and_oversized_numeric_queries_are_safe(self):
        item = make_task(user=self.owner, workplace=self.team, space=self.space, title='Area ²²')
        for query in ['²²', '①①', '9' * 120, '٠١']:
            with self.subTest(query=query):
                response = self.search(query)
                if query == '²²':
                    self.assertIn(item.title, [row['title'] for group in response.json()['groups'] for row in group['results']])

    def test_each_current_group_is_limited_in_sql_and_tasks_keep_newest_order(self):
        for index in range(GLOBAL_SEARCH_GROUP_LIMIT + 3):
            make_task(user=self.owner, workplace=self.team, space=self.space, title=f'Limit probe {index}')
            make_space(user=self.owner, workplace=self.team, name=f'Limit probe {index}')
        newest = make_task(user=self.owner, workplace=self.team, space=self.space, title='Limit probe newest')
        with CaptureQueriesContext(connection) as queries:
            payload = self.search('Limit probe').json()
        self.assertTrue(payload['truncated'])
        self.assertEqual(payload['total'], 2 * GLOBAL_SEARCH_GROUP_LIMIT)
        for key in ['space_tasks', 'spaces']:
            group = next(group for group in payload['groups'] if group['key'] == key)
            self.assertEqual(len(group['results']), GLOBAL_SEARCH_GROUP_LIMIT)
            self.assertTrue(group['has_more'])
        tasks = next(group for group in payload['groups'] if group['key'] == 'space_tasks')
        self.assertEqual(tasks['results'][0]['title'], newest.title)
        for table in ['spaces_workitem', 'spaces_space']:
            bounded = [q['sql'] for q in queries if f'FROM "{table}"' in q['sql'] and f'LIMIT {GLOBAL_SEARCH_GROUP_LIMIT + 1}' in q['sql']]
            self.assertTrue(bounded, table)

    def test_exact_task_key_precedes_newer_matches_beyond_limit_in_base_and_scoped_search(self):
        target = make_task(user=self.owner, workplace=self.team, space=self.space, title='Original key target')
        query = target.work_item.key.lower()
        title_match = make_task(user=self.owner, workplace=self.team, space=self.space, title=query.upper())
        for index in range(GLOBAL_SEARCH_GROUP_LIMIT + 3):
            make_task(user=self.owner, workplace=self.team, space=self.space,
                      title=f'Follow-up {index}: {query}', description=query)
        private = make_space(user=self.owner, workplace=self.team, name='Private match',
                             visibility='private', private_owner=self.owner)
        hidden = make_task(user=self.owner, workplace=self.team, space=private, title=query)
        foreign = make_task(user=self.owner, workplace=self.private, title=query)

        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                with CaptureQueriesContext(connection) as queries:
                    payload = self.search(query, scoped=scoped).json()
                group = next(group for group in payload['groups'] if group['key'] == 'space_tasks')
                self.assertEqual([row['title'] for row in group['results'][:2]], [target.title, title_match.title])
                self.assertEqual(len(group['results']), GLOBAL_SEARCH_GROUP_LIMIT)
                self.assertTrue(group['has_more'])
                self.assertTrue(payload['truncated'])
                urls = [row['url'] for row in group['results']]
                self.assertTrue(all(f'/workplaces/{self.team.slug}/' in url for url in urls))
                self.assertFalse(any(f'/space/{task.space.slug}/' in url for task in (hidden, foreign) for url in urls))
                self.assertTrue(any(
                    'FROM "spaces_workitem"' in query['sql'] and f'LIMIT {GLOBAL_SEARCH_GROUP_LIMIT + 1}' in query['sql']
                    for query in queries
                ))

    def test_task_title_rank_precedes_description_and_comments_with_newest_tiebreaker(self):
        def task(title, **values):
            return make_task(user=self.owner, workplace=self.team, space=self.space, title=title, **values)

        exact = task('Rank task')
        prefix_older = task('Rank task older')
        prefix_newer = task('Rank task newer')
        fragment = task('Before rank task')
        description = task('Description match', description='Rank task')
        comment = task('Comment match')
        SpaceTaskActivity.objects.create(task=comment, actor=self.owner, kind='comment', message='Rank task')
        expected = [exact, prefix_newer, prefix_older, fragment, comment, description]

        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                payload = self.search('rank task', scoped=scoped).json()
                group = next(group for group in payload['groups'] if group['key'] == 'space_tasks')
                self.assertEqual([row['title'] for row in group['results']], [item.title for item in expected])

    def test_spaces_rank_key_name_prefix_fragment_and_description_with_name_tiebreaker(self):
        def space(name, key, **values):
            return make_space(user=self.owner, workplace=self.team, name=name, key=key, **values)

        exact_key = space('Z Exact code', 'RANK')
        exact_name = space('RaNk', 'EXACTNAME')
        prefix_name_b = space('Rank Beta', 'PREFIXB')
        prefix_name_a = space('Rank Alpha', 'PREFIXA')
        prefix_key = space('A Key prefix', 'RANKX')
        fragment_name = space('Before rank', 'FRAGMENT')
        fragment_key = space('A Key fragment', 'XRANKX')
        description = space('A Description', 'DESCRIPTION', description='rank')
        expected = [exact_key, exact_name, prefix_key, prefix_name_a, prefix_name_b,
                    fragment_key, fragment_name, description]

        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                payload = self.search('rank', scoped=scoped).json()
                group = next(group for group in payload['groups'] if group['key'] == 'spaces')
                self.assertEqual([row['title'] for row in group['results']], [item.name for item in expected])

    def test_exact_limit_is_not_reported_as_truncated(self):
        for index in range(GLOBAL_SEARCH_GROUP_LIMIT):
            make_task(user=self.owner, workplace=self.team, space=self.space, title=f'Boundary probe {index}')
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

    def recent(self, *, scoped=False):
        if scoped:
            response = self.client.get(
                scoped_workplace_app_path(self.team, 'api', 'v1/page/'),
                {'url': reverse('global_search') + '?recent=1'},
            )
        else:
            response = self.client.get(reverse('global_search'), {'recent': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'no-store')
        return response.json()

    def test_space_search_and_recent_use_presets_and_controlled_photos_with_current_access(self):
        with patch.object(Space._meta.get_field('avatar_photo'), 'storage', InMemoryStorage()):
            self.space.name, self.space.avatar = 'Avatar preset', 'rocket'
            self.space.save(update_fields=['name', 'avatar'])
            photo = make_space(user=self.owner, workplace=self.team, name='Avatar photo',
                               avatar_photo=ContentFile(PNG, name='visible.png'))
            hidden = make_space(user=self.owner, workplace=self.team, name='Avatar private',
                                visibility='private', private_owner=self.owner,
                                avatar_photo=ContentFile(PNG, name='private.png'))
            foreign = make_space(user=self.owner, workplace=self.private, name='Avatar foreign',
                                 avatar_photo=ContentFile(PNG, name='foreign.png'))
            self.remember(self.space, photo, hidden, foreign)
            photo_url = space_avatar(photo)['photo_url']
            self.assertEqual(photo_url, scoped_workplace_app_path(self.team, 'space', f'{photo.slug}/avatar/photo/'))
            response = self.client.get(photo_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            self.assertEqual(b''.join(response.streaming_content), PNG)

            for scoped in (False, True):
                with self.subTest(scoped=scoped):
                    search = self.search('Avatar', scoped=scoped).json()
                    recent = self.recent(scoped=scoped)
                    for payload in (search, recent):
                        rows = {row['title']: row for group in payload['groups'] for row in group['results']}
                        self.assertEqual(set(rows), {self.space.name, photo.name})
                        self.assertEqual(rows[self.space.name]['avatar']['preset_class'], 'space-avatar-art--rocket')
                        self.assertEqual(rows[photo.name]['avatar']['photo_url'], photo_url)
                        serialized = json.dumps(payload)
                        self.assertNotIn(photo.avatar_photo.name, serialized)
                        for excluded in (hidden, foreign):
                            self.assertNotIn(space_avatar(excluded)['photo_url'], serialized)
                            self.assertNotIn(excluded.avatar_photo.name, serialized)

            photo.visibility, photo.private_owner = 'private', self.owner
            photo.save(update_fields=['visibility', 'private_owner'])
            self.assertEqual(self.client.get(photo_url).status_code, 404)
            for payload in (self.search('Avatar', scoped=True).json(), self.recent(scoped=True)):
                self.assertNotIn(photo_url, json.dumps(payload))
                self.assertNotIn(photo.name, json.dumps(payload))

    def test_workspace_search_uses_current_preset_and_photo_without_private_workspace_avatar(self):
        self.team.avatar = 'leaf'
        self.team.save(update_fields=['avatar'])
        self.personal.workplace_photo = 'workplace_photos/search-personal.png'
        self.personal.save(update_fields=['workplace_photo'])
        self.private.workplace_photo = 'workplace_photos/search-private.png'
        self.private.save(update_fields=['workplace_photo'])

        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                response = self.search('Search', scoped=scoped)
                group = next(group for group in response.json()['groups'] if group['key'] == 'workplaces')
                rows = {row['title']: row for row in group['results']}
                self.assertEqual(rows[self.team.name]['avatar'], workplace_avatar(self.team))
                self.assertEqual(rows[self.personal.name]['avatar'], workplace_avatar(self.personal))
                self.assertNotContains(response, self.private.workplace_photo.name)
                self.assertNotContains(response, workplace_avatar(self.private)['photo_url'])

    def test_search_and_recent_use_task_type_icons_and_distinguish_subtasks(self):
        expected = {}
        tasks = []
        for work_type, icon in [('task', 'square-check'), ('bug', 'circle-alert'), ('story', 'book-open'),
                                ('epic', 'zap'), ('custom-type', 'shapes')]:
            task = make_task(user=self.owner, workplace=self.team, space=self.space,
                             title=f'Icon example {work_type}', assignee=self.member)
            item = task.work_item
            item.work_type = work_type
            item.save(update_fields=['work_type'])
            tasks.append(task)
            expected[task.title] = (icon, 'Zadanie')
        child = make_task(user=self.owner, workplace=self.team, space=self.space,
                          parent=tasks[0], title='Icon example child')
        expected[child.title] = (child.work_item.type_icon, 'Podzadanie')
        self.remember(*tasks, child)

        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                for payload in (self.search('Icon example', scoped=scoped).json(), self.recent(scoped=scoped)):
                    rows = [row for group in payload['groups'] for row in group['results']]
                    self.assertEqual(len(rows), len(expected))
                    for row in rows:
                        self.assertEqual((row['icon'], row['type']), expected[row['title']])
                        self.assertNotIn('avatar', row)

    def test_recent_is_explicit_empty_and_requires_login(self):
        self.assertEqual(self.recent()['groups'], [])
        task = make_task(user=self.owner, workplace=self.team, space=self.space, title='Recently opened')
        self.remember(task)
        self.assertEqual(self.search('').json()['groups'], [])
        self.assertEqual(self.search('R').json()['groups'], [])
        self.client.logout()
        self.assertEqual(self.client.get(reverse('global_search'), {'recent': '1'}).status_code, 302)

    def test_recent_preserves_order_limits_results_and_resolves_current_titles_and_numbers(self):
        tasks = [make_task(user=self.owner, workplace=self.team, space=self.space, title=f'Recent {index}')
                 for index in range(GLOBAL_SEARCH_RECENT_LIMIT + 2)]
        self.remember(*reversed(tasks))
        tasks[-1].title = 'Renamed recently'
        tasks[-1].save()
        tasks[0].delete()
        payload = self.recent()
        self.assertEqual(payload['total'], GLOBAL_SEARCH_RECENT_LIMIT)
        rows = payload['groups'][0]['results']
        self.assertEqual([row['title'] for row in rows], [task.title for task in reversed(tasks[-GLOBAL_SEARCH_RECENT_LIMIT:])])
        self.assertIn(f'/tasks/{tasks[-1].work_item.key}/', rows[0]['url'])
        self.assertEqual(self.client.get(rows[0]['url']).context['task'].pk, tasks[-1].pk)

    def test_recent_rechecks_parent_privacy_deletion_and_workspace_membership(self):
        task = make_task(user=self.owner, workplace=self.team, space=self.space, title='Recent task')
        parent = make_task(user=self.owner, workplace=self.team, space=self.space, title='Private parent', visibility='private', private_owner=self.owner)
        child = make_task(user=self.owner, workplace=self.team, space=self.space, parent=parent, title='Hidden child')
        self.remember(self.space, task, child)
        self.assertEqual(self.recent()['total'], 2)
        self.space.visibility, self.space.private_owner = 'private', self.owner
        self.space.save()
        self.assertEqual(self.recent()['groups'], [])
        task.delete()
        self.assertEqual(self.recent()['total'], 0)
        self.membership.delete()
        self.assertEqual(self.recent()['total'], 0)

    def test_recent_never_trusts_session_ids_as_workspace_or_account_access(self):
        visible = make_task(user=self.owner, workplace=self.team, space=self.space, title='Visible')
        foreign = make_task(user=self.owner, workplace=self.private, title='Foreign Workspace')
        other_owner = make_task(user=self.member, workplace=self.team, title='Foreign owner')
        self.remember(visible, foreign, other_owner)
        self.assertEqual([row['title'] for row in self.recent()['groups'][0]['results']], [visible.title])
        session = self.client.session
        session[RECENT_SESSION_KEY][0]['identity'][0] = self.owner.pk
        session.save()
        self.assertEqual(self.recent()['groups'], [])


    def test_recent_records_current_space_views_and_rechecks_revoked_access(self):
        project = make_space(user=self.owner, workplace=self.team, name='Opened space')
        for url in (f'/space/{project.slug}/', f'/workplaces/{self.team.slug}/space/{project.slug}/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
                rows = self.recent()['groups'][0]['results']
                self.assertEqual(rows[0]['title'], project.name)
                self.assertEqual(rows[0]['url'], f'/workplaces/{self.team.slug}/space/{project.slug}/')
        self.assertEqual(self.recent()['total'], 1)
        project.visibility, project.private_owner = 'private', self.owner
        project.save()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.recent()['total'], 0)

    def test_recent_records_real_base_and_scoped_visits_with_subtask_links(self):
        parent = make_task(user=self.owner, workplace=self.team, space=self.space, title='Parent recent')
        child = make_task(user=self.owner, workplace=self.team, space=self.space, parent=parent, title='Child recent')
        for prefix in ('/space/', f'/workplaces/{self.team.slug}/space/'):
            with self.subTest(prefix=prefix):
                response = self.client.get(f'{prefix}{child.space.slug}/tasks/{child.work_item.key}/')
                self.assertEqual(response.status_code, 302)
                row = self.recent()['groups'][0]['results'][0]
                self.assertEqual(row['title'], child.title)
                self.assertEqual(row['type'], 'Podzadanie')
                self.assertIn(f'/tasks/{child.work_item.key}/', row['url'])
                self.assertEqual(self.client.get(row['url'], follow=True).context['task'].pk, parent.pk)
