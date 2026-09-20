import base64
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import DocumentLibrary, Folder


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j2ioAAAAASUVORK5CYII=')
CROP = 'data:image/png;base64,' + base64.b64encode(PNG).decode()


class LibraryPhotoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='photo-owner', email='photo-owner@example.test')
        cls.other = get_user_model().objects.create_user(username='photo-other', email='photo-other@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Zdjęcia bibliotek')
        cls.outside = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        cls.base = scoped_workplace_app_path(cls.workspace, 'documents')
        cls.outside_base = scoped_workplace_app_path(cls.outside, 'documents')
        cls.library = DocumentLibrary.objects.create(owner=cls.owner, workplace=cls.workspace, name='Biblioteka ze zdjęciem')
        cls.edit_url = f'{cls.base}libraries/{cls.library.pk}/edit/'
        cls.photo_url = f'{cls.base}libraries/{cls.library.pk}/photo/'

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.storage = FileSystemStorage(directory.name)
        field = DocumentLibrary._meta.get_field('photo')
        self.addCleanup(setattr, field, 'storage', field.storage)
        field.storage = self.storage
        self.client.force_login(self.owner)

    def save_legacy_photo(self):
        self.library.photo.save('legacy.png', SimpleUploadedFile('legacy.png', PNG))

    def test_create_ignores_photo_upload_and_crop_in_normal_and_scoped_routes(self):
        self.client.get(self.base)
        for root in (self.base, '/documents/'):
            for field in ('photo', 'photo_crop'):
                with self.subTest(root=root, field=field):
                    value = SimpleUploadedFile('logo.png', PNG, content_type='image/png') if field == 'photo' else CROP
                    name = f'{root}-{field}'
                    response = self.client.post(f'{root}libraries/create/', {'name': name, field: value})
                    self.assertEqual(response.status_code, 302)
                    library = DocumentLibrary.objects.get(name=name)
                    self.assertEqual((library.owner_id, library.workplace_id), (self.owner.pk, self.workspace.pk))
                    self.assertFalse(library.photo)
        self.assertEqual(list(Path(self.storage.location).rglob('*')), [])

    def test_edit_ignores_photo_fields_and_preserves_legacy_file(self):
        self.save_legacy_photo()
        original = self.library.photo.name
        self.client.get(self.base)
        for root in (self.base, '/documents/'):
            for field in ('photo', 'photo_crop', 'photo_remove'):
                with self.subTest(root=root, field=field):
                    value = {'photo': SimpleUploadedFile('new.png', PNG), 'photo_crop': CROP, 'photo_remove': '1'}[field]
                    response = self.client.post(f'{root}libraries/{self.library.pk}/edit/', {
                        'name': 'Nowa nazwa', 'description': 'Zmieniony opis', field: value,
                    }, headers={'X-Document-Modal': 'true'})
                    self.assertIn('redirect_url', response.json())
                    self.library.refresh_from_db()
                    self.assertEqual(self.library.name, 'Nowa nazwa')
                    self.assertEqual(self.library.description, 'Zmieniony opis')
                    self.assertEqual(self.library.photo.name, original)
                    self.assertTrue(self.storage.exists(original))
        self.assertEqual(len([p for p in Path(self.storage.location).rglob('*') if p.is_file()]), 1)

    def test_forms_have_only_metadata_and_all_surfaces_use_standard_icon(self):
        self.save_legacy_photo()
        for url in (f'{self.base}libraries/create/', self.edit_url):
            for headers in ({}, {'X-Document-Modal': 'true'}):
                with self.subTest(url=url, headers=headers):
                    response = self.client.get(url, headers=headers)
                    self.assertContains(response, 'name="name"')
                    self.assertContains(response, 'name="description"')
                    for field in ('photo', 'photo_crop', 'photo_remove'):
                        self.assertNotContains(response, f'name="{field}"')
                    self.assertNotContains(response, 'data-profile-photo-editor')
                    self.assertNotContains(response, 'enctype="multipart/form-data"')
        for query in ('?display=list', '?display=grid', f'?library={self.library.pk}'):
            with self.subTest(query=query):
                response = self.client.get(self.base + query)
                self.assertContains(response, 'documents-drive-icon')
                self.assertNotContains(response, f'src="{self.photo_url}"')
                self.assertNotContains(response, self.library.photo.name)

    def test_invalid_name_preserves_metadata_and_legacy_photo(self):
        self.save_legacy_photo()
        original = self.library.photo.name
        DocumentLibrary.objects.create(owner=self.owner, workplace=self.workspace, name='Zajęta nazwa')
        response = self.client.post(self.edit_url, {
            'name': 'Zajęta nazwa', 'description': 'Zachowany opis', 'photo_crop': CROP,
        }, headers={'X-Document-Modal': 'true'})
        self.assertIn('name', response.context['modal']['form'].errors)
        self.assertContains(response, 'Zachowany opis')
        self.library.refresh_from_db()
        self.assertEqual(self.library.name, 'Biblioteka ze zdjęciem')
        self.assertEqual(self.library.photo.name, original)
        self.assertTrue(self.storage.exists(original))

    def test_failed_database_save_preserves_legacy_photo(self):
        self.save_legacy_photo()
        original = self.library.photo.name
        with patch.object(DocumentLibrary, 'save', side_effect=IntegrityError('concurrent name conflict')):
            response = self.client.post(self.edit_url, {'name': 'Nowa nazwa'}, headers={'X-Document-Modal': 'true'})
        self.assertIn('name', response.context['modal']['form'].errors)
        self.library.refresh_from_db()
        self.assertEqual(self.library.photo.name, original)
        self.assertTrue(self.storage.exists(original))

    def test_legacy_photo_remains_available_through_authenticated_view(self):
        self.save_legacy_photo()
        response = self.client.get(self.photo_url)
        self.assertEqual(b''.join(response.streaming_content), PNG)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

    def test_photo_and_changes_require_owner_and_active_workspace(self):
        self.save_legacy_photo()
        original = self.library.photo.name
        self.assertEqual(Client().get(self.photo_url).status_code, 302)
        self.assertEqual(self.client.get(f'{self.outside_base}libraries/{self.library.pk}/photo/').status_code, 404)
        response = self.client.post(f'{self.outside_base}libraries/{self.library.pk}/edit/', {'name': self.library.name, 'photo_remove': '1'})
        self.assertEqual(response.status_code, 404)
        WorkplaceMembership.objects.create(workplace=self.workspace, user=self.other, role=WorkplaceMembership.Role.ADMIN)
        self.client.force_login(self.other)
        self.assertRedirects(self.client.get(self.photo_url), '/workplaces/', fetch_redirect_response=False)
        self.assertEqual(self.client.get(f'/documents/libraries/{self.library.pk}/photo/', follow=True).status_code, 404)
        self.assertEqual(self.client.post(self.edit_url, {'name': self.library.name, 'photo_crop': CROP}).status_code, 302)
        self.library.refresh_from_db()
        self.assertEqual(self.library.photo.name, original)

    def test_deletion_cleans_photo_but_nonempty_library_keeps_it(self):
        self.save_legacy_photo()
        original = self.library.photo.name
        folder = Folder.objects.create(library=self.library, workplace=self.workspace, owner=self.owner, name='Folder')
        self.client.post(f'{self.base}libraries/{self.library.pk}/delete/')
        self.assertTrue(self.storage.exists(original))
        folder.delete()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(f'{self.base}libraries/{self.library.pk}/delete/')
        self.assertFalse(self.storage.exists(original))
        self.assertFalse(DocumentLibrary.objects.filter(pk=self.library.pk).exists())
