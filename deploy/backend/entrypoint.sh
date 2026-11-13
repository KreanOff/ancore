#!/bin/sh
set -eu
umask 027
if [ "${1:-}" = gunicorn ]; then
    python manage.py check
    python manage.py migrate --noinput
    # Preserve chunks still used by browser tabs opened before an update.
    python manage.py collectstatic --noinput
fi
exec "$@"
