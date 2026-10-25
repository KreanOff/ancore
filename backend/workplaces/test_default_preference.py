"""Personal Workspace defaults affect login without changing access or active work."""
import json
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from .models import Workplace, WorkplaceMembership, create_workplace_for_user
from .services import (
    ACTIVE_WORKPLACE_SESSION_KEY, WORKPLACE_URL_SCOPE_SESSION_KEY,
    default_workplace_for_user, ensure_default_workplace, scoped_workplace_app_path,
)


class DefaultWorkplacePreferenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'default-workspace-test-83!'
        cls.user = get_user_model().objects.create_user(username='default-user', email='default@example.test', password=cls.password)
        cls.other = get_user_model().objects.create_user(username='other-default', email='other-default@example.test', password=cls.password)
        cls.first = create_workplace_for_user(cls.user, 'A pierwszy Workspace')
        cls.second = create_workplace_for_user(cls.user, 'Z drugi Workspace')
        cls.shared = create_workplace_for_user(cls.other, 'Workspace współdzielony')
        cls.foreign = create_workplace_for_user(cls.other, 'Niedostępny Workspace')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.shared, user=cls.user, role='member')

    def setUp(self):
        self.client.force_login(self.user)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.first.pk
        session.save()

    def url(self, workplace, api=False, scoped=False):
        path = reverse('workplaces:set-default', args=[workplace.pk])
        if api:
            base = scoped_workplace_app_path(self.first, 'api', 'v1/page/') if scoped else reverse('react-page')
            return base + '?' + urlencode({'url': path})
        return path

    def choose(self, workplace, action='set', api=False, scoped=False, **extra):
        return self.client.post(self.url(workplace, api, scoped), {'action': action, **extra})

    def saved(self):
        self.user.refresh_from_db()
        return self.user.default_workplace_id

    def login(self, client=None, api=False):
        client = client or self.client
        body = {'username': self.user.email, 'password': self.password, 'next': '/workplaces/'}
        if api:
            return client.post(reverse('accounts-api') + '?' + urlencode({'url': reverse('login')}),
                               json.dumps(body), content_type='application/json')
        return client.post(reverse('login'), body)

    def test_html_set_change_remove_and_only_one_default_per_account(self):
        self.assertRedirects(self.choose(self.second, user_id=self.other.pk), reverse('workplaces:workplaces'))
        self.assertEqual(self.saved(), self.second.pk)
        self.assertIsNone(get_user_model().objects.get(pk=self.other.pk).default_workplace_id)
        self.assertEqual(self.client.session[ACTIVE_WORKPLACE_SESSION_KEY], self.first.pk)
        self.choose(self.shared)
        self.assertEqual(self.saved(), self.shared.pk)
        self.choose(self.second, 'remove')
        self.assertEqual(self.saved(), self.shared.pk)
        self.choose(self.shared, 'remove')
        self.assertIsNone(self.saved())

    def test_plain_and_scoped_api_report_default_without_switching_active_workspace(self):
        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                response = self.choose(self.second, api=True, scoped=scoped)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {'default_workplace_id': str(self.second.pk)})
                self.assertEqual(self.client.session[ACTIVE_WORKPLACE_SESSION_KEY], self.first.pk)
                self.assertIn('no-store', response['Cache-Control'])
                rows = self.client.get(reverse('react-page'), {'url': reverse('workplaces:workplaces')}, follow=True).json()['data']['rows']
                self.assertEqual([row['id'] for row in rows if row['is_default']], [str(self.second.pk)])
                self.assertTrue(all(row['default_url'] for row in rows))
                self.assertEqual(self.choose(self.second, 'remove', api=True, scoped=scoped).json(), {'default_workplace_id': None})

    def test_html_badge_and_actions_follow_persisted_preference(self):
        self.choose(self.second)
        response = self.client.get(reverse('workplaces:workplaces'))
        self.assertContains(response, 'Otwierany po zalogowaniu')
        self.assertContains(response, '>Domyślny</span>')
        self.assertContains(response, 'Ustaw jako domyślny')
        self.assertContains(response, 'Usuń ustawienie domyślne')

    def test_foreign_workspace_missing_auth_bad_action_and_csrf_are_rejected(self):
        for api in (False, True):
            with self.subTest(api=api):
                self.assertEqual(self.choose(self.foreign, api=api).status_code, 404)
                self.assertEqual(self.choose(self.second, 'bad', api=api).status_code, 400)
                self.assertEqual(self.client.get(self.url(self.second, api)).status_code, 405)
                csrf_client = Client(enforce_csrf_checks=True)
                csrf_client.force_login(self.user)
                self.assertEqual(csrf_client.post(self.url(self.second, api), {'action': 'set'}).status_code, 403)
                anonymous = Client().post(self.url(self.second, api), {'action': 'set'})
                self.assertEqual(anonymous.status_code, 401 if api else 302)
        self.assertIsNone(self.saved())

    def test_shared_workspace_defaults_are_personal_for_all_membership_roles(self):
        for role in ('admin', 'member', 'guest'):
            with self.subTest(role=role):
                self.membership.role = role
                self.membership.save(update_fields=['role'])
                self.assertEqual(self.choose(self.shared, api=True).status_code, 200)
                self.assertEqual(self.saved(), self.shared.pk)
                self.assertIsNone(get_user_model().objects.get(pk=self.other.pk).default_workplace_id)

    def test_login_uses_saved_default_across_sessions_and_overrides_active_session(self):
        self.choose(self.second)
        for api in (False, True):
            for fresh_session in (False, True):
                with self.subTest(api=api, fresh=fresh_session):
                    client = Client() if fresh_session else self.client
                    response = self.login(client, api)
                    target = scoped_workplace_app_path(self.second, 'for-you')
                    self.assertEqual(response.json()['redirect'] if api else response.url, target)
                    self.assertEqual(client.session[SESSION_KEY], str(self.user.pk))
                    self.assertEqual(client.session[ACTIVE_WORKPLACE_SESSION_KEY], self.second.pk)
                    self.assertTrue(client.session[WORKPLACE_URL_SCOPE_SESSION_KEY])
                    self.assertContains(client.get(target), self.second.name)
        self.client.post(reverse('workplaces:switch', args=[self.first.pk]))
        self.assertEqual(self.client.session[ACTIVE_WORKPLACE_SESSION_KEY], self.first.pk)
        self.assertEqual(self.saved(), self.second.pk)
        self.assertEqual(self.login().url, scoped_workplace_app_path(self.second, 'for-you'))

    def test_no_preference_preserves_existing_login_and_active_session_behavior(self):
        self.assertEqual(self.login().url, reverse('for_you'))
        self.assertEqual(self.client.session[ACTIVE_WORKPLACE_SESSION_KEY], self.first.pk)
        self.assertEqual(ensure_default_workplace(self.user), self.first)

    def test_lost_membership_and_invalid_saved_workspace_do_not_grant_access(self):
        self.choose(self.shared)
        for action in ('inactive', 'deleted', 'foreign'):
            with self.subTest(action=action):
                if action == 'inactive':
                    self.membership.is_active = False
                    self.membership.save(update_fields=['is_active'])
                elif action == 'deleted':
                    self.membership.delete()
                else:
                    get_user_model().objects.filter(pk=self.user.pk).update(default_workplace=self.foreign)
                self.user.refresh_from_db()
                self.assertIsNone(default_workplace_for_user(self.user))
                self.assertEqual(ensure_default_workplace(self.user), self.first)
                fresh = Client()
                response = self.login(fresh)
                self.assertEqual(response.url, reverse('for_you'))
                self.assertNotContains(fresh.get(response.url), self.foreign.name)
                self.assertEqual(fresh.session[ACTIVE_WORKPLACE_SESSION_KEY], self.first.pk)

    def test_deleting_default_workspace_clears_preference_without_deleting_account(self):
        self.choose(self.second)
        self.second.delete()
        self.assertIsNone(self.saved())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.assertEqual(self.login().url, reverse('for_you'))

    def test_missing_active_session_uses_preference_but_manual_switch_is_preserved(self):
        self.choose(self.second)
        fresh = Client(); fresh.force_login(self.user)
        response = fresh.get(reverse('for_you'))
        self.assertEqual(response.wsgi_request.workplace, self.second)
        fresh.post(reverse('workplaces:switch', args=[self.first.pk]))
        self.assertEqual(fresh.get(reverse('for_you'), follow=True).wsgi_request.workplace, self.first)

    def test_pending_invitation_keeps_its_login_flow(self):
        self.choose(self.second)
        target = '/workplaces/join/00000000-0000-0000-0000-000000000001/'
        with patch('workplaces.invitations.pending_join_url', return_value=target):
            self.assertEqual(self.login().url, target)

    def test_profile_form_cannot_change_preference_as_extra_field(self):
        self.choose(self.second)
        self.client.post(reverse('profile'), {
            'first_name': 'Anna', 'last_name': 'Nowak', 'email': self.user.email,
            'username': self.user.username, 'presence_status': 'busy',
            'default_workplace': self.foreign.pk,
        })
        self.assertEqual(self.saved(), self.second.pk)


class DefaultWorkplaceMigrationTests(TransactionTestCase):
    def test_upgrade_preserves_accounts_workspaces_and_starts_without_preference(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [('accounts', '0001_initial'), ('workplaces', '0004_workplaceinvitation_unique_pending_workspace_email')]
        executor.migrate(previous)
        try:
            apps = executor.loader.project_state(previous).apps
            user = apps.get_model('accounts', 'User').objects.create(username='existing-default', email='existing-default@example.test')
            workspace = apps.get_model('workplaces', 'Workplace').objects.create(owner=user, name='Istniejący Workspace', code='w_' + 'a' * 26, slug='w_' + 'a' * 26)
            identity = (workspace.pk, workspace.name, workspace.code, workspace.slug)
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            user = get_user_model().objects.get(pk=user.pk)
            workspace = Workplace.objects.get(pk=workspace.pk)
            self.assertIsNone(user.default_workplace_id)
            self.assertEqual((workspace.pk, workspace.name, workspace.code, workspace.slug), identity)
            user.default_workplace_id = workspace.pk
            user.save(update_fields=['default_workplace'])
            workspace.delete()
            user.refresh_from_db()
            self.assertIsNone(user.default_workplace_id)
        finally:
            MigrationExecutor(connection).migrate(latest)
