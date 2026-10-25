"""Text encoding validation through the private Drive and Documents uploads."""
import codecs
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Document, DocumentLibrary, WorkspaceDocument


class TextUploadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='text-upload-owner', email='text-upload@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Text uploads')
        cls.library = DocumentLibrary.objects.create(owner=cls.owner, workplace=cls.workspace, name='Text drive')
        cls.office = scoped_workplace_app_path(cls.workspace, 'office')
        cls.drive = scoped_workplace_app_path(cls.workspace, 'documents')

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ancore-text-uploads-')
        self.addCleanup(temporary.cleanup)
        for model in (Document, WorkspaceDocument):
            field = model._meta.get_field('file')
            self.addCleanup(setattr, field, 'storage', field.storage)
            field.storage = FileSystemStorage(temporary.name)
        self.client.force_login(self.owner)

    def test_utf16_txt_and_csv_upload_to_both_catalogs_and_text_import(self):
        text = 'Nazwa;Opis\r\nPrzykład;Zażółć gęślą jaźń 🙂\r\n'
        for bom, encoding in ((codecs.BOM_UTF16_LE, 'utf-16-le'), (codecs.BOM_UTF16_BE, 'utf-16-be')):
            content = bom + text.encode(encoding)
            for extension in ('txt', 'csv'):
                for model, url in ((WorkspaceDocument, self.office + 'upload/'),
                                   (Document, self.drive + f'upload/?library={self.library.pk}')):
                    with self.subTest(encoding=encoding, extension=extension, model=model.__name__):
                        filename = f'example-{encoding}.{extension}'
                        response = self.client.post(url, {'files': SimpleUploadedFile(filename, content)})
                        self.assertEqual(response.status_code, 302)
                        item = model.objects.get(filename=filename)
                        with item.file.open('rb') as source:
                            self.assertEqual(source.read(), content)
                        if model is WorkspaceDocument and extension == 'txt':
                            response = self.client.post(f'{self.office}{item.pk}/import/')
                            self.assertEqual(response.status_code, 302)
                            imported = WorkspaceDocument.objects.get(title=item.title + ' — kopia tekstu')
                            self.assertIn('Zażółć gęślą jaźń 🙂', imported.content)

    def test_binary_text_upload_never_creates_a_document(self):
        for extension in ('txt', 'csv'):
            for content in (b'plain\x00binary', codecs.BOM_UTF16_LE + b'\x00\x00', b'\xff\xff\xff\xff'):
                for url in (self.office + 'upload/', self.drive + f'upload/?library={self.library.pk}'):
                    with self.subTest(extension=extension, content=content, url=url):
                        response = self.client.post(url, {'files': SimpleUploadedFile(f'example.{extension}', content)},
                                                    headers={'X-Document-Modal': 'true'})
                        self.assertContains(response, 'Załącznik ma nieprawidłową zawartość.')
        self.assertFalse(Document.objects.exists())
        self.assertFalse(WorkspaceDocument.objects.exists())
