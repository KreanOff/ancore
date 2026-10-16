import base64
import json
import tempfile

from django.contrib.auth import SESSION_KEY, get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from workplaces.models import create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, WORKPLACE_URL_SCOPE_SESSION_KEY
from .views import SWITCH_ACCOUNTS_HASHES_KEY, SWITCH_ACCOUNTS_SESSION_KEY


class AccountFrontendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'account-frontend-test-83!'
        cls.user = get_user_model().objects.create_user(
            username='@anna.frontend', email='anna.frontend@example.test',
            first_name='Anna', last_name='Nowak', password=cls.password,
        )
        cls.other = get_user_model().objects.create_user(
            username='@jan.frontend', email='jan.frontend@example.test',
            first_name='Jan', last_name='Kowalski', password=cls.password,
        )
        cls.workspace = create_workplace_for_user(cls.user, 'Konta frontend')

    def api(self, name, body=None, client=None, **extra):
        client = client or self.client
        url = reverse('accounts-api') + '?url=' + reverse(name)
        if body is None:
            return client.get(url, **extra)
        return client.post(url, json.dumps(body), content_type='application/json', **extra)

    def profile_data(self, **extra):
        return {'first_name': 'Anna', 'last_name': 'Nowak', 'email': self.user.email,
                'username': self.user.username, 'presence_status': 'busy', **extra}

    def add(self):
        return self.api('add_account', {'username': self.other.email, 'password': self.password})

    def test_public_screens_have_safe_bootstrap_and_no_store(self):
        for name in ('login', 'register'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, 'data-react-root="page"')
                self.assertContains(response, 'ancore-page-data')
                self.assertEqual(response.context['frontend_bootstrap']['type'], 'account-auth')
                self.assertEqual(response.context['frontend_bootstrap']['api_url'], reverse('accounts-api'))
                self.assertIn('no-store', response['Cache-Control'])
                data = self.api(name)
                self.assertEqual(data.status_code, 200)
                self.assertEqual(data['Cache-Control'], 'no-store')

    def test_account_api_does_not_proxy_other_routes_or_origins(self):
        for target, status in [('/settings/', 404), (reverse('presence_ping'), 404),
                               (reverse('accounts-api'), 404), ('https://example.test/', 400),
                               ('//example.test/', 400), ('/\\example.test/', 400), ('http://[', 400)]:
            with self.subTest(target=target):
                response = self.client.get(reverse('accounts-api'), {'url': target})
                self.assertEqual(response.status_code, status)
                self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(self.client.get(reverse('react-page'), {'url': reverse('login')}).status_code, 401)

    def test_private_account_routes_require_session(self):
        for name in ('profile', 'add_account', 'switch_account', 'remove_account', 'update_presence_status', 'logout'):
            for body in (None, {}):
                with self.subTest(name=name, body=body):
                    self.assertEqual(self.api(name, body).status_code, 401)

    def test_methods_and_json_shape_are_checked(self):
        self.client.force_login(self.user)
        for name in ('switch_account', 'remove_account', 'update_presence_status', 'logout'):
            response = self.api(name)
            self.assertEqual(response.status_code, 405)
            self.assertEqual(response['Allow'], 'POST')
        url = reverse('accounts-api') + '?url=' + reverse('profile')
        self.assertEqual(self.client.put(url).status_code, 405)
        for body in ('{bad', '[]', '{"email": {"nested": true}}'):
            self.assertEqual(self.client.post(url, body, content_type='application/json').status_code, 400)

    def test_login_ignores_next_and_preserves_workspace_and_csrf_rotation(self):
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session[WORKPLACE_URL_SCOPE_SESSION_KEY] = True
        session.save()
        self.client.get(reverse('login'))
        old_csrf = self.client.cookies['csrftoken'].value
        response = self.api('login', {'username': self.user.email.upper(), 'password': self.password,
                                      'next': 'https://example.test/'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('example.test', response.json()['redirect'])
        self.assertIn('/for-you/', response.json()['redirect'])
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.assertEqual(self.client.session[ACTIVE_WORKPLACE_SESSION_KEY], self.workspace.pk)
        self.assertNotEqual(old_csrf, self.client.cookies['csrftoken'].value)

    def test_wrong_and_inactive_login_do_not_echo_passwords(self):
        for inactive in (False, True):
            if inactive:
                get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
            response = self.api('login', {'username': self.user.email, 'password': 'never-echo-this'})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['type'], 'account-auth')
            self.assertNotContains(response, 'never-echo-this', status_code=400)
            self.assertNotIn(SESSION_KEY, self.client.session)
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=True)

    def test_registration_validates_then_creates_without_logging_in(self):
        payload = {'first_name': 'Ewa', 'last_name': 'Testowa', 'email': 'ewa.frontend@example.test',
                   'password1': self.password, 'password2': 'mismatch-never-echo'}
        response = self.api('register', payload)
        self.assertEqual(response.status_code, 400)
        self.assertNotContains(response, self.password, status_code=400)
        self.assertNotContains(response, payload['password2'], status_code=400)
        self.assertTrue(next(f for f in response.json()['data']['form']['fields'] if f['name'] == 'password2')['errors'])
        payload['password2'] = self.password
        self.assertEqual(self.api('register', payload).json(), {'redirect': reverse('login')})
        created = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(created.check_password(self.password))
        self.assertNotIn(SESSION_KEY, self.client.session)
        payload['email'] = payload['email'].upper()
        self.assertEqual(self.api('register', payload).status_code, 400)

    def test_csrf_is_required_for_public_and_private_operations(self):
        client = Client(enforce_csrf_checks=True)
        for name in ('login', 'register'):
            response = self.api(name, {}, client=client)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response['Content-Type'], 'application/json')
        client.force_login(self.user)
        for name in ('profile', 'add_account', 'switch_account', 'remove_account', 'update_presence_status', 'logout'):
            self.assertEqual(self.api(name, {}, client=client).status_code, 403)
        client.get(reverse('profile'))
        token = client.cookies['csrftoken'].value
        self.assertEqual(self.api('profile', self.profile_data(), client=client, HTTP_X_CSRFTOKEN=token).status_code, 200)

    def test_profile_only_exposes_current_identity_and_authenticated_switcher(self):
        self.client.force_login(self.user)
        response = self.api('profile')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['user']['email'], self.user.email)
        self.assertEqual([a['id'] for a in data['accounts']], [str(self.user.pk)])
        self.assertEqual(len(data['form']['avatars']), 30)
        self.assertNotIn(self.other.email, response.content.decode())
        self.assertNotIn(self.user.get_session_auth_hash(), response.content.decode())
        self.assertNotIn('password', response.content.decode())

    def test_invalid_profile_preserves_draft_separate_from_saved_summary(self):
        self.client.force_login(self.user)
        response = self.api('profile', self.profile_data(first_name='<script>draft</script>', email=self.other.email))
        self.assertEqual(response.status_code, 400)
        data = response.json()['data']
        self.assertEqual(data['user']['first_name'], 'Anna')
        fields = {f['name']: f for f in data['form']['fields']}
        self.assertEqual(fields['first_name']['value'], '<script>draft</script>')
        self.assertTrue(fields['email']['errors'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Anna')

    def test_profile_update_ignores_other_user_and_preserves_active_workspace(self):
        self.client.force_login(self.user)
        self.client.get(reverse('profile'))
        response = self.api('profile', self.profile_data(first_name='Zmieniona', user_id=self.other.pk, avatar='fox'))
        self.assertEqual(response.json(), {'redirect': reverse('profile')})
        self.user.refresh_from_db(); self.other.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Zmieniona')
        self.assertEqual(self.user.avatar, 'fox')
        self.assertEqual(self.other.first_name, 'Jan')
        self.assertEqual(self.client.session[ACTIVE_WORKPLACE_SESSION_KEY], self.workspace.pk)

    def test_multipart_profile_crop_and_invalid_upload(self):
        self.client.force_login(self.user)
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        url = reverse('accounts-api') + '?url=' + reverse('profile')
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            response = self.client.post(url, self.profile_data(avatar='upload', profile_photo_crop='data:image/png;base64,' + base64.b64encode(png).decode()))
            self.assertEqual(response.status_code, 200)
            self.user.refresh_from_db()
            saved = self.user.profile_photo.name
            self.assertTrue(saved)
            response = self.client.post(url, self.profile_data(avatar='upload', profile_photo=SimpleUploadedFile('bad.png', b'bad', 'image/png')))
            self.assertEqual(response.status_code, 400)
            self.user.refresh_from_db()
            self.assertEqual(self.user.profile_photo.name, saved)

    def test_presence_status_uses_existing_validation(self):
        self.client.force_login(self.user)
        self.assertEqual(self.api('update_presence_status', {'presence_status': 'busy'}).status_code, 200)
        self.assertEqual(self.api('update_presence_status', {'presence_status': 'unknown'}).status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.presence_status, 'busy')

    def test_adding_switching_and_removing_current_account_preserves_proven_credentials(self):
        self.client.force_login(self.user)
        self.client.get(reverse('profile'))
        self.assertEqual(self.add().json(), {'redirect': reverse('profile')})
        self.assertEqual(self.client.session[SESSION_KEY], str(self.other.pk))
        self.assertEqual(len(self.api('profile').json()['data']['accounts']), 2)
        self.assertEqual(self.api('switch_account', {'user_id': self.user.pk}).status_code, 200)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.assertEqual(self.api('remove_account', {'user_id': self.user.pk}).status_code, 200)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.other.pk))
        self.assertEqual(self.client.session[SWITCH_ACCOUNTS_SESSION_KEY], [str(self.other.pk)])
        self.assertEqual(self.api('remove_account', {'user_id': self.other.pk}).status_code, 400)

    def test_password_change_invalidates_switch_and_cannot_remove_current_to_bypass_it(self):
        self.client.force_login(self.user)
        self.add()
        self.user.set_password('updated-frontend-password-84!'); self.user.save()
        self.assertEqual(self.api('switch_account', {'user_id': self.user.pk}).status_code, 403)
        self.assertEqual(self.api('remove_account', {'user_id': self.other.pk}).status_code, 400)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.other.pk))
        self.assertNotIn(str(self.user.pk), [a['id'] for a in self.api('profile').json()['data']['accounts']])

    def test_switcher_ids_without_authentication_hashes_never_grant_access(self):
        self.client.force_login(self.user)
        session = self.client.session
        session[SWITCH_ACCOUNTS_SESSION_KEY] = [str(self.user.pk), str(self.other.pk)]
        session.save()
        self.assertEqual(self.api('switch_account', {'user_id': self.other.pk}).status_code, 403)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_logout_clears_both_accounts_and_session(self):
        self.client.force_login(self.user)
        self.add()
        self.assertEqual(self.api('logout', {}).status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotIn(SWITCH_ACCOUNTS_HASHES_KEY, self.client.session)
        self.assertNotIn(SWITCH_ACCOUNTS_SESSION_KEY, self.client.session)
        self.assertEqual(self.api('profile').status_code, 401)
