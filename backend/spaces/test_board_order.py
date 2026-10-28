from datetime import date
import re
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import SpaceMembership, SpaceTask, SpaceTaskMembership, Sprint, WorkItem
from .testing import make_space


class BoardOrderTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='board-owner', email='board-owner@example.test')
        self.member = get_user_model().objects.create_user(username='board-member', email='board-member@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Board order')
        WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
        self.space = make_space(user=self.owner, workplace=self.workspace, name='Scrum', template='scrum',
                                visibility='private', private_owner=self.owner)
        SpaceMembership.objects.create(space=self.space, user=self.member, role='member')
        self.active = Sprint.objects.create(space=self.space, name='Active', start_on=date(2026, 10, 3),
                                            end_on=date(2026, 10, 17), state='active')
        self.first, self.middle, self.last = [self.create_item(title) for title in ('Visible first', 'Hidden middle', 'Visible last')]
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def create_item(self, title, *, status='new', space=None):
        item = SpaceTask.objects.create(created_by=self.owner, space=space or self.space, title=title, status=status).work_item
        item.sprint, item.in_backlog = self.active if space is None else None, False
        item.save(update_fields=['sprint', 'in_backlog'])
        return item

    def move(self, item, *, status=None, before=None, after=None, direction='', query='', overrides=None, plain=False, key=False):
        item.refresh_from_db()
        for anchor in (before, after):
            if anchor:
                anchor.refresh_from_db()
        data = {'action': 'position', 'return_view': 'board', 'space': self.space.pk,
                'source_status': item.status, 'source_sprint': item.sprint_id or '', 'source_rank': item.rank,
                'status': status or item.status, 'before': before.pk if before else '', 'after': after.pk if after else '',
                'before_rank': before.rank if before else '', 'after_rank': after.rank if after else '', 'direction': direction}
        data.update(overrides or {})
        if key:
            path = f'/space/{self.space.slug}/tasks/{item.key}/action/'
            url = path if plain else scoped_workplace_app_path(self.workspace, 'space', path.removeprefix('/space/'))
        else:
            url = f'/spaces/items/{item.pk}/action/' if plain else scoped_workplace_app_path(self.workspace, 'spaces', f'items/{item.pk}/action/')
        return self.client.post(url + query, data, HTTP_X_WORK_ACTION='true')

    def order(self, status='new'):
        return list(WorkItem.objects.filter(space=self.space, sprint=self.active, status=status)
                    .order_by('rank', 'pk').values_list('pk', flat=True))

    def test_reorders_up_and_down_persists_on_get_and_records_actual_actor(self):
        original = (self.first.task.status, self.first.task.is_completed, self.first.task.completion_date)
        self.assertEqual(self.move(self.first, after=self.last, key=True).status_code, 200)
        self.assertEqual(self.order(), [self.middle.pk, self.last.pk, self.first.pk])
        self.assertEqual(self.move(self.first, before=self.middle, key=True, plain=True).status_code, 200)
        self.assertEqual(self.order(), [self.first.pk, self.middle.pk, self.last.pk])
        response = self.client.get(scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/?view=board'))
        self.assertEqual([row.pk for row in response.context['items']], self.order())
        self.first.task.refresh_from_db()
        self.assertEqual((self.first.task.status, self.first.task.is_completed, self.first.task.completion_date), original)
        activity = self.first.task.activities.order_by('-pk').first()
        self.assertEqual(activity.actor, self.member)
        self.assertEqual(activity.message, 'zmienił kolejność zadania na tablicy')

    def test_precise_cross_column_placement_changes_status_and_history_atomically(self):
        left, right = [self.create_item(title, status='in_progress') for title in ('Left', 'Right')]
        response = self.move(self.middle, status='in_progress', before=right, after=left)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.order('in_progress'), [left.pk, self.middle.pk, right.pk])
        self.middle.task.refresh_from_db()
        self.assertEqual(self.middle.task.status, 'in_progress')
        activity = self.middle.task.activities.filter(action='status_changed').get()
        self.assertEqual(activity.actor, self.member)
        self.assertEqual(activity.metadata['new_status'], 'in_progress')
        self.middle.refresh_from_db()
        self.assertEqual(self.middle.sprint_id, self.active.pk)
        self.assertFalse(self.middle.in_backlog)

    def test_empty_target_close_reorder_and_reopen_keep_completion_rules(self):
        self.assertEqual(self.move(self.first, status='closed').status_code, 200)
        self.assertEqual(self.move(self.last, status='closed', after=self.first).status_code, 200)
        self.first.task.refresh_from_db()
        finished = self.first.task.completion_date
        self.assertIsNotNone(finished)
        self.assertTrue(self.first.task.is_completed)
        self.assertEqual(self.move(self.first, status='closed', after=self.last).status_code, 200)
        self.assertEqual(self.order('closed'), [self.last.pk, self.first.pk])
        self.first.task.refresh_from_db()
        self.assertEqual(self.first.task.completion_date, finished)
        self.assertEqual(self.move(self.first, status='reopened').status_code, 200)
        self.first.task.refresh_from_db()
        self.assertFalse(self.first.task.is_completed)
        self.assertIsNone(self.first.task.completion_date)

    def test_menu_directions_and_boundary_noop(self):
        count = self.first.task.activities.count()
        self.assertEqual(self.move(self.first, direction='up').status_code, 200)
        self.assertEqual(self.first.task.activities.count(), count)
        self.assertEqual(self.move(self.first, direction='down').status_code, 200)
        self.assertEqual(self.order(), [self.middle.pk, self.first.pk, self.last.pk])
        self.assertEqual(self.move(self.first, direction='up').status_code, 200)
        self.assertEqual(self.order(), [self.first.pk, self.middle.pk, self.last.pk])
        self.assertEqual(self.move(self.last, direction='down').status_code, 200)
        self.assertEqual(self.move(self.first, direction='sideways').status_code, 400)

    def test_unchanged_placement_does_not_write_history(self):
        count = self.middle.task.activities.count()
        rank = self.middle.rank
        self.assertEqual(self.move(self.middle, before=self.last, after=self.first).status_code, 200)
        self.middle.refresh_from_db()
        self.assertEqual(self.middle.rank, rank)
        self.assertEqual(self.middle.task.activities.count(), count)

    def test_stale_sources_and_anchors_are_rejected_without_partial_status_changes(self):
        for overrides in ({'source_rank': 99}, {'source_status': 'closed'}, {'source_sprint': ''}, {'space': self.space.pk + 1},
                          {'source_rank': ''}, {'before_rank': 999}, {'before': self.first.pk}, {'after': self.last.pk},
                          {'status': 'invalid'}, {'before': ''}, {'before_rank': ''}):
            with self.subTest(overrides=overrides):
                self.assertEqual(self.move(self.first, before=self.middle, overrides=overrides).status_code, 400)
                self.assertEqual(self.order(), [self.first.pk, self.middle.pk, self.last.pk])
                self.assertEqual(self.first.task.activities.count(), 1)
        target = self.create_item('Target', status='closed')
        self.assertEqual(self.move(self.first, status='closed', before=target, overrides={'before_rank': 999}).status_code, 400)
        self.first.task.refresh_from_db()
        self.assertEqual(self.first.task.status, 'new')
        self.assertFalse(self.first.task.is_completed)

    def test_forbidden_transition_rolls_back_ordering(self):
        config = self.space.configuration
        config.settings['statuses'][0]['transitions'] = []
        config.save(update_fields=['settings'])
        rank = self.first.rank
        self.assertEqual(self.move(self.first, status='closed').status_code, 400)
        self.first.refresh_from_db()
        self.assertEqual(self.first.rank, rank)
        self.assertEqual(self.first.status, 'new')

    def test_filters_are_preserved_and_excluded_source_and_anchor_are_rejected(self):
        query = '?q=Visible&priority=medium&view=board'
        response = self.move(self.last, before=self.first, query=query, plain=True)
        self.assertEqual(response.status_code, 200)
        self.middle.refresh_from_db()
        self.assertEqual(self.middle.rank, 200)
        self.assertEqual(parse_qs(urlsplit(response.json()['url']).query), {'q': ['Visible'], 'priority': ['medium'], 'view': ['board']})
        self.assertEqual(self.move(self.middle, before=self.first, query=query).status_code, 400)
        self.assertEqual(self.move(self.last, before=self.middle, after=self.first, query=query).status_code, 400)

    def test_dense_and_duplicate_ranks_preserve_hidden_task(self):
        self.middle.task.visibility, self.middle.task.private_owner = 'private', self.owner
        self.middle.task.save(update_fields=['visibility', 'private_owner'])
        for ranks in ((0, 1, 2), (10, 10, 11)):
            with self.subTest(ranks=ranks):
                for item, rank in zip((self.first, self.middle, self.last), ranks):
                    item.rank = rank
                    item.save(update_fields=['rank'])
                incoming = self.create_item('Visible incoming', status='in_progress')
                self.assertEqual(self.move(incoming, status='new', before=self.last, after=self.first, query='?q=Visible').status_code, 200)
                self.middle.refresh_from_db()
                self.assertEqual(self.middle.rank, ranks[1])
                visible = WorkItem.objects.filter(space=self.space, status='new').exclude(pk=self.middle.pk).order_by('rank', 'pk')
                self.assertEqual(list(visible.values_list('pk', flat=True)), [self.first.pk, incoming.pk, self.last.pk])
                incoming.task.delete()

    def test_hidden_anchor_rejected_and_readonly_anchor_allowed_without_rewriting(self):
        self.middle.task.visibility, self.middle.task.private_owner = 'private', self.owner
        self.middle.task.save(update_fields=['visibility', 'private_owner'])
        self.assertEqual(self.move(self.last, before=self.middle, after=self.first).status_code, 400)
        SpaceTaskMembership.objects.create(task=self.middle.task, user=self.member, role='observer')
        self.assertEqual(self.move(self.last, before=self.middle, after=self.first).status_code, 200)
        self.middle.refresh_from_db()
        self.assertEqual(self.middle.rank, 200)

    def test_dense_readonly_neighbour_rolls_back_the_entire_move(self):
        self.middle.task.visibility, self.middle.task.private_owner = 'private', self.owner
        self.middle.task.save(update_fields=['visibility', 'private_owner'])
        SpaceTaskMembership.objects.create(task=self.middle.task, user=self.member, role='observer')
        for item, rank in zip((self.first, self.middle, self.last), (10, 11, 12)):
            item.rank = rank
            item.save(update_fields=['rank'])
        self.assertEqual(self.move(self.last, before=self.middle, after=self.first).status_code, 403)
        self.assertEqual(list(WorkItem.objects.filter(space=self.space).order_by('pk').values_list('rank', flat=True)), [10, 11, 12])

    def test_observer_cannot_reorder_and_has_no_draggable_cards_or_order_forms(self):
        SpaceMembership.objects.filter(space=self.space, user=self.member).update(role='observer')
        self.assertEqual(self.move(self.first, after=self.last).status_code, 403)
        response = self.client.get(scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/?view=board'))
        cards = re.findall(r'<article\b[^>]*data-work-card[^>]*>', response.content.decode())
        self.assertEqual(len(cards), 3)
        self.assertFalse(any('draggable="true"' in card for card in cards))
        self.assertNotContains(response, 'name="action" value="position"')

    def test_inactive_sprint_or_backlog_source_is_rejected(self):
        self.first.sprint = None
        self.first.save(update_fields=['sprint'])
        self.assertEqual(self.move(self.first, before=self.middle).status_code, 400)
        self.middle.sprint = self.active
        self.active.state = 'closed'
        self.active.save(update_fields=['state'])
        self.assertEqual(self.move(self.middle, before=self.last).status_code, 400)

    def test_foreign_space_workspace_and_status_anchor_are_rejected(self):
        for workspace in (self.workspace, create_workplace_for_user(self.member, 'Other workspace')):
            foreign = make_space(user=workspace.owner, workplace=workspace, name='Other')
            anchor = self.create_item('Foreign', space=foreign)
            self.assertEqual(self.move(self.first, before=anchor).status_code, 400)
        target = self.create_item('Other status', status='resolved')
        self.assertEqual(self.move(self.first, before=target).status_code, 400)

    def test_sources_and_anchors_beyond_one_hundred_remain_reorderable(self):
        for number in range(98):
            self.create_item(f'Extra {number}')
        original = self.order()
        outside = WorkItem.objects.get(pk=original[-1])
        previous = WorkItem.objects.get(pk=original[-2])
        self.assertEqual(self.move(outside, before=self.first, query='?page=1').status_code, 200)
        self.assertEqual(self.order(), [outside.pk, *original[:-1]])
        self.assertEqual(self.move(outside, after=previous, query='?page=2').status_code, 200)
        self.assertEqual(self.order(), original)
        self.assertEqual(self.move(self.first, after=outside, query='?page=2').status_code, 200)
        self.assertEqual(self.order(), [*original[1:], self.first.pk])

    def test_kanban_reorders_and_never_moves_backlog_items(self):
        self.space.template = 'kanban'
        self.space.save(update_fields=['template'])
        for item in (self.first, self.middle, self.last):
            item.sprint = None
            item.save(update_fields=['sprint'])
        self.assertEqual(self.move(self.last, before=self.first).status_code, 200)
        self.assertEqual(list(WorkItem.objects.filter(space=self.space).order_by('rank', 'pk').values_list('pk', flat=True)),
                         [self.last.pk, self.first.pk, self.middle.pk])
        self.middle.in_backlog = True
        self.middle.save(update_fields=['in_backlog'])
        self.assertEqual(self.move(self.first, before=self.middle, after=self.last).status_code, 400)
        self.assertEqual(self.move(self.middle, before=self.last).status_code, 400)

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        self.assertEqual(client.post(scoped_workplace_app_path(self.workspace, 'spaces', f'items/{self.first.pk}/action/'),
                                     {'action': 'position'}).status_code, 403)
