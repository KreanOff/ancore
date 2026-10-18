"""Selected-name mentions on current Space tasks and their personal inbox state."""
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import Client, TestCase

from spaces.models import SpaceTaskActivity
from spaces.testing import make_task
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .notification_service import change_notification_state, notification_page


class CollaborationTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.owner = users.create_user(username='owner', email='owner@example.test')
        self.member = users.create_user(username='żaneta.kowalska', email='member@example.test', first_name='Żaneta')
        self.outsider = users.create_user(username='outside', email='outside@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Zespół')
        self.membership = WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
        self.task = make_task(user=self.owner, workplace=self.workspace, title='Zadanie')
        self.login(self.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, scoped=True):
        suffix = f'{self.task.space.slug}/tasks/{self.task.work_item.key}/'
        return scoped_workplace_app_path(self.workspace, 'space', suffix) if scoped else '/space/' + suffix

    def comment(self, text='Hej @Żaneta!', entries=None, scoped=True):
        if entries is None:
            entries = [{'user_id': self.member.pk, 'start': 4, 'end': 11}]
        response = self.client.post(self.url(scoped), {'action': 'comment', 'activity_comment': text,
            'activity_mentions': json.dumps(entries)})
        self.assertEqual(response.status_code, 302)
        return self.task.activities.filter(kind='comment').latest('pk')

    def page(self, view='mentions', user=None, **filters):
        return notification_page(user or self.member, {'view': view, 'workspace': '', **filters})

    def test_mentions_are_personal_and_reuse_the_comment_notification(self):
        event = self.comment()
        self.assertEqual(event.metadata['mentions'][0]['user_id'], self.member.pk)
        items = self.page()['dashboard_notifications']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['event_label'], 'Wzmianka')
        self.assertEqual(items[0]['url'], self.url() + '?view=list')
        self.assertEqual(self.page(user=self.owner)['dashboard_notification_count'], 0)
        self.assertEqual(self.page(user=self.outsider)['dashboard_notification_count'], 0)
        self.assertEqual(sum(item['key'] == f'spaces:{event.pk}' for item in self.page('all')['dashboard_notifications']), 1)

    def test_unselected_handles_and_email_substrings_do_not_create_mentions(self):
        for text in ['@żaneta.kowalska', '@Żaneta', 'mail@żaneta.kowalska', '@żaneta.kowalska.extra']:
            self.comment(text, [])
        self.assertEqual(self.page()['dashboard_notification_count'], 0)

    def test_public_ancore_ids_and_picker_labels_keep_one_prefix(self):
        self.member.username, self.member.first_name, self.member.last_name = '@anna.kowalska', 'Anna', 'Kowalska'
        self.member.save()
        for scoped in (False, True):
            response = self.client.get(self.url(scoped))
            person = next(person for person in response.context['mention_people'] if person['id'] == self.member.pk)
            self.assertEqual(person['mention'], '@Anna Kowalska')
            self.assertEqual(person['email'], self.member.email)
            self.comment('Proszę @Anna Kowalska, sprawdź.', [{'user_id': self.member.pk, 'start': 7, 'end': 21}], scoped)
        self.assertEqual(self.page()['dashboard_notification_count'], 2)

    def test_username_fallback_keeps_a_single_prefix(self):
        self.member.first_name = ''
        self.member.username = '@anna'
        self.member.save()
        person = next(person for person in self.client.get(self.url()).context['mention_people'] if person['id'] == self.member.pk)
        self.assertEqual(person['mention'], '@anna')
        self.comment('@anna', [{'user_id': self.member.pk, 'start': 0, 'end': 5}])
        self.assertEqual(self.page()['dashboard_notification_count'], 1)

    def test_selected_name_notifies_only_selected_account_with_duplicate_names(self):
        twin = get_user_model().objects.create_user(username='twin', email='twin@example.test', first_name='Żaneta')
        WorkplaceMembership.objects.create(workplace=self.workspace, user=twin)
        event = self.comment()
        self.assertEqual([entry['user_id'] for entry in event.metadata['mentions']], [self.member.pk])
        self.assertEqual(self.page(user=twin)['dashboard_notification_count'], 0)

    def test_offsets_handle_unicode_newlines_and_trimmed_text(self):
        event = self.comment('  🙂\r\n@Żaneta  ', [{'user_id': self.member.pk, 'start': 4, 'end': 11}])
        self.assertEqual(event.message, '🙂\n@Żaneta')
        self.assertEqual(event.metadata['mentions'][0]['start'], 2)
        self.assertEqual(self.page()['dashboard_notification_count'], 1)

    def test_invalid_foreign_and_removed_mentions_are_rejected(self):
        self.outsider.first_name = 'Żaneta'
        self.outsider.save()
        for text, entries in [
            ('@Żaneta', [{'user_id': self.outsider.pk, 'start': 0, 'end': 7}]),
            ('Usunięta wzmianka', [{'user_id': self.member.pk, 'start': 0, 'end': 7}]),
            ('@Żaneta', [{'user_id': self.member.pk, 'start': -1, 'end': 7}]),
            ('@Żaneta', {'user_id': self.member.pk}),
            ('@Żaneta', [{'user_id': True, 'start': 0, 'end': 7}]),
        ]:
            self.assertEqual(self.comment(text, entries).metadata['mentions'], [])
        self.assertEqual(self.page()['dashboard_notification_count'], 0)

    def test_selected_name_does_not_mention_another_legacy_handle(self):
        other = get_user_model().objects.create_user(username='Żaneta', email='handle@example.test')
        WorkplaceMembership.objects.create(workplace=self.workspace, user=other)
        self.comment()
        self.assertEqual(self.page()['dashboard_notification_count'], 1)
        self.assertEqual(self.page(user=other)['dashboard_notification_count'], 0)

    def test_inactive_and_revoked_members_are_absent_from_mentions(self):
        self.member.is_active = False
        self.member.save()
        self.assertEqual(self.comment().metadata['mentions'], [])
        self.member.is_active = True
        self.member.save()
        self.membership.is_active = False
        self.membership.save()
        self.assertEqual(self.comment().metadata['mentions'], [])
        self.assertEqual(self.page()['dashboard_notification_count'], 0)

    def test_revocation_removes_access_to_existing_comment_and_receipt(self):
        event = self.comment()
        self.membership.delete()
        self.assertEqual(self.page()['dashboard_notification_count'], 0)
        with self.assertRaises(Http404):
            change_notification_state(self.member, {'action': 'read', 'key': f'spaces:{event.pk}'})
        self.login(self.member)
        self.assertEqual(self.client.get(self.url()).status_code, 302)

    def test_private_task_limits_picker_and_mentions_to_its_members(self):
        self.task.visibility, self.task.private_owner = 'private', self.owner
        self.task.save()
        self.assertEqual(self.comment().metadata['mentions'], [])
        self.task.memberships.create(user=self.member)
        self.assertEqual(self.comment().metadata['mentions'][0]['user_id'], self.member.pk)
        self.assertEqual(self.page()['dashboard_notification_count'], 1)

    def test_comment_failure_rolls_back_history_and_mentions(self):
        original = SpaceTaskActivity.save
        def fail_comment(instance, *args, **kwargs):
            if instance.kind == 'comment':
                raise RuntimeError('Comment unavailable')
            return original(instance, *args, **kwargs)
        with patch.object(SpaceTaskActivity, 'save', fail_comment), self.assertRaises(RuntimeError):
            self.comment()
        self.assertFalse(self.task.activities.exclude(action='created').exists())
        self.assertEqual(self.page()['dashboard_notification_count'], 0)

    def test_filters_pagination_and_bulk_read_preserve_personal_state(self):
        for index in range(15):
            self.comment(f'Hej @Żaneta! {index}')
        first = self.page()
        second = notification_page(self.member, {'view': 'mentions', 'workspace': ''}, first['next_cursor'])
        self.assertEqual(len(first['dashboard_notifications']) + len(second['dashboard_notifications']), 15)
        change_notification_state(self.member, {'action': 'read_all', 'snapshot': first['snapshot']})
        self.assertEqual(self.page()['filtered_unread_count'], 0)
        self.assertEqual(self.page(workspace=str(self.workspace.pk))['dashboard_notification_count'], 15)
        self.comment()
        self.assertEqual(self.page()['filtered_unread_count'], 1)

    def test_comment_requires_csrf_and_removed_follow_routes_stay_closed(self):
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.member)
        self.assertEqual(protected.post(self.url(), {'action': 'comment', 'message': 'CSRF'}).status_code, 403)
        self.assertFalse(self.task.activities.exclude(action='created').exists())
        for app in ('tasks', 'kanban'):
            for scoped in (False, True):
                prefix = f'/workplaces/{self.workspace.slug}' if scoped else ''
                self.assertEqual(self.client.post(f'{prefix}/{app}/follow/task/{self.task.pk}/', {'following': 'true'}).status_code, 404)
