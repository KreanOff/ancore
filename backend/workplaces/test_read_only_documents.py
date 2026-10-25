"""Guests can read legacy text documents while shared writes stay forbidden."""
import json
import tempfile
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from documents.models import Document, DocumentLibrary, WorkspaceDocument
from documents import office_service
from .models import WorkplaceMembership, create_workplace_for_user
from .services import scoped_workplace_app_path


class ReadOnlyTextDocumentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='text-owner', email='text-owner@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Dokumenty zespołu')
        for role in ('admin', 'member', 'guest'):
            person = users.objects.create_user(username='text-' + role, email='text-' + role + '@example.test')
            setattr(cls, role, person)
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=person, role=role)
        cls.document = WorkspaceDocument.objects.create(owner=cls.owner, workplace=cls.workspace,
            title='Wspólny dokument Ancore', content='<h2>Plan zespołu</h2><p>Zachowana treść.</p>')

    def client_for(self, person):
        client = Client()
        client.force_login(person)
        session = client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()
        return client

    def targets(self, document=None):
        document = document or self.document
        return [f'/office/{document.pk}/',
                scoped_workplace_app_path(self.workspace, 'office', f'{document.pk}/')]

    def apis(self):
        return ['/api/v1/page/', scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')]

    def assert_read_only_content(self, page):
        self.assertEqual(page['type'], 'office-text')
        self.assertTrue(page['read_only'])
        fields = {field['name']: field for field in page['data']['form']['fields']}
        self.assertEqual(fields['title']['value'], self.document.title)
        self.assertEqual(fields['content']['value'], self.document.content)

    def test_guest_reads_text_via_html_and_both_page_apis(self):
        client = self.client_for(self.guest)
        for target in self.targets():
            with self.subTest(target=target):
                response = client.get(target, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['office_read_only'])
                self.assert_read_only_content(response.context['frontend_bootstrap'])
                self.assertContains(response, 'data-office-read-only')
                self.assertNotContains(response, 'data-office-save')
                self.assertNotContains(response, 'contenteditable="true"')
                for api in self.apis():
                    response = client.get(api, {'url': target}, follow=True)
                    self.assertEqual(response.status_code, 200)
                    self.assert_read_only_content(response.json())

    def test_guest_text_posts_remain_forbidden_via_html_and_page_apis(self):
        client = self.client_for(self.guest)
        body = {'title': 'Nieuprawniona zmiana', 'content': '<p>Nie.</p>', 'revision': 1}
        for target in self.targets():
            self.assertEqual(client.post(target, body).status_code, 403)
            for api in self.apis():
                self.assertEqual(client.post(api + '?' + urlencode({'url': target}), body).status_code, 403)
        self.document.refresh_from_db()
        self.assertEqual(self.document.title, 'Wspólny dokument Ancore')
        self.assertEqual(self.document.content, '<h2>Plan zespołu</h2><p>Zachowana treść.</p>')
        self.assertEqual(self.document.revision, 1)

    def test_guest_html_preview_sanitizes_legacy_content(self):
        self.document.content = '<p onclick="alert(1)">Plan &amp; zakres</p><script>alert(2)</script><img src=x onerror="alert(3)">'
        self.document.save(update_fields=['content'])
        response = self.client_for(self.guest).get(self.targets()[1])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['office_preview_content'], '<p>Plan &amp; zakres</p>')
        self.assertContains(response, '<p>Plan &amp; zakres</p>', html=True)
        self.assertNotContains(response, '<script>alert(2)</script>')
        self.assertNotContains(response, 'onclick="alert(1)"')

    def test_text_read_exception_keeps_creation_and_file_metadata_forms_forbidden(self):
        client = self.client_for(self.guest)
        uploaded = WorkspaceDocument.objects.create(owner=self.owner, workplace=self.workspace,
            title='Przesłany dokument', kind=WorkspaceDocument.Kind.FILE, filename='praca.docx')
        targets = self.targets(uploaded) + [scoped_workplace_app_path(self.workspace, 'office', 'create/text/')]
        for target in targets:
            self.assertEqual(client.get(target, follow=True).status_code, 403)
            for api in self.apis():
                self.assertEqual(client.get(api, {'url': target}, follow=True).status_code, 403)

    def test_text_from_another_workspace_or_trash_is_not_readable(self):
        from django.utils import timezone
        client = self.client_for(self.guest)
        other_workspace = create_workplace_for_user(self.owner, 'Inne dokumenty')
        foreign = WorkspaceDocument.objects.create(owner=self.owner, workplace=other_workspace, title='Obcy tekst')
        trashed = WorkspaceDocument.objects.create(owner=self.owner, workplace=self.workspace,
            title='Tekst w koszu', deleted_at=timezone.now())
        for document in (foreign, trashed):
            target = scoped_workplace_app_path(self.workspace, 'office', f'{document.pk}/')
            self.assertEqual(client.get(target).status_code, 403)
            self.assertEqual(client.get(self.apis()[1], {'url': target}).status_code, 403)

    def test_owner_admin_and_member_keep_text_write_access(self):
        for person in (self.owner, self.admin, self.member):
            client = self.client_for(person)
            for target in self.targets():
                body = {'title': person.username, 'content': '<p>Zapis zespołu.</p>',
                        'revision': self.document.revision}
                self.assertEqual(client.post(target, body).status_code, 302)
                self.document.refresh_from_db()
                self.assertEqual(self.document.title, person.username)
                for api in self.apis():
                    body['revision'] = self.document.revision
                    response = client.post(api + '?' + urlencode({'url': target}), body)
                    self.assertEqual(response.status_code, 200)
                    self.document.refresh_from_db()
                    self.assertEqual(response.json()['revision'], self.document.revision)


@override_settings(ONLYOFFICE_URL='http://office.test', ONLYOFFICE_INTERNAL_URL='http://office-internal',
                   ONLYOFFICE_ANCORE_URL='http://ancore.test', ONLYOFFICE_JWT_SECRET='test-only-' * 8)
class OfficeRoleDowngradeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='office-role-owner', email='office-role-owner@example.test')
        cls.editor = users.objects.create_user(username='office-role-editor', email='office-role-editor@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Wspólna edycja')
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Oddzielne dokumenty')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.editor)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        storage = FileSystemStorage(directory.name)
        for model in (Document, WorkspaceDocument):
            field = model._meta.get_field('file')
            self.addCleanup(setattr, field, 'storage', field.storage)
            field.storage = storage
        self.documents = self.make_documents(self.workspace)
        self.other_documents = self.make_documents(self.other_workspace)
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def make_documents(self, workplace):
        library = DocumentLibrary.objects.create(owner=self.owner, workplace=workplace, name='Pliki zespołu')
        drive = Document(owner=self.owner, workplace=workplace, library=library,
                         title='Dokument Dysku', filename='dysk.docx')
        office = WorkspaceDocument(owner=self.owner, workplace=workplace, kind=WorkspaceDocument.Kind.FILE,
                                   title='Dokument Office', filename='office.docx')
        for item in (drive, office):
            content = office_service.blank_file('word')
            item.file_size = content.size
            item.file.save(item.filename, content, save=False)
            item.save()
        return (('documents', drive), ('office', office))

    def snapshot(self, item):
        values = type(item).objects.filter(pk=item.pk).values().get()
        values.pop('office_key')
        with item.file.open('rb') as stream:
            return values, stream.read()

    def endpoint(self, target, transport):
        if transport == 'html':
            return target
        api = '/api/v1/page/' if transport == 'api' else scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        return api + '?' + urlencode({'url': target})

    def change_role(self, role, transport):
        target = reverse('workplaces:member-update', args=[self.workspace.pk, self.membership.pk])
        response = self.client.post(self.endpoint(target, transport), {'action': 'role', 'role': role})
        self.assertEqual(response.status_code, 302 if transport == 'html' else 200)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, role)

    def test_downgrade_blocks_old_coauthor_callbacks_sources_and_save_keys(self):
        for role in ('member', 'admin'):
            for transport in ('html', 'api', 'scoped-api'):
                with self.subTest(role=role, transport=transport):
                    self.membership.role = role
                    self.membership.save(update_fields=['role'])
                    before = {item.pk: (item.office_key, self.snapshot(item))
                              for _, item in (*self.documents, *self.other_documents)}
                    configs = {item.pk: [(actor, office_service.editor_config(item, actor))
                                        for actor in (self.owner, self.editor)]
                               for _, item in self.documents}
                    self.change_role('guest', transport)
                    for app, item in self.documents:
                        item.refresh_from_db()
                        old_key, previous = before[item.pk]
                        self.assertNotEqual(item.office_key, old_key)
                        self.assertEqual(self.snapshot(item), previous)
                        for actor, config in configs[item.pk]:
                            self.assertEqual(Client().get(config['document']['url']).status_code, 404)
                            payload = {'key': config['document']['key'], 'status': 6, 'forcesavetype': 1,
                                       'filetype': 'docx', 'users': [str(self.editor.pk)],
                                       'url': 'http://office.test/cache/files/stale/result.docx'}
                            with patch('documents.office_service.download_result') as download:
                                response = Client().post(config['editorConfig']['callbackUrl'],
                                    json.dumps(payload), content_type='application/json',
                                    headers={'Authorization': 'Bearer ' + office_service.sign({'payload': payload})})
                            self.assertEqual(response.status_code, 409)
                            download.assert_not_called()
                            self.assertFalse(item.save_receipts.exists())
                            self.assertEqual(self.snapshot(item), previous)
                        old_editor_key = configs[item.pk][0][1]['document']['key']
                        for base in (f'/{app}/', scoped_workplace_app_path(self.workspace, app)):
                            state = self.client.get(base + f'{item.pk}/state/', follow=True)
                            self.assertEqual(state.json()['key'], office_service.document_key(item))
                            for api_transport in ('html', 'api', 'scoped-api'):
                                response = self.client.post(self.endpoint(base + f'{item.pk}/save/', api_transport),
                                                            HTTP_X_OFFICE_KEY=old_editor_key)
                                self.assertEqual(response.status_code, 409)
                        fresh = office_service.editor_config(item, self.editor)
                        self.assertFalse(fresh['document']['permissions']['edit'])
                        source = Client().get(fresh['document']['url'])
                        self.assertEqual(source.status_code, 200)
                        self.assertEqual(b''.join(source.streaming_content), previous[1])
                    for _, item in self.other_documents:
                        item.refresh_from_db()
                        self.assertEqual((item.office_key, self.snapshot(item)), before[item.pk])

    def test_other_role_changes_keep_existing_sessions(self):
        for old_role, new_role, active in (
            ('member', 'admin', True), ('admin', 'member', True),
            ('guest', 'member', True), ('guest', 'admin', True), ('guest', 'guest', True),
            ('member', 'guest', False),
        ):
            for transport in ('html', 'api', 'scoped-api'):
                with self.subTest(old=old_role, new=new_role, active=active, transport=transport):
                    self.membership.role, self.membership.is_active = old_role, active
                    self.membership.save(update_fields=['role', 'is_active'])
                    before = {item.pk: (item.office_key, self.snapshot(item)) for _, item in self.documents}
                    tokens = {item.pk: office_service.capability(item, 'callback', self.owner)
                              for _, item in self.documents}
                    self.change_role(new_role, transport)
                    for _, item in self.documents:
                        item.refresh_from_db()
                        self.assertEqual((item.office_key, self.snapshot(item)), before[item.pk])
                        self.assertTrue(office_service.check_capability(item, tokens[item.pk], 'callback'))
