# Instalacja produkcyjna Docker Compose

Pakiet uruchamia pięć usług na jednym serwerze Linux:

| Usługa | Rola |
| --- | --- |
| `web` | Nginx: zasoby Reacta, publiczne awatary, reverse proxy i opcjonalnie HTTPS |
| `backend` | Django przez Gunicorn, JSON API, kontrola dostępu i pobieranie plików |
| `postgres` | PostgreSQL 17, bez publikacji portu bazy na hoście |
| `backup` | Harmonogram nieszyfrowanych kopii bazy i plików |
| `onlyoffice` | ONLYOFFICE Document Server z JWT i obsługą WebSocketów przez Nginx |

Pliki, baza i backupy **nie są szyfrowane na dysku**. HTTPS chroni połączenia
użytkowników; JWT i hasła kont pozostają częścią dotychczasowych zabezpieczeń.
Nie zmieniono reguł Workspace, Przestrzeni, zadań ani prywatnego pobierania.

## Wymagania

- Serwer Linux z lokalnie działającym Docker Engine i aktualnym Docker Compose
  obsługującym `up --wait`. Działa plugin `docker compose` lub `docker-compose`.
- Pliki projektu na tym samym serwerze co daemon Docker. Instalator montuje
  katalog projektu; zdalny daemon bez tego katalogu nie jest obsługiwany.
- Dostęp do rejestru obrazów, PyPI i npm podczas budowania. Python, Node,
  PostgreSQL i Nginx na hoście nie są potrzebne. Instalator nie instaluje
  Dockera ani nie zmienia zapory hosta.
- Jako punkt startowy przewidź 4 vCPU, 8 GiB RAM i SSD z zapasem na pliki,
  ONLYOFFICE, obrazy oraz backupy. Dopasuj zasoby do obciążenia.

Backend używa Python 3.14.8, należącego do zakresu wsparcia Django 6.1.
Oba frontendy budowane są z lockfile przez Node 24 i pnpm 11.25.0;
proces Node nie działa obok Django w produkcji. Oba pakiety pnpm dopuszczają
skrypt instalacyjny istniejącego esbuild. Lokalny development pozostaje bez zmian.

## Pierwsza instalacja: HTTP bez domeny

Po zainstalowaniu Dockera z Compose pobierz lub skopiuj projekt na serwer,
wejdź do jego katalogu i wykonaj:

```sh
cd ancore
sh install.sh
```

Otwórz `http://IP_SERWERA:8080` (na samym serwerze także `http://localhost:8080`).
Domena i certyfikat nie są wymagane. Domyślny nasłuch to `0.0.0.0:8080`;
dostęp z innych komputerów wymaga przepuszczenia TCP 8080 w zaporze serwera.
Adres nie jest zapisany na sztywno: można użyć aktualnego IP serwera.
W tym trybie Django przyjmuje adresy IP i `localhost`, a odrzuca dowolne nazwy
DNS. Jeśli chcesz używać nazwy hosta, podaj ją przez `--url`.

Instalator automatycznie:

1. Uruchamia konfigurator w tymczasowym kontenerze Pythona.
2. Tworzy `deploy/.env` z uprawnieniami 0600 i osobnymi losowymi sekretami
   Django, bazy aplikacji, administratora PostgreSQL oraz JWT ONLYOFFICE.
3. Przygotowuje katalog backupów, buduje obrazy i oba frontendy.
4. Uruchamia migracje, `collectstatic` i pięć usług z nową pustą bazą.
5. Czeka na gotowość usług; scheduler wykonuje pierwszy backup po starcie.

Nie trzeba ręcznie kopiować ani edytować pliku `.env`. Lokalny `.env` z katalogu
głównego, lokalna baza i uploady nie są importowane ani nadpisywane.
Konfiguracja i dane produkcji są pomijane przez Git oraz `.dockerignore`.
Ponowne `sh install.sh` zachowuje sekrety, projekt i wolumeny; przy działającej
instalacji najpierw wykonuje backup, a następnie przebudowuje i uruchamia usługi.
Zmiana adresu, portu lub protokołu istniejącej instalacji wymaga `--reconfigure`.

Opcje można podać już przy pierwszym uruchomieniu, np.:

```sh
sh install.sh --http-port 8080 --backup-dir /srv/ancore-backups
# Stała nazwa hosta zamiast automatycznej obsługi adresów IP:
sh install.sh --reconfigure --url http://ancore.lan:8080
```

Domyślny katalog kopii to `deploy/backups`. Katalogi przekazuj jako osobny
argument po `--backup-dir` lub `--tls-dir` (ze spacją). Listę opcji pokazuje
`sh install.sh --help`. Konta tworzy istniejąca rejestracja Ancore.

## Opcjonalne HTTPS

Można włączyć HTTPS od razu lub później, zachowując dane i klucze instalacji.
Przygotuj katalog z certyfikatem `fullchain.pem` i kluczem `privkey.pem`, potem:

```sh
sh install.sh --reconfigure \
  --url https://ancore.example.com \
  --tls-dir /etc/ancore/tls
```

Nginx Ancore udostępni HTTPS na porcie 443 i przekieruje dotychczasowy HTTP
z portu 8080 na skonfigurowany adres HTTPS. Certyfikat może dotyczyć także
adresu IP; musi odpowiadać adresowi użytemu przez klienta. Inny port HTTPS
podaj w `--url`, np. `https://192.0.2.10:8443` (lub przez `--https-port` przy
adresie zawierającym ten sam port).

Użyj rzeczywistych plików lub symlinków wewnątrz montowanego katalogu;
symlinki Let's Encrypt z `live/` do zewnętrznego `archive/` nie zadziałają.
Pozyskanie i odnawianie certyfikatu należy do konfiguracji serwera.
Po podmianie plików przeładuj Nginx komendą `exec web nginx -s reload`
według sekcji utrzymania poniżej.

Jeśli HTTPS obsługuje istniejący reverse proxy na tym samym hoście:

```sh
sh install.sh --reconfigure --url https://ancore.example.com
```

Bez `--tls-dir` Nginx Ancore nasłuchuje tylko na `127.0.0.1:8080`.
Skieruj zewnętrzny proxy na ten port, zachowaj publiczny Host i WebSockety
oraz limit uploadu co najmniej 25 MiB. Taki wariant wymaga działającego proxy.

Powrót do domyślnego HTTP bez domeny:

```sh
sh install.sh --reconfigure
```

HTTP nie szyfruje ruchu, w tym sesji i przesyłanych plików. HTTPS włącza
bezpieczne ciasteczka, przekierowania oraz HSTS. Dane i backupy na dysku
pozostają nieszyfrowane w obu wariantach, zgodnie z konfiguracją tej wersji.
Przeglądarka może pamiętać HSTS po HTTPS, więc cofnięcie protokołu może
wymagać zmiany adresu lub usunięcia zapisanej polityki dla testowego hosta.

Przykład ustawień: [production.env.example](../deploy/production.env.example).
Do samego generowania konfiguracji służy także opcjonalne
`python3 scripts/production.py configure`; Python na hoście nie jest wymagany
przez `install.sh`. Konfigurator rozpoznaje również dawny
`deploy/.env.production` i zachowuje jego sekrety podczas przejścia na `deploy/.env`.
Zmiana hasła istniejącej bazy w pliku nie zmienia automatycznie hasła roli PostgreSQL.

## Dane, proxy i ONLYOFFICE

Wolumeny nazwane są w obrębie stałego projektu `ancore-prod`. Przechowują
PostgreSQL, prywatne dokumenty, media, pliki tymczasowe, blokady backupu,
zebrane zasoby oraz katalogi robocze ONLYOFFICE. Są lokalne na serwerze Docker
i pozostają po wymianie kontenerów. Zachowaj nazwę projektu przy aktualizacjach.
Nie używaj `docker compose down --volumes`: usuwa dane instalacji.

Django działa jako UID/GID 10001; katalogi mają ograniczone uprawnienia.
Rola bazy `ancore` jest właścicielem danych aplikacji, bez uprawnień superuser
ani tworzenia baz. Osobne hasło administratora PostgreSQL jest dostępne
wyłącznie usłudze bazy, a nie backendowi lub zadaniu backupu.
Nginx widzi tylko zasoby statyczne i media. Publiczne media obejmują wyłącznie
zdjęcia kont/Workspace z istniejącej listy rozszerzeń. Prywatne dokumenty
i załączniki pobiera Django po kontroli dostępu. Nie ma publicznego aliasu
całego katalogu mediów ani prywatnych dokumentów.

`TRUST_PROXY_HEADERS=true` włącza zaufanie Django do `X-Forwarded-Proto`.
Backend nie publikuje portu, a Nginx nadpisuje ten nagłówek na podstawie
skonfigurowanego publicznego schematu. Nie wystawiaj portu backendu ani nie
włączaj tej opcji przed proxy, które przepuszcza dowolne nagłówki klienta.

ONLYOFFICE jest dostępny dla przeglądarki pod `/onlyoffice/` tego samego
adresu IP lub hosta i portu. `ONLYOFFICE_URL=/onlyoffice` nie odsyła klienta
do `localhost` ani do nazwy kontenera. Adres wyniku z publicznym prefiksem
jest mapowany na skonfigurowany wewnętrzny cache ONLYOFFICE; Django nie
pobiera pliku z hosta przekazanego w callbacku.
Nginx przekazuje wirtualną ścieżkę i nagłówki zgodnie z
[przykładem ONLYOFFICE](https://github.com/ONLYOFFICE/document-server-proxy/blob/master/nginx/proxy-to-virtual-path.conf).
Django wywołuje usługę pod `http://onlyoffice`; podpisane pobrania i callbacki
wracają przez wewnętrzny listener Nginx `http://web:8081`, dopuszczający tylko
te endpointy i sprawdzenie gotowości. Ten port nie jest publikowany. JWT pozostaje włączony,
przykładowa aplikacja ONLYOFFICE wyłączona, a dostęp do adresów metadanych
chmury wyłączony. Dostęp do prywatnych adresów jest konieczny do komunikacji
wewnątrz Compose. Szczegóły domenowe: [OFFICE.md](OFFICE.md).

Logi HTTP nie zawierają standardowego access logu z podpisanymi URL.
Logi kontenerów mają rotację. Hasła są w prywatnym pliku konfiguracji
i środowisku usług; nie są szyfrowane przez Compose. Administrator Dockera
ma do nich dostęp. Nie kopiuj konfiguracji ani danych do Git; `.dockerignore`
wyklucza je również z kontekstu budowania.

## Backup i odtwarzanie

Scheduler wykonuje kopię po starcie, jeżeli jej brakuje lub minął skonfigurowany
interwał (domyślnie 24 godziny). Zachowuje 14 ostatnich poprawnych kopii.
`BACKUP_INTERVAL_SECONDS` i `BACKUP_KEEP` zmieniają te wartości.

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml exec -T backup python3 /opt/ancore/backup.py once
docker compose --env-file deploy/.env -f deploy/compose.yaml ps
```

Przy bezpośrednim HTTPS w tych i kolejnych poleceniach dodaj
`-f deploy/compose.tls.yaml` po `-f deploy/compose.yaml`. Przy samodzielnym
Compose użyj `docker-compose` zamiast `docker compose`.

Backup tworzy nieszyfrowane `.tar.gz` i plik `.sha256`. Archiwum zawiera
`database.dump` z `pg_dump --format=custom`, zapisane pliki prywatne, publiczne
media i manifest formatu/release. Kompresja nie jest szyfrowaniem.

Przed kopiowaniem scheduler ustawia znacznik przerwy, odrzuca nowe żądania
HTTP kodem 503 i czeka na zakończenie wcześniejszych żądań, pobrań i callbacków.
Pierwszy middleware Django używa wspólnej blokady plikowej we wszystkich
workerach. Obejmuje również GET, ponieważ obecna aplikacja może podczas GET
zapisywać sesję lub inicjalizować rekordy. Po `pg_dump` i archiwizacji plików
usuwa blokadę. Przerwa trwa przez przygotowanie całego archiwum; przy dużych
danych zaplanuj ją w oknie serwisowym i dostosuj mechanizm kopii.

Nie uruchamiaj w tym czasie dodatkowych skryptów zapisujących bazę/pliki
z pominięciem HTTP. Backup obejmuje dane zatwierdzone w Ancore, a nie niezapisany
stan edytora w przeglądarce lub roboczy cache ONLYOFFICE. Kopia nie zawiera
sekretów instalacji: zachowaj osobno bezpieczną kopię `deploy/.env` oraz
certyfikatów. Kopiuj archiwa także poza ten serwer — lokalny kontener backupu
nie zabezpiecza przed utratą całej maszyny.

Zaawansowane polecenia `scripts/production.py` wymagają Pythona 3.10+ na hoście;
nie są potrzebne do instalacji, aktualizacji ani zwykłego backupu.
Odtwarzanie do już przygotowanej instalacji, po zamknięciu edytorów:

```sh
# Umieść archiwum i jego plik .sha256 w skonfigurowanym katalogu backupów.
python3 scripts/production.py restore /srv/ancore-backups/ancore-NAZWA.tar.gz --yes
```

Komenda `restore` sama zatrzymuje zapisujące usługi, weryfikuje sumę i format,
uruchamia PostgreSQL, odtwarza bazę przez transakcyjny `pg_restore`, zastępuje katalogi plików,
ustawia ich właściciela i uruchamia zestaw ponownie. Zastępuje bieżące dane;
wcześniej zachowaj potrzebny aktualny backup. Przy błędzie pozostawia aplikację
zatrzymaną, aby można było dokończyć naprawę. Odtwarzaj kod zgodny z wersją kopii;
przy zmianach schematu zachowaj odpowiedni commit/tag oraz konfigurację.

Po nagłym zabiciu procesu backupu może pozostać znacznik przerwy.
Sprawdź logi i stan zadania, następnie użyj `python3 scripts/production.py unlock`.
Komenda odmówi usunięcia blokady, jeżeli proces kopii nadal ją trzyma.
Healthcheck backupu sygnalizuje brak aktualnej kopii; zewnętrzny monitoring
powinien zgłaszać niezdrowe usługi. Docker sam nie wysyła powiadomień.

## Aktualizacja i zatrzymywanie

Po pobraniu aktualnego kodu ponów instalator. Wykona backup działającej
instalacji przed przebudową obrazów i migracjami:

```sh
sh install.sh
docker compose --env-file deploy/.env -f deploy/compose.yaml ps
docker compose --env-file deploy/.env -f deploy/compose.yaml stop
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d --wait
```

Przy bezpośrednim HTTPS dodaj plik `-f deploy/compose.tls.yaml` do poleceń
Compose, także przy ponownym `up`. `sh install.sh` dobiera go automatycznie.
Opcjonalnego administratora Django utworzysz przez
`docker compose --env-file deploy/.env -f deploy/compose.yaml exec backend python manage.py createsuperuser`;
hasło jest wprowadzane interaktywnie. Przeładowanie certyfikatu wykonaj przez
`exec web nginx -s reload` z tymi samymi argumentami Compose.

`collectstatic` zachowuje poprzednie chunki dla otwartych kart. `stop` zatrzymuje
kontenery bez usuwania wolumenów. Nie zmieniaj głównej wersji PostgreSQL przez
samą zmianę tagu obrazu; wymaga to osobnej procedury migracji i odtworzenia.
Opcjonalny `scripts/production.py` nadal udostępnia polecenia `update`, `backup`,
`status`, `stop`, `start`, `admin`, `reload` i `restore`.

Domyślne obrazy mają przypięte wersje Python/Node/Nginx/ONLYOFFICE, a PostgreSQL
pozostaje na linii 17 (aktualizacje minor). Gunicorn i jego zależność są
przypięte w `deploy/requirements.txt`. Aktualizacje obrazów i zależności
wymagają ponownej weryfikacji, w tym zapisu dokumentu w ONLYOFFICE.

## Weryfikacja pakietu

Testy konfiguracji, blokad backupu i readiness:

```sh
.venv/bin/python manage.py test core.test_production core.test_project_layout
docker compose --env-file deploy/.env -f deploy/compose.yaml config --quiet
```

Przed wdrożeniem na docelowy serwer sprawdź pięć zdrowych usług, logowanie,
uprawnienia dwóch Workspace, upload/pobranie, zapis ONLYOFFICE, backup oraz
odtworzenie kopii w osobnej instalacji. Sprawdź również restart kontenerów
i zachowanie danych. Opis faktycznie wykonanej weryfikacji znajduje się
w [DEVELOPMENT.md](DEVELOPMENT.md#produkcja-docker-compose-20102026).
