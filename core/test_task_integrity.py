import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase

from dashboard.views import _dashboard_notifications
from kanban.models import Kanban, KanbanBoardColumn, KanbanProject, KanbanSection
from planner.models import CalendarEvent
from tasks.models import Task, TaskProject, TaskSection
from workplaces.models import create_workplace_for_user
from workplaces.services import backfill_legacy_records_for_workplace, scoped_workplace_app_path


MODULES = [('tasks', Task), ('kanban', Kanban)]


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

    def test_repeated_deletion_uses_pk_after_renumbering_and_is_idempotent(self):
        for app, model in MODULES:
            with self.subTest(app=app):
                a, b, c = [model.objects.create(user=self.user, workplace=self.first, title=title) for title in 'ABC']
                url = scoped_workplace_app_path(self.first, app, 'delete/')
                for key in [a.pk, a.pk, b.pk]:
                    self.assertEqual(self.post_json(url, {'task_pks': [key]}).status_code, 200)
                self.assertEqual(list(model.objects.values_list('pk', flat=True)), [c.pk])
                c.refresh_from_db()
                self.assertEqual(c.task_id, 1)

    def test_scoped_actions_stay_in_first_tab_after_opening_second_workspace(self):
        for app, model in MODULES:
            with self.subTest(app=app):
                a = model.objects.create(user=self.user, workplace=self.first, title='A')
                b = model.objects.create(user=self.user, workplace=self.second, title='B')
                self.client.get(scoped_workplace_app_path(self.second, 'calendar'))
                response = self.post_json(scoped_workplace_app_path(self.first, app, 'delete/'), {'task_pks': [a.pk, b.pk]})
                self.assertEqual(response.status_code, 200)
                self.assertFalse(model.objects.filter(pk=a.pk).exists())
                self.assertTrue(model.objects.filter(pk=b.pk).exists())

    def test_mutations_reject_display_numbers_and_malformed_identities(self):
        for app, model in MODULES:
            item = model.objects.create(user=self.user, workplace=self.first, title='Protected')
            for suffix in ['delete/', 'bulk-update-status/']:
                for data in [{'task_ids': [item.task_id]}, {'task_pks': []}, {'task_pks': [True]}, {'task_pks': ['1']}, []]:
                    with self.subTest(app=app, suffix=suffix, data=data):
                        self.assertEqual(self.post_json(scoped_workplace_app_path(self.first, app, suffix), data).status_code, 400)
            for suffix in [f'delete/{item.task_id}/', f'update/{item.task_id}/']:
                self.assertEqual(self.post_json(scoped_workplace_app_path(self.first, app, suffix), {}).status_code, 400)
            self.assertTrue(model.objects.filter(pk=item.pk, status='new').exists())

    def test_single_and_bulk_status_changes_preserve_scope_and_completion(self):
        for app, model in MODULES:
            item = model.objects.create(user=self.user, workplace=self.first, title='Target')
            other = model.objects.create(user=self.other, workplace=self.first, title='Foreign owner')
            elsewhere = model.objects.create(user=self.user, workplace=self.second, title='Foreign workspace')
            base = scoped_workplace_app_path(self.first, app)
            response = self.post_json(base + 'update/999/', {'task_pk': item.pk, 'status': 'closed'})
            self.assertEqual(response.status_code, 200)
            item.refresh_from_db()
            self.assertTrue(item.is_completed)
            self.assertIsNotNone(item.completion_date)
            for forbidden in [other, elsewhere]:
                self.assertEqual(self.post_json(base + 'update/999/', {'task_pk': forbidden.pk, 'status': 'closed'}).status_code, 404)
                self.assertEqual(self.post_json(base + 'delete/999/', {'task_pk': forbidden.pk}).status_code, 404)
            response = self.post_json(base + 'bulk-update-status/', {'task_pks': [item.pk, other.pk, elsewhere.pk], 'status': 'reopened'})
            self.assertEqual(response.json()['updated_count'], 1)
            item.refresh_from_db()
            self.assertFalse(item.is_completed)
            self.assertIsNone(item.completion_date)
            self.assertEqual(model.objects.get(pk=other.pk).status, 'new')
            self.assertEqual(model.objects.get(pk=elsewhere.pk).status, 'new')

    def test_stale_detail_link_uses_pk_and_does_not_open_reassigned_number(self):
        for app, model in MODULES:
            a, b, c = [model.objects.create(user=self.user, workplace=self.first, title=title) for title in 'ABC']
            old_number = b.task_id
            a.delete()
            url = scoped_workplace_app_path(self.first, app, f'view-task/{old_number}/')
            response = self.client.get(url, {'task_pk': b.pk})
            self.assertEqual(response.context['task'].pk, b.pk)
            self.assertContains(response, f'name="task_pk" value="{b.pk}"')
            self.assertEqual(self.client.get(url, {'task_pk': 'invalid'}).status_code, 404)
            foreign = model.objects.create(user=self.user, workplace=self.second, title='Foreign')
            self.assertEqual(self.client.get(url, {'task_pk': foreign.pk}).status_code, 404)

    def test_legacy_and_scoped_pages_render_workspace_and_pk_contract(self):
        for app, model, project_model, section_model in [('tasks', Task, TaskProject, TaskSection), ('kanban', Kanban, KanbanProject, KanbanSection)]:
            project = project_model.objects.create(user=self.user, workplace=self.first, name=app)
            section = section_model.objects.create(project=project, title='Group')
            if app == 'kanban':
                KanbanBoardColumn.objects.create(section=section, title='Column')
            item = model.objects.create(user=self.user, section=section, title='Item')
            base = scoped_workplace_app_path(self.first, app)
            self.client.get(scoped_workplace_app_path(self.first, 'calendar'))
            for path in [base + f'groups/{section.pk}/', f'/{app}/groups/{section.pk}/']:
                page = self.client.get(path, follow=True)
                self.assertContains(page, f'data-task-app="{app}"')
                self.assertContains(page, f'data-task-base-url="{base}"')
                self.assertContains(page, f'data-task-pk="{item.pk}"')
                self.assertContains(page, f'{base}view-task/{item.task_id}/?task_pk={item.pk}')

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

    def test_notifications_open_the_workspace_of_each_task_or_card(self):
        expected = {}
        for app, model in MODULES:
            for workspace in [self.first, self.second]:
                item = model.objects.create(user=self.user, workplace=workspace, title=f'{app}-{workspace.pk}')
                item.activities.create(actor=self.user, kind='comment', action='commented', message='Komentarz')
                expected[item.title] = (item.pk, workspace)
        notifications = _dashboard_notifications(self.user)
        self.assertEqual(len(notifications), len(expected))
        for notification in notifications:
            key, workspace = expected[notification['title']]
            self.client.get(scoped_workplace_app_path(self.first, 'calendar'))
            response = self.client.get(notification['url'], follow=True)
            self.assertEqual(response.context['task'].pk, key)
            self.assertEqual(response.context['task'].workplace_id, workspace.pk)

    def test_legacy_backfill_compacts_numbers_without_collisions(self):
        for app, model in MODULES:
            model.objects.create(user=self.user, workplace=self.first, title='Existing')
            model.objects.create(user=self.user, title='Legacy')
            backfill_legacy_records_for_workplace(self.user, self.first)
            self.assertEqual(list(model.objects.filter(workplace=self.first).order_by('task_id').values_list('task_id', flat=True)), [1, 2])

    def test_saving_stale_instance_does_not_restore_old_number(self):
        for app, model in MODULES:
            a, b = [model.objects.create(user=self.user, workplace=self.first, title=title) for title in 'AB']
            a.delete()
            b.title = 'Updated'
            b.save()
            b.refresh_from_db()
            self.assertEqual(b.task_id, 1)


class ConcurrentTaskNumberTests(TransactionTestCase):
    def test_simultaneous_creates_in_the_same_section_receive_distinct_numbers(self):
        user = get_user_model().objects.create_user(username='race-owner', email='race@example.test')
        workplace = create_workplace_for_user(user, 'Race')
        for model, project_model, section_model in [(Task, TaskProject, TaskSection), (Kanban, KanbanProject, KanbanSection)]:
            project = project_model.objects.create(user=user, workplace=workplace, name=model.__name__)
            section = section_model.objects.create(project=project, title='Section')
            first_read, release, second_started, second_finished = Event(), Event(), Event(), Event()
            original = QuerySet.aggregate

            def paused_first_read(queryset, *args, **kwargs):
                result = original(queryset, *args, **kwargs)
                if queryset.model is model and 'task_id__max' in result and not first_read.is_set():
                    first_read.set()
                    if not release.wait(10):
                        raise TimeoutError('Concurrent creation did not finish')
                return result

            def create(index):
                close_old_connections()
                if index == 2:
                    second_started.set()
                try:
                    return model.objects.create(user_id=user.pk, section_id=section.pk, title=f'Item {index}').task_id
                finally:
                    if index == 2:
                        second_finished.set()
                    close_old_connections()

            with patch.object(QuerySet, 'aggregate', paused_first_read), ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(create, 1)
                try:
                    self.assertTrue(first_read.wait(10))
                    second = executor.submit(create, 2)
                    self.assertTrue(second_started.wait(10))
                    blocked = not second_finished.wait(0.5)
                finally:
                    release.set()
                numbers = [first.result(timeout=10), second.result(timeout=10)]
            self.assertTrue(blocked)
            self.assertEqual(numbers, [1, 2])

    def test_database_rejects_duplicate_numbers_and_allows_other_scopes(self):
        user = get_user_model().objects.create_user(username='constraint-owner', email='constraint@example.test')
        first = create_workplace_for_user(user, 'First')
        second = create_workplace_for_user(user, 'Second')
        for app, model in MODULES:
            a, b = [model.objects.create(user=user, workplace=first, title=title) for title in 'AB']
            with self.assertRaises(IntegrityError), transaction.atomic():
                model.objects.filter(pk=b.pk).update(task_id=a.task_id)
            other = model.objects.create(user=user, workplace=second, title='Other workspace')
            self.assertEqual(other.task_id, 1)
