import json
import re
import tempfile
from io import BytesIO
from urllib.parse import parse_qs, urlencode, urlsplit
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
        self.assertTrue(index['libraries'])
        self.assertEqual(index['rows'], [])
        row = next(row for row in index['sidebar'] if row['id'] == str(self.library.pk))
        self.assertEqual(row['color'], '#123456')
        files = self.get(self.path() + f'?library={self.library.pk}').json()['data']
        self.assertEqual(files['rows'][0]['row_kind'], 'folder')
        self.assertTrue(files['rows'][0]['has_files'])
        self.assertEqual(files['rows'][0]['size'], '10\xa0bajtów')
        self.assertEqual(files['rows'][0]['location'], f'library:{self.library.pk}')
        nested = self.get(self.path()+f'?library={self.library.pk}&folder={self.child.pk}').json()['data']
        self.assertEqual([crumb['name'] for crumb in nested['breadcrumbs']], ['Produkt', 'Umowy', 'Podfolder'])
        self.assertEqual(nested['rows'][0]['variant'], 'text')
        encoded = json.dumps(nested)
        self.assertNotIn(self.storage.location, encoded)
        self.assertNotIn(self.document.file.name, encoded)

    def test_library_landing_ignores_old_table_queries_and_keeps_drives_only_in_sidebar(self):
        for base in (self.path(), '/documents/'):
            target = base + '?q=Nieistniejący&name=Inny&documents=no&sort=name_desc&display=grid&page=2'
            with self.subTest(target=target):
                data = self.get(target).json()['data']
                self.assertTrue(data['libraries'])
                self.assertEqual(data['rows'], [])
                self.assertEqual((data['window']['count'], data['window']['next_url']), (0, ''))
                self.assertEqual((data['query'], data['filters'], data['active_filters'], data['display_options']), ('', [], 0, []))
                self.assertEqual([row['id'] for row in data['sidebar']], [str(self.second.pk), str(self.library.pk)])
                response = self.client.get(target, follow=True)
                self.assertContains(response, '<h2>Wybierz dysk</h2>', html=True)
                self.assertContains(response, 'data-document-open-sidebar', count=1)
                self.assertContains(response, '<span>Nowy dysk</span>', html=True)
                self.assertNotContains(response, 'aria-label="Lista dysków"')
                self.assertNotContains(response, 'Dyski — kafelki')
                self.assertNotContains(response, 'documents-filterbar')
                self.assertNotContains(response, 'id="documents-search-form"')
                self.assertNotContains(response, 'Nie znaleziono dysków')

    def test_empty_library_landing_keeps_first_drive_and_create_form(self):
        self.workspace = create_workplace_for_user(self.owner, 'Pusty dysk')
        self.login(self.owner)
        base = self.path()
        data = self.get(base + '?q=Nieistniejący&display=grid').json()['data']
        self.assertEqual((data['rows'], data['sidebar'], data['sidebar_window']['count']), ([], [], 0))
        response = self.client.get(base + '?q=Nieistniejący')
        self.assertContains(response, 'Utwórz pierwszy dysk')
        self.assertContains(response, 'Brak dysków w tym Workspace.')
        self.assertNotContains(response, 'data-document-open-sidebar')
        response = self.client.get(base + 'libraries/create/')
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'data-documents-sidebar', count=1)
        self.assertNotContains(response, 'documents-filterbar')

    def test_every_drive_directory_uses_one_global_library_sidebar(self):
        suffixes = ('', f'?library={self.library.pk}', f'?library={self.library.pk}&folder={self.child.pk}',
                    '?view=all', '?view=recent', '?view=starred', '?view=trash')
        for base in ('/documents/', self.path()):
            for suffix in suffixes:
                with self.subTest(target=base + suffix):
                    data = self.get(base + suffix).json()['data']
                    self.assertEqual([row['id'] for row in data['sidebar']], [str(self.second.pk), str(self.library.pk)])
                    self.assertEqual(data['sidebar_window']['count'], 2)
                    self.assertEqual(data['sidebar'][1]['color'], '#123456')
                    response = self.client.get(base + suffix, follow=True)
                    self.assertContains(response, 'data-documents-sidebar', count=1)
                    self.assertContains(response, 'documents-sidebar--global', count=1)
                    self.assertNotContains(response, 'data-today-sidebar')
                    self.assertNotContains(response, 'data-documents-sidebar-toggle')
                    self.assertNotContains(response, 'data-documents-sidebar-close')
                    self.assertNotContains(response, 'data-documents-sidebar-backdrop')
                    self.assertNotContains(response, 'class="documents-layout"')
                    self.assertNotContains(response, self.foreign.name)
                    html = response.content.decode()
                    self.assertGreater(html.index('data-documents-sidebar'), html.index('id="app-right-sidebar-content"'))
                    script = re.search(r'<script[^>]+id="ancore-global-panels-data"[^>]*>(.*?)</script>', html, re.S)
                    self.assertEqual(json.loads(script.group(1))['shell']['sidebar_url'], '')
        office = self.get(self.path('office')).json()['data']
        self.assertIsNone(office['sidebar_window'])
        response = self.client.get(self.path('office'))
        self.assertContains(response, 'data-today-sidebar', count=1)
        self.assertNotContains(response, 'data-documents-sidebar')

    def test_library_sidebar_load_more_is_independent_and_retains_main_directory_state(self):
        DocumentLibrary.objects.bulk_create([
            DocumentLibrary(owner=self.owner, workplace=self.workspace, name=f'Raport {index:02}')
            for index in range(25)
        ])
        for params in (
            {'q': 'Produkt', 'sort': 'name_desc', 'display': 'grid', 'limit': '40'},
            {'library': str(self.library.pk), 'folder': str(self.child.pk), 'q': 'Instrukcja',
             'sort': 'name_desc', 'display': 'grid', 'limit': '40'},
        ):
            with self.subTest(params=params):
                data = self.get(self.path() + '?' + urlencode(params)).json()['data']
                self.assertEqual(len(data['sidebar']), 20)
                self.assertEqual(data['sidebar_window']['count'], 27)
                self.assertEqual(len(data['rows']), 1 if 'library' in params else 0)
                next_url = data['sidebar_window']['next_url']
                self.assertEqual(urlsplit(next_url).path, self.path())
                query = parse_qs(urlsplit(next_url).query)
                for key, value in params.items():
                    self.assertEqual(query[key], [value])
                self.assertEqual(query['sidebar_library_limit'], ['27'])
                loaded = self.get(next_url).json()['data']
                self.assertEqual(len(loaded['sidebar']), 27)
                self.assertEqual(len({row['id'] for row in loaded['sidebar']}), 27)
                self.assertEqual(loaded['rows'], data['rows'])
                self.assertFalse(loaded['sidebar_window']['has_next'])
                self.assertEqual(loaded['sidebar_window']['next_url'], '')
        data = self.get(self.path() + '?sidebar_library_page=2').json()['data']
        self.assertEqual(len(data['sidebar']), 27)
        self.assertEqual(data['rows'], [])

    def test_sidebar_expands_through_active_library_beyond_first_window(self):
        DocumentLibrary.objects.bulk_create([
            DocumentLibrary(owner=self.owner, workplace=self.workspace, name=f'Raport {index:02}')
            for index in range(45)
        ])
        active = DocumentLibrary.objects.get(owner=self.owner, workplace=self.workspace, name='Raport 24')
        initial = self.get(self.path()).json()['data']
        self.assertEqual(len(initial['sidebar']), 20)
        data = self.get(self.path() + f'?library={active.pk}').json()['data']
        self.assertEqual(len(data['sidebar']), 40)
        self.assertIn(str(active.pk), [row['id'] for row in data['sidebar']])
        self.assertEqual(data['library']['id'], str(active.pk))
        self.assertEqual(data['sidebar_window']['count'], 47)
        response = self.client.get(self.path() + f'?library={active.pk}')
        self.assertContains(response, 'documents-sidebar-library-link is-active')
        self.assertContains(response, f'aria-current="page" title="{active.name}"')

    def test_global_drive_sidebar_keeps_guest_scope_and_direct_form_fallback(self):
        response = self.client.get(self.path('documents', f'libraries/{self.library.pk}/edit/'))
        self.assertContains(response, 'data-documents-sidebar', count=1)
        self.assertNotContains(response, 'data-today-sidebar')
        self.assertContains(response, '"sidebar_url": ""')
        self.assertContains(response, 'Ustawienia dysku')
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).update(role='guest')
        data = self.get(self.path()).json()
        self.assertTrue(data['read_only'])
        self.assertEqual([row['id'] for row in data['data']['sidebar']], [str(self.second.pk), str(self.library.pk)])
        response = self.client.get(self.path())
        self.assertContains(response, 'data-documents-sidebar', count=1)
        self.assertNotContains(response, 'aria-label="Dodaj dysk"')
        self.assertNotContains(response, '<span>Nowy dysk</span>')
        self.assertEqual(self.post(self.path('documents', 'libraries/create/'), {'name': 'Nie'}).status_code, 403)

    def test_search_filters_sort_pagination_and_display_session(self):
        Document.objects.bulk_create([Document(owner=self.owner, workplace=self.workspace, library=self.library, title=f'Raport {i:02}', filename=f'raport{i}.txt') for i in range(51)])
        base = self.path() + f'?library={self.library.pk}'
        data = self.get(base + '&q=Raport&page_size=10&page=2&sort=name_desc&display=grid').json()['data']
        self.assertEqual((len(data['rows']), data['window']['page'], data['display']), (40, 2, 'grid'))
        self.assertIn('q=Raport', data['window']['next_url'])
        self.assertEqual(self.get(base).json()['data']['display'], 'grid')
        target = self.path()+f'?library={self.library.pk}&name_op=is_not_empty&file_type=.txt&sort=size_desc'
        data = self.get(target).json()['data']
        self.assertEqual(data['rows'][0]['id'], str(self.document.pk))
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
        self.assertTrue(self.document.favorited_by.filter(pk=self.member.pk).exists())
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
