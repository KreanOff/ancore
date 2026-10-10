# Przestrzenie i zespoły

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
`dashboard.recent` i zapamiętuje oglądany projekt przed renderowaniem menu.
Puste bloki nie pokazują nagłówków. `spaces/navigation.py` za każdym razem
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
`TaskProject.favorited_by` i endpointu POST; `space-navigation.js` odświeża
bieżący ekran przez `AncoreApp`, pozostawiając jego adres. Bez JavaScriptu
formularz wraca do bezpiecznego adresu `next` z tego samego hosta. Błąd zapisu
pokazuje powiadomienie i pozwala ponowić akcję. Nie powstają nowe modele.

„Zarządzaj przestrzeniami” (`/spaces/manage/` i scoped odpowiednik) to osobny
ekran ustawień, dostępny z menu „…” przy Przestrzeniach oraz z Ustawień Ancore.
Główny pasek boczny zastępuje menu Workspace nawigacją administracyjną
z powrotem do miejsca wejścia i pozycją „Zarządzaj przestrzeniami”. Po wejściu
z Ustawień powrót prowadzi do tej samej kategorii ustawień; wejście z katalogu
zachowuje jego filtry i przewinięcie. Bez punktu wejścia link prowadzi do katalogu.
Menu dotyczy
wyłącznie przestrzeni; Workspace ma własne menu zarządzania.
Powrót przywraca zwykłe menu,
także przy częściowej nawigacji i korzystaniu z historii przeglądarki.
Ekran zawiera wyszukiwanie po nazwie/kluczu, filtry rodzaju i sposobu zarządzania
oraz paginację. Lista współdzieli `spaces/directory.html` z „Przestrzenie”:
checkboxy, menu po lewej oraz kolumny Klucz, Przestrzeń, Rodzaj, Szablon, Opis
i liczba widocznych zadań. Zachowuje te same szerokości, ikony i awatary.
Zaznaczenie dotyczy bieżącej strony, bez operacji zbiorczych.
Filtry są po lewej, wyszukiwarka i paginacja po prawej.
Nazwa prowadzi do ustawień przestrzeni; menu wiersza udostępnia otwarcie,
osobiste ulubione, edycję, ustawienia dostępu i konfigurację zadań
(jeśli osoba może ją zmieniać). Gwiazdka zachowuje adres i filtry zarządzania.

`manageable_spaces` zawęża `visible_spaces` według istniejącego `manage_space`.
Właściciel/administrator Workspace zarządza widocznymi przestrzeniami
publicznymi; osoba odpowiedzialna również może zarządzać swoim publicznym
projektem. Prywatnymi przestrzeniami zarządza ich prywatny właściciel lub
administrator projektu. Administrator Workspace nie uzyskuje dostępu do
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
Nie powstają nowe modele ani kopie przestrzeni.

## Tworzenie przestrzeni i wybór szablonu

„Utwórz przestrzeń” w katalogu, zarządzaniu oraz plus w menu bocznym otwierają
ten sam kreator. Pierwszy krok to ilustrowane kafelki wszystkich sześciu
szablonów z `spaces/defaults.py`: Kanban, Scrum, Zarządzanie zadaniami,
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
tylko aktywny Workspace, jego właściciel danych i projekty dostępne aktualnemu
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
oraz widoczność projektu. Odpowiedź ma `private, no-store` i `nosniff`.
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

Typ zgłoszenia jest zapisywany w istniejącym `WorkItem.work_type`, osobno od
biznesowej kategorii `Task.task_type`. Formularz tworzenia/edycji w przestrzeni
oraz szczegóły zadania pozwalają wybrać typ z konfiguracji tej przestrzeni.
Nowe szablony zawierają Zadanie, Błąd, Historyjkę i Epik. Marketing zachowuje
Kampanię i Materiał; Rekrutacja Kandydaturę i Rozmowę, a Obsługa zgłoszeń
Zgłoszenie i Incydent, również jako dotychczasowe wartości domyślne.
Podzadania nadal korzystają z relacji `Task.parent`; sam typ nie zmienia hierarchii.

Migracja `spaces.0004_issue_types` dopisuje brakujące cztery standardowe typy do
istniejących konfiguracji, także współdzielonych. Zachowuje własne nazwy, typy,
kolejność, statusy, pola oraz wszystkie zadania. Cofnięcie migracji pozostawia
te opcje, ponieważ zadania mogą już ich używać. Administrator nadal może
zmieniać dostępne typy przez „Statusy, typy i pola”; używanego typu nie można usunąć.

Listy, backlog i karty tablicy pokazują ikonę i nazwę typu. Filtr „Typ zgłoszenia”
na liście, tablicy, backlogu, osi czasu i we Wszystkich zadaniach działa na
serwerze przed paginacją, razem z wyszukiwaniem, wykonawcą i zespołem.
Zakres danych i dostęp do edycji pozostają wyznaczane przez Tasks oraz aktywny
Workspace. Zmiana typu zapisuje w `TaskActivity` poprzednią i nową nazwę oraz
faktycznego autora; edycja innych pól nie zeruje typu. Formularze obu modułów
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

`spaces.Space` rozszerza istniejący `tasks.TaskProject` przez OneToOne.
Nazwa, opis, prywatność i role pozostają w projekcie, dzięki czemu wcześniejsze
uprawnienia, grupy, dokumenty, komentarze i zależności zachowują działanie.
`spaces.WorkItem` zawiera wyłącznie planowanie i wskazuje przez OneToOne
kanoniczne `tasks.Task`. Lista, tablica, backlog, kalendarz i szczegóły używają
tego samego zadania. Nie ma synchronizacji dwóch edytowalnych kopii.

Punkty wejścia: `spaces/views.py`, `services.py`, `forms.py`, `teams.py`,
`signals.py`, `middleware.py`, `templates/spaces/`, `static/js/spaces.js`.
Trasy `/spaces/`, `/spaces/items/`, `/teams/` mają również warianty scoped
`/workplaces/<slug>/spaces/` i `/workplaces/<slug>/teams/`.

## Dostępne funkcje

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
  Lista zachowuje zwarte wiersze i grupy statusów Zadań, a tablica dotychczasowy
  wygląd kart Kanbana. Status zmienia się przez przeciąganie lub menu działań,
  dostępne również klawiaturą. Filtry i paginacja są w standardowym pasku Zadań.
- Podsumowanie: cztery liczniki zakończonych, zaktualizowanych i utworzonych
  zadań w ostatnich 7 dniach oraz otwartych z terminem w najbliższych 7 dniach.
  Aktualizacja wynika z historii `TaskActivity` (dowolna akcja poza utworzeniem);
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
  szczegółów przez trwały PK. Lista zachowuje filtry przy szukaniu i paginacji,
  a zakres czasu/otwartych zadań można usunąć osobnym linkiem.
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
  przejścia. Każdy status ma jeden z pięciu istniejących stanów `Task`.
  Stan `closed` nadal odpowiada za zakończenie i datę wykonania.
- Zespoły: katalog, moje zespoły, wyszukiwanie, profil, prywatnie serwowane zdjęcie,
  członkowie i administratorzy, powiązane przestrzenie i przypisane zadania.
  Zadanie może równocześnie mieć zespół oraz konkretnego wykonawcę.

„Przesuń wyżej/niżej” działa w zakresie widocznego backlogu i tej samej grupy
sprintu. Pomija zadania na tablicy Kanbana, zadania zamknięte i wykluczone przez
filtry. URL akcji oraz powrót zachowują wyszukiwanie i filtry listy. Odczyt listy
i zmiana kolejności korzystają z tych samych funkcji filtrujących.

Przeciąganie (`spaces/backlog.py`, akcja `plan` w `item_action`) waliduje
zadanie i oba sąsiednie wiersze w zakresie filtrów oraz bieżącej strony
100 wyników. Cel należy do tej samej przestrzeni; zakończone sprinty,
zamknięte zadania, elementy na tablicy Kanbana i rekordy poza widoczną stroną
są odrzucane. Kanban udostępnia wyłącznie kolejność backlogu, bez sprintów.
Serwer porównuje również przestrzeń, sprint źródłowy i zapamiętaną kolejność
zadania; stare położenie wymaga odświeżenia listy. Blokady właściciela,
Workspace, przestrzeni i rekordu oraz ponowne sprawdzenie dostępu chronią zapis.
Zmiana ustawia wyłącznie `sprint`, `in_backlog` i `rank`, bez zmiany statusu
lub daty zakończenia zadania; historia zapisuje rzeczywistego autora.
Nowa pozycja korzysta z wolnego numeru pomiędzy sąsiadami. Gdy brak miejsca
między całkowitymi numerami, rotuje dostępne numery bieżącej grupy, sprawdzając
prawo edycji każdego zmienianego rekordu. Zadania ukryte, pominięte filtrami
lub poza stroną zachowują swoje numery. Zapis jest atomowy i wymaga CSRF.

Klucz przestrzeni jest unikalny w Workspace. Zadania otrzymują trwały klucz,
np. `ANC-12`, z rosnącego licznika przestrzeni. Usunięcie zadania nie zmienia
kluczy pozostałych. Przeniesienie do innej przestrzeni zachowuje pierwotny klucz,
resetuje relacje planowania i nadaje numer w nowym zakresie. Nie należy mylić
tego klucza z PK, renumerowanym `Task.task_id` ani dawnymi kodami grup.
Szczegóły zadań używają istniejących adresów z parametrem `task_pk`.

## Tagi przestrzeni

Zakładka „Tagi” pod `/<pk>/?view=tags` (także scoped) korzysta z istniejącego
modelu `tasks.TaskTag`, tabeli, filtrów, sortowania, paginacji, modali, informacji
i notatek starszego katalogu. Każdy tag wskazuje dokładnie jedną przestrzeń;
nazwa może powtarzać się w innych przestrzeniach. Osoby z prawem edycji projektu
tworzą, edytują i usuwają tagi, także zbiorczo, oraz dodają notatki. Obserwator
ma odczyt; edycja/usunięcie notatki dodatkowo wymaga bycia jej autorem.
Liczba zadań zachowuje zasadę starszego katalogu: dostępne zadania główne,
bez podzadań i bez ujawniania prywatnych zadań.

Formularze nowego zadania i szczegółów oraz powiązania tagów ograniczają wybór
do tej samej przestrzeni i Workspace. Starsze pickery zadań przełączają listę
tagów od razu po zmianie przestrzeni; dane wyboru obejmują tylko widoczne
projekty osoby oglądającej formularz. Bezpośredni zapis obcego identyfikatora
jest odrzucany. Edycja zadania nie pozwala zmieniać jego przestrzeni ani grupy;
tagi zawsze pochodzą z zapisanej przestrzeni. Techniczna zmiana przestrzeni
zadania lub całej grupy usuwa poprzednie
przypisania tagów spoza przestrzeni docelowej. Globalne wyszukiwanie filtruje
tagi przez dostęp do projektu i kieruje do zakładki ich przestrzeni.

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
`visible_to` i `editable_to` pozostają źródłem dostępu do projektu, grupy,
zadania oraz całego drzewa rodziców. Listy, liczniki i raporty liczą tylko
zadania dostępne osobie oglądającej ekran. Przydział zespołu lub wykonawcy
ani powiązanie zespołu z przestrzenią nie nadają dodatkowego dostępu.

Prywatną przestrzenią zarządza jej właściciel i administratorzy projektu;
wyłącznie właściciel zmienia widoczność i role administratorów. Przestrzenią
publiczną zarządza właściciel/administrator Workspace lub osoba odpowiedzialna.
Udostępnianie przestrzeni działa od razu przez istniejące członkostwa projektu,
bez zaproszeń. Role Workspace pozostają niezależne.

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

## Przeniesienie danych

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
`core/task_files.py` usuwa plik dopiero po zatwierdzeniu transakcji i zniknięciu
ostatniego odwołania w obu modelach. Historyczne źródło zachowuje więc plik.
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
czynnych zadań. Starsze szczegóły zadania nadal obsługują pliki, komentarze,
czas i prywatność; planowanie oraz zespół edytuje się z nowego okna.

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
