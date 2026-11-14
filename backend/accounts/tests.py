import base64
import json
import os
import tempfile
from datetime import timedelta

from django.contrib.auth import SESSION_KEY
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import UserRegistrationForm
from .presence import sync_stale_presence_statuses
from .views import _account_avatar


class UserRegistrationFormTests(TestCase):
    def test_registration_generates_public_username_from_name(self):
        form = UserRegistrationForm(data={
            'first_name': 'Anna',
            'middle_name': 'Maria',
            'last_name': 'Kowalska',
            'email': 'anna@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertEqual(user.username, '@anna.kowalska')
        self.assertEqual(user.middle_name, 'Maria')
        self.assertEqual(user.get_full_name(), 'Anna Maria Kowalska')

    def test_registration_generates_unique_public_username(self):
        get_user_model().objects.create_user(
            username='@anna.kowalska',
            email='existing@example.com',
            first_name='Anna',
            last_name='Kowalska',
            password='testpass123',
        )
        form = UserRegistrationForm(data={
            'first_name': 'Anna',
            'last_name': 'Kowalska',
            'email': 'anna@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertEqual(user.username, '@anna.kowalska2')


class AuthPageViewTests(TestCase):
    def test_login_page_uses_wallpaper_auth_layout(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="auth-tabs"')
        self.assertContains(response, 'aria-current="page">Logowanie</a>')
        self.assertContains(response, 'Zaloguj się')
        self.assertContains(response, 'data-password-toggle')
        self.assertContains(response, 'class="auth-page auth-page--login auth-page--wallpaper"')
        self.assertNotContains(response, 'Wróć do strony głównej')

    def test_registration_pairs_names_and_keeps_optional_middle_name(self):
        response = self.client.get(reverse('register'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="auth-field-row auth-field-row--names"')
        self.assertContains(response, 'Utwórz konto')
        self.assertContains(response, 'aria-current="page">Rejestracja</a>')
        self.assertContains(response, '>Drugie imię (opcjonalnie)</label>')

        content = response.content.decode()
        names_row_start = content.index('auth-field-row auth-field-row--names')
        email_field_start = content.index('for="email"', names_row_start)
        names_row = content[names_row_start:email_field_start]
        self.assertLess(names_row.index('id="first-name"'), names_row.index('id="last-name"'))
        self.assertLess(names_row.index('id="last-name"'), names_row.index('id="middle-name"'))


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='@anna.kowalska',
            email='anna@example.com',
            first_name='Anna',
            middle_name='Maria',
            last_name='Kowalska',
            phone_number='+48 500 600 700',
            job_title='Product Manager',
            bio='Zajmuje sie wdrozeniami i komunikacja z klientami.',
            password='testpass123',
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_profile_displays_current_user_data(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Anna Maria Kowalska')
        self.assertContains(response, 'anna@example.com')
        self.assertContains(response, '@anna.kowalska')
        self.assertContains(response, '+48 500 600 700')
        self.assertContains(response, 'Product Manager')
        self.assertContains(response, 'Zajmuje sie wdrozeniami i komunikacja z klientami.')
        self.assertContains(response, 'Aktywny')
        self.assertContains(response, 'class="profile-avatar-icon" data-icon="user-round"')
        self.assertContains(response, _account_avatar(self.user)['preset_class'])
        self.assertContains(response, 'profile-avatar--user')
        content = response.content.decode()
        self.assertNotIn('<h2>Sesja</h2>', content)
        self.assertNotIn('<span>Konta</span>', content)
        self.assertNotIn('<span>Aktywne</span>', content)
        self.assertNotIn('<h2>Akcje</h2>', content)
        self.assertNotIn('class="tasks-issue-icon-button" aria-label="Administracja"', content)
        self.assertContains(response, '<button type="button" class="tasks-filter-button" data-profile-edit-open>'
                            '<i data-icon="pencil" aria-hidden="true"></i>Edytuj profil</button>', html=True)
        for title in ('O mnie', 'Dane kontaktowe', 'Konto i aktywność'):
            self.assertContains(response, title)
        self.assertNotIn('data-profile-actions-toggle', content)
        self.assertNotIn("Konta w sesji", content)
        self.assertNotIn("Dodaj konto", content)
        self.assertIn(f'action="{reverse("update_presence_status")}"', content)
        self.assertIn('data-profile-status-form', content)
        self.assertIn('data-profile-photo-editor', content)
        self.assertIn('data-profile-photo-modal', content)
        self.assertIn('data-workplace-avatar-open', content)
        self.assertIn('data-profile-photo-remove', content)
        self.assertIn('data-profile-photo-change', content)
        self.assertIn('data-profile-photo-save', content)
        self.assertIn('data-profile-photo-remove-input', content)
        self.assertIn(
            'class="profile-avatar profile-page-avatar profile-avatar--user ',
            content,
        )

    def test_account_avatar_uses_user_specific_background_color(self):
        other_user = get_user_model().objects.create_user(
            username='@jan.nowak',
            email='jan@example.com',
            first_name='Jan',
            last_name='Nowak',
            password='testpass123',
        )

        avatar = _account_avatar(self.user)
        other_avatar = _account_avatar(other_user)

        self.assertEqual(avatar['background_color'], _account_avatar(self.user)['background_color'])
        self.assertNotEqual(avatar['background_color'], other_avatar['background_color'])
        self.assertIn('--profile-avatar-bg:', avatar['color_style'])

    def test_profile_updates_user_data(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('profile'), {
            'first_name': 'Jan',
            'middle_name': 'Piotr',
            'last_name': 'Nowak',
            'email': 'jan@example.com',
            'username': '@jan.nowak',
            'phone_number': '+48 111 222 333',
            'job_title': 'Koordynator',
            'bio': 'Odpowiada za kontakt z zespolem.',
            'presence_status': 'out_of_office',
        })

        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jan')
        self.assertEqual(self.user.middle_name, 'Piotr')
        self.assertEqual(self.user.last_name, 'Nowak')
        self.assertEqual(self.user.get_full_name(), 'Jan Piotr Nowak')
        self.assertEqual(self.user.email, 'jan@example.com')
        self.assertEqual(self.user.username, '@jan.nowak')
        self.assertEqual(self.user.phone_number, '+48 111 222 333')
        self.assertEqual(self.user.job_title, 'Koordynator')
        self.assertEqual(self.user.bio, 'Odpowiada za kontakt z zespolem.')
        self.assertEqual(self.user.presence_status, 'out_of_office')

    def test_profile_status_inline_updates_presence_status(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('update_presence_status'), {
            'presence_status': 'busy',
        })

        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.presence_status, get_user_model().PresenceStatus.BUSY)

    def test_profile_status_inline_rejects_invalid_status(self):
        self.user.presence_status = get_user_model().PresenceStatus.OUT_OF_OFFICE
        self.user.save(update_fields=['presence_status'])
        self.client.force_login(self.user)

        response = self.client.post(reverse('update_presence_status'), {
            'presence_status': 'unknown',
        })

        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.presence_status, get_user_model().PresenceStatus.OUT_OF_OFFICE)

    def test_profile_saves_cropped_profile_photo(self):
        self.client.force_login(self.user)
        image_content = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII='
        )
        crop_data = f'data:image/png;base64,{base64.b64encode(image_content).decode()}'

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse('profile'), {
                'first_name': 'Anna',
                'middle_name': 'Maria',
                'last_name': 'Kowalska',
                'email': 'anna@example.com',
                'username': '@anna.kowalska',
                'phone_number': '+48 500 600 700',
                'job_title': 'Product Manager',
                'bio': 'Zajmuje sie wdrozeniami i komunikacja z klientami.',
                'presence_status': 'active',
                'profile_photo_crop': crop_data,
            })

            self.assertRedirects(response, reverse('profile'))
            self.user.refresh_from_db()
            self.assertTrue(self.user.profile_photo.name.startswith('profile_photos/profile_'))
            self.assertTrue(os.path.exists(self.user.profile_photo.path))
            with open(self.user.profile_photo.path, 'rb') as photo_file:
                self.assertEqual(photo_file.read(), image_content)

            response = self.client.get(reverse('profile'))
            self.assertContains(response, f'data-profile-photo-url="{self.user.profile_photo.url}"')
            self.assertContains(response, 'Edytuj zdjęcie użytkownika')

            response = self.client.post(reverse('profile'), {
                'first_name': 'Anna',
                'middle_name': 'Maria',
                'last_name': 'Kowalska',
                'email': 'anna@example.com',
                'username': '@anna.kowalska',
                'phone_number': '+48 500 600 700',
                'job_title': 'Product Manager',
                'bio': 'Zajmuje sie wdrozeniami i komunikacja z klientami.',
                'presence_status': 'active',
                'profile_photo_remove': '1',
            })

            self.assertRedirects(response, reverse('profile'))
            self.user.refresh_from_db()
            self.assertFalse(self.user.profile_photo)

    def test_profile_rejects_duplicate_email(self):
        get_user_model().objects.create_user(
            username='@ewa.zielinska',
            email='ewa@example.com',
            first_name='Ewa',
            last_name='Zielinska',
            password='testpass123',
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('profile'), {
            'first_name': 'Anna',
            'last_name': 'Kowalska',
            'email': 'ewa@example.com',
            'username': '@anna.kowalska',
            'presence_status': 'active',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ten adres email jest już używany.')

    def test_profile_rejects_duplicate_public_username(self):
        get_user_model().objects.create_user(
            username='@ewa.zielinska',
            email='ewa@example.com',
            first_name='Ewa',
            last_name='Zielinska',
            password='testpass123',
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('profile'), {
            'first_name': 'Anna',
            'last_name': 'Kowalska',
            'email': 'anna@example.com',
            'username': '@ewa.zielinska',
            'presence_status': 'active',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'To ID Ancore jest już zajęte.')

    def test_presence_ping_marks_auto_status_active(self):
        self.user.presence_status = get_user_model().PresenceStatus.INACTIVE
        self.user.save(update_fields=['presence_status'])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('presence_ping'),
            json.dumps({'active': True}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.presence_status, get_user_model().PresenceStatus.ACTIVE)
        self.assertIsNotNone(self.user.last_seen_at)

    def test_presence_ping_marks_auto_status_inactive(self):
        self.user.presence_status = get_user_model().PresenceStatus.ACTIVE
        self.user.last_seen_at = timezone.now()
        self.user.save(update_fields=['presence_status', 'last_seen_at'])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('presence_ping'),
            json.dumps({'active': False}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.presence_status, get_user_model().PresenceStatus.INACTIVE)

    def test_presence_heartbeat_does_not_override_manual_status(self):
        self.user.presence_status = get_user_model().PresenceStatus.BUSY
        self.user.save(update_fields=['presence_status'])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('presence_ping'),
            json.dumps({'active': True}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.presence_status, get_user_model().PresenceStatus.BUSY)
        self.assertIsNotNone(self.user.last_seen_at)

    @override_settings(USER_PRESENCE_IDLE_SECONDS=60)
    def test_stale_active_presence_becomes_inactive(self):
        self.user.presence_status = get_user_model().PresenceStatus.ACTIVE
        self.user.last_seen_at = timezone.now() - timedelta(minutes=5)
        self.user.save(update_fields=['presence_status', 'last_seen_at'])

        updated_count = sync_stale_presence_statuses()

        self.assertEqual(updated_count, 1)
        self.user.refresh_from_db()
        self.assertEqual(self.user.presence_status, get_user_model().PresenceStatus.INACTIVE)


class SingleAccountSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'single-account-test-83!'
        cls.user = get_user_model().objects.create_user(
            username='@anna.single', email='anna.single@example.test', password=cls.password,
        )
        cls.other = get_user_model().objects.create_user(
            username='@ewa.single', email='ewa.single@example.test', password=cls.password,
        )

    def seed_legacy_session(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['switch_account_user_ids'] = [str(self.user.pk), str(self.other.pk)]
        session['switch_account_auth_hashes'] = {
            str(user.pk): user.get_session_auth_hash() for user in (self.user, self.other)
        }
        session['unrelated_preference'] = 'preserved'
        session.save()
        return session.session_key

    def test_old_session_credentials_are_discarded_without_logging_out_current_user(self):
        session_key = self.seed_legacy_session()
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session.session_key, session_key)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.assertEqual(self.client.session['unrelated_preference'], 'preserved')
        self.assertNotIn('switch_account_user_ids', self.client.session)
        self.assertNotIn('switch_account_auth_hashes', self.client.session)
        self.assertNotContains(response, self.other.email)

    def test_anonymous_legacy_credentials_cannot_restore_a_login(self):
        session = self.client.session
        session['switch_account_user_ids'] = [str(self.user.pk)]
        session['switch_account_auth_hashes'] = {str(self.user.pk): self.user.get_session_auth_hash()}
        session.save()
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotIn('switch_account_user_ids', self.client.session)
        self.assertNotIn('switch_account_auth_hashes', self.client.session)

    def test_retired_routes_cannot_change_identity(self):
        for authenticated in (False, True):
            if authenticated:
                self.seed_legacy_session()
            for action in ('add-account', 'switch-account', 'remove-account'):
                for method in ('get', 'post'):
                    with self.subTest(authenticated=authenticated, action=action, method=method):
                        response = getattr(self.client, method)(f'/accounts/profile/{action}/', {
                            'user_id': self.other.pk, 'username': self.other.email, 'password': self.password,
                        })
                        self.assertEqual(response.status_code, 404)
                        self.assertEqual(self.client.session.get(SESSION_KEY), str(self.user.pk) if authenticated else None)

    def test_login_requires_logout_before_changing_identity(self):
        self.client.force_login(self.user)
        for method in ('get', 'post'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(reverse('login'), {
                    'username': self.other.email, 'password': self.password,
                })
                self.assertRedirects(response, reverse('select_workspace'), fetch_redirect_response=False)
                self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.client.post(reverse('logout'))
        self.assertNotIn(SESSION_KEY, self.client.session)
        response = self.client.post(reverse('login'), {'username': self.other.email, 'password': self.password})
        self.assertRedirects(response, reverse('select_workspace'), fetch_redirect_response=False)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.other.pk))

    def test_authenticated_registration_does_not_create_or_log_in_another_account(self):
        self.client.force_login(self.user)
        for method in ('get', 'post'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(reverse('register'), {
                    'first_name': 'Jan', 'last_name': 'Testowy', 'email': 'new.single@example.test',
                    'password1': self.password, 'password2': self.password,
                })
                self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)
                self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
                self.assertFalse(get_user_model().objects.filter(email='new.single@example.test').exists())

    def test_logout_does_not_restore_a_saved_account_or_affect_other_browser_sessions(self):
        self.seed_legacy_session()
        other_browser = Client()
        other_browser.force_login(self.user)
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotIn('switch_account_user_ids', self.client.session)
        self.assertNotIn('switch_account_auth_hashes', self.client.session)
        self.assertEqual(other_browser.get(reverse('profile')).status_code, 200)
        self.assertEqual(other_browser.session[SESSION_KEY], str(self.user.pk))
