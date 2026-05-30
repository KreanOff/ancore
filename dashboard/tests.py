from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class DashboardViewTests(TestCase):
    def test_home_renders_for_authenticated_user(self):
        user = get_user_model().objects.create_user(
            username='dashboard-user',
            password='test-pass-123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
        self.assertContains(response, reverse('tasks:tasks'))
