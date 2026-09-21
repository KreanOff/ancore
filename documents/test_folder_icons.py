from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .folder_stats import set_folder_summaries
from .models import Document, DocumentLibrary, Folder


class FolderIconTestsMixin:
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='folder-icons-owner', email='folder-icons-owner@example.test')
        cls.other = get_user_model().objects.create_user(username='folder-icons-other', email='folder-icons-other@example.test')
        cls.workspace = create_workplace_for_user(cls.user, 'Ikony folderów')
        cls.outside = create_workplace_for_user(cls.user, 'Drugi Workspace')
        cls.base = scoped_workplace_app_path(cls.workspace, cls.app)
        if cls.app == 'documents':
            cls.library = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workspace, name='Dysk')
            cls.other_library = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workspace, name='Inny dysk')

    def setUp(self):
        self.client.force_login(self.user)

    def folder(self, name, **overrides):
        defaults = {'owner': self.user, 'workplace': self.workspace, 'name': name}
        if self.app == 'documents':
            defaults['library'] = self.library
        return self.folder_model.objects.create(**{**defaults, **overrides})

    def document(self, folder, **overrides):
        defaults = {'owner': self.user, 'workplace': self.workspace, 'folder': folder,
                    'title': 'Dokument', 'filename': 'Dokument.txt', 'file_size': 0}
        if self.app == 'documents':
            defaults['library'] = self.library
        return self.document_model.objects.create(**{**defaults, **overrides})

    def response(self, base=None, **params):
        if self.app == 'documents':
            params.setdefault('library', self.library.pk)
        response = self.client.get(base or self.base, params, follow=True)
        self.assertEqual(response.status_code, 200)
        return response

    def test_icons_include_nested_and_zero_byte_files_but_exclude_trash_and_foreign_data(self):
        empty = self.folder('Katalog pusty')
        empty_tree = self.folder('Katalog z pustym podfolderem')
        self.folder('Pusty podfolder', parent=empty_tree)
        direct = self.folder('Katalog z plikiem')
        self.document(direct)
        nested = self.folder('Katalog z plikiem w podfolderze')
        child = self.folder('Poziom 1', parent=nested)
        grandchild = self.folder('Poziom 2', parent=child)
        self.document(grandchild)
        trashed = self.folder('Katalog z plikiem w koszu')
        self.document(trashed, deleted_at=timezone.now(), file_size=10)
        foreign = self.folder('Katalog z obcymi powiązaniami')
        self.document(foreign, owner=self.other, file_size=10)
        self.document(foreign, workplace=self.outside, file_size=10)
        inaccessible = self.folder('Obcy podfolder', parent=foreign, owner=self.other)
        self.document(inaccessible, file_size=10)
        if self.app == 'documents':
            self.document(foreign, library=self.other_library, file_size=10)
            cross_drive = self.folder('Obcy dysk', parent=foreign, library=self.other_library)
            self.document(cross_drive, library=self.other_library, file_size=10)
        expected = {empty.pk: False, empty_tree.pk: False, direct.pk: True,
                    nested.pk: True, trashed.pk: False, foreign.pk: False}
        for base in [self.base, f'/{self.app}/']:
            for display in ['list', 'grid']:
                for filters in [{}, {'q': 'Katalog'}]:
                    with self.subTest(base=base, display=display, filters=filters):
                        response = self.response(base, display=display, **filters)
                        actual = {row['item'].pk: row['item'].has_files for row in response.context['rows'] if row['kind'] == 'folder'}
                        self.assertEqual(actual, expected)
                        self.assertContains(response, 'documents-folder-icon--filled', count=2)
                        self.assertContains(response, 'documents-folder-icon--empty', count=4)

    def test_icon_updates_after_move_trash_and_restore(self):
        source = self.folder('Źródło')
        target = self.folder('Cel')
        item = self.document(source)

        def assert_icons(source_has_files, target_has_files):
            response = self.response(display='grid')
            actual = {row['item'].pk: row['item'].has_files for row in response.context['rows']}
            self.assertEqual(actual, {source.pk: source_has_files, target.pk: target_has_files})

        assert_icons(True, False)
        item.folder = target
        item.save(update_fields=['folder'])
        assert_icons(False, True)
        self.assertEqual(self.client.post(f'{self.base}{item.pk}/trash/').status_code, 302)
        assert_icons(False, False)
        self.assertEqual(self.client.post(f'{self.base}{item.pk}/restore/').status_code, 302)
        assert_icons(False, True)

    def test_summary_query_count_is_constant_and_cycles_terminate(self):
        root = self.folder('Główny')
        child = self.folder('Podfolder', parent=root)
        self.document(child)
        root.parent = child
        root.save(update_fields=['parent'])
        folders = [root, child] + [self.folder(f'Pusty {number}') for number in range(30)]
        rows = [{'kind': 'folder', 'item': item} for item in folders]
        with self.assertNumQueries(2):
            set_folder_summaries(rows,
                self.folder_model.objects.filter(owner=self.user, workplace=self.workspace),
                self.document_model.objects.filter(owner=self.user, workplace=self.workspace),
                library_scoped=self.app == 'documents')
        self.assertTrue(root.has_files)
        self.assertTrue(child.has_files)
        self.assertTrue(all(not item.has_files for item in folders[2:]))


class DriveFolderIconTests(FolderIconTestsMixin, TestCase):
    app = 'documents'
    folder_model = Folder
    document_model = Document
