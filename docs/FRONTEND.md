# Frontend React i backend Django

## Zakres migracji

Interfejs aktywnej aplikacji korzysta z Reacta i TypeScriptu. Przeniesione ekrany:

- **Zasoby:** katalog, filtry, sortowanie, paginacja, kolumny i pełne CRUD.
- **Kalendarz:** miesiąc/tydzień/dzień/rok, plan, filtry, wydarzenia i terminy zadań.
- **Dla ciebie** oraz centrum **Ustawień**.
- **Przestrzenie:** katalog, kreator szablonu, formularze, awatary,
  podsumowanie, lista zadań, tablica, backlog, sprinty, oś czasu, raporty,
  ustawienia dostępu i konfiguracja statusów/typów/pól.
- **Szczegóły zadania Przestrzeni:** właściwości z automatycznym zapisem,
  komentarze ze wzmiankami i plikami, załączniki, podzadania, dziennik pracy,
  członkowie/role oraz historia.
- **Zespoły:** katalog, szczegóły, formularz i członkostwa.
- **Tagi Przestrzeni:** katalog, wyszukiwanie, filtry, sortowanie, doładowywanie po 20,
  układ/szerokości kolumn, tworzenie/edycja, informacje i notatki.
- **Filtry zadań:** wyszukiwanie podstawowe i zaawansowane, katalog,
  zapis/edycja/kopia definicji, osobiste gwiazdki i udostępnianie.
- **Pulpity:** katalog, pulpit domyślny, przegląd, ustawienia,
  dostępy oraz edytor gadżetów z katalogiem, siatką 12 kolumn, przeciąganiem i zmianą rozmiaru.
- **Dysk i Dokumenty:** listy/kafelki, filtry i wyszukiwanie, formularze, upload,
  podglądy, przenoszenie, gwiazdki, kosz, szablony, edytor tekstowy Ancore
  i powłoka pełnych edytorów z edycją nazwy oraz stanem zapisu.
- **Zarządzanie Workspace:** katalog, tworzenie, ustawienia, awatary/kadrowanie,
  członkowie i role, ręczne dodawanie istniejących kont, linki do dołączenia
  z potwierdzeniem oraz jawne przełączanie kontekstu.
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

Kalendarz przypisuje wydarzenia do lokalnych dni z wyłączną granicą końca:
wydarzenie kończące się o północy nie pojawia się w następnym dniu ani jego
kolumnie godzinowej. Punktowe terminy zadań (`start == end`), również o północy,
pozostają widoczne w dniu terminu. Granice dni zachowują zmianę czasu letniego
i zimowego; wydarzenia całodzienne pozostają poza siatką godzinową.
Godziny wydarzeń są wyświetlane w strefie przeglądarki i wysyłane z jawnym
offsetem/UTC. Zapis samego opisu zachowuje oryginalne chwile, sekundy oraz
drugie wystąpienie godziny po cofnięciu zegara. Nowe lub zmienione godziny
nieistniejące/dwuznaczne przy zmianie czasu wymagają poprawienia w formularzu.
Wydarzenia całodzienne zachowują daty kalendarzowe z API niezależnie od strefy
przeglądarki; ich zapis nadal normalizuje granice w Django. Te same zasady
obowiązują w React i adapterze `calendar.js`.

## Proces Kanban i blokady Przestrzeni

`spaces/WorkflowBoard.tsx` zastępuje tabelę statusów tablicą w sekcji
`statuses`. `spaces/workflow-board.ts` przekształca ten sam formset w węzły
i przejścia oraz aktualizuje szkic `ConfigurationForm`; zapis nadal wysyła
pełną konfigurację i rewizję. Ukryte pola `position_x`/`position_y` przyjmują
liczby całkowite 0–20000 i odpowiadają opcjonalnemu `position: {x, y}` statusu.
Pominięcie tych pól w starszym żądaniu zachowuje zapisany układ. Oba puste
pola usuwają położenie; pojedyncza współrzędna jest błędem. Istniejące
konfiguracje bez położenia otrzymują domyślny układ przy renderowaniu.
Węzły HTML i strzałki SVG korzystają z istniejącego Reacta, bez biblioteki grafów.
Przesuwanie uwzględnia powiększenie tablicy i wspólną skalę aplikacji.

`tasks/TaskWorkflow.tsx` renderuje bieżący etap i akcje z `item.transitions`.
`useTaskSave.changeStatus` zapisuje konkretny cel z bieżącym szkicem pól,
`autosave_fields` i snapshotem położenia. UI zmienia potwierdzony etap po
odczycie serwera. Błąd POST zachowuje cel do ponowienia; po zatwierdzonym POST
i błędzie GET kolejne przejścia są wyłączone do odświeżenia, które nie powtarza
mutacji. Odświeżenie po komentarzu lub podzadaniu również synchronizuje
snapshot i dostępne przejścia hooka. Natywny fallback wysyła pojedynczy cel
przyciskiem; adapter czeka na zapis innych pól przed wysłaniem formularza.

Kolumny Page API udostępniają `flow_stage`, `wip_limit`, `wip_count`,
`wip_full` oraz `policy`. Licznik obejmuje dostępne karty przed filtrowaniem,
a serwer egzekwuje pojemność całej kolumny bez ujawniania prywatnych kart.
`src/spaces/kanban.ts` współdzieli podpowiedzi i wstępną walidację ruchu
z menu, przeciągania oraz tworzenia. Zmiana kolejności w tej samej kolumnie
nie wymaga wolnego miejsca. Walidacja Django pozostaje rozstrzygająca.

`BlockDialog` używa wspólnego `Modal`, `Select` i API stron. Odczyt
`tasks/<key>/?block=1` zwraca typ `space-block` z konkretnym zadaniem,
również podzadaniem, i osobami mającymi do niego dostęp. Zwykły adres
podzadania nadal przekierowuje do zakładki podzadań rodzica. Zapis wysyła
`source_status`, `source_in_backlog` i `source_blocked_revision`; zmiany
statusu/planowania wysyłają dwa pierwsze pola. Po udanym POST i błędzie
odświeżania dialog ponawia tylko GET. Autosave szczegółów zachowuje nowy
snapshot także wtedy, gdy zamknięcie automatycznie usuwa kartę z backlogu,
a następujący odczyt się nie uda.

Tablica odświeża dane po odzyskaniu fokusu okna, gdy nie trwa zapis,
otwarty dialog ani przeciąganie. Nie jest to synchronizacja w czasie
rzeczywistym. Pierwszy render Django zachowuje natywne formularze blokady
i jej usuwania oraz pola snapshotu. Semantykę pól i migracji opisuje
[proces Kanban](SPACES.md#kanban-proces-pracy-wip-i-blokady).

## Raporty Przestrzeni

`src/spaces/ReportsView.tsx` renderuje zakładkę Raporty we wspólnej powłoce
Przestrzeni. Dane `data.reports` dostarcza `backend/spaces/reports.py` przez
istniejące API stron i `spaces/frontend.py`; obliczenia i kontrola dostępu
pozostają w Django. Widok raportów ma osobną ścieżkę odczytu w `detail_context`,
bez dekorowania i limitowania zwykłej listy zadań. Pierwszy render zachowuje
szablon `spaces/reports.html`.

Wykres SVG ma równoważną tabelę danych i opis serii. Filtry korzystają
ze wspólnego selektora, a przejścia i odświeżanie z istniejącego API stron.
Eksport CSV to bezpośrednie pobranie z adresu przestrzeni, z ponowną kontrolą
ACL, bez przechwytywania pobrania przez nawigację Reacta. Znaczenie okresów,
przypisań i ograniczenia historii opisują [Raporty przestrzeni](SPACES.md#raporty-przestrzeni).

## Doładowywanie listy zadań Przestrzeni

Page API dla `view=list` zwraca `pagination: null` oraz w każdej pozycji
`columns` pełne `count`, bieżące `loaded_count` i `more_url` (pusty po końcu).
Domyślnie wczytuje 20 zadań na status. Parametry `list_limit_<klucz statusu>`
określają liczbę pozycji danej grupy; serwer ogranicza je do liczby dostępnych
wyników. `spaces/list_window.py` stosuje `ROW_NUMBER()` po statusie już po
widoczności, filtrowaniu i sortowaniu. Stary parametr `page` jest ignorowany
na tej liście. Pozostali odbiorcy paginacji zachowują swój kontrakt.

Oś czasu (`view=timeline`) zwraca `pagination: null` i ignoruje `page`.
Domyślnie wczytuje 20 zadań po ograniczeniu widoczności, filtrach i sortowaniu.
`timeline_limit` rozszerza ten sam uporządkowany zakres; `group_limit` ogranicza
wartość do liczby dostępnych wyników. Obiekt `timeline` zawiera `count`,
`loaded_count` i `more_url` obok dat. Kolejne odczyty zwiększają limit o 20
i ponownie sprawdzają dostęp; `more_url` jest pusty po ostatniej partii.

Backlog (`view=backlog`) również zwraca `pagination: null`. Wczytuje po 20
otwartych zadań osobno dla kolejki bez sprintu i każdego otwartego sprintu.
`spaces/backlog_window.py` stosuje okno SQL po `sprint_id` po ograniczeniu
widoczności, filtrów i kolejności. Parametry `backlog_limit_backlog` oraz
`backlog_limit_sprint_<id>` rozszerzają wyłącznie wskazaną grupę, ignorując `page`.
API zwraca `backlog_loaded_count` i `backlog_more_url`, a sprinty mają
`loaded_count` i `more_url`. Pełny licznik sprintu w kolejce planowania to
`visible_count - finished_count`; ukończone zadania pozostają w podsumowaniu
postępu. Planowanie zbiorcze i zmiana kolejności walidują ten sam wczytany
zakres. Limit pojedynczej operacji zbiorczej nadal wynosi 100 zadań.

Tablica (`view=board`) również zwraca `pagination: null` i ignoruje `page`,
ale wczytuje od razu wszystkie dostępne, przefiltrowane zadania tablicy.
React i pierwszy render Django nie pokazują dolnego paska stron.
Przeciąganie i menu kolejności używają tego samego pełnego zakresu tablicy.

Kolumny tablicy udostępniają `create_item_url` dla uprawnionych osób
(w Scrum tylko przy aktywnym sprincie). Adres formularza `items/create/`
zawiera `view=board`, osobny `initial_status` i parametry filtrów/sortowania.
`initial_status` ustawia początkową wartość pola Status, bez nadpisywania
filtra `status`. `DetailPage` otwiera istniejący `FormDialog`; zapis wraca
do tablicy, a parametry inicjalizacji nie trafiają do adresu powrotu.
Serwer ponownie waliduje status, planowanie i dostęp podczas zapisu.

`DetailPage` pobiera rozszerzony obraz listy, backlogu lub osi czasu z `more_url` przez istniejący
`pageRequest`, bez ponownego montowania grup/wierszy. Jednoczesne odczyty
i zapisy są blokowane, a odejście ze strony anuluje żądanie. Dopiero sukces
aktualizuje URL, liczniki i dane; błąd pozwala powtórzyć ten sam odczyt.
Aktualny adres zachowuje zakres również przy odświeżeniu po akcji i otwieraniu
formularza zadania. Zmiana sortowania lub filtrów usuwa limity grup i osi czasu.
`TimelineView` zachowuje zamontowaną tabelę, skalę i przewinięcie, przekazując
stan zapisu dat do wspólnego przycisku; odczyt blokuje edycję dat, a zapis doładowanie.
Wyszukiwanie osi także usuwa `timeline_limit`.
Pierwszy render Django pokazuje te same limity i linki, z pełną nawigacją
po ich kliknięciu bez Reacta.

## Doładowywanie tagów Przestrzeni

Page API dla `view=tags` zwraca w `window` pełne `total_tags`, bieżące
`loaded_count` i `more_url`. `tasks.tag_directory` wczytuje pierwsze 20 tagów
po ograniczeniu do dostępnej Przestrzeni, wyszukiwaniu, filtrach i sortowaniu.
Parametr `tags_limit` rozszerza ten sam uporządkowany zakres, korzystając
z istniejącego `group_limit`; stare `page` i `page_size` są ignorowane.
Kolejny URL zwiększa zakres o 20, zachowuje filtry i zwykły/scoped adres,
a po końcu jest pusty. Każdy odczyt ponownie sprawdza dostęp.

`TagsPage` używa `pageRequest` i wspólnego paska `work-list-more` pod tabelą.
Doładowanie zachowuje zamontowane wiersze, zaznaczenia dostępnych tagów
oraz pionowe i poziome przewinięcie. Żądanie jest anulowane po odejściu;
błąd pozostawia dane i URL, umożliwiając ponowienie. Rozszerzony URL trafia
także do tworzenia, edycji, usuwania i notatek, aby zapis nie skracał listy.
Zmiana wyszukiwania, filtrów lub sortowania usuwa `tags_limit`.
Pierwszy render Django używa `spaces/load_more.html` z etykietą końcową
„Wszystkie tagi”; nie wyświetla strzałek stron ani wyboru liczby wierszy.

## Strona ustawień Przestrzeni

[`spaces/SettingsPage.tsx`](../frontend/app/src/spaces/SettingsPage.tsx) łączy
pola główne, członków, awatar oraz konfigurację zadań na osobnej stronie.
Powłoka otrzymuje tryb `space-settings` i `space_settings` z autoryzowanymi
linkami; `shell/Sidebar.tsx` zastępuje menu Workspace czterema sekcjami:
`main` („Ustawienia”), `members` („Udostępnienia”), `types` („Typy zgłoszeń”)
i `statuses` („Proces pracy”). Menu nie dodaje nagłówków ani linku powrotu;
typy i proces zależą od uprawnień konfiguracji. Sekcja `fields` pozostaje ukryta.
`useShellLayout` utrzymuje osobne zwinięcie menu ustawień podczas wizyty:
na desktopie początkowo pokazuje nazwy sekcji i nie nadpisuje preferencji
`ancoreSidebarCollapsed` zwykłego menu. Wyjście przywraca tę preferencję,
a ponowne wejście znów rozwija sekcje. Pierwszy render również pomija
zapisane zwinięcie w trybie `space-settings`.
Wejścia są normalizowane do `?view=settings#<sekcja>`. Fragment wybiera sekcję
i zachowuje historię Wstecz/Dalej; starsze `#configuration`
i `#fields` mapują na `types`, a `#statuses` na Proces pracy.
Zdarzenie `ancore:space-settings-tab` synchronizuje aktywny
wiersz menu. Pierwszy render menu zapewnia
`core/includes/space_settings_sidebar.html`. Centrum Ustawień otrzymuje `spaces`
z widocznymi przestrzeniami aktywnego Workspace i wyświetla ich linki w kategorii
Workspace, także w widoku Ogólne.

Dane sekcji są ładowane przy jej pierwszym otwarciu, a formularz głównych
ustawień pozostaje zamontowany po ukryciu panelu. `EmbeddedForm`
z `forms/FormDialog.tsx` współdzieli pola, upload,
walidację i zapis z `FormDialog`. `SpaceForm.inline_avatar` udostępnia
w „Ustawienia” ten sam `shared/AvatarControl` co Profil, z wariantem `space`,
nazwami pól `avatar_photo*` i dotychczasową pulą ilustracji Przestrzeni. Wybrany
awatar i kadr należą do formularza głównego, a picker pozostaje oknem nad stroną.
Zapis łączy pola Przestrzeni i awatar w jednej transakcji.
`ConfigurationForm` renderuje typy zgłoszeń przez
[`spaces/ConfigurationTable.tsx`](../frontend/app/src/spaces/ConfigurationTable.tsx).
Proces pracy korzysta z osobnego `WorkflowBoard` opisanego wyżej.
Tabela korzysta z klas i ról wzorca `Members` oraz takiego samego paska działań
i bocznych odstępów jak „Udostępnienia”. Zaznaczenie jednego wiersza włącza
„Edytuj”, jednego lub kilku — „Usuń”. „Dodaj typ” jest obok po lewej,
a „Zapisz” i „Anuluj” po prawej (`member-access-toolbar`,
`member-access-save-actions`). Nie ma menu wierszy, licznika ani dolnej stopki.
Obie tabele używają wariantu `space-settings-table-body`: wypełniają dostępną
wysokość i przewijają się we własnym kontenerze, z `--app-page-padding-x`
po bokach. Dla typów odpowiada za to `work-configuration-sheet--toolbar`.
Pierwszy render Django ma te same klasy i układ; rozwijany fallback zachowuje
linki natywnego usuwania. Formularz głównych ustawień zachowuje własne odstępy.
Typy mają kolumny `key`, `label` i `description`; ikona jest przed nazwą
w komórce `label`, jak na liście Przestrzeni. Glif tabeli pochodzi z `choices[].icon` wybranej opcji pola
formularza. `TypeForm` udostępnia ikony przez wspólny `VisualSelect`, w tym
domyślną opcję zależną od klucza; opis jest opcjonalnym polem tekstowym.
React otrzymuje `type_icon_defaults` z kanonicznego `ISSUE_TYPE_ICONS`
w `spaces.defaults`, aby także szkic zmienionego klucza miał poprawny symbol.
Nie utrzymuje osobnej mapy ikon typów. Przycisk „Dodaj typ”, nazwa lub „Edytuj”
otwierają pojedynczy formularz we wspólnym `Modal`.
[`spaces/TypeFields.tsx`](../frontend/app/src/spaces/TypeFields.tsx) układa
podgląd ikony z „Zmień” po lewej, a nazwę, opis i klucz po prawej, według
struktury głównych ustawień. Pola tekstowe nadal używają `FieldControl`;
`label` jest jawnie w `app-form-heading`, bez zmiany nazwy przesyłanej do Django.
Picker ikon używa wspólnego `Dropdown`, serwerowych `choices` oraz układu
`emoji-picker` z Pulpitów: wyszukiwarki, opcji domyślnej, siatki ośmiu kolumn
i dolnego podglądu. Wszystkie 24 symbole mają wspólne kolory w `tasks.css`.
Wyszukiwanie normalizuje polskie znaki i wielkość liter; jego zdarzenia nie
oznaczają szkicu formularza. Klawiatura obsługuje strzałki, Home/End, Enter
oraz Escape. Ukryte pole
zachowuje prefiks formsetu, a zmiana wartości zgłasza standardowe zdarzenia
formularza. Domyślna ikona reaguje na zmianę klucza, jawnie wybrana pozostaje.
Pierwszy render używa tej samej siatki i natywnego pola w rozwijanej sekcji „Zmień”.
Pusty dodatkowy formularz Django służy jako schemat dodawania i nie jest
wierszem tabeli. Kolejne pozycje klonują ten schemat z nowym prefiksem
i zwiększają `TOTAL_FORMS`; obowiązuje serwerowy limit 30 aktywnych typów.
„Usuń” zaznacza pozycje jako `DELETE` w lokalnym szkicu.

[`spaces/configuration-form.ts`](../frontend/app/src/spaces/configuration-form.ts)
obsługuje lokalne dodawanie, edycję i usuwanie oraz buduje końcowe żądanie
z pełnych formsetów szkicu i wspólnej rewizji.
Kontrakt JSON i zapis zachowują wszystkie trzy formsety, w tym statusy,
przejścia i pola dodatkowe używane przez zadania. Wielokrotne wartości przejść
i stan checkboxów są zachowane; niezaznaczony checkbox nie trafia do `FormData`.
„Dodaj” lub „Zastosuj” w oknie aktualizują tylko szkic. Dopiero „Zapisz”
na pasku wykonuje jeden istniejący POST całej sekcji i odświeża listę.
„Anuluj” odtwarza bazowy stan. Błąd zapisu zachowuje szkic, a błędna pozycja
otwiera się w oknie z fokusem na błędnej kontrolce. Konflikt rewizji (obecny
backend zwraca 400 z komunikatem) blokuje ponowny zapis; „Anuluj” pobiera
aktualny stan. Gdy POST się uda, a odświeżenie
listy zawiedzie, ponowienie wykonuje wyłącznie odczyt.
Przy uruchomieniu Reacta po błędnym natywnym POST odrzucenie szkicu pobiera
czysty stan konfiguracji przed zamknięciem okna, aby odrzucone wartości
i zaznaczenia `DELETE` nie trafiały do kolejnego zapisu.
`Modal` chroni szkic okna przed zamknięciem i przeładowaniem. Rodzic
chroni szkic głównych ustawień oraz typów przez `useDirtyGuard` i blokuje nawigację
podczas zapisu konfiguracji.
Zapis odświeża dane, nagłówek i tytuł dokumentu, pozostając na stronie;
zdarzenie `ancore:space-settings-saved` aktualizuje także kontekst powłoki
`shell/Shell.tsx`. `onCancel` w osadzonych formularzach zachowuje
`initialForm.return_url`, np. powrót do katalogu; gdy brak adresu lub prowadzi
on do ustawień, kieruje do przestrzeni. Nie dodano endpointu zapisu.

Serializer formularza edycji/awatara/członków zwraca opcjonalne `space_settings`
(`space_url`, `tab`), kierujące wszystkie wejścia do tej samej strony.
`FormPage` i `FormDialog` ładują `SettingsPage` dynamicznie dla tego kontraktu;
pozostali odbiorcy zachowują standardową powłokę. `?view=settings` i bezpośredni
URL konfiguracji również renderują tę stronę. Wejście `avatar/` otwiera picker
nad „Ustawienia”, zamiast osobnej sekcji. Udostępnienie i zmiana roli zachowują
kompaktowy `SharingDialog`, a lista członków zawiera serwerowe `can_remove`,
odpowiadające regułom właściciela i administratora Przestrzeni.

Sekcja udostępnień współdzieli `shared/AccessEditor` z Pulpitami, z parametrem
`publicVisibility="public"`. Payload `space_team.py` zawiera nazwę, widoczność,
rewizję dostępu, `can_change_visibility`, `can_configure` i opcjonalny wiersz
`private_owner` dla osoby prywatyzującej publiczną Przestrzeń.
`action=save` wysyła cały szkic `visibility=private|public` oraz JSON
`members=[{user_id,role}]`, bez właściciela. Rewizja jest hashem bieżącego
stanu dostępu; konflikt zwraca 409. Zapis jest atomowy, z walidacją ról,
Workspace i aktywnych odbiorców przed zmianami. Starsze operacje pozostają zgodne.
`team/candidates/?draft=1` zwraca ID osób i pozwala ponownie dodać osobę
usuniętą ze szkicu. Nowe wiersze mają oddzielne identyfikatory `draft:<user_id>`,
żeby nie kolidowały z kluczami członkostw.
Szkic udostępnień uczestniczy w `useDirtyGuard`, przetrwa zmianę sekcji i
nie zastępuje niezapisanych ustawień. Zmiana widoczności wymaga czystych
ustawień i typów; po zapisie unieważnia cache głównego formularza.
Główny formularz również blokuje zmianę widoczności przy szkicu typów,
ale pozwala zapisać pozostałe pola bez zmiany widoczności.
Aktualne uprawnienia odświeżają
podgląd i dostęp do konfiguracji, również w menu bocznym. Odświeżenie po
głównym zapisie również usuwa nieuprawnione formularze, cache konfiguracji
i ich stan szkicu, przekazując `canConfigure` do powłoki. Nawigacja pozostaje
zablokowana do zakończenia odczytów po zapisie.

Szablony Django również renderują pełną stronę: `spaces/settings_form.html`
zawiera formularz główny lub bezpośredni formularz edycji, awatara i członków,
`spaces/settings_members.html` tabelę, a `spaces/configuration.html` tabelę
typów zgłoszeń i okno edycji lub potwierdzenia usunięcia.
Menu pierwszego renderu używa `fallback_url`; sekcja członków przekazuje
`&section=members`, a konfiguracja `configuration/?section=types`,
więc wybór działa także bez obsługi fragmentów przez React. Linki dodawania
i edycji przekazują indeks przez `edit`, a usuwania przez `remove`.
Stare `section=fields|configuration` wybierają typy i pomijają
indeks edycji lub usunięcia ze starej sekcji. Szablon pokazuje kontrolki
wybranego typu w oknie, a pozostałe formsety przekazuje jako pola ukryte.
Błędny POST zachowuje okno, wartości i błędy;
walidacja ukrytych formsetów pokazuje komunikaty ogólne, bez otwierania
edytora pola. Udany zapis wraca do edytowanej sekcji typów albo procesu. Ograniczenia odczytu
i uprawnień są ustalane przez ten sam backend.

## Konfigurowalny pulpit Przestrzeni

`spaces/SummaryDashboard.tsx` zarządza szkicem i zapisem układu, katalogiem
`shared/WidgetCatalog.tsx`, błędami oraz ochroną wyjścia. `shared/DashboardCanvas.tsx`
współdzieli z Pulpitami uchwyty pointer/klawiatura, zmianę rozmiaru i panel opcji.
`Summary.tsx` zachowuje źródła danych i interakcje wykresów;
`SummaryWidgetControls.tsx` renderuje panel pozycji i rozmiaru, miniaturę
oraz suwaki i skróty szerokości we wspólnym `Dropdown`. Pozostaje otwarty
podczas zmian. Wariant `positioning="fixed"` zachowuje pozycję panelu
z chwili otwarcia, więc zmiana geometrii kafelka nie przesuwa kontrolek;
wspólna warstwa nadal dopasowuje panel do viewportu. W trybie edycji
kolejność węzłów DOM jest stabilna,
a CSS `order` zachowuje kolejność wizualną na telefonie; przeniesienie kafelka
nie przerywa pracy z panelem. Po zakończeniu edycji DOM wraca do kolejności
położenia. `summaryLayout.ts` wyznacza pozycje i rozwiązuje kolizje bez zależności
UI; helpery `moveWidget` i `resizeWidget` pilnują kierunków i krawędzi.
`ResizeObserver` rozpoznaje pionowy układ poniżej 700px. Wtedy panel pokazuje
góra/dół, a `moveWidgetInOrder` zamienia kafelek z sąsiadem w kolejności
położenia i układa siatkę ponownie, zachowując rozmiary oraz brak kolizji.
`summary.dashboard` zawiera `widgets: [{id,x,y,w,h}]`, `catalog`, `revision`,
`save_url`, `columns`, `max_rows` i `max_h`. Wspólny page API przekazuje JSON
`{revision, widgets}` do zwykłego/scoped `space/<slug>/dashboard/layout/`.
Odpowiedź zawiera aktualny `dashboard`; 400 oznacza błędną geometrię/identyfikatory,
a 409 konflikt rewizji. Serwer waliduje rozmiary, granice i brak kolizji;
`SpaceDashboardLayout` ma unikalność użytkownika i Przestrzeni. Wymagana jest
migracja `spaces.0003_space_dashboard_layout`. Nie zmienia agregacji ani ACL
zadań. Pierwszy render korzysta z tego samego zapisanego układu.

Podsumowanie i zadania współdzielą `ItemFiltering` z `spaces/ItemToolbar.tsx`.
Widok `overview` dostarcza te same opcje i aktywne warunki co lista;
zmiana/wyczyszczenie filtrów używa istniejącej nawigacji GET/JSON. Agregacje
nadal otrzymują queryset po filtrach i kontroli widoczności. Filtry z URL
nie są zapisywane jako część osobistego układu gadżetów.

## Animacje zadań Przestrzeni

Wszystkie sześć szablonów tablic Przestrzeni korzysta z jednego `ItemCard`
i `StatusGroup` w `spaces/DetailPage.tsx`. Wspólny wariant `work-sprint-board`
zachowuje wygląd aktywnego sprintu: kolorowe, zwijane kolumny, zwarte karty
i obramowane puste stany. Django używa tego samego układu przez
`spaces/card.html`; `spaces/sprint_card.html` pozostaje aliasem.

`spaces/useItemMotion.ts` łączy natywne przeciąganie z podglądem karty,
animowanym miejscem wstawienia i FLIP po zmianie danych Reacta. `DetailPage`
pokazuje lokalnie nową kolejność po upuszczeniu, zapisuje ją przez dotychczasowe
API i cofa po odrzuceniu zapisu. Autoryzacja, status/zakończenie i historia
nadal należą do Django. Kopie wizualne nie mają ID ani hooków aplikacji,
a `data-icon*` zachowuje właściwy wygląd ikon. Hook sprząta kopie, listenery,
klatki przewijania i animacje przy odmontowaniu. `prefers-reduced-motion`
wyłącza ruch. Nie dodano zależności; szczegóły interakcji: [UI](UI.md#przestrzenie-i-zespoły).

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
`pnpm --dir frontend/app test` uruchamia testy kontrolera nawigacji w Node.js,
z rzeczywistym kodem TypeScript bundlowanym przez esbuild i zastąpionymi
granicami HTTP/renderowania. Obejmują zmianę Workspace, przekierowania,
oczekiwanie na zapis i odrzucenie wyjścia po błędzie zapisu.
Regresje podsumowania Przestrzeni wykonują rzeczywiste callbacki wykresów,
przełączania liczb/procentów i sortowania, a także cykl obserwatora animacji,
fokus, Escape, zera i ograniczenie ruchu. Interakcje i style podsumowania
opisuje [standard UI](UI.md).
Każdy status w `summary.statuses` zawiera `path`: geometrię łuku SVG wyliczaną
przez `spaces.summary.status_arc_path`. React i pierwszy render Django używają
tej samej ścieżki; wcześniejsze `arc`, `gap` i `offset` pozostają w odpowiedzi
dla zgodności. Testy backendu obejmują granice segmentów oraz udziały 0% i 100%.
`pnpm --dir frontend/app format:check` sprawdza format źródeł;
`pnpm --dir frontend/app format` go poprawia.

Udostępnianie Przestrzeni używa kontraktu tabeli członków zadań (`team`),
`shared/Members`, `shared/SharingDialog` i pickera Workspace w trybie
udostępniania. Django `spaces.space_team` zachowuje zakres Workspace i role;
odpowiedź zapisu zwraca aktualną tabelę bez dodatkowego odczytu strony.
`workplace-team.css` jest ładowany również dla ekranów Przestrzeni i formularzy,
aby wejście bezpośrednie i częściowa nawigacja korzystały z tych samych stylów.

esbuild zapisuje lokalne pliki z hashem, osobne chunki i informacje licencyjne
w ignorowanym katalogu `static/frontend/`. `manifest.json` wskazuje bieżący
plik wejściowy, a tag `backend/core/templatetags/frontend.py` buduje jego URL przez
mechanizm Django `static`. Brak buildu daje jawny błąd konfiguracji.
Zbuduj frontend także przed testami renderującymi przeniesione ekrany.

Wdrożenie wymaga `pnpm install --frozen-lockfile`, `pnpm build`, a następnie
`manage.py collectstatic` i standardowego wdrożenia Django. Zachowaj poprzednie
chunki podczas wymiany wersji, aby otwarte karty mogły dokończyć ich pobieranie.
Node i pnpm są potrzebne podczas budowania; nie są procesami aplikacji w produkcji.
Domyślna instalacja produkcyjna obsługuje HTTP przez IP na porcie 8080.
Kopiowanie ID zadania używa `shared/clipboard.ts`: przy braku Clipboard API
korzysta z istniejącego wzorca `execCommand('copy')`, usuwa pole tymczasowe
i przywraca fokus; niepowodzenie pokazuje dotychczasowy komunikat błędu.
Pakiet tablicy nadal buduje się osobno według [OFFICE.md](OFFICE.md).

[Produkcyjny Dockerfile](../deploy/Dockerfile) buduje oba pakiety w etapie Node,
a następnie kopiuje bundle do obrazu backendu. Django wykonuje `collectstatic`
do trwałego wolumenu serwowanego przez Nginx. [Instalator i pięć usług](PRODUCTION.md).

## Podział źródeł i cykl życia

Formularze modalne współdzielą `forms/FormDialog.tsx`: `FormLayout` układa
nazwę/tytuł i opcjonalną widoczność, pełny opis oraz pozostałe pola parami.
`FormFields` włącza ten układ przez `layout`; domyślny wariant pozostaje
bez kontenera dla konfiguracji i osadzonych kontrolek. `PulpitFields` oraz
zakładki Filtrów zachowują warunkową widoczność swoich pól we wspólnym układzie.
Osobne edytory Kalendarza, Zasobów, Dysku, Workspace i profilu stosują klasy
`app-form-*` z `modal-system.css`. Zmiana kolejności jest częścią renderowania,
bez przenoszenia kontrolek przez JS i bez zmiany zapisu lub ACL.
Szczegóły i responsywność: [standard modali](UI.md#6-modale).

`shared/FieldLabel.tsx` renderuje etykietę i opcjonalny znak „!” z pomocą pola.
`static/js/field-help.js` obsługuje wspólny kontrakt Reacta i szablonów Django
przez delegowane zdarzenia, bez ponownego podpinania listenerów przy nawigacji.
Treść dymka pozostaje w formularzu i jest pozycjonowana przez
`AncoreDropdownLayer`; zachowuje ID używane w `aria-describedby` kontrolki.
Pomoc otwiera się przez hover/fokus oraz kliknięcie/dotyk, nie wysyła formularza
i nie zmienia jego szkicu. Escape zamyka dymek przed oknem formularza.

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
  `shared/Emoji` i include `core/emoji.html` wyświetlają dekoracyjne emoji
  Pulpitów wspólną klasą `ancore-emoji` i lokalnymi atlasami Fluent Emoji 3D.
  Dane Pulpitu, menu i wyszukiwarki zachowują `icon` oraz przekazują `emoji`
  i `emoji_art` (adres arkusza i pozycja albo `icon` wspólnego renderera).
  `layout-dashboard` jest domyślną ikoną czterech kafelków, a wybrany Unicode
  korzysta z grafiki Fluent. Formularz typu `emoji` przekazuje
  `emoji_picker`: wybrany symbol, wybór domyślny, adres katalogu oraz bazowy adres arkuszy.
  `shared/EmojiPicker` używa wspólnego `Dropdown`, pobiera katalog dopiero
  po otwarciu, buforuje udany odczyt i pozwala ponowić błąd. Kategorie,
  polska/angielska wyszukiwarka i lokalne ostatnie wybory nie dodają żądań API.
  Wariant `avatar` pokazuje duży podgląd i „Zmień”; `PulpitFields` umieszcza
  go w bocznej kolumnie istniejącego układu profilu/Przestrzeni. Pozostałe pola
  zachowują wspólne wiersze i responsywne kolumny. Zwykły wariant pola pozostaje dostępny.
  `core.emoji` jest wspólną listą dozwolonych wartości i buduje te same dane
  dla Reacta i pierwszego renderu Django. Osiem wcześniejszych identyfikatorów
  jest zgodnych, a nowe wybory zapisują Unicode w istniejącym polu.
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
przeglądarkowego `required` w pustych wierszach. `name` pozostaje nazwą HTML
używaną w POST (np. `subtask-description`), a `field_name` zawiera nazwę pola
Django bez prefiksu (`description`). Wspólny układ korzysta z `field_name`,
z fallbackiem do `name` dla schematów bez tych metadanych; nie zmienia nazw
ani ID kontrolek. Dotyczy to również schematów zwracanych po błędzie walidacji.
Pliki są wysyłane jako
`FormData`, bez ręcznego nagłówka multipart. Pobieranie pozostaje pod
kontrolowanymi adresami domenowymi, z dotychczasowym prywatnym storage.

Automatyczny zapis zadania wysyła `autosave_fields`, łączy je po stronie
Django z aktualnymi pozostałymi wartościami i szereguje kolejne zapisy.
Pola tekstowe i textarea pomijają powtórne `change` z tą samą wartością po
`input`, aby opuszczenie pola po debounce nie wysyłało ponownie zapisanego tekstu.
Nawigacja aplikacji czeka na zakończenie zapisu; błąd zachowuje wpisane dane.
Operacje zadania, w tym wysłanie komentarza, ustawiają blokadę przed
oczekiwaniem na autosave. Przez całe oczekiwanie pola komentarza i wysyłka
są wyłączone; ponowne kliknięcie nie tworzy drugiego żądania. Błąd autosave
zwalnia blokadę i zachowuje szkic do ponowienia.
Udany POST i następujący po nim odczyt strony mają osobne wyniki. Błąd
odświeżenia po zapisaniu komentarza usuwa już wysłany szkic i udostępnia
„Odśwież zadanie”, które ponawia wyłącznie GET. Podzadanie lub wpis czasu
pozostają po takim błędzie w zablokowanym formularzu z potwierdzeniem zapisu;
ponowienie odświeża dane bez ponownego tworzenia rekordu. Autosave pamięta
zaległe odświeżenie również po wyczyszczeniu listy zapisanych pól i plików,
więc „Spróbuj ponownie” może wykonać sam GET. Błąd samego POST nadal
zachowuje niezapisany szkic do ponowienia.
`TaskPage` pokazuje `start_at` i `due_at` razem w sekcji dat, z etykietami
„Data rozpoczęcia” i „Termin zakończenia” z `DetailForm`. Rozpoczęcie nie jest
ukrytym polem planowania. To te same wartości co na osi czasu; szczegóły
edytują datę i godzinę obu końców. Autosave waliduje pełny zakres przez istniejący
formularz, a historia zapisuje także zmianę lub usunięcie rozpoczęcia.
Podzadanie nie montuje własnego `TaskPage`: jego adres zwraca przekierowanie
do `tab=subtasks` zadania głównego po kontroli dostępu. Tytuł na liście rodzica
otwiera istniejący `FormDialog` przez `edit_url`, po zapisaniu szkicu rodzica.
Zapis okna odświeża dane rodzica bez nawigacji. Błąd samego odczytu po zapisie
pokazuje „Odśwież zadanie” i nie powtarza mutacji. Obserwator widzi tytuł bez
linku edycji. Formularz podzadania ma osobne identyfikatory kontrolek, także
po walidacji, aby etykiety i podglądy wyborów nie wskazywały formularza rodzica.
`SubtaskForm` dostarcza wspólny schemat dodawania (`SchemaDialog`, prefiks
`subtask-`) i edycji (`FormDialog`): tytuł, opis, status, priorytet, wykonawca,
typ zgłoszenia, rozpoczęcie, termin zakończenia i punkty. Oba okna korzystają
z istniejącego `FormLayout` oraz tych samych kontrolek; punkty pozostają
dostępne również poza Scrumem. Ukryta widoczność tworzenia zachowuje domyślną
prywatność i zgodność wcześniejszych żądań. Zapis edycji zmienia tylko pola
schematu, zachowując wcześniejsze powiązania i pozostałe dane planowania.
Pola dodatkowe zadania są edytowalne w panelu właściwości. Błędy pozostałych
pól planowania odsłaniają odpowiednią kontrolkę w tym panelu. Jeśli konfiguracja
doda pole podczas edycji, odpowiedź walidacji uzupełnia schemat bez odtwarzania
istniejących kontrolek i kasowania szkicu. Uzupełnienie pola ponawia również
wcześniej odrzucone zmiany.
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
Endpoint zbiorczego usuwania tagów przyjmuje wielokrotny `tag_ids` w FormData
i zachowuje atomową kontrolę wszystkich identyfikatorów. Katalog nie pokazuje
menu „…” ani menu wierszy; kolumnę „Działania” usunięto również z menedżera
kolumn. Opcjonalne skróty edycji, informacji i notatek pozostają dostępne
w konfiguracji tabeli. Edycja notatki wymaga jej autorstwa.
Po udanym zapisie notatki tagu szkic jest czyszczony przed odświeżeniem.
Awaria odczytu udostępnia „Odśwież notatki” i wstrzymuje dalsze operacje
na nieaktualnej liście do udanego GET, bez powtarzania zapisanego POST.
Wyniki Filtrów zawsze przechodzą przez bieżące ACL zadań; udostępnienie definicji
nie rozszerza dostępu. Rewizje i blokady nadal obsługują oryginalne widoki.
Starsze nagłówki `X-Filter-Modal` i `X-Filter-Navigation` są usuwane przez
adapter, więc nie mogą przełączyć odpowiedzi API na fragment HTML.

Tworzenie i edycja filtra otrzymują odpowiednio `filter_settings: "create"`
lub `"edit"` i schemat bez wariantu kompaktowego. `FormDialog` deleguje je do
`filters/SettingsDialog.tsx`, który zachowuje zamontowany `EmbeddedForm`
w zakładce „Ustawienia”, a w „Udostępnieniach” używa `shared/Members`
i `shared/SharingDialog`. Modal edycji zawiera `filter_team` z adresem `team/`
i autoryzowaną tabelą. Utworzenie zwraca `filter_modal` pozwalający przejść
do udostępniania bez zamykania okna. Zapisy ustawień zwracają świeży `form`.
Operacja udostępnienia zwraca poprzednią i nową rewizję; `EmbeddedForm`
aktualizuje sam token tylko przy zgodności poprzedniej wartości, zachowując
szkic i wykrywanie zewnętrznych konfliktów. Endpointy `filter_sharing`
sprawdzają role oraz aktywny Workspace tak samo jak zwykły routing.
Walidacja odsłania panel błędnego pola, również dla wymaganych pól HTML.
Po zapisie edycji okno pozostaje otwarte. Zamknięcie odświeża odpowiedni widok,
zachowując filtry katalogu; menu boczne otwiera okno nad bieżącym ekranem.
Bezpośrednie URL korzystają z tej samej powłoki. Tworzenie i „Zapisz jako”
przechodzą po sukcesie do udostępnień zapisanej definicji w tym samym oknie,
zachowując adres powrotu; kolejny zapis edytuje ją bez tworzenia duplikatu.
Globalne menu Filtrów, jego picker i wyszukiwanie definicji renderuje
`src/shell`; wyniki API zachowują ten sam zakres widoczności.

Pulpity używają `backend/dashboard/pulpit_frontend.py` i `src/pulpits/`. Odczyt gadżetu
udostępnia liczniki i statusy bieżących `SpaceTask`, bez fragmentu HTML.
Niedostępne źródło zwraca wyłącznie metadane gadżetu i `unavailable`, bez nazwy
prywatnej Przestrzeni ani jej liczników. Udostępnienie pulpitu nie rozszerza ACL
danych. Edycja gadżetów wymaga roli właściciela, administratora lub członka
konkretnego Pulpitu, niezależnie od roli Workspace.
Pulpit domyślny inicjalizuje oryginalny widok Django; usunięte gadżety nie są
odtwarzane podczas kolejnego wejścia.

`src/pulpits/DetailPage.tsx` renderuje edycję gadżetów i układu bezpośrednio
w głównej treści pulpitu. „Edytuj pulpit” przełącza szkic na tej samej stronie
i aktualizuje adres przez adapter nawigacji; „Gadżety i układ” oraz bezpośrednie
adresy otwierają ten sam edytor. `shared/DashboardCanvas.tsx` zapewnia siatkę
12 kolumn, uchwyty, rozmiary, menu i mobilną kolejność jak w Podsumowaniu.
`src/pulpits/SettingsPage.tsx` zawiera tabelę dostępów i formularz ustawień
na osobnej stronie, z układem `space-settings-page` współdzielonym z Przestrzeniami.
Powłoka `pulpit-settings` otrzymuje `pulpit_settings` z autoryzowanymi linkami
„Ustawienia” i „Udostępnienia”. Menu zastępuje nawigację Workspace i otwiera się
rozwinięte bez zmiany zapisanej preferencji zwykłego menu. Pierwszy render
zapewnia `core/includes/pulpit_settings_sidebar.html`.
Wejścia z katalogu, podglądu i menu bocznego korzystają ze zwykłej nawigacji JSON.
Bezpośrednie `edit/` i `access/`, także scoped, zarządzania oraz numeryczne,
otwierają tę samą stronę. `settings_tabs` zachowuje adresy i filtry; strona pomija
gadżety i normalizuje lokalne sekcje do `edit/#settings` oraz `edit/#access`.
Zmiana fragmentu i zdarzenie `ancore:pulpit-settings-tab` synchronizują boczne
menu z historią Wstecz/Dalej, bez odmontowania szkicu. `useDirtyGuard` chroni
niezapisane zmiany przy wyjściu. Zapis pozostaje na stronie i odświeża nagłówek,
tytuł dokumentu oraz dane powłoki przez `ancore:pulpit-settings-saved`.
Zamknięcie respektuje `return_url`; nie dodano nowych endpointów zapisu.
Sekcja „Udostępnienia” używa `shared/Members`, `shared/SharingDialog` oraz
pickera Workspace, tak jak Przestrzenie. Tabela ma po bokach odstępy
`--app-page-padding-x`, wyrównane do nagłówka i paska działań. Wypełnia pozostałą
wysokość i przewija się niezależnie od zwartego paska działań.
Sekcja nie ma dolnej stopki. Wariant `space-settings-table-body`
i pasek `tasks-filterbar--directory` obejmują React i pierwszy render Django;
istniejący formularz zgodności pod tabelą ma osobny obszar przewijania.
Pulpity i Przestrzenie używają wariantu `Members` z `rowActions={false}` i kontrolowanym
`selection`: pięć kolumn bez menu wiersza, zaznaczanie wszystkich wierszy,
Ctrl/Cmd+A oraz Escape. Dopiero akcje filtrują osoby przez `can_change`,
więc zaznaczenie właściciela nie pozwala zmieniać jego roli ani dostępu.
Domyślny wariant pozostałych modułów zachowuje menu.
Toolbar zawiera po lewej widoczność, zmianę roli, odebranie dostępu
i udostępnienie, a po prawej „Zapisz” oraz „Anuluj”.
`SharingDialog.people` rozszerza istniejący modal o zbiorczą zmianę roli.
Opcjonalne `onStage` przekazuje lokalną zmianę zamiast POST, a `candidatesUrl`
pozwala użyć `team/candidates/?draft=1`: kandydat ma ID, a wyszukiwanie
obejmuje również osoby usunięte ze szkicu. Pozostali odbiorcy modala nadal
zapisują bezpośrednio. `shared/AccessEditor` przechowuje bazową rewizję i szkic
widoczności oraz osób; `SettingsPage` chroni go przy wyjściu i zmianie sekcji.
„Zapisz” wysyła FormData `action=save`, `revision`, `visibility=private|workspace`
oraz `members=JSON.stringify([{user_id,role}])`, bez właściciela.
Backend waliduje cały snapshot przed zapisem, chroni administratorów,
sprawdza aktywność Workspace i podnosi rewizję raz. Konflikt zwraca 409;
„Anuluj” wtedy odrzuca szkic i wczytuje bieżącą wersję. Zwykłe anulowanie
jest lokalne. Błąd zapisu zachowuje szkic do ponowienia.
Starsze POST `action=role|remove|visibility|share` pozostają zgodne.
`can_change_visibility` ogranicza kontrolkę do twórcy. Zmiana widoczności
wymaga czystego formularza ustawień i po zapisie unieważnia jego cache;
zmiana samych ustawień może uaktualnić rewizję bez nadpisywania szkicu dostępu.
Pierwszy render pokazuje ten sam
pasek z przyciskami aktywowanymi przez React; formularz zgodności nadal działa.
`pulpit_sharing.py` obsługuje
zwykłe/scoped `dashboards/<slug>/team/` i `team/candidates/`, także przez API strony.
Serializer przekazuje `team` z rewizją i `team_url`; tabela odświeża się po zapisie,
bez odmontowania szkicu ustawień. Wspólny `EmbeddedForm` obsługuje zapis,
błędy i fokus ustawień, w tym widoczności. Prywatny pulpit z odbiorcami zachowuje
wewnętrzną widoczność `selected`; pierwszy odbiorca ją ustawia, a usunięcie ostatniego
przywraca `private`. Zmiana na Workspace usuwa indywidualne udostępnienia.
Operacje blokują pulpit i ponownie weryfikują rolę oraz aktywne osoby Workspace.
`DashboardMembership` jest jawnym modelem istniejącej relacji `shared_with`;
migracja zachowuje dawnych odbiorców jako obserwatorów. Tabela i `SharingDialog`
obsługują zmianę roli. Administrator zarządza członkami i obserwatorami,
bez promowania administratorów i operacji na innych administratorach lub właścicielu.
Kontrakt `editable`/`manageable`/`deletable` rozdziela menu gadżetów, ustawień
i usuwania także w powłoce i szablonach. Widoczność i usunięcie Pulpitu są
zastrzeżone dla właściciela. Źródła danych nadal stosują uprawnienia oglądającego.
Po zapisie okno pozostaje otwarte. Bezpośrednio otwarte okno odmontowuje się przed
nawigacją, także po potwierdzeniu odrzucenia szkicu, aby uniknąć ponownego zamknięcia.
Zamknięcie chroni wszystkie szkice i po zmianie odświeża stronę w tle.
Konfiguracja pojedynczego gadżetu używa standardowego formularza modalnego
nad edytorem; zapis wraca do siatki z aktualną rewizją.

`data.grid` zawiera `{widgets: [{id,x,y,w,h}], revision, save_url, columns}`
i granice siatki. Edytor wysyła do `arrange` JSON `{revision, widgets}`;
nowy gadżet ma tymczasowy identyfikator `new-*` oraz `kind: "progress"`.
Brak istniejącego ID oznacza usunięcie, a odpowiedź `{saved, revision, page}`
zawiera aktualne dane i trwałe ID. Dodanie, usunięcie oraz geometria są jednym
zapisem; „Anuluj” odrzuca cały szkic. Błąd zachowuje szkic, a „Wczytaj aktualny
układ” po potwierdzeniu pobiera wersję serwera. Konfiguracja istniejącego gadżetu
jest dostępna po zapisaniu układu i odświeża rewizję bez opuszczania edytora.
Nowe karty pokazują dane dopiero po zapisie. Katalog działa we wspólnym
`shared/WidgetCatalog.tsx`: wyszukiwarka, przewijane wiersze z miniaturą,
opisem i przyciskiem dodania. Miniatura Pulpitów używa `GadgetCard` z jawnymi
danymi przykładowymi; Podsumowanie przekazuje te same `renderWidget` co siatka,
z bieżącymi danymi i stanem „Dodano”. Podglądy nie wykonują dodatkowych żądań;
`ResizeObserver` skaluje ich rzeczywiste komponenty, a `inert` i `aria-hidden`
wyłączają interakcje. Wspólna pułapka fokusu w `tasks.js` pomija elementy
wewnątrz `inert`. Ten sam rodzaj w Pulpitach można dodać wielokrotnie, do limitu 24.

`dashboard.0008_dashboard_gadget_grid` dodaje `x/y/w/h` do `DashboardGadget`
i przenosi dotychczasowe kolumny na siatkę, zachowując konfiguracje. Odczyt
starszych rekordów bez geometrii ustala pozycje bez zapisu. Serwer sprawdza
identyfikatory, kolizje, granice 12×200, rozmiary 4–12×5–16, limit i rewizję
pod blokadą pulpitu. Role i widoczność źródeł pozostają sprawdzane osobno.
Pierwszy render korzysta z tych samych prostokątów. Starsze API
`{layout, columns, revision}` i `gadget_quick_add` pozostają zgodne i aktualizują
geometrię; aktywny React nie używa kolumnowego autosave.
Jawna lista `JSON_BODY_VIEWS` przekazuje strukturalny JSON do widoków domenowych;
formularze nadal używają FormData. Adapter usuwa starsze nagłówki `X-Pulpit-Modal`
i `X-Pulpit-Navigation`. Usunięcie przekazuje `invalidated_return_paths`
do istniejącej powłoki przed nawigacją. Tabele zachowują dotychczasowe klucze
szerokości. Menu boczne Pulpitów, picker i wyszukiwanie pozostają częścią powłoki.

Ustawienia pulpitu obejmują ikonę z istniejącej biblioteki, domyślny zakres
danych (Workspace, wybrane Przestrzenie albo zapisany filtr) i odświeżanie
wyłączone lub co 60/300/900 sekund. Ikona jest przekazywana do nagłówka,
katalogu, skrótów menu i wyników pickera. `PulpitFields` zachowuje szkice
źródeł przy przełączaniu zakresu; formularze Django ograniczają wybór do
widocznych źródeł aktywnego Workspace.
Widżety przekazują semantyczne ikony zakresu i odświeżania oraz avatary
wybranych Przestrzeni. Wielokrotny wybór korzysta z `SpaceSelectMultiple`,
tej samej serializacji `space_avatar` i istniejącego adaptera custom selecta.

Gadżet bez własnej Przestrzeni dziedziczy zakres pulpitu. Odczyt ponownie
sprawdza widoczność Przestrzeni, filtra i wynikowych zadań dla oglądającego;
zapisany filtr korzysta z istniejącego kompilatora zapytań. Usunięcie albo
utrata dostępu do źródła daje niedostępny gadżet, bez rozszerzenia na Workspace
i bez ujawnienia prywatnych nazw. Własna Przestrzeń gadżetu zastępuje zakres.

`src/pulpits/autoRefresh.ts` planuje odczyty wyłącznie widocznego podglądu,
bez nakładających się żądań. Ukrycie karty usuwa timer; powrót uruchamia
pełny nowy interwał. Edytor, otwarty modal, trwająca operacja i brak sieci
wstrzymują automatyczny odczyt. Odmontowanie usuwa listener i timer,
a cykl życia strony anuluje niedokończone żądania. Błąd pozostawia ostatnie
dane, pokazuje alert i zachowuje możliwość ręcznego ponowienia.

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
Gość widzi nazwę jako zwykły tekst bez kontrolek jej zmiany, zarówno w React,
jak i pierwszym renderze Django. Kolejka ONLYOFFICE zachowuje nowsze zmiany
powstałe podczas oczekiwania na zapis i wysyła je po jego potwierdzeniu.
Potwierdzeniem jest nowy `save_receipt` utworzony przez callback zapisujący plik;
zmiana ogólnego `revision` przy przeniesieniu albo edycji metadanych nie kończy
oczekiwania. React i adapter `office-suite.js` korzystają z tego samego kontraktu.
Pełny edytor wyłącza `global_panels_bootstrap` przez `disable_react_shell`,
ponieważ jego szablon pomija całą nawigację. Istniejący `layout.js` obsługuje
wtedy sam cykl ładowania strony bez sidebara, także usunięcie zasłony po
przeładowaniu i `pageshow`; korzeń Reacta strony pozostaje aktywny.
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
Jawne przełączenie lub potwierdzenie linku zmienia aktywny Workspace; ręczne
dodanie osoby nie zmienia kontekstu zarządzającego.
Zarządzanie innym dostępnym Workspace może korzystać z API aktywnego kontekstu;
nie udostępnia obcych Workspace ani nie rozszerza ACL Przestrzeni.

Dane obejmują ograniczone schematy formularzy, awatary i dozwolone akcje.
Członek otrzymuje ustawienia tylko do odczytu i skład zespołu, bez formularza
dodawania i tokenów linków. Administrator dodaje wyłącznie członków i gości;
nie zarządza właścicielem ani administratorami, także nieaktywnymi.
`add_form`, `add_url` i `add_open` opisują ręczne dodawanie przez POST `user_id`
i `role`; wybrane `user_id` jest identyfikatorem konta z pickera. Bez JS można
wpisać dokładne ID Ancore. Serwer odrzuca niejednoznaczne lub nieaktywne konta.
Podpowiedzi wymagają co najmniej 2 znaków i mają limit 10; zawierają `id`, nazwę,
e-mail i awatar, bez HTML w API Reacta. Formularz nie serializuje całego katalogu
kont. Błędny zapis daje HTTP 400 z zachowanym oknem i polami.
Zakładka `links` korzysta z `link_form`, `link_create_url` i `invite_links`;
nie zawiera domeny e-mail. Nie ma `incoming`, wysyłania ani odbioru zaproszeń e-mail.

Awatar jest odizolowaną wyspą DOM używającą istniejących `AncorePhotoEditors`
i `AncoreWorkplaceAvatars`. Zachowuje 30 ilustracji, wybór automatyczny,
własny obraz i kadrowanie, anulowanie wyboru oraz walidację Django.
Komponent inicjalizuje widget po montażu, a przy odmontowaniu zamyka okna,
odłącza listenery i zwalnia obraz. Formularz zachowuje wybór po błędzie zapisu.
Zmiany nazw nie zmieniają stałego kodu. Usunięcie członka zachowuje istniejące
czyszczenie dostępów Przestrzeni i unieważnienie sesji Office.
Favorites i globalny picker Workspace renderuje trwała powłoka `src/shell`.

Wiersze katalogu zawierają osobiste `is_default` i `default_url`. Menu używa
POST `default_url` z `action=set/remove`; JSON zwraca `default_workplace_id`
(tekst lub null). React aktualizuje etykiety bez przeładowania i bez zmiany
aktywnego Workspace. Stan błędu zachowuje poprzedni wybór; zapis blokuje
równoległe operacje. HTML zachowuje natywny formularz POST z CSRF.
Po logowaniu zapisany, nadal dostępny domyślny Workspace ma pierwszeństwo
przed aktywną sesją, z zachowaniem przepływu oczekującego zaproszenia.

## API i interfejs kont

`GET/POST /accounts/api/v1/page/?url=<adres_konta>` ma osobną, zamkniętą
listę adresów: logowanie, rejestracja i jej krok nazwy Workspace, wybór Workspace, profil,
dodanie/przełączenie/usunięcie konta z sesji, zmiana statusu i wylogowanie.
Logowanie, rejestracja i publiczny ekran zaproszenia działają bez uwierzytelnienia;
tworzenie Workspace wymaga sesji; ogólny `/api/v1/page/` nadal wymaga sesji
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
strony „Dla ciebie” po logowaniu. Konto bez Workspace przechodzi do tworzenia,
a sesja z linkiem zaproszenia wraca do jego potwierdzenia. `account-auth`
z `mode: workspace` zawiera wymagane pole `name`, flagę `has_workspaces` i link
`select_workspace` do `/accounts/workspaces/`. Osobny ekran
`account-workspace-picker` zawiera listę `workspaces` (id, nazwa, `switch_url`)
ograniczoną przez `workplaces_for_user`; nie zawiera formularza tworzenia.
Wybór używa istniejącego natywnego POST przełącznika z CSRF. Formularz
tworzenia osoby z dostępnym Workspace wysyła `create_another=1`, aby jawnie
utworzyć kolejne środowisko; ponowiony pierwszy POST bez tej flagi zachowuje
dotychczasowe przekierowanie do istniejącego Workspace. `account-join` obsługuje
potwierdzenie dołączenia w React. Tożsamość i CSRF zachowują pełne przeładowanie.
Kontrakt strony zawiera `read_only`; gość nie otrzymuje uprawnień/URL edycji.
Ustawienia Workspace zawierają moduły oraz formularz i listę linków zaproszeń.

Ekrany `src/accounts/` współdzielą z `auth_base.html` tapetę i prawą kartę
formularza (520px, wysokość według treści) z widocznym nagłówkiem, etykietami
i zakładkami logowania/rejestracji. Przycisk ma lokalny, fioletowy wariant
(szczegóły w [standardzie UI](UI.md#konta-w-react)).
Profil pozostaje w `core/base.html`. Formularze zachowują szkic po błędach i blokują
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
wyników i historia ostatnich pozostają w usługach Django.

Lista powiadomień dla Reacta zawiera `items`, jawne pola kart, daty, szczegóły,
aktualnie dostępne Workspace z awatarami, liczniki, podpisany `snapshot`
i `next_cursor`; serializer `backend/dashboard/notification_frontend.py` nie renderuje
fragmentów HTML. Starszy endpoint XHR zachowuje kontrakt HTML dla zgodności.
Wszystkie filtry, osobisty odczyt, archiwum, usunięcie i operacje zbiorcze używają
oryginalnego `notification_service`. Każdy odczyt/zapis ponawia kontrolę dostępu.
Powiadomienia obejmują komentarze i osobiste przypomnienia Przestrzeni.
Nie ma źródła ani filtra zaproszeń, `is_invitation` ani licznika oczekujących.
`deletable_count` podaje liczbę usuwalnych wpisów wszystkich stron bieżącego
filtra i steruje przyciskiem oraz potwierdzeniem usunięcia.

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
Formularz Zasobów używa wspólnego `app-page-modals`, obecnego zarówno przy
pierwszym renderze Django, jak i po nawigacji JSON. Kontener starego formularza
HTML pozostaje wyłącznie fallbackiem pierwszego renderu.

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
Adres z innym segmentem Workspace (również z globalnych powiadomień)
otwiera się w pełni już przed żądaniem API bieżącego Workspace. Nadal czeka
na zapis i respektuje odrzucenie wyjścia; tę samą kontrolę stosuje do przekierowań.
Backend docelowej strony ponownie sprawdza członkostwo i dostęp do obiektu.

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
Pozostają tylko dla szablonów zgodności. Historyczne systemy Tasks/Kanban
usunięto również z modeli, migracji i routingu. Nowe funkcje rozwijaj w istniejących komponentach
React i usługach Django, z aktualnym ACL oraz wspólnym systemem UI.

## Poprawki bezpieczeństwa po przeglądzie (25.10.2026)

Dynamiczne nazwy w potwierdzeniach odebrania dostępu przechodzą przez
`showConfirmModal({messageText: ...})`; helper escapuje tekst przed wstawieniem do HTML.
Dotychczasowe kontrolowane komunikaty HTML zachowują osobny parametr `message`.
Gość otwiera istniejący dokument tekstowy w trybie odczytu: React i pierwszy
render nie pokazują zapisu, konwersji ani edytowalnej treści. Stary HTML jest
sanityzowany; serwer nadal odrzuca zapisy. [Uprawnienia](TEAMWORK.md).

## Interaktywna oś czasu Przestrzeni

`spaces/TimelineView.tsx` korzysta z `DetailData.items`, również pozycji bez dat.
`item_payload` przekazuje pełne `start_at` i `due_at`, lokalne projekcje dni
`start_on` i `end_on` oraz `update_dates_url`. Timestampy są źródłem snapshotu,
a projekcje dni służą geometrii kalendarza. Zakres jest
ograniczany na serwerze przez te same filtry/ACL co inne widoki. Oś zwraca
pierwsze 20 pasujących zadań z możliwością doładowania kolejnych 20 przez
`timeline.more_url` i `pagination: null`; `page` jest ignorowany.
`spaces/timeline.ts` liczy dni kalendarzowe w UTC, bez przesunięć DST, nagłówki,
paski, dopasowanie i granice resize. Dzisiejszy dzień jest wyznaczany dla
Europe/Warsaw. Nie dodano biblioteki wykresów ani modeli danych.

POST do zwykłego/scoped `space/<slug>/tasks/<key>/dates/` przyjmuje formularz:
`start_at`, `due_at`, `source_start_at`, `source_due_at` przy zapisie okna dat.
Pierwsze dwa pola mają lokalny format `YYYY-MM-DDTHH:mm`, a snapshoty pełny
ISO timestamp ze strefą; brak wartości oznacza pusty ciąg. Kontrolki formatują
czas w Europe/Warsaw niezależnie od strefy przeglądarki. Niezmienione wartości
minutowe zachowują zapisane sekundy. Przesuwanie/rozciąganie paska zamiast
`start_at` i `due_at` wysyła `start_on` i `end_on` (`YYYY-MM-DD`), z tymi samymi
pełnymi snapshotami, a serwer zachowuje obie godziny i precyzję.
Endpoint jest również zarejestrowany w page API.
Odpowiedź 200: `saved`, `changed`, `start_at`, `start_on`, `end_on`, `due_at`, `due_urgency`;
400 walidacja, 409 konflikt dat, 403/404 brak uprawnień. Błędy mają `message`
i `error`. Po zapisie React aktualizuje wiersz bez przestawiania przewiniętej
listy; ponowne wejście stosuje aktualne sortowanie. Stan oczekiwania chroni
przed równoległym wysłaniem, a błąd pozostawia poprzednie daty i szkic formularza.
Przypięta kolumna zadań renderuje kompaktowy `TimelineItemRow` z `Item.tsx`.
Jej pływającą powierzchnię tworzą pseudoelementy komórek `work-timeline-heading`:
wspólny obrys, cień przycięty między wierszami i zaokrąglenia pierwszej/ostatniej
komórki `tbody`, także przy sprintach i pojedynczym wyniku. Przezroczyste komórki
zachowują `sticky` i oryginalną geometrię; tło najechania/fokusu należy do
powierzchni panelu. Nie ma drugiej listy, scrolla ani dodatkowych listenerów.
Nagłówek tabeli ma jedną komórkę obejmującą obie kolumny, z nazwą
„Zadania i kalendarz” dla czytników ekranu. `TimelineCalendarHeader`
mierzy szerokość przypiętych danych przez `ResizeObserver` i przekazuje ją
do `timelineHeaders(window, leadingWidth)`. Wcześniejsze daty wypełniają
lewą część paska, zachowując jednostki oryginalnego okna i współrzędne
względem początku kalendarza. CSS dodaje szerokość danych do etykiet
i znacznika dzisiaj; nagłówek przewija się razem z tabelą bez listenera
przewijania ani renderowania zadań. Obserwator jest usuwany przy wyjściu.
Wspólny z `ItemRow` komponent `ItemIdentity` zachowuje priorytet, status oraz
klucz/tytuł; `Planning` bez estymacji i z `showAssigneeName` pokazuje awatar
oraz pełną nazwę wykonawcy z `assignee.label` lub „Nie przypisano”. Pozostałe
widoki zachowują domyślny wariant samego awatara. Kompaktowy
wiersz nie renderuje zaznaczenia, typu, liczników, ikony terminu ani menu.
Nie wymaga stanu zaznaczeń ani akcji z `DetailPage`. Kliknięcie paska lub
„Zaplanuj zadanie” nadal otwiera okno dat z dotychczasową blokadą zapisu.
Nie ma oddzielnej kolumny Wykonawca ani Status. Kategorie nadal kolorują paski
i służą filtrowaniu.
„Dzisiaj” i trzy skale są bezpośrednimi przyciskami jednej grupy
`tasks-segments` o nazwie „Nawigacja osi czasu”. Tylko skale mają `aria-pressed`;
wspólny kontener zachowuje istniejące callbacki i blokadę podczas zapisu.
