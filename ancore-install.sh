#!/bin/sh
# One entry point for HTTP setup and the first Django administrator.
set +ax
set -eu
umask 077
ANCORE_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
ANCORE_ENV="$ANCORE_ROOT/deploy/.env"
. "$ANCORE_ROOT/deploy/cli/runtime.sh"
cd "$ANCORE_ROOT"

ANCORE_ACTION=${1:-install}
if [ "$#" -gt 0 ]; then shift; fi
case "$ANCORE_ACTION" in
    help|--help|-h) ancore_help; exit 0 ;;
    install|setup|update|start|stop|restart|status|logs|admin) ;;
    *) ancore_fail 'Nieznane polecenie. Użyj sh ancore-install.sh --help.' ;;
esac
if [ "${1:-}" = --help ] || [ "${1:-}" = -h ]; then ancore_help; exit 0; fi
if [ "$ANCORE_ACTION" = logs ]; then
    [ "$#" -le 1 ] || ancore_fail 'Użyj: sh ancore-install.sh logs [web|backend|postgres|onlyoffice].'
    case "${1:-}" in ''|web|backend|postgres|onlyoffice) ;; *) ancore_fail 'Nieznana usługa.' ;; esac
else
    [ "$#" -eq 0 ] || ancore_fail 'To polecenie nie przyjmuje opcji. Użyj sh ancore-install.sh --help.'
fi
case "$ANCORE_ACTION" in
    install|setup)
        . "$ANCORE_ROOT/deploy/cli/setup.sh"
        ancore_banner ;;
esac
ancore_require_docker
case "$ANCORE_ACTION" in
    install|setup)
        ancore_collect_setup
        printf '\n[1/3] Przygotowanie konfiguracji instalacji...\n'
        docker run --rm --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1 \
            --volume "$ANCORE_ROOT:$ANCORE_ROOT" --workdir "$ANCORE_ROOT" \
            python:3.14.8-slim-bookworm python deploy/cli/configure.py \
            "$ANCORE_INPUT_HOST" "$ANCORE_INPUT_PORT" ;;
esac
ancore_load_config
ancore_compose config --quiet
case "$ANCORE_ACTION" in
    install|setup)
        printf '\n[2/3] Instalacja i uruchomienie usług...\n'
        ancore_build
        ancore_start
        printf '\n[3/3] Przygotowanie administratora...\n'
        if ! ancore_finish_admin; then
            ancore_fail 'Tworzenie administratora Django nie powiodło się. Ponów: sh ancore-install.sh admin'
        fi
        ancore_show_ready ;;
    update) ancore_build; ancore_start; ancore_show_ready ;;
    start) ancore_start; ancore_show_ready ;;
    stop) ancore_compose stop ;;
    restart) ancore_compose stop; ancore_start; ancore_show_ready ;;
    status) ancore_compose ps -a ;;
    logs) ancore_compose logs --tail=100 --follow "$@" ;;
    admin) ancore_compose exec backend python manage.py createsuperuser ;;
esac
