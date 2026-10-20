"""Coordinated, unencrypted pg_dump + application files; no Docker socket."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
import uuid


CONTROL = Path(os.getenv('BACKUP_CONTROL_ROOT', '/control'))
DESTINATION = Path(os.getenv('BACKUP_DESTINATION', '/backups'))
SOURCE = Path(os.getenv('BACKUP_SOURCE', '/source'))


@contextmanager
def maintenance():
    # Never create requests.lock as root: Django's volume owns this file.
    with (CONTROL / 'backup.lock').open('a+b') as running:
        fcntl.flock(running, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = CONTROL / 'maintenance'
        if marker.exists():
            raise RuntimeError('Pozostała blokada poprzedniej operacji. Sprawdź stan i użyj unlock.')
        marker.touch(exist_ok=False)
        try:
            with (CONTROL / 'requests.lock').open('rb') as requests:
                # Wait until HTTP requests, streaming downloads and callbacks finish.
                fcntl.flock(requests, fcntl.LOCK_EX)
                yield
        finally:
            marker.unlink(missing_ok=True)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prune(keep):
    if keep < 1:
        raise ValueError('BACKUP_KEEP musi wynosić co najmniej 1.')
    archives = sorted(DESTINATION.glob('ancore-*.tar.gz'), reverse=True)
    for archive in archives[keep:]:
        archive.unlink()
        archive.with_name(archive.name + '.sha256').unlink(missing_ok=True)


def backup():
    keep = int(os.getenv('BACKUP_KEEP', '14'))
    if keep < 1:
        raise ValueError('BACKUP_KEEP musi wynosić co najmniej 1.')
    DESTINATION.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = 'ancore-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    archive = DESTINATION / (name + '.tar.gz')
    partial = archive.with_name(archive.name + '.partial')
    try:
        with tempfile.TemporaryDirectory(prefix='.ancore-', dir=DESTINATION) as temporary:
            staging = Path(temporary)
            with maintenance():
                subprocess.run(['pg_dump', '--format=custom', '--no-owner', '--no-acl',
                                '--file', str(staging / 'database.dump')], check=True, timeout=3600)
                metadata = {'format': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                            'release': os.getenv('ANCORE_RELEASE', 'local'), 'encrypted': False}
                (staging / 'manifest.json').write_text(json.dumps(metadata), encoding='utf-8')
                with tarfile.open(partial, 'w:gz') as output:
                    output.add(staging / 'database.dump', arcname='database.dump')
                    output.add(staging / 'manifest.json', arcname='manifest.json')
                    for directory in ('private', 'media'):
                        output.add(SOURCE / directory, arcname=directory)
            with partial.open('rb') as stream:
                os.fsync(stream.fileno())
            checksum = digest(partial)
            checksum_path = archive.with_name(archive.name + '.sha256')
            checksum_path.write_text(checksum + '  ' + archive.name + '\n', encoding='ascii')
            partial.replace(archive)
        prune(keep)
        (CONTROL / 'last-backup').write_text(str(time.time()), encoding='ascii')
        print(f'Zapisano backup: {archive.name}', flush=True)
        return archive
    finally:
        partial.unlink(missing_ok=True)


def restore(archive):
    # Called only with the backend and ONLYOFFICE stopped by production.py.
    checksum = archive.with_name(archive.name + '.sha256')
    if not checksum.is_file() or checksum.read_text().split()[0] != digest(archive):
        raise ValueError('Brak lub nieprawidłowa suma SHA-256 archiwum.')
    with tempfile.TemporaryDirectory(prefix='.restore-', dir=DESTINATION) as temporary:
        staging = Path(temporary)
        with tarfile.open(archive, 'r:gz') as source:
            for entry in source.getmembers():
                parts = Path(entry.name).parts
                if (not parts or parts[0] not in {'database.dump', 'manifest.json', 'private', 'media'}
                        or entry.issym() or entry.islnk() or not (entry.isfile() or entry.isdir())):
                    raise ValueError('Nieprawidłowa zawartość archiwum.')
            source.extractall(staging, filter='data')
        metadata = json.loads((staging / 'manifest.json').read_text())
        if metadata.get('format') != 1 or not all((staging / name).is_dir() for name in ('private', 'media')):
            raise ValueError('Nieobsługiwany format backupu.')
        subprocess.run(['pg_restore', '--clean', '--if-exists', '--no-owner', '--no-acl',
                        '--single-transaction', '--exit-on-error', '--dbname', os.environ['PGDATABASE'],
                        str(staging / 'database.dump')], check=True, timeout=3600)
        for name in ('private', 'media'):
            target = SOURCE / name
            for child in target.iterdir():
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            shutil.copytree(staging / name, target, dirs_exist_ok=True)
            for root, directories, files in os.walk(target):
                os.chown(root, 10001, 10001)
                os.chmod(root, 0o750)
                for filename in files:
                    path = Path(root) / filename
                    os.chown(path, 10001, 10001)
                    os.chmod(path, 0o640)
        print('Odtworzono bazę i zapisane pliki. Uruchom usługi aplikacji.', flush=True)


def unlock():
    with (CONTROL / 'backup.lock').open('a+b') as running:
        fcntl.flock(running, fcntl.LOCK_EX | fcntl.LOCK_NB)
        (CONTROL / 'maintenance').unlink(missing_ok=True)
    print('Usunięto pozostałą blokadę.', flush=True)


def health():
    interval = int(os.getenv('BACKUP_INTERVAL_SECONDS', '86400'))
    stamp = CONTROL / 'last-backup'
    if not stamp.exists() or time.time() - float(stamp.read_text()) > interval + 7200:
        raise RuntimeError('Brak aktualnego poprawnego backupu.')


def schedule():
    interval = int(os.getenv('BACKUP_INTERVAL_SECONDS', '86400'))
    if interval < 60:
        raise ValueError('BACKUP_INTERVAL_SECONDS musi wynosić co najmniej 60.')
    while True:
        stamp = CONTROL / 'last-backup'
        last = float(stamp.read_text()) if stamp.exists() else 0
        if time.time() >= last + interval:
            try:
                backup()
            except Exception as error:
                print(f'Backup nie powiódł się: {type(error).__name__}: {error}', flush=True)
                time.sleep(60)
        time.sleep(30)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('schedule', 'once', 'restore', 'unlock', 'health'))
    parser.add_argument('archive', nargs='?')
    args = parser.parse_args()
    def terminate(_signal, _frame):
        raise SystemExit(143)
    signal.signal(signal.SIGTERM, terminate)
    if args.command == 'restore':
        if not args.archive:
            parser.error('Podaj archiwum do odtworzenia.')
        restore(Path(args.archive))
    else:
        {'schedule': schedule, 'once': backup, 'unlock': unlock, 'health': health}[args.command]()


if __name__ == '__main__':
    main()
