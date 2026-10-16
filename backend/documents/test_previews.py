import io
import tarfile
import tempfile
from types import SimpleNamespace
import zipfile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Document, DocumentLibrary
from .previews import TEXT_LIMIT, XML_LIMIT, build_preview


def package(parts):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def workbook_parts():
    return {
        'xl/workbook.xml': '<workbook xmlns="urn:sheet" xmlns:r="urn:rel"><sheets><sheet name="Budżet" r:id="r1"/><sheet name="Pusty" r:id="r2"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/><Relationship Id="r2" Target="/xl/worksheets/sheet2.xml"/></Relationships>',
        'xl/sharedStrings.xml': '<sst xmlns="urn:sheet"><si><t>Koszt</t></si></sst>',
        'xl/worksheets/sheet1.xml': '<worksheet xmlns="urn:sheet"><sheetData><row r="3"><c r="A3" t="s"><v>0</v></c><c r="C3"><f>1+2</f><v>3</v></c></row><row r="5"><c r="A5" t="inlineStr"><is><t>Żółć</t></is></c><c r="B5"><f>2+2</f></c></row></sheetData></worksheet>',
        'xl/worksheets/sheet2.xml': '<worksheet xmlns="urn:sheet"><sheetData/></worksheet>',
    }


class PreviewParserTests(SimpleTestCase):
    def preview(self, filename, data):
        return build_preview(SimpleNamespace(filename=filename, file=ContentFile(data, name=filename)))

    def test_text_encoding_and_limit(self):
        for encoding in ['utf-8-sig', 'utf-16', 'cp1250']:
            with self.subTest(encoding=encoding):
                self.assertEqual(self.preview('a.txt', 'Zażółć gęślą'.encode(encoding))['text'], 'Zażółć gęślą')
        result = self.preview('large.txt', b'a' * (TEXT_LIMIT + 50))
        self.assertTrue(result['truncated'])
        self.assertEqual(len(result['text']), TEXT_LIMIT)
        result = self.preview('large.txt', 'ą'.encode() + b'a' * (TEXT_LIMIT - 3) + 'ó'.encode())
        self.assertTrue(result['truncated'])
        self.assertTrue(result['text'].startswith('ą'))

    def test_csv_dialect_quotes_and_row_limit(self):
        result = self.preview('a.csv', 'Nazwa;Opis\n"A;B";"Dwie\nlinie"\n'.encode())
        self.assertEqual(result['sheets'][0]['rows'][1]['cells'], ['A;B', 'Dwie\nlinie'])
        result = self.preview('a.csv', b'a,b\n' * 201)
        self.assertEqual(len(result['sheets'][0]['rows']), 200)
        self.assertTrue(result['truncated'])

    def test_docx_reads_text_including_tables(self):
        data = package({'word/document.xml': '<w:document xmlns:w="urn:word"><w:body><w:p><w:r><w:t>Zażółć</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Komórka</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'})
        result = self.preview('a.docx', data)
        self.assertEqual(result['text'], 'Zażółć\n\nKomórka')
        data = package({'word/document.xml': '<document><p><t>' + 'x' * (TEXT_LIMIT - 1) + '</t></p><p><t>Koniec</t></p></document>'})
        self.assertTrue(self.preview('large.docx', data)['truncated'])

    def test_xlsx_preserves_sparse_columns_rows_sheets_and_cached_values(self):
        result = self.preview('a.xlsx', package(workbook_parts()))
        self.assertEqual([sheet['name'] for sheet in result['sheets']], ['Budżet', 'Pusty'])
        self.assertEqual(result['sheets'][0]['rows'][0], {'number': '3', 'cells': ['Koszt', '', '3']})
        self.assertEqual(result['sheets'][0]['rows'][1]['cells'], ['Żółć', '=2+2', ''])
        self.assertEqual(result['sheets'][1]['rows'], [])

    def test_xlsx_rejects_external_relationships_and_invalid_strings(self):
        parts = workbook_parts()
        parts['xl/_rels/workbook.xml.rels'] = '<Relationships><Relationship Id="r1" Target="https://example.com/sheet.xml" TargetMode="External"/></Relationships>'
        self.assertEqual(self.preview('a.xlsx', package(parts))['kind'], 'error')
        parts = workbook_parts()
        parts['xl/worksheets/sheet1.xml'] = parts['xl/worksheets/sheet1.xml'].replace('<v>0</v>', '<v>-1</v>')
        self.assertEqual(self.preview('a.xlsx', package(parts))['kind'], 'error')
        parts = workbook_parts()
        parts['xl/worksheets/sheet1.xml'] = parts['xl/worksheets/sheet1.xml'].replace('A3', 'A' * 10000 + '3')
        self.assertEqual(self.preview('a.xlsx', package(parts))['kind'], 'error')

    def test_xlsx_bounds_expanded_shared_string_output(self):
        parts = workbook_parts()
        parts['xl/sharedStrings.xml'] = '<sst xmlns="urn:sheet"><si><t>' + 'x' * 4000 + '</t></si></sst>'
        parts['xl/worksheets/sheet1.xml'] = '<worksheet xmlns="urn:sheet"><sheetData>' + ''.join(
            f'<row r="{row}"><c r="A{row}" t="s"><v>0</v></c></row>' for row in range(1, 201)
        ) + '</sheetData></worksheet>'
        result = self.preview('a.xlsx', package(parts))
        self.assertTrue(result['truncated'])
        self.assertLessEqual(sum(len(cell) for sheet in result['sheets'] for row in sheet['rows'] for cell in row['cells']), TEXT_LIMIT)

    def test_office_rejects_entities_oversized_xml_and_invalid_packages(self):
        for xml in ['<!DOCTYPE a [<!ENTITY x "secret">]><a>&x;</a>', '<a>' + 'x' * XML_LIMIT + '</a>', '<a>' * 100 + '</a>' * 100]:
            with self.subTest(size=len(xml)):
                self.assertEqual(self.preview('a.docx', package({'word/document.xml': xml}))['kind'], 'error')
        for filename in ['bad.docx', 'bad.xlsx', 'bad.zip', 'bad.tar', 'fake.png']:
            self.assertEqual(self.preview(filename, b'not a valid file')['kind'], 'error')

    def test_archive_lists_names_without_extracting_paths(self):
        result = self.preview('a.zip', package({'../outside.txt': b'text', 'folder/': b''}))
        self.assertEqual([entry['name'] for entry in result['entries']], ['../outside.txt', 'folder/'])
        self.assertTrue(result['entries'][1]['folder'])
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w') as archive:
            info = tarfile.TarInfo('notes.txt')
            info.size = 5
            archive.addfile(info, io.BytesIO(b'hello'))
        result = self.preview('a.tar', buffer.getvalue())
        self.assertEqual(result['entries'], [{'name': 'notes.txt', 'size': 5, 'folder': False}])

    def test_empty_and_unsupported_files(self):
        self.assertEqual(self.preview('empty.txt', b'')['text'], '')
        for extension in ['doc', 'xls', 'rtf', 'rar', '7z', 'gz', 'html', 'svg']:
            self.assertEqual(self.preview(f'a.{extension}', b'contents')['kind'], 'unsupported')


class DocumentPreviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='preview-owner', email='preview@example.test')
        cls.other = get_user_model().objects.create_user(username='preview-other', email='other-preview@example.test')
        cls.workspace = create_workplace_for_user(cls.user, 'Podgląd')
        cls.other_workspace = create_workplace_for_user(cls.user, 'Inny Workspace')
        cls.foreign_workspace = create_workplace_for_user(cls.other, 'Obcy Workspace')
        cls.library = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workspace, name='Pliki')
        cls.base = scoped_workplace_app_path(cls.workspace, 'documents')

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        field = Document._meta.get_field('file')
        self.addCleanup(setattr, field, 'storage', field.storage)
        field.storage = FileSystemStorage(directory.name)
        self.client.force_login(self.user)

    def document(self, filename='Notes.txt', data=b'Hello', **kwargs):
        item = Document(owner=self.user, workplace=self.workspace, library=self.library,
                        title=filename, filename=filename, file_size=len(data), **kwargs)
        item.file.save(filename, ContentFile(data), save=True)
        return item

    def test_preview_fragment_and_direct_url_are_private_and_escape_uploaded_text(self):
        item = self.document(data=b'<script>alert(1)</script>')
        url = f'{self.base}{item.pk}/preview/'
        for headers in [{}, {'X-Document-Modal': 'true'}]:
            response = self.client.get(url, headers=headers)
            self.assertContains(response, 'data-document-preview')
            self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
            self.assertNotContains(response, '<script>alert(1)</script>')
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            if headers:
                self.assertNotContains(response, '<html')
            else:
                self.assertContains(response, 'documents-table')

    def test_list_and_grid_open_preview_and_keep_edit_action(self):
        item = self.document()
        for display in ['list', 'grid']:
            response = self.client.get(f'{self.base}?view=all&display={display}')
            self.assertContains(response, f'{self.base}{item.pk}/preview/')
            self.assertContains(response, f'aria-label="Edytuj dane: {item.title}"')

    def test_search_result_opens_preview(self):
        item = self.document('Notatki projektu.txt')
        self.client.get(self.base)
        response = self.client.get(reverse('global_search'), {'q': 'Notatki'})
        urls = [item['url'] for group in response.json()['groups'] for item in group['results']]
        self.assertIn(f'{self.base}{item.pk}/preview/', urls)

    def test_inline_pdf_and_images_use_fixed_mime_sameorigin_no_cache_and_download_unchanged(self):
        for filename, data, mime in [('a.pdf', b'%PDF-1.4\n%%EOF', 'application/pdf'),
                                     ('a.png', b'\x89PNG\r\n\x1a\n', 'image/png')]:
            item = self.document(filename, data)
            response = self.client.get(f'{self.base}{item.pk}/content/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], mime)
            self.assertTrue(response['Content-Disposition'].startswith('inline;'))
            self.assertEqual(response['X-Frame-Options'], 'SAMEORIGIN')
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            self.assertIn('sandbox', response['Content-Security-Policy'])
            self.assertEqual(b''.join(response.streaming_content), data)
            download = self.client.get(f'{self.base}{item.pk}/download/')
            self.assertTrue(download['Content-Disposition'].startswith('attachment;'))
            self.assertEqual(b''.join(download.streaming_content), data)

    def test_inline_rejects_active_or_mislabeled_content(self):
        for filename, data in [('a.svg', b'<svg/>'), ('a.txt', b'<script/>'), ('a.pdf', b'<html/>')]:
            item = self.document(filename, data)
            self.assertEqual(self.client.get(f'{self.base}{item.pk}/content/').status_code, 404)

    def test_preview_requires_login_owner_workspace_and_not_trash(self):
        item = self.document('a.pdf', b'%PDF-1.4')
        for suffix in ['preview/', 'content/']:
            url = f'{self.base}{item.pk}/{suffix}'
            self.assertEqual(Client().get(url).status_code, 302)
            other_base = scoped_workplace_app_path(self.other_workspace, 'documents')
            self.assertEqual(self.client.get(f'{other_base}{item.pk}/{suffix}').status_code, 404)
            self.client.force_login(self.other)
            self.assertRedirects(self.client.get(url), reverse('workplaces:workplaces'), fetch_redirect_response=False)
            foreign_base = scoped_workplace_app_path(self.foreign_workspace, 'documents')
            self.assertEqual(self.client.get(f'{foreign_base}{item.pk}/{suffix}').status_code, 404)
            self.client.force_login(self.user)
            item.deleted_at = timezone.now()
            item.save(update_fields=['deleted_at'])
            self.assertEqual(self.client.get(url).status_code, 404)
            item.deleted_at = None
            item.save(update_fields=['deleted_at'])
        # A malformed owner relation in the active Workspace does not grant access.
        item.owner = self.other
        item.save(update_fields=['owner'])
        for suffix in ['preview/', 'content/']:
            self.assertEqual(self.client.get(f'{self.base}{item.pk}/{suffix}').status_code, 404)

    def test_unscoped_urls_and_get_only(self):
        item = self.document('a.pdf', b'%PDF-1.4')
        self.client.get(self.base)
        for suffix in ['preview/', 'content/']:
            response = self.client.get(f'/documents/{item.pk}/{suffix}', follow=True)
            self.assertEqual(response.status_code, 200)
            if response.streaming:
                self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4')
            self.assertEqual(self.client.post(f'{self.base}{item.pk}/{suffix}').status_code, 405)

    def test_missing_and_unsupported_files_show_clear_fallback(self):
        item = self.document('legacy.doc', b'legacy')
        self.assertContains(self.client.get(f'{self.base}{item.pk}/preview/'), 'Podgląd tego formatu nie jest jeszcze dostępny')
        item.file.storage.delete(item.file.name)
        response = self.client.get(f'{self.base}{item.pk}/preview/', headers={'X-Document-Modal': 'true'})
        self.assertContains(response, 'Plik nie jest dostępny')
        self.assertNotContains(response, f'{item.pk}/download/')

    def test_trash_has_no_preview_or_edit_link(self):
        item = self.document(deleted_at=timezone.now())
        response = self.client.get(f'{self.base}?view=trash')
        self.assertNotContains(response, f'{item.pk}/preview/')
        self.assertNotContains(response, 'Edytuj dane:')
