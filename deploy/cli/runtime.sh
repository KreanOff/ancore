# Shared local deployment operations. Called only by ancore.sh and deploy/cli/setup.sh.

ancore_fail() {
    echo "Błąd: $*" >&2
    exit 1
}

ancore_config_value() {
    ANCORE_VALUE_FILE=$ANCORE_ENV
    if [ "$ANCORE_VALUE_FILE" = "$ANCORE_ROOT/deploy/.env" ] && [ ! -f "$ANCORE_VALUE_FILE" ] && [ -f "$ANCORE_ROOT/deploy/.env.production" ]; then
        ANCORE_VALUE_FILE="$ANCORE_ROOT/deploy/.env.production"
    fi
    if [ -f "$ANCORE_VALUE_FILE" ]; then
        sed -n "s/^$1=//p" "$ANCORE_VALUE_FILE" | sed "s/^'//; s/'$//"
    fi
}

ancore_raw_compose() {
    if [ "$ANCORE_COMPOSE" = plugin ]; then
        docker compose "$@"
    else
        docker-compose "$@"
    fi
}

ancore_require_docker() {
    command -v docker >/dev/null 2>&1 || ancore_fail 'Zainstaluj Docker Engine z Docker Compose.'
    if [ -n "${DOCKER_CONTEXT:-}" ]; then
        ANCORE_ENDPOINT=$(docker context inspect "$DOCKER_CONTEXT" --format '{{.Endpoints.docker.Host}}')
    elif [ -n "${DOCKER_HOST:-}" ]; then
        ANCORE_ENDPOINT=$DOCKER_HOST
    else
        ANCORE_ENDPOINT=$(docker context inspect --format '{{.Endpoints.docker.Host}}')
    fi
    case "$ANCORE_ENDPOINT" in
        unix://*) ;;
        *) ancore_fail 'Użyj lokalnego Dockera (socket unix://). Zdalny daemon nie jest obsługiwany.' ;;
    esac
    if ! ANCORE_DOCKER_OS=$(docker info --format '{{.OSType}}'); then
        ancore_fail 'Brak dostępu do Dockera. Uruchom usługę Docker i sprawdź uprawnienia. Na Ubuntu: sudo usermod -aG docker "$USER", potem newgrp docker.'
    fi
    [ "$ANCORE_DOCKER_OS" = linux ] || ancore_fail 'Wymagane są kontenery Linux.'
    if docker compose version >/dev/null 2>&1; then
        ANCORE_COMPOSE=plugin
    elif command -v docker-compose >/dev/null 2>&1; then
        ANCORE_COMPOSE=standalone
    else
        ancore_fail 'Brak Docker Compose.'
    fi
    if ! ancore_raw_compose up --help | grep -q -- '--wait-timeout'; then
        ancore_fail 'Zaktualizuj Docker Compose: wymagana jest obsługa up --wait --wait-timeout.'
    fi
}

ancore_load_config() {
    [ -r "$ANCORE_ENV" ] || ancore_fail "Brak dostępu do konfiguracji $ANCORE_ENV. Uruchom: sh ancore.sh setup"
    # Values from this installation take precedence over the invoking shell.
    for ANCORE_CONFIG_KEY in $(sed -n 's/^\([A-Z][A-Z0-9_]*\)=.*/\1/p' "$ANCORE_ENV"); do
        case "$ANCORE_CONFIG_KEY" in
            ANCORE_*|SECRET_KEY|POSTGRES_*|ONLYOFFICE_*|BACKUP_*|WEB_*) unset "$ANCORE_CONFIG_KEY" ;;
        esac
    done
    ANCORE_TLS_MODE=$(ancore_config_value ANCORE_TLS_MODE)
}

ancore_compose() {
    # Reconfiguration atomically replaces .env. Include its content fingerprint
    # in the backup service so Compose refreshes that file's bind mount.
    ANCORE_CONFIG_FINGERPRINT=$(cksum < "$ANCORE_ENV")
    if [ "${1:-}" = --restore ]; then
        shift
        set -- -f "$ANCORE_ROOT/deploy/compose.restore.yaml" "$@"
    fi
    if [ -f "$ANCORE_ROOT/deploy/compose.recovery.yaml" ]; then
        set -- -f "$ANCORE_ROOT/deploy/compose.recovery.yaml" "$@"
    fi
    if [ "$ANCORE_TLS_MODE" = direct ]; then
        ANCORE_ENV_FILE="$ANCORE_ENV" ANCORE_CONFIG_FINGERPRINT="$ANCORE_CONFIG_FINGERPRINT" ancore_raw_compose --env-file "$ANCORE_ENV" -f "$ANCORE_ROOT/deploy/compose.yaml" \
            -f "$ANCORE_ROOT/deploy/compose.tls.yaml" "$@"
    else
        ANCORE_ENV_FILE="$ANCORE_ENV" ANCORE_CONFIG_FINGERPRINT="$ANCORE_CONFIG_FINGERPRINT" ancore_raw_compose --env-file "$ANCORE_ENV" -f "$ANCORE_ROOT/deploy/compose.yaml" "$@"
    fi
}

ancore_check_port() {
    ANCORE_PORT=$1
    # A repeated install may replace its own web container on the same port.
    if [ -n "$ANCORE_WEB_ID" ]; then
        if docker port "$ANCORE_WEB_ID" | grep -Eq ":${ANCORE_PORT}$"; then
            return
        fi
    fi
    if docker ps --format '{{.Ports}}' | grep -Eq ":${ANCORE_PORT}->"; then
        ancore_fail "Port $ANCORE_PORT jest używany przez inny kontener. Wybierz inny port w sh ancore.sh setup."
    fi
    if command -v ss >/dev/null 2>&1; then
        ANCORE_LISTENERS=$(ss -H -ltn "sport = :$ANCORE_PORT")
        [ -z "$ANCORE_LISTENERS" ] || ancore_fail "Port $ANCORE_PORT jest zajęty na serwerze (np. przez Nginx). Wybierz inny port w sh ancore.sh setup."
    elif command -v netstat >/dev/null 2>&1; then
        ANCORE_LISTENERS=$(netstat -ltn | awk -v port="$ANCORE_PORT" '$4 ~ (":" port "$") {print $4}')
        [ -z "$ANCORE_LISTENERS" ] || ancore_fail "Port $ANCORE_PORT jest zajęty na serwerze. Wybierz inny port w sh ancore.sh setup."
    elif command -v lsof >/dev/null 2>&1; then
        if lsof -nP -iTCP:"$ANCORE_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
            ancore_fail "Port $ANCORE_PORT jest zajęty na serwerze. Wybierz inny port w sh ancore.sh setup."
        fi
    else
        echo 'Brak ss/netstat/lsof: zajętość portów hosta zweryfikuje Docker przy uruchomieniu.'
    fi
}

ancore_check_ports() {
    ANCORE_WEB_ID=$(ancore_compose ps --status running --quiet web)
    ancore_check_port "$(ancore_config_value ANCORE_HTTP_PORT)"
    if [ "$ANCORE_TLS_MODE" = direct ]; then
        ancore_check_port "$(ancore_config_value ANCORE_HTTPS_PORT)"
    fi
}

ancore_show_address() {
    ANCORE_ADDRESS=$(ancore_config_value ANCORE_PUBLIC_URL)
    ANCORE_DISPLAY_BIND=$(ancore_config_value ANCORE_BIND)
    if [ -z "$ANCORE_ADDRESS" ]; then
        if [ "$ANCORE_DISPLAY_BIND" = 127.0.0.1 ]; then
            ANCORE_ADDRESS="http://127.0.0.1:$(ancore_config_value ANCORE_HTTP_PORT)"
        else
            ANCORE_ADDRESS="http://IP_SERWERA:$(ancore_config_value ANCORE_HTTP_PORT)"
        fi
    fi
    echo "Adres Ancore: $ANCORE_ADDRESS"
    echo "Nasłuch: $ANCORE_DISPLAY_BIND"
    case "$(ancore_config_value ANCORE_HOST)" in
        localhost|127.*)
            echo 'Adres localhost/127.x jest lokalny. Dla innych urządzeń podaj IP lub domenę serwera w sh ancore.sh setup.' ;;
        *)
            if [ "$ANCORE_DISPLAY_BIND" = 0.0.0.0 ]; then
                echo 'Dostęp z innych urządzeń wymaga adresu tego serwera oraz przepuszczenia wybranego portu TCP przez zaporę i sieć.'
            fi ;;
    esac
}

ancore_start() {
    ancore_check_ports
    if ! ancore_compose up -d --no-build --pull never --wait --wait-timeout 600; then
        echo 'Uruchomienie nie powiodło się. Sprawdź: sh ancore.sh status oraz sh ancore.sh logs. Przy pierwszej instalacji zbuduj obrazy: sh ancore.sh install' >&2
        return 1
    fi
    echo 'Usługi Ancore są gotowe.'
    ancore_show_address
}

ancore_help() {
    cat <<'HELP'
Lokalny Ancore: sh ancore.sh [--env-file PLIK] [--context NAZWA] POLECENIE
  setup          Konfigurator krok po kroku (--quick: instalacja bez pytań).
  configure      Zapisz konfigurację bez budowania i uruchamiania.
  install        Konfiguracja, lokalne budowanie i uruchomienie.
  update         Backup, przebudowanie i start istniejącej instalacji.
  start          Uruchom zbudowaną aplikację i poczekaj na gotowość.
  stop           Zatrzymaj usługi, zachowując dane.
  restart        Zatrzymaj i ponownie uruchom usługi.
  status         Pokaż stan wszystkich usług.
  logs [USŁUGA]  Śledź ostatnie logi (Ctrl+C kończy podgląd).
  backup         Wykonaj pełny lokalny backup danych, kodu i konfiguracji.
  restore PLIK --yes  Odtwórz backup, zastępując bieżące dane.
  unlock         Usuń pozostałą blokadę backupu, jeśli nie trwa kopia.
  reload         Sprawdź i przeładuj Nginx w Dockerze.
  admin          Utwórz administratora Django.
  doctor         Sprawdź Docker, konfigurację, porty i pokaż stan usług.

Opcje konfiguracji: sh ancore.sh install --help
HELP
}

ancore_install_help() {
    cat <<'HELP'
Instalacja: sh ancore.sh install [OPCJE]
Sama konfiguracja: sh ancore.sh configure [OPCJE]
Domyślnie HTTP na porcie 8080 i dostęp przez IP serwera.
  --url ADRES          Stały adres HTTP lub HTTPS.
  --tls-dir KATALOG    Certyfikaty fullchain.pem i privkey.pem dla HTTPS.
  --reconfigure        Zmień ustawienia, zachowując dane i sekrety.
  --http-port PORT     Port HTTP (domyślnie 8080).
  --https-port PORT    Port HTTPS (domyślnie 443).
  --backup-dir KATALOG Lokalny katalog backupów (domyślnie deploy/backups).
  --bind ADRES         Adres IPv4 nasłuchu (HTTP: domyślnie 0.0.0.0).
  --project NAZWA      Nazwa nowej instalacji (domyślnie ancore-prod).
  --configure-only     Tylko w install: skrót zgodności do configure.
HELP
}

ancore_configure() {
    ANCORE_TLS_MOUNT=''
    ANCORE_BACKUP_MOUNT=''
    ANCORE_PREVIOUS=''
    for ANCORE_ARGUMENT in "$@"; do
        case "$ANCORE_PREVIOUS" in
            --tls-dir) ANCORE_TLS_MOUNT=$(CDPATH='' cd -- "$ANCORE_ARGUMENT" && pwd -P) ;;
            --backup-dir)
                mkdir -p -- "$ANCORE_ARGUMENT"
                ANCORE_BACKUP_MOUNT=$(CDPATH='' cd -- "$ANCORE_ARGUMENT" && pwd -P) ;;
        esac
        case "$ANCORE_ARGUMENT" in
            --env-file|--env-file=*|--context|--context=*)
                ancore_fail 'Opcje --env-file i --context podaj przed nazwą polecenia.' ;;
            --tls-dir=*|--backup-dir=*) ancore_fail 'Oddziel nazwę opcji i katalog spacją.' ;;
        esac
        ANCORE_PREVIOUS=$ANCORE_ARGUMENT
    done
    mkdir -p -- "$(dirname -- "$ANCORE_ENV")"
    ANCORE_ENV_DIR=$(CDPATH='' cd -- "$(dirname -- "$ANCORE_ENV")" && pwd -P)
    ANCORE_ENV="$ANCORE_ENV_DIR/$(basename -- "$ANCORE_ENV")"
    # Separate function positional parameters preserve arbitrary path spaces.
    ancore_run_configurator python:3.14.8-slim-bookworm python deploy/cli/configure.py --env-file "$ANCORE_ENV" "$@"
    ancore_load_config
    ancore_compose config --quiet
}

ancore_run_configurator() {
    if [ -n "$ANCORE_TLS_MOUNT" ]; then set -- --volume "$ANCORE_TLS_MOUNT:$ANCORE_TLS_MOUNT:ro" "$@"; fi
    if [ -n "$ANCORE_BACKUP_MOUNT" ]; then set -- --volume "$ANCORE_BACKUP_MOUNT:$ANCORE_BACKUP_MOUNT" "$@"; fi
    case "$ANCORE_ENV_DIR" in
        "$ANCORE_ROOT"|"$ANCORE_ROOT"/*) ;;
        *) set -- --volume "$ANCORE_ENV_DIR:$ANCORE_ENV_DIR" "$@" ;;
    esac
    docker run --rm --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1 \
        --volume "$ANCORE_ROOT:$ANCORE_ROOT" --workdir "$ANCORE_ROOT" "$@"
}

ancore_install() {
    ANCORE_CONFIGURE_ONLY=false
    ANCORE_ARGUMENT_COUNT=$#
    while [ "$ANCORE_ARGUMENT_COUNT" -gt 0 ]; do
        ANCORE_ARGUMENT=$1
        shift
        case "$ANCORE_ARGUMENT" in
            --configure-only) ANCORE_CONFIGURE_ONLY=true ;;
            *) set -- "$@" "$ANCORE_ARGUMENT" ;;
        esac
        ANCORE_ARGUMENT_COUNT=$((ANCORE_ARGUMENT_COUNT - 1))
    done
    ancore_configure "$@"
    if [ "$ANCORE_CONFIGURE_ONLY" = true ]; then
        echo 'Konfiguracja została zapisana; usługi nie zostały uruchomione.'
        return
    fi
    ancore_install_current
}

ancore_backup() {
    ancore_compose exec -T backup python3 /opt/ancore/backup.py once
}

ancore_install_current() {
    ancore_check_ports
    if [ -n "$(ancore_compose ps --status running --quiet backup)" ]; then ancore_backup; fi
    echo 'Budowanie obrazów i obu frontendów na tym serwerze...'
    BUILDX_BUILDER=default ancore_compose build --pull
    if ! docker image inspect "$(ancore_config_value ONLYOFFICE_IMAGE)" >/dev/null 2>&1; then
        ancore_compose pull onlyoffice
    fi
    ancore_start
}

ancore_restore() {
    [ "$#" -eq 2 ] && [ "$2" = --yes ] || ancore_fail 'Odtworzenie zastępuje dane instalacji. Użyj: sh ancore.sh restore PLIK --yes'
    case "$1" in /*) ANCORE_ARCHIVE=$1 ;; *) ANCORE_ARCHIVE="$ANCORE_CALLER_DIR/$1" ;; esac
    [ -f "$ANCORE_ARCHIVE" ] || ancore_fail 'Nie znaleziono archiwum backupu.'
    ANCORE_ARCHIVE_DIR=$(CDPATH='' cd -- "$(dirname -- "$ANCORE_ARCHIVE")" && pwd -P)
    ANCORE_BACKUP_DIR=$(CDPATH='' cd -- "$(ancore_config_value ANCORE_BACKUP_DIR)" && pwd -P)
    [ "$ANCORE_ARCHIVE_DIR" = "$ANCORE_BACKUP_DIR" ] || ancore_fail 'Archiwum musi znajdować się w skonfigurowanym katalogu backupów.'
    [ -f "$ANCORE_ARCHIVE.sha256" ] || ancore_fail 'Brak pliku .sha256 archiwum.'
    ANCORE_ARCHIVE_NAME=$(basename -- "$ANCORE_ARCHIVE")
    ancore_compose stop web backup backend onlyoffice
    ancore_compose up -d --no-build --pull never --wait postgres
    # On failure leave writers stopped, exactly as the original restore did.
    ancore_compose --restore run --rm --no-deps --pull never backup restore "/backups/$ANCORE_ARCHIVE_NAME"
    ancore_compose run --rm --no-deps --pull never backup unlock
    ancore_start
}
