from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import Dashboard


class PulpitNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='pulpit-nav-owner', email='nav-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='pulpit-nav-member', email='nav-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Nawigacja pulpitów')
        cls.other = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.first = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Pierwszy pulpit', visibility='workspace')
        cls.second = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Drugi pulpit', visibility='workspace')
        cls.private = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Prywatny pulpit')
        cls.foreign = Dashboard.objects.create(owner=cls.owner, workplace=cls.other, created_by=cls.owner, name='Obcy pulpit', visibility='workspace')

    def setUp(self):
        self.login(self.owner)

    def login(self, user, client=None):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'dashboards', suffix)

    def ids(self, response, kind):
        return [item.pk for item in response.context[f'navigation_{kind}_dashboards']]

    def test_navigation_matches_reference_and_default_dashboard_is_preserved(self):
        response = self.client.get(self.url())
        for text in ['Pulpit domyślny', 'Więcej pulpitów', 'Wyszukaj wszystkie pulpity', 'Wyświetl wszystkie pulpity', 'Utwórz pulpit', 'Zarządzaj pulpitami']:
            self.assertContains(response, text)
        self.assertEqual(self.ids(response, 'recent'), [])
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_search_rechecks_access_and_workspace_in_plain_and_scoped_urls(self):
        self.login(self.member)
        self.private.visibility = 'selected'
        self.private.save()
        self.private.shared_with.add(self.member)
        for url in ['/dashboards/search/', self.url('search/')]:
            with self.subTest(url=url):
                response = self.client.get(url, {'q': 'pulpit'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['count'], 3)
                self.assertEqual(response.headers['Cache-Control'], 'private, no-store')
                self.assertIn(self.url(f'{self.first.pk}/'), response.json()['html'])
                self.assertNotIn('Obcy pulpit', response.json()['html'])
        self.private.shared_with.remove(self.member)
        self.assertEqual(self.client.get(self.url('search/'), {'q': 'Prywatny'}).json()['count'], 0)
        self.first.visibility = 'private'
        self.first.save()
        self.assertEqual(self.client.get(self.url('search/'), {'q': 'Pierwszy'}).json()['count'], 0)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).delete()
        self.assertRedirects(self.client.get(self.url('search/'), {'q': 'Drugi'}), '/workplaces/', fetch_redirect_response=False)

    def test_search_matches_name_and_description_limits_results_and_escapes_text(self):
        self.first.description = 'Wyniki sprzedaży'
        self.first.save()
        self.assertEqual(self.client.get(self.url('search/'), {'q': 'WYNIKI'}).json()['count'], 1)
        for number in range(22):
            Dashboard.objects.create(owner=self.owner, workplace=self.workspace, created_by=self.owner, name=f'Wyszukiwanie {number:02}')
        data = self.client.get(self.url('search/'), {'q': 'Wyszukiwanie'}).json()
        self.assertEqual(data['count'], 20)
        self.assertIn('Więcej wyników', data['html'])
        self.assertNotIn('Wyszukiwanie 20', data['html'])
        self.first.name = '<script>Pulpit</script>'
        self.first.save()
        html = self.client.get(self.url('search/'), {'q': '<script>'}).json()['html']
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)

    def test_search_empty_query_login_and_get(self):
        for url in ['/dashboards/search/', self.url('search/')]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, {'q': '   '}).json()['count'], 0)
                self.assertEqual(self.client.post(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(self.url('search/')).status_code, 302)

    def test_recent_visits_are_immediate_personal_and_workplace_scoped(self):
        for url, dashboard in [(f'/dashboards/{self.first.pk}/', self.first), (self.url(f'{self.second.pk}/'), self.second), (self.url(f'{self.first.pk}/'), self.first)]:
            self.assertEqual(self.ids(self.client.get(url), 'recent')[0], dashboard.pk)
        response = self.client.get(self.url())
        self.assertEqual(self.ids(response, 'recent'), [self.first.pk, self.second.pk])
        self.login(self.member)
        self.assertEqual(self.ids(self.client.get(self.url()), 'recent'), [])

    def test_stars_and_history_recheck_access_without_duplicates(self):
        self.login(self.member)
        self.first.favorited_by.add(self.member)
        self.foreign.favorited_by.add(self.member)
        self.client.get(self.url(f'{self.first.pk}/'))
        self.client.get(self.url(f'{self.second.pk}/'))
        response = self.client.get(self.url())
        self.assertEqual(self.ids(response, 'starred'), [self.first.pk])
        self.assertEqual(self.ids(response, 'recent'), [self.second.pk])
        for item in [self.first, self.second]:
            item.visibility = 'private'
            item.save()
        response = self.client.get(self.url())
        self.assertEqual(self.ids(response, 'starred'), [])
        self.assertEqual(self.ids(response, 'recent'), [])
        self.assertNotContains(response, 'Pierwszy pulpit')
        self.assertEqual(self.client.post(self.url(f'{self.first.pk}/favorite/'), HTTP_X_PULPIT_NAVIGATION='true').status_code, 404)

    def test_favorite_ajax_is_personal_post_csrf_and_safe_return(self):
        self.login(self.member)
        url = self.url(f'{self.first.pk}/favorite/')
        self.assertEqual(self.client.post(url, HTTP_X_PULPIT_NAVIGATION='true').json(), {'saved': True})
        self.assertTrue(self.first.favorited_by.filter(pk=self.member.pk).exists())
        self.assertFalse(self.first.favorited_by.filter(pk=self.owner.pk).exists())
        self.assertEqual(self.ids(self.client.get(self.url()), 'starred'), [self.first.pk])
        target = self.url('?tab=all&q=Pierwszy')
        self.assertRedirects(self.client.post(url, {'next': target}), target, fetch_redirect_response=False)
        for target in ['//example.test/', 'https://example.test/']:
            self.assertTrue(self.client.post(url, {'next': target}).url.startswith(self.url()))
        self.assertEqual(self.client.get(url).status_code, 405)
        secure = Client(enforce_csrf_checks=True)
        self.login(self.member, secure)
        self.assertEqual(secure.post(url, HTTP_X_PULPIT_NAVIGATION='true').status_code, 403)

    def test_navigation_limits_starred_and_recent_without_duplicates(self):
        items = []
        for number in range(8):
            item = Dashboard.objects.create(owner=self.owner, workplace=self.workspace, created_by=self.owner, name=f'Pulpit {number}')
            items.append(item)
            self.client.get(self.url(f'{item.pk}/'))
        items[0].favorited_by.add(self.owner)
        response = self.client.get(self.url())
        self.assertEqual(self.ids(response, 'starred'), [items[0].pk])
        self.assertEqual(self.ids(response, 'recent'), [item.pk for item in reversed(items[2:])])
        for item in items:
            item.favorited_by.add(self.owner)
        response = self.client.get(self.url())
        self.assertEqual(self.ids(response, 'starred'), [item.pk for item in items[:6]])
        self.assertEqual(self.ids(response, 'recent'), [])
        self.assertEqual(self.client.get(self.url('?tab=all&q=Pulpit ')).context['page'].paginator.count, 11)
