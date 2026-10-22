# Instalacja i obsługa produkcji

Ancore działa na jednym serwerze Linux. Obrazy aplikacji i oba frontendy są
budowane na tym serwerze. Baza, pliki, edytor i backupy pozostają lokalne.
Pierwsza instalacja i przebudowa wymagają internetu do pobrania obrazów bazowych,
ONLYOFFICE oraz zależności Python/JavaScript; nie jest to instalator offline.

| Usługa | Rola |
| --- | --- |
| `web` | Nginx: zasoby, awatary, reverse proxy i opcjonalnie HTTPS |
| `backend` | Django/Gunicorn: aplikacja, API i kontrolowane pobieranie plików |
| `postgres` | PostgreSQL 17, bez portu publikowanego na hoście |
| `backup` | Harmonogram lokalnych kopii bazy i plików |
| `onlyoffice` | Edytor dokumentów z JWT i WebSocketami przez Nginx |

Dane i backupy nie są szyfrowane na dysku. HTTPS szyfruje połączenia użytkowników.
Instalator zachowuje uprawnienia Workspace, Przestrzeni i prywatnych plików.

## Wymagania

- Docker Engine z lokalnym socketem `unix://` i Compose obsługującym
  `up --wait --wait-timeout`. Obsługiwane są `docker compose` i `docker-compose`.
- Źródła projektu na tym samym serwerze co daemon Docker; zdalny daemon jest
  odrzucany. Użytkownik potrzebuje dostępu do Dockera i zapisu w katalogu projektu.
- Jako punkt startowy: 4 vCPU, 8 GiB RAM i SSD z zapasem na ONLYOFFICE, pliki,
  obrazy, archiwa oraz miejsce robocze backupu i odtwarzania.

Python, Node, PostgreSQL i Nginx działają w kontenerach. Instalator nie instaluje
Dockera, nie zmienia grup użytkownika ani zapory. Przy odmowie dostępu do socketu
sprawdź usługę Docker i [uprawnienia użytkownika](https://docs.docker.com/engine/install/linux-postinstall/).
Grupa `docker` daje uprawnienia równoważne administratorowi.

Backend budowany jest na Pythonie 3.14.8, frontendy na Node 24 i pnpm 11.25.0
z lockfile. Wersje bazowe wskazuje [Dockerfile](../deploy/Dockerfile), a zależności
Gunicorna [deploy/backend/requirements.txt](../deploy/backend/requirements.txt).

## Pierwsza instalacja

Po pobraniu lub skopiowaniu źródeł na serwer:

```sh
cd ancore
./ancore.sh setup
```

Konfigurator pyta o IP lub domenę **bez protokołu i portu**, HTTP/HTTPS, porty,
nasłuch i katalog backupów. Wartość `auto` zachowuje obsługę dowolnego IP serwera.
Domyślnie używa HTTP, portu 8080 oraz nasłuchu `0.0.0.0`, pozwalającego na
połączenia z sieci, jeśli przepuszcza je zapora. Nasłuch `127.0.0.1` ogranicza
połączenia do serwera. Można także wybrać konkretny interfejs IPv4.

Po podsumowaniu zapisuje `deploy/.env` (0600) z osobnymi losowymi sekretami
Django, aplikacyjnej i administracyjnej roli PostgreSQL oraz JWT ONLYOFFICE.
Następnie pyta, czy zbudować i uruchomić Ancore. Odpowiedź `n` zapisuje ustawienia;
później uruchom `./ancore.sh install`. Ponowny konfigurator podpowiada zapisane
wartości i zachowuje sekrety, nazwę projektu i wolumeny.

Przykładowy adres po instalacji: `http://IP_SERWERA:8080`. Na innym urządzeniu
wpisz IP serwera, nie `localhost`. Lokalne `.env`, baza developerska i uploady
nie są importowane ani nadpisywane przez instalator.

Przed budowaniem sprawdzane są zajęte porty innych kontenerów oraz hosta
(przez `ss`, `netstat` lub `lsof`, jeśli są dostępne). Port bieżącego kontenera
`web` tej instalacji jest dopuszczony przy jego wymianie. Kontrola jest wstępna;
ostatecznie gotowość potwierdza `up --wait`. Błąd kończy polecenie kodem błędu,
bez komunikatu o gotowości.

## Jedno polecenie do obsługi

Wszystkie operacje udostępnia `ancore.sh`; działa także `sh ancore.sh` na Ubuntu.

| Polecenie | Działanie |
| --- | --- |
| `./ancore.sh setup` | Konfigurator krok po kroku |
| `./ancore.sh configure [OPCJE]` | Zapis ustawień bez budowania i startu |
| `./ancore.sh install [OPCJE]` | Konfiguracja, backup działającej instalacji, lokalny build i start |
| `./ancore.sh update` | Backup, lokalny build i start istniejącej instalacji z aktualnego kodu |
| `./ancore.sh start` | Start lokalnych obrazów bez budowania i pobierania |
| `./ancore.sh stop` / `restart` | Zatrzymanie lub ponowny start z zachowaniem danych |
| `./ancore.sh status` | Stan wszystkich usług |
| `./ancore.sh logs [USŁUGA]` | Podgląd logów; Ctrl+C kończy podgląd, zachowując usługi |
| `./ancore.sh doctor` | Kontrola Dockera, konfiguracji, portów oraz tabela stanu usług |
| `./ancore.sh backup` | Lokalna kopia bazy i plików |
| `./ancore.sh restore PLIK --yes` | Odtworzenie kopii z zastąpieniem bieżących danych |
| `./ancore.sh unlock` | Usunięcie pozostałej blokady, jeśli kopia nie trwa |
| `./ancore.sh reload` | Sprawdzenie i przeładowanie Nginx w kontenerze |
| `./ancore.sh admin` | Interaktywne utworzenie administratora Django |

`start` wymaga obrazów wcześniej przygotowanych przez `install`. `update`
wymaga istniejącej konfiguracji i nie pobiera kodu z Git. Najpierw pobierz lub
skopiuj nowe źródła. Build używa lokalnego buildera Dockera, niezależnie od
globalnie wybranego buildera Buildx. `collectstatic` zachowuje poprzednie chunki
dla otwartych kart przeglądarki.

`doctor` pokazuje stan usług, ale nie potwierdza dostępu z fizycznego urządzenia
w LAN. Przy problemach sprawdź IP, port, nasłuch, zaporę, izolację Wi-Fi i tryb
sieci maszyny wirtualnej. Healthchecki nie zastępują monitoringu z powiadomieniami.

## Konfiguracja bez pytań

```sh
./ancore.sh install --http-port 8080 --backup-dir /srv/ancore-backups
./ancore.sh configure --reconfigure --url http://ancore.lan:8080
./ancore.sh install
./ancore.sh install --help
```

Zmiana adresu, portów lub protokołu wymaga `--reconfigure`. Katalogi przekazuj
jako osobny argument, np. `--backup-dir /srv/ancore-backups`. Przykład pól:
[production.env.example](../deploy/production.env.example). Zmiana hasła roli
bazy w pliku nie aktualizuje automatycznie hasła w istniejącym PostgreSQL.

Opcje globalne podaje się przed poleceniem:

```sh
./ancore.sh --env-file /srv/ancore/.env --context lokalny-docker status
```

Własny plik konfiguracji jest obsługiwany także przez konfigurator. Kontekst
musi wskazywać lokalny Docker i widzieć te same ścieżki. Nie zmienia to globalnie
wybranego kontekstu Docker użytkownika.

## Opcjonalne HTTPS

Nginx Ancore może obsługiwać HTTPS bez dodatkowej instalacji Nginx na hoście.
Przygotuj `fullchain.pem` i `privkey.pem` odpowiadające IP lub domenie, a następnie:

```sh
./ancore.sh configure --reconfigure \
  --url https://ancore.example.com --tls-dir /etc/ancore/tls
./ancore.sh start
```

Port HTTPS domyślnie wynosi 443; niestandardowy podaj w adresie, np. `:8443`.
HTTP na dotychczasowym porcie przekierowuje na skonfigurowany adres HTTPS.
Pliki certyfikatu lub ich symlinki muszą mieścić się w montowanym katalogu;
symlinki Let's Encrypt z `live/` do zewnętrznego `archive/` nie zadziałają.
Pozyskanie i odnawianie certyfikatu pozostaje zadaniem administratora.
Po wymianie plików wykonaj `./ancore.sh reload`.

Jeżeli HTTPS obsługuje istniejący reverse proxy:

```sh
./ancore.sh configure --reconfigure --url https://ancore.example.com
./ancore.sh start
```

Bez `--tls-dir` Ancore nasłuchuje na `127.0.0.1:8080`. Zewnętrzny proxy powinien
przekazywać publiczny Host, WebSockety i uploady co najmniej 25 MiB na ten port.
HTTPS włącza bezpieczne ciasteczka, przekierowania i HSTS. Powrót do HTTP:

```sh
./ancore.sh configure --reconfigure
./ancore.sh start
```

HTTP nie szyfruje sesji ani plików w przesyle. Po HTTPS przeglądarka może pamiętać
HSTS; cofnięcie protokołu może wymagać innego adresu lub wyczyszczenia polityki
dla testowego hosta. Dane na dysku pozostają nieszyfrowane w obu wariantach.

## Dane, proxy i ONLYOFFICE

Wolumeny należą do stałego projektu `ancore-prod` albo nazwy podanej przy
pierwszej instalacji przez `--project`. Przechowują bazę, media, prywatne pliki,
pliki tymczasowe, blokady, static oraz katalogi robocze ONLYOFFICE. Zachowaj nazwę
projektu. `stop` zachowuje dane; `docker compose down --volumes` je usuwa.

Django działa jako UID/GID 10001. Rola `ancore` jest właścicielem danych aplikacji,
bez superuser/CREATEDB. Osobne hasło administratora PostgreSQL widzi wyłącznie
usługa bazy. Nginx ma dostęp do static oraz dozwolonych awatarów JPG/JPEG/PNG/WebP;
prywatne dokumenty i załączniki wydaje Django po kontroli dostępu. Nie ma
publicznego aliasu całego katalogu mediów ani dokumentów.

Backend nie publikuje portu. `TRUST_PROXY_HEADERS=true` zakłada zaufany Nginx,
który nadpisuje `X-Forwarded-Proto` na podstawie skonfigurowanego schematu.
Nie wystawiaj backendu bezpośrednio z taką konfiguracją.

Przeglądarka używa `/onlyoffice/` pod adresem Ancore. Django łączy się z
`http://onlyoffice`, a podpisane pobrania i callbacki wracają przez wewnętrzny
listener `http://web:8081`, dopuszczający tylko endpointy edytora i readiness.
JWT pozostaje włączony, aplikacja demonstracyjna i dostęp do adresów metadanych
chmury są wyłączone. Wynik callbacku jest pobierany ze stałego wewnętrznego
cache ONLYOFFICE po walidacji ścieżki. Szczegóły: [OFFICE.md](OFFICE.md).

Konfiguracja i dane są pomijane przez Git i kontekst budowania. Sekrety są w
prywatnym pliku i środowisku usług, dostępnym administratorowi Dockera.
Logi mają rotację; standardowe access logi z podpisanymi URL są wyłączone.

## Backup i odtwarzanie

Scheduler domyślnie wykonuje kopię co 24 godziny i zachowuje 14 poprawnych kopii.
Wartości zmieniają `BACKUP_INTERVAL_SECONDS` i `BACKUP_KEEP`. Po starcie tworzy
kopię, jeśli jej brakuje lub upłynął interwał. Ręczne wykonanie:

```sh
./ancore.sh backup
```

Archiwum `.tar.gz` i jego `.sha256` zawierają `database.dump` z `pg_dump --format=custom`,
media, prywatne pliki i manifest formatu/release. Nie zawierają konfiguracji ani
certyfikatów; zachowaj ich osobną bezpieczną kopię. Lokalne kopie nie chronią
przed utratą całego serwera; przechowuj potrzebne archiwa także poza nim.

Backup ustawia znacznik przerwy, odrzuca nowe żądania kodem 503 i czeka na
zakończenie wcześniejszych operacji, pobrań i callbacków przez wspólną blokadę
wszystkich workerów. Obejmuje GET, ponieważ aplikacja może podczas odczytu
zapisywać sesje i inicjalizować rekordy. Przerwa trwa przez przygotowanie całego
archiwum; dla dużych instalacji przewidź okno serwisowe lub rozbudowę mechanizmu.
Nie zapisuj w tym czasie danych dodatkowymi skryptami omijającymi HTTP.
Kopia obejmuje dane zatwierdzone w Ancore, bez niezapisanych edycji i cache ONLYOFFICE.

Po zamknięciu edytorów umieść archiwum i `.sha256` w skonfigurowanym katalogu kopii:

```sh
./ancore.sh restore /srv/ancore-backups/ancore-NAZWA.tar.gz --yes
```

Polecenie sprawdza argumenty i lokalizację, zatrzymuje zapisujące usługi,
weryfikuje sumę i format archiwum, odtwarza bazę przez transakcyjny `pg_restore`,
zastępuje pliki, ustawia ich właściciela i uruchamia usługi ponownie.
Błąd pozostawia zapisujące usługi zatrzymane. Odtwarzaj kod zgodny z wersją kopii;
zachowaj potrzebny commit/tag i konfigurację. Przed zastąpieniem danych zachowaj
potrzebny aktualny backup. Główna wersja PostgreSQL wymaga osobnej procedury migracji.

Po nagłym zabiciu backupu sprawdź logi i stan operacji, a następnie użyj
`./ancore.sh unlock`. Polecenie odmówi usunięcia blokady trzymanej przez trwającą kopię.
Healthcheck backupu sygnalizuje brak aktualnej kopii; Docker sam nie wysyła powiadomień.

## Pliki i zgodność

- `ancore.sh` — wspólne publiczne polecenia instalacji i utrzymania.
- `deploy/cli/runtime.sh` — jedna implementacja Compose, konfiguracji, budowania i odtwarzania.
- `deploy/cli/setup.sh` — pytania i podsumowanie konfiguratora terminalowego.
- `deploy/cli/configure.py` — walidacja i zapis konfiguracji; instalator uruchamia go w Dockerze.
- `deploy/compose*.yaml`, `deploy/Dockerfile` — usługi i wspólne budowanie obrazów.
- `scripts/production.py` — zgodność ze starszymi poleceniami: konfigurację przekazuje
  do `deploy/cli/configure.py`, operacje do `ancore.sh`. Nie ma osobnego mechanizmu wdrażania.

Instalację uruchamiaj przez `./ancore.sh setup` lub `./ancore.sh install`.
Sama konfiguracja używa `./ancore.sh configure`; `install --configure-only`
pozostaje obsługiwanym wariantem.
Konfigurator rozpoznaje `deploy/.env.production` i przenosi jego ustawienia do
`deploy/.env`, zachowując sekrety. Lokalny development i `.env.office` pozostają osobne.

## Weryfikacja pakietu

```sh
.venv/bin/python manage.py test core.test_production_installer core.test_production core.test_project_layout
.venv/bin/python scripts/update_code_index.py --check
./ancore.sh doctor
```

Przed wdrożeniem sprawdź pięć zdrowych usług, logowanie, uprawnienia dwóch Workspace,
upload/pobranie, zapis ONLYOFFICE, backup i odtworzenie w osobnej instalacji oraz
restart z zachowaniem danych. Zakres wykonanej weryfikacji opisuje
[DEVELOPMENT.md](DEVELOPMENT.md).
