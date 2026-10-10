"""The retired module cannot be reopened or written, even without import mappings."""
from datetime import timedelta
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve, Resolver404, reverse
from django.utils import timezone

from dashboard.notification_service import notification_sources
from dashboard.recent import RECENT_SESSION_KEY
from spaces.models import LegacyKanbanLink, SpaceTask, SpaceTaskFile, SpaceMembership
from spaces.testing import make_space
from tasks.models import Task, TaskAttachment, TaskCommentImage, TaskProject, TaskSection
from workplaces.models import SidebarFavorite, WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Kanban, KanbanActivity, KanbanAttachment, KanbanProject, KanbanSection


class RetiredKanbanTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner, cls.member, cls.outsider = [get_user_model().objects.create_user(username=name, email=f'{name}@retired-kanban.test') for name in ('owner', 'member', 'outsider')]
        cls.workspace = create_workplace_for_user(cls.owner, 'Test Kanban retirement')
        cls.other = create_workplace_for_user(cls.owner, 'Other workspace')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.project = KanbanProject.objects.create(user=cls.owner, workplace=cls.workspace, name='ArchivedKanbanProbe')
        cls.board = KanbanSection.objects.create(project=cls.project, title='ArchivedKanbanProbe board')
        cls.card = Kanban.objects.create(user=cls.owner, workplace=cls.workspace, section=cls.board, title='ArchivedKanbanProbe card', due_at=timezone.now())
        cls.activity = KanbanActivity.objects.create(task=cls.card, actor=cls.owner, kind='comment', action='commented', message='ArchivedKanbanProbe')
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Current space')
        cls.current = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='CurrentTaskProbe', due_at=timezone.now())
        cls.source = Task.objects.create(user=cls.owner, workplace=cls.workspace, title='Archived source', space_archived=True)
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

    def url(self, suffix='', app='kanban', workplace=None):
        return scoped_workplace_app_path(workplace or self.workspace, app, suffix)

    def test_catalogs_redirect_to_spaces_without_any_imports(self):
        for user in (self.owner, self.member):
            for workplace in (self.workspace, self.other) if user == self.owner else (self.workspace,):
                for query in ('', '?view=all-groups', '?view=projects', '?view=tags', '?tab=private'):
                    for scoped in (False, True):
                        self.login(user)
                        session = self.client.session
                        session['active_workplace_id'] = workplace.pk
                        session.save()
                        path = self.url(workplace=workplace) if scoped else '/kanban/'
                        response = self.client.get(path + query, follow=True)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.wsgi_request.path, self.url(app='spaces', workplace=workplace))
                        self.assertNotContains(response, '/kanban/')
                        self.assertNotContains(response, '<span>Kanban</span>', html=True)

    def test_all_old_write_routes_are_unavailable_and_keep_data(self):
        removed = ('update/1/', 'delete/1/', 'delete/', 'bulk-update-status/', 'delete-attachment/1/', 'groups/1/reorder-columns/', 'projects/1/team/', 'projects/1/team/candidates/', 'groups/1/team/', 'groups/1/team/candidates/', 'favorites/project/1/', 'follow/task/1/')
        for prefix in ('/kanban/', self.url()):
            for suffix in removed:
                with self.subTest(path=prefix + suffix):
                    with self.assertRaises(Resolver404):
                        resolve(prefix + suffix)
                    self.assertEqual(self.client.post(prefix + suffix, {'status': 'closed'}).status_code, 404)
            for suffix in ('', f'view-task/{self.card.task_id}/', f'groups/{self.board.pk}/'):
                self.assertEqual(self.client.post(prefix + suffix, {'action': 'delete_project', 'project_id': self.project.pk}).status_code, 409)
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, 'new')
        self.assertTrue(KanbanProject.objects.filter(pk=self.project.pk).exists())
        self.assertTrue(KanbanActivity.objects.filter(pk=self.activity.pk).exists())
        for model in (Kanban, KanbanProject, KanbanSection, KanbanAttachment):
            self.assertFalse(admin.site.is_registered(model))

    def test_unmapped_objects_and_files_return_404(self):
        for suffix in (f'?project={self.project.pk}', f'groups/{self.board.pk}/', f'view-task/{self.card.task_id}/?task_pk={self.card.pk}', 'attachments/999/download/', 'comment-images/999/'):
            self.assertEqual(self.client.get(self.url(suffix)).status_code, 404)

    def test_imported_task_and_files_use_current_acl_and_workspace(self):
        self.space.visibility, self.space.private_owner = 'private', self.owner
        self.space.save()
        attachment = TaskAttachment.objects.bulk_create([TaskAttachment(task=self.source, file='kanban_attachments/preserved.txt', filename='preserved.txt', file_size=1)])[0]
        activity = self.source.activities.create(actor=self.owner, kind='comment', action='commented')
        comment = TaskCommentImage.objects.bulk_create([TaskCommentImage(activity=activity, file='comment_images/kanban/preserved.png', filename='preserved.png', file_size=1)])[0]
        files = [SpaceTaskFile.objects.create(task=self.current, file=attachment.file.name, filename=attachment.filename, legacy_storage=True),
                 SpaceTaskFile.objects.create(task=self.current, file=comment.file.name, filename=comment.filename)]
        for kind, source, target in [('task', self.card.pk, self.source.pk), ('attachment', 987, attachment.pk), ('comment', 988, comment.pk)]:
            LegacyKanbanLink.objects.create(kind=kind, source_id=source, target_id=target, space=self.space)
        base = f'{self.space.slug}/tasks/{self.current.work_item.key}/'
        paths = [(f'view-task/{self.card.task_id}/?task_pk={self.card.pk}', base+'?view=list'),
                 ('attachments/987/download/', base+f'files/{files[0].pk}/'),
                 ('comment-images/988/', base+f'files/{files[1].pk}/')]
        for suffix, target in paths:
            self.assertRedirects(self.client.get(self.url(suffix)), self.url(target, 'space'), fetch_redirect_response=False)
            self.assertEqual(self.client.get(self.url(suffix, workplace=self.other)).status_code, 404)
        self.login(self.member)
        for suffix, target in paths:
            self.assertEqual(self.client.get(self.url(suffix)).status_code, 404)
        SpaceMembership.objects.create(space=self.space, user=self.member)
        for suffix, target in paths:
            self.assertRedirects(self.client.get(self.url(suffix)), self.url(target, 'space'), fetch_redirect_response=False)
        SpaceMembership.objects.filter(space=self.space, user=self.member).delete()
        for suffix, target in paths:
            self.assertEqual(self.client.get(self.url(suffix)).status_code, 404)

    def test_legacy_records_absent_from_search_history_favorites_and_calendar(self):
        self.project.favorited_by.add(self.owner)
        self.board.favorited_by.add(self.owner)
        session = self.client.session
        session[RECENT_SESSION_KEY] = [{'identity': [self.owner.pk, self.workspace.pk, self.card._meta.label_lower, self.card.pk], 'at': timezone.now().isoformat()}]
        session.save()
        for query in ('ArchivedKanbanProbe', ''):
            response = self.client.get(reverse('global_search'), {'q': query})
            self.assertNotContains(response, '/kanban/')
            self.assertNotIn('ArchivedKanbanProbe', str(response.json()['groups']))
        for tab in ('starred', 'worked', 'viewed'):
            response = self.client.get(self.url(f'?tab={tab}', 'for-you'))
            self.assertNotContains(response, 'ArchivedKanbanProbe')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['columns'][0][0]['count'], 1)
        self.assertFalse(notification_sources(self.owner)['kanban'].exists())
        now = timezone.now()
        response = self.client.get(self.url('events/', 'calendar'), {'start': (now-timedelta(days=1)).isoformat(), 'end': (now+timedelta(days=1)).isoformat()})
        self.assertEqual([event['source'] for event in response.json()['events']], ['tasks'])
        self.assertTrue(all(event['id'].startswith('space_tasks:') for event in response.json()['events']))
        for key in ('kanban-spaces', 'kanban-boards', 'kanban-cards'):
            SidebarFavorite.objects.create(user=self.owner, workplace=self.workspace, item_key=key)
        response = self.client.get(self.url(app='spaces'))
        self.assertNotContains(response, '/kanban/')
        for item in response.context['sidebar_favorites']:
            if item['key'].startswith('kanban-'):
                self.assertEqual(item['url'], self.url(app='spaces'))

    def test_current_board_and_task_view_remain_available(self):
        response = self.client.get(self.url(f'{self.space.slug}/?view=board', 'space'))
        self.assertContains(response, self.current.title)
        self.assertContains(response, 'data-work-board')
        response = self.client.get(self.url(f'{self.space.slug}/tasks/{self.current.work_item.key}/', 'space'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.current.title)
