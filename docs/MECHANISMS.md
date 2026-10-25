# Wspólne mechanizmy i przepływy

## Zapisane filtry

Definicje są ograniczone do właściciela i aktywnego Workspace, twórcy
lub jawnych odbiorców. Ulubione są osobiste. Parser kompiluje ograniczoną
składnię do ORM po zastosowaniu aktualnych ACL Przestrzeni; udostępnienie
filtra nie zmienia dostępu do zadań. Zapisy używają blokady wiersza i rewizji,
a currentUser() jest ustalany dla osoby otwierającej wynik.
[Szczegóły](FILTERS.md).

Dawne systemy pracy usunięto ze schematu. [Czysta baza i migracje](DATABASE.md).

## Wspólne zadania przestrzeni

Listy, tablice, backlog i szczegóły korzystają z `spaces.SpaceTask`
i metadanych `WorkItem`. Numer klucza przestrzeni jest trwały; nie używa
dawnego numeru `task_id`. Dostęp wyznaczają `SpaceMembership`,
`SpaceTaskMembership` i `spaces.access`, w aktywnym Workspace i całym drzewie
rodziców. Zapisy statusu blokują Workspace, przestrzeń, zadanie i WorkItem;
zachowują zakończenie i autora historii.
Prywatne pliki zadań są usuwane dopiero po ostatnim odwołaniu
i zatwierdzeniu transakcji. [Modele, adresy, migracja i granice](SPACES.md).

Automatyczny zapis szczegółów wykonuje kolejno żądania AJAX `action=save`.
`DetailForm` waliduje zmienione pola wskazane w `autosave_fields`, uzupełniając
pozostałe bieżącymi wartościami pod blokadą Workspace/przestrzeni/zadania.
Zapis, status, historia i pliki pozostają jedną transakcją; autor to
`request.user`. Odpowiedź JSON aktualizuje otwarty widok bez zastępowania
edytowanych pól. Niepowodzenie zachowuje szkic; dopiero powodzenie przesuwa
snapshot zapisu. Żądanie bez `autosave_fields` zachowuje pełny formularz.
Niezmieniane relacje (wykonawca, zespół, sprint, epik) zachowują bieżące
wartości także po utracie możliwości ich wyboru. Nie są ponownie walidowane
jako nowe przypisania; nadal uczestniczą w walidacji zależności pól.
Jawna zmiana lub wyczyszczenie relacji przechodzi zwykłą walidację,
a niedostępne obiekty nie są dodawane do opcji formularza ani API.

Zbiorcze planowanie backlogu waliduje całą bieżącą stronę zaznaczenia i snapshot
`sprint_id/rank` pod blokadą Workspace oraz Przestrzeni. Zapis dopisuje wyłącznie
edytowalne zadania na końcu grupy docelowej i tworzy historię autora; błąd
wycofuje całą transakcję. Zakończenie sprintu korzysta z tego samego mechanizmu
dopisania dla niedokończonych zadań, z wyborem backlogu lub sprintu planowanego.
Pełne liczniki punktów i postępu są ograniczone aktualnymi ACL i filtrami.
[Przepływ planowania](SPACES.md#planowanie-w-backlogu).


## 1. Tożsamość, sesja i obecność

Logowanie korzysta z Django Auth oraz `accounts.User`, gdzie `USERNAME_FIELD`
to `email`. Profil i publiczny identyfikator są oddzielone od danych wpisu
`Contact`. Aktualne konto jest w `request.user`.

React używa osobnego `/accounts/api/v1/page/` z jawną listą operacji.
Anonimowy dostęp dotyczy logowania/rejestracji i ekranu zaproszenia; tworzenie Workspace wymaga zalogowania, a wszystkie zapisy
zachowują CSRF. Adapter przekazuje zmienionego użytkownika do middleware
i zachowuje cookie CSRF z wewnętrznej odpowiedzi `LoginView`, gdy zamienia
przekierowanie na JSON. Dane kont nie są cache'owane; hasła i hashe sesyjne
przełącznika pozostają wyłącznie w Django. Zmiana tożsamości wymaga pełnego
odświeżenia powłoki, aby nie zachować danych poprzedniego konta w interfejsie.

Logowanie otwiera „Dla ciebie” w dostępnym Workspace. Konto bez Workspace
przechodzi do `/accounts/register/workspace/`; oczekujące dołączenie przez link
wraca do potwierdzenia zaproszenia. Dowolny parametr `next` nadal nie zmienia
celu logowania. Rejestracja tworzy i uwierzytelnia konto, bez tworzenia Workspace.

`User.default_workplace` zapisuje osobisty wybór startowego Workspace. Menu
katalogu pozwala ustawić jeden dostępny Workspace albo usunąć wybór przez
POST `/workplaces/<pk>/default/` (`action=set/remove`, CSRF). Zmiana dotyczy
wyłącznie zalogowanej osoby i nie przełącza aktywnej sesji. Przy logowaniu
`default_workplace_for_user()` ponawia kontrolę dostępu; poprawny wybór ustawia
sesję i prowadzi do scoped „Dla ciebie”, również gdy poprzednio używano innego
Workspace. Oczekujące zaproszenie zachowuje pierwszeństwo. Bez poprawnego wyboru
obowiązuje dotychczasowe zachowanie. Usunięcie Workspace ustawia preferencję
na NULL; nieaktywne/usunięte członkostwo nie daje dostępu przez tę relację.

Rejestracja i tworzenie Workspace:
Krok „Utwórz Workspace” wymaga nazwy (1–140 znaków po normalizacji odstępów).
Dopiero POST tworzy Workspace, członkostwo właściciela, skrót Dashboardu,
pulpit domyślny i gadżet „Postęp pracy” w jednej transakcji. Blokada wiersza
użytkownika chroni pierwszy Workspace przed podwójnym zapisem. Błąd inicjalizacji
wycofuje Workspace; konto pozostaje gotowe do ponowienia. Utworzenie ustawia
sesję i prowadzi do scoped „Dla ciebie”. Istniejące dane i nazwy pozostają zachowane.
GET tego kroku pokazuje również listę dostępnych Workspace. Wybór używa
istniejącego POST przełącznika, z ponowną kontrolą członkostwa i CSRF.
Formularz osoby z istniejącym Workspace jawnie oznacza tworzenie kolejnego
przez `create_another=1`; pierwszy POST bez tej flagi zachowuje ochronę
przed utworzeniem kolejnego rekordu po ponowieniu.

Rejestracja i profil sprawdzają e-mail bez względu na wielkość liter.
Logowanie i dodanie kolejnego konta używają `accounts.backends.EmailBackend`
z wyszukiwaniem `email__iexact`, również dla kont zapisanych wcześniej z wielkimi
literami. Hasło i aktywność konta nadal sprawdza Django. Historyczny
`ModelBackend` pozostaje dostępny dla istniejących sesji.
Ograniczenie `accounts_user_email_ci_unique` na `Lower(email)` chroni również
równoczesne zapisy i operacje ORM. Konflikt pomiędzy walidacją a zapisem
wraca jako błąd pola e-mail, bez błędu HTTP 500. Sam adres e-mail nie nadaje
dostępu do Workspace; ręczne dodawanie wskazuje istniejące konto.
Przy rejestracji kolizja wygenerowanego `username` powoduje ponowny wybór
unikatowego ID i zapis w osobnym savepoincie (maksymalnie pięć prób).
Równoczesne rejestracje osób o takich samych imionach i nazwiskach mogą
dzięki temu utworzyć konta z kolejnymi końcówkami ID. Konflikty e-mail
zachowują dotychczasową obsługę błędu formularza.

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

- [middleware](../backend/accounts/middleware.py), który aktualizuje aktywność przy żądaniach;
- [presence.py](../backend/accounts/presence.py), który obsługuje status i ostatnią aktywność;
- [presence.js](../static/js/presence.js), który wysyła heartbeat do
  `/accounts/presence/ping/` i współdzieli czas aktywności między kartami;
- konfiguracji w `core/base.html` i `backend/ancore/settings.py`.

Domyślne wartości: bezczynność 120 s, heartbeat 30 s, ograniczenie zapisu
`last_seen_at` 25 s. Wymuszone aktualizacje mogą ominąć ograniczenie.
Automatycznie zmieniane są statusy aktywny/nieaktywny; ręczne statusy są
traktowane osobno. Stare aktywne wpisy wygasają przy obsłudze żądań — nie ma
osobnego workera obecności.

## 2. Aktywny Workspace i zakres danych

Panel `/workplaces/?workspace=<pk>` wybiera przestrzeń do zarządzania niezależnie
od aktywnego Workspace. `render_workplaces()` sprawdza wybór w `workplaces_for_user()`;
`team_context()` buduje skład i akcje według roli w wybranej przestrzeni.
`management_view` rozdziela katalog, członków i linki do dołączenia.
`workplace_management_url()` zachowuje wybór po zapisie i dopuszcza wyłącznie
znane wartości `view`; ustawienia odtwarzają zakładkę z formularza. Oglądanie i edycja zespołu
nie wywołują `set_active_workplace()`; utworzenie nowego Workspace, jawne przełączenie,
scoped URL modułu i potwierdzenie linku do dołączenia zmieniają aktywny kontekst.

Źródło: [workplaces/services.py](../backend/workplaces/services.py).

1. Middleware sprawdza, czy adres zawiera `/workplaces/<slug>/<app>/`.
2. Wyszukuje Workspace w zbiorze właściciela i członkostw bieżącego użytkownika.
3. Ustawia sesję oraz `request.workplace`, albo wraca do wyboru Workspace.
4. Dla zwykłych adresów korzysta z sesji; jeśli potrzeba, wybiera dostępny albo kieruje do jawnego tworzenia.
5. Zmiana Workspace nie przypisuje ani nie przenosi rekordów między katalogami.

`ensure_default_workplace()` wybiera dostępny Workspace wskazany w osobistej
preferencji, a przy jej braku pierwszy dostępny. Aktywny wybór sesji nadal ma
pierwszeństwo podczas zwykłej pracy. Funkcja nie tworzy
rekordów podczas logowania, GET ani utraty sesji. Jeśli użytkownik nie ma żadnego
miejsca pracy, domenowe ekrany prowadzą do jawnego tworzenia. Katalog Workspace,
konto, publiczny ekran zaproszenia i osobiste powiadomienia pozostają dostępne.
Moduły i odczyt gościa kontroluje `workplaces.policy`, również w delegowanych
operacjach `/api/v1/page/`. [Pełne zasady](TEAMWORK.md#system-workspace-25102026).

Nazwa Workspace jest etykietą: może zawierać dowolny tekst do 140 znaków
i może się powtarzać, również u tego samego właściciela. Formularz nadal wymaga
niepustej nazwy i normalizuje odstępy. `Workplace.code` jest stałym, losowym
identyfikatorem `w_` + 26 małych liter/cyfr generowanym przez `secrets`.
Globalne ograniczenie `unique_workplace_code` chroni unikalność w bazie;
przy kolizji tworzenie ponawia losowanie w osobnej transakcji/savepoincie.
Nie ma kodu z nazwy ani numerowanych końcówek. Formularze i admin nie pozwalają
zmieniać kodu. `slug` ma tę samą wartość, więc zmiana nazwy lub opisu nie zmienia
adresu `/workplaces/<code>/`. `legacy_slug` zachowuje poprzedni segment URL
istniejącego Workspace i jest zarezerwowany przed użyciem jako nowy identyfikator.

Backfill obejmuje stare projekty, zadania, karty, firmy, kontakty,
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
segmentów to `tasks`, `kanban`, `calendar`, `documents`, `office`,
`resources`, `for-you`, `spaces`, `teams` i `dashboards`. Dawne adresy Kontaktów zwracają 404
i nie są przepisywane przez middleware do aktywnego Workspace.
Wariant scoped ma namespace `workplace_tasks`, `workplace_kanban`,
`workplace_planner`, `workplace_documents`, `workplace_office`,
`workplace_resources`, `workplace_spaces`, `workplace_teams` albo `workplace_pulpits`. „Dla ciebie” ma nazwy tras `for_you` i
`workplace_for_you` bez osobnego namespace.

Po włączeniu zakresu URL middleware przekierowuje bazowe GET/HEAD do
odpowiedniego Workspace i zachowuje query string. POST nie jest w ten sam
sposób przekierowywany, więc bazowy endpoint POST nadal korzysta z sesji.
Stare scoped adresy z `legacy_slug` nadal sprawdzają dostęp bieżącego użytkownika:
GET/HEAD przekierowuje na losowy identyfikator z zachowaniem modułu, dalszej
ścieżki i query string, a POST obsługuje ten sam Workspace bez utraty treści.
Stary adres główny Workspace również prowadzi do jego „Dla ciebie”.
Operacje JS zadań, kart i kalendarza używają adresów scoped wygenerowanych
dla otwartego ekranu. Zmiana Workspace w drugiej karcie nie zmienia ich celu.
`tasks.js` odczytuje moduł i bazowy adres z `data-task-app` oraz
`data-task-base-url`, również po częściowej nawigacji.

**Przy nowej funkcji:** sprawdź adres GET, formularz POST, odpowiedź/redirect,
zachowanie w dwóch Workspace, back/forward i link z wyszukiwania. Parametry
`view`, `project`, `folder`, `library`, `q`, filtry i paginacja są częścią
użyteczności danego ekranu, a nie przypadkowym dodatkiem URL.

## 4. Dostęp i historyczne udostępnianie

Przestrzenie, zadania, historię, pliki i dzienniki ogranicza `spaces.access`.
Właściciel danych pochodzi z `workspace_owner(request)`, kontekst z `request.workplace`.
`SpaceMembership` i `SpaceTaskMembership` wyznaczają niezależne role,
z uwzględnieniem prywatnych rodziców. Wykonawca i zespół nie nadają dostępu.
Formularze relacji stosują ten sam zakres. Usunięcie lub dezaktywacja członka
Workspace czyści powiązane członkostwa Przestrzeni, zadań i zespołów.
Dawne modele udostępniania i ich sygnały usunięto. [Role](TEAMWORK.md).

## 5. Identyfikatory i numeracja

`pk` jest technicznym kluczem rekordu. Trwały klucz zadania, np. `PRO-7`,
przechowuje `WorkItem.key`; licznik `Space.next_number` jest zwiększany
pod blokadą przestrzeni w transakcji. Usunięcie nie renumeruje pozostałych zadań
ani nie przydziela ponownie ich kluczy. Baza wymusza unikalność `(space, number)`.
`SpaceTask.save()` blokuje przestrzeń, odrzuca przeniesienie i rodzica z innej
przestrzeni oraz cykle. `WorkItem.save()` chroni tożsamość zadania i klucza.

Adres zadania używa slugu przestrzeni i klucza WorkItem, także w scoped URL.
Workspace ma losowy stały kod `w_` + 26 znaków, przestrzenie i pulpity osobne slugi.
Tag ma losowy, globalnie unikatowy kod `T-` + 8 znaków base36.
Nie ma dawnych liczników `Task.task_id`, kodów projektów i grup ani mapowań importu.

## 6. Zapis zadania, status i historia

Zapis bieżących zadań obsługuje `spaces.task_views`, planowanie i statusy
`spaces.services` oraz `spaces.backlog`. Statusy pochodzą z konfiguracji
przestrzeni; przejścia są walidowane. Zapis blokuje Workspace, przestrzeń,
zadanie i WorkItem. `SpaceTask.save()` ustala `is_completed` i `completion_date`.
Historia `SpaceTaskActivity` zachowuje rzeczywistego autora operacji.
Zmiana zbiorcza używa tych samych reguł zakończenia i historii.

### Dziennik pracy zadania

`SpaceTaskWorkLog` należy do zadania i autora. `SpaceTaskWorkLogForm` waliduje
przedział oraz czas; baza wymaga dodatniej liczby sekund. Czas wynika z chwil UTC,
a formularz i wyświetlanie korzystają z lokalnej strefy. Edycja i usunięcie
ponownie sprawdzają widoczność oraz autora. Operacje czasu i wpis historii
należą do tej samej transakcji. Szczegóły oraz automatyczny zapis opisuje [SPACES.md](SPACES.md).

## 7. Katalogi, filtry i wydajność

Dawne katalogi Projektów, Grup, Zadań, Kontaktów i Kanbana oraz ich helpery
okien wyników usunięto. Bieżące listy Przestrzeni, Filtry i Dashboard
korzystają z `SpaceTask`; zakres ACL i Workspace jest nakładany przed
licznikami, filtrowaniem, sortowaniem i paginacją.

`tasks.tag_directory.tag_window_for_request()` obsługuje zakładkę tagów
Przestrzeni: wyszukiwanie etykiet, filtry, sortowanie i paginację serwerową.
Licznik użycia uwzględnia tylko widoczne zadania główne. Tagi bez Przestrzeni
nie trafiają do katalogu, pickerów ani wyszukiwania zadań.
Historyczne nazwy `data-project-*` i klasy `tasks-*` pozostają kontraktem
współdzielonych kontrolek, także w React.

Powiadomienia zachowują puste źródła `tasks` i `kanban`, aby stare tokeny
nie mogły zmieniać stanu archiwalnych aktywności. Zgodność adresów obsługuje
bieżący routing Przestrzeni.

Dysk używa `Paginator`; na stronie najpierw rozlicza foldery, potem pliki,
aby nie powielać i nie pomijać pozycji między stronami.

`backend/documents/query.py` normalizuje dozwolone filtry i pola sortowania przed
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

## 8. Pola i terminy projektów

Dawne projekty oraz system ich pól usunięto. Bieżące typy, statusy i pola
pochodzą z `SpaceConfiguration`; planowanie zapisuje `WorkItem`.
Szczegóły walidacji i wspólnej konfiguracji opisuje [SPACES.md](SPACES.md).

## 9. Upload, obrazy i pobieranie

Źródło: [core/upload_validation.py](../backend/core/upload_validation.py).

- Zdjęcia kont/Workspace: JPEG, PNG, WebP, domyślnie 5 MB.
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
| Pliki zadań Przestrzeni | `PRIVATE_DOCUMENT_ROOT/space_task_files/`, kontrolowane pobieranie |
| Pliki i zdjęcia komentarzy Przestrzeni | Prywatny `SpaceTaskFile`, powiązanie z aktywnością |
| Historyczne zdjęcia dysków (upload wyłączony) | `PRIVATE_DOCUMENT_ROOT/library_photos/<workplace_id>/`, losowa nazwa; kontrolowany widok obrazu |
| Pliki Documents | `FileSystemStorage` w `PRIVATE_DOCUMENT_ROOT`; losowa nazwa pod katalogiem Workspace |
| Metadane, foldery, gwiazdki, kosz | PostgreSQL |

Documents pobiera pliki tylko przez widok właściciela/Workspace,
wyklucza kosz i ustawia `Cache-Control: private, no-store`.
Foldery Dysku mają osobne `is_starred`. POST `folders/<pk>/star/` blokuje rekord,
przełącza gwiazdkę i zachowuje kontekst dysku albo widoku Workspace wraz
z filtrami, układem i stroną. GET `folders/<pk>/download/` sprawdza także
właściciela/Workspace dysku i tworzy ZIP przez wspólny
[folder_exports.py](../backend/documents/folder_exports.py). Zakres obejmuje tylko
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

`backend/documents/previews.py` odczytuje pozostałe obsługiwane formaty lokalnie,
a szablon escapuje cały tekst. Archiwa nie są rozpakowywane na dysk;
relacje zewnętrzne arkuszy są odrzucane, formuły i makra nie są wykonywane.
Limity podglądu: tekst 256 KiB (arkusze/DOCX do 262144 znaków), 200 wierszy
i 30 kolumn na arkusz, 10 arkuszy, 200 pozycji archiwum. XML Office jest
ograniczony do 2 MiB na część i 12 MiB na pakiet (maks. 2000 wpisów), bez
DTD/encji, z limitem 50 tys. elementów i głębokości 64. Ograniczenie lub błąd
odczytu daje komunikat; oryginał pozostaje dostępny do pobrania, jeśli istnieje.
Upload waliduje całą partię, używa transakcji bazy i sprząta już zapisane
pliki przy błędzie. Transakcja bazy sama nie wycofuje plików na dysku.

Przenoszenie obsługuje [move_views.py](../backend/documents/move_views.py):
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

[location_lock.py](../backend/documents/location_lock.py) serializuje zapisy lokalizacji
blokadą wiersza Workspace przed blokadami dokumentów. Obejmuje przenoszenie,
upload, tworzenie/edycję folderów i dokumentów, usuwanie pustych lokalizacji
oraz tworzenie kopii przez konwersję. Zapobiega cyklom przy równoczesnym
przenoszeniu i zapisaniu pliku ze starym dyskiem w właśnie przeniesionym folderze.
Frontend przesyła dedykowany typ drag-data, sprawdza zgodność modułu/Workspace
i korzysta z istniejącego uploadu oraz częściowego odświeżenia katalogu.

Sygnał `post_delete` plików zadań rejestruje sprzątanie po zatwierdzeniu transakcji.
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
Załączniki zadań Przestrzeni korzystają z tej samej zasady: sygnał `post_delete`
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

Źródła: [dashboard/views.py](../backend/dashboard/views.py),
[Search.tsx](../frontend/app/src/shell/Search.tsx); `global-search.js` pozostaje trybem zgodności.

GET `/global-search/?q=...` wymaga logowania. Minimum wynosi 2 znaki,
tekst jest ograniczany do 120 znaków. Wyszukiwanie obejmuje zadania Przestrzeni
i ich historię, Przestrzenie, ich tagi, wydarzenia,
Workspace, miejsca nawigacji oraz dyski/foldery/pliki. Wycofane katalogi Kontaktów
i Firm oraz historyczne projekty/grupy/zadania Tasks nie są przeszukiwane.
Zakres konkretnych querysetów uwzględnia właściciela i tam, gdzie przewidziano,
aktywny Workspace; lista Workspace obejmuje własne przestrzenie i aktywne
członkostwa faktycznie zalogowanej osoby (`request.user`), niezależnie od
właściciela danych bieżącego zespołu. Nie ujawnia nazw, kodów ani opisów
prywatnych Workspace tego właściciela.

Wyszukiwanie traktuje również znaki Unicode i długie ciągi cyfr jako tekst.
Linki bieżących zadań zawierają stały klucz `WorkItem.key` w adresie przestrzeni.
Historyczne wyniki Tasks i Kanbana są wycofane.

Wybrane grupy porządkują dopasowanie dokładne, początek nazwy i fragment nazwy.
Wynik zawiera grupy z `title`, `type`, `url`, `icon`, `meta`, `eyebrow`.
Odpowiedź ma `Cache-Control: no-store`. Każda grupa danych zwraca maksymalnie
20 wyników; zapytanie SQL pobiera najwyżej 21 rekordów, aby ustalić `has_more`.
`truncated` oznacza przekroczenie limitu w co najmniej jednej grupie, a `total`
liczbę zwróconych wyników, nie wszystkich dopasowań w bazie. Mały, stały zbiór
skrótów nawigacji pozostaje kompletny. Panel oznacza obciętą grupę jako „20+”
i prosi o doprecyzowanie frazy; nie ma paginacji wyników.

Frontend obsługuje opóźnienie wyszukiwania, anulowanie starszego requestu,
stany pusty/ładowanie/błąd oraz nawigację po wynikach. Wyniki pojawiają się
w rozwijanym panelu pod polem górnego paska; przyciski typów filtrują pobrane
wyniki bez zmiany uprawnień ani limitów serwera.

GET `/global-search/?recent=1` przy pustej frazie zwraca do 8 ostatnio oglądanych
zadań i przestrzeni z aktywnego modułu Przestrzeni, bez historycznych
projektów, grup i zadań Tasks/Kanbana. Korzysta z identyfikatorów
`dashboard.recent` zapisanych dla konta i Workspace w bieżącej sesji.
Przy każdym odczycie ponownie stosuje `workspace_owner`, Workspace i `visible_to`;
usunięte elementy oraz te, do których cofnięto dostęp, nie trafiają do odpowiedzi.
Otwarcie bieżącej Przestrzeni zapisuje jej własny identyfikator w tej historii,
po sprawdzeniu uprawnień i wyrenderowaniu widoku. Tytuły i numery są pobierane
z aktualnych rekordów. Nowe zadania używają adresu przestrzeni i klucza;
Odpowiedź ma `Cache-Control: no-store`; frontend nie zapisuje wyników
w localStorage. Zwykłe puste i jednoznakowe zapytania nadal nie wykonują wyszukiwania.

## 11. Historia a powiadomienia

`SpaceTaskActivity` przechowuje komentarze i historię; do inbox trafiają
wyłącznie dostępne komentarze. `NotificationState` wskazuje dokładnie jedno źródło:
komentarz albo `SpaceTaskReminder`. Nie ma dawnych dostaw
Tasks/Kanbana, projektów i grup ani modeli subskrypcji.

`dashboard.notification_service` sprawdza bieżące ACL przy liście, licznikach
i każdej akcji. Odczyt, archiwum i usunięcie są osobiste i nie kasują źródła.
Zaproszenia e-mail i ich stany zostały usunięte. Link do dołączenia nie jest
źródłem powiadomień. `deletable_count` liczy usuwalne wpisy wszystkich stron
aktualnego filtra.
Lista ma stronicowanie kursorem i podpisany snapshot; operacje zbiorcze obejmują
wszystkie strony aktualnego filtra do czasu snapshotu, bez późniejszych wpisów.
Kursor i snapshot są związane z użytkownikiem, czasem i filtrem Workspace.


### Pliki i zdjęcia w komentarzach
`SpaceTaskFile` przechowuje załączniki komentarzy i zadania. Mają rozmiar `file_size` i FK do aktywności (`images`),
nie do ogólnych załączników zadania. Wspólny `backend/core/comment_images.py` waliduje
całą partię przez `validate_comment_attachments()` w `backend/core/upload_validation.py`
(wspólna lista `ATTACHMENT_ALLOWED_EXTENSIONS`, łącznie 10 plików i `MAX_ATTACHMENT_SIZE`). Dopiero potem zapisuje komentarz,
wzmianki i pliki w jednej transakcji. Przy rollbacku usuwa nowe pliki;
usunięcie aktywności/zadania usuwa pliki dopiero po zatwierdzeniu transakcji.

`/space/<slug>/tasks/<klucz>/files/<pk>/` i scoped odpowiednik wymagają zalogowania,
właściciela danych oraz aktywnego Workspace. Zdjęcia zwracają inline, a pozostałe
pliki jako attachment. Wszystkie odpowiedzi mają `nosniff` i `private, no-store`; publiczne `/media/` nie obsługuje tych plików.
Link załącznika zawiera Workspace, a identyfikatorem jest PK pliku.
Usunięcie członkostwa odbiera dostęp także do wcześniej zapisanych URL.
Listy aktywności pobierają pliki przez prefetch relacji `images`. POST
`add_activity_comment` przyjmuje `comment_attachments` oraz starsze `comment_images`
z tym samym łącznym limitem; AJAX zwraca fragment wiadomości albo błąd 400,
bez przeładowania niezapisanego formularza zadania. Zwykły POST nadal działa;
po błędzie zachowuje tekst i wzmianki, a pliki trzeba wybrać ponownie.

### Wzmianki i obserwowanie

Komentarze Przestrzeni wstawiają `@Imię Nazwisko` po wyborze osoby z listy.
`dashboard.collaboration.mention_choices()` udostępnia nazwę, e-mail i ID
wyłącznie aktywnych osób Workspace z dostępem do zadania i jego rodziców.
Przy braku imienia i nazwiska etykieta korzysta z loginu z pojedynczym `@`.

`activity_mentions` przesyła ID i zakres wybranej wzmianki w punktach
kodowych Unicode. `comment_mention_metadata()` normalizuje nowe linie,
białe znaki, zakres, widoczny tekst i aktualny dostęp osoby.
Zatwierdzone wzmianki są zapisane w `SpaceTaskActivity.metadata.mentions`.
Zmiana nazwy osoby przed wysłaniem wymaga ponownego wyboru; dwie osoby
z tą samą nazwą pozostają różnymi odbiorcami. Wzmianka nie nadaje dostępu.

Centrum powiadomień ponownie sprawdza widoczność aktywności. Własne komentarze
są pomijane. Stan odczytu, archiwum i usunięcia należy do `NotificationState`.
Dawne modele obserwowania i dostaw usunięto.

### Przypomnienia zadań

`backend/dashboard/reminders.py` podczas odczytu centrum i jego licznika wyszukuje
otwarte zadania z `reminder_at <= teraz`. Odbiorcą jest wykonawca albo,
przy jego braku, właściciel zadania/Workspace. Wymagany jest aktualny dostęp
do przestrzeni; samo przypisanie wykonawcy go nie nadaje. Zapytania ponownie
sprawdzają właściciela danych, Workspace i odbiorcę także przy zmianie odczytu.

`SpaceTaskReminder` ma unikalność zadanie–odbiorca–zaplanowany termin; powtórne
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

## 12. Nawigacja i cykl życia frontendowej strony

Źródła: [kontrakt React](FRONTEND.md#powłoka-i-nawigacja-json),
[navigation.ts](../frontend/app/src/shell/navigation.ts), [shell.py](../backend/core/shell.py).

1. `AncoreApp.canNavigatePartially()` sprawdza origin i jawnie obsługiwane
   ekrany, normalizując scoped ścieżki Workspace. Zwykłe kliknięcia i formularze
   GET używają `navigate()`. Pliki, nowe karty, zewnętrzne linki, przełączanie
   konta/Workspace i pełne edytory mają własne przepływy.
2. `ancore:before-navigate` może zatrzymać wyjście. `waitUntil(promise)` czeka
   na zapis; odrzucenie lub `false` zatrzymuje przejście. Przy kolejnych próbach
   obowiązuje ostatni cel. Działa to również dla automatycznego zapisu zadania
   oraz oczekujących zmian menu i Favorites.
3. Scoped `api/v1/navigation/` pobiera dane ekranu i powłoki przez istniejące
   widoki, formularze i ACL Django. Anulowanie/wersja żądania chroni przed starą
   odpowiedzią. `main.tsx` ładuje route chunk i style przed usunięciem treści.
   Nie ma parsowania HTML ani wykonywania skryptów z odpowiedzi.
4. `ancore:content-unloading` odmontowuje ekran, a trwała powłoka pozostaje.
   URL jest publikowany przed montowaniem kolejnego ekranu React. Powłoka
   otrzymuje aktualne kolekcje, uprawnienia, aktywne linki i tryb zarządzania.
   `ancore:content-loaded` zachowuje kontrakt inicjalizacji wspólnych adapterów.
5. Wstecz/Dalej odtwarza dane i przewinięcie; odrzucone opuszczenie szkicu
   przywraca wpis historii. `setPageLocation()` włącza lokalne zmiany URL
   komponentów do tej samej historii. Błąd pobrania zachowuje ekran i pokazuje
   komunikat. Konto, Workspace lub inny build w odpowiedzi wymuszają pełny
   reload, aby osobiste elementy nie przetrwały zmiany tożsamości.
6. `.main-content[aria-busy]` oznacza pobieranie. Po 180 ms pojawia się istniejący
   szkielet nad treścią i tymczasowe `inert`; szybka odpowiedź nie miga szkieletem.
   Tylko zakończenie bieżącego żądania usuwa jego stan ładowania.

`Sidebar.tsx` obsługuje menu Workspace, Ustawień, zarządzania i edytora pulpitu.
Zwijanie grup, Favorites i szerokość zachowują dotychczasowe klucze. Menu mobilne
ma backdrop, fokus i `inert` treści. Pickery kolekcji pobierają typowane wyniki
z tym samym ACL co katalogi. Gwiazdka odświeża tylko powłokę, bez resetowania
szkicu strony. Favorites używają dotychczasowej bazy i widoków z walidacją
kompletnego porządku, sesji oraz CSRF; odpowiedź API nie zawiera HTML.

Link `data-management-return` odtwarza źródłowy URL z query/hash, etykietę
oraz przewinięcie. `ancoreManagementReturn` w historii i `sessionStorage`
zachowuje zakres konta/Workspace i poprzedni poziom zarządzania. Wewnętrzne
przejścia nie nadpisują źródła. Świeży bezpośredni adres używa domyślnego celu;
reload zachowuje źródło. `AncoreApp.invalidateManagementReturn` usuwa cele
potwierdzonego usunięcia, także z kontekstu nadrzędnego. 404 przy powrocie
uruchamia domyślny katalog; zwykłe wejście do usuniętego obiektu nadal daje 404.

`layout.js` zachowuje wcześniejszy kontrakt wyłącznie dla szablonów zgodności;
przy aktywnej powłoce Reacta nie jest ładowany.

## 13. Stan w przeglądarce

„Ostatnio oglądane” w „Dla ciebie” używa serwerowej sesji Django, klucza
`for_you_recent`: maksymalnie 60 ostatnich unikalnych kombinacji konta,
Workspace, modelu i PK wraz z czasem otwarcia. Udane GET szczegółów i widoków
projektu/grupy zapisują wpis, również po częściowej nawigacji. Tytuły i URL
nie są zapisywane; aktualne rekordy przechodzą `visible_to` oraz filtr
właściciela/Workspace przy każdym odczycie. Cofnięty dostęp i usunięte rekordy
znikają z widoku. Historia jest osobna dla kont i Workspace, ograniczona do sesji
i nie synchronizuje urządzeń. Linki zadań oraz kart zawierają `task_pk`, dlatego
renumeracja nie zmienia ich celu. „Ostatnia praca” opiera się na ostatniej dacie
aktywności z `actor=request.user`, nie na dacie zmiany przez dowolnego członka.


| Stan | Miejsce i zakres w obecnym kodzie |
| --- | --- |
| Aktywne konto i Workspace | Sesja Django |
| Ulubione i kolejność | Baza: użytkownik + Workspace |
| Szerokość i zwinięcie sidebaru | `localStorage`, np. `ancoreSidebarWidth`, `ancoreSidebarCollapsed` |
| Zwijanie grup i Favorites | Dotychczasowe klucze `localStorage`, obsługiwane przez `src/shell` |
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

Usunięcie przestrzeni usuwa jej zadania i powiązaną historię, członkostwa,
czas oraz przypomnienia. Usunięcie zadania obejmuje podzadania i wymaga prawa
edycji wszystkich potomków. Fizyczne pliki są sprzątane po zatwierdzeniu transakcji
i ostatnim odwołaniu. Rollback zachowuje pliki. Usuwanie Workspace kaskaduje dane
należące do jego modeli. W Dysku kosz ustawia `deleted_at`, bez fizycznego usunięcia.
Usuwanie Workspace blokuje wiersz właściciela przed sprawdzeniem zastępstwa
i kaskadą, w jednej transakcji. Równoczesne żądania zachowują co najmniej jeden
własny Workspace wraz z jego danymi.
Ograniczenia `RESTRICT` chronią m.in. używane konfiguracje i lokalizacje Dokumentów.

## 15. Ewidencja zasobów

Główny katalog oraz GET tworzenia/edycji montują teraz moduł React.
JSON API v1 w `backend/resources/api.py` współdzieli z widokami HTML zakres,
katalog i zapis z `backend/resources/services.py`; walidacja pozostaje w `ResourceForm`.
Sesja i CSRF nadal pochodzą z Django. Szczegóły kontraktu, cyklu życia
i zgodności: [Frontend React](FRONTEND.md).

`resources.views` ogranicza każdy odczyt i zapis jednocześnie przez
`workspace_owner(request)` i `request.workplace`, w obu wariantach adresów.
`ResourceForm` dopuszcza przypisanie wyłącznie aktywnych osób z
`workplace_people`; nie przyjmuje właściciela, Workspace ani autora z POST.
`created_by` i `updated_by` wskazują faktyczne konto wykonujące operację.
Usunięcie Workspace usuwa zasoby; usunięcie przypisanej osoby lub autora
zeruje odpowiednią relację, zachowując zasób.

Opcjonalny numer ewidencyjny ma częściowe ograniczenie unikalności
`Lower(inventory_number)` + Workspace. Formularz usuwa otaczające spacje,
wyjaśnia duplikat, a zapis obsługuje także konflikt równoczesnych żądań.
Status, typ i kolejność dat mają ograniczenia bazodanowe.
Terminy i przypisanie są informacją ewidencyjną, bez automatycznych zmian statusu.

GET katalogu łączy filtry i paginację. Formularze używają scoped adresów,
więc zmiana Workspace w drugiej karcie nie zmienia celu zapisu. Nagłówek
`X-Resource-Modal: true` wybiera JSON z HTML formularza (400 dla walidacji)
lub potwierdzenie zapisu; zwykły GET otwiera katalog i okno w React.
Usuwanie wymaga POST i CSRF. Query string przekazuje wyłącznie znane parametry
katalogu; klient nie może wskazać dowolnego adresu przekierowania.

## 16. Pulpity i gadżety

`Dashboard.is_default` oznacza osobisty pulpit domyślny. Warunkowy indeks unikalny
`(created_by, workplace)` i transakcyjny `default_dashboard(request)` tworzą jeden
rekord z początkowym „Postępem pracy”, także przy równoległych pierwszych wejściach.
Kolejne odczyty nie uzupełniają usuniętych gadżetów. Strona główna oraz zwykły/scoped
`default/` używają wspólnego `detail_context` i edytora; własny link pulpitu kieruje
na scoped `default/`. Domyślny rekord można konfigurować i udostępniać jak pozostałe
pulpity, ale endpoint usuwania odrzuca go, a menu nie pokazuje tej akcji.
Osobisty domyślny pulpit nie jest powielany w gwiazdkach ani historii menu twórcy;
udostępniony domyślny pulpit innej osoby używa zwykłego linku ze slugiem.

`Dashboard.slug` to zapisany segment URL pochodzący z nazwy, unikalny w obrębie
Workspace. `backend/dashboard/identifiers.py` normalizuje nazwę przez `slugify` i transliterację
`ł/Ł`, a dla kolizji dopisuje `-2`, `-3`. Nazwy `default`, `manage`, `create`,
`search`, `groups` oraz same cyfry otrzymują prefiks `pulpit-`; nazwa bez znaków
możliwych do użycia w URL daje `pulpit`. Przy tworzeniu `Dashboard.save()` blokuje
wiersz Workspace i przydziela wolny slug, także dla równoczesnych zapisów różnych
twórców; ograniczenie bazy chroni `(workplace, slug)`. Edycja nazwy zachowuje slug,
więc zapisane odnośniki i źródła powrotu nie wygasają. PK nadal identyfikuje relacje,
gwiazdki i historię. `get_dashboard` rozpoznaje int z historycznej trasy lub tekst
ze współczesnej, zawsze w aktualnym zakresie `visible_dashboards`.
Linki przeglądu, edytora, gadżetów, menu i wyszukiwania używają slugu.
GET na dawny `/<pk>/` przekierowuje na aktualny link, zachowując query string;
przekierowanie następuje dopiero po sprawdzeniu dostępu. Numeryczne endpointy
edycji i POST zachowują zgodność. Konwerter wyklucza zastrzeżone segmenty,
więc wycofane `groups/` nadal zwraca 404 dla GET i POST. Usunięcie unieważnia
źródła powrotu zarówno po slugu, jak i PK, w zwykłym/scoped i zarządzaniu.

`Dashboard.owner` jest właścicielem Workspace z `workspace_owner(request)`,
a `created_by` faktycznym twórcą. Katalog i każdy bezpośredni endpoint najpierw
ograniczają właściciela i aktywny Workspace, następnie widoczność pulpitu.
Osobista gwiazdka nie nadaje dostępu. `DashboardMembership` zapisuje rolę w tej samej
tabeli co dotychczasowe `shared_with`. Właściciel, administrator i członek edytują
gadżety; właściciel i administrator zarządzają ustawieniami i niższymi rolami.
Widoczność i usunięcie Pulpitu pozostają przy właścicielu. Formularz udostępniania
wybiera aktywne osoby obecnego Workspace; udostępnienie jest natychmiastowe,
bez zaproszeń. Obserwator i dostęp odziedziczony z Workspace mają tylko odczyt.
Administrator nie promuje ani nie zmienia innych administratorów i właściciela.
Zwykłe, scoped i starsze adresy korzystają z tych samych kontroli ról.

Listy, liczniki, historia i gwiazdki ponownie sprawdzają dostęp;
cofnięcie udostępnienia ukrywa pulpit również w menu.
`pulpit_navigation.py` pobiera gwiazdki przez `Exists`.
Panel „Więcej pulpitów” korzysta ze wspólnego komponentu panelu Przestrzeni.
GET `dashboards/search/` (także scoped) filtruje przez `visible_dashboards`,
wyszukuje po nazwie/opisie, ogranicza frazę do 120 znaków i wynik do 20 pulpitów.
Odpowiedź zawiera escapowany HTML i `Cache-Control: private, no-store`;
puste zapytanie zwraca pustą listę. Link katalogu zachowuje frazę.
Katalog pokazuje wszystkie dostępne pulpity bez zakładek; dawny parametr `tab`
jest ignorowany, a filtry widoczności i wyszukiwania nadal ograniczają wyniki.
Ostatnie odwiedziny korzystają z `backend/dashboard/recent.py`, który
zapisuje tylko identyfikatory, osobno dla użytkownika i Workspace. Samo otwarcie
katalogu nie dopisuje historii. Pulpit domyślny jest stałym skrótem do `/`.
Grupy pulpitów, ich formularze, przypisania i routing są usunięte.
Migracja `dashboard.0009_remove_dashboard_groups` usuwa tabelę grup oraz
relacje z pulpitami; konfiguracja, gadżety, gwiazdki i udostępnienia pozostają.
Stare adresy `groups/`, `<pk>/groups/` i `manage/<pk>/groups/` zwracają 404;
historyczny parametr katalogu `group` jest ignorowany i nie trafia do nowych
linków zakładek, wyszukiwania ani paginacji.
Gwiazdka z menu korzysta z tego samego endpointu co katalog; nagłówek
`X-Pulpit-Navigation` zwraca JSON do odświeżenia aktualnego ekranu.
Fallback formularza sprawdza lokalny adres `next` przed przekierowaniem.

Dawny katalog „Zarządzaj pulpitami” jest usunięty. GET `manage/` przekierowuje
na katalog „Pulpity” w aktywnym Workspace; API strony i nawigacji zwraca ten sam
adres w polu `redirect`. Menu oraz Ustawienia nie zawierają tego wejścia.
Zwykły katalog nadal korzysta z `visible_dashboards`, a edycja wymaga odpowiedniej roli Pulpitu.
Trasy `manage/create/` i `manage/<slug>/edit|access|delete/` pozostają zgodnymi
adresami istniejących operacji. `management_url` zachowuje parametry q,
visibility, favorite i page; pusty sufiks kieruje już do zwykłego katalogu.
Bezpośrednie wejście i błędy tworzenia pokazują modal nad `index.html`.
Dawny parametr gwiazdki katalogu jest ignorowany. Zapis/usunięcie wraca
na katalog, bez osobnego trybu menu `pulpits-management`.

Edytor konkretnego pulpitu ma osobny tryb zgodności `pulpit-editor`;
powłoka React zachowuje zwykłe menu Workspace także dla starych adresów.
`editor_navigation_context` buduje jego trzy
pozycje i powrót z zachowaniem filtrów. `DashboardSettingsForm` zapisuje tylko
nazwę/opis, parametry i widoczność (tę ostatnią tylko dla właściciela),
a starszy `DashboardAccessForm` widoczność/udostępnienie w `access/`, wyłącznie właścicielowi.
Tworzenie używa pełnego `DashboardForm`. Kopiowanie pulpitów jest usunięte;
dawne endpointy kopiowania zwracają 404 w obu zakresach URL, także w zarządzaniu.
Zapisy ponownie sprawdzają role
i zwiększają rewizję pod blokadą wiersza. Usunięcie lub wyłączenie członkostwa
Workspace usuwa role Pulpitów, więc ponowne dołączenie nie przywraca ich automatycznie.
Układ zmienia wyłącznie edytor
gadżetów przez `arrange/`. Nawigacja React aktualizuje kontekst i menu konkretnego
pulpitu z odpowiedzi JSON, odświeżając nazwę, adresy i aktywną pozycję.
Źródło powrotu edytora przechowuje również wcześniejsze źródło katalogu;
powrót oraz zwykły POST przywracają odpowiedni poziom zarządzania.

Gadżet „Postęp pracy” ponownie stosuje `spaces.access.visible_to` do `SpaceTask` oglądającego,
w zakresie właściciela i aktywnego Workspace. Filtr przestrzeni sprawdza
`visible_spaces`; utrata dostępu daje komunikat bez jej nazwy, liczników ani
poszerzania zakresu. Usunięcie źródłowej przestrzeni usuwa jej filtrowane gadżety
przez CASCADE, zamiast zmieniać filtr na wszystkie zadania. Usunięcie pulpitu
usuwa wyłącznie jego konfigurację i gadżety. Postęp agreguje zadania główne
po `SpaceTask.status`, bez limitu wyników; `closed / wszystkie × 100`
jest zaokrąglany do całego procentu, a pusty zakres daje zero. `resolved` oraz
`reopened` nie są zamknięte. Wybrana przestrzeń filtruje przez `work_item__space`,
a przypisanie „me” dotyczy faktycznego oglądającego. Szablon
`dashboard/includes/work_progress.html` współdzieli wygląd z Dashboardem.

Migracja `dashboard.0010_work_progress_gadget` zastępuje starsze rodzaje jedną
kartą na niepusty pulpit, w miejscu pierwszego gadżetu. Czyści tytuł i filtry
zastępowanej karty, usuwa pozostałe stare karty oraz pola status/group_by/limit.
Zachowuje konfigurację pulpitu, jego dostępy i gwiazdki; zwiększa rewizję
zmienionych pulpitów, aby stare okno edytora nie nadpisało nowej listy kart.
Puste pulpity i istniejące karty `progress` pozostają zachowane.

Zapisy konfiguracji i układu blokują wiersz pulpitu w transakcji. Endpoint
`arrange/` wymaga pełnej, nieduplikowanej listy gadżetów tego pulpitu w 1–3
kolumnach i aktualnej `revision`. Stara rewizja daje HTTP 409, bez nadpisania
układu; klient przywraca poprzedni układ i pokazuje instrukcję odświeżenia.
Dodanie/usunięcie/edycja gadżetu oraz edycja pulpitu zwiększają rewizję.
Mutacje wymagają POST i CSRF. Backend i źródłowe modele zadań pozostają
niezmienione; pulpit nie kopiuje danych biznesowych ani historii.

## Wycofanie starszych systemów pracy (10.10.2026)

Po resecie z 18.10.2026 usunięto również historyczne modele, tabele,
mapowania importu i trasy zgodności. Pozostał katalog tagów i wspólne komponenty.
Nowe migracje wymagają pustej bazy. [Zakres i uruchomienie](DATABASE.md).

## Adapter ekranów React

`backend/core/frontend.py` rejestruje jawne serializery i dopuszczone operacje
migracji. JSON API korzysta z sesji, CSRF i aktywnego scoped Workspace;
nie wywołuje dowolnych widoków z adresu klienta. Kontrakty danych i reguły
nawigacji/zapisu opisano w [FRONTEND.md](FRONTEND.md).
Pulpity zachowują własną walidację strukturalnego JSON wyłącznie dla układu
i szybkiego dodawania gadżetu. Jawna lista wyjątków nie zmienia płaskiego
kontraktu innych formularzy. Rewizje i transakcje należą do widoków domenowych;
frontend cofa optymistyczny układ po błędzie, a usunięcie unieważnia zapisane
adresy powrotu powłoki przez `AncoreApp.invalidateManagementReturn`.

Dysk i Dokumenty korzystają z `backend/documents/frontend.py`. Formularze JSON opisują
wyłącznie autoryzowane pola, upload używa FormData, a metadane plików nie
ujawniają nazw storage. Rewizje i unieważnianie klucza edytora nadal obsługują
oryginalne widoki. Konflikt edycji Dokumentów daje HTTP 409 z zachowanym
formularzem. Chronione pobieranie, źródło/callback ONLYOFFICE i zapis sceny
tablicy pozostają poza listą proxy. Powłoka React pełnego edytora używa
oryginalnych endpointów JSON i niszczy wyspę edytora przy odmontowaniu.

Zarządzanie Workspace serializuje `backend/workplaces/frontend.py`. Jawnie dopuszczone
operacje API wywołują te same widoki zarządzania, ręcznego dodawania i linków. Wybrany Workspace
jest autoryzowany niezależnie od aktywnej sesji, bez automatycznego przełączania
przy odczycie/edycji. Role i aktywność wybranego konta sprawdzają formularze
oraz blokowane transakcje; kod Workspace jest nieedytowalny. Podpowiedzi API
zwracają dane awatara bez fragmentu HTML. Favorites należą do trwałej powłoki
React i korzystają z jawnie dopuszczonych operacji API ekranów. [Pełny kontrakt](FRONTEND.md).
