import json
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from . import office_service as service
from .board import EMPTY_SCENE, clean_scene
from .models import WorkspaceDocument as Document, WorkspaceDocumentFolder as Folder, OfficeSaveReceipt
from .rich_text import docx_bytes


@override_settings(ONLYOFFICE_URL='http://office.test:8088', ONLYOFFICE_INTERNAL_URL='http://office-internal:80',
                   ONLYOFFICE_ANCORE_URL='http://ancore.test', ONLYOFFICE_JWT_SECRET='test-only-' * 8)
class FullEditorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='suite-owner', email='suite-owner@example.test', password='test-only-password')
        cls.other = get_user_model().objects.create_user(username='suite-other', email='suite-other@example.test', password='test-only-password')
        cls.workplace = create_workplace_for_user(cls.user, 'Pakiet QA')
        cls.second = create_workplace_for_user(cls.user, 'Drugi QA')
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy QA')
        cls.base = scoped_workplace_app_path(cls.workplace, 'office')

    def setUp(self):
        self.client.force_login(self.user)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        field = Document._meta.get_field('file')
        self.addCleanup(setattr, field, 'storage', field.storage)
        field.storage = FileSystemStorage(self.directory.name)

    def file(self, **overrides):
        item = Document(owner=self.user, workplace=self.workplace, kind=Document.Kind.FILE,
                        title='Dokument', filename='Dokument.docx', **overrides)
        item.file.save(item.filename, service.blank_file('word'), save=False)
        item.file_size = item.file.size
        item.save()
        return item

    def board(self, **overrides):
        return Document.objects.create(**{'owner': self.user, 'workplace': self.workplace, 'kind': Document.Kind.BOARD,
                                         'title': 'Mapa', 'content': json.dumps(EMPTY_SCENE), **overrides})

    def callback(self, item, payload, url=None):
        token = service.sign({'payload': payload})
        return Client().post(url or service.service_url(item, 'callback'), data=json.dumps(payload), content_type='application/json', headers={'Authorization': 'Bearer ' + token})

    def payload(self, item, **extra):
        return {'key': service.document_key(item), 'status': 6, 'filetype': 'docx',
                'url': 'http://office.test:8088/cache/files/test/output.docx?md5=signature', **extra}

    def test_create_all_four_types_and_open_private_editors(self):
        for kind, extension in [('word', 'DOCX'), ('cell', 'XLSX'), ('slide', 'PPTX'), ('board', 'BOARD')]:
            response = self.client.post(self.base + 'create/', {'kind': kind, 'title': kind})
            item = Document.objects.get(title=kind)
            self.assertRedirects(response, self.base + f'{item.pk}/editor/', fetch_redirect_response=False)
            self.assertEqual(item.extension, extension)
            page = self.client.get(response.url)
            self.assertContains(page, 'data-app-full-navigation')
            self.assertContains(page, 'class="office-editor-window"')
            self.assertNotContains(page, 'id="app-sidebar"')
            for base in (self.base, '/office/'):
                for display in ('list', 'grid'):
                    catalog = self.client.get(base, {'display': display}, follow=True)
                    self.assertRegex(catalog.content.decode(),
                                     rf'<a [^>]*href="{response.url}"[^>]*target="_blank"[^>]*rel="noopener"')
                metadata = self.client.get(base + f'{item.pk}/', headers={'X-Document-Modal': 'true'}, follow=True)
                self.assertRegex(metadata.content.decode(),
                                 rf'<a [^>]*href="{self.base}{item.pk}/preview/"[^>]*target="_blank"[^>]*rel="noopener"')
            if kind != 'board':
                config = page.context['editor_config']
                decoded = service.verify(config['token'])
                self.assertEqual(decoded['document']['key'], service.document_key(item))
                self.assertEqual(decoded['documentType'], kind)
                self.assertNotContains(page, 'test-only-')
                with item.file.open('rb') as file:
                    service.validate_ooxml(file, extension)
            else:
                self.assertContains(page, 'data-board-frame')

    def test_modal_creation_keeps_catalog_and_opens_full_editors_separately(self):
        folder = Folder.objects.create(owner=self.user, workplace=self.workplace, name='Umowy')
        for kind in ('word', 'cell', 'slide', 'board'):
            response = self.client.post(self.base + f'create/?folder={folder.pk}',
                                        {'kind': kind, 'title': kind}, headers={'X-Document-Modal': 'true'})
            item = Document.objects.get(title=kind)
            editor_url = self.base + f'{item.pk}/editor/'
            self.assertIsNone(item.folder)
            expected = {'redirect_url': self.base, 'editor_url': editor_url}
            self.assertEqual(response.json(), expected)
        invalid = self.client.post(self.base + 'create/', {'kind': 'word', 'title': ''},
                                   headers={'X-Document-Modal': 'true'})
        self.assertContains(invalid, 'data-office-create')
        self.assertContains(invalid, 'To pole jest wymagane.')
        self.assertEqual(Document.objects.count(), 4)

    def test_search_opens_full_editors_in_new_tab_and_preserves_other_results(self):
        office = self.file()
        board = self.board(title='Dokument tablicy')
        text = Document.objects.create(owner=self.user, workplace=self.workplace, title='Dokument Ancore')
        self.client.get(self.base)
        response = self.client.get(reverse('global_search'), {'q': 'Dokument'})
        group = next(group for group in response.json()['groups'] if group['key'] == 'office-documents')
        results = {result['title']: result for result in group['results']}
        self.assertTrue(results[office.title]['new_tab'])
        self.assertTrue(results[board.title]['new_tab'])
        self.assertFalse(results[text.title]['new_tab'])

    def test_creation_ignores_legacy_folder_and_invalid_type_does_not_write(self):
        foreign = Folder.objects.create(owner=self.other, workplace=self.foreign, name='Obce')
        self.assertEqual(self.client.post(self.base + f'create/?folder={foreign.pk}', {'kind': 'word', 'title': 'Test'}).status_code, 302)
        item = Document.objects.get()
        self.assertEqual((item.owner, item.workplace, item.folder), (self.user, self.workplace, None))
        self.client.post(self.base + 'create/', {'kind': 'binary', 'title': 'Test'})
        self.assertEqual(Document.objects.count(), 1)

    def test_editors_are_owner_and_workspace_scoped(self):
        items = [self.board(owner=self.other, workplace=self.foreign), self.board(workplace=self.second)]
        for item in items:
            for suffix in ('editor/', 'board/', 'state/', 'download/'):
                self.assertEqual(self.client.get(self.base + f'{item.pk}/{suffix}').status_code, 404)
            self.assertEqual(self.client.post(self.base + f'{item.pk}/board/save/', '{}', content_type='application/json').status_code, 404)
        own = self.file()
        self.assertEqual(Client().get(self.base + f'{own.pk}/editor/').status_code, 302)

    def test_board_save_reload_conflict_and_download(self):
        item = self.board()
        scene = {**EMPTY_SCENE, 'elements': [{'id': 'one', 'type': 'text', 'text': 'Pomysł', 'x': 1, 'y': 2}]}
        url = self.base + f'{item.pk}/board/save/'
        body = json.dumps({'revision': 1, 'scene': scene})
        response = self.client.post(url, body, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.revision, 2)
        self.assertEqual(json.loads(item.content)['elements'][0]['text'], 'Pomysł')
        self.assertEqual(self.client.post(url, body, content_type='application/json').status_code, 409)
        page = self.client.get(self.base + f'{item.pk}/board/')
        self.assertEqual(page['X-Frame-Options'], 'SAMEORIGIN')
        self.assertIn("connect-src 'self'", page['Content-Security-Policy'])
        download = self.client.get(self.base + f'{item.pk}/download/')
        self.assertEqual(json.loads(b''.join(download.streaming_content))['elements'][0]['text'], 'Pomysł')

    def test_board_csrf_and_invalid_scene(self):
        item = self.board()
        client = Client(enforce_csrf_checks=True); client.force_login(self.user)
        url = self.base + f'{item.pk}/board/save/'
        self.assertEqual(client.post(url, '{}', content_type='application/json').status_code, 403)
        for raw in ('[]', '{"revision":1,"scene":null}', '{"revision":1,"scene":{"type":"html"}}'):
            self.assertEqual(self.client.post(url, raw, content_type='application/json').status_code, 400)
        item.refresh_from_db(); self.assertEqual(item.revision, 1)

    def test_signed_source_does_not_require_session_and_rejects_stale_capability(self):
        item = self.file()
        url = service.service_url(item, 'source')
        response = Client().get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertTrue(b''.join(response.streaming_content))
        self.assertEqual(Client().get(reverse('office-service-source', args=[item.pk])).status_code, 404)
        second = self.file()
        self.assertEqual(Client().get(url.replace(str(item.pk), str(second.pk))).status_code, 404)
        item.office_key = uuid.uuid4(); item.save(update_fields=['office_key'])
        self.assertEqual(Client().get(url).status_code, 404)

    @patch('documents.office_service.download_result')
    def test_metadata_does_not_acknowledge_content_save(self, download):
        item = self.file()
        state_url = self.base + f'{item.pk}/state/'
        self.assertEqual(self.client.get(state_url).json()['save_receipt'], 0)
        response = self.client.post(self.base + f'{item.pk}/', {
            'title': 'Nowa nazwa', 'folder': '', 'revision': item.revision,
        })
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.revision, 2)
        self.assertEqual(self.client.get(state_url).json()['save_receipt'], 0)

        download.return_value = docx_bytes('<p>Potwierdzony zapis treści</p>')
        payload = self.payload(item)
        self.assertEqual(self.callback(item, payload).json(), {'error': 0})
        receipt = item.save_receipts.get()
        confirmed = self.client.get(state_url).json()
        self.assertEqual(confirmed['save_receipt'], receipt.pk)
        self.assertEqual(self.callback(item, payload).json(), {'error': 0})
        self.assertEqual(self.client.get(state_url).json()['save_receipt'], receipt.pk)

        for base in (self.base, '/office/'):
            editor = self.client.get(base + f'{item.pk}/editor/', follow=True)
            self.assertContains(editor, f'data-save-receipt="{receipt.pk}"')
            self.assertEqual(editor.context['frontend_bootstrap']['data']['save_receipt'], receipt.pk)
        item.refresh_from_db()
        response = self.client.post(self.base + f'{item.pk}/', {
            'title': 'Jeszcze inna nazwa', 'folder': '', 'revision': item.revision,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(state_url).json()['save_receipt'], receipt.pk)
        self.assertEqual(self.client.get(state_url).json()['saved_at'], confirmed['saved_at'])
        self.assertEqual(download.call_count, 1)

    @patch('documents.office_service.download_result')
    def test_force_save_writes_file_and_deduplicates_replay(self, download):
        item = self.file(); old_name = item.file.name; old_key = item.office_key
        content = docx_bytes('<p>Nowa treść</p>'); download.return_value = content
        payload = self.payload(item)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.callback(item, payload)
        self.assertEqual(response.json(), {'error': 0})
        item.refresh_from_db()
        self.assertEqual(item.office_key, old_key)
        self.assertEqual(item.revision, 2)
        self.assertFalse(item.file.storage.exists(old_name))
        self.assertFalse(item.versions.exists())
        with item.file.open('rb') as file: self.assertEqual(file.read(), content)
        self.callback(item, payload)
        self.assertEqual(download.call_count, 1)
        self.assertEqual(OfficeSaveReceipt.objects.count(), 1)

    @patch('documents.office_service.download_result')
    def test_final_save_rotates_session_and_duplicate_final_callback_succeeds(self, download):
        item = self.file(); key = item.office_key; url = service.service_url(item, 'callback')
        download.return_value = docx_bytes('<p>Zakończono</p>')
        payload = self.payload(item, status=2)
        self.assertEqual(self.callback(item, payload, url).json(), {'error': 0})
        item.refresh_from_db(); self.assertNotEqual(item.office_key, key)
        self.assertEqual(self.callback(item, payload, url).json(), {'error': 0})
        self.assertEqual(download.call_count, 1)

    @patch('documents.office_service.download_result')
    def test_tampered_unsigned_wrong_key_and_browser_tokens_cannot_save(self, download):
        item = self.file(); url = service.service_url(item, 'callback'); payload = self.payload(item)
        self.assertEqual(Client().post(url, payload).status_code, 403)
        token = service.editor_config(item, self.user)['token']
        self.assertEqual(Client().post(url, json.dumps(payload), content_type='application/json', headers={'Authorization': 'Bearer ' + token}).status_code, 403)
        self.assertEqual(self.callback(item, {**payload, 'key': '0'*64}).status_code, 409)
        self.assertEqual(self.callback(item, payload, url.split('?')[0]).status_code, 409)
        # Unsigned body cannot change the authenticated status or result URL.
        token = service.sign({'payload': {'key': service.document_key(item), 'status': 1}})
        response = Client().post(url, json.dumps(payload), content_type='application/json', headers={'Authorization': 'Bearer ' + token})
        self.assertEqual(response.json(), {'error': 0})
        download.assert_not_called()

    @patch('documents.office_service.download_result')
    def test_failed_save_keeps_original_and_exposes_error_without_receipt(self, download):
        item = self.file(); old_name = item.file.name
        download.side_effect = URLError('unavailable')
        self.assertEqual(self.callback(item, self.payload(item)).status_code, 502)
        item.refresh_from_db()
        self.assertEqual(item.file.name, old_name)
        self.assertEqual(item.revision, 1)
        self.assertTrue(item.office_save_error)
        self.assertFalse(OfficeSaveReceipt.objects.exists())

    @patch('documents.office_service.download_result')
    def test_replacement_and_trash_invalidate_old_callback(self, download):
        item = self.file(); payload = self.payload(item); url = service.service_url(item, 'callback')
        response = self.client.post(self.base + f'{item.pk}/', {'title': item.title, 'folder': '', 'revision': 1,
            'replacement': SimpleUploadedFile('new.docx', docx_bytes('<p>Replacement</p>'))})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.callback(item, payload, url).status_code, 409)
        item.refresh_from_db(); url = service.service_url(item, 'callback'); payload = self.payload(item)
        self.client.post(self.base + f'{item.pk}/trash/')
        self.assertEqual(self.callback(item, payload, url).status_code, 404)
        self.client.post(self.base + f'{item.pk}/restore/')
        self.assertEqual(self.callback(item, payload, url).status_code, 409)
        download.assert_not_called()

    def test_upload_office_formats_and_reject_renamed_zip(self):
        for kind in service.OFFICE_FORMATS:
            file = service.blank_file(kind)
            response = self.client.post(self.base + 'upload/', {'files': SimpleUploadedFile(file.name, file.read())})
            self.assertEqual(response.status_code, 302)
        before = Document.objects.count()
        response = self.client.post(self.base + 'upload/', {'files': SimpleUploadedFile('fake.xlsx', b'PK\x03\x04garbage')})
        self.assertContains(response, 'nieprawidłową zawartość')
        self.assertEqual(Document.objects.count(), before)

    def test_old_native_document_upgrades_as_copy(self):
        item = Document.objects.create(owner=self.user, workplace=self.workplace, title='Tekst', content='<h1>Treść</h1>')
        response = self.client.post(self.base + f'{item.pk}/upgrade/')
        copy = Document.objects.exclude(pk=item.pk).get()
        self.assertRedirects(response, self.base + f'{copy.pk}/editor/', fetch_redirect_response=False)
        self.assertEqual(copy.extension, 'DOCX'); item.refresh_from_db(); self.assertEqual(item.kind, Document.Kind.TEXT)

    @override_settings(ONLYOFFICE_URL='', ONLYOFFICE_JWT_SECRET='')
    def test_unconfigured_office_explains_unavailability_and_board_still_works(self):
        item = self.file()
        self.assertContains(self.client.get(self.base + f'{item.pk}/editor/'), 'Edytor biurowy jest niedostępny')
        board = self.board()
        self.assertContains(self.client.get(self.base + f'{board.pk}/editor/'), 'data-board-frame')
        self.assertEqual(Client().post(reverse('office-service-callback', args=[item.pk])).status_code, 503)

    @patch('documents.office_service.convert_file')
    def test_legacy_conversion_preserves_original(self, convert):
        item = self.file(); item.filename = 'old.doc'; item.save(update_fields=['filename'])
        convert.return_value = ('docx', docx_bytes('<p>Konwersja</p>'))
        response = self.client.post(self.base + f'{item.pk}/convert/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Document.objects.count(), 2)
        item.refresh_from_db(); self.assertEqual(item.filename, 'old.doc')

    @patch('documents.office_service.force_save', return_value=0)
    def test_manual_save_requires_current_editor_session(self, force):
        item = self.file()
        url = self.base + f'{item.pk}/save/'
        self.assertEqual(self.client.post(url).status_code, 409)
        force.assert_not_called()
        response = self.client.post(url, headers={'X-Office-Key': service.document_key(item)})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['pending'])
        self.assertEqual(self.client.get(self.base + f'{item.pk}/state/').json()['key'], service.document_key(item))

    def test_document_keys_unique_even_with_shared_migration_uuid(self):
        first, second = self.file(), self.file()
        second.office_key = first.office_key
        self.assertNotEqual(service.document_key(first), service.document_key(second))


class SceneValidationTests(SimpleTestCase):
    @override_settings(ONLYOFFICE_URL='/onlyoffice', ONLYOFFICE_INTERNAL_URL='http://office-internal',
                       ONLYOFFICE_JWT_SECRET='test-only-' * 8)
    @patch('documents.office_service._open')
    def test_ip_access_cache_results_always_use_the_internal_office_server(self, open_request):
        open_request.return_value.__enter__.return_value.read.return_value = b'document'
        for url in ('http://192.0.2.10:8080/onlyoffice/cache/files/result.docx',
                    'https://office.example/onlyoffice/cache/files/result.docx',
                    'http://office-internal/cache/files/result.docx'):
            self.assertEqual(service.download_result(url), b'document')
            self.assertEqual(open_request.call_args.args[0].full_url,
                             'http://office-internal/cache/files/result.docx')
        open_request.reset_mock()
        for url in ('http://169.254.169.254/latest/meta-data/', 'http://192.0.2.10:8080/cache/files/result.docx',
                    'http://192.0.2.10:8080/onlyoffice/cache/files/%2e%2e/private',
                    'http://user:password@192.0.2.10:8080/onlyoffice/cache/files/a',
                    'http://192.0.2.10:8080/onlyoffice/cache/files/a#fragment'):
            with self.assertRaises(ValueError):
                service.download_result(url)
        open_request.assert_not_called()

    def test_active_embeds_links_and_malformed_images_are_rejected(self):
        for element in ({'id': 'x', 'type': 'iframe'}, {'id': 'x', 'type': 'text', 'link': 'javascript:alert(1)'}):
            with self.assertRaises(ValidationError): clean_scene(json.dumps({**EMPTY_SCENE, 'elements': [element]}))
        for data in ('[]', 'null', '{"type":"excalidraw","version":2,"elements":NaN}', json.dumps({**EMPTY_SCENE, 'files': {'x': {'id': 'x', 'mimeType': 'image/png', 'dataURL': ''}}})):
            with self.assertRaises(ValidationError): clean_scene(data)

    @override_settings(ONLYOFFICE_URL='https://office.test', ONLYOFFICE_INTERNAL_URL='http://office-internal', ONLYOFFICE_JWT_SECRET='test-only-' * 8)
    @patch('documents.office_service._open')
    def test_callback_download_is_restricted_to_configured_cache(self, open_request):
        for url in ('http://127.0.0.1/secret', 'https://office.test@evil.test/cache/files/a',
                    'https://office.test/settings', 'https://office.test/cache/files/../../private',
                    'https://office.test/cache/files/%2e%2e/private', 'file:///cache/files/a'):
            with self.assertRaises(ValueError): service.download_result(url)
        open_request.assert_not_called()
        open_request.return_value.__enter__.return_value.read.return_value = b'document'
        self.assertEqual(service.download_result('https://office.test/cache/files/convert/output.docx/Notatka%20QA.docx'), b'document')
        self.assertIn('Notatka%20QA.docx', open_request.call_args.args[0].full_url)
