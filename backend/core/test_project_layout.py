"""Regressions for entry points, discovery and assets after moving the backend."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from django.apps import apps
from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase
from django.test.utils import get_runner, iter_test_cases

from ancore import settings as project_settings


class ProjectLayoutTests(SimpleTestCase):
    def test_production_configurator_defaults_stay_in_deploy_from_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = (Path(directory) / 'repo with spaces').resolve()
            target = root / 'deploy/cli/configure.py'
            target.parent.mkdir(parents=True)
            shutil.copyfile(settings.BASE_DIR / 'deploy/cli/configure.py', target)
            command = [sys.executable, str(target)]
            result = subprocess.run(command, cwd=directory, input="192.0.2.10\n\n", capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            configuration = root / 'deploy/.env'
            original = configuration.read_bytes()
            self.assertEqual(configuration.stat().st_mode & 0o777, 0o600)
            values = dict(line.split('=', 1) for line in original.decode().splitlines() if '=' in line)
            self.assertEqual(values['ANCORE_PUBLIC_URL'], "'http://192.0.2.10:8080'")
            self.assertFalse((root / 'deploy/backups').exists())
            repeated = subprocess.run(command, cwd=directory, input="\n\n", capture_output=True, text=True)
            self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
            self.assertEqual(configuration.read_bytes(), original)

    def test_local_office_configuration_stays_at_root_and_preserves_existing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = (Path(directory) / 'repo with spaces').resolve()
            target = root / 'scripts/office/configure.py'
            target.parent.mkdir(parents=True)
            shutil.copyfile(settings.BASE_DIR / 'scripts/office/configure.py', target)
            command = [sys.executable, str(target)]
            result = subprocess.run(command, cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            configuration = root / '.env.office'
            self.assertEqual(configuration.stat().st_mode & 0o777, 0o600)
            configuration.write_text('ONLYOFFICE_JWT_SECRET=existing-local-value\n')
            repeated = subprocess.run(command, cwd=directory, capture_output=True, text=True)
            self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
            self.assertEqual(configuration.read_text(), 'ONLYOFFICE_JWT_SECRET=existing-local-value\n')
            self.assertNotIn('existing-local-value', repeated.stdout + repeated.stderr)

    def test_manage_runs_from_outside_the_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(settings.BASE_DIR / 'manage.py'), 'check'],
                cwd=directory, capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_wsgi_and_asgi_import_with_backend_on_pythonpath(self):
        environment = {
            **os.environ,
            'PYTHONPATH': str(settings.BACKEND_DIR),
            'DJANGO_SETTINGS_MODULE': 'ancore.settings',
        }
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, '-c',
                 'from ancore.wsgi import application as wsgi; '
                 'from ancore.asgi import application as asgi; '
                 'assert callable(wsgi) and callable(asgi)'],
                cwd=directory, env=environment,
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_assets_and_both_template_loaders_use_existing_locations(self):
        root = Path(settings.BASE_DIR)
        self.assertTrue((root / 'manage.py').is_file())
        self.assertTrue((root / 'static/css/style.css').is_file())
        for name in ['core/base.html', 'accounts/auth_base.html']:
            self.assertTrue(Path(get_template(name).origin.name).is_relative_to(settings.BACKEND_DIR))
        self.assertEqual(Path(project_settings.MEDIA_ROOT), root / 'media')
        self.assertEqual(Path(project_settings.PRIVATE_DOCUMENT_ROOT), root / 'private_documents')

    def test_default_and_explicit_discovery_keep_original_module_names(self):
        runner = get_runner(settings)(verbosity=0)
        suite = runner.build_suite()
        ids = {test.id() for test in iter_test_cases(suite)}
        expected = 'core.test_project_layout.ProjectLayoutTests.test_manage_runs_from_outside_the_repository'
        self.assertIn(expected, ids)
        self.assertTrue(any(name.startswith('accounts.test_frontend.') for name in ids))
        self.assertTrue(any(name.startswith('spaces.test_navigation.') for name in ids))
        self.assertFalse(any(name.startswith('unittest.loader._FailedTest.') for name in ids))
        selected = runner.build_suite(['core.test_project_layout'])
        self.assertEqual({test.id() for test in iter_test_cases(selected)}, {
            name for name in ids if name.startswith('core.test_project_layout.')
        })
        for config in apps.get_app_configs():
            if Path(config.path).is_relative_to(settings.BACKEND_DIR):
                expected = config.label
                self.assertEqual(config.name, expected)
