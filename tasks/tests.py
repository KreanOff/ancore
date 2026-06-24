import json
import re
from datetime import date, datetime, timedelta, timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from contacts.models import Company, Contact, SharedItem, SharedItemLink, UserContact
from .models import Task, TaskActivity, TaskAttachment, TaskProject, TaskSection, TaskTag


class TaskProjectCreationTests(TestCase):
    PROJECT_CODE_PATTERN = r'^[A-Z]{3}-\d{4}-\d{3}$'

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='task-user',
            email='task-user@example.com',
            first_name='Task',
            last_name='User',
            password='test-pass-123',
        )
        self.client.force_login(self.user)

    def _share_task_object(self, obj, shared_with, permission='view'):
        return SharedItem.objects.create(
            content_type=ContentType.objects.get_for_model(obj.__class__),
            object_id=obj.pk,
            shared_by=self.user,
            shared_with=shared_with,
            permission=permission,
        )

    def _shared_task_object_exists(self, obj, shared_with):
        return SharedItem.objects.filter(
            content_type=ContentType.objects.get_for_model(obj.__class__),
            object_id=obj.pk,
            shared_with=shared_with,
        ).exists()

    def _assert_share_badge_uses_shared_access_cell(self, response, row_marker, badge_class):
        html = response.content.decode()
        row_start = html.index(row_marker)
        shared_access_cell = html.index('data-column="shared_access"', row_start)
        badge = html.index(badge_class, shared_access_cell)
        members_cell = html.index('data-directory-members-menu', badge)

        self.assertLess(shared_access_cell, badge)
        self.assertLess(badge, members_cell)

    def _assert_input_with_marker_is_enabled(self, html, marker):
        marker_position = html.index(marker)
        input_start = html.rfind('<input', 0, marker_position)
        input_end = html.index('>', marker_position)
        self.assertNotIn('disabled', html[input_start:input_end])

    def test_create_project_adds_default_group(self):
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt testowy',
            'section_title': 'Plan wdrożenia',
            'description': 'Opis projektu',
            'code': 'PT',
            'icon': 'star',
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt testowy')
        section = TaskSection.objects.get(project=project)

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.description, 'Opis projektu')
        self.assertEqual(project.icon, '')
        self.assertNotEqual(project.code, 'PT')
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertEqual(section.title, 'Plan wdrożenia')
        self.assertEqual(section.kind, 'custom')
        self.assertEqual(section.icon, '')
        self.assertEqual(section.order, 0)

    def test_create_project_saves_directory_metadata(self):
        company = Company.objects.create(owner=self.user, name='Ancore Labs')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt z metadanymi',
            'section_title': 'Plan',
            'description': '',
            'priority': 'high',
            'due_at': '2026-07-15',
            'company': company.id,
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt z metadanymi')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.priority, 'high')
        self.assertEqual(project.due_at, date(2026, 7, 15))
        self.assertEqual(project.company, company)

    def test_create_project_uses_default_group_name_when_group_name_is_empty(self):
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt z domyślną grupą',
            'section_title': '   ',
            'description': '',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt z domyślną grupą')
        section = TaskSection.objects.get(project=project)

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(section.title, 'Nowa Grupa')

    def test_create_project_generates_code_when_form_omits_it(self):
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt bez kodu',
            'description': '',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt bez kodu')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertEqual(project.icon, '')

    def test_create_project_generates_unique_random_code(self):
        first = TaskProject.objects.create(user=self.user, name='Projekt pierwszy')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt drugi',
            'description': '',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt drugi')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertNotEqual(project.code, first.code)

    def test_project_codes_are_unique_across_users(self):
        other_user = get_user_model().objects.create_user(username='other-user', password='test-pass-123')
        other_project = TaskProject.objects.create(user=other_user, name='Projekt innej osoby')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Mój projekt',
            'description': '',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Mój projekt')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertNotEqual(project.code, other_project.code)

    def test_project_codes_avoid_workspace_codes(self):
        from kanban.models import KanbanProject

        workspace = KanbanProject.objects.create(user=self.user, name='Przestrzeń robocza')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Mój projekt',
            'description': '',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Mój projekt')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertRegex(project.code, self.PROJECT_CODE_PATTERN)
        self.assertNotEqual(project.code, workspace.code)

    def test_project_icons_get_different_badge_colors(self):
        first = TaskProject.objects.create(user=self.user, name='Pierwszy')
        second = TaskProject.objects.create(user=self.user, name='Drugi')

        self.assertEqual(first.icon, '')
        self.assertEqual(second.icon, '')
        self.assertNotEqual(first.icon_color, second.icon_color)

    def test_projects_list_does_not_render_icons_next_to_names(self):
        company = Company.objects.create(owner=self.user, name='Acme CRM')
        project = TaskProject.objects.create(
            user=self.user,
            name='Projekt z ikoną',
            description='Opis projektu',
            code='PZI',
            icon='star',
            priority='high',
            due_at=date(2026, 7, 15),
            company=company,
        )
        TaskProject.objects.create(user=self.user, name='Projekt bez ikony', code='PBI', icon='')
        section = TaskSection.objects.create(project=project, title='Plan')
        Task.objects.create(user=self.user, section=section, title='Gotowe zadanie', status='closed')
        Task.objects.create(user=self.user, section=section, title='Otwarte zadanie', status='new')
        TaskProject.objects.filter(pk=project.pk).update(
            created_at=datetime(2026, 6, 7, 12, 0, tzinfo=datetime_timezone.utc)
        )

        response = self.client.get(reverse('tasks:tasks'))

        self.assertNotContains(response, 'tasks-project-row-icon')
        self.assertNotContains(response, 'tasks-project-row-icon--fallback')
        self.assertContains(response, '<span>Projekt z ikoną</span>', html=True)
        self.assertContains(response, '<span>Projekt bez ikony</span>', html=True)
        self.assertContains(response, 'KOD PROJEKTU')
        self.assertContains(response, 'OPIS')
        self.assertContains(response, 'POSTĘP')
        self.assertContains(response, 'TERMIN')
        self.assertContains(response, 'ZADANIA')
        self.assertContains(response, 'PRIORYTET')
        self.assertContains(response, 'OSTATNIA AKTYWNOŚĆ')
        self.assertContains(response, 'KLIENT / FIRMA')
        self.assertContains(response, project.code)
        self.assertContains(response, 'Opis projektu')
        self.assertContains(response, 'Brak opisu')
        self.assertContains(response, '50%')
        self.assertContains(response, '1/2')
        self.assertContains(response, 'Wysoki')
        self.assertContains(response, '15.07.2026')
        self.assertContains(response, 'Acme CRM')
        self.assertContains(response, 'tasks-project-progress-fill')
        self.assertContains(response, 'data-project-priority="high"')
        self.assertContains(response, 'data-project-due-at="2026-07-15"')
        self.assertContains(response, f'data-project-company-id="{company.id}"')
        self.assertContains(response, 'DATA')
        self.assertContains(response, '07.06.2026')
        self.assertNotContains(response, '7 cze')
        self.assertContains(
            response,
            '<span class="tasks-directory-member-label">Task User</span>',
            html=True,
            count=2,
        )

    def test_project_create_modal_uses_large_task_style_layout(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'tasks-project-create-modal')
        self.assertContains(response, 'tasks-project-create-modal__body')
        self.assertContains(response, 'tasks-project-create-fields')
        self.assertContains(response, 'Utwórz projekt')

    def test_project_members_include_owner_and_shared_users(self):
        shared_user = get_user_model().objects.create_user(
            username='shared-user',
            email='shared@example.com',
            first_name='Shared',
            last_name='Person',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt udostępniony', code='SHR')
        self._share_task_object(project, shared_user)

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(
            response,
            '<span class="tasks-directory-member-label">Udostępnione 1</span>',
            html=True,
        )
        self.assertContains(response, 'title="Task User, Shared Person"')
        self.assertContains(response, 'tasks-directory-members-toolbar')
        self.assertContains(response, 'data-directory-members-search')
        self.assertContains(response, 'data-directory-member-row', count=2)
        self.assertContains(response, 'id="directory-share-modal"')
        self.assertContains(response, 'data-directory-share-open')
        self.assertContains(response, 'data-directory-share-fields')
        self.assertContains(response, 'name="member_query"')
        self.assertContains(response, 'name="permission"')
        self.assertContains(response, 'data-directory-share-permission-picker')
        self.assertContains(response, 'data-directory-share-permission-option')
        self.assertNotContains(response, '<select id="directory-share-permission"')
        self.assertContains(response, 'Wpisz ID Ancore')
        self.assertContains(response, 'placeholder="@jan.kowalski"')
        self.assertContains(response, 'data-share-link-create-url')
        self.assertContains(response, 'data-directory-share-link-input')
        self.assertContains(response, 'data-directory-share-link-create')
        self.assertContains(response, 'data-directory-share-link-copy')
        self.assertContains(response, 'data-directory-share-link-revoke')
        self.assertNotContains(response, 'data-directory-share-contacts-toggle')
        self.assertContains(response, 'data-directory-share-results')
        self.assertContains(response, 'data-directory-share-results-empty')
        self.assertContains(response, 'data-directory-share-contacts')
        self.assertContains(response, 'data-directory-share-contacts-empty')
        self.assertContains(response, 'data-directory-share-selected-input')
        self.assertContains(response, 'data-directory-share-shared-list')
        self.assertContains(response, 'data-directory-share-shared-empty')
        self.assertContains(response, 'data-directory-share-shared-count')
        self.assertContains(response, f'data-share-project-id="{project.id}"')
        self.assertContains(response, f'data-share-members-template="tasks-directory-share-members-project-{project.id}"')
        self.assertContains(response, f'id="tasks-directory-share-members-project-{project.id}"')
        self.assertContains(response, 'data-directory-share-remove')
        self.assertContains(response, f'data-share-member-id="{shared_user.id}"')
        self.assertContains(response, 'shared-user')
        self.assertContains(response, 'tasks-directory-share-check')
        self.assertContains(response, 'tasks-directory-share-shared-details')
        self.assertContains(response, '<span class="tasks-directory-share-email"><i data-lucide="mail" aria-hidden="true"></i><span>shared@example.com</span></span>', html=True)
        self.assertContains(response, 'data-directory-share-permission-submit')
        self.assertContains(response, 'data-share-action="update_project_share_permission"')
        self.assertContains(response, 'tasks-directory-share-permission-badge')
        self.assertNotContains(response, 'name="member_first_name"')
        self.assertNotContains(response, 'name="member_last_name"')
        self.assertNotContains(response, '<datalist id="tasks-share-contact-options">')
        self.assertNotContains(response, 'data-directory-share-picker')
        self.assertNotContains(response, 'tasks-directory-member-input')
        self.assertContains(response, 'Właściciel')
        self.assertContains(response, 'Udostępniono')
        self.assertContains(response, 'data-directory-member-actions', count=1)
        self.assertContains(response, 'name="action" value="unshare_project"')
        self.assertContains(response, f'name="member_id" value="{shared_user.id}"')
        self.assertContains(response, 'Przestań udostępniać')

    def test_share_project_adds_user_from_contacts(self):
        shared_user = get_user_model().objects.create_user(
            username='shared-contact',
            email='shared-contact@example.com',
            first_name='Shared',
            last_name='Contact',
            password='test-pass-123',
        )
        UserContact.objects.create(owner=self.user, target_user=shared_user)
        project = TaskProject.objects.create(user=self.user, name='Projekt udostępniany', code='SHC')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'share_project',
            'project_id': project.id,
            'member_query': 'shared-contact',
            'next': reverse('tasks:tasks'),
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertTrue(self._shared_task_object_exists(project, shared_user))

    def test_unshare_project_removes_shared_user(self):
        shared_user = get_user_model().objects.create_user(
            username='shared-remove',
            email='shared-remove@example.com',
            first_name='Shared',
            last_name='Remove',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt udostępniony', code='UNP')
        self._share_task_object(project, shared_user)

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'unshare_project',
            'project_id': project.id,
            'member_id': shared_user.id,
            'next': reverse('tasks:tasks'),
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(self._shared_task_object_exists(project, shared_user))

    def test_view_only_shared_project_exposes_self_unshare_menu_action(self):
        shared_user = get_user_model().objects.create_user(
            username='shared-view-self-remove',
            email='shared-view-self-remove@example.com',
            first_name='Shared',
            last_name='Viewer',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt tylko do podglądu', code='VSP')
        self._share_task_object(project, shared_user, permission='view')

        self.client.force_login(shared_user)
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'id="unshare-selected-project-menu-btn"')
        self.assertContains(response, 'Przestań udostępniać to dla mnie')
        self.assertContains(response, f'data-project-id="{project.id}"')
        self.assertContains(response, 'data-can-manage="false"')
        self.assertContains(response, 'data-can-self-unshare="true"')
        self.assertContains(response, 'data-shared-access-permission="view"')

    def test_shared_project_user_can_unshare_project_for_self(self):
        shared_user = get_user_model().objects.create_user(
            username='shared-self-remove',
            email='shared-self-remove@example.com',
            first_name='Shared',
            last_name='Self Remove',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt do odpięcia', code='SDO')
        self._share_task_object(project, shared_user, permission='view')

        self.client.force_login(shared_user)
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'unshare_project',
            'project_id': project.id,
            'next': reverse('tasks:tasks'),
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(self._shared_task_object_exists(project, shared_user))

    def test_update_project_share_permission_changes_existing_user_access(self):
        shared_user = get_user_model().objects.create_user(
            username='@permission.user',
            email='permission-user@example.com',
            first_name='Permission',
            last_name='User',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt z dostępem')
        share = self._share_task_object(project, shared_user, permission='view')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'update_project_share_permission',
            'project_id': project.id,
            'member_id': shared_user.id,
            'permission': 'edit',
            'next': reverse('tasks:tasks'),
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        share.refresh_from_db()
        self.assertEqual(share.permission, 'edit')

    def test_ajax_update_project_share_permission_returns_json_without_redirect(self):
        shared_user = get_user_model().objects.create_user(
            username='@ajax.permission',
            email='ajax-permission@example.com',
            first_name='Ajax',
            last_name='Permission',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt z AJAX')
        share = self._share_task_object(project, shared_user, permission='view')

        response = self.client.post(
            reverse('tasks:tasks'),
            {
                'action': 'update_project_share_permission',
                'project_id': project.id,
                'member_id': shared_user.id,
                'permission': 'edit',
                'next': reverse('tasks:tasks'),
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        payload = response.json()
        queued_messages = [message.message for message in get_messages(response.wsgi_request)]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['status'], 'success')
        self.assertEqual(payload['permission'], 'edit')
        self.assertEqual(payload['permission_label'], 'Może przeglądać i edytować')
        self.assertEqual(queued_messages, [])
        share.refresh_from_db()
        self.assertEqual(share.permission, 'edit')

    def test_share_modal_lists_contacts_for_selection(self):
        shared_user = get_user_model().objects.create_user(
            username='jan.kowalski',
            email='jan@example.com',
            first_name='Jan',
            last_name='Kowalski',
            password='test-pass-123',
        )
        UserContact.objects.create(owner=self.user, target_user=shared_user)

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'data-directory-share-result')
        self.assertContains(response, 'data-directory-share-contact')
        self.assertContains(response, 'data-directory-share-pick')
        self.assertContains(response, 'data-directory-share-check')
        self.assertContains(response, 'tasks-directory-share-person-cell')
        self.assertContains(response, 'tasks-directory-share-contacts-panel')
        self.assertContains(response, 'tasks-directory-share-contact-row')
        self.assertContains(response, 'tasks-directory-share-shared-details')
        self.assertNotContains(response, 'data-directory-share-contact-permission')
        self.assertContains(response, 'data-share-value="jan.kowalski"')
        self.assertNotContains(response, 'tasks-directory-share-table-header')
        self.assertContains(response, 'jan@example.com')
        self.assertContains(response, '<span class="tasks-directory-share-email"><i data-lucide="mail" aria-hidden="true"></i><span>jan@example.com</span></span>', html=True)
        self.assertNotContains(response, '<small class="tasks-directory-share-person-email">jan@example.com</small>', html=True)
        self.assertContains(response, 'id="directory-share-contacts-panel"')
        self.assertNotContains(response, 'data-directory-share-contacts-toggle')
        self.assertContains(response, '<span class="tasks-directory-share-first-name">Jan</span>', html=True)
        self.assertContains(response, '<span class="tasks-directory-share-last-name">Kowalski</span>', html=True)
        self.assertNotContains(response, '<span class="tasks-directory-share-middle-name">-</span>', html=True)
        self.assertContains(response, '<span class="tasks-directory-share-shared-username tasks-directory-share-username"><i data-lucide="at-sign" aria-hidden="true"></i><span>jan.kowalski</span></span>', html=True)
        self.assertNotContains(response, 'Użytkownik aplikacji')

    def test_share_modal_lists_active_users_outside_contacts_for_selection(self):
        get_user_model().objects.create_user(
            username='@outside.user',
            email='outside-user@example.com',
            first_name='Outside',
            last_name='User',
            password='test-pass-123',
        )
        inactive_user = get_user_model().objects.create_user(
            username='@inactive.user',
            email='inactive-user@example.com',
            first_name='Inactive',
            last_name='User',
            password='test-pass-123',
            is_active=False,
        )

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'data-directory-share-result')
        self.assertContains(response, 'data-share-value="@outside.user"')
        self.assertContains(response, '<span class="tasks-directory-share-first-name">Outside</span>', html=True)
        self.assertContains(response, '<span class="tasks-directory-share-last-name">User</span>', html=True)
        self.assertContains(response, '<small>Użytkownik aplikacji</small>', html=True)
        self.assertContains(response, '<span class="tasks-directory-share-email"><i data-lucide="mail" aria-hidden="true"></i><span>outside-user@example.com</span></span>', html=True)
        self.assertNotContains(response, f'data-share-value="{inactive_user.username}"')

    def test_share_modal_groups_contact_identity(self):
        linked_user = get_user_model().objects.create_user(
            username='@jan.kowalski',
            email='jan@example.com',
            middle_name='Piotr',
            password='test-pass-123',
        )
        contact = Contact.objects.create(
            user=self.user,
            first_name='Jan',
            middle_name='Adam',
            last_name='Kowalski',
            company='Netology',
            email='jan.contact@example.com',
        )
        UserContact.objects.create(owner=self.user, target_user=linked_user, linked_contact=contact)

        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()

        self.assertContains(response, '<span class="tasks-directory-share-first-name">Jan</span>', html=True)
        self.assertContains(response, '<span class="tasks-directory-share-last-name">Kowalski</span>', html=True)
        self.assertContains(response, '<span class="tasks-directory-share-middle-name">Adam</span>', html=True)
        self.assertContains(response, '<span class="tasks-directory-share-shared-username tasks-directory-share-username"><i data-lucide="at-sign" aria-hidden="true"></i><span>@jan.kowalski</span></span>', html=True)
        row_start = html.index('data-share-value="@jan.kowalski"')
        person_position = html.index('tasks-directory-share-person-cell', row_start)
        check_position = html.index('data-directory-share-check', row_start)
        avatar_position = html.index('tasks-directory-share-contact-avatar', row_start)
        first_name_position = html.index('<span class="tasks-directory-share-first-name">Jan</span>', row_start)
        last_name_position = html.index('<span class="tasks-directory-share-last-name">Kowalski</span>', row_start)
        middle_name_position = html.index('<span class="tasks-directory-share-middle-name">Adam</span>', row_start)
        ancore_position = html.index('tasks-directory-share-username', row_start)
        ancore_value_position = html.index('<span>@jan.kowalski</span>', row_start)
        email_position = html.index('<span class="tasks-directory-share-email">', row_start)
        self.assertLess(check_position, person_position)
        self.assertLess(person_position, avatar_position)
        self.assertLess(avatar_position, first_name_position)
        self.assertLess(first_name_position, last_name_position)
        self.assertLess(last_name_position, middle_name_position)
        self.assertLess(middle_name_position, ancore_position)
        self.assertLess(ancore_position, ancore_value_position)
        self.assertLess(ancore_value_position, email_position)

    def test_share_modal_uses_user_name_when_linked_contact_has_only_company(self):
        linked_user = get_user_model().objects.create_user(
            username='@jan.kowalski',
            email='jan@example.com',
            first_name='Jan',
            middle_name='Piotr',
            last_name='Kowalski',
            password='test-pass-123',
        )
        contact = Contact.objects.create(
            user=self.user,
            company='Netology',
            email='jan.contact@example.com',
        )
        UserContact.objects.create(owner=self.user, target_user=linked_user, linked_contact=contact)

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, '<span class="tasks-directory-share-first-name">Jan</span>', html=True)
        self.assertContains(response, '<span class="tasks-directory-share-last-name">Kowalski</span>', html=True)
        self.assertContains(response, '<span class="tasks-directory-share-middle-name">Piotr</span>', html=True)
        self.assertContains(response, '<span class="tasks-directory-share-shared-username tasks-directory-share-username"><i data-lucide="at-sign" aria-hidden="true"></i><span>@jan.kowalski</span></span>', html=True)
        self.assertNotContains(response, '<span class="tasks-directory-share-first-name">Netology</span>', html=True)

    def test_share_project_adds_user_by_ancore_id(self):
        shared_user = get_user_model().objects.create_user(
            username='@outside.user',
            email='outside@example.com',
            first_name='Outside',
            last_name='User',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt po ID', code='PID')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'share_project',
            'project_id': project.id,
            'member_query': '@outside.user',
            'next': reverse('tasks:tasks'),
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertTrue(self._shared_task_object_exists(project, shared_user))

    def test_share_project_adds_multiple_users_by_selected_ancore_ids(self):
        first_user = get_user_model().objects.create_user(
            username='@multi.first',
            email='multi-first@example.com',
            first_name='Multi',
            last_name='First',
            password='test-pass-123',
        )
        second_user = get_user_model().objects.create_user(
            username='@multi.second',
            email='multi-second@example.com',
            first_name='Multi',
            last_name='Second',
            password='test-pass-123',
        )
        third_user = get_user_model().objects.create_user(
            username='@multi.third',
            email='multi-third@example.com',
            first_name='Multi',
            last_name='Third',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt multi', code='MUL')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'share_project',
            'project_id': project.id,
            'member_query': '@multi.first: @multi.second: @multi.third',
            'member_queries': '@multi.first\n@multi.second',
            'next': reverse('tasks:tasks'),
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertTrue(self._shared_task_object_exists(project, first_user))
        self.assertTrue(self._shared_task_object_exists(project, second_user))
        self.assertTrue(self._shared_task_object_exists(project, third_user))

    def test_share_project_does_not_add_user_by_email(self):
        shared_user = get_user_model().objects.create_user(
            username='@email.user',
            email='email-user@example.com',
            first_name='Email',
            last_name='User',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt po emailu', code='PEM')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'share_project',
            'project_id': project.id,
            'member_query': 'email-user@example.com',
            'next': reverse('tasks:tasks'),
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(self._shared_task_object_exists(project, shared_user))

    def test_share_project_does_not_add_user_by_full_name(self):
        shared_user = get_user_model().objects.create_user(
            username='@name.user',
            email='name-user@example.com',
            first_name='Natalia',
            last_name='Zielinska',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt po nazwisku', code='PNZ')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'share_project',
            'project_id': project.id,
            'member_query': 'Natalia Zielinska',
            'next': reverse('tasks:tasks'),
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(self._shared_task_object_exists(project, shared_user))

    def test_share_project_does_not_add_user_by_linked_contact_identity(self):
        shared_user = get_user_model().objects.create_user(
            username='@linked.user',
            email='linked-user@example.com',
            first_name='Account',
            last_name='Name',
            password='test-pass-123',
        )
        contact = Contact.objects.create(
            user=self.user,
            first_name='Alicja',
            last_name='Nowak',
            email='alicja.nowak@example.com',
        )
        UserContact.objects.create(owner=self.user, target_user=shared_user, linked_contact=contact)
        project = TaskProject.objects.create(user=self.user, name='Projekt po kontakcie', code='PCK')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'share_project',
            'project_id': project.id,
            'member_query': 'Alicja Nowak',
            'next': reverse('tasks:tasks'),
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(self._shared_task_object_exists(project, shared_user))

    def test_share_section_adds_user_from_contacts(self):
        shared_user = get_user_model().objects.create_user(
            username='shared-section-contact',
            email='shared-section@example.com',
            first_name='Shared',
            last_name='Section',
            password='test-pass-123',
        )
        UserContact.objects.create(owner=self.user, target_user=shared_user)
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PSC')
        section = TaskSection.objects.create(project=project, title='Grupa')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'share_section',
            'section_id': section.id,
            'member_query': 'shared-section-contact',
            'next': reverse('tasks:tasks'),
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertTrue(self._shared_task_object_exists(section, shared_user))

    def test_unshare_section_removes_shared_user(self):
        shared_user = get_user_model().objects.create_user(
            username='shared-section-remove',
            email='shared-section-remove@example.com',
            first_name='Shared',
            last_name='Section Remove',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='USR')
        section = TaskSection.objects.create(project=project, title='Grupa')
        self._share_task_object(section, shared_user)

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'unshare_section',
            'section_id': section.id,
            'member_id': shared_user.id,
            'next': reverse('tasks:tasks'),
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(self._shared_task_object_exists(section, shared_user))

    def test_share_task_adds_user_by_ancore_id(self):
        shared_user = get_user_model().objects.create_user(
            username='@task.user',
            email='task-user-shared@example.com',
            first_name='Task',
            last_name='Shared',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='TSK')
        section = TaskSection.objects.create(project=project, title='Grupa')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie udostępniane')

        response = self.client.post(reverse('tasks:view-task', args=[task.task_id]), {
            'action': 'share_task',
            'task_id': task.id,
            'member_query': '@task.user',
            'next': reverse('tasks:view-task', args=[task.task_id]),
        })

        self.assertRedirects(response, reverse('tasks:view-task', args=[task.task_id]))
        self.assertTrue(self._shared_task_object_exists(task, shared_user))

    def test_task_detail_renders_share_controls_for_owner(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='TDT')
        section = TaskSection.objects.create(project=project, title='Grupa')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie z udostępnianiem')

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))

        self.assertContains(response, 'Udostępnione')
        self.assertContains(response, 'data-share-action="share_task"')
        self.assertContains(response, f'data-share-task-id="{task.id}"')
        self.assertContains(response, 'data-share-object-kind="task"')
        self.assertContains(response, 'data-directory-share-link-input')

    def test_create_share_link_returns_project_link(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt linkowany', code='LNK')

        response = self.client.post(reverse('tasks:create-share-link'), {
            'object_type': 'project',
            'object_id': project.id,
        })

        payload = response.json()
        link = SharedItemLink.objects.get(
            content_type=ContentType.objects.get_for_model(TaskProject),
            object_id=project.id,
            created_by=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['status'], 'success')
        self.assertIn(reverse('tasks:accept-share-link', args=[link.token]), payload['url'])
        self.assertRegex(link.token, r'^[0-9a-f]{32}$')
        self.assertTrue(link.is_active)

    def test_revoke_share_link_allows_creating_new_project_link(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt z nowym linkiem', code='RNL')

        first_response = self.client.post(reverse('tasks:create-share-link'), {
            'object_type': 'project',
            'object_id': project.id,
        })
        first_link = SharedItemLink.objects.get(
            content_type=ContentType.objects.get_for_model(TaskProject),
            object_id=project.id,
            created_by=self.user,
            is_active=True,
        )

        revoke_response = self.client.post(reverse('tasks:revoke-share-link'), {
            'object_type': 'project',
            'object_id': project.id,
        })
        second_response = self.client.post(reverse('tasks:create-share-link'), {
            'object_type': 'project',
            'object_id': project.id,
        })
        second_link = SharedItemLink.objects.get(
            content_type=ContentType.objects.get_for_model(TaskProject),
            object_id=project.id,
            created_by=self.user,
            is_active=True,
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(revoke_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertNotEqual(second_link.token, first_link.token)
        self.assertFalse(SharedItemLink.objects.get(pk=first_link.pk).is_active)
        self.assertIn(
            reverse('tasks:accept-share-link', args=[second_link.token]),
            second_response.json()['url'],
        )

    def test_missing_share_link_redirects_without_debug_404(self):
        response = self.client.get(reverse('tasks:accept-share-link', args=['nieistniejacy-token']))
        messages = [message.message for message in get_messages(response.wsgi_request)]

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(messages, ['Ten link udostępniania nie istnieje albo został przepisany niepoprawnie.'])

    def test_revoked_share_link_redirects_without_granting_access(self):
        shared_user = get_user_model().objects.create_user(
            username='@revoked.link',
            email='revoked-link@example.com',
            first_name='Revoked',
            last_name='Link',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt z wyłączonym linkiem', code='RLK')
        link = SharedItemLink.objects.create(
            content_type=ContentType.objects.get_for_model(TaskProject),
            object_id=project.id,
            created_by=self.user,
            is_active=False,
        )

        self.client.force_login(shared_user)
        response = self.client.get(reverse('tasks:accept-share-link', args=[link.token]))
        messages = [message.message for message in get_messages(response.wsgi_request)]

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(messages, ['Ten link udostępniania został wyłączony.'])
        self.assertFalse(self._shared_task_object_exists(project, shared_user))

    def test_accept_project_share_link_grants_access(self):
        shared_user = get_user_model().objects.create_user(
            username='@link.user',
            email='link-user@example.com',
            first_name='Link',
            last_name='User',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt z linku', code='LKP')
        link = SharedItemLink.objects.create(
            content_type=ContentType.objects.get_for_model(TaskProject),
            object_id=project.id,
            created_by=self.user,
        )

        self.client.force_login(shared_user)
        response = self.client.get(reverse('tasks:accept-share-link', args=[link.token]))

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=shared-projects")
        self.assertTrue(self._shared_task_object_exists(project, shared_user))

    def test_shared_project_appears_in_default_projects_for_recipient(self):
        shared_user = get_user_model().objects.create_user(
            username='@default.shared',
            email='default-shared@example.com',
            first_name='Default',
            last_name='Shared',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt widoczny normalnie', code='PVN')
        section = TaskSection.objects.create(project=project, title='Grupa widoczna normalnie')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie widoczne normalnie')
        self._share_task_object(project, shared_user)

        self.client.force_login(shared_user)
        response = self.client.get(reverse('tasks:tasks'))
        project_response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")
        section_response = self.client.get(reverse('tasks:task_group', args=[section.id]))

        self.assertContains(response, 'Projekt widoczny normalnie')
        self.assertContains(response, 'Grupa widoczna normalnie')
        self.assertContains(response, f'?project={project.id}')
        self.assertNotContains(response, f'data-share-project-id="{project.id}"')
        self.assertContains(response, 'tasks-shared-access-badge--incoming')
        self.assertContains(response, 'tasks-shared-access-badge--view')
        self.assertContains(response, 'data-lucide="share-2"')
        self.assertContains(response, 'Udostępnione dla Ciebie: Może przeglądać')
        self._assert_share_badge_uses_shared_access_cell(
            response,
            f'data-project-id="{project.id}"',
            'tasks-shared-access-badge--incoming',
        )
        self.assertContains(project_response, 'Grupa widoczna normalnie')
        self.assertContains(project_response, 'tasks-shared-access-badge--incoming')
        self.assertContains(project_response, 'tasks-shared-access-badge--view')
        self._assert_share_badge_uses_shared_access_cell(
            project_response,
            f'data-section-id="{section.id}"',
            'tasks-shared-access-badge--incoming',
        )
        self.assertContains(section_response, 'Zadanie widoczne normalnie')
        self.assertContains(section_response, reverse('tasks:view-shared-task', args=[task.id]))
        self.assertContains(section_response, 'tasks-shared-access-badge--incoming')
        self.assertContains(section_response, 'tasks-shared-access-badge--view')

    def test_shared_project_marks_owner_rows_as_shared_outgoing(self):
        shared_user = get_user_model().objects.create_user(
            username='@owner.shared',
            email='owner-shared@example.com',
            first_name='Owner',
            last_name='Shared',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt wysłany', code='PWS')
        section = TaskSection.objects.create(project=project, title='Grupa wysłana')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie wysłane')
        self._share_task_object(project, shared_user)

        response = self.client.get(reverse('tasks:tasks'))
        project_response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")
        section_response = self.client.get(reverse('tasks:task_group', args=[section.id]))

        self.assertContains(response, 'Projekt wysłany')
        self.assertContains(response, 'tasks-shared-access-badge--outgoing')
        self.assertContains(response, 'data-lucide="send"')
        self.assertContains(response, 'Udostępnione przez Ciebie')
        self._assert_share_badge_uses_shared_access_cell(
            response,
            f'data-project-id="{project.id}"',
            'tasks-shared-access-badge--outgoing',
        )
        self.assertContains(project_response, 'Grupa wysłana')
        self.assertContains(project_response, 'tasks-shared-access-badge--outgoing')
        self._assert_share_badge_uses_shared_access_cell(
            project_response,
            f'data-section-id="{section.id}"',
            'tasks-shared-access-badge--outgoing',
        )
        self.assertContains(section_response, 'Zadanie wysłane')
        self.assertContains(section_response, 'tasks-shared-access-badge--outgoing')

    def test_accept_section_share_link_grants_group_access(self):
        shared_user = get_user_model().objects.create_user(
            username='@section.link',
            email='section-link@example.com',
            first_name='Section',
            last_name='Link',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='SLK')
        section = TaskSection.objects.create(project=project, title='Grupa z linku')
        Task.objects.create(user=self.user, section=section, title='Zadanie w grupie')
        link = SharedItemLink.objects.create(
            content_type=ContentType.objects.get_for_model(TaskSection),
            object_id=section.id,
            created_by=self.user,
        )

        self.client.force_login(shared_user)
        response = self.client.get(reverse('tasks:accept-share-link', args=[link.token]))
        group_response = self.client.get(reverse('tasks:task_group', args=[section.id]))

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertTrue(self._shared_task_object_exists(section, shared_user))
        self.assertContains(group_response, 'Zadanie w grupie')

    def test_accept_task_share_link_uses_stable_shared_task_route(self):
        shared_user = get_user_model().objects.create_user(
            username='@task.link',
            email='task-link@example.com',
            first_name='Task',
            last_name='Link',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='TLK')
        section = TaskSection.objects.create(project=project, title='Grupa')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie z linku')
        link = SharedItemLink.objects.create(
            content_type=ContentType.objects.get_for_model(Task),
            object_id=task.id,
            created_by=self.user,
        )

        self.client.force_login(shared_user)
        response = self.client.get(reverse('tasks:accept-share-link', args=[link.token]))
        detail_response = self.client.get(reverse('tasks:view-shared-task', args=[task.id]))

        self.assertRedirects(response, reverse('tasks:view-shared-task', args=[task.id]))
        self.assertTrue(self._shared_task_object_exists(task, shared_user))
        self.assertContains(detail_response, 'Zadanie z linku')
        self.assertNotContains(detail_response, 'data-share-action="share_task"')

    def test_shared_views_list_received_items(self):
        shared_user = get_user_model().objects.create_user(
            username='@shared.views',
            email='shared-views@example.com',
            first_name='Shared',
            last_name='Views',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt udostępniony w widoku', code='SVP')
        section = TaskSection.objects.create(project=project, title='Grupa udostępniona w widoku')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie udostępnione w widoku')
        self._share_task_object(project, shared_user)
        self._share_task_object(section, shared_user)
        self._share_task_object(task, shared_user)

        self.client.force_login(shared_user)
        projects_response = self.client.get(f"{reverse('tasks:tasks')}?view=shared-projects")
        groups_response = self.client.get(f"{reverse('tasks:tasks')}?view=shared-groups")
        tasks_response = self.client.get(f"{reverse('tasks:tasks')}?view=shared-tasks")

        self.assertContains(projects_response, 'Projekt udostępniony w widoku')
        self.assertContains(groups_response, 'Grupa udostępniona w widoku')
        self.assertContains(tasks_response, 'Zadanie udostępnione w widoku')
        self.assertContains(projects_response, 'tasks-shared-access-badge--incoming')
        self.assertContains(projects_response, 'tasks-shared-access-badge--view')
        self.assertContains(groups_response, 'tasks-shared-access-badge--incoming')
        self.assertContains(groups_response, 'tasks-shared-access-badge--view')
        self.assertContains(tasks_response, 'tasks-shared-access-badge--incoming')
        self.assertContains(tasks_response, 'tasks-shared-access-badge--view')
        self.assertContains(projects_response, f'data-view-url="{reverse("tasks:tasks")}?project={project.id}"')
        self.assertContains(tasks_response, reverse('tasks:view-shared-task', args=[task.id]))

    def test_view_only_shared_task_opens_detail_with_readonly_controls(self):
        shared_user = get_user_model().objects.create_user(
            username='@readonly.task',
            email='readonly-task@example.com',
            first_name='Read',
            last_name='Only',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt tylko do odczytu', code='RDO')
        section = TaskSection.objects.create(project=project, title='Grupa tylko do odczytu')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie tylko do odczytu')
        subtask = Task.objects.create(
            user=self.user,
            section=section,
            parent=task,
            title='Podzadanie tylko do odczytu',
        )
        self._share_task_object(project, shared_user, permission='view')

        self.client.force_login(shared_user)
        detail_response = self.client.get(reverse('tasks:view-shared-task', args=[task.id]))
        list_response = self.client.get(f"{reverse('tasks:tasks')}?view=shared-tasks")
        projects_response = self.client.get(reverse('tasks:tasks'))
        sections_response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")
        html = detail_response.content.decode()
        list_html = list_response.content.decode()
        projects_html = projects_response.content.decode()
        sections_html = sections_response.content.decode()

        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'tasks-issue-form--readonly')
        self.assertContains(detail_response, 'data-task-readonly="true"')
        self.assertRegex(html, r'<input[^>]*name="title"[^>]*disabled|<input[^>]*disabled[^>]*name="title"')
        self.assertRegex(html, r'<select[^>]*name="status"[^>]*disabled|<select[^>]*disabled[^>]*name="status"')
        self.assertContains(detail_response, 'data-task-detail-toggle disabled aria-disabled="true"')
        self.assertContains(detail_response, f'data-view-url="{reverse("tasks:view-shared-task", args=[subtask.id])}"')
        self.assertContains(detail_response, 'draggable="false"')
        self.assertContains(list_response, f'data-view-url="{reverse("tasks:view-shared-task", args=[task.id])}"')
        self.assertContains(list_response, 'draggable="false"')
        self._assert_input_with_marker_is_enabled(html, f'data-task-id="{subtask.task_id}" data-can-edit="false"')
        self._assert_input_with_marker_is_enabled(list_html, f'data-task-id="{task.task_id}" data-can-edit="false"')
        self._assert_input_with_marker_is_enabled(projects_html, f'data-project-id="{project.id}"')
        self._assert_input_with_marker_is_enabled(sections_html, f'data-section-id="{section.id}"')

    def test_view_only_shared_project_cannot_create_task(self):
        shared_user = get_user_model().objects.create_user(
            username='@readonly.create',
            email='readonly-create@example.com',
            first_name='Read',
            last_name='Create',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt bez edycji', code='PBE')
        section = TaskSection.objects.create(project=project, title='Grupa bez edycji')
        self._share_task_object(project, shared_user, permission='view')

        self.client.force_login(shared_user)
        group_response = self.client.get(reverse('tasks:task_group', args=[section.id]))
        post_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'section': section.id,
            'title': 'Nie powinno powstać',
            'description': '',
            'priority': 'medium',
            'status': 'new',
        })

        self.assertContains(group_response, 'data-open-issue disabled')
        self.assertEqual(post_response.status_code, 403)
        self.assertFalse(Task.objects.filter(section=section, title='Nie powinno powstać').exists())

    def test_edit_shared_project_can_create_task_for_project_owner(self):
        shared_user = get_user_model().objects.create_user(
            username='@edit.create',
            email='edit-create@example.com',
            first_name='Edit',
            last_name='Create',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt do edycji', code='PDE')
        section = TaskSection.objects.create(project=project, title='Grupa do edycji')
        self._share_task_object(project, shared_user, permission='edit')

        self.client.force_login(shared_user)
        group_response = self.client.get(reverse('tasks:task_group', args=[section.id]))
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'section': section.id,
            'title': 'Zadanie dodane przez edytora',
            'description': '',
            'priority': 'medium',
            'status': 'new',
        })
        task = Task.objects.get(section=section, title='Zadanie dodane przez edytora')

        self.assertContains(group_response, f'data-project-option data-project-id="{project.id}"')
        self.assertContains(group_response, f'data-section-option data-section-id="{section.id}"')
        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(task.user, self.user)

    def test_edit_shared_section_can_create_task_even_without_project_edit(self):
        shared_user = get_user_model().objects.create_user(
            username='@section.edit.create',
            email='section-edit-create@example.com',
            first_name='Section',
            last_name='Editor',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt z edytowaną grupą', code='PEG')
        readonly_section = TaskSection.objects.create(project=project, title='Grupa tylko widoczna')
        editable_section = TaskSection.objects.create(project=project, title='Grupa edytowalna')
        self._share_task_object(project, shared_user, permission='view')
        self._share_task_object(editable_section, shared_user, permission='edit')

        self.client.force_login(shared_user)
        group_response = self.client.get(reverse('tasks:task_group', args=[editable_section.id]))
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'section': editable_section.id,
            'title': 'Zadanie w edytowalnej grupie',
            'description': '',
            'priority': 'medium',
            'status': 'new',
        })

        self.assertContains(group_response, f'data-project-option data-project-id="{project.id}"')
        self.assertContains(group_response, f'data-section-option data-section-id="{editable_section.id}"')
        self.assertNotContains(group_response, f'data-section-option data-section-id="{readonly_section.id}"')
        self.assertRedirects(response, reverse('tasks:task_group', args=[editable_section.id]))
        self.assertTrue(Task.objects.filter(
            user=self.user,
            section=editable_section,
            title='Zadanie w edytowalnej grupie',
        ).exists())

    def test_project_and_group_icon_pickers_are_not_rendered(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertNotContains(response, 'data-project-icon-picker')
        self.assertNotContains(response, 'Ikona projektu')
        self.assertNotContains(response, 'Ikona grupy')

    def test_project_group_rows_do_not_render_group_type_label(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        TaskSection.objects.create(project=project, title='Frontend')

        response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")

        self.assertNotContains(
            response,
            '<span class="status-indicator status-label-plain">Grupa</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="tasks-directory-member-label">Task User</span>',
            html=True,
        )

    def test_group_members_include_project_owner_and_shared_users(self):
        shared_project_user = get_user_model().objects.create_user(
            username='shared-project-user',
            email='shared-project@example.com',
            first_name='Shared',
            last_name='Project',
            password='test-pass-123',
        )
        shared_group_user = get_user_model().objects.create_user(
            username='shared-group-user',
            email='shared-group@example.com',
            first_name='Shared',
            last_name='Group',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        self._share_task_object(project, shared_project_user)
        self._share_task_object(section, shared_group_user)

        response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")

        self.assertContains(
            response,
            '<span class="tasks-directory-member-label">Udostępnione 2</span>',
            html=True,
        )
        self.assertContains(response, 'title="Task User, Shared Project, Shared Group"')
        self.assertContains(response, 'tasks-directory-members-toolbar')
        self.assertContains(response, 'data-directory-members-search')
        self.assertContains(response, 'data-directory-member-row', count=3)
        self.assertContains(response, f'data-share-section-id="{section.id}"')
        self.assertContains(response, 'Udostępniono w projekcie')
        self.assertContains(response, 'Udostępniono w grupie')

    def test_shared_group_members_summary_opens_large_share_modal(self):
        owner = get_user_model().objects.create_user(
            username='project-owner',
            email='project-owner@example.com',
            first_name='Project',
            last_name='Owner',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=owner, name='Udostępniony projekt', code='UDP')
        section = TaskSection.objects.create(project=project, title='Udostępniona grupa')
        SharedItem.objects.create(
            content_type=ContentType.objects.get_for_model(TaskProject),
            object_id=project.pk,
            shared_by=owner,
            shared_with=self.user,
            permission='view',
        )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")
        html = response.content.decode()
        row_start = html.index('data-section-title="Udostępniona grupa"')
        members_cell_start = html.index('data-directory-members-menu', row_start)
        button_start = html.index('<button', members_cell_start)
        button_end = html.index('>', button_start)
        button_html = html[button_start:button_end]

        self.assertContains(
            response,
            '<span class="tasks-directory-member-label">Udostępnione 1</span>',
            html=True,
        )
        self.assertIn('aria-controls="directory-share-modal"', button_html)
        self.assertIn('data-directory-share-open', button_html)
        self.assertIn('data-share-can-manage="false"', button_html)
        self.assertIn(f'data-share-members-template="tasks-directory-share-members-section-{section.id}"', button_html)
        self.assertIn(f'data-share-object-id="{section.id}"', button_html)
        self.assertNotIn('data-share-action="share_section"', button_html)

    def test_view_task_uses_profile_photo_for_user_avatars(self):
        self.user.profile_photo = 'profile_photos/task-user.webp'
        self.user.save(update_fields=['profile_photo'])
        task = Task.objects.create(user=self.user, title='Zadanie z avatarem')
        TaskActivity.objects.create(task=task, actor=self.user, action='commented', message='Komentarz')

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/media/profile_photos/task-user.webp')

    def test_delete_project_removes_related_tasks_and_renumbers_remaining_tasks(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt do usunięcia', code='DEL')
        section = TaskSection.objects.create(project=project, title='Frontend')
        parent = Task.objects.create(user=self.user, section=section, title='Zadanie projektu')
        subtask = Task.objects.create(user=self.user, section=section, parent=parent, title='Podzadanie projektu')
        TaskActivity.objects.create(task=parent, actor=self.user, action='commented', message='Komentarz')
        TaskAttachment.objects.create(
            task=parent,
            file=SimpleUploadedFile('notatka.txt', b'tresc', content_type='text/plain'),
        )
        remaining_project = TaskProject.objects.create(user=self.user, name='Projekt zostaje', code='STAY')
        remaining_section = TaskSection.objects.create(project=remaining_project, title='Backend')
        remaining_task = Task.objects.create(user=self.user, section=remaining_section, title='Zadanie zostaje')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_project',
            'project_id': project.id,
        })

        remaining_task.refresh_from_db()
        messages = [message.message for message in get_messages(response.wsgi_request)]

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(TaskProject.objects.filter(id=project.id).exists())
        self.assertFalse(TaskSection.objects.filter(id=section.id).exists())
        self.assertFalse(Task.objects.filter(id__in=[parent.id, subtask.id]).exists())
        self.assertFalse(TaskActivity.objects.filter(task_id=parent.id).exists())
        self.assertFalse(TaskAttachment.objects.filter(task_id=parent.id).exists())
        self.assertEqual(remaining_task.task_id, 1)
        self.assertEqual(messages, ['Projekt usunięty razem z zadaniami.'])

    def test_bulk_delete_projects_removes_related_tasks_and_renumbers_remaining_tasks(self):
        first_project = TaskProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        first_section = TaskSection.objects.create(project=first_project, title='Frontend')
        second_project = TaskProject.objects.create(user=self.user, name='Drugi projekt', code='TWO')
        second_section = TaskSection.objects.create(project=second_project, title='Backend')
        first_task = Task.objects.create(user=self.user, section=first_section, title='Pierwsze zadanie')
        second_task = Task.objects.create(user=self.user, section=second_section, title='Drugie zadanie')
        remaining_project = TaskProject.objects.create(user=self.user, name='Projekt zostaje', code='STAY')
        remaining_section = TaskSection.objects.create(project=remaining_project, title='QA')
        remaining_task = Task.objects.create(user=self.user, section=remaining_section, title='Zadanie zostaje')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_project',
            'project_ids': [first_project.id, second_project.id],
        })

        remaining_task.refresh_from_db()
        messages = [message.message for message in get_messages(response.wsgi_request)]

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(TaskProject.objects.filter(id__in=[first_project.id, second_project.id]).exists())
        self.assertFalse(Task.objects.filter(id__in=[first_task.id, second_task.id]).exists())
        self.assertEqual(remaining_task.task_id, 1)
        self.assertEqual(messages, ['Usunięto 2 projekty razem z zadaniami.'])

    def test_all_groups_view_lists_sections(self):
        first_project = TaskProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        second_project = TaskProject.objects.create(user=self.user, name='Drugi projekt', code='TWO')
        frontend = TaskSection.objects.create(project=first_project, title='Frontend', description='Prace po stronie UI')
        TaskSection.objects.create(project=second_project, title='Backend')
        Task.objects.create(user=self.user, section=frontend, title='Zadanie frontendowe')
        TaskSection.objects.filter(pk=frontend.pk).update(
            created_at=datetime(2026, 6, 7, 12, 0, tzinfo=datetime_timezone.utc)
        )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")

        self.assertContains(response, 'Wszystkie grupy')
        self.assertContains(response, 'tasks-directory-header')
        self.assertContains(response, 'UDOSTĘPNIONE')
        self.assertContains(response, 'data-column="shared_access"', count=3)
        self.assertContains(response, 'ODPOWIEDZIALNY ZA ZADANIA')
        self.assertContains(response, 'DATA')
        self.assertContains(response, 'Frontend')
        self.assertContains(response, 'Prace po stronie UI')
        self.assertContains(response, 'Backend')
        self.assertContains(response, 'Drugi projekt')
        self.assertContains(response, first_project.code)
        self.assertContains(response, second_project.code)
        self.assertContains(response, 'Pracownik', count=2)
        self.assertContains(
            response,
            '<div class="tasks-directory-members-menu tasks-directory-sheet__cell" data-column="members" data-directory-members-menu>',
            count=2,
        )
        self.assertContains(
            response,
            '<span class="tasks-directory-member-label">Task User</span>',
            html=True,
            count=2,
        )
        self.assertContains(response, 'data-select-all-target="sections"')
        self.assertContains(response, '07.06.2026')
        self.assertNotContains(response, '7 cze')
        self.assertNotContains(response, 'tasks-section-row-icon')
        self.assertNotContains(response, 'MEMBERS')
        self.assertNotContains(response, 'DEFAULT ASSIGNEE FOR ISSUES')
        self.assertNotContains(response, 'Employee')

    def test_flat_navigation_shows_projects_and_tags(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        TaskSection.objects.create(project=project, title='Frontend')
        TaskSection.objects.create(project=project, title='Backend')
        TaskTag.objects.create(user=self.user, name='Design')

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'Wszystkie projekty')
        self.assertContains(response, 'Wszystkie grupy')
        self.assertContains(response, 'Tagi')
        self.assertContains(response, 'tasks-directory-header')
        self.assertContains(response, 'data-select-all-target="projects"')
        self.assertNotContains(response, 'Moje grupy')

    def test_tags_view_lists_tags(self):
        frontend = TaskTag.objects.create(user=self.user, name='Frontend', description='Prace po stronie UI')
        backend = TaskTag.objects.create(user=self.user, name='Backend')
        TaskTag.objects.filter(pk=frontend.pk).update(
            created_at=datetime(2026, 6, 7, 12, 0, tzinfo=datetime_timezone.utc)
        )
        project = TaskProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        section = TaskSection.objects.create(project=project, title='Grupa')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie frontendowe')
        task.tags.add(frontend)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags")

        self.assertContains(response, 'Tagi')
        self.assertContains(response, 'KOD TAGU')
        self.assertContains(response, 'NAZWA TAGU')
        self.assertContains(response, 'data-column="tag_code"', count=3)
        self.assertContains(response, 'data-column="tag_name"', count=3)
        self.assertContains(response, 'Frontend')
        self.assertContains(response, 'Prace po stronie UI')
        self.assertContains(response, 'Brak opisu')
        self.assertContains(response, 'Backend')
        self.assertContains(response, frontend.code)
        self.assertContains(response, backend.code)
        self.assertContains(response, '1 zadań')
        self.assertContains(response, '0 zadań')
        self.assertContains(response, '07.06.2026')
        self.assertNotContains(response, '7 cze')

    def test_tags_link_is_rendered(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        TaskSection.objects.create(project=project, title='Frontend')
        TaskTag.objects.create(user=self.user, name='Frontend')
        TaskTag.objects.create(user=self.user, name='Backend')

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'Tagi')
        self.assertContains(response, 'href="/tasks/?view=tags"')

    def test_create_tag_from_tasks_page(self):
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_tag',
            'name': 'Design',
            'description': 'Makiety i decyzje wizualne',
            'code': 'DES',
        })

        tag = TaskTag.objects.get(user=self.user, name='Design')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=tags")
        self.assertEqual(tag.description, 'Makiety i decyzje wizualne')
        self.assertNotEqual(tag.code, 'DES')
        self.assertRegex(tag.code, r'^TAG-\d{4}-001$')

    def test_create_tag_uses_next_tag_number_for_current_year(self):
        first = TaskTag.objects.create(user=self.user, name='Design')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_tag',
            'name': 'Backend',
            'description': '',
        })

        tag = TaskTag.objects.get(user=self.user, name='Backend')
        prefix = first.code.rsplit('-', 1)[0]

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=tags")
        self.assertEqual(tag.code, f'{prefix}-002')

    def test_delete_tag_from_tasks_page(self):
        tag = TaskTag.objects.create(user=self.user, name='Design')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_tag',
            'tag_id': tag.id,
        })

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=tags")
        self.assertFalse(TaskTag.objects.filter(id=tag.id).exists())

    def test_edit_tag_from_tasks_page(self):
        tag = TaskTag.objects.create(user=self.user, name='Design', description='Stary opis')
        old_code = tag.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_tag',
            'tag_id': tag.id,
            'name': 'UI',
            'description': 'Nowy opis',
            'code': 'NEW',
        })

        tag.refresh_from_db()

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=tags")
        self.assertEqual(tag.name, 'UI')
        self.assertEqual(tag.description, 'Nowy opis')
        self.assertEqual(tag.code, old_code)

    def test_more_options_render_edit_and_delete_actions_for_list_views(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        Task.objects.create(user=self.user, section=section, title='Zadanie')
        TaskTag.objects.create(user=self.user, name='Design')

        section_response = self.client.get(reverse('tasks:task_group', args=[section.id]))
        project_response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")
        all_tasks_response = self.client.get(f"{reverse('tasks:tasks')}?view=all-tasks")
        my_tasks_response = self.client.get(f"{reverse('tasks:tasks')}?view=my-tasks")
        projects_response = self.client.get(reverse('tasks:tasks'))
        groups_response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")
        tags_response = self.client.get(f"{reverse('tasks:tasks')}?view=tags")

        self.assertContains(section_response, 'id="delete-selected-task-menu-btn"')
        self.assertContains(section_response, 'id="edit-selected-task-menu-btn"')
        self.assertContains(project_response, 'id="delete-selected-section-menu-btn"')
        self.assertContains(project_response, 'id="edit-selected-section-menu-btn"')
        self.assertContains(all_tasks_response, 'id="delete-selected-task-menu-btn"')
        self.assertContains(all_tasks_response, 'id="edit-selected-task-menu-btn"')
        self.assertContains(my_tasks_response, 'id="delete-selected-task-menu-btn"')
        self.assertContains(my_tasks_response, 'id="edit-selected-task-menu-btn"')
        self.assertContains(projects_response, 'id="delete-selected-project-menu-btn"')
        self.assertContains(projects_response, 'id="edit-selected-project-menu-btn"')
        self.assertContains(projects_response, 'data-select-all-target="projects"')
        self.assertContains(groups_response, 'id="delete-selected-section-menu-btn"')
        self.assertContains(groups_response, 'id="edit-selected-section-menu-btn"')
        self.assertContains(groups_response, 'data-select-all-target="sections"')
        self.assertNotContains(groups_response, 'id="delete-selected-tag-menu-btn"')
        self.assertNotContains(groups_response, 'id="edit-selected-tag-menu-btn"')
        self.assertContains(tags_response, 'id="delete-selected-tag-menu-btn"')
        self.assertContains(tags_response, 'id="edit-selected-tag-menu-btn"')

    def test_create_task_modal_assigns_existing_tags(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        tag = TaskTag.objects.create(user=self.user, name='Pilne')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'title': 'Zadanie z tagiem',
            'section': section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'tags': [tag.id],
        })

        task = Task.objects.get(user=self.user, title='Zadanie z tagiem')

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(list(task.tags.all()), [tag])

    def test_create_task_modal_saves_due_at(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'title': 'Zadanie z terminem',
            'section': section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'due_at': '2026-06-12T14:30',
        })

        task = Task.objects.get(user=self.user, title='Zadanie z terminem')

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(timezone.localtime(task.due_at).strftime('%Y-%m-%dT%H:%M'), '2026-06-12T14:30')

    def test_task_due_urgency_uses_time_remaining(self):
        now = timezone.now()

        self.assertEqual(Task(due_at=None).due_urgency, 'none')
        self.assertEqual(Task(due_at=now + timedelta(days=8)).due_urgency, 'green')
        self.assertEqual(Task(due_at=now + timedelta(days=5)).due_urgency, 'green')
        self.assertEqual(Task(due_at=now + timedelta(days=2)).due_urgency, 'yellow')
        self.assertEqual(Task(due_at=now + timedelta(hours=2)).due_urgency, 'red')
        self.assertEqual(Task(due_at=now - timedelta(minutes=1)).due_urgency, 'red')

    def test_create_subtask_from_task_detail(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie główne')

        response = self.client.post(reverse('tasks:view-task', args=[task.task_id]), {
            'action': 'create_subtask_modal',
            'title': 'Pierwsze podzadanie',
            'description': 'Opis podzadania',
            'status': 'in_progress',
        })

        subtask = Task.objects.get(user=self.user, title='Pierwsze podzadanie')

        self.assertRedirects(response, reverse('tasks:view-task', args=[task.task_id]))
        self.assertEqual(subtask.parent, task)
        self.assertEqual(subtask.section, section)
        self.assertEqual(subtask.description, 'Opis podzadania')
        self.assertEqual(subtask.priority, 'medium')
        self.assertEqual(subtask.status, 'in_progress')
        self.assertEqual(list(subtask.tags.all()), [])

        detail_response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))
        subtask_detail_response = self.client.get(reverse('tasks:view-subtask', args=[subtask.task_id]))
        list_response = self.client.get(reverse('tasks:task_group', args=[section.id]))

        self.assertContains(detail_response, 'Pierwsze podzadanie')
        self.assertContains(detail_response, 'Opis podzadania')
        self.assertContains(detail_response, 'Realizowane')
        self.assertContains(detail_response, 'tasks-issue-row--compact')
        self.assertContains(detail_response, reverse('tasks:view-subtask', args=[subtask.task_id]))
        self.assertNotContains(detail_response, '<span>Zadanie</span>', html=True)
        self.assertContains(subtask_detail_response, '<label for="id_parent">Zadanie</label>', html=True)
        self.assertContains(subtask_detail_response, 'Zadanie główne')
        subtask_detail_html = subtask_detail_response.content.decode()
        project_label_position = subtask_detail_html.index('<label for="id_project">Projekt</label>')
        section_label_position = subtask_detail_html.index('<label for="id_section">Grupa</label>')
        parent_label_position = subtask_detail_html.index('<label for="id_parent">Zadanie</label>')
        self.assertLess(project_label_position, section_label_position)
        self.assertLess(section_label_position, parent_label_position)
        self.assertContains(subtask_detail_response, f'href="{reverse("tasks:view-task", args=[task.task_id])}"')
        self.assertContains(subtask_detail_response, 'aria-label="Wróć do zadania"')
        self.assertNotRegex(
            subtask_detail_response.content.decode(),
            rf'<a\s+href="{re.escape(reverse("tasks:view-task", args=[task.task_id]))}"[^>]*data-history-back',
        )
        self.assertNotContains(subtask_detail_response, f'{project.code}-{task.task_id}')
        self.assertNotContains(detail_response, f'{project.code}-{subtask.task_id}')
        self.assertNotContains(list_response, 'Pierwsze podzadanie')

    def test_task_detail_sidebar_shows_project_code(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))
        content = response.content.decode()

        self.assertContains(response, '<span>Kod projektu</span>', html=True)
        self.assertContains(response, f'<strong class="tasks-issue-muted">{project.code}</strong>', html=True)
        self.assertLess(content.index('<label for="id_tags">Tagi</label>'), content.index('<span>Kod projektu</span>'))
        self.assertLess(content.index('<span>Kod projektu</span>'), content.index('<span>Utworzył</span>'))

    def test_subtask_detail_can_change_parent_task(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        first_section = TaskSection.objects.create(project=project, title='Frontend')
        second_section = TaskSection.objects.create(project=project, title='Backend')
        first_parent = Task.objects.create(user=self.user, section=first_section, title='Zadanie frontendowe')
        second_parent = Task.objects.create(user=self.user, section=second_section, title='Zadanie backendowe')
        subtask = Task.objects.create(user=self.user, section=first_section, parent=first_parent, title='Podzadanie')

        response = self.client.post(reverse('tasks:view-subtask', args=[subtask.task_id]), {
            'title': 'Podzadanie',
            'parent': second_parent.id,
            'project': project.id,
            'section': first_section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'time_spent_hours': '',
            'time_spent_minutes': '',
        })

        subtask.refresh_from_db()

        self.assertRedirects(response, reverse('tasks:view-subtask', args=[subtask.task_id]))
        self.assertEqual(subtask.parent, second_parent)
        self.assertEqual(subtask.section, second_section)

    def test_subtask_detail_does_not_allow_adding_attachments(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        parent = Task.objects.create(user=self.user, section=section, title='Zadanie główne')
        subtask = Task.objects.create(user=self.user, section=section, parent=parent, title='Podzadanie')

        detail_response = self.client.get(reverse('tasks:view-subtask', args=[subtask.task_id]))

        self.assertNotContains(detail_response, 'Dodaj załącznik')
        self.assertNotContains(detail_response, 'name="attachments"')

        response = self.client.post(reverse('tasks:view-subtask', args=[subtask.task_id]), {
            'title': 'Podzadanie',
            'parent': parent.id,
            'project': project.id,
            'section': section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'time_spent_hours': '',
            'time_spent_minutes': '',
            'attachments': SimpleUploadedFile('notatka.txt', b'tresc', content_type='text/plain'),
        })

        self.assertRedirects(response, reverse('tasks:view-subtask', args=[subtask.task_id]))
        self.assertFalse(TaskAttachment.objects.filter(task=subtask).exists())

    def test_task_activity_comment_is_saved_from_detail_view(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(reverse('tasks:view-task', args=[task.task_id]), {
            'action': 'add_activity_comment',
            'activity_comment': 'To jest wiadomość w czacie.',
        })

        activity = TaskActivity.objects.get(task=task, kind='comment')

        self.assertRedirects(response, reverse('tasks:view-task', args=[task.task_id]))
        self.assertEqual(activity.actor, self.user)
        self.assertEqual(activity.action, 'commented')
        self.assertEqual(activity.message, 'To jest wiadomość w czacie.')

        detail_response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))
        self.assertContains(detail_response, 'Aktywność')
        self.assertContains(detail_response, 'Tylko czat')
        self.assertContains(detail_response, 'Tylko historia')
        self.assertContains(detail_response, 'To jest wiadomość w czacie.')

    def test_task_activity_feed_shows_newest_items_first(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')
        TaskActivity.objects.create(task=task, actor=self.user, kind='comment', action='commented', message='Starsza wiadomość')
        TaskActivity.objects.create(task=task, actor=self.user, kind='comment', action='commented', message='Nowsza wiadomość')

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))
        content = response.content.decode()

        self.assertLess(content.index('Nowsza wiadomość'), content.index('Starsza wiadomość'))

    def test_detail_update_records_multiple_field_changes_as_one_activity(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(reverse('tasks:view-task', args=[task.task_id]), {
            'title': 'Zadanie po zmianach',
            'parent': '',
            'section': section.id,
            'description': 'Nowy opis',
            'priority': 'high',
            'status': 'in_progress',
            'due_at': '2026-06-15T09:45',
            'time_spent_hours': 1,
            'time_spent_minutes': 15,
        })

        activities = TaskActivity.objects.filter(task=task).exclude(action='created')
        activity = activities.get()

        self.assertRedirects(response, reverse('tasks:view-task', args=[task.task_id]))
        self.assertEqual(activity.action, 'updated')
        self.assertEqual(activity.message, 'zaktualizował zadanie')
        self.assertEqual(activity.metadata['fields'], ['status', 'priorytet', 'tytuł', 'opis', 'termin wykonania', 'czas pracy'])
        self.assertEqual(activity.metadata['changes'][0]['from_label'], 'Nowe')
        self.assertEqual(activity.metadata['changes'][0]['to_label'], 'Realizowane')
        self.assertEqual(activity.metadata['changes'][1]['from_label'], 'Średni')
        self.assertEqual(activity.metadata['changes'][1]['to_label'], 'Wysoki')
        self.assertEqual(activity.metadata['changes'][4]['to_label'], '15.06.2026 09:45')

    def test_task_detail_uses_autosave_without_manual_save_button(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))

        self.assertContains(response, 'data-task-autosave-status')
        self.assertNotContains(response, 'class="tasks-issue-save"')
        self.assertNotContains(response, 'tasks-issue-autosave-section')

    def test_detail_autosave_returns_json_and_records_activity(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(
            reverse('tasks:view-task', args=[task.task_id]),
            {
                'autosave': '1',
                'title': 'Zadanie po autosave',
                'parent': '',
                'section': section.id,
                'description': 'Opis zapisany automatycznie',
                'priority': 'high',
                'status': 'in_progress',
                'due_at': '',
                'time_spent_hours': '',
                'time_spent_minutes': '',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        task.refresh_from_db()
        activity = TaskActivity.objects.filter(task=task).exclude(action='created').get()

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['status'], 'success')
        self.assertEqual(payload['task']['title'], 'Zadanie po autosave')
        self.assertIn('data-activity-kind="history"', payload['activity_html'])
        self.assertIn('zaktualizował zadanie', payload['activity_html'])
        self.assertEqual(task.title, 'Zadanie po autosave')
        self.assertEqual(task.priority, 'high')
        self.assertEqual(activity.action, 'updated')

    def test_detail_autosave_returns_validation_errors_as_json(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(
            reverse('tasks:view-task', args=[task.task_id]),
            {
                'autosave': '1',
                'title': '',
                'parent': '',
                'section': section.id,
                'description': '',
                'priority': 'high',
                'status': 'in_progress',
                'due_at': '',
                'time_spent_hours': '',
                'time_spent_minutes': '',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        task.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
        self.assertIn('Tytuł', response.json()['message'])
        self.assertEqual(task.title, 'Zadanie')

    def test_detail_shows_saved_time_spent_with_delete_action(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(
            user=self.user,
            section=section,
            title='Zadanie',
            time_spent_hours=2,
            time_spent_minutes=5,
        )

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))

        self.assertContains(response, '02:05')
        self.assertContains(response, 'name="action" value="clear_time_spent"')

    def test_clear_time_spent_action_removes_time_and_records_activity(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(
            user=self.user,
            section=section,
            title='Zadanie',
            time_spent_hours=2,
            time_spent_minutes=5,
        )

        response = self.client.post(reverse('tasks:view-task', args=[task.task_id]), {
            'action': 'clear_time_spent',
        })

        task.refresh_from_db()
        activity = TaskActivity.objects.filter(task=task).exclude(action='created').get()

        self.assertRedirects(response, reverse('tasks:view-task', args=[task.task_id]))
        self.assertIsNone(task.time_spent_hours)
        self.assertIsNone(task.time_spent_minutes)
        self.assertEqual(activity.metadata['fields'], ['czas pracy'])
        self.assertEqual(activity.metadata['changes'][0]['from_label'], '02:05')
        self.assertEqual(activity.metadata['changes'][0]['to_label'], '00:00')

    def test_update_task_status_records_activity(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(
            reverse('tasks:update_task_status', args=[task.task_id]),
            data=json.dumps({'status': 'in_progress'}),
            content_type='application/json',
        )

        activity = TaskActivity.objects.filter(task=task, action='status_changed').latest('id')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(activity.actor, self.user)
        self.assertEqual(activity.metadata['from_label'], 'Nowe')
        self.assertEqual(activity.metadata['to_label'], 'Realizowane')

    def test_my_tasks_view_is_available_from_secondary_navigation(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        Task.objects.create(user=self.user, section=section, title='Moje zadanie testowe')

        response = self.client.get(f"{reverse('tasks:tasks')}?view=my-tasks")

        self.assertContains(response, 'Moje zadania')
        self.assertContains(response, 'Moje zadanie testowe')
        self.assertContains(
            response,
            f'<a href="{reverse("tasks:tasks")}?view=my-tasks" class="tasks-rail-link is-active">',
        )

    def test_secondary_navigation_is_flat_and_limited(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'Moje zadania')
        self.assertContains(response, 'Wszystkie zadania')
        self.assertContains(response, 'Wszystkie projekty')
        self.assertContains(response, 'Wszystkie grupy')
        self.assertContains(response, 'Tagi')
        self.assertContains(response, 'tasks-rail-nav-separator')
        self.assertNotContains(response, 'Udostępnione zadania')
        self.assertNotContains(response, 'Udostępnione grupy')
        self.assertNotContains(response, 'Udostępnione projekty')
        self.assertNotContains(response, 'Moje grupy')
        self.assertNotContains(response, 'data-rail-nav-group')
        self.assertNotContains(response, 'data-rail-nav-group-toggle')

        all_tasks_response = self.client.get(f"{reverse('tasks:tasks')}?view=all-tasks")

        self.assertContains(
            all_tasks_response,
            f'<a href="{reverse("tasks:tasks")}?view=all-tasks" class="tasks-rail-link is-active">',
        )

    def test_edit_project_updates_details_without_changing_code_or_icon(self):
        company = Company.objects.create(owner=self.user, name='Firma projektowa')
        project = TaskProject.objects.create(user=self.user, name='Stara nazwa', description='Stary opis', code='OLD')
        old_code = project.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Nowa nazwa',
            'description': 'Nowy opis',
            'code': 'new',
            'icon': 'rocket',
            'priority': 'medium',
            'due_at': '2026-08-20',
            'company': company.id,
        })

        project.refresh_from_db()

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.name, 'Nowa nazwa')
        self.assertEqual(project.description, 'Nowy opis')
        self.assertEqual(project.priority, 'medium')
        self.assertEqual(project.due_at, date(2026, 8, 20))
        self.assertEqual(project.company, company)
        self.assertEqual(project.icon, '')
        self.assertEqual(project.code, old_code)

    def test_edit_project_ignores_icon_field(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ', icon='rocket')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Projekt',
            'description': '',
            'code': 'PRJ',
            'icon': '',
        })

        project.refresh_from_db()

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.icon, 'rocket')

    def test_edit_project_ignores_posted_code(self):
        TaskProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        project = TaskProject.objects.create(user=self.user, name='Drugi projekt', code='TWO')
        old_code = project.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Drugi projekt',
            'description': '',
            'code': 'one',
            'icon': '',
        })

        project.refresh_from_db()

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.code, old_code)

    def test_create_section_saves_description(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_section',
            'project_id': project.id,
            'title': 'Frontend',
            'description': 'Prace nad widokami',
            'icon': 'star',
        })

        section = TaskSection.objects.get(project=project, title='Frontend')

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(section.description, 'Prace nad widokami')
        self.assertEqual(section.icon, '')

    def test_edit_section_updates_description(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend', description='Stary opis')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_section',
            'section_id': section.id,
            'title': 'API',
            'description': 'Nowy opis',
            'icon': '',
        })

        section.refresh_from_db()

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(section.title, 'API')
        self.assertEqual(section.description, 'Nowy opis')

    def test_bulk_delete_sections_from_all_groups_view(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        first_section = TaskSection.objects.create(project=project, title='Frontend')
        second_section = TaskSection.objects.create(project=project, title='Backend')
        remaining_section = TaskSection.objects.create(project=project, title='QA')
        first_task = Task.objects.create(user=self.user, section=first_section, title='Pierwsze zadanie')
        second_task = Task.objects.create(user=self.user, section=second_section, title='Drugie zadanie')
        remaining_task = Task.objects.create(user=self.user, section=remaining_section, title='Zadanie zostaje')

        response = self.client.post(f"{reverse('tasks:tasks')}?view=all-groups", {
            'action': 'delete_section',
            'section_ids': [first_section.id, second_section.id],
        })

        remaining_task.refresh_from_db()
        messages = [message.message for message in get_messages(response.wsgi_request)]

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=all-groups")
        self.assertFalse(TaskSection.objects.filter(id__in=[first_section.id, second_section.id]).exists())
        self.assertFalse(Task.objects.filter(id__in=[first_task.id, second_task.id]).exists())
        self.assertTrue(TaskSection.objects.filter(id=remaining_section.id).exists())
        self.assertEqual(remaining_task.task_id, 1)
        self.assertEqual(messages, ['Usunięto 2 grupy razem z zadaniami.'])

    def test_bulk_update_status_runs_task_completion_logic(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        first_task = Task.objects.create(user=self.user, section=section, title='Pierwsze zadanie')
        second_task = Task.objects.create(user=self.user, section=section, title='Drugie zadanie')

        response = self.client.post(
            reverse('tasks:bulk_update_status'),
            data=json.dumps({
                'task_ids': [first_task.task_id, second_task.task_id],
                'status': 'closed',
            }),
            content_type='application/json',
        )

        first_task.refresh_from_db()
        second_task.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['updated_count'], 2)
        self.assertTrue(first_task.is_completed)
        self.assertTrue(second_task.is_completed)
        self.assertIsNotNone(first_task.completion_date)
        self.assertIsNotNone(second_task.completion_date)

    def test_bulk_update_status_rejects_invalid_status(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.post(
            reverse('tasks:bulk_update_status'),
            data=json.dumps({
                'task_ids': [task.task_id],
                'status': 'nie-ma-takiego',
            }),
            content_type='application/json',
        )

        task.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['message'], 'Nieprawidłowy status')
        self.assertEqual(task.status, 'new')
