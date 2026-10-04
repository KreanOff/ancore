import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.http import Http404
from django.test import Client, TestCase
from django.urls import reverse

from dashboard.models import ActivityInterest, ObjectFollow
from dashboard.notification_service import change_notification_state, notification_page
from kanban.models import Kanban, KanbanActivity, KanbanProject, KanbanSection
from tasks.models import Task, TaskActivity, TaskProject, TaskSection
from workplaces.models import WorkplaceMembership, create_workplace_for_user


class CollaborationTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.owner = users.create_user(username='owner', email='owner@example.test')
        self.member = users.create_user(username='żaneta.kowalska', email='member@example.test', first_name='Żaneta')
        self.outsider = users.create_user(username='outside', email='outside@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Zespół')
        self.other = create_workplace_for_user(self.owner, 'Prywatny')
        self.membership = WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member, role='member')
        self.project = TaskProject.objects.create(user=self.owner, workplace=self.workspace, name='Projekt')
        self.section = TaskSection.objects.create(project=self.project, title='Grupa')
        self.task = Task.objects.create(user=self.owner, workplace=self.workspace, section=self.section, title='Zadanie')
        self.kproject = KanbanProject.objects.create(user=self.owner, workplace=self.workspace, name='Przestrzeń')
        self.ksection = KanbanSection.objects.create(project=self.kproject, title='Tablica')
        self.card = Kanban.objects.create(user=self.owner, workplace=self.workspace, section=self.ksection, title='Karta')
        self.login(self.member)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def follow(self, obj=None, app='tasks', kind='task', value='true', scoped=True):
        obj = obj or self.task
        url = reverse(f'{app}:follow_object', args=[kind, obj.pk])
        if scoped:
            url = f'/workplaces/{self.workspace.slug}' + url
        return self.client.post(url, {'following': value})

    def comment(self, task=None, actor=None, message=None):
        task = task or self.task
        model = TaskActivity if isinstance(task, Task) else KanbanActivity
        return model.objects.create(task=task, actor=actor or self.owner, kind='comment', action='commented',
                                    message=message if message is not None else f'Proszę @{self.member.username}, sprawdź.')

    def page(self, view, user=None, **filters):
        return notification_page(user or self.member, {'view': view, 'workspace': '', **filters})

    def test_mentions_are_personal_and_share_one_existing_notification(self):
        event = self.comment(message=f'@{self.member.username} @{self.member.username}! @outside @owner')
        delivery = ActivityInterest.objects.get(task_activity=event)
        self.assertEqual(delivery.user, self.member)
        self.assertTrue(delivery.mentioned)
        self.assertFalse(delivery.followed)
        items = self.page('mentions')['dashboard_notifications']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['event_label'], 'Wzmianka')
        self.assertIn(f'task_pk={self.task.pk}', items[0]['url'])
        self.assertEqual(self.page('mentions', self.owner)['dashboard_notification_count'], 0)
        self.assertEqual(self.page('mentions', self.outsider)['dashboard_notification_count'], 0)
        self.assertEqual(sum(i['key'] == f'tasks:{event.pk}' for i in self.page('all')['dashboard_notifications']), 1)

    def test_mentions_require_exact_handles_and_ignore_email_substrings(self):
        for text in [f'mail@{self.member.username}', f'@{self.member.username}-extra', f'@{self.member.username}.extra']:
            self.comment(message=text)
        self.assertFalse(ActivityInterest.objects.exists())
        self.comment(message=f'(@{self.member.username}).')
        self.assertEqual(ActivityInterest.objects.count(), 1)

    def test_public_ancore_ids_use_one_at_in_suggestions_and_deliveries(self):
        self.member.username = '@anna.kowalska'
        self.member.first_name = 'Anna'
        self.member.last_name = 'Kowalska'
        self.member.save(update_fields=['username', 'first_name', 'last_name'])
        self.login(self.owner)
        for app, task in [('tasks', self.task)]:
            url = f'/workplaces/{self.workspace.slug}/{app}/view-task/{task.task_id}/'
            page = self.client.get(url, {'task_pk': task.pk})
            person = next(person for person in page.context['mention_people'] if person['username'] == self.member.username)
            self.assertEqual(person['mention'], '@Anna Kowalska')
            self.assertEqual(person['email'], self.member.email)
            response = self.client.post(url, {'task_pk': task.pk, 'action': 'add_activity_comment',
                                              'activity_mentions': json.dumps([{'user_id': self.member.pk, 'start': 7, 'end': 7 + len(person['mention'])}]),
                                              'activity_comment': f"Proszę {person['mention']}, sprawdź."})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(self.page('mentions')['dashboard_notification_count'], 1)
        self.comment(message='@@anna.kowalska @anna.kowalska.extra mail@anna.kowalska')
        self.assertEqual(self.page('mentions')['dashboard_notification_count'], 1)

    def test_legacy_username_suggestions_keep_a_single_prefix(self):
        self.member.first_name = ''
        self.member.save(update_fields=['first_name'])
        url = f'/workplaces/{self.workspace.slug}/tasks/view-task/{self.task.task_id}/'
        page = self.client.get(url, {'task_pk': self.task.pk})
        person = next(person for person in page.context['mention_people'] if person['username'] == self.member.username)
        self.assertEqual(person['mention'], f'@{self.member.username}')

    def post_named_comment(self, text, mentions, task=None, app='tasks'):
        task = task or self.task
        self.login(self.owner)
        url = f'/workplaces/{self.workspace.slug}/{app}/view-task/{task.task_id}/'
        return self.client.post(url, {'task_pk': task.pk, 'action': 'add_activity_comment',
                                     'activity_comment': text, 'activity_mentions': json.dumps(mentions)})

    def test_selected_name_notifies_only_selected_account_with_duplicate_names(self):
        twin = get_user_model().objects.create_user(username='other-zaneta', email='twin@example.test', first_name='Żaneta')
        WorkplaceMembership.objects.create(workplace=self.workspace, user=twin, role='member')
        response = self.post_named_comment('Hej @Żaneta!', [{'user_id': self.member.pk, 'start': 4, 'end': 11}])
        self.assertEqual(response.status_code, 302)
        event = self.task.activities.filter(kind='comment').latest('pk')
        self.assertEqual(event.message, 'Hej @Żaneta!')
        self.assertEqual(event.metadata['mentions'][0]['user_id'], self.member.pk)
        self.assertEqual(list(ActivityInterest.objects.filter(task_activity=event).values_list('user_id', flat=True)), [self.member.pk])
        self.assertEqual(self.page('mentions', twin)['dashboard_notification_count'], 0)

    def test_selected_name_offsets_handle_unicode_newlines_and_trimmed_text(self):
        response = self.post_named_comment('  🙂\r\n@Żaneta  ', [{'user_id': self.member.pk, 'start': 4, 'end': 11}], self.task, 'tasks')
        self.assertEqual(response.status_code, 302)
        event = self.task.activities.filter(kind='comment').latest('pk')
        self.assertEqual(event.message, '🙂\n@Żaneta')
        self.assertEqual(event.metadata['mentions'][0]['start'], 2)
        self.assertTrue(ActivityInterest.objects.filter(task_activity=event, user=self.member, mentioned=True).exists())

    def test_selected_names_reject_foreign_inactive_or_removed_text(self):
        self.outsider.first_name = 'Żaneta'
        self.outsider.save(update_fields=['first_name'])
        for text, entries in [
            ('@Żaneta', [{'user_id': self.outsider.pk, 'start': 0, 'end': 7}]),
            ('Usunięta wzmianka', [{'user_id': self.member.pk, 'start': 0, 'end': 7}]),
            ('@Żaneta', [{'user_id': self.member.pk, 'start': -1, 'end': 7}]),
            ('@Żaneta', {'user_id': self.member.pk}),
            ('@Żaneta', []),
        ]:
            self.assertEqual(self.post_named_comment(text, entries).status_code, 302)
        self.membership.is_active = False
        self.membership.save(update_fields=['is_active'])
        self.post_named_comment('@Żaneta', [{'user_id': self.member.pk, 'start': 0, 'end': 7}])
        self.assertFalse(ActivityInterest.objects.exists())

    def test_selected_name_does_not_mention_a_different_legacy_handle(self):
        other = get_user_model().objects.create_user(username='Żaneta', email='prefix@example.test')
        WorkplaceMembership.objects.create(workplace=self.workspace, user=other, role='member')
        self.post_named_comment('@Żaneta', [{'user_id': self.member.pk, 'start': 0, 'end': 7}])
        self.assertEqual(list(ActivityInterest.objects.values_list('user_id', flat=True)), [self.member.pk])

    def test_inactive_accounts_and_revoked_members_are_not_mentioned(self):
        self.member.is_active = False
        self.member.save(update_fields=['is_active'])
        self.comment()
        self.member.is_active = True
        self.member.save(update_fields=['is_active'])
        self.membership.is_active = False
        self.membership.save(update_fields=['is_active'])
        self.comment()
        self.assertFalse(ActivityInterest.objects.exists())

    def test_case_distinct_handles_and_email_handles_are_unambiguous(self):
        upper = get_user_model().objects.create_user(username=self.member.username.upper(), email='upper@example.test')
        email_user = get_user_model().objects.create_user(username='login@example.test', email='email-handle@example.test')
        for person in [upper, email_user]:
            WorkplaceMembership.objects.create(workplace=self.workspace, user=person, role='member')
        first = self.comment()
        self.assertEqual(list(ActivityInterest.objects.filter(task_activity=first).values_list('user_id', flat=True)), [self.member.pk])
        second = self.comment(message='Kontakt login@example.test, wzmianka @login@example.test.')
        self.assertEqual(list(ActivityInterest.objects.filter(task_activity=second).values_list('user_id', flat=True)), [email_user.pk])

    def test_status_and_bulk_status_changes_stay_in_history_without_notifying_followers(self):
        for app, obj in [('tasks', self.task)]:
            self.follow(obj, app=app)
        self.login(self.owner)
        for app, obj in [('tasks', self.task)]:
            history_count = obj.activities.filter(kind='system').count()
            response = self.client.post(f'/workplaces/{self.workspace.slug}/{app}/update/{obj.task_id}/',
                                       json.dumps({'task_pk': obj.pk, 'status': 'closed'}), content_type='application/json')
            self.assertEqual(response.status_code, 200)
            response = self.client.post(f'/workplaces/{self.workspace.slug}/{app}/bulk-update-status/',
                                       json.dumps({'task_pks': [obj.pk], 'status': 'reopened'}), content_type='application/json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(obj.activities.filter(kind='system').count(), history_count + 2)
            obj.refresh_from_db()
            self.assertEqual(obj.status, 'reopened')
        self.assertFalse(ActivityInterest.objects.exists())
        self.assertEqual(self.page('following')['dashboard_notification_count'], 0)
        self.assertEqual(self.page('all')['dashboard_notification_count'], 0)

    def test_task_and_project_subscription_deduplicate_and_exclude_own_changes(self):
        for obj, kind in [(self.task, 'task'), (self.project, 'project')]:
            for _ in range(2):
                self.assertEqual(self.follow(obj, kind=kind).status_code, 200)
        self.assertEqual(ObjectFollow.objects.count(), 2)
        event = self.comment()
        delivery = ActivityInterest.objects.get(task_activity=event)
        self.assertTrue(delivery.mentioned and delivery.followed)
        self.comment(actor=self.member)
        self.assertEqual(self.page('following')['dashboard_notification_count'], 1)
        self.assertEqual(self.page('mentions')['dashboard_notification_count'], 1)

    def test_project_observes_comments_on_future_tasks_and_subtasks_but_not_their_creation(self):
        self.follow(self.project, kind='project')
        new = Task.objects.create(user=self.owner, workplace=self.workspace, section=self.section, title='Nowe')
        child = Task.objects.create(user=self.owner, workplace=self.workspace, section=self.section, parent=new, title='Podzadanie')
        self.assertFalse(ActivityInterest.objects.exists())
        self.assertEqual(self.page('following')['dashboard_notification_count'], 0)
        self.comment(new, message='Komentarz w nowym zadaniu')
        self.comment(child, message='Komentarz w podzadaniu')
        unrelated = Task.objects.create(user=self.owner, workplace=self.workspace, title='Poza projektem')
        self.comment(unrelated, message='Bez wzmianki')
        self.assertEqual(self.page('following')['dashboard_notification_count'], 2)

    def test_unfollow_stops_new_deliveries_and_retains_already_delivered_entries(self):
        self.follow()
        self.comment(message='Pierwszy')
        self.assertEqual(self.follow(value='false').status_code, 200)
        self.comment(message='Drugi')
        self.assertEqual(self.page('following')['dashboard_notification_count'], 1)
        self.assertFalse(ObjectFollow.objects.exists())
        self.follow()
        self.assertEqual(self.page('following')['dashboard_notification_count'], 1)
        self.comment(message='Trzeci')
        self.assertEqual(self.page('following')['dashboard_notification_count'], 2)


    def test_revocation_removes_access_to_deliveries_and_endpoints(self):
        self.follow()
        self.comment()
        self.membership.is_active = False
        self.membership.save(update_fields=['is_active'])
        self.assertEqual(self.page('mentions')['dashboard_notification_count'], 0)
        self.assertEqual(self.page('following')['dashboard_notification_count'], 0)
        # Scoped middleware redirects revoked memberships to Workspace selection.
        self.assertIn(self.follow().status_code, (302, 403, 404))
        self.comment()
        self.assertEqual(ActivityInterest.objects.count(), 1)
        with self.assertRaises(Http404):
            change_notification_state(self.member, {'action': 'read', 'key': f'tasks:{self.task.activities.last().pk}'})

    def test_follow_rejects_other_workspaces_wrong_owner_get_and_invalid_input(self):
        foreign = Task.objects.create(user=self.owner, workplace=self.other, title='Prywatne')
        corrupt = Task.objects.create(user=self.outsider, workplace=self.workspace, title='Obcy właściciel')
        for obj in [foreign, corrupt]:
            self.assertEqual(self.follow(obj).status_code, 404)
        self.assertEqual(self.client.get(f'/workplaces/{self.workspace.slug}' + reverse('tasks:follow_object', args=['task', self.task.pk])).status_code, 405)
        self.assertEqual(self.follow(value='bad').status_code, 400)
        self.assertFalse(ObjectFollow.objects.exists())
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        self.assertEqual(client.post(reverse('tasks:follow_object', args=['task', self.task.pk]), {'following': 'true'}).status_code, 403)

    def test_comment_http_paths_and_suggestions_are_scoped(self):
        self.login(self.owner)
        for app, task in [('tasks', self.task)]:
            for scoped in [False, True]:
                url = reverse(f'{app}:view-task', args=[task.task_id])
                if scoped:
                    url = f'/workplaces/{self.workspace.slug}' + url
                page = self.client.get(url, {'task_pk': task.pk}, follow=True)
                self.assertContains(page, 'mention-people')
                self.assertContains(page, json.dumps(self.member.username))
                self.assertNotContains(page, '"username": "outside"')
                response = self.client.post(url, {'task_pk': task.pk, 'action': 'add_activity_comment', 'activity_comment': f'@{self.member.username} — sprawdź'})
                self.assertEqual(response.status_code, 302)
        self.assertEqual(self.page('mentions')['dashboard_notification_count'], 2)

    def test_comment_and_delivery_rollback_together(self):
        from tasks.views.tasks import _record_task_activity
        count = TaskActivity.objects.count()
        with patch('dashboard.collaboration.ActivityInterest.objects.bulk_create', side_effect=RuntimeError('delivery failed')):
            with self.assertRaises(RuntimeError):
                _record_task_activity(self.task, self.owner, 'commented', f'@{self.member.username}', kind='comment')
        self.assertEqual(TaskActivity.objects.count(), count)

    def test_database_constraints_and_cascade(self):
        self.follow()
        self.comment()
        for kwargs in [{}, {'task': self.task, 'task_project': self.project}, {'task': self.task}]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                ObjectFollow.objects.create(user=self.member, **kwargs)
        self.task.delete()
        self.assertFalse(ActivityInterest.objects.exists())
        self.assertFalse(ObjectFollow.objects.exists())

    def test_filters_pagination_and_bulk_read_preserve_personal_state(self):
        for n in range(15):
            self.comment(message=f'@{self.member.username} wiadomość {n}')
        page = self.page('mentions')
        next_page = notification_page(self.member, {'view': 'mentions', 'workspace': ''}, page['next_cursor'])
        self.assertEqual(len(page['dashboard_notifications']) + len(next_page['dashboard_notifications']), 15)
        change_notification_state(self.member, {'action': 'read_all', 'snapshot': page['snapshot']})
        self.assertEqual(self.page('mentions')['filtered_unread_count'], 0)
        self.assertEqual(self.page('mentions', workspace=str(self.workspace.pk))['dashboard_notification_count'], 15)
        self.comment()
        self.assertEqual(self.page('mentions')['filtered_unread_count'], 1)
