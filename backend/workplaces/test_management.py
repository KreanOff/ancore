"""Managing another Workspace must preserve the active business-data context."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import WorkplaceInviteLink, WorkplaceMembership, create_workplace_for_user
from .services import workplace_management_url, scoped_workplace_app_path


class WorkspaceManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='manager', email='manager@example.test')
        cls.member = users.objects.create_user(username='colleague', email='colleague@example.test')
        cls.recipient = users.objects.create_user(username='recipient', email='recipient@example.test')
        cls.active = create_workplace_for_user(cls.owner, 'Aktywny Workspace')
        cls.selected = create_workplace_for_user(cls.owner, 'Wybrany Workspace')
        cls.foreign = create_workplace_for_user(cls.recipient, 'Obcy Workspace')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.selected, user=cls.member, role='member')

    def setUp(self):
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.active.pk
        session.save()

    def assert_active_unchanged(self):
        self.assertEqual(self.client.session['active_workplace_id'], self.active.pk)

    def test_members_tab_shows_only_selected_team(self):
        response = self.client.get(workplace_management_url(self.selected))
        self.assertContains(response, self.active.name)
        self.assertContains(response, self.selected.name)
        self.assertNotContains(response, self.foreign.name)
        self.assertEqual(response.context['team_workplace'], self.selected)
        self.assertEqual({m.user_id for m in response.context['members']}, {self.owner.pk, self.member.pk})
        self.assertEqual(response.context['active_workplace'], self.active)
        self.assertEqual(response.context['management_view'], 'workspaces')
        self.assertTrue(response.context['workplace_edit_modal_open'])
        self.assertEqual(response.context['workplace_edit_tab'], 'members')
        self.assertContains(response, 'id="workspace-team-members"', count=1)
        self.assertContains(response, 'data-workplace-row ')
        self.assert_active_unchanged()

    def test_members_legacy_link_and_settings_open_the_requested_tab(self):
        for query, tab in [({'view': 'members'}, 'members'), ({'tab': 'main'}, 'main')]:
            response = self.client.get(reverse('workplaces:workplaces'), {'workspace': self.selected.pk, **query})
            self.assertTrue(response.context['workplace_edit_modal_open'])
            self.assertEqual(response.context['workplace_edit_tab'], tab)
            self.assertEqual(response.context['team_workplace'], self.selected)
            self.assertNotContains(response, 'href="/workplaces/?view=members')
            self.assert_active_unchanged()

    def test_member_can_read_modal_but_cannot_change_settings(self):
        self.client.force_login(self.member)
        response = self.client.get(workplace_management_url(self.selected))
        self.assertTrue(response.context['workplace_edit_modal_open'])
        self.assertContains(response, 'id="workspace-team-members"')
        self.assertContains(response, 'data-workplace-edit-autofocus readonly')
        self.assertNotContains(response, 'data-workplace-main-action')
        self.assertNotContains(response, 'data-team-remove')
        self.assertNotContains(response, 'id="team-role-modal"')
        self.assertContains(response, 'data-sidebar-navigation="settings" hidden')
        response = self.client.post(reverse('workplaces:update', args=[self.selected.pk]), {'name': 'Nie wolno'})
        self.assertEqual(response.status_code, 403)
        self.selected.refresh_from_db()
        self.assertEqual(self.selected.name, 'Wybrany Workspace')

    def test_settings_validation_keeps_values_in_main_tab(self):
        response = self.client.post(reverse('workplaces:update', args=[self.selected.pk]), {
            'name': ' ', 'description': 'Opis do zachowania', 'code': 'KOD', 'view': 'workspaces',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['edit_form'].errors)
        self.assertTrue(response.context['workplace_edit_modal_open'])
        self.assertEqual(response.context['workplace_edit_tab'], 'main')
        self.assertContains(response, 'Opis do zachowania')
        self.assertEqual(response.context['sidebar_mode'], 'workplaces')
        self.assertContains(response, 'aria-current="page" aria-label="Workspace"')
        self.selected.refresh_from_db()
        self.assertEqual(self.selected.name, 'Wybrany Workspace')
        self.assert_active_unchanged()

    def test_old_team_link_opens_selected_panel_without_switching(self):
        response = self.client.get(reverse('workplaces:team', args=[self.selected.pk]), {'view': 'links'})
        self.assertRedirects(response, workplace_management_url(self.selected, 'links'))
        self.assert_active_unchanged()

    def test_invalid_or_inaccessible_selection_cannot_expose_team(self):
        for selected in [self.foreign.pk, 'bad-id', '999999999999999999999999', '']:
            with self.subTest(selected=selected):
                response = self.client.get(reverse('workplaces:workplaces'), {'workspace': selected})
                self.assertEqual(response.status_code, 404)
                self.assert_active_unchanged()

    def test_manual_add_errors_and_success_keep_selected_team(self):
        url = reverse('workplaces:team', args=[self.selected.pk])
        response = self.client.post(url, {'user_id': 'invalid', 'role': 'member'})
        self.assertEqual(response.context['team_workplace'], self.selected)
        self.assertTrue(response.context['add_form'].errors)
        self.assertTrue(response.context['workplace_edit_modal_open'])
        self.assertEqual(response.context['workplace_edit_tab'], 'members')
        self.assertContains(response, self.active.name)
        self.assertContains(response, 'id="team-add-modal"')
        self.assert_active_unchanged()
        response = self.client.post(url, {'user_id': self.recipient.pk, 'role': 'member'})
        self.assertRedirects(response, workplace_management_url(self.selected))
        self.assertEqual(WorkplaceMembership.objects.get(workplace=self.selected, user=self.recipient).role, 'member')
        self.assert_active_unchanged()

    def test_roles_settings_and_removal_return_to_same_panel(self):
        url = reverse('workplaces:member-update', args=[self.selected.pk, self.membership.pk])
        response = self.client.post(url, {'action': 'role', 'role': 'admin'})
        self.assertRedirects(response, workplace_management_url(self.selected))
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, 'admin')
        response = self.client.post(reverse('workplaces:update', args=[self.selected.pk]), {'name': 'Zmieniony Workspace'})
        self.assertRedirects(response, workplace_management_url(self.selected))
        self.selected.refresh_from_db()
        self.assertEqual(self.selected.name, 'Zmieniony Workspace')
        response = self.client.post(url, {'action': 'remove'})
        self.assertRedirects(response, workplace_management_url(self.selected))
        self.assertFalse(WorkplaceMembership.objects.filter(pk=self.membership.pk).exists())
        self.assert_active_unchanged()

    def test_member_cannot_see_links_or_management_controls(self):
        link = WorkplaceInviteLink.objects.create(workplace=self.selected)
        self.client.force_login(self.member)
        response = self.client.get(workplace_management_url(self.selected, 'links'))
        self.assertFalse(response.context['show_links'])
        self.assertFalse(response.context['can_manage_team'])
        self.assertNotContains(response, str(link.token))
        self.assertNotContains(response, 'id="team-add-modal"')
        self.assertNotContains(response, 'data-workplace-tab="links"')
        self.assertEqual(self.client.post(reverse('workplaces:team', args=[self.selected.pk]), {'user_id': self.recipient.pk, 'role': 'member'}).status_code, 403)
        self.membership.delete()
        self.assertEqual(self.client.get(workplace_management_url(self.selected)).status_code, 404)

    def test_cross_workspace_actions_are_rejected(self):
        response = self.client.post(reverse('workplaces:member-update', args=[self.active.pk, self.membership.pk]), {'action': 'remove'})
        self.assertEqual(response.status_code, 404)
        self.assertTrue(WorkplaceMembership.objects.filter(pk=self.membership.pk).exists())
        self.assert_active_unchanged()

    def test_csrf_is_required_for_management_actions(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.post(reverse('workplaces:team', args=[self.selected.pk]), {'user_id': self.recipient.pk, 'role': 'member'})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(WorkplaceMembership.objects.filter(workplace=self.selected, user=self.recipient).exists())

    def test_creation_enters_new_workspace_and_explicit_switch_changes_context(self):
        response = self.client.post(reverse('workplaces:workplaces'), {'name': 'Nowy Workspace'})
        created = self.owner.owned_workplaces.get(name='Nowy Workspace')
        self.assertRedirects(response, scoped_workplace_app_path(created, 'for-you'))
        self.assertEqual(self.client.session['active_workplace_id'], created.pk)
        response = self.client.post(reverse('workplaces:switch', args=[created.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session['active_workplace_id'], created.pk)

    def test_link_tab_keeps_directory_and_active_context(self):
        response = self.client.get(reverse('workplaces:workplaces'))
        self.assertEqual(response.context['sidebar_mode'], 'workplaces')
        self.assertEqual(response.context['management_view'], 'workspaces')
        self.assertFalse(response.context['workplace_edit_modal_open'])
        response = self.client.get(workplace_management_url(self.selected, 'links'))
        self.assertEqual(response.context['management_view'], 'workspaces')
        self.assertTrue(response.context['workplace_edit_modal_open'])
        self.assertEqual(response.context['workplace_edit_tab'], 'links')
        self.assertContains(response, 'data-workplace-row ')
        self.assert_active_unchanged()

    def test_retired_received_query_does_not_open_an_invitation(self):
        response = self.client.get(reverse('workplaces:workplaces'), {'invitation': 1})
        self.assertNotContains(response, 'data-invitation-response-modal')
        self.assertNotIn('response_invitation', response.context)
        self.assertFalse(response.context['workplace_edit_modal_open'])
        self.assert_active_unchanged()

    def test_link_list_is_scoped_to_selected_workspace(self):
        selected = WorkplaceInviteLink.objects.create(workplace=self.selected)
        other = WorkplaceInviteLink.objects.create(workplace=self.active)
        response = self.client.get(workplace_management_url(self.selected, 'links'))
        self.assertEqual(list(response.context['invite_links']), [selected])
        self.assertContains(response, str(selected.token))
        self.assertNotContains(response, str(other.token))
        self.assertEqual(response.context['workplace_edit_tab'], 'links')
        self.assert_active_unchanged()

    def test_settings_can_return_to_workspace_directory(self):
        response = self.client.post(reverse('workplaces:update', args=[self.selected.pk]), {'name': self.selected.name, 'view': 'workspaces'})
        self.assertRedirects(response, workplace_management_url(self.selected, 'workspaces'))
        self.assert_active_unchanged()
