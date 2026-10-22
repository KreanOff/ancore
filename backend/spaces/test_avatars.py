from .testing import make_space
import base64
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import SpaceMembership
from workplaces.models import WorkplaceMembership
from .avatars import AVATARS, preset_avatar, space_avatar
from .models import Space


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


class SpaceAvatarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from .tests import SpaceTests
        SpaceTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.storage = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        self.settings_override = override_settings(PRIVATE_DOCUMENT_ROOT=self.storage.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        field = Space._meta.get_field('avatar_photo')
        original_storage = field.storage
        field.storage = FileSystemStorage(location=self.storage.name)
        self.addCleanup(setattr, field, 'storage', original_storage)
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix='avatar/', space=None):
        return f'/workplaces/{self.workspace.slug}/space/{(space or self.space).slug}/{suffix}'

    def upload(self, name='avatar.png', content=PNG):
        return self.client.post(self.url(), {'avatar': 'upload', 'avatar_photo': SimpleUploadedFile(name, content, 'image/png')}, HTTP_X_WORK_MODAL='true')

    def test_default_avatars_are_stable_and_vary_between_spaces(self):
        before = space_avatar(self.space)
        self.space.refresh_from_db()
        self.assertEqual(before, space_avatar(self.space))
        self.assertNotEqual(before, space_avatar(self.hidden_project))
        self.assertEqual(preset_avatar(seed=24)['key'], 'rocket')
        self.assertEqual(preset_avatar(seed=29)['key'], 'globe')

    def test_preset_plain_and_scoped_persists_in_header_directory_and_sidebar(self):
        choices = [(f'/spaces/{self.space.pk}/avatar/', 'rocket'), (self.url(), 'leaf')]
        choices += [(self.url(), key) for key, _ in AVATARS[-6:]]
        for url, choice in choices:
            response = self.client.post(url, {'avatar': choice}, HTTP_X_WORK_MODAL='true')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['saved'])
            self.space.refresh_from_db()
            self.assertEqual(self.space.avatar, choice)
            for path in [self.url(''), f'/workplaces/{self.workspace.slug}/spaces/', '/']:
                rendered = self.client.get(path)
                self.assertContains(rendered, f'data-space-avatar="{self.space.pk}"')
                self.assertContains(rendered, f'space-avatar-art--{choice}')
        self.client.post(self.url(), {'avatar': 'auto'})
        self.space.refresh_from_db()
        self.assertEqual(self.space.avatar, '')

    def test_owner_and_project_admin_can_edit_but_member_and_observer_cannot(self):
        for person in (self.member, self.observer):
            self.client.force_login(person)
            self.assertEqual(self.client.get(self.url()).status_code, 403)
            self.assertEqual(self.client.post(self.url(), {'avatar': 'rocket'}).status_code, 403)
            self.assertNotContains(self.client.get(self.url('')), 'Zmień awatar')
        SpaceMembership.objects.filter(space=self.project, user=self.member).update(role='admin')
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(self.url(), {'avatar': 'rocket'}).status_code, 302)

    def test_public_space_respects_existing_management_policy(self):
        self.project.visibility = 'public'
        self.project.private_owner = None
        self.project.save()
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(self.url(), {'avatar': 'rocket'}).status_code, 403)
        self.project.responsible_user = self.member
        self.project.save()
        self.assertEqual(self.client.post(self.url(), {'avatar': 'rocket'}).status_code, 302)

    def test_upload_is_private_validated_and_available_to_space_members(self):
        self.assertEqual(self.upload().status_code, 200)
        self.space.refresh_from_db()
        self.assertTrue(self.space.avatar_photo.name.startswith('space_avatars/'))
        self.assertNotIn('avatar.png', self.space.avatar_photo.name)
        for person in (self.owner, self.member, self.observer):
            self.client.force_login(person)
            for url in [self.url('avatar/photo/'), f'/spaces/{self.space.pk}/avatar/photo/']:
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Cache-Control'], 'private, no-store')
                self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
                self.assertEqual(b''.join(response.streaming_content), PNG)
        SpaceMembership.objects.filter(space=self.project, user=self.member).delete()
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(self.url('avatar/photo/')).status_code, 404)
        self.client.force_login(self.other)
        self.assertRedirects(self.client.get(self.url('avatar/photo/')), reverse('workplaces:workplaces'), fetch_redirect_response=False)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url('avatar/photo/', self.foreign_project)).status_code, 404)

    def test_workspace_membership_revocation_removes_image_access(self):
        self.upload()
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).update(is_active=False)
        self.client.force_login(self.member)
        self.assertRedirects(self.client.get(self.url('avatar/photo/')), reverse('workplaces:workplaces'), fetch_redirect_response=False)

    def test_invalid_choices_files_and_empty_upload_do_not_change_avatar(self):
        self.client.post(self.url(), {'avatar': 'rocket'})
        payloads = [
            {'avatar': '../../bad'}, {'avatar': 'upload'},
            {'avatar': 'upload', 'avatar_photo': SimpleUploadedFile('bad.svg', b'<svg></svg>')},
            {'avatar': 'upload', 'avatar_photo': SimpleUploadedFile('bad.png', b'not an image')},
            {'avatar': 'upload', 'avatar_photo': SimpleUploadedFile('big.png', PNG + b'x' * (5 * 1024 * 1024))},
        ]
        for payload in payloads:
            with self.subTest(payload=payload['avatar']):
                response = self.client.post(self.url(), payload, HTTP_X_WORK_MODAL='true')
                self.assertEqual(response.status_code, 400)
                self.assertIn('role="alert"', response.json()['html'])
                self.space.refresh_from_db()
                self.assertEqual(self.space.avatar, 'rocket')
                self.assertFalse(self.space.avatar_photo)

    def test_replacement_and_preset_remove_old_file_only_after_commit(self):
        self.upload()
        self.space.refresh_from_db()
        storage, first = self.space.avatar_photo.storage, self.space.avatar_photo.name
        with self.captureOnCommitCallbacks(execute=True):
            self.upload()
            self.assertTrue(storage.exists(first))
        self.assertFalse(storage.exists(first))
        self.space.refresh_from_db()
        second = self.space.avatar_photo.name
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url(), {'avatar': 'rocket'})
            self.assertTrue(storage.exists(second))
        self.assertFalse(storage.exists(second))
        self.space.refresh_from_db()
        self.assertFalse(self.space.avatar_photo)
        self.assertEqual(self.space.avatar, 'rocket')

    def test_deletion_and_rollback_preserve_file_lifecycle(self):
        self.upload()
        self.space.refresh_from_db()
        storage, name = self.space.avatar_photo.storage, self.space.avatar_photo.name
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    Space.objects.get(pk=self.space.pk).delete()
                    raise ValueError('rollback')
            except ValueError:
                pass
        self.assertTrue(storage.exists(name))
        with self.captureOnCommitCallbacks(execute=True):
            Space.objects.get(pk=self.space.pk).delete()
            self.assertTrue(storage.exists(name))
        self.assertFalse(storage.exists(name))

    def test_failed_save_cleans_new_file_and_keeps_previous_photo(self):
        self.upload()
        self.space.refresh_from_db()
        storage, original = self.space.avatar_photo.storage, self.space.avatar_photo.name
        with patch.object(Space, 'save', side_effect=RuntimeError('save failed')):
            with self.assertRaises(RuntimeError):
                self.upload()
        self.space.refresh_from_db()
        self.assertEqual(self.space.avatar_photo.name, original)
        self.assertEqual(len(storage.listdir('space_avatars')[1]), 1)

    def test_missing_file_method_and_csrf(self):
        self.assertEqual(self.client.get(self.url('avatar/photo/')).status_code, 404)
        self.upload()
        self.space.refresh_from_db()
        self.space.avatar_photo.storage.delete(self.space.avatar_photo.name)
        self.assertEqual(self.client.get(self.url('avatar/photo/')).status_code, 404)
        self.assertEqual(self.client.post(self.url('avatar/photo/')).status_code, 405)
        self.assertEqual(self.client.delete(self.url()).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url(), {'avatar': 'rocket'}).status_code, 403)
        client.logout()
        self.assertEqual(client.get(self.url()).status_code, 302)

    def test_settings_save_name_and_preset_together_in_plain_and_scoped_urls(self):
        for url in (self.url('edit/'), f'/spaces/{self.space.pk}/edit/'):
            response = self.client.post(url, {'name': 'Zmieniona przestrzeń', 'description': '', 'visibility': 'private', 'avatar': 'leaf'}, HTTP_X_WORK_MODAL='true')
            self.assertEqual(response.status_code, 200)
            self.space.refresh_from_db()
            self.assertEqual((self.space.name, self.space.avatar), ('Zmieniona przestrzeń', 'leaf'))

    def test_settings_crop_and_preset_preserve_private_file_lifecycle(self):
        crop = 'data:image/png;base64,' + base64.b64encode(PNG).decode()
        response = self.client.post(self.url('edit/'), {'name': 'Przycięty awatar', 'visibility': 'private', 'avatar': 'upload', 'avatar_photo_crop': crop}, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 200)
        self.space.refresh_from_db()
        storage, name = self.space.avatar_photo.storage, self.space.avatar_photo.name
        with storage.open(name) as image:
            self.assertEqual(image.read(), PNG)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url('edit/'), {'name': self.space.name, 'visibility': 'private', 'avatar': 'rocket'}, HTTP_X_WORK_MODAL='true')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(storage.exists(name))
        self.assertFalse(storage.exists(name))
        self.space.refresh_from_db()
        self.assertEqual(self.space.avatar, 'rocket')
        self.assertFalse(self.space.avatar_photo)

    def test_settings_invalid_name_or_crop_do_not_write_name_or_photo(self):
        original_name = self.space.name
        for payload in (
            {'name': ' ', 'avatar': 'upload', 'avatar_photo': SimpleUploadedFile('avatar.png', PNG, 'image/png')},
            {'name': 'Nie zapisuj', 'avatar': 'upload', 'avatar_photo_crop': 'data:image/png;base64,invalid'},
        ):
            response = self.client.post(self.url('edit/'), {'visibility': 'private', **payload}, HTTP_X_WORK_MODAL='true')
            self.assertEqual(response.status_code, 400)
            self.space.refresh_from_db()
            self.assertEqual(self.space.name, original_name)
            self.assertFalse(self.space.avatar_photo)
            self.assertEqual(list(Path(self.storage.name).rglob('*')), [])

    def test_settings_older_client_preserves_existing_photo(self):
        self.upload()
        self.space.refresh_from_db()
        old_photo = self.space.avatar_photo.name
        response = self.client.post(self.url('edit/'), {'name': self.space.name, 'visibility': 'private'}, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 200)
        self.space.refresh_from_db()
        self.assertEqual(self.space.avatar_photo.name, old_photo)

    def test_settings_rollback_after_photo_save_cleans_new_file(self):
        self.upload()
        self.space.refresh_from_db()
        old_name, storage = self.space.avatar_photo.name, self.space.avatar_photo.storage
        queryset_class = type(self.space.memberships.all())
        with patch.object(queryset_class, 'delete', side_effect=RuntimeError('Membership failure')):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url('edit/'), {'name': 'Nie zapisuj', 'visibility': 'public', 'avatar': 'upload', 'avatar_photo': SimpleUploadedFile('new.png', PNG, 'image/png')}, HTTP_X_WORK_MODAL='true')
        self.space.refresh_from_db()
        self.assertEqual(self.space.avatar_photo.name, old_name)
        self.assertEqual(self.space.visibility, 'private')
        self.assertEqual(storage.listdir('space_avatars')[1], [old_name.split('/')[-1]])
