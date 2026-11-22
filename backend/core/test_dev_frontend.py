"""Local builds must follow source changes without serving a stale application."""
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.management import get_commands, load_command_class
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.dev_frontend import FrontendBuilder, FrontendBuildError, FrontendBuildHandler
from core.management.commands.runserver import Command, StaticRunserver


class FrontendBuilderTests(SimpleTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='ancore-frontend-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'repo with spaces'
        self.frontend = self.root / 'frontend/app'
        self.source = self.frontend / 'src/main.tsx'
        self.source.parent.mkdir(parents=True)
        self.source.write_text('export const value = 1;\n')
        for name in ('package.json', 'tsconfig.json'):
            (self.frontend / name).write_text('{}\n')
        (self.frontend / 'build.mjs').write_text('// build\n')
        (self.frontend / 'pnpm-lock.yaml').write_text('lockfileVersion: 9\n')
        self.output = self.root / 'static/frontend'
        self.output.mkdir(parents=True)
        self.manifest = self.output / 'manifest.json'
        self.builder = FrontendBuilder(self.root, io.StringIO())
        self.build = Mock(side_effect=self.write_bundle)
        self.builder.build = self.build

    def write_bundle(self):
        name = f'main-{self.builder.fingerprint()}.js'
        (self.output / name).write_text('// compiled application\n')
        self.manifest.write_text(json.dumps({'main': name}))

    def test_startup_replaces_an_existing_bundle_then_reuses_current_build(self):
        (self.output / 'main-old.js').write_text('// other branch\n')
        self.manifest.write_text(json.dumps({'main': 'main-old.js'}))
        self.builder.ensure_current()
        self.assertNotEqual(json.loads(self.manifest.read_text())['main'], 'main-old.js')
        self.builder.ensure_current()
        self.assertEqual(self.build.call_count, 1)

    def test_content_changes_are_detected_even_when_size_and_mtime_are_preserved(self):
        self.builder.ensure_current()
        before = self.source.stat()
        self.source.write_text('export const value = 2;\n')
        os.utime(self.source, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.builder.ensure_current()
        self.assertEqual(self.build.call_count, 2)

    def test_added_removed_and_reverted_sources_each_require_a_new_build(self):
        self.builder.ensure_current()
        original = self.source.read_text()
        extra = self.source.parent / 'added.ts'
        extra.write_text('export const extra = true;\n')
        self.builder.ensure_current()
        extra.unlink()
        self.builder.ensure_current()
        self.source.write_text('export const value = 3;\n')
        self.builder.ensure_current()
        self.source.write_text(original)
        self.builder.ensure_current()
        self.assertEqual(self.build.call_count, 5)

    def test_build_configuration_and_dependency_state_trigger_rebuilds(self):
        self.builder.ensure_current()
        names = [
            'build.mjs', 'package.json', 'tsconfig.json', 'pnpm-lock.yaml', '.npmrc',
            'node_modules/.modules.yaml', 'node_modules/typescript/package.json',
            'node_modules/esbuild/package.json',
        ]
        for index, name in enumerate(names, start=2):
            with self.subTest(name=name):
                path = self.frontend / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f'changed configuration: {index}\n')
                self.builder.ensure_current()
                self.assertEqual(self.build.call_count, index)

    def test_unrelated_repository_changes_do_not_build(self):
        self.builder.ensure_current()
        (self.root / 'README.md').write_text('Documentation only.\n')
        (self.root / 'static/example.css').write_text('body { color: red; }\n')
        self.builder.ensure_current()
        self.build.assert_called_once()

    def test_changed_corrupted_missing_manifest_and_missing_entry_are_repaired(self):
        self.builder.ensure_current()
        changed = json.loads(self.manifest.read_text())
        for content in [json.dumps({**changed, 'replaced': True}), '{broken', '[]', '{"main": 12}']:
            with self.subTest(content=content):
                calls = self.build.call_count
                self.manifest.write_text(content)
                self.builder.ensure_current()
                self.assertEqual(self.build.call_count, calls + 1)
                self.assertIsNotNone(self.builder.bundle())
        self.manifest.unlink()
        self.builder.ensure_current()
        entry = self.output / json.loads(self.manifest.read_text())['main']
        entry.unlink()
        self.builder.ensure_current()
        self.assertTrue(entry.is_file())
        self.assertEqual(self.build.call_count, 7)

    def test_concurrent_requests_share_one_build(self):
        barrier = threading.Barrier(6)

        def request():
            barrier.wait(timeout=5)
            self.builder.ensure_current()

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(request) for _ in range(6)]
            for future in futures:
                future.result(timeout=5)
        self.build.assert_called_once()
        self.assertIsNotNone(self.builder.bundle())

    def test_source_changed_during_compilation_is_built_again(self):
        def change_once():
            self.write_bundle()
            if self.build.call_count == 1:
                self.source.write_text('export const value = 4;\n')

        self.build.side_effect = change_once
        self.builder.ensure_current()
        self.assertEqual(self.build.call_count, 2)
        self.assertEqual(self.builder.ready[0], self.builder.fingerprint())
        self.builder.ensure_current()
        self.assertEqual(self.build.call_count, 2)

    def test_continuously_changing_sources_stop_after_three_attempts_and_can_retry(self):
        def always_change():
            self.write_bundle()
            self.source.write_text(f'export const value = {self.build.call_count + 1};\n')

        self.build.side_effect = always_change
        with self.assertRaisesMessage(FrontendBuildError, 'Kod zmienił się'):
            self.builder.ensure_current()
        self.assertEqual(self.build.call_count, 3)
        self.assertIsNone(self.builder.ready)
        self.build.side_effect = self.write_bundle
        self.builder.ensure_current()
        self.assertEqual(self.build.call_count, 4)

    def test_failed_build_is_cached_until_source_is_fixed(self):
        self.builder.ensure_current()
        previous_manifest = self.manifest.read_bytes()
        self.source.write_text('invalid TypeScript\n')
        self.build.side_effect = FrontendBuildError('Popraw TypeScript.')
        for _ in range(2):
            with self.assertRaisesMessage(FrontendBuildError, 'Popraw TypeScript'):
                self.builder.ensure_current()
        self.assertEqual(self.build.call_count, 2)
        self.assertEqual(self.manifest.read_bytes(), previous_manifest)
        self.source.write_text('export const value = 5;\n')
        self.build.side_effect = self.write_bundle
        self.builder.ensure_current()
        self.assertEqual(self.build.call_count, 3)
        self.assertIsNone(self.builder.failed)

    def test_transient_failure_retries_after_five_seconds_without_source_edit(self):
        self.build.side_effect = FrontendBuildError('Tymczasowy błąd procesu.')
        with patch('core.dev_frontend.time.monotonic', return_value=100):
            with self.assertRaises(FrontendBuildError):
                self.builder.ensure_current()
        self.build.side_effect = self.write_bundle
        with patch('core.dev_frontend.time.monotonic', return_value=104.99):
            with self.assertRaisesMessage(FrontendBuildError, 'Tymczasowy błąd'):
                self.builder.ensure_current()
        self.assertEqual(self.build.call_count, 1)
        with patch('core.dev_frontend.time.monotonic', return_value=105):
            self.builder.ensure_current()
        self.assertEqual(self.build.call_count, 2)
        self.assertIsNone(self.builder.failed)

    def test_success_without_valid_output_is_not_marked_ready(self):
        self.build.side_effect = None
        with self.assertRaisesMessage(FrontendBuildError, 'poprawnego manifestu'):
            self.builder.ensure_current()
        self.assertIsNone(self.builder.ready)

    def test_missing_pnpm_reports_dependency_problem_before_spawning(self):
        with patch('core.dev_frontend.shutil.which', return_value=None), \
                patch('core.dev_frontend.subprocess.Popen') as popen:
            with self.assertRaisesMessage(FrontendBuildError, 'Brak pnpm w PATH'):
                FrontendBuilder(self.root, io.StringIO()).build()
        popen.assert_not_called()

    def test_new_pnpm_path_invalidates_a_cached_missing_tool_failure(self):
        self.build.side_effect = FrontendBuildError('Brak pnpm w PATH.')
        with patch('core.dev_frontend.shutil.which', return_value=None):
            with self.assertRaises(FrontendBuildError):
                self.builder.ensure_current()
        self.build.side_effect = self.write_bundle
        with patch('core.dev_frontend.shutil.which', return_value='/new/bin/pnpm'):
            self.builder.ensure_current()
        self.assertEqual(self.build.call_count, 2)

    def test_build_environment_prepends_configured_path_without_mutating_process(self):
        with patch.dict(os.environ, {'PATH': '/original/bin', 'ANCORE_BUILD_TEST': 'original'}):
            for extra in ['', '/tools/node' + os.pathsep + '/tools/pnpm']:
                with self.subTest(extra=extra), override_settings(FRONTEND_BUILD_PATH=extra):
                    environment = self.builder.environment()
                    expected = extra + os.pathsep + '/original/bin' if extra else '/original/bin'
                    self.assertEqual(environment['PATH'], expected)
                    self.assertEqual(environment['ANCORE_BUILD_TEST'], 'original')
                    environment['PATH'] = '/changed/locally'
                    environment['ANCORE_BUILD_TEST'] = 'changed'
                    self.assertEqual(os.environ['PATH'], '/original/bin')
                    self.assertEqual(os.environ['ANCORE_BUILD_TEST'], 'original')

    def test_configured_tool_path_is_used_for_lookup_and_forwarded_to_subprocess(self):
        tools = self.root / 'local tool bin'
        tools.mkdir()
        executable = tools / 'pnpm'
        executable.write_text(
            f'#!{sys.executable}\n'
            'import json, os, pathlib\n'
            'pathlib.Path("path.json").write_text(json.dumps({"path": os.environ["PATH"], '
            '"marker": os.environ["ANCORE_BUILD_TEST"]}))\n'
        )
        executable.chmod(0o755)
        expected = str(tools) + os.pathsep + '/original/bin'
        with override_settings(FRONTEND_BUILD_PATH=str(tools)), \
                patch.dict(os.environ, {'PATH': '/original/bin', 'ANCORE_BUILD_TEST': 'preserved'}), \
                patch('core.dev_frontend.shutil.which', wraps=shutil.which) as lookup:
            builder = FrontendBuilder(self.root, io.StringIO())
            builder.fingerprint()
            builder.build()
            self.assertEqual(lookup.call_count, 2)
            for call in lookup.call_args_list:
                self.assertEqual(call.args, ('pnpm',))
                self.assertEqual(call.kwargs, {'path': expected})
            self.assertEqual(os.environ['PATH'], '/original/bin')
        self.assertEqual(json.loads((self.frontend / 'path.json').read_text()), {
            'path': expected, 'marker': 'preserved',
        })

    def test_build_invokes_package_script_without_implicit_dependency_installation(self):
        executable = self.root / 'fake pnpm'
        executable.write_text(
            f'#!{sys.executable}\n'
            'import json, pathlib, sys\n'
            'pathlib.Path("invoked.json").write_text(json.dumps({"argv": sys.argv[1:], '
            '"cwd": str(pathlib.Path.cwd())}))\n'
        )
        executable.chmod(0o755)
        with patch('core.dev_frontend.shutil.which', return_value=str(executable)):
            FrontendBuilder(self.root, io.StringIO()).build()
        invocation = json.loads((self.frontend / 'invoked.json').read_text())
        self.assertEqual(invocation, {
            'argv': ['--config.verify-deps-before-run=false', 'build'],
            'cwd': str(self.frontend.resolve()),
        })

    def test_failed_process_reports_error_and_removes_exit_cleanup(self):
        process = Mock()
        process.wait.return_value = 1
        process.poll.return_value = 1
        with patch('core.dev_frontend.shutil.which', return_value='/bin/pnpm'), \
                patch('core.dev_frontend.subprocess.Popen', return_value=process), \
                patch('core.dev_frontend.atexit.register') as register, \
                patch('core.dev_frontend.atexit.unregister') as unregister:
            with self.assertRaisesMessage(FrontendBuildError, 'Nie udało się przebudować'):
                FrontendBuilder(self.root, io.StringIO()).build()
        unregister.assert_called_once_with(register.call_args.args[0])
        process.kill.assert_not_called()

    def test_timed_out_build_terminates_process_group_and_unregisters_cleanup(self):
        process = Mock(pid=12345)
        process.wait.side_effect = [subprocess.TimeoutExpired('pnpm', 120), 0]
        process.poll.return_value = None
        with patch('core.dev_frontend.shutil.which', return_value='/bin/pnpm'), \
                patch('core.dev_frontend.subprocess.Popen', return_value=process), \
                patch('core.dev_frontend.os.killpg', create=True) as killpg, \
                patch('core.dev_frontend.atexit.register') as register, \
                patch('core.dev_frontend.atexit.unregister') as unregister:
            with self.assertRaisesMessage(FrontendBuildError, '120 sekund'):
                FrontendBuilder(self.root, io.StringIO()).build()
        self.assertEqual(process.wait.call_args_list[0].kwargs, {'timeout': 120})
        if os.name == 'posix':
            killpg.assert_called_once_with(process.pid, signal.SIGKILL)
        else:
            process.kill.assert_called_once()
        unregister.assert_called_once_with(register.call_args.args[0])

    def test_filesystem_errors_are_explained_instead_of_escaping_guard(self):
        with patch.object(self.builder, 'fingerprint', side_effect=PermissionError('denied')):
            with self.assertRaisesMessage(FrontendBuildError, 'Sprawdź pliki, zależności i PATH'):
                self.builder.ensure_current()


class FrontendBuildHandlerTests(SimpleTestCase):
    def setUp(self):
        self.builder = Mock()
        self.application = Mock(return_value=[b'application'])
        self.handler = FrontendBuildHandler(self.application, self.builder, '/static/')
        self.factory = RequestFactory()

    def invoke(self, path, **headers):
        environ = self.factory.get(path, **headers).environ
        start = Mock()
        content = b''.join(self.handler(environ, start))
        return content, start

    def test_normal_page_and_scoped_api_are_guarded_before_dispatch(self):
        for path in ['/spaces/', '/workplaces/w_test/api/v1/navigation/']:
            with self.subTest(path=path):
                self.builder.reset_mock()
                self.application.reset_mock()
                self.application.side_effect = lambda *args: (
                    self.builder.ensure_current.assert_called_once() or [b'application']
                )
                content, _ = self.invoke(path)
                self.assertEqual(content, b'application')
                self.application.assert_called_once()

    def test_failure_returns_json_503_for_api_or_json_accept_without_dispatch(self):
        self.builder.ensure_current.side_effect = FrontendBuildError('Błąd kompilacji.')
        for path, headers in [
            ('/api/v1/navigation/', {}),
            ('/workplaces/w_test/api/v1/page/', {}),
            ('/spaces/', {'HTTP_ACCEPT': 'application/json'}),
        ]:
            with self.subTest(path=path):
                content, start = self.invoke(path, **headers)
                self.assertEqual(json.loads(content), {'message': 'Błąd kompilacji.'})
                status, response_headers = start.call_args.args
                self.assertTrue(status.startswith('503 '))
                self.assertEqual(dict(response_headers)['Cache-Control'], 'no-store')
                self.assertEqual(dict(response_headers)['Content-Type'], 'application/json')
        self.application.assert_not_called()

    def test_failure_returns_explanation_for_html_without_serving_old_page(self):
        self.builder.ensure_current.side_effect = FrontendBuildError('Popraw kod i odśwież stronę.')
        content, start = self.invoke('/spaces/')
        self.assertIn('Popraw kod'.encode(), content)
        self.assertTrue(start.call_args.args[0].startswith('503 '))
        headers = dict(start.call_args.args[1])
        self.assertEqual(headers['Content-Type'], 'text/plain; charset=utf-8')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.application.assert_not_called()

    def test_static_and_health_requests_do_not_wait_for_a_build(self):
        self.builder.ensure_current.side_effect = FrontendBuildError('not ready')
        for path in ['/static/frontend/main.js', '/health/ready/', '/health/live/']:
            with self.subTest(path=path):
                content, _ = self.invoke(path)
                self.assertEqual(content, b'application')
        self.builder.ensure_current.assert_not_called()

    def test_static_url_with_origin_uses_its_path_and_not_similar_prefix(self):
        self.handler = FrontendBuildHandler(self.application, self.builder, 'https://cdn.test/assets/')
        self.invoke('/assets/main.js')
        self.builder.ensure_current.assert_not_called()
        self.invoke('/assets-other/page/')
        self.builder.ensure_current.assert_called_once()


class FrontendRunserverTests(SimpleTestCase):
    def test_project_selects_runserver_with_staticfiles_support(self):
        self.assertEqual(get_commands()['runserver'], 'core')
        command = load_command_class('core', 'runserver')
        self.assertIsInstance(command, StaticRunserver)
        parser = command.create_parser('manage.py', 'runserver')
        options = parser.parse_args(['127.0.0.1:8000', '--noreload', '--no-frontend-build', '--nostatic'])
        self.assertTrue(options.no_frontend_build)
        self.assertFalse(options.use_reloader)
        self.assertFalse(options.use_static_handler)

    @override_settings(DEBUG=True)
    def test_startup_build_runs_before_server_and_handler_is_guarded(self):
        command = Command(stdout=io.StringIO(), stderr=io.StringIO())
        application = Mock()
        with patch('core.management.commands.runserver.FrontendBuilder') as factory, \
                patch.object(StaticRunserver, 'inner_run') as run, \
                patch.object(StaticRunserver, 'get_handler', return_value=application):
            run.side_effect = lambda *args, **kwargs: factory.return_value.ensure_current.assert_called_once()
            command.inner_run(None, no_frontend_build=False)
            handler = command.get_handler()
        factory.assert_called_once_with(settings.BASE_DIR, command.stdout)
        self.assertIsInstance(handler, FrontendBuildHandler)
        self.assertIs(handler.application, application)
        self.assertIs(handler.builder, factory.return_value)

    def test_production_mode_and_explicit_optout_never_start_builder(self):
        for debug, disabled in [(False, False), (True, True)]:
            with self.subTest(debug=debug, disabled=disabled), override_settings(DEBUG=debug):
                command = Command(stdout=io.StringIO(), stderr=io.StringIO())
                application = Mock()
                with patch('core.management.commands.runserver.FrontendBuilder') as factory, \
                        patch.object(StaticRunserver, 'inner_run') as run, \
                        patch.object(StaticRunserver, 'get_handler', return_value=application):
                    command.inner_run(None, no_frontend_build=disabled)
                    self.assertIs(command.get_handler(), application)
                factory.assert_not_called()
                run.assert_called_once()

    @override_settings(DEBUG=True)
    def test_reused_command_drops_previous_builder_when_building_is_disabled(self):
        command = Command(stdout=io.StringIO(), stderr=io.StringIO())
        with patch('core.management.commands.runserver.FrontendBuilder') as factory, \
                patch.object(StaticRunserver, 'inner_run'):
            command.inner_run(None, no_frontend_build=False)
            self.assertIs(command.frontend_builder, factory.return_value)
            command.inner_run(None, no_frontend_build=True)
        self.assertIsNone(command.frontend_builder)
        factory.assert_called_once()

    @override_settings(DEBUG=True)
    def test_startup_error_keeps_guarded_server_available_for_repair(self):
        stderr = io.StringIO()
        command = Command(stdout=io.StringIO(), stderr=stderr)
        with patch('core.management.commands.runserver.FrontendBuilder') as factory, \
                patch.object(StaticRunserver, 'inner_run') as run, \
                patch.object(StaticRunserver, 'get_handler', return_value=Mock()):
            factory.return_value.ensure_current.side_effect = FrontendBuildError('Napraw kompilację.')
            command.inner_run(None, no_frontend_build=False)
            self.assertIsInstance(command.get_handler(), FrontendBuildHandler)
        self.assertIn('Napraw kompilację.', stderr.getvalue())
        run.assert_called_once()
