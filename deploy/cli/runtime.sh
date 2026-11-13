# Shared operations for ancore-install.sh. POSIX sh; no host Python or Node needed.

ancore_fail() {
    echo "Błąd: $*" >&2
    exit 1
}

ancore_help() {
    cat <<'HELP'
Instalacja: sh ancore-install.sh
Podaj IP serwera, port HTTP i dane administratora. Potem instalacja przebiega automatycznie.

  install / setup  Instalacja i pierwszy administrator; zachowuje dane i hasła.
  update           Przebuduj i uruchom z aktualnych źródeł.
  start            Uruchom przygotowaną instalację.
  stop             Zatrzymaj kontenery, zachowując dane.
  restart          Uruchom kontenery ponownie.
  status           Pokaż stan czterech usług.
  logs [USŁUGA]    Pokaż logi: web, backend, postgres lub onlyoffice.
  admin            Utwórz administratora Django.
HELP
}

ancore_config_value() {
    sed -n "s/^$1=//p" "$ANCORE_ENV" | sed "s/^'//; s/'$//"
}

ancore_raw_compose() {
    if [ "$ANCORE_COMPOSE" = plugin ]; then docker compose "$@"; else docker-compose "$@"; fi
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
    case "$ANCORE_ENDPOINT" in unix://*) ;; *) ancore_fail 'Użyj lokalnego Dockera (socket unix://).' ;; esac
    if ! ANCORE_DOCKER_OS=$(docker info --format '{{.OSType}}'); then
        ancore_fail 'Brak dostępu do Dockera. Uruchom usługę Docker i sprawdź uprawnienia użytkownika.'
    fi
    [ "$ANCORE_DOCKER_OS" = linux ] || ancore_fail 'Wymagane są kontenery Linux.'
    if docker compose version >/dev/null 2>&1; then
        ANCORE_COMPOSE=plugin
    elif command -v docker-compose >/dev/null 2>&1; then
        ANCORE_COMPOSE=standalone
    else
        ancore_fail 'Zainstaluj Docker Compose.'
    fi
    if ! ancore_raw_compose up --help | grep -q -- '--wait-timeout'; then
        ancore_fail 'Zaktualizuj Docker Compose: wymagana obsługa up --wait --wait-timeout.'
    fi
}

ancore_load_config() {
    [ -r "$ANCORE_ENV" ] || ancore_fail 'Brak deploy/.env. Uruchom: sh ancore-install.sh'
    # Compose gives shell variables precedence over --env-file. Keep the saved
    # project, image tags and credentials authoritative without sourcing a file.
    unset ANCORE_PROJECT ANCORE_HOST ANCORE_PUBLIC_URL ANCORE_HTTP_PORT ANCORE_RELEASE
    unset SECRET_KEY POSTGRES_PASSWORD POSTGRES_ADMIN_PASSWORD ONLYOFFICE_JWT_SECRET ONLYOFFICE_IMAGE
    unset WEB_WORKERS WEB_THREADS
    ANCORE_PROJECT_NAME=$(ancore_config_value ANCORE_PROJECT)
    [ -n "$ANCORE_PROJECT_NAME" ] || ancore_fail 'Brak nazwy projektu w deploy/.env. Uruchom: sh ancore-install.sh'
    case "$(ancore_config_value ANCORE_PUBLIC_URL)" in
        http://*) ;;
        *) ancore_fail 'Konfiguracja wymaga IP i portu HTTP. Uruchom: sh ancore-install.sh' ;;
    esac
}

ancore_compose() {
    # Older recovered installations used explicit volume names. Keep their data
    # mapping without retaining a recovery command or a backup service.
    if [ -f "$ANCORE_ROOT/deploy/compose.recovery.yaml" ]; then
        set -- -f "$ANCORE_ROOT/deploy/compose.recovery.yaml" "$@"
    fi
    ancore_raw_compose --project-name "$ANCORE_PROJECT_NAME" --env-file "$ANCORE_ENV" \
        -f "$ANCORE_ROOT/deploy/compose.yaml" "$@"
}

ancore_check_port() {
    ANCORE_PORT=$(ancore_config_value ANCORE_HTTP_PORT)
    ANCORE_WEB_ID=$(ancore_compose ps --status running --quiet web)
    # Reinstalling may reuse the port of this project's current web container.
    if [ -n "$ANCORE_WEB_ID" ] && docker port "$ANCORE_WEB_ID" | grep -Eq ":${ANCORE_PORT}$"; then return; fi
    if docker ps --format '{{.Ports}}' | grep -Eq ":${ANCORE_PORT}->"; then
        ancore_fail "Port $ANCORE_PORT jest używany przez inny kontener. Uruchom sh ancore-install.sh i wybierz inny port."
    fi
    if command -v ss >/dev/null 2>&1; then
        ANCORE_LISTENERS=$(ss -H -ltn "sport = :$ANCORE_PORT")
        [ -z "$ANCORE_LISTENERS" ] || ancore_fail "Port $ANCORE_PORT jest zajęty. Uruchom sh ancore-install.sh i wybierz inny port."
    elif command -v lsof >/dev/null 2>&1; then
        if lsof -nP -iTCP:"$ANCORE_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
            ancore_fail "Port $ANCORE_PORT jest zajęty. Uruchom sh ancore-install.sh i wybierz inny port."
        fi
    fi
}

ancore_build() {
    ancore_check_port
    echo 'Budowanie aplikacji i pobieranie potrzebnych obrazów...'
    BUILDX_BUILDER=default ancore_compose build --pull backend web postgres
    if ! docker image inspect "$(ancore_config_value ONLYOFFICE_IMAGE)" >/dev/null 2>&1; then
        ancore_compose pull onlyoffice
    fi
}

ancore_start() {
    ancore_check_port
    if ! ancore_compose up -d --no-build --pull never --remove-orphans --wait --wait-timeout 600; then
        echo 'Uruchomienie nie powiodło się. Sprawdź: sh ancore-install.sh status oraz sh ancore-install.sh logs.' >&2
        return 1
    fi
}

ancore_show_ready() {
    echo 'Usługi Ancore są gotowe.'
    printf 'Adres Ancore: %s\n' "$(ancore_config_value ANCORE_PUBLIC_URL)"
}
