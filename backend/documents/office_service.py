"""Private, signed ONLYOFFICE connection. No user-provided service endpoints."""
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import unquote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from zipfile import BadZipFile, ZipFile

import jwt
from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils.crypto import salted_hmac

OFFICE_FORMATS = {'word': ('docx', 'Dokument'), 'cell': ('xlsx', 'Arkusz'), 'slide': ('pptx', 'Prezentacja'),
                  'pdf': ('pdf', 'PDF')}


def configured():
    return bool(settings.ONLYOFFICE_URL and settings.ONLYOFFICE_ANCORE_URL and len(settings.ONLYOFFICE_JWT_SECRET) >= 32)


def sign(payload):
    now = int(time.time())
    return jwt.encode({**payload, 'iat': now, 'exp': now + 300}, settings.ONLYOFFICE_JWT_SECRET, algorithm='HS256')


def verify(token):
    return jwt.decode(token, settings.ONLYOFFICE_JWT_SECRET, algorithms=['HS256'], options={'verify_aud': False})


def capability(document, purpose, actor=None):
    return signing.dumps([str(document.pk), document.owner_id, document.workplace_id, str(document.office_key), actor.pk if actor else document.owner_id], salt=f'{_service_scope(document)}.{purpose}')


def check_capability(document, token, purpose):
    from django.contrib.auth import get_user_model
    from workplaces.services import workplace_role
    try:
        payload = signing.loads(token, salt=f'{_service_scope(document)}.{purpose}', max_age=7 * 86400)
    except signing.BadSignature:
        return False
    expected = [str(document.pk), document.owner_id, document.workplace_id, str(document.office_key)]
    if payload == expected:
        payload = [*payload, document.owner_id]
    if not isinstance(payload, list) or len(payload) != 5 or payload[:4] != expected:
        return False
    actor = get_user_model().objects.filter(pk=payload[4], is_active=True).first()
    return bool(actor and workplace_role(actor, document.workplace))


def _service_scope(document):
    return 'drive-office' if document._meta.label_lower == 'documents.document' else 'office'


def service_url(document, purpose, actor=None):
    path = reverse(f'{_service_scope(document)}-service-{purpose}', args=[document.pk])
    return settings.ONLYOFFICE_ANCORE_URL.rstrip('/') + path + '?' + urlencode({'token': capability(document, purpose, actor)})


def document_key(document):
    return salted_hmac(f'{_service_scope(document)}-editor', f'{document.pk}:{document.office_key}', algorithm='sha256').hexdigest()


def editor_config(document, user):
    config = {
        'documentType': document.office_type, 'type': 'desktop', 'width': '100%', 'height': '100%',
        'document': {'fileType': document.extension.lower(), 'key': document_key(document),
                     'title': document.filename, 'url': service_url(document, 'source', user),
                     'permissions': {'edit': True, 'download': True, 'print': True, 'chat': False}},
        'editorConfig': {'lang': 'pl', 'mode': 'edit', 'callbackUrl': service_url(document, 'callback', user),
                         'user': {'id': str(user.pk), 'name': user.get_full_name() or user.username},
                         'customization': {'forcesave': True, 'autosave': True, 'macros': False,
                                           'plugins': False, 'help': False}},
    }
    if document.extension == 'PDF' and getattr(document, 'is_pdf_form', False):
        config['document']['isForm'] = True
    config['token'] = sign(config)
    return config


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open(request):
    return build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=20)


def _origin(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Invalid office service URL')
    return parsed.scheme, parsed.hostname.lower(), parsed.port or (443 if parsed.scheme == 'https' else 80)


def download_result(url):
    """Only download signed results from this configured server's cache, no redirects."""
    public = settings.ONLYOFFICE_URL.rstrip('/')
    internal = settings.ONLYOFFICE_INTERNAL_URL.rstrip('/') or public
    parsed = urlsplit(url)
    origin = _origin(url)
    # A same-origin public prefix supports IP access without fixing the hostname.
    # Only the configured internal server is ever contacted, including for a
    # signed result whose public hostname differs between browsers.
    target = urlsplit(internal)
    internal_origin = _origin(internal)
    prefixes = []
    if origin == internal_origin:
        prefixes.append(target.path.rstrip('/') + '/cache/files/')
    if public.startswith('/') and not public.startswith('//'):
        prefixes.append(public + '/cache/files/')
    elif origin == _origin(public):
        prefixes.append(urlsplit(public).path.rstrip('/') + '/cache/files/')
    prefix = next((prefix for prefix in prefixes if parsed.path.startswith(prefix)), None)
    if not prefix or parsed.fragment:
        raise ValueError('Untrusted office result URL')
    decoded_path = parsed.path
    for _ in range(4):
        decoded_path = unquote(decoded_path, errors='strict')
    if (not parsed.path.startswith(prefix) or not decoded_path.startswith(prefix)
            or any(part in {'.', '..'} for part in decoded_path.split('/'))
            or '\\' in decoded_path or any(ord(char) < 32 for char in decoded_path)):
        raise ValueError('Untrusted office cache path')
    path = target.path.rstrip('/') + '/cache/files/' + parsed.path[len(prefix):]
    url = urlunsplit((target.scheme, target.netloc, path, parsed.query, ''))
    request = Request(url, headers={'Authorization': 'Bearer ' + sign({'payload': {'url': url}})})
    limit = settings.MAX_ATTACHMENT_SIZE
    with _open(request) as response:
        content = response.read(limit + 1)
    if not content or len(content) > limit:
        raise ValueError('Invalid office result size')
    return content


def force_save(document):
    payload = {'c': 'forcesave', 'key': document_key(document)}
    body = json.dumps({**payload, 'token': sign(payload)}).encode()
    url = (settings.ONLYOFFICE_INTERNAL_URL or settings.ONLYOFFICE_URL).rstrip('/') + '/coauthoring/CommandService.ashx'
    with _open(Request(url, data=body, headers={'Content-Type': 'application/json'})) as response:
        return json.loads(response.read(65536)).get('error')


def validate_ooxml(file, extension):
    main = {'docx': 'word/document.xml', 'xlsx': 'xl/workbook.xml', 'pptx': 'ppt/presentation.xml'}.get(extension.lower())
    if not main:
        return
    position = file.tell()
    try:
        file.seek(0)
        with ZipFile(file) as archive:
            entries = archive.infolist()
            if len(entries) > 10000 or sum(item.file_size for item in entries) > 100 * 1024 * 1024:
                raise ValueError
            names = {item.filename for item in entries}
            if main not in names or '[Content_Types].xml' not in names:
                raise ValueError
            if any(item.flag_bits & 1 for item in entries):
                raise ValueError
    except (BadZipFile, KeyError, OSError, ValueError):
        raise ValidationError('Plik biurowy ma nieprawidłową zawartość lub jest zaszyfrowany.')
    finally:
        file.seek(position)


def blank_file(kind):
    extension, _ = OFFICE_FORMATS['pdf' if kind == 'form' else kind]
    filename = 'new-form.pdf' if kind == 'form' else f'new.{extension}'
    return ContentFile((Path(__file__).parent / 'blank' / filename).read_bytes(), name=f'Nowy.{extension}')


def receipt_digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


LEGACY_FORMATS = {'DOC': 'docx', 'RTF': 'docx', 'TXT': 'docx', 'XLS': 'xlsx', 'CSV': 'xlsx', 'PPT': 'pptx'}


def convert_file(document):
    extension = LEGACY_FORMATS[document.extension]
    payload = {'async': False, 'filetype': document.extension.lower(), 'key': document_key(document) + '-convert',
               'outputtype': extension, 'title': document.filename, 'url': service_url(document, 'source')}
    body = json.dumps({**payload, 'token': sign(payload)}).encode()
    url = (settings.ONLYOFFICE_INTERNAL_URL or settings.ONLYOFFICE_URL).rstrip('/') + '/ConvertService.ashx'
    with _open(Request(url, data=body, headers={'Content-Type': 'application/json', 'Accept': 'application/json'})) as response:
        result = json.loads(response.read(65536))
    if not result.get('endConvert') or result.get('error'):
        raise ValueError('Conversion not ready')
    return extension, download_result(result['fileUrl'])
