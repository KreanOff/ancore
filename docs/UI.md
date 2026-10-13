# Standard UI Ancore

## Dolny pasek stron Przestrzeni

`spaces/base.html` umieszcza wspólny `spaces/pagination.html` pod przewijaną
treścią w bloku `work_pagination`. Pasek pozostaje widoczny przy dolnej
krawędzi panelu, także przy krótkiej lub pustej liście. Pokazuje zakres
wyników, strzałki i numery stron; aktualny numer ma `aria-current="page"`,
a niedostępne strzałki są wyłączone. Długie zakresy skraca tag
`pagination_pages` z `space_ui`, zachowując pierwszą, ostatnią i sąsiednie strony.
Linki używają `querystring`, zachowują filtry oraz zwykłe/scoped adresy
i korzystają z istniejącej częściowej nawigacji. Bez JavaScriptu działają
jako zwykłe linki.

Wariant `work-pagination` rozszerza wspólne klasy `tasks-project-pagination`
w `spaces.css`. Na wąskim ekranie zakres i przyciski mogą przejść do dwóch
wierszy. Korzystają z niego katalog/zarządzanie Przestrzeniami, lista zadań,
backlog, tablica, oś czasu, Zespoły oraz katalog/wyniki Filtrów.
Podsumowanie, raporty, ustawienia i szczegóły zadania nie pokazują tego paska.
Tagi przestrzeni zachowują osobny mechanizm `directory_pagination_toolbar.html`.

## Filtry zadań

Szablony dashboard/filters rozszerzają spaces/base i core/base.
Katalog używa wspólnych zakładek notifications-tabs/work-tabs, menu
directory_row_menu oraz tabeli tasks-directory-sheet. Wariant
task-filter-directory określa kolumny katalogu; ich szerokości mają
osobny klucz ustawień w tasks.js. Wyniki w „Wyszukaj zadania” i zapisanych
filtrach korzystają z spaces/item_list.html i spaces/row.html: kolorowych
grup statusów, zwijania oraz wierszy z checkboxem, priorytetem, statusem,
kluczem, tytułem, typem, licznikami tagów/załączników i oznaczeniem terminu.
Grupy obejmują bieżącą stronę wyników, a sortowanie zachowuje kolejność
zadań wewnątrz grup. Wyniki nie używają tabeli z nagłówkami kolumn.

„Zarządzaj filtrami” jest osobną stroną `dashboard/filters/manage.html`,
bez zakładek katalogu, z własnym minimalnym menu zarządzania: powrót
do Ustawień i aktywna pozycja „Filtry”.
`directory.html` współdzieli tabelę z katalogiem; wariant
`task-filter-directory--management` zamienia gwiazdki w pierwszej kolumnie
na checkboxy i przenosi gwiazdki do menu wiersza. Nazwa otwiera modal edycji.
`tasks.js` obsługuje zaznaczanie bieżącej strony, stan częściowy i osobny
klucz szerokości `task-filters-management`, wspólny dla zwykłego/scoped URL.
Toolbar i przycisk tworzenia korzystają z wzorca zarządzania Przestrzeniami.

Podstawowe pola korzystają z AncoreCustomSelect, tekstowego wyszukiwania
i istniejących przycisków. Zaawansowany tryb ma pole zapytania i pomoc
ze składnią. Formularz zapisu/edycji korzysta z AncoreTaskModals:
fokus, inert, Escape, potwierdzenie odrzucenia zmian i błędy w dialogu.
Skrypt task-filters.js czeka przy pierwszym ładowaniu na wspólny
AncoreTaskModals (jak spaces.js), dzięki czemu bezpośredni adres formularza
otwiera dialog. Inicjalizuje się także po ancore:content-loaded,
usuwając poprzednie listenery. Częściowa nawigacja aktualizuje gwiazdki
i ulubione w menu. Na telefonie pola zawijają się, a listy przewijają się
we własnym kontenerze. [Zakres funkcji](FILTERS.md).

Przestrzenie, Pulpity i Filtry współdzielą wariant sidebar-nav-group--collection:
ta sama wysokość nagłówka, fokus, plus, trzy kropki i strzałka zastępująca
ikonę przy hover/fokusie. Wiersze Filtrów korzystają z sidebar-space-row,
sidebar-subnav-link i istniejących menu akcji. Ulubione/ostatnie mają
ten sam styl i wspólny limit sześciu skrótów. Panel „Więcej filtrów”
używa core/includes/sidebar_picker.html i space-picker.js; działa także
w zwiniętym pasku i na telefonie. filter-navigation.js obsługuje gwiazdki
z dowolnego ekranu, zachowując aktualny URL oraz przywracając fokus.

Stary moduł Tablice Kanban jest wycofany. Pozostałe opisy jego modeli,
szablonów i wspólnych komponentów są referencją historyczną; nie oznaczają
aktywnych ekranów ani endpointów. Obecne tablice Przestrzeni używają `spaces.SpaceTask`.
[Szczegóły wycofania](MODULES.md#4-wycofany-moduł-tablice-kanban).

## Przestrzenie i zespoły

Szczegóły nowego zadania (`spaces/task_detail.html`) odwzorowują ekran
`tasks/view_task.html`, używając jego powłoki, kontrolek i include'ów przez
`spaces/base.html` oraz `core/base.html`. Nagłówek ma strzałkę powrotu,
tytuł i „Zapisz”. Adres i nawigacja zachowują przestrzeń, a powrót `view`
i filtry. Panel po prawej zawiera widoczność, status, priorytet, tagi,
typ zgłoszenia, kategorię zadania, wykonawcę, trwały klucz z kopiowaniem,
autora oraz daty utworzenia, zamknięcia, wykonania i przypomnienia.
Widoczność jest polem tego samego formularza; właściciel prywatnego zadania
zarządza jego widocznością. Planowanie jest dostępne przez dotychczasową
edycję w przestrzeni; jego wartości są zachowane przy zapisie szczegółów.
Na wąskim ekranie panel przechodzi pod treść, a zakładki przewijają się.

Wszystkie pięć paneli jest renderowane razem. Wspólny `task-work-log.js`
przełącza przyciski zakładek, URL `tab`, ARIA i fokus klawiatury, zachowując
szkic tytułu, opisu i pól. Podzadania mają standardowy toolbar, grupy statusów,
zaznaczanie, sortowanie, usuwanie i modal tworzenia. Dziennik pracy korzysta
z `tasks/includes/work_log_list.html`, `work_log_modal.html` i wspólnego
`core.work_logs.TimeLogForm`: suma minut, paginacja, awatary, edycja i usuwanie
przez modal. Członkowie używają `project_members_panel.html`, wspólnej tabeli
Workspace oraz modali udostępniania i ról; publiczne zadanie pokazuje osoby
z dostępem odziedziczonym. Endpointy tabeli i pickera należą do przestrzeni.
Historia i komentarze współdzielą `task_activity_item.html`, z awatarami,
datami, zmianami pól i kartami/miniaturami załączników.

Pola `DetailForm` należą do `space-task-form` przez atrybut `form`.
`spaces.js` porównuje stan formularza: „Zapisz” jest nieaktywny do zmiany
lub wyboru pliku. Wybrane załączniki można usunąć przed zapisem. Czat używa
wspólnego composera, pickera wzmianek, uploadu i błędów AJAX. Pliki mają
chronione adresy przestrzeni. Inicjalizacja działa również po
`ancore:content-loaded`, z usuwaniem poprzednich listenerów.
`AncoreCustomSelect` wspiera opcjonalne etykiety pustego wyboru i ikony;
picker tagów używa „Tagi”. Nie wprowadzono osobnego systemu kontrolek.


`spaces/base.html` rozszerza `core/base.html` i wspólny kontener katalogu.
Katalog i zarządzanie przestrzeniami współdzielą `spaces/directory.html`
z listą `tasks-directory-sheet`, `tasks-project-sheet`
i `tasks-spreadsheet-sheet`, tak jak projekty i grupy. Wariant `work-space-sheet`
określa kolumny: zaznaczenie, działania, klucz, nazwa, rodzaj, szablon, opis
i liczba zadań. Pierwsze dwie kolumny mają po 40px, jak w Projektach.
Checkboxy `tasks-row-checkbox` są stale widoczne dzięki
`tasks-project-sheet--selectable`; zaznaczenie podświetla wiersz wspólnym stylem.
Wspólny wariant obsługuje też checkbox wewnątrz komórki `data-column="select"`
z rolą `cell`, zachowując centrowanie i widoczność kontrolki.
Checkbox nagłówka zaznacza bieżącą stronę i pokazuje stan częściowego wyboru.
Zaznaczenie jest lokalne, bez operacji zbiorczych. Przycisk trzech pasków korzysta
z `directory_row_menu.html`, `row-actions.js` i `tasks-directory-menu-sheet`.
Include obsługuje opcjonalny `actions_template` dla działań danego modułu.
Menu Przestrzeni otwiera przestrzeń, zmienia osobiste ulubione, otwiera ustawienia
i według uprawnień edycję lub dodawanie osób do prywatnej przestrzeni.
Zachowuje wspólne wysokości wierszy, separatory, zmianę szerokości kolumn,
poziome przewijanie oraz pasek filtrów i wyszukiwania z paginacją na dole. Nazwa otwiera
przestrzeń, a akcja w menu wiersza zmienia osobiste ulubione, zachowując filtry.
`tasks.js` obsługuje zaznaczenie i szerokości, a `space-navigation.js` zapis
gwiazdki oraz przywrócenie fokusu po częściowej nawigacji. Pusty wynik ukrywa nagłówki
i pokazuje komunikat zależny od filtrów/zakładki.
Puste katalogi przestrzeni i zarządzania używają wariantu `work-space-empty-state`
wspólnego `tasks-empty-state`: kolorowej ilustracji 3D
`static/img/empty-states/spaces-empty.webp`, tekstu `tasks-empty-state__copy`
oraz dotychczasowych przycisków tworzenia, przeglądania lub czyszczenia filtrów.
Ilustracja przedstawia warstwy projektów i kolorowe karty zadań, ma przezroczyste
tło, maksymalną szerokość 440px i skaluje się do kontenera na telefonie.
Jest dekoracyjna (`alt=""`, `draggable="false"`), a pusty stan ma `role="status"`.
Katalogi Przestrzeni i Pulpitów (także zarządzanie) oraz przegląd pustego pulpitu
współdzielą `tasks-empty-state--illustrated` i `tasks-empty-state__illustration`:
obraz zajmuje pole 440×330px, z proporcjami 4:3 i `object-fit: contain`.
Cały pusty stan jest wyśrodkowany poziomo i pionowo w dostępnej treści pod
nagłówkiem, zakładkami i filtrami. Na wąskim ekranie obraz proporcjonalnie
maleje, a zbyt niska treść pozostaje przewijana bez ucinania opisu i akcji.
Przyciski zachowują wspólny styl bez podkreślenia tekstu.
Katalog zespołów używa kart.
Przestrzeń ma kontekstowe zakładki
Podsumowanie, Backlog (Kanban/Scrum), Lista, Tablica/Aktywny sprint, Oś czasu,
Raporty, Tagi, Ustawienia. Główna nawigacja pokazuje katalog, ulubione/ostatnie
przestrzenie, Filtry z wyszukiwaniem zadań i Zespoły.

Wiersze backlogu i Listy zadań przestrzeni z prawem edycji używają wariantu `work-issue-row--actions`
z dodatkową kolumną 30px i istniejącym include'em `spaces/item_actions.html`.
Menu oferuje edycję, zmianę statusu i kolejności oraz przeniesienie na tablicę
Kanbana. Obsługuje je wspólny `row-actions.js`, również po podmianie treści.
Obserwatorzy zachowują wiersze bez przycisków zapisu.

Backlog, Lista zadań przestrzeni i kafelki Aktywnego sprintu współdzielą
`spaces/item_planning.html`: awatar przypisanego wykonawcy lub ikonę osoby
oraz, w Scrum, małą etykietę punktów. Zero wyświetla się jako `0`, a brak
estymacji jako `—`. Wariant `work-issue-row--planning` rezerwuje kolumny
punktów i awatara na liście/backlogu; menu z trzema paskami pochodzi z tego
samego `spaces/item_actions.html` i pozostaje dostępne tylko przy prawie
edycji. `show_work_metadata` włącza ten wariant dla listy otwartej przestrzeni;
pozostali odbiorcy `row.html` (Filtry, Dla ciebie, Zespoły i podzadania)
zachowują dotychczasowy wariant.
Nie ma osobnego nagłówka „Planowanie sprintów” ani stałego paska zaznaczania.
`work-backlog-bulk` pojawia się dopiero po zaznaczeniu checkboxu wiersza;
pokazuje liczbę zaznaczonych zadań, przyciski i `AncoreCustomSelect`.
Odznaczenie ostatniego zadania lub „Odznacz” ukrywa cały pasek; fokus wraca
do checkboxu wiersza. Zadania tylko do odczytu są pomijane.
Nagłówki sprintów i Backlogu nie mają checkboxów. Zachowują dotychczasowe kolory,
zwijanie i licznik strony, dodając `work-planning-summary` dla pełnych
agregacji po filtrach. Sekcje mają link do wspólnego modalnego tworzenia
zadania z wybranym backlogiem/sprintem. „Utwórz sprint” znajduje się po prawej
stronie nagłówka sekcji Backlog, przed licznikiem, i pozostaje
widoczne po jej zwinięciu; przycisk widzi osoba zarządzająca przestrzenią Scrum.
Formularze sprintu używają tej samej powłoki, z opcjonalnym podsumowaniem
`work-sprint-preview` i etykietą zapisu.
Bezpośredni adres formularza pokazuje go nad pełnym backlogiem; Escape wraca
do backlogu. Nowa logika odnawia się na `ancore:content-loaded`, usuwa poprzednie
listenery przez `AbortController` i zachowuje częściową nawigację.
Na telefonie kontrolki i metadane zawijają się, a wiersze przewijają wewnątrz sekcji.

Backlog i otwarte sprinty używają `spaces/backlog.html` oraz tej samej powłoki
`tasks-table-wrap tasks-board`, sekcji `tasks-issue-group tasks-status-block`
i nagłówka `tasks/includes/issue_group_header.html` co Lista zadań.
Treść ma wariant `work-content--tasks`, bez dodatkowego paddingu paneli;
wiersze dochodzą do krawędzi sekcji. Nagłówki mają standardową wysokość 40px,
przycisk zwijania i licznik zadań bieżącej strony po filtrach.
Sprint planowany korzysta z koloru kategorii `new`, aktywny z `in_progress`,
a Backlog z neutralnego nagłówka grupy i ikony warstw. Wspólny include obsługuje
opcjonalne `label_suffix` i `details_template`; sprint dodaje nimi stan, daty
i dotychczasową akcję rozpoczęcia/zakończenia. Na wąskim ekranie nagłówek
zawija metadane i przyciski, a wiersze przewijają się poziomo wewnątrz sekcji.
Cel sprintu pojawia się tylko, gdy został podany, i zwija się razem z listą.
Puste sekcje używają `tasks-empty-section` z `role="status"`; brak wyników
backlogu po filtrach ma osobny komunikat. Zwijanie obsługuje istniejący `tasks.js`,
również po częściowej nawigacji. Kolejność planowania i menu wierszy są zachowane.

Wiersze backlogu z prawem edycji mogą być przeciągane w sekcji, pomiędzy
otwartymi sprintami oraz do/z backlogu. Nie pokazują osobnego uchwytu ani
kolumny przeciągania; pierwszym elementem wiersza pozostaje checkbox.
Dotyk korzysta z istniejącej ikony priorytetu i Pointer Events; gest poza nią
nadal przewija listę. Fioletowy obrys wskazuje sekcję docelową, a linia miejsce wstawienia.
Zwinięty nagłówek i pusta sekcja przyjmują zadanie na końcu swojej dostępnej
grupy. Escape anuluje przeciąganie, a dotyk obsługuje przewijanie pionowe
przy krawędzi treści. Zapis korzysta z `X-Work-Action` i istniejącego endpointu
zadania z akcją `plan`; po potwierdzeniu odświeża treść, liczniki i menu,
zachowując filtry oraz URL. Podczas zapisu blokowane jest kolejne
przeciąganie; `aria-busy` i region live informują o stanie oraz wyniku. Błąd nie przestawia wiersza
w DOM i wyświetla komunikat. Obserwator nie ma `draggable` ani obsługi przeciągania dotykiem.
Menu sprintu/backlogu udostępnia te same przeniesienia klawiaturą;
„Przesuń wyżej/niżej” pozostaje alternatywą dla zmiany kolejności.
`tasks.js` pomija własną obsługę drag tych wierszy, które mają
`data-work-backlog-row`; obsługuje je delegacja w `spaces.js`, odnawiana
po `ancore:content-loaded`. Tablica obsługuje osobny gest zmiany statusu i kolejności.

„Aktywny sprint” używa wariantu `work-sprint-board`: kolumny rozszerzają
`tasks-issue-group tasks-status-block` i wspólny `issue_group_header.html`
z Listy zadań. Mają te same kolory kategorii, wysokość 40px, ikony statusów,
liczniki oraz zwijanie klawiaturą i nagłówkiem. `spaces/sprint_card.html`
rozszerza `tasks-issue-row work-issue-row` o zwarty układ w kolumnie: priorytet,
status, klucz i zawijany tytuł, menu działań, wspólny typ zgłoszenia oraz
liczniki tagów/załączników i oznaczenie terminu. Punkty i awatar wykonawcy
znajdują się w metadanych, po typie zadania, jak w backlogu; opcjonalny zespół
pozostaje opisem karty. Białe powierzchnie i podświetlenie zadania
pochodzą z listy. Każde zadanie jest osobnym kafelkiem z pełnym obramowaniem
`--border-color` i zaokrągleniem jak nagłówek kolumny Kanbana. Kafelki mają
odstęp `0.55rem`, a nagłówek statusu jest oddzielony od pierwszej karty
odstępem `0.65rem`, jak w istniejącej tablicy. Kolumna nie ma wspólnej ramki;
pusty stan zachowuje własną ramkę. Karty mają `flex: 0 0 auto`, dzięki czemu długa lista
przewija się pionowo bez ściskania kart i nakładania metadanych. Powłoka
sprintu ogranicza tablicę do miejsca między opisem a dolną paginacją;
lista w kolumnie wypełnia tę wysokość bez stałego offsetu od viewportu.
Każda kolumna sprintu zajmuje pełną dostępną wysokość tablicy, również
gdy jest pusta albo zawiera tylko jeden kafelek; cały ten obszar przyjmuje
upuszczenie zadania do danego statusu.
Kolumny przewijają się poziomo na wąskim ekranie, a opis
sprintu zawija się do dostępnej szerokości. Przeciąganie nadal obsługuje
`spaces.js` przez `data-work-card`; `tasks.js` pomija dla niego własne
listenery przeciągania wierszy. Podczas inicjalizacji tablicy linki i zdjęcia
wewnątrz kart otrzymują `draggable=false`, więc przeciąganie od tytułu,
klucza, awatara i metadanych uruchamia kartę z jej ID i podglądem całego
kafelka. Zwykłe kliknięcie tytułu nadal otwiera zadanie. Menu i kontrolki
nie rozpoczynają gestu; obserwator nie może przeciągać. Podświetlenie celu
obejmuje jedną kolumnę. Podgląd `work-board-drag-preview` jest czytelną,
nieinteraktywną kopią kafelka nad interfejsem: korzysta z istniejących cieni,
lekkiego przechylenia i skali, śledzi kursor z uwzględnieniem zoomu UI
i pozostaje w granicach okna. Nie zawiera ID ani aktywnych hooków menu/form;
ma `inert` oraz `aria-hidden`. Przezroczysty obraz natywnego gestu zapobiega
wyświetleniu drugiego podglądu przez przeglądarkę.
Źródłowy kafelek zachowuje rozmiar, ma przygaszoną zawartość i przerywaną
ramkę. Cel sprintu ma lekko zaakcentowane tło i przerywaną ramkę w nakładce
nad kafelkami, więc linia jest widoczna na całej wysokości. Dodatkowa pozioma,
przerywana linia `work-board-drop-marker` wskazuje miejsce przed lub po
konkretnym zadaniu. Uwzględnia środek kafelka, przewinięcie kolumny i zoom UI;
zwinięta lub pusta kolumna przyjmuje zadanie na końcu. Nakładki nie
przechwytują myszy; kolor pochodzi z `--system-accent`. Przy krawędzi listy
gest przewija pionowo kolumnę, a przy krawędzi tablicy także poziomo.
Obsługa `dragenter` podtrzymuje natywny cel przy zmianie kafelka pod kursorem
podczas przewijania.
Escape, zakończenie gestu i podmiana treści czyszczą
stan przeciągania oraz zatrzymują przewijanie. Można zmienić kolejność
w tej samej kolumnie oraz wybrać dokładne miejsce w innym statusie.
Tylko niezmieniona pozycja nie wysyła zapisu. Akcja `position` zapisuje
`rank` przez istniejący endpoint zadania, z pozycją źródła i obu sąsiadów;
kolejność pozostaje po odświeżeniu i jest współdzielona z listą/backlogiem.
Kolejny gest podczas zapisu jest blokowany; `aria-busy` i region live
informują o zapisie. Błąd lub konflikt zachowuje zadanie w poprzednim
położeniu i pokazuje komunikat. Menu z trzema paskami udostępnia również
„Przesuń wyżej/niżej” jako alternatywę klawiaturową w bieżącej kolumnie.
Po potwierdzeniu zapisu i odświeżeniu treści `is-board-arriving` krótko
podświetla przeniesiony kafelek oraz przewija go do widocznego obszaru.
Efekt znika automatycznie. `prefers-reduced-motion` wyłącza przechylenie,
skalowanie, animację i płynne przewijanie; zachowuje przerywane ramki oraz
krótkie statyczne potwierdzenie.
Tablica Kanbana zachowuje `spaces/card.html` i współdzieli obsługę gestu.

Zakładka „Tagi” zachowuje nagłówek i nawigację otwartej przestrzeni.
`spaces/tags.html` korzysta ze wspólnych include'ów `tag_directory`,
`tag_sort`, `tag_filters`, `tag_modal` i `tag_notes_modal`. Przycisk „Dodaj tag”,
menu wiersza, informacje, notatki, wybór kolumn i operacje zbiorcze obsługuje
istniejący `tasks.js`, również po `ancore:content-loaded`. Obserwator widzi
informacje i notatki bez przycisków zapisu; modal edycji jest niedostępny.
Tabela dochodzi do krawędzi kontenera jak lista zadań. W formularzu zadania
przestrzeni picker „Tagi” korzysta z `AncoreCustomSelect` i lokalnego wyszukiwania.
Modal tworzenia zadania przełącza opcje tagów po wyborze przestrzeni
przez `AncoreTaskTags` w `tasks.js`, zachowując własne dropdowny. Szczegóły
zadania korzystają wyłącznie z tagów jego zapisanej przestrzeni. Dane opcji
są filtrowane przez widoczność projektów; etykiety trafiają do DOM jako tekst.

Osobny ekran „Zarządzaj przestrzeniami” (`spaces/manage.html`) używa tej samej
powłoki. Główny pasek boczny przełącza się na minimalne menu danej strony,
według wzorca katalogu Workspace. Wspólny wariant
`core/includes/management_sidebar.html` renderuje osobne menu Przestrzeni,
Pulpitów i Filtrów: nagłówek „Zarządzanie…”, „Wróć do ustawień” oraz jedną
aktywną pozycję z nazwą modułu. Nie zawiera kategorii centrum Ustawień
ani linków pozostałych stron zarządzania. Strony otwiera się z wierszy
sekcji Workspace w centrum Ustawień. „Wróć do ustawień” prowadzi do `#workspace`.
Treść zajmuje całą szerokość obok tego paska. Oba warianty menu używają wspólnych klas i zachowują zwijanie,
zmianę szerokości oraz mobilne otwieranie/zamykanie. `layout.js` przełącza
widoczną nawigację również przy częściowym przejściu, powrocie i historii
przeglądarki. Bezpośrednie wejście do kreatora/edycji używa trybu administracyjnego.
Tabela ma te same kolumny, szerokości i awatary co „Przestrzenie”: checkbox,
menu z trzema paskami, Klucz, Przestrzeń, Rodzaj, Szablon, Opis i Zadania.
Checkboxy zaznaczają tylko bieżącą stronę, bez operacji zbiorczych.
`work-space-sheet--management` wybiera osobny klucz `spaces-management`
dla preferencji kolumn w `tasks.js`, wspólny dla zwykłego i scoped URL;
nie nadpisuje wspólnej siatki. Filtry rodzaju i sposobu zarządzania są po lewej,
wyszukiwarka po prawej, a paginacja na dole panelu. Nazwa przestrzeni otwiera ustawienia.
Wspólne menu `spaces/directory_row_actions.html` zachowuje osobistą gwiazdkę,
otwarcie, edycję, ustawienia dostępu i konfigurację zadań według uprawnień.
Formularze, `row-actions.js` i obsługa częściowej nawigacji pozostają wspólne.
Menu „…” w głównej nawigacji zawiera wyłącznie „Zarządzaj przestrzeniami”;
dostępność zarządzania odświeża się po częściowej nawigacji.
Skrót Favorites „Przestrzenie” pozostaje aktywny tylko w codziennym module,
a ekran zarządzania aktywuje ikonę Ustawień. Przy braku odpowiadającego linku
w menu JS zachowuje stan aktywności skrótu otrzymany z serwera, także po częściowej
nawigacji. Szczegóły uprawnień: [SPACES.md](SPACES.md).

Centrum „Ustawienia” (`/settings/`) jest osobną stroną z własnym wariantem
głównego paska bocznego (`core/includes/settings_sidebar.html`). Zastępuje
menu Workspace kategoriami Ogólne, Konto i dostęp i Workspace.
Trzy linki zarządzania znajdują się w treści sekcji Workspace, bez duplikatów
w bocznym menu. Link przestrzeni zależy od istniejącego prawa zarządzania. Na stronie centrum
jest „Wróć do przestrzeni”. Strony zarządzania mają osobne minimalne menu
z linkiem „Wróć do ustawień”.
Sekcja Workspace centrum zawiera również wiersze prowadzące do tych stron.
Treść nie ma dodatkowej wewnętrznej nawigacji;
wiersze, podsumowanie konta i kontrolki zachowują dotychczasowy wygląd.
`settings.js` obsługuje kategorie w stałej powłoce, aktywne pozycje, adresy
z fragmentem (`#account`, `#workspace` i skrót `#security`),
historię Wstecz/Dalej i ponowne wejście po częściowej nawigacji. Wybór kategorii
zamyka menu na telefonie; stan zwinięcia i szerokość są wspólne z resztą aplikacji.
Wyjście ze strony usuwa jej listenery.
Sekcja Preferencje i jej opcje są usunięte z Ustawień; zwijanie menu i panel
powiadomień pozostają dostępne przez kontrolki wspólnej powłoki aplikacji.
Profil nie odsyła już do usuniętych opcji. Dla zgodności
stare fragmenty `#preferences`, `#appearance`, `#notifications` i `#region`
otwierają widok Ogólne.

Sekcja „Starsze widoki” wraz z Projektami, Ulubionymi projektami, Grupami,
Zadaniami i Szablonami projektów jest usunięta. Menu zachowuje Przestrzenie,
Filtry i pozostałe aktywne moduły, także po częściowej nawigacji,
zwinięciu sidebaru i na telefonie.
Globalny katalog „Tagi” nie ma pozycji menu, skrótów Favorites ani modali
w katalogu Zadań; tagi są dostępne wyłącznie w zakładce przestrzeni.
Stary Kanban nie ma pozycji menu; jego dawne adresy służą wyłącznie
przekierowaniom do Przestrzeni i zaimportowanych zadań.
Katalogi Kontaktów, Firm, Użytkowników i Gości zostały wycofane także
z wyszukiwania, ulubionych i częściowej nawigacji; stare adresy zwracają 404.

Nagłówek otwartej przestrzeni pokazuje awatar i nazwę, bez strzałki powrotu
i klucza obok niej. Nazwa ma rozmiar 17px i grubość 700 (`work-space-title`).
Ten sam nagłówek obowiązuje we wszystkich jej zakładkach.
Tytuł „Przestrzenie” w katalogu również ma rozmiar 17px i grubość 700.
Nagłówek otwartej przestrzeni, pasek zakładek i treść podsumowania mają po 22px
odstępu z lewej i prawej strony, również na telefonie. Wspólna zmienna
`--work-space-inline-padding` obejmuje też katalog Przestrzeni: jego nagłówek,
zakładki i filtry. Tabele katalogu oraz zarządzania w `work-content--directory`
dochodzą do obu krawędzi kontenera, jak tabele Workspace i Projektów, również
na telefonie. Lista zadań i tablica wewnątrz przestrzeni nadal korzystają
z pełnej szerokości; katalog Zespołów zachowuje własne odstępy.
Awatar ma 32px w nagłówku, 24px w katalogu, 20px w codziennym menu bocznym
i 21px w panelu zwiniętego paska.
W katalogu odstęp między awatarem a nazwą przestrzeni wynosi 8px.
Include `spaces/avatar.html` rozszerza wspólny `profile-avatar`; globalny
`space-avatars.css` zapewnia jego wygląd również poza modułem Przestrzeni.
Zapis odświeża awatar w menu przy częściowej nawigacji.
Przy każdej częściowej nawigacji `layout.js` synchronizuje całe podmenu
przestrzeni z HTML serwera: dodaje nowe pozycje, usuwa nieobecne, aktualizuje
nazwy, awatary, grupy, dozwolone akcje i kolejność. Nowo utworzona przestrzeń pojawia się od razu po
zapisie, bez ręcznego odświeżenia. Grupa, stan zwinięcia i „Więcej przestrzeni”
pozostają zachowane; nowy link także zamyka menu na telefonie po wyborze.

Osoby zarządzające przestrzenią klikają jej awatar lub „Zmień awatar”
w ustawieniach. Okno korzysta z `app-modal-panel--compact`, standardowej
stopki i `AncoreTaskModals`. Zawiera 30 kolorowych ilustracji, wybór automatyczny
oraz upload z podglądem i przeciąganiem. Natywna grupa radio zapewnia wybór
klawiaturą; zaznaczenie ma fioletową ramkę. Na telefonie siatka dopasowuje
liczbę kolumn. Zapis, błędy, szkic, Escape i fokus obsługuje `spaces.js`.
Ilustracje mają pełnokolorowe tła i wypełnione kształty. Korzystają z dwóch
lokalnych atlasów PNG w `static/img/space-avatars/` i klas `space-avatar-art--*`.
Atlas `illustrations-extra-v1.png` dodaje aparat, słuchawki, góry, diament, kawę
i balon. Wybór automatyczny nadal korzysta z pierwotnych 24 ilustracji,
dzięki czemu rozszerzenie nie zmienia istniejących przypisań.
Zachowują stabilne identyfikatory wcześniejszych ikon. W pickerze mają 56px
(40px na telefonie); pozostałe rozmiary awatarów pozostają bez zmian.
Zestaw jest współdzielony z Workspace, a ikony kontrolek nadal używają
`AncoreIcons`. Wybór ilustracji czyści niezapisany plik, a zamknięcie zwalnia jego podgląd.
Zakładki katalogów przestrzeni i zespołów oraz widoków przestrzeni używają
wspólnego `work-tabs`: tekst 13,5px/400 również na telefonie, tę samą wysokość
i odstępy z `notifications-tabs`. Dekoracyjne ikony z `AncoreIcons` mają we
wspólnym pasku 18px i odstęp 8px od etykiety. Katalog przestrzeni używa `layers`
przy „Wszystkie”, `star` przy „Ulubione” i `lock` przy „Prywatne”; widoki
przestrzeni (`work-tabs--views`) zachowują ikony odpowiadające widokom. Wszystkie paski zachowują
wspólne podkreślenie aktywnej zakładki i przewijanie poziome na wąskim ekranie.
Najechanie na nieaktywną zakładkę pokazuje szare
podkreślenie (`--system-interaction`), tak jak w katalogu Zadań; po odsunięciu
kursora podkreślenie znika. Aktywna zakładka zachowuje fioletowe podkreślenie
także pod kursorem. Katalog zespołów ma zakładki bez ikon.

Nagłówek „Przestrzenie” zwija i rozwija podmenu przez wspólny
`data-sidebar-group="spaces"` w `layout.js`. Stan zapisuje istniejąca
preferencja `ancoreSidebarCollapsedGroups`; pozostaje zachowany po odświeżeniu
i częściowej nawigacji. Przycisk ma `aria-controls` i `aria-expanded`
oraz obsługuje Enter/Spację. Przed nazwą jest ikona warstw (`layers`), która
przy najechaniu lub fokusie klawiatury zmienia się w strzałkę zwijania (`chevron-down`),
obróconą w prawo dla zwiniętej sekcji. Fokus klawiatury zaznacza całą powłokę
nagłówka fioletową ramką. W trybie zwiniętego całego paska ikona nadal otwiera
panel skrótów. Ikona warstw oznacza również Przestrzenie
w Favorites (także dla starszych zapisanych skrótów), nagłówku kolumny katalogu
oraz jego pustym stanie. Wspólny wariant `sidebar-group-header` umieszcza
obok przycisku zwijania „+” otwierający kreator i „…” z opcją „Zarządzaj
przestrzeniami” (według uprawnień). Obie ikony mają 13px w przyciskach 28px
(`--control-height` minus 4px). Nagłówek ma wspólne zaokrąglone szare tło
oraz wysokość 32px, tak jak pozostałe pozycje codziennego menu. Minimalna
wysokość jego powłoki korzysta z `--dropdown-menu-item-height`, jak sam
przycisk; nie powiększa tła do 36px z wariantu zwiniętego paska.
Szare tło pojawia się
po najechaniu, przy fokusie klawiatury lub otwartym menu. Token
`--sidebar-interaction-bg` (`#e9ebef`) zapewnia ten sam kolor hover dla Dashboardu
i pozostałych pozycji menu; obejmuje też szare podświetlenia wierszy przestrzeni,
otwarty przycisk „Więcej przestrzeni” oraz zwinięty pasek i jego panel skrótów.
Fioletowe zaznaczenie wybranej pozycji pozostaje odrębne. Fokus pozostający
po kliknięciu myszą nie utrzymuje tła ani strzałki po odsunięciu kursora.
Plus i trzy kropki otrzymują
dodatkowe szare podświetlenie bez ramki przy najechaniu, fokusie klawiatury
lub otwarciu menu. Dodatkowa warstwa ikon używa `--system-interaction-soft`.
Menu korzysta z `row-actions.js`, natywnego popovera i stylów
menu Zadań; obsługuje klawiaturę, Escape i przywrócenie fokusu. Skrót katalogu
w Favorites zachowuje klucz `spaces`. Podmenu używa wariantu
`sidebar-subnav--spaces`: płaskie wiersze o wysokości 32px, bez
linii drzewa, z podpisami „Oznaczone gwiazdką” i „Ostatnie”. Gwiazdki są
osobiste; ostatnie przestrzenie uwzględniają kolejność odwiedzin z sesji,
z uzupełnieniem przez najnowsze. Łączny limit pozostaje równy sześć.
Puste bloki ukrywają podpisy. Podlista ma wcięcie 14px względem nagłówka;
podpisy i awatary stoją w tej samej kolumnie, 6px od jej krawędzi. Awatar ma
20px, a odstęp do nazwy wynosi 6px. Nazwy przestrzeni i pozycji codziennej
nawigacji mają wagę 600 również na wewnętrznych `span`, pomimo globalnej
reguły wagi 400. Pozycje codziennej nawigacji również mają wysokość 32px;
zwinięty pasek zachowuje dotychczasowe wymiary. Tło głównego paska bocznego
jest takie samo jak górnego paska aplikacji: `--sidebar-bg` (`#FBFBFC`), także
w codziennym menu Workspace, po zwinięciu i na telefonie.
Wybrana pozycja (`a.nav-link.active`) ma jasne fioletowe
tło, fioletowy tekst/ikonę i krótki znacznik przy lewej krawędzi. Ta sama reguła
obejmuje Dashboard, pozostałe moduły, Favorites oraz kategorie
Ustawień i menu zarządzania. Wybrana pozycja zachowuje fioletowy stan pod
kursorem; szary hover i fokus nieaktywnej pozycji nie oznaczają wyboru.
Otwarcie menu lub rozwinięcie sekcji także nie wybiera punktu nawigacji.
Dotychczasowa klasa `active` pochodzi z serwera i jest synchronizowana przy
częściowej nawigacji; Ustawienia przełączają ją przy wyborze kategorii.
Lokalne zmienne
`--sidebar-space-selection`, `--sidebar-space-selection-bg`, `--sidebar-space-focus`
i `--sidebar-space-marker` są współdzielone przez cały główny pasek boczny
i jego panel skrótów. Kolor zaznaczenia, ramki fokusu i znacznika wynosi
`#5b5fc7`, a jasne tło `#e8ebfa`. Ten wariant menu używa palety `brandTeams`
jasnego motywu [Microsoft Fluent UI](https://github.com/microsoft/fluentui/blob/master/packages/tokens/src/global/brandColors.ts).
Menu boczne współdzieli główny token akcentu aplikacji `--system-accent`.
Przy zwiniętym pasku nagłówek grupy z aktywnym podpunktem
także ma fioletowy stan. Długie nazwy zachowują wielokropek
oraz pełną nazwę w `title`. Pozostałe podmenu zachowują dotychczasowe drzewka.

Wariant `sidebar-space-row` dodaje „…” widoczne przy najechaniu/fokusie
i otwartym menu; na urządzeniach dotykowych i telefonie przycisk jest stały.
Szare tło wiersza pojawia się przy najechaniu, fokusie klawiatury lub otwartym
menu; sam fokus po kliknięciu myszą go nie utrzymuje. Aktywna przestrzeń
zachowuje własne fioletowe zaznaczenie niezależnie od fokusu.
`sidebar-space-menu` rozszerza wspólne `tasks-section-menu` i `row-actions.js`:
osobista gwiazdka, dodawanie osób według praw zarządzania prywatną przestrzenią,
ustawienia oraz neutralna stopka z rodzajem i sposobem zarządzania.
Zachowuje Escape, strzałki, powrót fokusu i pozycjonowanie wewnątrz viewportu.
`space-navigation.js` obsługuje formularz gwiazdki także poza modułem Przestrzeni,
odświeża bieżący ekran bez zmiany adresu i przywraca fokus do menu wiersza.
Podział, wiersze i ich akcje działają także w panelu zwiniętego sidebaru;
klony otrzymują osobne identyfikatory powiązane z etykietami i popoverami.

Na końcu znajduje się przycisk „Więcej przestrzeni” z ikoną `align-left`
i strzałką w prawo. Otwiera niemodalny panel `sidebar-space-picker` obok menu,
z tytułem, zamknięciem, wyszukiwaniem i linkiem „Wyświetl wszystkie przestrzenie”.
Przycisk ma przezroczyste tło w spoczynku; podświetla się przy najechaniu,
fokusie klawiatury lub otwartym panelu.
Wariant rozszerza komponenty wyszukiwania Workspace i nagłówka panelu skrótów.
Tytuł „Przestrzenie” w tym panelu ma grubość 700.
Wiersz wyniku ma stałą kolumnę awatara 24×24px, odstęp 8px i elastyczną nazwę
z wielokropkiem. Reguły rozciągania tekstu nie obejmują awatarów.
Wyszukiwanie po nazwie lub kluczu obejmuje wszystkie dostępne przestrzenie
bieżącego Workspace, z limitem 20 wyników; link do katalogu zachowuje zapytanie.
Bez zapytania panel pokazuje samą wyszukiwarkę i link, także przy pustym Workspace.
`core/includes/sidebar_picker.html` i `space-picker.js` są wspólnym komponentem
paneli Przestrzeni i Pulpitów (`data-sidebar-picker` i `data-sidebar-picker-toggle`).
Skrypt obsługuje opóźnienie 200ms, anulowanie nieaktualnych żądań,
stan pusty/błąd, strzałki klawiatury, Enter, Escape oraz powrót fokusu.
Błąd pokazuje wyłącznie komunikat; zmiana zapytania uruchamia nowe wyszukiwanie.
Natywny popover zamyka się po kliknięciu poza panelem; wybór linku zamyka menu na
telefonie. Panel działa po częściowej nawigacji i mieści się w wąskim ekranie.
Wariant `sidebar-subnav--extended` mieści sześć przestrzeni oraz przycisk
bez przycinania wysokości. Przy zwiniętym
całym sidebarze ikona otwiera panel skrótów zawierający także tworzenie
i zarządzanie przestrzeniami (`data-sidebar-group-action`). Na telefonie
zwijanie działa wewnątrz otwartego menu, a wybór akcji nawigacyjnej je zamyka.

`spaces/form.html` korzysta z `AncoreTaskModals`, wspólnych klas formularza,
ikon i `AncoreCustomSelect`. `spaces.js` obsługuje fokus, Escape, ostrzeżenie
o szkicu, błędy zapisu, inert tła i ponowne wejście przez `ancore:content-loaded`.
Tworzenie przestrzeni ma dwa kroki w tym samym oknie. Najpierw
`spaces/template_picker.html` pokazuje sześć przycisków-kafelków z opisami
oraz lokalnymi ilustracjami SVG w `static/img/space-templates/`. Każda ilustracja
ma własny kolor akcentu i dopasowane jasne tło: Kanban — niebieski, Scrum —
fioletowy, Zarządzanie zadaniami — zielony, Marketing — pomarańczowy,
Rekrutacja — różowy, Obsługa zgłoszeń — turkusowy. Ten sam plik jest używany
w podsumowaniu wyboru w drugim kroku. Kolory ilustracji są dekoracyjne;
kontrolki i zaznaczenie zachowują wspólny akcent aplikacji. Wariant
`work-template-card` rozszerza `work-space-card`; siatka ma trzy kolumny na
desktopie, dwie na tablecie i jedną na telefonie. Enter/Spacja wybierają
szablon i przenoszą fokus do nazwy. Rodzaj przestrzeni wynika z szablonu.
Pola danych pozostają ukryte i wyłączone przed wyborem; przycisk tworzenia
jest widoczny tylko w drugim kroku. Podsumowanie pokazuje ilustrację, szablon
i rodzaj. „Zmień szablon” wraca do kafelków bez kasowania danych i przywraca
fokus do wybranego kafelka. Błędy zapisu zachowują drugi krok, wybór i szkic;
nieznany szablon wraca do pierwszego kroku z błędem. Edycja istniejącej
przestrzeni oraz inne formularze nadal używają dotychczasowego układu.
Kreator przestrzeni otwierany bezpośrednio przez URL pokazuje modal nad pełnym
katalogiem (`spaces/index.html`), tak jak formularze Zasobów. Po zamknięciu
`data-work-directory-url` przywraca adres katalogu bez przeładowania i bez
dodatkowego wpisu w historii. Plus w menu bocznym oraz w panelu zwiniętego
sidebaru używa `data-work-open`; na ekranach Przestrzeni i Zespołów działa nad
bieżącą treścią. W innych modułach otwiera kreator nad katalogiem.
Listy zadań w przestrzeni, „Wyszukaj zadania” w Filtrach oraz zadania zespołu zachowują
wygląd Zadań: `tasks-status-block` z kolorowym nagłówkiem i zwijaniem oraz
wiersze `tasks-issue-row` z priorytetem, stanem, tagami, załącznikami i terminem.
Wspólny `work-issue-row` w `spaces.css` podświetla cały wiersz przy najechaniu
lub fokusie klawiatury wewnątrz: 8% `--system-accent` na białym tle, pasek 3px
po lewej i przejście 0,12s, tak samo jak w „Dla ciebie”. Link nazwy nie ma
podkreślenia przy najechaniu. Wzorzec obejmuje też backlog i sprinty;
zaznaczenie checkboxa utrzymuje to samo fioletowe tło i pasek również po
odsunięciu kursora i utracie fokusu, tak jak zaznaczenie w katalogu Projektów.
Include `spaces/issue_type.html` dodaje wspólne oznaczenie `tasks-issue-type`:
ikonę z lokalnego `AncoreIcons` i nazwę typu zgłoszenia w neutralnym tle.
Oznaczenie jest widoczne po prawej stronie wiersza, bezpośrednio przed licznikiem
tagów, oraz w metadanych karty; długą nazwę skraca wielokropek, a pełną udostępnia
`title` i etykieta dostępności. Wspólny wiersz `work-issue-row` ma osobną kolumnę
typu również w backlogu i sprintach; „Dla ciebie” zachowuje ten układ bez checkboxa.
Kolumna klucza i tytułu może się zwężać, zachowując wielokropek i jedną linię metadanych.
`IssueTypeSelect` używa istniejących ikon opcji `AncoreCustomSelect` w formularzu
przestrzeni i szczegółach zadania. Ikony typu mają wspólne kolory w opcjach,
wybranej wartości, filtrze, wierszach, kartach i podsumowaniu: Zadanie — niebieski,
Błąd — czerwony, Historyjka — zielony, Epik — fioletowy. Materiał i Zgłoszenie
używają niebieskiego, Incydent czerwonego, Kandydatura fioletowego, a Kampania
i Rozmowa bursztynowego. Barwy pochodzą z obecnych statusów, priorytetów i akcentów;
nieznany typ zachowuje neutralną ikonę. Nazwy i tła kontrolek pozostają standardowe,
a kolory dotyczą tylko ikon w komponentach typu zgłoszenia.
Toolbar zawiera filtr „Typ zgłoszenia”;
dotychczasowe pole biznesowe w szczegółach ma etykietę „Kategoria zadania”.
Pierwsza kolumna wiersza zawiera stale widoczny, standardowy `tasks-row-checkbox`
z etykietą zawierającą kod i tytuł zadania. Zaznaczenie myszą lub Spacją podświetla
wiersz przez wspólne style; nie zmienia statusu zadania. Wiersze list nie pokazują
menu trzech pasków; backlog i sprinty udostępniają je osobom z prawem edycji
przez `spaces/item_actions.html`. Checkbox służy lokalnemu zaznaczeniu,
bez operacji zbiorczych i utrwalania wyboru po zmianie widoku.
Grupowanie dotyczy dostępnej strony wyników; rozróżnia nazwy własnych statusów
nawet wtedy, gdy mają tę samą kategorię. Backlog zachowuje kolejność planowania.
Na telefonie lista zachowuje kolumny i przewija się poziomo we własnym obszarze.
Tablica używa dotychczasowych `tasks-kanban-column` i `tasks-kanban-card`,
włącznie z oznaczeniem zakończonych kart. Nie ma osobnej tabeli ani szarych
paneli zastępujących te komponenty. Filtry korzystają z paska Zadań,
a paginacja z dolnego paska Przestrzeni.

Karty tablicy w `item_actions.html` używają wspólnego menu `row-actions.js`: otwarcie zadania,
edycja, dozwolone przejścia statusów i planowanie. Menu działa klawiaturą,
zamyka się przez Escape i przywraca fokus; zastępuje stałe formularze na karcie.
Przeciąganie tablicy nadal obsługuje `spaces.js`. Elementy nie mają klasy
`task-row` ani danych dawnego API Kanbana. `tasks.js` pomija lokalne filtrowanie
grup na `data-work-page`, aby nie ukrywać wyników filtrowanych przez serwer.

`spaces.css` zawiera tylko adaptery kontekstu przestrzeni oraz style katalogów,
podsumowania, osi czasu, raportów i konfiguracji. Geometria wierszy, kolumn, kart i menu
pochodzi ze wspólnych komponentów. [Funkcje](SPACES.md).

Zakładka „Podsumowanie” używa `spaces/summary.html` i lokalnego wariantu
`work-summary` wspólnych `work-panel` i `work-metrics`. Układ nawiązuje do
[podsumowania Jiry](https://support.atlassian.com/jira-software-cloud/docs/what-is-the-summary-view/):
cztery liczniki u góry, przegląd statusów i ostatnia aktywność w pierwszym rzędzie,
priorytety i typy zgłoszeń w drugim, a obciążenie zespołu i opcjonalny postęp
epików poniżej. Panel statusów centruje mniejszy, cienki pierścień SVG obok
zwartej legendy z separatorami wierszy i licznikami na neutralnym tle.
Na telefonie pierścień zmniejsza się do 120px, a nagłówek zawija odnośnik,
gdy brakuje miejsca; do 360px legenda przechodzi pod wykres. Panel nie
rozciąga się do wysokości sąsiedniej aktywności.
Wykres i legenda zachowują paletę kategorii statusów
z listy zadań, ze wzmocnioną czytelnością na białym tle. Używają pełnych kolorów
ikon statusów (`--tasks-status-color`) z `theme/elestio.css` przez klasy
`status-*`; własne statusy przyjmują kolor swojej kategorii. Nagłówki listy
zachowują jasne tła. „Podział priorytetów” używa szarych słupków opartych na
`--system-interaction`, wspólnych osi oraz poziomej siatki. Skala zaczyna się
od zera i ma trzy oznaczenia, dopasowane do największej liczby otwartych zadań.
Wysokości są liniowe; zero nie tworzy słupka. Kolorowe ikony priorytetów stoją
obok polskich etykiet, a na telefonie nad nimi. „Typy zgłoszeń” mają kolumny
„Typ” i „Rozkład” oraz szare, prostokątne paski `progress` o wysokości 24px.
Procenty są wewnątrz pasków; przy małym udziale stoją w jasnej części, a zero
pozostawia pusty pasek. Liczby zadań są w etykiecie dostępności i podpowiedzi.
Na telefonie rozkład przechodzi pod nazwę typu. Panel dopasowuje wysokość do
wierszy i zawiera podkreślony odnośnik do wszystkich zadań. Pozostałe natywne
`progress` w postępie epików zachowują fioletowy akcent.
„Obciążenie zespołu” korzysta z tego samego wariantu
`work-summary-bars--distribution`: kolumny „Osoba przypisana” i „Rozkład prac”,
szare paski 24px i procenty wewnątrz. Nazwy zachowują awatary; nieprzypisane
zadania mają neutralną ikonę osoby. Liczby otwartych zadań pozostają w podpowiedzi
i etykiecie dostępności. Podkreślony link „Zmień przypisanie zadań” otwiera listę;
wiersz osoby otwiera jej otwarte zadania. Panel dopasowuje wysokość do wierszy,
na telefonie paski przechodzą pod osoby, a pusty stan nie pokazuje nagłówków kolumn.
Ikony priorytetów i awatary pochodzą ze standardowych include'ów. Panele
zachowują font, ramki, tło, zaokrąglenie i odstępy Ancore. Przy szerokości
do 1099px tworzą jedną kolumnę, a liczniki dwie. Na telefonie poziome paski
przenoszą się pod etykiety. Długie nazwy zadań, epików i wykonawców zachowują
pełny tekst w `title`; aktywność i dłuższe listy przewijają się w panelu.
Całe podsumowanie przewija się we wspólnym `work-content`.

Liczniki i elementy wykresów są natywnymi linkami GET obsługiwanymi przez
`AncoreApp`; nie wymagają nowego JavaScriptu. Lista przestrzeni oferuje
standardowe selecty statusu, priorytetu i wykonawcy, także „Nieprzypisane”.
Opcje wykonawców pochodzą wyłącznie z dostępnych zadań tej przestrzeni.
Zakres czasu lub otwartych zadań w drill-downie ma widoczną etykietę oraz
„Usuń filtr”, które zachowuje pozostałe filtry. Toolbar zawija kontrolki.
Puste podsumowanie pokazuje zera i opisy bez pustej tabeli ani paginacji.


## 1. Cel i punkt odniesienia

Nowe funkcje mają wyglądać i zachowywać się jak część obecnego Ancore.
Punktem odniesienia są istniejące ekrany i komponenty opisane poniżej.

Historyczne modale projektów oraz wspólne tabele pozostają źródłem komponentów
używanych przez bieżące moduły. Katalog i edytor Szablonów projektów są wycofane;
ich endpointy nie udostępniają formularzy. Szablony tworzenia Przestrzeni
zachowują dotychczasowy kreator. Kalendarz pokazuje terminy zadań Przestrzeni
z linkami do ich aktualnych szczegółów.
Ten dokument utrwala aktualny styl; zmiana całego stylu wymaga zadania
obejmującego redesign.

Pierwszy opis powstał z przeglądu szablonów, CSS i JS. Nie jest pomiarem
wszystkich końcowych stylów w przeglądarce. Przed zmianą wizualną obejrzyj
referencyjny ekran w tej samej szerokości i stanie co ekran zmieniany.

Formularze „Nowy projekt” i „Edytuj projekt” mają pole „Widoczność” po prawej
stronie „Nazwa projektu”, w pierwszym wspólnym wierszu `tasks-project-heading-fields`.
Na ekranach do 600px pola układają się pionowo: nazwa, następnie widoczność.
W formularzu tworzenia dalej znajdują się „Opis”, „Szablon projektu” i parametry projektu.
Kontrolka używa istniejącego `tasks-inline-select` i `AncoreCustomSelect`:
„Publiczny — cały Workspace” oraz „Prywatny — wybrane osoby”. Domyślny nowy projekt
jest prywatny, także po wyborze publicznego szablonu. Otwarcie edycji z wiersza, zaznaczenia lub menu projektu pobiera
bieżącą widoczność przez `data-project-visibility`; błędy zachowują wybór.
„Prywatny” ma ikonę `lock`, a „Publiczny” ikonę `users`, zarówno w zamkniętym
polu, jak i na liście. `ProjectVisibilitySelect` nadaje opcjom
`data-ancore-option-icon`; wspólny `AncoreCustomSelect` renderuje ten opcjonalny
atrybut przez `AncoreIcons`, zachowując tekst i wskaźnik zaznaczenia. Ikony są
dekoracyjne (`aria-hidden`), mają 16px i dziedziczą kolor kontrolki.
Wspólny select obsługuje także `data-ancore-option-preview` wskazujący ID
lokalnego `<template>`. Klonuje jego pierwszy element jako dekoracyjną
miniaturę w opcji i przy jednej wybranej wartości. Brak szablonu zachowuje
zwykłą ikonę lub tekst; ponowne odświeżenie zastępuje poprzednią miniaturę.
Pole wykonawcy w szczegółach oraz formularzach zadań i Przestrzeni używa
`accounts.widgets.UserChoiceField` i `UserSelect`: imię i nazwisko (także zapisane
drugie imię), z e-mailem lub nazwą konta jako zastępstwem przy braku danych.
W opcjach i wybranej wartości pojawia się awatar 24px ze wspólnego
`accounts/includes/user_avatar.html`: zdjęcie profilowe albo istniejący awatar konta.
Lokalne szablony podglądów są generowane tylko z użytkowników dopuszczonych
przez queryset pola; tooltip awatara udostępnia pełną nazwę i e-mail.
„Brak osoby” pozostaje opcją bez awatara. Wartością formularza nadal jest PK osoby.
Nowy projekt ma formularz główny. Po utworzeniu okno „Edytuj projekt” ma
zakładki „Główna” i „Członkowie”. `notifications-tabs` obsługuje strzałki,
Home i End. Członkowie korzystają ze wspólnego `members_table.html` Workspace:
zaznaczenie, menu, avatar i nazwa, e-mail, rola, data dołączenia. Parametr
`project_team` wybiera akcje projektu; układ sześciu kolumn i przewijanie są wspólne.

„Udostępnij” otwiera kompaktowe okno z pickerem konta
(`AncoreTeamInvitationPicker` z `workplace-team.js`) oraz rolą. Wariant
`data-sharing-picker` ma komunikaty udostępniania, bez treści o zaproszeniach.
Wyszukiwanie obejmuje aktywnych członków Workspace poza obecnymi uczestnikami.
Po zapisie osoba od razu trafia do tabeli członków, a projekt jest dla niej
widoczny przy kolejnym odczycie listy. Nie ma zakładki wysłanych zaproszeń ani
okna akceptacji projektu/grupy. Zaproszenia do Workspace zachowują własny przepływ.

Menu członka pozwala zmienić rolę i odebrać dostęp zgodnie z uprawnieniami.
Checkboxy zaznaczają wiersze. Publiczny projekt pokazuje zespół Workspace
oraz informację o wspólnym dostępie, bez osobnego udostępniania.
`project-team.js` pobiera tabelę i zapisuje operacje przez AJAX, zachowując
niezapisane pola głównej zakładki. Błędy pozostają w aktualnym oknie.
W zakładce zespołu stopka ma „Zamknij”; zapis pól projektu jest na „Główna”.
Widoczność prywatnego projektu zmienia wyłącznie jego właściciel.
Okna udostępnienia i roli używają `AncoreTaskModals`, `inert`, Escape i przywrócenia
fokusu. Ponowna inicjalizacja po `ancore:content-loaded` anuluje stare listenery,
pickery i żądania. Wybór innego projektu zeruje stan i ignoruje spóźnione odpowiedzi.
`project-access-data` zawiera uprawnienia do edycji i widoczności oraz URL zespołu
projektów dostępnych odbiorcy. Układ pól zachowuje `modal-system.css`.

Udostępnianie i zmiana roli oferują „Członek”, „Administrator” oraz „Obserwator”;
administrator projektu nadaje tylko role członka i obserwatora. `TeamRoleSelect`
używa ikon `user-round`, `shield-check` i `eye` przez `AncoreCustomSelect`.
Obserwator otwiera „Podgląd projektu” z ikoną `eye`, wyłączonymi polami,
listą członków i stopką „Zamknij”. Zadania używają istniejącego wariantu
`tasks-issue-form--readonly`, bez kompozytora czatu, edycji czasu i plików.
Notatki pozostają widoczne bez formularzy zapisu. Uprawnienia wierszy wyłączają
przeciąganie i operacje zbiorcze. Otwarcie edytowalnego projektu przywraca kontrolki.

Formularze grup korzystają z tego samego wiersza nazwy i widoczności co projekty.
„Nowa grupa” domyślnie wybiera „Prywatna — wybrane osoby”; „Publiczna — uczestnicy
projektu” zachowuje ograniczenia projektu nadrzędnego. Po utworzeniu „Edytuj grupę”
ma wspólne zakładki „Główna” i „Członkowie”, picker osoby, tabelę oraz modale
roli/udostępnienia. `project-team.js` inicjalizuje osobne instancje projektu, grupy i zadania,
zachowując kontrakt `data-project-*` wewnątrz formularza. Prefiksy identyfikatorów
pozwalają obu oknom współistnieć na stronie. `section-access-data` przekazuje
widoczność, uprawnienia oraz URL zespołu. Menu obserwatora udostępnia „Podgląd grupy”
z wyłączonymi polami i listą członków. Obsługa błędów, szkicu, fokusu, Escape
i ponownego wejścia po częściowej nawigacji pozostaje wspólna.

W szczegółach zadania „Widoczność” jest pierwszą sekcją bocznego panelu.
Zakładka „Członkowie” korzysta z istniejącego systemu zakładek `task-work-log.js`
i wspólnej tabeli zespołu. `project-team.js` obsługuje `task-detail-form` oraz
osobny host modali `data-project-team-modal-host="task"`; zachowuje szkic pól,
błędy, fokus, Escape i inicjalizację po `ancore:content-loaded`. Po zapisaniu
widoczności przez AJAX zdarzenie `ancore:task-team-updated` odświeża członków.
Tworzenie zadania i podzadania używa istniejącego wiersza tytułu z widocznością,
domyślnie „Prywatne — wybrane osoby”. Publiczne zadanie pokazuje dostęp
odziedziczony, bez osobnego przycisku udostępnienia. Prywatne udostępnia się
od razu przez „Członkowie” → „Udostępnij”, bez wysłanych zaproszeń.

## 2. Powłoka aplikacji

„Dla ciebie” jest osobną pozycją nad Dashboardem, z ikoną `user-round-check`
i obsługą ulubionych menu. Widok rozszerza `core/base.html` i komponenty
Dashboardu: nagłówek katalogu, panele, wiersze i podkreślane zakładki.
Górny pasek zawiera tylko tytuł „Dla ciebie”, bez przycisku „Moje zadania”.
Nagłówek strony i główna treść mają po 22px odstępu z lewej i prawej strony,
także na telefonie, zgodnie ze wspólnym wariantem `.dashboard-overview`.
Treść zaczyna się od nagłówka „Rekomendowane przestrzenie” i kart, bez powitania
oraz dodatkowego opisu. Po prawej pozostaje link do wszystkich przestrzeni.
Nagłówek sekcji oraz tytuł „Dla ciebie” na górnym pasku mają 17px i wagę 700;
lokalne warianty nadpisują wspólne reguły typografii.
Wariant `for-you-project` to pionowy kafelek przestrzeni: wspólny awatar 32px
z `spaces/avatar.html` znajduje się u góry po lewej, a pod nim nazwa 15px/700
i rodzaj 13px/400. Kafelek ma minimum 120px wysokości, padding 16px i odstęp
16px między awatarem a tekstem. Zachowuje wspólną ramkę i zaokrąglenie panelu.
Cała powierzchnia linku otwiera przestrzeń; nie ma oznaczenia gwiazdką,
dolnych skrótów do przypisanych zadań i tablicy/aktywnego sprintu ani licznika.
Ulubione nadal decydują o kolejności. Siatka ma 4, 2 lub 1 kolumnę zależnie od
szerokości. Brak skrótów pokazuje instrukcję i link do katalogu Przestrzeni
w pustym stanie bez obramowania (`for-you-spaces-empty`).
Pięć zakładek jest linkami z `aria-current`; adresy zachowują kategorię,
Workspace oraz parametry wyszukiwania i przestrzeni z istniejących adresów.
„Polecane”, „Przypisane do mnie”, „Ulubione” i „Ostatnia praca” pokazują
tylko 20 najnowszych pozycji łącznie we wszystkich grupach, bez dolnego licznika
wyników i strzałek paginacji. Wybór opiera się na dacie utworzenia, a w ostatniej
pracy — na czasie aktywności zalogowanej osoby. „Ostatnio oglądane” zachowuje
paginację po 25 pozycji w zakresie ostatnich 7 dni. Dolny licznik zakresu i liczby
elementów jest usunięty również z oglądanych. Ich stopka pokazuje tylko strzałki
po prawej, gdy istnieje poprzednia lub następna strona; przy jednej stronie nie
ma stopki ani dolnego separatora.
Pasek używa wspólnych `notifications-tabs work-tabs`, tak jak widoki Przestrzeni:
tekstu 13,5px/400, ikon 18px, odstępu ikona–tekst 8px, wysokości i podkreślenia.
Ikony zakładek to `sparkles`, `user-round-check`, `star`, `clock` i `eye`.
Licznik przypisanych zachowuje szare tło; nieaktywne zakładki pokazują szare
podkreślenie przy najechaniu, a aktywna — fioletowe. Wewnętrzny odstęp paska
wynosi 22px również na telefonie, zgodnie z Przestrzeniami.
Lista zaczyna się bezpośrednio pod zakładkami, bez paska filtrów/wyszukiwarki
i paska opisu aktywnej zakładki. Brak wyników dla parametrów w adresie ma osobny
pusty stan z akcją „Wyczyść filtry”. Linki korzystają ze wspólnej nawigacji
`AncoreApp`, także przy Wstecz/Dalej i ponownym wejściu.
Panel „Twoja praca” używa wariantu `for-you-work-panel` bez zewnętrznego
obramowania; grupy zadań/przestrzeni i poziome separatory zachowują swoje ramki.
`for-you.js` utrzymuje aktywną zakładkę w widocznej części paska po wejściu,
częściowej nawigacji i zmianie szerokości. Przewija wyłącznie zakładki, bez
przesuwania strony lub fokusu; odłącza obserwator rozmiaru przy opuszczeniu widoku.
Puste stany wyjaśniają źródło danych każdej zakładki. Wariant `for-you-empty-state`
pokazuje kolorowe ilustracje 3D: `spaces-empty.webp` przy braku rekomendowanych
przestrzeni, a każda zakładka ma własny obrazek: Polecane — lista z zielonym
znacznikiem (`for-you-tasks-empty.webp`), Przypisane do mnie — karty z symbolem
osoby (`for-you-assigned-empty.webp`), Ulubione — folder z gwiazdką
(`for-you-starred-empty.webp`), Ostatnia praca — zegar i ołówek
(`for-you-worked-empty.webp`), Ostatnio oglądane — dokumenty z symbolem oka
(`for-you-viewed-empty.webp`). `EMPTY_ILLUSTRATIONS` w `dashboard/for_you.py`
wybiera ilustrację aktywnej zakładki, również przy braku wyników filtrów.
Obrazki z `static/img/empty-states/` mają przezroczyste tło, maksymalną
szerokość 240px i skalują się do kontenera. Są dekoracyjne (`alt=""`,
`draggable="false"`); kontener ma `role="status"`, a tekst i dotychczasowa akcja
korzystają ze wspólnego `tasks-empty-state__copy`.
Zakładki pozostają w jednym wierszu i przewijają się poziomo,
gdy brakuje miejsca, także na telefonie. Etykiety i licznik nie zawijają się.
Zadania we wszystkich pięciu zakładkach używają wspólnego `spaces/row.html`,
tak jak „Wyszukaj zadania” w Filtrach: wiersza `tasks-issue-row` z priorytetem,
ikoną statusu, oznaczeniem typu zgłoszenia, kluczem, tytułem, licznikami tagów
i załączników oraz ikoną terminu. Link obejmujący typ, klucz i tytuł w „Dla ciebie”
nie ma podkreślenia tekstu, również po najechaniu kursorem.
Wariant `hide_selection=True` nie renderuje
checkboxa ani jego toru siatki w „Dla ciebie”. Lokalizacja i czas ostatniej aktywności są dostępne w `title` linku,
a własna nazwa statusu i termin w etykietach ikon. Liczniki są pobierane zbiorczo
dla zadań bieżącej strony. Przestrzenie w zakładkach „Ulubione” i „Ostatnio oglądane”
używają wspólnego `spaces/directory.html` w wariancie `directory_compact=True`:
trzy kolumny danych w kolejności Przestrzeń z awatarem, Klucz i Opis.
`hide_actions=True` pomija komórki i menu działań; wariant kompaktowy
`work-space-sheet--no-actions` usuwa ich tor z siatki, także bez JavaScriptu.
`hide_selection=True` usuwa checkboxy wierszy,
checkbox nagłówka i kolumnę wyboru z siatki. Nagłówek kolumn „PRZESTRZEŃ”,
„KLUCZ” i „OPIS” jest ukryty w `for-you-space-sheet`; jego metadane nadal
służą wspólnemu mechanizmowi szerokości kolumn. Katalog i „Zarządzaj przestrzeniami”
korzystają z pełnego wariantu z widocznym nagłówkiem. `spaces.services.decorate_directory_spaces` wspólnie przygotowuje
dane tabel w katalogu, zarządzaniu i „Dla ciebie”; licznik obejmuje tylko widoczne
zadania przestrzeni. Nazwa otwiera przestrzeń. Menu z osobistą gwiazdką,
ustawieniami i edycją/dodawaniem osób według roli pozostaje w katalogu
i zarządzaniu Przestrzeniami. W każdej grupie dat tabela znajduje się w sekcji
`for-you-space-group`, z taką samą ramką, zaokrągleniem, odstępami i wysokością
nagłówka jak grupy zadań. Wspólny `tasks/includes/issue_group_header.html`
pokazuje neutralny nagłówek „Przestrzenie”, ikonę, liczbę przestrzeni na stronie
w tej grupie dat i przycisk zwijania (mysz/Enter/Spacja). Nagłówki statusów
korzystają z tego samego include przez `status_group_header.html`.
Wiersze mają 40px wysokości jak zadania, poziome podziały i brak pionowych linii
między kolumnami. Wszystkie komórki, również pierwsza po usunięciu menu, mają
0,75rem odstępu wewnętrznego z obu boków i zawartość wyśrodkowaną pionowo.
Kolumna Klucz ma dodatkowe 100px odstępu z lewej strony, oddzielające ją od nazwy
przestrzeni. Lokalny token `--work-space-key-gap` powiększa także tor klucza
ze 150px do 250px, zachowując miejsce na jego tekst. Kolumna nazwy ma minimum
320px i rozszerza się do najdłuższej pełnej nazwy w danej tabeli, bez wielokropka.
Siatka `subgrid` wyrównuje klucze i opisy wszystkich wierszy. Wspólny mechanizm
szerokości kolumn pomija ten wariant, również na telefonie, aby nie przywracać
stałej szerokości nazwy. Długie nazwy pozostają w jednym wierszu i są dostępne
przez poziome przewijanie tabeli na wąskich ekranach.
Awatar i nazwa zachowują odstęp 8px. Wariant `for-you-space-sheet` zachowuje wysokość tabeli według liczby
wierszy i osobny schemat trzech kolumn danych bez odtwarzania stałych preferencji
szerokości. Układ jest wspólny dla zwykłego i scoped URL. Kolumna Opis wypełnia
pozostałą szerokość tabeli; na telefonie tabela przewija się poziomo.
Grupy nadal używają wierszy Dashboardu, a górne rekomendowane przestrzenie — kart.
Zadania bieżącej strony są grupowane według kategorii i własnej nazwy statusu,
w kolejności konfiguracji przestrzeni. Wewnątrz statusu pozostaje kolejność
właściwa dla zakładki. Nagłówki używają wspólnego
`tasks/includes/status_group_header.html`, również na listach Przestrzeni:
kolorowego tła, ikony, nazwy, liczby zadań w grupie oraz przycisku zwijania.
`tasks.js` obsługuje zwijanie po pierwszym wejściu i częściowej nawigacji;
lokalne filtrowanie nie ukrywa grup obliczonych przez serwer w „Dla ciebie”.
Historia i oglądane zachowują nagłówki grup dat (`for-you-date-heading`),
a statusy są grupowane osobno wewnątrz każdej daty. „Ostatnio oglądane” obejmuje
ostatnie 7 dni od bieżącej chwili, z grupami Dzisiaj, Wczoraj i Ostatnie 7 dni;
pusty stan wyjaśnia ten zakres oraz zapis w sesji przeglądarki. „Ostatnia praca”
zachowuje również grupę Wcześniej. Nagłówki dat rozszerzają
`tasks-space-group-title`: mają ikonę `calendar-days` 18px, tekst 13px/400
i cienki separator po etykiecie, bez tła i ramki. Margines 1rem u góry
i 0,95rem po bokach wyrównuje je do grup i oddziela kolejne przedziały dat.
Przestrzenie mają osobną
sekcję bez statusu, a grupy pozostają poza sekcjami statusów. Na telefonie lista zadań przewija się
poziomo we własnym obszarze.
Adaptery `for-you-*` w `components/dashboard.css` zachowują geometrię wspólnego wiersza.
Wiersze zadań oraz pozostałe linki do grup w liście mają takie samo podświetlenie
jak wiersze tabeli przestrzeni: tło z `--system-accent` zmieszanym w 8% z bielą
i pasek 3px po lewej. Efekt pojawia się po najechaniu na cały wiersz lub przy
fokusie klawiatury (także na linku wewnątrz zadania), z przejściem 0,12s.
Pasek jest pozycjonowany absolutnie i nie przechwytuje kliknięć ani nie przesuwa treści.

Dawne katalogi „Przestrzenie Kanban” i „Tablice” są wycofane. Ich pozostałe
szablony, klasy CSS i współdzielony JavaScript stanowią kod historyczny, nie
aktywny interfejs. Nie usuwamy wspólnych komponentów używanych przez Zadania
ani obecne tablice w Przestrzeniach. Kalendarz ma tylko filtry wydarzeń i zadań.

Menu Zadań używa nazw „Projekty”, „Grupy” i „Zadania”, w tej kolejności.
„Nieprzydzielone” jest ostatnią zakładką katalogu „Zadania”, po „Ulubione”,
bez osobnej pozycji w menu. Pokazuje dostępne zadania główne bez projektu
i grupy, niezależnie od wykonawcy. Zachowuje filtr wykonawcy, gwiazdki ulubionych
oraz paginację po statusach, ale pomija filtry projektu i grupy.
Pusty stan wyjaśnia brak zadań bez projektu i grupy. Stary adres
`view=unassigned-tasks` oraz zapisane skróty sidebaru otwierają tę zakładkę.
Nagłówek pozostaje „Zadania”, a aktywna pozycja menu to również „Zadania”.

Katalogi „Projekty”, „Grupy” i „Zadania” mają zakładki „Prywatne”,
„Udostępnione”, „Publiczne” i „Ulubione” w nagłówku, po prawej stronie tytułu.
Wariant `tasks-topbar--with-tabs` umieszcza je w `tasks-titlebar-left` z odstępem
1.5rem od tytułu. `notifications-tabs tasks-directory-tabs` korzysta ze wspólnego
fioletowego podkreślenia i tekstu 15px/400, bez osobnej dolnej ramki całego paska.
Najechanie na nieaktywną zakładkę pokazuje identyczne podkreślenie w szarym
kolorze `--system-interaction`; aktywna zakładka zachowuje fioletowy pasek.
Na wąskim ekranie zakładki przechodzą do kolejnego wiersza wewnątrz nagłówka;
tytuł pozostawia miejsce na mobilny przycisk menu. Poniżej pozostaje pasek filtrów,
wyszukiwania i paginacji. Zakładki są linkami z `aria-current="page"`,
obsługiwanymi przez wspólną częściową nawigację i historię przeglądarki.
Parametr `tab` zachowuje się podczas wyszukiwania, sortowania, filtrowania
i paginacji; przełączenie kategorii zeruje numer strony, zachowując filtry.
Nieznana lub pominięta wartość wybiera „Prywatne”; adres
`view=unassigned-tasks` wybiera osobno zakładkę „Nieprzydzielone”.
Menu wiersza zawiera „Dodaj do ulubionych” / „Usuń z ulubionych”. Zapis przez POST
jest wspólny ze stale widoczną gwiazdką po prawej stronie wiersza zadania.
Wariant `tasks-issue-row--with-favorite` dodaje kolumnę 30px, a przycisk
`tasks-icon-button tasks-row-favorite` korzysta z fioletowego akcentu dla
`aria-pressed="true"`. Jego kliknięcie i użycie klawiatury nie otwierają szczegółów.
Gwiazdkę pokazuje wyłącznie katalog „Zadania”. Zapis ulubionych
blokuje przycisk do zakończenia żądania, pokazuje potwierdzenie albo błąd bez
zmiany oznaczenia. Usunięcie z zakładki „Ulubione” odświeża jej wyniki i liczniki,
zachowując URL i przywracając fokus aktywnej zakładce. Puste stany odróżniają
brak elementów kategorii, brak ulubionych i brak wyników wyszukiwania.

Źródło: [core/base.html](../core/templates/core/base.html).

- Stały pasek u góry całej aplikacji (`app-topbar`) ma tło
  `--sidebar-bg`, identyczne jak boczna nawigacja, i wysokość `--app-topbar-height`
  (44px przed skalowaniem UI). Po lewej zawiera przełącznik Workspace
  z avatarem i nazwą, na środku jedno pole globalnego wyszukiwania,
  a po prawej Sticker, powiadomienia, ustawienia i profil z avatarem.
  Symetryczne boczne kolumny utrzymują wyszukiwarkę na środku całego paska,
  niezależnie od szerokości sidebaru oraz długości nazw Workspace i profilu.
  Pole ma maksymalnie 672px i zajmuje do 55,2% szerokości wewnętrznej paska.
  Na telefonie wypełnia miejsce między bocznymi kontrolkami, których kolumny
  dopasowują się do zawartości. Na tablecie prawa kolumna rezerwuje miejsce
  na wszystkie cztery kontrolki, aby nie nachodziły na wyszukiwanie.
  Kontrolki paska mają wspólną wysokość `--app-topbar-control-height`
  (36px z `--dropdown-control-height`), ikony 20px, a tekst nazw i pola 14px.
  Awatary Workspace i profilu mają po 33px (`--app-topbar-avatar-size`)
  i są wyśrodkowane pionowo w kontrolkach.
  Pasek zostawia po 4px nad i pod kontrolkami; rozmiary kontrolek są lokalne dla paska.
  Odsunięcie treści i menu oraz wysokość panelu wyszukiwania uwzględniają wysokość paska.
  Wysokość pola wyszukiwania obejmuje ramkę; wewnętrzny input wypełnia jej wnętrze.
  Także aktywna wyszukiwarka na telefonie zachowuje tę wysokość i pionowe wyśrodkowanie.
  Przycisk zwijania i rozwijania menu znajduje się przy lewej krawędzi
  górnego paska, przed przełącznikiem Workspace. Korzysta z `tasks-icon-button`
  i wariantu `app-topbar__action`: ma 36px, standardowe zaokrąglenie oraz
  ikonę `panel-left` ze wspólnego zestawu. Szare tło oznacza rozwinięte menu.
  Na telefonie otwiera i zamyka boczne menu, zastępując osobny przycisk
  pod paskiem. Zmiana stanu aktualizuje tło, etykietę i `aria-expanded`;
  użycie przycisku zamyka otwarte panele wyszukiwania i powiadomień.
  Pole używa istniejącego `global-search-form`; wpisywanie, strzałki i skrót
  Ctrl/Cmd+K otwierają panel szybkiego wyszukiwania. Na telefonie nazwy Workspace
  i profilu oraz podpowiedź skrótu są ukryte; wszystkie kontrolki pozostają
  dostępne. Zwinięcie sidebaru nie zmienia przełącznika Workspace ani
  położenia jego menu, które rozwija się pod avatarem w górnym pasku.
  Na telefonie menu Workspace wyrównuje się do lewej krawędzi paska,
  aby mieściło się w szerokości ekranu.
  Menu, treść, szkielet ładowania oraz panel wyszukiwania zaczynają się
  pod nim, także na telefonie. Modal powiadomień przykrywa również górny pasek,
  zgodnie ze wspólną powłoką „Utwórz zadanie”.
  Wysokość treści uwzględnia pasek, zachowując przewijanie i widoczną dolną
  krawędź. Pasek należy do bloku `app_navigation`, więc nie występuje w osobnym
  edytorze Dokumentów ani na ekranach uwierzytelniania.
- Wyszukiwanie używa wariantu `global-search-panel--quick` wewnątrz formularza
  górnego paska. Panel jest wyśrodkowany pod polem, ma maksymalnie 680px szerokości
  i 620px wysokości, własne przewijanie, wspólny cień oraz zaokrąglenia dropdownów.
  Nie przyciemnia ani nie blokuje treści strony. Powiadomienia zachowują boczny panel.
  Przed wpisaniem frazy pokazuje do 8 ostatnio oglądanych elementów bieżącego
  Workspace z ponowną kontrolą dostępu; pustą historię zastępuje podpowiedź.
  Przy wynikach przyciski „Wszystko” i dostępne typy filtrują pobrane grupy.
  Filtry przewijają się poziomo, a stopka podaje liczbę wyników i skróty.
  Nagłówek panelu zawiera wyłącznie filtry, bez osobnego przycisku zamknięcia.
  Strzałki przenoszą fokus na linki, Enter otwiera wynik, Escape zamyka panel
  i przywraca fokus polu. Tab zachowuje naturalną kolejność, a kliknięcie lub
  przeniesienie fokusu poza formularz zamyka wyszukiwanie. Na telefonie aktywne
  pole zajmuje szerokość paska, panel mieści się w ekranie, a podpowiedzi klawiszy
  są ukryte. `ancore:content-loaded` czyści frazę i wyniki bez ponownego podpinania
  listenerów. Zmiana frazy od razu usuwa stare wyniki, aby Enter nie otworzył
  elementu z poprzedniego zapytania; anulowane odpowiedzi i błędy są ignorowane.
- Stała nawigacja z modułami i ulubionymi.
  Menu zaczyna się od Favorites, bez osobnego przycisku domu.
  Do strony głównej prowadzi istniejący link Dashboard.
  „Zasoby” i „Zespoły”, w tej kolejności, znajdują się przy dolnej krawędzi
  menu Workspace we wspólnym wariancie `sidebar-menu-section--bottom`.
  Pionowy układ nawigacji i automatyczny margines oddzielają je od głównej
  listy, także po zwinięciu menu i na telefonie. Przy braku wysokości menu
  przewija się razem ze wszystkimi pozycjami, bez nakładania linków.
- Stan zwinięty/rozwinięty i regulowana szerokość sidebaru. Odsunięcie i szerokość
  treści korzystają z `--app-sidebar-total-width`, także przy szerokości
  768–1024px; zwinięcie menu do ikon zwalnia miejsce dla treści. Na telefonie
  menu otwiera się nad treścią, która zachowuje pełną szerokość. Cień menu
  występuje wyłącznie w stanie otwartym (`sidebar--visible`); schowane menu
  nie zacienia lewej krawędzi ani narożnika treści.
- Biały obszar treści w `.main-content > .page-container`.
- Na ekranach katalogów `full-width`, pasek tytułu, akcje, filtry, wyszukiwanie,
  paginacja i przewijana lista.
- Osobny host `#app-page-modals` oraz komunikaty `#app-notifications`.
- Wspólne panele wyszukiwania i powiadomień oraz Sticker.

Zwykła nawigacja między ekranami podmienia treść przy zachowaniu bocznego menu,
także pod adresami Workspace. Działają historia Wstecz/Dalej, filtry GET,
powrót ze szczegółów i ponowna inicjalizacja kontrolek. Podczas pobierania obszar
główny ma `aria-busy`. Po 180 ms pojawia się szkielet nagłówka, narzędzi i wierszy
z delikatnym przesuwającym się rozjaśnieniem. Używa istniejących tokenów szarości,
powierzchni i zaokrągleń; pozostawia aktywne menu boczne oraz mobilny przycisk menu.
`core/includes/content_skeleton.html` jest stałą częścią powłoki poza podmienianą
treścią. Szybkie odpowiedzi nie pokazują szkieletu i nie czekają na animację.
Przy `prefers-reduced-motion` placeholdery są nieruchome. Zasłonięta treść ma
tymczasowo `inert`, a czytnik ekranu otrzymuje „Wczytywanie widoku…”.
Zmiana konta/Workspace, edytory i adresy spoza listy ekranów
zachowują pełną nawigację. Szczegóły zadania pytają o porzucenie niezapisanych
zmian, a po podmianie usuwają poprzednie listenery. Kontrakt i wyjątki opisuje
[cykl życia strony](MECHANISMS.md#12-częściowa-nawigacja-i-cykl-życia-frontendowej-strony).

Globalne wyszukiwanie pokazuje najwyżej 20 wyników w każdej kategorii danych.
Jeśli dopasowań jest więcej, istniejący licznik kategorii pokazuje „20+”,
a pod wynikami pojawia się prośba o doprecyzowanie frazy. Komunikat czytnika
ekranu podaje wtedy liczbę pokazanych wyników, nie całkowitą liczbę dopasowań.
Wygląd panelu, obsługa klawiatury i stany pusty/błąd pozostają wspólne.

Sticker otwiera przycisk z ikoną `sticky-note` po prawej stronie górnego paska,
przed dzwonkiem, z etykietą dostępną i podpowiedzią „Sticker”. Używa wspólnego
`tasks-icon-button app-topbar__action`; `aria-expanded` oznacza otwartą notatkę.
Menu boczne nie zawiera już tego przycisku ani pustej stopki z separatorem.
Sticker zachowuje wygląd i kontrolki oraz zapisuje treść i geometrię osobno
dla zalogowanego konta. Po przełączeniu konta pojawia się jego własna notatka
(pusta przy pierwszym użyciu); powrót przywraca poprzednią. Dane starej notatki
bez właściciela nie są automatycznie przypisywane ani wyświetlane innemu kontu.
Powtórna inicjalizacja po nawigacji nie powiela obsługi przycisku.

Przełącznik Workspace w górnym pasku pokazuje avatar i nazwę bez strzałki.
Kliknięcie avatara lub nazwy otwiera dotychczasowe menu wyboru Workspace
z wyszukiwaniem, stanem „Brak wyników” i linkiem zarządzania.
Escape zamyka menu i przywraca fokus na przełączniku. Wybór zachowuje
istniejący formularz POST i pełne przeładowanie kontekstu Workspace.

Nagłówek strony profilu pokazuje tekst „Profil użytkownika” bez poprzedzającej
go ikony. Avatar użytkownika pozostaje w treści profilu. Do 767px nagłówek
zachowuje 3.5rem odstępu po lewej na przycisk nawigacji, jak paski katalogów.

Otwarty dzwonek używa
`color-mix(in srgb, var(--system-accent) 15%, #ffffff)`, także przy zwiniętym
sidebarze. Pozostałe interakcje w górnym pasku korzystają z szarego
`--system-interaction-soft`. Linki profilu i ustawień zachowują aktywny stan
po częściowej nawigacji. Menu Workspace, wyszukiwanie i powiadomienia zamykają się przed
podmianą strony oraz wzajemnie przy przełączaniu, bez przejmowania fokusu
przez zamykany panel.

Nową stronę modułu oprzyj na aktywnych blokach `title`, `extra_head`,
`page_container_class`, `content` i `page_modals`. Niektóre starsze szablony
definiują bloki `secondary_menu`/`page_header`, których aktualny base nie
wywołuje. Sprawdź rzeczywiste dziedziczenie, zanim skopiujesz cały szablon.

Ekrany logowania/rejestracji mają oddzielny
[auth_base.html](../accounts/templates/accounts/auth_base.html), z osobnym
układem i akcentem typograficznym Playfair Display. To istniejący wyjątek;
nie należy przenosić jego dekoracyjnej typografii do tabel aplikacji.

## 3. Skąd bierze się końcowy styl

Źródła:
[style.css](../static/css/style.css),
[variables.css](../static/css/base/variables.css),
[elestio.css](../static/css/theme/elestio.css),
[modal-system.css](../static/css/components/modal-system.css).

```text
base/fonts.css (lokalny Atlassian Sans)
  → base/variables.css
  → base/reset.css
  → layout/*.css
  → komponenty (m.in. buttons, forms, tables, tasks, contacts, workplaces)
  → theme/elestio.css
  → profile, modal-system, global-search, notifications-panel
  → reguły bezpośrednio w style.css
  → opcjonalne arkusze extra_head konkretnej strony
```

Kolejność importów, specyficzność selektora i `!important` współtworzą wynik.
`style.css` zawiera dużo aktywnych reguł, nie jest tylko listą importów.
Później dołączony arkusz nie zawsze wygrywa z wcześniejszym `!important`.

`elestio.css` to nazwa historyczna motywu w tym repozytorium. Nie oznacza
zależności od zewnętrznego systemu UI. Podobnie `bootstrap.html` zawiera
komentarz ostrzegający przed konfliktem pełnego Bootstrap CSS, a nie import
tej biblioteki. Nie dodawaj frameworka UI tylko na podstawie nazw plików.

## 4. Tokeny i język wizualny

Wartości poniżej pochodzą z aktualnych deklaracji CSS. Preferuj użycie
zmiennej zamiast powielania wartości liczbowej.

| Obszar | Token / obecna wartość |
| --- | --- |
| Font aplikacji | `--font-family-ui`: `Atlassian Sans`, fallback systemowy |
| Mały/podstawowy/większy tekst | `--font-size-sm: 13px`, `--font-size-base: 14px`, `--font-size-lg: 15px` |
| Zwykły tekst | `--text-primary: #40444C` |
| Tekst na akcencie | `--text-inverse: #FFFFFF` |
| Główny akcent | `--system-accent: #5b5fc7`, `--system-accent-rgb: 91, 95, 199` |
| Interakcje | `--system-interaction: #6f7580`, miękkie tło z alfa 0.1 |
| Szare podświetlenie menu bocznego | `--sidebar-interaction-bg: #e9ebef` |
| Wybrana pozycja menu bocznego | `--sidebar-space-selection: var(--system-accent)`, tło `--sidebar-space-selection-bg: #e8ebfa`, znacznik i ramka fokusu korzystają z koloru zaznaczenia |
| Główna powierzchnia | `--bg-main: #ffffff`, `--card-bg: #ffffff` |
| Nawigacja pomocnicza | `--secondary-menu-bg: #FBFBFC` |
| Tło panelu | `--panel-bg: #f7f6f4` |
| Delikatna ramka | `--border-color: #e7e4e0` |
| Standardowa kontrolka | `--control-height: 32px` |
| Dropdown | kontrolka 36px, radius 6px; menu radius 7px, element 32px |
| Checkbox | `--checkbox-size: 18px` |
| Standardowe zaokrąglenie | `--radius: var(--radius-max)`, bazowo 8px |
| Pasek narzędzi | `--toolbar-height: 52px` |
| Sidebar | bazowo 272px; zwinięty 64px; JS pozwala regulować 220–420px |
| Skala UI | `--app-ui-scale: 0.98`, stosowana przez `zoom` w resecie |

Główny akcent `#5b5fc7` pochodzi z palety `brandTeams` Microsoft Fluent UI.
Wspólne kontrolki, aktywne zakładki, zaznaczenia, postęp i jasne tła
przycisków korzystają z `--system-accent` oraz jego wariantu RGB.
Interakcje neutralne zachowują szarości; kolory danych i ilustracji
pozostają niezależne od akcentu aplikacji.

Neutralne obramowania i separatory są przyciemnione o 2% względem wcześniejszej
palety (kanały sRGB × 0,98, zaokrąglone do liczb całkowitych). Dotyczy to wspólnych
tokenów oraz lokalnych odcieni ramek i tabel w komponentach. Grubości linii,
przezroczystość, białe obwódki i kolory stanów/akcentów pozostają bez zmian.

Ważne wyjątki:

- `--text-muted`, `--text-main`, `--text-strong` są aliasami tej samej podstawowej
  barwy. Nazwa „muted” nie upoważnia do wprowadzania nowego jasnoszarego tekstu.
- `--accent-red`, `--accent-blue`, `--accent-peach` są historycznymi aliasami;
  wskazują wspólny fioletowy akcent MS Teams.
- Globalne reguły w `style.css` wymuszają wagę tekstu 400 w szerokim zakresie,
  także dla wielu nagłówków i `strong`. Nie dodawaj lokalnych boldów jako
  domyślnego sposobu wyróżniania nowego ekranu.
- Kolory statusów, tagów, avatarów i terminów mają osobne znaczenie
  i często pochodzą z danych. Zachowuj te wyjątki.
- Nie ma jednej uniwersalnej skali spacingu dla całej historycznej bazy.
  Odstępy bierz z właściwego istniejącego komponentu; dla modali z tokenów powłoki.

## 5. Referencje komponentów

| Element | Wzorzec do ponownego użycia | Styl / zachowanie |
| --- | --- | --- |
| Katalog projektów/grup | [tasks/tasks.html](../tasks/templates/tasks/tasks.html) | `components/tasks.css`, `tasks.js` |
| Historyczna lista kontaktów i firm (wycofana) | [contacts.html](../contacts/templates/contacts/contacts.html), [companies.html](../contacts/templates/contacts/companies.html) | `contacts.css` + wspólne style katalogu |
| Tytuł i toolbar katalogu | [toolbar Dysku](../documents/templates/documents/toolbar.html) jako przykład użycia wspólnych klas | `tasks-topbar`, `tasks-filterbar`, `tasks-filter-button`, `tasks-search-field` |
| Paginacja | [directory_pagination_toolbar.html](../tasks/templates/tasks/includes/directory_pagination_toolbar.html) | Kontekst `window`, atrybuty `data-project-*`, serwerowe URL |
| Zarządzanie kolumnami | [directory_column_manager.html](../tasks/templates/tasks/includes/directory_column_manager.html) | `tasks.js`, zapis ustawień lokalnych |
| Agregat filtrów | [directory_filter_aggregate.html](../tasks/templates/tasks/includes/directory_filter_aggregate.html) | Wspólne menu i aktywny stan |
| Wiersz zadania | [task_issue_row.html](../tasks/templates/tasks/includes/task_issue_row.html) | Stan, uprawnienia, `data-task-*`, ikony, JS listy |
| Karta Kanban | [task_board_card.html](../kanban/templates/kanban/includes/task_board_card.html) | Kolumna, okładka i przeciąganie |
| Standardowy modal formularza | [form.html Dysku](../documents/templates/documents/form.html), modale projektów/zadań | `tasks-modal*` + `modal-system.css` |
| Potwierdzenie | [modal.js](../static/js/modal.js) | `showConfirmModal`, `dialogs.css` |
| Zwykłe przyciski | [buttons.css](../static/css/components/buttons.css) | `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-sm`, `.btn-cancel` |
| Formularz/dropdown | [forms.css](../static/css/components/forms.css), [custom-select.js](../static/js/custom-select.js) | `.form-input`, `.form-select`, `.ancore-custom-select*` |
| Checkbox | [checkboxes.css](../static/css/components/checkboxes.css) | Wspólna geometria i stany |
| Avatar konta | [user_avatar.html](../accounts/templates/accounts/includes/user_avatar.html) | Helper `accounts.avatar`, zdjęcie/fallback/status |
| Priorytet | [priority_icon.html](../core/templates/core/includes/priority_icon.html) | Istniejąca symbolika priorytetów |
| Ikony załączników | [attachment_icon.html](../core/templates/core/includes/attachment_icon.html) | `attachment-icons.js`, format i typ pliku |
| Wiersz ustawień | [settings_row.html](../dashboard/templates/dashboard/includes/settings_row.html) | `settings.css` |

Referencje pokazują bieżące wzorce kodu, a nie polecenie skopiowania całych
ekranów. Szablony mają wymagany kontekst i kontrakt z JS. Przy użyciu include'a
sprawdź wszystkie jego zmienne oraz miejsca wywołania.

### Ikony notatek

„Projekty” mają osobną kolumnę „Działania” (40px) po zaznaczeniu,
przed zachowanymi kolumnami edycji, informacji i notatek. Przycisk z trzema
paskami używa `row-actions.js` i wspólnego popovera Dokumentów. Menu otwiera
dotychczasowe okna projektu, zapisuje szablon lub wywołuje istniejące potwierdzenie
usunięcia, zgodnie z uprawnieniami. Dotyczy tylko projektu w danym wierszu
i nie zmienia zaznaczenia do operacji zbiorczych. Kolumna uczestniczy w zarządzaniu
widocznością i kolejnością; wcześniejsze ustawienia kolumn oraz szerokości
są przenoszone do nowego układu. Wariant `tasks-project-directory-sheet`
dodaje jedną kolumnę także na wąskim ekranie, zachowując przewijanie tabeli.
Nagłówki kolumn działań, edycji, informacji i notatek są wizualnie puste,
z zachowanymi etykietami dostępności oraz nazwami w zarządzaniu kolumnami.
Ikony pozostają w przyciskach wierszy, a checkbox zaznaczania w nagłówku.
Kolumny „Edytuj”, „Informacje” i „Notatki” są domyślnie ukryte; „Działania”
pozostają widoczne. `data-directory-default-hidden` określa domyślny układ
katalogu projektów przy braku zapisanych preferencji i po „Resetuj”. Użytkownik
może włączyć te kolumny i zapisać wybór w zarządzaniu tabelą. Zapisany wybór
ma pierwszeństwo przed ustawieniami domyślnymi; menu wiersza działa także
przy ukrytych kolumnach skrótów.
Ten sam układ obowiązuje w „Wszystkich grupach”, „Przestrzeniach roboczych”
Kanbana oraz „Tagach” Zadań i Kanbana. Historyczne szablony wycofanych
Kontaktów, Firm i Gości mają dwa skróty (edycja i informacja), bez osobnej
kolumny notatek. Pozostałe wymienione katalogi mają także notatki.
Wspólny `directory_row_menu.html` korzysta z przycisków i linków danego wiersza;
menu grup, tagów i przestrzeni wywołuje istniejące potwierdzenie usunięcia.
Zapis szablonu jest dostępny wyłącznie dla projektów Zadań. `tasks-directory-menu-sheet`
oznacza tabele z tym układem. Grupy wewnątrz projektu i tablice Kanbana
zachowują dotychczasowe kontrolki.

Na ekranie „Projekty” od szerokości okna 1181px kolumny
„Ostatnia aktywność” i „Data utworzenia” mają domyślnie odpowiednio 190px i 170px.
Wartości określa `projectColumnDefaultWidths` w `tasks.js`; obowiązują przy braku
zapisanych szerokości oraz po „Resetuj”. Ręcznie zapisane szerokości mają pierwszeństwo.
„Grupy” w tym samym zakresie szerokości okna mają domyślną kolumnę
„Data utworzenia” 170px (`allGroupsColumnDefaultWidths`), z tymi samymi zasadami
zapisu i resetowania szerokości.
Domyślna kolejność danych w „Wszystkich grupach” zaczyna się od „Kod grupy”,
a następnie „Grupa”. Nagłówek, komórki i siatka zachowują tę kolejność również
na wąskich ekranach. Zapisana własna kolejność, widoczność i szerokości kolumn
są odczytywane także z wcześniejszego układu; „Resetuj” przywraca nową kolejność.

Zaznaczone wiersze zadań i podzadań w module Zadania używają tego samego
jasnofioletowego tła (8% `--system-accent` na bieli) oraz paska 3px po lewej
co katalogi projektów i grup. Styl działa dla `.checked` i zaznaczonego checkboxa,
również po najechaniu kursorem; odznaczenie przywraca zwykły wiersz bez paska.
Wspólne reguły są ograniczone przez `data-task-app="tasks"` do modułu Zadania.

Na tablecie i telefonie siatka tych katalogów powstaje z widocznych kolumn w ich
bieżącej kolejności, używając szerokości z tokenów CSS. Ukrycie skrótów
nie przesuwa szerokości kolumn danych; tabela nadal przewija się poziomo.
Historyczne szablony wycofanych Kontaktów, Firm i Gości zawierają karty na telefonie: menu działań
mieści się pod checkboxem, a edycja i informacje są dostępne przez to menu.
Osobne kolumny skrótów są dostępne w ich widoku tabeli.

Przyciski notatek projektów i grup w Zadaniach oraz przestrzeni w Kanbanie
używają wspólnego stanu `.tasks-project-sheet__notes-button.has-notes`.
Gdy istnieje wpis, tylko ikona ma ciepły, wyrazisty żółty kolor `#d4a000`.
Tło i stany interakcji przycisku pozostają standardowe.
Pusty stan zachowuje szarą ikonę kartki z plusem. Stan wynika z istniejących
notatek, także po zapisie i ponownym wejściu.

### Powrót i zamykanie okien

Linki powrotu `tasks-issue-close` oraz krzyżyki standardowych modali,
potwierdzeń, edycji profilu i zdjęć korzystają ze wspólnej geometrii
w `modal-system.css`: kwadrat `--control-height` (32px), zaokrąglenie
`--dropdown-control-radius` (6px) i ikona `--app-navigation-icon-size` (18px).
Domyślnie mają przezroczyste tło i kolor `--text-primary`; hover oraz fokus
klawiatury dodają szare tło `--system-interaction-soft`, bez obrysu.
Powrót zachowuje strzałkę Flaticon, a zamknięcie używa maski `x-mask.svg`
z tego samego lokalnego zestawu, generowanej przez `build_flaticon_icons.py`.
Nagłówki przestrzeni, zespołu i konfiguracji przestrzeni używają tego samego
`tasks-issue-close`; lokalne style fokusu Przestrzeni nie nadpisują tego przycisku.
Wspólna reguła obejmuje także puste przyciski zamknięcia doładowywanych
formularzy Dysku i Dokumentów. Pozycja przycisków, etykiety, Escape,
powrót fokusu i dotychczasowa nawigacja pozostają odpowiedzialnością
istniejących szablonów oraz JS.
Na telefonie nagłówek szczegółów pozostawia 3.5rem miejsca po lewej na
przycisk nawigacji aplikacji, aby nie zasłaniał strzałki powrotu.
Lewa część nagłówka zadania i podzadania zawiera wyłącznie przycisk powrotu
i bieżący tytuł, także dla zadań w Przestrzeniach; bez nazwy przestrzeni
i klucza zgłoszenia. Powrót zachowuje dotychczasowy kontekst nawigacji,
a tytuł odświeża się podczas edycji.

### Paski listy grup

Lista grup otwartego projektu używa tych samych dwóch pasków co „Grupy”: `tasks-topbar--directory` z tytułem i akcjami oraz
`tasks-filterbar--directory` z kolumnami, „Filtruj”, „Sortuj”, wyszukiwaniem
i wspólnym `directory_pagination_toolbar.html`. Projekt zachowuje nazwę
i strzałkę powrotu. Paginacja występuje wyłącznie w drugim pasku.
Filtry i sortowanie używają wspólnego mechanizmu grup; wewnątrz projektu
nie ma dodatkowego wyboru projektu w filtrach. Czyszczenie filtrów,
wyszukiwanie i zmiana strony zachowują otwarty projekt oraz Workspace.
Na telefonie nagłówek projektu pozostawia miejsce po lewej na przycisk
nawigacji aplikacji, aby strzałka powrotu pozostała dostępna.

### Limit zadań według stanu

„Zadania” i „Zadania nieprzydzielone” używają wspólnego paska paginacji.
Wariant `page_size_suffix='/ stan'` w `directory_pagination_toolbar.html`
wyjaśnia, że np. 50 dotyczy osobno każdej sekcji statusu. Etykieta dostępności
brzmi „Liczba zadań na stronie w każdym stanie”. Strzałki zmieniają stronę
we wszystkich stanach jednocześnie; licznik sumuje pokazane zadania.
Pozostałe katalogi zachowują etykietę „/ stronę” i dotychczasowe działanie.

### Krótkie powiadomienia

Komunikaty Django Messages i `showNotification(message, type, options)` używają
jednego komponentu z [notifications.css](../static/css/components/notifications.css)
i [notifications.js](../static/js/notifications.js), także na ekranach logowania.
Nie dodawaj wariantów wyglądu zależnych od modułu ani klas `tasks-page`/`tasks-ui`.
Powiadomienia pojawiają się w prawym górnym rogu, 20px od góry i 24px od prawej
krawędzi, z uwzględnieniem bezpiecznych obszarów urządzenia.
Wspólny stos ma szerokość 280–420px; do 767px wypełnia szerokość z marginesami
1rem. Długi tekst, również bez spacji, zawija się wewnątrz komunikatu.

Wszystkie typy mają białą powierzchnię `--card-bg`, ramkę `--border-color`,
zaokrąglenie `--radius`, cień `--shadow-md` i tekst 13px/400 z `--text-primary`.
Typ rozróżnia wyłącznie lewa ramka 3px: fiolet `--system-accent` dla sukcesu
i informacji, dotychczasowy czerwony `#c94f45` dla błędu, bursztynowy `#c18a34`
dla ostrzeżenia, szary `--system-interaction` dla komunikatu bez typu.
Animacje wejścia/wyjścia respektują `prefers-reduced-motion`.
Zachowane są automatyczne wygaszanie, role `status`/`alert` i inicjalizacja
po `ancore:content-loaded`. Centrum powiadomień pozostaje osobnym komponentem.

### Przyciski akcji w paskach narzędzi

Przyciski używają wariantu `tasks-tag-topbar-button--row-highlight`:
tła `color-mix(in srgb, var(--system-accent) 17%, #ffffff)` oraz tekstu i ikony
w kolorze `--text-primary`. Tło jest o 9 punktów procentowych intensywniejsze
niż podświetlenie wiersza tabeli; przycisk nie ma paska po lewej ani cienia.
Po najechaniu na aktywny przycisk udział fioletu rośnie do 24%, z przejściem
koloru wspólnego komponentu; fokus klawiatury używa tego samego tła, bez obrysu.
Rozmiar, zaokrąglenie i obsługa modala pochodzą ze wspólnego
przycisku. Wariant jest stosowany do akcji „Dodaj projekt”, „Dodaj grupę”
i „Dodaj zadanie” w Zadaniach, „Dodaj przestrzeń” i „Dodaj tablicę” w Kanbanie
oraz „Dodaj kontakt”, „Dodaj firmę” i „Dodaj gościa” w Kontaktach.
Ten sam wariant mają „Dodaj tag” w Zadaniach i Kanbanie, „Nowe wydarzenie”
w pasku Kalendarza, „Nowy dysk” w pasku Dysku oraz „Otwórz zadania”
w pasku Dashboardu.
Obejmuje przyciski katalogów oraz ich odpowiedniki wewnątrz projektu/grupy.

Te same kolory obowiązują we wszystkich głównych przyciskach tworzenia,
zapisu i potwierdzania: w modalach, formularzach, edycji zdjęć, Workspace
i uwierzytelnianiu. Wspólne tokeny `--primary-button-bg` (17% akcentu)
i `--primary-button-hover-bg` (24%) są używane także przez „Dodaj projekt”.
Reguła w `style.css` ustala ciemny tekst i ikony, usuwa cień, oznacza
fokus zmianą tła i osłabia przyciski nieaktywne przez opacity 0.55.
Przyciski usuwania w `showConfirmModal` korzystają z tej samej reguły:
jasny fiolet przechodzi po najechaniu w mocniejszy fiolet, z ciemnym tekstem.
Historyczne style potwierdzeń w `tasks.css` określają ich geometrię,
bez osobnego szarego tła, białego tekstu ani cienia w stanie hover/focus.
„Zastosuj” w filtrach tekstowych projektów, Dysku i Dokumentów korzysta
ze wspólnej klasy `btn-primary` w `project_text_filter_detail.html`.
Akcje filtrów zachowują własną geometrię, a kolory i stany interakcji pochodzą
ze wspólnego stylu przycisków. „Wyczyść” pozostaje akcją drugorzędną.
Wspólna reguła nie zmienia geometrii przycisków, akcji drugorzędnych ani kolorów stanów
`saved`/`error` przycisku zapisu zadania.

Przyciski drugorzędne `.btn-secondary`, `.btn-cancel` i `.tasks-btn-cancel`
korzystają w `buttons.css` z szarego tła `--system-interaction-soft` po najechaniu
i przy fokusie klawiatury. Obramowanie zachowuje zwykły kolor i grubość, bez
przyciemnienia. Dotyczy to m.in. „Oznacz wszystkie jako przeczytane”, „Pokaż starsze”
oraz „Anuluj” w modalach. Przyciski wyłączone nie otrzymują podświetlenia.
Okna potwierdzania usuwania również korzystają z tego wspólnego stylu „Anuluj”,
bez lokalnego nadpisania tła i obramowania w `tasks.css`.

W całej aplikacji, także na ekranach logowania, interakcja z kontrolką nie
dodaje zewnętrznego obrysu ani poświaty. Globalna reguła w `style.css` wyłącza
`outline` dla fokusu, a tokeny `--focus-ring` i `--checkbox-focus-ring` mają
wartość `none`. Formularze, selecty, checkboxy, nawigacja i przyciski korzystają
z tej zasady również w modalach oraz po częściowej nawigacji. Nie dodawaj
lokalnych obrysów ani cieni imitujących ramkę w stanach hover/focus/otwarcia.
Zwykłe obramowania kontrolek, komunikaty walidacji i cienie paneli pozostają
częścią ich stylu. Obsługa Tab, Escape i przywracanie fokusu pozostają bez zmian.

### Tabele i formularze Dysku

Nawigacja główna i ulubione używają nazwy „Dysk” oraz ikony Flaticon pod nazwą aplikacji `hard-drive`.
Indeks nosi tytuł „Dyski”, tworzenie — „Nowy dysk”, edycja — „Ustawienia dysku”.
Każdy dysk zawiera własne foldery i pliki. Zdjęcia referencyjne ilustrują tę
organizację i układy lista/kafelki; wygląd zachowuje tokeny oraz komponenty Ancore.

Przełącznik `documents-display-switch` używa dwóch linków `tasks-icon-button`
z etykietami „Lista” i „Kafelki” i `aria-current` dla aktywnego układu.
Serwer renderuje jeden układ, bez ukrytej kopii tabeli. Kafelki tworzą semantyczną
listę w `documents-grid`, z ikoną, nazwą do dwóch linii i pełnym tekstem w linku,
metadanymi oraz wspólnymi akcjami z tabeli. Kafelki dysków pokazują standardową ikonę,
nazwę i datę, bez opisu oraz liczników plików i folderów. Wspólny komponent
`documents-card` zachowuje proporcje kwadratu (`aspect-ratio: 1`). Pole podglądu
wypełnia dostępną wysokość, z minimum 100px, bez osobnego tła — ikony są
na białej powierzchni kafelka. Ikony plików mają 115,5×115,5px,
a dysków 139,755×139,755px. Ikony pustych i pełnych folderów mają
149,68×149,68px — są powiększone o kolejne 5% względem poprzednich 142,55px,
bez zmiany wymiarów kafelków ani pozostałych ikon.
Wariant `documents-card--library` używa wyłącznie standardowej ikony dysku.
Nazwa, data i akcje pozostają poniżej. W ciasnych kolumnach zawartość kafelka można przewinąć bez zmiany jego proporcji. Rozmiar ikon kafelków nie zmienia ikon
w tabeli ani panelu bocznym.
Siatka dopasowuje liczbę kolumn do miejsca z minimalną szerokością kolumny
248px (lub całą dostępną szerokością, gdy jest węższa), również na telefonie.
Kafelek zajmuje całą szerokość kolumny, więc odstępy między kafelkami wynikają
wyłącznie z `gap`: 16px w obu kierunkach, a na ekranach do 767px — 12px.
Dotyczy Dysków, plików i Dokumentów. Kafelki pozostają kwadratowe;
rozmiary tekstu, ikon oraz przycisków pozostają bez zmian.
Akcje plików i folderów są dostępne przez jeden przycisk z trzema paskami
po prawej stronie daty w stopce kafelka, także na wąskim ekranie.
Kafelki używają tokenów powierzchni, ramek i fontów Ancore. Pasek Dysków nie zawiera
przycisku „Zarządzaj tabelą”; listy dysków i plików pokazują wszystkie kolumny,
także przy zapisanych wcześniej preferencjach ich ukrywania. „Nowy folder” używa
istniejącego drugorzędnego przycisku w pasku, obok „Prześlij pliki”. Wyszukiwanie ma widoczny
opis zakresu obejmującego podfoldery i akcję czyszczenia pustych wyników.

`documents.css` zachowuje semantyczne tabele plików, dopasowane do
katalogu projektów: tekst 13px, nagłówki 35px, wiersze plików minimum 36px, białe tło,
delikatne podziały poziome i pionowe z tokenu `--tasks-directory-column-separator` oraz szare
podświetlenie hover/focus. Wiersze plików mogą być wyższe, aby pomieścić
drugą linię z lokalizacją. Lista nie wyświetla pod nazwą etykiety „Folder” ani
typu pliku (np. „PDF”, „JPEG”); bez lokalizacji nie tworzy drugiej linii.
Lista plików i folderów Dysku (`documents-layout`) ma symetryczne odstępy 24px
od obu krawędzi tabeli, także na telefonie i w nagłówku. Przed ikoną pliku
lub folderu znajduje się przycisk trzech pasków otwierający menu działań;
tabela nie ma osobnej kolumny akcji.
Foldery Dysku mają akcje w kolejności zgodnej z plikami: przenoszenie, edycja,
gwiazdka, pobranie ZIP i usunięcie pustego folderu. Wspólny include
`documents/includes/row_actions.html` obsługuje tabelę i kafelki, z etykietami
zawierającymi nazwę folderu i `aria-pressed` gwiazdki. W zbiorczym widoku
gwiazdek folder pokazuje nazwę dysku jako link, tak jak lokalizacja pliku.
Pusty stan gwiazdek obejmuje pliki i foldery.
Pusty stan zachowuje własne wyśrodkowanie i padding. Nazwy mają
ellipsis; pełna nazwa pozostaje w tekście linku i jego `title`. Ikony nie mają
ozdobnych ramek. Foldery na listach i kafelkach Dysku używają
wspólnego include'a `documents/includes/folder_icon.html` z parametrem `has_files`.
Pusty folder jest zamknięty, a folder z plikami ma otwartą okładkę i dwie
widoczne kartki. Oba warianty są płaskimi SVG, domyślnie żółtymi (`#ffd855`) z pomarańczową
zakładką (`#ffb41f`), bez obrysu. Własny kolor folderu zmienia oba warianty;
zakładka otrzymuje ciemniejszy odcień wybranej barwy. Stan uwzględnia aktywne pliki w podfolderach,
również dokumenty 0 B; pomija kosz. Same puste podfoldery nie zmieniają ikony.
Wspólny `folder_stats.py` ustala obecność plików niezależnie od ich rozmiaru
i aktualnych filtrów listy, w zakresie właściciela, Workspace oraz dysku.
Ikona dekoracyjna ma `aria-hidden` i nie podlega zamianie przez
`AncoreIcons`. Pliki mają jasną kartkę z zagiętym rogiem i kolorowe pole z symbolem:
`documents/includes/file_icon.html` wybiera wariant według rozszerzenia lub
natywnego typu dokumentu, a `file_icon_shape.html` rysuje wspólny SVG.
Dokument tekstowy ma niebieskie wiersze tekstu, arkusz zieloną siatkę,
prezentacja pomarańczowy wykres, a PDF czerwone pole z „PDF”.
Obrazy, archiwa, audio, wideo, kod, tekst i tablice mają
własne symbole oraz kolory; nieznany format otrzymuje szarą kartkę.
Kolory formatów pochodzą z `--documents-file-color` w `documents.css`,
a jasna kartka miesza tę samą barwę z bielą. Zestaw używa płaskich wypełnień,
bez gradientów i cieni.
Te same ikony występują na listach, kafelkach, w formularzu danych pliku
i zastępczym widoku podglądu. Są dekoracyjne, bez fokusu, zachowują kolory
po inicjalizacji `AncoreIcons` i podmianie treści. Nie zmieniają obsługi formatów
ani ikon załączników w innych modułach.
Ikony plików w tabelach Dysku i Dokumentów oraz folderów Dysku mają 32×32px w polu 32×32px.
Wszystkie dyski używają płaskiej, poziomej obudowy z include'a
`documents/includes/drive_icon.html` na liście, w kafelkach i panelu bocznym.
SVG używa zapisanego koloru dysku (domyślnie `#4285d4`) i białych detali,
nie ma obrysu ani fokusu i jest dekoracyjne.
Nawigacja, pusty stan, filtry, sortowanie i globalne wyszukiwanie zachowują
ikonę Flaticon `hard-drive`. Ikona w wierszu listy dysków ma rozmiar
32×32px w polu 32×32px, a w panelu bocznym 30×30px, również na telefonie.
Wiersze dysków mają 35px wysokości, a odstęp między ikoną i nazwą
wynosi 8px, także w zwężonej liście.

Formularz tworzenia i ustawień dysku zawiera nazwę, kolor ikony i opis.
Tworzenie oraz edycja folderów Dysku zawierają nazwę i kolor.
Przycisk ołówka ma etykietę „Edytuj folder”. Wspólny include
`documents/includes/color_field.html` używa natywnego pola `type="color"`
z własną klasą `documents-color-input`, podglądu SVG 64×64px
i przycisku „Domyślny”. Wybrany kolor widać od razu w podglądzie; zapis
aktualizuje listę, kafelki oraz panel dysków. Formularz zachowuje kolor
przy błędzie nazwy. `documents.js` obsługuje pole przez delegację zdarzeń
i `AbortController`, także po `ancore:content-loaded` i otwarciu modala.
Nazwy pozostają widoczne niezależnie od koloru.
Nie udostępnia wyboru zdjęcia ani kadrowania. Wcześniej zapisane zdjęcia
nie są wyświetlane; lista, kafelki i panel boczny zawsze używają wspólnej ikony.

Lista dysków zajmuje całą szerokość treści. Pod tytułem jest pasek narzędzi
z przełącznikiem widoku, filtrami, sortowaniem, wyszukiwaniem i paginacją.
Za sortowaniem przycisk `documents-view-selector` pokazuje nazwę bieżącego
widoku: „Dyski” na indeksie, nazwę otwartego dysku lub nazwę zbiorczego widoku.
Otwiera `documents-views-menu`: Dyski, Wszystkie pliki, Ostatnio zmienione,
Oznaczone gwiazdką i Kosz. Skróty i liczniki obejmują cały Workspace,
także przy otwarciu menu wewnątrz dysku lub folderu.
Menu zastępuje zakładki oraz skróty z panelu bocznego. Korzysta ze wspólnych
`tasks-filter-button`, `tasks-project-query-trigger`,
`tasks-project-menu-button` i istniejącej obsługi `data-document-actions`
w `row-actions.js`: natywny popover, pozycjonowanie w granicach ekranu,
strzałki, Home/End, Escape i powrót fokusu. Aktywny widok ma `aria-current`;
liczniki zachowują zakres Workspace i nie zależą od filtrów.
Indeks nie powtarza listy dysków w panelu bocznym.
Pasek narzędzi i siatka dysków mają wspólny
odstęp boczny `--documents-index-padding-x: 0.95rem`, zgodny z paskiem narzędzi
katalogów. Lista używa `tasks-directory-sheet tasks-project-sheet` z „Wszystkich
projektów” oraz wariantu `documents-library-sheet` w `documents.css`.
Tekst 13px/400, wiersze 35px, nagłówki z ikonami, separatory oraz fioletowe
podświetlenie z paskiem po lewej pochodzą ze wspólnego komponentu.

Lista dysków ma trzy kolumny danych: „Nazwa”, „Zmodyfikowano”, „Rozmiar”,
poprzedzone kolumną wyboru 40px i kolumną menu 40px. Checkboxy korzystają
z `tasks-project-sheet--selectable` i wspólnego stylu projektów, są stale
widoczne i podświetlają zaznaczone wiersze. Checkbox w nagłówku wybiera całą
bieżącą stronę i pokazuje stan częściowego zaznaczenia. Cała kolumna wyboru
jest klikalna; `documents.js` obsługuje wybór również po `ancore:content-loaded`
bez powielania listenerów. Nowe wyniki, strona lub przeładowanie resetują wybór.
Menu ma wizualnie pusty nagłówek
i etykietę „Działania” dla czytników ekranu. Przycisk z trzema paskami używa
`tasks-project-sheet__edit-button` i wypełnia komórkę. Wspólny `row_menu.html`
przyjmuje `menu_kind='library'`, aby zbudować identyfikator i etykietę dysku.
Menu pokazuje ustawienia, usunięcie pustego dysku i otwarcie, korzystając
z `library_actions.html` w wariancie `action_menu`. `row-actions.js` zapewnia
popover, klawiaturę, Escape i powrót fokusu. Kafelki korzystają z tego samego
menu w stopce, po prawej stronie daty, z przyciskiem
`tasks-icon-button documents-icon-button`. Nazwa wypełnia wolne miejsce, data ma 176px,
a rozmiar 120px. Wariant ma semantykę ARIA tabeli, wierszy i komórek oraz
`data-directory-resize="false"`. Atrybuty celu przeciągania pozostają na wierszu.
Lista folderów i plików Dysku pokazuje
te same trzy kolumny danych, bez kolumny „Tagi”, z menu działań w nazwie.
Minimalna szerokość tabeli plików z menu w nazwie wynosi 690px;
węższy obszar zachowuje wszystkie kolumny dzięki przewijaniu poziomemu.
Rozmiar dysku i folderu sumuje aktywne pliki, również w podfolderach,
w zakresie właściciela i Workspace. Puste elementy pokazują 0 bajtów.
Dysk nie pokazuje tagów w formularzach, filtrach ani kafelkach.
W koszu kolumna pokazuje datę modyfikacji, a data usunięcia jest
dostępna w `title` komórki.
Foldery nadal używają daty utworzenia, ponieważ model nie zapisuje daty modyfikacji.
Data i rozmiar pozostają widoczne w trybie listy.

`documents-library-entry` jest linkiem obejmującym miniaturę i nazwę (13px).
Lista dysków nie wyświetla opisu pod nazwą ani opcji „Opis” w wyborze kolumn.
Rozmiar jest wyrównany do prawej, a akcja
ze strzałką otwiera dysk. Długie nazwy mają wielokropek oraz pełny tekst w `title`.
Na wąskich ekranach tabela przewija się poziomo, zachowując wszystkie
kolumny i menu działań (minimalna szerokość 616px).
Pusty wynik pomija nagłówki, mieści się w szerokości ekranu i ma bezpośrednią
akcję wyczyszczenia wyszukiwania i filtrów.

Panel dysków ma białe tło `--bg-main`, takie samo jak lista dysków,
również w wariancie wysuwanym na wąskich ekranach.
Panel jest dostępny w widokach plików i wewnątrz dysku.
Zawiera nagłówek „Dyski”, dodawanie dysku oraz listę dysków;
przełączanie widoków plików jest na pasku narzędzi za sortowaniem.
Linki poszczególnych dysków używają wariantu `documents-sidebar-library-link`:
minimum 40px wysokości, pole ikony 30×30px, zdjęcie 28×28px i odstęp 10px od nazwy.
Zastępczy SVG z `drive_icon.html` jest wyśrodkowany w tym samym polu.
Pełna nazwa pozostaje w `title`, a długie nazwy skracają się przez ellipsis.
Przycisk z ikoną `panel-right` na końcu paska filtrów zwija i rozwija cały
prawy panel, zgodnie ze wzorcem Kalendarza. Na szerokich ekranach zwinięcie
poszerza tabelę i jest zapamiętywane lokalnie w przeglądarce. Do 1100px
przycisk otwiera dotychczasowy panel wysuwany z tłem, obsługą Escape i fokusu;
otwarcie tego panelu nie zmienia preferencji szerokiego ekranu.
Panel dysków używa `tasks-rail-link`, a akcje ikonowe `tasks-icon-button`.
Formularze korzystają z `form-input`, `tasks-inline-input`,
`form-select`/`tasks-inline-select` oraz
`tasks-modal__errors`. Lokalne reguły odpowiadają za układ modułu i upload;
wspólne komponenty za kontrolki, stany interakcji i powłokę okna.

Przeciąganie w Dysku i Dokumentach inicjalizuje `initDocumentDragDrop` w
`documents.js`, również po `ancore:content-loaded`; poprzednie listenery usuwa
wspólny `AbortController`. Kafelki i wiersze aktywnych plików/folderów Dysku
mają `data-document-drag`, a miejsca docelowe `data-document-drop` (`folder:<pk>`
lub `library:<pk>`). W Dokumentach pozostaje wyłącznie upload do katalogu
(`root`), bez przeciągania wierszy i kafelków między lokalizacjami. Prawidłowy cel podświetla się istniejącym fioletem
z przerywanym obrysem; komunikat `role=status` podaje nazwę miejsca docelowego.
Podczas przenoszenia elementu przy kursorze podąża nieprzezroczysta karta
`documents-drag-preview` (320px): własna ikona pliku/folderu, nazwa do trzech
linii, typ i rozmiar oraz wskazany cel. Zastępuje natywną miniaturę linku;
nie zawiera adresu URL. Nie przechwytuje wskaźnika, uwzględnia skalę UI
i mieści się w oknie. Źródło przygasa, a ikona folderu docelowego lekko się unosi.
Po upuszczeniu karta pokazuje „Przenoszenie…”; dopiero po zapisie animuje się
w stronę celu (180ms), przed odświeżeniem listy. Ustawienie
`prefers-reduced-motion` wyłącza animacje. Escape, błąd, opuszczenie okna
i podmiana treści sprzątają podgląd oraz wyróżnienia.
Upuszczenie plików w katalogu otwiera i wysyła standardowy formularz uploadu;
błąd pozostawia pliki w oknie. Upuszczenie w otwartym formularzu zastępuje
bieżący wybór plików, a zapis odbywa się jego przyciskiem.
Ikonowa akcja „Przenieś” z etykietą dostępną dla czytników otwiera standardowy
modal z wyborem lokalizacji, także z klawiatury i na telefonie. Akcje wiersza
są dostępne w menu przed ikoną. Kosz nie udostępnia przeciągania.

Filtry Dysku używają panelu `tasks-project-filter-builder` i wspólnych
szablonów warunków tekstowych oraz wyboru wartości. Lista pól i aktywne warunki
pochodzą z `documents/query.py`; obsługę wyszukiwania, czyszczenia i nawigacji
zapewnia `tasks.js`. Panel sortowania
[directory_sort_builder.html](../tasks/templates/tasks/includes/directory_sort_builder.html)
jest wspólny dla Dysku i Wszystkich projektów: wyszukiwanie pola,
wybór kierunku i zaznaczenie aktualnego ustawienia. Dysk, folder i widok
stanowią kontekst nawigacji; przycisk „Wyczyść” w panelu filtrów ich nie usuwa.

### Katalog i edytor Dokumentów

Pliki DOCX/XLSX/PPTX/PDF w Dysku używają tej samej powłoki pełnego edytora
`documents/office/suite.html` co Dokumenty. Linki nazwy i kafelka otwierają
osobną kartę (`target="_blank"`, `rel="noopener"`), podobnie jak wyniki wyszukiwania.
„Wróć do dysku” prowadzi do folderu pliku. Pozostałe formaty zachowują
modal podglądu. Dla starszych formatów biurowych wspólna akcja „Otwórz kopię
w pełnym edytorze” tworzy kopię w tym samym dysku i otwiera nową kartę.

Pasek pełnego edytora (`office-suite-topbar`) ma jeden wiersz i wysokość
40px (`--control-height` + 8px) także na telefonie. Kontrolki i ikona
zachowują 32px wysokości. Pasek pokazuje wyłącznie strzałkę
powrotu `tasks-issue-close`, wspólną ikonę typu pliku oraz nazwę.
Nie zawiera separatora, rozszerzenia, statusu, ołówka, potwierdzenia ani
przycisków pobierania, zapisu i menu. Długa nazwa ma ellipsis; pełna pozostaje
w tekście oraz `title`. Układ obejmuje Dokumenty, Dysk, tablicę i stan
niedostępnego edytora; katalogi oraz starszy edytor zachowują swoje układy.

Podświetlenie nazwy (`office-suite-title-button`) ma standardowe zaokrąglenie
6px (`--dropdown-control-radius`) i szare tło `--system-interaction-soft`,
spójne z kontrolkami aplikacji. Kliknięcie nazwy, Enter lub Spacja odsłania
płaskie pole `form-input` z cienkim podkreśleniem. Enter i opuszczenie pola
zapisują nazwę; Escape przywraca ostatnią zapisaną wartość i fokus nazwy.
Pusta nazwa lub błąd zapisu pozostawiają tekst do poprawienia i pokazują
alert pod paskiem. Zapis blokuje ponowne wysłanie, aktualizuje tytuł karty
bez przeładowania iframe i nie wpływa na treść dokumentu.

Statusy nazwy i dokumentu pozostają w regionach `role=status` ukrytych
wizualnie przez `u-sr-only`. Automatyczny zapis ONLYOFFICE i tablicy działa
bez przycisku w powłoce. Błędy pozostają widoczne pod paskiem; błędy zapisu
udostępniają tam „Ponów zapis”. Pobieranie i ręczny zapis są dostępne wewnątrz
edytora, a historia i dane pliku w katalogu. W stanie niedostępnego edytora
akcje pobierania i powrotu znajdują się w treści komunikatu.
`office-suite.js` inicjalizuje obsługę także na `ancore:content-loaded`,
z istniejącą ochroną przed duplikacją. Nie zależy od usuniętych kontrolek.

Osobna pozycja „Dokumenty” używa ikony `file-text`. Katalog w
`documents/office/index.html` zachowuje paski `tasks-topbar`/`tasks-filterbar`,
tabelę projektów i kafelki Dysku. Na pasku narzędzi, po prawej stronie sortowania,
przycisk `documents-view-selector` pokazuje ikonę i nazwę bieżącego widoku
oraz strzałkę. W domyślnym katalogu ma napis „Wszystkie dokumenty”; menu
zawiera Wszystkie dokumenty, Ostatnio zmienione, Oznaczone gwiazdką, Szablony i Kosz.
Przycisk używa `tasks-filter-button` i `tasks-project-query-trigger`,
a wrapper ma `order: 3`, po sortowaniu z `order: 2`. Korzysta
z tego samego `documents-views-menu` oraz `data-document-actions` co Dysk,
z licznikami, `aria-current`, obsługą klawiatury i pozycjonowaniem popovera.
Kliknięcie myszą nie przenosi fokusu na pierwszą pozycję. Otwarcie
klawiaturą zachowuje fokus wewnątrz menu; aktywny widok oznacza `aria-current`.
Upload używa
tego samego `documents/form.html` oraz obsługi fokusu, Escape i błędów w
`documents.js`. Wariant uploadu `office_upload` wyświetla wyłącznie formaty dokumentów.

Upload w Dokumentach i Dysku pokazuje pod polem wyboru listę nazw oraz rozmiarów
wybranych plików, opartą na wspólnych klasach `file-list`, `file-item` i `file-details`.
Wariant `documents-upload-files` zawija długie nazwy i ukrywa pustą listę.
Lista odzwierciedla bieżący wybór oraz przeciągnięte pliki; nazwy są zwykłym tekstem.
`documents.js` odtwarza ją z zachowanego pola plikowego po błędzie walidacji
i przy inicjalizacji po `ancore:content-loaded`, bez powielania listenerów.

Lista Dokumentów używa komponentu `tasks-directory-sheet tasks-project-sheet`
z katalogu „Projekty”, z wariantem `office-document-sheet` w `office.css`.
Wiersze mają 35px wysokości; nagłówki z ikonami, tekst, separatory, fioletowe
podświetlenie oraz pasek przy lewej krawędzi po najechaniu pochodzą ze wspólnego CSS.
Pierwsza kolumna 40px zawiera stale widoczne checkboxy w wariancie
`tasks-project-sheet--selectable`, tak jak lista Dysków. Wspólna obsługa
`data-document-selection` w `documents.js` zaznacza pojedyncze wiersze lub
całą bieżącą stronę, pokazuje częściowy wybór w nagłówku i podświetla wiersze.
Cała kolumna wyboru jest klikalna. Działa również w koszu i po częściowej
nawigacji; zmiana wyników, strony lub przeładowanie resetuje wybór.
Druga kolumna 40px zawiera menu z trzema paskami w wierszach. Jej nagłówek
jest wizualnie pusty, z etykietą „Działania” dla czytników ekranu. Przycisk wypełnia komórkę
i używa `tasks-project-sheet__edit-button`; include `row_menu.html` przyjmuje
opcjonalny `button_class`, zachowując domyślny przycisk Dysku i kafelków.
Kolorowa ikona pliku 32×32px pozostaje obok nazwy. Dokumenty mają jeden
płaski katalog, bez folderów, ścieżki lokalizacji i akcji „Przenieś”. Include
`documents/office/actions.html` obsługuje gwiazdkę, edycję, pobieranie oraz kosz;
na kafelkach te same akcje otwiera przycisk z trzema paskami w stopce.
Pusty widok gwiazdek dotyczy dokumentów.
Pusty stan zachowuje własne odstępy i wyśrodkowanie.
Lista pokazuje trzy kolumny danych: „Nazwa”, „Zmodyfikowano” i „Rozmiar”.
Nazwa wypełnia wolne miejsce, długi tekst ma wielokropek i pełną treść w `title`.
Data ma 176px, rozmiar 120px z wyrównaniem do prawej. Minimalna szerokość
wynosi 656px; na telefonie wszystkie kolumny pozostają w przewijanym obszarze.
Wariant ma `data-directory-resize="false"` i semantykę ARIA tabeli, wierszy oraz
komórek. Pusty stan nie renderuje nagłówków i mieści się w szerokości ekranu.
Tagi nie są dostępne w kafelkach, filtrach, oknie „Dane dokumentu” ani
starszym edytorze tekstu. Aktywne filtry pozostałych pól mają nad listą akcję
czyszczenia i pozostają przy wyszukiwaniu, sortowaniu, paginacji, zmianie
układu oraz akcjach gwiazdki/kosza.

Oba katalogi korzystają z jednego odstępu bocznego siatki
(`--documents-index-padding-x` na `.documents-page`). Nagłówki tabel plików Dysku
są tekstowe, bez ikon. Lista Dokumentów nie pokazuje historycznej lokalizacji w folderach.
Kafelki Dokumentów mają tę samą powierzchnię podglądu,
nazwę, metadane i stopkę co pliki Dysku oraz własny przewijany kontener.
Dokumenty używają wspólnego z Dyskiem include'a `documents/filter_sort.html`:
przycisku „Filtruj” z licznikiem, wyszukiwaniem pól, warunkami tekstowymi,
wyborem wartości oraz etykietami aktywnych filtrów z usuwaniem. Wariant
przyjmuje `filter_title`, `filter_heading` i `sort_title`, aby zachować nazwy
modułu. Sortowanie używa `directory_sort_builder.html` z wyszukiwaniem pól,
kierunkiem rosnąco/malejąco i aktualnym ustawieniem w przycisku, identycznie
jak w Dysku. Pusty wynik filtrów ma akcję czyszczenia.
Paginacja korzysta z `directory_pagination_toolbar.html` z wyborem 25/50/100 pozycji. `tasks.js`
obsługuje także wyszukiwanie z opóźnieniem i Enter; układ i widok
pozostają zachowane przy zmianie filtrów, sortowania lub liczby pozycji.
Układ należy do adresu formularza wyszukiwania, a nie do zbioru
czyszczonych filtrów. Filtry i sortowanie wracają na pierwszą stronę;
zmiana lista/kafelki zachowuje stronę. Na telefonie
wiele akcji nagłówka zawija się do kolejnych rzędów we wspólnym wariancie
Dysku i Dokumentów; tabela zachowuje własne przewijanie poziome.

Starszy edytor tekstu jest pełnym ekranem z nazwą, paskiem formatowania,
powierzchnią dokumentu oraz jawnym zapisem. `office.css` dodaje wyłącznie układ
tej części; kontrolki i kolory pochodzą ze wspólnych komponentów. Szerokości
dropdownów określa także na wrapperach `AncoreCustomSelect`. Przyciski na telefonie
zawijają się do szerokości paska. Lokalne reguły dla pogrubienia/kursywy w treści
autora celowo nadpisują globalną wagę 400; nie zmieniają typografii nawigacji.
Status zapisu używa `role=status`, błędy `role=alert`, a pole treści jest opisanym
`contenteditable` z rolą wielowierszowego pola tekstowego. Pobieranie niezapisanych
zmian jest blokowane komunikatem z prośbą o zapis.

Nowe pliki mają wspólny ekran `office/suite.html`: pasek Ancore z nazwą,
formatem, metadanymi, pobraniem i statusem zapisu oraz iframe pełnego edytora.
Pliki ONLYOFFICE i tablice BOARD otwierają ten ekran w osobnej karcie (`target="_blank"`,
`rel="noopener"`), również z globalnego wyszukiwania. Wariant
`office-editor-window` rozszerza `core/base.html`, pomija blok `app_navigation`
i wykorzystuje pełną szerokość bez bocznego menu i skalowania iframe.
Tworzenie pliku rezerwuje kartę podczas zatwierdzenia modalu, a po zapisie
odświeża katalog w pierwotnej karcie. Błąd zamyka pustą kartę; blokada okien
pokazuje odnośnik do utworzonego pliku. Ten sam mechanizm obejmuje tablice.
ONLYOFFICE zachowuje własny polski interfejs, Excalidraw jest izolowany od
CSS aplikacji i używa turkusowego akcentu. Katalog ma dwa wspólne paski:
tytuł oraz narzędzia z wyszukiwaniem i paginacją.
Tworzenie dokumentów oraz upload są dostępne jako kafelki bez nagłówka;
górny pasek nie zawiera przycisków tych akcji. Pod paskiem narzędzi, nad listą
plików, sekcja `office-quick-create` pokazuje siedem skrótów:
dokument, arkusz kalkulacyjny, prezentację, PDF, formularz PDF, tablicę
i „Prześlij dokumenty”. Nie ma kafelka „Z szablonu”; kopię szablonu
tworzy się z menu oznaczonego dokumentu w widoku „Szablony”.
Ostatnia akcja otwiera istniejący modal uploadu w bieżącym Workspace.
Wariant `office-create-card`
korzysta z powierzchni `documents-card`, istniejących kolorowych ikon plików
oraz małego plusa z tłem głównego przycisku; upload korzysta z ikony `cloud-upload` i małej ikony `upload` zamiast plusa.
Siatka dobiera liczbę kolumn do dostępnego miejsca (minimum 184px na kafelek)
i rozciąga kolumny równomiernie na całą szerokość, bez pustego pasa po prawej;
na telefonie ma dwie kolumny z mniejszą ikoną obok nazwy i bez dekoracyjnego
plusa, aby pozostawić miejsce na listę; nie występuje w koszu. Skróty działają także
w pustym katalogu, wynikach wyszukiwania i widoku kafelków.
Sekcja ma dostępną nazwę „Tworzenie dokumentów” przez `aria-label`,
bez widocznego nagłówka ani przycisku zwijania. Kafelki pozostają widoczne
po przeładowaniu i `ancore:content-loaded`; wcześniejsze preferencje
zwinięcia w `localStorage` nie są odczytywane. Sekcja ma równe odstępy nad i pod
kafelkami: 8px na komputerze i telefonie. Przerwy między kafelkami w obu
kierunkach wynoszą 16px na komputerze oraz 12px na telefonie. Marginesy boczne korzystają
z `--documents-index-padding-x`, a lista nie ma dodatkowego marginesu.
Kliknięcie kafelka typu pliku otwiera wspólny modal z wybranym typem i zachowuje bieżący Workspace. Fokus od razu trafia do nazwy, błędy mają pierwszeństwo;
Escape i powrót fokusu obsługuje istniejący `documents.js`.
Typ nadal można zmienić w formularzu, a zapis otwiera edytor w osobnej karcie.
`office-suite.js` inicjalizuje ekran także po `ancore:content-loaded`;
`data-app-full-navigation` wymusza bezpieczne opuszczanie aktywnych edytorów.
Statusy zapisu są potwierdzane przez serwer. Tablica przy błędzie zachowuje
scenę i pozwala pobrać bieżącą kopię; jej iframe przyjmuje wyłącznie komunikaty
z okna rodzica tego samego originu.

Na listach plików i folderów Dysku akcje wiersza otwiera
jeden przycisk z ikoną `menu`
(trzy poziome paski), po lewej stronie ikony pliku lub folderu. Nie ma osobnej
kolumny działań. Lista Dokumentów ma osobną kolumnę menu zgodną z tabelą
projektów; oba warianty ukrywają nagłówki w pustym stanie.
`documents/includes/row_menu.html` przyjmuje szablon akcji danego modułu
w parametrze `actions_template` i korzysta z dotychczasowych formularzy,
z tekstowymi etykietami w wariancie `action_menu`.
Kafelki plików i folderów Dysku oraz Dokumentów używają tego samego include'a
w stopce, po prawej stronie daty, zamiast rzędu ikon. Menu używa wspólnych klas
`tasks-section-menu` i `tasks-project-menu-button` oraz natywnego `popover`
poza obszarem przycinania tabeli lub kafelka. `row-actions.js` dopasowuje położenie do
viewportu i skali UI, obsługuje strzałki, Home/End, Escape, kliknięcie poza menu
oraz zamknięcie przy przewijaniu. Otwarcie myszą pozostawia fokus na przycisku;
Enter/Spacja przenoszą go na pierwszą akcję. Długie etykiety akcji zawijają się w menu,
zachowując pełny tekst także na telefonie. Po zamknięciu modala fokus wraca na przycisk
wiersza lub kafelka. Inicjalizacja działa także po `ancore:content-loaded` bez powielania
listenerów. Kosz udostępnia w tym samym miejscu akcję przywrócenia.

Menu plików Dysku i Dokumentów, zarówno na liście, jak i w kafelkach, nie
udostępniają „Historii wersji”. Ekran historii został wycofany. Pozostałe
akcje oraz wspólna obsługa menu i modali pozostają bez zmian.

### Dashboard bieżącego Workspace

`dashboard/home.html` rozszerza `dashboard/pulpits/detail.html`, a przez niego
wspólną powłokę `core/base.html`. Strona główna i `/dashboards/default/` używają
tych samych nagłówków, siatki, pustych stanów, CSS i `pulpits.js` co nowe pulpity.
„Edytuj pulpit” prowadzi do wspólnego edytora z menu „Gadżety i układ”, „Dostępy”
i „Ustawienia”. Pierwsze wejście pokazuje jeden „Postęp pracy”; kolejne odczytują
zapisany układ i gadżety. Przegląd nie pokazuje kontrolek zmiany gadżetów.
Nazwa i opis są edytowalne, a osobista pozycja „Pulpit domyślny” pozostaje w menu.
Nie ma akcji „Usuń pulpit” dla rekordów domyślnych; gadżety można usuwać wszystkie.
Wspólne odstępy, tokeny, responsywność, modale i częściowa nawigacja pozostają
takie jak w systemie Pulpitów opisanym w rozdziale 15.

## 6. Modale

„Nowe zadanie” otwiera się z pustymi polami „Projekt” i „Grupa”, również
na ekranie konkretnego projektu lub grupy i po ponownym otwarciu.
Wybór projektu nie wybiera automatycznie pierwszej grupy. Opcje „Brak projektu”
i „Brak grupy” pozwalają wyczyścić wybór; usunięcie projektu zeruje też grupę.
Zapis obu pustych pól kieruje do „Zadań nieprzydzielonych”, także w pustym Workspace.
Wybrany projekt wymaga wskazania jego grupy; błąd zachowuje tytuł i wybrane pola.
Wariant `data-allow-unassigned` dotyczy wyłącznie formularza Zadań; Kanban
zachowuje istniejący wybór przestrzeni i tablicy.

Zakładka „Główna” szczegółów zadania i podzadania nie pokazuje „Powodu blokady”,
dawnych kontrolek „Czasu pracy”, „Szacowanego czasu” ani bocznej „Historii statusu”. Modal tworzenia
zadania również nie zawiera powodu blokady ani szacowanego czasu; zachowuje
termin wykonania i przypomnienie. Edytor szablonów projektów nie
pokazuje pola szacowanego czasu ani kolumny „Czas (min)”. Zmiany statusu są nadal
widoczne w zakładce „Historia”.
Wspólne style czasu pracy i historii są nadal używane przez Kanban.

Zakładki „Główna”, „Podzadania”, „Dziennik pracy”, „Członkowie” i „Historia” (`tasks-issue-tabbar`) znajdują się
w lewej kolumnie szczegółów (`tasks-issue-primary`), bezpośrednio nad tematem
zadania i są wyrównane do jego lewej krawędzi, także na telefonie.
Pasek zakładek i ich treść mają po 50px odstępu od obu krawędzi lewej kolumny
(`--tasks-issue-content-padding-x`), także na telefonie. Treść wykorzystuje całą
pozostałą szerokość bez limitu 980px; wariant dotyczy zadań i podzadań.
Korzystają z `notifications-tabs`, z fioletowym podkreśleniem. Tekst zakładek
ma rozmiar `--font-size-lg` (15px); wariant jest ograniczony do szczegółów
zadania i podzadania. Dekoracyjne ikony z `AncoreIcons` oznaczają dokument
przy „Główna”, listę przy „Podzadania”, zegar przy „Dziennik pracy”, osoby
przy „Członkowie” i strzałkę historii przy „Historia”. Mają 18px i odstęp 8px
od etykiety, tak jak zakładki Przestrzeni; dziedziczą kolor tekstu. Pasek
zachowuje przewijanie poziome na telefonie i obsługę klawiatury.
Edytowalny tytuł w treści tych widoków ma 20px,
także na telefonie, zgodnie z rozmiarem nagłówków standardowych modali.
Pod paskiem zakładek nie ma poziomej linii oddzielającej go od treści.
Temat i opis (`tasks-issue-overview`) są widoczne tylko w „Głównej”,
przed załącznikami i czatem. „Dziennik pracy” zaczyna się od podsumowania
i listy wpisów, również przy bezpośrednim wejściu z `tab=work-log`.
Pola pozostają w formularzu, a przełączanie zakładek zachowuje ich niezapisane
zmiany. Wspólny obszar `tasks-issue-primary-body` przewija zawartość wybranej
zakładki. Lista w „Historii” nie ma limitu wysokości ani własnego przewijania:
wypełnia dostępną wysokość treścią, a dłuższą historię przewija wspólny obszar
zakładki (na wąskich ekranach główny obszar szczegółów). Czat zachowuje własny
limit wysokości. Zapis wpisu czasu odświeża tylko tabelę i historię, zachowując wartości
tematu i opisu. Dotyczy to zadań i podzadań.
Prawy panel szczegółów jest wspólny dla wszystkich zakładek zadania
i podzadania; na wąskich ekranach pozostaje pod treścią zgodnie ze wspólnym
układem szczegółów. Przycisk „Zapisz” jest dostępny we wszystkich zakładkach i zapisuje
ten sam formularz, w tym zmiany z panelu bocznego. „Dodaj czas” pojawia się
obok zakładek w lewej kolumnie i zapisuje wpisy przez osobny formularz modala.
Panel boczny szczegółów zadania i podzadania nie pokazuje wierszy „Przestrzeń”
ani „Grupa”. Ostatnia sekcja panelu występuje wyłącznie w podzadaniu i zawiera
wybór zadania nadrzędnego. Okno „Planowanie i zespół” również nie pozwala zmienić grupy;
wybór grupy pozostaje w formularzu tworzenia. Picker rodzica podzadania
obejmuje tylko zadania z tej samej grupy.
ARIA tablist/tab/tabpanel, strzałki, Home i End obsługują klawiaturę.
Wybrany widok jest zapisywany w parametrze `tab=subtasks`, `tab=work-log` lub `tab=history`, bez przeładowania.
„Podzadania” są dostępne dla zadania głównego, także przy pustej liście.
Panel pokazuje dotychczasowy licznik, sortowanie, usuwanie zaznaczonych
i modal dodawania oraz listę grupowaną według statusu. Lista i grupy statusów są
stale rozwinięte, bez przycisków zwijania; „Podzadania” z licznikiem to zwykły
nagłówek. Nie pokazuje tematu, opisu
ani czatu. Pusta lista wyświetla „Brak podzadań.”, a dodawanie pozostaje dostępne.
Zapis podzadania i błąd formularza pozostawiają wybraną zakładkę.
Szczegóły podzadania zachowują trzy zakładki, bez kolejnego poziomu podzadań.

„Główna” zawiera wyłącznie komentarze w sekcji „Czat”, z dotychczasowym
formularzem i wzmiankami. Nie ma menu filtrowania aktywności. Zakładka
„Historia” pokazuje wyłącznie zdarzenia zadania, bez tematu, opisu ani formularza
komentarza. Ukrycie pól nie usuwa ich niezapisanych wartości; błąd walidacji
ukrytego pola przywraca „Główną”, aby umożliwić poprawę. Obie listy korzystają
z `task_activity_item.html` i pokazują najnowsze wpisy jako pierwsze; mają osobne
stany puste. Serwer rozdziela komentarze (`kind=comment`) od pozostałych zdarzeń,
a `prependTaskDetailActivityItems` kieruje nowe wpisy po zapisie zadania lub czasu
do odpowiedniej listy, również gdy zakładka jest ukryta. Dotyczy to zadań
oraz podzadań, pod zwykłymi i scoped adresami. Kanban zachowuje własną Aktywność.

`tasks-work-log` wykorzystuje wariant `tasks-work-log-sheet` wspólnej tabeli
katalogu projektów: wiersze 35px,
nagłówki z ikonami, separatory oraz fioletowe podświetlenie z paskiem po lewej.
Cały dziennik korzysta z `tasks-issue-content`: tabela, podsumowanie, pusty stan
i paginacja mają tę samą pełną szerokość i boczne odstępy 50px
co temat i opis, również na telefonie. Podsumowanie i paginacja nie dodają
własnego poziomego wcięcia. Tabela zachowuje poziome przewijanie kolumn.
Pierwsza kolumna 40px zawiera wspólne checkboxy katalogu projektów, zawsze
widoczne. Checkbox w nagłówku zaznacza/odznacza bieżącą stronę i pokazuje
stan częściowego zaznaczenia. Kliknięcie pustego miejsca w kolumnie wyboru
również przełącza wpis. Zaznaczenie utrzymuje podświetlenie wiersza oraz
pozostaje po edycji i odświeżeniu fragmentu; usunięte i niewidoczne wpisy
wypadają z wyboru. Pełne przeładowanie lub zmiana strony zaczyna nowy wybór.
Delegacja w `task-work-log.js` obsługuje także nowe wiersze po zapisie i
ponowną inicjalizację, bez wpływu na checkboxy pozostałych modułów.
Menu działań ma osobną kolumnę 40px, ukrytą przy braku prawa edycji;
przycisk `tasks-project-sheet__edit-button` wypełnia całą komórkę, ma proste
rogi i ten sam fioletowy hover/fokus co akcje projektów. Wrapper menu rozciąga
się do rozmiaru komórki; obsługę menu nadal zapewnia `row-actions.js`.
Autor korzysta ze wspólnego avatara katalogów. Wąskie ekrany zachowują wszystkie
kolumny w przewijanym poziomo obszarze, a opis wypełnia wolną szerokość.
Wariant ma `data-directory-resize="false"`: szerokości ustala CSS, a wspólny
mechanizm zmiany szerokości kolumn pomija tę tabelę także po ponownej inicjalizacji.
Suma minut i licznik wpisów obejmują także pozostałe strony. Długi opis ma
wielokropek i pełną treść w `title`; edytor pozwala przeczytać i zmienić całość.
Pusty stan pokazuje instrukcję dodania czasu. Modal `task-work-log-modal`
używa `tasks-modal app-modal-panel`, wspólnych pól, fokusu, Escape i stopki.
„Czas poświęcony” używa dwóch edytowalnych pól „Godziny” i „Minuty” we wspólnym
układzie `tasks-issue-time-spent` znanym z Kanbana. Edycja dat przelicza tę parę;
edycja godzin lub minut wylicza rozpoczęcie względem zakończenia, domyślnie
bierze bieżącą chwilę. Daty liczone są w Europe/Warsaw niezależnie od strefy
przeglądarki. Pola pozostają w jednym rzędzie także na telefonie. Dodawanie
i edycja rozpoczynają się z fokusem w godzinach. Ostatnia edytowana strona
określa kierunek obliczeń; nie ma dodatkowego przełącznika.
`task-work-log.js` obsługuje inicjalizację i `ancore:content-loaded`, sprząta
listenery i żądania, ustawia `inert` na tle i blokuje ponowny zapis oraz
zamknięcie w trakcie żądania. Błędy serwera pozostają w formularzu z wpisanymi
danymi. Zapis odświeża dziennik i Historię bez nadpisywania głównego formularza.

`modal-system.css` wprost wskazuje okna projektów i zadań jako wzorzec
standardowego okna aplikacji. Powłoka odpowiada za powierzchnię, przyciemnienie,
szerokość, cień, nagłówek, stopkę, przycisk zamknięcia i geometrię kontrolek.
Moduł odpowiada za treść oraz specjalistyczne układy pól.

Duże formularze używają wariantu `app-modal-panel` na istniejącym elemencie
`tasks-modal` (lub `profile-edit-overlay` w profilu). Dotyczy tworzenia i edycji
projektów/przestrzeni, grup/tablic, tagów, zadań i podzadań, edytora szablonów
projektów, kontaktów/firm, wydarzeń, Workspace, profilu oraz formularzy Dysku
i Dokumentów. Wariant jest jawnie oznaczony w szablonach; nie wymaga nowej
inicjalizacji JS i działa również po częściowej nawigacji oraz błędach formularza.

Panel jest wyśrodkowany poziomo względem całego ekranu, niezależnie od
szerokości i stanu menu bocznego. Zachowuje dotychczasową szerokość na desktopie:
`calc(100vw - clamp(64px, 13.5vw, 280px) - 16px)`, ograniczoną dostępnym
obszarem. Od góry pozostaje 24px, a panel dochodzi do dolnej krawędzi ekranu.
Odstępy po lewej i prawej są równe. Zachowuje dotychczasowe zaokrąglenie
tylko górnych rogów oraz brak dolnego obramowania.
Jasnoszara powierzchnia używa `--secondary-menu-bg` (`#FBFBFC`),
tego samego tokenu co boczny pasek nawigacji; wewnątrz jest biała,
przewijana treść `--card-bg` z odstępami 24px.
Nagłówek ma 72px i tytuł 20px/400, stopka minimum 68px i akcje po lewej.
Oba paski pozostają poza przewijaną treścią. Przycisk zamknięcia, fioletowe
akcje, kontrolki, obsługa fokusu, Escape, list wyboru i zapisu korzystają
z dotychczasowych mechanizmów. Panel wysuwa się od dołu i chowa w dół
w 320ms, z łagodnym wyhamowaniem i zmianą przyciemnienia tła. CSS używa
`@starting-style` oraz dyskretnego przejścia `display`, więc usunięcie
`is-open`/`active` pozostawia okno widoczne do końca animacji. Szybkie ponowne
otwarcie odwraca ruch bez opóźnionych callbacków. W Dysku i Dokumentach
usunięcie formularza z DOM czeka na zakończenie animacji samej powłoki;
w tym czasie ponowne zamknięcie, zapis i otwarcie są blokowane, a nawigacja
przerywa oczekiwanie na sprzątanie starego ekranu. Potwierdzenia i podglądy
plików zachowują własne zachowanie. `prefers-reduced-motion` wyłącza ruch
i oczekiwanie; starsze przeglądarki bez dyskretnych przejść mają animację
otwierania oraz natychmiastowe zamknięcie.

Od szerokości 1100px pełne wiersze `tasks-form-field` mają etykietę po lewej
(180px), a kontrolkę po prawej. Parametry projektu zachowują dwie kolumny,
z etykietą 128px w każdej; ukryte pola pierwszej grupy nadal są ukryte po
wybraniu szablonu. „Nowe zadanie” używa tej samej sekcji `tasks-project-parameters`
i siatki `tasks-project-create-fields`: dwie równe kolumny, identyczne odstępy
i etykiety obok kontrolek. Wspólny wariant wiersza obejmuje także kontrolki
projektu i grupy w elementach `.tasks-issue-field`. Do 720px parametry projektu
i zadania przechodzą do jednej kolumny. Węższe okna zachowują pionowy układ pól. Do 900px panel
ma 16px odstępu od góry i po 20px z boków, a do 600px wypełnia ekran, z odstępami treści 12px,
większą stopką przy zawijaniu akcji i uwzględnieniem bezpiecznego obszaru ekranu.
Dane kontaktowe mają dwie kolumny, a do 600px jedną; ID Ancore zajmuje pełny wiersz.

Okna „Informacje” oraz „Notatki” projektów, grup i tagów w Zadaniach oraz
przestrzeni i tagów w Kanbanie również używają `app-modal-panel`.
Wspólny `project_info_modal.html` zachowuje podsumowanie i siatkę danych.
Notatki zachowują formularz i listę wpisów; cała biała treść przewija się razem,
bez osobnego przewijania listy. Okna mają stałą stopkę „Zamknij” oraz
dotychczasowe zamykanie krzyżykiem i Escape, fokus i obsługę zapisu.

Małe okna formularzy używają `app-modal-panel app-modal-panel--compact`,
jak „Utwórz pulpit”, „Zaproś osobę”, „Zmień rolę”, „Zaproszenie do Workspace”
oraz wybór awatara. Są wyśrodkowane poziomo i przylegają do górnej krawędzi
ekranu, z wysokością dopasowaną do treści oraz szerokością do 760px.
Wysuwają się od góry i chowają w górę w 320ms, z tą samą krzywą ruchu
co duże panele. `--app-panel-enter-offset` określa kierunek: `100%` dla
dużego panelu i `-100%` dla małego. Mały panel ma zaokrąglone tylko dolne
rogi i brak górnego obramowania; powierzchnie, nagłówek i stopkę dziedziczy
po panelu „Edytuj miejsce pracy”.
`AncoreTaskModals` kończy zamykanie małego formularza po zakończeniu ruchu,
zanim moduł usunie jego HTML. Ponowne otwarcie anuluje poprzednie sprzątanie
i zachowuje pierwotny punkt powrotu fokusu.
Ma jasnoszare tło, białą przewijaną treść i akcje po lewej. Etykiety pozostają
nad kontrolkami; w zaproszeniu osoba i rola są obok siebie. Długi tytuł zawija się.
Na telefonie zachowuje margines od krawędzi, a stopka może zawijać akcje.
Potwierdzenia `showConfirmModal` i edytory zdjęć konta, firmy oraz logo Workspace
korzystają z tego samego małego panelu przy górnej krawędzi oraz reguł
powierzchni, nagłówka, białej treści i stopki w `modal-system.css`, zachowując
własne szerokości i mechanizmy otwierania. Potwierdzenie jest usuwane z DOM
po zakończeniu ruchu, a powrót fokusu następuje po zamknięciu. Kadrowanie
używa istniejącego atrybutu `hidden` i dyskretnego przejścia `display`.
`prefers-reduced-motion` wyłącza ruch również w małych oknach.
Nagłówki mają minimum 72px i tekst 20px/400; stopki minimum 68px oraz akcje
po lewej. Do 600px jest to odpowiednio 60px, 18px i 60px, z odstępami 12px.
Długie komunikaty przewijają się w treści, a przyciski potwierdzeń mogą się
zawijać. Potwierdzenia mają krzyżyk zamykania bez wykonania operacji;
Tab obejmuje krzyżyk i oba przyciski, a Escape i powrót fokusu działają jak wcześniej.
Kadrowanie zachowuje płótno, powiększenie i zapis; przewijana sekcja mieści się
między stałym nagłówkiem i stopką. Nowe małe okna powinny korzystać z tego wzorca.
Podglądy plików zachowują swoją geometrię.
Poniższe tokeny opisują bazową powłokę i podglądy; nie wyznaczają wysokości
i szerokości paneli ani ujednoliconych małych okien.

| Token powłoki | Wartość bazowa |
| --- | --- |
| `--app-modal-surface` | `var(--card-bg)` — biały |
| `--app-modal-scrim` | `var(--modal-scrim-bg)` — `rgba(20, 23, 29, 0.24)` |
| `--app-modal-scrim-filter` | `var(--modal-scrim-filter)` — `blur(1px)` |
| `--app-modal-radius` | `var(--radius)` — 8px |
| `--app-modal-shadow` | `var(--shadow-lg)` |
| `--app-modal-width` | `min(760px, calc(100vw - 2rem))` |
| `--app-modal-padding-x` | `24px` |
| `--app-modal-bar-min-height` | `50px` (stała wysokość nagłówka i stopki) |
| `--app-modal-bar-padding-y` | `4px` |
| `--app-modal-control-height` | `var(--dropdown-control-height)` — 36px |
| `--app-modal-field-gap` | `16px` |

Nagłówki i stopki bazowej powłoki mają po 50px wysokości CSS,
również na telefonie. Panele i ujednolicone małe okna mają wymiary opisane powyżej.
Paski nie kurczą się przy przewijaniu treści.
Na ekranach do 600px stopka może zwiększyć wysokość i zawinąć akcje,
aby ich etykiety pozostały dostępne. Podgląd plików zachowuje pojedynczy rząd.

Bazowy nagłówek używa tekstu 15px/400 oraz wspólnego przycisku zamknięcia 34px
po prawej. Nie dodaje dekoracyjnej ikony walizki; istniejące przełączniki
typu kontaktu zachowują działanie. Pola tekstowe, daty i listy wyboru mają
tekst 13px, wysokość 36px, ramkę `--border-color` i radius
`--dropdown-control-radius`. Opisy mają minimum 84px i możliwość zmiany
wysokości. Kolory, checkboxy, pola ukryte i źródła niestandardowych selectów
zachowują własną obsługę. Pola tekstowe, opisy, daty, wyszukiwarki wewnątrz
dropdownów i przyciski list wyboru zachowują zwykłą cienką ramkę podczas
hover, fokusu i otwarcia listy — bez zewnętrznej poświaty lub dodatkowego
obrysu. Reguła jest wspólna dla wszystkich okien w `modal-system.css`.
Oznaczenia błędów walidacji oraz zaznaczenie opcji na liście pozostają widoczne.

Listy wyboru korzystają ze wspólnej warstwy
[dropdown-layer.js](../static/js/dropdown-layer.js) i
[dropdown-layer.css](../static/css/components/dropdown-layer.css).
`AncoreDropdownLayer.open(menu, button, onClose)` wyświetla menu przez natywne
`popover="manual"` w najwyższej warstwie przeglądarki, ponad oknem i jego stopką.
Menu pozostaje w DOM formularza, więc zachowuje delegację zdarzeń i pułapkę fokusu.
Nie wyłączaj `overflow` przewijanej treści modala ani nie zwiększaj lokalnie
`z-index`, aby ominąć przycinanie. Warstwa dobiera kierunek góra/dół według
miejsca w widocznym obszarze ekranu, ogranicza wysokość listy i uwzględnia skalę UI.
Lista ma co najmniej szerokość kontrolki i wspólną szerokość bazową 240px
(`--dropdown-menu-min-width`, domyślne `--dropdown-menu-width`). Dłuższe opcje
mogą rozszerzyć ją do 360px
(`--dropdown-menu-max-width`); szersze pola formularzy zachowują wyrównanie
do kontrolki. Widoczna szerokość ekranu ogranicza wszystkie te wartości,
także po zmianie rozmiaru okna. Długi tekst opcji zawija się, zamiast ucinać
nazwę; tooltip udostępnia jej pełną treść.
`dropdown-layer.css` określa wspólną powierzchnię list wyboru i menu akcji:
ramkę, tło, cień, zaokrąglenia, font, odstępy i podświetlenie pozycji.
Przełącznik Workspace korzysta z tych samych tokenów. Wielopolowe panele
filtrów zachowują układ, a listy ich pól używają wspólnej warstwy.
Aktualizuje pozycję przy przewijaniu i zmianie rozmiaru; gdy kontrolka znika
z przewijanego obszaru lub modal zostaje zamknięty/usunięty, zamyka też menu.
Escape zamyka najpierw listę i przywraca fokus kontrolce; kliknięcie poza listą,
przeniesienie fokusu lub `ancore:content-loaded` również ją zamyka.
Przy własnym zamykaniu kontrolka wywołuje `AncoreDropdownLayer.hide(menu)`.
Każda lista wyboru w oknie formularza ma wyszukiwarkę, również przy niewielu
opcjach (np. status, priorytet, kolor). `AncoreCustomSelect` dodaje ją domyślnie
w oknach; wspólna warstwa uzupełnia pozostałe listy, które nie mają własnego
wyszukiwania. Pole używa wyglądu `ancore-custom-select__search`, filtruje opcje
bez zmiany wybranej wartości i pokazuje „Brak wyników”. Strzałki nawigują
po widocznych opcjach, Enter zatwierdza wybór, a Escape zamyka listę.
Ponowne otwarcie czyści zapytanie. Istniejące wyszukiwarki firm/osób i źródeł
zachowują własną obsługę wyszukiwania oraz dodawania wartości.
Listy wielokrotnego wyboru i zwykłe selecty z ponad ośmioma opcjami mają
wyszukiwarkę również poza modalami; wyszukiwanie pomija polskie znaki.
`AncoreCustomSelect` zachowuje podglądy `data-ancore-option-preview`
i ikony `data-ancore-option-icon`, a pozostałym opcjom dobiera ikonę pola.
Wspólna warstwa uzupełnia ikony prostych filtrów, sortowania i paginacji.
`core.widgets.VisualSelect/VisualSelectMultiple` przekazują serwerowe ikony
lub podglądy przez lokalne szablony, bez zmiany wartości opcji i walidacji.
Filtry zadań pokazują awatary/zdjęcia widocznych przestrzeni, wykonawców
i zespołów, kolorowe typy zgłoszeń, statusy i priorytety. Podglądy korzystają
z tych samych include'ów co szczegóły i zachowują kontrolowane adresy obrazów.
`UserSelectMultiple` rozszerza podglądy kont o wybór osób w dostępie Pulpitów
i Filtrów. `SpaceSelect` i `TeamSelect` zachowują queryset formularza;
formularz Zasobów używa istniejącego `UserSelect`. Brak zdjęcia pokazuje
obecny awatar lub ikonę. Miniatury kont/przestrzeni/zespołów mają 24px.
Warstwa obejmuje `AncoreCustomSelect`, priorytety/statusy/tagi oraz wybór projektu
i grupy w zadaniach, listy firm/osób, Kontaktów, Kalendarza i Profilu,
również w szczegółach zadań/Kanbana. Ta sama zasada obowiązuje w listach
filtrów i prostego sortowania, warunkach tekstowych w panelach filtrów
(także Dysku i Dokumentów), wyborze liczby wierszy we wszystkich katalogach
i Workspace oraz filtrze aktywności zadania/karty. Lista filtra w zbiorczym
panelu otwiera się ponad panelem i stosuje wspólną minimalną szerokość bez zmiany
układu pozostałych pól. Wielopolowe panele konfiguracji filtrów/sortowania
zachowują własną szerokość; menu działań mają wspólną szerokość bazową,
zawarte w nich listy wyboru korzystają z tej samej warstwy co formularze.
Rozwijane panele edycji firmy/osoby z
`position: static` zachowują swój układ wewnątrz formularza.

`tasks-form-field` łączy widoczną etykietę z kontrolką w pionie z odstępem
6px. Nazwy i opisy używają tego samego wariantu w tworzeniu i edycji.
Parametry projektów/przestrzeni mają dwie kolumny, do 600px jedną;
tak samo zawężają się pola zadań, kontaktów i wydarzeń. Przyciski „Anuluj”
korzystają z dotychczasowych akcji zamykania danego modułu. Upload Dysku
i Dokumentów grupuje wskazówki oraz wybór plików w `documents-upload-control`,
z jedną delikatną ramką i listą wybranych plików poniżej.

`showConfirmModal` używa wspólnego nagłówka, treści i stopki opartej na tych
samych tokenach. Potwierdzenia usunięcia notatki projektu/grupy/tagu i kontaktu
lub firmy korzystają z niego zamiast natywnego `confirm()`. Delegacja działa
także dla nowych notatek oraz po `ancore:content-loaded`. Escape zamyka
najwyższe potwierdzenie, zachowując okno notatek pod nim; ponowne kliknięcie
potwierdzenia podczas zamykania nie wysyła drugiego żądania. Błędy operacji
w szczegółach zadań i Kanbana używają wspólnych powiadomień zamiast `alert()`.

Modal ma nazwę dostępną dla czytnika, sensowny fokus po otwarciu, obsługę
klawiatury i powrót fokusu. Błędy formularza zachowują wpisane dane. Podczas
zapisu użytkownik dostaje stan oczekiwania, a powtórne wysłanie jest kontrolowane.

Dysk jest przykładem dialogu HTML pobieranego nagłówkiem `X-Document-Modal`.
Obsługa aktywuje `inert` na tle i przywraca je po zamknięciu. Nie należy
dodawać drugiej równoległej powłoki tylko dlatego, że nowy formularz jest w innym module.

Podgląd Dysku używa tej samej powłoki i obsługi `data-document-dialog`.
Wariant `documents-preview-modal` zajmuje niemal całą szerokość i wysokość ekranu,
z marginesem 1rem z każdej strony i uwzględnieniem skali UI oraz dynamicznej
wysokości viewportu. Treść wypełnia miejsce między nagłówkiem a stałą stopką;
nie ma limitu szerokości 1100px ani wysokości treści 650px.
Nagłówek pokazuje nazwę dokumentu. Pod nim zaczyna się zawartość podglądu;
nie ma dodatkowego paska metadanych ani stałego komunikatu nad czytnikiem PDF.
Czytnik PDF wypełnia obszar treści bez wewnętrznych odstępów na komputerze
i telefonie; tekst, tabele i komunikaty zachowują standardowy padding.
Przewijana treść mieści obraz/PDF, tekst, tabele arkuszy albo listę archiwum;
stopka zawiera „Edytuj dane”, „Pobierz” i „Zamknij”. Nagłówek i stopka mają
po 50px wysokości CSS i po 4px paddingu pionowego. Stopka zachowuje jeden rząd
przycisków, z mniejszymi odstępami bocznymi na telefonie. Tabele mają własny
poziomy scroll, a tekst zawija się.
Podgląd i formularz mogą zastępować się w jednym hoście. Fokus, Escape, Tab
i powrót do wybranego pliku korzystają ze wspólnej obsługi Dysku.
Pusty, nieobsługiwany, uszkodzony i niedostępny plik mają osobne komunikaty;
obraz sygnalizuje ładowanie i błąd. Natywny czytnik PDF obsługuje własną klawiaturę.

## 7. Ikony i typografia

Wspólna powłoka, formularze, logowanie i wybór Workspace używają **Atlassian Sans**,
tego samego kroju co obecny interfejs Jiry. Token `--font-family-ui` w
`base/variables.css` jest jedynym źródłem rodziny fontu interfejsu.
`base/fonts.css` ładuje lokalne pliki WOFF2: latin i latin-ext (polskie znaki),
zwykły krój i kursywę, ze zmienną wagą 100–900 oraz `font-display: swap`.
Oba bazowe szablony wstępnie pobierają zwykły krój. Font nie wymaga CDN.
Źródło, wersja, sumy kontrolne i licencja SIL OFL 1.1 znajdują się w
[static/vendor/atlassian-sans](../static/vendor/atlassian-sans/README.md).
Rozmiary, wagi i odstępy istniejących komponentów pozostają bez zmian;
dekoracyjny Playfair Display na ekranach uwierzytelniania zachowuje swój krój.
Osobne edytory w iframe (Excalidraw/ONLYOFFICE) zarządzają własną typografią.

Biblioteka ikon to **Flaticon UIcons Regular Rounded 3.3.1**, ładowana lokalnie
w bazowych szablonach aplikacji i uwierzytelniania. Lokalny adapter
[flaticon-icons.js](../static/js/flaticon-icons.js) normalizuje nazwy i udostępnia
`AncoreIcons.render(scope)`, `create`, `html`, `safeName` i `normalize`.
Nazwy używane przez moduły pozostają stabilne; ich odpowiedniki Flaticon określa
[mapowanie](../scripts/flaticon-icon-map.json). Nie wymagają migracji danych.
`data-icon` jest wspólnym atrybutem placeholdera i wygenerowanego SVG;
`data-flaticon` wskazuje nazwę źródłową UIcons. Ponowne renderowanie jest idempotentne,
obejmuje również przekazany element główny i działa na `ancore:content-loaded`.
Nieznane nazwy używają podanego fallbacku lub `circle`.

Kontury SVG dziedziczą `currentColor`, zachowując istniejącą geometrię kontrolek.
Flaticon używa wypełnionych konturów, dlatego `.ancore-icon` wyłącza obrys `stroke`;
nie stosuj do nich `stroke-width`. Checkboxy, strzałki selectów i wskaźniki statusu
korzystają z lokalnych SVG przez tokeny `--icon-*`.
Zestaw, licencja i instrukcja odtworzenia znajdują się w
[static/vendor/flaticon](../static/vendor/flaticon/README.md).
Oznaczenie źródła ikon jest widoczne w Ustawieniach i na ekranach uwierzytelniania.

```html
<button type="button" class="btn btn-secondary btn-sm" aria-label="Odśwież listę">
    <i data-icon="refresh-cw" aria-hidden="true"></i>
    Odśwież
</button>
```

To przykład użycia istniejących klas, bez nowej stylistyki. Ikona dekoracyjna
ma `aria-hidden`; przycisk z samą ikoną wymaga etykiety. Projekty i grupy mają
wycofane edytowalne ikony encji — nie przywracaj dawnych pickerów.

## 8. JavaScript jako część komponentu

| API / zdarzenie | Zastosowanie |
| --- | --- |
| `AncoreIcons.render(scope)` | Ikony po wstawieniu HTML |
| `AncoreCustomSelect.init/refresh/closeAll` | Dropdowny i odświeżanie opcji |
| `AncoreDropdownLayer.open/hide/dismiss` | Wspólna szerokość, pozycjonowanie i najwyższa warstwa list wyboru w całej aplikacji |
| `AncoreApp.canNavigatePartially(url)` | Sprawdzenie, czy adres obsługuje częściową nawigację |
| `AncoreApp.navigate(url, options)` | Istniejąca nawigacja aplikacji |
| `AncoreApp.invalidateManagementReturn(paths)` | Usunięcie lokalnych celów powrotu po potwierdzonym skasowaniu obiektu |
| `showConfirmModal(options)` | Wspólne potwierdzenie operacji |
| `ancore:content-loaded` | Ponowne uruchomienie logiki po podmianie widoku |
| `ancore:file-upload-updated` | Zmiana listy dodawanych plików |
| `ancore:task-description-ready` | Gotowość opisu zadania po inicjalizacji |

Obsługa `data-*`, nazwy pól, ukryty select, klasy stanu i URL są częścią
kontraktu komponentu. Samo odtworzenie wyglądu bez tego kontraktu może zepsuć
filtrowanie, zapis, dostępność albo częściową nawigację.

Nie każda klasa `tasks-*` jest specyficzna dla Zadań: wiele z nich jest już
używanych w Kontaktach, Workspace i Dysku. Przed zmianą selektora
przeszukaj całe repozytorium.

## 9. Responsywność i geometria

Układ używa zmiennych viewportu skorygowanych o skalę UI oraz kontrolowanego
przewijania. `html`/`body` mają reguły `overflow`, a listy i dialogi własne
obszary scrollowania. Dodanie przypadkowego `100vh`, globalnego `overflow:auto`
albo zmiana `position` może naruszyć całą powłokę.

Sprawdź [responsive.css](../static/css/layout/responsive.css), końcowe reguły
`style.css` oraz media queries komponentu. JS rozróżnia m.in. 1024px i 767px.
Przy zmianie szerokości/sidebaru testuj stan zwinięty i rozwinięty, tablet,
wąski ekran oraz duży desktop. Istnieją również reguły dla ograniczenia ruchu.

## 10. Procedura zmiany UI

1. Wskaż istniejący ekran/komponent o podobnej funkcji.
2. Obejrzyj go w przeglądarce; sprawdź szablon, CSS, JS i końcowe style.
3. Wykorzystaj istniejący include/klasę/token. Dopiero przy rzeczywistym braku
   wzorca dodaj mały wariant komponentu.
4. Styl specyficzny dla modułu ogranicz do jego kontenera. Nie dopisuj globalnego
   `button`, `input`, `h2` lub szerokiego `!important` jako lokalnej poprawki.
5. Zachowaj wspólny rozmiar, wyrównanie, ikony, stany hover/focus/disabled,
   błędy walidacji i sposób zapisu.
6. Przy zmianie importowanego CSS/JS sprawdź istniejące parametry `?v=`
   i zaktualizuj właściwe odwołania, jeśli wymaga tego odświeżenie cache.
7. Sprawdź zmieniany ekran i co najmniej najbliższego odbiorcę wspólnego komponentu.
8. Dopisz nowy wariant/wzorzec do tego dokumentu, jeśli ma być stosowany dalej.

## 11. Zakres wizualnej weryfikacji

- Pierwsze wejście, ponowne wejście, reload, back/forward i częściowa nawigacja,
  jeśli dana ścieżka ją obsługuje.
- Pusta lista, zwykłe dane, długi tekst, brak obrazka, zaznaczone wiersze.
- Otwarty/zamknięty dropdown i modal, błędny formularz oraz stan zapisu.
- Klawiatura, widoczny fokus, etykiety ikon i powrót fokusu.
- Responsywność i scrollowanie bez uciętych przycisków/stopki.
- Porównanie rozmiarów, odstępów, fontu i kolorów z ekranem referencyjnym.

Wynik weryfikacji zapisuj w podsumowaniu zadania. Jeśli nie oglądano ekranu
w przeglądarce, nazwij weryfikację przeglądem kodu, a nie wizualnym testem.

## 12. Zarządzanie Workspace i zespołem

Katalog `/workplaces/` jest osobną stroną administracyjną, tak jak
„Zarządzaj przestrzeniami”. Zastępuje codzienne menu własnym
`core/includes/workplace_management_sidebar.html` (tryb `workplaces`):
Link powrotu prowadzi do miejsca wejścia (z Ustawień: „Wróć do ustawień”),
a „Workspace” jest pozycją aktywną. Bez wcześniejszego wejścia w aplikacji
domyślnym powrotem jest Dashboard aktywnego Workspace. Menu nie zawiera
dodatkowych pozycji przestrzeni ani Ustawień Ancore.
Treść zajmuje całą szerokość obok głównego paska; nie zawiera dodatkowego menu
ustawień. `render_workplaces` zachowuje ten tryb również dla okien zespołu,
zaproszeń i błędów formularzy. Istniejący `layout.js` synchronizuje osobne menu
każdego ekranu przy częściowej nawigacji i przejściach Wstecz/Dalej.
Powrót zachowuje pełny adres poprzedniego widoku, kategorię ustawień,
filtry i pozycję przewinięcia. Punkt wejścia jest zapisany w historii i
`sessionStorage` osobno dla obu ekranów, konta, Workspace i karty przeglądarki;
pozostaje dostępny po przeładowaniu, otwieraniu okien i błędach/zapisie formularzy.
Oglądanie lub edycja wybranego Workspace nie przełącza aktywnego kontekstu pracy.

Profil użytkownika korzysta ze wspólnego okna `core/includes/avatar_picker.html`
i `workplace-avatars.js`, z osobną pulą 30 zwierzęcych maskotek w
`accounts/avatar_presets.py`. Lokalne atlasy `static/img/user-avatars/illustrations-v1.png`
oraz `illustrations-extra-v1.png` zachowują proste wypełnione kształty i kolorystykę
Przestrzeni i Workspace; nie zawierają portretów ludzi. Dodatkowe sześć ilustracji
to ośmiornica, wieloryb, żółw, nietoperz, pszczoła i dinozaur. Pierwotne 24 grafiki
i wybór automatyczny pozostają niezmienione. Klasy `user-avatar-art--*` są oddzielone od motywów
Workspace. Siatka wyboru zachowuje kwadratowe kafelki, a awatary użytkownika
w aplikacji pozostają okrągłe w dotychczasowych rozmiarach.
Kliknięcie awatara na profilu otwiera edycję oraz okno wyboru; w edycji dostępny
jest także przycisk „Zmień”. Zapis w pickerze zatwierdza szkic, a „Zapisz” profilu
utrwala go. Wspólna obsługa zapewnia wybór automatyczny, upload z kadrowaniem,
przeciąganie, anulowanie, Escape, fokus i inicjalizację po częściowej nawigacji.
Pula kont nie zmienia dostępnych motywów Przestrzeni ani Workspace.

Workspace korzysta z tych samych 30 ilustracji co Przestrzenie. Wspólne
`core/avatars.py` i `core/includes/avatar_presets.html` definiują motywy
oraz siatkę radio; `space-avatars.css` obsługuje atlasy i zaznaczenie.
W formularzach tworzenia i edycji kliknięcie awatara albo „Dodaj”/„Zmień”
otwiera osobne okno „Wybierz awatar” z powłoką `app-modal-panel--compact`,
tak jak w Przestrzeniach. Siatka nie jest widoczna w głównym formularzu.
Okno zawiera ilustracje, wybór automatyczny i własny obraz z przyciskiem
„Wybierz obraz”, przeciąganiem oraz istniejącym kadrowaniem. Zatwierdzenie
kadru zaznacza „Własny obraz”. „Zapisz” w oknie zatwierdza wybór w formularzu
Workspace; zapis Workspace utrwala go w bazie. „Anuluj”, krzyżyk, tło i Escape
przywracają poprzedni wybór wraz z obrazem, pozostawiając formularz otwarty
i zachowując jego pozostałe pola. Fokus wraca do klikniętego awatara lub przycisku.
Na czas otwarcia okno jest przenoszone nad formularz, a tło staje się `inert`.
Pola zachowują powiązanie z formularzem przez atrybut `form`; po zamknięciu
wracają na swoje miejsce. Tab pozostaje w najwyższym oknie, także przy kadrowaniu.
Awatar automatyczny jest stabilnie dobierany według ID, dotychczasowe obrazy
pozostają widoczne. Błędy zachowują wybrany motyw.
Edycja wymaga właściciela lub administratora.
Ilustracje mają zaokrąglone kwadratowe tło; rozmiary tabeli i przełącznika
pozostają dotychczasowe. Te same motywy pojawiają się w katalogu, bieżącym
Workspace i menu przełączania. `workplace-avatars.js` inicjalizuje picker
również po `ancore:content-loaded`, bez powielania listenerów.
`profile.js` udostępnia snapshot/restore zaakceptowanego kadru oraz zdarzenia
`ancore:photo-preview`, `ancore:photo-saved` i `ancore:photo-error`. Pozwala to
cofnąć szkic obrazu przy anulowaniu okna awatara i wyświetlić błąd odczytu.
Spóźniony odczyt anulowanego obrazu nie otwiera ponownie kadrowania.


Oczekujące zaproszenia odbiorcy są widoczne w istniejącym panelu powiadomień,
przed aktywnością zadań. Karta podaje autora, Workspace, rolę, termin i przycisk
„Przyjmij lub odrzuć zaproszenie”. Dzwonek pokazuje jasnofioletowy licznik oczekujących
zaproszeń `notifications-toggle__invitation-count` (do 9, potem „9+”). Pełna liczba
jest dostępna w opisie i podpowiedzi. Tło licznika używa `--primary-button-bg`,
tak jak liczniki zakładek powiadomień, a tekst `--text-primary`.
Gdy nie ma zaproszeń, nieprzeczytane wpisy
sygnalizuje kropka `notifications-toggle__indicator`. Opis czytnika ekranu
rozróżnia obie liczby. Znaczniki zaproszeń są renderowane także przed uruchomieniem JS.

Link powiadomienia `?invitation=<pk>` otwiera okno konkretnego zaproszenia nad
katalogiem Workspace.
Include `workplaces/includes/invitation_response_modal.html` korzysta z
`tasks-modal`, standardowej stopki i kompaktowej listy szczegółów
`workplace-invitation__details`. Akcje „Później”, „Odrzuć” i „Przyjmij” są razem
w stopce; wspólne przyciski paginacji pozwalają przejść do innych zaproszeń.
`workplace-team.js` obsługuje ten modal także na stronie Workspace przez
`data-team-modal-page`, zachowując inert, fokus i inicjalizację po częściowej
nawigacji. Zamknięcie usuwa parametr zaproszenia z adresu i przywraca fokus
polu „Szukaj Workspace” w pasku katalogu. Formularz nadal wymaga POST i CSRF.

Ekran `/workplaces/` rozszerza `core/base.html` i pokazuje katalog Workspace.
Nazwa Workspace może się powtarzać. Kolumna „Kod miejsca pracy” pokazuje stały
losowy identyfikator `w_` + 26 małych liter/cyfr. Minimalna szerokość kolumny kodu
wynosi 250px, aby pomieścić cały identyfikator; `title` udostępnia pełną wartość.
W tworzeniu pole jest tylko do
odczytu i pokazuje „Generowany automatycznie”; kod jest nadawany przy zapisie.
W edycji i podglądzie pole pozostaje tylko do odczytu dla każdej roli i pokazuje
zapisany identyfikator. Pola kodu nie są wysyłane w formularzach, a backend
ignoruje próby jego nadpisania. Zmiana nazwy nie zmienia kodu ani adresu.
Powłoka, klasy pól i obsługa modali pozostają wspólne z Projektami.
Widoczny tytuł „Workspace” na górnym pasku ma rozmiar 17px i grubość 700.
Nie ma zakładki, tabeli ani licznika otrzymanych zaproszeń; są dostępne
przez panel powiadomień. Dawny parametr `view=received` pokazuje katalog.
Pasek nie ma osobnego przycisku „Workspace” ani separatora po nim.
Pasek ma odstępy, przyciski i menu takie jak Dokumenty.
Katalog ma dwa wspólne paski, jak Dokumenty i Projekty:
`tasks-topbar--directory` z tytułem i akcjami oraz `tasks-filterbar--directory`
(`management_toolbar.html`) z wyszukiwaniem i paginacją katalogu.
Wysłane zaproszenia i przycisk „Zaproś osobę” są w oknie miejsca pracy.
W katalogu wyszukiwanie i kompaktowa paginacja znajdują się po prawej stronie
drugiego paska. Paginacja używa wspólnych klas `tasks-project-pagination--toolbar`,
zachowując filtrowanie i zmianę strony w przeglądarce; zakres i liczba wyników
zastępują osobny dolny pasek z numerami stron. Pod paskami zaczyna się tabela.

„Workspace” pokazuje pełną listę, wyszukiwanie, dodawanie, ustawienia i paginację.
Znacznik „Bieżący” wskazuje aktywną przestrzeń. Nazwa otwiera „Główną” w oknie
miejsca pracy, a liczba członków — zakładkę „Członkowie”. Kolumna „Działania”
(40px, pusty wizualnie nagłówek) zastępuje kolumnę koła zębatego. Przycisk
trzech pasków korzysta ze wspólnego `row-actions.js` i popovera Dokumentów.
Menu otwiera edycję, członków i wysłane zaproszenia; zwykły członek widzi
informacje tylko do odczytu oraz członków. Zamknięcie menu przez Escape
i zamknięcie otwartego z niego okna przywracają fokus przyciskowi menu.
Kliknięcie pozostałej części wiersza (także kodu, opisu, roli i statusu)
otwiera tę samą „Główną” przez link nazwy. Enter i Spacja na wierszu działają
tak samo. Checkbox, przełączanie, menu i link członków zachowują własne
akcje; zaznaczanie tekstu nie otwiera okna. Obsługa w `workplace-team.js`
działa także po częściowej nawigacji, bez powielania listenerów.
Ikony przełączania i menu w tabeli używają podświetlenia
całej komórki, tak jak ikony projektów: `rgba(var(--system-accent-rgb), 0.24)`
na delikatnym fioletowym tle wiersza. Hover i fokus klawiatury zachowują
siatkę tabeli, bez dodatkowego obrysu i cienia. Komórki ikon mają jedną
kolumnę `minmax(0, 1fr)`, aby przycisk wypełniał ich szerokość. Wyłączone
przełączanie bieżącego Workspace nie otrzymuje tego podświetlenia.
`team_panel.html` renderuje tabelę składu lub wysłanych zaproszeń wewnątrz
osobnych zakładek okna. Workspace wybieramy przez katalog.

Pasek filtrów zachowuje wysokość wiersza z polem wyszukiwania Dokumentów
(`--dropdown-control-height` plus wspólny padding i ramka) oraz zawijanie
na telefonie.
`team_modals.html` dostarcza istniejące okna zaproszenia
i roli. Przełączenie zakładki lub wybór Workspace nie zmienia aktywnej
przestrzeni pracy. Ustawienia wracają po zapisie do katalogu.

Okno w `edit_modal.html` ma zakładki „Główna”, „Członkowie” i — tylko dla
zarządzających — „Wysłane zaproszenia”, korzystające
z `notifications-tabs tasks-issue-tabs`, jak szczegóły zadania: tekst 15px/400
i fioletowe podkreślenie. Zmiana zakładki zachowuje wpisane ustawienia;
strzałki, Home i End przełączają treść oraz fokus. Zakładki mają role i relacje
`tablist`/`tab`/`tabpanel`. Przycisk „Zapisz zmiany” jest widoczny na „Głównej”,
a „Zaproś osobę” nad tabelami członków i wysłanych zaproszeń. Formularz ustawień jest oddzielony od
formularzy akcji członków, aby uniknąć zagnieżdżania formularzy.
Błąd ustawień otwiera „Główną” z wartościami i komunikatami walidacji.
Dla zwykłego członka pola są tylko do odczytu, bez przycisku zapisu.

Serwer renderuje jeden modal wybranego Workspace. Link do innego Workspace
pobiera jego kontekst; ponowne otwarcie bieżącego okna działa lokalnie.
Stare linki `view=members` otwierają skład nad katalogiem. Zamknięcie okna
usuwa żądanie otwarcia z adresu, więc reload pozostawia katalog.
`workplace-team.js` obsługuje zakładki, fokus i inert ostatniego otwartego okna,
a wspólny `AncoreTaskModals` zamykanie oraz klawiaturę. Zamknięcie okna roli
lub zaproszenia odsłania nadal otwartą zakładkę. Przy błędzie wysyłania
okno zaproszenia jest nad „Wysłane zaproszenia”; zamknięcie przywraca fokus
widocznemu przyciskowi tej zakładki. Inicjalizacja działa
również po `ancore:content-loaded` bez powielania listenerów.

Tabele członków (`members_table.html`) i wysłanych zaproszeń
(`invitations_table.html`) korzystają z tego samego komponentu
co „Projekty”: `tasks-directory-board tasks-directory-sheet
tasks-project-sheet`, wspólnych nagłówków, komórek i wierszy. Wariant
`workplace-team-sheet` określa wyłącznie układ sześciu kolumn: zaznaczenie
(40px), działania (40px), nazwa z avatarem, e-mail, rola i data dołączenia
lub ważności zaproszenia. Nagłówki danych mają ikony; nagłówek kolumny
działań jest pusty wizualnie i zachowuje etykietę dostępną „Działania”.
Wiersze zachowują wysokość 35px, tekst 13px/400, cienką siatkę i jasnofioletowe
podświetlenie z paskiem po lewej. Avatary członków i odbiorców zaproszeń mają
30×30px, jak na liście Kontaktów, również na wąskich ekranach. Stały rozmiar
obejmuje zdjęcia oraz ikonę zastępczą i nie kurczy się przy długiej nazwie.
Menu członka lub zaproszenia jest w osobnej komórce działań,
z takim samym przyciskiem wypełniającym komórkę jak akcje projektów.
Tabela ma role `table`/`rowgroup`/`row`/`columnheader`/`cell`.
Układ kolumn skaluje się z oknem; `data-directory-resize="false"` wyłącza
zapamiętywanie i ręczne rozszerzanie kolumn przez mechanizm katalogu projektów.
Checkboxy używają `tasks-project-sheet--selectable` i `tasks-row-checkbox`,
tak jak „Projekty”. Nagłówek zaznacza wszystkie wiersze wyłącznie
swojej tabeli i pokazuje stan częściowego wyboru. Kliknięcie pustego miejsca
w kolumnie zaznaczenia też przełącza checkbox. `workplace-team.js`
synchronizuje podświetlenie i nagłówek niezależnie dla obu zakładek, również
po `ancore:content-loaded`. Przełączanie zakładek zachowuje wybór;
zaznaczenie nie wykonuje operacji na członkach ani zaproszeniach.

Nazwa i e-mail pozostają w jednym wierszu z ellipsis oraz pełną treścią
w `title`. Na telefonie obie tabele zachowują kolumny i wiersze, przewijając
się poziomo we własnym kontenerze o minimalnej szerokości zawartości 890px.
Pusty stan członków używa `tasks-empty-state`, a wysłanych zaproszeń
`documents-empty documents-grid-empty`; oba mieszczą się w szerokości okna
i nie wyświetlają pustych nagłówków tabeli.
Wspólny pusty stan `documents-empty` centruje ikonę nad tytułem i opisem
przez blokowe SVG z automatycznymi marginesami bocznymi, zachowując 16px
odstępu pod ikoną. Reguła obowiązuje też w pustych katalogach Dokumentów.

Parametr `view=invitations` otwiera zakładkę „Wysłane zaproszenia” w oknie;
po wysłaniu lub anulowaniu zaproszenia użytkownik wraca do tej zakładki.
Na wąskim ekranie wspólny pasek zakładek można przewijać poziomo; klawiatura
przewija go do aktywnej pozycji.

Menu trzech pasków używa wspólnego mechanizmu akcji wiersza: w tabeli
członków i wysłanych zaproszeń zajmuje osobną kolumnę. Wspólny `row-actions.js`, ładowany w `core/base.html`,
obsługuje zarówno `data-document-actions`, jak i `data-row-actions`. Zachowuje
popover, pozycjonowanie względem viewportu i skali UI, obsługę klawiatury,
zamykanie przy przewijaniu oraz inicjalizację po `ancore:content-loaded`.
W Zespole menu zawiera zmianę roli, odebranie dostępu lub anulowanie zaproszenia,
zależnie od uprawnień. Właściciel nie ma akcji zmiany swojej roli ani usunięcia.

Zaproszenie, odpowiedź na zaproszenie i zmiana roli używają wspólnej powłoki
`tasks-modal app-modal-panel app-modal-panel--compact`, pól
`tasks-form-field` i stopki z `tasks-modal__submit`. `workplace-team.js` zarządza
otwarciem, `inert` tła, fokusem i blokadą ponownego wysłania; `tasks.js` obsługuje
zamykanie i pułapkę fokusu, a listy wyboru korzystają z `AncoreCustomSelect`
i `AncoreDropdownLayer`. Błąd zaproszenia otwiera ten sam modal z wpisanymi danymi.
Formularz zaproszenia ma pole osoby po lewej i „Rolę” po prawej, w jednym
wierszu `workplace-invite__fields`. Kolumna roli ma 180px, a pole osoby zajmuje
pozostałą szerokość; etykiety są nad kontrolkami. Podpowiedzi i podgląd pozostają
pod polem osoby. Do 600px pola przechodzą do jednej kolumny, zgodnie ze wzorcem
formularzy kontaktowych.
Pole osoby w zaproszeniu ma podpowiedzi od 2 znaków imienia, nazwiska, ID Ancore
lub e-maila. Wariant `workplace-invite__results` pokazuje przewijaną listę pod
polem, w białej treści modala; korzysta ze wspólnych przycisków menu, układu
tożsamości `tasks-responsible-select__person` i avatara 30px. Po wyborze pozostaje
nazwa i e-mail odbiorcy z komunikatem „Zapraszasz”. Pełny pasujący e-mail także
pokazuje odbiorcę. Lista ma role combobox/listbox/option; strzałki wybierają,
Enter zatwierdza osobę, Escape najpierw zamyka podpowiedzi. Zmiana tekstu usuwa
poprzedni wybór. Obsługa anuluje nieaktualne żądania oraz sprząta je przy zamknięciu
i częściowej nawigacji. Status komunikuje ładowanie, brak wyników, limit i błąd;
przy błędzie nadal można ręcznie wpisać adres. Dopiero przycisk zaproszenia zapisuje.
Odebranie dostępu wymaga `showConfirmModal` wyjaśniającego wpływ na Office.
Zapis nadal używa POST, CSRF i komunikatów aplikacji.

Ustawienia prowadzą do wspólnego panelu przez „Zarządzaj Workspace”. Funkcje i role opisuje
[TEAMWORK.md](TEAMWORK.md).

## 13. Centrum powiadomień

Powiadomienia są dostępne wyłącznie w panelu dzwonka. Panel używa include'ów
`notification_controls.html`, `notification_list.html`, `notification_pagination.html`
oraz `notifications-panel.js` i `notifications-panel.css`. Używa tej samej powłoki
`tasks-modal app-modal-panel` co „Utwórz zadanie”: szerokiego okna z jasnoszarym
tłem, białą treścią, wspólnymi odstępami i animacją. Nagłówek zawiera tytuł
„Powiadomienia” i standardowy krzyżyk. Stała stopka zawiera „Zamknij” oraz
paginację „Pokaż starsze”, gdy są dalsze wpisy. Wariant `notifications-panel__body`
układa filtry i niezależnie przewijaną listę pionowo we wspólnej białej powierzchni.
Avatary kont, przyciski, ikony i tokeny kolorów pozostają wspólne.
Białe karty mają delikatne ramki; nieprzeczytane dodatkowo kropkę i 5% akcentu
w tle. Zaproszenia mają przycisk prowadzący do istniejącego modala decyzji.

Zakładki „Wszystkie”, „Nieprzeczytane”, „Zaproszenia”, „Przypomnienia”, „Archiwum” używają
przycisków z `aria-pressed`; filtr Workspace korzysta ze wspólnego selecta.
„Zaproszenia” pokazuje pełną liczbę oczekujących zaproszeń z centrum powiadomień,
ze wszystkich Workspace, podobnie jak globalny licznik nieprzeczytanych.
Licznik na zakładce i dzwonku pozostaje po oznaczeniu zaproszenia jako przeczytane.
Jest ukryty przy zerze; korzysta z istniejącego `pending_invitation_count`, więc
nie obejmuje zaproszeń rozpatrzonych, cofniętych, wygasłych ani usuniętych z powiadomień.
Wspólne odświeżanie aktualizuje oba miejsca po operacji, powrocie na stronę i pollingu;
zmiana liczby oczekujących także sygnalizuje potrzebę odświeżenia otwartej listy.
Filtr Workspace zachowuje zwykłą cienką ramkę po najechaniu, uzyskaniu fokusu
i otwarciu listy, bez dodatkowego obrysu ani poświaty, tak jak pola w modalach.
Karty grupują się według daty, pokazują podgląd komentarza, szczegóły zaproszenia
lub przypomnienia, Workspace, moduł, numer rekordu i czas z pełną datą w tooltipie.
Wpisy historii zmian nie pojawiają się w żadnym filtrze ani liczniku panelu.
Puste stany „Wszystkie” i „Obserwowane” opisują komentarze i pozostałe dostępne
typy powiadomień, bez zapowiadania historii zmian.
Na każdej karcie jest jeden stale widoczny przycisk z trzema paskami (`menu`).
Otwiera wspólne menu `row-actions.js` z akcją odczytu, archiwizacji/przywrócenia
i usunięcia; zaproszenia nie mają akcji archiwizacji. Menu korzysta z
`tasks-section-menu`, `tasks-project-menu-button` i natywnego popovera,
więc nie jest przycinane przez przewijaną listę. Ma szare stany interakcji,
obsługuje strzałki, Home/End i Escape z powrotem fokusu na przycisk.
Zdarzenie `ancore:notifications-loaded` inicjalizuje menu również po doczytaniu
starszych stron i zmianie stanu. Odświeżenie listy lub zamknięcie panelu zamyka
otwarte menu; zapis blokuje przyciski i przywraca fokus na widoczny przycisk karty.
„Oznacz wszystkie jako przeczytane” obejmuje bieżący filtr, również starsze strony;
przycisk jest nieaktywny, gdy wszystkie wpisy w tym widoku są przeczytane.
Kosz w pasku usuwa wszystkie powiadomienia z bieżącego filtra, także ze starszych
stron. „Usuń powiadomienie” w menu karty usuwa tylko ten wpis. Obie akcje otwierają `showConfirmModal`
z informacją o osobistym zakresie oraz zachowaniu historii i zaproszeń w Workspace.
Potwierdzenie zbiorcze pokazuje liczbę wpisów i zachowuje snapshot z chwili otwarcia.
Tab i Escape dotyczą wtedy potwierdzenia, bez zamykania panelu pod spodem.
Zapis blokuje ponowne wysłanie; błąd zachowuje wpis i umożliwia ponowienie.
Po potwierdzonym odczycie/usunięciu wyświetla się wspólny komunikat sukcesu.
„Pokaż starsze” doczytuje listę.
Stopka nie zawiera dodatkowego opisu zakresu aktywności.
Dzwonek w górnym pasku jest przyciskiem otwierającym panel. Osobna strona powiadomień
i jej link w wyszukiwarce zostały usunięte; dawny adres przekierowuje do Dashboardu.

Stan odczytu zmienia się po potwierdzonym zapisie; samo otwarcie panelu niczego
nie oznacza. Nowe zdarzenia sygnalizuje przycisk nad listą, bez automatycznego
przesuwania treści. Stany puste mają opis zależny od filtra. Błąd pobrania ma
akcję ponowienia; błąd zapisu pozostawia wpis i komunikat `role=alert`.
Żądania mają limit czasu, a zmiana filtra anuluje starsze pobranie.

Panel deklaruje `aria-modal="true"` i blokuje treść strony, menu boczne oraz
górny pasek przez `inert`. Korzysta z `AncoreTaskModals.open/close` i zdarzeń
otwarcia/zamknięcia, więc Tab i Shift+Tab pozostają w oknie, a Escape, krzyżyk,
„Zamknij” i kliknięcie tła zamykają je z powrotem fokusu do przycisku otwierającego.
Listy wyboru i potwierdzenie usunięcia obsługują Escape przed oknem powiadomień.
Skrót wyszukiwania zamyka powiadomienia i ustawia fokus w wyszukiwarce.
Na telefonie okno zajmuje ekran, a toolbar zawija kontrolki.
Inicjalizacja po `ancore:content-loaded` nie powiela listenerów; polling działa
wyłącznie w widocznej karcie. Dane są prywatne dla konta i nie trafiają do localStorage.

### Załączniki czatu
Wspólny `comment_composer.html` rozszerza obecne pole komentarza Zadań i Kanbana.
„Dodaj pliki” używa `tasks-issue-tool` i ikony `paperclip`; przycisk wysyłania
pozostaje po prawej, także na telefonie. `tasks-comment-images` pokazuje
miniatury wiadomości, a wariant `--pending` mniejsze podglądy z krzyżykiem
usuwania przed wysłaniem. Obrazy zachowują proporcje (`object-fit: contain`).
Kliknięcie wysłanego zdjęcia otwiera kontrolowany URL w nowej karcie.
Pozostałe pliki używają `tasks-attachment-card` i wspólnych ikon załączników.
Minimalny wariant `tasks-comment-file` ogranicza kartę do 260px i szerokości
kontenera, zachowuje skracanie długich nazw, rozmiar oraz przycisk usunięcia
przed wysłaniem. Po wysłaniu karta pobiera plik (atrybut `download`).
Lista wyboru formatów w `accept` pochodzi ze wspólnego walidatora serwera.

`comment-images.js` obsługuje wybór plików, wklejenie załącznika udostępnionego
przez schowek przeglądarki do pola tekstu,
przeciągnięcie do kompozytora i zapis bez przeładowania. Błędy są przy polu
(`role=alert`), a wybór i wysyłka mają komunikaty czytnika ekranu.
W trakcie wysyłki kontrolki są zablokowane; błąd pozostawia tekst, wzmianki
i podglądy do poprawienia lub ponowienia. Sukces czyści wyłącznie szkic czatu.
Inicjalizacja działa także po `ancore:content-loaded`, nie powiela listenerów
i zwalnia lokalne URL podglądów. Synchronizacja wzmianek na `submit` działa
w fazie capture, przed utworzeniem multipart `FormData`.

### Wzmianki i obserwowanie

Nagłówek szczegółów zadania i podzadania nie zawiera przycisku „Obserwuj”.
W szczegółach kart/podkart oraz w nagłówku otwartego projektu lub przestrzeni
Kanbana standardowy przycisk `btn-secondary btn-sm`
przełącza „Obserwuj” / „Obserwujesz”. `aria-pressed` odzwierciedla zapisany
stan. Błąd zachowuje stan i używa wspólnego komunikatu z możliwością ponowienia.

Podpowiedzi osób z bieżącego Workspace pojawiają się po wpisaniu `@` oraz
co najmniej jednej litery lub cyfry. Samo `@`, spacje lub znaki interpunkcyjne
nie otwierają listy. Usunięcie wyszukiwanej frazy ponownie ukrywa podpowiedzi.
Wybór wstawia `@Imię Nazwisko`. Lista pokazuje `Imię Nazwisko · e-mail`,
pozwalając rozróżnić osoby o tych samych nazwach; wyszukiwanie obejmuje nazwę
oraz adres e-mail. Przy braku imienia i nazwiska
używany jest login z pojedynczym `@`. Ukryte pole komentarza przechowuje ID
wybranej osoby i pozycję wzmianki. Dopisywanie tekstu przesuwa pozycje,
a edycja wewnątrz wzmianki lub jej usunięcie odłącza wybór. W takiej sytuacji
trzeba ponownie wybrać osobę z listy.
Wspólny wariant `tasks-mention-menu` korzysta z `tasks-filter-menu` i tokenów
menu; `tasks-issue-comment--mentions` pozwala pokazać listę poza ramką pola.
Strzałki wybierają osobę, Enter wstawia wzmiankę, Escape zamyka bez utraty treści.
Działa także wybór myszą. Pusta lista wyświetla komunikat, a nazwy są
wstawiane jako tekst. Dane osób są przekazywane przez bezpieczne `json_script`.
`collaboration.js` inicjalizuje UI także po `ancore:content-loaded` i usuwa
stare listenery przez `AbortController`. Centrum używa istniejących zakładek
z dodatkowymi filtrami „Wzmianki” i „Obserwowane”, w tym stanami pustymi.

## 14. Katalog Zasobów

Zasoby rozszerzają `core/base.html`, `tasks-topbar`, `tasks-filterbar`, wspólne
menu filtrów/sortowania i `directory_pagination_toolbar.html`. Lista używa
wspólnej tabeli Projektów (`tasks-directory-sheet tasks-project-sheet`) z wariantem
`resources-sheet`: wiersze 35px, separatory, nagłówki z ikonami, checkboxy
z podświetleniem zaznaczenia oraz menu działań po lewej. Dalej są numer ewidencyjny,
nazwa z ikoną typu, typ, status, osoba, lokalizacja i ważność/gwarancja.
Miniony termin korzysta ze wspólnego oznaczenia `tasks-project-value-badge--due-overdue`.
Menu wiersza używa `row-actions.js`, oferuje edycję i usunięcie z potwierdzeniem.
Zamknięcie edycji przywraca fokus do przycisku menu.

Pasek zawiera `directory_column_manager.html`, wspólny agregat „Filtruj”
i sortowanie z widoczną bieżącą opcją. `tasks.js` obsługuje szerokości,
kolejność i widoczność kolumn; Zasoby mają oddzielny klucz ustawień `resources`,
wspólny dla zwykłego i scoped URL. Checkbox nagłówka zaznacza bieżącą stronę,
a częściowy wybór pokazuje stan pośredni; nie uruchamia operacji zbiorczych.
Kolumny przewijają się poziomo także na telefonie, a pasek narzędzi zawija.
Pusty katalog i brak wyników mają osobne komunikaty i działające akcje.

`resources.css` ustala wariant siatki oraz dwukolumnowy układ formularza,
który przechodzi w jedną kolumnę na telefonie. Powłoka, pola i przyciski
pozostają wspólne (`tasks-modal app-modal-panel`, `documents-field`, `form-input`).
`resources.js` korzysta z `AncoreTaskModals`, ikon, custom selectów,
`showConfirmModal` oraz `AncoreApp.navigate`. Inicjalizuje się na pierwszym
wejściu i `ancore:content-loaded`, anulując poprzednie listenery i żądania.
Modal blokuje tło przez `inert`, zachowuje fokus, Escape i potwierdzenie
porzucenia zmian. Pobranie/zapis/usunięcie pokazują błędy umożliwiające ponowienie.

## 15. Pulpity

System „Pulpity” rozszerza Dashboard przez `dashboard/pulpits/base.html`,
wspólne paski, przyciski, `row-actions.js` i `AncoreCustomSelect`.
Katalog i zarządzanie współdzielą `dashboard/pulpits/directory.html`
oraz tabelę Przestrzeni w powłoce `work-page`:
`tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable
tasks-directory-menu-sheet tasks-spreadsheet-sheet work-space-sheet`.
Minimalny wariant `pulpit-directory-sheet` w `components/pulpits.css` określa
kolumny zaznaczenia, menu, nazwy, twórcy, widoczności, liczby gadżetów i opisu
oraz ikonę pulpitu 24px. Tabela dochodzi do krawędzi kontenera i zachowuje
wspólne wysokości wierszy, separatory, podświetlenia oraz przewijanie.
Nagłówek oraz toolbar mają 22px odstępu. Katalog nie ma zakładek
Wszystkie, Ulubione i Moje; pokazuje wszystkie dostępne pulpity.
Filtr widoczności i przycisk „Filtruj”
są po lewej, wyszukiwarka i paginacja po 30 pozycji po prawej.
Checkboxy zaznaczają wyłącznie bieżącą stronę, bez operacji zbiorczych.
`tasks.js` obsługuje zaznaczenie, stan częściowego wyboru i szerokości kolumn
z osobnym kluczem `pulpits-directory`, wspólnym dla zwykłego i scoped URL.
Menu z trzema paskami używa `directory_row_menu.html` oraz
`dashboard/pulpits/row_actions.html`; zawiera osobistą gwiazdkę i dotychczasowe
akcje według uprawnień. Nazwa otwiera pulpit. Opis jest osobną kolumną,
a pełne teksty są dostępne w `title`. Puste wyniki ukrywają nagłówki i pokazują
komunikat odpowiedni do filtrów lub pustego katalogu. Przegląd pulpitu nadal używa
`dashboard-overview` i gadżetów. Pozostałe warianty `pulpit-*` zachowują tokeny.
Puste stany katalogu i zarządzania używają `pulpit-directory-empty-state`:
kolorowej ilustracji 3D `static/img/empty-states/dashboard-empty.webp`
o maksymalnej szerokości 440px, wspólnego `tasks-empty-state__copy` oraz
opisów i akcji dla pustego katalogu lub filtrów. Ilustracja jest
dekoracyjna (`alt=""`), ma przezroczyste tło i skaluje się do szerokości
kontenera na telefonie. Przyciski zachowują `tasks-filter-button` bez
podkreślenia tekstu. Wiersze niepustej tabeli używają dotychczasowych ikon.

Jedyny gadżet „Postęp pracy” rozszerza `dashboard-panel` i współdzieli
`dashboard/includes/work_progress.html` z pulpitem domyślnym. Pokazuje procent,
„Zamknięte: X z Y”, wspólny `progress`, opis zakresu i pięć liczników
z istniejącymi kolorowymi `status-indicator`. Pusty zakres nadal pokazuje wszystkie
statusy z zerami, bez ilustracji zastępującej dane. Ikona wykresu jest po prawej
stronie nagłówka; uchwyt i menu występują wyłącznie w edytorze. Nagłówek pulpitu
pokazuje samą nazwę po lewej, a „Edytuj pulpit” (dla twórcy), odświeżenie i menu
edycji (dla twórcy) po prawej. „Kopiuj pulpit” jest usunięte ze wszystkich menu;
przegląd odbiorcy udostępnionego pulpitu nie pokazuje pustego menu działań.
„Edytuj pulpit” i „Odśwież” używają wspólnego
białego wariantu `tasks-tag-topbar-button--secondary` z delikatną ramką,
tak samo jak przyciski nagłówka edytora. Nawigacja i gwiazdki są dostępne w bocznym menu
oraz katalogu pulpitów. Pod nagłówkiem nie ma osobnego wiersza widoczności,
autora ani wyboru układu. Przegląd nie pokazuje uchwytów ani menu gadżetów,
także twórcy. „Edytuj pulpit” otwiera osobny edytor `gadgets.html` z menu
wybranego pulpitu po lewej: „Gadżety i układ”, „Dostępy” i „Ustawienia”.
Edytor ma w głównym nagłówku „Dodaj gadżet”, „Zmień układ” oraz „Gotowe”
(powrót do przeglądu). Wszystkie trzy używają wspólnego białego wariantu
`tasks-tag-topbar-button--secondary` z delikatną ramką. Pod nagłówkiem zaczyna się siatka gadżetów;
nie ma dodatkowego paska trybu edycji ani licznika. Komunikaty automatycznego
zapisu pozostają w regionie live dostępnym dla czytnika ekranu, a błędy są
widoczne nad siatką. Wariant `pulpit-layout-control` korzysta ze wspólnych
tokenów. „Zmień układ” otwiera wspólny popover
`row-actions.js` z pięcioma miniaturami i zaznaczeniem aktualnego układu.
Na telefonie przyciski nagłówka zawijają się,
a wszystkie kolumny wyświetlają się pionowo. Puste kolumny edytora mają
przerywaną ramkę, kolorową ilustrację 3D i podpowiedź przeciągania.
Widoczność zmienia się na stronie
„Dostępy”, otwieranej też przez menu akcji. Menu gadżetu
w edytorze zapewnia konfigurację, przeniesienie wyżej/niżej/do
następnej kolumny i usunięcie. Przeciąganie zaczyna się wyłącznie od uchwytu,
więc nie zakłóca linków i zaznaczania tekstu. Niedostępne kierunki przeniesienia
są wyłączone. Zapis aktualizuje żywy komunikat i blokuje kolejne zmiany oraz
wyjście do zakończenia żądania; błąd przywraca poprzednie pozycje i układ,
wartość selecta oraz pokazuje alert. Wspólny `canvas.html` zachowuje ten sam
odczyt danych w przeglądzie i edytorze.

Pozycje menu edytora i nagłówki gadżetów mają dekoracyjne ikony z `AncoreIcons`:
aplikacje dla układu, osoby dla dostępu, ustawienia dla konfiguracji
i `chart-no-axes-combined` dla „Postępu pracy”. `GadgetKindSelect` przekazuje te same ikony do
wspólnego dropdownu przez `data-ancore-option-icon`.
`pulpit-layout-preview` pokazuje miniaturę aktualnego układu kolumn i zmienia
ją razem z selectem, również przy przywracaniu układu po błędzie zapisu.
Include `dashboard/pulpits/layout_preview.html` jest wspólny dla menu
„Zmień układ” i pola „Układ” w tworzeniu pulpitu. `DashboardLayoutSelect`
przekazuje pięć miniatur przez `data-ancore-option-preview`; pole pokazuje
podgląd 32×23px przy wybranej wartości i 44×32px w wierszach listy o wysokości
48px. Lokalny limit wysokości menu 320px mieści pięć wariantów i wyszukiwarkę;
wspólna warstwa dropdownów ogranicza go do dostępnego miejsca na ekranie.
Pole zachowuje wyszukiwarkę, checkbox zaznaczenia i zapis natywnego selecta.
Formularz rodzaju gadżetu zawiera `pulpit-gadget-preview`: miniaturę z ikoną
oraz krótki opis, aktualizowane po wyborze rodzaju. Niedostępne źródło ma ikonę
kłódki i komunikat bez nazwy przestrzeni oraz liczników. Opisy oraz standardowa
walidacja formularza pozostają tekstowe.

Pusty pulpit używa wariantu `pulpit-empty-state` wspólnego `tasks-empty-state`:
kolorowa ilustracja `static/img/empty-states/dashboard-empty.webp` i opis
są wyśrodkowane w wolnej przestrzeni pod nagłówkiem. Przegląd kieruje do edycji.
Edytor pokazuje pustą siatkę z miejscem na
przeciągany gadżet i przyciskiem otwarcia katalogu w każdej kolumnie.
Każda pusta kolumna używa dekoracyjnej, przezroczystej ilustracji
`static/img/empty-states/gadget-column-empty.webp` o maksymalnej szerokości 240px.
Obraz przedstawia kolorowe kafelki gadżetów i wolne miejsce do ich dodania,
w tym samym stylu 3D co pusty pulpit. `canvas.html` udostępnia wzorzec `<template>`
z adresem wygenerowanym przez `{% static %}`; `pulpits.js` klonuje go po zmianie
układu i opróżnieniu kolumny oraz usuwa po dodaniu gadżetu. Obraz ma `alt=""`
i `draggable="false"`, więc przeciąganie nadal dotyczy uchwytów gadżetów.
Ilustracja przeglądu pulpitu ma przezroczyste tło i wspólne pole 440×330px,
tak jak puste katalogi Przestrzeni i Pulpitów. Skaluje się do dostępnej szerokości
i wraz z opisem jest wyśrodkowana w treści. Jest dekoracyjna (`alt=""`,
`draggable="false"`); stan opisuje polski tekst.
Typografia pustego pulpitu nawiązuje do wskazanego wzorca Jiry: nagłówek
28px/700 (24px na telefonie), opis 16px z interlinią 1,6 i odstępem 16px
od nagłówka. Używa wspólnego Atlassian Sans i koloru `--text-primary`.
Lokalna waga nagłówka nadpisuje globalne 400 wyłącznie w tym pustym stanie.
Siatka pustych kolumn pozostaje widoczna w edytorze po zmianie układu.
Przegląd pustego pulpitu zachowuje wyśrodkowaną ilustrację.
W trybie tylko do odczytu ilustracja pozostaje, a opis dotyczy twórcy pulpitu.

Tworzenie i gadżety używają standardowego `app-modal-panel--compact` i
`AncoreTaskModals`: fokus, Escape, inert tła, błędy zapisu, zachowanie szkicu
oraz potwierdzenie zamknięcia niezapisanych zmian. „Osoby z dostępem” jest
widoczne dla „Wybrane osoby”. Formularz gadżetu udostępnia wyłącznie
„Postęp pracy”, tytuł, przestrzeń i przypisanie; nie ma pól statusu,
grupowania ani limitu wyników. Podgląd rodzaju korzysta
z tego samego katalogu i miniatur co panel dodawania.
Porównywanie szkicu pomija token CSRF, który może się zmienić po błędzie walidacji.
Bezpośredni URL gadżetu otwiera to samo okno nad edytorem, pozostałe nad
katalogiem albo pulpitem;
zamknięcie przywraca adres ekranu tła. `pulpits.js` inicjalizuje się po pierwszym
ładowaniu i `ancore:content-loaded`, odłączając poprzednie listenery.
Utworzenie przechodzi do zapisanego pulpitu z aktualizacją adresu;
odświeżenie, konfiguracja i akcje zachowują częściową nawigację. Dodawanie,
konfiguracja i usuwanie gadżetu pozostają w edytorze, także z filtrami zarządzania.

Menu „Pulpity” wykorzystuje istniejący wariant nagłówka Przestrzeni, listy
`sidebar-space-list` i wiersze z `row-actions.js`. Ikona nagłówka zmienia się
na chevron przy hover/fokus; plus otwiera tworzenie pulpitu, menu oferuje
„Zarządzaj pulpitami”. Sekcje pokazują gwiazdki, ostatnie oraz przycisk
„Więcej pulpitów” z ikoną `align-left` i strzałką w prawo, jak „Więcej przestrzeni”.
Otwiera ten sam niemodalny panel z tytułem „Pulpity”, zamknięciem, polem
„Wyszukaj wszystkie pulpity” i linkiem „Wyświetl wszystkie pulpity”.
Wyszukiwanie po nazwie/opisie obejmuje dostępne pulpity aktywnego Workspace
i pokazuje do 20 wyników. Link zachowuje zapytanie i otwiera katalog pulpitów.
Przycisk podświetla się na szaro po otwarciu, bez zaznaczenia aktywnej strony.
„Pulpit domyślny” prowadzi do scoped `/dashboards/default/` osobistego pulpitu
aktywnego Workspace, bez duplikowania go w gwiazdkach i ostatnich twórcy.
Jest aktywny także na `/` oraz w przeglądzie własnego domyślnego rekordu po PK.
Grupy pulpitów i akcje przypisania są usunięte z katalogu, przeglądu, menu
bocznego oraz zarządzania.

`layout.js` synchronizuje zawartość sekcji po częściowej nawigacji, zachowując
stan zwinięcia i fokus. Zwinięte menu otwiera flyout z tymi samymi sekcjami,
unikalnymi ID i działającymi menu wierszy. Globalny `pulpit-navigation.js`
obsługuje osobistą gwiazdkę także poza modułem i po `ancore:content-loaded`,
odłączając listenery. Zapis tworzenia pulpitu i konfiguracji gadżetu aktualizuje menu.
Wspólny flyout ma nagłówek poza przewijanym obszarem,
aby linki i akcje pozostały dostępne również przy wielu pozycjach.

„Zarządzaj pulpitami” używa powłoki `work-page--management`, pasków
`tasks-topbar--directory`, `work-item-toolbar` i paginacji w toolbarze.
Lista używa tego samego include'a, klas i szerokości kolumn co „Pulpity”:
checkbox, menu z trzema paskami, Pulpit, Twórca, Widoczność, Gadżety i Opis.
Twórca jest tekstem, a osobista gwiazdka znajduje się w menu wiersza.
Filtry widoczności i gwiazdki pozostają po lewej, wyszukiwarka i paginacja po prawej.
Checkboxy zaznaczają tylko bieżącą stronę, bez operacji zbiorczych.
Klasa `pulpit-management-sheet` wybiera osobny klucz `pulpits-management`
w `tasks.js`; nie nadpisuje wspólnej siatki `pulpit-directory-sheet`.
Preferencje szerokości pozostają wspólne dla zwykłego i scoped adresu zarządzania,
niezależne od katalogu. Nazwa otwiera edytor gadżetów,
„Utwórz pulpit” modal nad katalogiem. Anulowanie i zapis edycji wracają
do tego katalogu z jego filtrami; błąd pozostaje na stronie edycji.
Tworzenie i usunięcie zachowują katalog oraz filtry. Filtry widoczności
i gwiazdki wysyłają formularz także po wyborze wartości.

Katalog zarządzania pulpitami pokazuje własne minimalne menu przez
`core/includes/management_sidebar.html`: „Wróć do ustawień” i aktywne „Pulpity”.
Powrót prowadzi do Ustawień (`#workspace`), również po usunięciu pulpitu.
Wewnętrzny tryb `pulpits-management` pozostaje osobny od edytora pulpitu
oraz zarządzania Workspace. Wspólny `layout.js` synchronizuje aktywność
i widoczność menu przy częściowej nawigacji, reload i Wstecz/Dalej.

Edytor konkretnego pulpitu ma osobny tryb `pulpit-editor` i menu
`core/includes/pulpit_editor_sidebar.html`. Pokazuje nazwę pulpitu, powrót oraz
„Gadżety i układ”, „Dostępy” i „Ustawienia”; wyłącznie bieżąca sekcja jest aktywna.
Nie ma poziomych zakładek. Po wejściu z katalogu menu ogólnego zarządzania jest
ukryte. `layout.js` podmienia zawartość menu również przy zmianie pulpitu,
zachowując fokus i kontekst powrotu. Menu używa istniejących klas sidebaru,
ikon i obsługi na telefonie oraz po zwinięciu.

Ustawienia i dostępy (`dashboard/pulpits/edit.html`) są osobnymi stronami,
także przy bezpośrednim wejściu przez zwykły/scoped URL oraz wariant zarządzania.
Używają powłoki `work-page--management` i menu wybranego pulpitu. Linki w katalogu,
menu akcji i bocznej nawigacji korzystają ze wspólnej częściowej nawigacji.
Nagłówek zawiera nazwę sekcji i pulpitu oraz „Wyświetl pulpit”. Ustawienia
zawierają nazwę/opis, dostępy widoczność/osoby. Pola mają maksymalną szerokość 640px,
odstęp 22px od krawędzi oraz wspólne przyciski „Anuluj” i „Zapisz”.
Include `dashboard/pulpits/fields.html` współdzieli pola i błędy z modalami.
Zapis przez POST wraca do pulpitu albo katalogu zarządzania z jego filtrami;
błąd pozostaje na stronie ze szkicem i fokusem nieprawidłowego pola.
Pole „Widoczność” w tworzeniu pulpitu i na stronie „Dostępy” używa
`DashboardVisibilitySelect` oraz istniejącego `data-ancore-option-icon`:
`lock` dla „Prywatny”, `users` dla „Wybrane osoby” i `building-2` dla
„Cały Workspace”. Wspólny select pokazuje dekoracyjną ikonę w liście
oraz przy wybranej wartości, zachowując checkbox zaznaczenia i wyszukiwarkę.
„Osoby z dostępem” pojawiają się po wyborze „Wybrane osoby”. `pulpits.js`
chroni niezapisane zmiany przy nawigacji i zamykaniu/przeładowaniu karty,
a po `ancore:content-loaded` odłącza poprzednie listenery.


Panel katalogu gadżetów (`catalog.html`) jest dokowany po prawej stronie
edytora, ma niezależne przewijanie, wyszukiwarkę ignorującą wielkość liter
oraz polskie znaki, kategorię Statystyki i stan bez wyników. Katalog oraz
liczniki „Wszystkie”/„Statystyki” obejmują wyłącznie jeden rodzaj „Postęp pracy”.
Miniatury `catalog_preview.html` korzystają z istniejących ikon i tokenów,
a przyciski z klas wspólnych kontrolek. `pulpit-editor-body` rozszerza powłokę
Dashboardu bez zmian na innych ekranach. Na telefonie katalog pojawia się
nad siatką i ma ograniczoną wysokość z przewijaną listą. Przy średniej szerokości
otwarty katalog układa gadżety pionowo, zachowując zapisane kolumny.
Escape i zamknięcie katalogu przywracają fokus do przycisku otwarcia;
otwarcie skupia wyszukiwarkę. Stan otwarcia i filtrów jest zapamiętywany
w `sessionStorage` osobno dla adresu edytora, również po konfiguracji i reload.

„Dodaj” zapisuje gadżet z domyślnymi filtrami i dołącza go do najmniej
zapełnionej zapisanej kolumny bez nawigacji i zamykania katalogu. Formularz
„Konfiguruj” służy do dopasowania źródła i filtrów. Bez JS link nagłówka nadal
otwiera standardowy formularz dodawania. W trakcie żądania dodawanie, zmiana
układu i wyjście są blokowane. Osiągnięcie limitu 24 wyłącza przyciski katalogu
oraz pokazuje opis. Błąd sieci i konflikt rewizji wyświetlają alert bez dokładania
pozornego gadżetu; przy niepewnym wyniku żądania należy odświeżyć pulpit.
Po zakończeniu dodawania przycisk odzyskuje fokus utracony podczas blokady,
również po błędzie; przy osiągnięciu limitu fokus przechodzi do zamknięcia katalogu.
Nowe menu gadżetów inicjalizują się przez `ancore:modals-loaded`.
