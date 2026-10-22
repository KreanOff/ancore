#!/bin/sh
# Terminal wizard called by ancore.sh setup; POSIX sh, including Ubuntu dash.
set -eu
umask 077
ANCORE_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
cd "$ANCORE_ROOT"
ANCORE_ENV=${ANCORE_ENV:-$ANCORE_ROOT/deploy/.env}
. "$ANCORE_ROOT/deploy/cli/runtime.sh"

case "${1:-}" in
    --help|-h) ancore_help; exit 0 ;;
    --quick) shift; exec sh "$ANCORE_ROOT/ancore.sh" --env-file "$ANCORE_ENV" install "$@" ;;
    '') ;;
    *) ancore_fail 'Nieznana opcja. Użyj sh ancore.sh --help.' ;;
esac
ancore_require_docker

ancore_ask() {
    printf '%s [%s]: ' "$1" "$2"
    if ! IFS= read -r ANCORE_REPLY; then
        ancore_fail 'Przerwano konfigurację: brak odpowiedzi. Dla instalacji automatycznej użyj sh ancore.sh install.'
    fi
    ANCORE_REPLY=${ANCORE_REPLY:-$2}
}

ancore_ask_port() {
    while :; do
        ancore_ask "$1" "$2"
        case "$ANCORE_REPLY" in ''|*[!0-9]*|??????*) ;;
            *) if [ "$ANCORE_REPLY" -ge 1 ] && [ "$ANCORE_REPLY" -le 65535 ]; then return; fi ;;
        esac
        echo 'Podaj port od 1 do 65535.'
    done
}

echo 'Ancore — instalacja na tym serwerze'
echo 'Obrazy aplikacji i oba frontendy zostaną zbudowane lokalnie. Nginx, baza, pliki, backup i ONLYOFFICE działają w Dockerze.'
echo 'Pierwszy build pobiera obrazy bazowe i zależności z internetu.'

ANCORE_WIZ_HOST=$(ancore_config_value ANCORE_HOST)
case "$ANCORE_WIZ_HOST" in ''|_) ANCORE_WIZ_HOST=auto ;; esac
while :; do
    ancore_ask 'IP lub domena serwera, bez protokołu i portu (auto = dowolny IP serwera)' "$ANCORE_WIZ_HOST"
    case "$ANCORE_REPLY" in
        *[!a-zA-Z0-9.-]*) echo 'Podaj samo IP lub domenę, bez protokołu i portu. Port wybierzesz osobno.' ;;
        *) ANCORE_WIZ_HOST=$ANCORE_REPLY; break ;;
    esac
done
ANCORE_WIZ_MODE=$(ancore_config_value ANCORE_TLS_MODE)
case "$ANCORE_WIZ_MODE" in direct) ANCORE_WIZ_MODE=2 ;; external) ANCORE_WIZ_MODE=3 ;; *) ANCORE_WIZ_MODE=1 ;; esac
echo '1 — HTTP; 2 — HTTPS z certyfikatem na serwerze; 3 — HTTPS przez istniejący reverse proxy'
while :; do
    ancore_ask 'Sposób dostępu' "$ANCORE_WIZ_MODE"
    case "$ANCORE_REPLY" in 1|2|3) ANCORE_WIZ_MODE=$ANCORE_REPLY; break ;; esac
    echo 'Wybierz 1, 2 albo 3.'
done
[ "$ANCORE_WIZ_MODE" = 1 ] || [ "$ANCORE_WIZ_HOST" != auto ] || ancore_fail 'HTTPS wymaga konkretnego IP lub domeny. Ponów konfigurator i podaj adres.'
ANCORE_WIZ_HTTP=$(ancore_config_value ANCORE_HTTP_PORT)
ancore_ask_port 'Port HTTP na serwerze' "${ANCORE_WIZ_HTTP:-8080}"
ANCORE_WIZ_HTTP=$ANCORE_REPLY
ANCORE_WIZ_HTTPS=$(ancore_config_value ANCORE_HTTPS_PORT)
if [ "$(ancore_config_value ANCORE_TLS_MODE)" = external ]; then
    ANCORE_WIZ_AUTHORITY=$(ancore_config_value ANCORE_AUTHORITY)
    case "$ANCORE_WIZ_AUTHORITY" in *:*) ANCORE_WIZ_HTTPS=${ANCORE_WIZ_AUTHORITY##*:} ;; esac
fi
if [ "$ANCORE_WIZ_MODE" != 1 ]; then
    ancore_ask_port 'Publiczny port HTTPS' "${ANCORE_WIZ_HTTPS:-443}"
    ANCORE_WIZ_HTTPS=$ANCORE_REPLY
fi
ANCORE_WIZ_TLS=''
if [ "$ANCORE_WIZ_MODE" = 2 ]; then
    ANCORE_WIZ_TLS=$(ancore_config_value ANCORE_TLS_DIR)
    ancore_ask 'Katalog z fullchain.pem i privkey.pem' "${ANCORE_WIZ_TLS:-$ANCORE_ROOT/deploy/certs}"
    ANCORE_WIZ_TLS=$ANCORE_REPLY
fi
if [ "$ANCORE_WIZ_MODE" = 3 ]; then
    ANCORE_WIZ_BIND=127.0.0.1
else
    ANCORE_WIZ_ACCESS=1
    ANCORE_WIZ_BIND=$(ancore_config_value ANCORE_BIND)
    case "$ANCORE_WIZ_BIND" in 127.0.0.1) ANCORE_WIZ_ACCESS=2 ;; ''|0.0.0.0) ;; *) ANCORE_WIZ_ACCESS=3 ;; esac
    echo '1 — dostęp z sieci (0.0.0.0); 2 — tylko ten serwer (127.0.0.1); 3 — konkretny interfejs IPv4'
    while :; do
        ancore_ask 'Nasłuch' "$ANCORE_WIZ_ACCESS"
        case "$ANCORE_REPLY" in
            1) ANCORE_WIZ_BIND=0.0.0.0; break ;;
            2) ANCORE_WIZ_BIND=127.0.0.1; break ;;
            3)
                ancore_ask 'Adres IPv4 interfejsu serwera' "${ANCORE_WIZ_BIND:-0.0.0.0}"
                ANCORE_WIZ_BIND=$ANCORE_REPLY
                break ;;
        esac
        echo 'Wybierz 1, 2 albo 3.'
    done
fi
ANCORE_WIZ_BACKUP=$(ancore_config_value ANCORE_BACKUP_DIR)
ancore_ask 'Lokalny katalog backupów' "${ANCORE_WIZ_BACKUP:-$ANCORE_ROOT/deploy/backups}"
ANCORE_WIZ_BACKUP=$ANCORE_REPLY

set -- --reconfigure --http-port "$ANCORE_WIZ_HTTP" --bind "$ANCORE_WIZ_BIND" --backup-dir "$ANCORE_WIZ_BACKUP"
if [ "$ANCORE_WIZ_MODE" = 1 ]; then
    ANCORE_WIZ_URL="http://IP_SERWERA:$ANCORE_WIZ_HTTP"
    if [ "$ANCORE_WIZ_HOST" != auto ]; then
        ANCORE_WIZ_URL="http://$ANCORE_WIZ_HOST:$ANCORE_WIZ_HTTP"
        set -- "$@" --url "$ANCORE_WIZ_URL"
    fi
else
    ANCORE_WIZ_URL="https://$ANCORE_WIZ_HOST:$ANCORE_WIZ_HTTPS"
    set -- "$@" --url "$ANCORE_WIZ_URL" --https-port "$ANCORE_WIZ_HTTPS"
    if [ -n "$ANCORE_WIZ_TLS" ]; then set -- "$@" --tls-dir "$ANCORE_WIZ_TLS"; fi
fi

echo ''
echo 'Podsumowanie konfiguracji:'
echo "Adres: $ANCORE_WIZ_URL"
echo "Nasłuch: $ANCORE_WIZ_BIND; port HTTP: $ANCORE_WIZ_HTTP"
echo 'Dane aplikacji i edytora: trwałe wolumeny Docker na tym serwerze'
echo "Backupy: $ANCORE_WIZ_BACKUP"
if [ "$ANCORE_WIZ_MODE" = 3 ]; then
    echo "Istniejący proxy musi kierować ruch na 127.0.0.1:$ANCORE_WIZ_HTTP."
fi
sh "$ANCORE_ROOT/ancore.sh" --env-file "$ANCORE_ENV" configure "$@"
while :; do
    ancore_ask 'Zbudować lokalnie i uruchomić Ancore teraz? (t/n)' t
    case "$ANCORE_REPLY" in
        t|T|tak|Tak|y|Y|yes) exec sh "$ANCORE_ROOT/ancore.sh" --env-file "$ANCORE_ENV" install ;;
        n|N|nie|Nie|no)
            if [ "$ANCORE_ENV" = "$ANCORE_ROOT/deploy/.env" ]; then
                echo 'Konfiguracja została zapisana. Zbuduj i uruchom później: sh ancore.sh install'
            else
                echo 'Konfiguracja została zapisana. Później wykonaj polecenie install z tym samym --env-file.'
                printf 'Plik konfiguracji: %s\n' "$ANCORE_ENV"
            fi
            exit 0 ;;
    esac
    echo 'Wpisz t albo n.'
done
