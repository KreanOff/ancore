"""Drain HTTP operations before a coordinated database and file backup."""
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse


class BackupMaintenanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        directory = settings.BACKUP_CONTROL_ROOT
        if not directory:
            return self.get_response(request)

        # Production runs on Linux. Separate opens coordinate threads and workers.
        import fcntl
        lock = None
        try:
            root = Path(directory)
            lock = (root / 'requests.lock').open('a+b')
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
            if (root / 'maintenance').exists():
                raise BlockingIOError
        except OSError:
            if lock is not None:
                lock.close()
            response = JsonResponse(
                {'message': 'Trwa wykonywanie kopii zapasowej. Spróbuj ponownie za chwilę.'},
                status=503,
            )
            response['Retry-After'] = '60'
            response['Cache-Control'] = 'no-store'
            return response

        try:
            response = self.get_response(request)
        except BaseException:
            lock.close()
            raise
        if response.streaming:
            response._resource_closers.append(lock.close)
        else:
            lock.close()
        return response
