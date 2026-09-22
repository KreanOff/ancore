"""Managing another Workspace must preserve the active business-data context."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import WorkplaceInvitation, WorkplaceMembership, create_workplace_for_user
from .services import workplace_management_url


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
        self.assertContains(response, 'id="workspace-team"')
        self.assertNotContains(response, 'data-workplace-row ')
        self.assert_active_unchanged()

    def test_old_team_link_opens_selected_panel_without_switching(self):
        response = self.client.get(reverse('workplaces:team', args=[self.selected.pk]), {'view': 'invitations'})
        self.assertRedirects(response, workplace_management_url(self.selected, 'invitations'))
        self.assert_active_unchanged()

    def test_invalid_or_inaccessible_selection_cannot_expose_team(self):
        for selected in [self.foreign.pk, 'bad-id', '999999999999999999999999', '']:
            with self.subTest(selected=selected):
                response = self.client.get(reverse('workplaces:workplaces'), {'workspace': selected})
                self.assertEqual(response.status_code, 404)
                self.assert_active_unchanged()

    def test_invitation_errors_and_success_keep_selected_team(self):
        url = reverse('workplaces:team', args=[self.selected.pk])
        response = self.client.post(url, {'email': 'missing@example.test', 'role': 'member'})
        self.assertEqual(response.context['team_workplace'], self.selected)
        self.assertTrue(response.context['invite_form'].errors)
        self.assertContains(response, self.active.name)
        self.assertContains(response, 'id="team-invite-modal"')
        self.assert_active_unchanged()
        response = self.client.post(url, {'email': self.recipient.email, 'role': 'member'})
        self.assertRedirects(response, workplace_management_url(self.selected, 'invitations'))
        invitation = WorkplaceInvitation.objects.get(recipient=self.recipient)
        self.assertEqual(invitation.workplace, self.selected)
        self.assertEqual(invitation.invited_by, self.owner)
        self.assert_active_unchanged()
        response = self.client.post(reverse('workplaces:invitation-cancel', args=[self.selected.pk, invitation.pk]))
        self.assertRedirects(response, workplace_management_url(self.selected, 'invitations'))
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'revoked')
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

    def test_member_cannot_see_sent_invitations_or_management_controls(self):
        WorkplaceInvitation.objects.create(workplace=self.selected, recipient=self.recipient, invited_by=self.owner)
        self.client.force_login(self.member)
        response = self.client.get(workplace_management_url(self.selected, 'invitations'))
        self.assertFalse(response.context['show_invitations'])
        self.assertFalse(response.context['can_manage_team'])
        self.assertNotContains(response, self.recipient.email)
        self.assertNotContains(response, 'id="team-invite-modal"')
        self.assertEqual(self.client.post(reverse('workplaces:team', args=[self.selected.pk]), {'email': self.recipient.email, 'role': 'member'}).status_code, 403)
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
        response = client.post(reverse('workplaces:team', args=[self.selected.pk]), {'email': self.recipient.email, 'role': 'member'})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(WorkplaceInvitation.objects.filter(recipient=self.recipient).exists())

    def test_creation_stays_in_management_and_explicit_switch_changes_context(self):
        response = self.client.post(reverse('workplaces:workplaces'), {'name': 'Nowy Workspace'})
        created = self.owner.owned_workplaces.get(name='Nowy Workspace')
        self.assertRedirects(response, workplace_management_url(created, 'workspaces'))
        self.assert_active_unchanged()
        response = self.client.post(reverse('workplaces:switch', args=[created.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session['active_workplace_id'], created.pk)

    def test_directory_and_invitation_tabs_show_one_list_at_a_time(self):
        response = self.client.get(reverse('workplaces:workplaces'))
        self.assertEqual(response.context['management_view'], 'workspaces')
        self.assertContains(response, 'data-workplace-row ')
        self.assertNotContains(response, 'id="workspace-team"')
        response = self.client.get(workplace_management_url(self.selected, 'invitations'))
        self.assertEqual(response.context['management_view'], 'invitations')
        self.assertContains(response, 'Brak oczekujących zaproszeń.')
        self.assertNotContains(response, 'data-workplace-row ')
        response = self.client.get(workplace_management_url(self.selected, 'received'))
        self.assertContains(response, 'Brak otrzymanych zaproszeń.')
        self.assertNotContains(response, 'id="workspace-team"')
        self.assert_active_unchanged()

    def test_received_invitations_tab_is_recipient_only(self):
        incoming = WorkplaceInvitation.objects.create(workplace=self.foreign, recipient=self.owner, invited_by=self.recipient)
        WorkplaceInvitation.objects.create(workplace=self.selected, recipient=self.recipient, invited_by=self.owner)
        response = self.client.get(workplace_management_url(self.selected, 'received'))
        self.assertEqual(response.context['pending_invitations'], [incoming])
        self.assertContains(response, 'Otwórz zaproszenie do Obcy Workspace')
        self.assertNotContains(response, 'Anuluj zaproszenie')
        self.assert_active_unchanged()

    def test_settings_can_return_to_workspace_directory(self):
        response = self.client.post(reverse('workplaces:update', args=[self.selected.pk]), {'name': self.selected.name, 'view': 'workspaces'})
        self.assertRedirects(response, workplace_management_url(self.selected, 'workspaces'))
        self.assert_active_unchanged()
