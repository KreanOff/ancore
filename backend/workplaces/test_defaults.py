"""Selecting a Workspace must never silently create one."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse
from .models import Workplace, WorkplaceMembership, create_workplace_for_user
from .services import ensure_default_workplace


class DefaultWorkplaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='setup', email='setup@example.test', password='testpass123')

    def test_first_login_requires_explicit_setup_and_does_not_create_workspace(self):
        response = self.client.post(reverse('login'), {'username': self.user.email, 'password': 'testpass123'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register_workspace.html')
        self.assertFalse(Workplace.objects.exists())
        self.client.get(reverse('for_you'))
        self.assertFalse(Workplace.objects.exists())

    def test_existing_membership_is_selected_without_creating_workspace(self):
        owner = get_user_model().objects.create_user(username='owner', email='owner@example.test')
        workspace = create_workplace_for_user(owner, 'Wspólny Workspace')
        WorkplaceMembership.objects.create(workplace=workspace, user=self.user, role='guest')
        self.assertEqual(ensure_default_workplace(self.user), workspace)
        self.assertEqual(Workplace.objects.count(), 1)

    def test_anonymous_or_empty_account_has_no_default(self):
        self.assertIsNone(ensure_default_workplace(AnonymousUser()))
        self.assertIsNone(ensure_default_workplace(self.user))
        self.assertFalse(Workplace.objects.exists())
