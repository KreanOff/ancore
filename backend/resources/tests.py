from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.navigation import sidebar_favorite_catalog, sidebar_favorite_is_active
from workplaces.services import scoped_workplace_app_path
from .models import Resource


class ResourceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='resources-owner', email='resources-owner@example.test')
        cls.member = users.objects.create_user(username='resources-member', email='resources-member@example.test', first_name='Jan', last_name='Testowy')
        cls.other = users.objects.create_user(username='resources-other', email='resources-other@example.test')
        cls.team = create_workplace_for_user(cls.owner, 'Zespół zasobów')
        cls.second = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy Workspace')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.team, user=cls.member, role='member')
        cls.resource = Resource.objects.create(owner=cls.owner, workplace=cls.team, name='Laptop zespołowy', inventory_number='EQ-001', assigned_to=cls.member, created_by=cls.owner)
        cls.hidden = Resource.objects.create(owner=cls.owner, workplace=cls.second, name='Laptop drugiego Workspace', inventory_number='EQ-001')
        cls.foreign_resource = Resource.objects.create(owner=cls.other, workplace=cls.foreign, name='Laptop obcego zespołu')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.team.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.team, 'resources', suffix)

    def payload(self, **changes):
        return {'name': 'Monitor', 'kind': 'equipment', 'status': 'available', **changes}

    def test_list_scopes_owner_and_workspace_for_both_routes(self):
        for url in [reverse('resources:index'), self.url()]:
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual([row.pk for row in response.context['resources']], [self.resource.pk])
        corrupt = Resource.objects.create(owner=self.other, workplace=self.team, name='Inny właściciel')
        self.assertNotContains(self.client.get(self.url()), corrupt.name)

    def test_create_uses_workspace_owner_and_actual_actor(self):
        for url in [reverse('resources:create'), self.url('create/')]:
            with self.subTest(url=url):
                response = self.client.post(url, self.payload(assigned_to=self.member.pk, owner=self.other.pk, workplace=self.foreign.pk), HTTP_X_RESOURCE_MODAL='true')
                self.assertTrue(response.json()['saved'])
                item = Resource.objects.latest('pk')
                self.assertEqual((item.owner_id, item.workplace_id, item.created_by_id, item.updated_by_id, item.assigned_to_id), (self.owner.pk, self.team.pk, self.member.pk, self.member.pk, self.member.pk))
                self.assertEqual(response.json()['url'], self.url())

    def test_edit_and_clear_assignment(self):
        for url in [reverse('resources:edit', args=[self.resource.pk]), self.url(f'{self.resource.pk}/edit/')]:
            response = self.client.post(url, self.payload(name='Zmieniony laptop', status='maintenance', assigned_to=''), HTTP_X_RESOURCE_MODAL='true')
            self.assertTrue(response.json()['saved'])
            self.resource.refresh_from_db()
            self.assertEqual(self.resource.name, 'Zmieniony laptop')
            self.assertEqual(self.resource.status, 'maintenance')
            self.assertIsNone(self.resource.assigned_to)
            self.assertEqual(self.resource.created_by, self.owner)
            self.assertEqual(self.resource.updated_by, self.member)

    def test_other_workspaces_are_inaccessible(self):
        for item in [self.hidden, self.foreign_resource]:
            for suffix in [f'{item.pk}/edit/', f'{item.pk}/delete/']:
                for base in [self.url(), '/resources/']:
                    response = self.client.post(base + suffix, self.payload(), HTTP_X_RESOURCE_MODAL='true')
                    self.assertEqual(response.status_code, 404)
            self.assertEqual(self.client.get(self.url(f'{item.pk}/edit/')).status_code, 404)
        self.assertEqual(self.client.post(scoped_workplace_app_path(self.foreign, 'resources', 'create/'), self.payload()).status_code, 302)

    def test_assignment_does_not_grant_access_after_revocation(self):
        self.membership.delete()
        self.assertEqual(self.client.get(self.url()).status_code, 302)
        response = self.client.post(self.url(f'{self.resource.pk}/edit/'), self.payload())
        self.assertEqual(response.status_code, 302)
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.name, 'Laptop zespołowy')
        response = self.client.get(reverse('global_search'), {'q': 'Laptop'})
        self.assertNotIn(self.resource.name, str(response.json()))

    def test_assignment_choices_are_only_active_workspace_people(self):
        response = self.client.get(self.url('create/'))
        choices = set(response.context['modal']['form'].fields['assigned_to'].queryset)
        self.assertSetEqual(choices, {self.owner, self.member})
        for candidate in [self.other.pk, 999999]:
            response = self.client.post(self.url('create/'), self.payload(assigned_to=candidate), HTTP_X_RESOURCE_MODAL='true')
            self.assertEqual(response.status_code, 400)
            self.assertIn('id_assigned_to_error', response.json()['html'])
        self.other.is_active = False
        self.other.save()
        WorkplaceMembership.objects.create(workplace=self.team, user=self.other, role='member')
        response = self.client.post(self.url('create/'), self.payload(assigned_to=self.other.pk))
        self.assertEqual(response.status_code, 400)

    def test_form_after_member_leaves_can_clear_assignment(self):
        self.membership.delete()
        self.client.force_login(self.owner)
        response = self.client.get(self.url(f'{self.resource.pk}/edit/'))
        self.assertContains(response, 'Poprzednia osoba nie należy już')
        response = self.client.post(self.url(f'{self.resource.pk}/edit/'), self.payload(assigned_to=''))
        self.assertEqual(response.status_code, 302)
        self.resource.refresh_from_db()
        self.assertIsNone(self.resource.assigned_to)

    def test_duplicate_number_is_case_insensitive_and_preserves_input(self):
        response = self.client.post(self.url('create/'), self.payload(name='Ważny szkic', inventory_number=' eq-001 ', notes='Zachowaj opis'), HTTP_X_RESOURCE_MODAL='true')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Ważny szkic', response.json()['html'])
        self.assertIn('Zachowaj opis', response.json()['html'])
        self.assertIn('już istnieje', response.json()['html'])
        self.assertFalse(Resource.objects.filter(name='Ważny szkic').exists())
        response = self.client.post(self.url(f'{self.resource.pk}/edit/'), self.payload(inventory_number='EQ-001'))
        self.assertEqual(response.status_code, 302)

    def test_database_enforces_unique_number_but_allows_empty_numbers(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Resource.objects.create(owner=self.owner, workplace=self.team, name='Duplikat', inventory_number='eq-001')
        Resource.objects.create(owner=self.owner, workplace=self.team, name='Bez numeru 1')
        Resource.objects.create(owner=self.owner, workplace=self.team, name='Bez numeru 2')

    def test_dates_and_enum_validation(self):
        invalid = [
            {'purchased_on': '2026-10-10', 'expires_on': '2026-10-09'},
            {'purchased_on': 'invalid'}, {'kind': 'unknown'}, {'status': 'unknown'}, {'name': ' '},
        ]
        for values in invalid:
            self.assertEqual(self.client.post(self.url('create/'), self.payload(**values)).status_code, 400)
        response = self.client.post(self.url('create/'), self.payload(kind='license', purchased_on='2026-10-10', expires_on='2027-10-10'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Resource.objects.latest('pk').expires_on, date(2027, 10, 10))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Resource.objects.create(owner=self.owner, workplace=self.team, name='Złe daty', purchased_on=date(2026, 10, 10), expires_on=date(2026, 10, 9))

    def test_search_filters_sort_and_pagination_combine(self):
        Resource.objects.bulk_create([Resource(owner=self.owner, workplace=self.team, name=f'Licencja {i:02}', kind='license', status='in_use', assigned_to=self.member) for i in range(31)])
        params = {'q': 'Licencja', 'kind': 'license', 'status': 'in_use', 'assignee': 'me', 'sort': '-name', 'page_size': '25'}
        response = self.client.get(self.url(), params)
        self.assertEqual(len(response.context['resources']), 25)
        self.assertEqual(response.context['resources'][0].name, 'Licencja 30')
        next_url = response.context['resource_window']['next_url']
        for token in ['q=Licencja', 'kind=license', 'status=in_use', 'assignee=me', 'sort=-name', 'page=2']:
            self.assertIn(token, next_url)
        self.assertEqual(len(self.client.get(next_url).context['resources']), 6)
        self.assertEqual(len(self.client.get(self.url(), {'assignee': 'unassigned'}).context['resources']), 0)
        self.assertEqual(self.client.get(self.url(), {'page': 'invalid', 'page_size': 'bad', 'sort': 'bad'}).status_code, 200)

    def test_search_matches_inventory_serial_location_and_notes(self):
        self.resource.serial_number = 'SERIAL-314'
        self.resource.location = 'Magazyn'
        self.resource.notes = 'Kalibracja'
        self.resource.save()
        for query in ['EQ-001', 'SERIAL-314', 'Magazyn', 'Kalibracja']:
            self.assertEqual([r.pk for r in self.client.get(self.url(), {'q': query}).context['resources']], [self.resource.pk])

    def test_global_search_is_limited_scoped_and_links_to_editor(self):
        Resource.objects.bulk_create([Resource(owner=self.owner, workplace=self.team, name=f'Laptop {i:02}') for i in range(23)])
        response = self.client.get(reverse('global_search'), {'q': 'Laptop'})
        group = next(group for group in response.json()['groups'] if group['key'] == 'resources')
        self.assertEqual(len(group['results']), 20)
        self.assertTrue(group['has_more'])
        self.assertNotIn(self.hidden.name, str(group))
        self.assertNotIn(self.foreign_resource.name, str(group))
        for row in group['results']:
            self.assertTrue(row['url'].startswith(self.url()))
            self.assertTrue(row['url'].endswith('/edit/'))

    def test_delete_requires_post_and_csrf(self):
        url = self.url(f'{self.resource.pk}/delete/')
        self.assertEqual(self.client.get(url).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.member)
        self.assertEqual(csrf_client.post(url).status_code, 403)
        self.assertEqual(csrf_client.post(self.url('create/'), self.payload()).status_code, 403)
        self.assertEqual(csrf_client.post(self.url(f'{self.resource.pk}/edit/'), self.payload()).status_code, 403)
        self.assertTrue(self.client.post(url, HTTP_X_RESOURCE_MODAL='true').json()['saved'])
        self.assertFalse(Resource.objects.filter(pk=self.resource.pk).exists())
        self.assertTrue(Resource.objects.filter(pk=self.hidden.pk).exists())

    def test_sidebar_favorites_and_legacy_redirect(self):
        catalog = sidebar_favorite_catalog(self.team)
        self.assertEqual(catalog['resources']['url'], self.url())
        response = self.client.get(self.url())
        self.assertTrue(sidebar_favorite_is_active('resources', response.wsgi_request))
        self.assertContains(response, 'data-sidebar-source-item="resources"')
        self.assertRedirects(self.client.get('/resources/?kind=license'), self.url() + '?kind=license', fetch_redirect_response=False)

    def test_context_query_is_preserved_after_mutations_without_open_redirect(self):
        response = self.client.post(self.url('create/') + '?kind=equipment&page=2&next=https://example.test', self.payload(), HTTP_X_RESOURCE_MODAL='true')
        self.assertEqual(response.json()['url'], self.url() + '?kind=equipment&page=2')

    def test_workspace_delete_cascades_and_assignee_delete_keeps_resource(self):
        self.member.delete()
        self.resource.refresh_from_db()
        self.assertIsNone(self.resource.assigned_to)
        self.team.delete()
        self.assertFalse(Resource.objects.filter(pk=self.resource.pk).exists())
        self.assertTrue(Resource.objects.filter(pk=self.hidden.pk).exists())

    def test_anonymous_access_requires_login(self):
        self.client.logout()
        for url in [self.url(), self.url('create/'), self.url(f'{self.resource.pk}/edit/'), self.url(f'{self.resource.pk}/delete/')]:
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_html_escapes_user_content(self):
        self.resource.name = '<img src=x onerror=alert(1)>'
        self.resource.save()
        response = self.client.get(self.url())
        self.assertContains(response, '&lt;img src=x onerror=alert(1)&gt;')
        self.assertNotContains(response, '<img src=x onerror=alert(1)>')
