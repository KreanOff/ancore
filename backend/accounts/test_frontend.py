import base64
import json
import tempfile

from django.contrib.auth import SESSION_KEY, get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from workplaces.models import create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, WORKPLACE_URL_SCOPE_SESSION_KEY


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
        for name in ('profile', 'select_workspace', 'update_profile_banner', 'update_presence_status', 'logout'):
            for body in (None, {}):
                with self.subTest(name=name, body=body):
                    self.assertEqual(self.api(name, body).status_code, 401)

    def test_methods_and_json_shape_are_checked(self):
        self.client.force_login(self.user)
        for name in ('update_profile_banner', 'update_presence_status', 'logout'):
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

    def test_registration_validates_then_authenticates_for_workspace_setup(self):
        payload = {'first_name': 'Ewa', 'last_name': 'Testowa', 'email': 'ewa.frontend@example.test',
                   'password1': self.password, 'password2': 'mismatch-never-echo'}
        response = self.api('register', payload)
        self.assertEqual(response.status_code, 400)
        self.assertNotContains(response, self.password, status_code=400)
        self.assertNotContains(response, payload['password2'], status_code=400)
        self.assertTrue(next(f for f in response.json()['data']['form']['fields'] if f['name'] == 'password2')['errors'])
        payload['password2'] = self.password
        self.assertEqual(self.api('register', payload).json(), {'redirect': reverse('register_workspace')})
        created = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(created.check_password(self.password))
        self.assertEqual(self.client.session[SESSION_KEY], str(created.pk))
        self.client.logout()
        payload['email'] = payload['email'].upper()
        self.assertEqual(self.api('register', payload).status_code, 400)

    def test_csrf_is_required_for_public_and_private_operations(self):
        client = Client(enforce_csrf_checks=True)
        for name in ('login', 'register', 'register_workspace'):
            response = self.api(name, {}, client=client)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response['Content-Type'], 'application/json')
        client.force_login(self.user)
        for name in ('profile', 'update_profile_banner', 'update_presence_status', 'logout'):
            self.assertEqual(self.api(name, {}, client=client).status_code, 403)
        client.get(reverse('profile'))
        token = client.cookies['csrftoken'].value
        self.assertEqual(self.api('profile', self.profile_data(), client=client, HTTP_X_CSRFTOKEN=token).status_code, 200)

    def test_profile_only_exposes_current_identity_without_saved_accounts(self):
        self.client.force_login(self.user)
        response = self.api('profile')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['user']['email'], self.user.email)
        self.assertNotIn('accounts', data)
        self.assertEqual(set(data['urls']), {'profile', 'update_profile_banner', 'update_presence_status', 'logout'})
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

    def test_selecting_active_clears_manual_status_in_api_and_html(self):
        self.client.force_login(self.user)
        for manual_status in ('busy', 'out_of_office', 'do_not_disturb'):
            for api in (True, False):
                with self.subTest(manual_status=manual_status, api=api):
                    self.user.presence_status = manual_status
                    self.user.save(update_fields=['presence_status'])
                    payload = {'presence_status': 'active'}
                    if api:
                        response = self.api('update_presence_status', payload)
                        self.assertEqual(response.json(), {'redirect': reverse('profile')})
                    else:
                        response = self.client.post(reverse('update_presence_status'), payload)
                        self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)
                    self.user.refresh_from_db()
                    self.assertEqual(self.user.presence_status, 'active')

    def test_retired_account_api_targets_return_404_without_changing_identity(self):
        for authenticated in (False, True):
            if authenticated:
                self.client.force_login(self.user)
            for action in ('add-account', 'switch-account', 'remove-account'):
                for method in ('get', 'post'):
                    with self.subTest(authenticated=authenticated, action=action, method=method):
                        url = reverse('accounts-api') + f'?url=/accounts/profile/{action}/'
                        response = self.client.get(url) if method == 'get' else self.client.post(url, {'user_id': self.other.pk})
                        self.assertEqual(response.status_code, 404)
                        self.assertEqual(response['Cache-Control'], 'no-store')
                        self.assertEqual(self.client.session.get(SESSION_KEY), str(self.user.pk) if authenticated else None)

    def test_logged_in_auth_api_cannot_replace_identity_or_create_second_account(self):
        self.client.force_login(self.user)
        before = get_user_model().objects.count()
        for route, body in (
            ('login', {'username': self.other.email, 'password': self.password}),
            ('register', {'first_name': 'Ewa', 'last_name': 'Testowa', 'email': 'new.frontend@example.test',
                          'password1': self.password, 'password2': self.password}),
        ):
            for payload in (None, body):
                with self.subTest(route=route, payload=payload):
                    response = self.api(route, payload)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('redirect', response.json())
                    self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
                    self.assertEqual(get_user_model().objects.count(), before)

    def test_logout_then_login_changes_account_without_old_workspace_or_credentials(self):
        self.client.force_login(self.user)
        self.client.get(reverse('profile'))
        session = self.client.session
        session['switch_account_user_ids'] = [str(self.user.pk), str(self.other.pk)]
        session['switch_account_auth_hashes'] = {
            str(user.pk): user.get_session_auth_hash() for user in (self.user, self.other)
        }
        session.save()
        self.assertEqual(self.api('logout', {}).status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotIn(ACTIVE_WORKPLACE_SESSION_KEY, self.client.session)
        self.assertNotIn('switch_account_user_ids', self.client.session)
        self.assertNotIn('switch_account_auth_hashes', self.client.session)
        self.assertEqual(self.api('profile').status_code, 401)
        response = self.api('login', {'username': self.other.email, 'password': self.password})
        self.assertEqual(response.json(), {'redirect': reverse('register_workspace')})
        self.assertEqual(self.client.session[SESSION_KEY], str(self.other.pk))
        self.assertNotIn(ACTIVE_WORKPLACE_SESSION_KEY, self.client.session)
