#!/usr/bin/env python3
"""Ask for the server IPv4 and HTTP port; keep all other settings automatic."""
import ipaddress
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile


DEPLOY = Path(__file__).resolve().parents[1]
SECRET_KEYS = ('SECRET_KEY', 'POSTGRES_PASSWORD', 'POSTGRES_ADMIN_PASSWORD', 'ONLYOFFICE_JWT_SECRET')


def read_config(path):
    values = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition('=')
        if not separator or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key) or key in values:
            raise ValueError('Nieprawidłowy plik deploy/.env.')
        if len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1]
        if any(char in value for char in "\r\n'\x00"):
            raise ValueError('Konfiguracja zawiera niedozwolony znak.')
        values[key] = value
    return values


def server_ip(value):
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as error:
        raise ValueError('Podaj adres IPv4, np. 192.168.1.10, bez http:// i portu.') from error
    if address.is_unspecified or address.is_multicast or str(address) == '255.255.255.255':
        raise ValueError('Podaj adres IPv4 serwera, np. 192.168.1.10.')
    return str(address)


def http_port(value):
    if not re.fullmatch(r'[0-9]{1,5}', value) or not 1 <= int(value) <= 65535:
        raise ValueError('Podaj port od 1 do 65535.')
    return str(int(value))


def ask(label, default, validate):
    while True:
        try:
            value = input(f'{label}' + (f' [{default}]' if default else '') + ': ').strip()
        except EOFError as error:
            raise ValueError('Przerwano instalację: brak odpowiedzi. Konfiguracja nie została zmieniona.') from error
        try:
            return validate(value or default)
        except ValueError as error:
            print(error, flush=True)


def write_config(path, config):
    content = '# Ancore — HTTP, cztery kontenery. Plik zawiera prywatne sekrety.\n'
    content += ''.join(f"{key}='{value}'\n" for key, value in config.items())
    descriptor, temporary = tempfile.mkstemp(prefix='.env.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def configure():
    path = DEPLOY / '.env'
    previous = path if path.exists() else DEPLOY / '.env.production'
    existing = read_config(previous) if previous.exists() else {}
    if previous.exists() and any(not existing.get(key) for key in (*SECRET_KEYS, 'ANCORE_PROJECT')):
        raise ValueError('Istniejąca konfiguracja jest niepełna. Zachowano plik; uzupełnij brakujące sekrety i ANCORE_PROJECT.')
    project = existing.get('ANCORE_PROJECT', 'ancore-prod')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', project):
        raise ValueError('Nieprawidłowa nazwa projektu w deploy/.env.')
    default_ip = existing.get('ANCORE_HOST', '')
    try:
        default_ip = server_ip(default_ip)
    except ValueError:
        default_ip = ''
    host = ask('Adres IP serwera', default_ip, server_ip)
    port = ask('Port HTTP', existing.get('ANCORE_HTTP_PORT', '8080'), http_port)
    config = {
        'ANCORE_PROJECT': project,
        'ANCORE_HOST': host,
        'ANCORE_PUBLIC_URL': f'http://{host}:{port}',
        'ANCORE_HTTP_PORT': port,
    }
    for key in SECRET_KEYS:
        config[key] = existing.get(key) or secrets.token_hex(48)
    config['ANCORE_RELEASE'] = existing.get('ANCORE_RELEASE', 'local')
    config['ONLYOFFICE_IMAGE'] = existing.get('ONLYOFFICE_IMAGE', 'onlyoffice/documentserver:10.0.0.1')
    for key in ('WEB_WORKERS', 'WEB_THREADS'):
        if key in existing:
            config[key] = existing[key]
    write_config(path, config)
    print('Zapisano deploy/.env.', flush=True)


if __name__ == '__main__':
    try:
        if len(sys.argv) != 1:
            raise ValueError('Uruchom instalację przez sh ancore-install.sh, bez dodatkowych opcji.')
        configure()
    except (OSError, ValueError, KeyboardInterrupt) as error:
        sys.exit(f'Błąd: {error or "Przerwano instalację."}')
