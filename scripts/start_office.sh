#!/bin/sh
# Run from any directory; leaves the user's default Docker context unchanged.
set -eu
cd "$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
PATH="/opt/homebrew/bin:$PATH"
export PATH
.venv/bin/python scripts/configure_office.py
if [ "$(uname -s)" = Darwin ]; then
    colima start --profile ancore --cpu 2 --memory 4 --disk 40 --mount none --activate=false
    export DOCKER_CONTEXT=colima-ancore
fi
if command -v docker-compose >/dev/null 2>&1; then
    docker-compose --env-file .env.office -f deploy/office.compose.yml up -d --wait
else
    docker compose --env-file .env.office -f deploy/office.compose.yml up -d --wait
fi
