from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import Dashboard, DashboardGroup


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

    def group(self, **kwargs):
        return DashboardGroup.objects.create(owner=self.owner, workplace=self.workspace, user=self.owner, name='Obsługa klienta', **kwargs)

    def ids(self, response, kind):
        return [item.pk for item in response.context[f'navigation_{kind}_dashboards']]

    def test_navigation_matches_reference_and_default_dashboard_is_preserved(self):
        response = self.client.get(self.url())
        for text in ['Pulpit domyślny', 'Pokaż wszystkie pulpity', 'Utwórz pulpit', 'Zarządzaj pulpitami']:
            self.assertContains(response, text)
        self.assertEqual(self.ids(response, 'recent'), [])
        self.assertEqual(self.client.get('/').status_code, 200)

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
        target = self.url('groups/')
        self.assertRedirects(self.client.post(url, {'next': target}), target, fetch_redirect_response=False)
        for target in ['//example.test/', 'https://example.test/']:
            self.assertTrue(self.client.post(url, {'next': target}).url.startswith(self.url()))
        self.assertEqual(self.client.get(url).status_code, 405)
        secure = Client(enforce_csrf_checks=True)
        self.login(self.member, secure)
        self.assertEqual(secure.post(url, HTTP_X_PULPIT_NAVIGATION='true').status_code, 403)

    def test_create_edit_duplicate_and_delete_group_keep_dashboards(self):
        response = self.client.post(self.url('groups/create/'), {'name': 'Obsługa klienta', 'dashboards': [self.first.pk]}, HTTP_X_PULPIT_MODAL='true')
        self.assertTrue(response.json()['saved'])
        group = DashboardGroup.objects.get()
        self.assertEqual((group.owner, group.user, group.workplace), (self.owner, self.owner, self.workspace))
        response = self.client.post(self.url('groups/create/'), {'name': 'obsługa klienta'}, HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Masz już grupę', response.json()['html'])
        response = self.client.post(self.url(f'groups/{group.pk}/edit/'), {'name': 'Wydanie', 'dashboards': [self.second.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(group.dashboards.all()), [self.second])
        self.assertEqual(self.client.get(self.url(f'groups/{group.pk}/delete/')).status_code, 405)
        self.client.post(self.url(f'groups/{group.pk}/delete/'))
        self.assertFalse(DashboardGroup.objects.exists())
        self.assertTrue(Dashboard.objects.filter(pk=self.second.pk).exists())

    def test_groups_and_direct_forms_use_management_sidebar_in_plain_and_scoped_urls(self):
        group = self.group()
        for prefix in ['/dashboards/', self.url()]:
            for suffix in ['groups/', 'groups/create/', f'groups/{group.pk}/edit/']:
                response = self.client.get(prefix + suffix)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'dashboard/pulpits/groups.html')
                self.assertTrue(response.context['pulpits_management_mode'])
                self.assertTrue(response.context['pulpit_groups_management_mode'])
                self.assertContains(response, 'data-sidebar-mode="pulpits-management"')
                self.assertContains(response, 'data-sidebar-navigation="workspace" hidden')
                self.assertNotContains(response, 'data-sidebar-navigation="pulpits-management" hidden')
                self.assertContains(response, 'Grupy pulpitów | ancore')
            response = self.client.post(prefix + 'groups/create/', {'name': ''})
            self.assertEqual(response.status_code, 400)
            self.assertTrue(response.context['pulpit_groups_management_mode'])
        response = self.client.get(self.url())
        self.assertFalse(response.context['pulpits_management_mode'])
        self.assertNotContains(response, 'Twoje grupy')
        response = self.client.get(self.url('manage/'))
        self.assertTrue(response.context['pulpits_management_mode'])
        self.assertFalse(response.context['pulpit_groups_management_mode'])
        self.assertContains(response, f'href="{self.url("groups/")}"')

    def test_groups_never_leak_private_or_foreign_dashboards_or_grant_access(self):
        self.login(self.member)
        group = DashboardGroup.objects.create(owner=self.owner, workplace=self.workspace, user=self.member, name='Moja grupa')
        group.dashboards.add(self.first, self.private, self.foreign)
        response = self.client.get(self.url('groups/'))
        self.assertEqual(response.context['groups'][0].dashboard_count, 1)
        response = self.client.get(self.url(f'?tab=all&group={group.pk}'))
        self.assertEqual([row.pk for row in response.context['dashboards']], [self.first.pk])
        self.assertEqual([row.pk for row in response.context['navigation_dashboard_groups'][0].navigation_dashboards], [self.first.pk])
        self.assertNotContains(response, 'Prywatny pulpit')
        self.assertNotContains(response, 'Obcy pulpit')
        self.assertEqual(self.client.get(self.url(f'{self.private.pk}/')).status_code, 404)
        self.assertEqual(self.client.post(self.url(f'groups/{group.pk}/edit/'), {'name': 'Moja grupa', 'dashboards': [self.private.pk]}, HTTP_X_PULPIT_MODAL='true').status_code, 400)

    def test_another_users_groups_and_other_workspaces_are_unavailable(self):
        group = self.group()
        foreign = DashboardGroup.objects.create(owner=self.owner, workplace=self.other, user=self.owner, name='Obca grupa')
        for item, viewer in [(group, self.member), (foreign, self.owner)]:
            self.login(viewer)
            self.assertEqual(self.client.get(self.url(f'?tab=all&group={item.pk}')).status_code, 404)
            self.assertEqual(self.client.get(self.url(f'groups/{item.pk}/edit/')).status_code, 404)
            self.assertEqual(self.client.post(self.url(f'groups/{item.pk}/delete/')).status_code, 404)
            self.assertEqual(self.client.post(self.url(f'{self.first.pk}/groups/'), {'groups': [item.pk]}, HTTP_X_PULPIT_MODAL='true').status_code, 400)

    def test_viewer_organizes_shared_dashboard_without_changing_others_or_revision(self):
        owner_group = self.group()
        owner_group.dashboards.add(self.first)
        member_group = DashboardGroup.objects.create(owner=self.owner, workplace=self.workspace, user=self.member, name='Moje pulpity')
        self.login(self.member)
        url = self.url(f'{self.first.pk}/groups/')
        self.assertTrue(self.client.post(url, {'groups': [member_group.pk]}, HTTP_X_PULPIT_MODAL='true').json()['saved'])
        self.assertTrue(member_group.dashboards.filter(pk=self.first.pk).exists())
        self.assertTrue(owner_group.dashboards.filter(pk=self.first.pk).exists())
        self.first.refresh_from_db()
        self.assertEqual(self.first.revision, 0)
        self.client.post(url, {})
        self.assertFalse(member_group.dashboards.exists())
        self.assertTrue(owner_group.dashboards.exists())

    def test_group_filter_survives_search_tabs_and_favorite(self):
        group = self.group()
        group.dashboards.add(self.first)
        target = self.url(f'?tab=all&group={group.pk}&q=Pierwszy')
        response = self.client.get(target)
        self.assertEqual([row.pk for row in response.context['dashboards']], [self.first.pk])
        self.assertTrue(all(f'group={group.pk}' in tab['url'] for tab in response.context['tabs']))
        self.assertEqual(self.client.post(self.url(f'{self.first.pk}/favorite/'), {'next': target}, HTTP_X_PULPIT_MODAL='true').json()['url'], target)

    def test_empty_group_and_overflow_are_linked_to_complete_catalog(self):
        group = self.group()
        response = self.client.get(self.url())
        self.assertContains(response, 'Brak pulpitów')
        for number in range(8):
            item = Dashboard.objects.create(owner=self.owner, workplace=self.workspace, created_by=self.owner, name=f'Pulpit {number}')
            group.dashboards.add(item)
            item.favorited_by.add(self.owner)
        response = self.client.get(self.url())
        nav_group = response.context['navigation_dashboard_groups'][0]
        self.assertEqual(len(self.ids(response, 'starred')), 6)
        self.assertEqual(len(nav_group.navigation_dashboards), 6)
        self.assertTrue(nav_group.has_more)
        self.assertContains(response, 'Pokaż całą grupę')
        response = self.client.get(nav_group.url)
        self.assertEqual(response.context['page'].paginator.count, 8)
