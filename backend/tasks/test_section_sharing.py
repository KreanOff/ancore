"""Group grants must narrow project access across every entry point."""
import json

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.http import Http404
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from dashboard.notification_service import notification_page, notification_summary, change_notification_state
from tasks.access import editable_to, visible_to
from tasks.forms import TaskModalForm
from tasks.models import (Task, TaskActivity, TaskAttachment, TaskSectionNote, TaskProject,
                          TaskProjectMembership, TaskSection, TaskSectionMembership, TaskSectionInvitation)
from tasks.project_templates import save_project_template
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class SectionSharingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner, cls.admin, cls.member, cls.outsider = [users.objects.create_user(username=name, email=f'{name}@groups.test')
            for name in ['owner', 'admin', 'member', 'outsider']]
        cls.workspace = create_workplace_for_user(cls.owner, 'Grupy QA')
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Druga przestrzeń')
        for person in [cls.admin, cls.member]:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=person)
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Wspólny projekt')
        cls.public = TaskSection.objects.create(project=cls.project, title='Publiczna grupa')
        cls.private = TaskSection.objects.create(project=cls.project, title='Poufna grupa', visibility='private', private_owner=cls.owner)
        cls.task = Task.objects.create(user=cls.owner, workplace=cls.workspace, section=cls.private, title='Poufne zadanie', assignee=cls.member)
        cls.child = Task.objects.create(user=cls.owner, workplace=cls.workspace, section=cls.public, parent=cls.task, title='Stare podzadanie')
        cls.note = TaskSectionNote.objects.create(section=cls.private, author=cls.owner, message='Sekret grupy')
        cls.attachment = TaskAttachment.objects.bulk_create([TaskAttachment(task=cls.task, file='task_attachments/group-secret.txt', file_size=4)])[0]
        cls.admin_membership = TaskSectionMembership.objects.create(section=cls.private, user=cls.admin, role='admin')

    def setUp(self):
        self.login(self.owner)

    def login(self, person):
        self.client.force_login(person)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'tasks', suffix)

    def team(self, **params):
        return self.client.post(self.url(f'groups/{self.private.pk}/team/'), params)

    def share(self, role='member'):
        self.assertEqual(self.team(action='share', email=self.member.email.upper(), role=role).status_code, 200)
        return self.private.memberships.get(user=self.member)

    def legacy_invitation(self):
        return TaskSectionInvitation.objects.create(section=self.private, recipient=self.member, invited_by=self.owner)

    def test_privacy_and_workspace_scope_apply_to_group_and_task_tree(self):
        for person, expected in [(self.owner, True), (self.admin, True), (self.member, False), (self.outsider, False)]:
            for model, pk in [(TaskSection, self.private.pk), (Task, self.task.pk), (Task, self.child.pk),
                              (TaskSectionNote, self.note.pk), (TaskAttachment, self.attachment.pk)]:
                with self.subTest(person=person, model=model, pk=pk):
                    self.assertEqual(visible_to(model.objects.all(), person).filter(pk=pk).exists(), expected)
        self.login(self.member)
        for base in [self.url(), reverse('tasks:tasks')]:
            for suffix in [f'groups/{self.private.pk}/', f'view-task/{self.task.task_id}/?task_pk={self.task.pk}',
                           f'attachments/{self.attachment.pk}/download/', f'groups/{self.private.pk}/team/']:
                self.assertEqual(self.client.get(base + suffix, follow=True).status_code, 404)

    def test_sharing_immediately_opens_group_and_task_tree(self):
        self.share()
        self.assertFalse(self.private.invitations.exists())
        self.login(self.member)
        self.assertTrue(visible_to(Task.objects.all(), self.member).filter(pk=self.child.pk).exists())
        for base in [self.url(), reverse('tasks:tasks')]:
            response = self.client.get(base, {'view': 'all-groups'}, follow=True)
            self.assertContains(response, self.private.title)
            self.assertNotContains(response, 'id="section-tab-invitations"')
            self.assertEqual(self.client.get(base + f'groups/{self.private.pk}/', follow=True).status_code, 200)
        self.assertEqual(self.private.memberships.get(user=self.member).role, 'member')

    def test_legacy_invitation_no_longer_requires_or_accepts_response(self):
        invitation = self.legacy_invitation()
        self.assertEqual(self.team(action='invite', email=self.member.email, role='member').status_code, 400)
        self.login(self.member)
        for base in [self.url(), reverse('tasks:tasks')]:
            self.assertEqual(self.client.post(base + f'section-invitations/{invitation.pk}/respond/', {'action': 'accept'}).status_code, 404)
        self.assertFalse(visible_to(TaskSection.objects.all(), self.member).filter(pk=self.private.pk).exists())
        self.login(self.owner)
        self.share()
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'revoked')

    def test_candidates_and_invalid_recipients(self):
        endpoint = self.url(f'groups/{self.private.pk}/team/candidates/')
        self.assertEqual(self.client.get(endpoint, {'q': 'm'}).json()['results'], [])
        response = self.client.get(endpoint, {'q': 'groups.test'})
        self.assertEqual([person['email'] for person in response.json()['results']], [self.member.email])
        for email in [self.outsider.email, self.owner.email, self.admin.email, 'missing@groups.test']:
            self.assertEqual(self.team(action='share', email=email, role='member').status_code, 400)
        self.share()
        self.assertEqual(self.client.get(endpoint, {'q': 'member'}).json()['results'], [])
        self.assertEqual(self.team(action='share', email=self.member.email, role='member').status_code, 400)

    def test_project_privacy_is_a_ceiling_and_candidate_boundary(self):
        self.project.visibility = 'private'
        self.project.private_owner = self.owner
        self.project.save()
        self.assertEqual(self.team(action='share', email=self.member.email, role='member').status_code, 400)
        parent = TaskProjectMembership.objects.create(project=self.project, user=self.member, role='member')
        self.share()
        self.login(self.member)
        parent.delete()
        self.assertFalse(visible_to(Task.objects.all(), self.member).filter(pk=self.task.pk).exists())
        self.assertFalse(self.private.memberships.filter(user=self.member).exists())
        TaskProjectMembership.objects.create(project=self.project, user=self.member)
        self.assertFalse(visible_to(TaskSection.objects.all(), self.member).filter(pk=self.private.pk).exists())

    def test_parent_observer_cannot_manage_group_even_as_group_owner(self):
        self.project.visibility = 'private'
        self.project.private_owner = self.owner
        self.project.save()
        TaskProjectMembership.objects.create(project=self.project, user=self.member, role='observer')
        self.private.private_owner = self.member
        self.private.save()
        self.login(self.member)
        response = self.client.get(self.url(f'groups/{self.private.pk}/team/'))
        self.assertFalse(response.json()['can_manage'])
        self.assertNotIn('data-project-role-member', response.json()['members'])
        self.assertEqual(self.team(action='share', email=self.owner.email, role='member').status_code, 403)
        self.assertFalse(editable_to(Task.objects.all(), self.member).filter(pk=self.task.pk).exists())

    def test_roles_observer_readonly_and_revocation(self):
        self.share('observer')
        self.login(self.member)
        member = self.private.memberships.get(user=self.member)
        self.assertTrue(visible_to(Task.objects.all(), self.member).filter(pk=self.task.pk).exists())
        self.assertFalse(editable_to(Task.objects.all(), self.member).filter(pk=self.child.pk).exists())
        self.assertEqual(self.team(action='share', email=self.owner.email, role='member').status_code, 403)
        for base in [self.url(), reverse('tasks:tasks')]:
            self.assertEqual(self.client.post(base, {'action': 'edit_section', 'section_id': self.private.pk, 'title': 'Zmiana'}).status_code, 404)
            self.assertEqual(self.client.post(base, {'action': 'delete_section', 'section_ids': [self.public.pk, self.private.pk]}).status_code, 403)
            self.assertEqual(self.client.post(base + f'update/{self.task.task_id}/', json.dumps({'status': 'closed', 'task_pk': self.task.pk}), content_type='application/json').status_code, 404)
        self.login(self.admin)
        self.assertEqual(self.team(action='role', member_id=member.pk, role='admin').status_code, 403)
        self.assertEqual(self.team(action='share', email=self.member.email, role='admin').status_code, 400)
        self.login(self.owner)
        self.assertEqual(self.team(action='role', member_id=member.pk, role='member').status_code, 200)
        self.assertTrue(editable_to(Task.objects.all(), self.member).filter(pk=self.child.pk).exists())
        self.assertEqual(self.team(action='remove', member_id=member.pk).status_code, 200)
        self.assertFalse(visible_to(Task.objects.all(), self.member).filter(pk=self.task.pk).exists())

    def test_visibility_owner_actual_creator_defaults_and_stale_forms(self):
        self.login(self.member)
        for base in [self.url(), reverse('tasks:tasks')]:
            response = self.client.post(base, {'action': 'create_section', 'project_id': self.project.pk, 'title': 'Moja grupa'})
            self.assertEqual(response.status_code, 302)
            section = TaskSection.objects.filter(title='Moja grupa').latest('pk')
            self.assertEqual((section.visibility, section.private_owner_id), ('private', self.member.pk))
            self.assertEqual(self.client.post(base, {'action': 'edit_section', 'section_id': section.pk, 'title': 'Nowa nazwa'}).status_code, 302)
            section.refresh_from_db()
            self.assertEqual(section.visibility, 'private')
        self.login(self.admin)
        response = self.client.post(self.url(), {'action': 'edit_section', 'section_id': self.private.pk,
                                               'title': self.private.title, 'visibility': 'public'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('visibility', response.context['section_rename_form'].errors)
        self.private.refresh_from_db()
        self.assertEqual(self.private.visibility, 'private')

    def test_publishing_clears_old_members_and_pending_invitations(self):
        self.share()
        invitation = self.legacy_invitation()
        self.assertEqual(self.client.post(self.url(), {'action': 'edit_section', 'section_id': self.private.pk,
                         'title': self.private.title, 'visibility': 'public'}).status_code, 302)
        invitation.refresh_from_db()
        self.private.refresh_from_db()
        self.assertEqual(invitation.status, 'revoked')
        self.assertIsNone(self.private.private_owner_id)
        self.assertFalse(self.private.memberships.exists())
        self.assertTrue(visible_to(Task.objects.all(), self.member).filter(pk=self.task.pk).exists())

    def test_workspace_removal_clears_memberships_and_pending_invitations(self):
        self.share()
        invitation = self.legacy_invitation()
        membership = WorkplaceMembership.objects.get(workplace=self.workspace, user=self.member)
        membership.is_active = False
        membership.save()
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'revoked')
        WorkplaceMembership.objects.get(workplace=self.workspace, user=self.admin).delete()
        self.assertFalse(self.private.memberships.filter(user=self.admin).exists())

    def test_no_hidden_data_in_lists_search_calendar_notifications_or_templates(self):
        self.login(self.member)
        for params in [{'view': 'all-groups'}, {'view': 'all-tasks'}, {'project': self.project.pk}]:
            response = self.client.get(self.url(), params)
            self.assertNotContains(response, self.private.title)
            self.assertNotContains(response, self.task.title)
            self.assertNotContains(response, self.child.title)
        from dashboard.notification_service import notification_sources
        self.assertFalse(notification_sources(self.member)['tasks'].filter(task=self.task).exists())
        template = save_project_template(self.project, self.member)
        self.assertNotIn(self.private.pk, [item['id'] for item in template.structure['sections']])
        self.assertEqual(template.structure['tasks'], [])
        template = save_project_template(self.project, self.owner)
        self.assertEqual(template.visibility, 'private')
        response = self.client.get(reverse('global_search'), {'q': 'Poufne'})
        self.assertNotIn(self.task.title, response.content.decode())
        response = self.client.get(scoped_workplace_app_path(self.workspace, 'calendar'))
        self.assertNotIn(self.task.title, response.content.decode())

    def test_project_cascade_rejects_private_empty_groups(self):
        self.task.delete()
        self.login(self.member)
        self.assertEqual(self.client.post(self.url(), {'action': 'delete_project', 'project_id': self.project.pk}).status_code, 403)
        self.assertTrue(TaskProject.objects.filter(pk=self.project.pk).exists())

    def test_sharing_and_legacy_invitations_do_not_create_inbox_requests(self):
        invitation = self.legacy_invitation()
        self.share()
        data = notification_page(self.member, {'view': 'invitations', 'workspace': str(self.workspace.pk)})
        self.assertEqual(data['dashboard_notifications'], [])
        self.assertEqual(notification_summary(self.member)['pending_invitation_count'], 0)
        self.assertTrue(self.private.shared_with.filter(pk=self.member.pk).exists())
        with self.assertRaises(Http404):
            change_notification_state(self.member, {'action': 'read', 'key': f'section:{invitation.pk}'})

    def test_csrf_and_missing_private_owner_fail_closed(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url(f'groups/{self.private.pk}/team/'), {'action': 'invite'}).status_code, 403)
        self.private.private_owner = None
        self.private.save()
        self.assertFalse(visible_to(TaskSection.objects.all(), self.admin).filter(pk=self.private.pk).exists())

    def test_project_activity_sort_and_metrics_ignore_private_groups(self):
        self.login(self.member)
        for sort in ['last_activity_asc', 'last_activity_desc']:
            response = self.client.get(self.url(), {'sort': sort})
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, self.private.title)
        response = self.client.get(self.url(), {'project': self.project.pk})
        project = response.context['active_project']
        self.assertEqual(project.tasks_total_count, 0)
        self.assertEqual(project.groups_total_count, 1)

    def test_forged_group_relation_and_unknown_visibility_are_rejected(self):
        self.login(self.member)
        response = self.client.post(self.url(), {'action': 'create_section', 'project_id': self.project.pk,
                                               'title': 'Błędna grupa', 'visibility': 'internet'})
        self.assertIn('visibility', response.context['section_form'].errors)
        self.assertFalse(TaskSection.objects.filter(title='Błędna grupa').exists())
        form = TaskModalForm(user=self.owner, viewer=self.member, workplace=self.workspace)
        self.assertFalse(form.fields['section'].queryset.filter(pk=self.private.pk).exists())

    def test_publishing_project_preserves_independent_group_grants(self):
        self.project.visibility = 'private'
        self.project.private_owner = self.owner
        self.project.save()
        TaskProjectMembership.objects.create(project=self.project, user=self.admin)
        self.assertEqual(self.client.post(self.url(), {'action': 'edit_project', 'project_id': self.project.pk,
                         'name': self.project.name, 'visibility': 'public'}).status_code, 302)
        self.assertTrue(self.private.memberships.filter(user=self.admin).exists())
        self.assertTrue(visible_to(TaskSection.objects.all(), self.admin).filter(pk=self.private.pk).exists())


class SectionSharingMigrationTests(TransactionTestCase):
    def test_existing_group_keeps_content_and_inherited_access(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        owner = get_user_model().objects.create_user(username='group-migration', email='migration@groups.test')
        executor.migrate([('tasks', '0057_project_observer')])
        apps = executor.loader.project_state([('tasks', '0057_project_observer')]).apps
        project = apps.get_model('tasks', 'TaskProject').objects.create(user_id=owner.pk, name='Istniejący projekt')
        section = apps.get_model('tasks', 'TaskSection').objects.create(project=project, title='Istniejąca grupa', code='OLD', description='Treść')
        MigrationExecutor(connection).migrate(latest)
        restored = TaskSection.objects.get(pk=section.pk)
        self.assertEqual((restored.visibility, restored.private_owner_id), ('public', None))
        self.assertEqual((restored.title, restored.code, restored.description), ('Istniejąca grupa', 'OLD', 'Treść'))
        self.assertFalse(restored.memberships.exists())
        self.assertFalse(restored.invitations.exists())
