from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from tasks.models import TaskProject, TaskProjectMembership


class ProjectMembershipMigrationTests(TransactionTestCase):
    def test_existing_grants_survive_migration_as_members(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        owner = get_user_model().objects.create_user(username='migration-project-owner', email='migration-owner@project.test')
        person = get_user_model().objects.create_user(username='migration-project-member', email='migration-member@project.test')
        executor.migrate([('tasks', '0055_project_sharing')])
        apps = executor.loader.project_state([('tasks', '0055_project_sharing')]).apps
        Project = apps.get_model('tasks', 'TaskProject')
        project = Project.objects.create(user_id=owner.pk, name='Existing grant', visibility='private', private_owner_id=owner.pk)
        project.shared_with.add(person.pk)
        MigrationExecutor(connection).migrate(latest)
        membership = TaskProjectMembership.objects.get(project_id=project.pk, user_id=person.pk)
        self.assertEqual(membership.role, 'member')
        self.assertTrue(TaskProject.objects.get(pk=project.pk).shared_with.filter(pk=person.pk).exists())
