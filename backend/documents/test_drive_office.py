"""The shared office editor must persist to the drive, within its own scope."""
import json
import tempfile
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from tasks.models import TaskTag
from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from . import office_service as service
from .forms import DocumentForm
from .models import Document, DocumentLibrary, Folder, DriveOfficeSaveReceipt, WorkspaceDocument
from .rich_text import docx_bytes


@override_settings(ONLYOFFICE_URL='http://office.test:8088', ONLYOFFICE_INTERNAL_URL='http://office-internal',
                   ONLYOFFICE_ANCORE_URL='http://ancore.test', ONLYOFFICE_JWT_SECRET='test-only-' * 8)
class DriveOfficeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='drive-editor', email='drive-editor@example.test')
        cls.other = get_user_model().objects.create_user(username='drive-other', email='drive-other@example.test')
        cls.workplace = create_workplace_for_user(cls.user, 'Pliki QA')
        cls.second = create_workplace_for_user(cls.user, 'Drugi QA')
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy QA')
        cls.library = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workplace, name='Materiały')
        cls.folder = Folder.objects.create(owner=cls.user, workplace=cls.workplace, library=cls.library, name='Umowy')
        cls.base = scoped_workplace_app_path(cls.workplace, 'documents')

    def setUp(self):
        self.client.force_login(self.user)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        field = Document._meta.get_field('file')
        self.addCleanup(setattr, field, 'storage', field.storage)
        field.storage = FileSystemStorage(directory.name)

    def file(self, kind='word', **overrides):
        extension = service.OFFICE_FORMATS[kind][0]
        item = Document(**{'owner': self.user, 'workplace': self.workplace, 'library': self.library,
                           'folder': self.folder, 'title': f'Plik {kind}', 'filename': f'Plik.{extension}', **overrides})
        item.file.save(item.filename, service.blank_file(kind), save=False)
        item.file_size = item.file.size
        item.save()
        return item

    def payload(self, item, **overrides):
        return {'key': service.document_key(item), 'status': 6, 'filetype': item.extension.lower(),
                'url': 'http://office.test:8088/cache/files/test/output.docx', **overrides}

    def callback(self, item, payload, url=None):
        return Client().post(url or service.service_url(item, 'callback'), json.dumps(payload),
                             content_type='application/json',
                             headers={'Authorization': 'Bearer ' + service.sign({'payload': payload})})

    def test_word_excel_powerpoint_open_in_new_tabs_and_keep_drive_location(self):
        for kind in service.OFFICE_FORMATS:
            item = self.file(kind)
            editor_url = f'{self.base}{item.pk}/editor/'
            for display in ('list', 'grid'):
                page = self.client.get(self.base, {'library': self.library.pk, 'folder': self.folder.pk, 'display': display})
                self.assertRegex(page.content.decode(), rf'<a [^>]*href="{editor_url}"[^>]*target="_blank"[^>]*rel="noopener"')
                self.assertNotRegex(page.content.decode(), rf'<a [^>]*href="{editor_url}"[^>]*data-document-modal')
                self.assertContains(page, f'aria-label="Edytuj dane: {item.title}"')
            page = self.client.get(editor_url)
            config = page.context['editor_config']
            self.assertEqual(config['documentType'], kind)
            # Timestamped signatures can differ across a second boundary.
            # Verify the editor URL and its capability instead of minting a
            # second token and comparing the two serialized signatures.
            source = urlsplit(config['document']['url'])
            self.assertEqual((source.scheme, source.netloc), ('http', 'ancore.test'))
            self.assertEqual(source.path, reverse('drive-office-service-source', args=[item.pk]))
            self.assertTrue(service.check_capability(item, parse_qs(source.query)['token'][0], 'source'))
            self.assertIn('/drive-office-service/', config['editorConfig']['callbackUrl'])
            self.assertEqual(service.verify(config['token'])['document']['key'], service.document_key(item))
            self.assertContains(page, 'office-editor-window')
            self.assertNotContains(page, 'id="app-sidebar"')
            self.assertContains(page, 'Wróć do dysku')
            self.assertEqual(page.context['folder_url'], f'{self.base}?library={self.library.pk}&folder={self.folder.pk}')
            self.assertEqual(page['Cache-Control'], 'private, no-store')
            self.assertRedirects(self.client.get(f'{self.base}{item.pk}/preview/'), editor_url, fetch_redirect_response=False)
        self.assertFalse(WorkspaceDocument.objects.exists())

    def test_search_and_unscoped_editor(self):
        item = self.file()
        self.client.get(self.base)
        response = self.client.get(reverse('documents:editor', args=[item.pk]), follow=True)
        self.assertContains(response, 'data-office-suite')
        response = self.client.get(reverse('global_search'), {'q': item.title})
        group = next(group for group in response.json()['groups'] if group['key'] == 'documents')
        self.assertEqual(group['results'][0]['url'], f'{self.base}{item.pk}/editor/')
        self.assertTrue(group['results'][0]['new_tab'])

    def test_all_user_endpoints_require_owner_workspace_and_active_file(self):
        item = self.file()
        for method, suffix in [('get', 'editor/'), ('get', 'state/'), ('post', 'save/'), ('post', 'convert/')]:
            with self.subTest(suffix=suffix):
                self.assertEqual(getattr(Client(), method)(f'{self.base}{item.pk}/{suffix}').status_code, 302)
                other_base = scoped_workplace_app_path(self.second, 'documents')
                self.assertEqual(getattr(self.client, method)(f'{other_base}{item.pk}/{suffix}').status_code, 404)
                self.client.force_login(self.other)
                foreign_base = scoped_workplace_app_path(self.foreign, 'documents')
                self.assertEqual(getattr(self.client, method)(f'{foreign_base}{item.pk}/{suffix}').status_code, 404)
                self.client.force_login(self.user)
                item.deleted_at = timezone.now()
                item.save(update_fields=['deleted_at'])
                self.assertEqual(getattr(self.client, method)(f'{self.base}{item.pk}/{suffix}').status_code, 404)
                item.deleted_at = None
                item.save(update_fields=['deleted_at'])
        item.owner = self.other
        item.save(update_fields=['owner'])
        self.assertEqual(self.client.get(f'{self.base}{item.pk}/editor/').status_code, 404)

    def test_csrf_and_http_methods(self):
        item = self.file()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        for suffix in ('save/', 'convert/'):
            self.assertEqual(client.post(f'{self.base}{item.pk}/{suffix}').status_code, 403)
            self.assertEqual(self.client.get(f'{self.base}{item.pk}/{suffix}').status_code, 405)
        for suffix in ('editor/', 'state/'):
            self.assertEqual(self.client.post(f'{self.base}{item.pk}/{suffix}').status_code, 405)

    def test_service_tokens_are_scoped_to_module_and_file(self):
        item = self.file()
        url = service.service_url(item, 'source')
        response = Client().get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b''.join(response.streaming_content))
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(Client().get(url.split('?')[0]).status_code, 404)
        second = self.file()
        self.assertEqual(Client().get(url.replace(str(item.pk), str(second.pk))).status_code, 404)
        # Even identical UUIDs and session values cannot cross the two modules.
        office = WorkspaceDocument.objects.create(id=item.pk, owner=self.user, workplace=self.workplace,
            title='Dokumenty', kind='file', filename=item.filename, file=item.file.name, office_key=item.office_key)
        self.assertNotEqual(service.document_key(item), service.document_key(office))
        self.assertFalse(service.check_capability(office, service.capability(item, 'source'), 'source'))
        self.assertEqual(Client().get(service.service_url(office, 'source').replace('office-service/', 'drive-office-service/')).status_code, 404)
        self.assertEqual(Client().get(url.replace('drive-office-service/', 'office-service/')).status_code, 404)

    @patch('documents.office_service.download_result')
    def test_moves_do_not_acknowledge_content_save(self, download):
        item = self.file()
        target = DocumentLibrary.objects.create(owner=self.user, workplace=self.workplace, name='Drugi dysk')
        state_url = f'{self.base}{item.pk}/state/'
        initial_key, initial_name = service.document_key(item), item.file.name
        self.assertEqual(self.client.get(state_url).json()['save_receipt'], 0)
        response = self.client.post(f'{self.base}{item.pk}/move/', {'target': f'library:{target.pk}'})
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual((item.revision, item.file.name, service.document_key(item)), (2, initial_name, initial_key))
        self.assertEqual(self.client.get(state_url).json()['save_receipt'], 0)

        download.return_value = docx_bytes('<p>Treść zapisana po przeniesieniu</p>')
        payload = self.payload(item)
        self.assertEqual(self.callback(item, payload).json(), {'error': 0})
        receipt = item.save_receipts.get()
        confirmed = self.client.get(state_url).json()
        self.assertEqual(confirmed['save_receipt'], receipt.pk)
        for base in (self.base, '/documents/'):
            editor = self.client.get(f'{base}{item.pk}/editor/', follow=True)
            self.assertContains(editor, f'data-save-receipt="{receipt.pk}"')
            self.assertEqual(editor.context['frontend_bootstrap']['data']['save_receipt'], receipt.pk)

        response = self.client.post(f'{self.base}{item.pk}/move/', {'target': f'folder:{self.folder.pk}'})
        self.assertEqual(response.status_code, 302)
        # Moving the containing folder to another drive also updates document metadata.
        response = self.client.post(f'{self.base}folders/{self.folder.pk}/move/', {'target': f'library:{target.pk}'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(state_url).json()['save_receipt'], receipt.pk)
        self.assertEqual(self.client.get(state_url).json()['saved_at'], confirmed['saved_at'])
        self.assertEqual(self.callback(item, payload).json(), {'error': 0})
        self.assertEqual(self.client.get(state_url).json()['save_receipt'], receipt.pk)
        self.assertEqual(download.call_count, 1)

    @patch('documents.office_service.download_result')
    def test_save_and_final_callback_persist_on_drive_and_deduplicate(self, download):
        for kind in service.OFFICE_FORMATS:
            item = self.file(kind)
            original_name, original_key = item.file.name, item.office_key
            content = service.blank_file(kind).read()
            download.return_value = content
            payload, url = self.payload(item), service.service_url(item, 'callback')
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.callback(item, payload, url).json(), {'error': 0})
            item.refresh_from_db()
            self.assertEqual(item.revision, 2)
            self.assertEqual(item.office_key, original_key)
            self.assertEqual((item.library_id, item.folder_id), (self.library.pk, self.folder.pk))
            self.assertFalse(item.file.storage.exists(original_name))
            self.assertFalse(item.versions.exists())
            response = self.client.get(f'{self.base}{item.pk}/download/')
            self.assertEqual(b''.join(response.streaming_content), content)
            self.assertEqual(self.callback(item, payload, url).json(), {'error': 0})
            final = self.payload(item, status=2)
            self.assertEqual(self.callback(item, final, url).json(), {'error': 0})
            item.refresh_from_db()
            self.assertNotEqual(item.office_key, original_key)
            self.assertEqual(item.revision, 3)
            self.assertEqual(self.callback(item, final, url).json(), {'error': 0})
            self.assertEqual(item.save_receipts.count(), 2)
        self.assertEqual(download.call_count, 2 * len(service.OFFICE_FORMATS))
        self.assertFalse(WorkspaceDocument.objects.exists())

    @patch('documents.office_service.download_result')
    def test_unsigned_and_browser_tokens_cannot_save(self, download):
        item = self.file()
        url, payload = service.service_url(item, 'callback'), self.payload(item)
        self.assertEqual(Client().post(url, payload).status_code, 403)
        token = service.editor_config(item, self.user)['token']
        self.assertEqual(Client().post(url, json.dumps(payload), content_type='application/json',
            headers={'Authorization': 'Bearer ' + token}).status_code, 403)
        self.assertEqual(self.callback(item, {**payload, 'key': '0' * 64}).status_code, 409)
        self.assertEqual(self.callback(item, payload, url.split('?')[0]).status_code, 409)
        download.assert_not_called()

    @patch('documents.office_service.download_result')
    def test_failed_or_invalid_save_keeps_original(self, download):
        item = self.file()
        original = item.file.name
        for value in (URLError('unavailable'), b'PK\x03\x04invalid'):
            download.side_effect = value if isinstance(value, Exception) else None
            download.return_value = value
            self.assertEqual(self.callback(item, self.payload(item)).status_code, 502)
            item.refresh_from_db()
            self.assertEqual(item.file.name, original)
            self.assertEqual(item.revision, 1)
            self.assertTrue(item.office_save_error)
            self.assertFalse(DriveOfficeSaveReceipt.objects.exists())

    @patch('documents.office_service.download_result')
    def test_trash_and_restore_invalidate_source_and_save_session(self, download):
        item = self.file()
        source_url, callback_url = service.service_url(item, 'source'), service.service_url(item, 'callback')
        payload = self.payload(item)
        self.client.post(f'{self.base}{item.pk}/trash/')
        self.assertEqual(Client().get(source_url).status_code, 404)
        self.assertEqual(self.callback(item, payload, callback_url).status_code, 404)
        self.client.post(f'{self.base}{item.pk}/restore/')
        self.assertEqual(Client().get(source_url).status_code, 404)
        self.assertEqual(self.callback(item, payload, callback_url).status_code, 409)
        download.assert_not_called()

    @patch('documents.office_service.force_save', return_value=0)
    def test_manual_save_requires_current_key(self, force):
        item = self.file()
        url = f'{self.base}{item.pk}/save/'
        self.assertEqual(self.client.post(url).status_code, 409)
        force.assert_not_called()
        self.assertTrue(self.client.post(url, headers={'X-Office-Key': service.document_key(item)}).json()['pending'])
        self.assertEqual(self.client.get(f'{self.base}{item.pk}/state/').json()['key'], service.document_key(item))

    def test_metadata_save_preserves_concurrent_editor_save(self):
        item = self.file()
        original_is_valid = DocumentForm.is_valid

        def save_during_validation(form):
            valid = original_is_valid(form)
            # A completed callback between loading the form and saving metadata.
            Document.objects.filter(pk=item.pk).update(revision=2, file_size=123, file='new-version.docx')
            return valid

        with patch.object(DocumentForm, 'is_valid', save_during_validation):
            response = self.client.post(f'{self.base}{item.pk}/',
                {'title': 'Nowa nazwa', 'description': 'Nowy opis', 'folder': self.folder.pk})
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual((item.title, item.description), ('Nowa nazwa', 'Nowy opis'))
        self.assertEqual((item.revision, item.file_size, item.file.name), (2, 123, 'new-version.docx'))

    @patch('documents.office_service.convert_file')
    def test_legacy_conversion_preserves_location_without_copying_tags(self, convert):
        item = self.file(filename='Notatki.doc', description='Opis')
        tag = TaskTag.objects.create(user=self.user, workplace=self.workplace, name='Materiały')
        item.tags.add(tag)
        convert.return_value = ('docx', docx_bytes('<p>Konwersja</p>'))
        self.assertContains(self.client.get(f'{self.base}{item.pk}/preview/'), f'{item.pk}/convert/')
        response = self.client.post(f'{self.base}{item.pk}/convert/')
        copy = Document.objects.exclude(pk=item.pk).get()
        self.assertRedirects(response, f'{self.base}{copy.pk}/editor/', fetch_redirect_response=False)
        self.assertEqual((copy.library_id, copy.folder_id, copy.description), (item.library_id, item.folder_id, item.description))
        self.assertFalse(copy.tags.exists())
        self.assertEqual(list(item.tags.all()), [tag])
        item.refresh_from_db()
        self.assertEqual(item.filename, 'Notatki.doc')
        self.assertFalse(WorkspaceDocument.objects.exists())

    def test_upload_valid_office_and_reject_invalid_and_empty_files(self):
        for kind in service.OFFICE_FORMATS:
            file = service.blank_file(kind)
            self.assertEqual(self.client.post(f'{self.base}upload/?library={self.library.pk}',
                {'files': SimpleUploadedFile(file.name, file.read())}).status_code, 302)
        before = Document.objects.count()
        for data in (b'', b'PK\x03\x04invalid'):
            response = self.client.post(f'{self.base}upload/?library={self.library.pk}',
                {'files': SimpleUploadedFile('fake.xlsx', data)})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['document_form']['form'].errors)
        self.assertEqual(Document.objects.count(), before)

    @override_settings(ONLYOFFICE_URL='', ONLYOFFICE_JWT_SECRET='')
    def test_unconfigured_office_keeps_download_and_return_to_drive(self):
        item = self.file()
        response = self.client.get(f'{self.base}{item.pk}/editor/')
        self.assertContains(response, 'Edytor biurowy jest niedostępny')
        self.assertContains(response, f'{item.pk}/download/')
        self.assertContains(response, 'Wróć do dysku')
        self.assertEqual(self.client.post(f'{self.base}{item.pk}/save/').status_code, 503)
