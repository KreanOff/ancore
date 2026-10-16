import json
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from tasks.models import TaskTag
from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from . import office_service as service
from .models import Document, DocumentLibrary, DocumentVersion, WorkspaceDocument


@override_settings(ONLYOFFICE_URL='http://office.test', ONLYOFFICE_INTERNAL_URL='http://office.test',
                   ONLYOFFICE_ANCORE_URL='http://ancore.test', ONLYOFFICE_JWT_SECRET='test-only-' * 8)
class OfficeExtrasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='extras', email='extras@example.test')
        cls.other = get_user_model().objects.create_user(username='foreign', email='foreign@example.test')
        cls.workplace = create_workplace_for_user(cls.owner, 'Dokumenty testowe')
        cls.second = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy Workspace')
        cls.base = scoped_workplace_app_path(cls.workplace, 'office')
        cls.drive = scoped_workplace_app_path(cls.workplace, 'documents')
        cls.library = DocumentLibrary.objects.create(owner=cls.owner, workplace=cls.workplace, name='Dysk QA')

    def setUp(self):
        self.client.force_login(self.owner)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        for model in (Document, WorkspaceDocument, DocumentVersion):
            field = model._meta.get_field('file')
            self.addCleanup(setattr, field, 'storage', field.storage)
            field.storage = FileSystemStorage(directory.name)

    def file(self, kind='word', drive=False, **overrides):
        data = service.blank_file(kind)
        model = Document if drive else WorkspaceDocument
        values = {'owner': self.owner, 'workplace': self.workplace, 'title': 'Wzór',
                  'filename': data.name, 'file_size': data.size}
        values.update({'library': self.library} if drive else {'kind': 'file', 'is_pdf_form': kind == 'form'})
        item = model(**{**values, **overrides})
        item.file.save(data.name, data, save=False)
        item.save()
        return item

    def save_callback(self, item, content=None, url=None, payload=None):
        payload = payload or {'key': service.document_key(item), 'status': 6, 'filetype': item.extension.lower(),
                              'url': 'http://office.test/cache/files/result'}
        with patch.object(service, 'download_result', return_value=content or service.blank_file(item.office_type).read()):
            return Client().post(url or service.service_url(item, 'callback'), data=json.dumps(payload),
                                 content_type='application/json', headers={'Authorization': 'Bearer ' + service.sign({'payload': payload})})

    def test_create_pdf_and_form_use_real_private_pdf_and_signed_config(self):
        for kind in ('pdf', 'form'):
            response = self.client.post(self.base + 'create/', {'kind': kind, 'title': kind}, headers={'X-Document-Modal': 'true'})
            self.assertEqual(response.status_code, 200)
            item = WorkspaceDocument.objects.get(title=kind)
            self.assertEqual(item.office_type, 'pdf')
            self.assertEqual(item.is_pdf_form, kind == 'form')
            self.assertTrue(item.file.read().startswith(b'%PDF-'))
            config = self.client.get(response.json()['editor_url']).context['editor_config']
            self.assertEqual(config['documentType'], 'pdf')
            self.assertTrue(config['document']['permissions']['edit'])
            self.assertEqual(config['document'].get('isForm', False), kind == 'form')
            self.assertEqual(service.verify(config['token'])['document'], config['document'])
            self.assertEqual(self.client.get(self.base + f'{item.pk}/preview/').status_code, 302)

    def test_template_copy_is_independent_and_does_not_inherit_template_flag(self):
        source = self.file('form', is_template=True)
        tag = TaskTag.objects.create(user=self.owner, workplace=self.workplace, name='Historyczna etykieta')
        source.tags.add(tag)
        response = self.client.post(self.base + 'templates/create/', {'template': source.pk, 'title': 'Kopia'}, headers={'X-Document-Modal': 'true'})
        self.assertEqual(response.status_code, 200)
        item = WorkspaceDocument.objects.get(title='Kopia')
        self.assertNotEqual(item.file.name, source.file.name)
        self.assertNotEqual(item.office_key, source.office_key)
        self.assertEqual(item.file.read(), source.file.read())
        self.assertFalse(item.is_template)
        self.assertFalse(item.tags.exists())
        self.assertTrue(item.is_pdf_form)
        self.assertEqual(item.revision, 1)
        self.assertEqual(response.json()['editor_url'], self.base + f'{item.pk}/editor/')

    def test_template_form_rejects_other_owner_workspace_trash_and_unmarked(self):
        for overrides in ({'owner': self.other}, {'workplace': self.second}, {'deleted_at': timezone.now()}, {'is_template': False}):
            source = self.file(**{'is_template': True, **overrides})
            before = WorkspaceDocument.objects.count()
            response = self.client.post(self.base + 'templates/create/', {'template': source.pk, 'title': 'Kopia'})
            self.assertContains(response, 'Wybierz poprawną wartość')
            self.assertEqual(WorkspaceDocument.objects.count(), before)

    def test_toggle_and_templates_catalog_keep_document_access_scoped(self):
        item = self.file()
        self.assertEqual(self.client.get(self.base + f'{item.pk}/template/').status_code, 405)
        self.client.post(self.base + f'{item.pk}/template/')
        self.assertContains(self.client.get(self.base + '?view=templates'), item.title)
        self.client.post(self.base + f'{item.pk}/template/')
        self.assertContains(self.client.get(self.base + '?view=templates'), 'Brak szablonów')
        self.assertTrue(WorkspaceDocument.objects.filter(pk=item.pk).exists())
        self.assertContains(self.client.get(self.base + 'templates/create/'), 'Nie masz jeszcze szablonów')

    def test_missing_template_returns_error_without_creating_copy(self):
        item = self.file(is_template=True)
        item.file.storage.delete(item.file.name)
        response = self.client.post(self.base + 'templates/create/', {'template': item.pk, 'title': 'Kopia'})
        self.assertContains(response, 'Nie można odczytać szablonu')
        self.assertEqual(WorkspaceDocument.objects.count(), 1)

    def legacy_version(self, item):
        parent = {'drive_document': item} if isinstance(item, Document) else {'document': item}
        return DocumentVersion.objects.create(**parent, revision=item.revision, file=item.file.name,
                                              filename=item.filename, file_size=item.file_size,
                                              saved_at=item.updated_at, is_pdf_form=getattr(item, 'is_pdf_form', False))

    def test_pdf_save_replaces_file_without_creating_history_in_both_modules(self):
        for drive in (False, True):
            item = self.file('pdf', drive=drive)
            original_name, original_key = item.file.name, item.office_key
            changed = item.file.read() + b'\n% changed'
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.save_callback(item, content=changed).json(), {'error': 0})
                self.assertTrue(item.file.storage.exists(original_name))
            item.refresh_from_db()
            self.assertEqual(item.file.read(), changed)
            self.assertEqual(item.revision, 2)
            self.assertEqual(item.office_key, original_key)
            self.assertFalse(item.versions.exists())
            self.assertFalse(item.file.storage.exists(original_name))
            base = self.drive if drive else self.base
            response = self.client.get(base + f'{item.pk}/download/')
            self.assertEqual(b''.join(response.streaming_content), changed)
            self.assertIn('private', response['Cache-Control'])

    def test_callback_replay_does_not_create_history_or_repeat_save(self):
        item = self.file()
        self.save_callback(item)
        self.save_callback(item)
        item.refresh_from_db()
        self.assertEqual(item.revision, 2)
        self.assertEqual(item.save_receipts.count(), 1)
        self.assertFalse(item.versions.exists())

    def test_failed_callback_leaves_original_and_no_history(self):
        item = self.file('pdf')
        original = item.file.name
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.save_callback(item, content=b'not a pdf').json(), {'error': 1})
        item.refresh_from_db()
        self.assertEqual(item.file.name, original)
        self.assertTrue(item.file.storage.exists(original))
        self.assertFalse(item.versions.exists())

    def test_template_actions_still_require_csrf(self):
        item = self.file()
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.owner)
        self.assertEqual(strict.post(self.base + 'templates/create/', {}).status_code, 403)
        self.assertEqual(strict.post(self.base + f'{item.pk}/template/').status_code, 403)

    def test_retired_history_routes_cannot_read_or_restore_existing_versions(self):
        for drive in (False, True):
            item = self.file('pdf', drive=drive)
            snapshot = self.legacy_version(item)
            original_name, original_key = item.file.name, item.office_key
            bases = [self.drive, '/documents/'] if drive else [self.base, '/office/']
            for base in bases:
                for suffix in ['history/', f'versions/{snapshot.pk}/download/', f'versions/{snapshot.pk}/restore/']:
                    for method in [self.client.get, self.client.post]:
                        with self.subTest(drive=drive, base=base, suffix=suffix, method=method.__name__):
                            response = method(base + f'{item.pk}/{suffix}', {'revision': item.revision}, follow=True)
                            self.assertEqual(response.status_code, 404)
            item.refresh_from_db()
            self.assertEqual((item.file.name, item.revision, item.office_key), (original_name, 1, original_key))
            self.assertEqual(item.versions.get().pk, snapshot.pk)
            self.assertTrue(snapshot.file.storage.exists(snapshot.file.name))

    def test_catalogs_and_editors_have_no_history_actions_in_both_layouts(self):
        for drive in (False, True):
            item = self.file(drive=drive)
            bases = [self.drive, '/documents/'] if drive else [self.base, '/office/']
            for base in bases:
                for display in ['list', 'grid']:
                    query = {'display': display, **({'library': self.library.pk} if drive else {})}
                    response = self.client.get(base, query, follow=True)
                    self.assertContains(response, item.title)
                    self.assertContains(response, 'Edytuj dane')
                    self.assertContains(response, 'Pobierz')
                    self.assertNotContains(response, 'Historia wersji')
                    self.assertNotContains(response, '/history/')
                response = self.client.get(base + f'{item.pk}/editor/', follow=True)
                self.assertContains(response, 'office-editor-window')
                self.assertNotContains(response, '/history/')

    def test_replacement_cleans_file_after_commit_and_resets_form_type(self):
        item = self.file('form', is_template=True)
        old_name, old_key = item.file.name, item.office_key
        old_url = service.service_url(item, 'callback')
        old_payload = {'key': service.document_key(item), 'status': 6, 'filetype': 'pdf',
                       'url': 'http://office.test/cache/files/test'}
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.base + f'{item.pk}/', {'title': item.title, 'revision': item.revision,
                             'replacement': SimpleUploadedFile('tekst.txt', b'new content')})
            self.assertTrue(item.file.storage.exists(old_name))
        item.refresh_from_db()
        self.assertFalse(item.versions.exists())
        self.assertFalse(item.file.storage.exists(old_name))
        self.assertEqual(item.file.read(), b'new content')
        self.assertEqual(item.revision, 2)
        self.assertNotEqual(item.office_key, old_key)
        self.assertFalse(item.is_pdf_form)
        self.assertFalse(item.is_template)
        self.assertFalse(item.tags.exists())
        self.assertEqual(self.save_callback(item, content=b'%PDF old session', url=old_url, payload=old_payload).status_code, 409)

    def test_storage_failure_keeps_current_file(self):
        for drive in (False, True):
            item = self.file(drive=drive)
            original = item.file.name
            with self.captureOnCommitCallbacks(execute=True):
                with patch.object(item.file.storage, 'save', side_effect=OSError('Disk full')):
                    self.assertEqual(self.save_callback(item).json(), {'error': 1})
            item.refresh_from_db()
            self.assertEqual(item.file.name, original)
            self.assertEqual(item.revision, 1)
            self.assertTrue(item.file.storage.exists(original))
            self.assertFalse(item.versions.exists())

    def test_database_failure_keeps_original_and_removes_new_file(self):
        for drive in (False, True):
            item = self.file(drive=drive)
            original = item.file.name
            before = set(item.file.storage.listdir(str(item.workplace_id))[1])
            with self.captureOnCommitCallbacks(execute=True):
                with patch.object(type(item), 'save', side_effect=RuntimeError('Database write failed')):
                    with self.assertRaises(RuntimeError):
                        self.save_callback(item)
            item.refresh_from_db()
            self.assertEqual(item.file.name, original)
            self.assertEqual(item.revision, 1)
            self.assertTrue(item.file.storage.exists(original))
            self.assertFalse(item.versions.exists())
            self.assertEqual(set(item.file.storage.listdir(str(item.workplace_id))[1]), before)

    def test_save_preserves_existing_archived_files_without_new_versions(self):
        for drive in (False, True):
            item = self.file('pdf', drive=drive)
            snapshot = self.legacy_version(item)
            archived_content = item.file.read()
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.save_callback(item, content=archived_content + b'\n% changed').json(), {'error': 0})
            self.assertEqual(item.versions.count(), 1)
            snapshot.refresh_from_db()
            self.assertEqual(snapshot.file.read(), archived_content)

    def test_delete_cleans_current_and_legacy_archived_files_after_commit(self):
        item = self.file()
        snapshot = self.legacy_version(item)
        self.save_callback(item)
        item.refresh_from_db()
        names = [item.file.name, snapshot.file.name]
        storage = item.file.storage
        with self.captureOnCommitCallbacks(execute=True):
            item.delete()
        self.assertFalse(DocumentVersion.objects.exists())
        self.assertFalse(any(storage.exists(name) for name in names))
