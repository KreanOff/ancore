import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import IntegrityError, close_old_connections, transaction
from django.test import TestCase, TransactionTestCase

from dashboard.views import _dashboard_notifications
from planner.models import CalendarEvent
from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class ConcurrentSpaceTaskNumberTests(TransactionTestCase):
    def test_simultaneous_creation_allocates_distinct_stable_keys(self):
        from spaces.models import SpaceTask
        from spaces.testing import make_space

        owner = get_user_model().objects.create_user(username='number-owner', email='numbers@example.test')
        workplace = create_workplace_for_user(owner, 'Numeracja')
        space = make_space(user=owner, workplace=workplace, name='Praca', key='KEY')
        barrier = Barrier(2)

        def create(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                task = SpaceTask.objects.create(space_id=space.pk, created_by_id=owner.pk, title=f'Zadanie {index}')
                return task.work_item.key
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            keys = list(pool.map(create, (1, 2)))
        self.assertEqual(set(keys), {'KEY-1', 'KEY-2'})
        space.refresh_from_db()
        self.assertEqual(space.next_number, 3)

    def test_database_rejects_duplicate_numbers_within_a_space(self):
        from spaces.models import WorkItem
        from spaces.testing import make_task

        owner = get_user_model().objects.create_user(username='number-constraint', email='constraint@example.test')
        workplace = create_workplace_for_user(owner, 'Ograniczenia')
        first = make_task(user=owner, workplace=workplace, title='Pierwsze')
        second = make_task(user=owner, workplace=workplace, space=first.space, title='Drugie')
        with self.assertRaises(IntegrityError), transaction.atomic():
            WorkItem.objects.filter(task=second).update(number=first.work_item.number)
        elsewhere = make_task(user=owner, workplace=workplace, title='Inna przestrzeń')
        self.assertEqual(elsewhere.work_item.number, first.work_item.number)


class TaskIdentityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='identity-owner', email='identity@example.test')
        cls.other = get_user_model().objects.create_user(username='identity-other', email='other@example.test')
        cls.first = create_workplace_for_user(cls.user, 'Workspace A')
        cls.second = create_workplace_for_user(cls.user, 'Workspace B')

    def setUp(self):
        self.client.force_login(self.user)

    def post_json(self, url, data):
        return self.client.post(url, json.dumps(data), content_type='application/json')

    def test_calendar_urls_preserve_workspace_for_all_operations(self):
        page = self.client.get(scoped_workplace_app_path(self.first, 'calendar'))
        urls = page.context['calendar_config']['urls']
        for url in urls.values():
            self.assertTrue(url.startswith(scoped_workplace_app_path(self.first, 'calendar')))
        self.client.get(scoped_workplace_app_path(self.second, 'calendar'))
        fields = {'title': 'Event A', 'start': '2026-09-19T10:00', 'end': '2026-09-19T11:00', 'color': 'red'}
        self.assertEqual(self.client.post(urls['create'], fields).status_code, 200)
        event = CalendarEvent.objects.get(title='Event A')
        self.assertEqual(event.workplace_id, self.first.pk)
        self.client.get(scoped_workplace_app_path(self.second, 'calendar'))
        self.assertEqual(self.client.post(urls['update'].replace('__ID__', str(event.pk)), {**fields, 'title': 'Updated'}).status_code, 200)
        self.client.get(scoped_workplace_app_path(self.second, 'calendar'))
        self.assertEqual(self.client.post(urls['delete'].replace('__ID__', str(event.pk))).status_code, 200)
        self.assertFalse(CalendarEvent.objects.exists())


class SpaceTaskIdentityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from spaces.testing import make_space
        cls.user = get_user_model().objects.create_user(username='space-identity', email='space-identity@example.test')
        cls.first = create_workplace_for_user(cls.user, 'First')
        cls.second = create_workplace_for_user(cls.user, 'Second')
        cls.space = make_space(user=cls.user, workplace=cls.first, name='Stable keys', key='STABLE')
        cls.other_space = make_space(user=cls.user, workplace=cls.second, name='Elsewhere')

    def setUp(self):
        self.client.force_login(self.user)

    def task(self, title, space=None, **values):
        from spaces.models import SpaceTask
        return SpaceTask.objects.create(space=space or self.space, created_by=self.user, title=title, **values)

    def url(self, task, suffix='', workplace=None):
        return scoped_workplace_app_path(workplace or task.space.workplace, 'space',
            f'{task.space.slug}/tasks/{task.work_item.key}/{suffix}')

    def test_deletion_never_reassigns_surviving_or_new_task_keys(self):
        first, target, later = [self.task(title) for title in ('First', 'Target', 'Later')]
        key, url = target.work_item.key, self.url(target)
        first.delete()
        self.assertEqual(self.client.get(url).context['task'].pk, target.pk)
        self.assertEqual(target.work_item.key, key)
        target.delete()
        newest = self.task('Newest')
        self.assertGreater(newest.work_item.number, later.work_item.number)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_url_identity_overrides_forged_posted_pk(self):
        target, other = self.task('Target'), self.task('Other')
        response = self.client.post(self.url(target, 'action/'),
            {'action': 'status', 'status': 'closed', 'task_pk': other.pk}, HTTP_X_WORK_ACTION='true')
        self.assertEqual(response.status_code, 200)
        target.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(target.is_completed)
        self.assertEqual(other.status, 'new')

    def test_scoped_actions_keep_original_workspace_after_another_tab_is_opened(self):
        target = self.task('Target')
        elsewhere = self.task('Elsewhere', space=self.other_space)
        self.client.get(scoped_workplace_app_path(self.second, 'calendar'))
        response = self.client.post(self.url(target, 'action/'), {'action': 'status', 'status': 'closed'}, HTTP_X_WORK_ACTION='true')
        self.assertEqual(response.status_code, 200)
        target.refresh_from_db()
        elsewhere.refresh_from_db()
        self.assertTrue(target.is_completed)
        self.assertEqual(elsewhere.status, 'new')
        self.assertEqual(self.client.post(self.url(elsewhere, 'action/', workplace=self.first), {'action': 'status', 'status': 'closed'}).status_code, 404)

    def test_base_and_scoped_links_use_the_same_current_task(self):
        target = self.task('Target')
        self.client.get(scoped_workplace_app_path(self.first, 'calendar'))
        for url in [self.url(target), f'/space/{self.space.slug}/tasks/{target.work_item.key}/']:
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['task'].pk, target.pk)
                self.assertContains(response, target.work_item.key)

    def test_notifications_link_to_each_task_workspace_and_stable_key(self):
        expected = {}
        for space in (self.space, self.other_space):
            task = self.task(space.name, space=space)
            task.activities.create(actor=self.user, kind='comment', action='commented', message='Komentarz')
            expected[task.title] = task
        notifications = _dashboard_notifications(self.user)
        self.assertEqual(len(notifications), 2)
        for notification in notifications:
            task = expected[notification['title']]
            self.assertEqual(notification['url'], self.url(task) + '?view=list')
            self.client.get(scoped_workplace_app_path(self.first, 'calendar'))
            response = self.client.get(notification['url'])
            self.assertEqual(response.context['task'].pk, task.pk)
            self.assertEqual(response.context['task'].space.workplace_id, task.space.workplace_id)

    def test_deletion_cascades_descendants_and_preserves_other_workspace(self):
        from spaces.models import SpaceTask
        root = self.task('Root')
        child = self.task('Child', parent=root)
        elsewhere = self.task('Elsewhere', space=self.other_space)
        response = self.client.post(self.url(root), {'action': 'delete', 'task_pk': elsewhere.pk})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SpaceTask.objects.filter(pk__in=[root.pk, child.pk]).exists())
        self.assertTrue(SpaceTask.objects.filter(pk=elsewhere.pk).exists())
