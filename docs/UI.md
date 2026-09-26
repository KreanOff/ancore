# Standard UI Ancore

## 1. Cel i punkt odniesienia

Nowe funkcje mają wyglądać i zachowywać się jak część obecnego Ancore.
Punktem odniesienia są istniejące ekrany i komponenty opisane poniżej.

Akcja „Zapisz jako szablon” znajduje się w menu „Więcej opcji” listy projektów.
Jest aktywna po zaznaczeniu dokładnie jednego projektu, którym można zarządzać.
Szablony projektów używają standardowego okna „Nowy projekt” z dodatkowym
wyborem szablonu. Po wyborze ukryte i wyłączone są pola pierwszej grupy,
ponieważ grupy pochodzą ze snapshotu. Katalog szablonów korzysta ze wspólnych
dwóch pasków katalogu, zarządzania kolumnami, filtra opisu, sortowania,
wyszukiwania oraz `directory_pagination_toolbar.html` (25/50/100 pozycji).
Wariant tabeli `tasks-template-sheet` zachowuje wiersze 35px, separatory
i przewijanie katalogu projektów. Kolumny obejmują osobno nazwę szablonu
i nazwę projektu, opis, liczbę grup, liczbę zadań z podzadaniami i datę utworzenia.
Nazwa szablonu w tabeli jest zwykłym tekstem, bez ołówka i akcji edycji.
Pełna nazwa jest dostępna w `title` komórki. Pierwsza kolumna
zawiera przycisk z trzema paskami, korzystający z klas menu Dokumentów
oraz wspólnego `row-actions.js`. Menu udostępnia edycję szablonu, utworzenie
projektu i usunięcie z potwierdzeniem `showConfirmModal`.
Nazwa projektu otwiera standardowe okno tworzenia z wybranym szablonem.
Delegacja w `project-templates.js` obsługuje również częściową nawigację,
a wybór w `tasks.js` jest inicjalizowany z resztą ekranu.
Reguła `#project-create-form .tasks-project-create-fields > label.u-hidden`
zapewnia ukrycie pól mimo późniejszych reguł układu etykiet.

Katalog szablonów jest zwykłą stroną z pełną tabelą, paskiem tytułu
oraz strzałką powrotu do projektów. „Edytuj szablon” jest przyciskiem w menu
wiersza. Otwiera modal nad tą tabelą, bez zmiany adresu i historii przeglądarki,
tak jak edycja projektu. Powłoka `tasks-modal app-modal-panel`
(`template-page-panel`) zachowuje animację od dołu, nagłówek, przewijaną białą
treść i stałą stopkę. Krzyżyk, „Zamknij” i Escape zamykają okno lokalnie.
Nazwa w tabeli pozostaje zwykłym tekstem, bez skrótu do edycji.

`project-templates.js` pobiera formularze do `data-project-template-modal-host`
i zapisuje je przez fetch. Endpoint `/tasks/templates/<id>/edit/` oraz scoped
odpowiednik zwracają JSON z HTML modala dla `X-Template-Modal: true`.
Zwykłe wejście pod dawny adres edytora przekierowuje do katalogu.
Po zapisie okno pozostaje otwarte; zamknięcie odświeża tabelę z bieżącymi
parametrami wyszukiwania, sortowania i paginacji, bez nowego wpisu w historii.
Błąd pobrania pozostawia katalog, a błąd zapisu zachowuje pola i daje możliwość
ponowienia. Nazwa szablonu, nazwa projektu i opis są polami głównego formularza.

Moduł korzysta ze wspólnego `AncoreTaskModals.open/close` w `tasks.js`.
Delegowane zamykanie działa także dla doładowanych okien. Zdarzenia
`ancore:task-modal-opened`, anulowalne `ancore:task-modal-before-close` i
`ancore:task-modal-closed` pozwalają modułowi obsłużyć `inert`, niezapisane dane
i powrót fokusu. `ancore:modals-loaded` inicjalizuje wspólne menu wierszy
po wymianie formularzy; ikony i selecty odświeżają istniejące API.
Inicjalizacja po `ancore:content-loaded` anuluje wcześniejsze listenery i żądania.

Edytor ma zakładki „Grupy” i „Zadania” bez liczników,
korzystające z `notifications-tabs`: aktywną pozycję oznacza turkusowe podkreślenie.
Widoczna jest jedna tabela i odpowiadający jej przycisk dodawania po prawej stronie.
Domyślnie otwierają się „Grupy”; zapis lub błąd zachowuje wybraną zakładkę.
Przełączenie nie usuwa niezapisanych danych głównego formularza.
`tablist`/`tab`/`tabpanel` łączą zakładki z treścią; strzałki, Home i End
przełączają widok oraz fokus. Obsługa działa także po częściowej nawigacji.
Wspólny styl `notifications-tabs` obsługuje zarówno `aria-pressed` filtrów,
jak i `aria-selected` zakładek.

Wariant `project-template-editor` zawiera tabele `documents-table` zgodne z listą
Dokumentów: wspólne nagłówki, tekst 13px/400, separatory, szare podświetlenie
oraz odstępy 24px od obu krawędzi. Pole nazwy ma minimum 32px wysokości,
jak pole ikony Dokumentów. Długie nazwy, opisy i powiązania pozostają w jednym
wierszu z wielokropkiem i pełną treścią w `title`; nie zwiększają wysokości wierszy.
Ostatnia kolumna ma 120px i wyrównanie do prawej. Tabele zachowują
wszystkie kolumny i własne przewijanie poziome na wąskich ekranach.
Menu grup i zadań otwierają formularze we wspólnej powłoce. Tabela katalogu i nawigacja
są `inert` podczas edycji, a przy otwartym formularzu podrzędnym także główne
okno edytora. Tab i Escape dotyczą ostatniego otwartego modala. Zamknięcie
przywraca fokus do przycisku otwierającego. Każda operacja zapisuje się osobno.
Niezapisane nazwy/opis wymagają potwierdzenia przy zamykaniu całego edytora;
pozostają wpisane po zapisie lub usunięciu elementu struktury. Błędy walidacji
pozostają we właściwym formularzu; nowy formularz zeruje poprzedni wpis.
Usuwanie grupy lub zadania używa `showConfirmModal` z informacją o podzadaniach.
Puste tabele ukrywają nagłówki; dodanie zadania wymaga wcześniejszego dodania grupy.

Kalendarz ma filtr rodzaju pozycji, zachowuje dotychczasowe kolory i widoki.
Terminy mają etykiety „Zadanie”, „Podzadanie”, „Karta” lub „Podkarta” oraz
otwierają źródłowe szczegóły. Liczniki obejmują „pozycje”. Centrum powiadomień
ma zakładkę „Przypomnienia”, używającą istniejących stanów odczytu i archiwum.
Ten dokument utrwala aktualny styl; zmiana całego stylu wymaga zadania
obejmującego redesign.

Pierwszy opis powstał z przeglądu szablonów, CSS i JS. Nie jest pomiarem
wszystkich końcowych stylów w przeglądarce. Przed zmianą wizualną obejrzyj
referencyjny ekran w tej samej szerokości i stanie co ekran zmieniany.

## 2. Powłoka aplikacji

Źródło: [core/base.html](../core/templates/core/base.html).

- Stała nawigacja z przełącznikiem Workspace, modułami, ulubionymi i profilem.
- Stan zwinięty/rozwinięty i regulowana szerokość sidebaru.
- Biały obszar treści w `.main-content > .page-container`.
- Na ekranach katalogów `full-width`, pasek tytułu, akcje, filtry, wyszukiwanie,
  paginacja i przewijana lista.
- Osobny host `#app-page-modals` oraz komunikaty `#app-notifications`.
- Wspólne panele wyszukiwania i powiadomień oraz Sticker.

Globalne wyszukiwanie pokazuje najwyżej 20 wyników w każdej kategorii danych.
Jeśli dopasowań jest więcej, istniejący licznik kategorii pokazuje „20+”,
a pod wynikami pojawia się prośba o doprecyzowanie frazy. Komunikat czytnika
ekranu podaje wtedy liczbę pokazanych wyników, nie całkowitą liczbę dopasowań.
Wygląd panelu, obsługa klawiatury i stany pusty/błąd pozostają wspólne.

Sticker zachowuje wygląd i kontrolki, ale zapisuje treść oraz geometrię osobno
dla zalogowanego konta. Po przełączeniu konta pojawia się jego własna notatka
(pusta przy pierwszym użyciu); powrót przywraca poprzednią. Dane starej notatki
bez właściciela nie są automatycznie przypisywane ani wyświetlane innemu kontu.
Powtórna inicjalizacja po nawigacji nie powiela obsługi przycisku.

Przełącznik Workspace w nagłówku pokazuje avatar i nazwę bez strzałki.
Kliknięcie avatara lub nazwy nadal otwiera menu wyboru Workspace.

Aktywna ikona w przełączniku domu, powiadomień i wyszukiwania używa
`color-mix(in srgb, var(--system-accent) 15%, #ffffff)`, także przy zwiniętym
sidebarze.

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
base/variables.css
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
| Font aplikacji | `Inter`, fallback systemowy |
| Mały/podstawowy/większy tekst | `--font-size-sm: 13px`, `--font-size-base: 14px`, `--font-size-lg: 15px` |
| Zwykły tekst | `--text-primary: #40444C` |
| Tekst na akcencie | `--text-inverse: #FFFFFF` |
| Główny akcent | `--system-accent: rgb(30, 191, 191)` |
| Interakcje | `--system-interaction: #6f7580`, miękkie tło z alfa 0.1 |
| Główna powierzchnia | `--bg-main: #ffffff`, `--card-bg: #ffffff` |
| Nawigacja pomocnicza | `--secondary-menu-bg: #FBFBFC` |
| Tło panelu | `--panel-bg: #f7f6f4` |
| Delikatna ramka | `--border-color: #ece9e5` |
| Standardowa kontrolka | `--control-height: 32px` |
| Dropdown | kontrolka 36px, radius 6px; menu radius 7px, element 32px |
| Checkbox | `--checkbox-size: 18px` |
| Standardowe zaokrąglenie | `--radius: var(--radius-max)`, bazowo 8px |
| Pasek narzędzi | `--toolbar-height: 52px` |
| Sidebar | bazowo 272px; zwinięty 64px; JS pozwala regulować 220–420px |
| Skala UI | `--app-ui-scale: 0.98`, stosowana przez `zoom` w resecie |

Ważne wyjątki:

- `--text-muted`, `--text-main`, `--text-strong` są aliasami tej samej podstawowej
  barwy. Nazwa „muted” nie upoważnia do wprowadzania nowego jasnoszarego tekstu.
- `--accent-red`, `--accent-blue`, `--accent-peach` są historycznymi aliasami;
  ich rzeczywisty kolor może być turkusowy.
- Globalne reguły w `style.css` wymuszają wagę tekstu 400 w szerokim zakresie,
  także dla wielu nagłówków i `strong`. Nie dodawaj lokalnych boldów jako
  domyślnego sposobu wyróżniania nowego ekranu.
- Kolory statusów, tagów, avatarów i progów terminu mają osobne znaczenie
  i często pochodzą z danych. Zachowuj te wyjątki.
- Nie ma jednej uniwersalnej skali spacingu dla całej historycznej bazy.
  Odstępy bierz z właściwego istniejącego komponentu; dla modali z tokenów powłoki.

## 5. Referencje komponentów

| Element | Wzorzec do ponownego użycia | Styl / zachowanie |
| --- | --- | --- |
| Katalog projektów/grup/tagów | [tasks/tasks.html](../tasks/templates/tasks/tasks.html) | `components/tasks.css`, `tasks.js` |
| Lista kontaktów i firm | [contacts.html](../contacts/templates/contacts/contacts.html), [companies.html](../contacts/templates/contacts/companies.html) | `contacts.css` + wspólne style katalogu |
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

Przyciski notatek projektów i grup w Zadaniach oraz przestrzeni w Kanbanie
używają wspólnego stanu `.tasks-project-sheet__notes-button.has-notes`.
Gdy istnieje wpis, tylko ikona ma ciepły, wyrazisty żółty kolor `#d4a000`.
Tło i stany interakcji przycisku pozostają standardowe.
Pusty stan zachowuje szarą ikonę kartki z plusem. Stan wynika z istniejących
notatek, także po zapisie i ponownym wejściu.

### Paski listy grup

Lista grup otwartego projektu używa tych samych dwóch pasków co „Wszystkie
grupy”: `tasks-topbar--directory` z tytułem i akcjami oraz
`tasks-filterbar--directory` z kolumnami, „Filtruj”, „Sortuj”, wyszukiwaniem
i wspólnym `directory_pagination_toolbar.html`. Projekt zachowuje nazwę
i strzałkę powrotu. Paginacja występuje wyłącznie w drugim pasku.
Filtry i sortowanie używają wspólnego mechanizmu grup; wewnątrz projektu
nie ma dodatkowego wyboru projektu w filtrach. Czyszczenie filtrów,
wyszukiwanie i zmiana strony zachowują otwarty projekt oraz Workspace.
Na telefonie nagłówek projektu pozostawia miejsce po lewej na przycisk
nawigacji aplikacji, aby strzałka powrotu pozostała dostępna.

### Limit zadań według stanu

„Wszystkie zadania” i „Moje zadania” używają wspólnego paska paginacji.
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
Typ rozróżnia wyłącznie lewa ramka 3px: turkus `--system-accent` dla sukcesu
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
Po najechaniu na aktywny przycisk udział turkusu rośnie do 24%, z przejściem
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
jasny turkus przechodzi po najechaniu w mocniejszy turkus, z ciemnym tekstem.
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

`documents.css` zachowuje semantyczne tabele dysków i plików, dopasowane do
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
Wiersze dysków mają minimum 44px wysokości, a odstęp między ikoną i nazwą
wynosi 8px (10px w zwężonej liście).

Formularz tworzenia i ustawień dysku zawiera nazwę, kolor ikony i opis.
Tworzenie oraz edycja folderów Dysku zawierają nazwę i kolor.
Przycisk ołówka ma etykietę „Edytuj folder”. Wspólny include
`documents/includes/color_field.html` używa natywnego pola `type="color"`
z istniejącą klasą `tasks-project-option-color`, podglądu SVG 64×64px
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
katalogów. Skrajne komórki listy dysków mają symetryczne odstępy od krawędzi tabeli:
24px na komputerze i 20px na telefonie, również w nagłówku i przy węższej tabeli.
Na komputerze lewy odstęp jest taki sam jak na liście plików.

Lista dysków ma trzy kolumny danych: „Nazwa”, „Zmodyfikowano”, „Rozmiar”,
z osobnym polem przycisków działań. Lista folderów i plików Dysku pokazuje
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
ze strzałką otwiera dysk. Przy szerokości obszaru listy do 740px (container
query, także przy rozwiniętej nawigacji aplikacji na tablecie) nazwa zawija się.
Na wąskich ekranach tabela przewija się poziomo, zachowując wszystkie
trzy kolumny danych (minimalna szerokość 620px).
Ustawienia i usunięcie pustego dysku pozostają oddzielnymi kontrolkami.
Pusty wynik ma bezpośrednią akcję wyczyszczenia wyszukiwania i filtrów.

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
(`root`), bez przeciągania wierszy i kafelków między lokalizacjami. Prawidłowy cel podświetla się istniejącym turkusem
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
tabelę i kafelki Dysku. Na pasku narzędzi, po prawej stronie sortowania,
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

Lista Dokumentów używa tych samych odstępów co lista plików Dysku: 24px
od lewej i prawej krawędzi tabeli, także na telefonie oraz w nagłówku.
Przycisk menu działań jest po lewej stronie ikony pliku. Dokumenty mają jeden
płaski katalog, bez folderów, ścieżki lokalizacji i akcji „Przenieś”. Include
`documents/office/actions.html` obsługuje gwiazdkę, edycję, pobieranie oraz kosz;
na kafelkach te same akcje otwiera przycisk z trzema paskami w stopce.
Pusty widok gwiazdek dotyczy dokumentów.
Pusty stan zachowuje własne odstępy i wyśrodkowanie.
Lista pokazuje trzy kolumny: „Nazwa”, „Zmodyfikowano” i „Rozmiar”, bez kolumny
„Tagi”. Oba katalogi mają tę samą minimalną szerokość tabeli z menu (690px).
Tagi nie są dostępne w kafelkach, filtrach, oknie „Dane dokumentu” ani
starszym edytorze tekstu. Aktywne filtry pozostałych pól mają nad listą akcję
czyszczenia i pozostają przy wyszukiwaniu, sortowaniu, paginacji, zmianie
układu oraz akcjach gwiazdki/kosza.

Oba katalogi korzystają z jednego odstępu bocznego siatki
(`--documents-index-padding-x` na `.documents-page`). Nagłówki tabel Dysków,
plików Dysku i Dokumentów są tekstowe, bez ikon. Lista Dokumentów nie pokazuje historycznej lokalizacji w folderach.
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

Na listach plików Dysku i Dokumentów oraz folderów Dysku akcje wiersza otwiera
jeden przycisk z ikoną `menu`
(trzy poziome paski), po lewej stronie ikony pliku lub folderu. Nie ma osobnej
kolumny działań; pusty stan ukrywa nagłówki i mieści się na wąskim ekranie.
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

`dashboard/home.html` rozszerza `core/base.html` i używa `tasks-topbar`,
istniejących `dashboard-stat`, `dashboard-panel`, ikon statusów oraz include'a
priorytetu. Wariant `.dashboard-overview` w `components/dashboard.css` ogranicza
lokalne zmiany do układu pulpitu: cztery liczniki, dwie kolumny paneli,
natywne paski `progress` i zwarte wiersze linków. Używa tokenów Ancore;
turkus wyróżnia aktywną listę i postęp. Na węższych ekranach panele tworzą
jedną kolumnę, liczniki dwie. Treść przewija się w `.dashboard-main`.

Zakładki są linkami GET z `aria-current`, obsługiwanymi również przez wspólną
częściową nawigację. Dashboard nie wymaga osobnego JavaScriptu. Puste stany
prowadzą do odpowiedniego modułu; pełne nazwy pozostają w tekście i `title`.

## 6. Modale

Zakładka „Główna” szczegółów zadania i podzadania nie pokazuje „Powodu blokady”,
dawnych kontrolek „Czasu pracy”, „Szacowanego czasu” ani bocznej „Historii statusu”. Modal tworzenia
zadania również nie zawiera powodu blokady ani szacowanego czasu; zachowuje
termin wykonania i przypomnienie. Edytor szablonów projektów nie
pokazuje pola szacowanego czasu ani kolumny „Czas (min)”. Zmiany statusu są nadal
widoczne w zakładce „Historia”.
Wspólne style czasu pracy i historii są nadal używane przez Kanban.

Zakładki „Główna”, „Podzadania”, „Dziennik pracy” i „Historia” (`tasks-issue-tabbar`) znajdują się
w lewej kolumnie szczegółów (`tasks-issue-primary`), bezpośrednio nad tematem
zadania i są wyrównane do jego lewej krawędzi, także na telefonie.
Pasek zakładek i ich treść mają po 50px odstępu od obu krawędzi lewej kolumny
(`--tasks-issue-content-padding-x`), także na telefonie. Treść wykorzystuje całą
pozostałą szerokość bez limitu 980px; wariant dotyczy zadań i podzadań.
Korzystają z `notifications-tabs`, z turkusowym podkreśleniem. Tekst zakładek
ma rozmiar `--font-size-lg` (15px); wariant jest ograniczony do szczegółów
zadania i podzadania. Edytowalny tytuł w treści tych widoków ma 20px,
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
nagłówki z ikonami, separatory oraz turkusowe podświetlenie z paskiem po lewej.
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
rogi i ten sam turkusowy hover/fokus co akcje projektów. Wrapper menu rozciąga
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

Panel zajmuje prawą część ekranu od 24px pod górną krawędzią do dołu.
Po lewej pozostaje `clamp(64px, 13.5vw, 280px)` kontekstu aplikacji, po prawej
16px. Jasnoszara powierzchnia używa `--secondary-menu-bg` (`#FBFBFC`),
tego samego tokenu co boczny pasek nawigacji; wewnątrz jest biała,
przewijana treść `--card-bg` z odstępami 24px.
Nagłówek ma 72px i tytuł 20px/400, stopka minimum 68px i akcje po lewej.
Oba paski pozostają poza przewijaną treścią. Przycisk zamknięcia, turkusowe
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
ma 40px odstępu po lewej, a do 600px wypełnia ekran, z odstępami treści 12px,
większą stopką przy zawijaniu akcji i uwzględnieniem bezpiecznego obszaru ekranu.
Dane kontaktowe mają dwie kolumny, a do 600px jedną; ID Ancore zajmuje pełny wiersz.

Okna „Informacje” oraz „Notatki” projektów, grup i tagów w Zadaniach oraz
przestrzeni i tagów w Kanbanie również używają `app-modal-panel`.
Wspólny `project_info_modal.html` zachowuje podsumowanie i siatkę danych.
Notatki zachowują formularz i listę wpisów; cała biała treść przewija się razem,
bez osobnego przewijania listy. Okna mają stałą stopkę „Zamknij” oraz
dotychczasowe zamykanie krzyżykiem i Escape, fokus i obsługę zapisu.

Potwierdzenia, okna zespołu, kadrowanie zdjęć i podglądy plików zachowują
swoje dotychczasowe powłoki.
Poniższe tokeny opisują bazowy, kompaktowy wariant; nie wyznaczają wysokości
i szerokości formularza z `app-modal-panel`.

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

Nagłówki i stopki kompaktowych okien aplikacji mają po 50px wysokości CSS,
również na telefonie. Wariant panelu formularza ma wymiary opisane powyżej.
Paski nie kurczą się przy przewijaniu treści.
Na ekranach do 600px stopka może zwiększyć wysokość i zawinąć akcje,
aby ich etykiety pozostały dostępne. Podgląd plików zachowuje pojedynczy rząd.

Kompaktowy nagłówek używa tekstu 15px/400 oraz wspólnego przycisku zamknięcia 34px
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
Szerokość listy jest równa aktualnej szerokości otwierającej ją kontrolki,
także po zmianie rozmiaru okna. Stałe szerokości poszczególnych menu nie
nadpisują tej zasady; jedynym ograniczeniem jest widoczna szerokość ekranu.
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
Warstwa obejmuje `AncoreCustomSelect`, priorytety/statusy/tagi oraz wybór projektu
i grupy w zadaniach, listy firm/osób, Kontaktów, Kalendarza i Profilu,
również w szczegółach zadań/Kanbana. Ta sama zasada obowiązuje w listach
filtrów i prostego sortowania, warunkach tekstowych w panelach filtrów
(także Dysku i Dokumentów), wyborze liczby wierszy we wszystkich katalogach
i Workspace oraz filtrze aktywności zadania/karty. Lista filtra w zbiorczym
panelu otwiera się ponad panelem i zachowuje szerokość kontrolki bez zmiany
układu pozostałych pól. Wielopolowe panele konfiguracji filtrów/sortowania
oraz menu działań przy przyciskach ikonowych zachowują własną szerokość;
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

Oczekujące zaproszenia odbiorcy są widoczne w istniejącym panelu powiadomień,
przed aktywnością zadań. Karta podaje autora, Workspace, rolę, termin i przycisk
„Przyjmij lub odrzuć zaproszenie”. Dzwonek pokazuje jasnoturkusowy licznik oczekujących
zaproszeń `notifications-toggle__invitation-count` (do 9, potem „9+”). Pełna liczba
jest dostępna w opisie i podpowiedzi. Tło licznika używa `--primary-button-bg`,
tak jak liczniki zakładek powiadomień, a tekst `--text-primary`.
Gdy nie ma zaproszeń, nieprzeczytane wpisy
sygnalizuje kropka `notifications-toggle__indicator`. Opis czytnika ekranu
rozróżnia obie liczby. Znaczniki zaproszeń są renderowane także przed uruchomieniem JS.

Link powiadomienia `?invitation=<pk>` otwiera okno konkretnego zaproszenia na
stronie Workspace. Przycisk „Otwórz” przy otrzymanym zaproszeniu otwiera to samo okno.
Include `workplaces/includes/invitation_response_modal.html` korzysta z
`tasks-modal`, standardowej stopki i kompaktowej listy szczegółów
`workplace-invitation__details`. Akcje „Później”, „Odrzuć” i „Przyjmij” są razem
w stopce; wspólne przyciski paginacji pozwalają przejść do innych zaproszeń.
`workplace-team.js` obsługuje ten modal także na stronie Workspace przez
`data-team-modal-page`, zachowując inert, fokus i inicjalizację po częściowej
nawigacji. Zamknięcie usuwa parametr zaproszenia z adresu i przywraca fokus
przyciskowi w wierszu lub zakładce „Zaproszenia”. Formularz nadal wymaga POST i CSRF.

Ekran `/workplaces/` rozszerza `core/base.html` i ma sekcje „Workspace”,
„Członkowie” oraz „Zaproszenia”. Przełącznik używa `documents-display-switch`
i standardowych linków `tasks-filter-button` z ikonami i `aria-current="page"`.
Aktywna opcja ma klasę `is-active` i wspólne szare tło kontrolek katalogu.
Licznik przy zaproszeniach używa `tasks-project-query-count` i oznacza
otrzymane zaproszenia. Pasek ma odstępy, przyciski i menu takie jak Dokumenty.
Serwer renderuje jedną listę, zamiast łączyć katalog i skład zespołu pionowo.
Każda zakładka ma dwa wspólne paski katalogu, jak Dokumenty i Projekty:
`tasks-topbar--directory` z tytułem i akcjami oraz `tasks-filterbar--directory`
(`management_toolbar.html`) z zakładkami i kontrolkami bieżącego widoku.
„Ustawienia” i „Zaproś osobę” znajdują się w nagłówku członków i wysłanych
zaproszeń. Wybór Workspace/rodzaju zaproszeń i licznik są obok zakładek.
W katalogu wyszukiwanie i kompaktowa paginacja znajdują się po prawej stronie
drugiego paska. Paginacja używa wspólnych klas `tasks-project-pagination--toolbar`,
zachowując filtrowanie i zmianę strony w przeglądarce; zakres i liczba wyników
zastępują osobny dolny pasek z numerami stron. Pod paskami zaczyna się tabela.

„Workspace” pokazuje pełną listę, wyszukiwanie, dodawanie, ustawienia i paginację.
Znacznik „Bieżący” wskazuje aktywną przestrzeń. Nazwa i liczba członków otwierają
zakładkę „Członkowie”. Ikony przełączania i edycji w tabeli używają podświetlenia
całej komórki, tak jak ikony projektów: `rgba(var(--system-accent-rgb), 0.24)`
na delikatnym turkusowym tle wiersza. Hover i fokus klawiatury zachowują
siatkę tabeli, bez dodatkowego obrysu i cienia. Komórki ikon mają jedną
kolumnę `minmax(0, 1fr)`, aby przycisk wypełniał ich szerokość. Wyłączone akcje (bieżący
Workspace lub brak uprawnień do edycji) nie otrzymują tego podświetlenia.
`team_panel.html` renderuje tabelę składu lub wysłanych
zaproszeń; listę wyboru Workspace i licznik zapewnia wspólny drugi pasek.
`invitation_filter.html` rozdziela „Otrzymane” i „Wysłane”; `received_invitations.html`
pokazuje Workspace, zapraszającego, rolę, datę i akcję „Otwórz”.
Wybory Workspace i rodzaju zaproszeń używają `documents-view-selector`,
`tasks-project-query-trigger` i menu `documents-item-menu`, tak jak wybór
widoku Dokumentów. Wspólny `row-actions.js` obsługuje popover, strzałki,
Escape i fokus; linki korzystają z nawigacji aplikacji. Menu wysłanych zaproszeń
zawiera tylko Workspace, którymi użytkownik może zarządzać. Inicjalizacja po
`ancore:content-loaded` usuwa stare listenery przez `AbortController`.

Pasek filtrów zachowuje wysokość wiersza z polem wyszukiwania Dokumentów
(`--dropdown-control-height` plus wspólny padding i ramka) oraz zawijanie
na telefonie. Nazwa w przycisku wyboru używa ograniczenia 180px ze wspólnego
`documents-view-selector`; pełna nazwa jest w opisie przycisku i menu.
`team_modals.html` dostarcza istniejące okna zaproszenia
i roli. Przełączenie zakładki lub wyboru Workspace nie zmienia aktywnej
przestrzeni pracy. Ustawienia wracają po zapisie do właściwej zakładki.
Tabela używa bezpośrednio
`documents-table` i `documents-name` z katalogu Dokumentów. Nagłówki mają 35px,
wiersze 36px, tekst 13px/400, białe tło i cienką siatkę kolumn. Kolumny to
„Nazwa”, „E-mail”, „Rola” i „Dołączono” (w zaproszeniach „Ważne do”). Nazwa
z avatarem mieści się w jednym wierszu; długie wartości mają ellipsis i pełny
tekst w `title`. Na telefonie pozostaje tabela przewijana poziomo we własnym
kontenerze, bez zmiany wierszy na karty.
Pusta tabela na telefonie dopasowuje się do szerokości ekranu i pomija
nagłówki kolumn, aby komunikat o braku członków lub zaproszeń był widoczny w całości.

Parametr `view=invitations` wybiera wysłane zaproszenia;
po wysłaniu lub anulowaniu zaproszenia użytkownik wraca do tej listy.

Menu trzech pasków przed avatarem korzysta z tych samych klas i zachowania
co lista Dokumentów. Wspólny `row-actions.js`, ładowany w `core/base.html`,
obsługuje zarówno `data-document-actions`, jak i `data-row-actions`. Zachowuje
popover, pozycjonowanie względem viewportu i skali UI, obsługę klawiatury,
zamykanie przy przewijaniu oraz inicjalizację po `ancore:content-loaded`.
W Zespole menu zawiera zmianę roli, odebranie dostępu lub anulowanie zaproszenia,
zależnie od uprawnień. Właściciel nie ma akcji zmiany swojej roli ani usunięcia.

Zaproszenie i zmiana roli używają wspólnej powłoki `tasks-modal`, pól
`tasks-form-field` i stopki z `tasks-modal__submit`. `workplace-team.js` zarządza
otwarciem, `inert` tła, fokusem i blokadą ponownego wysłania; `tasks.js` obsługuje
zamykanie i pułapkę fokusu, a listy wyboru korzystają z `AncoreCustomSelect`
i `AncoreDropdownLayer`. Błąd zaproszenia otwiera ten sam modal z wpisanymi danymi.
Odebranie dostępu wymaga `showConfirmModal` wyjaśniającego wpływ na Office.
Zapis nadal używa POST, CSRF i komunikatów aplikacji.

Ustawienia prowadzą do wspólnego panelu przez „Zarządzaj Workspace”. Funkcje i role opisuje
[TEAMWORK.md](TEAMWORK.md).

## 13. Centrum powiadomień

Powiadomienia są dostępne wyłącznie w panelu dzwonka. Panel używa include'ów
`notification_controls.html`, `notification_list.html`, `notification_pagination.html`
oraz `notifications-panel.js` i `notifications-panel.css`. Zachowuje powłokę panelu
wyszukiwania, avatary kont, standardowe przyciski, ikony i tokeny kolorów Ancore.
Nagłówek zawiera tytuł „Powiadomienia”, ikonę i zamknięcie, bez licznika ani podtytułu.
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
Karty grupują się według daty, pokazują podgląd komentarza lub do trzech zmian,
Workspace, moduł, numer rekordu i czas z pełną datą w tooltipie.
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
Panel nie ma dodatkowego dolnego paska z opisem zakresu aktywności.
Dzwonek jest przyciskiem,
a skrót w Ustawieniach otwiera ten sam panel. Osobna strona powiadomień
i jej link w wyszukiwarce zostały usunięte; dawny adres przekierowuje do Dashboardu.

Stan odczytu zmienia się po potwierdzonym zapisie; samo otwarcie panelu niczego
nie oznacza. Nowe zdarzenia sygnalizuje przycisk nad listą, bez automatycznego
przesuwania treści. Stany puste mają opis zależny od filtra. Błąd pobrania ma
akcję ponowienia; błąd zapisu pozostawia wpis i komunikat `role=alert`.
Żądania mają limit czasu, a zmiana filtra anuluje starsze pobranie.

Panel blokuje treść strony i pozostałe części menu przez `inert`, pozostawiając
dostępny przełącznik dom–powiadomienia–wyszukiwanie. Domek zamyka panel i przywraca
bazowy ekran, tak jak w wyszukiwaniu; lupa przełącza bezpośrednio do wyszukiwarki,
a ponowne kliknięcie dzwonka zamyka powiadomienia. Aktywny stan wskazuje otwarty panel.
Panel nie deklaruje `aria-modal`, ponieważ przełącznik pozostaje dostępny poza nim.
Tab i Shift+Tab obejmują panel oraz widoczne kontrolki przełącznika; Escape
zamyka panel i przywraca fokus. Przejście skrótem do wyszukiwania nie przywraca
fokusu do ukrytego panelu. Na telefonie panel zajmuje ekran,
a na najwęższym układzie toolbar przechodzi do dwóch wierszy.
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
