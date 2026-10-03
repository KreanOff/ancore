import base64
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.avatars import AVATARS
from .forms import WorkplaceForm
from .models import Workplace, WorkplaceMembership, create_workplace_for_user
from .templatetags.workplace_avatar import workplace_avatar

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


class WorkplaceAvatarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='avatar-owner', email='avatar-owner@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Workspace awatara')
        cls.admin = get_user_model().objects.create_user(username='avatar-admin', email='avatar-admin@example.test')
        cls.member = get_user_model().objects.create_user(username='avatar-member', email='avatar-member@example.test')
        cls.other = get_user_model().objects.create_user(username='avatar-other', email='avatar-other@example.test')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.admin, role='admin')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member, role='member')

    def setUp(self):
        self.storage = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.storage.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.client.force_login(self.owner)
        self.url = reverse('workplaces:update', args=[self.workspace.pk])

    def post(self, **extra):
        return self.client.post(self.url, {'name': self.workspace.name, **extra})

    def upload(self):
        return self.post(avatar='upload', workplace_photo=SimpleUploadedFile('logo.png', PNG, 'image/png'))

    def test_presets_create_and_update_render_in_directory_and_scoped_header(self):
        response = self.client.post(reverse('workplaces:workplaces'), {'name': 'Nowy Workspace', 'avatar': 'ship'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Workplace.objects.get(name='Nowy Workspace').avatar, 'ship')
        for key, _ in AVATARS:
            with self.subTest(key=key):
                self.assertEqual(self.post(avatar=key).status_code, 302)
                self.workspace.refresh_from_db()
                self.assertEqual(self.workspace.avatar, key)
        for path in [reverse('workplaces:workplaces'), f'/workplaces/{self.workspace.slug}/spaces/']:
            self.assertContains(self.client.get(path), 'space-avatar-art--smile')
        self.post(avatar='auto')
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.avatar, '')
        self.assertEqual(workplace_avatar(self.workspace), workplace_avatar(Workplace.objects.get(pk=self.workspace.pk)))

    def test_management_roles_and_csrf(self):
        for user, status in [(self.owner, 302), (self.admin, 302), (self.member, 403), (self.other, 404)]:
            self.client.force_login(user)
            self.assertEqual(self.post(avatar='rocket').status_code, status)
        self.client.force_login(self.member)
        response = self.client.get(reverse('workplaces:workplaces'), {'workspace': self.workspace.pk})
        # The creation picker remains available; the read-only edit form has none.
        edit_html = response.content.decode().split('id="workplace-edit-form"', 1)[1].split('</form>', 1)[0]
        self.assertNotIn('data-workplace-avatar-picker', edit_html)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.owner)
        self.assertEqual(csrf_client.post(self.url, {'name': self.workspace.name, 'avatar': 'leaf'}).status_code, 403)

    def test_settings_without_avatar_keep_existing_choice_and_photo(self):
        self.post(avatar='leaf')
        self.post(description='Nowy opis')
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.avatar, 'leaf')
        self.assertEqual(self.upload().status_code, 302)
        self.workspace.refresh_from_db()
        photo = self.workspace.workplace_photo.name
        self.post(description='Kolejny opis')
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.workplace_photo.name, photo)

    def test_photo_to_preset_removes_file_only_after_commit(self):
        self.upload()
        self.workspace.refresh_from_db()
        photo = self.workspace.workplace_photo
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.post(avatar='rocket').status_code, 302)
            self.assertTrue(photo.storage.exists(photo.name))
        self.workspace.refresh_from_db()
        self.assertFalse(self.workspace.workplace_photo)
        self.assertFalse(photo.storage.exists(photo.name))
        self.assertEqual(self.workspace.avatar, 'rocket')

    def test_rollback_preserves_photo(self):
        self.upload()
        self.workspace.refresh_from_db()
        photo = self.workspace.workplace_photo
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError), transaction.atomic():
                form = WorkplaceForm({'name': self.workspace.name, 'avatar': 'ship'}, instance=self.workspace, user=self.owner)
                self.assertTrue(form.is_valid(), form.errors)
                form.save()
                raise RuntimeError('rollback')
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.workplace_photo.name, photo.name)
        self.assertTrue(photo.storage.exists(photo.name))

    def test_invalid_avatar_or_photo_does_not_change_workspace(self):
        self.post(avatar='leaf')
        for data in [{'avatar': 'unknown'}, {'avatar': 'upload'}, {'avatar': 'upload', 'workplace_photo': SimpleUploadedFile('bad.png', b'broken', 'image/png')}]:
            with self.subTest(data=list(data)):
                response = self.post(**data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['edit_form'].errors)
                self.workspace.refresh_from_db()
                self.assertEqual(self.workspace.avatar, 'leaf')
        response = self.client.post(self.url, {'name': '', 'avatar': 'ship'})
        self.assertContains(response, 'value="ship" checked')

    def test_crop_round_trip_and_preset_take_precedence(self):
        crop = 'data:image/png;base64,' + base64.b64encode(PNG).decode()
        self.assertEqual(self.post(avatar='upload', workplace_photo_crop=crop).status_code, 302)
        self.workspace.refresh_from_db()
        self.assertTrue(self.workspace.workplace_photo)
        self.assertEqual(self.post(avatar='star', workplace_photo_crop=crop).status_code, 302)
        self.workspace.refresh_from_db()
        self.assertFalse(self.workspace.workplace_photo)
        self.assertEqual(self.workspace.avatar, 'star')
        response = self.client.post(reverse('workplaces:workplaces'), {'name': 'Ilustracja', 'avatar': 'ship', 'workplace_photo_crop': crop})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Workplace.objects.get(name='Ilustracja').workplace_photo)

    def test_preset_ignores_unselected_invalid_upload_and_crop(self):
        response = self.post(
            avatar='compass', workplace_photo_crop='invalid',
            workplace_photo=SimpleUploadedFile('bad.png', b'broken', 'image/png'),
        )
        self.assertEqual(response.status_code, 302)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.avatar, 'compass')
        self.assertFalse(self.workspace.workplace_photo)
