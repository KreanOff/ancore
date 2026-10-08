# Uruchamianie, weryfikacja i utrzymanie projektu

## Uruchomienie przestrzeni i zespołów

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
`spaces.test_management` i regresje katalogu Projektów `tasks.test_directory_tabs`.

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

Źródła: [requirements.txt](../requirements.txt), [settings.py](../ancore/settings.py).

- Python zgodny z używaną wersją Django.
- PostgreSQL; migracje Tasks korzystają z `TrigramExtension` (`pg_trgm`) i GIN.
- Zależności: `django>=5.0`, `psycopg2-binary`, `python-dotenv`, `PyJWT>=2.10,<3`.
- Lokalnie podczas pierwszego przeglądu odczytano Python **3.14.6** i Django
  **6.0.7** z `.venv`. Są to wersje tego środowiska, nie ścisłe wymagania zapisane
  w repozytorium. Zależności nie są przypięte lockfile'em.

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
| `MAX_PROFILE_PHOTO_SIZE` | Limit zdjęcia, domyślnie 5 MiB |
| `MAX_ATTACHMENT_SIZE` | Limit załącznika, domyślnie 10 MiB |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | Próg uploadu w pamięci, domyślnie 5 MiB |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | Limit danych żądania Django, domyślnie 20 MiB |

`TIME_ZONE` to `Europe/Warsaw`, język `pl-pl`, `USE_TZ=True`.
`MEDIA_ROOT` wskazuje `media/`, a `PRIVATE_DOCUMENT_ROOT` wskazuje
`private_documents/`. Te ścieżki są ustawiane w Pythonie, nie przez zmienne
środowiskowe o tych samych nazwach.

Nie nadpisuj istniejącego `.env` podczas wykonywania zwykłego zadania.

## 3. Start nowego środowiska

Komendy wykonuj w katalogu repozytorium. Najpierw skonfiguruj oddzielną bazę
developerską oraz zmienne z poprzedniej sekcji.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate --plan
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Jeśli `.venv` już istnieje, użyj go. Konto można założyć przez rejestrację;
do panelu `/admin/` służy opcjonalnie `manage.py createsuperuser`.
Przy DEBUG=false konfiguracja wymaga prawidłowego klucza/hostów i domyślnie
włącza bezpieczne ciasteczka/HTTPS, co nie pasuje automatycznie do lokalnego HTTP.

Migracje są wersjonowane w Git; `.gitignore` nie wyklucza nowych migracji.
Przed wdrożeniem sprawdź `makemigrations --check --dry-run` i `migrate --plan`.
Migracje Tasks 0047 i Kanban 0034 naprawiają istniejącą numerację oraz dodają
unikalność numerów w Workspace. Na czas tej operacji blokują zapisy w tabeli;
uwzględnij to w oknie wdrożenia dla dużej bazy.

Pełne edytory Dokumentów wymagają dodatkowej konfiguracji opisanej w
[OFFICE.md](OFFICE.md): lokalnego ONLYOFFICE oraz zbudowania zasobów tablicy.
`./scripts/start_office.sh` uruchamia osobny profil Colima/Compose; nie uruchamia
Django. Przy wdrożeniu buduj `frontend/board` przed `collectstatic`.

## 4. Testy

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
.venv/bin/python manage.py test contacts accounts workplaces
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

Zakładki katalogów i osobiste ulubione wymagają migracji Tasks
`0061_directory_favorites`, dodającej dwie relacje many-to-many bez zmiany
dotychczasowych rekordów i dostępu. `0062_task_favorites` dodaje analogiczną
relację `Task.favorited_by`. Testy `tasks.test_directory_tabs` obejmują
kategorie, dziedziczenie grup i zadań, oba warianty URL, filtry/paginację, osobiste ulubione,
obserwatorów, cofnięcie dostępu, obcy Workspace i CSRF. Dawne testy katalogów
z publicznymi danymi wybierają jawnie `tab=public`, ponieważ domyślną zakładką
jest teraz „Prywatne”.

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
zwykły/scoped URL, stabilne linki, zmianę Workspace i cofnięcie dostępu.
Obejmuje też filtry przed paginacją i zachowanie ich w adresach, wyszukiwanie
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
W przeglądarce sprawdź wszystkie zakładki, paginację, wejście w element i powrót,
Dashboard i listę „Wszystkie zadania” jako referencje, nawigację modułów,
kolory/liczniki statusów i zwijanie myszą/klawiaturą (również po ponownym wejściu),
telefon, puste stany oraz błąd sieci.
Przestrzenie w zakładkach „Ulubione” i „Ostatnio oglądane” porównaj z tabelą
„Zarządzaj przestrzeniami”: awatary,
menu (Escape/fokus), otwarcie przestrzeni, gwiazdkę z odświeżeniem zakładki,
filtry, ponowne wejście i poziome przewijanie na telefonie.
Ramkę sekcji „Przestrzenie”, wysokość nagłówka/wierszy i poziome podziały porównaj
z grupami zadań. Sprawdź licznik osobno dla każdej daty, zwijanie nagłówkiem,
Enter/Spacją oraz brak checkboxów i pustej kolumny wyboru w każdej zakładce.
W „Dla ciebie” sprawdź kolejność trzech kolumn danych: Przestrzeń, Klucz, Opis,
brak Rodzaju/Szablonu/Zadań również po odtworzeniu preferencji, wyrównanie komórek
na telefonie i pełny zestaw kolumn w katalogu oraz zarządzaniu. Checkboxy pozostają
na listach zadań, w backlogu i w katalogach przestrzeni poza „Dla ciebie”.

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

`tasks.test_unassigned_creation` sprawdza puste powiązania nowego zadania,
tworzenie bez projektu/grupy (także w pustym Workspace), oba warianty URL,
autora historii, prywatność, wykonawcę, zakończenie, edycję i późniejsze przypisanie
grupy oraz odrzucanie obcych, prywatnych i niespójnych grup.
Regresje katalogu i paginacji są w `tasks.test_directory_tabs`
i `tasks.test_status_pagination`; wspólny skrypt wymaga też sprawdzenia Kanbana w przeglądarce.

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
szablony, statyczne zasoby i spis testów. Nie analizuje semantycznie, czy
wszystkie zdefiniowane funkcje są osiągalne.

Tryb `--check` porównuje bieżący indeks z wynikiem generatora i kończy się
błędem, jeśli indeks wymaga aktualizacji. Nie sprawdza prawdziwości opisów
pisanych ręcznie; te trzeba porównywać z zachowaniem zmienianego kodu.

## 7. Rzeczy ustalone podczas pierwszego przeglądu

To obserwacje stanu na 15.09.2026, nie lista wdrożonych poprawek.

- Drzewo robocze miało zmiany aplikacji przed utworzeniem dokumentacji,
  m.in. cały moduł Documents i jego integrację. Dokumentacja obejmuje ten stan.
- `.gitignore` ignoruje `**/migrations/*.py` z wyjątkami. Odczyt lokalnych
  katalogów wykazał migracje nieśledzone także w starszych modułach.
  Sam `rg --files` respektujący ignore może ich nie pokazać.
- `requirements.txt` nie przypina dokładnych wersji.
- `tasks/views.py` jest pustą pozostałością; routing używa pakietu `tasks/views/`.
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

Nie znaleziono w sprawdzonych plikach konfiguracji CI, Docker/Compose,
osobnego runnera frontendowych testów ani serwisu zadań w tle. Nie oznacza to,
że takie elementy nie istnieją poza repozytorium.

## 8. Wdrożenie

Projekt ma wejścia WSGI i ASGI. Repozytorium nie dokumentuje konkretnego
serwera wdrożenia, domeny, pipeline'u ani backupów; ten opis nie zakłada ich
konfiguracji. `STATIC_ROOT` wskazuje `BASE_DIR / 'staticfiles'` (katalog ignorowany
przez Git). `manage.py collectstatic --noinput` zbiera tam zasoby do serwowania
przez serwer produkcyjny; `--dry-run` pozwala sprawdzić zbieranie bez zapisu.

Publiczne media ogranicz do `profile_photos/`, `company_photos/` i
`workplace_photos/` oraz rozszerzeń JPG/JPEG/PNG/WebP. Nie konfiguruj publicznego
aliasu całego `MEDIA_ROOT`: `task_attachments/` i `kanban_attachments/` są
prywatne i wymagają pobierania przez widoki aplikacji. Wbudowany routing DEBUG
egzekwuje tę listę w `core/media.py`. Dysk/Dokumenty pozostają poza publicznym
storage. Konfiguracja zewnętrznego serwera nie jest częścią repozytorium.

Przy osobnym zadaniu wdrożeniowym ustal konfigurację procesu, statycznych
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
w `documents/blank/`; ich pochodzenie opisuje tamtejszy README. Nie ma nowych
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
bez migracji istniejących wartości. Testy `tasks.test_project_observer` obejmują
blokady zapisu, odczyt, relacje formularzy, role zespołu i mieszane operacje zbiorcze.
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
Testy: `manage.py test contacts dashboard.tests dashboard.test_search_regressions
workplaces.test_team workplaces.test_invitation_candidates accounts.tests`.
Browser QA: pozostałe Starsze widoki i Przestrzenie, wyszukiwanie bez wycofanych
modułów, 404 starego adresu, desktop/telefon, zwinięte menu i ponowne wejście.

## Pulpity i gadżety

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

Testy: `dashboard.test_pulpits`, `dashboard.test_pulpit_editor`, `dashboard.test_pulpit_catalog`, `dashboard.test_pulpit_navigation`, `dashboard.test_pulpit_group_retirement`, `dashboard.test_pulpit_management`, `spaces.test_management`, `spaces.test_navigation`, `dashboard.test_overview`,
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
Katalog `GADGET_CATALOG` i `AVAILABLE_GADGET_KINDS` w `dashboard/pulpits.py`
obejmują pięć istniejących rodzajów; zmiana nie wymaga migracji. Testy sprawdzają
dodawanie i konfigurację wszystkich rodzajów, odrzucenie nieznanego rodzaju
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
Ikony i ilustracje: dropdown rodzaju z ikonami, zmiana podglądu listy/statystyk,
ilustrowane puste gadżety, miniatura wszystkich pięciu układów i jej przywrócenie
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
pięć kolejnych dodań bez nawigacji, konfigurację i powrót z otwartym katalogiem,
reload, zamknięcie/Escape/fokus, wszystkie miniatury układu, przeciąganie oraz
menu przenoszenia nowych gadżetów. Sprawdź błąd sieci/ponowienie, konflikt dwóch
okien, limit 24 oraz brak pozornie dodanych kart. Przegląd zachowuje ilustrację
pustego pulpitu i brak kontrolek gadżetów. Desktop, tablet z dokowanym katalogiem
oraz telefon z katalogiem nad siatką muszą zachować własne przewijanie i dostęp
do przycisków. Referencją powłoki i kontrolek jest „Zarządzaj przestrzeniami”.
