"""Observer grants are read-only at every project mutation boundary."""
import json
from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .access import editable_to, visible_to
from .forms import TaskForm, TaskModalForm
from .models import (Task, TaskActivity, TaskAttachment, TaskProject,
                     TaskProjectMembership, TaskProjectNote, TaskProjectTemplate, TaskSection, TaskSectionNote)


class ProjectObserverTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner, cls.observer, cls.admin, cls.candidate = [
            get_user_model().objects.create_user(username=name, email=f'{name}@observer.test')
            for name in ['owner', 'observer', 'admin', 'candidate']
        ]
        cls.workspace = create_workplace_for_user(cls.owner, 'Obserwatorzy')
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Inny Workspace')
        for person in [cls.observer, cls.admin, cls.candidate]:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=person, role='admin')
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace,
            visibility='private', private_owner=cls.owner, name='Obserwowany projekt')
        cls.membership = TaskProjectMembership.objects.create(project=cls.project, user=cls.observer, role='observer')
        TaskProjectMembership.objects.create(project=cls.project, user=cls.admin, role='admin')
        cls.section = TaskSection.objects.create(project=cls.project, title='Obserwowana grupa')
        cls.task = Task.objects.create(user=cls.owner, section=cls.section, title='Obserwowane zadanie', due_at=timezone.now())
        cls.child = Task.objects.create(user=cls.owner, section=cls.section, parent=cls.task, title='Podzadanie')
        cls.public = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Wspólny projekt')
        cls.public_section = TaskSection.objects.create(project=cls.public, title='Wspólna grupa')
        cls.public_task = Task.objects.create(user=cls.owner, section=cls.public_section, title='Wspólne zadanie')
        cls.note = TaskProjectNote.objects.create(project=cls.project, author=cls.observer, message='Dawna notatka')
        cls.section_note = TaskSectionNote.objects.create(section=cls.section, author=cls.observer, message='Dawna notatka grupy')

    def setUp(self):
        self.login(self.observer)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'tasks', suffix)

    def team(self, **data):
        return self.client.post(self.url(f'projects/{self.project.pk}/team/'), data)

    def post_json(self, base, suffix, data):
        return self.client.post(base + suffix, json.dumps(data), content_type='application/json')

    def test_observer_reads_lists_details_team_search_calendar_and_downloads(self):
        for base in ['/tasks/', self.url()]:
            for suffix in ['', f'?project={self.project.pk}', '?view=all-groups', '?view=all-tasks&tab=shared',
                           f'groups/{self.section.pk}/', f'view-task/{self.task.task_id}/?task_pk={self.task.pk}',
                           f'view-subtask/{self.child.task_id}/?task_pk={self.child.pk}']:
                with self.subTest(base=base, suffix=suffix):
                    response = self.client.get(base + suffix, follow=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'Obserwow')
            payload = self.client.get(base + f'projects/{self.project.pk}/team/', follow=True).json()
            self.assertFalse(payload['can_manage'])
            self.assertIn('Obserwator', payload['members'])
            self.assertEqual(payload['modals'].strip(), '')
        self.assertGreater(self.client.get(reverse('global_search'), {'q': 'Obserwow'}).json()['total'], 0)
        events = self.client.get(scoped_workplace_app_path(self.workspace, 'calendar', 'events/'), {
            'start': (timezone.now() - timedelta(days=1)).isoformat(),
            'end': (timezone.now() + timedelta(days=1)).isoformat(),
        })
        self.assertIn('Obserwowane zadanie', json.dumps(events.json(), ensure_ascii=False))
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            attachment = TaskAttachment.objects.create(task=self.task, filename='plan.txt', file_size=4,
                file=SimpleUploadedFile('plan.txt', b'plan', content_type='text/plain'))
            response = self.client.get(self.url(f'attachments/{attachment.pk}/download/'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'plan')
            self.assertEqual(self.client.post(self.url(f'delete-attachment/{attachment.pk}/')).status_code, 404)
            self.assertTrue(TaskAttachment.objects.filter(pk=attachment.pk).exists())

    def test_observer_cannot_mutate_project_groups_notes_or_snapshot(self):
        payloads = [
            {'action': action, 'project_id': self.project.pk, 'name': 'Zmiana', 'message': 'Zmiana'}
            for action in ['edit_project', 'rename_project', 'delete_project', 'create_section',
                           'add_project_note', 'update_project_notes', 'save_project_template']
        ] + [
            {'action': action, 'section_id': self.section.pk, 'title': 'Zmiana', 'message': 'Zmiana'}
            for action in ['edit_section', 'rename_section', 'delete_section', 'create_task',
                           'add_section_note', 'update_section_notes']
        ] + [
            {'action': action, 'project_id': self.project.pk, 'note_id': self.note.pk, 'message': 'Zmiana'}
            for action in ['edit_project_note', 'delete_project_note']
        ] + [
            {'action': action, 'section_id': self.section.pk, 'note_id': self.section_note.pk, 'message': 'Zmiana'}
            for action in ['edit_section_note', 'delete_section_note']
        ]
        for base in ['/tasks/', self.url(), self.url(f'groups/{self.section.pk}/')]:
            for data in payloads:
                with self.subTest(base=base, action=data['action']):
                    self.assertIn(self.client.post(base, data).status_code, [403, 404])
        self.project.refresh_from_db(); self.section.refresh_from_db(); self.note.refresh_from_db()
        self.assertEqual(self.project.name, 'Obserwowany projekt')
        self.assertEqual(self.section.title, 'Obserwowana grupa')
        self.assertEqual(self.note.message, 'Dawna notatka')
        self.assertFalse(TaskProjectTemplate.objects.exists())

    def test_task_mutations_comments_uploads_work_logs_and_subtasks_are_denied(self):
        activity_count = TaskActivity.objects.count()
        for base in ['/tasks/', self.url()]:
            for task in [self.task, self.child]:
                kind = 'view-subtask' if task.parent_id else 'view-task'
                for action in ['edit_task', 'add_activity_comment', 'create_subtask_modal',
                               'add_work_log', 'edit_work_log', 'delete_work_log']:
                    with self.subTest(base=base, task=task.pk, action=action):
                        response = self.client.post(base + f'{kind}/{task.task_id}/?task_pk={task.pk}', {
                            'action': action, 'title': 'Zmiana', 'activity_comment': 'Komentarz',
                            'section': self.public_section.pk,
                            'attachments': SimpleUploadedFile('plan.txt', b'plan'),
                        })
                        self.assertEqual(response.status_code, 403)
                for suffix in [f'update/{task.task_id}/', f'delete/{task.task_id}/']:
                    self.assertEqual(self.post_json(base, suffix, {'task_pk': task.pk, 'status': 'closed'}).status_code, 404)
        self.assertEqual(Task.objects.count(), 3)
        self.assertEqual(TaskActivity.objects.count(), activity_count)
        self.assertFalse(TaskAttachment.objects.exists())

    def test_mixed_bulk_operations_are_atomic(self):
        for base in ['/tasks/', self.url()]:
            for suffix in ['bulk-update-status/', 'delete/']:
                self.assertEqual(self.post_json(base, suffix, {'task_pks': [self.public_task.pk, self.task.pk], 'status': 'closed'}).status_code, 403)
            for action, ids in [('delete_project', {'project_ids': [self.public.pk, self.project.pk]}),
                                ('delete_section', {'section_ids': [self.public_section.pk, self.section.pk]})]:
                self.assertEqual(self.client.post(base, {'action': action, **ids}).status_code, 403)
        self.public_task.refresh_from_db()
        self.assertEqual(self.public_task.status, 'new')
        self.assertEqual(Task.objects.count(), 3)
        self.assertEqual(TaskProject.objects.count(), 2)

    def test_creation_and_moves_cannot_target_observed_group(self):
        for form_class in [TaskForm, TaskModalForm]:
            form = form_class(user=self.owner, viewer=self.observer, workplace=self.workspace)
            self.assertFalse(form.fields['section'].queryset.filter(pk=self.section.pk).exists())
            self.assertTrue(form.fields['section'].queryset.filter(pk=self.public_section.pk).exists())
        for base in ['/tasks/', self.url()]:
            self.client.post(base, {'action': 'create_task_modal', 'section': self.section.pk, 'title': 'Nie twórz'})
            self.client.post(base + f'view-task/{self.public_task.task_id}/?task_pk={self.public_task.pk}', {
                'title': 'Nie przenoś', 'section': self.section.pk, 'project': self.project.pk,
                'status': 'new', 'priority': 'none', 'task_type': 'general',
            })
        self.assertFalse(Task.objects.filter(title='Nie twórz').exists())
        self.public_task.refresh_from_db()
        self.assertEqual(self.public_task.section_id, self.public_section.pk)
        self.assertEqual(self.public_task.title, 'Wspólne zadanie')

    def test_legacy_descendants_and_cascades_preserve_readonly_children(self):
        Task.objects.filter(pk=self.child.pk).update(section=self.public_section)
        self.assertTrue(visible_to(Task.objects.all(), self.observer).filter(pk=self.child.pk).exists())
        self.assertFalse(editable_to(Task.objects.all(), self.observer).filter(pk=self.child.pk).exists())
        Task.objects.filter(pk=self.task.pk).update(parent=self.public_task)
        self.assertEqual(self.post_json(self.url(), f'delete/{self.public_task.task_id}/', {'task_pk': self.public_task.pk}).status_code, 403)
        self.assertEqual(self.client.post(self.url(), {'action': 'delete_section', 'section_id': self.public_section.pk}).status_code, 403)
        self.assertTrue(Task.objects.filter(pk=self.public_task.pk).exists())

    def test_observer_cannot_manage_team_or_deadlines_even_as_workspace_admin(self):
        for action in ['share', 'role', 'remove']:
            self.assertEqual(self.team(action=action, member_id=self.membership.pk,
                email=self.candidate.email, role='admin', invitation_id=123).status_code, 403)
        self.assertEqual(self.client.get(self.url(f'projects/{self.project.pk}/team/candidates/'), {'q': 'candidate'}).status_code, 403)
        for action in ['enable_project_deadline_rules', 'reset_project_deadline_rules',
                       'create_project_deadline_rule', 'update_project_deadline_rule', 'delete_project_deadline_rule']:
            self.assertEqual(self.client.post(reverse('project_field_settings'), {
                'project_id': self.project.pk, 'action': action, 'days': 1, 'color': '#ffffff',
            }).status_code, 404)
        self.assertFalse(self.project.use_custom_deadline_rules)

    def test_owner_and_admin_share_with_observer_and_owner_can_change_role(self):
        for inviter in [self.owner, self.admin]:
            self.login(inviter)
            self.assertEqual(self.team(action='share', email=self.candidate.email, role='observer').status_code, 200)
            self.login(self.candidate)
            grant = self.project.memberships.get(user=self.candidate)
            self.assertEqual(grant.role, 'observer')
            self.assertFalse(editable_to(TaskProject.objects.all(), self.candidate).filter(pk=self.project.pk).exists())
            self.login(self.admin)
            self.assertEqual(self.team(action='role', member_id=grant.pk, role='member').status_code, 403)
            self.assertEqual(self.team(action='remove', member_id=grant.pk).status_code, 200)
        self.login(self.owner)
        self.assertEqual(self.team(action='role', member_id=self.membership.pk, role='member').status_code, 200)
        self.login(self.observer)
        self.assertEqual(self.post_json(self.url(), f'update/{self.task.task_id}/', {'task_pk': self.task.pk, 'status': 'closed'}).status_code, 200)
        self.login(self.owner)
        self.assertEqual(self.team(action='role', member_id=self.membership.pk, role='observer').status_code, 200)
        self.login(self.observer)
        self.assertEqual(self.post_json(self.url(), f'update/{self.task.task_id}/', {'task_pk': self.task.pk, 'status': 'new'}).status_code, 404)

    def test_admin_can_revoke_observer_access_immediately(self):
        self.login(self.admin)
        self.assertEqual(self.team(action='share', email=self.candidate.email, role='observer').status_code, 200)
        grant = self.project.memberships.get(user=self.candidate)
        self.assertTrue(visible_to(TaskProject.objects.all(), self.candidate).filter(pk=self.project.pk).exists())
        self.assertEqual(self.team(action='remove', member_id=grant.pk).status_code, 200)
        self.assertFalse(visible_to(TaskProject.objects.all(), self.candidate).filter(pk=self.project.pk).exists())

    def test_readonly_ui_and_workspace_boundaries(self):
        response = self.client.get(self.url(f'view-task/{self.task.task_id}/?task_pk={self.task.pk}'))
        self.assertFalse(response.context['can_edit_task'])
        self.assertFalse(response.context['can_manage_task'])
        self.assertContains(response, 'data-task-readonly="true"')
        self.assertNotContains(response, 'name="activity_comment"')
        self.assertNotContains(response, 'id="task-work-log-modal"')
        self.assertEqual(response.context['form']['section'].value(), self.section.pk)
        page = self.client.get(self.url(f'?project={self.project.pk}'))
        self.assertFalse(page.context['active_project'].can_manage)
        self.assertFalse(page.context['can_create_issue'])
        self.assertFalse(page.context['project_access_data'][str(self.project.pk)]['canEdit'])
        self.assertEqual(len(page.context['project_sections']), 1)
        WorkplaceMembership.objects.create(workplace=self.other_workspace, user=self.observer)
        other = scoped_workplace_app_path(self.other_workspace, 'tasks', f'view-task/{self.task.task_id}/?task_pk={self.task.pk}')
        self.assertIn(self.client.get(other, follow=True).status_code, [403, 404])
        self.membership.delete()
        self.assertEqual(self.client.get(self.url(f'view-task/{self.task.task_id}/?task_pk={self.task.pk}')).status_code, 404)

    def test_workspace_owner_has_no_edit_override_for_observer_membership(self):
        self.project.private_owner = self.admin
        self.project.save(update_fields=['private_owner'])
        TaskProjectMembership.objects.create(project=self.project, user=self.owner, role='observer')
        self.login(self.owner)
        self.assertTrue(visible_to(Task.objects.all(), self.owner).filter(pk=self.task.pk).exists())
        self.assertFalse(editable_to(Task.objects.all(), self.owner).filter(pk=self.task.pk).exists())
        self.assertEqual(self.post_json(self.url(), f'update/{self.task.task_id}/', {'task_pk': self.task.pk, 'status': 'closed'}).status_code, 404)
        self.assertEqual(self.team(action='share', email=self.candidate.email, role='member').status_code, 403)
        self.login(self.admin)
        self.assertEqual(self.post_json(self.url(), f'update/{self.task.task_id}/', {'task_pk': self.task.pk, 'status': 'closed'}).status_code, 200)
