from io import BytesIO
import tempfile
from urllib.parse import parse_qs, urlsplit
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Document, DocumentLibrary, Folder


class DriveFolderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='drive-folder-owner', email='drive-folder-owner@example.test')
        cls.other = get_user_model().objects.create_user(username='drive-folder-other', email='drive-folder-other@example.test')
        cls.workspace = create_workplace_for_user(cls.user, 'Foldery dysku')
        cls.outside = create_workplace_for_user(cls.user, 'Drugi Workspace')
        cls.base = scoped_workplace_app_path(cls.workspace, 'documents')
        cls.library = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workspace, name='Pierwszy dysk')
        cls.second_library = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workspace, name='Drugi dysk')

    def setUp(self):
        self.client.force_login(self.user)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        field = Document._meta.get_field('file')
        self.addCleanup(setattr, field, 'storage', field.storage)
        field.storage = FileSystemStorage(directory.name)

    def folder(self, **kwargs):
        starred = kwargs.pop('is_starred', False)
        item = Folder.objects.create(**{'owner': self.user, 'workplace': self.workspace, 'library': self.library,
                                        'name': 'Materiały', **kwargs})
        if starred:
            item.favorited_by.add(item.owner)
        return item

    def document(self, **kwargs):
        starred = kwargs.pop('is_starred', False)
        item = Document.objects.create(**{'owner': self.user, 'workplace': self.workspace, 'library': self.library,
            'title': 'Plik', 'filename': 'Plik.txt', 'file': SimpleUploadedFile('Plik.txt', b'content'), 'file_size': 7, **kwargs})
        if starred:
            item.favorited_by.add(item.owner)
        return item

    def rows(self, **params):
        response = self.client.get(self.base, {'view': 'starred', **params})
        self.assertEqual(response.status_code, 200)
        return [row['item'] for row in response.context['rows']]

    def download(self, folder, base=None):
        response = self.client.get(f'{base or self.base}folders/{folder.pk}/download/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        return ZipFile(BytesIO(b''.join(response.streaming_content)))

    def test_star_toggle_preserves_library_workspace_and_filters(self):
        parent = self.folder()
        folder = self.folder(parent=parent, name='Podfolder')
        item = self.document(folder=folder)
        params = {'view': 'all', 'folder': str(parent.pk), 'q': 'Pod', 'name': 'Pod', 'modified': 'today',
                  'starred': 'no', 'sort': 'name_desc', 'page': '2', 'page_size': '10', 'display': 'grid'}
        for base in [self.base, '/documents/']:
            self.client.get(self.base)
            response = self.client.post(f'{base}folders/{folder.pk}/star/', {**params, 'next': 'https://example.test/'})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(urlsplit(response.url).path, self.base)
            self.assertEqual(parse_qs(urlsplit(response.url).query), {key: [value] for key, value in {**params, 'library': str(self.library.pk)}.items()})
            folder.refresh_from_db()
            self.assertEqual(folder.favorited_by.filter(pk=self.user.pk).exists(), base == self.base)
        item.refresh_from_db()
        parent.refresh_from_db()
        self.assertFalse(item.favorited_by.exists())
        self.assertFalse(parent.favorited_by.exists())
        params = {'scope': 'workspace', 'view': 'starred', 'document_library': str(self.library.pk), 'display': 'list'}
        response = self.client.post(f'{self.base}folders/{folder.pk}/star/', {**params, 'folder': parent.pk})
        self.assertEqual(parse_qs(urlsplit(response.url).query), {key: [value] for key, value in params.items() if key != 'scope'})

    def test_starred_views_filter_across_drives_show_sizes_locations_and_actions(self):
        parent = self.folder()
        child = self.folder(parent=parent, name='Podfolder', is_starred=True)
        other = self.folder(library=self.second_library, is_starred=True)
        item = self.document(is_starred=True)
        self.document(folder=child)
        self.document(folder=other, library=self.second_library, file_size=9)
        self.document(folder=child, library=self.second_library, file_size=1000)  # Invalid cross-drive relation.
        self.document(folder=child, deleted_at=timezone.now(), is_starred=True)
        for layout in ['list', 'grid']:
            response = self.client.get(self.base, {'view': 'starred', 'display': layout, 'sort': 'name_asc'})
            rows = response.context['rows']
            self.assertEqual([row['item'] for row in rows], [other, child, item])
            self.assertEqual([row['item'].total_size for row in rows[:2]], [9, 7])
            self.assertEqual(rows[0]['url'], f'{self.base}?library={self.second_library.pk}&folder={other.pk}')
            count = next(view['count'] for view in response.context['sidebar_views'] if view['value'] == 'starred')
            self.assertEqual(count, 3)
            self.assertContains(response, f'folders/{child.pk}/star/')
            self.assertContains(response, f'folders/{child.pk}/download/')
            self.assertContains(response, 'aria-pressed="true"')
            self.assertContains(response, 'Drugi dysk')
        self.assertEqual(self.rows(library=self.library.pk, name='Pod'), [child])
        self.assertEqual(self.rows(document_library=self.second_library.pk), [other])
        self.assertEqual(self.rows(view='all', starred='yes', name='Pod'), [child])
        self.assertEqual(self.rows(view='all', starred='no', name='Materiały', library=self.library.pk), [parent])
        self.assertEqual(self.rows(view='all', library=self.library.pk, folder=parent.pk), [child])
        for filters in [{'file_type': '.pdf'}, {'starred': 'no'}, {'q': 'Nieistniejący'}]:
            self.assertEqual(self.rows(**filters), [])
        self.assertNotIn(child, self.rows(view='recent'))
        self.assertNotIn(child, self.rows(view='trash'))
        response = self.client.post(f'{self.base}folders/{other.pk}/star/', {'scope': 'workspace', 'view': 'starred', 'document_library': self.second_library.pk}, follow=True)
        self.assertEqual(response.context['rows'], [])
        self.assertEqual(self.rows(document_library=self.second_library.pk), [])

    def test_starred_folder_pagination(self):
        for number in range(22):
            self.folder(name=f'Folder {number:02}', is_starred=True)
        response = self.client.get(self.base, {'view': 'starred', 'page_size': 10, 'display': 'grid', 'sort': 'name_asc'})
        first = [row['item'].pk for row in response.context['rows']]
        response = self.client.get(response.context['document_window']['next_url'])
        last = [row['item'].pk for row in response.context['rows']]
        self.assertEqual((len(first), len(last), len(set(first + last))), (20, 22, 22))

    def test_actions_require_owner_workspace_library_login_method_and_csrf(self):
        folder = self.folder()
        invalid = []
        for index, overrides in enumerate([{'owner': self.other}, {'workplace': self.outside}]):
            library = DocumentLibrary.objects.create(**{'owner': self.user, 'workplace': self.workspace, 'name': f'Ukryty {index}', **overrides})
            invalid += [self.folder(name=f'Obcy folder {index}', **overrides), self.folder(name='Zły dysk', library=library)]
        for base in [self.base, '/documents/']:
            self.client.get(self.base)
            for hidden in invalid:
                self.assertEqual(self.client.get(f'{base}folders/{hidden.pk}/download/', follow=True).status_code, 404)
                self.assertEqual(self.client.post(f'{base}folders/{hidden.pk}/star/').status_code, 404)
                hidden.favorited_by.add(self.user)
            self.assertEqual(self.client.get(base, {'view': 'starred'}, follow=True).context['rows'], [])
        self.assertEqual(self.client.get(f'{self.base}folders/{folder.pk}/star/').status_code, 405)
        self.assertEqual(self.client.post(f'{self.base}folders/{folder.pk}/download/').status_code, 405)
        for action in ['download', 'star']:
            self.assertEqual(Client().get(f'{self.base}folders/{folder.pk}/{action}/').status_code, 302)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(f'{self.base}folders/{folder.pk}/star/').status_code, 403)

    def test_zip_includes_subfolders_empty_directories_and_original_files(self):
        root = self.folder()
        nested = self.folder(parent=root, name='Podfolder')
        self.folder(parent=nested, name='Pusty')
        self.document(folder=root, filename='Pierwszy.txt')
        self.document(folder=nested, filename='Drugi.txt', file=SimpleUploadedFile('data.txt', b'nested'))
        for base in [self.base, '/documents/']:
            self.client.get(self.base)
            with self.download(root, base) as archive:
                self.assertEqual(set(archive.namelist()), {'Materiały/', 'Materiały/Podfolder/', 'Materiały/Podfolder/Pusty/', 'Materiały/Pierwszy.txt', 'Materiały/Podfolder/Drugi.txt'})
                self.assertEqual(archive.read('Materiały/Pierwszy.txt'), b'content')
                self.assertEqual(archive.read('Materiały/Podfolder/Drugi.txt'), b'nested')
                self.assertIsNone(archive.testzip())

    def test_zip_excludes_trash_other_drives_owners_workspaces_and_invalid_relations(self):
        root = self.folder()
        child = self.folder(parent=root, name='Własny')
        self.document(folder=child)
        self.document(folder=root, deleted_at=timezone.now())
        self.document()
        for index, overrides in enumerate([{'owner': self.other}, {'workplace': self.outside}, {'library': self.second_library}]):
            self.document(folder=child, **overrides)
            foreign = self.folder(parent=root, name=f'Ukryty {index}', **overrides)
            self.document(folder=foreign)
            self.folder(parent=foreign, name='Za_obcym_folderem')
        with self.download(root) as archive:
            self.assertEqual(set(archive.namelist()), {'Materiały/', 'Materiały/Własny/', 'Materiały/Własny/Plik.txt'})

    def test_zip_empty_folder_collisions_paths_and_missing_file(self):
        root = self.folder(name='../../')
        with self.download(root) as archive:
            self.assertEqual(archive.namelist(), ['Folder/'])
        self.folder(parent=root, name='Same.txt')
        for filename in ['same.txt', 'SAME.txt', '../escape.txt']:
            self.document(folder=root, filename=filename, file=SimpleUploadedFile('data.txt', filename.encode()))
        with self.download(root) as archive:
            names = archive.namelist()
            self.assertEqual(len(names), 5)
            self.assertEqual(len(names), len({name.rstrip('/').casefold() for name in names}))
            self.assertTrue(all(name.startswith('Folder/') and '..' not in name.split('/') for name in names))
            self.assertEqual(sorted(archive.read(name) for name in names if not name.endswith('/')),
                             sorted(filename.encode() for filename in ['same.txt', 'SAME.txt', '../escape.txt']))
        self.document(folder=root, filename='Missing.txt', file='missing.txt')
        self.assertEqual(self.client.get(f'{self.base}folders/{root.pk}/download/').status_code, 404)
