"""Access and lifecycle guarantees introduced by the production deployment."""
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.db import DatabaseError
from django.core.exceptions import DisallowedHost
from django.http import HttpResponse, StreamingHttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.health import readiness
from core.maintenance import BackupMaintenanceMiddleware
from core.hosts import ServerAddressMiddleware


class BackupMaintenanceTests(SimpleTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.configuration = override_settings(BACKUP_CONTROL_ROOT=self.temporary.name)
        self.configuration.enable()
        self.addCleanup(self.configuration.disable)
        self.factory = RequestFactory()

    def test_marker_blocks_reads_writes_and_office_callbacks_before_view(self):
        (self.root / 'maintenance').touch()
        for path in ('/spaces/', '/api/v1/page/', '/office-service/example/callback/'):
            for method in ('get', 'post'):
                with self.subTest(path=path, method=method):
                    def view(request):
                        self.fail('Maintenance must run before domain operations.')
                    response = BackupMaintenanceMiddleware(view)(getattr(self.factory, method)(path))
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response['Retry-After'], '60')
                    self.assertEqual(response['Cache-Control'], 'no-store')

    def test_backup_cannot_lock_until_streaming_response_closes(self):
        middleware = BackupMaintenanceMiddleware(lambda request: StreamingHttpResponse([b'private']))
        response = middleware(self.factory.get('/documents/download/'))
        with (self.root / 'requests.lock').open('rb') as exclusive:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(exclusive, fcntl.LOCK_EX | fcntl.LOCK_NB)
            response.close()
            fcntl.flock(exclusive, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_exclusive_backup_lock_and_missing_control_directory_fail_closed(self):
        middleware = BackupMaintenanceMiddleware(lambda request: HttpResponse('ok'))
        self.assertEqual(middleware(self.factory.get('/')).status_code, 200)
        with (self.root / 'requests.lock').open('rb') as exclusive:
            fcntl.flock(exclusive, fcntl.LOCK_EX)
            self.assertEqual(middleware(self.factory.get('/')).status_code, 503)
        with override_settings(BACKUP_CONTROL_ROOT=str(self.root / 'missing')):
            self.assertEqual(middleware(self.factory.get('/')).status_code, 503)

    def test_view_exception_releases_lock(self):
        def view(request):
            raise ValueError('failed')
        with self.assertRaises(ValueError):
            BackupMaintenanceMiddleware(view)(self.factory.get('/'))
        with (self.root / 'requests.lock').open('rb') as exclusive:
            fcntl.flock(exclusive, fcntl.LOCK_EX | fcntl.LOCK_NB)

    @override_settings(BACKUP_CONTROL_ROOT='')
    def test_development_keeps_existing_lifecycle(self):
        self.assertEqual(BackupMaintenanceMiddleware(lambda request: HttpResponse('ok'))(
            self.factory.get('/')).content, b'ok')


class ProductionConfigurationTests(SimpleTestCase):
    def test_explicit_http_origin_uses_its_public_port(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for suffix, port in (('', 80), (':8082', 8082)):
                path = root / f'.env-{port}'
                command = [sys.executable, str(settings.BASE_DIR / 'scripts/production.py'),
                           '--env-file', str(path), 'configure', '--url', 'http://192.0.2.10' + suffix,
                           '--backup-dir', str(root / 'backups')]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"ANCORE_HTTP_PORT='{port}'", path.read_text())
                path.unlink()
                result = subprocess.run([*command, '--http-port', '8083'], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(path.exists())

    def test_default_installation_needs_no_domain_and_preserves_keys_on_https_switch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / '.env'
            command = [sys.executable, str(settings.BASE_DIR / 'scripts/production.py'),
                       '--env-file', str(path), 'configure', '--backup-dir', str(root / 'backups')]
            initial = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(initial.returncode, 0, initial.stderr)
            def config():
                return dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)
            before = config()
            for key, value in {'ANCORE_PUBLIC_URL': '', 'ANCORE_HTTP_PORT': '8080',
                               'ANCORE_BIND': '0.0.0.0', 'ANCORE_SCHEME': 'http',
                               'ANCORE_TLS_MODE': 'http', 'ANCORE_HTTPS': 'false',
                               'ANCORE_ALLOW_IP_HOSTS': 'true'}.items():
                self.assertEqual(before[key], f"'{value}'")
            certificate = root / 'certs'
            certificate.mkdir()
            for name in ('fullchain.pem', 'privkey.pem'):
                (certificate / name).write_text('fixture')
            result = subprocess.run([*command, '--reconfigure', '--url', 'https://192.0.2.10',
                                     '--tls-dir', str(certificate)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            after = config()
            self.assertEqual(after['ANCORE_TLS_MODE'], "'direct'")
            self.assertEqual(after['ANCORE_HTTPS'], "'true'")
            for key in ('SECRET_KEY', 'POSTGRES_PASSWORD', 'POSTGRES_ADMIN_PASSWORD',
                        'ONLYOFFICE_JWT_SECRET', 'ANCORE_PROJECT', 'ANCORE_BACKUP_DIR'):
                self.assertEqual(before[key], after[key])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_configuration_is_repeatable_and_never_prints_or_replaces_secrets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / '.env.production'
            command = [sys.executable, str(settings.BASE_DIR / 'scripts/production.py'),
                       '--env-file', str(path), 'configure', '--url', 'https://ancore.example.test',
                       '--backup-dir', str(root / 'backups')]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            initial = path.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(path.read_bytes(), initial)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            for line in initial.decode().splitlines():
                if line.startswith(('SECRET_KEY=', 'POSTGRES_PASSWORD=', 'POSTGRES_ADMIN_PASSWORD=', 'ONLYOFFICE_JWT_SECRET=')):
                    secret = line.partition('=')[2].strip("'")
                    self.assertGreaterEqual(len(secret), 50)
                    self.assertNotIn(secret, first.stdout + first.stderr + second.stdout + second.stderr)

    def test_invalid_origin_does_not_create_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / '.env.production'
            for url in ('ftp://example.test', 'https://example.test/path', 'https://user:pass@example.test',
                        'https://example.test?x=1', 'https://example.test;bad', 'https://example.test:0'):
                result = subprocess.run([sys.executable, str(settings.BASE_DIR / 'scripts/production.py'),
                                         '--env-file', str(path), 'configure', '--url', url],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(path.exists())

    def test_production_paths_and_proxy_header_are_configurable(self):
        environment = {**os.environ, 'DEBUG': 'false', 'SECRET_KEY': 'test-secret-' * 8,
                       'ALLOWED_HOSTS': 'example.test', 'TRUST_PROXY_HEADERS': 'true',
                       'MEDIA_ROOT': '/data/media', 'PRIVATE_DOCUMENT_ROOT': '/data/private',
                       'STATIC_ROOT': '/data/static', 'FILE_UPLOAD_TEMP_DIR': '/data/tmp',
                       'SESSION_COOKIE_SECURE': 'true', 'CSRF_COOKIE_SECURE': 'true',
                       'SECURE_SSL_REDIRECT': 'true',
                       'BACKUP_CONTROL_ROOT': '/data/control', 'PYTHONPATH': str(settings.BACKEND_DIR)}
        code = ('from ancore import settings as s; '
                'assert str(s.MEDIA_ROOT)=="/data/media"; '
                'assert str(s.PRIVATE_DOCUMENT_ROOT)=="/data/private"; '
                'assert str(s.STATIC_ROOT)=="/data/static"; '
                'assert s.FILE_UPLOAD_TEMP_DIR=="/data/tmp"; '
                'assert s.BACKUP_CONTROL_ROOT=="/data/control"; '
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
