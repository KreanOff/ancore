import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from tasks.models import TaskTag
from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Document, DocumentLibrary, Folder


class DocumentLibraryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='documents-user', email='documents@example.com', password='test-pass-123')
        cls.other = get_user_model().objects.create_user(username='documents-other', email='other-documents@example.com', password='test-pass-123')
        cls.workspace = create_workplace_for_user(cls.user, 'Dokumenty testowe')
        cls.other_workspace = create_workplace_for_user(cls.user, 'Drugi Workspace')
        cls.foreign_workspace = create_workplace_for_user(cls.other, 'Obcy Workspace')
        cls.base = scoped_workplace_app_path(cls.workspace, 'documents')
        cls.primary_library = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workspace, name='Dokumenty zespołu')
        cls.secondary_library = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workspace, name='Materiały klientów')
        cls.other_library = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.other_workspace, name='Inna biblioteka')
        cls.foreign_library = DocumentLibrary.objects.create(owner=cls.other, workplace=cls.foreign_workspace, name='Obca biblioteka')
        cls.library_url = f'{cls.base}?library={cls.primary_library.pk}'
        cls.upload_url = f'{cls.base}upload/?library={cls.primary_library.pk}'
        cls.folder_create_url = f'{cls.base}folders/create/?library={cls.primary_library.pk}'

    def setUp(self):
        self.storage_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage_dir.cleanup)
        field = Document._meta.get_field('file')
        self.addCleanup(setattr, field, 'storage', field.storage)
        field.storage = FileSystemStorage(self.storage_dir.name)
        self.client.force_login(self.user)

    def test_workspace_deletion_cascades_through_document_folders(self):
        parent = Folder.objects.create(owner=self.user, workplace=self.workspace, library=self.primary_library, name='Parent')
        child = Folder.objects.create(owner=self.user, workplace=self.workspace, library=self.primary_library, parent=parent, name='Child')
        self.document(folder=child)
        self.workspace.delete()
        self.assertFalse(Document.objects.exists())
        self.assertFalse(Folder.objects.exists())

    def upload(self, name='Instrukcja.txt', body=b'Tresc dokumentu', folder=None):
        url = self.upload_url + (f'&folder={folder.pk}' if folder else '')
        return self.client.post(url, {'files': SimpleUploadedFile(name, body)})

    def document(self, **kwargs):
        defaults = {'owner': self.user, 'workplace': self.workspace, 'title': 'Dokument', 'filename': 'Dokument.txt'}
        defaults.update(kwargs)
        if 'library' not in defaults:
            defaults['library'] = DocumentLibrary.objects.filter(owner=defaults['owner'], workplace=defaults['workplace']).first()
        return Document.objects.create(**defaults)

    def test_library_requires_login(self):
        self.assertRedirects(Client().get(self.base), f'{reverse("login")}?next={self.base}', fetch_redirect_response=False)

    def test_empty_library_and_navigation(self):
        response = self.client.get(self.library_url)
        self.assertContains(response, 'Ta biblioteka jest pusta')
        self.assertContains(response, 'data-sidebar-source-item="documents"')
        self.assertContains(response, self.upload_url)

    def test_form_links_render_dialogs_over_their_document_list(self):
        folder = Folder.objects.create(owner=self.user, workplace=self.workspace, library=self.primary_library, name='Umowy')
        document = self.document(folder=folder)
        urls = [
            f'{self.base}libraries/create/', f'{self.base}libraries/{self.primary_library.pk}/edit/',
            self.folder_create_url, f'{self.base}folders/{folder.pk}/edit/',
            f'{self.upload_url}&folder={folder.pk}', f'{self.base}{document.pk}/',
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'data-document-dialog')
                self.assertContains(response, 'documents-table')
                self.assertEqual(response.context['document_form']['form_action'], url)
                fragment = self.client.get(url, headers={'X-Document-Modal': 'true'})
                self.assertContains(fragment, 'data-document-dialog')
                self.assertNotContains(fragment, '<html')
                self.assertNotContains(fragment, 'documents-table')

    def test_modal_validation_keeps_errors_and_submitted_values(self):
        response = self.client.post(f'{self.base}libraries/create/', {
            'name': self.primary_library.name, 'description': 'Zachowaj ten opis',
        }, headers={'X-Document-Modal': 'true'})
        self.assertContains(response, 'Biblioteka o tej nazwie już istnieje')
        self.assertContains(response, 'Zachowaj ten opis')
        self.assertContains(response, 'data-document-dialog')
        self.assertNotContains(response, '<html')
        self.assertEqual(DocumentLibrary.objects.filter(workplace=self.workspace).count(), 2)

    def test_modal_save_returns_location_and_persists_changes(self):
        header = {'X-Document-Modal': 'true'}
        response = self.client.post(f'{self.base}libraries/{self.primary_library.pk}/edit/', {'name': 'Nowa nazwa'}, headers=header)
        self.assertEqual(response.json(), {'redirect_url': self.library_url})
        self.primary_library.refresh_from_db()
        self.assertEqual(self.primary_library.name, 'Nowa nazwa')
        response = self.client.post(self.folder_create_url, {'name': 'Umowy'}, headers=header)
        self.assertEqual(response.json(), {'redirect_url': self.library_url})
        folder = Folder.objects.get(name='Umowy')
        response = self.client.post(f'{self.upload_url}&folder={folder.pk}', {'files': SimpleUploadedFile('A.txt', b'Alpha')}, headers=header)
        self.assertEqual(response.json(), {'redirect_url': f'{self.library_url}&folder={folder.pk}'})
        document = Document.objects.get(filename='A.txt')
        response = self.client.post(f'{self.base}{document.pk}/', {'title': 'Zmieniony dokument', 'folder': ''}, headers=header)
        self.assertEqual(response.json(), {'redirect_url': self.library_url})
        document.refresh_from_db()
        self.assertEqual(document.title, 'Zmieniony dokument')
        self.assertIsNone(document.folder)

    def test_modal_requests_keep_owner_and_workspace_restrictions(self):
        for item in [self.other_library, self.foreign_library]:
            for method in ['get', 'post']:
                with self.subTest(library=item.pk, method=method):
                    response = getattr(self.client, method)(f'{self.base}libraries/{item.pk}/edit/', headers={'X-Document-Modal': 'true'})
                    self.assertEqual(response.status_code, 404)

    def test_multiple_uploads_and_authenticated_download(self):
        response = self.client.post(self.upload_url, {'files': [SimpleUploadedFile('A.txt', b'Alpha'), SimpleUploadedFile('B.txt', b'Beta')]})
        self.assertRedirects(response, self.library_url)
        self.assertEqual(Document.objects.count(), 2)
        document = Document.objects.get(filename='A.txt')
        response = self.client.get(f'{self.base}{document.pk}/download/')
        self.assertEqual(b''.join(response.streaming_content), b'Alpha')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertTrue(Path(document.file.path).is_relative_to(self.storage_dir.name))

    def test_all_uploads_are_validated_before_saving(self):
        response = self.client.post(self.upload_url, {'files': [SimpleUploadedFile('A.txt', b'Alpha'), SimpleUploadedFile('bad.pdf', b'not a pdf')]})
        self.assertContains(response, 'nieprawidłową zawartość')
        self.assertEqual(Document.objects.count(), 0)
        self.assertEqual(list(Path(self.storage_dir.name).rglob('*')), [])

    def test_upload_rejects_empty_disallowed_and_oversized_files(self):
        for name, content in [('empty.txt', b''), ('bad.html', b'<html>test</html>')]:
            with self.subTest(name=name):
                self.assertEqual(self.upload(name, content).status_code, 200)
        with override_settings(MAX_ATTACHMENT_SIZE=4):
            self.assertEqual(self.upload(body=b'12345').status_code, 200)
        self.assertEqual(Document.objects.count(), 0)

    def test_create_nested_folder_and_upload(self):
        self.client.post(self.folder_create_url, {'name': 'Projekty'})
        parent = Folder.objects.get(name='Projekty')
        self.client.post(f'{self.folder_create_url}&folder={parent.pk}', {'name': 'Umowy'})
        child = Folder.objects.get(name='Umowy')
        self.assertEqual(child.parent, parent)
        self.upload(folder=child)
        self.assertContains(self.client.get(f'{self.library_url}&folder={child.pk}'), 'Instrukcja.txt')
        self.assertNotContains(self.client.get(self.library_url), 'Instrukcja.txt')
        self.assertContains(self.client.get(f'{self.library_url}&q=Instrukcja'), 'Instrukcja.txt')

    def test_duplicate_folder_and_invalid_names_are_rejected(self):
        self.client.post(self.folder_create_url, {'name': 'Umowy'})
        for name in ['umowy', '..', 'a/b']:
            self.assertEqual(self.client.post(self.folder_create_url, {'name': name}).status_code, 200)
        self.assertEqual(Folder.objects.count(), 1)

    def test_folder_rename_and_nonempty_delete(self):
        folder = Folder.objects.create(owner=self.user, workplace=self.workspace, library=self.primary_library, name='Stary')
        self.client.post(f'{self.base}folders/{folder.pk}/edit/', {'name': 'Nowy'})
        folder.refresh_from_db()
        self.assertEqual(folder.name, 'Nowy')
        document = self.document(folder=folder)
        self.client.post(f'{self.base}folders/{folder.pk}/delete/')
        self.assertTrue(Folder.objects.filter(pk=folder.pk).exists())
        document.delete()
        self.client.post(f'{self.base}folders/{folder.pk}/delete/')
        self.assertFalse(Folder.objects.filter(pk=folder.pk).exists())

    def test_edit_move_tag_filter_and_star(self):
        self.upload()
        document = Document.objects.get()
        folder = Folder.objects.create(owner=self.user, workplace=self.workspace, library=self.primary_library, name='Umowy')
        tag = TaskTag.objects.create(user=self.user, workplace=self.workspace, name='Ważne')
        response = self.client.post(f'{self.base}{document.pk}/', {'title': 'Zmieniona nazwa', 'description': 'Opis', 'folder': folder.pk, 'tags': [tag.pk]})
        self.assertRedirects(response, f'{self.library_url}&folder={folder.pk}')
        document.refresh_from_db()
        self.assertEqual(document.folder, folder)
        self.assertEqual(document.tags.get(), tag)
        self.assertContains(self.client.get(f'{self.library_url}&tag={tag.pk}'), 'Zmieniona nazwa')
        self.client.post(f'{self.base}{document.pk}/star/')
        self.assertContains(self.client.get(f'{self.library_url}&view=starred'), 'Zmieniona nazwa')
        self.client.post(f'{self.base}{document.pk}/star/')
        self.assertNotContains(self.client.get(f'{self.library_url}&view=starred'), 'Zmieniona nazwa')

    def test_trash_restore_and_download_restriction(self):
        self.upload()
        document = Document.objects.get()
        self.client.post(f'{self.base}{document.pk}/trash/')
        self.assertNotContains(self.client.get(self.library_url), document.title)
        self.assertContains(self.client.get(f'{self.library_url}&view=trash'), document.title)
        self.assertEqual(self.client.get(f'{self.base}{document.pk}/download/').status_code, 404)
        self.client.post(f'{self.base}{document.pk}/restore/')
        self.assertContains(self.client.get(self.library_url), document.title)

    def test_workspace_and_owner_isolation_for_all_actions(self):
        for owner, workplace in [(self.user, self.other_workspace), (self.other, self.foreign_workspace)]:
            with self.subTest(workplace=workplace):
                document = self.document(owner=owner, workplace=workplace, title='Ukryty dokument')
                folder = Folder.objects.create(owner=owner, workplace=workplace, library=document.library, name='Ukryty folder')
                self.assertNotContains(self.client.get(self.library_url), 'Ukryty')
                for suffix in ['', 'download/']:
                    self.assertEqual(self.client.get(f'{self.base}{document.pk}/{suffix}').status_code, 404)
                for suffix in ['', 'trash/', 'restore/', 'star/']:
                    self.assertEqual(self.client.post(f'{self.base}{document.pk}/{suffix}').status_code, 404)
                self.assertEqual(self.client.post(f'{self.base}upload/?folder={folder.pk}', {'files': SimpleUploadedFile('A.txt', b'test')}).status_code, 404)
                self.assertEqual(self.client.get(f'{self.library_url}&folder={folder.pk}').status_code, 404)
                self.assertEqual(self.client.post(f'{self.base}folders/{folder.pk}/delete/').status_code, 404)

    def test_cannot_assign_foreign_folder_or_tags(self):
        document = self.document()
        folder = Folder.objects.create(owner=self.user, workplace=self.other_workspace, library=self.other_library, name='Inny')
        tag = TaskTag.objects.create(user=self.other, workplace=self.foreign_workspace, name='Obcy')
        response = self.client.post(f'{self.base}{document.pk}/', {'title': 'Zmiana', 'folder': folder.pk, 'tags': [tag.pk]})
        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertEqual(document.title, 'Dokument')
        self.assertIsNone(document.folder_id)
        self.assertFalse(document.tags.exists())

    def test_mutations_require_post_and_csrf(self):
        document = self.document()
        for suffix in ['star/', 'trash/', 'restore/']:
            self.assertEqual(self.client.get(f'{self.base}{document.pk}/{suffix}').status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(f'{self.base}{document.pk}/trash/').status_code, 403)

    def test_pagination_includes_folders_and_documents_without_duplicates(self):
        Folder.objects.bulk_create([Folder(owner=self.user, workplace=self.workspace, library=self.primary_library, name=f'Folder {i:02}') for i in range(28)])
        for i in range(3):
            self.document(title=f'Plik {i}')
        first = self.client.get(f'{self.library_url}&page_size=25').context['rows']
        second_page = self.client.get(f'{self.library_url}&page=2&page_size=25')
        second = second_page.context['rows']
        self.assertIn('page_size=25', second_page.context['document_window']['previous_url'])
        self.assertEqual(len(first), 25)
        self.assertEqual(len(second), 6)
        self.assertEqual(len({str(row['item'].pk) for row in first + second}), 31)

    def test_search_ignores_trash_and_other_workspaces(self):
        self.document(title='Umowa aktywna')
        self.document(title='Umowa obca', workplace=self.other_workspace)
        deleted = self.document(title='Umowa usunięta')
        self.client.post(f'{self.base}{deleted.pk}/trash/')
        response = self.client.get(reverse('global_search'), {'q': 'Umowa'})
        self.assertContains(response, 'Umowa aktywna')
        self.assertNotContains(response, 'Umowa obca')
        self.assertNotContains(response, 'Umowa usuni')

    def test_invalid_folder_returns_404(self):
        self.assertEqual(self.client.get(self.base, {'folder': 'abc'}).status_code, 404)
        self.assertEqual(self.client.get(f'{self.library_url}&tag=abc').status_code, 404)

    def test_nested_destination_folder_has_full_path(self):
        document = self.document()
        parent = Folder.objects.create(owner=self.user, workplace=self.workspace, library=self.primary_library, name='Projekty')
        Folder.objects.create(owner=self.user, workplace=self.workspace, library=self.primary_library, parent=parent, name='Umowy')
        response = self.client.get(f'{self.base}{document.pk}/')
        self.assertContains(response, 'Projekty / Umowy')

    def test_upload_batch_limit(self):
        response = self.client.post(self.upload_url, {'files': [SimpleUploadedFile(f'{i}.txt', b'test') for i in range(21)]})
        self.assertContains(response, 'maksymalnie 20 plików')
        self.assertFalse(Document.objects.exists())

    def test_index_lists_libraries_without_exposing_contents(self):
        self.document(title='Poufny plik zespołu')
        Folder.objects.create(owner=self.user, workplace=self.workspace, library=self.primary_library, name='Wewnętrzny folder')
        response = self.client.get(self.base)
        self.assertEqual(list(response.context['libraries']), [self.primary_library, self.secondary_library])
        self.assertContains(response, 'Biblioteki dokumentów')
        self.assertNotContains(response, 'Poufny plik zespołu')
        self.assertNotContains(response, 'Wewnętrzny folder')
        self.assertNotContains(response, 'documents-rail')
        self.assertNotContains(response, self.other_library.name)
        self.assertNotContains(response, self.foreign_library.name)

    def test_library_create_edit_duplicate_names_and_empty_delete(self):
        response = self.client.post(f'{self.base}libraries/create/', {'name': 'Nowa biblioteka', 'description': 'Materiały projektu'})
        item = DocumentLibrary.objects.get(name='Nowa biblioteka')
        self.assertRedirects(response, f'{self.base}?library={item.pk}')
        self.assertEqual((item.owner, item.workplace), (self.user, self.workspace))
        duplicate = self.client.post(f'{self.base}libraries/create/', {'name': 'nowa biblioteka'})
        self.assertContains(duplicate, 'Biblioteka o tej nazwie już istnieje')
        self.client.post(f'{self.base}libraries/{item.pk}/edit/', {'name': 'Archiwum', 'description': 'Zamknięte projekty'})
        item.refresh_from_db()
        self.assertEqual(item.name, 'Archiwum')
        response = self.client.get(self.base, {'q': 'Zamknięte'})
        self.assertEqual(list(response.context['libraries']), [item])
        self.assertEqual(self.client.get(f'{self.base}libraries/{item.pk}/delete/').status_code, 405)
        self.client.post(f'{self.base}libraries/{item.pk}/delete/')
        self.assertFalse(DocumentLibrary.objects.filter(pk=item.pk).exists())

    def test_library_cannot_be_deleted_with_files_including_trash_or_folders(self):
        document = self.document()
        url = f'{self.base}libraries/{self.primary_library.pk}/delete/'
        self.client.post(url)
        self.assertTrue(DocumentLibrary.objects.filter(pk=self.primary_library.pk).exists())
        self.client.post(f'{self.base}{document.pk}/trash/')
        self.client.post(url)
        self.assertTrue(DocumentLibrary.objects.filter(pk=self.primary_library.pk).exists())
        document.delete()
        Folder.objects.create(owner=self.user, workplace=self.workspace, library=self.primary_library, name='Pusty folder')
        self.client.post(url)
        self.assertTrue(DocumentLibrary.objects.filter(pk=self.primary_library.pk).exists())

    def test_all_content_views_and_search_are_scoped_to_library(self):
        from django.utils import timezone
        tag = TaskTag.objects.create(user=self.user, workplace=self.workspace, name='Wspólny tag')
        for library, title in [(self.primary_library, 'Plik widoczny'), (self.secondary_library, 'Plik drugiej biblioteki')]:
            document = self.document(library=library, title=title, is_starred=True)
            document.tags.add(tag)
            self.document(library=library, title=f'{title} w koszu', deleted_at=timezone.now())
        for params in ['', '&q=Plik', '&view=recent', '&view=starred', '&view=trash', f'&tag={tag.pk}']:
            response = self.client.get(self.library_url + params)
            self.assertContains(response, 'Plik widoczny')
            self.assertNotContains(response, 'Plik drugiej biblioteki')

    def test_cross_library_folder_is_rejected_and_names_can_repeat_between_libraries(self):
        self.client.post(self.folder_create_url, {'name': 'Umowy'})
        response = self.client.post(f'{self.base}folders/create/?library={self.secondary_library.pk}', {'name': 'Umowy'})
        self.assertEqual(response.status_code, 302)
        folder = Folder.objects.get(library=self.secondary_library, name='Umowy')
        self.assertEqual(self.client.get(f'{self.library_url}&folder={folder.pk}').status_code, 404)
        self.assertEqual(self.upload(folder=folder).status_code, 404)
        self.assertEqual(self.client.post(f'{self.folder_create_url}&folder={folder.pk}', {'name': 'Niepoprawny'}).status_code, 404)
        document = self.document()
        response = self.client.post(f'{self.base}{document.pk}/', {'title': 'Przeniesiony', 'folder': folder.pk})
        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertIsNone(document.folder_id)
        self.assertEqual(document.library, self.primary_library)

    def test_library_is_required_for_new_content_and_foreign_libraries_are_inaccessible(self):
        for parameter in ['', '?library=abc', '?library=99999999', f'?library={self.other_library.pk}', f'?library={self.foreign_library.pk}']:
            self.assertEqual(self.client.get(f'{self.base}upload/{parameter}').status_code, 404)
            self.assertEqual(self.client.post(f'{self.base}folders/create/{parameter}', {'name': 'Folder'}).status_code, 404)
        for library in [self.other_library, self.foreign_library]:
            self.assertEqual(self.client.get(f'{self.base}?library={library.pk}').status_code, 404)
            self.assertEqual(self.client.post(f'{self.base}libraries/{library.pk}/edit/', {'name': 'Zmiana'}).status_code, 404)
            self.assertEqual(self.client.post(f'{self.base}libraries/{library.pk}/delete/').status_code, 404)
        self.assertFalse(Folder.objects.exists())

    def test_legacy_folder_link_redirects_to_its_library(self):
        folder = Folder.objects.create(owner=self.user, workplace=self.workspace, library=self.primary_library, name='Stary folder')
        self.assertRedirects(self.client.get(f'{self.base}?folder={folder.pk}'), f'{self.base}?folder={folder.pk}&library={self.primary_library.pk}')

    def test_global_search_links_libraries_and_folders_with_library_context(self):
        folder = Folder.objects.create(owner=self.user, workplace=self.workspace, library=self.primary_library, name='Materiały dla zespołu')
        response = self.client.get(self.library_url)
        response = self.client.get(reverse('global_search'), {'q': 'zespołu'})
        results = [item for group in response.json()['groups'] for item in group['results']]
        urls = [item['url'] for item in results]
        self.assertIn(self.library_url, urls)
        self.assertIn(f'{self.library_url}&folder={folder.pk}', urls)

    def test_workspace_sidebar_counts_and_links_include_all_libraries_and_ignore_search(self):
        from django.utils import timezone
        self.document(title='Widoczny', is_starred=True)
        self.document(library=self.secondary_library, title='Druga biblioteka')
        self.document(library=self.secondary_library, deleted_at=timezone.now(), is_starred=True)
        self.document(library=self.other_library, workplace=self.other_workspace, is_starred=True)
        self.document(library=self.foreign_library, workplace=self.foreign_workspace, owner=self.other)
        for url in [self.base, self.library_url, f'{self.library_url}&q=Nieistniejący']:
            response = self.client.get(url)
            views = {view['value']: view for view in response.context['sidebar_views']}
            self.assertEqual({key: value['count'] for key, value in views.items()}, {'all': 2, 'recent': None, 'starred': 1, 'trash': 1})
            self.assertEqual(views['starred']['url'], f'{self.base}?view=starred')
            self.assertEqual(list(response.context['sidebar_libraries']), [self.primary_library, self.secondary_library])
            self.assertContains(response, 'data-documents-sidebar')

    def test_workspace_document_views_include_nested_files_from_all_owned_libraries(self):
        from django.utils import timezone
        folder = Folder.objects.create(owner=self.user, workplace=self.workspace, library=self.secondary_library, name='Zagnieżdżony')
        active = self.document(title='Pierwszy', is_starred=True)
        nested = self.document(library=self.secondary_library, folder=folder, title='Drugi', is_starred=True)
        trashed = self.document(library=self.secondary_library, title='W koszu', deleted_at=timezone.now())
        self.document(workplace=self.other_workspace, library=self.other_library, title='Niedostępny')
        for view, expected in [('all', {active.pk, nested.pk}), ('recent', {active.pk, nested.pk}), ('starred', {active.pk, nested.pk}), ('trash', {trashed.pk})]:
            response = self.client.get(f'{self.base}?view={view}')
            self.assertEqual({row['item'].pk for row in response.context['rows']}, expected)
            self.assertTrue(all(row['kind'] == 'document' for row in response.context['rows']))
            self.assertEqual([item['value'] for item in response.context['sidebar_views'] if item['active']], [view])
            self.assertIsNone(response.context['current_library'])
            self.assertNotContains(response, 'Niedostępny')

    def test_workspace_view_search_tag_pagination_and_actions_keep_workspace_scope(self):
        self.upload()
        document = Document.objects.get()
        tag = TaskTag.objects.create(user=self.user, workplace=self.workspace, name='Wspólny')
        document.tags.add(tag)
        response = self.client.get(f'{self.base}?view=all&q=Instrukcja&tag={tag.pk}&page_size=10')
        self.assertEqual([row['item'].pk for row in response.context['rows']], [document.pk])
        self.assertContains(response, 'name="scope" value="workspace"')
        self.assertContains(response, f'{self.base}?view=all&amp;tag={tag.pk}')
        params = {'scope': 'workspace', 'view': 'all', 'q': 'Instrukcja', 'page_size': 10}
        response = self.client.post(f'{self.base}{document.pk}/star/', params)
        self.assertRedirects(response, f'{self.base}?view=all&q=Instrukcja&page_size=10')
        self.client.post(f'{self.base}{document.pk}/trash/', params)
        sidebar = self.client.get(self.library_url).context['sidebar_views']
        self.assertEqual({view['value']: view['count'] for view in sidebar}, {'all': 0, 'recent': None, 'starred': 0, 'trash': 1})
        response = self.client.post(f'{self.base}{document.pk}/restore/', {'scope': 'workspace', 'view': 'trash'})
        self.assertRedirects(response, f'{self.base}?view=trash')
        self.assertContains(self.client.get(f'{self.base}?view=all'), 'Instrukcja.txt')
