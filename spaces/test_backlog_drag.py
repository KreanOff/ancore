from datetime import date
import re
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from tasks.models import Task, TaskMembership, TaskProject, TaskProjectMembership, TaskSection
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Sprint, WorkItem


class BacklogDragTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='drag-owner', email='drag-owner@example.test')
        self.member = get_user_model().objects.create_user(username='drag-member', email='drag-member@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Drag backlog')
        WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
        self.project = TaskProject.objects.create(user=self.owner, workplace=self.workspace, name='Scrum', visibility='private', private_owner=self.owner)
        TaskProjectMembership.objects.create(project=self.project, user=self.member, role='member')
        self.space = self.project.space
        self.space.template = 'scrum'
        self.space.save(update_fields=['template'])
        self.section = TaskSection.objects.create(project=self.project, title='Tasks')
        self.first, self.middle, self.last = [Task.objects.create(user=self.owner, section=self.section, title=title).work_item for title in ('Visible first', 'Hidden middle', 'Visible last')]
        for row, rank in zip((self.first, self.middle, self.last), (100, 200, 300)):
            row.rank, row.in_backlog = rank, True
            row.save(update_fields=['rank', 'in_backlog'])
        self.planned = Sprint.objects.create(space=self.space, name='Next sprint', start_on=date(2026, 10, 11), end_on=date(2026, 10, 18))
        self.active = Sprint.objects.create(space=self.space, name='Active sprint', start_on=date(2026, 10, 3), end_on=date(2026, 10, 10), state='active')
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def move(self, item, *, sprint=None, before=None, after=None, query='', overrides=None, plain=False):
        item.refresh_from_db()
        data = {'action': 'plan', 'return_view': 'backlog', 'space': self.space.pk,
                'source_sprint': item.sprint_id or '', 'source_rank': item.rank,
                'sprint': sprint.pk if sprint else '', 'before': before.pk if before else '', 'after': after.pk if after else ''}
        data.update(overrides or {})
        base = f'/spaces/items/{item.pk}/action/' if plain else scoped_workplace_app_path(self.workspace, 'spaces', f'items/{item.pk}/action/')
        return self.client.post(base + query, data, HTTP_X_WORK_ACTION='true')

    def order(self, sprint=None):
        return list(WorkItem.objects.filter(space=self.space, sprint=sprint).order_by('rank', 'pk').values_list('pk', flat=True))

    def test_reordering_persists_and_records_actual_actor_without_changing_status(self):
        original = (self.first.task.status, self.first.task.is_completed, self.first.task.completion_date)
        self.assertEqual(self.move(self.first, after=self.last).status_code, 200)
        self.assertEqual(self.order(), [self.middle.pk, self.last.pk, self.first.pk])
        self.first.task.refresh_from_db()
        self.assertEqual((self.first.task.status, self.first.task.is_completed, self.first.task.completion_date), original)
        activity = self.first.task.activities.order_by('-pk').first()
        self.assertEqual(activity.actor, self.member)
        self.assertEqual(activity.message, 'zmienił kolejność zadania')

    def test_moves_to_empty_planned_and_active_sprints_and_back_to_backlog(self):
        for sprint in (self.planned, self.active):
            with self.subTest(sprint=sprint.name):
                self.assertEqual(self.move(self.first, sprint=sprint).status_code, 200)
                self.first.refresh_from_db()
                self.assertEqual(self.first.sprint_id, sprint.pk)
                self.assertFalse(self.first.in_backlog)
                self.assertEqual(self.move(self.first, before=self.middle).status_code, 200)
                self.first.refresh_from_db()
                self.assertIsNone(self.first.sprint_id)
                self.assertTrue(self.first.in_backlog)
                self.assertEqual(self.order()[0], self.first.pk)

    def test_reorders_inside_a_sprint(self):
        for row in (self.first, self.middle, self.last):
            row.sprint, row.in_backlog = self.active, False
            row.save(update_fields=['sprint', 'in_backlog'])
        self.assertEqual(self.move(self.last, sprint=self.active, before=self.first).status_code, 200)
        self.assertEqual(self.order(self.active), [self.last.pk, self.first.pk, self.middle.pk])

    def test_filtered_reordering_preserves_excluded_records_and_return_filters(self):
        response = self.move(self.last, before=self.first, query='?q=Visible&priority=medium&view=backlog', plain=True)
        self.assertEqual(response.status_code, 200)
        self.middle.refresh_from_db()
        self.assertEqual(self.middle.rank, 200)
        self.assertEqual(parse_qs(urlsplit(response.json()['url']).query), {'q': ['Visible'], 'priority': ['medium'], 'view': ['backlog']})

    def test_adjacent_and_duplicate_ranks_are_resolved_without_touching_filtered_rows(self):
        for first_rank, middle_rank, last_rank in [(10, 11, 12), (10, 10, 30)]:
            with self.subTest(ranks=(first_rank, middle_rank, last_rank)):
                for row, rank in zip((self.first, self.middle, self.last), (first_rank, middle_rank, last_rank)):
                    row.rank = rank
                    row.save(update_fields=['rank'])
                self.assertEqual(self.move(self.last, before=self.middle, after=self.first).status_code, 200)
                self.assertEqual(self.order(), [self.first.pk, self.last.pk, self.middle.pk])
                ranks = list(WorkItem.objects.filter(space=self.space).values_list('rank', flat=True))
                self.assertEqual(len(ranks), len(set(ranks)))

    def test_noop_does_not_duplicate_history(self):
        count = self.first.task.activities.count()
        self.assertEqual(self.move(self.first, before=self.middle).status_code, 200)
        self.assertEqual(self.first.task.activities.count(), count)

    def test_rejects_stale_or_malformed_source_and_stale_neighbours_atomically(self):
        for overrides in ({'source_rank': 99}, {'source_sprint': self.active.pk}, {'space': self.space.pk + 100},
                          {'sprint': 'bad'}, {'source_rank': ''}, {'before': self.first.pk}, {'after': self.middle.pk}):
            with self.subTest(overrides=overrides):
                self.assertEqual(self.move(self.first, after=self.last, overrides=overrides).status_code, 400)
                self.assertEqual(self.order(), [self.first.pk, self.middle.pk, self.last.pk])
                self.assertEqual(self.first.task.activities.count(), 1)

    def test_rejects_filtered_out_source_and_anchor(self):
        self.assertEqual(self.move(self.middle, before=self.first, query='?q=Visible').status_code, 400)
        self.assertEqual(self.move(self.last, before=self.middle, after=self.first, query='?q=Visible').status_code, 400)

    def test_closed_tasks_and_sprints_cannot_be_moved(self):
        self.planned.state = 'closed'
        self.planned.save(update_fields=['state'])
        self.assertEqual(self.move(self.first, sprint=self.planned).status_code, 400)
        self.first.task.status = 'closed'
        self.first.task.save(update_fields=['status'])
        self.assertEqual(self.move(self.first, sprint=self.active).status_code, 400)

    def test_foreign_sprint_space_workspace_and_anchor_are_rejected(self):
        for workplace in (self.workspace, create_workplace_for_user(self.member, 'Foreign workspace')):
            project = TaskProject.objects.create(user=workplace.owner, workplace=workplace, name='Other project')
            sprint = Sprint.objects.create(space=project.space, name='Foreign sprint', start_on=date(2026, 10, 3), end_on=date(2026, 10, 10))
            section = TaskSection.objects.create(project=project, title='Other tasks')
            other = Task.objects.create(user=workplace.owner, section=section, title='Other').work_item
            self.assertEqual(self.move(self.first, sprint=sprint).status_code, 400)
            self.assertEqual(self.move(self.first, before=other).status_code, 400)

    def test_observer_cannot_drag_or_submit_move(self):
        TaskProjectMembership.objects.filter(project=self.project, user=self.member).update(role='observer')
        self.assertEqual(self.move(self.first, sprint=self.active).status_code, 403)
        response = self.client.get(scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/?view=backlog'))
        rows = re.findall(r'<article\b[^>]*data-work-backlog-row[^>]*>', response.content.decode())
        self.assertEqual(len(rows), 3)
        self.assertFalse(any('draggable="true"' in row for row in rows))
        self.assertNotContains(response, 'work-backlog-drag-handle')
        self.assertNotContains(response, 'name="action" value="plan"')

    def test_hidden_task_cannot_be_used_as_an_anchor_and_is_unchanged(self):
        self.middle.task.visibility, self.middle.task.private_owner = 'private', self.owner
        self.middle.task.save(update_fields=['visibility', 'private_owner'])
        self.assertEqual(self.move(self.last, before=self.middle, after=self.first).status_code, 400)
        self.assertEqual(self.move(self.last, before=self.first).status_code, 200)
        self.middle.refresh_from_db()
        self.assertEqual(self.middle.rank, 200)

    def test_dense_sprint_ranks_preserve_hidden_and_filtered_rows(self):
        self.middle.task.visibility, self.middle.task.private_owner = 'private', self.owner
        self.middle.task.save(update_fields=['visibility', 'private_owner'])
        for row, rank in zip((self.first, self.middle, self.last), (0, 1, 2)):
            row.rank, row.sprint, row.in_backlog = rank, self.active, False
            row.save(update_fields=['rank', 'sprint', 'in_backlog'])
        incoming = Task.objects.create(user=self.owner, section=self.section, title='Visible incoming').work_item
        self.assertEqual(self.move(incoming, sprint=self.active, before=self.last, after=self.first, query='?q=Visible').status_code, 200)
        self.middle.refresh_from_db()
        self.assertEqual(self.middle.rank, 1)
        visible_order = list(WorkItem.objects.filter(space=self.space, sprint=self.active, task__title__contains='Visible')
                             .order_by('rank', 'pk').values_list('pk', flat=True))
        self.assertEqual(visible_order, [self.first.pk, incoming.pk, self.last.pk])

    def test_readonly_neighbour_can_be_an_anchor_when_its_rank_is_unchanged(self):
        self.middle.task.visibility, self.middle.task.private_owner = 'private', self.owner
        self.middle.task.save(update_fields=['visibility', 'private_owner'])
        TaskMembership.objects.create(task=self.middle.task, user=self.member, role='observer')
        self.assertEqual(self.move(self.last, before=self.middle, after=self.first).status_code, 200)
        self.middle.refresh_from_db()
        self.assertEqual(self.middle.rank, 200)
        self.assertEqual(self.order(), [self.first.pk, self.last.pk, self.middle.pk])

    def test_no_gap_rollback_cannot_rewrite_a_readonly_neighbour(self):
        self.middle.task.visibility, self.middle.task.private_owner = 'private', self.owner
        self.middle.task.save(update_fields=['visibility', 'private_owner'])
        TaskMembership.objects.create(task=self.middle.task, user=self.member, role='observer')
        for row, rank in zip((self.first, self.middle, self.last), (10, 11, 12)):
            row.rank = rank
            row.save(update_fields=['rank'])
        self.assertEqual(self.move(self.last, before=self.middle, after=self.first).status_code, 403)
        self.assertEqual(list(WorkItem.objects.filter(space=self.space).order_by('pk').values_list('rank', flat=True)), [10, 11, 12])

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        url = scoped_workplace_app_path(self.workspace, 'spaces', f'items/{self.first.pk}/action/')
        self.assertEqual(client.post(url, {'action': 'plan'}).status_code, 403)

    def test_source_outside_the_displayed_page_is_rejected(self):
        for number in range(98):
            Task.objects.create(user=self.owner, section=self.section, title=f'Extra {number}')
        outside = WorkItem.objects.filter(space=self.space).order_by('rank', 'pk').last()
        self.assertEqual(self.move(outside, before=self.first, query='?page=1').status_code, 400)
        self.assertEqual(self.move(self.first, before=outside, query='?page=1').status_code, 400)

    def test_kanban_supports_reorder_but_rejects_sprints_and_board_items(self):
        self.space.template = 'kanban'
        self.space.save(update_fields=['template'])
        self.assertEqual(self.move(self.first, after=self.last).status_code, 200)
        self.assertEqual(self.move(self.first, sprint=self.active).status_code, 400)
        self.first.in_backlog = False
        self.first.save(update_fields=['in_backlog'])
        self.assertEqual(self.move(self.first, before=self.middle).status_code, 400)
