"""Bounded, read-only previews. Uploaded HTML and office code are never executed."""

import csv
import io
from itertools import islice
from pathlib import PurePosixPath
import posixpath
import re
import tarfile
import xml.etree.ElementTree as ET
import zipfile
import zlib

from core.upload_validation import _validate_attachment_signature


INLINE_TYPES = {
    '.pdf': ('pdf', 'application/pdf'),
    '.jpg': ('image', 'image/jpeg'), '.jpeg': ('image', 'image/jpeg'),
    '.png': ('image', 'image/png'), '.gif': ('image', 'image/gif'),
    '.webp': ('image', 'image/webp'),
}
TEXT_LIMIT = 256 * 1024
XML_LIMIT = 2 * 1024 * 1024
PACKAGE_LIMIT = 12 * 1024 * 1024
ENTRY_LIMIT = 2000
ROW_LIMIT = 200
COLUMN_LIMIT = 30
SHEET_LIMIT = 10
UNSUPPORTED = 'Podgląd tego formatu nie jest jeszcze dostępny. Pobierz plik, aby otworzyć go w odpowiednim programie.'
INVALID = 'Nie udało się odczytać podglądu. Plik może być uszkodzony, zaszyfrowany lub zbyt złożony. Możesz go pobrać.'


def inline_type(document):
    return INLINE_TYPES.get(PurePosixPath(document.filename).suffix.lower())


def validate_inline(file, filename):
    valid = _validate_attachment_signature(PurePosixPath(filename).suffix.lower(), file.read(4096))
    file.seek(0)
    if not valid:
        raise ValueError('Invalid inline file signature')


def _decode(data, truncated=False):
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data.decode('utf-16', errors='replace')
    try:
        return data.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        if truncated and error.reason == 'unexpected end of data':
            return data.decode('utf-8-sig', errors='replace')
        return data.decode('cp1250', errors='replace')


class OfficePackage:
    def __init__(self, archive):
        self.archive = archive
        self.read_size = 0
        entries = archive.infolist()
        if len(entries) > ENTRY_LIMIT or sum(entry.file_size for entry in entries) > PACKAGE_LIMIT:
            raise ValueError('Office package too large')

    def xml(self, name):
        entry = self.archive.getinfo(name)
        if entry.file_size > XML_LIMIT:
            raise ValueError('XML too large')
        with self.archive.open(entry) as stream:
            data = stream.read(XML_LIMIT + 1)
        self.read_size += len(data)
        if len(data) > XML_LIMIT or self.read_size > PACKAGE_LIMIT:
            raise ValueError('Preview too large')
        # Reject DTDs/entities, including XML encoded as UTF-16/32.
        normalized = data.replace(b'\x00', b'').upper()
        if b'<!DOCTYPE' in normalized or b'<!ENTITY' in normalized:
            raise ValueError('XML declarations not allowed')
        root = ET.fromstring(data)
        pending = [(root, 0)]
        count = 0
        while pending:
            node, depth = pending.pop()
            count += 1
            if count > 50000 or depth > 64:
                raise ValueError('XML too complex')
            pending.extend((child, depth + 1) for child in node)
        return root


def _docx(file):
    with zipfile.ZipFile(file) as archive:
        root = OfficePackage(archive).xml('word/document.xml')
        paragraphs = []
        length = 0
        for paragraph in root.iter():
            if paragraph.tag.rsplit('}', 1)[-1] != 'p':
                continue
            text = ''.join(
                node.text or '' if node.tag.rsplit('}', 1)[-1] == 't'
                else {'tab': '\t', 'br': '\n', 'cr': '\n'}.get(node.tag.rsplit('}', 1)[-1], '')
                for node in paragraph.iter()
            )
            length += len(text) + (2 if paragraphs else 0)
            paragraphs.append(text[:TEXT_LIMIT + 1])
            if length > TEXT_LIMIT:
                break
        text = '\n\n'.join(paragraphs)
        return {'kind': 'text', 'text': text[:TEXT_LIMIT], 'truncated': len(text) > TEXT_LIMIT,
                'note': 'Uproszczony podgląd tekstu DOCX, bez układu stron, obrazów i formatowania.'}


def _xlsx(file):
    with zipfile.ZipFile(file) as archive:
        package = OfficePackage(archive)
        workbook = package.xml('xl/workbook.xml')
        relations = package.xml('xl/_rels/workbook.xml.rels')
        targets = {item.get('Id'): item.get('Target', '') for item in relations
                   if item.get('TargetMode') != 'External'}
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            strings = [''.join(part.text or '' for part in item.iter() if part.tag.endswith('}t'))
                       for item in package.xml('xl/sharedStrings.xml')]
        sheets = []
        truncated = False
        remaining = TEXT_LIMIT
        for sheet in workbook.findall('.//{*}sheet'):
            if len(sheets) == SHEET_LIMIT or not remaining:
                truncated = True
                break
            relation = next((value for key, value in sheet.attrib.items() if key.endswith('}id')), '')
            target = targets.get(relation, '')
            path = posixpath.normpath(target.lstrip('/') if target.startswith('/') else f'xl/{target}')
            if not path.startswith('xl/worksheets/') or not path.endswith('.xml'):
                raise ValueError('Invalid worksheet path')
            root = package.xml(path)
            rows = []
            width = 0
            for row in root.findall('.//{*}sheetData/{*}row'):
                if len(rows) == ROW_LIMIT or not remaining:
                    truncated = True
                    break
                cells = {}
                next_column = 0
                for cell in row.findall('{*}c'):
                    if not remaining:
                        truncated = True
                        break
                    reference = cell.get('r', '')
                    match = re.fullmatch(r'([A-Z]{1,3})[1-9][0-9]{0,6}', reference)
                    if reference and not match:
                        raise ValueError('Invalid cell reference')
                    column = next_column
                    if match:
                        column = 0
                        for letter in match[1]:
                            column = column * 26 + ord(letter) - 64
                        column -= 1
                    next_column = column + 1
                    if column >= COLUMN_LIMIT:
                        truncated = True
                        continue
                    value = cell.findtext('{*}v', '')
                    if cell.get('t') == 's':
                        index = int(value)
                        if not 0 <= index < len(strings):
                            raise ValueError('Invalid shared string')
                        value = strings[index]
                    elif cell.get('t') == 'inlineStr':
                        value = ''.join(part.text or '' for part in cell.iter() if part.tag.endswith('}t'))
                    elif cell.get('t') == 'b':
                        value = 'TAK' if value == '1' else 'NIE'
                    if not value and cell.find('{*}f') is not None:
                        value = '=' + cell.findtext('{*}f', '')
                    cells[column] = value[:min(4000, remaining)]
                    remaining -= len(cells[column])
                    truncated |= len(value) > len(cells[column])
                    width = max(width, column + 1)
                rows.append({'number': row.get('r', str(len(rows) + 1)), 'cells': cells})
            for row in rows:
                row['cells'] = [row['cells'].get(column, '') for column in range(width)]
            sheets.append({'name': sheet.get('name', 'Arkusz'), 'rows': rows})
        return {'kind': 'sheets', 'sheets': sheets, 'truncated': truncated,
                'note': 'Uproszczony podgląd XLSX: zapisane wartości, bez formatowania i przeliczania formuł. Daty mogą być pokazane jako liczby.'}


def _text(file, extension):
    data = file.read(TEXT_LIMIT + 1)
    truncated = len(data) > TEXT_LIMIT
    text = _decode(data[:TEXT_LIMIT], truncated=truncated)
    if extension == '.txt':
        return {'kind': 'text', 'text': text, 'truncated': truncated}
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=',;\t|')
    except csv.Error:
        dialect = csv.excel
    # A cropped byte range may end inside a record. Never present it as complete.
    if truncated:
        text = text.rsplit('\n', 1)[0] if '\n' in text else ''
    rows = list(islice(csv.reader(io.StringIO(text), dialect), ROW_LIMIT + 1))
    truncated |= len(rows) > ROW_LIMIT or any(len(row) > COLUMN_LIMIT for row in rows)
    return {'kind': 'sheets', 'truncated': truncated, 'sheets': [{
        'name': 'Zawartość CSV', 'rows': [
            {'number': index, 'cells': row[:COLUMN_LIMIT]} for index, row in enumerate(rows[:ROW_LIMIT], 1)
        ],
    }]}


def _archive(file, extension):
    entries = []
    if extension == '.zip':
        with zipfile.ZipFile(file) as archive:
            for item in islice(archive.infolist(), ROW_LIMIT + 1):
                entries.append({'name': item.filename, 'size': item.file_size, 'folder': item.is_dir()})
    else:
        # Plain TAR only: never decompress or extract potentially hostile entries.
        with tarfile.open(fileobj=file, mode='r:') as archive:
            for item in islice(archive, ROW_LIMIT + 1):
                entries.append({'name': item.name, 'size': item.size, 'folder': item.isdir()})
    return {'kind': 'archive', 'entries': entries[:ROW_LIMIT], 'truncated': len(entries) > ROW_LIMIT,
            'note': 'Lista zawartości archiwum. Pliki wewnątrz archiwum nie są rozpakowywane.'}


def build_preview(document):
    extension = PurePosixPath(document.filename).suffix.lower()
    if not document.file:
        return {'kind': 'unavailable', 'message': 'Plik nie jest dostępny.'}
    try:
        with document.file.open('rb') as file:
            if extension in INLINE_TYPES:
                validate_inline(file, document.filename)
                return {'kind': INLINE_TYPES[extension][0]}
            if extension in {'.txt', '.csv'}:
                return _text(file, extension)
            if extension == '.docx':
                return _docx(file)
            if extension == '.xlsx':
                return _xlsx(file)
            if extension in {'.zip', '.tar'}:
                return _archive(file, extension)
            return {'kind': 'unsupported', 'message': UNSUPPORTED}
    except OSError:
        return {'kind': 'unavailable', 'message': 'Plik nie jest dostępny. Nie udało się go odczytać.'}
    except (ValueError, KeyError, RuntimeError, EOFError, NotImplementedError, csv.Error,
            ET.ParseError, zipfile.BadZipFile, tarfile.TarError, zlib.error):
        return {'kind': 'error', 'message': INVALID}
