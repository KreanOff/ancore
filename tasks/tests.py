import json
import re
import tempfile
from datetime import date, datetime, timedelta, timezone as datetime_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.models import Case, Count, IntegerField, Value, When
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.urls import reverse

from contacts.models import Company, SharedItem
from .models import Task, TaskActivity, TaskAttachment, TaskProject, TaskProjectNote, TaskSection, TaskSectionNote, TaskTag, TaskTagNote


class TaskProjectCreationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='task-user',
            email='task-user@example.com',
            first_name='Task',
            last_name='User',
            password='test-pass-123',
        )
        self.client.force_login(self.user)

    def test_create_project_adds_default_group(self):
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt testowy',
            'section_title': 'Plan wdrożenia',
            'section_code': 'wd',
            'description': 'Opis projektu',
            'code': 'PT',
            'icon': 'star',
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt testowy')
        section = TaskSection.objects.get(project=project)

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.description, 'Opis projektu')
        self.assertIsNone(project.responsible_user)
        self.assertEqual(project.icon, '')
        self.assertEqual(project.code, 'PT')
        self.assertEqual(section.title, 'Plan wdrożenia')
        self.assertEqual(section.code, 'WD')
        self.assertEqual(section.kind, 'custom')
        self.assertEqual(section.icon, '')
        self.assertEqual(section.order, 0)
        self.assertEqual(section.full_code, f'{project.code}/{section.code}')

    def test_create_project_saves_client_and_responsible_fields(self):
        company = Company.objects.create(owner=self.user, name='Ancore Labs')
        responsible_user = get_user_model().objects.create_user(
            username='responsible-user',
            email='responsible@example.com',
            first_name='Anna',
            last_name='Projektowa',
            password='test-pass-123',
        )
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt z metadanymi',
            'section_title': 'Plan',
            'description': '',
            'priority': 'urgent',
            'due_at': '2026-07-15',
            'company': company.id,
            'responsible_user': responsible_user.id,
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt z metadanymi')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertEqual(project.priority, 'urgent')
        self.assertEqual(project.due_at, date(2026, 7, 15))
        self.assertEqual(project.company, company)
        self.assertEqual(project.responsible_user, responsible_user)

    def test_create_project_modal_shows_project_parameters(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'Parametry projektu')
        self.assertContains(response, 'Pierwsza grupa')
        self.assertContains(response, 'aria-label="Wybierz priorytet projektu"')
        self.assertContains(response, 'data-inline-priority-icon')
        self.assertContains(response, 'data-inline-select-value="urgent"')
        self.assertContains(response, 'Pilny')
        self.assertContains(response, 'Firma')
        self.assertContains(response, 'data-ancore-custom-select-search="true"')
        self.assertContains(response, 'data-ancore-custom-select-search-placeholder="Szukaj firmy"')
        self.assertContains(response, 'Odpowiedzialny')
        self.assertContains(response, 'data-ancore-custom-select-search-placeholder="Szukaj osoby"')
        self.assertContains(response, 'Status projektu')
        self.assertContains(response, 'Etap')
        self.assertContains(response, 'Kondycja')
        self.assertContains(response, 'Budżet')
        self.assertNotContains(response, 'Klient / firma')
        self.assertContains(response, 'Kod projektu')
        self.assertContains(response, 'name="code"')
        self.assertContains(response, 'Kod pierwszej grupy')
        self.assertContains(response, 'name="section_code"')
        self.assertNotContains(response, 'Automatyczny')
        self.assertNotContains(response, 'data-responsible-select-url')
        self.assertNotContains(response, 'Szukaj lub wpisz ID Ancore')

    def test_edit_project_updates_responsible_field(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', responsible_user=self.user)
        target = get_user_model().objects.create_user(
            username='@outside-contact',
            email='outside@example.com',
            first_name='Osoba',
            last_name='Spoza Kontaktow',
            password='test-pass-123',
        )

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project',
            'project_id': project.id,
            'name': 'Projekt',
            'description': '',
            'priority': 'none',
            'due_at': '',
            'company': '',
            'responsible_user': target.id,
        })

        project.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(project.responsible_user, target)

        response = self.client.get(reverse('tasks:tasks'))
        self.assertContains(response, 'Osoba Spoza Kontaktow')
        self.assertContains(response, 'data-project-responsible-user-id')
        self.assertNotContains(response, 'tasks-responsible-select__avatar')

    def test_search_field_is_rendered_in_topbar(self):
        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        topbar_start = html.index('class="tasks-topbar"')
        topbar_end = html.index('</header>', topbar_start)
        topbar_html = html[topbar_start:topbar_end]
        filterbar_start = html.index('class="tasks-filterbar"', topbar_end)
        filterbar_end = html.index('</div>', filterbar_start)
        filterbar_html = html[filterbar_start:filterbar_end]

        self.assertIn('tasks-titlebar-search', topbar_html)
        self.assertIn('id="filter-search"', topbar_html)
        self.assertNotIn('data-filter-search-submit', topbar_html)
        self.assertNotIn('id="filter-search"', filterbar_html)

    def test_projects_view_shows_priority_filter_without_status_filter(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'data-priority-filter-menu')
        self.assertContains(response, 'data-priority-filter-label')
        self.assertNotContains(response, 'data-status-filter-menu')

    def test_sort_button_exposes_mutable_lucide_icon(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'data-task-sort')
        self.assertContains(response, 'data-sort-direction="asc"')
        self.assertContains(response, 'data-lucide="arrow-up-wide-narrow"')
        self.assertContains(response, 'data-task-sort-icon')

    def test_projects_view_renders_server_filter_and_sort_controls(self):
        company = Company.objects.create(owner=self.user, name='Acme CRM')
        TaskProject.objects.create(
            user=self.user,
            name='Projekt CRM',
            status='planned',
            stage='offer',
            health='at_risk',
            company=company,
            responsible_user=self.user,
        )
        TaskProject.objects.create(user=self.user, name='Projekt bez firmy')

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'data-project-sort-menu')
        self.assertContains(response, 'data-project-sort-value="priority_desc"')
        self.assertContains(response, 'data-project-filter-menu="status"')
        self.assertContains(response, 'data-project-filter-menu="stage"')
        self.assertContains(response, 'data-project-filter-menu="health"')
        self.assertContains(response, 'data-project-filter-menu="company"')
        self.assertContains(response, 'data-project-filter-menu="responsible"')
        self.assertContains(response, 'data-project-filter-input="company"')
        self.assertContains(response, 'data-project-filter-search', count=2)
        self.assertContains(response, 'placeholder="Szukaj firmy"')
        self.assertContains(response, 'placeholder="Szukaj osoby"')
        self.assertContains(response, 'data-project-filter-empty', count=2)
        self.assertContains(response, 'data-project-filter-value="none"')
        self.assertContains(response, 'Acme CRM')
        self.assertContains(response, 'Task User')

    def test_projects_view_filters_searches_and_sorts_on_server(self):
        company = Company.objects.create(owner=self.user, name='Acme CRM')
        responsible = get_user_model().objects.create_user(
            username='project-owner',
            email='owner@example.com',
            first_name='Anna',
            last_name='Kowalska',
            password='test-pass-123',
        )
        matching = TaskProject.objects.create(
            user=self.user,
            name='Oferta CRM',
            code='P-CRM0001',
            status='active',
            stage='offer',
            health='at_risk',
            priority='high',
            company=company,
            responsible_user=responsible,
        )
        TaskProject.objects.create(
            user=self.user,
            name='Projekt wewnętrzny',
            code='P-INT0001',
            status='planned',
            stage='internal',
            health='ok',
            priority='none',
        )

        response = self.client.get(
            reverse('tasks:tasks'),
            {
                'q': 'aktywny',
                'status': 'active',
                'stage': 'offer',
                'health': 'at_risk',
                'company': company.id,
                'responsible': responsible.id,
                'priority': 'high',
            },
        )
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-project-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-project-row tasks-directory-row', count=1)
        self.assertIn(matching.name, table_html)
        self.assertNotIn('Projekt wewnętrzny', table_html)
        self.assertContains(response, 'value="active" data-project-filter-input="status"')
        self.assertContains(response, 'Status: Aktywny')
        self.assertContains(response, 'Etap: Oferta')
        self.assertContains(response, 'Kondycja: Zagrożony')

    def test_projects_view_sort_preserves_query_params_in_pagination(self):
        low = TaskProject.objects.create(user=self.user, name='Niski projekt', priority='low')
        urgent = TaskProject.objects.create(user=self.user, name='Pilny projekt', priority='urgent')
        for index in range(55):
            TaskProject.objects.create(
                user=self.user,
                name=f'Projekt testowy {index:03d}',
                priority='low',
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?sort=priority_desc&page_size=50")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-project-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertLess(table_html.index(urgent.name), table_html.index(low.name))
        self.assertContains(response, 'Sortowanie: Priorytet')
        self.assertContains(response, 'data-project-page-url="/tasks/?sort=priority_desc&amp;page_size=50&amp;page=2"')

    def test_task_create_modal_billable_checkbox_is_checked_by_default(self):
        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        field_index = html.index('name="is_billable"')
        input_start = html.rfind('<input', 0, field_index)
        input_end = html.index('>', field_index)
        input_html = html[input_start:input_end]

        self.assertIn('class="tasks-inline-checkbox"', input_html)
        self.assertIn('checked', input_html)

    def test_all_groups_view_shows_priority_filter_without_status_filter(self):
        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")

        self.assertContains(response, 'data-priority-filter-menu')
        self.assertContains(response, 'data-priority-filter-label')
        self.assertNotContains(response, 'data-status-filter-menu')

    def test_all_groups_view_renders_server_filter_and_sort_controls(self):
        owner = get_user_model().objects.create_user(
            username='group-owner',
            email='group-owner@example.com',
            first_name='Olga',
            last_name='Grupowa',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt grupowy', code='GRP')
        TaskSection.objects.create(
            project=project,
            title='Frontend',
            status='ready',
            kind='milestones',
            owner=owner,
        )
        TaskSection.objects.create(project=project, title='Bez osoby')

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")

        self.assertContains(response, 'data-project-sort-menu')
        self.assertContains(response, 'data-project-sort-value="priority_desc"')
        self.assertContains(response, 'data-project-filter-menu="status"')
        self.assertContains(response, 'data-project-filter-menu="kind"')
        self.assertContains(response, 'data-project-filter-menu="group_project"')
        self.assertContains(response, 'data-project-filter-menu="owner"')
        self.assertContains(response, 'data-project-filter-input="group_project"')
        self.assertContains(response, 'placeholder="Szukaj projektu"')
        self.assertContains(response, 'placeholder="Szukaj osoby"')
        self.assertContains(response, 'data-project-filter-empty', count=2)
        self.assertContains(response, 'Projekt grupowy')
        self.assertContains(response, 'Olga Grupowa')
        self.assertContains(response, 'data-project-filter-value="none"')

    def test_all_groups_view_filters_searches_and_sorts_on_server(self):
        owner = get_user_model().objects.create_user(
            username='group-owner',
            email='group-owner@example.com',
            first_name='Olga',
            last_name='Grupowa',
            password='test-pass-123',
        )
        matching_project = TaskProject.objects.create(user=self.user, name='Projekt CRM', code='CRM')
        other_project = TaskProject.objects.create(user=self.user, name='Projekt wewnętrzny', code='INT')
        matching = TaskSection.objects.create(
            project=matching_project,
            title='Kamień CRM',
            description='Gotowy etap wdrożenia',
            status='ready',
            kind='milestones',
            priority='urgent',
            owner=owner,
        )
        TaskSection.objects.create(
            project=other_project,
            title='Backend',
            status='open',
            kind='issues',
            priority='none',
        )

        response = self.client.get(
            reverse('tasks:tasks'),
            {
                'view': 'all-groups',
                'q': 'gotowa',
                'status': 'ready',
                'kind': 'milestones',
                'group_project': matching_project.id,
                'owner': owner.id,
                'priority': 'urgent',
            },
        )
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=1)
        self.assertIn(matching.title, table_html)
        self.assertNotIn('Backend', table_html)
        self.assertContains(response, 'value="ready" data-project-filter-input="status"')
        self.assertContains(response, 'Status: Gotowa')
        self.assertContains(response, 'Typ: Kamienie milowe')
        self.assertContains(response, 'Projekt: Projekt CRM')
        self.assertContains(response, 'Odpowiedzialny: Olga Grupowa')

    def test_all_groups_view_sort_preserves_query_params_in_pagination(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt grup', code='GRP')
        low = TaskSection.objects.create(project=project, title='Niska grupa', priority='low')
        urgent = TaskSection.objects.create(project=project, title='Pilna grupa', priority='urgent')
        for index in range(55):
            TaskSection.objects.create(
                project=project,
                title=f'Grupa testowa {index:03d}',
                priority='low',
                order=index,
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups&sort=priority_desc&page_size=50")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertLess(table_html.index(urgent.title), table_html.index(low.title))
        self.assertContains(response, 'Sortowanie: Priorytet')
        self.assertContains(response, 'data-project-page-url="/tasks/?view=all-groups&amp;sort=priority_desc&amp;page_size=50&amp;page=2"')

    def test_tags_view_renders_server_filter_controls(self):
        TaskTag.objects.create(user=self.user, name='Tag właściciela', owner_label='Zespół CRM')
        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags")

        self.assertContains(response, 'data-project-filter-menu="status"')
        self.assertContains(response, 'data-project-filter-menu="category"')
        self.assertContains(response, 'data-project-filter-menu="scope"')
        self.assertContains(response, 'data-project-filter-menu="owner"')
        self.assertContains(response, 'data-project-filter-menu="priority"')
        self.assertContains(response, 'name="status" value="" data-project-filter-input="status"')
        self.assertContains(response, 'name="category" value="" data-project-filter-input="category"')
        self.assertContains(response, 'name="scope" value="" data-project-filter-input="scope"')
        self.assertContains(response, 'name="owner" value="" data-project-filter-input="owner"')
        self.assertContains(response, 'name="priority" value="" data-project-filter-input="priority"')
        self.assertContains(response, 'placeholder="Szukaj właściciela"')
        self.assertContains(response, 'Zespół CRM')
        self.assertNotContains(response, 'data-status-filter-menu')
        self.assertNotContains(response, 'data-priority-filter-menu')

    def test_tags_view_filters_on_server(self):
        matching = TaskTag.objects.create(
            user=self.user,
            name='Ryzyko klienta',
            description='Pilny temat wdrożenia',
            category='risk',
            priority='urgent',
            scope='clients',
            owner_label='Zespół CRM',
            status='archived',
        )
        TaskTag.objects.create(
            user=self.user,
            name='Tag ogólny',
            description='Inny temat',
            category='general',
            priority='low',
            scope='tasks',
            owner_label='Zespół Support',
            status='active',
        )

        response = self.client.get(
            reverse('tasks:tasks'),
            {
                'view': 'tags',
                'q': 'ryzyko',
                'status': 'archived',
                'category': 'risk',
                'scope': 'clients',
                'owner': 'Zespół CRM',
                'priority': 'urgent',
            },
        )
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-tag-sheet__row', count=1)
        self.assertIn(matching.name, table_html)
        self.assertNotIn('Tag ogólny', table_html)
        self.assertContains(response, 'Status: Archiwalny')
        self.assertContains(response, 'Typ: Ryzyko')
        self.assertContains(response, 'Zakres: Klienci')
        self.assertContains(response, 'Właściciel: Zespół CRM')
        self.assertContains(response, 'Priorytet: Krytyczny')

    def test_tags_view_renders_server_sort_controls(self):
        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags")

        self.assertContains(response, 'data-project-sort-menu')
        self.assertContains(response, 'data-project-default-sort="name_asc"')
        self.assertContains(response, 'aria-label="Sortowanie tagów"')
        self.assertContains(response, 'name="sort" value="" data-project-sort-input')
        self.assertContains(response, 'data-project-sort-value="name_desc"')
        self.assertContains(response, 'data-project-sort-value="priority_desc"')
        self.assertContains(response, 'data-project-sort-value="task_count_desc"')
        self.assertContains(response, 'data-project-sort-value="related_desc"')

    def test_tags_view_sorts_by_priority_and_preserves_query_params_in_pagination(self):
        low = TaskTag.objects.create(user=self.user, name='Niski tag', priority='low')
        urgent = TaskTag.objects.create(user=self.user, name='Pilny tag', priority='urgent')
        for index in range(55):
            TaskTag.objects.create(
                user=self.user,
                name=f'Tag testowy {index:03d}',
                priority='low',
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags&sort=priority_desc&page_size=50")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertLess(table_html.index(urgent.name), table_html.index(low.name))
        self.assertContains(response, 'Sortowanie: Priorytet')
        self.assertContains(response, 'data-project-page-url="/tasks/?view=tags&amp;sort=priority_desc&amp;page_size=50&amp;page=2"')

    def test_tags_view_sorts_by_task_count(self):
        busy = TaskTag.objects.create(user=self.user, name='Aktywny tag')
        quiet = TaskTag.objects.create(user=self.user, name='Cichy tag')
        for index in range(2):
            task = Task.objects.create(user=self.user, title=f'Zadanie aktywne {index}')
            task.tags.add(busy)
        task = Task.objects.create(user=self.user, title='Zadanie ciche')
        task.tags.add(quiet)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags&sort=task_count_desc")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertLess(table_html.index(busy.name), table_html.index(quiet.name))
        self.assertContains(response, 'Sortowanie: Najwięcej zadań')
        self.assertContains(response, '2 zadań')

    def test_projects_priority_column_uses_priority_icons(self):
        project = TaskProject.objects.create(user=self.user, name='Pilny projekt', priority='urgent')

        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        row_start = html.index(f'data-project-id="{project.id}"')
        row_end = html.index('</article>', row_start)
        row_html = html[row_start:row_end]

        self.assertIn('data-column="priority"', row_html)
        self.assertIn('tasks-row-priority priority-urgent', row_html)
        self.assertIn('data-lucide="circle-alert"', row_html)
        self.assertNotIn('tasks-project-priority-dot', row_html)

    def test_group_priority_is_rendered_independently_from_project_priority(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt pilny', priority='urgent')
        section = TaskSection.objects.create(project=project, title='Grupa bez priorytetu', priority='none')

        project_response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")
        all_groups_response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")

        for response in (project_response, all_groups_response):
            html = response.content.decode()
            row_start = html.index(f'data-section-id="{section.id}"')
            row_end = html.index('</article>', row_start)
            row_html = html[row_start:row_end]

            self.assertIn('data-column="priority"', row_html)
            self.assertIn('tasks-row-priority priority-none', row_html)
            self.assertNotIn('tasks-row-priority priority-urgent', row_html)
            self.assertNotIn('Pilny', row_html)

    def test_groups_priority_column_uses_section_priority_icons(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', priority='none')
        section = TaskSection.objects.create(project=project, title='Pilna grupa', priority='urgent')

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")
        html = response.content.decode()
        row_start = html.index(f'data-section-id="{section.id}"')
        row_end = html.index('</article>', row_start)
        row_html = html[row_start:row_end]

        self.assertIn('data-column="priority"', row_html)
        self.assertIn('tasks-row-priority priority-urgent', row_html)
        self.assertIn('data-lucide="circle-alert"', row_html)
        self.assertIn('Pilny', row_html)

    def test_edit_project_modal_uses_issue_modal_layout(self):
        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        modal_start = html.index('id="project-rename-modal"')
        modal_end = html.index('id="section-create-modal"', modal_start)
        modal_html = html[modal_start:modal_end]

        self.assertIn('tasks-project-edit-modal', modal_html)
        self.assertIn('tasks-issue-modal__dialog', modal_html)
        self.assertIn('tasks-issue-modal__header', modal_html)
        self.assertIn('tasks-issue-modal__body', modal_html)
        self.assertIn('tasks-issue-modal__footer', modal_html)
        self.assertIn('Parametry projektu', modal_html)
        self.assertIn('aria-label="Wybierz priorytet projektu"', modal_html)
        self.assertIn('data-inline-priority-icon', modal_html)
        self.assertIn('class="u-sr-only" for="project-rename-name"', modal_html)

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

    def test_create_project_leaves_code_blank_when_form_omits_it(self):
        first_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt bez kodu',
            'description': '',
            'icon': '',
        })
        second_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Drugi projekt bez kodu',
            'description': '',
            'icon': '',
        })

        project = TaskProject.objects.get(user=self.user, name='Projekt bez kodu')
        second_project = TaskProject.objects.get(user=self.user, name='Drugi projekt bez kodu')
        section = TaskSection.objects.get(project=project)

        self.assertRedirects(first_response, f"{reverse('tasks:tasks')}?project={project.id}")
        self.assertRedirects(second_response, f"{reverse('tasks:tasks')}?project={second_project.id}")
        self.assertEqual(project.code, '')
        self.assertEqual(second_project.code, '')
        self.assertEqual(section.code, '')
        self.assertEqual(section.full_code, '')
        self.assertEqual(project.icon, '')

    def test_create_project_rejects_duplicate_manual_code(self):
        TaskProject.objects.create(user=self.user, name='Projekt pierwszy', code='ABC')
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Projekt drugi',
            'description': '',
            'code': 'abc',
            'icon': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taki kod projektu już istnieje.')
        self.assertFalse(TaskProject.objects.filter(user=self.user, name='Projekt drugi').exists())

    def test_project_codes_are_unique_across_users_when_provided(self):
        other_user = get_user_model().objects.create_user(username='other-user', password='test-pass-123')
        TaskProject.objects.create(user=other_user, name='Projekt innej osoby', code='GLOBAL')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Mój projekt',
            'description': '',
            'code': 'global',
            'icon': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taki kod projektu już istnieje.')
        self.assertFalse(TaskProject.objects.filter(user=self.user, name='Mój projekt').exists())

    def test_project_codes_avoid_workspace_codes(self):
        from kanban.models import KanbanProject

        workspace = KanbanProject.objects.create(user=self.user, name='Przestrzeń robocza')
        KanbanProject.objects.filter(pk=workspace.pk).update(code='SPACE')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project',
            'name': 'Mój projekt',
            'description': '',
            'code': 'space',
            'icon': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taki kod projektu już istnieje.')
        self.assertFalse(TaskProject.objects.filter(user=self.user, name='Mój projekt').exists())

    def test_group_codes_keep_hierarchy_and_task_codes_use_task_id(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='P-8K3FQ2A9')
        first_section = TaskSection.objects.create(project=project, title='Frontend', code='FE')
        second_section = TaskSection.objects.create(project=project, title='Backend', code='BE')
        first_task = Task.objects.create(user=self.user, section=first_section, title='Pierwsze zadanie')
        second_task = Task.objects.create(user=self.user, section=first_section, title='Drugie zadanie')
        other_group_task = Task.objects.create(user=self.user, section=second_section, title='Zadanie backendowe')

        self.assertEqual(first_section.code, 'FE')
        self.assertEqual(second_section.code, 'BE')
        self.assertEqual(first_section.full_code, f'{project.code}/FE')
        self.assertEqual(first_task.code, '1')
        self.assertEqual(second_task.code, '2')
        self.assertEqual(other_group_task.code, '3')
        self.assertEqual(first_task.full_code, '1')
        self.assertEqual(other_group_task.full_code, '3')

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
            responsible_user=self.user,
        )
        other_user = get_user_model().objects.create_user(username='project-note-other', password='test-pass-123')
        TaskProjectNote.objects.create(project=project, author=self.user, message='Moja notatka projektu')
        TaskProjectNote.objects.create(project=project, author=other_user, message='Cudza notatka projektu')
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
        self.assertContains(response, 'FIRMA')
        self.assertContains(response, 'ODPOWIEDZIALNY')
        self.assertContains(response, 'STATUS')
        self.assertContains(response, 'ETAP')
        self.assertContains(response, 'KONDYCJA')
        self.assertContains(response, 'POSTĘP')
        self.assertContains(response, 'START')
        self.assertContains(response, 'TERMIN')
        self.assertContains(response, 'BUDŻET')
        self.assertContains(response, 'ŹRÓDŁO')
        self.assertContains(response, 'ZADANIA')
        self.assertContains(response, 'PRIORYTET')
        self.assertContains(response, 'OSTATNIA AKTYWNOŚĆ')
        self.assertNotContains(response, 'KLIENT / FIRMA')
        self.assertNotContains(response, 'ODPOWIEDZIALNY ZA PROJEKT')
        self.assertContains(response, 'aria-label="Edytuj projekt"')
        self.assertContains(response, 'aria-label="Informacje o projekcie"')
        self.assertContains(response, 'aria-label="Notatki projektu"')
        self.assertContains(response, 'Informacje o projekcie')
        self.assertContains(response, 'id="info-selected-project-menu-btn"')
        self.assertContains(response, 'id="notes-selected-project-menu-btn"')
        self.assertContains(response, 'data-open-project-info', count=4)
        self.assertContains(response, 'data-lucide="file-text"')
        self.assertContains(response, 'data-open-project-notes', count=4)
        self.assertContains(response, 'id="project-info-modal"')
        self.assertContains(response, 'id="project-notes-modal"')
        self.assertContains(response, 'name="action" value="add_project_note"')
        self.assertContains(response, 'name="action" value="edit_project_note"')
        self.assertContains(response, 'name="action" value="delete_project_note"')
        self.assertContains(response, 'data-project-notes-message')
        self.assertContains(response, 'tasks-project-notes-list')
        self.assertContains(response, 'tasks-project-notes-compose__input')
        self.assertContains(response, 'tasks-project-note--owned')
        self.assertNotContains(response, 'tasks-project-note--mine')
        self.assertContains(response, 'Moja notatka projektu')
        self.assertContains(response, 'Cudza notatka projektu')
        self.assertContains(response, 'data-project-pagination')
        self.assertContains(response, 'data-project-page-size')
        self.assertContains(response, 'data-project-page-prev')
        self.assertContains(response, 'data-project-page-next')
        for page_size in (10, 25, 50, 100, 150, 200):
            self.assertContains(response, f'<option value="{page_size}"')
        self.assertNotContains(response, '<option value="110"')
        content = response.content.decode()
        expected_columns = [
            'data-column="action" aria-label="Edytuj projekt"',
            'data-column="info" aria-label="Informacje o projekcie"',
            'data-column="notes" aria-label="Notatki projektu"',
            'data-column="project_code">KOD PROJEKTU',
            'data-column="project">PROJEKT',
            'data-column="company">FIRMA',
            'data-column="responsible_user">ODPOWIEDZIALNY',
            'data-column="project_status">STATUS',
            'data-column="stage">ETAP',
            'data-column="health">KONDYCJA',
            'data-column="description">OPIS',
            'data-column="progress">POSTĘP',
            'data-column="start_at">START',
            'data-column="due_at">TERMIN',
            'data-column="budget">BUDŻET',
            'data-column="source">ŹRÓDŁO',
            'data-column="tasks_count">ZADANIA',
            'data-column="priority">PRIORYTET',
            'data-column="last_activity">OSTATNIA AKTYWNOŚĆ',
            'data-column="created_at">DATA UTWORZENIA',
        ]
        column_positions = [content.index(column) for column in expected_columns]
        self.assertEqual(column_positions, sorted(column_positions))
        self.assertEqual(content.count('data-project-note-edit-toggle'), 1)
        self.assertEqual(content.count('name="action" value="delete_project_note"'), 1)
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
        self.assertContains(response, f'data-project-responsible-user-id="{self.user.id}"')
        self.assertContains(response, 'DATA UTWORZENIA')
        self.assertContains(response, '07.06.2026')
        self.assertNotContains(response, '7 cze')
        self.assertContains(response, 'Brak osoby')

    def test_projects_view_query_count_does_not_grow_with_task_volume(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt')
        section = TaskSection.objects.create(project=project, title='Plan')
        Task.objects.create(user=self.user, section=section, title='Pierwsze zadanie')

        with CaptureQueriesContext(connection) as baseline_queries:
            response = self.client.get(reverse('tasks:tasks'))

        self.assertEqual(response.status_code, 200)

        for index in range(12):
            Task.objects.create(
                user=self.user,
                section=section,
                title=f'Dodatkowe zadanie {index}',
                status='closed' if index % 2 else 'new',
            )

        with CaptureQueriesContext(connection) as expanded_queries:
            response = self.client.get(reverse('tasks:tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(expanded_queries), len(baseline_queries) + 1)

    def test_paginated_status_groups_batch_status_counts(self):
        from tasks.views.tasks import _status_groups_for_tasks

        project = TaskProject.objects.create(user=self.user, name='Projekt')
        section = TaskSection.objects.create(project=project, title='Plan')
        for index, status in enumerate(('new', 'new', 'in_progress', 'closed'), start=1):
            Task.objects.create(
                user=self.user,
                section=section,
                title=f'Zadanie {index}',
                status=status,
            )

        request = RequestFactory().get(f"{reverse('tasks:tasks')}?view=all-tasks")
        request.user = self.user
        queryset = Task.objects.filter(user=self.user, parent__isnull=True).annotate(
            is_closed_sort=Case(
                When(status='closed', then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            tags_total=Count('tags', distinct=True),
            attachments_total=Count('attachments', distinct=True),
        ).order_by('is_closed_sort', 'task_id')

        with CaptureQueriesContext(connection) as queries:
            groups = _status_groups_for_tasks(
                queryset,
                self.user,
                request=request,
                base_url=reverse('tasks:tasks'),
                paginate=True,
            )

        sql_statements = [query['sql'] for query in queries]
        per_status_count_queries = [
            sql for sql in sql_statements
            if sql.startswith('SELECT COUNT') and '"tasks_task"."status" =' in sql
        ]
        grouped_status_count_queries = [
            sql for sql in sql_statements
            if sql.startswith('SELECT "tasks_task"."status"') and 'COUNT' in sql
        ]
        counts_by_status = {group['status']: group['count'] for group in groups}

        self.assertEqual(counts_by_status['new'], 2)
        self.assertEqual(counts_by_status['in_progress'], 1)
        self.assertEqual(counts_by_status['closed'], 1)
        self.assertEqual(per_status_count_queries, [])
        self.assertEqual(len(grouped_status_count_queries), 1)

    def test_projects_view_renders_only_server_side_window(self):
        for index in range(60):
            project = TaskProject.objects.create(
                user=self.user,
                name=f'Projekt {index:03d}',
                code=f'PRJ-{index:04d}-000',
            )
            TaskSection.objects.create(project=project, title='Plan')

        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-server-pagination="true"')
        self.assertContains(response, 'tasks-project-row tasks-directory-row', count=50)
        self.assertContains(response, 'Projekt 000')
        self.assertContains(response, 'Projekt 049')
        self.assertNotContains(response, 'Projekt 050')
        self.assertContains(response, 'data-project-page-next')
        self.assertContains(response, 'Pokazano 1-50 z 60 projektów')
        self.assertIn('data-project-page="1"', html)
        self.assertIn('data-project-page="2"', html)
        self.assertIn('aria-current="page">1</button>', html)
        self.assertIn('data-project-page-url="/tasks/?page_size=50&amp;page=2"', html)
        self.assertNotIn('&amp;after=', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?page_size=50&page=2")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-project-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-project-row tasks-directory-row', count=10)
        self.assertIn('Projekt 050', table_html)
        self.assertIn('Projekt 059', table_html)
        self.assertNotIn('Projekt 049', table_html)
        self.assertContains(response, 'Pokazano 51-60 z 60 projektów')
        self.assertIn('aria-current="page">2</button>', html)
        self.assertIn('data-project-page-url="/tasks/?page_size=50"', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?page_size=10")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-project-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-project-row tasks-directory-row', count=10)
        self.assertIn('Projekt 000', table_html)
        self.assertNotIn('Projekt 010', table_html)
        self.assertIn('data-project-page="6"', html)

    def test_all_groups_view_renders_only_server_side_window(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt grup', code='GRP')
        for index in range(60):
            TaskSection.objects.create(
                project=project,
                title=f'Grupa {index:03d}',
                order=index,
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-server-pagination="true"')
        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=50)
        self.assertIn('Grupa 000', table_html)
        self.assertIn('Grupa 049', table_html)
        self.assertNotIn('Grupa 050', table_html)
        self.assertContains(response, 'Na stronie')
        self.assertContains(response, 'grup')
        self.assertContains(response, 'Pokazano 1-50 z 60 grup')
        self.assertIn('data-project-page-url="/tasks/?view=all-groups&amp;page_size=50&amp;page=2"', html)
        self.assertIn('aria-current="page">1</button>', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups&page_size=50&page=2")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=10)
        self.assertIn('Grupa 050', table_html)
        self.assertIn('Grupa 059', table_html)
        self.assertNotIn('Grupa 049', table_html)
        self.assertContains(response, 'Pokazano 51-60 z 60 grup')
        self.assertIn('aria-current="page">2</button>', html)
        self.assertIn('data-project-page-url="/tasks/?view=all-groups&amp;page_size=50"', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups&page_size=10")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=10)
        self.assertIn('Grupa 000', table_html)
        self.assertNotIn('Grupa 010', table_html)
        self.assertIn('data-project-page="6"', html)

    def test_project_view_paginates_project_groups(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt z grupami', code='PZG')
        for index in range(60):
            TaskSection.objects.create(
                project=project,
                title=f'Grupa projektu {index:03d}',
                order=index,
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-server-pagination="true"')
        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=50)
        self.assertIn('Grupa projektu 000', table_html)
        self.assertIn('Grupa projektu 049', table_html)
        self.assertNotIn('Grupa projektu 050', table_html)
        self.assertContains(response, 'Na stronie')
        self.assertContains(response, 'grup')
        self.assertContains(response, 'Pokazano 1-50 z 60 grup')
        self.assertIn(
            f'data-project-page-url="/tasks/?project={project.id}&amp;page_size=50&amp;page=2"',
            html,
        )
        self.assertIn('aria-current="page">1</button>', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}&page_size=50&page=2")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=10)
        self.assertIn('Grupa projektu 050', table_html)
        self.assertIn('Grupa projektu 059', table_html)
        self.assertNotIn('Grupa projektu 049', table_html)
        self.assertContains(response, 'Pokazano 51-60 z 60 grup')
        self.assertIn('aria-current="page">2</button>', html)
        self.assertIn(
            f'data-project-page-url="/tasks/?project={project.id}&amp;page_size=50"',
            html,
        )

        response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}&page_size=10")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-section-row tasks-directory-row', count=10)
        self.assertIn('Grupa projektu 000', table_html)
        self.assertNotIn('Grupa projektu 010', table_html)
        self.assertIn('data-project-page="6"', html)

    def test_all_tasks_view_paginates_each_status_independently(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt zadań', code='TSK')
        section = TaskSection.objects.create(project=project, title='Plan')
        for index in range(60):
            Task.objects.create(
                user=self.user,
                section=section,
                title=f'Nowe zadanie {index:03d}',
                status='new',
            )
        for index in range(12):
            Task.objects.create(
                user=self.user,
                section=section,
                title=f'Realizowane zadanie {index:03d}',
                status='in_progress',
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-tasks")
        html = response.content.decode()
        new_start = html.index('id="all-tasks-new"')
        new_end = html.index('</section>', new_start)
        new_html = html[new_start:new_end]
        in_progress_start = html.index('id="all-tasks-in_progress"')
        in_progress_end = html.index('</section>', in_progress_start)
        in_progress_html = html[in_progress_start:in_progress_end]

        self.assertContains(
            response,
            'class="tasks-project-pagination tasks-status-pagination" data-task-status-pagination',
            count=2,
        )
        self.assertContains(response, 'task-row tasks-issue-row', count=37)
        self.assertIn('Nowe zadanie 000', new_html)
        self.assertIn('Nowe zadanie 024', new_html)
        self.assertNotIn('Nowe zadanie 025', new_html)
        self.assertIn('Realizowane zadanie 011', in_progress_html)
        self.assertContains(response, 'Pokazano 1-25 z 60 zadań')
        self.assertContains(response, 'Pokazano 1-12 z 12 zadań')
        self.assertIn(
            'data-task-status-page-url="/tasks/?view=all-tasks&amp;task_new_page_size=25&amp;task_new_page=2"',
            html,
        )
        self.assertIn('data-task-status-page="2"', html)

        response = self.client.get(
            f"{reverse('tasks:tasks')}?view=all-tasks&task_new_page_size=50&task_new_page=2"
        )
        html = response.content.decode()
        new_start = html.index('id="all-tasks-new"')
        new_end = html.index('</section>', new_start)
        new_html = html[new_start:new_end]
        in_progress_start = html.index('id="all-tasks-in_progress"')
        in_progress_end = html.index('</section>', in_progress_start)
        in_progress_html = html[in_progress_start:in_progress_end]

        self.assertContains(response, 'task-row tasks-issue-row', count=22)
        self.assertIn('Nowe zadanie 050', new_html)
        self.assertIn('Nowe zadanie 059', new_html)
        self.assertNotIn('Nowe zadanie 049', new_html)
        self.assertIn('Realizowane zadanie 011', in_progress_html)
        self.assertContains(response, 'Pokazano 51-60 z 60 zadań')
        self.assertIn('aria-current="page">2</button>', html)
        self.assertIn(
            'data-task-status-page-url="/tasks/?view=all-tasks&amp;task_new_page_size=50"',
            html,
        )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-tasks&task_new_page_size=10")
        html = response.content.decode()
        new_start = html.index('id="all-tasks-new"')
        new_end = html.index('</section>', new_start)
        new_html = html[new_start:new_end]

        self.assertIn('Nowe zadanie 000', new_html)
        self.assertNotIn('Nowe zadanie 010', new_html)
        self.assertIn('data-task-status-page="6"', html)

    def test_all_tasks_view_renders_server_search_sort_and_filter_controls(self):
        company = Company.objects.create(owner=self.user, name='Alpha CRM')
        assignee = get_user_model().objects.create_user(
            username='alpha-owner',
            first_name='Adam',
            last_name='Nowak',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt Alpha', code='ALP')
        section = TaskSection.objects.create(project=project, title='Wdrożenie')
        Task.objects.create(
            user=self.user,
            section=section,
            title='Zadanie Alpha',
            company=company,
            assignee=assignee,
        )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-tasks")

        self.assertContains(response, 'data-server-directory-filters="true"')
        self.assertContains(response, 'data-project-sort-menu')
        self.assertContains(response, 'data-project-default-sort="task_id_asc"')
        self.assertContains(response, 'aria-label="Sortowanie zadań"')
        self.assertContains(response, 'id="filter-status"')
        self.assertContains(response, 'name="task_project"')
        self.assertContains(response, 'name="task_section"')
        self.assertContains(response, 'name="task_assignee"')
        self.assertContains(response, 'name="task_company"')
        self.assertContains(response, 'name="task_type"')
        self.assertContains(response, 'name="task_due"')
        self.assertContains(response, 'data-project-filter-menu="task_project"')
        self.assertContains(response, 'data-project-filter-menu="task_section"')
        self.assertContains(response, 'data-project-filter-menu="task_assignee"')
        self.assertContains(response, 'data-project-filter-menu="task_company"')
        self.assertContains(response, 'data-project-filter-menu="task_type"')
        self.assertContains(response, 'data-project-filter-menu="task_due"')
        self.assertContains(response, 'data-project-filter-search', count=4)
        self.assertContains(response, 'Szukaj projektu')
        self.assertContains(response, 'Szukaj grupy')
        self.assertContains(response, 'Szukaj osoby')
        self.assertContains(response, 'Szukaj firmy')

    def test_all_tasks_view_filters_searches_sorts_and_preserves_status_pagination_params(self):
        company = Company.objects.create(owner=self.user, name='Alpha CRM')
        other_company = Company.objects.create(owner=self.user, name='Beta CRM')
        assignee = get_user_model().objects.create_user(
            username='alpha-assignee',
            first_name='Adam',
            last_name='Nowak',
            password='test-pass-123',
        )
        project = TaskProject.objects.create(user=self.user, name='Projekt Alpha', code='ALP')
        section = TaskSection.objects.create(project=project, title='Wdrożenie')
        due_at = timezone.now() - timedelta(days=1)
        for index in range(30):
            Task.objects.create(
                user=self.user,
                section=section,
                title=f'Alpha telefon {index:03d}',
                status='new',
                priority='high',
                task_type='call',
                due_at=due_at,
                company=company,
                assignee=assignee,
            )
        Task.objects.create(
            user=self.user,
            section=section,
            title='Alpha realizowane ukryte',
            status='in_progress',
            priority='high',
            task_type='call',
            due_at=due_at,
            company=company,
            assignee=assignee,
        )
        Task.objects.create(
            user=self.user,
            section=section,
            title='Beta ukryte',
            status='new',
            priority='high',
            task_type='call',
            due_at=due_at,
            company=other_company,
            assignee=assignee,
        )

        response = self.client.get(
            f"{reverse('tasks:tasks')}?view=all-tasks&q=Alpha&priority=high&status=new"
            f"&task_project={project.id}&task_section={section.id}&task_assignee={assignee.id}"
            f"&task_company={company.id}&task_type=call&task_due=overdue&sort=title_desc"
        )
        html = response.content.decode()
        new_start = html.index('id="all-tasks-new"')
        new_end = html.index('</section>', new_start)
        new_html = html[new_start:new_end]

        self.assertContains(response, 'task-row tasks-issue-row', count=25)
        self.assertIn('Alpha telefon 029', new_html)
        self.assertIn('Alpha telefon 005', new_html)
        self.assertNotIn('Alpha telefon 004', new_html)
        self.assertNotIn('Alpha realizowane ukryte', html)
        self.assertNotIn('Beta ukryte', html)
        self.assertIn('id="all-tasks-new"', html)
        self.assertNotIn('id="all-tasks-in_progress"', html)
        self.assertIn('task_new_page=2', html)
        self.assertIn('q=Alpha', html)
        self.assertIn('priority=high', html)
        self.assertIn('status=new', html)
        self.assertIn(f'task_project={project.id}', html)
        self.assertIn(f'task_section={section.id}', html)
        self.assertIn(f'task_assignee={assignee.id}', html)
        self.assertIn(f'task_company={company.id}', html)
        self.assertIn('task_type=call', html)
        self.assertIn('task_due=overdue', html)
        self.assertIn('sort=title_desc', html)
        self.assertContains(response, 'Projekt: Projekt Alpha')
        self.assertContains(response, 'Grupa: Wdrożenie (Projekt Alpha)')
        self.assertContains(response, 'Odpowiedzialny: Adam Nowak')
        self.assertContains(response, 'Firma: Alpha CRM')
        self.assertContains(response, 'Typ: Telefon')
        self.assertContains(response, 'Termin: Po terminie')

    def test_task_rows_render_only_task_title_in_title_cell(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt zadań', code='TSK')
        section = TaskSection.objects.create(project=project, title='Plan')
        company = Company.objects.create(owner=self.user, name='Netology')
        assignee = get_user_model().objects.create_user(
            username='assignee-user',
            first_name='Adam',
            last_name='Mickiewicz',
            password='test-pass-123',
        )
        task = Task.objects.create(
            user=self.user,
            section=section,
            title='Zadanie bez widocznego typu',
            company=company,
            assignee=assignee,
            is_billable=True,
        )

        response = self.client.get(reverse('tasks:task_group', args=[section.id]))
        html = response.content.decode()
        task_marker = f'data-task-id="{task.task_id}"'
        marker_index = html.index(task_marker)
        row_start = html.rfind('<article', 0, marker_index)
        row_end = html.index('</article>', row_start)
        row_html = html[row_start:row_end]

        self.assertIn('Zadanie bez widocznego typu', row_html)
        self.assertNotIn('<span>Ogólne</span>', row_html)
        self.assertNotIn('tasks-row-crm-meta', row_html)
        self.assertNotIn('<span>Netology</span>', row_html)
        self.assertNotIn('<span>Adam Mickiewicz</span>', row_html)
        self.assertNotIn('<span>Fakturowalne</span>', row_html)

    def test_group_task_view_uses_group_url_for_status_pagination(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt grupy', code='GRP')
        section = TaskSection.objects.create(project=project, title='Sprint')
        for index in range(55):
            Task.objects.create(
                user=self.user,
                section=section,
                title=f'Zadanie grupy {index:03d}',
                status='new',
            )

        group_url = reverse('tasks:task_group', args=[section.id])
        response = self.client.get(group_url)
        html = response.content.decode()

        self.assertContains(response, 'task-row tasks-issue-row', count=25)
        self.assertIn('Zadanie grupy 024', html)
        self.assertNotIn('Zadanie grupy 025', html)
        self.assertContains(response, 'Pokazano 1-25 z 55 zadań')
        self.assertIn(
            f'data-task-status-page-url="{group_url}?task_new_page_size=25&amp;task_new_page=2"',
            html,
        )

        response = self.client.get(f"{group_url}?task_new_page_size=50&task_new_page=2")
        html = response.content.decode()

        self.assertContains(response, 'task-row tasks-issue-row', count=5)
        self.assertIn('Zadanie grupy 050', html)
        self.assertIn('Zadanie grupy 054', html)
        self.assertNotIn('Zadanie grupy 049', html)
        self.assertContains(response, 'Pokazano 51-55 z 55 zadań')

    def test_project_create_modal_uses_large_task_style_layout(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'tasks-project-create-modal')
        self.assertContains(response, 'tasks-project-create-modal__body')
        self.assertContains(response, 'tasks-project-create-fields')
        self.assertContains(response, 'Utwórz projekt')

    def test_section_create_modal_uses_task_style_field_layout(self):
        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        modal_start = html.index('id="section-create-modal"')
        modal_end = html.index('id="section-rename-modal"', modal_start)
        modal_html = html[modal_start:modal_end]

        self.assertIn('id="section-create-form"', modal_html)
        self.assertIn('class="u-sr-only" id="section-create-parameters-title"', modal_html)
        expected_fields = [
            'tasks-section-create-field--kind',
            'tasks-section-create-field--status',
            'tasks-section-create-field--owner',
            'tasks-section-create-field--priority',
            'tasks-section-create-field--due',
            'tasks-section-create-field--wip',
        ]
        for field_class in expected_fields:
            self.assertIn(field_class, modal_html)
        self.assertIn('data-ancore-custom-select-search-placeholder="Szukaj osoby"', modal_html)

    def test_create_menu_uses_requested_item_order(self):
        response = self.client.get(reverse('tasks:tasks'))
        html = response.content.decode()
        menu_start = html.index('id="create-menu-panel"')
        menu_end = html.index('</div>', menu_start)
        menu_html = html[menu_start:menu_end]
        expected_items = ['Utwórz projekt', 'Utwórz grupę', 'Utwórz zadanie', 'Utwórz tag']

        self.assertEqual([menu_html.count(item) for item in expected_items], [1, 1, 1, 1])
        self.assertEqual(
            [menu_html.index(item) for item in expected_items],
            sorted(menu_html.index(item) for item in expected_items),
        )
        self.assertNotIn('Import', menu_html)

    def test_project_and_group_icon_pickers_are_not_rendered(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertNotContains(response, 'data-project-icon-picker')
        self.assertNotContains(response, 'Ikona projektu')
        self.assertNotContains(response, 'Ikona grupy')

    def test_projects_view_renders_column_manager(self):
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'data-directory-column-manager')
        self.assertContains(response, 'data-directory-column-manager-toggle')
        self.assertContains(response, 'data-directory-column-manager-list')
        self.assertContains(response, 'data-directory-column-manager-search')
        self.assertContains(response, 'data-directory-column-manager-save')
        self.assertContains(response, 'data-directory-column-manager-cancel')
        self.assertContains(response, 'Zarządzaj tabelą')

    def test_project_group_rows_do_not_render_group_type_label(self):
        company = Company.objects.create(owner=self.user, name='Acme CRM')
        project = TaskProject.objects.create(
            user=self.user,
            name='Projekt',
            code='PRJ',
            priority='high',
            due_at=date(2026, 7, 15),
            company=company,
        )
        section = TaskSection.objects.create(project=project, title='Frontend', description='Prace po stronie UI', code='FE')
        TaskSectionNote.objects.create(section=section, author=self.user, message='Moja notatka grupy')
        Task.objects.create(user=self.user, section=section, title='Zadanie ukończone', status='closed')
        Task.objects.create(user=self.user, section=section, title='Zadanie otwarte')

        response = self.client.get(f"{reverse('tasks:tasks')}?project={project.id}")

        self.assertNotContains(
            response,
            '<span class="status-indicator status-label-plain">Grupa</span>',
            html=True,
        )
        self.assertContains(response, 'tasks-project-sheet--selectable')
        self.assertContains(response, 'tasks-section-sheet')
        self.assertContains(response, 'data-directory-column-manager')
        self.assertContains(response, 'data-directory-column-manager-toggle')
        self.assertContains(response, 'Zarządzaj tabelą')
        self.assertContains(response, 'data-priority-filter-menu')
        self.assertNotContains(response, 'data-status-filter-menu')
        self.assertContains(response, 'KOD GRUPY')
        self.assertContains(response, 'STATUS')
        self.assertContains(response, 'TYP')
        self.assertContains(response, 'POSTĘP')
        self.assertContains(response, 'TERMIN')
        self.assertContains(response, 'LIMIT WIP')
        self.assertContains(response, 'ZADANIA')
        self.assertContains(response, 'PRIORYTET')
        self.assertContains(response, 'OSTATNIA AKTYWNOŚĆ')
        self.assertNotContains(response, 'KLIENT / FIRMA')
        self.assertContains(response, 'data-column="action"', count=2)
        self.assertContains(response, 'data-column="action" aria-label="Edytuj grupę"')
        self.assertContains(response, 'data-column="info"', count=2)
        self.assertContains(response, 'data-column="info" aria-label="Informacje o grupie"')
        self.assertContains(response, 'data-column="notes"', count=2)
        self.assertContains(response, 'data-column="notes" aria-label="Notatki grupy"')
        self.assertContains(response, 'data-open-section-info')
        self.assertContains(response, 'data-open-section-notes')
        self.assertContains(response, 'data-open-section-rename')
        self.assertContains(response, 'aria-label="Edytuj grupę Frontend"')
        self.assertContains(response, 'aria-label="Informacje o grupie Frontend"')
        self.assertContains(response, 'aria-label="Notatki grupy Frontend"')
        self.assertContains(response, 'id="section-notes-modal"')
        self.assertContains(response, 'name="action" value="add_section_note"')
        self.assertContains(response, 'name="action" value="edit_section_note"')
        self.assertContains(response, 'name="action" value="delete_section_note"')
        self.assertContains(response, 'Moja notatka grupy')
        self.assertContains(response, 'data-section-notes-message')
        self.assertContains(response, 'data-section-note-edit-toggle')
        self.assertContains(response, f'data-section-id="{section.id}"')
        content = response.content.decode()
        expected_columns = [
            'data-column="action" aria-label="Edytuj grupę"',
            'data-column="info" aria-label="Informacje o grupie"',
            'data-column="notes" aria-label="Notatki grupy"',
            'data-column="section">GRUPA',
            'data-column="project_code">KOD GRUPY',
            'data-column="section_status">STATUS',
            'data-column="section_kind">TYP',
            'data-column="description">OPIS',
            'data-column="progress">POSTĘP',
            'data-column="due_at">TERMIN',
            'data-column="wip_limit">LIMIT WIP',
            'data-column="tasks_count">ZADANIA',
            'data-column="priority">PRIORYTET',
            'data-column="last_activity">OSTATNIA AKTYWNOŚĆ',
            'data-column="created_at">DATA UTWORZENIA',
        ]
        column_positions = [content.index(column) for column in expected_columns]
        self.assertEqual(column_positions, sorted(column_positions))
        self.assertContains(response, 'data-column="project_code"', count=2)
        self.assertContains(response, section.full_code)
        self.assertNotContains(response, 'data-column="company"')
        self.assertContains(response, 'Prace po stronie UI')
        self.assertContains(response, '50%')
        self.assertContains(response, '1/2')
        self.assertContains(response, 'Wysoki')
        self.assertContains(response, '15.07.2026')
        self.assertContains(response, 'Acme CRM')
        self.assertNotContains(
            response,
            '<div class="tasks-directory-members-menu tasks-directory-sheet__cell tasks-project-sheet__cell" data-column="members" data-directory-members-menu>',
        )

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
        frontend = TaskSection.objects.create(project=first_project, title='Frontend', description='Prace po stronie UI', code='FE')
        TaskSectionNote.objects.create(section=frontend, author=self.user, message='Notatka Frontendu')
        TaskSection.objects.create(project=second_project, title='Backend', code='BE')
        Task.objects.create(user=self.user, section=frontend, title='Zadanie frontendowe')
        TaskSection.objects.filter(pk=frontend.pk).update(
            created_at=datetime(2026, 6, 7, 12, 0, tzinfo=datetime_timezone.utc)
        )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=all-groups")

        self.assertContains(response, 'Wszystkie grupy')
        self.assertContains(response, 'title="Dodaj grupę"')
        self.assertContains(response, 'data-open-section-create')
        self.assertContains(response, 'data-section-create-project-select')
        self.assertContains(response, 'data-ancore-custom-select-search-placeholder="Szukaj projektu"')
        self.assertContains(response, 'Wybierz projekt')
        self.assertContains(response, 'tasks-directory-header')
        self.assertContains(response, 'tasks-section-sheet')
        self.assertContains(response, 'tasks-all-groups-sheet')
        self.assertContains(response, 'data-directory-column-manager')
        self.assertContains(response, 'data-directory-column-manager-toggle')
        self.assertContains(response, 'KOD GRUPY')
        self.assertContains(response, 'POSTĘP')
        self.assertContains(response, 'TERMIN')
        self.assertContains(response, 'data-column="action"', count=3)
        self.assertContains(response, 'data-column="action" aria-label="Edytuj grupę"')
        self.assertContains(response, 'data-column="info"', count=3)
        self.assertContains(response, 'data-column="info" aria-label="Informacje o grupie"')
        self.assertContains(response, 'data-column="notes"', count=3)
        self.assertContains(response, 'data-column="notes" aria-label="Notatki grupy"')
        self.assertContains(response, 'data-open-section-info', count=2)
        self.assertContains(response, 'data-open-section-notes', count=2)
        self.assertContains(response, 'data-open-section-rename', count=2)
        self.assertContains(response, 'id="section-notes-modal"')
        self.assertContains(response, 'name="action" value="add_section_note"')
        self.assertContains(response, 'name="action" value="edit_section_note"')
        self.assertContains(response, 'name="action" value="delete_section_note"')
        self.assertContains(response, 'Notatka Frontendu')
        self.assertContains(response, f'data-section-id="{frontend.id}"')
        self.assertContains(response, 'data-column="priority"', count=3)
        self.assertContains(response, 'OSTATNIA AKTYWNOŚĆ')
        self.assertNotContains(response, 'WŁAŚCICIEL')
        content = response.content.decode()
        expected_columns = [
            'data-column="action" aria-label="Edytuj grupę"',
            'data-column="info" aria-label="Informacje o grupie"',
            'data-column="notes" aria-label="Notatki grupy"',
            'data-column="section">GRUPA',
            'data-column="project_code">KOD GRUPY',
            'data-column="description">OPIS',
            'data-column="progress">POSTĘP',
            'data-column="due_at">TERMIN',
            'data-column="tasks_count">ZADANIA',
            'data-column="priority">PRIORYTET',
            'data-column="last_activity">OSTATNIA AKTYWNOŚĆ',
            'data-column="project_name">PROJEKT',
            'data-column="created_at">DATA UTWORZENIA',
        ]
        column_positions = [content.index(column) for column in expected_columns]
        self.assertEqual(column_positions, sorted(column_positions))
        self.assertContains(response, 'data-column="project_code"', count=3)
        self.assertContains(response, 'data-column="progress"', count=3)
        self.assertContains(response, 'data-column="project_name"', count=3)
        self.assertContains(response, 'ODPOWIEDZIALNY ZA GRUPĘ')
        self.assertContains(response, 'DATA UTWORZENIA')
        self.assertContains(response, 'Frontend')
        self.assertContains(response, frontend.full_code)
        self.assertContains(response, 'Prace po stronie UI')
        self.assertContains(response, 'Backend')
        self.assertContains(response, 'Drugi projekt')
        self.assertContains(response, first_project.code)
        self.assertContains(response, second_project.code)
        self.assertContains(response, '0/1')
        self.assertContains(response, '0/0')
        self.assertContains(response, '0%')
        self.assertContains(response, 'Brak terminu')
        self.assertContains(response, 'Brak')
        self.assertContains(response, 'Pracownik', count=2)
        self.assertNotContains(
            response,
            '<div class="tasks-directory-members-menu tasks-directory-sheet__cell tasks-project-sheet__cell" data-column="members" data-directory-members-menu>',
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
        self.assertContains(response, 'aria-label="Zaznacz projekt Projekt"')
        self.assertNotContains(response, 'Moje grupy')

    def test_tags_view_lists_tags(self):
        frontend = TaskTag.objects.create(
            user=self.user,
            name='Frontend',
            description='Prace po stronie UI',
            category='area',
            color='#1d4ed8',
            icon='flag',
            priority='high',
            scope='projects',
            owner_label='IT',
            status='active',
            usage_notes='Używaj przy pracach interfejsu.',
            automation_rules='Dodaj przy kanale frontend.',
        )
        backend = TaskTag.objects.create(user=self.user, name='Backend')
        frontend.related_tags.add(backend)
        TaskTagNote.objects.create(tag=frontend, author=self.user, message='Moja notatka tagu')
        TaskTag.objects.filter(pk=frontend.pk).update(
            created_at=datetime(2026, 6, 7, 12, 0, tzinfo=datetime_timezone.utc)
        )
        project = TaskProject.objects.create(user=self.user, name='Pierwszy projekt', code='ONE')
        section = TaskSection.objects.create(project=project, title='Grupa')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie frontendowe')
        task.tags.add(frontend)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags")
        html = response.content.decode()

        self.assertContains(response, 'Tagi')
        self.assertContains(response, 'tasks-spreadsheet-sheet')
        self.assertContains(response, 'KOD TAGU')
        self.assertContains(response, 'NAZWA TAGU')
        self.assertContains(response, 'data-directory-column-manager')
        self.assertContains(response, 'data-directory-column-manager-toggle')
        self.assertContains(response, 'data-directory-column-manager-list')
        self.assertContains(response, 'data-directory-column-manager-search')
        self.assertContains(response, 'data-directory-column-manager-save')
        self.assertContains(response, 'data-directory-column-manager-cancel')
        self.assertContains(response, 'Zarządzaj tabelą')
        self.assertContains(response, 'data-ancore-custom-select-search-placeholder="Szukaj tagów"')
        self.assertContains(response, 'data-column-label="Edytuj"')
        self.assertContains(response, 'data-column-label="Informacje"')
        self.assertContains(response, 'data-column-label="Notatki"')
        expected_columns = [
            'data-column="action" aria-label="Edytuj tag"',
            'data-column="info" aria-label="Informacje o tagu"',
            'data-column="notes" aria-label="Notatki tagu"',
            'data-column="tag_name">NAZWA TAGU',
            'data-column="tag_code">KOD TAGU',
            'data-column="tag_type">TYP',
            'data-column="tag_visual">KOLOR / IKONA',
            'data-column="priority">PRIORYTET',
            'data-column="scope">ZAKRES',
            'data-column="owner">WŁAŚCICIEL',
            'data-column="status">STATUS',
            'data-column="description">OPIS',
            'data-column="usage_notes">UŻYCIE',
            'data-column="automation">AUTOMATYKA',
            'data-column="related_tags">POWIĄZANE',
            'data-column="task_count">ZADANIA',
            'data-column="created_at">DATA UTWORZENIA',
        ]
        column_positions = [html.index(column) for column in expected_columns]
        self.assertEqual(column_positions, sorted(column_positions))
        self.assertContains(response, 'data-column="action"', count=3)
        self.assertContains(response, 'data-column="action" aria-label="Edytuj tag"')
        self.assertContains(response, 'data-column="info"', count=3)
        self.assertContains(response, 'data-column="info" aria-label="Informacje o tagu"')
        self.assertContains(response, 'data-column="notes"', count=3)
        self.assertContains(response, 'data-column="notes" aria-label="Notatki tagu"')
        self.assertContains(response, 'tasks-directory-sheet__cell tasks-project-sheet__cell tasks-tag-sheet__cell" data-column="action"')
        self.assertContains(response, 'tasks-directory-sheet__cell tasks-project-sheet__cell tasks-tag-sheet__cell" data-column="info"')
        self.assertContains(response, 'tasks-directory-sheet__cell tasks-project-sheet__cell tasks-tag-sheet__cell" data-column="notes"')
        self.assertContains(response, 'tasks-project-sheet__action tasks-directory-sheet__cell tasks-project-sheet__cell tasks-tag-sheet__cell" data-column="action"')
        self.assertContains(response, 'tasks-project-sheet__info tasks-directory-sheet__cell tasks-project-sheet__cell tasks-tag-sheet__cell" data-column="info"')
        self.assertContains(response, 'tasks-project-sheet__notes tasks-directory-sheet__cell tasks-project-sheet__cell tasks-tag-sheet__cell" data-column="notes"')
        self.assertContains(response, 'data-open-tag-edit', count=2)
        self.assertContains(response, 'data-open-tag-info', count=2)
        self.assertContains(response, 'data-open-tag-notes', count=2)
        self.assertContains(response, 'aria-label="Edytuj tag Frontend"')
        self.assertContains(response, 'aria-label="Informacje o tagu Frontend"')
        self.assertContains(response, 'aria-label="Notatki tagu Frontend"')
        self.assertContains(response, 'id="tag-notes-modal"')
        self.assertContains(response, 'name="action" value="add_tag_note"')
        self.assertContains(response, 'name="action" value="edit_tag_note"')
        self.assertContains(response, 'name="action" value="delete_tag_note"')
        self.assertContains(response, 'Moja notatka tagu')
        self.assertContains(response, 'data-tag-notes-message')
        self.assertContains(response, 'data-tag-note-edit-toggle')
        self.assertContains(response, 'data-column="tag_code"', count=3)
        self.assertContains(response, 'data-column="tag_name"', count=3)
        frontend_row_start = html.index(f'data-tag-id="{frontend.id}"')
        self.assertLess(
            html.index('data-column="action"', frontend_row_start),
            html.index('data-column="info"', frontend_row_start),
        )
        self.assertLess(
            html.index('data-column="info"', frontend_row_start),
            html.index('data-column="notes"', frontend_row_start),
        )
        self.assertLess(
            html.index('data-column="notes"', frontend_row_start),
            html.index('data-column="tag_name"', frontend_row_start),
        )
        self.assertLess(
            html.index('data-column="tag_name"', frontend_row_start),
            html.index('data-column="tag_code"', frontend_row_start),
        )
        self.assertContains(response, 'Frontend')
        self.assertContains(response, 'Prace po stronie UI')
        self.assertContains(response, 'Obszar')
        self.assertContains(response, '#1d4ed8')
        self.assertContains(response, 'Flaga')
        self.assertContains(response, 'Wysoki')
        self.assertContains(response, 'Projekty')
        self.assertContains(response, 'IT')
        self.assertContains(response, 'Aktywny')
        self.assertContains(response, 'Używaj przy pracach interfejsu.')
        self.assertContains(response, 'Dodaj przy kanale frontend.')
        self.assertContains(response, 'Backend')
        self.assertContains(response, 'Brak opisu')
        self.assertContains(response, frontend.code)
        self.assertContains(response, backend.code)
        self.assertContains(response, '1 zadań')
        self.assertContains(response, '0 zadań')
        self.assertContains(response, '07.06.2026')
        self.assertNotContains(response, '7 cze')

    def test_tags_view_renders_only_server_side_window(self):
        for index in range(60):
            TaskTag.objects.create(
                user=self.user,
                name=f'Tag {index:03d}',
                description=f'Opis tagu {index:03d}',
            )

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-server-pagination="true"')
        self.assertContains(response, 'tasks-tag-sheet__row', count=50)
        self.assertIn('Tag 000', table_html)
        self.assertIn('Tag 049', table_html)
        self.assertNotIn('Tag 050', table_html)
        self.assertContains(response, 'Na stronie')
        self.assertContains(response, 'tagów')
        self.assertContains(response, 'Pokazano 1-50 z 60 tagów')
        self.assertIn('data-project-page-url="/tasks/?view=tags&amp;page_size=50&amp;page=2"', html)
        self.assertIn('aria-current="page">1</button>', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags&page_size=50&page=2")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-tag-sheet__row', count=10)
        self.assertIn('Tag 050', table_html)
        self.assertIn('Tag 059', table_html)
        self.assertNotIn('Tag 049', table_html)
        self.assertContains(response, 'Pokazano 51-60 z 60 tagów')
        self.assertIn('aria-current="page">2</button>', html)
        self.assertIn('data-project-page-url="/tasks/?view=tags&amp;page_size=50"', html)

        response = self.client.get(f"{reverse('tasks:tasks')}?view=tags&page_size=10")
        html = response.content.decode()
        table_start = html.index('class="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list')
        table_end = html.index('</section>', table_start)
        table_html = html[table_start:table_end]

        self.assertContains(response, 'tasks-tag-sheet__row', count=10)
        self.assertIn('Tag 000', table_html)
        self.assertNotIn('Tag 010', table_html)
        self.assertIn('data-project-page="6"', html)

    def test_tags_link_is_rendered(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        TaskSection.objects.create(project=project, title='Frontend')
        TaskTag.objects.create(user=self.user, name='Frontend')
        TaskTag.objects.create(user=self.user, name='Backend')

        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'Tagi')
        self.assertContains(response, 'href="/tasks/?view=tags"')

    def test_create_tag_from_tasks_page(self):
        related = TaskTag.objects.create(user=self.user, name='Backend')
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_tag',
            'name': 'Design',
            'description': 'Makiety i decyzje wizualne',
            'category': 'work_type',
            'color': '#22c55e',
            'icon': 'briefcase',
            'priority': 'medium',
            'scope': 'tasks',
            'owner_label': 'Design',
            'status': 'active',
            'usage_notes': 'Używać dla makiet i UI.',
            'automation_rules': 'Dodaj po imporcie briefu.',
            'related_tags': [related.id],
            'code': 'DES',
        })

        tag = TaskTag.objects.get(user=self.user, name='Design')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=tags")
        self.assertEqual(tag.description, 'Makiety i decyzje wizualne')
        self.assertEqual(tag.category, 'work_type')
        self.assertEqual(tag.color, '#22c55e')
        self.assertEqual(tag.icon, 'briefcase')
        self.assertEqual(tag.priority, 'medium')
        self.assertEqual(tag.scope, 'tasks')
        self.assertEqual(tag.owner_label, 'Design')
        self.assertEqual(tag.status, 'active')
        self.assertEqual(tag.usage_notes, 'Używać dla makiet i UI.')
        self.assertEqual(tag.automation_rules, 'Dodaj po imporcie briefu.')
        self.assertEqual(list(tag.related_tags.all()), [related])
        self.assertNotEqual(tag.code, 'DES')
        self.assertRegex(tag.code, r'^T-[0-9A-Z]{8}$')

    def test_create_tag_avoids_existing_base36_tag_code(self):
        TaskTag.objects.create(user=self.user, name='Design', code='T-COLLIDE1')

        with patch('tasks.models.secrets.choice', side_effect=list('COLLIDE1BACKEND1')):
            response = self.client.post(reverse('tasks:tasks'), {
                'action': 'create_tag',
                'name': 'Backend',
                'description': '',
            })

        tag = TaskTag.objects.get(user=self.user, name='Backend')

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=tags")
        self.assertEqual(tag.code, 'T-BACKEND1')

    def test_delete_tag_from_tasks_page(self):
        tag = TaskTag.objects.create(user=self.user, name='Design')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_tag',
            'tag_id': tag.id,
        })

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=tags")
        self.assertFalse(TaskTag.objects.filter(id=tag.id).exists())

    def test_tag_note_actions_add_edit_and_delete_own_notes(self):
        tag = TaskTag.objects.create(
            user=self.user,
            name='Design',
            description='Opis tagu',
            status='active',
        )
        old_code = tag.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'add_tag_note',
            'tag_id': tag.id,
            'message': '  Nowa notatka tagu  ',
        })

        tag.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        note = TaskTagNote.objects.get(tag=tag)
        self.assertEqual(tag.name, 'Design')
        self.assertEqual(tag.description, 'Opis tagu')
        self.assertEqual(tag.status, 'active')
        self.assertEqual(tag.code, old_code)
        self.assertEqual(note.author, self.user)
        self.assertEqual(note.message, 'Nowa notatka tagu')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_tag_note',
            'tag_id': tag.id,
            'note_id': note.id,
            'message': '  Poprawiona notatka tagu  ',
        })

        note.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(note.message, 'Poprawiona notatka tagu')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_tag_note',
            'tag_id': tag.id,
            'note_id': note.id,
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(TaskTagNote.objects.filter(id=note.id).exists())

    def test_tag_note_actions_only_allow_author_to_change_note(self):
        other_user = get_user_model().objects.create_user(username='tag-note-owner', password='test-pass-123')
        tag = TaskTag.objects.create(user=self.user, name='Design')
        note = TaskTagNote.objects.create(tag=tag, author=other_user, message='Cudza notatka tagu')

        edit_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_tag_note',
            'tag_id': tag.id,
            'note_id': note.id,
            'message': 'Nie moje',
        })
        delete_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_tag_note',
            'tag_id': tag.id,
            'note_id': note.id,
        })

        note.refresh_from_db()
        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(note.message, 'Cudza notatka tagu')

    def test_edit_tag_from_tasks_page(self):
        tag = TaskTag.objects.create(user=self.user, name='Design', description='Stary opis')
        related = TaskTag.objects.create(user=self.user, name='Backend')
        old_code = tag.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_tag',
            'tag_id': tag.id,
            'name': 'UI',
            'description': 'Nowy opis',
            'category': 'area',
            'color': '#0f766e',
            'icon': 'layers',
            'priority': 'high',
            'scope': 'projects',
            'owner_label': 'Produkt',
            'status': 'archived',
            'usage_notes': 'Stosować przy zmianach UI.',
            'automation_rules': 'Dodaj przy typie zadania UI.',
            'related_tags': [related.id],
            'code': 'NEW',
        })

        tag.refresh_from_db()

        self.assertRedirects(response, f"{reverse('tasks:tasks')}?view=tags")
        self.assertEqual(tag.name, 'UI')
        self.assertEqual(tag.description, 'Nowy opis')
        self.assertEqual(tag.category, 'area')
        self.assertEqual(tag.color, '#0f766e')
        self.assertEqual(tag.icon, 'layers')
        self.assertEqual(tag.priority, 'high')
        self.assertEqual(tag.scope, 'projects')
        self.assertEqual(tag.owner_label, 'Produkt')
        self.assertEqual(tag.status, 'archived')
        self.assertEqual(tag.usage_notes, 'Stosować przy zmianach UI.')
        self.assertEqual(tag.automation_rules, 'Dodaj przy typie zadania UI.')
        self.assertEqual(list(tag.related_tags.all()), [related])
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
        self.assertContains(project_response, 'id="info-selected-section-menu-btn"')
        self.assertContains(project_response, 'id="notes-selected-section-menu-btn"')
        self.assertContains(project_response, 'Informacje o grupie')
        self.assertContains(project_response, 'Notatki grupy')
        self.assertContains(all_tasks_response, 'id="delete-selected-task-menu-btn"')
        self.assertContains(all_tasks_response, 'id="edit-selected-task-menu-btn"')
        self.assertContains(my_tasks_response, 'id="delete-selected-task-menu-btn"')
        self.assertContains(my_tasks_response, 'id="edit-selected-task-menu-btn"')
        self.assertContains(projects_response, 'id="delete-selected-project-menu-btn"')
        self.assertContains(projects_response, 'class="tasks-project-delete-button tasks-project-delete-button--separated"')
        self.assertContains(projects_response, 'id="edit-selected-project-menu-btn"')
        self.assertContains(projects_response, 'id="edit-selected-project-bar-btn"')
        self.assertContains(projects_response, 'data-select-all-target="projects"')
        self.assertContains(projects_response, 'aria-label="Zaznacz projekt Projekt"')
        self.assertContains(groups_response, 'id="delete-selected-section-menu-btn"')
        self.assertContains(groups_response, 'id="edit-selected-section-menu-btn"')
        self.assertContains(groups_response, 'id="info-selected-section-menu-btn"')
        self.assertContains(groups_response, 'id="notes-selected-section-menu-btn"')
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

    def test_create_task_modal_places_tags_before_assignee(self):
        response = self.client.get(reverse('tasks:tasks'))
        content = response.content.decode()

        self.assertLess(
            content.index('tasks-issue-field--company'),
            content.index('tasks-issue-field--tags'),
        )
        self.assertLess(
            content.index('tasks-issue-field--tags'),
            content.index('tasks-issue-field--assignee'),
        )
        self.assertLess(
            content.index('tasks-issue-field--assignee'),
            content.index('tasks-issue-field--due'),
        )

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

    def test_create_task_modal_saves_split_estimated_time(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'title': 'Zadanie z estymacją',
            'section': section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'estimated_hours': '2',
            'estimated_minutes_part': '15',
        })

        task = Task.objects.get(user=self.user, title='Zadanie z estymacją')

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(task.estimated_minutes, 135)

    def test_create_task_modal_saves_single_estimated_time_field(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_task_modal',
            'project_id': project.id,
            'title': 'Zadanie z jednym polem estymacji',
            'section': section.id,
            'description': '',
            'priority': 'medium',
            'status': 'new',
            'estimated_duration': '2 godz. 15 min.',
        })

        task = Task.objects.get(user=self.user, title='Zadanie z jednym polem estymacji')

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(task.estimated_minutes, 135)

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

    def test_task_detail_sidebar_shows_task_id(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        response = self.client.get(reverse('tasks:view-task', args=[task.task_id]))
        content = response.content.decode()

        self.assertContains(response, '<span>ID zadania</span>', html=True)
        self.assertContains(
            response,
            f'<span class="tasks-issue-code__value" data-task-code-value>{task.code}</span>',
            html=True,
        )
        self.assertContains(response, f'data-task-code-copy="{task.code}"')
        self.assertNotContains(response, 'data-task-code-short')
        self.assertNotContains(response, 'data-task-code-full')
        self.assertNotContains(response, 'data-task-code-toggle')
        self.assertContains(response, 'data-lucide="copy"')
        self.assertLess(content.index('<label for="id_tags">Tagi</label>'), content.index('<span>ID zadania</span>'))
        self.assertLess(content.index('<span>ID zadania</span>'), content.index('<span>Utworzył</span>'))

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

    def test_task_detail_rejects_spoofed_attachment_content(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse('tasks:view-task', args=[task.task_id]), {
                'title': 'Zadanie',
                'parent': '',
                'section': section.id,
                'description': '',
                'priority': 'medium',
                'status': 'new',
                'time_spent_hours': '',
                'time_spent_minutes': '',
                'attachments': SimpleUploadedFile(
                    'payload.png',
                    b'<svg><script>alert(1)</script></svg>',
                    content_type='image/png',
                ),
            })

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Załącznik ma nieprawidłową zawartość.')
            self.assertFalse(TaskAttachment.objects.filter(task=task).exists())

    def test_task_attachment_download_requires_owner(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Frontend')
        task = Task.objects.create(user=self.user, section=section, title='Zadanie')
        other_user = get_user_model().objects.create_user(
            username='other-user',
            email='other@example.com',
            first_name='Other',
            last_name='User',
            password='test-pass-123',
        )

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            attachment = TaskAttachment.objects.create(
                task=task,
                file=SimpleUploadedFile('notatka.txt', b'tresc', content_type='text/plain'),
            )

            response = self.client.get(reverse('tasks:download_attachment', args=[attachment.id]))
            self.assertEqual(response.status_code, 200)
            self.assertIn('attachment;', response['Content-Disposition'])
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

            self.client.force_login(other_user)
            response = self.client.get(reverse('tasks:download_attachment', args=[attachment.id]))
            self.assertEqual(response.status_code, 404)

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

    def test_edit_project_updates_details_and_manual_code_without_changing_icon(self):
        company = Company.objects.create(owner=self.user, name='Firma projektowa')
        project = TaskProject.objects.create(user=self.user, name='Stara nazwa', description='Stary opis', code='OLD')

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

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(project.name, 'Nowa nazwa')
        self.assertEqual(project.description, 'Nowy opis')
        self.assertEqual(project.priority, 'medium')
        self.assertEqual(project.due_at, date(2026, 8, 20))
        self.assertEqual(project.company, company)
        self.assertEqual(project.icon, '')
        self.assertEqual(project.code, 'NEW')

    def test_project_note_actions_add_edit_and_delete_own_notes(self):
        project = TaskProject.objects.create(
            user=self.user,
            name='Projekt notatek',
            description='Opis projektu',
            code='NOTE',
            status='active',
        )
        old_code = project.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'add_project_note',
            'project_id': project.id,
            'message': '  Nowa notatka projektu  ',
        })

        project.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        note = TaskProjectNote.objects.get(project=project)
        self.assertEqual(project.name, 'Projekt notatek')
        self.assertEqual(project.description, 'Opis projektu')
        self.assertEqual(project.status, 'active')
        self.assertEqual(project.code, old_code)
        self.assertEqual(note.author, self.user)
        self.assertEqual(note.message, 'Nowa notatka projektu')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project_note',
            'project_id': project.id,
            'note_id': note.id,
            'message': '  Poprawiona notatka  ',
        })

        note.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(note.message, 'Poprawiona notatka')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_project_note',
            'project_id': project.id,
            'note_id': note.id,
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(TaskProjectNote.objects.filter(id=note.id).exists())

    def test_project_note_actions_only_allow_author_to_change_note(self):
        other_user = get_user_model().objects.create_user(username='note-owner', password='test-pass-123')
        project = TaskProject.objects.create(user=self.user, name='Projekt notatek', code='NOTE')
        note = TaskProjectNote.objects.create(project=project, author=other_user, message='Cudza notatka')

        edit_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project_note',
            'project_id': project.id,
            'note_id': note.id,
            'message': 'Nie moje',
        })
        delete_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_project_note',
            'project_id': project.id,
            'note_id': note.id,
        })

        note.refresh_from_db()
        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(note.message, 'Cudza notatka')

    def test_section_note_actions_add_edit_and_delete_own_notes(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt grup', code='GRP')
        section = TaskSection.objects.create(
            project=project,
            title='Grupa notatek',
            description='Opis grupy',
            status='open',
        )
        old_code = section.code

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'add_section_note',
            'section_id': section.id,
            'message': '  Nowa notatka grupy  ',
        })

        section.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        note = TaskSectionNote.objects.get(section=section)
        self.assertEqual(section.title, 'Grupa notatek')
        self.assertEqual(section.description, 'Opis grupy')
        self.assertEqual(section.status, 'open')
        self.assertEqual(section.code, old_code)
        self.assertEqual(note.author, self.user)
        self.assertEqual(note.message, 'Nowa notatka grupy')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_section_note',
            'section_id': section.id,
            'note_id': note.id,
            'message': '  Poprawiona notatka grupy  ',
        })

        note.refresh_from_db()
        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(note.message, 'Poprawiona notatka grupy')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_section_note',
            'section_id': section.id,
            'note_id': note.id,
        })

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertFalse(TaskSectionNote.objects.filter(id=note.id).exists())

    def test_section_note_actions_only_allow_author_to_change_note(self):
        other_user = get_user_model().objects.create_user(username='section-note-owner', password='test-pass-123')
        project = TaskProject.objects.create(user=self.user, name='Projekt grup', code='GRP')
        section = TaskSection.objects.create(project=project, title='Grupa')
        note = TaskSectionNote.objects.create(section=section, author=other_user, message='Cudza notatka grupy')

        edit_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_section_note',
            'section_id': section.id,
            'note_id': note.id,
            'message': 'Nie moje',
        })
        delete_response = self.client.post(reverse('tasks:tasks'), {
            'action': 'delete_section_note',
            'section_id': section.id,
            'note_id': note.id,
        })

        note.refresh_from_db()
        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(note.message, 'Cudza notatka grupy')

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

        self.assertRedirects(response, reverse('tasks:tasks'))
        self.assertEqual(project.icon, 'rocket')

    def test_edit_project_rejects_duplicate_posted_code(self):
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

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taki kod projektu już istnieje.')
        self.assertEqual(project.code, old_code)

    def test_create_section_saves_description(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_section',
            'project_id': project.id,
            'title': 'Frontend',
            'description': 'Prace nad widokami',
            'code': 'fe',
            'priority': 'high',
            'icon': 'star',
        })

        section = TaskSection.objects.get(project=project, title='Frontend')

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(section.description, 'Prace nad widokami')
        self.assertEqual(section.code, 'FE')
        self.assertEqual(section.priority, 'high')
        self.assertEqual(section.icon, '')

    def test_edit_section_updates_description_priority_and_code(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend', description='Stary opis', code='BE', priority='low')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_section',
            'section_id': section.id,
            'title': 'API',
            'description': 'Nowy opis',
            'code': 'api',
            'priority': 'urgent',
            'icon': '',
        })

        section.refresh_from_db()

        self.assertRedirects(response, reverse('tasks:task_group', args=[section.id]))
        self.assertEqual(section.title, 'API')
        self.assertEqual(section.description, 'Nowy opis')
        self.assertEqual(section.code, 'API')
        self.assertEqual(section.priority, 'urgent')

    def test_edit_section_rejects_duplicate_code_in_same_project(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        TaskSection.objects.create(project=project, title='Frontend', code='FE')
        section = TaskSection.objects.create(project=project, title='Backend', code='BE')

        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_section',
            'section_id': section.id,
            'title': 'Backend',
            'description': '',
            'code': 'fe',
        })

        section.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taki kod grupy już istnieje w tym projekcie.')
        self.assertEqual(section.code, 'BE')

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

    def test_bulk_update_status_uses_batched_updates(self):
        project = TaskProject.objects.create(user=self.user, name='Projekt', code='PRJ')
        section = TaskSection.objects.create(project=project, title='Backend')
        tasks = [
            Task.objects.create(user=self.user, section=section, title=f'Zadanie {index}')
            for index in range(5)
        ]
        already_closed = Task.objects.create(
            user=self.user,
            section=section,
            title='Zamknięte wcześniej',
            status='closed',
        )
        original_completion_date = timezone.now() - timedelta(days=2)
        Task.objects.filter(pk=already_closed.pk).update(completion_date=original_completion_date)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.post(
                reverse('tasks:bulk_update_status'),
                data=json.dumps({
                    'task_ids': [task.task_id for task in [*tasks, already_closed]],
                    'status': 'closed',
                }),
                content_type='application/json',
            )

        already_closed.refresh_from_db()
        task_status_update_queries = [
            query['sql'] for query in queries
            if query['sql'].startswith('UPDATE "tasks_task" SET "status"')
        ]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['updated_count'], 6)
        self.assertLessEqual(len(task_status_update_queries), 2)
        self.assertEqual(already_closed.completion_date, original_completion_date)

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
