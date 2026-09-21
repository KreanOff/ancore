from django.contrib.auth import get_user_model
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connections
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone

from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Document, DocumentLibrary, Folder, WorkspaceDocument, WorkspaceDocumentFolder


class CatalogMoveTests:
    drive = False

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='move-owner', email='move-owner@example.test')
        self.other = get_user_model().objects.create_user(username='move-other', email='move-other@example.test')
        self.workspace = create_workplace_for_user(self.user, 'Przenoszenie')
        self.outside = create_workplace_for_user(self.user, 'Drugi Workspace')
        self.module = 'documents' if self.drive else 'office'
        self.base = scoped_workplace_app_path(self.workspace, self.module)
        self.folder_model = Folder if self.drive else WorkspaceDocumentFolder
        self.document_model = Document if self.drive else WorkspaceDocument
        self.scope = {'owner': self.user, 'workplace': self.workspace}
        self.library = DocumentLibrary.objects.create(**self.scope, name='Pierwszy') if self.drive else None
        self.defaults = {**self.scope, **({'library': self.library} if self.drive else {})}
        self.parent = self.folder_model.objects.create(**self.defaults, name='Materiały')
        self.child = self.folder_model.objects.create(**self.defaults, parent=self.parent, name='Zagnieżdżony')
        self.target = self.folder_model.objects.create(**self.defaults, name='Docelowy')
        self.item = self.document_model.objects.create(**self.defaults, title='Treść', filename='test.txt', file='original.txt')
        self.client.force_login(self.user)

    def move_url(self, item, base=None):
        prefix = 'folders/' if isinstance(item, self.folder_model) else ''
        return f'{base or self.base}{prefix}{item.pk}/move/'

    def move(self, item, target, base=None):
        return self.client.post(self.move_url(item, base), {'target': target}, headers={'X-Document-Move': 'true'})

    @property
    def root(self):
        return f'library:{self.library.pk}' if self.drive else 'root'

    def test_move_file_into_folder_and_back_with_plain_and_scoped_urls(self):
        original = (self.item.file.name, self.item.office_key, self.item.title)
        for base in [self.base, f'/{self.module}/']:
            self.client.get(self.base)
            for target, expected in [(f'folder:{self.child.pk}', self.child.pk), (self.root, None)]:
                response = self.move(self.item, target, base)
                self.assertEqual(response.status_code, 200)
                self.item.refresh_from_db()
                self.assertEqual(self.item.folder_id, expected)
                self.assertEqual((self.item.file.name, self.item.office_key, self.item.title), original)
        self.assertEqual(self.item.revision, 5)

    def test_move_folder_keeps_nested_contents_and_cannot_create_cycle(self):
        self.item.folder = self.child
        self.item.save()
        for folder in [self.parent, self.child]:
            self.assertEqual(self.move(self.parent, f'folder:{folder.pk}').status_code, 400)
        self.assertEqual(self.move(self.parent, f'folder:{self.target.pk}').status_code, 200)
        self.parent.refresh_from_db()
        self.child.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(self.parent.parent, self.target)
        self.assertEqual(self.child.parent, self.parent)
        self.assertEqual(self.item.folder, self.child)
        self.assertEqual(self.move(self.parent, self.root).status_code, 200)
        self.parent.refresh_from_db()
        self.assertIsNone(self.parent.parent_id)

    def test_duplicate_folder_name_is_case_insensitive_and_atomic(self):
        self.folder_model.objects.create(**self.defaults, parent=self.target, name=self.parent.name.upper())
        response = self.move(self.parent, f'folder:{self.target.pk}')
        self.assertEqual(response.status_code, 400)
        self.assertIn('już istnieje', response.json()['error'])
        self.parent.refresh_from_db()
        self.assertIsNone(self.parent.parent_id)

    def test_sources_and_destinations_require_owner_and_workspace(self):
        for index, overrides in enumerate([{'owner': self.other}, {'workplace': self.outside}]):
            hidden_folder = self.folder_model.objects.create(**{**self.defaults, **overrides}, name=f'Ukryty {index}')
            hidden_item = self.document_model.objects.create(**{**self.defaults, **overrides}, title='Ukryty')
            for source in [hidden_folder, hidden_item]:
                self.assertEqual(self.move(source, self.root).status_code, 404)
            self.assertEqual(self.move(self.item, f'folder:{hidden_folder.pk}').status_code, 400)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.folder_id)

    def test_trash_is_not_movable(self):
        self.item.deleted_at = timezone.now()
        self.item.save()
        self.assertEqual(self.move(self.item, f'folder:{self.target.pk}').status_code, 404)
        for display in ['list', 'grid']:
            response = self.client.get(self.base, {'view': 'trash', 'display': display})
            self.assertNotContains(response, 'data-document-drag ')
            self.assertNotContains(response, f'{self.item.pk}/move/')

    def test_move_requires_login_csrf_and_valid_destination(self):
        url = self.move_url(self.item)
        self.assertEqual(Client().post(url, {'target': self.root}).status_code, 302)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.user)
        self.assertEqual(csrf.post(url, {'target': self.root}).status_code, 403)
        for target in ['', 'folder:abc', 'folder:99999999999999999999999999', 'https://example.test/', 'root:2']:
            self.assertEqual(self.move(self.item, target).status_code, 400)
        self.assertEqual(self.client.put(url).status_code, 405)

    def test_move_dialog_and_noop_preserve_revision(self):
        response = self.client.get(self.move_url(self.parent), headers={'X-Document-Modal': 'true'})
        self.assertContains(response, 'data-document-dialog')
        self.assertContains(response, f'value="folder:{self.target.pk}"')
        self.assertNotContains(response, f'value="folder:{self.parent.pk}"')
        self.assertNotContains(response, f'value="folder:{self.child.pk}"')
        self.assertEqual(self.move(self.item, self.root).status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.revision, 1)
        response = self.client.post(self.move_url(self.item), {'target': f'folder:{self.target.pk}'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(self.base))

    def test_both_layouts_publish_scoped_move_and_drop_targets(self):
        params = {'library': self.library.pk} if self.drive else {}
        for display in ['list', 'grid']:
            response = self.client.get(self.base, {**params, 'display': display})
            self.assertContains(response, f'data-document-move-url="{self.move_url(self.item)}"')
            self.assertContains(response, f'data-document-drop="folder:{self.parent.pk}"')
            response = self.client.get(self.base, {**params, 'display': display, 'folder': self.child.pk})
            self.assertContains(response, f'data-document-drop="folder:{self.parent.pk}"')


class DriveMoveTests(CatalogMoveTests, TestCase):
    drive = True

    def test_cross_drive_folder_move_includes_nested_and_trashed_files(self):
        second = DocumentLibrary.objects.create(**self.scope, name='Drugi')
        self.item.folder = self.child
        self.item.save()
        trashed = Document.objects.create(**self.defaults, title='Kosz', folder=self.parent, deleted_at=timezone.now())
        response = self.move(self.parent, f'library:{second.pk}')
        self.assertEqual(response.status_code, 200)
        for item in [self.parent, self.child, self.item, trashed]:
            item.refresh_from_db()
            self.assertEqual(item.library, second)
        self.assertIsNotNone(trashed.deleted_at)
        self.assertEqual(self.item.file.name, 'original.txt')
        self.assertEqual(self.item.folder, self.child)
        self.target.refresh_from_db()
        self.assertEqual(self.target.library, self.library)

    def test_cross_drive_file_move_and_foreign_library_denied(self):
        second = DocumentLibrary.objects.create(**self.scope, name='Drugi')
        destination = Folder.objects.create(**self.scope, library=second, name='Cel')
        self.assertEqual(self.move(self.item, f'folder:{destination.pk}').status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual((self.item.library, self.item.folder), (second, destination))
        for overrides in [{'owner': self.other}, {'workplace': self.outside}]:
            foreign = DocumentLibrary.objects.create(**{**self.scope, **overrides}, name='Obcy')
            self.assertEqual(self.move(self.item, f'library:{foreign.pk}').status_code, 400)

    def test_inconsistent_subtree_is_rejected_without_modifying_foreign_data(self):
        second = DocumentLibrary.objects.create(**self.scope, name='Drugi')
        foreign = Document.objects.create(**{**self.defaults, 'owner': self.other}, title='Obcy', folder=self.child)
        self.assertEqual(self.move(self.parent, f'library:{second.pk}').status_code, 400)
        for item in [foreign, self.parent, self.child]:
            item.refresh_from_db()
            self.assertEqual(item.library, self.library)

    def test_cross_drive_conflict_leaves_whole_subtree_in_source_drive(self):
        second = DocumentLibrary.objects.create(**self.scope, name='Drugi')
        Folder.objects.create(**self.scope, library=second, name=self.parent.name.upper())
        self.item.folder = self.child
        self.item.save()
        self.assertEqual(self.move(self.parent, f'library:{second.pk}').status_code, 400)
        for item in [self.parent, self.child, self.item]:
            item.refresh_from_db()
            self.assertEqual(item.library, self.library)


class ConcurrentMoveTests(TransactionTestCase):
    def test_opposing_folder_moves_cannot_create_a_cycle(self):
        user = get_user_model().objects.create_user(username='concurrent-move', email='concurrent@example.test')
        workspace = create_workplace_for_user(user, 'Równoczesne przenoszenie')
        scope = {'owner': user, 'workplace': workspace}
        library = DocumentLibrary.objects.create(**scope, name='Dysk')
        for module, model, extra in [('documents', Folder, {'library': library})]:
            with self.subTest(module=module):
                first = model.objects.create(**scope, **extra, name='Pierwszy')
                second = model.objects.create(**scope, **extra, name='Drugi')
                base = scoped_workplace_app_path(workspace, module)
                clients = [Client(), Client()]
                for client in clients:
                    client.force_login(user)
                barrier = Barrier(2)

                def move(index):
                    try:
                        source, target = (first, second) if index == 0 else (second, first)
                        barrier.wait(timeout=10)
                        response = clients[index].post(f'{base}folders/{source.pk}/move/',
                            {'target': f'folder:{target.pk}'}, headers={'X-Document-Move': 'true'})
                        return response.status_code
                    finally:
                        connections.close_all()

                with ThreadPoolExecutor(max_workers=2) as pool:
                    self.assertEqual(sorted(pool.map(move, [0, 1])), [200, 400])
                first.refresh_from_db()
                second.refresh_from_db()
                self.assertFalse(first.parent_id == second.pk and second.parent_id == first.pk)
