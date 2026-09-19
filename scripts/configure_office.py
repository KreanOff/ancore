"""Create isolated local configuration; never replace existing credentials."""
from pathlib import Path
import secrets

path = Path(__file__).resolve().parents[1] / '.env.office'
try:
    with path.open('x') as config:
        path.chmod(0o600)
        config.write('ONLYOFFICE_URL=http://127.0.0.1:8088\n')
        config.write('ONLYOFFICE_INTERNAL_URL=http://127.0.0.1:8088\n')
        config.write('ONLYOFFICE_ANCORE_URL=http://host.lima.internal:8000\n')
        config.write('ONLYOFFICE_JWT_SECRET=' + secrets.token_urlsafe(48) + '\n')
    print('Utworzono .env.office. Dane logowania nie są wyświetlane.')
except FileExistsError:
    print('.env.office już istnieje; zachowano obecną konfigurację.')
