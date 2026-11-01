"""The workflow editor preserves old clients and defines usable flow boundaries."""
from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from spaces.defaults import TEMPLATES, status_flow_stage, template_settings
from spaces.forms import ItemForm, StatusForm, SubtaskForm
from spaces.models import WorkItem
from spaces.testing import make_space, make_task
from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class KanbanConfigurationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='kanban-process', email='process@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Proces')
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Kanban', template='kanban')

    def setUp(self):
        self.client.force_login(self.owner)
        self.url = scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/configuration/?section=statuses')
        self.api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')

    def payload(self):
        data = self.client.get(self.api, {'url': self.url}).json()['data']
        values = {'revision': data['revision'], 'configuration_section': 'statuses'}
        for group in data['sets']:
            for schema in [group['management'], *group['forms']]:
                for field in schema['fields']:
                    if field['type'] == 'checkbox':
                        if field['checked']:
                            values[field['name']] = 'on'
                    elif field.get('multiple') and not field['value']:
                        continue
                    else:
                        values[field['name']] = field['value'] or ''
        return values

    def test_status_editor_and_native_fallback_expose_flow_metadata(self):
        for scoped in (False, True):
            url = self.url if scoped else f'/space/{self.space.slug}/configuration/?section=statuses'
            response = self.client.get(url + '&edit=1')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['editor'], {'section': 'statuses', 'index': 1, 'remove': False})
            self.assertContains(response, 'Proces pracy')
            for field in ('key', 'label', 'category', 'flow_stage', 'wip_limit', 'policy', 'transitions'):
                self.assertContains(response, f'name="statuses-1-{field}"', count=1)

    def test_new_templates_start_with_directional_workflow(self):
        expected = {'new': ['in_progress'], 'in_progress': ['resolved'], 'resolved': ['closed'],
                    'closed': ['reopened'], 'reopened': ['in_progress']}
        for template in TEMPLATES:
            with self.subTest(template=template):
                self.assertEqual({row['key']: row['transitions'] for row in template_settings(template)['statuses']}, expected)

    def test_board_positions_round_trip_and_hidden_fields_are_not_table_columns(self):
        payload = self.payload()
        payload.update({'statuses-1-position_x': '320', 'statuses-1-position_y': '0'})
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.space.configuration.refresh_from_db()
        row = self.space.configuration.settings['statuses'][1]
        self.assertEqual(row['position'], {'x': 320, 'y': 0})
        self.assertNotIn('position_x', row)
        data = self.client.get(self.api, {'url': self.url}).json()['data']
        group = next(group for group in data['sets'] if group['key'] == 'statuses')
        fields = {field['field_name']: field for field in group['forms'][1]['fields']}
        headers = next(group for group in self.client.get(self.url).context['sets'] if group['key'] == 'statuses')['headers']
        for name, value in [('position_x', 320), ('position_y', 0)]:
            self.assertEqual(fields[name]['value'], str(value))
            self.assertTrue(fields[name]['hidden'])
            self.assertNotIn(name, [header['key'] for header in headers])

    def test_old_clients_preserve_board_positions_and_existing_transitions(self):
        config = self.space.configuration
        config.settings['statuses'][0].update(position={'x': 0, 'y': 200}, transitions=['closed', 'in_progress'])
        config.save(update_fields=['settings'])
        before = deepcopy(config.settings['statuses'])
        payload = {name: value for name, value in self.payload().items()
                   if not name.endswith(('-position_x', '-position_y'))}
        payload.update(configuration_section='types', **{'types-0-label': 'Praca'})
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        config.refresh_from_db()
        self.assertEqual(config.settings['statuses'], before)

    def test_invalid_board_positions_reject_whole_snapshot(self):
        before = deepcopy(self.space.configuration.settings)
        for x, y in [('-1', '0'), ('20001', '0'), ('5.5', '0'), ('0', ''), ('', '20')]:
            with self.subTest(x=x, y=y):
                payload = self.payload()
                payload.update({'statuses-1-position_x': x, 'statuses-1-position_y': y})
                self.assertEqual(self.client.post(self.url, payload).status_code, 400)
                self.space.configuration.refresh_from_db()
                self.assertEqual(self.space.configuration.settings, before)

    def test_position_write_retains_revision_conflict_protection(self):
        stale = self.payload()
        latest = self.payload()
        latest.update({'statuses-0-position_x': '40', 'statuses-0-position_y': '80'})
        self.assertEqual(self.client.post(self.url, latest).status_code, 302)
        stale.update({'statuses-0-position_x': '120', 'statuses-0-position_y': '160'})
        self.assertContains(self.client.post(self.url, stale), 'Konfiguracja zmieniła się', status_code=400)
        self.space.configuration.refresh_from_db()
        self.assertEqual(self.space.configuration.settings['statuses'][0]['position'], {'x': 40, 'y': 80})

    def test_three_stage_workflow_does_not_require_all_task_categories(self):
        payload = self.payload()
        payload.update({'statuses-2-DELETE': 'on', 'statuses-4-DELETE': 'on',
                        'statuses-0-transitions': ['in_progress'], 'statuses-1-transitions': ['closed'],
                        'statuses-3-transitions': ['new'], 'statuses-1-wip_limit': '3',
                        'statuses-1-policy': 'Rozpoczynamy po uzgodnieniu zakresu; kończymy po weryfikacji.'})
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.space.configuration.refresh_from_db()
        statuses = self.space.configuration.settings['statuses']
        self.assertEqual([row['key'] for row in statuses], ['new', 'in_progress', 'closed'])
        self.assertEqual([status_flow_stage(row) for row in statuses], ['queue', 'active', 'done'])
        self.assertEqual(statuses[1]['wip_limit'], 3)
        self.assertEqual(statuses[1]['policy'], payload['statuses-1-policy'])

    def test_legacy_full_formset_preserves_saved_kanban_metadata(self):
        config = self.space.configuration
        config.settings['statuses'][1].update(wip_limit=4, policy='Gotowe do rozpoczęcia.')
        config.save(update_fields=['settings'])
        before = deepcopy(config.settings)
        payload = {name: value for name, value in self.payload().items()
                   if not name.endswith(('-flow_stage', '-wip_limit', '-policy'))}
        payload['configuration_section'] = 'types'
        payload['types-0-label'] = 'Praca'
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        config.refresh_from_db()
        self.assertEqual(config.settings['statuses'], before['statuses'])
        self.assertEqual(config.settings['types'][0]['label'], 'Praca')

    def test_invalid_flow_settings_keep_snapshot_and_return_field_errors(self):
        before = deepcopy(self.space.configuration.settings)
        for field, value, index in [('wip_limit', '0', 1), ('wip_limit', '2', 0),
                                    ('flow_stage', 'done', 1), ('flow_stage', 'active', 3),
                                    ('policy', 'x' * 1001, 1)]:
            with self.subTest(field=field, value=value):
                payload = self.payload()
                payload[f'statuses-{index}-{field}'] = value
                response = self.client.post(self.api, payload, QUERY_STRING='url=' + self.url)
                self.assertEqual(response.status_code, 400)
                data = response.json()['data']
                status_set = next(group for group in data['sets'] if group['key'] == 'statuses')
                actual = next(item for item in status_set['forms'][index]['fields'] if item['field_name'] == field)
                self.assertTrue(actual['errors'])
                self.space.configuration.refresh_from_db()
                self.assertEqual(self.space.configuration.settings, before)

    def test_missing_queue_is_rejected_and_used_status_cannot_change_boundary(self):
        payload = self.payload()
        payload['statuses-0-flow_stage'] = 'active'
        self.assertContains(self.client.post(self.url, payload), 'Proces pracy wymaga', status_code=400)
        task = make_task(user=self.owner, workplace=self.workspace, space=self.space, title='Rozpoczęte')
        item = WorkItem.objects.get(task=task)
        item.status = 'in_progress'
        item.save(update_fields=['status'])
        payload = self.payload()
        payload['statuses-1-flow_stage'] = 'queue'
        self.assertContains(self.client.post(self.url, payload), 'przed zmianą etapu przepływu', status_code=400)

    def test_new_status_can_be_referenced_in_same_snapshot(self):
        payload = self.payload()
        payload.update({'statuses-5-key': 'review', 'statuses-5-label': 'Weryfikacja',
                        'statuses-5-category': 'in_progress', 'statuses-5-flow_stage': 'active',
                        'statuses-5-wip_limit': '2', 'statuses-5-transitions': ['closed'],
                        'statuses-1-transitions': ['review']})
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.space.configuration.refresh_from_db()
        self.assertEqual(self.space.configuration.settings['statuses'][1]['transitions'], ['review'])
        self.assertEqual(self.space.configuration.settings['statuses'][-1]['key'], 'review')

    def test_old_status_read_does_not_mutate_configuration_before_revision(self):
        statuses = [{'key': 'new', 'category': 'new', 'label': 'Kolejka', 'transitions': []}]
        before = deepcopy(statuses)
        form = StatusForm(initial=statuses[0], statuses=statuses)
        self.assertEqual(form['flow_stage'].value(), 'queue')
        self.assertEqual(statuses, before)

    def test_new_tasks_use_queue_after_reordering_without_new_category(self):
        config = self.space.configuration
        config.settings['statuses'] = [
            {'key': 'working', 'label': 'Praca', 'category': 'in_progress', 'flow_stage': 'active', 'transitions': ['done']},
            {'key': 'done', 'label': 'Gotowe', 'category': 'closed', 'flow_stage': 'done', 'transitions': ['waiting']},
            {'key': 'waiting', 'label': 'Kolejka', 'category': 'reopened', 'flow_stage': 'queue', 'transitions': ['working']},
        ]
        config.save(update_fields=['settings'])
        request = RequestFactory().get('/')
        request.user, request.workplace = self.owner, self.workspace
        item = ItemForm(request=request, space=self.space, initial_status='invalid')
        child = SubtaskForm(request=request, space=self.space)
        self.assertEqual(item['status'].value(), 'waiting')
        self.assertEqual(child['status'].value(), 'waiting')
        task = make_task(user=self.owner, workplace=self.workspace, space=self.space, title='Kolejka')
        self.assertEqual(WorkItem.objects.get(task=task).status, 'waiting')
