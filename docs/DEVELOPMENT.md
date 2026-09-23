# Uruchamianie, weryfikacja i utrzymanie projektu

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

### Istniejące obszary testów

| Moduł | Co sprawdzają istniejące testy |
| --- | --- |
| Accounts | Konto/profil, kadrowanie i walidacja obrazu, obecność, przełączanie kont |
| Workplaces | Wybór i izolacja Workspace, scoped URL, ulubione, zmiany i usuwanie |
| Tasks | Numeracja, hierarchie, CRUD, zakres dostępu, formularze, katalogi, paginacja, zapytania, historia, pliki |
| Osobne testy Tasks | Słowniki źródeł, reguły terminów, nadpisanie reguł per projekt i migracje |
| Kanban | Tablice/kolumny/karty, właściciel, zmiany statusu, katalogi, tagi, pliki |
| Contacts | Osoby, firmy, powiązania z kontami, zakres dostępu i UI szablonów |
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
`kanban.test_deadlines` sprawdza tworzenie, edycję, wyczyszczenie i walidację
terminu karty oraz autora i zawartość historii zmian.
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
