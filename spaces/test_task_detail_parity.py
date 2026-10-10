"""Behavior behind the shared issue UI, scoped entirely to SpaceTask."""
import json
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from dashboard.notification_service import notification_filters, notification_page, notification_sources, change_notification_state
from tasks.models import Task
from . import test_independent_tasks as fixtures
from .models import SpaceTask, SpaceTaskWorkLog, SpaceTaskMembership, SpaceTaskReminder


class DetailParityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.IndependentTaskTests.setUpTestData.__func__(cls)

    login = fixtures.IndependentTaskTests.login
    url = fixtures.IndependentTaskTests.url
    task_url = fixtures.IndependentTaskTests.task_url
    data = fixtures.IndependentTaskTests.data

    def setUp(self):
        self.login(self.owner)

    def log_data(self, action='add_work_log', **extra):
        return {'action': action, 'worklog-calculation_mode': 'duration', 'worklog-hours': '1', 'worklog-minutes': '15', 'worklog-description': 'Wykonana praca', **extra}

    def test_all_tabs_use_shared_components_and_sidebar_fields(self):
        for tab in ['main', 'subtasks', 'work-log', 'members', 'history']:
            response = self.client.get(self.task_url('?tab=' + tab))
            self.assertContains(response, 'role="tabpanel"')
            self.assertContains(response, 'data-task-tab="' + tab + '"')
            self.assertContains(response, 'Kategoria zadania')
            self.assertContains(response, 'Przypomnienie')
            self.assertContains(response, 'tasks-subtasks-toolbar')
            self.assertContains(response, 'tasks-work-log-summary')
            self.assertContains(response, 'workplace-team-sheet')
            self.assertContains(response, 'tasks-issue-feed-item')
            self.assertNotContains(response, '<summary>Planowanie</summary>')
        self.assertFalse(Task.objects.filter(title=self.task.title).exists())

    def test_category_reminder_and_history_save_in_own_domain(self):
        reminder = timezone.now().replace(second=0, microsecond=0) + timedelta(hours=1)
        response = self.client.post(self.task_url('?tab=history'), self.data(task_type='meeting', reminder_at=reminder.isoformat()))
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.task_type, 'meeting')
        self.assertEqual(self.task.reminder_at, reminder)
        changes = self.task.activities.filter(action='updated').get().metadata['changes']
        self.assertIn('kategoria zadania', [change['field'] for change in changes])
        reminder_change = next(change for change in changes if change['field'] == 'przypomnienie')
        self.assertEqual(reminder_change['from_label'], '—')
        self.assertEqual(reminder_change['to_label'], timezone.localtime(reminder).strftime('%d.%m.%Y %H:%M'))

    def test_inline_visibility_uses_owner_permissions_and_preserves_private_children(self):
        child = SpaceTask.objects.create(space=self.space, parent=self.task, title='Private child', created_by=self.owner, visibility='private', private_owner=self.owner)
        SpaceTaskMembership.objects.create(task=child, user=self.member)
        self.assertEqual(self.client.post(self.task_url(), self.data(visibility='private')).status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.private_owner, self.owner)
        SpaceTaskMembership.objects.create(task=self.task, user=self.member, role='admin')
        self.login(self.member)
        self.assertEqual(self.client.post(self.task_url(), self.data(visibility='public')).status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.visibility, 'private')
        self.login(self.owner)
        self.assertEqual(self.client.post(self.task_url(), self.data(visibility='public')).status_code, 302)
        self.assertFalse(self.task.memberships.exists())
        self.assertTrue(child.memberships.filter(user=self.member).exists())

    def test_malformed_action_ids_return_not_found(self):
        for action in ['edit_work_log', 'delete_work_log']:
            self.assertEqual(self.client.post(self.task_url(), self.log_data(action, work_log_id='bad')).status_code, 404)
        self.assertEqual(self.client.post(self.task_url('team/'), {'action': 'remove', 'member_id': 'bad'}).status_code, 404)

    def test_subtask_modal_preserves_parent_context_and_properties(self):
        response = self.client.post(self.task_url('?tab=subtasks&view=backlog'), {'action': 'create_subtask_modal', 'subtask-title': 'Podzadanie modal', 'subtask-description': 'Opis', 'subtask-status': 'in_progress', 'subtask-visibility': 'private'})
        self.assertEqual(response.status_code, 302)
        child = self.task.subtasks.get()
        self.assertEqual(child.status, 'in_progress')
        self.assertEqual(child.private_owner, self.owner)
        self.assertEqual(child.work_item.status, 'in_progress')
        self.assertEqual(child.description, 'Opis')
        self.assertEqual(response.url, self.task_url('?tab=subtasks&view=backlog'))
        self.assertFalse(Task.objects.filter(title=child.title).exists())

    def test_invalid_subtask_preserves_draft_and_opens_modal(self):
        response = self.client.post(self.task_url('?tab=subtasks'), {'action': 'create_subtask_modal', 'subtask-title': '', 'subtask-description': 'Szkic', 'subtask-status': 'bad', 'subtask-visibility': 'public'})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.context['subtask_modal_open'])
        self.assertEqual(response.context['subtask_form']['description'].value(), 'Szkic')
        self.assertFalse(self.task.subtasks.exists())

    def test_subtask_bulk_delete_enforces_descendant_acl_and_scope(self):
        child = SpaceTask.objects.create(space=self.space, parent=self.task, title='Child', created_by=self.owner)
        unrelated = SpaceTask.objects.create(space=self.space, title='Other', created_by=self.owner)
        response = self.client.post(self.task_url(), {'action': 'delete_subtasks', 'subtask_ids': [child.pk, unrelated.pk]})
        self.assertEqual(response.status_code, 404)
        self.assertTrue(SpaceTask.objects.filter(pk=child.pk).exists())
        self.login(self.observer)
        self.assertEqual(self.client.post(self.task_url(), {'action': 'delete_subtasks', 'subtask_ids': [child.pk]}).status_code, 403)
        self.login(self.owner)
        self.assertEqual(self.client.post(self.task_url(), {'action': 'delete_subtasks', 'subtask_ids': [child.pk]}).status_code, 302)
        self.assertFalse(SpaceTask.objects.filter(pk=child.pk).exists())

    def test_time_entry_create_edit_delete_returns_shared_list_and_history(self):
        response = self.client.post(self.task_url(), self.log_data(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertIn('tasks-work-log-sheet', response.json()['work_log_html'])
        entry = self.task.work_logs.get()
        self.assertEqual(entry.duration_minutes, 75)
        self.assertEqual(entry.author, self.owner)
        response = self.client.post(self.task_url(), self.log_data('edit_work_log', work_log_id=entry.pk, **{'worklog-hours': '2'}), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.duration_minutes, 135)
        response = self.client.post(self.task_url(), {'action': 'delete_work_log', 'work_log_id': entry.pk}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Brak wpisów w dzienniku pracy', response.json()['work_log_html'])
        self.assertFalse(SpaceTaskWorkLog.objects.exists())
        self.assertEqual(self.task.activities.filter(action__startswith='work_log_').count(), 3)

    def test_time_entry_invalid_duration_and_cross_task_edit(self):
        response = self.client.post(self.task_url(), self.log_data(**{'worklog-minutes': '60'}), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        self.assertIn('form_html', response.json())
        self.assertFalse(SpaceTaskWorkLog.objects.exists())
        other = SpaceTask.objects.create(space=self.space, title='Other', created_by=self.owner)
        now = timezone.now()
        entry = SpaceTaskWorkLog.objects.create(task=other, author=self.owner, started_at=now, ended_at=now+timedelta(hours=1), description='Other')
        self.assertEqual(self.client.post(self.task_url(), self.log_data('edit_work_log', work_log_id=entry.pk)).status_code, 404)
        self.login(self.observer)
        self.assertEqual(self.client.post(self.task_url(), self.log_data()).status_code, 403)

    def test_work_log_totals_and_pagination(self):
        now = timezone.now().replace(second=0, microsecond=0)
        SpaceTaskWorkLog.objects.bulk_create([SpaceTaskWorkLog(task=self.task, author=self.owner, started_at=now, ended_at=now+timedelta(minutes=10), description=str(index)) for index in range(26)])
        response = self.client.get(self.task_url('?view=backlog&tab=work-log&work_log_page=2'))
        self.assertEqual(response.context['work_log_total_minutes'], 260)
        self.assertEqual(len(response.context['work_log_page']), 1)
        self.assertIn('view=backlog', response.context['work_log_previous_url'])

    def test_member_table_inherited_and_private_roles_share_remove(self):
        response = self.client.get(self.task_url('team/'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Właściciel', response.json()['members'])
        self.assertIn('Obserwator', response.json()['members'])
        self.task.visibility, self.task.private_owner = 'private', self.owner
        self.task.save()
        url = self.task_url('team/')
        response = self.client.post(url, {'action': 'share', 'email': self.member.email, 'role': 'observer'})
        self.assertEqual(response.status_code, 200)
        member = self.task.memberships.get()
        self.assertEqual(member.role, 'observer')
        self.assertEqual(self.client.post(url, {'action': 'role', 'member_id': member.pk, 'role': 'admin'}).status_code, 200)
        member.refresh_from_db()
        self.assertEqual(member.role, 'admin')
        self.assertEqual(self.client.post(url, {'action': 'remove', 'member_id': member.pk}).status_code, 200)
        self.assertFalse(self.task.memberships.exists())

    def test_member_observer_cannot_grant_and_public_share_is_rejected(self):
        self.assertEqual(self.client.post(self.task_url('team/'), {'action': 'share', 'email': self.member.email, 'role': 'member'}).status_code, 400)
        self.assertFalse(self.task.memberships.exists())
        self.login(self.observer)
        self.assertEqual(self.client.post(self.task_url('team/'), {'action': 'share', 'email': self.member.email, 'role': 'member'}).status_code, 403)
        self.assertEqual(self.client.get(self.task_url('team/candidates/?q=member')).status_code, 403)

    def test_admin_cannot_change_or_remove_another_admin(self):
        self.task.visibility, self.task.private_owner = 'private', self.owner
        self.task.save()
        admin = SpaceTaskMembership.objects.create(task=self.task, user=self.member, role='admin')
        self.login(self.member)
        self.assertEqual(self.client.post(self.task_url('team/'), {'action': 'role', 'member_id': admin.pk, 'role': 'member'}).status_code, 403)
        self.assertEqual(self.client.post(self.task_url('team/'), {'action': 'remove', 'member_id': admin.pk}).status_code, 403)
        ordinary = SpaceTaskMembership.objects.create(task=self.task, user=self.observer, role='member')
        self.assertEqual(self.client.post(self.task_url('team/'), {'action': 'role', 'member_id': ordinary.pk, 'role': 'observer'}).status_code, 200)
        ordinary.refresh_from_db()
        self.assertEqual(ordinary.role, 'observer')
        self.assertEqual(self.client.post(self.task_url('team/'), {'action': 'role', 'member_id': ordinary.pk, 'role': 'admin'}).status_code, 403)

    def test_reminders_deliver_once_to_visible_recipient_and_withdraw(self):
        self.task.reminder_at = timezone.now()-timedelta(minutes=1)
        self.task.save()
        self.assertEqual(notification_sources(self.owner)['space-reminders'].count(), 1)
        self.assertEqual(notification_sources(self.owner)['space-reminders'].count(), 1)
        self.assertEqual(SpaceTaskReminder.objects.count(), 1)
        page = notification_page(self.owner, notification_filters(self.owner, {'view': 'reminders'}))
        self.assertIn('/space/scrum-szablon/tasks/SZ-1/', page['dashboard_notifications'][0]['url'])
        change_notification_state(self.owner, {'key': 'space-reminders:' + str(SpaceTaskReminder.objects.get().pk), 'action': 'read'})
        self.task.status = 'closed'
        self.task.save()
        self.assertFalse(notification_sources(self.owner)['space-reminders'].exists())

    def test_mentions_use_shared_picker_and_enforce_access(self):
        label = '@' + (self.member.get_full_name() or self.member.username).lstrip('@')
        metadata = [{'user_id': self.member.pk, 'start': 0, 'end': len(label)}]
        response = self.client.post(self.task_url(), {'action': 'comment', 'activity_comment': label + ' sprawdź', 'activity_mentions': json.dumps(metadata)})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(notification_sources(self.member)['spaces'].filter(inbox_mentioned=True).count(), 1)
        from .models import SpaceMembership
        SpaceMembership.objects.filter(space=self.space, user=self.member).delete()
        self.assertFalse(notification_sources(self.member)['spaces'].exists())
