# Standard UI Ancore

## 1. Cel i punkt odniesienia

Nowe funkcje mają wyglądać i zachowywać się jak część obecnego Ancore.
Punktem odniesienia są istniejące ekrany i komponenty opisane poniżej.
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
po `ancore:content-loaded`. Panel historii aktywności pozostaje osobnym komponentem.

### Przyciski akcji w paskach narzędzi

Przyciski używają wariantu `tasks-tag-topbar-button--row-highlight`:
tła `color-mix(in srgb, var(--system-accent) 17%, #ffffff)` oraz tekstu i ikony
w kolorze `--text-primary`. Tło jest o 9 punktów procentowych intensywniejsze
niż podświetlenie wiersza tabeli; przycisk nie ma paska po lewej ani cienia.
Po najechaniu na aktywny przycisk udział turkusu rośnie do 24%, z przejściem
koloru wspólnego komponentu; fokus klawiatury dodaje obrys.
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
Reguła w `style.css` ustala ciemny tekst i ikony, usuwa cień, zachowuje
widoczny obrys fokusu i osłabia przyciski nieaktywne przez opacity 0.55.
Nie zmienia geometrii przycisków, akcji drugorzędnych ani kolorów stanów
`saved`/`error` przycisku zapisu zadania.

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
na białej powierzchni kafelka. Ikony plików mają 115,5×115,5px, a folderów
i dysków 139,755×139,755px — wszystkie powiększone o 5% względem poprzednich
110px i 133,1px, bez zmiany wymiarów kafelków. Foldery i dyski korzystają
ze wspólnej reguły rozmiaru w kafelkach.
Wariant `documents-card--library` używa wyłącznie standardowej ikony dysku.
Nazwa, data i akcje pozostają poniżej. W ciasnych kolumnach lub przy dużej liczbie tagów
zawartość kafelka można przewinąć bez zmiany jego proporcji. Rozmiar ikon kafelków nie zmienia ikon
w tabeli ani panelu bocznym.
Siatka dopasowuje liczbę kolumn do miejsca z minimalną szerokością kolumny
248px (lub całą dostępną szerokością, gdy jest węższa), również na telefonie.
Kafelek zajmuje 85,7375% szerokości kolumny, dzięki czemu jego szerokość i wysokość
są o kolejne 5% mniejsze względem poprzednich 90,25%, przy tej samej liczbie kolumn.
Dotyczy Dysków, plików i Dokumentów;
rozmiary tekstu, ikon oraz przycisków pozostają bez zmian.
Na wąskim ekranie akcje mogą przejść pod datę.
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
od obu krawędzi tabeli, także na telefonie i w nagłówku. Przyciski działań
są wyrównane do prawej; ich kolumna ma 168px szerokości, aby zachować miejsce
na cztery przyciski także przy przewijaniu poziomym.
Foldery Dysku mają cztery akcje w kolejności zgodnej z plikami: zmiana nazwy,
gwiazdka, pobranie ZIP i usunięcie pustego folderu. Wspólny include
`documents/includes/row_actions.html` obsługuje tabelę i kafelki, z etykietami
zawierającymi nazwę folderu i `aria-pressed` gwiazdki. W zbiorczym widoku
gwiazdek folder pokazuje nazwę dysku jako link, tak jak lokalizacja pliku.
Pusty stan gwiazdek obejmuje pliki i foldery.
Pusty stan zachowuje własne wyśrodkowanie i padding. Nazwy mają
ellipsis; pełna nazwa pozostaje w tekście linku i jego `title`. Ikony nie mają
ozdobnych ramek. Foldery na listach i kafelkach Dysku oraz Dokumentów używają
wspólnego include'a `documents/includes/folder_icon.html` z parametrem `has_files`.
Pusty folder jest zamknięty, a folder z plikami ma otwartą okładkę i dwie
widoczne kartki. Oba warianty są płaskimi żółtymi SVG (`#ffd855`) z pomarańczową
zakładką (`#ffb41f`), bez obrysu. Stan uwzględnia aktywne pliki w podfolderach,
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
Ikony plików i folderów w tabelach Dysku i Dokumentów mają 32×32px w polu 32×32px.
Wszystkie dyski używają płaskiej, poziomej niebieskiej obudowy z include'a
`documents/includes/drive_icon.html` na liście, w kafelkach i panelu bocznym.
SVG zachowuje stałe kolory oparte na `#4285d4` i białych detalach,
nie ma obrysu ani fokusu i jest dekoracyjne.
Nawigacja, pusty stan, filtry, sortowanie i globalne wyszukiwanie zachowują
ikonę Flaticon `hard-drive`. Ikona w wierszu listy dysków ma rozmiar
32×32px w polu 32×32px, a w panelu bocznym 30×30px, również na telefonie.
Wiersze dysków mają minimum 44px wysokości, a odstęp między ikoną i nazwą
wynosi 8px (10px w zwężonej liście).

Formularz tworzenia i ustawień dysku zawiera wyłącznie nazwę i opis.
Nie udostępnia wyboru zdjęcia ani kadrowania. Wcześniej zapisane zdjęcia
nie są wyświetlane; lista, kafelki i panel boczny zawsze używają wspólnej ikony.

Lista dysków zajmuje całą szerokość treści. Pod tytułem jest pasek narzędzi
z przełącznikiem widoku, filtrami, sortowaniem, wyszukiwaniem i paginacją.
Poniżej pasek `documents-workspace-nav` używa zwartego wariantu `tasks-rail-link`: aktywne „Dyski” oraz
linki do wszystkich plików, ostatnich zmian, gwiazdek i kosza. Liczniki
zachowują zakres Workspace i nie zależą od filtrów. Na telefonie pasek przewija
się poziomo. Indeks nie powtarza listy dysków w panelu bocznym.
Pasek narzędzi, zakładki i siatka dysków mają wspólny
odstęp boczny `--documents-index-padding-x: 0.95rem`, zgodny z paskiem narzędzi
katalogów. Skrajne komórki listy dysków mają symetryczne odstępy od krawędzi tabeli:
24px na komputerze i 20px na telefonie, również w nagłówku i przy węższej tabeli.
Na komputerze lewy odstęp jest taki sam jak na liście plików.

Lista dysków ma trzy kolumny danych: „Nazwa”, „Zmodyfikowano”, „Rozmiar”,
z osobnym polem przycisków działań. Lista folderów i plików Dysku pokazuje
dodatkowo kolumnę „Tagi” między nazwą a datą. Używa tych samych etykiet
`documents-tag` co kafelki; kliknięcie tagu filtruje listę z zachowaniem
kontekstu dysku/Workspace, wyszukiwania i pozostałych filtrów. Foldery i pliki
bez tagów pokazują „—”. Kolumna ma 180px, a etykiety zawijają się w komórce.
Minimalna szerokość tabeli plików wynosi 870px (800px na telefonie);
węższy obszar zachowuje wszystkie kolumny dzięki przewijaniu poziomemu.
Rozmiar dysku i folderu sumuje aktywne pliki, również w podfolderach,
w zakresie właściciela i Workspace. Puste elementy pokazują 0 bajtów.
Tagi są dostępne także w filtrach, edycji i kafelkach. W koszu kolumna pokazuje datę
modyfikacji, a data usunięcia jest dostępna w `title` komórki.
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

Filtry Dysku używają panelu `tasks-project-filter-builder` i wspólnych
szablonów warunków tekstowych oraz wyboru wartości. Lista pól i aktywne warunki
pochodzą z `documents/query.py`; obsługę wyszukiwania, czyszczenia i nawigacji
zapewnia `tasks.js`. Panel sortowania
[directory_sort_builder.html](../tasks/templates/tasks/includes/directory_sort_builder.html)
jest wspólny dla Dysku i Wszystkich projektów: wyszukiwanie pola,
wybór kierunku i zaznaczenie aktualnego ustawienia. Dysk, folder i widok
stanowią kontekst nawigacji; przycisk „Wyczyść” w panelu filtrów ich nie usuwa.

### Katalog i edytor Dokumentów

Pliki DOCX/XLSX/PPTX w Dysku używają tej samej powłoki pełnego edytora
`documents/office/suite.html` co Dokumenty. Linki nazwy i kafelka otwierają
osobną kartę (`target="_blank"`, `rel="noopener"`), podobnie jak wyniki wyszukiwania.
Pasek udostępnia metadane, pobieranie i zapis, a „Wróć do dysku” prowadzi
do folderu pliku. Pozostałe formaty zachowują modal podglądu. Dla starszych
formatów biurowych wspólna akcja „Otwórz kopię w pełnym edytorze” tworzy kopię
w tym samym dysku i otwiera ją w nowej karcie. Stan niedostępnego edytora
zachowuje pobieranie i powrót. Funkcja nie dodaje nowych stylów ani kontrolek.
Przycisk powrotu w powłoce pełnego edytora używa tego samego komponentu co
nagłówek grup: `tasks-issue-close` ze strzałką bez ramki oraz pionowego
separatora `tasks-issue-divider` w `tasks-issue-breadcrumb tasks-project-breadcrumb`.
Dotyczy to także tablicy i stanu niedostępnego edytora.

Osobna pozycja „Dokumenty” używa ikony `file-text`. Katalog w
`documents/office/index.html` zachowuje paski `tasks-topbar`/`tasks-filterbar`,
nawigację `tasks-rail-link`, tabelę i kafelki Dysku. Foldery i upload używają
tego samego `documents/form.html` oraz obsługi fokusu, Escape i błędów w
`documents.js`. Wariant uploadu `office_upload` wyświetla wyłącznie formaty dokumentów.

Lista Dokumentów używa tych samych odstępów co lista plików Dysku: 24px
od lewej i prawej krawędzi tabeli, także na telefonie oraz w nagłówku.
Kolumna działań ma 168px szerokości i przyciski wyrównane do prawej.
Foldery Dokumentów używają tej samej kolejności akcji co pliki: gwiazdka,
zmiana nazwy, pobieranie ZIP i usunięcie pustego folderu. Include
`documents/office/actions.html` obsługuje listę oraz kafelki, zachowując
istniejące przyciski ikonowe, etykiety i `aria-pressed` gwiazdki.
Pusty widok oznaczonych elementów informuje o dokumentach i folderach.
Pusty stan zachowuje własne odstępy i wyśrodkowanie.
Kolumna „Tagi” między nazwą a datą używa etykiet `documents-tag` z Dysku;
foldery i dokumenty bez tagów pokazują „—”. Oba katalogi mają tę samą
minimalną szerokość tabeli (870px, 800px na telefonie) oraz zawijanie tagów.
Tagi są widoczne również na kafelkach. Kliknięcie etykiety filtruje dokumenty
ze wszystkich folderów bieżącego Workspace; aktywny tag i akcja czyszczenia
pojawiają się nad listą. Filtr pozostaje przy wyszukiwaniu, sortowaniu,
paginacji, zmianie układu i akcjach gwiazdki/kosza.
Przypisanie tagów korzysta ze wspólnego pola `documents-tag-picker` w oknie
„Dane dokumentu” i w metadanych starszego edytora tekstu. Zmiana tagów
w edytorze tekstu oznacza niezapisane zmiany tak samo jak zmiana treści.

Oba katalogi korzystają z jednego odstępu bocznego zakładek i siatki
(`--documents-index-padding-x` na `.documents-page`). Nagłówki tabel Dysków,
plików Dysku i Dokumentów są tekstowe, bez ikon. Lista Dokumentów pokazuje
drugą linię tylko dla lokalizacji
poza bieżącym folderem. Kafelki Dokumentów mają tę samą powierzchnię podglądu,
nazwę, metadane i stopkę co pliki Dysku oraz własny przewijany kontener.
Dokumenty używają wspólnego z Dyskiem include'a `documents/filter_sort.html`:
przycisku „Filtruj” z licznikiem, wyszukiwaniem pól, warunkami tekstowymi,
wyborem wartości oraz etykietami aktywnych filtrów z usuwaniem. Wariant
przyjmuje `filter_title`, `filter_heading` i `sort_title`, aby zachować nazwy
modułu. Sortowanie używa `directory_sort_builder.html` z wyszukiwaniem pól,
kierunkiem rosnąco/malejąco i aktualnym ustawieniem w przycisku, identycznie
jak w Dysku. Pusty wynik filtrów ma akcję czyszczenia.
Paginacja korzysta z `directory_pagination_toolbar.html` z wyborem 25/50/100 pozycji. `tasks.js`
obsługuje także wyszukiwanie z opóźnieniem i Enter; układ, folder i widok
pozostają zachowane przy zmianie filtrów, sortowania lub liczby pozycji.
Folder i układ należą do adresu formularza wyszukiwania, a nie do zbioru
czyszczonych filtrów. Filtry i sortowanie wracają na pierwszą stronę;
zmiana lista/kafelki zachowuje stronę. Na telefonie
wiele akcji nagłówka zawija się do kolejnych rzędów we wspólnym wariancie
Dysku i Dokumentów; tabela zachowuje własne przewijanie poziome.

Starszy edytor tekstu jest pełnym ekranem z nazwą, wyborem folderu, paskiem formatowania,
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
Pliki ONLYOFFICE otwierają ten ekran w osobnej karcie (`target="_blank"`,
`rel="noopener"`), również z globalnego wyszukiwania. Wariant
`office-editor-window` rozszerza `core/base.html`, pomija blok `app_navigation`
i wykorzystuje pełną szerokość bez bocznego menu i skalowania iframe.
Tworzenie pliku rezerwuje kartę podczas zatwierdzenia modalu, a po zapisie
odświeża katalog w pierwotnej karcie. Błąd zamyka pustą kartę; blokada okien
pokazuje odnośnik do utworzonego pliku. Tablica zachowuje nawigację Ancore.
ONLYOFFICE zachowuje własny polski interfejs, Excalidraw jest izolowany od
CSS aplikacji i używa turkusowego akcentu. Katalog ma dwa wspólne paski:
tytuł z akcjami oraz narzędzia z wyszukiwaniem i paginacją. „Nowy dokument”
jest główną akcją; upload i folder używają wariantu drugorzędnego. Typ pliku
(dokument, arkusz, prezentacja, tablica) wybiera się w istniejącym modalu tworzenia.
Nie ma osobnego rzędu powielającego akcje tworzenia.
`office-suite.js` inicjalizuje ekran także po `ancore:content-loaded`;
`data-app-full-navigation` wymusza bezpieczne opuszczanie aktywnych edytorów.
Statusy zapisu są potwierdzane przez serwer. Tablica przy błędzie zachowuje
scenę i pozwala pobrać bieżącą kopię; jej iframe przyjmuje wyłącznie komunikaty
z okna rodzica tego samego originu.

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

`modal-system.css` wprost wskazuje okna projektów i zadań jako wzorzec
standardowego okna aplikacji. Powłoka odpowiada za powierzchnię, przyciemnienie,
szerokość, cień, nagłówek, stopkę i przycisk zamknięcia; moduł odpowiada za pola.

| Token powłoki | Wartość bazowa |
| --- | --- |
| `--app-modal-surface` | `#ffffff` |
| `--app-modal-scrim` | `rgba(21, 27, 38, 0.38)` |
| `--app-modal-scrim-filter` | `blur(2px)` |
| `--app-modal-radius` | `14px` |
| `--app-modal-width` | `min(760px, calc(100vw - 2rem))` |
| `--app-modal-padding-x` | `24px` |
| `--app-modal-bar-min-height` | `50px` (stała wysokość nagłówka i stopki) |
| `--app-modal-bar-padding-y` | `4px` |

Nagłówki i stopki standardowych okien aplikacji mają po 50px wysokości CSS,
również na telefonie. Wspólny standard obejmuje projekty, grupy, zadania,
Kanban, kontakty, firmy, Kalendarz, Workspace i Dokumenty, a także edycję
profilu oraz kadrowanie zdjęć. Paski nie kurczą się przy przewijaniu treści.

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
