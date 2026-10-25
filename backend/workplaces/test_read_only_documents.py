"""Guests can read legacy text documents while shared writes stay forbidden."""
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from documents.models import WorkspaceDocument
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
