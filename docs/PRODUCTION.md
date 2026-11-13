# Instalacja na serwerze

Ancore działa przez HTTP na jednym serwerze Linux. Instalator wyświetla
poziomy baner: czerwone terminalowe logo po lewej i duży napis **ANCORE** po
prawej. Znak odwzorowuje `static/img/logo.png` za pomocą znaków ćwierćblokowych
Unicode, a napis ma pełne litery bez obrysów. Terminal od 106 kolumn pokazuje
większy wariant, a mniejszy baner mieści się w 78 kolumnach. Rozmiar jest
odczytywany przez `stty size`, z wartością zapasową `COLUMNS` lub 80.
Napis używa domyślnego koloru terminala; logo korzysta z RGB, palety 256 kolorów
lub jasnej czerwieni ANSI odpowiednio do zgłaszanych możliwości terminala.
`NO_COLOR` i `TERM=dumb` wyłączają kolory. Baner jest zapisany w skrypcie i nie
wymaga programu graficznego na serwerze. Następnie instalator pyta o **adres IPv4 serwera**,
**port HTTP** i **dane administratora Django**. Dopiero po zebraniu odpowiedzi
pobiera potrzebne obrazy, generuje konfigurację, buduje aplikację
i uruchamia dokładnie cztery kontenery:

| Kontener | Rola |
| --- | --- |
| `web` | Nginx: HTTP, zasoby aplikacji i proxy ONLYOFFICE |
| `backend` | Django/Gunicorn: aplikacja, API i kontrolowane pobieranie plików |
| `postgres` | PostgreSQL 17: baza danych |
| `onlyoffice` | Edytor dokumentów |

Instalacja nie zawiera backupu, harmonogramu kopii, odtwarzania ani konfiguracji
HTTPS. Baza i pliki pozostają w trwałych wolumenach Docker.

## Wymagania

- Serwer Linux z lokalnym Docker Engine i Docker Compose obsługującym
  `up --wait --wait-timeout` (polecenie `docker compose` lub `docker-compose`).
- Dostęp użytkownika do Dockera i zapisu w katalogu projektu.
- Źródła projektu na serwerze i internet do pobrania obrazów oraz zależności.
- Dostęp do wybranego portu HTTP z urządzeń użytkowników.

Python, Node, Nginx i PostgreSQL działają w kontenerach. Nie trzeba instalować
ich osobno na hoście. Instalator nie instaluje Dockera i nie zmienia zapory.
Wersje obrazów i zależności wskazują [Dockerfile](../deploy/Dockerfile),
[Compose](../deploy/compose.yaml) oraz lockfile frontendów.

## Instalacja

Po pobraniu lub skopiowaniu projektu na serwer:

```sh
cd ancore
./ancore-install.sh
```

Równoważne polecenia to `./ancore-install.sh install` i `./ancore-install.sh setup`.
Można również użyć `sh ancore-install.sh`.

1. Podaj IPv4 serwera, pod którym użytkownicy będą otwierać Ancore, np. `192.168.1.20`.
2. Podaj port HTTP; Enter wybiera domyślne `8080`.
3. Podaj dane administratora: e-mail do logowania, nazwę użytkownika
   (domyślnie `admin`), imię, nazwisko i dwukrotnie hasło.
4. Poczekaj na automatyczną instalację i komunikat z adresem aplikacji.

Pytania obsługuje powłoka `sh` na hoście, zanim Docker pobierze obraz Pythona;
Python nie jest wymagany na serwerze poza kontenerami. Po zebraniu odpowiedzi
instalator automatycznie zapisuje `deploy/.env`, buduje obrazy i oba frontendy,
wykonuje migracje oraz `collectstatic`, a następnie czeka na gotowość czterech
usług. Dopiero wtedy tworzy konto z wcześniej podanych danych, stosując
walidację pól i hasła Django. Hasło wpisujesz w ukrytym polu terminala.
Pozostaje tylko w pamięci procesu do przekazania przez standardowe wejście
polecenia `ensure_admin --from-stdin`. Nie jest zapisywane w `deploy/.env`
ani przekazywane w argumentach polecenia lub zmiennych środowiska.
Dopiero gotowe usługi i konto administratora dają komunikat o zakończeniu
oraz adres, np. `http://192.168.1.20:8080`. Błąd dowolnego etapu kończy
polecenie kodem błędu. Jeśli usługi już działają, a utworzenie konta się nie
powiodło, ponów ten krok przez `./ancore-install.sh admin` w interaktywnym
terminalu. Przerwanie odpowiedzi na początku wymaga ponownego uruchomienia
instalatora.

Nginx publikuje wybrany port na `0.0.0.0`. Na innym komputerze użyj podanego
IP serwera; sieć i zapora muszą dopuszczać połączenia na wybrany port.
Portów bazy, backendu i ONLYOFFICE nie publikuje się osobno.

Ponowne uruchomienie instalatora podpowiada zapisany IPv4 i port. Zachowuje
sekrety, nazwę projektu oraz wolumeny, więc służy także do zmiany adresu
lub portu. Jeśli zapisano konfigurację i backend działa, instalator sprawdza
istnienie aktywnego administratora z hasłem przez `ensure_admin --check-only`.
Po udanym sprawdzeniu pomija pytania o konto. Zatrzymany, niedostępny lub
starszy backend, który nie obsługuje tego sprawdzenia, powoduje zebranie danych
administratora przed instalacją. Po uruchomieniu usług ponownie sprawdzane
jest istnienie administratora: jego konto i hasło zawsze pozostają zachowane,
niezależnie od podanych odpowiedzi.
Nie importuje lokalnej bazy developerskiej ani uploadów z repozytorium.

## Obsługa

| Polecenie | Działanie |
| --- | --- |
| `./ancore-install.sh` | Logo, IP, port i dane administratora, następnie instalacja |
| `./ancore-install.sh start` | Uruchomienie wcześniej zbudowanych usług |
| `./ancore-install.sh stop` | Zatrzymanie usług z zachowaniem danych |
| `./ancore-install.sh restart` | Ponowne uruchomienie usług |
| `./ancore-install.sh status` | Stan kontenerów |
| `./ancore-install.sh logs [USŁUGA]` | Logi wszystkich usług albo wskazanego kontenera |
| `./ancore-install.sh update` | Przebudowa i start z obecnego kodu oraz zapisanej konfiguracji |
| `./ancore-install.sh admin` | Utworzenie dodatkowego administratora Django |
| `./ancore-install.sh --help` | Lista poleceń |

`update` nie pobiera kodu z Git: najpierw pobierz lub skopiuj nowe źródła.
`start` wymaga wcześniejszego zbudowania obrazów przez instalator.
`start`, `restart` i `update` nie pytają o administratora. Polecenie `admin`
pozwala dodać następne konto administracyjne. Zwykłe konta użytkowników można
tworzyć przez rejestrację w aplikacji.

## Konfiguracja i dane

Plik `deploy/.env` ma uprawnienia `0600` i zawiera losowy klucz Django,
osobne hasła ról PostgreSQL oraz sekret JWT ONLYOFFICE. Przykład pól:
[production.env.example](../deploy/production.env.example).
Sekrety, pliki lokalne i dane nie trafiają do Git ani kontekstu budowania.
Starszy plik `deploy/.env.production` jest odczytywany, jeśli nie ma `deploy/.env`.
Instalator zachowuje jego sekrety. Istniejący `deploy/compose.recovery.yaml`
z dawnej odzyskanej instalacji nadal wskazuje jej wolumeny; skrypt zachowuje
to mapowanie. Nie tworzy nowych pakietów odzyskiwania.
Przy uruchomieniu nowego zestawu Compose usuwa stary kontener backupu
tego projektu. Nie usuwa jego archiwów ani wolumenów danych.

Wolumeny przechowują bazę, media, prywatne dokumenty, zasoby statyczne,
pliki tymczasowe oraz dane robocze ONLYOFFICE. Nazwa projektu domyślnie wynosi
`ancore-prod`; przy istniejącej konfiguracji pozostaje zachowana. `stop`
nie usuwa danych. Nie używaj `docker compose down --volumes`, jeśli mają pozostać.

Backend działa jako UID/GID 10001. Rola aplikacji `ancore` nie jest superuserem
PostgreSQL. Nginx udostępnia zasoby statyczne i dozwolone obrazy profilu oraz
Workspace. Prywatne dokumenty i załączniki wydaje Django po kontroli dostępu;
nie ma publicznego aliasu całego katalogu mediów ani dokumentów.
Publiczny limit żądania wynosi 225 MiB, a aplikacja nadal waliduje każdy plik.

## ONLYOFFICE

Przeglądarka używa `/onlyoffice/` pod tym samym adresem HTTP i portem co Ancore.
Django łączy się z `http://onlyoffice`, a podpisane pobrania i callbacki wracają
przez wewnętrzny listener `http://web:8081`. Ten port nie jest publikowany i
obsługuje wyłącznie endpointy edytora oraz readiness.
JWT pozostaje włączony. Wyniki callbacków są pobierane ze stałego wewnętrznego
cache po walidacji ścieżki. Szczegóły: [Dokumenty](OFFICE.md).

## Weryfikacja

Testy instalatora i konfiguracji:

```sh
.venv/bin/python manage.py test core.test_production_installer core.test_production core.test_project_layout
.venv/bin/python scripts/run_tests.py accounts.test_ensure_admin
.venv/bin/python scripts/update_code_index.py --check
```

Po instalacji sprawdź `./ancore-install.sh status`, otwarcie podanego adresu,
logowanie utworzonym kontem administratora, upload i pobranie oraz zapis
dokumentu w ONLYOFFICE. Ponowna instalacja powinna zachować konto i hasło
administratora; przy działającym backendzie powinna też pominąć pytania
o jego dane. Ponowny start powinien zachować dane.
Testy skryptów z zastępczym Docker CLI nie zastępują
uruchomienia pełnego zestawu na docelowym serwerze.
