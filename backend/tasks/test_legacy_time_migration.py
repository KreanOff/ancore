from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from tasks.models import Task, TaskProject, TaskSection, TaskWorkLog
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class LegacyTaskTimeMigrationTests(TransactionTestCase):
    def setUp(self):
        executor = MigrationExecutor(connection)
        self.latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(self.restore_schema)
        self.owner = get_user_model().objects.create_user(
            username='legacy-time-owner', email='legacy-time-owner@example.test',
        )
        self.team = create_workplace_for_user(self.owner, 'Legacy time team')
        project = TaskProject.objects.create(user=self.owner, workplace=self.team, name='Project')
        self.section = TaskSection.objects.create(project=project, title='Group')
        self.parent = Task.objects.create(user=self.owner, section=self.section, title='Parent')
        # Seed with current models before rolling back; later project fields
        # are intentionally absent from the historical schema under test.
        executor.migrate([('tasks', '0050_task_work_log')])
        self.HistoricalTask = executor.loader.project_state([('tasks', '0050_task_work_log')]).apps.get_model('tasks', 'Task')

    def restore_schema(self):
        # This column exists only in the simulated legacy test database.
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE tasks_task DROP COLUMN IF EXISTS logged_seconds')
        MigrationExecutor(connection).migrate(self.latest)

    def migrate_forward(self):
        MigrationExecutor(connection).migrate(self.latest)

    def test_fresh_database_does_not_gain_legacy_column(self):
        self.migrate_forward()
        with connection.cursor() as cursor:
            columns = connection.introspection.get_table_description(cursor, 'tasks_task')
        self.assertNotIn('logged_seconds', [column.name for column in columns])
        child = Task.objects.create(
            user=self.owner, section=self.section, parent=self.parent, title='Fresh child',
        )
        self.assertEqual(child.workplace, self.team)

    def test_legacy_database_preserves_time_and_allows_task_and_subtask_creation(self):
        started_at = timezone.now().replace(second=0, microsecond=0)
        entry = TaskWorkLog.objects.create(
            task=self.parent, author=self.owner, description='Existing work',
            started_at=started_at, ended_at=started_at + timedelta(minutes=45),
        )
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE tasks_task ADD COLUMN logged_seconds bigint NOT NULL DEFAULT 0')
            cursor.execute('ALTER TABLE tasks_task ALTER COLUMN logged_seconds DROP DEFAULT')
            cursor.execute('UPDATE tasks_task SET logged_seconds = 3600 WHERE id = %s', [self.parent.pk])

        # Reproduce the missing legacy default using fields from that schema.
        with self.assertRaisesMessage(IntegrityError, 'logged_seconds'), transaction.atomic():
            self.HistoricalTask.objects.create(user_id=self.owner.pk, workplace_id=self.team.pk,
                section_id=self.section.pk, task_id=2, code_number=2, title='Before repair')

        self.migrate_forward()
        imported_parent = self.parent
        project = TaskProject.objects.create(user=self.owner, workplace=self.team, name='Legacy project after migration')
        self.section = TaskSection.objects.create(project=project, title='Legacy group after migration')
        self.parent = Task.objects.create(user=self.owner, section=self.section, title='Legacy parent after migration')
        task = Task.objects.create(user=self.owner, section=self.section, title='After repair')
        member = get_user_model().objects.create_user(
            username='legacy-time-member', email='legacy-time-member@example.test',
        )
        WorkplaceMembership.objects.create(workplace=self.team, user=member, role='member')
        self.client.force_login(member)
        session = self.client.session
        session['active_workplace_id'] = self.team.pk
        session.save()

        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                suffix = f'view-task/{self.parent.task_id}/'
                url = (scoped_workplace_app_path(self.team, 'tasks', suffix)
                       if scoped else f'/tasks/{suffix}')
                title = f'Child {scoped}'
                response = self.client.post(url, {
                    'task_pk': self.parent.pk, 'action': 'create_subtask_modal',
                    'title': title, 'description': 'Child description', 'status': 'closed',
                })
                self.assertEqual(response.status_code, 302)
                child = self.parent.subtasks.get(title=title)
                self.assertEqual(child.user, self.owner)
                self.assertEqual(child.workplace, self.team)
                self.assertEqual(child.section, self.section)
                self.assertTrue(child.is_completed)
                self.assertIsNotNone(child.completion_date)
                self.assertFalse(child.work_logs.exists())
                activity = self.parent.activities.filter(action='subtask_created').latest('pk')
                self.assertEqual(activity.actor, member)
                self.assertEqual(activity.metadata['subtask_task_id'], child.task_id)
                self.assertContains(self.client.get(response.url, follow=True), title)

        with connection.cursor() as cursor:
            cursor.execute('SELECT id, logged_seconds FROM tasks_task ORDER BY id')
            values = dict(cursor.fetchall())
        self.assertEqual(values[imported_parent.pk], 3600)
        self.assertEqual(values[self.parent.pk], 0)
        self.assertEqual(values[task.pk], 0)
        for child in self.parent.subtasks.all():
            self.assertEqual(values[child.pk], 0)
        entry.refresh_from_db()
        self.assertEqual(entry.duration_minutes, 45)
        self.assertEqual(entry.description, 'Existing work')
        self.assertEqual(entry.author, self.owner)

        # A workspace member cannot create children under another workspace.
        other_team = create_workplace_for_user(self.owner, 'Other legacy team')
        other_task = Task.objects.create(user=self.owner, workplace=other_team, title='Elsewhere')
        url = scoped_workplace_app_path(self.team, 'tasks', f'view-task/{self.parent.task_id}/')
        response = self.client.post(url, {
            'task_pk': other_task.pk, 'action': 'create_subtask_modal',
            'title': 'Forbidden child', 'status': 'new',
        })
        self.assertEqual(response.status_code, 404)
        self.assertFalse(other_task.subtasks.exists())
