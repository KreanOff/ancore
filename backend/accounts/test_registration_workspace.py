"""Explicit Workspace setup after registration, with atomic initialization."""
import json
from unittest.mock import patch

from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from dashboard.models import Dashboard
from workplaces.models import Workplace, WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class RegistrationWorkspaceTests(TestCase):
    password = 'registration-workspace-83!'

    def register(self, api=False):
        client = Client()
        email = f'new-{get_user_model().objects.count()}@example.test'
        target = reverse('register')
        url = reverse('accounts-api') + '?url=' + target if api else target
        response = client.post(url, {'first_name': 'Anna', 'last_name': 'Nowak', 'email': email,
                                    'password1': self.password, 'password2': self.password})
        self.assertEqual(response.status_code, 200 if api else 302)
        user = get_user_model().objects.get(email=email)
        self.assertEqual(client.session[SESSION_KEY], str(user.pk))
        self.assertFalse(Workplace.objects.filter(owner=user).exists())
        return client, user

    def step(self, client, values=None, api=False):
        url = reverse('register_workspace')
        if api:
            url = reverse('accounts-api') + '?url=' + url
        return client.get(url) if values is None else client.post(url, values)

    def picker(self, client, api=False):
        url = reverse('select_workspace')
        if api:
            url = reverse('accounts-api') + '?url=' + url
        return client.get(url)

    def test_account_is_authenticated_and_workspace_is_created_only_after_named_post(self):
        for api in (False, True):
            with self.subTest(api=api):
                client, user = self.register(api)
                response = self.step(client, api=api)
                self.assertEqual(response.status_code, 200)
                self.assertIn('no-store', response['Cache-Control'])
                if api:
                    field, = response.json()['data']['form']['fields']
                    self.assertTrue(field['required'])
                for name in ('', '   ', 'A' * 141):
                    response = self.step(client, {'name': name}, api)
                    self.assertEqual(response.status_code, 400 if api else 200)
                    self.assertFalse(Workplace.objects.filter(owner=user).exists())
                response = self.step(client, {'name': '  Zespół   Anny  ', 'owner': '999', 'code': 'forged'}, api)
                workspace = Workplace.objects.get(owner=user)
                self.assertEqual(workspace.name, 'Zespół Anny')
                self.assertRegex(workspace.code, r'^w_[a-z0-9]{26}$')
                self.assertEqual(workspace.memberships.get(user=user).role, 'owner')
                self.assertEqual(client.session['active_workplace_id'], workspace.pk)
                dashboard = Dashboard.objects.get(workplace=workspace, is_default=True)
                self.assertEqual(dashboard.gadgets.count(), 1)
                expected = scoped_workplace_app_path(workspace, 'for-you')
                self.assertEqual(response.json()['redirect'] if api else response.url, expected)
                self.step(client, {'name': 'Drugie kliknięcie'}, api)
                self.assertEqual(Workplace.objects.filter(owner=user).count(), 1)

    def test_existing_membership_skips_setup_without_creating_personal_workspace(self):
        from workplaces.models import WorkplaceMembership
        client, user = self.register()
        owner = get_user_model().objects.create_user(username='owner', email='owner@example.test')
        workspace = create_workplace_for_user(owner, 'Zespół')
        WorkplaceMembership.objects.create(workplace=workspace, user=user)
        response = self.step(client, {'name': 'Nie twórz'})
        self.assertEqual(response.url, scoped_workplace_app_path(workspace, 'for-you'))
        self.assertFalse(Workplace.objects.filter(owner=user).exists())

    def test_failed_initialization_rolls_back_workspace_but_keeps_account_for_retry(self):
        client, user = self.register()
        with patch('dashboard.models.DashboardGadget.objects.create', side_effect=RuntimeError('initialization')):
            with self.assertRaises(RuntimeError):
                self.step(client, {'name': 'Zespół'})
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
        self.assertFalse(Workplace.objects.filter(owner=user).exists())
        self.assertEqual(self.step(client, {'name': 'Ponowienie'}).status_code, 302)

    def test_requires_authentication_and_csrf(self):
        self.assertEqual(self.step(Client(), {'name': 'Nie twórz'}).status_code, 302)
        self.assertEqual(self.step(Client(), {'name': 'Nie twórz'}, True).status_code, 401)
        client, user = self.register()
        secure = Client(enforce_csrf_checks=True)
        secure.cookies = client.cookies
        self.assertEqual(self.step(secure, {'name': 'Nie twórz'}).status_code, 403)
        self.assertFalse(Workplace.objects.exists())

    def test_empty_workspace_picker_is_available_in_html_and_api(self):
        client, user = self.register()
        response = self.step(client)
        self.assertContains(response, 'Wybierz Workspace')
        self.assertContains(response, f'href="{reverse("select_workspace")}"')
        self.assertNotContains(response, 'Brak dostępnych Workspace.')
        self.assertNotContains(response, 'name="create_another"')
        self.assertNotIn('workspaces', self.step(client, api=True).json()['data'])
        response = self.picker(client)
        self.assertTemplateUsed(response, 'accounts/select_workspace.html')
        self.assertContains(response, 'Brak dostępnych Workspace.')
        self.assertNotContains(response, 'name="name"')
        self.assertIn('no-store', response['Cache-Control'])
        payload = self.picker(client, api=True)
        self.assertEqual(payload.json()['type'], 'account-workspace-picker')
        self.assertEqual(payload.json()['data']['workspaces'], [])
        self.assertEqual(payload['Cache-Control'], 'no-store')
        self.assertFalse(Workplace.objects.filter(owner=user).exists())

    def test_picker_requires_authentication_and_does_not_accept_post(self):
        self.assertEqual(self.picker(Client()).status_code, 302)
        self.assertEqual(self.picker(Client(), api=True).status_code, 401)
        client, user = self.register()
        target = reverse('select_workspace')
        for url in (target, reverse('accounts-api') + '?url=' + target):
            self.assertEqual(client.post(url).status_code, 405)
        self.assertFalse(Workplace.objects.filter(owner=user).exists())

    def test_picker_exposes_only_owned_and_active_memberships_and_uses_existing_switch(self):
        client, user = self.register()
        owned = create_workplace_for_user(user, 'Własny <Workspace>')
        owner = get_user_model().objects.create_user(username='picker-owner', email='picker-owner@example.test')
        member = create_workplace_for_user(owner, 'Workspace członka')
        guest = create_workplace_for_user(owner, 'Workspace gościa')
        inactive = create_workplace_for_user(owner, 'Nieaktywny Workspace')
        foreign = create_workplace_for_user(owner, 'Obcy Workspace')
        WorkplaceMembership.objects.create(workplace=member, user=user, role='member')
        WorkplaceMembership.objects.create(workplace=guest, user=user, role='guest')
        WorkplaceMembership.objects.create(workplace=inactive, user=user, role='member', is_active=False)
        session = client.session
        session['active_workplace_id'] = owned.pk
        session.save()

        response = self.picker(client)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Własny &lt;Workspace&gt;')
        self.assertContains(response, 'Workspace członka')
        self.assertContains(response, 'Workspace gościa')
        for excluded in (inactive, foreign):
            self.assertNotContains(response, excluded.name)
        choices = self.picker(client, api=True).json()['data']['workspaces']
        self.assertEqual({item['id'] for item in choices}, {str(item.pk) for item in (owned, member, guest)})
        for choice in choices:
            self.assertEqual(choice['switch_url'], reverse('workplaces:switch', args=[choice['id']]))
        self.assertEqual(client.session['active_workplace_id'], owned.pk)

        target = reverse('workplaces:switch', args=[guest.pk])
        self.assertEqual(client.get(target).status_code, 405)
        secure = Client(enforce_csrf_checks=True)
        secure.cookies = client.cookies
        self.assertEqual(secure.post(target).status_code, 403)
        response = client.post(target)
        self.assertEqual(response.url, scoped_workplace_app_path(guest, 'for-you'))
        self.assertEqual(client.session['active_workplace_id'], guest.pk)
        self.assertEqual(client.post(reverse('workplaces:switch', args=[foreign.pk])).status_code, 404)
        WorkplaceMembership.objects.filter(workplace=guest, user=user).update(is_active=False)
        self.assertEqual(client.post(target).status_code, 404)
        self.assertNotIn(str(guest.pk), {item['id'] for item in self.picker(client, api=True).json()['data']['workspaces']})

    def test_member_can_explicitly_create_another_workspace_from_creation_form(self):
        for api in (False, True):
            with self.subTest(api=api):
                client, user = self.register(api)
                create_workplace_for_user(user, 'Pierwszy Workspace')
                response = self.step(client, {'name': '', 'create_another': '1'}, api)
                self.assertEqual(response.status_code, 400 if api else 200)
                if api:
                    self.assertTrue(response.json()['data']['has_workspaces'])
                else:
                    self.assertNotContains(response, 'Pierwszy Workspace')
                    self.assertContains(response, 'name="create_another"')
                response = self.step(client, {'name': 'Kolejny Workspace', 'create_another': '1'}, api)
                created = Workplace.objects.get(owner=user, name='Kolejny Workspace')
                expected = scoped_workplace_app_path(created, 'for-you')
                self.assertEqual(response.json()['redirect'] if api else response.url, expected)
                self.assertEqual(client.session['active_workplace_id'], created.pk)
                self.assertEqual(Workplace.objects.filter(owner=user).count(), 2)
