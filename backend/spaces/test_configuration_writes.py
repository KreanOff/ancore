"""Workflow edits must serialize with tasks in every space using the configuration."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from threading import Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import OperationalError, close_old_connections, connection, transaction
from django.db.models.query import QuerySet
from django.test import RequestFactory, TransactionTestCase

from workplaces.models import Workplace, WorkplaceMembership, create_workplace_for_user
from . import task_views, views
from .models import SpaceTask
from .services import set_status
from .testing import make_space


class ConfigurationWriteTests(TransactionTestCase):
    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user(username='workflow-owner', email='workflow-owner@example.test')
        self.member = users.objects.create_user(username='workflow-member', email='workflow-member@example.test')
        self.workplace = create_workplace_for_user(self.owner, 'Workflow writes')
        WorkplaceMembership.objects.create(workplace=self.workplace, user=self.member)
        self.space = make_space(user=self.owner, workplace=self.workplace, name='Editor', key='EDIT')
        self.config = self.space.configuration
        self.config.shared = True
        self.config.settings['statuses'].append({
            'key': 'temporary', 'label': 'Temporary', 'category': 'new', 'transitions': ['new'],
        })
        self.config.settings['statuses'][0]['transitions'].append('temporary')
        self.config.save()
        self.other = make_space(user=self.owner, workplace=self.workplace, name='Hidden', key='HID',
                                configuration=self.config, visibility='private', private_owner=self.member)
        self.task = SpaceTask.objects.create(space=self.other, title='Shared workflow task', created_by=self.member)

    def request(self, data=None, *, user=None):
        path = f'/space/{self.space.slug}/configuration/'
        request = RequestFactory().get(path) if data is None else RequestFactory().post(path, data)
        request.user, request.workplace = user or self.owner, self.workplace
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def payload(self, *, remove_status=True, remove_type=False):
        with patch.object(views, 'render', side_effect=lambda request, template, context, **kwargs: context):
            context = views.configuration(self.request(), self.space.slug)
        payload = {'revision': context['revision']}
        for group in context['sets']:
            formset = group['formset']
            prefix = formset.prefix
            payload[f'{prefix}-TOTAL_FORMS'] = str(formset.total_form_count())
            payload[f'{prefix}-INITIAL_FORMS'] = str(formset.initial_form_count())
            for index, form in enumerate(formset.extra_forms, formset.initial_form_count()):
                for name, field in form.fields.items():
                    if field.initial is not None and not isinstance(field.initial, bool):
                        payload[f'{prefix}-{index}-{name}'] = field.initial
            for index, initial in enumerate(formset.initial):
                for name, value in initial.items():
                    if remove_status and prefix == 'statuses' and name == 'transitions':
                        value = [key for key in value if key != 'temporary']
                    payload[f'{prefix}-{index}-{name}'] = value if value is not None else ''
                if initial['key'] == 'temporary' and (
                    prefix == 'statuses' and remove_status or prefix == 'types' and remove_type
                ):
                    payload[f'{prefix}-{index}-DELETE'] = 'on'
        return payload

    def assert_waits_for_writer(self, write, payload, expected_error):
        written, release = Event(), Event()

        def writer():
            close_old_connections()
            try:
                with transaction.atomic():
                    write()
                    written.set()
                    if not release.wait(10):
                        raise AssertionError('Configuration request did not finish.')
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(writer)
            try:
                self.assertTrue(written.wait(10))
                with self.assertRaisesMessage(OperationalError, 'lock timeout'):
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute("SET LOCAL lock_timeout = '300ms'")
                        views.configuration(self.request(payload), self.space.slug)
            finally:
                release.set()
                future.result(timeout=10)
        with patch.object(views, 'render', side_effect=lambda request, template, context, **kwargs: context):
            context = views.configuration(self.request(payload), self.space.slug)
        self.assertIn(expected_error, context['errors'])
        self.config.refresh_from_db()

    def test_configuration_waits_for_status_write_in_hidden_shared_space(self):
        payload = self.payload()

        def write():
            set_status(self.request(user=self.member), self.task.work_item, 'temporary')

        self.assert_waits_for_writer(write, payload, 'Nie można usunąć statusu używanego przez zadania.')
        self.assertIn('temporary', {row['key'] for row in self.config.settings['statuses']})
        self.assertEqual(SpaceTask.objects.get(pk=self.task.pk).work_item.status, 'temporary')

    def test_configuration_waits_for_model_creation_in_hidden_shared_space(self):
        self.config.settings['types'].insert(0, {'key': 'temporary', 'label': 'Temporary'})
        self.config.save()
        payload = self.payload(remove_status=False, remove_type=True)

        def write():
            SpaceTask.objects.create(space=self.other, title='Concurrent creation', created_by=self.member)

        self.assert_waits_for_writer(write, payload, 'Nie można usunąć typu używanego przez zadania.')
        self.assertIn('temporary', {row['key'] for row in self.config.settings['types']})

    def remove_before_task_lock(self, request):
        original, changed = QuerySet.select_for_update, False

        def update_configuration():
            close_old_connections()
            try:
                self.assertEqual(views.configuration(self.request(self.payload(remove_type=True)), self.space.slug).status_code, 302)
            finally:
                close_old_connections()

        def before_lock(queryset, *args, **kwargs):
            nonlocal changed
            if not changed and queryset.model is Workplace:
                changed = True
                with ThreadPoolExecutor(max_workers=1) as executor:
                    executor.submit(update_configuration).result(timeout=10)
            return original(queryset, *args, **kwargs)

        with patch.object(QuerySet, 'select_for_update', before_lock):
            return task_views.detail(request, self.space.slug, request.task_key)

    def test_task_forms_reload_workflow_after_waiting_for_lock(self):
        task = SpaceTask.objects.create(space=self.space, title='Stale form', created_by=self.owner)
        original = deepcopy(self.config.settings)
        original['types'].append({'key': 'temporary', 'label': 'Temporary'})
        for action, values in [
            ('save', {'autosave_fields': json.dumps(['work_type']), 'work_type': 'temporary'}),
            ('create_subtask_modal', {'subtask-title': 'Stale child', 'subtask-status': 'temporary',
                                      'subtask-visibility': 'public'}),
        ]:
            with self.subTest(action=action):
                self.config.settings = deepcopy(original)
                self.config.save()
                request = self.request({'action': action, **values})
                request._react_api, request.task_key = True, task.work_item.key
                response = self.remove_before_task_lock(request)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(task.subtasks.exists())
                self.assertEqual(SpaceTask.objects.get(pk=task.pk).work_item.work_type, 'task')
