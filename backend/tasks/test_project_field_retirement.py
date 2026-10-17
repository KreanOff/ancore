from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import TaskProject


class ProjectFieldRetirementTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='fields-owner', email='fields-owner@example.test')
        self.member = get_user_model().objects.create_user(username='fields-member', email='fields-member@example.test')
        self.workplace = create_workplace_for_user(self.owner, 'Pola projektu')
        WorkplaceMembership.objects.create(workplace=self.workplace, user=self.member)
        self.project = TaskProject.objects.create(
            user=self.owner, workplace=self.workplace, name='Historyczny projekt', visibility='public',
            status='legacy_qa', stage='legacy_stage', health='legacy_health',
            source='Polecenie klienta', due_at=date(2026, 10, 20),
        )
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.workplace.pk
        session.save()

    def test_removed_endpoint_and_old_actions_cannot_change_projects(self):
        for method in ['get', 'post']:
            response = getattr(self.client, method)('/settings/project-fields/', {
                'action': 'create_project_field_option', 'field_type': 'status',
                'project_id': self.project.pk, 'label': 'Nowa opcja', 'color': '#123456',
            })
            self.assertEqual(response.status_code, 404)
        for url in [reverse('settings'), scoped_workplace_app_path(self.workplace, 'tasks')]:
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, '/settings/project-fields/')
            self.assertNotContains(response, 'Wartości pól projektu')
            self.assertNotContains(response, 'Progi i kolory terminu')
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, 'legacy_qa')

    def test_retired_edit_cannot_change_old_values_or_source(self):
        payload = {
            'name': 'Zmieniona nazwa', 'visibility': 'public', 'status': self.project.status,
            'stage': self.project.stage, 'health': self.project.health,
            'source': 'Nowe źródło wpisane ręcznie', 'due_at': '2026-10-20',
        }
        for url in ['/tasks/', scoped_workplace_app_path(self.workplace, 'tasks')]:
            response = self.client.post(url, {'action': 'rename_project', 'project_id': self.project.pk, **payload})
            self.assertEqual(response.status_code, 409)
        self.project.refresh_from_db()
        self.assertEqual((self.project.status, self.project.stage, self.project.health),
                         ('legacy_qa', 'legacy_stage', 'legacy_health'))
        self.assertEqual(self.project.due_at, date(2026, 10, 20))
        self.assertEqual(self.project.source, 'Polecenie klienta')
        self.assertEqual(self.project.name, 'Historyczny projekt')

    def test_legacy_values_remain_stored_but_are_absent_from_active_catalog(self):
        self.client.force_login(self.member)
        response = self.client.get(scoped_workplace_app_path(self.workplace, 'tasks'),
                                   {'status': 'legacy_qa'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.project.name)
        self.assertNotContains(response, self.project.source)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, 'legacy_qa')
        self.assertEqual(self.client.get('/settings/project-fields/').status_code, 404)


class ProjectFieldRemovalMigrationTests(TransactionTestCase):
    def test_migration_removes_configuration_and_preserves_project_data(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [('tasks', '0062_task_favorites')]
        owner = get_user_model().objects.create_user(username='migration-owner', email='migration-owner@example.test')
        try:
            executor.migrate(previous)
            old_apps = executor.loader.project_state(previous).apps
            Project = old_apps.get_model('tasks', 'TaskProject')
            Option = old_apps.get_model('tasks', 'TaskProjectFieldOption')
            Rule = old_apps.get_model('tasks', 'TaskProjectDeadlineRule')
            project = Project.objects.create(user_id=owner.pk, name='Zachowany', status='custom_qa', source='Polecenie', due_at=date(2026, 10, 20), use_custom_deadline_rules=True)
            Option.objects.create(owner_id=owner.pk, field_type='status', value='custom_qa', label='Kontrola', color='#123456')
            Rule.objects.create(owner_id=owner.pk, project=project, days=5, color='#123456')
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            saved = TaskProject.objects.get(pk=project.pk)
            self.assertEqual((saved.name, saved.status, saved.source, saved.due_at),
                             ('Zachowany', 'custom_qa', 'Polecenie', date(2026, 10, 20)))
            tables = connection.introspection.table_names()
            self.assertNotIn('tasks_taskprojectfieldoption', tables)
            self.assertNotIn('tasks_taskprojectdeadlinerule', tables)
            with connection.cursor() as cursor:
                columns = [column.name for column in connection.introspection.get_table_description(cursor, 'tasks_taskproject')]
            self.assertNotIn('use_custom_deadline_rules', columns)
        finally:
            MigrationExecutor(connection).migrate(latest)
