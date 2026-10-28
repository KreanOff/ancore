import json
from datetime import date
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import SpaceMembership, SpaceTask, SpaceTaskMembership, Sprint, WorkItem
from .testing import make_space


class BacklogPlanningTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='plan-owner', email='plan-owner@example.test')
        self.member = get_user_model().objects.create_user(username='plan-member', email='plan-member@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Planowanie')
        WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
        self.space = make_space(user=self.owner, workplace=self.workspace, name='Scrum', template='scrum', visibility='private', private_owner=self.owner)
        SpaceMembership.objects.create(space=self.space, user=self.member, role='member')
        self.first, self.second, self.third = [SpaceTask.objects.create(space=self.space, created_by=self.owner, title=title).work_item for title in ('Pierwsze', 'Drugie', 'Trzecie')]
        for item, points in ((self.first, 0), (self.second, 5), (self.third, None)):
            item.in_backlog, item.points = True, points
            item.save()
        self.planned = Sprint.objects.create(space=self.space, name='Następny', start_on=date(2026,10,19), end_on=date(2026,11,1))
        self.login(self.member)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix='', query='view=backlog'):
        return scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/{suffix}') + ('?' + query if query else '')

    def bulk(self, items, destination='', query='view=backlog', overrides=None):
        for item in items:
            item.refresh_from_db()
        data = {'item_ids': [str(item.pk) for item in items], 'destination': str(destination),
                'positions': json.dumps({str(item.pk): [item.sprint_id, item.rank] for item in items})}
        data.update(overrides or {})
        return self.client.post(self.url('backlog/plan/', query), data, HTTP_X_WORK_ACTION='true')

    def test_bulk_moves_preserve_order_status_completion_and_actual_actor(self):
        before = (self.first.task.status, self.first.task.is_completed, self.first.task.completion_date)
        response = self.bulk([self.second, self.first], self.planned.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['changed'], 2)
        self.assertEqual(list(self.planned.items.values_list('pk', flat=True)), [self.first.pk, self.second.pk])
        self.first.refresh_from_db(); self.first.task.refresh_from_db()
        self.assertFalse(self.first.in_backlog)
        self.assertEqual((self.first.task.status, self.first.task.is_completed, self.first.task.completion_date), before)
        self.assertEqual(self.first.task.activities.last().actor, self.member)
        self.third.refresh_from_db()
        self.assertEqual(self.third.rank, 300)

    def test_bulk_noop_does_not_create_history(self):
        count = self.first.task.activities.count()
        response = self.bulk([self.first])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['changed'], 0)
        self.assertEqual(self.first.task.activities.count(), count)

    def test_stale_snapshot_rejects_entire_batch(self):
        response = self.bulk([self.first, self.second], self.planned.pk, overrides={'positions': json.dumps({str(self.first.pk): [None, 100], str(self.second.pk): [None, 999]})})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.planned.items.exists())

    def test_filtered_or_closed_source_rejects_entire_batch(self):
        self.assertEqual(self.bulk([self.first, self.second], self.planned.pk, query='q=Pierwsze').status_code, 400)
        self.second.task.status = 'closed'; self.second.task.save()
        self.assertEqual(self.bulk([self.first, self.second], self.planned.pk).status_code, 400)
        self.assertFalse(self.planned.items.exists())

    def test_hidden_and_readonly_source_rejects_entire_batch(self):
        self.second.task.visibility, self.second.task.private_owner = 'private', self.owner
        self.second.task.save()
        self.assertEqual(self.bulk([self.first, self.second], self.planned.pk).status_code, 400)
        SpaceTaskMembership.objects.create(task=self.second.task, user=self.member, role='observer')
        self.assertEqual(self.bulk([self.first, self.second], self.planned.pk).status_code, 403)
        self.assertFalse(self.planned.items.exists())

    def test_observer_and_revoked_space_cannot_plan(self):
        SpaceMembership.objects.filter(space=self.space, user=self.member).update(role='observer')
        self.assertEqual(self.bulk([self.first], self.planned.pk).status_code, 403)
        page = self.client.get(self.url())
        self.assertNotContains(page, 'data-backlog-bulk>')
        self.assertNotContains(page, 'data-backlog-select-group')
        SpaceMembership.objects.filter(space=self.space, user=self.member).delete()
        self.assertEqual(self.bulk([self.first], self.planned.pk).status_code, 404)

    def test_invalid_selection_and_target(self):
        for override in ({'item_ids': []}, {'item_ids': [self.first.pk, self.first.pk]}, {'item_ids': ['bad']}, {'positions': '{}'}, {'positions': 'null'}, {'destination': 'bad'}, {'destination': 'board'}):
            with self.subTest(override=override):
                self.assertEqual(self.bulk([self.first], self.planned.pk, overrides=override).status_code, 400)
        self.planned.state = 'closed'; self.planned.save()
        self.assertEqual(self.bulk([self.first], self.planned.pk).status_code, 400)
        self.assertFalse(self.planned.items.exists())

    def test_foreign_sprint_and_workspace_are_rejected(self):
        other = make_space(user=self.owner, workplace=self.workspace, name='Obca', template='scrum')
        sprint = Sprint.objects.create(space=other, name='Obcy sprint', start_on=self.planned.start_on, end_on=self.planned.end_on)
        self.assertEqual(self.bulk([self.first], sprint.pk).status_code, 400)
        session = self.client.session
        other_workspace = create_workplace_for_user(self.member, 'Inny Workspace')
        session['active_workplace_id'] = other_workspace.pk; session.save()
        self.assertEqual(self.client.post(f'/space/{self.space.slug}/backlog/plan/', {'item_ids': [self.first.pk]}).status_code, 404)

    def test_selection_outside_loaded_group_cannot_be_used_until_expanded(self):
        for number in range(100):
            SpaceTask.objects.create(space=self.space, created_by=self.owner, title=f'Extra {number}')
        last = WorkItem.objects.filter(space=self.space).last()
        self.assertEqual(self.bulk([self.first, last], self.planned.pk, query='page=1').status_code, 400)
        response = self.bulk([self.first, last], self.planned.pk, query='page=2&backlog_limit_backlog=103')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['changed'], 2)
        self.assertEqual(parse_qs(urlsplit(response.json()['url']).query), {'backlog_limit_backlog': ['103'], 'view': ['backlog']})

    def test_expanding_backlog_does_not_raise_the_bulk_selection_cap(self):
        for number in range(98):
            SpaceTask.objects.create(space=self.space, created_by=self.owner, title=f'Extra {number}')
        self.assertEqual(self.bulk(list(WorkItem.objects.filter(space=self.space)), self.planned.pk,
                                   query='backlog_limit_backlog=101').status_code, 400)
        self.assertFalse(self.planned.items.exists())

    def test_kanban_batch_moves_to_board_without_sprint(self):
        self.space.template = 'kanban'; self.space.save()
        self.assertEqual(self.bulk([self.first], self.planned.pk).status_code, 400)
        self.assertEqual(self.bulk([self.first, self.second], 'board').status_code, 200)
        self.first.refresh_from_db()
        self.assertFalse(self.first.in_backlog)
        self.assertIsNone(self.first.sprint_id)

    def test_batch_requires_csrf(self):
        client = Client(enforce_csrf_checks=True); client.force_login(self.owner)
        self.assertEqual(client.post(self.url('backlog/plan/'), {'item_ids': [self.first.pk]}).status_code, 403)

    def test_plain_and_scoped_routes_preserve_filters(self):
        for base in (self.url('backlog/plan/', 'q=Pierwsze&priority=medium'), f'/space/{self.space.slug}/backlog/plan/?q=Pierwsze&priority=medium'):
            response = self.client.post(base, {'item_ids': [self.first.pk], 'positions': json.dumps({str(self.first.pk): [None, self.first.rank]}), 'destination': ''}, HTTP_X_WORK_ACTION='true')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(parse_qs(urlsplit(response.json()['url']).query), {'q': ['Pierwsze'], 'priority': ['medium'], 'view': ['backlog']})

    def test_full_filtered_totals_distinguish_zero_from_missing_and_hide_private_data(self):
        page = self.client.get(self.url())
        self.assertEqual(page.context['backlog_totals']['points'], 5)
        self.assertEqual(page.context['backlog_totals']['unestimated'], 1)
        self.second.task.visibility, self.second.task.private_owner = 'private', self.owner
        self.second.task.save()
        page = self.client.get(self.url())
        self.assertEqual(page.context['backlog_totals']['points'], 0)
        self.assertEqual(page.context['backlog_totals']['total'], 2)
        self.assertEqual(self.client.get(self.url(query='view=backlog&q=Pierwsze')).context['backlog_totals']['unestimated'], 0)

    def test_totals_include_unloaded_items_and_closed_sprint_is_not_planned(self):
        for number in range(100):
            SpaceTask.objects.create(space=self.space, created_by=self.owner, title=f'Extra {number}')
        self.planned.state = 'closed'; self.planned.save()
        page = self.client.get(self.url())
        self.assertEqual(page.context['backlog_totals']['total'], 103)
        self.assertEqual(len(page.context['items']), 20)
        self.assertEqual(page.context['sprints'], [])

    def test_contextual_create_defaults_and_return_to_backlog(self):
        for query, sprint_id, backlog in (('view=backlog&q=Nowe', None, True), (f'view=backlog&planning_sprint={self.planned.pk}', self.planned.pk, False)):
            response = self.client.get(self.url('items/create/', query))
            form = response.context['modal']['form']
            self.assertEqual(getattr(form.initial.get('sprint'), 'pk', None), sprint_id)
            self.assertEqual(form.initial['in_backlog'], backlog)
            self.assertContains(response, 'data-work-backlog')
        response = self.client.post(self.url('items/create/', 'view=backlog&q=Nowe'), {'title': 'Nowe zadanie', 'work_type': 'task', 'priority': 'medium', 'in_backlog': 'on'}, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 200)
        created = WorkItem.objects.get(task__title='Nowe zadanie')
        self.assertTrue(created.in_backlog)
        self.assertEqual(parse_qs(urlsplit(response.json()['url']).query), {'q': ['Nowe'], 'view': ['backlog']})

    def test_sprint_edit_and_invalid_dates(self):
        self.login(self.owner)
        url = self.url(f'sprints/{self.planned.pk}/edit/', 'view=backlog&q=Pierwsze')
        data = {'name': 'Poprawiony', 'goal': 'Cel', 'start_on': '2026-10-19', 'end_on': '2026-10-01'}
        self.assertEqual(self.client.post(url, data, HTTP_X_WORK_MODAL='true').status_code, 400)
        self.planned.refresh_from_db(); self.assertEqual(self.planned.name, 'Następny')
        data['end_on'] = '2026-11-01'
        response = self.client.post(url, data, HTTP_X_WORK_MODAL='true')
        self.assertTrue(response.json()['saved'])
        self.assertIn('q=Pierwsze', response.json()['url'])
        self.planned.refresh_from_db(); self.assertEqual(self.planned.goal, 'Cel')

    def test_start_empty_sprint_or_second_active_sprint_is_rejected(self):
        self.login(self.owner)
        data = {'name': 'Następny', 'start_on': '2026-10-19', 'end_on': '2026-11-01'}
        url = self.url(f'sprints/{self.planned.pk}/start/')
        self.assertEqual(self.client.post(url, data, HTTP_X_WORK_MODAL='true').status_code, 400)
        self.first.sprint = self.planned; self.first.save()
        self.assertEqual(self.client.post(url, data, HTTP_X_WORK_MODAL='true').status_code, 200)
        self.assertEqual(self.client.post(url, data, HTTP_X_WORK_MODAL='true').status_code, 400)
        self.planned.refresh_from_db(); self.assertEqual(self.planned.state, 'active')

    def test_completion_carries_unfinished_to_next_sprint_and_keeps_done(self):
        self.login(self.owner)
        active = Sprint.objects.create(space=self.space, name='Aktywny', start_on=date(2026,10,1), end_on=date(2026,10,14), state='active')
        for item in (self.first, self.second):
            item.sprint, item.in_backlog = active, False; item.save()
        self.second.task.status = 'closed'; self.second.task.save()
        self.third.sprint, self.third.in_backlog = self.planned, False; self.third.save()
        response = self.client.post(self.url(f'sprints/{active.pk}/complete/'), {'destination': self.planned.pk}, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(self.planned.items.values_list('pk', flat=True)), [self.third.pk, self.first.pk])
        self.second.refresh_from_db(); self.assertEqual(self.second.sprint_id, active.pk)
        self.assertEqual(self.first.task.activities.last().actor, self.owner)
        active.refresh_from_db()
        self.assertEqual((active.state, active.result['total'], active.result['finished'], active.result['finished_points']), ('closed', 2, 1, 5))
        self.assertIsNotNone(active.completed_at)

    def test_completion_with_readonly_task_rolls_back_sprint_and_all_moves(self):
        self.login(self.owner)
        self.planned.state = 'active'; self.planned.save()
        for item in (self.first, self.second):
            item.sprint = self.planned; item.save()
        self.second.task.visibility, self.second.task.private_owner = 'private', self.member
        self.second.task.save()
        response = self.client.post(self.url(f'sprints/{self.planned.pk}/complete/'), {'destination': ''}, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 400)
        self.planned.refresh_from_db(); self.assertEqual(self.planned.state, 'active')
        self.assertEqual(self.planned.items.count(), 2)

    def test_sprint_operations_reject_member_and_foreign_destination(self):
        for operation in ('edit', 'start', 'complete'):
            self.assertEqual(self.client.get(self.url(f'sprints/{self.planned.pk}/{operation}/')).status_code, 403)
        self.login(self.owner)
        self.planned.state = 'active'; self.planned.save()
        other = make_space(user=self.owner, workplace=self.workspace, name='Obca', template='scrum')
        foreign = Sprint.objects.create(space=other, name='Obcy', start_on=self.planned.start_on, end_on=self.planned.end_on)
        self.assertEqual(self.client.post(self.url(f'sprints/{self.planned.pk}/complete/'), {'destination': foreign.pk}, HTTP_X_WORK_MODAL='true').status_code, 400)

    def test_rank_exhaustion_rolls_back_whole_batch(self):
        self.third.rank = 2147483600; self.third.save()
        self.assertEqual(self.bulk([self.first, self.second], self.planned.pk).status_code, 400)
        self.assertFalse(self.planned.items.exists())

    def test_creating_after_planning_appends_without_colliding_with_existing_ranks(self):
        self.assertEqual(self.bulk([self.first, self.second], self.planned.pk).status_code, 200)
        new = SpaceTask.objects.create(space=self.space, created_by=self.member, title='Nowa pozycja').work_item
        new.sprint = self.planned; new.save()
        self.assertEqual(list(self.planned.items.values_list('pk', flat=True)), [self.first.pk, self.second.pk, new.pk])
        ranks = list(self.planned.items.values_list('rank', flat=True))
        self.assertEqual(len(ranks), len(set(ranks)))
