"""Team access contracts across the shared application, including revocation."""
import json
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from documents.models import Document, DocumentLibrary, WorkspaceDocument
from documents import office_service
from planner.models import CalendarEvent
from spaces.models import SpaceTask, SpaceTaskFile
from spaces.testing import make_task
from .models import WorkplaceMembership, create_workplace_for_user
from .services import workplaces_for_user, scoped_workplace_app_path


class TeamAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='team-owner', email='owner@team.test')
        cls.member = users.objects.create_user(username='team-member', email='member@team.test')
        cls.admin = users.objects.create_user(username='team-admin', email='admin@team.test')
        cls.outsider = users.objects.create_user(username='outside-team', email='outside@team.test')
        cls.team = create_workplace_for_user(cls.owner, 'Zespół wdrożeniowy')
        cls.private = create_workplace_for_user(cls.owner, 'Prywatne właściciela')
        cls.personal = create_workplace_for_user(cls.member, 'Prywatne członka')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.team, user=cls.member, role='member')
        cls.admin_membership = WorkplaceMembership.objects.create(workplace=cls.team, user=cls.admin, role='admin')
        cls.task = make_task(user=cls.owner, workplace=cls.team, title='Zespołowe wdrożenie', assignee=cls.member)
        cls.other_task = make_task(user=cls.owner, workplace=cls.private, title='Tajne prywatne zadanie')
        cls.task_space = cls.task.space
        cls.space_task = cls.task
        cls.event = CalendarEvent.objects.create(user=cls.owner, workplace=cls.team, title='Zespołowe spotkanie', start=timezone.now(), end=timezone.now()+timedelta(hours=1))
        cls.library = DocumentLibrary.objects.create(owner=cls.owner, workplace=cls.team, name='Zespołowy dysk')
        cls.document = Document.objects.create(owner=cls.owner, workplace=cls.team, library=cls.library, title='Zespołowy plik', filename='team.txt')
        cls.office = WorkspaceDocument.objects.create(owner=cls.owner, workplace=cls.team, title='Zespołowy dokument', kind='file', filename='team.docx')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.team.pk
        session.save()

    def url(self, app='spaces', suffix=''):
        return scoped_workplace_app_path(self.team, app, suffix)

    def task_url(self, task=None, suffix=''):
        task = task or self.task
        return scoped_workplace_app_path(self.team, 'space', f'{task.space.slug}/tasks/{task.work_item.key}/{suffix}')

    def create_task(self, **data):
        return self.client.post(self.url('space', f'{self.task_space.slug}/items/create/'),
            {'title': 'Zadanie członka', 'priority': 'medium', 'work_type': 'task', **data})

    def post_json(self, url, data):
        return self.client.post(url, json.dumps(data), content_type='application/json')

    def test_workspace_membership_and_private_boundaries(self):
        self.assertSetEqual(set(workplaces_for_user(self.member)), {self.personal, self.team})
        response = self.client.get(reverse('workplaces:workplaces'))
        shared = next(space for space in response.context['workplaces'] if space.pk == self.team.pk)
        self.assertEqual(shared.team_member_count, 3)
        self.assertEqual(self.client.get(self.url()).status_code, 200)
        self.assertEqual(self.client.get(self.task_url()).status_code, 200)
        self.assertEqual(self.client.get(self.task_url(self.other_task)).status_code, 404)
        self.assertEqual(self.client.get(scoped_workplace_app_path(self.private, 'spaces')).status_code, 302)

    def test_every_module_is_visible_to_members(self):
        for app in ['spaces', 'calendar', 'documents', 'office']:
            with self.subTest(app=app):
                self.assertEqual(self.client.get(self.url(app)).status_code, 200)
        self.assertContains(self.client.get(self.url('documents')), self.library.name)
        self.assertContains(self.client.get(self.url('office')), self.office.title)

    def test_search_dashboard_and_notifications_use_team_scope(self):
        for task in (self.task, self.other_task):
            task.activities.create(actor=self.owner, kind='comment', action='commented', message='Komentarz')
        response = self.client.get(reverse('global_search'), {'q': 'Zespołow'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.task.title, json.dumps(response.json(), ensure_ascii=False))
        self.assertIn(self.document.title, json.dumps(response.json(), ensure_ascii=False))
        self.assertNotIn(self.other_task.title, json.dumps(response.json(), ensure_ascii=False))
        self.assertEqual(self.client.get(reverse('home')).context['columns'][0][0]['count'], 1)
        notifications = self.client.get(reverse('notifications'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(notifications.status_code, 200)
        self.assertIn(self.task.title, notifications.json()['html'])
        self.assertNotIn(self.other_task.title, notifications.json()['html'])

    def test_task_assignment_filter_uses_current_space_tasks(self):
        other = make_task(user=self.owner, workplace=self.team, space=self.task_space, title='Dla administratora', assignee=self.admin)
        response = self.client.get(self.url('space', f'{self.task_space.slug}/'), {'assignee': self.member.pk, 'view': 'list'})
        ids = {item.task_id for item in response.context['items']}
        self.assertEqual(ids, {self.task.pk})
        self.assertNotIn(other.pk, ids)

    def test_member_creates_task_in_owner_scope_with_real_actor(self):
        response = self.create_task(assignee=self.admin.pk)
        self.assertEqual(response.status_code, 302)
        task = SpaceTask.objects.get(title='Zadanie członka')
        self.assertEqual((task.space.user_id, task.space.workplace_id, task.assignee_id), (self.owner.pk, self.team.pk, self.admin.pk))
        self.assertEqual(task.activities.get(action='created').actor, self.member)
        self.membership.delete()
        self.assertTrue(SpaceTask.objects.filter(pk=task.pk).exists())

    def test_comments_and_status_keep_actor_completion_and_history(self):
        response = self.client.post(self.task_url(), {'action': 'comment', 'activity_comment': 'Gotowe do odbioru'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.task.activities.get(kind='comment').actor, self.member)
        response = self.client.post(self.task_url(suffix='action/'), {'action': 'status', 'status': 'closed'}, HTTP_X_WORK_ACTION='true')
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_completed)
        self.assertIsNotNone(self.task.completion_date)
        self.assertEqual(self.task.activities.get(action='status_changed').actor, self.member)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.task_url()), 'Gotowe do odbioru')

    def test_retired_status_posts_cannot_mutate_current_or_legacy_tasks(self):
        self.assertEqual(self.client.post(self.url('tasks', 'update/1/'), {'task_pk': self.task.pk, 'status': 'closed'}).status_code, 404)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'new')

    def test_assignment_choices_and_forged_assignment(self):
        form = self.client.get(self.task_url()).context['form']
        self.assertSetEqual(set(form.fields['assignee'].queryset.values_list('pk', flat=True)), {self.owner.pk, self.member.pk, self.admin.pk})
        response = self.create_task(title='Niedozwolone przypisanie', assignee=self.outsider.pk)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SpaceTask.objects.filter(title='Niedozwolone przypisanie').exists())

    def test_member_calendar_writes_preserve_owner(self):
        response = self.client.post(self.url('calendar', f'events/{self.event.pk}/update/'), {'title': 'Zmienione spotkanie',
            'start': '2026-09-24T10:00', 'end': '2026-09-24T11:00', 'color': 'blue'})
        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.user_id, self.owner.pk)

    def test_member_can_download_both_catalogs_and_attachments_then_loses_access(self):
        with tempfile.TemporaryDirectory() as directory:
            objects = [self.document, self.office, SpaceTaskFile(task=self.task, filename='team.txt', file_size=11)]
            urls = [self.url('documents', f'{self.document.pk}/download/'), self.url('office', f'{self.office.pk}/download/')]
            for item in objects:
                field = item._meta.get_field('file')
                old = field.storage
                self.addCleanup(setattr, field, 'storage', old)
                field.storage = FileSystemStorage(directory)
                item.file.storage = field.storage
                item.file.save('team.txt', ContentFile(b'Team access'), save=True)
            urls += [objects[2].get_url()]
            for url in urls:
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, url)
                self.assertEqual(b''.join(response.streaming_content), b'Team access')
            self.membership.delete()
            for url in urls:
                response = self.client.get(url, follow=True)
                self.assertNotEqual(response.get('Content-Disposition', '').split(';')[0], 'attachment')

    def test_member_can_create_drive_and_office_board(self):
        response = self.client.post(self.url('documents', 'libraries/create/'), {'name': 'Dysk członka', 'icon_color': '#2563eb'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(DocumentLibrary.objects.filter(owner=self.owner, workplace=self.team, name='Dysk członka').exists())
        response = self.client.post(self.url('office', 'create/'), {'title': 'Mapa zespołu', 'kind': 'board'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(WorkspaceDocument.objects.filter(owner=self.owner, workplace=self.team, title='Mapa zespołu').exists())

    def test_revocation_blocks_session_urls_search_and_office_tokens(self):
        source_token = office_service.capability(self.office, 'source', self.member)
        callback_token = office_service.capability(self.office, 'callback', self.member)
        self.assertTrue(office_service.check_capability(self.office, source_token, 'source'))
        self.client.force_login(self.owner)
        response = self.client.post(reverse('workplaces:member-update', args=[self.team.pk, self.membership.pk]), {'action': 'remove'})
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.member)
        for purpose, token in [('source', source_token), ('callback', callback_token)]:
            self.assertFalse(office_service.check_capability(self.office, token, purpose))
        self.assertEqual(self.client.get(self.url(suffix=f'view-task/{self.task.work_item.key}/')).status_code, 302)
        self.assertNotIn(self.task.title, json.dumps(self.client.get(reverse('global_search'), {'q': 'Zespołow'}).json(), ensure_ascii=False))
        self.assertEqual(self.post_json(self.url(suffix=f'update/{self.task.work_item.key}/'), {'task_pk': self.task.pk, 'status': 'closed'}).status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'new')

    def test_manual_addition_is_immediate_and_preserves_the_managers_active_workspace(self):
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.private.pk
        session.save()
        self.assertFalse(self.team.memberships.filter(user=self.outsider).exists())
        response = self.client.post(reverse('workplaces:team', args=[self.team.pk]), {'user_id': self.outsider.pk, 'role': 'member'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.team.memberships.filter(user=self.outsider, role='member', is_active=True).exists())
        self.assertEqual(self.client.session['active_workplace_id'], self.private.pk)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_manual_addition_requires_an_existing_active_account_identity(self):
        inactive = get_user_model().objects.create_user(username='inactive-add', email='inactive-add@team.test', is_active=False)
        self.client.force_login(self.owner)
        url = reverse('workplaces:team', args=[self.team.pk])
        for values in [
            {'user_id': '999999999'}, {'user_id': 'bad'}, {'user_id': inactive.pk},
            {'user_id': self.owner.pk}, {'email': self.outsider.email},
        ]:
            with self.subTest(values=values):
                response = self.client.post(url, {**values, 'role': 'member'})
                self.assertEqual(response.status_code, 200)
                self.assertIn('user_id', response.context['add_form'].errors)
        self.assertFalse(self.team.memberships.filter(user=self.outsider).exists())
        self.assertFalse(self.team.memberships.filter(user=inactive).exists())

    def test_role_escalation_and_workspace_management_are_blocked(self):
        team_url = reverse('workplaces:team', args=[self.team.pk])
        self.assertEqual(self.client.post(team_url, {'user_id': self.outsider.pk, 'role': 'admin'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('workplaces:update', args=[self.team.pk]), {'name': 'Zmiana'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('workplaces:delete', args=[self.team.pk])).status_code, 404)
        self.client.force_login(self.admin)
        response = self.client.post(team_url, {'user_id': self.outsider.pk, 'role': 'admin'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('role', response.context['add_form'].errors)
        self.assertFalse(self.team.memberships.filter(user=self.outsider).exists())
        self.assertEqual(self.client.post(reverse('workplaces:member-update', args=[self.team.pk, self.admin_membership.pk]), {'action': 'role', 'role': 'owner'}).status_code, 403)
        self.assertEqual(self.client.post(team_url, {'user_id': self.outsider.pk, 'role': 'member'}).status_code, 302)
        membership = self.team.memberships.get(user=self.outsider)
        self.assertEqual(membership.role, 'member')
        self.assertEqual(self.client.post(reverse('workplaces:member-update', args=[self.team.pk, membership.pk]), {'action': 'remove'}).status_code, 302)
        self.assertFalse(self.team.memberships.filter(user=self.outsider).exists())

    def test_owner_can_promote_and_admin_can_remove_member_but_not_owner(self):
        self.client.force_login(self.owner)
        url = reverse('workplaces:member-update', args=[self.team.pk, self.membership.pk])
        self.assertEqual(self.client.post(url, {'action': 'role', 'role': 'admin'}).status_code, 302)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, 'admin')
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(url, {'action': 'remove'}).status_code, 403)
        owner_membership = self.team.memberships.get(user=self.owner)
        self.assertEqual(self.client.post(reverse('workplaces:member-update', args=[self.team.pk, owner_membership.pk]), {'action': 'remove'}).status_code, 403)
        self.membership.role = 'member'
        self.membership.save()
        self.assertEqual(self.client.post(url, {'action': 'remove'}).status_code, 302)
        self.assertTrue(SpaceTask.objects.filter(pk=self.task.pk).exists())


    def test_workspace_slugs_are_unique_across_owners(self):
        other = create_workplace_for_user(self.member, self.team.name)
        self.assertNotEqual(other.slug, self.team.slug)
        self.assertEqual(self.client.get(scoped_workplace_app_path(other, 'spaces')).status_code, 200)
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_scoped_status_records_actor_and_cannot_target_another_workspace(self):
        response = self.client.post(self.task_url(suffix='action/'), {'action': 'status', 'status': 'closed'}, HTTP_X_WORK_ACTION='true')
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.task_url(self.other_task, 'action/'), {'action': 'status', 'status': 'closed'}, HTTP_X_WORK_ACTION='true')
        self.assertEqual(response.status_code, 404)
        self.task.refresh_from_db()
        self.other_task.refresh_from_db()
        self.assertTrue(self.task.is_completed)
        self.assertEqual(self.other_task.status, 'new')
        self.assertEqual(self.task.activities.get(action='status_changed').actor, self.member)

    def test_removal_invalidates_all_existing_office_sessions(self):
        token = office_service.capability(self.office, 'callback', self.owner)
        self.assertTrue(office_service.check_capability(self.office, token, 'callback'))
        self.client.force_login(self.owner)
        response = self.client.post(reverse('workplaces:member-update', args=[self.team.pk, self.membership.pk]), {'action': 'remove'})
        self.assertEqual(response.status_code, 302)
        self.office.refresh_from_db()
        self.assertFalse(office_service.check_capability(self.office, token, 'callback'))
        self.assertTrue(office_service.check_capability(self.office, office_service.capability(self.office, 'callback', self.owner), 'callback'))

    def test_manager_can_reactivate_membership_without_changing_active_workspace(self):
        self.membership.is_active = False
        self.membership.save(update_fields=['is_active'])
        self.assertNotIn(self.team, workplaces_for_user(self.member))
        self.assertEqual(self.client.get(self.url()).status_code, 302)
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.private.pk
        session.save()
        self.assertEqual(self.client.post(reverse('workplaces:team', args=[self.team.pk]), {'user_id': self.member.pk, 'role': 'member'}).status_code, 302)
        self.assertEqual(self.client.session['active_workplace_id'], self.private.pk)
        self.membership.refresh_from_db()
        self.assertTrue(self.membership.is_active)
        self.assertEqual(self.membership.role, 'member')
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(self.url()).status_code, 200)
