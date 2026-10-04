import importlib
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.db.models.query import QuerySet
from django.test import RequestFactory, TestCase, TransactionTestCase

from kanban.models import Kanban
from tasks.models import Task
from workplaces.models import WorkplaceMembership, create_workplace_for_user


MODULES = [('tasks', Task)]


class StatusUpdateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='status-owner', email='status-owner@example.test')
        cls.member = users.objects.create_user(username='status-member', email='status-member@example.test')
        cls.team = create_workplace_for_user(cls.owner, 'Status team')
        WorkplaceMembership.objects.create(workplace=cls.team, user=cls.member, role='member')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.team.pk
        session.save()

    def post_status(self, app, item, status, scoped=True):
        prefix = f'/workplaces/{self.team.slug}' if scoped else ''
        return self.client.post(f'{prefix}/{app}/update/{item.task_id}/',
                                json.dumps({'task_pk': item.pk, 'status': status}), content_type='application/json')

    def test_status_save_preserves_other_fields_written_since_instance_was_loaded(self):
        for app, model in MODULES:
            with self.subTest(app=app):
                stale = model.objects.create(user=self.owner, workplace=self.team, title='Old title')
                current = model.objects.get(pk=stale.pk)
                current.title = 'Saved by colleague'
                current.description = 'New description'
                current.priority = 'high'
                current.save()
                view = importlib.import_module(f'{app}.views.tasks')
                self.assertTrue(view._set_task_status(stale, 'closed'))
                stale.refresh_from_db()
                self.assertEqual((stale.title, stale.description, stale.priority),
                                 ('Saved by colleague', 'New description', 'high'))
                self.assertTrue(stale.is_completed)
                self.assertIsNotNone(stale.completion_date)

    def test_repeated_close_preserves_completion_and_records_only_real_changes(self):
        for app, model in MODULES:
            for scoped in [False, True]:
                with self.subTest(app=app, scoped=scoped):
                    item = model.objects.create(user=self.owner, workplace=self.team, title='Status target')
                    self.assertEqual(self.post_status(app, item, 'closed', scoped).status_code, 200)
                    item.refresh_from_db()
                    closed_at = item.completion_date
                    self.assertIsNotNone(closed_at)
                    self.assertEqual(self.post_status(app, item, 'closed', scoped).status_code, 200)
                    item.refresh_from_db()
                    self.assertEqual(item.completion_date, closed_at)
                    activity = item.activities.get(action='status_changed')
                    self.assertEqual(activity.actor_id, self.member.pk)
                    self.assertEqual(self.post_status(app, item, 'reopened', scoped).status_code, 200)
                    item.refresh_from_db()
                    self.assertFalse(item.is_completed)
                    self.assertIsNone(item.completion_date)
                    self.assertEqual(item.activities.filter(action='status_changed').count(), 2)

    def test_status_and_history_are_rolled_back_together(self):
        for app, model in MODULES:
            with self.subTest(app=app):
                item = model.objects.create(user=self.owner, workplace=self.team, title='Rollback target')
                with patch(f'{app}.views.tasks._record_task_activity', side_effect=RuntimeError('History unavailable')):
                    with self.assertRaises(RuntimeError):
                        self.post_status(app, item, 'closed')
                item.refresh_from_db()
                self.assertEqual(item.status, 'new')
                self.assertFalse(item.is_completed)
                self.assertIsNone(item.completion_date)
                self.assertFalse(item.activities.filter(action='status_changed').exists())


class ConcurrentStatusUpdateTests(TransactionTestCase):
    def test_simultaneous_close_requests_preserve_completion_and_single_history_entry(self):
        owner = get_user_model().objects.create_user(username='concurrent-status', email='concurrent-status@example.test')
        team = create_workplace_for_user(owner, 'Concurrent status')
        for app, model in MODULES:
            with self.subTest(app=app):
                item = model.objects.create(user=owner, workplace=team, title='Concurrent target')
                view = importlib.import_module(f'{app}.views.tasks')
                first_read, release, second_started = Event(), Event(), Event()
                original_get = QuerySet.get

                def pause_first_read(queryset, *args, **kwargs):
                    result = original_get(queryset, *args, **kwargs)
                    if queryset.model is model and kwargs.get('pk') == item.pk and not first_read.is_set():
                        first_read.set()
                        if not release.wait(10):
                            raise TimeoutError('Status request was not released')
                    return result

                def close_item(index):
                    close_old_connections()
                    request = RequestFactory().post(f'/{app}/update/{item.task_id}/',
                        json.dumps({'task_pk': item.pk, 'status': 'closed'}), content_type='application/json')
                    request.user, request.workplace = owner, team
                    if index == 2:
                        second_started.set()
                    try:
                        return view.update_task_status(request, item.task_id).status_code
                    finally:
                        close_old_connections()

                with patch.object(QuerySet, 'get', pause_first_read), ThreadPoolExecutor(max_workers=2) as executor:
                    first = executor.submit(close_item, 1)
                    try:
                        self.assertTrue(first_read.wait(10))
                        second = executor.submit(close_item, 2)
                        self.assertTrue(second_started.wait(10))
                        # The second request must wait for the first transaction.
                        with self.assertRaises(TimeoutError):
                            second.result(timeout=0.3)
                    finally:
                        release.set()
                    self.assertEqual([first.result(timeout=10), second.result(timeout=10)], [200, 200])
                item.refresh_from_db()
                self.assertTrue(item.is_completed)
                self.assertIsNotNone(item.completion_date)
                self.assertEqual(item.activities.filter(action='status_changed').count(), 1)
