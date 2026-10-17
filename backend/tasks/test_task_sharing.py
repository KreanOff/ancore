"""Preserve historical task privacy and stable activity identities during migration."""

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from tasks.models import Task, TaskActivity


class TaskSharingMigrationTests(TransactionTestCase):
    def test_existing_tasks_keep_access_and_child_history_uses_stable_pk(self):
        executor=MigrationExecutor(connection);latest=executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda:MigrationExecutor(connection).migrate(latest))
        user=get_user_model().objects.create_user(username='task-migration',email='task-migration@task.test')
        executor.migrate([('tasks','0059_direct_sharing')])
        apps=executor.loader.project_state([('tasks','0059_direct_sharing')]).apps
        OldTask=apps.get_model('tasks','Task');Activity=apps.get_model('tasks','TaskActivity')
        parent=OldTask.objects.create(user_id=user.pk,title='Parent',task_id=1)
        child=OldTask.objects.create(user_id=user.pk,title='Child',parent=parent,task_id=2)
        event=Activity.objects.create(task=parent,action='subtask_created',metadata={'subtask_title':'Child','subtask_task_id':2})
        stale=Activity.objects.create(task=parent,action='subtask_created',metadata={'subtask_title':'Gone','subtask_task_id':3})
        MigrationExecutor(connection).migrate(latest)
        restored=Task.objects.get(pk=child.pk)
        self.assertEqual(restored.visibility,'public');self.assertIsNone(restored.private_owner_id)
        self.assertFalse(restored.memberships.exists())
        self.assertEqual(TaskActivity.objects.get(pk=event.pk).metadata['subtask_pk'],child.pk)
        self.assertNotIn('subtask_title',TaskActivity.objects.get(pk=stale.pk).metadata)
