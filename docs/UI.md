# Standard UI Ancore

## Obowiązujący wzorzec — zacznij tutaj

Ancore ma jeden interfejs. Nowy ekran składaj z aktualnych komponentów
i poniższych układów. Nazwa modułu nie uzasadnia osobnego nagłówka, przycisku,
formularza ani okna. Wzorcami są nagłówek **otwartej Przestrzeni** (nazwa, akcje
i zakładki), dolny pasek narzędzi **Zasobów**, tabela **Tagów** oraz wspólne
`Modal` i `FormDialog`. Opisy
wycofanych Projektów, Grup i Kanbana dalej w tym pliku stanowią wyłącznie
kontekst historyczny. Nie kopiuj ich dawnych ekranów.

**W całej aplikacji nie renderujemy przycisków menu z trzema paskami
(`menu`) ani kolumn przeznaczonych wyłącznie na te przyciski.** Usunięto całe
menu wraz z jego wejściami do akcji, bez zastępowania innym przyciskiem.
Pozostają istniejące kontrolki edycji, informacji, notatek, wyboru, przełączania
Workspace, menu z wielokropkiem i zwijania nawigacji (`panel-left`).
Historyczna nazwa klasy `tasks-directory-menu-sheet` nadal występuje
w układach tabel; nie oznacza widocznego menu ani dodatkowej kolumny.
Te same zasady obowiązują w React i pierwszym renderze Django.

Schemat każdej strony (w obrębie wspólnej powłoki aplikacji):

```text
┌──────────────────────────────────────────────────────────────┐
│ Tytuł strony                              Główne działania    │
│ Zakładki z ikonami, jeżeli strona ma kilka widoków              │
├──────────────────────────────────────────────────────────────┤
│ Filtruj · Sortuj · Wyszukiwarka              Działania         │
├──────────────────────────────────────────────────────────────┤
│ Przewijana tabela lub karty                                   │
│ W tym samym obszarze: wyniki / stan pusty                      │
├──────────────────────────────────────────────────────────────┤
│               Pokaż więcej (20 / 65)                          │
└──────────────────────────────────────────────────────────────┘
```

Schemat formularza:

```text
┌──────────────────────────────────────────────────────────────┐
│ Tytuł okna                                          Zamknij   │
├──────────────────────────────────────────────────────────────┤
│ Tytuł [pole]                      Widoczność [wybór]           │
│ Opis  [pole wielowierszowe]                                   │
│ Etykieta [kontrolka]              Etykieta [kontrolka]         │
│ Na telefonie jedna para w wierszu; etykieta nadal po lewej     │
│ Błędy pod kontrolkami; przewijana treść                        │
│                                                              │
│                                              Anuluj   Zapisz │
└──────────────────────────────────────────────────────────────┘
```

| Element | Aktualne źródło do użycia |
| --- | --- |
| Nagłówek strony | [`shared/PageHeader.tsx`](../frontend/app/src/shared/PageHeader.tsx): `heading`, `actions`, `navigation`; te same klasy w pierwszym renderze Django |
| Zakładki strony | [`shared/PageTabs.tsx`](../frontend/app/src/shared/PageTabs.tsx) w `PageHeader.navigation`; linki/przyciski z istniejącymi ikonami i aktywnym stanem ARIA |
| Dolny pasek narzędzi | [`shared/DirectoryToolbar.tsx`](../frontend/app/src/shared/DirectoryToolbar.tsx): `Toolbar` lub formularz `DirectoryToolbar`, z `filters` i `search` po lewej oraz `actions` po prawej; wzorzec [`resources/App.tsx`](../frontend/app/src/resources/App.tsx) |
| Filtruj i Sortuj | `ToolbarFilter` i `ToolbarSort` z `shared/DirectoryToolbar.tsx`; istniejące pola i opcje modułu we wspólnej powłoce |
| Strona referencyjna | [`spaces/SpaceHeader.tsx`](../frontend/app/src/spaces/SpaceHeader.tsx), [`spaces/base.html`](../backend/spaces/templates/spaces/base.html) |
| Tabela danych | [`components/data-table.css`](../static/css/components/data-table.css), wzorzec [`tags/TagsPage.tsx`](../frontend/app/src/tags/TagsPage.tsx); te same klasy w React i Django |
| Kolejne wyniki | [`shared/LoadMore.tsx`](../frontend/app/src/shared/LoadMore.tsx), [`core/includes/load_more.html`](../backend/core/templates/core/includes/load_more.html), wspólny `work-list-more` |
| Powłoka okna | [`shared/Modal.tsx`](../frontend/app/src/shared/Modal.tsx): duży panel albo jawny `size="compact"` dla krótkich operacji |
| Formularz ze schematu | [`forms/FormDialog.tsx`](../frontend/app/src/forms/FormDialog.tsx): `FormLayout`, `FormFields`, `FormDialog`; rozmiar z `schema.compact` |
| Wygląd | [`base/variables.css`](../static/css/base/variables.css), [`components/page-header.css`](../static/css/components/page-header.css), [`components/app-toolbar.css`](../static/css/components/app-toolbar.css), [`components/tasks.css`](../static/css/components/tasks.css), [`components/modal-system.css`](../static/css/components/modal-system.css); uwzględnij kolejność nadpisań opisaną w rozdziale 3 |

`PageHeader` jest wspólny dla katalogów i szczegółów Przestrzeni, Zespołów,
Filtrów, Pulpitów, Zasobów, Dysków/Dokumentów, Workspace, zadania, Kalendarza,
Dla ciebie, profilu i ustawień. `SpaceHeader` układa w nim awatar Przestrzeni.
Górny wiersz zawiera tytuł i działania. **Ikona lub zdjęcie przy tytule
występuje wyłącznie w otwartej Przestrzeni**; katalog Przestrzeni, pozostałe
katalogi, Pulpity, Zespoły i ich profile oraz edytory mają sam tytuł.
Gwiazdkę ulubionych zapisanego filtra umieszczaj w działaniach po prawej.
Ikony przycisków powrotu, działań i zakładek pozostają. Drugi wiersz,
jeśli występuje, zawiera dotychczasowe widoki strony. Nie dodawaj fikcyjnych
zakładek do ekranu, który ich nie potrzebuje. Nawigacja wewnętrznego panelu
(np. „Twoja praca”) pozostaje przy tym panelu.

Oba wiersze tworzą jedną białą powierzchnię `app-page-header-group`,
z linią wyłącznie pod całym nagłówkiem. Tytuł używa tokenów 17px/700,
interlinii 1.45, wiersz ma minimum 45px i padding 0.5rem / 15px.
Awatar otwartej Przestrzeni ma 32px; pozostałe tytuły nie rezerwują pola ikony.
`PageTabs` zachowuje 13.5px/400, ikony 18px i czerwone podkreślenie
aktywnego widoku, zgodnie z otwartą Przestrzenią. Na wąskich ekranach akcje
mogą przejść do kolejnego wiersza, a zakładki przewijają się poziomo wewnątrz
nagłówka. Wspólny CSS jest w `components/page-header.css`.

W Kalendarzu przełącznik „Dzień / Tydzień / Miesiąc / Rok” znajduje się po
prawej stronie paska narzędzi (`Toolbar.actions`), jako tekstowa grupa
`tasks-segments app-toolbar__segments`, zgodna z przełącznikiem skali Osi czasu.
Aktywny przycisk ma `aria-pressed` i szare podświetlenie. Nagłówek zawiera
tytuł i „Nowe wydarzenie”, bez osobnego wiersza zakładek. Nawigacja po datach,
nazwa okresu, licznik i wyszukiwarka pozostają po lewej.
Grupa widoków ma szerokość `--calendar-views-width`: 280px, a do szerokości
kontenera 1050px — 244px. Przyciski dzielą tę szerokość równo.
Pasek i treść mają ten sam boczny padding `--app-page-padding-x`.
Do szerokości kontenera 720px grupa zajmuje cały kolejny wiersz paska.
Jej szerokość jest niezależna od prawego panelu.
W Zasobach szybkie filtry z licznikami
korzystają z tego samego paska zakładek i zachowują dotychczasowe filtrowanie.
Pasek Kalendarza nie zawiera wyboru „Wszystkie pozycje” ani filtra „Kolory”.
Pokazuje wszystkie dostępne wydarzenia i zadania w wybranym okresie;
pozostają wyszukiwarka oraz licznik pozycji.
Kolory wydarzeń i wybór koloru w formularzu pozostają dostępne.
Pole „Kolor” w oknie wydarzenia zajmuje pełny wiersz i używa wspólnego
`shared/ColorControl`, zgodnego z kolorem nazwy w konfiguracji Przestrzeni:
próbka otwiera paletę, pole przyjmuje `#RRGGBB`, „Domyślny” przywraca
czerwień, a podgląd pokazuje oznaczenie wydarzenia. Kontrolki korzystają
z istniejących klas `documents-color-control` i `work-configuration-color`
i zawijają się na wąskich ekranach. Style próbki i układu znajdują się
w `components/shared-controls.css`, dostępnym również przy bezpośrednim
wejściu do Kalendarza. `calendar-color-preview` jest wariantem
etykiety wydarzenia o naturalnej szerokości, bez zachowania przycisku.

Prawy pasek Kalendarza jest identyczny z panelem przy Przestrzeniach i liście
zadań: wspólny `shell/TodaySidebar` pokazuje mini kalendarz i „Plan na dziś”.
Pierwszy render dziedziczy `default_today_sidebar` z `core/base.html`.
`CalendarPage` nie renderuje osobnego portalu ani „Planu dnia”. Wspólna
powłoka zachowuje szerokość 272px, zapamiętane rozszerzenie i szufladę
do 1100px. Kliknięcie dnia w mini kalendarzu otwiera odpowiednią datę
w głównym Kalendarzu. Przycisk `panel-right` zwija i otwiera panel,
oddając miejsce siatce bez zmiany jej widoku.
„+N więcej” w miesiącu otwiera wskazany dzień w głównej siatce, pokazując
wszystkie jego pozycje. Tworzenie wydarzeń pozostaje w nagłówku i komórkach.
Wspólne reguły w
[`calendar.css`](../static/css/calendar.css) obejmują React i pierwszy render Django.
Pozycje w komórce miesiąca przewijają się, gdy brakuje wysokości, dzięki
czemu nie zasłaniają następnego tygodnia i zachowują dostęp do „+N więcej”.

Specjalistyczne treści, np. kalendarz, tablica, karty zespołów, edytor pliku
i kadrowanie obrazu, zachowują swój układ. Kolejne wyniki odsłania
wspólny pasek „Pokaż więcej” pod listą. Wspólne komponenty określają wygląd
kontrolek, stanów błędu i działania okna. Każdą zmianę porównaj z ekranem
referencyjnym przy tej samej szerokości, również po ponownym wejściu.

## Klawiatura i błędy formularzy

Fokus klawiatury kontrolek jest widoczny także w przewijanych listach,
formularzach oraz na logowaniu. Pola wpisywania tekstu, liczb i dat oraz
wyszukiwarki w listach wyboru zachowują zwykłe obramowanie bez czerwonego
obrysu aktywnego pola. Tak samo zachowują się przyciski w oknach potwierdzenia,
w tym zamknięcie krzyżykiem; wyjątkiem jest systemowy tryb wymuszonych kolorów.
Wspólne `Dropdown` otwiera panel formularza strzałką
w dół na pierwszej widocznej kontrolce. Strzałki, Home i End nie przejmują
edycji tekstu ani obsługi natywnego selecta. Panel osadzony w formularzu
zamyka się po przeniesieniu fokusu poza niego, zachowując wartości pól.
Escape przywraca fokus przycisku; już obsłużone zdarzenie nie zamyka rodzica.

Błędy muszą być powiązane z polami przez `aria-invalid` i `aria-describedby`.
Dotyczy to również każdego checkboxa w grupie, pól Workspace, wydarzenia
Kalendarza oraz obu dat nieprawidłowego zakresu na osi czasu. Wspólny
`FieldControl` utrzymuje opis pomocy również w wariancie `bare`.
Po nieudanym zapisie `FormDialog` przenosi fokus do pierwszego widocznego,
aktywnego błędnego pola lub do komunikatu ogólnego (`role="alert"`,
`tabIndex={-1}`). Nie gub szkicu ani możliwości ponowienia zapisu.
Pierwszy render Django nadaje komunikatowi pola jeden identyfikator
`<id_pola>_error`; nie dubluj ID generowanego przez listę błędów Django.

Dokumenty zapamiętują przycisk przed rozpoczęciem odczytu okna i przekazują
`returnFocus` do `Modal`. Zmiana podglądu na edycję zachowuje pierwotny
przycisk strony. Powrót przez historię przeglądarki odtwarza przewinięcie
katalogów Dysku i Dokumentów zarówno w tabeli, jak i w kafelkach.
Kalendarz tylko do odczytu wyłącza wszystkie wejścia do tworzenia wydarzeń;
stan pusty nie zachęca wtedy do niedostępnego dodawania.

## Wspólny dolny pasek narzędzi — wzorzec Zasobów

Pod nagłówkiem i zakładkami znajduje się jedna powłoka `app-toolbar`.
Kontrolki tabeli i widoku, „Filtruj” i „Sortuj” trafiają do `filters`,
wyszukiwarka do `search`, a istniejące działania do `actions`.
Kontrolki, sortowanie i wyszukiwarka są po lewej; działania są wyrównane
do prawej. Do działań należą m.in. „Zapisz”, „Edytuj”, „Usuń”, „Dodaj”,
eksport, odświeżanie oraz operacje na zaznaczonych wierszach, np. przekazanie
i zwrot Zasobów. Liczniki i informacje o wynikach pozostają przy kontrolkach.
Widoczność, wyłączenie i zakres operacji nadal wynikają z uprawnień
oraz stanu modułu.
**Aktywne filtry, ich usuwanie, informacje o zakresie wyników i operacje
zaznaczenia pozostają w tym samym pasku.** Nie renderuj pod nim drugiego
paska po zastosowaniu filtra lub zaznaczeniu wiersza. `app-toolbar__summary`
umieszcza etykiety i usuwanie filtrów w `filters`, bez własnej ramki,
paddingu ani wymuszonej pełnej szerokości. `app-toolbar__selection` grupuje
operacje zaznaczenia w `actions`. Długie etykiety mogą zawijać się wewnątrz
paska bez obcinania tekstu i poziomego przewijania strony.
Dotyczy to widoków Przestrzeni (w tym Raportów i Backlogu), Zasobów oraz
informacji o wynikach Dysku/Dokumentów, w React i pierwszym renderze Django.
Pasek pozostaje poza przewijaną listą. Na wąskim ekranie grupy zawijają się,
a wyszukiwarka przechodzi do pełnego wiersza; działania nadal są wyrównane
do prawej.

`Toolbar` renderuje `div`; `DirectoryToolbar` renderuje `form` i przekazuje
atrybuty formularza. Oba eksportuje
[`shared/DirectoryToolbar.tsx`](../frontend/app/src/shared/DirectoryToolbar.tsx).
Sloty w DOM mają kolejność `app-toolbar__controls`, `app-toolbar__search`,
`app-toolbar__actions`, zgodną z kolejnością klawiatury. Zachowują wspólne
klasy `tasks-filterbar-*`; historyczna nazwa `tasks-filterbar-right`
wyszukiwarki nie określa jej bieżącego położenia.
Wyszukiwarka zaczyna się za kontrolkami, a grupa działań korzysta z
`margin-left: auto`. Nie dodawaj osobnej powłoki dla lewego i prawego obszaru.
`children` służy m.in. ukrytym polom formularza. Nie zagnieżdżaj formularzy:
dla osobnego formularza wyszukiwania lub filtrów wybierz `Toolbar`.
[`spaces/ViewToolbar.tsx`](../frontend/app/src/spaces/ViewToolbar.tsx) jest
adapterem tego komponentu: jego `children` trafia do `filters`.
Pierwszy render Django używa tych samych klas, nazw pól i istniejących
atrybutów obsługi JS.

`ToolbarFilter` pokazuje `list-filter`, „Filtruj” i `chevron-down`;
`active` oznacza zastosowane filtry. `ToolbarSort` pokazuje `arrow-up-down`,
„Sortuj”, bieżącą etykietę `current` za separatorem oraz `chevron-down`.
Oba przyjmują dotychczasowe opcje/pola jako `children` i `label` dla
dostępności. Zachowaj istniejący sposób zastosowania filtrów: zatwierdzenie
formularza albo automatyczne przejście po wyborze. Pola formularza muszą
pozostać skojarzone z nim również po otwarciu panelu (`layer={false}`
w formularzowym wariancie filtrów).

Styl określa [`components/app-toolbar.css`](../static/css/components/app-toolbar.css),
a wymiary tokeny w `base/variables.css`: samodzielne przyciski, selecty
i wyszukiwarka mają wspólną wysokość 36px (`--app-toolbar-control-height`)
na wszystkich szerokościach ekranu. Wyszukiwarka ma maksymalnie 420px
szerokości, odstęp między kontrolkami wynosi 8px, a pionowy padding 4px.
Sloty mają wspólną minimalną wysokość
wiersza 36px (`--app-toolbar-row-height`), także bez wyszukiwarki.
Jednowierszowy pasek ma 44px: 36px wiersza oraz po 4px u góry i dołu.
`--app-toolbar-min-height` wynika z tych tokenów; nie ustawiaj odrębnej
wysokości ani pionowych marginesów dla modułu.
`app-toolbar__segments` rozszerza wspólny wariant przełącznika Osi czasu:
jedna ramka o wysokości kontrolki, połączone przyciski z separatorami
i szare podświetlenie aktywnego stanu. Kalendarz używa go w `actions`.
Poziomy padding pochodzi z `--app-page-padding-x` (15px).
Przy szerokości do 767px wyszukiwarka przechodzi do pełnego wiersza;
wysokość kontrolek pozostaje 36px.
Na wąskich ekranach i przy większej liczbie kontrolek pasek rośnie wraz
z zawiniętymi wierszami, zachowując pionowy padding 4px. Formularz
zaawansowanego zapytania również zachowuje naturalną wysokość treści.
`app-toolbar--embedded` zeruje wyłącznie padding poziomy, gdy zapewnia go
rodzic; nie tworzy odrębnego stylu przycisków.

Na granicy paska i treści odstęp zapewnia sam pasek. Kontenery Przestrzeni,
Zespołów, szczegółów Zasobu i Kalendarza oraz panel tworzenia Dokumentów
nie dodają tam drugiego górnego paddingu. Dotyczy to także Podsumowania
Przestrzeni, gdzie `.work-summary` opakowuje `.work-summary-dashboard`
w React i pierwszym renderze Django. Mierz rzeczywistą przerwę od dolnej
krawędzi nagłówka do kontrolek i od kontrolek do treści, nie tylko padding
samego paska. Lista zadań, Oś czasu i Raporty
nie dodają `gap` bezpośrednio po pasku; odstępy między dalszymi panelami
pozostają właściwe dla danego widoku. Ta sama zasada dotyczy paska ustawień
Przestrzeni, bez dodatkowych pionowych marginesów.

Nie dodawaj brakujących funkcji tylko po to, by zapełnić pasek: Workspace
może mieć samą wyszukiwarkę, a szczegóły Zasobu same działania. Zachowaj
istniejące wejścia do edycji, usuwania i operacji zbiorczych oraz ich ACL.
Ujednolicenie paska nie przywraca usuniętych przycisków trzech pasków,
menu wierszy ani ich kolumn. Specjalistyczne narzędzia edytorów dokumentów
pozostają przy edytorze.

## Jeden mechanizm kolejnych wyników: „Pokaż więcej”

W całej aplikacji listy korzystają z „Pokaż więcej”, zgodnie z listą zadań
Przestrzeni. Nie stosuj numerów stron, strzałek poprzednia/następna ani
wyboru liczby pozycji na stronę. Pierwsza porcja to 20 wyników; kliknięcie
odsłania kolejne 20 bez usuwania już widocznych wierszy i zaznaczeń.
Filtr lub nowe sortowanie rozpoczyna okno od pierwszych 20 wyników.

Używaj [`shared/LoadMore.tsx`](../frontend/app/src/shared/LoadMore.tsx),
[`shared/useLoadMorePage.ts`](../frontend/app/src/shared/useLoadMorePage.ts)
i [`components/load-more.css`](../static/css/components/load-more.css).
Wzorzec `work-list-more` ma pełną szerokość, wyśrodkowany tekst i licznik
`(wczytane / wszystkie)`, cienką górną linię oraz szare najechanie.
Stany: „Pokaż więcej”, „Wczytywanie…” oraz nieaktywny „Wszystkie wyniki”
(po doładowaniu całości); lista z maksymalnie 20 wynikami nie wymaga paska.
Zadania i Tagi zachowują własne nazwy końcowego stanu i ten sam wspólny styl.
Błąd zachowuje dotychczasowe wyniki oraz pozwala ponowić ten sam odczyt.
Powtórne kliknięcia nie mogą uruchamiać równoległych odczytów tej samej porcji;
zmiana widoku lub filtra unieważnia spóźnioną odpowiedź.

Serwerowe okna z [`core/list_window.py`](../backend/core/list_window.py)
operują wyłącznie na wcześniej ograniczonych uprawnieniami i posortowanych
danych. Kolejne żądanie zwraca pełny prefiks 20 → 40 → 60; React podmienia
okno w stanie, zachowując tożsamość wierszy. Parametr `limit` utrwala wielkość
okna w URL; dziennik pracy ma `work_log_limit`, historia Zasobu `history_limit`.
Stare adresy `page=2` oznaczają teraz pierwsze 40 wyników.
[`core/includes/load_more.html`](../backend/core/templates/core/includes/load_more.html)
zapewnia ten sam wygląd i kumulatywny wynik również bez JavaScriptu.
Workspace odsłania po 20 z już pobranej listy; powiadomienia zachowują kursor
oraz wspólny pasek „Pokaż więcej”.

## Tabele według Tagów

Wszystkie tabele danych aplikacji, również w oknach, używają `app-data-table`
i tokenów `--data-table-*` z `base/variables.css`. Wzorzec obejmuje katalogi
Przestrzeni, Filtrów, Pulpitów i Workspace, tabelę „Dla ciebie”, członków
Zespołów, udostępnienia, konfigurację Przestrzeni, Zasoby, Dyski/Dokumenty,
dziennik pracy, raporty i listę plików archiwum. Zawartość importowanych
arkuszy, grupowane listy zadań bez nagłówków kolumn oraz specjalistyczne
osie czasu, kalendarze, tablice i karty zachowują własną strukturę.

```text
┌──────┬─────────────────────┬──────────────────┬─────────────────┐
│  □   │ ikona NAZWA         │ ikona KOLUMNA    │ ikona KOLUMNA   │
├──────┼─────────────────────┼──────────────────┼─────────────────┤
│  □   │ Wartość             │ Wartość          │ Wartość         │
├──────┼─────────────────────┼──────────────────┼─────────────────┤
│  □   │ Wartość             │ Wartość          │ Wartość         │
└──────┴─────────────────────┴──────────────────┴─────────────────┘
```

Nagłówek jest biały, ma wielkie litery i ikonę 14px przed nazwą kolumny.
Nagłówek i standardowy wiersz mają 35px, tekst Atlassian Sans 13px/400
z interlinią 1.45, separatory 1px `#e1e4e7`. Padding poziomy nagłówka
wynosi 0.5rem, danych 0.75rem; kontrolki są wyśrodkowane bez paddingu.
Kolumny zaznaczania oraz zachowanych skrótów edycji, informacji, notatek
i przełączania Workspace mają szerokość 40px. Nagłówki skrótów są wizualnie
puste, z nazwą dostępną dla czytnika ekranu.
Nie dodawaj zaznaczania ani działań, których dany moduł nie obsługuje.
Najechanie i zaznaczenie stosują 8% czerwonego akcentu oraz pasek 3px
z lewej. Istniejące skróty wierszy zachowują swoje wspólne klasy przycisków.

Siatki oznaczaj przez `app-table-header` i `app-table-row`; komórki zachowują
`data-column`, role ARIA lub jawną klasę `app-table-cell`. Natywne `<table>`
używają dodatkowo `app-data-table--native`, treść nagłówka `app-table-heading`,
a istniejące komórki kontrolek `app-table-control`.
Wspólny arkusz określa wygląd, a moduł nadal szerokości/ukrywanie kolumn,
przewijanie, wyrównanie liczb oraz sortowanie, filtry, wybór i zmianę szerokości.
Nie dodawaj `tasks-tag-sheet` do innych tabel: ta klasa ustawia kolumny Tagów.
Wiersze plików pokazują lokalizację obok nazwy.
Na telefonie przewijaj tabelę w jej kontenerze, bez rozszerzania całej strony.
Pierwszy render Django stosuje te same oznaczenia.

## Katalog i profile Zespołów

Zespoły zachowują wspólny nagłówek, zakładki `work-tabs`, wyszukiwarkę,
karty `work-space-card`, formularze i pasek „Pokaż więcej”. Karta katalogu
ma kolejno baner, nazwę i opis; cała powierzchnia prowadzi do profilu zespołu.
Baner `.team-card-banner` ma proporcje 3:1 i kadruje istniejące zdjęcie przez
`object-fit: cover`. Bez zdjęcia ma jednolite neutralne tło `--panel-bg`.
Nazwa i opis znajdują się w `.team-card-body`; brak opisu ma tekst zastępczy.
Katalog nie pokazuje roli ani liczników na karcie. React i pierwszy render
Django używają tych samych klas. Profil rozdziela
„Podsumowanie”, „Zadania”, „Członkowie” i „Przestrzenie”. Podsumowanie rozszerza
istniejące `work-panel`, `work-summary-metrics` i `work-summary-grid`;
procent zamkniętych zadań ma natywny, opisany pasek `progress` w kolorze akcentu.

Wariant `.teams-page` dodaje wyłącznie lokalny układ profilu, banery kart,
listę wykonawców i kontrolki filtrów. Do 800px metryki mają dwie kolumny,
a dolne panele jedną. Lista członków używa wspólnych komórek bez menu wiersza,
z lokalnym wariantem `.team-members-sheet` bez zaznaczania zbiorczego i daty
członkostwa, której model nie przechowuje. Na wąskim ekranie tabela przewija
się poziomo. Lista zadań zachowuje układ bez pól zaznaczenia.

Dodawanie osoby korzysta ze wspólnego kompaktowego `FormDialog`.
Menu zmiany roli, usuwania osoby i zespołu z trzema paskami zostały usunięte
z aktywnego interfejsu. Nie dodano zastępczych kontrolek. Backend nadal
weryfikuje role oraz ochronę ostatniego administratora. Puste wyniki mają
istniejące ilustracje i tekst zależny od kontekstu.
[Funkcje Zespołów](SPACES.md#system-zespołów-04112026).

## Wspólna powłoka React

`frontend/app/src/shell/Shell.tsx` renderuje nagłówek, menu Workspace,
minimalne menu zarządzania, Favorites i globalne panele. `core/base.html`
zachowuje kontenery oraz pierwszy render. Istniejące klasy, font, tokeny,
szerokości i wysokości kontrolek pozostają wspólne. Minimalny wariant selektorów
w `layout/main.css` uwzględnia korzeń Reacta z `display: contents`, zachowując
wysokość topbaru i położenie sidebaru. Dropdowny korzystają ze wspólnego
adaptera; `.react-sidebar-row-menu` nie dodaje własnego pola w układzie.

Powłoka aplikacji używa biało-czerwono-czarnej tapety
`wallpaper-red-black-white.png` przez osobny token
`--app-shell-wallpaper-image`. Obraz pokrywa viewport przez `cover`,
z wyrównaniem do lewej i środka. Jasna górna część tapety zapewnia czytelne
tło kontrolek górnego paska. Ogólny token `--app-wallpaper-image`
pozostaje domyślnie `none`. Ekrany logowania, rejestracji, tworzenia i wyboru Workspace lokalnie ustawiają go na
`var(--app-shell-wallpaper-image)`; karty zespołów zachowują jednolite tło.
Zachowane wspólne tokeny
`--glass-surface-bg: var(--card-bg)` i `--glass-surface-filter: none`
zapewniają białe powierzchnie paneli bez rozmycia. Tło strony używa osobnego
`--app-shell-bg`: 12% neutralnej szarości `--system-interaction` zmieszanej
z bielą `--card-bg`, jako kolor zastępczy podczas ładowania obrazu.
Warstwa `body::before` wyświetla tapetę w odstępach i odsłoniętych
narożnikach paneli, a przezroczysty górny pasek pokazuje to samo tło. Karty,
główna treść, boczne panele, modale oraz panele logowania i rejestracji zachowują
białe powierzchnie.

Pod górnym paskiem znajdują się trzy osobne powierzchnie: lewe menu,
główna treść i prawy panel boczny. Mają wspólną górną i dolną krawędź,
obrys `--border-color` oraz promień `--app-shell-radius` (15px). Odstęp
między panelami oraz od bocznych i dolnej krawędzi okna wynosi
`--app-shell-gap` (4px na każdej szerokości ekranu). Panele zaczynają się
bezpośrednio pod górnym paskiem: od jego kontrolek oddziela je wyłącznie
dolny padding paska 2px, taki sam jak u góry. Geometrię współdzielą React,
pierwszy render Django i zasłona ładowania nawigacji przez
[`layout/panels.css`](../static/css/layout/panels.css). Wysokość treści
uwzględnia odstępy, zachowując wewnętrzne przewijanie stron.

Uchwyty zmiany szerokości lewego i prawego panelu współdzielą reguły
w `layout/panels.css`. Oba mają pole chwytania 9px oraz linię 3px,
wyśrodkowaną w odstępie między panelem bocznym a główną treścią.
Linia jest odsunięta o 12px od góry i dołu paneli; wskazanie kursorem,
fokus klawiatury i przeciąganie pokazują ten sam `--system-interaction`.
Linia jest wskaźnikiem fokusu bez dodatkowej ramki; tryb wymuszonych kolorów
zachowuje systemowy obrys.
Pozycjonowanie `fixed` utrzymuje uchwyty poza przycinaną zawartością paneli.
Dotychczasowe zasady ukrywania po zwinięciu oraz na ekranach mobilnych
pozostają wspólne z mechanizmem zmiany szerokości.

Prawy panel ma bazową szerokość `--app-right-sidebar-width` (272px). Na stronie
zadania pokazuje jego właściwości i używa `--app-task-sidebar-width` (370px).
W Kalendarzu i na pozostałych stronach aplikacji poza Dyskiem zawiera ten sam
miesięczny kalendarz, bez osobnego nagłówka i przycisku otwarcia.
Kalendarz korzysta z poniedziałkowego początku tygodnia, wyróżnia dzisiejszy
dzień, pozwala przełączać miesiące i wrócić przyciskiem „Dzisiaj”. Kliknięcie
dnia otwiera go w pełnym Kalendarzu. Pod kalendarzem znajduje się lista
„Plan na dziś” z łącznym licznikiem: wydarzenia Kalendarza przypadające na dziś
oraz widoczne, niezakończone zadania Przestrzeni z dzisiejszym terminem
w aktywnym Workspace, bez ograniczenia do wykonawcy. Wydarzenia całodzienne
są pierwsze, pozostałe pozycje mają wspólną kolejność chronologiczną.
Wiersz zadania pokazuje tytuł, klucz, Przestrzeń i godzinę oraz otwiera szczegóły.
Wiersz wydarzenia pokazuje tytuł, kropkę w zapisanym kolorze, „Kalendarz”
i godzinę lub „Cały dzień”; otwiera wydarzenie w Kalendarzu. Wydarzenie
rozpoczęte wcześniej pokazuje również datę rozpoczęcia.
Lista przewija się w pozostałej wysokości panelu; „Pokaż więcej” odsłania
kolejne wyniki po 20. Pusta lista pokazuje „Brak zadań i wydarzeń na dziś.”,
a błąd odczytu pozwala ponowić żądanie. Wyłączenie modułu Przestrzeni
pomija zadania, zachowując wydarzenia.
Powłokę renderuje `shell/TodaySidebar.tsx`, a pierwszy render Django
`core/includes/today_sidebar.html`; oba używają klas `today-sidebar`
z `layout/panels.css`. Wyłączenie modułu Kalendarza ukrywa domyślną zawartość.
Edytor Pulpitu zachowuje własny układ bez tej zawartości.
Na komputerze szerokość prawego panelu można zmieniać uchwytem po jego lewej
stronie. `right-sidebar-resizer` pozostaje w szczelinie także podczas przewijania
zawartości. Zakres wynosi 240–520px i dodatkowo zostawia co najmniej 360px
na główną treść, uwzględniając szerokość lewego menu i skalę interfejsu.
Szerokość zapisywana w `ancoreRightSidebarWidth` obowiązuje również
w Kalendarzu i właściwościach zadania. Zmniejszenie okna ogranicza bieżący
rozmiar bez zmiany zapisanej preferencji. Dwuklik przywraca domyślny rozmiar
(272px, a w zadaniu 370px). Uchwyt obsługuje klawiaturę: strzałka w lewo
poszerza panel, w prawo zwęża, Shift zwiększa krok z 8 do 24px, Home/End
wybierają granice zakresu. Do 1100px i po zwinięciu panelu uchwyt jest
ukryty; mobilna szuflada zachowuje ograniczenie do szerokości ekranu.
Przycisk `panel-right` na końcu górnego paska zwija go, oddając miejsce
treści. Desktop zapamiętuje wybór w `ancoreRightSidebarCollapsed`; bootstrap
odtwarza klasę przed załadowaniem CSS. Przy szerokości okna do 1100px panel
jest początkowo zamkniętą szufladą, bez zmiany preferencji desktopowej.
Escape, kliknięcie tła, nawigacja i zmiana szerokości zamykają szufladę.
Zamknięcie przez Escape lub tło przywraca fokus przycisku. Otwarcie na telefonie
zamyka lewe menu; treść pod szufladą jest `inert`. Host okien pozostaje
dostępny, aby formularz otwarty z panelu przyjmował wpisywanie i fokus.
Szuflada i `Modal` współdzielą blokowanie tła, zachowując je także po
zmianie szerokości przy otwartym oknie. Panel nie zmienia działania
Stickera ani Powiadomień. Do 600px wyszukiwarka zajmuje drugi wiersz górnego
paska, aby kontrolki i pole wyszukiwania mieściły się bez nakładania.

Podświetlenia menu nakładają się na jednolite tło: neutralne najechanie korzysta
z 6% krycia `--system-interaction`, a naciśnięcie z 10%. Aktywna pozycja
ma czerwone tło o kryciu 10%, wzmacniane do 16% przy najechaniu, fokusie
lub otwartym menu wiersza. W aktywnym wierszu tło rodzica jest przezroczyste,
więc kolory nie nakładają się. Tekst i zwykłe ikony aktywnej pozycji używają
ciemniejszego wariantu akcentu (`--sidebar-space-selection-ink`: 60% akcentu
z czernią), aby zachować czytelność na jasnym tle; znacznik i fokus zachowują
bazowy akcent. Krótkie przejście tła ma 120ms; preferencja
ograniczenia ruchu wyłącza przejścia istniejącą regułą powłoki.
Fokus klawiatury linków i „Więcej…” ma wewnętrzny obrys 2px,
również w panelu zwiniętego menu. Lokalna reguła obrysu nadpisuje globalne
`outline: none !important`; zwykłe kliknięcie nie utrzymuje fokusu wizualnego.

Nazwa Workspace w topbarze wykorzystuje dostępną szerokość przed wyszukiwarką,
niezależnie od szerokości i zwinięcia bocznego menu. Wielokropek pojawia się
dopiero po wypełnieniu tego miejsca. Menu wyboru zachowuje własną szerokość,
a na telefonie przycisk pokazuje sam awatar.

Menu ma dotychczasowe grupy i skróty, zapamiętywanie szerokości/zwinięcia,
podmenu w zwiniętym pasku oraz backdrop na telefonie. Wybór Workspace
obsługuje wyszukiwanie z normalizacją polskich znaków i klawiaturę.
Ikony podpunktów Pulpitów, Przestrzeni i Filtrów mają wspólne pole 20×20px
oraz stałą szerokość w układzie flex przez `--sidebar-subnav-icon-size`.
Dotyczy to SVG, emoji Pulpitów, awatarów Przestrzeni, pulpitu domyślnego,
wyszukiwania i przycisków „Więcej…”, także w zwiniętym i mobilnym menu.
Nagłówki sekcji zachowują token `--sidebar-icon-size` o wartości 18px.
Pickery Przestrzeni, Pulpitów i Filtrów używają istniejącej powłoki popover,
stanu pustego/błędu/ponowienia, strzałek i Escape z powrotem fokusu.
Menu mobilne wyłącza treść przez `inert` i ogranicza Tab do swoich kontrolek.
Maksymalne rozsunięcie lewego menu uwzględnia szerokość otwartego prawego
panelu, odstępy i skalę UI, zostawiając co najmniej 360px logicznej szerokości
treści. Ograniczenie chwilowe nie nadpisuje zapamiętanej preferencji szerokości.

Akcje oznaczania Przestrzeni, Pulpitów i Filtrów współdzielą
`tasks-favorite-toggle` oraz stan `aria-pressed`. Oznaczony element ma pełną
żółtą gwiazdkę `star-filled` (`#e2b203`), także przy hover/fokusie;
nieoznaczony ma zwykły kontur `star`. Dotyczy to menu bocznego i jego panelu
skrótów oraz zachowanych kontrolek gwiazdek Filtrów, w React i pierwszym
renderze Django.
Dekoracyjne gwiazdki zakładek i nagłówków pozostają konturowe.

Favorites zachowują bazę i klucze ustawień. Obsługują dodanie/usunięcie przez
przeciąganie, zmianę kolejności, anulowanie gestu oraz Alt+strzałki i akcje
dostępne klawiaturą. Dotyk używa ikony jako uchwytu, a tekst pozwala przewijać
menu. Natywny drag linku wewnątrz ulubionego wiersza jest wyłączony, by nie
przerywał gestu wskaźnika. Krótkie komunikaty renderuje `Toasts.tsx`, z tymi
samymi klasami i bez interpretacji HTML. Formularze otwierane z menu używają
`FormDialog` w `app-shell-modals`, ze wspólną obsługą fokusu i szkicu.

Historyczne odwołania do szablonów i ich kontrolerów poniżej opisują wzorzec
wyglądu oraz zgodność; aktualne interakcje przeniesionych ekranów należą do Reacta.

## Konta w React

Logowanie, rejestracja i krok nazwy Workspace renderują
`src/accounts/AuthPage.tsx`
w powłoce `accounts/auth_base.html`. Wszystkie trzy ekrany dodają wariant
`body.auth-page--wallpaper`, który
wyświetla tę samą biało-czerwono-czarną tapetę co aplikacja, przez lokalny
alias `--app-wallpaper-image: var(--app-shell-wallpaper-image)`. Tło
`.auth-shell` używa `left center / cover`. Ekran wyboru Workspace włącza ten sam
wariant tapety w swoim szablonie, zarówno dla Reacta, jak i pierwszego renderu
Django. Dołączanie do Workspace zachowuje jednolite białe tło `--bg-main`. Jasny panel formularza
ma szerokość 520px, wysokość dopasowaną do treści i jest wyśrodkowany pionowo
po prawej stronie. Korzysta z `--card-bg`, `--border-color` i `--shadow-lg`.
Panel jest w pełni kryjący i nie rozmywa tła. Pola mają pełne białe wypełnienie `--card-bg`
i wyraźniejsze szare obramowanie (80% `--system-interaction` z `--card-bg`).
Hover i fokus zachowują `--system-interaction`, a fokus dodatkowy obrys 1px.
Wariant zachowuje szare teksty `--text-primary`
i neutralne interakcje `--system-interaction`. Przycisk ma lokalny wariant
`--primary-button-bg: var(--system-accent)` z białym tekstem; hover delikatnie
przyciemnia czerwień. Aktywna zakładka ma czerwone podkreślenie.
Powłoka ma `color-scheme: light`. Znak Ancore używa oryginalnej grafiki
`logo.png`, dopasowanej przez `contain` do pola 24×24px, bez maskowania
i przycinania. Odstęp od napisu wynosi 8px, a napis ma 18px i odstęp liter
0.04em. Wspólna powłoka i favicon również korzystają z tego pliku; logo
w nawigacji zachowuje proporcje bez dodatkowego powiększania.
Logo Ancore pozostaje w lewym górnym rogu.
Wariant `auth-tabs` przełącza zwykłymi linkami „Rejestrację” i „Logowanie”.
Napisy zakładek mają rozmiar 18px, z zachowaniem odstępu 24px między nimi.
Aktywny adres ma `aria-current="page"` i czerwone podkreślenie. Nad zakładkami
jest widoczny nagłówek „Witaj ponownie” lub „Utwórz konto”. Pola mają widoczne
etykiety i wysokość 48px. Email ma placeholder `email@firma.pl`; pozostałe pola
nie powtarzają etykiet wewnątrz. Białe tło pól obejmuje także
przycisk podglądu hasła; reguły `:autofill`/`:-webkit-autofill` ujednolicają
kolor autouzupełnienia przeglądarki i tekstu. Imię i nazwisko
są w jednym wierszu, opcjonalne drugie imię poniżej; hasła są ułożone pionowo.
Formularze kont nie wyświetlają dopisku o bibliotece ikon. Panel zachowuje
lokalny Atlassian Sans i ikony UIcons, podgląd hasła,
stany błędu/zapisu oraz fokus klawiatury. Do 760px zajmuje szerokość
ekranu pod logo; do 380px również imię i nazwisko układają się pionowo.
Na niskim ekranie formularz i błędy przewijają się razem z panelem.
Pierwszy render Django zachowuje ten sam układ i formularze POST.
`auth.js` pomija korzeń Reacta, więc przycisk hasła ma jedną obsługę.
Błędy formularza są ogłaszane i otrzymują fokus; pola zachowują wpisany szkic.

Po utworzeniu konta ekran „Utwórz Workspace” używa tej samej tapety i białej karty
co logowanie. Nagłówek nie ma dodatkowego opisu. Jedno wymagane pole nazwy
ma limit 140 znaków; przycisk
„Utwórz Workspace” pokazuje rzeczywisty stan zapisu „Przygotowywanie Workspace…”.
Sukces otwiera nowe środowisko. Pod przyciskiem wiersz „Masz już Workspace?” z linkiem „Wybierz Workspace”
otwiera osobną stronę `/accounts/workspaces/` w tej samej powłoce kont.
Ta strona pojawia się również po logowaniu, niezależnie od liczby dostępnych
Workspace i zapisanej preferencji domyślnej. Wyjątkiem jest powrót do
potwierdzenia oczekującego zaproszenia.
Strona zawiera listę miejsc pracy dostępnych dla konta, bez formularza tworzenia,
oraz dwa zwarte wiersze: „Chcesz utworzyć kolejny Workspace? Utwórz Workspace”
i „Nie widzisz swojego Workspace? Wyloguj się i zmień konto”. Druga akcja
jest przyciskiem formularza POST wylogowania z CSRF; dopiero po wylogowaniu
otwiera ekran logowania. Sesja przeglądarki obsługuje jedno konto.
Wariant `auth-footer--workspace` ma tekst 13px, interlinię 1.4, bez dodatkowych
odstępów między wierszami. Opisy są przygaszone; linki mają kolor głównego tekstu
i podkreślenie dopiero przy najechaniu. Zachowują wspólny fokus klawiatury.
Wiersze nie mają obramowań i pokazują wspólny awatar Workspace (własne zdjęcie,
wybraną ilustrację albo stabilny motyw automatyczny) w rozmiarze katalogu Workspace.
Nazwa i strzałka zachowują neutralny hover/fokus; dłuższa lista ma własne przewijanie.
Pusta lista wyświetla „Brak dostępnych Workspace.”. Wybór wysyła standardowy
POST z CSRF do przełącznika Workspace i otwiera jego „Dla ciebie”. Ten sam
układ i działanie zachowuje pierwszy render Django bez JavaScriptu.
Publiczny ekran linku do dołączenia korzysta z tej samej powłoki: nazwa
Workspace, rola, logowanie/rejestracja i potwierdzenie przez POST albo komunikat
niedostępnego linku. Link nie jest przypisany do adresu e-mail. GET nie nadaje dostępu.

Profil zachowuje wspólną powłokę szczegółów i przycisk „Edytuj profil”
w nagłówku. Treść jest wyśrodkowana, ograniczona tokenem `--page-max-width`
i przewija się jako całość w `profile-overview`. Sekcja otwierająca łączy
baner, częściowo zachodzący na jego dolną krawędź awatar, nazwę, ID Ancore,
status obecności i stanowisko. Kliknięcie awatara otwiera jego edytor;
brak stanowiska udostępnia akcję „Dodaj stanowisko”.

Nad awatarem znajduje się osobisty baner z przyciskiem „Zmień baner”.
Bez własnego obrazu wykorzystuje lokalną grafikę
`static/img/auth/wallpaper-fluent-bloom-light-4k.webp`, zachowaną wyłącznie
jako domyślny baner osobisty. [Pochodzenie i prompt](../static/img/auth/README.md).
Baner
i kadr w edytorze mają proporcje 4:1; `object-fit: cover`, pozycja i skala
pokazują zapisany kadr bez zmieniania przesłanego pliku. Domyślnie obraz
jest wyśrodkowany bez dodatkowego powiększenia. Zalecany rozmiar obrazu
to 1600 × 400 px.
Osobny `BannerEditor` otwiera wspólny `Modal` w dużej powłoce edytora zdjęcia
awatara: panel pływa pośrodku ekranu, a pole z szachownicą zawiera prostokątny
kadr 4:1 z obrysem i przyciemnionym otoczeniem. Bez własnego obrazu i po
„Usuń” pokazuje pusty podgląd „Wybierz baner użytkownika”. Stopka zawiera
„Usuń”, „Zmień” i „Zapisz”. „Zmień” otwiera ukryty wybór pliku przyjmujący
PNG, JPG i WebP do 5 MB. Własny lub nowo wybrany obraz można przeciągać
w podglądzie; stale widoczne suwak „Powiększenie obrazu” oraz przyciski
minus/plus („Pomniejsz obraz” i „Powiększ obraz”) zmieniają skalę od 100%
do 300%. Kadrowanie i powiększenie są nieaktywne bez odczytanego obrazu,
przy błędzie pliku i podczas zapisu. Podgląd „Kadr banera” obsługuje też strzałki klawiatury,
a Shift zwiększa krok przesuwania. Pozycja pozostaje w granicach obrazu.
Kontrolki powiększenia używają istniejących klas `profile-photo-zoom-controls`
z edytora awatara. Zmiana zaczyna obowiązywać po „Zapisz”, także gdy edytowany
jest tylko kadr istniejącego obrazu. Przycisk zapisu jest nieaktywny bez zmian.
„Usuń” zmienia wyłącznie szkic: opróżnia podgląd, a dopiero „Zapisz”
usuwa własny baner i przywraca na profilu domyślną grafikę, środek kadru
i powiększenie 100%. Usunięcie nowo wybranego pliku przy braku zapisanego
banera pozostawia profil bez zmian. Zamknięcie edytora zachowuje zapisany obraz.
Błędy formatu, rozmiaru i odczytu obrazu blokują zapis; błąd serwera zachowuje
wybrany plik, pozycję, powiększenie i podgląd.
Modal zachowuje fokus, Escape, potwierdzenie odrzucenia szkicu i blokadę
kontrolek, w tym wyboru pliku, podczas zapisu. Pierwszy render Django udostępnia pod „Zmień baner”
rozwijany, natywny formularz z CSRF, działający bez JavaScriptu. Oprócz uploadu
i resetu zawiera pola „Pozycja pozioma (%)”, „Pozycja pionowa (%)” oraz
„Powiększenie”, z tą samą walidacją zakresów co API. Ten formularz i kontrakt
API zachowują dotychczasowe działanie.

Pod banerem i danymi użytkownika `profile-details-grid` ma dwie kolumny.
Lewa zawiera „O mnie”, opcjonalną kartę „Uzupełnij swój profil” oraz informację,
że dane są wspólne dla Workspace użytkownika. Pusty opis pokazuje „Daj się
poznać” i przycisk „Dodaj opis”. Sugestie dotyczą wyłącznie brakującego opisu,
stanowiska i telefonu; licznik wskazuje liczbę uzupełnionych pól z trzech.
Po uzupełnieniu wszystkich karta znika. Akcje Reacta otwierają wspólny edytor
z fokusem na odpowiednim polu; natywny pierwszy render otwiera formularz
przez istniejący adapter `profile.js`.

Prawa kolumna dzieli dane na „Dane kontaktowe” i „Konto i aktywność”.
Obie sekcje zachowują obrys, zaokrąglenie, cień i odstępy panelu zadania
ze wspólnej reguły `tasks.css`. Karta kończy się na ostatniej sekcji i przewija
razem z pozostałą treścią. Do 800px kolumny układają się jedna pod drugą.
E-mail i telefon są linkami `mailto:` i `tel:`. React dodaje kopiowanie
e-maila, ID Ancore i telefonu: sukces zmienia ikonę i ogłasza potwierdzenie,
a błąd wyświetla komunikat z możliwością ręcznego skopiowania tekstu.
Brak telefonu udostępnia akcję dodania numeru. Sekcja konta pokazuje zmianę
statusu, dostęp, „Rolę w aplikacji”, datę dołączenia i ostatnie logowanie.
Profil nie zawiera sekcji „Konta w sesji” ani akcji dodawania, przełączania
i usuwania kont z sesji. Zmiana tożsamości odbywa się przez wylogowanie
i ponowne logowanie.
Warianty `profile-overview`, `profile-hero`, `profile-details-grid`
i `profile-edit-avatar` w `profile.css` korzystają ze wspólnych tokenów,
kontrolek i awatarów. Układ mobilny zachowuje pełne dane kontaktowe
oraz wspólne przewijanie treści profilu.
React renderuje formularz edycji we
wspólnym `Modal` z klasami `profile-edit-overlay`, `profile-edit-dialog`
oraz `profile-edit-form`. Zachowuje Escape, fokus, inert, błędy i potwierdzenie
odrzucenia zmian. Imię i nazwisko są obok siebie, opcjonalne drugie imię
poniżej. Zapis jest nieaktywny do pierwszej zmiany. Natywny sygnał `change`
wspólnego pickera awatara także oznacza formularz jako zmieniony, umożliwiając
zapis samego awatara i potwierdzenie odrzucenia takiego szkicu.
`FieldLabel` udostępnia oznaczenia wymaganych pól i pomoc ID Ancore.
Błędy pojawiają się przy polach, statusie i awatarze oraz w podsumowaniu
otrzymującym fokus. Podczas zapisu zablokowany jest również wybór awatara;
błąd nie resetuje szkicu ani wybranego obrazu. Pierwszy render Django
zachowuje układ i pomoc pól. Wybór statusu korzysta ze wspólnego dropdownu i menu z
zaznaczeniem aktualnej opcji, obsługiwanego również klawiaturą.

`shared/AvatarControl.tsx` jest wspólnym adapterem istniejącego pickera i
kadrowania. W profilu używa puli 30 zwierzęcych ilustracji, klas
`user-avatar-art` i pól `profile_photo*`; w Workspace zachowuje osobne
ilustracje, klasy i pola `workplace_photo*`. Zagnieżdżony picker i canvas
mają własny cykl życia. Minimalne adaptery `react.css` zachowują przepływ
kontenera awatara i wielowierszowe bio. Nie dodano nowego systemu stylów.

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
wierszy. Korzystają z niego katalog/zarządzanie Przestrzeniami,
Zespoły oraz katalog/wyniki Filtrów.
Podsumowanie, oś czasu, raporty, ustawienia i szczegóły zadania nie pokazują tego paska.
Tagi przestrzeni korzystają z paska „Pokaż więcej” pod tabelą.

Tablica Przestrzeni nie pokazuje dolnego paska z zakresem i numerami stron,
również w pierwszym renderze Django. Wczytuje wszystkie dostępne zadania
pasujące do filtrów, bez podziału po 100 wyników; karty przewijają się
w dotychczasowych kolumnach. Nagłówki statusów zachowują liczniki.

Pod kartami każdej kolumny jest „Utwórz zadanie” z ikoną plusa, również
w pustej kolumnie. Puste kolumny nie wyświetlają ramki ani komunikatu
„Brak zadań”, zarówno w React, jak i pierwszym renderze Django.
Wariant `work-board-create` używa istniejącego
`tasks-project-menu-button`, zachowuje szare interakcje i nie kurczy się
w przewijanej kolumnie. Otwiera wspólny modal z wybranym statusem; jego
nazwa dostępności zawiera nazwę kolumny. W czasie odczytu jest wyłączony,
a obserwator go nie widzi. `aria-disabled` i blokada ponownego żądania
zachowują fokus przycisku, dzięki czemu Escape wraca do tej samej kolumny.
W Scrum akcja wymaga aktywnego sprintu.
Pierwszy render Django zachowuje ten sam wygląd i adres formularza.

Lista zadań otwartej Przestrzeni ładuje osobno po 20 pozycji w każdym statusie.
Wiersze nie pokazują przycisku trzech kresek ani menu działań i nie rezerwują
na nie osobnej kolumny. Dotyczy to Reacta oraz pierwszego renderu Django.
Tytuł nadal otwiera zadanie, a checkbox służy do zaznaczania. Backlog
również nie renderuje tego menu ani jego kolumny.
Nagłówek grupy pokazuje pełną liczbę dostępnych wyników po filtrowaniu.
Pod wierszami jest pełnej szerokości, wyśrodkowany pasek „Pokaż więcej (20 / 21)”.
Wariant `work-list-more` rozszerza `tasks-filter-button` w `spaces.css`:
wysokość co najmniej 40px (44px dla dotyku), górna ramka, neutralne tło,
szare interakcje i licznik o mniejszym kryciu. Odczyt pokazuje „Wczytywanie…”,
błąd pozostawia zadania i pozwala ponowić tym samym przyciskiem.
Po ostatniej partii pasek zmienia się w „Wszystkie zadania (21 / 21)”;
małe grupy mieszczące się w pierwszej partii nie potrzebują paska.
Na telefonie wariant `work-item-list--incremental` przewija poziomo same
wiersze; nagłówek i pasek doładowania pozostają w szerokości widocznej grupy.
React zachowuje pozycję przewijania, zaznaczenia nadal dostępnych zadań
i zwinięcia grup podczas doładowania. Zmiana filtrów/sortowania zaczyna od
20 pozycji. Lista nie ma dolnego paska numerów stron. Pierwszy render
`spaces/task_list.html` zachowuje wygląd i zwykłe linki do rozszerzonej listy.

Backlog korzysta z tego samego paska `work-list-more`, wspólnej obsługi
Reacta i szablonu `spaces/load_more.html`. Każdy otwarty sprint i sekcja
Backlog wczytują niezależnie po 20 pozycji; ich nagłówki pokazują pełną liczbę
nieukończonych zadań po filtrach. Pasek jest pod wierszami i akcją tworzenia,
poza poziomym przewijaniem wierszy, także na telefonie. Doładowanie zachowuje
zaznaczenia, zwinięcia sekcji i pozycję przewijania; filtry i sortowanie
resetują zakres. Backlog nie pokazuje dolnego paska numerów stron ani tekstu
„Na stronie”. Sprint zawierający wyłącznie ukończone zadania pokazuje
„Wszystkie zadania w tym sprincie są ukończone.”.

## Kolejność identyfikacji zadania

Wiersze i karty zadań zachowują kolejność: priorytet → klucz (np. `HELP-24`)
→ stan → tytuł. Dotyczy to Listy zadań, Backlogu, Tablicy, Osi czasu,
„Dla ciebie”, wyników Filtrów, zadań Zespołu i Podzadań. Klucz ma osobny
tor siatki o szerokości treści i pozostaje klikalny tak jak tytuł; w Podzadaniach
otwiera dotychczasowy modal edycji, z zachowaniem uprawnień.
React i wspólne szablony Django `spaces/row.html` oraz `spaces/card.html`
zachowują tę samą kolejność. Kolory, ikony i metadane pozostają wspólne.

## Wspólny pasek widoków Przestrzeni

Podsumowanie, Lista zadań, Tablica, Backlog, Oś czasu, Raporty i Tagi
korzystają z `spaces/ViewToolbar.tsx`, adaptera wspólnego `Toolbar`.
Pierwszy render Django używa tych samych klas `app-toolbar` i slotów.
Wymiary oraz odstępy określają `--app-toolbar-*` i `components/app-toolbar.css`,
zgodnie z [dolnym paskiem Zasobów](#wspólny-dolny-pasek-narzędzi--wzorzec-zasobów).

Po lewej znajdują się „Filtruj” i „Sortuj” (jeśli dany widok je obsługuje),
dodatkowe kontrolki widoku oraz wyszukiwanie; działania znajdują się po prawej.
Kolejność wizualna odpowiada kolejności klawiatury. Tagi zachowują wyszukiwanie
po 350ms od wpisania tekstu, a Oś czasu po zatwierdzeniu. Na małych ekranach
grupy zawijają się, a wyszukiwarka zajmuje cały wiersz; działania zachowują
wyrównanie do prawej.

Raporty mają pasek nad nagłówkiem, z filtrowaniem, okresem, sprintem
(w Scrum) i wykonawcą po lewej oraz odświeżaniem i eksportem po prawej.
Etykiety selektorów pozostają dostępne dla czytników ekranu.
Przełączniki skali Osi czasu zachowują wspólny segment i aktywny stan.
Zakres danych, uprawnienia oraz sposób zapisu filtrów pozostają bez zmian.

## Raporty Przestrzeni

Zakładka Raporty zachowuje nagłówek i nawigację Przestrzeni. Lokalny wariant
`work-reports` w `spaces.css` rozszerza istniejące panele, przyciski,
selektory, awatary i tabele. Nie wprowadza biblioteki wykresów ani nowych
tokenów kolorystycznych. Bieżące wskaźniki są oddzielone od aktywności
w wybranym okresie; opis zakresu obejmuje także podzadania.

Wykres utworzeń i ostatnich zakończeń ma legendę, odróżnione linie oraz
przełącznik równoważnej tabeli. Rozkłady statusów i priorytetów oraz
wykonawcy i sprinty pozwalają zawęzić raport, zachowując pozostałe filtry.
Zadania po terminie mają odnośniki do szczegółów. Eksport opisuje bieżący
zakres zadań. Pusty wynik i niedostępny sprint mają własne komunikaty
oraz możliwość wyczyszczenia filtrów. Na telefonie panele układają się
w jednej kolumnie, a szerokie tabele przewijają się we własnym kontenerze.

## Oś czasu Przestrzeni

`spaces/TimelineView.tsx` rozszerza istniejący ekran o tabelę i wspólną siatkę
kalendarza. Kontrolki, ikony, awatary i kolory statusów pochodzą ze wspólnych
komponentów; lokalne reguły `work-timeline-*` są w `spaces.css`. Nagłówek
kalendarza pozostaje widoczny przy przewijaniu pionowym, a kolumna zadań
przy poziomym. Lista zadań tworzy jeden pływający panel z obrysem,
cieniem `--shadow-md` i narożnikami `--radius` (8px) na początku i końcu.
Od siatki oddziela ją 5px odstępu (na telefonie 4px). Sprinty są częścią
tej samej powierzchni. Tła podświetlenia i separatory mieszczą się w panelu;
wysokość wierszy i wyrównanie z paskami kalendarza pozostają bez zmian.
Jeden ciągły pasek dat obejmuje całą szerokość tabeli,
również nad przypiętymi zadaniami. Zachowuje poziomy miesiąca/roku i dni/okresów;
nie ma wydzielonego pola zakresu, napisu „Praca” ani licznika. Wcześniejsze
daty wypełniają część nad zadaniami, a daty nad kalendarzem pozostają wyrównane
z paskami. Nagłówek przewija się poziomo razem z kalendarzem; etykieta
miesiąca/roku utrzymuje się przy lewej krawędzi w granicach swojego okresu.
Wspólna komórka ma nazwę „Zadania i kalendarz” dla czytników ekranu;
statyczny pierwszy render Django ma osobne kolumny i ukrytą nazwę „Zadania”.
Kompaktowy `TimelineItemRow` z `spaces/Item.tsx` współdzieli
z Listą zadań priorytet, klucz, wskaźnik statusu, tytuł i awatar wykonawcy.
Obok awatara pokazuje imię i nazwisko z `assignee.label` (lub e-mail, gdy
profil nie ma nazwy); brak przypisania opisuje „Nie przypisano”. Wariant
`work-backlog-assignee--named` zachowuje wspólny awatar, skraca długi tekst
wielokropkiem i udostępnia całą nazwę w podpowiedzi.
Nie renderuje zaznaczenia, typu, estymacji, liczników tagów/załączników,
ikony terminu ani menu działań. Nie ma osobnej kolumny Wykonawca ani Status.
Kategorie nadal określają kolory pasków; kliknięcie tytułu otwiera szczegóły
zadania. Wiersze zachowują uprawnienia i bieżące sortowanie osi.
Tygodnie pokazują dni i przygaszone weekendy;
miesiące i kwartały rzeczywiste granice okresów. Linia i znacznik bieżącego
dnia używają czerwonego akcentu. Pasy sprintów mają obrys, a paski zadań
wypełnienie `--tasks-status-background`, takie jak nagłówki grup Listy zadań,
z delikatnym obrysem kategorii; pojedyncza data ma przerywany obrys.
Wiersze mają 40px wysokości. Najechanie, fokus i wybrany wiersz korzystają
z tego samego 8% tła akcentu i znacznika 3px przy lewej krawędzi co Lista zadań.
Siatka kalendarza jest lżejsza od poziomych separatorów. Znacznik dzisiaj
oraz dymek przeciągania ustawiają `--app-text-color`, zachowując biały tekst
również przy globalnych regułach typografii. Kontrolki mają widoczny fokus klawiatury.

Wyszukiwanie działa po zatwierdzeniu Enterem lub przyciskiem i obejmuje cały
przefiltrowany zbiór. Zachowano menu Sortowanie/Filtrowanie. Oś wczytuje początkowo
20 zadań. Pod wierszami jest wspólny pasek `work-list-more` z „Pokaż więcej”
i licznikiem wczytanych oraz wszystkich dostępnych wyników po filtrach.
Każde kliknięcie doładowuje kolejne 20; końcowa partia pokazuje „Wszystkie zadania”.
Małe i puste wyniki nie potrzebują paska. Wariant `work-timeline-results`
stosuje ten sam wygląd co Lista zadań, również w pierwszym renderze Django.
Pasek pozostaje w widocznej szerokości podczas poziomego przewijania kalendarza.
Doładowanie zachowuje skalę i przewinięcie; błąd pozostawia zadania i umożliwia
ponowienie. Odczyt i zapis dat wzajemnie blokują swoje kontrolki. Wyszukiwanie,
filtry i sortowanie resetują zakres do 20 pozycji. Nie ma
dolnego paska paginacji, legendy „Dzisiaj” ani widocznej podpowiedzi przeciągania.
Linia bieżącego dnia i pomoc dla czytników ekranu pozostają w kalendarzu.
„Dzisiaj” i trzy przełączniki skali tworzą jeden `tasks-segments` w wariancie
`work-timeline-scales`: jedna wspólna zaokrąglona ramka, bez odstępów między
segmentami, z pojedynczymi pionowymi separatorami i szarym tłem aktywnej skali
oraz najechania. Tylko zewnętrzne narożniki są zaokrąglone. Całość zachowuje
wysokość `--app-toolbar-control-height`, a fokus każdego przycisku pozostaje
widoczny. Reguły wariantu są w `components/app-toolbar.css`.
Cała grupa należy do prawego obszaru
działań paska (`ItemToolbar.actions`); filtry, sortowanie i wyszukiwarka
pozostają po lewej. Przy braku miejsca grupa przechodzi razem do kolejnego
wiersza, zachowując wyrównanie do prawej. Grupa ma nazwę „Nawigacja osi czasu”; tylko skale
używają `aria-pressed`. Przycisk „Dzisiaj” przewija kalendarz do bieżącego dnia, zachowując
wybraną skalę. Działa także po ręcznym przewinięciu osi i jest wyłączony podczas zapisu.
Nie ma licznika „Zaplanowane”,
przycisku „Dopasuj”, strzałek okresu ani osobnej nazwy miesiąca. Zakres można
przewijać poziomo, a daty odczytać z nagłówków kalendarza.
Niezaplanowany wiersz ma „Zaplanuj zadanie”; data poza oknem przycisk powrotu
do jej okresu. Kliknięcie paska otwiera wspólny kompaktowy
`Modal` z polami dat i godzin rozpoczęcia oraz zakończenia, zakresem dni
na osi, usunięciem dat i ochroną szkicu. Oba pola używają `datetime-local`
i tej samej strefy czasu co szczegóły zadania. Walidacja uwzględnia godziny,
również gdy początek i koniec wypadają tego samego dnia. Przesuwanie oraz
rozciąganie paska zachowuje zapisane godziny obu końców.
Przeciąganie oraz skróty klawiatury mają alternatywę w formularzu.
Błąd nie zmienia zapisanych dat; formularz zachowuje wpisane wartości.

Kolumna zadań ma 560px, w tym 160px na wykonawcę; do 1000px zwęża się do
430px z 130px na wykonawcę, a do 650px do 190px. Na telefonie klucz i tytuł
zajmują pierwszy wiersz, a awatar 16px i nazwa wykonawcy drugi. Priorytet
i status obejmują oba wiersze; wysokość całego wiersza tabeli pozostaje 40px.
Wiersze pozostają przypięte, a daty przewijają się wewnątrz tabeli. Wspólny pasek
„Dzisiaj” i skali mieści się w obrębie telefonu. Pełne właściwości zadania pozostają dostępne
po otwarciu jego szczegółów. Pusty wynik korzysta ze wspólnego `EmptyState`.
Pierwszy render Django w `spaces/timeline.html` ma statyczną tabelę dat,
wykonawców z linkiem edycji; interaktywny kalendarz wymaga Reacta.

## Wspólny wzorzec pustej strony

Puste strony używają wyglądu pustego pulpitu. Wspólny wariant
`tasks-empty-state--illustrated` w `components/tasks.css` określa ilustrację
w polu 440×330px, odstęp 20px przed tekstem, nagłówek 28px/700 (24px do 767px),
opis 16px z interlinią 1.6 oraz odstępy 16px w bloku tekstu o maksymalnej
szerokości 640px. Całość jest wyśrodkowana w dostępnej treści, z paddingiem
24px; obraz maleje do szerokości kontenera, a niskie widoki pozwalają przewijać
cały komunikat. Typografia pulpitu pochodzi z tego samego wariantu.

`frontend/app/src/shared/EmptyState.tsx` udostępnia nagłówek i opis,
z dekoracyjnym obrazem `src` lub istniejącą ilustracją wskazaną wariantem
CSS (`spaces`, `tasks`, `people`, `work`). Tło ilustracji jest przezroczyste,
a element jest pomijany przez czytnik ekranu; kontener ma `role="status"`.
Adresy grafik w CSS pozostają względne wobec arkusza zasobów statycznych.
Szablony Django zachowują ten sam kontrakt klas i grafik.

Wzorzec obejmuje katalogi i zarządzanie Przestrzeniami, Pulpitami i Filtrami,
pusty pulpit, Zasoby, Tagi przestrzeni, listy i wyszukiwanie zadań, oś czasu,
Zespoły, Dysk (dyski, foldery, kosz, ulubione), Dokumenty (także szablony),
katalog Workspace i pustą tabelę członków. Puste rekomendowane
przestrzenie oraz główny pusty wynik zakładki „Dla ciebie” korzystają z niego
z własną ilustracją. Puste stany nie zawierają
przycisków ani linków akcji, również w rekomendowanych przestrzeniach,
kolumnach gadżetów i pustym katalogu gadżetów. Tworzenie, przeglądanie
i filtrowanie pozostają dostępne w nagłówkach, nawigacji i toolbarach;
przyciski ponowienia po błędzie zachowują swoje działanie. Małe sekcje
podsumowań, kolumny tablic, listy powiadomień i pickerów oraz stany wczytywania
zachowują kompaktowy układ. Puste Dokumenty przewijają również kafelki tworzenia,
aby opis pozostał dostępny na niskim ekranie.

## Filtry zadań

Szablony dashboard/filters rozszerzają spaces/base i core/base.
Katalog używa wspólnych zakładek notifications-tabs/work-tabs
oraz tabeli tasks-directory-sheet bez hamburgera i jego kolumny. Wariant
task-filter-directory określa kolumny katalogu; ich szerokości mają
osobny klucz ustawień w tasks.js. Wyniki w „Wyszukaj zadania” i zapisanych
filtrach korzystają z spaces/item_list.html i spaces/row.html: kolorowych
grup statusów, zwijania oraz wierszy z checkboxem, priorytetem, kluczem,
statusem, tytułem, typem, licznikami tagów/załączników i oznaczeniem terminu.
Grupy obejmują wczytane okno wyników, a sortowanie zachowuje kolejność
zadań wewnątrz grup. Wyniki nie używają tabeli z nagłówkami kolumn.

Osobny ekran „Zarządzaj filtrami”, jego wariant menu i wejścia w Ustawieniach,
nagłówku Filtrów, wyszukiwaniu oraz zwiniętym menu są usunięte. Stare zwykłe/scoped
`filters/manage/` prowadzą do zakładki „Moje filtry” w katalogu; zachowują
poprawną zakładkę, wyszukiwanie i numer strony. Katalog ma jeden wariant
`task-filter-directory`, z gwiazdką w pierwszej kolumnie, nazwą otwierającą
wyniki. Nie dodano zastępstwa dla usuniętych akcji menu. Szerokości używają
klucza `task-filters-directory`. Starsze adresy formularzy korzystają z modali
nad zwykłym katalogiem i zachowują menu Workspace. Ustawienia Workspace
zachowują własny ekran zarządzania; dawny wspólny `management_sidebar.html`
nie ma już odbiorców i został usunięty.

Pusty katalog Filtrów, również przy braku pasujących wyników,
używają wspólnego wariantu `tasks-empty-state--illustrated` z dekoracyjną
ilustracją `static/img/empty-states/filters-empty.webp`: pastelowym lejkiem,
kolorowymi znacznikami i kartami wyszukiwania. Obraz ma przezroczyste tło,
pole 440×330px i skaluje się do szerokości kontenera. Cały pusty stan jest
wyśrodkowany w dostępnej treści. React otrzymuje adres przez Django `static`,
a szablon zgodności korzysta z tej samej ilustracji. Teksty zależne
od zakładki lub kryteriów pozostają zachowane; akcje są poza pustym stanem.

Podstawowe pola korzystają z AncoreCustomSelect, tekstowego wyszukiwania
i istniejących przycisków. Nagłówek wyników łączy tytuł, działania i zakładki
trybu w `work-space-header`, z jedną dolną ramką, jak w otwartej Przestrzeni.
Wspólny `work-content--items` wyrównuje pasek i listę. Pasek podstawowy
(`filters/SearchToolbar.tsx`) ma menu „Sortowanie” i „Filtrowanie” z istniejącego
wzorca `tasks-project-query-*` oraz licznik wyników w tym samym wierszu.
Panel filtrów zachowuje wszystkie pola i wielokrotny wybór, przewijaną treść
oraz stale dostępną stopkę „Szukaj”; aktywne kryteria oznacza licznik przy menu.
Zmiana sortowania zachowuje bieżące warunki, a „Wyczyść” korzysta z dotychczasowego
adresu. Pierwszy render Django używa tego samego układu i formularza GET
z menu `details`. Zaawansowany tryb ma pole zapytania i pomoc
ze składnią. Tworzenie i ustawienia filtra używają dużego wspólnego `app-modal-panel`,
z zakładkami `notifications-tabs` „Ustawienia” i „Udostępnienia”.
Powłokę renderuje `filters/SettingsDialog.tsx`; `EmbeddedForm` zachowuje szkic
nazwy, opisu, warunków i widoczności, a fieldset korzysta z `display: contents`
bez dodatkowej widocznej ramki. Pola na desktopie używają istniejących wierszy
etykieta/kontrolka; na telefonie układają się pionowo.

Udostępnienia używają tych samych `shared/Members`, `shared/SharingDialog`
i stylów `workplace-team.css` co Przestrzenie. Właściciel jest chroniony;
pozostałe wiersze mają awatar, e-mail, rolę i datę. Menu zmiany roli
i odebrania dostępu jest usunięte bez zastępczego wejścia. Istniejący przycisk
udostępnienia otwiera picker aktywnych osób Workspace i kompaktowy dialog
nadania roli. Zapis działa od razu, z obsługą błędu i ponowienia, zachowując
szkic ustawień i kontrolę rewizji. Backend zachowuje kontrolę pozostałych operacji.
Przy widoczności Workspace tabela pokazuje dziedziczenie bez przycisku
udostępnienia. Przed utworzeniem filtra zakładka wyjaśnia potrzebę pierwszego
zapisu; po nim to samo okno przechodzi do tabeli osób. Zapis ustawień także
pozostawia okno otwarte. Zakładki obsługują strzałki, Home i End.
Formularz zapisu/edycji korzysta z AncoreTaskModals:
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

W przeniesionych ekranach powyższy układ i klasy renderują komponenty
`frontend/app/src/filters`. `task-filters.js` pomija korzeń Reacta;
stan formularza, walidację i modal obsługuje React z `AncoreTaskModals`.
Przycisk „+” Filtrów oraz „Utwórz filtr” w zwiniętym menu otwierają formularz
przez wspólny `openForm`. Adres `create_url` prowadzi do `new/`, a osobny
`task_search_url` zachowuje skrót „Wyszukaj zadania”; `search_url` pozostaje
adresem wyszukiwania definicji w pickerze.
Pola wyszukiwania korzystają z wariantu `FieldControl` bez stylu właściwości
szczegółów zadania, zachowując dotychczasowe obramowania i ikony wyboru.
Menu boczne, gwiazdki i pickery renderuje teraz `src/shell`; dawny
`filter-navigation.js` pozostaje wyłącznie dla zgodności.

Stary moduł Tablice Kanban jest wycofany. Pozostałe opisy jego modeli,
szablonów i wspólnych komponentów są referencją historyczną; nie oznaczają
aktywnych ekranów ani endpointów. Obecne tablice Przestrzeni używają `spaces.SpaceTask`.
[Szczegóły wycofania](MODULES.md#4-wycofany-moduł-tablice-kanban).

## Przestrzenie i zespoły

Nazwy typów i etapów w tabelach ustawień oraz nazwy etapów na mapie używają
`tasks-project-value-badge--tag-visual`: pastelowego tła o 16% udziału
wybranego koloru i ciemnego tekstu, jak kolumna „Kolor / ikona” Tagów.
Ikona i nazwa są we wspólnej etykiecie; długie nazwy skraca wielokropek.
Bezpośrednia ikona SVG etykiety `tasks-project-value-badge--tag-visual`
ma 16×16px i stały udział 16px w układzie flex również poza komórką Tagów.
Dzięki temu nazwy typów i etapów mają tę samą wysokość co etykiety Tagów;
nie dziedziczą domyślnej ikony 24px.
`work-configuration-badge-label` i ograniczenie szerokości w `spaces.css`
chronią układ tabeli. Pole „Kolor nazwy” wykorzystuje `documents-color-control`
i `documents-color-input`, kod HEX, przycisk „Domyślny” oraz podgląd.
Minimalny wariant `work-configuration-color` ogranicza szerokość pola HEX;
kontrolki zawijają się na wąskim ekranie. Domyślne barwy pochodzą z istniejącej
palety ikon typów i stanów; własny kolor jest niezależny od wybranej ikony.
Kolor etapu w ustawieniach jest źródłem wyglądu w całej Przestrzeni.
`shared/status-color.ts` oraz filtr Django `status_style` przekazują wspólne
zmienne `--tasks-status-color`, `--tasks-status-background` (16% koloru)
i `--tasks-status-border` (30% koloru). Lista i tablica mają takie samo tło
nagłówka jak etykieta ustawień; ikony zadań i przejść używają pełnego koloru.
Oś czasu i wykresy korzystają z tych samych zmiennych, zachowując swoje
istniejące proporcje mieszania. Nagłówki sprintów nadal określają stan sprintu.


Proces pracy ma podzakładki „Stany” i „Mapa” w drugim wierszu wspólnego
nagłówka Przestrzeni, przed paskiem działań. Korzystają z `notifications-tabs work-tabs work-tabs--views`,
jak widoki Przestrzeni: ikony `list-checks` i `workflow`, tekst 13,5px,
czerwone podkreślenie aktywnej pozycji i przewijanie poziome na telefonie.
W React przyciski mają role `tablist`/`tab`/`tabpanel`, `aria-selected`
oraz obsługę strzałek, Home i End; pierwszy render Django używa linków
z `aria-current="page"`. Domyślnie wybrane są „Stany”.

„Stany” pokazują istniejącą `ConfigurationTable` z zaznaczeniami i paskiem
„Edytuj”, „Usuń”, „Dodaj stan” po prawej. Lista nie pokazuje dodatkowej pary
„Zapisz” / „Anuluj”; zapis i odrzucenie całego procesu są dostępne na „Mapie”.
Przy niezapisanych zmianach lista wskazuje tę zakładkę w komunikacie.
Nazwa otwiera wspólny formularz etapu. Lista i mapa współdzielą szkic oraz
historię; przełączanie nie zapisuje ani nie odrzuca zmian. Wybór podzakładki
pozostaje po zapisie i przejściu do innej sekcji ustawień, bez zmiany adresu Reacta.
Natywny widok przekazuje wybór przez `workflow_view=states|map`.

Dodawanie i edycja etapu używają wariantu `work-type-form`, tak jak okno
„Dodaj typ zgłoszenia”: podgląd ikony 100px z „Zmień” po lewej, pełna szerokość
nazwy i opisu zasad po prawej, a poniżej klucz i WIP w dwóch kolumnach.
Na telefonie pola przechodzą pod ikonę. Wspólny `ConfigurationIcon` zachowuje
siatkę ikon, wyszukiwanie, pusty wynik, klawiaturę i powrót fokusu.
Etapy mają osobny katalog 16 ikon statusów (m.in. kolejka, oczekiwanie,
blokada i zakończenie), z podpisem „Ikony statusów”. Typy zgłoszeń nadal
korzystają ze swojego zestawu 24 ikon. Zapisana wcześniej ikona typu pozostaje
dostępna wyłącznie przy jej etapie jako „Dotychczasowa ikona”.
Pole klucza jest zawsze widoczne; ręczne wpisanie blokuje dalsze generowanie
z nazwy. „Stan zadania” i „Etap przepływu” są ukryte z zachowaniem danych.
WIP poza pracą w toku pozostaje tylko do odczytu, z wyjaśnieniem pod „!”.
Ikona jest widoczna przed nazwą w tabeli i na mapie. Pierwszy render Django
zachowuje ten sam układ i natywny wybór ikony rozwijany przez „Zmień”.

„Mapa” pokazuje swobodny układ węzłów i kierunkowych połączeń. Lokalny wariant
`work-flow-*` w `spaces.css` zachowuje wspólny pasek ustawień, przyciski,
ikony statusów i tokeny powierzchni. Wybrany etap ma czerwony obrys oraz
wyróżnione wejścia i wyjścia; pozostałe strzałki są przygaszone. Przy karcie
jest przycisk „+” do połączenia. Mapa zajmuje całą szerokość edytora.
Mapa nie ma panelu bocznego listy ani szczegółów, liczników, przycisku „Etapy”,
starego paska sterowania mapą ani górnego i dolnego paska wskazówek.
Sama mapa pozostaje obszarem przeciągania i skalowania.

Podwójne kliknięcie lub Enter na karcie otwiera wspólny modal edycji, z nazwą na początku.
Formularz zachowuje połączenia w ukrytych polach. Przycisk dodania pierwszego
etapu pozostaje w stanie pustym; główny przycisk „Dodaj etap” jest usunięty.
Nowa karta otrzymuje automatyczny klucz i pojawia się w środku bieżącego
widoku. Alt + strzałki przesuwają etap o 10 jednostek mapy, z Shift o 40;
układ dopuszcza współrzędne ujemne.
Łączenie rozpoczyna „+” przy źródle, a kończy kliknięcie karty celu;
Escape lub ponowne kliknięcie aktywnego „+” je anuluje. Przejścia są kierunkowe, więc powrót dodaje się osobno.
Tab odsłania etap poza kadrem; przesuwanie klawiaturą utrzymuje kartę w widoku.

Przeciąganie tła przesuwa mapę w dowolnym kierunku; nad kartami tę samą
akcję wykonuje Spacja z przeciągnięciem lub środkowy przycisk myszy.
Kółko skaluje mapę wokół kursora, Shift z kółkiem przesuwa ją poziomo.
Dotyk obsługuje przesuwanie tła jednym palcem oraz przesuwanie i skalowanie
dwoma. Przy fokusie na obszarze mapy strzałki przesuwają widok,
`+`/`−` zmieniają skalę, `0` przywraca 100%, a Home dopasowuje całość.
Escape anuluje gest. Przesunięcie i skala widoku nie zmieniają szkicu
ani historii cofania.

Minimapa w prawym dolnym rogu jest lokalną nakładką na niepustej mapie.
Pokazuje uproszczone karty i połączenia oraz ramkę widocznego obszaru.
Używa istniejących tokenów powierzchni, obramowania i czerwonego akcentu;
na telefonie ma kompaktowy rozmiar. Kliknięcie lub przeciągnięcie przesuwa
kamerę, a Escape, anulowanie wskaźnika i utrata fokusu okna cofają gest.
Przy fokusie na podglądzie strzałki przesuwają widok, a Enter, Spacja i Home
dopasowują całość. Pod podglądem są „−”, suwak skali i „+”. Suwak obejmuje
1–200%, rozszerzając dolną granicę dla dopasowania poniżej 1%.
Kontrolki minimapy zachowują fokus klawiatury i nie zmieniają danych procesu.

Pasek pokazuje stan szkicu, cofanie i ponawianie oraz „Zapisz” i „Anuluj”.
Początkowa skala ma minimum 65% dla czytelności; Home dopasowuje wszystkie
karty, również na rozległej mapie. Akcje usuwania etapów i przejść, zmiany
kolejności, automatycznego układu i „Połącz kolejno” nie mają kontrolek
na mapie; usuwanie stanów jest dostępne na liście „Stany”. Kontrolki zapisu
zawijają się na telefonie.
Ikony ostrzeżeń przy etapach nadal sygnalizują problemy grafu; nie blokują edycji.

W szczegółach zadania `TaskWorkflowStatus` zastępuje selektor statusu bieżącym
etapem, a `TaskWorkflowActions` pokazuje dozwolone przejścia. Wariant `task-workflow-*` w
`react.css` używa dotychczasowych ikon i przycisków. Bieżący etap ma wcięcie,
wysokość i tekst zgodne z sąsiednimi właściwościami, bez osobnego tła.
Przejścia zajmują osobną sekcję na górze prawego panelu, przed widocznością.
Przyciski są ułożone pionowo na całą szerokość i używają wariantu
`tasks-tag-topbar-button--row-highlight`, tak jak „Utwórz zadanie”. Mają
nazwę celu i jego ikonę `status-indicator` według kategorii stanu;
pełną akcję „Przejdź do…” opisuje etykieta dostępności.
Komunikaty zapisu i błędy statusu są przy akcjach. Zapis wyłącza przyciski;
błąd nie zmienia potwierdzonego etapu. Brak przejść i odczyt obserwatora
mają osobne stany. Pierwszy render Django zachowuje przyciski, a konfiguracja
bez JavaScriptu pokazuje wybraną listę lub karty etapów i linki do standardowych formularzy.

Tablica pokazuje pod nagłówkiem aktywnej kolumny licznik widocznego WIP
oraz limit. Zasady etapu rozwijają się w natywnym `details`; pełny limit
wyłącza przyjęcie karty i tworzenie w kolumnie. `work-board-wip`,
`work-board-policy` i `is-drop-unavailable` rozszerzają istniejący układ
kolumn bez nowej palety. Licznik WIP nie zmienia się po filtrowaniu tablicy.
Karta ma opcjonalny panel `work-card-blocked` z powodem, osobą odpowiedzialną
i czasem blokady oraz `work-card-age` z czasem w etapie. Lista i oś czasu
używają małej ikony blokady przy tytule, zachowując siatkę kolumn.
„Blokada” we wspólnym filtrze pozwala wyświetlić zablokowane zadania.
Menu karty otwiera standardowe kompaktowe okno `BlockDialog`; korzysta ono
z istniejących klas pól i `Modal`, fokusu, Escape, stanu zapisu oraz błędów.
Siatka `work-block-fields` pozwala polom zwężać się do szerokości panelu,
a wspólny selektor nie dodaje zewnętrznych marginesów filtra.
Po udanym zapisie i błędzie odczytu przycisk „Odśwież widok” ponawia odczyt.
Bez JavaScriptu blokadę i jej usunięcie obsługują formularze w menu.

Ustawienia Przestrzeni są osobną stroną `space-settings-page`. Główne lewe menu
zastępuje menu Workspace sześcioma sekcjami: „Ustawienia”, „Udostępnienia”,
„Typy zgłoszeń”, „Kategorie”, „Grupy” oraz „Proces pracy”, według uprawnień. Proces pracy używa
wspólnego edytora konfiguracji; pola dodatkowe pozostają ukryte w ustawieniach.
Zawiera same pozycje sekcji, bez dodatkowych nagłówków i powrotu. Wykorzystuje
istniejące wiersze `nav-link`, ikony oraz aktywny stan menu. Sekcja procesu
ma dodatkowy pasek „Stany”/„Mapa”; pozostałe sekcje nie powielają menu
w treści. Centrum Ustawień w kategorii Workspace pokazuje
listę dostępnych przestrzeni z wejściem na tę stronę.

Główny formularz rozszerza się wraz z panelem, bez stałego limitu szerokości.
Padding poziomy wynosi `max(var(--app-modal-padding-x), 10%)`. Na szerokim
ekranie formularz ma po 24px od góry i dołu (`--app-modal-padding-y`), awatar ma 100px i odstęp 32px od
pól. Nazwa i widoczność zajmują wspólny wiersz, opis pełną szerokość poniżej,
a pozostałe pola tworzą dwie kolumny z odstępem 48px. Pionowe odstępy między
wierszami wynoszą 12px, również w układzie mobilnym. Opis ma minimum 128px
wysokości. Zapytania kontenera `space-settings` reagują na szerokość panelu,
również przy zmianie szerokości menu: do 960px padding i odstępy kolumn
maleją do 24px, do 640px pola przechodzą do jednej kolumny, a awatar nad nie.
Na desktopie wejście do ustawień rozwija menu sekcji niezależnie od zapisanej
preferencji zwykłego menu. Ręczne zwinięcie obowiązuje tylko podczas tej
wizyty; powrót przywraca preferencję Workspace. Mobilne menu zachowuje
dotychczasowy przycisk otwierania i zamykanie po wyborze sekcji.
Tabele „Udostępnienia”, „Typy zgłoszeń” i „Proces pracy → Stany” używają
`LocalDirectoryTable` z klasami arkusza Tagów (`tasks-tag-sheet`,
`tasks-spreadsheet-sheet`). Mają wiersze 35px, kolumnę zaznaczeń 40px,
te same separatory i przewijanie. „Filtruj”, „Sortuj”, „Zarządzaj tabelą”
oraz wyszukiwarka są po lewej, a grupa działań po prawej we wspólnym pasku.
Na szerokim ekranie mieszczą się w jednym wierszu; przy braku miejsca zawijają
się według wspólnego wzorca `ViewToolbar`. Kontener działań wewnątrz
`settings-directory-toolbar` jest przezroczysty dla układu (`display: contents`).
Wyszukiwanie obejmuje także ukryte kolumny i ignoruje polskie znaki.
Sortowanie zmienia wyłącznie widok; domyślna kolejność stanów pozostaje
kolejnością procesu. Filtry typów obejmują klucz, stanów klucz, kategorię
i etap przepływu, a osób rolę. Zmiana wyszukiwania lub filtra czyści
zaznaczenie; checkbox nagłówka i Ctrl/Cmd+A zaznaczają widoczne wyniki.
Wspólne `DirectoryColumnManager`, `useDirectoryColumns` i `Resize` zapisują
lokalnie kolejność, widoczność i szerokość kolumn osobno dla każdej sekcji.
Reset przywraca układ. Długie tabele przewijają się poziomo także na telefonie,
a brak wyników używa wspólnego `EmptyState`. Pierwszy render Django ma
te same domyślne szerokości; kontrolki tabeli są dostępne po uruchomieniu Reacta.

Tabela „Udostępnienia” korzysta z tego samego `shared/AccessEditor` co Pulpity.
Ma po bokach `--app-page-padding-x`, pięć kolumn bez menu wiersza oraz
pasek widoczności i akcji nad tabelą. Pole widoczności znajduje się po lewej,
a „Zmień rolę”, „Odbierz dostęp” i „Udostępnij” po prawej.
Pasek nie ma „Zapisz” ani „Anuluj”.
Zmiany osób i ról zapisuje zatwierdzenie formularza; zmiana widoczności
i odebranie dostępu wymagają zatwierdzenia kompaktowego okna.
Nie ma licznika członków ani dolnej stopki. Wspólne klasy `access-editor`,
`member-access-toolbar` i `member-access-save-actions` w `workplace-team.css`
zachowują odstępy, zawijanie i wyłączone kontrolki wzorca Pulpitów.
Wariant `space-settings-table-body` oddaje tabeli pozostałą wysokość oraz
przewijanie w obu kierunkach. Pierwszy render Django zachowuje ten sam układ,
a rozwijany formularz zgodności pozwala nadal korzystać ze starszych operacji.
„Typy zgłoszeń” zachowują ten sam układ co „Udostępnienia”: wspólny pasek
działań, tabelę odsuniętą od boków o `--app-page-padding-x` i brak dolnej
stopki. Wariant `settings-directory-sheet` korzysta z siatki i ról
tabeli Tagów. Ma checkboxy oraz kolumny klucza,
nazwy i opisu typu zgłoszenia, bez osobnej kolumny menu wiersza.
Ikona znajduje się w komórce nazwy, po jej lewej stronie,
z odstępem 8px jak na liście Przestrzeni.
Ikona używa wspólnego `tasks-issue-type`, z tymi samymi symbolami i kolorami
co zadania. Formularze dodawania i edycji typu mają strukturę ustawień
Przestrzeni: po lewej podgląd ikony 100px i „Zmień”, po prawej nazwa u góry,
opis na całą szerokość oraz klucz poniżej. Wariant `work-type-form` korzysta
z `app-form-avatar-layout`, `app-form-heading` i `app-form-description`;
opis ma minimum 128px, a na telefonie pola przechodzą pod ikonę.
Podglądy ikon typów i etapów mają przezroczyste tło w React i pierwszym
renderze Django; wielkość ikon oraz położenie przycisku „Zmień” są wspólne.
„Zmień” otwiera wspólny `Dropdown` z 24 kolorowymi ikonami lokalnego zestawu.
Picker wykorzystuje klasy `emoji-picker` ze wzorca Pulpitów: wyszukiwarkę,
opcję domyślną, siatkę ośmiu kolumn i dolny podgląd wybranego symbolu.
Wyszukiwanie ignoruje wielkość liter i polskie znaki, pokazuje licznik wyników
oraz stan pusty; samo wpisywanie nie oznacza zmiany formularza.
Strzałki poruszają się po siatce, Enter wybiera, a Escape zamyka picker
i przywraca fokus przycisku „Zmień”. Szerokość 400px dopasowuje się do telefonu.
Wybór „Domyślna dla typu” przywraca symbol według klucza i aktualizuje podgląd
podczas jego wpisywania. Własna ikona pozostaje niezależna od zmiany klucza.
Pierwszy render Django zachowuje układ; „Zmień” rozwija natywne pole ikony.
Kolumna opisu ma domyślnie 320px, a pełny tekst jest dostępny
w podpowiedzi i edycji. Brak opisu jest oznaczony „—”.
Na pasku są „Edytuj”, „Usuń” i „Dodaj typ”, z klasą `member-access-toolbar`.
Nie ma prawej pary „Zapisz” / „Anuluj”. Dodawanie i edycję zapisuje przycisk
w formularzu; zbiorcze usuwanie ma kompaktowe okno potwierdzenia.
„Edytuj” wymaga dokładnie jednego zaznaczenia; „Usuń” obejmuje wszystkie
zaznaczone pozycje. Nazwa typu również otwiera standardowy `Modal`.
Checkboxy, Ctrl/Cmd+A i Escape obsługują zaznaczenie. Opis konfiguracji
oraz licznik typów nie są wyświetlane. Pusta grupa pokazuje komunikat,
zachowując pasek działań. Tabela przewija się we własnym kontenerze, także
poziomo na małych ekranach; pasek pozostaje poza przewijaną treścią.
Pierwszy render Django ma ten sam układ. Link nazwy i „Dodaj typ” zachowują
natywne formularze, a rozwijana sekcja zgodności udostępnia usuwanie bez Reacta.
Wspólna powłoka okna zachowuje fokus, Escape, blokadę podczas zapisu
i potwierdzenie odrzucenia zmian. Wariant wysokości opisu głównych ustawień korzysta ze
wspólnego `--app-form-textarea-min-height`, ustawionego wyłącznie wewnątrz
strony ustawień przestrzeni.

Zmiany wspólnego CSS formularzy wymagają odświeżenia wersji importu
`modal-system.css` w `style.css` oraz wersji `style.css` w `core/base.html`.
Sama zmiana adresu arkusza nadrzędnego nie unieważnia cache jego importów.

Wspólny `AvatarControl` pokazuje pod awatarem przycisk „Zmień”. Wybór
ilustracji, upload i kadrowanie zachowują istniejący picker; szkic awatara
zapisuje się dopiero z całym formularzem ustawień. Nie ma osobnej sekcji
awatara. `space-settings-panel` jest elastycznym kontenerem istniejącej
treści; ukrycie głównych ustawień zachowuje ich formularz i szkic.
Główne ustawienia mają nad formularzem pasek z przyciskami po prawej:
„Zapisz” z ikoną `check`, następnie „Anuluj”, zgodnie z mapą Procesu pracy.
Pasek korzysta z `member-access-toolbar` i `member-access-save-actions`;
wariant formularza zeruje tylko jego dolny margines. Nie ma dolnej stopki.
W React zapis jest nieaktywny przed zmianą danych i podczas wysyłania;
natywny formularz Django zachowuje aktywny submit. Nagłówek i pasek pozostają
poza przewijaną treścią. „Zapisz” głównych ustawień
pozostawia stronę otwartą i aktualizuje nazwę w nagłówku i tytule dokumentu.
W sekcjach typów, kategorii i grup zatwierdzenie okna zapisuje dodanie lub
edycję, a usuwanie wymaga potwierdzenia. „Anuluj” w oknie odtwarza stan
sprzed jego otwarcia, pozostając w sekcji.
Żądanie przekazuje pełne formsety, w tym nienaruszone statusy i pola dodatkowe,
wraz ze wspólną rewizją do dotychczasowej walidacji Django. Błąd zachowuje szkic;
błędne pola otwierają edytor z fokusem, a konflikt wymaga wybrania
„Wczytaj aktualną konfigurację”. Po zapisaniu i błędzie odczytu ponowienie tylko pobiera dane.
Nawigacja i przeładowanie chronią szkic głównych ustawień i typów,
a `Modal` chroni szkic otwartego okna.
Zmiana widoczności w ustawieniach i udostępnieniach wymaga wcześniejszego
zapisania lub anulowania szkicu typów, aby zmiana uprawnień go nie usunęła.
„Anuluj” głównego formularza zachowuje kontekst powrotu
formularza, np. katalog; domyślnie, podobnie jak strzałka w nagłówku, prowadzi
do przestrzeni. Zmiana sekcji aktualizuje adres `?view=settings#<sekcja>`
(`main`, `members`, `types`, `statuses`) oraz historię Wstecz/Dalej
z zachowaniem formularza głównych ustawień. Starsze `#configuration`
i `#fields` otwierają typy zgłoszeń; `#statuses` otwiera Proces pracy.
Udostępnianie i zmiana roli otwierają
kompaktowe okno z pickerem osoby. Bezpośrednie URL ustawień i konfiguracji
renderują tę samą stronę. Pierwszy render Django również zawiera formularze
i tabelę członków; jego menu przekazuje sekcję członków przez `&section=members`
oraz wybiera typy przez `configuration/?section=types`. Bezpośrednie adresy
usuniętych sekcji również pokazują typy, bez otwierania ich edytorów.
Po błędzie zapisu konfiguracji Django zachowuje formularz z błędami w oknie;
błędy ukrytych formsetów statusów i pól są komunikatami ogólnymi.
Szczegóły:
[Strona ustawień](SPACES.md#strona-ustawień-przestrzeni).

Menu wierszy Przestrzeni w nawigacji nie zawierają „Dodaj osoby”.
Udostępnianie pozostaje w sekcji „Udostępnienia” strony ustawień przestrzeni.

Zakładka „Udostępnienia” używa `shared/MemberDirectory` z kontrolowanym zaznaczeniem
wszystkich wierszy, Ctrl/Cmd+A i Escape. Akcje obejmują tylko `can_change`,
więc właściciel i chronieni administratorzy pozostają bez edycji. Model
członkostwa Przestrzeni nie zapisuje daty dołączenia; brak daty pokazuje „—”.
`SharingDialog` obsługuje picker Workspace i zbiorczą zmianę roli.
„Udostępnij” i „Zapisz rolę” w oknie od razu zapisują operację.
Widoczność i „Odbierz dostęp” mają oddzielne potwierdzenie; „Anuluj” w oknie
odrzuca niezapisaną operację. Błąd pozostawia okno do poprawy lub ponowienia,
a konflikt blokuje zapis do wczytania aktualnego dostępu przez anulowanie.
Nawigacja chroni niezapisane zmiany.
Wyszukiwanie `draft=1` obejmuje aktywnych członków Workspace, także osoby
usunięte ze szkicu; dodanie obecnej osoby pokazuje błąd. Publiczna Przestrzeń
pokazuje „Dostęp z Workspace” i wyłącza indywidualne akcje. Zmiana na prywatną
przygotowuje wiersz nowego właściciela według reguł Przestrzeni.
Okna zachowują wspólny fokus, Escape, `inert` i ochronę szkicu; style tabeli
i pickera pochodzą z `workplace-team.css`.

Pasek zadań Listy, Tablicy, Backlogu i Osi czasu ma dwa menu:
„Sortowanie” i „Filtrowanie”. Lista, Tablica i Backlog nie mają osobnego pola wyszukiwania zadań; Oś czasu dodaje wyszukiwanie opisane poniżej.
W otwartej Przestrzeni pasek jest pierwszą częścią obszaru zadań
`work-content--items`, a w Liście i Backlogu przewija się razem z wynikami.
Wspólny kontener wyrównuje menu i treść do tych samych marginesów strony,
z wewnętrznym odstępem 5px u góry i dołu oraz 8px między częściami.
Pionowe 5px obowiązuje również w Podsumowaniu i wynikach Filtrów korzystających
z `work-content--items`, także na telefonie. Tabele nie dodają drugiego
wewnętrznego paddingu. Pasek nie ma osobnej ramki ani separatora;
ramki przycisków i separator pod nagłówkiem Przestrzeni pozostają zachowane.
Ten sam układ obejmuje Tablicę i Oś czasu oraz pierwszy render Django.
`spaces/ItemToolbar.tsx` używa wspólnego `Dropdown` oraz klas
`tasks-project-query-*`, tak jak Dysk i Zasoby. Sortowanie ma wybór pola,
kierunku i powrót do domyślnej kolejności. Filtrowanie zawiera typ zgłoszenia,
wykonawcę, status, priorytet i zespół, wyszukiwanie opcji, licznik aktywnych
warunków oraz czyszczenie. Wybór od razu odświeża wyniki, zachowuje pozostałe
warunki i usuwa numer strony. Escape zamyka panel i przywraca fokus.
Pierwszy render Django używa dwóch `details` i tych samych klas;
formularz filtrów oraz linki kolejności działają także bez JavaScriptu.

Nagłówek otwartej Przestrzeni łączy awatar, nazwę, działania i zakładki widoków
w jeden `work-space-header`, również w Tagach. React współdzieli
`src/spaces/SpaceHeader.tsx`; pierwszy render Django zachowuje tę samą powłokę
w `spaces/detail.html`. Nazwa i działania pozostają w górnym wierszu, zakładki
poniżej. Jedna dolna ramka oddziela cały nagłówek od treści; między wierszami
nie ma separatora. Podkreślenie aktywnej zakładki, polskie etykiety, wspólne
kontrolki i poziome przewijanie zakładek na telefonie pozostają zachowane.
Ustawienia korzystają z tej samej powłoki, typografii i odstępów, zachowując
strzałkę powrotu oraz tytuł „Ustawienia przestrzeni · nazwa”. Podzakładki
„Stany” i „Mapa” są częścią nagłówka, bez dodatkowej ramki między tytułem
a zakładkami. Tytuł dokumentu również określa kontekst „Ustawienia przestrzeni”.
Długie tytuły zawijają się jak w zwykłej Przestrzeni.

Szczegóły nowego zadania (`spaces/task_detail.html`) zachowują powłokę,
kontrolki i współdzielone include'y dawnego ekranu Tasks przez
`spaces/base.html` oraz `core/base.html`. Nagłówek współdzieli z Przestrzenią
`work-space-header`, `tasks-topbar--directory` i `work-tabs`: strzałka powrotu
i tytuł 17px/700 są w pierwszym wierszu, zakładki w drugim, ponad obiema
kolumnami zadania. „Dodaj czas” jest po prawej stronie pierwszego wiersza
przy aktywnym Dzienniku pracy i prawie edycji. Jedna dolna ramka oddziela
cały nagłówek od treści, bez separatora między wierszami. Długie tytuły
zawijają się; zakładki przewijają się poziomo. React i pierwszy render Django
zachowują ten sam układ. Adres i nawigacja zachowują przestrzeń, a powrót `view`
i filtry. Panel po prawej zaczyna się osobną sekcją widoczności. Właściwości
zadania mają kolejność: status, priorytet, przypisane do, typ zgłoszenia,
kategoria zadania i tagi. Następna sekcja zawiera terminy: datę rozpoczęcia,
termin zakończenia i przypomnienie. Ostatnia sekcja informacji o zadaniu
zawiera trwały klucz z kopiowaniem, autora, datę utworzenia i datę zamknięcia.
Sekcje mają odpowiednio nazwy dostępności „Widoczność zadania”, „Właściwości
zadania”, „Terminy zadania” i „Informacje o zadaniu”.
„Data rozpoczęcia” i „Termin zakończenia” są zawsze widoczne w sekcji terminów,
także bez wartości, i korzystają ze wspólnych pól oraz automatycznego zapisu.
Oba pola wskazują datę i godzinę, tak jak formularz na osi czasu.
Zmiana w szczegółach i na osi czasu dotyczy tych samych
danych. Obserwator widzi wyłączone pola. Pierwszy render Django zachowuje
ten sam układ i nie powiela pola rozpoczęcia w ukrytym planowaniu.
Pola dodatkowe konfiguracji są widoczne w osobnej sekcji tego samego panelu,
z istniejącymi klasami `tasks-issue-side-section` i `tasks-issue-field`.
Błąd ukrytego pola planowania odsłania jego kontrolkę i komunikat w tej sekcji.
Widoczność jest polem tego samego formularza; właściciel prywatnego zadania
zarządza jego widocznością. Pozostałe planowanie jest dostępne przez dotychczasową
edycję w przestrzeni; jego wartości są zachowane przy zapisie szczegółów.
Na wąskim ekranie panel przechodzi pod treść, a zakładki przewijają się.

Wariant panelu właściwości w `spaces.css` ogranicza kolumnę etykiet do 128px
i 36% szerokości wiersza, pozostawiając więcej miejsca na wartości i daty.
Sekcje mają równy odstęp `0.25rem` między polami, również z kontenerami Reacta.
Statyczne wartości mają takie samo wcięcie jak kontrolki. Etykiety, wybrane
wartości i nazwa autora mogą się zawijać; błędy zajmują pełny wiersz pod polem.
Do 360px etykieta znajduje się nad wartością, aby natywne pola daty i godziny
mieściły się w panelu. Wariant obejmuje tylko szczegóły zadań głównych,
także pierwszy render Django; panel profilu zachowuje własny układ.

Nagłówek nie wyświetla statusu ani przycisku zapisu. Automatyczny zapis
uruchamia atrybut `data-space-task-autosave` formularza, niezależnie od
widocznych kontrolek. Stan jest zapisany w `data-save-state`, a komunikat
`role=status` ogłasza go wyłącznie czytnikom ekranu. Błędy korzystają z
istniejącego banera i `errorlist`; przycisk „Spróbuj ponownie” pojawia się
tylko w banerze błędu. Bez JavaScript formularz ma przycisk „Zapisz” w
`noscript`. Edycja tekstu ma 700 ms opóźnienia,
pozostałe pola zapisują się od razu. Kolejkowanie zachowuje nowszy szkic,
fokus, otwartą zakładkę i komentarz. Inicjalizacja `spaces.js` działa również
po `ancore:content-loaded`, a abort usuwa listenery i timer poprzedniej strony.

Wszystkie pięć paneli jest renderowane razem. Wspólny `task-work-log.js`
przełącza przyciski zakładek, URL `tab`, ARIA i fokus klawiatury, zachowując
szkic tytułu, opisu i pól. Podzadania mają standardowy toolbar, grupy statusów,
zaznaczanie, sortowanie, usuwanie i modal tworzenia. Podzadania nie mają osobnej
pełnej strony. Kliknięcie tytułu z prawem edycji otwiera istniejący `FormDialog`
nad zakładką rodzica; obserwator widzi sam tytuł. Tworzenie i edycja mają
dziewięć pól: Tytuł, Opis, Status, Priorytet, Wykonawca, Typ zgłoszenia,
Data rozpoczęcia, Termin zakończenia i Estymacja (punkty), również poza Scrumem.
Tytuł i opis zajmują pełne wiersze; pozostałe pola korzystają ze wspólnych
dwóch kolumn `app-form-layout`, na telefonie z jednej. Widoczność nowego
podzadania pozostaje domyślnie prywatna i nie zajmuje miejsca w formularzu.
Status i priorytet używają istniejącego `VisualSelect` oraz podglądów
`select_status.html` i `select_priority.html`, także z prefiksem `subtask-`.
Własny status ma oznaczenie swojej kategorii, a wykonawca dotychczasowy awatar.
Okno zachowuje walidację, ochronę szkicu, Escape i powrót fokusu. Zapis odświeża listę
bez opuszczania rodzica; błąd odświeżenia pozwala ponowić sam odczyt.
Pierwszy render używa tego samego linku edycji z `data-work-open`.
Wiersze podzadań mają minimalną szerokość 520px i przewijają się poziomo
wewnątrz grupy, tak jak lista zadań Przestrzeni. Tytuł zachowuje miejsce
również na telefonie; nagłówek statusu pozostaje w szerokości panelu.
Stare adresy podzadań prowadzą po kontroli dostępu do „Podzadań” zadania
głównego. Istniejące dalsze poziomy są widoczne w tej samej płaskiej liście.
Dziennik pracy korzysta
z `tasks/includes/work_log_list.html`, `work_log_modal.html` i wspólnego
`core.work_logs.TimeLogForm`: suma minut, „Pokaż więcej”, awatary i dodawanie
przez modal. Wejścia do edycji i usuwania z menu wiersza zostały usunięte. Zakładka „Udostępnienia” używa `project_members_panel.html`, wspólnej tabeli
Workspace oraz modali udostępniania i ról; publiczne zadanie pokazuje osoby
z dostępem odziedziczonym. Endpointy tabeli i pickera należą do przestrzeni.
Historia i komentarze współdzielą `task_activity_item.html`, z awatarami,
datami, zmianami pól i kartami/miniaturami załączników.

Pola `DetailForm` należą do `space-task-form` przez atrybut `form`.
`spaces.js` porównuje stan formularza i zapisuje zmianę pola lub wybór pliku.
Wybrane załączniki można usunąć przed zapisem. Czat używa
wspólnego composera, pickera wzmianek, uploadu i błędów AJAX. Pliki mają
chronione adresy przestrzeni. Inicjalizacja działa również po
`ancore:content-loaded`, z usuwaniem poprzednich listenerów.
`AncoreCustomSelect` wspiera opcjonalne etykiety pustego wyboru i ikony;
picker tagów używa „Tagi”. Nie wprowadzono osobnego systemu kontrolek.


`spaces/base.html` rozszerza `core/base.html` i wspólny kontener katalogu.
Katalog i zarządzanie przestrzeniami współdzielą `spaces/directory.html`
z listą `tasks-directory-sheet`, `tasks-project-sheet`
i `tasks-spreadsheet-sheet`, tak jak projekty i grupy. Wariant `work-space-sheet`
określa kolumny: zaznaczenie, klucz, nazwa, rodzaj, szablon, opis
i liczba zadań. Kolumna zaznaczenia ma 40px.
Checkboxy `tasks-row-checkbox` są stale widoczne dzięki
`tasks-project-sheet--selectable`; zaznaczenie podświetla wiersz wspólnym stylem.
Checkbox może być wewnątrz komórki `data-column="select"` z rolą `cell`.
Checkbox nagłówka zaznacza wczytane wiersze i pokazuje stan częściowego wyboru.
Zaznaczenie jest lokalne, bez operacji zbiorczych. Katalog nie zawiera menu
wiersza ani jego kolumny. Nazwa nadal otwiera przestrzeń; menu boczne zachowuje
istniejące wejścia do gwiazdki i ustawień.
Wysokości wierszy, separatory, zmiana szerokości kolumn, poziome przewijanie
oraz pasek filtrów, wyszukiwania i „Pokaż więcej” pod listą pozostają wspólne.
Pusty wynik ukrywa nagłówki i pokazuje komunikat zależny od filtrów/zakładki.
Pusty katalog przestrzeni używa wariantu `work-space-empty-state`
wspólnego `tasks-empty-state`: kolorowej ilustracji 3D
`static/img/empty-states/spaces-empty.webp`, tekstu `tasks-empty-state__copy`
bez przycisków i linków akcji w pustym stanie.
Ilustracja przedstawia warstwy projektów i kolorowe karty zadań, ma przezroczyste
tło, maksymalną szerokość 440px i skaluje się do kontenera na telefonie.
Jest dekoracyjna (`alt=""`, `draggable="false"`), a pusty stan ma `role="status"`.
Katalogi Przestrzeni, Pulpitów i Filtrów (także zarządzanie) oraz przegląd pustego pulpitu
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

Wiersze Backlogu i jego sprintów nie mają przycisku menu ani dodatkowej
kolumny działań. Pozostały linki do zadania oraz przeciąganie zgodne
z prawem edycji, wybranym sortowaniem i filtrami.

Backlog, Lista zadań przestrzeni i kafelki Aktywnego sprintu współdzielą
`spaces/item_planning.html`: awatar przypisanego wykonawcy lub ikonę osoby
oraz, w Scrum, małą etykietę punktów. Zero wyświetla się jako `0`, a brak
estymacji jako `—`. Wariant `work-issue-row--planning` rezerwuje kolumny
punktów i awatara na liście/backlogu. `show_work_metadata` włącza metadane
dla listy otwartej przestrzeni;
pozostali odbiorcy `row.html` (Filtry, Dla ciebie, Zespoły i podzadania)
zachowują dotychczasowy wariant.
Nie ma osobnego nagłówka „Planowanie sprintów” ani stałego paska zaznaczania.
Grupa `app-toolbar__selection` w działaniach istniejącego paska pojawia się
po zaznaczeniu checkboxu; pokazuje liczbę zadań, przyciski i `AncoreCustomSelect`.
Pierwszy render Django zachowuje formularz `data-backlog-bulk` jako sąsiada
formularza filtrów we wspólnej powłoce. Odznaczenie ostatniego zadania lub
„Odznacz” ukrywa grupę działań, zachowując pasek filtrów; fokus adaptera JS wraca
do checkboxu wiersza. Zadania tylko do odczytu są pomijane.
Nagłówki sprintów i Backlogu nie mają checkboxów. Zachowują kolory według stanu,
zwijanie i licznik strony, dodając `work-planning-summary` dla pełnych
agregacji po filtrach. Sekcje mają link do wspólnego modalnego tworzenia
zadania z wybranym backlogiem/sprintem. „Utwórz sprint” znajduje się po prawej
stronie nagłówka sekcji Backlog, przed licznikiem, i pozostaje
widoczne po jej zwinięciu; przycisk widzi osoba zarządzająca przestrzenią Scrum.
Akcje edycji, rozpoczęcia/zakończenia oraz tworzenia sprintu w nagłówkach
mają kompaktową wysokość 28px, jak przycisk zwijania, przezroczyste tło i ramkę.
Ikony mają 16px, a przyciski tekstowe odstęp wewnętrzny 8px po bokach.
Najechanie i fokus klawiatury dodają neutralne `--system-interaction-soft`;
niedostępna akcja ma 45% krycia i nie podświetla się. Wariant dotyczy wyłącznie
bezpośrednich przycisków nagłówków backlogu/sprintów w React i renderze Django.
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
przycisk zwijania i pełny licznik nieukończonych zadań po filtrach.
Sprint planowany korzysta z koloru kategorii `new`, a aktywny z jasnego zielonego
tła (`#e8eee4`, jak w kategorii `resolved`), zachowując ikonę zegara `in_progress`.
Lokalna reguła `work-sprint` obejmuje React i pierwszy render Django; nie zmienia
kolorów statusów zadań. Backlog ma szary nagłówek grupy i ikonę warstw. Wspólny include obsługuje
opcjonalne `label_suffix` i `details_template`; sprint dodaje nimi stan, daty
i dotychczasową akcję rozpoczęcia/zakończenia. Na wąskim ekranie nagłówek
zawija metadane i przyciski, a wiersze przewijają się poziomo wewnątrz sekcji.
Cel sprintu pojawia się tylko, gdy został podany, i zwija się razem z listą.
Puste sekcje używają `tasks-empty-section` z `role="status"`; brak wyników
backlogu po filtrach ma osobny komunikat. Zwijanie aktywnych grup obsługuje
React `StatusGroup`; `tasks.js` zachowuje obsługę pierwszego renderu zgodności.
Kolejność planowania jest zachowana; hamburgerów wierszy nie ma.

W aktywnym ekranie React tablicę i backlog renderują
`spaces/DetailPage.tsx`, `spaces/Item.tsx` oraz wspólny `StatusGroup`.
Szablony `spaces/card.html` i `spaces/row.html` zachowują pierwszy render;
`spaces/sprint_card.html` jest aliasem wspólnej karty. Starsze kontrolery
`spaces.js`/`tasks.js` nie obsługują interakcji korzenia Reacta. Zwijanie grup
należy do `StatusGroup`.

Wszystkie tablice Przestrzeni używają wariantu `work-sprint-board`, wspólnego
z „Aktywnym sprintem”. Dotyczy to Kanbana, Scrum, Zarządzania zadaniami,
Marketingu, Rekrutacji i Obsługi zgłoszeń. Kolumny rozszerzają
`tasks-issue-group tasks-status-block` z Listy zadań. Mają te same kolory
kategorii, wysokość nagłówka 40px, ikony statusów, liczniki i przyciski zwijania.
Szerokość kolumny dodaje 10px do wspólnego `--tasks-kanban-column-width`:
zakres wynosi 240–310px, z dotychczasową responsywnością i przewijaniem poziomym.
Karta `tasks-issue-row work-issue-row work-sprint-card` zawiera priorytet,
klucz, status i zawijany tytuł w pierwszym wierszu oraz metadane poniżej:
typ, wykonawcę, tagi, załączniki i oznaczenie terminu. Karty nie pokazują
przycisku trzech kresek ani menu działań, również w pierwszym renderze Django.
Siatka ma cztery kolumny; klucz ma własny tor o szerokości treści, a tytuł wykorzystuje pozostałe miejsce.
Punkty są widoczne tylko w Scrum, zgodnie z formularzami planowania.
Opcjonalny zespół pozostaje opisem. Każdy kafelek ma białą powierzchnię, pełne obramowanie
`--border-color` i zaokrąglenie nagłówka Kanbana. Odstęp kart wynosi `0.55rem`,
a odstęp nagłówka od listy `0.65rem`. Karty mają `flex: 0 0 auto`, dzięki
czemu długa lista przewija się bez ściskania metadanych. Pusty stan ma własną
ramkę, a cała wysokość kolumny przyjmuje upuszczenie. Powłoka ogranicza tablicę
do dostępnego miejsca pod paskiem sortowania/filtrowania. Widok
„Aktywny sprint” nie pokazuje dodatkowego wiersza z nazwą, datami i celem sprintu;
te informacje pozostają w Backlogu. Przy braku aktywnego sprintu nadal pokazuje
komunikat z linkiem do Backlogu. Na wąskim ekranie kolumny przewijają się poziomo.
React renderuje jeden `ItemCard` i jeden `StatusGroup` dla każdego szablonu,
bez osobnej karty i szarego nagłówka Kanbana. Pierwszy render Django używa
`spaces/card.html` oraz wspólnego `issue_group_header.html`. Historyczne nazwy
klas z prefiksem `work-sprint-` oznaczają teraz wspólny wzorzec tablic.
Przeciąganie, animacje, zwijanie i pola docelowe mają to samo zachowanie.

`spaces/useItemMotion.ts` obsługuje efekty natywnego przeciągania kart i wierszy
backlogu. Elementy mają `data-work-motion-item`, a sekcje docelowe
`data-work-drop-group`. Linki i obrazy wewnątrz nie uruchamiają osobnego drag;
kliknięcie tytułu nadal otwiera zadanie. Kontrolki i menu nie rozpoczynają gestu.
Obserwator i widok sortowany inaczej niż rosnąca kolejność ręczna nie
udostępniają przeciągania. W backlogu pierwszą kontrolką pozostaje checkbox;
nie dodano osobnego uchwytu. Menu Backlogu „Przesuń wyżej/niżej” i przeniesienia między
sprintami pozostają alternatywą klawiaturową.

Podgląd `work-board-drag-preview` jest nieinteraktywną kopią całej karty lub
wiersza, z istniejącymi cieniami, lekkim przechyleniem i powiększeniem.
Śledzi kursor z uwzględnieniem zoomu UI i pozostaje w granicach okna.
Kopia zachowuje dekoracyjne atrybuty ikon, ale nie zawiera ID ani aktywnych
hooków aplikacji; ma `inert` i `aria-hidden`. Przezroczysty obraz natywnego drag
usuwa drugi podgląd przeglądarki. Źródło zachowuje rozmiar i jest przygaszone.
Cel ma czerwony obrys i delikatne tło. `work-item-drop-slot` tworzy miejsce
w wysokości zadania; sąsiednie karty płynnie przesuwają się, gdy zmienia się
miejsce wstawienia. Pusta i zwinięta sekcja przyjmują zadanie na końcu.
Przy krawędziach gest przewija kolumnę lub backlog pionowo i tablicę poziomo.

Po upuszczeniu React od razu pokazuje nową kolejność/status i blokuje kolejną
operację na czas zapisu. Animacja FLIP (320ms) przesuwa sąsiadów; przy przenoszeniu
między sekcjami kopia ponad interfejsem dolatuje do celu (360ms), dzięki czemu
nie jest obcinana przez przewijane listy. Zmiany z menu również animują układ
po odpowiedzi serwera. Zapis nadal używa JSON API i istniejących akcji
`position`/`plan`, z pozycją źródła i sąsiadów. Po potwierdzeniu odświeża
liczniki, metadane i uprawnienia, zachowując URL i filtry. Odrzucony zapis
przywraca poprzedni układ i pokazuje błąd. Błąd samego odczytu po przyjętym
zapisie zachowuje przeniesienie i pozwala odświeżyć widok. Upuszczenie bez
zmiany pozycji nie wysyła zapisu. `aria-busy` oraz region live opisują stan.

Escape, zakończenie gestu, utrata fokusu okna i odmontowanie ekranu usuwają
podgląd, cel oraz przewijanie. Hook usuwa również listenery i animacje przy
częściowej nawigacji. `prefers-reduced-motion` wyłącza przechylenie,
powiększenie i animacje ruchu; pozostawia czytelny podgląd i obrys celu.

Zakładka „Tagi” zachowuje nagłówek i nawigację otwartej przestrzeni.
`spaces/tags.html` korzysta ze wspólnych include'ów `tag_directory`,
`tag_sort`, `tag_filters`, `tag_modal` i `tag_notes_modal`. Przycisk „Dodaj tag”,
edycję, informacje, notatki i wybór kolumn obsługuje `frontend/app/src/tags`,
z tymi samymi klasami CSS i powłoką modali. Tagi nie pokazują menu „…”
w nagłówku ani kolumny menu wiersza z trzema kreskami. Opcjonalne kolumny
„Edytuj”, „Informacje” i „Notatki” pozostają w menedżerze kolumn tabeli.
`tasks.js` zachowuje obsługę szablonów zgodności i pomija korzeń Reacta.
Inicjalizacja działa również po `ancore:content-loaded`. Obserwator widzi
informacje i notatki bez przycisków zapisu; modal edycji jest niedostępny.
Katalog wczytuje po 20 tagów. Pod wierszami jest wspólny pasek `work-list-more`
„Pokaż więcej (20 / 45)”, ze stanami „Wczytywanie…” i „Wszystkie tagi (45 / 45)”.
Lista mieszcząca się w pierwszych 20 wierszach nie pokazuje paska.
Przycisk pozostaje w szerokości widocznej tabeli również przy poziomym
przewijaniu na telefonie. Błąd pozwala ponowić odczyt bez utraty wierszy,
a sukces zachowuje zaznaczenia i przewinięcie. Wyszukiwanie, filtry i sortowanie
resetują zakres do 20. Toolbar nie ma strzałek stron ani wyboru „/ stronę”.
Pierwszy render Django zachowuje ten sam pasek jako zwykły link.
Tabela ma po bokach odstęp `--app-page-padding-x` (15px), jak Udostępnienia. Kontener tabeli tagów
wypełnia pozostałą wysokość panelu i obsługuje przewijanie w obu kierunkach.
Poziomy pasek jest przy dolnej krawędzi panelu także przy krótkiej liście;
nagłówek przestrzeni i pasek filtrów pozostają poza przewijaną treścią.
Reguła obejmuje React i pierwszy render Django. W formularzu zadania
przestrzeni picker „Tagi” korzysta z `AncoreCustomSelect` i lokalnego wyszukiwania.
Modal tworzenia zadania przełącza opcje tagów po wyborze przestrzeni
przez `AncoreTaskTags` w `tasks.js`, zachowując własne dropdowny. Szczegóły
zadania korzystają wyłącznie z tagów jego zapisanej przestrzeni. Dane opcji
są filtrowane przez widoczność projektów; etykiety trafiają do DOM jako tekst.

Osobny ekran „Zarządzaj przestrzeniami” jest usunięty wraz z jego menu bocznym,
wejściem w nagłówku Przestrzeni i wierszem w Ustawieniach. Stare zwykłe/scoped
`spaces/manage/` otwierają katalog „Przestrzenie”, z zachowaniem wyszukiwania,
rodzaju, zakładki i numeru strony. Katalog ma jeden wariant listy; stary filtr
sposobu zarządzania i klucz szerokości `spaces-management` są wycofane.
Zachowane są zakładki Wszystkie, Ulubione i Prywatne, wspólna tabela,
wyszukiwanie, filtr rodzaju i pasek „Pokaż więcej”. Menu konkretnej przestrzeni pozostaje
wyłącznie w istniejącej nawigacji bocznej.
Formularz tworzenia zachowuje powłokę modalną nad katalogiem oraz zwykłą
nawigację Workspace. Edycja, dostęp i konfiguracja zadań korzystają z osobnej
strony ustawień konkretnej przestrzeni. Uprawnienia: [SPACES.md](SPACES.md).
Katalog Workspace korzysta z menu Ustawień z aktywną kategorią „Workspace”; dawne osobne katalogi
zarządzania Przestrzeniami, Pulpitami i Filtrami są wycofane.

Centrum „Ustawienia” (`/settings/`) jest osobną stroną z własnym wariantem
głównego paska bocznego (`core/includes/settings_sidebar.html`). Zastępuje
menu Workspace kategoriami Ogólne, Konto i dostęp, Workspace i Przestrzenie.
Ustawienia konta prowadzą do profilu i wylogowania; nie zawierają
„Kont w sesji” ani „Dodaj konto”.
Kategoria Workspace otwiera bezpośrednio katalog `/workplaces/`: nagłówek
„Workspace”, „Dodaj Workspace”, wyszukiwarkę i dotychczasową tabelę.
W menu pozostają wszystkie kategorie z aktywną pozycją Workspace.
Widok Ogólne zachowuje skrót „Zarządzaj Workspace”, dla personelu także „Panel
administracyjny”, oraz krótki skrót do kategorii „Przestrzenie”.
Kategoria „Przestrzenie”, oznaczona ikoną warstw, otwiera
`/settings/?section=spaces` z katalogiem widocznych przestrzeni aktywnego
Workspace. Układ odpowiada katalogowi Workspace: wspólny `PageHeader`,
wyszukiwarka w `DirectoryToolbar` oraz kompaktowa tabela `app-data-table`.
Kolumny obejmują zaznaczenie, nazwę z awatarem, klucz, opis, rodzaj, szablon
i liczbę zadań. Awatary korzystają ze wspólnego `Avatar`. Checkbox nagłówka
zaznacza wczytane wiersze; zaznaczenie nie wykonuje operacji zbiorczych.
„Utwórz przestrzeń” znajduje się w nagłówku. Po prawej stronie
`DirectoryToolbar` są „Edytuj” i „Usuń”, z wyszukiwarką po lewej. Te dwa działania
wymagają dokładnie jednej zaznaczonej przestrzeni oraz uprawnienia do
zarządzania nią. Edycja otwiera dotychczasową stronę ustawień, tworzenie
dotychczasowy kreator we wspólnym `FormDialog`, a usuwanie kompaktowe okno
z potwierdzeniem aktualnej nazwy. Okno wyjaśnia, że usunięta zostanie także
zawartość przestrzeni. Gość i wyłączony moduł nie udostępniają tych operacji.
Opcjonalne `form.confirmation_message` rozszerza wspólny formularz o widoczny
akapit nad polami, na pełną szerokość `app-form-wide`. Usuwanie Przestrzeni
pokazuje w nim nazwę oraz zakres trwałego usunięcia. React i pierwszy render
Django wyświetlają ten sam tekst bez otwierania tooltipa; pozostałe formularze
nie wymagają tego pola.
Anulowanie kreatora wraca do katalogu ustawień, a utworzenie przestrzeni
otwiera jej ustawienia. Zatwierdzone usunięcie wraca do katalogu bez filtra
wyszukiwania i bez zaznaczeń.
Kliknięcie nazwy lub wiersza, również Enter i Spacja na wierszu, prowadzi
do istniejących ustawień wybranej przestrzeni. Checkboxy, pozostałe kontrolki
i zaznaczanie tekstu zachowują własne działanie. Wszystkie operacje są
ponownie autoryzowane przez Django.
Wyszukiwanie po nazwie, kluczu i opisie odbywa się po stronie serwera przed
oknem wyników. Nowe wyszukiwanie rozpoczyna okno od 20; kolejne wyniki odsłania
wspólne „Pokaż więcej”, zachowując dotychczasowe wiersze i zaznaczenia.
Brak przestrzeni oraz brak dopasowań mają odrębne komunikaty.
Katalog nie jest powielany w widoku Ogólne; pozostaje tam tylko skrót.
Wyłączenie modułu Przestrzeni ukrywa tę pozycję menu i skrót w Ogólnych;
bezpośredni adres nie ujawnia wtedy katalogu.
Prawo zarządzania i konfigurowania jest sprawdzane na stronie wybranej przestrzeni.
Na stronie centrum jest „Wróć do przestrzeni”. Strona ustawień przestrzeni
zastępuje główne menu sześcioma sekcjami bez dodatkowych nagłówków i powrotu.
Treść nie ma dodatkowej wewnętrznej nawigacji;
wiersze, podsumowanie konta i kontrolki zachowują dotychczasowy wygląd.
`dashboard/SettingsPage.tsx` i `shell/Sidebar.tsx` obsługują kategorie w stałej
powłoce, aktywne pozycje, adresy
z fragmentem (`#account` i skrót `#security`) oraz `?section=spaces`,
historię Wstecz/Dalej i ponowne wejście po częściowej nawigacji. Wybór kategorii
zamyka menu na telefonie; stan zwinięcia i szerokość są wspólne z resztą aplikacji.
Wyjście ze strony usuwa jej listenery; `settings.js` zachowuje obsługę
starszego renderowania HTML. Dawny adres `/settings/#workspace` przechodzi
do katalogu Workspace przez zastąpienie bieżącego wpisu historii.
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
Nagłówek otwartej przestrzeni, pasek zakładek i treść podsumowania mają po 15px
odstępu z lewej i prawej strony, również na telefonie. Wspólna zmienna
`--work-space-inline-padding` obejmuje też katalog Przestrzeni: jego nagłówek,
zakładki i filtry. Tabele katalogów w `work-content--directory`
mają po bokach odstęp 15px, jak Udostępnienia, również
na telefonie. Lista zadań i tablica wewnątrz przestrzeni nadal korzystają
z pełnej szerokości; katalog Zespołów używa wspólnego odstępu 15px.
Awatar ma 32px w nagłówku, 24px w katalogu, 20px w codziennym menu bocznym
i 21px w panelu zwiniętego paska.
Przycisk zmiany awatara (`space-avatar-trigger`) nie dodaje natywnej ramki,
tła ani paddingu: jego rozmiar odpowiada awatarowi 32×32px, tak jak dla
linku w szablonie. Fokus klawiatury używa tej samej zmiany przezroczystości
co hover, zgodnie ze wspólną zasadą bez dodatkowej ramki;
kliknięcie nadal otwiera standardowy wybór awatara.
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
klawiaturą; zaznaczenie ma czerwoną ramkę. Na telefonie siatka dopasowuje
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
kursora podkreślenie znika. Aktywna zakładka zachowuje czerwone podkreślenie
także pod kursorem. Katalog zespołów ma zakładki bez ikon.

Nagłówek „Przestrzenie” zwija i rozwija podmenu przez wspólny
`data-sidebar-group="spaces"` w `layout.js`. Stan zapisuje istniejąca
preferencja `ancoreSidebarCollapsedGroups`; pozostaje zachowany po odświeżeniu
i częściowej nawigacji. Przycisk ma `aria-controls` i `aria-expanded`
oraz obsługuje Enter/Spację. Przed nazwą jest ikona warstw (`layers`), która
przy najechaniu lub fokusie klawiatury zmienia się w strzałkę zwijania (`chevron-down`),
obróconą w prawo dla zwiniętej sekcji. Fokus klawiatury zaznacza całą powłokę
nagłówka czerwoną ramką. W trybie zwiniętego całego paska ikona nadal otwiera
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
`--sidebar-interaction-bg` (6% krycia `--system-interaction`) zapewnia ten sam kolor hover dla Dashboardu
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
jest takie samo jak górnego paska aplikacji: wspólna jednolita biała
powierzchnia, także w codziennym menu Workspace, po zwinięciu i na telefonie.
Wybrana pozycja (`a.nav-link.active`) ma jasne czerwone
tło, czerwony tekst/ikonę i krótki znacznik przy lewej krawędzi. Ta sama reguła
obejmuje Dashboard, pozostałe moduły, Favorites oraz kategorie
Ustawień i menu zarządzania. Wybrana pozycja zachowuje czerwony stan pod
kursorem; szary hover i fokus nieaktywnej pozycji nie oznaczają wyboru.
Otwarcie menu lub rozwinięcie sekcji także nie wybiera punktu nawigacji.
Dotychczasowa klasa `active` pochodzi z serwera i jest synchronizowana przy
częściowej nawigacji; Ustawienia przełączają ją przy wyborze kategorii.
Lokalne zmienne
`--sidebar-space-selection`, `--sidebar-space-selection-bg`, `--sidebar-space-focus`
i `--sidebar-space-marker` są współdzielone przez cały główny pasek boczny
i jego panel skrótów. Kolor zaznaczenia, ramki fokusu i znacznika wynosi
`#df2b2b`; tekst i zwykłe ikony mają ciemniejszy wariant `--sidebar-space-selection-ink`,
a półprzezroczyste tło używa akcentu z kryciem 10%
(16% przy interakcji). Wariant menu korzysta ze wspólnej czerwieni Ancore.
Menu boczne współdzieli główny token akcentu aplikacji `--system-accent`.
Przy zwiniętym pasku nagłówek grupy z aktywnym podpunktem
także ma czerwony stan. Długie nazwy zachowują wielokropek
oraz pełną nazwę w `title`. Pozostałe podmenu zachowują dotychczasowe drzewka.

Wariant `sidebar-space-row` dodaje „…” widoczne przy najechaniu/fokusie
i otwartym menu; na urządzeniach dotykowych i telefonie przycisk jest stały.
Szare tło wiersza pojawia się przy najechaniu, fokusie klawiatury lub otwartym
menu; sam fokus po kliknięciu myszą go nie utrzymuje. Aktywna przestrzeń
zachowuje własne czerwone zaznaczenie niezależnie od fokusu.
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
zaznaczenie checkboxa utrzymuje to samo czerwone tło i pasek również po
odsunięciu kursora i utracie fokusu, tak jak zaznaczenie w katalogu Projektów.
Include `spaces/issue_type.html` dodaje wspólne oznaczenie `tasks-issue-type`:
ikonę z lokalnego `AncoreIcons` i nazwę typu zgłoszenia na pastelowym tle
o 16% udziału koloru z konfiguracji, takim jak etykieta w ustawieniach.
Ikona etykiety ma neutralny kolor tekstu; geometria wiersza i karty pozostaje wspólna.
Oznaczenie jest widoczne po prawej stronie wiersza, bezpośrednio przed licznikiem
tagów, oraz w metadanych karty; długą nazwę skraca wielokropek, a pełną udostępnia
`title` i etykieta dostępności. Wspólny wiersz `work-issue-row` ma osobną kolumnę
typu również w backlogu i sprintach; „Dla ciebie” zachowuje ten układ bez checkboxa.
Kolumna klucza i tytułu może się zwężać, zachowując wielokropek i jedną linię metadanych.
`IssueTypeSelect` używa istniejących ikon opcji `AncoreCustomSelect` w formularzu
przestrzeni i szczegółach zadania. Kolor typu jest rozwiązywany przez `configuration_name_color('types', ...)`,
nie przez symbol ikony. Domyślne Zadanie jest niebieskie, Błąd czerwony,
Historyjka zielona, a Epik fioletowy; własny kolor nadpisuje tę paletę.
Etykiety używają `issueTypeBadgeStyle` w React i filtra `type_badge_style`
w Django. Zmienna `--tasks-type-icon-color` pozwala zachować ciemną ikonę
etykiety i pełny kolor typu w opcjach formularzy oraz podsumowaniu.
Wariant podglądu opcji `tasks-type-option` zachowuje dotychczasowe 16×16px
ikony, także po wybraniu wartości oraz w pierwszym renderze Django.
Picker ikon nadal pokazuje dotychczasową paletę symboli; ich wybór nie zmienia
koloru zapisanego typu. Bez metadanych koloru wspólny komponent zachowuje
wygląd domyślny. Filtr typu w Przestrzeni korzysta z jej konfiguracji.
Toolbar zawiera filtr „Typ zgłoszenia”;
dotychczasowe pole biznesowe w szczegółach ma etykietę „Kategoria”, a obok
niego znajduje się opcjonalna „Grupa” z pustą opcją „Brak grupy”. Oba pola
korzystają ze wspólnego selektora i automatycznego zapisu. Ich listy
w ustawieniach Przestrzeni używają tabeli i modali Typów zgłoszeń:
wyszukiwania, zaznaczeń oraz edycji nazwy, klucza i opisu. Nazwy kategorii
i grup są zwykłym tekstem, bez ikon i tła etykiety, również w selektorach
zadań. Modale nie mają kolumny podglądu ikony ani kontrolek koloru;
korzystają ze wspólnego układu formularza. Pierwszy render Django zachowuje
tę samą prezentację oraz siatkę kolumn listy co Typy zgłoszeń.
Pierwsza kolumna wiersza zawiera stale widoczny, standardowy `tasks-row-checkbox`
z etykietą zawierającą kod i tytuł zadania. Zaznaczenie myszą lub Spacją podświetla
wiersz przez wspólne style; nie zmienia statusu zadania. Wiersze list,
Backlogu i sprintów nie pokazują menu trzech pasków. W zwykłej liście
checkbox służy lokalnemu zaznaczeniu bez utrwalania wyboru po zmianie widoku;
Backlog zachowuje istniejący pasek planowania zaznaczonych zadań.
Grupowanie dotyczy dostępnej strony wyników; rozróżnia nazwy własnych statusów
nawet wtedy, gdy mają tę samą kategorię. Backlog zachowuje kolejność planowania.
Na telefonie lista zachowuje kolumny i przewija się poziomo we własnym obszarze.
Tablica używa dotychczasowych `tasks-kanban-column` i `tasks-kanban-card`,
włącznie z oznaczeniem zakończonych kart. Nie ma osobnej tabeli ani szarych
paneli zastępujących te komponenty. Filtry korzystają z paska Zadań,
a kolejne wyniki odsłania pasek „Pokaż więcej” pod listą.

Karty tablicy nie mają menu działań; tytuł otwiera zadanie.
Przeciąganie tablicy nadal obsługuje istniejący mechanizm Przestrzeni.
Elementy nie mają klasy `task-row` ani danych dawnego API Kanbana.
`tasks.js` pomija lokalne filtrowanie
grup na `data-work-page`, aby nie ukrywać wyników filtrowanych przez serwer.

`spaces.css` zawiera tylko adaptery kontekstu przestrzeni oraz style katalogów,
podsumowania, osi czasu, raportów i konfiguracji. Geometria wierszy, kolumn, kart i menu
pochodzi ze wspólnych komponentów. [Funkcje](SPACES.md).

Zakładka „Podsumowanie” używa `spaces/summary.html` i lokalnego wariantu
`work-summary` wspólnych `work-panel`. Jest osobistym, konfigurowalnym pulpitem
Przestrzeni. `SummaryDashboard.tsx` umieszcza dotychczasowe dane na siatce
12 kolumn (wiersz 48px, odstęp 12px), a `summaryLayout.ts` rozwiązuje kolizje
przez przesuwanie sąsiednich kafelków w dół. Domyślnie zachowuje
cztery liczniki u góry, przegląd statusów i ostatnia aktywność w pierwszym rzędzie,
priorytety i typy zgłoszeń w drugim, a obciążenie zespołu i opcjonalny postęp
epików poniżej. Panel statusów centruje pierścień SVG o grubości 16 jednostek
(24 dla aktywnego segmentu) w polu `viewBox="0 0 100 100"` obok
zwartej legendy z separatorami wierszy i licznikami na neutralnym tle.
Na telefonie pierścień zmniejsza się do 120px; aktywny podgląd ma liczbę 24px
i ciaśniejszy układ tekstu, by dwuwierszowa nazwa mieściła się w grubszym pierścieniu.
Nagłówek zawija odnośnik,
gdy brakuje miejsca; do 360px legenda przechodzi pod wykres. Wysokość panelu wynika z zapisanego rozmiaru kafelka.
Pierścień i legenda zachowują odcienie statusów zadań, ze wzmocnieniem
przez `color-mix(in srgb, tło 66.9%, kolor statusu 33.1%)` wyłącznie
na segmentach i kropkach. Mieszanie z mocniejszym kolorem statusu zwiększa
widoczność także szarego segmentu; nie używa filtra `saturate`, który
praktycznie nie zmienia bardzo jasnych pasteli. Tekst, tło panelu i lista
zadań zachowują swoje kolory.
Wspólny `--tasks-status-background`
w `theme/elestio.css` jest zdefiniowany raz dla kategorii `status-*`
oraz odpowiadających im nagłówków `tasks-status-block-header--*`
i `tasks-status-subgroup-header--*`. Token `--work-summary-status-color`
łączy to tło z `--tasks-status-color`, również w pierwszym renderze Django.
Własne statusy korzystają z obu wartości swojej kategorii.
„Podział priorytetów” używa szarych słupków opartych na
`--system-interaction`, wspólnych osi oraz poziomej siatki. Skala zaczyna się
od zera i ma trzy oznaczenia, dopasowane do największej liczby otwartych zadań.
Wysokości są liniowe; zero nie tworzy słupka. Kolorowe ikony priorytetów stoją
obok polskich etykiet, a na telefonie nad nimi. „Typy zgłoszeń” mają kolumny
„Typ” i „Rozkład” oraz szare, prostokątne paski o wysokości 24px.
Procenty są wewnątrz pasków; przy małym udziale stoją w jasnej części, a zero
pozostawia pusty pasek z `0%`. Liczby zadań są również obok nazw,
w etykiecie dostępności i podpowiedzi.
Na telefonie rozkład przechodzi pod nazwę typu. Panel zawiera
podkreślony odnośnik do wszystkich zadań. Pozostałe natywne
`progress` w postępie epików zachowują czerwony akcent.
„Obciążenie zespołu” korzysta z tego samego wariantu
`work-summary-bars--distribution`: kolumny „Osoba przypisana” i „Rozkład prac”,
szare paski 24px i procenty wewnątrz. Nazwy zachowują awatary; nieprzypisane
zadania mają neutralną ikonę osoby. Liczby otwartych zadań są obok nazw,
w podpowiedzi i etykiecie dostępności. Podkreślony link „Zmień przypisanie zadań” otwiera listę;
wiersz osoby otwiera jej otwarte zadania. Dłuższe listy przewijają się w kafelku,
na telefonie paski przechodzą pod osoby, a pusty stan nie pokazuje nagłówków kolumn.
Ikony priorytetów i awatary pochodzą ze standardowych include'ów. Panele
zachowują font, ramki, tło, zaokrąglenie i odstępy Ancore. Tytuły paneli,
etykiety liczników oraz nazwy widżetów w edycji i panelu opcji mają
`font-weight: 700`; opisy i wartości zachowują dotychczasową wagę. Przy szerokości
kontenera poniżej 700px wszystkie kafelki tworzą jedną kolumnę w kolejności
położenia na pulpicie, z wysokością dopasowaną do treści. Na telefonie poziome paski
przenoszą się pod etykiety. Długie nazwy zadań, epików i wykonawców zachowują
pełny tekst w `title`; aktywność i dłuższe listy przewijają się w panelu.
Całe podsumowanie przewija się we wspólnym `work-content`.
Korzysta z tego samego wariantu `work-content--items` co lista zadań:
5px nad paskiem filtrów i na dole oraz wspólny odstęp boczny
`--work-space-inline-padding`. Pomiędzy paskiem a pierwszym rzędem gadżetów jest 8px,
tak jak pomiędzy paskiem a listą zadań.

Pasek Podsumowania zawiera to samo menu „Filtrowanie” co w zadaniach
(`ItemFiltering` w `ItemToolbar.tsx`): typ zgłoszenia, wykonawca, status,
priorytet i zespół, wyszukiwanie pól/opcji, licznik aktywnych warunków i „Wyczyść”.
Wybór aktualizuje URL i dane wszystkich gadżetów, zachowując zapisany układ.
Warunki można łączyć, a linki wykresów zachowują pozostałe filtry. Podsumowanie
nie pokazuje menu sortowania zadań. Pierwszy render Django wykorzystuje
wariant `filters_only` wspólnego formularza `spaces/item_toolbar.html`.

„Edytuj pulpit” pokazuje uchwyty, a „Dodaj gadżet” otwiera katalog
w istniejącym `Modal` z wyszukiwaniem i stanem już dodanych pozycji.
Kafelki przesuwa się za nagłówek i skaluje prawym dolnym uchwytem; strzałki
na uchwytach zapewniają obsługę klawiaturą. Escape anuluje bieżący gest.
Na wąskim ekranie kafelki układają się pionowo, a strzałki góra/dół na
zachowanym uchwycie zmieniają ich kolejność. Przeciąganie i uchwyt rozmiaru
są tam wyłączone. Menu kafelka, jego panel pozycji/rozmiaru i wejście
„Usuń gadżet” zostały usunięte bez zastępowania innymi kontrolkami.
„Zapisz układ” utrwala szkic, a „Anuluj” przywraca poprzedni; wspólny guard
chroni niezapisane zmiany podczas nawigacji. Konflikt rewizji zachowuje szkic
i udostępnia wczytanie aktualnego układu po potwierdzeniu odrzucenia zmian.
Backend nadal obsługuje zapis pustego układu.
Po lewej pozostaje filtrowanie, a po prawej „Edytuj pulpit”; pasek nie pokazuje
osobnego tytułu z ikoną ani przycisku „Odśwież”. Edycja jest osobistą preferencją dostępną
dla członka z widocznością Przestrzeni; gość zachowuje tryb tylko do odczytu.
Pierwszy render Django odtwarza zapisany układ i odnośniki. Dodane ponownie
wykresy rejestrują się w obserwatorze animacji, także po zmianie preferencji ruchu.

React `spaces/Summary.tsx` synchronizuje najechanie lub fokus legendy
z pierścieniem: wybrany fragment pogrubia się i zachowuje pełny kolor.
Skalowanie `transform` wokół środka SVG zwiększa widoczny promień z 40 do 44,
a skorygowana grubość daje po skalowaniu 24 zamiast 16 jednostek. Fragment
powiększa się na zewnątrz, zachowując miejsce na tekst w środku. Promień ścieżki
pozostaje stały. Każdy segment jest osobnym łukiem SVG, bez kreskowania zamkniętego
koła, które powodowało dodatkowe fragmenty przy animacji i skalowaniu interfejsu.
Pełne 100% tworzą dwa półokręgi, a zerowy udział nie rysuje łuku. Pierwszy render
Django i React używają tych samych ścieżek z podsumowania. SVG pozwala wyświetlić wysunięty fragment poza
polem wykresu. Zmiana skali i grubości trwa 160ms i respektuje ograniczenie ruchu,
a pozostałe segmenty oraz ich kropki w legendzie przechodzą do 30% krycia.
Środek pokazuje liczbę, nazwę i udział statusu. Nazwa w środku ma limit
dwóch wierszy i 60% szerokości pierścienia, aby nie nachodziła na pogrubiony
segment; pełna nazwa pozostaje w legendzie. Kliknięcie fragmentu otwiera
filtrowaną listę przez wspólny `navigate`; te same akcje są dostępne
klawiaturą przez linki legendy. Escape przywraca łączny wynik.
Zejście kursora, opuszczenie fokusu i Escape przywracają pełne kolory,
gdy nie ma drugiego aktywnego podglądu z myszy lub klawiatury.
Teksty legendy zachowują pełną czytelność. Przejście krycia trwa 160ms;
przy ograniczeniu ruchu zmiana jest natychmiastowa. Panel i pierścień
nie mają animacji przezroczystości podczas wejścia; wyciszenie dotyczy
wyłącznie nieaktywnych segmentów i kropek podczas podglądu statusu.
Priorytety podświetlają wybrany słupek; liczby pozostają nad słupkami,
a liczba i udział są dostępne w etykietach linków dla czytników ekranu.
Pod wykresem nie ma paska „Otwarte zadania” ani podpowiedzi wyboru priorytetu.
Przy pustym zbiorze pozostaje komunikat „Brak otwartych zadań.”.
Karty liczników mają neutralne podświetlenie
i skrót „Wyświetl zadania”. Fokus klawiatury używa wewnętrznego obrysu
przez `box-shadow`, niezależnie od globalnego wyłączenia `outline`.

`SummaryDistribution.tsx` dodaje niezależne kontrolki `%`/„Liczba”
oraz wspólny `Dropdown` sortowania: kolejność domyślna lub najwięcej zadań.
Zmiany dotyczą prezentacji danych już dostępnych użytkownikowi i nie
wykonują zapisów. Szerokości pozostają udziałem w sumie również w trybie
liczbowym; niezerowy udział zaokrąglony do zera ma etykietę `<1%`.
Animowany element wizualny paska zachowuje dokładny udział, a ukryty
natywny `progress` dostarcza wartości technologiom asystującym.
`useSummaryMotion` uruchamia krótkie wejście paneli, rozwinięcie słupków
i pierścienia raz, kiedy panel pojawi się w przewijanej treści.
Wejście paneli zmienia tylko krycie, bez przesuwania całej karty; panel
statusów nie animuje także krycia. Dzięki temu animacja nie powiększa
przewijanej wysokości kafelka i nie wywołuje chwilowych pionowych pasków.
Kafelki nadal przewijają rzeczywiście długą treść lub zawartość niemieszczącą
się w zapisanym rozmiarze.
Hook odłącza obserwator po wyjściu z ekranu. `prefers-reduced-motion` wyłącza
animacje i przesunięcia; bez obserwatora wartości są od razu widoczne.
Szablon Django zachowuje podstawowe wykresy i linki pierwszego renderu.

Liczniki i linki legendy, słupków oraz wierszy pozostają natywnymi linkami
GET obsługiwanymi przez `AncoreApp`. Lista przestrzeni oferuje
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

**Kontekst historyczny:** poniższy opis formularzy Projektów i Grup dotyczy
wycofanych ekranów. Bieżące formularze korzystają ze wspólnych komponentów,
a ich zachowanie opisują rozdziały właściwych modułów powyżej.

Formularze „Nowy projekt” i „Edytuj projekt” miały pole „Widoczność” po prawej
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
okna akceptacji projektu/grupy. Workspace dodaje istniejące konta lub udostępnia
link do dołączenia, zgodnie z sekcją zarządzania Workspace.

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
Zakładka „Udostępnienia” korzysta z istniejącego systemu zakładek `task-work-log.js`
i wspólnej tabeli zespołu. `project-team.js` obsługuje `task-detail-form` oraz
osobny host modali `data-project-team-modal-host="task"`; zachowuje szkic pól,
błędy, fokus, Escape i inicjalizację po `ancore:content-loaded`. Po zapisaniu
widoczności przez AJAX zdarzenie `ancore:task-team-updated` odświeża członków.
Bieżący formularz podzadania używa pełnego wiersza tytułu i ukrytej
widoczności, domyślnie prywatnej, zgodnie z opisem Przestrzeni powyżej.
Historyczny wzorzec tworzenia zadania używa wiersza tytułu z widocznością,
domyślnie „Prywatne — wybrane osoby”. Publiczne zadanie pokazuje dostęp
odziedziczony, bez osobnego przycisku udostępnienia. Prywatne udostępnia się
od razu przez „Udostępnienia” → „Udostępnij”, bez wysłanych zaproszeń.

## 2. Powłoka aplikacji

Domyślny odstęp poziomy treści stron wynosi **15px z obu stron**. Wspólny
token `--app-page-padding-x` w `base/variables.css` określa padding nagłówków,
pasków narzędzi oraz treści Przestrzeni, Zespołów, Filtrów,
Pulpitów, Dla ciebie, Ustawień i siatek Dysku/Dokumentów. Zmienne modułów
`--work-space-inline-padding`, `--dashboard-inline-padding` i
`--documents-index-padding-x` odwołują się do tego tokenu. Reguła obowiązuje
także na telefonie; nagłówki rezerwują dodatkowe miejsce na przycisk menu.
Tabele katalogów korzystają z tego samego odstępu, jak Udostępnienia.
Tablice oraz wewnętrzne odstępy kart, modali i szczegółów zadania zachowują
własną geometrię.

„Dla ciebie” jest osobną pozycją nad Dashboardem, z ikoną `user-round-check`
i obsługą ulubionych menu. Widok rozszerza `core/base.html` i komponenty
Dashboardu: nagłówek katalogu, panele, wiersze i podkreślane zakładki.
Górny pasek zawiera tylko tytuł „Dla ciebie”, bez przycisku „Moje zadania”.
Nagłówek strony i główna treść mają po 15px odstępu z lewej i prawej strony,
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
szerokości. Brak skrótów pokazuje wspólny `EmptyState` bez obramowania
(`for-you-spaces-empty`): ilustrację 440×330px, nagłówek „Brak rekomendowanych
przestrzeni” i opis, z typografią i odstępami pustego pulpitu, bez przycisków.
Gdy rekomendacje i aktywna zakładka są jednocześnie puste, React i szablon
dodają `for-you-page--empty`. Dwa panele dzielą dostępną wysokość treści
na równe wiersze; ilustracje maleją do wolnego miejsca (maksymalnie 320px
szerokości i 200px wysokości, z limitem zależnym od wysokości kontenera).
Nagłówki mają wtedy 24px (20px na telefonie), opisy 14px, a odstępy są
mniejsze. Całe komunikaty mieszczą się bez przewijania przy typowych wysokościach
okna. Widoki z rzeczywistymi rekomendacjami lub wynikami zachowują swój układ
i przewijanie list; pozostałe puste strony używają standardowego rozmiaru.
Pięć zakładek jest linkami z `aria-current`; adresy zachowują kategorię,
Workspace oraz parametry wyszukiwania i przestrzeni z istniejących adresów.
„Polecane”, „Przypisane do mnie”, „Ulubione” i „Ostatnia praca” pokazują
tylko 20 najnowszych pozycji łącznie we wszystkich grupach, bez dolnego licznika
wyników i strzałek paginacji. Wybór opiera się na dacie utworzenia, a w ostatniej
pracy — na czasie aktywności zalogowanej osoby. „Ostatnio oglądane” pokazuje
pierwsze 20 pozycji z ostatnich 7 dni i wspólny pasek „Pokaż więcej” pod listą,
wewnątrz jej przewijanego obszaru. Licznik pokazuje wczytane i wszystkie wyniki.
Pasek używa wspólnych `notifications-tabs work-tabs`, tak jak widoki Przestrzeni:
tekstu 13,5px/400, ikon 18px, odstępu ikona–tekst 8px, wysokości i podkreślenia.
Ikony zakładek to `sparkles`, `user-round-check`, `star`, `clock` i `eye`.
Licznik przypisanych zachowuje szare tło; nieaktywne zakładki pokazują szare
podkreślenie przy najechaniu, a aktywna — czerwone. Wewnętrzny odstęp paska
wynosi 15px również na telefonie, zgodnie z Przestrzeniami.
Lista zaczyna się bezpośrednio pod zakładkami, bez paska filtrów/wyszukiwarki
i paska opisu aktywnej zakładki. Brak wyników dla parametrów w adresie ma osobny
pusty stan z podpowiedzią o wyczyszczeniu filtrów. Linki poza pustym stanem korzystają ze wspólnej nawigacji
`AncoreApp`, także przy Wstecz/Dalej i ponownym wejściu.
Panel „Twoja praca” używa wariantu `for-you-work-panel` bez zewnętrznego
obramowania; grupy zadań/przestrzeni i poziome separatory zachowują swoje ramki.
`for-you.js` utrzymuje aktywną zakładkę w widocznej części paska po wejściu,
częściowej nawigacji i zmianie szerokości. Przewija wyłącznie zakładki, bez
przesuwania strony lub fokusu; odłącza obserwator rozmiaru przy opuszczeniu widoku.
Puste stany wyjaśniają źródło danych każdej zakładki. Wspólny komponent `EmptyState`
pokazuje `spaces-empty.webp` przy braku rekomendowanych
przestrzeni, a każda zakładka ma własny obrazek: Polecane — lista z zielonym
znacznikiem (`for-you-tasks-empty.webp`), Przypisane do mnie — karty z symbolem
osoby (`for-you-assigned-empty.webp`), Ulubione — folder z gwiazdką
(`for-you-starred-empty.webp`), Ostatnia praca — zegar i ołówek
(`for-you-worked-empty.webp`), Ostatnio oglądane — dokumenty z symbolem oka
(`for-you-viewed-empty.webp`). `EMPTY_ILLUSTRATIONS` w `backend/dashboard/for_you.py`
wybiera ilustrację aktywnej zakładki, również przy braku wyników filtrów.
Obrazki z `static/img/empty-states/` mają przezroczyste tło i skalują się do
kontenera: do 440px zarówno w sekcji rekomendowanych przestrzeni, jak i w głównym
pustym wyniku zakładki. Oba korzystają ze wspólnego `EmptyState`. Są dekoracyjne (`alt=""`,
`draggable="false"`); kontener ma `role="status"`, a tekst
korzysta ze wspólnego `tasks-empty-state__copy`. Puste stany nie pokazują linków akcji.
Zakładki pozostają w jednym wierszu i przewijają się poziomo,
gdy brakuje miejsca, także na telefonie. Etykiety i licznik nie zawijają się.
Zadania we wszystkich pięciu zakładkach używają wspólnego `spaces/row.html`,
tak jak „Wyszukaj zadania” w Filtrach: wiersza `tasks-issue-row` z priorytetem,
kluczem, ikoną statusu, tytułem, oznaczeniem typu zgłoszenia, licznikami tagów
i załączników oraz ikoną terminu. Linki klucza i tytułu w „Dla ciebie”
nie mają podkreślenia tekstu, również po najechaniu kursorem.
Wariant `hide_selection=True` nie renderuje
checkboxa ani jego toru siatki w „Dla ciebie”. Lokalizacja i czas ostatniej aktywności są dostępne w `title` linku,
a własna nazwa statusu i termin w etykietach ikon. Liczniki są pobierane zbiorczo
dla zadań bieżącej strony. Przestrzenie w zakładkach „Ulubione” i „Ostatnio oglądane”
używają wspólnego `spaces/directory.html` w wariancie `directory_compact=True`:
trzy kolumny danych w kolejności Przestrzeń z awatarem, Klucz i Opis.
Wariant kompaktowy, tak jak pełny katalog, nie zawiera komórek menu
ani ich toru siatki, także bez JavaScriptu.
`hide_selection=True` usuwa checkboxy wierszy,
checkbox nagłówka i kolumnę wyboru z siatki. Nagłówek kolumn „PRZESTRZEŃ”,
„KLUCZ” i „OPIS” jest ukryty w `for-you-space-sheet`. Katalog Przestrzeni
zachowuje pełny wariant tabeli z widocznym nagłówkiem.
`spaces.services.decorate_directory_spaces` wspólnie przygotowuje
dane tabel w katalogu i „Dla ciebie”; licznik obejmuje tylko widoczne
zadania przestrzeni. Nazwa otwiera przestrzeń. W każdej grupie dat tabela
znajduje się w sekcji
`for-you-space-group`, z taką samą ramką, zaokrągleniem, odstępami i wysokością
nagłówka jak grupy zadań. Wspólny `tasks/includes/issue_group_header.html`
pokazuje neutralny nagłówek „Przestrzenie”, ikonę, liczbę przestrzeni na stronie
w tej grupie dat i przycisk zwijania (mysz/Enter/Spacja). Nagłówki statusów
korzystają z tego samego include przez `status_group_header.html`.
W React obie sekcje renderuje wspólny `shared/StatusGroup`: sekcja Przestrzeni
używa neutralnego wariantu z ikoną warstw, licznikiem po prawej i tym samym
przyciskiem zwijania oraz kontenerem `tasks-issue-list` co zadania. Nie używa
osobnego nagłówka `h3`, który pomijał styl i obsługę wspólnej grupy.
Wiersze mają wspólne 35px wysokości i tekst 13px, zgodnie z `app-data-table`
i tokenami `--data-table-*`. Wariant `for-you-space-sheet` zachowuje wyłącznie
poziome separatory między wierszami, bez pionowych linii między kolumnami.
Komórki danych mają 0,75rem odstępu z obu boków i zawartość wyśrodkowaną
pionowo. Lokalna siatka `320px 150px minmax(320px, 1fr)` wyrównuje wszystkie
wiersze: nazwa zajmuje 320px, klucz 150px, a opis minimum 320px
i pozostałą szerokość tabeli. Długie nazwy mają wielokropek, a pełny tekst
pozostaje w linku i jego `title`. Awatar i nazwa zachowują odstęp 8px.
Wariant `for-you-space-sheet` wyłącza warstwę `::before` przeznaczoną dla
kolumny wyboru, dzięki czemu nie zasłania ona awatara w tabeli bez checkboxów.
Zachowuje wysokość tabeli według liczby wierszy oraz lokalny schemat kolumn,
bez odtwarzania zapisanych preferencji szerokości. Układ jest wspólny dla Reacta,
pierwszego renderu Django oraz zwykłego i scoped URL. Na telefonie tabela
przewija się poziomo we własnym kontenerze.
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
`tasks-space-group-title`: mają sam tekst 13px/400
i cienki separator po etykiecie, bez ikony, tła i ramki. Margines 1rem u góry
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
ani obecne tablice w Przestrzeniach. Kalendarz pokazuje wydarzenia i zadania;
wyszukiwanie zawęża pozycje w wybranym okresie.

**Historyczny układ wycofanego modułu Zadań:** dawne menu używało nazw
„Projekty”, „Grupy” i „Zadania”, w tej kolejności. Poniższy opis zakładek
i ulubionych nie dotyczy bieżących zadań Przestrzeni.
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
czerwonego podkreślenia i tekstu 15px/400, bez osobnej dolnej ramki całego paska.
Najechanie na nieaktywną zakładkę pokazuje identyczne podkreślenie w szarym
kolorze `--system-interaction`; aktywna zakładka zachowuje czerwony pasek.
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
`tasks-icon-button tasks-row-favorite` korzysta z czerwonego akcentu dla
`aria-pressed="true"`. Jego kliknięcie i użycie klawiatury nie otwierają szczegółów.
Gwiazdkę pokazuje wyłącznie katalog „Zadania”. Zapis ulubionych
blokuje przycisk do zakończenia żądania, pokazuje potwierdzenie albo błąd bez
zmiany oznaczenia. Usunięcie z zakładki „Ulubione” odświeża jej wyniki i liczniki,
zachowując URL i przywracając fokus aktywnej zakładce. Puste stany odróżniają
brak elementów kategorii, brak ulubionych i brak wyników wyszukiwania.

Źródło: [core/base.html](../backend/core/templates/core/base.html).

- Stały pasek u góry całej aplikacji (`app-topbar`) jest przezroczysty,
  pokazuje tapetę strony `--app-shell-wallpaper-image` i ma wysokość
  `--app-topbar-height`
  (40px przed skalowaniem UI; 80px w dwóch wierszach do 600px).
  Po lewej zawiera przełącznik Workspace
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
  Przyciski menu, Stickera, powiadomień, ustawień oraz link profilu nie mają
  stałego tła dla aktywnej strony ani otwartego panelu (`active`, `is-open`,
  `aria-expanded="true"`). Szare tło pojawia się przy hover/fokusie klawiatury.
  Awatary Workspace i profilu mają po 33px (`--app-topbar-avatar-size`)
  i są wyśrodkowane pionowo w kontrolkach. Wspólna reguła rozmiaru obejmuje
  bezpośredni awatar przycisku Workspace, z pierwszeństwem przed bazowym
  rozmiarem `space-avatar` (24px); nie obejmuje opcji rozwijanego menu.
  Pasek zostawia po 2px nad i pod kontrolkami (`--app-topbar-padding-y`),
  bez dodatkowej przerwy przed panelami treści. Na telefonie dwa wiersze
  kontrolek rozdziela 4px. Rozmiary kontrolek są lokalne dla paska.
  Odsunięcie treści i menu oraz wysokość panelu wyszukiwania uwzględniają wysokość paska.
  Wysokość pola wyszukiwania obejmuje ramkę; wewnętrzny input wypełnia jej wnętrze.
  Także aktywna wyszukiwarka na telefonie zachowuje tę wysokość i pionowe wyśrodkowanie.
  Przycisk zwijania i rozwijania menu znajduje się przy lewej krawędzi
  górnego paska, przed przełącznikiem Workspace. Korzysta z `tasks-icon-button`
  i wariantu `app-topbar__action`: ma 36px, standardowe zaokrąglenie oraz
  ikonę `panel-left` ze wspólnego zestawu. Rozwinięcie menu nie nadaje mu
  stałego tła; szare podświetlenie pojawia się tylko przy hover/fokusie klawiatury.
  Na telefonie otwiera i zamyka boczne menu, zastępując osobny przycisk
  pod paskiem. Zmiana stanu aktualizuje etykietę i `aria-expanded`;
  użycie przycisku zamyka otwarte panele wyszukiwania i powiadomień.
  Pole używa istniejącego `global-search-form`; wpisywanie, strzałki i skrót
  Ctrl/Cmd+K otwierają panel szybkiego wyszukiwania. Na telefonie nazwy Workspace
  i profilu oraz podpowiedź skrótu są ukryte; wszystkie kontrolki pozostają
  dostępne. Zwinięcie sidebaru nie zmienia przełącznika Workspace ani
  położenia jego menu, które rozwija się pod avatarem w górnym pasku.
  Przycisk Workspace dopasowuje szerokość do zawartości, z ograniczeniem
  do dostępnego miejsca w lewej kolumnie górnego paska; w ciasnym układzie
  skraca nazwę. Jego szerokość nie zależy od szerokości sidebaru.
  Menu zachowuje szerokość docelową 280px (`--app-topbar-workspace-width`)
  z ograniczeniem do szerokości ekranu.
  Na telefonie menu Workspace wyrównuje się do lewej krawędzi paska,
  aby mieściło się w szerokości ekranu.
  Menu, treść, zasłona ładowania oraz panel wyszukiwania zaczynają się
  pod nim, także na telefonie. Modal powiadomień przykrywa również górny pasek,
  zgodnie ze wspólną powłoką „Utwórz zadanie”.
  Wysokość treści uwzględnia pasek, zachowując przewijanie i widoczną dolną
  krawędź. Pasek należy do bloku `app_navigation`, więc nie występuje w osobnym
  edytorze Dokumentów ani na ekranach uwierzytelniania.
- Wyszukiwanie używa wariantu `global-search-panel--quick` wewnątrz formularza
  górnego paska. Panel jest wyśrodkowany pod polem, dopasowany do jego szerokości
  (na węższym desktopie rozszerza się do 640px w granicach ekranu)
  i 620px wysokości, własne przewijanie, wspólny cień oraz zaokrąglenia dropdownów.
  Nie przyciemnia ani nie blokuje treści strony.
  Przed wpisaniem frazy pokazuje do 8 ostatnio oglądanych elementów bieżącego
  Workspace z ponowną kontrolą dostępu; pustą historię zastępuje podpowiedź.
  Nagłówek pustej frazy pokazuje „Ostatnio oglądane” z licznikiem, bez samotnego
  filtra „Wszystko”. Po wpisaniu frazy dostępne są „Wszystko”, „Zadania”,
  „Przestrzenie”, „Dokumenty” i „Pliki”; pozostałe typy pojawiają się przy
  dopasowaniach lub gdy pozostają wybrane. Filtry mają liczniki i przewijają się
  poziomo. Wybór pozostaje aktywny podczas dopisywania frazy, również przy braku
  wyników; pusty stan pozwala wrócić do wszystkich typów. Wyczyszczenie frazy
  resetuje wybór. Pasujące fragmenty tytułu i metadanych mają delikatne tło
  akcentu. Przestrzenie i Workspace pokazują własne ilustracje lub zdjęcia przez
  wspólny `Avatar` (30px); zdjęcia Przestrzeni zachowują kontrolowany adres pobrania.
  Zadania i podzadania pokazują ikonę swojego typu oraz kolory `tasks-issue-type`,
  tak jak Lista zadań. Dotyczy to wyników oraz ostatnio oglądanych.
  Pozostałe typy zachowują swoje ikony. Nagłówek ostatnich używa dostępnej ikony
  `clock`. Wiersze mają tekst 13px i metadane 12px; na telefonie typ przechodzi
  pod tytuł. Stopka podaje liczbę wyników
  i skróty. Nagłówek ma przycisk zamknięcia, także na telefonie.
  Strzałki przenoszą fokus na linki, Enter otwiera wynik, Escape zamyka panel
  i przywraca fokus polu. Najechanie myszą nie zmienia wyboru klawiaturą.
  Enter lub strzałka w zamkniętym polu tylko otwiera panel; nie uruchamia
  ukrytego wyniku. Fokus kontrolek ma widoczny obrys wspólnego akcentu.
  Tab zachowuje naturalną kolejność, a kliknięcie lub
  przeniesienie fokusu poza formularz zamyka wyszukiwanie. Na telefonie aktywne
  pole zajmuje szerokość paska, panel mieści się w ekranie, a podpowiedzi klawiszy
  są ukryte. Do 480px zamknięte pole zachowuje klikalną powierzchnię także
  przy niepustej frazie; przycisk czyszczenia pojawia się po jego otwarciu.
  `ancore:content-unloading` w React czyści frazę i wyniki bez ponownego podpinania
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
  przewijana lista i pasek „Pokaż więcej” pod jej wynikami.
- Osobny host `#app-page-modals` oraz komunikaty `#app-notifications`.
- Wspólne panele wyszukiwania i powiadomień oraz Sticker.

Zwykła nawigacja między ekranami podmienia treść przy zachowaniu bocznego menu,
także pod adresami Workspace. Działają historia Wstecz/Dalej, filtry GET,
powrót ze szczegółów i ponowna inicjalizacja kontrolek. Podczas pobierania obszar
główny ma `aria-busy`. Po 180 ms pojawia się biała zasłona z wyśrodkowanym
wskaźnikiem: cztery szare kwadraty w siatce 2×2 kolejno rozjaśniają się
i wygaszają zgodnie z ruchem wskazówek zegara. Cały wskaźnik ma 24px,
odstęp 3px, a cykl trwa 1,6s; kolor pochodzi z `--system-interaction`,
tło z `--bg-main`. Menu boczne oraz mobilny przycisk menu pozostają aktywne.
`core/includes/content_skeleton.html` zachowuje historyczną nazwę i stały host
poza podmienianą treścią; wspólny `core/includes/loading_indicator.html` służy
również pełnoekranowej zasłonie przeładowania strony, bez ramki i widocznej
etykiety. Style obu wariantów są w `layout/main.css`; geometrię treści
nadal wyznacza `layout/panels.css`. Szybkie odpowiedzi nie pokazują wskaźnika
i nie czekają na animację. Ukryte wskaźniki mają wstrzymaną animację,
a `prefers-reduced-motion` pokazuje cztery nieruchome kwadraty. Zasłonięta
treść ma tymczasowe `inert` przez wspólny mechanizm blokad, a czytnik ekranu
otrzymuje „Wczytywanie widoku…”. Kolejne żądanie zachowuje tę samą blokadę;
błąd usuwa zasłonę i przywraca dostęp oraz wcześniejszy fokus treści,
o ile inny panel nadal jej nie blokuje.

Logowanie, rejestracja oraz tworzenie Workspace po rejestracji pokazują ten sam
pełnoekranowy wskaźnik od wysłania formularza do przekierowania.
`shared/LoadingOverlay.tsx` używa `data-loading-active`, wspólnej animacji
i tekstu statusu dla czytników ekranu. Portal do `body` utrzymuje zasłonę
poza transformacjami okna oraz formularzem z `aria-busy`; współdzielony
`acquireInert` tymczasowo blokuje pozostałą treść. Formularz blokuje ponowne
wysłanie. Błąd usuwa zasłonę, zachowuje dane
i pozwala ponowić zapis. Powrót z pamięci historii przeglądarki resetuje
stan oczekiwania. Pierwszy render Django korzysta z tego samego include'u
i adaptera `auth.js`; bez JavaScriptu pozostaje zwykły POST.
Wybór Workspace po logowaniu, przełącznik w górnym menu i przełączanie
w katalogu Workspace również używają `LoadingOverlay`. Wspólny hook
`useNativeSubmitLoading` zachowuje natywny POST menu i wyboru, blokuje
ponowne wysłanie oraz usuwa zasłonę po powrocie z historii lub anulowaniu
wyjścia z niezapisanymi zmianami. W katalogu stan zasłony jest niezależny
od blokady zapisu, więc obejmuje również przekierowanie do nowego Workspace.
Kreator Przestrzeni używa tego komponentu podczas zapisu wybranego szablonu;
po sukcesie przekazuje sterowanie istniejącej nawigacji. Inne formularze
zachowują swój dotychczasowy stan zapisu. Nie dodajemy sztucznego czasu oczekiwania.

Logowanie, wylogowanie, zmiana Workspace, edytory i adresy spoza listy ekranów
zachowują pełną nawigację. Szczegóły zadania przestrzeni czekają na automatyczny
zapis przed podmianą i zatrzymują nawigację przy błędzie. Pełne wyjście z
niezapisanymi zmianami chroni `beforeunload`. Po podmianie ekran usuwa poprzednie
listenery. Kontrakt i wyjątki opisuje
[cykl życia strony](MECHANISMS.md#12-nawigacja-i-cykl-życia-frontendowej-strony).

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
dla zalogowanego konta. Po wylogowaniu i zalogowaniu na inne konto pojawia się
jego własna notatka (pusta przy pierwszym użyciu); ponowne logowanie na
wcześniejsze konto przywraca poprzednią. Dane starej notatki
bez właściciela nie są automatycznie przypisywane ani wyświetlane innemu kontu.
Powtórna inicjalizacja po nawigacji nie powiela obsługi przycisku.

Przełącznik Workspace w górnym pasku pokazuje avatar i nazwę bez strzałki.
Kliknięcie avatara lub nazwy otwiera dotychczasowe menu wyboru Workspace
z wyszukiwaniem, stanem „Brak wyników” i linkiem zarządzania.
Escape zamyka menu i przywraca fokus na przełączniku. Wybór zachowuje
istniejący formularz POST i pełne przeładowanie kontekstu Workspace.

Nagłówek strony profilu pokazuje tekst „Profil użytkownika” bez poprzedzającej
go ikony. Avatar użytkownika pozostaje w treści profilu. Do 767px nagłówek
zachowuje wspólny odstęp 15px po bokach, jak pozostałe nagłówki stron.

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
[auth_base.html](../backend/accounts/templates/accounts/auth_base.html), z tapetą aplikacji
i białym prawym panelem formularza. Zachowują wspólny Atlassian Sans; szczegóły
wariantu opisuje rozdział [Konta w React](#konta-w-react).

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
  → komponenty (m.in. buttons, forms, tables, tasks, shared-controls, workplaces)
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

Wspólne menu profilu, selecty i kadrowanie obrazów należą do
`components/shared-controls.css`. Prefiksy klas `contacts-actions-menu`,
`contacts-custom-select` i `contacts-photo-editor` są zachowanym kontraktem
komponentów. Nie oznaczają modułu Kontaktów; jego style katalogów usunięto.

## 4. Tokeny i język wizualny

Wartości poniżej pochodzą z aktualnych deklaracji CSS. Preferuj użycie
zmiennej zamiast powielania wartości liczbowej.

| Obszar | Token / obecna wartość |
| --- | --- |
| Font aplikacji | `--font-family-ui`: `Atlassian Sans`, fallback systemowy |
| Mały/podstawowy/większy tekst | `--font-size-sm: 13px`, `--font-size-base: 14px`, `--font-size-lg: 15px` |
| Zwykły tekst | `--text-primary: #40444C` |
| Tekst na akcencie | `--text-inverse: #FFFFFF` |
| Główny akcent | `--system-accent: #df2b2b`, `--system-accent-rgb: 223, 43, 43` |
| Interakcje | `--system-interaction: #6f7580`, miękkie tło z alfa 0.1 |
| Szare podświetlenie menu bocznego | `--sidebar-interaction-bg` (6% krycia `--system-interaction`), naciśnięcie: `--sidebar-interaction-pressed-bg` (10%) |
| Wybrana pozycja menu bocznego | `--sidebar-space-selection: var(--system-accent)`, tekst/ikony: `--sidebar-space-selection-ink` (60% akcentu z czernią), tło `--sidebar-space-selection-bg` (10% krycia akcentu), `--sidebar-space-selection-hover-bg` (16%); znacznik i ramka fokusu zachowują bazowy akcent |
| Główna powierzchnia | `--bg-main: #ffffff`, `--card-bg: #ffffff` |
| Tło zastępcze strony za panelami | `--app-shell-bg`: 12% `--system-interaction` zmieszane z `--card-bg` |
| Tapeta strony za panelami | `--app-shell-wallpaper-image`: `wallpaper-red-black-white.png`, `left center / cover` |
| Nawigacja pomocnicza | `--secondary-menu-bg: #FBFBFC` |
| Tło panelu | `--panel-bg: #f7f6f4` |
| Delikatna ramka | `--border-color: #e0ddd9` |
| Standardowa kontrolka | `--control-height: 32px` |
| Dropdown | kontrolka 36px, radius 6px; menu radius 7px, element 32px |
| Checkbox | `--checkbox-size: 18px` |
| Standardowe zaokrąglenie | `--radius: var(--radius-max)`, bazowo 8px |
| Pasek narzędzi | `--toolbar-height: 52px` |
| Odstęp treści stron od lewej i prawej krawędzi | `--app-page-padding-x: 15px` |
| Sidebar | bazowo 272px; zwinięty 64px; JS pozwala regulować 220–420px |
| Odstęp paneli powłoki | `--app-shell-gap`: 4px na każdej szerokości |
| Odstęp nad i pod kontrolkami górnego paska | `--app-topbar-padding-y`: 2px |
| Promień paneli powłoki | `--app-shell-radius`: 15px |
| Prawy panel boczny | `--app-right-sidebar-default-width`: 272px (zadanie 370px); `--app-right-sidebar-user-width` zapisany wybór 240–520px; `--app-right-sidebar-width` bieżący rozmiar; do 1100px szuflada |
| Skala UI | `--app-ui-scale: 0.98`, stosowana przez `zoom` w resecie |

Główny akcent `#df2b2b` jest ciemniejszym wariantem czerwieni nowego logo
`#ff3131`. Zapewnia kontrast białego tekstu 4,65:1 na pełnym akcencie.
Logo `static/img/logo.png` zachowuje oryginalne kolory i proporcje; używają go
powłoka, ekrany kont i favicon. Edytor tablicy w iframe ładuje te same tokeny
z `base/variables.css`, a paleta kontrolek Excalidraw jest ich adapterem.
Wspólne kontrolki, aktywne zakładki, zaznaczenia, postęp i jasne tła
przycisków korzystają z `--system-accent` oraz jego wariantu RGB.
Interakcje neutralne zachowują szarości; kolory danych i ilustracji
pozostają niezależne od akcentu aplikacji.

Neutralne obramowania i separatory są przyciemnione o kolejne 3% względem
palety po wcześniejszej korekcie 2% (kanały sRGB × 0,97, zaokrąglone do liczb
całkowitych). Dotyczy to wspólnych tokenów oraz lokalnych odcieni ramek
i tabel w komponentach. Grubości linii,
przezroczystość, białe obwódki i kolory stanów/akcentów pozostają bez zmian.

Ważne wyjątki:

- `--text-muted`, `--text-main`, `--text-strong` są aliasami tej samej podstawowej
  barwy. Nazwa „muted” nie upoważnia do wprowadzania nowego jasnoszarego tekstu.
- `--accent-red`, `--accent-blue`, `--accent-peach` są historycznymi aliasami;
  wskazują wspólny czerwony akcent Ancore.
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
| Katalog Przestrzeni | [spaces/directory.html](../backend/spaces/templates/spaces/directory.html) | `components/tasks.css`, `tasks.js`, React `spaces/DirectoryPage.tsx` |
| Tytuł i toolbar katalogu | [toolbar Dysku](../backend/documents/templates/documents/toolbar.html) jako przykład użycia wspólnych klas | `tasks-topbar`, `tasks-filterbar`, `tasks-filter-button`, `tasks-search-field` |
| Kolejne wyniki | [load_more.html](../backend/core/templates/core/includes/load_more.html), [LoadMore.tsx](../frontend/app/src/shared/LoadMore.tsx) | Po 20 wyników, licznik wczytane/wszystkie, zachowanie wierszy |
| Zarządzanie kolumnami | [directory_column_manager.html](../backend/tasks/templates/tasks/includes/directory_column_manager.html) | `tasks.js`, zapis ustawień lokalnych |
| Agregat filtrów | [directory_filter_aggregate.html](../backend/tasks/templates/tasks/includes/directory_filter_aggregate.html) | Wspólne menu i aktywny stan |
| Wiersz zadania | [spaces/row.html](../backend/spaces/templates/spaces/row.html) | Stan, uprawnienia, `data-task-*`, ikony, JS listy |
| Karta tablicy Przestrzeni | [spaces/card.html](../backend/spaces/templates/spaces/card.html) | Status, kolejność i przeciąganie |
| Standardowy modal formularza | [form.html Dysku](../backend/documents/templates/documents/form.html), modale projektów/zadań | `tasks-modal*` + `modal-system.css` |
| Potwierdzenie | [modal.js](../static/js/modal.js) | `showConfirmModal`, `dialogs.css` |
| Zwykłe przyciski | [buttons.css](../static/css/components/buttons.css) | `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-sm`, `.btn-cancel` |
| Formularz/dropdown | [forms.css](../static/css/components/forms.css), [custom-select.js](../static/js/custom-select.js) | `.form-input`, `.form-select`, `.ancore-custom-select*` |
| Checkbox | [checkboxes.css](../static/css/components/checkboxes.css) | Wspólna geometria i stany |
| Avatar konta | [user_avatar.html](../backend/accounts/templates/accounts/includes/user_avatar.html) | Helper `accounts.avatar`, zdjęcie/fallback/status |
| Priorytet | [priority_icon.html](../backend/core/templates/core/includes/priority_icon.html) | Istniejąca symbolika priorytetów |
| Ikony załączników | [attachment_icon.html](../backend/core/templates/core/includes/attachment_icon.html) | `attachment-icons.js`, format i typ pliku |
| Wiersz ustawień | [settings_row.html](../backend/dashboard/templates/dashboard/includes/settings_row.html) | `settings.css` |

Referencje pokazują bieżące wzorce kodu, a nie polecenie skopiowania całych
ekranów. Szablony mają wymagany kontekst i kontrakt z JS. Przy użyciu include'a
sprawdź wszystkie jego zmienne oraz miejsca wywołania.

### Tabele katalogów według Udostępnień

Pełne listy Przestrzeni, Pulpitów, Filtrów, Tagów, Zasobów, Workspace,
Dysków i Dokumentów oraz lista plików na Dysku zachowują wspólny boczny
odstęp `--app-page-padding-x` (15px), jak tabela Udostępnień. Pasek filtrów
tych katalogów nie dodaje dolnej linii nad nagłówkiem tabeli.
Wspólne reguły w `components/tasks.css` obejmują React i pierwszy render Django.
Kontener ma szerokość automatyczną uwzględniającą oba marginesy, bez dodatkowego
paddingu; szeroka tabela przewija się wewnątrz niego również na telefonie.
Kolumny, zaznaczanie i zmiana szerokości zachowują dotychczasowe mechanizmy;
kolejne wyniki udostępnia wspólny pasek „Pokaż więcej”. Udostępnienia i Typy zgłoszeń mają już ten sam
układ. Tabele osadzone w modalach, dziennik pracy i skrót „Dla ciebie”
korzystają z odstępów własnego rodzica, bez dodawania kolejnego marginesu.

### Ikony notatek i zachowane skróty

Kolumny edycji, informacji i notatek w Tagach pozostają dostępne zgodnie
z dotychczasowym wyborem kolumn i uprawnieniami. Ich nagłówki są wizualnie
puste i zachowują etykiety dostępności. Usunięcie hamburgerów nie usuwa tych
skrótów ani checkboxów. Tabela nadal przewija się poziomo na wąskim ekranie.

Przycisk notatek używa wspólnego stanu
`.tasks-project-sheet__notes-button.has-notes`. Gdy istnieje wpis, ikona ma
żółty kolor `#d4a000`; tło i stany interakcji przycisku pozostają standardowe.
Pusty stan zachowuje szarą ikonę kartki z plusem. Stan wynika z zapisanych
notatek, także po ponownym wejściu.

Dawne osobne katalogi Projektów, Grup, Kontaktów i Kanbana są wycofane.
Ich historyczne kolumny menu oraz dawne układy skrótów nie stanowią wzorca
aktywnej aplikacji.

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
i strzałkę powrotu. Pasek „Pokaż więcej” znajduje się pod wynikami.
Filtry i sortowanie używają wspólnego mechanizmu grup; wewnątrz projektu
nie ma dodatkowego wyboru projektu w filtrach. Czyszczenie filtrów,
wyszukiwanie i zmiana strony zachowują otwarty projekt oraz Workspace.
Na telefonie nagłówek projektu pozostawia miejsce po lewej na przycisk
nawigacji aplikacji, aby strzałka powrotu pozostała dostępna.

### Limit zadań według stanu

Historyczne listy „Zadania” i „Zadania nieprzydzielone” oraz ich przełącznik
„/ stan” są wycofane. Aktualne zadania Przestrzeni mają osobne okna po 20
w grupach statusów, doładowywane przez „Pokaż więcej”. Pozostałe listy
korzystają z tego samego wzorca opisanego na początku tego dokumentu.

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
Typ rozróżnia wyłącznie lewa ramka 3px: czerwień `--system-accent` dla sukcesu
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
Po najechaniu na aktywny przycisk udział czerwieni rośnie do 24%, z przejściem
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
jasna czerwień przechodzi po najechaniu w mocniejszy odcień, z ciemnym tekstem.
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

Interakcja myszą nie dodaje zewnętrznego obrysu ani poświaty. Klawiatura
korzysta natomiast ze wspólnego wskaźnika `:focus-visible` w `style.css`:
wewnętrzny obrys 2px w kolorze `--system-accent`, uwzględniający skalę UI.
Ujemny offset utrzymuje go wewnątrz kontrolki, również przy przewijanych
tabelach i zakładkach. Checkboxy i radio mają obrys odsunięty o 2px na zewnątrz,
aby był widoczny także na czerwonym zaznaczeniu i stanie pośrednim.
W trybie wymuszonych kolorów używa systemowego
`Highlight`. Dotyczy to także uwierzytelniania, formularzy i okien.
Pola tekstowe, liczbowe, daty i `textarea`, w tym wyszukiwarki list wyboru,
nie otrzymują tego obrysu w zwykłym trybie kolorów. Zachowują dotychczasowe
obramowania, kolory błędów i fokus. Przyciski potwierdzenia, anulowania
i zamknięcia w `.confirm-modal` również nie otrzymują czerwonego obrysu;
zachowują dotychczasowe tła interakcji i obsługę klawiatury.
Potwierdzenia zbudowane przez wspólny `Modal` stosują w tym celu klasę
`app-confirmation-modal`, m.in. zmiany dostępu i usuwanie konfiguracji Przestrzeni.
Pozostałe przyciski, opcje, checkboxy i radio nadal używają wskaźnika klawiatury.
Nie wyłączaj fokusu pozostałych kontrolek i nie dodawaj lokalnej poświaty;
tokeny cieni `--focus-ring` i `--checkbox-focus-ring` nadal mają wartość `none`.
Zwykłe obramowania i geometria kontrolek pozostają bez zmian.

### Tabele i formularze Dysku

Nawigacja główna i ulubione używają nazwy „Dysk” oraz ikony Flaticon pod nazwą aplikacji `hard-drive`.
Indeks nosi tytuł „Dyski”, tworzenie — „Nowy dysk”, edycja — „Ustawienia dysku”.
Każdy dysk zawiera własne foldery i pliki. Zdjęcia referencyjne ilustrują tę
organizację i układy lista/kafelki; wygląd zachowuje tokeny oraz komponenty Ancore.

Przełącznik `documents-display-switch` używa dwóch linków `tasks-icon-button`
z etykietami „Lista” i „Kafelki” i `aria-current` dla aktywnego układu.
Serwer renderuje jeden układ, bez ukrytej kopii tabeli. Kafelki tworzą semantyczną
listę w `documents-grid`, z ikoną, nazwą do dwóch linii i pełnym tekstem w linku,
metadanymi oraz wspólnymi akcjami z tabeli. Układy dotyczą zawartości dysków
i Dokumentów. Wspólny komponent
`documents-card` zachowuje proporcje kwadratu (`aspect-ratio: 1`). Pole podglądu
wypełnia dostępną wysokość, z minimum 100px, bez osobnego tła — ikony są
na białej powierzchni kafelka. Ikony plików mają 115,5×115,5px.
Ikony pustych i pełnych folderów mają
149,68×149,68px — są powiększone o kolejne 5% względem poprzednich 142,55px,
bez zmiany wymiarów kafelków ani pozostałych ikon.
W ciasnych kolumnach zawartość kafelka można przewinąć bez zmiany jego proporcji. Rozmiar ikon kafelków nie zmienia ikon
w tabeli ani panelu bocznym.
Siatka dopasowuje liczbę kolumn do miejsca z minimalną szerokością kolumny
248px (lub całą dostępną szerokością, gdy jest węższa), również na telefonie.
Kafelek zajmuje całą szerokość kolumny, więc odstępy między kafelkami wynikają
wyłącznie z `gap`: 16px w obu kierunkach, a na ekranach do 767px — 12px.
Dotyczy folderów, plików i Dokumentów. Kafelki pozostają kwadratowe;
rozmiary tekstu, ikon oraz przycisków pozostają bez zmian.
Stopka kafelka pokazuje datę, bez przycisku menu i jego akcji.
Kafelki używają tokenów powierzchni, ramek i fontów Ancore. Pasek Dysków nie zawiera
przycisku „Zarządzaj tabelą”; listy plików pokazują wszystkie kolumny,
także przy zapisanych wcześniej preferencjach ich ukrywania. „Nowy folder” używa
istniejącego drugorzędnego przycisku w pasku, obok „Prześlij pliki”. Wyszukiwanie ma widoczny
opis zakresu obejmującego podfoldery i akcję czyszczenia pustych wyników.

`documents.css` zachowuje semantyczne tabele plików, dopasowane do
katalogu projektów: tekst 13px, nagłówki 35px, wiersze plików minimum 36px, białe tło,
delikatne podziały poziome i pionowe z tokenu `--tasks-directory-column-separator` oraz szare
podświetlenie hover/focus. Wiersze plików mogą być wyższe, aby pomieścić
drugą linię z lokalizacją. Lista nie wyświetla pod nazwą etykiety „Folder” ani
typu pliku (np. „PDF”, „JPEG”); bez lokalizacji nie tworzy drugiej linii.
Lista plików i folderów Dysku (`documents-main`) zachowuje wspólne odstępy
tabeli. Komórka nazwy zaczyna się od ikony pliku lub folderu, bez menu działań.
Nie ma osobnej kolumny akcji. Usunięto także menu na kafelkach; nie dodano
zastępczych przycisków przenoszenia, edycji metadanych, gwiazdki, pobrania
folderu, usuwania ani przywracania z kosza. Istniejące odnośniki nazw
oraz obsługa przeciągania pozostają. W zbiorczym widoku gwiazdek folder
pokazuje nazwę dysku jako link, tak jak lokalizacja pliku.
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
Dyski w prawym panelu używają płaskiej, poziomej obudowy z include'a
`documents/includes/drive_icon.html`. SVG korzysta z zapisanego koloru
(domyślnie `#4285d4`) i białych detali; jest dekoracyjne, bez obrysu ani fokusu.
Ikona w panelu ma 30×30px również na telefonie. Nawigacja, formularze
i globalne wyszukiwanie zachowują ikonę Flaticon `hard-drive`.

Formularz tworzenia i ustawień dysku zawiera nazwę, kolor ikony i opis.
Tworzenie oraz edycja folderów Dysku zawierają nazwę i kolor.
Przycisk ołówka ma etykietę „Edytuj folder”. Wspólny include
`documents/includes/color_field.html` używa natywnego pola `type="color"`
z własną klasą `documents-color-input`, podglądu SVG 64×64px
i przycisku „Domyślny”. Wybrany kolor widać od razu w podglądzie; zapis
aktualizuje listy i kafelki folderów oraz panel dysków. Formularz zachowuje kolor
przy błędzie nazwy. `documents.js` obsługuje pole przez delegację zdarzeń
i `AbortController`, także po `ancore:content-loaded` i otwarciu modala.
Nazwy pozostają widoczne niezależnie od koloru.
Nie udostępnia wyboru zdjęcia ani kadrowania. Wcześniej zapisane zdjęcia
nie są wyświetlane; panel dysków zawsze używa wspólnej ikony.

Indeks „Dyski” jest ekranem wyboru. Lista dysków występuje wyłącznie
w prawym panelu; środek nie pokazuje tabeli ani kafelków dysków, ich
checkboxów, filtrów, wyszukiwania ani przełącznika układu. Zachowuje nagłówek
z „Nowy dysk” oraz wspólny `EmptyState`: „Wybierz dysk” z opisem
„Otwórz dysk z prawego panelu, aby zobaczyć foldery i pliki.”.
Przycisk „Wybierz dysk” otwiera prawy panel przez `openRightSidebar`, również
na telefonie i po zwinięciu panelu. Pierwszy render używa tego samego wzorca
oraz `data-document-open-sidebar` w adapterze JS.
Jeżeli Workspace nie ma dysków, pozostaje istniejący stan „Utwórz pierwszy dysk”.
Stare parametry indeksu, np. `display=grid` i `q`, nie przywracają centralnej listy.

Po wybraniu dysku środek pokazuje foldery i pliki z dotychczasowym paskiem
narzędzi, listą/kafelkami, filtrami i „Pokaż więcej”. Przycisk
`documents-view-selector` za sortowaniem pokazuje otwarty dysk lub nazwę
zbiorczego widoku. Menu zawiera Dyski, Wszystkie pliki, Ostatnio zmienione,
Oznaczone gwiazdką i Kosz; liczniki obejmują cały Workspace.
Zachowuje wspólne kontrolki, natywny popover, obsługę klawiatury i powrót fokusu.
Lista folderów i plików pokazuje „Nazwa”, „Zmodyfikowano” i „Rozmiar”,
bez kolumny tagów i menu w nazwie. Minimalna szerokość tabeli wynosi 690px;
węższy obszar zachowuje kolumny przez przewijanie poziome.
Rozmiar folderu sumuje aktywne pliki w podfolderach w zakresie właściciela
oraz Workspace. W koszu data usunięcia pozostaje w `title` komórki daty.
Foldery pokazują datę utworzenia, ponieważ model nie zapisuje daty modyfikacji.

W module Dysk listę dysków renderuje wspólny prawy panel aplikacji.
Jest dostępna na stronie wszystkich dysków, w listach/kafelkach plików,
wewnątrz dysku i folderu oraz w widokach ostatnich plików, gwiazdek i kosza.
Zastępuje tam kalendarz i „Plan na dziś”; nie tworzy drugiego panelu w treści.
Moduł Dokumenty zachowuje dotychczasowy panel z kalendarzem.
Panel ma białe tło `--bg-main`, nagłówek „Dyski”, dodawanie dysku (zgodnie
z uprawnieniami) oraz autoryzowaną listę Workspace. Nie zawiera skrótu „Wszystkie dyski”.
Przełączanie widoków plików pozostaje na pasku narzędzi za sortowaniem.
Aktywny dysk jest wyróżniony także w podfolderze. Lista doładowuje się po 20
przez „Pokaż więcej”, niezależnie od tabeli i jej zaznaczeń; wejście do
późniejszego dysku odsłania część listy obejmującą jego aktywny wiersz.
Pusty panel pokazuje „Brak dysków w tym Workspace.”, a błąd doładowania
zachowuje dotychczasowe wyniki i umożliwia ponowienie.
Linki dysków używają wariantu `documents-sidebar-library-link`:
minimum 40px wysokości, pole ikony 30×30px i odstęp 10px od nazwy.
W polu jest wspólna ikona dysku w zapisanym kolorze; nazwa ma ellipsis
oraz pełny tekst w `title`.
`documents/Sidebar.tsx` korzysta z `shared/RightSidebarContent`, a szablony
Django wypełniają blok `right_sidebar` przez `documents/sidebar.html`.
Wariant `.documents-sidebar--global` ma stały nagłówek i przewijaną nawigację.
Zwijanie, zapamiętana szerokość i szuflada do 1100px korzystają ze wspólnej
powłoki i przycisku w topbarze. Lokalny przełącznik w toolbarze, własne tło
szuflady i preferencja `ancore:documents:sidebar-collapsed:v1` nie są używane.
Przeciąganie plików/folderów na dysk zachowuje istniejący mechanizm
przenoszenia i kontrolę uprawnień również po przeniesieniu panelu.
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
(`root`), bez przeciągania wierszy i kafelków między lokalizacjami. Prawidłowy cel podświetla się istniejącym czerwonym akcentem
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
Kosz nie udostępnia przeciągania. Usunięte menu nie udostępnia już
formularza „Przenieś”; nie dodano innego wejścia w wierszu.

Filtry Dysku używają panelu `tasks-project-filter-builder` i wspólnych
szablonów warunków tekstowych oraz wyboru wartości. Lista pól i aktywne warunki
pochodzą z `backend/documents/query.py`; obsługę wyszukiwania, czyszczenia i nawigacji
zapewnia `tasks.js`. Panel sortowania
[directory_sort_builder.html](../backend/tasks/templates/tasks/includes/directory_sort_builder.html)
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
Gość Workspace widzi nazwę jako zwykły tekst `office-suite-title-text`,
bez przycisku, pola edycji i instrukcji zapisu. Wariant zachowuje wymiary,
odstępy i wielokropek nazwy, bez hover ani dodatkowego punktu fokusu.
Dotyczy Reacta oraz pierwszego renderu Django w Dokumentach i Dysku.

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
Wiersze mają 35px wysokości; nagłówki z ikonami, tekst, separatory, czerwone
podświetlenie oraz pasek przy lewej krawędzi po najechaniu pochodzą ze wspólnego CSS.
Pierwsza kolumna 40px zawiera stale widoczne checkboxy w wariancie
`tasks-project-sheet--selectable`, tak jak lista Dysków. Wspólna obsługa
`data-document-selection` w `documents.js` zaznacza pojedyncze wiersze lub
wszystkie wczytane wiersze, pokazuje częściowy wybór w nagłówku i podświetla wiersze.
Cała kolumna wyboru jest klikalna. Działa również w koszu i po częściowej
nawigacji. React zachowuje wybór podczas doładowania; filtr, sortowanie
lub pełne przeładowanie zaczynają nowy wybór.
Po kolumnie wyboru występuje nazwa z kolorową ikoną pliku 32×32px.
Dokumenty mają jeden płaski katalog, bez folderów i ścieżki lokalizacji.
Menu wierszy i kafelków zostały usunięte wraz z wejściami do gwiazdki,
edycji metadanych, pobierania i kosza. Link nazwy nadal otwiera dokument.
Pusty widok gwiazdek dotyczy dokumentów.
Pusty stan zachowuje własne odstępy i wyśrodkowanie.
Lista pokazuje trzy kolumny danych: „Nazwa”, „Zmodyfikowano” i „Rozmiar”.
Nazwa wypełnia wolne miejsce, długi tekst ma wielokropek i pełną treść w `title`.
Data ma 176px, rozmiar 120px z wyrównaniem do prawej. Minimalna szerokość
wynosi 616px; na telefonie wszystkie kolumny pozostają w przewijanym obszarze.
Wariant ma `data-directory-resize="false"` i semantykę ARIA tabeli, wierszy oraz
komórek. Pusty stan nie renderuje nagłówków i mieści się w szerokości ekranu.
Tagi nie są dostępne w kafelkach, filtrach, oknie „Dane dokumentu” ani
starszym edytorze tekstu. Aktywne filtry pozostałych pól mają nad listą akcję
czyszczenia i pozostają przy wyszukiwaniu, sortowaniu, doładowaniu i zmianie
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
Pod wynikami znajduje się wspólny pasek „Pokaż więcej”, po 20 pozycji.
React zachowuje wyszukiwanie z opóźnieniem i Enter, układ oraz widok.
Układ należy do adresu formularza wyszukiwania, a nie do zbioru
czyszczonych filtrów. Filtry i sortowanie rozpoczynają okno od pierwszych
20 pozycji; doładowanie zachowuje bieżące filtry i zaznaczenia. Na telefonie
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
CSS aplikacji i używa turkusowego akcentu. Tablica nie pokazuje hamburgera
ani jego menu: pusty `MainMenu` oraz lokalny selektor
`#board-root .excalidraw .main-menu-trigger` usuwają tę kontrolkę bez zmian
w kodzie vendora. Zapis automatyczny i Ctrl/⌘+S pozostają aktywne.
Katalog ma dwa wspólne paski:
tytuł oraz narzędzia z wyszukiwaniem; „Pokaż więcej” jest pod wynikami.
Tworzenie dokumentów oraz upload są dostępne jako kafelki bez nagłówka;
górny pasek nie zawiera przycisków tych akcji. Pod paskiem narzędzi, nad listą
plików, sekcja `office-quick-create` pokazuje siedem skrótów:
dokument, arkusz kalkulacyjny, prezentację, PDF, formularz PDF, tablicę
i „Prześlij dokumenty”. Nie ma kafelka „Z szablonu”; usunięte menu dokumentu
nie udostępnia już tworzenia kopii szablonu.
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
Tekstowy Dokument Ancore otwierany przez gościa ma tytuł „Podgląd dokumentu”,
nieedytowalną nazwę i treść oraz status „Dostęp tylko do odczytu”. Brakuje
przycisku zapisu, narzędzi formatowania i konwersji; Ctrl/⌘+S nie zapisuje.
Pobranie DOCX pozostaje dostępne. Treść HTML przechodzi przez `clean_content`,
również w pierwszym renderze Django. Wyjątek odczytu tekstu nie odblokowuje
formularzy tworzenia ani metadanych plików; serwer odrzuca zapis także przez API.
Obecność gościa nie wyłącza edycji pozostałym uprawnionym osobom.

Statusy zapisu są potwierdzane przez serwer. Tablica przy błędzie zachowuje
scenę; usunięte menu nie udostępnia już pobrania jej kopii. Iframe zachowuje
adapter zapisu/pobrania i przyjmuje wyłącznie komunikaty z okna rodzica
tego samego originu.

Listy i kafelki Dysków, plików, folderów oraz Dokumentów nie renderują
hamburgerów ani powiązanych paneli menu. Tabele Dysków i Dokumentów nie
rezerwują ich kolumn. Puste stany nadal ukrywają nagłówki. Nie przeniesiono
usuniętych akcji w inne miejsce; istniejące endpointy i ich kontrola dostępu
pozostają niezależne od widocznych kontrolek. Ekran historii wersji jest wycofany.

### Dashboard bieżącego Workspace

`dashboard/home.html` rozszerza `dashboard/pulpits/detail.html`, a przez niego
wspólną powłokę `core/base.html`. Strona główna i `/dashboards/default/` używają
tych samych nagłówków, siatki, pustych stanów, CSS i `pulpits.js` co nowe pulpity.
„Edytuj pulpit” prowadzi do wspólnego edytora z menu „Gadżety i układ”
i „Ustawienia”. Pierwsze wejście pokazuje jeden „Postęp pracy”; kolejne odczytują
zapisany układ i gadżety. Przegląd nie pokazuje kontrolek zmiany gadżetów.
Nazwa i opis są edytowalne, a osobista pozycja „Pulpit domyślny” pozostaje w menu.
Nie ma akcji „Usuń pulpit” dla rekordów domyślnych. Menu usuwania pojedynczych
gadżetów jest usunięte; backend zachowuje możliwość zapisu pustego układu.
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

Zakładki „Główna”, „Podzadania”, „Dziennik pracy”, „Udostępnienia” i „Historia”
znajdują się w nagłówku głównej treści zadania. Panel właściwości zajmuje
prawy pasek wspólnej powłoki, obok nagłówka i treści. Pasek `notifications-tabs work-tabs` ma boczny odstęp
`--app-page-padding-x` i tekst 13,5px, tak jak w Przestrzeni. Wspólne style
obejmują linki widoków i przyciski zakładek; aktywny przycisk zachowuje
`aria-selected` i czerwone podkreślenie. Treść lewej kolumny bieżącego zadania
Przestrzeni ma od krawędzi strony odstęp `--app-page-padding-x` (15px), przez lokalny
`--tasks-issue-content-padding-x`, i całą pozostałą szerokość bez limitu 980px.
Treść zachowuje po 15px z obu stron na wszystkich szerokościach. Wyjątkiem
jest sekcja tematu i opisu (`tasks-issue-overview`), która ma po 50px wcięcia.
Po przeniesieniu właściwości do prawego paska `tasks-issue-main` ma jedną
kolumnę, więc czat, historia i pozostałe zakładki wypełniają główny obszar.
Dekoracyjne ikony z `AncoreIcons` oznaczają dokument
przy „Główna”, listę przy „Podzadania”, zegar przy „Dziennik pracy”, osoby
przy „Udostępnienia” i strzałkę historii przy „Historia”. Mają 18px i odstęp 8px
od etykiety, tak jak zakładki Przestrzeni; dziedziczą kolor tekstu. Pasek
zachowuje przewijanie poziome na telefonie i obsługę klawiatury.
Edytowalny tytuł w treści tych widoków ma 20px,
także na telefonie, zgodnie z rozmiarem nagłówków standardowych modali.
Pod paskiem zakładek jest wspólna dolna ramka nagłówka na całą szerokość.
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
Panel szczegółów jest wspólny dla wszystkich zakładek otwartego zadania.
`TaskPage` renderuje istniejące pola przez `shared/RightSidebarContent` do
trwałego `#app-right-sidebar-content`, poza korzeniami strony i powłoki React.
Pierwszy render korzysta z bloku `right_sidebar` oraz
`spaces/task_sidebar.html`. Podczas montowania strony usuwana jest tylko
zawartość `[data-right-sidebar-fallback]`; portal jest usuwany razem z ekranem,
więc następna strona nie pokazuje danych poprzedniego zadania.

Panel ma obrys i promień wspólnego prawego paska, bez drugiej karty wewnątrz.
Sekcje i kontrolki zachowują istniejący wygląd. Ma szerokość 370px i własne
przewijanie, a na wąskim ekranie otwiera się jako szuflada. W tej szufladzie
błąd zapisu i przycisk ponowienia są dostępne nad właściwościami. Zwijanie
zachowuje szkic pól oraz preferencję powłoki. Pola portalu wskazują natywny
formularz `space-task-form`; autosave nasłuchuje dokumentu i sprawdza
`input.form`, zachowując jeden `FormData`, kolejność zapisu, walidację i ACL.
Podzadania nadal otwierają się przez zakładkę rodzica oraz istniejący modal;
przeniesienie panelu nie zmienia tego przepływu.

Automatyczny zapis obejmuje pola treści i prawego paska na każdej zakładce.
„Dodaj czas” pojawia się
po prawej stronie górnego wiersza nagłówka w Dzienniku pracy
i zapisuje wpisy przez osobny formularz modala.
Prawy panel zachowuje widoczność, etap zadania, priorytet, wykonawcę, typ
zgłoszenia, kategorię, grupę i tagi, a także pola dodatkowe, daty i metadane.
Dostępność kontrolek i przejść nadal wynika z odpowiedzi serwera; konto tylko
do odczytu widzi wartości bez możliwości zapisu.
ARIA tablist/tab/tabpanel, strzałki, Home i End obsługują klawiaturę.
Wybrany widok jest zapisywany w parametrze `tab=subtasks`, `tab=work-log` lub `tab=history`, bez przeładowania.
„Podzadania” są dostępne dla zadania głównego, także przy pustej liście.
Panel pokazuje dotychczasowy licznik, sortowanie, usuwanie zaznaczonych
i modal dodawania oraz listę grupowaną według statusu. Lista i grupy statusów są
stale rozwinięte, bez przycisków zwijania; „Podzadania” z licznikiem to zwykły
nagłówek. Nie pokazuje tematu, opisu
ani czatu. Pusta lista wyświetla „Brak podzadań.”, a dodawanie pozostaje dostępne.
Zapis podzadania i błąd formularza pozostawiają wybraną zakładkę.
W bieżących Przestrzeniach podzadanie korzysta z okna edycji nad listą rodzica;
nie ma osobnego ekranu szczegółów ani własnego paska zakładek.

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
nagłówki z ikonami, separatory oraz czerwone podświetlenie z paskiem po lewej.
Cały dziennik korzysta z `tasks-issue-content`: tabela, podsumowanie, pusty stan
i pasek „Pokaż więcej” mają tę samą pełną szerokość i boczne odstępy 50px
co temat i opis, również na telefonie. Podsumowanie i pasek nie dodają
własnego poziomego wcięcia. Tabela zachowuje poziome przewijanie kolumn.
Pierwsza kolumna 40px zawiera wspólne checkboxy katalogu projektów, zawsze
widoczne. Checkbox w nagłówku zaznacza/odznacza wczytane wiersze i pokazuje
stan częściowego zaznaczenia. Kliknięcie pustego miejsca w kolumnie wyboru
również przełącza wpis. Zaznaczenie utrzymuje podświetlenie wiersza oraz
pozostaje po edycji i odświeżeniu fragmentu; usunięte i niewidoczne wpisy
wypadają z wyboru. Doładowanie zachowuje wybór; pełne przeładowanie zaczyna nowy wybór.
Delegacja w `task-work-log.js` obsługuje także nowe wiersze po zapisie i
ponowną inicjalizację, bez wpływu na checkboxy pozostałych modułów.
Tabela dziennika pracy nie ma menu wiersza ani jego kolumny 40px.
W nagłówku pozostaje „Dodaj czas”. Zaznaczenie jest lokalne; nie dodano
zastępczych wejść do edycji i usuwania pojedynczego wpisu.
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

Panel jest wyśrodkowany poziomo i pionowo względem całego ekranu, niezależnie od
szerokości i stanu menu bocznego. Zachowuje dotychczasową szerokość na desktopie:
`calc(100vw - clamp(64px, 13.5vw, 280px) - 16px)`, ograniczoną dostępnym
obszarem. Wysokość dopasowuje się do treści, z minimum 24px odstępu od góry
i dołu; dłuższy formularz przewija się wewnątrz okna. Odstępy po lewej
i prawej oraz od góry i dołu są równe. Panel jest pływającą kartą z pełnym
obramowaniem, czterema zaokrąglonymi rogami i wspólnym cieniem okna.
Całe okno ma jednolite białe tło: `--app-panel-surface` wskazuje
`--app-modal-surface` (`--card-bg`, `#ffffff`). Nagłówek, zakładki, obrzeża,
przewijana treść i stopka mają ten sam kolor; treść zachowuje odstępy 24px.
Nagłówek ma 72px i tytuł 20px/400, stopka minimum 68px i akcje po prawej.
Stopka łączy się z treścią bez poziomej linii ani osobnego obramowania.
Dotyczy to dużych i małych okien, potwierdzeń, profilu i edytorów zdjęć;
przyciski są wyrównane do prawej, z zachowaną kolejnością i działaniem.
Oba paski pozostają poza przewijaną treścią. Przycisk zamknięcia, czerwone
akcje, kontrolki, obsługa fokusu, Escape, list wyboru i zapisu korzystają
z dotychczasowych mechanizmów. Panel pojawia się i znika z krótkim pionowym
przesunięciem równym `--app-panel-viewport-gap` w 320ms, z łagodnym wyhamowaniem
i zmianą przyciemnienia tła. CSS używa
`@starting-style` oraz dyskretnego przejścia `display`, więc usunięcie
`is-open`/`active` pozostawia okno widoczne do końca animacji. Szybkie ponowne
otwarcie odwraca ruch bez opóźnionych callbacków. W Dysku i Dokumentach
usunięcie formularza z DOM czeka na zakończenie animacji samej powłoki;
w tym czasie ponowne zamknięcie, zapis i otwarcie są blokowane, a nawigacja
przerywa oczekiwanie na sprzątanie starego ekranu. Potwierdzenia i podglądy
plików zachowują własne zachowanie. `prefers-reduced-motion` wyłącza ruch
i oczekiwanie; starsze przeglądarki bez dyskretnych przejść mają animację
otwierania oraz natychmiastowe zamknięcie.

Formularze tworzenia i edycji korzystają ze wspólnego układu `app-form-layout`
w `modal-system.css`. Pierwszy wiersz `app-form-heading` zawiera nazwę/tytuł
oraz widoczność po prawej, jeżeli formularz udostępnia to pole. Bez widoczności
nazwa wypełnia wiersz. Opis zajmuje pełną szerokość bezpośrednio pod nazwą;
dotyczy to także celu sprintu, notatek Zasobu i Bio profilu. Pozostałe pola
tworzą dwie równe kolumny z odstępem `--app-modal-field-gap`. Etykiety są
po lewej stronie kontrolek, także na telefonie; ich kolumna zajmuje do 32%
szerokości pola, maksymalnie 180px, a długie nazwy mogą się zawijać.
Etykieta opisu jest wyrównana do pierwszego wiersza kontrolki. Błędy zajmują
kolumnę kontrolki pod właściwym polem. Dotyczy to wspólnego renderowania
React i Django; etykiety zawierające checkbox zachowują swój układ inline.
Pomoc przy polu nie zajmuje osobnego wiersza: znak „!” obok etykiety otwiera
dymek po najechaniu
lub fokusie, a kliknięcie/dotknięcie utrzymuje go do zamknięcia. Escape zamyka
najpierw dymek; kliknięcie poza nim i zamknięcie formularza również go usuwają.
Dymek zachowuje powiązanie `aria-describedby` z kontrolką i korzysta ze wspólnej
warstwy dropdownów, więc nie jest obcinany przez przewijaną treść okna.
Preferuje miejsce nad etykietą, aby pozostawić samą kontrolkę dostępną;
gdy go brakuje, warstwa dopasowuje położenie do widocznego ekranu.
`shared/FieldLabel.tsx` oraz `core/includes/field_help.html` współdzielą klasy
i delegowaną obsługę `static/js/field-help.js`, także po podmianie treści.
Pola „Opis”, komunikaty błędów i istotne instrukcje uploadu pozostają widoczne.
Kolejność DOM
i przechodzenia Tab odpowiada układowi wizualnemu. Awatar/ikona zajmuje osobną
kolumnę 68px po lewej (`app-form-avatar-layout`), bez zwężania opisu względem
pozostałych pól; osobna strona ustawień przestrzeni używa wariantu 100px.
Profil zachowuje grupę imienia, drugiego imienia i nazwiska.

Układ obejmuje zadania i podzadania, sprinty, tagi, Przestrzenie, Pulpity,
Filtry, Zespoły, Zasoby, Kalendarz, formularze Dysku/Dokumentów, Workspace
i profil. `app-form-wide` oznacza treści wymagające pełnego wiersza, np.
upload lub wybór modułów. W React wspólny `FormLayout` porządkuje pola schematu;
rozpoznaje ich bazową nazwę (`field_name`), również w formularzach z prefiksem
`subtask-` lub `worklog-`. Podzadanie zachowuje tytuł i widoczność w pierwszym
wierszu, pełny opis poniżej oraz status i termin w kolejnej parze pól.
Osobne edytory stosują te same klasy. Pierwszy render Django używa wspólnych
include'ów `core/includes/modal_form_fields.html` i `modal_form_field.html`
oraz tych samych klas w formularzach specjalistycznych. Pola ukryte i warunkowe
zachowują dotychczasowe mechanizmy. Wariant dotyczy formularzy, nie tabel
udostępniania, podglądów plików ani edytorów w szczegółach zadania.

Do 720px pola i nazwa z widocznością przechodzą do jednej kolumny; do 600px
awatar znajduje się nad polami. Do 900px panel ma minimum 16px odstępu od góry
i dołu oraz po 20px z boków. Do 600px pozostaje pływającą kartą z minimum 12px
odstępu od każdej krawędzi, z odstępami treści 12px, większą
stopką przy zawijaniu akcji i uwzględnieniem bezpiecznego obszaru ekranu.

Okna „Informacje” oraz „Notatki” projektów, grup i tagów w Zadaniach oraz
przestrzeni i tagów w Kanbanie również używają `app-modal-panel`.
Wspólny `project_info_modal.html` zachowuje podsumowanie i siatkę danych.
Notatki zachowują formularz i listę wpisów; cała biała treść przewija się razem,
bez osobnego przewijania listy. Okna mają stałą stopkę „Zamknij” oraz
dotychczasowe zamykanie krzyżykiem i Escape, fokus i obsługę zapisu.

Małe okna formularzy używają `app-modal-panel app-modal-panel--compact`,
jak „Utwórz pulpit”, „Dodaj osobę”, „Zmień rolę” oraz wybór awatara.
Są wyśrodkowane poziomo i pionowo względem całego ekranu, z wysokością
dopasowaną do treści oraz szerokością do 760px. Dziedziczą odstęp od każdej
krawędzi jak duże panele: minimum 24px, do 900px — 16px, do 600px — 12px.
Wysokość jest ograniczona również dostępnym obszarem wewnątrz tych odstępów.
Pojawiają się i znikają z krótkim przesunięciem `--app-panel-enter-offset`
równym `var(--app-panel-viewport-gap)` w 320ms, jak duże panele.
Mały panel ma cztery zaokrąglone rogi, pełne obramowanie i wspólny cień;
powierzchnie, nagłówek i stopkę dziedziczy
po panelu „Edytuj miejsce pracy”.
`AncoreTaskModals` kończy zamykanie małego formularza po zakończeniu ruchu,
zanim moduł usunie jego HTML. Ponowne otwarcie anuluje poprzednie sprzątanie
i zachowuje pierwotny punkt powrotu fokusu.
Ma jednolite białe tło nagłówka, przewijanej treści i stopki oraz akcje po prawej. Etykiety pozostają
nad kontrolkami; w formularzu dodawania osoby konto i rola są obok siebie. Długi tytuł zawija się.
Na telefonie zachowuje margines od krawędzi, a stopka może zawijać akcje.
Potwierdzenia `showConfirmModal` i edytory zdjęć konta, firmy oraz logo Workspace
korzystają z tego samego wyśrodkowanego, pływającego panelu oraz reguł
powierzchni, nagłówka, białej treści i stopki w `modal-system.css`, zachowując
własne szerokości i mechanizmy otwierania. Potwierdzenie jest usuwane z DOM
po zakończeniu ruchu, a powrót fokusu następuje po zamknięciu. Kadrowanie
używa istniejącego atrybutu `hidden` i dyskretnego przejścia `display`.
`prefers-reduced-motion` wyłącza ruch również w małych oknach.
Nagłówki mają minimum 72px i tekst 20px/400; stopki minimum 68px oraz akcje
po prawej. Do 600px jest to odpowiednio 60px, 18px i 60px, z odstępami 12px.
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
Adapter zachowuje opcjonalny wariant pozycjonowania panelu:
można ustawić
`data-dropdown-positioning="fixed"` (`Dropdown positioning="fixed"` w React).
Warstwa dobiera położenie przy otwarciu, potem zachowuje te współrzędne
i ogranicza panel do widocznego ekranu. Przesunięcie kontrolki poza przewijany
obszar nie zamyka takiego panelu; ukrycie lub usunięcie kontrolki nadal go zamyka.
Ponowne otwarcie ustala pozycję od nowa. Domyślne menu nadal śledzą kontrolkę.
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
Pola klasyfikacji zadania `task_type` i `task_group` wyświetla wyłącznie
tekstowo, pomijając również wcześniejsze metadane wyglądu.
Wspólna warstwa uzupełnia ikony prostych filtrów i sortowania.
`core.widgets.VisualSelect/VisualSelectMultiple` przekazują serwerowe ikony
lub podglądy przez lokalne szablony, bez zmiany wartości opcji i walidacji.
Filtry zadań pokazują awatary/zdjęcia widocznych przestrzeni, wykonawców
i zespołów, kolorowe typy zgłoszeń, statusy i priorytety. Podglądy korzystają
z tych samych include'ów co szczegóły i zachowują kontrolowane adresy obrazów.
„Brak priorytetu” (`none`) ma neutralną ikonę pustego okręgu `circle` z tej
samej rodziny UIcons co statusy. Wspólny select używa jej w menu oraz przy
wybranej wartości, zgodnie z listami zadań i podglądami z szablonów.
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
samych tokenach. Dynamiczne nazwy i inne dane użytkownika przekazuj przez
`messageText`, które escapuje tekst przed wstawieniem do HTML. `message`
pozostaje wariantem dla zaufanego, stałego HTML; nie interpoluj w nim nazw
Workspace, przestrzeni, filtrów ani pulpitów. Potwierdzenia usunięcia notatki projektu/grupy/tagu i kontaktu
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
Rozmiary, wagi i odstępy istniejących komponentów pozostają bez zmian.
Ekrany uwierzytelniania również korzystają wyłącznie z lokalnego kroju UI.
Osobne edytory w iframe (Excalidraw/ONLYOFFICE) zarządzają własną typografią.

Biblioteka ikon to **Flaticon UIcons Regular Rounded 3.3.1**, z pełną gwiazdką
`star-filled` z wariantu Solid Rounded tej samej wersji, ładowana lokalnie
w bazowych szablonach aplikacji i uwierzytelniania. Lokalny adapter
[flaticon-icons.js](../static/js/flaticon-icons.js) normalizuje nazwy i udostępnia
`AncoreIcons.render(scope)`, `create`, `html`, `safeName` i `normalize`.
Nazwy używane przez moduły pozostają stabilne; ich odpowiedniki Flaticon określa
[mapowanie](../scripts/assets/flaticon-icon-map.json). Nie wymagają migracji danych.
`data-icon` jest wspólnym atrybutem placeholdera i wygenerowanego SVG;
`data-flaticon` wskazuje nazwę źródłową UIcons. Ponowne renderowanie jest idempotentne,
obejmuje również przekazany element główny i działa na `ancore:content-loaded`.
Nieznane nazwy używają podanego fallbacku lub `circle`.

Przełączniki paneli (`panel-left` i `panel-right`) pokazują prosty obrys okna
z pionowym podziałem po odpowiedniej stronie, bez trzech kropek. Są to
uproszczone glify `sidebar` i `sidebar-flip`, odtwarzane przez generator
zestawu; React i pierwszy render Django korzystają z tych samych ikon.

Kontury SVG dziedziczą `currentColor`, zachowując istniejącą geometrię kontrolek.
Flaticon używa wypełnionych konturów, dlatego `.ancore-icon` wyłącza obrys `stroke`;
nie stosuj do nich `stroke-width`. Checkboxy, strzałki selectów i wskaźniki statusu
korzystają z lokalnych SVG przez tokeny `--icon-*`.
Zestaw, licencja i instrukcja odtworzenia znajdują się w
[static/vendor/flaticon](../static/vendor/flaticon/README.md).
Oznaczenie źródła ikon jest widoczne w Ustawieniach.

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

Katalog `/workplaces/` jest stroną kategorii „Workspace” we wspólnym menu
„Ustawienia Ancore” (tryb `settings`, `settings_category=workspace`).
Menu zawiera „Ogólne”, „Konto i dostęp”, aktywną pozycję „Workspace”, „Przestrzenie” oraz
powrót do przestrzeni. Treść katalogu zajmuje środkowy panel aplikacji.
Wybranie Workspace otwiera pełną stronę ustawień z trybem
`workspace-settings`: główne menu zastępują sekcje „Ustawienia”, „Członkowie”
i dostępne zarządzającym „Linki do dołączenia”. Pierwszy render używa
`core/includes/workspace_settings_sidebar.html`, a React `shell/Sidebar`.
`render_workplaces` utrzymuje wybraną sekcję także po walidacji formularza.
Strzałka nagłówka i „Anuluj” wracają do katalogu `/workplaces/`;
historia przeglądarki zachowuje adresy odwiedzanych sekcji.
Oglądanie lub edycja wybranego Workspace nie przełącza aktywnego kontekstu pracy.

Etykieta „Domyślny” z opisem „Domyślny Workspace” wskazuje zapisaną
osobistą preferencję Workspace; „Bieżący” nadal oznacza aktualny kontekst.
Menu ustawienia i usunięcia tej preferencji zostało usunięte z wiersza
katalogu bez zastępczego wejścia. Zapisane preferencje pozostają w bazie.

Profil użytkownika korzysta ze wspólnego okna `core/includes/avatar_picker.html`
i `workplace-avatars.js`, z osobną pulą 30 zwierzęcych maskotek w
`backend/accounts/avatar_presets.py`. Lokalne atlasy `static/img/user-avatars/illustrations-v1.png`
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
`backend/core/avatars.py` i `core/includes/avatar_presets.html` definiują motywy
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


Ekran `/workplaces/` rozszerza `core/base.html` i pokazuje katalog Workspace.
Nazwa może się powtarzać. Kolumna „Kod miejsca pracy” pokazuje stały losowy
identyfikator `w_` + 26 małych liter/cyfr; ma minimum 250px i pełną wartość
w `title`. Tworzenie pokazuje „Generowany automatycznie”, a edycja zapisany
kod tylko do odczytu. Zmiana nazwy nie zmienia kodu ani adresu.
Tytuł „Workspace” ma rozmiar 17px i grubość 700. Dwa wspólne paski
`tasks-topbar--directory` oraz `tasks-filterbar--directory` zachowują tytuł,
akcje i wyszukiwanie. Tabela zaczyna się pod paskami, a pod wynikami
znajduje się „Pokaż więcej”, odsłaniające po 20 kolejnych Workspace.
Po prawej stronie paska wyszukiwania są „Edytuj” i „Usuń”, zgodnie z katalogiem
Przestrzeni w Ustawieniach. Działania dotyczą dokładnie jednego zaznaczonego,
widocznego wiersza. „Edytuj” wymaga właściciela albo administratora wybranego
Workspace i otwiera `?workspace=<id>&tab=main`. „Usuń” jest dostępne wyłącznie
właścicielowi, jeżeli pozostanie co najmniej jeden jego własny Workspace.
Kompaktowy `FormDialog` pokazuje nazwę i zakres usunięcia przez
`confirmation_message` oraz wymaga przepisania aktualnej nazwy.
Prawa dotyczą wybranego wiersza: rola gościa w aktywnym Workspace nie odbiera
możliwości zarządzania innym Workspace, którego użytkownik jest właścicielem.
Nie ma zbiorczej edycji ani usuwania; „Dodaj Workspace” pozostaje w nagłówku.

Nazwa Workspace otwiera główną sekcję strony ustawień, liczba członków —
„Członkowie”. Tabela nie zawiera hamburgera ani kolumny jego menu.
Znacznik „Bieżący” oraz przycisk przełączenia zachowują oddzielne działanie.
Kliknięcie reszty wiersza, Enter i Spacja otwierają ustawienia; zaznaczenie tekstu,
checkboxy i pozostałe linki zachowują własne akcje. Hover i fokus ikon
wypełniają komórkę istniejącym akcentem bez zmiany siatki tabeli.

Strona ustawień Workspace korzysta z układu ustawień Przestrzeni.
`PageHeader` zawiera strzałkę powrotu do katalogu i tytuł
„Ustawienia Workspace · <nazwa>”, bez ikony przy tytule. Menu po lewej
pokazuje „Ustawienia” (`main`), „Członkowie” (`members`) i — tylko dla
zarządzających — „Linki do dołączenia” (`links`). Aktywna sekcja ma
`aria-current="page"` i ten sam styl co menu ustawień Przestrzeni.
Menu zaczyna wizytę rozwinięte; na telefonie korzysta ze wspólnej szuflady.
„Zapisz” i „Anuluj” są po prawej we wspólnym `Toolbar` nad formularzem,
a „Dodaj osobę” nad tabelą członków. Awatar, nazwa, opis, niezmienny kod
i włączone moduły zachowują dotychczasowe kontrolki. Formularz chroni
niezapisane zmiany przy nawigacji. Członek i gość odczytują ustawienia
oraz członków bez przycisków zarządzania. Błąd zachowuje formularz;
tworzenie Workspace i dodawanie osoby nadal korzystają ze wspólnych modali.

Powłoka strony współdzieli `.space-settings-page`, przewijanie paneli
i kontener responsywny `space-settings` z ustawieniami Przestrzeni.
Minimalny wariant `.workspace-settings-main` w `components/workplace-team.css`
układa awatar wewnątrz wspólnych pól (`.app-form-avatar-layout`): kolumna
awatara ma 100px, a resztę zajmują pola. Do szerokości kontenera 960px karty
modułów przechodzą do jednej kolumny, a do 640px formularz układa awatar
nad polami. Opis modułu zajmuje wtedy pełny wiersz karty pod nazwą i
przełącznikiem. Wariant nie zmienia formularza tworzenia ani innych ekranów.

Tabela członków używa `tasks-directory-board tasks-directory-sheet
tasks-project-sheet workplace-team-sheet` oraz pięciu kolumn: zaznaczenie
40px, nazwa z awatarem, e-mail, rola i data dołączenia.
Zachowuje wiersze 35px, tekst 13px/400, cienką siatkę, jasnoczerwone
podświetlenie oraz awatary 30×30px. Checkbox nagłówka obejmuje własną tabelę
i pokazuje stan częściowy; zaznaczenie nie wykonuje operacji. Nazwa i e-mail
mają ellipsis i pełną treść w `title`. Na telefonie tabela przewija się poziomo
we własnym kontenerze. Pusty stan korzysta ze wspólnego komponentu.
Menu zmiany roli i odebrania dostępu zostało usunięte bez zastępczego
wejścia w tabeli. Backend zachowuje dotychczasowe kontrole ról i ochronę
właściciela.

Formularze dodawania osoby i zmiany roli używają `tasks-modal app-modal-panel
app-modal-panel--compact`, pól `tasks-form-field` i wspólnej stopki.
Pole istniejącego konta jest obok roli w `workplace-invite__fields`;
kolumna roli ma 180px, a do 600px pola przechodzą do jednej kolumny.
Picker wyszukuje od 2 znaków imienia, drugiego imienia, nazwiska, ID Ancore
lub e-maila i pokazuje do 10 aktywnych kont z nazwą, adresem oraz awatarem.
Wybór zapisuje `user_id`; zmiana tekstu czyści wybrane konto. Komunikat
„Dodajesz” potwierdza wybór, a „Dodaj do Workspace” natychmiast nadaje dostęp.
Sam wpisany e-mail nie jest zaproszeniem ani tożsamością zapisu.
Właściciel wybiera `admin`, `member` lub `guest`, administrator tylko
`member` lub `guest`; podpowiedzi i zapis blokują mu także nieaktywnych
administratorów. Lista zachowuje combobox/listbox/option, strzałki, Enter,
Escape, anulowanie starszych pobrań i stan błędu. Bez JavaScriptu zakładka
„Członkowie” zawiera natywny formularz z dokładnym ID Ancore (`@username`)
i rolą. Zapis wymaga POST i CSRF; błąd zachowuje dane i punkt powrotu fokusu.

„Linki do dołączenia” pokazuje adres do skopiowania, rolę, wykorzystanie
limitu, ważność i „Unieważnij link”. Formularz „Utwórz link do dołączenia”
wybiera `member` lub `guest`, 1–30 dni i 1–1000 użyć. Nie ma pola domeny e-mail.
Posiadacz linku loguje się lub rejestruje i potwierdza dołączenie przez POST.
Wygasły, unieważniony lub wykorzystany do limitu link pokazuje niedostępność;
nie ma dopasowywania do adresu odbiorcy. `workplace-invite-links` oraz
`workplace-invite-link` zachowują zawijanie adresu i akcji na telefonie.

Nie ma zakładek otrzymanych/wysłanych zaproszeń, formularza wysyłki e-mail,
okna przyjęcia/odrzucenia e-maila ani licznika takich zaproszeń pod dzwonkiem.
Dawne parametry `view=received`, `view=invitations` i `invitation` nie otwierają
wycofanych ekranów. Odebranie dostępu nadal wymaga `showConfirmModal`
wyjaśniającego wpływ na sesje Office. React oraz szablony zgodności zachowują
wspólny fokus, `inert`, Escape i inicjalizację po `ancore:content-loaded`.
Kategoria „Workspace” w Ustawieniach prowadzi bezpośrednio do katalogu,
bez pośredniego ekranu „Zarządzaj Workspace”. Skrót pozostaje w widoku Ogólne.
[Funkcje, role i migracje](TEAMWORK.md).

## 13. Centrum powiadomień

Powiadomienia są dostępne wyłącznie w panelu dzwonka. Panel renderuje
`src/shell/NotificationPanel.tsx` z jawnymi danymi JSON i dotychczasowym
`notifications-panel.css`. Include'y `notification_controls.html`,
`notification_list.html`, `notification_pagination.html` oraz
`notifications-panel.js` pozostają wzorcem i trybem zgodności. Panel używa tej samej powłoki
`tasks-modal app-modal-panel` co „Utwórz zadanie”: szerokiego okna z jednolitym
białym tłem, wspólnymi odstępami i animacją. Nagłówek zawiera tytuł
„Powiadomienia” i standardowy krzyżyk. Stała stopka zawiera „Zamknij”,
a pasek „Pokaż więcej” jest pod wpisami wewnątrz przewijanej listy.
Wariant `notifications-panel__body`
układa filtry i niezależnie przewijaną listę pionowo we wspólnej białej powierzchni.
Avatary kont, przyciski, ikony i tokeny kolorów pozostają wspólne.
Białe karty mają delikatne ramki; nieprzeczytane dodatkowo kropkę i 5% akcentu
w tle. Dzwonek sygnalizuje nieprzeczytane wpisy kropką
`notifications-toggle__indicator` i opisem dostępnym dla czytnika ekranu.

Zakładki „Wszystkie”, „Nieprzeczytane”, „Przypomnienia”, „Wzmianki”,
„Obserwowane” i „Archiwum” używają przycisków z `aria-pressed`; filtr Workspace
korzysta ze wspólnego selecta. Źródłami są komentarze Przestrzeni (`spaces`)
i osobiste przypomnienia (`space-reminders`). Nie ma źródła ani filtra
zaproszeń; summary nie zawiera `pending_invitation_count`, a karty nie mają
pola `is_invitation`. Odświeżanie po operacji, powrocie do karty i pollingu
aktualizuje stan nieprzeczytanych oraz sygnalizuje nowe wpisy.
Filtr Workspace zachowuje zwykłą cienką ramkę po najechaniu, uzyskaniu fokusu
i otwarciu listy, bez dodatkowego obrysu ani poświaty, tak jak pola w modalach.
Karty pokazują podgląd komentarza lub przypomnienia, Workspace, moduł, klucz
zadania i czas z pełną datą w tooltipie. Komentarze grupują się według daty,
a przypomnienia zachowują własną etykietę grupy.
Wpisy historii zmian nie pojawiają się w żadnym filtrze ani liczniku panelu.
Puste stany „Wszystkie” i „Obserwowane” opisują komentarze i pozostałe dostępne
typy powiadomień, bez zapowiadania historii zmian.
Karty nie mają menu z trzema paskami ani jego akcji pojedynczego odczytu,
archiwizacji/przywracania i usuwania. Zachowane linki otwierają powiązaną
treść, a istniejące akcje zbiorcze pozostają w pasku panelu.
„Oznacz wszystkie jako przeczytane” obejmuje bieżący filtr, również starsze strony;
przycisk jest nieaktywny, gdy wszystkie wpisy w tym widoku są przeczytane.
Kosz w pasku usuwa powiadomienia z bieżącego filtra, także ze starszych
stron. Jest nieaktywny, gdy filtr nie ma
usuwalnych wpisów. Usunięcie zbiorcze otwiera `showConfirmModal`
z informacją o osobistym zakresie,
zachowaniu komentarzy i zapisów przypomnień w danych źródłowych.
Potwierdzenie zbiorcze pokazuje liczbę wpisów i zachowuje snapshot z chwili otwarcia.
Tab i Escape dotyczą wtedy potwierdzenia, bez zamykania panelu pod spodem.
Zapis blokuje ponowne wysłanie; błąd zachowuje wpis i umożliwia ponowienie.
Po potwierdzonym odczycie/usunięciu wyświetla się wspólny komunikat sukcesu.
„Pokaż więcej” doczytuje kolejną porcję 20 wpisów, zachowując kursor.
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

Panele globalne mają trwały korzeń `[data-react-global-panels]` i osobny host
modali, poza podmienianą treścią strony. Wyszukiwarka używa tego samego pola,
grup, filtrów oraz skrótów Ctrl/⌘+K i `/`, strzałek, Home/End i Escape.
Po nawigacji czyści frazę i anuluje pobranie. Sticker zachowuje dotychczasowy
wygląd, klucz zapisu konta, geometrię i zmianę rozmiaru klawiaturą. Jego treść
trwa podczas częściowej nawigacji. Stare skrypty tych trzech paneli nie są
ładowane razem z Reactem; helpery ikon, selectów, modali i toastów pozostają wspólne.

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

Od 16.10.2026 interaktywny katalog i formularz renderuje React/TypeScript
z `frontend/app/src/resources/`. Powłoka, CSS, polskie etykiety i geometria
pozostają wspólne. Komponenty React zarządzają filtrami, kolumnami, zaznaczeniem
i tabelą bez równoczesnego modyfikowania ich DOM przez `tasks.js`.
Adaptery ikon i custom selectów mają osobne kontenery; modal nadal używa
`AncoreTaskModals`. Szczegóły: [Frontend React](FRONTEND.md).

Zasoby rozszerzają `core/base.html`, `tasks-topbar`, `tasks-filterbar`, wspólne
menu filtrów/sortowania oraz wspólny pasek „Pokaż więcej”. Lista używa
wspólnej tabeli Projektów (`tasks-directory-sheet tasks-project-sheet`) z wariantem
`resources-sheet`: wiersze 35px, separatory, nagłówki z ikonami, checkboxy
z podświetleniem zaznaczenia. Dalej są numer ewidencyjny,
nazwa z ikoną typu, typ, status, osoba, lokalizacja, ważność/gwarancja i planowany zwrot.
Miniony termin korzysta ze wspólnego oznaczenia `tasks-project-value-badge--due-overdue`.
Nazwa otwiera kartę zasobu, która zachowuje istniejący przycisk edycji.
Menu wiersza i jego kolumna są usunięte; nie dodano zastępczego wejścia do usuwania.

Pasek zachowuje wygląd zarządzania kolumnami, agregatu „Filtruj”
i sortowania z widoczną bieżącą opcją. Komponent `columns.tsx` obsługuje szerokości,
kolejność i widoczność kolumn; Zasoby mają oddzielny klucz ustawień `resources`,
wspólny dla zwykłego i scoped URL. Checkbox nagłówka zaznacza wczytane wiersze,
a częściowy wybór pokazuje stan pośredni. Po zaznaczeniu wspólny pasek
pokazuje w `actions` przekazanie, zwrot, zmianę statusu i lokalizacji;
akcje niedostępne dla wybranego
zestawu są wyłączone. Zaznaczenie ponad 100 pozycji pokazuje komunikat
i blokuje operacje zbiorcze zgodnie z limitem API.
Gość nie zaznacza ani nie edytuje zasobów.
Kolumny przewijają się poziomo także na telefonie, a pasek narzędzi zawija.
Pusty katalog i brak wyników mają osobne komunikaty, a działania pozostają w pasku.

Zwarty `resources-summary` nad filtrami pokazuje liczniki całego Workspace.
Przyciski używają `tasks-filter-button`, ikon i istniejących tokenów; kliknięcie
resetuje filtry do wskazanego zakresu. Aktywne filtry i ich usuwanie są
w `app-toolbar__summary` przy kontrolkach tego samego paska.
„Eksport CSV” pozostaje w nagłówku, a odświeżanie w działaniach paska po prawej.
Nazwa otwiera kartę z danymi i historią. Minimalne warianty
`resources-detail-panel`, `resources-properties` i `resources-history`
w `resources.css` zachowują ramki, odstępy i font wspólnej aplikacji;
poniżej 1100px panele układają się pionowo, przewijane we wspólnej treści.
Historia pokazuje autora, czas, wartości przed/po i notatkę; długie wartości mają
własne przewijanie. Terminy wymagające uwagi mają opis tekstowy w karcie.
Przekazanie, zwrot, status, lokalizacja i notatka korzystają ze wspólnego `Modal`
z istniejącym `app-modal-panel--compact`, custom selectów i ochrony szkicu.
Walidacja zachowuje pola i ogłasza błąd. Konflikt blokuje zapis i udostępnia
„Odrzuć szkic i odśwież”. Karta jest dostępna również dla gościa i w pierwszym
renderze Django; operacje wymagają Reacta. Dodanie kolumny zwrotu kopiuje
wcześniejsze preferencje układu i szerokości do rozszerzonego schematu.

`resources.css` ustala wariant siatki oraz dwukolumnowy układ formularza,
który przechodzi w jedną kolumnę na telefonie. Powłoka, pola i przyciski
pozostają wspólne (`tasks-modal app-modal-panel`, `documents-field`, `form-input`).
Zgodne formularze HTML nadal używają `resources.js`, który pomija kontener React.
Skrypt korzysta z `AncoreTaskModals`, ikon, custom selectów,
`showConfirmModal` oraz `AncoreApp.navigate`. Inicjalizuje się na pierwszym
wejściu i `ancore:content-loaded`, anulując poprzednie listenery i żądania.
Modal blokuje tło przez `inert`, zachowuje fokus, Escape i potwierdzenie
porzucenia zmian. Pobranie/zapis/usunięcie pokazują błędy umożliwiające ponowienie.

## 15. Pulpity

System „Pulpity” rozszerza Dashboard przez `dashboard/pulpits/base.html`,
wspólne paski, przyciski, `row-actions.js` i `AncoreCustomSelect`.
Od 16.10.2026 interaktywne ekrany renderuje `frontend/app/src/pulpits/`.
Zachowuje te same klasy, tokeny i układy; poniższe szablony są również
referencją oraz początkowym HTML. React obsługuje zaznaczenie, szerokości,
formularze, katalog i układ. `pulpits.js` pomija korzeń Reacta; wspólne
menu boczne i wyszukiwarka Pulpitów nadal należą do powłoki.
Małe adaptery w `react.css` zachowują rozmiar ikon nagłówka, łamanie opisu
oraz geometrię pól renderowanych przez wyspy kontrolek DOM.
Katalog korzysta z `dashboard/pulpits/directory.html`
oraz tabeli Przestrzeni w powłoce `work-page`:
`tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable
tasks-directory-menu-sheet tasks-spreadsheet-sheet work-space-sheet`.
Minimalny wariant `pulpit-directory-sheet` w `components/pulpits.css` określa
kolumny zaznaczenia, nazwy, twórcy, widoczności, liczby gadżetów i opisu
oraz ikonę pulpitu 24px. Tabela ma po bokach 15px odstępu i zachowuje
wspólne wysokości wierszy, separatory, podświetlenia oraz przewijanie.
Nagłówek oraz toolbar mają 15px odstępu. Katalog nie ma zakładek
Wszystkie, Ulubione i Moje; pokazuje wszystkie dostępne pulpity.
Przycisk „Filtruj” po lewej otwiera pole widoczności i zatwierdzenie
formularza; wyszukiwarka znajduje się obok niego po lewej. Pod tabelą pasek „Pokaż więcej"
odsłania kolejne porcje po 20 wyników. Checkboxy zaznaczają wczytane
wiersze, bez operacji zbiorczych; doładowanie zachowuje wybór.
React (a w szablonach zgodności `tasks.js`) obsługuje zaznaczenie, stan częściowego wyboru i szerokości kolumn
z osobnym kluczem `pulpits-directory`, wspólnym dla zwykłego i scoped URL.
Katalog nie zawiera menu wiersza ani jego kolumny. Nazwa otwiera pulpit.
Opis jest osobną kolumną,
a pełne teksty są dostępne w `title`. Puste wyniki ukrywają nagłówki i pokazują
komunikat odpowiedni do filtrów lub pustego katalogu. Przegląd pulpitu nadal używa
`dashboard-overview` i gadżetów. Pozostałe warianty `pulpit-*` zachowują tokeny.
Puste stany katalogu używają `pulpit-directory-empty-state`:
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
stronie nagłówka. Przegląd pokazuje nazwę pulpitu, odświeżenie i menu działań
zgodne z rolą; „Edytuj pulpit” jest w nagłówku, bezpośrednio przed „Odśwież”,
z tym samym stylem przycisku.
Opis pulpitu pozostaje w ustawieniach i katalogu; przegląd oraz edytor nie
wyświetlają go pod nagłówkiem.
Menu z wielokropkiem nie zawiera „Kopiuj pulpit”. Nawigacja i gwiazdki
pozostają w menu bocznym. Podgląd nie pokazuje uchwytów ani opcji układu.

Aktywny edytor React współdzieli `DashboardCanvas` i klasy `work-summary-*`
z Podsumowaniem Przestrzeni. Siatka ma 12 kolumn, wiersz 48px i odstępy 12px.
W edycji pokazuje kropkowane tło, nagłówek z uchwytem oraz uchwyt rozmiaru
w prawym dolnym rogu. Uchwyty obsługują także strzałki klawiatury.
Górny pasek zawiera „Dodaj gadżet”, „Anuluj” i „Zapisz układ”. Siatka zaczyna
się bezpośrednio pod nim. Nie ma wyboru gotowych układów ani automatycznego
zapisu geometrii. Na wąskim ekranie kafelki układają się pionowo, a zachowany
uchwyt pozwala zmieniać kolejność strzałkami góra/dół.

Menu kafelka, panel suwaków/pozycji, „Konfiguruj” i „Usuń gadżet” zostały
usunięte bez zastępczych wejść. Dodawanie, pozycja i rozmiar tworzą jeden szkic.
„Zapisz układ” zapisuje go razem, a „Anuluj” przywraca poprzedni stan. Błąd
zachowuje szkic; pobranie aktualnej wersji wymaga potwierdzenia odrzucenia
zmian. Nawigacja chroni niezapisany szkic. Nowa karta przed zapisem informuje,
że dane pojawią się po zapisaniu układu. Backend zachowuje formularze
konfiguracji i zapisy układu, w tym pustego.

Nagłówki gadżetów zachowują dekoracyjne ikony z `AncoreIcons`, np.
`chart-no-axes-combined` dla „Postępu pracy”. `GadgetKindSelect` przekazuje
ikony do wspólnego dropdownu przez `data-ancore-option-icon`.
Tworzenie pulpitu nie wymaga wybrania dawnego układu kolumn.
Formularz rodzaju gadżetu zawiera `pulpit-gadget-preview`: miniaturę z ikoną
oraz krótki opis, aktualizowane po wyborze rodzaju. Niedostępne źródło ma ikonę
kłódki i komunikat bez nazwy przestrzeni oraz liczników. Opisy oraz standardowa
walidacja formularza pozostają tekstowe.

Pusty pulpit używa wariantu `pulpit-empty-state` wspólnego `tasks-empty-state`:
kolorowa ilustracja `static/img/empty-states/dashboard-empty.webp` i opis
są wyśrodkowane w wolnej przestrzeni pod nagłówkiem. Przegląd kieruje do edycji.
Edytor pokazuje wspólny pusty stan dla zapisanego układu bez gadżetów.
Katalog otwiera przycisk „Dodaj gadżet” na pasku nad siatką.
Ilustracja przeglądu pulpitu ma przezroczyste tło i wspólne pole 440×330px,
tak jak puste katalogi Przestrzeni i Pulpitów. Skaluje się do dostępnej szerokości
i wraz z opisem jest wyśrodkowana w treści. Jest dekoracyjna (`alt=""`,
`draggable="false"`); stan opisuje polski tekst.
Typografia pustego pulpitu nawiązuje do wskazanego wzorca Jiry: nagłówek
28px/700 (24px na telefonie), opis 16px z interlinią 1,6 i odstępem 16px
od nagłówka. Używa wspólnego Atlassian Sans i koloru `--text-primary`.
Lokalna waga nagłówka nadpisuje globalne 400 wyłącznie w tym pustym stanie.
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
Utworzenie przechodzi do zapisanego pulpitu z aktualizacją adresu.
Odświeżenie i zapis zachowują częściową nawigację. Dodawanie gadżetu pozostaje
w edytorze; wejścia do konfiguracji i usuwania z menu kafelka zostały usunięte.
Bezpośrednie formularze zachowują istniejącą kontrolę dostępu.

Menu „Pulpity” wykorzystuje istniejący wariant nagłówka Przestrzeni, listy
`sidebar-space-list` i wiersze z `row-actions.js`. Ikona nagłówka zmienia się
na chevron przy hover/fokus; plus otwiera tworzenie pulpitu. Nagłówek nie ma
menu zarządzania. Sekcje pokazują gwiazdki, ostatnie oraz przycisk
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

Akcja gwiazdki w menu wiersza używa wspólnego `tasks-favorite-toggle` i `aria-pressed`:
oznaczony pulpit ma wypełnioną żółtą ikonę `star-filled` (`#e2b203`), także przy hover/fokusie,
a nieoznaczony zachowuje obrys `star` i zwykły kolor ikony. Ten wariant działa
w menu bocznym i jego zwiniętym panelu, w React oraz pierwszym renderze Django.

`layout.js` synchronizuje zawartość sekcji po częściowej nawigacji, zachowując
stan zwinięcia i fokus. Zwinięte menu otwiera flyout z tymi samymi sekcjami,
unikalnymi ID i działającymi menu wierszy. Globalny `pulpit-navigation.js`
obsługuje osobistą gwiazdkę także poza modułem i po `ancore:content-loaded`,
odłączając listenery. Zapis tworzenia pulpitu i konfiguracji gadżetu aktualizuje menu.
Wspólny flyout ma nagłówek poza przewijanym obszarem,
aby linki i akcje pozostały dostępne również przy wielu pozycjach.

Osobny ekran „Zarządzaj pulpitami”, jego menu boczne oraz wejście w Ustawieniach
Ancore są usunięte. Stare zwykłe/scoped adresy `dashboards/manage/` otwierają
zwykły katalog „Pulpity”, z zachowaniem wyszukiwania, widoczności i numeru strony.
Katalog ma jeden wariant listy i klucz szerokości `pulpits-directory`.
Menu konkretnego pulpitu zawiera „Gadżety i układ” oraz „Ustawienia”.
Nie ma osobnej pozycji „Dostępy”; udostępnieniami zarządza się w zakładce
„Udostępnienia” strony ustawień.

Ustawienia konkretnego pulpitu renderuje `src/pulpits/SettingsPage.tsx`
na osobnej stronie zgodnej z ustawieniami Przestrzeni. Wspólne klasy
`space-settings-page` i `space-settings-panel` zapewniają nagłówek, przewijaną
treść i stopkę formularza. Główne menu zastępują dwie pozycje „Ustawienia”
i „Udostępnienia”, bez dodatkowych nagłówków. Menu otwiera się rozwinięte,
zachowując zapisaną preferencję zwinięcia zwykłego menu Workspace.
Ukryty formularz pozostaje zamontowany i zachowuje szkic przy zmianie sekcji,
także przez Wstecz/Dalej. Wyjście chroni dotychczasowe potwierdzenie niezapisanych zmian.
Menu przeglądu i nawigacji przechodzą na tę stronę. Bezpośrednie
zwykłe/scoped URL oraz wariant zarządzania używają tej samej powłoki.
Zapis nie zamyka strony; aktualizuje nazwę w nagłówku i dane menu.
Powrót oraz „Anuluj”/„Zamknij” respektują kontekst wejścia.
Szablony Django również pokazują pełną stronę i zachowują formularze POST.

„Ustawienia” zawierają nazwę, opis, ikonę, zakres danych, automatyczne
odświeżanie i widoczność („Prywatny — wybrane osoby” albo „Cały Workspace”).
„Udostępnienia” używają tych samych `shared/Members`, `shared/SharingDialog`
i pickera osób Workspace co Przestrzenie: tabela z chronionym wierszem twórcy,
przycisk „Udostępnij”, wyszukiwanie osoby oraz szkic zmian dostępu.
Tabela ma po bokach odstępy `--app-page-padding-x` (15 px), wyrównane do
nagłówka i paska przycisków, oraz wypełnia pozostałą wysokość panelu.
Wspólny `space-settings-table-body` zapewnia własne przewijanie tabeli,
a zwarty pasek `tasks-filterbar--directory` zawiera po lewej „Widoczność:
Publiczna/Prywatna”, a po prawej „Zmień rolę”, „Odbierz dostęp”, „Udostępnij”
oraz „Zapisz” i „Anuluj”, we wspólnej grupie `member-access-save-actions`.
Wariant `member-access-toolbar` zawija kontrolki na wąskim ekranie i nie ma
dolnej linii oddzielającej przyciski od nagłówka tabeli. Tabela
`workplace-members-sheet--toolbar` pomija kolumnę i menu trzech pasków;
checkboxy pozwalają zaznaczyć każdy wiersz, także właściciela i nagłówek
na liście zawierającej wyłącznie właściciela. Sam wybór nie zmienia uprawnień.
Przyciski roli i odebrania dostępu są wyłączone bez zaznaczenia edytowalnej
osoby. Przy mieszanym zaznaczeniu operują wyłącznie na dozwolonych osobach.
Wyłączone przyciski mają krycie 55%, kursor niedostępnej akcji i nie zmieniają
tła ani ramki po najechaniu. Zaznaczenie edytowalnej osoby przywraca zwykły
wygląd oraz działanie; wariant dotyczy akcji w paskach dostępu Pulpitów i Przestrzeni.
Właściciel, dostęp odziedziczony i niedozwolone dla administratora wiersze
pozostają chronione przy wykonywaniu akcji.
Publiczna widoczność oznacza cały Workspace; prywatna — wybrane osoby.
Widoczność, role, dodawanie i odbieranie dostępu tworzą wspólny szkic.
„Zapisz” zatwierdza go w jednej operacji; „Anuluj” przywraca zapisany stan
i usuwa zaznaczenie. Modal roli używa „Zastosuj”, a udostępnienia „Dodaj”;
oba wyjaśniają, że zmiany czekają na główny zapis. Odebranie dostępu usuwa
wiersz ze szkicu; można je cofnąć przed zapisem. Nie ma dolnej stopki „Zamknij”.
Wyjście chroni potwierdzenie niezapisanych zmian, a błędy zachowują szkic.
Pod paskiem nie ma komunikatu o niezapisanych zmianach, opisu dostępu całego
Workspace ani potwierdzenia zapisu, anulowania lub ponownego wczytania dostępu.
Stan szkicu wskazują przyciski zapisu i anulowania; komunikaty błędów pozostają widoczne.
Konflikt z innym zapisem wymaga „Anuluj”, które odrzuca szkic i pobiera aktualny dostęp.
Przy szkicu ustawień kontrolka widoczności wymaga najpierw zapisania
ustawień, a wskazówka wyjaśnia blokadę. Po zapisaniu zmiany widoczności czysty
formularz ustawień pobiera aktualne dane przy kolejnym wejściu.
Układ obejmuje React i pierwszy render Django (przyciski aktywuje React);
formularz zgodności pod tabelą zachowuje własny przewijany obszar.
Szkic dostępu zachowuje się podczas zmiany sekcji. Udostępnienie i „Zmień rolę”
używają ról „Administrator”, „Członek” i „Obserwator”, z domyślnym członkiem.
Właściciel wybiera wszystkie role; administrator tylko członka i obserwatora,
bez możliwości zmiany innych administratorów i właściciela. Ustawienia są dostępne
właścicielowi i administratorowi; pole widoczności jest wyłączone dla administratora.
Gadżety i układ edytuje również członek, a obserwator ma tylko odczyt.
Usunięcie Pulpitu jest dostępne wyłącznie właścicielowi. Daty nowych udostępnień
są zapisywane, a brak historycznej daty jest pokazywany jako „—”.
Przy widoczności Workspace tabela pokazuje dostęp odziedziczony, bez indywidualnych
akcji. Dawne formularze `access/` pozostają zgodne dla starszych klientów.
Strona ustawień korzysta z układu formularza Przestrzeni: nazwa i widoczność
obok siebie, opis na pełną szerokość pól, następnie zakres danych
i odświeżanie w dwóch kolumnach. Etykiety znajdują się nad kontrolkami,
a opisy i błędy pod nimi. Na wąskim ekranie pola przechodzą do jednej kolumny.
Po lewej jest podgląd ikony 100×100px bez dodatkowego tła,
z przyciskiem „Zmień” pod spodem; tworzenie zachowuje podgląd 68×68px.
Korzysta ze wspólnego `profile-edit-body` oraz
`profile-photo-control`; na telefonie podgląd przechodzi nad pola. Dotyczy to
ustawień i tworzenia Pulpitu. Domyślny wybór to konturowa ikona czterech
kafelków `layout-dashboard`, wyświetlana wspólnym rendererem ikon w podglądzie,
menu i katalogu. Nagłówek strony pulpitu zawiera samą nazwę.
Wybrane emoji zachowują własną grafikę.
Kliknięcie podglądu lub „Zmień” otwiera wspólny `shared/EmojiPicker`:
3145 emoji i wariantów Microsoft Fluent Emoji 3D, dziewięć kategorii,
wyszukiwanie po polskich i angielskich nazwach oraz samym emoji. Wyszukiwanie
ignoruje polskie znaki i wielkość liter. „Ostatnio używane” przechowuje lokalnie
do 32 wyborów, osobno dla konta i Workspace. Siatka pokazuje po 120 elementów;
„Pokaż więcej” udostępnia kolejne. Katalog jest pobierany dopiero po otwarciu
pickera, a błędny odczyt można ponowić. Opcja „Domyślna ikona pulpitu” przywraca
cztery kafelki. Wszystkie nazwy i komunikaty są polskie.

Picker używa wspólnego `Dropdown` i jego top layer, zachowuje modal w tle,
obsługuje strzałki siatki i kategorii, Escape oraz powrót fokusu. Rezerwuje
szerokość 400px już przed wczytaniem katalogu; na wąskim ekranie adapter
ogranicza ją do dostępnego miejsca. Pierwsze i ponowne otwarcie, wyszukiwanie
oraz błąd/ponowienie zachowują tę samą szerokość. Wariant flex ma pierwszeństwo
przed siatką zwykłych menu: przewijają się wyniki, a nagłówek i dolny pasek
pozostają widoczne. Wybrany
symbol jest widoczny w dużym podglądzie, a jego nazwa w pickerze; zapis pozostaje częścią formularza
Pulpitu. Ta sama grafika trafia do nagłówka, katalogu, menu i wyszukiwarki.
`ancore-emoji` używa lokalnych atlasów WebP (64px na symbol), dzięki czemu
wygląd jest niezależny od fontu systemu. Grafika jest dekoracyjna, a przyciski
mają polskie nazwy dla czytników ekranu. Cały zestaw zajmuje około 5 MiB.
Zapisane wcześniej identyfikatory ośmiu ikon nadal działają. Nowe wybory
zapisują Unicode; backend akceptuje wyłącznie symbole z lokalnego katalogu.
Źródła, licencje i generator: [biblioteka emoji](../static/vendor/fluent-emoji/README.md).
Zakres ma opcje „Cały Workspace”,
„Wybrane Przestrzenie” i „Zapisany filtr”. Odpowiedni wybór źródła pojawia
się po wyborze zakresu; ukrycie zachowuje szkic do ponownego przełączenia.
Odświeżanie ma opcje „Wyłączone”, „Co minutę”, „Co 5 minut” i „Co 15 minut”.
Zakres pokazuje budynek Workspace, warstwy Przestrzeni albo lejek filtra,
zarówno w wybranej wartości, jak i na liście opcji. Wyłączone odświeżanie
ma przekreślone koło, a aktywne interwały strzałki odświeżania. Wybór
Przestrzeni używa ich własnych avatarów przez wspólny `SpaceSelectMultiple`;
pusty i zbiorczy wybór mają ikonę warstw. Zapisane filtry mają ikonę lejka.
Domyślnie pozostaje wyłączone; działa w widocznym podglądzie, z pauzą
podczas edycji lub otwarcia modalu. W konfiguracji gadżetu pusta Przestrzeń
ma etykietę „Zakres danych pulpitu”; wybór własnej zastępuje ten zakres.
Wspólny `EmbeddedForm` zapisuje tylko bieżącą sekcję i pozostawia okno otwarte.
Błędy walidacji zachowują szkic i ustawiają fokus na nieprawidłowym polu.
Zamknięcie przez Escape, tło lub przycisk chroni szkice wszystkich zakładek.
Zamknięcie po zapisie odświeża także otwarty edytor i jego rewizję.
Widoczność używa wspólnego selecta z ikonami: `lock` dla „Prywatny”, `users`
dla „Wybrane osoby” i `building-2` dla „Cały Workspace”. Pole „Osoby z dostępem”
pojawia się po wyborze „Wybrane osoby”. Gadżety i ich układ korzystają
z `DashboardView` bezpośrednio na stronie; „Gadżety i układ” otwiera ten sam
edytor. Bezpośredni adres konfiguracji pojedynczego gadżetu używa standardowego
formularza modalnego; menu kafelka nie udostępnia już tego wejścia.

Katalog aktywnego Reacta i Podsumowania korzysta ze wspólnego
`shared/WidgetCatalog.tsx` oraz `Modal`. Każdy wiersz pokazuje miniaturę
rzeczywistego komponentu gadżetu, nazwę, opis i osobny przycisk „Dodaj”.
Pulpity oferują „Postęp pracy” z jawnie oznaczonymi danymi przykładowymi;
Podsumowanie pokazuje swoje dostępne gadżety z danymi bieżącej Przestrzeni
i stanem „Dodano”. Podglądy są nieinteraktywne (`inert`, `aria-hidden`)
i skalują się przez `ResizeObserver`; kontrolki miniatur nie przejmują fokusu.
Wariant `widget-catalog-modal` ma do 900px szerokości i 840px wysokości,
przewijaną listę pod stałą wyszukiwarką oraz jednokolumnowe wiersze poniżej 620px.
Wyszukiwanie ignoruje wielkość liter i polskie znaki; brak dopasowań ma osobny stan.
Można dodać wiele kart tego samego rodzaju; limit 24 wyłącza dalsze dodawanie.
Katalog pozostaje otwarty po dodaniu. Escape i zamknięcie przywracają fokus
przycisku, a otwarcie skupia wyszukiwarkę. Wspólna pułapka fokusu pomija
potomków `inert`. Katalog nie zmniejsza szerokości
siatki i nie zapisuje stanu w sessionStorage. Dawny `catalog.html` oraz
kolumnowy kontroler pozostają tylko adapterami zgodności starszych wejść;
React przejmuje edycję siatki. Pierwszy render Django pokazuje zapisane
pozycje bez menu konfiguracji/usuwania; bezpośrednie formularze pozostają
w backendzie.

## Ekrany React podczas migracji

Aktualny zakres i kontrakt danych opisuje [FRONTEND.md](FRONTEND.md).
Przeniesione ekrany zachowują klasy istniejących szablonów. Małe adaptery
są w `static/css/components/react.css`: kontenery `display: contents`,
wyspy selectów i jawne ukrywanie paneli z `hidden`, których dawny
CSS był związany z atrybutami starszego JavaScriptu. Wariant
`tasks-issue-select-wrap` zapewnia kontrolkom zadania ten sam wygląd co wcześniej.
Modale, pasek „Pokaż więcej”, tabela członków i grupy statusów mają współdzielone
komponenty React. Biblioteka ikon, tokeny i kolory pozostają istniejące.

`shared/Icon` renderuje bezpośredni SVG, pobierając glif przez `AncoreIcons`
w odłączonym kontenerze. React zachowuje własność korzenia, a helper nie
podmienia zamontowanego elementu. Brak dodatkowego wrappera zachowuje
selektory `> svg`, rozmiary, kolejność i wyrównanie ikon wspólnego CSS.
Strzałkę grupy obraca istniejący CSS według `aria-expanded`.
`Select.hideLabel` używa `tasks-inline-select` i wariantu `react-select-inline`:
kontenery nie dodają marginesów ani własnych pól do układu flex. Filtry
Przestrzeni zachowują nazwy pól, ikony i zawijanie jak w szablonie.

Pola formularzy wewnątrz `resources-react-fieldset` zachowują na szerokim
ekranie wiersze z etykietą 180px, odstępem 24px i elastyczną kontrolką.
`react-field-control` jest przezroczysty dla układu; pomoc i błędy należą
do kolumny kontrolki. Kompaktowe modale zachowują układ pionowy.
Backlog i kolumny aktywnego sprintu renderują `StatusGroup` bez dodatkowej
sekcji: działają odstępy między grupami, wysokości list i kolejność
metadanych, akcji oraz końcowego licznika. Komórki miesiąca Kalendarza
używają dotychczasowego tekstowego „+”, dopasowanego do szerokości na telefonie.

Dysk i Dokumenty używają `src/documents/`: zachowane klasy katalogów, ikon SVG,
paneli filtrów/sortowania, osobnego wyboru liczby wierszy i modali. Adapter CSS
odwzorowuje rozmiary bezpośrednich ikon SVG oraz desktopowy układ
etykieta–pole w formularzu. Ikony plików/folderów/dysków mają tę samą geometrię
co include’y Django. React obsługuje listę/kafelki, zaznaczenia, panel dysków
z fokusem i Escape, przenoszenie oraz podglądy. Opisy wcześniejszych funkcji
`documents.js`, `office.js` i `office-suite.js` dotyczą szablonów zgodności;
te skrypty pomijają korzeń Reacta. Tekstowy edytor treści oraz zewnętrzne
edytory mają odrębne wyspy DOM. Tworzenie pliku zachowuje katalog i otwiera
nową kartę; blokada popupu pokazuje jeden link do zapisanego dokumentu.

Zarządzanie Workspace renderuje `src/workspaces/`. Zachowuje katalog, lokalne
wyszukiwanie, odsłanianie po 20 przez „Pokaż więcej”, zaznaczenia wczytanych
wierszy i oddzielne przełączanie
kontekstu. Ustawienia korzystają z pełnej strony, menu sekcji po lewej,
wspólnego `PageHeader` oraz `Toolbar`, zgodnie z ustawieniami Przestrzeni.
Tworzenie zachowuje `workplace-create-modal`; dodawanie osoby pozostaje
kompaktowym oknem nad stroną członków. `shared/Modal` ma opcjonalny nagłówek
i klasy dialogu dla powłoki Projektów, z tą samą obsługą fokusu i Escape.
Picker awatara/kadrowania jest wyspą DOM z dotychczasowym wyglądem i helperami.
Escape w kadrze lub podpowiedziach osoby zamyka najpierw ten element.
Pozycjonowanie dropdownu pomija kontenery za przodkiem `position: fixed`,
które nie przycinają kontrolek pełnego modala nad boczną nawigacją.
Powłoka modala wybiera początkowy fokus wyłącznie spośród własnych kontrolek
w widocznych panelach; pomija schowany picker awatara i preferuje aktywną zakładkę.


Lista modułów Workspace używa wariantu `workplace-module-fields` z siatką
`workplace-module-grid`: dwie kolumny kart, a do 767px jedna. Karta zawiera
ikonę ze wspólnego zestawu, nazwę, krótki polski opis i istniejący przełącznik
`tasks-toggle` w kolorze `--system-accent`. Cała etykieta przełącza natywny
checkbox z rolą `switch`; Tab i spacja zachowują obsługę klawiatury, a fokus
wyróżnia kartę. Powierzchnie, obramowanie i odstępy korzystają ze wspólnych
tokenów. Wyłączony moduł ma tło `--panel-bg` oraz przygaszoną ikonę i tekst
(krycie 55%); przełącznik pozostaje w pełni widoczny i aktywny.
Włączenie natychmiast przywraca pełne krycie. Zmiany zapisuje przycisk formularza;
dane modułu pozostają zachowane. React oraz widget `WorkplaceModuleSelect`
pierwszego renderu Django współdzielą opisy i ikony z `MODULE_DETAILS`.
`workplace-invite-links` i `workplace-invite-link` układają
link, opis i istniejące przyciski w zawijanym wierszu; pole adresu może się
zwężać na telefonie, a modal zachowuje własne przewijanie.
