import json
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

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
        response = self.client.post(self.base + 'templates/create/', {'template': source.pk, 'title': 'Kopia'}, headers={'X-Document-Modal': 'true'})
        self.assertEqual(response.status_code, 200)
        item = WorkspaceDocument.objects.get(title='Kopia')
        self.assertNotEqual(item.file.name, source.file.name)
        self.assertNotEqual(item.office_key, source.office_key)
        self.assertEqual(item.file.read(), source.file.read())
        self.assertFalse(item.is_template)
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

    def test_pdf_save_download_restore_and_old_session_rejection_in_both_modules(self):
        for drive in (False, True):
            item = self.file('pdf', drive=drive)
            base = self.drive if drive else self.base
            original = item.file.read()
            old_url = service.service_url(item, 'callback')
            old_payload = {'key': service.document_key(item), 'status': 6, 'filetype': 'pdf', 'url': 'http://office.test/cache/files/test'}
            self.assertEqual(self.save_callback(item, content=original + b'\n% changed').json(), {'error': 0})
            item.refresh_from_db()
            snapshot = item.versions.get()
            response = self.client.get(base + f'{item.pk}/versions/{snapshot.pk}/download/')
            self.assertEqual(b''.join(response.streaming_content), original)
            self.assertIn('private', response['Cache-Control'])
            self.client.post(base + f'{item.pk}/versions/{snapshot.pk}/restore/', {'revision': item.revision})
            item.refresh_from_db()
            self.assertEqual(item.file.read(), original)
            self.assertEqual(item.revision, 3)
            self.assertEqual(item.versions.count(), 2)
            self.assertEqual(self.save_callback(item, url=old_url, payload=old_payload).status_code, 409)
            self.assertEqual(self.client.get(base + f'{item.pk}/history/').status_code, 200)

    def test_callback_replay_does_not_duplicate_history(self):
        item = self.file()
        self.save_callback(item)
        self.save_callback(item)
        self.assertEqual(item.versions.count(), 1)

    def test_failed_callback_leaves_original_and_no_history(self):
        item = self.file('pdf')
        original = item.file.name
        self.assertEqual(self.save_callback(item, content=b'not a pdf').json(), {'error': 1})
        item.refresh_from_db()
        self.assertEqual(item.file.name, original)
        self.assertEqual(item.versions.count(), 0)

    def test_restore_conflict_missing_file_and_csrf_leave_current_untouched(self):
        item = self.file()
        self.save_callback(item)
        item.refresh_from_db()
        snapshot = item.versions.get()
        target = self.base + f'{item.pk}/versions/{snapshot.pk}/restore/'
        self.assertEqual(self.client.get(target).status_code, 405)
        self.client.post(target, {'revision': 1})
        item.refresh_from_db()
        self.assertEqual(item.revision, 2)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.owner)
        self.assertEqual(strict.post(target, {'revision': 2}).status_code, 403)
        self.assertEqual(strict.post(self.base + 'templates/create/', {}).status_code, 403)
        self.assertEqual(strict.post(self.base + f'{item.pk}/template/').status_code, 403)
        snapshot.file.storage.delete(snapshot.file.name)
        self.assertEqual(self.client.get(target.replace('restore/', 'download/')).status_code, 404)
        response = self.client.post(target, {'revision': 2}, follow=True)
        self.assertContains(response, 'Bieżący plik pozostał bez zmian')
        item.refresh_from_db()
        self.assertEqual(item.revision, 2)

    def test_history_boundaries_include_parent_version_owner_workspace_and_trash(self):
        for drive in (False, True):
            item = self.file(drive=drive)
            self.save_callback(item)
            snapshot = item.versions.get()
            base = self.drive if drive else self.base
            sibling = self.file(drive=drive)
            self.assertEqual(self.client.get(base + f'{sibling.pk}/versions/{snapshot.pk}/download/').status_code, 404)
            for field, value in [('owner', self.other), ('workplace', self.second), ('deleted_at', timezone.now())]:
                original = getattr(item, field)
                setattr(item, field, value)
                item.save(update_fields=[field])
                for suffix in ['history/', f'versions/{snapshot.pk}/download/']:
                    self.assertEqual(self.client.get(base + f'{item.pk}/{suffix}').status_code, 404)
                self.assertEqual(self.client.post(base + f'{item.pk}/versions/{snapshot.pk}/restore/', {'revision': 2}).status_code, 404)
                setattr(item, field, original)
                item.save(update_fields=[field])

    def test_replacement_preserves_file_in_history_and_resets_form_type(self):
        item = self.file('form', is_template=True)
        old_name = item.file.name
        self.client.post(self.base + f'{item.pk}/', {'title': item.title, 'revision': item.revision,
                         'replacement': SimpleUploadedFile('tekst.txt', b'new content')})
        item.refresh_from_db()
        self.assertEqual(item.versions.get().file.name, old_name)
        self.assertTrue(item.file.storage.exists(old_name))
        self.assertFalse(item.is_pdf_form)
        self.assertFalse(item.is_template)

    def test_version_storage_failure_rolls_back_snapshot(self):
        item = self.file()
        original = item.file.name
        with patch.object(item.file.storage, 'save', side_effect=OSError('Disk full')):
            self.assertEqual(self.save_callback(item).json(), {'error': 1})
        item.refresh_from_db()
        self.assertEqual(item.file.name, original)
        self.assertEqual(item.versions.count(), 0)

    def test_empty_history_pagination_and_normal_urls(self):
        item = self.file()
        response = self.client.get(self.base + f'{item.pk}/history/')
        self.assertContains(response, 'Brak wcześniejszych wersji')
        self.assertEqual(response['Referrer-Policy'], 'same-origin')
        for revision in range(1, 28):
            # Separate objects are needed here: snapshots own their file paths.
            DocumentVersion.objects.create(document=item, revision=revision, file=f'versions/{revision}.docx',
                                           filename=f'{revision}.docx', file_size=1, saved_at=timezone.now())
        self.assertEqual(len(self.client.get(self.base + f'{item.pk}/history/').context['versions']), 25)
        self.assertEqual(len(self.client.get(self.base + f'{item.pk}/history/?page=2').context['versions']), 2)
        self.assertRedirects(self.client.get(f'/office/{item.pk}/history/'), self.base + f'{item.pk}/history/')

    def test_delete_cleans_current_and_archived_files_after_commit(self):
        item = self.file()
        self.save_callback(item)
        item.refresh_from_db()
        names = [item.file.name, item.versions.get().file.name]
        storage = item.file.storage
        with self.captureOnCommitCallbacks(execute=True):
            item.delete()
        self.assertFalse(DocumentVersion.objects.exists())
        self.assertFalse(any(storage.exists(name) for name in names))
