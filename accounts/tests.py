import base64
import os
import tempfile

from django.contrib.auth import SESSION_KEY
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import UserRegistrationForm
from .views import SWITCH_ACCOUNTS_SESSION_KEY, _account_avatar


class UserRegistrationFormTests(TestCase):
    def test_registration_generates_public_username_from_name(self):
        form = UserRegistrationForm(data={
            'first_name': 'Anna',
            'last_name': 'Kowalska',
            'email': 'anna@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertEqual(user.username, '@anna.kowalska')

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


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='@anna.kowalska',
            email='anna@example.com',
            first_name='Anna',
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
        self.assertContains(response, 'Anna Kowalska')
        self.assertContains(response, 'anna@example.com')
        self.assertContains(response, '@anna.kowalska')
        self.assertContains(response, '+48 500 600 700')
        self.assertContains(response, 'Product Manager')
        self.assertContains(response, 'Zajmuje sie wdrozeniami i komunikacja z klientami.')
        self.assertContains(response, 'Aktywny')
        self.assertContains(response, 'icon-tabler-user-square')

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
        self.assertEqual(self.user.last_name, 'Nowak')
        self.assertEqual(self.user.email, 'jan@example.com')
        self.assertEqual(self.user.username, '@jan.nowak')
        self.assertEqual(self.user.phone_number, '+48 111 222 333')
        self.assertEqual(self.user.job_title, 'Koordynator')
        self.assertEqual(self.user.bio, 'Odpowiada za kontakt z zespolem.')
        self.assertEqual(self.user.presence_status, 'out_of_office')

    def test_profile_saves_cropped_profile_photo(self):
        self.client.force_login(self.user)
        image_content = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII='
        )
        crop_data = f'data:image/png;base64,{base64.b64encode(image_content).decode()}'

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse('profile'), {
                'first_name': 'Anna',
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
        self.assertContains(response, 'Ten login jest już zajęty.')


class AccountSwitcherTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='@anna.kowalska',
            email='anna@example.com',
            first_name='Anna',
            last_name='Kowalska',
            password='testpass123',
        )
        self.second_user = user_model.objects.create_user(
            username='@ewa.zielinska',
            email='ewa@example.com',
            first_name='Ewa',
            last_name='Zielinska',
            password='testpass123',
        )

    def _seed_switcher_session(self):
        self.client.force_login(self.user)
        session = self.client.session
        session[SWITCH_ACCOUNTS_SESSION_KEY] = [str(self.user.pk), str(self.second_user.pk)]
        session.save()

    def test_add_account_requires_login(self):
        response = self.client.get(reverse('add_account'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_add_account_with_valid_credentials_switches_to_added_account(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('add_account'), {
            'username': 'ewa@example.com',
            'password': 'testpass123',
        })

        self.assertRedirects(response, reverse('profile'))
        session = self.client.session
        self.assertEqual(session[SESSION_KEY], str(self.second_user.pk))
        self.assertEqual(
            session[SWITCH_ACCOUNTS_SESSION_KEY],
            [str(self.second_user.pk), str(self.user.pk)],
        )

    def test_switch_account_changes_authenticated_user(self):
        self._seed_switcher_session()

        response = self.client.post(reverse('switch_account'), {
            'user_id': self.second_user.pk,
        })

        self.assertRedirects(response, reverse('profile'))
        self.assertEqual(self.client.session[SESSION_KEY], str(self.second_user.pk))

    def test_switch_account_rejects_account_not_in_switcher(self):
        third_user = get_user_model().objects.create_user(
            username='@jan.nowak',
            email='jan@example.com',
            first_name='Jan',
            last_name='Nowak',
            password='testpass123',
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('switch_account'), {
            'user_id': third_user.pk,
        })

        self.assertRedirects(response, reverse('profile'))
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_remove_non_current_account_removes_it_from_switcher(self):
        self._seed_switcher_session()

        response = self.client.post(reverse('remove_account'), {
            'user_id': self.second_user.pk,
        })

        self.assertRedirects(response, reverse('profile'))
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.assertEqual(self.client.session[SWITCH_ACCOUNTS_SESSION_KEY], [str(self.user.pk)])
        self.assertTrue(get_user_model().objects.filter(pk=self.second_user.pk).exists())

    def test_remove_current_account_switches_to_remaining_account(self):
        self._seed_switcher_session()

        response = self.client.post(reverse('remove_account'), {
            'user_id': self.user.pk,
        })

        self.assertRedirects(response, reverse('profile'))
        self.assertEqual(self.client.session[SESSION_KEY], str(self.second_user.pk))
        self.assertEqual(self.client.session[SWITCH_ACCOUNTS_SESSION_KEY], [str(self.second_user.pk)])
