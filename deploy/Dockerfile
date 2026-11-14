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
# Older installers checked out sources with umask 077. Normalize only image
# sources, keeping them root-owned and read-only for the runtime user.
RUN chmod -R a=rX,u+w /app \
    && mkdir -p /data/private /data/media /data/tmp /app/staticfiles \
    && chown -R ancore:ancore /data /app/staticfiles && chmod 750 /data/*
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["/bin/sh", "/app/deploy/backend/entrypoint.sh"]
CMD ["gunicorn", "--config", "/app/deploy/backend/gunicorn.conf.py", "ancore.wsgi:application"]

FROM nginx:1.30.6-alpine AS web
RUN addgroup -g 10001 ancore && addgroup nginx ancore && rm /etc/nginx/conf.d/default.conf
COPY --chmod=0644 deploy/web/nginx.conf /etc/nginx/conf.d/default.conf

FROM postgres:17-alpine AS database
COPY --chmod=0755 deploy/postgres/init.sh /docker-entrypoint-initdb.d/10-ancore.sh
