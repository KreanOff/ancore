from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class LibraryMigrationTests(TransactionTestCase):
    def test_existing_content_keeps_its_files_hierarchy_tags_and_trash_status(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        other_apps = [node for node in executor.loader.graph.leaf_nodes() if node[0] != 'documents']
        previous = other_apps + [('documents', '0001_initial')]
        current = other_apps + [('documents', '0002_documentlibrary_and_more')]
        executor.migrate(previous)
        try:
            apps = executor.loader.project_state(previous).apps
            User = apps.get_model(settings.AUTH_USER_MODEL)
            Workplace = apps.get_model('workplaces', 'Workplace')
            Folder = apps.get_model('documents', 'Folder')
            Document = apps.get_model('documents', 'Document')
            Tag = apps.get_model('tasks', 'TaskTag')
            user = User.objects.create(username='migration-owner', email='migration@example.test')
            workspace = Workplace.objects.create(owner=user, name='Pierwszy', slug='pierwszy')
            second = Workplace.objects.create(owner=user, name='Drugi', slug='drugi')
            empty = Workplace.objects.create(owner=user, name='Pusty', slug='pusty')
            parent = Folder.objects.create(owner=user, workplace=workspace, name='Akademia WSB')
            child = Folder.objects.create(owner=user, workplace=workspace, parent=parent, name='Materiały')
            removed_at = timezone.now()
            document = Document.objects.create(owner=user, workplace=workspace, folder=child, title='Umowa',
                filename='Umowa.txt', file='existing/private-file.txt', file_size=18, is_starred=True, deleted_at=removed_at)
            tag = Tag.objects.create(user=user, workplace=workspace, name='Ważne')
            document.tags.add(tag)
            other = Document.objects.create(owner=user, workplace=second, title='Drugi plik', filename='Drugi.txt', file='existing/other.txt')
            executor = MigrationExecutor(connection)
            executor.migrate(current)
            apps = executor.loader.project_state(current).apps
            Document = apps.get_model('documents', 'Document')
            Folder = apps.get_model('documents', 'Folder')
            Library = apps.get_model('documents', 'DocumentLibrary')
            library = Library.objects.get(owner_id=user.pk, workplace_id=workspace.pk)
            migrated = Document.objects.get(pk=document.pk)
            self.assertEqual(library.name, 'Dokumenty')
            self.assertEqual(migrated.library_id, library.pk)
            self.assertEqual(migrated.folder_id, child.pk)
            self.assertEqual(migrated.file.name, 'existing/private-file.txt')
            self.assertEqual(migrated.file_size, 18)
            self.assertTrue(migrated.is_starred)
            self.assertEqual(migrated.deleted_at, removed_at)
            self.assertEqual(list(migrated.tags.values_list('pk', flat=True)), [tag.pk])
            self.assertEqual(Folder.objects.get(pk=child.pk).parent_id, parent.pk)
            self.assertEqual(set(Folder.objects.values_list('library_id', flat=True)), {library.pk})
            self.assertNotEqual(Document.objects.get(pk=other.pk).library_id, library.pk)
            self.assertFalse(Library.objects.filter(workplace_id=empty.pk).exists())
        finally:
            MigrationExecutor(connection).migrate(latest)
