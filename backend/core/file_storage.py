"""Django file storage backed by Ancore's internal production service."""

from contextlib import contextmanager
from http.client import HTTPConnection, HTTPException
from shutil import copyfileobj
from tempfile import SpooledTemporaryFile
from urllib.parse import quote

from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage, Storage
from django.core.files.utils import validate_file_name
from django.utils.encoding import filepath_to_uri


class RemoteFileStorage(Storage):
    def __init__(self, address, scope, base_url=None):
        self.address = address
        self.scope = scope
        self.base_url = base_url

    @contextmanager
    def _request(self, method, name, *, body=None, headers=None):
        path = f'/{self.scope}/{quote(str(name), safe="/")}'
        connection = HTTPConnection(self.address, timeout=60)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            with connection.getresponse() as response:
                yield response
        except HTTPException as error:
            raise OSError('Nie udało się odczytać odpowiedzi magazynu plików.') from error
        finally:
            connection.close()

    @staticmethod
    def _require_status(response, status):
        if response.status == 404:
            raise FileNotFoundError('Plik jest niedostępny.')
        if response.status != status:
            raise OSError(f'Magazyn plików zwrócił kod HTTP {response.status}.')

    def save(self, name, content, max_length=None):
        if name is None:
            name = content.name
        name = str(name).replace('\\', '/')
        validate_file_name(name, allow_relative_path=True)
        if not hasattr(content, 'chunks'):
            content = File(content, name)
        headers = {'Content-Length': str(content.size)}
        if max_length is not None:
            headers['X-File-Max-Length'] = str(max_length)
        # The service selects the available name and publishes it atomically.
        with self._request('POST', name, body=content.chunks(), headers=headers) as response:
            self._require_status(response, 201)
            return validate_file_name(response.read().decode('utf-8'), allow_relative_path=True)

    def _open(self, name, mode='rb'):
        if mode != 'rb':
            raise ValueError('Pliki z magazynu można otwierać do odczytu binarnego.')
        # ZIP/Office previews need seek(). Larger reads spill to Django's upload temp directory.
        with self._request('GET', name) as response:
            self._require_status(response, 200)
            buffer = SpooledTemporaryFile(
                max_size=max(1, settings.FILE_UPLOAD_MAX_MEMORY_SIZE),
                dir=settings.FILE_UPLOAD_TEMP_DIR,
            )
            try:
                copyfileobj(response, buffer)
                if buffer.tell() != int(response.headers['Content-Length']):
                    raise OSError('Magazyn plików zwrócił niekompletny plik.')
                buffer.seek(0)
                return File(buffer, name=name)
            except BaseException:
                buffer.close()
                raise

    def exists(self, name):
        with self._request('HEAD', name) as response:
            if response.status == 404:
                return False
            self._require_status(response, 200)
            return True

    def size(self, name):
        with self._request('HEAD', name) as response:
            self._require_status(response, 200)
            return int(response.headers['Content-Length'])

    def delete(self, name):
        with self._request('DELETE', name) as response:
            self._require_status(response, 204)

    def url(self, name):
        if self.base_url is None:
            raise NotImplementedError('Prywatne pliki są dostępne przez widoki Ancore.')
        return self.base_url.rstrip('/') + '/' + filepath_to_uri(name).lstrip('/')


def private_storage():
    if settings.FILE_STORAGE_ADDRESS:
        return RemoteFileStorage(settings.FILE_STORAGE_ADDRESS, 'private')
    return FileSystemStorage(location=settings.PRIVATE_DOCUMENT_ROOT)
