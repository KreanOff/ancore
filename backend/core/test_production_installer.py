"""Exercise installation prompts and lifecycle with a controlled Docker CLI."""
import hashlib
import json
import os
import pty
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import termios
import time

from django.conf import settings
from django.test import SimpleTestCase


FAKE_DOCKER = r'''
import hashlib, json, os, pathlib, subprocess, sys
args = sys.argv[1:]
secret_digest = os.getenv('INSTALLER_PASSWORD_DIGEST')
if secret_digest and any(hashlib.sha256(value.encode()).hexdigest() == secret_digest for value in os.environ.values()):
    sys.exit('Hasło administratora trafiło do środowiska procesu.')
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
    print('TEST: konfigurator Docker.', flush=True)
    index = next(index for index, argument in enumerate(args) if argument.endswith('deploy/cli/configure.py'))
    sys.exit(subprocess.call([sys.executable, 'deploy/cli/configure.py', *args[index + 1:]]))
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
    while args[0] in ('--env-file', '-f', '--project-name', '--project-directory'):
        args = args[2:]
    if args[0] == 'up' and '--help' in args:
        print('--wait-timeout' if not os.getenv('INSTALLER_OLD_COMPOSE') else '--detach')
    elif args[0] == 'ps':
        if args[-1] == 'web':
            print(os.getenv('INSTALLER_WEB_ID', ''))
        elif args[-1] == 'backend':
            print(os.getenv('INSTALLER_BACKEND_ID', ''))
        else:
            print('backend web postgres onlyoffice')
    elif args[0] == 'build':
        sys.exit(1 if os.getenv('INSTALLER_BUILD_ERROR') else 0)
    elif args[0] == 'up':
        sys.exit(1 if os.getenv('INSTALLER_START_ERROR') else 0)
    elif args[0] == 'config':
        sys.exit(1 if os.getenv('INSTALLER_CONFIG_ERROR') else 0)
    elif args[0] == 'exec':
        if 'ensure_admin' in args:
            if '--check-only' in args:
                sys.exit(0 if os.getenv('INSTALLER_EXISTING_ADMIN') else 1)
            if '--from-stdin' in args:
                pathlib.Path(os.environ['INSTALLER_ADMIN_INPUT']).write_text(sys.stdin.read())
            if os.getenv('INSTALLER_ADMIN_ERROR'):
                sys.exit(1)
            print('TEST: administrator jest gotowy.')
    elif args[0] in ('stop', 'logs', 'pull'):
        pass
    else:
        raise RuntimeError(args)
else:
    raise RuntimeError(args)
'''


class ProductionInstallerTests(SimpleTestCase):
    password = 'Ancore-install!57-private-credential'
    admin_fields = 'admin@example.test\nancore-admin\nAnna\nNowak\n'

    def admin_answers(self, password=None):
        password = self.password if password is None else password
        return self.admin_fields + password + '\n' + password + '\n'

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ancore-installer-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'repo with spaces'
        self.root.mkdir()
        for name in ('ancore-install.sh', 'deploy/cli/runtime.sh', 'deploy/cli/setup.sh', 'deploy/cli/update.sh', 'deploy/cli/configure.py',
                     'deploy/compose.yaml', 'scripts/start_office.sh', 'scripts/office/start.sh'):
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
        self.admin_input = Path(temporary.name) / 'admin-input.txt'
        self.environment = {key: value for key, value in os.environ.items()
                            if not key.startswith(('DOCKER_', 'INSTALLER_', 'ANCORE_', 'GIT_'))}
        self.environment.update(PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                                INSTALLER_CALLS=str(self.calls), INSTALLER_ADMIN_INPUT=str(self.admin_input),
                                GIT_CONFIG_GLOBAL=str(self.bin / 'gitconfig'), GIT_CONFIG_NOSYSTEM='1')

    def run_script(self, *arguments, answers='', **environment):
        return subprocess.run(['sh', str(self.root / 'ancore-install.sh'), *arguments],
                              input=answers, capture_output=True, text=True,
                              env={**self.environment, **environment}, cwd=self.bin, timeout=30)

    def start_terminal(self):
        master, slave = pty.openpty()
        self.addCleanup(os.close, slave)
        self.addCleanup(os.close, master)
        process = subprocess.Popen(
            ['sh', str(self.root / 'ancore-install.sh')], stdin=slave, stdout=slave, stderr=slave,
            env=self.environment, cwd=self.bin,
        )

        def cleanup():
            if process.poll() is None:
                process.kill()
            self.terminal_exit(process)

        self.addCleanup(cleanup)
        self.terminal_output = b''
        self.terminal_master = master
        return process, master, slave

    def terminal_exit(self, process):
        deadline = time.monotonic() + 10
        while process.poll() is None and time.monotonic() < deadline:
            # Drain final output while waiting: closing a PTY can wait for it.
            if select.select([self.terminal_master], [], [], 0.01)[0]:
                try:
                    self.terminal_output += os.read(self.terminal_master, 65536)
                except OSError:
                    pass
        self.assertIsNotNone(process.returncode, 'Instalator nie zakończył pracy w terminalu.')
        return process.returncode

    def terminal_until(self, master, text):
        expected = text.encode()
        deadline = time.monotonic() + 10
        while expected not in self.terminal_output:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([master], [], [], max(remaining, 0))[0]:
                self.fail(f'Brak komunikatu {text!r}: {self.terminal_output.decode(errors="replace")}')
            self.terminal_output += os.read(master, 65536)

    def terminal_password_prompt(self, master, slave):
        self.terminal_until(master, 'Adres IP serwera')
        os.write(master, ('192.0.2.10\n\n' + self.admin_fields).encode())
        self.terminal_until(master, 'Hasło administratora')
        deadline = time.monotonic() + 3
        while termios.tcgetattr(slave)[3] & termios.ECHO and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertFalse(termios.tcgetattr(slave)[3] & termios.ECHO)

    def config(self):
        path = self.root / 'deploy/.env'
        return dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)

    def recorded_calls(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []

    def commands(self, action):
        return [call for call in self.recorded_calls() if action in call and '--help' not in call]

    def prepare(self):
        result = self.run_script('install', answers='192.0.2.10\n\n' + self.admin_answers())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.environment.update(INSTALLER_BACKEND_ID='own-backend', INSTALLER_EXISTING_ADMIN='1')
        self.calls.write_text('')
        self.admin_input.unlink()

    def git(self, *arguments, cwd=None):
        result = subprocess.run(['git', *arguments], cwd=cwd or self.root,
                                env=self.environment, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def prepare_git_update(self):
        self.prepare()
        # All Git configuration and repositories belong to this temporary fixture.
        # URL rewriting exercises the public GitHub syntax without network access.
        self.environment = {key: value for key, value in self.environment.items()
                            if not key.startswith('GIT_')}
        self.environment.update(GIT_CONFIG_GLOBAL=str(self.bin / 'gitconfig'),
                                GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0',
                                GIT_ALLOW_PROTOCOL='file')
        self.git('config', '--global', 'user.name', 'Installer Test')
        self.git('config', '--global', 'user.email', 'installer@example.test')
        self.git('config', '--global', 'commit.gpgsign', 'false')
        shutil.copyfile(settings.BASE_DIR / '.gitignore', self.root / '.gitignore')
        for name in ('deploy/Dockerfile', 'manage.py', 'backend/ancore/settings.py'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# Installer Git fixture\n')
        (self.root / 'version.txt').write_text('original\n')
        (self.root / 'obsolete.txt').write_text('Remove in the next release.\n')
        self.git('init', '--initial-branch=main')
        self.git('add', '.')
        self.git('commit', '-m', 'Initial installation')
        self.initial_revision = self.git('rev-parse', 'HEAD')
        self.original_origin = 'https://github.com/original/ancore.git'
        self.git('remote', 'add', 'origin', self.original_origin)
        self.source = self.root.parent / 'source with spaces'
        self.git('clone', str(self.root), str(self.source))
        self.github_url = 'https://github.com/installer-test/ancore.git'
        for address in (self.github_url, 'git@github.com:installer-test/ancore.git'):
            self.git('config', '--global', '--add', f'url.{self.source}.insteadOf', address)

    def commit_source(self, message='Next release'):
        self.git('add', '--all', cwd=self.source)
        self.git('commit', '-m', message, cwd=self.source)
        return self.git('rev-parse', 'HEAD', cwd=self.source)

    def assert_update_rejected(self, *arguments):
        before = self.git('rev-parse', 'HEAD')
        configuration = (self.root / 'deploy/.env').read_bytes()
        self.calls.write_text('')
        result = self.run_script('update', *arguments)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git('rev-parse', 'HEAD'), before)
        self.assertEqual((self.root / 'deploy/.env').read_bytes(), configuration)
        for action in ('build', 'up', 'stop', 'down', 'volume', 'exec'):
            self.assertFalse(self.commands(action), action)
        self.assertNotIn('Usługi Ancore są gotowe.', result.stdout)
        return result

    def test_default_installation_configures_ip_port_and_prepares_admin_after_start(self):
        result = self.run_script(answers='192.0.2.10\n8087\n' + self.admin_answers())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.config()['ANCORE_PUBLIC_URL'], "'http://192.0.2.10:8087'")
        self.assertEqual(self.config()['ANCORE_HOST'], "'192.0.2.10'")
        self.assertEqual(self.config()['ANCORE_HTTP_PORT'], "'8087'")
        self.assertEqual(len(self.commands('build')), 1)
        build = self.commands('build')[0]
        self.assertEqual({value for value in build[build.index('build') + 1:] if not value.startswith('-')},
                         {'web', 'backend', 'postgres'})
        self.assertEqual(len(self.commands('up')), 1)
        self.assertIn('--wait', self.commands('up')[0])
        self.assertIn('--no-build', self.commands('up')[0])
        self.assertIn('--remove-orphans', self.commands('up')[0])
        self.assertIn('http://192.0.2.10:8087', result.stdout)
        self.assertEqual(len(self.commands('exec')), 1)
        admin = self.commands('exec')[0]
        self.assertEqual(admin[-5:], ['backend', 'python', 'manage.py', 'ensure_admin', '--from-stdin'])
        self.assertIn('-T', admin)
        self.assertEqual(self.admin_input.read_text(), self.admin_fields + self.password + '\n')
        self.assertLess(result.stdout.index('ANCORE'), result.stdout.index('Adres IP serwera'))
        self.assertLess(result.stdout.index('Powtórz hasło'), result.stdout.index('TEST: konfigurator Docker.'))
        self.assertNotIn(self.password, result.stdout + result.stderr + self.calls.read_text()
                         + (self.root / 'deploy/.env').read_text())
        calls = self.recorded_calls()
        self.assertLess(calls.index(build), calls.index(self.commands('up')[0]))
        self.assertLess(calls.index(self.commands('up')[0]), calls.index(admin))
        self.assertLess(result.stdout.index('TEST: administrator jest gotowy.'),
                        result.stdout.index('Usługi Ancore są gotowe.'))
        self.assertFalse(self.commands('stop'))
        self.assertEqual((self.root / 'deploy/.env').stat().st_mode & 0o777, 0o600)
        for key in ('SECRET_KEY', 'POSTGRES_PASSWORD', 'POSTGRES_ADMIN_PASSWORD', 'ONLYOFFICE_JWT_SECRET'):
            self.assertNotIn(self.config()[key].strip("'"), result.stdout + result.stderr)

    def test_setup_alias_collects_answers_upfront_and_pulls_missing_office(self):
        result = self.run_script('setup', answers='192.0.2.10\n\n' + self.admin_answers(), INSTALLER_OFFICE_MISSING='1')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.config()['ANCORE_HTTP_PORT'], "'8080'")
        self.assertEqual(self.commands('pull')[0][-1], 'onlyoffice')
        self.assertIn('--rm', self.commands('run')[0])
        self.assertEqual(self.commands('exec')[0][-1], '--from-stdin')

    def test_repeated_install_preserves_secrets_project_and_saved_defaults(self):
        self.prepare()
        before = (self.root / 'deploy/.env').read_bytes()
        repeated = self.run_script('install', answers='\n\n')
        self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
        self.assertEqual((self.root / 'deploy/.env').read_bytes(), before)
        self.assertEqual(len(self.commands('build')), 1)
        self.assertEqual(self.commands('exec')[0][-1], '--check-only')
        self.assertNotIn('Hasło administratora', repeated.stdout)
        self.assertFalse(self.admin_input.exists())

    def test_stopped_or_missing_administrator_is_collected_before_reinstallation(self):
        self.prepare()
        before = (self.root / 'deploy/.env').read_bytes()
        for environment in ({'INSTALLER_BACKEND_ID': ''}, {'INSTALLER_EXISTING_ADMIN': ''}):
            with self.subTest(environment=environment):
                self.calls.write_text('')
                result = self.run_script('install', answers='\n\n' + self.admin_answers(), **environment)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual((self.root / 'deploy/.env').read_bytes(), before)
                self.assertEqual(self.admin_input.read_text(), self.admin_fields + self.password + '\n')
                self.assertLess(result.stdout.index('Powtórz hasło'),
                                result.stdout.index('TEST: konfigurator Docker.'))

    def test_password_mismatch_reprompts_and_preserves_literal_special_characters(self):
        password = '  S3cure!$(touch should-not-exist)`false`\\quoted\'"  '
        answers = ('192.0.2.10\n\n' + self.admin_fields + self.password + '\nwrong-confirmation\n'
                   + password + '\n' + password + '\n')
        result = self.run_script('install', answers=answers,
                                 INSTALLER_PASSWORD_DIGEST=hashlib.sha256(password.encode()).hexdigest())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.admin_input.read_text(), self.admin_fields + password + '\n')
        self.assertEqual(result.stdout.count('Hasło administratora'), 2)
        self.assertFalse((self.root / 'should-not-exist').exists())
        self.assertNotIn(password, result.stdout + result.stderr + self.calls.read_text())
        for path in self.root.rglob('*'):
            if path.is_file():
                self.assertNotIn(password.encode(), path.read_bytes())

    def test_eof_during_credentials_never_downloads_builds_or_writes_configuration(self):
        for suffix in ('', 'admin@example.test\n', self.admin_fields,
                       self.admin_fields + self.password + '\n'):
            with self.subTest(suffix=suffix):
                self.calls.unlink(missing_ok=True)
                result = self.run_script('install', answers='192.0.2.10\n\n' + suffix)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.commands('run'))
                self.assertFalse(self.commands('build'))
                self.assertFalse(self.commands('up'))
                self.assertFalse((self.root / 'deploy/.env').exists())
                self.assertNotIn(self.password, result.stdout + result.stderr)

    def test_invalid_name_and_blank_profile_fields_reprompt_before_downloading(self):
        answers = (' 192.0.2.10 \n 8080 \n admin@example.test \ninvalid name\nancore-admin\n'
                   '   \n Anna \n\t\n Nowak \n' + self.password + '\n' + self.password + '\n')
        result = self.run_script('install', answers=answers)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.admin_input.read_text(), self.admin_fields + self.password + '\n')
        for label in ('Nazwa administratora', 'Imię administratora', 'Nazwisko administratora'):
            self.assertEqual(result.stdout.count(label), 2)
        self.assertLess(result.stdout.index('Powtórz hasło'), result.stdout.index('TEST: konfigurator Docker.'))

    def test_terminal_hides_password_and_restores_echo_after_success(self):
        process, master, slave = self.start_terminal()
        original = termios.tcgetattr(slave)
        self.terminal_password_prompt(master, slave)
        os.write(master, (self.password + '\n').encode())
        self.terminal_until(master, 'Powtórz hasło')
        deadline = time.monotonic() + 3
        while termios.tcgetattr(slave)[3] & termios.ECHO and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertFalse(termios.tcgetattr(slave)[3] & termios.ECHO)
        os.write(master, (self.password + '\n').encode())
        self.terminal_until(master, 'Usługi Ancore są gotowe.')
        self.assertEqual(self.terminal_exit(process), 0)
        self.assertEqual(termios.tcgetattr(slave), original)
        self.assertNotIn(self.password.encode(), self.terminal_output)
        self.assertEqual(self.admin_input.read_text(), self.admin_fields + self.password + '\n')

    def test_terminal_restores_echo_after_interruption_during_password(self):
        process, master, slave = self.start_terminal()
        original = termios.tcgetattr(slave)
        self.terminal_password_prompt(master, slave)
        process.send_signal(signal.SIGTERM)
        self.assertNotEqual(self.terminal_exit(process), 0)
        self.assertEqual(termios.tcgetattr(slave), original)
        self.assertFalse(self.commands('run'))
        self.assertFalse((self.root / 'deploy/.env').exists())

    def test_changed_address_preserves_existing_credentials_and_volume_project(self):
        self.prepare()
        before = self.config()
        changed = self.run_script('install', answers='192.0.2.11\n8090\n')
        self.assertEqual(changed.returncode, 0, changed.stdout + changed.stderr)
        after = self.config()
        self.assertEqual(after['ANCORE_PUBLIC_URL'], "'http://192.0.2.11:8090'")
        for key in ('SECRET_KEY', 'POSTGRES_PASSWORD', 'POSTGRES_ADMIN_PASSWORD',
                    'ONLYOFFICE_JWT_SECRET', 'ANCORE_PROJECT'):
            self.assertEqual(after[key], before[key])

    def test_invalid_address_and_port_reprompt_without_extra_configuration_questions(self):
        result = self.run_script('install', answers='http://192.0.2.10\nexample.test\n999.1.1.1\n192.0.2.10\nwrong\n0\n65536\n999999999999999999999\n8087\n' + self.admin_answers())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.config()['ANCORE_HTTP_PORT'], "'8087'")
        self.assertEqual(self.config()['ANCORE_HOST'], "'192.0.2.10'")

    def test_eof_keeps_existing_configuration_and_never_builds(self):
        self.prepare()
        before = (self.root / 'deploy/.env').read_bytes()
        for answers in ('', '192.0.2.11\n'):
            with self.subTest(answers=answers):
                interrupted = self.run_script('install', answers=answers)
                self.assertNotEqual(interrupted.returncode, 0)
                self.assertEqual((self.root / 'deploy/.env').read_bytes(), before)
                self.assertFalse(self.commands('build'))
                self.assertFalse(self.commands('up'))

    def test_incomplete_existing_credentials_fail_without_replacement(self):
        self.prepare()
        path = self.root / 'deploy/.env'
        for key in ('SECRET_KEY', 'POSTGRES_PASSWORD', 'POSTGRES_ADMIN_PASSWORD', 'ONLYOFFICE_JWT_SECRET'):
            with self.subTest(key=key):
                original = path.read_text()
                broken = '\n'.join(line for line in original.splitlines() if not line.startswith(key + '=')) + '\n'
                path.write_text(broken)
                result = self.run_script('install', answers='\n\n')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(path.read_text(), broken)
                self.assertFalse(self.commands('build'))
                path.write_text(original)

    def test_old_configuration_migrates_without_backup_tls_or_credential_changes(self):
        self.prepare()
        path = self.root / 'deploy/.env'
        original = self.config()
        path.write_text(path.read_text() + "ANCORE_TLS_MODE='direct'\nANCORE_BACKUP_DIR='/old/backups'\nBACKUP_KEEP='10'\n")
        path.rename(path.with_name('.env.production'))
        migrated = self.run_script('install', answers='\n\n')
        self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)
        self.assertEqual(self.config(), original)
        self.assertFalse((self.root / 'deploy/backups').exists())
        self.assertEqual(self.commands('exec')[0][-1], '--check-only')

    def test_occupied_host_port_aborts_before_build_or_start(self):
        result = self.run_script('install', answers='192.0.2.10\n\n' + self.admin_answers(),
                                 INSTALLER_LISTENERS='LISTEN 0 511 0.0.0.0:8080')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('8080', result.stderr)
        self.assertFalse(self.commands('build'))
        self.assertFalse(self.commands('up'))
        self.assertNotIn('są gotowe', result.stdout)

    def test_other_container_port_is_rejected_but_own_web_is_allowed(self):
        self.prepare()
        rejected = self.run_script('start', INSTALLER_OTHER_PORTS='0.0.0.0:8080->80/tcp')
        self.assertNotEqual(rejected.returncode, 0)
        allowed = self.run_script('start', INSTALLER_WEB_ID='own-web',
                                  INSTALLER_LISTENERS='LISTEN 0 511 0.0.0.0:8080')
        self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)

    def test_docker_access_remote_endpoint_and_old_compose_fail_before_configuration(self):
        for environment in ({'INSTALLER_NO_ACCESS': '1'}, {'INSTALLER_ENDPOINT': 'ssh://remote'},
                            {'INSTALLER_OLD_COMPOSE': '1'}):
            with self.subTest(environment=environment):
                result = self.run_script('install', answers='192.0.2.10\n\n', **environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.root / 'deploy/.env').exists())
                self.assertFalse(self.commands('build'))

    def test_failed_build_configuration_or_start_never_creates_admin_or_reports_ready(self):
        self.prepare()
        for arguments in (('install',), ('update', '--local')):
            for environment in ({'INSTALLER_BUILD_ERROR': '1'}, {'INSTALLER_START_ERROR': '1'},
                                {'INSTALLER_CONFIG_ERROR': '1'}):
                with self.subTest(arguments=arguments, environment=environment):
                    result = self.run_script(*arguments, answers='\n\n', **environment)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn('są gotowe', result.stdout)
        self.assertFalse([call for call in self.commands('exec') if '--check-only' not in call])

    def test_failed_admin_creation_never_reports_installation_ready(self):
        result = self.run_script('install', answers='192.0.2.10\n\n' + self.admin_answers(), INSTALLER_ADMIN_ERROR='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.commands('up')), 1)
        self.assertEqual(len(self.commands('exec')), 1)
        self.assertEqual(self.commands('exec')[0][-1], '--from-stdin')
        self.assertNotIn('Usługi Ancore są gotowe.', result.stdout)
        self.assertNotIn('Adres Ancore:', result.stdout)
        self.assertFalse(self.commands('down'))
        self.assertFalse(self.commands('volume'))

    def test_explicit_admin_command_remains_available_without_rebuild(self):
        self.prepare()
        result = self.run_script('admin')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.commands('exec')[0][-4:], ['backend', 'python', 'manage.py', 'createsuperuser'])
        self.assertFalse(self.commands('build'))
        self.assertFalse(self.commands('up'))

    def test_standalone_compose_status_does_not_build_or_start(self):
        self.prepare()
        result = self.run_script('status', INSTALLER_STANDALONE='1')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(any(call[0] == 'docker-compose' for call in self.commands('ps')))
        self.assertFalse(self.commands('build'))
        self.assertFalse(self.commands('up'))

    def test_unknown_retired_commands_and_help_need_no_daemon(self):
        result = self.run_script('--help', INSTALLER_NO_ACCESS='1')
        self.assertEqual(result.returncode, 0)
        for arguments in (('not-a-command',), ('backup',), ('restore',), ('configure',),
                          ('start', '--configure-only'), ('install', '--url', 'https://example.test')):
            with self.subTest(arguments=arguments):
                self.assertNotEqual(self.run_script(*arguments).returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_local_update_requires_configuration_then_builds_without_prompting(self):
        missing = self.run_script('update', '--local')
        self.assertNotEqual(missing.returncode, 0)
        self.assertFalse((self.root / 'deploy/.env').exists())
        self.prepare()
        before = (self.root / 'deploy/.env').read_bytes()
        update = self.run_script('update', '--local')
        self.assertEqual(update.returncode, 0, update.stdout + update.stderr)
        self.assertNotIn('Podaj link do repozytorium GitHub:', update.stdout)
        self.assertEqual((self.root / 'deploy/.env').read_bytes(), before)
        self.assertEqual(len(self.commands('build')), 1)
        self.assertEqual(len(self.commands('up')), 1)
        self.assertFalse(self.commands('run'))
        self.assertFalse(self.commands('exec'))

        no_git = self.root.parent / 'path without git'
        no_git.mkdir()
        for command in ('docker', 'ss', 'sh', 'dirname', 'sed', 'grep', 'cat'):
            executable = shutil.which(command, path=self.environment['PATH'])
            self.assertIsNotNone(executable, command)
            (no_git / command).symlink_to(executable)
        self.calls.write_text('')
        local = self.run_script('update', '--local', PATH=str(no_git))
        self.assertEqual(local.returncode, 0, local.stdout + local.stderr)
        self.assertEqual(len(self.commands('build')), 1)
        help_result = self.run_script('update', '--help', PATH=str(no_git), INSTALLER_NO_ACCESS='1')
        self.assertEqual(help_result.returncode, 0, help_result.stdout + help_result.stderr)
        self.assertNotIn('Podaj link do repozytorium GitHub:', help_result.stdout)
        self.calls.write_text('')
        remote = self.run_script('update', 'https://github.com/installer-test/ancore', PATH=str(no_git))
        self.assertNotEqual(remote.returncode, 0)
        self.assertIn('git', remote.stderr)
        self.assertFalse(self.commands('build'))
        self.assertFalse(self.commands('up'))

    def test_git_update_prompt_downloads_sources_and_reexecutes_new_installer_before_building(self):
        self.prepare_git_update()
        preserved = {}
        for name in ('deploy/.env', 'deploy/compose.recovery.yaml', 'media/private-upload.txt'):
            path = self.root / name
            if name != 'deploy/.env':
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('Local installation data.\n')
            preserved[name] = path.read_bytes()
        (self.source / 'version.txt').write_text('updated\n')
        (self.source / 'new-source.txt').write_text('New application source.\n')
        (self.source / 'obsolete.txt').unlink()
        installer = self.source / 'ancore-install.sh'
        installer.write_text(installer.read_text().replace(
            'set -eu\n', "set -eu\necho 'TEST: nowy instalator.'\n", 1))
        runtime = self.source / 'deploy/cli/runtime.sh'
        runtime.write_text(runtime.read_text().replace(
            'ancore_build() {\n',
            'ancore_build() {\n'
            '    [ "$(cat version.txt)" = updated ] || exit 23\n'
            '    [ -f new-source.txt ] && [ ! -e obsolete.txt ] || exit 24\n'
            "    echo 'TEST: nowy runtime przed budowaniem.'\n", 1))
        revision = self.commit_source()

        result = self.run_script('update', answers=f' \t{self.github_url}/\t  \n')

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count('Podaj link do repozytorium GitHub:'), 1)
        self.assertEqual(self.git('rev-parse', 'HEAD'), revision)
        self.assertEqual(self.git('config', '--get', 'remote.origin.url'), self.original_origin)
        self.assertEqual(self.git('symbolic-ref', '--short', 'HEAD'), 'main')
        self.assertEqual(result.stdout.count('TEST: nowy instalator.'), 1)
        self.assertEqual(result.stdout.count('TEST: nowy runtime przed budowaniem.'), 1)
        self.assertLess(result.stdout.index('TEST: nowy runtime przed budowaniem.'),
                        result.stdout.index('Usługi Ancore są gotowe.'))
        self.assertEqual(len(self.commands('build')), 1)
        self.assertEqual(len(self.commands('up')), 1)
        self.assertIn(str((self.root / 'deploy/compose.recovery.yaml').resolve()), self.commands('up')[0])
        self.assertFalse(self.commands('exec'))
        self.assertFalse(self.commands('stop'))
        self.assertFalse(self.commands('volume'))
        for name, content in preserved.items():
            self.assertEqual((self.root / name).read_bytes(), content)

    def test_git_update_prompt_retries_blank_and_invalid_links_until_valid_input(self):
        self.prepare_git_update()
        (self.source / 'version.txt').write_text('Corrected link release.\n')
        revision = self.commit_source()
        answers = '\nnot a GitHub link\nhttps://github.com/installer-test/ancore\\repo\n'

        result = self.run_script('update', answers=answers + self.github_url + '\n')

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count('Podaj link do repozytorium GitHub:'), 4)
        self.assertEqual(self.git('rev-parse', 'HEAD'), revision)
        self.assertEqual(len(self.commands('build')), 1)
        self.assertEqual(len(self.commands('up')), 1)
        self.assertFalse(self.commands('exec'))

    def test_git_update_prompt_eof_after_blank_or_invalid_input_never_calls_git_or_docker(self):
        self.prepare_git_update()
        configuration = (self.root / 'deploy/.env').read_bytes()
        git_calls = self.root.parent / 'unexpected-git-call.txt'
        git_stub = self.bin / 'git'
        git_stub.write_text(
            f'#!{sys.executable}\nfrom pathlib import Path\n'
            f'Path({str(git_calls)!r}).write_text("Git must wait for a valid link.")\n'
            'raise SystemExit(1)\n'
        )
        git_stub.chmod(0o700)
        for answers in ('', '\n', ' \t \n', 'not a GitHub link\n',
                        '\nhttps://github.com/installer-test/$(touch should-not-exist)\n'):
            with self.subTest(answers=answers):
                self.calls.write_text('')
                result = self.run_script('update', answers=answers)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout.count('Podaj link do repozytorium GitHub:'),
                                 len(answers.splitlines()) + 1)
                self.assertFalse(self.recorded_calls())
                self.assertFalse(git_calls.exists())
                self.assertFalse((self.root / '.git/FETCH_HEAD').exists())
                self.assertFalse((self.root / 'should-not-exist').exists())
                self.assertEqual((self.root / 'deploy/.env').read_bytes(), configuration)
                self.assertNotIn('Usługi Ancore są gotowe.', result.stdout)
        git_stub.unlink()
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.initial_revision)

    def test_git_update_accepts_repository_links_and_uses_current_branch(self):
        self.prepare_git_update()
        self.git('branch', '-m', 'production')
        self.git('tag', 'production')
        self.git('checkout', '-b', 'production', cwd=self.source)
        (self.source / 'version.txt').write_text('production release\n')
        revision = self.commit_source()
        for url in ('https://github.com/installer-test/ancore',
                    'https://github.com/installer-test/ancore/',
                    'https://github.com/installer-test/ancore.git/',
                    'git@github.com:installer-test/ancore',
                    'git@github.com:installer-test/ancore.git'):
            with self.subTest(url=url):
                self.calls.write_text('')
                result = self.run_script('update', url)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn('Podaj link do repozytorium GitHub:', result.stdout)
                self.assertEqual(self.git('rev-parse', 'HEAD'), revision)
                self.assertEqual(self.git('symbolic-ref', 'HEAD'), 'refs/heads/production')
                self.assertEqual(len(self.commands('build')), 1)
                self.assertEqual(len(self.commands('up')), 1)

    def test_git_update_accepts_an_explicit_branch_without_changing_origin(self):
        self.prepare_git_update()
        self.git('checkout', '-b', 'release/next', cwd=self.source)
        (self.source / 'version.txt').write_text('selected release\n')
        revision = self.commit_source()

        result = self.run_script('update', self.github_url, 'release/next')

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('Podaj link do repozytorium GitHub:', result.stdout)
        self.assertEqual(self.git('rev-parse', 'HEAD'), revision)
        self.assertEqual(self.git('config', '--get', 'remote.origin.url'), self.original_origin)
        self.assertEqual(self.git('symbolic-ref', '--short', 'HEAD'), 'main')

    def test_git_update_rejects_local_changes_including_staged_and_untracked_files(self):
        self.prepare_git_update()
        (self.source / 'version.txt').write_text('remote release\n')
        self.commit_source()
        for kind in ('modified', 'staged', 'untracked'):
            with self.subTest(kind=kind):
                path = self.root / ('local-notes.txt' if kind == 'untracked' else 'version.txt')
                path.write_text('Do not overwrite this local change.\n')
                if kind == 'staged':
                    self.git('add', 'version.txt')
                status = self.git('status', '--porcelain')
                self.assert_update_rejected(self.github_url)
                self.assertEqual(self.git('status', '--porcelain'), status)
                self.assertEqual(path.read_text(), 'Do not overwrite this local change.\n')
                if kind == 'untracked':
                    path.unlink()
                else:
                    self.git('restore', '--staged', '--worktree', 'version.txt')

    def test_git_update_rejects_divergent_history_and_detached_head(self):
        self.prepare_git_update()
        (self.root / 'local-source.txt').write_text('Local commit.\n')
        self.git('add', 'local-source.txt')
        self.git('commit', '-m', 'Local source change')
        self.assert_update_rejected(self.github_url)
        (self.source / 'version.txt').write_text('Remote commit.\n')
        self.commit_source()
        self.assert_update_rejected(self.github_url)
        self.git('checkout', '--detach', self.initial_revision)
        self.assert_update_rejected(self.github_url)

    def test_git_update_rejects_missing_branch_and_fetch_failure_before_building(self):
        self.prepare_git_update()
        self.assert_update_rejected(self.github_url, 'missing-branch')
        self.source.rename(self.source.with_name('temporarily unavailable source'))
        self.assert_update_rejected(self.github_url)

    def test_git_update_rejects_incomplete_or_symlinked_application_sources(self):
        self.prepare_git_update()
        for index, (name, symlink) in enumerate((('manage.py', False), ('deploy/compose.yaml', True))):
            with self.subTest(name=name, symlink=symlink):
                branch = f'invalid-layout-{index}'
                self.git('checkout', '-b', branch, self.initial_revision, cwd=self.source)
                path = self.source / name
                path.unlink()
                if symlink:
                    path.symlink_to('Dockerfile')
                self.commit_source()
                self.assert_update_rejected(self.github_url, branch)

    def test_git_update_rejects_sources_that_track_configuration_or_local_data(self):
        self.prepare_git_update()
        for index, name in enumerate(('deploy/.env', 'deploy/compose.recovery.yaml', '.env',
                                      'media/upload.txt', 'private_documents/file.txt',
                                      'deploy/backups/archive.txt')):
            with self.subTest(name=name):
                local = self.root / name
                if name != 'deploy/.env':
                    local.parent.mkdir(parents=True, exist_ok=True)
                    local.write_text('Private local data.\n')
                original = local.read_bytes()
                branch = f'protected-path-{index}'
                self.git('checkout', '-b', branch, self.initial_revision, cwd=self.source)
                remote = self.source / name
                remote.parent.mkdir(parents=True, exist_ok=True)
                remote.write_text('Must never replace local data.\n')
                self.git('add', '--force', name, cwd=self.source)
                self.commit_source()
                self.assert_update_rejected(self.github_url, branch)
                self.assertEqual(local.read_bytes(), original)

    def test_git_update_does_not_overwrite_other_ignored_files(self):
        self.prepare_git_update()
        (self.root / '.git/info/exclude').write_text('local-cache.txt\n')
        (self.root / 'local-cache.txt').write_text('Keep local content.\n')
        (self.source / 'local-cache.txt').write_text('Incoming tracked content.\n')
        self.commit_source()
        self.assertEqual(self.git('status', '--porcelain'), '')

        self.assert_update_rejected(self.github_url)

        self.assertEqual((self.root / 'local-cache.txt').read_text(), 'Keep local content.\n')

    def test_git_update_rejects_invalid_urls_branches_and_extra_arguments(self):
        self.prepare_git_update()
        for arguments in (('http://github.com/installer-test/ancore',),
                          ('https://github.com.example.test/installer-test/ancore',),
                          ('https://token@github.com/installer-test/ancore',),
                          ('https://github.com/installer-test/ancore/tree/main',),
                          ('https://github.com/installer-test/ancore?token=private',),
                          ('https://github.com/installer-test/ancore#main',),
                          ('https://github.com/installer-test/$(touch should-not-exist)',),
                          ('--upload-pack=touch should-not-exist',),
                          ('--local', 'main'),
                          (self.github_url, '--upload-pack=false'),
                          (self.github_url, 'main', 'extra')):
            with self.subTest(arguments=arguments):
                self.assert_update_rejected(*arguments)
        self.assertFalse((self.root / 'should-not-exist').exists())
        self.assertFalse((self.root / '.git/FETCH_HEAD').exists())

    def test_git_update_requires_checkout_at_the_installer_root(self):
        self.prepare()
        result = self.run_script('update', 'https://github.com/installer-test/ancore')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / '.git').exists())
        self.assertFalse(self.commands('build'))
        # A parent repository must not accidentally become the deployment target.
        self.git('init', '--initial-branch=main', cwd=self.root.parent)
        result = self.run_script('update', 'https://github.com/installer-test/ancore')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.commands('build'))
        self.assertFalse(self.commands('up'))
        self.assertFalse((self.root.parent / '.git/FETCH_HEAD').exists())

    def test_git_update_build_failure_keeps_services_running_without_success_message(self):
        self.prepare_git_update()
        (self.source / 'version.txt').write_text('Next release.\n')
        revision = self.commit_source()

        result = self.run_script('update', self.github_url, INSTALLER_BUILD_ERROR='1')

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git('rev-parse', 'HEAD'), revision)
        self.assertEqual(len(self.commands('build')), 1)
        self.assertFalse(self.commands('up'))
        self.assertFalse(self.commands('stop'))
        self.assertFalse(self.commands('down'))
        self.assertNotIn('Usługi Ancore są gotowe.', result.stdout)

    def test_start_restart_and_stop_preserve_data_without_rebuilding_or_admin_prompts(self):
        self.prepare()
        started = self.run_script('start')
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        self.assertIn('--pull', self.commands('up')[0])
        self.assertIn('never', self.commands('up')[0])
        restarted = self.run_script('restart')
        self.assertEqual(restarted.returncode, 0, restarted.stdout + restarted.stderr)
        stopped = self.run_script('stop')
        self.assertEqual(stopped.returncode, 0, stopped.stdout + stopped.stderr)
        self.assertFalse(self.commands('build'))
        self.assertFalse(self.commands('pull'))
        self.assertFalse(self.commands('down'))
        self.assertFalse(self.commands('volume'))
        self.assertFalse(self.commands('exec'))

    def test_recovered_installation_keeps_its_existing_volume_mapping(self):
        self.prepare()
        override = self.root / 'deploy/compose.recovery.yaml'
        content = 'volumes:\n  postgres:\n    name: previous-recovery-postgres\n'
        override.write_text(content)
        for arguments, answers in ((('start',), ''), (('update', '--local'), ''), (('install',), '\n\n')):
            with self.subTest(arguments=arguments):
                self.calls.write_text('')
                result = self.run_script(*arguments, answers=answers)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(str(override.resolve()), self.commands('up')[0])
                self.assertEqual(override.read_text(), content)
                self.assertFalse(self.commands('volume'))

    def test_retired_office_launcher_fails_before_creating_configuration(self):
        result = subprocess.run(['sh', str(self.root / 'scripts/start_office.sh')], cwd=self.bin,
                                capture_output=True, text=True, env=self.environment, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Brak lokalnej konfiguracji deploy/office.compose.yml', result.stderr)
        self.assertFalse((self.root / '.env.office').exists())
        self.assertFalse(self.calls.exists())
