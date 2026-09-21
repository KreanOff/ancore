from io import BytesIO
from pathlib import Path
import tempfile
from unittest.mock import patch
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from tasks.models import TaskTag
from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Document, DocumentLibrary, WorkspaceDocument, WorkspaceDocumentFolder
from .rich_text import CONTENT_LIMIT, clean_content, docx_bytes


class RichTextTests(SimpleTestCase):
    def test_content_removes_active_elements_and_all_attributes(self):
        content = clean_content('<h1 onclick="bad()">Tytuł</h1><p><b>Ważne</b> &amp; <i>tekst</i><img src=x onerror=bad()><a href="javascript:bad()">link</a></p><script>bad()</script><svg><script>bad()</script></svg>')
        self.assertEqual(content, '<h1>Tytuł</h1><p><strong>Ważne</strong> &amp; <em>tekst</em>link</p>')
        self.assertEqual(clean_content(content), content)

    def test_malformed_content_is_balanced_and_bounded(self):
        self.assertEqual(clean_content('<p><b>tekst</p>'), '<p><strong>tekst</strong></p>')
        with self.assertRaises(ValidationError):
            clean_content('x' * (CONTENT_LIMIT + 1))
        with self.assertRaises(ValidationError):
            clean_content('<p>' * 100)
        self.assertEqual(clean_content('<p>A\x01B</p>'), '<p>AB</p>')

    def test_docx_contains_unicode_headings_lists_and_inline_styles(self):
        content = '<h1>Żółć</h1><p><strong>ważne</strong> <em>kursywa</em><u>podkreślenie</u></p><ol><li>Pierwszy</li><li>Drugi</li></ol>'
        with ZipFile(BytesIO(docx_bytes(content))) as archive:
            self.assertIn('[Content_Types].xml', archive.namelist())
            xml = archive.read('word/document.xml')
            root = ET.fromstring(xml)
            text = ''.join(root.itertext())
            self.assertIn('Żółć', text)
            self.assertIn('2. Drugi', text)
            self.assertIn(b'<w:b', xml)
            self.assertIn(b'<w:i', xml)
            self.assertIn(b'<w:u', xml)


class OfficeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='office-owner', email='office-owner@example.test', password='test-pass-123')
        cls.other = get_user_model().objects.create_user(username='office-other', email='office-other@example.test', password='test-pass-123')
        cls.workspace = create_workplace_for_user(cls.user, 'Dokumenty QA')
        cls.second_workspace = create_workplace_for_user(cls.user, 'Drugi QA')
        cls.foreign_workspace = create_workplace_for_user(cls.other, 'Obcy QA')
        cls.base = scoped_workplace_app_path(cls.workspace, 'office')
        cls.drive = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workspace, name='Dysk QA')

    def setUp(self):
        self.client.force_login(self.user)
        self.storage_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage_dir.cleanup)
        field = WorkspaceDocument._meta.get_field('file')
        self.addCleanup(setattr, field, 'storage', field.storage)
        field.storage = FileSystemStorage(self.storage_dir.name)

    def document(self, **kwargs):
        return WorkspaceDocument.objects.create(**{'owner': self.user, 'workplace': self.workspace,
                                                    'title': 'Plan zespołu', 'content': '<p>Treść</p>', **kwargs})

    def folder(self, **kwargs):
        return WorkspaceDocumentFolder.objects.create(**{'owner': self.user, 'workplace': self.workspace, 'name': 'Materiały', **kwargs})

    def save_payload(self, **kwargs):
        return {'title': 'Nowy dokument', 'content': '<p>Treść</p>', 'folder': '', 'revision': 1, **kwargs}

    def test_empty_catalog_is_separate_from_drive_and_requires_login(self):
        response = Client().get(self.base)
        self.assertEqual(response.status_code, 302)
        Document.objects.create(owner=self.user, workplace=self.workspace, library=self.drive, title='Tylko na dysku', filename='dysk.txt')
        response = self.client.get(self.base)
        self.assertContains(response, 'Twoje dokumenty w jednym miejscu')
        self.assertContains(response, 'data-sidebar-source-item="office"')
        self.assertContains(response, 'data-sidebar-source-item="documents"')
        self.assertNotContains(response, 'Tylko na dysku')
        item = self.document(title='Tylko w dokumentach')
        drive_response = self.client.get(scoped_workplace_app_path(self.workspace, 'documents') + '?view=all')
        self.assertNotContains(drive_response, item.title)

    def test_create_edit_reload_and_export(self):
        response = self.client.post(self.base + 'create/text/', self.save_payload(content='<h2>Plan</h2><p><b>Ważne</b><img src=x></p>'))
        item = WorkspaceDocument.objects.get()
        self.assertRedirects(response, self.base + f'{item.pk}/')
        self.assertEqual(item.content, '<h2>Plan</h2><p><strong>Ważne</strong></p>')
        self.assertEqual(item.file_size, len(item.content.encode('utf-8')))
        response = self.client.post(self.base + f'{item.pk}/', self.save_payload(title='Po zmianie', content='<p>Druga wersja</p>'), headers={'X-Office-Editor': 'true'})
        self.assertEqual(response.json()['revision'], 2)
        self.assertContains(self.client.get(self.base + f'{item.pk}/'), 'Druga wersja')
        response = self.client.get(self.base + f'{item.pk}/download/')
        self.assertIn('.docx', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        with ZipFile(BytesIO(b''.join(response.streaming_content))) as archive:
            self.assertIn('Druga wersja', archive.read('word/document.xml').decode())

    def test_blank_document_can_be_saved(self):
        response = self.client.post(self.base + 'create/text/', self.save_payload(content=''), headers={'X-Office-Editor': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(WorkspaceDocument.objects.get().content, '')

    def test_document_tags_save_reload_and_clear_for_each_kind(self):
        tag = TaskTag.objects.create(user=self.user, workplace=self.workspace, name='Ważne')
        for kind in WorkspaceDocument.Kind.values:
            with self.subTest(kind=kind):
                item = self.document(kind=kind)
                url = self.base + f'{item.pk}/'
                response = self.client.post(url, self.save_payload(tags=[tag.pk]), headers={'X-Office-Editor': 'true'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(list(item.tags.all()), [tag])
                self.assertContains(self.client.get(url), 'Ważne')
                response = self.client.post(url, self.save_payload(revision=2, tags=[]), headers={'X-Office-Editor': 'true'})
                self.assertEqual(response.status_code, 200)
                self.assertFalse(item.tags.exists())

    def test_document_tags_reject_other_owner_workspace_and_stale_revision(self):
        tag = TaskTag.objects.create(user=self.user, workplace=self.workspace, name='Własny')
        foreign = TaskTag.objects.create(user=self.other, workplace=self.workspace, name='Obcy właściciel')
        outside = TaskTag.objects.create(user=self.user, workplace=self.second_workspace, name='Inny Workspace')
        item = self.document(revision=2)
        item.tags.add(tag)
        url = self.base + f'{item.pk}/'
        response = self.client.get(url)
        self.assertNotContains(response, foreign.name)
        self.assertNotContains(response, outside.name)
        for invalid in [foreign, outside]:
            response = self.client.post(url, self.save_payload(revision=2, tags=[invalid.pk]), headers={'X-Office-Editor': 'true'})
            self.assertEqual(response.status_code, 400)
            self.assertIn('tags', response.json()['errors'])
        response = self.client.post(url, self.save_payload(revision=1, tags=[]), headers={'X-Office-Editor': 'true'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(list(item.tags.all()), [tag])
        item.refresh_from_db()
        self.assertEqual(item.revision, 2)

    def test_tag_filter_search_and_navigation_keep_scope(self):
        tag = TaskTag.objects.create(user=self.user, workplace=self.workspace, name='Klient')
        second_tag = TaskTag.objects.create(user=self.user, workplace=self.workspace, name='Klient ważny')
        folder = self.folder()
        item = self.document(folder=folder)
        item.tags.set([tag, second_tag])
        self.document(title='Bez tagu')
        for overrides in [{'owner': self.other}, {'workplace': self.second_workspace}, {'deleted_at': timezone.now()}]:
            self.document(**overrides).tags.add(tag)
        for url in [self.base, '/office/']:
            response = self.client.get(url, {'tag': tag.pk, 'sort': 'name', 'page_size': 50}, follow=True)
            self.assertEqual([row['item'].pk for row in response.context['rows']], [item.pk])
            self.assertContains(response, 'Tagi')
            for option in response.context['display_options']:
                self.assertIn(f'tag={tag.pk}', option['url'])
            self.assertIn(f'tag={tag.pk}', response.context['return_query'])
            self.assertIn('sort=name', response.context['tag_filter_url'])
        response = self.client.get(self.base, {'q': 'Klient'})
        self.assertEqual([row['item'].pk for row in response.context['rows']], [item.pk])
        response = self.client.post(self.base + f'{item.pk}/star/', {'return_query': f'tag={tag.pk}&display=list'})
        self.assertIn(f'tag={tag.pk}', response.url)
        response = self.client.get(self.base, {'tag': tag.pk, 'view': 'trash'})
        self.assertEqual(len(response.context['rows']), 1)
        self.assertContains(response, tag.name)

    def test_tag_filter_rejects_foreign_and_invalid_tags(self):
        foreign = TaskTag.objects.create(user=self.other, workplace=self.workspace, name='Obcy')
        outside = TaskTag.objects.create(user=self.user, workplace=self.second_workspace, name='Inny')
        for tag in [foreign.pk, outside.pk, 'abc', '9' * 40]:
            with self.subTest(tag=tag):
                self.assertEqual(self.client.get(self.base, {'tag': tag}).status_code, 404)

    def test_conflict_preserves_current_version_and_returns_409(self):
        item = self.document(revision=4)
        response = self.client.post(self.base + f'{item.pk}/', self.save_payload(content='<p>Nie nadpisuj</p>', revision=3), headers={'X-Office-Editor': 'true'})
        self.assertEqual(response.status_code, 409)
        self.assertIn('innym oknie', str(response.json()))
        item.refresh_from_db()
        self.assertEqual(item.revision, 4)
        self.assertEqual(item.content, '<p>Treść</p>')

    def test_invalid_form_preserves_user_input_and_has_no_write(self):
        response = self.client.post(self.base + 'create/text/', self.save_payload(title='', content='<p>Zachowaj mnie</p>'))
        self.assertContains(response, 'Zachowaj mnie')
        self.assertFalse(WorkspaceDocument.objects.exists())
        response = self.client.post(self.base + 'create/text/', self.save_payload(content='x' * (CONTENT_LIMIT + 1)), headers={'X-Office-Editor': 'true'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(WorkspaceDocument.objects.exists())

    def test_documents_are_scoped_and_legacy_folder_parameters_are_ignored(self):
        for owner, workplace in [(self.user, self.second_workspace), (self.other, self.foreign_workspace), (self.other, self.workspace)]:
            item = self.document(owner=owner, workplace=workplace, title='Niewidoczny dokument')
            folder = self.folder(owner=owner, workplace=workplace)
            for suffix in ['', 'preview/', 'download/', 'content/']:
                self.assertEqual(self.client.get(self.base + f'{item.pk}/{suffix}').status_code, 404)
            for suffix in ['', 'star/', 'trash/', 'restore/', 'import/']:
                self.assertEqual(self.client.post(self.base + f'{item.pk}/{suffix}', self.save_payload()).status_code, 404)
            self.assertNotContains(self.client.get(self.base + f'?folder={folder.pk}'), 'Niewidoczny dokument')
            self.assertEqual(self.client.post(self.base + f'folders/{folder.pk}/edit/', {'name': 'Zmiana'}).status_code, 404)
            self.assertEqual(self.client.post(self.base + f'folders/{folder.pk}/delete/').status_code, 404)
            response = self.client.post(self.base + 'create/text/', self.save_payload(folder=folder.pk), headers={'X-Office-Editor': 'true'})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(WorkspaceDocument.objects.filter(owner=self.user, workplace=self.workspace, folder__isnull=False).exists())
        self.assertNotContains(self.client.get(self.base), 'Niewidoczny dokument')

    def test_star_trash_restore_and_hidden_downloads(self):
        item = self.document()
        self.client.post(self.base + f'{item.pk}/star/')
        self.assertContains(self.client.get(self.base + '?view=starred'), item.title)
        self.client.post(self.base + f'{item.pk}/trash/', {'return_query': 'view=starred&display=grid&q=Plan'})
        self.assertNotContains(self.client.get(self.base), item.title)
        self.assertContains(self.client.get(self.base + '?view=trash'), item.title)
        for suffix in ['', 'download/', 'preview/', 'content/']:
            self.assertEqual(self.client.get(self.base + f'{item.pk}/{suffix}').status_code, 404)
        self.assertEqual(self.client.post(self.base + f'{item.pk}/', self.save_payload()).status_code, 404)
        self.client.post(self.base + f'{item.pk}/restore/')
        self.assertContains(self.client.get(self.base), item.title)

    def test_search_pagination_grid_and_owner_scope(self):
        parent = self.folder(name='Katalog')
        WorkspaceDocument.objects.bulk_create([WorkspaceDocument(owner=self.user, workplace=self.workspace, folder=parent, title=f'Materiał {n:02}') for n in range(30)])
        response = self.client.get(self.base + '?q=Materiał&display=grid')
        self.assertEqual(len(response.context['rows']), 25)
        self.assertContains(response, 'documents-grid')
        self.assertIn('q=Mater', response.context['document_window']['next_url'])
        response = self.client.get(response.context['document_window']['next_url'])
        self.assertEqual(len(response.context['rows']), 5)
        self.assertContains(self.client.get(self.base + '?q=nigdzieniema'), 'Brak pasujących dokumentów')

    def test_upload_validation_is_atomic_and_document_only(self):
        for file in [SimpleUploadedFile('zly.txt', b''), SimpleUploadedFile('zly.pdf', b'tekst'), SimpleUploadedFile('obraz.png', b'\x89PNG\r\n\x1a\n')]:
            response = self.client.post(self.base + 'upload/', {'files': [SimpleUploadedFile('Dobry.txt', b'Tresc'), file]}, headers={'X-Document-Modal': 'true'})
            self.assertContains(response, 'tasks-modal__errors')
            self.assertFalse(WorkspaceDocument.objects.exists())
            self.assertEqual(list(Path(self.storage_dir.name).rglob('*')), [])
        with override_settings(MAX_ATTACHMENT_SIZE=5):
            self.client.post(self.base + 'upload/', {'files': SimpleUploadedFile('duzy.txt', b'123456')})
        self.assertFalse(WorkspaceDocument.objects.exists())
        self.client.post(self.base + 'upload/', {'files': [SimpleUploadedFile(f'{i}.txt', b'A') for i in range(21)]})
        self.assertFalse(WorkspaceDocument.objects.exists())

    def test_upload_rollback_removes_files(self):
        with patch.object(WorkspaceDocument, 'save', side_effect=RuntimeError('test rollback')):
            with self.assertRaises(RuntimeError):
                self.client.post(self.base + 'upload/', {'files': SimpleUploadedFile('A.txt', b'A')})
        self.assertFalse(WorkspaceDocument.objects.exists())
        self.assertFalse(any(path.is_file() for path in Path(self.storage_dir.name).rglob('*')))

    def test_upload_import_and_replace_preserve_original_until_replaced(self):
        original = 'Zażółć gęślą\nDrugi akapit'.encode()
        self.client.post(self.base + 'upload/', {'files': SimpleUploadedFile('Tekst.txt', original)})
        source = WorkspaceDocument.objects.get()
        old_path = Path(source.file.path)
        response = self.client.get(self.base + f'{source.pk}/preview/', headers={'X-Document-Modal': 'true'})
        self.assertContains(response, 'Utwórz edytowalną kopię')
        self.client.post(self.base + f'{source.pk}/import/')
        copied = WorkspaceDocument.objects.get(kind='text')
        self.assertEqual(copied.content, '<p>Zażółć gęślą</p><p>Drugi akapit</p>')
        self.assertEqual(old_path.read_bytes(), original)
        response = self.client.get(self.base + f'{source.pk}/download/')
        self.assertEqual(b''.join(response.streaming_content), original)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.base + f'{source.pk}/', {'title': 'Nowszy', 'folder': '', 'revision': 1, 'replacement': SimpleUploadedFile('Nowszy.txt', b'Nowa tresc')}, headers={'X-Document-Modal': 'true'})
        self.assertEqual(response.status_code, 200)
        source.refresh_from_db()
        self.assertEqual(Path(source.file.path).read_bytes(), b'Nowa tresc')
        self.assertTrue(old_path.exists())
        self.assertEqual(source.versions.get().filename, 'Tekst.txt')

    def test_docx_import_and_truncated_import_rejection(self):
        self.client.post(self.base + 'upload/', {'files': SimpleUploadedFile('Plan.docx', docx_bytes('<h1>Plan</h1><p>Treść dokumentu</p>'))})
        source = WorkspaceDocument.objects.get()
        self.client.post(self.base + f'{source.pk}/import/')
        self.assertIn('Treść dokumentu', WorkspaceDocument.objects.get(kind='text').content)
        self.client.post(self.base + 'upload/', {'files': SimpleUploadedFile('Duzy.txt', b'A' * (256 * 1024 + 1))})
        source = WorkspaceDocument.objects.get(filename='Duzy.txt')
        self.client.post(self.base + f'{source.pk}/import/')
        self.assertEqual(WorkspaceDocument.objects.filter(kind='text').count(), 1)

    def test_pdf_preview_private_headers_and_missing_file(self):
        self.client.post(self.base + 'upload/', {'files': SimpleUploadedFile('Plan.pdf', b'%PDF-1.7\n%%EOF')})
        item = WorkspaceDocument.objects.get()
        response = self.client.get(self.base + f'{item.pk}/content/')
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertIn('sandbox', response['Content-Security-Policy'])
        b''.join(response.streaming_content)
        item.file.storage.delete(item.file.name)
        self.assertEqual(self.client.get(self.base + f'{item.pk}/download/').status_code, 404)
        self.assertRedirects(self.client.get(self.base + f'{item.pk}/preview/'), self.base + f'{item.pk}/editor/', fetch_redirect_response=False)

    def test_workspace_deletion_cascades_and_cleans_upload(self):
        parent = self.folder()
        child = self.folder(parent=parent, name='Podfolder')
        self.client.post(self.base + f'upload/?folder={child.pk}', {'files': SimpleUploadedFile('A.txt', b'A')})
        path = Path(WorkspaceDocument.objects.get().file.path)
        with self.captureOnCommitCallbacks(execute=True):
            self.workspace.delete()
        self.assertFalse(WorkspaceDocument.objects.exists())
        self.assertFalse(WorkspaceDocumentFolder.objects.exists())
        self.assertFalse(path.exists())

    def test_legacy_route_and_global_search(self):
        item = self.document(title='Apollo dokument')
        self.document(title='Apollo inny', workplace=self.second_workspace)
        self.document(title='Apollo obcy', owner=self.other, workplace=self.workspace)
        self.document(title='Apollo kosz', deleted_at=timezone.now())
        self.client.get(self.base)
        self.assertRedirects(self.client.get('/office/'), self.base)
        response = self.client.get(reverse('global_search'), {'q': 'Apollo'})
        groups = {group['key']: group for group in response.json()['groups']}
        results = groups['office-documents']['results']
        self.assertEqual([result['title'] for result in results], [item.title])
        self.assertEqual(results[0]['url'], self.base + f'{item.pk}/')

    def test_csrf_and_method_protection(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.base + 'create/text/', self.save_payload()).status_code, 403)
        item = self.document()
        self.assertEqual(self.client.get(self.base + f'{item.pk}/trash/').status_code, 405)
