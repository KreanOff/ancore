from io import BytesIO
import tempfile
from urllib.parse import parse_qs, urlencode, urlsplit
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import WorkspaceDocument as Document, WorkspaceDocumentFolder as Folder


class OfficeFolderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='folder-owner', email='folder-owner@example.test')
        cls.other = get_user_model().objects.create_user(username='folder-other', email='folder-other@example.test')
        cls.workspace = create_workplace_for_user(cls.user, 'Foldery')
        cls.outside = create_workplace_for_user(cls.user, 'Drugi Workspace')
        cls.base = scoped_workplace_app_path(cls.workspace, 'office')

    def setUp(self):
        self.client.force_login(self.user)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        field = Document._meta.get_field('file')
        self.addCleanup(setattr, field, 'storage', field.storage)
        field.storage = FileSystemStorage(directory.name)

    def folder(self, **kwargs):
        return Folder.objects.create(**{'owner': self.user, 'workplace': self.workspace, 'name': 'Materiały', **kwargs})

    def document(self, **kwargs):
        return Document.objects.create(**{'owner': self.user, 'workplace': self.workspace, 'title': 'Notatki',
                                         'content': '<p>Treść dokumentu</p>', **kwargs})

    def download(self, folder, base=None):
        response = self.client.get(f'{base or self.base}folders/{folder.pk}/download/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertIn('.zip', response['Content-Disposition'])
        return ZipFile(BytesIO(b''.join(response.streaming_content)))

    def test_star_toggle_preserves_query_and_does_not_star_contents(self):
        parent = self.folder()
        folder = self.folder(parent=parent, name='Podfolder')
        item = self.document(folder=folder)
        params = {'folder': str(parent.pk), 'view': 'all', 'q': 'Pod', 'name': 'Pod', 'modified': 'today',
                  'starred': 'no', 'sort': 'name_desc', 'page': '2', 'page_size': '25', 'display': 'grid'}
        for base in [self.base, '/office/']:
            self.client.get(self.base)
            response = self.client.post(f'{base}folders/{folder.pk}/star/', {
                'return_query': urlencode({**params, 'next': 'https://example.test/'})})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(urlsplit(response.url).path, self.base)
            self.assertEqual(parse_qs(urlsplit(response.url).query), {key: [value] for key, value in params.items()})
            folder.refresh_from_db()
            self.assertEqual(folder.is_starred, base == self.base)
        item.refresh_from_db()
        parent.refresh_from_db()
        self.assertFalse(item.is_starred)
        self.assertFalse(parent.is_starred)

    def test_starred_view_filters_counts_and_both_layouts(self):
        parent = self.folder()
        folder = self.folder(parent=parent, name='Wybrane', is_starred=True)
        document = self.document(is_starred=True)
        self.document(is_starred=True, deleted_at=timezone.now())
        self.folder(owner=self.other, is_starred=True)
        self.folder(workplace=self.outside, is_starred=True)
        for display in ['list', 'grid']:
            response = self.client.get(self.base, {'view': 'starred', 'display': display})
            self.assertEqual([row['item'] for row in response.context['rows']], [folder, document])
            count = next(view['count'] for view in response.context['office_views'] if view['value'] == 'starred')
            self.assertEqual(count, 2)
            self.assertContains(response, f'folders/{folder.pk}/star/')
            self.assertContains(response, f'folders/{folder.pk}/download/')
            self.assertContains(response, 'aria-pressed="true"')
            self.assertContains(response, 'Pobierz folder ZIP')
        response = self.client.get(self.base, {'starred': 'yes', 'name': 'Wybrane'})
        self.assertEqual([row['item'] for row in response.context['rows']], [folder])
        response = self.client.get(self.base, {'starred': 'no'})
        self.assertEqual([row['item'] for row in response.context['rows']], [parent])
        for params in [{'view': 'starred', 'starred': 'no'}, {'view': 'starred', 'file_type': '.pdf'},
                       {'view': 'starred', 'q': 'Nieistniejący'}]:
            self.assertEqual(self.client.get(self.base, params).context['rows'], [])
        response = self.client.post(f'{self.base}folders/{folder.pk}/star/', {'return_query': 'view=starred'}, follow=True)
        self.assertEqual([row['item'] for row in response.context['rows']], [document])

    def test_starred_folders_paginate_without_repeating_or_losing_rows(self):
        for number in range(27):
            self.folder(name=f'Folder {number:02}', is_starred=True)
        response = self.client.get(self.base, {'view': 'starred', 'page_size': 25, 'display': 'grid', 'sort': 'name_asc'})
        first = [row['item'].pk for row in response.context['rows']]
        response = self.client.get(response.context['document_window']['next_url'])
        last = [row['item'].pk for row in response.context['rows']]
        self.assertEqual((len(first), len(last), len(set(first + last))), (25, 2, 27))

    def test_folder_actions_require_owner_workspace_login_method_and_csrf(self):
        folder = self.folder()
        for base in [self.base, '/office/']:
            self.client.get(self.base)
            for overrides in [{'owner': self.other}, {'workplace': self.outside}]:
                hidden, _ = Folder.objects.get_or_create(name='Ukryty', **{'owner': self.user, 'workplace': self.workspace, **overrides})
                self.assertEqual(self.client.get(f'{base}folders/{hidden.pk}/download/', follow=True).status_code, 404)
                self.assertEqual(self.client.post(f'{base}folders/{hidden.pk}/star/').status_code, 404)
                hidden.refresh_from_db()
                self.assertFalse(hidden.is_starred)
        self.assertEqual(self.client.get(f'{self.base}folders/{folder.pk}/star/').status_code, 405)
        self.assertEqual(self.client.post(f'{self.base}folders/{folder.pk}/download/').status_code, 405)
        for action in ['download', 'star']:
            response = Client().get(f'{self.base}folders/{folder.pk}/{action}/')
            self.assertEqual(response.status_code, 302)
            self.assertIn('login', response.url)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(f'{self.base}folders/{folder.pk}/star/').status_code, 403)

    def test_zip_contains_nested_documents_native_exports_and_empty_folders(self):
        root = self.folder()
        nested = self.folder(parent=root, name='Podfolder')
        self.folder(parent=nested, name='Pusty')
        self.document(folder=root)
        self.document(folder=nested, kind='board', title='Tablica', content='{"type":"excalidraw","elements":[]}')
        self.document(folder=nested, kind='file', filename='Oryginał.txt', file=SimpleUploadedFile('data.txt', b'original'))
        for base in [self.base, '/office/']:
            self.client.get(self.base)
            with self.download(root, base) as archive:
                self.assertEqual(set(archive.namelist()), {'Materiały/', 'Materiały/Podfolder/', 'Materiały/Podfolder/Pusty/',
                    'Materiały/Notatki.docx', 'Materiały/Podfolder/Tablica.excalidraw', 'Materiały/Podfolder/Oryginał.txt'})
                self.assertEqual(archive.read('Materiały/Podfolder/Oryginał.txt'), b'original')
                self.assertEqual(archive.read('Materiały/Podfolder/Tablica.excalidraw'), b'{"type":"excalidraw","elements":[]}')
                with ZipFile(BytesIO(archive.read('Materiały/Notatki.docx'))) as document:
                    self.assertIn('Treść dokumentu', document.read('word/document.xml').decode())
                self.assertIsNone(archive.testzip())

    def test_zip_excludes_trash_unrelated_and_foreign_data_even_with_invalid_relations(self):
        root = self.folder()
        nested = self.folder(parent=root, name='Dołączony')
        self.document(folder=nested, title='Własny')
        self.document(folder=root, deleted_at=timezone.now())
        self.document()  # Outside the requested subtree.
        for overrides in [{'owner': self.other}, {'workplace': self.outside}]:
            self.document(folder=root, **overrides)
            foreign = self.folder(parent=root, name='Ukryty', **overrides)
            self.document(folder=foreign)
            self.folder(parent=foreign, name='Za_obcym_folderem')
        with self.download(root) as archive:
            self.assertEqual(set(archive.namelist()), {'Materiały/', 'Materiały/Dołączony/', 'Materiały/Dołączony/Własny.docx'})

    def test_zip_safe_paths_unique_names_and_empty_folder(self):
        root = self.folder(name='../../')
        with self.download(root) as archive:
            self.assertEqual(archive.namelist(), ['Folder/'])
        self.folder(parent=root, name='Same.txt')
        self.folder(parent=root, name='a/b')
        self.folder(parent=root, name='ab')
        for filename in ['same.txt', 'SAME.txt', '../escape.txt', r'C:\temp\file.txt', '/absolute.txt']:
            self.document(folder=root, kind='file', filename=filename, file=SimpleUploadedFile('data.txt', filename.encode()))
        with self.download(root) as archive:
            names = archive.namelist()
            self.assertEqual(len(names), len(set(name.rstrip('/').casefold() for name in names)))
            self.assertEqual(len(names), 9)
            for name in names:
                self.assertTrue(name.startswith('Folder/'))
                self.assertNotIn('..', name.split('/'))
                self.assertNotIn('\\', name)
            self.assertEqual(sorted(archive.read(name) for name in names if not name.endswith('/')),
                             sorted(filename.encode() for filename in ['same.txt', 'SAME.txt', '../escape.txt', r'C:\temp\file.txt', '/absolute.txt']))

    def test_zip_missing_file_returns_error_instead_of_partial_archive(self):
        folder = self.folder()
        item = self.document(folder=folder, kind='file', filename='Missing.txt', file='missing.txt')
        for file in ['missing.txt', '']:
            item.file = file
            item.save()
            self.assertEqual(self.client.get(f'{self.base}folders/{folder.pk}/download/').status_code, 404)

    def test_zip_handles_cyclic_folder_data_without_recursing_forever(self):
        root = self.folder()
        child = self.folder(parent=root, name='Podfolder')
        root.parent = child
        root.save(update_fields=['parent'])
        with self.download(root) as archive:
            self.assertEqual(archive.namelist(), ['Materiały/', 'Materiały/Podfolder/'])
