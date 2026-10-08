# Wspólne mechanizmy i przepływy

Stary moduł Tablice Kanban jest wycofany. Pozostałe opisy jego modeli,
szablonów i wspólnych komponentów są referencją historyczną; nie oznaczają
aktywnych ekranów ani endpointów. Obecne tablice Przestrzeni używają Tasks.
[Szczegóły wycofania](MODULES.md#4-wycofany-moduł-tablice-kanban).

## Wspólne zadania przestrzeni

Nowe listy, tablice i backlog korzystają z `Task` i metadanych `WorkItem`.
Numer klucza przestrzeni jest trwały i niezależny od renumerowanego `task_id`.
Dostęp nadal wyznaczają istniejące projekty, grupy i zadania. Przejścia statusów
w nowych i dotychczasowych formularzach/statusowych endpointach podlegają
konfiguracji przestrzeni. Stare pliki współdzielone po imporcie są usuwane
dopiero po ostatnim odwołaniu i zatwierdzeniu transakcji. [Szczegóły](SPACES.md).


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

`ensure_default_workplace()` tworzy Workspace tylko wtedy, gdy użytkownik nie
ma żadnego dostępnego miejsca (własnego ani przez aktywne członkostwo).
Losuje polską nazwę z `DEFAULT_WORKPLACE_NAMES` i zapisuje ją razem ze zwykłym
kodem i slugiem generowanymi przez model, rolą właściciela oraz ulubionym
Dashboardem. W transakcji blokuje wiersz użytkownika i ponownie sprawdza
dostępne Workspace, aby równoczesne pierwsze wejścia nie tworzyły duplikatów.
Kolejne wejścia, utrata sesji oraz edycja nazwy nie powodują ponownego losowania.
Istniejące Workspace, również z dawną nazwą domyślną, pozostają bez zmian.

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
Operacje JS zadań, kart i kalendarza używają adresów scoped wygenerowanych
dla otwartego ekranu. Zmiana Workspace w drugiej karcie nie zmienia ich celu.
`tasks.js` odczytuje moduł i bazowy adres z `data-task-app` oraz
`data-task-base-url`, również po częściowej nawigacji.

**Przy nowej funkcji:** sprawdź adres GET, formularz POST, odpowiedź/redirect,
zachowanie w dwóch Workspace, back/forward i link z wyszukiwania. Parametry
`view`, `project`, `folder`, `library`, `q`, filtry i paginacja są częścią
użyteczności danego ekranu, a nie przypadkowym dodatkiem URL.

## 4. Dostęp i historyczne udostępnianie

Aktywne zapytania Tasks/Planner/Documents ograniczają rekordy
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
`WorkplaceMembership` nadaje dostęp do wspólnych danych Workspace zgodnie z [TEAMWORK.md](TEAMWORK.md).
Projekty Zadań mogą mieć `visibility=private`: `tasks.access.visible_to(queryset, viewer)`
wymaga wtedy zgodności `private_owner` z faktycznym odbiorcą albo wpisu w `shared_with`,
istniejącego prywatnego właściciela oraz nadal aktywnego
dostępu do Workspace. Widoki i formularze przekazują `request.user` osobno od
właściciela danych. Zwykłe managery modeli pozostają nieograniczone na potrzeby
migracji, numeracji i operacji utrzymaniowych; nowe odczyty użytkownika muszą
korzystać z jawnego filtra widoczności. Dotyczy to również powiązanych grup, zadań,
plików, szablonów i integracji Dashboard/Kalendarza.
Grupy mają dodatkowy filtr `visibility` / `private_owner` / `shared_with`;
prywatność grupy nie omija projektu nadrzędnego. `editable_to` uwzględnia rolę
obserwatora na poziomie projektu, grupy i zadania, także dla potomków w starszych drzewach.
Prywatność `Task` zawęża dostęp odziedziczony po wszystkich rodzicach.
Szablon kopiuje tylko edytowalne grupy i zadania; obecność prywatnej grupy lub zadania
wymusza prywatny snapshot dla autora. Udostępnienia nie przechodzą do szablonu.
Formularz projektu zmienia widoczność wyłącznie dla prywatnego właściciela.
Zespół obsługują osobne endpointy `projects/<id>/team/` (GET/POST),
`projects/<id>/team/candidates/` (GET), także pod scoped URL. POST `action=share`
od razu tworzy `TaskProjectMembership` dla aktywnego członka Workspace.
Analogiczne `groups/<id>/team/` i `groups/<id>/team/candidates/` obsługują grupy
przez `TaskSectionMembership`, z zachowaniem dostępu do projektu nadrzędnego.
Zadania używają `items/<pk>/team/`, `items/<pk>/team/candidates/` i `TaskMembership`.
Nie ma zaproszeń ani endpointów akceptacji dla projektu/grupy/zadania.
Zapisy zespołu blokują Workspace i odpowiedni projekt, grupę lub zadanie; nie zapisują pól głównego formularza.
Rola `observer` zachowuje `visible_to`, ale jest wykluczona z zapisu przez
`tasks.access.editable_to(queryset, viewer)`. Ten filtr obejmuje projekt, grupy,
notatki i całe drzewa zadań wraz z plikami. Relacje formularzy edycji korzystają
z tego samego zakresu; formularz podglądu zachowuje widoczne bieżące wartości.
`require_editable` odrzuca całą mieszaną operację zbiorczą przed zapisem,
a `require_deletable_tasks` chroni również obserwowane podzadania przy kaskadzie.
Widoki szczegółów blokują każdy POST obserwatora, również komentarze i pliki.
Role projektu oraz cofnięcie dostępu opisuje [TEAMWORK.md](TEAMWORK.md).
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

Pojedyncza i zbiorcza zmiana statusu w Tasks blokuje numerację właściciela
przed odczytem i blokadą wiersza zadania. Odczyt, zapis modelu i historia należą
do jednej transakcji. Zapis statusu obejmuje tylko `status`, `is_completed`
i `completion_date`, zachowując pozostałe pola. Powtórne zamknięcie zachowuje
datę zakończenia; tylko faktyczna zmiana dodaje historię z autorem `request.user`.
Błąd zapisu historii wycofuje również status. Archiwalny, nieroutowany endpoint Kanbana
stosował tę samą blokadę także przy zmianie kolumny.

W historycznym modelu Kanbana kolumna jest oddzielona od statusu. `_set_task_column()` sprawdza,
czy kolumna należy do tablicy karty i właściciela, a następnie zapisuje relację.
Dawny endpoint przestawiania kolumn jest wyłączony.

### Dziennik pracy zadania

`TaskWorkLog` jest powiązany z trwałym PK `Task`. Osobne akcje POST
`add_work_log`, `edit_work_log` i `delete_work_log` w widoku szczegółów wymagają
`task_pk`. Widok ogranicza zadanie do właściciela aktywnego Workspace;
identyfikator edytowanego/usuwanego wpisu jest dodatkowo ograniczony do tego
zadania. Formularz nie udostępnia autora ani zadania. Dodanie ustawia autora
na `request.user`, edycja go zachowuje; historia rejestruje aktualnego aktora.
Zmiana wpisu i zapis Aktywności są jedną transakcją, edycja/usunięcie blokują
wiersz wpisu. Usunięcie zadania usuwa wpisy, usunięcie autora zachowuje je
z etykietą „Usunięte konto”. Autor Aktywności bez konta ma etykietę „System”.

Daty są świadome strefy czasowej. Formularz wymaga pełnych minut, dodatniego
przedziału i opisu; baza dodatkowo wymusza `ended_at > started_at`.
Czas wynika z różnicy chwil UTC. `TaskWorkLogForm` przyjmuje pomocnicze
`hours`, `minutes` (0–59) i `calculation_mode`. Przy `interval` (także przy
braku trybu w starszym POST) ignoruje przesłane godziny/minuty i oblicza je
z dat. Przy `duration` ignoruje przesłany początek, wymaga dodatniej sumy
godzin/minut i oblicza początek jako zakończenie minus czas. Pusty koniec
oznacza bieżącą chwilę zaokrągloną do minuty. Obliczenia po stronie serwera
odbywają się w UTC również podczas zmiany czasu. Błędne części czasu,
przepełnienie daty i nieprawidłowy koniec nie zapisują wpisu. Przy błędzie
opisu formularz zachowuje wpisany czas, wyliczone daty oraz kierunek obliczeń.
Pola pomocnicze nie są osobno przechowywane w modelu.
Agregat SQL liczy sumę całego zadania, paginacja pobiera po 25 wpisów
z autorami. Zakresy nakładające się nie są blokowane; każdy wpis wchodzi do sumy.
Warianty zwykły i scoped korzystają z tej samej walidacji. Formularz, paginacja
i przekierowanie po zapisie używają scoped URL z PK, aby inna karta przeglądarki
ani renumeracja zadania nie zmieniły celu operacji. Stare pola łącznego czasu
w `Task` nie są synchronizowane z dziennikiem.

## 7. Katalogi, filtry i wydajność

Katalogi projektów, wszystkich grup i wszystkich zadań używają `tasks/directory.py` do
wyboru `tab=private|shared|public|favorites` (domyślnie `private`). Filtr zakładki
jest nakładany po `visible_to` i ograniczeniu Workspace, przed sortowaniem,
licznikami i paginacją. Publiczne grupy dziedziczą kategorię projektu; własna
prywatna grupa trafia do „Prywatne” także w projekcie udostępnionym odbiorcy.
Katalog zadań nadal filtruje `parent__isnull=True`. Własne prywatne zadanie
trafia do „Prywatne”, publiczne dziedziczy kategorię grupy/projektu, a publiczne
bez grupy jest „Publiczne”. Filtr obejmuje dane przed liczeniem i stronicowaniem
każdego statusu. Zakładka „Nieprzydzielone” nie stosuje podziału według widoczności.
Dawny „Moje zadania” i lista konkretnej grupy nie stosują filtrów zakładek.
Stan ulubionych jest adnotacją `Exists` względem relacji `favorited_by` aktualnego
odbiorcy, bez osobnego zapytania dla każdego wiersza. Endpoint POST
`/tasks/favorites/<project|section|task>/<pk>/` i jego wariant scoped przyjmują
`favorite_action=add|remove`; operacje są idempotentne i wymagają aktualnego
dostępu do obiektu, ale nie uprawnienia edycji. Ulubione nie nadają dostępu.
Pole `user` nadal wskazuje właściciela Workspace; relacja ulubionych wskazuje
faktycznego odbiorcę `request.user`.
Wariant `task` obsługuje zadania główne; podzadania nie należą do katalogu ulubionych.

Historyczny Kanban jest wycofany: `tasks.access` deleguje jego modele do
`kanban.access`, które zwraca pusty queryset także dla właściciela.
Wyszukiwanie, Dashboard, „Dla ciebie” i kalendarz korzystają wyłącznie z Tasks.
Powiadomienia zachowują pusty typ `kanban`, żeby historyczny identyfikator nie
mógł zmienić stanu archiwalnej aktywności. Endpointy zespołu, ulubionych,
obserwowania i operacji Kanbana nie są routowane. `LegacyKanbanMiddleware`
obsługuje tylko adresy zgodności, z aktualną kontrolą dostępu Tasks.

Tasks oraz archiwalny kod Kanbana mają rozbudowane funkcje `*_window_for_request()`, które
filtrują, sortują i wycinają okno wyników po stronie serwera. Widoki używają
`select_related`, `prefetch_related`, agregacji i adnotacji do liczników.
Tasks ma osobne mechanizmy katalogów projektów, grup, tagów i zadań oraz
grupowania/paginacji po statusach.

W `_task_window_for_request()` liczności statusów są liczone jednym agregatem
na identyfikatorach przefiltrowanego zbioru. Katalogi zadań, nieprzydzielonych oraz dawny widok Moje zadania
pobierają następnie najwyżej `page_size` rekordów z każdego stanu, z tym samym
offsetem strony. Liczba stron zależy od największej liczności statusu.
Krótsze sekcje nie powtarzają ostatnich rekordów na dalszych stronach.
Zakładka „Nieprzydzielone” zachowuje URL `view=unassigned-tasks` i nakłada
`section__isnull=True` po `visible_to`,
a przed filtrami i paginacją. Parametry `task_project` i `task_section` są w nim
ignorowane, a `task_assignee` filtruje wykonawcę. Projekt zadania wynika z grupy.
Tworzenie bez grupy zapisuje właściciela przez `workspace_owner(request)`,
aktywny Workspace oraz faktycznego autora historii; nie tworzy zastępczego projektu/grupy.
Historyczny klucz preferencji sidebaru `tasks-my` pozostaje zachowany, ale wskazuje
zakładkę nieprzydzielonych. Linki `directory_tabs(..., include_unassigned=True)`
łączą ją z czterema kategoriami `view=all-tasks`, zachowują wspólne filtry
i zerują stronę; wejście do nieprzydzielonych usuwa filtry projektu i grupy.
Menu boczne oznacza „Zadania” jako aktywne w obu widokach.
Stary URL `my-tasks` zachowuje swój filtr osoby.
Zakres właściciela, Workspace, wykonawcy i zadań głównych jest ustalany przed
filtrowaniem, agregacją i paginacją.

Wycofane widoki Kontaktów i Firm zachowują historyczny kod okien wyników. Dysk używa `Paginator`;
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

## 8. Pola i terminy projektów

Źródła: [modele Tasks](../tasks/models.py), [formularze](../tasks/forms.py),
`_project_choices()` i `_decorate_project_dates()` w głównych widokach.

Status/etap/kondycja mają stałe opcje. Lista i formularze uwzględniają także
historyczne wartości zapisane w widocznych projektach właściciela/Workspace.
Nie można dodać nowej własnej opcji przez dawne formularze konfiguracji;
`/settings/project-fields/` jest usunięty. Źródło jest tekstem, a formularz
podpowiada źródła z dostępnych projektów i przyjmuje ręcznie wpisaną wartość.

Opisy terminu i `due_highlight` pozostają wyliczane z daty. Nie ma modeli
słowników ani reguł progów/kolorów. Migracja `tasks/0063` usuwa konfigurację,
bez zmiany pól statusu, etapu, kondycji, źródła lub dat istniejących projektów.
Historyczne migracje tworzące słowniki pozostają częścią łańcucha migracji.
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
| Pliki i zdjęcia komentarzy Tasks/Kanban | `PRIVATE_DOCUMENT_ROOT/comment_images/<moduł>/`, losowe nazwy, kontrolowane pobieranie/podgląd |
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
historię, projekty/grupy, tagi, wydarzenia,
Workspace, miejsca nawigacji oraz dyski/foldery/pliki. Wycofane katalogi Kontaktów
i Firm nie są przeszukiwane; firma pozostaje metadanymi istniejącego projektu.
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
stany pusty/ładowanie/błąd oraz nawigację po wynikach. Wyniki pojawiają się
w rozwijanym panelu pod polem górnego paska; przyciski typów filtrują pobrane
wyniki bez zmiany uprawnień ani limitów serwera.

GET `/global-search/?recent=1` przy pustej frazie zwraca do 8 ostatnio oglądanych
zadań, projektów i grup Tasks (bez historycznego Kanbana). Korzysta z identyfikatorów
`dashboard.recent` zapisanych dla konta i Workspace w bieżącej sesji.
Przy każdym odczycie ponownie stosuje `workspace_owner`, Workspace i `visible_to`;
usunięte elementy oraz te, do których cofnięto dostęp, nie trafiają do odpowiedzi.
Otwarcie bieżącej Przestrzeni również zapisuje jej projekt w tej historii,
po sprawdzeniu uprawnień i wyrenderowaniu widoku. Tytuły i numery są pobierane
z aktualnych rekordów, a linki zadań zawierają
`task_pk`. Odpowiedź ma `Cache-Control: no-store`; frontend nie zapisuje wyników
w localStorage. Zwykłe puste i jednoznakowe zapytania nadal nie wykonują wyszukiwania.

## 11. Historia a powiadomienia

`TaskActivity`, `KanbanActivity` i `ContactActivity` są historią obiektów.
Centrum powiadomień (`dashboard/notification_service.py`) odczytuje wyłącznie
komentarze (`kind='comment'`) Zadań, ważne oczekujące zaproszenia
oraz osobiste przypomnienia. Wpisy historii (`kind='system'`), np. utworzenie,
edycja lub zmiana statusu, pozostają tylko w historii obiektu. Nie trafiają
do żadnej zakładki powiadomień, liczników ani akcji osobistych i zbiorczych,
również gdy mają wcześniejszy `NotificationState` lub `ActivityInterest`.
Zmiana nie usuwa historii ani dawnych stanów i nie wymaga migracji.
GET może utworzyć brakujące dostawy osiągniętych przypomnień.
`dashboard.NotificationState` przechowuje osobisty stan odczytu, archiwum i usunięcia,
z FK do dokładnie jednego źródła oraz unikalnością użytkownik + źródło.
Usunięcie źródła usuwa jego stan przez CASCADE.

Domyślny zakres obejmuje wszystkie dostępne Workspace oraz własne starsze rekordy
bez Workspace; filtr pozwala wybrać pojedynczą dostępną przestrzeń.
Każde pobranie i każda akcja ponownie sprawdzają członkostwo oraz właściciela
rekordu zgodnego z właścicielem Workspace. Sam wpis `NotificationState` nie daje
dostępu. Zaproszenia do Workspace korzystają z `pending_invitations_for_user()`
i są widoczne przed dołączeniem tylko dla odbiorcy. Filtr zaproszeń i licznik
dzwonka obejmują wyłącznie te zaproszenia; zakończone i wygasłe znikają.
Projekt i grupa nadają dostęp bezpośrednio przez członkostwo, bez wpisu
w powiadomieniach wymagającego decyzji odbiorcy.

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
Udostępnienia projektów i grup nie tworzą zaproszeń w powiadomieniach;
historyczne rekordy tych zaproszeń są pomijane przez listę, liczniki i akcje.
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

### Pliki i zdjęcia w komentarzach
`TaskCommentImage` i `KanbanCommentImage` zachowują historyczne nazwy, ale przechowują
wszystkie załączniki komentarzy. Mają rozmiar `file_size` i FK do aktywności (`images`),
nie do ogólnych załączników zadania. Wspólny `core/comment_images.py` waliduje
całą partię przez `validate_comment_attachments()` w `core/upload_validation.py`
(wspólna lista `ATTACHMENT_ALLOWED_EXTENSIONS`, łącznie 10 plików i `MAX_ATTACHMENT_SIZE`). Dopiero potem zapisuje komentarz,
wzmianki i pliki w jednej transakcji. Przy rollbacku usuwa nowe pliki;
usunięcie aktywności/zadania usuwa pliki dopiero po zatwierdzeniu transakcji.

`/<moduł>/comment-images/<pk>/` i scoped odpowiednik wymagają zalogowania,
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
Nowe komentarze obserwowanego elementu oraz zadań/kart w obserwowanym projekcie
otrzymują `ActivityInterest` z odbiorcą i flagami `mentioned`/`followed`.
Dotyczy to także komentarzy do nowo tworzonych zadań i podzadań projektu.
Samo utworzenie, edycja i operacje zbiorcze nie tworzą dostaw historii do
obserwujących. Zmiany metadanych projektu również nie generują powiadomień.
Własne działania są pomijane.
Zapis komentarza i jego dostaw odbywa się w jednej transakcji.

Nie powstaje drugi wpis w centrum: filtry „Wzmianki” i „Obserwowane” wybierają
istniejące aktywności, zachowując wspólny odczyt, archiwum, usunięcie, paginację
i snapshoty operacji zbiorczych. „Wszystkie” zawierają komentarze ze wszystkich
dostępnych Workspace. Rozpoczęcie obserwowania nie dostarcza wstecz komentarzy;
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

1. `canNavigatePartially()` sprawdza origin i listę dozwolonych ekranów,
   normalizując `/workplaces/<slug>/<moduł>/` do bazowej ścieżki modułu.
2. Zwykłe kliknięcia oraz formularze GET korzystają z `navigate()`. Pobieranie
   HTML przerywa poprzedni request; spóźniona odpowiedź nie nadpisuje nowego ekranu.
3. `ancore:before-navigate` pozwala anulować opuszczenie niezapisanego zadania.
   Przed podmianą `ancore:content-unloading` usuwa listenery szczegółów zadania/karty.
4. Kod wczytuje brakujące style, podmienia kontener strony z modalami oraz
   komunikaty. Ustawia URL przed inicjalizacją, synchronizuje aktywne linki menu
   według adresów i wykonuje skrypty inline raz, z pominięciem danych JSON.
   Zewnętrzne skrypty są ładowane tylko raz; równoczesne przejścia współdzielą
   oczekujące pobrania.
5. Aktualizuje tytuł, historię, przewijanie i ikony, a następnie wysyła
   `ancore:content-loaded`. Wstecz/Dalej także podmienia treść. Odrzucenie wyjścia
   z niezapisanego zadania przywraca pozycję historii i zachowuje formularz.
6. Boczne menu i dokument przeglądarki pozostają na miejscu. Lista przestrzeni
   w menu jest synchronizowana z odpowiedzią serwera: nowe linki są dodawane,
   nieobecne usuwane, a nazwy, awatary i kolejność aktualizowane. Grupa zachowuje
   stan zwinięcia; istniejące linki i przycisk „Więcej przestrzeni” zachowują
   swoje elementy. Delegowana obsługa kliknięć zamyka menu na telefonie także
   dla nowych linków. Pobieranie oznacza
   `.main-content` przez `aria-busy`. `requestContentLoading()` po 180 ms pokazuje
   szkielet wyłącznie nad treścią i wyłącza zasłonięty kontener przez `inert`.
   Zakończenie bieżącego żądania usuwa szkielet, timer i tymczasowy stan kontenera;
   zakończenie starszego, anulowanego żądania nie ukrywa wskaźnika nowszego.
   Szybkie odpowiedzi nie pokazują placeholderów ani nie mają sztucznego opóźnienia.
   Nieobsługiwane adresy i błędy pobrania zachowują pełną nawigację.

Powłoka oznacza konto i Workspace przez `body[data-account-id]` oraz
`body[data-workplace-id]`. Zmiana któregokolwiek z nich w odpowiedzi wymaga
pełnego przeładowania, aby osobiste elementy, ulubione i adresy operacji
nie pozostały z poprzedniego kontekstu. Tak samo działa odpowiedź bez powłoki
aplikacji (np. logowanie) lub z edytorem `data-app-full-navigation`.

Lista obejmuje Dashboard, „Dla ciebie”, ustawienia i pola projektów, zarządzanie Workspace,
profil, katalogi Zadań, grupy, szczegóły zadań/podzadań, szablony
projektów, Kalendarz oraz katalogi Dysku i Dokumentów. Działa dla
bazowych i scoped URL, łącznie z query string filtrów i paginacji. Otwieranie
zadania z Kalendarza, powiadomień i powrót ze szczegółów używają tego samego API.
Pobieranie plików, zewnętrzne linki, nowe karty, akcje POST, przełączanie konta
lub Workspace i pełne edytory nadal mają własne przepływy. Nowy ekran wymaga
jawnego dopisania do listy. Tasks ma także własną podmianę pojedynczego stanu katalogu.

Przy nowym skrypcie zachowaj inicjalizację na pierwszym wejściu i po podmianie,
sprawdzanie istnienia elementu oraz sprzątanie/ochronę listenerów.
Nie opieraj całej inicjalizacji wyłącznie na jednorazowym `DOMContentLoaded`.

Linki `data-management-return` w menu zarządzania Workspace, przestrzeniami i pulpitami
wracają do miejsca wejścia. `layout.js` zapisuje źródłowy URL z query/hash,
etykietę i przewinięcie w `history.state.ancoreManagementReturn` oraz
`sessionStorage`, w zakresie konta i aktywnego Workspace. Wewnętrzne przejścia,
filtry i okna zarządzania nie nadpisują źródła; historia odtwarza kontekst
właściwego wpisu. Powrót odtwarza przewinięcie po inicjalizacji docelowego UI.
Adres musi być lokalny i obsługiwany przez częściową nawigację. Świeże
bezpośrednie wejście używa domyślnego linku z szablonu; reload oraz formularze
wewnątrz zarządzania zachowują wcześniej zapamiętane źródło.
Po potwierdzonym usunięciu pulpitu odpowiedź JSON zawiera
`invalidated_return_paths` dla zwykłego i scoped przeglądu/edytora.
`pulpits.js` przekazuje je do `AncoreApp.invalidateManagementReturn` przed
odświeżeniem listy. `layout.js` usuwa pasujące cele także z zagnieżdżonego
kontekstu, bieżącego wpisu historii i osobistego `sessionStorage`;
pozostałe cele oraz filtry zachowuje. Powrót dotyczący usuniętego pulpitu
korzysta wtedy z domyślnego katalogu. Jeśli stary wpis historii lub usunięcie
w innej karcie pozostawi nieaktualny cel, odpowiedź 404 przy kliknięciu
`data-management-return` uruchamia domyślny powrót w powłoce aplikacji.
Bezpośrednie wejście na adres usuniętego pulpitu nadal zwraca 404.

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
  jest `SET_NULL`. Kanban blokuje usuwanie przestrzeni/tablicy zawierającej
  prywatne karty: najpierw trzeba usunąć karty, aby nie ujawnić ich jako osieroconych.
  Usunięcie publicznej przestrzeni/tablicy zachowuje dawne przeniesienie kart poza tablicę.
- Usunięcie kolumny Kanban w aktywnym widoku usuwa jej karty.
- Podzadania/podkarty mają rodzica z `CASCADE`.
- Pliki/foldery/dyski używają `RESTRICT` dla ochrony niepustych
  kontenerów. Workspace ma relacje kaskadowe; jego usuwanie jest osobnym
  scenariuszem od usuwania niepustego folderu/dysku.

Przed zmianą usuwania czytaj zarówno model, jak i akcję widoku oraz test.
Nie wyciągaj zachowania całego scenariusza tylko z jednej deklaracji `on_delete`.

## 15. Ewidencja zasobów

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
lub potwierdzenie zapisu; zwykłe wejście renderuje katalog z otwartym oknem.
Usuwanie wymaga POST i CSRF. Query string przekazuje wyłącznie znane parametry
katalogu; klient nie może wskazać dowolnego adresu przekierowania.

## 16. Pulpity i gadżety

`Dashboard.owner` jest właścicielem Workspace z `workspace_owner(request)`,
a `created_by` faktycznym twórcą. Katalog i każdy bezpośredni endpoint najpierw
ograniczają właściciela i aktywny Workspace, następnie widoczność pulpitu.
Osobista gwiazdka nie nadaje dostępu. Tylko twórca może edytować
konfigurację, usuwać pulpit oraz zarządzać gadżetami. Formularz udostępniania
wybiera aktywne osoby obecnego Workspace; udostępnienie jest natychmiastowe,
bez zaproszeń, a pozostali użytkownicy mają tylko odczyt.

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
Ostatnie odwiedziny korzystają z `dashboard/recent.py`, który
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

`management_context` zawęża `visible_dashboards` do `created_by=request.user`.
Nowy katalog nie rozszerza prawa edycji; bezpośrednie endpointy nadal wymagają
widoczności i twórcy. Trasy `manage/create/` i `manage/<pk>/edit|access|delete/`
korzystają z tych samych operacji, z jawnym parametrem `management=True`.
`management_url` zachowuje wyłącznie parametry q, visibility, favorite i page,
budując docelowy adres w aktywnym Workspace. Bezpośrednie wejście oraz błędy
tworzenia renderują `manage.html` pod modalem. Zapis/usunięcie wraca do katalogu.
Ostatnia zmiana pochodzi z `Dashboard.updated_at`, nie z aktywności zadań.
Tryb `pulpits-management` korzysta ze wspólnego mechanizmu źródła powrotu;
nie nadpisuje źródła podczas filtrowania, paginacji i pracy w modalu.

Edytor konkretnego pulpitu ma osobny tryb `pulpit-editor`; wejście z nazwy
w zarządzaniu otwiera gadżety. `editor_navigation_context` buduje jego trzy
pozycje i powrót z zachowaniem filtrów. `DashboardSettingsForm` zapisuje tylko
nazwę/opis, a `DashboardAccessForm` widoczność/udostępnienie w `access/`.
Tworzenie używa pełnego `DashboardForm`. Kopiowanie pulpitów jest usunięte;
dawne endpointy kopiowania zwracają 404 w obu zakresach URL, także w zarządzaniu.
Wszystkie konfiguracje wymagają
twórcy i zwiększają rewizję pod blokadą wiersza. Układ zmienia wyłącznie edytor
gadżetów przez `arrange/`. `layout.js` wymienia menu konkretnego pulpitu przy
częściowej nawigacji, odświeżając nazwę, adresy, aktywną pozycję i fokus.
Źródło powrotu edytora przechowuje również wcześniejsze źródło katalogu;
powrót oraz zwykły POST przywracają odpowiedni poziom zarządzania.

Gadżet „Postęp pracy” ponownie stosuje `visible_to` do Tasks oglądającego,
w zakresie właściciela i aktywnego Workspace. Filtr przestrzeni sprawdza
`visible_spaces`; utrata dostępu daje komunikat bez jej nazwy, liczników ani
poszerzania zakresu. Usunięcie źródłowej przestrzeni usuwa jej filtrowane gadżety
przez CASCADE, zamiast zmieniać filtr na wszystkie zadania. Usunięcie pulpitu
usuwa wyłącznie jego konfigurację i gadżety. Postęp agreguje zadania główne
po kanonicznym `Task.status`, bez limitu wyników; `closed / wszystkie × 100`
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
