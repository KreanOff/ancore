# Frontend React i backend Django

## Zakres migracji

Interfejs aktywnej aplikacji korzysta z Reacta i TypeScriptu. Przeniesione ekrany:

- **Zasoby:** katalog, filtry, sortowanie, paginacja, kolumny i pełne CRUD.
- **Kalendarz:** miesiąc/tydzień/dzień/rok, plan, filtry, wydarzenia i terminy zadań.
- **Dla ciebie** oraz centrum **Ustawień**.
- **Przestrzenie:** katalog i zarządzanie, kreator szablonu, formularze, awatary,
  podsumowanie, lista zadań, tablica, backlog, sprinty, oś czasu, raporty,
  ustawienia dostępu i konfiguracja statusów/typów/pól.
- **Szczegóły zadania Przestrzeni:** właściwości z automatycznym zapisem,
  komentarze ze wzmiankami i plikami, załączniki, podzadania, dziennik pracy,
  członkowie/role oraz historia.
- **Zespoły:** katalog, szczegóły, formularz i członkostwa.
- **Tagi Przestrzeni:** katalog, wyszukiwanie, filtry, sortowanie, paginacja,
  układ/szerokości kolumn, CRUD, informacje, notatki i zbiorcze usuwanie.
- **Filtry zadań:** wyszukiwanie podstawowe i zaawansowane, katalog i zarządzanie,
  zapis/edycja/kopia definicji, osobiste gwiazdki i udostępnianie.
- **Pulpity:** katalog i zarządzanie, pulpit domyślny, przegląd, ustawienia,
  dostępy oraz edytor gadżetów z katalogiem, pięcioma układami i przeciąganiem.
- **Dysk i Dokumenty:** listy/kafelki, filtry i wyszukiwanie, formularze, upload,
  podglądy, przenoszenie, gwiazdki, kosz, szablony, edytor tekstowy Ancore
  i powłoka pełnych edytorów z edycją nazwy oraz stanem zapisu.
- **Zarządzanie Workspace:** katalog, tworzenie, ustawienia, awatary/kadrowanie,
  członkowie i role, wysyłanie/anulowanie zaproszeń, przeglądanie otrzymanych
  zaproszeń oraz przyjęcie/odrzucenie i jawne przełączanie kontekstu.
- **Konta:** logowanie, rejestracja, dodawanie konta, profil i edycja danych,
  30 awatarów użytkownika oraz zdjęcie z kadrowaniem, status obecności,
  przełączanie i usuwanie kont z sesji.
- **Globalne panele:** wyszukiwanie z ostatnio oglądanymi i filtrami typów,
  centrum powiadomień z licznikami, filtrami, paginacją i akcjami oraz Sticker.

- **Wspólna powłoka:** nagłówek, wybór Workspace, wszystkie tryby menu bocznego,
  zwijanie i szerokość, Favorites z kolejnością/przeciąganiem, pickery kolekcji,
  komunikaty oraz nawigacja z historią i powrotem z zarządzania.

Zakres migracji aktywnych modułów i powłoki jest zaimplementowany. Django
zachowuje szablony pierwszego renderowania i zgodności; po uruchomieniu UI
ich interakcje należą do Reacta. Osobny `frontend/board` pozostaje edytorem
React/Excalidraw, a ONLYOFFICE i Django admin zachowują własne interfejsy.
Helpery ikon, dropdownów, awatarów, canvas, plików i modali oraz heartbeat
obecności są adapterami/usługami używanymi przez React. Ich obecność nie
jest pozostałym modułem do migracji. Stan wdrożenia produkcyjnego nie był sprawdzany.

Django pozostaje odpowiedzialne za sesję, CSRF, Workspace, uprawnienia,
walidację, ORM i PostgreSQL. React obsługuje stan i renderowanie przeniesionego
modułu oraz komunikuje się z JSON API. Wspólny origin pozwala zachować obecną
sesję bez nowego systemu tokenów ani konfiguracji CORS.

## Budowanie i uruchamianie

Wymagania frontendu: Node.js 22 lub nowszy oraz pnpm 11. Repozytorium przypina
wersje zależności w `frontend/app/package.json` i `pnpm-lock.yaml`.
React 18.3.1 jest zgodny z wersją używaną przez odizolowany edytor tablicy.

```sh
cd frontend/app
pnpm install --frozen-lockfile
pnpm build
cd ../..
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Podczas pracy można uruchomić `pnpm --dir frontend/app dev` w drugim terminalu.
Polecenie obserwuje źródła i przebudowuje bundle; po zmianie odśwież przeglądarkę.
Nie uruchamia osobnego serwera HTTP ani HMR. Sprawdzanie typów wykonuje
`pnpm --dir frontend/app typecheck`; produkcyjny `build` też je uruchamia.
`pnpm --dir frontend/app format:check` sprawdza format źródeł;
`pnpm --dir frontend/app format` go poprawia.

esbuild zapisuje lokalne pliki z hashem, osobne chunki i informacje licencyjne
w ignorowanym katalogu `static/frontend/`. `manifest.json` wskazuje bieżący
plik wejściowy, a tag `backend/core/templatetags/frontend.py` buduje jego URL przez
mechanizm Django `static`. Brak buildu daje jawny błąd konfiguracji.
Zbuduj frontend także przed testami renderującymi przeniesione ekrany.

Wdrożenie wymaga `pnpm install --frozen-lockfile`, `pnpm build`, a następnie
`manage.py collectstatic` i standardowego wdrożenia Django. Zachowaj poprzednie
chunki podczas wymiany wersji, aby otwarte karty mogły dokończyć ich pobieranie.
Node i pnpm są potrzebne podczas budowania; nie są procesami aplikacji w produkcji.
Pakiet tablicy nadal buduje się osobno według [OFFICE.md](OFFICE.md).

## Podział źródeł i cykl życia

- `frontend/app/src/main.tsx` montuje moduł na pierwszym wejściu i
  `ancore:content-loaded`, a odmontowuje na `ancore:content-unloading`.
  Import modułu jest odroczony; odłączony kontener nie zostaje zamontowany.
  `AncoreReactRuntime.dispose()` odłącza poprzednią wersję entry pointu
  przed rejestracją nowego hasha podczas częściowej nawigacji.
- Osobny korzeń `[data-react-global-panels]` montuje `src/shell/Shell.tsx`
  z menu, nagłówkiem i `GlobalPanels.tsx`; pozostaje aktywny podczas nawigacji.
  React tworzy hosty wyszukiwania, przycisków, powiadomień, komunikatów i Stickera.
  `dispose()` odłącza także ten korzeń po zmianie bundla. Szablon udostępnia
  konfigurację przez `global_panels_bootstrap` i bezpieczny `json_script`.
- `PageApp.tsx` ładuje osobne chunki ekranów z `src/calendar/`, `src/dashboard/`,
  `src/spaces/`, `src/tasks/`, `src/tags/`, `src/filters/`, `src/pulpits/`, `src/documents/`, `src/workspaces/`, `src/accounts/` i `src/forms/`.
  `backend/core/frontend.py` jawnie rejestruje
  wspierane szablony oraz serializery; pozostałe ekrany zachowują dotychczasowy tryb.
- `src/resources/` zawiera stan katalogu, tabelę, ustawienia kolumn i formularz.
  Początkowe dane pochodzą z bezpiecznego `json_script`; kolejne operacje używają API.
  Bezpośrednie adresy tworzenia/edycji otwierają ten sam moduł i modal.
- `src/shared/` zawiera klienta API oraz adaptery istniejących ikon,
  dropdownów i custom selectów. Zmiany DOM wykonywane przez wspólne helpery
  są zamknięte w osobnych kontenerach, których wnętrza nie renderuje React.
  Ikony korzystają z glifu wygenerowanego w odłączonym kontenerze i korzenia
  SVG należącego do Reacta, bez wrappera zmieniającego selektory wspólnego CSS.
  Selecty z ukrytą etykietą zachowują geometrię `tasks-inline-select` przez
  `react-select-inline`; adapter formularzy uwzględnia techniczne fieldsety
  oraz kontenery kontrolek. [Szczegóły układu](UI.md#ekrany-react-podczas-migracji).
  `DirectoryColumns.tsx` współdzieli zarządzanie kolumnami Zasobów i Tagów,
  zachowując dotychczasowe klucze localStorage. Tagi zachowują również dawny
  podział kluczy zwykłego/scoped adresu (`tasks`/`workplaces`).
- Powłokę zapewnia `core/base.html`, a modal używa `AncoreTaskModals`,
  obsługi Escape, fokusu, `inert` i potwierdzenia porzucenia zmian.
  Wspólny kontrakt okna jest w `static/js/task-modals.js`; `tasks.js` korzysta
  z niego także na starszych ekranach. Styl pochodzi z istniejącego CSS. Nie wprowadzono nowego systemu UI.
- Stary `resources.js` obsługuje wyłącznie zgodne formularze HTML. Pomija
  kontener React, także przy ponownym wejściu po częściowej nawigacji.
  `tasks.js`, `spaces.js`, `calendar.js`, `for-you.js`, `settings.js`,
  `task-filters.js`, `pulpits.js`, `documents.js`, `office.js`, `office-suite.js`, `workplace-team.js`
  i `task-work-log.js` pomijają interakcje strony
  z `[data-react-root="page"]`.
  Nie mogą przestawiać ani podmieniać DOM należącego do Reacta.
- Katalog i zapis używają anulowania żądań, limitu czasu i komunikatów błędu.
  Nowszy tekst wyszukiwania nie jest zastępowany starszą odpowiedzią.
  Parametry filtrów pozostają w URL, a ustawienia kolumn zachowują istniejące
  klucze `resources:directoryColumnLayout:v2` i `resources:directoryColumnWidths:v4`.

Szablon zawiera podstawową listę przed zamontowaniem Reacta. Interakcje Reacta
wymagają JavaScriptu. Dotychczasowe endpointy formularzy HTML i POST pozostają
zgodne; nie stanowią osobnego nowego modułu biznesowego.

Po porządkowaniu z 18.10.2026 stare ekrany Tasks/Kanbana/Kontaktów i skrypt
`project-templates.js` są usunięte. Wspólne include'y Tasks, adaptery JS
oraz CSS pozostają częścią pierwszego renderu i aktualnych ekranów Reacta.
Serializer tagów korzysta z `tasks.tag_directory`, bez importowania
historycznych widoków. Kontrakt API i klasy interfejsu pozostały zachowane.

## API ekranów v1

`GET /api/v1/page/?url=<lokalny_adres>` i scoped wariant
`/workplaces/<slug>/api/v1/page/` zwracają `{type, title, url, api_url, data}`.
`POST` pod ten sam endpoint deleguje formularz do jawnie dopuszczonej
operacji domenowej. Przekierowanie po zapisie staje się `{redirect: adres}`;
walidacja zachowuje HTTP 400 i definicję pól/błędy danego ekranu. JSON nie
zawiera wyrenderowanych fragmentów interfejsu. Opis zadania zachowuje HTML
użytkownika, filtrowany w edytorze tą samą listą dozwolonych znaczników co wcześniej. Nieznana trasa/operacja nie jest dowolnym proxy.
Adresy zewnętrzne są odrzucane, a scoped cel musi należeć do bieżącego Workspace.

`core/frontend.render` używa jawnego serializera dla przeniesionego szablonu.
Przy zwykłym wejściu zachowuje jego kontekst i podstawowy HTML oraz przekazuje
bezpieczny `json_script` do Reacta. Przy żądaniu API zwraca wyłącznie dane.
Dzięki temu te same widoki i formularze zachowują ACL, blokady transakcyjne,
sygnały, walidację relacji, numerację i historię. Ten adapter jest warstwą
migracji, a nie niezależnym drugim zestawem operacji biznesowych.

`form_payload` serializuje wyłącznie pola i opcje dozwolone przez oryginalny
formularz. Zachowuje typy kontrolek, ukryte/wyłączone pola, wybory wielokrotne,
błędy, awatary i ikony, a dla formsetów także management form oraz brak
przeglądarkowego `required` w pustych wierszach. Pliki są wysyłane jako
`FormData`, bez ręcznego nagłówka multipart. Pobieranie pozostaje pod
kontrolowanymi adresami domenowymi, z dotychczasowym prywatnym storage.

Automatyczny zapis zadania wysyła `autosave_fields`, łączy je po stronie
Django z aktualnymi pozostałymi wartościami i szereguje kolejne zapisy.
Nawigacja aplikacji czeka na zakończenie zapisu; błąd zachowuje wpisane dane.
Niezmieniane relacje zachowują wartości również po odebraniu dostępu do epika
lub usunięciu wykonawcy z Workspace, bez dodawania ich do dostępnych wyborów.
Niewysłany tekst komentarza albo wybrane pliki uruchamiają wspólne ostrzeżenie
przed opuszczeniem zadania i zamknięciem karty. Anulowanie pozostawia szkic;
udane wysłanie lub ręczne wyczyszczenie usuwa ostrzeżenie. Zgoda na odrzucenie
zmian formularza dotyczy jednej próby nawigacji, więc błąd pobrania lub blokada
innego formularza nie wyłącza ochrony przy następnej próbie.
Tablica/backlog przekazują istniejące migawki statusu, sprintu, rankingu
oraz sąsiadów. Odrzucony konflikt nie zmienia częściowo kolejności.
Konfiguracja zachowuje kontrolę rewizji i ochronę używanych statusów/typów.

Tagi i Filtry mają jawne serializery `backend/spaces/tag_frontend.py` oraz
`backend/dashboard/filter_frontend.py`. Formularz otwierany nad katalogiem/wynikami
jest w `data.modal`, z autoryzowanym schematem pól i dodatkowymi wartościami
akcji/powrotu. Nieprawidłowy zapis zwraca HTTP 400 z tym samym modalem;
React pokazuje błędy bez zamykania okna. Puste notatki w API zwracają HTTP 400.
Zbiorcze usuwanie tagów wysyła wielokrotny `tag_ids` w FormData i zachowuje
atomową kontrolę wszystkich identyfikatorów. Edycja notatki wymaga jej autorstwa.
Wyniki Filtrów zawsze przechodzą przez bieżące ACL zadań; udostępnienie definicji
nie rozszerza dostępu. Rewizje i blokady nadal obsługują oryginalne widoki.
Starsze nagłówki `X-Filter-Modal` i `X-Filter-Navigation` są usuwane przez
adapter, więc nie mogą przełączyć odpowiedzi API na fragment HTML.
Globalne menu Filtrów, jego picker i wyszukiwanie definicji renderuje
`src/shell`; wyniki API zachowują ten sam zakres widoczności.

Pulpity używają `backend/dashboard/pulpit_frontend.py` i `src/pulpits/`. Odczyt gadżetu
udostępnia liczniki i statusy bieżących `SpaceTask`, bez fragmentu HTML.
Niedostępne źródło zwraca wyłącznie metadane gadżetu i `unavailable`, bez nazwy
prywatnej Przestrzeni ani jej liczników. Udostępnienie pulpitu nie rozszerza ACL
danych. Edycja nadal wymaga autorstwa pulpitu, niezależnie od roli Workspace.
Pulpit domyślny inicjalizuje oryginalny widok Django; usunięte gadżety nie są
odtwarzane podczas kolejnego wejścia.

Wyłącznie `arrange` i `gadget_quick_add` zachowują oryginalne strukturalne JSON:
odpowiednio `{layout, columns: [[id, ...], ...], revision}` i `{kind, revision}`.
Jawna lista `JSON_BODY_VIEWS` przekazuje te dane do walidacji domenowej;
pozostałe formularze JSON nadal przyjmują płaskie wartości. Rewizje, blokady,
pełny zbiór ID i limit 24 chronią zapis przed konfliktem i częściową zmianą.
React cofa niezapisany układ po błędzie i umożliwia odświeżenie danych.
Formularze używają FormData. Adapter usuwa starsze nagłówki `X-Pulpit-Modal`
i `X-Pulpit-Navigation`. Usunięcie przekazuje `invalidated_return_paths`
do istniejącej powłoki przed nawigacją. Stan katalogu gadżetów zachowuje
dotychczasowy klucz sessionStorage, a tabele dotychczasowe klucze szerokości.
Menu boczne Pulpitów, picker i wyszukiwanie w menu pozostają częścią powłoki.

## Dysk, Dokumenty i edytory

`backend/documents/frontend.py` i `src/documents/` obsługują osobno katalogi Dysku oraz
Dokumentów. Dane zawierają autoryzowane metadane, schemat formularza i kontrolowane
URL, bez ścieżek storage. API deleguje upload, przenoszenie, metadane i szablony
do istniejących formularzy/widoków. Zachowuje ograniczenia folderów, sygnatury
plików, limity uploadu, niezależne kopie szablonów oraz prywatne pobieranie.
Plik w koszu udostępnia jedynie przywrócenie i nawigację do jego lokalizacji.
Starsze nagłówki `X-Document-Modal`, `X-Document-Move` i `X-Office-Editor` nie
przełączają API na HTML. Konflikt rewizji tekstu lub metadanych Dokumentów daje
HTTP 409; formularz i wybrany plik pozostają w oknie. Metadane Dysku nie
nadpisują rewizji ani treści pełnego edytora.

Przeciąganie aktywnych plików/folderów korzysta z dotychczasowego `move/` i
walidacji celu; animacja kończy się po potwierdzonym zapisie. Zrzut plików z
systemu otwiera ten sam formularz uploadu. Stan listy/kafelków pozostaje w sesji,
filtry w URL, a zwinięcie panelu dysków pod istniejącym kluczem localStorage.
Podglądy renderują tekst jako tekst, ograniczone dane arkusza/archiwum oraz
kontrolowany obraz/PDF. Poprawiono zgodność rodzaju podglądu ZIP (`archive`)
także w szablonie HTML.

Tworzenie i kopia szablonu zwracają `{redirect, editor_url}`. React rezerwuje
nową kartę w gestach użytkownika; blokada popupu pokazuje link do już utworzonego
pliku, bez ponownego zapisu. Starszy edytor tekstowy zachowuje czyszczenie HTML,
Ctrl+S, rewizje i ochronę szkicu. Pełne edytory są wyspami DOM: ONLYOFFICE
`DocEditor` i odizolowany iframe istniejącego `frontend/board`. React obsługuje
ich powłokę, nazwę, komunikaty, ponowienie zapisu i sprzątanie sesji.
Pobieranie, źródła/callbacki usługi oraz zapis sceny tablicy pozostają pod
oryginalnymi chronionymi endpointami; nie są dopuszczone do proxy API ekranów.
Przy przejściu do pełnego edytora helper nawigacji sprawdza
`AncoreApp.canNavigatePartially`; pełny adres otwiera zwykłą nawigacją.
Szczegóły integracji i uruchomienia: [OFFICE.md](OFFICE.md).

## Zarządzanie Workspace

`backend/workplaces/frontend.py` i `src/workspaces/` obsługują katalog oraz okna
Workspace. Wyszukiwanie, strony i zaznaczenia katalogu pozostają lokalne,
jak w dotychczasowym ekranie. Wybrany Workspace do zarządzania jest niezależny
od aktywnego kontekstu danych. API wskazuje jawne adresy z identyfikatorem
Workspace, a oryginalne widoki sprawdzają dostęp i role przy każdym zapisie.
Tylko jawne przełączenie lub przyjęcie zaproszenia zmienia aktywny Workspace.
Zarządzanie innym dostępnym Workspace może korzystać z API aktywnego kontekstu;
nie udostępnia obcych Workspace ani nie rozszerza ACL Przestrzeni.

Dane obejmują ograniczone schematy formularzy, awatary i dozwolone akcje.
Członek otrzymuje ustawienia tylko do odczytu i skład zespołu, bez wysłanych
zaproszeń, schematu zapraszania i zapisu ustawień. Administrator nie może
zarządzać administratorem/właścicielem ani zapraszać nowych administratorów.
Podpowiedzi osób przez API zawierają nazwę, e-mail i dane awatara; nie zawierają
HTML. Dotychczasowa końcówka podpowiedzi zachowuje HTML dla starszych odbiorców.
Błędny formularz daje HTTP 400 z zachowanym oknem i polami. Nie ma nowego
mechanizmu zaproszeń ani dodatkowej wysyłki e-mail.

Awatar jest odizolowaną wyspą DOM używającą istniejących `AncorePhotoEditors`
i `AncoreWorkplaceAvatars`. Zachowuje 30 ilustracji, wybór automatyczny,
własny obraz i kadrowanie, anulowanie wyboru oraz walidację Django.
Komponent inicjalizuje widget po montażu, a przy odmontowaniu zamyka okna,
odłącza listenery i zwalnia obraz. Formularz zachowuje wybór po błędzie zapisu.
Zmiany nazw nie zmieniają stałego kodu. Usunięcie członka zachowuje istniejące
czyszczenie dostępów Przestrzeni i unieważnienie sesji Office.
Favorites i globalny picker Workspace renderuje trwała powłoka `src/shell`.

## API i interfejs kont

`GET/POST /accounts/api/v1/page/?url=<adres_konta>` ma osobną, zamkniętą
listę adresów: logowanie, rejestracja, profil, dodanie/przełączenie/usunięcie
konta z sesji, zmiana statusu i wylogowanie. Tylko logowanie i rejestracja
działają bez uwierzytelnienia; ogólny `/api/v1/page/` nadal wymaga sesji
i nie udostępnia tras Accounts. Operacje zapisu wymagają CSRF. Walidacja
zwraca JSON 400, brak sesji 401, a niedozwolone przełączenie konta 403.
Odpowiedzi mają `Cache-Control: no-store`; hasła i hashe przełącznika
nigdy nie są serializowane do klienta.

`backend/accounts/frontend.py` dostarcza jawny schemat formularza i dane aktualnego
użytkownika oraz wyłącznie wcześniej uwierzytelnionych kont sesji. Przy błędzie
edycji podsumowanie profilu pokazuje dane z bazy, a szkic pozostaje w formularzu.
`backend/accounts/api.py` deleguje do dotychczasowych widoków i formularzy Django.
Zachowuje rotację sesji i cookie CSRF także wtedy, gdy `LoginView` już zapisał
cookie do odpowiedzi przekierowania. Parametr `next` nadal nie zastępuje
strony „Dla ciebie” po logowaniu. Po rejestracji trzeba się zalogować.

Ekrany `src/accounts/` używają dotychczasowego wyglądu `auth_base.html` oraz
profilu w `core/base.html`. Formularze zachowują szkic po błędach i blokują
równoległy zapis. Edytor profilu korzysta ze wspólnego modalu: Escape, fokus,
inert oraz potwierdzenie odrzucenia zmian. `shared/AvatarControl.tsx` współdzieli
z Workspace izolowany picker i canvas, z osobną pulą ilustracji użytkownika,
polami uploadu i etykietami. `auth.js` pomija kontener Reacta. Po zapisie
profilu lub zmianie tożsamości React wykonuje pełne przejście na otrzymany
adres, aby odświeżyć powłokę, awatar, Workspace i token formularzy. Heartbeat
obecności nadal jest wspólnym serwisem Django/JS.

## Globalne wyszukiwanie, powiadomienia i Sticker

Panele `src/shell/` korzystają z tego samego, uwierzytelnionego API ekranów.
Jawna lista `dashboard.views` obejmuje `global_search`, `notifications` oraz
`notification_action`. Wywołanie przez scoped API utrzymuje Workspace wyszukiwania,
nawet gdy inna karta zmieni aktywny kontekst sesji. Dotychczasowe ACL, limity
wyników, historia ostatnich i semantyka zaproszeń pozostają w usługach Django.

Lista powiadomień dla Reacta zawiera `items`, jawne pola kart, daty, szczegóły,
aktualnie dostępne Workspace z awatarami, liczniki, podpisany `snapshot`
i `next_cursor`; serializer `backend/dashboard/notification_frontend.py` nie renderuje
fragmentów HTML. Starszy endpoint XHR zachowuje kontrakt HTML dla zgodności.
Wszystkie filtry, osobisty odczyt, archiwum, usunięcie i operacje zbiorcze używają
oryginalnego `notification_service`. Każdy odczyt/zapis ponawia kontrolę dostępu.

React obsługuje stan paneli, anulowanie pobrań i limit czasu, menu kart,
potwierdzenia oraz ponowienie błędu. Dzwonek odpytuje serwer co 30 sekund
w widocznej karcie i po powrocie/odzyskaniu połączenia/nawigacji. Nowe wpisy
sygnalizuje przycisk odświeżenia, bez przestawiania listy. Filtry panelu
pozostają wybrane po zamknięciu i ponownym otwarciu. Modal ma osobny host
`app-global-modals`, ale korzysta ze wspólnego `Modal` i `AncoreTaskModals`.
Przejście po odczycie zamyka modal przed uruchomieniem częściowej nawigacji.

Sticker zachowuje klucz `ancore:sticky-note:v2:user:<id>`, treść, geometrię,
przeciąganie i zmianę rozmiaru (także klawiaturą). Brak localStorage nie blokuje
notatki; dane starej notatki bez właściciela nie są przypisywane kontu.
Podmiana treści nie usuwa szkicu. Wyniki wyszukiwania i powiadomienia nie są
zapisywane w localStorage. `global-search.js`, `notifications-panel.js`
i `sticky-note.js` nie są ładowane przy aktywnym korzeniu Reacta; ich szablony
i kontrakty pozostają fallbackiem zgodności. Krótkie komunikaty renderuje `Toasts.tsx`; zachowuje API `showNotification`,
`hideNotification`, deduplikację, czas wyświetlania i bezpieczny tekst.
Heartbeat obecności pozostaje oddzielną usługą.

## API Zasobów v1

Poniższe końcówki dotyczą zarówno `/resources/api/v1/`, jak i
`/workplaces/<slug>/resources/api/v1/`. Frontend otrzymuje i wykorzystuje scoped URL,
aby zmiana aktywnego Workspace w innej karcie nie zmieniała celu zapisu.

| Końcówka | Metoda | Wynik |
| --- | --- | --- |
| `/` | GET | Lista, filtry, sortowanie, scoped URL i paginacja |
| `/` | POST | Utworzenie zasobu; HTTP 201 |
| `/new/` | GET | Puste pola formularza i dozwolone opcje |
| `/<pk>/` | GET | Pola formularza istniejącego zasobu |
| `/<pk>/` | PUT | Pełny zapis edytowalnych pól zasobu |
| `/<pk>/delete/` | POST | Usunięcie zasobu |

GET listy obsługuje `q`, `kind`, `status`, `assignee`, `sort`, `page_size` i `page`
z tymi samymi ograniczeniami co dotychczasowy katalog. Zapis przyjmuje płaski
obiekt `application/json` i nagłówek `X-CSRFToken`. Brak sesji zwraca JSON 401,
brak dostępu 403 lub 404, błędna metoda 405, a walidacja JSON 400 z `message`,
`errors` oraz aktualną definicją pól. Odpowiedzi nie zawierają HTML i mają
`Cache-Control: no-store`. Dla API odrzucony CSRF także zwraca JSON;
pozostałe formularze zachowują standardową odpowiedź Django.

`backend/resources/services.py` współdzieli zakres danych, katalog i zapis między
widokami HTML a API. Każdy obiekt jest ograniczony jednocześnie przez
`workspace_owner(request)` i `request.workplace`. `ResourceForm` nadal
waliduje osobę, typ, status, daty i unikalny numer ewidencyjny. Pola właściciela,
Workspace i autora nie są edytowalne przez klienta; autorem pozostaje faktyczny
`request.user`. Nie zmieniono modeli ani migracji.

## Powłoka i nawigacja JSON

`backend/core/shell.py` jawnie serializuje kontekst powłoki: konto, aktywny Workspace,
listę rzeczywistych członkostw, kolekcje z aktualnym ACL, ulubione, adresy,
tryb zarządzania i menu edytora pulpitu. Bootstrap jest przekazywany przez
bezpieczny `json_script`. Nie serializuje modeli ani fragmentów HTML.

`GET /api/v1/navigation/?url=...` i scoped odpowiednik zwracają `page`, `shell`,
`csrf_token` oraz komunikaty Django. Korzystają z tego samego zamkniętego
rejestru widoków i serializerów co API ekranów. Żądanie ponawia autoryzację
Workspace i domenową kontrolę dostępu. `GET /api/v1/shell/?url=...` odświeża
same kolekcje/Favorites bez resetowania szkicu strony. Oba endpointy wymagają
sesji, obsługują tylko GET i zwracają `Cache-Control: no-store`.

`src/shell/navigation.ts` udostępnia zgodne `AncoreApp.navigate`,
`canNavigatePartially` i `invalidateManagementReturn`. Pobiera JSON, anuluje
poprzednie żądanie, czeka na `ancore:before-navigate`/`waitUntil`, ładuje chunk
oraz brakujące style, po czym montuje Reacta w kontenerze strony. Nie parsuje
HTML ani nie wykonuje skryptów z odpowiedzi. Błąd pozostawia aktualny ekran
z komunikatem i możliwością ponowienia. Konto, Workspace lub inny hash bundla
w odpowiedzi wymagają pełnego przeładowania. Logowanie, przełączanie tożsamości,
pliki, nowe karty i pełne edytory zachowują własne przepływy.

Wstecz/Dalej odtwarza ekran oraz przewinięcie. `setPageLocation()` łączy lokalne
zmiany query/hash (np. Zasoby, Dokumenty, zakładki zadania i zarządzanie Workspace)
z tą samą historią. Minimalne menu zarządzania zachowuje zagnieżdżony powrót,
query/hash, przewinięcie oraz klucze `ancoreManagementReturn` w historii
i `sessionStorage`, w zakresie konta i Workspace. Usunięty cel jest unieważniany,
a 404 przy powrocie uruchamia domyślny katalog.

`Sidebar.tsx`, `Collections.tsx`, `WorkspaceMenu.tsx` i `CollectionPicker.tsx`
renderują wspólne klasy i tokeny. Zachowują klucze localStorage szerokości,
zwinięcia oraz grup/Favorites. Kolekcje korzystają z typowanych wyników
`spaces:search`, `pulpits:search`, `filters:lookup` przez API ekranów, z debounce,
anulowaniem, błędem/ponowieniem, klawiaturą i powrotem fokusu. Gwiazdka
odświeża menu bez utraty szkicu/filtrów strony. Formularze z menu mają osobny
host `app-shell-modals` i wspólny `FormDialog`/`Modal`.

Favorites nadal zapisują istniejące widoki `workplaces.views`, walidujące
członkostwo, dozwolone klucze i kompletny, unikalny porządek. Kontrakt Reacta
zwraca dane zamiast HTML. Stan jest osobisty w obrębie Workspace. Przeciąganie
obsługuje wskaźnik; na dotyku uchwytem jest ikona, więc pozostała część wiersza
pozwala przewijać menu. Alt+strzałki i dostępne klawiaturą akcje są alternatywą.
Błąd zapisu zachowuje potwierdzoną kolejność. Brak localStorage nie blokuje UI.

`layout.js`, `space-navigation.js`, `filter-navigation.js`, `pulpit-navigation.js`,
`space-picker.js` i `notifications.js` nie są ładowane z powłoką Reacta.
Pozostają tylko dla szablonów zgodności. Historyczne Tasks/Kanban nie otrzymały
nowych tras ani operacji. Nowe funkcje rozwijaj w istniejących komponentach
React i usługach Django, z aktualnym ACL oraz wspólnym systemem UI.
