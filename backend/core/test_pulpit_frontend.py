import json
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from dashboard.models import Dashboard, DashboardGadget
from spaces.models import SpaceTask
from spaces.testing import make_space
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class ReactPulpitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='pulpit-react-owner', email='owner@example.test')
        cls.member = users.objects.create_user(username='pulpit-react-member', email='member@example.test')
        cls.foreign = users.objects.create_user(username='pulpit-react-foreign', email='foreign@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Pulpity React')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        cls.default_dashboard = Dashboard.objects.get(workplace=cls.workspace, created_by=cls.owner, is_default=True)
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Produkt', key='PRO')
        cls.hidden = make_space(user=cls.owner, workplace=cls.workspace, name='Poufne źródło', key='SEC', visibility='private', private_owner=cls.owner)
        cls.task = SpaceTask.objects.create(space=cls.space, title='Bieżące zadanie', created_by=cls.member, assignee=cls.member)
        SpaceTask.objects.create(space=cls.space, title='Zakończone', status='closed', created_by=cls.owner)
        SpaceTask.objects.create(space=cls.hidden, title='Tajne zadanie', created_by=cls.owner, assignee=cls.member)
        cls.dashboard = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.member, name='Wspólny pulpit', visibility='workspace', layout='three', description='Pierwszy wiersz\nDrugi <tekst>')
        cls.gadget = DashboardGadget.objects.create(dashboard=cls.dashboard, kind='progress', assignee='me')
        cls.private = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.member, name='Prywatny pulpit')
        cls.secret_gadget = DashboardGadget.objects.create(dashboard=cls.dashboard, kind='progress', space=cls.hidden, column=1)

    def setUp(self):
        self.login(self.member)

    def login(self, user, client=None):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def path(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'dashboards', suffix)

    def endpoint(self, target):
        return scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') + '?' + urlencode({'url': target})

    def get(self, target, **headers):
        return self.client.get(self.endpoint(target), **headers)

    def post(self, target, data, **headers):
        return self.client.post(self.endpoint(target), data, **headers)

    def operation(self, name, data):
        return self.post(self.path(f'{self.dashboard.slug}/{name}/'), json.dumps(data), content_type='application/json')

    def test_registered_screens_have_typed_bootstrap_scoped_and_plain(self):
        for prefix in (self.path(), '/dashboards/'):
            for suffix, kind in (('', 'pulpit-directory'), (f'{self.dashboard.slug}/', 'pulpit-detail'), (f'{self.dashboard.slug}/gadgets/', 'pulpit-detail'), (f'{self.dashboard.slug}/edit/', 'pulpit-edit'), (f'{self.dashboard.slug}/access/', 'pulpit-edit')):
                with self.subTest(path=prefix + suffix):
                    response = self.get(prefix + suffix)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()['type'], kind)
                    self.assertNotIn('html', response.json())
                    self.assertEqual(response['Cache-Control'], 'no-store')
                    self.assertContains(self.client.get(prefix + suffix, follow=True), 'data-react-root="page"')

    def test_retired_management_redirects_in_page_and_navigation_api(self):
        for prefix in (self.path(), '/dashboards/'):
            target = prefix + 'manage/?q=Raport&visibility=workspace&page=2'
            destination = self.path() + '?q=Raport&visibility=workspace&page=2'
            self.assertEqual(self.get(target).json(), {'redirect': destination})
            navigation = scoped_workplace_app_path(self.workspace, 'api', 'v1/navigation/')
            result = self.client.get(navigation, {'url': target}).json()
            self.assertEqual(result, {'redirect': destination})
        data = self.get(self.path()).json()['data']
        self.assertNotIn('management', data)
        self.assertNotIn('favorite', data)

    def test_default_initializes_once_and_does_not_recreate_deleted_gadgets(self):
        for target in ('/', self.path('default/'), '/'):
            result = self.get(target).json()
            self.assertEqual(result['type'], 'pulpit-detail')
            self.assertEqual(len(result['data']['columns'][0]), 1)
        item = Dashboard.objects.get(created_by=self.member, workplace=self.workspace, is_default=True)
        self.assertEqual(self.post(self.path(f'{item.slug}/delete/'), {}).status_code, 403)
        gadget = item.gadgets.get()
        self.assertEqual(self.post(self.path(f'{item.slug}/gadgets/{gadget.pk}/delete/'), {}).status_code, 200)
        self.assertFalse(any(self.get(self.path('default/')).json()['data']['columns']))

    def test_detail_does_not_expose_unavailable_source_or_counts(self):
        data = self.get(self.path(self.dashboard.slug + '/')).json()['data']
        self.assertEqual(data['columns'][0][0]['count'], 1)
        self.assertEqual(data['columns'][0][0]['edit_url'], '')
        unavailable = data['columns'][1][0]
        self.assertTrue(unavailable['unavailable'])
        for key in ('count', 'closed_count', 'percent', 'statuses', 'caption', 'space'):
            self.assertNotIn(key, unavailable)
        self.assertNotIn(self.hidden.name, json.dumps(data, ensure_ascii=False))
        self.assertEqual(data['dashboard']['description'], self.dashboard.description)

    def test_visibility_and_creator_rights_are_independent_of_workspace_owner(self):
        self.login(self.owner)
        catalog = self.get(self.path()).json()['data']
        self.assertSetEqual({row['id'] for row in catalog['results']}, {self.dashboard.pk, self.default_dashboard.pk})
        self.assertEqual(self.get(self.path(self.private.slug + '/')).status_code, 404)
        for operation in ('gadgets/', 'edit/', 'access/'):
            self.assertEqual(self.get(self.path(f'{self.dashboard.slug}/{operation}')).status_code, 403)
        self.assertEqual(self.operation('arrange', {'layout': 'single', 'columns': [[self.gadget.pk, self.secret_gadget.pk]], 'revision': 0}).status_code, 403)
        self.assertEqual(self.operation('gadgets/quick-add', {'kind': 'progress', 'revision': 0}).status_code, 403)
        self.assertEqual(self.post(self.path(f'{self.dashboard.slug}/delete/'), {}).status_code, 403)
        self.assertEqual(self.get(self.path('manage/')).json(), {'redirect': self.path()})

    def test_create_validation_choices_actor_and_sharing(self):
        target = self.path('manage/create/') + '?q=React&visibility=selected'
        modal = self.get(target, HTTP_X_PULPIT_MODAL='true').json()['data']['modal']
        fields = {row['name']: row for row in modal['form']['fields']}
        self.assertEqual(modal['form']['layout'], 'pulpit')
        self.assertEqual(len(fields['layout']['choices']), 5)
        self.assertTrue(all(row['layout_preview'] == row['value'] for row in fields['layout']['choices']))
        self.assertEqual([row['value'] for row in fields['shared_with']['choices']], [str(self.owner.pk)])
        self.assertIn('q=React', modal['return_url'])
        invalid = self.post(target, {'name': 'Nowy pulpit React', 'layout': 'equal', 'visibility': 'selected'})
        self.assertEqual(invalid.status_code, 400)
        self.assertTrue(next(row for row in invalid.json()['data']['modal']['form']['fields'] if row['name'] == 'shared_with')['errors'])
        self.assertEqual(self.post(target, {'name': 'Niedozwolony', 'layout': 'equal', 'visibility': 'selected', 'shared_with': [self.foreign.pk]}).status_code, 400)
        saved = self.post(target, {'name': 'Nowy pulpit React', 'description': '<b>Opis</b>', 'layout': 'equal', 'visibility': 'selected', 'shared_with': [self.owner.pk]}, HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(saved.status_code, 200)
        self.assertIn('q=React', saved.json()['redirect'])
        item = Dashboard.objects.get(name='Nowy pulpit React')
        self.assertEqual((item.owner_id, item.created_by_id, item.workplace_id), (self.owner.pk, self.member.pk, self.workspace.pk))
        self.assertEqual(list(item.shared_with.all()), [self.owner])
        self.assertTrue(item.favorited_by.filter(pk=self.member.pk).exists())

    def test_editor_settings_access_and_gadget_forms_are_separate(self):
        prefix = self.path(f'manage/{self.dashboard.slug}/')
        settings = self.get(prefix + 'edit/?q=Plan&page=2').json()['data']
        self.assertEqual([row['name'] for row in settings['form']['fields']],
                         ['name', 'description', 'icon', 'data_scope', 'scope_spaces', 'scope_filter', 'refresh_interval', 'visibility'])
        self.assertIn('page=2', settings['return_url'])
        access = self.get(prefix + 'access/').json()['data']
        self.assertEqual([row['name'] for row in access['form']['fields']], ['visibility', 'shared_with'])
        gadget_page = self.get(prefix + f'gadgets/{self.gadget.pk}/edit/').json()['data']
        self.assertEqual(gadget_page['return_url'], self.path())
        self.assertEqual(gadget_page['modal']['return_url'], prefix + 'gadgets/')
        gadget = gadget_page['modal']
        fields = {row['name']: row for row in gadget['form']['fields']}
        self.assertNotIn(str(self.hidden.pk), [row['value'] for row in fields['space']['choices']])
        self.assertEqual([row['value'] for row in fields['kind']['choices']], ['', 'progress'])
        self.assertEqual([row['kind'] for row in gadget['form']['gadget_catalog']], ['progress'])
        self.assertEqual(self.post(prefix + 'access/', {'visibility': 'selected'}).status_code, 400)
        self.assertIn('redirect', self.post(prefix + 'edit/', {'name': self.dashboard.name, 'description': 'Zmieniony opis'}).json())
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 1)
        self.assertEqual(self.operation('arrange', {'layout': 'three', 'columns': [[self.gadget.pk], [self.secret_gadget.pk], []], 'revision': 0}).status_code, 409)

    def test_settings_window_tabs_preserve_scope_filters_and_background_navigation(self):
        for prefix in (self.path(), '/dashboards/'):
            for management in (False, True):
                root = prefix + ('manage/' if management else '') + self.dashboard.slug + '/'
                for suffix, active in (('gadgets/', 'gadgets'), ('access/', 'access'), ('edit/', 'settings')):
                    target = root + suffix + '?q=Plan&visibility=workspace&page=2'
                    with self.subTest(target=target):
                        page = self.get(target).json()
                        tabs = page['data']['settings_tabs']
                        self.assertEqual([tab['key'] for tab in tabs], ['gadgets', 'settings', 'access'])
                        self.assertEqual([tab['label'] for tab in tabs], ['Gadżety i układ', 'Ustawienia', 'Udostępnienia'])
                        self.assertEqual([tab['key'] for tab in tabs if tab['active']], [active])
                        for tab in tabs:
                            self.assertTrue(tab['url'].startswith(self.path('manage/' if management else '')))
                            if management:
                                self.assertIn('q=Plan', tab['url'])
                                self.assertIn('page=2', tab['url'])
                        navigation = self.client.get(self.endpoint(target).replace('/page/', '/navigation/')).json()
                        self.assertEqual(navigation['shell']['mode'], 'workspace')

    def test_quick_add_returns_current_space_task_counts_without_html(self):
        result = self.operation('gadgets/quick-add', {'kind': 'progress', 'revision': 0})
        self.assertEqual(result.status_code, 200)
        payload = result.json()
        self.assertNotIn('html', payload)
        self.assertEqual((payload['column'], payload['revision'], payload['gadget_count']), (2, 1, 3))
        self.assertEqual((payload['gadget']['count'], payload['gadget']['closed_count'], payload['gadget']['percent']), (2, 1, 50))
        self.assertEqual(len(payload['gadget']['statuses']), 5)
        detail = self.get(self.path(f'{self.dashboard.slug}/gadgets/')).json()['data']
        self.assertEqual(payload['gadget'], detail['columns'][2][0])
        self.assertEqual(self.operation('gadgets/quick-add', {'kind': 'progress', 'revision': 0}).status_code, 409)
        self.assertEqual(self.dashboard.gadgets.count(), 3)

    def test_arrangement_accepts_complete_nested_integer_ids_and_is_atomic(self):
        valid = {'layout': 'equal', 'columns': [[self.secret_gadget.pk], [self.gadget.pk]], 'revision': 0}
        result = self.operation('arrange', valid)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['revision'], 1)
        self.dashboard.refresh_from_db()
        self.gadget.refresh_from_db()
        self.assertEqual((self.dashboard.layout, self.gadget.column), ('equal', 1))
        self.assertEqual(self.operation('arrange', valid).status_code, 409)
        invalids = [
            {'layout': 'equal', 'columns': [[self.gadget.pk], [self.gadget.pk]], 'revision': 1},
            {'layout': 'equal', 'columns': [[], []], 'revision': 1},
            {'layout': 'equal', 'columns': [[str(self.gadget.pk)], [self.secret_gadget.pk]], 'revision': 1},
            {'layout': 'single', 'columns': [[self.gadget.pk], [self.secret_gadget.pk]], 'revision': 1},
            {'layout': 'single', 'columns': [[self.gadget.pk, 999999]], 'revision': 1},
            {**valid, 'revision': True},
        ]
        for body in invalids:
            self.assertEqual(self.operation('arrange', body).status_code, 400)
        self.dashboard.refresh_from_db()
        self.gadget.refresh_from_db()
        self.assertEqual((self.dashboard.revision, self.dashboard.layout, self.gadget.column), (1, 'equal', 1))

    def test_raw_json_allowlist_does_not_weaken_other_form_endpoints(self):
        for body in ('broken', '[]', 'null', '{}', '{"kind":"progress","revision":true}'):
            self.assertEqual(self.post(self.path(f'{self.dashboard.slug}/gadgets/quick-add/'), body, content_type='application/json').status_code, 400)
        self.assertEqual(self.operation('gadgets/quick-add', {'kind': 'assigned', 'revision': 0}).status_code, 400)
        target = scoped_workplace_app_path(self.workspace, 'filters', 'manage/new/')
        self.assertEqual(self.post(target, json.dumps({'name': 'Nie', 'shared_with': [self.owner.pk]}), content_type='application/json').status_code, 400)

    def test_limit_and_gadget_source_validation(self):
        path = self.path(f'{self.dashboard.slug}/gadgets/{self.gadget.pk}/edit/')
        self.assertEqual(self.post(path, {'kind': 'progress', 'space': self.hidden.pk, 'assignee': 'all'}).status_code, 400)
        self.assertEqual(self.post(path, {'kind': 'progress', 'space': self.space.pk, 'assignee': 'me', 'title': 'Dla mnie'}).status_code, 200)
        self.gadget.refresh_from_db()
        self.assertEqual((self.gadget.title, self.gadget.space_id, self.gadget.assignee), ('Dla mnie', self.space.pk, 'me'))
        DashboardGadget.objects.bulk_create([DashboardGadget(dashboard=self.dashboard, kind='progress') for _ in range(22)])
        self.assertEqual(self.operation('gadgets/quick-add', {'kind': 'progress', 'revision': 1}).status_code, 400)
        self.assertEqual(self.dashboard.gadgets.count(), 24)

    def test_favorite_redirect_delete_invalidates_all_saved_return_paths(self):
        target = self.path('manage/') + '?q=Wspólny&favorite=unstarred'
        result = self.post(self.path(f'{self.dashboard.slug}/favorite/'), {'next': target}, HTTP_X_PULPIT_NAVIGATION='true')
        self.assertEqual(result.json()['redirect'], target)
        self.assertTrue(self.dashboard.favorited_by.filter(pk=self.member.pk).exists())
        result = self.post(self.path(f'manage/{self.dashboard.slug}/delete/') + '?q=Wspólny', {}).json()
        self.assertIn('q=Wsp%C3%B3lny', result['redirect'])
        for prefix in ('/dashboards/', self.path()):
            for management in ('', 'manage/'):
                for identifier in (self.dashboard.pk, self.dashboard.slug):
                    self.assertIn(f'{prefix}{management}{identifier}/', result['invalidated_return_paths'])
        self.assertFalse(Dashboard.objects.filter(pk=self.dashboard.pk).exists())

    def test_pagination_filters_and_numeric_links_preserve_query(self):
        Dashboard.objects.bulk_create([Dashboard(owner=self.owner, workplace=self.workspace, created_by=self.member, name=f'Raport {i:02}', slug=f'raport-{i}', visibility='workspace') for i in range(32)])
        data = self.get(self.path() + '?q=Raport&visibility=workspace&page=2').json()['data']
        self.assertEqual((len(data['results']), data['pagination']['count']), (2, 32))
        self.assertIn('visibility=workspace', data['pagination']['previous'])
        self.assertTrue(data['results'][0]['gadgets_url'].startswith(self.path()))
        self.assertEqual(self.get(self.path(f'{self.dashboard.pk}/') + '?q=Plan').json()['redirect'], self.path(self.dashboard.slug + '/') + '?q=Plan')

    def test_auth_csrf_methods_foreign_workspace_and_removed_routes(self):
        guarded = Client(enforce_csrf_checks=True)
        self.login(self.member, guarded)
        self.assertEqual(guarded.post(self.endpoint(self.path('create/')), {'name': 'X'}).status_code, 403)
        self.assertEqual(self.get(self.path(f'{self.dashboard.slug}/arrange/')).status_code, 405)
        self.assertEqual(self.client.put(self.endpoint(self.path())).status_code, 405)
        foreign_path = scoped_workplace_app_path(self.other, 'dashboards', self.dashboard.slug + '/')
        self.assertEqual(self.get(foreign_path).status_code, 403)
        self.assertEqual(self.get(self.path(self.dashboard.slug + '/copy/')).status_code, 404)
        self.client.logout()
        self.assertEqual(self.get(self.path()).status_code, 401)
