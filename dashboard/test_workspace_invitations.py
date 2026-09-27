from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.views import DASHBOARD_NOTIFICATION_LIMIT, _dashboard_notifications
from tasks.models import Task, TaskActivity
from workplaces.models import WorkplaceInvitation, create_workplace_for_user
from workplaces.services import workplaces_for_user


class WorkspaceInvitationNotificationTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.owner = users.create_user(username='inviter', email='inviter@example.test')
        self.recipient = users.create_user(username='recipient', email='recipient@example.test')
        self.other = users.create_user(username='other', email='other@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Zapraszający zespół')
        self.personal = create_workplace_for_user(self.recipient, 'Osobisty Workspace')
        self.invitation = WorkplaceInvitation.objects.create(
            workplace=self.workspace, recipient=self.recipient, invited_by=self.owner, role='admin',
        )
        self.client.force_login(self.recipient)
        session = self.client.session
        session['active_workplace_id'] = self.personal.pk
        session.save()

    def panel(self):
        return self.client.get(reverse('notifications'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def summary(self):
        return self.client.get(reverse('notifications'), {'summary': '1'})

    def test_invitation_is_visible_before_membership_and_links_to_decision(self):
        response = self.panel()
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['pending_invitation_count'], 1)
        self.assertEqual(payload['count'], 1)
        for text in ('inviter', 'zaprasza Cię do Workspace', self.workspace.name, 'Administrator',
                     'Przyjmij lub odrzuć zaproszenie', f'?invitation={self.invitation.pk}'):
            self.assertIn(text, payload['html'])
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertNotIn(self.workspace, workplaces_for_user(self.recipient))
        response = self.client.get(reverse('workplaces:team', args=[self.personal.pk]), follow=True)
        self.assertEqual(response.context['pending_workspace_invitation_count'], 1)
        self.assertContains(response, 'data-notifications-invitation-badge aria-hidden="true">1</span>')
        self.assertContains(response, 'data-notifications-invitation-count>1</span>')
        response = self.client.get(reverse('workplaces:workplaces'))
        self.assertNotContains(response, 'aria-label="Otrzymane zaproszenia: 1"')
        self.assertNotContains(response, '?view=received')
        self.assertNotContains(response, 'workplace-invitations__row')
        self.assertFalse(response.context['invitation_modal_open'])
        response = self.client.get(reverse('workplaces:workplaces'), {'invitation': self.invitation.pk})
        self.assertTrue(response.context['invitation_modal_open'])
        self.assertEqual(response.context['response_invitation'], self.invitation)
        self.assertContains(response, 'data-team-response-form')
        self.assertNotIn(self.workspace, workplaces_for_user(self.recipient))

    def test_invitations_are_recipient_only_in_panel_and_summary(self):
        for user in (self.owner, self.other):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.panel().json()['pending_invitation_count'], 0)
                self.assertNotIn('zaprasza Cię do Workspace', self.panel().json()['html'])
                self.assertEqual(self.summary().json()['pending_invitation_count'], 0)

    def test_inactive_and_expired_invitations_disappear_from_all_surfaces(self):
        for status in ('accepted', 'declined', 'revoked'):
            with self.subTest(status=status):
                self.invitation.status = status
                self.invitation.save(update_fields=['status'])
                self.assertEqual(self.panel().json()['count'], 0)
                self.assertEqual(self.summary().json()['pending_invitation_count'], 0)
                response = self.client.get(reverse('workplaces:workplaces'))
                self.assertNotContains(response, 'data-invitation-response-modal')
                self.assertContains(response, 'data-notifications-pending aria-hidden="true" hidden')
                self.assertContains(response, 'data-notifications-invitation-badge aria-hidden="true" hidden>0</span>')
                self.assertContains(response, 'data-notifications-invitation-count hidden>0</span>')
        self.invitation.status = 'pending'
        self.invitation.expires_at = timezone.now() - timedelta(seconds=1)
        self.invitation.save(update_fields=['status', 'expires_at'])
        self.assertEqual(self.panel().json()['count'], 0)
        self.assertEqual(self.summary().json()['pending_invitation_count'], 0)

    def test_pending_invitation_stays_ahead_of_newer_task_activity(self):
        task = Task.objects.create(user=self.recipient, workplace=self.personal, title='Aktywne zadanie')
        for _ in range(DASHBOARD_NOTIFICATION_LIMIT + 1):
            TaskActivity.objects.create(task=task, actor=self.recipient, action='updated', message='zmienił zadanie')
        notifications = _dashboard_notifications(self.recipient)
        self.assertEqual(len(notifications), DASHBOARD_NOTIFICATION_LIMIT)
        self.assertEqual(notifications[0]['source'], 'workplace')
        self.assertEqual(notifications[0]['object_id'], self.invitation.pk)
        self.assertTrue(any(item['source'] == 'tasks' for item in notifications))

    def test_accepting_clears_indicator_and_grants_access_only_after_post(self):
        url = reverse('workplaces:invitation-response', args=[self.invitation.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertNotIn(self.workspace, workplaces_for_user(self.recipient))
        self.assertEqual(self.client.post(url, {'action': 'accept'}).status_code, 302)
        self.assertIn(self.workspace, workplaces_for_user(self.recipient))
        self.assertEqual(self.summary().json()['pending_invitation_count'], 0)
        self.assertNotIn('zaprasza Cię do Workspace', self.panel().json()['html'])
        self.assertEqual(self.client.post(url, {'action': 'accept'}).status_code, 404)

    def test_declining_clears_indicator_without_granting_access(self):
        url = reverse('workplaces:invitation-response', args=[self.invitation.pk])
        self.assertEqual(self.client.post(url, {'action': 'decline'}).status_code, 302)
        self.assertEqual(self.summary().json()['pending_invitation_count'], 0)
        self.assertNotIn(self.workspace, workplaces_for_user(self.recipient))

    def test_summary_is_private_and_does_not_render_activity(self):
        response = self.summary()
        self.assertEqual(response.json()['pending_invitation_count'], 1)
        self.assertEqual(response.json()['unread_count'], 1)
        self.assertNotIn('html', response.json())
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.client.logout()
        self.assertEqual(self.summary().status_code, 302)
        self.assertEqual(self.panel().status_code, 302)

    def test_invitation_dialog_rejects_foreign_invalid_and_expired_links(self):
        url = reverse('workplaces:workplaces')
        self.client.force_login(self.other)
        response = self.client.get(url, {'invitation': self.invitation.pk})
        self.assertRedirects(response, url)
        self.client.force_login(self.recipient)
        for value in ('invalid', '99999999999999999999999999999999', ''):
            self.assertRedirects(self.client.get(url, {'invitation': value}), url)
        self.invitation.expires_at = timezone.now() - timedelta(seconds=1)
        self.invitation.save(update_fields=['expires_at'])
        response = self.client.get(url, {'invitation': self.invitation.pk}, follow=True)
        self.assertContains(response, 'To zaproszenie nie jest już dostępne.')
        self.assertNotContains(response, 'data-invitation-response-modal')

    def test_dialog_navigation_contains_only_recipients_pending_invitations(self):
        second = create_workplace_for_user(self.owner, 'Drugi zapraszający zespół')
        invitation = WorkplaceInvitation.objects.create(workplace=second, recipient=self.recipient, invited_by=self.owner)
        foreign = create_workplace_for_user(self.owner, 'Niewidoczny zespół')
        WorkplaceInvitation.objects.create(workplace=foreign, recipient=self.other, invited_by=self.owner)
        url = reverse('workplaces:workplaces')
        response = self.client.get(url, {'invitation': invitation.pk})
        self.assertEqual(response.context['invitation_position'], 1)
        self.assertIsNone(response.context['previous_invitation'])
        self.assertEqual(response.context['next_invitation'], self.invitation)
        self.assertNotContains(response, foreign.name)
        response = self.client.get(url, {'invitation': self.invitation.pk})
        self.assertEqual(response.context['invitation_position'], 2)
        self.assertEqual(response.context['previous_invitation'], invitation)
        self.assertIsNone(response.context['next_invitation'])

    def test_count_includes_invitations_beyond_panel_limit_and_deleted_actor_is_safe(self):
        self.invitation.invited_by = None
        self.invitation.save(update_fields=['invited_by'])
        self.assertIn('System', self.panel().json()['html'])
        for index in range(DASHBOARD_NOTIFICATION_LIMIT):
            workplace = create_workplace_for_user(self.owner, f'Zespół {index}')
            WorkplaceInvitation.objects.create(workplace=workplace, recipient=self.recipient, invited_by=self.owner)
        self.assertEqual(self.summary().json()['pending_invitation_count'], DASHBOARD_NOTIFICATION_LIMIT + 1)
        self.assertEqual(self.panel().json()['count'], DASHBOARD_NOTIFICATION_LIMIT)
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'data-notifications-invitation-badge aria-hidden="true">9+</span>')
        self.assertContains(response, f'data-notifications-invitation-count>{DASHBOARD_NOTIFICATION_LIMIT + 1}</span>')
