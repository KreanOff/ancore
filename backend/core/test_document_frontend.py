import json
import tempfile
from io import BytesIO
from urllib.parse import urlencode
import zipfile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from documents.models import Document, DocumentLibrary, Folder, WorkspaceDocument
from documents.office_service import blank_file
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class ReactDocumentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='react-doc-owner', email='owner@example.test')
        cls.member = users.objects.create_user(username='react-doc-member', email='member@example.test')
        cls.outsider = users.objects.create_user(username='react-doc-outside', email='outside@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Dysk React')
        cls.other = create_workplace_for_user(cls.owner, 'Inny kontekst')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.library = DocumentLibrary.objects.create(owner=cls.owner, workplace=cls.workspace, name='Produkt', color='#123456')
        cls.second = DocumentLibrary.objects.create(owner=cls.owner, workplace=cls.workspace, name='Klienci')
        cls.foreign = DocumentLibrary.objects.create(owner=cls.owner, workplace=cls.other, name='Poufny dysk')
        cls.folder = Folder.objects.create(owner=cls.owner, workplace=cls.workspace, library=cls.library, name='Umowy')
        cls.child = Folder.objects.create(owner=cls.owner, workplace=cls.workspace, library=cls.library, parent=cls.folder, name='Podfolder')
        cls.document = Document.objects.create(owner=cls.owner, workplace=cls.workspace, library=cls.library, folder=cls.child, title='Instrukcja', filename='instrukcja.txt', file_size=10)
        cls.text = WorkspaceDocument.objects.create(owner=cls.owner, workplace=cls.workspace, title='Dokument Ancore', content='<h2>Nagłówek</h2><p>Treść</p>')

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.storage = FileSystemStorage(directory.name)
        for model in (Document, WorkspaceDocument):
            field = model._meta.get_field('file')
            self.addCleanup(setattr, field, 'storage', field.storage)
            field.storage = self.storage
        self.document.file.save('instrukcja.txt', ContentFile('Tekst podglądu <script>nie wykonuj</script>'.encode()))
        self.login(self.member)

    def login(self, user, client=None):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def path(self, app='documents', suffix=''):
        return scoped_workplace_app_path(self.workspace, app, suffix)

    def endpoint(self, target):
        return self.path('api', 'v1/page/') + '?' + urlencode({'url': target})

    def get(self, target, **headers):
        return self.client.get(self.endpoint(target), **headers)

    def post(self, target, values, **headers):
        return self.client.post(self.endpoint(target), values, **headers)

    def test_catalogs_bootstrap_json_for_plain_scoped_list_and_grid(self):
        for base in (self.path(), '/documents/', self.path('office'), '/office/'):
            for suffix in ('', '?display=grid'):
                with self.subTest(url=base+suffix):
                    response = self.get(base+suffix)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()['type'], 'document-directory')
                    self.assertNotIn('html', response.json())
                    self.assertEqual(response['Cache-Control'], 'no-store')
                    self.assertContains(self.client.get(base+suffix, follow=True), 'data-react-root="page"')

    def test_catalog_contract_preserves_colors_recursive_totals_and_location(self):
        index = self.get(self.path()).json()['data']
        row = next(row for row in index['rows'] if row['id'] == str(self.library.pk))
        self.assertEqual(row['color'], '#123456')
        files = self.get(self.path() + f'?library={self.library.pk}').json()['data']
        self.assertEqual(files['rows'][0]['row_kind'], 'folder')
        self.assertTrue(files['rows'][0]['has_files'])
        self.assertEqual(files['rows'][0]['size'], row['size'])
        self.assertEqual(files['rows'][0]['location'], f'library:{self.library.pk}')
        nested = self.get(self.path()+f'?library={self.library.pk}&folder={self.child.pk}').json()['data']
        self.assertEqual([crumb['name'] for crumb in nested['breadcrumbs']], ['Produkt', 'Umowy', 'Podfolder'])
        self.assertEqual(nested['rows'][0]['variant'], 'text')
        encoded = json.dumps(nested)
        self.assertNotIn(self.storage.location, encoded)
        self.assertNotIn(self.document.file.name, encoded)

    def test_search_filters_sort_pagination_and_display_session(self):
        DocumentLibrary.objects.bulk_create([DocumentLibrary(owner=self.owner, workplace=self.workspace, name=f'Raport {i:02}') for i in range(31)])
        data = self.get(self.path()+'?q=Raport&page_size=10&page=2&sort=name_desc&display=grid').json()['data']
        self.assertEqual((len(data['rows']), data['window']['page'], data['display']), (10, 2, 'grid'))
        self.assertIn('q=Raport', data['window']['next_url'])
        self.assertEqual(self.get(self.path()).json()['data']['display'], 'grid')
        target = self.path()+f'?library={self.library.pk}&name_op=is_not_empty&file_type=.txt&sort=size_desc'
        data = self.get(target).json()['data']
        self.assertEqual([row['id'] for row in data['rows']], [str(self.document.pk)])
        self.assertEqual(data['active_filters'], 2)
        self.assertEqual(data['sort'], 'size_desc')
        self.assertEqual(self.get(self.path()+f'?library={self.library.pk}&name=brak').json()['data']['rows'], [])

    def test_library_and_folder_forms_validate_duplicates_and_keep_color(self):
        create = self.path('documents', 'libraries/create/')
        form = self.get(create, HTTP_X_DOCUMENT_MODAL='true').json()
        self.assertEqual(form['type'], 'document-form')
        self.assertEqual(form['data']['color_kind'], 'library')
        invalid = self.post(create, {'name': 'produkt', 'color': '#aabbcc', 'description': 'Szkic'})
        self.assertEqual(invalid.status_code, 400)
        self.assertTrue(invalid.json()['data']['form']['fields'][0]['errors'])
        self.assertEqual(invalid.json()['data']['form']['fields'][1]['value'], '#aabbcc')
        self.assertEqual(self.post(create, {'name': 'Nowy dysk', 'color': '#aabbcc'}).status_code, 200)
        library = DocumentLibrary.objects.get(name='Nowy dysk')
        self.assertEqual((library.owner_id, library.workplace_id, library.color), (self.owner.pk, self.workspace.pk, '#aabbcc'))
        create = self.path('documents', 'folders/create/')+f'?library={library.pk}'
        self.assertEqual(self.post(create, {'name': '../Nie', 'color': '#ffd855'}).status_code, 400)
        self.assertEqual(self.post(create, {'name': 'Nowy folder', 'color': '#654321'}).status_code, 200)
        folder = Folder.objects.get(name='Nowy folder')
        self.assertEqual((folder.owner_id, folder.library_id, folder.color), (self.owner.pk, library.pk, '#654321'))

    def test_upload_uses_original_signature_limits_and_private_storage(self):
        target = self.path('documents', 'upload/')+f'?library={self.library.pk}&folder={self.folder.pk}'
        invalid = self.post(target, {'files': SimpleUploadedFile('zly.png', b'not an image')})
        self.assertEqual(invalid.status_code, 400)
        self.assertTrue(invalid.json()['data']['upload'])
        before = Document.objects.count()
        self.assertEqual(self.post(target, {'files': [SimpleUploadedFile(f'{i}.txt', b'QA') for i in range(21)]}).status_code, 400)
        self.assertEqual(Document.objects.count(), before)
        response = self.post(target, {'files': [SimpleUploadedFile('pierwszy.txt', b'QA'), SimpleUploadedFile('drugi.txt', b'Drugi')]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Document.objects.filter(folder=self.folder).count(), 2)
        item = Document.objects.get(filename='pierwszy.txt')
        self.assertEqual(item.owner_id, self.owner.pk)
        self.assertTrue(self.storage.exists(item.file.name))
        download = self.client.get(self.path('documents', f'{item.pk}/download/'))
        self.assertEqual(b''.join(download.streaming_content), b'QA')
        self.assertEqual(download['Cache-Control'], 'private, no-store')

    def test_move_keeps_domain_subtree_guards_and_current_return_location(self):
        target = self.path('documents', f'folders/{self.folder.pk}/move/')
        options = self.get(target).json()['data']['form']['fields'][0]['choices']
        self.assertNotIn(f'folder:{self.child.pk}', [option['value'] for option in options])
        invalid = self.post(target, {'target': f'folder:{self.child.pk}'}, HTTP_X_DOCUMENT_MOVE='true')
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('podfolderu', invalid.json()['data']['form']['fields'][0]['errors'][0])
        self.assertEqual(self.post(target, {'target': f'library:{self.second.pk}'}).status_code, 200)
        self.document.refresh_from_db()
        self.child.refresh_from_db()
        self.assertEqual((self.document.library_id, self.child.library_id), (self.second.pk, self.second.pk))
        self.assertEqual(self.document.revision, 2)

    def test_metadata_cannot_select_foreign_library_or_overwrite_editor_revision(self):
        target = self.path('documents', f'{self.document.pk}/')
        data = self.get(target).json()['data']
        self.assertFalse(any(field['name'] in {'owner', 'workplace', 'file', 'tags', 'revision'} for field in data['form']['fields']))
        self.assertEqual(self.post(target, {'title': 'X', 'folder': '99999'}).status_code, 400)
        Document.objects.filter(pk=self.document.pk).update(revision=7)
        self.assertEqual(self.post(target, {'title': 'Nowa nazwa', 'description': 'Opis', 'folder': self.folder.pk}).status_code, 200)
        self.document.refresh_from_db()
        self.assertEqual((self.document.revision, self.document.folder_id), (7, self.folder.pk))

    def test_preview_is_bounded_data_with_controlled_urls_and_archive_entries(self):
        data = self.get(self.path('documents', f'{self.document.pk}/preview/')).json()['data']
        self.assertEqual(data['preview']['kind'], 'text')
        self.assertIn('<script>nie wykonuj</script>', data['preview']['text'])
        self.assertNotIn('html', data)
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('instrukcja.txt', 'Zawartość')
        self.document.filename = 'archiwum.zip'
        self.document.file.save('archiwum.zip', ContentFile(buffer.getvalue()))
        result = self.get(self.path('documents', f'{self.document.pk}/preview/')).json()['data']
        self.assertEqual(result['preview']['kind'], 'archive')
        self.assertEqual(result['preview']['entries'][0]['name'], 'instrukcja.txt')

    def test_star_trash_restore_preserve_filters_and_invalidate_office_session(self):
        values = {'scope': 'workspace', 'view': 'starred', 'name': 'Instr', 'name_op': 'contains', 'display': 'grid', 'page_size': 25}
        response = self.post(self.path('documents', f'{self.document.pk}/star/'), values)
        self.assertIn('name=Instr', response.json()['redirect'])
        self.assertNotIn('library=', response.json()['redirect'])
        self.document.refresh_from_db()
        self.assertTrue(self.document.is_starred)
        key = self.document.office_key
        self.assertEqual(self.post(self.path('documents', f'{self.document.pk}/trash/'), values).status_code, 200)
        self.assertEqual(self.get(self.path('documents', f'{self.document.pk}/preview/')).status_code, 404)
        self.document.refresh_from_db()
        self.assertNotEqual(self.document.office_key, key)
        trash = self.get(self.path()+'?scope=workspace&view=trash').json()['data']
        row = next(row for row in trash['rows'] if row['id'] == str(self.document.pk))
        self.assertTrue(row['restore_url'])
        self.assertTrue(all(not row[name] for name in ('edit_url', 'preview_url', 'editor_url', 'download_url', 'star_url', 'trash_url', 'move_url')))
        self.assertEqual(self.post(self.path('documents', f'{self.document.pk}/restore/'), {'view': 'trash'}).status_code, 200)
        self.document.refresh_from_db()
        self.assertIsNone(self.document.deleted_at)

    def test_nonempty_drive_and_folder_deletion_keep_all_content(self):
        self.assertEqual(self.post(self.path('documents', f'libraries/{self.library.pk}/delete/'), {}).status_code, 200)
        self.assertEqual(self.post(self.path('documents', f'folders/{self.folder.pk}/delete/'), {}).status_code, 200)
        self.assertTrue(DocumentLibrary.objects.filter(pk=self.library.pk).exists())
        self.assertTrue(Folder.objects.filter(pk=self.folder.pk).exists())
        self.assertTrue(Document.objects.filter(pk=self.document.pk).exists())

    def test_office_create_all_types_returns_editor_separately_without_duplicate_storage(self):
        for kind in ('word', 'cell', 'slide', 'pdf', 'form', 'board'):
            response = self.post(self.path('office', 'create/'), {'kind': kind, 'title': f'Nowy {kind}'}, HTTP_X_DOCUMENT_MODAL='true')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['redirect'], self.path('office'))
            item = WorkspaceDocument.objects.get(title=f'Nowy {kind}')
            self.assertEqual(item.owner_id, self.owner.pk)
            self.assertEqual(response.json()['editor_url'], self.path('office', f'{item.pk}/editor/'))
            if kind != 'board':
                self.assertTrue(self.storage.exists(item.file.name))

    def test_office_upload_templates_and_copy_are_independent(self):
        upload = SimpleUploadedFile('Wzor.docx', blank_file('word').read())
        self.assertEqual(self.post(self.path('office', 'upload/'), {'files': upload}).status_code, 200)
        item = WorkspaceDocument.objects.get(filename='Wzor.docx')
        self.assertEqual(self.post(self.path('office', f'{item.pk}/template/'), {'return_query': 'view=templates&q=Wzor'}).status_code, 200)
        original = self.storage.open(item.file.name).read()
        response = self.post(self.path('office', 'templates/create/'), {'template': item.pk, 'title': 'Kopia szablonu'})
        self.assertEqual(response.status_code, 200)
        copy = WorkspaceDocument.objects.get(title='Kopia szablonu')
        self.assertNotEqual((copy.pk, copy.office_key, copy.file.name), (item.pk, item.office_key, item.file.name))
        self.assertFalse(copy.is_template)
        self.assertEqual(self.storage.open(copy.file.name).read(), original)
        self.assertIn('editor_url', response.json())
        WorkspaceDocument.objects.filter(pk=item.pk).update(revision=item.revision + 1)
        stale = self.post(self.path('office', f'{item.pk}/'), {'title': 'Stary szkic', 'revision': item.revision})
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()['type'], 'document-form')
        self.assertTrue(stale.json()['data']['form']['errors'])
        item.refresh_from_db()
        self.assertEqual(item.title, 'Wzor.docx')
        invalid = self.post(self.path('office', 'templates/create/'), {'template': self.document.pk, 'title': 'Nie'})
        self.assertEqual(invalid.status_code, 400)

    def test_legacy_text_saves_clean_content_and_rejects_stale_revision(self):
        target = self.path('office', f'{self.text.pk}/')
        self.assertEqual(self.get(target).json()['type'], 'office-text')
        result = self.post(target, {'title': 'React tekst', 'content': '<p onclick="x()"><b>Treść</b></p><script>x()</script>', 'revision': 1})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['revision'], 2)
        self.text.refresh_from_db()
        self.assertIn('<strong>Treść</strong>', self.text.content)
        self.assertNotIn('onclick', self.text.content)
        self.assertNotIn('<script>', self.text.content)
        conflict = self.post(target, {'title': 'Stary szkic', 'content': '<p>Stara treść</p>', 'revision': 1})
        self.assertEqual(conflict.status_code, 409)
        self.assertIn('__all__', conflict.json()['errors'])
        self.text.refresh_from_db()
        self.assertEqual(self.text.title, 'React tekst')
        self.assertEqual(self.get(self.path('office', 'create/text/')).json()['type'], 'office-text')

    @override_settings(ONLYOFFICE_URL='', ONLYOFFICE_JWT_SECRET='')
    def test_suite_unavailable_board_and_rename_keep_file_and_revision(self):
        self.post(self.path('office', 'create/'), {'kind': 'word', 'title': 'Edytor'})
        item = WorkspaceDocument.objects.get(title='Edytor')
        data = self.get(self.path('office', f'{item.pk}/editor/')).json()['data']
        self.assertIsNone(data['editor_config'])
        self.assertFalse(data['drive'])
        key, revision, filename = item.office_key, item.revision, item.filename
        self.assertEqual(self.post(self.path('office', f'{item.pk}/rename/'), {'title': 'Nowa nazwa'}).json()['title'], 'Nowa nazwa')
        item.refresh_from_db()
        self.assertEqual((item.office_key, item.revision, item.filename), (key, revision, filename))
        self.assertEqual(self.post(self.path('office', f'{item.pk}/rename/'), {'title': ''}).status_code, 400)
        self.post(self.path('office', 'create/'), {'kind': 'board', 'title': 'Tablica'})
        board = WorkspaceDocument.objects.get(title='Tablica')
        self.assertEqual(self.get(self.path('office', f'{board.pk}/editor/')).json()['data']['board_url'], self.path('office', f'{board.pk}/board/'))
        self.document.filename = 'plik.docx'
        self.document.save()
        drive = self.get(self.path('documents', f'{self.document.pk}/editor/')).json()['data']
        self.assertTrue(drive['drive'])
        self.assertIn(f'folder={self.child.pk}', drive['back_url'])

    def test_member_scope_revocation_auth_csrf_methods_and_protected_downloads(self):
        encoded = json.dumps(self.get(self.path()).json(), ensure_ascii=False)
        self.assertNotIn(self.foreign.name, encoded)
        for target in (self.path()+f'?library={self.foreign.pk}', self.path('documents', f'libraries/{self.foreign.pk}/edit/')):
            self.assertEqual(self.get(target).status_code, 404)
        foreign_path = scoped_workplace_app_path(self.other, 'documents')
        self.assertEqual(self.get(foreign_path).status_code, 403)
        guarded = Client(enforce_csrf_checks=True)
        self.login(self.member, guarded)
        self.assertEqual(guarded.post(self.endpoint(self.path('documents', 'libraries/create/')), {'name': 'Nie'}).status_code, 403)
        self.assertEqual(self.get(self.path('documents', f'{self.document.pk}/trash/')).status_code, 405)
        self.assertEqual(self.get(self.path('documents', f'{self.document.pk}/download/')).status_code, 404)
        self.assertEqual(self.get(self.path('documents', f'{self.document.pk}/history/')).status_code, 404)
        self.assertEqual(self.get(self.path('office', f'{self.text.pk}/board/save/')).status_code, 404)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).delete()
        self.assertEqual(self.get(self.path()).status_code, 403)
        self.assertEqual(self.client.get(self.path('documents', f'{self.document.pk}/download/')).status_code, 302)
        self.client.logout()
        self.assertEqual(self.get(self.path()).status_code, 401)
