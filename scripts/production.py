#!/usr/bin/env python3
"""Install and maintain Ancore's five-service Docker Compose deployment."""
import argparse
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / 'deploy'


def read_config(path):
    values = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition('=')
        if not separator or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key):
            raise ValueError('Nieprawidłowy plik konfiguracji.')
        if len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1]
        values[key] = value
    return values


def configure(args):
    path = args.env_file
    previous = path
    if not previous.exists() and path == DEPLOY / '.env' and (DEPLOY / '.env.production').exists():
        previous = DEPLOY / '.env.production'
    existing = previous.exists()
    config = read_config(previous) if existing else {}
    if existing and not args.reconfigure:
        if args.url and args.url.rstrip('/') != config['ANCORE_PUBLIC_URL']:
            raise ValueError('Instalacja ma już inny adres. Dodaj --reconfigure, aby zmienić adres bez wymiany sekretów.')
        if previous == path:
            print('Zachowano istniejącą konfigurację i sekrety.', flush=True)
            return config
        write_config(path, config)
        print('Przeniesiono istniejącą konfigurację do deploy/.env; zachowano sekrety.', flush=True)
        return config
    url = urlsplit(args.url or '')
    host = url.hostname or ''
    if args.url and (url.scheme not in {'http', 'https'} or not re.fullmatch(r'[a-zA-Z0-9.-]+', host)
            or url.username or url.password or url.query or url.fragment or url.path not in {'', '/'}):
        raise ValueError('Podaj bazowy adres HTTP(S) bez ścieżki i danych logowania.')
    if url.port is not None and not 1 <= url.port <= 65535:
        raise ValueError('Port adresu musi należeć do zakresu 1–65535.')
    project = args.project or config.get('ANCORE_PROJECT', 'ancore-prod')
    if existing and args.project and args.project != config['ANCORE_PROJECT']:
        raise ValueError('Zmiana protokołu nie może zmienić projektu i jego wolumenów.')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', project):
        raise ValueError('Nieprawidłowa nazwa projektu Compose.')
    for port in (args.http_port, args.https_port):
        if port is not None and not 1 <= port <= 65535:
            raise ValueError('Port musi należeć do zakresu 1–65535.')
    tls = args.tls_dir.resolve() if args.tls_dir else None
    if tls:
        if url.scheme != 'https':
            raise ValueError('Certyfikaty wymagają adresu HTTPS.')
        for name in ('fullchain.pem', 'privkey.pem'):
            if not (tls / name).is_file():
                raise ValueError(f'Brak pliku certyfikatu: {name}.')
            if not (tls / name).resolve().is_relative_to(tls):
                raise ValueError('Certyfikaty muszą znajdować się wewnątrz montowanego katalogu; skopiuj pliki zamiast zewnętrznych symlinków.')
    http_port = args.http_port or ((url.port or 80) if url.scheme == 'http' else config.get('ANCORE_HTTP_PORT', 8080))
    https_port = args.https_port or (url.port if tls else None) or 443
    if ((url.scheme == 'http' and int(http_port) != (url.port or 80))
            or (tls and https_port != (url.port or 443))):
        raise ValueError('Port w --url musi odpowiadać portowi udostępnianemu przez Ancore.')
    backup_dir = (args.backup_dir or Path(config.get('ANCORE_BACKUP_DIR', str(DEPLOY / 'backups')))).resolve()
    if not existing or args.backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    config.update({
        'ANCORE_PROJECT': project,
        'ANCORE_PUBLIC_URL': f'{url.scheme}://{url.netloc}' if args.url else '',
        'ANCORE_HOST': host or '_',
        'ANCORE_AUTHORITY': url.netloc or 'localhost',
        'ANCORE_ALLOWED_HOSTS': f'{host},localhost' if host else '*',
        'ANCORE_ALLOW_IP_HOSTS': str(not host).lower(),
        'ANCORE_SCHEME': url.scheme or 'http',
        'ANCORE_HTTPS': str(url.scheme == 'https').lower(),
        'ANCORE_HSTS_SECONDS': '31536000' if url.scheme == 'https' else '0',
        'ANCORE_TLS_MODE': 'direct' if tls else ('external' if url.scheme == 'https' else 'http'),
        'ANCORE_BIND': args.bind or ('127.0.0.1' if url.scheme == 'https' and not tls else '0.0.0.0'),
        'ANCORE_HTTP_PORT': str(http_port),
        'ANCORE_HTTPS_PORT': str(https_port),
        'ANCORE_TLS_DIR': str(tls or DEPLOY / 'certs'),
        'ANCORE_BACKUP_DIR': str(backup_dir),
    })
    for key, value in {
        'SECRET_KEY': secrets.token_urlsafe(64), 'POSTGRES_PASSWORD': secrets.token_hex(32),
        'POSTGRES_ADMIN_PASSWORD': secrets.token_hex(32), 'ONLYOFFICE_JWT_SECRET': secrets.token_hex(48),
        'BACKUP_INTERVAL_SECONDS': '86400', 'BACKUP_KEEP': '14', 'ANCORE_RELEASE': 'local',
        'ONLYOFFICE_IMAGE': 'onlyoffice/documentserver:10.0.0.1',
    }.items():
        config.setdefault(key, value)
    write_config(path, config, replace=path.exists())
    print(f'Przygotowano konfigurację: {path}. Sekrety nie są wyświetlane.', flush=True)
    return config


def write_config(path, config, replace=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    for value in config.values():
        if any(char in value for char in "\r\n'"):
            raise ValueError('Konfiguracja zawiera niedozwolony znak.')
    content = '# Ancore production — dane i backupy bez szyfrowania.\n'
    content += ''.join(f"{key}='{value}'\n" for key, value in config.items())
    if replace:
        descriptor, temporary = tempfile.mkstemp(prefix='.env.', dir=path.parent)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
                output.write(content)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
    else:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(content)


class Deployment:
    def __init__(self, args, config):
        self.config = config
        self.environment = dict(os.environ)
        # Explicit config wins over unrelated variables from the invoking shell.
        for key in config:
            self.environment.pop(key, None)
        if args.context:
            self.environment['DOCKER_CONTEXT'] = args.context
        docker = shutil.which('docker')
        if not docker:
            raise ValueError('Zainstaluj Docker Engine i Docker Compose przed instalacją Ancore.')
        probe = subprocess.run([docker, 'compose', 'version'], env=self.environment,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if probe.returncode == 0:
            self.command = [docker, 'compose']
        elif shutil.which('docker-compose'):
            self.command = [shutil.which('docker-compose')]
        else:
            raise ValueError('Brak Docker Compose.')
        self.command += ['--env-file', str(args.env_file), '-f', str(DEPLOY / 'compose.yaml')]
        if config['ANCORE_TLS_MODE'] == 'direct':
            self.command += ['-f', str(DEPLOY / 'compose.tls.yaml')]

    def run(self, *arguments, restore=False):
        command = list(self.command)
        if restore:
            command += ['-f', str(DEPLOY / 'compose.restore.yaml')]
        subprocess.run([*command, *arguments], cwd=ROOT, env=self.environment, check=True)

    def backup(self):
        self.run('exec', '-T', 'backup', 'python3', '/opt/ancore/backup.py', 'once')

    def restore(self, archive, confirmed):
        if not confirmed:
            raise ValueError('Odtworzenie zastępuje dane instalacji. Po sprawdzeniu archiwum dodaj --yes.')
        archive = archive.resolve()
        destination = Path(self.config['ANCORE_BACKUP_DIR']).resolve()
        if archive.parent != destination or not archive.is_file():
            raise ValueError('Archiwum musi znajdować się w skonfigurowanym katalogu backupów.')
        checksum = archive.with_name(archive.name + '.sha256')
        if not checksum.is_file():
            raise ValueError('Brak pliku .sha256 archiwum.')
        self.run('stop', 'web', 'backup', 'backend', 'onlyoffice')
        self.run('up', '-d', '--wait', 'postgres')
        # Failure deliberately leaves writers stopped, allowing recovery/retry.
        self.run('run', '--rm', '--no-deps', 'backup', 'restore', '/backups/' + archive.name, restore=True)
        self.run('run', '--rm', '--no-deps', 'backup', 'unlock')
        self.run('up', '-d', '--wait', '--wait-timeout', '600')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=DEPLOY / '.env')
    parser.add_argument('--context', help='Opcjonalny kontekst Docker; nie zmienia kontekstu globalnego.')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('configure', 'install'):
        command = commands.add_parser(name)
        command.add_argument('--url')
        command.add_argument('--project')
        command.add_argument('--backup-dir', type=Path)
        command.add_argument('--tls-dir', type=Path)
        command.add_argument('--http-port', type=int)
        command.add_argument('--https-port', type=int)
        command.add_argument('--bind', help='Adres nasłuchiwania, domyślnie 0.0.0.0 dla HTTP.')
        command.add_argument('--reconfigure', action='store_true', help='Zmień adres/protokół, zachowując sekrety i wolumeny.')
        command.add_argument('--allow-http', action='store_true', help=argparse.SUPPRESS)  # Older installation commands.
    for name in ('update', 'backup', 'status', 'stop', 'start', 'unlock', 'reload', 'admin'):
        commands.add_parser(name)
    restore = commands.add_parser('restore')
    restore.add_argument('archive', type=Path)
    restore.add_argument('--yes', action='store_true')
    args = parser.parse_args()
    args.env_file = args.env_file.resolve()
    try:
        config = configure(args) if args.command in {'configure', 'install'} else read_config(args.env_file)
        if args.command == 'configure':
            return
        deployment = Deployment(args, config)
        deployment.run('config', '--quiet')
        if args.command == 'install':
            deployment.run('build', '--pull')
            deployment.run('up', '-d', '--wait', '--wait-timeout', '600')
        elif args.command == 'update':
            deployment.backup()
            deployment.run('build', '--pull')
            deployment.run('up', '-d', '--wait', '--wait-timeout', '600')
        elif args.command == 'backup':
            deployment.backup()
        elif args.command == 'restore':
            deployment.restore(args.archive, args.yes)
        elif args.command == 'unlock':
            deployment.run('exec', '-T', 'backup', 'python3', '/opt/ancore/backup.py', 'unlock')
        elif args.command == 'status':
            deployment.run('ps')
        elif args.command == 'reload':
            deployment.run('exec', '-T', 'web', 'nginx', '-s', 'reload')
        elif args.command == 'admin':
            deployment.run('exec', 'backend', 'python', 'manage.py', 'createsuperuser')
        elif args.command == 'stop':
            deployment.run('stop')
        elif args.command == 'start':
            deployment.run('up', '-d', '--wait', '--wait-timeout', '600')
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Błąd: {error}\n')


if __name__ == '__main__':
    main()
