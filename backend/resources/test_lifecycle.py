import csv
import io
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Resource, ResourceActivity


class ResourceLifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='resource-owner', email='resource-owner@example.test', first_name='Jan')
        cls.member = users.objects.create_user(username='resource-member', email='resource-member@example.test', first_name='Jan')
        cls.outsider = users.objects.create_user(username='resource-outsider', email='resource-outsider@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Ewidencja')
        cls.second = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.resource = Resource.objects.create(owner=cls.owner, workplace=cls.workspace, name='Laptop', inventory_number='IT-001')
        cls.other = Resource.objects.create(owner=cls.owner, workplace=cls.workspace, name='Monitor')
        cls.hidden = Resource.objects.create(owner=cls.owner, workplace=cls.second, name='Poufny zasób')
        cls.corrupt = Resource.objects.create(owner=cls.outsider, workplace=cls.workspace, name='Inny właściciel')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'resources', 'api/v1/' + suffix)

    def write(self, suffix, data, method='post', client=None):
        return getattr(client or self.client, method)(self.url(suffix), json.dumps(data), content_type='application/json')

    def operation(self, operation_action, resources=None, **data):
        resources = resources or [self.resource]
        for resource in resources:
            resource.refresh_from_db()
        return self.write('operate/', {
            'ids': ','.join(str(resource.pk) for resource in resources), 'action': operation_action,
            'revisions': json.dumps({str(resource.pk): resource.updated_at.isoformat() for resource in resources}), **data,
        })

    def test_create_update_and_html_share_history_and_actor(self):
        response = self.write('', {'name': 'Drukarka', 'kind': 'equipment', 'status': 'available'})
        item = Resource.objects.get(pk=response.json()['resource']['id'])
        created = item.activities.get()
        self.assertEqual((created.action, created.actor_id, created.actor_name), ('created', self.member.pk, 'Jan'))
        url = scoped_workplace_app_path(self.workspace, 'resources', f'{item.pk}/edit/')
        response = self.client.post(url, {'name': 'Nowa drukarka', 'kind': 'equipment', 'status': 'maintenance'})
        self.assertEqual(response.status_code, 302)
        entry = item.activities.first()
        self.assertEqual(entry.action, 'updated')
        self.assertEqual({change['field'] for change in entry.changes}, {'name', 'status'})
        self.assertEqual(entry.changes[0]['before'], 'Drukarka')
        self.assertEqual(entry.actor_id, self.member.pk)

    def test_handover_return_and_same_display_name_assignment_are_audited(self):
        due = (timezone.localdate() + timedelta(days=7)).isoformat()
        self.assertEqual(self.operation('handover', assigned_to=self.owner.pk, return_due_on=due, note='Komplet z zasilaczem').status_code, 200)
        self.resource.refresh_from_db()
        self.assertEqual((self.resource.status, self.resource.assigned_to_id, str(self.resource.return_due_on)), ('in_use', self.owner.pk, due))
        self.assertEqual(self.resource.activities.get().note, 'Komplet z zasilaczem')
        self.assertEqual(self.operation('handover', assigned_to=self.member.pk, return_due_on=due).status_code, 200)
        self.assertEqual(self.resource.activities.count(), 2)
        self.assertEqual(self.resource.activities.first().changes[0]['field'], 'assigned_to')
        self.assertEqual(self.operation('return', note='Sprawny').status_code, 200)
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.status, 'available')
        self.assertIsNone(self.resource.assigned_to_id)
        self.assertIsNone(self.resource.return_due_on)
        self.assertEqual(self.resource.activities.first().action, 'return')

    def test_history_supports_the_full_account_name_limits(self):
        self.member.first_name = 'A' * 150
        self.member.middle_name = 'B' * 150
        self.member.last_name = 'C' * 150
        self.member.save()
        response = self.operation('note', note='Przegląd')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.resource.activities.get().actor_name, self.member.get_full_name())

    def test_invalid_handover_preserves_data_and_history(self):
        cases = [{'assigned_to': ''}, {'assigned_to': self.outsider.pk}, {'assigned_to': self.member.pk, 'return_due_on': 'bad'},
                 {'assigned_to': self.member.pk, 'return_due_on': (timezone.localdate() - timedelta(days=1)).isoformat()}]
        for data in cases:
            self.assertEqual(self.operation('handover', **data).status_code, 400)
        self.member.is_active = False
        self.member.save()
        self.client.force_login(self.owner)
        self.assertEqual(self.operation('handover', assigned_to=self.member.pk).status_code, 400)
        self.assertFalse(self.resource.activities.exists())
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.status, 'available')

    def test_bulk_is_atomic_for_invalid_state_or_scope(self):
        self.other.status = 'maintenance'
        self.other.save()
        self.assertEqual(self.operation('handover', [self.resource, self.other], assigned_to=self.member.pk).status_code, 400)
        for hidden in [self.hidden, self.corrupt]:
            self.assertEqual(self.operation('location', [self.resource, hidden], location='Magazyn').status_code, 404)
        self.assertEqual(self.operation('return', [self.resource, self.other]).status_code, 400)
        self.resource.refresh_from_db()
        self.assertEqual((self.resource.status, self.resource.location), ('available', ''))
        self.assertFalse(ResourceActivity.objects.exists())

    def test_bulk_status_location_and_notes_preserve_other_fields(self):
        self.operation('handover', assigned_to=self.member.pk, return_due_on=timezone.localdate().isoformat())
        self.assertEqual(self.operation('status', [self.resource, self.other], status='maintenance', note='Przegląd').status_code, 200)
        self.resource.refresh_from_db()
        self.assertIsNone(self.resource.return_due_on)
        self.assertEqual(self.resource.assigned_to_id, self.member.pk)
        self.assertEqual(self.operation('location', [self.resource, self.other], location='Warszawa').status_code, 200)
        self.assertEqual(self.operation('note', note='Diagnoza w toku').status_code, 200)
        self.assertEqual(self.resource.activities.first().note, 'Diagnoza w toku')
        self.assertEqual(self.operation('note', note=' ').status_code, 400)
        self.assertEqual(self.operation('note', note='x' * 2001).status_code, 400)
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.inventory_number, 'IT-001')
        self.assertEqual(self.resource.notes, '')

    def test_revisions_block_stale_editor_and_whole_bulk_operation(self):
        revision = self.resource.updated_at.isoformat()
        self.operation('location', location='Nowa lokalizacja')
        response = self.write(f'{self.resource.pk}/', {'name': 'Stara wersja', 'kind': 'equipment', 'status': 'available', 'revision': revision}, method='put')
        self.assertEqual(response.status_code, 400)
        response = self.operation('status', [self.resource, self.other], status='retired', revisions=json.dumps({str(self.resource.pk): revision, str(self.other.pk): self.other.updated_at.isoformat()}))
        self.assertEqual(response.status_code, 409)
        self.resource.refresh_from_db(); self.other.refresh_from_db()
        self.assertEqual((self.resource.name, self.resource.location, self.other.status), ('Laptop', 'Nowa lokalizacja', 'available'))
        self.assertEqual(ResourceActivity.objects.count(), 1)

    def test_operation_validation_and_csrf(self):
        for changes in [{'ids': ''}, {'ids': []}, {'ids': '-1'}, {'ids': '1,'}, {'ids': '9' * 100}, {'ids': ','.join(['1'] * 101)},
                        {'revisions': '[]'}, {'revisions': '{}'}, {'revisions': 3}, {'action': 'delete'}, {'status': 'wrong'}]:
            response = self.operation('status', status='retired', **{key: value for key, value in changes.items() if key != 'status'}) if 'status' not in changes else self.operation('status', **changes)
            self.assertEqual(response.status_code, 400, changes)
        self.assertEqual(self.client.get(self.url('operate/')).status_code, 405)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.member)
        self.assertEqual(self.write('operate/', {}, client=csrf).status_code, 403)
        self.assertFalse(ResourceActivity.objects.exists())

    def test_guests_read_details_history_and_export_but_cannot_operate(self):
        self.operation('note', note='Historia współdzielona')
        self.membership.role = 'guest'; self.membership.save()
        for suffix in [f'{self.resource.pk}/overview/', 'export/']:
            self.assertEqual(self.client.get(self.url(suffix)).status_code, 200)
        page = scoped_workplace_app_path(self.workspace, 'resources', f'{self.resource.pk}/')
        self.assertContains(self.client.get(page), 'Historia współdzielona')
        for url in [self.url('operate/'), reverse('resources:api-operate')]:
            self.assertEqual(self.client.post(url, '{}', content_type='application/json').status_code, 403)
        self.assertTrue(self.client.get(self.url()).json()['read_only'])
        self.assertNotContains(self.client.get(page), '>Edytuj zasób</a>')

    def test_details_history_and_export_recheck_access(self):
        for resource in [self.hidden, self.corrupt]:
            self.assertEqual(self.client.get(self.url(f'{resource.pk}/overview/')).status_code, 404)
            self.assertEqual(self.client.get(scoped_workplace_app_path(self.workspace, 'resources', f'{resource.pk}/')).status_code, 404)
        self.membership.delete()
        self.assertEqual(self.client.get(self.url(f'{self.resource.pk}/overview/')).status_code, 403)
        self.assertEqual(self.client.get(self.url('export/')).status_code, 403)

    def test_disabled_module_blocks_new_routes(self):
        self.workspace.disabled_modules = ['resources']; self.workspace.save()
        for suffix in ['export/', f'{self.resource.pk}/overview/']:
            self.assertEqual(self.client.get(self.url(suffix)).status_code, 404)
        self.assertEqual(self.operation('note', note='Nie').status_code, 404)

    def test_history_pagination_and_actor_snapshot_after_account_deletion(self):
        ResourceActivity.objects.bulk_create([ResourceActivity(resource=self.resource, actor=self.member, actor_name='Jan', action='note', note=str(i)) for i in range(25)])
        first = self.client.get(self.url(f'{self.resource.pk}/overview/')).json()
        second = self.client.get(self.url(f'{self.resource.pk}/overview/'), {'history_page': 2}).json()
        self.assertEqual((len(first['history']), len(second['history']), first['history_total']), (20, 25, 25))
        self.assertEqual(second['history'][:20], first['history'])
        self.assertEqual(second['history_end'], 25)
        self.assertEqual(second['history_next'], '')
        self.assertIn('history_limit=25', first['history_next'])
        self.assertEqual(self.client.get(first['history_next']).json()['history'], second['history'])
        self.client.force_login(self.owner); self.member.delete()
        entry = self.resource.activities.first()
        self.assertIsNone(entry.actor_id)
        self.assertEqual(entry.actor_name, 'Jan')

    def test_deadline_boundaries_summary_and_null_last_sort(self):
        today = timezone.localdate()
        self.resource.expires_on = today; self.resource.save()
        self.other.expires_on = today - timedelta(days=1); self.other.status = 'retired'; self.other.save()
        extra = Resource.objects.create(owner=self.owner, workplace=self.workspace, name='Licencja', kind='license', expires_on=today + timedelta(days=30), status='in_use', return_due_on=today - timedelta(days=1))
        self.hidden.expires_on = today; self.hidden.save()
        listing = self.client.get(self.url()).json()
        self.assertEqual(listing['summary'], {'total': 3, 'available': 1, 'in_use': 1, 'maintenance': 0, 'attention': 2, 'return_overdue': 1})
        self.assertEqual(len(self.client.get(self.url(), {'deadline': 'soon'}).json()['results']), 2)
        self.assertEqual(self.client.get(self.url(), {'deadline': 'expired'}).json()['results'], [])
        filtered = self.client.get(self.url(), {'deadline': 'return_overdue', 'kind': 'license'}).json()
        self.assertEqual([entry['id'] for entry in filtered['results']], [extra.pk])
        self.resource.expires_on = None; self.resource.save()
        ordered = self.client.get(self.url(), {'sort': 'expires_on'}).json()['results']
        self.assertEqual(ordered[-1]['id'], self.resource.pk)

    def test_export_contains_all_filtered_rows_and_neutralizes_formulas(self):
        Resource.objects.bulk_create([Resource(owner=self.owner, workplace=self.workspace, name=f'Licencja {i}', kind='license') for i in range(30)])
        Resource.objects.create(owner=self.owner, workplace=self.workspace, name=' =HYPERLINK("test")', kind='license', notes='@SUM(1;2)')
        response = self.client.get(self.url('export/'), {'kind': 'license', 'page': 2, 'page_size': 25})
        content = b''.join(response.streaming_content).decode('utf-8-sig')
        rows = list(csv.reader(io.StringIO(content), delimiter=';'))
        self.assertEqual(len(rows), 32)
        self.assertNotIn('Poufny', content)
        self.assertNotIn('Inny właściciel', content)
        formula = next(row for row in rows if 'HYPERLINK' in row[0])
        self.assertTrue(formula[0].startswith("'"))
        self.assertTrue(formula[-1].startswith("'"))
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_return_date_constraint_and_edit_clearing(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Resource.objects.filter(pk=self.resource.pk).update(return_due_on=timezone.localdate())
        self.operation('handover', assigned_to=self.member.pk, return_due_on=timezone.localdate().isoformat())
        response = self.write(f'{self.resource.pk}/', {'name': 'Laptop', 'kind': 'equipment', 'status': 'retired', 'return_due_on': timezone.localdate().isoformat()}, method='put')
        self.assertEqual(response.status_code, 200)
        self.resource.refresh_from_db()
        self.assertIsNone(self.resource.return_due_on)

    def test_unscoped_detail_and_json_navigation(self):
        self.operation('note', note='<script>alert(1)</script>')
        response = self.client.get(reverse('resources:detail', args=[self.resource.pk]), follow=True)
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
        target = scoped_workplace_app_path(self.workspace, 'resources', f'{self.resource.pk}/')
        nav = scoped_workplace_app_path(self.workspace, 'api', 'v1/navigation/')
        response = self.client.get(nav, {'url': target})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['page']['data']['detail']['resource']['id'], self.resource.pk)
        self.assertEqual(self.client.get(reverse('resources:api-overview', args=[self.resource.pk]), follow=True).status_code, 200)
