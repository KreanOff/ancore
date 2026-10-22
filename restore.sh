#!/bin/sh
# Standalone recovery. This file can be copied without the application or installer.
set -eu
umask 077

RECOVERY_HOME=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
RECOVERY_ENV="$RECOVERY_HOME/deploy/.env"
RECOVERY_BACKUPS=''
RECOVERY_TARGET="$RECOVERY_HOME/.recovery"
while [ "$#" -gt 0 ]; do
    case "$1" in
        --help|-h)
            cat <<'HELP'
Ancore — samodzielne odzyskiwanie: sh restore.sh [OPCJE]
  --backup-dir KATALOG  Katalog kopii (domyślnie z deploy/.env lub deploy/backups).
  --target KATALOG      Katalog odzyskanych instalacji (domyślnie .recovery obok skryptu).
  --env-file PLIK       Odczytaj lokalizację kopii z innego pliku konfiguracji.
  --context NAZWA       Lokalny kontekst Docker, bez zmiany kontekstu globalnego.

Wybierz numer jednej z 10 ostatnich kopii; 0 anuluje operację.
Wybranie numeru rozpoczyna odzyskiwanie bez dalszych pytań.
Skrypt odtwarza zapisany kod, konfigurację, bazę i pliki na nowych wolumenach.
Wymaga Dockera z Compose i internetu do brakujących obrazów oraz zależności.
Nie korzysta z instalatora ani Pythona zainstalowanego na hoście.
HELP
            exit 0 ;;
        --backup-dir|--target|--env-file|--context)
            [ "$#" -ge 2 ] || { echo "Brak wartości opcji $1." >&2; exit 1; }
            case "$1" in
                --backup-dir) RECOVERY_BACKUPS=$2 ;;
                --target) RECOVERY_TARGET=$2 ;;
                --env-file) RECOVERY_ENV=$2 ;;
                --context) DOCKER_CONTEXT=$2; export DOCKER_CONTEXT ;;
            esac
            shift 2 ;;
        *) echo "Nieznana opcja: $1. Użyj sh restore.sh --help." >&2; exit 1 ;;
    esac
done
if [ -z "$RECOVERY_BACKUPS" ] && [ -f "$RECOVERY_ENV" ]; then
    RECOVERY_BACKUPS=$(sed -n "s/^ANCORE_BACKUP_DIR=//p" "$RECOVERY_ENV" | sed "s/^'//; s/'$//")
fi
RECOVERY_BACKUPS=${RECOVERY_BACKUPS:-$RECOVERY_HOME/deploy/backups}
[ -d "$RECOVERY_BACKUPS" ] || { echo 'Nie znaleziono katalogu kopii. Podaj --backup-dir KATALOG.' >&2; exit 1; }
RECOVERY_BACKUPS=$(CDPATH='' cd -- "$RECOVERY_BACKUPS" && pwd -P)
command -v docker >/dev/null 2>&1 || { echo 'Zainstaluj i uruchom Docker z Compose.' >&2; exit 1; }
if [ -n "${DOCKER_CONTEXT:-}" ]; then
    RECOVERY_ENDPOINT=$(docker context inspect "$DOCKER_CONTEXT" --format '{{.Endpoints.docker.Host}}')
elif [ -n "${DOCKER_HOST:-}" ]; then
    RECOVERY_ENDPOINT=$DOCKER_HOST
else
    RECOVERY_ENDPOINT=$(docker context inspect --format '{{.Endpoints.docker.Host}}')
fi
case "$RECOVERY_ENDPOINT" in
    unix://*) ;;
    *) echo 'Odzyskiwanie wymaga lokalnego Dockera (socket unix://).' >&2; exit 1 ;;
esac
[ "$(docker info --format '{{.OSType}}')" = linux ] || { echo 'Uruchom Docker z kontenerami Linux.' >&2; exit 1; }
if docker compose version >/dev/null 2>&1; then
    RECOVERY_COMPOSE=plugin
elif command -v docker-compose >/dev/null 2>&1; then
    RECOVERY_COMPOSE=standalone
else
    echo 'Brak Docker Compose.' >&2; exit 1
fi
recovery_raw_compose() {
    if [ "$RECOVERY_COMPOSE" = plugin ]; then docker compose "$@"; else docker-compose "$@"; fi
}
recovery_raw_compose up --help | grep -q -- '--wait-timeout' || {
    echo 'Zaktualizuj Docker Compose: wymagana obsługa up --wait --wait-timeout.' >&2; exit 1;
}

RECOVERY_TEMP=$(mktemp -d "${TMPDIR:-/tmp}/ancore-recovery.XXXXXX")
RECOVERY_WORK=$RECOVERY_TEMP
RECOVERY_STOPPED=false
RECOVERY_LOCK=''
recovery_cleanup() {
    RECOVERY_RESULT=$?
    trap - EXIT
    if [ "$RECOVERY_RESULT" -ne 0 ] && [ "$RECOVERY_STOPPED" = true ]; then
        recovery_compose stop web backup backend onlyoffice >&2 || :
        echo "Odzyskiwanie nie powiodło się. Usługi aplikacji pozostały zatrzymane. Pliki diagnostyczne: $RECOVERY_WORK" >&2
        echo 'Poprzednie wolumeny danych zostały zachowane. Możesz ponowić wybór kopii.' >&2
    fi
    if [ -n "$RECOVERY_LOCK" ]; then docker rm "$RECOVERY_LOCK" >/dev/null 2>&1 || :; fi
    rm -rf -- "$RECOVERY_TEMP"
    exit "$RECOVERY_RESULT"
}
trap recovery_cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Only Docker is needed on the host. This embedded helper has no Docker socket.
cat > "$RECOVERY_TEMP/recovery.py" <<'PYTHON'
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tarfile
import uuid

VOLUMES = ('postgres', 'private', 'media', 'temporary', 'control', 'static',
           'office_data', 'office_cache', 'office_database', 'office_rabbitmq',
           'office_redis', 'office_logs')
SOURCE_ROOTS = {'backend', 'frontend', 'static', 'deploy', 'scripts', 'manage.py',
                'requirements.txt', 'ancore.sh', 'restore.sh', '.dockerignore',
                'docs', 'README.md', 'AGENTS.md'}


def extract(archive, destination, roots):
    with tarfile.open(archive, 'r:gz') as source:
        seen = set()
        for entry in source.getmembers():
            path = Path(entry.name)
            if entry.name in ('.', './') and entry.isdir():
                continue
            if (not path.parts or path.is_absolute() or '..' in path.parts
                    or path.parts[0] not in roots or str(path) in seen
                    or entry.issym() or entry.islnk()
                    or not (entry.isfile() or entry.isdir())):
                raise ValueError('Archiwum zawiera nieprawidłową ścieżkę lub typ pliku.')
            seen.add(str(path))
        source.extractall(destination, filter='data')


def read_config(path):
    config = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, separator, value = line.partition('=')
        if not separator or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key):
            raise ValueError('Nieprawidłowy plik konfiguracji w kopii.')
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        if any(char in value for char in "\r\n'"):
            raise ValueError('Niedozwolony znak w konfiguracji kopii.')
        config[key] = value
    required = ('ANCORE_PROJECT', 'SECRET_KEY', 'POSTGRES_PASSWORD',
                'POSTGRES_ADMIN_PASSWORD', 'ONLYOFFICE_JWT_SECRET', 'ONLYOFFICE_IMAGE')
    if not all(config.get(key) for key in required):
        raise ValueError('Kopia nie zawiera pełnej konfiguracji instalacji.')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', config['ANCORE_PROJECT']):
        raise ValueError('Nieprawidłowy projekt Compose w kopii.')
    return config


def prepare(archive, work, backups, uid, gid):
    checksum = archive.with_name(archive.name + '.sha256').read_text().split()
    with archive.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if not checksum or checksum[0].lower() != actual:
        raise ValueError('Nieprawidłowa suma SHA-256. Żadne usługi nie zostały zatrzymane.')
    payload = work / 'payload'
    extract(archive, payload, {'database.dump', 'manifest.json', 'private', 'media', 'recovery'})
    metadata = json.loads((payload / 'manifest.json').read_text())
    if metadata.get('format') != 2:
        raise ValueError('Ta starsza kopia nie zawiera kodu i konfiguracji. '
                         'Pełne odzyskiwanie wymaga nowej kopii formatu 2; '
                         'starsze dane można odtworzyć dotychczasowym poleceniem restore.')
    if not (payload / 'database.dump').is_file() or not all(
            (payload / name).is_dir() for name in ('private', 'media')):
        raise ValueError('Brak bazy lub katalogów plików w kopii.')
    application = work / 'application'
    extract(payload / 'recovery/application.tar.gz', application, SOURCE_ROOTS)
    for name in ('manage.py', 'requirements.txt', 'ancore.sh', 'restore.sh', '.dockerignore',
                 'deploy/compose.yaml', 'deploy/compose.restore.yaml', 'deploy/compose.tls.yaml',
                 'deploy/Dockerfile', 'deploy/backup/backup.py', 'deploy/cli/runtime.sh',
                 'frontend/app/pnpm-lock.yaml', 'frontend/board/pnpm-lock.yaml'):
        if not (application / name).is_file():
            raise ValueError('Kopia nie zawiera pełnego kodu aplikacji: ' + name)
    # Never reuse volume names, environment files or TLS paths embedded in the source.
    (application / 'deploy/compose.recovery.yaml').unlink(missing_ok=True)
    config = read_config(payload / 'recovery/production.env')
    config.update(ANCORE_BACKUP_DIR=str(backups), BACKUP_KEEP='10', BACKUP_INTERVAL_SECONDS='86400')
    if config.get('ANCORE_TLS_MODE') == 'direct':
        tls = application / 'deploy/certs'
        tls.mkdir(parents=True, exist_ok=True)
        for name in ('fullchain.pem', 'privkey.pem'):
            (tls / name).write_bytes((payload / 'recovery/tls' / name).read_bytes())
            (tls / name).chmod(0o600)
        config['ANCORE_TLS_DIR'] = str(tls)
    env = application / 'deploy/.env'
    env.write_text(''.join(f"{key}='{value}'\n" for key, value in config.items()))
    env.chmod(0o600)
    token = uuid.uuid4().hex[:12]
    override = {'volumes': {name: {'name': f"{config['ANCORE_PROJECT']}_recovery_{token}_{name}"}
                            for name in VOLUMES}}
    (application / 'deploy/compose.recovery.yaml').write_text(json.dumps(override, indent=2) + '\n')
    (work / 'project').write_text(config['ANCORE_PROJECT'])
    (work / 'tls-mode').write_text(config.get('ANCORE_TLS_MODE', 'http'))
    (work / 'office-image').write_text(config['ONLYOFFICE_IMAGE'])
    (work / 'config-keys').write_text('\n'.join(config))
    address = config.get('ANCORE_PUBLIC_URL') or 'http://IP_SERWERA:' + config.get('ANCORE_HTTP_PORT', '8080')
    (work / 'address').write_text(address)
    # The helper runs as root to read private archives made by the backup container.
    # Source/configuration must remain manageable by the user running this script.
    for root, directories, files in os.walk(application):
        os.chown(root, uid, gid)
        for name in files:
            os.chown(Path(root) / name, uid, gid)
    for name in ('ancore.sh', 'restore.sh'):
        (application / name).chmod(0o700)
    for name in ('project', 'tls-mode', 'office-image', 'config-keys', 'address'):
        os.chown(work / name, uid, gid)
    print('Sprawdzono kopię. Przygotowano kod, konfigurację i nowe nazwy wolumenów.', flush=True)


def main():
    action, *arguments = sys.argv[1:]
    if action == 'list':
        backups, choices = map(Path, arguments)
        archives = sorted((path for path in backups.glob('ancore-*.tar.gz')
                           if re.fullmatch(r'ancore-\d{8}T\d{6}-[a-f0-9]{8}\.tar\.gz', path.name)
                           and path.is_file() and not path.is_symlink()
                           and path.with_name(path.name + '.sha256').is_file()), reverse=True)[:10]
        if not archives:
            raise ValueError('Brak kopii z plikami .sha256 w wybranym katalogu.')
        choices.write_text(''.join(path.name + '\n' for path in archives))
        choices.chmod(0o644)
        for index, path in enumerate(archives, 1):
            print(f'{index:2}. {path.name}  ({path.stat().st_size / 1024**2:.1f} MiB)')
    elif action == 'prepare':
        archive, work, backups, uid, gid = arguments
        prepare(Path(archive), Path(work), Path(backups), int(uid), int(gid))
    else:
        raise ValueError('Nieznana operacja odzyskiwania.')


try:
    main()
except (OSError, ValueError, KeyError, tarfile.TarError) as error:
    print(f'Błąd odzyskiwania: {error}', file=sys.stderr)
    sys.exit(1)
PYTHON

recovery_helper() {
    if [ "$RECOVERY_WORK" != "$RECOVERY_TEMP" ]; then
        set -- --volume "$RECOVERY_WORK:$RECOVERY_WORK" python:3.14.8-slim-bookworm \
            python "$RECOVERY_TEMP/recovery.py" "$@"
    else
        set -- python:3.14.8-slim-bookworm python "$RECOVERY_TEMP/recovery.py" "$@"
    fi
    docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 \
        --volume "$RECOVERY_TEMP:$RECOVERY_TEMP" \
        --volume "$RECOVERY_BACKUPS:$RECOVERY_BACKUPS:ro" "$@"
}

echo 'Ancore — odzyskiwanie danych i aplikacji'
echo "Katalog kopii: $RECOVERY_BACKUPS"
echo 'Ostatnie 10 kopii (od najnowszej; znacznik daty w nazwie jest w UTC):'
recovery_helper list "$RECOVERY_BACKUPS" "$RECOVERY_TEMP/choices"
echo ''
echo 'Wybór kopii zastąpi działającą instalację stanem zapisanym w tej kopii.'
echo 'Bieżące usługi zostaną zatrzymane po sprawdzeniu kopii i przygotowaniu obrazów.'
echo 'Dotychczasowe wolumeny pozostaną zachowane. 0 — anuluj.'
while :; do
    printf 'Numer kopii: '
    if ! IFS= read -r RECOVERY_CHOICE; then
        echo 'Przerwano: nie wybrano kopii.' >&2; exit 1
    fi
    case "$RECOVERY_CHOICE" in
        0) echo 'Anulowano odzyskiwanie.'; exit 0 ;;
        [1-9]|10)
            RECOVERY_ARCHIVE=$(sed -n "${RECOVERY_CHOICE}p" "$RECOVERY_TEMP/choices")
            [ -z "$RECOVERY_ARCHIVE" ] || break ;;
    esac
    echo 'Podaj numer kopii z listy albo 0.'
done

mkdir -p -- "$RECOVERY_TARGET"
RECOVERY_TARGET=$(CDPATH='' cd -- "$RECOVERY_TARGET" && pwd -P)
RECOVERY_WORK=$(mktemp -d "$RECOVERY_TARGET/restore-XXXXXXXX")
echo '[1/5] Sprawdzanie sumy kontrolnej i przygotowywanie wybranej wersji...'
recovery_helper prepare "$RECOVERY_BACKUPS/$RECOVERY_ARCHIVE" "$RECOVERY_WORK" \
    "$RECOVERY_BACKUPS" "$(id -u)" "$(id -g)"
RECOVERY_APP="$RECOVERY_WORK/application"
RECOVERY_PROJECT=$(cat "$RECOVERY_WORK/project")
RECOVERY_TLS=$(cat "$RECOVERY_WORK/tls-mode")
RECOVERY_OFFICE=$(cat "$RECOVERY_WORK/office-image")
for RECOVERY_KEY in $(cat "$RECOVERY_WORK/config-keys"); do
    case "$RECOVERY_KEY" in
        ANCORE_*|SECRET_KEY|POSTGRES_*|ONLYOFFICE_*|BACKUP_*|WEB_*) unset "$RECOVERY_KEY" ;;
    esac
done
recovery_compose() {
    if [ "${1:-}" = --restore ]; then
        shift
        set -- -f "$RECOVERY_APP/deploy/compose.restore.yaml" "$@"
    fi
    set -- -f "$RECOVERY_APP/deploy/compose.recovery.yaml" "$@"
    if [ "$RECOVERY_TLS" = direct ]; then
        set -- -f "$RECOVERY_APP/deploy/compose.tls.yaml" "$@"
    fi
    ANCORE_ENV_FILE="$RECOVERY_APP/deploy/.env" recovery_raw_compose \
        --project-name "$RECOVERY_PROJECT" --env-file "$RECOVERY_APP/deploy/.env" \
        -f "$RECOVERY_APP/deploy/compose.yaml" "$@"
}
recovery_compose config --quiet
# A named, stopped container serializes recovery across different target directories.
if ! docker create --name "$RECOVERY_PROJECT-recovery-lock" --network none \
    python:3.14.8-slim-bookworm python -c pass >/dev/null; then
    echo 'Inne odzyskiwanie tej instalacji trwa albo pozostawiło blokadę. Sprawdź kontener z końcówką -recovery-lock.' >&2
    exit 1
fi
RECOVERY_LOCK="$RECOVERY_PROJECT-recovery-lock"
echo '[2/5] Budowanie obrazów z kodu zapisanego w kopii. To może potrwać...'
BUILDX_BUILDER=default recovery_compose build
if ! docker image inspect "$RECOVERY_OFFICE" >/dev/null 2>&1; then
    recovery_compose pull onlyoffice
fi
recovery_compose run --rm --no-deps --pull never --entrypoint pg_restore \
    --volume "$RECOVERY_WORK/payload:/recovery-input:ro" backup --list /recovery-input/database.dump >/dev/null
echo '[3/5] Zatrzymywanie usług i przygotowywanie nowej bazy...'
RECOVERY_STOPPED=true
recovery_compose stop web backup backend onlyoffice postgres
recovery_compose up -d --no-build --pull never --wait --wait-timeout 600 postgres
echo '[4/5] Odtwarzanie bazy, dokumentów i załączników...'
recovery_compose --restore run --rm --no-deps --pull never \
    --volume "$RECOVERY_WORK/payload:/recovery-input:ro" backup restore-prepared /recovery-input
echo '[5/5] Uruchamianie aplikacji i sprawdzanie gotowości usług...'
recovery_compose up -d --no-build --pull never --wait --wait-timeout 600
RECOVERY_STOPPED=false
echo "Odzyskano aplikację z kopii: $RECOVERY_ARCHIVE"
echo "Adres: $(cat "$RECOVERY_WORK/address")"
echo "Odtworzona instalacja: $RECOVERY_APP"
echo "Dalsza obsługa: cd \"$RECOVERY_APP\" && ./ancore.sh status"
