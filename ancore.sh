#!/bin/sh
# Canonical entry point for local installation and service management.
set -eu
umask 077
ANCORE_CALLER_DIR=$(pwd -P)
ANCORE_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
ANCORE_ENV="$ANCORE_ROOT/deploy/.env"
. "$ANCORE_ROOT/deploy/cli/runtime.sh"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --env-file|--context)
            [ "$#" -ge 2 ] || ancore_fail "Brak wartości opcji $1."
            if [ "$1" = --env-file ]; then
                case "$2" in /*) ANCORE_ENV=$2 ;; *) ANCORE_ENV="$ANCORE_CALLER_DIR/$2" ;; esac
            else
                DOCKER_CONTEXT=$2
                export DOCKER_CONTEXT
            fi
            shift 2 ;;
        --) shift; break ;;
        *) break ;;
    esac
done
cd "$ANCORE_ROOT"
ANCORE_ACTION=${1:-help}
if [ "$#" -gt 0 ]; then shift; fi
case "$ANCORE_ACTION" in
    help|--help|-h) ancore_help; exit 0 ;;
    setup)
        case "${1:-}" in --help|-h) ancore_help; exit 0 ;; esac
        export ANCORE_ENV
        exec sh "$ANCORE_ROOT/deploy/cli/setup.sh" "$@" ;;
    install|configure)
        case "${1:-}" in --help|-h) ancore_install_help; exit 0 ;; esac ;;
    update|start|stop|restart|status|logs|backup|restore|unlock|reload|admin|doctor) ;;
    *) ancore_fail 'Nieznane polecenie. Użyj sh ancore.sh --help.' ;;
esac
case "$ANCORE_ACTION" in
    install|configure|logs|restore) ;;
    *) [ "$#" -eq 0 ] || ancore_fail 'To polecenie nie przyjmuje dodatkowych argumentów. Użyj sh ancore.sh --help.' ;;
esac
ancore_require_docker
case "$ANCORE_ACTION" in
    install) ancore_install "$@"; exit ;;
    configure) ancore_configure "$@"; exit ;;
esac
ancore_load_config
ancore_compose config --quiet
case "$ANCORE_ACTION" in
    start) ancore_start ;;
    stop) ancore_compose stop ;;
    restart) ancore_compose stop; ancore_start ;;
    status) ancore_compose ps -a ;;
    logs) ancore_compose logs --tail=100 --follow "$@" ;;
    update) ancore_configure; ancore_install_current ;;
    backup) ancore_backup ;;
    restore) ancore_restore "$@" ;;
    unlock) ancore_compose run --rm --no-deps --pull never backup unlock ;;
    reload)
        ancore_compose exec -T web nginx -t
        ancore_compose exec -T web nginx -s reload ;;
    admin) ancore_compose exec backend python manage.py createsuperuser ;;
    doctor)
        ancore_check_ports
        echo 'Docker, konfiguracja Compose i porty: OK'
        ancore_compose ps -a
        ancore_show_address ;;
esac
