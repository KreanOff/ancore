"""Preserve historical project privacy and deny retired entry points."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .access import visible_to
from .models import Task, TaskActivity, TaskAttachment, TaskCommentImage, TaskProject, TaskProjectTemplate, TaskSection


class ProjectVisibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='privacy-owner', email='privacy-owner@example.test')
        cls.member = users.objects.create_user(username='privacy-member', email='privacy-member@example.test')
        cls.admin = users.objects.create_user(username='privacy-admin', email='privacy-admin@example.test')
        cls.outsider = users.objects.create_user(username='privacy-outsider', email='privacy-outsider@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Widoczność projektów')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.admin, role='admin')
        cls.public = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Wspólny plan')
        cls.private = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Poufny projekt',
            visibility='private', private_owner=cls.member, source='Poufne źródło')
        cls.section = TaskSection.objects.create(project=cls.private, title='Poufna grupa')
        cls.public_section = TaskSection.objects.create(project=cls.public, title='Wspólna grupa')
        cls.task = Task.objects.create(user=cls.owner, section=cls.section, title='Poufne zadanie',
            assignee=cls.owner, due_at=timezone.now(), reminder_at=timezone.now()-timedelta(hours=1))
        cls.child = Task.objects.create(user=cls.owner, section=cls.section, parent=cls.task, title='Poufne podzadanie')
        cls.public_task = Task.objects.create(user=cls.owner, section=cls.public_section, title='Wspólne zadanie')
        cls.attachment = TaskAttachment.objects.bulk_create([TaskAttachment(task=cls.task, file='privacy-test.txt', filename='Poufny plik', file_size=1)])[0]
        cls.comment = TaskActivity.objects.create(task=cls.task, actor=cls.member, action='commented', kind='comment', message='Poufny komentarz')
        cls.image = TaskCommentImage.objects.create(activity=cls.comment, filename='Poufny obraz', file='privacy-test.png')

    def setUp(self):
        self.login(self.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'tasks', suffix)

    def test_detail_group_files_settings_and_follow_reject_both_url_variants(self):
        for base in ['/tasks/', self.url()]:
            for suffix in [f'view-task/{self.task.task_id}/?task_pk={self.task.pk}',
                           f'view-subtask/{self.child.task_id}/?task_pk={self.child.pk}',
                           f'groups/{self.section.pk}/', f'attachments/{self.attachment.pk}/download/',
                           f'comment-images/{self.image.pk}/']:
                with self.subTest(base=base, suffix=suffix):
                    response = self.client.get(base+suffix, follow=True)
                    self.assertEqual(response.status_code, 404)
            self.assertEqual(self.client.post(base+f'follow/project/{self.private.pk}/', {'following': 'true'}).status_code, 404)
        self.assertEqual(self.client.get('/settings/project-fields/', {'project_id': self.private.pk}).status_code, 404)

    def test_revoked_membership_and_wrong_workspace_override_private_ownership(self):
        self.login(self.member)
        self.membership.is_active = False
        self.membership.save(update_fields=['is_active'])
        self.assertFalse(visible_to(Task.objects.all(), self.member).filter(pk=self.task.pk).exists())
        self.assertEqual(self.client.get(self.url()).status_code, 302)
        self.login(self.owner)
        self.assertEqual(self.client.get(scoped_workplace_app_path(self.other, 'tasks', f'view-task/{self.public_task.task_id}/'), {'task_pk': self.public_task.pk}).status_code, 404)

    def test_deleted_private_owner_never_publishes_project(self):
        self.member.delete()
        self.private.refresh_from_db()
        self.assertEqual(self.private.visibility, 'private')
        self.assertIsNone(self.private.private_owner_id)
        self.assertFalse(visible_to(TaskProject.objects.all(), self.owner).filter(pk=self.private.pk).exists())


class ProjectVisibilityMigrationTests(TransactionTestCase):
    def test_existing_projects_and_templates_remain_public_with_relations_intact(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        owner = get_user_model().objects.create_user(username='privacy-migration', email='migration@example.test')
        executor.migrate([('tasks', '0053_comment_attachment_size')])
        old = executor.loader.project_state([('tasks', '0053_comment_attachment_size')]).apps
        project = old.get_model('tasks', 'TaskProject').objects.create(user_id=owner.pk, name='Dawny projekt')
        section = old.get_model('tasks', 'TaskSection').objects.create(project_id=project.pk, title='Dawna grupa')
        template = old.get_model('tasks', 'TaskProjectTemplate').objects.create(user_id=owner.pk, name='Dawny szablon', template_name='Szablon', structure={})
        MigrationExecutor(connection).migrate(latest)
        for item in [TaskProject.objects.get(pk=project.pk), TaskProjectTemplate.objects.get(pk=template.pk)]:
            self.assertEqual(item.visibility, 'public')
            self.assertIsNone(item.private_owner_id)
        self.assertEqual(TaskSection.objects.get(pk=section.pk).project_id, project.pk)
