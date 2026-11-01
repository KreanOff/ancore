"""Kanban admission covers every write surface and never discloses hidden cards."""
import json
import importlib
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.db import connection
from django.apps import apps
from django.test import RequestFactory, TestCase, TransactionTestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import SpaceMembership, SpaceTask, WorkItem
from .services import set_status
from .testing import make_space
from .workflow import board_wip


class KanbanWorkflowTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='flow-owner', email='flow-owner@example.test')
        self.member = get_user_model().objects.create_user(username='flow-member', email='flow-member@example.test')
        self.outsider = get_user_model().objects.create_user(username='flow-outsider', email='flow-outsider@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Flow')
        WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
        self.space = make_space(user=self.owner, workplace=self.workspace, name='Kanban', template='kanban',
                                visibility='private', private_owner=self.owner)
        SpaceMembership.objects.create(space=self.space, user=self.member)
        self.item = self.create('Zadanie')
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def create(self, title, status='new', *, backlog=False, private=False):
        task = SpaceTask(space=self.space, title=title, status=status, created_by=self.owner,
                         visibility='private' if private else 'public', private_owner=self.owner if private else None)
        task._initial_in_backlog = backlog
        task.save()
        return task.work_item

    def limit(self, count=1, status='in_progress'):
        config = self.space.configuration
        next(row for row in config.settings['statuses'] if row['key'] == status)['wip_limit'] = count
        config.save()

    def url(self, suffix='', **query):
        return scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/{suffix}') + ('?' + urlencode(query) if query else '')

    def action(self, action, item=None, **data):
        return self.client.post(self.url(f'tasks/{(item or self.item).key}/action/', view='board'),
                                {'action': action, **data}, HTTP_X_WORK_ACTION='true')

    def save(self, fields, item=None, **data):
        return self.client.post(self.url(f'tasks/{(item or self.item).key}/'),
                                {'action': 'save', 'autosave_fields': json.dumps(fields), **data},
                                HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_menu_snapshot_rejects_stale_status_and_backlog_without_history(self):
        count = self.item.task.activities.count()
        for values in ({'source_status': 'in_progress'}, {'source_in_backlog': 'true'}):
            response = self.action('status', status='closed', **values)
            self.assertEqual(response.status_code, 400)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'new')
        self.assertEqual(self.item.task.activities.count(), count)
        self.assertEqual(self.action('status', status='in_progress', source_status='new', source_in_backlog='false').status_code, 200)

    def test_closed_cannot_enter_backlog_from_menu_or_form(self):
        self.assertEqual(self.action('status', status='closed').status_code, 200)
        self.assertEqual(self.action('backlog').status_code, 400)
        self.assertEqual(self.save(['in_backlog'], in_backlog='on').status_code, 400)
        edit = self.client.post(self.url(f'tasks/{self.item.key}/edit/'),
                                {'title': 'Nowy', 'priority': 'medium', 'work_type': 'task', 'in_backlog': 'on'},
                                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(edit.status_code, 400)
        self.item.refresh_from_db()
        self.assertFalse(self.item.in_backlog)
        self.assertEqual(self.item.task.title, 'Zadanie')

    def test_closing_backlog_task_moves_it_to_done_and_reopen_preserves_first_start(self):
        self.action('status', status='in_progress')
        self.item.refresh_from_db()
        started = self.item.flow_started_at
        self.assertIsNotNone(started)
        self.assertEqual(self.action('backlog').status_code, 200)
        self.assertEqual(self.save(['status'], status='closed').status_code, 200)
        self.item.refresh_from_db()
        self.assertFalse(self.item.in_backlog)
        self.assertIsNotNone(self.item.flow_finished_at)
        self.assertIsNotNone(self.item.task.completion_date)
        self.assertEqual(self.action('status', status='reopened').status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.flow_started_at, started)
        self.assertIsNone(self.item.flow_finished_at)
        self.assertIsNone(self.item.task.completion_date)
        event = self.item.task.activities.filter(action='status_changed').latest('pk')
        self.assertEqual(event.metadata['old_flow']['stage'], 'done')
        self.assertEqual(event.metadata['flow']['stage'], 'active')

    def test_wip_admission_counts_hidden_tasks_without_disclosing_them(self):
        hidden = self.create('Tajny tytuł', 'in_progress', private=True)
        self.limit()
        visible = board_wip(self.space, self.member)['in_progress']
        self.assertEqual(visible['wip_count'], 0)
        self.assertFalse(visible['wip_full'])
        response = self.action('status', status='in_progress')
        self.assertEqual(response.status_code, 400)
        self.assertIn('WIP', response.json()['error'])
        self.assertNotIn(hidden.task.title, response.json()['error'])
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'new')
        self.assertFalse(self.item.task.activities.filter(action='status_changed').exists())

    def test_wip_ignores_filters_and_backlog_and_done(self):
        self.create('Backlog', 'in_progress', backlog=True)
        self.create('Zakończone', 'closed')
        self.limit()
        self.assertEqual(self.action('status', status='in_progress').status_code, 200)
        candidate = self.create('Kolejne')
        response = self.client.post(self.url(f'tasks/{candidate.key}/action/', view='board', q='Kolejne'),
                                   {'action': 'status', 'status': 'in_progress'}, HTTP_X_WORK_ACTION='true')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(board_wip(self.space, self.member)['in_progress']['wip_count'], 1)

    def test_over_limit_existing_card_can_be_edited_and_reordered(self):
        first = self.create('Pierwsze', 'in_progress')
        last = self.create('Drugie', 'in_progress')
        self.limit()
        self.assertEqual(self.save(['title'], item=first, title='Zmienione').status_code, 200)
        response = self.action('position', item=first, status='in_progress', space=self.space.pk,
                               source_status=first.status, source_sprint='', source_rank=first.rank, direction='down')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.action('status', item=last, status='closed').status_code, 200)

    def test_wip_rejects_creation_and_rolls_back_number_and_history(self):
        self.create('Zajęte', 'in_progress')
        self.limit()
        self.space.refresh_from_db()
        number = self.space.next_number
        response = self.client.post(self.url('items/create/', view='board', initial_status='in_progress'),
                                   {'title': 'Niedozwolone', 'priority': 'medium', 'work_type': 'task', 'status': 'in_progress'},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SpaceTask.objects.filter(title='Niedozwolone').exists())
        self.space.refresh_from_db()
        self.assertEqual(self.space.next_number, number)

    def test_wip_rejects_autosave_and_regular_edit_when_moving_from_backlog(self):
        backlog = self.create('Backlog', 'in_progress', backlog=True)
        self.create('Zajęte', 'in_progress')
        self.limit()
        self.assertEqual(self.save(['status'], status='in_progress').status_code, 400)
        self.assertEqual(self.save(['in_backlog'], item=backlog, in_backlog='').status_code, 400)
        response = self.client.post(self.url(f'tasks/{backlog.key}/edit/'),
                                   {'title': 'Zmiana', 'priority': 'medium', 'work_type': 'task'},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        backlog.refresh_from_db()
        self.assertTrue(backlog.in_backlog)
        self.assertEqual(backlog.task.title, 'Backlog')

    def test_wip_rejects_drag_atomically_and_subtask_creation(self):
        occupied = self.create('Zajęte', 'in_progress')
        self.limit()
        old_rank = self.item.rank
        response = self.action('position', status='in_progress', space=self.space.pk,
            source_status=self.item.status, source_sprint='', source_rank=self.item.rank,
            before='', after=occupied.pk, before_rank='', after_rank=occupied.rank)
        self.assertEqual(response.status_code, 400)
        self.item.refresh_from_db()
        self.assertEqual((self.item.status, self.item.rank), ('new', old_rank))
        self.assertEqual(self.item.task.activities.count(), 1)
        response = self.client.post(self.url(f'tasks/{self.item.key}/'), {
            'action': 'create_subtask_modal', 'subtask-title': 'Podzadanie', 'subtask-status': 'in_progress',
            'subtask-priority': 'medium', 'subtask-work_type': 'task', 'subtask-visibility': 'public'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SpaceTask.objects.filter(title='Podzadanie').exists())

    def test_bulk_board_planning_rolls_back_whole_batch_at_limit(self):
        a = self.create('Backlog A', 'in_progress', backlog=True)
        b = self.create('Backlog B', 'in_progress', backlog=True)
        self.limit()
        response = self.client.post(self.url('backlog/plan/', view='backlog'), {
            'item_ids': [a.pk, b.pk], 'destination': 'board',
            'positions': json.dumps({str(row.pk): [None, row.rank] for row in (a, b)})}, HTTP_X_WORK_ACTION='true')
        self.assertEqual(response.status_code, 400)
        for item in (a, b):
            item.refresh_from_db()
            self.assertTrue(item.in_backlog)
            self.assertEqual(item.task.activities.count(), 1)

    def test_creation_snapshot_uses_custom_status_and_real_planning(self):
        config = self.space.configuration
        config.settings['statuses'].append({'key': 'review', 'label': 'Weryfikacja', 'category': 'in_progress',
                                            'flow_stage': 'active', 'transitions': []})
        config.save()
        response = self.client.post(self.url('items/create/', view='board'), {'title': 'Weryfikacja',
            'priority': 'medium', 'work_type': 'task', 'status': 'review', 'in_backlog': 'on'})
        self.assertEqual(response.status_code, 302)
        item = SpaceTask.objects.get(title='Weryfikacja').work_item
        event = item.task.activities.get(action='created')
        self.assertEqual(event.actor, self.member)
        self.assertEqual(event.metadata['flow']['status'], 'review')
        self.assertTrue(event.metadata['flow']['in_backlog'])
        self.assertIsNone(item.flow_started_at)

    def test_moving_between_done_columns_preserves_completion_and_finish(self):
        config = self.space.configuration
        config.settings['statuses'].append({'key': 'archived_done', 'label': 'Odebrane', 'category': 'closed',
                                            'flow_stage': 'done', 'transitions': ['new']})
        next(row for row in config.settings['statuses'] if row['key'] == 'closed')['transitions'].append('archived_done')
        config.save()
        self.action('status', status='closed')
        self.item.refresh_from_db()
        completed, finished = self.item.task.completion_date, self.item.flow_finished_at
        self.assertEqual(self.action('status', status='archived_done').status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.flow_finished_at, finished)
        self.assertEqual(self.item.task.completion_date, completed)

    def test_block_is_independent_audited_and_responsible_must_have_access(self):
        self.item.task.assignee = self.member
        self.item.task.save()
        response = self.action('block', blocked_reason='Czekamy na decyzję', source_blocked_revision='0')
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        task = self.item.task
        at = task.blocked_at
        self.assertEqual((self.item.status, task.blocked_by_id, task.blocked_responsible_id), ('new', self.member.pk, self.member.pk))
        self.assertEqual(self.action('block', blocked_reason='Obca osoba', blocked_responsible=self.outsider.pk).status_code, 400)
        self.assertEqual(self.action('block', blocked_reason='Nowy powód', source_blocked_revision='0').status_code, 400)
        self.assertEqual(self.action('block', blocked_reason='Nowy powód', source_blocked_revision='1').status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.blocked_at, at)
        self.assertEqual(task.blocked_revision, 2)
        self.assertEqual(self.action('unblock', source_blocked_revision='2').status_code, 200)
        task.refresh_from_db()
        self.assertIsNone(task.blocked_at)
        self.assertEqual(task.blocked_reason, '')
        self.assertEqual(task.activities.filter(action='blocked', actor=self.member).count(), 2)
        self.assertEqual(task.activities.get(action='unblocked').metadata['before']['reason'], 'Nowy powód')

    def test_observer_cannot_block_and_private_task_responsible_is_restricted(self):
        SpaceMembership.objects.filter(space=self.space, user=self.member).update(role='observer')
        self.assertEqual(self.action('block', blocked_reason='Brak dostępu').status_code, 403)
        self.client.force_login(self.owner)
        private = self.create('Prywatne', private=True)
        self.assertEqual(self.action('block', item=private, blocked_reason='Powód', blocked_responsible=self.member.pk).status_code, 400)

    def test_stale_status_autosave_does_not_undo_new_status_but_title_is_independent(self):
        self.action('status', status='in_progress')
        self.assertEqual(self.save(['status'], status='closed', source_status='new').status_code, 400)
        self.assertEqual(self.save(['title'], title='Tytuł', source_status='new').status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'in_progress')

    def test_stale_rank_only_save_preserves_live_status_and_flow_timestamps(self):
        stale = WorkItem.objects.get(pk=self.item.pk)
        self.action('status', status='in_progress')
        current = WorkItem.objects.get(pk=self.item.pk)
        flow = (current.status_entered_at, current.flow_started_at, current.flow_finished_at)
        stale.rank += 1
        stale.save(update_fields=['rank'])
        current.refresh_from_db()
        self.assertEqual(current.status, 'in_progress')
        self.assertEqual((current.status_entered_at, current.flow_started_at, current.flow_finished_at), flow)
        stale.points = 3
        stale.save(update_fields=['points'])
        current.refresh_from_db()
        self.assertEqual((current.status_entered_at, current.flow_started_at, current.flow_finished_at), flow)

    def test_subtask_block_data_preserves_navigation_and_checks_access(self):
        child = SpaceTask.objects.create(space=self.space, parent=self.item.task, title='Podzadanie', created_by=self.owner)
        target = self.url(f'tasks/{child.work_item.key}/', block=1)
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        response = self.client.get(api, {'url': target})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['type'], 'space-block')
        self.assertEqual(response.json()['data']['item']['task_id'], child.pk)
        self.assertEqual(self.client.get(target).status_code, 302)
        SpaceMembership.objects.filter(space=self.space, user=self.member).update(role='observer')
        self.assertEqual(self.client.get(api, {'url': target}).status_code, 403)
        SpaceMembership.objects.filter(space=self.space, user=self.member).delete()
        self.assertEqual(self.client.get(api, {'url': target}).status_code, 404)

    def test_migration_restores_closed_backlog_without_rewriting_history(self):
        closed = self.create('Ukryte zakończone', 'closed')
        backlog = self.create('Otwarte', backlog=True)
        # Reproduce data written by the old endpoint, bypassing today's guard.
        WorkItem.objects.filter(pk=closed.pk).update(in_backlog=True)
        finished, rank, history = closed.task.completion_date, closed.rank, closed.task.activities.count()
        migration = importlib.import_module('spaces.migrations.0005_kanban_flow')
        with connection.schema_editor() as editor:
            migration.restore_closed_cards(apps, editor)
        closed.refresh_from_db()
        backlog.refresh_from_db()
        self.assertFalse(closed.in_backlog)
        self.assertTrue(backlog.in_backlog)
        self.assertEqual((closed.task.completion_date, closed.rank, closed.task.activities.count()), (finished, rank, history))

    def test_block_filter_survives_report_csv_and_summary_drilldown(self):
        self.create('Bez blokady')
        self.action('block', blocked_reason='Czekamy')
        report = self.client.get(self.url(view='reports', blocked='yes'))
        self.assertEqual(report.context['reports']['snapshot']['total'], 1)
        export_url = report.context['reports']['export_url']
        self.assertIn('blocked=yes', export_url)
        csv = b''.join(self.client.get(export_url).streaming_content).decode('utf-8-sig')
        self.assertIn('Zadanie', csv)
        self.assertNotIn('Bez blokady', csv)
        summary = self.client.get(self.url(view='overview', blocked='yes'))
        self.assertTrue(all('blocked=yes' in row['url'] for row in summary.context['summary']['metrics']))
        self.assertEqual(summary.context['item_filter_count'], 1)


class KanbanCapacityRaceTests(TransactionTestCase):
    def test_two_concurrent_transitions_cannot_overfill_one_slot(self):
        owner = get_user_model().objects.create_user(username='capacity-race-owner', email='capacity-race@example.test')
        workspace = create_workplace_for_user(owner, 'Race')
        space = make_space(user=owner, workplace=workspace, name='Capacity', template='kanban')
        config = space.configuration
        next(row for row in config.settings['statuses'] if row['key'] == 'in_progress')['wip_limit'] = 1
        config.save()
        items = [SpaceTask.objects.create(space=space, title=f'Praca {i}', created_by=owner).work_item for i in range(2)]
        barrier = Barrier(2)

        def change(pk):
            close_old_connections()
            try:
                request = RequestFactory().post('/')
                request.user, request.workplace = owner, workspace
                item = WorkItem.objects.get(pk=pk)
                barrier.wait(timeout=10)
                try:
                    set_status(request, item, 'in_progress')
                    return 'saved'
                except ValidationError:
                    return 'full'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(change, [item.pk for item in items]))
        self.assertCountEqual(results, ['saved', 'full'])
        self.assertEqual(WorkItem.objects.filter(space=space, status='in_progress').count(), 1)
