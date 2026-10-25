import base64
import tempfile
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from documents.models import WorkspaceDocument
from workplaces.models import Workplace, WorkplaceInvitation, WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


class ReactWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='react-ws-owner', email='owner@example.test')
        cls.admin = users.objects.create_user(username='react-ws-admin', email='admin@example.test')
        cls.member = users.objects.create_user(username='react-ws-member', email='member@example.test')
        cls.outside = users.objects.create_user(username='react-ws-outside', email='outside@example.test', first_name='<Osoba>')
        cls.active = create_workplace_for_user(cls.owner, 'Aktywny')
        cls.selected = create_workplace_for_user(cls.owner, 'Wybrany')
        cls.foreign = create_workplace_for_user(cls.outside, 'Niedostępny')
        cls.administrator = WorkplaceMembership.objects.create(workplace=cls.selected, user=cls.admin, role='admin')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.selected, user=cls.member)
        cls.base = reverse('workplaces:workplaces')

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        storage = FileSystemStorage(directory.name)
        field = Workplace._meta.get_field('workplace_photo')
        self.addCleanup(setattr, field, 'storage', field.storage)
        field.storage = storage
        self.login(self.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.active.pk if user == self.owner else self.selected.pk
        session.save()

    def target(self, name, *args):
        return reverse('workplaces:'+name, args=args)

    def endpoint(self, target, scoped=False):
        base = scoped_workplace_app_path(self.active, 'api', 'v1/page/') if scoped else '/api/v1/page/'
        return base+'?'+urlencode({'url': target})

    def get(self, target=None, **headers):
        return self.client.get(self.endpoint(target or self.base), follow=True, **headers)

    def post(self, target, values):
        return self.client.post(self.endpoint(target), values)

    def test_bootstrap_catalog_has_typed_rows_and_explicit_management_context(self):
        for endpoint in (self.endpoint(self.base), self.endpoint(self.base, scoped=True)):
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['type'], 'workspace-directory')
            self.assertEqual(response['Cache-Control'], 'no-store')
            rows = response.json()['data']['rows']
            self.assertEqual(rows[0]['id'], str(self.active.pk))
            self.assertEqual(rows[0]['role'], 'Właściciel')
            self.assertNotIn(self.foreign.name, str(rows))
        self.assertContains(self.client.get(self.base), 'data-react-root="page"')
        data = self.get(self.base+f'?workspace={self.selected.pk}&tab=main').json()['data']
        self.assertEqual(data['team']['name'], 'Wybrany')
        self.assertTrue(data['edit_open'])
        self.assertEqual(data['tab'], 'main')
        self.assertEqual(self.client.session['active_workplace_id'], self.active.pk)

    def test_creation_enters_new_context_and_keeps_immutable_code(self):
        result = self.post(self.base, {'name': ' Powtarzalny  Workspace ', 'avatar': 'ship', 'code': 'evil', 'owner': self.outside.pk})
        self.assertEqual(result.status_code, 200)
        item = Workplace.objects.get(name='Powtarzalny Workspace')
        self.assertEqual(item.owner, self.owner)
        self.assertEqual(item.avatar, 'ship')
        self.assertNotEqual(item.code, 'evil')
        self.assertTrue(item.memberships.filter(user=self.owner, is_active=True).exists())
        self.assertEqual(result.json()['redirect'], scoped_workplace_app_path(item, 'for-you'))
        self.assertEqual(self.client.session['active_workplace_id'], item.pk)
        self.assertEqual(self.post(self.base, {'name': item.name}).status_code, 200)
        self.assertEqual(Workplace.objects.filter(name=item.name).count(), 2)

    def test_invalid_create_settings_and_upload_return_bound_schema(self):
        result = self.post(self.base, {'name': ' ', 'description': 'Szkic', 'avatar': 'rocket'})
        self.assertEqual(result.status_code, 400)
        data = result.json()['data']
        self.assertTrue(data['create_open'])
        self.assertTrue(next(f for f in data['create_form']['fields'] if f['name']=='name')['errors'])
        result = self.post(self.target('update', self.selected.pk), {'name': '', 'description': 'Opis'})
        self.assertEqual(result.status_code, 400)
        self.assertTrue(result.json()['data']['edit_open'])
        self.assertEqual(result.json()['data']['tab'], 'main')
        self.assertEqual(self.post(self.base, {'name': 'Błędny obraz', 'avatar': 'upload', 'workplace_photo': SimpleUploadedFile('zly.png', b'not image')}).status_code, 400)
        self.assertFalse(Workplace.objects.filter(name='Błędny obraz').exists())

    def test_photo_and_presets_keep_existing_validation_and_storage(self):
        target = self.target('update', self.selected.pk)
        result = self.post(target, {'name': 'Nowa nazwa', 'avatar': 'upload', 'workplace_photo_crop': 'data:image/png;base64,'+base64.b64encode(PNG).decode()})
        self.assertEqual(result.status_code, 200)
        self.selected.refresh_from_db()
        code, photo = self.selected.code, self.selected.workplace_photo.name
        self.assertTrue(self.selected.workplace_photo.storage.exists(photo))
        self.assertEqual(self.post(target, {'name': 'Jeszcze inna', 'code': 'zmieniony'}).status_code, 200)
        self.selected.refresh_from_db()
        self.assertEqual((self.selected.code, self.selected.workplace_photo.name), (code, photo))
        with self.captureOnCommitCallbacks(execute=True):
            self.post(target, {'name': 'Jeszcze inna', 'avatar': 'leaf'})
        self.selected.refresh_from_db()
        self.assertFalse(self.selected.workplace_photo.storage.exists(photo))
        self.assertEqual(self.selected.avatar, 'leaf')

    def test_member_cannot_read_sent_invitations_or_write_settings(self):
        WorkplaceInvitation.objects.create(workplace=self.selected, recipient=self.outside, invited_by=self.owner)
        self.login(self.member)
        data = self.get(self.base+f'?workspace={self.selected.pk}&view=invitations').json()['data']
        self.assertFalse(data['team']['can_manage'])
        self.assertIsNone(data['team']['form'])
        self.assertIsNone(data['team']['invite_form'])
        self.assertEqual(data['team']['invitations'], [])
        self.assertNotIn(self.outside.email, str(data))
        self.assertTrue(all(not p['change_url'] for p in data['team']['members']))
        self.assertEqual(self.post(self.target('update', self.selected.pk), {'name': 'Nie'}).status_code, 403)
        self.assertEqual(self.get(self.target('invitation-candidates', self.selected.pk)+'?q=Osoba').status_code, 403)

    def test_candidates_are_data_without_html_and_are_revalidated_on_invite(self):
        target = self.target('invitation-candidates', self.selected.pk)
        results = self.get(target+'?q=Osoba').json()['results']
        self.assertEqual(results[0]['name'], '<Osoba>')
        self.assertIn('avatar', results[0])
        self.assertNotIn('html', results[0])
        invitation = self.post(self.target('team', self.selected.pk), {'email': self.outside.email, 'role': 'admin'})
        self.assertEqual(invitation.status_code, 200)
        created = WorkplaceInvitation.objects.get(recipient=self.outside)
        self.assertEqual((created.invited_by, created.role), (self.owner, 'admin'))
        self.assertEqual(self.get(target+'?q=Osoba').json()['results'], [])
        duplicate = self.post(self.target('team', self.selected.pk), {'email': self.outside.email, 'role': 'member'})
        self.assertEqual(duplicate.status_code, 400)
        self.assertTrue(duplicate.json()['data']['invite_open'])
        self.assertEqual(self.client.session['active_workplace_id'], self.active.pk)

    def test_admin_cannot_promote_or_remove_admin_or_cancel_admin_invitation(self):
        invitation = WorkplaceInvitation.objects.create(workplace=self.selected, recipient=self.outside, invited_by=self.owner, role='admin')
        self.login(self.admin)
        data = self.get(self.base+f'?workspace={self.selected.pk}').json()['data']['team']
        self.assertEqual([c['value'] for f in data['invite_form']['fields'] if f['name']=='role' for c in f['choices']], ['member', 'guest'])
        self.assertFalse(next(p for p in data['members'] if p['id']==str(self.administrator.pk))['change_url'])
        self.assertFalse(next(p for p in data['invitations'] if p['id']==str(invitation.pk))['cancel_url'])
        self.assertEqual(self.post(self.target('member-update', self.selected.pk, self.membership.pk), {'action':'role','role':'admin'}).status_code, 403)
        self.assertEqual(self.post(self.target('invitation-cancel', self.selected.pk, invitation.pk), {}).status_code, 403)
        self.assertEqual(self.post(self.target('team', self.selected.pk), {'email':self.outside.email,'role':'admin'}).status_code, 400)

    def test_owner_role_removal_and_cancel_keep_domain_effects(self):
        target = self.target('member-update', self.selected.pk, self.membership.pk)
        self.assertEqual(self.post(target, {'action':'role','role':'admin'}).status_code, 200)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, 'admin')
        item = WorkspaceDocument.objects.create(owner=self.owner, workplace=self.selected, title='Tekst')
        key = item.office_key
        self.assertEqual(self.post(target, {'action':'remove'}).status_code, 200)
        self.assertFalse(WorkplaceMembership.objects.filter(pk=self.membership.pk).exists())
        item.refresh_from_db()
        self.assertNotEqual(key, item.office_key)
        invitation = WorkplaceInvitation.objects.create(workplace=self.selected, recipient=self.outside, invited_by=self.owner)
        self.assertEqual(self.post(self.target('invitation-cancel', self.selected.pk, invitation.pk), {}).status_code, 200)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status,'revoked')
        self.assertEqual(self.client.session['active_workplace_id'], self.active.pk)

    def test_incoming_invitation_is_recipient_only_and_accept_switches(self):
        incoming = WorkplaceInvitation.objects.create(workplace=self.foreign, recipient=self.owner, invited_by=self.outside)
        another = create_workplace_for_user(self.outside, 'Drugie zaproszenie')
        WorkplaceInvitation.objects.create(workplace=another, recipient=self.owner, invited_by=self.outside)
        data = self.get(self.base+f'?invitation={incoming.pk}&workspace={self.selected.pk}').json()['data']['incoming']
        self.assertEqual(data['name'], self.foreign.name)
        self.assertEqual(data['role'], 'Członek')
        navigation = data['previous'] or data['next']
        self.assertIn(f'workspace={self.selected.pk}', navigation)
        self.assertIn('view=workspaces', navigation)
        self.assertEqual(self.client.session['active_workplace_id'], self.active.pk)
        self.assertEqual(self.post(data['action'], {'action':'accept'}).status_code, 200)
        self.assertEqual(self.client.session['active_workplace_id'], self.foreign.pk)
        self.assertTrue(WorkplaceMembership.objects.filter(workplace=self.foreign, user=self.owner, is_active=True).exists())
        self.assertEqual(self.post(data['action'], {'action':'accept'}).status_code, 404)
        self.login(self.member)
        self.assertEqual(self.post(data['action'], {'action':'decline'}).status_code, 404)

    def test_expired_declined_and_missing_invitations_do_not_grant_access(self):
        incoming = WorkplaceInvitation.objects.create(workplace=self.foreign, recipient=self.owner, invited_by=self.outside)
        response = self.post(self.target('invitation-response', incoming.pk), {'action':'decline'})
        self.assertEqual(response.status_code, 200)
        incoming.refresh_from_db()
        self.assertEqual(incoming.status,'declined')
        expired = WorkplaceInvitation.objects.create(workplace=self.foreign, recipient=self.owner, invited_by=self.outside, expires_at=timezone.now()-timedelta(days=1))
        self.assertEqual(self.post(self.target('invitation-response', expired.pk), {'action':'accept'}).status_code, 404)
        self.assertIn('redirect', self.get(self.base+'?invitation=999999').json())
        self.assertFalse(WorkplaceMembership.objects.filter(workplace=self.foreign, user=self.owner).exists())

    def test_explicit_switch_delete_last_owner_guard_and_foreign_targets(self):
        self.assertEqual(self.post(self.target('switch', self.selected.pk), {}).status_code, 200)
        self.assertEqual(self.client.session['active_workplace_id'], self.selected.pk)
        self.assertEqual(self.get(self.base+f'?workspace={self.foreign.pk}').status_code, 404)
        self.assertEqual(self.post(self.target('update', self.foreign.pk), {'name':'Nie'}).status_code, 404)
        self.assertEqual(self.post(self.target('member-update', self.active.pk, self.membership.pk), {'action':'remove'}).status_code, 404)
        self.assertEqual(self.post(self.target('delete', self.active.pk), {}).status_code, 200)
        self.assertEqual(self.post(self.target('delete', self.selected.pk), {}).status_code, 200)
        self.assertTrue(Workplace.objects.filter(pk=self.selected.pk).exists())

    def test_session_csrf_methods_and_revoked_membership(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        self.assertEqual(csrf.post(self.endpoint(self.base), {'name':'Nie'}).status_code, 403)
        self.assertEqual(self.get(self.target('update', self.selected.pk)).status_code, 405)
        self.login(self.member)
        self.membership.delete()
        self.assertEqual(self.get(self.base+f'?workspace={self.selected.pk}').status_code, 404)
        self.client.logout()
        self.assertEqual(self.get().status_code, 401)
