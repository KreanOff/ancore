# Host-side questions run before Docker downloads any image. POSIX sh only.

# Pregenerated from static/img/logo.png; no graphics tools are needed on the server.
# Unicode quadrants retain the mark's diagonal cuts and rounded ends.
ancore_banner_art() {
    if [ "$1" = wide ]; then
        cat <<'LOGO'
               ▗▄▄                |
             ▄█████▙▖             |
            ▟████████▖            |
           ▄▝█████████▖           |
          ▟█▙▝█████████▖          |   ▗██▌    ▐██▖   ▐█▌    ▄███▙▄     ▗▟███▙▖   ▐██████▄▖   ████████
         ▟███▙▝█████████▖         |   ▟███    ▐███   ▐█▌  ▗███▀▀██▙   ▟██▛▀▜██▖  ▐██▀▀▀▜██▖  ████████
        ▗█████▙▝█████████▖        |  ▗████▖   ▐███▙  ▐█▌  ▟█▛   ▝██▖ ▗██▘   ▝██▖ ▐██    ██▌  ██▌
       ▗███████▙▝█████████        |  ▟█▌▐█▙   ▐██▜█▌ ▐█▌ ▗██▘        ▐█▛     ██▌ ▐██    ██▌  ██▙▄▄▄▄▖
      ▗████████▛ ▝████████▌       | ▗██▘ ██▖  ▐██ ██▖▐█▌ ▐██         ▐█▌     ██▌ ▐███████▀   ███████▌
     ▗████████▛   ▝██████▘▟▙      | ▐██▄▄██▙  ▐██ ▝██▟█▌ ▝██▖    ▄▄▖ ▐█▙     ██▌ ▐██▀▀▀▜██   ██▌
    ▗████████▛     ▝███▛▘▟██▙     | ████████▖ ▐██  ▜███▌  ▜█▙   ▗██▘ ▝██▖   ▗██▘ ▐██    ██▌  ██▌
   ▗████████▛       ▝█▛▗█████▙    |▐█▛    ▜█▙ ▐██   ▜██▌  ▝███▄▄██▛   ▜██▙▄▟██▘  ▐██    ▜█▌  ████████
  ▗████████▛         ▝▄███████▙   |██▌    ▝██ ▐██    ██▌    ▀███▛▀     ▝▜███▀▘   ▐██    ▐█▙  ████████
  ▟███████▛          ▟█████████▙  |
  ███████▛         ▗▟███████████  |
  ▝▜████▀         ▗███████████▛▘  |
                 ▝▀▀▀▀▀▀▀▀▀▀▀     |
                                  |ANCORE · Instalator serwera
LOGO
    else
        cat <<'LOGO'
          ▄▄▄▖          |
        ▗█████▙         |
        ▖▜█████▙        |  ▗█▙   ▐█▌  ▐█   ▟██▙▖   ▄███▄   █████▄  ██████
       ▟█▖▜█████▙       |  ▟██   ▐██▖ ▐█  ██▀▝▜█▖ ▐█▛▘▀█▙  █▛▀▀▜█▖ ██▀▀▀▀
      ▟███▖▜█████▙      | ▗█▌█▌  ▐█▜▙ ▐█ ▐█▌   ▀▘ █▛   ▐█▌ █▌  ▐█▘ ██
     ▟█████ ██████▙     | ▐█ ▜█  ▐█▝█▙▐█ ▐█       █▌   ▐█▌ █████▛  █████▌
    ▟█████▛  █████▚▙    | █▙▄▟█▌ ▐█ ▐█▟█ ▐█▌   ▄▖ █▙   ▐█▌ █▛▀▀▜█  ██
   ▟█████▛   ▝██▛▗██▌   |▐█▀▀▀██ ▐█  ▜██  ██▄▗▟█▘ ▐█▙▖▄█▛  █▌  ▐█▌ ██▄▄▄▄
  ▟█████▛     ▝▛▟████▖  |█▛   ▐█▖▐█   ██   ▀██▛▘   ▀███▀   █▌   █▌ ██████
 ▐█████▛      ▗▟██████▖ |
 ▐████▛      ▗████████▌ |
  ▝▀▀▘       ▀▀▀▀▀▀▀▀▘  |
                        |ANCORE · Instalator serwera
LOGO
    fi
}

ancore_banner() {
    ANCORE_LOGO_COLOR=''
    ANCORE_LOGO_RESET=''
    if [ -t 1 ] && [ "${TERM:-dumb}" != dumb ] && [ -z "${NO_COLOR:-}" ]; then
        case "${COLORTERM:-}" in
            truecolor|24bit) ANCORE_LOGO_COLOR='\033[38;2;255;46;46m' ;;
            *)
                case "$TERM" in
                    *256color*) ANCORE_LOGO_COLOR='\033[38;5;196m' ;;
                    *) ANCORE_LOGO_COLOR='\033[91m' ;;
                esac ;;
        esac
        ANCORE_LOGO_RESET='\033[0m'
    fi

    ANCORE_BANNER_COLUMNS=${COLUMNS:-80}
    if [ -t 1 ]; then
        # Preserve the terminal descriptor before $() captures stdout in a pipe.
        { ANCORE_TERMINAL_SIZE=$(stty size <&3 2>/dev/null) || ANCORE_TERMINAL_SIZE=''; } 3<&1
        ANCORE_MEASURED_COLUMNS=${ANCORE_TERMINAL_SIZE##* }
        case "$ANCORE_MEASURED_COLUMNS" in
            [1-9]|[1-9][0-9]|[1-9][0-9][0-9]) ANCORE_BANNER_COLUMNS=$ANCORE_MEASURED_COLUMNS ;;
        esac
    fi
    case "$ANCORE_BANNER_COLUMNS" in
        [0-9]|[0-9][0-9]|[0-9][0-9][0-9]) ;;
        *) ANCORE_BANNER_COLUMNS=80 ;;
    esac
    ANCORE_BANNER_VARIANT=compact
    if [ "$ANCORE_BANNER_COLUMNS" -ge 106 ]; then ANCORE_BANNER_VARIANT=wide; fi

    printf '\n'
    # The word uses the terminal's foreground, readable on light and dark themes.
    ancore_banner_art "$ANCORE_BANNER_VARIANT" |
        while IFS='|' read -r ANCORE_LOGO_LINE ANCORE_WORD_LINE; do
            printf '  %b%s%b    %s\n' "$ANCORE_LOGO_COLOR" "$ANCORE_LOGO_LINE" \
                "$ANCORE_LOGO_RESET" "$ANCORE_WORD_LINE"
        done
    printf '\n'
}

ancore_setup_cleanup() {
    if [ -n "${ANCORE_TERMINAL_STATE:-}" ]; then
        stty "$ANCORE_TERMINAL_STATE" || :
        ANCORE_TERMINAL_STATE=''
        printf '\n'
    fi
    unset ANCORE_ADMIN_PASSWORD ANCORE_PASSWORD_CONFIRM ANCORE_PASSWORD_INPUT
}

ancore_answer() {
    printf '%s' "$1"
    if [ -n "$2" ]; then printf ' [%s]' "$2"; fi
    printf ': '
    IFS= read -r ANCORE_ANSWER || ancore_fail 'Przerwano instalację: brak odpowiedzi. Konfiguracja nie została zmieniona.'
    ANCORE_ANSWER=$(printf '%s' "$ANCORE_ANSWER" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
    ANCORE_ANSWER=${ANCORE_ANSWER:-$2}
}

ancore_valid_ip() {
    printf '%s\n' "$1" | LC_ALL=C awk -F. '
        NF != 4 { exit 1 }
        { for (i = 1; i <= 4; i++)
            if ($i !~ /^[0-9]+$/ || length($i) > 3 || $i > 255 || (length($i) > 1 && substr($i, 1, 1) == "0")) exit 1
          if ($0 == "0.0.0.0" || $0 == "255.255.255.255" || ($1 >= 224 && $1 <= 239)) exit 1
        }'
}

ancore_valid_port() {
    printf '%s\n' "$1" | LC_ALL=C awk '
        $0 !~ /^[0-9]+$/ || length($0) > 5 || $0 < 1 || $0 > 65535 { exit 1 }'
}

ancore_existing_admin() {
    [ -f "$ANCORE_ENV" ] || return 1
    ANCORE_PROJECT_NAME=$(ancore_config_value ANCORE_PROJECT)
    case "$ANCORE_PROJECT_NAME" in ''|*[!a-z0-9_-]*) return 1 ;; esac
    ANCORE_BACKEND_ID=$(ancore_compose ps --status running --quiet backend 2>/dev/null) || return 1
    [ -n "$ANCORE_BACKEND_ID" ] || return 1
    ancore_compose exec -T backend python manage.py ensure_admin --check-only </dev/null >/dev/null 2>&1
}

ancore_read_password() {
    printf '%s: ' "$1"
    if [ -t 0 ]; then
        ANCORE_TERMINAL_STATE=$(stty -g) || ancore_fail 'Nie można odczytać ustawień terminala.'
        stty -echo || ancore_fail 'Nie można ukryć hasła w terminalu.'
    fi
    IFS= read -r ANCORE_PASSWORD_INPUT || ancore_fail 'Przerwano instalację: brak hasła. Konfiguracja nie została zmieniona.'
    if [ -n "$ANCORE_TERMINAL_STATE" ]; then
        stty "$ANCORE_TERMINAL_STATE"
        ANCORE_TERMINAL_STATE=''
    fi
    printf '\n'
}

ancore_collect_setup() {
    # Unset inherited/exported values so credentials stay shell-local.
    unset ANCORE_ADMIN_EMAIL ANCORE_ADMIN_USERNAME ANCORE_ADMIN_FIRST_NAME ANCORE_ADMIN_LAST_NAME
    unset ANCORE_ADMIN_PASSWORD ANCORE_PASSWORD_CONFIRM ANCORE_PASSWORD_INPUT
    ANCORE_TERMINAL_STATE=''
    trap 'ancore_setup_cleanup' 0
    trap 'exit 130' INT
    trap 'exit 143' TERM
    trap 'exit 129' HUP
    ANCORE_ORIGINAL_ENV=$ANCORE_ENV
    if [ ! -f "$ANCORE_ENV" ] && [ -f "$ANCORE_ROOT/deploy/.env.production" ]; then
        ANCORE_ENV="$ANCORE_ROOT/deploy/.env.production"
    fi
    ANCORE_DEFAULT_HOST=''
    ANCORE_DEFAULT_PORT=8080
    if [ -f "$ANCORE_ENV" ]; then
        ANCORE_DEFAULT_HOST=$(ancore_config_value ANCORE_HOST)
        ANCORE_DEFAULT_PORT=$(ancore_config_value ANCORE_HTTP_PORT)
        ancore_valid_ip "$ANCORE_DEFAULT_HOST" || ANCORE_DEFAULT_HOST=''
        ancore_valid_port "$ANCORE_DEFAULT_PORT" || ANCORE_DEFAULT_PORT=8080
    fi
    while :; do
        ancore_answer 'Adres IP serwera' "$ANCORE_DEFAULT_HOST"
        if ancore_valid_ip "$ANCORE_ANSWER"; then break; fi
        printf 'Podaj adres IPv4 serwera, np. 192.168.1.10, bez http:// i portu.\n'
    done
    ANCORE_INPUT_HOST=$ANCORE_ANSWER
    while :; do
        ancore_answer 'Port HTTP' "$ANCORE_DEFAULT_PORT"
        if ancore_valid_port "$ANCORE_ANSWER"; then break; fi
        printf 'Podaj port od 1 do 65535.\n'
    done
    ANCORE_INPUT_PORT=$ANCORE_ANSWER
    ANCORE_SKIP_ADMIN=0
    if ancore_existing_admin; then
        ANCORE_SKIP_ADMIN=1
        printf 'Administrator już istnieje. Zachowano jego konto i hasło.\n'
    fi
    ANCORE_ENV=$ANCORE_ORIGINAL_ENV
    if [ "$ANCORE_SKIP_ADMIN" = 1 ]; then return; fi

    printf '\nKonto administratora (do logowania służy adres e-mail).\n'
    while :; do
        ancore_answer 'E-mail administratora' ''
        case "$ANCORE_ANSWER" in
            *' '*|*'@'|@*) ;;
            *@*.*) ANCORE_ADMIN_EMAIL=$ANCORE_ANSWER; break ;;
        esac
        printf 'Podaj prawidłowy adres e-mail.\n'
    done
    while :; do
        ancore_answer 'Nazwa administratora' 'admin'
        case "$ANCORE_ANSWER" in
            *[![:alnum:]@.+_-]*) printf 'Użyj liter, cyfr lub znaków @ . + - _.\n'; continue ;;
        esac
        if [ "${#ANCORE_ANSWER}" -le 150 ]; then ANCORE_ADMIN_USERNAME=$ANCORE_ANSWER; break; fi
        printf 'Nazwa może mieć najwyżej 150 znaków.\n'
    done
    while :; do
        ancore_answer 'Imię administratora' ''
        if [ -n "$ANCORE_ANSWER" ] && [ "${#ANCORE_ANSWER}" -le 150 ]; then ANCORE_ADMIN_FIRST_NAME=$ANCORE_ANSWER; break; fi
        printf 'Podaj imię (do 150 znaków).\n'
    done
    while :; do
        ancore_answer 'Nazwisko administratora' ''
        if [ -n "$ANCORE_ANSWER" ] && [ "${#ANCORE_ANSWER}" -le 150 ]; then ANCORE_ADMIN_LAST_NAME=$ANCORE_ANSWER; break; fi
        printf 'Podaj nazwisko (do 150 znaków).\n'
    done
    printf 'Hasło: co najmniej 8 znaków; nie może być popularne ani podobne do danych konta.\n'
    while :; do
        ancore_read_password 'Hasło administratora'
        ANCORE_ADMIN_PASSWORD=$ANCORE_PASSWORD_INPUT
        unset ANCORE_PASSWORD_INPUT
        if [ "${#ANCORE_ADMIN_PASSWORD}" -lt 8 ]; then
            printf 'Hasło musi mieć co najmniej 8 znaków.\n'
            continue
        fi
        case "$ANCORE_ADMIN_PASSWORD" in
            *[!0-9]*) ;;
            *) printf 'Hasło nie może składać się wyłącznie z cyfr.\n'; continue ;;
        esac
        ancore_read_password 'Powtórz hasło'
        ANCORE_PASSWORD_CONFIRM=$ANCORE_PASSWORD_INPUT
        unset ANCORE_PASSWORD_INPUT
        if [ "$ANCORE_ADMIN_PASSWORD" = "$ANCORE_PASSWORD_CONFIRM" ]; then break; fi
        printf 'Hasła nie są takie same. Wpisz je ponownie.\n'
    done
    unset ANCORE_PASSWORD_CONFIRM
}

ancore_finish_admin() {
    if [ "$ANCORE_SKIP_ADMIN" = 1 ]; then
        ancore_compose exec -T backend python manage.py ensure_admin --check-only
    else
        printf '%s\n' "$ANCORE_ADMIN_EMAIL" "$ANCORE_ADMIN_USERNAME" \
            "$ANCORE_ADMIN_FIRST_NAME" "$ANCORE_ADMIN_LAST_NAME" "$ANCORE_ADMIN_PASSWORD" |
            ancore_compose exec -T backend python manage.py ensure_admin --from-stdin
    fi
}
