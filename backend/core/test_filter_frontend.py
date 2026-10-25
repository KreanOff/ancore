import json
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from dashboard.models import SavedTaskFilter
from spaces.models import SpaceMembership, SpaceTask
from spaces.testing import make_space
from tasks.models import TaskTag, TaskTagNote
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class ReactFilterAndTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='react-tags-owner', email='react-tags-owner@example.test')
        cls.member = users.objects.create_user(username='react-tags-member', email='react-tags-member@example.test')
        cls.outsider = users.objects.create_user(username='react-tags-outsider', email='react-tags-outsider@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Tagi i Filtry React')
        cls.other = create_workplace_for_user(cls.owner, 'Inny kontekst')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Produkt', key='PRO')
        cls.hidden = make_space(user=cls.owner, workplace=cls.workspace, name='Poufna przestrzeń', key='SEC', visibility='private', private_owner=cls.owner)
        cls.observed = make_space(user=cls.owner, workplace=cls.workspace, name='Obserwowana', key='OBS', visibility='private', private_owner=cls.owner)
        SpaceMembership.objects.create(space=cls.observed, user=cls.member, role='observer')
        cls.task = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, assignee=cls.member, title='Publiczne zadanie', priority='high')
        cls.secret = SpaceTask.objects.create(space=cls.hidden, created_by=cls.owner, assignee=cls.member, title='Tajna treść')
        cls.tag = TaskTag.objects.create(user=cls.owner, workplace=cls.workspace, space=cls.space, name='Frontend')
        cls.task.tags.add(cls.tag)
        cls.hidden_tag = TaskTag.objects.create(user=cls.owner, workplace=cls.workspace, space=cls.hidden, name='Poufny tag')
        cls.observed_tag = TaskTag.objects.create(user=cls.owner, workplace=cls.workspace, space=cls.observed, name='Obserwowany tag')
        cls.note = TaskTagNote.objects.create(tag=cls.tag, author=cls.owner, message='Notatka właściciela')
        cls.saved = SavedTaskFilter.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Wspólny filtr', visibility='workspace', query='assignee = currentUser()')
        cls.private_filter = SavedTaskFilter.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Prywatna definicja')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def path(self, app, suffix='', workspace=None):
        return scoped_workplace_app_path(workspace or self.workspace, app, suffix)

    def endpoint(self, target):
        return self.path('api', 'v1/page/') + '?' + urlencode({'url': target})

    def tags(self, space=None):
        return self.path('space', (space or self.space).slug + '/') + '?view=tags'

    def get(self, target):
        return self.client.get(self.endpoint(target))

    def post(self, target, data, **headers):
        return self.client.post(self.endpoint(target), data, **headers)

    def test_screens_bootstrap_typed_data_in_scoped_and_unscoped_routes(self):
        for scoped in (True, False):
            prefix = self.path('filters') if scoped else '/filters/'
            tags = self.tags() if scoped else f'/space/{self.space.slug}/?view=tags'
            for path, kind in ((prefix, 'filter-directory'), (prefix + 'search/', 'filter-search'), (tags, 'space-tags')):
                with self.subTest(path=path):
                    response = self.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()['type'], kind)
                    self.assertNotIn('html', response.json())
                    self.assertEqual(response['Cache-Control'], 'no-store')
                    self.assertContains(self.client.get(path, follow=True), 'data-react-root="page"')

    def test_search_options_and_results_keep_space_acl(self):
        data = self.get(self.path('filters', 'search/')).json()['data']
        encoded = json.dumps(data, ensure_ascii=False)
        for secret in (self.secret.title, self.hidden.name, self.hidden_tag.name):
            self.assertNotIn(secret, encoded)
        self.assertEqual([row['task_id'] for row in data['items']], [self.task.pk])
        fields = {field['name']: field for field in data['form']['fields']}
        status = fields['status']['choices'][0]
        self.assertIn('status_category', status)
        self.assertTrue(any(choice.get('avatar') for choice in fields['assignee']['choices']))
        self.assertTrue(any(choice.get('priority') for choice in fields['priority']['choices']))

    def test_basic_multi_values_advanced_errors_and_pagination_keep_query(self):
        path = self.path('filters', 'search/')
        data = self.get(path + '?' + urlencode({'basic': '1', 'mode': 'basic', 'sort': 'created_desc', 'priority': ['high', 'urgent']}, doseq=True)).json()['data']
        self.assertEqual([row['task_id'] for row in data['items']], [self.task.pk])
        self.assertIn('priority', data['jql'])
        invalid = self.get(path + '?' + urlencode({'mode': 'advanced', 'jql': 'unknown = 1'})).json()['data']
        self.assertTrue(invalid['search_error'])
        self.assertFalse(invalid['can_save'])
        self.assertEqual(invalid['items'], [])
        for index in range(52):
            SpaceTask.objects.create(space=self.space, title=f'Wynik {index}', priority='high', created_by=self.owner)
        result = self.get(path + '?' + urlencode({'jql': 'priority = high', 'mode': 'advanced', 'page': 2})).json()['data']
        self.assertEqual(result['pagination']['count'], 53)
        self.assertEqual(len(result['items']), 3)
        self.assertIn('jql=', result['pagination']['pages'][0]['url'])

    def test_retired_management_redirects_in_page_and_navigation_api(self):
        for prefix in ['/filters/', self.path('filters')]:
            target = prefix + 'manage/?q=Plan&page=2&visibility=private&favorite=starred'
            expected = self.path('filters') + '?tab=mine&q=Plan&page=2'
            self.assertEqual(self.get(target).json(), {'redirect': expected})
            endpoint = self.path('api', 'v1/navigation/')
            self.assertEqual(self.client.get(endpoint, {'url': target}).json(), {'redirect': expected})
        data = self.get(self.path('filters')).json()['data']
        for field in ['management', 'management_url', 'visibility_filter', 'favorite_filter']:
            self.assertNotIn(field, data)

    def test_filter_crud_preserves_actor_authorized_sharing_and_revision(self):
        create = self.path('filters', 'manage/new/') + '?visibility=workspace&q=React'
        modal = self.get(create).json()['data']['modal']
        self.assertEqual(modal['values']['return_to'], self.path('filters') + '?tab=mine&q=React')
        values = {'name': 'React filtr', 'description': 'Opis', 'visibility': 'private',
                  'query': 'assignee = currentUser()', 'revision': 0, 'return_to': modal['return_url'], 'owner': self.outsider.pk}
        saved = self.post(create, values)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()['redirect'], modal['return_url'])
        self.assertEqual(saved.json()['filter_modal']['filter_settings'], 'edit')
        item = SavedTaskFilter.objects.get(name='React filtr')
        self.assertEqual((item.owner_id, item.created_by_id, item.workplace_id), (self.owner.pk, self.member.pk, self.workspace.pk))
        self.assertTrue(item.favorited_by.filter(pk=self.member.pk).exists())
        team = self.path('filters', f'{item.pk}/team/')
        invalid = self.post(team, {'action': 'share', 'email': self.outsider.email, 'role': 'member'})
        self.assertEqual(invalid.status_code, 400)
        self.assertTrue(invalid.json()['errors']['email'])
        self.assertEqual(self.post(team, {'action': 'share', 'email': self.owner.email, 'role': 'observer'}).status_code, 200)
        self.assertEqual(list(item.shared_with.values_list('pk', flat=True)), [self.owner.pk])
        item.refresh_from_db()
        edit = self.path('filters', f'{item.pk}/edit/')
        good = self.post(edit, {**values, 'revision': item.revision, 'name': 'Zmieniony filtr'})
        self.assertEqual(good.status_code, 200)
        conflict = self.post(edit, {**values, 'revision': item.revision, 'name': 'Starszy szkic'})
        self.assertEqual(conflict.status_code, 400)
        self.assertTrue(conflict.json()['data']['modal']['form']['errors'])
        item.refresh_from_db()
        self.assertEqual(item.name, 'Zmieniony filtr')
        self.assertEqual(self.post(self.path('filters', f'{item.pk}/delete/'), {'return_to': self.path('filters', 'manage/')}).status_code, 200)
        self.assertFalse(SavedTaskFilter.objects.filter(pk=item.pk).exists())

    def test_shared_filter_can_run_and_favorite_but_cannot_be_edited(self):
        target = self.path('filters', f'{self.saved.pk}/')
        data = self.get(target).json()['data']
        self.assertEqual([row['task_id'] for row in data['items']], [self.task.pk])
        self.assertFalse(data['saved_filter']['editable'])
        self.assertEqual(self.post(target + 'favorite/', {'return_to': target}).status_code, 200)
        self.assertTrue(self.saved.favorited_by.filter(pk=self.member.pk).exists())
        for operation in ('edit/', 'delete/', 'save/'):
            self.assertEqual(self.post(target + operation, {'jql': '', 'revision': self.saved.revision}).status_code, 403)
        self.assertEqual(self.get(self.path('filters', f'{self.private_filter.pk}/')).status_code, 404)
        self.assertEqual(self.get(self.path('filters', 'manage/')).json(), {'redirect': self.path('filters') + '?tab=mine'})

    def test_filter_settings_window_metadata_validation_and_repeated_saves(self):
        item = SavedTaskFilter.objects.create(owner=self.owner, workplace=self.workspace, created_by=self.member,
                                              name='Ustawienia React', visibility='private')
        for prefix in (self.path('filters'), '/filters/'):
            for management in (False, True):
                root = prefix + ('manage/' if management else '')
                target = root + f'{item.pk}/edit/?q=Ustawienia&visibility=private&page=2'
                with self.subTest(target=target):
                    modal = self.get(target).json()['data']['modal']
                    self.assertEqual(modal['filter_settings'], 'edit')
                    self.assertFalse(modal['form']['compact'])
                    self.assertEqual(modal['title'], 'Ustawienia filtra')
                    if management:
                        self.assertIn('q=Ustawienia', modal['return_url'])
                        self.assertIn('page=2', modal['return_url'])
                    create = self.get(root + 'new/').json()['data']['modal']
                    self.assertEqual(create['filter_settings'], 'create')
                    self.assertFalse(create['form']['compact'])
        target = self.path('filters', f'manage/{item.pk}/edit/')
        values = {'name': item.name, 'description': 'Pierwszy zapis', 'query': '', 'visibility': 'private',
                  'revision': item.revision}
        invalid = self.post(target, {**values, 'query': 'unknown = field'})
        self.assertEqual(invalid.status_code, 400)
        modal = invalid.json()['data']['modal']
        self.assertTrue(modal['filter_settings'])
        self.assertTrue(next(field for field in modal['form']['fields'] if field['name'] == 'query')['errors'])
        first = self.post(target, values)
        self.assertEqual(first.status_code, 200)
        fields = {field['name']: field for field in first.json()['form']['fields']}
        self.assertEqual(fields['revision']['value'], '1')
        self.assertNotIn('shared_with', fields)
        shared = self.post(self.path('filters', f'{item.pk}/team/'),
                           {'action': 'share', 'email': self.owner.email, 'role': 'observer'})
        self.assertEqual(shared.status_code, 200)
        second = self.post(target, {**values, 'description': 'Drugi zapis', 'revision': shared.json()['revision']})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(next(field for field in second.json()['form']['fields'] if field['name'] == 'revision')['value'], '3')
        self.assertEqual(self.post(target, values).status_code, 400)
        item.refresh_from_db()
        self.assertEqual((item.description, item.revision), ('Drugi zapis', 3))
        self.assertEqual(item.memberships.get(user=self.owner).role, 'observer')

    def test_query_save_conflict_does_not_overwrite_current_definition(self):
        self.client.force_login(self.owner)
        target = self.path('filters', f'{self.saved.pk}/save/')
        revision = self.saved.revision
        self.assertEqual(self.post(target, {'jql': 'priority = high', 'revision': revision}).status_code, 200)
        self.assertEqual(self.post(target, {'jql': '', 'revision': revision}).status_code, 409)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.query, 'priority = high')
        invalid = self.post(target, {'jql': 'unknown = 1', 'revision': self.saved.revision})
        self.assertEqual(invalid.status_code, 400)

    def test_tags_scope_counts_notes_and_author_permissions(self):
        data = self.get(self.tags()).json()['data']
        self.assertEqual([tag['id'] for tag in data['tags']], [self.tag.pk])
        self.assertEqual(data['tags'][0]['task_count'], 1)
        self.assertFalse(data['tags'][0]['notes'][0]['editable'])
        self.assertNotIn(self.hidden_tag.name, json.dumps(data, ensure_ascii=False))
        created = self.post(self.tags(), {'action': 'create_tag', 'name': 'Nowy tag', 'color': '#5b5fc7', 'related_tags': [self.tag.pk]})
        self.assertEqual(created.status_code, 200)
        tag = TaskTag.objects.get(name='Nowy tag')
        self.assertEqual((tag.user_id, tag.workplace_id, tag.space_id), (self.owner.pk, self.workspace.pk, self.space.pk))
        self.assertEqual(list(tag.related_tags.values_list('pk', flat=True)), [self.tag.pk])
        invalid = self.post(self.tags(), {'action': 'edit_tag', 'tag_id': tag.pk, 'name': tag.name, 'related_tags': [self.hidden_tag.pk]})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()['data']['modal']['values']['action'], 'edit_tag')
        self.assertEqual(invalid.json()['data']['modal']['form']['submit_label'], 'Zapisz zmiany')
        self.assertTrue(next(field for field in invalid.json()['data']['modal']['form']['fields'] if field['name'] == 'related_tags')['errors'])
        duplicate = self.post(self.tags(), {'action': 'create_tag', 'name': self.tag.name.lower()})
        self.assertEqual(duplicate.status_code, 400)
        self.assertTrue(duplicate.json()['data']['modal']['form']['fields'][0]['errors'])

    def test_notes_are_authored_by_actor_and_only_author_can_edit_or_delete(self):
        target = self.tags()
        self.assertEqual(self.post(target, {'action': 'add_tag_note', 'tag_id': self.tag.pk, 'message': 'Notatka React', 'author': self.owner.pk}).status_code, 200)
        note = TaskTagNote.objects.get(message='Notatka React')
        self.assertEqual(note.author_id, self.member.pk)
        self.assertEqual(self.post(target, {'action': 'edit_tag_note', 'tag_id': self.tag.pk, 'note_id': self.note.pk, 'message': 'Niedozwolona'}).status_code, 404)
        self.assertEqual(self.post(target, {'action': 'edit_tag_note', 'tag_id': self.tag.pk, 'note_id': note.pk, 'message': ''}).status_code, 400)
        self.assertEqual(self.post(target, {'action': 'add_tag_note', 'tag_id': self.tag.pk, 'message': ''}).status_code, 400)
        self.assertEqual(self.post(target, {'action': 'edit_tag_note', 'tag_id': self.tag.pk, 'note_id': note.pk, 'message': 'Po edycji'}).status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.message, 'Po edycji')
        self.assertIsNotNone(note.edited_at)
        self.assertEqual(self.post(target, {'action': 'delete_tag_note', 'tag_id': self.tag.pk, 'note_id': note.pk}).status_code, 200)
        self.assertFalse(TaskTagNote.objects.filter(pk=note.pk).exists())

    def test_bulk_delete_is_atomic_and_cannot_include_hidden_tag(self):
        result = self.post(self.tags(), {'action': 'delete_tag', 'tag_ids': [self.tag.pk, self.hidden_tag.pk]})
        self.assertEqual(result.status_code, 404)
        self.assertTrue(TaskTag.objects.filter(pk=self.tag.pk).exists())
        second = TaskTag.objects.create(user=self.owner, workplace=self.workspace, space=self.space, name='Drugi tag')
        self.assertEqual(self.post(self.tags(), {'action': 'delete_tag', 'tag_ids': [self.tag.pk, second.pk]}).status_code, 200)
        self.assertFalse(TaskTag.objects.filter(pk__in=[self.tag.pk, second.pk]).exists())
        self.assertTrue(SpaceTask.objects.filter(pk=self.task.pk).exists())

    def test_observer_and_hidden_space_cannot_mutate_tags(self):
        data = self.get(self.tags(self.observed)).json()['data']
        self.assertFalse(data['can_edit'])
        self.assertIsNone(data['form'])
        for action in ('create_tag', 'edit_tag', 'delete_tag', 'add_tag_note'):
            self.assertEqual(self.post(self.tags(self.observed), {'action': action, 'tag_id': self.observed_tag.pk, 'name': 'Nie', 'message': 'Nie'}).status_code, 403)
        self.assertEqual(self.get(self.tags(self.hidden)).status_code, 404)

    def test_api_strips_legacy_filter_headers_and_rejects_cross_workspace(self):
        target = self.path('filters', 'new/')
        response = self.client.get(self.endpoint(target), HTTP_X_FILTER_MODAL='true')
        self.assertEqual(response.json()['type'], 'filter-search')
        self.assertNotIn('html', response.json())
        saved = self.post(target, {'name': 'Nagłówki', 'query': '', 'visibility': 'private'}, HTTP_X_FILTER_MODAL='true')
        self.assertIn('redirect', saved.json())
        self.client.force_login(self.owner)
        for path in (self.path('filters', workspace=self.other), self.path('space', self.space.slug + '/', workspace=self.other) + '?view=tags'):
            self.assertEqual(self.get(path).status_code, 403)

    def test_new_operations_require_csrf_and_mutations_use_post(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        for target in (self.tags(), self.path('filters', 'new/'), self.path('filters', f'{self.saved.pk}/favorite/')):
            self.assertEqual(client.post(self.endpoint(target), {}).status_code, 403)
        for operation in ('favorite/', 'delete/', 'save/'):
            self.assertEqual(self.get(self.path('filters', f'{self.saved.pk}/' + operation)).status_code, 405)
