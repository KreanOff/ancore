import importlib
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import clear_url_caches

from documents.models import Document, DocumentLibrary, Folder
from kanban.models import Kanban, KanbanAttachment
from spaces.models import SpaceTask, SpaceTaskFile
from spaces.testing import make_space
from tasks.models import Task, TaskAttachment
from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class FileLifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='file-owner', email='files@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'File lifecycle')

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.storage = FileSystemStorage(directory.name)
        for model in (TaskAttachment, KanbanAttachment, Document):
            field = model._meta.get_field('file')
            self.addCleanup(setattr, field, 'storage', field.storage)
            field.storage = self.storage

    def files(self):
        attachments = []
        for model, attachment in ((Task, TaskAttachment), (Kanban, KanbanAttachment)):
            task = model.objects.create(user=self.owner, workplace=self.workspace, title='Test file')
            item = attachment(task=task)
            item.file.save('attachment.txt', ContentFile(b'Private attachment'))
            attachments.append(item)
        library = DocumentLibrary.objects.create(owner=self.owner, workplace=self.workspace, name='Test drive')
        folder = Folder.objects.create(owner=self.owner, workplace=self.workspace, library=library, name='Folder')
        item = Document(owner=self.owner, workplace=self.workspace, library=library, folder=folder,
                        title='Test file', filename='document.txt')
        item.file.save('document.txt', ContentFile(b'Private document'))
        return [*attachments, item]

    def test_deletion_removes_files_only_after_commit(self):
        for item in self.files():
            with self.subTest(model=type(item).__name__):
                name = item.file.name
                with self.captureOnCommitCallbacks(execute=True):
                    item.delete()
                    self.assertTrue(self.storage.exists(name))
                self.assertFalse(self.storage.exists(name))

    def test_rollback_preserves_records_and_files(self):
        for item in self.files():
            with self.subTest(model=type(item).__name__):
                pk, name = item.pk, item.file.name
                with self.captureOnCommitCallbacks(execute=True):
                    with self.assertRaises(RuntimeError), transaction.atomic():
                        item.delete()
                        raise RuntimeError('Rollback')
                self.assertTrue(type(item).objects.filter(pk=pk).exists())
                self.assertTrue(self.storage.exists(name))

    def test_workspace_cascade_removes_files_after_commit(self):
        items = self.files()
        with self.captureOnCommitCallbacks(execute=True):
            self.workspace.delete()
            self.assertTrue(all(self.storage.exists(item.file.name) for item in items))
        for item in items:
            self.assertFalse(type(item).objects.filter(pk=item.pk).exists())
            self.assertFalse(self.storage.exists(item.file.name))

    def test_workspace_cascade_rollback_preserves_files(self):
        items = self.files()
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError), transaction.atomic():
                self.workspace.delete()
                raise RuntimeError('Rollback')
        for item in items:
            self.assertTrue(type(item).objects.filter(pk=item.pk).exists())
            self.assertTrue(self.storage.exists(item.file.name))

    def test_attachment_download_still_requires_owner_and_workspace(self):
        items = self.files()[:2]
        self.client.force_login(self.owner)
        other_workspace = create_workplace_for_user(self.owner, 'Other files')
        for app, item in zip(('tasks', 'kanban'), items):
            suffix = f'attachments/{item.pk}/download/'
            response = self.client.get(scoped_workplace_app_path(self.workspace, app, suffix))
            self.assertEqual(response.status_code, 404)
            if app == 'kanban':
                continue
            space = make_space(user=self.owner, workplace=self.workspace, name='Imported files')
            task = SpaceTask.objects.create(space=space, created_by=self.owner, title='Imported task')
            work_item = task.work_item
            work_item.legacy_task = item.task
            work_item.save()
            SpaceTaskFile.objects.create(task=task, file=item.file.name, filename=item.filename, legacy_storage=True)
            with override_settings(MEDIA_ROOT=self.storage.location):
                response = self.client.get(scoped_workplace_app_path(self.workspace, app, suffix), follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            self.assertEqual(b''.join(response.streaming_content), b'Private attachment')
            self.assertEqual(self.client.get(scoped_workplace_app_path(other_workspace, app, suffix)).status_code, 404)
            self.assertEqual(Client().get(scoped_workplace_app_path(self.workspace, app, suffix)).status_code, 302)


class PublicMediaTests(SimpleTestCase):
    def test_only_public_photos_are_served_by_debug_routing(self):
        import ancore.urls
        with tempfile.TemporaryDirectory() as directory:
            for relative in ('task_attachments/secret.txt', 'kanban_attachments/secret.png',
                             'profile_photos/avatar.png', 'workplace_photos/logo.png', 'company_photos/logo.png'):
                path = Path(directory, relative)
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(b'Synthetic content')
            try:
                with override_settings(DEBUG=True, MEDIA_ROOT=directory, SECURE_SSL_REDIRECT=False):
                    importlib.reload(ancore.urls)
                    clear_url_caches()
                    for relative in ('task_attachments/secret.txt', 'kanban_attachments/secret.png',
                                     'profile_photos/../task_attachments/secret.txt',
                                     'profile_photos/%2e%2e/kanban_attachments/secret.png'):
                        with self.subTest(path=relative):
                            self.assertEqual(self.client.get('/media/' + relative).status_code, 404)
                    for relative in ('profile_photos/avatar.png', 'workplace_photos/logo.png', 'company_photos/logo.png'):
                        response = self.client.get('/media/' + relative)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(b''.join(response.streaming_content), b'Synthetic content')
            finally:
                importlib.reload(ancore.urls)
                clear_url_caches()
