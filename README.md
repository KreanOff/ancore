<p align="center">
  <img src="static/img/logo.png" alt="Logo Ancore" width="112" height="112">
</p>

<h1 align="center">Ancore</h1>

<p align="center">
  <strong>Zadania, dokumenty i codzienna praca zespołu.</strong><br>
  Aplikacja z polskim interfejsem, uruchamiana na własnym serwerze.
</p>

<p align="center">
  Django · React · TypeScript · PostgreSQL · ONLYOFFICE
</p>

<p align="center">
  <a href="#instalacja-na-serwerze">Instalacja</a> ·
  <a href="#codzienna-obsługa">Polecenia</a> ·
  <a href="#rozwój-lokalny">Dla developerów</a> ·
  <a href="docs/README.md">Dokumentacja</a>
</p>

---

## Praca zespołu w jednym miejscu

Ancore łączy organizację pracy w Workspace z Przestrzeniami, zadaniami,
kalendarzem i dokumentami. Dostęp do wspólnych danych wynika z członkostwa
oraz uprawnień użytkownika.

| Obszar | Możliwości |
| --- | --- |
| **Workspace i zespoły** | Wspólna przestrzeń pracy, członkowie i role dostępu. |
| **Przestrzenie i zadania** | Zadania, podzadania, sprinty, backlog, tablica i rejestrowanie czasu pracy. |
| **Pulpity i filtry** | Konfigurowalne pulpity, gadżety i zapisane filtry zadań. |
| **Kalendarz** | Wydarzenia i terminy zadań. |
| **Dysk i Dokumenty** | Pliki, foldery, dokumenty biurowe w ONLYOFFICE i tablice Excalidraw. |
| **Zasoby** | Ewidencja sprzętu, licencji i narzędzi, przekazania, zwroty i historia. |

[Poznaj moduły aplikacji →](docs/MODULES.md)

## Instalacja na serwerze

**Logo ANCORE → IP → port HTTP → dane administratora → instalacja.**

Potrzebujesz serwera Linux z **Docker Engine i Docker Compose**, źródeł projektu
oraz internetu do pobrania obrazów i zależności. Użytkownik uruchamiający skrypt
musi mieć dostęp do Dockera i możliwość zapisu w katalogu projektu.
Instalator korzysta z lokalnego Dockera i wymaga obsługi `up --wait --wait-timeout`.
Python, Node i baza danych działają w kontenerach.

W terminalu serwera przejdź do katalogu Ancore:

```sh
cd ancore
sh ancore-install.sh
```

Możesz także uruchomić `./ancore-install.sh`. Polecenia `install` i `setup`
uruchamiają ten sam proces. Na początku zobaczysz terminalowe logo i napis
**ANCORE**. Wszystkie pytania pojawiają się przed pobieraniem obrazów
i budowaniem aplikacji.

1. **Podaj IPv4 serwera**, np. `192.168.1.20`, bez protokołu i portu.
2. **Podaj port HTTP** — Enter wybiera `8080`.
3. **Podaj dane administratora Django.** Podaj e-mail do logowania, nazwę
   użytkownika (domyślnie `admin`), imię, nazwisko i dwukrotnie hasło.
   Podczas wpisywania hasła w terminalu znaki są ukryte.
4. **Poczekaj na instalację.** Instalator wygeneruje sekrety, zbuduje obrazy
   i oba frontendy, wykona migracje, sprawdzi gotowość usług i utworzy konto.
5. **Otwórz pokazany adres i zaloguj się utworzonym kontem.** Dla powyższego
   przykładu będzie to `http://192.168.1.20:8080`.

Przy ponownej instalacji działający backend pozwala sprawdzić, czy aktywny
administrator z hasłem już istnieje, i pominąć pytania o konto. Jeśli backend
jest zatrzymany lub nie obsługuje jeszcze tego sprawdzenia, instalator zbierze
dane na początku, ale zachowa istniejące konto i hasło. Hasło nie trafia do
konfiguracji ani argumentów polecenia. Jeśli usługi już działają, a utworzenie
konta się nie powiodło, możesz ponowić ten etap przez `sh ancore-install.sh admin`.

Instalator nie instaluje Dockera ani nie zmienia zapory. Wybrany port musi być
dostępny z urządzeń, na których otwierasz aplikację.

[Pełna instrukcja instalacji →](docs/PRODUCTION.md)

### Cztery kontenery, jeden publiczny port

| Kontener | Odpowiedzialność | Dostęp |
| --- | --- | --- |
| `web` | Nginx, zasoby statyczne i proxy aplikacji oraz edytora | Wybrany port HTTP |
| `backend` | Django, Gunicorn, API i kontrolowane pobieranie plików | Wewnętrzna sieć Docker |
| `postgres` | Baza danych PostgreSQL | Wewnętrzna sieć Docker |
| `onlyoffice` | Edytor dokumentów biurowych | Przez `web`, pod `/onlyoffice/` |

**Instalacja działa przez HTTP, bez HTTPS i bez systemu backupu.** Baza oraz
pliki są przechowywane w trwałych wolumenach Docker.

## Codzienna obsługa

Wszystkie polecenia uruchamiaj w katalogu projektu:

| Polecenie | Działanie |
| --- | --- |
| `sh ancore-install.sh` | Instalacja lub zmiana IP i portu |
| `sh ancore-install.sh status` | Stan czterech usług |
| `sh ancore-install.sh logs` | Logi wszystkich usług |
| `sh ancore-install.sh logs backend` | Logi wybranej usługi; także `web`, `postgres` lub `onlyoffice` |
| `sh ancore-install.sh stop` | Zatrzymanie kontenerów z zachowaniem danych |
| `sh ancore-install.sh start` | Uruchomienie wcześniej zbudowanej aplikacji |
| `sh ancore-install.sh restart` | Ponowny start usług |
| `sh ancore-install.sh update` | Przebudowa i start z aktualnych źródeł |
| `sh ancore-install.sh admin` | Utworzenie kolejnego administratora Django |
| `sh ancore-install.sh --help` | Pomoc instalatora |

Z podglądu logów wychodzisz przez **Ctrl+C**; usługi nadal działają.
`start`, `restart` i `update` nie pytają o administratora.

### Aktualizacja i dane

Przed `update` pobierz lub skopiuj nowy kod do katalogu projektu. Polecenie
przebudowuje lokalne źródła; nie pobiera zmian z Git.

- **Konfiguracja:** `deploy/.env` zawiera losowe sekrety instalacji i ma uprawnienia
  `0600`. Hasło administratora Django nie jest w nim zapisywane.
- **Ponowna instalacja:** zachowuje sekrety, nazwę projektu Compose, konta
  i wolumeny. Pozwala zmienić IP lub port.
- **Dane:** `stop` nie usuwa bazy ani plików. `docker compose down --volumes`
  usuwa wolumeny — nie używaj tego polecenia, jeśli chcesz zachować dane.

## Rozwój lokalny

Frontend głównej aplikacji znajduje się w `frontend/app`, a backend Django
w `backend/`. Lokalny development korzysta z `.env` w katalogu głównym;
konfiguracja serwerowa jest oddzielona w `deploy/.env`.

<details>
<summary><strong>Przygotowanie środowiska i uruchomienie aplikacji</strong></summary>

Lokalna konfiguracja projektu wskazuje Python **3.15.0**, Django **6.1.2**,
PostgreSQL **15+**, Node.js **22+** i pnpm **11**. Wersje kontenerów są określone
osobno w [Dockerfile](deploy/Dockerfile). Zgodność i ograniczenia lokalnego
Pythona opisuje [instrukcja developerska](docs/DEVELOPMENT.md#aktualizacja-do-pythona-315-17102026).

Przygotuj własną bazę PostgreSQL. Jeśli nie masz `.env`, skopiuj
[.env.example](.env.example) i uzupełnij parametry połączenia. Pierwsze
uruchomienie nowego schematu wymaga pustej bazy; starsze schematy sprzed resetu
nie są automatycznie migrowane. [Zasady bazy danych](docs/DATABASE.md).

```sh
python3.15 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

pnpm --dir frontend/app install --frozen-lockfile
pnpm --dir frontend/app build

.venv/bin/python manage.py check
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Pełne edytory wymagają również buildu `frontend/board` i serwera ONLYOFFICE.
Sposób konfiguracji opisuje [instrukcja Dokumentów](docs/OFFICE.md).

`manage.py` ustawia ścieżkę do `backend/`. Dla bezpośrednio uruchamianych
procesów WSGI/ASGI ustaw `PYTHONPATH` na ten katalog; wejścia pozostają
`ancore.wsgi:application` i `ancore.asgi:application`.

</details>

<details>
<summary><strong>Sprawdzanie zmian</strong></summary>

```sh
.venv/bin/python manage.py check
.venv/bin/python scripts/update_code_index.py --check
pnpm --dir frontend/app test
pnpm --dir frontend/app build
```

Testy backendu dobieraj do zmienianego modułu. Przykład z osobną bazą testową
i tymczasowym storage:

```sh
.venv/bin/python scripts/run_tests.py spaces.test_navigation
```

Regresje instalatora i tworzenia administratora:

```sh
.venv/bin/python manage.py test core.test_production_installer core.test_production core.test_project_layout
.venv/bin/python scripts/run_tests.py accounts.test_ensure_admin
```

Zakres sprawdzeń i wymagania środowiska: [Praca developerska](docs/DEVELOPMENT.md).

</details>

## Mapa projektu

```text
ancore/
├── backend/           Django: konfiguracja, moduły, migracje i testy
├── frontend/
│   ├── app/           Główna aplikacja React / TypeScript
│   └── board/         Edytor tablicy Excalidraw
├── static/            Wspólne style, skrypty, logo i biblioteki
├── deploy/            Obrazy, Compose, proxy i konfigurator instalacji
├── scripts/           Narzędzia developerskie i utrzymanie dokumentacji
├── docs/              Dokumentacja projektu
├── ancore-install.sh  Instalacja i obsługa serwera
├── manage.py          Polecenia Django
└── requirements.txt   Zależności backendu
```

Konfiguracja z sekretami, pliki użytkowników, środowiska i wygenerowane bundle
pozostają poza Git oraz kontekstem budowania Dockera.
[Zasady organizacji repozytorium →](docs/REPOSITORY.md)

## Dokumentacja

| Chcesz… | Przejdź do |
| --- | --- |
| Uruchomić Ancore na serwerze | [Instalacja i obsługa](docs/PRODUCTION.md) |
| Poznać funkcje aplikacji | [Moduły](docs/MODULES.md) |
| Zrozumieć Workspace i uprawnienia | [Praca zespołowa](docs/TEAMWORK.md) |
| Pracować z Przestrzeniami i zadaniami | [Przestrzenie](docs/SPACES.md) |
| Skonfigurować edytory dokumentów | [ONLYOFFICE i tablice](docs/OFFICE.md) |
| Rozwijać aplikację | [Architektura](docs/ARCHITECTURE.md) · [Frontend](docs/FRONTEND.md) · [Standard UI](docs/UI.md) |
| Znaleźć właściwy plik lub mechanizm | [Mapa dokumentacji](docs/README.md) · [Indeks kodu](docs/CODE_INDEX.md) |

---

<p align="center">
  <strong>Ancore</strong><br>
  Praca zespołu na Twoim serwerze.
</p>
