"""Retired Tasks routes never expose or change historical work."""
from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import Resolver404, resolve, reverse
from django.utils import timezone

from dashboard.models import ActivityInterest, NotificationState, ObjectFollow, TaskReminder
from dashboard.notification_service import notification_sources
from dashboard.recent import RECENT_SESSION_KEY
from spaces.models import SpaceMembership, SpaceTask, SpaceTaskFile
from spaces.testing import make_space
from tasks.access import editable_to, visible_to
from tasks.models import Task, TaskActivity, TaskAttachment, TaskCommentImage, TaskProject, TaskProjectTemplate, TaskSection, TaskTag
from workplaces.models import SidebarFavorite, WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class RetiredTasksTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner, cls.member, cls.outsider = [get_user_model().objects.create_user(username=name, email=f'{name}@retired-tasks.test') for name in ('owner', 'member', 'outsider')]
        cls.workspace = create_workplace_for_user(cls.owner, 'Tasks retirement')
        cls.other = create_workplace_for_user(cls.owner, 'Other Workspace')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='LegacyTasksProbe project')
        cls.group = TaskSection.objects.create(project=cls.project, title='LegacyTasksProbe group')
        cls.task = Task.objects.create(user=cls.owner, workplace=cls.workspace, section=cls.group, title='LegacyTasksProbe task', due_at=timezone.now(), reminder_at=timezone.now()-timedelta(hours=1))
        cls.activity = cls.task.activities.create(actor=cls.owner, kind='comment', action='commented', message='LegacyTasksProbe comment')
        cls.template = TaskProjectTemplate.objects.create(user=cls.owner, workplace=cls.workspace, name='LegacyTasksProbe template', structure={'groups': []})
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='CurrentSpaceProbe')
        cls.current = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='CurrentTaskProbe', due_at=timezone.now(), reminder_at=timezone.now()-timedelta(hours=1))
        cls.source = Task.objects.create(user=cls.owner, workplace=cls.workspace, title='Imported source', space_archived=True)
        item = cls.current.work_item
        item.legacy_task = cls.source
        item.save()

    def setUp(self):
        self.login(self.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session['workspace_url_scope_enabled'] = False
        session.save()

    def url(self, suffix='', app='tasks', workplace=None):
        return scoped_workplace_app_path(workplace or self.workspace, app, suffix)

    def prefixes(self):
        return ['/tasks/', self.url()]

    def test_catalogs_redirect_to_spaces_and_shell_has_no_retired_links(self):
        for user in (self.owner, self.member):
            for query in ('', '?view=all-groups', '?view=all-tasks', '?view=my-tasks', '?tab=favorites'):
                for scoped in (False, True):
                    self.login(user)
                    response = self.client.get((self.url() if scoped else '/tasks/') + query, follow=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.wsgi_request.path, self.url(app='spaces'))
                    for marker in ('data-sidebar-group="legacy"', 'Starsze widoki', '<span>Projekty</span>', '<span>Grupy</span>', '<span>Zadania</span>', 'Ulubione projekty', 'Szablony projektów', 'href="/tasks/', self.url()):
                        self.assertNotContains(response, marker)
                    self.assertNotIn('tasks', response.context['workplace_app_urls'])
                    self.assertContains(response, 'Wszystkie zadania')
                    self.assertContains(response, 'Przestrzenie')
        self.assertEqual(self.client.head(self.url()).status_code, 302)

    def test_removed_endpoints_and_admin_are_unavailable_without_data_loss(self):
        removed = ('templates/', f'templates/{self.template.pk}/edit/', 'favorites/project/1/', 'favorites/section/1/', 'favorites/task/1/', 'projects/1/team/', 'projects/1/team/candidates/', 'groups/1/team/', 'groups/1/team/candidates/', 'items/1/team/', 'items/1/team/candidates/', 'follow/task/1/', 'update/1/', 'delete/1/', 'delete/', 'bulk-update-status/', 'delete-attachment/1/')
        for prefix in self.prefixes():
            for suffix in removed:
                with self.subTest(path=prefix+suffix):
                    with self.assertRaises(Resolver404):
                        resolve(prefix+suffix)
                    self.assertEqual(self.client.get(prefix+suffix).status_code, 404)
                    self.assertEqual(self.client.post(prefix+suffix, {'action': 'delete_project', 'project_id': self.project.pk}).status_code, 404)
            for suffix in ('', f'groups/{self.group.pk}/', f'view-task/{self.task.task_id}/', f'view-subtask/{self.task.task_id}/', 'attachments/1/download/', 'comment-images/1/'):
                self.assertEqual(self.client.post(prefix+suffix, {'action': 'delete_project', 'project_id': self.project.pk}).status_code, 409)
        self.task.refresh_from_db()
        self.template.refresh_from_db()
        self.assertEqual(self.task.status, 'new')
        self.assertEqual(self.template.structure, {'groups': []})
        self.assertTrue(TaskProject.objects.filter(pk=self.project.pk).exists())
        self.assertTrue(TaskSection.objects.filter(pk=self.group.pk).exists())
        self.assertTrue(TaskActivity.objects.filter(pk=self.activity.pk).exists())
        self.owner.is_staff = self.owner.is_superuser = True
        self.owner.save()
        for model in (Task, TaskProject, TaskSection, TaskProjectTemplate, TaskAttachment):
            self.assertFalse(admin.site.is_registered(model))
            self.assertEqual(self.client.get(f'/admin/tasks/{model._meta.model_name}/').status_code, 404)

    def test_unmapped_and_malformed_links_return_404(self):
        for prefix in self.prefixes():
            for suffix in (f'?project={self.project.pk}', f'groups/{self.group.pk}/', f'view-task/{self.task.task_id}/?task_pk={self.task.pk}', 'view-subtask/999/', 'attachments/999/download/', 'comment-images/999/', '?view=tags', '?project=bad', '?section='+'9'*100, f'view-task/{self.source.task_id}/?task_pk=bad', f'view-task/{self.source.task_id}/?task_pk='+'9'*100):
                self.assertEqual(self.client.get(prefix+suffix, follow=True).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get('/tasks/').status_code, 302)

    def test_access_helpers_hide_all_historical_work_and_preserve_space_tags(self):
        for viewer in (self.owner, self.member, self.outsider):
            for model in (Task, TaskProject, TaskSection, TaskProjectTemplate, TaskActivity, TaskAttachment, TaskCommentImage):
                self.assertFalse(visible_to(model.objects.all(), viewer).exists())
                self.assertFalse(editable_to(model.objects.all(), viewer).exists())
        tag = TaskTag.objects.create(user=self.owner, workplace=self.workspace, space=self.space, name='SpaceTagProbe')
        self.assertTrue(visible_to(TaskTag.objects.filter(pk=tag.pk), self.owner).exists())
        response = self.client.get(self.url(f'{self.space.slug}/?view=tags', app='space'))
        self.assertContains(response, tag.name)

    def test_imported_task_and_files_redirect_with_current_acl(self):
        self.space.visibility, self.space.private_owner = 'private', self.owner
        self.space.save()
        attachment = TaskAttachment.objects.bulk_create([TaskAttachment(task=self.source, file='task_attachments/preserved.txt', filename='preserved.txt')])[0]
        activity = self.source.activities.create(actor=self.owner, kind='comment', action='commented')
        comment = TaskCommentImage.objects.bulk_create([TaskCommentImage(activity=activity, file='comment_images/tasks/preserved.txt', filename='preserved.txt')])[0]
        files = [SpaceTaskFile.objects.create(task=self.current, file=attachment.file.name, filename=attachment.filename, legacy_storage=True), SpaceTaskFile.objects.create(task=self.current, file=comment.file.name, filename=comment.filename)]
        base = f'{self.space.slug}/tasks/{self.current.work_item.key}/'
        suffixes = [(f'view-task/{self.source.task_id}/?task_pk={self.source.pk}', base+'?view=list'), (f'view-subtask/{self.source.task_id}/?task_pk={self.source.pk}', base+'?view=list'), (f'attachments/{attachment.pk}/download/', base+f'files/{files[0].pk}/'), (f'comment-images/{comment.pk}/', base+f'files/{files[1].pk}/')]
        for scoped in (False, True):
            self.login(self.owner)
            prefix = self.url() if scoped else '/tasks/'
            for suffix, target in suffixes:
                self.login(self.owner)
                self.assertRedirects(self.client.get(prefix+suffix), self.url(target, app='space'), fetch_redirect_response=False)
                self.assertEqual(self.client.get(self.url(suffix, workplace=self.other)).status_code, 404)
                self.login(self.owner)
                self.assertEqual(self.client.post(prefix+suffix, {'action': 'delete'}).status_code, 409)
            self.login(self.member)
            for suffix, _ in suffixes:
                self.assertEqual(self.client.get(prefix+suffix).status_code, 404)
            membership = SpaceMembership.objects.create(space=self.space, user=self.member)
            for suffix, target in suffixes:
                self.assertRedirects(self.client.get(prefix+suffix), self.url(target, app='space'), fetch_redirect_response=False)
            membership.delete()
            for suffix, _ in suffixes:
                self.assertEqual(self.client.get(prefix+suffix).status_code, 404)
        self.assertTrue(TaskAttachment.objects.filter(pk=attachment.pk).exists())
        self.assertTrue(TaskCommentImage.objects.filter(pk=comment.pk).exists())
        self.login(self.owner)
        self.current.delete()
        for suffix, _ in suffixes:
            self.assertEqual(self.client.get(self.url(suffix)).status_code, 404)

    def test_imported_project_and_group_links_use_space_acl_and_scope(self):
        self.space.project, self.space.visibility, self.space.private_owner = self.project, 'private', self.owner
        self.space.save()
        suffixes = [(f'?project={self.project.pk}', ''), (f'?section={self.group.pk}', '?view=list'), (f'groups/{self.group.pk}/', '?view=list')]
        for suffix, target in suffixes:
            self.assertRedirects(self.client.get(self.url(suffix)), self.url(f'{self.space.slug}/{target}', app='space'), fetch_redirect_response=False)
            self.assertEqual(self.client.get(self.url(suffix, workplace=self.other)).status_code, 404)
        self.login(self.member)
        for suffix, _ in suffixes:
            self.assertEqual(self.client.get(self.url(suffix)).status_code, 404)
        membership = SpaceMembership.objects.create(space=self.space, user=self.member)
        for suffix, target in suffixes:
            self.assertRedirects(self.client.get(self.url(suffix)), self.url(f'{self.space.slug}/{target}', app='space'), fetch_redirect_response=False)
        membership.delete()
        for suffix, _ in suffixes:
            self.assertEqual(self.client.get(self.url(suffix)).status_code, 404)

    def test_old_records_absent_from_search_recent_favorites_and_calendar(self):
        self.project.favorited_by.add(self.owner)
        self.group.favorited_by.add(self.owner)
        self.task.favorited_by.add(self.owner)
        session = self.client.session
        session[RECENT_SESSION_KEY] = [{'identity': [self.owner.pk, self.workspace.pk, obj._meta.label_lower, obj.pk], 'at': timezone.now().isoformat()} for obj in (self.task, self.project, self.group, self.current)]
        session.save()
        for query in ('LegacyTasksProbe', 'zadania'):
            payload = self.client.get(reverse('global_search'), {'q': query}).json()
            self.assertNotIn('LegacyTasksProbe', str(payload['groups']))
            for group in payload['groups']:
                for row in group['results']:
                    self.assertFalse(row['url'].startswith(('/tasks/', self.url())))
            self.assertFalse({'tasks', 'projects', 'groups'} & {group['key'] for group in payload['groups']})
        payload = self.client.get(reverse('global_search'), {'recent': '1'}).json()
        self.assertNotIn('LegacyTasksProbe', str(payload))
        self.assertIn(self.current.title, str(payload))
        for tab in ('starred', 'worked', 'viewed'):
            self.assertNotContains(self.client.get(self.url(f'?tab={tab}', app='for-you')), 'LegacyTasksProbe')
        now = timezone.now()
        events = self.client.get(self.url('events/', app='calendar'), {'start': (now-timedelta(days=1)).isoformat(), 'end': (now+timedelta(days=1)).isoformat()}).json()['events']
        self.assertEqual([event['id'] for event in events], [f'space_tasks:{self.current.pk}'])
        for key in ('tasks-projects', 'tasks-all', 'tasks-groups', 'tasks-my'):
            SidebarFavorite.objects.create(user=self.owner, workplace=self.workspace, item_key=key)
        response = self.client.get(self.url(app='spaces'))
        self.assertNotContains(response, 'data-sidebar-favorite-item="tasks-groups"')
        self.assertNotContains(response, 'data-sidebar-favorite-item="tasks-my"')
        self.assertTrue(all('/tasks/' not in item['url'] for item in response.context['sidebar_favorites']))

    def test_retired_notifications_and_reminders_cannot_be_delivered_or_changed(self):
        reminder = TaskReminder.objects.create(task=self.task, recipient=self.owner, scheduled_at=self.task.reminder_at)
        state = NotificationState.objects.create(user=self.owner, task_activity=self.activity, is_read=False)
        ObjectFollow.objects.create(user=self.member, task=self.task)
        self.task.activities.create(actor=self.owner, kind='comment', action='commented', message='@member')
        self.assertFalse(ActivityInterest.objects.exists())
        sources = notification_sources(self.owner)
        self.assertFalse(sources['tasks'].exists())
        self.assertFalse(sources['reminders'].exists())
        self.assertTrue(sources['space-reminders'].exists())
        self.assertEqual(TaskReminder.objects.count(), 1)
        for key in (f'tasks:{self.activity.pk}', f'reminders:{reminder.pk}'):
            self.assertEqual(self.client.post(reverse('notification_action'), {'action': 'read', 'key': key}).status_code, 404)
        state.refresh_from_db()
        self.assertFalse(state.is_read)
        self.assertTrue(TaskReminder.objects.filter(pk=reminder.pk).exists())
