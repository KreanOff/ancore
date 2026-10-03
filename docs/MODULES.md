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

`User` rozszerza `AbstractUser`. E-mail jest unikalny bez względu na wielkość
liter (formularze oraz ograniczenie bazy `Lower(email)`) i służy do logowania;
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

**Funkcje:** wspólny panel z zakładkami „Workspace” i „Zaproszenia”
(otrzymane) oraz zakładkami „Członkowie” i „Wysłane zaproszenia”
w oknie edycji miejsca pracy; utworzenie, edycja, usunięcie i przełączenie;
nazwa, opis, kod, slug i obraz; ulubione miejsca w nawigacji oraz ich kolejność.
Po zalogowaniu, jeśli nie ma Workspace, usługa może utworzyć domyślne
„Moje miejsce pracy”.

`WorkplaceMembership` udostępnia wspólny Workspace rolom owner/admin/member.
Zakładkę członków Workspace, zaproszenia w aplikacji do istniejących kont, zmiany ról oraz
odebranie dostępu opisuje [Praca zespołowa](TEAMWORK.md). Członkostwo obejmuje
wszystkie moduły danego Workspace. Dane są zapisywane z właścicielem Workspace;
autorzy komentarzy i historii pozostają faktycznymi użytkownikami.

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

Źródła: [modele](../tasks/models.py), [formularze](../tasks/forms.py),
[główna logika](../tasks/views/tasks.py), [ustawienia pól](../tasks/views/project_settings.py).

### Ekrany

- Katalog projektów — domyślny widok modułu.
- Projekt — lista jego grup.
- Grupy oraz widok konkretnej grupy.
- Zadania z zakładką „Nieprzydzielone”.
- Szczegóły zadania/podzadania, komentarze z plikami, zdjęciami i `@Imię Nazwisko` oraz historia; nagłówek nie udostępnia przycisku obserwowania.
- Obserwowanie projektu: nowe komentarze i zmiany jego zadań w filtrze „Obserwowane”.
- Katalog tagów oraz formularze tworzenia i edycji.

Katalogi obsługują wyszukiwanie, sortowanie, filtrowanie i paginację po stronie
serwera. UI ma wybór widocznych kolumn, zmianę szerokości/kolejności oraz akcje
zbiorcze. Zakres funkcji różni się między typami list; nie należy automatycznie
przenosić każdej funkcji jednego katalogu do wszystkich pozostałych.

„Projekty”, „Grupy” i „Zadania” współdzielą cztery zakładki:
„Prywatne” (domyślna, własne prywatne elementy, również udostępnione innym),
„Udostępnione” (prywatne elementy innych osób dostępne odbiorcy), „Publiczne”
(dostęp dla całego Workspace) i „Ulubione” (osobiste oznaczenia z dowolnej kategorii).
Publiczna grupa dziedziczy kategorię projektu; prywatna grupa ma własnego
właściciela i dodatkowe ograniczenia. Zakładki nie zmieniają uprawnień.
Menu wiersza pozwala dodać lub usunąć ulubiony projekt/grupę, również obserwatorowi.
Zadania mają w tym celu gwiazdkę po prawej stronie wiersza. Publiczne zadanie
dziedziczy kategorię grupy i projektu; własne prywatne zadanie ma pierwszeństwo
przed kategorią rodziców. Publiczne zadanie bez grupy trafia do „Publiczne”.
Katalog nadal zawiera zadania główne, a podzadania są dostępne w szczegółach rodzica.
Relacje `favorited_by` są osobne dla każdego konta i niezależne od skrótów sidebaru.
Odebranie dostępu ukrywa również ulubiony element. „Zadania” mają dodatkowo
zakładkę „Nieprzydzielone” po „Ulubione”, zamiast osobnej pozycji menu bocznego.
Zadania grupy oraz grupy wewnątrz konkretnego projektu zachowują listę bez zakładek.

Lista grup projektu współdzieli z „Grupy” wyszukiwanie, sortowanie,
filtry statusu, typu, odpowiedzialnego i priorytetu oraz paginację w pasku
narzędzi. Wyniki i opcje odpowiedzialnych pozostają ograniczone do otwartego
projektu w bieżącym Workspace; czyszczenie filtrów nie usuwa tego kontekstu.

Projekt można oznaczyć jako „Publiczny — cały Workspace” albo „Prywatny — wybrane osoby”.
Prywatny projekt jest początkowo dostępny tylko właścicielowi. W edycji ma
zakładki „Główna” i „Członkowie”. „Udostępnij” od razu nadaje dostęp wybranemu
aktywnemu członkowi tego Workspace, bez zaproszenia ani akceptacji.
Grupy mogą dodatkowo być prywatne, z własnymi rolami i członkami; są udostępniane tak samo.
Dostęp do grupy wymaga dostępu do projektu. Zadania dziedziczą oba ograniczenia
i mogą dodatkowo być prywatne, z polem „Widoczność” i zakładką „Członkowie”.
Udostępnienie zadania od razu nadaje dostęp, bez akceptacji; podzadania zachowują
ograniczenia rodziców. Nowe zadania domyślnie są prywatne faktycznego autora;
pełną macierz dostępu opisuje
[Praca zespołowa](TEAMWORK.md#widoczność-projektów-zadań).

### Dane

| Obiekt | Zawartość i powiązania |
| --- | --- |
| `TaskProject` | Nazwa, opis, kod, priorytet, status, etap, kondycja, początek i termin, budżet/waluta, źródło, firma, osoba odpowiedzialna, właściciel danych i Workspace, widoczność publiczna/prywatna, prywatny właściciel i wybrani członkowie Workspace z dostępem (`shared_with`) |
| `TaskProjectMembership` | Osoba z bezpośrednio nadanym dostępem do projektu z rolą administrator/członek/obserwator i datą dołączenia; relacja `shared_with` |
| `TaskProjectInvitation` | Historyczne zaproszenie; nie jest tworzone ani obsługiwane przez aktywny przepływ udostępniania |
| `TaskSection` | Grupa projektu: nazwa, opis, kod, rodzaj, status, właściciel grupy, priorytet, termin, limit WIP, kolejność oraz widoczność, prywatny właściciel i udostępnienia |
| `TaskSectionMembership` | Bezpośredni dostęp do grupy z rolą administrator/członek/obserwator; zawężony dostępem projektu |
| `TaskSectionInvitation` | Historyczne zaproszenie, bez aktywnego przepływu akceptacji |
| `Task` | Tytuł, opis, status, priorytet, termin i przypomnienie w aplikacji, estymata, czas poświęcony, typ, powód blokady, wykonawca, grupa, tagi, rodzic, widoczność, prywatny właściciel i udostępnienia |
| `TaskMembership` | Bezpośredni dostęp do prywatnego zadania z rolą administrator/członek/obserwator; zawężony całą hierarchią rodziców |
| Notatki | Osobne modele dla projektu, grupy i tagu, z autorem i czasem edycji |
| `TaskActivity` | Historia i komentarze zadania; aktor, akcja, wiadomość i metadane zmian |
| `TaskCommentImage` | Prywatne pliki i zdjęcia przypisane do konkretnego komentarza; nazwa i rozmiar |
| `TaskAttachment` | Plik przypisany do zadania, nazwa i rozmiar |
| `TaskWorkLog` | Wpis dziennika pracy: zadanie, autor, rozpoczęcie, zakończenie, opis i daty zapisu; liczba minut wynika z przedziału czasu |

Zakładka „Nieprzydzielone” (`view=unassigned-tasks`) pokazuje dostępne zadania
główne bez projektu i grupy w aktywnym Workspace, niezależnie od wykonawcy.
Przypisanie grupy usuwa zadanie z tej listy; przypisanie osoby nie zmienia jego obecności.
Modal nowego zadania domyślnie pozostawia projekt i grupę puste. Zapis bez nich
działa również w Workspace bez projektów i przekierowuje do nieprzydzielonych.
Projekt wynika z grupy, dlatego po wybraniu projektu trzeba wybrać jego grupę
albo wyczyścić oba pola. Szczegóły pozwalają edytować zadanie bez grupy i później ją przypisać.
Dawny adres `view=my-tasks` nadal pokazuje zadania przypisane zalogowanej osobie,
ale nie występuje w nowym menu.
Wykonawcy i odpowiedzialni są ograniczeni do aktywnych kont zespołu.

W katalogach „Zadania” i „Zadania nieprzydzielone” limit strony dotyczy każdego
stanu osobno: 50 oznacza do 50 nowych, realizowanych, rozwiązanych, zamkniętych
i ponownie otwartych. Wspólne strzałki przechodzą do kolejnych pozycji w każdym
stanie; liczba stron wynika z najliczniejszego stanu po filtrowaniu.
Licznik w pasku sumuje zadania z pokazanych sekcji, a licznik sekcji dotyczy jej
bieżącej strony. Wyszukiwanie i filtry obejmują cały dostępny zbiór przed podziałem
na strony; sortowanie obowiązuje wewnątrz każdego stanu. Widok pojedynczej grupy
zachowuje własne, niezależne kontrolki paginacji statusów.

### Podstawowy scenariusz

1. Utwórz projekt. Aktywna akcja tworzy razem z nim początkową grupę.
2. Dodaj lub wybierz grupę i utwórz zadanie przez istniejący formularz/modal.
3. Otwórz szczegóły, zmień pola i użyj przycisku zapisu.
4. Dodaj komentarz, pliki do zadania głównego lub podzadanie.
5. Zmień status. `closed` wiąże się z zakończeniem i datą zakończenia;
   otwarcie ponownie czyści te dane.

Szczegóły zadania mają jawny zapis. Nazwa starego parametru wersji skryptu
zawierająca „autosave” nie oznacza aktywnego autozapisu.
Główny formularz zadania nie udostępnia powodu blokady, dawnych pól czasu pracy ani szacowanego czasu, a panel boczny
nie pokazuje sekcji „Historia statusu”. Dawne wartości pozostają w modelu;
zapis zadania ich nie zmienia, także gdy stare pola zostaną przesłane w POST.
Akcja `clear_time_spent` w Zadaniach została wycofana. Historia zmian statusu
w zakładce „Historia” pozostaje dostępna. Kanban zachowuje własne kontrolki.
Podzadanie dziedziczy kontekst rodzica; w obecnych widokach nie można dodawać
do niego załączników.

Szczegóły zadania i podzadania mają drugi pasek z zakładkami „Główna”,
„Dziennik pracy” i „Historia”. Zadanie główne ma dodatkowo zakładkę „Podzadania”
po „Głównej”, z listą według statusów, licznikiem i dotychczasowymi akcjami.
Lista podzadań i jej grupy statusów pozostają rozwinięte, bez możliwości zwijania.
Jest dostępna również bez podzadań; dodanie lub błąd formularza zachowuje tę zakładkę.
„Główna” pokazuje temat, opis i komentarze w sekcji „Czat”.
Komentarz może zawierać tekst, pliki i zdjęcia albo same załączniki. „Dodaj pliki”,
wklejenie ze schowka (gdy przeglądarka udostępnia plik) i przeciągnięcie do pola
pokazują załączniki z możliwością usunięcia przed wysłaniem. Obowiązuje wspólna
lista formatów Ancore: obrazy, PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX, TXT/CSV/RTF
oraz ZIP/RAR/7Z/TAR/GZ. Limit to 10 plików łącznie, domyślnie do 10 MiB każdy.
Zdjęcia mają miniatury otwierające pełny obraz w osobnej karcie; pozostałe pliki
mają ikonę formatu, nazwę, rozmiar i pobieranie. Dotyczy też podzadań oraz czatu kart/podkart Kanbana;
załączniki wiadomości nie trafiają do ogólnych załączników zadania.
Zapis przez fetch zachowuje niezapisane pola zadania, a błąd zachowuje szkic i wybrane pliki.
„Dziennik pracy” pokazuje podsumowanie i wpisy, bez tematu i opisu zadania,
a „Historia” tylko zdarzenia, bez formularza komentarza. W dzienniku „Dodaj czas” otwiera standardowy modal:
data i godzina rozpoczęcia, data i godzina zakończenia, wymagany opis
(do 4000 znaków) oraz dwa edytowalne pola czasu poświęconego: „Godziny” i „Minuty”.
Zmiana dat oblicza godziny i minuty. Wpisanie czasu poświęconego zachowuje
zakończenie i wylicza rozpoczęcie wstecz; domyślne zakończenie to bieżąca
chwila zaokrąglona do minuty. Liczba godzin może przekraczać 24, minuty mają
zakres 0–59, łączny czas musi być dodatni. Przeliczanie działa także przez
północ i zmianę czasu letniego. Godziny interpretowane są w Europe/Warsaw,
z dokładnością do minuty. Koniec musi być późniejszy od początku.
Autor jest ustalany z zalogowanego konta, bez pola wyboru osoby.

Tabela pokazuje autora, minuty, rozpoczęcie, zakończenie i opis. Menu wiersza
pozwala edytować lub usunąć wpis z potwierdzeniem; obowiązują zwykłe prawa
edycji danych Workspace, również dla członków zespołu. Edycja zachowuje
pierwotnego autora. Suma obejmuje wszystkie wpisy tego zadania, tabela pokazuje
25 wpisów na stronę, od najpóźniejszego rozpoczęcia. Podzadania mają osobne
dzienniki; suma zadania głównego nie obejmuje wpisów podzadań.
Dodanie, edycja i usunięcie zapisują rzeczywistego wykonawcę operacji w Historii.
Wycofane pola `time_spent_hours` i `time_spent_minutes` pozostają bez zmian;
historyczne sumy nie są automatycznie zamieniane na wpisy bez dat i autora.

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

### Szablony projektów Zadań

Po zaznaczeniu jednego projektu na liście opcja „Zapisz jako szablon” w menu
„Więcej opcji” tworzy niezależny snapshot jego nazwy, opisu, grup, zadań
i podzadań. Katalog `/tasks/templates/` (także scoped)
jest dostępny z menu „Więcej opcji” katalogu projektów. Używa tabeli i pasków
katalogu projektów: wyszukiwania po nazwie szablonu, nazwie projektu i opisie,
filtra obecności opisu, sortowania po obu nazwach, opisie lub dacie utworzenia
oraz paginacji 25/50/100. Nazwa szablonu jest edytowalna niezależnie od zapisanej
nazwy projektu. Przy zapisie i migracji istniejących szablonów otrzymuje nazwę
projektu. Wybór szablonu pokazuje jego własną nazwę, a nowy projekt nadal
dostaje podpowiedź nazwy projektu ze snapshotu.
Pokazuje liczniki struktury. Menu wiersza pod trzema paskami udostępnia utworzenie
projektu, pełną edycję szablonu oraz usunięcie z potwierdzeniem.
Szablon można też wybrać w standardowym oknie „Nowy projekt”.

Katalog jest zwykłą stroną z nagłówkiem i strzałką powrotu do projektów.
Edytor jest modalem wysuwanym od dołu nad katalogiem, jak edycja projektu.
Otwarcie, zapis i zamknięcie nie zmieniają adresu katalogu. Endpoint
`/tasks/templates/<id>/edit/` (także scoped) obsługuje pobranie i zapis modala;
bezpośrednie wejście przekierowuje do katalogu. Edytor udostępnia obie nazwy i opis projektu,
zapisywane przyciskiem „Zapisz dane”, oraz dodawanie, edycję i usuwanie grup,
zadań i podzadań. Edytor otwiera akcja „Edytuj szablon” w menu wiersza.
Nazwa szablonu w tabeli jest zwykłym tekstem; jej zmiana odbywa się w edytorze.
Formularze w `tasks/project_template_forms.py` walidują pola snapshotu, nie
zapisują modeli żywych projektów. Każdy POST blokuje wiersz szablonu i zapisuje
jedną operację w transakcji. Powiązania wybiera się wyłącznie z tego szablonu;
cykle i podzadania w innej grupie są odrzucane. Przeniesienie zadania do grupy
przenosi również jego podzadania. Usunięcie grupy usuwa jej zadania, a usunięcie
zadania — jego podzadania, zawsze po potwierdzeniu. Zmiany wpływają tylko na
projekty tworzone później z szablonu, nie na źródło ani wcześniej utworzone kopie.

Kopiowane są nazwy, opisy, priorytety, rodzaje grup i zadań, kolejność grup,
limit WIP. Szacowany czas nie jest już dostępny w edytorze ani kopiowany do
nowych projektów; stare wartości w zapisanych snapshotach pozostają zachowane.
Grupy zaczynają jako otwarte, zadania jako nowe;
kopie otrzymują własne PK i numery, a historia utworzenia wskazuje faktycznego
autora. Terminy, przypomnienia, wykonawcy, odpowiedzialni grup, tagi, czas pracy,
załączniki i komentarze nie są kopiowane. Parametry nowego projektu ustala
formularz; wejście z katalogu szablonów podpowiada nazwę i opis.
Zmiana lub usunięcie oryginału nie zmienia szablonu, a usunięcie szablonu nie
usuwa projektów. Dane są ograniczone do właściciela i aktywnego Workspace.

## 4. Przestrzenie, tablice i karty — Kanban

Źródła: [modele](../kanban/models.py), [formularze](../kanban/forms.py),
[widoki](../kanban/views/tasks.py), [szablony](../kanban/templates/kanban).

**Hierarchia:** `KanbanProject` (przestrzeń robocza) → `KanbanSection` (tablica)
→ `KanbanBoardColumn` → `Kanban` (karta), z opcjonalnymi podkartami.

Menu modułu: „Przestrzenie Kanban” i „Tablice”. Domyślne wejście bez
parametrów pokazuje tablice; `view=projects` otwiera przestrzenie,
a dotychczasowy adres `view=all-tasks` nadal otwiera karty z tablic aktywnego
Workspace z wyszukiwaniem oraz filtrami stanu i priorytetu. Nie ma osobnej
pozycji „Karty” w menu ani w Ulubionych. Zmiana menu zachowuje hierarchię danych.

Oba katalogi mają zakładki „Prywatne”, „Udostępnione”, „Publiczne” i „Ulubione”.
Domyślne „Prywatne” pokazują własne prywatne elementy. „Udostępnione” obejmują
prywatne elementy innych osób, do których odbiorca ma dostęp. Publiczna tablica
prywatnej przestrzeni dziedziczy kategorię przestrzeni; „Publiczne” obejmują
wspólny dostęp aktywnego Workspace. Nowe formularze domyślnie tworzą prywatny
element, a pierwsza tablica nowej przestrzeni dziedziczy jej dostęp.
`KanbanProjectMembership` i `KanbanSectionMembership` zapewniają bezpośrednie
udostępnianie z rolami administrator/członek/obserwator, bez zaproszeń.
Szczegóły dziedziczenia, cofania dostępu i usuwania opisuje [TEAMWORK](TEAMWORK.md).
Osobiste relacje `favorited_by` przestrzeni i tablic są niezależne: oznaczenie
przestrzeni nie oznacza automatycznie jej tablic. Nie zmieniają dostępu.
Ulubione przestrzeni dodaje menu wiersza, a tablic — gwiazdka na kafelku.

Katalog tablic grupuje kafelki według przestrzeni Kanban w zwijanych sekcjach,
tak jak sekcje statusów w Zadaniach. Pokazuje wyłącznie przestrzenie mające
tablice w bieżącym wyniku. Przestrzenie sortuje alfabetycznie, tablice wewnątrz
każdej grupy według wybranego A–Z/Z–A. Filtry i wyszukiwanie poprzedzają
globalną paginację tablic; licznik nagłówka dotyczy bieżącej strony.
Kafelki mają ten sam wygląd i okładki co w widoku pojedynczej przestrzeni;
ustawienia katalogu pozwalają ukryć okładki we wszystkich grupach.

**Funkcje:** katalog przestrzeni, katalog tablic, tablica z kolumnami,
tworzenie/edycja kart, komentarze z plikami i zdjęciami (`KanbanCommentImage`) i wzmiankami, obserwowanie kart i przestrzeni, historia, załączniki, czas pracy,
priorytety, tagi, dodawanie/nazywanie/usuwanie i przestawianie kolumn,
przenoszenie kart między kolumnami. Ustawienia widoku obejmują m.in.
okładki i lokalnie przechowywane tapety.

Karty i podkarty mają opcjonalny `due_at`. Termin jest dostępny w oknie nowej
karty i szczegółach, a jego zmiana trafia do historii. Otwarte karty z terminem
są widoczne w kalendarzu. Przypomnienia dotyczą obecnie modelu `Task`.

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
formularze i katalogi Tasks/Kanban.

Tag ma nazwę, opis, kod, kategorię, kolor, ikonę, priorytet, deklarowany zakres,
etykietę właściciela, status, powiązane tagi, notatki użycia i tekst reguł.
Ten sam model jest przypinany do zadań i kart. Dysk i Dokumenty nie obsługują tagów;
ich dawne relacje pozostają wyłącznie jako dane historyczne.

`scope` jest zapisaną klasyfikacją; nie jest samoistnym systemem uprawnień.
`automation_rules` jest tekstem. Nie znaleziono silnika wykonującego te reguły.
Przy zmianie/usunięciu tagu sprawdź Zadania, Kanban, wyszukiwanie i historyczne
powiązania w Dysku oraz Dokumentach.

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
obejrzyj szczegóły → edytuj dane lub dopisz komentarz. Relacja kontaktu z użytkownikiem
nie nadaje mu dostępu; dostęp zespołowy wynika z członkostwa Workspace.

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

Kalendarz dołącza terminy otwartych zadań/podzadań oraz kart/podkart Kanban
z aktywnego Workspace. Pozycje pobiera z modeli źródłowych, bez tworzenia
`CalendarEvent`; zamknięte rekordy i rekordy bez terminu są pomijane.
Filtr rodzaju rozdziela wydarzenia, zadania i karty; wyszukiwanie i kolory
działają łącznie. Kliknięcie terminu otwiera szczegóły z trwałym `task_pk`.
Własne wydarzenia nadal otwierają modal edycji. Termin jest punktem w czasie,
nie blokiem zaplanowanej pracy. API ogranicza zakres do 370 dni. Brak
synchronizacji z Google Calendar/Outlook.

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
Plik ma UUID, nazwę, opis, oryginalną nazwę pliku, rozmiar,
gwiazdkę oraz datę przeniesienia do kosza.

**Ekrany i funkcje:**

- Katalog dysków z tworzeniem, zmianą nazwy, koloru ikony i opisu oraz usunięciem pustego dysku.
- Dyski zawsze używają wspólnej płaskiej ikony z `drive_icon.html` na liście,
  w kafelkach i panelu bocznym, w zapisanym kolorze (domyślnie niebieskim).
  Formularze zawierają nazwę, kolor ikony i opis;
  dodawanie własnego zdjęcia jest wyłączone, a stare zdjęcia nie są wyświetlane.
- Foldery Dysku i Dokumentów mają własny kolor ikony, wybierany przy tworzeniu
  lub edycji pod przyciskiem ołówka. Domyślnie pozostają żółte; kolor obejmuje
  listę i kafelki, zarówno folder pusty, jak i z plikami. Przycisk „Domyślny”
  przywraca pierwotny kolor. Kolory są zapisywane jako walidowane `#RRGGBB`,
  w zakresie właściciela i Workspace, bez dziedziczenia przez podfoldery.
- Zawartość dysku/folderu i ścieżka nawigacyjna.
- Przełącznik „Lista / Kafelki” na indeksie dysków i w widokach plików.
  Kafelki pokazują typ, rozmiar, datę i lokalizację pliku oraz te same
  akcje co lista; dyski pokazują ikonę, nazwę i datę, bez opisu i liczników.
  Układ jest zapamiętywany w sesji oddzielnie dla konta, Workspace oraz katalogu
  dysków i plików. Zmiana układu zachowuje wyszukiwanie, filtry i stronę.
  „Nowy folder” jest bezpośrednią akcją w pasku dysku.
- Widoki całego Workspace: wszystkie, ostatnio zmienione, oznaczone i kosz.
- Listy dysków, folderów i plików pokazują „Nazwa”, „Zmodyfikowano” i „Rozmiar”.
  Lista folderów i plików nie powtarza pod nazwą etykiety „Folder” ani rozszerzenia
  pliku; dodatkowa linia pokazuje jedynie lokalizację, gdy jest dostępna.
  Dyski i foldery sumują rozmiary aktywnych plików także w podfolderach,
  wyłącznie w zakresie właściciela i Workspace; pliki w koszu są pomijane.
  Data folderu pozostaje datą utworzenia (model nie zapisuje modyfikacji).
  Dysk rozróżnia ikoną folder bez plików oraz folder z plikami.
  Liczą się aktywne pliki także w podfolderach i dokumenty 0 B; kosz i obce dane
  są pomijane. Same puste podfoldery zachowują ikonę pustego folderu.
  Liczniki plików i folderów pozostają dostępne w filtrach/sortowaniu dysków.
- Indeks, zawartość dysku i zbiorcze widoki plików mają za sortowaniem przycisk
  z nazwą bieżącego widoku lub otwartego dysku. Menu zachowuje skróty i liczniki
  plików całego Workspace, przeniesione z panelu bocznego.
  Lista pokazuje nazwy bez opisów.
  Panel przełączania dysków jest dostępny
  wewnątrz dysków i w widokach plików; zawiera listę dysków i ich dodawanie,
  nie powtarza listy na indeksie.
- Wyszukiwanie, sortowanie, filtry i paginacja. Listy dysków i plików
  pokazują wszystkie kolumny; pasek nie zawiera przycisku „Zarządzaj tabelą”.
- Panele filtrów i sortowania zgodne z Wszystkimi projektami. Dyski można
  filtrować po nazwie, opisie, obecności plików/folderów i ostatniej zmianie;
  pliki po nazwie, oryginalnej nazwie pliku, opisie, dysku (widok Workspace),
  rozszerzeniu, rozmiarze, gwiazdce i dacie zmiany/usunięcia.
  Warunki tekstowe obsługują zawieranie, wykluczenie i pustą/niepustą wartość.
  Sortowanie ma oba kierunki dla pól tekstowych, liczników dysków, lokalizacji,
  rozmiaru i dat; dostępne pola zależą od listy.
- Upload wielu plików, pobieranie po autoryzacji i edycja metadanych.
  Pliki z komputera można upuszczać na kafelek/wiersz dysku, folder,
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
zagnieżdżone. Filtry właściwe tylko plikom (np. rozszerzenie, rozmiar)
pokazują wyłącznie pliki. Zmiana filtra lub sortowania wraca na pierwszą
stronę; paginacja i operacje gwiazdki/kosza zachowują warunki.
Formularze tworzenia/edycji działają jako dialog na tle listy także po otwarciu
bezpośredniego linku; specjalny nagłówek pobiera sam fragment formularza.
Wyniki wyszukiwania wskazują, że obejmują podfoldery; pusty wynik pozwala
wyczyścić wyszukiwanie i filtry. Oba układy korzystają z tej samej paginacji
i zasad dostępu. Kafelki plików pokazują ikony formatów, nie podgląd zawartości.

Upload wymaga dysku, waliduje całą partię przed zapisem i dopuszcza do
20 plików. Dostępne formaty i limity wynikają ze wspólnego walidatora.
Folder zawierający pliki, podfoldery lub pliki w koszu nie może zostać usunięty.
Dysk również musi być pusty. Kosz jest logiczny; nie ma tu endpointu
trwałego opróżniania kosza ani OCR. Historia wersji została wycofana zarówno
z Dysku, jak i Dokumentów: menu i endpointy historii są usunięte, a zapis
nie tworzy nowych archiwów. Dawne archiwa pozostają zachowane; szczegóły
opisuje [OFFICE.md](OFFICE.md). Pełne edytory biurowe są wspólne dla obu modułów.

### Dokumenty — osobny katalog i edytor

Źródła: [widoki](../documents/editor_views.py), [formularze](../documents/editor_forms.py),
[format treści i eksport](../documents/rich_text.py), [routing](../documents/workspace_urls.py),
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
  Plik powstaje w bieżącym Workspace; typ można jeszcze zmienić w formularzu. Wspólna paginacja
  pozwala wyświetlić 25, 50 lub 100 pozycji.
- Filtry i sortowanie korzystają z tych samych paneli co Dysk. Filtry obejmują
  nazwę dokumentu, oryginalną nazwę pliku, typ pliku (także Dokument Ancore
  i tablicę Board), rozmiar, gwiazdkę oraz datę zmiany, a w koszu datę usunięcia.
  Warunki tekstowe obsługują zawieranie, wykluczenie i pustą/niepustą wartość.
  Łączą się ze sobą i wyszukiwaniem, obejmując dokumenty bieżącego Workspace.
  Sortowanie pozwala wybrać oba kierunki dla nazwy, oryginalnej nazwy pliku,
  rozmiaru, daty zmiany/usunięcia i daty dodania.
  Zmiana warunków wraca na pierwszą stronę. Paginacja, zmiana lista/kafelki
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
  automatyczny zapis, import i eksport sceny oraz eksport PNG/SVG. Otwiera się
  w osobnej karcie bez menu bocznego, tak samo jak pliki Office: z listy,
  kafelków, wyszukiwarki, metadanych oraz po utworzeniu w modalu.
- Upload: do 20 plików, domyślnie 10 MiB na plik. Nazwę można zmieniać,
  a przesłany plik podmienić. Pliki w koszu wymagają przywrócenia przed otwarciem.
- Starsze tekstowe dokumenty Ancore zachowują dotychczasowy edytor, eksport DOCX,
  konflikt rewizji i możliwość utworzenia kopii w pełnym edytorze.

Pełne edytory biurowe wymagają działającego, skonfigurowanego ONLYOFFICE.
Tablica działa bez niego. Interfejs i dane są dostępne właścicielowi i członkom Workspace
zgodnie z [zasadami zespołu](TEAMWORK.md); nie dodano publicznych linków, OCR ani VBA. Dokumenty i Dysk mają
historię poprzednich plików z pobieraniem i przywracaniem. Katalog Dokumentów
obsługuje oznaczanie szablonów i tworzenie niezależnych kopii z ich menu.
Szczegółowe możliwości, zasady zapisu i uruchomienie opisuje
[Pełne edytory Dokumentów](OFFICE.md).

## 9. Start, ustawienia, wyszukiwarka i powiadomienia — Dashboard

Źródła: [widoki](../dashboard/views.py), [routing](../dashboard/urls.py).

- **Dla ciebie:** osobisty przegląd pod `/for-you/` i
  `/workplaces/<slug>/for-you/`, dostępny w menu nad Dashboardem, globalnym
  wyszukiwaniu i ulubionych menu. Zakładki mają paginację po 25 pozycji:
  „Polecane” (otwarte zadania wykonawcy, zaległe, do 7 dni lub wysoki/pilny
  priorytet), „Przypisane do mnie” (również podzadania), „Ulubione”
  (osobiste gwiazdki zadań, projektów, grup, przestrzeni Kanban i tablic),
  „Ostatnia praca” (ostatnia aktywność zalogowanej osoby w zadaniach i kartach),
  „Ostatnio oglądane” (zadania, karty, projekty, grupy i tablice otwarte w sesji).
  Cztery skróty projektów Zadań pochodzą z ulubionych lub własnej aktywności
  w dostępnych zadaniach. Każda lista ponownie sprawdza dostęp w aktywnym
  Workspace; przypisanie, historia ani ulubione nie nadają uprawnień.
  Kanban nie ma wykonawcy, a karty nie mają osobistych gwiazdek — pojawiają
  się w ostatniej pracy i oglądanych. Funkcja nie wymaga migracji.
- **Dashboard:** `/` pokazuje dane właściciela w aktywnym Workspace:
  liczbę otwartych zadań i kart Kanban, ich wysokich/pilnych priorytetów,
  zaległych zadań oraz pozycji zamkniętych w ostatnich 7 dniach.
  Przełączane listy `focus=deadlines|priority|kanban` pokazują maksymalnie
  6 pozycji. Są też rozkład statusów, 4 niezakończone/nieanulowane projekty
  Zadań z postępem oraz do 4 trwających/nadchodzących wydarzeń.
- **Ustawienia:** centrum linków do profilu, kont, Workspace, pól projektów
  i preferencji dostępnych na ekranie.
- **Globalne szukanie:** panel przeszukuje dane modułów i miejsca nawigacji.
- **Powiadomienia:** centrum zaproszeń oraz aktywności Zadań i Kanbana,
  z odczytem, archiwum, usuwaniem, filtrami Workspace i doczytywaniem starszych wpisów.

Podsumowanie z [overview.py](../dashboard/overview.py) liczy główne zadania
i karty, bez podzadań/podkart. Zamknięcie oznacza status `closed`; `resolved`
pozostaje otwarte. Terminy obejmują zaległości i czas do północy za 7 dni
w aktywnej strefie czasu. Licznik ostatnich zamknięć obejmuje dziś i 6 poprzednich
dni według `completion_date`. Projekty są sortowane po terminie, potem od
najnowszych; postęp liczy zamknięte zadania tego samego właściciela i Workspace.
Linki do modułów mają scoped URL, szczegóły zadań/kart używają `task_id`,
a projekty i wydarzenia PK. `/` nadal używa aktywnego kontekstu z sesji.

Centrum jest dostępne wyłącznie jako panel w powłoce aplikacji, otwierany
dzwonkiem lub skrótem w Ustawieniach. Pełna strona została wycofana;
zwykłe wejście na `/notifications/` przekierowuje do Dashboardu, a żądania
danych panelu i licznika nadal obsługuje ten sam endpoint. `NotificationState` zapisuje
odczyt, archiwum i usunięcie osobno dla konta. Własna aktywność jest domyślnie przeczytana.
„Oznacz wszystkie jako przeczytane” i zbiorcze usuwanie obejmują bieżący filtr
oraz starsze strony listy. Usunięcie wymaga potwierdzenia i nie ma akcji przywracania;
historia obiektów oraz powiadomienia innych osób pozostają bez zmian.
Usunięte powiadomienie o zaproszeniu nie usuwa zaproszenia z katalogu Workspace.
Zaproszenia czekają na decyzję także po odczytaniu. Centrum obejmuje dostępne
Workspace; link określa przestrzeń konkretnego zadania/karty. Licznik odświeża
się co 30 sekund w widocznej karcie. Szczegóły uprawnień, paginacji i zbiorczego
odczytu: [Mechanizmy](MECHANISMS.md#11-historia-a-powiadomienia).
Zakładki „Wzmianki” i „Obserwowane” pokazują nowe aktywności kierowane do
użytkownika przez `@Imię Nazwisko` lub osobistą subskrypcję. Ten sam wpis zachowuje
wspólny stan we wszystkich filtrach. Wyłączenie obserwowania zatrzymuje nowe
dostawy, zachowując już otrzymane.
Zakładka „Przypomnienia” pokazuje zadania z osiągniętym `reminder_at`.
Odbiorcą jest wykonawca, a gdy go brak — właściciel Workspace.
Automatyczne sprawdzanie odbywa się co 30 sekund w widocznej karcie oraz
przy powrocie do aplikacji. Przypomnienia z czasu nieobecności pojawiają się
przy kolejnym odczycie. Nie ma wysyłki push/e-mail poza aplikacją.

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

Źródła: [modele](../resources/models.py), [formularz](../resources/forms.py),
[widoki](../resources/views.py), [katalog](../resources/templates/resources/index.html).

Katalog „Zasoby” jest dostępny w menu Workspace pod `/resources/` oraz
`/workplaces/<slug>/resources/`. Przechowuje sprzęt, licencje i narzędzia:
nazwę, opcjonalny numer ewidencyjny i seryjny, status (Dostępny, W użyciu,
W serwisie, Wycofany), osobę odpowiedzialną, lokalizację, datę zakupu,
termin ważności/gwarancji i notatki. Numer ewidencyjny jest unikalny w Workspace
bez rozróżniania wielkości liter; puste numery mogą się powtarzać.
Termin ważności nie może poprzedzać daty zakupu. Miniony termin ma oznaczenie
w tabeli, ale nie zmienia automatycznie statusu ani nie wysyła przypomnienia.

Lista udostępnia wyszukiwanie nazwy, numerów, lokalizacji i notatek,
łączone filtry typu, statusu i przypisania (do mnie / nieprzypisane),
sortowanie według nazwy, daty utworzenia i ważności oraz paginację 25/50/100.
Układ listy odpowiada katalogowi Projektów: zarządzanie kolumnami, zbiorcze
menu filtrów, checkboxy z podświetleniem zaznaczenia i menu działań wiersza
z edycją/usunięciem. Ustawienia kolumn są zapisywane lokalnie dla Zasobów.
Globalne wyszukiwanie ma osobną kategorię Zasoby z limitem 20 wyników i linkami
do edycji. Moduł można dodać do osobistych ulubionych menu.

Dodawanie i edycja używają standardowego modala nad katalogiem; błędy walidacji
zachowują pola, błędy sieci pozwalają ponowić zapis. Zamknięcie niezapisanego
formularza wymaga potwierdzenia. Usuwanie jest trwałe, przez POST po potwierdzeniu.
Po zapisie/usunięciu lista zachowuje filtry, sortowanie i bieżącą stronę
(z ograniczeniem do ostatniej istniejącej strony).

Dane należą do właściciela i aktywnego Workspace; rzeczywisty autor utworzenia
oraz ostatniej zmiany jest zapisany osobno. Formularz przypisania ogranicza
osoby do aktywnego zespołu. Model nie zawiera kluczy licencyjnych, załączników,
rezerwacji, amortyzacji ani automatycznego śledzenia dostępności.
