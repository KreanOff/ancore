"""Team access contracts across the shared application, including revocation."""
import json
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from contacts.models import Company, Contact
from documents.models import Document, DocumentLibrary, WorkspaceDocument
from documents import office_service
from kanban.models import Kanban, KanbanProject, KanbanSection, KanbanAttachment
from planner.models import CalendarEvent
from tasks.forms import TaskForm, TaskModalForm, TaskProjectForm, TaskSectionForm
from tasks.models import Task, TaskProject, TaskSection, TaskAttachment
from .models import WorkplaceInvitation, WorkplaceMembership, create_workplace_for_user
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
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.team, name='Wspólny projekt')
        cls.section = TaskSection.objects.create(project=cls.project, title='Realizacja')
        cls.task = Task.objects.create(user=cls.owner, workplace=cls.team, section=cls.section, title='Zespołowe wdrożenie', assignee=cls.member)
        cls.other_task = Task.objects.create(user=cls.owner, workplace=cls.private, title='Tajne prywatne zadanie')
        cls.space = KanbanProject.objects.create(user=cls.owner, workplace=cls.team, name='Zespołowa tablica')
        cls.board = KanbanSection.objects.create(project=cls.space, title='Realizacja')
        cls.card = Kanban.objects.create(user=cls.owner, workplace=cls.team, section=cls.board, title='Zespołowa karta')
        cls.company = Company.objects.create(owner=cls.owner, workplace=cls.team, name='Zespołowa firma')
        cls.contact = Contact.objects.create(user=cls.owner, workplace=cls.team, first_name='Zespołowy', last_name='Kontakt')
        cls.event = CalendarEvent.objects.create(user=cls.owner, workplace=cls.team, title='Zespołowe spotkanie', start=timezone.now(), end=timezone.now()+timedelta(hours=1))
        cls.library = DocumentLibrary.objects.create(owner=cls.owner, workplace=cls.team, name='Zespołowy dysk')
        cls.document = Document.objects.create(owner=cls.owner, workplace=cls.team, library=cls.library, title='Zespołowy plik', filename='team.txt')
        cls.office = WorkspaceDocument.objects.create(owner=cls.owner, workplace=cls.team, title='Zespołowy dokument', kind='file', filename='team.docx')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.team.pk
        session.save()

    def url(self, app='tasks', suffix=''):
        return scoped_workplace_app_path(self.team, app, suffix)

    def post_json(self, url, data):
        return self.client.post(url, json.dumps(data), content_type='application/json')

    def test_workspace_membership_and_private_boundaries(self):
        self.assertSetEqual(set(workplaces_for_user(self.member)), {self.personal, self.team})
        response = self.client.get(reverse('workplaces:workplaces'))
        shared = next(space for space in response.context['workplaces'] if space.pk == self.team.pk)
        self.assertEqual(shared.team_member_count, 3)
        self.assertEqual(self.client.get(self.url()).status_code, 200)
        self.assertEqual(self.client.get(self.url(suffix=f'view-task/{self.task.task_id}/')).status_code, 200)
        self.assertEqual(self.client.get(self.url(suffix=f'view-task/{self.task.task_id}/'), {'task_pk': self.other_task.pk}).status_code, 404)
        self.assertEqual(self.client.get(scoped_workplace_app_path(self.private, 'tasks')).status_code, 302)

    def test_every_module_is_visible_to_members(self):
        for app in ['tasks', 'kanban', 'contacts', 'calendar', 'documents', 'office']:
            with self.subTest(app=app):
                self.assertEqual(self.client.get(self.url(app)).status_code, 200)
        self.assertContains(self.client.get(self.url('documents')), self.library.name)
        self.assertContains(self.client.get(self.url('office')), self.office.title)
        self.assertContains(self.client.get(self.url('contacts', 'companies/')), self.company.name)

    def test_search_dashboard_and_notifications_use_team_scope(self):
        response = self.client.get(reverse('global_search'), {'q': 'Zespołow'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.task.title, json.dumps(response.json(), ensure_ascii=False))
        self.assertIn(self.document.title, json.dumps(response.json(), ensure_ascii=False))
        self.assertNotIn(self.other_task.title, json.dumps(response.json(), ensure_ascii=False))
        self.assertEqual(self.client.get(reverse('home')).context['dashboard_totals']['total'], 2)
        notifications = self.client.get(reverse('notifications'))
        self.assertContains(notifications, self.task.title)
        self.assertNotContains(notifications, self.other_task.title)

    def test_my_tasks_filters_by_viewer_in_shared_space(self):
        Task.objects.create(user=self.owner, workplace=self.team, section=self.section, title='Dla administratora', assignee=self.admin)
        response = self.client.get(self.url(), {'view': 'my-tasks'})
        self.assertEqual(response.context['task_window']['total_tasks'], 1)
        self.assertEqual(list(response.context['task_window']['queryset']), [self.task])

    def test_member_creates_task_in_owner_scope_with_real_actor(self):
        response = self.client.post(self.url(), {'action': 'create_task_modal', 'project_id': self.project.pk,
            'section': self.section.pk, 'title': 'Zadanie członka', 'priority': 'medium', 'status': 'new', 'assignee': self.admin.pk})
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(title='Zadanie członka')
        self.assertEqual((task.user_id, task.workplace_id, task.assignee_id), (self.owner.pk, self.team.pk, self.admin.pk))
        self.assertEqual(task.activities.get(action='created').actor_id, self.member.pk)
        self.membership.delete()
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_comments_and_status_keep_actor_completion_and_history(self):
        detail = self.url(suffix=f'view-task/{self.task.task_id}/')
        response = self.client.post(detail, {'action': 'add_activity_comment', 'activity_comment': 'Gotowe do odbioru'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.task.activities.get(kind='comment').actor_id, self.member.pk)
        response = self.post_json(self.url(suffix=f'update/{self.task.task_id}/'), {'task_pk': self.task.pk, 'status': 'closed'})
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_completed)
        self.assertIsNotNone(self.task.completion_date)
        self.assertEqual(self.task.activities.filter(action='status_changed').latest('pk').actor_id, self.member.pk)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(detail), 'Gotowe do odbioru')

    def test_legacy_post_uses_active_team_and_rejects_foreign_pk(self):
        response = self.post_json(reverse('tasks:update_task_status', args=[self.task.task_id]), {'task_pk': self.task.pk, 'status': 'closed'})
        self.assertEqual(response.status_code, 200)
        response = self.post_json(reverse('tasks:update_task_status', args=[self.other_task.task_id]), {'task_pk': self.other_task.pk, 'status': 'closed'})
        self.assertEqual(response.status_code, 404)
        self.other_task.refresh_from_db()
        self.assertEqual(self.other_task.status, 'new')

    def test_assignment_choices_and_forged_assignment(self):
        expected = {self.owner.pk, self.member.pk, self.admin.pk}
        for form, field in [(TaskForm(instance=self.task, user=self.owner, workplace=self.team), 'assignee'),
                            (TaskModalForm(user=self.owner, workplace=self.team), 'assignee'),
                            (TaskProjectForm(user=self.owner, workplace=self.team), 'responsible_user'),
                            (TaskSectionForm(user=self.owner, project=self.project), 'owner')]:
            self.assertSetEqual(set(form.fields[field].queryset.values_list('pk', flat=True)), expected)
        response = self.client.post(self.url(), {'action': 'create_task_modal', 'section': self.section.pk,
            'title': 'Niedozwolone przypisanie', 'priority': 'medium', 'status': 'new', 'assignee': self.outsider.pk})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.filter(title='Niedozwolone przypisanie').exists())

    def test_member_calendar_and_kanban_writes(self):
        response = self.post_json(self.url('kanban', f'update/{self.card.task_id}/'), {'task_pk': self.card.pk, 'status': 'closed'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.card.activities.filter(action='status_changed').latest('pk').actor_id, self.member.pk)
        response = self.client.post(self.url('calendar', f'events/{self.event.pk}/update/'), {'title': 'Zmienione spotkanie',
            'start': '2026-09-24T10:00', 'end': '2026-09-24T11:00', 'color': 'blue'})
        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.user_id, self.owner.pk)

    def test_member_can_download_both_catalogs_and_attachments_then_loses_access(self):
        with tempfile.TemporaryDirectory() as directory:
            objects = [self.document, self.office, TaskAttachment(task=self.task), KanbanAttachment(task=self.card)]
            urls = [self.url('documents', f'{self.document.pk}/download/'), self.url('office', f'{self.office.pk}/download/')]
            for item in objects:
                field = item._meta.get_field('file')
                old = field.storage
                self.addCleanup(setattr, field, 'storage', old)
                field.storage = FileSystemStorage(directory)
                item.file.storage = field.storage
                item.file.save('team.txt', ContentFile(b'Team access'), save=True)
            urls += [self.url('tasks', f'attachments/{objects[2].pk}/download/'), self.url('kanban', f'attachments/{objects[3].pk}/download/')]
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
        self.assertEqual(self.client.get(self.url(suffix=f'view-task/{self.task.task_id}/')).status_code, 302)
        self.assertNotIn(self.task.title, json.dumps(self.client.get(reverse('global_search'), {'q': 'Zespołow'}).json(), ensure_ascii=False))
        self.assertEqual(self.post_json(self.url(suffix=f'update/{self.task.task_id}/'), {'task_pk': self.task.pk, 'status': 'closed'}).status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'new')

    def test_invitation_acceptance_requires_recipient_and_is_single_use(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('workplaces:team', args=[self.team.pk]), {'email': self.outsider.email.upper(), 'role': 'member'})
        self.assertEqual(response.status_code, 302)
        invitation = WorkplaceInvitation.objects.get(recipient=self.outsider)
        response_url = reverse('workplaces:invitation-response', args=[invitation.pk])
        self.assertEqual(self.client.post(response_url, {'action': 'accept'}).status_code, 404)
        self.client.force_login(self.outsider)
        self.assertContains(self.client.get(reverse('workplaces:workplaces')), self.team.name)
        self.assertEqual(self.client.post(response_url, {'action': 'accept'}).status_code, 302)
        self.assertTrue(self.team.memberships.filter(user=self.outsider, role='member').exists())
        self.assertEqual(self.client.post(response_url, {'action': 'accept'}).status_code, 404)
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_expired_cancelled_and_declined_invitations_do_not_grant_access(self):
        invitation = WorkplaceInvitation.objects.create(workplace=self.team, recipient=self.outsider, invited_by=self.owner, expires_at=timezone.now()-timedelta(seconds=1))
        self.client.force_login(self.outsider)
        url = reverse('workplaces:invitation-response', args=[invitation.pk])
        self.assertEqual(self.client.post(url, {'action': 'accept'}).status_code, 404)
        invitation.expires_at = timezone.now()+timedelta(days=1)
        invitation.save()
        self.assertEqual(self.client.post(url, {'action': 'decline'}).status_code, 302)
        self.assertEqual(self.client.post(url, {'action': 'accept'}).status_code, 404)
        self.assertFalse(self.team.memberships.filter(user=self.outsider).exists())

    def test_role_escalation_and_workspace_management_are_blocked(self):
        team_url = reverse('workplaces:team', args=[self.team.pk])
        self.assertEqual(self.client.post(team_url, {'email': self.outsider.email, 'role': 'admin'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('workplaces:update', args=[self.team.pk]), {'name': 'Zmiana'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('workplaces:delete', args=[self.team.pk])).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(team_url, {'email': self.outsider.email, 'role': 'admin'}).status_code, 200)
        self.assertFalse(WorkplaceInvitation.objects.filter(recipient=self.outsider).exists())
        self.assertEqual(self.client.post(reverse('workplaces:member-update', args=[self.team.pk, self.admin_membership.pk]), {'action': 'role', 'role': 'owner'}).status_code, 403)
        self.assertEqual(self.client.post(team_url, {'email': self.outsider.email, 'role': 'member'}).status_code, 302)
        invitation = WorkplaceInvitation.objects.get(recipient=self.outsider)
        self.assertEqual(self.client.post(reverse('workplaces:invitation-cancel', args=[self.team.pk, invitation.pk])).status_code, 302)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'revoked')

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
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_joining_never_backfills_personal_legacy_data_into_team(self):
        legacy = Task.objects.create(user=self.member, title='Moje stare dane')
        self.client.get(self.url())
        legacy.refresh_from_db()
        self.assertIsNone(legacy.workplace_id)

    def test_workspace_slugs_are_unique_across_owners(self):
        other = create_workplace_for_user(self.member, self.team.name)
        self.assertNotEqual(other.slug, self.team.slug)
        self.assertEqual(self.client.get(scoped_workplace_app_path(other, 'tasks')).status_code, 200)
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_bulk_status_records_each_actor_and_keeps_foreign_tasks_unchanged(self):
        response = self.post_json(self.url(suffix='bulk-update-status/'), {'task_pks': [self.task.pk, self.other_task.pk], 'status': 'closed'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['updated_count'], 1)
        self.task.refresh_from_db()
        self.other_task.refresh_from_db()
        self.assertTrue(self.task.is_completed)
        self.assertIsNotNone(self.task.completion_date)
        self.assertEqual(self.other_task.status, 'new')
        self.assertEqual(self.task.activities.filter(action='status_changed').latest('pk').actor_id, self.member.pk)
        response = self.post_json(self.url('kanban', 'bulk-update-status/'), {'task_pks': [self.card.pk], 'status': 'closed'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.card.activities.filter(action='status_changed').latest('pk').actor_id, self.member.pk)

    def test_removal_invalidates_all_existing_office_sessions(self):
        token = office_service.capability(self.office, 'callback', self.owner)
        self.assertTrue(office_service.check_capability(self.office, token, 'callback'))
        self.client.force_login(self.owner)
        response = self.client.post(reverse('workplaces:member-update', args=[self.team.pk, self.membership.pk]), {'action': 'remove'})
        self.assertEqual(response.status_code, 302)
        self.office.refresh_from_db()
        self.assertFalse(office_service.check_capability(self.office, token, 'callback'))
        self.assertTrue(office_service.check_capability(self.office, office_service.capability(self.office, 'callback', self.owner), 'callback'))

    def test_inactive_historical_membership_requires_an_invitation(self):
        self.membership.is_active = False
        self.membership.save(update_fields=['is_active'])
        self.assertNotIn(self.team, workplaces_for_user(self.member))
        self.assertEqual(self.client.get(self.url()).status_code, 302)
        invitation = WorkplaceInvitation.objects.create(workplace=self.team, recipient=self.member, invited_by=self.owner)
        self.assertEqual(self.client.post(reverse('workplaces:invitation-response', args=[invitation.pk]), {'action': 'accept'}).status_code, 302)
        self.membership.refresh_from_db()
        self.assertTrue(self.membership.is_active)
        self.assertEqual(self.client.get(self.url()).status_code, 200)


class TeamSlugMigrationTests(TransactionTestCase):
    def test_duplicate_slugs_are_resolved_without_changing_team_data(self):
        from django.conf import settings
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        # Inbox state and project templates depend on Workspace 0008. Roll
        # both back so the historical app state agrees with the database.
        previous = [node for node in latest if node[0] not in {'workplaces', 'dashboard', 'tasks'}] + [
            ('workplaces', '0007_sidebarfavorite_position'), ('dashboard', None),
            ('tasks', '0047_task_unique_tasks_number_per_workspace'),
        ]
        executor.migrate(previous)
        try:
            state = executor.loader.project_state([node for node in previous if node[1] is not None]).apps
            users = state.get_model(settings.AUTH_USER_MODEL)
            owner = users.objects.create(username='slug-owner', email='slug-owner@example.test')
            other = users.objects.create(username='slug-other', email='slug-other@example.test')
            spaces = state.get_model('workplaces', 'Workplace')
            first = spaces.objects.create(owner=owner, name='Studio', slug='studio')
            second = spaces.objects.create(owner=other, name='Studio', slug='studio')
            membership = state.get_model('workplaces', 'WorkplaceMembership').objects.create(workplace=second, user=owner, role='member')
            task = state.get_model('tasks', 'Task').objects.create(user=other, workplace=second, title='Zachowane zadanie', task_id=1)
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            state = executor.loader.project_state(latest).apps
            spaces = state.get_model('workplaces', 'Workplace')
            self.assertEqual(spaces.objects.get(pk=first.pk).slug, 'studio')
            self.assertNotEqual(spaces.objects.get(pk=second.pk).slug, 'studio')
            self.assertEqual(state.get_model('tasks', 'Task').objects.get(pk=task.pk).workplace_id, second.pk)
            self.assertTrue(state.get_model('workplaces', 'WorkplaceMembership').objects.filter(pk=membership.pk, workplace_id=second.pk, user_id=owner.pk, is_active=False).exists())
        finally:
            MigrationExecutor(connection).migrate(latest)
