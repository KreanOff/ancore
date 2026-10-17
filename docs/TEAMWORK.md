# Praca zespołowa w Workspace

Stary moduł Tablice Kanban jest wycofany. Pozostałe opisy jego modeli,
szablonów i wspólnych komponentów są referencją historyczną; nie oznaczają
aktywnych ekranów ani endpointów. Obecne tablice Przestrzeni używają `spaces.SpaceTask`.
[Szczegóły wycofania](MODULES.md#4-wycofany-moduł-tablice-kanban).

## Zespoły pracy a członkostwo Workspace

Moduł `/teams/` grupuje aktywnych członków Workspace w zespoły z własnymi
administratorami i profilami. Powiązanie z przestrzenią i przypisanie zadania
do zespołu nie nadaje dostępu do danych. Obowiązują role Workspace oraz niezależne członkostwa Przestrzeni i ich zadań. „Zarządzana przez zespół” w kreatorze
przestrzeni oznacza niezależną konfigurację, nie automatyczne udostępnienie
członkom zespołu. [Pełny opis](SPACES.md).


Starsze Projekty, Grupy, Zadania, Ulubione projekty i Szablony projektów są
wycofane. Opisy ich członkostw poniżej stanowią referencję historycznych danych,
bez aktywnych ekranów udostępniania. Bieżący dostęp i role opisuje [SPACES.md](SPACES.md).

## Zakres pierwszej wersji

Workspace obejmuje Przestrzenie i ich zadania, Kalendarz, Dysk,
Dokumenty oraz Zasoby. Dawne katalogi Kontaktów, Firm, Użytkowników i Gości
są wycofane; nie zmienia to kont ani członkostw Workspace. Dołączenie udostępnia wspólne dane Workspace.
Przestrzenie i ich zadania mają własną widoczność oraz role.
Rola „Obserwator” zapewnia wyłącznie odczyt w swoim zakresie; rola Workspace
nie omija prywatności Przestrzeni ani zadania. Nie ma roli gościa Workspace. Historyczne `SharedItem` i linki udostępniania
pozostają wyłączone.

| Rola | Dostęp |
| --- | --- |
| Właściciel | Wspólne dane i własne i udostępnione prywatne przestrzenie; ustawienia Workspace; zaproszenia członków i administratorów; zmiana ról i odbieranie dostępu; usunięcie Workspace zgodnie z dotychczasowym ograniczeniem ostatniej własnej przestrzeni |
| Administrator | Wspólne dane i własne i udostępnione prywatne przestrzenie; ustawienia Workspace; zapraszanie i usuwanie członków; anulowanie zaproszeń członków. Nie zmienia administratorów ani właściciela |
| Członek | Tworzenie, odczyt, edycja i usuwanie wspólnych danych oraz własnych i udostępnionych prywatnych przestrzeni; lista zespołu. Bez zarządzania zespołem i ustawieniami Workspace |

Właściciel wynika z `Workplace.owner`; nie można go usunąć z zespołu ani
zmienić tą ścieżką. Przenoszenie własności i usuwanie kont właścicieli nie
wchodzą w zakres tej wersji.

Zasoby są wspólne dla właściciela i aktywnych członków Workspace. Obowiązuje
ten sam zakres tworzenia, edycji i usuwania co dla innych wspólnych danych.
Osobą odpowiedzialną może być aktywne konto właściciela lub członka tego Workspace;
samo przypisanie nie nadaje dostępu. Odebranie członkostwa odbiera dostęp także
do przypisanych zasobów. Dawne przypisanie pozostaje w ewidencji do edycji,
podczas której formularz wymaga wyboru aktywnej osoby lub wyczyszczenia przypisania.

## Widoczność projektów Zadań

Historyczne `TaskProject.visibility`, `private_owner`, członkostwa,
ulubione i zaproszenia pozostają zapisane. Projekty nie mają ekranów,
formularzy, operacji zapisu ani endpointów zespołu. `tasks.access.visible_to`
wyklucza je również dla właściciela. Widoki i helpery dawnych operacji usunięto.
Mapowanie `Space.project` służy importowi i starym linkom; bieżący dostęp
zawsze sprawdza ACL Przestrzeni, niezależnie od historycznych ról projektu.

## Widoczność i udostępnianie grup

`TaskSectionMembership` i dawne prywatne grupy są danymi historycznymi.
Nie ma aktywnych endpointów `groups/<id>/team/` ani kandydatów grupy.
Historyczne członkostwo nie daje dostępu do Przestrzeni i jej zadań.

## Widoczność i udostępnianie zadań

`tasks.Task` i `TaskMembership` zachowują historyczne dane oraz powiązania
plików. Stare formularze, zespoły i operacje zapisu są usunięte.
Sygnały `tasks.sharing_signals` nadal czyszczą dawne udostępnienia i oczekujące
zaproszenia po usunięciu/dezaktywacji członka Workspace lub prywatnego rodzica.
Zapobiega to odtworzeniu dawnych grantów po ponownym dołączeniu.

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

Otrzymane zaproszenia są dostępne przez panel powiadomień; jego link
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

Nie wystarczy usunąć filtrów właściciela. Formularze relacji korzystają z tego
samego zakresu danych co widoki. Wykonawcy zadań oraz odpowiedzialni za projekty
i grupy pochodzą z aktywnych kont zespołu i właściciela; spreparowany wybór
osoby spoza zespołu jest błędem walidacji. Zakładka „Nieprzydzielone” w katalogu „Zadania”
filtruje brak projektu i grupy, niezależnie od wykonawcy. Dawny adres `view=my-tasks` nadal filtruje wykonawcę
według rzeczywiście zalogowanej osoby. Kanban zachowuje swój osobny model;
nie dodano pola wykonawcy do kart.

Backfill starych rekordów bez Workspace działa wyłącznie przy wejściu właściciela
do jego własnej przestrzeni. Nie przenosi prywatnych rekordów członka do zespołu.
Powiadomienia obejmują aktywność dostępnych Workspace, z faktycznym autorem.
Osobisty odczyt i archiwum zapisuje `dashboard.NotificationState`.
Wzmianki `@Imię Nazwisko` w komentarzach oraz osobiste obserwowanie zadań i projektów
korzystają z tego centrum. Dostawy są ograniczone do aktywnych osób zespołu;
nie nadają dostępu. Nie ma dostarczania push/e-mail.
Zbiorcza zmiana statusów zachowuje zakończenie, datę i historię każdego zadania
lub karty oraz blokadę numeracji w kolejności właściciel → rekord.

ONLYOFFICE otrzymuje tożsamość faktycznego edytora. Podpisane URL źródła i callbacku
zawierają jego identyfikator; serwer ponownie sprawdza aktywność konta i dostęp.
Starsze podpisy właściciela pozostają zgodne. Usunięcie członka zmienia klucze
Office także dla współdzielonych sesji; pliki już pobrane na urządzenie pozostają
poza kontrolą aplikacji.

## Widoczność i udostępnianie Kanbana

Kanban zachowuje modele, migracje, członkostwa oraz pliki historycznych kart.
`kanban.access.visible_to` zwraca pusty wynik; dawne formularze, widoki,
szablony oraz helpery udostępniania usunięto. Zgodne stare adresy prowadzą
wyłącznie do zaimportowanych Przestrzeni po sprawdzeniu ich aktualnego ACL.
Sygnały `kanban.sharing_signals` nadal czyszczą granty po odebraniu członkostwa.

## Migracja i sprawdzenia

Migracja `workplaces/0008_team_invitations.py` tworzy `WorkplaceInvitation`,
dodaje `WorkplaceMembership.is_active` i wyłącza dawne członkostwa osób innych
niż właściciel. Te historyczne wpisy nie dawały wcześniej dostępu; ich aktywacja
wymaga nowego zaproszenia i przyjęcia. Właściciele zachowują dostęp.
Migracja wprowadza też globalną unikalność slugów. Dotąd slug był unikalny tylko w obrębie
właściciela, co po przyjęciu zaproszenia mogłoby wskazywać niewłaściwy Workspace.
Migracja zachowuje pierwsze wystąpienie slugu, a kolejnym dopisuje identyfikator.
Adresy z takim zmienionym slugiem trzeba odświeżyć; dane i nazwy pozostają zachowane.

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
