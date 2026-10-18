import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.models import NotificationState
from spaces.models import SpaceTask, SpaceTaskActivity
from spaces.testing import make_space
from workplaces.models import WorkplaceInvitation, WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class GlobalPanelsApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='panels-owner', email='panels-owner@example.test')
        cls.member = users.objects.create_user(username='panels-member', email='panels-member@example.test')
        cls.outsider = users.objects.create_user(username='panels-outsider', email='panels-outsider@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Panele wspólne')
        cls.personal = create_workplace_for_user(cls.member, 'Panele osobiste')
        cls.foreign = create_workplace_for_user(cls.outsider, 'Panele obce')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Szukana przestrzeń')
        cls.private = make_space(user=cls.owner, workplace=cls.workspace, name='Tajna przestrzeń', visibility='private', private_owner=cls.owner)
        cls.task = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='Szukane zadanie')
        cls.hidden = SpaceTask.objects.create(space=cls.private, created_by=cls.owner, title='Tajne zadanie', assignee=cls.member)
        cls.comment = SpaceTaskActivity.objects.create(task=cls.task, actor=cls.owner, kind='comment', action='commented', message='Komentarz <script>tekst</script>')
        cls.secret = SpaceTaskActivity.objects.create(task=cls.hidden, actor=cls.owner, kind='comment', message='Tajny komentarz')
        cls.invitation = WorkplaceInvitation.objects.create(workplace=cls.foreign, recipient=cls.member, invited_by=cls.outsider)

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def api(self, name='notifications', params=None, body=None, client=None, workspace=None):
        target = reverse(name)
        if params:
            from urllib.parse import urlencode
            target += '?' + urlencode(params)
        url = scoped_workplace_app_path(workspace or self.workspace, 'api', 'v1/page/')
        if body is None:
            return (client or self.client).get(url, {'url': target})
        from urllib.parse import urlencode
        return (client or self.client).post(url + '?' + urlencode({'url': target}), json.dumps(body), content_type='application/json')

    def action(self, action, key=None, **extra):
        return self.api('notification_action', body={'action': action, 'key': key or f'spaces:{self.comment.pk}', **extra})

    def test_shared_shell_bootstrap_uses_scoped_api_and_legacy_handlers_are_not_loaded(self):
        for route in (reverse('profile'), scoped_workplace_app_path(self.workspace, 'spaces'), scoped_workplace_app_path(self.workspace, 'resources')):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-react-global-panels')
                self.assertContains(response, 'ancore-global-panels-data')
                self.assertContains(response, 'app-global-search-host')
                self.assertContains(response, 'app-sticker-host')
                self.assertContains(response, scoped_workplace_app_path(self.workspace, 'api', 'v1/page/'))
                for legacy in ('js/global-search.js', 'js/notifications-panel.js', 'js/sticky-note.js'):
                    self.assertNotContains(response, legacy)

    def test_auth_pages_do_not_mount_personal_panels(self):
        self.client.logout()
        for name in ('login', 'register'):
            self.assertNotContains(self.client.get(reverse(name)), 'data-react-global-panels')

    def test_search_and_inbox_require_session_and_actions_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        for name in ('global_search', 'notifications'):
            self.assertEqual(self.api(name, client=client).status_code, 401)
        client.force_login(self.member)
        self.assertEqual(self.api('notification_action', client=client, body={'action': 'read', 'key': f'spaces:{self.comment.pk}'}).status_code, 403)

    def test_search_keeps_workspace_and_space_acl(self):
        payload = self.api('global_search', {'q': 'Szukane'}).json()
        results = [item for group in payload['groups'] for item in group['results']]
        self.assertTrue(any(item['title'] == self.task.title for item in results))
        self.assertTrue(any(self.task.work_item.key in item['url'] for item in results))
        hidden = self.api('global_search', {'q': 'Tajne'})
        self.assertNotContains(hidden, self.hidden.title)
        self.assertNotContains(hidden, self.secret.message)
        self.assertEqual(hidden['Cache-Control'], 'no-store')

    def test_scoped_search_does_not_follow_another_tabs_active_workspace(self):
        session = self.client.session
        session['active_workplace_id'] = self.personal.pk
        session.save()
        self.assertEqual(self.api('global_search', {'q': self.task.title}).json()['workspace'], self.workspace.name)
        self.assertEqual(self.api('global_search', {'q': self.task.title}, workspace=self.personal).json()['total'], 0)

    def test_search_recent_is_rechecked_when_access_changes(self):
        self.client.get(scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/tasks/{self.task.work_item.key}/'))
        self.assertIn(self.task.title, json.dumps(self.api('global_search', {'recent': '1'}).json()))
        self.space.visibility = 'private'; self.space.private_owner = self.owner; self.space.save()
        self.assertNotIn(self.task.title, json.dumps(self.api('global_search', {'recent': '1'}).json()))

    def test_inbox_is_typed_with_same_items_and_tokens_as_legacy(self):
        typed = self.api().json()
        legacy = self.client.get(reverse('notifications'), HTTP_X_REQUESTED_WITH='XMLHttpRequest').json()
        self.assertNotIn('html', typed)
        self.assertEqual(typed['total'], legacy['total'])
        self.assertEqual(typed['unread_count'], legacy['unread_count'])
        self.assertEqual(typed['items'][0]['key'], f'workplace:{self.invitation.pk}')
        for item in typed['items']:
            self.assertIn('created_at', item)
            self.assertIn('actor_avatar', item)
            self.assertIn('details', item)
            self.assertIn(f'data-notification-key="{item["key"]}"', legacy['html'])
        self.assertTrue(typed['snapshot'])
        self.assertNotIn(f'spaces:{self.secret.pk}', [item['key'] for item in typed['items']])
        self.assertCountEqual([w['id'] for w in typed['workplaces']], [str(self.workspace.pk), str(self.personal.pk)])

    def test_foreign_workspace_filters_and_revoked_context_are_denied(self):
        self.assertEqual(self.api(params={'workspace': self.foreign.pk}).status_code, 404)
        self.membership.delete()
        self.assertEqual(self.api('global_search', {'q': 'Szukane'}).status_code, 403)
        self.assertEqual(self.api().status_code, 403)
        response = self.api(workspace=self.personal)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(f'spaces:{self.comment.pk}', [item['key'] for item in response.json()['items']])

    def test_all_filters_validate_and_mentions_use_actual_metadata(self):
        for view in ('all', 'unread', 'invitations', 'reminders', 'mentions', 'following', 'archived'):
            self.assertEqual(self.api(params={'view': view}).status_code, 200)
        self.assertEqual(self.api(params={'view': 'bad'}).status_code, 400)
        self.comment.metadata = {'mentions': [{'user_id': self.member.pk}]}; self.comment.save()
        self.assertEqual(self.api(params={'view': 'mentions'}).json()['items'][0]['key'], f'spaces:{self.comment.pk}')
        self.assertEqual(self.api(params={'view': 'following'}).json()['total'], 0)

    def test_cursor_paginates_stably_and_rejects_other_filters_and_viewers(self):
        for i in range(14):
            SpaceTaskActivity.objects.create(task=self.task, actor=self.owner, kind='comment', message=f'Komentarz {i}')
        first = self.api().json()
        second = self.api(params={'cursor': first['next_cursor']}).json()
        self.assertEqual(len(first['items']), 12)
        self.assertEqual(first['total'], 16)
        self.assertFalse(set(i['key'] for i in first['items']) & set(i['key'] for i in second['items']))
        self.assertEqual(self.api(params={'cursor': first['next_cursor'], 'view': 'unread'}).status_code, 400)
        self.client.force_login(self.owner)
        self.assertEqual(self.api(params={'cursor': first['next_cursor']}).status_code, 400)

    def test_read_archive_restore_unread_and_delete_are_personal(self):
        for action in ('read', 'unread', 'archive'):
            self.assertEqual(self.action(action).status_code, 200)
        archived = self.api(params={'view': 'archived'}).json()
        self.assertEqual(archived['items'][0]['key'], f'spaces:{self.comment.pk}')
        self.assertEqual(self.action('restore').status_code, 200)
        self.assertEqual(self.action('delete').status_code, 200)
        self.assertEqual(self.action('delete').status_code, 200)
        self.assertEqual(self.action('read').status_code, 404)
        self.assertTrue(SpaceTaskActivity.objects.filter(pk=self.comment.pk).exists())
        self.assertFalse(NotificationState.objects.filter(user=self.owner, space_activity=self.comment).exists())

    def test_private_and_history_items_cannot_be_mutated(self):
        for key in (f'spaces:{self.secret.pk}', f'spaces:{self.task.activities.filter(kind="system").first().pk}'):
            self.assertEqual(self.action('read', key=key).status_code, 404)

    def test_invitation_cannot_be_archived_or_deleted(self):
        key = f'workplace:{self.invitation.pk}'
        self.assertEqual(self.action('archive', key=key).status_code, 400)
        self.assertEqual(self.action('delete', key=key).status_code, 400)
        payload = self.api(params={'view': 'invitations'}).json()
        self.assertEqual(payload['pending_invitation_count'], 1)
        self.assertEqual(payload['deletable_count'], 0)
        self.assertEqual(payload['items'][0]['key'], key)
        self.assertTrue(WorkplaceInvitation.objects.filter(pk=self.invitation.pk, status='pending').exists())

    def test_bulk_read_snapshot_excludes_newer_items(self):
        snapshot = self.api(params={'view': 'unread'}).json()['snapshot']
        newer = SpaceTaskActivity.objects.create(task=self.task, actor=self.owner, kind='comment', message='Nowy po otwarciu')
        self.assertEqual(self.action('read_all', snapshot=snapshot).status_code, 200)
        unread = self.api(params={'view': 'unread'}).json()
        self.assertEqual([item['key'] for item in unread['items']], [f'spaces:{newer.pk}'])

    def test_bulk_delete_uses_filtered_snapshot_and_rejects_tampering(self):
        self.assertEqual(self.action('delete_all', snapshot='bad').status_code, 400)
        snapshot = self.api(params={'view': 'invitations'}).json()['snapshot']
        self.assertEqual(self.action('delete_all', snapshot=snapshot).status_code, 200)
        self.assertEqual(self.api().json()['total'], 2)
        self.assertTrue(SpaceTaskActivity.objects.filter(pk=self.comment.pk).exists())
        self.assertTrue(WorkplaceInvitation.objects.filter(pk=self.invitation.pk).exists())

    def test_reminder_uses_current_domain_and_summary_is_json(self):
        self.task.assignee = self.member
        self.task.reminder_at = timezone.now() - timedelta(minutes=1)
        self.task.save()
        reminders = self.api(params={'view': 'reminders'}).json()
        self.assertEqual(reminders['total'], 1)
        self.assertTrue(reminders['items'][0]['key'].startswith('space-reminders:'))
        summary = self.api(params={'summary': '1'})
        self.assertEqual(summary.status_code, 200)
        self.assertNotIn('html', summary.json())
        self.assertEqual(summary['Cache-Control'], 'no-store')
