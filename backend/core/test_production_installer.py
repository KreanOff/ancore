"""Exercise the shell installer with a controlled Docker CLI, without real data."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from django.conf import settings
from django.test import SimpleTestCase


FAKE_DOCKER = r'''
import json, os, pathlib, subprocess, sys
args = sys.argv[1:]
with open(os.environ['INSTALLER_CALLS'], 'a') as output:
    output.write(json.dumps([pathlib.Path(sys.argv[0]).name, *args]) + '\n')
if pathlib.Path(sys.argv[0]).name == 'ss':
    print(os.getenv('INSTALLER_LISTENERS', ''))
    sys.exit(0)
if pathlib.Path(sys.argv[0]).name == 'docker-compose':
    args.insert(0, 'compose')
if args[0] == 'context':
    print(os.getenv('INSTALLER_ENDPOINT', 'unix:///var/run/docker.sock'))
elif args[0] == 'info':
    if os.getenv('INSTALLER_NO_ACCESS'):
        sys.exit(1)
    print('linux')
elif args[0] == 'run':
    index = next(index for index, argument in enumerate(args)
                 if argument == 'deploy/cli/configure.py' or argument.endswith('/recovery.py'))
    sys.exit(subprocess.call([sys.executable, *args[index:]]))
elif args[0] == 'create':
    sys.exit(1 if os.getenv('INSTALLER_LOCKED') else 0)
elif args[0] == 'rm':
    pass
elif args[0] == 'port':
    print(os.getenv('INSTALLER_WEB_PORTS', '80/tcp -> 0.0.0.0:8080'))
elif args[0] == 'ps':
    print(os.getenv('INSTALLER_OTHER_PORTS', ''))
elif args[0] == 'image':
    sys.exit(1 if os.getenv('INSTALLER_OFFICE_MISSING') else 0)
elif args[0] == 'compose':
    args.pop(0)
    if args[0] == 'version':
        sys.exit(1 if os.getenv('INSTALLER_STANDALONE') else 0)
    while args[0] in ('--env-file', '-f', '--project-name'):
        args = args[2:]
    if args[0] == 'up' and '--help' in args:
        print('--wait-timeout' if not os.getenv('INSTALLER_OLD_COMPOSE') else '--detach')
    elif args[0] == 'ps':
        if args[-1] == 'web':
            print(os.getenv('INSTALLER_WEB_ID', ''))
        elif args[-1] == 'backup':
            print(os.getenv('INSTALLER_BACKUP_ID', ''))
        else:
            print('backend web postgres backup onlyoffice')
    elif args[0] == 'build':
        sys.exit(1 if os.getenv('INSTALLER_BUILD_ERROR') else 0)
    elif args[0] == 'up':
        sys.exit(1 if os.getenv('INSTALLER_START_ERROR') else 0)
    elif args[0] == 'exec':
        sys.exit(1 if os.getenv('INSTALLER_EXEC_ERROR') else 0)
    elif args[0] == 'config':
        sys.exit(1 if os.getenv('INSTALLER_CONFIG_ERROR') else 0)
    elif args[0] == 'run' and 'restore' in args:
        sys.exit(1 if os.getenv('INSTALLER_RESTORE_ERROR') else 0)
    elif args[0] == 'run' and 'restore-prepared' in args:
        sys.exit(1 if os.getenv('INSTALLER_RESTORE_ERROR') else 0)
    elif args[0] == 'run' and 'pg_restore' in args:
        sys.exit(1 if os.getenv('INSTALLER_DUMP_ERROR') else 0)
else:
    raise RuntimeError(args)
'''


class ProductionInstallerTests(SimpleTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ancore-installer-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'repo with spaces'
        self.root.mkdir()
        for name in ('ancore.sh', 'deploy/cli/runtime.sh',
                     'deploy/cli/setup.sh', 'deploy/cli/configure.py', 'scripts/production.py',
                     'scripts/start_office.sh', 'scripts/office/start.sh',
                     'deploy/compose.yaml', 'deploy/compose.tls.yaml', 'deploy/compose.restore.yaml'):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(settings.BASE_DIR / name, target)
        self.bin = Path(temporary.name) / 'bin'
        self.bin.mkdir()
        for name in ('docker', 'docker-compose', 'ss'):
            script = self.bin / name
            script.write_text(f'#!{sys.executable}\n' + FAKE_DOCKER)
            script.chmod(0o700)
        self.calls = Path(temporary.name) / 'calls.jsonl'
        self.environment = {key: value for key, value in os.environ.items()
                            if not key.startswith(('DOCKER_', 'INSTALLER_', 'ANCORE_'))}
        self.environment.update(PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                                INSTALLER_CALLS=str(self.calls))

    def run_script(self, name, *arguments, answers='', **environment):
        return subprocess.run(['sh', str(self.root / name), *arguments],
                              input=answers, capture_output=True, text=True,
                              env={**self.environment, **environment}, cwd=self.bin, timeout=30)

    def config(self):
        path = self.root / 'deploy/.env'
        return dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)

    def commands(self, action):
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        return [call for call in calls if action in call and '--help' not in call]

    def prepare(self):
        result = self.run_script('ancore.sh', 'install', '--configure-only')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_wizard_saves_lan_configuration_without_starting_and_keeps_secrets(self):
        result = self.run_script('ancore.sh', 'setup', answers='192.0.2.10\n1\n8087\n1\n\nn\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        config = self.config()
        self.assertEqual(config['ANCORE_PUBLIC_URL'], "'http://192.0.2.10:8087'")
        self.assertEqual(config['ANCORE_BIND'], "'0.0.0.0'")
        self.assertFalse(self.commands('build'))
        self.assertFalse(self.commands('up'))
        repeated = self.run_script('ancore.sh', 'setup', answers='\n\n\n\n\nn\n')
        self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
        self.assertEqual(self.config(), config)
        self.assertEqual((self.root / 'deploy/.env').stat().st_mode & 0o777, 0o600)
        for key in ('SECRET_KEY', 'POSTGRES_PASSWORD', 'POSTGRES_ADMIN_PASSWORD', 'ONLYOFFICE_JWT_SECRET'):
            self.assertNotIn(config[key].strip("'"), result.stdout + result.stderr)

    def test_wizard_builds_then_waits_for_services_only_after_start_answer(self):
        result = self.run_script('ancore.sh', 'setup', answers='\n\n\n\n\nt\n', INSTALLER_OFFICE_MISSING='1')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.commands('build')), 1)
        self.assertIn('--wait', self.commands('up')[0])
        self.assertIn('--no-build', self.commands('up')[0])
        self.assertEqual(self.commands('pull')[0][-1], 'onlyoffice')
        self.assertIn('Usługi Ancore są gotowe.', result.stdout)

    def test_wizard_reprompts_invalid_port_and_host_and_handles_eof(self):
        result = self.run_script('ancore.sh', 'setup', answers='http://example.test:80\nexample.test\n1\nwrong\n999999999999999999999\n8087\n1\n\nn\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.config()['ANCORE_HTTP_PORT'], "'8087'")
        before = (self.root / 'deploy/.env').read_bytes()
        interrupted = self.run_script('ancore.sh', 'setup')
        self.assertNotEqual(interrupted.returncode, 0)
        self.assertEqual((self.root / 'deploy/.env').read_bytes(), before)

    def test_direct_https_is_managed_by_compose_including_later_start(self):
        tls = self.root / 'certificates with spaces'
        tls.mkdir()
        for name in ('fullchain.pem', 'privkey.pem'):
            (tls / name).write_text('fixture')
        result = self.run_script('ancore.sh', 'setup', answers=f'example.test\n2\n8080\n8443\n{tls}\n1\n\nn\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.config()['ANCORE_TLS_MODE'], "'direct'")
        started = self.run_script('ancore.sh', 'start')
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        self.assertIn(str((self.root / 'deploy/compose.tls.yaml').resolve()), self.commands('up')[-1])

    def test_existing_external_https_keeps_public_port_and_local_proxy_binding(self):
        configured = self.run_script('ancore.sh', 'install', '--url', 'https://example.test:8443', '--configure-only')
        self.assertEqual(configured.returncode, 0, configured.stdout + configured.stderr)
        result = self.run_script('ancore.sh', 'setup', answers='\n\n\n\n\nn\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.config()['ANCORE_PUBLIC_URL'], "'https://example.test:8443'")
        self.assertEqual(self.config()['ANCORE_BIND'], "'127.0.0.1'")

    def test_invalid_bind_and_colliding_tls_ports_never_write_configuration(self):
        tls = self.root / 'certs'
        tls.mkdir()
        for name in ('fullchain.pem', 'privkey.pem'):
            (tls / name).write_text('fixture')
        for arguments in (('--bind', 'server:8080'),
                          ('--url', 'https://example.test:8080', '--http-port', '8080', '--tls-dir', str(tls))):
            with self.subTest(arguments=arguments):
                result = self.run_script('ancore.sh', 'install', '--configure-only', *arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.root / 'deploy/.env').exists())

    def test_occupied_host_port_aborts_before_backup_or_build(self):
        result = self.run_script('ancore.sh', 'install', INSTALLER_LISTENERS='LISTEN 0 511 0.0.0.0:8080')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Port 8080 jest zajęty', result.stderr)
        self.assertFalse(self.commands('build'))
        self.assertFalse(self.commands('exec'))
        self.assertNotIn('są gotowe', result.stdout)

    def test_other_container_port_is_rejected_but_own_web_is_allowed(self):
        self.prepare()
        rejected = self.run_script('ancore.sh', 'start', INSTALLER_OTHER_PORTS='0.0.0.0:8080->80/tcp')
        self.assertNotEqual(rejected.returncode, 0)
        allowed = self.run_script('ancore.sh', 'start', INSTALLER_WEB_ID='own-web',
                                  INSTALLER_LISTENERS='LISTEN 0 511 0.0.0.0:8080')
        self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)

    def test_docker_access_remote_endpoint_and_old_compose_fail_before_configuration(self):
        for environment in ({'INSTALLER_NO_ACCESS': '1'}, {'INSTALLER_ENDPOINT': 'ssh://remote'},
                            {'INSTALLER_OLD_COMPOSE': '1'}):
            with self.subTest(environment=environment):
                result = self.run_script('ancore.sh', 'setup', **environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.root / 'deploy/.env').exists())

    def test_failed_build_or_start_never_reports_ready_and_update_keeps_backup(self):
        self.prepare()
        for environment in ({'INSTALLER_BUILD_ERROR': '1'}, {'INSTALLER_START_ERROR': '1'}):
            with self.subTest(environment=environment):
                result = self.run_script('ancore.sh', 'update', INSTALLER_BACKUP_ID='backup', **environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('są gotowe', result.stdout)
        self.assertTrue(self.commands('exec'))

    def test_standalone_compose_and_read_only_status_do_not_build_or_start(self):
        self.prepare()
        result = self.run_script('ancore.sh', 'status', INSTALLER_STANDALONE='1')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(any(call[0] == 'docker-compose' for call in self.commands('ps')))
        self.assertFalse(self.commands('build'))
        self.assertFalse(self.commands('up'))

    def test_local_only_address_and_explicit_loopback_are_identified_in_diagnostics(self):
        configured = self.run_script('ancore.sh', 'install', '--configure-only', '--bind', '127.0.0.1')
        self.assertEqual(configured.returncode, 0, configured.stdout + configured.stderr)
        result = self.run_script('ancore.sh', 'doctor')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Adres Ancore: http://127.0.0.1:8080', result.stdout)
        configured = self.run_script('ancore.sh', 'install', '--configure-only', '--reconfigure',
                                     '--url', 'http://localhost:8080')
        self.assertEqual(configured.returncode, 0, configured.stdout + configured.stderr)
        result = self.run_script('ancore.sh', 'doctor')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Adres localhost/127.x jest lokalny.', result.stdout)

    def test_unknown_command_and_help_need_no_daemon_and_reload_checks_config(self):
        result = self.run_script('ancore.sh', '--help', INSTALLER_NO_ACCESS='1')
        self.assertEqual(result.returncode, 0)
        unknown = self.run_script('ancore.sh', 'not-a-command')
        self.assertNotEqual(unknown.returncode, 0)
        extra = self.run_script('ancore.sh', 'start', '--configure-only')
        self.assertNotEqual(extra.returncode, 0)
        self.assertFalse(self.calls.exists())
        self.prepare()
        reload = self.run_script('ancore.sh', 'reload', INSTALLER_EXEC_ERROR='1')
        self.assertNotEqual(reload.returncode, 0)
        self.assertEqual(len(self.commands('exec')), 1)
        self.assertIn('-t', self.commands('exec')[0])

    def test_update_requires_existing_installation_and_configure_does_not_start(self):
        missing = self.run_script('ancore.sh', 'update')
        self.assertNotEqual(missing.returncode, 0)
        self.assertFalse((self.root / 'deploy/.env').exists())
        result = self.run_script('ancore.sh', 'configure', '--http-port', '8089')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.config()['ANCORE_HTTP_PORT'], "'8089'")
        self.assertFalse(self.commands('build'))
        self.assertFalse(self.commands('up'))

    def test_update_migrates_previous_default_retention_without_replacing_secrets(self):
        self.prepare()
        path = self.root / 'deploy/.env'
        original = path.read_text()
        path.write_text(original.replace("BACKUP_KEEP='10'", "BACKUP_KEEP='14'"))
        result = self.run_script('ancore.sh', 'update')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(path.read_text(), original)

    def test_custom_configuration_and_legacy_python_command_use_same_runtime(self):
        custom = self.root.parent / 'custom configuration' / '.env'
        configured = self.run_script('ancore.sh', '--env-file', str(custom), 'configure')
        self.assertEqual(configured.returncode, 0, configured.stdout + configured.stderr)
        self.assertTrue(custom.is_file())
        self.assertFalse((self.root / 'deploy/.env').exists())
        status = subprocess.run([sys.executable, str(self.root / 'scripts/production.py'),
                                 '--env-file', str(custom), 'status'], cwd=self.bin,
                                capture_output=True, text=True, env=self.environment, timeout=30)
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertIn(str(custom.resolve()), self.commands('ps')[-1])
        self.assertFalse(self.commands('build'))
        misplaced = self.root.parent / 'misplaced.env'
        invalid = self.run_script('ancore.sh', 'configure', '--env-file', str(misplaced))
        self.assertNotEqual(invalid.returncode, 0)
        self.assertFalse(misplaced.exists())

    def test_restore_requires_confirmation_and_valid_location_before_stopping_writers(self):
        self.prepare()
        backup_dir = self.root / 'deploy/backups'
        archive = backup_dir / 'ancore-qa.tar.gz'
        archive.write_bytes(b'QA archive')
        for args in ((str(archive),), (str(archive), '--yes')):
            result = self.run_script('ancore.sh', 'restore', *args)
            self.assertNotEqual(result.returncode, 0)
        outside = self.root / 'outside-backup-directory.tar.gz'
        outside.write_bytes(b'QA archive')
        outside.with_name(outside.name + '.sha256').write_text('QA checksum')
        misplaced = self.run_script('ancore.sh', 'restore', str(outside), '--yes')
        self.assertNotEqual(misplaced.returncode, 0)
        self.assertFalse(self.commands('stop'))
        archive.with_name(archive.name + '.sha256').write_text('QA checksum')
        result = self.run_script('ancore.sh', 'restore', str(archive), '--yes')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        restore = next(call for call in self.commands('run') if 'restore' in call)
        self.assertIn(str((self.root / 'deploy/compose.restore.yaml').resolve()), restore)
        self.assertIn('/backups/ancore-qa.tar.gz', restore)
        self.assertEqual(len(self.commands('stop')), 1)

    def test_failed_restore_keeps_writers_stopped_and_unlock_works_without_running_backup(self):
        self.prepare()
        archive = self.root / 'deploy/backups/ancore-qa.tar.gz'
        archive.write_bytes(b'QA archive')
        archive.with_name(archive.name + '.sha256').write_text('QA checksum')
        result = self.run_script('ancore.sh', 'restore', str(archive), '--yes', INSTALLER_RESTORE_ERROR='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.commands('up')), 1)
        self.assertEqual(self.commands('up')[0][-1], 'postgres')
        self.assertNotIn('są gotowe', result.stdout)
        unlocked = self.run_script('ancore.sh', 'unlock')
        self.assertEqual(unlocked.returncode, 0, unlocked.stdout + unlocked.stderr)
        self.assertIn('unlock', self.commands('run')[-1])

    def test_retired_office_launcher_fails_before_creating_configuration(self):
        result = self.run_script('scripts/start_office.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Brak lokalnej konfiguracji deploy/office.compose.yml', result.stderr)
        self.assertFalse((self.root / '.env.office').exists())
        self.assertFalse(self.calls.exists())
