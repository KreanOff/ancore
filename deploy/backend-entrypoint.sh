#!/bin/sh
set -eu
umask 027
if [ "${1:-}" = gunicorn ]; then
    if [ "${SECURE_SSL_REDIRECT:-true}" = true ]; then
        python manage.py check --deploy --fail-level WARNING
    else
        python manage.py check
    fi
    python manage.py migrate --noinput
    # Preserve chunks still used by browser tabs opened before an update.
    python manage.py collectstatic --noinput
fi
exec "$@"
