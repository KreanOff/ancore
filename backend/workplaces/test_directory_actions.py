"""Directory actions use the selected Workspace's role, independently of the active one."""
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from spaces.models import Space, SpaceTask
from spaces.testing import make_space
from .models import Workplace, WorkplaceMembership, create_workplace_for_user
from .services import scoped_workplace_app_path, workplace_management_url


class WorkspaceDirectoryActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='actions-owner', email='workspace-actions@example.test')
        cls.other = users.objects.create_user(username='actions-other', email='workspace-other@example.test')
        cls.first = create_workplace_for_user(cls.owner, 'Pierwszy Workspace')
        cls.second = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        cls.shared = {}
        for role in ('admin', 'member', 'guest'):
            workspace = create_workplace_for_user(cls.other, f'Wspólny {role}')
            WorkplaceMembership.objects.create(workplace=workspace, user=cls.owner, role=role)
            cls.shared[role] = workspace
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy Workspace')

    def setUp(self):
        self.client.force_login(self.owner)
        self.activate(self.first)

    def activate(self, workspace, client=None):
        session = (client or self.client).session
        session['active_workplace_id'] = workspace.pk
        session.save()

    def delete_url(self, workspace=None):
        return reverse('workplaces:delete', args=[(workspace or self.first).pk])

    def api(self, target, values=None, *, workspace=None, navigation=False, client=None):
        kind = 'navigation' if navigation else 'page'
        client = client or self.client
        workspace = workspace or Workplace.objects.get(pk=client.session['active_workplace_id'])
        base = scoped_workplace_app_path(workspace, 'api', f'v1/{kind}/')
        url = base + '?' + urlencode({'url': target})
        return client.get(url) if values is None else client.post(url, values)

    def test_directory_capabilities_follow_each_row_even_with_active_guest(self):
        active = self.shared['guest']
        self.activate(active)
        response = self.api(reverse('workplaces:workplaces'), workspace=active)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['read_only'])
        rows = {row['id']: row for row in response.json()['data']['rows']}
        for workplace in (self.first, self.second):
            row = rows[str(workplace.pk)]
            self.assertTrue(row['can_manage'])
            self.assertEqual(row['edit_url'], workplace_management_url(workplace) + '&tab=main')
            self.assertTrue(row['can_delete'])
            self.assertEqual(row['delete_url'], self.delete_url(workplace))
            self.assertEqual(row['delete_disabled_reason'], '')
        for role, workplace in self.shared.items():
            row = rows[str(workplace.pk)]
            self.assertEqual(row['can_manage'], role == 'admin')
            self.assertEqual(bool(row['edit_url']), role == 'admin')
            self.assertFalse(row['can_delete'])
            self.assertEqual(row['delete_url'], '')
            self.assertIn('właściciel', row['delete_disabled_reason'])
        self.assertNotIn(str(self.foreign.pk), rows)
        self.assertEqual(self.client.session['active_workplace_id'], active.pk)

    def test_confirmation_is_compact_writable_and_has_workspace_settings_navigation(self):
        active = self.shared['guest']
        self.activate(active)
        response = self.api(self.delete_url(), workspace=active, navigation=True)
        self.assertEqual(response.status_code, 200)
        page, shell = response.json()['page'], response.json()['shell']
        self.assertEqual(page['type'], 'workspace-form')
        self.assertFalse(page['read_only'])
        self.assertEqual(shell['mode'], 'settings')
        self.assertEqual(shell['settings_category'], 'workspace')
        self.assertEqual(shell['workplace_id'], str(active.pk))
        data = page['data']
        self.assertEqual(data['title'], 'Usuń Workspace')
        self.assertEqual(data['return_url'], reverse('workplaces:workplaces'))
        self.assertEqual(data['action'], self.delete_url())
        self.assertTrue(data['form']['compact'])
        self.assertEqual(data['form']['submit_label'], 'Usuń Workspace')
        self.assertIn(self.first.name, data['form']['confirmation_message'])
        self.assertIn('nie można cofnąć', data['form']['confirmation_message'])
        self.assertEqual(data['form']['fields'][0]['name'], 'name')
        self.assertTrue(Workplace.objects.filter(pk=self.first.pk).exists())

    def test_missing_wrong_and_stale_names_do_not_delete(self):
        for value in ('', 'Inna nazwa', self.first.name + ' '):
            response = self.api(self.delete_url(), {'name': value})
            self.assertEqual(response.status_code, 400)
            self.assertTrue(response.json()['data']['form']['fields'][0]['errors'])
        old_name = self.first.name
        self.first.name = 'Zmieniony Workspace'
        self.first.save(update_fields=['name'])
        response = self.api(self.delete_url(), {'name': old_name})
        self.assertEqual(response.status_code, 400)
        self.assertIn(self.first.name, response.json()['data']['form']['confirmation_message'])
        self.assertTrue(Workplace.objects.filter(pk=self.first.pk).exists())
        response = self.api(self.delete_url(), {'name': self.first.name})
        self.assertEqual(response.json()['redirect'], reverse('workplaces:workplaces'))
        self.assertFalse(Workplace.objects.filter(pk=self.first.pk).exists())

    def test_nonowners_cannot_get_or_post_delete_including_admin_and_foreign(self):
        for workspace in [*self.shared.values(), self.foreign]:
            for values in (None, {'name': workspace.name}):
                with self.subTest(workspace=workspace.pk, post=values is not None):
                    self.assertEqual(self.api(self.delete_url(workspace), values).status_code, 404)
                    self.assertTrue(Workplace.objects.filter(pk=workspace.pk).exists())

    def test_own_nonactive_delete_works_from_active_guest_and_keeps_context_and_default(self):
        active = self.shared['guest']
        self.activate(active)
        self.owner.default_workplace = self.second
        self.owner.save(update_fields=['default_workplace'])
        response = self.api(self.delete_url(), {'name': self.first.name}, workspace=active)
        self.assertEqual(response.json()['redirect'], reverse('workplaces:workplaces'))
        self.assertFalse(Workplace.objects.filter(pk=self.first.pk).exists())
        self.assertEqual(self.client.session['active_workplace_id'], active.pk)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.default_workplace_id, self.second.pk)

    def test_active_delete_replaces_with_owned_workspace_and_clears_deleted_default(self):
        self.shared['member'].name = 'AAA Joined first'
        self.shared['member'].save(update_fields=['name'])
        self.owner.default_workplace = self.first
        self.owner.save(update_fields=['default_workplace'])
        response = self.api(self.delete_url(), {'name': self.first.name}, workspace=self.first)
        self.assertEqual(response.json()['redirect'], reverse('workplaces:workplaces'))
        self.assertEqual(self.client.session['active_workplace_id'], self.second.pk)
        self.owner.refresh_from_db()
        self.assertIsNone(self.owner.default_workplace_id)
        page = self.api(reverse('workplaces:workplaces'), navigation=True).json()
        self.assertEqual(page['shell']['workplace_id'], str(self.second.pk))

    def test_last_owned_is_disabled_and_protected_despite_memberships_elsewhere(self):
        self.second.delete()
        self.activate(self.shared['guest'])
        rows = self.api(reverse('workplaces:workplaces')).json()['data']['rows']
        row = next(row for row in rows if row['id'] == str(self.first.pk))
        self.assertTrue(row['can_manage'])
        self.assertTrue(row['edit_url'])
        self.assertFalse(row['can_delete'])
        self.assertEqual(row['delete_url'], '')
        self.assertIn('ostatniego', row['delete_disabled_reason'])
        self.assertEqual(self.api(self.delete_url()).status_code, 403)
        response = self.client.post(self.delete_url(), {'name': self.first.name})
        self.assertRedirects(response, reverse('workplaces:workplaces'))
        self.assertTrue(Workplace.objects.filter(pk=self.first.pk).exists())
        self.assertEqual(self.client.session['active_workplace_id'], self.shared['guest'].pk)

    def test_confirmation_opened_before_last_owned_change_cannot_delete_remaining(self):
        self.assertEqual(self.api(self.delete_url()).status_code, 200)
        self.second.delete()
        response = self.api(self.delete_url(), {'name': self.first.name})
        self.assertEqual(response.json()['redirect'], reverse('workplaces:workplaces'))
        self.assertTrue(Workplace.objects.filter(pk=self.first.pk).exists())

    def test_native_confirmation_shows_scope_and_invalid_field_without_mutation(self):
        response = self.client.get(self.delete_url())
        self.assertContains(response, 'class="resources-form-wide app-form-wide">Usunięcie Workspace')
        self.assertContains(response, 'app-modal-panel--compact')
        self.assertEqual(response.context['settings_category'], 'workspace')
        response = self.client.post(self.delete_url(), {'name': 'Błąd'})
        self.assertContains(response, 'Wpisz dokładną nazwę Workspace.', status_code=400)
        self.assertTrue(Workplace.objects.filter(pk=self.first.pk).exists())

    def test_native_toolbar_has_search_then_single_selection_actions_and_target_urls(self):
        response = self.client.get(reverse('workplaces:workplaces'))
        html = response.content.decode()
        self.assertLess(html.index('data-workplaces-search'), html.index('data-workplaces-edit'))
        self.assertLess(html.index('data-workplaces-edit'), html.index('data-workplaces-delete'))
        self.assertContains(response, 'data-workplaces-edit disabled')
        self.assertContains(response, 'data-workplaces-delete disabled')
        self.assertContains(response, f'data-workplace-delete-url="{self.delete_url()}"')
        self.assertNotContains(response, f'data-workplace-delete-url="{self.delete_url(self.shared["admin"])}"')

    def test_csrf_is_required_for_native_and_api_deletion(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.activate(self.first, client)
        self.assertEqual(client.post(self.delete_url(), {'name': self.first.name}).status_code, 403)
        self.assertEqual(self.api(self.delete_url(), {'name': self.first.name}, client=client).status_code, 403)
        client.get(self.delete_url())
        token = client.cookies['csrftoken'].value
        response = client.post(self.delete_url(), {'name': self.first.name}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Workplace.objects.filter(pk=self.first.pk).exists())

    def test_native_delete_cascades_only_selected_workspace_and_keeps_user_accounts(self):
        spaces = [make_space(user=self.owner, workplace=workspace, name='Dane') for workspace in (self.first, self.second)]
        tasks = [SpaceTask.objects.create(space=space, created_by=self.owner, title='Zadanie') for space in spaces]
        WorkplaceMembership.objects.create(workplace=self.first, user=self.other)
        response = self.client.post(self.delete_url(), {'name': self.first.name})
        self.assertRedirects(response, reverse('workplaces:workplaces'))
        self.assertFalse(Space.objects.filter(pk=spaces[0].pk).exists())
        self.assertFalse(SpaceTask.objects.filter(pk=tasks[0].pk).exists())
        self.assertTrue(Space.objects.filter(pk=spaces[1].pk).exists())
        self.assertTrue(SpaceTask.objects.filter(pk=tasks[1].pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.owner.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.other.pk).exists())
        self.assertTrue(Workplace.objects.filter(pk=self.foreign.pk).exists())
