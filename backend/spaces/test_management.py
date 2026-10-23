from .testing import make_space

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import SpaceTask, Space, SpaceMembership
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.navigation import sidebar_favorite_is_active
from workplaces.services import scoped_workplace_app_path
from .services import manageable_spaces, manage_space


class SpaceManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username='manage-owner', email='owner@example.test')
        cls.admin = User.objects.create_user(username='manage-admin', email='admin@example.test')
        cls.member = User.objects.create_user(username='manage-member', email='member@example.test')
        cls.other = User.objects.create_user(username='manage-other', email='other@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Zarządzanie')
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.admin, role='admin')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member, role='member')
        cls.private = make_space(user=cls.owner, workplace=cls.workspace, name='Prywatny produkt', visibility='private', private_owner=cls.owner)
        SpaceMembership.objects.create(space=cls.private, user=cls.admin, role='admin')
        SpaceMembership.objects.create(space=cls.private, user=cls.member, role='member')
        cls.hidden = make_space(user=cls.owner, workplace=cls.workspace, name='Poufny projekt', visibility='private', private_owner=cls.owner)
        cls.public = make_space(user=cls.owner, workplace=cls.workspace, name='Publiczny produkt', visibility='public')
        cls.foreign_project = make_space(user=cls.other, workplace=cls.foreign, name='Obcy projekt')

    def setUp(self):
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix='manage/'):
        return scoped_workplace_app_path(self.workspace, 'spaces', suffix)

    def test_retired_management_redirects_to_catalog_in_plain_and_scoped_urls(self):
        for url in ['/spaces/manage/', self.url()]:
            response = self.client.get(url, {'q': 'produkt', 'kind': 'business', 'tab': 'private', 'page': 2})
            self.assertRedirects(response, self.url('') + '?q=produkt&kind=business&tab=private&page=2')
        daily = self.client.get(self.url(''))
        self.assertTemplateUsed(daily, 'spaces/index.html')
        self.assertContains(daily, 'data-sidebar-mode="workspace"')
        self.assertNotContains(daily, 'data-sidebar-navigation="administration"')
        self.assertNotContains(daily, 'Zarządzaj przestrzeniami')
        self.assertNotContains(daily, self.url())
        self.assertNotContains(daily, 'Obcy projekt')
        self.assertTrue(sidebar_favorite_is_active('spaces', daily.wsgi_request))
        settings = self.client.get('/settings/')
        self.assertNotContains(settings, 'Zarządzaj przestrzeniami')
        self.assertNotContains(settings, self.url())

    def test_redirect_in_page_and_navigation_api(self):
        for prefix in ['/spaces/', self.url('')]:
            target = prefix + 'manage/?q=produkt&kind=business&page=2&management=company'
            destination = self.url('') + '?q=produkt&kind=business&page=2'
            for api in ['page', 'navigation']:
                endpoint = scoped_workplace_app_path(self.workspace, 'api', f'v1/{api}/')
                response = self.client.get(endpoint, {'url': target})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {'redirect': destination})
        endpoint = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        data = self.client.get(endpoint, {'url': self.url('')}).json()['data']
        self.assertNotIn('management', data)
        self.assertNotIn('management_filter', data)

    def test_management_respects_workspace_and_private_access(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url(), follow=True)
        self.assertContains(response, 'Prywatny produkt')
        self.assertContains(response, 'Publiczny produkt')
        self.assertNotContains(response, 'Poufny projekt')
        self.assertNotContains(response, 'Obcy projekt')
        SpaceMembership.objects.filter(space=self.private, user=self.admin).delete()
        self.assertNotContains(self.client.get(self.url(), follow=True), 'Prywatny produkt')

    def test_members_and_observers_keep_daily_access_without_management(self):
        section = self.public
        SpaceTask.objects.create(created_by=self.owner, space=section, title='Przydział bez zarządzania', assignee=self.member)
        self.client.force_login(self.member)
        for role in ['member', 'observer']:
            SpaceMembership.objects.filter(space=self.private, user=self.member).update(role=role)
            self.assertContains(self.client.get(self.url('')), 'Prywatny produkt')
            self.assertRedirects(self.client.get(self.url()), self.url(''))
            for suffix in ['manage/create/', f'manage/{self.private.pk}/edit/']:
                self.assertEqual(self.client.get(self.url(suffix)).status_code, 403)
            settings = self.client.get('/settings/')
            self.assertNotContains(settings, 'Ustawienia, konfiguracje i dostęp do przestrzeni')

    def test_project_admin_and_public_leader_manage_only_their_spaces(self):
        self.client.force_login(self.member)
        SpaceMembership.objects.filter(space=self.private, user=self.member).update(role='admin')
        response = self.client.get(self.url(), follow=True)
        self.assertEqual({space.pk for space in response.context['page']}, {self.private.pk, self.public.pk})
        self.assertEqual(set(manageable_spaces(response.wsgi_request).values_list('pk', flat=True)), {self.private.pk})
        self.public.responsible_user = self.member
        self.public.save()
        response = self.client.get(self.url(), follow=True)
        self.assertEqual(set(manageable_spaces(response.wsgi_request).values_list('pk', flat=True)), {self.private.pk, self.public.pk})
        self.assertTrue(all(manage_space(response.wsgi_request, space) for space in response.context['page']))

    def test_redirect_keeps_catalog_search_kind_and_pagination(self):
        self.client.force_login(self.admin)
        space = self.public
        space.kind = 'software'
        space.management = 'company'
        space.save()
        response = self.client.get(self.url(), {'q': space.key.lower(), 'kind': 'software', 'management': 'company'}, follow=True)
        self.assertEqual([space.pk for space in response.context['page']], [self.public.pk])
        response = self.client.get(self.url(), {'q': space.key, 'management': 'team'}, follow=True)
        self.assertEqual([space.pk for space in response.context['page']], [self.public.pk])
        self.assertNotContains(response, 'Każdy sposób zarządzania')
        for number in range(31):
            make_space(user=self.owner, workplace=self.workspace, name=f'Filtrowany {number:02}')
        response = self.client.get(self.url(), {'q': 'Filtrowany', 'page': '2', 'kind': 'business'}, follow=True)
        self.assertEqual(response.context['page'].paginator.count, 31)
        self.assertEqual(len(response.context['page']), 1)
        self.assertContains(response, 'q=Filtrowany')
        self.assertContains(response, 'kind=business')

    def test_catalog_count_does_not_reveal_hidden_tasks(self):
        section = self.private
        SpaceTask.objects.create(created_by=self.owner, space=section, title='Dostępne')
        SpaceTask.objects.create(created_by=self.owner, space=section, title='Ukryte', visibility='private', private_owner=self.member)
        response = self.client.get(self.url(), {'q': self.private.key}, follow=True)
        row = response.context['page'][0]
        self.assertEqual(row.item_count, 1)

    def test_legacy_create_and_edit_return_to_catalog(self):
        create_url = self.url('manage/create/')
        response = self.client.get(create_url)
        self.assertTemplateUsed(response, 'spaces/index.html')
        self.assertContains(response, 'data-sidebar-mode="workspace"')
        self.assertEqual(response.context['modal']['directory_url'], self.url(''))
        payload = {'name': 'Nowa przestrzeń', 'key': 'NOWA', 'kind': 'business', 'template': 'tasks', 'management': 'team', 'visibility': 'private'}
        invalid = self.client.post(create_url, {**payload, 'key': '!'})
        self.assertEqual(invalid.status_code, 400)
        self.assertTemplateUsed(invalid, 'spaces/index.html')
        self.assertContains(invalid, 'data-sidebar-mode="workspace"', status_code=400)
        response = self.client.post(create_url, payload, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.json(), {'saved': True, 'url': self.url('')})
        space = Space.objects.get(name='Nowa przestrzeń')
        response = self.client.post(self.url(f'manage/{space.pk}/edit/'), {**payload, 'name': 'Zmieniona przestrzeń'}, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.json(), {'saved': True, 'url': self.url('')})
        self.assertContains(self.client.get(self.url(), follow=True), 'Zmieniona przestrzeń')
        self.assertRedirects(self.client.post(self.url(f'{space.pk}/favorite/'), {'directory': 'manage'}), self.url(''))

    def test_management_edit_still_checks_each_space(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(self.url(f'manage/{self.hidden.pk}/edit/'), {}).status_code, 404)
        self.client.force_login(self.member)
        self.public.responsible_user = self.member
        self.public.save()
        self.assertEqual(self.client.post(self.url(f'manage/{self.private.pk}/edit/'), {}).status_code, 403)

    def test_empty_workspace_and_method_guards(self):
        empty = create_workplace_for_user(self.owner, 'Pusty')
        response = self.client.get(scoped_workplace_app_path(empty, 'spaces', 'manage/'), follow=True)
        self.assertContains(response, 'Brak przestrzeni')
        self.assertEqual(self.client.post(self.url()).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(self.url()).status_code, 302)
