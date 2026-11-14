# Moduły i funkcje aplikacji

## Filtry zadań

Menu Filtry zawiera wyszukiwanie podstawowe i zaawansowane, zapisane
definicje, osobiste gwiazdki, katalog i udostępnianie wybranym osobom
lub całemu Workspace. Twórca zarządza definicją, a każdy odbiorca widzi
wyłącznie zadania dostępne dla swojego konta. Filtry obsługują bieżące
zadania Przestrzeni. [Przepływ, składnia i źródła](FILTERS.md).

## Przestrzenie i zespoły — aktualna nawigacja

Przestrzenie mają własne modele `Space`, `SpaceTask`, członkostwa, historię,
pliki i dziennik pracy. Szczegóły zadań są pod `/space/<slug>/tasks/<klucz>/`,
bez przejścia do starszych projektów, grup lub zadań. Nowe rekordy nie tworzą
rekordów w innym module. Schemat dawnych systemów został usunięty.
Szczegóły automatycznie zapisują pola i załączniki bez przeładowania;
błąd zachowuje szkic i udostępnia ponowienie. Komentarze są wysyłane osobno.
[Zasady zapisu](SPACES.md#pozostałe-funkcje).

Główne menu używa Przestrzeni, Wszystkich zadań i Zespołów. Starsze systemy
projektów, grup, zadań, ulubionych projektów i szablonów są wycofane.
Nowy przepływ pracy, katalog, kreator, sprinty i profile zespołów opisuje [SPACES.md](SPACES.md).
Zespoły mają katalog „Wszystkie / Moje / Zarządzane”, podsumowanie terminów i postępu,
filtry zadań, zarządzanie członkami i powiązania przestrzeni. Usunięcie zespołu
z potwierdzeniem nazwy zachowuje zadania i przestrzenie. [Szczegóły](SPACES.md#system-zespołów-04112026).

Backlog udostępnia indywidualne i zbiorcze planowanie, estymacje, wykonawców,
tworzenie w sekcji, edycję sprintu oraz zamknięcie z przeniesieniem pracy
do backlogu lub następnego sprintu. [Funkcje i zasady dostępu](SPACES.md#planowanie-w-backlogu).


Ten dokument opisuje aktywny kod lokalny. Szczegółowe modele, relacje,
formularze, endpointy i szablony są w [indeksie kodu](CODE_INDEX.md).
Zasady wspólne znajdują się w [MECHANISMS.md](MECHANISMS.md).

## 1. Konta i profil — Accounts

Źródła: [widoki](../backend/accounts/views.py), [model](../backend/accounts/models.py),
[formularze](../backend/accounts/forms.py), [obecność](../backend/accounts/presence.py).

**Funkcje:** rejestracja, logowanie przez e-mail, wylogowanie, edycja profilu,
30 gotowych awatarów zwierzęcych, wybór automatyczny oraz zdjęcie z kadrowaniem/usuwaniem,
osobisty baner, publiczny identyfikator Ancore, dane kontaktowe,
status obecności oraz jedno zalogowane konto w sesji przeglądarki.

Logowanie, rejestracja i profil są renderowane przez React
(`frontend/app/src/accounts/`) z jawnymi danymi `backend/accounts/frontend.py`.
Osobne API Accounts deleguje do tych samych formularzy i operacji Django;
publiczne pozostają wyłącznie logowanie i rejestracja. Po zapisie profilu lub
ponownym logowaniu pełna nawigacja aktualizuje również awatar i kontekst
wspólnej powłoki. [Kontrakt migracji](FRONTEND.md#api-i-interfejs-kont).

`User` rozszerza `AbstractUser`. E-mail jest unikalny bez względu na wielkość
liter (formularze oraz ograniczenie bazy `Lower(email)`) i służy do logowania;
`username` pozostaje osobnym publicznym identyfikatorem. Profil zawiera imiona,
nazwisko, telefon, stanowisko, opis, zdjęcie, baner i dane obecności.

`User.avatar` zapisuje wybraną ilustrację z osobnej puli `backend/accounts/avatar_presets.py`;
nie korzysta z motywów Przestrzeni i Workspace. Pusty identyfikator oznacza
stabilny wybór automatyczny według użytkownika z pierwotnych 24 ilustracji;
rozszerzenie katalogu nie zmienia wcześniejszych przypisań. Istniejące zdjęcie ma pierwszeństwo.
Zmiana na ilustrację lub wybór automatyczny usuwa powiązanie ze zdjęciem;
poprzedni plik jest sprzątany dopiero po zatwierdzeniu transakcji.
Wspólny helper `accounts.avatar.account_avatar` i include avatara udostępniają
wybór w profilu, pasku konta, zespołach, komentarzach i powiadomieniach.
Profil zapisuje wyłącznie konto aktualnie zalogowanej osoby.
Nagłówek udostępnia „Edytuj profil”, a formularz zachowuje wpisane dane
po błędzie. Jawny wybór „Aktywny” przywraca aktywność także po ręcznych
statusach „Zajęty”, „Poza biurem” i „Nie przeszkadzać”; sam heartbeat nadal
nie zastępuje ręcznych statusów.

`User.profile_banner` przechowuje osobisty obraz niezależny od awatara
i Workspace. Bez własnego pliku profil pokazuje istniejącą lokalną tapetę
`static/img/auth/wallpaper-fluent-bloom-light-4k.webp`. Można przesłać JPG,
PNG lub WebP do 5 MB albo przywrócić domyślny baner. Osobny formularz
i POST zapisują wyłącznie baner zalogowanej osoby. Podgląd 4:1 pozwala
przesuwać obraz i zmieniać powiększenie w zakresie 100–300%, również dla
wcześniej zapisanego pliku. Kadr przechowują `profile_banner_x`,
`profile_banner_y` (0–100) i `profile_banner_zoom` (1–3); zmiana samego kadru
zachowuje oryginalny plik i jego URL. Domyślna pozycja to 50/50 przy skali 1,
przywracana także przez reset. Zastąpienie lub reset sprzątają poprzedni plik po zatwierdzeniu
transakcji. Każdy upload dostaje nazwę z UUID, aby przeglądarka nie odtworzyła
starego obrazu z pamięci podręcznej. Zmiana banera nie zapisuje pozostałych
pól profilu.

Profil i Ustawienia nie zawierają listy kont sesji ani akcji „Dodaj konto”.
Zmiana tożsamości wymaga wylogowania przez POST z CSRF i ponownego logowania.
Wycofane adresy dodawania, przełączania i usuwania kont z sesji zwracają 404.
Wejście zalogowanej osoby na logowanie zachowuje obecne konto i kieruje do
jego strony startowej, a rejestracja kieruje do profilu. Middleware usuwa
stare dane przełącznika bez wylogowania. Reguła dotyczy pojedynczej sesji
przeglądarki; osobne logowania na innych urządzeniach pozostają dostępne.

Rejestracja tworzy i uwierzytelnia konto, a następnie otwiera
`/accounts/register/workspace/` z wymaganą nazwą. Dopiero potwierdzenie tworzy
Workspace i otwiera „Dla ciebie”. Rejestracja z linku zaproszenia wraca do
potwierdzenia dołączenia, bez tworzenia osobistego Workspace.

**Scenariusz:** rejestracja → nazwany Workspace lub przyjęcie zaproszenia →
„Dla ciebie” → profil i ustawienia. Statusy obecności opisują Mechanizmy.

## 2. Workspace — Workplaces

Źródła: [modele](../backend/workplaces/models.py), [usługi](../backend/workplaces/services.py),
[middleware](../backend/workplaces/middleware.py), [widoki](../backend/workplaces/views.py),
[nawigacja](../backend/workplaces/navigation.py).

**Funkcje:** katalog Workspace oraz zakładki „Główna”, „Członkowie”
i „Linki do dołączenia” w oknie edycji miejsca pracy. Członków dodaje się
ręcznie przez wybór istniejącego konta albo przez potwierdzenie linku. Utworzenie, edycja, usunięcie i przełączenie;
nazwa, opis i awatar; stały losowy kod oraz ulubione miejsca w nawigacji i ich kolejność.
Nazwy mogą się powtarzać. Kod `w_` + 26 małych liter/cyfr jest globalnie unikatowy,
nadawany automatycznie i tylko do odczytu. Jest także segmentem adresu Workspace;
zmiana nazwy nie zmienia kodu ani adresu. Dawne adresy pozostają aliasami
z tymi samymi kontrolami dostępu.

Katalog Workspace pokazuje pierwsze 20 wyników; „Pokaż więcej” rozszerza
widoczną listę lokalnie o kolejne 20. Wyszukiwanie resetuje okno. Zaznaczenie
pozostaje przy doładowaniu. Katalog nie zawiera hamburgera ani jego kolumny.
Usunięte menu było wejściem do ustawiania domyślnego Workspace; nie dodano zastępczej kontrolki. Zapisana
preferencja nadal działa: etykieta „Domyślny” wskazuje osobisty wybór, niezależny
od „Bieżącego”. Służy do ustalenia kontekstu przy braku dostępnego aktywnego
Workspace w sesji. Po zalogowaniu pojawia się ekran wyboru Workspace;
preferencja go nie pomija. Endpoint zachowuje dotychczasowe uprawnienia.
`Workplace.avatar` zapisuje identyfikator jednej z 30 ilustracji współdzielonych
z Przestrzeniami; pusta wartość oznacza wybór automatyczny według ID z pierwotnej
puli 24 motywów, zachowujący wcześniejsze przypisania.
`workplace_photo` zachowuje istniejący upload i kadrowanie własnego obrazu.
Wybór ilustracji usuwa poprzedni plik po zatwierdzeniu transakcji.
Właściciel i administrator otwierają wybór kliknięciem awatara lub „Dodaj”/„Zmień”
w formularzu tworzenia lub edycji. Wybór zatwierdzają w osobnym oknie,
a następnie zapisują Workspace. Anulowanie okna przywraca poprzedni awatar.
Zwykły członek ma podgląd. Zapis jest widoczny w katalogu i przełączniku Workspace.
Workspace powstaje po jawnym POST z nazwą i otwiera własne „Dla ciebie”.
Inicjalizacja transakcyjnie tworzy rolę właściciela oraz pulpit z jednym gadżetem;
nie kopiuje Przestrzeni, zadań ani członków innego Workspace. Nie ma workera
inicjalizacji ani osobnego serwera/bazy dla każdego Workspace.

`WorkplaceMembership` obsługuje role owner/admin/member/guest. Gość odczytuje
dostępne dane; prywatność Przestrzeni i zadań nadal obowiązuje. `disabled_modules`
przechowuje wyłączone moduły, zachowując ich dane. Ręczne dodawanie, linki,
terminy, limity i role opisuje [Praca zespołowa](TEAMWORK.md#system-workspace-25102026).

`SidebarFavorite` zapisuje w bazie parę użytkownik–Workspace, klucz miejsca
nawigacji i pozycję. Katalog dozwolonych miejsc jest w
`SIDEBAR_FAVORITE_DEFINITIONS`. Zwijanie i szerokość nawigacji to lokalny stan UI.

Wybór do zarządzania (`?workspace=<pk>`) nie zmienia aktywnego kontekstu.
Utworzenie wraca do katalogu, a zapis ustawień zachowuje wybraną przestrzeń
i wraca do katalogu.

**Scenariusz pracy:** przełącz Workspace → otwórz moduł pod jego adresem → pracuj na
danych tego kontekstu. Zmiana Workspace zmienia kontekst list, formularzy,
tagów i wyszukiwania. Samo przypisanie wykonawcy nie nadaje dostępu; wymagane jest członkostwo.

## 3. Projekty, grupy i zadania — Tasks

Dawne projekty, grupy, zadania i szablony usunięto wraz z modelami,
relacjami i migracjami. Pakiet `tasks` obsługuje wyłącznie tagi Przestrzeni
oraz wspólne szablony. `/tasks/` i scoped odpowiednik zwracają 404.
Bieżących zadań szuka się przez „Filtry → Wyszukaj zadania”.
[Nowa baza](DATABASE.md).

## 4. Wycofany moduł Tablice Kanban

Pakiet `backend/kanban`, wszystkie jego modele, migracje i trasy usunięto.
Tablice Kanban i Scrum są częścią Przestrzeni i używają `SpaceTask`/`WorkItem`.
Dawne `/kanban/`, także scoped, zwraca 404. [Przestrzenie](SPACES.md).

## 5. Tagi przestrzeni

Źródła: `TaskTag`, `TaskTagNote` w [tasks/models.py](../backend/tasks/models.py),
formularze Tasks, `backend/tasks/tagging.py` oraz zakładka przestrzeni w `backend/spaces/views.py`.

Tag ma nazwę, opis, kod, kategorię, kolor, ikonę, priorytet, deklarowany zakres,
etykietę właściciela, status, powiązane tagi, notatki użycia i tekst reguł.
Każda przestrzeń ma własny katalog `TaskTag.space`, dostępny w zakładce „Tagi”.
Formularze zadań oraz powiązanych tagów pokazują tylko jej rekordy. Globalny
katalog „Tagi” został usunięty z menu, Favorites, formularzy i wyszukiwania.
Dawny `/tasks/?view=tags` oraz jego scoped odpowiednik zwracają 404, podobnie
jak wszystkie dawne akcje tagów wysłane do katalogu Zadań lub grup.
Osobny katalog tagów Django admin jest także usunięty, a formularz zadania
w adminie nie udostępnia dawnych tagów. Rekordy bez przestrzeni i ich notatki
pozostają wyłącznie historyczne; nie można ich wybierać także w zadaniach
bez przestrzeni ani automatycznie przypisywać do Workspace przy wejściu.
Dostęp i edycja dziedziczą uprawnienia projektu przestrzeni. Globalne wyszukiwanie
respektuje prywatność i otwiera właściwą zakładkę przestrzeni. Dysk i Dokumenty nie obsługują tagów;
ich dawne relacje pozostają wyłącznie jako dane historyczne.

`scope` jest zapisaną klasyfikacją; nie jest samoistnym systemem uprawnień.
`automation_rules` jest tekstem. Nie znaleziono silnika wykonującego te reguły.
Przy zmianie/usunięciu tagu sprawdź zadania Przestrzeni, wyszukiwanie i historyczne
powiązania w Dysku oraz Dokumentach.

## 6. Wycofane katalogi Kontaktów, Firm, Użytkowników i Gości

Pakiety Kontaktów i `legacy` usunięto całkowicie, łącznie z ich modelami,
relacjami firm, członkostwami i dawnym udostępnianiem. Adresy `/contacts/`
i scoped odpowiedniki zwracają 404. Konta, profile i członkostwa są obsługiwane
przez Accounts, Workplaces i Spaces. [Nowa baza](DATABASE.md).

## 7. Kalendarz — Planner

Źródła: [widoki](../backend/planner/views.py), [formularz](../backend/planner/forms.py),
[szablon](../backend/planner/templates/planner/index.html), [JS](../static/js/calendar.js).

Własny kalendarz przeglądarkowy pracuje na `CalendarEvent`: tytuł, opis,
początek, koniec, cały dzień, kolor, użytkownik i Workspace.
Ekran pozwala nawigować po datach i zmieniać widok; wydarzenia pobierane są
przez endpoint zakresu dat. Tworzenie, edycja i usuwanie używają POST.

Kolor wydarzenia można wybrać z natywnej palety lub wpisać jako `#RRGGBB`.
Formularz pokazuje podgląd, a „Domyślny” przywraca dotychczasową czerwień
`#e04f63`. Django waliduje kolor i zapisuje HEX małymi literami; wcześniej
zapisane nazwy pięciu kolorów nadal są obsługiwane bez zmiany ich wyglądu.
Własny kolor obejmuje wydarzenie w siatce miesiąca, tygodnia i dnia.

Formularz sprawdza kolejność dat. Dla wydarzenia całodniowego normalizuje
godziny do początku i końca dnia. Parametry `date`/`event` pozwalają wejść
na wybraną datę lub wydarzenie, np. z wyszukiwarki.

Kalendarz dołącza terminy otwartych zadań/podzadań `SpaceTask` z aktywnego
Workspace. Pomija dawne karty Kanbana. Pozycje pobiera bez tworzenia
`CalendarEvent`; zamknięte rekordy i rekordy bez terminu są pomijane.
Wydarzenia i zadania są wyświetlane razem, bez filtrów rodzaju i koloru.
Wyszukiwanie zawęża pozycje w wybranym okresie. Kliknięcie terminu otwiera szczegóły zadania.
Własne wydarzenia nadal otwierają modal edycji. Termin jest punktem w czasie,
nie blokiem zaplanowanej pracy. API ogranicza zakres do 370 dni. Brak
synchronizacji z Google Calendar/Outlook.

W Kalendarzu i na stronach Przestrzeni wspólny prawy panel pokazuje ten sam mini kalendarz i
„Plan na dziś”: wydarzenia Kalendarza obejmujące dzisiejszy dzień oraz otwarte
zadania Przestrzeni z dzisiejszym terminem w aktywnym Workspace, zgodnie
z dostępem użytkownika. Lista nie ogranicza się do zadań przypisanych
zalogowanej osobie. Całodzienne wydarzenia są pierwsze, a następnie pozycje
obu źródeł według czasu rozpoczęcia/terminu. Wydarzenia zachowują własny kolor
i prowadzą do okna w Kalendarzu; zadania do swoich szczegółów. „Pokaż więcej”
doładowuje wspólną listę po 20 pozycji. Zapis i usunięcie wydarzenia odświeża panel.
Wyłączenie Przestrzeni nie ukrywa wydarzeń Kalendarza.
Szczegóły zadania zachowują panel właściwości. Pełny Kalendarz używa tego samego
panelu co lista zadań; „+N więcej” w miesiącu otwiera główny widok dnia.

## 8. Dysk — Documents

Źródła: [modele](../backend/documents/models.py), [widoki](../backend/documents/views.py),
[podgląd](../backend/documents/previews.py), [formularze](../backend/documents/forms.py), [JS](../static/js/documents.js).

**Hierarchia:** Workspace → dyski → foldery i pliki; foldery mogą zawierać podfoldery i pliki.
Pliki mogą znajdować się także bezpośrednio w katalogu głównym dysku.

Katalogi, formularze i podglądy renderuje React (`src/documents/`), a
`backend/documents/frontend.py` przekazuje dane z istniejących widoków i formularzy Django.
Dotyczy to także Dokumentów, edytora tekstowego i powłoki pełnego edytora;
prywatne pliki, reguły dostępu oraz integracja ONLYOFFICE pozostają w Django.
Szczegóły kontraktu: [FRONTEND.md](FRONTEND.md).

Nazwa modułu w nawigacji to „Dysk”, a jego ekran główny to „Dyski”.
Każda dotychczasowa biblioteka jest osobnym dyskiem; nazwy i zawartość istniejących
rekordów pozostają bez zmian. Formularze, filtry, komunikaty, ulubione i wyszukiwarka
używają pojęć „dysk”, „folder” i „plik”. Techniczne nazwy `documents`,
`DocumentLibrary`, `Folder`, `Document`, parametr `library` i dotychczasowe URL
pozostają kompatybilne; ta zmiana nazewnictwa nie wymaga migracji danych.

Każdy dysk, folder i plik ma właściciela oraz Workspace.
Plik ma UUID, nazwę, opis, oryginalną nazwę pliku, rozmiar,
osobiste oznaczenia gwiazdką (`favorited_by`) oraz datę przeniesienia do kosza.
Gwiazdki plików, folderów i Dokumentów są niezależne dla każdego użytkownika,
także gościa. Katalog, filtry, liczniki i stan przycisków uwzględniają
wyłącznie oznaczenia zalogowanego konta w dostępnym Workspace.

**Ekrany i funkcje:**

- Ekran wyboru dysku z listą wyłącznie w prawym panelu. Tworzenie, zmiana nazwy,
  koloru ikony i opisu oraz usunięcie pustego dysku zachowują istniejące formularze.
- Dyski zawsze używają wspólnej płaskiej ikony z `drive_icon.html`
  w panelu bocznym, w zapisanym kolorze (domyślnie niebieskim).
  Formularze zawierają nazwę, kolor ikony i opis;
  dodawanie własnego zdjęcia jest wyłączone, a stare zdjęcia nie są wyświetlane.
- Foldery Dysku i Dokumentów mają własny kolor ikony, wybierany przy tworzeniu
  lub edycji pod przyciskiem ołówka. Domyślnie pozostają żółte; kolor obejmuje
  listę i kafelki, zarówno folder pusty, jak i z plikami. Przycisk „Domyślny”
  przywraca pierwotny kolor. Kolory są zapisywane jako walidowane `#RRGGBB`,
  w zakresie właściciela i Workspace, bez dziedziczenia przez podfoldery.
- Zawartość dysku/folderu i ścieżka nawigacyjna.
- Wspólny prawy panel modułu Dysk pokazuje listę dostępnych dysków Workspace
  na indeksie i w widokach plików/folderów. Zawiera kolory ikon, zaznaczenie
  aktywnego dysku i „Pokaż więcej” po 20 wyników; kliknięcie otwiera zawartość.
  Zwijaniem i mobilną szufladą steruje przycisk w górnym pasku aplikacji.
  Kalendarz z planem dnia pozostaje w pozostałych modułach.
- Przełącznik „Lista / Kafelki” w widokach plików.
  Kafelki pokazują typ, rozmiar, datę i lokalizację pliku oraz te same
  akcje co lista. Układ jest zapamiętywany w sesji dla konta i Workspace. Zmiana układu zachowuje wyszukiwanie, filtry i wczytany zakres.
  „Nowy folder” jest bezpośrednią akcją w pasku dysku.
- Widoki całego Workspace: wszystkie, ostatnio zmienione, oznaczone i kosz.
- Listy folderów i plików pokazują „Nazwa”, „Zmodyfikowano” i „Rozmiar”.
  Lista folderów i plików nie powtarza pod nazwą etykiety „Folder” ani rozszerzenia
  pliku; dodatkowa linia pokazuje jedynie lokalizację, gdy jest dostępna.
  Foldery sumują rozmiary aktywnych plików także w podfolderach,
  wyłącznie w zakresie właściciela i Workspace; pliki w koszu są pomijane.
  Data folderu pozostaje datą utworzenia (model nie zapisuje modyfikacji).
  Dysk rozróżnia ikoną folder bez plików oraz folder z plikami.
  Liczą się aktywne pliki także w podfolderach i dokumenty 0 B; kosz i obce dane
  są pomijane. Same puste podfoldery zachowują ikonę pustego folderu.
- Indeks „Dyski” pokazuje wskazówkę „Wybierz dysk” i przycisk otwarcia
  prawego panelu, a pusty Workspace — „Utwórz pierwszy dysk”. Nie powtarza
  centralnej tabeli/kafelków ani kontrolek filtrowania dysków.
- Zawartość dysku i zbiorcze widoki plików mają za sortowaniem przycisk
  z nazwą widoku lub otwartego dysku. Menu zachowuje skróty i liczniki
  plików całego Workspace. Lista pokazuje nazwy bez opisów.
- Wyszukiwanie, sortowanie, filtry i doładowywanie plików po 20 pozycji.
  Listy pokazują wszystkie kolumny; brak przycisku „Zarządzaj tabelą”.
  Filtry plików obejmują nazwę, nazwę oryginalną, opis, dysk (widok Workspace),
  rozszerzenie, rozmiar, gwiazdkę i datę zmiany/usunięcia. Sortowanie zachowuje
  oba kierunki dla dostępnych pól. Dawne parametry filtrów indeksu dysków
  nie zmieniają ekranu wyboru ani zakresu listy w prawym panelu.
- Upload wielu plików, pobieranie po autoryzacji i edycja metadanych.
  Pliki z komputera można upuszczać na folder,
  bieżący katalog lub link dysku w panelu bocznym. Upuszczenie w katalogu
  uruchamia przesyłanie przez wspólny modal z dotychczasową walidacją.
  Upuszczenie w już otwartym oknie przesyłania wybiera pliki do zatwierdzenia.
- Przeciąganie pojedynczych plików i folderów (z całym poddrzewem) między
  folderami i dyskami tego samego Workspace, także na linki ścieżki nadrzędnej.
  Akcja „Przenieś” otwiera równoważny wybór miejsca docelowego w modalu.
  Kosz, cykle folderów i konflikty nazw są blokowane. Zawartość kosza w przenoszonym
  folderze zachowuje relację z folderem i nowym dyskiem. Kolejność kafelków
  nadal wynika z sortowania; Dysk i Dokumenty pozostają osobnymi katalogami.
- Kliknięcie nazwy/kafelka DOCX, XLSX lub PPTX albo wyniku globalnego wyszukiwania
  otwiera pełny edytor ONLYOFFICE w osobnej karcie, tak jak w Dokumentach.
  Zapis aktualizuje ten sam plik na Dysku, bez przenoszenia do Dokumentów.
  DOC/XLS/PPT/RTF/TXT/CSV mają w podglądzie opcję utworzenia kopii OOXML
  do edycji, w tym samym dysku i folderze, z opisem oryginału.
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
  pojawiają się obok plików w osobistym widoku „Oznaczone gwiazdką” obejmującym Workspace
  i jego liczniku; pokazują nazwę dysku oraz prawidłowy link do zawartości.
  Filtr gwiazdki obejmuje foldery, również zagnieżdżone, i łączy się z wyborem dysku.
  Gwiazdka nie oznacza automatycznie zawartości. ZIP zachowuje aktywne pliki
  w oryginalnym formacie i strukturę podfolderów (także pustych); pomija kosz
  oraz dane innych dysków, kont i Workspace.
- Przeniesienie do kosza i przywrócenie do poprzedniej lokalizacji.

W widoku Workspace pliki mogą pochodzić z wielu dysków i zagnieżdżonych
folderów. Liczniki nawigacji są niezależne od aktualnego wyszukiwania.
Filtry łączą się ze sobą i wyszukiwaniem. Na dysku obejmują także foldery
zagnieżdżone. Filtry właściwe tylko plikom (np. rozszerzenie, rozmiar)
pokazują wyłącznie pliki. Zmiana filtra lub sortowania wraca do pierwszych
20 pozycji; „Pokaż więcej” i operacje gwiazdki/kosza zachowują warunki.
Formularze tworzenia/edycji działają jako dialog na tle listy także po otwarciu
bezpośredniego linku; specjalny nagłówek pobiera sam fragment formularza.
Wyniki wyszukiwania wskazują, że obejmują podfoldery; pusty wynik pozwala
wyczyścić wyszukiwanie i filtry. Oba układy korzystają z tego samego
kumulatywnego okna wyników i zasad dostępu. Kafelki plików pokazują ikony formatów, nie podgląd zawartości.

Upload wymaga dysku, waliduje całą partię przed zapisem i dopuszcza do
20 plików. Dostępne formaty i limity wynikają ze wspólnego walidatora.
Folder zawierający pliki, podfoldery lub pliki w koszu nie może zostać usunięty.
Dysk również musi być pusty. Kosz jest logiczny; nie ma tu endpointu
trwałego opróżniania kosza ani OCR. Historia wersji została wycofana zarówno
z Dysku, jak i Dokumentów: menu i endpointy historii są usunięte, a zapis
nie tworzy nowych archiwów. Dawne archiwa pozostają zachowane; szczegóły
opisuje [OFFICE.md](OFFICE.md). Pełne edytory biurowe są wspólne dla obu modułów.

### Dokumenty — osobny katalog i edytor

Źródła: [widoki](../backend/documents/editor_views.py), [formularze](../backend/documents/editor_forms.py),
[format treści i eksport](../backend/documents/rich_text.py), [routing](../backend/documents/workspace_urls.py),
[edytor JS](../static/js/office.js).

„Dokumenty” w nawigacji otwierają `/office/` albo
`/workplaces/<slug>/office/`. Moduł ma własne dokumenty (`WorkspaceDocument`),
niezależne od Dysku, i pokazuje je w jednym płaskim katalogu. Dotychczasowe
pliki ze wszystkich poziomów folderów są widoczne razem. Foldery nie występują
na liście, w kafelkach, licznikach, formularzach, sortowaniu ani wyszukiwarce.
Stare parametry `folder` są ignorowane; akcje folderów i przenoszenia zwracają 404.
Modele i zapisane relacje folderów pozostają dla zgodności ze starymi danymi,
bez kasowania plików i bez migracji. Nowe pliki, uploady i kopie powstają bez folderu.

Przeciągnięcie plików z komputera do katalogu nadal otwiera upload z walidacją
formatów i limitów Dokumentów. Przenoszenie między folderami dotyczy tylko Dysku.

- Sześć rodzajów nowych plików: dokument DOCX, arkusz XLSX, prezentacja PPTX,
  PDF, formularz PDF i tablica Board. Katalog zachowuje listę/kafelki, sortowanie,
  wyszukiwanie, gwiazdki, kosz i globalne szukanie. Nad listą, poza koszem,
  jest sześć kafelków tworzenia, które otwierają okno „Nowy dokument”
  z wybranym typem i fokusem na nazwie. Siódmy kafelek „Prześlij dokumenty”
  otwiera formularz uploadu. Górny pasek zawiera tytuł „Dokumenty”. Na pasku
  narzędzi za sortowaniem przycisk z nazwą bieżącego widoku otwiera skróty
  do wszystkich dokumentów, ostatnich zmian, gwiazdek, szablonów i kosza,
  z zachowanymi licznikami.
  Kafelki pozostają widoczne bez nagłówka i przycisku zwijania;
  wcześniej zapisany stan zwinięcia nie jest odczytywany.
  Plik powstaje w bieżącym Workspace; typ można jeszcze zmienić w formularzu.
  Wspólny przycisk „Pokaż więcej” rozszerza listę o 20 pozycji i zachowuje
  wcześniej widoczne dokumenty oraz zaznaczenie.
- Filtry i sortowanie korzystają z tych samych paneli co Dysk. Filtry obejmują
  nazwę dokumentu, oryginalną nazwę pliku, typ pliku (także Dokument Ancore
  i tablicę Board), rozmiar, gwiazdkę oraz datę zmiany, a w koszu datę usunięcia.
  Warunki tekstowe obsługują zawieranie, wykluczenie i pustą/niepustą wartość.
  Łączą się ze sobą i wyszukiwaniem, obejmując dokumenty bieżącego Workspace.
  Sortowanie pozwala wybrać oba kierunki dla nazwy, oryginalnej nazwy pliku,
  rozmiaru, daty zmiany/usunięcia i daty dodania.
  Zmiana warunków wraca do pierwszych 20 wyników. Doładowywanie, zmiana lista/kafelki
  oraz akcje gwiazdki/kosza zachowują filtry i sortowanie.
  Czyszczenie filtrów w panelu zachowuje układ i widok.
- Lista pokazuje kolumny „Nazwa”, „Zmodyfikowano” i „Rozmiar”. Dysk i Dokumenty
  nie pokazują tagów w formularzach, starszym edytorze, listach ani kafelkach.
  Filtry i wyszukiwanie (także globalne) nie używają historycznych powiązań
  z tagami. Stary parametr `tag` jest ignorowany i pomijany w nawigacji;
  przesłane pole `tags` nie jest zapisywane. Kopie i szablony nie dziedziczą tagów.
  Relacje w bazie pozostają historyczne, bez zmiany tagów Zadań i Kanbana.
- DOCX/XLSX/PPTX/PDF otwierają się w pełnych edytorach ONLYOFFICE w osobnej karcie
  Ancore, na pełną szerokość bez menu bocznego; katalog zostaje w pierwotnej karcie.
  Edytory zapisują pliki w prywatnym storage. DOC/XLS/PPT/RTF/TXT/CSV mogą utworzyć osobną
  kopię OOXML do edycji. PDF obsługuje pełną edycję oraz tworzenie formularzy.
- Tablica Excalidraw obsługuje rysowanie, tekst, kształty, strzałki, obrazy,
  automatyczny zapis i Ctrl/⌘+S. Hamburger i całe menu tablicy są usunięte
  bez zastępczych przycisków importu/eksportu lub pobrania kopii. Endpoint
  zapisu zachowuje kontrolę dostępu, CSRF i rewizję. Tablica otwiera się
  w osobnej karcie bez menu bocznego, tak samo jak pliki Office: z listy,
  kafelków, wyszukiwarki, metadanych oraz po utworzeniu w modalu.
- Upload: do 20 plików, domyślnie 10 MiB na plik. Nazwę można zmieniać,
  a przesłany plik podmienić. Pliki w koszu wymagają przywrócenia przed otwarciem.
- Starsze tekstowe dokumenty Ancore zachowują dotychczasowy edytor, eksport DOCX,
  konflikt rewizji i możliwość utworzenia kopii w pełnym edytorze.

Pełne edytory biurowe wymagają działającego, skonfigurowanego ONLYOFFICE.
Tablica działa bez niego. Interfejs i dane są dostępne właścicielowi i członkom Workspace
zgodnie z [zasadami zespołu](TEAMWORK.md); nie dodano publicznych linków, OCR ani VBA.
Ekran historii wersji Dokumentów i Dysku jest usunięty. Katalog Dokumentów zachowuje widok zapisanych
szablonów, ale menu oznaczania i tworzenia kopii zostało usunięte. Menu wierszy
i kafelków Dysków/Dokumentów oraz ich kolumny nie są renderowane; nie dodano
zastępczych wejść do dawnych akcji. Backend nadal obsługuje istniejące operacje
z ich kontrolą dostępu.
Szczegółowe możliwości, zasady zapisu i uruchomienie opisuje
[Pełne edytory Dokumentów](OFFICE.md).

## 9. Start, ustawienia, wyszukiwarka i powiadomienia — Dashboard

Źródła: [widoki](../backend/dashboard/views.py), [routing](../backend/dashboard/urls.py).

- **Dla ciebie:** osobisty przegląd pod `/for-you/` i
  `/workplaces/<slug>/for-you/`, dostępny w menu nad Dashboardem, globalnym
  wyszukiwaniu i ulubionych menu. Cztery zakładki pokazują tylko 20 najnowszych
  pozycji, bez paginacji:
  „Polecane” (otwarte zadania wykonawcy, zaległe, do 7 dni lub wysoki/pilny
  priorytet), „Przypisane do mnie” (również podzadania), „Ulubione”
  (osobiste gwiazdki przestrzeni, grup i zadań), „Ostatnia praca”
  (ostatnia aktywność zalogowanej osoby), „Ostatnio oglądane” (elementy otwarte
  w sesji w ciągu ostatnich 7 dni, liczonych od bieżącej chwili). Limit czasu
  obejmuje zadania, przestrzenie i grupy przed liczeniem wyników i ograniczeniem
  okna. „Ostatnio oglądane” wczytuje 20 pozycji i udostępnia „Pokaż więcej”;
  ponowne otwarcie odświeża czas wpisu. Lista zaczyna się bezpośrednio pod zakładkami; pasek filtrów,
  wyszukiwarka i pasek opisu zakładki są usunięte. Istniejące adresy nadal
  obsługują wyszukiwanie `q` po nazwie/kluczu `WorkItem` i filtr `space`.
  „Polecane”, „Przypisane do mnie” i „Ulubione” wybierają po dacie utworzenia;
  „Ostatnia praca” — po ostatniej aktywności zalogowanej osoby. Limit 20 jest
  wspólny dla wszystkich statusów i rodzajów pozycji w zakładce. Dawny parametr
  `page` jest ignorowany w tych czterech zakładkach. Filtry działają przed limitem
  i doładowywaniem oglądanych; pozostają w adresach zakładek i rozszerzanego okna.
  Pusty wynik udostępnia „Wyczyść filtry”, zachowujące zakładkę.
  Niedostępna lub błędna przestrzeń daje pusty wynik, bez rozszerzania zakresu.
  Historia ma grupy Dzisiaj, Wczoraj, Ostatnie 7 dni i Wcześniej według lokalnej
  strefy czasu. „Ostatnio oglądane” ma tylko pierwsze trzy grupy, a „Ostatnia praca”
  zachowuje również starszą historię. Wspólna historia odwiedzin w sesji i jej
  pozostali odbiorcy nie mają tego limitu czasu. Wiersze pokazują stabilny klucz oraz własną nazwę statusu przestrzeni;
  URL zadania nadal zawiera `task_pk`.
  Cztery karty „Rekomendowane przestrzenie” pochodzą z osobistych ulubionych, odwiedzin
  przestrzeni w sesji lub własnej aktywności w dostępnych zadaniach. Ulubione
  są pierwsze, dalej decyduje ostatnie użycie. Karty pokazują awatar, nazwę i rodzaj;
  kliknięcie kafelka otwiera przestrzeń. Nie zawierają dodatkowych skrótów ani
  liczników zadań. Filtry listy nie zmieniają kart ani licznika
  wszystkich przypisanych zadań. Każda lista i licznik ponownie sprawdza dostęp
  w aktywnym Workspace; przypisanie, historia, odwiedziny i ulubione nie nadają uprawnień.
  Historyczne elementy Kanbana są pomijane także w ulubionych i historii,
  niezależnie od importu. Filtr konkretnej przestrzeni obejmuje kanoniczne Tasks.
- **Pulpit domyślny:** `/` używa aktywnego Workspace z sesji, a
  `/dashboards/default/` i scoped odpowiednik otwierają ten sam zapisany pulpit.
  Każdy użytkownik ma osobną konfigurację w każdym Workspace; właścicielem danych
  pozostaje właściciel Workspace, twórcą zalogowana osoba. Przy pierwszym wejściu
  pulpit jest prywatny i zawiera jeden „Postęp pracy”. Używa tych samych gadżetów,
  siatki 12 kolumn, konfiguracji źródła/przypisania, nazwy/opisu i dostępów co nowe
  pulpity. Zapisane zmiany pozostają po kolejnym wejściu; backend nadal
  obsługuje pusty układ, mimo usunięcia wejścia do usuwania gadżetów.
  Nie można usunąć rekordu domyślnego pulpitu. Stałe liczniki, listy terminów,
  projektów i kalendarza starego Dashboardu nie są już renderowane na stronie głównej.
- **Pulpity:** osobny katalog `/dashboards/` oraz scoped odpowiednik, dostępny
  w menu, ulubionych menu i globalnym wyszukiwaniu jako skrót modułu.
  Katalog, zarządzanie, przegląd i edytor renderuje React (`src/pulpits/`),
  a dane i zapisy obsługują istniejące widoki Django przez JSON API v1.
  Katalog pokazuje wszystkie dostępne pulpity, bez zakładek Wszystkie,
  Ulubione i Moje. Wyszukiwanie po nazwie/opisie i filtr widoczności mają
  doładowywanie po 20 pozycji. Dawny parametr `tab` jest ignorowany.
  Katalog używa tej samej
  tabeli co Przestrzenie, z lokalnym zaznaczeniem, bez hamburgera i jego kolumny.
  Każdy członek Workspace może utworzyć pulpit,
  edytować własny i oznaczać dostępny osobistą gwiazdką.
  Przegląd i edytor używają nazwy w URL, np. `/dashboards/plan-zespolu/`
  i `/dashboards/plan-zespolu/gadgets/`, także w zarządzaniu i scoped adresach.
  Segment powstaje z nazwy przy tworzeniu (dla istniejących rekordów przy migracji),
  ze spacjami jako myślnikami i polskimi znakami bez akcentów. Powtarzające się
  nazwy w jednym Workspace otrzymują `-2`, `-3`; zmiana tytułu nie zmienia
  zapisanego adresu. Stare adresy liczbowe przeglądu przekierowują po sprawdzeniu
  dostępu, a dotychczasowe endpointy liczbowe nadal obsługują formularze.
  Kopiowanie pulpitów jest usunięte z menu i backendu; dawne adresy
  `<pk>/copy/` i `manage/<pk>/copy/` zwracają 404 w zwykłym i scoped routingu.
  Menu „Pulpity” ma przycisk tworzenia, sekcje Oznaczone gwiazdką/Ostatnie,
  oraz „Więcej pulpitów” z panelem wyszukiwania po nazwie/opisie i linkiem
  „Wyświetl wszystkie pulpity” do katalogu. „Pulpit domyślny” ma stały link
  do osobistej konfiguracji; nie jest powielany w gwiazdkach ani ostatnich twórcy.
  Dostępny domyślny pulpit innej osoby można oglądać jak zwykły udostępniony pulpit,
  bez zmiany własnego domyślnego pulpitu. Ostatnie pochodzą z osobistej historii
  sesji; gwiazdki są zapisane w bazie. Menu pokazuje do 6 ulubionych
  i 6 ostatnich bez gwiazdki. Mechanizm grup pulpitów jest usunięty wraz
  z konfiguracją grup i przypisaniami; dawne zwykłe/scoped adresy zwracają 404.
  Stary parametr katalogu `group` jest ignorowany.
  Osobny ekran „Zarządzaj pulpitami” jest usunięty z menu i Ustawień Ancore.
  Stare `/dashboards/manage/` i scoped adresy kierują do zwykłego katalogu
  z zachowaniem wyszukiwania, widoczności i numeru strony. Katalog obejmuje
  wszystkie dostępne pulpity; właściciel lub administrator otwiera „Ustawienia”
  z zachowanego menu z wielokropkiem w przeglądzie lub nawigacji. Ustawienia
  są osobną stroną z sekcjami „Ustawienia” i „Udostępnienia”. Menu nie zawiera
  osobnej pozycji „Dostępy”.
  „Udostępnienia” pokazuje wspólną tabelę osób jak w Przestrzeniach, z przyciskiem
  „Udostępnij”, wyszukiwaniem osób Workspace i potwierdzanym odebraniem dostępu.
  Role to Administrator, Członek i Obserwator. Administrator zarządza ustawieniami
  oraz niższymi rolami; członek edytuje gadżety i układ, a obserwator tylko ogląda.
  Twórca pozostaje chronionym właścicielem; tylko on zmienia widoczność i usuwa Pulpit.
  „Ustawienia” zmienia nazwę, opis, ikonę, domyślny zakres danych, automatyczne
  odświeżanie i widoczność. Przy wyborze całego Workspace tabela pokazuje
  dostęp odziedziczony, a indywidualne udostępnienia są usuwane.
  Udostępnienie i odebranie zapisują się od razu, bez utraty szkicu ustawień.
  Ustawienia nie zmieniają układu. Menu przeglądu i nawigacji otwiera tę samą
  stronę. Przełączanie sekcji zachowuje szkice; zapis pozostawia stronę otwartą.
  Błędy walidacji zachowują szkic; wyjście z niezapisanymi zmianami wymaga
  potwierdzenia. Menu katalogu zostało usunięte; nazwa nadal otwiera pulpit,
  a istniejące menu z wielokropkiem w przeglądzie zachowuje usuwanie.
  Tworzenie i usunięcie wracają do katalogu z filtrami.
  Dostępne pulpity innych twórców pozostają w zwykłym katalogu, z akcjami zgodnymi z rolą.
  Widoczność: prywatny, wybrane aktywne osoby albo cały Workspace.
  Uprawnienia wynikają z roli konkretnego Pulpitu, niezależnie od roli Workspace.
  Nowy pulpit jest pusty i otrzymuje gwiazdkę twórcy; gadżety dodaje się ręcznie
  przyciskiem „Dodaj gadżet”.
  Edytor współdzieli z Podsumowaniem siatkę 12 kolumn, przeciąganie,
  zmianę szerokości/wysokości i uchwyty klawiatury. Menu pozycji/rozmiaru
  oraz wejścia do konfiguracji i usuwania gadżetu zostały usunięte bez zastępstwa.
  Przegląd pozostaje widokiem do oglądania; „Edytuj pulpit” włącza szkic
  na tej samej stronie, a „Dodaj gadżet” otwiera katalog w modalu.
  „Zapisz układ” zatwierdza razem pozycje, rozmiary i dodane karty;
  „Anuluj” odrzuca zmiany. Pusty układ pozostaje zapisany po ponownym wejściu.
  Błąd lub konflikt rewizji zachowuje szkic i umożliwia wczytanie aktualnej
  wersji po potwierdzeniu. Dostęp do edycji mają właściciel, administrator
  i członek Pulpitu; każda operacja ponownie weryfikuje rolę.
  Katalog oferuje „Postęp pracy” i wyszukiwanie. Nowa karta trafia w pierwsze
  wolne miejsce i otrzymuje dane po zapisie. Backend zachowuje formularze
  konfiguracji źródła, tytułu i filtrów, mimo usunięcia wejścia z menu gadżetu.
  Na telefonie kafelki są ułożone pionowo; istniejący uchwyt obsługuje kolejność
  strzałkami góra/dół.
  Migracja `dashboard.0008_dashboard_gadget_grid` przenosi istniejące kolumny
  bez usuwania gadżetów ani ich konfiguracji.
  Filtry obejmują przestrzeń i wykonawcę (wszyscy, oglądający, bez wykonawcy).
  Gadżet pokazuje procent zamkniętych zadań, licznik „Zamknięte: X z Y”,
  pasek postępu i pięć kategorii statusu. Liczy wszystkie dostępne zadania główne
  bez podzadań, tak jak karta Dashboardu; tylko `closed` oznacza zakończenie.
  Brak zadań daje 0% i pięć zer. Na pulpicie można dodać do 24 kart tego samego rodzaju,
  np. dla różnych przestrzeni. Starsze rodzaje zastępuje migracja `dashboard.0010`:
  jedna karta „Postęp pracy” na niepusty stary pulpit, bez dawnych filtrów i tytułów.
  Puste pulpity pozostają puste. Automatyczne odświeżanie może być wyłączone
  lub działać co 1, 5 albo 15 minut w widocznym podglądzie. Edycja, otwarte
  okno, ukryta karta i trwające żądanie wstrzymują odczyty. Nie ma zewnętrznych gadżetów;
  „Odśwież” w przeglądzie pulpitu pobiera aktualne dane. Szczegóły implementacji:
  [pulpits.py](../backend/dashboard/pulpits.py), [widoki](../backend/dashboard/pulpit_views.py)
  i [routing](../backend/dashboard/pulpit_urls.py). Inspiracja funkcjonalna:
  [pulpity Jira](https://support.atlassian.com/jira-software-cloud/docs/create-and-edit-dashboards/).

  Zakres danych pulpitu obejmuje Workspace, wybrane widoczne Przestrzenie
  albo dostępny zapisany filtr. Dziedziczą go gadżety bez własnej Przestrzeni.
  Własne źródło gadżetu zastępuje zakres, zachowując filtr przypisania.
  Odbiorca widzi wyłącznie dane dostępne dla niego. Cofnięty dostęp,
  usunięty filtr lub pusta po usunięciach lista Przestrzeni nie rozszerza
  zakresu; gadżet pokazuje niedostępne źródło. Ikona z biblioteki 3145 emoji
  Fluent Emoji 3D rozpoznaje pulpit w katalogu i menu; nagłówek strony ma sam tytuł.
  Picker ma kategorie, polskie/angielskie wyszukiwanie i ostatnie wybory.
- **Ustawienia:** centrum linków do profilu i Workspace oraz wylogowania.
  Sekcja Preferencje jest usunięta; zwijanie menu i powiadomienia są dostępne
  przez kontrolki wspólnej powłoki aplikacji.
- **Globalne szukanie:** panel przeszukuje dane modułów i miejsca nawigacji.
- **Powiadomienia:** centrum przypomnień oraz komentarzy Zadań,
  z odczytem, widokiem archiwum, zbiorczym usuwaniem, filtrami Workspace
  i doczytywaniem starszych wpisów. Menu każdej karty zostało usunięte bez
  zastępczych kontrolek odczytu, archiwizacji/przywracania i usuwania.
  Historia utworzenia i zmian obiektów nie trafia do powiadomień, także obserwujących.

Historyczny serwis `dashboard.overview` i testy jego nieużywanych agregacji usunięto.
Regresje aktywnej strony głównej zachowuje `dashboard.test_home`.
Routing strony głównej korzysta z `pulpit_views.default` oraz
[pulpits.py](../backend/dashboard/pulpits.py). Dane każdego gadżetu są ponownie filtrowane
według właściciela/Workspace i prywatności oglądającego; udostępnienie konfiguracji
pulpitu nie nadaje dostępu do jego źródeł. `/` nadal używa aktywnego kontekstu z sesji.

Centrum jest dostępne wyłącznie jako panel w powłoce aplikacji, otwierany
dzwonkiem w górnym pasku aplikacji. Pełna strona została wycofana;
zwykłe wejście na `/notifications/` przekierowuje do Dashboardu, a żądania
danych panelu i licznika nadal obsługuje ten sam endpoint. `NotificationState` zapisuje
odczyt, archiwum i usunięcie osobno dla konta. Własna aktywność jest domyślnie przeczytana.
„Oznacz wszystkie jako przeczytane” i zbiorcze usuwanie obejmują bieżący filtr
oraz starsze, jeszcze niewczytane wyniki listy. Usunięcie wymaga potwierdzenia i nie ma akcji przywracania;
historia obiektów oraz powiadomienia innych osób pozostają bez zmian.
Centrum obejmuje dostępne
Workspace; link określa przestrzeń konkretnego zadania/karty. Licznik odświeża
się co 30 sekund w widocznej karcie. Szczegóły uprawnień, doładowywania i zbiorczego
odczytu: [Mechanizmy](MECHANISMS.md#11-historia-a-powiadomienia).
Zakładki „Wzmianki” i „Obserwowane” pokazują nowe komentarze kierowane do
użytkownika przez `@Imię Nazwisko` lub osobistą subskrypcję. Ten sam wpis zachowuje
wspólny stan we wszystkich filtrach. Wyłączenie obserwowania zatrzymuje nowe
dostawy, zachowując już otrzymane.
Zakładka „Przypomnienia” pokazuje zadania z osiągniętym `reminder_at`.
Odbiorcą jest wykonawca, a gdy go brak — właściciel Workspace.
Automatyczne sprawdzanie odbywa się co 30 sekund w widocznej karcie oraz
przy powrocie do aplikacji. Przypomnienia z czasu nieobecności pojawiają się
przy kolejnym odczycie. Nie ma wysyłki push/e-mail poza aplikacją.

## 10. Wspólna powłoka i narzędzia — Core / Static

[core/base.html](../backend/core/templates/core/base.html) dostarcza nawigację,
przełącznik Workspace, ulubione, profil, obszar treści, host modali,
komunikaty, globalne wyszukiwanie, panel powiadomień i Sticker.

Sticker przechowuje tekst, pozycję, rozmiar i otwarcie w `localStorage`
przeglądarki. Nie jest zapisem w bazie ani notatką synchronizowaną między kontami.
Pozostałe lokalne preferencje UI opisuje [MECHANISMS.md](MECHANISMS.md).

## 11. Funkcje wymagające ostrożnej interpretacji

| Element w kodzie | Faktyczny zakres |
| --- | --- |
| Role Workspace / firmy | Członkostwo Workspace daje dostęp zespołowy; członkostwo firmy nadal nie nadaje dostępu do Workspace |
| `SharedItem`, funkcje share i tokeny | Pozostałości; aktywny routing Tasks nie rejestruje endpointów linków udostępniania, helpery dostępu zwracają puste wartości |
| `reminder_at` | Uruchamia osobiste przypomnienie w aplikacji podczas odpytywania powiadomień; bez push/e-mail |
| `automation_rules` tagu | Tekst opisu; nie znaleziono wykonawcy reguł |
| `wip_limit` grupy | Zapisane pole; brak potwierdzenia mechanizmu blokującego przekroczenie limitu |
| `is_done` kolumny Kanban | Pole modelu; przeniesienie do kolumny nie kończy samo karty |
| `icon` projektu/grupy | Pole historyczne, nieedytowalne; pickery usunięte, nie przywracać ich przy okazji |
| „Dokumenty” | Lokalny moduł bibliotek i plików; nie integracja SharePoint/Drive |

Przed rozwinięciem tych obszarów sprawdź ich aktualne wywołania i testy.

## 12. Zasoby — Resources

Źródła: [modele](../backend/resources/models.py), [formularz](../backend/resources/forms.py),
[widoki](../backend/resources/views.py), [API](../backend/resources/api.py),
[frontend React](../frontend/app/src/resources/App.tsx),
[powłoka](../backend/resources/templates/resources/react.html).

Katalog, karta zasobu i formularze korzystają z Reacta z TypeScriptem.
Django udostępnia JSON API v1 i odpowiada za sesję, CSRF, zakres danych,
walidację oraz historię. Budowanie: [Frontend React](FRONTEND.md).

Katalog „Zasoby” jest dostępny w menu Workspace pod `/resources/` oraz
`/workplaces/<slug>/resources/`. Przechowuje sprzęt, licencje i narzędzia:
nazwę, opcjonalny numer ewidencyjny i seryjny, status (Dostępny, W użyciu,
W serwisie, Wycofany), osobę odpowiedzialną, lokalizację, datę zakupu,
termin ważności/gwarancji, planowany zwrot i notatki. Numer ewidencyjny jest unikalny w Workspace
bez rozróżniania wielkości liter; puste numery mogą się powtarzać.
Termin ważności nie może poprzedzać daty zakupu. Planowany zwrot jest opcjonalny
i występuje wyłącznie przy statusie „W użyciu”; zapis innego statusu usuwa datę.
Ograniczenie jest również w bazie. Minione terminy i ważność do 30 dni mają
oznaczenia w tabeli i karcie. Nie zmieniają automatycznie statusu ani nie wysyłają
przypomnienia. Wycofane zasoby nie wchodzą do alertów ważności.

Lista udostępnia wyszukiwanie nazwy, numerów, lokalizacji i notatek,
łączone filtry typu, statusu, przypisania (do mnie / nieprzypisane) i terminów:
ważność po terminie, najbliższe 30 dni, oba zakresy, zwrot po terminie,
zwrot w najbliższych 7 dniach oraz brak daty ważności. Sortowanie obejmuje nazwę,
datę utworzenia, ostatnią zmianę, ważność i zwrot; brakujące daty są na końcu.
Lista wczytuje 20 pozycji; „Pokaż więcej” dodaje kolejne 20, zachowując
widoczne wiersze i zaznaczenie. Liczniki nad katalogiem dotyczą całego Workspace;
kliknięcie otwiera wskazany zakres i resetuje pozostałe filtry.
Układ listy korzysta ze wspólnej tabeli: zarządzanie kolumnami, zbiorcze
menu filtrów i checkboxy z podświetleniem zaznaczenia. Hamburger i jego kolumna
zostały usunięte bez zastępczych kontrolek. Nazwa nadal otwiera kartę zasobu,
która zachowuje przycisk edycji. Ustawienia kolumn są zapisywane lokalnie dla Zasobów;
nowa kolumna zwrotu zachowuje wcześniejsze preferencje.
Globalne wyszukiwanie ma osobną kategorię Zasoby z limitem 20 wyników i linkami
do karty. Moduł można dodać do osobistych ulubionych menu.

Karta pod `/<pk>/` ma dane, notatki ewidencyjne i historię `ResourceActivity`
doładowywaną po 20 wpisów wspólnym przyciskiem „Pokaż więcej”. Zapisuje faktycznego autora, czas, rodzaj operacji,
zmienione pola przed/po oraz opcjonalną notatkę do operacji (do 2000 znaków).
Nazwa autora pozostaje po usunięciu konta. Historia zaczyna się od wdrożenia
mechanizmu; migracja nie odtwarza wcześniejszych zdarzeń. Notatka do historii
nie nadpisuje ogólnych notatek zasobu. Nazwy i tekst są renderowane bez interpretacji HTML.

„Przekaż” wybiera aktywną osobę Workspace, ustawia „W użyciu” i opcjonalną datę
zwrotu (dzisiaj lub później). Dotyczy zasobów dostępnych lub w użyciu; pozwala
również przekazać zasób kolejnej osobie. „Przyjmij zwrot” wymaga „W użyciu”,
ustawia „Dostępny” i usuwa przypisanie oraz termin. Zmiana samego statusu
zachowuje osobę odpowiedzialną. Karta udostępnia też notatkę do historii.
Zaznaczenie obejmuje widoczne wiersze i pozwala zbiorczo przekazać, przyjąć
zwrot, zmienić status lub lokalizację. Operacja nadal obejmuje najwyżej 100
zasobów; większe zaznaczenie pokazuje komunikat i blokuje przyciski operacji. Walidacja całego zestawu,
zapis i historia są atomowe, z blokadą rekordów. Niedostępny zasób, błędny stan
lub nieaktualna wersja zatrzymuje całą operację. Dialog konfliktu pozwala odrzucić
szkic i pobrać bieżące dane. Zmiana filtra lub sortowania czyści zaznaczenie
i resetuje okno; doładowanie zachowuje zaznaczone dostępne wiersze.

„Eksport CSV” pobiera wszystkie wyniki bieżących filtrów i sortowania, niezależnie
od wczytanego zakresu. Plik ma UTF-8 z BOM, separator średnik i neutralizację komórek mogących
uruchomić formułę w arkuszu. Zachowuje ten sam zakres Workspace co katalog.

Dodawanie i edycja używają standardowego modala nad katalogiem; błędy walidacji
zachowują pola, błędy sieci pozwalają ponowić zapis. Zamknięcie niezapisanego
formularza wymaga potwierdzenia. Backend zachowuje trwałe usuwanie przez POST;
wejście do tej operacji z menu wiersza zostało usunięte.
Po zapisie/usunięciu lista zachowuje filtry, sortowanie i wczytany limit
(z ograniczeniem do liczby dostępnych wyników).

Dane należą do właściciela i aktywnego Workspace; rzeczywisty autor utworzenia
oraz ostatniej zmiany jest zapisany osobno. Formularz przypisania ogranicza
osoby do aktywnego zespołu. Gość odczytuje katalog, kartę, historię i eksport,
ale nie zapisuje zmian. Formularze interfejsu przekazują wersję `updated_at`,
chroniąc przed nadpisaniem równoczesnej zmiany. Starsze wywołania edycji bez wersji
pozostają zgodne; nowe operacje wymagają wersji wszystkich wskazanych zasobów.
Usunięcie zasobu usuwa również jego historię; wycofanie przez status zachowuje ją.
Model nie zawiera kluczy licencyjnych, załączników,
rezerwacji, amortyzacji ani automatycznego śledzenia dostępności.

## Zakres frontendu React

Zasoby, Kalendarz, Dla ciebie, centrum Ustawień, Przestrzenie z Tagami,
szczegóły ich zadań, Zespoły, Filtry, Pulpity, Dysk, Dokumenty i zarządzanie Workspace korzystają z Reacta i JSON API Django.
Pozostałe aktywne moduły nadal działają w dotychczasowej architekturze;
lista i ograniczenia migracji: [FRONTEND.md](FRONTEND.md).
