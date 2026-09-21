"""Inline title changes leave the open editor's content and session untouched."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from . import office_service
from .models import Document, DocumentLibrary, Folder, WorkspaceDocument


@override_settings(ONLYOFFICE_URL='')
class EditorRenameTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='rename-owner', email='rename-owner@example.test')
        cls.other = get_user_model().objects.create_user(username='rename-other', email='rename-other@example.test')
        cls.workplace = create_workplace_for_user(cls.user, 'Zmiana nazwy')
        cls.second = create_workplace_for_user(cls.user, 'Drugi Workspace')
        cls.library = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workplace, name='Dysk')
        cls.folder = Folder.objects.create(owner=cls.user, workplace=cls.workplace, library=cls.library, name='Folder')
        cls.drive = Document.objects.create(owner=cls.user, workplace=cls.workplace,
            library=cls.library, folder=cls.folder, title='Przed zmianą', filename='oryginał.docx',
            description='Opis', file_size=123, revision=3)
        cls.office = WorkspaceDocument.objects.create(owner=cls.user, workplace=cls.workplace,
            title='Przed zmianą', filename='oryginał.docx', kind='file', is_template=True, file_size=456, revision=4)
        cls.board = WorkspaceDocument.objects.create(owner=cls.user, workplace=cls.workplace,
            title='Tablica', kind='board', content='{"elements": []}', revision=5)

    def setUp(self):
        self.client.force_login(self.user)

    def base(self, module, workplace=None):
        return scoped_workplace_app_path(workplace or self.workplace, module)

    def items(self):
        return [('documents', self.drive), ('office', self.office), ('office', self.board)]

    def test_rename_scoped_and_ordinary_urls_changes_only_title_and_modified_date(self):
        for module, item in self.items():
            base = self.base(module)
            self.client.get(base)
            for route in (base, f'/{module}/'):
                with self.subTest(module=module, kind=getattr(item, 'kind', 'drive'), route=route):
                    before = type(item).objects.values().get(pk=item.pk)
                    key = office_service.document_key(item)
                    title = f'Nowa nazwa {route} — ąćę'
                    response = self.client.post(f'{route}{item.pk}/rename/', {
                        'title': f'  {title}  ', 'revision': 99, 'content': 'Nadpisana treść',
                        'filename': 'podmiana.pdf', 'folder': '', 'is_template': '',
                    })
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json(), {'title': title})
                    self.assertEqual(response['Cache-Control'], 'private, no-store')
                    after = type(item).objects.values().get(pk=item.pk)
                    self.assertEqual(after.pop('title'), title)
                    before.pop('title')
                    self.assertGreaterEqual(after.pop('updated_at'), before.pop('updated_at'))
                    self.assertEqual(after, before)
                    item.refresh_from_db()
                    self.assertEqual(office_service.document_key(item), key)
                    self.assertContains(self.client.get(f'{base}{item.pk}/editor/'), title)
                    params = {'library': item.library_id, 'folder': item.folder_id} if module == 'documents' else {}
                    self.assertContains(self.client.get(base, params), title)

    def test_invalid_titles_are_rejected_without_writing(self):
        for module, item in self.items():
            for title in ('', '   ', 'x' * 256, 'bad\x00name'):
                response = self.client.post(f'{self.base(module)}{item.pk}/rename/', {'title': title})
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.json()['error'])
                item.refresh_from_db()
                self.assertIn(item.title, ('Przed zmianą', 'Tablica'))
            response = self.client.post(f'{self.base(module)}{item.pk}/rename/', {'title': 'x' * 255})
            self.assertEqual(response.status_code, 200)

    def test_owner_workspace_trash_and_module_boundaries(self):
        for module, item in self.items():
            url = f'{self.base(module)}{item.pk}/rename/'
            self.assertEqual(Client().post(url, {'title': 'Obca nazwa'}).status_code, 302)
            wrong_workspace = f'{self.base(module, self.second)}{item.pk}/rename/'
            self.assertEqual(self.client.post(wrong_workspace, {'title': 'Obca nazwa'}).status_code, 404)
            other_module = 'office' if module == 'documents' else 'documents'
            self.assertEqual(self.client.post(f'{self.base(other_module)}{item.pk}/rename/', {'title': 'Obca nazwa'}).status_code, 404)
            item.owner = self.other
            item.save(update_fields=['owner'])
            self.assertEqual(self.client.post(url, {'title': 'Obca nazwa'}).status_code, 404)
            item.owner, item.deleted_at = self.user, timezone.now()
            item.save(update_fields=['owner', 'deleted_at'])
            self.assertEqual(self.client.post(url, {'title': 'Obca nazwa'}).status_code, 404)
            item.refresh_from_db()
            self.assertIn(item.title, ('Przed zmianą', 'Tablica'))

    def test_post_and_csrf_required(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        for module, item in self.items():
            url = f'{self.base(module)}{item.pk}/rename/'
            self.assertEqual(self.client.get(url).status_code, 405)
            self.assertEqual(csrf_client.post(url, {'title': 'Bez tokenu'}).status_code, 403)
            csrf_client.get(f'{self.base(module)}{item.pk}/editor/')
            token = csrf_client.cookies['csrftoken'].value
            response = csrf_client.post(url, {'title': 'Z tokenem'}, headers={'X-CSRFToken': token})
            self.assertEqual(response.status_code, 200)

    def test_unchanged_name_does_not_touch_modified_date(self):
        for module, item in self.items():
            before = item.updated_at
            response = self.client.post(f'{self.base(module)}{item.pk}/rename/', {'title': item.title})
            self.assertEqual(response.status_code, 200)
            item.refresh_from_db()
            self.assertEqual(item.updated_at, before)
