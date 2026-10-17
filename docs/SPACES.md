# Przestrzenie i zespoły

## Adresy przestrzeni

Przestrzeń używa adresu `/space/<slug>/` oraz
`/workplaces/<kod-workspace>/space/<slug>/`, np. `space/scrum-szablon/`.
`Space.slug` powstaje z nazwy przestrzeni: małe litery, myślniki zamiast spacji
i transliteracja polskich znaków, również `ł`. Duplikaty w tym samym Workspace
otrzymują `-2`, `-3`; nazwy numeryczne prefiks `przestrzen-`, a nazwy bez znaków
URL zastępczy segment `przestrzen`. Zapis blokuje Workspace podczas przydziału,
a baza wymusza unikalność `(workplace, slug)`. Zmiana nazwy zachowuje adres.
Migracja `spaces.0005_space_slugs` nadaje adresy istniejącym przestrzeniom,
nie zmieniając ich pozostałych danych ani relacji.

Menu, katalog, wyszukiwanie, podsumowanie, zespoły, zakładki i powroty po zapisie
używają nazwy w adresie. Akcje przestrzeni mają ten sam prefiks `space/<slug>/`.
Katalog i zarządzanie pozostają pod `/spaces/`. Szczegóły zadania i jego akcje
są pod `/space/<slug>/tasks/<klucz>/`, również w adresie scoped.
Parametr `view=list|backlog|board|timeline` zachowuje miejsce powrotu;
zakładkę szczegółów wybiera `tab`. Stare numeryczne endpointy operacji
`/spaces/items/<pk>/` pozostają dla zgodności.
Edycja z zarządzania używa `/spaces/manage/<slug>/edit/`.
Nazwy routingu `spaces` i `workplace_spaces` pozostają wspólne dla obu prefiksów.
Dawne `/spaces/<pk>/` przekierowuje GET/HEAD po kontroli dostępu, zachowując
parametry zapytania; numeryczne endpointy zapisu nadal działają dla zgodności.
Slug rozwiązywany jest wyłącznie w aktywnym Workspace przez `visible_spaces`.
Częściowa nawigacja obsługuje oba prefiksy także w scoped adresach.

## Katalog i zarządzanie przestrzeniami

„Przestrzenie” (`/spaces/` i scoped odpowiednik) jest katalogiem do codziennej
pracy: wszystkie dostępne przestrzenie, ulubione, prywatne, rodzaj, wyszukiwanie
i liczba widocznych zadań. Nazwa otwiera podsumowanie przestrzeni.
Tabela ma checkboxy i menu trzech pasków w dwóch pierwszych kolumnach,
jak katalog Projektów. Checkbox nagłówka zaznacza bieżącą stronę;
zaznaczenie jest lokalne i resetuje się po zmianie widoku. Menu wiersza
zawiera otwarcie, ulubione i ustawienia; edycja oraz dodawanie osób do
prywatnej przestrzeni wymagają istniejącego prawa `manage_space`.
Zmiana ulubionych zachowuje adres i filtry katalogu, także bez JavaScriptu.
Podmenu głównej nawigacji pokazuje do sześciu dostępnych przestrzeni w blokach
„Oznaczone gwiazdką” i „Ostatnie”, bez linii drzewa. Osobiste ulubione są
uporządkowane po nazwie; pozostałe miejsca zajmują ostatnio odwiedzone
przestrzenie, a następnie najnowsze. Historia korzysta z istniejącej sesji
`dashboard.recent` i zapamiętuje oglądaną przestrzeń przed renderowaniem menu.
Puste bloki nie pokazują nagłówków. `backend/spaces/navigation.py` za każdym razem
sprawdza aktywny Workspace i bieżący dostęp; gwiazdka nie nadaje uprawnień.
Częściowa nawigacja odświeża linki z
odpowiedzi serwera, więc utworzenie przestrzeni nie wymaga ręcznego przeładowania
strony. Ten sam mechanizm aktualizuje nazwy, awatary i pozycje po zmianie
ulubionych lub utracie dostępu, zachowując stan zwinięcia sekcji.

Wiersz pokazuje menu „…” przy najechaniu, fokusie lub otwarciu, a na telefonie
stale. Menu pozwala zmienić osobistą gwiazdkę i otworzyć ustawienia przestrzeni.
„Dodaj osoby” otwiera istniejący formularz członków wyłącznie dla osób
zarządzających prywatną przestrzenią. Publiczne przestrzenie zachowują dostęp
poprzez Workspace; obserwatorzy nie zarządzają członkami. Stopka menu pokazuje
rodzaj i sposób zarządzania. Korzysta ze wspólnego `row-actions.js` oraz
niemodalnego popovera. Akcja gwiazdki używa dotychczasowej relacji
`Space.favorited_by` i endpointu POST; `space-navigation.js` odświeża
bieżący ekran przez `AncoreApp`, pozostawiając jego adres. Bez JavaScriptu
formularz wraca do bezpiecznego adresu `next` z tego samego hosta. Błąd zapisu
pokazuje powiadomienie i pozwala ponowić akcję.

„Zarządzaj przestrzeniami” (`/spaces/manage/` i scoped odpowiednik) to osobny
ekran ustawień, dostępny z menu „…” przy Przestrzeniach oraz z Ustawień Ancore.
Główny pasek boczny pokazuje własne minimalne menu, jak katalog Workspace:
„Wróć do ustawień” i aktywne „Przestrzenie”, pod nagłówkiem zarządzania
przestrzeniami. Nie ma kategorii Ustawień ani innych modułów. Link powrotu
prowadzi do sekcji Workspace w treści Ustawień. Linki trzech stron zarządzania
pozostają w tej sekcji. Menu i aktywność aktualizują się także przy częściowej nawigacji,
przeładowaniu i korzystaniu z historii. Workspace zachowuje własne menu zarządzania.
Ekran zawiera wyszukiwanie po nazwie/kluczu, filtry rodzaju i sposobu zarządzania
oraz paginację. Lista współdzieli `spaces/directory.html` z „Przestrzenie”:
checkboxy, menu po lewej oraz kolumny Klucz, Przestrzeń, Rodzaj, Szablon, Opis
i liczba widocznych zadań. Zachowuje te same szerokości, ikony i awatary.
Zaznaczenie dotyczy bieżącej strony, bez operacji zbiorczych.
Filtry są po lewej, wyszukiwarka po prawej, a pasek stron na dole panelu.
Nazwa prowadzi do ustawień przestrzeni; menu wiersza udostępnia otwarcie,
osobiste ulubione, edycję, ustawienia dostępu i konfigurację zadań
(jeśli osoba może ją zmieniać). Gwiazdka zachowuje adres i filtry zarządzania.

`manageable_spaces` zawęża `visible_spaces` według istniejącego `manage_space`.
Właściciel/administrator Workspace zarządza widocznymi przestrzeniami
publicznymi; osoba odpowiedzialna również może zarządzać swoją publiczną
przestrzenią. Prywatnymi przestrzeniami zarządza ich prywatny właściciel lub
administrator przestrzeni. Administrator Workspace nie uzyskuje dostępu do
nieudostępnionych prywatnych przestrzeni. Zwykłe członkostwo, obserwowanie
i przydział wykonawcy nie dają dostępu do katalogu zarządzania.
Właściciel/administrator Workspace ma do niego dostęp również przed
utworzeniem pierwszej przestrzeni; pozostałe osoby muszą mieć co najmniej
jedną przestrzeń, którą mogą zarządzać. Endpoint i formularze kontrolują
uprawnienia niezależnie od widoczności linków.

`/spaces/manage/create/` i `/spaces/manage/<pk>/edit/` używają istniejącego
formularza oraz powłoki modalnej. Bezpośrednie wejście i błąd walidacji
pozostawiają ekran zarządzania pod modalem; anulowanie i zapis wracają do
niego. Tworzenie z codziennego katalogu zachowuje dotychczasowy przepływ.
Oba katalogi korzystają z tego samego modelu `Space`.

## Tworzenie przestrzeni i wybór szablonu

„Utwórz przestrzeń” w katalogu, zarządzaniu oraz plus w menu bocznym otwierają
ten sam kreator. Pierwszy krok to ilustrowane kafelki wszystkich sześciu
szablonów z `backend/spaces/defaults.py`: Kanban, Scrum, Zarządzanie zadaniami,
Marketing, Rekrutacja i Obsługa zgłoszeń. Wybranie kafelka otwiera drugi krok
z nazwą, kluczem, opisem, sposobem zarządzania, wspólną konfiguracją
i widocznością. Rodzaj przestrzeni jest automatycznie ustalany na podstawie
szablonu; oba identyfikatory pozostają walidowanymi polami formularza.
„Zmień szablon” zachowuje wpisane dane. Błąd formularza także zachowuje wybór
i drugi krok, a nieznany szablon ponownie pokazuje kafelki z komunikatem.
Przejście pomiędzy krokami nie zapisuje niczego w bazie. Dopiero końcowe
„Utwórz przestrzeń” używa istniejącej transakcji i konfiguracji szablonu.
Edycja istniejącej przestrzeni nie udostępnia zmiany szablonu.

## Szybkie wyszukiwanie przestrzeni

„Więcej przestrzeni” w menu bocznym otwiera panel z wyszukiwaniem po nazwie
lub kluczu i przejściem do pełnego katalogu. Endpoint GET `/spaces/search/`
oraz jego scoped odpowiednik zwracają do 20 wyników przez `visible_spaces`:
tylko aktywny Workspace, jego właściciel danych i przestrzenie dostępne aktualnemu
użytkownikowi. Obserwatorzy również mogą wyszukiwać; przydział wykonawcy nie
nadaje dostępu. Odpowiedź jest prywatna i nie jest buforowana. Puste zapytanie
nie zwraca wyników; katalog zachowuje wpisaną frazę. Panel korzysta ze wspólnych
awatarów, nie pobiera plików poza kontrolowanym endpointem.

## Awatary przestrzeni

Każda przestrzeń ma awatar widoczny w menu bocznym, katalogu i nagłówku
wszystkich jej widoków. Domyślny wariant dobierany jest stabilnie według ID
przestrzeni z 24 kolorowych ilustracji. Kliknięcie awatara w nagłówku lub
„Zmień awatar” w ustawieniach otwiera okno wyboru. Zapis wymaga tego samego
prawa zarządzania co edycja przestrzeni (`manage_space`); członek i obserwator
widzą awatar, ale go nie zmieniają.

Można wybrać jedną z 30 ilustracji, przywrócić awatar automatyczny albo przesłać własny PNG,
JPG lub WebP do 5 MB, również przez przeciągnięcie. Gotowe awatary to pełnokolorowe
ilustracje z lokalnych atlasów `static/img/space-avatars/illustrations-v1.png`
oraz `illustrations-extra-v1.png`, wygenerowanych przez ImageGen. Dokładne prompty
zapisano obok w `PROMPT.txt` i `PROMPT-extra.txt`. Dodatkowe sześć motywów to
aparat, słuchawki, góry, diament, kawa i balon. Zestaw współdzielą Przestrzenie
i Workspace. Rozszerzenie zachowuje pierwotne ilustracje i automatyczne przypisania.
Wspólny CSS wybiera kwadratowy fragment dla każdego motywu. Pole `Space.avatar`
przechowuje stabilny identyfikator motywu, a `Space.avatar_photo` opcjonalny obraz.
Zamiana wcześniejszych ikon konturowych na ilustracje zachowuje zapisane wybory
i automatyczne przypisania; nie wymaga kolejnej migracji.
Zmiana awatara nie zmienia nazwy, konfiguracji, zadań ani uprawnień przestrzeni.

Obrazy mają losowe nazwy w prywatnym storage; pobieranie przez
`/spaces/<pk>/avatar/photo/` i scoped odpowiednik sprawdza aktywny Workspace
oraz widoczność przestrzeni. Odpowiedź ma `private, no-store` i `nosniff`.
Wybór ikony usuwa własny obraz po zatwierdzeniu transakcji. Podmiana i usunięcie
przestrzeni sprzątają nieużywany plik dopiero po commit; nieudany zapis usuwa
nowo przesłany plik. Wymagana migracja: `spaces.0003_space_avatar_space_avatar_photo`.

Weryfikacja awatarów (3.10.2026): 43 testy `spaces` i `core.test_file_lifecycle`
przeszły; lokalna migracja została zastosowana. Playwright/Chrome na izolowanej
bazie sprawdził wybór i trwałość ikony, aktualizację menu, upload i przeciąganie,
błędy walidacji, Escape/fokus, pusty katalog i ponowne wejście przy 1440×1000
oraz 390×844. Szerszy zestaw Core/Workplaces ma wcześniejsze błędy; porównanie
z ostatnim commitem potwierdziło te same 13 nieudanych asercji i 14 błędów
w starszych testach nawigacji oraz Workspace.

## Typy zgłoszeń

Typ zgłoszenia jest zapisywany w `WorkItem.work_type` należącym do `SpaceTask`. Formularz tworzenia/edycji w przestrzeni
oraz szczegóły zadania pozwalają wybrać typ z konfiguracji tej przestrzeni.
Nowe szablony zawierają Zadanie, Błąd, Historyjkę i Epik. Marketing zachowuje
Kampanię i Materiał; Rekrutacja Kandydaturę i Rozmowę, a Obsługa zgłoszeń
Zgłoszenie i Incydent, również jako dotychczasowe wartości domyślne.
Podzadania nadal korzystają z relacji `SpaceTask.parent`; sam typ nie zmienia hierarchii.

Migracja `spaces.0004_issue_types` dopisuje brakujące cztery standardowe typy do
istniejących konfiguracji, także współdzielonych. Zachowuje własne nazwy, typy,
kolejność, statusy, pola oraz wszystkie zadania. Cofnięcie migracji pozostawia
te opcje, ponieważ zadania mogą już ich używać. Administrator nadal może
zmieniać dostępne typy przez „Statusy, typy i pola”; używanego typu nie można usunąć.

Listy, backlog i karty tablicy pokazują ikonę i nazwę typu. Filtr „Typ zgłoszenia”
na liście, tablicy, backlogu, osi czasu i we Wszystkich zadaniach działa na
serwerze przed paginacją, razem z wyszukiwaniem, wykonawcą i zespołem.
Zakres danych i dostęp do edycji wyznaczają `spaces.access` oraz aktywny
Workspace. Zmiana typu zapisuje w `SpaceTaskActivity` faktycznego autora
i poprzednią wartość. Formularze przestrzeni
blokują zmianę epika z przypisanymi zadaniami oraz zagnieżdżenie epika w epiku.

## Model pracy

Od 3.10.2026 główna nawigacja prowadzi do katalogu Przestrzeni, Wszystkich
zadań i Zespołów. Przestrzeń organizuje pracę; zespół grupuje osoby. Workspace
pozostaje nadrzędną granicą danych i członkostwa. Pod Zasobami zwijana sekcja
„Starsze widoki” udostępnia dawne katalogi Projektów (także Ulubione), Grup,
Zadań, Szablonów projektów i Kanbana. Globalny katalog Tagów jest wycofany. Katalogi Kontaktów, Firm, Użytkowników
i Gości są wycofane z menu i routingu. Skróty używają aktywnego Workspace
i zachowują istniejące przekierowania
Kanbana; nie przywracają edycji przeniesionych rekordów źródłowych.

Od 10.10.2026 `Space` ma własną nazwę, opis, właściciela, widoczność,
ulubione i role `SpaceMembership`. `SpaceTask` przechowuje treść, terminy,
wykonawcę, hierarchię i stan zakończenia. `WorkItem.task` wskazuje wyłącznie
`SpaceTask`; nadal przechowuje klucz oraz planowanie: status przestrzeni,
typ zgłoszenia, sprint, epik, zespół, punkty i kolejność.
Komentarze/historia, pliki, czas i dostęp do zadania mają własne modele
`SpaceTaskActivity`, `SpaceTaskFile`, `SpaceTaskWorkLog`, `SpaceTaskMembership`.
Nowe przestrzenie i zadania nie tworzą projektów, grup ani `tasks.Task`.
Tworzenie starszych obiektów również nie tworzy przestrzeni.

`Space.project` i `WorkItem.legacy_task` są opcjonalnymi, historycznymi
mapowaniami importu. Nie wyznaczają bieżącej treści ani uprawnień i nie
synchronizują zmian. Wspólne konto, Workspace, słownik tagów `TaskTag`,
walidatory plików i komponenty UI pozostają mechanizmami całej aplikacji.

Punkty wejścia: `backend/spaces/views.py`, `task_views.py`, `access.py`, `services.py`, `forms.py`, `teams.py`,
`signals.py`, `middleware.py`, `templates/spaces/`, `static/js/spaces.js`.
Trasy `/spaces/` i `/teams/` mają również warianty scoped
`/workplaces/<slug>/spaces/` i `/workplaces/<slug>/teams/`.
Dawne `/spaces/items/` oraz scoped odpowiednik przekierowują do
„Filtry → Wyszukaj zadania”, zachowując tekst, typ, przypisanie do mnie
i stronę. Osobny ekran Wszystkich zadań i skrót `tasks-all` są wycofane.

## Dostępne funkcje

### Planowanie w Backlogu

Backlog Scrum pokazuje aktywny sprint jako pierwszy, następnie sprinty planowane
i kolejkę bez sprintu. Wiersze mają estymację (zero jest wartością, „—” oznacza
brak estymacji) oraz wykonawcę. Nagłówki pokazują punkty, brakujące estymacje
i postęp ukończenia. Agregacje obejmują wszystkie dostępne zadania po filtrach,
również poza stroną; licznik wierszy dotyczy bieżącej strony, a różnica jest
opisana jako „Na stronie”. Zakończone zadania nie należą do kolejki planowania.

Checkboxy wierszy zaznaczają wyłącznie zadania bieżącej strony,
do których użytkownik ma prawo edycji. Nie ma górnego checkboxu ani nagłówka
„Planowanie sprintów”; pasek operacji pojawia się po zaznaczeniu zadania
i znika po odznaczeniu ostatniego. „Przenieś zaznaczone” przenosi od 1 do
100 zadań do otwartego sprintu lub backlogu, w dotychczasowej kolejności,
na koniec grupy docelowej. Kanban pozwala przenieść zaznaczenie na tablicę.
`backlog/plan/` sprawdza pełne zaznaczenie, filtry, stronę, ACL i zapamiętane
położenia przed zapisem. Konflikt lub brak prawa do jednego zadania wycofuje
całą operację. Pozostałe zadania zachowują kolejność; statusy i daty zakończenia
nie zmieniają się, a historia wskazuje faktycznego autora.
Nagłówki sprintów i sekcji Backlog nie zawierają checkboxów.
Nowy `WorkItem` otrzymuje kolejność po najwyższym aktualnym numerze, niezależnie
od trwałego klucza zadania; tworzenie nie koliduje z pozycjami zmienionymi w planowaniu.

Każda sekcja pozwala utworzyć zadanie z domyślnym miejscem planowania.
Tworzenie i edycja zachowują filtry oraz wracają do backlogu. Sprint można
edytować, rozpocząć po dodaniu zadań oraz zakończyć przez wspólne okno aplikacji.
Przycisk „Utwórz sprint” znajduje się w nagłówku sekcji Backlog, również
przy zwiniętej liście, z dotychczasową kontrolą uprawnień zarządzania Scrum.
Nowy sprint otrzymuje propozycję nazwy i dwutygodniowych dat po ostatnim
otwartym sprincie. Zakończenie pokazuje podsumowanie dostępnej pracy i pozwala
przenieść niedokończone zadania do backlogu lub kolejnego sprintu planowanego.
Zakończone zadania pozostają w starym sprincie. `Sprint.result` zachowuje
podsumowanie punktów i przeniesień, bez zmiany statusów zadań.

Zarządzanie sprintami wymaga `manage_space`; przenoszenie zadań wymaga ich
indywidualnego prawa edycji. Obserwator widzi dane bez kontrolek zapisu.
Zakończenie sprintu z zadaniem niedostępnym do edycji jest odrzucane atomowo.
Endpointy planowania i formularze sprintów mają zwykłe, scoped oraz zachowane
numeryczne warianty adresów. Nie wymagają nowych modeli ani migracji.

### Pozostałe funkcje

- Katalog przestrzeni: lista w stylu projektów i grup, wyszukiwanie, rodzaj,
  ulubione, prywatne i paginacja. Kolumny pokazują klucz, nazwę, rodzaj,
  szablon, opis i liczbę dostępnych zadań.
- Kreator: nazwa, klucz, opis, rodzaj, szablon, zarządzanie i widoczność.
  Bezpośrednie wejście pod `/spaces/create/` (również scoped) wyświetla ten sam
  modal nad pełnym katalogiem przestrzeni. Zamknięcie, anulowanie lub Escape
  pozostawia katalog i przywraca jego adres; nie ma pustej strony „Utwórz
  przestrzeń” z przyciskiem „Wróć”. Błąd walidacji zachowuje formularz nad listą.
  Plus w menu bocznym na ekranach Przestrzeni i Zespołów otwiera modal nad
  bieżącą treścią; z innych modułów prowadzi do kreatora nad katalogiem.
- Rodzaje: programistyczny, biznesowy, obsługowy.
- Szablony: Kanban, Scrum, zarządzanie zadaniami, marketing, rekrutacja,
  obsługa zgłoszeń. Szablon określa początkowe statusy, typy i pola.
- Widoki przestrzeni: podsumowanie, lista, tablica, oś czasu, raporty, tagi i ustawienia.
  Lista i aktywny sprint współdzielą kolorowe, zwijane nagłówki statusów
  oraz styl zadań. Tak jak backlog pokazują punkty w Scrum, awatar wykonawcy
  i menu z trzema paskami dla zadań z prawem edycji. Sprint zachowuje osobne
  kafelki w kolumnach i zawijane tytuły, a tablica
  Kanbana dotychczasowy wygląd kart. Przeciąganie zapisuje kolejność w kolumnie
  oraz miejsce wstawienia w innym statusie; przerywana linia wskazuje pozycję.
  Status i kolejność można zmienić również przez menu działań,
  dostępne również klawiaturą. Filtry są w standardowym pasku Zadań.
  Lista, backlog, tablica i oś czasu mają wspólny dolny pasek z zakresem
  wyników, strzałkami i numerami stron. Pasek pozostaje widoczny pod przewijaną
  treścią, zachowuje filtry i działa również dla jednej strony/pustego wyniku.
  Katalogi Przestrzeni, Zespoły i Filtry korzystają z tego samego komponentu;
  podsumowanie, raporty i ustawienia nie pokazują stron wyników.
- Podsumowanie: cztery liczniki zakończonych, zaktualizowanych i utworzonych
  zadań w ostatnich 7 dniach oraz otwartych z terminem w najbliższych 7 dniach.
  Aktualizacja wynika z historii `SpaceTaskActivity` (dowolna akcja poza utworzeniem);
  wiele wpisów jednego zadania liczy się raz. Zakończenie opiera się na
  aktualnym statusie `closed` i `completion_date`. Przedziały są liczone od
  chwili wyświetlenia, z obiema granicami włącznie; przyszła historia i daty
  utworzenia/zakończenia są pomijane. Wykres statusów obejmuje otwarte zadania
  i zakończone w ostatnich 14 dniach, zachowując własne nazwy statusów.
  Priorytety i obciążenie wykonawców obejmują otwarte zadania, w tym
  nieprzypisane; typy zgłoszeń obejmują wszystkie zadania. Historia pokazuje
  8 ostatnich wpisów z autorem i linkiem do zadania. Przestrzenie programistyczne
  pokazują też postęp epików liczony z ich dostępnych powiązanych zadań.
  Agregacje uwzględniają podzadania i pełny zbiór dostępny użytkownikowi,
  niezależnie od paginacji listy. Liczniki, statusy, priorytety, typy i wykonawcy
  otwierają listę z odpowiednimi filtrami; epiki i aktywność prowadzą do
  szczegółów pod trwałym kluczem przestrzeni. Lista zachowuje filtry przy szukaniu i paginacji,
  a zakres czasu/otwartych zadań można usunąć osobnym linkiem.
  `backend/spaces/summary.py` wyznacza identyfikatory z istniejącego querysetu
  ACL i filtrów w PostgreSQL `MATERIALIZED` CTE przed agregacją. Zapobiega to
  rozwijaniu wielokrotnie zagnieżdżonych kontroli dostępu do wolnego planu
  grupowania po wykonawcy. Zakres jest obliczany na nowo w tym samym zapytaniu
  co licznik/wykres; nie ma cache ani utrwalenia uprawnień między żądaniami.
- Scrum: backlog, epiki, punkty, planowanie i rozpoczęcie sprintu, jeden aktywny
  sprint, zakończenie z powrotem niezakończonych zadań do backlogu.
  Backlog i sprinty mają zwarte sekcje Listy zadań ze zwijaniem, licznikami,
  datami i akcjami sprintu w nagłówku; pusty cel nie dodaje odstępu.
  Przeciąganie zmienia kolejność oraz przenosi zadania między backlogiem
  a planowanymi/aktywnymi sprintami; dotyk zaczyna gest na istniejącej ikonie
  priorytetu. Osobne uchwyty i ich kolumna nie są wyświetlane.
  Te same przeniesienia są dostępne w menu zadania.
- Kanban: kolejka backlogu oddzielona od zadań na tablicy i zmiana kolejności,
  wyświetlana w tej samej zwijanej sekcji Zadań.

- Oś czasu: paski pomiędzy początkiem i terminem; zadania bez dat są pomijane.
- Raporty: aktualne liczby statusów, zakończone i zaległe zadania oraz sprinty.
- Konfiguracja: typy, pola tekst/liczba/data, wymagane pola, statusy i dozwolone
  przejścia. Każdy status ma jeden z pięciu stanów `SpaceTask`.
  Stan `closed` nadal odpowiada za zakończenie i datę wykonania.
- Zespoły: katalog, moje zespoły, wyszukiwanie, profil, prywatnie serwowane zdjęcie,
  członkowie i administratorzy, powiązane przestrzenie i przypisane zadania.
  Zadanie może równocześnie mieć zespół oraz konkretnego wykonawcę.

W backlogu „Przesuń wyżej/niżej” działa w zakresie widocznych zadań i tej samej grupy
sprintu. Pomija zadania na tablicy Kanbana, zadania zamknięte i wykluczone przez
filtry. URL akcji oraz powrót zachowują wyszukiwanie i filtry listy. Odczyt listy
i zmiana kolejności korzystają z tych samych funkcji filtrujących.

Przeciąganie (`backend/spaces/backlog.py`, akcja `plan` w `item_action`) waliduje
zadanie i oba sąsiednie wiersze w zakresie filtrów oraz bieżącej strony
100 wyników. Cel należy do tej samej przestrzeni; zakończone sprinty,
zamknięte zadania, elementy na tablicy Kanbana i rekordy poza widoczną stroną
są odrzucane. Akcja planowania w backlogu Kanbana nie przyjmuje sprintów ani kart z tablicy.
Serwer porównuje również przestrzeń, sprint źródłowy i zapamiętaną kolejność
zadania; stare położenie wymaga odświeżenia listy. Blokady właściciela,
Workspace, przestrzeni i rekordu oraz ponowne sprawdzenie dostępu chronią zapis.
Zmiana ustawia wyłącznie `sprint`, `in_backlog` i `rank`, bez zmiany statusu
lub daty zakończenia zadania; historia zapisuje rzeczywistego autora.
Nowa pozycja korzysta z wolnego numeru pomiędzy sąsiadami. Gdy brak miejsca
między całkowitymi numerami, rotuje dostępne numery bieżącej grupy, sprawdzając
prawo edycji każdego zmienianego rekordu. Zadania ukryte, pominięte filtrami
lub poza stroną zachowują swoje numery. Zapis jest atomowy i wymaga CSRF.

Tablica (`backend/spaces/board.py`, akcja `position` w `item_action`) korzysta z tych
samych numerów `WorkItem.rank` i funkcji wyznaczania wolnego miejsca.
Obsługuje kolejność w statusie i wstawienie między sąsiadami innego statusu;
menu „Przesuń wyżej/niżej” działa w bieżącej kolumnie. Źródło i sąsiedzi muszą
należeć do aktualnej widocznej, przefiltrowanej strony 100 wyników. Scrum
ogranicza operację do aktywnego sprintu, a pozostałe tablice do zadań poza
backlogiem. Porównanie przestrzeni, źródłowego statusu, sprintu, numeru
kolejności oraz numerów obu sąsiadów odrzuca nieaktualne położenie.
Zapis zachowuje Workspace, ACL, CSRF i blokady jak planowanie; ukryte,
wykluczone i pozostałe strony nie są przestawiane. Czytelny sąsiad bez prawa
edycji może wskazać miejsce, ale jego numer nie może zostać zmieniony.
Zmiana statusu przechodzi przez `set_status`, z zachowaniem sygnałów zadania,
dat zakończenia i historii rzeczywistego autora; cała operacja jest atomowa.
Zmiana samej kolejności, także w kolumnie zakończonych, zachowuje status
i datę zakończenia. Niezmienione położenie nie dopisuje historii.

Klucz przestrzeni jest unikalny w Workspace. Zadania otrzymują trwały klucz,
np. `ANC-12`, z rosnącego licznika przestrzeni. Usunięcie zadania nie zmienia
kluczy pozostałych. Zadanie pozostaje w swojej przestrzeni; zapis modelu
odrzuca zmianę przestrzeni, obcego rodzica i cykl podzadań. Nie należy mylić
klucza z PK ani dawnym, renumerowanym `tasks.Task.task_id`.
Szczegóły są pod `/space/<slug>/tasks/<klucz>/?view=list`. Wspólna powłoka
zadania pokazuje strzałkę powrotu i tytuł, zakładki i treść po lewej
oraz właściwości po prawej, bez powtarzania nagłówka przestrzeni. Powrót
zachowuje widok i filtry. Wszystkie pięć zakładek używa układu starszego ekranu
Zadań i wspólnych tabel, modali oraz strumienia historii. Kategoria i
przypomnienie są polami `SpaceTask`; planowanie pozostaje w istniejącej edycji
przestrzeni i jest zachowane przy zapisie szczegółów.
Szczegóły automatycznie zapisują tytuł i opis po 700 ms przerwy w pisaniu;
zmiana pola wyboru, daty lub dodanie załącznika uruchamia zapis od razu.
Żądania do tego samego endpointu `action=save` są wykonywane kolejno, bez
przeładowania strony. Zmiany wpisane podczas zapisu trafiają do następnego
żądania. Lista `autosave_fields` określa zmienione pola; pozostałe wartości,
w tym planowanie, pochodzą z aktualnego rekordu pod blokadą. Powtórzenie
niezmienionych danych nie dopisuje historii. Nagłówek, data zamknięcia,
historia, członkowie po zmianie widoczności i zapisane załączniki odświeżają
się w otwartym widoku. Komentarze wymagają użycia przycisku wysyłania.
Błąd zachowuje szkic oraz wybrane pliki; „Spróbuj ponownie” w banerze błędu ponawia zapis,
a powrót połączenia uruchamia kolejną próbę. Częściowa nawigacja czeka na
zapis i pozostaje na zadaniu przy błędzie. Pełne wyjście lub przeładowanie
z niezapisanymi zmianami chroni `beforeunload`; szkic nie jest utrwalany poza
otwartą stroną. Bez JavaScript pozostaje zwykły przycisk „Zapisz” i POST.
Załączniki wybrane przy „Dodaj załącznik” zapisują się razem z danymi zadania,
z walidacją i wycofaniem całej operacji przy błędzie. „Główna”, „Podzadania”, „Dziennik pracy”,
„Członkowie” i „Historia” mają własne operacje w `backend/spaces/task_views.py`.
Pliki są walidowane i pobierane po ponownej kontroli dostępu. Usunięcie
zadania wymaga prawa edycji wszystkich kaskadowo usuwanych potomków.

## Tagi przestrzeni

Zakładka „Tagi” pod `/<pk>/?view=tags` (także scoped) korzysta z istniejącego
modelu `tasks.TaskTag`, tabeli, filtrów, sortowania, paginacji, modali, informacji
i notatek starszego katalogu. Każdy tag wskazuje dokładnie jedną przestrzeń;
nazwa może powtarzać się w innych przestrzeniach. Osoby z prawem edycji przestrzeni
tworzą, edytują i usuwają tagi, także zbiorczo, oraz dodają notatki. Obserwator
ma odczyt; edycja/usunięcie notatki dodatkowo wymaga bycia jej autorem.
Liczba zadań zachowuje zasadę starszego katalogu: dostępne zadania główne,
bez podzadań i bez ujawniania prywatnych zadań.

Formularze nowego zadania i szczegółów oraz powiązania tagów ograniczają wybór
do zapisanej przestrzeni i Workspace. Bezpośredni zapis obcego identyfikatora
jest odrzucany, również od strony relacji odwrotnej `TaskTag.space_tasks`.
Starsze formularze Tasks nie edytują nowych zadań i nie przypisują tagów przestrzeni. Globalne wyszukiwanie
filtruje tagi przez dostęp do przestrzeni i kieruje do jej zakładki.

Migracje Tasks `0064_space_tags` i `0065_space_tag_data` rozdzielają zmianę schematu
i danych, aby indeks FK powstał przed kopiowaniem rekordów w PostgreSQL.
Druga tworzy niezależne kopie używanych starszych tagów w przestrzeniach zadań,
przenosi przypisania, kopiuje notatki z autorami/datami i powiązane tagi.
Oryginały i historyczne relacje Kanbana/Dokumentów pozostają zachowane.
Tagi bez przestrzeni pozostają wyłącznie danymi historycznymi. Globalny
katalog i jego akcje zwracają 404; nie mają pozycji menu, Favorites ani
wyników wyszukiwania. Formularze zadań bez przestrzeni mają pusty wybór tagów. Migracja odwrotna łączy tagi o tej samej nazwie w starszym
katalogu i zachowuje przypisania oraz notatki; przed wdrożeniem wykonaj backup.
Pole „Zakres” nadal jest klasyfikacją, a tekst reguł nie uruchamia automatyzacji.

## Uprawnienia i konfiguracje

Zakres pochodzi z `workspace_owner(request)` i `request.workplace`.
`spaces.access.visible_to` i `editable_to` wyznaczają dostęp do przestrzeni,
zadania oraz całego drzewa rodziców. Prywatne zadanie dodatkowo zawęża
dostęp do wybranych osób. Obserwatorzy zachowują tylko odczyt. Listy, liczniki i raporty liczą tylko
zadania dostępne osobie oglądającej ekran. Przydział zespołu lub wykonawcy
ani powiązanie zespołu z przestrzenią nie nadają dodatkowego dostępu.

Prywatną przestrzenią zarządza jej właściciel i administratorzy przestrzeni;
wyłącznie właściciel zmienia widoczność i role administratorów. Przestrzenią
publiczną zarządza właściciel/administrator Workspace lub osoba odpowiedzialna.
Udostępnianie przestrzeni działa od razu przez `SpaceMembership`,
bez zaproszeń. Role Workspace pozostają niezależne.
Prywatnym zadaniem zarządza jego właściciel lub administrator zadania;
tylko właściciel zmienia widoczność i role administratorów. Kandydaci muszą
mieć bieżący dostęp do przestrzeni i wszystkich rodziców. Zmiana zadania
na dziedziczące dostęp przestrzeni czyści jego członkostwa, zachowując
niezależne prywatne podzadania. Usunięcie lub dezaktywacja członka Workspace,
odebranie dostępu do prywatnej przestrzeni albo rodzica usuwa odpowiednie
udostępnienia zadań. Ponowne dołączenie ich nie przywraca. Operacje przez
`QuerySet.update()` wymagają jawnego czyszczenia, ponieważ pomijają sygnały.

Zarządzanie przez zespół oznacza niezależną konfigurację przestrzeni.
Zarządzanie przez organizację pozwala administratorowi Workspace utworzyć lub
wybrać `SpaceConfiguration.shared`. Zmiana wspólnej konfiguracji obejmuje
wszystkie powiązane przestrzenie; edycja wymaga uprawnień administratora
Workspace. Formularz chroni przed zapisem nieaktualnej wersji. Nie można usunąć
używanego statusu/typu lub zmienić kategorii statusu z zadaniami.

Zespół może utworzyć aktywny członek Workspace; staje się jego administratorem.
Członków wybiera się tylko z aktywnych osób Workspace. Zwykły członek zespołu
nie edytuje profilu ani członkostw. Usunięcie/wyłączenie członkostwa Workspace
usuwa członkostwa zespołów; ich przywrócenie wymaga ponownego dodania.
Formularz nie pozwala odebrać ostatniej aktywnej roli administratora zespołu.

## Oddzielenie od starszych Zadań (10.10.2026)

Migracja `spaces.0006_independent_space_tasks` kopiuje dane i ulubione
przestrzeni oraz zadania z ich autorami, datami, komentarzami, historią,
tagami, plikami i dziennikiem pracy. Zachowuje PK importowanych zadań,
klucze, liczniki, awatary, konfiguracje i planowanie `WorkItem`.
Prywatność dawnych grup i rodziców składa w przecięcie dostępu do zadania;
przydział wykonawcy nie rozszerza tego dostępu.

`tasks.0066_task_space_archived_taskproject_space_archived` oraz
`spaces.0007_archive_import_sources` oznaczają źródła jako archiwalne.
Starsze systemy projektów, grup i zadań są w całości wycofane, również dla
rekordów bez importu i po usunięciu nowego zadania lub przestrzeni.
[Kontrakt zgodności](MODULES.md#3-projekty-grupy-i-zadania--tasks). GET/HEAD starego linku szczegółów przekierowuje do nowego
adresu po bieżącej kontroli dostępu; POST tego linku zwraca 409. Pobieranie
importowanego pliku przekierowuje do chronionego endpointu przestrzeni.
Usunięcie starego źródła nie usuwa nowego zadania (`SET_NULL`).
Migracja jest jednokierunkowa; cofnięcie wdrożenia wymaga backupu bazy i storage.

Filtry („Wyszukaj zadania”), „Dla ciebie”, Dashboard, postęp pulpitów i wyszukiwanie
odczytują nowe zadania przez ich ACL. Kalendarz pokazuje również ich terminy.
Wspólne listy nie wymagają odwołania do projektu lub grupy.

## Historyczny import Kanbana (3.10.2026)

`spaces/0001_initial.py` tworzy tabele. `0002_unify_work.py` atomowo:

1. Tworzy przestrzenie dla obecnych projektów Zadań i metadane istniejących zadań.
2. Importuje projekty i grupy Kanbana do projektów/grup Zadań z prywatnością,
   właścicielami, rolami, ulubionymi i notatkami projektu.
3. Importuje karty, podkarty, statusy, terminy, czas, tagi, historię i załączniki.
   Dawna kolumna i niezależny stan karty są reprezentowane razem jako status.
4. Przenosi odwołania powiadomień, wzmianek i obserwowania do nowych rekordów.
5. Zapisuje mapowania `LegacyKanbanLink`. Oryginalne rekordy nie są kasowane.

Projekty bez Workspace pozostają wyłącznie w historycznych tabelach, bez ekranów. Nieprzypisane karty
otrzymują zadania bez przestrzeni. Dane nowego widoku weryfikuje się przez
mapowania i `Task.work_item`, nie przez obecność dawnego rekordu.

`kanban.access` wyklucza wszystkie historyczne obiekty z bieżącej aplikacji.
Stary moduł nie ma aktywnych ekranów ani operacji, także bez mapowań importu.
Katalog `/kanban/` (również scoped) przekierowuje zawsze do Przestrzeni. `LegacyKanbanMiddleware` przekierowuje stare linki szczegółów i plików
po kontroli aktualnego zakresu oraz ACL; zapisy pod zachowane adresy zgodności
zwracają 409 i adres nowego modułu, a usunięte endpointy operacji — 404. Mapowania przetrwają usunięcie przestrzeni,
aby archiwalne dane nie pojawiły się ponownie.

Załączniki wskazują istniejące ścieżki; migracja nie kopiuje plików na dysku.
`backend/core/task_files.py` usuwa plik dopiero po zatwierdzeniu transakcji i zniknięciu
ostatniego odwołania w modelach Tasks, Kanbana i SpaceTaskFile. Historyczne źródło zachowuje więc plik.
Zdjęcia zespołów podlegają wspólnemu walidatorowi i prywatnemu pobieraniu.

Przed wdrożeniem zatrzymaj zapisy, wykonaj backup bazy i storage, zastosuj
`manage.py migrate`, następnie uruchom nowy kod. Lokalny backup i migrację
wykonano w ramach tej zmiany. Nie dodano zależności ani usług zewnętrznych.
Migracja odwrotna nie usuwa importowanych danych ani nie synchronizuje ich
z powrotem do Kanbana. Powrót do starej wersji wymaga odtworzenia backupu;
samo `migrate spaces zero` nie jest procedurą cofnięcia wdrożenia.

## Granice i dalszy rozwój

To wspólny model pracy inspirowany Jira, bez integracji z usługą Atlassian.
Szablon obsługowy zapewnia kolejkę i formularze, bez portalu klientów, SLA
czy obsługi poczty. Raporty pokazują aktualny postęp, bez burndown i velocity.
Automatyzacje, zależności na osi czasu oraz rozszerzone schematy uprawnień
nie są częścią tej wersji. Klucz, szablon i sposób zarządzania istniejącej
przestrzeni są zablokowane w formularzu — ich zmiana wymaga osobnej migracji
czynnych zadań. Nowe szczegóły przestrzeni obsługują pliki, komentarze,
podzadania, czas, prywatność oraz planowanie. Przypomnienia, wzmianki
powiadomień i obserwowanie starszych Tasks nie są przeniesione do nowego
systemu; sam komentarz nie wysyła powiadomienia. Historyczne wpisy tych
mechanizmów pozostają w starszych tabelach.

## Wykonana weryfikacja (3.10.2026)

- Lokalna migracja: liczba mapowań odpowiada liczbie źródłowych kart,
  źródła pozostały w bazie, a wszystkie zadania otrzymały metadane.
- Zestaw 176 testów: 175 poprawnych wyników i błąd zamykania strumienia
  w nowym teście zdjęcia. Po naprawie samego testu powtórzono testy `spaces`
  i `core.test_file_lifecycle`: 32/32 OK. Pozostałe 144 testy przeszły
  w poprzednim przebiegu. Nie uruchamiano całego repozytorium.
- Sprawdzono uprawnienia, obserwatorów, zakres Workspace, ukryte grupy,
  stare linki, pliki, migrowaną historię, trwałe klucze, dozwolone przejścia,
  operacje zbiorcze, sprinty, prywatne zdjęcia i rollback.
- Przeglądarka na izolowanej bazie: pusty katalog, Scrum i Marketing,
  zespół/powiązanie, zadanie/lista/backlog/sprint, zmiana statusu z listy
  i przeciągnięciem, zakończenie sprintu, oś czasu, zapis konfiguracji,
  zduplikowany klucz z zachowaniem formularza, Escape, ponowne wejście,
  ekran referencyjny oraz rozmiary desktopowe i 390 px.
- `manage.py check`, `makemigrations --check --dry-run`, kontrola składni JS,
  `update_code_index.py --check`, linki dokumentacji i `git diff --check`: OK.

## Weryfikacja tagów przestrzeni (9.10.2026)

Zastosowano lokalne migracje po backupie bazy. Nowe 15 testów obejmuje także
pełną migrację schematu ze starszymi przypisaniami i jej cofnięcie na PostgreSQL.
Końcowe zestawy: 63 testy nowych funkcji i powiązanych uprawnień/statusów oraz
33 testy nowych i starszych operacji tagów — oba OK (15 testów jest wspólnych).
Szerszy przebieg 208 testów miał 2 wcześniejsze błędy `dashboard_totals`,
potwierdzone na HEAD. Osobno potwierdzono wcześniejszy błąd skrótu `tasks-my`
i nieaktualną asercję koloru separatora w teście stylu. Nie uruchamiano całego repozytorium.

Playwright z zainstalowanym Chrome (plugin Browser niedostępny) na osobnej bazie
sprawdził 1440×1000 i 390×844: nową zakładkę i starszy katalog, dodanie, edycję,
usunięcie z potwierdzeniem, notatkę, duplikat nazwy, wyszukiwanie, izolowany pusty
stan, Escape, częściową nawigację i ponowne wejście. Oba starsze pickery zadań
zmieniają opcje wraz z przestrzenią; nie zarejestrowano błędów JavaScript.
Kontrole Django, zgodności migracji, składni `tasks.js`, linków dokumentacji,
indeksu kodu i `git diff --check` przeszły.

## Pełne szczegóły niezależnego zadania

`backend/spaces/task_views.py` obsługuje właściwości, podzadania, wpisy czasu,
pliki i komentarze, a `backend/spaces/task_team.py` tabelę członków, kandydatów,
udostępnianie, zmianę roli i odbieranie dostępu. Wszystkie operacje zapisują
własne modele przestrzeni. Zakładki zachowują szkic formularza. Statusy
pochodzą z konfiguracji przestrzeni, numer to trwały klucz `WorkItem`.
Członkostwo zadania nadal zawęża dostęp przestrzeni oraz wszystkich rodziców;
rola administratora nie pozwala zmieniać widoczności prywatnego zadania
ani zarządzać innym administratorem. Usuwanie podzadań sprawdza całe drzewa.

Migracja `spaces.0008` dodaje kategorię, przypomnienie, datę członkostwa
oraz własne dostarczenia `SpaceTaskReminder`; kopiuje kategorię i przypomnienie
z historycznego źródła bez zmiany kluczy i planowania. `dashboard.0013`
rozszerza osobisty stan powiadomień o komentarze i przypomnienia przestrzeni.
`spaces.0009` zachowuje daty bezpośrednich członkostw ze źródłowego zadania.
Polling skrzynki dostarcza termin raz dla wykonawcy, a bez wykonawcy dla
właściciela zadania lub przestrzeni. Zamknięcie, zmiana terminu i cofnięcie
dostępu wycofują przypomnienie z wyników. Wzmianki są walidowane według
bieżącego dostępu do zadania i pojawiają się w istniejącej skrzynce.

## Migracja React (16.10.2026)

Katalog Przestrzeni, formularze, podsumowanie/lista/tablica/backlog/sprinty,
oś czasu/raporty/ustawienia, konfiguracja, Tagi, szczegóły zadania i Zespoły
są renderowane przez `frontend/app`.
Serializery `backend/spaces/frontend.py` i `backend/spaces/tag_frontend.py` otrzymują zakres już ograniczony przez
istniejące widoki, a API deleguje zapisy do tych samych formularzy i operacji.
Nie zmieniono modeli ani reguł ACL. Schemat, build i szczegóły cyklu życia:
[FRONTEND.md](FRONTEND.md).
