# Uruchamianie, weryfikacja i utrzymanie projektu

## Doładowywanie backlogu i sprintów (28.10.2026)

Backlog oraz każdy otwarty sprint wczytują niezależnie po 20 zadań i używają
tego samego paska „Pokaż więcej” co Lista zadań. Nagłówki pokazują pełne
liczniki po filtrach; brak dolnego paska numerów stron. SQL ogranicza grupy
po ACL, filtrowaniu i sortowaniu. Planowanie zbiorcze, przeciąganie i menu
kolejności używają tego samego wczytanego zakresu, także powyżej 100 pozycji;
jedna operacja zbiorcza nadal obejmuje najwyżej 100 zadań.
[Kontrakt API](FRONTEND.md#doładowywanie-listy-zadań-przestrzeni),
[UI](UI.md#dolny-pasek-stron-przestrzeni), [planowanie](SPACES.md#planowanie-w-backlogu).

Sprawdzono 105 różnych testów PostgreSQL na izolowanych bazach przez
`scripts/run_tests.py`: `spaces.test_backlog_window`, `spaces.test_backlog_planning`,
`spaces.test_backlog_drag`, `spaces.test_item_query`, `spaces.test_list_window`,
`spaces.test_write_access`, `spaces.test_urls` i `core.test_frontend`.
W końcowym przebiegu przeszły 93 testy; 12 niezmienionych testów listy przeszło
we wcześniejszym przebiegu. Ich ponowne równoległe wykonanie przerwano z powodu
wolnych zapytań ACL; nie zgłoszono błędu ani blokady bazy. Runner zakończył się
wynikiem `Ran 93 tests — OK`, a bazy testowe i procesy zostały posprzątane.
Wcześniejszą asercję cofniętego dostępu poprawiono, aby uwzględniała kanoniczne
przekierowanie przed 404; ponowny test przeszedł.
Przeszły 193 testy frontendu, build TypeScript, Django check oraz kontrola
indeksu i diff. Testy callbacków obejmują niezależność grup, zachowanie
zaznaczeń i URL, błędy/ponowienie oraz reset zakresu przez filtry i sortowanie.

Playwright z lokalnym Chrome i osobną bazą PostgreSQL potwierdził
20→40→125, sprint 20→25, pełne liczniki, niezależność grup, zachowanie
zaznaczenia, zwinięcia, fokusu i przewijania, odświeżenie rozszerzonego URL,
reset filtrów/sortowania, błąd HTTP 503 i ponowienie, stan pusty oraz sprint
z wyłącznie ukończonymi zadaniami. Wykonano zmianę kolejności i przeniesienie
zbiorcze zadania ponad dawną granicą 100, sprawdzono Scrum/Kanban,
zwykły/scoped adres, ponowne wejście oraz referencyjną Listę zadań.
Przy 1440×1000, 1024×900, 390×844 i 320×844 kontrolka mieści się w ekranie;
jej typografia, tło i wysokość odpowiadają wzorcowi listy. Pierwszy render
bez JavaScriptu zachowuje niezależne linki doładowania (60→80 wierszy).
Nie było błędów wykonania JavaScriptu; jedyny błąd HTTP 503 zasymulowano celowo.
Łącznie przeszło 16 scenariuszy przeglądarki; po korekcie opisu sprintu
powtórzono pierwszy render w świeżym procesie. Serwer QA zatrzymano,
tymczasową bazę, storage i dane sesji usunięto. Plugin Browser był niedostępny,
użyto zainstalowanego Playwright/Chrome. Nie testowano Safari, Firefoksa ani
wdrożenia produkcyjnego. Modele i migracje pozostały bez zmian.

## Tablica bez dolnego paska stron (28.10.2026)

Tablica Przestrzeni w React i pierwszym renderze Django nie pokazuje zakresu
wyników ani paginacji. Odczyt oraz zmiana kolejności obejmują wszystkie
dostępne zadania po filtrach, także ponad dawny limit 100; `page` jest ignorowany.
Backlog doładowuje grupy przez „Pokaż więcej” (opis poniżej i w aktualnym
kontrakcie API); oś czasu zachowuje paginację.

Przeszły 72 testy PostgreSQL na izolowanych bazach przez `scripts/run_tests.py`:
`spaces.test_board_order`, `spaces.test_list_window`, `spaces.test_item_query`,
`spaces.test_backlog_drag` i `core.test_frontend`. Obejmują 163 zadania,
Scrum/Kanban, zwykłe/scoped adresy, prywatnych rodziców, filtry, sortowanie,
przestawianie ponad dawną granicą strony oraz zachowane stronicowanie innych
widoków. Przeszły też 182 testy frontendu, build z TypeScriptem i Django check.

Playwright/Chrome na jednorazowej bazie QA potwierdził brak paska przy
1440×1000, 390×844 i 320×844, powrót z referencyjnego Backlogu,
125 kart przy starym `page=2`, sortowanie, odświeżenie, zmianę kolejności,
pusty wynik, błąd zapisu i udane ponowienie. Sprawdzono również pierwszy
render bez JavaScriptu. Nie było błędów wykonania aplikacji; jedyny błąd
HTTP 503 był celowo zasymulowany. Plugin Browser był niedostępny.
Nie sprawdzano Safari/Firefox ani wydajności tablic z tysiącami kart;
pełny odczyt zwiększa rozmiar odpowiedzi i DOM wraz z liczbą zadań.
Indeks i kontrola diff przeszły. Modele i migracje pozostały bez zmian.

## Doładowywanie listy zadań (28.10.2026)

Lista Przestrzeni wczytuje po 20 zadań na status, z pełnymi licznikami
i paskiem „Pokaż więcej”. Backlog korzysta z tego samego mechanizmu
osobno dla sprintów i kolejki; oś czasu zachowuje paginację;
tablica pokazuje wszystkie pasujące zadania bez dolnego paska stron.
[Kontrakt API](FRONTEND.md#doładowywanie-listy-zadań-przestrzeni),
[wygląd i stany](UI.md#dolny-pasek-stron-przestrzeni).

Przeszło 130 różnych testów PostgreSQL na izolowanych bazach przez
`scripts/run_tests.py`: `spaces.test_list_window`, `spaces.test_item_query`,
`spaces.test_urls`, `spaces.test_independent_tasks`, `spaces.test_board_order`,
`spaces.test_backlog_drag`, `core.test_frontend`, `spaces.test_summary`
i `spaces.test_issue_types`. Obejmują zwykłe/scoped API, sortowanie, filtry,
prywatnych rodziców, Workspace, pełne liczniki, 20/21, ponad 100 zadań,
powrót po utworzeniu i pierwszy render. Przeszły 182 testy frontendu,
build TypeScript, Django check, kontrola indeksu oraz diff.

IAB na osobnej bazie i fikcyjnych kontach potwierdziła 20→40→45,
20→21, niezależność grup, zaznaczenie i zwinięcie podczas doładowania,
odświeżenie rozszerzonego URL, reset przez filtr, ponowne wejście, pustą listę
oraz referencyjny Backlog. Przy 1440×1000, 390×844 i 320×700 obejrzano
rzeczywisty ekran. Na telefonie poprawiono przewijanie samych wierszy,
żeby pasek był w całości widoczny. Enter zachowuje fokus na końcowym pasku
i pozycję przewijania. Wstrzymanie serwera QA sprawdziło timeout i udane
ponowienie bez utraty danych; test regresji sprawdza polski komunikat timeoutu.
Nie stwierdzono błędów wykonania aplikacji w końcowym widoku.
Nie testowano Safari, Firefoksa ani wdrożenia produkcyjnego.
Nie zmieniono modeli ani migracji.

## Katalog gadżetów z rzeczywistymi podglądami (28.10.2026)

Pulpity i Podsumowanie używają `shared/WidgetCatalog.tsx`: miniatury rzeczywistych
komponentów, opisy, „Dodaj”/„Dodano”, wyszukiwanie i przewijana lista.
Pulpity oznaczają dane przykładowe; Podsumowanie korzysta z bieżących danych
Przestrzeni. `inert` wyłącza kontrolki w miniaturach, a wspólna pułapka fokusu
je pomija. Nie zmieniono rodzajów gadżetów, API ani modeli.

Przeszły build TypeScript, 164 testy frontendu i kontrola składni `tasks.js`.
Playwright z lokalnym Chrome wykonał 12 sprawdzeń na osobnej bazie QA
(plugin Browser niedostępny): rzeczywisty wygląd i rozmiar okna, wyszukiwanie
z polskimi znakami i bez, stan pusty, ponowne dodanie, Escape/fokus, anulowanie,
zapis/reload, komplet podglądów Podsumowania, „Dodano”, pomijanie kontrolek
`inert`, przewijanie długiej listy i stała wyszukiwarka. Sprawdzono 1440, 390
i 320px, obejrzano zrzuty; brak poziomego przepełnienia i błędów konsoli.
Serwer QA zatrzymano, tymczasową bazę i storage usunięto.
Nie testowano Safari ani Firefoksa.

## Pulpity ze wspólną siatką Podsumowania (28.10.2026)

Pulpity używają `shared/DashboardCanvas.tsx` wspólnie z Podsumowaniem:
siatka 12 kolumn, przeciąganie, zmiana rozmiaru, menu i klawiatura.
Dodawanie/usuwanie i geometria są szkicem zatwierdzanym przez „Zapisz układ”
lub odrzucanym przez „Anuluj”. Katalog jest modalem; tworzenie pulpitu nie ma
starego wyboru układu kolumn. [UI](UI.md#15-pulpity), [API](FRONTEND.md).
Migracja `dashboard.0008_dashboard_gadget_grid` przenosi istniejące kolumny
bez utraty gadżetów i konfiguracji. Została zastosowana także lokalnie.

Przeszły 134 testy PostgreSQL na osobnych bazach: `dashboard.test_pulpit_grid`,
`dashboard.test_pulpits`, `dashboard.test_pulpit_catalog`,
`dashboard.test_pulpit_preferences`, `dashboard.test_pulpit_roles`,
`dashboard.test_default_pulpit`, `dashboard.test_pulpit_editor`,
`core.test_pulpit_frontend`, `spaces.test_dashboard`, `spaces.test_summary`.
Sprawdzono transakcję szkicu, rewizje, granice, kolizje, role i źródła danych,
scoped API oraz migrację wszystkich wcześniejszych układów. Przeszły 164 testy
frontendu (`pnpm --dir frontend/app test`), build z TypeScriptem,
format zmienionych plików, Django check, zgodność modeli i migracji,
indeks oraz `git diff --check`.

Playwright z lokalnym Chrome wykonał 22 sprawdzenia na osobnej bazie QA;
plugin Browser był niedostępny. Potwierdzono nowe/domyślne/puste pulpity,
dodawanie/usuwanie, wskaźnik i klawiaturę, granice, menu, anulowanie,
zapis/reload/ponowne wejście, konfigurację, 503 i ponowienie, konflikt dwóch
okien i odrzucenie szkicu, role członka/obserwatora, scoped i zwykłe adresy,
pierwszy render bez JavaScriptu oraz referencyjne Podsumowanie. Szerokości:
1440, 1024, 390 i 320px. Końcowy formularz tworzenia sprawdzono po usunięciu
wyboru kolumn. Zrzuty obejrzano; brak przepełnienia, błędów wykonania
i nieoczekiwanych błędów konsoli. Serwery QA zatrzymano, bazę i storage usunięto.
Nie testowano Safari, Firefoksa ani wdrożenia produkcyjnego.


## Stała pozycja opcji gadżetu Przestrzeni (28.10.2026)

Panel pozycji i rozmiaru zachowuje współrzędne z chwili otwarcia, gdy
zmiany parametrów przesuwają kafelek. Wariant wspólnej warstwy jest opcjonalny;
pozostałe menu nadal śledzą kontrolkę. [Kontrakt](UI.md).

Przeszły 152 testy frontendu, w tym 8 regresji rzeczywistego
`dropdown-layer.js`: stała pozycja, domyślne śledzenie, clipping, ponowne
otwarcie, viewport, Escape/fokus i sprzątanie obserwatorów. Przeszły build
TypeScript, składnia JS, formatowanie i indeks. IAB na osobnej bazie QA
potwierdziła niezmienione współrzędne po serii zmian szerokości, wysokości
i położenia, także po przesunięciu kafelka poza ekran. Sprawdzono 1440×1000,
390×844 i 320×568, ponowne otwarcie, Escape oraz referencyjne menu filtrowania
listy zadań. Brak poziomego przepełnienia, błędów i ostrzeżeń konsoli.
Nie sprawdzano pozostałych przeglądarek ani wdrożenia produkcyjnego.

## Filtrowanie pulpitu Przestrzeni (28.10.2026)

Podsumowanie współdzieli `ItemFiltering` z zadaniami i otrzymuje komplet
opcji filtrowania przez istniejący page API. Pierwszy render korzysta
z wariantu `filters_only` wspólnego formularza. [Opis UI](UI.md).

Wykonano 55 testów PostgreSQL: `spaces.test_summary`, `spaces.test_dashboard`,
`spaces.test_backlog_drag`, `core.test_space_settings_frontend` oraz
`spaces.test_item_query`. Przeszło 127 testów frontendu (w tym 6 nowych
regresji wspólnego menu), build TypeScript, kontrola Django i indeksu.
IAB na odizolowanych danych QA przy 1440×1000 i 390×844 potwierdziła
łączenie typu/priorytetu/wykonawcy, aktualizację danych, pusty wynik,
czyszczenie, zachowanie filtrów po odświeżeniu i zgodność z menu listy zadań.
Bez błędów konsoli i poziomego przepełnienia. Pozostałych przeglądarek
oraz wdrożenia produkcyjnego nie sprawdzano; nie zmieniono modeli ani migracji.

## Konfigurowalny pulpit Przestrzeni (28.10.2026)

Podsumowanie ma osobisty zapis siatki, katalog istniejących gadżetów,
przesuwanie i zmianę rozmiaru, szkic z zapisem/anulowaniem oraz obsługę
konfliktów rewizji. [Funkcje](SPACES.md), [UI](UI.md), [API](FRONTEND.md).
Wymagana migracja: `spaces.0003_space_dashboard_layout`.

Sprawdzenia regresji:

```sh
.venv/bin/python scripts/run_tests.py spaces.test_dashboard spaces.test_summary core.test_space_settings_frontend core.test_schema_baseline
pnpm --dir frontend/app test
pnpm --dir frontend/app build
python scripts/update_code_index.py --check
```

Wykonano 32 testy PostgreSQL i 121 testów frontendu, build TypeScript,
kontrole Django/migracji i indeksu. Siatka jest testowana także przez 400
deterministycznych zmian z niezależną kontrolą granic i kolizji.
Przeglądarka IAB na odizolowanej bazie QA potwierdziła zapis i ponowne wejście,
przeciąganie przez inne kafelki, resize wskaźnikiem i klawiaturą, dodawanie,
usuwanie, wyszukiwanie/pusty katalog, Escape, anulowanie, pusty zapisany pulpit,
konflikt dwóch okien oraz odczyt aktualnej wersji. Sprawdzono 1440×1000,
bieżący widok 630px oraz 390×844, brak poziomego przepełnienia i błędów JS.
Ekran referencyjny: Pulpit domyślny. Porównanie z dostarczonym ekranem obejmowało
nawigację i polskie nazwy, font/skalę, kolory i ikony, zawartość wykresów,
ramki/odstępy oraz mobilną kolejność. Celowo dodano toolbar i kontrolki edycji;
domyślny układ jest ciaśniejszy, a na telefonie jednokolumnowy. Nie tworzono
nowego kierunku wizualnego ani bitmapowej makiety. Nie sprawdzano pozostałych
przeglądarek ani wdrożenia produkcyjnego.

## Cztery poprawki po pełnym przeglądzie (25.10.2026)

Zmiana aktywnego administratora/członka na gościa unieważnia sesje Office
Dysku i Dokumentów, także podpisane callbacki współautorów; pozostałe zmiany
ról zachowują klucze. [Dostęp zespołu](TEAMWORK.md#dodawanie-osób-i-linki-do-dołączenia).
Potwierdzenie zapisu treści korzysta z istniejących rekordów callbacków
(`save_receipt`), a przeniesienie pliku/folderu lub zapis metadanych nie
zwalnia oczekiwania. [Kontrakt zapisu](OFFICE.md#zapis-i-granice-dostępu).
Kilka warunków tekstowych filtra pozostaje w trybie zaawansowanym bez utraty
kryteriów. [Filtry](FILTERS.md). Kalendarz przesyła jednoznaczne chwile,
zachowuje niezmienione sekundy/wariant DST oraz kalendarzowe daty wydarzeń
całodniowych. Nowe nieistniejące i dwuznaczne godziny wymagają poprawienia.
[Kontrakt frontendu](FRONTEND.md#zakres-migracji).

Przeszły **1272/1272 testy Django** przez `scripts/run_tests.py --parallel 4`
na izolowanych bazach i storage oraz **93/93 testy frontendu**. Dodano 9 metod
regresji Django i 21 przypadków frontendu obejmujących rzeczywiste endpointy,
callbacki React oraz adapterów. Przeszły build z TypeScriptem, Prettier,
kontrola Django, zgodność modeli i migracji, składnia JS, indeks kodu, lokalne
linki dokumentacji oraz diff. Modele i migracje pozostają bez zmian.

Plugin Browser był niedostępny. Playwright z lokalnym Chrome i osobną bazą QA
sprawdził 13 scenariuszy: UTC/Warszawę/Nowy Jork, niezmienione godziny i daty
całodniowe po zapisie/reloadzie, tworzenie wydarzeń, walidację DST, kontrolowany
błąd POST i ponowienie, pełne kryteria filtra i pusty wynik, ekran referencyjny
konfiguracji, ponowne wejście, przeniesienie podczas zapisu, nadal aktywny
limit potwierdzenia, rzeczywisty podpisany callback i zmianę roli na gościa.
Sprawdzono 1440, 1024, 390 i 320 px. Zrzuty obejrzano; nie wykryto błędów
wykonania, nieoczekiwanych błędów konsoli ani przepełnienia zmienionych ekranów.
Usługę ONLYOFFICE zastępowała atrapa DocsAPI/force-save i pobrania wyniku;
kontrole sesji, zapis pliku i callback działały w rzeczywistym Django.
Nie uruchamiano żywego ONLYOFFICE, wdrożenia Docker, Safari ani Firefoksa.
Serwer QA zatrzymano, a jego tymczasową bazę i storage usunięto.

## Ponowienia odczytu i kolejka edytora po przeglądzie (25.10.2026)

Po udanym POST błąd następującego GET nie powtarza komentarza, podzadania,
wpisu czasu ani notatki tagu. Interfejs potwierdza zapis i pozwala ponowić
sam odczyt; błąd POST nadal zachowuje szkic. Autosave pamięta zaległy GET
oraz pomija powtórne zdarzenie `change` niezmienionego tekstu po blur.
[Kontrakt i zachowanie](FRONTEND.md#api-ekranów-v1).

Kolejka ONLYOFFICE w React i adapterze zapisuje nowszą generację po
potwierdzeniu wcześniejszej, bez równoległych żądań i automatycznej pętli
po błędzie zapisu. [Granice zapisu](OFFICE.md#zapis-i-granice-dostępu).
Gość ma zwykły tytuł bez edycji, także w pierwszym renderze Django.
Pełny edytor jawnie wyłącza nieobecną powłokę React; istniejący `layout.js`
usuwa zasłonę ładowania po reloadzie i obsługuje anulowane wyjście.
Bootstrap React samej strony pozostaje aktywny. [Standard UI](UI.md#katalog-i-edytor-dokumentów).

Przeszło **1263/1263 testów Django** przez `scripts/run_tests.py --parallel 4`
na izolowanych bazach i storage oraz **72/72 testy frontendu**. Dodano cztery
regresje Django i 45 przypadków frontendu, obejmujących rzeczywiste callbacki,
hooki, render React i lifecycle adaptera. Przeszły build aplikacji z TypeScriptem,
Prettier, kontrola Django, składnia JS, indeks, lokalne linki i diff.
Modele i migracje pozostały bez zmian.

Plugin Browser był niedostępny. Chrome/Playwright na osobnej bazie i fikcyjnych
kontach sprawdził 13 scenariuszy: zapis i kontrolowany błąd odczytu, ponowienie
samego GET, zachowanie szkicu po błędzie POST, komentarz z plikiem, podzadanie,
czas, notatkę tagu, prawa gościa w Dysku/Dokumentach/tablicy, zmianę nazwy,
Escape, reload, kolejkę edytora, pusty katalog i konfigurację referencyjną.
Sprawdzono 1440, 1024, 390 i 320 px, długą nazwę oraz pierwszy render bez JS.
Zrzuty obejrzano; brak nieoczekiwanych błędów JS, ostrzeżeń konsoli i przepełnienia.
Kontrolowane odpowiedzi 503 były częścią testu. ONLYOFFICE sprawdzono przez
atrapę DocsAPI i odpowiedzi zapisu/stanu; nie uruchamiano żywej usługi ani
wdrożenia Docker. Safari i Firefox nie były testowane.
Serwer QA zatrzymano, a jego tymczasową bazę i storage usunięto.

## Cztery poprawki po przeglądzie projektu (25.10.2026)

Zabezpieczono właściciela zadania w obu endpointach członkostwa oraz przy
usuwaniu nadmiarowego rekordu przez sygnał. Operacja zadania blokuje się
przed oczekiwaniem na autosave; błąd zachowuje szkic komentarza i pozwala
ponowić zapis. Tablica gościa potwierdza gotowość bez zapisu. Gwiazdki Dysku,
folderów i Dokumentów należą do zalogowanej osoby. Migracja
`documents.0003_personal_document_stars` zachowuje dawne oznaczenia właściciela;
opis upgrade i cofnięcia: [Baza danych](DATABASE.md#osobiste-gwiazdki-dokumentów-25102026).

Przeszło **1259/1259 testów Django** przez `scripts/run_tests.py --parallel 4`
na izolowanych bazach i storage, w tym 17 nowych regresji uprawnień,
osobistych oznaczeń oraz migracji forward/reverse. Przeszło również
**27/27 testów frontendu**, oba buildy (aplikacja z TypeScriptem i tablica),
Prettier, kontrola Django, zgodność modeli i planu migracji, indeks oraz diff.

Plugin Browser był niedostępny. Chrome/Playwright na osobnej bazie QA i
fikcyjnych kontach sprawdził blokadę podczas opóźnionego autosave, pojedynczy
komentarz po reload, szkic po błędzie autosave i wysyłki oraz udane ponowienia;
osobiste gwiazdki w sesjach właściciela, członka i gościa; foldery; podgląd
tablicy gościa przez ponad 20 sekund bez błędu i żądań zapisu. Sprawdzono
1440, 1024, 390 i 320 px, ponowne wejście, stany puste/błędu oraz referencyjne
okno konfiguracji Przestrzeni. Zrzuty obejrzano. Brak nieoczekiwanych błędów
JS, ostrzeżeń konsoli i przepełnienia strony zadania; odpowiedzi 503 były
kontrolowanymi awariami w teście. Nie sprawdzano żywego ONLYOFFICE,
wdrożenia Docker, Safari ani Firefoksa.
Serwer QA zatrzymano, a tymczasową bazę i storage usunięto.

Lokalny plan zawierał wyłącznie nową migrację Dokumentów. Po zgodzie użytkownika
wykonano świeży prywatny `pg_dump` w `.cache/database-backups/`, sprawdzono listę
archiwum oraz SHA-256 i zastosowano `documents.0003_personal_document_stars`.
Porównanie przed/po potwierdziło zachowanie rekordów, ich pozostałych pól
i dawnych oznaczeń właściciela. Nie ma zaległych migracji ani rozbieżności
modeli; kontrola Django przeszła.

## Granice uploadu, role zadania i północ w Kalendarzu (25.10.2026)

Publiczny limit Nginx wynosi 225 MiB i mieści obsługiwaną paczkę 20 plików
po 10 MiB, pola formularza oraz narzut multipart. Walidacja plików pozostaje
w Django; wewnętrzny listener ONLYOFFICE zachowuje 25 MiB.
[Konfiguracja proxy](PRODUCTION.md). Test `core.test_production` porównuje
limit z rzeczywistą granicą formularza i rozmiarem zakodowanego multipart.

Zakładka „Członkowie” zadania przekazuje uprawnienie zarządzania rolami do
wspólnej tabeli. Administrator zmienia członka w obserwatora i odwrotnie;
chronione wiersze właściciela i administratorów nadal nie mają jego operacji.
[Zasady](TEAMWORK.md#dostęp-do-niezależnych-zadań-przestrzeni-10102026).
Kalendarz traktuje koniec wydarzenia jako wyłączny: koniec o północy nie
tworzy pozycji następnego dnia. Punktowe terminy zadań zachowują swój dzień.
[Frontend i testy](FRONTEND.md#budowanie-i-uruchamianie).

Przeszło **1242/1242 testów Django** przez `scripts/run_tests.py --parallel 4`
na izolowanych bazach i storage oraz **21 testów frontendu**, w tym regresje
rzeczywistego renderu TaskPage dla czterech ról i dat kalendarza z DST.
Build z TypeScriptem i Prettier przeszły. Browser plugin był niedostępny;
Playwright z lokalnym Chrome na osobnej bazie QA sprawdził zmianę ról,
zapis i reload, ochronę pozostałych ról, kalendarz miesiąca i dnia, terminy
punktowe, całodzienne, pusty filtr, kontrolowany błąd zapisu i ponowienie,
ponowne wejście oraz referencyjne ustawienia Przestrzeni. Szerokości:
1440, 1024, 390 i 320 px. Zrzuty obejrzano. Nie wykonywano wdrożenia ani
testu żywego Nginx (brak daemona Docker), ONLYOFFICE, Safari lub Firefoksa.
Kontrola Django, aktualność indeksu, lokalne linki zmienionej dokumentacji
i `git diff --check` przeszły. Serwer QA zatrzymano, jego bazę i storage usunięto.

## Poprawki po przeglądzie i dostęp Workspace (25.10.2026)

Usunięto zaproszenia e-mail: model, trasy bezpośrednie i delegowane API,
wysyłkę SMTP, oczekujące powiadomienia i ich interfejs. Workspace zachowuje
ręczne dodawanie istniejących kont oraz linki do dołączenia. Picker wybiera
identyfikator konta, ma minimum 2 znaki i limit 10; formularz nie eksportuje
katalogu użytkowników. Bez JS działa dokładne ID Ancore. Walidacja odrzuca
same adresy e-mail, nieaktywne/niejednoznaczne konta i niedozwolone role.
Administrator nie zarządza również nieaktywnym administratorem.
[Zasady i migracje](TEAMWORK.md), [schemat](DATABASE.md).

Naprawiono także XSS w potwierdzeniach dostępu (`messageText`), blokowanie
zapisu wszystkich osób po dodaniu gościa, podgląd TEXT przez gościa w obu
frontendach, walidację TXT/CSV UTF-16 oraz odświeżenie mountu konfiguracji
backupu po rekonfiguracji. Nieaktywny gość nie blokuje pozostałych ról.
Wygasłe zaproszenia e-mail nie mogą już wywoływać konfliktu ponownej wysyłki,
ponieważ cały ten mechanizm został usunięty.

Na izolowanych bazach i storage przez `scripts/run_tests.py --parallel 4`
przeszło **1241/1241 testów Django**. Dodano regresje uprawnień, braku starych
tras i źródeł e-mail, ręcznego dodawania (również równoczesnego), migracji
istniejących danych, TXT/CSV i konfiguracji backupu. Dostosowano nieaktualne
fixture/asercje do jawnego tworzenia Workspace, istniejących pulpitów
domyślnych oraz pełnego stanu migracji; produkcyjne zachowanie nie zostało
zmienione w celu dopasowania do starych testów.

Przeszły build/TypeScript, **12 testów frontendu**, Prettier, składnia JS
oraz szablonów, kontrola Django, zgodności migracji, indeksu i diffu.
Browser plugin nie był dostępny. Chrome/Playwright przy 1440×900 i 390px
sprawdził **24 scenariusze** na osobnej bazie: wybór istniejącego konta,
błąd/ponowienie zapisu, role, brak grantów przez e-mail, linki i ich cofnięcie,
wygaśnięcie, odczyt gościa, pierwszy render i rzeczywiste dodanie bez JS,
ponowne wejście oraz trzy okna podatne wcześniej na XSS. Zrzuty obejrzano;
brak nieoczekiwanych błędów JS. Bazę i storage QA usunięto, serwer zatrzymano.
Dodatkowe dwa scenariusze Chrome potwierdziły kopiowanie linku przy braku
Clipboard API (typowe dla HTTP): React i adapter zaznaczają adres i pokazują
instrukcję ręcznego kopiowania, bez błędu JS. Po ochronie starszych formularzy
z domeną ponowiono 23 testy linków, ręcznego dodawania i migracji — przeszły.

Migracje `dashboard.0007_remove_workspace_invitations` oraz
`workplaces.0005_remove_email_invitations` zastosowano lokalnie po wykonaniu
prywatnego `pg_dump` w `.cache/database-backups/`, walidacji archiwum oraz
zapisaniu SHA-256. Plan zawierał wyłącznie te dwie migracje. Istniejące
członkostwa i dane biznesowe są zachowane; stare linki z domeną unieważniono.
Nie wykonywano wdrożenia, rzeczywistego odzyskiwania produkcji ani testu żywego
ONLYOFFICE. Konfigurację Compose sprawdzono bez działającego demona Docker;
Safari i Firefox nie były testowane.

Przed podziałem zmian na commity ponowiono pełny zestaw: **1241 testów Django**
na izolowanych bazach i storage oraz **12 testów frontendu** — wszystkie przeszły.
Ponownie sprawdzono build z TypeScriptem, Prettier, kontrolę Django, zgodność
modeli i historii migracji, składnię skryptu runtime, indeks kodu oraz diff.
Sprawdzono 1024 lokalne odnośniki dokumentacji; nie było brakujących plików.
Podczas tej kontroli nie ponawiano prób UI w przeglądarce ani testu wdrożenia.


## Osobisty domyślny Workspace (25.10.2026)

Katalog Workspace pozwala ustawić/zmienić/usunąć osobisty wybór startowy.
Po logowaniu otwiera się „Dla ciebie” wskazanego, nadal dostępnego Workspace;
zwykłe przełączanie nie zmienia preferencji. Oczekujące zaproszenie zachowuje
swój przepływ. [Mechanizm](MECHANISMS.md#1-tożsamość-sesja-i-obecność).

Migracja `accounts.0002_user_default_workplace` dodaje opcjonalną relację
`SET_NULL`, bez zmiany istniejących danych. Zastosowano ją lokalnie po backupie
w `.cache/database-backups/`; plan obejmował wyłącznie tę migrację.
Na osobnej bazie i storage przeszło **277 testów Django**: `workplaces`,
`accounts`, `core.test_workspace_frontend`, `core.test_navigation_frontend`,
`core.test_schema_baseline`, `dashboard.test_for_you`. Nowe testy obejmują
HTML i zwykłe/scoped API, osobiste uprawnienia, CSRF, utratę dostępu, usunięcie
Workspace, logowanie z nowej/istniejącej sesji i migrację istniejących kont.
Przeszły build z TypeScriptem, 10 testów frontendu, format, kontrola Django,
migracji, indeksu, lokalnych linków dokumentacji i `git diff --check`.

Plugin Browser był niedostępny; Playwright z lokalnym Chrome na osobnej bazie
QA (`http://127.0.0.1:8783`) sprawdził katalog referencyjny i zmieniony,
1440×900, 1024×768, 390×844 i 320×568: menu, ustawienie/zamianę/usunięcie,
przeładowanie i ponowne wejście, kontrolowany błąd zapisu i ponowienie,
logowanie do domyślnego Workspace z nowej sesji i po ręcznym przełączeniu,
niezależność wyborów właściciela/członka, pusty katalog i natywny POST bez JS.
Zrzuty obejrzano. Brak nieoczekiwanych błędów konsoli/wykonania i nieudanych
żądań; szeroka tabela zachowuje własne przewijanie. Bazę i storage QA usunięto.
Nie sprawdzano Safari/Firefox ani pełnego zestawu testów repozytorium.

## System Workspace inspirowany Huly (25.10.2026)

Jawne tworzenie po rejestracji, wejście do nowego Workspace, transakcyjne
przygotowanie pulpitu, moduły, gość tylko do odczytu oraz zaproszenia e-mail
i linkiem opisuje [Praca zespołowa](TEAMWORK.md#system-workspace-25102026).
Zachowano Django, istniejące konta, granice danych i aktualny wygląd.

Przeszło **314 testów Django**: `workplaces`, `accounts`,
`core.test_workspace_frontend`, `core.test_navigation_frontend`,
`dashboard.test_workspace_invitations`, `documents.test_suite`,
`documents.test_drive_office`, `spaces.test_write_access`, `resources`.
Końcowy dodatkowy zestaw **55 testów** objął nowy system, migrację, Dla ciebie
i regresje wyszukiwania. Testy używały osobnych baz i storage.
Sprawdzono równoczesne przyjęcia ostatniego miejsca w linku oraz upgrade
zaproszeń istniejących przed migracją; stare rekordy dostały różne UUID.
Przeszły TypeScript, oba buildy (aplikacja i tablica), 10 testów frontendu,
kontrola Django, indeks kodu, lokalne linki i `git diff --check`.
Migracje `workplaces.0002`–`0004` zastosowano w lokalnej bazie; plan nie zawierał
innych operacji. Nie wykonywano wdrożenia produkcyjnego.

Browser plugin nie był dostępny. Playwright z lokalnym Chrome na osobnej bazie
(`http://127.0.0.1:8791`) sprawdził 1440×900, 1024×768, 390×844 i 320×568:
rejestrację, błędną/pustą nazwę, tworzenie kolejnego Workspace, przełączenie
kontekstu, reload, moduł wyłączony/włączony, odrzucenie bezpośredniego API,
link, jego unieważnienie, zewnętrzny adres bez konta, rejestrację z zaproszenia,
potwierdzenie dołączenia oraz gościa na katalogu i zadaniu. Próba z poprawnym
CSRF potwierdziła 403 dla zapisu gościa. Zadziałały też natywne POST bez JS
oraz pierwszy render z zaproszeniem do osoby bez konta. Zrzuty obejrzano;
poprawiono szerokość checkboxów modułów i odczyt pustego odbiorcy w szablonie.
Brak nieoczekiwanych błędów JS, pustych ekranów i poziomego przepełnienia strony;
szerokie tabele zachowują własne przewijanie. Nie testowano Safari/Firefox,
prawdziwej dostawy SMTP ani rzeczywistego serwera ONLYOFFICE (uprawnienia,
konfigurację view i odrzucenie callbacku pokrywają testy Django).

## Opcjonalna nazwa Workspace po rejestracji (25.10.2026)

Rejestracja tworzy konto i domyślny Workspace atomowo, po czym otwiera
`/accounts/register/workspace/` we wspólnej powłoce kont. Sesja ogranicza zmianę
do nowego Workspace. Własna nazwa zastępuje losową; puste pole zachowuje nazwę.
Nie zmieniono modeli ani migracji. [Przepływ](MECHANISMS.md#1-tożsamość-sesja-i-obecność).

Na osobnej bazie PostgreSQL przez `scripts/run_tests.py` przeszło **110 testów**:
`accounts.test_registration_workspace`, `accounts.tests`, `accounts.test_frontend`,
`accounts.test_login_redirects`, `accounts.test_email_identity`,
`accounts.test_registration_races`, `workplaces.test_defaults` i `dashboard.test_for_you`.
Obejmują HTML/API, granice sesji, CSRF, walidację, zachowanie kodu/adresu,
wycofanie transakcji i pierwsze logowanie w zwykłym/scoped Workspace.
Przeszły też build z TypeScriptem, 10 testów frontendu, format, kontrola Django,
indeks kodu, lokalne linki dokumentacji i `git diff --check`.

Playwright z lokalnym Chrome (plugin Browser niedostępny) na osobnej bazie i storage
QA sprawdził rejestrację → własną/pustą nazwę → logowanie → zapisany Workspace,
przeładowanie i zakończony krok. Porównano kartę z rejestracją i układ przy
1440×900, 1024×768, 390×844 i 320×568; sprawdzono błąd długości, fokus, zachowanie
szkicu, ponowienie oraz formularz bez JavaScriptu. Brak błędów wykonania,
nieoczekiwanych błędów konsoli i nieudanych żądań. Tymczasową bazę i storage
usunięto. Safari, Firefox i pełnego zestawu testów repozytorium nie sprawdzano.

## Podświetlenia menu na szklanym tle (25.10.2026)

Kryjące tła hover i zaznaczenia zastąpiono wariantami neutralnych kolorów
i akcentu z przezroczystością. Aktywny wiersz ma jedną warstwę tła,
ciemniejszy tekst akcentu i dotychczasowy znacznik. Dodano stan naciśnięcia,
wewnętrzny obrys fokusu klawiatury oraz podświetlenie „Więcej…” powiązane
z otwartym natywnym popoverem. Nagłówki i wiersze mają przejście tła 120ms.
Topbar używa neutralnego tła także w przełączniku Workspace.

Playwright z lokalnym Chrome (plugin Browser niedostępny), osobną bazą
i fikcyjnym kontem potwierdził 27 sprawdzeń: hover, naciśnięcie, aktywny
wiersz i jego menu, fokus, zwinięty pasek z panelem skrótów, pusty i błędny
picker z ponowieniem, reload i częściową nawigację do Zasobów oraz powrót.
Sprawdzono 1440×900, 1024×900, 390×900 i 320×900; zrzuty przed/po obejrzano.
Brak poziomego przepełnienia i nieoczekiwanych błędów JS. Jeden HTTP 503
był symulowaną awarią pickera. Pomiar przykładowej aktywnej pozycji na tapecie
dał kontrast tekstu 6,30:1. Logowanie zachowuje 46% przezroczystości.
Kontrola Django, indeks, lokalne linki UI i diff przeszły. Nie ponawiano
builda ani testów domenowych dla zmiany CSS; Safari i Firefox nie testowano.

Po ustawieniu 45% przezroczystości szkła złagodzono podświetlenia:
neutralny hover ma 6% krycia, naciśnięcie 10%, aktywne tło 10%, a jego
wariant interakcji 16%. Zachowano znacznik, fokus i ciemniejszy tekst.
Na tej samej konfiguracji Chrome przeszło 28 sprawdzeń, w tym wskazany
przez użytkownika hover „Pulpit domyślny” obok aktywnego Scrum, mobilne
menu, stany otwartego pickera i jego błędu oraz nawigacja i reload.
Zrzuty obejrzano; kontrast przykładowego aktywnego tekstu wyniósł 6,77:1.
Nie wykryto nieoczekiwanych błędów JS. Indeks, lokalne linki i diff przeszły.

## Tapeta z fałdami inspirowana Windows 11 (25.10.2026)

Wspólny token tapety wskazuje `wallpaper-fluent-bloom-light-4k.webp`:
błękitno-lawendowe, przestrzenne fałdy wygenerowane wbudowanym Image Gen.
Pochodzenie, pełny prompt i sposób powiększenia do 3840×2160 opisuje
[README grafiki](../static/img/auth/README.md). Odświeżono cache powłok
i tokenów oraz indeks; szkło i poprawka narożników pozostają wspólne.

Plugin Browser był niedostępny; użyto Playwright z lokalnym Chrome,
osobnej tymczasowej bazy i fikcyjnego konta. Sprawdzono logowanie,
rejestrację i paski przy 1440×900, 390×844, 320×568 oraz 3840×2160;
powłokę także przy 1024×768. Zrzuty obejrzano pod kątem kadrowania
i czytelności. Potwierdzono odczyt WebP 3840×2160, zachowanie szkła,
mobilne menu, zwijanie, picker Workspace, częściową nawigację do Zasobów,
powrót/reload, pierwszy render bez JS i błąd pustego formularza logowania.
Brak przepełnienia, nieoczekiwanych błędów JS i nieudanych żądań;
jeden HTTP 400 był oczekiwaną walidacją. Pomiar narożników potwierdził
ciągłość tła (różnica sąsiednich kanałów maksymalnie 2/255).
Indeks, lokalne linki i diff przeszły. Dla podmiany obrazu nie ponawiano
builda ani testów domenowych; Safari i Firefox nie były sprawdzane.

## Tapeta i matowe szkło pasków aplikacji (25.10.2026)

Górny i boczny pasek współdzielą tapetę i tokeny szkła z panelem logowania.
Mobilne menu ma własną warstwę tej samej grafiki pod szkłem. Zmieniono CSS
i wersje cache obu powłok; układ, React i mechanizmy domenowe pozostają wspólne.

Plugin Browser był niedostępny; Playwright z lokalnym Chrome na osobnej,
tymczasowej bazie sprawdził 1440×900, 1920×1080, 1024×768, 768×1024,
390×844, 320×568 i 3840×2160. Przeszły: pusty ekran „Dla ciebie”,
Zasoby, scoped Przestrzenie, zwijanie i mobilne menu, picker Workspace,
pusty/błędny wynik wyszukiwania oraz ponowienie, częściowa nawigacja,
Wstecz/reload, pierwszy render bez JS i ograniczenie przezroczystości.
Potwierdzono odczyt tapety 3840×2160 i zgodność parametrów szkła z logowaniem
oraz rejestracją. Zrzuty obejrzano; brak poziomego przepełnienia,
nieoczekiwanych błędów JS i nieudanych żądań. Jeden HTTP 503 był celowo
symulowany w pickerze. Kontrola Django, indeks kodu, lokalne linki UI i diff
przeszły. Nie ponawiano builda ani testów domenowych dla zmiany CSS;
Safari i Firefox nie były sprawdzane.

Korekta narożników: szkło przeniesiono z osobnych powierzchni pasków na
jedną dekoracyjną warstwę `body::before`, także pod zaokrągloną treścią.
Usuwa to ciemniejszy prostokąt surowej tapety przy narożnikach. Mobilne menu
zachowuje własną warstwę szkła nad swoją tapetą. Filtr pozostaje oddzielony
od elementów interaktywnych; powłoka używa `isolation: isolate`.
Chrome/Playwright potwierdził narożniki przez porównanie sąsiednich pikseli,
przy 1440×900, 1920×1080, 1024×768 i 3840×2160 oraz menu przy 390×844
i 320×568. Przeszły też zwijanie, menu Workspace, picker, otwarcie i zamknięcie
modala Przestrzeni, nawigacja do Zasobów i powrót, reload, pierwszy render
bez JS, ograniczenie przezroczystości i referencja logowania. Zrzuty przed
i po poprawce porównano wizualnie; kontrola Django, indeks i diff przeszły.

## Kompaktowa karta kont w jasnym trybie (25.10.2026)

Dopisek „Ikony UIcons: Flaticon” usunięto z Reacta i pierwszego renderu
formularzy kont, wraz z nieużywanymi regułami stopki. Oznaczenie w Ustawieniach
i lokalne pliki biblioteki pozostają. Build/TypeScript, Prettier, indeks i diff
przeszły. Playwright/Chrome przy 1440×900 i 390×844 potwierdził brak dopisku
w logowaniu i rejestracji, także bez JS, oraz brak przepełnienia i błędów JS.

Korekta nagłówka kont używa oryginalnej sylwetki znaku jako maski w kolorze
`--system-accent`, pomija przezroczyste marginesy PNG i zmniejsza odstępy
napisu Ancore. Reguły obejmują wyłącznie powłokę kont; źródłowe logo nie jest
zmieniane. Ponowiono build/TypeScript, Prettier, indeks i diff. Playwright/Chrome
przy 1440×900, 390×844, 320×568 i 3840×2160 sprawdził logo obu formularzy,
rzeczywisty kolor i wycięcie maski, fokus linku, błędy/reload, brak JS,
przepełnienia oraz nieoczekiwanych błędów konsoli. Zrzuty porównano ze zdjęciem
użytkownika. Dla tej zmiany prezentacji nie ponawiano testów domenowych.

Logowanie, rejestracja i dodanie konta używają białej karty 520px z wysokością
dopasowaną do treści, wyśrodkowanej pionowo po prawej stronie tapety.
Publiczne formularze mają widoczny nagłówek i etykiety, pola 48px oraz lokalny
fioletowy wariant przycisku z białym tekstem. Tło autouzupełnienia i obszaru
podglądu hasła jest wspólne. Pierwszy render Django odpowiada Reactowi;
nie zmieniono obsługi sesji, walidacji, zapisu ani modelu kont.

Przeszły build z kontrolą TypeScript, Prettier zmienionego komponentu oraz
28 testów: `accounts.tests.AuthPageViewTests`, `accounts.test_frontend`
i `accounts.test_login_redirects`, na osobnej bazie przez `scripts/run_tests.py`.
Plugin Browser był niedostępny; użyto istniejącego Playwright i Chrome.
Przy 1440×900, 1024×768, 390×844, 320×568 i 3840×2160 sprawdzono oba
formularze, błędy/fokus, podgląd hasła, szkic po 503, zakładki/reload,
POST bez JS oraz natywny stan `autofill` wymuszony przez Chrome DevTools.
Na tymczasowej bazie przeszła rzeczywista rejestracja → logowanie → „Dla ciebie”
oraz dodanie drugiego konta. Profil był ekranem referencyjnym; dodanie konta
sprawdzono też na telefonie i przed uruchomieniem Reacta. Dodatkowo przeszły
3600×1906 (rozmiar zdjęcia użytkownika) i 844×390. Zrzuty obejrzano przez
`view_image`, porównując tapetę, proporcje, nagłówek, etykiety, odstępy,
przycisk i kolor autouzupełnienia z zaakceptowanym opisem korekty.
Poprawiono nadpisanie białego tekstu CTA przez globalny CSS; nie pozostały
znane problemy w badanych widokach. Nie sprawdzano Safari/Firefox ani całego
zestawu testów repozytorium. Tymczasową bazę i storage usunięto po QA.

## Logowanie i rejestracja z tapetą (25.10.2026)

Kolejna korekta na prośbę użytkownika zastąpiła niebieskie fałdy spokojnymi
fioletowo-granatowymi wydmami.
Odświeżono wersje arkuszy. Playwright/Chrome na lokalnym porcie 8000 przy
1440×900 i 390×844 potwierdził odczyt grafiki, kadrowanie obu formularzy,
zakładki, podgląd hasła, ponowne wejście/reload oraz brak przepełnienia
i błędów JS. Sprawdzono indeks, linki i diff; dla samej podmiany obrazu
nie ponawiano poniższego zestawu testów ani builda.

Na żądanie 4K tapetę zastąpił `wallpaper-violet-dunes-4k.webp`: dokładnie
3840×2160px, bezstratny WebP, 2 601 788 bajtów. Image Gen zwrócił źródło
1672×941px mimo żądania UHD; końcowy eksport powiększono filtrem Lanczos3.
Nie jest to natywna generacja szczegółów w 4K. Metadane pliku i odczyt
`naturalWidth`/`naturalHeight` w Chrome potwierdziły rozdzielczość.
Playwright/Chrome przy 3840×2160, 1440×900 i 390×844 sprawdził tapetę,
formularze, zakładki, podgląd hasła i reload; brak błędów JS i poziomego
przepełnienia. Odświeżono cache arkuszy, dokumentację i indeks. Przeszły
linki i diff; dla samego obrazu nie ponawiano testów domenowych ani builda.

Na prośbę użytkownika przywrócono wariant ze wskazanego zdjęcia: kryjący
ciemny gradient panelu, jasny tekst, ciemne pola z jasnymi ramkami i lawendowy
przycisk. Przywrócono wcześniejszy subtelny cień; panel nie używa filtra szkła
ani przezroczystości. Zachowano układ i tapetę 3840×2160px.
Playwright/Chrome przy 1440×900, 390×844 i 3840×2160 potwierdził gradient,
kolory pól i przycisku, brak rozmycia, błędy, podgląd hasła, zakładki/reload
oraz brak błędów JS i poziomego przepełnienia. Indeks, linki i diff przeszły;
dla przywrócenia CSS nie ponawiano builda ani testów domenowych.

Następnie przygotowano jasny wariant tej samej powłoki: perłowo-lawendowe
wydmy `wallpaper-violet-dunes-light-4k.webp`, biały panel i pola, ciemnoszary
tekst, fioletowe podkreślenie oraz standardowy przycisk aplikacji. Logo
korzysta z oryginalnych kolorów. Jasny wariant jest aktywną powłoką kont;
układ i obsługa formularzy pozostają wspólne. Tapeta ma 3840×2160px,
bezstratny WebP i 3 197 040 bajtów; źródło Image Gen 1672×941px powiększono
filtrem Lanczos3. Ciemny plik zachowano jako wcześniejszą wersję.
Playwright/Chrome przy 1440×900, 1024×768, 390×844, 320×568 i 3840×2160
potwierdził oba formularze, kolory, rozdzielczość tapety, błędy/fokus,
podgląd hasła, szkic po 503, zakładki/reload, klawiaturę i POST bez JS.
Nie wykryto błędów JS ani poziomego przepełnienia. Zaktualizowano cache
arkuszy, opis UI, pochodzenie grafiki i indeks; linki i diff przeszły.
Dla zmiany CSS i obrazu nie ponawiano builda ani testów domenowych.

Powłoka kont ma lokalną tapetę WebP, prawy biały panel i zakładki
logowania/rejestracji. React i pierwszy render Django współdzielą układ;
dodanie konta zachowuje nagłówek oraz powrót do profilu. Zmiana nie dotyczy
modeli, sesji, uprawnień ani migracji. [Wariant UI](UI.md#konta-w-react).

Na tymczasowej bazie PostgreSQL przeszły **64 testy**:
`accounts.tests`, `accounts.test_frontend`, `accounts.test_login_redirects`,
`accounts.test_email_identity` i `accounts.test_registration_races`, uruchomione
przez `scripts/run_tests.py`. Przeszło też 10 testów frontendu, build z TypeScriptem,
Prettier zmienionego komponentu, kontrola Django, indeks, lokalne linki i diff.

Plugin Browser był niedostępny; Playwright z lokalnym Chrome sprawdził
`http://127.0.0.1:8779` na osobnej bazie i fikcyjnych kontach. Rozmiary:
1586×992 (natywny rozmiar koncepcji), 1440×900, 1024×768, 390×844,
320×568 i 844×390. Sprawdzono oba formularze, ponowne wejście, zakładki,
błędne/puste dane, podgląd hasła, fokus komunikatów i skrót do formularza,
zachowanie szkicu po HTTP 503 i ponowienie, rzeczywistą rejestrację → logowanie
→ „Dla ciebie”, dodanie drugiego konta oraz pierwszy render i POST bez JS.
Na 320px formularz z błędami pozwala przewinąć do zapisu. Profil i dodanie
konta posłużyły jako ekrany referencyjne. Tożsamość stron, treść, brak nakładek
błędu, konsola, zrzuty i interakcje przeszły; brak nieoczekiwanych błędów JS
oraz poziomego przepełnienia formularzy.

Porównano koncepcję i końcowe zrzuty przez `view_image`: proporcje panelu,
kadrowanie tapety bez nakładki, paletę, typografię, odstępy i wysokości pól,
zakładki oraz mobilne ułożenie. Poprawiono proporcje panelu, kontrast przycisku
przesłaniany przez globalny CSS i tło powrotu do profilu. Teksty sprawdzono
względem koncepcji: polskie etykiety, własne logo Ancore, opcjonalne drugie imię
i wymagane przypisanie ikon są świadomym dostosowaniem do aplikacji.
Nie dodano tekstów marketingowych. Nie pozostały znane problemy w badanych
widokach. Safari, Firefox i pełny zestaw testów repozytorium nie były sprawdzane.

## Weryfikacja przed podziałem zmian na commity (23.10.2026)

Na osobnej, tymczasowej bazie PostgreSQL i storage przez `scripts/run_tests.py`
przeszły **234 testy Django** obejmujące role, migrację i udostępnianie Pulpitów,
katalogi i wycofane ekrany zarządzania, Filtry, nawigację i kontrakty React,
powłokę, schemat oraz udostępnianie Przestrzeni. Dostosowano trzy nieaktualne
testy do przekierowań katalogu, kolejności zakładek i widoczności w ustawieniach.

Przeszło **10 testów frontendu**, build z kontrolą TypeScript, `format:check`,
kontrola Django, `makemigrations --check --dry-run`, kontrola indeksu kodu,
lokalnych odnośników dokumentacji oraz `git diff --check`. Migracja
`dashboard.0005_dashboard_membership_roles` została objęta commitem.
Nie uruchamiano pełnego zestawu repozytorium ani nie ponawiano wcześniejszych
prób UI w przeglądarce opisanych poniżej. Zweryfikowano też opis szerokości
przełącznika Workspace na podstawie aktualnych reguł CSS.

## Role Pulpitów (23.10.2026)

Pulpity obsługują role Administrator/Członek/Obserwator przez jawny model
`DashboardMembership` w istniejącej tabeli M2M. Migracja `dashboard.0005`
zachowuje tabelę, identyfikatory i odbiorców, nadając dotychczasowym relacjom
rolę obserwatora. Test migracji sprawdził przejście w obie strony na danych,
niezmienny identyfikator tabeli oraz zapis starego procesu M2M po migracji.
Usunięcie/wyłączenie członkostwa Workspace czyści role Pulpitów.
Uprawnienia i wyjątki właściciela opisuje [Praca zespołowa](TEAMWORK.md#role-pulpitów).

Na osobnej bazie PostgreSQL przeszło **166 testów**: role, migracja,
udostępnianie i podstawowe mechanizmy Pulpitów, wspólne API/powłoka, schemat
oraz udostępnianie Przestrzeni. Sprawdzono m.in. każde wejście edycji gadżetów,
układ, ustawienia, dostęp i usuwanie, ograniczenia administratora, obniżenie roli,
cofnięte członkostwo, prywatne źródła oraz zgodność starych formularzy i M2M.
Przeszły też build/TypeScript, 10 testów frontendu, Prettier, kontrola Django,
`makemigrations --check --dry-run`, SQL migracji, linki, indeks i diff.

Plugin Browser był niedostępny; istniejący Playwright/Chrome na osobnej bazie
i fikcyjnych osobach sprawdził 1440×900, 1024×900 i 390×900: nadanie i zmianę ról,
503/ponowienie, zachowanie szkicu, uprawnienia menu, administratora bez operacji
na właścicielu/innych administratorach, rzeczywiste dodanie gadżetu przez członka,
odmowę zapisu w otwartym edytorze po obniżeniu roli, odebranie dostępu, reload
i referencyjne role Przestrzeni. Brak nieoczekiwanych błędów JS i przepełnienia.
Po kopii lokalnej bazy zastosowano migrację; stan modeli i migracji jest zgodny.
Nie sprawdzano pełnego zestawu, Safari/Firefox ani wdrożenia produkcyjnego.

## Wspólne udostępnianie Pulpitów i Przestrzeni (23.10.2026)

„Udostępnienia” Pulpitu używają `shared/Members`, `shared/SharingDialog`
i pickera Workspace, z natychmiastowym dodawaniem/odbieraniem dostępu.
Widoczność przeniesiono do „Ustawień”; dotychczasowe relacje `shared_with`,
odbiorcy oraz prawo edycji wyłącznie przez twórcę pozostają zachowane.
Nie zmieniono modeli ani migracji. Naprawiono również rekurencję zamknięcia
bezpośredniego okna po potwierdzeniu odrzucenia szkicu.

Na osobnej bazie PostgreSQL przeszło 158 testów: nowe `dashboard.test_pulpit_sharing`,
kontrakty React, parametry/adresy/nawigacja Pulpitów, udostępnianie Przestrzeni
oraz wspólne API i powłoka. Po końcowej poprawce odświeżania nazwy i ponawiania
operacji ponowiono 35 testów udostępniania i kontraktów. Build z TypeScriptem,
10 testów frontendu, Prettier, kontrola Django, lokalne linki dokumentacji,
indeks kodu i `git diff --check` przeszły.

Plugin Browser był niedostępny; użyto istniejącego Playwright/Chrome, osobnej
bazy i fikcyjnych osób. Przy 1440×1000/900, 1024×900 i 390×900 sprawdzono
tabelę i chronionego twórcę, pustą listę odbiorców, wyszukiwanie/pusty wynik,
wybór klawiaturą, udostępnienie i odebranie (także 503 i ponowienie), odczyt
odbiorcy bez prawa edycji, natychmiastowe cofnięcie dostępu, widoczność Workspace,
zachowanie szkicu, ponowne wejście/reload, Escape/fokus oraz referencyjne okno
Przestrzeni. Nie wykryto błędów JS ani przepełnienia dokumentu. Pełnego zestawu,
Safari i Firefoksa nie uruchamiano.

## Wspólny rozmiar ikon podpunktów menu (23.10.2026)

`--sidebar-subnav-icon-size: 20px` określa pole i flex-basis wszystkich ikon
podpunktów Pulpitów, Przestrzeni i Filtrów, w tym emoji, awatarów, pulpitu
domyślnego, wyszukiwania i „Więcej…”. Usunięto osobne nadpisania 20/21px;
nagłówki sekcji zachowują 18px. Odświeżono wersje arkuszy w `core/base.html`.

Playwright/Chrome na osobnej bazie QA przy 1440×1100 i 390×844 zmierzył
jednakowe wymiary 12 ikon SVG/emoji/awatarów oraz sprawdził hover, aktywny
wiersz, reload, referencyjne Zasoby, wszystkie trzy podmenu zwiniętego paska,
menu mobilne i pierwszy render Django bez JavaScriptu. Wymiary uwzględniają
istniejący `zoom: 0.98`; nominalne pole CSS wynosi 20×20px. Nie było błędów
konsoli, nakładek błędów ani przepełnienia strony. Plugin Browser był
niedostępny; użyto istniejącego Playwright. Indeks i `git diff --check` przeszły.
Zmiana dotyczy CSS i wersji zasobów; nie ponawiano builda ani testów backendu.
Nie sprawdzano Safari/Firefox.

## Usunięcie ekranu zarządzania Filtrami (23.10.2026)

Usunięto „Zarządzaj filtrami”, jego szablon, wariant tabeli i menu oraz wejścia
w Ustawieniach, nagłówku kolekcji, wyszukiwaniu i zwiniętej nawigacji.
Stare zwykłe/scoped `filters/manage/` kierują do „Moje filtry”; zachowują
poprawną jawną zakładkę, wyszukiwanie i stronę, pomijając dawne parametry
widoczności/gwiazdki. API strony i nawigacji zwraca identyczny adres.
Starsze formularze tworzenia/edycji działają nad zwykłym katalogiem i zachowują
kontrolę twórcy, Workspace, udostępnienia i rewizji. `return_to` wskazujący
wycofany katalog jest normalizowany także dla gwiazdki/usuwania.
Po wycofaniu trzech ekranów usunięto nieużywany `management_sidebar.html`.
Katalogi Przestrzeni, Pulpitów i Filtrów oraz zarządzanie Workspace nadal działają.

Przeszły 124 testy Django: `dashboard.test_filters`, `core.test_filter_frontend`,
`core.test_frontend`, `core.test_navigation_frontend`,
`dashboard.tests.DashboardViewTests`, `core.test_pulpit_frontend`,
`dashboard.test_pulpit_management`, `spaces.test_management`
i `spaces.test_navigation`. Przeszło też 10 testów frontendu, build TypeScript,
format, kontrola Django, indeks, składnia skryptów i `git diff --check`.

Playwright/Chrome na osobnej bazie QA przy 1440×1000 i 390×844 potwierdził
przekierowania/parametry, brak skrótów w menu, zwiniętym menu, Ustawieniach
i wyszukiwaniu, okna ustawień/dostępów i tworzenia, zakładki, pusty wynik,
reload, częściową nawigację i Wstecz oraz referencyjne zarządzanie Workspace.
Nie było błędów konsoli, nakładek błędów ani przepełnienia strony.
Plugin Browser był niedostępny; użyto istniejącego Playwright bez instalacji
zależności. Nie sprawdzano Safari/Firefox ani pełnego zestawu repozytorium.

## Usunięcie ekranu zarządzania Przestrzeniami (23.10.2026)

Usunięto osobny ekran „Zarządzaj przestrzeniami”, jego menu boczne, odnośniki
w nagłówku Przestrzeni i Ustawieniach oraz warianty listy w React i HTML.
Stare zwykłe/scoped `spaces/manage/` przekierowują do katalogu „Przestrzenie”,
zachowując wyszukiwanie, rodzaj, zakładkę i numer strony. Dawny filtr sposobu
zarządzania jest ignorowany. Starsze formularze tworzenia/edycji nadal
sprawdzają dotychczasowe uprawnienia, a zapis i anulowanie wracają do katalogu.
Ustawienia i konfiguracja każdej przestrzeni oraz modele i dane pozostają zachowane.

Przeszło 130 testów Django: `spaces.test_management`, `spaces.test_navigation`,
`spaces.test_urls`, `spaces.tests`, `core.test_frontend`,
`core.test_navigation_frontend`, `core.test_space_settings_frontend`,
`core.test_pulpit_frontend`, `dashboard.test_pulpit_management`
i `dashboard.tests.DashboardViewTests`. Przeszło też 10 testów frontendu,
build TypeScript, format, kontrola Django, składnia zmienionych skryptów,
indeks i `git diff --check`.

Playwright/Chrome na osobnej bazie QA przy 1440×1000 i 390×844 potwierdził
przekierowania i parametry URL, brak odnośników w menu/Ustawieniach,
ustawienia przestrzeni, otwarcie kreatora, zakładki, pusty wynik, reload,
częściową nawigację i Wstecz oraz referencyjne zarządzanie Filtrami.
Nie było błędów konsoli, nakładek błędów ani przepełnienia strony.
Plugin Browser był niedostępny; użyto istniejącego Playwright bez instalacji
zależności. Nie sprawdzano Safari/Firefox ani pełnego zestawu repozytorium.

## Usunięcie ekranu zarządzania pulpitami (23.10.2026)

Usunięto osobny katalog „Zarządzaj pulpitami”, jego wariant menu i odnośniki
w menu Pulpitów oraz Ustawieniach (HTML i JSON). Stare zwykłe/scoped adresy
`dashboards/manage/` przekierowują do katalogu „Pulpity”, zachowując parametry
wyszukiwania, widoczności i strony. Starsze adresy edycji i POST nadal działają;
zapis oraz anulowanie wracają do zwykłego katalogu. Usunięto nieużywany szablon,
wariant Reacta i obsługę filtrów wycofanego ekranu. Modele i dane pozostają bez zmian.

Przeszło 115 testów Django obejmujących zarządzanie, nawigację, pulpity,
pulpit domyślny, usunięte grupy, kontrakt Reacta, powłokę i Ustawienia,
a także 10 testów frontendu, build TypeScript, format, kontrola Django,
indeks oraz `git diff --check`. Playwright/Chrome na izolowanej bazie QA
przy 1440×1000 i 390×844 potwierdził stare przekierowania, brak odnośników,
ustawienia/dostępy, edytor gadżetów, częściową nawigację i Wstecz, pusty wynik,
reload oraz referencyjne zarządzanie Filtrami. Nie było przepełnienia strony,
nakładek błędów ani błędów konsoli. Plugin Browser był niedostępny;
użyto istniejącego Playwright bez instalowania zależności. Nie sprawdzano
Safari/Firefox ani pełnego zestawu repozytorium.

## Kontrola przed zapisaniem commitów (23.10.2026)

Ponowiono celowany zestaw **100 testów Django** na oddzielnej, tymczasowej
bazie PostgreSQL i storage tworzonych przez `scripts/run_tests.py`:

```sh
.venv/bin/python scripts/run_tests.py core.test_emoji \
  dashboard.test_pulpit_preferences spaces.test_space_sharing \
  core.test_pulpit_frontend core.test_schema_baseline \
  dashboard.test_pulpit_editor dashboard.test_default_pulpit \
  dashboard.test_pulpit_management core.test_shell_frontend \
  core.test_space_settings_frontend core.test_workspace_frontend
```

Wszystkie testy przeszły. Przeszło również **10 testów frontendu**, build
z kontrolą TypeScript, `format:check`, kontrola Django i indeksu kodu oraz
`git diff --check`. `makemigrations --check --dry-run` nie wykazało zmian,
a `showmigrations dashboard --plan` potwierdziło zastosowanie lokalnych
migracji `0003` i `0004`. Nie uruchamiano pełnego zestawu repozytorium
ani nie ponawiano wcześniejszych prób UI w przeglądarce opisanych poniżej.

## Stały rozmiar pickera emoji (23.10.2026)

Pierwsze otwarcie mierzyło menu przed nadejściem katalogu i zachowywało 240px;
ponowne otwarcie z gotowymi kategoriami dawało inną szerokość. Wariant
`emoji-picker-menu` ustawia wspólne minimum i maksimum na 400px. Adapter nadal
ogranicza menu do szerokości ekranu. Doprecyzowany selektor otwartego pickera
zachowuje flex zamiast dziedziczonej siatki menu; kurczą się wyniki, dzięki
czemu dolny pasek pozostaje wewnątrz okna. Odświeżono wersje arkuszy CSS.

Playwright/Chrome (plugin Browser niedostępny) na osobnej bazie i storage QA
odtworzył przed poprawką szerokości 240px i około 365px oraz uciętą stopkę.
Po poprawce pierwsze otwarcie z wstrzymanym katalogiem, gotowy katalog,
osiem ponownych otwarć, wyszukiwanie/pusty wynik i kategorie zachowały 400px.
Błąd katalogu 503 i ponowienie nie zmieniły szerokości; sprawdzono zapis emoji
i reload. Przy 1920, 1440, 1024, 390 i 360px menu oraz dolny pasek mieściły się
w ekranie, również po zmianie szerokości otwartego menu. Referencyjny awatar
i select ustawień Przestrzeni działały bez zmiany. Nie było przepełnienia
dokumentu ani nieoczekiwanych błędów konsoli; jedyny błąd HTTP był wymuszonym
503. Indeks i `git diff --check` przeszły. Zmiana dotyczy CSS i wersji zasobów;
nie ponawiano builda TypeScript ani testów backendu. Safari/Firefox nie sprawdzano.

## Domyślna ikona Pulpitu (23.10.2026)

Wartość `layout-dashboard` wyświetla istniejącą ikonę czterech kafelków przez
wspólny adapter ikon. `emoji_payload` i `shared/Emoji` obsługują prezentację
`art.icon` obok dotychczasowych atlasów emoji. Picker pozwala przywrócić
„Domyślną ikonę pulpitu”; wybrane emoji, w tym jawne 📊, zachowują swoją grafikę.
Podgląd pozostaje przezroczysty i używa koloru tekstu aplikacji. Domyślna
wartość modelu już wynosiła `layout-dashboard`; nie zmieniano rekordów ani migracji.

Build z TypeScriptem oraz **50 testów** `core.test_emoji`,
`dashboard.test_pulpit_preferences`, `core.test_pulpit_frontend`,
`core.test_shell_frontend` i `dashboard.test_default_pulpit` przeszło.
Playwright/Chrome (plugin Browser niedostępny), na osobnej bazie i storage QA,
przy 1440×1000 i 390×844 potwierdził natywną ikonę w podglądzie, nagłówku,
menu, katalogu, wyszukiwarce i pulpicie domyślnym. Sprawdzono tworzenie/pusty
stan, wybór emoji, przywrócenie ikony, zapis/reload, pierwszy render Django,
referencyjny awatar Przestrzeni i brak przepełnienia telefonu. Nie było błędów
konsoli ani zewnętrznych żądań. Format, indeks i `git diff --check` przeszły.
Nie uruchamiano pełnego zestawu repozytorium ani Safari/Firefox.

## Podgląd ikony Pulpitu jak w Przestrzeniach (23.10.2026)

`PulpitFields` umieszcza pole emoji w lewej kolumnie istniejącego
`profile-edit-body` / `profile-photo-control`. Wariant `avatar` wspólnego
`EmojiPicker` ma podgląd 68×68px i „Zmień” pod nim, z geometrią przycisku
profilu/Przestrzeni. Cały podgląd i podpis są jednym przyciskiem otwierającym
dotychczasową bibliotekę 3145 emoji. Pozostałe pola zajmują prawą kolumnę,
a parametry zachowują dwie kolumny pól z etykietą po lewej od 1100px.
Na telefonie ikona jest nad polami. Tworzenie Pulpitu korzysta z tego samego
wariantu; Dostępy i konfiguracja gadżetu zachowują swoje formularze.

Build z TypeScriptem, format, indeks i `git diff --check` przeszły.
Playwright/Chrome (plugin Browser niedostępny) przy 1440×1000 i 390×844
porównał rozmiar podglądu z rzeczywistymi ustawieniami Przestrzeni,
sprawdził picker, wyszukiwanie/stan pusty, błąd katalogu i ponowienie,
klawiaturę/Escape, zachowanie wyboru przy walidacji, zapis, reload,
ponowne wejście i wariant odcienia skóry. Nagłówek, menu, katalog,
picker wyników, pulpit domyślny i pierwszy render zachowały tę samą grafikę.
Nie było przepełnienia telefonu ani nieoczekiwanych błędów konsoli.
Sprawdzono też utworzenie nowego pustego Pulpitu, układ przy 1920×1000
i 1024×1000 oraz zakładkę „Dostępy”.
Zmiana jest prezentacyjna; testów backendu nie ponawiano. Brak zmian modeli/API.
Nie sprawdzano Safari/Firefox.

## Biblioteka Fluent Emoji i wspólny picker (22.10.2026)

`core/emoji.py` ładuje lokalny katalog 3145 emoji i wariantów, buduje dane
prezentacyjne atlasów oraz waliduje wartości. `EmojiPickerInput` przekazuje
do Reactowego pola `emoji` wybrany symbol i adresy zasobów. Wspólny picker
używa `Dropdown`, kategorii, polskich/angielskich nazw, ostatnich wyborów
osobnych dla konta i Workspace oraz kolejnych porcji po 120 przycisków.
Wyszukiwanie jest stanem kontrolki i nie oznacza formularza jako zmienionego.
Wybór wpisuje zwykłą wartość formularza i zachowuje walidację oraz szkice.

Microsoft Fluent Emoji 3D i polskie dane Unicode CLDR są przypięte w
`scripts/assets/build_fluent_emoji.py`. Generator sprawdza SHA-256 źródeł,
tworzy 13 arkuszy WebP z kafelkami 64px i katalog; razem około 5 MiB.
Obrazy są grupowane kategoriami. Katalog pobierany jest dopiero po otwarciu,
udany odczyt jest współdzielony, a błąd można ponowić. Wszystko działa z
lokalnych zasobów bez CDN i bez nowej zależności wykonawczej. Źródła,
licencje i odtwarzanie: [README biblioteki](../static/vendor/fluent-emoji/README.md).

`dashboard.0004_dashboard_emoji_library` zastępuje stałe choices walidatorem
katalogu. `sqlmigrate` potwierdził brak operacji SQL; migrację zastosowano
lokalnie bez przepisywania danych. Nowe wybory zapisują Unicode w obecnym
polu 32 znaków, a wcześniejsze osiem identyfikatorów pozostaje aliasami.
Grafika jest wspólna dla Reacta i pierwszego renderu Django: ustawień,
nagłówka, edytora, menu, katalogu, pickera wyników i pulpitu domyślnego.

Przeszło 70 testów biblioteki, walidacji, parametrów Pulpitów, kontraktu React,
formularzy, powłoki i pulpitu domyślnego, a także build z TypeScriptem.
Playwright/Chrome (plugin Browser niedostępny) na odizolowanej bazie QA przy
1440×1000 i 390×844 potwierdził wyszukiwanie PL/EN i brak wyników, kategorie,
ostatnie wybory/pustą historię, dokładny symbol na początku wyników, klawiaturę
siatki, wybór przez Enter oraz Escape/fokus. Sprawdzono lazy loading, błąd katalogu
503 i ponowienie, brak oznaczania formularza jako zmienionego przy szukaniu,
zapis Unicode i wariantu odcienia skóry, zachowanie wyboru przy walidacji,
reload i ponowne wejście. Nagłówek, menu, katalog, picker wyników i pulpit
domyślny używały tej samej grafiki; sprawdzono zwykłe/scoped adresy,
referencyjny awatar Przestrzeni i pierwszy render Django bez JavaScript.
Utworzenie nowego pulpitu z emoji sprawdzono wraz z jego pustym stanem.
Nie było zewnętrznych żądań, przepełnienia telefonu ani nieoczekiwanych
błędów konsoli. Kontrola Django, migracji, formatu, indeksu i `git diff --check`
przeszła; dwa testy integralności katalogu ponowiono po grupowaniu atlasów.
Nie sprawdzano Safari/Firefox ani pełnego zestawu repozytorium.

## Emoji pulpitów (22.10.2026)

Ikony Pulpitów mają osiem podglądów emoji w istniejącym `VisualSelect`.
Zapisane identyfikatory pozostają zgodne; `Dashboard.Icon.emoji` i
`Dashboard.icon_emoji` dostarczają prezentację dla formularza, danych strony,
menu, wyszukiwarki i pierwszego renderu Django. Wspólne `shared/Emoji`
i `core/emoji.html` używają klasy `ancore-emoji` z systemowym fontem emoji.
Schemat formularza przekazuje opcjonalne `emoji` do istniejących podglądów
custom selecta. Ta zmiana nie wymaga nowej migracji ani aktualizacji rekordów.

Przeszło 67 testów parametrów Pulpitów, ich kontraktu React, wspólnego
formularza, powłoki i pulpitu domyślnego. Build z TypeScriptem, formatowanie,
kontrola Django, brak oczekujących zmian modeli, indeks i `git diff --check`
również przeszły. Playwright/Chrome (plugin Browser niedostępny) na osobnej
bazie QA przy 1440×1000 i 390×844 sprawdził osiem opcji, wyszukiwanie,
wybór, zapis i reload, nagłówek/edytor, menu, katalog i zarządzanie,
picker, pulpit domyślny oraz zwykłe/scoped URL. Sprawdzono referencyjne
awatary Przestrzeni i pierwszy render bez JavaScript. Nie było przepełnienia
telefonu ani błędów konsoli. Nie sprawdzano Safari/Firefox ani całego zestawu repozytorium.

## Dwie kolumny parametrów pulpitu (22.10.2026)

`components/pulpits.css` układa parametry zakładki „Ustawienia” w dwie równe
kolumny od 1100px. Nazwa i opis zajmują całą szerokość; parametry korzystają
ze wspólnego wiersza ustawień Przestrzeni: etykieta 180px po lewej,
odstęp 24px i kontrolka po prawej. Opisy i błędy pozostają pod kontrolką.
Warunkowy wybór Przestrzeni/filtra zachowuje
naturalną kolejność pól i zajmuje miejsce tylko wtedy, gdy jest widoczny.
Mniejsze ekrany zachowują jedną kolumnę. Wariant jest ograniczony do tej
zakładki; „Dostępy” i pozostałe formularze zachowują dotychczasowy układ.
Zaktualizowano wersję arkusza w pierwszym renderze Django.

Playwright/Chrome na izolowanej bazie QA (plugin Browser niedostępny)
potwierdził dwie kolumny i etykiety po lewej przy 1440×1000 i 1920×1000, jedną kolumnę przy
1024×900 i 390×844, puste źródło i walidację, wybór źródeł, zapis,
ponowne wejście i reload. Bezpośrednie porównanie z oknem ustawień
Przestrzeni potwierdziło tę samą szerokość etykiet i odstęp od kontrolek. Stopka pozostała
dostępna, nie było przepełnienia ani nieoczekiwanych błędów konsoli.
Kontrola indeksu i `git diff --check` przeszły. Zmiana dotyczy CSS;
nie ponawiano testów backendu ani budowania bundla. Nie sprawdzano Safari/Firefox.

## Ikony pól ustawień pulpitu (22.10.2026)

Zakres danych przekazuje do wspólnego selecta ikony `building-2`, `layers`
i `filter`; odświeżanie `circle-slash` lub `refresh-cw`. Wybór Przestrzeni
korzysta z `SpaceSelectMultiple`, rozszerzającego istniejący `SpaceSelect`
o wiele wartości, z tymi samymi avatarami. Pusty/zbiorczy wybór ma warstwy,
a zapisane filtry lejek. W `FieldControl` poprawiono klasy podglądu avatara
na wspólne `profile-avatar space-avatar` oraz `space-avatar-art` lub `has-photo`.
Bez nich podgląd w React nie miał rozmiaru ani ilustracji.

Przeszły 24 istniejące testy parametrów i kontraktu API Pulpitów, build,
kontrola typów/formatu, kontrola Django, indeks i `git diff --check`.
Playwright/Chrome (plugin Browser niedostępny) na osobnej bazie QA przy
1440×1000 i 390×844 potwierdził ikony opcji i wybranych wartości, widoczne
avatary Przestrzeni, pusty i wielokrotny wybór, zapis i reload, wspólny
wybór Przestrzeni w Filtrach oraz referencyjną Przestrzeń. Nie było błędów
konsoli, nakładek błędów ani przepełnienia telefonu. Nie sprawdzano
Safari/Firefox ani całego zestawu repozytorium. Nie ma zmian modeli/migracji.

## Parametry pulpitów (22.10.2026)

`dashboard.0003_dashboard_preferences` dodaje ikonę (osiem istniejących glifów),
zakres danych (Workspace, wybrane Przestrzenie lub zapisany filtr) oraz interwał
odświeżania 0/60/300/900 sekund. Domyślne wartości zachowują dotychczasowy
zakres danych i wyłączone odświeżanie. Przed lokalnym zastosowaniem migracji wykonano backup PostgreSQL;
porównanie istniejących pulpitów, gadżetów, gwiazdek i dostępów potwierdziło
zachowanie danych. Backup pozostaje lokalnie w ignorowanym `.local/backups/`.
Inne środowiska wymagają standardowego backupu i `manage.py migrate`.

Formularz ustawień zwraca po zapisie aktualny schemat, dzięki czemu znika
wcześniejszy błąd walidacji. Starszy POST zawierający tylko nazwę i opis
zachowuje nowe preferencje. Wybór źródeł jest ograniczony do aktywnego Workspace
i widoczności autora, a każdy odczyt ponownie sprawdza prawa oglądającego.
Gadżety bez własnej Przestrzeni dziedziczą zakres. Utrata źródła nie rozszerza
danych; zapisany filtr używa istniejącego kompilatora i ACL wynikowych zadań.
Ikona trafia do nagłówka, katalogu, menu, pickera i pierwszego renderu Django.
Odświeżanie działa tylko w widocznym podglądzie, z ochroną przed równoległymi
odczytami i sprzątaniem timerów po wyjściu.

Build, kontrola typów/formatu, składnia JS/Pythona oraz 112 testów Django
Pulpitów, kontraktu React, schematu i powiązanych Filtrów przeszły.
Po poprawce odpowiedzi zapisu ponowiono 43 testy formularzy i Pulpitów.
Dziesięć testów Node obejmuje nawigację oraz rzeczywisty kontroler timerów:
interwały, widoczność, wyłączenie, brak nakładania żądań, błąd i odmontowanie.
Kontrole modeli i zastosowania migracji potwierdziły brak dalszych zmian.

Plugin Browser był niedostępny. Playwright/Chrome na osobnej bazie QA przy
1440×1000, 1024×900 i 390×844 sprawdził nowe dropdowny, brak wymaganego źródła,
zachowanie szkiców, zapis i usunięcie błędów, ikony w menu/katalogu,
zakres Przestrzeni i zapisany filtr oraz zwykłe/scoped adresy. Zegar przeglądarki
przyspieszył interwał 60 sekund: po rzeczywistej zmianie zadania postęp
zmienił się z 50% na 100%. Sprawdzono pauzę modalu, edytora i ukrytej karty,
wznowienie, symulowany błąd 503 z zachowaniem danych i ręczne ponowienie,
cofnięcie dostępu odbiorcy do filtra, telefon i referencyjną Przestrzeń.
Nie było przepełnienia ani nieoczekiwanych błędów konsoli. Nie sprawdzano
Safari/Firefox ani pełnego zestawu repozytorium.

## Edycja układu bezpośrednio na pulpicie (22.10.2026)

`src/pulpits/DetailPage.tsx` renderuje edytor gadżetów w głównej treści strony.
Powłoka otwiera w modalu tylko ustawienia i dostępy; okno ma dwie zakładki.
„Edytuj pulpit” i „Gadżety i układ” używają dotychczasowej nawigacji JSON,
katalogu, przeciągania i automatycznego zapisu z rewizją. Nazwa w zarządzaniu
nadal otwiera ustawienia. Nie zmieniono modeli, API zapisu ani uprawnień.

Weryfikacja: build i format czterech zmienionych plików Reacta, pięć testów
nawigacji oraz 40 testów `core.test_pulpit_frontend`,
`dashboard.test_pulpit_editor`, `dashboard.test_default_pulpit`
i `dashboard.test_pulpit_management` przeszły. Testy Django używały osobnej
bazy PostgreSQL przez `scripts/run_tests.py`.

Plugin Browser był niedostępny; Playwright z lokalnym Chrome na izolowanej
bazie QA sprawdził 1440×1000, 1024×900 i 390×844: pusty pulpit, wejście do
edycji bez modalu i przeładowania dokumentu, pięć układów, dodawanie,
konfigurację (także z bezpośredniego adresu), usuwanie, przenoszenie menu
i przeciąganie, trwałość po reload,
symulowany konflikt 409 z przywróceniem układu i ponowieniem, „Gotowe”,
powrót do edycji, szkice i zapis dwóch zakładek ustawień, zwykłe/scoped adresy
oraz wariant zarządzania. Ekranem referencyjnym było podsumowanie Przestrzeni.
Nie było przepełnienia strony ani nieoczekiwanych błędów konsoli.
Nie uruchamiano pełnego zestawu repozytorium ani Safari/Firefox.

## Udostępnianie Przestrzeni (22.10.2026)

Zakładka „Członkowie” używa wspólnej tabeli, wyszukiwarki aktywnych osób
Workspace oraz kompaktowych okien udostępniania i zmiany roli. `space_team.py`
zachowuje bieżące członkostwa, ograniczenia administratorów i czyszczenie
dostępów zadań po odebraniu dostępu do Przestrzeni. Bez zmian modeli/migracji.

Na oddzielnych bazach PostgreSQL przeszło **119/119 testów**:

```sh
.venv/bin/python scripts/run_tests.py spaces.test_space_sharing \
  spaces.test_independent_tasks spaces.test_task_detail_parity \
  spaces.test_write_access core.test_frontend core.test_navigation_frontend \
  core.test_shell_frontend
.venv/bin/python scripts/run_tests.py core.test_space_settings_frontend \
  core.test_workspace_frontend
pnpm --dir frontend/app test
```

Pierwsze dwa polecenia obejmują 9 nowych testów udostępniania i istniejące
regresje. Testy nawigacji frontendu przeszły **5/5**. Build z TypeScriptem,
Prettier zmienionych źródeł, kontrola Django, linki dokumentacji, indeks
i `git diff --check` również przeszły.

Plugin Browser był niedostępny; użyto Playwright z lokalnym Chrome,
fikcyjnymi kontami, osobną bazą i storage QA. Przy 1440×1000, 1024×900
i 390×844 sprawdzono tabelę, wyszukiwanie/pusty wynik, wybór klawiaturą,
udostępnienie, zmianę roli, anulowanie i potwierdzenie odebrania dostępu,
błąd 503 i ponowienie bez duplikatu, zachowanie szkicu Głównej, Escape/fokus,
trwałość po reload i ponowne wejście. Publiczna Przestrzeń pokazuje dostęp
Workspace, odbiorca-obserwator nie ma kontrolek zapisu, a administrator nie
nadaje roli administratora. Sprawdzono także referencyjną tabelę zadania,
brak przepełnienia dokumentu i brak nieoczekiwanych błędów/ostrzeżeń JS.
Nie sprawdzano Safari/Firefox ani pełnego zestawu repozytorium.

## Pełny backup i samodzielne odzyskiwanie (22.10.2026)

Backup ma domyślny interwał 24 godzin i retencję 10 kopii. Format 2 dodaje
do bazy i zapisanych plików pakiet źródeł, konfigurację produkcji i certyfikaty
HTTPS Nginx Ancore. Snapshot kodu powstaje podczas budowania obrazu backupu;
nie wymaga montowania repozytorium ani socketu Dockera w schedulerze.
Konfigurator i `update` zmieniają poprzednią domyślną retencję 14 na 10,
zachowując sekrety i inne ustawione wartości retencji.

`restore.sh` jest osobnym, samodzielnym skryptem, który można skopiować bez
pozostałych źródeł na serwer z Dockerem i Compose. Wyświetla 10 ostatnich kopii,
po wyborze sprawdza archiwum i zrzut, buduje zapisany kod, odtwarza bazę i pliki
na nowych wolumenach oraz czeka na healthchecki. Poprzednie wolumeny zachowuje.
Nie wywołuje instalatora ani jego helperów. Odtworzona instalacja ma osobny
katalog i `deploy/compose.recovery.yaml`, uwzględniany przez jej polecenia
utrzymania. [Procedura, zakres kopii i wymagania](PRODUCTION.md#backup-i-odtwarzanie).

Przeszło **50/50 testów** `core.test_backup_recovery`,
`core.test_production_installer`, `core.test_production` i `core.test_project_layout`.
Nowe testy obejmują retencję, interwał, zawartość kopii, wybór wersji,
samodzielne działanie skryptu przy ścieżkach ze spacjami, konfigurację/TLS,
integralność i ścieżki archiwów, błędy budowania/odtwarzania/startu, blokadę
równoczesnego odzyskiwania, anulowanie i zgodność starszego odtwarzania danych.
Testy cyklu skryptu używają kontrolowanego CLI Docker, a testy archiwów
zastępują wywołania PostgreSQL; same w sobie nie potwierdzają pełnej instalacji.

Wykonano także rzeczywisty test na osobnym projekcie Compose w lokalnym silniku
Docker Linux, bez bazy ani uploadów użytkownika:

- zapisano konto testowe, prywatny plik i media, wykonano pełny backup, następnie
  zmieniono rekord i pliki oraz usunięto kontenery i odłączono pierwotne źródła;
- uruchomiono wyłącznie samodzielny `restore.sh` z archiwum: przebudował cztery
  obrazy, odtworzył bazę i pliki oraz uruchomił pięć zdrowych usług z ONLYOFFICE;
- porównano odzyskany rekord i treść plików ze stanem sprzed zmian; stary wolumen
  nadal zawierał późniejszą treść, co potwierdziło jego zachowanie;
- polecenie `ancore.sh status` odtworzonej instalacji wskazało właściwe usługi;
  uszkodzona kopia została odrzucona bez zatrzymania odzyskanej aplikacji;
- wykonano 11 kolejnych rzeczywistych kopii i potwierdzono dokładnie 10 archiwów
  oraz 10 odpowiadających plików SHA-256.

Zasoby tej instalacji QA, jej konfigurację, archiwa i wolumeny usunięto po teście.
Przeszły również `manage.py check`, składnia sh, lokalne linki dokumentacji,
kontrola indeksu i diffu. Pełny test używał HTTP; konfigurację i certyfikaty HTTPS
sprawdziły testy archiwizacji oraz kontrolowanego CLI, bez odtwarzania całego
środowiska HTTPS. Nie wykonywano wdrożenia na docelowym serwerze, testu awarii
fizycznego dysku ani pełnej regresji modułów aplikacji. Zmiana nie dotyczy UI,
modeli ani migracji.

## Porządkowanie repozytorium (22.10.2026)

[Mapa plików i zasady organizacji](REPOSITORY.md) opisują podział usług
w `deploy/`, narzędzi w `scripts/` oraz źródeł, wyników budowania i danych
lokalnych. Publiczne polecenia instalacji korzystają wyłącznie z `ancore.sh`;
na polecenie użytkownika usunięto główne skróty `install.sh` i `setup.sh`.
Lokalny start ONLYOFFICE zachowuje swój skrót zgodności.
Nieużywane archiwum starego środowiska
(`venv.bak/`, następnie `.local/venv-backups/`) usunięto na późniejsze
polecenie użytkownika; bieżące `.venv/` zachowano. Usunięto również cache
Pythona ze źródeł i puste katalogi lokalne, odzyskując około 115 MiB.
Generator indeksu obejmuje teraz również tablicę oraz narzędzia i wdrożenie.

Przeszło **37/37 testów** `core.test_production_installer`,
`core.test_production` i `core.test_project_layout`. Nowe przypadki sprawdzają
domyślne lokalizacje konfiguracji produkcji i ONLYOFFICE spoza repozytorium,
przy ścieżce ze spacjami, prywatne uprawnienia oraz zachowanie istniejących wartości.
Przeszły także kontrola Django, próbny `collectstatic`, składnia Pythona i sh,
lokalne linki dokumentacji, źródła `COPY`, indeks oraz kontrola diffu.

Na lokalnym silniku Docker Linux zbudowano cztery obrazy pod osobnymi nazwami
QA, w tym oba frontendy i kontrolę TypeScriptu. Jednorazowe kontenery bez
sieci i bez wolumenów danych potwierdziły `manage.py check`, `collectstatic`,
składnię entrypointów Nginx/PostgreSQL oraz pomoc CLI backupu.
Próba rzeczywistego konfiguratora przez kontekst Colimy zakończyła się
brakiem pliku źródłowego: ta maszyna nie udostępnia katalogu repozytorium
przez bind mount. Build przekazujący kontekst przez API działał poprawnie;
próba konfiguratora nie zmieniła istniejących ustawień.
Nie uruchamiano całej instalacji, nie wykonywano migracji danych użytkownika
ani pełnej regresji aplikacji. Porządkowanie nie zmienia kodu interfejsu.

## Uporządkowanie instalacji produkcyjnej (21.10.2026)

Wspólnym publicznym wejściem jest `ancore.sh`: `setup`, `configure`, `install`,
`update`, `start`, `stop`, `restart`, `status`, `logs`, `backup`, `restore`,
`unlock`, `reload`, `admin` i `doctor`. `configure` zapisuje ustawienia bez startu; `update` wymaga
istniejącej konfiguracji. Obsługiwane są globalne `--env-file` i `--context`
przed nazwą polecenia, z kontrolą lokalnego socketu Docker.

Kod poleceń wdrożenia jest w `deploy/cli/`: `runtime.sh` zarządza Compose,
budowaniem, portami, backupem i odtwarzaniem; `setup.sh` obsługuje pytania
terminala; `configure.py` waliduje i zapisuje ustawienia w kontenerze Pythona.
`scripts/production.py` przekazuje starsze wywołania do tych samych implementacji.
Usunięto drugą implementację cyklu życia usług w Pythonie i nieużywaną kopię
instalatora z obrazu backendu. `start` nadal używa lokalnych obrazów przez
`--no-build --pull never`; obrazy aplikacji i oba frontendy powstają na serwerze.
Przebudowa wymaga dostępu do rejestrów obrazów i pakietów.

`restore` zachowuje dotychczasową kolejność: kontrola argumentów i lokalizacji,
zatrzymanie zapisujących usług, odtworzenie bazy i plików, usunięcie blokady,
start z kontrolą gotowości. Błąd pozostawia zapisujące usługi zatrzymane.
`unlock` korzysta z jednorazowego kontenera i działa także po zatrzymaniu
schedulera, zachowując kontrolę blokady. Wolumeny, nazwa projektu i sekrety
nie zmieniają się przy porządkowaniu skryptów.

Starszy `scripts/start_office.sh` wykrywa brak lokalnego
`deploy/office.compose.yml` przed generowaniem `.env.office` lub startem Colimy.
Nie odtwarza wycofanej konfiguracji; kompletny aktualny zestaw jest w produkcyjnym
Compose. Istniejąca konfiguracja developmentu i jej odczyt w Django pozostają.

Weryfikacja: **35/35 testów** `core.test_production_installer`,
`core.test_production` i `core.test_project_layout`. Zestaw obejmuje zgodność
starych poleceń, własny plik konfiguracji, odmowę aktualizacji bez konfiguracji,
restore bez potwierdzenia lub wymaganych plików, pozostawienie zapisujących
usług zatrzymanych po błędzie oraz działanie unlock bez uruchomionego schedulera.

Osobny projekt Docker Linux `ancore-install-cleanup-qa`, na nowych wolumenach:

- przeszedł konfigurator, lokalny build czterech obrazów z oboma frontendami
  oraz start pięciu zdrowych usług;
- przełączenie na HTTPS z lokalnym certyfikatem, backup, zmiana danych QA,
  `restore`, `unlock`, przeładowanie Nginx i aktualizacja przez wspólne CLI
  zakończyły się poprawnie; restore przywrócił wartość rekordu konta i treść
  prywatnego pliku, a cztery sekrety i nazwa projektu pozostały niezmienione;
- drugi kontener potwierdził HTTPS readiness i logowanie (200), gotowość
  ONLYOFFICE oraz przekierowanie HTTP 308; testowano certyfikat samopodpisany;
- sprawdzono składnię POSIX sh w Debian dash, lokalne linki dokumentacji,
  indeks kodu i diff. Zasoby QA usunięto po weryfikacji.

Nie wykonano wdrożenia na docelowym Ubuntu użytkownika, testu z jego fizycznego
LAN, publicznego certyfikatu CA ani pełnej regresji aplikacji. Nie zmieniano
interfejsu przeglądarkowego. Instrukcja użytkowa:
[Produkcja](PRODUCTION.md).

## Produkcja Docker Compose (20.10.2026)

Zapis historyczny pierwszego pakietu. Aktualne polecenia i układ plików opisano
powyżej oraz w [instrukcji produkcji](PRODUCTION.md).

Dodano [pakiet produkcyjny](PRODUCTION.md) z pięcioma usługami: Nginx,
Django/Gunicorn, PostgreSQL 17, harmonogram backupów oraz ONLYOFFICE 10.0.0.1.
Instalator `sh ancore.sh install` potrzebuje na hoście wyłącznie Dockera z Compose:
konfigurator Pythona działa w tymczasowym kontenerze i automatycznie tworzy
`deploy/.env` (0600) z losowymi sekretami. Domyślnie Ancore działa przez HTTP,
bez domeny, na `0.0.0.0:8080`; `ALLOW_IP_HOSTS` sprawdza adresy IP i localhost.
Podanie `--url` włącza konkretną nazwę hosta. Opcjonalne HTTPS może kończyć
Nginx Ancore albo istniejący zewnętrzny proxy. `--reconfigure` zmienia transport
bez wymiany sekretów i wolumenów. Ponowny instalator robi backup przed buildem.
Nie instaluje Dockera ani nie pozyskuje certyfikatów. Dane i archiwa pozostają
nieszyfrowane. Dodatkowy `scripts/production.py` udostępnia utrzymanie i restore;
użycie go bezpośrednio wymaga Pythona na hoście.

Ścieżki storage i katalogu tymczasowego można wskazać środowiskiem;
domyślne ścieżki developmentu są zachowane. Django działa jako UID 10001,
z rolą PostgreSQL bez superuser/CREATEDB. Nginx udostępnia jedynie static
i dozwolone awatary; dokumenty i załączniki zachowują kontrolę Django.
Prywatne źródła/callbacki ONLYOFFICE przechodzą przez wewnętrzny listener.
Proxy odświeża adresy usług przez DNS Dockera po wymianie kontenerów.

Middleware `core.maintenance` synchronizuje żądania wszystkich workerów
z zadaniem backupu. Nowe żądania dostają 503, istniejące operacje i odpowiedzi
strumieniowe kończą się przed `pg_dump` i archiwizacją plików. Backup jest
nieszyfrowanym `.tar.gz` z sumą SHA-256; odtwarzanie zatrzymuje zapisujące
usługi, weryfikuje archiwum i odtwarza bazę oraz pliki. Przerwa obejmuje
przygotowanie całego archiwum, więc duże instalacje wymagają osobnego okna
serwisowego lub rozbudowy mechanizmu. Kopie obejmują dane zapisane w Ancore,
bez niezapisanych edycji i roboczych baz/cache ONLYOFFICE.

Weryfikacja na osobnym projekcie i nowych wolumenach `ancore-prod-qa`, bez
korzystania z bazy ani uploadów lokalnej aplikacji:

- zbudowano obrazy backendu, Nginx, PostgreSQL i backupu, wraz z oboma
  frontendami; do etapu zależności kopiowane są istniejące konfiguracje
  pnpm obu pakietów, dopuszczające skrypt esbuild;
- uruchomiono pięć zdrowych usług, w tym rzeczywisty ONLYOFFICE 10.0.0.1;
- przeszło 13 testów konfiguracji, blokad i struktury na lokalnym Pythonie 3.15
  oraz 87 testów produkcji, plików, dostępu i Dokumentów na Pythonie 3.14
  i osobnej bazie PostgreSQL w kontenerach;
- sprawdzono przez HTTP oraz HTTPS logowanie dwóch kont, zasoby Reacta,
  prywatne pobieranie, awatar, odmowę dostępu obcego konta, niedostępność
  prywatnych katalogów mediów oraz zasoby/powłokę ONLYOFFICE;
- wykonano rzeczywistą konwersję TXT → DOCX w ONLYOFFICE, pobranie przez
  podpisane źródło i zapis przez podpisany callback ze wzrostem rewizji;
- wykonano backup, sprawdzono SHA-256, format `pg_dump` i zawartość pliku,
  zmieniono dane testowe, odtworzono kopię i potwierdzono powrót oryginalnej
  treści, dokumentu Office oraz usunięcie danych utworzonych po kopii;
- sprawdzono wymianę/restart usług z zachowaniem danych, wariant Nginx
  z lokalnym certyfikatem testowym oraz kontrolę wdrożeniową Django.

Dodatkowa weryfikacja domyślnego HTTP i instalatora Docker-only na osobnym
projekcie `ancore-http-qa`:

- instalację (obecnie `sh ancore.sh install`) uruchomiono z linuksowego środowiska Docker CLI bez Pythona
  na hoście; wygenerował prywatny `deploy/.env` i pięć zdrowych usług na 8080;
- sprawdzono HTTP przez IP i localhost, poprawny nagłówek IP Host, odmowę dla
  obcej nazwy DNS oraz publiczny skrypt ONLYOFFICE pod względnym prefiksem;
- przeszło 20 lokalnych testów konfiguracji, struktury i walidacji edytora
  oraz 92 testy kontenerowe konfiguracji, plików, uprawnień i Dokumentów;
- ponowny instalator wykonał backup i zachował cały plik konfiguracji;
  sprawdzono SHA-256 archiwum, obecność `pg_dump`, plików i flagi braku szyfrowania;
  następnie `--reconfigure` włączyło HTTPS na testowym certyfikacie dla IP,
  zachowując wszystkie cztery sekrety, konto, zadanie i zapisaną rewizję;
  potwierdzono przekierowanie 308 z HTTP, logowanie i zasoby ONLYOFFICE
  przez HTTPS. Pięć usług pozostało zdrowych;
- rzeczywisty ONLYOFFICE pobrał prywatne źródło, przekonwertował TXT → DOCX
  i zapisał rewizję 2 przez podpisany callback z publiczną ścieżką IP;
  pobieranie wyniku połączyło się wyłącznie z wewnętrznym ONLYOFFICE;
- Chrome/Playwright sprawdził logowanie, zadanie, profil referencyjny i ponowne
  wejście przy 1366×900 oraz ekran zadania przy 390×844. Wymuszono brak
  Clipboard API (localhost jest przez przeglądarkę traktowany jako bezpieczny
  kontekst): fallback skopiował ID, pokazał sukces i przywrócił fokus;
  odmowa `execCommand` pokazała istniejący komunikat błędu. Zrzuty potwierdziły
  renderowanie; brak błędów JavaScript, ostrzeżeń konsoli i nakładek błędów.
  Powtórzono logowanie, kopiowanie i stan błędu przez HTTPS;
- `makemigrations --check --dry-run` nie wykazał zmian. Kompilacja i TypeScript
  przeszły w Dockerze, Prettier zaakceptował zmienione pliki React.
  Wyłączono nieużywany socket sterujący Gunicorna, eliminując błąd uprawnień
  do nieistniejącego katalogu domowego; start backendu nie zgłasza tego błędu.

Wtyczka Browser była niedostępna (`Browser plugin not available`); użyto
istniejącego Playwright i Chrome bez instalowania zależności. Skrypty i zrzuty
pozostały w katalogu tymczasowym poza repozytorium. Po weryfikacji usunięto
kontenery, wolumeny, konfigurację, backupy i certyfikat tej instalacji QA.
Poprawka interfejsu obejmuje
wyłącznie fallback kopiowania ID na HTTP; nie zmienia układu ani stylów.
Nie wykonano wdrożenia na docelowym serwerze, testu publicznego certyfikatu CA,
fizycznego klienta z innego komputera, pełnej regresji, testu obciążenia ani
Safari/Firefox. Pakiet nie zmienia modeli i nie dodaje migracji.

**Aktualny schemat od 18.10.2026:** [czysta baza i nowe migracje](DATABASE.md).
Poniższe datowane zapisy zachowują historię wcześniejszych prac i wyników;
opisy zachowania starych modeli oraz ich migracji nie są instrukcją obecnego uruchomienia.

## Wspólny wygląd wszystkich tablic Przestrzeni (18.10.2026)

Kanban, Scrum, Zarządzanie zadaniami, Marketing, Rekrutacja i Obsługa zgłoszeń
używają teraz jednego `ItemCard` oraz `StatusGroup` według wzorca aktywnego
sprintu. Kolumny mają kolorowe, zwijane nagłówki z licznikami, karty wspólny
zwarty układ i metadane, a puste kolumny obramowany komunikat. Pierwszy render
Django używa `spaces/card.html`; `spaces/sprint_card.html` jest aliasem.
Współdzielony wariant CSS zachowuje nazwę `work-sprint-board`. Estymacja
pozostaje polem Scrum. Zachowano animacje i akcje planowania/statusów;
nie zmieniono modeli, migracji, uprawnień ani zależności.

Przeszło **55 testów** `spaces.test_board_order`, `spaces.test_backlog_drag`
i `core.test_frontend` na osobnej bazie PostgreSQL, produkcyjny build
z TypeScriptem, 5 testów kontrolera nawigacji, Prettier, kontrola Django,
lokalne linki dokumentacji, indeks i diff.

Chrome/Playwright porównał kolory, wysokości i odstępy nagłówków wszystkich
sześciu szablonów oraz ich karty, metadane, puste stany i pełną wysokość kolumn.
Sprawdzono zgodność pierwszego HTML z Reactem, zwijanie klawiaturą, referencyjną
listę i ponowne wejście bez reloadu, długie tytuły i awatary. Zrzuty przy
1920×1000, 1024×900 i 390×900 potwierdziły wygląd sprintu i Kanbana oraz
poziome przewijanie bez przepełnienia strony. Powtórzony zestaw interakcji
z rozdziału o animacjach przeszedł, w tym błąd zapisu, Escape, ograniczenie
ruchu, obserwator, zwykłe/scoped adresy i sprzątanie po nawigacji w trakcie gestu.
Nie było nieoczekiwanych błędów JavaScript ani konsoli.

Wtyczka Browser była niedostępna; użyto istniejącego Playwright/Chrome
i tymczasowej bazy QA. Skrypty i zrzuty pozostały poza repozytorium.
Nie sprawdzano Safari/Firefox, fizycznego dotyku ani całego zestawu repozytorium;
nie wykonano wdrożenia produkcyjnego.

## Animacje tablicy i backlogu React (18.10.2026)

`spaces/useItemMotion.ts` podłącza efekty do aktywnego ekranu React:
podgląd śledzący kursor, animowane miejsce wstawienia, przesuwanie sąsiadów
i dolot do nowej sekcji. `DetailPage` pokazuje przeniesienie od razu i cofa je
po odrzuconym zapisie. Akcje `position`/`plan`, autoryzacja i historia nadal
korzystają z istniejącego backendu. Początek gestu na kontrolce jest wykluczony
na podstawie `pointerdown`, ponieważ natywne `dragstart` wskazuje cały artykuł.
Nie zmieniono modeli, migracji ani zależności. [Zachowanie i styl](UI.md#przestrzenie-i-zespoły).

Przeszło **55 testów** `spaces.test_board_order`, `spaces.test_backlog_drag`
i `core.test_frontend` na osobnej, usuniętej po przebiegu bazie PostgreSQL.
Przeszło również 5 testów kontrolera nawigacji (`pnpm --dir frontend/app test`),
produkcyjny build z TypeScriptem, Prettier, kontrola Django, indeks i diff.

Chrome/Playwright na osobnej bazie QA sprawdził natywny gest myszy i trwałość
kolejności po reloadzie, przenoszenie do statusu i planowanego sprintu, backlog
i Kanban, menu otwierane klawiaturą, natychmiastowy układ przy opóźnionym zapisie,
cofnięcie przy 409, Escape, brak zapisu bez zmiany pozycji oraz ograniczony ruch.
Sprawdzono zwinięty status, zwykły/scoped URL, brak gestu od przycisku,
wyłączony drag przy innym sortowaniu i dla obserwatora, listę referencyjną,
puste kolumny, ponowną nawigację oraz sprzątanie po opuszczeniu ekranu w trakcie gestu.
Zrzuty przy 1920×1000, 1024×900 i 390×900, również w świeżym kontekście mobilnym,
potwierdziły układ po zakończeniu przejść powłoki. Nie było nieoczekiwanych błędów
JavaScript ani konsoli. Celowy błąd 409 był oczekiwany.

Wtyczka Browser była niedostępna; użyto istniejącego Playwright i Chrome,
bez instalowania zależności. Skrypty, logi i zrzuty pozostały poza repozytorium.
Nie sprawdzano Safari/Firefox, gestów na fizycznym ekranie dotykowym ani całego
zestawu testów repozytorium. Nie wykonano wdrożenia produkcyjnego.

## Usunięcie akcji z pustych stanów (18.10.2026)

Puste strony i panele pokazują wyłącznie ilustrację, nagłówek i opis.
Usunięto przyciski i linki z Reacta oraz szablonów, w tym z obu pustych sekcji
„Dla ciebie”, kolumn gadżetów i pustego katalogu gadżetów. `EmptyState` nie
przyjmuje już dodatkowych dzieci. Akcje nagłówków i toolbarów pozostają dostępne.

Przeszło 158 testów tego samego zestawu co poniżej, build z TypeScriptem,
formatowanie, kompilacja 21 zmienionych szablonów i kontrola indeksu.
Chrome/Playwright na osobnej bazie potwierdził brak interaktywnych kontrolek
w 28 pustych widokach przy 1440×1000 i 390×844 (56 przypadków), działanie
tworzenia z nagłówków, Escape, wyszukiwania Workspace i katalogu gadżetów,
pustych kolumn oraz przeładowania. Nie było błędów JavaScript ani konsoli.
Nie sprawdzano innych przeglądarek; wtyczka Browser była niedostępna.

## Wspólny wygląd pustych stron (18.10.2026)

Pełne puste widoki korzystają z typografii i odstępów pustego pulpitu oraz
istniejących ilustracji. Wariant `tasks-empty-state--illustrated` jest wspólnym
źródłem stylu, a `shared/EmptyState.tsx` obsługuje pozostałe ekrany React.
Szablony Django zachowują ten sam kontrakt. [Zakres i parametry](UI.md#wspólny-wzorzec-pustej-strony).

Przeszło **158/158 testów** (`core.test_frontend`, `core.test_filter_frontend`,
`core.test_pulpit_frontend`, `core.test_document_frontend`,
`core.test_workspace_frontend`, `resources`, `dashboard.test_for_you`,
`spaces.test_tags`, `spaces.test_management`), build z TypeScriptem,
pięć testów nawigacji oraz kontrola formatu i kompilacja zmienionych szablonów.

Chrome/Playwright na osobnej bazie QA porównał 23 widoki przy 1440×1000,
1024×800 i 390×844: te same rozmiary tekstu, wagi, interlinie i odstępy
co na pustym pulpicie, poprawne grafiki oraz brak przepełnień poziomych.
Sprawdzono tworzenie filtrów, zasobów, zespołów i dokumentów, okno uploadu,
Escape, czyszczenie filtrów, nawigację bez przeładowania, reload,
pusty wynik Workspace, zaproszenia i listę z istniejącym zadaniem.
Przy 390×568 potwierdzono dostępność tekstu i akcji przez przewijanie w siedmiu
widokach; puste Dokumenty przewijają cały obszar wraz z kafelkami tworzenia.
Nie było błędów JavaScript ani HTTP 5xx. Wtyczka Browser była niedostępna;
użyto istniejącego Playwrighta. Nie sprawdzano innych przeglądarek ani wdrożenia.
Skrypty i zrzuty QA pozostają w `/tmp`; bazę i sesję QA usunięto po sprawdzeniu.

## Poprawki po code review (18.10.2026)

Formularz Zasobów używa wspólnego `app-page-modals`, dzięki czemu dodawanie
i edycja działają po nawigacji JSON i ponownym wejściu. Pola dodatkowe zadania
są dostępne w panelu właściwości; odpowiedź walidacji potrafi dodać pole nowej
konfiguracji bez odtwarzania istniejących kontrolek. Uzupełnienie pola zachowuje
i ponawia wcześniejszy szkic autosave. Nie dodano CSS ani nowego komponentu kontrolek.

Usuwanie Workspace blokuje właściciela w transakcji przed wyborem zastępstwa,
więc równoczesne żądania zachowują ostatnie własne miejsce pracy i jego dane.
Zaproszeń oczekujących nie można ukryć przez usunięcie lub archiwizację
powiadomienia; usuwanie zbiorcze je pomija. Starsze stany `is_deleted` nie
ukrywają ważnych zaproszeń. API HTML i React zwracają `deletable_count`
dla całego bieżącego filtra, używany przez przycisk i potwierdzenie usuwania.

Regresje: `workplaces.test_deletions`, `spaces.test_task_autosave`,
`dashboard.test_notifications` i `core.test_shell_frontend`. Przeszło
**1064/1064 testów** w pełnym przebiegu `scripts/run_tests.py --parallel 4`
na osobnych bazach PostgreSQL i tymczasowym storage, TypeScript, build Reacta
oraz pięć testów nawigacji. Modele i migracje pozostały zgodne, bez zmian schematu.

Playwright 1.62.1 z Chrome, na osobnej bazie QA i syntetycznych danych, sprawdził
1440×1000 i 390×844: dodawanie/edycję Zasobów po częściowej nawigacji,
walidację duplikatu, Escape i ponowne wejście, pusty wynik, wymagane pole
dodane podczas edycji zadania, zachowanie szkicu i zapis wartości zero,
odczyt obserwatora oraz odzyskanie wcześniej ukrytego zaproszenia i pominięcie
go w usuwaniu zbiorczym. Referencją był widok „Dla ciebie”. Nie było błędów
wykonania JavaScript ani odpowiedzi HTTP 5xx; 400 przy walidacji były oczekiwane.
Wtyczka Browser nie była dostępna; użyto lokalnego Playwrighta. Skrypty QA
i zrzuty pozostają w `/tmp`, poza repozytorium. Nie sprawdzano innych przeglądarek
ani wdrożenia na serwerze.

## Czysta baza i usunięcie dawnych systemów (18.10.2026)

Zastąpiono dawną historię migracji 11 migracjami początkowymi ośmiu aplikacji.
Usunięto modele Kontaktów, Tasks i osobnego Kanbana, mapowania importu,
trasy zgodności oraz dawne źródła powiadomień. Pozostały tagi Przestrzeni
oraz wspólne komponenty. [Zakres i start](DATABASE.md).

Nowe migracje zastosowano na pustej lokalnej bazie PostgreSQL `ancore`.
Przed resetem wykonano kopię poprzedniej bazy i potwierdzono jej pełne
odtworzenie w tymczasowej bazie. Aplikację przełączono na nową bazę;
poprzednie tabele usunięto. Uploadów na dysku nie kasowano.

Weryfikacja: **1059/1059 testów** w pełnym przebiegu `--parallel 4` (33 s)
i 88 testów ukierunkowanych (24 s), na odrębnych bazach i tymczasowym storage.
Przeszły kontrola Django, brak oczekujących migracji, zgodność modeli,
parsowanie źródeł, aktualność indeksu i `git diff --check`. Nowe migracje
nie są ignorowane przez Git. Sprawdzono linki zmienionych dokumentów.

Lokalny serwer zrestartowano na dotychczasowym porcie. Odczyt HTTP potwierdził
strony logowania i rejestracji oraz przekierowanie anonimowego wejścia do
Przestrzeni. Aktywna baza ma puste konta, przestrzenie i zadania.
Nie zmieniano UI i nie wykonywano kontroli wizualnej w przeglądarce ani wdrożenia.
Zachowano wcześniejsze, niezwiązane zmiany robocze.

## Układ repozytorium

Kod i konfiguracja Django znajdują się w `backend/`. Polecenia poniżej nadal
uruchamiaj przez `manage.py` w katalogu głównym; dodaje on katalog źródeł do
ścieżki importów. Nazwy modułów, etykiety aplikacji i migracje pozostają takie
same. Test runner `ancore.testing.BackendDiscoverRunner` wykrywa testy w
`backend/` również po samym `manage.py test`; jawne etykiety testów działają
jak wcześniej. W zwykłym skrypcie Pythona ustaw `PYTHONPATH` na katalog `backend/`.

Szablony, migracje i testy pozostają wewnątrz swoich aplikacji, React w
`frontend/`, wspólne zasoby w `static/`, a konfiguracja usług w `deploy/`.
Podział wdrożenia na `cli/`, `backend/`, `web/`, `postgres/` i `backup/`,
narzędzia w `scripts/assets/` i `scripts/office/` oraz zasady przechowywania
plików opisuje [Organizacja repozytorium](REPOSITORY.md).
Nieużywaną kopię poprzedniego środowiska Python usunięto na polecenie
użytkownika; bieżące `.venv/` pozostaje w dotychczasowym miejscu. Opcjonalne
`.local/` przechowuje pliki lokalne, a `.cache/` pliki odtwarzalne.
Oba katalogi są wyłączone z Git i builda oraz ukryte w Explorerze.
Nie umieszczaj nowych aplikacji Django w katalogu głównym.
Katalog `files/` zawierał wyłącznie nieużywany cache Pythona i został usunięty;
nie jest modułem aplikacji. Usunięto też puste `deploy/chat/` i `deploy/cypht/`.
Zasady formatu plików zapisuje `.editorconfig`. Wersjonowane
`.vscode/settings.json` ustawia katalog importów i ukrywa cache, zależności,
bundle oraz lokalne dane w Explorerze, bez usuwania ich z dysku.

## Odłączenie dawnych Kontaktów (18.10.2026)

Kontakty nie są modułem aplikacji. Pakiet `backend/contacts` usunięto z katalogu
aplikacji; jedyna zgodność pozostaje w `backend/legacy/contacts`.
`legacy.contacts.apps.LegacyContactsConfig` zachowuje etykietę Django `contacts`,
modele tabel historycznych i niezmienione pliki migracji, ponieważ stare
migracje Tasks/Kanbana i zapisane relacje `Company` nadal odwołują się do tej
etykiety. Nie tworzy nowych tabel, rekordów ani ekranów. Usunięto pusty admin,
a testy braku modułu przeniesiono do `core.test_contact_retirement`.

Bieżące przełączanie Workspace nie wykonuje już backfillu `Company`, `Contact`
ani `UserContact`. Routing Django w `DEBUG` zwraca 404 dla
`/media/company_photos/...`; zachowane pliki
nie są kasowane. Z `contacts.css` usunięto 1551 linii stylów dawnych ekranów.
Pozostałe 460 linii wspólnych menu profilu, selectów i kadrowania przeniesiono
do `shared-controls.css`, z zachowaniem selektorów i kolejności kaskady.
Adres wspólnego arkusza ma nową wersję cache. Generator indeksu obsługuje
jawne konfiguracje Django i pakiety w przestrzeni nazw `legacy`.

Regresje sprawdzają stałą etykietę/tabele, ładowanie dawnych migracji,
relacje firm, brak endpointów i wyników wyszukiwania, brak backfillu po
przełączaniu Workspace oraz zamknięcie publicznego dostępu do zdjęć firm.

Przeszło **1139/1139 testów** w pełnym przebiegu `--parallel 4` (87 s)
oraz 208 testów ukierunkowanych (20 s), na osobnych bazach PostgreSQL
i tymczasowym storage. Kontrola migracji w trybie tylko do odczytu nie
wykazała zmian modeli ani oczekujących operacji; wszystkie dziewięć plików
migracji Kontaktów, łącznie z `__init__.py`, zachowało identyczną zawartość
i Git ich nie ignoruje. Przeszły kontrola Django, parsowanie
444 plików Pythona, kompilacja 186 szablonów, linki i kotwice dokumentacji,
aktualność indeksu oraz `git diff --check`.

Playwright 1.62.1 z Chrome sprawdził menu profilu, picker awatara, upload
syntetycznego obrazu do okna kadrowania, Escape i ponowne wejście na profil,
przy 1440×1000 oraz 390×844. Referencjami były Tagi i Zasoby. Porównanie
obliczonych stylów kontrolek z pierwotnym arkuszem, w tym samym miejscu
kaskady i po wyłączeniu przejść CSS, potwierdziło identyczny wygląd.
Nie było błędów konsoli ani nieudanych żądań. Wtyczka Browser była niedostępna;
użyto lokalnego Playwrighta bez instalowania zależności. Nie zmieniano źródeł
React ani zależności, nie wykonywano wdrożenia ani migracji bazy użytkownika.
Nie sprawdzano innych przeglądarek; skrypty i zrzuty QA pozostają w `/tmp`.

## Usunięcie nieużywanego kodu (18.10.2026)

Po sprawdzeniu routingu, importów i przechodnich zależności szablonów usunięto
stare widoki, formularze i ekrany Projektów, Grup, Zadań, Kanbana oraz Kontaktów.
Usunięto także helpery dawnych katalogów, szablonów projektów i udostępniania,
`project-templates.js`, dawny serwis `dashboard.overview`, nieużywane ilustracje
gadżetów oraz puste pliki Core. Bieżący katalog tagów używa teraz
`tasks.tag_directory`; `tasks.forms` zawiera wyłącznie `TaskTagForm`.

Pozostawiono historyczne modele, wszystkie migracje, mapowania importu,
chronione pliki i przekierowania z aktualnym ACL Przestrzeni. Sygnały czyszczące
stare granty po odebraniu członkostwa pozostają aktywne. Usunięto nieużywane
endpointy/helpery obserwowania i receiver dawnych komentarzy; zapisane
`ObjectFollow`, `ActivityInterest` i `NotificationState` pozostają w bazie.
Współdzielone include'y Tasks, CSS (obecnie `shared-controls.css`), adaptery JS oraz
pierwszy render Django są nadal używane przez aktualną aplikację.

Regresje dotyczą aktualnych endpointów i zachowania danych historycznych.
Usunięto osiem testów wywołujących wyłącznie nieużywane helpery starego pulpitu
i katalogów; testy bieżącej strony głównej zachowano w `dashboard.test_home`.
Pozostałe testy dawnych formularzy sprawdzają odrzucenie zapisów przez routing.
Test czasu pracy mockuje teraz zegar rzeczywistej implementacji `core.work_logs`.
Zachowano wcześniejsze zmiany robocze, bez wdrożenia ani migracji bazy użytkownika.

Zakres usunięcia: **79 plików** (33 Python, 42 szablony HTML, jeden JS,
dwie ilustracje SVG i ich opis); bieżące testy strony głównej przeniesiono
do `test_home.py`, a katalog tagów wydzielono do `tag_directory.py`.
Trzy historyczne pliki modeli i wszystkie 178 plików migracji, łącznie
z `__init__.py`, są identyczne z wersjonowanym stanem sprzed porządkowania.

Weryfikacja: **1137/1137 testów** w pełnym przebiegu `--parallel 4` (90 s),
bez pominięć, oraz 98 testów ukierunkowanych sekwencyjnie (121 s).
Każdy przebieg używał osobnej bazy PostgreSQL i tymczasowego storage.
Przeszły kontrola Django, TypeScript i build Reacta, parsowanie 444 plików
Pythona, kompilacja 186 szablonów, linki i kotwice dokumentacji,
aktualność indeksu oraz `git diff --check`. Kontrola migracji w trybie
tylko do odczytu nie wykazała zmian modeli ani oczekujących operacji.

Playwright 1.62.1 ze zainstalowanym Chrome, na osobnej bazie QA, sprawdził
1440×1000 i 390×844: katalog tagów, walidację duplikatu, zapis, pusty wynik
i przywrócenie wyszukiwania, sortowanie, przejście do listy i Wstecz
w tym samym dokumencie, szczegóły zadania, zakładki, modal czasu i Escape.
Ekranami referencyjnymi były Zasoby i pulpit domyślny. Nie było przepełnienia
całej strony ani nieoczekiwanych błędów konsoli/HTTP; 400 przy duplikacie tagu
było oczekiwaną walidacją. Wtyczka Browser nie była dostępna; użyto lokalnego
Playwrighta, bez instalowania zależności. Zrzuty i skrypty QA pozostają w `/tmp`,
poza repozytorium. Nie sprawdzano wszystkich ekranów ani innych przeglądarek.

## Utrzymanie zestawu regresji (18.10.2026)

Zestaw sprawdza aktywną aplikację oraz zachowanie historycznych danych.
Dawne scenariusze tworzenia/edycji Projektów, Grup, katalogów Tasks,
szablonów i ich udostępniania usunięto po wycofaniu tych ekranów. Ich
kontrakt zastępują `tasks.test_retirement` i `kanban.test_retirement`:
404 dla usuniętych endpointów, 409 dla dawnych zapisów, przekierowania
zgodności z aktualnym ACL i zachowanie danych. Nie zmieniono wykrywania
testów i nie dodano `skip`, `expectedFailure` ani filtrowania błędów.

Regresje nadal używanych mechanizmów przeniesiono na aktualne modele:

| Mechanizm | Bieżące testy |
| --- | --- |
| Komentarze, załączniki, rollback i prywatne pobieranie | `core.test_comment_images`, `spaces.test_task_detail_parity` |
| Status, zakończenie, historia i równoczesny zapis | `core.test_status_updates`, `spaces.test_write_access` |
| Stałe klucze zadań i granice Workspace | `core.test_task_integrity`, `workplaces.test_team` |
| Wyszukiwanie i ostatnio oglądane | `dashboard.test_search_regressions`, `dashboard.tests` |
| Wzmianki, inbox, paginacja i operacje zbiorcze | `dashboard.test_collaboration`, `dashboard.test_notifications` |
| Osobiste przypomnienia | `dashboard.test_reminders` na `SpaceTaskReminder` |
| Dziennik pracy, DST, walidacja i transakcje | `spaces.test_work_logs` (przeniesione z `tasks.test_work_logs`) |

Zachowano testy migracji, numeracji i przechowywanych modeli Tasks, w tym
prywatności, członkostw, historycznych szablonów i czasu pracy. Test migracji
identyfikatorów Workspace buduje teraz dane ze stanu rzeczywiście
zastosowanych migracji; cofnięcie `workplaces.0010` cofa także zależne
migracje innych aplikacji. Dzięki temu historyczny model nie żąda kolumny
`legacy_slug`, której cofnięty schemat jeszcze nie zawiera. Nie wymagało to
zmiany migracji ani modeli produkcyjnych.

Testy zapisu AJAX oczekują JSON 200 i sprawdzają zapis, historię oraz ponowny
odczyt. Testy Workspace używają Przestrzeni i bieżącej powłoki; testy
wycofanych Kontaktów/Dokumentów potwierdzają brak dawnych wyników
wyszukiwania. `spaces.testing.make_task` tworzy jawne fixture'y bieżących
zadań, z kontrolą właściciela i Workspace.

Pełny, izolowany przebieg uruchamiaj z katalogu repozytorium:

```sh
.venv/bin/python scripts/run_tests.py
# Opcjonalnie wybrane etykiety i standardowe flagi Django:
.venv/bin/python scripts/run_tests.py core.test_status_updates spaces.test_work_logs --verbosity 2
```

[Skrypt](../scripts/run_tests.py) używa standardowego polecenia Django `test` i istniejącego
`BackendDiscoverRunner`. Nadaje bazie testowej unikatową nazwę, ustawia
MEDIA/PRIVATE/STATIC_ROOT w katalogu tymczasowym i sprząta storage po
zakończeniu. Tylko połączenia tego procesu dostają wyłączony PostgreSQL JIT
i limit zapytania 60 s (można nadpisać przez `PGOPTIONS`). Nie uruchamia
migracji na bazie z danymi użytkownika. Tak jak `manage.py test`, wymaga
uprawnień PostgreSQL do utworzenia i usunięcia bazy testowej oraz zbudowanego
bundla `frontend/app`.

Test otwarcia edytorów Dysku (`documents.test_drive_office`) sprawdza
ścieżkę źródła i ważność podpisanego tokenu. Nie porównuje dwóch osobno
wygenerowanych podpisów: ich znacznik czasu może zmienić się pomiędzy
wywołaniami. Usuwa to losową porażkę na granicy sekundy, bez zmiany
mechanizmu podpisywania lub czasu ważności adresów.

Pełny przebieg ujawnił również timeout grupowania obciążenia w podsumowaniu
Przestrzeni dla 106 zadań. `spaces.summary.materialized_summary_items`
oddziela istniejący zakres ACL/filtrów od agregacji przez PostgreSQL
`MATERIALIZED` CTE, zachowując ten sam snapshot i kontrolę widoczności.
`spaces.test_summary` sprawdza pełne sumy z podzadaniami przy limicie 2 s
na zapytanie oraz obciążenie przed nadaniem i po odebraniu dostępu.
Nie zmieniono limitu 60 s całego runnera ani ustawień serwera PostgreSQL.

Końcowa weryfikacja na Pythonie 3.15/Django 6.1.2: **1145/1145 testów**
przeszło sekwencyjnie (397 s) oraz równolegle, `--parallel 4` (87 s),
bez pominięć i oczekiwanych porażek. Liczba zmalała z 1407 po usunięciu
scenariuszy wycofanych ekranów i przeniesieniu bieżących regresji; żaden
test nie jest wyłączony w runnerze. Każdy przebieg używał odrębnej bazy
PostgreSQL i tymczasowego storage, usuniętych po zakończeniu.
Przeszły kontrola Django, `pip check`, parsowanie zmienionych źródeł,
lokalne linki dokumentacji, aktualność indeksu oraz `git diff --check`.
Nie zmieniono UI, modeli, migracji ani zależności. Nie uruchamiano przeglądarki,
nie wykonano wdrożenia ani migracji bazy z danymi użytkownika.

Poniższe zapisy aktualizacji zachowują wyniki historycznych przebiegów,
w tym wcześniejsze 395 nieudanych przypadków spośród 1407 testów.

## Aktualizacja zależności (17.10.2026)

W `requirements.txt` oraz lokalnym `.venv` zaktualizowano trzy pakiety:

- `python-dotenv`: 1.2.2 → **1.2.4** ([zmiany](https://github.com/theskumar/python-dotenv/blob/main/CHANGELOG.md#124---2026-10-01));
- PyJWT: 2.14.0 → **2.15.1** ([zmiany](https://pyjwt.readthedocs.io/en/stable/changelog.html#v2-15-1));
- `sqlparse`: 0.5.5 → **0.6.0** ([zmiany](https://sqlparse.readthedocs.io/en/latest/changes.html#release-0-6-0-aug-13-2026)).

PyJWT 2.15 dodaje obsługę Pythona 3.15. Django 6.1.2, `asgiref` 3.12.1
i `psycopg2-binary` 2.9.13 zachowano. Wersje sześciu zależności pozostają
przypięte operatorem `==`. Dodatkowe lokalne narzędzia nie są zależnościami
aplikacji; `fonttools` pozostaje osobną zależnością skryptu regenerowania ikon.
Docelową wersję Pythona opisują instrukcja startu i komentarz
w `requirements.txt`; projekt nie zawiera pliku `.python-version`.

Instalację sprawdzono w czystym środowisku Python 3.15, zawierającym wyłącznie
`requirements.txt` i pip. Przeszły `pip check`, kontrola Django oraz wszystkie
**137 testów**: `core.test_project_layout`, `accounts.test_frontend`,
`accounts.test_email_identity.EmailIdentityTests`, `documents.test_suite`,
`documents.test_drive_office`, `documents.test_office_extras`,
`documents.test_office`, `core.test_document_frontend`,
`core.tests.UploadValidationTests` i `spaces.test_tags`. Testy korzystały
z osobnej bazy PostgreSQL i storage w `/tmp`.

Przeszły również kontrola istniejącej bazy w trybie tylko do odczytu,
`makemigrations --check --dry-run`, `migrate --plan`,
`collectstatic --dry-run --noinput`, kompilacja 228 szablonów, parsowanie
485 plików Pythona, linki dokumentacji, indeks oraz `git diff --check`.
Pełnego zestawu 1407 testów po tej aktualizacji zależności nie ponawiano.

## Aktualizacja do Pythona 3.15 (17.10.2026)

Docelowa wersja interpretera to [**Python 3.15.0**](https://www.python.org/downloads/release/python-3150/),
opisana w `requirements.txt` i instrukcji startu. Odtworzono `.venv` na zainstalowanym interpreterze
3.15.0 z python.org. Zastane środowisko miało zerwane odwołania do usuniętej
instalacji Homebrew 3.14; jego kopię zachowano wówczas w `venv.bak/` poza Git
(nieużywane archiwum usunięto 22.10.2026 na polecenie użytkownika).
Ponownie zainstalowano zależności projektu i dziesięć dodatkowych pakietów
lokalnych z poprzedniego środowiska, bez kopiowania `site-packages`.
Środowisko nadal zawiera 17 pakietów; pip pochodzi z nowego interpretera
i ma wersję 26.2.1 (wcześniej 26.1.2).

`psycopg2-binary` podniesiono z **2.9.12** do **2.9.13**, które jako pierwsze
[dodaje obsługę Pythona 3.15](https://www.psycopg.org/docs/news.html#what-s-new-in-psycopg-2-9-13).
Zainstalowano gotowy wheel dla CPython 3.15 i macOS arm64. Pozostałe wersje
z `requirements.txt` zachowano. Nie zmieniają się modele ani migracje.

Django pozostaje w wersji **6.1.2**. Jego [oficjalna macierz zgodności](https://docs.djangoproject.com/en/6.1/faq/install/#what-python-version-can-i-use-with-django)
obejmuje Python 3.12–3.14, więc lokalna weryfikacja na 3.15 nie oznacza
oficjalnego wsparcia tej konfiguracji przez Django.

Pełny przebieg na Pythonie 3.15 wykonał **1407 testów** na osobnej bazie
PostgreSQL i storage w `/tmp`, z wyłączonym JIT PostgreSQL oraz limitem
60 sekund na zapytanie. Wynik to **499 nieudanych asercji i 138 błędów
w 395 przypadkach testowych**. Porównanie z zachowanym raportem wcześniejszego
przebiegu na Pythonie 3.14.8 wykazało tę samą listę nieudanych przypadków
i te same liczby. Różnice komunikatów wynikały z losowych identyfikatorów, tokenów, kodów
Przestrzeni i tagów, domyślnych nazw Workspace oraz czasu utworzenia danych
testowych. Pełny zestaw nadal nie jest zielony.
W tym zadaniu nie uruchamiano ponownie testów na 3.14: ten interpreter
nie był już zainstalowany.

Na Pythonie 3.15 przeszły cztery testy `core.test_project_layout`, aktywacja
środowiska, `pip check`, kontrola Django z PostgreSQL 18.6,
`makemigrations --check --dry-run`, `migrate --plan`,
`collectstatic --dry-run --noinput`, kompilacja 228 szablonów i parsowanie
485 plików Pythona. Przeszedł również build Reacta z kontrolą TypeScriptu;
użyto Node.js z runtime Codex, ponieważ `node` nie był dostępny w `PATH`.
Kontrole istniejącej bazy wykonano w trybie tylko do odczytu. Sprawdzono
lokalne linki i kotwice dokumentacji, aktualność indeksu oraz `git diff --check`.

Nie wykonywano wdrożenia, migracji bazy użytkownika ani weryfikacji
w przeglądarce; aktualizacja nie zmienia kodu interfejsu.

## Poprzednia aktualizacja Pythona 3.14 (17.10.2026)

Poniższy zapis przedstawia stan sprzed przejścia na 3.15.

Lokalny interpreter projektu podniesiono z **3.14.6** do
[**3.14.8**](https://www.python.org/downloads/release/python-3148/), najnowszego
wydania serii wspieranej przez Django 6.1.2. Python 3.15.0 jest nowszy,
ale nie figuruje jeszcze w [macierzy zgodności Django 6.1](https://docs.djangoproject.com/en/6.1/faq/install/#what-python-version-can-i-use-with-django).
Wybraną wersję zapisuje `.python-version`.

Python 3.14.8 został zainstalowany przez Homebrew, a `.venv` odtworzono
z zachowaniem wersji wszystkich **17** wcześniejszych pakietów, także narzędzi
lokalnych spoza `requirements.txt`. Poprzednie środowisko zachowano lokalnie
w `venv.bak/python-3.14.6` (poza Git; nieużywane archiwum usunięto później,
22.10.2026, na polecenie użytkownika). Instalacja frameworka Python 3.14.6
pozostaje dostępna pod pełną ścieżką. Lokalna konfiguracja `~/.zprofile`
i `~/.zshrc` nadaje pierwszeństwo Pythonowi Homebrew dla `python3`, `python3.14`
i `pip3`, zachowując aktywne środowiska wirtualne. Wcześniejszy wpis instalatora
python.org w `~/.zprofile` wskazywał nadal 3.14.6 mimo aktualizacji `.venv`.
Po korekcie sprawdzono wersję 3.14.8 w powłokach login i non-login, także ze
starym odziedziczonym `PATH`, oraz zachowanie interpretera aktywnego `.venv`.
Otwarte wcześniej terminale wymagają przeładowania powłoki (`exec zsh -l`)
albo otwarcia nowej sesji.

Na obu interpreterach wykonano po **1407 testów** na osobnych bazach PostgreSQL
i storage w `/tmp`, z wyłączonym JIT oraz limitem 60 sekund na zapytanie.
Na 3.14.6 runner zgłosił 499 nieudanych asercji i 139 błędów w 396 testach;
na 3.14.8 — 499 asercji i 138 błędów w 395 testach. Nie pojawiły się nowe
nieudane przypadki; istniejące problemy zachowały miejsca i przyczyny po
pominięciu losowych identyfikatorów, tokenów i danych odpowiedzi.
Dodatkowy błąd starego interpretera to timeout
`spaces.test_summary.SpaceSummaryTests.test_priority_type_and_workload_totals_include_all_pages_and_subtasks`;
na nowym interpreterze ten test przeszedł. Pełny zestaw nadal nie jest zielony.

W końcowym `.venv` przeszły cztery testy `core.test_project_layout`, aktywacja
środowiska, `pip check`, kontrola Django z bazą, `makemigrations --check --dry-run`,
`migrate --plan`, `collectstatic --dry-run --noinput`, kompilacja 228 szablonów
oraz parsowanie 485 plików Pythona. Sprawdzono też lokalne linki dokumentacji,
aktualność indeksu i `git diff --check`. Nie ma nowych ani oczekujących migracji.
Nie wykonywano wdrożenia, migracji bazy użytkownika ani kontroli w przeglądarce;
aktualizacja nie zmienia UI.

## Aktualizacja Django (17.10.2026)

Django podniesiono z **6.0.7** do **6.1.2** w `requirements.txt` i lokalnym
`.venv`, zgodnie z [oficjalnym stabilnym wydaniem](https://www.djangoproject.com/download/).
Pozostałe przypięte zależności zachowano; `pip check` potwierdził ich zgodność.
Wymagania uruchomienia to Python 3.12–3.14 i PostgreSQL 15+; lokalnie sprawdzono
Python 3.14.6 i PostgreSQL 18.6.

Przeszły kontrola Django z bazą, `makemigrations --check --dry-run`,
`migrate --plan`, `collectstatic --dry-run --noinput`, kompilacja wszystkich
228 szablonów, lokalne linki dokumentacji, aktualność indeksu i `git diff --check`.
Nie ma zmian modeli ani nowych/oczekujących migracji. Kontrole istniejącej
bazy wykonano w trybie tylko do odczytu; testy używały osobnych baz PostgreSQL
i storage w `/tmp`, z wyłączonym JIT oraz limitem 60 sekund na zapytanie.

Pełne przebiegi wykonały po **1407 testów** na Django 6.0.7 i 6.1.2.
Na obu wersjach odtworzono te same **395 nieudanych testów** (wiele zawiera
nieudane podprzypadki): 275 w Tasks, 58 w Dashboard, 29 w Workspace,
28 w Core, dwa w Contacts, dwa w Spaces i jeden w Documents. Większość
dotyczy wycofanych modułów; aktualizacja nie przywraca ich operacji.
Runner zgłosił na starej wersji 499 nieudanych asercji i 138 błędów,
na nowej 499 asercji i 139 błędów. Wynik nie oznacza zielonego zestawu regresji.

Jedyna dodatkowa różnica to przekroczenie limitu zapytania w
`spaces.test_backlog_planning.BacklogPlanningTests.test_totals_include_all_pages_and_closed_sprint_is_not_planned`.
Ten test przeszedł osobno na obu wersjach w mniej niż sekundę, a cały moduł
`spaces.test_backlog_planning` na 6.1.2 przeszedł **22/22** w 2,5 sekundy.
Porównanie SQL wykazało zgodność po pominięciu nowego cytowania aliasów.
Timeoutu nie odtworzono na czystych bazach; stabilność czasu tego zapytania
w pełnym przebiegu pozostaje ograniczeniem weryfikacji.

Nie wykonywano wdrożenia, migracji bazy użytkownika ani sprawdzenia
w przeglądarce; aktualizacja nie zmienia kodu interfejsu.

## Weryfikacja przeniesienia backendu (17.10.2026)

Porównanie sum kontrolnych zachowało wszystkie 712 plików źródłowych obecnych
przed przeniesieniem, w tym wcześniejsze zmiany robocze. W istniejącym kodzie
backendu zmieniono jedynie ustawienie katalogów i test runnera w konfiguracji;
nowe pliki to runner i cztery testy struktury. Modele, migracje, szablony,
widoki i wcześniejsze testy pozostały identyczne. Zachowano 75 modeli i nazw
tabel, 451 wzorców URL, 185 migracji odczytywanych przez Django oraz ścieżki
storage. Wszystkie 178 lokalnych plików migracji (łącznie z `__init__.py`)
pozostały dostępne do wersjonowania. Domyślne wykrywanie znajduje 1402 testy:
1398 wcześniejszych i cztery nowe.

Przeszły kontrola Django, składnia Pythona, build Reacta z TypeScriptem,
`makemigrations --check --dry-run`, odczyt planu migracji, `collectstatic
--dry-run --noinput` (1325 zasobów), linki lokalne dokumentacji, indeks kodu
oraz `git diff --check`. Plan nie wykazał oczekujących migracji. Nowe testy
potwierdziły uruchomienie `manage.py` spoza repozytorium, importy WSGI/ASGI
z `backend/` na ścieżce importów, wykrywanie testów oraz dostęp do szablonów
i lokalizacje domyślnego storage.

Regresję wykonano na osobnych bazach PostgreSQL i storage w `/tmp`.
Zestaw obejmował wspólne API i powłokę React, konta, Zasoby, Przestrzenie,
Workspace, Filtry, nawigację Pulpitów, Planner, Dokumenty i zgodność wycofanych
modułów. Końcowy przebieg wykonał **625 testów: 622 sukcesy, dwie nieudane
asercje i jeden błąd**. Trzy problemy odtworzono na kopii kodu sprzed przeniesienia.
Dwa kolejne wcześniejsze błędy potwierdzono w pierwszym przebiegu i osobno
na tej samej kopii; pominięto je w końcowym zestawie:

| Testy z wcześniejszym problemem | Obserwacja na kodzie przed i po przeniesieniu |
| --- | --- |
| `spaces.test_issue_types.IssueTypeTests.test_detail_edit_and_reopen_keep_type_and_history` oraz `test_other_detail_edits_do_not_reset_type` | Oczekiwane 302, odpowiedź 200 |
| `core.test_contact_retirement.RetiredContactDirectoryTests.test_legacy_favorites_do_not_restore_retired_directories` | Oczekiwana usunięta sekcja „Starsze widoki” |
| `core.test_contact_retirement.RetiredContactDirectoryTests.test_search_omits_retired_records_and_navigation` | Oczekiwana usunięta grupa wyników `projects` |
| `documents.tests.DocumentLibraryTests.test_workspace_view_search_tag_pagination_and_actions_keep_workspace_scope` | Oczekiwana usunięta grupa wyników `tags` |

Pierwszy przebieg przerwano na
`spaces.test_summary.SpaceSummaryTests.test_priority_type_and_workload_totals_include_all_pages_and_subtasks`
z powodu wielominutowego zapytania agregującego. Anulowano wyłącznie zapytanie
w tymczasowej bazie testowej; wszystkie bazy testowe zostały usunięte przez
runnera. Dziesięć testów `spaces.test_summary` pominięto w końcowym przebiegu.
Nie wykonano całego zestawu 1402 testów ani weryfikacji w przeglądarce;
porządkowanie nie zmieniło UI. Nie wykonywano wdrożenia ani migracji bazy
z danymi użytkownika. Konfiguracja serwera WSGI/ASGI przy następnym wdrożeniu
wymaga dodania `backend/` do ścieżki importów zgodnie z sekcją „Wdrożenie”.

## Dokończenie frontendu React (16.10.2026)

Wspólną powłokę renderuje teraz `src/shell/Shell.tsx`. Nawigacja używa JSON
z `api/v1/navigation/`, a same kolekcje i Favorites można odświeżyć przez
`api/v1/shell/` bez utraty szkicu strony. Oba endpointy mają zwykły i scoped
adres, wymagają sesji i zachowują aktualne uprawnienia Django. Stare kontrolery
menu/nawigacji/toastów nie są ładowane w aktywnej powłoce. Szczegóły kontraktu:
[Frontend React](FRONTEND.md#powłoka-i-nawigacja-json).

Przeszło **246 testów** na oddzielnej bazie PostgreSQL: 14 nowych w
`core.test_navigation_frontend`, a także `core.test_shell_frontend`,
`core.test_frontend`, `core.test_document_frontend`, `core.test_filter_frontend`,
`core.test_pulpit_frontend`, `core.test_workspace_frontend`, `accounts.test_frontend`,
całe `resources`, `spaces.test_navigation`, `spaces.test_task_detail_parity`,
`spaces.test_tags`, `dashboard.test_pulpit_navigation`, `dashboard.test_filters`,
`workplaces.test_management` i `workplaces.test_defaults`.
Nowe testy obejmują wszystkie rodzaje ekranów, typowane pickery/Favorites,
osobisty i kompletny porządek, CSRF (odrzucenie oraz poprawny token z nawigacji),
prywatne zadania/Przestrzenie, odebrane członkostwo, obcy i zmieniony w innej
karcie Workspace, tryby zarządzania oraz brak starych kontrolerów w powłoce.

Browser QA: Chrome przez istniejący Playwright, 1440×900, 1024×900 i 390×900
(oraz 390×844 bez localStorage), lokalny serwer z fikcyjnymi danymi i osobną
bazą. Klasyfikacja: **Browser plugin not available**; użyto dostępnego
Playwright/Chrome. Nie instalowano nowych zależności. Tymczasowe skrypty,
logi i zrzuty pozostały poza repozytorium; serwer i baza QA zostały usunięte.

| Sprawdzenie | Wynik |
| --- | --- |
| Adres, tytuł i właściwy ekran | OK dla 12 modułów, zwykłych/scoped tras |
| Treść i brak overlay błędu frameworka | OK |
| Konsola i błędy wykonania | Brak nieoczekiwanych błędów |
| Wygląd i responsywność | Zrzuty przy trzech szerokościach, bez overflow |
| Wzorzec poprzedniego menu | Zgodne wymiary nagłówka, sidebaru, sekcji i wierszy |
| Interakcje | OK, scenariusze poniżej |

Sprawdzono rzeczywiste linki, JSON zamiast dokumentów HTML przy przejściach,
trwałość powłoki, Wstecz/Dalej, query/hash i kategorię `#security`, przewijanie
oraz aktywność menu. Szerokość działa myszą i klawiaturą (Home/End, strzałki,
reset), zachowuje się po reloadzie; to samo dotyczy grup i Favorites.
Przeciągnięcie rzeczywiście dodaje/usuwa skrót, Alt+strzałki zapisują kolejność.
Naprawiono konflikt natywnego drag linku z gestem wskaźnika.

Pickery mają wyniki/stan pusty oraz brak dostępu do prywatnej Przestrzeni,
strzałki, Escape i powrót fokusu także ze zwiniętego paska. Sprawdzono
normalizację wyszukiwania Workspace, natywne przełączenie Workspace i powrót,
reset dokumentu po zmianie konta lub bundla, zachowanie ustawień bez storage.
Gwiazdka odświeża menu bez utraty zapytania Zasobów. Modal z menu zachowuje
`inert`, szkic i potwierdzenie odrzucenia; anulowanie pozostawia edycję.
Wstecz po wpisach hash z niezapisanym modalem przywraca właściwy wpis historii.
Zagnieżdżony powrót edytor→katalog→Ustawienia zachowuje kontekst po reloadzie.
Awaria 503 pozostawia ekran i pozwala ponowić, a spóźniona odpowiedź nie
zastępuje nowszej. Regresyjnie sprawdzono wyszukiwanie globalne, powiadomienia,
Sticker oraz deduplikację/zamykanie toastów. Menu/pickery mobilne mieszczą
się w oknie, a zamknięcie przywraca interaktywność treści.

Przeszły produkcyjny `pnpm --dir frontend/app build` (w tym TypeScript),
Prettier, kontrola Django, składnia Pythona, lokalne linki dokumentacji,
indeks kodu i `git diff --check`. Nie zmieniono modeli, migracji ani zależności.
Nie uruchamiano całego historycznego zestawu repozytorium, Safari/Firefox,
rzeczywistego urządzenia dotykowego ani produkcyjnego ONLYOFFICE. Nie wykonano
wdrożenia produkcyjnego; przed nim nadal trzeba zbudować bundle i wykonać
`collectstatic` zgodnie z rozdziałem Frontend.

## Globalne panele w React (16.10.2026)

`core.test_shell_frontend` sprawdza bootstrap i brak równoległych starych
handlerów, sesję/CSRF, scoped wyszukiwanie i ostatnio oglądane z ponowną
kontrolą ACL, jawny kontrakt powiadomień, dostępne Workspace, filtry,
podpisaną paginację, odczyt/archiwum/usunięcie, zaproszenia, wzmianki,
przypomnienia i osobiste operacje zbiorcze ograniczone snapshotem.
Uruchamiaj razem z `core.test_frontend`, `accounts.test_frontend`,
`spaces.test_task_detail_parity`, `spaces.test_tags` oraz regresjami dostępu
Workspace w `dashboard.test_search_regressions`.

Weryfikacja: wszystkie **85 testów** powyższego zestawu (w tym 16 nowych)
przeszły na oddzielnej bazie PostgreSQL. Z regresji wyszukiwania uruchomiono
`test_workspace_results_follow_viewer_memberships_not_data_owner` oraz
`test_revoked_membership_removes_workspace_and_business_results`;
pozostałe historyczne testy Tasks nie stanowią opisu aktywnego modułu.
Nie zmieniano modeli, migracji ani zależności.

Playwright/Chrome na izolowanym QA sprawdził wyszukiwanie, filtry typów,
ostatnio oglądane, stany pusty/błąd, opóźnioną odpowiedź, skróty i klawiaturę,
częściowe przejście do zadania, listę powiadomień na trzech stronach,
archiwizację/przywracanie, filtrowanie Workspace i zachowanie filtrów po
ponownym otwarciu. Sprawdzono polling z jawnym odświeżeniem czytanej listy,
usunięcie zaproszenia z potwierdzeniem/anulowaniem, aktualizację licznika,
zbiorczy odczyt i przejście po oznaczeniu wpisu jako przeczytany.
Sticker sprawdzono przez zapis tekstu, drag, zmianę rozmiaru klawiaturą,
przejście do Zasobów i reload oraz zmianę konta w tym samym localStorage.
Wyszukiwanie porównano z dawnym panelem. Szerokości 1440, 1024 i 390 px
nie miały przepełnienia dokumentu ani nieoczekiwanych błędów JS/konsoli.

Osobny przebieg sprawdził Ctrl+K z powiadomień, Home/End i `/`, błąd odczytu
oraz kolejnej strony z zachowaniem kart i kursora, błąd zapisu bez zmiany
stanu oraz ponowienie. Błąd pollingu zachowywał licznik. Sprawdzono kolejność
Escape w menu/panelu, fokus i zamknięcie tłem, ochronę edytora profilu,
Escape powiadomień na ekranie Zasobów, Back/Forward bez podwójnego korzenia,
potwierdzenie zbiorczego usunięcia z archiwum oraz działanie Stickera na
telefonie z wyłączonym localStorage. Nie było błędów JS/konsoli.
Końcowe porównanie ze starym panelem powiadomień potwierdziło tę samą
geometrię okna i treść przy 1440 i 390 px. Serwer, baza, metadane sesji
i storage QA zostały usunięte po sprawdzeniu.

Browser plugin był niedostępny, użyto lokalnego Playwrighta z Chrome.
Nie uruchamiano całego zestawu repozytorium ani Safari/Firefox.
Build/typecheck, formatowanie, kontrola Django, składnia Python/JS,
indeks, lokalne linki i `git diff --check` przeszły.

## Konta i profil w React (16.10.2026)

`accounts.test_frontend` sprawdza publiczne i prywatne API kont, zamkniętą
listę adresów/metod, walidację i brak haseł w odpowiedzi, CSRF i jego rotację,
rejestrację bez logowania, niezmienny cel logowania, profil i upload/kadr,
status, udowodnione uwierzytelnienie przełączanych kont oraz wylogowanie.
Uruchamiaj razem z `accounts.test_login_redirects`, `accounts.tests`,
`accounts.test_avatars` i `accounts.test_email_identity.EmailIdentityTests`.
Po zmianie wspólnego adaptera awatara sprawdzaj także `core.test_frontend`,
`core.test_workspace_frontend`, `workplaces.test_avatars`,
`workplaces.test_management` i `workplaces.test_invitation_candidates`.

Weryfikacja: przeszły wszystkie **72 testy kont** (w tym 17 nowych) oraz
**65 testów wspólnego API i Workspace**, na oddzielnych bazach PostgreSQL.
Build/typecheck, formatowanie, kontrola Django, składnia Pythona/JS,
indeks dokumentacji, linki i `git diff --check` przeszły.
Nie zmieniano modeli, migracji ani zależności.

Playwright z lokalnym Chrome na oddzielnej bazie i storage QA sprawdził
logowanie, rejestrację, dodanie/przełączenie/usunięcie konta, profil,
walidację, status, 30 awatarów, kadrowanie/zoom, usunięcie zdjęcia i reload.
Porównano logowanie/rejestrację/profil z dawnym renderowaniem szablonów.
Sprawdzono desktop 1440, tablet 1024 i telefon 390 px, błędy 503 i 401
z zachowaniem szkicu/ponowieniem, blokadę podwójnej rejestracji, fokus,
Escape i niezapisane zmiany, powrót przez Zasoby oraz Back/Forward.
Osobny przebieg potwierdził współdzielony picker i zapis awatara Workspace,
odrębną pulę użytkownika oraz czyszczenie zagnieżdżonych okien po ponownym
wejściu. Nie było nieoczekiwanych błędów konsoli ani JS. Browser plugin był
niedostępny. Nie sprawdzano Safari/Firefox ani całego zestawu repozytorium.
Serwer QA i jego baza zostały usunięte po sprawdzeniu.

## Etapowa migracja do Reacta (16.10.2026)

Przeniesione ekrany wymagają zbudowanego `frontend/app` przed uruchomieniem
aplikacji, testami renderującymi te ekrany i `collectstatic`. Aktualny zakres
i końcowa weryfikacja są w rozdziale „Kontynuacja migracji React” poniżej:

```sh
pnpm --dir frontend/app install --frozen-lockfile
pnpm --dir frontend/app build
.venv/bin/python manage.py test resources
```

Wymagania, tryb obserwowania plików, deployment i kontrakt API opisuje
[Frontend React](FRONTEND.md). Nie ma nowych zależności Python ani migracji.
`resources.test_api` sprawdza CRUD JSON, scoped i zwykłe adresy, właściciela,
autora, aktywne osoby, walidację, izolację Workspace, cofnięcie członkostwa,
CSRF, kody błędów i bezpieczny bootstrap. Uruchamiaj razem z `resources.tests`
i testami kontekstu Workspace oraz logowania. Browser QA obejmuje listę
referencyjną, CRUD, walidację i sieć, filtry, kolumny, Escape/fokus,
bezpośredni edytor, ponowne wejście, historię nawigacji i telefon.

Weryfikacja 16.10.2026: wszystkie 35 testów Zasobów (w tym 16 nowych API)
przeszły na osobnej bazie PostgreSQL. Szerszy przebieg 113 testów miał
99 sukcesów, 11 nieudanych asercji i 3 błędy. Te same 14 problemów odtworzono
na niezmienionym HEAD w osobnej kopii i bazie: testy `workplaces.test_team`
odwołują się do wycofanego Tasks, a test migracji identyfikatorów zgłasza
brak kolumny `legacy_slug`. Nie przywracano historycznych funkcji.

Playwright/Chrome na izolowanym QA przy 1440×1000, 1024×900 i 390×900
potwierdził listę i formularz referencyjny, rzeczywisty CRUD przez JSON,
walidację z zachowaniem pól, błąd odczytu/zapisu i ponowienie, nowszy tekst
podczas opóźnionego wyszukiwania, filtry, sortowanie, paginację, kolumny
z obsługą klawiatury i trwałością, zaznaczenia, Escape i porzucenie szkicu,
bezpośredni edytor, zwykły/scoped URL, powrót i Wstecz/Dalej, pusty Workspace
oraz brak przepełnienia i nieoczekiwanych błędów konsoli/JS. Plugin Browser
był niedostępny. Nie sprawdzano Safari/Firefox ani całego repozytorium.
Instalacja z lockfile, build, typy, format, start trybu watch, kontrola Django,
składnia Pythona i JS, linki dokumentacji, indeks i diff przeszły.

## Usunięcie statusu zapisu z nagłówka (15.10.2026)

Nagłówek szczegółów zadania zawiera powrót i tytuł. Automatyczny zapis
uruchamia `data-space-task-autosave` formularza; widoczny status nie jest
wymagany do jego działania. `data-save-state` przechowuje stan, a komunikaty
otrzymuje wyłącznie czytnik ekranu. Błąd pokazuje przycisk „Spróbuj ponownie”
w banerze. `noscript` zachowuje zwykły zapis formularza.

Playwright/Chrome na osobnej bazie i storage QA przy 1440×1000 i 390×900
potwierdził brak statusu w nagłówku przed/w trakcie/po zapisie i przy błędzie,
zapis tytułu/opisu, nowszą edycję podczas żądania, zakończenie zadania,
załączniki, zachowanie szkicu i ponowienie z banera, ochronę wyjścia,
listę referencyjną, częściową nawigację, ponowne wejście i reload.
Sprawdzono także obserwatora bez edycji i rzeczywisty zapis z wyłączonym JS.
Nie było przepełnienia telefonu ani nieoczekiwanych błędów konsoli/JS.
Plugin Browser był niedostępny. Kontrola Django, składni JS, indeksu i
`git diff --check` przeszła. Backend nie zmienił się; jego testów nie ponawiano.
Safari i Firefox nie były sprawdzane.

## Automatyczny zapis szczegółów zadania (14.10.2026)

`spaces.test_task_autosave` sprawdza zapis JSON, zwykły/scoped adres i zwykły
POST, niezmienione dane bez dodatkowej historii, autora, zachowanie bieżących
właściwości i planowania, precyzję dat, wyczyszczenie opcjonalnych pól,
zerową wartość pola niestandardowego, status/zakończenie/ponowne otwarcie,
walidację formularza i plików z rollbackiem, odświeżenie członków, CSRF,
obserwatora, prywatne zadanie i obcy Workspace. Uruchamiaj także
`spaces.test_task_detail_parity`, `spaces.test_independent_tasks`, testy tagów
oraz `core.test_file_lifecycle`.

Browser QA: tytuł/opis → zapis po przerwie → reload; szybka edycja podczas
opóźnionego żądania; pola wyboru/daty → aktualna historia i data zamknięcia;
komentarz bez automatycznej publikacji; załącznik → karta/pobranie/reload;
błędne pole/plik, błąd sieci, ponowienie, brak prawa edycji; powrót do listy
podczas oczekiwania → zapis → ponowne wejście przez częściową nawigację.
Sprawdź brak zapisu przy pierwszym renderowaniu, podwójnych listenerów,
pusty stan, referencyjną listę oraz desktop/tablet/telefon na osobnej bazie QA.

Weryfikacja 14.10.2026: przeszły 74 testy wymienionych modułów wraz z
`planner.test_task_calendar`. Kontrola Django, składnia Pythona/JS, lokalne
linki dokumentacji, aktualność indeksu i `git diff --check` przeszły.
Playwright/Chrome (plugin Browser niedostępny) na osobnej bazie PostgreSQL
i storage QA sprawdził szerokości 1440×1000, 1024×900 i 390×900: zapis
tytułu/opisu bez przeładowania, zmianę podczas opóźnionego żądania, pola/daty,
historię/zakończenie, pliki/pobranie, szkic komentarza, pusty czat i pozostałe
panele, niepoprawny tytuł/plik, błąd sieci/ponowienie i zdarzenie `online`.
Sprawdzono także listę referencyjną, powrót przed zapisem, ponowne wejście,
obserwatora, widoczność/tabelę członków, pięć zakładek, zwykły/scoped adres,
zatrzymanie wyjścia przy błędzie i ostatni cel przy kolejnych kliknięciach
podczas zapisu. Nie stwierdzono błędów wykonania JS ani przepełnienia strony.
Celowo przerwane żądania i odrzucony plik dawały oczekiwane błędy sieci/400.
Nie uruchamiano całego repozytorium; Safari i Firefox nie były sprawdzane.

Dodatkowa zmiana stylu statusu (14.10.2026): `work-task-save-status` używa
neutralnego tekstu bez tła i ramki. Playwright/Chrome na osobnej bazie QA
potwierdził wygląd stanów oczekiwania, zapisywania, powodzenia i błędu,
niezmienione etykiety, podkreślenie przy hover/fokusie klawiatury oraz
działające ponowienie zapisu. Sprawdzono 1440×1000 i 390×900, pusty czat,
listę referencyjną, ponowne wejście i reload, bez przepełnienia strony
ani nieoczekiwanych błędów konsoli/JS. Kontrola Django, indeksu i
`git diff --check` przeszła. Dla samej zmiany CSS/szablonu nie ponawiano
testów backendu ani nie dodawano nowych testów. Innych przeglądarek nie sprawdzano.

## Wygląd Aktywnego sprintu (13.10.2026)

Przeszło 61 istniejących testów `spaces.tests.SpaceTests`,
`spaces.test_backlog_drag` i `spaces.test_issue_types` na odrębnej bazie
PostgreSQL. Kontrola Django, składnia `tasks.js`, `git diff --check`
oraz sprawdzenie indeksu również przeszły.

Playwright/Chrome na osobnej bazie QA pod `127.0.0.1:8016` sprawdził szerokości
1920, 1024 i 390px. Wszystkie pięć nagłówków miało te same kolory, font,
wysokość i maski ikon co Lista zadań; zgodne były też etykiety i liczniki.
Sprawdzono zwijanie klawiaturą/nagłówkiem, rzeczywisty zapis statusu przez
przeciąganie i menu, liczniki po zapisie, reload, częściową nawigację,
ponowne wejście, zwykły/scoped URL, długi tytuł, zerową estymację,
brak sprintu i wyniki po filtrach oraz obserwatora bez edycji/przeciągania.
Celowo przerwane żądanie pokazało błąd i zachowało pierwotną kolumnę zadania.
Lista, Backlog i Kanban były ekranami referencyjnymi. Nie było przepełnienia
całej strony ani nieoczekiwanych błędów JS/konsoli w końcowym przebiegu.
Plugin Browser był niedostępny; użyto zwykłego Playwright z lokalnym Chrome.
Nie sprawdzano Safari/Firefox ani pełnego zestawu testów repozytorium.

Poprawka nakładania kart w długiej kolumnie: odtworzono problem z 14 zadaniami
w jednym statusie. Brak blokady `flex-shrink` zmniejszał karty poniżej wysokości
ich zawartości. Karty otrzymały `flex: 0 0 auto`, a wysokość tablicy została
ograniczona do dostępnej treści ponad paginacją. Po poprawce sprawdzono
w Chrome 1920×1000, 1024×844, 390×844 i 1920×600: metadane mieściły się w każdej
karcie, sąsiednie karty nie nachodziły na siebie, a cała ostatnia karta i jej
menu mieściły się w widocznej treści po przewinięciu. Ponownie sprawdzono zwijanie, przeciąganie
z zapisem statusu, reload, powrót z Listy zadań, Backlog, Kanban i pusty sprint.
Nie było błędów JS ani ostrzeżeń konsoli; sprawdzenie indeksu i diffu przeszło.
Przy tej poprawce samego CSS nie powtarzano testów backendu.

Osobne kafelki zadań: kolumna nie ma ciągłej ramki, nagłówek jest oddzielony,
a każda karta ma pełne obramowanie, zaokrąglenie i odstęp od sąsiedniej.
Chrome na tej samej izolowanej bazie QA potwierdził te cechy dla wszystkich
14 kart przy 1920×1000, 1024×844, 390×844 i 1920×600. Ponownie sprawdzono
metadane, przewijanie do całej ostatniej karty, jej menu, zwijanie,
przeciąganie z zapisem statusu, reload, powrót z Listy zadań oraz referencyjny
Backlog, Kanban i pusty sprint. Nie było błędów JS ani ostrzeżeń konsoli.
Sprawdzenie indeksu i diffu przeszło; testów backendu nie powtarzano.

Ujednolicenie punktów, wykonawcy i menu z backlogiem: przeszło 98 testów
`spaces.tests.SpaceTests`, `spaces.test_backlog_planning`,
`spaces.test_backlog_drag` i `dashboard.test_filters` na odrębnej bazie.
Kontrola Django, indeks oraz `git diff --check` przeszły. Chrome/Playwright
na izolowanym QA przy 1920×1000, 1024×844 i 390×844 porównał markup i końcowe
style punktów, awatarów oraz przycisku menu w backlogu, liście i sprincie.
Sprawdzono zero, brak estymacji, przypisaną/brakującą osobę, geometrię
metadanych, menu ostatniego kafelka, zapis statusu z listy z zachowaniem
filtra i częściowej nawigacji oraz reload. Edycja z listy przez rzeczywisty
custom select zapisała punkty i wykonawcę widoczne we wszystkich trzech
widokach. Sprawdzono również przeciąganie sprintu, ponowne wejście, puste
wyniki, obserwatora bez akcji, zwykły/scoped URL, Kanban i wyniki Filtrów.
Nie było błędów JS ani ostrzeżeń konsoli. Plugin Browser pozostawał
niedostępny; nie sprawdzano Safari/Firefox ani pełnego zestawu repozytorium.

Naprawa przeciągania kafelków sprintu: przed zmianą Chrome odtworzył gest
od tytułu jako przeciąganie URL bez zapisu statusu. Krótkie kolumny miały
również ograniczony do zawartości obszar upuszczania. Po poprawce linki
i obrazy w kartach nie uruchamiają osobnego drag, a kolumny sprintu i ich
listy wypełniają dostępną wysokość tablicy. Ponownie przeszło 98 testów
wymienionego wyżej zestawu, kontrola Django, składnia `spaces.js`, indeks
oraz diff. Native drag w Chrome na osobnym QA sprawdził tytuł, klucz,
awatar i tło, upuszczenie pod zawartością pustej/krótkiej kolumny,
jedno żądanie zapisu, brak URI w danych gestu, ten sam status bez zapisu,
Escape i czyszczenie podświetleń. Kliknięcie tytułu, menu, błąd zapisu,
ponowienie, reload, zwykły/scoped URL i częściowa nawigacja przeszły.
Sprawdzono też gest backlogu, tytuł karty Kanbana i brak drag obserwatora.
Geometria przy 1920×1000, 1024×844 i 390×844 potwierdziła pełną wysokość
celów i widoczność ostatniego kafelka; gesty wykonano myszą. Nie było
błędów JS/konsoli. Nie sprawdzano przeciągania dotykiem ani Safari/Firefox.

Efekty przeciągania: czytelny podgląd DOM zastępuje natywny półprzezroczysty
obraz; źródło oraz cel mają przerywane ramki, a potwierdzony zapis krótką
animację kafelka. Przeszło 98 testów tego samego zestawu oraz pełny przebieg
wcześniejszych prób gestu w Chrome. Osobny przebieg sprawdził cień, skalę,
przechylenie, współrzędne podglądu, `inert`, brak ID/form/aktywnych hooków
w kopii, pojedynczą widoczną ramkę celu nad kafelkami oraz czyszczenie
podglądu i obrazu gestu. Zapis uruchamiał animację, błąd pozostawiał zadanie
w źródle bez efektu sukcesu. Escape i ponowna inicjalizacja czyściły stan.
`prefers-reduced-motion` wyłączał ruch i zachowywał statyczne potwierdzenie.
Sprawdzono również 1024 i 390px; końcowe przebiegi nie miały błędów JS/konsoli.
Kontrola Django, składnia JS, indeks i diff przeszły. Nadal nie sprawdzano
gestów dotykiem ani Safari/Firefox; QA używało Playwright z lokalnym Chrome.

Kolejność kafelków na tablicy: przeszło 125 testów `spaces.tests.SpaceTests`,
`spaces.test_backlog_planning`, `spaces.test_backlog_drag`,
`spaces.test_board_order`, `spaces.test_issue_types` i `dashboard.test_filters`
na osobnej bazie PostgreSQL. Nowe 17 testów sprawdza przesunięcia w kolumnie
i między statusami, puste cele, kierunki z menu, zachowanie dat zakończenia,
historię autora, konflikty źródła/sąsiadów, atomowość, ACL, CSRF, filtry,
paginację, gęste/zdublowane numery, Kanban i zwykłe/scoped adresy z kluczem.
Chrome/Playwright na odrębnej bazie potwierdził rzeczywiste przeciąganie
tytułu w górę/w dół, wstawienie między sąsiadami innego statusu i trwałość
po reloadzie. Sprawdzono menu klawiaturą, filtry z zachowaniem pominiętego
numeru, faktyczny konflikt równoczesnego zapisu, pusty i zwinięty cel,
przerywaną linię wstawienia, przewijanie pionowe/poziome, Escape, powrót
z Listy zadań, ponowne wejście oraz 1920, 1024 i 390px bez przepełnienia.
Przy przewijaniu odtworzono utratę natywnego upuszczenia po zmianie kafelka
pod kursorem; obsługa `dragenter` naprawiła ten gest. Kontrola referencji
potwierdziła przeniesienie w backlogu do planowanego sprintu, tytuł karty
Kanbana i obserwatora bez drag. Pusty sprint oraz puste wyniki filtrów
zachowały swój stan. Sprawdzono również podgląd, potwierdzenie, błąd zapisu,
czyszczenie po podmianie treści i ograniczenie ruchu. Kontrola Django,
składnia JS/Python, indeks oraz diff przeszły. Nie ma nowych migracji ani
zależności; nie sprawdzano dotyku, Safari/Firefox ani całego repozytorium.

## Planowanie Backlogu (13.10.2026)

`spaces.test_backlog_planning` sprawdza zbiorcze przeniesienia, zachowanie
kolejności/statusów/zakończenia/autora, snapshot położenia, atomowy rollback,
zadania ukryte i tylko do odczytu, cofnięcie członkostwa, obcy sprint/Workspace,
bieżącą stronę, CSRF, Kanban, zwykłe/scoped adresy, pełne agregacje po filtrach,
zero i brak estymacji, tworzenie w sekcji, edycję i cykl sprintu oraz przydział
kolejności nowych zadań po planowaniu. Sprawdzaj razem z
`spaces.test_backlog_drag`, `spaces.test_backlog_ordering` i całym `spaces`.
Powiązane aktywne moduły: `dashboard.test_home`, `dashboard.test_for_you`
i `planner.test_task_calendar`. Nie ma nowych migracji ani zależności.

Weryfikacja: przeszło 196 testów Przestrzeni i 43 testy wskazanych aktywnych
modułów. Szersza próba wykazała 4 nieudane asercje `core.test_status_updates`
oraz 8 nieudanych asercji i 4 błędy `dashboard.test_search_regressions` dotyczące
historycznych Tasks. Te same błędy odtworzono w osobnej kopii niezmienionego
HEAD; nie przywracano wycofanych endpointów. Kontrole Django, składni JS,
stanu migracji, indeksu i `git diff --check` przeszły.

Playwright/Chrome (plugin Browser niedostępny) na osobnej bazie QA sprawdził
zaznaczanie sekcji/strony i stan częściowy, rzeczywisty dropdown, przeniesienie
zbiorcze i trwałość po reload, tworzenie zadania w sprincie z punktami, edycję
celu, zamknięcie z przeniesieniem do następnego sprintu, błąd dat i rozpoczęcie,
przeciąganie, listę referencyjną, częściową nawigację i ponowne wejście,
puste/odfiltrowane wyniki, przeniesienie na tablicę Kanbana oraz obserwatora.
Widoki sprawdzono przy 1440×1000, 1920×1000, 1024×1000 i świeżym wejściu
390×844, także modal/Escape i kompaktowy pasek operacji. Nie było błędów
aplikacji w konsoli; odpowiedź 400 przy błędnych datach była oczekiwana.
Nie uruchamiano całego repozytorium ani Safari/Firefox. Tymczasowe dane QA
nie należą do bazy użytkownika.

Po usunięciu checkboxów nagłówków sprintów i Backlogu sprawdzono w Chrome
1440×1000 i 390×844 brak tych kontrolek, zaznaczanie wierszy i całej strony,
stan częściowy, zwijanie, listę referencyjną, ponowne wejście, reload i pusty
backlog. Kontrole składni JS, Django, indeksu i `git diff --check` przeszły;
konsola i aplikacja nie zgłaszały błędów. Nie powtarzano testów backendu
dla tej korekty szablonów i obsługi zaznaczenia.

Po przeniesieniu „Utwórz sprint” do nagłówka Backlogu sprawdzono w Chrome
1440×1000 i 390×844 jego pojedyncze wystąpienie, położenie, zwiniętą sekcję,
otwarcie formularza, walidację wymaganej nazwy i rzeczywiste utworzenie sprintu.
Sprawdzono również pusty backlog, Escape, listę referencyjną, ponowne wejście,
reload i brak przycisku dla obserwatora oraz Kanbana. Nie było błędów konsoli
ani przepełnienia strony; Django, indeks i `git diff --check` przeszły.

Po usunięciu nagłówka „Planowanie sprintów” i stałego paska wyboru sprawdzono
w Chrome 1440×1000 i 390×844 brak nagłówka/górnego checkboxu oraz pustego
odstępu. Pasek pojawia się po zaznaczeniu wiersza, aktualizuje licznik, znika
po odznaczeniu, a „Odznacz” przywraca fokus do wiersza. Rzeczywiste przeniesienie
zbiorcze, modal sprintu, lista referencyjna, ponowne wejście, reload, pusty wynik,
Kanban i obserwator przeszły bez błędów konsoli. Kontrole Django, JS, indeksu
i `git diff --check` przeszły; nie powtarzano pełnego zestawu backendu.

## Zarządzanie w Ustawieniach (13.10.2026)

Zarządzanie Przestrzeniami, Pulpitami i Filtrami ma trzy osobne strony
z własnymi minimalnymi paskami bocznymi, według wzorca katalogu Workspace.
Filtry mają osobny katalog `/filters/manage/` oraz scoped
odpowiednik, ograniczony do własnych definicji. Formularze i akcje zachowują
kryteria listy; zmiana nie wymaga migracji.

Boczne menu Ustawień zawiera tylko Ogólne, Konto i dostęp i Workspace.
Trzy linki zarządzania pozostają w treści sekcji Workspace. Strony zarządzania
pokazują tylko powrót do Ustawień oraz jedną aktywną pozycję własnego modułu.
Po usunięciu duplikatów przeszły cztery istniejące testy
Ustawień i katalogów zarządzania. Chrome przy 1440×1000 i 390×844 potwierdził
brak tych pozycji w menu, działanie linków w treści, powroty, częściową nawigację,
Wstecz/Dalej, reload i ekran referencyjny Przestrzeni, bez błędów konsoli.

Końcowy zestaw 84 testów Filtrów, zarządzania Przestrzeniami/Pulpitami/Workspace,
edytora Pulpitów, Ustawień i aktywności menu przeszedł. Po ostatniej poprawce
powrotu z bezpośredniego modalu ponownie przeszły trzy testy nowego zarządzania
Filtrami. Szerszy przebieg 87 testów
miał 85 sukcesów i dwa wcześniejsze problemy powiadomień w `DashboardViewTests`.
Oba odtworzono z identycznymi komunikatami na niezmienionym HEAD w osobnej
bazie. Nie sprawdzano całego repozytorium.

Playwright z Chrome na osobnej bazie QA pod `127.0.0.1:8015`, przy 1440×1000,
1024×844 i 390×844, sprawdził Ustawienia → zarządzanie Filtrami → Przestrzenie
→ Pulpity → powrót, aktywne menu, skrót pod trzema kropkami, nawigację częściową,
Wstecz/Dalej, reload, paginację, zaznaczenie wszystkich/części wierszy,
wyszukiwanie, filtr widoczności, gwiazdkę, pusty wynik/czyszczenie,
modal tworzenia/edycji, także bezpośredni adres formularza, walidację HTTP 400,
zapis z zachowaniem kryteriów,
usuwanie, Escape/fokus oraz zwykłe/scoped adresy. Strona nie przepełniała się
poziomo, a konsola nie zgłosiła nieoczekiwanych błędów ani ostrzeżeń.
Tabela zarządzania Przestrzeniami była referencją powłoki, toolbaru i ikon.
Plugin Browser był niedostępny. Nie sprawdzano Safari/Firefox.

Wariant osobnych minimalnych menu: przeszło 81 testów Przestrzeni, Filtrów,
zarządzania Pulpitami i ich edytora, zarządzania Workspace, Ustawień oraz menu.
Chrome z Playwright na odrębnej bazie QA przy 1440×1000, 1024×844 i 390×844
potwierdził dokładnie dwa linki każdego menu, brak kategorii Ustawień,
identyczne wysokości/fonty jak w katalogu Workspace, modale/Escape, wejście
z centrum Ustawień, powroty, częściową nawigację, Wstecz/Dalej, reload,
zwykłe/scoped URL, pusty wynik, zwinięte menu oraz mobilne otwieranie/zamykanie.
Konsola bez błędów i ostrzeżeń. Zmiana nie wymaga migracji. Nie ponawiano
całego repozytorium ani sprawdzeń Safari/Firefox.

## Dolny pasek stron Przestrzeni (13.10.2026)

Przeszło 80 testów `spaces.tests.SpaceTests`, `spaces.test_backlog_ordering`,
`spaces.test_backlog_drag` i `dashboard.test_filters`. Playwright/Chrome na
oddzielnej bazie QA pod `127.0.0.1:8014` sprawdził backlog i referencyjną listę
zadań, tablicę, oś czasu, katalog/zarządzanie Przestrzeniami, Zespoły oraz Filtry.
Potwierdzono numery i strzałki na pierwszej, środkowej i ostatniej stronie,
zakres wyników, zachowanie filtrów, zwykłe/scoped linki, częściową nawigację,
Wstecz/Dalej, reload, ponowne wejście, klawiaturę i działanie bez JavaScriptu.
Pusty backlog i brak wyników pokazują wyłączone strzałki; podsumowanie,
raporty i ustawienia nie pokazują paginacji.

Przy 1920×1000, 1440×1000, 1024×1000 i 390×844 pasek mieści się pod
przewijaną treścią i pozostaje widoczny przy dolnej krawędzi panelu.
Osobne renderowanie zakresów 7 i 40 stron potwierdziło zawijanie bez
przepełnienia przy 390px i 320px oraz skracanie zakresu wielokropkiem.
Konsola nie zgłosiła błędów ani ostrzeżeń. Plugin Browser był niedostępny,
dlatego użyto zwykłego Playwright. Nie sprawdzano Safari/Firefox ani całego
zestawu repozytorium. Zmiana nie wymaga migracji.

## Wspólne dropdowny (13.10.2026)

Przeszło 112 testów `dashboard.test_filters`, `spaces.test_issue_types`,
`spaces.test_task_detail_parity`, `spaces.tests.SpaceTests` i `dashboard.test_pulpits`.
Zestaw 65 testów Zasobów, powiadomień, Kalendarza i awatarów kont/Workspace
miał 47 sukcesów oraz 17 niepowodzeń i jeden błąd w historycznych testach
powiadomień. Osobny przebieg `dashboard.test_notifications` na niezmienionym
HEAD `2bb0b0b` potwierdził identyczną listę 18 błędów; pozostałe 39 testów
powiązanych modułów przeszło. Nowa regresja sprawdza wartości wielokrotnego
wyboru, zdjęcia i kontrolowane adresy podglądów, prywatne przestrzenie,
obcy Workspace oraz escapowanie własnego typu zgłoszenia.

Playwright z lokalnym Chrome na osobnej bazie QA, przy 1440×1000,
1024×844 i 390×844, potwierdził szerokość/pozycję menu, ikony i zdjęcia,
wybór wielokrotny, wyszukiwanie polskich znaków, brak wyników, długie nazwy,
klawiaturę/Escape/fokus, modal, referencyjną listę Przestrzeni, menu działań,
filtry/formularz Zasobów, Profil, Kalendarz, listy warunków Dysku/Dokumentów,
przełącznik Workspace i awatary w powiadomieniach, zwykłe/scoped adresy,
częściową nawigację i ponowne wejście/reload. Strona nie przepełniała się
poziomo; konsola nie zgłosiła błędów ani ostrzeżeń. Plugin Browser nie był
dostępny, dlatego użyto zwykłego Playwright. Kontrola Django, składnia JS,
indeks kodu i `git diff --check` przeszły. Zmiana nie wymaga migracji;
nie sprawdzano całego repozytorium ani innych silników przeglądarek.

## Weryfikacja Filtrów

Moduł wymaga migracji dashboard.0014_savedtaskfilter. Testy
dashboard.test_filters obejmują parser, sortowanie, aktualne ACL zadań
i rodziców, Workspace, udostępnianie, cofnięcie dostępu, autorstwo,
rewizje, formularze, CSRF, zwykłe/scoped URL i paginację.
Powiązane zestawy to spaces.tests.SpaceTests, spaces.test_tags
oraz dashboard.test_pulpits.

UI należy sprawdzać na osobnej bazie QA: podstawowe/zaawansowane
wyszukiwanie, zapis i edycja, widoczność, gwiazdki, menu, zamykanie
dialogu, błędy i pusty wynik, ponowne wejście przez częściową nawigację,
desktop i telefon oraz referencyjną listę zadań Przestrzeni.

Wycofanie osobnego ekranu „Wszystkie zadania” (11.10.2026): przeszło
86 testów dashboard.test_filters, spaces.tests.SpaceTests,
spaces.test_issue_types, tasks.test_retirement, core.tests.SidebarActiveStateTests
oraz trzech testów kolejności Favorites w workplaces.tests. Sprawdzono
przekierowania zwykłych/scoped adresów, zachowanie kryteriów, ACL,
ukrycie starego skrótu i wyszukiwanie globalne. Chrome z Playwright
na osobnej bazie QA przy 1280×720 i 390×844 potwierdził menu,
zwinięty sidebar, listę referencyjną Przestrzeni, zapisany filtr,
stany puste/błędy, ponowne wejście przez częściową nawigację i reload.
Strona nie przepełniała się poziomo; konsola nie zgłosiła błędów ani ostrzeżeń.
Plugin Browser był niedostępny. Nie sprawdzano całego repozytorium
ani innych przeglądarek; zmiana nie wymaga migracji.

Grupowana lista wyników (11.10.2026): przeszło 109 testów
dashboard.test_filters, spaces.tests.SpaceTests, spaces.test_tags,
dashboard.test_pulpits i core.tests.SidebarActiveStateTests. Playwright
z Chrome na osobnej bazie QA przy 1920×1080, 1024×900 i 390×844 potwierdził
grupy statusów i liczniki, zwijanie klawiaturą i nagłówkiem, zaznaczenie,
przejście do zadania/powrót, sortowanie, paginację, błędy i puste wyniki,
zapisany filtr oraz statusy z różnych słowników. Geometria, fonty i kolory
wiersza/nagłówka zgadzają się z listą Przestrzeni. Sprawdzono zwykły/scoped
adres, częściową nawigację, reload, katalog filtrów i przewijanie listy
na telefonie bez przepełnienia strony. Konsola nie zgłosiła błędów.
Plugin Browser był niedostępny. Nie sprawdzano całego repozytorium
ani innych przeglądarek; zmiana nie wymaga migracji.

Weryfikacja (10.10.2026): przeszło 96 testów wymienionych wyżej zestawów,
kontrola Django, zgodność migracji, składnia zmienionego JS, lokalne linki,
indeks kodu i git diff --check. Przeglądarka Codex na oddzielnej bazie QA
potwierdziła wybór wielu kryteriów, zapis, zmianę warunków i widoczności,
gwiazdki i aktualizację menu, błędne zapytanie, pusty wynik, czyszczenie,
błąd zapisu w modalu, Escape/odrzucenie szkicu, potwierdzenie usuwania
oraz ponowne wejście z Wszystkich zadań. Sprawdzono szerokości 1280,
1024 i 390 px, modal na telefonie i brak przepełnienia strony.
Konsola nie zgłosiła błędów ani ostrzeżeń.

Szersze starsze zestawy dashboard.test_search_regressions i workplaces.tests
mają wcześniejsze rozbieżności z wycofanymi Tasks oraz nawigacją.
Powtórzenie ich na niezmienionym HEAD fed9ebd, w odrębnej bazie testowej,
potwierdziło 23 niepowodzenia i 5 błędów w 56 testach.
Nie sprawdzono całego repozytorium ani innych silników przeglądarek.

Ujednolicenie menu Filtrów z Przestrzeniami (10.10.2026): przeszły 123 testy
dashboard.test_filters, spaces.tests.SpaceTests, dashboard.test_pulpits,
dashboard.test_for_you oraz core.tests.SidebarActiveStateTests.
Przeglądarka na osobnej bazie QA przy 1280×720 i 390×844 potwierdziła
wspólne nagłówki, zarządzanie pod trzema kropkami, panel „Więcej filtrów”,
wyszukiwanie i pusty wynik, Escape, zmianę gwiazdki z Wszystkich zadań,
podział ulubione/ostatnie, ponowne wejście przez częściową nawigację,
zwijanie sekcji oraz całego paska i zamknięcie menu telefonu po nawigacji.
Strona nie przepełniała się poziomo, konsola nie miała błędów ani ostrzeżeń.
Nie zmieniono modeli ani migracji. Nie sprawdzano innych przeglądarek.

Oddzielny system Zadań przestrzeni (10.10.2026) wymaga migracji
`spaces.0006_independent_space_tasks`, `tasks.0066_task_space_archived_taskproject_space_archived`
i `spaces.0007_archive_import_sources`, po backupie bazy i storage.
Przestrzenie tworzą `SpaceTask` bez projektów/grup Tasks. Testy przestrzeni
używają jawnych własnych fixture'ów; historyczne testy migracji korzystają
ze stanu właściwego dla ich schematu, z cofnięciem zależnych migracji.
Uruchamiaj `manage.py test spaces core.test_status_updates core.test_file_lifecycle`.
`spaces.test_independent_tasks` obejmuje niezależność modeli, scoped/zwykłe
adresy, powrót do widoku, prywatnych rodziców, obserwatorów, cofnięcie dostępu,
obce relacje, statusy, pliki, komentarze, podzadania, czas i migrację.
Browser QA: lista → zadanie → zapis/komentarz → powrót i ponowne wejście;
sprawdź też stary link, pustą listę, walidację, obserwatora, Dashboard oraz
szerokości desktop/tablet/telefon. Dane do zapisów przygotuj w odrębnej bazie QA.


## Wycofanie starszych systemów pracy (10.10.2026)

Starsze systemy **Projekty, Grupy, Zadania, Ulubione projekty i Szablony
projektów** są wycofane. Nie mają ekranów, operacji zapisu ani rejestracji
w Django admin. Sekcja „Starsze widoki” jest usunięta z menu. Historyczne dane,
pliki i szablony pozostają w bazie; nie jest wymagana nowa migracja.

`backend/tasks/urls.py` zachowuje tylko adresy zgodności. GET/HEAD `/tasks/` oraz scoped
odpowiednik przekierowuje do Przestrzeni. Link projektu lub grupy działa
wyłącznie po mapowaniu `Space.project`; szczegóły zadań przez `WorkItem.legacy_task`,
a pliki przez `SpaceTaskFile`. Wszystkie przekierowania sprawdzają aktywny
Workspace i bieżący dostęp Przestrzeni. Obiekt bez mapowania, usunięty albo
niedostępny zwraca 404. POST pod zachowany adres zwraca 409; usunięte endpointy
szablonów, statusów, usuwania, zespołów, ulubionych i obserwowania zwracają 404.

`tasks.access` zwraca pusty wynik dla historycznych modeli pracy. Menedżery
modeli nadal widzą zapisane dane dla migracji i utrzymania. `TaskTag` i
`TaskTagNote`, wspólne szablony oraz `static/js/tasks.js` pozostają używane
przez aktywne moduły. Tagi sprawdzają dostęp przez Przestrzeń.
Wyszukiwarka, ostatnio oglądane, kalendarz i powiadomienia nie pokazują
historycznych projektów, grup ani zadań. Stare przypomnienia i subskrypcje nie
powodują nowych dostarczeń; zapisane stany pozostają zachowane. Osobiste skróty
`tasks-projects` prowadzi do Przestrzeni; skróty `tasks-all`, grup i „moich
zadań” pozostają ukryte. Samodzielny ekran „Wszystkie zadania” jest wycofany;
lista zadań jest dostępna przez „Filtry → Wyszukaj zadania”.

Testy `tasks.test_retirement` sprawdzają menu, zwykłe/scoped linki, brak operacji
i ekranów admin, zachowanie danych/szablonów/plików, mapowania importu, cofnięcie
dostępu, nieprawidłowe identyfikatory, wyszukiwanie, historię sesji, ulubione,
kalendarz i brak dostarczania historycznych powiadomień/przypomnień.
Uruchamiaj też `spaces`, `planner`, `core.tests.SidebarActiveStateTests`,
`dashboard.test_for_you`, `dashboard.test_pulpits`, `core.test_file_lifecycle`
i `kanban.test_retirement`. Historyczne testy ekranów Tasks nie opisują już
kontraktu bieżącej aplikacji; ich oczekiwania aktywnych URL są nieaktualne.
Browser QA: Przestrzenie → Wszystkie zadania → zadanie → powrót, stary katalog
i importowane szczegóły, brak starych pozycji, pusty Workspace i wynik szukania,
błąd sieci, referencyjny pulpit, częściowa nawigacja i ponowne wejście,
zwinięty sidebar oraz desktop/tablet/telefon.

Weryfikacja (10.10.2026): wszystkie **273 testy** powyższego zestawu przeszły
na osobnej bazie PostgreSQL. Playwright/Chrome (plugin Browser niedostępny)
na izolowanej bazie QA przy 1440×1000, 1920×1000, 1024×1000 i 390×844
potwierdził menu bez starszych systemów, Wszystkie zadania → szczegóły →
Wstecz/Dalej/reload, zachowanie dokumentu przy częściowej nawigacji,
przekierowania katalogu i importowanych szczegółów, zwinięty sidebar/Escape,
menu telefonu, referencyjny pulpit, pusty Workspace, pusty wynik katalogu
oraz pusty wynik i błąd sieci globalnego wyszukiwania. Zrzuty desktop/telefon
potwierdziły dotychczasowy wygląd bez starej sekcji. Nie było nieoczekiwanych
błędów konsoli, pustych ekranów, nakładek błędów ani przepełnienia strony;
symulowana awaria wyszukiwania wywołała oczekiwany `ERR_FAILED`.
Kontrole Django, braku zmian modeli/migracji, linków i kotwic dokumentacji,
indeksu oraz `git diff --check` przeszły. Serwer i baza QA zostały usunięte.
Nie uruchamiano całego repozytorium, historycznych testów ekranów Tasks,
Safari ani Firefox. Kod nie wymaga migracji i nie kasuje danych użytkowników.

## Regresje zapisu i numeracji

`tasks.test_task_moves` zachowuje kontrolę blokady zmiany historycznej
lokalizacji i edycję aktualnego zadania bez pól dawnego projektu/grupy.
Bieżące operacje sprawdzają `spaces.test_independent_tasks`,
`spaces.test_issue_types`, `spaces.test_tags` i `core.test_task_integrity`.
`core.test_status_updates` sprawdza współbieżną zmianę statusu, trwałość daty
zakończenia i rollback razem z historią. `spaces.test_write_access` zmienia
rolę/członkostwo z drugiego połączenia przed uzyskaniem blokady; zapis musi
zostać odrzucony. `spaces.test_backlog_ordering` obejmuje kolejność, filtry,
zadania na tablicy/zamknięte oraz menu członka i obserwatora.

Weryfikacja wyglądu backlogu (9.10.2026): 44 testy `spaces.tests.SpaceTests`,
`spaces.test_backlog_ordering` i `spaces.test_write_access` przeszły.
Playwright/Chrome na oddzielnej bazie QA (plugin Browser niedostępny) sprawdził
Scrum i Kanban przy 1440×1000, 1920×1000, 1024×1000 i 390×844.
Geometria sekcji i wierszy odpowiada Liście zadań. Potwierdzono zwijanie myszą
i klawiaturą, checkboxy, menu/Escape/fokus, zmianę kolejności z reload,
przeniesienie na tablicę, daty i cel sprintu, pusty wynik i pusty backlog,
zwykłe/scoped adresy, częściową nawigację i ponowne wejście oraz brak akcji
zapisu obserwatora. Formularz sprintu zachowuje błędy i zamykanie; celowo
niepoprawny POST zwrócił oczekiwany HTTP 400. Nie było nieoczekiwanych błędów
konsoli. Kontrole Django, szablonów, linków dokumentacji, indeksu i
`git diff --check` przeszły. Nie uruchamiano całego zestawu repozytorium.

Przeciąganie backlogu: `spaces.test_backlog_drag` sprawdza kolejność w sekcji,
przeniesienia do/z pustych planowanych i aktywnych sprintów, rzeczywistego autora
historii, zachowanie statusu, filtry i zwykłe/scoped URL. Obejmuje gęste/powtarzające
się numery kolejności, ukrytych i obserwowanych sąsiadów, stronę 100 wyników,
nieaktualne dane, obce przestrzenie/Workspace, zakończone sprinty/zadania,
CSRF i Kanban. `spaces.test_write_access` sprawdza cofnięcie roli przed blokadą.
Weryfikacja (9.10.2026): 127 testów `spaces core.test_status_updates` przeszło;
po dodaniu dwóch przypadków sąsiadów ponownie przeszło 18 testów
`spaces.test_backlog_drag`. Playwright/Chrome na oddzielnej bazie QA przy
1440×1000 i 390×844 potwierdził przeciąganie myszą oraz rzeczywistymi zdarzeniami
dotyku, wstawienie przed pierwszym zadaniem i na zwinięty nagłówek, trwałość po
reload, liczniki, zachowanie statusu, menu klawiaturą, Escape, błąd sieci bez
pozornej zmiany, powrót przez częściową nawigację bez podwójnego zapisu,
filtry/URL i brak kontrolek obserwatora. Lista zadań oraz przeciąganie statusu
na tablicy zachowują działanie; telefon nie ma poziomego przepełnienia strony.
Końcowe przejście przy 1920×1000 i 1024×1000 potwierdziło geometrię wiersza
40px, brak przepełnienia strony, pusty backlog i wynik filtrów oraz obsługę
przeciągania pojedynczego zadania Kanbana (bez zmiany kolejności).
Nie było nieoczekiwanych błędów konsoli; symulowany błąd sieci jest oczekiwany.
Plugin Browser był niedostępny. Nie sprawdzano Safari/Firefox ani całego
zestawu testów repozytorium.

Usunięcie ikon uchwytu backlogu (10.10.2026): nie ma osobnego elementu ani
kolumny z kropkami, a checkbox pozostaje pierwszym elementem wiersza.
Playwright/Chrome na osobnej bazie QA przy 1440×1000 i 390×844 potwierdził
przeciąganie myszą oraz dotykiem od istniejącej ikony priorytetu, zapis po
przeładowaniu, przeniesienia między sprintami/backlogiem, menu klawiaturą,
Escape, błąd sieci, filtry i zwykłe/scoped URL, ponowne wejście przez częściową
nawigację oraz brak przeciągania u obserwatora. Lista zadań i tablica zachowują
dotychczasowe działanie; nie było nieoczekiwanych błędów konsoli ani
przepełnienia strony na telefonie. Kontrola Django, składni JS, indeksu i
`git diff --check` przeszła. Nie ponawiano testów backendu ani innych przeglądarek.

## Uruchomienie przestrzeni i zespołów

Adresy Przestrzeni sprawdza `spaces.test_urls`: nazwa i polskie znaki w URL,
duplikaty w jednym/dwóch Workspace, nazwy numeryczne i bez liter, długa nazwa,
niezmienny adres po edycji, zwykłe/scoped trasy, stare GET/HEAD/POST,
parametry zapytania, menu/katalog/szukaj/zespoły/Dla ciebie, zakładki,
konfiguracja, formularze i powroty, prywatność, role, cofnięcie dostępu,
unikalność w bazie, równoczesny przydział oraz migracja zachowująca dane.
Migracja `spaces.0005_space_slugs` wymaga backupu i `manage.py migrate`.

Weryfikacja adresów Przestrzeni (10.10.2026): 194 testy `spaces`,
`dashboard.tests.DashboardViewTests`, `dashboard.test_for_you`,
`dashboard.test_home` i `dashboard.test_search_regressions` przeszły.
W dodatkowym zestawie `kanban.test_retirement` przeszło 5 z 6 testów;
błąd `dashboard_totals` w historycznym teście odtworzono na niezmienionym HEAD.
Playwright/Chrome (plugin Browser niedostępny) na izolowanej bazie QA przy
1440×1000, 1920×1000, 1024×1000 i 390×844 potwierdził przekierowanie i filtry,
katalog/menu → podsumowanie → zakładki → edycja/zapis → powrót, walidację
pustej nazwy, zachowanie URL po zmianie nazwy i reload, utworzenie rzeczywistego
zadania i powrót do listy, duplikat, Wstecz/Dalej i częściową nawigację bez
przeładowania dokumentu. Sprawdzono pusty wynik katalogu i referencyjny pulpit
domyślny; zrzuty desktop/telefon potwierdziły dotychczasowy wygląd. Nie było
błędów/warningów konsoli, pustego ekranu, nakładek błędów ani przepełnienia strony.
Sprawdzono też podany adres na działającym `127.0.0.1:8000`: liczbowy adres
przekierowuje do nazwy, a lista i podsumowanie działają.
Kontrole Django, migracji, składni JS, linków dokumentacji, indeksu oraz
`git diff --check` przeszły. Migrację zastosowano lokalnie po pełnym backupie;
porównanie przestrzeni, projektów, planowania, gwiazdek i dostępów potwierdziło
zachowanie dotychczasowych danych. Nie uruchamiano całego repozytorium ani
Safari/Firefox.

Przed nowym kodem wykonaj backup i `manage.py migrate`. Migracje `spaces/0001`
i `spaces/0002` dodają model przestrzeni i importują Kanban; oryginały oraz
pliki zostają zachowane. Cofnięcie wdrożenia wymaga backupu, nie tylko migracji
odwrotnej. [Procedura i ograniczenia](SPACES.md).

Testy: `manage.py test spaces`, regresje statusów i plików w Core, prywatności
i ról w Tasks, zespołu Workspace oraz Dashboard/Planner. Testy historycznych
migracji muszą wycofać zależny moduł `spaces` i odczytać stan faktycznie
zastosowanych migracji. Browser QA obejmuje katalog pusty i z danymi,
kreator/szablony, błędy formularzy, zadanie na liście i tablicy, sprint,
zespół i powiązania, szeroki/wąski ekran, Escape/fokus i częściową nawigację.

Podsumowanie przestrzeni obejmuje `spaces.test_summary`: przedziały 7/14 dni,
ponownie otwarte zadania, wiele aktualizacji jednego zadania, własne statusy,
pełne agregacje ponad pierwszą stronę i podzadania, priorytety, typy,
skalę wykresu priorytetów od zera oraz proporcje słupków i puste wartości,
nieprzypisani wykonawcy, postęp epików, historia i stabilne odnośniki,
granice Workspace oraz prywatność projektu/grupy/zadania/rodzica i cofnięcie
dostępu. Sprawdzaj także `spaces`, `tasks.test_task_sharing`,
`tasks.test_section_sharing`, `core.test_status_updates` i Dashboard.
Browser QA obejmuje porównanie z Dashboardem, puste podsumowanie i puste
wyniki filtrów, kliknięcie liczników i wykresów, usunięcie zakresu bez utraty
innych filtrów, desktop/tablet/telefon, przewijanie oraz częściową nawigację,
powrót i przeładowanie. Nie potrzeba nowej migracji ani bibliotek wykresów.

Wyszukiwanie z panelu „Więcej przestrzeni” obejmują testy `SpaceTests.test_space_search_*`:
zwykłe/scoped adresy, członek/obserwator, cofnięcie dostępu, obcy Workspace,
nazwa/klucz, limit wyników, escapowanie tekstu i wymóg logowania/GET.
W przeglądarce sprawdź otwarcie, wpisanie frazy spoza skrótów menu, wybór wyniku,
link do katalogu, Escape/fokus, kliknięcie poza panelem, brak wyników/błąd,
ponowne wyszukiwanie po zmianie zapytania, kwadratowe awatary,
zwinięty sidebar, telefon i ponowne wejście po częściowej nawigacji.


Rozdzielenie katalogu i zarządzania przestrzeniami sprawdza
`spaces.test_management`: zwykłe/scoped adresy, właściciel i administrator
Workspace, role projektu, osoba odpowiedzialna, cofnięcie dostępu, obcy
Workspace, ukryte zadania w licznikach, filtry/paginacja, tworzenie i edycja
nad katalogiem oraz powrót po zapisie. Uruchamiaj także `spaces`,
`dashboard.tests.DashboardViewTests` i `kanban.test_retirement`.
Browser QA obejmuje przejście Katalog → menu „…” → Zarządzaj przestrzeniami,
zastąpienie głównego menu Workspace menu administracyjnym i jego przywrócenie
po powrocie, historię Wstecz/Dalej, zwinięty pasek oraz menu na telefonie,
Ustawienia jako ekran referencyjny, edycję/zapis, błędy kreatora, anulowanie,
wyszukiwanie/pusty wynik, pusty Workspace, ponowne wejście i desktop/telefon.
Porównaj listę z katalogiem „Przestrzenie”: kolejność i szerokości kolumn,
checkboxy, menu trzech pasków, awatary, szablon, opis i liczbę widocznych zadań.
Sprawdź zaznaczenie wszystkich/części wierszy, gwiazdkę i edycję z menu,
przejście z nazwy do ustawień oraz niezależne preferencje kolumn zarządzania
między zwykłym i scoped URL. Wyszukiwarka i paginacja są po prawej.

Dwukrokowy kreator sprawdzają także testy `SpaceTests.test_template_picker_is_only_used_when_creating_spaces`,
`test_each_template_creates_its_matching_configuration` i
`test_template_error_keeps_selection_and_space_details` (tworzenie i edycja,
sześć konfiguracji, zachowanie szkicu i nieznany szablon). Browser QA:
brak dostępnych pól/zapisu przed wyborem, każdy kafelek, Enter/Spacja,
automatyczny rodzaj, cofnięcie i zmiana szablonu bez utraty danych,
błąd walidacji/sieci i ponowienie, zapis, Escape/powrót fokusu,
zwykłe/scoped adresy, tworzenie z zarządzania i plusa w menu,
pusty katalog, częściowa nawigacja oraz desktop/tablet/telefon.
Po zapisie sprawdź także natychmiastowe pojawienie się nowego linku w menu
bocznym bez przeładowania dokumentu, jego nazwę/awatar i aktywność. Przy więcej
niż sześciu przestrzeniach sprawdź limit oraz kolejność gwiazdek/odwiedzin/najnowszych,
usunięcie nieobecnych linków po aktualizacji danych, zachowanie zwinięcia,
panel skrótów i „Więcej przestrzeni” oraz zamknięcie menu na telefonie po
wybraniu nowej pozycji.

Checkboxy i menu katalogu Przestrzeni: browser QA obejmuje zaznaczenie
jednego/wszystkich wierszy bieżącej strony, stan częściowego wyboru,
podświetlenie jak w Projektach, menu bez zmiany zaznaczenia, Escape/fokus,
ulubione z zachowaniem filtrów, edycję/dodanie osób według ról, pusty wynik,
zmianę szerokości kolumn, telefon i ponowne wejście po częściowej nawigacji.
Katalog i zarządzanie Przestrzeniami sprawdzaj także pod kątem braku bocznych
odstępów tabeli, porównując je z Workspace i Projektami na desktopie, tablecie
i telefonie, również po paginacji i przeładowaniu.
Uruchamiaj `spaces.tests.SpaceTests`, `spaces.test_navigation`,
`spaces.test_management`, `core.test_navigation_frontend` i `core.test_workspace_frontend`.

`spaces.test_navigation` sprawdza osobiste gwiazdki, kolejność odwiedzin,
limit i brak duplikatów, zwykłe/scoped adresy, cofnięcie dostępu, granice
Workspace, role menu oraz CSRF i bezpieczny powrót formularza. W przeglądarce:
menu wiersza → dodanie/usunięcie gwiazdki → przeniesienie między podpisanymi
blokami bez opuszczania ekranu, Enter/strzałki/Escape i fokus, błąd/ponowienie,
ustawienia i formularz osób, długie nazwy, puste bloki, częściowa nawigacja,
historia, przeładowanie, panel zwiniętego sidebaru, wyszukiwarka oraz telefon.

Centrum `/settings/` sprawdzaj razem z `dashboard.tests.DashboardViewTests`.
Browser QA: wejście z codziennego katalogu i zarządzania przestrzeniami,
zastąpienie głównego paska kategoriami ustawień, wybór każdej kategorii,
bezpośredni fragment URL i historia Wstecz/Dalej, powrót do Workspace,
ponowne wejście, zwijanie menu z przycisku wspólnej powłoki i menu na telefonie.
Sekcja Preferencje wraz z opcjami jest usunięta; stare fragmenty tej sekcji
otwierają Ogólne. Sprawdź brak odsyłaczy do usuniętych opcji w profilu,
dzwonek w górnym pasku oraz widoczność administracyjnych linków według roli.

## Usunięcie systemu Wartości pól projektu

`tasks/0063_remove_project_field_settings` usuwa tabele słowników i reguł
terminów oraz `TaskProject.use_custom_deadline_rules`; zapisane pola projektu
pozostają bez zmian. Przed zastosowaniem migracji wykonaj backup bazy.
Testy `tasks.test_project_field_retirement` sprawdzają brak endpointu GET/POST,
stałe opcje, edycję i filtrowanie historycznych wartości, granice Workspace
oraz migrację zachowującą projekty. Uruchamiaj również `tasks`, `spaces`,
`dashboard.tests.DashboardViewTests` i formularze Dokumentów.
Browser QA: ustawienia bez pozycji, katalog projektów i edycja/utworzenie
projektu, źródło i daty, stare adresy, ponowne wejście, desktop/telefon.
Kontrolka koloru Dysku ma własną klasę `documents-color-input` i style
w `documents.css`, niezależne od usuniętego systemu.

## Wycofanie Tablic Kanban

`kanban.test_retirement` sprawdza przekierowania zwykłe/scoped, brak dawnych
operacji, brak wyników w integracjach, zachowanie danych oraz kontrolę dostępu
do zaimportowanych szczegółów i plików. Regresje modelu i historycznej migracji
pozostają w `kanban.tests` i `kanban.test_sharing`; testy dawnych ekranów zastąpiły
testy wycofania. Sprawdzaj też `spaces`, Dashboard, Planner i wspólne mechanizmy
Zadań. Wycofanie nie wymaga nowej migracji ani usuwania danych.

## Typy zgłoszeń

Przed zastosowaniem `spaces.0004_issue_types` wykonaj backup danych.
Migracja dopisuje brakujące standardowe typy do konfiguracji bez zmiany zadań
i schematu tabel; cofnięcie zachowuje dopisane opcje. Nowe przestrzenie
otrzymują typy z aktualnego `template_settings`.
`spaces.test_issue_types` sprawdza tworzenie/edycję w Marketingu, oba warianty
adresów, szczegóły zadania, autora i rollback historii, zachowanie typu przy
innych edycjach, nieznane/niedostępne typy, role, obcy Workspace, relacje epików,
filtry z wyszukiwaniem i prywatnością oraz idempotencję migracji.
Uruchamiaj też `spaces`, testy udostępniania/nieprzydzielonych zadań i szablonów
projektów oraz `core.test_status_updates`. Browser QA obejmuje wybór i zapis
typu, ikonę/nazwę na liście i tablicy, filtr/pusty wynik, szczegóły i historię,
walidację, Escape/fokus, ponowne wejście oraz desktop i telefon.

## 1. Wymagania i wersje

Tagi przestrzeni wymagają migracji Tasks `0064_space_tags` i `0065_space_tag_data`.
Wykonaj backup bazy przed migracją danych. `spaces.test_tags` sprawdza zwykłe/scoped
adresy, izolację dwóch przestrzeni i Workspace, wycofany katalog, obserwatora,
autora notatek, formularze, usuwanie zbiorcze, CSRF, wyszukiwanie, przenoszenie
zadań oraz kopiowanie/cofanie danych migracji. Sprawdzaj również `spaces`,
uprawnienia Tasks, `tasks.test_tag_retirement`, wyszukiwanie Dashboardu,
wycofanie Kanbana oraz brak tagów w Dokumentach. Browser QA: zakładka i ekran
referencyjny, dodanie/edycja/usunięcie, notatka, błąd nazwy, filtry, pusty stan,
Escape, powrót po częściowej nawigacji oraz desktop i 390px.

Źródła: [requirements.txt](../requirements.txt), [settings.py](../backend/ancore/settings.py).

- Python **3.15.0**, opisany w [requirements.txt](../requirements.txt).
  Django 6.1.2 oficjalnie wspiera Python 3.12–3.14; zakres lokalnej weryfikacji
  na 3.15 i ograniczenia opisuje [aktualizacja interpretera](#aktualizacja-do-pythona-315-17102026).
- PostgreSQL **15+**, zgodnie z [wymaganiami Django 6.1](https://docs.djangoproject.com/en/6.1/ref/databases/#postgresql-notes);
  migracje Tasks korzystają z `TrigramExtension` (`pg_trgm`) i GIN.
- `requirements.txt` przypina dokładne wersje Django, `asgiref`,
  `psycopg2-binary`, `python-dotenv`, PyJWT i `sqlparse` operatorem `==`.
  `asgiref` jest również bezpośrednio używany przez backend uwierzytelniania;
  `sqlparse` jest zależnością Django.
- Django zaktualizowano z **6.0.7** do **6.1.2** w `requirements.txt`
  i lokalnym `.venv` (obecnie Python **3.15.0**). Sterownik PostgreSQL to
  `psycopg2-binary==2.9.13`; pozostałe przypięte pakiety zachowują
  dotychczasowe wersje. W innych środowiskach aktualizację wykonuje
  `.venv/bin/python -m pip install -r requirements.txt`; sama zmiana pliku
  nie aktualizuje zainstalowanych pakietów.
  Zależności warunkowe innych systemów (np. `tzdata` na Windows) rozwiązuje pip.

Brak aktywnego fallbacku SQLite: blok SQLite w settings jest komentarzem.
Nie zastępuj PostgreSQL przy testowaniu funkcji zależnych od jego indeksów/migracji.

Ikony Flaticon UIcons są wersjonowane lokalnie w `static/vendor/flaticon`.
Aplikacja nie wymaga połączenia z CDN ani instalowania npm do ich wyświetlania.
Jedynie regenerowanie podzbioru ikon wymaga narzędzia `fonttools`; źródło,
wersję, sumę kontrolną i komendę opisuje
[instrukcja zestawu](../static/vendor/flaticon/README.md).

## 2. Konfiguracja środowiska

`load_dotenv(BASE_DIR / '.env')` ładuje lokalną konfigurację. Poniżej są nazwy
ustawień i ich znaczenie; nie wartości prywatnego środowiska.

| Zmienna | Znaczenie |
| --- | --- |
| `DEBUG` | Domyślnie false; lokalnie ustaw true |
| `SECRET_KEY` | Klucz Django; wymagany przy DEBUG=false, produkcja odrzuca prefix `django-insecure-` |
| `ALLOWED_HOSTS` | Lista hostów rozdzielona przecinkami; wymagana poza DEBUG |
| `DJANGO_ALLOW_LAN_HOSTS` | Przy DEBUG pozwala na wszystkie hosty; opcjonalne lokalne ustawienie |
| `CSRF_TRUSTED_ORIGINS` | Lista dozwolonych originów |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Połączenie PostgreSQL |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD` | Polityka HTTPS/HSTS |
| `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE` | Ciasteczko sesji |
| `CSRF_COOKIE_SECURE`, `CSRF_COOKIE_HTTPONLY`, `CSRF_COOKIE_SAMESITE` | Ciasteczko CSRF |
| `SECURE_REFERRER_POLICY` | Domyślnie same-origin |
| `MEDIA_ROOT`, `PRIVATE_DOCUMENT_ROOT`, `STATIC_ROOT` | Opcjonalne ścieżki trwałych danych i zasobów; domyślnie katalogi repozytorium |
| `FILE_UPLOAD_TEMP_DIR` | Opcjonalny katalog uploadów tymczasowych |
| `BACKUP_CONTROL_ROOT` | Katalog blokad i znacznika przerwy backupu; pusty wyłącza mechanizm w developmencie |
| `TRUST_PROXY_HEADERS` | Zaufanie do `X-Forwarded-Proto` wyłącznie za kontrolowanym proxy |
| `MAX_PROFILE_PHOTO_SIZE` | Limit zdjęcia, domyślnie 5 MiB |
| `MAX_ATTACHMENT_SIZE` | Limit załącznika, domyślnie 10 MiB |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | Próg uploadu w pamięci, domyślnie 5 MiB |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | Limit danych żądania Django, domyślnie 20 MiB |

`TIME_ZONE` to `Europe/Warsaw`, język `pl-pl`, `USE_TZ=True`.
`MEDIA_ROOT` domyślnie wskazuje `media/`, a `PRIVATE_DOCUMENT_ROOT` wskazuje
`private_documents/`. Produkcja może nadpisać te ścieżki zmiennymi
środowiskowymi o tych samych nazwach.

Nie nadpisuj istniejącego `.env` podczas wykonywania zwykłego zadania.
Nowe środowisko skonfiguruj na podstawie [.env.example](../.env.example).
`.gitignore` pomija `.env` i jego lokalne warianty, zachowując ten przykład.
Pomija również zależności i cache pnpm, cache kompilacji TypeScript,
generowane bundle Reacta i tablicy, raporty coverage/Playwright oraz lokalne
dane aplikacji i pliki pomocnicze SQLite. Źródła, migracje, lockfile pnpm
i wspólne `.vscode/settings.json` pozostają wersjonowane.

## 3. Start nowego środowiska

Komendy wykonuj w katalogu repozytorium. Najpierw skonfiguruj oddzielną bazę
developerską oraz zmienne z poprzedniej sekcji.

```sh
python3.15 --version  # oczekiwane: Python 3.15.0
python3.15 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate --plan
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Jeśli `.venv` już istnieje, sprawdź `.venv/bin/python --version`.
Po zmianie interpretera odtwórz `.venv` i zainstaluj zależności ponownie;
wcześniej zachowaj kopię środowiska i listę lokalnych pakietów z
`.venv/bin/python -m pip freeze --all`, jeśli zawiera ono dodatkowe narzędzia.
Nie przenoś `site-packages` pomiędzy wersjami Pythona.

Na macOS lokalna instalacja z python.org udostępnia interpreter pod ścieżką
`/Library/Frameworks/Python.framework/Versions/3.15/bin/python3.15`.
Jeśli `PATH` wskazuje inny interpreter, użyj pełnej ścieżki przy tworzeniu
środowiska. Sprawdź wersję przed utworzeniem `.venv`, a następnie
`.venv/bin/python --version` i `.venv/bin/python -m pip check`.
Otwarte terminale mogą wymagać nowej sesji lub `exec zsh -l` po zmianie `PATH`.

Konto można założyć przez rejestrację;
do panelu `/admin/` służy opcjonalnie `manage.py createsuperuser`.
Przy DEBUG=false konfiguracja wymaga prawidłowego klucza/hostów i domyślnie
włącza bezpieczne ciasteczka/HTTPS, co nie pasuje automatycznie do lokalnego HTTP.

Migracje są wersjonowane w Git; `.gitignore` nie wyklucza nowych migracji.
Przed wdrożeniem sprawdź `makemigrations --check --dry-run` i `migrate --plan`.
Nowy zestaw migracji początkowych wymaga pustej bazy; nie aktualizuje dawnego
schematu. Procedura i zakres resetu: [Baza danych](DATABASE.md).

Pełne edytory Dokumentów wymagają dodatkowej konfiguracji opisanej w
[OFFICE.md](OFFICE.md): lokalnego ONLYOFFICE oraz zbudowania zasobów tablicy.
Starszy `./scripts/start_office.sh` wymaga lokalnego `deploy/office.compose.yml`,
którego nie ma w repozytorium. Kompletny zestaw uruchamia `./ancore.sh setup`.
Przy ręcznym wdrożeniu buduj `frontend/board` przed `collectstatic`.

## 4. Testy

Regresje poprawek czasu pracy, konfiguracji i nawigacji między Workspace:

```sh
.venv/bin/python scripts/run_tests.py spaces.test_configuration_writes spaces.test_work_logs core.test_navigation_frontend
pnpm --dir frontend/app test
```

Testy konfiguracji używają osobnych połączeń PostgreSQL oraz lokalnego
`lock_timeout`, sprawdzając blokadę podczas zapisu statusu i tworzenia zadania
w prywatnej przestrzeni współdzielącej konfigurację. Obejmują także formularze
zadania rozpoczęte przed usunięciem statusu/typu. Test czasu sprawdza dane
Reacta w zwykłym i scoped adresie oraz zachowanie godzin przy edycji minut.
Testy kontrolera nawigacji nie zastępują próby w przeglądarce: edycja 90 min
→ zmiana minut na 45 → 105 min, a następnie globalne powiadomienie → zadanie
w innym dostępnym Workspace; sprawdź też błąd zapisu, ponowne wejście i telefon.

Losowe identyfikatory Workspace wymagają migracji
`workplaces.0010_random_workspace_identifiers`. Migracja usuwa unikalność nazwy
u właściciela, nadaje wszystkim istniejącym Workspace globalnie unikatowy kod
`w_` + 26 małych liter/cyfr i identyczny slug, zachowując dotychczasowy slug
w `legacy_slug`. Nazwy, PK, dane, członkostwa, awatary i relacje pozostają zachowane.
Stare linki zachowują kontrolę dostępu i prowadzą do właściwego Workspace.
Migracja danych nie odtwarza dawnych kodów przy cofnięciu; do przywrócenia
poprzedniego stanu użyj backupu bazy. Przed wdrożeniem wykonaj standardowe
sprawdzenie planu i backup, a następnie `manage.py migrate`.
Uruchamiaj `workplaces.test_identifiers`, `workplaces`,
`accounts.test_login_redirects`, `dashboard.test_search_regressions`,
`core.test_task_integrity.TaskIdentityTests` i `planner.test_task_calendar`.
Testy obejmują powtarzające się nazwy, niezależność kodu/adresu od nazwy,
kolizje i globalną unikalność w bazie, migrację danych, stare GET/HEAD/POST,
scoped moduły, członków, obce Workspace i cofnięcie dostępu.
Browser QA: katalog → tworzenie dwóch Workspace o tej samej nazwie → edycja,
stały kod po zmianie nazwy, stare linki, wyszukiwanie, błąd/pusty wynik,
referencyjny modal Projektów, ponowne wejście oraz desktop/telefon.

Weryfikacja identyfikatorów (10.10.2026): 153 z 159 testów powyższego zestawu
przeszło, w tym wszystkie 11 testów nowego mechanizmu. Sześć błędów
`workplaces.tests` odtworzono na niezmienionym HEAD w osobnej bazie.
Playwright/Chrome na izolowanej bazie QA przy 1440×1000 i 390×844 potwierdził
powtarzające się nazwy, automatyczny kod tylko do odczytu, zapis i przeładowanie
po zmianie nazwy, stare scoped linki z filtrami, pusty wynik, błąd formularza,
referencyjny modal Projektów i ponowne otwarcie modali. Nie było błędów JavaScript
ani przepełnienia strony. Plugin Browser był niedostępny. Kontrole Django,
migracji, składni, dokumentacji i indeksu przeszły; całego repozytorium
ani innych przeglądarek nie sprawdzano.

`accounts.test_login_redirects` sprawdza wejście na „Dla ciebie” po pierwszym
logowaniu, rejestracji i ponownym logowaniu, ignorowanie `next` z GET/POST,
zachowanie aktywnego Workspace i scoped URL, dostęp członka, obcy Workspace,
błędne hasło oraz CSRF. Uruchamiaj z `accounts.tests`,
`accounts.test_email_identity`, `workplaces.test_defaults`, `workplaces.tests`
i `dashboard.test_for_you`. Browser QA: rejestracja → logowanie → „Dla ciebie”,
ponowne logowanie, wejście z `next` do katalogu Workspace, błędne hasło,
aktywne menu, zwykły/scoped URL i desktop/telefon.

Weryfikacja przekierowania (10.10.2026): z 127 testów powyższego zestawu
121 przeszło, w tym wszystkie 9 nowych testów logowania. Sześć błędów
`workplaces.tests` odtworzono z tymi samymi asercjami na niezmienionym HEAD
w osobnej bazie. Playwright/Chrome na izolowanej bazie QA przy 1440×1000
i 390×844 potwierdził rejestrację, pierwsze i ponowne logowanie, ignorowanie
`next`, aktywny Workspace/scoped URL, członkostwo, błędne hasło, pusty stan,
przeładowanie i powrót po częściowej nawigacji. Nie było błędów JavaScript
ani przepełnienia strony. Plugin Browser był niedostępny. Kontrola Django,
składni Pythona, linków dokumentacji, indeksu i `git diff --check` przeszła.
Nie uruchamiano całego repozytorium ani innych przeglądarek.

Awatary użytkowników wymagają migracji `accounts.0009_user_avatar`, dodającej
pole wyboru bez zmiany dotychczasowych zdjęć. `accounts.0010_user_avatar_thirty`
rozszerza wybór do 30 ilustracji bez zmiany danych. Uruchamiaj `accounts.test_avatars`,
`accounts.tests`, `accounts.test_email_identity`, `workplaces.test_avatars`,
`spaces.test_avatars` i `core.test_file_lifecycle`. Testy obejmują odrębną pulę,
stabilny wybór automatyczny, zapis zalogowanego konta, CSRF, zwykły/scoped kontekst,
walidację obrazu/kadru, zachowanie starszych formularzy oraz sprzątanie po commit
i rollback. Testy historycznych migracji Accounts muszą używać modeli historycznych,
ponieważ starszy schemat nie zawiera pola `avatar`.
Browser QA: Profil → kliknięcie awatara → wybór → zapis pickera → zapis profilu,
przeładowanie, pasek konta, błąd formularza, anulowanie ilustracji i kadru, własny
obraz, brak obrazu/błędny format, Escape/Tab/fokus, szkic profilu, częściowa nawigacja
oraz desktop/telefon. Sprawdź również referencyjne pickery Workspace i Przestrzeni.

Awatary Workspace wymagają migracji `workplaces.0009_workplace_avatar`.
Dodaje ona puste pole motywu; zachowuje istniejące obrazy. Rozszerzenie wspólnej
puli Przestrzeni i Workspace do 30 ilustracji nie wymaga kolejnej migracji:
wybór walidują formularze przez `core.avatars`. Uruchamiaj
`manage.py test workplaces.test_avatars spaces.test_avatars core.test_file_lifecycle`
oraz regresje `workplaces` i `spaces`. Testy obejmują tworzenie/edycję, wszystkie
motywy, zwykłe/scoped ekrany, role, CSRF, walidację uploadu i kadru, zachowanie
starszych formularzy, zastępowanie obrazu i rollback. W przeglądarce sprawdź
Workspace → edycja → kliknięcie awatara lub „Zmień” → okno wyboru → zatwierdzenie
→ zapis Workspace, tabelę i przełącznik, ponowne wejście, własny obraz z kadrowaniem,
anulowanie motywu i kadru, zachowanie szkicu głównego formularza, błąd formularza,
Escape/fokus/Tab w zagnieżdżonych oknach oraz desktop i telefon.


Awatary przestrzeni wymagają migracji `spaces.0003_space_avatar_space_avatar_photo`.
`spaces.test_avatars` sprawdza domyślny wybór, zapis ikon, zwykłe/scoped adresy,
role, prywatny upload, walidację, cofnięcie dostępu, CSRF, podmianę i usuwanie
plików oraz rollback. Przy zmianach sprawdzaj też `spaces`, `core.tests`,
`core.test_file_lifecycle` i `workplaces`. W przeglądarce: kliknięcie awatara,
wybór, zapis i ponowne wejście, aktualizacja menu, własny obraz, przeciąganie,
błędy plików, Escape/fokus oraz desktop i telefon.

Projekt używa testów Django (`TestCase`, `TransactionTestCase`) w modułach.
Polecenia wymagające bazy uruchamiaj na środowisku testowym/developerskim
z możliwością utworzenia bazy testowej. Runner Django tworzy osobną bazę testową.

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py test tasks
.venv/bin/python manage.py test kanban
.venv/bin/python manage.py test core.test_contact_retirement accounts workplaces
.venv/bin/python manage.py test planner dashboard core
.venv/bin/python manage.py test documents
```

Cały zestaw, gdy zakres zmiany tego wymaga:

```sh
.venv/bin/python manage.py test
```

Testy migracji mogą przebudowywać schemat bazy testowej. Nie uruchamiaj ich
ręcznie na bazie z danymi użytkownika. Samo `manage.py check` nie potwierdza
stanu migracji, poprawnego połączenia z bazą ani działania UI.

Historyczne migracje Tasks `0061_directory_favorites` i `0062_task_favorites`
zachowują osobiste ulubione Projektów, Grup i Zadań. Nie przywracają ich
katalogów. `tasks.test_retirement` sprawdza zachowanie danych i brak dawnych
operacji; `spaces.test_navigation` sprawdza bieżące gwiazdki i nawigację.

Historyczne migracje Kanbana `0038_directory_favorites` i `0039_sharing`
zachowują dawne ulubione, prywatność i członkostwa. Test migracji pozostaje
w `kanban.test_sharing`; aktywne endpointy zastąpił kontrakt wycofania sprawdzany
przez `kanban.test_retirement`. Uruchamiaj też regresje Tasks, Workspace,
Planner, Dashboard, Spaces oraz współdzielonych plików/statusów w Core.
Browser QA: dwa konta, „Członkowie” → „Udostępnij”, role i odebranie dostępu,
prywatna tablica w przestrzeni, tryb tylko do odczytu, błąd pobierania członków,
ponowne wejście, klawiatura, szerokość telefonu oraz referencyjne okno Zadań.

### Istniejące obszary testów

`dashboard.test_for_you` sprawdza osobisty widok „Dla ciebie”: wykonawcę,
podzadania, terminy, ulubione, historię autora, zapis oglądanych, paginację,
limit oglądanych do ostatnich 7 dni (granica czasu, wszystkie rodzaje, filtr
przed paginacją, pusty stan i odświeżenie po ponownym otwarciu),
limit 20 najnowszych pozycji w czterech pozostałych zakładkach (wspólny dla
rodzajów i statusów), wybór według utworzenia/aktywności, brak paginacji oraz
ignorowanie dawnych numerów stron,
zwykły/scoped URL, stabilne linki, zmianę Workspace i cofnięcie dostępu.
Obejmuje też filtry przed limitem/paginacją i zachowanie ich w adresach, wyszukiwanie
kluczy, niedostępną przestrzeń, własne nazwy statusów, lokalne grupy dat oraz
skróty przestrzeni z odwiedzin/ulubionych oraz licznik zakładki przypisanych,
ograniczone dostępem. Wiersze zadań sprawdzają własne typy zgłoszeń, dokładne
liczniki tagów/załączników przy wielu relacjach, brak ujawniania metadanych
obcej przestrzeni oraz link podzadania bez metadanych planowania. Grupowanie
statusów obejmuje wszystkie zakładki, własne nazwy i kolejność konfiguracji,
wyniki filtrów, zachowanie grup dat oraz ulubionych przestrzeni i grup.
Tabela przestrzeni w „Dla ciebie” sprawdza licznik widocznych zadań (także
zakończonych), ukrytych rodziców/potomków i obcy Workspace, role menu,
zwykłe/scoped odnośniki oraz osobistą gwiazdkę. Wspólny dekorator tabel wymaga
regresji `spaces.tests.SpaceTests`, `spaces.test_management` i `spaces.test_navigation`.
Przy zmianach uruchom też Dashboard, testy prywatności Zadań i Kanbana,
`core.test_task_integrity.TaskIdentityTests`, Workplaces i testy menu Core.
W przeglądarce sprawdź wszystkie zakładki, limit 20 bez paginacji w czterech
zakładkach, paginację oglądanych, wejście w element i powrót,
Dashboard i listę zadań Przestrzeni jako referencje, nawigację modułów,
kolory/liczniki statusów i zwijanie myszą/klawiaturą (również po ponownym wejściu),
telefon, puste stany oraz błąd sieci.
Przestrzenie w zakładkach „Ulubione” i „Ostatnio oglądane” porównaj z tabelą
„Zarządzaj przestrzeniami”: awatary, otwarcie przestrzeni, ponowne wejście
i poziome przewijanie na telefonie. W „Dla ciebie” nie ma menu działań ani
pustej kolumny po nim; pełne menu (Escape/fokus), gwiazdkę i filtry sprawdzaj
w katalogu i zarządzaniu Przestrzeniami.
Ramkę sekcji „Przestrzenie”, wysokość nagłówka/wierszy i poziome podziały porównaj
z grupami zadań. Sprawdź licznik osobno dla każdej daty, zwijanie nagłówkiem,
Enter/Spacją oraz brak checkboxów i pustej kolumny wyboru w każdej zakładce.
W „Dla ciebie” sprawdź kolejność trzech kolumn danych: Przestrzeń, Klucz, Opis,
brak Rodzaju/Szablonu/Zadań również po odtworzeniu preferencji, wyrównanie komórek
na telefonie i pełny zestaw kolumn w katalogu oraz zarządzaniu. Checkboxy pozostają
na listach zadań, w backlogu i w katalogach przestrzeni poza „Dla ciebie”.
Pełne nazwy przestrzeni w „Dla ciebie” muszą mieścić się bez wielokropka,
zachowując wspólne wyrównanie kluczy i odstęp 100px. Sprawdź długą nazwę,
przeładowanie, zwinięcie/rozwinięcie grupy oraz poziome przewijanie na telefonie;
katalog i zarządzanie nadal stosują dotychczasowe szerokości i skracanie nazw.

| Moduł | Co sprawdzają istniejące testy |
| --- | --- |
| Accounts | Konto/profil, kadrowanie i walidacja obrazu, obecność, przełączanie kont |
| Workplaces | Wybór i izolacja Workspace, scoped URL, ulubione, zmiany i usuwanie |
| Tasks | Numeracja, hierarchie, CRUD, zakres dostępu, formularze, katalogi, paginacja, zapytania, historia, pliki |
| Tasks: `test_project_visibility.py` | Publiczne i prywatne projekty, rzeczywisty odbiorca, dziedziczenie dostępu, zwykłe/scoped URL, operacje zbiorcze, formularze, pliki, search, Dashboard, kalendarz, powiadomienia i szablony |
| Tasks: `test_work_logs.py` | Dziennik pracy: CRUD, autor, osobne podzadania, zwykłe/scoped URL, izolacja kont i Workspace, odebranie dostępu, stabilne PK, dwukierunkowe przeliczanie godzin/minut i dat, północ i zmiany czasu, zachowanie pól po błędach, paginacja/sumy, walidacja, CSRF, usunięcie autora, CASCADE oraz rollback wraz z historią |
| Tasks: `test_legacy_time_migration.py` | Migracja dawnej kolumny czasu: świeża i starsza baza, zachowanie danych, tworzenie zadań i podzadań, zwykłe/scoped URL, autor historii i izolacja Workspace |
| Osobne testy Tasks | Słowniki źródeł, reguły terminów, nadpisanie reguł per projekt i migracje |
| Kanban | Tablice/kolumny/karty, właściciel, zmiany statusu, katalogi, tagi, pliki |
| Contacts | Wycofanie katalogów: 404 dla GET/POST w obu wariantach URL, brak menu/wyszukiwania/admina, historyczne ulubione i zachowanie kont/członkostw/relacji projektów |
| Planner | Wydarzenia i izolacja właściciela |
| Dashboard | Wyszukiwanie, powiadomienia i integracje |
| Dashboard: `test_search_regressions.py` | Lista Workspace według członkostwa odbiorcy, cofnięcie dostępu, trwałe linki zadań/podzadań i kart/podkart po renumeracji/usunięciu, Unicode, limit SQL i granica 20 wyników |
| Core | Wspólne mechanizmy i kontrakty UI/uploadu według aktualnych przypadków |
| Core: `test_status_updates.py` | Zapis statusu bez nadpisywania pozostałych pól, zwykłe i scoped URL, autor historii, powtórne zamknięcie, rollback statusu razem z historią oraz dwa równoczesne żądania zamknięcia w PostgreSQL |
| Core: `test_task_integrity.py`, `test_task_number_migrations.py` | Stabilne PK, dwie karty/Workspace, uprawnienia, kalendarz, powiadomienia, równoczesne tworzenie, unikalność i naprawa istniejących numerów |
| Documents | Dyski, foldery, pliki, kosz, izolacja, modale, paginacja, wyszukiwarka, migracja dysków |
| Documents: `test_suite.py` | Tworzenie czterech typów, osobna karta ONLYOFFICE/BOARD i katalog po utworzeniu, linki listy/kafelków/metadanych oraz cel wyników wyszukiwania, podpisane callbacki i źródła, deduplikacja, konflikty tablicy, walidacja OOXML, izolacja właściciela/Workspace, stara sesja po podmianie/koszu |
| Documents: `test_office.py` | Osobny katalog Dokumentów, edycja i konflikt rewizji, formatowanie/eksport DOCX, import, walidacja/rollback plików, dwa konta i Workspace, globalne szukanie |
| Documents: `test_office_query.py` | Łączenie filtrów katalogu Dokumentów, płaski katalog i stare parametry folderów, typy natywne i uploady, granice rozmiaru, daty kosza, kierunki sortowania, stare linki, izolacja oraz zachowanie warunków w paginacji i akcjach |

Lista klas i liczba zdefiniowanych metod testowych jest generowana w
[CODE_INDEX.md](CODE_INDEX.md). Nie jest to raport wykonania testów ani procent pokrycia.

`workplaces.test_defaults` sprawdza losową nazwę pierwszego Workspace po
rzeczywistym logowaniu, zapis roli właściciela/ulubionego Dashboardu oraz kodu
i slugu, zachowanie nazwy po edycji i ponownym logowaniu, zwykłe/scoped adresy,
istniejącą dawną nazwę, dostęp przez członkostwo i brak tworzenia dla anonimowego
użytkownika. Test transakcyjny na PostgreSQL wymusza równoczesne pierwsze
wejścia i sprawdza pojedynczy Workspace. Uruchamiaj razem z `workplaces`
i `accounts.tests`. W przeglądarce sprawdź nowe konto → pierwsze logowanie →
losową nazwę w przełączniku i katalogu Workspace → przeładowanie/powrót,
desktop/telefon oraz edycję nazwy przez istniejący formularz.

Tworzenie samodzielnych zadań Przestrzeni sprawdzają
`spaces.test_independent_tasks`, `spaces.test_issue_types`,
`spaces.test_task_detail_parity` i `workplaces.test_team`. Katalog,
filtrowanie i paginację sprawdzają `spaces`, `dashboard.test_filters`
oraz `core.test_frontend`. Dawne testy katalogów Tasks zastąpił kontrakt
`tasks.test_retirement`.

## 5. Dobór zakresu sprawdzenia

| Zmiana | Minimalny sensowny zakres |
| --- | --- |
| Jedna funkcja domenowa | Testy tego zachowania, formularza i kontroli dostępu |
| Model, usuwanie, migracja | Dane przed/po, zależności, ograniczenia i odpowiednie testy migracyjne |
| Workspace/owner/URL | Dwa konta, dwa Workspace, formularze, bezpośrednie URL, search/download |
| Wspólny tag | Tasks, Kanban, Documents i globalne szukanie |
| Wspólny CSS/JS | Ekran zmieniany oraz odbiorcy komponentu, reload i ponowne wejście |
| Pliki | Format, rozmiar, pusty plik, obcy właściciel, kosz i pobieranie |
| Same opisy | Linki, aktualność indeksu i zgodność twierdzeń z kodem |

Przy zmianie UI stosuj [procedurę wizualnej weryfikacji](UI.md).
Test HTML sprawdzający klasę nie dowodzi, że końcowy układ wygląda prawidłowo.

Przy zmianie nawigacji sprawdź bazowy i scoped URL, przejścia między wszystkimi
modułami, aktywne menu, filtry/paginację, modale po powrocie, Wstecz/Dalej,
szybkie kliknięcia oraz odrzucenie wyjścia z niezapisanego zadania. Porównanie
tego samego obiektu `document`/sidebaru lub znacznika na `window` przed i po
kliknięciu potwierdza brak pełnego przeładowania. Sprawdź również doładowanie
skryptów Kalendarza/Dysku, pusty stan, błąd pobrania i zmianę konta/Workspace
w odpowiedzi. Dla linków i granic danych uruchom
`core.test_task_integrity.TaskIdentityTests`, `dashboard.test_notifications`
i `planner.test_task_calendar`; testy backendu nie zastępują prób w przeglądarce.

## 6. Utrzymanie dokumentacji

| Zmieniło się | Zaktualizuj |
| --- | --- |
| Moduł, zależność, routing lub układ katalogów | `ARCHITECTURE.md`, `MODULES.md`, indeks kodu |
| Zachowanie biznesowe lub nowa funkcja | `MODULES.md`, `MECHANISMS.md`, odpowiednie ograniczenia |
| Uprawnienia, sesja, identyfikatory, pliki | `MECHANISMS.md`, macierz sprawdzeń |
| Komponent UI, token, wzorzec, inicjalizacja JS | `UI.md`, opcjonalnie `MECHANISMS.md` |
| Konfiguracja, zależności, testy, wdrażanie | `DEVELOPMENT.md`, w razie potrzeby README |
| Zasady przyszłej pracy agenta | `AGENTS.md` |

Indeks generuje skrypt oparty na AST Pythona i listach plików:

```sh
python scripts/update_code_index.py
python scripts/update_code_index.py --check
```

Nie wymaga zależności aplikacji ani bazy. Uwzględnia wszystkie obecne lokalnie
źródła w katalogach aplikacji, również nowe pliki przed dodaniem do Git.
Generuje strukturę, modele/relacje, formularze, routing, definicje widoków,
szablony, statyczne zasoby, oba pakiety frontendu, spis testów oraz narzędzia
i konfigurację wdrożenia. Nie analizuje semantycznie, czy wszystkie
zdefiniowane funkcje są osiągalne.

Tryb `--check` porównuje bieżący indeks z wynikiem generatora i kończy się
błędem, jeśli indeks wymaga aktualizacji. Nie sprawdza prawdziwości opisów
pisanych ręcznie; te trzeba porównywać z zachowaniem zmienianego kodu.

## 7. Rzeczy ustalone podczas pierwszego przeglądu

To obserwacje stanu na 15.09.2026, nie lista wdrożonych poprawek.

- Drzewo robocze miało zmiany aplikacji przed utworzeniem dokumentacji,
  m.in. cały moduł Documents i jego integrację. Dokumentacja obejmuje ten stan.
- Ówczesny `.gitignore` ignorował `**/migrations/*.py` z wyjątkami. Odczyt
  lokalnych katalogów wykazał migracje nieśledzone także w starszych modułach.
  Obecne reguły nie wykluczają migracji; są one wersjonowane w `backend/`.
- Ówczesny `requirements.txt` nie przypinał dokładnych wersji. Obecnie
  zależności backendu są przypięte do wersji lokalnie zweryfikowanych.
- Dawny `tasks/views.py` był pustą pozostałością obok pakietu widoków.
  Obie implementacje usunięto podczas porządkowania 18.10.2026.
- Nazwy części plików/bloków/klas są historyczne. Decydują aktywne importy,
  trasy i wywołania, nie nazwa.
- Uprawnienia udostępniania są wyłączone mimo pozostałych modeli/helperów.
- Część preferencji w `localStorage`, w tym Sticker, nie ma zakresu konta.
- Powiadomienia są historią właściciela z Tasks/Kanban; helper nie ogranicza
  ich do bieżącego Workspace.
- Częściowa nawigacja ma listę obsługiwanych ścieżek, nie obejmuje automatycznie
  nowych modułów ani wszystkich wariantów scoped URL.
- Dysk ma prywatny storage; standardowe media są serwowane w DEBUG
  przez konfigurację Django. Politykę plików produkcji trzeba sprawdzić osobno.
- `Task`/Kanban numerują i renumerują `task_id`; numer nie jest trwałym PK.
- Wspólne reguły CSS nadpisują m.in. kolory i wagi; bazowy plik komponentu
  nie wystarcza do odtworzenia finalnego wyglądu.

Aktualny Docker Compose i polecenia utrzymania opisuje [Produkcja](PRODUCTION.md).
Testy frontendu uruchamia `pnpm --dir frontend/app test`; ich zakres opisuje
[Frontend React](FRONTEND.md). Nie zakładaj istnienia dodatkowych usług CI
lub workerów na podstawie samej konfiguracji modeli.

## 8. Wdrożenie

Gotowy wariant jednego serwera z pięcioma usługami, instalatorem, trwałymi
wolumenami i backupem opisuje [Produkcja Docker Compose](PRODUCTION.md).
`deploy/compose.yaml` rozdziela Nginx, Django/Gunicorn, PostgreSQL, backup
i ONLYOFFICE. Dane na dysku i archiwa nie są szyfrowane. Poniżej pozostają
zasady ścieżek dla wdrożeń ręcznych.

Po przeniesieniu źródeł dodaj katalog `backend/` do ścieżki importów procesu
serwera. Przykład zmiennej środowiskowej (podstaw rzeczywistą ścieżkę):

```sh
export PYTHONPATH=/ścieżka/do/ancore/backend
```

Wejścia pozostają `ancore.wsgi:application` oraz `ancore.asgi:application`.
Alternatywnie użyj opcji serwera wskazującej katalog importów. Nie importuj
`backend.ancore` ani `backend.spaces`: aplikacje zachowują pierwotne nazwy.
`manage.py` ustawia ścieżkę samodzielnie. `BASE_DIR` nadal wskazuje katalog
repozytorium, więc nie trzeba przenosić `.env`, mediów, prywatnych dokumentów,
zasobów ani plików zbieranych przez `collectstatic`.

Projekt ma wejścia WSGI i ASGI. Pakiet Compose używa Gunicorna; rzeczywistą
domenę, certyfikaty i katalog kopii ustala administrator przy instalacji.
Domyślnie `STATIC_ROOT` wskazuje `BASE_DIR / 'staticfiles'` (katalog ignorowany
przez Git). `manage.py collectstatic --noinput` zbiera tam zasoby do serwowania
przez serwer produkcyjny; `--dry-run` pozwala sprawdzić zbieranie bez zapisu.

Publiczne media ogranicz do `profile_photos/` i `workplace_photos/`
oraz rozszerzeń JPG/JPEG/PNG/WebP. Nie konfiguruj publicznego
aliasu całego `MEDIA_ROOT`: `task_attachments/` i `kanban_attachments/` są
prywatne i wymagają pobierania przez widoki aplikacji. Wbudowany routing DEBUG
egzekwuje tę listę w `backend/core/media.py`. Dysk/Dokumenty pozostają poza publicznym
storage. Konfiguracja zewnętrznego serwera nie jest częścią repozytorium.

Przy wdrożeniu ręcznym ustal konfigurację procesu, statycznych
zasobów, HTTPS, bazy, migracji oraz publicznych/prywatnych plików. Nie zapisuj
sekretów ani danych połączenia do tej dokumentacji.

### Naprawy integralności kont i plików

Przed uruchomieniem wersji z unikalnością e-maili wykonaj `manage.py migrate`.
Migracja `accounts/0008_user_email_case_insensitive.py` dodaje unikalny indeks
`Lower(email)`. Jeśli wykryje stare duplikaty, zatrzymuje się przed zmianą
danych: administrator musi wyjaśnić tożsamości i poprawić adresy. Nie scala
ani nie usuwa kont. Test migracji obejmuje zachowanie danych przy takim błędzie.

Testy `accounts.test_email_identity` i `core.test_file_lifecycle` obejmują
walidację/rejestrację/profil, konflikt zapisu po walidacji, zaproszenia,
ograniczenie bazy, migrację, publiczne media, kontrolowane pobieranie oraz
commit/rollback usuwania załączników, plików Dysku i całego Workspace.
Sprzątanie dotyczy nowych operacji usuwania; nie kasuje automatycznie plików
osieroconych przez starszą wersję. Błędy storage po commit są logowane i
wymagają sprawdzenia logów oraz miejsca na dysku.

## 9. Granice pierwszej weryfikacji

Dokumentację opracowano z kodu, routingu, modeli, szablonów, CSS/JS i testów.
Odczytano wersje lokalnego runtime. Nie wykonywano migracji ani zapisu danych
aplikacji w ramach dokumentowania.

Weryfikacja 15.09.2026:

- `python scripts/update_code_index.py --check` — indeks aktualny.
- Kontrola lokalnych linków dokumentacji — 494 poprawne cele, brak brakujących.
- `DEBUG=true .venv/bin/python manage.py check` — brak zgłoszonych problemów.
- `git diff --check` i kontrola whitespace nowych dokumentów — bez błędów.
- Porównanie sum źródeł aplikacji przed/po dokumentowaniu — bez zmian.

Nie uruchamiano pełnego zestawu testów ani wizualnej weryfikacji ekranów;
zakres zmian obejmuje dokumentację i jej generator.

## 10. Uruchomienie osobnego modułu Dokumenty

Migracja `documents/0004_workspacedocumentfolder_workspacedocument_and_more.py`
dodaje dwie osobne tabele oraz ich ograniczenia i indeks. Nie przenosi ani nie
zmienia rekordów Dysku. Przed wejściem do Dokumentów zastosuj migrację na bazie
danego środowiska; nowa trasa to `/office/` i jej wariant scoped Workspace.
Nie dodano zależności Python/npm ani usług zewnętrznych.

Migracja `documents/0006_workspacedocument_tags.py` dodała historyczną relację
Dokumentów do `tasks.TaskTag`. Obecnie Dysk i Dokumenty nie obsługują tagów;
stare relacje pozostają w bazie, więc usunięcie funkcji nie wymaga migracji
ani kasowania danych. Testy sprawdzają brak pól i filtrów tagów, pomijanie
starych parametrów i zapisów, wyszukiwanie oraz kopie bez tagów.

Migracja `documents/0007_workspacedocumentfolder_is_starred.py` dodaje gwiazdkę
folderom Dokumentów; istniejące foldery początkowo nie są oznaczone.
Jest zachowana jako historyczna migracja. Foldery Dokumentów zostały
wycofane z interfejsu i routingu; model oraz relacja pozostają w bazie.
Nie ma nowej migracji ani usuwania danych. `documents.test_office_folders`
sprawdza płaski katalog, stare odnośniki, brak aktywnych akcji folderów,
zachowanie treści, upload, wyszukiwanie, paginację i izolację kont/Workspace.
`documents.test_migrations` nadal sprawdza historyczne migracje.

Migracja `documents/0008_folder_is_starred.py` dodaje analogiczne pole folderom
Dysku z domyślną wartością false, bez zmiany gwiazdek w Dokumentach.
Wymaga zastosowania przed uruchomieniem nowego widoku Dysku.
`documents.test_drive_folders` obejmuje listę i kafelki, gwiazdki i filtry
między dyskami, rozmiary folderów, ZIP oraz granice dostępu do podfolderów.

Migracja `documents/0009_drive_office_editor.py` dodaje plikom Dysku rewizję,
klucz sesji, flagę błędu zapisu oraz tabelę `DriveOfficeSaveReceipt`.
Zastosuj ją przed uruchomieniem wersji z edycją Office na Dysku; istniejące
pliki i ich lokalizacja pozostają bez zmian. Serwer ONLYOFFICE i konfiguracja
są wspólne z Dokumentami. `documents.test_drive_office` obejmuje trzy formaty,
listę/kafelki/wyszukiwarkę, zwykłe i scoped URL, zapis/konwersję, błędne pliki,
CSRF, izolację kont/Workspace/modułów, deduplikację oraz unieważnianie sesji.

Migracja `documents/0010_icon_colors.py` dodaje kolor ikony do dysków i obu
modeli folderów. Istniejące dyski otrzymują `#4285d4`, foldery `#ffd855`;
hierarchia i pliki pozostają bez zmian. Zastosuj ją przed uruchomieniem wersji
z wyborem koloru. `documents.test_colors` sprawdza zapis, walidację, przywracanie
domyślnego koloru, zgodność starych formularzy, listę/kafelki i granice dostępu.

Sprawdzenia funkcji obejmują `manage.py test documents` oraz
`manage.py test workplaces dashboard core`. Siedem starszych testów Workspace/core
ma oczekiwania niezgodne z obecną nawigacją i CSS; ten sam zestaw błędów
odtworzono na kopii wersji sprzed dodania Dokumentów. Nie należy traktować
tego jako zielonego wyniku całego zestawu. Szczegóły aktualnego wykonania
podaje podsumowanie zadania.


Migracja `documents/0011_workspacedocument_is_pdf_form_and_more.py` dodaje
pola formularza PDF i szablonu oraz `DocumentVersion` z wyłącznym powiązaniem
z Dyskiem albo Dokumentami. Jest addytywna; istniejące pliki nie są przenoszone.
Zastosuj ją przed uruchomieniem ekranów PDF i szablonów. Nowe puste PDF-y są wersjonowane
w `backend/documents/blank/`; ich pochodzenie opisuje tamtejszy README. Nie ma nowych
zależności aplikacji. Historia wersji została wycofana z Dysku i Dokumentów;
model i migracja pozostają dla zgodności z istniejącymi danymi. Nie ma nowej
migracji ani masowego usuwania archiwów. Dotychczasowe pliki historii nadal
należy uwzględniać w backupie prywatnego storage.

`documents.test_office_extras` sprawdza PDF/formularze, kopie szablonów, prywatny
katalog, brak akcji historii na liście i kafelkach obu modułów, brak aktywnych
adresów historii/pobierania/przywracania, zapis bez nowych archiwów, cleanup
po commit, zachowanie dawnych archiwów, błędy storage i rollback zapisu.
Testy `test_suite`, `test_drive_office` i `test_office` nadal sprawdzają
rewizje, konflikty, CSRF, granice dostępu oraz unieważnianie sesji edytora.

## Wdrożenie pracy zespołowej

Przed uruchomieniem nowego ekranu zespołu zastosuj migrację Workspace 0008.
Sprawdź zduplikowane slugi: migracja rozróżnia adresy przestrzeni różnych właścicieli.
Szczegóły zakresu, przechowywania danych i testów: [TEAMWORK.md](TEAMWORK.md).

## Centrum powiadomień

Wyłączenie powiadomień o historii zmian nie wymaga migracji. Historia Zadań
i Kanbana pozostaje w bazie; panel i jego akcje pomijają `kind='system'`,
także z dawnymi stanami lub dostawami do obserwujących. Nowe dostawy obserwowania
obejmują komentarze. `dashboard.test_notifications` sprawdza wszystkie filtry,
liczniki, puste stany, paginację oraz pomijanie historii w akcjach osobistych
i zbiorczych; `dashboard.test_collaboration` sprawdza zapis statusów i historii
bez powiadomień oraz komentarze w obserwowanych zadaniach i podzadaniach.

Usuwanie powiadomień wymaga migracji `dashboard/0003_notificationstate_is_deleted.py`.
Dodaje `is_deleted=False` do istniejących stanów; nie usuwa źródeł ani danych historycznych.
Testy Dashboardu obejmują usuwanie osobiste i zbiorcze, więcej niż 500 wpisów,
podpisane snapshoty, nowe zdarzenia, archiwum, izolację kont/Workspace, cofnięty
dostęp, zaproszenia dostępne po ukryciu oraz ponowne odpytywanie przypomnień.
Testy przeglądarkowe powinny objąć odczyt wszystkich stron, anulowanie i potwierdzenie
usunięcia, błąd zapisu/ponowienie, klawiaturę, reload i wąski ekran.

Rozszerzenie kalendarza, przypomnień i szablonów wymaga addytywnych migracji
`dashboard/0002_taskreminder_and_more.py`, `kanban/0035_kanban_due_at.py`
i `tasks/0048_taskprojecttemplate.py`. Dodają dostawy przypomnień i ich
osobisty stan, opcjonalny termin kart oraz snapshoty szablonów. Istniejące
projekty i zadania nie są kopiowane ani przenoszone. Nie ma nowych zależności,
usług, konfiguracji poczty ani cron — przypomnienia w aplikacji obsługuje polling.

Testy `planner.test_task_calendar`, `dashboard.test_reminders` oraz
`tasks.test_project_templates` obejmują terminy i linki, izolację Workspace,
wycofanie dostępu, zegar przypomnień, deduplikację, snapshoty odczytu,
paginację, kopiowanie hierarchii, reset stanu wykonania i rollback.
`kanban.test_retirement` sprawdza pomijanie historycznych terminów kart.
Historyczny test Workspace wycofuje również Tasks do 0047, ponieważ
szablony 0048 zależą od Workspace 0008.

Przed uruchomieniem zastosuj addytywną migrację `dashboard/0001_initial.py`.
Dodaje osobisty stan odczytu i archiwum bez kopiowania lub zmiany historii.
Nie wymaga nowych zależności ani workera. Migracja zależy od Workspace 0008,
Tasks 0047 i Kanban 0034. Testy historycznych migracji wycofują również
Dashboard, aby stan modeli odpowiadał schematowi sprzed tych zależności.

Zakres sprawdzeń: `manage.py test dashboard workplaces.test_team
core.test_task_integrity core.test_task_number_migrations`.
`dashboard.test_notifications` obejmuje odczyt, archiwizację, idempotencję,
izolację kont i Workspace, cofnięcie członkostwa, CSRF, zaproszenia, stabilną
paginację, podpisane snapshoty zbiorczego odczytu, nowe zdarzenia, escapowanie
HTML, CASCADE i ograniczenia bazy. Przeglądarka powinna sprawdzić panel,
przekierowanie z wycofanej strony `/notifications/`, telefon, klawiaturę,
pusty stan, błąd/ponowienie i częściową nawigację.

## Zgodność dawnej kolumny czasu zadań

Migracja `tasks/0051_legacy_logged_seconds_default.py` naprawia zapis zadań
i podzadań w bazach, w których po dawnej wersji pomiaru czasu pozostała
kolumna `tasks_task.logged_seconds` z `NOT NULL`, bez wartości domyślnej.
Obecny model `Task` nie używa tej kolumny, dlatego taki schemat blokował INSERT.
Migracja ustawia domyślne `0` w bazie tylko wtedy, gdy kolumna istnieje i nie
ma wartości domyślnej. Zachowuje dotychczasowe wartości i wpisy `TaskWorkLog`;
nie dodaje kolumny do świeżych baz ani nie zmienia stanu modeli Django.
Wycofanie migracji pozostawia tę zgodność, aby nie przywrócić błędu zapisu.
Zastosuj ją przez `manage.py migrate` przed tworzeniem kolejnych zadań.

Testy `tasks.test_legacy_time_migration` odtwarzają błąd na starszym schemacie
i sprawdzają zapis po migracji, obie wersje URL, autora historii, kontekst
Workspace, zamknięcie podzadania oraz zachowanie zapisanych czasów.

## Wzmianki i obserwowanie

Przed uruchomieniem wersji zastosuj migrację
`dashboard/0004_mentions_and_following.py`. Dodaje `ObjectFollow` oraz
`ActivityInterest` z FK, ograniczeniem jednego źródła i unikalnością odbiorca
+ źródło. Nie zmienia istniejącej historii, stanów powiadomień ani członkostw.
Nie dostarcza historycznych komentarzy jako nowych wzmianek.

`dashboard.test_collaboration` sprawdza wzmianki, podpowiedzi osób, pełne nazwy
powiązane z ID, powtarzające się nazwiska, zakresy Unicode i usunięte wzmianki, oba modele
i warianty URL, obserwowanie zadań/projektów, wyłączenie i ponowienie,
deduplikację, własne działania, cofnięcie dostępu, CSRF, rollback, ograniczenia
bazy, paginację i osobisty odczyt/archiwum. Powiązane regresje obejmują Zadania,
Kanban, Dashboard, Workspace i Core.

## Załączniki komentarzy

Migracje `tasks/0052_comment_images.py` i `kanban/0036_comment_images.py`
dodają osobne tabele zdjęć wiadomości, bez zmiany dawnych komentarzy i załączników.
Przed uruchomieniem nowego kodu wykonaj `manage.py migrate`. Obrazy korzystają
z istniejącego `PRIVATE_DOCUMENT_ROOT` i limitu `MAX_ATTACHMENT_SIZE`.
Migracje `tasks/0053_comment_attachment_size.py` i
`kanban/0037_comment_attachment_size.py` dodają rozmiar załącznika. Te same
rekordy obsługują teraz wszystkie pliki dopuszczone przez wspólny walidator;
stare zdjęcia i ich adresy pozostają dostępne.

`core.test_comment_images` sprawdza tekst/obrazy/pliki, zadania/podzadania i karty/podkarty,
zwykłe/scoped URL, format/rozmiar/liczbę plików, partie mieszane, starsze pole
`comment_images`, pobieranie zamiast inline dla dokumentów, CSRF, autorstwo, wzmianki,
izolację Workspace, cofnięcie członkostwa, prywatny odczyt oraz rollback bazy
razem z plikami i sprzątanie po zatwierdzonym usunięciu. Uruchamiaj wraz z
`dashboard.test_collaboration` i regresjami załączników Tasks/Kanban.

## Udostępnianie projektów członkom Workspace

Tasks `0055_project_sharing` dodaje relację odbiorców, a
`0056_project_invitations` przenosi jej wpisy do jawnych członkostw z rolą
„Członek” i dodaje zaproszenia. Migracja zachowuje dostęp w obu kierunkach.
Dashboard `0005_project_invitations` rozszerza osobisty stan powiadomień.
Tasks `0057_project_observer` dodaje rolę tylko do odczytu do obu pól `role`,
bez migracji istniejących wartości. Są to historyczne dane: obecne testy
`tasks.test_retirement` sprawdzają wyłączenie operacji, a `spaces.test_write_access`
i `spaces.test_task_detail_parity` bieżące role i granice odczytu/zapisu.
Uruchom `manage.py migrate`; sprawdź obecność wszystkich plików migracji
w repozytorium. UI korzysta z `project-team.js`, istniejącego pickera
`workplace-team.js`, tabel Workspace oraz stylów `workplace-team.css`.

Sprawdzenia: `manage.py test tasks.test_project_invitations tasks.test_project_sharing
tasks.test_project_visibility tasks.test_project_templates workplaces.test_team
workplaces.test_management workplaces.test_invitation_candidates dashboard.test_collaboration
dashboard.test_notifications dashboard.test_workspace_invitations`.
Test migracji odtwarza wcześniejsze udostępnienie i sprawdza jego zachowanie
po przejściu na członkostwo. Pozostałe testy obejmują natychmiastowy dostęp,
brak zaproszeń, role projektu, CSRF, granice Workspace oraz pliki
i inne powiązane moduły po cofnięciu dostępu.

Browser QA: porównanie z oknem Workspace, natychmiastowe udostępnienie na dwóch
kontach, zmiana roli i usunięcie członka, błąd odbiorcy spoza Workspace,
brak wyników wyszukiwania, zachowanie szkicu głównego formularza, telefon,
klawiatura i ponowne wejście przez częściową nawigację.

## Widoczność i zespół grup

Zastosuj `tasks/0058_section_sharing` i `dashboard/0006_section_sharing` przez
`manage.py migrate` przed uruchomieniem nowej wersji. Migracje są addytywne;
istniejące grupy otrzymują widoczność publiczną w zakresie projektu, bez nowych
członkostw i bez przenoszenia zadań. Pliki migracji są wersjonowane.

`tasks.test_section_sharing` sprawdza natychmiastowy dostęp bez zaproszeń, role, CSRF, rzeczywistego autora, prywatność projektu nadrzędnego,
cofnięcie członkostwa i publikację, zwykłe/scoped URL, stare drzewa podzadań,
pliki, listy, szablony, liczniki, powiadomienia i migrację wcześniejszych grup. Uruchamiaj wraz z testami
prywatności i zespołu projektów oraz regresjami Tasks/Kanban/Workspace/Planner/
Dashboard/Core. W przeglądarce sprawdź menu grupy, widoczność, zespół na dwóch
kontach, błędnego odbiorcę, brak wyników wyszukiwania, szkic głównego formularza,
obserwatora, telefon, klawiaturę, częściową nawigację i referencyjny modal projektu.

Migracja `tasks/0059_direct_sharing` kończy przepływ zaproszeń do projektów i grup.
Przed uruchomieniem wykonaj `manage.py migrate`. Ważne oczekujące zaproszenia
są przekształcane w członkostwa po ponownej walidacji uprawnień; odrzucone,
wygasłe i wycofane nie nadają dostępu. Istniejące członkostwa zachowują role.
`tasks.test_direct_sharing_migration` sprawdza konwersję obu poziomów,
granice Workspace, nieaktywne konta, prawa autora, projekt nadrzędny oraz
zachowanie istniejących ról. Cofnięcie migracji zachowuje nadany dostęp.
Zaproszenia do Workspace nadal wymagają przyjęcia.

## Widoczność i zespół zadań

Przed uruchomieniem zastosuj `tasks/0060_task_sharing` przez `manage.py migrate`.
Migracja zachowuje wcześniejszy odziedziczony dostęp i normalizuje historyczne
wpisy utworzenia podzadań do stabilnego PK; nie nadaje nowych członkostw.
Nowe formularze tworzą prywatne zadania faktycznego autora.

`tasks.test_task_sharing` sprawdza natychmiastowy dostęp bez zaproszeń, role,
CSRF, kandydatów, Workspace i całe drzewa rodziców, cofnięcie dostępu, publikację,
starsze formularze, autora, podzadania i historię, pliki, wzmianki, przypomnienia,
listy, search, kalendarz, szablony oraz migrację. Uruchamiaj wraz z testami
projektów i grup oraz regresjami Tasks/Kanban/Workspace/Planner/Dashboard/Core.
W przeglądarce sprawdź dwa konta, członka i obserwatora, odebranie dostępu,
zapis widoczności przez AJAX, szkic formularza, tworzenie zadania/podzadania,
błąd i pusty wynik pickera, telefon, fokus i Escape, zakładki klawiaturą,
ponowne wejście przez częściową nawigację oraz referencyjne okna projektu/grupy.

## Moduł Zasoby

Przed uruchomieniem zastosuj `resources/0001_initial.py` przez
`manage.py migrate`. Migracja dodaje osobną tabelę, relacje do kont i Workspace,
indeks zakresu/statusu oraz ograniczenia numeru ewidencyjnego, typu, statusu i dat.
Nie zmienia istniejących danych innych modułów ani nie wymaga nowych zależności.

Uruchamiaj `manage.py test resources dashboard.test_search_regressions workplaces.tests`
oraz regresje uprawnień Workspace. Testy Zasobów obejmują zwykłe/scoped URL,
CRUD, autora operacji, dwa Workspace jednego właściciela i obcy zespół,
cofnięcie dostępu, wybór osoby, daty i unikalność w bazie, filtry, paginację,
wyszukiwanie globalne, CSRF, escapowanie, usuwanie konta i kaskadę Workspace.
Browser QA: pusty katalog, tworzenie, edycja, duplikat numeru, błąd sieci/ponowienie,
filtry, usuwanie/anulowanie, fokus, Escape, telefon, ponowne wejście przez menu
oraz ekran referencyjny Projektów/Firm. Częściowa nawigacja obejmuje listę
oraz bezpośrednie adresy tworzenia i edycji zasobów.

## Wycofanie katalogów Kontaktów, Firm, Użytkowników i Gości

Zmiana nie wymaga migracji. Modele i dane historyczne pozostają, natomiast
routing, pozycje menu, globalne wyniki wyszukiwania i Django admin są wyłączone.
Stare ulubione są pomijane przez katalog dozwolonych skrótów.
Testy: `manage.py test core.test_contact_retirement dashboard.tests dashboard.test_search_regressions
workplaces.test_team workplaces.test_invitation_candidates accounts.tests`.
Browser QA: pozostałe Starsze widoki i Przestrzenie, wyszukiwanie bez wycofanych
modułów, 404 starego adresu, desktop/telefon, zwinięte menu i ponowne wejście.

## Pulpity i gadżety

Migracja `dashboard.0012_dashboard_slugs` dopisuje nazwy URL wszystkim istniejącym
pulpitom i unikalność `(workplace, slug)`, zachowując pozostałe dane, PK, gadżety,
gwiazdki i udostępnienia. Duplikaty w jednym Workspace otrzymują kolejne końcówki;
nazwa po edycji nie zmienia już zapisanego adresu. Przed zastosowaniem wykonaj
backup, sprawdź plan, zastosuj migrację i odśwież `layout.js` (wersja zasobu w powłoce).
`dashboard.test_pulpit_urls` sprawdza zwykłe/scoped adresy, stare przekierowania,
query string, aktywne menu, duplikaty/zastrzeżone nazwy/polskie znaki, zachowanie
adresu po edycji, uprawnienia i cofnięcie dostępu, dwa Workspace, dawne POST,
unikalność, dwa równoczesne zapisy oraz migrację z zachowaniem danych.
Uruchamiaj także Dashboard, `core.test_task_integrity.TaskIdentityTests`
i `planner.test_task_calendar`. Browser QA: stary adres → nazwa w URL,
menu/katalog/wyszukiwanie → podgląd → edytor → ustawienia/dostępy → zapis/powrót,
częściowa nawigacja i Wstecz/Dalej, reload, pusty pulpit/wynik, błąd formularza,
duplikaty i desktop/telefon. Osobisty pulpit domyślny zachowuje `default/`.

Weryfikacja adresów (10.10.2026): 228 testów Dashboardu,
`core.test_task_integrity.TaskIdentityTests` i `planner.test_task_calendar` przeszło,
w tym migracja i równoczesny przydział slugów. Playwright/Chrome na osobnej bazie
QA (plugin Browser niedostępny) przy 1440×1000, 1920×1000, 1024×1000 i 390×844
potwierdził przekierowanie z parametrami, aktywne menu, podgląd → edytor →
ustawienia/dostępy → zapis/powrót, zachowanie adresu po zmianie tytułu i reload,
Wstecz/Dalej, częściową nawigację bez przeładowania dokumentu, wyszukiwanie
duplikatu, pusty pulpit/katalog, błąd formularza, filtry zarządzania i widok
domyślny jako referencję. Nie było nieoczekiwanych błędów konsoli ani
przepełnienia strony. Kontrole Django, planu/migracji, składni JS i indeksu
przeszły. Migrację zastosowano lokalnie po backupie; porównanie danych pulpitów,
gadżetów, gwiazdek i dostępów potwierdziło zachowanie wszystkich dotychczasowych
pól. Nie sprawdzano Safari/Firefox ani całego zestawu repozytorium.

Migracja `dashboard.0011_default_dashboard` dodaje znacznik `is_default` oraz
warunkową unikalność użytkownika/Workspace. Zachowuje istniejące pulpity i gadżety;
osobista konfiguracja domyślna powstaje dopiero przy pierwszym wejściu na `/`
lub `/dashboards/default/` (zwykłe/scoped), z jednym „Postępem pracy”.
Przed uruchomieniem tej wersji zastosuj migrację i odśwież `layout.js`.
`dashboard.test_default_pulpit` sprawdza idempotencję inicjalizacji, zapamiętywanie
pustego pulpitu, wspólny edytor, pięć układów, dodawanie/konfigurację/usuwanie
gadżetów, nazwę/opis/dostępy, granice Workspace i użytkownika, prywatność źródeł,
blokadę usunięcia rekordu, unikalność, CSRF i cofnięte członkostwo.
Browser QA: strona główna → Edytuj pulpit → Dodaj gadżet → Zmień układ → Gotowe,
ponowne wejście i reload, konfiguracja, usunięcie wszystkich gadżetów, błąd zapisu,
aktywny link domyślnego pulpitu, częściowa nawigacja i desktop/telefon.

Migracja `dashboard.0007_dashboard_dashboardgadget_and_more` dodaje wyłącznie
konfigurację pulpitów, gadżety i osobiste relacje gwiazdek/udostępnienia.
Nie konwertuje starego Dashboardu ani danych zadań. Wymaga istniejącej migracji
`spaces.0004_issue_types`. Sprawdź plan, zastosuj migrację i odśwież zasoby.
Historyczna migracja `dashboard.0008_dashboardgroup` dodawała osobiste grupy
oraz relacje do pulpitów. `dashboard.0009_remove_dashboard_groups` usuwa ten
mechanizm i jego dwie tabele, zachowując pulpity, gadżety, gwiazdki i dostęp.
Przed zastosowaniem wykonaj backup bazy; migracja odwrotna odtwarza puste tabele,
nie odzyskuje usuniętych grup. Wszystkie migracje są źródłami aplikacji
i muszą być wersjonowane.

Testy: `dashboard.test_pulpits`, `dashboard.test_pulpit_editor`, `dashboard.test_pulpit_catalog`, `dashboard.test_pulpit_navigation`, `dashboard.test_pulpit_group_retirement`, `dashboard.test_pulpit_management`, `spaces.test_management`, `spaces.test_navigation`, `dashboard.test_home`,
`dashboard.test_for_you`, `dashboard.test_search_regressions`,
`core.test_task_integrity`, `planner.test_task_calendar` oraz `workplaces`.
Nowe testy obejmują właściciela/twórcę, dwa Workspace, prywatność rodziców,
cofnięcie dostępu, tylko odczyt, formularze źródeł/udostępniania, gwiazdki,
wycofanie kopiowania, usuwanie, CSRF i walidację układu/rewizji. Tworzenie przez katalog
i zarządzanie zaczyna od zera gadżetów; ponowne wejście zachowuje pusty stan,
a ręczne dodanie pierwszego gadżetu usuwa komunikat pustego pulpitu.
Wycofanie kopiowania nie wymaga migracji. Testy w `dashboard.test_pulpits`
sprawdzają też katalog bez zakładek: wszystkie dostępne pulpity bez gwiazdki,
ignorowanie dawnych wartości `tab`, granice dostępu i Workspace, filtry,
paginację, gwiazdkę oraz style i akcję czyszczenia pustych wyników.
Browser QA: filtr widoczności i wyszukiwanie bez zakładek, pusty wynik/czyszczenie,
zwykły/scoped URL, ponowne wejście przez częściową nawigację i desktop/telefon.
Testy wycofania kopiowania w `dashboard.test_pulpits`
sprawdzają 404 dawnych adresów GET/POST (zwykłe/scoped, katalog/zarządzanie)
dla twórcy i członka, zachowanie konfiguracji, gadżetów, dostępu i gwiazdek,
brak akcji kopiowania w menu oraz brak pustego menu w przeglądzie odbiorcy.
Katalog `GADGET_CATALOG` i `AVAILABLE_GADGET_KINDS` w `backend/dashboard/pulpits.py`
obejmują wyłącznie „Postęp pracy”. Migracja `dashboard.0010_work_progress_gadget`
zastępuje stare gadżety jedną kartą na niepusty pulpit, w miejscu pierwszej starej
karty; resetuje jej tytuł/źródło/przypisanie i usuwa pozostałe stare karty.
Zachowuje puste pulpity, istniejące karty `progress`, układ, dostępy i gwiazdki.
Usuwa nieużywane pola status/group_by/limit oraz zwiększa rewizję zmienionych
pulpitów. Przed zastosowaniem wykonaj backup bazy i `manage.py migrate`.
Cofnięcie migracji odtwarza pola, ale nie odzyskuje dawnych konfiguracji;
przywrócenie starszej wersji wymaga backupu.
`dashboard.test_work_progress_migration` sprawdza zastąpienie, dwa Workspace,
pusty pulpit, istniejący postęp, idempotencję i zachowanie danych zadań.
Testy gadżetu obejmują puste dane, pięć statusów, ponowne otwarcie,
pełne agregacje ponad 24 zadania, wykluczenie podzadań, filtry źródła/przypisania
i prywatność projektu/grupy/zadania. Testy sprawdzają też
dodawanie i konfigurację postępu, odrzucenie nieznanego i wycofanych rodzajów
oraz zachowanie zapisanego rekordu po błędzie, także przez scoped URL i modal.
`dashboard.test_pulpit_catalog` obejmuje szybkie dodawanie, rozmieszczenie
w kolumnach, rzeczywisty HTML, rewizję i duplikaty, limit, błędny JSON, CSRF,
twórcę i granice Workspace oraz zachowanie filtrów zarządzania.

Testy pulpitów sprawdzają również brak kontrolek edycji w przeglądzie twórcy,
osobny edytor z kontrolą dostępu GET, zwykłe/scoped adresy, tło bezpośrednich
formularzy gadżetów, powrót do edytora i zachowanie filtrów zarządzania.
Pięć układów pustego pulpitu nie tworzy gadżetów.
`dashboard.test_pulpit_editor` sprawdza wejście z nazwy katalogu do gadżetów,
osobne menu trzech sekcji, formularze ustawień/dostępu zapisujące tylko własne
pola, walidację, twórcę, Workspace, CSRF, zachowanie filtrów oraz tło modali.
Zmiana menu i rozdzielenie formularzy nie wymagają migracji.

Katalog Pulpitów: `dashboard.test_pulpits` sprawdza filtr widoczności
w zwykłym/scoped URL, dostęp członka, cofnięcie udostępnienia, obcy Workspace
oraz zachowanie wyszukiwania/widoczności przy paginacji po 30 pozycji,
zmianie zakładki i zapisie osobistej gwiazdki. W browser QA porównaj katalog
z Przestrzeniami: wiersze i odstępy, checkboxy pojedyncze/wszystkie/częściowe,
menu z trzema paskami, Escape/fokus, gwiazdkę, wyszukiwanie i filtr, paginację,
pusty wynik, szerokości kolumn, desktop/telefon oraz ponowne wejście.

Browser QA: pusty katalog, utworzenie, przegląd → edytor → przegląd,
osobne menu edycji, pięć układów w edytorze gadżetów i przeładowanie,
przeciąganie oraz przenoszenie klawiaturą, konfiguracja gadżetu, wybrana osoba,
gwiazdki i brak akcji kopiowania, błędy formularza/sieci/konfliktu, Escape/fokus,
ponowne wejście z Dashboardu, zwykły/scoped URL oraz desktop/telefon.
Sprawdź zachowanie dokumentu podczas częściowej nawigacji do `/<pk>/gadgets/`
i `/manage/<pk>/gadgets/`, aktywne pozycje menu, błędy zapisu i region live, wyłączone
kierunki przenoszenia, powrót do edytora po dodaniu/edycji/usunięciu i przywrócenie
układu/selecta po konflikcie rewizji. Przegląd nie może pokazywać kontrolek
gadżetów również twórcy; odbiorca nie ma dostępu do URL edytora.
Ikony i ilustracje: dropdown rodzaju z ikoną, podgląd „Postępu pracy”,
pusta karta z 0% i pięcioma zerami, miniatura wszystkich pięciu układów i jej przywrócenie
po błędzie. Sprawdź formularz po walidacji, częściowej nawigacji i ponownym
otwarciu, a także modal z dostępną stopką na telefonie.
Panel „Więcej pulpitów”: `dashboard.test_pulpit_navigation` sprawdza
wyszukiwanie po nazwie/opisie, limit, escapowanie, logowanie/GET, zwykłe/scoped
adresy, Workspace, cofnięcie udostępnienia i członkostwa. W browser QA porównaj
panel z „Więcej przestrzeni”: otwarcie, wyszukiwanie, brak wyników/błąd,
link do wszystkich pulpitów zachowujący frazę, wybór wyniku, Escape/fokus,
kliknięcie poza panelem, zwinięte menu, telefon i częściową nawigację.

Nawigacja: gwiazdki z katalogu i menu wiersza, osobiste ostatnie,
cofnięcie dostępu, limit skrótów, plus w nagłówku, zwinięta sekcja
i flyout całego menu. `dashboard.test_pulpit_group_retirement` sprawdza
404 dawnych endpointów GET/POST w obu zakresach URL, brak dawnych akcji,
ignorowanie parametru `group` bez poszerzania dostępu oraz migrację
z istniejącymi grupami, zachowującą konfigurację pulpitów i gadżetów.
Zarządzanie: własne pulpity dwóch osób/dwóch Workspace, osobne menu, zwykły
i scoped URL, pusty stan, filtry/paginacja, tworzenie/edycja/usunięcie,
modal tworzenia, osobna strona edycji, walidacja ze szkicem, powrót
z filtrami oraz Wstecz/Dalej/reload. Edycja: wejście z nazwy/menu katalogu,
menu otwartego pulpitu i menu bocznego, zapis/anulowanie, „Wybrane osoby”,
zmiana liczby kolumn, ochrona szkicu przy wyjściu oraz ponowne wejście.
Regresja usuwania: utwórz i otwórz pulpit → „Zarządzaj pulpitami” → usuń go
→ link powrotu otwiera wszystkie pulpity. Sprawdź ostatni pulpit, usunięcie
innego pulpitu (zachowanie celu), filtry katalogu, zagnieżdżony powrót edytora,
zwykły/scoped adres, anulowanie i błąd usuwania, reload oraz Wstecz/Dalej.
Usunięcie w innej karcie i stary cel w historii powinny użyć domyślnego
powrotu bez opuszczania powłoki aplikacji. `dashboard.test_pulpit_management`
sprawdza adresy unieważniane po udanym usunięciu oraz brak unieważnienia
przy odmowie dostępu; samo działanie linku wymaga browser QA.
Menu wybranego pulpitu: lista → nazwa → Gadżety i układ → Dostępy → Ustawienia,
brak poziomych zakładek i ogólnego menu zarządzania w edytorze, nazwa/aktywna
pozycja po zmianie pulpitu, przeładowanie i Wstecz/Dalej. Sprawdź zapis obu
formularzy, ich izolację, walidację ze szkicem, ochronę zmian przy przełączaniu
sekcji, powrót z filtrami po częściowej nawigacji i zwykłym POST, menu zwinięte
oraz telefon. Zapis ustawień nie może zmieniać uprawnień ani układu.
Porównaj w przeglądarce tabelę z „Pulpity”: te same kolumny, ikony, szerokości,
checkboxy i menu po lewej; sprawdź opis i gwiazdkę w menu wiersza.
Wyszukiwarka i paginacja są po prawej, a filtry zarządzania po lewej.
Sprawdź zaznaczenie wszystkich/części wierszy oraz niezależny zapis szerokości
kolumn katalogu i zarządzania w zwykłym/scoped URL.
Wycofanie grup: menu katalogu, wiersza, pulpitu i zarządzania bez akcji grup,
404 starego adresu, zachowanie powrotu, historii/reload, gwiazdek i gadżetów
na desktopie oraz telefonie.
Testuj na oddzielnej bazie; nie dodawaj danych QA do Workspace użytkowników.


Katalog gadżetów: w browser QA sprawdź tworzenie pustego pulpitu, otwarcie
panelu, kategorie i wyszukiwanie (także bez polskich znaków), brak wyników/reset,
kilka kolejnych dodań „Postępu pracy” bez nawigacji, konfigurację i powrót z otwartym katalogiem,
reload, zamknięcie/Escape/fokus, wszystkie miniatury układu, przeciąganie oraz
menu przenoszenia nowych gadżetów. Sprawdź błąd sieci/ponowienie, konflikt dwóch
okien, limit 24 oraz brak pozornie dodanych kart. Przegląd zachowuje ilustrację
pustego pulpitu i brak kontrolek gadżetów. Desktop, tablet z dokowanym katalogiem
oraz telefon z katalogiem nad siatką muszą zachować własne przewijanie i dostęp
do przycisków. Referencją powłoki i kontrolek jest „Zarządzaj przestrzeniami”.

## Usunięcie globalnego katalogu Tagów

Globalny katalog „Tagi” w Starszych widokach jest usunięty. Testy
`tasks.test_tag_retirement` sprawdzają 404 dla zwykłych i scoped adresów oraz
akcji CRUD/notatek, brak menu i modali, odrzucenie dawnego skrótu Favorites,
wyszukiwanie, puste pickery zadań bez przestrzeni, brak katalogu w adminie
oraz brak backfillu dawnych tagów. Historyczne rekordy
i relacje pozostają w bazie. Zmiana nie wymaga dodatkowej migracji ponad
`0064_space_tags` i `0065_space_tag_data`. Weryfikuj również `spaces.test_tags`,
`tasks.tests`, `workplaces.tests`, wyszukiwanie Dashboardu, wycofanie Kanbana
i brak tagów w Dysku/Dokumentach. Browser QA: Starsze widoki, 404 starego
katalogu, tagi przestrzeni, ekran referencyjny, częściowa nawigacja i 390px.

Weryfikacja 9.10.2026: końcowy zestaw 317 testów zakończył się 307 poprawnymi
wynikami i 10 wcześniejszymi błędami/asercjami nawigacji, podzadania i pulpitu.
Te same 10 przypadków odtworzono na niezmienionym HEAD w osobnej bazie.
Wszystkie 8 testów wycofania oraz testy tagów przestrzeni przeszły. Wcześniejszy
zestaw 36 testów funkcji, formularzy i wyszukiwania również przeszedł.
Pełny powtórny przebieg na świeżej bazie potrzebował wyłączenia PostgreSQL JIT
wyłącznie w tymczasowej konfiguracji testowej; standardowy przebieg zatrzymał
długo wykonywany SELECT podsumowania przestrzeni. Konfiguracja aplikacji
nie została zmieniona. Playwright/Chrome (plugin Browser niedostępny),
1440×1000 i 390×844, potwierdził brak starego menu i Favorites, 404 zwykłego
i scoped katalogu, brak modali Zadań, dodanie tagu przestrzeni, Escape, pusty
stan, częściową nawigację, powrót i reload bez błędów JavaScript.
Kontrole Django, zgodności migracji, składni, linków dokumentacji, indeksu
i `git diff --check` przeszły. Nie uruchamiano całego repozytorium.

## Weryfikacja niezależnych zadań przestrzeni (10.10.2026)

Końcowy zestaw 329 testów `spaces`, Core (tożsamość/status/pliki),
Dashboard (Dla ciebie, podsumowanie, pulpity, wyszukiwanie), zgodności Kanbana,
wycofania tagów i edycji lokalizacji Tasks oraz dostępu Workspace przeszedł.
Po ostatniej poprawce publikacji przestrzeni ponownie przeszły 22 testy
`spaces.test_independent_tasks`, w tym import historii/pliku/uprawnień,
trwałe cofanie udostępnień i zachowanie prywatnych zadań przy publikacji.

Pełny przebieg 1163 testów miał 26 nieudanych asercji i 9 błędów.
Porównanie z osobnym przebiegiem niezmienionego HEAD (1145 testów,
26 asercji i 10 błędów) potwierdziło 34 wspólne problemy z identycznymi
komunikatami: głównie historyczna nawigacja/styl, wycofany katalog tagów,
Dysk oraz dawne testy podzadań. Dodatkowy test pulpitu Workspace używał
starszych Tasks; jego dane dostosowano do `SpaceTask` i ponownie sprawdzono
w końcowym zestawie 329 testów. Pełny zestaw repozytorium pozostaje czerwony.

Playwright/Chrome przy 1440×1000, 1024×1000 i 390×844 potwierdził:
lista → szczegóły w przestrzeni → zapis/reload → komentarz AJAX → powrót
z filtrami → ponowne wejście → historia/podzadanie. Sprawdzono pusty wynik,
walidację wymaganego tytułu w przeglądarce i błąd HTTP 400 serwera,
brak zapisu obserwatora, pulpit referencyjny oraz brak przepełnienia telefonu.
Zrzuty potwierdziły wspólną powłokę i zakładki przestrzeni; nie było
nieoczekiwanych błędów konsoli. Plugin Browser był niedostępny; użyto
istniejącego Playwright i Chrome, bez instalowania zależności. Safari/Firefox
nie były sprawdzane. Podany stary link na `127.0.0.1:8000` przekierowuje
po kontroli dostępu do `space/scrum-szablon/tasks/SZ-6/?view=list`.

Migracje `spaces.0006`, `tasks.0066` i `spaces.0007` zastosowano lokalnie
po pełnym backupie PostgreSQL. Porównanie potwierdziło zachowanie adresów,
kluczy, liczników i planowania. Kontrole Django, zgodności migracji, składni JS,
linków dokumentacji, indeksu kodu oraz `git diff --check` przeszły.
Ten wcześniejszy etap nie obejmował przypomnień ani wzmianek. Ich aktualną
obsługę oraz procedurę przywrócenia opisuje [SPACES.md](SPACES.md).

## Układ szczegółów zadania przestrzeni (10.10.2026)

`spaces/task_detail.html` korzysta z tej samej powłoki szczegółów co
referencyjny `tasks/view_task.html`: jeden nagłówek z powrotem i zapisem,
zakładki i edytor/czat po lewej, właściwości po prawej. Adres pozostaje
w przestrzeni, a jej pozycja w głównej nawigacji pozostaje aktywna.
Panel odwzorowuje pełne właściwości starszego ekranu, w tym kategorię
i przypomnienie zapisane we własnym modelu. Planowanie pozostaje w edycji
przestrzeni; szczegóły zachowują jego wartości.

165 testów `spaces core.test_file_lifecycle` przeszło. Po końcowej poprawce
zachowania szkicu przy błędnym pliku ponownie przeszły 24 testy
`spaces.test_independent_tasks`. Dodane przypadki sprawdzają wspólny zapis
załączników/danych/planowania, chronione pobieranie i brak częściowego zapisu
przy błędnym pliku lub formularzu. Pliki tych testów są w tymczasowym storage.
Nie ponawiano całego zestawu repozytorium; jego wcześniejsze problemy opisano powyżej.

Playwright z istniejącym Chrome (plugin Browser niedostępny) na osobnej bazie
QA i magazynie plików potwierdził przy 1440×1000, 1024×1000 i 390×844:
lista → otwarcie → wybór/usunięcie oczekujących plików → zmiana danych,
statusu i planowania → zapis → chronione pobranie/reload → komentarz AJAX
→ powrót → ponowne wejście → historia/podzadanie. „Zapisz” pozostaje
nieaktywny dla niezmienionego formularza oraz po usunięciu ostatniego wybranego
pliku. Sprawdzono kopiowanie klucza, pusty wynik, walidację przeglądarki,
HTTP 400 serwera i brak zapisu u obserwatora. Ekran referencyjny szczegółów
starszego zadania oraz pulpit zachowują działanie. Przy 1920×1080 sprawdzono
również wskazany adres na porcie 8000 i geometrię względem wzorca.
Nie było pustej strony, nakładki błędu, nieoczekiwanych błędów konsoli
ani przepełnienia telefonu. Celowo błędny POST zwrócił oczekiwany HTTP 400.
Safari/Firefox nie były sprawdzane. Kontrole Django, składni JS, linków
zmienionej dokumentacji, indeksu kodu i `git diff --check` przeszły.

## Pełna zgodność ekranu zadań przestrzeni

Po backupie zastosuj `spaces.0008`, `spaces.0009` i `dashboard.0013`. Sprawdź obecność nowych
migracji w Git. `spaces.test_task_detail_parity` obejmuje pięć paneli,
kategorię/przypomnienie, widoczność i prywatnych potomków, modal podzadania,
zbiorcze usuwanie, modal czasu z dodawaniem/edycją/usuwaniem, paginację,
udostępnianie/role, granice administratora, nieprawidłowe ID i powiadomienia.
Wspólna walidacja czasu jest w `backend/core/work_logs.py`; testuj także starsze
`spaces.test_work_logs`, `dashboard.test_notifications`, `test_reminders`,
`test_collaboration` i `core.test_file_lifecycle`.

Browser QA musi obejmować wszystkie pięć zakładek, puste i wypełnione panele,
modale, błędy, fokus/Escape, zachowanie szkicu przy przełączaniu, zapis,
ponowne wejście, obserwatora i częściową nawigację. Porównaj ze starszym
zadaniem w tej samej szerokości oraz sprawdź tablet i telefon. Używaj
oddzielnej bazy i storage QA; sam pomiar zakładki „Główna” nie potwierdza
zgodności całego ekranu.

Weryfikacja 10.10.2026: przeszło 255 testów powiązanych modułów, następnie
120 testów po zmianach wspólnych komponentów i migracji dat członkostwa.
Końcowe 15 testów zgodności potwierdziło także daty/nazwy w historii oraz
zarządzanie zwykłymi członkami przez administratora bez podnoszenia ich roli
do administratora. Nie ponawiano pełnego zestawu repozytorium; jego wcześniejsze
problemy są opisane powyżej.

Playwright z Chrome (plugin Browser niedostępny) sprawdził wszystkie pięć
zakładek przy 1920×1080, 1024×900 i 390×900. Porównanie położenia, szerokości,
fontów, kolorów, obramowań i odstępów wspólnej powłoki oraz głównych elementów
każdego panelu ze starszym zadaniem przy 1920×1080 nie wykazało różnic powyżej
1px. Sprawdzono puste i wypełnione panele, zapis kategorii/przypomnienia,
zachowanie szkicu, tworzenie/usuwanie podzadania, dodawanie/edycję/usuwanie
czasu, błąd zerowego czasu, udostępnianie/zmianę roli/odebranie dostępu
i widok obserwatora. Podany adres lokalny otwiera wszystkie pięć paneli
przez przekierowanie do szczegółów w przestrzeni, bez błędów konsoli.
Sprawdzono także wybór/usunięcie oczekujących plików, komentarz AJAX ze
wzmianką i zdjęciem, prywatne pobieranie oraz obraz inline, fokus/Escape
modali, powrót/ponowne wejście i inicjalizację po nawigacji częściowej.
Po weryfikacji usunięto bazę i pliki QA oraz tymczasową sesję używaną
do odczytu lokalnego ekranu. Wcześniejsze dane planowania, adresy i treści
importowanych zadań pozostały zachowane.
Safari i Firefox nie były sprawdzane.

## Kontynuacja migracji React (16.10.2026)

Aktualny zakres ekranów, API, budowanie i pozostałe moduły:
[FRONTEND.md](FRONTEND.md). Przed uruchomieniem testów renderujących te ekrany
zbuduj `frontend/app`. Wspólna powłoka Django i nieprzeniesione moduły nadal
są potrzebne; nie usuwaj starszych skryptów ani szablonów przy okazji migracji.

Wykonany zestaw `core.test_frontend spaces resources planner
 dashboard.test_for_you core.test_file_lifecycle` objął 319 testów:
317 przeszło. Dwie asercje `spaces.test_issue_types` oczekują HTTP 302
po AJAX zapisie szczegółów, choć obecny widok zwraca JSON 200. Obie awarie
odtworzono na osobnej kopii niezmienionego HEAD. Nowe testy API uruchomiono
też osobno; po dodaniu ochrony starszych nagłówków AJAX przeszło 20 testów.
Pełny zestaw wszystkich aplikacji nie był ponawiany; znane starsze problemy
pozostają opisane we wcześniejszych rozdziałach.

Browser plugin był niedostępny, dlatego użyto Playwright z lokalnym Chrome,
oddzielną bazą testową, kontami i storage QA. Sprawdzono 1440×1000,
1024×900 i 390×900: katalog/formularze, zapis, błędy, ponowne wejście,
częściową nawigację, Back/Forward, filtry i kolumny Zasobów, cztery widoki
Kalendarza, Dla ciebie/Ustawienia, Przestrzenie/listę/tablicę/backlog,
przeciąganie kart, zbiorcze planowanie i rozpoczęcie sprintu, konfigurację,
Zespoły i ochronę ostatniego administratora. Dla zadań: automatyczny zapis,
komentarz ze wzmianką, prywatny upload/download/usunięcie pliku, podzadania,
walidację/dodawanie/edycję czasu, historię, wyszukiwanie osób, udostępnianie,
role, obserwatora i odebranie dostępu. Porównano ekran zadania z dotychczasowym
szablonem; nie wykonywano automatycznego porównania pikseli całej aplikacji.
Safari i Firefox nie były sprawdzane.

Przy wymianie hashowanego entry pointu `AncoreReactRuntime.dispose()` odłącza
starsze listenery i korzenie Reacta przed rejestracją nowej wersji. Zapobiega
to podwójnemu montowaniu po wdrożeniu i częściowej nawigacji. Zmiany tej
warstwy wymagają sprawdzenia również ponownego załadowania entry pointu
w otwartej karcie. Nie zmieniono modeli ani migracji bazy.

Dodatkowe końcowe sprawdzenia Chrome potwierdziły zachowanie pogrubienia
oraz list w opisie zadania po ponownym wejściu, filtrowanie znaczników/atrybutów
według dotychczasowej listy dozwolonych, szczegółowy komunikat odrzuconego
załącznika i usuwanie oczekującego pliku. Sprawdzono przeniesienie wybranego
dnia z miesiąca do widoku dziennego, linię bieżącej godziny oraz wyświetlanie
czasu pracy w Europe/Warsaw przy strefie przeglądarki America/Los_Angeles.
Symulacja trzykrotnego zastąpienia entry pointu nie tworzyła dodatkowych
korzeni ani modali. Poprawka wspólnego otwierania okna respektuje fokus,
który użytkownik zdążył już przenieść do innego pola; regresje Kalendarza
i Zasobów z szybkim wypełnianiem formularzy przeszły ponownie.

## Migracja Tagów i Filtrów do Reacta (16.10.2026)

Tagi Przestrzeni oraz katalog, zarządzanie i wyniki Filtrów używają
`frontend/app/src/tags`, `src/filters`, `backend/spaces/tag_frontend.py`
i `backend/dashboard/filter_frontend.py`. API nadal deleguje do `tag_action`
i `filter_views`, zachowując właściciela Workspace, faktycznego autora,
ACL Przestrzeni/zadań, transakcje, rewizje oraz ograniczone opcje formularzy.
Nie zmieniono modeli, migracji ani zależności.

Wykonany końcowy zestaw:

```sh
.venv/bin/python manage.py test core.test_filter_frontend core.test_frontend \
  dashboard.test_filters spaces.test_tags dashboard.test_pulpits resources --noinput
```

Na osobnej bazie PostgreSQL przeszło **139/139 testów**, w tym 12 nowych
`core.test_filter_frontend`. Sprawdzają JSON i bootstrap zwykłych/scoped adresów,
ACL wyników/opcji, wyszukiwanie wielowartościowe i paginację, CRUD i udostępnianie,
autora notatek, rewizje, atomowe usuwanie wielu tagów, obserwatora, CSRF
i usuwanie starszych nagłówków AJAX. Szerszy przebieg 147 testów miał 143 sukcesy;
trzy awarie i jeden błąd w `tasks.test_tag_retirement` odtworzono identycznie
na tymczasowej kopii niezmienionego HEAD i osobnej bazie. Testy oczekują dawnych
ekranów Tasks (200 zamiast obecnych 302/409) oraz usuniętej trasy admina
`tasks_task_change`. Nie przywracano wycofanych ekranów.

Plugin Browser był niedostępny; użyto Playwright z lokalnym Chrome,
fikcyjnymi kontami oraz oddzielną bazą i storage QA. Sprawdzono 1440×900/1000,
1024×900 i 390×900. Tagi: katalog, filtry, sortowanie, paginację/rozmiar strony,
wyszukiwanie i pusty wynik, CRUD, duplikat/kolor, informacje, notatki
z dodawaniem/edycją/usuwaniem i ponownym wejściem, zaznaczanie/usuwanie zbiorcze,
kolumny i ich trwałość/zmianę szerokości klawiaturą oraz Escape/porzucenie szkicu.
Filtry: wybory wielokrotne, grupy statusów/zaznaczenie/zwijanie, zaawansowane
zapytanie i błędną składnię, ochronę bezstratnego przełączenia trybu, zapis,
kopię, edycję, zarządzanie z zachowaniem URL, gwiazdki, strony, udostępnienie,
odbiorcę bez prywatnego zadania oraz obserwatora tagów bez akcji zapisu.
Bezpośredni adres modalu zachowuje kryteria przy anulowaniu. Konflikt dwóch
okien nie nadpisuje nowszej definicji i zachowuje starszy szkic. Błąd sieci
zachowuje pola i pozwala ponowić zapis. Usunięcie filtra wymaga potwierdzenia
i zachowuje kontekst zarządzania.

Porównano ekran tagów, katalog i wyniki Filtrów oraz modal tagu z zachowanymi
szablonami Django przy 1440×1000; nie wykonywano automatycznego porównania pikseli
całej aplikacji. Sprawdzono częściową nawigację, Wstecz/Dalej, ponowne otwieranie
modali, brak pustej strony/nakładki błędu, brak przepełnienia dokumentu
i brak nieoczekiwanych ostrzeżeń/błędów konsoli. Pełna regresja przeglądarkowa
Zasobów po wydzieleniu `shared/DirectoryColumns.tsx` także przeszła.
Safari/Firefox ani pełny zestaw repozytorium nie były sprawdzane.

Kontrole wykryły i objęły poprawkami obramowania pól wyszukiwania, widoczność
checkboxów i rozmiary ikon tagów, zagnieżdżone menu, etykietę zapisu po walidacji,
natywne zdarzenie widoczności dla pól DOM i inicjalizację ujawnionego pickera
osób. Zapis czeka na zakończenie częściowej nawigacji przed odblokowaniem
kolejnej akcji. Budowanie/typecheck, Prettier, kontrola Django, składnia JS,
linki dokumentacji, indeks kodu i `git diff --check` przeszły.


## Migracja Pulpitów do Reacta (16.10.2026)

Katalog, zarządzanie, pulpit domyślny, przegląd, ustawienia/dostępy oraz edytor
używają `frontend/app/src/pulpits/` i `backend/dashboard/pulpit_frontend.py`.
Oryginalne formularze i widoki zachowują ACL, autora, transakcje i rewizje.
Strukturalny JSON dopuszczono wyłącznie dla `arrange` i `gadget_quick_add`;
pozostałe operacje zachowują kontrakt formularza. Nowy gadżet odczytuje bieżące
`SpaceTask` tak samo jak pełny przegląd, także przed odświeżeniem. Usunięcie
przekazuje unieważnione adresy powrotu do istniejącej powłoki.
Nie zmieniono modeli, migracji ani zależności.

Wykonany końcowy zestaw:

```sh
.venv/bin/python manage.py test core.test_pulpit_frontend dashboard.test_pulpits \
  dashboard.test_pulpit_editor dashboard.test_pulpit_catalog \
  dashboard.test_pulpit_management dashboard.test_pulpit_urls \
  dashboard.test_default_pulpit dashboard.test_pulpit_navigation \
  dashboard.test_work_progress_migration dashboard.test_pulpit_group_retirement \
  core.test_frontend core.test_filter_frontend resources --noinput
```

Na osobnej bazie PostgreSQL przeszły **164/164 testy**, w tym 13 nowych testów
kontraktu React Pulpitów. Obejmują zwykłe/scoped adresy, inicjalizację domyślnego
pulpitu, uprawnienia twórcy, prywatne źródła i liczniki, oddzielne formularze,
relacje dozwolonych osób/Przestrzeni, walidację, autora, bieżące dane zadań,
kompletny układ i atomowe odrzucenie błędnych ID, rewizje, limit, gwiazdki,
paginację, unieważnienie powrotów, starsze nagłówki AJAX, CSRF i sesję.
Pełny zestaw repozytorium nie był ponawiany.


Plugin Browser był niedostępny; użyto Playwright z lokalnym Chrome,
oddzielną bazą, fikcyjnymi kontami i storage QA. Sprawdzono 1440×1000/900,
1024×900 i 390×900: katalog/zarządzanie, wyszukiwanie i puste wyniki,
paginację, zaznaczenie i stan częściowy, gwiazdki, tworzenie z walidacją
odbiorców, zachowanie szkicu, ustawienia/dostępy i ponowne wejście.
Edytor: pięć układów, scalanie usuwanych kolumn, przenoszenie menu i natywnym
uchwytem pomiędzy kolumnami, konfigurację/usuwanie gadżetów, szybkie dodawanie
z bieżącymi licznikami, szukanie bez polskich znaków, kategorie i trwałość
katalogu oraz limit 24. Odbiorca nie ma kontrolek edycji, liczy własne przypisania
i nie widzi nazwy/liczników prywatnego źródła. Usunięcie Pulpitu zachowuje
kontekst zarządzania. Pulpit domyślny nie ma akcji usuwania, a usunięte gadżety
nie wracają po przeładowaniu.

Bezpośrednie adresy tworzenia i gadżetu otwierają pojedynczy modal nad ekranem;
anulowanie w zarządzaniu zachowuje parametry. Sprawdzono Escape/fokus,
potwierdzenie porzucenia szkicu, częściową nawigację i Wstecz/Dalej.
Symulacja HTTP 503 zachowuje formularz i pozwala ponowić zapis, a błąd układu
cofa zmianę. Dwa okna potwierdziły HTTP 409 i odświeżenie nowszej rewizji;
nawigacja czeka na zapis. Nie stwierdzono pustych ekranów, nakładki błędu,
przepełnienia dokumentu ani nieoczekiwanych błędów/ostrzeżeń konsoli.

Porównano katalog, przegląd, edytor, ustawienia/dostępy i modal tworzenia
z zachowanymi szablonami Django. Poprawiono rozmiar ikon, semantyczną nazwę
filtra widoczności (zachowuje ikony opcji), łamanie opisu i geometrię pól.
Zrzuty porównywano po skończeniu animacji modalu; nie wykonano automatycznego
porównania pikseli całej aplikacji. Pełna regresja Chrome Zasobów po zmianach
wspólnych komponentów przeszła. Budowanie/typecheck, Prettier, kontrola Django,
składnia JS, linki dokumentacji, indeks i `git diff --check` przeszły.
Safari i Firefox nie były sprawdzane.

## Migracja Dysku i Dokumentów do Reacta (16.10.2026)

`backend/documents/frontend.py` oraz `frontend/app/src/documents/` przenoszą katalogi,
listy/kafelki, formularze, upload, podglądy, przenoszenie, gwiazdki, kosz,
szablony, tekstowy edytor Ancore i powłokę pełnych edytorów. Django zachowuje
formularze, sesję/CSRF, zakres właściciela Workspace, prywatny storage, sygnatury
plików, rewizje, transakcje i kontrolowane źródła/callbacki. Nie zmieniono modeli,
migracji ani zależności. Chronione pobieranie i zapis sceny tablicy pozostają
poza proxy API ekranów. Poprawiono też zgodność rodzaju podglądu ZIP w szablonie
HTML oraz wybór pełnej nawigacji do edytora podczas importu tekstu.

Końcowy zestaw na osobnej bazie PostgreSQL:

```sh
.venv/bin/python manage.py test core.test_document_frontend documents.tests \
  documents.test_office documents.test_previews documents.test_moves \
  documents.test_suite documents.test_office_extras documents.test_drive_office \
  documents.test_colors documents.test_rename documents.test_drive_folders \
  documents.test_office_folders documents.test_folder_icons documents.test_query \
  documents.test_office_query documents.test_library_photos core.test_frontend \
  core.test_filter_frontend core.test_pulpit_frontend --noinput
```

**258 z 259 testów przeszło**, w tym wszystkie 15 nowych testów kontraktu.
Jedyna nieudana asercja, `documents.tests.DocumentLibraryTests.
test_workspace_view_search_tag_pagination_and_actions_keep_workspace_scope`,
oczekuje wycofanych globalnych tagów (`'tags' in groups`). Odtworzono ją
identycznie na osobnej kopii niezmienionego HEAD i osobnej bazie. Nie
przywracano tagów. Nowe testy obejmują zwykłe/scoped adresy, członkostwo i jego
cofnięcie, obcy Workspace, CSRF, metody, niedozwolone endpointy proxy,
bezpieczny bootstrap, filtry/strony, formularze, kolory, upload i limity,
przenoszenie poddrzewa, kosz, prywatne pobranie, podgląd archiwum,
sześć typów dokumentów, niezależne kopie szablonów, czyszczenie HTML,
konflikt tekstu i metadanych oraz zmianę nazwy bez zmiany rewizji/klucza.

Plugin Browser był niedostępny; użyto Playwright z lokalnym Chrome,
fikcyjnymi kontami oraz oddzielną bazą i storage QA. Przy 1440×1000/900,
1024×900 i 390×900 sprawdzono katalogi i modale, zaznaczenia, filtry,
sortowanie, paginację, listę/kafelki i trwałość, pusty wynik, tworzenie dysku
oraz folderu, kolory, duplikat z zachowaniem danych, rzeczywisty upload wielu
plików, podglądy tekstu/obrazu/ZIP, metadane, natywne przeciąganie do folderu,
przenoszenie między dyskami, gwiazdkę, kosz/przywracanie i prywatne pobranie.
Sprawdzono mobilny panel dysków, fokus/Escape, ponowne wejście i brak
przepełnienia dokumentu oraz nieoczekiwanych błędów/ostrzeżeń konsoli.

Dokumenty: utworzenie i kopia szablonu otwierają osobną kartę; blokada popupu
pokazuje link do jednego zapisanego pliku. Zmiana nazwy zachowuje się po reload,
Escape anuluje szkic. Sprawdzono potwierdzenie kosza, rzeczywisty zapis tekstu
Ctrl+S z formatowaniem, reload, HTTP 409 z zachowaniem lokalnej treści i import
TXT. Istniejąca tablica Excalidraw działała w prawdziwym iframe: narysowany
kształt zapisano przez Django i odtworzono po reload.

Pełny serwer ONLYOFFICE nie był uruchamiany w QA. Sprawdzono jego stan
niedostępności oraz protokół powłoki z lokalnym symulatorem `DocEditor`:
automatyczny zapis, HTTP 503, ponowienie, oczekiwanie na rzeczywistą rewizję
Django i unieważnienie sesji. To nie potwierdza edycji formatów biurowych przez
żywą usługę. Testy backendu integracji używają istniejących atrap sieciowych.
Nie sprawdzano Safari/Firefox ani pełnego zestawu repozytorium.

Dodatkowe scenariusze Chrome potwierdziły zachowanie wybranych plików po
błędzie sygnatury i HTTP 503, pojedynczy zapis po ponowieniu, anulowanie/
porzucenie szkicu, zamknięcie bezpośredniego formularza z powrotem do dysku,
zrzut pliku z systemu do wskazanego folderu i brak zmiany źródła po odrzuconym
przeniesieniu. Opóźniona starsza odpowiedź wyszukiwania nie zastępuje nowszego
tekstu, również ze spacjami na brzegach. Konflikt metadanych HTTP 409 zachowuje
nazwę i wybrany plik zastępujący. Menu, częściowa nawigacja Dysk–Zasoby oraz
Wstecz/Dalej działają bez błędów JS. Pełna regresja przeglądarkowa Zasobów
po zmianach wspólnych helperów także przeszła.

Porównano katalogi Dysku/Dokumentów, listę plików, modal dysku oraz oba rodzaje
powłoki edytora z zachowanymi szablonami Django. Poprawki obejmują rozmiary
ikon, osobny wybór liczby wierszy, menu akcji, układ etykiet formularza,
panele filtrów/sortowania i szybkie zamykanie mobilnego panelu dysków.
Nie wykonywano automatycznego porównania pikseli całej aplikacji.
Build/typecheck, Prettier, kontrola Django, składnia Pythona i trzech skryptów
Dokumentów, lokalne linki dokumentacji, aktualność indeksu oraz diff przeszły.

## Migracja zarządzania Workspace do Reacta (16.10.2026)

Katalog, tworzenie, ustawienia, członkowie/role, wysłane i otrzymane zaproszenia
korzystają z `backend/workplaces/frontend.py` i `frontend/app/src/workspaces/`.
Django zachowuje formularze, transakcje, sesję/CSRF, ograniczenia administratora,
walidację plików, stały kod oraz czyszczenie dostępów po odebraniu członkostwa.
Wybrany Workspace do zarządzania nie zmienia aktywnego kontekstu. Picker awatara
jest wyspą DOM używającą istniejącego kadrowania i ilustracji. Nie zmieniono
modeli, migracji ani zależności.

Końcowy celowany zestaw na oddzielnej bazie PostgreSQL przeszedł **45/45**:

```sh
.venv/bin/python manage.py test core.test_workspace_frontend \
  workplaces.test_management workplaces.test_avatars \
  workplaces.test_invitation_candidates --noinput
```

W tym 12 nowych testów kontraktu: bootstrap i JSON, zwykłe/scoped API, wybór
niezależny od aktywnego kontekstu, utworzenie i powtarzające się nazwy, stały
kod, błędy formularzy, ilustracje/zdjęcia i cleanup, podpowiedzi bez HTML,
ponowna walidacja zaproszenia, role i uprawnienia, autor, anulowanie, cofnięcie
dostępu i klucze Office, odpowiedź odbiorcy/wygaśnięcie, kontekst przeglądania
zaproszeń, przełączenie, ostatni własny Workspace, obce identyfikatory,
sesja, CSRF i metody.

Szerszy zestaw obejmował powyższe moduły oraz `workplaces.tests`,
`workplaces.test_team`, `workplaces.test_defaults`, `accounts.test_avatars`,
`core.test_frontend`, `core.test_document_frontend`, `core.test_filter_frontend`
i `core.test_pulpit_frontend`: **158 z 186 testów przeszło**. Wszystkie 26
nieudanych asercji i 2 błędy odtworzono na tymczasowej kopii niezmienionego
HEAD i osobnej bazie. Zgodne były nazwy testów, linie i powody błędów
(z wyjątkiem losowych identyfikatorów w adresach). Dotyczą dawnych Tasks,
Favorites, przekierowań i starych asercji HTML Workspace. Nie przywracano
wycofanych funkcji ani nie zmieniano testów tylko po to, aby były zielone.
Nie uruchamiano testów migracji ani całego repozytorium.

Plugin Browser był niedostępny; użyto Playwright z lokalnym Chrome oraz
fikcyjnymi kontami, oddzielną bazą i storage QA. Katalog → utworzenie →
ustawienia → awatar/kadr → zapis/reload i członkowie → zaproszenie → role →
anulowanie były sprawdzane przez rzeczywiste API. Przeszły zaznaczenia i stan
częściowy, rozmiar strony/strony, wyszukiwanie/pusty wynik, Enter na wierszu,
klawiatura zakładek i zachowanie szkicu, anulowanie/porzucenie zmian,
błąd HTTP 503 i ponowienie bez duplikatu, błędy ustawień i e-maila,
30 ilustracji, anulowanie wyboru, uszkodzony obraz, Escape w kadrze,
powiększenie i zapis zdjęcia. Zmiana nazwy/zdjęcia zachowała kod i aktywny
kontekst. Porównano katalog i okna z zachowanymi szablonami Django.

Przy 1440×1000/900, 1024×900 i 390×900 sprawdzono katalog, tworzenie, Główną,
członków, wysłane i otrzymane zaproszenia, ponowne wejście oraz brak
przepełnienia dokumentu i nieoczekiwanych błędów/ostrzeżeń konsoli.
Właściciel promuje i obniża rolę; administrator nie ma operacji na
administratorach/właścicielu i zaproszeniach administratorów; członek widzi
ustawienia tylko do odczytu i nie dostaje wysłanych zaproszeń. Odebranie dostępu
wymaga potwierdzenia; anulowanie nic nie usuwa, a zatwierdzenie blokuje także
stare żądanie członka. Zagnieżdżone okno zachowuje szkic ustawień rodzica.
Otrzymane zaproszenia przeglądano, odroczono, odrzucono i przyjęto;
rzeczywiste członkostwo oraz jawne przełączenie zmieniły aktywny Workspace.

Poprawiono wspólną kontrolę przycięcia menu w `dropdown-layer.js`: kontenery
za przodkiem `position: fixed` nie przycinają kontrolek modala. Krótkie menu
akcji używa wariantu `Dropdown.searchable=false`. Escape respektuje otwarty
kadr i podpowiedzi osoby. Nowe API widgetu awatara ma inicjalizację per kontener
i sprzątanie przy odmontowaniu. Kontrola Django, build/typy, format, składnia
Pythona/JS, linki dokumentacji, indeks i diff przeszły. Safari/Firefox oraz
pełna regresja wszystkich ekranów nie były sprawdzane.

Dodatkowo sprawdzono błąd odczytu wybranego kontekstu i ponowienie zachowujące
żądaną zakładkę, menu otwierane klawiaturą nad boczną nawigacją oraz Escape
bez zamykania rodzica. Opóźniona odpowiedź podpowiedzi nie zastępuje nowszego
tekstu. Błąd podpowiedzi nadal pozwala wpisać e-mail; wysłanie przy otwartej
liście nie gubi kliknięcia, a walidacja zachowuje tekst i pozwala ponowić zapis.
Regresja wspólnych elementów potwierdziła powrót do pulpitu, częściową nawigację
Wstecz/Dalej, select i zamykanie formularza Zasobów, dotychczasowy picker awatara
konta oraz ponowne wejście i sprzątanie pickera Workspace. Początkowy fokus
modala pomija kontrolki schowanego, zagnieżdżonego pickera i wybiera aktywną
zakładkę lub pole tworzenia.

## Naprawy czterech błędów P2 (17.10.2026)

Autosave zachowuje niezmieniane relacje, których nie można już wybrać;
jawne przypisania nadal podlegają ograniczeniom formularza. Komentarz z tekstem
lub plikami chroni szkic przed opuszczeniem zadania. Zgoda na odrzucenie zmian
dotyczy pojedynczej próby nawigacji. Rejestracja ponawia zapis po kolizji
wygenerowanego ID użytkownika.

Na osobnej bazie PostgreSQL przeszły **182/182 testy**:

```sh
.venv/bin/python manage.py test accounts spaces.test_task_autosave \
  spaces.test_task_detail_parity spaces.test_independent_tasks \
  spaces.test_write_access core.test_frontend core.test_navigation_frontend \
  core.test_shell_frontend --noinput
```

Nowe przypadki obejmują dawnego wykonawcę, prywatnego epika, odłączony zespół,
walidację zależności pól, zwykłe/scoped adresy i JSON API oraz rzeczywistą
równoczesną rejestrację przez HTML i API. Nie rozszerzają dostępnych wyborów
relacji ani nie zmieniają migracji.

Plugin Browser był niedostępny; użyto Playwright i lokalnego Chrome z fikcyjnymi
kontami, osobną bazą i storage. Przy 1440×900 i 390×900 sprawdzono pusty
komentarz, tekst, same pliki, anulowanie/Escape, błąd wysłania i ponowienie,
udane wysłanie oraz ostrzeżenie przed zamknięciem karty. Kontrolowany błąd
nawigacji HTTP 503 zachował szkic i ponownie uruchomił ostrzeżenie dla komentarza
oraz konfiguracji. Zapis konfiguracji, autosave zadania z niedostępnymi
relacjami i ponowne wejście przeszły. Porównano zadanie z profilem użytkownika;
nie wykryto przepełnienia dokumentu ani błędów wykonania JavaScript.

Build TypeScript, formatowanie, kontrola Django, indeks kodu i diff przeszły.
Nie uruchamiano ponownie pełnego zestawu repozytorium; wynik powyżej dotyczy
wymienionych modułów. Safari i Firefox nie były sprawdzane.

## Korekty układu po migracji React (17.10.2026)

`shared/Icon` zachowuje bezpośredni SVG, a selecty toolbarów nie dodają
marginesów technicznych kontenerów. Adapter pól odtwarza etykiety i kontrolki
przez fieldsety, również w formularzach Pulpitów/Filtrów. Backlog i aktywny
sprint zachowują bezpośrednią strukturę grup, odstępy, wysokości list oraz
kolejność metadanych/liczników. Strzałki grup i plusy miesiąca Kalendarza
używają dotychczasowego mechanizmu CSS. Wersje zasobów w szablonach zostały
odświeżone. Nie zmieniono modeli, uprawnień ani zależności.

Wykonano `pnpm --dir frontend/app build` (z TypeScriptem), Prettier,
`manage.py check`, kontrolę lokalnych linków UI/Frontend, indeksu i diffu.
Na osobnej bazie PostgreSQL przeszły **50/50 istniejących testów**:

```sh
.venv/bin/python manage.py test core.test_frontend \
  core.test_navigation_frontend core.test_shell_frontend --noinput
```

Plugin Browser był niedostępny; wykorzystano istniejący Playwright i Chrome,
osobną bazę, storage oraz fikcyjne dane. Układ 15 ekranów sprawdzono przy
1440, 1280, 1100, 1024, 768 i 390px; zrzuty porównano także z zachowanymi
szablonami listy Przestrzeni i szczegółów zadania. Kontrole adresu, tytułu,
treści, konsoli oraz geometrii nie wykazały pustych ekranów, nakładki błędu,
przepełnienia dokumentu ani nakładania sekcji nagłówka.

Sprawdzono modale zadania, sprintu, Zasobów, Pulpitu i Dysku przy 1440, 1100,
1024 i 390px: geometrię pól, selecty i Escape. Przeszły filtrowanie/pusty
wynik, zwijanie, zaznaczanie, pasek zbiorczy, aktywny sprint, przeciąganie
z backlogu do sprintu i między kolumnami, utworzenie zadania oraz błąd 503
Zasobów z zachowaniem szkicu i rzeczywistym zapisem po ponowieniu. Częściowe
przejścia Zasoby–Kalendarz–Przestrzenie oraz Wstecz/Dalej zachowały dokument
i nie zgłosiły błędów JS. Sprawdzono też mobilny przycisk dodania wydarzenia oraz formularz tagu
i drugi krok kreatora Przestrzeni przy czterech szerokościach, wraz
z potwierdzeniem odrzucenia szkicu.
Zrzuty i skrypty QA pozostały w `/tmp`. Pełny zestaw backendu, Safari,
Firefox, fizyczny ekran dotykowy i produkcyjne ONLYOFFICE nie były sprawdzane.
