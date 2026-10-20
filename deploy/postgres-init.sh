#!/bin/sh
set -eu
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1 \
    --set=app_password="$ANCORE_DB_PASSWORD" <<'SQL'
CREATE ROLE ancore LOGIN PASSWORD :'app_password';
ALTER DATABASE ancore OWNER TO ancore;
GRANT USAGE, CREATE ON SCHEMA public TO ancore;
SQL
