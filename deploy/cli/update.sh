# Download a fast-forward update without replacing local configuration or data.
# Loaded for update with a prompted or supplied URL. POSIX sh; Git runs on the host.

ancore_prompt_update_url() {
    while :; do
        printf 'Podaj link do repozytorium GitHub: '
        IFS= read -r ANCORE_UPDATE_INPUT || \
            ancore_fail 'Przerwano aktualizację: nie podano linku do repozytorium.'
        ANCORE_UPDATE_INPUT=$(printf '%s' "$ANCORE_UPDATE_INPUT" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
        # A failed validation exits only the subshell, so the prompt can retry.
        if (ancore_update_url "$ANCORE_UPDATE_INPUT"); then
            ancore_update_url "$ANCORE_UPDATE_INPUT"
            return
        fi
    done
}

ancore_update_url() {
    ANCORE_UPDATE_URL=${1%/}
    case "$ANCORE_UPDATE_URL" in
        https://github.com/*) ANCORE_UPDATE_PATH=${ANCORE_UPDATE_URL#https://github.com/} ;;
        git@github.com:*) ANCORE_UPDATE_PATH=${ANCORE_UPDATE_URL#git@github.com:} ;;
        *) ancore_fail 'Podaj adres repozytorium https://github.com/WŁAŚCICIEL/REPO lub git@github.com:WŁAŚCICIEL/REPO.git.' ;;
    esac
    # Accept repository links, not browser subpages, credentials or shell options.
    case "$ANCORE_UPDATE_PATH" in
        ''|*[!a-zA-Z0-9_./-]*) ancore_fail 'Nieprawidłowy link do repozytorium GitHub.' ;;
    esac
    ANCORE_UPDATE_OWNER=${ANCORE_UPDATE_PATH%%/*}
    ANCORE_UPDATE_REPO=${ANCORE_UPDATE_PATH#*/}
    ANCORE_UPDATE_REPO=${ANCORE_UPDATE_REPO%.git}
    case "$ANCORE_UPDATE_OWNER" in
        ''|[!a-zA-Z0-9]*|*[!a-zA-Z0-9-]*) ancore_fail 'Nieprawidłowy właściciel repozytorium GitHub.' ;;
    esac
    case "$ANCORE_UPDATE_REPO" in
        ''|.|..|*/*) ancore_fail 'Podaj link do repozytorium, bez /tree/ ani /blob/. Gałąź podaj jako osobny argument.' ;;
    esac
    [ "$ANCORE_UPDATE_OWNER" != "$ANCORE_UPDATE_PATH" ] || ancore_fail 'Link musi zawierać właściciela i nazwę repozytorium.'
    case "$ANCORE_UPDATE_URL" in
        https://*) ANCORE_UPDATE_URL="https://github.com/$ANCORE_UPDATE_OWNER/$ANCORE_UPDATE_REPO.git" ;;
        *) ANCORE_UPDATE_URL="git@github.com:$ANCORE_UPDATE_OWNER/$ANCORE_UPDATE_REPO.git" ;;
    esac
}

ancore_update_tree() {
    # Check the fetched tree before touching the checkout. Git ignores are not
    # enough: a remote commit could start tracking configuration or local data.
    ANCORE_UPDATE_PROTECTED=$(git ls-tree -r --name-only "$ANCORE_UPDATE_COMMIT" -- \
        .env .env.production .env.office deploy/.env deploy/.env.production \
        .local .recovery .venv venv env ENV media private_documents staticfiles \
        deploy/backups deploy/certs deploy/compose.recovery.yaml)
    [ -z "$ANCORE_UPDATE_PROTECTED" ] || ancore_fail 'Pobrana wersja śledzi konfigurację lub dane lokalne. Przerwano bez zmiany źródeł.'
    for ANCORE_UPDATE_FILE in ancore-install.sh deploy/cli/runtime.sh deploy/compose.yaml \
        deploy/Dockerfile manage.py backend/ancore/settings.py; do
        ANCORE_UPDATE_ENTRY=$(git ls-tree "$ANCORE_UPDATE_COMMIT" -- "$ANCORE_UPDATE_FILE")
        case "$ANCORE_UPDATE_ENTRY" in
            '100644 blob '*|'100755 blob '*) ;;
            *) ancore_fail "Pobrane repozytorium nie zawiera pliku Ancore: $ANCORE_UPDATE_FILE. Przerwano bez zmiany źródeł." ;;
        esac
    done
}

ancore_update_sources() {
    command -v git >/dev/null 2>&1 || ancore_fail 'Aktualizacja z GitHub wymaga programu git na serwerze.'
    ANCORE_UPDATE_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || \
        ancore_fail 'Aktualizacja z GitHub wymaga projektu pobranego przez git clone.'
    [ "$(CDPATH='' cd -- "$ANCORE_UPDATE_ROOT" && pwd -P)" = "$ANCORE_ROOT" ] || \
        ancore_fail 'Katalog Ancore musi być katalogiem głównym repozytorium Git.'
    ANCORE_UPDATE_CURRENT=$(git symbolic-ref --quiet HEAD) || \
        ancore_fail 'Repozytorium ma odłączony HEAD. Przełącz je na gałąź przed aktualizacją.'
    ANCORE_UPDATE_CURRENT=${ANCORE_UPDATE_CURRENT#refs/heads/}
    ANCORE_UPDATE_BRANCH=${1:-$ANCORE_UPDATE_CURRENT}
    case "$ANCORE_UPDATE_BRANCH" in
        -*) ancore_fail 'Nieprawidłowa nazwa gałęzi Git.' ;;
    esac
    git check-ref-format "refs/heads/$ANCORE_UPDATE_BRANCH" >/dev/null 2>&1 || \
        ancore_fail 'Nieprawidłowa nazwa gałęzi Git.'
    ANCORE_UPDATE_STATUS=$(git status --porcelain --untracked-files=normal)
    [ -z "$ANCORE_UPDATE_STATUS" ] || \
        ancore_fail 'Repozytorium zawiera lokalne zmiany lub nieśledzone pliki. Uporządkuj git status przed aktualizacją.'

    printf 'Pobieranie kodu z %s (gałąź: %s)...\n' "$ANCORE_UPDATE_URL" "$ANCORE_UPDATE_BRANCH"
    if ! git fetch --no-tags --no-recurse-submodules -- "$ANCORE_UPDATE_URL" "refs/heads/$ANCORE_UPDATE_BRANCH"; then
        ancore_fail 'Nie udało się pobrać kodu. Sprawdź link, gałąź i dostęp Git do repozytorium. Usługi nie zostały zmienione.'
    fi
    ANCORE_UPDATE_COMMIT=$(git rev-parse --verify 'FETCH_HEAD^{commit}')
    git merge-base --is-ancestor HEAD "$ANCORE_UPDATE_COMMIT" || \
        ancore_fail 'Pobrana wersja nie jest kontynuacją lokalnej historii. Aktualizacja wymaga fast-forward; źródła i usługi pozostają bez zmian.'
    ancore_update_tree
    # The installer keeps secrets private with umask 077. Source files must also
    # be readable by the container user; keep the relaxed mask in this subshell.
    if ! (umask 022; git -c core.hooksPath=/dev/null merge --ff-only --no-autostash --no-overwrite-ignore "$ANCORE_UPDATE_COMMIT"); then
        ancore_fail 'Nie udało się zastosować aktualizacji bez nadpisania lokalnych plików. Sprawdź git status; usługi nie zostały przebudowane.'
    fi
    printf 'Kod zaktualizowany do %s. Przebudowa i uruchomienie usług...\n' "$ANCORE_UPDATE_COMMIT"
    # Load the new installer and runtime, not functions from the previous version.
    # The explicit local mode resumes without fetching or prompting a second time.
    exec sh "$ANCORE_ROOT/ancore-install.sh" update --local
}
