import json
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Resource


class ResourceApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='api-owner', email='api-owner@example.test')
        cls.member = users.objects.create_user(username='api-member', email='api-member@example.test', first_name='Jan')
        cls.other = users.objects.create_user(username='api-other', email='api-other@example.test')
        cls.team = create_workplace_for_user(cls.owner, 'API')
        cls.second = create_workplace_for_user(cls.owner, 'Drugi')
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.team, user=cls.member)
        cls.resource = Resource.objects.create(owner=cls.owner, workplace=cls.team, name='Laptop', inventory_number='EQ-1', created_by=cls.owner, assigned_to=cls.member)
        cls.hidden = Resource.objects.create(owner=cls.owner, workplace=cls.second, name='Ukryty laptop')
        cls.corrupt = Resource.objects.create(owner=cls.other, workplace=cls.team, name='Inny właściciel')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.team.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.team, 'resources', f'api/v1/{suffix}')

    def payload(self, **changes):
        return {'name': 'Monitor', 'kind': 'equipment', 'status': 'available', **changes}

    def write(self, url=None, payload=None, method='post', client=None, **kwargs):
        return getattr(client or self.client, method)(url or self.url(), json.dumps(payload or self.payload()), content_type='application/json', **kwargs)

    def test_directory_scopes_both_routes_and_returns_json_only(self):
        for url in [reverse('resources:api-list'), self.url()]:
            response = self.client.get(url, follow=True)
            data = response.json()
            self.assertEqual([item['id'] for item in data['results']], [self.resource.pk])
            self.assertEqual(data['api_url'], self.url())
            self.assertNotIn('html', data)
            self.assertEqual(response['Cache-Control'], 'no-store')

    def test_create_uses_workspace_principal_and_actual_actor(self):
        for url in [reverse('resources:api-list'), self.url()]:
            response = self.write(url, self.payload(owner=self.other.pk, workplace=self.foreign.pk, created_by=self.other.pk, assigned_to=self.member.pk))
            self.assertEqual(response.status_code, 201)
            item = Resource.objects.get(pk=response.json()['resource']['id'])
            self.assertEqual((item.owner_id, item.workplace_id, item.created_by_id, item.updated_by_id, item.assigned_to_id), (self.owner.pk, self.team.pk, self.member.pk, self.member.pk, self.member.pk))

    def test_update_all_fields_and_clear_assignment(self):
        response = self.write(self.url(f'{self.resource.pk}/'), self.payload(name='Licencja', kind='license', status='retired', assigned_to=None, purchased_on='2026-10-01', expires_on='2027-10-01', notes='Notatka', location='Biuro', serial_number='SER-1'), method='put')
        self.assertEqual(response.status_code, 200)
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.created_by_id, self.owner.pk)
        self.assertEqual(self.resource.updated_by_id, self.member.pk)
        self.assertIsNone(self.resource.assigned_to)
        self.assertEqual(self.resource.expires_on, date(2027, 10, 1))
        self.assertEqual((self.resource.notes, self.resource.serial_number, self.resource.kind), ('Notatka', 'SER-1', 'license'))

    def test_unscoped_update_and_delete_remain_supported(self):
        self.assertEqual(self.write(reverse('resources:api-detail', args=[self.resource.pk]), method='put').status_code, 200)
        self.assertTrue(self.write(reverse('resources:api-delete', args=[self.resource.pk])).json()['deleted'])

    def test_form_schema_scopes_people_and_includes_shared_avatar(self):
        fields = {field['name']: field for field in self.client.get(self.url('new/')).json()['fields']}
        self.assertEqual({choice['value'] for choice in fields['assigned_to']['choices']}, {'', str(self.owner.pk), str(self.member.pk)})
        self.assertIn('avatar', fields['assigned_to']['choices'][1])
        self.assertEqual(fields['kind']['value'], 'equipment')
        self.assertEqual(fields['notes']['type'], 'textarea')

    def test_detail_form_preserves_values(self):
        data = self.client.get(self.url(f'{self.resource.pk}/')).json()
        self.assertEqual(data['id'], self.resource.pk)
        self.assertEqual(next(field['value'] for field in data['fields'] if field['name'] == 'assigned_to'), str(self.member.pk))

    def test_rejects_foreign_and_inactive_assignments(self):
        for user in [self.other, self.member]:
            if user == self.member:
                self.member.is_active = False
                self.member.save()
                self.client.force_login(self.owner)
            response = self.write(payload=self.payload(assigned_to=user.pk))
            self.assertEqual(response.status_code, 400)
            self.assertIn('assigned_to', response.json()['errors'])
        self.assertEqual(Resource.objects.count(), 3)

    def test_validation_does_not_mutate_existing_resource(self):
        cases = [({'name': ''}, 'name'), ({'kind': 'bad'}, 'kind'), ({'status': 'bad'}, 'status'), ({'purchased_on': '2026-10-02', 'expires_on': '2026-10-01'}, 'expires_on'), ({'notes': 'x' * 10001}, 'notes')]
        for values, field in cases:
            response = self.write(self.url(f'{self.resource.pk}/'), self.payload(**values), method='put')
            self.assertEqual(response.status_code, 400)
            self.assertIn(field, response.json()['errors'])
            self.resource.refresh_from_db()
            self.assertEqual(self.resource.name, 'Laptop')

    def test_duplicate_inventory_uses_existing_validation_and_keeps_input(self):
        response = self.write(payload=self.payload(inventory_number=' eq-1 '))
        self.assertEqual(response.status_code, 400)
        self.assertIn('inventory_number', response.json()['errors'])
        self.assertEqual(next(field['value'] for field in response.json()['editor']['fields'] if field['name'] == 'inventory_number'), ' eq-1 ')

    def test_json_contract_rejects_wrong_shapes_and_content_types(self):
        for body, content_type in [('{', 'application/json'), ('[]', 'application/json'), ('null', 'application/json'), ('{"name":{}}', 'application/json'), ('name=Monitor', 'application/x-www-form-urlencoded')]:
            self.assertEqual(self.client.post(self.url(), body, content_type=content_type).status_code, 400)
        self.assertEqual(Resource.objects.count(), 3)

    def test_filters_sort_and_pagination_share_html_behavior(self):
        Resource.objects.bulk_create([Resource(owner=self.owner, workplace=self.team, name=f'Licencja {index:02}', kind='license', assigned_to=self.member, status='in_use') for index in range(31)])
        params = {'q': 'Licencja', 'kind': 'license', 'status': 'in_use', 'assignee': 'me', 'sort': '-name', 'page_size': '25', 'next': 'https://example.test'}
        data = self.client.get(self.url(), params).json()
        self.assertEqual(len(data['results']), 25)
        self.assertEqual(data['results'][0]['name'], 'Licencja 30')
        self.assertEqual(data['pagination']['summary'], '1–25 z 31')
        self.assertNotIn('next=', data['list_url'])
        self.assertIn('kind=license', data['pagination']['next_url'])
        params['page'] = '2'
        self.assertEqual(len(self.client.get(self.url(), params).json()['results']), 6)

    def test_cross_workspace_and_wrong_owner_cannot_be_read_updated_or_deleted(self):
        for resource in [self.hidden, self.corrupt]:
            self.assertEqual(self.client.get(self.url(f'{resource.pk}/')).status_code, 404)
            self.assertEqual(self.write(self.url(f'{resource.pk}/'), method='put').status_code, 404)
            self.assertEqual(self.write(self.url(f'{resource.pk}/delete/')).status_code, 404)
            self.assertTrue(Resource.objects.filter(pk=resource.pk).exists())

    def test_foreign_workspace_and_revoked_membership_return_json_without_redirect(self):
        foreign_url = scoped_workplace_app_path(self.foreign, 'resources', 'api/v1/')
        self.assertEqual(self.client.get(foreign_url).status_code, 403)
        self.membership.is_active = False
        self.membership.save()
        for suffix in ['', 'new/', f'{self.resource.pk}/', f'{self.resource.pk}/delete/']:
            response = self.client.get(self.url(suffix))
            self.assertEqual(response.status_code, 403)
            self.assertIn('message', response.json())
        self.assertTrue(Resource.objects.filter(pk=self.resource.pk).exists())

    def test_anonymous_unauthorized_and_wrong_method_are_json(self):
        self.assertEqual(self.client.delete(self.url()).status_code, 405)
        self.assertEqual(self.client.get(self.url(f'{self.resource.pk}/delete/')).status_code, 405)
        self.client.logout()
        for suffix in ['', 'new/', f'{self.resource.pk}/']:
            response = self.client.get(self.url(suffix))
            self.assertEqual(response.status_code, 401)
            self.assertIn('message', response.json())

    def test_csrf_is_required_for_create_update_and_delete_and_valid_token_works(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        for suffix, method in [('', 'post'), (f'{self.resource.pk}/', 'put'), (f'{self.resource.pk}/delete/', 'post')]:
            response = self.write(self.url(suffix), method=method, client=client)
            self.assertEqual(response.status_code, 403)
            self.assertIn('message', response.json())
        client.get(scoped_workplace_app_path(self.team, 'resources'))
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        created = self.write(client=client, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(created.status_code, 201)
        pk = created.json()['resource']['id']
        self.assertEqual(self.write(self.url(f'{pk}/'), method='put', client=client, HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(self.write(self.url(f'{pk}/delete/'), client=client, HTTP_X_CSRFTOKEN=token).status_code, 200)

    def test_react_shell_and_direct_editor_keep_scoped_context_and_escape_data(self):
        self.resource.name = '</script><img src=x onerror=alert(1)>'
        self.resource.save()
        response = self.client.get(scoped_workplace_app_path(self.team, 'resources', f'{self.resource.pk}/edit/'), {'kind': 'equipment'})
        self.assertContains(response, 'data-react-root="resources"')
        self.assertContains(response, 'type="module"')
        self.assertNotContains(response, self.resource.name)
        self.assertEqual(response.context['react_bootstrap']['editor']['id'], self.resource.pk)
        self.assertIn('?kind=equipment', response.context['react_bootstrap']['list_url'])
