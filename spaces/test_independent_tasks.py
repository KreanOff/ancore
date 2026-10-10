from datetime import timedelta
from importlib import import_module
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from tasks.models import Task, TaskProject, TaskSection, TaskTag
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .defaults import template_settings
from .models import Space, SpaceConfiguration, SpaceMembership, SpaceTask, SpaceTaskActivity, SpaceTaskMembership, SpaceTaskFile, Sprint, WorkItem


class IndependentTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='space-independent-owner', email='independent@example.test')
        cls.member = get_user_model().objects.create_user(username='space-independent-member', email='member@example.test')
        cls.observer = get_user_model().objects.create_user(username='space-independent-observer', email='observer@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Workspace')
        for user in [cls.member, cls.observer]:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=user)
        cls.config = SpaceConfiguration.objects.create(workplace=cls.workspace, name='Scrum', settings=template_settings('scrum'))
        cls.space = Space.objects.create(user=cls.owner, workplace=cls.workspace, name='Scrum szablon', key='SZ', template='scrum', kind='software', configuration=cls.config, visibility='private', private_owner=cls.owner)
        SpaceMembership.objects.create(space=cls.space, user=cls.member)
        SpaceMembership.objects.create(space=cls.space, user=cls.observer, role='observer')
        cls.task = SpaceTask.objects.create(space=cls.space, title='Praca w przestrzeni', created_by=cls.owner)
        cls.key = cls.task.work_item.key

    def setUp(self):
        self.login(self.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/{suffix}')

    def task_url(self, suffix=''):
        return self.url(f'tasks/{self.key}/{suffix}')

    def data(self, **extra):
        return {'title': self.task.title, 'description': 'Nowy opis', 'priority': 'high', 'work_type': 'task', **extra}

    def test_list_links_and_all_views_keep_the_space(self):
        for view in ['list', 'backlog', 'board', 'timeline', 'reports', 'overview', 'settings', 'tags']:
            response = self.client.get(self.url('?view=' + view))
            self.assertEqual(response.status_code, 200, view)
        response = self.client.get(self.url('?view=list&q=Praca'))
        self.assertContains(response, self.task_url('?view=list&amp;q=Praca'))
        for base in [self.task_url(), f'/space/{self.space.slug}/tasks/{self.key}/']:
            for tab in ['main', 'subtasks', 'work-log', 'members', 'history']:
                response = self.client.get(base, {'view': 'backlog', 'tab': tab, 'q': 'Praca'}, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Scrum szablon')
                self.assertContains(response, 'view=backlog')
                self.assertNotContains(response, 'Planowanie i zespół')

    def test_creation_is_independent_of_legacy_projects_groups_and_tasks(self):
        old_counts = (TaskProject.objects.count(), TaskSection.objects.count(), Task.objects.count())
        response = self.client.post(self.url('items/create/'), self.data(title='Drugie zadanie'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SpaceTask.objects.filter(title='Drugie zadanie', space=self.space).exists())
        self.assertEqual(old_counts, (TaskProject.objects.count(), TaskSection.objects.count(), Task.objects.count()))
        task = SpaceTask.objects.get(title='Drugie zadanie')
        self.assertEqual(task.work_item.key, 'SZ-2')
        self.assertIsNone(task.work_item.legacy_task_id)

    def test_legacy_creation_does_not_create_new_space_or_item(self):
        old = TaskProject.objects.create(user=self.owner, workplace=self.workspace, name='Starszy projekt')
        section = TaskSection.objects.create(project=old, title='Starsza grupa')
        task = Task.objects.create(user=self.owner, workplace=self.workspace, section=section, title='Starsze zadanie')
        self.assertFalse(Space.objects.filter(project=old).exists())
        self.assertFalse(WorkItem.objects.filter(legacy_task=task).exists())
        self.assertNotContains(self.client.get(self.url('?view=list')), 'Starsze zadanie')
        self.assertEqual(self.client.get(scoped_workplace_app_path(self.workspace, 'tasks', f'view-task/{task.task_id}/?task_pk={task.pk}')).status_code, 200)

    def test_save_status_completion_history_and_reopen(self):
        response = self.client.post(self.task_url('?view=list'), self.data(status='closed'))
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'closed')
        self.assertTrue(self.task.is_completed)
        self.assertIsNotNone(self.task.completion_date)
        self.assertTrue(SpaceTaskActivity.objects.filter(task=self.task, action='status_changed', actor=self.owner).exists())
        response = self.client.post(self.task_url('?view=list'), self.data(status='reopened'))
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.completion_date)

    def test_detail_save_keeps_planning_and_uploads_in_the_independent_task(self):
        with TemporaryDirectory() as root, override_settings(PRIVATE_DOCUMENT_ROOT=root), patch.object(SpaceTaskFile._meta.get_field('file'), 'storage', FileSystemStorage(location=root)):
            response = self.client.post(self.task_url('?view=backlog'), self.data(
                title='Tytuł z załącznikiem', status='in_progress', points=8, in_backlog='on',
                files=SimpleUploadedFile('opis.txt', b'Opis pracy', content_type='text/plain'),
            ))
            self.assertEqual(response.status_code, 302)
            self.task.refresh_from_db()
            self.assertEqual(self.task.title, 'Tytuł z załącznikiem')
            self.assertEqual(self.task.work_item.points, 8)
            self.assertTrue(self.task.work_item.in_backlog)
            file = self.task.attachments.get(activity__isnull=True)
            response = self.client.get(self.task_url(f'files/{file.pk}/'))
            self.assertEqual(b''.join(response.streaming_content), b'Opis pracy')
            self.assertFalse(Task.objects.filter(title=self.task.title).exists())
            self.assertTrue(self.task.activities.filter(action='attachments_added', actor=self.owner).exists())

    def test_invalid_detail_upload_and_fields_do_not_partially_save(self):
        with TemporaryDirectory() as root, override_settings(PRIVATE_DOCUMENT_ROOT=root), patch.object(SpaceTaskFile._meta.get_field('file'), 'storage', FileSystemStorage(location=root)):
            for title, filename in [('Nie zapisuj', 'skrypt.exe'), ('', 'opis.txt')]:
                response = self.client.post(self.task_url(), self.data(
                    title=title, status='closed', files=SimpleUploadedFile(filename, b'plik'),
                ))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.context['form']['title'].value(), title)
                self.task.refresh_from_db()
                self.assertEqual(self.task.title, 'Praca w przestrzeni')
                self.assertEqual(self.task.status, 'new')
                self.assertFalse(self.task.attachments.exists())

    def test_invalid_transition_does_not_save_other_changes(self):
        settings = self.config.settings
        settings['statuses'][0]['transitions'] = []
        self.config.settings = settings
        self.config.save()
        response = self.client.post(self.task_url(), self.data(title='Nie zapisuj', status='closed'))
        self.assertEqual(response.status_code, 400)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Praca w przestrzeni')
        self.assertEqual(self.task.status, 'new')

    def test_space_roles_task_privacy_ancestor_and_revocation(self):
        self.login(self.observer)
        self.assertEqual(self.client.get(self.task_url()).status_code, 200)
        self.assertEqual(self.client.post(self.task_url(), self.data()).status_code, 403)
        self.assertNotContains(self.client.get(self.task_url()), 'name="activity_comment"')
        self.task.visibility = 'private'
        self.task.private_owner = self.owner
        self.task.save()
        self.login(self.member)
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)
        SpaceTaskMembership.objects.create(task=self.task, user=self.member, role='observer')
        self.assertEqual(self.client.get(self.task_url()).status_code, 200)
        self.assertEqual(self.client.post(self.task_url(), self.data()).status_code, 403)
        child = SpaceTask.objects.create(space=self.space, parent=self.task, title='Prywatne podzadanie', created_by=self.owner)
        SpaceTaskMembership.objects.filter(task=self.task, user=self.member).delete()
        self.assertEqual(self.client.get(self.url(f'tasks/{child.work_item.key}/')).status_code, 404)
        self.task.assignee = self.member
        self.task.save()
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)
        self.login(self.observer)
        SpaceMembership.objects.filter(space=self.space, user=self.observer).delete()
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)

    def test_space_and_workspace_in_url_are_authoritative(self):
        other = create_workplace_for_user(self.owner, 'Inny Workspace')
        foreign_url = self.task_url().replace(self.workspace.slug, other.slug)
        self.assertEqual(self.client.get(foreign_url).status_code, 404)
        second = Space.objects.create(user=self.owner, workplace=self.workspace, name='Inna przestrzeń', key='IN', configuration=self.config)
        self.assertEqual(self.client.get(self.task_url().replace(self.space.slug, second.slug)).status_code, 404)

    def test_revocation_does_not_restore_task_grants_after_rejoining(self):
        self.task.visibility, self.task.private_owner = 'private', self.owner
        self.task.save()
        child = SpaceTask.objects.create(space=self.space, parent=self.task, title='Potomek', created_by=self.owner, visibility='private', private_owner=self.owner)
        for task in [self.task, child]:
            SpaceTaskMembership.objects.create(task=task, user=self.member)
        self.task.memberships.filter(user=self.member).delete()
        self.assertFalse(child.memberships.filter(user=self.member).exists())
        for task in [self.task, child]:
            SpaceTaskMembership.objects.create(task=task, user=self.member)
        SpaceMembership.objects.filter(space=self.space, user=self.member).delete()
        self.assertFalse(SpaceTaskMembership.objects.filter(user=self.member).exists())
        SpaceMembership.objects.create(space=self.space, user=self.member)
        self.login(self.member)
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)
        SpaceTaskMembership.objects.create(task=self.task, user=self.member)
        membership = WorkplaceMembership.objects.get(workplace=self.workspace, user=self.member)
        membership.is_active = False
        membership.save()
        self.assertFalse(SpaceMembership.objects.filter(user=self.member).exists())
        self.assertFalse(SpaceTaskMembership.objects.filter(user=self.member).exists())
        membership.is_active = True
        membership.save()
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)

    def test_publication_clears_task_members_but_preserves_private_children(self):
        self.task.visibility, self.task.private_owner = 'private', self.owner
        self.task.save()
        child = SpaceTask.objects.create(space=self.space, parent=self.task, title='Potomek', created_by=self.owner, visibility='private', private_owner=self.owner)
        for task in [self.task, child]:
            SpaceTaskMembership.objects.create(task=task, user=self.member)
        response = self.client.post(self.task_url('members/'), {'visibility': 'public', 'role': 'member'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.task.memberships.exists())
        self.assertTrue(child.memberships.filter(user=self.member).exists())
        self.client.post(self.task_url('members/'), {'visibility': 'private', 'role': 'member'})
        self.login(self.member)
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)

    def test_task_sharing_requires_existing_space_and_parent_access(self):
        self.task.visibility, self.task.private_owner = 'private', self.owner
        self.task.save()
        child = SpaceTask.objects.create(space=self.space, parent=self.task, title='Potomek', created_by=self.owner, visibility='private', private_owner=self.owner)
        url = self.url(f'tasks/{child.work_item.key}/members/')
        response = self.client.post(url, {'visibility': 'private', 'role': 'member', 'person': self.member.pk})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(child.memberships.exists())
        SpaceTaskMembership.objects.create(task=self.task, user=self.member)
        self.assertEqual(self.client.post(url, {'visibility': 'private', 'role': 'member', 'person': self.member.pk}).status_code, 302)
        self.assertTrue(child.memberships.filter(user=self.member).exists())
        SpaceMembership.objects.filter(space=self.space, user=self.member).delete()
        self.assertEqual(self.client.post(url, {'visibility': 'private', 'role': 'member', 'person': self.member.pk}).status_code, 400)

    def test_public_space_preserves_independent_private_task_grants(self):
        self.task.visibility, self.task.private_owner = 'private', self.owner
        self.task.save()
        SpaceTaskMembership.objects.create(task=self.task, user=self.member)
        response = self.client.post(self.url('edit/'), {'name': self.space.name, 'description': '', 'visibility': 'public'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.space.memberships.exists())
        self.assertTrue(self.task.memberships.filter(user=self.member).exists())
        self.login(self.member)
        self.assertEqual(self.client.get(self.task_url()).status_code, 200)

    def test_upload_download_comment_author_and_validation(self):
        with TemporaryDirectory() as root, override_settings(PRIVATE_DOCUMENT_ROOT=root), patch.object(SpaceTaskFile._meta.get_field('file'), 'storage', FileSystemStorage(location=root)):
            self.login(self.member)
            response = self.client.post(self.task_url(), {'action': 'comment', 'message': 'Komentarz zespołu', 'files': SimpleUploadedFile('tekst.txt', b'bezpieczny plik', content_type='text/plain')})
            self.assertEqual(response.status_code, 302)
            activity = self.task.activities.get(kind='comment')
            self.assertEqual(activity.actor, self.member)
            file = SpaceTaskFile.objects.get(activity=activity)
            response = self.client.get(self.task_url(f'files/{file.pk}/'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'bezpieczny plik')
            response = self.client.post(self.task_url(), {'action': 'attachment', 'files': SimpleUploadedFile('bad.exe', b'bad')})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(SpaceTaskFile.objects.count(), 1)
            self.login(self.observer)
            SpaceMembership.objects.filter(space=self.space, user=self.observer).delete()
            self.assertEqual(self.client.get(self.task_url(f'files/{file.pk}/')).status_code, 404)

    def test_subtask_and_worklog_are_independent(self):
        response = self.client.post(self.task_url('?tab=subtasks&view=list'), {'action': 'subtask', 'title': 'Podzadanie'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/space/scrum-szablon/tasks/SZ-2/', response.url)
        self.assertEqual(self.task.subtasks.count(), 1)
        now = timezone.now().replace(second=0, microsecond=0)
        response = self.client.post(self.task_url('?tab=work-log'), {'action': 'work-log', 'started_at': now.isoformat(), 'ended_at': (now + timedelta(hours=1)).isoformat(), 'description': 'Praca'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.task.work_logs.get().author, self.owner)

    def test_foreign_tags_and_epics_cannot_be_saved(self):
        second = Space.objects.create(user=self.owner, workplace=self.workspace, name='Inna', key='IN', configuration=self.config)
        tag = TaskTag.objects.create(user=self.owner, workplace=self.workspace, space=second, name='Obcy')
        response = self.client.post(self.task_url(), self.data(tags=[tag.pk]))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.task.tags.exists())

    def test_new_space_does_not_create_project(self):
        counts = TaskProject.objects.count()
        response = self.client.post(scoped_workplace_app_path(self.workspace, 'spaces', 'create/'), {'name': 'Nowa', 'key': 'NW', 'kind': 'business', 'template': 'tasks', 'management': 'team', 'visibility': 'public'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TaskProject.objects.count(), counts)
        self.assertIsNone(Space.objects.get(key='NW').project_id)

    def test_legacy_link_redirect_and_imported_content_no_longer_synchronize(self):
        legacy = Task.objects.create(user=self.owner, workplace=self.workspace, title='Archiwalna treść', space_archived=True)
        item = self.task.work_item
        item.legacy_task = legacy
        item.save()
        old = scoped_workplace_app_path(self.workspace, 'tasks', f'view-task/{legacy.task_id}/?task_pk={legacy.pk}')
        self.assertRedirects(self.client.get(old), self.task_url('?view=list'))
        self.assertEqual(self.client.post(old, self.data()).status_code, 409)
        self.client.post(self.task_url(), self.data(title='Niezależna treść'))
        legacy.refresh_from_db()
        self.assertEqual(legacy.title, 'Archiwalna treść')
        self.assertNotContains(self.client.get(scoped_workplace_app_path(self.workspace, 'tasks')), 'Archiwalna treść')
        self.client.post(self.task_url(), {'action': 'delete'})
        self.assertTrue(Task.objects.filter(pk=legacy.pk, space_archived=True).exists())
        self.assertEqual(self.client.get(old).status_code, 404)

    def test_delete_refuses_a_hidden_or_observed_descendant(self):
        child = SpaceTask.objects.create(space=self.space, parent=self.task, title='Tylko dla właściciela', visibility='private', private_owner=self.owner, created_by=self.owner)
        self.login(self.member)
        response = self.client.post(self.task_url(), {'action': 'delete'})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(SpaceTask.objects.filter(pk=child.pk).exists())
        self.assertTrue(SpaceTask.objects.filter(pk=self.task.pk).exists())

    def test_integrations_use_space_tasks_and_space_addresses(self):
        self.task.assignee = self.owner
        self.task.due_at = timezone.now() + timedelta(days=1)
        self.task.save()
        self.space.favorited_by.add(self.owner)
        for tab in ['recommended', 'assigned', 'starred', 'worked', 'viewed']:
            self.client.get(self.task_url())
            response = self.client.get(scoped_workplace_app_path(self.workspace, 'for-you'), {'tab': tab})
            self.assertEqual(response.status_code, 200, tab)
        response = self.client.get('/global-search/', {'q': 'Praca'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.task_url('?view=list'), str(response.json()))
        response = self.client.get(scoped_workplace_app_path(self.workspace, 'dashboards', 'default/'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Postęp pracy')
        start, end = timezone.now(), timezone.now() + timedelta(days=7)
        response = self.client.get(scoped_workplace_app_path(self.workspace, 'calendar', 'events/'), {'start': start.isoformat(), 'end': end.isoformat()})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(event.get('url') == self.task_url('?view=list') for event in response.json()['events']))

    def test_ajax_comment_uses_shared_composer_response(self):
        response = self.client.post(self.task_url(), {'action': 'comment', 'activity_comment': 'Komentarz AJAX'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertIn('Komentarz AJAX', response.json()['activity_html'])
        self.assertEqual(self.task.activities.get(kind='comment').actor, self.owner)

    def test_task_owner_manages_access_without_space_management(self):
        self.task.visibility, self.task.private_owner = 'private', self.member
        self.task.save()
        self.login(self.member)
        self.assertEqual(self.client.get(self.task_url('members/')).status_code, 200)
        response = self.client.post(self.task_url('members/'), {'visibility': 'private', 'person': self.observer.pk, 'role': 'observer'})
        self.assertEqual(response.status_code, 302)
        membership = self.task.memberships.get(user=self.observer)
        self.assertEqual(membership.role, 'observer')
        self.assertEqual(self.client.post(self.task_url('members/'), {'visibility': 'private', 'role': 'member', 'remove_member': membership.pk}).status_code, 302)
        self.assertFalse(self.task.memberships.exists())

    def test_malformed_planning_never_exposes_foreign_space(self):
        from django.core.exceptions import ValidationError
        from django.db import transaction
        from .access import visible_to
        hidden = Space.objects.create(user=self.owner, workplace=self.workspace, name='Ukryta', key='HID', configuration=self.config, visibility='private', private_owner=self.owner)
        item = self.task.work_item
        item.space = hidden
        with self.assertRaises(ValidationError), transaction.atomic():
            item.save()
        WorkItem.objects.filter(pk=item.pk).update(space=hidden)
        self.assertFalse(visible_to(SpaceTask.objects.all(), self.member).filter(pk=self.task.pk).exists())
        self.login(self.member)
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)



class IndependentMigrationTests(TransactionTestCase):
    def test_import_preserves_keys_content_history_and_private_group_acl(self):
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        executor.migrate([('spaces', '0005_space_slugs')])
        executor = MigrationExecutor(connection)
        old = executor.loader.project_state(list(executor.loader.applied_migrations)).apps
        try:
            User = old.get_model('accounts', 'User')
            owner = User.objects.create(username='migration-independent', email='migration@example.test')
            member = User.objects.create(username='migration-member', email='migration-member@example.test')
            workspace = old.get_model('workplaces', 'Workplace').objects.create(owner_id=owner.pk, name='Migracja', slug='w_independent')
            project = old.get_model('tasks', 'TaskProject').objects.create(user_id=owner.pk, workplace_id=workspace.pk, name='Przeniesiona', code='OLD')
            group = old.get_model('tasks', 'TaskSection').objects.create(project_id=project.pk, title='Prywatna grupa', code='GR', visibility='private', private_owner_id=owner.pk)
            old.get_model('tasks', 'TaskSectionMembership').objects.create(section_id=group.pk, user_id=member.pk, role='observer')
            config = old.get_model('spaces', 'SpaceConfiguration').objects.create(workplace_id=workspace.pk, name='Konfiguracja', settings=template_settings())
            space = old.get_model('spaces', 'Space').objects.create(project_id=project.pk, workplace_id=workspace.pk, key='IMP', slug='przeniesiona', configuration_id=config.pk, next_number=8)
            source = old.get_model('tasks', 'Task').objects.create(user_id=owner.pk, workplace_id=workspace.pk, section_id=group.pk, title='Zachowaj', task_id=7, description='Treść', priority='high', task_type='meeting', reminder_at=timezone.now().replace(second=0, microsecond=0))
            old_member = old.get_model('tasks', 'TaskMembership').objects.create(task_id=source.pk, user_id=member.pk)
            item = old.get_model('spaces', 'WorkItem').objects.create(task_id=source.pk, space_id=space.pk, key='IMP-7', number=7, rank=700)
            old.get_model('tasks', 'TaskActivity').objects.create(task_id=source.pk, actor_id=member.pk, kind='comment', action='commented', message='Historia')
            executor = MigrationExecutor(connection)
            executor.migrate(leaves)
            result = WorkItem.objects.get(pk=item.pk)
            self.assertEqual(result.key, 'IMP-7')
            self.assertEqual(result.task.title, 'Zachowaj')
            self.assertEqual(result.task.description, 'Treść')
            self.assertEqual(result.task.task_type, 'meeting')
            self.assertEqual(result.task.reminder_at, source.reminder_at)
            self.assertEqual(result.task.activities.get().actor_id, member.pk)
            self.assertEqual(result.task.memberships.get(user_id=member.pk).role, 'observer')
            self.assertEqual(result.task.memberships.get(user_id=member.pk).created_at, old_member.created_at)
            self.assertEqual(result.task.visibility, 'private')
            self.assertEqual(result.space.name, 'Przeniesiona')
            self.assertTrue(Task.objects.filter(pk=source.pk).exists())
            self.assertEqual(result.legacy_task_id, source.pk)
        finally:
            MigrationExecutor(connection).migrate(leaves)
