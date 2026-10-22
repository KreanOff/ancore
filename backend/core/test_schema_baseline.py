"""The clean migration baseline installs only the current work system."""
from django.apps import apps
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TestCase
from django.urls import Resolver404, resolve


class CleanMigrationGraphTests(SimpleTestCase):
    def test_retired_apps_and_models_are_absent(self):
        self.assertFalse(apps.is_installed('kanban'))
        self.assertFalse(apps.is_installed('legacy.contacts'))
        self.assertEqual({model.__name__ for model in apps.get_app_config('tasks').get_models()},
                         {'TaskTag', 'TaskTagNote'})
        for model, field in [('Space', 'project'), ('WorkItem', 'legacy_task'), ('SpaceTaskFile', 'legacy_storage')]:
            self.assertNotIn(field, {f.name for f in apps.get_model('spaces', model)._meta.fields})

    def test_project_migrations_start_from_the_current_schema(self):
        loader = MigrationLoader(None)
        self.assertFalse({'contacts', 'kanban'} & {label for label, _ in loader.disk_migrations})
        project_labels = {'accounts', 'workplaces', 'spaces', 'tasks', 'dashboard', 'planner', 'documents', 'resources'}
        for (label, name), migration in loader.disk_migrations.items():
            if label in project_labels:
                with self.subTest(app=label, migration=name):
                    if name in {'0001_initial', '0002_initial'}:
                        self.assertTrue(migration.initial)
                        self.assertFalse(any(type(op).__name__ == 'RunPython' for op in migration.operations))

    def test_retired_routes_are_not_registered(self):
        for root in ('contacts', 'tasks', 'kanban'):
            for prefix in ('', '/workplaces/example'):
                for suffix in ('', 'new/', 'view-task/1/', 'attachments/1/download/'):
                    path = f'{prefix}/{root}/{suffix}'
                    with self.subTest(path=path), self.assertRaises(Resolver404):
                        resolve(path)


class CleanDatabaseSchemaTests(TestCase):
    def test_fresh_database_has_current_tables_and_no_retired_tables(self):
        tables = set(connection.introspection.table_names())
        self.assertTrue({'spaces_space', 'spaces_spacetask', 'spaces_workitem', 'tasks_tasktag'} <= tables)
        self.assertFalse({table for table in tables if table.startswith(('contacts_', 'kanban_'))})
        self.assertFalse({'tasks_task', 'tasks_taskproject', 'tasks_tasksection', 'spaces_legacykanbanlink',
                          'dashboard_objectfollow', 'dashboard_activityinterest', 'dashboard_taskreminder'} & tables)
