from .testing import make_space
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import SpaceTask, Space, SpaceMembership, Team
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class BacklogOrderingTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='order-owner', email='order-owner@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Backlog ordering')
        self.project = make_space(user=self.owner, workplace=self.workspace, name='Kanban')
        self.space = self.project
        self.space.template = 'kanban'
        self.space.save(update_fields=['template'])
        self.section = self.project
        self.first, self.middle, self.last = [SpaceTask.objects.create(created_by=self.owner, space=self.section, title=title).work_item for title in ('Visible first', 'Hidden middle', 'Visible last')]
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()
        self.reset_order()

    def reset_order(self):
        for item, rank in ((self.first, 10), (self.middle, 20), (self.last, 30)):
            item.rank, item.in_backlog = rank, True
            item.save(update_fields=['rank', 'in_backlog'])

    def action(self, item, query=''):
        url = scoped_workplace_app_path(self.workspace, 'spaces', f'items/{item.pk}/action/') + query
        return self.client.post(url, {'action': 'down', 'return_view': 'backlog'}, HTTP_X_WORK_ACTION='true')

    def assert_visible_swapped(self):
        self.first.refresh_from_db()
        self.middle.refresh_from_db()
        self.last.refresh_from_db()
        self.assertEqual((self.first.rank, self.middle.rank, self.last.rank), (30, 20, 10))

    def test_backlog_reorder_skips_board_items(self):
        self.middle.in_backlog = False
        self.middle.save(update_fields=['in_backlog'])
        self.assertEqual(self.action(self.first).status_code, 200)
        self.assert_visible_swapped()

    def test_backlog_reorder_skips_closed_tasks(self):
        self.middle.task.status = 'closed'
        self.middle.task.save(update_fields=['status'])
        self.assertEqual(self.action(self.first).status_code, 200)
        self.assert_visible_swapped()

    def test_backlog_reorder_respects_search_and_preserves_return_filters(self):
        response = self.action(self.first, '?q=Visible&view=backlog')
        self.assertEqual(response.status_code, 200)
        self.assert_visible_swapped()
        params = parse_qs(urlsplit(response.json()['url']).query)
        self.assertEqual(params, {'q': ['Visible'], 'view': ['backlog']})

    def test_backlog_reorder_respects_team_filter(self):
        team = Team.objects.create(owner=self.owner, workplace=self.workspace, name='Widoczny zespół')
        team.spaces.add(self.space)
        for item in (self.first, self.last):
            item.team = team
            item.save(update_fields=['team'])
        self.assertEqual(self.action(self.first, f'?team={team.pk}').status_code, 200)
        self.assert_visible_swapped()


    def test_filtered_out_item_returns_error_without_changing_order(self):
        response = self.action(self.first, '?q=missing')
        self.assertEqual(response.status_code, 400)
        self.first.refresh_from_db()
        self.assertEqual(self.first.rank, 10)

    def test_rendered_action_preserves_the_displayed_filter_scope(self):
        url = scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/')
        response = self.client.get(url, {'view': 'backlog', 'q': 'Visible', 'priority': 'medium'})
        self.assertEqual(response.status_code, 200)
        rows = response.context['items']
        self.assertEqual(len(rows), 2)
        params = parse_qs(urlsplit(rows[0].action_url).query)
        self.assertEqual(params, {'view': ['backlog'], 'q': ['Visible'], 'priority': ['medium']})
        self.assertContains(response, 'Przesuń niżej', count=2)
        self.assertContains(response, 'work-issue-row--actions', count=2)

    def test_observer_backlog_does_not_expose_write_controls(self):
        observer = get_user_model().objects.create_user(username='order-observer', email='order-observer@example.test')
        WorkplaceMembership.objects.create(workplace=self.workspace, user=observer)
        self.project.visibility, self.project.private_owner = 'private', self.owner
        self.project.save(update_fields=['visibility', 'private_owner'])
        SpaceMembership.objects.create(space=self.project, user=observer, role='observer')
        self.client.force_login(observer)
        url = scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/?view=backlog')
        response = self.client.get(url)
        self.assertContains(response, 'Visible first')
        self.assertNotContains(response, 'Przesuń niżej')
        self.assertNotContains(response, 'work-issue-row--actions')
