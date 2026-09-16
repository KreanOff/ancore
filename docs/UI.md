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
`color-mix(in srgb, var(--system-accent) 15%, #ffffff)`, tak jak podstawowe
tło przycisku „Dodaj projekt”, także przy zwiniętym sidebarze.

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
| Tytuł i toolbar katalogu | [toolbar Dokumentów](../documents/templates/documents/toolbar.html) jako przykład użycia wspólnych klas | `tasks-topbar`, `tasks-filterbar`, `tasks-filter-button`, `tasks-search-field` |
| Paginacja | [directory_pagination_toolbar.html](../tasks/templates/tasks/includes/directory_pagination_toolbar.html) | Kontekst `window`, atrybuty `data-project-*`, serwerowe URL |
| Zarządzanie kolumnami | [directory_column_manager.html](../tasks/templates/tasks/includes/directory_column_manager.html) | `tasks.js`, zapis ustawień lokalnych |
| Agregat filtrów | [directory_filter_aggregate.html](../tasks/templates/tasks/includes/directory_filter_aggregate.html) | Wspólne menu i aktywny stan |
| Wiersz zadania | [task_issue_row.html](../tasks/templates/tasks/includes/task_issue_row.html) | Stan, uprawnienia, `data-task-*`, ikony, JS listy |
| Karta Kanban | [task_board_card.html](../kanban/templates/kanban/includes/task_board_card.html) | Kolumna, okładka i przeciąganie |
| Standardowy modal formularza | [form.html Dokumentów](../documents/templates/documents/form.html), modale projektów/zadań | `tasks-modal*` + `modal-system.css` |
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

### Przyciski akcji w paskach narzędzi

Przyciski używają wariantu `tasks-tag-topbar-button--row-highlight`:
tła `color-mix(in srgb, var(--system-accent) 15%, #ffffff)` oraz tekstu i ikony
w kolorze `--text-primary`. Tło jest o 7 punktów procentowych intensywniejsze
niż podświetlenie wiersza tabeli; przycisk nie ma paska po lewej ani cienia.
Po najechaniu na aktywny przycisk udział turkusu rośnie do 22%, z przejściem
koloru wspólnego komponentu; fokus klawiatury dodaje obrys.
Rozmiar, zaokrąglenie i obsługa modala pochodzą ze wspólnego
przycisku. Wariant jest stosowany do akcji „Dodaj projekt”, „Dodaj grupę”
i „Dodaj zadanie” w Zadaniach, „Dodaj przestrzeń” i „Dodaj tablicę” w Kanbanie
oraz „Dodaj kontakt”, „Dodaj firmę” i „Dodaj gościa” w Kontaktach.
Ten sam wariant mają „Dodaj tag” w Zadaniach i Kanbanie, „Nowe wydarzenie”
w pasku Kalendarza, „Nowa biblioteka” w pasku Dokumentów oraz „Otwórz zadania”
w pasku Dashboardu.
Obejmuje przyciski katalogów oraz ich odpowiedniki wewnątrz projektu/grupy.

### Tabele i formularze Dokumentów

`documents.css` zachowuje semantyczne tabele bibliotek i plików, dopasowane do
katalogu projektów: tekst 13px, nagłówki 35px, wiersze danych minimum 48px, białe tło,
delikatne podziały poziome bez separatorów między kolumnami oraz szare
podświetlenie hover/focus. Wiersze plików mogą być wyższe, aby pomieścić
drugą linię z typem i lokalizacją. Nazwy mają
ellipsis; pełna nazwa pozostaje w tekście linku i jego `title`. Ikony bibliotek,
folderów i plików są monochromatyczne, bez ozdobnych ramek.

Panel bibliotek używa `tasks-rail-link`, akcje ikonowe `tasks-icon-button`,
a wybór kolumn `tasks-directory-column-item`. Formularze korzystają z
`form-input`, `tasks-inline-input`, `form-select`/`tasks-inline-select` oraz
`tasks-modal__errors`. Lokalne reguły odpowiadają za układ modułu i upload;
wspólne komponenty za kontrolki, stany interakcji i powłokę okna.

Filtry Dokumentów używają panelu `tasks-project-filter-builder` i wspólnych
szablonów warunków tekstowych oraz wyboru wartości. Lista pól i aktywne warunki
pochodzą z `documents/query.py`; obsługę wyszukiwania, czyszczenia i nawigacji
zapewnia `tasks.js`. Panel sortowania
[directory_sort_builder.html](../tasks/templates/tasks/includes/directory_sort_builder.html)
jest wspólny dla Dokumentów i Wszystkich projektów: wyszukiwanie pola,
wybór kierunku i zaznaczenie aktualnego ustawienia. Biblioteka, folder i widok
stanowią kontekst nawigacji; przycisk „Wyczyść” w panelu filtrów ich nie usuwa.

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
| `--app-modal-bar-min-height` | `60px` |

Modal ma nazwę dostępną dla czytnika, sensowny fokus po otwarciu, obsługę
klawiatury i powrót fokusu. Błędy formularza zachowują wpisane dane. Podczas
zapisu użytkownik dostaje stan oczekiwania, a powtórne wysłanie jest kontrolowane.

Dokumenty są przykładem dialogu HTML pobieranego nagłówkiem `X-Document-Modal`.
Obsługa aktywuje `inert` na tle i przywraca je po zamknięciu. Nie należy
dodawać drugiej równoległej powłoki tylko dlatego, że nowy formularz jest w innym module.

## 7. Ikony i typografia

Biblioteka ikon to Lucide, ładowana przez bazowy szablon. Lokalny adapter
[lucide-icons.js](../static/js/lucide-icons.js) normalizuje nazwy i udostępnia
`AncoreIcons.render(scope)`, `create`, `html`, `safeName` i `normalize`.

```html
<button type="button" class="btn btn-secondary btn-sm" aria-label="Odśwież listę">
    <i data-lucide="refresh-cw" aria-hidden="true"></i>
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
używanych w Kontaktach, Workspace i Dokumentach. Przed zmianą selektora
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
