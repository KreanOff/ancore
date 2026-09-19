"""Small, attribute-free document format. No uploaded HTML is trusted."""
from html import escape
from html.parser import HTMLParser
from io import BytesIO
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

from django.core.exceptions import ValidationError

CONTENT_LIMIT = 500_000
TAGS = {'p', 'br', 'h1', 'h2', 'h3', 'strong', 'em', 'u', 's', 'ul', 'ol', 'li', 'blockquote'}
ALIASES = {'div': 'p', 'b': 'strong', 'i': 'em', 'strike': 's'}
BLOCKED = {'script', 'style', 'iframe', 'object', 'svg', 'math', 'template'}


class DocumentHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.stack, self.blocked = [], [], []

    def handle_starttag(self, tag, attrs):
        if tag in BLOCKED:
            self.blocked.append(tag)
        if self.blocked:
            return
        tag = ALIASES.get(tag, tag)
        if tag in TAGS:
            if len(self.stack) >= 64:
                raise ValidationError('Dokument ma zbyt złożone formatowanie.')
            self.parts.append(f'<{tag}>')
            if tag != 'br':
                self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.blocked:
            if tag == self.blocked[-1]:
                self.blocked.pop()
            return
        tag = ALIASES.get(tag, tag)
        if tag in self.stack:
            while self.stack:
                current = self.stack.pop()
                self.parts.append(f'</{current}>')
                if current == tag:
                    break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag != 'br':
            self.handle_endtag(tag)

    def handle_data(self, data):
        if not self.blocked:
            # XML 1.0 control characters cannot be exported to DOCX.
            data = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]', '', data)
            self.parts.append(escape(data))


def clean_content(value):
    if len(value) > CONTENT_LIMIT:
        raise ValidationError('Dokument może mieć maksymalnie 500 000 znaków wraz z formatowaniem.')
    parser = DocumentHTML()
    parser.feed(value)
    parser.close()
    result = ''.join(parser.parts + [f'</{tag}>' for tag in reversed(parser.stack)])
    if len(result) > CONTENT_LIMIT:
        raise ValidationError('Dokument przekracza limit długości.')
    return result


def text_to_content(text):
    return clean_content(''.join(f'<p>{escape(line) or "<br>"}</p>' for line in text.splitlines()))


def docx_bytes(content):
    """Export the supported paragraphs and inline styles to a local OOXML file."""
    ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    ET.register_namespace('w', ns)
    def element(parent, name, **attrs):
        return ET.SubElement(parent, f'{{{ns}}}{name}', {f'{{{ns}}}{key}': value for key, value in attrs.items()})
    root = ET.Element(f'{{{ns}}}document')
    body = element(root, 'body')

    class Exporter(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.paragraph = None
            self.styles = []
            self.lists = []

        def start_paragraph(self, tag='p'):
            self.paragraph = element(body, 'p')
            if tag in {'h1', 'h2', 'h3', 'blockquote'}:
                props = element(self.paragraph, 'pPr')
                element(props, 'spacing', before='180', after='120')
                if tag == 'blockquote':
                    element(props, 'ind', left='720')
                else:
                    element(props, 'outlineLvl', val=str(int(tag[1]) - 1))
            if tag in {'h1', 'h2', 'h3'}:
                self.styles.append(tag)

        def handle_starttag(self, tag, attrs):
            if tag in {'ul', 'ol'}:
                self.lists.append([tag, 0])
            elif tag in {'p', 'h1', 'h2', 'h3', 'blockquote', 'li'}:
                self.start_paragraph(tag)
                if tag == 'li':
                    if self.lists:
                        self.lists[-1][1] += 1
                    prefix = f'{self.lists[-1][1]}. ' if self.lists and self.lists[-1][0] == 'ol' else '• '
                    self.handle_data(prefix)
            elif tag == 'br':
                if self.paragraph is None:
                    self.start_paragraph()
                element(element(self.paragraph, 'r'), 'br')
            elif tag in {'strong', 'em', 'u', 's'}:
                self.styles.append(tag)

        def handle_endtag(self, tag):
            if tag in self.styles:
                self.styles.remove(tag)
            if tag in {'p', 'h1', 'h2', 'h3', 'blockquote', 'li'}:
                self.paragraph = None
            if tag in {'ol', 'ul'} and self.lists:
                self.lists.pop()

        def handle_data(self, text):
            if not text:
                return
            if self.paragraph is None:
                self.start_paragraph()
            run = element(self.paragraph, 'r')
            if self.styles:
                props = element(run, 'rPr')
                for tag in set(self.styles):
                    if tag in {'h1', 'h2', 'h3'}:
                        element(props, 'sz', val={'h1': '36', 'h2': '30', 'h3': '26'}[tag])
                    elif tag == 'u':
                        element(props, 'u', val='single')
                    else:
                        element(props, {'strong': 'b', 'em': 'i', 's': 'strike'}[tag])
            node = element(run, 't')
            node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            node.text = text

    parser = Exporter()
    parser.feed(clean_content(content))
    parser.close()
    if not len(body):
        element(body, 'p')
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr('word/document.xml', ET.tostring(root, encoding='utf-8', xml_declaration=True))
    return output.getvalue()
