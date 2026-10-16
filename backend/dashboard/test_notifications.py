from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.models import ActivityInterest, NotificationState
from dashboard.notification_service import DASHBOARD_NOTIFICATION_LIMIT, notification_page
from kanban.models import Kanban, KanbanActivity
from tasks.models import Task, TaskActivity
from workplaces.models import WorkplaceInvitation, WorkplaceMembership, create_workplace_for_user


class NotificationCenterTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.owner = users.create_user(username='inbox-owner', email='inbox-owner@example.test')
        self.member = users.create_user(username='inbox-member', email='inbox-member@example.test')
        self.outsider = users.create_user(username='inbox-outsider', email='inbox-outsider@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Wspólny')
        self.other_workspace = create_workplace_for_user(self.owner, 'Prywatny')
        self.membership = WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member, role='member')
        self.task = Task.objects.create(user=self.owner, workplace=self.workspace, title='Wdrożenie')
        self.activity = TaskActivity.objects.create(task=self.task, actor=self.owner, kind='comment', action='commented', message='Gotowe do sprawdzenia')
        self.card = Kanban.objects.create(user=self.owner, workplace=self.workspace, title='Karta')
        self.kanban_activity = KanbanActivity.objects.create(task=self.card, actor=self.owner, kind='comment', action='commented', message='Komentarz do karty')
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def feed(self, **params):
        return self.client.get(reverse('notifications'), params, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def act(self, action, key=None, **params):
        return self.client.post(reverse('notification_action'), {'action': action, 'key': key or f'tasks:{self.activity.pk}', **params})

    def summary(self):
        return self.client.get(reverse('notifications'), {'summary': '1'}).json()

    def test_history_is_excluded_from_every_view_and_summary_even_with_old_deliveries(self):
        before = self.summary()
        keys = []
        for source, task in [('tasks', self.task), ('kanban', self.card)]:
            field = 'task_activity' if source == 'tasks' else 'kanban_activity'
            for index, action in enumerate(['created', 'updated', 'status_changed', 'attachments_added']):
                activity = task.activities.create(actor=self.owner, kind='system', action=action,
                                                  message='Historia nie jest powiadomieniem')
                keys.append(f'{source}:{activity.pk}')
                # Existing subscriptions and receipts cannot reintroduce old history.
                ActivityInterest.objects.create(user=self.member, **{field: activity}, followed=True, mentioned=True)
                NotificationState.objects.create(user=self.member, **{field: activity},
                                                 is_read=False, is_archived=bool(index % 2))
        for workspace in ['', str(self.workspace.pk)]:
            for view in ['all', 'unread', 'invitations', 'reminders', 'mentions', 'following', 'archived']:
                with self.subTest(workspace=workspace, view=view):
                    payload = self.feed(view=view, workspace=workspace).json()
                    self.assertEqual(payload['total'], 1 if view in {'all', 'unread'} else 0)
                    for key in keys:
                        self.assertNotIn(f'data-notification-key="{key}"', payload['html'])
        self.assertEqual(self.summary(), before)
        self.assertEqual(self.task.activities.filter(kind='system', message='Historia nie jest powiadomieniem').count(), 4)
        self.assertEqual(self.card.activities.filter(kind='system', message='Historia nie jest powiadomieniem').count(), 4)

    def test_history_cannot_be_changed_through_inbox_actions_or_bulk_snapshots(self):
        receipts = []
        for source, task in [('tasks', self.task), ('kanban', self.card)]:
            activity = task.activities.filter(kind='system').first()
            field = 'task_activity' if source == 'tasks' else 'kanban_activity'
            receipt = NotificationState.objects.create(user=self.member, **{field: activity}, is_read=False)
            receipts.append(receipt)
            for action in ['read', 'unread', 'archive', 'restore', 'delete']:
                with self.subTest(source=source, action=action):
                    self.assertEqual(self.act(action, f'{source}:{activity.pk}').status_code, 404)
        snapshot = self.feed().json()['snapshot']
        for action in ['read_all', 'delete_all']:
            self.assertEqual(self.act(action, snapshot=snapshot).status_code, 200)
            for receipt in receipts:
                receipt.refresh_from_db()
                self.assertFalse(receipt.is_read or receipt.is_archived or receipt.is_deleted)
        self.assertEqual(self.feed().json()['total'], 0)
        self.assertEqual(self.summary()['unread_count'], 0)

    def test_history_only_renders_empty_state_and_preserves_object_history(self):
        self.activity.delete()
        self.kanban_activity.delete()
        self.assertTrue(self.task.activities.filter(kind='system').exists())
        self.assertTrue(self.card.activities.filter(kind='system').exists())
        for user in [self.member, self.owner]:
            self.client.force_login(user)
            payload = self.feed().json()
            self.assertEqual(payload['total'], 0)
            self.assertEqual(payload['unread_count'], 0)
            self.assertIn('Brak nowych powiadomień.', payload['html'])
            self.assertIn('Zaproszenia, komentarze, wzmianki i przypomnienia', payload['html'])

    def test_opening_is_read_only_and_own_actions_do_not_count_as_unread(self):
        self.assertEqual(self.summary()['unread_count'], 1)
        self.feed()
        self.assertFalse(NotificationState.objects.exists())
        self.client.force_login(self.owner)
        self.assertEqual(self.summary()['unread_count'], 0)
        self.assertIn('Wdrożenie', self.feed().json()['html'])
        self.act('unread')
        self.assertEqual(self.summary()['unread_count'], 1)

    def test_partial_navigation_to_retired_page_redirects_home(self):
        response = self.client.get(reverse('notifications'), HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_ACCEPT='text/html')
        self.assertRedirects(response, reverse('home'))

    def test_read_state_is_persistent_idempotent_and_personal(self):
        for _ in range(2):
            self.assertEqual(self.act('read').status_code, 200)
        self.assertEqual(NotificationState.objects.count(), 1)
        self.assertEqual(self.summary()['unread_count'], 0)
        self.client.force_login(self.member)
        self.assertNotIn('Gotowe do sprawdzenia', self.feed(view='unread').json()['html'])
        self.act('unread')
        self.assertIn('Gotowe do sprawdzenia', self.feed(view='unread').json()['html'])
        self.assertFalse(NotificationState.objects.filter(user=self.owner).exists())

    def test_archive_and_restore_do_not_remove_activity(self):
        self.assertEqual(self.act('archive').status_code, 200)
        self.assertNotIn('Gotowe do sprawdzenia', self.feed().json()['html'])
        self.assertIn('Gotowe do sprawdzenia', self.feed(view='archived').json()['html'])
        self.assertEqual(self.summary()['unread_count'], 0)
        self.assertTrue(TaskActivity.objects.filter(pk=self.activity.pk).exists())
        self.assertEqual(self.act('restore').status_code, 200)
        self.assertIn('Gotowe do sprawdzenia', self.feed().json()['html'])
        self.assertEqual(self.summary()['unread_count'], 0)

    def test_foreign_records_revoked_access_and_owner_mismatch_are_rejected(self):
        foreign = Task.objects.create(user=self.owner, workplace=self.other_workspace, title='Tajne')
        corrupt = Task.objects.create(user=self.outsider, workplace=self.workspace, title='Nieprawidłowy właściciel')
        for task in (foreign, corrupt):
            activity = TaskActivity.objects.create(task=task, actor=self.owner, kind='comment', action='commented')
            self.assertEqual(self.act('read', f'tasks:{activity.pk}').status_code, 404)
        self.assertNotIn('Tajne', self.feed().json()['html'])
        self.assertNotIn('Nieprawidłowy właściciel', self.feed().json()['html'])
        self.act('read')
        self.membership.is_active = False
        self.membership.save(update_fields=['is_active'])
        self.assertEqual(self.summary()['unread_count'], 0)
        self.assertEqual(self.act('unread').status_code, 404)
        self.assertNotIn('Wdrożenie', self.feed().json()['html'])

    def test_workspace_filter_checks_membership(self):
        self.assertIn('Wdrożenie', self.feed(workspace=self.workspace.pk).json()['html'])
        for workspace in (self.other_workspace.pk, 'bad', '9' * 100):
            self.assertEqual(self.feed(workspace=workspace).status_code, 404)
        self.assertEqual(self.feed(view='invalid').status_code, 400)

    def test_invitation_read_is_separate_from_decision_and_cannot_be_archived(self):
        invitation = WorkplaceInvitation.objects.create(workplace=self.other_workspace, invited_by=self.owner, recipient=self.member)
        key = f'workplace:{invitation.pk}'
        self.assertEqual(self.feed(view='invitations').json()['count'], 1)
        self.assertEqual(self.act('read', key).status_code, 200)
        self.assertEqual(self.summary()['pending_invitation_count'], 1)
        self.assertEqual(self.act('archive', key).status_code, 400)
        self.assertFalse(WorkplaceMembership.objects.filter(workplace=self.other_workspace, user=self.member).exists())
        invitation.expires_at = timezone.now() - timedelta(seconds=1)
        invitation.save(update_fields=['expires_at'])
        self.assertEqual(self.act('read', key).status_code, 404)
        self.assertEqual(self.feed(view='invitations').json()['count'], 0)

    def test_foreign_invitation_and_invalid_keys_rejected(self):
        invitation = WorkplaceInvitation.objects.create(workplace=self.workspace, invited_by=self.owner, recipient=self.outsider)
        for key in (f'workplace:{invitation.pk}', 'tasks:0', 'tasks:abc', 'tasks:' + '9' * 100, 'users:1'):
            self.assertEqual(self.act('read', key).status_code, 404)
        self.assertEqual(self.act('invalid-action').status_code, 400)

    def test_delete_is_personal_persistent_idempotent_and_preserves_sources(self):
        original_total = self.feed().json()['total']
        for key in (f'tasks:{self.activity.pk}',):
            for _ in range(2):
                self.assertEqual(self.act('delete', key).status_code, 200)
            for action in ('read', 'unread', 'archive', 'restore'):
                self.assertEqual(self.act(action, key).status_code, 404)
        self.client.force_login(self.member)
        self.assertEqual(self.feed().json()['total'], original_total - 1)
        self.assertEqual(self.feed(view='archived').json()['total'], 0)
        self.assertEqual(self.summary()['unread_count'], 0)
        self.assertTrue(TaskActivity.objects.filter(pk=self.activity.pk).exists())
        self.assertTrue(KanbanActivity.objects.filter(pk=self.kanban_activity.pk).exists())
        self.client.force_login(self.owner)
        self.assertIn(f'data-notification-key="tasks:{self.activity.pk}"', self.feed().json()['html'])
        self.assertFalse(NotificationState.objects.filter(user=self.owner).exists())

    def test_deleted_invitation_remains_available_in_workspace(self):
        invitation = WorkplaceInvitation.objects.create(workplace=self.other_workspace, invited_by=self.owner, recipient=self.member)
        self.assertEqual(self.act('delete', f'workplace:{invitation.pk}').status_code, 200)
        self.assertEqual(self.feed(view='invitations').json()['total'], 0)
        self.assertEqual(self.summary()['pending_invitation_count'], 0)
        page = self.client.get(reverse('home'))
        self.assertEqual(page.context['pending_workspace_invitation_count'], 1)
        self.assertEqual(page.context['pending_notification_invitation_count'], 0)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'pending')
        self.assertFalse(WorkplaceMembership.objects.filter(workplace=self.other_workspace, user=self.member).exists())
        response = self.client.get(reverse('workplaces:workplaces'), {'invitation': invitation.pk})
        self.assertEqual(response.context['response_invitation'], invitation)

    def test_delete_rechecks_access_and_rejects_foreign_keys(self):
        foreign = Task.objects.create(user=self.owner, workplace=self.other_workspace, title='Prywatne')
        foreign_comment = foreign.activities.create(actor=self.owner, kind='comment', action='commented')
        invitation = WorkplaceInvitation.objects.create(workplace=self.workspace, invited_by=self.owner, recipient=self.outsider)
        for key in (f'tasks:{foreign_comment.pk}', f'workplace:{invitation.pk}', 'tasks:bad', 'tasks:' + '9' * 100):
            self.assertEqual(self.act('delete', key).status_code, 404)
        snapshot = self.feed(workspace=self.workspace.pk).json()['snapshot']
        self.membership.is_active = False
        self.membership.save(update_fields=['is_active'])
        self.assertEqual(self.act('delete').status_code, 404)
        self.assertEqual(self.act('delete_all', snapshot=snapshot).status_code, 404)
        self.assertFalse(NotificationState.objects.filter(user=self.member).exists())

    def test_bulk_delete_covers_all_pages_but_preserves_archived_and_new_items(self):
        self.act('archive')
        TaskActivity.objects.bulk_create([TaskActivity(task=self.task, actor=self.owner, kind='comment', action='commented', message=f'Komentarz {i}') for i in range(505)])
        payload = self.feed(workspace=self.workspace.pk).json()
        self.assertGreater(payload['total'], 500)
        new = TaskActivity.objects.create(task=self.task, actor=self.owner, kind='comment', action='commented', message='Nowsze niż lista')
        for _ in range(2):
            self.assertEqual(self.act('delete_all', snapshot=payload['snapshot']).status_code, 200)
        self.assertEqual(NotificationState.objects.filter(user=self.member, is_deleted=True).count(), payload['total'])
        self.assertEqual(self.feed().json()['total'], 1)
        self.assertEqual(self.summary()['unread_count'], 1)
        self.assertFalse(NotificationState.objects.filter(user=self.member, task_activity=new).exists())
        self.assertEqual(self.feed(view='archived').json()['total'], 1)
        archived = self.feed(view='archived').json()
        self.assertEqual(self.act('delete_all', snapshot=archived['snapshot']).status_code, 200)
        self.assertEqual(self.feed(view='archived').json()['total'], 0)
        self.assertTrue(TaskActivity.objects.filter(pk=self.activity.pk).exists())

    def test_bulk_delete_respects_workspace_and_validates_snapshot(self):
        second = create_workplace_for_user(self.member, 'Osobiste')
        task = Task.objects.create(user=self.member, workplace=second, title='Pozostawione')
        task.activities.create(actor=self.member, kind='comment', action='commented', message='Komentarz w drugim Workspace')
        payload = self.feed(workspace=self.workspace.pk).json()
        self.assertEqual(self.act('delete_all', snapshot='invalid').status_code, 400)
        self.client.force_login(self.outsider)
        self.assertEqual(self.act('delete_all', snapshot=payload['snapshot']).status_code, 400)
        self.client.force_login(self.member)
        self.assertEqual(self.act('delete_all', snapshot=payload['snapshot']).status_code, 200)
        self.assertIn('Pozostawione', self.feed().json()['html'])
        self.assertFalse(NotificationState.objects.filter(user=self.member, task_activity__task=task).exists())
        self.assertEqual(self.act('read_all', snapshot=payload['snapshot']).status_code, 200)
        self.assertNotIn('Wdrożenie', self.feed().json()['html'])

    def test_bulk_read_includes_invitation_without_accepting_it(self):
        invitation = WorkplaceInvitation.objects.create(workplace=self.other_workspace, invited_by=self.owner, recipient=self.member)
        payload = self.feed().json()
        self.assertEqual(self.act('read_all', snapshot=payload['snapshot']).status_code, 200)
        self.assertEqual(self.summary()['unread_count'], 0)
        self.assertEqual(self.summary()['pending_invitation_count'], 1)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'pending')

    def test_bulk_read_uses_snapshot_and_filters_and_preserves_new_arrivals(self):
        payload = self.feed(workspace=self.workspace.pk).json()
        new = TaskActivity.objects.create(task=self.task, actor=self.owner, kind='comment', action='commented', message='Nowa wiadomość')
        self.assertEqual(self.act('read_all', snapshot=payload['snapshot']).status_code, 200)
        self.assertEqual(self.summary()['unread_count'], 1)
        self.assertFalse(NotificationState.objects.filter(user=self.member, task_activity=new).exists())
        self.assertEqual(self.act('read_all', snapshot=payload['snapshot']).status_code, 200)
        self.assertEqual(self.summary()['unread_count'], 1)
        self.assertEqual(self.act('read_all', snapshot='invalid').status_code, 400)
        self.client.force_login(self.outsider)
        self.assertEqual(self.act('read_all', snapshot=payload['snapshot']).status_code, 400)

    def test_bulk_read_handles_more_than_one_page(self):
        TaskActivity.objects.bulk_create([TaskActivity(task=self.task, actor=self.owner, kind='comment', action='commented', message=f'Komentarz {i}') for i in range(30)])
        payload = self.feed(view='unread').json()
        self.assertEqual(payload['count'], DASHBOARD_NOTIFICATION_LIMIT)
        self.assertEqual(payload['total'], 31)
        self.assertEqual(self.act('read_all', snapshot=payload['snapshot']).status_code, 200)
        self.assertEqual(self.summary()['unread_count'], 0)

    def test_bulk_does_not_change_archived_or_other_workspace_items(self):
        self.act('archive')
        self.client.force_login(self.owner)
        private_task = Task.objects.create(user=self.owner, workplace=self.other_workspace, title='Druga przestrzeń')
        private_activity = TaskActivity.objects.create(task=private_task, actor=self.outsider, kind='comment', action='commented', message='Prywatny komentarz')
        payload = self.feed(workspace=self.workspace.pk).json()
        self.act('read_all', snapshot=payload['snapshot'])
        self.assertFalse(NotificationState.objects.filter(user=self.owner, task_activity=private_activity).exists())
        self.assertTrue(NotificationState.objects.get(user=self.member, task_activity=self.activity).is_archived)

    def test_cursor_pagination_is_stable_with_equal_timestamps_and_new_arrivals(self):
        TaskActivity.objects.bulk_create([TaskActivity(task=self.task, actor=self.owner, kind='comment', action='commented', message=f'Komentarz {i}') for i in range(25)])
        TaskActivity.objects.bulk_create([TaskActivity(task=self.task, actor=self.owner, kind='system', message=f'Historia {i}') for i in range(30)])
        moment = timezone.now() - timedelta(days=1)
        TaskActivity.objects.filter(task=self.task).update(created_at=moment)
        KanbanActivity.objects.filter(task=self.card).update(created_at=moment)
        filters = {'view': 'all', 'workspace': ''}
        first = notification_page(self.member, filters)
        new = TaskActivity.objects.create(task=self.task, actor=self.owner, kind='comment', action='commented', message='Po otwarciu')
        seen = [item['key'] for item in first['dashboard_notifications']]
        cursor = first['next_cursor']
        while cursor:
            page = notification_page(self.member, filters, cursor)
            seen.extend(item['key'] for item in page['dashboard_notifications'])
            cursor = page['next_cursor']
        self.assertEqual(len(seen), 26)
        self.assertEqual(len(seen), len(set(seen)))
        self.assertNotIn(f'tasks:{new.pk}', seen)
        self.assertEqual(self.feed(cursor='bad').status_code, 400)
        self.assertEqual(self.feed(cursor=first['next_cursor'], view='unread').status_code, 400)

    def test_invitations_paginate_before_activity(self):
        for i in range(14):
            workspace = create_workplace_for_user(self.owner, f'Zapraszający {i}')
            WorkplaceInvitation.objects.create(workplace=workspace, invited_by=self.owner, recipient=self.member)
        filters = {'view': 'all', 'workspace': ''}
        first = notification_page(self.member, filters)
        self.assertTrue(all(item['source'] == 'workplace' for item in first['dashboard_notifications']))
        second = notification_page(self.member, filters, first['next_cursor'])
        self.assertEqual([item['source'] for item in second['dashboard_notifications'][:2]], ['workplace', 'workplace'])
        self.assertEqual(len(second['dashboard_notifications']), 3)

    def test_deleted_source_cleans_receipt(self):
        self.act('read')
        self.activity.delete()
        self.assertFalse(NotificationState.objects.exists())

    def test_receipt_constraints_require_one_unique_source(self):
        for values in ({}, {'task_activity': self.activity, 'kanban_activity': self.kanban_activity}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                NotificationState.objects.create(user=self.member, **values)
        self.act('read')
        with self.assertRaises(IntegrityError), transaction.atomic():
            NotificationState.objects.create(user=self.member, task_activity=self.activity)

    def test_html_escapes_content_and_links_include_stable_pk_and_workspace(self):
        self.activity.message = '<script>alert("x")</script>'
        self.activity.save(update_fields=['message'])
        html = self.feed().json()['html']
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn(f'?task_pk={self.task.pk}', html)
        self.assertIn(f'/workplaces/{self.workspace.slug}/tasks/', html)

    def test_writes_require_post_authentication_and_csrf(self):
        url = reverse('notification_action')
        self.assertEqual(self.client.get(url).status_code, 405)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.member)
        self.assertEqual(protected.post(url, {'action': 'read', 'key': f'tasks:{self.activity.pk}'}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.act('read').status_code, 302)
        self.assertEqual(self.feed().status_code, 302)
