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
| Core | Wspólne mechanizmy i kontrakty UI/uploadu według aktualnych przypadków |
| Core: `test_task_integrity.py`, `test_task_number_migrations.py` | Stabilne PK, dwie karty/Workspace, uprawnienia, kalendarz, powiadomienia, równoczesne tworzenie, unikalność i naprawa istniejących numerów |
| Documents | Dyski, foldery, pliki, kosz, izolacja, modale, paginacja, wyszukiwarka, migracja dysków |
| Documents: `test_suite.py` | Tworzenie czterech typów, osobna karta ONLYOFFICE i katalog po utworzeniu, cel wyników wyszukiwania, podpisane callbacki i źródła, deduplikacja, konflikty tablicy, walidacja OOXML, izolacja właściciela/Workspace, stara sesja po podmianie/koszu |
| Documents: `test_office.py` | Osobny katalog Dokumentów, edycja i konflikt rewizji, formatowanie/eksport DOCX, import, walidacja/rollback plików, dwa konta i Workspace, globalne szukanie |

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
konfiguracji. `STATIC_ROOT` nie jest obecnie ustawiony w `settings.py`, więc
produkcyjnej procedury `collectstatic` nie można uznać za kompletną.

Przy osobnym zadaniu wdrożeniowym ustal konfigurację procesu, statycznych
zasobów, HTTPS, bazy, migracji oraz publicznych/prywatnych plików. Nie zapisuj
sekretów ani danych połączenia do tej dokumentacji.

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

Sprawdzenia funkcji obejmują `manage.py test documents` oraz
`manage.py test workplaces dashboard core`. Siedem starszych testów Workspace/core
ma oczekiwania niezgodne z obecną nawigacją i CSS; ten sam zestaw błędów
odtworzono na kopii wersji sprzed dodania Dokumentów. Nie należy traktować
tego jako zielonego wyniku całego zestawu. Szczegóły aktualnego wykonania
podaje podsumowanie zadania.
