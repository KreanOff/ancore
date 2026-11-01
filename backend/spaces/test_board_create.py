"""Creating a task from a board column preserves its status, scope and return view."""
from datetime import date
from urllib.parse import parse_qs, urlencode, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import SpaceMembership, SpaceTask, Sprint
from .testing import make_space


class BoardCreateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='board-create-owner', email='owner@board-create.test')
        cls.member = users.objects.create_user(username='board-create-member', email='member@board-create.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Tworzenie na tablicy')
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Inny Workspace tablicy')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Kanban', template='kanban',
                               visibility='private', private_owner=cls.owner)
        cls.space_membership = SpaceMembership.objects.create(space=cls.space, user=cls.member, role='member')
        cls.scrum = make_space(user=cls.owner, workplace=cls.workspace, name='Scrum', template='scrum')
        cls.active = Sprint.objects.create(space=cls.scrum, name='Aktywny', state='active',
                                          start_on=date(2026, 11, 1), end_on=date(2026, 11, 14))
        cls.foreign_space = make_space(user=cls.owner, workplace=cls.other_workspace, name='Obca tablica')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def target(self, suffix='', *, space=None, scoped=True, **query):
        path = f'{(space or self.space).slug}/{suffix}'
        path = scoped_workplace_app_path(self.workspace, 'space', path) if scoped else '/space/' + path
        return path + '?' + urlencode({'view': 'board', **query})

    def api(self, target, scoped=True):
        base = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
        return base + '?' + urlencode({'url': target})

    def values(self, **extra):
        return {'title': 'Zadanie z kolumny', 'work_type': 'task', 'priority': 'medium', 'status': 'in_progress', **extra}

    def test_column_links_keep_board_filters_separate_from_initial_status(self):
        for scoped in (False, True):
            target = self.target(scoped=scoped, q='Raport', status='new', sort='title_desc', priority='high')
            response = self.client.get(self.api(target, scoped))
            self.assertEqual(response.status_code, 200)
            data = response.json()['data']
            self.assertTrue(data['can_edit'])
            for column in data['columns']:
                params = parse_qs(urlsplit(column['create_item_url']).query)
                self.assertEqual(params, {'view': ['board'], 'q': ['Raport'], 'status': ['new'],
                                          'sort': ['title_desc'], 'priority': ['high'],
                                          'initial_status': [column['key']]})
                form = self.client.get(self.api(column['create_item_url'], scoped)).json()['data']
                field = next(field for field in form['form']['fields'] if field['field_name'] == 'status')
                self.assertEqual(field['value'], [column['key']])
                self.assertIn(column['category'], {choice['status_category'] for choice in field['choices']})
                returned = parse_qs(urlsplit(form['return_url']).query)
                self.assertEqual(returned, {name: values for name, values in params.items() if name != 'initial_status'})

    def test_html_form_uses_board_background_and_presets_visible_status(self):
        for scoped in (False, True):
            response = self.client.get(self.target('items/create/', scoped=scoped, initial_status='closed'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['view'], 'board')
            form = response.context['modal']['form']
            self.assertEqual(form['status'].value(), 'closed')
            self.assertIn('status', [field.name for field in form.visible_fields()])
            self.assertContains(response, 'name="status"')

    def test_create_html_and_api_persist_selected_column_and_completion_with_actual_actor(self):
        settings = self.space.configuration.settings
        settings['statuses'].append({'key': 'approved', 'label': 'Zatwierdzone', 'category': 'closed', 'transitions': []})
        self.space.configuration.save()
        for scoped in (False, True):
            for api in (False, True):
                for status in ('in_progress', 'approved'):
                    with self.subTest(scoped=scoped, api=api, status=status):
                        target = self.target('items/create/', scoped=scoped, initial_status='new', q='Zadanie', sort='title_desc')
                        title = f'Zadanie {scoped} {api} {status}'
                        response = self.client.post(self.api(target, scoped) if api else target,
                                                    self.values(title=title, status=status, user=self.member.pk,
                                                                workplace=self.other_workspace.pk, space=self.foreign_space.pk))
                        self.assertEqual(response.status_code, 200 if api else 302)
                        task = SpaceTask.objects.get(title=title)
                        self.assertEqual((task.space_id, task.space.user_id, task.space.workplace_id),
                                         (self.space.pk, self.owner.pk, self.workspace.pk))
                        self.assertEqual(task.created_by_id, self.member.pk)
                        self.assertEqual(task.work_item.status, status)
                        self.assertEqual(task.status, 'closed' if status == 'approved' else status)
                        self.assertEqual(task.is_completed, status == 'approved')
                        self.assertEqual(task.completion_date is not None, status == 'approved')
                        self.assertFalse(task.work_item.in_backlog)
                        self.assertEqual(task.activities.get().action, 'created')
                        self.assertEqual(task.activities.get().actor_id, self.member.pk)
                        self.assertTrue(task.work_item.key.startswith(self.space.key + '-'))
                        returned = response.json()['redirect'] if api else response['Location']
                        self.assertEqual(parse_qs(urlsplit(returned).query),
                                         {'view': ['board'], 'q': ['Zadanie'], 'sort': ['title_desc']})
                        board = self.client.get(self.api(returned)).json()['data']
                        self.assertIn(task.pk, [item['task_id'] for item in board['items']])

    def test_invalid_fields_and_removed_status_keep_form_without_creating_task(self):
        target = self.target('items/create/', initial_status='in_progress')
        for values in (self.values(title=''), self.values(status=''), self.values(status='other-space-status')):
            response = self.client.post(self.api(target), values)
            self.assertEqual(response.status_code, 400)
            self.assertTrue(any(field['errors'] for field in response.json()['data']['form']['fields']))
            self.assertEqual(SpaceTask.objects.count(), 0)
        fields = self.client.post(self.api(target), self.values(title='')).json()['data']['form']['fields']
        self.assertEqual(next(field for field in fields if field['field_name'] == 'status')['value'], ['in_progress'])
        config = self.space.configuration
        config.settings['statuses'].append({'key': 'temporary', 'label': 'Tymczasowy', 'category': 'new', 'transitions': []})
        config.save()
        target = self.target('items/create/', initial_status='temporary')
        self.assertEqual(self.client.get(self.api(target)).status_code, 200)
        config.settings['statuses'] = [status for status in config.settings['statuses'] if status['key'] != 'temporary']
        config.save()
        self.assertEqual(self.client.post(self.api(target), self.values(status='temporary')).status_code, 400)
        self.assertEqual(SpaceTask.objects.count(), 0)

    def test_scrum_columns_target_active_sprint_and_created_task_is_visible(self):
        target = self.target(space=self.scrum)
        data = self.client.get(self.api(target)).json()['data']
        create_url = data['columns'][1]['create_item_url']
        self.assertEqual(parse_qs(urlsplit(create_url).query)['planning_sprint'], [str(self.active.pk)])
        form = self.client.get(self.api(create_url)).json()['data']
        fields = {field['field_name']: field for field in form['form']['fields']}
        self.assertEqual(fields['sprint']['value'], [str(self.active.pk)])
        self.assertFalse(fields['in_backlog']['value'])
        response = self.client.post(self.api(create_url), self.values(sprint=self.active.pk))
        self.assertEqual(response.status_code, 200)
        task = SpaceTask.objects.get()
        self.assertEqual(task.work_item.sprint_id, self.active.pk)
        self.assertFalse(task.work_item.in_backlog)
        board = self.client.get(self.api(response.json()['redirect'])).json()['data']
        self.assertEqual([item['task_id'] for item in board['items']], [task.pk])
        self.assertNotIn('planning_sprint', parse_qs(urlsplit(response.json()['redirect']).query))

    def test_scrum_without_active_sprint_has_no_column_creation_and_rejects_stale_sprint(self):
        create_url = self.client.get(self.api(self.target(space=self.scrum))).json()['data']['columns'][0]['create_item_url']
        self.active.state = 'closed'
        self.active.save()
        board = self.client.get(self.api(self.target(space=self.scrum))).json()['data']
        self.assertTrue(all(not column['create_item_url'] for column in board['columns']))
        self.assertEqual(self.client.get(self.api(create_url)).status_code, 404)
        self.assertEqual(self.client.post(self.api(create_url), self.values(sprint=self.active.pk)).status_code, 404)
        foreign = Sprint.objects.create(space=self.foreign_space, name='Obcy sprint', state='active',
                                        start_on=date(2026, 11, 1), end_on=date(2026, 11, 14))
        target = self.target('items/create/', space=self.scrum, planning_sprint=foreign.pk)
        self.assertEqual(self.client.get(self.api(target)).status_code, 404)
        self.assertEqual(SpaceTask.objects.count(), 0)

    def test_observer_guest_revoked_and_foreign_space_cannot_create(self):
        self.space_membership.role = 'observer'
        self.space_membership.save()
        for role, expected in (('observer', 403), ('guest', 403), ('revoked', 404)):
            if role == 'guest':
                self.space_membership.role = 'member'
                self.space_membership.save()
                self.membership.role = 'guest'
                self.membership.save()
            elif role == 'revoked':
                self.membership.role = 'member'
                self.membership.save()
                self.space_membership.delete()
            for scoped in (False, True):
                for api in (False, True):
                    target = self.target('items/create/', scoped=scoped, initial_status='closed')
                    target = self.api(target, scoped) if api else target
                    self.assertEqual(self.client.get(target, follow=True).status_code, expected)
                    self.assertEqual(self.client.post(target, self.values()).status_code, expected)
                if role != 'revoked':
                    board = self.client.get(self.api(self.target(scoped=scoped), scoped), follow=True).json()['data']
                    self.assertFalse(board['can_edit'])
                    self.assertTrue(all(not column['create_item_url'] for column in board['columns']))
        for scoped in (False, True):
            target = self.target('items/create/', space=self.foreign_space, scoped=scoped)
            self.assertEqual(self.client.post(self.api(target, scoped), self.values()).status_code, 404)
        self.assertEqual(SpaceTask.objects.count(), 0)

    def test_ordinary_create_keeps_original_default_status(self):
        target = self.target('items/create/', view='list')
        form = self.client.get(self.api(target)).json()['data']['form']
        self.assertNotIn('status', [field['field_name'] for field in form['fields']])
        values = self.values()
        values.pop('status')
        response = self.client.post(self.api(target), values)
        self.assertEqual(response.status_code, 200)
        task = SpaceTask.objects.get()
        self.assertEqual((task.status, task.work_item.status), ('new', 'new'))
