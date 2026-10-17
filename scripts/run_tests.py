"""Run Django tests with a unique database and disposable file storage."""
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4


def main():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / 'backend'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ancore.settings')
    # Apply only to test connections; do not change the PostgreSQL server.
    os.environ.setdefault('PGOPTIONS', '-c jit=off -c statement_timeout=60000')

    import django
    from django.conf import settings
    from django.core.management import call_command

    settings.DATABASES['default'].setdefault('TEST', {})['NAME'] = 'test_ancore_' + uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix='ancore-tests-') as directory:
        for name, suffix in [('MEDIA_ROOT', 'media'), ('PRIVATE_DOCUMENT_ROOT', 'private'), ('STATIC_ROOT', 'static')]:
            path = Path(directory) / suffix
            path.mkdir()
            setattr(settings, name, path)
        django.setup()
        call_command('test', *sys.argv[1:], interactive=False)


if __name__ == '__main__':
    main()
