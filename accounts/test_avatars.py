import base64
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.avatars import AVATARS as WORKSPACE_AVATARS
from workplaces.models import create_workplace_for_user
from .avatar import account_avatar
from .avatar_presets import AVATARS, preset_avatar
from .forms import UserProfileForm

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


class UserAvatarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username='@avatar.user', email='avatar-user@example.test', first_name='Anna', last_name='Testowa',
        )
        cls.other = get_user_model().objects.create_user(username='@avatar.other', email='avatar-other@example.test')
        cls.workspace = create_workplace_for_user(cls.user, 'Awatary')

    def setUp(self):
        storage = tempfile.TemporaryDirectory()
        self.addCleanup(storage.cleanup)
        settings = override_settings(MEDIA_ROOT=storage.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.client.force_login(self.user)
        self.url = reverse('profile')

    def data(self, **extra):
        return {
            'first_name': self.user.first_name, 'last_name': self.user.last_name,
            'email': self.user.email, 'username': self.user.username, 'presence_status': 'active', **extra,
        }

    def post(self, **extra):
        return self.client.post(self.url, self.data(**extra))

    def upload(self):
        self.assertEqual(self.post(avatar='upload', profile_photo=SimpleUploadedFile('avatar.png', PNG, 'image/png')).status_code, 302)
        self.user.refresh_from_db()
        return self.user.profile_photo

    def test_personal_pool_is_separate_and_automatic_choice_is_stable(self):
        self.assertEqual(len(AVATARS), 30)
        self.assertFalse(set(dict(AVATARS)) & set(dict(WORKSPACE_AVATARS)))
        self.assertEqual(account_avatar(self.user), account_avatar(get_user_model().objects.get(pk=self.user.pk)))
        self.assertTrue(account_avatar(self.user)['preset_class'].startswith('user-avatar-art--'))
        self.assertNotIn('preset_class', account_avatar(None))
        # Extending the picker must not reshuffle previously automatic avatars.
        self.assertEqual(preset_avatar(seed=24)['key'], 'fox')
        self.assertEqual(preset_avatar(seed=29)['key'], 'bear')

    def test_all_presets_persist_and_render_across_workspace_contexts(self):
        for key, _ in AVATARS:
            with self.subTest(key=key):
                self.assertEqual(self.post(avatar=key).status_code, 302)
                self.user.refresh_from_db()
                self.assertEqual(self.user.avatar, key)
        for path in [self.url, '/spaces/', f'/workplaces/{self.workspace.slug}/spaces/']:
            response = self.client.get(path)
            self.assertContains(response, 'user-avatar-art--dinosaur')
        self.post(avatar='auto')
        self.user.refresh_from_db()
        self.assertEqual(self.user.avatar, '')

    def test_profile_only_updates_signed_in_user_and_requires_csrf(self):
        self.post(avatar='fox', user_id=self.other.pk)
        self.other.refresh_from_db()
        self.assertEqual(self.other.avatar, '')
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(self.url, self.data(avatar='cat')).status_code, 403)
        self.client.logout()
        self.assertEqual(self.post(avatar='cat').status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.avatar, 'fox')

    def test_comment_and_team_render_the_saved_personal_preset(self):
        from django.template.loader import render_to_string
        from tasks.models import Task, TaskActivity

        self.post(avatar='owl')
        self.user.refresh_from_db()
        task = Task.objects.create(user=self.user, workplace=self.workspace, title='Awatar autora')
        activity = TaskActivity.objects.create(task=task, actor=self.user, action='commented', message='Komentarz autora')
        html = render_to_string('tasks/includes/task_activity_item.html', {'item': activity})
        self.assertIn('user-avatar-art--owl', html)
        html = render_to_string('workplaces/includes/invitation_person.html', {'person': self.user})
        self.assertIn('user-avatar-art--owl', html)

    def test_older_profile_forms_preserve_preset_or_photo(self):
        self.post(avatar='fox')
        self.post(bio='Opis')
        self.user.refresh_from_db()
        self.assertEqual(self.user.avatar, 'fox')
        photo = self.upload()
        self.post(bio='Nowy opis')
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile_photo.name, photo.name)

    def test_photo_replacement_cleanup_runs_after_commit(self):
        for choice in ['cat', 'auto']:
            photo = self.upload()
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.post(avatar=choice).status_code, 302)
                self.assertTrue(photo.storage.exists(photo.name))
            self.user.refresh_from_db()
            self.assertFalse(self.user.profile_photo)
            self.assertFalse(photo.storage.exists(photo.name))

    def test_rollback_keeps_previous_photo(self):
        photo = self.upload()
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError), transaction.atomic():
                form = UserProfileForm(self.data(avatar='cat'), instance=self.user)
                self.assertTrue(form.is_valid(), form.errors)
                form.save()
                raise RuntimeError('rollback')
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile_photo.name, photo.name)
        self.assertTrue(photo.storage.exists(photo.name))

    def test_invalid_choices_and_uploads_preserve_saved_avatar(self):
        self.post(avatar='fox')
        invalid = [
            {'avatar': 'rocket'}, {'avatar': 'unknown'}, {'avatar': 'upload'},
            {'avatar': 'upload', 'profile_photo_crop': 'invalid'},
            {'avatar': 'upload', 'profile_photo': SimpleUploadedFile('bad.png', b'broken', 'image/png')},
            {'avatar': 'upload', 'profile_photo': SimpleUploadedFile('vector.svg', b'<svg/>', 'image/svg+xml')},
        ]
        for fields in invalid:
            with self.subTest(fields=list(fields)):
                response = self.post(**fields)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
                self.user.refresh_from_db()
                self.assertEqual(self.user.avatar, 'fox')
        response = self.post(avatar='cat', first_name='')
        self.assertContains(response, 'value="cat" checked')

    def test_crop_round_trip_and_preset_ignores_unselected_upload(self):
        crop = 'data:image/png;base64,' + base64.b64encode(PNG).decode()
        self.assertEqual(self.post(avatar='upload', profile_photo_crop=crop).status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_photo)
        self.assertEqual(account_avatar(self.user)['photo_url'], self.user.profile_photo.url)
        self.assertEqual(self.post(
            avatar='panda', profile_photo_crop='invalid',
            profile_photo=SimpleUploadedFile('bad.png', b'broken', 'image/png'),
        ).status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_photo)
        self.assertEqual(self.user.avatar, 'panda')
