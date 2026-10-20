#!/bin/sh
# Docker-only bootstrap. Run on the server whose Docker daemon stores the data.
set -eu
umask 077
ANCORE_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
cd "$ANCORE_ROOT"
ANCORE_ENV="$ANCORE_ROOT/deploy/.env"

if ! command -v docker >/dev/null 2>&1; then
    echo 'Zainstaluj Docker Engine z Docker Compose, a następnie ponów instalację.' >&2
    exit 1
fi
if docker compose version >/dev/null 2>&1; then
    ANCORE_COMPOSE=plugin
elif command -v docker-compose >/dev/null 2>&1; then
    ANCORE_COMPOSE=standalone
else
    echo 'Brak Docker Compose.' >&2
    exit 1
fi

if [ "${1:-}" = --help ] || [ "${1:-}" = -h ]; then
    cat <<'HELP'
Instalacja Ancore: sh install.sh
Domyślnie: HTTP na porcie 8080, dostęp przez IP serwera.

Opcje:
  --url ADRES          Stały adres HTTP lub HTTPS (opcjonalny).
  --tls-dir KATALOG    Certyfikaty fullchain.pem i privkey.pem dla HTTPS.
  --reconfigure        Zmień adres/protokół, zachowując dane i sekrety.
  --http-port PORT     Port HTTP (domyślnie 8080).
  --https-port PORT    Port HTTPS (domyślnie 443).
  --backup-dir KATALOG Katalog backupów (domyślnie deploy/backups).
  --bind ADRES         Adres nasłuchiwania (HTTP: domyślnie 0.0.0.0).
  --project NAZWA      Nazwa nowej instalacji (domyślnie ancore-prod).
HELP
    exit 0
fi

# Mount optional directories at identical absolute host/container paths.
ANCORE_TLS_MOUNT=''
ANCORE_BACKUP_MOUNT=''
ANCORE_PREVIOUS=''
for ANCORE_ARGUMENT in "$@"; do
    case "$ANCORE_PREVIOUS" in
        --tls-dir)
            ANCORE_TLS_MOUNT=$(CDPATH='' cd -- "$ANCORE_ARGUMENT" && pwd -P)
            ;;
        --backup-dir)
            mkdir -p -- "$ANCORE_ARGUMENT"
            ANCORE_BACKUP_MOUNT=$(CDPATH='' cd -- "$ANCORE_ARGUMENT" && pwd -P)
            ;;
    esac
    case "$ANCORE_ARGUMENT" in
        --tls-dir=*|--backup-dir=*)
            echo 'Oddziel nazwę opcji i katalog spacją.' >&2
            exit 1
            ;;
    esac
    ANCORE_PREVIOUS=$ANCORE_ARGUMENT
done

run_configurator() {
    if [ -n "$ANCORE_TLS_MOUNT" ]; then
        set -- --volume "$ANCORE_TLS_MOUNT:$ANCORE_TLS_MOUNT:ro" "$@"
    fi
    if [ -n "$ANCORE_BACKUP_MOUNT" ]; then
        set -- --volume "$ANCORE_BACKUP_MOUNT:$ANCORE_BACKUP_MOUNT" "$@"
    fi
    docker run --rm --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1 \
        --volume "$ANCORE_ROOT:$ANCORE_ROOT" --workdir "$ANCORE_ROOT" "$@"
}
run_configurator python:3.14.8-slim-bookworm python scripts/production.py configure "$@"
if [ ! -f "$ANCORE_ENV" ]; then
    echo 'Docker musi działać lokalnie na serwerze i widzieć katalog projektu.' >&2
    exit 1
fi
config_value() {
    sed -n "s/^$1=//p" "$ANCORE_ENV" | sed "s/^'//; s/'$//"
}
for ANCORE_CONFIG_KEY in $(sed -n 's/^\([A-Z][A-Z0-9_]*\)=.*/\1/p' "$ANCORE_ENV"); do
    case "$ANCORE_CONFIG_KEY" in
        ANCORE_*|SECRET_KEY|POSTGRES_*|ONLYOFFICE_*|BACKUP_*|WEB_*) unset "$ANCORE_CONFIG_KEY" ;;
    esac
done
ANCORE_TLS_MODE=$(config_value ANCORE_TLS_MODE)
compose() {
    if [ "$ANCORE_COMPOSE" = plugin ]; then
        if [ "$ANCORE_TLS_MODE" = direct ]; then
            docker compose --env-file "$ANCORE_ENV" -f deploy/compose.yaml -f deploy/compose.tls.yaml "$@"
        else
            docker compose --env-file "$ANCORE_ENV" -f deploy/compose.yaml "$@"
        fi
    elif [ "$ANCORE_TLS_MODE" = direct ]; then
        docker-compose --env-file "$ANCORE_ENV" -f deploy/compose.yaml -f deploy/compose.tls.yaml "$@"
    else
        docker-compose --env-file "$ANCORE_ENV" -f deploy/compose.yaml "$@"
    fi
}
compose config --quiet
if [ -n "$(compose ps --status running --quiet backup)" ]; then
    compose exec -T backup python3 /opt/ancore/backup.py once
fi
compose build --pull
compose up -d --wait --wait-timeout 600
ANCORE_ADDRESS=$(config_value ANCORE_PUBLIC_URL)
if [ -n "$ANCORE_ADDRESS" ]; then
    echo "Ancore jest gotowe: $ANCORE_ADDRESS"
else
    echo "Ancore jest gotowe: http://IP_SERWERA:$(config_value ANCORE_HTTP_PORT)"
fi
