"""Retired email invitations cannot reappear as inbox sources or access grants."""
from uuid import uuid4

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import FieldDoesNotExist
from django.db import connection
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from dashboard.models import NotificationState
from dashboard.notification_service import SIGNING_SALT
from spaces.models import SpaceTaskActivity
from spaces.testing import make_task
from workplaces.models import WorkplaceInviteLink, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path, workplaces_for_user


class RetiredWorkspaceInvitationTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.owner = users.create_user(username='retired-inviter', email='retired-inviter@example.test')
        self.recipient = users.create_user(username='retired-recipient', email='retired-recipient@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Niedostępny Workspace')
        self.personal = create_workplace_for_user(self.recipient, 'Osobisty Workspace')
        self.task = make_task(user=self.recipient, workplace=self.personal, title='Bieżące zadanie')
        self.comment = SpaceTaskActivity.objects.create(task=self.task, actor=self.owner, kind='comment', message='Bieżący komentarz')
        self.client.force_login(self.recipient)
        session = self.client.session
        session['active_workplace_id'] = self.personal.pk
        session.save()

    def panel(self, **params):
        return self.client.get(reverse('notifications'), params, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def summary(self):
        return self.client.get(reverse('notifications'), {'summary': '1'})

    def test_email_model_table_and_receipt_relation_are_removed(self):
        with self.assertRaises(LookupError):
            apps.get_model('workplaces', 'WorkplaceInvitation')
        with self.assertRaises(FieldDoesNotExist):
            NotificationState._meta.get_field('invitation')
        self.assertNotIn('workplaces_workplaceinvitation', connection.introspection.table_names())
        with connection.cursor() as cursor:
            columns = connection.introspection.get_table_description(cursor, NotificationState._meta.db_table)
        self.assertNotIn('invitation_id', [column.name for column in columns])

    def test_retired_route_names_and_urls_do_not_grant_access(self):
        retired = [('join-email', [uuid4()]), ('invitation-response', [1]),
                   ('invitation-resend', [self.workspace.pk, 1]), ('invitation-cancel', [self.workspace.pk, 1]),
                   ('invitation-candidates', [self.workspace.pk])]
        for name, args in retired:
            with self.subTest(name=name), self.assertRaises(NoReverseMatch):
                reverse('workplaces:' + name, args=args)
        urls = [f'/workplaces/invite/{uuid4()}/', '/workplaces/invitations/1/respond/',
                f'/workplaces/{self.workspace.pk}/invitations/1/resend/',
                f'/workplaces/{self.workspace.pk}/invitations/1/cancel/']
        for url in urls:
            for method in ('get', 'post'):
                with self.subTest(url=url, method=method):
                    self.assertEqual(getattr(self.client, method)(url, {'action': 'accept'}).status_code, 404)
        self.assertNotIn(self.workspace, workplaces_for_user(self.recipient))
        self.assertFalse(NotificationState.objects.exists())

    def test_retired_source_and_filter_are_rejected_without_changing_comments(self):
        for action in ('read', 'unread', 'archive', 'restore', 'delete'):
            response = self.client.post(reverse('notification_action'), {'action': action, 'key': 'workplace:1'})
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.panel(view='invitations').status_code, 400)
        payload = self.panel().json()
        self.assertEqual((payload['count'], payload['total'], payload['deletable_count']), (1, 1, 1))
        self.assertIn(f'data-notification-key="spaces:{self.comment.pk}"', payload['html'])
        self.assertFalse(NotificationState.objects.exists())

    def test_old_invitation_snapshots_and_cursors_are_rejected(self):
        token = signing.dumps({'user': self.recipient.pk, 'asof': timezone.now().isoformat(),
                               'filters': {'view': 'invitations', 'workspace': ''}}, salt=SIGNING_SALT, compress=True)
        self.assertEqual(self.panel(cursor=token).status_code, 400)
        for action in ('read_all', 'delete_all'):
            response = self.client.post(reverse('notification_action'), {'action': action, 'snapshot': token})
            self.assertEqual(response.status_code, 400)
        self.assertFalse(NotificationState.objects.exists())
        self.assertEqual(self.panel().json()['total'], 1)

    def test_current_invite_links_do_not_create_inbox_sources_or_unrelated_memberships(self):
        link = WorkplaceInviteLink.objects.create(workplace=self.workspace, created_by=self.owner)
        before = self.summary().json()
        directory = self.client.get(reverse('workplaces:workplaces'), {'invitation': '1'})
        self.assertEqual(directory.status_code, 200)
        self.assertNotIn('response_invitation', directory.context)
        self.assertNotContains(directory, 'data-invitation-response-modal')
        self.assertEqual(self.summary().json(), before)
        self.assertEqual(self.panel().json()['total'], 1)
        self.assertTrue(WorkplaceInviteLink.objects.filter(pk=link.pk).exists())
        self.assertNotIn(self.workspace, workplaces_for_user(self.recipient))

    def test_payload_summary_and_shell_have_no_email_invitation_indicators(self):
        payload = self.panel().json()
        self.assertNotIn('pending_invitation_count', payload)
        self.assertNotIn('data-notifications-invitation', payload['html'])
        api = scoped_workplace_app_path(self.personal, 'api', 'v1/page/')
        typed = self.client.get(api, {'url': reverse('notifications')}).json()
        self.assertNotIn('pending_invitation_count', typed)
        self.assertTrue(typed['items'])
        self.assertTrue(all('is_invitation' not in item for item in typed['items']))
        page = self.client.get(scoped_workplace_app_path(self.personal, 'spaces'))
        self.assertEqual(page.status_code, 200)
        for key in ('pending_workspace_invitation_count', 'pending_notification_invitation_count'):
            self.assertNotIn(key, page.context)
        self.assertContains(page, 'data-notifications-unread-status')
        for marker in ('data-notifications-invitation-badge',
                       'data-notifications-invitation-count', 'data-invitation-response-modal'):
            self.assertNotContains(page, marker)

    def test_summary_remains_private_json_and_requires_authentication(self):
        response = self.summary()
        self.assertEqual(response.json()['unread_count'], 1)
        self.assertNotIn('pending_invitation_count', response.json())
        self.assertNotIn('html', response.json())
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.client.logout()
        self.assertEqual(self.summary().status_code, 302)
        self.assertEqual(self.panel().status_code, 302)
