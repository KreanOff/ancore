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

    def save_photo(self, **values):
        payload = {'name': self.library.name, 'photo_crop': CROP, **values}
        response = self.client.post(self.edit_url, payload, headers={'X-Document-Modal': 'true'})
        self.library.refresh_from_db()
        return response

    def test_upload_and_crop_work_in_normal_and_scoped_routes(self):
        self.client.get(self.base)
        for root, field in [(self.base, 'photo'), ('/documents/', 'photo_crop')]:
            with self.subTest(root=root):
                value = SimpleUploadedFile('logo.png', PNG, content_type='image/png') if field == 'photo' else CROP
                response = self.client.post(f'{root}libraries/create/', {'name': field, field: value})
                self.assertEqual(response.status_code, 302)
                library = DocumentLibrary.objects.get(name=field)
                self.assertEqual((library.owner_id, library.workplace_id), (self.owner.pk, self.workspace.pk))
                self.assertTrue(library.photo.name.startswith(f'library_photos/{self.workspace.pk}/'))
                self.assertEqual(library.photo.read(), PNG)
                library.photo.close()
                response = self.client.get(f'{root}libraries/{library.pk}/photo/', follow=True)
                self.assertEqual(b''.join(response.streaming_content), PNG)
                self.assertEqual(response['Content-Type'], 'image/png')
                self.assertEqual(response['Cache-Control'], 'private, no-store')
                self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

    def test_shared_editor_and_saved_photo_render_on_both_surfaces(self):
        response = self.save_photo()
        self.assertIn('redirect_url', response.json())
        response = self.client.get(self.edit_url, headers={'X-Document-Modal': 'true'})
        self.assertContains(response, 'enctype="multipart/form-data"')
        for marker in ('data-profile-photo-editor', 'data-profile-photo-canvas', 'data-profile-photo-zoom', 'data-profile-photo-remove', 'data-profile-photo-save'):
            self.assertContains(response, marker)
        self.assertContains(response, f'data-profile-photo-url="{self.photo_url}"')
        index = self.client.get(self.base)
        self.assertContains(index, f'src="{self.photo_url}"', count=1)
        contents = self.client.get(f'{self.base}?library={self.library.pk}')
        self.assertContains(contents, f'src="{self.photo_url}"', count=1)
        self.assertNotContains(index, '/media/library_photos/')
        self.assertNotContains(index, self.library.photo.name)

    def test_replace_and_remove_clean_files_only_after_commit(self):
        self.save_photo()
        old = self.library.photo.name
        with self.captureOnCommitCallbacks(execute=True):
            self.save_photo()
            self.assertTrue(self.storage.exists(old))
        self.assertFalse(self.storage.exists(old))
        replacement = self.library.photo.name
        self.assertNotEqual(old, replacement)
        with self.captureOnCommitCallbacks(execute=True):
            self.save_photo(photo_crop='', photo_remove='1')
            self.assertTrue(self.storage.exists(replacement))
        self.assertFalse(self.library.photo)
        self.assertFalse(self.storage.exists(replacement))
        self.assertEqual(self.client.get(self.photo_url).status_code, 404)
        self.assertContains(self.client.get(self.base), 'data-lucide="hard-drive"')

    def test_ordinary_metadata_edit_preserves_photo(self):
        self.save_photo()
        name = self.library.photo.name
        self.client.post(self.edit_url, {'name': 'Nowa nazwa', 'description': 'Opis'})
        self.library.refresh_from_db()
        self.assertEqual(self.library.photo.name, name)
        self.assertTrue(self.storage.exists(name))

    def test_crop_takes_precedence_over_remove_flag(self):
        self.save_photo(photo_remove='1')
        self.assertTrue(self.library.photo)

    def test_rejects_invalid_file_content_extension_and_size(self):
        for filename, data in [('fake.png', b'bad'), ('empty.png', b''), ('image.svg', b'<svg/>'), ('image.gif', b'GIF89a'), ('image.jpg', PNG), ('large.png', PNG + b'x' * (5 * 1024 * 1024))]:
            with self.subTest(filename=filename):
                response = self.client.post(self.edit_url, {'name': self.library.name, 'photo': SimpleUploadedFile(filename, data)}, headers={'X-Document-Modal': 'true'})
                self.assertEqual(response.status_code, 200)
                self.assertIn('photo', response.context['modal']['form'].errors)
                self.library.refresh_from_db()
                self.assertFalse(self.library.photo)
        self.assertEqual(list(Path(self.storage.location).rglob('*')), [])

    def test_rejects_invalid_crop_data_without_replacing_saved_photo(self):
        self.save_photo()
        original = self.library.photo.name
        for crop in ['invalid', 'data:image/png;base64,@@@', 'data:image/png;base64,', 'data:image/jpeg;base64,' + base64.b64encode(PNG).decode(), 'data:image/svg+xml;base64,PHN2Zy8+', 'data:image/png;base64,' + 'A' * (7 * 1024 * 1024)]:
            with self.subTest(crop=crop[:32]):
                response = self.save_photo(photo_crop=crop)
                self.assertIn('photo_crop', response.context['modal']['form'].errors)
                self.assertEqual(self.library.photo.name, original)
                self.assertTrue(self.storage.exists(original))

    def test_validation_preserves_crop_and_does_not_apply_photo_removal(self):
        self.save_photo()
        original = self.library.photo.name
        duplicate = DocumentLibrary.objects.create(owner=self.owner, workplace=self.workspace, name='Zajęta nazwa')
        response = self.save_photo(name=duplicate.name)
        self.assertContains(response, CROP)
        self.assertIn('name', response.context['modal']['form'].errors)
        self.assertEqual(self.library.photo.name, original)
        self.save_photo(name=duplicate.name, photo_crop='', photo_remove='1')
        self.assertEqual(self.library.photo.name, original)
        self.assertTrue(self.storage.exists(original))

    def test_failed_database_save_removes_new_file_and_preserves_original(self):
        self.save_photo()
        original = self.library.photo.name
        real_save = DocumentLibrary.save
        def fail_after_file_write(instance, *args, **kwargs):
            real_save(instance, *args, **kwargs)
            raise IntegrityError('simulated concurrent name conflict')
        with patch.object(DocumentLibrary, 'save', fail_after_file_write):
            response = self.save_photo()
        self.assertIn('name', response.context['modal']['form'].errors)
        self.assertEqual(self.library.photo.name, original)
        self.assertTrue(self.storage.exists(original))
        self.assertEqual(len([p for p in Path(self.storage.location).rglob('*') if p.is_file()]), 1)

    def test_photo_and_changes_require_owner_and_active_workspace(self):
        self.save_photo()
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
        self.save_photo()
        original = self.library.photo.name
        folder = Folder.objects.create(library=self.library, workplace=self.workspace, owner=self.owner, name='Folder')
        self.client.post(f'{self.base}libraries/{self.library.pk}/delete/')
        self.assertTrue(self.storage.exists(original))
        folder.delete()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(f'{self.base}libraries/{self.library.pk}/delete/')
        self.assertFalse(self.storage.exists(original))
        self.assertFalse(DocumentLibrary.objects.filter(pk=self.library.pk).exists())
