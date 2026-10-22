"""Recovery of saved data and deployment, using isolated files and a controlled Docker CLI."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from core.test_production_installer import FAKE_DOCKER


def load_backup():
    spec = importlib.util.spec_from_file_location('ancore_backup_test', settings.BASE_DIR / 'deploy/backup/backup.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checksum(archive):
    archive.with_name(archive.name + '.sha256').write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')


class StandaloneRecoveryTests(SimpleTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ancore-recovery-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.home = self.root / 'standalone with spaces'
        self.home.mkdir()
        shutil.copyfile(settings.BASE_DIR / 'restore.sh', self.home / 'restore.sh')
        self.backups = self.root / 'backups with spaces'
        self.backups.mkdir()
        self.target = self.root / 'recovered installations'
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        for name in ('docker', 'docker-compose'):
            script = self.bin / name
            script.write_text(f'#!{sys.executable}\n' + FAKE_DOCKER)
            script.chmod(0o700)
        self.calls = self.root / 'calls.jsonl'
        self.environment = {key: value for key, value in os.environ.items()
                            if not key.startswith(('DOCKER_', 'INSTALLER_', 'ANCORE_'))}
        self.environment.update(PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                                INSTALLER_CALLS=str(self.calls))

    def archive(self, day=22, version=2, tls=False, unsafe=None, nested_unsafe=None):
        fixture = self.root / f'fixture-{day}'
        fixture.mkdir()
        source = fixture / 'source'
        source.mkdir()
        names = ('manage.py', 'requirements.txt', 'ancore.sh', 'restore.sh', '.dockerignore',
                 'deploy/compose.yaml', 'deploy/compose.restore.yaml', 'deploy/compose.tls.yaml',
                 'deploy/Dockerfile', 'deploy/backup/backup.py', 'deploy/cli/runtime.sh',
                 'frontend/app/pnpm-lock.yaml', 'frontend/board/pnpm-lock.yaml')
        for name in names:
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(settings.BASE_DIR / name, target)
        (source / 'backend').mkdir()
        (source / 'backend/recovered.txt').write_text(f'version-{day}')
        (source / 'deploy/compose.recovery.yaml').write_text('old volume names')
        payload = fixture / 'payload'
        (payload / 'recovery').mkdir(parents=True)
        for name in ('media', 'private'):
            (payload / name).mkdir()
            (payload / name / 'saved.txt').write_text(f'saved-{name}-{day}')
        (payload / 'database.dump').write_bytes(b'PGDMP fixture')
        (payload / 'manifest.json').write_text(json.dumps({'format': version, 'release': 'local'}))
        configured = subprocess.run(
            [sys.executable, str(settings.BASE_DIR / 'deploy/cli/configure.py'),
             '--env-file', str(payload / 'recovery/production.env'),
             '--backup-dir', str(self.backups)], capture_output=True, text=True)
        self.assertEqual(configured.returncode, 0, configured.stderr)
        if tls:
            path = payload / 'recovery/production.env'
            path.write_text(path.read_text().replace("ANCORE_TLS_MODE='http'", "ANCORE_TLS_MODE='direct'"))
            (payload / 'recovery/tls').mkdir()
            for name in ('fullchain.pem', 'privkey.pem'):
                (payload / 'recovery/tls' / name).write_text('fixture certificate')
        with tarfile.open(payload / 'recovery/application.tar.gz', 'w:gz') as output:
            output.add(source, arcname='.')
            if nested_unsafe:
                entry = tarfile.TarInfo(nested_unsafe)
                entry.size = 1
                output.addfile(entry, io.BytesIO(b'x'))
        archive = self.backups / f'ancore-202610{day:02}T120000-00000000.tar.gz'
        with tarfile.open(archive, 'w:gz') as output:
            for name in ('database.dump', 'manifest.json', 'private', 'media', 'recovery'):
                output.add(payload / name, arcname=name)
            if unsafe:
                entry = tarfile.TarInfo(unsafe)
                entry.size = 1
                output.addfile(entry, io.BytesIO(b'x'))
        checksum(archive)
        return archive

    def run_recovery(self, answers='1\n', *arguments, **environment):
        return subprocess.run(
            ['sh', str(self.home / 'restore.sh'), '--backup-dir', str(self.backups),
             '--target', str(self.target), *arguments], cwd=self.root, input=answers,
            capture_output=True, text=True, timeout=30,
            env={**self.environment, **environment})

    def commands(self, action):
        if not self.calls.exists():
            return []
        return [call for line in self.calls.read_text().splitlines()
                if action in (call := json.loads(line)) and '--help' not in call]

    def test_menu_lists_ten_newest_complete_archives_and_cancel_never_mutates_services(self):
        for day in range(1, 13):
            archive = self.backups / f'ancore-202610{day:02}T120000-00000000.tar.gz'
            archive.touch()
            checksum(archive)
        (self.backups / 'ancore-20261030T120000-00000000.tar.gz').touch()
        (self.backups / 'ancore-20261031T120000-00000000.tar.gz.partial').touch()
        result = self.run_recovery('0\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('ancore-20261012T', result.stdout)
        self.assertIn('ancore-20261003T', result.stdout)
        self.assertNotIn('ancore-20261002T', result.stdout)
        self.assertNotIn('ancore-20261030T', result.stdout)
        self.assertFalse(self.commands('build'))
        self.assertFalse(self.commands('stop'))
        self.assertFalse(self.target.exists())

    def test_standalone_recovers_selected_version_without_installer_or_host_application(self):
        self.archive(day=21)
        selected = self.archive(day=22)
        result = self.run_recovery('99\n2\n', INSTALLER_STANDALONE='1')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.home / 'ancore.sh').exists())
        application = next(self.target.glob('restore-*/application'))
        self.assertEqual((application / 'backend/recovered.txt').read_text(), 'version-21')
        config = (application / 'deploy/.env').read_text()
        self.assertIn("BACKUP_KEEP='10'", config)
        self.assertIn("BACKUP_INTERVAL_SECONDS='86400'", config)
        self.assertIn(f"ANCORE_BACKUP_DIR='{self.backups}'", config)
        self.assertEqual((application / 'deploy/.env').stat().st_mode & 0o777, 0o600)
        original = (self.root / 'fixture-21/payload/recovery/production.env').read_text()
        secret = next(line for line in original.splitlines() if line.startswith('SECRET_KEY='))
        self.assertIn(secret, config)
        self.assertNotIn(secret.partition('=')[2].strip("'"), result.stdout + result.stderr)
        override = json.loads((application / 'deploy/compose.recovery.yaml').read_text())
        self.assertTrue(all('_recovery_' in value['name'] for value in override['volumes'].values()))
        self.assertEqual(len(override['volumes']), 12)
        self.assertTrue(selected.exists())
        self.assertIn('Odzyskano aplikację', result.stdout)
        self.assertEqual(len(self.commands('build')), 1)
        restore = next(call for call in self.commands('run') if 'restore-prepared' in call)
        self.assertIn(str(application / 'deploy/compose.restore.yaml'), restore)
        self.assertIn(str(application / 'deploy/compose.recovery.yaml'), restore)
        self.assertFalse(self.commands('down'))
        self.assertTrue(self.commands('rm'))

    def test_integrity_legacy_and_unsafe_archives_fail_before_building_or_stopping(self):
        scenarios = (
            {'version': 1}, {'unsafe': 'private/../../escaped.txt'},
            {'unsafe': '/absolute.txt'}, {'nested_unsafe': './backend/../../../escaped.txt'},
            {'unsafe': 'unexpected.txt'}, {'corrupt': True},
        )
        for day, options in enumerate(scenarios, 1):
            with self.subTest(options=options):
                archive = self.archive(day=day, **{key: value for key, value in options.items() if key != 'corrupt'})
                if options.get('corrupt'):
                    archive.write_bytes(archive.read_bytes() + b'corruption')
                result = self.run_recovery()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertFalse(self.commands('build'))
                self.assertFalse(self.commands('stop'))
                self.assertNotIn('Odzyskano aplikację', result.stdout)
                archive.unlink()
                archive.with_name(archive.name + '.sha256').unlink()

    def test_build_and_dump_validation_errors_leave_existing_application_running(self):
        self.archive()
        for environment in ({'INSTALLER_BUILD_ERROR': '1'}, {'INSTALLER_DUMP_ERROR': '1'},
                            {'INSTALLER_LOCKED': '1'}):
            with self.subTest(environment=environment):
                self.calls.unlink(missing_ok=True)
                result = self.run_recovery(**environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.commands('stop'))
                self.assertNotIn('Odzyskano aplikację', result.stdout)

    def test_restore_or_start_failure_never_reports_success_and_stops_writers(self):
        self.archive()
        for environment in ({'INSTALLER_RESTORE_ERROR': '1'}, {'INSTALLER_START_ERROR': '1'}):
            with self.subTest(environment=environment):
                self.calls.unlink(missing_ok=True)
                result = self.run_recovery(**environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Odzyskano aplikację', result.stdout)
                self.assertIn('Usługi aplikacji pozostały zatrzymane', result.stderr)
                self.assertEqual(len(self.commands('stop')), 2)
                self.assertFalse(self.commands('down'))

    def test_tls_is_restored_and_compose_uses_archived_certificates(self):
        self.archive(tls=True)
        result = self.run_recovery()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        application = next(self.target.glob('restore-*/application'))
        certificate = application / 'deploy/certs/privkey.pem'
        self.assertEqual(certificate.read_text(), 'fixture certificate')
        self.assertEqual(certificate.stat().st_mode & 0o777, 0o600)
        self.assertIn(str(application / 'deploy/compose.tls.yaml'), self.commands('build')[0])

    def test_empty_directory_eof_and_remote_docker_never_stop_services(self):
        result = self.run_recovery()
        self.assertNotEqual(result.returncode, 0)
        self.archive()
        for answers, environment in (('', {}), ('1\n', {'INSTALLER_ENDPOINT': 'tcp://remote:2375'})):
            with self.subTest(answers=answers):
                result = self.run_recovery(answers, **environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.commands('stop'))


class BackupArchiveTests(SimpleTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ancore-backup-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.backup = load_backup()
        self.backup.SOURCE = self.root / 'source'
        self.backup.CONTROL = self.root / 'control'
        self.backup.DESTINATION = self.root / 'backups'
        self.backup.APPLICATION = self.root / 'application.tar.gz'
        for directory in (self.backup.SOURCE, self.backup.CONTROL, self.backup.DESTINATION):
            directory.mkdir()
        (self.backup.CONTROL / 'requests.lock').touch()
        self.backup.APPLICATION.write_bytes(b'application snapshot')
        (self.backup.SOURCE / 'production.env').write_text("SECRET_KEY='fixture'\n")
        for name in ('private', 'media'):
            (self.backup.SOURCE / name).mkdir()
            (self.backup.SOURCE / name / 'saved.txt').write_text('saved ' + name)
        environment = patch.dict(os.environ, {'PGDATABASE': 'ancore', 'BACKUP_KEEP': '10',
                                              'BACKUP_INTERVAL_SECONDS': '86400', 'BACKUP_TLS_MODE': 'direct'})
        environment.start()
        self.addCleanup(environment.stop)
        (self.backup.SOURCE / 'tls').mkdir()
        for name in ('fullchain.pem', 'privkey.pem'):
            (self.backup.SOURCE / 'tls' / name).write_text('fixture ' + name)

    @staticmethod
    def dump(command, **kwargs):
        Path(command[command.index('--file') + 1]).write_bytes(b'PGDMP fixture')

    def test_full_archive_contains_data_source_configuration_tls_and_prunes_to_ten(self):
        os.environ.pop('BACKUP_KEEP')
        for day in range(1, 13):
            archive = self.backup.DESTINATION / f'ancore-202001{day:02}T120000-00000000.tar.gz'
            archive.touch()
            checksum(archive)
        with patch.object(self.backup.subprocess, 'run', side_effect=self.dump):
            archive = self.backup.backup()
        self.assertEqual(len(list(self.backup.DESTINATION.glob('*.tar.gz'))), 10)
        self.assertEqual(len(list(self.backup.DESTINATION.glob('*.sha256'))), 10)
        self.assertEqual(archive.with_name(archive.name + '.sha256').read_text().split()[0],
                         hashlib.sha256(archive.read_bytes()).hexdigest())
        with tarfile.open(archive) as saved:
            self.assertEqual(json.load(saved.extractfile('manifest.json'))['format'], 2)
            for name in ('database.dump', 'private/saved.txt', 'media/saved.txt', 'recovery/application.tar.gz',
                         'recovery/production.env', 'recovery/tls/fullchain.pem', 'recovery/tls/privkey.pem'):
                self.assertTrue(saved.extractfile(name).read())
        self.assertFalse((self.backup.CONTROL / 'maintenance').exists())
        self.backup.health()

    def test_failed_backup_keeps_previous_copies_and_releases_maintenance(self):
        self.backup.APPLICATION.unlink()
        old = self.backup.DESTINATION / 'ancore-20200101T120000-00000000.tar.gz'
        old.write_bytes(b'previous')
        with patch.object(self.backup.subprocess, 'run', side_effect=self.dump), self.assertRaises(RuntimeError):
            self.backup.backup()
        self.assertEqual(old.read_bytes(), b'previous')
        self.assertFalse((self.backup.CONTROL / 'last-backup').exists())
        self.assertFalse((self.backup.CONTROL / 'maintenance').exists())
        self.assertFalse(list(self.backup.DESTINATION.glob('*.partial')))

    def test_restore_recovers_saved_files_and_initializes_fresh_control_volume(self):
        with patch.object(self.backup.subprocess, 'run', side_effect=self.dump):
            archive = self.backup.backup()
        (self.backup.SOURCE / 'private/saved.txt').write_text('lost content')
        (self.backup.SOURCE / 'private/new.txt').write_text('after backup')
        with patch.object(self.backup.subprocess, 'run') as restore, patch.object(self.backup.os, 'chown'):
            self.backup.restore(archive)
        self.assertEqual((self.backup.SOURCE / 'private/saved.txt').read_text(), 'saved private')
        self.assertFalse((self.backup.SOURCE / 'private/new.txt').exists())
        self.assertIn('--single-transaction', restore.call_args.args[0])
        self.backup.health()

    def test_legacy_data_only_archive_remains_restorable(self):
        payload = self.root / 'legacy'
        payload.mkdir()
        (payload / 'manifest.json').write_text('{"format": 1}')
        (payload / 'database.dump').write_bytes(b'PGDMP fixture')
        for name in ('private', 'media'):
            (payload / name).mkdir()
        (payload / 'private/legacy.txt').write_text('legacy data')
        archive = self.backup.DESTINATION / 'ancore-20200101T120000-00000000.tar.gz'
        with tarfile.open(archive, 'w:gz') as output:
            for name in ('database.dump', 'manifest.json', 'private', 'media'):
                output.add(payload / name, arcname=name)
        checksum(archive)
        with patch.object(self.backup.subprocess, 'run'), patch.object(self.backup.os, 'chown'):
            self.backup.restore(archive)
        self.assertEqual((self.backup.SOURCE / 'private/legacy.txt').read_text(), 'legacy data')

    def test_scheduler_runs_only_when_24_hours_have_elapsed_or_no_copy_exists(self):
        stamp = self.backup.CONTROL / 'last-backup'
        for age, expected in ((None, 1), (86399, 0), (86400, 1)):
            with self.subTest(age=age):
                if age is None:
                    stamp.unlink(missing_ok=True)
                else:
                    stamp.write_text(str(100000 - age))
                with patch.object(self.backup.time, 'time', return_value=100000), \
                        patch.object(self.backup, 'backup') as backup, \
                        patch.object(self.backup.time, 'sleep', side_effect=InterruptedError):
                    with self.assertRaises(InterruptedError):
                        self.backup.schedule()
                    self.assertEqual(backup.call_count, expected)
