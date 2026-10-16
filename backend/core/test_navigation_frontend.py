import json
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from dashboard.models import Dashboard, SavedTaskFilter
from resources.models import Resource
from spaces.models import SpaceTask
from spaces.testing import make_space
from workplaces.models import SidebarFavorite, WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class ReactNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='navigation-owner', email='nav-owner@example.test')
        cls.member = users.objects.create_user(username='navigation-member', email='nav-member@example.test')
        cls.other = users.objects.create_user(username='navigation-other', email='nav-other@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Workspace nawigacji')
        cls.personal = create_workplace_for_user(cls.member, 'Osobisty Workspace')
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy Workspace')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Widoczna przestrzeń', key='NAV')
        cls.private = make_space(user=cls.owner, workplace=cls.workspace, name='Poufna przestrzeń', visibility='private', private_owner=cls.owner)
        cls.task = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='Zadanie nawigacji')
        cls.hidden = SpaceTask.objects.create(space=cls.private, created_by=cls.owner, title='Poufne zadanie', assignee=cls.member)
        cls.dashboard = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Widoczny pulpit', visibility='workspace')
        cls.filter = SavedTaskFilter.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Widoczny filtr', visibility='workspace')
        cls.secret_dashboard = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Poufny pulpit', visibility='private')
        cls.secret_filter = SavedTaskFilter.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Poufny filtr', visibility='private')
        cls.resource = Resource.objects.create(owner=cls.owner, workplace=cls.workspace, name='Zasób nawigacji')

    def setUp(self):
        self.client.force_login(self.member)
        self.activate(self.workspace)

    def activate(self, workplace):
        session = self.client.session
        session['active_workplace_id'] = workplace.pk
        session.save()

    def endpoint(self, kind='navigation', workplace=None):
        return scoped_workplace_app_path(workplace or self.workspace, 'api', f'v1/{kind}/')

    def nav(self, target, **kwargs):
        return self.client.get(self.endpoint(), {'url': target}, **kwargs)

    def api(self, target, body=None, client=None):
        url = self.endpoint('page') + '?' + urlencode({'url': target})
        return (client or self.client).get(url) if body is None else (client or self.client).post(url, json.dumps(body), content_type='application/json')

    def test_shell_has_single_react_owner_and_no_legacy_navigation_controllers(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-react-global-panels', count=1)
        for name in ('layout', 'space-navigation', 'pulpit-navigation', 'filter-navigation', 'space-picker', 'notifications', 'global-search', 'notifications-panel', 'sticky-note'):
            self.assertNotContains(response, f'js/{name}.js')
        self.assertContains(response, self.endpoint())

    def test_navigation_requires_session_is_get_only_and_never_caches(self):
        client = Client()
        self.assertEqual(client.get(self.endpoint(), {'url': '/settings/'}).status_code, 401)
        self.assertEqual(self.client.post(self.endpoint(), {'url': '/settings/'}).status_code, 405)
        response = self.nav('/settings/')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response.json()['page']['type'], 'settings')
        self.assertTrue(response.json()['csrf_token'])

    def test_business_screens_return_data_and_shell_without_html(self):
        targets = [(reverse('profile'), 'account-profile'), (reverse('settings'), 'settings'),
                   (reverse('for_you'), 'for-you'), (reverse('planner:index'), 'calendar'),
                   (reverse('spaces:index'), 'space-directory'), (reverse('teams:index'), 'teams'),
                   (reverse('filters:index'), 'filter-directory'), (reverse('pulpits:index'), 'pulpit-directory'),
                   (reverse('documents:library'), 'document-directory'), (reverse('office:index'), 'document-directory'),
                   (reverse('workplaces:workplaces'), 'workspace-directory'), (reverse('resources:index'), 'resources')]
        for target, kind in targets:
            with self.subTest(target=target):
                response = self.nav(target)
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload['page']['type'], kind)
                self.assertEqual(payload['shell']['account_id'], str(self.member.pk))
                self.assertEqual(payload['shell']['workplace_id'], str(self.workspace.pk))
                self.assertNotIn('html', payload)
                self.assertNotIn('<!DOCTYPE', response.content.decode())
                self.assertTrue(payload['page']['styles'])

    def test_private_task_and_foreign_context_stay_inaccessible(self):
        visible = scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/tasks/{self.task.work_item.key}/')
        hidden = scoped_workplace_app_path(self.workspace, 'space', f'{self.private.slug}/tasks/{self.hidden.work_item.key}/')
        self.assertEqual(self.nav(visible).status_code, 200)
        self.assertEqual(self.nav(hidden).status_code, 404)
        self.assertEqual(self.nav(scoped_workplace_app_path(self.personal, 'spaces')).status_code, 403)
        self.membership.delete()
        self.assertEqual(self.nav(visible).status_code, 403)

    def test_scoped_navigation_survives_another_tabs_active_workspace(self):
        self.activate(self.personal)
        response = self.nav(scoped_workplace_app_path(self.workspace, 'spaces'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['shell']['workplace_id'], str(self.workspace.pk))
        self.assertIn(self.space.name, [row['name'] for row in response.json()['page']['data']['results']])

    def test_unregistered_targets_and_external_urls_are_rejected(self):
        for target in ('https://example.test/', '//example.test/', '/\\example.test/', '/admin/', reverse('logout')):
            with self.subTest(target=target):
                self.assertIn(self.nav(target).status_code, (400, 404))

    def test_sidebar_collections_and_refresh_recheck_current_acl(self):
        self.space.favorited_by.add(self.member)
        self.dashboard.favorited_by.add(self.member)
        self.filter.favorited_by.add(self.member)
        payload = self.nav(reverse('spaces:index')).json()['shell']
        text = json.dumps(payload, ensure_ascii=False)
        for name in (self.private.name, self.secret_dashboard.name, self.secret_filter.name, self.foreign.name):
            self.assertNotIn(name, text)
        self.assertCountEqual([item['name'] for item in payload['workplaces']], [self.workspace.name, self.personal.name])
        self.assertEqual(payload['collections'][1]['starred'][0]['id'], str(self.space.pk))
        self.space.visibility = 'private'; self.space.private_owner = self.owner; self.space.save()
        refreshed = self.client.get(self.endpoint('shell'), {'url': reverse('spaces:index')})
        self.assertEqual(refreshed.status_code, 200)
        self.assertNotIn(self.space.name, refreshed.content.decode())
        self.assertNotIn('page', refreshed.json())

    def test_pickers_use_typed_results_and_same_visibility_as_original_views(self):
        for name, wanted, secret in [('spaces:search', self.space.name, self.private.name), ('pulpits:search', self.dashboard.name, self.secret_dashboard.name), ('filters:lookup', self.filter.name, self.secret_filter.name)]:
            with self.subTest(name=name):
                target = reverse(name) + '?q=' + 'Widocz'
                response = self.api(target)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertNotIn('html', data)
                self.assertIn(wanted, [row['name'] for row in data['results']])
                self.assertNotIn(secret, json.dumps(data, ensure_ascii=False))
                self.assertIn('html', self.client.get(target, follow=True).json())
        self.membership.delete()
        self.assertEqual(self.api(reverse('spaces:search') + '?q=Widocz').status_code, 403)

    def test_favorites_are_personal_typed_and_keep_order(self):
        target = reverse('workplaces:toggle-sidebar-favorite', args=[self.workspace.pk])
        owner_before = list(SidebarFavorite.objects.filter(user=self.owner).values_list('item_key', 'position'))
        for key in ('calendar', 'resources'):
            response = self.api(target, {'item_key': key, 'favorite_action': 'add'})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('html', response.json())
        reorder = reverse('workplaces:reorder-sidebar-favorites', args=[self.workspace.pk])
        response = self.api(reorder, {'item_order': json.dumps(['resources', 'calendar'])})
        self.assertEqual([item['key'] for item in response.json()['favorites']], ['resources', 'calendar'])
        self.assertEqual(list(SidebarFavorite.objects.filter(user=self.owner).values_list('item_key', 'position')), owner_before)
        response = self.api(target, {'item_key': 'calendar', 'favorite_action': 'remove'})
        self.assertEqual([item['key'] for item in response.json()['favorites']], ['resources'])
        self.assertEqual(self.api(target, {'item_key': 'tasks-all', 'favorite_action': 'add'}).status_code, 400)
        self.assertEqual(self.api(reorder, {'item_order': '["calendar"]'}).status_code, 400)
        self.assertEqual(list(SidebarFavorite.objects.filter(user=self.member, workplace=self.workspace).values_list('item_key', flat=True)), ['resources'])

    def test_favorites_require_csrf_and_membership(self):
        client = Client(enforce_csrf_checks=True); client.force_login(self.member)
        target = reverse('workplaces:toggle-sidebar-favorite', args=[self.workspace.pk])
        self.assertEqual(self.api(target, {'item_key': 'calendar', 'favorite_action': 'add'}, client=client).status_code, 403)
        foreign = reverse('workplaces:toggle-sidebar-favorite', args=[self.foreign.pk])
        self.assertEqual(self.api(foreign, {'item_key': 'calendar', 'favorite_action': 'add'}).status_code, 404)

    def test_resource_direct_editor_navigation_keeps_scoped_form(self):
        target = scoped_workplace_app_path(self.workspace, 'resources', f'{self.resource.pk}/edit/')
        payload = self.nav(target).json()['page']
        self.assertEqual(payload['data']['editor']['id'], self.resource.pk)
        self.assertIn(self.workspace.slug, payload['data']['api_url'])

    def test_refresh_can_update_sidebar_from_resources_without_loading_page(self):
        response = self.client.get(self.endpoint('shell'), {'url': scoped_workplace_app_path(self.workspace, 'resources', '?q=test')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['account_id'], str(self.member.pk))
        self.assertNotIn('page', response.json())

    def test_csrf_token_from_navigation_authorizes_the_following_mutation(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        response = client.get(self.endpoint(), {'url': reverse('spaces:index')})
        self.assertEqual(response.status_code, 200)
        target = reverse('workplaces:toggle-sidebar-favorite', args=[self.workspace.pk])
        response = client.post(self.endpoint('page') + '?' + urlencode({'url': target}),
                               json.dumps({'item_key': 'calendar', 'favorite_action': 'add'}),
                               content_type='application/json', HTTP_X_CSRFTOKEN=response.json()['csrf_token'])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SidebarFavorite.objects.filter(user=self.member, workplace=self.workspace, item_key='calendar').exists())

    def test_management_modes_and_editor_links_match_server_context(self):
        self.client.force_login(self.owner)
        self.activate(self.workspace)
        for name, mode in [('spaces:manage', 'administration'), ('filters:manage', 'filters-management'), ('pulpits:manage', 'pulpits-management'), ('workplaces:workplaces', 'workplaces'), ('settings', 'settings')]:
            with self.subTest(name=name):
                response = self.nav(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['shell']['mode'], mode)
        response = self.nav(reverse('pulpits:edit', args=[self.dashboard.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['shell']['mode'], 'pulpit-editor')
        self.assertTrue(response.json()['shell']['editor']['links'])
