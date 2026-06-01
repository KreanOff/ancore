from django.contrib.auth import SESSION_KEY
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .views import SWITCH_ACCOUNTS_SESSION_KEY


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='anna@example.com',
            email='anna@example.com',
            first_name='Anna',
            last_name='Kowalska',
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
        self.assertContains(response, 'Aktywny')

    def test_profile_updates_user_data(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('profile'), {
            'first_name': 'Jan',
            'last_name': 'Nowak',
            'email': 'jan@example.com',
            'presence_status': 'out_of_office',
        })

        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jan')
        self.assertEqual(self.user.last_name, 'Nowak')
        self.assertEqual(self.user.email, 'jan@example.com')
        self.assertEqual(self.user.username, 'jan@example.com')
        self.assertEqual(self.user.presence_status, 'out_of_office')

    def test_profile_rejects_duplicate_email(self):
        get_user_model().objects.create_user(
            username='ewa@example.com',
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
            'presence_status': 'active',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ten adres email jest już używany.')


class AccountSwitcherTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='anna@example.com',
            email='anna@example.com',
            first_name='Anna',
            last_name='Kowalska',
            password='testpass123',
        )
        self.second_user = user_model.objects.create_user(
            username='ewa@example.com',
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
            username='jan@example.com',
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
