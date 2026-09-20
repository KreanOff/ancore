# Moduły i funkcje aplikacji

Ten dokument opisuje aktywny kod lokalny. Szczegółowe modele, relacje,
formularze, endpointy i szablony są w [indeksie kodu](CODE_INDEX.md).
Zasady wspólne znajdują się w [MECHANISMS.md](MECHANISMS.md).

## 1. Konta i profil — Accounts

Źródła: [widoki](../accounts/views.py), [model](../accounts/models.py),
[formularze](../accounts/forms.py), [obecność](../accounts/presence.py).

**Funkcje:** rejestracja, logowanie przez e-mail, wylogowanie, edycja profilu,
zdjęcie z kadrowaniem/usuwaniem, publiczny identyfikator Ancore, dane kontaktowe,
status obecności i przełączanie między kontami dodanymi do jednej sesji.

`User` rozszerza `AbstractUser`. E-mail jest unikalny i służy do logowania;
`username` pozostaje osobnym publicznym identyfikatorem. Profil zawiera imiona,
nazwisko, telefon, stanowisko, opis, zdjęcie i dane obecności.

Dodanie kolejnego konta wymaga jego uwierzytelnienia. Przełącznik przechowuje
identyfikatory i hashe sesyjne wcześniej uwierzytelnionych kont. Po zmianie hasła
lub dezaktywacji konto nie może zostać wybrane; zmiana hasła wymaga ponownego
dodania z aktualnymi danymi logowania. „Usuń konto z przełącznika”
usuwa wpis z przełącznika; nie usuwa użytkownika z bazy. Nie można w ten sposób
usunąć jedynego pozostałego konta sesji.

**Scenariusz:** rejestracja → logowanie → Workspace → profil/ustawienia →
opcjonalnie dodanie drugiego konta → przełączenie. Statusy automatyczne i ręczne
obsługuje osobny mechanizm opisany w Mechanizmach.

## 2. Workspace — Workplaces

Źródła: [modele](../workplaces/models.py), [usługi](../workplaces/services.py),
[middleware](../workplaces/middleware.py), [widoki](../workplaces/views.py),
[nawigacja](../workplaces/navigation.py).

**Funkcje:** lista miejsc pracy, utworzenie, edycja, usunięcie i przełączenie;
nazwa, opis, kod, slug i obraz; ulubione miejsca w nawigacji oraz ich kolejność.
Po zalogowaniu, jeśli nie ma Workspace, usługa może utworzyć domyślne
„Moje miejsce pracy”.

`WorkplaceMembership` przechowuje role owner/admin/member, ale
`workplaces_for_user()` zwraca obecnie wyłącznie Workspace, których konto jest
właścicielem. Nie jest to aktywny system współdzielonych przestrzeni zespołowych.

`SidebarFavorite` zapisuje w bazie parę użytkownik–Workspace, klucz miejsca
nawigacji i pozycję. Katalog dozwolonych miejsc jest w
`SIDEBAR_FAVORITE_DEFINITIONS`. Zwijanie i szerokość nawigacji to lokalny stan UI.

**Scenariusz:** wybierz Workspace → otwórz moduł pod jego adresem → pracuj na
danych tego kontekstu. Zmiana Workspace zmienia kontekst list, formularzy,
tagów i wyszukiwania. Konto wykonawcy i członkostwo nie zastępują kontroli właściciela.

## 3. Projekty, grupy i zadania — Tasks

Źródła: [modele](../tasks/models.py), [formularze](../tasks/forms.py),
[główna logika](../tasks/views/tasks.py), [ustawienia pól](../tasks/views/project_settings.py).

### Ekrany

- Katalog projektów — domyślny widok modułu.
- Projekt — lista jego grup.
- Wszystkie grupy oraz widok konkretnej grupy.
- Wszystkie zadania i Moje zadania.
- Szczegóły zadania/podzadania, komentarze i historia.
- Katalog tagów oraz formularze tworzenia i edycji.

Katalogi obsługują wyszukiwanie, sortowanie, filtrowanie i paginację po stronie
serwera. UI ma wybór widocznych kolumn, zmianę szerokości/kolejności oraz akcje
zbiorcze. Zakres funkcji różni się między typami list; nie należy automatycznie
przenosić każdej funkcji jednego katalogu do wszystkich pozostałych.

### Dane

| Obiekt | Zawartość i powiązania |
| --- | --- |
| `TaskProject` | Nazwa, opis, kod, priorytet, status, etap, kondycja, początek i termin, budżet/waluta, źródło, firma, osoba odpowiedzialna, właściciel i Workspace |
| `TaskSection` | Grupa projektu: nazwa, opis, kod, rodzaj, status, właściciel grupy, priorytet, termin, zapisany limit WIP i kolejność |
| `Task` | Tytuł, opis, status, priorytet, termin i zapisane przypomnienie, estymata, czas poświęcony, typ, powód blokady, wykonawca, grupa, tagi, rodzic |
| Notatki | Osobne modele dla projektu, grupy i tagu, z autorem i czasem edycji |
| `TaskActivity` | Historia i komentarze zadania; aktor, akcja, wiadomość i metadane zmian |
| `TaskAttachment` | Plik przypisany do zadania, nazwa i rozmiar |

„Moje zadania” korzystają z przypisania, nadal wewnątrz dostępnych danych
właściciela. Przypisanie innego użytkownika nie udostępnia mu rekordu.

### Podstawowy scenariusz

1. Utwórz projekt. Aktywna akcja tworzy razem z nim początkową grupę.
2. Dodaj lub wybierz grupę i utwórz zadanie przez istniejący formularz/modal.
3. Otwórz szczegóły, zmień pola i użyj przycisku zapisu.
4. Dodaj komentarz, pliki do zadania głównego lub podzadanie.
5. Zmień status. `closed` wiąże się z zakończeniem i datą zakończenia;
   otwarcie ponownie czyści te dane.

Szczegóły zadania mają jawny zapis. Nazwa starego parametru wersji skryptu
zawierająca „autosave” nie oznacza aktywnego autozapisu.
Podzadanie dziedziczy kontekst rodzica; w obecnych widokach nie można dodawać
do niego załączników.

### Konfigurowalne pola projektu i terminy

`TaskProjectFieldOption` definiuje etykiety i kolory statusu, etapu, kondycji
i źródła w zakresie właściciela/Workspace. Źródło może też zostać wpisane ręcznie.
Zmiana nazwy źródła może aktualizować używające go projekty w tym samym zakresie.
Usunięcie używanej opcji jest blokowane. Dla statusu/etapu/kondycji trzeba
zachować co najmniej jedną aktywną opcję; źródła mogą być puste.

`TaskProjectDeadlineRule` określa kolor terminu według liczby dni. Są reguły
wspólne dla Workspace i opcjonalne reguły konkretnego projektu. Włączenie
własnych progów kopiuje reguły wspólne; reset przywraca dziedziczenie.
To osobny mechanizm od `Task.due_urgency`, który ocenia termin zadania w godzinach.

## 4. Przestrzenie, tablice i karty — Kanban

Źródła: [modele](../kanban/models.py), [formularze](../kanban/forms.py),
[widoki](../kanban/views/tasks.py), [szablony](../kanban/templates/kanban).

**Hierarchia:** `KanbanProject` (przestrzeń robocza) → `KanbanSection` (tablica)
→ `KanbanBoardColumn` → `Kanban` (karta), z opcjonalnymi podkartami.

**Funkcje:** katalog przestrzeni, katalog tablic, tablica z kolumnami,
tworzenie/edycja kart, komentarze, historia, załączniki, czas pracy,
priorytety, tagi, dodawanie/nazywanie/usuwanie i przestawianie kolumn,
przenoszenie kart między kolumnami. Ustawienia widoku obejmują m.in.
okładki i lokalnie przechowywane tapety.

Karty mają osobne statusy i relację `column`. Zmiana kolumny w obecnym kodzie
ustawia relację; nie należy utożsamiać jej ze zmianą statusu na `closed`.
Pole `is_done` na kolumnie samo nie stanowi automatyzacji zakończenia karty.
`ensure_defaults_for_section()` jest obecnie funkcją pustą.

Usunięcie kolumny przez aktywną akcję usuwa również przypisane do niej karty.
Nie można tą akcją usunąć ostatniej kolumny. To ważny kontrakt do sprawdzenia
przy każdej zmianie zarządzania tablicą.

Modele projektów Kanbana mają m.in. status, etap, kondycję i firmę, ale nie
korzystają automatycznie ze wszystkich ustawień `TaskProjectFieldOption`
i reguł terminu modułu Tasks. UI i JavaScript są częściowo wspólne, dane osobne.

## 5. Wspólne tagi

Źródła: `TaskTag`, `TaskTagNote` w [tasks/models.py](../tasks/models.py),
formularze i katalogi Tasks/Kanban oraz formularze Dysku.

Tag ma nazwę, opis, kod, kategorię, kolor, ikonę, priorytet, deklarowany zakres,
etykietę właściciela, status, powiązane tagi, notatki użycia i tekst reguł.
Ten sam model jest przypinany do zadań, kart i dokumentów.

`scope` jest zapisaną klasyfikacją; nie jest samoistnym systemem uprawnień.
`automation_rules` jest tekstem. Nie znaleziono silnika wykonującego te reguły.
Przy zmianie/usunięciu tagu sprawdź wszystkie trzy moduły i wyszukiwanie.

## 6. Kontakty, firmy i goście — Contacts

Źródła: [modele](../contacts/models.py), [widoki](../contacts/views.py),
[formularze](../contacts/forms.py).

- `Company`: firma właściciela w Workspace; dane kontaktowe, adres, notatki,
  zdjęcie, kontakty i model członkostwa.
- `Contact`: osoba lub wpis kontaktowy z danymi, firmą tekstową/opcjonalnym
  rekordem `Company`, rolą, statusem, źródłem i datą ostatniego kontaktu.
- `UserContact`: połączenie wpisu właściciela z kontem Ancore.
- `ContactActivity`: historia zmian i komentarze.

Moduł rozróżnia wpisy powiązane z kontem Ancore oraz gości bez tego powiązania.
Są formularze tworzenia kontaktu/firmy, szczegóły i edycja, wyszukiwanie,
sortowanie, paginacja i wyszukiwanie publicznego identyfikatora Ancore.
Widok katalogu użytkowników odnosi się do dodanych kontaktów, a nie pełnego
publicznego katalogu wszystkich kont.

**Scenariusz:** utwórz firmę → utwórz kontakt, opcjonalnie wskaż ID Ancore →
obejrzyj szczegóły → edytuj dane lub dopisz komentarz. Relacja z użytkownikiem
nie nadaje mu dostępu do prywatnych projektów właściciela.

Modele `SharedItem` i `SharedItemLink` nadal istnieją, lecz nie opisują
obecnie aktywnej funkcji udostępniania w interfejsie. Patrz Mechanizmy.

## 7. Kalendarz — Planner

Źródła: [widoki](../planner/views.py), [formularz](../planner/forms.py),
[szablon](../planner/templates/planner/index.html), [JS](../static/js/calendar.js).

Własny kalendarz przeglądarkowy pracuje na `CalendarEvent`: tytuł, opis,
początek, koniec, cały dzień, kolor, użytkownik i Workspace.
Ekran pozwala nawigować po datach i zmieniać widok; wydarzenia pobierane są
przez endpoint zakresu dat. Tworzenie, edycja i usuwanie używają POST.

Formularz sprawdza kolejność dat. Dla wydarzenia całodniowego normalizuje
godziny do początku i końca dnia. Parametry `date`/`event` pozwalają wejść
na wybraną datę lub wydarzenie, np. z wyszukiwarki.

To własne wydarzenia aplikacji. Kod nie potwierdza synchronizacji z Google
Calendar/Outlook ani automatycznej zamiany każdego terminu zadania w wydarzenie.

## 8. Dysk — Documents

Źródła: [modele](../documents/models.py), [widoki](../documents/views.py),
[podgląd](../documents/previews.py), [formularze](../documents/forms.py), [JS](../static/js/documents.js).

**Hierarchia:** Workspace → dyski → foldery i pliki; foldery mogą zawierać podfoldery i pliki.
Pliki mogą znajdować się także bezpośrednio w katalogu głównym dysku.

Nazwa modułu w nawigacji to „Dysk”, a jego ekran główny to „Dyski”.
Każda dotychczasowa biblioteka jest osobnym dyskiem; nazwy i zawartość istniejących
rekordów pozostają bez zmian. Formularze, filtry, komunikaty, ulubione i wyszukiwarka
używają pojęć „dysk”, „folder” i „plik”. Techniczne nazwy `documents`,
`DocumentLibrary`, `Folder`, `Document`, parametr `library` i dotychczasowe URL
pozostają kompatybilne; ta zmiana nazewnictwa nie wymaga migracji danych.

Każdy dysk, folder i plik ma właściciela oraz Workspace.
Plik ma UUID, nazwę, opis, oryginalną nazwę pliku, rozmiar, tagi,
gwiazdkę oraz datę przeniesienia do kosza.

**Ekrany i funkcje:**

- Katalog dysków z tworzeniem, zmianą nazwy/opisu i usunięciem pustego dysku.
- Własne zdjęcie dysku: dodanie, kadrowanie, podmiana i usunięcie w formularzu,
  przez wspólny edytor zdjęć Workspace. Zdjęcie zastępuje ikonę na liście i w panelu
  bocznym; bez zdjęcia dysk używa wspólnej płaskiej ikony z `drive_icon.html`.
- Zawartość dysku/folderu i ścieżka nawigacyjna.
- Przełącznik „Lista / Kafelki” na indeksie dysków i w widokach plików.
  Kafelki pokazują typ, rozmiar, datę, lokalizację i tagi pliku oraz te same
  akcje co lista; dyski pokazują zdjęcie/ikonę, nazwę i datę, bez opisu i liczników.
  Układ jest zapamiętywany w sesji oddzielnie dla konta, Workspace oraz katalogu
  dysków i plików. Zmiana układu zachowuje wyszukiwanie, filtry i stronę.
  „Nowy folder” jest bezpośrednią akcją w pasku dysku.
- Widoki całego Workspace: wszystkie, ostatnio zmienione, oznaczone i kosz.
- Listy dysków, folderów i plików pokazują „Nazwa”, „Zmodyfikowano” i „Rozmiar”.
  Lista folderów i plików ma także kolumnę „Tagi” po nazwie. Etykiety plików
  filtrują listę po kliknięciu; foldery i pliki bez tagów pokazują „—”.
  Lista folderów i plików nie powtarza pod nazwą etykiety „Folder” ani rozszerzenia
  pliku; dodatkowa linia pokazuje jedynie lokalizację, gdy jest dostępna.
  Dyski i foldery sumują rozmiary aktywnych plików także w podfolderach,
  wyłącznie w zakresie właściciela i Workspace; pliki w koszu są pomijane.
  Data folderu pozostaje datą utworzenia (model nie zapisuje modyfikacji).
  Dysk i Dokumenty rozróżniają ikoną folder bez plików oraz folder z plikami.
  Liczą się aktywne pliki także w podfolderach i dokumenty 0 B; kosz i obce dane
  są pomijane. Same puste podfoldery zachowują ikonę pustego folderu.
  Liczniki plików i folderów pozostają dostępne w filtrach/sortowaniu dysków.
- Indeks dysków ma skróty do tych widoków nad listą; lista pokazuje nazwy bez opisów.
  Panel przełączania dysków jest dostępny
  wewnątrz dysków i w widokach plików; nie powtarza listy na indeksie.
- Wyszukiwanie, sortowanie, filtr tagu i paginacja. Listy dysków i plików
  pokazują wszystkie kolumny; pasek nie zawiera przycisku „Zarządzaj tabelą”.
- Panele filtrów i sortowania zgodne z Wszystkimi projektami. Dyski można
  filtrować po nazwie, opisie, obecności plików/folderów i ostatniej zmianie;
  pliki po nazwie, oryginalnej nazwie pliku, opisie, dysku (widok Workspace),
  tagu, rozszerzeniu, rozmiarze, gwiazdce i dacie zmiany/usunięcia.
  Warunki tekstowe obsługują zawieranie, wykluczenie i pustą/niepustą wartość.
  Sortowanie ma oba kierunki dla pól tekstowych, liczników dysków, lokalizacji,
  rozmiaru i dat; dostępne pola zależą od listy.
- Upload wielu plików, pobieranie po autoryzacji, edycja metadanych,
  przenoszenie pliku między folderami tego samego dysku.
- Kliknięcie nazwy/kafelka DOCX, XLSX lub PPTX albo wyniku globalnego wyszukiwania
  otwiera pełny edytor ONLYOFFICE w osobnej karcie, tak jak w Dokumentach.
  Zapis aktualizuje ten sam plik na Dysku, bez przenoszenia do Dokumentów.
  DOC/XLS/PPT/RTF/TXT/CSV mają w podglądzie opcję utworzenia kopii OOXML
  do edycji, w tym samym dysku i folderze, z opisem oraz tagami oryginału.
  Wymagania serwera i zapis opisuje [OFFICE.md](OFFICE.md).
- Pozostałe formaty otwierają podgląd w aplikacji. PDF i obrazy (JPEG, PNG,
  GIF, WebP) używają przeglądarki; TXT pokazuje tekst, CSV tabelę, ZIP/TAR listę
  zawartości. Akcja „Edytuj dane” otwiera dotychczasowy
  formularz, a „Pobierz” nadal pobiera oryginał. Zamknięcie dialogu przywraca listę
  z jej filtrami, układem i fokusem; bezpośredni URL wraca do folderu pliku.
- Podgląd CSV nie oblicza formuł. DOC, XLS, PPT, RTF, RAR, 7Z i GZ mają
  komunikat o braku podglądu oraz pobieranie; formaty biurowe można przekonwertować,
  gdy skonfigurowany jest ONLYOFFICE.
  Duże podglądy są ograniczane z komunikatem; brakujący, uszkodzony lub
  zaszyfrowany plik ma stan zastępczy. PDF wymaga obsługi tego formatu w przeglądarce.
- Tworzenie/zmiana nazwy/usunięcie pustego folderu.
- Foldery mają gwiazdkę i pobieranie ZIP w obu układach. Oznaczone foldery
  pojawiają się obok plików w widoku „Oznaczone gwiazdką” całego Workspace
  i jego liczniku; pokazują nazwę dysku oraz prawidłowy link do zawartości.
  Filtr gwiazdki obejmuje foldery, również zagnieżdżone, i łączy się z wyborem dysku.
  Gwiazdka nie oznacza automatycznie zawartości. ZIP zachowuje aktywne pliki
  w oryginalnym formacie i strukturę podfolderów (także pustych); pomija kosz
  oraz dane innych dysków, kont i Workspace.
- Przeniesienie do kosza i przywrócenie do poprzedniej lokalizacji.

W widoku Workspace pliki mogą pochodzić z wielu dysków i zagnieżdżonych
folderów. Liczniki nawigacji są niezależne od aktualnego wyszukiwania.
Filtry łączą się ze sobą i wyszukiwaniem. Na dysku obejmują także foldery
zagnieżdżone. Filtry właściwe tylko plikom (np. tag, rozszerzenie, rozmiar)
pokazują wyłącznie pliki. Zmiana filtra lub sortowania wraca na pierwszą
stronę; paginacja, kliknięcie tagu i operacje gwiazdki/kosza zachowują warunki.
Formularze tworzenia/edycji działają jako dialog na tle listy także po otwarciu
bezpośredniego linku; specjalny nagłówek pobiera sam fragment formularza.
Wyniki wyszukiwania wskazują, że obejmują podfoldery; pusty wynik pozwala
wyczyścić wyszukiwanie i filtry. Oba układy korzystają z tej samej paginacji
i zasad dostępu. Kafelki plików pokazują ikony formatów, nie podgląd zawartości.

Upload wymaga dysku, waliduje całą partię przed zapisem i dopuszcza do
20 plików. Dostępne formaty i limity wynikają ze wspólnego walidatora.
Folder zawierający pliki, podfoldery lub pliki w koszu nie może zostać usunięty.
Dysk również musi być pusty. Kosz jest logiczny; nie ma tu endpointu
trwałego opróżniania kosza, wersjonowania ani OCR. Edytor treści znajduje się
w osobnym module Dokumenty opisanym poniżej.

### Dokumenty — osobny katalog i edytor

Źródła: [widoki](../documents/editor_views.py), [formularze](../documents/editor_forms.py),
[format treści i eksport](../documents/rich_text.py), [routing](../documents/workspace_urls.py),
[edytor JS](../static/js/office.js).

„Dokumenty” w nawigacji otwierają `/office/` albo
`/workplaces/<slug>/office/`. Moduł ma własne foldery (`WorkspaceDocumentFolder`)
i dokumenty (`WorkspaceDocument`), niezależne od Dysku. Katalog od razu
pokazuje dokumenty i foldery, bez tworzenia osobnego dysku/biblioteki.

- Cztery rodzaje nowych plików: dokument DOCX, arkusz XLSX, prezentacja PPTX
  i tablica Board. Katalog zachowuje foldery, listę/kafelki, sortowanie,
  wyszukiwanie, gwiazdki, kosz i globalne szukanie. Typ wybiera się w oknie
  „Nowy dokument”. Wspólna paginacja pozwala wyświetlić 25, 50 lub 100 pozycji.
- Foldery można oznaczać gwiazdką i pobierać jako ZIP z listy oraz kafelków.
  Widok „Oznaczone gwiazdką”, jego licznik i filtr gwiazdki obejmują również
  foldery we wszystkich poziomach Workspace. Gwiazdka folderu nie zmienia
  oznaczenia jego zawartości. ZIP zawiera aktywne dokumenty i podfoldery,
  w tym puste; pomija kosz. Starsze dokumenty Ancore eksportuje do DOCX,
  tablice do `.excalidraw`, a przesłane pliki zachowuje w oryginalnym formacie.
- Filtry i sortowanie korzystają z tych samych paneli co Dysk. Filtry obejmują
  nazwę dokumentu, oryginalną nazwę pliku, tag, typ pliku (także Dokument Ancore
  i tablicę Board), rozmiar, gwiazdkę oraz datę zmiany, a w koszu datę usunięcia.
  Warunki tekstowe obsługują zawieranie, wykluczenie i pustą/niepustą wartość.
  Łączą się ze sobą i wyszukiwaniem, obejmując wszystkie foldery Workspace.
  Warunki dotyczące wyłącznie dokumentów ukrywają foldery w wynikach.
  Sortowanie pozwala wybrać oba kierunki dla nazwy, oryginalnej nazwy pliku,
  folderu, rozmiaru, daty zmiany/usunięcia i daty dodania. Foldery są pierwsze;
  ich data odpowiada utworzeniu, a dla pól właściwych plikom są sortowane po nazwie.
  Zmiana warunków wraca na pierwszą stronę. Paginacja, zmiana lista/kafelki,
  kliknięcie tagu oraz akcje gwiazdki/kosza zachowują filtry i sortowanie.
  Czyszczenie filtrów w panelu zachowuje bieżący folder, układ i widok.
- Wspólne tagi `TaskTag` można przypisywać w edycji danych dokumentu (także
  tablicy) oraz w starszym edytorze tekstu. Lista ma kolumnę „Tagi” po nazwie,
  a kafelki pokazują te same etykiety. Kliknięcie tagu filtruje dokumenty
  we wszystkich folderach bieżącego Workspace; wyszukiwanie uwzględnia nazwy tagów.
  Wybór i filtrowanie tagów są ograniczone do właściciela oraz Workspace.
- DOCX/XLSX/PPTX otwierają się w pełnych edytorach ONLYOFFICE w osobnej karcie
  Ancore, na pełną szerokość bez menu bocznego; katalog zostaje w pierwotnej karcie.
  Edytory zapisują pliki w prywatnym storage. DOC/XLS/PPT/RTF/TXT/CSV mogą utworzyć osobną
  kopię OOXML do edycji. PDF ma dotychczasowy podgląd i pobieranie.
- Tablica Excalidraw obsługuje rysowanie, tekst, kształty, strzałki, obrazy,
  automatyczny zapis, import i eksport sceny oraz eksport PNG/SVG.
- Upload: do 20 plików, domyślnie 10 MiB na plik. Nazwę/folder można zmieniać,
  a przesłany plik podmienić. Pliki w koszu wymagają przywrócenia przed otwarciem.
- Starsze tekstowe dokumenty Ancore zachowują dotychczasowy edytor, eksport DOCX,
  konflikt rewizji i możliwość utworzenia kopii w pełnym edytorze.

Pełne edytory biurowe wymagają działającego, skonfigurowanego ONLYOFFICE.
Tablica działa bez niego. Interfejs i dane pozostają prywatne dla właściciela
oraz Workspace; nie dodano udostępniania, historii wersji, OCR, VBA ani edycji PDF.
Szczegółowe możliwości, zasady zapisu i uruchomienie opisuje
[Pełne edytory Dokumentów](OFFICE.md).

## 9. Start, ustawienia, wyszukiwarka i powiadomienia — Dashboard

Źródła: [widoki](../dashboard/views.py), [routing](../dashboard/urls.py).

- **Dashboard:** `/` pokazuje dane właściciela w aktywnym Workspace:
  liczbę otwartych zadań i kart Kanban, ich wysokich/pilnych priorytetów,
  zaległych zadań oraz pozycji zamkniętych w ostatnich 7 dniach.
  Przełączane listy `focus=deadlines|priority|kanban` pokazują maksymalnie
  6 pozycji. Są też rozkład statusów, 4 niezakończone/nieanulowane projekty
  Zadań z postępem oraz do 4 trwających/nadchodzących wydarzeń.
- **Ustawienia:** centrum linków do profilu, kont, Workspace, pól projektów
  i preferencji dostępnych na ekranie.
- **Globalne szukanie:** panel przeszukuje dane modułów i miejsca nawigacji.
- **Powiadomienia:** panel/strona ostatniej aktywności Zadań i Kanbana.

Podsumowanie z [overview.py](../dashboard/overview.py) liczy główne zadania
i karty, bez podzadań/podkart. Zamknięcie oznacza status `closed`; `resolved`
pozostaje otwarte. Terminy obejmują zaległości i czas do północy za 7 dni
w aktywnej strefie czasu. Licznik ostatnich zamknięć obejmuje dziś i 6 poprzednich
dni według `completion_date`. Projekty są sortowane po terminie, potem od
najnowszych; postęp liczy zamknięte zadania tego samego właściciela i Workspace.
Linki do modułów mają scoped URL, szczegóły zadań/kart używają `task_id`,
a projekty i wydarzenia PK. `/` nadal używa aktywnego kontekstu z sesji.

Szablon powiadomień to `dashboard/notifications.html`. Powiadomienia nie mają
oddzielnej tabeli dostarczenia/odczytu ani push/email w sprawdzonej implementacji.
Obejmują aktywność właściciela z różnych Workspace; link określa Workspace
konkretnego zadania lub karty, zamiast polegać na sesji.

## 10. Wspólna powłoka i narzędzia — Core / Static

[core/base.html](../core/templates/core/base.html) dostarcza nawigację,
przełącznik Workspace, ulubione, profil, obszar treści, host modali,
komunikaty, globalne wyszukiwanie, panel powiadomień i Sticker.

Sticker przechowuje tekst, pozycję, rozmiar i otwarcie w `localStorage`
przeglądarki. Nie jest zapisem w bazie ani notatką synchronizowaną między kontami.
Pozostałe lokalne preferencje UI opisuje [MECHANISMS.md](MECHANISMS.md).

## 11. Funkcje wymagające ostrożnej interpretacji

| Element w kodzie | Faktyczny zakres |
| --- | --- |
| Role członkostwa Workspace/firmy | Są w modelach; obecne widoki biznesowe opierają się na właścicielu |
| `SharedItem`, funkcje share i tokeny | Pozostałości; aktywny routing Tasks nie rejestruje endpointów linków udostępniania, helpery dostępu zwracają puste wartości |
| `reminder_at` | Termin przechowywany w zadaniu; nie znaleziono harmonogramu wysyłania przypomnień |
| `automation_rules` tagu | Tekst opisu; nie znaleziono wykonawcy reguł |
| `wip_limit` grupy | Zapisane pole; brak potwierdzenia mechanizmu blokującego przekroczenie limitu |
| `is_done` kolumny Kanban | Pole modelu; przeniesienie do kolumny nie kończy samo karty |
| `icon` projektu/grupy | Pole historyczne, nieedytowalne; pickery usunięte, nie przywracać ich przy okazji |
| „Dokumenty” | Lokalny moduł bibliotek i plików; nie integracja SharePoint/Drive |

Przed rozwinięciem tych obszarów sprawdź ich aktualne wywołania i testy.
