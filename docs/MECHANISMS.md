# Wspólne mechanizmy i przepływy

## 1. Tożsamość, sesja i obecność

Logowanie korzysta z Django Auth oraz `accounts.User`, gdzie `USERNAME_FIELD`
to `email`. Profil i publiczny identyfikator są oddzielone od danych wpisu
`Contact`. Aktualne konto jest w `request.user`.

Rejestracja i profil sprawdzają e-mail bez względu na wielkość liter.
Ograniczenie `accounts_user_email_ci_unique` na `Lower(email)` chroni również
równoczesne zapisy i operacje ORM. Konflikt pomiędzy walidacją a zapisem
wraca jako błąd pola e-mail, bez błędu HTTP 500. Zaproszenia wymagają
jednoznacznego odbiorcy; starsze duplikaty są odrzucane.

Sesja zawiera m.in. `switch_account_user_ids`, `switch_account_auth_hashes`, `active_workplace_id`
i `workspace_url_scope_enabled`. Przełączenie konta wykonuje `auth_login()`
i zachowuje listę uwierzytelnionych kont. Aktywny Workspace jest ponownie
weryfikowany względem bieżącego użytkownika.

Każde dodane konto ma zapisany hash sesyjny Django. Przed przełączeniem
jest on porównywany z aktualnym hashem aktywnego użytkownika docelowego.
Zmiana hasła unieważnia możliwość przełączenia; trzeba ponownie dodać konto
z aktualnym hasłem. Stare sesje zawierające wyłącznie identyfikatory wymagają
ponownego uwierzytelnienia pozostałych kont. Wylogowanie czyści cały przełącznik.

Obecność składa się z:

- [middleware](../accounts/middleware.py), który aktualizuje aktywność przy żądaniach;
- [presence.py](../accounts/presence.py), który obsługuje status i ostatnią aktywność;
- [presence.js](../static/js/presence.js), który wysyła heartbeat do
  `/accounts/presence/ping/` i współdzieli czas aktywności między kartami;
- konfiguracji w `core/base.html` i `ancore/settings.py`.

Domyślne wartości: bezczynność 120 s, heartbeat 30 s, ograniczenie zapisu
`last_seen_at` 25 s. Wymuszone aktualizacje mogą ominąć ograniczenie.
Automatycznie zmieniane są statusy aktywny/nieaktywny; ręczne statusy są
traktowane osobno. Stare aktywne wpisy wygasają przy obsłudze żądań — nie ma
osobnego workera obecności.

## 2. Aktywny Workspace i zakres danych

Panel `/workplaces/?workspace=<pk>` wybiera przestrzeń do zarządzania niezależnie
od aktywnego Workspace. `render_workplaces()` sprawdza wybór w `workplaces_for_user()`;
`team_context()` buduje skład i akcje według roli w wybranej przestrzeni.
`management_view` rozdziela katalog, członków i zaproszenia otrzymane/wysłane.
`workplace_management_url()` zachowuje wybór po zapisie i dopuszcza wyłącznie
znane wartości `view`; ustawienia odtwarzają zakładkę z formularza. Oglądanie i edycja zespołu
oraz tworzenie Workspace nie wywołują `set_active_workplace()`; jawne przełączenie,
scoped URL modułu i przyjęcie zaproszenia zachowują dotychczasowe działanie.

Źródło: [workplaces/services.py](../workplaces/services.py).

1. Middleware sprawdza, czy adres zawiera `/workplaces/<slug>/<app>/`.
2. Wyszukuje Workspace w zbiorze właściciela i członkostw bieżącego użytkownika.
3. Ustawia sesję oraz `request.workplace`, albo wraca do wyboru Workspace.
4. Dla zwykłych adresów korzysta z sesji; jeśli potrzeba, wybiera/tworzy domyślny.
5. Wybrane modele ze starym `workplace=NULL` mogą zostać przypisane do aktywnego
   Workspace przez `backfill_legacy_records_for_workplace()`.

Backfill obejmuje stare projekty, zadania, tagi, karty, firmy, kontakty,
powiązania kontaktów i wydarzenia. Nie jest ogólną migracją wszystkich modeli.

Typowy filtr jest dwuczęściowy: właściciel Workspace **i** Workspace.
`workspace_owner(request)` sprawdza członkostwo i wyznacza właściciela danych,
a `request.user` zachowuje tożsamość autora. Pełne zasady: [Praca zespołowa](TEAMWORK.md).
Dla grupy/tablicy kontekst wynika z projektu, dla kolumny z tablicy.
Formularz musi ograniczać także listy wyboru relacji, aby POST nie przypinał
obiektu innego użytkownika/Workspace.

Niektóre helpery zwracają nieograniczony po Workspace queryset, gdy przekazano
`None`. Nie należy kopiować tego jako uniwersalnej zasady nowych endpointów;
sprawdź oczekiwany kontekst i zachowanie aktywnego middleware.

## 3. Routing zwykły i scoped

`scoped_workplace_app_path()` buduje adresy modułów. Zestaw obsługiwanych
segmentów to `tasks`, `kanban`, `contacts`, `calendar`, `documents`, `office`.
Wariant scoped ma namespace `workplace_tasks`, `workplace_kanban`,
`workplace_contacts`, `workplace_planner`, `workplace_documents` albo `workplace_office`.

Po włączeniu zakresu URL middleware przekierowuje bazowe GET/HEAD do
odpowiedniego Workspace i zachowuje query string. POST nie jest w ten sam
sposób przekierowywany, więc bazowy endpoint POST nadal korzysta z sesji.
Operacje JS zadań, kart i kalendarza używają adresów scoped wygenerowanych
dla otwartego ekranu. Zmiana Workspace w drugiej karcie nie zmienia ich celu.
`tasks.js` odczytuje moduł i bazowy adres z `data-task-app` oraz
`data-task-base-url`, również po częściowej nawigacji.

**Przy nowej funkcji:** sprawdź adres GET, formularz POST, odpowiedź/redirect,
zachowanie w dwóch Workspace, back/forward i link z wyszukiwania. Parametry
`view`, `project`, `folder`, `library`, `q`, filtry i paginacja są częścią
użyteczności danego ekranu, a nie przypadkowym dodatkiem URL.

## 4. Dostęp i historyczne udostępnianie

Aktywne zapytania Tasks/Kanban/Contacts/Planner/Documents ograniczają rekordy
do właściciela Workspace i odpowiedniego kontekstu. `workspace_owner(request)`
weryfikuje rzeczywiste członkostwo przed przekazaniem właściciela danych do
istniejących helperów Tasks/Kanban. Komentarze i historia zachowują rzeczywistego autora.

W `tasks/views/tasks.py` są starsze funkcje udostępniania i linków, ale:

- `_received_share_permission()` i `_direct_share_permission()` zwracają pusty tekst;
- `_task_shared_ids()` zwraca pustą listę, a współdzielone querysety są puste;
- flagi widoków współdzielonych są wyłączone;
- aktywny `tasks/urls.py` nie rejestruje endpointów tworzenia/akceptacji linków.

Samo istnienie `SharedItem`, `SharedItemLink`, `CompanyMembership`,
`assignee` czy `responsible_user` nie daje dostępu. Aktywne członkostwo
`WorkplaceMembership` nadaje dostęp do całego Workspace zgodnie z [TEAMWORK.md](TEAMWORK.md).
Przy zmianie uprawnień trzeba świadomie przeanalizować całą ścieżkę,
łącznie z formularzami, wyszukiwaniem, plikami i akcjami zbiorczymi.

## 5. Identyfikatory i numeracja

| Identyfikator | Znaczenie |
| --- | --- |
| `pk`/`id` modelu | Klucz bazy; dokument ma UUID, większość innych obiektów liczbowy klucz |
| `Task.task_id`, `Kanban.task_id` | Numer widoczny w danym module, użytkowniku i Workspace; używany w trasach szczegółów |
| Kod projektu | Domyślnie `P-` + 8 znaków base36; sprawdzane są projekty Tasks i Kanban |
| Kod tagu | Domyślnie `T-` + 8 znaków base36; osobny od PK i nazwy |
| Kod grupy Tasks | Licznik w projekcie, domyślny format z prefiksem `G`; może być wpisany ręcznie |
| `code_number` zadania | Licznik wewnątrz grupy; nie jest tym samym co `task_id` |

`Task.code` i `Task.full_code` zwracają obecnie tekst numeru `task_id`.
Liczniki grup/zadań korzystają z blokady `select_for_update()` i transakcji.
Numer `task_id` powstaje z maksimum w zakresie właściciela/Workspace.
`core/task_numbering.py` blokuje wiersz właściciela przed zapisem, usuwaniem
i renumeracją; blokada poprzedza blokady grup/zadań. Odroczone ograniczenie
unikalności w PostgreSQL chroni kombinację użytkownika, Workspace i numeru.
Migracje Tasks 0047 i Kanban 0034 porządkują istniejące numery przed dodaniem
ograniczeń, zachowując PK i relacje. Backfill starych rekordów bez Workspace
również porządkuje numery w tej samej transakcji.
Po usuwaniu numery są porządkowane. Nie traktuj starego numeru zadania jako
trwałego klucza dla zewnętrznej integracji.

Operacje JSON wymagają stabilnego `task_pk` (pojedynczy zapis/usunięcie) albo
listy `task_pks` (akcja zbiorcza). Brak PK lub dawne `task_ids` daje HTTP 400.
Numer w ścieżce aktualizacji/usuwania nie wyznacza tożsamości rekordu.
Wiersze, karty i wyniki globalnego wyszukiwania przekazują PK także w parametrze linku `?task_pk=`, a formularze
szczegółów w ukrytym polu. Szczegóły bez tego parametru zachowują historyczne
wyszukiwanie po numerze. W każdym wariancie obowiązuje właściciel i Workspace.
Po usunięciu lista jest przeładowywana, aby pokazać aktualną numerację.

Przy zmianie grupy zadania model aktualizuje `code_number` i Workspace na
podstawie projektu. Kontrola właściciela nadal należy również do widoku/formularza.

## 6. Zapis zadania, status i historia

Główna ścieżka tworzenia/edycji przechodzi przez formularz Django. Widok
ustawia właściciela i Workspace. Szczegóły zadania zapisują zmiany jawnie;
odpowiedź AJAX może zawierać zaktualizowane dane i wyrenderowaną historię.

`Task.save()` oraz `Kanban.save()` reagują na przejście do/z `closed`,
ustawiając `is_completed` i `completion_date`. Aktywności początkowe powstają
przez `post_save`; zmiany pól i komentarze zapisują także helpery widoków.
Notatki projektów/grup/tagów mają osobne modele i kontrolę autora przy edycji.

Pojedyncza i zbiorcza zmiana statusu w Tasks i Kanban blokuje numerację właściciela
przed odczytem i blokadą wiersza zadania. Odczyt, zapis modelu i historia należą
do jednej transakcji. Zapis statusu obejmuje tylko `status`, `is_completed`
i `completion_date`, zachowując pozostałe pola. Powtórne zamknięcie zachowuje
datę zakończenia; tylko faktyczna zmiana dodaje historię z autorem `request.user`.
Błąd zapisu historii wycofuje również status. Pojedynczy endpoint Kanbana
stosuje tę samą blokadę także przy zmianie kolumny.

Kolumna Kanban jest oddzielona od statusu. `_set_task_column()` sprawdza,
czy kolumna należy do tablicy karty i właściciela, a następnie zapisuje relację.
Przestawianie kolumn ma osobny endpoint, który waliduje zestaw identyfikatorów.

## 7. Katalogi, filtry i wydajność

Tasks i Kanban mają rozbudowane funkcje `*_window_for_request()`, które
filtrują, sortują i wycinają okno wyników po stronie serwera. Widoki używają
`select_related`, `prefetch_related`, agregacji i adnotacji do liczników.
Tasks ma osobne mechanizmy katalogów projektów, grup, tagów i zadań oraz
grupowania/paginacji po statusach.

Kontakty i firmy mają własne okna wyników. Dysk używa `Paginator`;
na jednej stronie najpierw rozlicza foldery, potem pliki, aby nie
powielać i nie pomijać pozycji przy przechodzeniu między stronami.

`documents/query.py` normalizuje dozwolone filtry i pola sortowania przed
wykonaniem zapytań. Warunki są nakładane na zbiory ograniczone właścicielem
i Workspace; wybór dysku również weryfikuje ten zakres. Dawny parametr `tag`
jest ignorowany, a wyszukiwanie nie używa historycznych tagów dokumentów.
Foldery Dysku pozostają przed plikami, z kolejnością według nazwy albo daty utworzenia.
Daty filtrów obejmują dzisiaj lub ostatnie 7/30 dni kalendarzowych w strefie
aplikacji. W koszu filtr i sortowanie „Usunięto” używają `deleted_at`.
Puste lokalizacje trafiają na koniec sortowania; `pk` rozstrzyga remisy.
Historyczne linki `sort=name`, `updated`, `oldest`, `size` pozostają obsługiwane.

Parametr Dysku `display=list|grid` wybiera tabelę albo kafelki z tych samych
wierszy i zakresu paginacji. Preferencja w sesji ma zakres konta, Workspace i rodzaju
katalogu (dyski/pliki); nieznany parametr korzysta z zapisanej wartości lub
domyślnej listy. Linki przełącznika zachowują parametry GET, a wyszukiwanie i akcje
gwiazdki/kosza/przywracania przekazują wybrany układ. Zmiana układu działa również
bez JavaScriptu. Kafelki korzystają z tych samych formularzy i kontrolowanego
pobierania co tabela.

**Zasada:** zachowuj filtrowanie i paginację na serwerze. Pobranie wszystkich
rekordów do JS i ukrywanie części wierszy zmienia koszt oraz zachowanie list.
Przed zmianą zapytań sprawdź testy liczby zapytań i renderowania tylko bieżącego okna.

## 8. Konfiguracja pól i terminów projektów

Źródła: [modele Tasks](../tasks/models.py),
[project_settings.py](../tasks/views/project_settings.py),
`_project_field_configuration()` w głównych widokach.

Słowniki statusu/etapu/kondycji mają wartości techniczne, etykiety, kolory,
kolejność i flagę aktywności. Źródło projektu jest przechowywane tekstowo;
formularz obsługuje preset oraz ręczną wartość. Nie zastępuj etykiet
bezrefleksyjnie stałymi choices w nowym widoku.

Reguły terminu wybierają pierwszy próg spełniający `days_left <= rule.days`,
po sortowaniu rosnąco. Termin przeterminowany również mieści się w najniższym
progu; brak terminu lub dopasowania daje pusty kolor. Domyślne progi to
2, 16 i 30 dni. Usunięte reguły wspólne pozostają nieaktywne, aby brak aktywnych
reguł nie powodował ponownego utworzenia domyślnych.

`Task.due_urgency` jest osobne: czerwony przy ≤24 h (także po terminie),
żółty przy ≤3 dniach, zielony dalej, `none` bez terminu.

## 9. Upload, obrazy i pobieranie

Źródło: [core/upload_validation.py](../core/upload_validation.py).

- Zdjęcia kont/firm/Workspace: JPEG, PNG, WebP, domyślnie 5 MB.
- Załączniki: lista rozszerzeń w `ATTACHMENT_ALLOWED_EXTENSIONS`, domyślnie 10 MB.
- Walidacja obejmuje pusty plik, rozmiar, rozszerzenie i rozpoznawaną sygnaturę.
  To walidacja formatu, nie skaner antywirusowy ani pełne parsowanie zawartości.
- Kadrowanie obrazu po stronie klienta współpracuje z walidacją formularzy
  zdjęć po stronie Django.
- Pobieranie używa `FileResponse(as_attachment=True)`, `nosniff` oraz
  `Cache-Control: private, no-store`;
  widok musi wcześniej zweryfikować właściciela/kontekst.

| Rodzaj danych | Przechowywanie |
| --- | --- |
| Zdjęcia i załączniki Tasks/Kanban | Standardowy `MEDIA_ROOT`, podkatalog zależny od modelu |
| Historyczne zdjęcia dysków (upload wyłączony) | `PRIVATE_DOCUMENT_ROOT/library_photos/<workplace_id>/`, losowa nazwa; kontrolowany widok obrazu |
| Pliki Documents | `FileSystemStorage` w `PRIVATE_DOCUMENT_ROOT`; losowa nazwa pod katalogiem Workspace |
| Metadane, foldery, gwiazdki, kosz | PostgreSQL |

Documents pobiera pliki tylko przez widok właściciela/Workspace,
wyklucza kosz i ustawia `Cache-Control: private, no-store`.
Foldery Dysku mają osobne `is_starred`. POST `folders/<pk>/star/` blokuje rekord,
przełącza gwiazdkę i zachowuje kontekst dysku albo widoku Workspace wraz
z filtrami, układem i stroną. GET `folders/<pk>/download/` sprawdza także
właściciela/Workspace dysku i tworzy ZIP przez wspólny
[folder_exports.py](../documents/folder_exports.py). Zakres obejmuje tylko
dostępne foldery i aktywne pliki tego samego dysku; błędna relacja między
dyskami nie pozwala włączyć obcego poddrzewa. Pozostałe zasady archiwizacji
(bezpieczne nazwy, kolizje, plik tymczasowy i brakujące pliki) są wspólne
z historycznymi modelami folderów Dokumentów.
Te same ograniczenia obowiązują dla `/<uuid>/preview/` (dialog/pełna strona)
i `/<uuid>/content/` (strumień podglądu). Surowe pliki są serwowane inline
wyłącznie dla PDF i obrazów rastrowych, z ponownym sprawdzeniem sygnatury,
ustalonym MIME, `nosniff`, `X-Frame-Options: SAMEORIGIN` oraz CSP sandbox
i `frame-ancestors 'self'`. Globalna ochrona ramek pozostaje bez zmian.
Podgląd nie korzysta z zewnętrznych usług ani publicznych adresów storage.

DOCX/XLSX/PPTX na Dysku otwierają `/documents/<uuid>/editor/` (także scoped),
a dawny `preview/` przekierowuje do tego edytora. Wspólne `suite_views.py`
obsługują edycję, force save, stan i konwersję; parametr routingu wybiera model
Dysku albo Dokumentów. Sesyjne endpointy sprawdzają właściciela, aktywny Workspace
i kosz. Podpisane źródło oraz callback Dysku mają osobną przestrzeń URL i podpisu;
nie korzystają z sesji przeglądarki. Zapis aktualizuje prywatny plik `Document`,
jego rozmiar, rewizję i datę. Kosz/przywrócenie zmieniają klucz sesji pod blokadą
rekordu, a zapis metadanych aktualizuje tylko swoje pola. Szczegóły zabezpieczeń
i uruchomienia: [OFFICE.md](OFFICE.md). Upload Dysku waliduje także pakiety OOXML.

`documents/previews.py` odczytuje pozostałe obsługiwane formaty lokalnie,
a szablon escapuje cały tekst. Archiwa nie są rozpakowywane na dysk;
relacje zewnętrzne arkuszy są odrzucane, formuły i makra nie są wykonywane.
Limity podglądu: tekst 256 KiB (arkusze/DOCX do 262144 znaków), 200 wierszy
i 30 kolumn na arkusz, 10 arkuszy, 200 pozycji archiwum. XML Office jest
ograniczony do 2 MiB na część i 12 MiB na pakiet (maks. 2000 wpisów), bez
DTD/encji, z limitem 50 tys. elementów i głębokości 64. Ograniczenie lub błąd
odczytu daje komunikat; oryginał pozostaje dostępny do pobrania, jeśli istnieje.
Upload waliduje całą partię, używa transakcji bazy i sprząta już zapisane
pliki przy błędzie. Transakcja bazy sama nie wycofuje plików na dysku.

Przenoszenie obsługuje [move_views.py](../documents/move_views.py):
`<uuid>/move/` dla plików i `folders/<pk>/move/` dla folderów Dysku,
również pod scoped URL. GET renderuje modal, POST wymaga CSRF i waliduje
cel `folder:<pk>` lub `library:<pk>` wyłącznie w zakresie właściciela
i aktywnego Workspace. Dokumenty nie udostępniają tras przenoszenia.
Nie przyjmuje dowolnego URL docelowego. Usunięte pliki, cykle i kolizje nazw
folderów (porównanie `casefold`, także polskie litery) są odrzucane.
Zmiana dysku folderu aktualizuje atomowo całe poddrzewo oraz pliki aktywne
i w koszu. Niespójne lub obce relacje w tym poddrzewie blokują zmianę dysku.
Przenoszenie zachowuje PK, prywatny plik i klucz edytora; zmiana
lokalizacji pliku zwiększa rewizję i datę modyfikacji. Nie zmienia jego treści.

[location_lock.py](../documents/location_lock.py) serializuje zapisy lokalizacji
blokadą wiersza Workspace przed blokadami dokumentów. Obejmuje przenoszenie,
upload, tworzenie/edycję folderów i dokumentów, usuwanie pustych lokalizacji
oraz tworzenie kopii przez konwersję. Zapobiega cyklom przy równoczesnym
przenoszeniu i zapisaniu pliku ze starym dyskiem w właśnie przeniesionym folderze.
Frontend przesyła dedykowany typ drag-data, sprawdza zgodność modułu/Workspace
i korzysta z istniejącego uploadu oraz częściowego odświeżenia katalogu.

Sygnały `post_delete` załączników Tasks/Kanban usuwają powiązany plik.
Historyczne zdjęcia dysków pozostają w prywatnym storage i polu `photo`;
interfejs ich nie wyświetla. Formularz dysku przyjmuje tylko nazwę i opis,
a przesłane pola `photo`, `photo_crop` i `photo_remove` są ignorowane,
także pod zwykłymi i scoped URL. Zmiana metadanych nie modyfikuje starego pliku.
Sygnał `post_delete` nadal usuwa historyczne zdjęcie po zatwierdzeniu
transakcji usunięcia dysku. Zachowany GET `libraries/<pk>/photo/` sprawdza
właściciela i aktywny Workspace, zwraca obraz z `nosniff` oraz
`Cache-Control: private, no-store`; brak zdjęcia daje 404.
Model `Document` usuwa fizyczny plik po zatwierdzeniu usunięcia rekordu,
także przy kaskadowym usuwaniu Workspace. Wycofanie transakcji zachowuje plik.
Kosz ustawia tylko `deleted_at` i pozostawia plik do przywrócenia.
Załączniki Tasks i Kanbana korzystają z tej samej zasady: sygnał `post_delete`
rejestruje `storage.delete()` przez `transaction.on_commit` na właściwej bazie.
Błąd storage jest logowany i nie przerywa kolejnych callbacków sprzątania.

### Treść i pliki osobnego modułu Dokumenty

`WorkspaceDocument` zapisuje natywną treść w PostgreSQL, a przesłany oryginał
w tym samym prywatnym storage co Dysk, z losową nazwą. Każdy odczyt i zapis
widoków `editor_views.py` ogranicza obiekty do właściciela i aktywnego Workspace.
Formularze Dysku i Dokumentów nie obsługują pola `tags`; zapis pomija też
to pole przesłane przez starego klienta. Kosz blokuje
edycję, import, podgląd i pobieranie.

Katalog Dokumentów filtruje i stronicuje wyłącznie `WorkspaceDocument`, niezależnie
od historycznej wartości `folder_id`. Stare foldery i ich gwiazdki nie wpływają
na wyniki ani liczniki. Parametr `folder` nie jest używany ani przekazywany dalej;
wycofane sortowanie po folderze wraca do domyślnego sortowania po modyfikacji.
Formularze nie zawierają pola folderu; stare POST-y nie zmieniają tej relacji.
Nowe pliki, uploady, importy i kopie mają `folder=None`. Edytory wracają do
katalogu Dokumenty. Model folderu i relacja pozostają w bazie wyłącznie dla
zgodności ze starymi danymi, bez aktywnych tras CRUD, ZIP, gwiazdek i przenoszenia.
Usunięcie funkcji nie usuwa treści ani plików z prywatnego storage.

Treść przechodzi przez `rich_text.clean_content`: dopuszczona jest mała lista
znaczników formatowania bez atrybutów; aktywne elementy, skrypty, style, obrazy,
odnośniki i nieprawidłowe znaki XML są usuwane. Limit wynosi 500 tys. znaków
z formatowaniem oraz 64 poziomy zagnieżdżenia. Przeglądarka dodatkowo buduje
edytor z listy dozwolonych elementów i wkleja wyłącznie tekst. Eksport DOCX
tworzy lokalnie pakiet OOXML, bez makr, zewnętrznych relacji i wykonywania kodu.

Zapis blokuje rekord transakcją (`select_for_update`) i porównuje numer
`revision`. Stara wersja daje błąd 409 dla edytora AJAX bez nadpisania bazy.
Zmiana metadanych/przesłanie nowego pliku również zwiększa rewizję. Gwiazdka
i kosz są oddzielnymi operacjami. Edytor wyświetla błąd po utracie połączenia
lub sesji, zachowując lokalnie wpisaną treść.

Upload waliduje całą partię przed zapisem i sprząta pliki przy wycofaniu
transakcji. Podmiana zachowuje stary plik w `DocumentVersion` w tej samej transakcji. Sygnał
`WorkspaceDocument.post_delete` usuwa oryginał po commit, także przy usuwaniu
Workspace. Jest to osobny mechanizm od starszego modelu `Document` Dysku.
PDF jest serwowany przez autoryzowany endpoint z kontrolą sygnatury,
`nosniff`, `SAMEORIGIN`, CSP sandbox i `private, no-store`. Pozostałe podglądy
korzystają z istniejących limitów `previews.py`; import tekstu odrzuca obcięte dane.

Pełne edytory DOCX/XLSX/PPTX/PDF używają podpisanej integracji ONLYOFFICE.
Serwisowe URL wymagają podpisu przypisanego do dokumentu/właściciela/Workspace,
a zapis dodatkowo JWT serwera. Klucze sesji, powtórzone callbacki, podmiana
plików oraz pobieranie wyników są opisane w [mechanizmie zapisu](OFFICE.md#zapis-i-granice-dostępu).
Tablice przechowują walidowany JSON Excalidraw w `content`; nie korzystają
z sanitizera HTML. Ten sam licznik rewizji chroni przed konfliktem okien.

Znacznik `data-app-full-navigation` na edytorze wyłącza częściową nawigację,
aby `beforeunload` mógł chronić niezapisane zmiany. Anulowanie wyjścia usuwa
wskaźnik ładowania. `office.js` inicjalizuje obsługę przy starcie i
`ancore:content-loaded`, usuwając poprzednie listenery przez `AbortController`.

Przy DEBUG routing mediów używa `core.media.public_media`: udostępnia tylko
JPEG/PNG/WebP bezpośrednio w `profile_photos`, `company_photos` i `workplace_photos`.
Załączniki i próby wyjścia poza te katalogi zwracają 404. Stare ścieżki plików
pozostają zgodne z kontrolowanym pobieraniem w Tasks/Kanbanie.
Serwer produkcyjny musi stosować tę samą listę publicznych katalogów;
nie wolno publicznie mapować całego `MEDIA_ROOT`. Szczegóły wdrożenia:
[DEVELOPMENT.md](DEVELOPMENT.md#8-wdrożenie).

## 10. Globalne wyszukiwanie

Źródła: [dashboard/views.py](../dashboard/views.py),
[global-search.js](../static/js/global-search.js).

GET `/global-search/?q=...` wymaga logowania. Minimum wynosi 2 znaki,
tekst jest ograniczany do 120 znaków. Wyszukiwanie obejmuje zadania i ich
historię, projekty/grupy, karty/tablice/przestrzenie Kanban, tagi, kontakty,
firmy, wydarzenia, Workspace, miejsca nawigacji oraz dyski/foldery/pliki.
Zakres konkretnych querysetów uwzględnia właściciela i tam, gdzie przewidziano,
aktywny Workspace; lista Workspace obejmuje własne przestrzenie i aktywne
członkostwa faktycznie zalogowanej osoby (`request.user`), niezależnie od
właściciela danych bieżącego zespołu. Nie ujawnia nazw, kodów ani opisów
prywatnych Workspace tego właściciela.

Cyfry dziesiętne Unicode mogą oznaczać numer zadania; pozostałe znaki, np. `²²`,
są zwykłym zapytaniem tekstowym. Linki do zadań, kart i ich podpozycji zawierają
stabilne `task_pk`, więc renumeracja po usunięciu nie zmienia celu wyniku.

Wybrane grupy porządkują dopasowanie dokładne, początek nazwy i fragment nazwy.
Wynik zawiera grupy z `title`, `type`, `url`, `icon`, `meta`, `eyebrow`.
Odpowiedź ma `Cache-Control: no-store`. Każda grupa danych zwraca maksymalnie
20 wyników; zapytanie SQL pobiera najwyżej 21 rekordów, aby ustalić `has_more`.
`truncated` oznacza przekroczenie limitu w co najmniej jednej grupie, a `total`
liczbę zwróconych wyników, nie wszystkich dopasowań w bazie. Mały, stały zbiór
skrótów nawigacji pozostaje kompletny. Panel oznacza obciętą grupę jako „20+”
i prosi o doprecyzowanie frazy; nie ma paginacji wyników.

Frontend obsługuje opóźnienie wyszukiwania, anulowanie starszego requestu,
stany pusty/ładowanie/błąd oraz nawigację po wynikach.

## 11. Historia a powiadomienia

`TaskActivity`, `KanbanActivity` i `ContactActivity` są historią obiektów.
Centrum powiadomień (`dashboard/notification_service.py`) odczytuje aktywności
Zadań i Kanbana, ważne oczekujące zaproszenia oraz osobiste przypomnienia.
Nie kopiuje historii; GET może utworzyć brakujące dostawy osiągniętych przypomnień.
`dashboard.NotificationState` przechowuje osobisty stan odczytu, archiwum i usunięcia,
z FK do dokładnie jednego źródła oraz unikalnością użytkownik + źródło.
Usunięcie źródła usuwa jego stan przez CASCADE.

Domyślny zakres obejmuje wszystkie dostępne Workspace oraz własne starsze rekordy
bez Workspace; filtr pozwala wybrać pojedynczą dostępną przestrzeń.
Każde pobranie i każda akcja ponownie sprawdzają członkostwo oraz właściciela
rekordu zgodnego z właścicielem Workspace. Sam wpis `NotificationState` nie daje
dostępu. Zaproszenia korzystają z `pending_invitations_for_user()` i są widoczne
przed dołączeniem, wyłącznie dla odbiorcy. Zakończone i wygasłe znikają.

Własna aktywność jest domyślnie przeczytana; działania innych osób i zaproszenia
są nieprzeczytane. Można ręcznie zmienić ten stan. Archiwizacja oznacza wpis jako
przeczytany i ukrywa go w głównej liście; przywrócenie zachowuje odczyt.
Oczekujących zaproszeń nie można archiwizować. Ich odczyt nie zastępuje decyzji.
Usuwanie ustawia `is_deleted=True` i `is_read=True` wyłącznie dla odbiorcy.
Lista, archiwum, liczniki i polling pomijają te wpisy; ponowna dostawa tego samego
przypomnienia ich nie odtwarza. Nowy termin przypomnienia tworzy odrębny wpis.
Źródłowe aktywności, zadania i zaproszenia pozostają w bazie. Zaproszenie nadal
można obsłużyć w Workspace, choć znika z panelu i jego licznika.
Stan początkowego dzwonka również pomija usunięte powiadomienia o zaproszeniach;
licznik zaproszeń w zarządzaniu Workspace nadal obejmuje wszystkie oczekujące decyzje.
Ponowne usunięcie jest idempotentne; odczyt, archiwizacja i przywrócenie usuniętego
wpisu są odrzucane. Każda operacja ponownie sprawdza dostęp do źródła.
Link `/workplaces/?invitation=<pk>` otwiera istniejący modal „Przyjmij / Odrzuć”.
Link zadania/karty określa Workspace, aktualny numer i stabilne `task_pk`.

Lista ma filtry wszystkie / nieprzeczytane / zaproszenia / przypomnienia / wzmianki / obserwowane / archiwum, grupy dat
oraz po 12 wpisów na stronę. Zaproszenia poprzedzają aktywność. Podpisany kursor
wiąże użytkownika, filtry, czas otwarcia i ostatni wpis; sortowanie rozstrzyga
remisy dat przez PK i źródło. Nowe wpisy nie przesuwają już doczytywanych stron.
`POST /notifications/action/` wymaga sesji i CSRF. Akcja zbiorczego odczytu
obejmuje cały wybrany filtr do podpisanego czasu otwarcia, także dalsze strony;
nie oznacza nowszych zdarzeń. Tokeny wygasają po 24 godzinach.
`delete` usuwa osobisty wpis według klucza, a `delete_all` korzysta z tego samego
podpisanego snapshotu i zakresu co `read_all`. Zbiorcze akcje przetwarzają po 500
rekordów w jednej transakcji i nie zmieniają wpisów spoza filtra ani nowszych zdarzeń.

`GET /notifications/` zwraca listę panelu jako JSON dla `X-Requested-With:
XMLHttpRequest` bez `Accept: text/html`. Wejście przeglądarką oraz dawna częściowa
nawigacja HTML przekierowują do Dashboardu; osobny pełny widok nie jest renderowany.
Endpoint `?summary=1` zwraca globalny licznik nieprzeczytanych, oczekujących
zaproszeń i identyfikatory najnowszych dostępnych zdarzeń. Odpowiedzi mają
`Cache-Control: no-store`. Dzwonek odświeża stan po uruchomieniu, po powrocie
do karty, po `ancore:content-loaded` i co 30 sekund w widocznej karcie.
Otwarta lista sygnalizuje zmianę przyciskiem odświeżenia, bez przestawiania
czytanej treści. Błędy sieci zachowują ostatni licznik; panel udostępnia ponowienie.
To powiadomienia wewnątrz aplikacji przez HTTP, bez push, e-maila i workera.

### Wzmianki i obserwowanie
Komentarze zadań, podzadań, kart i podkart wstawiają `@Imię Nazwisko` po
wyborze osoby z podpowiedzi. `mention_choices()` przekazuje nazwę, e-mail oraz ID
osoby. E-mail służy rozróżnianiu i wyszukiwaniu osób na liście. Przy braku
imienia i nazwiska tekstem wzmianki pozostaje login z pojedynczym `@`.

`activity_mentions` przesyła ID i zakres każdej wybranej wzmianki w punktach
kodowych Unicode. JavaScript przesuwa zakres przy dopisywaniu tekstu przed
wzmianką i usuwa powiązanie przy jej edycji/usunięciu. `comment_mention_metadata()`
normalizuje nowe linie i białe znaki, weryfikuje zakres, widoczny tekst, aktywne
konto i członkostwo; zapisuje zatwierdzone wpisy w `Activity.metadata.mentions`.
Dwie osoby o tym samym imieniu i nazwisku pozostają osobnymi odbiorcami.
Zmiana nazwy wybranej osoby przed wysłaniem wymaga ponownego wyboru.

Dostawa ponownie sprawdza odbiorcę i zakres. Widoczna nazwa wybranej osoby nie
jest interpretowana jako login innego konta. Ręcznie wpisane `@login` nadal są
obsługiwane dla zgodności; dokładny login uwzględnia wielkość liter, Unicode,
kropki oraz starsze loginy e-mail. Zwykły adres e-mail nie jest wzmianką.
Samo wpisanie imienia i nazwiska bez wyboru z listy nie określa odbiorcy.
Osoby bez dostępu i autor komentarza nie otrzymują wzmianki. Wzmianka
nie przyznaje dostępu. Istniejąca treść komentarzy pozostaje zachowana.

`dashboard.ObjectFollow` zapisuje osobistą subskrypcję dokładnie jednego
zadania, karty, projektu Zadań lub przestrzeni Kanbana. Przycisk „Obserwuj”
w szczegółach albo nagłówku projektu wysyła POST pod
`/<moduł>/follow/<task|project>/<pk>/`, również w scoped URL. Wymaga CSRF,
aktywnego Workspace i prawidłowego właściciela danych. Stan `following`
jest jawny, więc ponowienie żądania nie odwraca subskrypcji.

`dashboard/collaboration.py` odbiera utworzenie `TaskActivity` i `KanbanActivity`.
Nowe aktywności obserwowanego elementu oraz zadań/kart w obserwowanym projekcie
otrzymują `ActivityInterest` z odbiorcą i flagami `mentioned`/`followed`.
Dotyczy to także nowo tworzonych zadań i podzadań projektu oraz historii
operacji zbiorczych. Zmiany samych metadanych projektu nie mają historii
`TaskActivity` i nie generują tego typu powiadomień. Własne działania są pomijane.
Zapis komentarza i jego dostaw odbywa się w jednej transakcji.

Nie powstaje drugi wpis w centrum: filtry „Wzmianki” i „Obserwowane” wybierają
istniejące aktywności, zachowując wspólny odczyt, archiwum, usunięcie, paginację
i snapshoty operacji zbiorczych. „Wszystkie” nadal zawierają historię wszystkich
dostępnych Workspace. Rozpoczęcie obserwowania nie dostarcza wstecz historii;
wyłączenie zatrzymuje nowe dostawy, zachowując wcześniej dostarczone wpisy.
Obserwowanie projektu działa niezależnie od obserwowania pojedynczego zadania.
Cofnięcie członkostwa odcina odczyt i nowe dostawy, nawet gdy subskrypcja
pozostaje w bazie. FK i unikalność w bazie zapobiegają duplikatom i sprzątają
powiązania po usunięciu źródła. Powiadomienia działają wewnątrz aplikacji.

### Przypomnienia zadań

`dashboard/reminders.py` podczas odczytu centrum i jego licznika wyszukuje
otwarte zadania z `reminder_at <= teraz`. Odbiorcą jest wykonawca albo,
przy jego braku, właściciel zadania/Workspace. Wymagany jest aktualny dostęp
do przestrzeni; samo przypisanie wykonawcy go nie nadaje. Zapytania ponownie
sprawdzają właściciela danych, Workspace i odbiorcę także przy zmianie odczytu.

`TaskReminder` ma unikalność zadanie–odbiorca–zaplanowany termin; powtórne
odpytywanie nie powiela dostawy. Czas utworzenia oznacza faktyczny moment
dostarczenia, więc późniejsza dostawa nie jest obejmowana starszym snapshotem
„Przeczytaj wszystkie”. Odczyt i archiwum korzystają z `NotificationState`.
Zmiana terminu daje osobne przypomnienie. Zamknięcie, wyczyszczenie lub
przełożenie przypomnienia, zmiana wykonawcy i odebranie dostępu wycofują
nieaktualny wpis z aktywnych źródeł. Usunięcie zadania usuwa jego dostawy.

Nie ma osobnego harmonogramu serwerowego: obecny polling co 30 sekund w
widocznej karcie uruchamia dostarczanie. Przy zamkniętej aplikacji wpis czeka
do kolejnego odczytu. Przypomnienia nie są wpisami historii wykonanymi przez
użytkownika i pozostają domyślnie nieprzeczytane również dla właściciela.

## 12. Częściowa nawigacja i cykl życia frontendowej strony

Źródło: [layout.js](../static/js/layout.js).

1. `canNavigatePartially()` sprawdza origin i listę dozwolonych ścieżek.
2. `navigate()` pobiera HTML, przerywając poprzedni request.
3. Kod wczytuje brakujące style, podmienia kontener strony/modali/komunikatów,
   wykonuje właściwe skrypty i synchronizuje wybrane elementy nawigacji.
4. Aktualizuje tytuł, historię przeglądarki, przewijanie i ikony.
5. Wysyła `ancore:content-loaded`.
6. Przy nieobsługiwanym adresie lub błędzie stosuje pełną nawigację.

Powłoka oznacza konto przez `body[data-account-id]`. Jeśli odpowiedź częściowej
nawigacji pochodzi z innego konta, następuje pełne przeładowanie, aby osobiste
elementy (w tym Sticker) nie pozostały z poprzedniej sesji.

Lista ścieżek nie obejmuje automatycznie wszystkich adresów modułów.
W sprawdzonej wersji regexy `layout.js` są głównie bazowe; nie zawierają
scoped ścieżek Workspace ani Dysku. Obsługa `ancore:content-loaded`
w danym skrypcie nie dowodzi, że każdy jego adres jest częściowo nawigowany.
Tasks ma dodatkowo własny mechanizm podmiany widoków katalogu.

Przy nowym skrypcie zachowaj inicjalizację na pierwszym wejściu i po podmianie,
sprawdzanie istnienia elementu oraz sprzątanie/ochronę listenerów.
Nie opieraj całej inicjalizacji wyłącznie na jednorazowym `DOMContentLoaded`.

## 13. Stan w przeglądarce

| Stan | Miejsce i zakres w obecnym kodzie |
| --- | --- |
| Aktywne konto i Workspace | Sesja Django |
| Ulubione i kolejność | Baza: użytkownik + Workspace |
| Szerokość i zwinięcie sidebaru | `localStorage`, np. `ancoreSidebarWidth`, `ancoreSidebarCollapsed` |
| Zwijanie grup/ulubionych/sidebaru pomocniczego | `localStorage` w `layout.js` |
| Widoczność/szerokość/kolejność kolumn | `localStorage` w `tasks.js` i `documents.js`; klucze zależą od komponentu |
| Powrót z zadania do listy | `sessionStorage`, klucze modułu Tasks/Kanban |
| Okładki i tapety Kanban | `localStorage`; wybrana tapeta m.in. wg ścieżki tablicy |
| Sticker | `ancore:sticky-note:v2:user:<pk>`: tekst, geometria i otwarcie osobno dla konta |
| Ostatnia aktywność między kartami | `ancore:lastActivityAt` |

Nie wszystkie klucze zawierają ID użytkownika/Workspace. Lokalny stan nie
jest automatycznie prywatny dla konta ani synchronizowany z bazą.
Zmieniając strukturę klucza, uwzględnij odczyt starszych danych i reset preferencji.

Sticker jest osobisty dla konta i wspólny dla jego Workspace w danej przeglądarce.
Stary klucz `ancore:sticky-note:v1` nie zawiera właściciela: nie importujemy go
automatycznie ani nie kasujemy. Jego treść nie jest wyświetlana po zalogowaniu.
Nowy kod inicjalizuje notatkę również na `ancore:content-loaded`, z ochroną
przed podwójnymi listenerami na tym samym elemencie.

## 14. Usuwanie i zależności

- Usunięcie projektu Tasks kasuje jego grupy i zadania; widoki porządkują numery.
- Grupa Tasks ma kaskadowe zadania; relacja karty Kanban do sekcji w modelu
  jest `SET_NULL`, ale akcja UI może jawnie usuwać powiązane karty.
- Usunięcie kolumny Kanban w aktywnym widoku usuwa jej karty.
- Podzadania/podkarty mają rodzica z `CASCADE`.
- Pliki/foldery/dyski używają `RESTRICT` dla ochrony niepustych
  kontenerów. Workspace ma relacje kaskadowe; jego usuwanie jest osobnym
  scenariuszem od usuwania niepustego folderu/dysku.

Przed zmianą usuwania czytaj zarówno model, jak i akcję widoku oraz test.
Nie wyciągaj zachowania całego scenariusza tylko z jednej deklaracji `on_delete`.
