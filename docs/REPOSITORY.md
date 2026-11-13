# Organizacja plików i katalogów

Repozytorium rozdziela kod aplikacji, narzędzia, wdrożenie oraz lokalne dane.
Punkty wejścia pozostają w katalogu głównym, a implementacje trafiają do
katalogu odpowiadającego ich zastosowaniu.

## Mapa projektu

```text
ancore/
├── backend/                 Django: konfiguracja i aplikacje domenowe
│   ├── ancore/              settings, routing, WSGI/ASGI, test runner
│   └── <aplikacja>/         modele, widoki, formularze, szablony, testy, migracje
├── frontend/
│   ├── app/                 React/TypeScript głównej aplikacji
│   └── board/               izolowany edytor tablicy
├── static/                  wspólne CSS, JS, obrazy, biblioteki i licencje
├── deploy/
│   ├── cli/                 instalacja, konfigurator i operacje Compose
│   ├── backend/             entrypoint Django, Gunicorn, zależności produkcji
│   ├── web/                 stała konfiguracja HTTP Nginx
│   ├── postgres/            inicjalizacja roli aplikacji w bazie
│   ├── Dockerfile           wspólny build obrazów usług i obu frontendów
│   ├── compose.yaml         cztery usługi HTTP
│   └── production.env.example
├── scripts/
│   ├── assets/              generator ikon i jego mapowanie
│   ├── office/              lokalna konfiguracja i start ONLYOFFICE
│   ├── run_tests.py         testy z osobną bazą i tymczasowym storage
│   ├── update_code_index.py generator indeksu dokumentacji
│   └── start_office.sh      zgodność starszego polecenia ONLYOFFICE
├── docs/                    dokumentacja i generowany CODE_INDEX.md
├── .vscode/settings.json    wspólne ustawienia edytora
├── .env.example             przykład konfiguracji lokalnej
├── .editorconfig            format plików
├── .gitignore               wykluczenia z repozytorium
├── .dockerignore            wykluczenia z kontekstu budowania
├── AGENTS.md                zasady pracy nad projektem
├── README.md                start i mapa dokumentacji
├── ancore-install.sh        publiczne polecenia produkcji
├── manage.py                publiczne polecenia Django
└── requirements.txt         wspólne zależności Pythona
```

`backend/` jest katalogiem źródeł Pythona; importy używają nadal nazw
`spaces`, `accounts` i `ancore.settings`, bez prefiksu `backend`.
`static/` zawiera wspólne zasoby Django, niezależnie od pakietów Reacta.
Szablony, testy i migracje pozostają przy swoich aplikacjach.

## Źródła, wyniki budowania i dane lokalne

| Rodzaj | Lokalizacja | Przechowywanie |
| --- | --- | --- |
| Kod, migracje, szablony, CSS/JS, obrazy, biblioteki i licencje | `backend/`, `frontend/`, `static/` | W Git, poza wynikami budowania i zależnościami |
| Przykłady konfiguracji | `.env.example`, `deploy/production.env.example` | W Git, bez sekretów |
| Indeks kodu | `docs/CODE_INDEX.md` | W Git; aktualizowany generatorem |
| Bundle Reacta i manifest | `static/frontend/` | Generowane; poza Git i kontekstem Dockera |
| Bundle tablicy | `static/vendor/board/` | Generowany; poza Git i kontekstem Dockera |
| Wynik `collectstatic` | `staticfiles/` lub `STATIC_ROOT` | Generowany; poza Git |
| Bieżące środowisko i zależności | `.venv/`, `node_modules/` | Lokalne; odtwarzane z zależności i lockfile |
| Cache narzędzi | `.cache/`, `__pycache__/` | Lokalne pliki odtwarzalne |
| Konfiguracja z sekretami | `.env`, `.env.office`, `deploy/.env` | Prywatne pliki lokalne; nie nadpisywać przy porządkowaniu |
| Uploady | `media/`, `private_documents/` lub skonfigurowane ścieżki | Trwałe dane; w produkcji zapisane w wolumenach |
| Archiwa i certyfikaty starszych instalacji | `deploy/backups/`, `deploy/certs/` | Prywatne dane poza Git/buildem; nowy instalator ich nie tworzy |
| Pozostałości starszego odzyskiwania | `.recovery/`, `deploy/compose.recovery.yaml` | Prywatne dane poza Git/buildem; nie usuwać przy porządkowaniu |

Lokalne zależności, cache, archiwa, konfiguracja z sekretami i dane aplikacji
są wyłączone z Git oraz kontekstu Dockera. Build sam tworzy oba bundle.
`.local/` służy zachowanym plikom pomocniczym; `.cache/` plikom odtwarzalnym.
Nieużywaną kopię poprzedniego środowiska Python (`venv.bak/`, następnie
`.local/venv-backups/`) usunięto 22.10.2026 na polecenie użytkownika.
Bieżące środowisko aplikacji znajduje się w `.venv/`. Puste katalogi `.local/`
i `.cache/` również usunięto; nie są wymagane do uruchomienia aplikacji.

Explorer VS Code ukrywa cache, archiwa lokalne, zależności, uploady i bundle.
Pliki nadal są na dysku; widoczność reguluje
[settings.json](../.vscode/settings.json). Konfiguracja i przykłady pozostają widoczne.

## Zasady dalszego porządkowania

1. Aplikacje Django dodawaj do `backend/`, moduły Reacta do istniejącego
   `frontend/app/src/`, a wspólne zasoby do `static/`.
2. Pliki kontenera umieszczaj w odpowiednim podkatalogu `deploy/`.
   Instalacja ma jedną implementację w `deploy/cli/` i wejście `ancore-install.sh`.
3. Narzędzia integracji i zasobów umieszczaj w podkatalogach `scripts/`.
   Rozwiązuj ścieżki względem pliku skryptu, aby działał również spoza repozytorium.
4. Nie twórz katalogów `old/`, `misc/`, `temp/` ani kopii `plik_final_2`.
   Historię źródeł przechowuje Git; potrzebne lokalne archiwa mają opisane
   przeznaczenie pod `.local/`.
5. Przy zmianie ścieżki aktualizuj odbiorców, build, testy i dokumentację.
   Odświeżaj indeks przez `python scripts/update_code_index.py`.

Szczegóły: [Architektura](ARCHITECTURE.md), [Praca developerska](DEVELOPMENT.md),
[Produkcja](PRODUCTION.md), [Frontend React](FRONTEND.md).
