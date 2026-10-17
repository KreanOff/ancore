"""Status transactions and concurrency for current Space tasks."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.db.models.query import QuerySet
from django.test import RequestFactory, TestCase, TransactionTestCase

from spaces import services, views
from spaces.models import SpaceTask
from spaces.testing import make_task
from workplaces.models import WorkplaceMembership, create_workplace_for_user


class StatusUpdateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='status-owner', email='status-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='status-member', email='status-member@example.test')
        cls.team = create_workplace_for_user(cls.owner, 'Status team')
        WorkplaceMembership.objects.create(workplace=cls.team, user=cls.member)

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.team.pk
        session.save()

    def post_status(self, task, status, scoped=True):
        prefix = f'/workplaces/{self.team.slug}' if scoped else ''
        return self.client.post(f'{prefix}/space/{task.space.slug}/tasks/{task.work_item.key}/action/',
                                {'action': 'status', 'status': status}, HTTP_X_WORK_ACTION='true')

    def test_status_save_preserves_other_fields_written_since_instance_was_loaded(self):
        stale = make_task(user=self.owner, workplace=self.team, title='Old title')
        item = stale.work_item
        current = SpaceTask.objects.get(pk=stale.pk)
        current.title, current.description, current.priority = 'Saved by colleague', 'New description', 'high'
        current.save()
        services.set_status(SimpleNamespace(user=self.member, workplace=self.team), item, 'closed')
        stale.refresh_from_db()
        self.assertEqual((stale.title, stale.description, stale.priority), ('Saved by colleague', 'New description', 'high'))
        self.assertTrue(stale.is_completed)
        self.assertIsNotNone(stale.completion_date)

    def test_repeated_close_preserves_completion_and_records_only_real_changes(self):
        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                task = make_task(user=self.owner, workplace=self.team, title='Status target')
                self.assertEqual(self.post_status(task, 'closed', scoped).status_code, 200)
                task.refresh_from_db()
                closed_at = task.completion_date
                self.assertIsNotNone(closed_at)
                self.assertEqual(self.post_status(task, 'closed', scoped).status_code, 200)
                task.refresh_from_db()
                self.assertEqual(task.completion_date, closed_at)
                self.assertEqual(task.activities.get(action='status_changed').actor, self.member)
                self.assertEqual(self.post_status(task, 'reopened', scoped).status_code, 200)
                task.refresh_from_db()
                self.assertFalse(task.is_completed)
                self.assertIsNone(task.completion_date)
                self.assertEqual(task.activities.filter(action='status_changed').count(), 2)

    def test_status_and_history_are_rolled_back_together(self):
        task = make_task(user=self.owner, workplace=self.team, title='Rollback target')
        with patch('spaces.services.record', side_effect=RuntimeError('History unavailable')):
            with self.assertRaises(RuntimeError):
                self.post_status(task, 'closed')
        task.refresh_from_db()
        task.work_item.refresh_from_db()
        self.assertEqual(task.work_item.status, 'new')
        self.assertEqual(task.status, 'new')
        self.assertFalse(task.is_completed)
        self.assertIsNone(task.completion_date)
        self.assertFalse(task.activities.exclude(action='created').exists())


class ConcurrentStatusUpdateTests(TransactionTestCase):
    def test_simultaneous_close_requests_preserve_completion_and_single_history_entry(self):
        owner = get_user_model().objects.create_user(username='concurrent-status', email='concurrent-status@example.test')
        team = create_workplace_for_user(owner, 'Concurrent status')
        task = make_task(user=owner, workplace=team, title='Concurrent target')
        key, slug = task.work_item.key, task.space.slug
        first_read, release, second_started = Event(), Event(), Event()
        original_get = QuerySet.get

        def pause_first_read(queryset, *args, **kwargs):
            result = original_get(queryset, *args, **kwargs)
            if queryset.model is SpaceTask and kwargs.get('pk') == task.pk and not first_read.is_set():
                first_read.set()
                if not release.wait(10):
                    raise TimeoutError('Status request was not released')
            return result

        def close_item(index):
            close_old_connections()
            request = RequestFactory().post(f'/space/{slug}/tasks/{key}/action/',
                {'action': 'status', 'status': 'closed'}, HTTP_X_WORK_ACTION='true')
            request.user, request.workplace = owner, team
            if index == 2:
                second_started.set()
            try:
                return views.item_action(request, space_pk=slug, key=key).status_code
            finally:
                close_old_connections()

        with patch.object(QuerySet, 'get', pause_first_read), ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(close_item, 1)
            try:
                self.assertTrue(first_read.wait(10))
                second = executor.submit(close_item, 2)
                self.assertTrue(second_started.wait(10))
                with self.assertRaises(TimeoutError):
                    second.result(timeout=0.3)
            finally:
                release.set()
            self.assertEqual([first.result(timeout=10), second.result(timeout=10)], [200, 200])
        task.refresh_from_db()
        self.assertTrue(task.is_completed)
        self.assertIsNotNone(task.completion_date)
        self.assertEqual(task.activities.filter(action='status_changed').count(), 1)
