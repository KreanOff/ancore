# Przestrzenie i zespoły

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

## Model pracy

Od 3.10.2026 główna nawigacja prowadzi do katalogu Przestrzeni, Wszystkich
zadań i Zespołów. Przestrzeń organizuje pracę; zespół grupuje osoby. Workspace
pozostaje nadrzędną granicą danych i członkostwa. Kontakty i firmy zachowują
rekordy i historyczne adresy, ale nie występują w głównym menu.

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
  ulubione, prywatne i paginacja. Kolumny pokazują nazwę, klucz, rodzaj,
  szablon, opis i liczbę dostępnych zadań.
- Kreator: nazwa, klucz, opis, rodzaj, szablon, zarządzanie i widoczność.
- Rodzaje: programistyczny, biznesowy, obsługowy.
- Szablony: Kanban, Scrum, zarządzanie zadaniami, marketing, rekrutacja,
  obsługa zgłoszeń. Szablon określa początkowe statusy, typy i pola.
- Widoki przestrzeni: przegląd, lista, tablica, oś czasu, raporty i ustawienia.
  Lista zachowuje zwarte wiersze i grupy statusów Zadań, a tablica dotychczasowy
  wygląd kart Kanbana. Status zmienia się przez przeciąganie lub menu działań,
  dostępne również klawiaturą. Filtry i paginacja są w standardowym pasku Zadań.
- Scrum: backlog, epiki, punkty, planowanie i rozpoczęcie sprintu, jeden aktywny
  sprint, zakończenie z powrotem niezakończonych zadań do backlogu.
- Kanban: kolejka backlogu oddzielona od zadań na tablicy i zmiana kolejności.
- Oś czasu: paski pomiędzy początkiem i terminem; zadania bez dat są pomijane.
- Raporty: aktualne liczby statusów, zakończone i zaległe zadania oraz sprinty.
- Konfiguracja: typy, pola tekst/liczba/data, wymagane pola, statusy i dozwolone
  przejścia. Każdy status ma jeden z pięciu istniejących stanów `Task`.
  Stan `closed` nadal odpowiada za zakończenie i datę wykonania.
- Zespoły: katalog, moje zespoły, wyszukiwanie, profil, prywatnie serwowane zdjęcie,
  członkowie i administratorzy, powiązane przestrzenie i przypisane zadania.
  Zadanie może równocześnie mieć zespół oraz konkretnego wykonawcę.

Klucz przestrzeni jest unikalny w Workspace. Zadania otrzymują trwały klucz,
np. `ANC-12`, z rosnącego licznika przestrzeni. Usunięcie zadania nie zmienia
kluczy pozostałych. Przeniesienie do innej przestrzeni zachowuje pierwotny klucz,
resetuje relacje planowania i nadaje numer w nowym zakresie. Nie należy mylić
tego klucza z PK, renumerowanym `Task.task_id` ani dawnymi kodami grup.
Szczegóły zadań używają istniejących adresów z parametrem `task_pk`.

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

Projekty bez Workspace pozostają w historycznym module. Nieprzypisane karty
otrzymują zadania bez przestrzeni. Dane nowego widoku weryfikuje się przez
mapowania i `Task.work_item`, nie przez obecność dawnego rekordu.

`kanban.access` wyklucza przeniesione obiekty, co zapobiega duplikatom w innych
modułach. `LegacyKanbanMiddleware` przekierowuje stare linki szczegółów i plików
po kontroli aktualnego zakresu oraz ACL; dawne zapisy w przeniesionym Workspace
zwracają 409 i adres nowego modułu. Mapowania przetrwają usunięcie przestrzeni,
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
