# Praca zespołowa w Workspace

## Zakres pierwszej wersji

Workspace obejmuje wspólne Projekty i Zadania, Kanban, Kontakty i firmy,
Kalendarz, Dysk oraz Dokumenty. Dołączenie udostępnia **cały Workspace**.
Nie ma jeszcze prywatnych projektów wewnątrz zespołu, ról gości ani uprawnień
odczytu dla wybranych elementów. Historyczne `SharedItem` i linki udostępniania
pozostają wyłączone.

| Rola | Dostęp |
| --- | --- |
| Właściciel | Wszystkie dane; ustawienia Workspace; zaproszenia członków i administratorów; zmiana ról i odbieranie dostępu; usunięcie Workspace zgodnie z dotychczasowym ograniczeniem ostatniej własnej przestrzeni |
| Administrator | Wszystkie dane; ustawienia Workspace; zapraszanie i usuwanie członków; anulowanie zaproszeń członków. Nie zmienia administratorów ani właściciela |
| Członek | Tworzenie, odczyt, edycja i usuwanie danych we wszystkich modułach; lista zespołu. Bez zarządzania zespołem i ustawieniami Workspace |

Właściciel wynika z `Workplace.owner`; nie można go usunąć z zespołu ani
zmienić tą ścieżką. Przenoszenie własności i usuwanie kont właścicieli nie
wchodzą w zakres tej wersji.

## Zaproszenia i ekran zespołu

Ekran `/workplaces/` ma zakładki „Workspace” i „Zaproszenia”, przełączane
standardowymi przyciskami katalogu. Skład zespołu znajduje się w zakładce
„Członkowie” okna „Edytuj miejsce pracy”, obok „Główna” z ustawieniami
i „Wysłane zaproszenia” z oczekującymi zaproszeniami do tego Workspace.
Nazwa Workspace i ikona ustawień otwierają „Główną”; liczba członków oraz stare
linki `?workspace=<pk>` / `?view=members&workspace=<pk>` otwierają „Członkowie”.
Okno wybranego Workspace jest renderowane nad katalogiem. Zarządzanie nim nie
zmienia aktywnej sesji ani kontekstu modułów. Znacznik „Bieżący” wskazuje
przestrzeń pracy; strzałka przełączenia nadal otwiera jej Zadania.
Zwykły członek ma okno „Miejsce pracy” z odczytem danych i składu zespołu,
bez akcji edycji, zapraszania, zmiany ról i odbierania dostępu.

Strona „Zaproszenia” pokazuje wyłącznie otrzymane zaproszenia
(`view=received`, wszystkie zaproszenia zalogowanego odbiorcy) i ich licznik.
Przycisk „Otwórz” uruchamia istniejące okno decyzji. Wysłane zaproszenia są
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

Tabele członków i wysłanych zaproszeń korzystają ze wspólnego komponentu „Wszystkie projekty”:
wiersze 35px, nagłówki z ikonami, siatka i turkusowe podświetlenie. Kolumny
obejmują zaznaczenie, działania, nazwę z avatarem, e-mail, rolę i datę dołączenia lub
ważności zaproszenia. Menu zaproszenia pozwala je anulować zgodnie z rolą
użytkownika. Checkbox w nagłówku zaznacza wszystkie wiersze swojej tabeli;
wybór pozostaje niezależny w obu zakładkach i podświetla zaznaczone wiersze.
Tabela otrzymanych zaproszeń zachowuje style Dokumentów. „Zaproś osobę” i „Zmień rolę”
otwierają standardowe modale. Wpływ
odebrania dostępu na Office opisuje potwierdzenie operacji.

Zaproszenie wskazuje **istniejące aktywne konto Ancore przez e-mail**. Jest
zapisywane w aplikacji, bez wysyłania e-maila. Odbiorca widzi je pod dzwonkiem
oraz na stronie Workspace, niezależnie od aktualnie wybranej przestrzeni.
Wyszukanie nie rozróżnia wielkości liter, ale musi wskazać dokładnie jedno
konto. Niejednoznaczny adres w starszej bazie daje błąd formularza; nie wybieramy
pierwszego konta. Migracja Accounts 0008 blokuje tworzenie takich duplikatów.
Turkusowa kropka przy dzwonku oznacza nieprzeczytane wpisy lub oczekujące
zaproszenia; obie liczby są dostępne w opisie przycisku. Stan jest sprawdzany co 30 sekund w widocznej karcie,
po powrocie do karty i po częściowej nawigacji. Powiadomienie pokazuje autora,
Workspace, rolę i termin ważności. Kliknięcie otwiera konkretne zaproszenie
w standardowym oknie na stronie Workspace (`?invitation=<pk>`). To samo okno
otwiera przycisk „Otwórz” na liście otrzymanych zaproszeń. Pokazuje zapraszającą
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
osoby spoza zespołu jest błędem walidacji. „Moje zadania” filtrują wykonawcę
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

## Migracja i sprawdzenia

Migracja `workplaces/0008_team_invitations.py` tworzy `WorkplaceInvitation`,
dodaje `WorkplaceMembership.is_active` i wyłącza dawne członkostwa osób innych
niż właściciel. Te historyczne wpisy nie dawały wcześniej dostępu; ich aktywacja
wymaga nowego zaproszenia i przyjęcia. Właściciele zachowują dostęp.
Migracja wprowadza też globalną unikalność slugów. Dotąd slug był unikalny tylko w obrębie
właściciela, co po przyjęciu zaproszenia mogłoby wskazywać niewłaściwy Workspace.
Migracja zachowuje pierwsze wystąpienie slugu, a kolejnym dopisuje identyfikator.
Adresy z takim zmienionym slugiem trzeba odświeżyć; dane i nazwy pozostają zachowane.

Testy `workplaces/test_team.py` obejmują role, zaproszenia, zakres danych,
przypisania, historię, oba warianty URL, pobieranie plików, odebranie dostępu,
Office i osobiste dane bez Workspace. Weryfikacja wymaga PostgreSQL.

Testy `workplaces/test_management.py` obejmują wybór niezależny od aktywnej sesji,
powroty po zapisie i błędach, stare linki, niedostępne identyfikatory, role, CSRF
oraz jawne przełączenie kontekstu.
