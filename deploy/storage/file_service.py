"""Internal file service for the production private and media volumes."""

import os
import stat
from contextlib import contextmanager
from errno import ELOOP
from http import HTTPStatus
from uuid import uuid4
from wsgiref.util import FileWrapper

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import Storage
from django.core.files.utils import validate_file_name


DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
TEMP_PREFIX = '.ancore-upload-'
BLOCK_SIZE = 64 * 1024
FILE_METHODS = ('GET', 'HEAD', 'POST', 'DELETE')


def _response(start_response, status, body=b'', headers=()):
    headers = list(headers)
    if status != HTTPStatus.NO_CONTENT:
        headers.append(('Content-Length', str(len(body))))
    start_response(f'{status.value} {status.phrase}', headers)
    return [body] if body else []


def _path_parts(name):
    parts = name.split('/')
    if (any(part in {'', '.', '..'} or part.startswith(TEMP_PREFIX) for part in parts)
            or '\\' in name or '\x00' in name):
        raise ValueError('Invalid file name')
    validate_file_name(name, allow_relative_path=True)
    return parts


@contextmanager
def _directory(root, folders, *, create=False):
    """Walk via directory descriptors so path components cannot follow symlinks."""
    try:
        directory = os.open(root, DIRECTORY_FLAGS)
    except OSError as error:
        raise OSError('Storage volume is unavailable') from error
    try:
        for folder in folders:
            created = False
            if create:
                try:
                    os.mkdir(folder, 0o750, dir_fd=directory)
                    created = True
                except FileExistsError:
                    pass
            child = os.open(folder, DIRECTORY_FLAGS, dir_fd=directory)
            os.close(directory)
            directory = child
            if created:
                os.fchmod(directory, 0o750)
        yield directory
    finally:
        os.close(directory)


class _AvailableNames(Storage):
    """Apply Django's collision and max_length rules inside an opened parent."""

    def __init__(self, directory):
        self.directory = directory

    def exists(self, name):
        try:
            os.stat(name.rsplit('/', 1)[-1], dir_fd=self.directory, follow_symlinks=False)
        except FileNotFoundError:
            return False
        return True


def _content_length(value, *, minimum=0):
    if not value or not value.isascii() or not value.isdecimal():
        raise ValueError('Invalid length')
    length = int(value)
    if length < minimum:
        raise ValueError('Invalid length')
    return length


def _store(directory, name, source, length, max_length):
    naming = _AvailableNames(directory)
    candidate = naming.get_available_name(name, max_length=max_length)
    temporary = TEMP_PREFIX + uuid4().hex
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600, dir_fd=directory)
    try:
        with os.fdopen(descriptor, 'wb') as target:
            remaining = length
            while remaining:
                try:
                    chunk = source.read(min(remaining, BLOCK_SIZE))
                except OSError as error:
                    raise ValueError('Incomplete upload') from error
                if not chunk or len(chunk) > remaining:
                    raise ValueError('Incomplete upload')
                target.write(chunk)
                remaining -= len(chunk)
            os.fchmod(target.fileno(), 0o640)
        while True:
            try:
                os.link(temporary, candidate.rsplit('/', 1)[-1], src_dir_fd=directory,
                        dst_dir_fd=directory, follow_symlinks=False)
            except FileExistsError:
                candidate = naming.get_available_name(name, max_length=max_length)
            else:
                return candidate
    finally:
        os.unlink(temporary, dir_fd=directory)


def _read(environ, start_response, directory, filename, method):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    descriptor = os.open(filename, flags, dir_fd=directory)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise FileNotFoundError
        start_response('200 OK', [('Content-Type', 'application/octet-stream'),
                                  ('Content-Length', str(info.st_size))])
        if method == 'HEAD':
            return []
        source = os.fdopen(descriptor, 'rb')
        descriptor = None  # The response now owns the open file.
        return environ.get('wsgi.file_wrapper', FileWrapper)(source, BLOCK_SIZE)
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _delete(directory, filename):
    try:
        info = os.stat(filename, dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            return HTTPStatus.NOT_FOUND
        os.unlink(filename, dir_fd=directory)
    except FileNotFoundError:
        pass
    return HTTPStatus.NO_CONTENT


def _readiness(start_response, roots):
    try:
        for root in roots:
            with _directory(root, ()) as directory:
                if not os.access('.', os.R_OK | os.W_OK | os.X_OK, dir_fd=directory):
                    return _response(start_response, HTTPStatus.SERVICE_UNAVAILABLE)
    except OSError:
        return _response(start_response, HTTPStatus.SERVICE_UNAVAILABLE)
    return _response(start_response, HTTPStatus.OK)


def make_application(private_root, media_root):
    roots = {'private': private_root, 'media': media_root}

    def application(environ, start_response):
        try:
            path = environ['PATH_INFO'].encode('latin-1').decode('utf-8')
        except UnicodeError:
            return _response(start_response, HTTPStatus.BAD_REQUEST)
        method = environ['REQUEST_METHOD']
        if path == '/health/ready/':
            if method != 'GET':
                return _response(start_response, HTTPStatus.METHOD_NOT_ALLOWED, headers=(('Allow', 'GET'),))
            return _readiness(start_response, roots.values())

        bucket, _, name = path.removeprefix('/').partition('/')
        if bucket not in roots:
            return _response(start_response, HTTPStatus.NOT_FOUND)
        if method not in FILE_METHODS:
            return _response(start_response, HTTPStatus.METHOD_NOT_ALLOWED,
                             headers=(('Allow', ', '.join(FILE_METHODS)),))
        try:
            parts = _path_parts(name)
            if method == 'POST':
                length = _content_length(environ.get('CONTENT_LENGTH'))
                bound = environ.get('HTTP_X_FILE_MAX_LENGTH')
                max_length = _content_length(bound, minimum=1) if bound is not None else None
            with _directory(roots[bucket], parts[:-1], create=method == 'POST') as directory:
                if method == 'POST':
                    stored = _store(directory, name, environ['wsgi.input'], length, max_length)
                    return _response(start_response, HTTPStatus.CREATED, stored.encode('utf-8'),
                                     headers=(('Content-Type', 'text/plain; charset=utf-8'),))
                if method == 'DELETE':
                    return _response(start_response, _delete(directory, parts[-1]))
                return _read(environ, start_response, directory, parts[-1], method)
        except (ValueError, SuspiciousFileOperation):
            return _response(start_response, HTTPStatus.BAD_REQUEST)
        except FileNotFoundError:
            status = HTTPStatus.NO_CONTENT if method == 'DELETE' else HTTPStatus.NOT_FOUND
            return _response(start_response, status)
        except NotADirectoryError:
            return _response(start_response, HTTPStatus.NOT_FOUND)
        except OSError as error:
            if error.errno == ELOOP:
                return _response(start_response, HTTPStatus.NOT_FOUND)
            return _response(start_response, HTTPStatus.INTERNAL_SERVER_ERROR)

    return application


application = make_application('/data/private', '/data/media')
