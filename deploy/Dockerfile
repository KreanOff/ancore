# syntax=docker/dockerfile:1
FROM node:24.22.0-bookworm-slim AS frontend
RUN npm install --global pnpm@11.25.0
WORKDIR /build
COPY frontend/app/package.json frontend/app/pnpm-lock.yaml frontend/app/pnpm-workspace.yaml ./frontend/app/
COPY frontend/board/package.json frontend/board/pnpm-lock.yaml frontend/board/pnpm-workspace.yaml ./frontend/board/
RUN pnpm --dir frontend/app install --frozen-lockfile && pnpm --dir frontend/board install --frozen-lockfile
COPY frontend ./frontend
RUN pnpm --dir frontend/app build && pnpm --dir frontend/board build

FROM python:3.14.8-slim-bookworm AS backend
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/backend \
    DJANGO_SETTINGS_MODULE=ancore.settings TMPDIR=/data/tmp
WORKDIR /app
COPY requirements.txt ./requirements.txt
COPY deploy/backend/requirements.txt ./deploy/backend/requirements.txt
RUN pip install --no-cache-dir -r deploy/backend/requirements.txt \
    && groupadd --gid 10001 ancore && useradd --uid 10001 --gid ancore --no-create-home ancore
COPY backend ./backend
COPY manage.py ./manage.py
COPY static ./static
COPY --from=frontend /build/static/frontend ./static/frontend
COPY --from=frontend /build/static/vendor/board ./static/vendor/board
COPY deploy/backend/entrypoint.sh deploy/backend/gunicorn.conf.py ./deploy/backend/
RUN mkdir -p /data/private /data/media /data/control /data/tmp /app/staticfiles \
    && chown -R ancore:ancore /data /app/staticfiles && chmod 750 /data/*
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["/bin/sh", "/app/deploy/backend/entrypoint.sh"]
CMD ["gunicorn", "--config", "/app/deploy/backend/gunicorn.conf.py", "ancore.wsgi:application"]

FROM nginx:1.30.6-alpine AS web
RUN addgroup -g 10001 ancore && addgroup nginx ancore && rm /etc/nginx/conf.d/default.conf
COPY deploy/web/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY deploy/web/entrypoint.sh /docker-entrypoint.d/15-ancore.envsh
RUN chmod +x /docker-entrypoint.d/15-ancore.envsh
ENV NGINX_ENVSUBST_FILTER=^ANCORE_

FROM postgres:17-alpine AS database
COPY deploy/postgres/init.sh /docker-entrypoint-initdb.d/10-ancore.sh

FROM python:3.14.8-slim-bookworm AS recovery-source
WORKDIR /application
COPY backend ./backend
COPY frontend ./frontend
COPY static ./static
COPY deploy ./deploy
COPY scripts ./scripts
COPY docs ./docs
COPY README.md AGENTS.md ./
COPY manage.py requirements.txt ancore.sh restore.sh .dockerignore ./
RUN tar -czf /application.tar.gz .

FROM postgres:17-alpine AS backup
RUN apk add --no-cache python3 tzdata
COPY deploy/backup/backup.py /opt/ancore/backup.py
COPY --from=recovery-source /application.tar.gz /opt/ancore/application.tar.gz
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TZ=Europe/Warsaw
ENTRYPOINT ["python3", "/opt/ancore/backup.py"]
CMD ["schedule"]
