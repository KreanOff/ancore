"""Stage appearance follows configuration across JSON and first render."""
from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase

from spaces.defaults import configuration_name_color
from spaces.models import WorkItem
from spaces.testing import make_space, make_task
from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class StatusColorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='colors', email='colors@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Kolory')
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Przestrzeń', template='kanban')
        settings = deepcopy(cls.space.configuration.settings)
        for status in settings['statuses']:
            status['transitions'].append('paused')
        settings['statuses'].append({'key': 'paused', 'label': 'Wstrzymane', 'category': 'in_progress', 'color': '#ee33cc', 'transitions': []})
        cls.space.configuration.settings = settings
        cls.space.configuration.save(update_fields=['settings'])
        cls.task = make_task(user=cls.owner, workplace=cls.workspace, space=cls.space, title='Kolor etapu', status='in_progress')
        cls.item = WorkItem.objects.get(task=cls.task)
        cls.item.status = 'paused'
        cls.item.in_backlog = False
        cls.item.save(update_fields=['status', 'in_backlog'])

    def setUp(self):
        self.client.force_login(self.owner)

    def data(self, base, suffix=''):
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if base.startswith('/workplaces/') else '/api/v1/page/'
        response = self.client.get(api, {'url': base + suffix}, follow=True)
        self.assertEqual(response.status_code, 200)
        return response.json()['data']

    def test_custom_and_default_stage_colors_reach_every_space_view(self):
        for base in (f'/space/{self.space.slug}/', scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')):
            for view in ('list', 'board', 'backlog', 'timeline', 'summary', 'reports'):
                with self.subTest(base=base, view=view):
                    data = self.data(base, '?view=' + view)
                    statuses = data['summary']['statuses'] if view == 'summary' else data['reports']['statuses'] if view == 'reports' else data['columns']
                    colors = {s['key']: s['color'] for s in statuses}
                    self.assertEqual(colors['paused'], '#ee33cc')
                    self.assertEqual(colors['in_progress'], configuration_name_color('statuses', {'category': 'in_progress'}))
                    for item in data['items']:
                        if item['id'] == self.item.pk:
                            self.assertEqual(item['status_color'], '#ee33cc')
                    if view in ('list', 'board', 'summary'):
                        self.assertContains(self.client.get(base + '?view=' + view), '--tasks-status-color: #ee33cc')
            detail = self.data(base, f'tasks/{self.item.key}/')
            self.assertEqual(detail['item']['status_color'], '#ee33cc')
            self.assertEqual(next(s['color'] for s in detail['statuses'] if s['key'] == 'paused'), '#ee33cc')
            create_url = self.data(base, '?view=board')['create_item_url']
            new = self.data(create_url, ('&' if '?' in create_url else '?') + 'status=paused')
            form = new.get('form') or new['modal']['form']
            choice = next(c for f in form['fields'] if f['field_name'] == 'status' for c in f['choices'] if c['value'] == 'paused')
            self.assertEqual(choice['status_color'], '#ee33cc')

    def test_configuration_change_and_reset_are_read_without_rewriting_tasks(self):
        config = self.space.configuration
        before = deepcopy(config.settings)
        base = f'/space/{self.space.slug}/'
        for color, expected in [('#27ab91', '#27ab91'), ('', '#c18a34')]:
            config.settings['statuses'][-1]['color'] = color
            config.save(update_fields=['settings'])
            data = self.data(base, '?view=board')
            self.assertEqual(next(i['status_color'] for i in data['items'] if i['id'] == self.item.pk), expected)
            self.assertEqual(data['columns'][-1]['color'], expected)
        self.item.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.item.status, 'paused')
        self.assertEqual(self.task.status, 'in_progress')
        self.assertIsNone(self.task.completion_date)
        config.refresh_from_db()
        self.assertEqual(config.settings['statuses'][:-1], before['statuses'][:-1])

    def test_color_data_does_not_grant_access_to_another_workspace(self):
        outsider = get_user_model().objects.create_user(username='outside-colors', email='outside-colors@example.test')
        create_workplace_for_user(outsider, 'Obcy Workspace')
        self.client.force_login(outsider)
        self.assertEqual(self.client.get('/api/v1/page/', {'url': f'/space/{self.space.slug}/?view=board'}).status_code, 404)
