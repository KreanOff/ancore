from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from http.client import HTTPConnection
from pathlib import Path
from runpy import run_path
import socket
from socketserver import ThreadingMixIn
from tempfile import TemporaryDirectory
from threading import Thread
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from django.conf import settings
from django.core.files.base import ContentFile
from django.test import SimpleTestCase

from core.file_storage import RemoteFileStorage


class ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class QuietRequestHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


class FileStorageTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        source = settings.BASE_DIR / 'deploy/storage/file_service.py'
        cls.make_application = staticmethod(run_path(str(source))['make_application'])

    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.private_root = Path(directory.name, 'private')
        self.private_root.mkdir()
        self.media_root = Path(directory.name, 'media')
        self.media_root.mkdir()

        application = self.make_application(self.private_root, self.media_root)
        server = make_server('127.0.0.1', 0, application, ThreadedServer, QuietRequestHandler)
        self.addCleanup(server.server_close)
        thread = Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, timeout=5)
        self.addCleanup(server.shutdown)

        self.address = f'127.0.0.1:{server.server_port}'
        self.private = RemoteFileStorage(self.address, 'private')
        self.media = RemoteFileStorage(self.address, 'media', base_url='/media/')

    def test_reads_existing_private_files_by_their_current_keys(self):
        name = 'space_task_files/zażółć #100%.pdf'
        path = self.private_root / name
        path.parent.mkdir()
        path.write_bytes(b'%PDF-test-file')

        self.assertTrue(self.private.exists(name))
        self.assertEqual(self.private.size(name), path.stat().st_size)
        with self.private.open(name, 'rb') as source:
            self.assertEqual(source.read(4), b'%PDF')
            source.seek(0)
            self.assertEqual(source.read(), path.read_bytes())
        self.assertFalse(self.media.exists(name))
        with self.assertRaises(NotImplementedError):
            self.private.url(name)

    def test_concurrent_uploads_keep_both_files_within_max_length(self):
        name = 'space_task_files/' + 'ź' * 24 + '.txt'
        payloads = (b'first upload', b'second upload')

        def save(data):
            return self.private.save(name, ContentFile(data), max_length=len(name))

        with ThreadPoolExecutor(max_workers=2) as executor:
            names = list(executor.map(save, payloads))

        self.assertIn(name, names)
        self.assertEqual(len(set(names)), 2)
        for stored_name, data in zip(names, payloads):
            with self.subTest(name=stored_name):
                self.assertLessEqual(len(stored_name), len(name))
                self.assertEqual(Path(stored_name).parent.as_posix(), 'space_task_files')
                self.assertEqual(Path(stored_name).suffix, '.txt')
                self.assertEqual((self.private_root / stored_name).read_bytes(), data)

    def test_media_preserves_url_and_file_deletion_is_idempotent(self):
        name = 'profile_photos/żółty obraz.png'
        self.assertEqual(self.media.save(name, ContentFile(b'avatar')), name)
        self.assertEqual(self.media.url(name), '/media/profile_photos/%C5%BC%C3%B3%C5%82ty%20obraz.png')
        with self.media.open(name) as source:
            self.assertEqual(source.read(), b'avatar')
        self.assertFalse(self.private.exists(name))

        self.media.delete(name)
        self.media.delete(name)
        self.assertFalse(self.media.exists(name))
        with self.assertRaises(FileNotFoundError):
            self.media.open(name)

    def test_interrupted_upload_leaves_no_file(self):
        name = 'space_task_files/partial.txt'
        with closing(HTTPConnection(self.address, timeout=5)) as connection:
            connection.request('POST', f'/private/{name}', b'short body', {'Content-Length': '100'})
            connection.sock.shutdown(socket.SHUT_WR)
            with connection.getresponse() as response:
                self.assertEqual(response.status, 400)

        self.assertFalse(self.private.exists(name))
        self.assertFalse(any(path.is_file() for path in self.private_root.rglob('*')))
        self.assertEqual(self.private.save(name, ContentFile(b'complete')), name)

    def test_parent_traversal_cannot_reach_data_in_another_scope(self):
        file = self.media_root / 'avatar.png'
        file.write_bytes(b'avatar')
        with closing(HTTPConnection(self.address, timeout=5)) as connection:
            connection.request('DELETE', '/private/%2E%2E/media/avatar.png')
            with connection.getresponse() as response:
                self.assertEqual(response.status, 400)
        self.assertEqual(file.read_bytes(), b'avatar')
