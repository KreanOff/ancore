"""Project privacy must hold for every entry point, including stale open tabs."""
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.collaboration import mention_people
from dashboard.notification_service import notification_sources
from dashboard.reminders import reminders_for_user
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .access import visible_to
from .forms import TaskForm, TaskModalForm
from .models import Task, TaskActivity, TaskAttachment, TaskCommentImage, TaskProject, TaskProjectTemplate, TaskSection
from .project_templates import save_project_template


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

    def post_json(self, suffix, data):
        return self.client.post(self.url(suffix), json.dumps(data), content_type='application/json')

    def test_private_only_for_its_person_even_for_owner_and_admin(self):
        for person in [self.owner, self.admin, self.member, self.outsider]:
            with self.subTest(person=person.username):
                self.assertEqual(visible_to(TaskProject.objects.all(), person).filter(pk=self.private.pk).exists(), person == self.member)
                self.assertEqual(visible_to(Task.objects.all(), person).filter(pk=self.child.pk).exists(), person == self.member)
                self.assertEqual(visible_to(TaskProject.objects.all(), person).filter(pk=self.public.pk).exists(), person != self.outsider)

    def test_create_and_edit_bind_private_owner_to_actual_actor(self):
        self.login(self.member)
        response = self.client.post(self.url(), {'action': 'create_project', 'name': 'Tylko ja', 'visibility': 'private', 'private_owner': self.owner.pk})
        self.assertEqual(response.status_code, 302)
        project = TaskProject.objects.get(name='Tylko ja')
        self.assertEqual((project.user_id, project.private_owner_id), (self.owner.pk, self.member.pk))
        for visibility in ['public', 'private']:
            self.assertEqual(self.client.post(self.url(), {'action': 'edit_project', 'project_id': project.pk,
                'name': project.name, 'visibility': visibility}).status_code, 302)
            project.refresh_from_db()
            self.assertEqual(project.private_owner_id, self.member.pk if visibility == 'private' else None)
        # Legacy form omitting the new control preserves privacy.
        self.client.post(self.url(), {'action': 'edit_project', 'project_id': project.pk, 'name': 'Nadal prywatny'})
        project.refresh_from_db()
        self.assertEqual(project.visibility, 'private')

    def test_unknown_visibility_is_rejected_and_form_keeps_error(self):
        response = self.client.post(self.url(), {'action': 'create_project', 'name': 'Błędny', 'visibility': 'anyone'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('visibility', response.context['project_form'].errors)
        self.assertFalse(TaskProject.objects.filter(name='Błędny').exists())

    def test_new_projects_default_to_private_for_actual_creator(self):
        self.login(self.member)
        for url in [self.url(), reverse('tasks:tasks')]:
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.context['project_form']['visibility'].value(), 'private')
                response = self.client.post(url, {'action': 'create_project', 'name': 'Domyślnie prywatny'})
                self.assertEqual(response.status_code, 302)
                project = TaskProject.objects.filter(name='Domyślnie prywatny').latest('pk')
                self.assertEqual((project.visibility, project.private_owner_id, project.user_id),
                                 ('private', self.member.pk, self.owner.pk))
                self.assertFalse(visible_to(TaskProject.objects.all(), self.owner).filter(pk=project.pk).exists())

    def test_public_template_does_not_publish_new_project_by_default(self):
        template = save_project_template(self.public)
        self.login(self.member)
        response = self.client.get(self.url(), {'template': template.pk})
        self.assertEqual(response.context['project_form']['visibility'].value(), 'private')
        response = self.client.post(self.url(), {'action': 'create_project', 'name': 'Prywatna kopia', 'template': template.pk})
        self.assertEqual(response.status_code, 302)
        project = TaskProject.objects.get(name='Prywatna kopia')
        self.assertEqual((project.visibility, project.private_owner_id), ('private', self.member.pk))

    def test_public_visibility_can_be_selected_and_is_preserved_on_edit(self):
        self.login(self.member)
        response = self.client.post(self.url(), {'action': 'create_project', 'name': 'Jawnie publiczny', 'visibility': 'public'})
        self.assertEqual(response.status_code, 302)
        project = TaskProject.objects.get(name='Jawnie publiczny')
        self.assertEqual((project.visibility, project.private_owner_id), ('public', None))
        self.client.post(self.url(), {'action': 'edit_project', 'project_id': project.pk, 'name': project.name})
        project.refresh_from_db()
        self.assertEqual(project.visibility, 'public')

    def test_lists_navigation_options_search_dashboard_and_calendar_hide_private(self):
        for view in ['', 'all-groups', 'all-tasks', 'my-tasks', 'tags']:
            with self.subTest(view=view):
                response = self.client.get(self.url(), {'view': view})
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'Poufn')
        search = self.client.get(reverse('global_search'), {'q': 'Poufn'})
        self.assertEqual(search.json()['total'], 0)
        home = self.client.get(reverse('home'))
        self.assertEqual(home.context['dashboard_totals']['total'], 1)
        self.assertEqual(home.context['dashboard_project_count'], 1)
        events = self.client.get(scoped_workplace_app_path(self.workspace, 'calendar', 'events/'), {
            'start': (timezone.now()-timedelta(days=1)).isoformat(), 'end': (timezone.now()+timedelta(days=1)).isoformat(),
        })
        self.assertEqual(events.status_code, 200)
        self.assertNotIn('Poufn', json.dumps(events.json(), ensure_ascii=False))

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

    def test_forged_mutations_and_bulk_actions_do_not_change_private_records(self):
        for action in ['edit_project', 'delete_project', 'add_project_note', 'create_section', 'save_project_template']:
            response = self.client.post(self.url(), {'action': action, 'project_id': self.private.pk, 'name': 'Wyciek', 'message': 'Wyciek'})
            self.assertEqual(response.status_code, 404, action)
        self.assertEqual(self.post_json(f'update/{self.task.task_id}/', {'task_pk': self.task.pk, 'status': 'closed'}).status_code, 404)
        response = self.post_json('bulk-update-status/', {'task_pks': [self.task.pk, self.public_task.pk], 'status': 'closed'})
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.public_task.refresh_from_db()
        self.assertEqual(self.task.status, 'new')
        self.assertEqual(self.public_task.status, 'closed')
        self.assertEqual(self.client.post(self.url(f'delete-attachment/{self.attachment.pk}/')).status_code, 404)
        self.assertEqual(self.client.post(self.url(f'view-task/{self.task.task_id}/'), {'action': 'add_activity_comment', 'activity_comment': 'Wyciek'}).status_code, 404)
        self.assertTrue(TaskProject.objects.filter(pk=self.private.pk).exists())

    def test_forms_reject_private_relations_even_with_supplied_queryset(self):
        for form in [TaskForm(user=self.owner, viewer=self.owner, workplace=self.workspace),
                     TaskModalForm(user=self.owner, viewer=self.owner, workplace=self.workspace, sections_queryset=TaskSection.objects.all())]:
            self.assertFalse(form.fields['section'].queryset.filter(pk=self.section.pk).exists())
        response = self.client.post(self.url(), {'action': 'create_task_modal', 'section': self.section.pk,
            'title': 'Wyciek', 'priority': 'medium', 'status': 'new'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.filter(title='Wyciek').exists())

    def test_person_keeps_access_and_publication_immediately_updates_access(self):
        self.login(self.member)
        self.assertContains(self.client.get(self.url()), self.private.name)
        self.assertEqual(self.client.get(self.url(f'view-task/{self.task.task_id}/')).status_code, 200)
        self.assertEqual(self.post_json(f'update/{self.task.task_id}/', {'task_pk': self.task.pk, 'status': 'closed'}).status_code, 200)
        self.assertEqual(self.task.activities.get(action='status_changed').actor, self.member)
        self.client.post(self.url(), {'action': 'edit_project', 'project_id': self.private.pk, 'name': self.private.name, 'visibility': 'public'})
        self.login(self.owner)
        self.assertEqual(self.client.get(self.url(f'view-task/{self.task.task_id}/')).status_code, 200)

    def test_notifications_mentions_and_reminders_do_not_grant_access(self):
        self.assertFalse(notification_sources(self.owner)['tasks'].filter(task=self.task).exists())
        self.assertFalse(reminders_for_user(self.owner).filter(task=self.task).exists())

        self.assertEqual(list(mention_people(self.task)), [self.member])
        self.assertTrue(notification_sources(self.member)['tasks'].filter(task=self.task).exists())
        self.private.visibility = 'public'
        self.private.save(update_fields=['visibility'])
        self.assertTrue(reminders_for_user(self.owner).filter(task=self.task).exists())
        self.private.visibility = 'private'
        self.private.save(update_fields=['visibility'])
        self.assertFalse(reminders_for_user(self.owner).filter(task=self.task).exists())

    def test_unassigned_private_task_reminds_its_private_owner(self):
        self.task.assignee = None
        self.task.save(update_fields=['assignee'])
        self.assertTrue(reminders_for_user(self.member).filter(task=self.task).exists())
        self.assertFalse(reminders_for_user(self.owner).filter(task=self.task).exists())

    def test_private_templates_preserve_scope_in_catalog_forms_and_editor(self):
        template = save_project_template(self.private)
        self.assertEqual((template.visibility, template.private_owner), ('private', self.member))
        self.assertNotContains(self.client.get(self.url('templates/')), 'Poufn')
        self.assertEqual(self.client.get(self.url(f'templates/{template.pk}/edit/')).status_code, 404)
        response = self.client.post(self.url(), {'action': 'create_project', 'name': 'Wyciek', 'template': template.pk})
        self.assertIn('template', response.context['project_form'].errors)
        self.login(self.member)
        response = self.client.get(self.url(), {'template': template.pk})
        self.assertEqual(response.context['project_form'].initial['visibility'], 'private')
        self.assertContains(self.client.get(self.url('templates/')), template.name)
        response = self.client.post(self.url(), {'action': 'create_project', 'name': 'Moja kopia', 'template': template.pk})
        self.assertEqual(response.status_code, 302)
        copied = TaskProject.objects.get(name='Moja kopia')
        self.assertEqual((copied.visibility, copied.private_owner_id), ('private', self.member.pk))

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

    def test_nested_children_in_legacy_other_groups_inherit_hidden_ancestor(self):
        child = Task.objects.create(user=self.owner, section=self.public_section, parent=self.task, title='Legacy child')
        grandchild = Task.objects.create(user=self.owner, section=self.public_section, parent=child, title='Legacy grandchild')
        for task in [child, grandchild]:
            self.assertFalse(visible_to(Task.objects.all(), self.owner).filter(pk=task.pk).exists())
            self.assertEqual(self.client.get(self.url(f'view-subtask/{task.task_id}/')).status_code, 404)
            self.assertTrue(visible_to(Task.objects.all(), self.member).filter(pk=task.pk).exists())
            self.assertEqual(list(mention_people(task)), [self.member])

    def test_delete_public_parent_or_project_cannot_cascade_into_hidden_child(self):
        self.task.parent = self.public_task
        self.task.save(update_fields=['parent'])
        for suffix, data in [(f'delete/{self.public_task.task_id}/', {'task_pk': self.public_task.pk}),
                             ('delete/', {'task_pks': [self.public_task.pk]})]:
            self.assertEqual(self.post_json(suffix, data).status_code, 403)
        self.assertEqual(self.client.post(self.url(), {'action': 'delete_project', 'project_id': self.public.pk}).status_code, 403)
        self.assertEqual(self.client.post(self.url(), {'action': 'delete_section', 'section_id': self.public_section.pk}).status_code, 403)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())
        self.assertTrue(Task.objects.filter(pk=self.public_task.pk).exists())


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
