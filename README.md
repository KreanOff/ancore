# Ancore

Nowe migracje początkowe wymagają pustej bazy PostgreSQL.
[Zakres resetu i uruchomienie](docs/DATABASE.md).

Aplikacja do pracy zespołowej: Workspace, Przestrzenie i zadania, kalendarz,
pulpity, zasoby oraz Dysk i Dokumenty. Backend korzysta z Django i PostgreSQL,
a interfejs z Reacta i TypeScriptu.

## Instalacja na serwerze (Docker)

Instalacja produkcyjna z konfiguracją w terminalu, pięcioma usługami Docker
Compose, lokalnymi wolumenami i backupami: [Produkcja](docs/PRODUCTION.md).
Po zainstalowaniu Dockera z Compose pobierz lub skopiuj projekt na serwer:

```sh
cd ancore
./ancore.sh setup
```

Konfigurator pyta o IP/domenę, port, HTTP/HTTPS, dostęp z sieci i katalog
backupów. Generuje `deploy/.env` z losowymi sekretami i proponuje lokalne
budowanie oraz uruchomienie. Domyślny adres to `http://IP_SERWERA:8080`;
nasłuch `0.0.0.0` pozwala na połączenia z innych urządzeń, jeśli przepuszcza je
sieć i zapora. Python, Node, Nginx i PostgreSQL działają w kontenerach.
Pierwszy build pobiera obrazy bazowe i zależności z internetu; aplikacja, baza,
pliki, ONLYOFFICE i nieszyfrowane backupy pozostają na tym serwerze.
Do instalacji bez pytań służy `./ancore.sh install`, a do zapisania samych
ustawień `./ancore.sh configure`.

```sh
./ancore.sh start
./ancore.sh status
./ancore.sh logs
./ancore.sh stop
```

Polecenie `start` uruchamia już zbudowaną aplikację bez pobierania obrazów.
Aktualny kod przebudujesz przez `./ancore.sh update`; polecenie wymaga istniejącej
konfiguracji i wykonuje backup działającej instalacji. Backup, odtwarzanie,
przeładowanie Nginx i diagnostykę obsługuje to samo polecenie;
listę operacji pokazuje `./ancore.sh --help`.

## Struktura projektu

```text
backend/           konfiguracja Django i aplikacje domenowe z testami i szablonami
frontend/app/      interfejs React i TypeScript
frontend/board/    odizolowany edytor tablicy Excalidraw
static/            wspólne style, skrypty, obrazy i lokalne biblioteki
deploy/            produkcyjny Docker Compose: WWW, Django, PostgreSQL, backup, ONLYOFFICE
ancore.sh          wspólne polecenia instalacji i utrzymania produkcji
scripts/           narzędzia do budowania i utrzymania projektu
docs/              dokumentacja i generowany indeks kodu
manage.py          główne wejście do poleceń Django
requirements.txt   zależności Pythona
.env.example       przykład lokalnej konfiguracji bez sekretów
AGENTS.md          zasady pracy nad projektem
```

`.venv/`, `node_modules/`, `.env`, `.env.office`, `media/`,
`private_documents/` oraz generowane bundle są lokalne i pomijane przez Git.
Wspólne ustawienia VS Code ukrywają zależności, cache i pliki danych w Explorerze.
Pliki nadal istnieją na dysku; reguły widoczności można zmienić w
[ustawieniach edytora](.vscode/settings.json).

## Uruchomienie lokalne

Projekt jest skonfigurowany dla Pythona **3.15.0**. Pozostałe wymagania to Django 6.1.2,
PostgreSQL 15+, Node.js 22+ i pnpm 11. Komendy wykonuj w katalogu głównym
repozytorium. Przed utworzeniem środowiska sprawdź, czy `python3.15 --version`
wskazuje wybraną wersję.
Django 6.1 deklaruje oficjalne wsparcie dla Pythona 3.12–3.14; stan weryfikacji
na 3.15 i ograniczenia opisuje [instrukcja developerska](docs/DEVELOPMENT.md#aktualizacja-do-pythona-315-17102026).

1. Utwórz własną bazę PostgreSQL. Jeśli nie masz `.env`, skopiuj
   [.env.example](.env.example) do `.env` i uzupełnij dane połączenia.
2. Przygotuj zależności i zbuduj frontend:

   ```sh
   python3.15 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   pnpm --dir frontend/app install --frozen-lockfile
   pnpm --dir frontend/app build
   ```

3. Sprawdź konfigurację, zastosuj migracje i uruchom aplikację:

   ```sh
   .venv/bin/python manage.py check
   .venv/bin/python manage.py migrate
   .venv/bin/python manage.py runserver 127.0.0.1:8000
   ```

Jeżeli `.venv` już istnieje, sprawdź `.venv/bin/python --version`.
Zmianę interpretera opisuje [instrukcja developerska](docs/DEVELOPMENT.md#3-start-nowego-środowiska).
Pełne edytory Dokumentów wymagają osobnego buildu tablicy i ONLYOFFICE;
instrukcja znajduje się w [OFFICE.md](docs/OFFICE.md).

## Sprawdzanie zmian

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py test
.venv/bin/python scripts/update_code_index.py --check
pnpm --dir frontend/app build
```

Testy Django wymagające bazy tworzą osobną bazę testową. Dobieraj zakres
zgodnie z [instrukcją developerską](docs/DEVELOPMENT.md). Można wskazać moduł, np.
`manage.py test spaces.test_navigation`.

## Dokumentacja i wdrażanie

Zacznij od [mapy dokumentacji](docs/README.md),
[architektury](docs/ARCHITECTURE.md) i [indeksu kodu](docs/CODE_INDEX.md).
Zasady interfejsu opisują [UI](docs/UI.md) i [frontend React](docs/FRONTEND.md).

`manage.py` dodaje `backend/` do ścieżki importów. Inne procesy Pythona,
w tym serwer WSGI/ASGI, muszą otrzymać tę ścieżkę, np. przez
`PYTHONPATH=/ścieżka/do/ancore/backend`. Nazwy wejść pozostają
`ancore.wsgi:application` i `ancore.asgi:application`.
Konfiguracja `.env`, zasoby i pliki użytkowników są rozwiązywane względem
katalogu głównego repozytorium, niezależnie od katalogu roboczego procesu.
