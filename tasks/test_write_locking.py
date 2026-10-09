import importlib
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event, local
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import close_old_connections
from django.test import RequestFactory, TransactionTestCase
from django.urls import resolve

from core.task_numbering import lock_task_numbers
from tasks.models import Task, TaskProject, TaskSection
from tasks.project_templates import save_project_template
from workplaces.models import create_workplace_for_user

views = importlib.import_module('tasks.views.tasks')


class ProjectTemplateWriteLockTests(TransactionTestCase):
    def test_concurrent_template_creation_and_task_post_both_complete(self):
        owner = get_user_model().objects.create_user(username='template-lock-owner', email='template-lock@example.test')
        workspace = create_workplace_for_user(owner, 'Template locks')
        project = TaskProject.objects.create(user=owner, workplace=workspace, name='Source')
        section = TaskSection.objects.create(project=project, title='Group')
        task = Task.objects.create(user=owner, section=section, title='Source task')
        template = save_project_template(project, owner)
        template_ready, task_started, task_locked, release = Event(), Event(), Event(), Event()
        operation = local()
        original_populate = views.populate_project_from_template

        def paused_populate(*args, **kwargs):
            template_ready.set()
            if not release.wait(10):
                raise TimeoutError('Template creation was not released')
            return original_populate(*args, **kwargs)

        @contextmanager
        def observed_lock(*args, **kwargs):
            is_task = operation.name == 'task'
            if is_task:
                task_started.set()
            with lock_task_numbers(*args, **kwargs):
                if is_task:
                    task_locked.set()
                yield

        def run(name):
            operation.name = name
            close_old_connections()
            try:
                path = '/tasks/' if name == 'project' else f'/tasks/view-task/{task.task_id}/'
                data = {'action': 'create_project', 'name': 'Copied', 'template': template.pk} if name == 'project' else {
                    'action': 'create_subtask_modal', 'task_pk': task.pk, 'title': 'Child', 'status': 'new',
                }
                request = RequestFactory().post(path, data)
                request.user, request.workplace, request.session = owner, workspace, {}
                request._messages, request.resolver_match = FallbackStorage(request), resolve(path)
                return views.tasks(request).status_code if name == 'project' else views.view_task(request, task.task_id).status_code
            finally:
                close_old_connections()

        with patch.object(views, 'populate_project_from_template', paused_populate), patch.object(views, 'lock_task_numbers', observed_lock), ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(run, 'project')
            try:
                self.assertTrue(template_ready.wait(10))
                second = executor.submit(run, 'task')
                self.assertTrue(task_started.wait(10))
                self.assertFalse(task_locked.wait(0.3))
            finally:
                release.set()
            self.assertEqual(first.result(timeout=15), 302)
            self.assertEqual(second.result(timeout=15), 302)
        self.assertEqual(Task.objects.count(), 3)
