"""Access and lifecycle guarantees introduced by the production deployment."""
import os
import re
import subprocess
import sys
from unittest.mock import patch

from django.conf import settings
from django.db import DatabaseError
from django.core.exceptions import DisallowedHost, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.test.client import encode_multipart

from core.health import readiness
from core.hosts import ServerAddressMiddleware
from core.upload_validation import DEFAULT_ATTACHMENT_MAX_SIZE
from documents.forms import MultipleFileField


class ProductionConfigurationTests(SimpleTestCase):
    @override_settings(MAX_ATTACHMENT_SIZE=DEFAULT_ATTACHMENT_MAX_SIZE, DATA_UPLOAD_MAX_MEMORY_SIZE=20 * 1024 * 1024)
    def test_public_proxy_accepts_maximum_file_batch_with_multipart_overhead(self):
        template = (settings.BASE_DIR / 'deploy/web/nginx.conf').read_text()
        public_server = re.split(r'\nserver\s*\{', template)[1]
        limit = re.search(r'client_max_body_size\s+(\d+)([kmg]?)\s*;', public_server)
        self.assertIsNotNone(limit)
        proxy_bytes = int(limit[1]) * {'': 1, 'k': 1024, 'm': 1024**2, 'g': 1024**3}[limit[2]]

        # Discover the batch boundary through the same field used by Drive/Office.
        field = MultipleFileField()
        files = []
        for number in range(1, 101):
            candidate = SimpleUploadedFile(f'{number}-' + 'ą' * 240 + '.pdf', b'%PDF-1.7\n')
            try:
                field.clean([*files, candidate])
            except ValidationError:
                break
            files.append(candidate)
        else:
            self.fail('The upload field must bound the number of files.')
        self.assertTrue(files)

        body = encode_multipart('ancore-upload-boundary', {'files': files, 'csrfmiddlewaretoken': 'x' * 64})
        multipart_overhead = len(body) - sum(file.size for file in files)
        self.assertGreater(multipart_overhead, 0)
        required_bytes = (len(files) * settings.MAX_ATTACHMENT_SIZE
                          + settings.DATA_UPLOAD_MAX_MEMORY_SIZE + multipart_overhead)
        self.assertGreaterEqual(proxy_bytes, required_bytes)

    def test_production_paths_and_proxy_header_are_configurable(self):
        environment = {**os.environ, 'DEBUG': 'false', 'SECRET_KEY': 'test-secret-' * 8,
                       'ALLOWED_HOSTS': 'example.test', 'TRUST_PROXY_HEADERS': 'true',
                       'MEDIA_ROOT': '/data/media', 'PRIVATE_DOCUMENT_ROOT': '/data/private',
                       'STATIC_ROOT': '/data/static', 'FILE_UPLOAD_TEMP_DIR': '/data/tmp',
                       'SESSION_COOKIE_SECURE': 'true', 'CSRF_COOKIE_SECURE': 'true',
                       'SECURE_SSL_REDIRECT': 'true',
                       'PYTHONPATH': str(settings.BACKEND_DIR)}
        code = ('from ancore import settings as s; '
                'assert str(s.MEDIA_ROOT)=="/data/media"; '
                'assert str(s.PRIVATE_DOCUMENT_ROOT)=="/data/private"; '
                'assert str(s.STATIC_ROOT)=="/data/static"; '
                'assert s.FILE_UPLOAD_TEMP_DIR=="/data/tmp"; '
                'assert s.SECURE_PROXY_SSL_HEADER==("HTTP_X_FORWARDED_PROTO","https"); '
                'assert not s.DEBUG and s.SESSION_COOKIE_SECURE')
        result = subprocess.run([sys.executable, '-c', code], env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_readiness_failure_hides_database_details(self):
        with patch('core.health.connection') as connection:
            connection.cursor.side_effect = DatabaseError('private connection details')
            response = readiness(RequestFactory().get('/health/ready/'))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b'private', response.content)


@override_settings(ALLOW_IP_HOSTS=True, ALLOWED_HOSTS=['*'])
class ServerAddressTests(SimpleTestCase):
    def test_address_mode_accepts_server_ips_and_localhost(self):
        middleware = ServerAddressMiddleware(lambda request: HttpResponse('ok'))
        for host in ('192.0.2.10:8080', '127.0.0.1:8080', 'localhost:8080', '[2001:db8::1]:8080'):
            with self.subTest(host=host):
                self.assertEqual(middleware(RequestFactory().get('/', HTTP_HOST=host)).status_code, 200)

    def test_address_mode_rejects_unconfigured_domains_and_invalid_hosts(self):
        middleware = ServerAddressMiddleware(lambda request: HttpResponse('ok'))
        for host in ('attacker.example:8080', '999.999.999.999:8080', 'user@192.0.2.10:8080'):
            with self.subTest(host=host), self.assertRaises(DisallowedHost):
                middleware(RequestFactory().get('/', HTTP_HOST=host))
