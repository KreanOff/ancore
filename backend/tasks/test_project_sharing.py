"""Workspace-only project grants must apply to all existing privacy boundaries."""
import json
from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from dashboard.collaboration import mention_people
from dashboard.notification_service import notification_sources
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .access import visible_to
from .forms import TaskModalForm
from .models import Task, TaskActivity, TaskAttachment, TaskProject, TaskProjectTemplate, TaskSection, TaskProjectInvitation


class ProjectSharingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='share-owner', email='owner@share.test')
        cls.author = users.objects.create_user(username='share-author', email='author@share.test')
        cls.member = users.objects.create_user(username='share-member', email='member@share.test')
        cls.outsider = users.objects.create_user(username='share-outsider', email='outsider@share.test')
        cls.inactive = users.objects.create_user(username='share-inactive', email='inactive@share.test', is_active=False)
        cls.workspace = create_workplace_for_user(cls.owner, 'Udostępnianie')
        cls.other = create_workplace_for_user(cls.owner, 'Inna przestrzeń')
        for user in [cls.author, cls.member, cls.inactive]:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=user)
        WorkplaceMembership.objects.create(workplace=cls.other, user=cls.outsider)
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Poufna strategia',
                                                 visibility='private', private_owner=cls.author)
        cls.section = TaskSection.objects.create(project=cls.project, title='Poufna grupa')
        cls.task = Task.objects.create(user=cls.owner, section=cls.section, title='Poufne zadanie', due_at=timezone.now())
        cls.child = Task.objects.create(user=cls.owner, section=cls.section, parent=cls.task, title='Poufne podzadanie')
        cls.activity = TaskActivity.objects.create(task=cls.task, actor=cls.author, action='commented', kind='comment', message='Poufny komentarz')

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'tasks', suffix)

    def edit(self, **data):
        return self.client.post(self.url(), dict(action='edit_project', project_id=self.project.pk,
                                                name=self.project.name, **data))

    def setUp(self):
        self.login(self.author)

    def test_creation_does_not_allow_bypassing_team_permissions_with_old_checkbox_payload(self):
        response = self.client.post(self.url(), dict(action='create_project', name='Nowy współdzielony',
            visibility='private', sharing_present='1', shared_with=[self.owner.pk, self.member.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TaskProject.objects.filter(name='Nowy współdzielony').exists())

    def test_grant_opens_directories_tasks_forms_search_calendar_and_notifications(self):
        response = self.client.post(self.url(f'projects/{self.project.pk}/team/'), dict(action='share', email=self.member.email, role='member'))
        self.assertEqual(response.status_code, 200)
        self.login(self.member)
        for base in [self.url(), '/tasks/']:
            for suffix in ['', f'groups/{self.section.pk}/', f'view-task/{self.task.task_id}/?task_pk={self.task.pk}',
                           f'view-subtask/{self.child.task_id}/?task_pk={self.child.pk}']:
                response = self.client.get(base + suffix, follow=True)
                self.assertEqual(response.status_code, 200, suffix)
                self.assertContains(response, 'Poufn')
        form = TaskModalForm(user=self.owner, viewer=self.member, workplace=self.workspace)
        self.assertTrue(form.fields['section'].queryset.filter(pk=self.section.pk).exists())
        self.assertGreater(self.client.get(reverse('global_search'), {'q': 'Poufn'}).json()['total'], 0)
        self.assertTrue(notification_sources(self.member)['tasks'].filter(task=self.task).exists())
        self.assertCountEqual(mention_people(self.task), [self.author, self.member])
        events = self.client.get(scoped_workplace_app_path(self.workspace, 'calendar', 'events/'), {
            'start': (timezone.now()-timedelta(days=1)).isoformat(), 'end': (timezone.now()+timedelta(days=1)).isoformat()})
        self.assertIn('Poufne zadanie', json.dumps(events.json(), ensure_ascii=False))
        self.assertEqual(self.client.post(self.url(f'follow/project/{self.project.pk}/'), {'following': 'true'}).status_code, 200)

    def test_revocation_closes_stale_urls_forms_notifications_and_edits(self):
        self.project.shared_with.add(self.member)
        self.assertEqual(self.client.post(self.url(f'projects/{self.project.pk}/team/'), dict(action='remove', member_id=self.project.memberships.get(user=self.member).pk)).status_code, 200)
        self.login(self.member)
        self.assertNotContains(self.client.get(self.url()), self.project.name)
        self.assertEqual(self.client.get(self.url(f'view-task/{self.task.task_id}/')).status_code, 404)
        self.assertEqual(self.edit(visibility='public').status_code, 404)
        self.assertFalse(notification_sources(self.member)['tasks'].filter(task=self.task).exists())
        self.assertNotIn(self.member, mention_people(self.task))
        self.assertFalse(TaskModalForm(user=self.owner, viewer=self.member, workplace=self.workspace).fields['section'].queryset.filter(pk=self.section.pk).exists())

    def test_shared_attachment_download_is_protected_after_revocation(self):
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            attachment = TaskAttachment.objects.create(task=self.task, filename='plan.txt', file_size=4,
                file=SimpleUploadedFile('plan.txt', b'plan', content_type='text/plain'))
            self.project.shared_with.add(self.member)
            self.login(self.member)
            download = self.url(f'attachments/{attachment.pk}/download/')
            response = self.client.get(download)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'plan')
            self.project.shared_with.clear()
            self.assertEqual(self.client.get(download).status_code, 404)

    def test_recipient_can_edit_content_but_cannot_publish_or_change_grants(self):
        self.project.shared_with.add(self.member)
        self.login(self.member)
        self.assertEqual(self.edit(description='Zmiana uczestnika').status_code, 302)
        for data in [dict(visibility='public'), dict(sharing_present='1', shared_with=[self.owner.pk]),
                     dict(sharing_present='1', shared_with=[])]:
            response = self.edit(**data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['project_rename_form'].errors)
        self.project.refresh_from_db()
        self.assertEqual(self.project.description, 'Zmiana uczestnika')
        self.assertEqual((self.project.visibility, self.project.private_owner_id), ('private', self.author.pk))
        self.assertEqual(list(self.project.shared_with.all()), [self.member])

    def test_forged_outside_inactive_self_and_mixed_recipients_are_atomic_errors(self):
        for ids in [[self.outsider.pk], [self.inactive.pk], [self.author.pk], [self.member.pk, self.outsider.pk], [9999999]]:
            response = self.edit(sharing_present='1', shared_with=ids, description='Nie zapisuj')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['project_rename_form'].non_field_errors())
            self.assertFalse(self.project.shared_with.exists())
            self.project.refresh_from_db()
            self.assertEqual(self.project.description, '')

    def test_old_form_preserves_grants_and_publication_clears_them(self):
        self.project.shared_with.add(self.member)
        self.assertEqual(self.edit(description='Stary formularz').status_code, 302)
        self.assertTrue(self.project.shared_with.filter(pk=self.member.pk).exists())
        self.assertEqual(self.edit(visibility='public').status_code, 302)
        self.assertFalse(self.project.shared_with.exists())
        self.assertEqual(self.edit(visibility='private').status_code, 302)
        self.assertFalse(visible_to(TaskProject.objects.all(), self.member).filter(pk=self.project.pk).exists())

    def test_removed_or_disabled_members_do_not_recover_grants_on_rejoining(self):
        for remove in [False, True]:
            self.project.shared_with.add(self.member)
            membership = WorkplaceMembership.objects.get(workplace=self.workspace, user=self.member)
            if remove:
                membership.delete()
                WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
            else:
                membership.is_active = False
                membership.save(update_fields=['is_active'])
                membership.is_active = True
                membership.save(update_fields=['is_active'])
            self.assertFalse(self.project.shared_with.filter(pk=self.member.pk).exists())
            self.assertFalse(visible_to(TaskProject.objects.all(), self.member).filter(pk=self.project.pk).exists())

    def test_wrong_workspace_or_deleted_owner_still_denies_grants(self):
        self.project.shared_with.add(self.outsider, self.member)
        self.assertFalse(visible_to(TaskProject.objects.all(), self.outsider).filter(pk=self.project.pk).exists())
        self.author.delete()
        self.assertFalse(visible_to(TaskProject.objects.all(), self.member).filter(pk=self.project.pk).exists())

    def test_new_workspace_member_does_not_inherit_private_access(self):
        self.project.shared_with.add(self.member)
        WorkplaceMembership.objects.create(workplace=self.workspace, user=self.outsider)
        self.assertFalse(visible_to(TaskProject.objects.all(), self.outsider).filter(pk=self.project.pk).exists())

    def test_recipient_template_is_private_to_snapshot_author_without_copied_grants(self):
        self.project.shared_with.add(self.member)
        self.login(self.member)
        response = self.client.post(self.url(), dict(action='save_project_template', project_id=self.project.pk))
        self.assertEqual(response.status_code, 302)
        template = TaskProjectTemplate.objects.get()
        self.assertEqual((template.visibility, template.private_owner_id), ('private', self.member.pk))
        self.assertFalse(visible_to(TaskProjectTemplate.objects.all(), self.author).exists())
        response = self.client.post(self.url(), dict(action='create_project', name='Prywatna kopia', template=template.pk))
        self.assertEqual(response.status_code, 302)
        copied = TaskProject.objects.get(name='Prywatna kopia')
        self.assertEqual((copied.visibility, copied.private_owner_id), ('private', self.member.pk))
        self.assertFalse(copied.shared_with.exists())

    def test_member_lists_are_scoped_and_hidden_projects_absent_from_page_metadata(self):
        self.login(self.owner)
        response = self.client.get(self.url())
        self.assertNotIn(str(self.project.pk), response.context['project_access_data'])
        self.assertEqual(self.client.get(self.url(f'projects/{self.project.pk}/team/')).status_code, 404)
        self.assertNotContains(response, self.outsider.email)
