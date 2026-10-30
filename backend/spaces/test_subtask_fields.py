"""The subtask dialog exposes and persists its own nine issue properties."""
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from tasks.models import TaskTag
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from . import test_independent_tasks as fixtures
from .defaults import TEMPLATES
from .models import SpaceTask, SpaceTaskMembership, Sprint, Team
from .testing import make_space


class SubtaskFieldsTests(TestCase):
    fields = ['title', 'description', 'status', 'priority', 'assignee', 'work_type',
              'start_at', 'due_at', 'points']

    @classmethod
    def setUpTestData(cls):
        fixtures.IndependentTaskTests.setUpTestData.__func__(cls)
        cls.child = SpaceTask.objects.create(space=cls.space, parent=cls.task, title='Podzadanie', created_by=cls.owner)
        cls.outsider = get_user_model().objects.create_user(username='subtask-outsider', email='outsider@example.test')
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Inny Workspace')
        WorkplaceMembership.objects.create(workplace=cls.other_workspace, user=cls.outsider)

    login = fixtures.IndependentTaskTests.login

    def setUp(self):
        self.login(self.owner)

    def target(self, task=None, suffix='', scoped=True):
        task = task or self.task
        path = f'{task.space.slug}/tasks/{task.work_item.key}/{suffix}'
        return scoped_workplace_app_path(self.workspace, 'space', path) if scoped else '/space/' + path

    def api(self, target, scoped=True):
        path = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
        return path + '?' + urlencode({'url': target})

    def values(self, **extra):
        return {
            'title': 'Pełne podzadanie', 'description': 'Opis do wykonania', 'status': 'in_progress',
            'priority': 'urgent', 'assignee': str(self.member.pk), 'work_type': 'bug',
            'start_at': '2026-11-02T09:15', 'due_at': '2026-11-04T16:45', 'points': '8',
            **extra,
        }

    def create_values(self, **extra):
        return {'action': 'create_subtask_modal', **{
            'subtask-' + name: value for name, value in self.values(**extra).items()
        }}

    def assert_saved(self, child, values):
        child.refresh_from_db()
        item = child.work_item
        self.assertEqual(child.title, values['title'])
        self.assertEqual(child.description, values['description'])
        self.assertEqual(child.priority, values['priority'])
        self.assertEqual(child.assignee_id, int(values['assignee']) if values['assignee'] else None)
        self.assertEqual(item.status, values['status'])
        self.assertEqual(item.work_type, values['work_type'])
        self.assertEqual(item.points, int(values['points']) if values['points'] else None)
        for actual, value in [(item.start_at, values['start_at']), (child.due_at, values['due_at'])]:
            self.assertEqual(timezone.localtime(actual).strftime('%Y-%m-%dT%H:%M') if actual else '', value)

    def test_create_and_edit_schemas_have_nine_visible_fields_in_every_template(self):
        labels = ['Tytuł', 'Opis', 'Status', 'Priorytet', 'Wykonawca', 'Typ zgłoszenia',
                  'Data rozpoczęcia', 'Termin zakończenia', 'Estymacja (punkty)']
        for template in TEMPLATES:
            space = make_space(user=self.owner, workplace=self.workspace, name='Pola ' + template,
                               template=template, kind=TEMPLATES[template]['kind'])
            parent = SpaceTask.objects.create(space=space, title='Rodzic', created_by=self.owner)
            child = SpaceTask.objects.create(space=space, parent=parent, title='Potomek', created_by=self.owner)
            for scoped in [False, True]:
                for task, suffix, form_key in [(parent, '?tab=subtasks', 'subtask_form'), (child, 'edit/', 'form')]:
                    with self.subTest(template=template, scoped=scoped, form=form_key):
                        target = self.target(task, suffix, scoped)
                        response = self.client.get(self.api(target, scoped), follow=True)
                        self.assertEqual(response.status_code, 200)
                        schema = response.json()['data'][form_key]
                        visible = [field for field in schema['fields'] if not field['hidden']]
                        self.assertEqual([field['field_name'] for field in visible], self.fields)
                        self.assertEqual([field['label'] for field in visible], labels)
                        fields = {field['field_name']: field for field in visible}
                        priorities = {choice['value']: choice['priority'] for choice in fields['priority']['choices']}
                        self.assertEqual({key: priorities[key] for key in ['none', 'medium', 'high']},
                                         {'none': 'none', 'medium': 'medium', 'high': 'high'})
                        statuses = {choice['value']: choice['status_category'] for choice in fields['status']['choices']}
                        self.assertEqual(statuses['new'], 'new')
                        self.assertEqual(statuses['closed'], 'closed')
                        assignees = {choice['value'] for choice in fields['assignee']['choices']}
                        self.assertIn(str(self.member.pk), assignees)
                        self.assertNotIn(str(self.outsider.pk), assignees)
                        response = self.client.get(target, follow=True)
                        self.assertEqual(response.status_code, 200)
                        form = response.context[form_key]
                        self.assertEqual([field.name for field in form.visible_fields()], self.fields)
                        for field in form.visible_fields():
                            self.assertContains(response, 'name="' + field.html_name + '"')

    def test_create_persists_all_fields_in_html_and_api_with_plain_and_scoped_urls(self):
        for scoped in [False, True]:
            for use_api in [False, True]:
                with self.subTest(scoped=scoped, use_api=use_api):
                    target = self.target(suffix='?tab=subtasks', scoped=scoped)
                    title = f'Nowe {scoped} {use_api}'
                    response = self.client.post(self.api(target, scoped) if use_api else target,
                                                self.create_values(title=title))
                    self.assertEqual(response.status_code, 200 if use_api else 302)
                    child = self.task.subtasks.get(title=title)
                    self.assert_saved(child, self.values(title=title))
                    self.assertEqual((child.visibility, child.private_owner_id), ('private', self.owner.pk))
                    self.assertEqual(child.created_by_id, self.owner.pk)
                    self.assertTrue(self.task.activities.filter(action='subtask_created', actor=self.owner,
                                                               metadata__subtask_pk=child.pk).exists())
                    schema = self.client.get(self.api(self.target(child, 'edit/'), scoped)).json()['data']['form']
                    fields = {field['field_name']: field for field in schema['fields']}
                    self.assertEqual(fields['points']['value'], '8')
                    self.assertEqual(fields['work_type']['value'], ['bug'])
                    self.assertEqual(fields['assignee']['value'], [str(self.member.pk)])

    def test_points_persist_for_non_scrum_subtasks(self):
        for template in ['kanban', 'tasks', 'marketing', 'recruitment', 'service']:
            with self.subTest(template=template):
                space = make_space(user=self.owner, workplace=self.workspace, name='Estymacja ' + template,
                                   template=template, kind=TEMPLATES[template]['kind'])
                parent = SpaceTask.objects.create(space=space, title='Rodzic', created_by=self.owner)
                response = self.client.post(self.api(self.target(parent)), self.create_values(points='0'))
                self.assertEqual(response.status_code, 200)
                child = parent.subtasks.get()
                self.assertEqual(child.work_item.points, 0)
                response = self.client.post(self.api(self.target(child, 'edit/')), self.values(points='13'))
                self.assertEqual(response.status_code, 200)
                child.refresh_from_db()
                self.assertEqual(child.work_item.points, 13)

    def test_edit_updates_only_visible_fields_and_preserves_other_properties(self):
        tag = TaskTag.objects.create(user=self.owner, workplace=self.workspace, space=self.space, name='Zachowany tag')
        self.child.tags.add(tag)
        reminder = timezone.now().replace(microsecond=0) + timedelta(days=1)
        self.child.task_type, self.child.reminder_at = 'meeting', reminder
        self.child.visibility, self.child.private_owner = 'private', self.owner
        self.child.save()
        membership = SpaceTaskMembership.objects.create(task=self.child, user=self.member, role='observer')
        team = Team.objects.create(workplace=self.workspace, owner=self.owner, created_by=self.owner, name='Odłączony zespół')
        sprint = Sprint.objects.create(space=self.space, name='Zamknięty sprint', state='closed',
                                       start_on='2026-09-01', end_on='2026-09-14')
        epic = SpaceTask.objects.create(space=self.space, title='Epik', created_by=self.owner).work_item
        epic.work_type = 'epic'
        epic.save()
        item = self.child.work_item
        item.team, item.sprint, item.epic, item.in_backlog = team, sprint, epic, True
        item.custom_values = {'existing': 'Zachowana wartość', 'legacy': 'Dawna wartość'}
        item.save()
        original_key = item.key
        settings = self.config.settings
        settings['fields'] = [{'key': 'existing', 'label': 'Pole wymagane', 'type': 'text', 'required': True}]
        self.config.settings = settings
        self.config.save()
        for scoped in [False, True]:
            for use_api in [False, True]:
                with self.subTest(scoped=scoped, use_api=use_api):
                    target = self.target(self.child, 'edit/', scoped)
                    # Even manually supplied hidden-away properties are not part of this editor.
                    values = self.values(title=f'Edycja {scoped} {use_api}')
                    response = self.client.post(self.api(target, scoped) if use_api else target, {
                        **values, 'tags': [], 'team': '', 'sprint': '', 'epic': '', 'in_backlog': '',
                        'task_type': 'general', 'reminder_at': '', 'visibility': 'public', 'custom_existing': 'Podmiana',
                    })
                    self.assertEqual(response.status_code, 200 if use_api else 302)
                    self.assert_saved(self.child, values)
                    self.assertEqual(list(self.child.tags.all()), [tag])
                    self.assertEqual((self.child.task_type, self.child.reminder_at), ('meeting', reminder))
                    self.assertEqual((self.child.visibility, self.child.private_owner_id), ('private', self.owner.pk))
                    self.assertTrue(self.child.memberships.filter(pk=membership.pk).exists())
                    item = self.child.work_item
                    self.assertEqual((item.team_id, item.sprint_id, item.epic_id, item.in_backlog),
                                     (team.pk, sprint.pk, epic.pk, True))
                    self.assertEqual(item.custom_values, {'existing': 'Zachowana wartość', 'legacy': 'Dawna wartość'})
                    self.assertEqual((item.key, self.child.parent_id), (original_key, self.task.pk))

    def test_invalid_create_fields_preserve_draft_without_creating_task(self):
        invalid_values = [
            ('title', ''), ('priority', 'invalid'), ('assignee', str(self.outsider.pk)),
            ('work_type', 'not-configured'), ('status', 'not-configured'), ('points', '-1'),
            ('points', '10001'), ('points', '1.5'), ('start_at', '2026-11-02'),
            ('start_at', '2026-03-29T02:30'), ('start_at', '2026-10-25T02:30'),
            ('due_at', '2026-11-01T10:00'), ('due_at', 'invalid'),
        ]
        initial_count = self.task.subtasks.count()
        for name, value in invalid_values:
            with self.subTest(name=name, value=value):
                response = self.client.post(self.api(self.target()), self.create_values(**{name: value}))
                self.assertEqual(response.status_code, 400)
                schema = response.json()['data']['subtask_form']
                fields = {field['field_name']: field for field in schema['fields']}
                self.assertTrue(fields[name]['errors'])
                self.assertEqual(fields['description']['value'], 'Opis do wykonania')
                self.assertEqual(fields['points']['name'], 'subtask-points')
                self.assertEqual(self.task.subtasks.count(), initial_count)

    def test_invalid_edit_is_atomic_and_allowed_status_preserves_completion_history(self):
        target = self.api(self.target(self.child, 'edit/'))
        for name, value in [('assignee', str(self.outsider.pk)), ('points', '-1'),
                            ('work_type', 'not-configured'), ('due_at', '2026-11-01T10:00')]:
            with self.subTest(name=name):
                response = self.client.post(target, self.values(status='closed', **{name: value}))
                self.assertEqual(response.status_code, 400)
                fields = {field['field_name']: field for field in response.json()['data']['form']['fields']}
                self.assertTrue(fields[name]['errors'])
                self.child.refresh_from_db()
                self.assertEqual((self.child.title, self.child.status), ('Podzadanie', 'new'))
                self.assertFalse(self.child.is_completed)
                self.assertFalse(self.child.activities.filter(action='status_changed').exists())
        response = self.client.post(target, self.values(status='closed'))
        self.assertEqual(response.status_code, 200)
        self.child.refresh_from_db()
        self.assertTrue(self.child.is_completed)
        self.assertIsNotNone(self.child.completion_date)
        self.assertTrue(self.child.activities.filter(action='status_changed', actor=self.owner).exists())
        response = self.client.post(target, self.values(status='reopened', assignee='', points='', start_at='', due_at=''))
        self.assertEqual(response.status_code, 200)
        self.assert_saved(self.child, self.values(status='reopened', assignee='', points='', start_at='', due_at=''))
        self.assertIsNone(self.child.completion_date)

    def test_create_uses_configured_status_category_and_member_as_author(self):
        settings = self.config.settings
        settings['statuses'].append({'key': 'delivered', 'label': 'Dostarczone', 'category': 'closed', 'transitions': ['new']})
        self.config.settings = settings
        self.config.save()
        self.login(self.member)
        schema = self.client.get(self.api(self.target())).json()['data']['subtask_form']
        status = next(field for field in schema['fields'] if field['field_name'] == 'status')
        delivered = next(choice for choice in status['choices'] if choice['value'] == 'delivered')
        self.assertEqual(delivered['status_category'], 'closed')
        response = self.client.post(self.api(self.target()), self.create_values(status='delivered', assignee=str(self.observer.pk)))
        self.assertEqual(response.status_code, 200)
        child = self.task.subtasks.get(title='Pełne podzadanie')
        self.assertEqual((child.status, child.work_item.status), ('closed', 'delivered'))
        self.assertTrue(child.is_completed)
        self.assertIsNotNone(child.completion_date)
        self.assertEqual((child.created_by_id, child.private_owner_id), (self.member.pk, self.member.pk))
        self.login(self.observer)
        # Assignment does not grant access to a newly private subtask.
        self.assertEqual(self.client.get(self.api(self.target(child, 'edit/'))).status_code, 404)

    def test_type_change_respects_existing_epic_relations(self):
        epic = SpaceTask.objects.create(space=self.space, title='Epik nadrzędny', created_by=self.owner).work_item
        epic.work_type = 'epic'
        epic.save()
        item = self.child.work_item
        item.epic = epic
        item.save()
        target = self.api(self.target(self.child, 'edit/'))
        response = self.client.post(target, self.values(work_type='epic'))
        self.assertEqual(response.status_code, 400)
        fields = {field['field_name']: field for field in response.json()['data']['form']['fields']}
        self.assertTrue(fields['work_type']['errors'])
        item.refresh_from_db()
        self.assertEqual((item.work_type, item.epic_id), ('task', epic.pk))
        item.epic, item.work_type = None, 'epic'
        item.save()
        related = SpaceTask.objects.create(space=self.space, title='Praca w epiku', created_by=self.owner).work_item
        related.epic = item
        related.save()
        response = self.client.post(target, self.values(work_type='bug'))
        self.assertEqual(response.status_code, 400)
        fields = {field['field_name']: field for field in response.json()['data']['form']['fields']}
        self.assertTrue(fields['work_type']['errors'])
        item.refresh_from_db()
        self.assertEqual(item.work_type, 'epic')

    def test_parent_access_and_workspace_scope_protect_create_and_edit(self):
        initial_count = self.task.subtasks.count()
        self.login(self.observer)
        for target, values in [(self.target(), self.create_values()), (self.target(self.child, 'edit/'), self.values())]:
            self.assertEqual(self.client.post(self.api(target), values).status_code, 403)
        self.task.visibility, self.task.private_owner = 'private', self.owner
        self.task.save()
        self.login(self.member)
        for task, suffix, values in [(self.task, '', self.create_values()), (self.child, 'edit/', self.values())]:
            self.assertEqual(self.client.post(self.api(self.target(task, suffix)), values).status_code, 404)
        self.login(self.owner)
        for task, suffix, values in [(self.task, '', self.create_values()), (self.child, 'edit/', self.values())]:
            wrong_workspace = self.target(task, suffix).replace(self.workspace.slug, self.other_workspace.slug)
            self.assertEqual(self.client.post(wrong_workspace, values).status_code, 404)
        self.assertEqual(self.task.subtasks.count(), initial_count)
        self.child.refresh_from_db()
        self.assertEqual(self.child.title, 'Podzadanie')

    def test_quick_create_and_older_modal_payloads_retain_defaults(self):
        response = self.client.post(self.target(), {'action': 'subtask', 'title': 'Szybkie podzadanie'})
        self.assertEqual(response.status_code, 302)
        quick = self.task.subtasks.get(title='Szybkie podzadanie')
        self.assertEqual((quick.visibility, quick.priority, quick.work_item.work_type), ('public', 'medium', 'task'))
        response = self.client.post(self.target(), {
            'action': 'create_subtask_modal', 'subtask-title': 'Starszy modal', 'subtask-description': 'Opis',
            'subtask-status': 'new', 'subtask-visibility': 'public',
        })
        self.assertEqual(response.status_code, 302)
        older = self.task.subtasks.get(title='Starszy modal')
        self.assertEqual((older.visibility, older.priority, older.work_item.work_type), ('public', 'medium', 'task'))
