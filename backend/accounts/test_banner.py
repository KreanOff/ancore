import base64
import json
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.templatetags.static import static
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from workplaces.models import create_workplace_for_user
from .forms import PROFILE_BANNER_MAX_SIZE, UserBannerForm, UserProfileForm


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


class UserBannerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username='@banner.user', email='banner-user@example.test',
            first_name='Anna', last_name='Testowa', avatar='fox', bio='Zapisany opis',
            phone_number='123456789', job_title='Projektantka', presence_status='busy',
        )
        cls.other = get_user_model().objects.create_user(
            username='@banner.other', email='banner-other@example.test', first_name='Jan',
        )
        cls.workspace = create_workplace_for_user(cls.user, 'Banery')

    def setUp(self):
        storage = tempfile.TemporaryDirectory()
        self.addCleanup(storage.cleanup)
        settings = override_settings(MEDIA_ROOT=storage.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user.profile_photo.save('avatar.png', SimpleUploadedFile('avatar.png', PNG, 'image/png'))
        self.photo_name = self.user.profile_photo.name
        self.client.force_login(self.user)
        self.url = reverse('update_profile_banner')
        self.api_url = reverse('accounts-api') + '?url=' + self.url
        self.profile_api = reverse('accounts-api') + '?url=' + reverse('profile')

    def upload(self, name='banner.png', content=PNG):
        return SimpleUploadedFile(name, content, 'image/png')

    def assert_saved(self, response, api=False):
        if api:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {'redirect': reverse('profile')})
        else:
            self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)

    def save_banner(self, api=False, **crop):
        response = self.client.post(self.api_url if api else self.url, {'profile_banner': self.upload(), **crop})
        self.assert_saved(response, api)
        self.user.refresh_from_db()
        return self.user.profile_banner

    def test_default_and_custom_banner_payload_and_separate_forms(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['banner_form'].is_bound)
        data = self.client.get(self.profile_api).json()['data']
        self.assertEqual(data['banner'], {
            'url': static('img/auth/wallpaper-fluent-bloom-light-4k.webp'),
            'default_url': static('img/auth/wallpaper-fluent-bloom-light-4k.webp'),
            'custom': False, 'max_size': PROFILE_BANNER_MAX_SIZE,
            'crop': {'x': 50, 'y': 50, 'zoom': 1},
        })
        self.assertEqual(data['urls']['update_profile_banner'], self.url)
        self.assertEqual({field['name'] for field in data['banner_form']['fields']}, {
            'profile_banner', 'remove_banner', 'profile_banner_x', 'profile_banner_y', 'profile_banner_zoom',
        })
        self.assertNotIn('profile_banner', {field['name'] for field in data['form']['fields']})
        saved = self.save_banner(api=True)
        data = self.client.get(self.profile_api).json()['data']
        self.assertTrue(data['banner']['custom'])
        self.assertEqual(data['banner']['url'], saved.url)
        self.assertNotEqual(data['banner']['url'], data['banner']['default_url'])

    def test_html_and_api_upload_only_change_current_users_banner(self):
        fields = ('first_name', 'last_name', 'email', 'username', 'avatar', 'profile_photo',
                  'bio', 'phone_number', 'job_title', 'presence_status')
        original = get_user_model().objects.values(*fields).get(pk=self.user.pk)
        for api in (False, True):
            with self.subTest(api=api), self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(self.api_url if api else self.url, {
                    'profile_banner': self.upload(), 'user_id': self.other.pk,
                    'first_name': 'Nadpisane', 'bio': 'Nadpisane', 'avatar': 'cat',
                    'profile_photo': self.upload('other-avatar.png'),
                })
                self.assert_saved(response, api)
                self.user.refresh_from_db()
                self.other.refresh_from_db()
                self.assertTrue(self.user.profile_banner.name.startswith('profile_banners/'))
                self.assertEqual(self.user.profile_banner.read(), PNG)
                self.assertFalse(self.other.profile_banner)
                self.assertEqual(get_user_model().objects.values(*fields).get(pk=self.user.pk), original)
                self.assertTrue(self.user.profile_photo.storage.exists(self.photo_name))

    def test_replacement_deletes_previous_file_only_after_commit(self):
        previous = self.save_banner()
        for api in (False, True):
            with self.subTest(api=api):
                with self.captureOnCommitCallbacks(execute=True):
                    current = self.save_banner(api=api)
                    self.assertNotEqual(current.name, previous.name)
                    self.assertTrue(previous.storage.exists(previous.name))
                self.assertFalse(previous.storage.exists(previous.name))
                self.assertTrue(current.storage.exists(current.name))
                previous = current

    def test_reset_restores_default_and_cleans_file_after_commit(self):
        for api in (False, True):
            with self.subTest(api=api):
                previous = self.save_banner()
                with self.captureOnCommitCallbacks(execute=True):
                    if api:
                        response = self.client.post(self.api_url, json.dumps({'remove_banner': True}), content_type='application/json')
                    else:
                        response = self.client.post(self.url, {'remove_banner': '1'})
                    self.assert_saved(response, api)
                    self.assertTrue(previous.storage.exists(previous.name))
                self.assertFalse(previous.storage.exists(previous.name))
                self.user.refresh_from_db()
                self.assertFalse(self.user.profile_banner)
                self.assertEqual(self.user.profile_photo.name, self.photo_name)
                data = self.client.get(self.profile_api).json()['data']
                self.assertFalse(data['banner']['custom'])
                self.assertEqual(data['banner']['url'], data['banner']['default_url'])

    def test_reupload_after_reset_gets_a_new_url_and_preserves_extension(self):
        previous = self.save_banner()
        with self.captureOnCommitCallbacks(execute=True):
            self.assert_saved(self.client.post(self.url, {'remove_banner': '1'}))
        self.assertFalse(previous.storage.exists(previous.name))
        current = self.save_banner()
        self.assertNotEqual(current.url, previous.url)
        self.assertTrue(current.name.endswith('.png'))
        self.assertEqual(current.read(), PNG)

    def test_invalid_uploads_preserve_saved_banner_and_return_only_banner_errors(self):
        saved = self.save_banner()
        invalid = [
            lambda: {},
            lambda: {'remove_banner': 'false'},
            lambda: {'profile_banner': self.upload('bad.png', b'broken')},
            lambda: {'profile_banner': self.upload('vector.svg', b'<svg/>')},
            lambda: {'profile_banner': self.upload('mismatch.jpg')},
            lambda: {'profile_banner': self.upload('large.png', PNG + b'x' * PROFILE_BANNER_MAX_SIZE)},
        ]
        for api in (False, True):
            for case, payload in enumerate(invalid):
                with self.subTest(api=api, case=case):
                    response = self.client.post(self.api_url if api else self.url, payload())
                    self.assertEqual(response.status_code, 400)
                    if api:
                        data = response.json()['data']
                        self.assertEqual(response.json()['type'], 'account-profile')
                        self.assertTrue(data['banner_form']['bound'])
                        self.assertTrue(next(field for field in data['banner_form']['fields'] if field['name'] == 'profile_banner')['errors'])
                        self.assertFalse(data['form']['bound'])
                        self.assertEqual(data['banner']['url'], saved.url)
                    else:
                        self.assertTrue(response.context['banner_form'].errors['profile_banner'])
                        self.assertFalse(response.context['form'].is_bound)
                    self.user.refresh_from_db()
                    self.assertEqual(self.user.profile_banner.name, saved.name)
                    self.assertTrue(saved.storage.exists(saved.name))

    def test_upload_takes_precedence_over_reset_and_reset_without_custom_banner_is_valid(self):
        self.assert_saved(self.client.post(self.url, {'remove_banner': '1'}))
        self.assert_saved(self.client.post(self.url, {'remove_banner': '1', 'profile_banner': self.upload()}))
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_banner)

    def test_csrf_is_required_for_html_and_api_upload(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        for url in (self.url, self.api_url):
            with self.subTest(url=url):
                self.assertEqual(client.post(url, {'profile_banner': self.upload()}).status_code, 403)
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_banner)
        client.get(reverse('profile'))
        token = client.cookies['csrftoken'].value
        self.assert_saved(client.post(self.api_url, {'profile_banner': self.upload()}, HTTP_X_CSRFTOKEN=token), api=True)

    def test_anonymous_and_non_post_requests_cannot_change_banner(self):
        for url in (self.url, self.api_url):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)
                self.assertEqual(self.client.put(url).status_code, 405)
        self.client.logout()
        response = self.client.post(self.url, {'profile_banner': self.upload()})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('login')))
        self.assertEqual(self.client.post(self.api_url, {'profile_banner': self.upload()}).status_code, 401)
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_banner)

    def test_profile_update_ignores_banner_fields(self):
        saved = self.save_banner()
        response = self.client.post(reverse('profile'), {
            'first_name': 'Zmieniona', 'last_name': self.user.last_name,
            'email': self.user.email, 'username': self.user.username, 'presence_status': 'busy',
            'profile_banner': self.upload('ignored.png'), 'remove_banner': '1',
        })
        self.assert_saved(response)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Zmieniona')
        self.assertEqual(self.user.profile_banner.name, saved.name)
        self.assertTrue(saved.storage.exists(saved.name))

    def test_banner_save_preserves_a_concurrent_profile_update(self):
        form = UserBannerForm({}, {'profile_banner': self.upload()}, instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        get_user_model().objects.filter(pk=self.user.pk).update(bio='Nowszy opis')
        form.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, 'Nowszy opis')
        self.assertTrue(self.user.profile_banner)

    def test_stale_profile_form_preserves_a_concurrent_banner_update(self):
        form = UserProfileForm({
            'first_name': self.user.first_name, 'last_name': self.user.last_name,
            'email': self.user.email, 'username': self.user.username,
            'presence_status': 'busy', 'bio': 'Nowy opis',
        }, instance=get_user_model().objects.get(pk=self.user.pk))
        self.assertTrue(form.is_valid(), form.errors)
        saved = self.save_banner(profile_banner_x=15, profile_banner_y=85, profile_banner_zoom=2)
        form.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, 'Nowy opis')
        self.assertEqual(self.user.profile_banner.name, saved.name)
        self.assertEqual((self.user.profile_banner_x, self.user.profile_banner_y, self.user.profile_banner_zoom), (15, 85, 2))

    def test_rollback_keeps_previous_banner(self):
        saved = self.save_banner()
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError), transaction.atomic():
                form = UserBannerForm({'remove_banner': '1'}, instance=self.user)
                self.assertTrue(form.is_valid(), form.errors)
                form.save()
                raise RuntimeError('rollback')
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile_banner.name, saved.name)
        self.assertTrue(saved.storage.exists(saved.name))

    def test_cleanup_preserves_a_file_still_referenced_by_another_account(self):
        saved = self.save_banner()
        self.other.profile_banner = saved.name
        self.other.save(update_fields=['profile_banner'])
        with self.captureOnCommitCallbacks(execute=True):
            self.assert_saved(self.client.post(self.url, {'remove_banner': '1'}))
        self.assertTrue(saved.storage.exists(saved.name))
        self.other.refresh_from_db()
        self.assertEqual(self.other.profile_banner.name, saved.name)

    def test_stale_banner_form_cleans_the_latest_replaced_file(self):
        first = self.save_banner()
        stale_form = UserBannerForm({}, {'profile_banner': self.upload('last.png')},
                                    instance=get_user_model().objects.get(pk=self.user.pk))
        self.assertTrue(stale_form.is_valid(), stale_form.errors)
        with self.captureOnCommitCallbacks(execute=True):
            second = self.save_banner()
        self.assertFalse(first.storage.exists(first.name))
        with self.captureOnCommitCallbacks(execute=True):
            last = stale_form.save().profile_banner
            self.assertTrue(second.storage.exists(second.name))
        self.assertFalse(second.storage.exists(second.name))
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile_banner.name, last.name)
        self.assertTrue(last.storage.exists(last.name))

    def test_upload_stores_crop_without_changing_original_image(self):
        crop = {'profile_banner_x': 12.5, 'profile_banner_y': 81.25, 'profile_banner_zoom': 1.75}
        for api in (False, True):
            with self.subTest(api=api), self.captureOnCommitCallbacks(execute=True):
                saved = self.save_banner(api=api, **crop)
                self.assertEqual(saved.read(), PNG)
                self.assertEqual(self.client.get(self.profile_api).json()['data']['banner']['crop'], {
                    'x': 12.5, 'y': 81.25, 'zoom': 1.75,
                })
                response = self.client.get(reverse('profile'))
                self.assertContains(response, 'object-position: 12.5% 81.25%; transform: scale(1.75); transform-origin: 12.5% 81.25%;')
                self.assertContains(response, 'class="profile-banner-crop-fields"')
                for name in crop:
                    self.assertContains(response, f'name="{name}"')

    def test_crop_only_keeps_file_url_and_does_not_write_or_delete_storage(self):
        saved = self.save_banner()
        for api in (False, True):
            with self.subTest(api=api):
                with patch.object(saved.storage, 'save', wraps=saved.storage.save) as store, \
                        patch.object(saved.storage, 'delete', wraps=saved.storage.delete) as delete, \
                        self.captureOnCommitCallbacks(execute=True) as callbacks:
                    response = self.client.post(self.api_url if api else self.url, {
                        'profile_banner_x': 23.4567, 'profile_banner_y': 78.9,
                        'profile_banner_zoom': 2.25, 'user_id': self.other.pk,
                    })
                    self.assert_saved(response, api)
                store.assert_not_called()
                delete.assert_not_called()
                self.assertEqual(callbacks, [])
                self.user.refresh_from_db()
                self.other.refresh_from_db()
                self.assertEqual(self.user.profile_banner.url, saved.url)
                self.assertEqual(self.user.profile_banner.read(), PNG)
                self.assertEqual((self.user.profile_banner_x, self.user.profile_banner_y, self.user.profile_banner_zoom), (23.4567, 78.9, 2.25))
                self.assertEqual((self.other.profile_banner_x, self.other.profile_banner_y, self.other.profile_banner_zoom), (50, 50, 1))

    def test_partial_crop_preserves_other_coordinates_and_legacy_upload_and_reset_center(self):
        self.save_banner(profile_banner_x=10, profile_banner_y=90, profile_banner_zoom=2)
        self.assert_saved(self.client.post(self.api_url, json.dumps({'profile_banner_x': 30}), content_type='application/json'), api=True)
        self.user.refresh_from_db()
        self.assertEqual((self.user.profile_banner_x, self.user.profile_banner_y, self.user.profile_banner_zoom), (30, 90, 2))
        self.save_banner()
        self.assertEqual((self.user.profile_banner_x, self.user.profile_banner_y, self.user.profile_banner_zoom), (50, 50, 1))
        self.save_banner(profile_banner_x=10, profile_banner_y=90, profile_banner_zoom=2)
        self.assert_saved(self.client.post(self.url, {
            'remove_banner': '1', 'profile_banner_x': 20, 'profile_banner_y': 80, 'profile_banner_zoom': 3,
        }))
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_banner)
        self.assertEqual((self.user.profile_banner_x, self.user.profile_banner_y, self.user.profile_banner_zoom), (50, 50, 1))

    def test_crop_validation_rejects_nonfinite_and_out_of_range_values(self):
        saved = self.save_banner(profile_banner_x=15, profile_banner_y=85, profile_banner_zoom=2)
        invalid = [
            ('profile_banner_x', 'nan'), ('profile_banner_y', 'inf'),
            ('profile_banner_zoom', '-inf'), ('profile_banner_zoom', '1e309'),
            ('profile_banner_x', '-0.1'), ('profile_banner_y', '100.01'),
            ('profile_banner_zoom', '0.99'), ('profile_banner_zoom', '3.01'),
        ]
        for api in (False, True):
            for name, value in invalid:
                with self.subTest(api=api, name=name, value=value):
                    response = self.client.post(self.api_url if api else self.url, {name: value})
                    self.assertEqual(response.status_code, 400)
                    if api:
                        data = response.json()['data']
                        self.assertTrue(next(field for field in data['banner_form']['fields'] if field['name'] == name)['errors'])
                        self.assertEqual(data['banner']['crop'], {'x': 15, 'y': 85, 'zoom': 2})
                        self.assertFalse(data['form']['bound'])
                    else:
                        self.assertTrue(response.context['banner_form'].errors[name])
                    self.user.refresh_from_db()
                    self.assertEqual(self.user.profile_banner.name, saved.name)
                    self.assertEqual((self.user.profile_banner_x, self.user.profile_banner_y, self.user.profile_banner_zoom), (15, 85, 2))

    def test_crop_boundaries_are_allowed(self):
        self.save_banner()
        for x, y, zoom in ((0, 100, 1), (100, 0, 3)):
            with self.subTest(x=x, y=y, zoom=zoom):
                self.assert_saved(self.client.post(self.url, {
                    'profile_banner_x': x, 'profile_banner_y': y, 'profile_banner_zoom': zoom,
                }))
                self.user.refresh_from_db()
                self.assertEqual((self.user.profile_banner_x, self.user.profile_banner_y, self.user.profile_banner_zoom), (x, y, zoom))

    def test_crop_only_requires_a_custom_banner_owned_by_current_user(self):
        self.other.profile_banner = 'profile_banners/other.png'
        self.other.save(update_fields=['profile_banner'])
        for url in (self.url, self.api_url):
            with self.subTest(url=url):
                response = self.client.post(url, {'profile_banner_x': 10, 'user_id': self.other.pk})
                self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.other.refresh_from_db()
        self.assertFalse(self.user.profile_banner)
        self.assertEqual(self.user.profile_banner_x, 50)
        self.assertEqual(self.other.profile_banner_x, 50)

    def test_invalid_crop_upload_renders_persisted_banner_in_html(self):
        saved = self.save_banner(profile_banner_x=12.5, profile_banner_y=81.25, profile_banner_zoom=1.75)
        response = self.client.post(self.url, {
            'profile_banner': self.upload('unsaved.png'), 'profile_banner_x': 75,
            'profile_banner_y': 25, 'profile_banner_zoom': 4,
        })
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, f'src="{saved.url}"', status_code=400)
        self.assertContains(response, 'object-position: 12.5% 81.25%; transform: scale(1.75)', status_code=400)
        self.assertNotContains(response, 'src="/media/unsaved.png"', status_code=400)
        self.assertEqual(response.context['banner_form']['profile_banner_x'].value(), '75')
        self.assertFalse(response.context['form'].is_bound)
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile_banner.name, saved.name)

    def test_stale_crop_form_cannot_restore_a_replaced_or_removed_file(self):
        for remove in (False, True):
            with self.subTest(remove=remove):
                self.save_banner()
                form = UserBannerForm({'profile_banner_x': 25},
                                      instance=get_user_model().objects.get(pk=self.user.pk))
                self.assertTrue(form.is_valid(), form.errors)
                with self.captureOnCommitCallbacks(execute=True):
                    if remove:
                        self.assert_saved(self.client.post(self.url, {'remove_banner': '1'}))
                        latest = ''
                    else:
                        latest = self.save_banner(profile_banner_x=90).name
                with self.assertRaisesMessage(ValidationError, 'Baner został zmieniony'):
                    form.save()
                self.user.refresh_from_db()
                self.assertEqual(self.user.profile_banner.name, latest)
                self.assertEqual(self.user.profile_banner_x, 50 if remove else 90)

    def test_stale_crop_validation_error_returns_bound_form(self):
        self.save_banner()
        for url in (self.url, self.api_url):
            with self.subTest(url=url), patch.object(UserBannerForm, 'save', side_effect=ValidationError('Baner został zmieniony.')):
                response = self.client.post(url, {'profile_banner_x': 25})
                self.assertEqual(response.status_code, 400)
                if url == self.api_url:
                    self.assertEqual(response.json()['data']['banner_form']['errors'], ['Baner został zmieniony.'])
                else:
                    self.assertEqual(response.context['banner_form'].non_field_errors(), ['Baner został zmieniony.'])
