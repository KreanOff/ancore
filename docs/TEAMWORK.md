# Praca zespołowa w Workspace

Dostęp dotyczy aktualnych Przestrzeni i modułów Workspace.
[Dawne systemy usunięto ze schematu](DATABASE.md).

## Zespoły pracy a członkostwo Workspace

Moduł `/teams/` grupuje aktywnych członków Workspace w zespoły z własnymi
administratorami i profilami. Powiązanie z przestrzenią i przypisanie zadania
do zespołu nie nadaje dostępu do danych. Obowiązują role Workspace oraz niezależne członkostwa Przestrzeni i ich zadań. „Zarządzana przez zespół” w kreatorze
przestrzeni oznacza niezależną konfigurację, nie automatyczne udostępnienie
członkom zespołu. [Pełny opis](SPACES.md).


## Zakres pierwszej wersji

Workspace obejmuje Przestrzenie i ich zadania, Kalendarz, Dysk,
Dokumenty oraz Zasoby. Dawne katalogi Kontaktów, Firm, Użytkowników i Gości
są wycofane; nie zmienia to kont ani członkostw Workspace. Dołączenie udostępnia wspólne dane Workspace.
Przestrzenie i ich zadania mają własną widoczność oraz role.
Rola „Obserwator” zapewnia wyłącznie odczyt w swoim zakresie; rola Workspace
nie omija prywatności Przestrzeni ani zadania. Nie ma roli gościa Workspace.

| Rola | Dostęp |
| --- | --- |
| Właściciel | Wspólne dane i własne i udostępnione prywatne przestrzenie; ustawienia Workspace; zaproszenia członków i administratorów; zmiana ról i odbieranie dostępu; usunięcie Workspace zgodnie z dotychczasowym ograniczeniem ostatniej własnej przestrzeni |
| Administrator | Wspólne dane i własne i udostępnione prywatne przestrzenie; ustawienia Workspace; zapraszanie i usuwanie członków; anulowanie zaproszeń członków. Nie zmienia administratorów ani właściciela |
| Członek | Tworzenie, odczyt, edycja i usuwanie wspólnych danych oraz własnych i udostępnionych prywatnych przestrzeni; lista zespołu. Bez zarządzania zespołem i ustawieniami Workspace |

Właściciel wynika z `Workplace.owner`; nie można go usunąć z zespołu ani
zmienić tą ścieżką. Przenoszenie własności i usuwanie kont właścicieli nie
wchodzą w zakres tej wersji.
Usunięcie Workspace blokuje właściciela przed wyborem zastępczego miejsca
pracy. Ochrona ostatniego własnego Workspace obejmuje równoczesne żądania.

Zasoby są wspólne dla właściciela i aktywnych członków Workspace. Obowiązuje
ten sam zakres tworzenia, edycji i usuwania co dla innych wspólnych danych.
Osobą odpowiedzialną może być aktywne konto właściciela lub członka tego Workspace;
samo przypisanie nie nadaje dostępu. Odebranie członkostwa odbiera dostęp także
do przypisanych zasobów. Dawne przypisanie pozostaje w ewidencji do edycji,
podczas której formularz wymaga wyboru aktywnej osoby lub wyczyszczenia przypisania.

## Role Pulpitów

Role `DashboardMembership` dotyczą konkretnego Pulpitu, niezależnie od roli
Workspace. Właścicielem Pulpitu pozostaje jego `created_by`; `owner` nadal
wyznacza właściciela danych Workspace. Członkostwo Workspace jest wymagane
dla każdej roli. Widoczność całego Workspace daje pozostałym osobom tylko odczyt.

| Rola Pulpitu | Uprawnienia |
| --- | --- |
| Właściciel | Pełna edycja, wszystkie role, widoczność i usunięcie zwykłego Pulpitu; chroniony wiersz bez zmiany właściciela |
| Administrator | Gadżety, układ, ustawienia oraz udostępnianie i zmiana/odebranie ról członka i obserwatora; bez operacji na administratorach i właścicielu, bez zmiany widoczności ani usuwania Pulpitu |
| Członek | Dodawanie, konfiguracja, usuwanie i układanie gadżetów; bez ustawień Pulpitu i zarządzania dostępem |
| Obserwator | Wyłącznie oglądanie Pulpitu i danych, do których ma własny dostęp |

Obniżenie roli i odebranie dostępu obowiązuje przy następnym żądaniu, również
w już otwartym edytorze. Usunięcie lub wyłączenie członka Workspace usuwa
jego udostępnienia Pulpitów; ponowne dołączenie nie przywraca dawnych ról.
Dotychczasowi odbiorcy pozostają obserwatorami po migracji. Pulpitu domyślnego
nadal nie można usunąć. Role nie rozszerzają dostępu do Przestrzeni ani Filtrów.

## Widoczność projektów Zadań

Dawne projekty usunięto. Bieżący zakres wyznaczają `SpaceMembership` i `spaces.access`.

## Widoczność i udostępnianie grup

Dawne grupy i ich członkostwa usunięto. Zadania należą bezpośrednio do Przestrzeni.

## Widoczność i udostępnianie zadań

Bieżące zadania używają `SpaceTaskMembership` oraz `spaces.task_team`.
Role i ograniczenia rodziców opisuje sekcja
[Dostęp do niezależnych zadań przestrzeni](#dostęp-do-niezależnych-zadań-przestrzeni-10102026).

## Zaproszenia i ekran zespołu

Ekran `/workplaces/` pokazuje katalog Workspace jako osobną stronę z własnym
menu „Zarządzanie Workspace”: powrotem do miejsca wejścia i aktywną pozycją
„Workspace”, bez zakładki otrzymanych zaproszeń. Skład zespołu znajduje się w zakładce
„Członkowie” okna „Edytuj miejsce pracy”, obok „Główna” z ustawieniami
i „Wysłane zaproszenia” z oczekującymi zaproszeniami do tego Workspace.
Nazwa Workspace i ikona ustawień otwierają „Główną”; liczba członków oraz stare
linki `?workspace=<pk>` / `?view=members&workspace=<pk>` otwierają „Członkowie”.
Okno wybranego Workspace jest renderowane nad katalogiem. Zarządzanie nim nie
zmienia aktywnej sesji ani kontekstu modułów. Znacznik „Bieżący” wskazuje
przestrzeń pracy; strzałka przełączenia nadal otwiera jej Zadania.
Zwykły członek ma okno „Miejsce pracy” z odczytem danych i składu zespołu,
bez akcji edycji, zapraszania, zmiany ról i odbierania dostępu.
Wejście z Ustawień pokazuje „Wróć do ustawień” i zachowuje kategorię oraz
przewinięcie. Wejście z menu bieżącego Workspace wraca do wcześniej otwartego
widoku. Bez źródłowego widoku domyślnym powrotem pozostaje Dashboard.

Otrzymane zaproszenia są dostępne przez panel powiadomień, także po dawnym
usunięciu powiadomienia. Oczekujących
zaproszeń nie można usuwać ani archiwizować w centrum powiadomień;
zbiorcze usuwanie je pomija. Link zaproszenia
otwiera okno decyzji nad katalogiem Workspace. Dawny adres `view=received`
pokazuje katalog bez tabeli ani licznika otrzymanych zaproszeń. Wysłane zaproszenia są
w trzeciej zakładce okna miejsca pracy i są dostępne wyłącznie właścicielowi
oraz administratorowi. Stare linki `view=invitations` otwierają tę zakładkę
nad katalogiem; wybranie Workspace bez uprawnień nadal nie ujawnia zaproszeń.
Nie ma już przełącznika rodzaju zaproszeń ani wyboru Workspace na tej stronie.

Właściciel i administrator mają przycisk „Zaproś osobę” w zakładce
„Członkowie” i „Wysłane zaproszenia” w oknie miejsca pracy.
Zmiana ról i odebranie dostępu pozostają w menu wiersza,
zgodnie z macierzą ról. Po utworzeniu Workspace wracamy do katalogu,
po zapisie ustawień — do katalogu, po zmianie roli —
do otwartej zakładki „Członkowie” w oknie, a po wysłaniu lub anulowaniu zaproszenia —
do zakładki „Wysłane zaproszenia” tego Workspace.
Utworzenie nie przełącza kontekstu pracy. Ustawienia aplikacji mają jeden
link „Zarządzaj Workspace”. Dotychczasowy GET `/workplaces/<pk>/team/`
przekierowuje do właściwej zakładki; POST nadal waliduje zaproszenie i przy
błędzie renderuje okno wysyłania nad zakładką „Wysłane zaproszenia”.
Zamknięcie błędu przywraca fokus widocznemu przyciskowi „Zaproś osobę”.

Tabele członków i wysłanych zaproszeń korzystają ze wspólnego komponentu „Projekty”:
wiersze 35px, nagłówki z ikonami, siatka i turkusowe podświetlenie. Kolumny
obejmują zaznaczenie, działania, nazwę z avatarem, e-mail, rolę i datę dołączenia lub
ważności zaproszenia. Menu zaproszenia pozwala je anulować zgodnie z rolą
użytkownika. Checkbox w nagłówku zaznacza wszystkie wiersze swojej tabeli;
wybór pozostaje niezależny w obu zakładkach i podświetla zaznaczone wiersze.
„Zaproś osobę” i „Zmień rolę”
otwierają standardowe modale. Wpływ
odebrania dostępu na Office opisuje potwierdzenie operacji.

Zaproszenie wskazuje **istniejące aktywne konto Ancore przez e-mail**. Jest
zapisywane w aplikacji, bez wysyłania e-maila. Odbiorca widzi je pod dzwonkiem,
niezależnie od aktualnie wybranej przestrzeni.
Formularz podpowiada osoby po co najmniej 2 znakach imienia, drugiego imienia,
nazwiska, ID Ancore lub e-maila. Można łączyć części imienia i nazwiska.
Lista pokazuje do 10 aktywnych kont z avatarem, nazwą i adresem; większy zbiór
wymaga doprecyzowania. Wybór wpisuje e-mail i pokazuje odbiorcę zaproszenia;
pełny pasujący adres również pokazuje podgląd. Podpowiedzi pomijają właściciela,
aktywnych członków i osoby z ważnym oczekującym zaproszeniem do wybranego Workspace.
GET `/workplaces/<pk>/team/candidates/` wymaga właściciela lub administratora
tego Workspace, niezależnie od aktywnej sesji. Nie tworzy zaproszeń i zwraca
wyłącznie dane potrzebne do rozpoznania odbiorcy; odpowiedź nie jest cache'owana.
Zapis nadal ponownie weryfikuje adres, konto, członkostwo i oczekujące zaproszenia.
Przy zapisie porównanie adresu nie rozróżnia wielkości liter, ale musi wskazać
dokładnie jedno konto. Niejednoznaczny adres w starszej bazie daje błąd formularza; nie wybieramy
pierwszego konta. Migracja Accounts 0008 blokuje tworzenie takich duplikatów.
Turkusowa kropka przy dzwonku oznacza nieprzeczytane wpisy lub oczekujące
zaproszenia; obie liczby są dostępne w opisie przycisku. Stan jest sprawdzany co 30 sekund w widocznej karcie,
po powrocie do karty i po częściowej nawigacji. Powiadomienie pokazuje autora,
Workspace, rolę i termin ważności. Kliknięcie otwiera konkretne zaproszenie
w standardowym oknie nad katalogiem Workspace (`?invitation=<pk>`). Pokazuje zapraszającą
osobę, Workspace, rolę, termin oraz przyciski „Później”, „Odrzuć” i „Przyjmij”.
Przy kilku zaproszeniach strzałki przechodzą między nimi; zamknięcie nie zmienia
zaproszenia. Nie ma osobnych szerokich pasków nad listą Workspace.
Nieaktualny lub cudzy adres pokazuje ogólny komunikat o niedostępności.
Dotyczy to także wcześniej zapisanych zaproszeń.
Zakładka „Wysłane zaproszenia” w oknie miejsca pracy pokazuje oczekujące
zaproszenia wysłane z wybranego Workspace.
Przyjęcie wymaga POST i sesji właściwego odbiorcy;
GET nie nadaje dostępu. Zaproszenie wygasa po 7 dniach, może zostać odrzucone
lub anulowane i nie może zostać wykorzystane ponownie. Zapis jest blokowany
na wierszu Workspace, także przy zmianie ról, przyjęciu i usuwaniu członka.
Unikalność oczekującego zaproszenia egzekwuje baza.

Odebranie dostępu zachowuje zadania i pliki zespołu. Stara sesja użytkownika,
zapisane URL, wyszukiwanie, załączniki i oba katalogi plików nie nadają mu
ponownie dostępu. Operacja unieważnia również klucze otwartych edytorów Office
w tym Workspace; pozostali użytkownicy muszą ponownie otworzyć edytory.

## Zakres danych i tożsamość

`workplaces_for_user()` obejmuje właściciela i członkostwa. Middleware ustala
aktywny kontekst zarówno z sesji, jak i scoped URL.
`workspace_owner(request)` w `workplaces.services` weryfikuje rolę, a następnie
zwraca właściciela Workspace jako właściciela **danych biznesowych**.
Dotychczasowe filtry właściciel + Workspace, numeracja oraz relacje pozostają
w mocy. Nowy rekord utworzony przez członka zapisuje właściciela Workspace;
usunięcie członkostwa nie usuwa rekordów. `request.user` nadal oznacza osobę
wykonującą operację, autora komentarza i wpisu historii oraz właściciela
osobistych preferencji widoku.

Formularze relacji stosują ten sam zakres co widoki. Wykonawcy zadań i osoby
odpowiedzialne za przestrzeń pochodzą z aktywnych kont Workspace.
Zmiana Workspace nie wykonuje backfillu rekordów. Powiadomienia, wzmianki
i przypomnienia ponownie sprawdzają dostęp; nie nadają go. Stan inbox jest osobisty.
Zmiana statusu zachowuje zakończenie, datę i autora historii.

ONLYOFFICE otrzymuje tożsamość faktycznego edytora. Podpisane URL źródła i callbacku
zawierają jego identyfikator; serwer ponownie sprawdza aktywność konta i dostęp.
Starsze podpisy właściciela pozostają zgodne. Usunięcie członka zmienia klucze
Office także dla współdzielonych sesji; pliki już pobrane na urządzenie pozostają
poza kontrolą aplikacji.

## Widoczność i udostępnianie Kanbana

Tablice Przestrzeni używają tych samych zadań, członkostw i ACL. Osobny moduł Kanbana usunięto.

## Migracja i sprawdzenia

Nowe migracje początkowe od razu tworzą aktualny model Workspace,
członkostw i zaproszeń. Wymagają pustej bazy; [procedura](DATABASE.md).

Testy `backend/workplaces/test_team.py` obejmują role, zaproszenia, zakres danych,
przypisania, historię, oba warianty URL, pobieranie plików, odebranie dostępu,
Office i osobiste dane bez Workspace. Weryfikacja wymaga PostgreSQL.

Testy `backend/workplaces/test_management.py` obejmują wybór niezależny od aktywnej sesji,
powroty po zapisie i błędach, stare linki, niedostępne identyfikatory, role, CSRF
oraz jawne przełączenie kontekstu.
`backend/workplaces/test_invitation_candidates.py` obejmuje podpowiedzi, limit, uprawnienia,
wykluczenia w wybranym Workspace, cofnięcie dostępu, escapowanie danych i ponowną
walidację zapisu po zmianie członkostwa.


## Dostęp do niezależnych zadań przestrzeni (10.10.2026)

Nowy system używa `SpaceMembership` i `SpaceTaskMembership`; role starszych
projektów, grup i zadań nie sterują jego bieżącymi uprawnieniami.
`spaces.access` sprawdza aktywne członkostwo Workspace, prywatność przestrzeni
i całe drzewo rodziców. Obserwator dowolnego poziomu ma wyłącznie odczyt.
Udostępnienie zadania nie udostępnia przestrzeni ani rodziców.

Właściciel prywatnego zadania zmienia widoczność i administratorów;
administrator zadania zarządza zwykłymi członkami i obserwatorami.
Kandydat jest aktywną osobą Workspace z dostępem do przestrzeni i rodziców.
Endpoint po blokadzie ponownie sprawdza autora, kandydata i zakres.
Zmiana widoczności na dziedziczoną czyści członkostwa samego zadania,
pozostawiając niezależne prywatne podzadania.

`backend/spaces/signals.py` czyści udostępnienia po usunięciu lub dezaktywacji członka
Workspace, usunięciu członka prywatnej przestrzeni lub prywatnego rodzica.
Ponowne dodanie nie przywraca tych dostępów. `QuerySet.update()` pomija
sygnały i wymaga jawnego czyszczenia. Historyczne uprawnienia zostały
jednorazowo odwzorowane podczas migracji opisanej w [SPACES.md](SPACES.md).

## Interfejs zarządzania Workspace w React

Katalog i okna ustawień/członków/zaproszeń korzystają z React/TypeScript oraz
JSON API Django (`backend/workplaces/frontend.py`, `frontend/app/src/workspaces/`).
Reguły ról, transakcje i operacje domenowe pozostają w `views.py` oraz
`team_views.py`. Wybór do zarządzania nadal nie przełącza aktywnego Workspace.
Odpowiedź na otrzymane zaproszenie jest dostępna wyłącznie jego odbiorcy;
przyjęcie tworzy/aktywuje członkostwo i przełącza kontekst. API podpowiedzi
osób udostępnia dane zamiast HTML. [Kontrakt migracji](FRONTEND.md).
