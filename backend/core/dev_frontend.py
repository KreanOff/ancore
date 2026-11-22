"""Keep the local runserver bundle in sync without a persistent Node process."""
import atexit
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time
from urllib.parse import urlsplit

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, JsonResponse


class FrontendBuildError(Exception):
    pass


class FrontendBuilder:
    def __init__(self, root, stdout):
        self.root = Path(root)
        self.frontend = self.root / 'frontend/app'
        self.stdout = stdout
        self.lock = threading.Lock()
        self.ready = None
        self.failed = None
        self.failed_at = 0
        self.error = ''

    def environment(self):
        environment = os.environ.copy()
        if settings.FRONTEND_BUILD_PATH:
            environment['PATH'] = (
                settings.FRONTEND_BUILD_PATH + os.pathsep + environment.get('PATH', '')
            )
        return environment

    def fingerprint(self):
        paths = set((self.frontend / 'src').rglob('*'))
        paths.update(self.frontend.glob('*.json'))
        paths.update(self.frontend.glob('*.mjs'))
        paths.update(self.frontend.glob('*.yaml'))
        paths.update(self.frontend / name for name in (
            '.npmrc', 'node_modules/.modules.yaml',
            'node_modules/typescript/package.json', 'node_modules/esbuild/package.json',
        ))
        digest = hashlib.sha256()
        for path in sorted(paths):
            if not path.is_file():
                continue
            digest.update(str(path.relative_to(self.frontend)).encode())
            digest.update(b'\0')
            digest.update(path.read_bytes())
            digest.update(b'\0')
        digest.update(str(shutil.which('pnpm', path=self.environment().get('PATH'))).encode())
        return digest.hexdigest()

    def bundle(self):
        directory = self.root / 'static/frontend'
        try:
            content = (directory / 'manifest.json').read_bytes()
            entry = json.loads(content)['main']
            if not isinstance(entry, str) or not (directory / entry).is_file():
                return None
            return content
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def build(self):
        environment = self.environment()
        executable = shutil.which('pnpm', path=environment.get('PATH'))
        if not executable:
            raise FrontendBuildError(
                'Brak pnpm w PATH. Zainstaluj Node.js 22+ i pnpm 11 lub ustaw '
                'FRONTEND_BUILD_PATH w .env na katalogi z tymi narzędziami.'
            )
        self.stdout.write('Ancore: przebudowa frontendu (TypeScript + bundle)…\n')
        process = subprocess.Popen(
            # pnpm 11 otherwise installs dependencies implicitly before scripts.
            [executable, '--config.verify-deps-before-run=false', 'build'], cwd=self.frontend,
            env=environment,
            start_new_session=os.name == 'posix',
        )

        def stop():
            if process.poll() is None:
                try:
                    if os.name == 'posix':
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                except ProcessLookupError:
                    pass
                process.wait()

        # Django reload may exit the main thread while a request is building.
        atexit.register(stop)
        try:
            result = process.wait(timeout=120)
            if result:
                raise FrontendBuildError(
                    'Nie udało się przebudować frontendu. Popraw błędy wskazane w terminalu '
                    'runserver i odśwież stronę. Zależności instaluj przez '
                    'pnpm --dir frontend/app install --frozen-lockfile.'
                )
        except subprocess.TimeoutExpired as error:
            raise FrontendBuildError('Przebudowa frontendu przekroczyła limit 120 sekund.') from error
        finally:
            stop()
            atexit.unregister(stop)

    def ensure_current(self):
        # Check inside the lock so simultaneous browser requests share one build.
        with self.lock:
            try:
                for _ in range(3):
                    source = self.fingerprint()
                    bundle = self.bundle()
                    state = (source, bundle)
                    if bundle is not None and state == self.ready:
                        return
                    if state == self.failed and time.monotonic() - self.failed_at < 5:
                        raise FrontendBuildError(self.error)
                    try:
                        self.build()
                    except FrontendBuildError as error:
                        self.failed = (source, self.bundle())
                        self.failed_at = time.monotonic()
                        self.error = str(error)
                        raise
                    # A checkout/save during compilation must not certify a stale bundle.
                    if self.fingerprint() != source:
                        continue
                    bundle = self.bundle()
                    if bundle is None:
                        raise FrontendBuildError('Przebudowa nie utworzyła poprawnego manifestu frontendu.')
                    self.ready = (source, bundle)
                    self.failed = None
                    return
                raise FrontendBuildError('Kod zmienił się podczas przebudowy. Odśwież stronę, aby ponowić.')
            except OSError as error:
                raise FrontendBuildError(
                    'Nie można odczytać lub zbudować frontendu. Sprawdź pliki, zależności i PATH.'
                ) from error


class FrontendBuildHandler:
    def __init__(self, application, builder, static_url):
        self.application = application
        self.builder = builder
        self.static_path = urlsplit(static_url).path

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if not ((self.static_path and path.startswith(self.static_path)) or path.startswith('/health/')):
            try:
                self.builder.ensure_current()
            except FrontendBuildError as error:
                request = WSGIRequest(environ)
                if '/api/' in path or 'application/json' in request.headers.get('Accept', ''):
                    response = JsonResponse({'message': str(error)}, status=503)
                else:
                    response = HttpResponse(str(error), status=503, content_type='text/plain; charset=utf-8')
                response['Cache-Control'] = 'no-store'
                start_response(f'{response.status_code} {response.reason_phrase}', list(response.items()))
                return [response.content]
        return self.application(environ, start_response)
