from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class LibraryMigrationTests(TransactionTestCase):
    def test_drive_folder_stars_preserve_files_and_existing_office_stars(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [node for node in latest if node[0] != 'documents'] + [('documents', '0007_workspacedocumentfolder_is_starred')]
        executor.migrate(previous)
        try:
            apps = executor.loader.project_state(previous).apps
            user = apps.get_model(settings.AUTH_USER_MODEL).objects.create(username='drive-folder-migration', email='drive-folder-migration@example.test')
            workplace = apps.get_model('workplaces', 'Workplace').objects.create(owner=user, name='Dysk', slug='dysk')
            library = apps.get_model('documents', 'DocumentLibrary').objects.create(owner=user, workplace=workplace, name='Materiały')
            Folder = apps.get_model('documents', 'Folder')
            parent = Folder.objects.create(owner=user, workplace=workplace, library=library, name='Materiały')
            child = Folder.objects.create(owner=user, workplace=workplace, library=library, parent=parent, name='Podfolder')
            document = apps.get_model('documents', 'Document').objects.create(owner=user, workplace=workplace, library=library,
                folder=child, title='Plik', filename='Plik.txt', file='existing/private.txt', file_size=12, is_starred=True)
            office = apps.get_model('documents', 'WorkspaceDocumentFolder').objects.create(owner=user, workplace=workplace, name='Dokumenty', is_starred=True)
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            apps = executor.loader.project_state(latest).apps
            Folder = apps.get_model('documents', 'Folder')
            self.assertFalse(Folder.objects.filter(is_starred=True).exists())
            self.assertEqual(Folder.objects.get(pk=child.pk).parent_id, parent.pk)
            preserved = apps.get_model('documents', 'Document').objects.get(pk=document.pk)
            self.assertEqual((preserved.folder_id, preserved.library_id), (child.pk, library.pk))
            self.assertEqual((preserved.file.name, preserved.file_size), ('existing/private.txt', 12))
            self.assertTrue(preserved.is_starred)
            self.assertTrue(apps.get_model('documents', 'WorkspaceDocumentFolder').objects.get(pk=office.pk).is_starred)
        finally:
            MigrationExecutor(connection).migrate(latest)

    def test_folder_stars_default_to_false_and_preserve_existing_hierarchy(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [node for node in latest if node[0] != 'documents'] + [('documents', '0006_workspacedocument_tags')]
        executor.migrate(previous)
        try:
            apps = executor.loader.project_state(previous).apps
            user = apps.get_model(settings.AUTH_USER_MODEL).objects.create(username='folder-migration', email='folder-migration@example.test')
            workplace = apps.get_model('workplaces', 'Workplace').objects.create(owner=user, name='Foldery', slug='foldery')
            Folder = apps.get_model('documents', 'WorkspaceDocumentFolder')
            parent = Folder.objects.create(owner=user, workplace=workplace, name='Materiały')
            child = Folder.objects.create(owner=user, workplace=workplace, parent=parent, name='Podfolder')
            document = apps.get_model('documents', 'WorkspaceDocument').objects.create(
                owner=user, workplace=workplace, folder=child, title='Notatki', content='<p>Treść</p>', is_starred=True)
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            apps = executor.loader.project_state(latest).apps
            Folder = apps.get_model('documents', 'WorkspaceDocumentFolder')
            self.assertFalse(Folder.objects.filter(is_starred=True).exists())
            self.assertEqual(Folder.objects.get(pk=child.pk).parent_id, parent.pk)
            preserved = apps.get_model('documents', 'WorkspaceDocument').objects.get(pk=document.pk)
            self.assertEqual(preserved.folder_id, child.pk)
            self.assertEqual(preserved.content, '<p>Treść</p>')
            self.assertTrue(preserved.is_starred)
        finally:
            MigrationExecutor(connection).migrate(latest)

    def test_office_migration_keeps_drive_content_separate(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [node for node in latest if node[0] != 'documents'] + [('documents', '0003_documentlibrary_photo')]
        executor.migrate(previous)
        try:
            apps = executor.loader.project_state(previous).apps
            User = apps.get_model(settings.AUTH_USER_MODEL)
            Workplace = apps.get_model('workplaces', 'Workplace')
            Library = apps.get_model('documents', 'DocumentLibrary')
            Document = apps.get_model('documents', 'Document')
            user = User.objects.create(username='office-migration', email='office-migration@example.test')
            workplace = Workplace.objects.create(owner=user, name='Migracja', slug='migracja')
            library = Library.objects.create(owner=user, workplace=workplace, name='Istniejący dysk')
            document = Document.objects.create(owner=user, workplace=workplace, library=library, title='Oryginał',
                                              filename='Oryginał.txt', file='existing/original.txt', file_size=123)
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            apps = executor.loader.project_state(latest).apps
            preserved = apps.get_model('documents', 'Document').objects.get(pk=document.pk)
            self.assertEqual(preserved.library_id, library.pk)
            self.assertEqual(preserved.file.name, 'existing/original.txt')
            self.assertEqual(preserved.file_size, 123)
            self.assertFalse(apps.get_model('documents', 'WorkspaceDocument').objects.exists())
            self.assertFalse(apps.get_model('documents', 'WorkspaceDocumentFolder').objects.exists())
        finally:
            MigrationExecutor(connection).migrate(latest)

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
