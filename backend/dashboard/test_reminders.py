from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from spaces.models import SpaceTaskReminder
from spaces.testing import make_task
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from .models import NotificationState
from .notification_service import change_notification_state, notification_page


class SpaceTaskReminderTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='reminder-owner', email='reminder-owner@example.test')
        self.member = get_user_model().objects.create_user(username='reminder-member', email='reminder-member@example.test')
        self.other = get_user_model().objects.create_user(username='reminder-other', email='reminder-other@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Przypomnienia')
        self.membership = WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
        self.task = make_task(user=self.owner, workplace=self.workspace, assignee=self.member,
                                        title='Oddaj raport', reminder_at=timezone.now() - timedelta(minutes=1))
        self.filters = {'view': 'reminders', 'workspace': ''}

    def page(self, user=None):
        return notification_page(user or self.member, self.filters)

    def test_delivery_on_poll_is_due_personal_and_idempotent(self):
        for _ in range(2):
            items = self.page()['dashboard_notifications']
            self.assertEqual(len(items), 1)
            self.assertFalse(items[0]['is_read'])
            self.assertIn(f'/tasks/{self.task.work_item.key}/', items[0]['url'])
        self.assertEqual(SpaceTaskReminder.objects.count(), 1)
        self.assertEqual(self.page(self.owner)['dashboard_notification_count'], 0)
        self.assertEqual(self.page(self.other)['dashboard_notification_count'], 0)
        self.client.force_login(self.member)
        response = self.client.get(reverse('notifications'), {'summary': '1'})
        self.assertGreaterEqual(response.json()['unread_count'], 1)

    def test_future_reminder_appears_when_clock_reaches_it(self):
        future = timezone.now() + timedelta(hours=1)
        self.task.reminder_at = future
        self.task.save()
        self.assertEqual(self.page()['dashboard_notification_count'], 0)
        with patch('django.utils.timezone.now', return_value=future):
            self.assertEqual(self.page()['dashboard_notification_count'], 1)

    def test_deleted_reminder_stays_deleted_after_polling_but_new_schedule_is_visible(self):
        key = self.page()['dashboard_notifications'][0]['key']
        change_notification_state(self.member, {'action': 'delete', 'key': key})
        for _ in range(2):
            self.assertEqual(self.page()['dashboard_notification_count'], 0)
        self.assertEqual(SpaceTaskReminder.objects.filter(task=self.task).count(), 1)
        self.assertTrue(NotificationState.objects.get(user=self.member, space_reminder__task=self.task).is_deleted)
        self.task.reminder_at -= timedelta(minutes=1)
        self.task.save()
        item = self.page()['dashboard_notifications'][0]
        self.assertNotEqual(item['key'], key)
        self.assertFalse(item['is_read'])

    def test_unassigned_task_reminds_owner(self):
        self.task.assignee = None
        self.task.save()
        self.assertEqual(self.page()['dashboard_notification_count'], 0)
        self.assertEqual(self.page(self.owner)['dashboard_notification_count'], 1)

    def test_read_archive_and_new_schedule_are_independent(self):
        key = self.page()['dashboard_notifications'][0]['key']
        change_notification_state(self.member, {'action': 'archive', 'key': key})
        self.assertEqual(self.page()['dashboard_notification_count'], 0)
        self.assertTrue(NotificationState.objects.get(space_reminder__task=self.task).is_read)
        self.task.reminder_at -= timedelta(minutes=1)
        self.task.save()
        item = self.page()['dashboard_notifications'][0]
        self.assertNotEqual(item['key'], key)
        self.assertFalse(item['is_read'])

    def test_completion_rescheduling_reassignment_and_revocation_withdraw_stale_items(self):
        key = self.page()['dashboard_notifications'][0]['key']
        for values in [{'status': 'closed'}, {'status': 'new', 'reminder_at': None},
                       {'reminder_at': timezone.now(), 'assignee': self.other}]:
            for name, value in values.items():
                setattr(self.task, name, value)
            self.task.save()
            self.assertEqual(self.page()['dashboard_notification_count'], 0)
            with self.assertRaises(Http404):
                change_notification_state(self.member, {'action': 'read', 'key': key})
        self.assertEqual(self.page(self.other)['dashboard_notification_count'], 0)
        self.task.assignee = self.member
        self.task.save()
        self.assertEqual(self.page()['dashboard_notification_count'], 1)
        self.membership.delete()
        self.assertEqual(self.page()['dashboard_notification_count'], 0)

    def test_read_all_snapshot_does_not_mark_later_delivery(self):
        page = self.page()
        self.task.reminder_at -= timedelta(minutes=2)
        self.task.save()
        later = self.page()['dashboard_notifications'][0]
        change_notification_state(self.member, {'action': 'read_all', 'snapshot': page['snapshot']})
        self.assertFalse(self.page()['dashboard_notifications'][0]['is_read'])
        self.assertEqual(later['key'], self.page()['dashboard_notifications'][0]['key'])

    def test_workspace_filter_and_reminder_pagination(self):
        for index in range(15):
            make_task(user=self.owner, workplace=self.workspace, assignee=self.member,
                                title=f'Raport {index}', reminder_at=timezone.now() - timedelta(minutes=1))
        page = self.page()
        next_page = notification_page(self.member, self.filters, page['next_cursor'])
        keys = [item['key'] for item in page['dashboard_notifications'] + next_page['dashboard_notifications']]
        self.assertEqual(len(keys), 16)
        self.assertEqual(len(set(keys)), 16)
        other_workspace = create_workplace_for_user(self.member, 'Puste')
        empty = notification_page(self.member, dict(self.filters, workspace=str(other_workspace.pk)))
        self.assertEqual(empty['dashboard_notification_count'], 0)
