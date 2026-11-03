"""Space dictionaries classify tasks without changing ownership or workflow."""
from copy import deepcopy
import json
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import Space, SpaceMembership, SpaceTask
from .testing import make_space


class TaskClassificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='classification-owner', email='classification-owner@example.test')
        cls.member = users.objects.create_user(username='classification-member', email='classification-member@example.test')
        cls.observer = users.objects.create_user(username='classification-observer', email='classification-observer@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Klasyfikacja')
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Inny Workspace')
        for person in (cls.member, cls.observer):
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=person)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Zadania',
                               visibility='private', private_owner=cls.owner)
        SpaceMembership.objects.create(space=cls.space, user=cls.member, role='member')
        SpaceMembership.objects.create(space=cls.space, user=cls.observer, role='observer')
        cls.task = SpaceTask.objects.create(space=cls.space, title='Zadanie', created_by=cls.owner)

    def setUp(self):
        self.login(self.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def target(self, suffix='', scoped=True, space=None, workspace=None):
        space = space or self.space
        path = f'{space.slug}/{suffix}'
        return (scoped_workplace_app_path(workspace or self.workspace, 'space', path)
                if scoped else '/space/' + path)

    def task_target(self, task=None, suffix='', scoped=True, workspace=None):
        task = task or self.task
        return self.target(f'tasks/{task.work_item.key}/{suffix}', scoped, task.space, workspace)

    def api(self, target, scoped=True, workspace=None):
        endpoint = (scoped_workplace_app_path(workspace or self.workspace, 'api', 'v1/page/')
                    if scoped else '/api/v1/page/')
        return endpoint + '?' + urlencode({'url': target})

    def configuration_target(self, section='categories', scoped=True):
        return self.target('configuration/?section=' + section, scoped)

    def configuration_payload(self, section='categories', scoped=True):
        response = self.client.get(self.api(self.configuration_target(section, scoped), scoped))
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        values = {'revision': data['revision'], 'configuration_section': section}
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

    def configure(self):
        config = self.space.configuration
        config.settings['categories'] = [
            {'key': 'general', 'label': 'Ogólne'},
            {'key': 'billing', 'label': 'Rozliczenia', 'icon': 'square-check', 'color': '#a153cc', 'description': 'Obsługa faktur'},
        ]
        config.settings['groups'] = [
            {'key': 'support', 'label': 'Wsparcie', 'color': '#2a9d8f'},
            {'key': 'sales', 'label': 'Sprzedaż'},
        ]
        config.save(update_fields=['settings'])
        return config

    def values(self, **overrides):
        return {'title': 'Zadanie po zmianie', 'description': 'Opis zadania', 'priority': 'high',
                'work_type': 'task', 'task_type': 'billing', 'task_group': 'support', **overrides}

    def autosave(self, fields, scoped=True, use_api=False, **values):
        target = self.task_target(scoped=scoped)
        return self.client.post(self.api(target, scoped) if use_api else target,
                                {'action': 'save', 'autosave_fields': json.dumps(fields), **values},
                                HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_existing_configuration_uses_original_categories_and_empty_groups(self):
        config = self.space.configuration
        config.settings.pop('categories', None)
        config.settings.pop('groups', None)
        config.save(update_fields=['settings'])
        for scoped in (False, True):
            data = self.client.get(self.api(self.task_target(scoped=scoped), scoped)).json()['data']
            fields = {field['field_name']: field for field in data['form']['fields']}
            self.assertEqual(fields['task_type']['label'], 'Kategoria')
            self.assertEqual(fields['task_group']['label'], 'Grupa')
            self.assertEqual({choice['value']: choice['label'] for choice in fields['task_type']['choices']},
                             dict(SpaceTask.TASK_TYPE_CHOICES))
            self.assertEqual([choice['value'] for choice in fields['task_group']['choices']], [''])
            self.assertFalse(fields['task_group']['required'])
            self.assertEqual(data['item']['task_type_label'], 'Ogólne')
            self.assertEqual(data['item']['task_group'], '')
            native = self.client.get(self.task_target(scoped=scoped))
            self.assertContains(native, 'name="task_type"', count=1)
            self.assertContains(native, 'name="task_group"', count=1)
        config.refresh_from_db()
        self.assertNotIn('categories', config.settings)
        self.assertNotIn('groups', config.settings)

    def test_dictionaries_create_edit_and_round_trip_with_existing_configuration(self):
        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                config = self.space.configuration
                before = deepcopy(config.settings)
                payload = self.configuration_payload(scoped=scoped)
                category_index = int(payload['categories-INITIAL_FORMS'])
                group_index = int(payload['groups-INITIAL_FORMS'])
                suffix = 'scoped' if scoped else 'plain'
                payload.update({
                    f'categories-{category_index}-key': 'billing_' + suffix,
                    f'categories-{category_index}-label': 'Rozliczenia ' + suffix,
                    f'categories-{category_index}-description': 'Obsługa faktur',
                    f'categories-{category_index}-icon': 'square-check',
                    f'categories-{category_index}-color': '#A153CC',
                    f'groups-{group_index}-key': 'support_' + suffix,
                    f'groups-{group_index}-label': 'Wsparcie ' + suffix,
                })
                target = self.configuration_target(scoped=scoped)
                response = self.client.post(self.api(target, scoped), payload)
                self.assertEqual(response.status_code, 200, response.content)
                config.refresh_from_db()
                category = next(row for row in config.settings['categories'] if row['key'] == 'billing_' + suffix)
                self.assertEqual(category, {'key': 'billing_' + suffix, 'label': 'Rozliczenia ' + suffix,
                                            'description': 'Obsługa faktur'})
                self.assertEqual(config.settings['groups'][-1]['label'], 'Wsparcie ' + suffix)
                for section in ('statuses', 'types', 'fields'):
                    self.assertEqual(config.settings[section], before[section])
                payload = self.configuration_payload('groups', scoped)
                payload[f'groups-{group_index}-label'] = 'Zespół wsparcia ' + suffix
                self.assertEqual(self.client.post(self.configuration_target('groups', scoped), payload).status_code, 302)
                data = self.client.get(self.api(self.configuration_target('groups', scoped), scoped)).json()['data']
                self.assertEqual(data['section'], 'groups')
                groups = next(group for group in data['sets'] if group['key'] == 'groups')
                for section in ('categories', 'groups'):
                    dictionary = next(group for group in data['sets'] if group['key'] == section)
                    for form in dictionary['forms']:
                        self.assertTrue({'icon', 'color'}.isdisjoint(field['field_name'] for field in form['fields']))
                label = next(field for field in groups['forms'][group_index]['fields'] if field['field_name'] == 'label')
                self.assertEqual(label['value'], 'Zespół wsparcia ' + suffix)

    def test_old_configuration_post_preserves_both_dictionaries(self):
        config = self.configure()
        before = deepcopy(config.settings)
        payload = {name: value for name, value in self.configuration_payload('types').items()
                   if not name.startswith(('categories-', 'groups-'))}
        payload['types-0-label'] = 'Praca'
        self.assertEqual(self.client.post(self.configuration_target('types'), payload).status_code, 302)
        config.refresh_from_db()
        self.assertEqual(config.settings['categories'], before['categories'])
        self.assertEqual(config.settings['groups'], before['groups'])
        self.assertEqual(config.settings['statuses'], before['statuses'])
        self.assertEqual(config.settings['fields'], before['fields'])
        self.assertEqual(config.settings['types'][0]['label'], 'Praca')

    def test_task_create_and_edit_persist_classification_with_plain_scoped_html_and_api(self):
        self.configure()
        self.login(self.member)
        for scoped in (False, True):
            for use_api in (False, True):
                with self.subTest(scoped=scoped, api=use_api):
                    title = f'Klasyfikacja {scoped} {use_api}'
                    target = self.target('items/create/', scoped)
                    response = self.client.post(self.api(target, scoped) if use_api else target, self.values(title=title))
                    self.assertEqual(response.status_code, 200 if use_api else 302, response.content)
                    task = self.space.tasks.get(title=title)
                    self.assertEqual((task.task_type, task.task_group), ('billing', 'support'))
                    self.assertEqual(task.created_by, self.member)
                    self.assertEqual(task.activities.get(action='created').actor, self.member)
                    original_key = task.work_item.key
                    target = self.task_target(task, 'edit/', scoped)
                    response = self.client.post(self.api(target, scoped) if use_api else target,
                                                self.values(title=title, task_type='general', task_group='sales'))
                    self.assertEqual(response.status_code, 200 if use_api else 302, response.content)
                    task.refresh_from_db()
                    self.assertEqual((task.task_type, task.task_group, task.work_item.key), ('general', 'sales', original_key))
                    self.assertEqual(task.activities.get(action='updated').actor, self.member)
                    data = self.client.get(self.api(self.task_target(task, scoped=scoped), scoped)).json()['data']
                    self.assertEqual((data['item']['task_type_label'], data['item']['task_group_label']), ('Ogólne', 'Sprzedaż'))
                    fields = {field['field_name']: field for field in data['form']['fields']}
                    category = next(choice for choice in fields['task_type']['choices'] if choice['value'] == 'billing')
                    group = next(choice for choice in fields['task_group']['choices'] if choice['value'] == 'support')
                    for choice in (category, group):
                        self.assertNotIn('type_color', choice)
                        self.assertNotIn('icon', choice)

    def test_autosave_history_uses_configured_labels_and_preserves_unsent_properties(self):
        self.configure()
        self.login(self.member)
        for scoped, use_api in ((False, False), (True, True)):
            self.task.task_type, self.task.task_group = 'general', ''
            self.task.save(update_fields=['task_type', 'task_group'])
            response = self.autosave(['task_type', 'task_group'], scoped, use_api,
                                     task_type='billing', task_group='support', title='Nie zapisuj')
            self.assertEqual(response.status_code, 200, response.content)
            self.task.refresh_from_db()
            self.assertEqual((self.task.task_type, self.task.task_group, self.task.title), ('billing', 'support', 'Zadanie'))
            activity = self.task.activities.filter(action='updated').latest('pk')
            self.assertEqual(activity.actor, self.member)
            self.assertEqual(activity.metadata['changes'], [
                {'field': 'kategoria zadania', 'from_label': 'Ogólne', 'to_label': 'Rozliczenia'},
                {'field': 'grupa', 'from_label': 'Brak grupy', 'to_label': 'Wsparcie'},
            ])
            count = self.task.activities.count()
            self.assertEqual(self.autosave(['task_type', 'task_group'], scoped, use_api,
                                          task_type='billing', task_group='support').status_code, 200)
            self.assertEqual(self.task.activities.count(), count)
            self.assertEqual(self.autosave(['task_group'], scoped, use_api, task_group='').status_code, 200)
            self.task.refresh_from_db()
            self.assertEqual((self.task.task_type, self.task.task_group), ('billing', ''))
            self.assertEqual(self.task.activities.latest('pk').metadata['changes'], [
                {'field': 'grupa', 'from_label': 'Wsparcie', 'to_label': 'Brak grupy'},
            ])

    def test_older_task_edit_omissions_preserve_current_category_and_group(self):
        self.configure()
        self.task.task_type, self.task.task_group = 'billing', 'support'
        self.task.save(update_fields=['task_type', 'task_group'])
        for scoped in (False, True):
            for suffix in ('', 'edit/'):
                values = self.values(title='Starszy formularz')
                del values['task_type']
                del values['task_group']
                response = self.client.post(self.api(self.task_target(suffix=suffix, scoped=scoped), scoped), values)
                self.assertEqual(response.status_code, 200, response.content)
                self.task.refresh_from_db()
                self.assertEqual((self.task.task_type, self.task.task_group), ('billing', 'support'))

    def test_unknown_or_other_space_choices_are_rejected_without_partial_task_save(self):
        self.configure()
        other = make_space(user=self.owner, workplace=self.workspace, name='Osobne słowniki')
        other.configuration.settings['categories'] = [{'key': 'external', 'label': 'Inna kategoria'}]
        other.configuration.settings['groups'] = [{'key': 'external', 'label': 'Inna grupa'}]
        other.configuration.save(update_fields=['settings'])
        for field in ('task_type', 'task_group'):
            for value in ('unknown', 'external'):
                for scoped in (False, True):
                    with self.subTest(field=field, value=value, scoped=scoped):
                        response = self.autosave(['title', field], scoped, True,
                                                 title='Nie zapisuj', **{field: value})
                        self.assertEqual(response.status_code, 400)
                        self.task.refresh_from_db()
                        self.assertEqual((self.task.title, self.task.task_type, self.task.task_group), ('Zadanie', 'general', ''))
                        self.assertFalse(self.task.activities.filter(action='updated').exists())
        target = self.target('items/create/')
        response = self.client.post(self.api(target), self.values(task_group='external'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.space.tasks.count(), 1)

    def test_used_dictionary_values_cannot_be_deleted_even_in_private_shared_space(self):
        config = self.configure()
        config.shared = True
        config.save(update_fields=['shared'])
        hidden = make_space(user=self.owner, workplace=self.workspace, name='Prywatna',
                            configuration=config, visibility='private', private_owner=self.member)
        hidden_task = SpaceTask.objects.create(space=hidden, title='Prywatne zadanie', created_by=self.member,
                                               visibility='private', private_owner=self.member,
                                               task_type='billing', task_group='support')
        self.assertEqual(self.client.get(self.task_target(hidden_task)).status_code, 404)
        before = deepcopy(config.settings)
        for section, index in (('categories', 1), ('groups', 0)):
            payload = self.configuration_payload(section)
            payload[f'{section}-{index}-DELETE'] = 'on'
            response = self.client.post(self.api(self.configuration_target(section)), payload)
            self.assertEqual(response.status_code, 400, response.content)
            config.refresh_from_db()
            self.assertEqual(config.settings, before)
        payload = self.configuration_payload('groups')
        payload['groups-1-DELETE'] = 'on'
        self.assertEqual(self.client.post(self.configuration_target('groups'), payload).status_code, 302)
        config.refresh_from_db()
        self.assertEqual([row['key'] for row in config.settings['groups']], ['support'])

    def test_dictionary_validation_rejects_duplicates_invalid_keys_and_empty_categories(self):
        config = self.configure()
        before = deepcopy(config.settings)
        for section, updates in (
            ('categories', {'categories-1-key': 'general'}),
            ('categories', {'categories-1-key': 'x' * 21}),
            ('categories', {'categories-1-key': 'Invalid key'}),
            ('categories', {'categories-0-DELETE': 'on', 'categories-1-DELETE': 'on'}),
            ('groups', {'groups-1-key': 'support'}),
            ('groups', {'groups-1-key': 'x' * 41}),
            ('groups', {'groups-1-key': 'Invalid key'}),
        ):
            with self.subTest(updates=updates):
                payload = {**self.configuration_payload(section), **updates}
                response = self.client.post(self.api(self.configuration_target(section)), payload)
                self.assertEqual(response.status_code, 400)
                config.refresh_from_db()
                self.assertEqual(config.settings, before)
        payload = self.configuration_payload('groups')
        payload.update({'groups-0-DELETE': 'on', 'groups-1-DELETE': 'on'})
        self.assertEqual(self.client.post(self.configuration_target('groups'), payload).status_code, 302)
        config.refresh_from_db()
        self.assertEqual(config.settings['groups'], [])

    def test_dictionary_conflict_does_not_overwrite_newer_changes(self):
        config = self.configure()
        stale = self.configuration_payload()
        config.settings['groups'][0]['label'] = 'Bieżąca grupa'
        config.save(update_fields=['settings'])
        stale['categories-1-label'] = 'Starszy szkic'
        response = self.client.post(self.api(self.configuration_target()), stale)
        self.assertEqual(response.status_code, 400)
        config.refresh_from_db()
        self.assertEqual(config.settings['groups'][0]['label'], 'Bieżąca grupa')
        self.assertEqual(config.settings['categories'][1]['label'], 'Rozliczenia')

    def test_renaming_used_labels_updates_display_while_changing_keys_is_rejected(self):
        config = self.configure()
        self.task.task_type, self.task.task_group = 'billing', 'support'
        self.task.save(update_fields=['task_type', 'task_group'])
        payload = self.configuration_payload()
        payload.update({'categories-1-label': 'Nowe rozliczenia', 'groups-0-label': 'Nowe wsparcie'})
        self.assertEqual(self.client.post(self.configuration_target(), payload).status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual((self.task.task_type, self.task.task_group), ('billing', 'support'))
        for scoped in (False, True):
            response = self.client.get(self.api(self.task_target(scoped=scoped), scoped), follow=True)
            self.assertEqual(response.status_code, 200, response.headers)
            data = response.json()['data']
            self.assertEqual((data['item']['task_type_label'], data['item']['task_group_label']),
                             ('Nowe rozliczenia', 'Nowe wsparcie'))
        for section, index in (('categories', 1), ('groups', 0)):
            payload = self.configuration_payload(section)
            payload[f'{section}-{index}-key'] = 'new_key'
            response = self.client.post(self.api(self.configuration_target(section)), payload)
            self.assertEqual(response.status_code, 400)
        config.refresh_from_db()
        self.assertEqual(config.settings['categories'][1]['key'], 'billing')
        self.assertEqual(config.settings['groups'][0]['key'], 'support')

    def test_creation_uses_first_configured_category_after_removing_general(self):
        config = self.configure()
        self.task.delete()
        stale_space = Space.objects.select_related('configuration').get(pk=self.space.pk)
        payload = self.configuration_payload()
        payload['categories-0-DELETE'] = 'on'
        self.assertEqual(self.client.post(self.configuration_target(), payload).status_code, 302)
        config.refresh_from_db()
        self.assertEqual([row['key'] for row in config.settings['categories']], ['billing'])
        values = self.values(title='Zadanie bez kategorii')
        del values['task_type']
        self.assertEqual(self.client.post(self.api(self.target('items/create/')), values).status_code, 200)
        parent = self.space.tasks.get(title='Zadanie bez kategorii')
        self.assertEqual(parent.task_type, 'billing')
        for action, values in (
            ('subtask', {'title': 'Szybkie podzadanie'}),
            ('create_subtask_modal', {'subtask-title': 'Modal podzadania', 'subtask-status': 'new'}),
        ):
            response = self.client.post(self.api(self.task_target(parent)), {'action': action, **values})
            self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(list(parent.subtasks.values_list('task_type', flat=True)), ['billing', 'billing'])
        created = SpaceTask.objects.create(space=stale_space, title='Model z domyślną kategorią', created_by=self.owner)
        self.assertEqual(created.task_type, 'billing')

    def test_task_and_configuration_permissions_remain_scoped(self):
        self.configure()
        for person in (self.member, self.observer):
            self.login(person)
            for section in ('categories', 'groups'):
                self.assertEqual(self.client.get(self.api(self.configuration_target(section))).status_code, 403)
        for scoped in (False, True):
            self.assertEqual(self.autosave(['task_group'], scoped, True, task_group='support').status_code, 403)
        self.login(self.owner)
        for section in ('categories', 'groups'):
            target = self.target('configuration/?section=' + section, workspace=self.other_workspace)
            self.assertEqual(self.client.get(self.api(target, workspace=self.other_workspace)).status_code, 404)
        target = self.task_target(workspace=self.other_workspace)
        self.assertEqual(self.client.post(self.api(target, workspace=self.other_workspace),
                                         {'action': 'save', 'autosave_fields': '["task_group"]',
                                          'task_group': 'support'}).status_code, 404)
        self.task.refresh_from_db()
        self.assertEqual(self.task.task_group, '')

    def test_reduced_subtask_editor_preserves_classification(self):
        self.configure()
        child = SpaceTask.objects.create(space=self.space, parent=self.task, title='Podzadanie',
                                         created_by=self.owner, task_type='billing', task_group='support')
        for scoped in (False, True):
            target = self.task_target(child, 'edit/', scoped)
            schema = self.client.get(self.api(target, scoped)).json()['data']['form']
            fields = {field['field_name'] for field in schema['fields']}
            self.assertNotIn('task_type', fields)
            self.assertNotIn('task_group', fields)
            response = self.client.post(self.api(target, scoped), self.values(
                title='Podzadanie po zmianie', status='new', task_type='general', task_group='sales'))
            self.assertEqual(response.status_code, 200, response.content)
            child.refresh_from_db()
            self.assertEqual((child.task_type, child.task_group), ('billing', 'support'))
            self.assertEqual(child.title, 'Podzadanie po zmianie')
