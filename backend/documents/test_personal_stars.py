"""Document stars belong to the viewer, including read-only Workspace guests."""
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Document, DocumentLibrary, Folder, WorkspaceDocument


class PersonalDocumentStarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='star-owner', email='star-owner@example.test')
        cls.member = users.objects.create_user(username='star-member', email='star-member@example.test')
        cls.guest = users.objects.create_user(username='star-guest', email='star-guest@example.test')
        cls.outsider = users.objects.create_user(username='star-outsider', email='star-outsider@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Osobiste gwiazdki')
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Inne dokumenty')
        cls.member_access = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.guest_access = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.guest, role='guest')
        cls.library = DocumentLibrary.objects.create(owner=cls.owner, workplace=cls.workspace, name='Dysk zespołu')
        cls.folder = Folder.objects.create(owner=cls.owner, workplace=cls.workspace, library=cls.library, name='Folder zespołu')
        cls.drive_file = Document.objects.create(owner=cls.owner, workplace=cls.workspace, library=cls.library,
                                               title='Plik zespołu', filename='plik.txt')
        cls.office_file = WorkspaceDocument.objects.create(owner=cls.owner, workplace=cls.workspace,
                                                           title='Tekst zespołu', content='<p>Treść</p>')

    def client_for(self, user):
        client = Client()
        client.force_login(user)
        session = client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()
        return client

    def cases(self):
        return [('documents', self.drive_file, f'{self.drive_file.pk}/star/'),
                ('documents', self.folder, f'folders/{self.folder.pk}/star/'),
                ('office', self.office_file, f'{self.office_file.pk}/star/')]

    def directory(self, client, module, *, api=False, **params):
        base = scoped_workplace_app_path(self.workspace, module)
        if module == 'documents' and 'library' not in params and params.get('view', 'all') == 'all':
            params['library'] = self.library.pk
        if api:
            response = client.get(scoped_workplace_app_path(self.workspace, 'api', 'v1/page/'),
                                  {'url': base + '?' + urlencode(params)})
            self.assertEqual(response.status_code, 200)
            return response.json()['data']
        response = client.get(base, params)
        self.assertEqual(response.status_code, 200)
        return response.context['frontend_bootstrap']['data']

    def test_guest_owner_and_member_toggle_only_their_own_stars_on_both_routes(self):
        for module, item, suffix in self.cases():
            item.favorited_by.add(self.owner, self.member)
            for base in [scoped_workplace_app_path(self.workspace, module), f'/{module}/']:
                with self.subTest(model=type(item).__name__, route=base):
                    guest = self.client_for(self.guest)
                    self.assertEqual(guest.post(base + suffix).status_code, 302)
                    self.assertEqual(set(item.favorited_by.values_list('pk', flat=True)),
                                     {self.owner.pk, self.member.pk, self.guest.pk})
                    self.assertEqual(self.client_for(self.owner).post(base + suffix).status_code, 302)
                    self.assertEqual(set(item.favorited_by.values_list('pk', flat=True)), {self.member.pk, self.guest.pk})
                    self.assertEqual(guest.post(base + suffix).status_code, 302)
                    self.assertEqual(list(item.favorited_by.values_list('pk', flat=True)), [self.member.pk])
                    item.favorited_by.add(self.owner)

    def test_guest_does_not_change_owner_catalog_counters_or_filter_results(self):
        guest, owner = self.client_for(self.guest), self.client_for(self.owner)
        for module, item, suffix in self.cases():
            self.assertEqual(guest.post(scoped_workplace_app_path(self.workspace, module, suffix)).status_code, 302)
        for api in (False, True):
            for module, expected in [('documents', {str(self.drive_file.pk), str(self.folder.pk)}),
                                     ('office', {str(self.office_file.pk)})]:
                with self.subTest(module=module, api=api):
                    guest_data = self.directory(guest, module, api=api, view='starred')
                    owner_data = self.directory(owner, module, api=api, view='starred')
                    self.assertEqual({row['id'] for row in guest_data['rows']}, expected)
                    self.assertTrue(all(row['starred'] for row in guest_data['rows']))
                    self.assertEqual(owner_data['rows'], [])
                    guest_count = next(view['count'] for view in guest_data['views'] if view['value'] == 'starred')
                    owner_count = next(view['count'] for view in owner_data['views'] if view['value'] == 'starred')
                    self.assertEqual((guest_count, owner_count), (len(expected), 0))
                    guest_filtered = self.directory(guest, module, api=api, view='all', starred='yes')
                    owner_filtered = self.directory(owner, module, api=api, view='all', starred='no')
                    self.assertEqual({row['id'] for row in guest_filtered['rows']}, expected)
                    self.assertEqual({row['id'] for row in owner_filtered['rows']}, expected)
                    self.assertFalse(any(row['starred'] for row in owner_filtered['rows']))

    def test_delegated_star_operation_uses_actor_without_changing_shared_content(self):
        guest = self.client_for(self.guest)
        endpoint = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        for module, item, suffix in self.cases():
            before = {field.attname: getattr(item, field.attname) for field in item._meta.concrete_fields}
            target = scoped_workplace_app_path(self.workspace, module, suffix)
            response = guest.post(endpoint + '?' + urlencode({'url': target}))
            self.assertEqual(response.status_code, 200)
            item.refresh_from_db()
            self.assertEqual({field.attname: getattr(item, field.attname) for field in item._meta.concrete_fields}, before)
            self.assertEqual(list(item.favorited_by.values_list('pk', flat=True)), [self.guest.pk])

    def test_multiple_peoples_stars_do_not_duplicate_rows_or_counts(self):
        for _module, item, _suffix in self.cases():
            item.favorited_by.add(self.owner, self.member, self.guest)
        for module, count in [('documents', 2), ('office', 1)]:
            data = self.directory(self.client_for(self.member), module, view='starred')
            self.assertEqual(len(data['rows']), count)
            self.assertEqual(next(view['count'] for view in data['views'] if view['value'] == 'starred'), count)

    def test_stars_do_not_grant_access_to_foreign_owner_or_workspace(self):
        guest = self.client_for(self.guest)
        for owner, workplace in [(self.outsider, self.workspace), (self.owner, self.other_workspace)]:
            library = DocumentLibrary.objects.create(owner=owner, workplace=workplace, name=f'Obcy dysk {owner.pk}')
            folder = Folder.objects.create(owner=owner, workplace=workplace, library=library, name='Obcy folder')
            drive_file = Document.objects.create(owner=owner, workplace=workplace, library=library, title='Obcy plik', filename='obcy.txt')
            office_file = WorkspaceDocument.objects.create(owner=owner, workplace=workplace, title='Obcy tekst')
            for module, item, suffix in [('documents', folder, f'folders/{folder.pk}/star/'),
                                         ('documents', drive_file, f'{drive_file.pk}/star/'),
                                         ('office', office_file, f'{office_file.pk}/star/')]:
                item.favorited_by.add(self.guest)
                self.assertEqual(guest.post(scoped_workplace_app_path(self.workspace, module, suffix)).status_code, 404)
                self.assertEqual(self.directory(guest, module, view='starred')['rows'], [])
                self.assertTrue(item.favorited_by.filter(pk=self.guest.pk).exists())

    def test_trashed_files_keep_personal_stars_without_being_toggleable(self):
        guest = self.client_for(self.guest)
        for module, item in [('documents', self.drive_file), ('office', self.office_file)]:
            item.favorited_by.add(self.guest)
            item.deleted_at = timezone.now()
            item.save(update_fields=['deleted_at'])
            self.assertEqual(self.directory(guest, module, view='starred')['rows'], [])
            self.assertEqual(guest.post(scoped_workplace_app_path(self.workspace, module, f'{item.pk}/star/')).status_code, 404)
            self.assertEqual(len(self.directory(guest, module, view='trash', starred='yes')['rows']), 1)
            self.assertEqual(self.directory(self.client_for(self.owner), module, view='trash', starred='yes')['rows'], [])
            self.assertTrue(item.favorited_by.filter(pk=self.guest.pk).exists())

    def test_personal_star_exception_does_not_allow_guest_content_edits(self):
        guest = self.client_for(self.guest)
        targets = [('documents', f'{self.drive_file.pk}/'),
                   ('documents', f'folders/{self.folder.pk}/edit/'), ('office', f'{self.office_file.pk}/')]
        for module, suffix in targets:
            self.assertEqual(guest.post(scoped_workplace_app_path(self.workspace, module, suffix),
                                        {'title': 'Zmiana', 'name': 'Zmiana', 'revision': 1}).status_code, 403)

    def test_revoked_membership_cannot_toggle_existing_personal_stars(self):
        guest = self.client_for(self.guest)
        for _module, item, _suffix in self.cases():
            item.favorited_by.add(self.guest)
        self.guest_access.delete()
        for module, item, suffix in self.cases():
            response = guest.post(scoped_workplace_app_path(self.workspace, module, suffix))
            self.assertEqual(response.status_code, 302)
            self.assertTrue(item.favorited_by.filter(pk=self.guest.pk).exists())
