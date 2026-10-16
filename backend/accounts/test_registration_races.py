"""Concurrent registrations keep generated IDs unique without losing an account."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse

from . import forms


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class RegistrationRaceTests(TransactionTestCase):
    def test_same_names_can_register_concurrently_through_html_and_api(self):
        barrier = Barrier(2)
        original = forms.unique_public_username

        def concurrent_username(*args, **kwargs):
            candidate = original(*args, **kwargs)
            if candidate == '@anna.nowak':
                barrier.wait(timeout=10)
            return candidate

        def register(index):
            close_old_connections()
            try:
                path = reverse('register') if index == 1 else reverse('accounts-api') + '?url=' + reverse('register')
                return Client().post(path, {
                    'first_name': 'Anna', 'last_name': 'Nowak', 'email': f'registration-{index}@example.test',
                    'password1': 'Unrelated-83-long!', 'password2': 'Unrelated-83-long!',
                })
            finally:
                close_old_connections()

        with patch.object(forms, 'unique_public_username', concurrent_username):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(register, index) for index in (1, 2)]
                html, api = [future.result(timeout=20) for future in futures]
        self.assertEqual(html.status_code, 302, html.content)
        self.assertEqual(api.status_code, 200, api.content)
        self.assertEqual(api.json()['redirect'], reverse('login'))
        users = list(get_user_model().objects.order_by('email'))
        self.assertEqual({user.username for user in users}, {'@anna.nowak', '@anna.nowak2'})
        self.assertEqual(len(users), 2)
        self.assertTrue(all(user.check_password('Unrelated-83-long!') for user in users))
