"""Compatibility of existing documents after retiring Office folders."""
from io import BytesIO
import tempfile
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import WorkspaceDocument as Document, WorkspaceDocumentFolder as Folder


class OfficeFlatCatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='flat-owner', email='flat-owner@example.test')
        cls.other = get_user_model().objects.create_user(username='flat-other', email='flat-other@example.test')
        cls.workspace = create_workplace_for_user(cls.user, 'Dokumenty')
        cls.outside = create_workplace_for_user(cls.user, 'Drugi Workspace')
        cls.base = scoped_workplace_app_path(cls.workspace, 'office')
        cls.parent = Folder.objects.create(owner=cls.user, workplace=cls.workspace, name='Dawny folder', is_starred=True)
        cls.nested = Folder.objects.create(owner=cls.user, workplace=cls.workspace, parent=cls.parent, name='Dawny podfolder')
        cls.root = Document.objects.create(owner=cls.user, workplace=cls.workspace, title='Dokument główny')
        cls.item = Document.objects.create(owner=cls.user, workplace=cls.workspace, folder=cls.nested,
                                          title='Dokument z podfolderu', content='<p>Zachowana treść</p>')
        cls.trash = Document.objects.create(owner=cls.user, workplace=cls.workspace, folder=cls.parent,
                                           title='Usunięty dokument', deleted_at=timezone.now())
        for overrides in [{'owner': cls.other}, {'workplace': cls.outside}]:
            Document.objects.create(**{'owner': cls.user, 'workplace': cls.workspace, 'folder': cls.nested,
                                       'title': 'Ukryty dokument', **overrides})

    def setUp(self):
        self.client.force_login(self.user)
        self.client.get(self.base)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        field = Document._meta.get_field('file')
        self.addCleanup(setattr, field, 'storage', field.storage)
        field.storage = FileSystemStorage(directory.name)

    def test_all_documents_are_visible_without_folder_controls_in_both_layouts(self):
        for base in [self.base, '/office/']:
            for display in ['list', 'grid']:
                response = self.client.get(base, {'display': display}, follow=True)
                self.assertEqual({row['item'].pk for row in response.context['rows']}, {self.root.pk, self.item.pk})
                self.assertEqual(response.context['document_window']['compact_summary'], '1–2 z 2')
                counts = {view['value']: view['count'] for view in response.context['office_views']}
                self.assertEqual((counts['all'], counts['starred'], counts['trash']), (2, 0, 1))
                for old_ui in ['Nowy folder', 'Dawny folder', 'Dawny podfolder', '/move/', '/folders/', 'data-document-drag', 'name="folder"']:
                    self.assertNotContains(response, old_ui)
                self.assertNotContains(response, 'Ukryty dokument')
                self.assertNotIn('folder', {field['value'] for field in response.context['sort_fields']})

    def test_legacy_folder_links_do_not_hide_documents_or_propagate_location(self):
        for value in [str(self.parent.pk), 'invalid', '9999999999999999999999']:
            response = self.client.get(self.base, {'folder': value, 'sort': 'folder_asc'})
            self.assertEqual({row['item'].pk for row in response.context['rows']}, {self.root.pk, self.item.pk})
            for url in [response.context['search_url'], response.context['clear_url'], response.context['return_query'],
                        *(option['url'] for option in response.context['display_options'])]:
                self.assertNotIn('folder=', url)
        response = self.client.post(f'{self.base}{self.item.pk}/star/', {'return_query': f'folder={self.parent.pk}&display=grid'})
        self.assertEqual(response.url, self.base + '?display=grid')
        self.assertEqual([row['item'].pk for row in self.client.get(response.url + '&view=starred').context['rows']], [self.item.pk])

    def test_retired_routes_cannot_create_modify_or_delete_data(self):
        for base in [self.base, '/office/']:
            for suffix in ['folders/create/', *(f'folders/{self.parent.pk}/{action}/' for action in ['edit', 'delete', 'star', 'download', 'move']), f'{self.item.pk}/move/']:
                for method in [self.client.get, self.client.post]:
                    response = method(base + suffix, {'name': 'Zmiana', 'target': 'root'}, follow=True)
                    self.assertEqual(response.status_code, 404)
        self.parent.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(Folder.objects.count(), 2)
        self.assertEqual(self.parent.name, 'Dawny folder')
        self.assertTrue(self.parent.is_starred)
        self.assertEqual(self.item.folder_id, self.nested.pk)

    def test_metadata_ignores_old_folder_field_and_preserves_content_and_revision_checks(self):
        url = f'{self.base}{self.item.pk}/'
        self.assertNotContains(self.client.get(url), 'name="folder"')
        response = self.client.post(url, {'title': 'Zmieniona nazwa', 'content': self.item.content,
                                         'revision': self.item.revision, 'folder': self.parent.pk}, headers={'X-Office-Editor': 'true'})
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual((self.item.folder_id, self.item.content, self.item.revision), (self.nested.pk, '<p>Zachowana treść</p>', 2))
        stale = self.client.post(url, {'title': 'Stara nazwa', 'content': '', 'revision': 1}, headers={'X-Office-Editor': 'true'})
        self.assertEqual(stale.status_code, 409)
        response = self.client.get(url + 'download/')
        with ZipFile(BytesIO(b''.join(response.streaming_content))) as archive:
            self.assertIn('Zachowana treść', archive.read('word/document.xml').decode())

    def test_upload_and_import_ignore_legacy_folder_and_create_in_catalog(self):
        response = self.client.post(self.base + f'upload/?folder={self.nested.pk}',
                                    {'files': SimpleUploadedFile('Nowy.txt', b'Nowa tresc')})
        self.assertEqual(response.url, self.base)
        item = Document.objects.get(filename='Nowy.txt')
        self.assertIsNone(item.folder_id)
        item.folder = self.nested
        item.save(update_fields=['folder'])
        response = self.client.post(f'{self.base}{item.pk}/import/')
        copy = Document.objects.get(title='Nowy.txt — kopia tekstu')
        self.assertIsNone(copy.folder_id)
        self.assertIn('Nowa tresc', copy.content)
        self.assertEqual(response.url, f'{self.base}{copy.pk}/')

    def test_trash_restore_search_and_pagination_cover_old_subfolders(self):
        response = self.client.get(self.base, {'view': 'trash'})
        self.assertEqual([row['item'].pk for row in response.context['rows']], [self.trash.pk])
        self.client.post(f'{self.base}{self.trash.pk}/restore/')
        response = self.client.get(self.base, {'q': 'Usunięty'})
        self.assertEqual([row['item'].pk for row in response.context['rows']], [self.trash.pk])
        for number in range(27):
            Document.objects.create(owner=self.user, workplace=self.workspace, folder=self.nested, title=f'Plik {number:02}')
        response = self.client.get(self.base, {'sort': 'name_asc', 'page_size': 25})
        first = [row['item'].pk for row in response.context['rows']]
        second = self.client.get(response.context['document_window']['next_url'])
        last = [row['item'].pk for row in second.context['rows']]
        self.assertEqual((len(first), len(last), len(set(first + last))), (25, 5, 30))
        response = self.client.get(reverse('global_search'), {'q': self.item.title})
        result = next(group for group in response.json()['groups'] if group['key'] == 'office-documents')['results'][0]
        self.assertNotIn('Dawny', str(result))
        self.assertEqual(result['url'], f'{self.base}{self.item.pk}/')
