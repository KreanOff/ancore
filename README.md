# Ancore

Aplikacja do pracy zespołowej: Workspace, Przestrzenie i zadania, kalendarz,
pulpity, zasoby oraz Dysk i Dokumenty. Backend korzysta z Django i PostgreSQL,
a interfejs z Reacta i TypeScriptu.

## Struktura projektu

```text
backend/           konfiguracja Django i aplikacje domenowe z testami i szablonami
frontend/app/      interfejs React i TypeScript
frontend/board/    odizolowany edytor tablicy Excalidraw
static/            wspólne style, skrypty, obrazy i lokalne biblioteki
deploy/            konfiguracja usług pomocniczych (ONLYOFFICE)
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

Wymagane są Python zgodny z zainstalowanym Django, PostgreSQL, Node.js 22+
i pnpm 11. Komendy wykonuj w katalogu głównym repozytorium.

1. Utwórz własną bazę PostgreSQL. Jeśli nie masz `.env`, skopiuj
   [.env.example](.env.example) do `.env` i uzupełnij dane połączenia.
2. Przygotuj zależności i zbuduj frontend:

   ```sh
   python3 -m venv .venv
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

Jeżeli `.venv` już istnieje, korzystaj z obecnego środowiska.
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
zgodnie z [instrukcją developerską](docs/DEVELOPMENT.md); część historycznych
testów opisuje wycofane moduły. Można nadal wskazać moduł, np.
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
