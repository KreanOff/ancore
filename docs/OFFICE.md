# Pełne edytory Dokumentów

Dokumenty pozostają osobnym modułem obok Dysku. Katalog i metadane używają
Django, wspólnych szablonów/CSS oraz zwykłego JavaScriptu. DOCX, XLSX i PPTX
edytuje lokalny ONLYOFFICE Docs; tablice — lokalnie zbudowany Excalidraw.
To edytory zgodne z formatami Microsoft Office, a nie oryginalne aplikacje
Microsoft 365. Zgodność wszystkich funkcji desktopowego Office nie jest gwarantowana.

## Funkcje

- **Dokument:** plik DOCX, formatowanie, tabele, obrazy, układ stron, komentarze
  i pozostałe narzędzia dostępne w ONLYOFFICE Document Editor.
- **Arkusz:** XLSX, komórki, formuły, arkusze, formatowanie i wykresy.
- **Prezentacja:** PPTX, slajdy, tekst, kształty, obrazy i pokaz slajdów.
- **Tablica:** tekst, kształty, strzałki, rysowanie, obrazy PNG/JPG/WebP,
  cofanie, powiększenie, import `.excalidraw`, eksport sceny oraz PNG/SVG.
- Wysłane DOCX/XLSX/PPTX otwierają się bezpośrednio w odpowiednim edytorze.
  ONLYOFFICE otwiera się w osobnej karcie przeglądarki, na pełną szerokość
  bez nawigacji bocznej. Dotyczy to katalogu, wyszukiwarki, tworzenia pliku
  oraz konwersji. Pierwotna karta zachowuje katalog; nowa ma pasek nazwy,
  metadanych, pobierania i zapisu. Tablica pozostaje w bieżącej karcie Ancore.
  Jeżeli przeglądarka blokuje nową kartę podczas tworzenia, modal pokazuje
  odnośnik do już zapisanego dokumentu, bez ponownego tworzenia pliku.
  DOC/XLS/PPT/RTF/TXT/CSV można przekonwertować do osobnej kopii OOXML;
  oryginał pozostaje w katalogu. PDF zachowuje dotychczasowy podgląd/pobieranie.
- Starsze dokumenty Ancore nadal używają prostego edytora. Przycisk nad treścią
  tworzy kopię DOCX z obsługiwanym formatowaniem i otwiera pełny edytor.
- Pliki należą wyłącznie do właściciela i Workspace. Integracja nie włącza
  udostępniania, współpracy pomiędzy kontami ani dostępu członków Workspace.

## Lokalne uruchomienie na Macu

Zależności: Homebrew, Colima, Docker CLI i Compose, Python z `requirements.txt`.
Serwer dokumentów używa osobnej maszyny `ancore` (2 CPU, 4 GiB RAM, dysk 40 GiB).
Start/stop nie zmienia domyślnego kontekstu Docker użytkownika. Przy pierwszym
uruchomieniu potrzebne jest połączenie z Internetem do pobrania obrazu.

```sh
brew install colima docker docker-compose
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
./scripts/start_office.sh
```

Skrypt tworzy `.env.office` z losowym kluczem i prawami 0600 tylko, jeśli pliku
jeszcze nie ma. Nie zmienia głównego `.env` ani istniejących sekretów.
`settings.py` ładuje dodatkowy plik bez nadpisywania istniejących zmiennych.
Obraz w [Compose](../deploy/office.compose.yml) jest przypięty wersją 9.4.0
oraz digestem; port 8088 jest związany wyłącznie z 127.0.0.1.

Ancore musi być dostępne z VM pod `host.lima.internal:8000`, np. przez
`manage.py runserver 0.0.0.0:8000`. Host `host.lima.internal` musi być dozwolony
w `ALLOWED_HOSTS`. Lokalny proces uruchomiony tylko na 127.0.0.1 może wymagać
zmiany bindowania. Serwer Ancore uruchamia się niezależnie od serwera dokumentów.
Po utworzeniu konfiguracji zrestartuj proces Django, jeśli nie używa autoreload.

```sh
curl -fsS http://127.0.0.1:8088/healthcheck
DOCKER_CONTEXT=colima-ancore docker-compose --env-file .env.office -f deploy/office.compose.yml ps
colima stop --profile ancore
```

Aby wznowić po restarcie Maca, uruchom `./scripts/start_office.sh`.
Nie skonfigurowano autostartu przy logowaniu. Wolumeny `docs-data`, `docs-lib`
i `docs-logs` zachowują dane serwera przy restarcie. Dokumenty Ancore znajdują
się nadal w `private_documents/`, tablice w bazie PostgreSQL.

## Zasoby tablicy

Node i pnpm są potrzebne wyłącznie przy budowaniu lokalnych zasobów. React
jest ograniczony do odizolowanego iframe edytora; nie zastępuje frontendu Ancore.
Źródła i lockfile znajdują się w [frontend/board](../frontend/board/package.json).

```sh
pnpm --dir frontend/board install --frozen-lockfile
pnpm --dir frontend/board build
```

Wynik `static/vendor/board/` jest ignorowany w Git. Zbuduj go przed `collectstatic`
i przy wdrożeniu na nowym środowisku. Pakiety są przypięte: Excalidraw 0.18.1,
React 18.3.1 i esbuild 0.25.12. Fonty są kopiowane lokalnie. Kontrolowana poprawka w `build.mjs` zastępuje
zapasowy adres fontów CDN adresem lokalnym (sprawdza oczekiwany fragment
przypiętej wersji); aktualizacja Excalidraw wymaga ponownej weryfikacji tej poprawki. Licencje zależności
są dołączane do wygenerowanego `THIRD_PARTY_LICENSES.txt`. Wtyczki zewnętrzne,
zewnętrzne osadzane strony i zewnętrzne fonty nie są wymagane do edycji tablicy.
Prywatna scena nie jest wysyłana do excalidraw.com i nie jest utrwalana w
localStorage przeglądarki. Biblioteka kształtów w panelu Excalidraw nie jest
osobnym trwałym katalogiem Ancore — elementy dodane do sceny są zapisywane.

## Konfiguracja na innym serwerze

| Zmienna | Znaczenie |
| --- | --- |
| `ONLYOFFICE_URL` | Adres ONLYOFFICE dostępny w przeglądarce użytkownika |
| `ONLYOFFICE_INTERNAL_URL` | Adres tego samego ONLYOFFICE osiągalny z Django; domyślnie powyższy |
| `ONLYOFFICE_ANCORE_URL` | Bazowy adres Ancore osiągalny z serwera dokumentów |
| `ONLYOFFICE_JWT_SECRET` | Wspólny losowy sekret, minimum 32 znaki, taki sam jak `JWT_SECRET` serwera |

Compose jest konfiguracją dla jednego Maca. Dostęp z innych komputerów wymaga
osiągalnych nazw/HTTPS, poprawnych hostów Django i reverse proxy z WebSocketami.
Nie używaj `127.0.0.1` jako adresu edytora dla klientów na innych komputerach.
Nie publikuj prywatnego storage przez serwer WWW. Nie włączaj publicznego
serwera demonstracyjnego ONLYOFFICE ani wyłączania JWT.

Integracja korzysta z ONLYOFFICE Community; przed publiczną dystrybucją lub
wdrożeniem komercyjnym sprawdź warunki licencji wybranej edycji i jej limity
połączeń/urządzeń. Mobilny interfejs desktopowy może wymagać większego ekranu;
nie wdrażano płatnych funkcji mobilnych ani integracji Microsoft 365.

## Zapis i granice dostępu

- Ekrany użytkownika i zapis tablicy wymagają sesji, właściciela oraz aktywnego
  Workspace; operacje POST wymagają CSRF. Przechowywanie plików używa istniejącego
  prywatnego storage, wspólnej walidacji sygnatur i limitu 10 MiB.
- Pliki OOXML są dodatkowo sprawdzane pod kątem głównej części pakietu,
  liczby wpisów i łącznego rozmiaru po rozpakowaniu; archiwa nie są wypakowywane
  na dysk. Domyślne puste pliki w `documents/blank/` powstały lokalnie i nie
  zawierają danych użytkowników ani makr.
- Dwa serwisowe endpointy `/office-service/<uuid>/source/` i `callback/` nie
  używają sesji ani aktywnego Workspace z ciasteczka. Wymagają podpisanej
  zdolności dostępu do konkretnego pliku/właściciela/Workspace/sesji edytora
  (ważność 7 dni). Po tym czasie należy ponownie otworzyć edytor.
- Callback dodatkowo wymaga poprawnego HS256 JWT z serwera; podpisane dane
  `payload` są jedynym źródłem statusu, klucza i URL wyniku. Token konfiguracji
  przeglądarki nie uprawnia do zapisu. Własne tokeny JWT wygasają po 5 minutach.
- Wynik jest pobierany wyłącznie z `/cache/files/` skonfigurowanego ONLYOFFICE,
  bez przekierowań, z limitem rozmiaru i czasem oczekiwania. Błąd nie podmienia
  oryginału. Nowy plik trafia do storage, rekord jest aktualizowany transakcyjnie,
  a stary plik usuwany dopiero po commit.
- Status 6 zapisuje plik podczas pracy; status 2 kończy sesję i zmienia jej
  klucz. Ponowione callbacki są rozpoznawane przez `OfficeSaveReceipt`.
  Podmiana pliku oraz przeniesienie do/z kosza unieważniają stare sesje.
  Klucz zawiera pośrednio UUID dokumentu i sekret instalacji, więc nie zależy
  wyłącznie od numeru rewizji. Nie zmieniaj pliku w katalogu storage poza Ancore.
- Zapis w edytorze i przycisk Ancore wyzwalają force save. Po ustaniu zmian
  aplikacja też zleca zapis. Pasek statusu potwierdza zapis po zwiększeniu rewizji
  w Django; sam komunikat edytora o synchronizacji nie jest potwierdzeniem
  zapisu w prywatnym storage. Zamknięcie edytora może zapisać wynik po kilku
  sekundach, zgodnie z protokołem ONLYOFFICE.
- Tablica zapisuje scenę po krótkiej przerwie w edycji oraz na żądanie/Ctrl+S.
  Rewizja zapobiega nadpisaniu przez starsze okno (409). Przy błędzie scena
  pozostaje w przeglądarce; „Pobierz” pobiera bieżącą lokalną kopię. Ochrona
  przed wyjściem działa, gdy istnieją niezapisane zmiany.
- Scena tablicy ma limit 10 MiB i 10 000 elementów. Obrazy są walidowanymi
  danymi PNG/JPEG/WebP (do 200 obrazów, po 5 MiB każdy, w ramach limitu sceny).
  Aktywne osadzenia i niebezpieczne schematy odnośników są odrzucane. Iframe ma
  CSP ograniczające połączenia, skrypty i fonty do lokalnej aplikacji.

`revision` i potwierdzenia callbacków nie są historią wersji do przywracania.
Nie ma wspólnej edycji pomiędzy różnymi użytkownikami, OCR, edycji PDF ani VBA.
Kopia przekonwertowana ze starego formatu może różnić się wizualnie; oryginał
pozostaje dostępny. Utworzenie pliku nie wymaga działającego serwera, ale jego
pełna edycja wymaga uruchomionego ONLYOFFICE. Tablica działa niezależnie.

## Źródła integracji

- [ONLYOFFICE — konfiguracja i architektura](https://api.onlyoffice.com/docs/docs-api/get-started/basic-concepts/)
- [ONLYOFFICE — podpisy żądań](https://api.onlyoffice.com/docs/docs-api/additional-api/signature/request/token-in-header/)
- [ONLYOFFICE — callback zapisu](https://api.onlyoffice.com/docs/docs-api/usage-api/callback-handler/)
- [Excalidraw — instalacja i lokalne fonty](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/installation)
