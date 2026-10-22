#!/bin/sh
set -eu
case "${ANCORE_TLS_MODE:-http}" in
    direct)
        test -s /etc/nginx/tls/fullchain.pem && test -s /etc/nginx/tls/privkey.pem
        export ANCORE_LISTEN='listen 443 ssl;'
        export ANCORE_TLS_SETTINGS='ssl_certificate /etc/nginx/tls/fullchain.pem; ssl_certificate_key /etc/nginx/tls/privkey.pem; ssl_protocols TLSv1.2 TLSv1.3;'
        export ANCORE_HTTP_REDIRECT="server { listen 80; server_name _; return 308 ${ANCORE_PUBLIC_URL}\$request_uri; }"
        ;;
    http|external)
        export ANCORE_LISTEN='listen 80;'
        export ANCORE_TLS_SETTINGS=''
        export ANCORE_HTTP_REDIRECT=''
        ;;
    *) echo 'Nieprawidłowy ANCORE_TLS_MODE.' >&2; exit 1 ;;
esac
