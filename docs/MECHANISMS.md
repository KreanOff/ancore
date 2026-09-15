# Wspólne mechanizmy i przepływy

## 1. Tożsamość, sesja i obecność

Logowanie korzysta z Django Auth oraz `accounts.User`, gdzie `USERNAME_FIELD`
to `email`. Profil i publiczny identyfikator są oddzielone od danych wpisu
`Contact`. Aktualne konto jest w `request.user`.

Sesja zawiera m.in. `switch_account_user_ids`, `active_workplace_id`
i `workspace_url_scope_enabled`. Przełączenie konta wykonuje `auth_login()`
i zachowuje listę uwierzytelnionych kont. Aktywny Workspace jest ponownie
weryfikowany względem bieżącego użytkownika.

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

Źródło: [workplaces/services.py](../workplaces/services.py).

1. Middleware sprawdza, czy adres zawiera `/workplaces/<slug>/<app>/`.
2. Wyszukuje Workspace w zbiorze należącym do bieżącego użytkownika.
3. Ustawia sesję oraz `request.workplace`, albo wraca do wyboru Workspace.
4. Dla zwykłych adresów korzysta z sesji; jeśli potrzeba, wybiera/tworzy domyślny.
5. Wybrane modele ze starym `workplace=NULL` mogą zostać przypisane do aktywnego
   Workspace przez `backfill_legacy_records_for_workplace()`.

Backfill obejmuje stare projekty, zadania, tagi, karty, firmy, kontakty,
powiązania kontaktów i wydarzenia. Nie jest ogólną migracją wszystkich modeli.

Typowy filtr jest dwuczęściowy: właściciel rekordu **i** Workspace.
Dla grupy/tablicy kontekst wynika z projektu, dla kolumny z tablicy.
Formularz musi ograniczać także listy wyboru relacji, aby POST nie przypinał
obiektu innego użytkownika/Workspace.

Niektóre helpery zwracają nieograniczony po Workspace queryset, gdy przekazano
`None`. Nie należy kopiować tego jako uniwersalnej zasady nowych endpointów;
sprawdź oczekiwany kontekst i zachowanie aktywnego middleware.

## 3. Routing zwykły i scoped

`scoped_workplace_app_path()` buduje adresy modułów. Zestaw obsługiwanych
segmentów to `tasks`, `kanban`, `contacts`, `calendar`, `documents`.
Wariant scoped ma namespace `workplace_tasks`, `workplace_kanban`,
`workplace_contacts`, `workplace_planner` albo `workplace_documents`.

Po włączeniu zakresu URL middleware przekierowuje bazowe GET/HEAD do
odpowiedniego Workspace i zachowuje query string. POST nie jest w ten sam
sposób przekierowywany: istniejący JS częściowo używa bazowych endpointów,
które działają na kontekście sesji.

**Przy nowej funkcji:** sprawdź adres GET, formularz POST, odpowiedź/redirect,
zachowanie w dwóch Workspace, back/forward i link z wyszukiwania. Parametry
`view`, `project`, `folder`, `library`, `q`, filtry i paginacja są częścią
użyteczności danego ekranu, a nie przypadkowym dodatkiem URL.

## 4. Dostęp i historyczne udostępnianie

Aktywne zapytania Tasks/Kanban/Contacts/Planner/Documents ograniczają rekordy
do właściciela i odpowiedniego kontekstu. W Tasks helpery uprawnień zwracają
`owner` dla właściciela i pustą wartość dla innych kont.

W `tasks/views/tasks.py` są starsze funkcje udostępniania i linków, ale:

- `_received_share_permission()` i `_direct_share_permission()` zwracają pusty tekst;
- `_task_shared_ids()` zwraca pustą listę, a współdzielone querysety są puste;
- flagi widoków współdzielonych są wyłączone;
- aktywny `tasks/urls.py` nie rejestruje endpointów tworzenia/akceptacji linków.

Samo istnienie `SharedItem`, `SharedItemLink`, `CompanyMembership`,
`WorkplaceMembership`, `assignee` czy `responsible_user` nie daje dostępu.
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
Po usuwaniu numery są porządkowane. Nie traktuj starego numeru zadania jako
trwałego klucza dla zewnętrznej integracji.

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

Operacje zbiorcze mają własne ścieżki. Tasks używa zbiorczych aktualizacji
z jawnym odtworzeniem reguł zakończenia. Nie wszystkie operacje zbiorcze
zapisują identyczną historię jak pojedynczy zapis. Przy rozszerzaniu tego
mechanizmu sprawdź zarówno stan danych, jak i spodziewane zdarzenia.

Kolumna Kanban jest oddzielona od statusu. `_set_task_column()` sprawdza,
czy kolumna należy do tablicy karty i właściciela, a następnie zapisuje relację.
Przestawianie kolumn ma osobny endpoint, który waliduje zestaw identyfikatorów.

## 7. Katalogi, filtry i wydajność

Tasks i Kanban mają rozbudowane funkcje `*_window_for_request()`, które
filtrują, sortują i wycinają okno wyników po stronie serwera. Widoki używają
`select_related`, `prefetch_related`, agregacji i adnotacji do liczników.
Tasks ma osobne mechanizmy katalogów projektów, grup, tagów i zadań oraz
grupowania/paginacji po statusach.

Kontakty i firmy mają własne okna wyników. Dokumenty używają `Paginator`;
na jednej stronie najpierw rozliczają foldery, potem dokumenty, aby nie
powielać i nie pomijać pozycji przy przechodzeniu między stronami.

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
- Pobieranie używa `FileResponse(as_attachment=True)` i `nosniff`;
  widok musi wcześniej zweryfikować właściciela/kontekst.

| Rodzaj danych | Przechowywanie |
| --- | --- |
| Zdjęcia i załączniki Tasks/Kanban | Standardowy `MEDIA_ROOT`, podkatalog zależny od modelu |
| Pliki Documents | `FileSystemStorage` w `PRIVATE_DOCUMENT_ROOT`; losowa nazwa pod katalogiem Workspace |
| Metadane, foldery, tagi, gwiazdki, kosz | PostgreSQL |

Documents pobiera pliki tylko przez widok właściciela/Workspace,
wyklucza kosz i ustawia `Cache-Control: private, no-store`.
Upload waliduje całą partię, używa transakcji bazy i sprząta już zapisane
pliki przy błędzie. Transakcja bazy sama nie wycofuje plików na dysku.

Sygnały `post_delete` załączników Tasks/Kanban usuwają powiązany plik.
Nie przenoś tej gwarancji automatycznie na Documents: obecny model Documents
nie ma analogicznego sygnału. Kosz ustawia tylko `deleted_at`.

`ancore/urls.py` serwuje `MEDIA_ROOT` bezpośrednio przy DEBUG. Kontrolowany
endpoint załącznika nie oznacza automatycznie, że każdy inny sposób dostępu
do jego pliku jest zablokowany. Konfiguracja produkcyjnego serwowania mediów
wymaga sprawdzenia w środowisku wdrożenia.

## 10. Globalne wyszukiwanie

Źródła: [dashboard/views.py](../dashboard/views.py),
[global-search.js](../static/js/global-search.js).

GET `/global-search/?q=...` wymaga logowania. Minimum wynosi 2 znaki,
tekst jest ograniczany do 120 znaków. Wyszukiwanie obejmuje zadania i ich
historię, projekty/grupy, karty/tablice/przestrzenie Kanban, tagi, kontakty,
firmy, wydarzenia, Workspace, miejsca nawigacji oraz biblioteki/foldery/dokumenty.
Zakres konkretnych querysetów uwzględnia właściciela i tam, gdzie przewidziano,
aktywny Workspace; lista samych Workspace dotyczy przestrzeni właściciela.

Wybrane grupy porządkują dopasowanie dokładne, początek nazwy i fragment nazwy.
Wynik zawiera grupy z `title`, `type`, `url`, `icon`, `meta`, `eyebrow`.
Odpowiedź ma `Cache-Control: no-store`. Aktualny helper grup nie stronicuje
wyników i ustawia `has_more=False`; nie zakładaj limitu wyników na podstawie
samego pola `truncated`.

Frontend obsługuje opóźnienie wyszukiwania, anulowanie starszego requestu,
stany pusty/ładowanie/błąd oraz nawigację po wynikach.

## 11. Historia a powiadomienia

`TaskActivity`, `KanbanActivity` i `ContactActivity` są historią obiektów.
Panel powiadomień bierze ostatnie aktywności Tasks i Kanban właściciela,
scala i sortuje je, zwracając maksymalnie 12. Obecny helper powiadomień
nie filtruje po `request.workplace`, ponieważ otrzymuje tylko użytkownika.
Nie opisuj go jako ściśle ograniczonego do bieżącego Workspace.

Panel pobiera dane HTTP przy otwarciu; może otrzymać JSON z liczbą oraz
fragmentem HTML. Nie jest to push/WebSocket ani system read/unread.
`notifications.js` obsługuje również osobne krótkie komunikaty z Django Messages.

## 12. Częściowa nawigacja i cykl życia frontendowej strony

Źródło: [layout.js](../static/js/layout.js).

1. `canNavigatePartially()` sprawdza origin i listę dozwolonych ścieżek.
2. `navigate()` pobiera HTML, przerywając poprzedni request.
3. Kod wczytuje brakujące style, podmienia kontener strony/modali/komunikatów,
   wykonuje właściwe skrypty i synchronizuje wybrane elementy nawigacji.
4. Aktualizuje tytuł, historię przeglądarki, przewijanie i ikony.
5. Wysyła `ancore:content-loaded`.
6. Przy nieobsługiwanym adresie lub błędzie stosuje pełną nawigację.

Lista ścieżek nie obejmuje automatycznie wszystkich adresów modułów.
W sprawdzonej wersji regexy `layout.js` są głównie bazowe; nie zawierają
scoped ścieżek Workspace ani Dokumentów. Obsługa `ancore:content-loaded`
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
| Sticker | `ancore:sticky-note:v1`: tekst, geometria, otwarcie |
| Ostatnia aktywność między kartami | `ancore:lastActivityAt` |

Nie wszystkie klucze zawierają ID użytkownika/Workspace. Lokalny stan nie
jest automatycznie prywatny dla konta ani synchronizowany z bazą.
Zmieniając strukturę klucza, uwzględnij odczyt starszych danych i reset preferencji.

## 14. Usuwanie i zależności

- Usunięcie projektu Tasks kasuje jego grupy i zadania; widoki porządkują numery.
- Grupa Tasks ma kaskadowe zadania; relacja karty Kanban do sekcji w modelu
  jest `SET_NULL`, ale akcja UI może jawnie usuwać powiązane karty.
- Usunięcie kolumny Kanban w aktywnym widoku usuwa jej karty.
- Podzadania/podkarty mają rodzica z `CASCADE`.
- Dokumenty/foldery/biblioteki używają `RESTRICT` dla ochrony niepustych
  kontenerów. Workspace ma relacje kaskadowe; jego usuwanie jest osobnym
  scenariuszem od usuwania niepustego folderu/biblioteki.

Przed zmianą usuwania czytaj zarówno model, jak i akcję widoku oraz test.
Nie wyciągaj zachowania całego scenariusza tylko z jednej deklaracji `on_delete`.
