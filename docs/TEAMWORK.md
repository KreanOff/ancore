# Praca zespołowa w Workspace

## Zakres pierwszej wersji

Workspace obejmuje wspólne Projekty i Zadania, Kanban, Kontakty i firmy,
Kalendarz, Dysk, Dokumenty oraz Zasoby. Dołączenie udostępnia wspólne dane Workspace.
Projekty Zadań mają widoczność **Publiczny** (cały Workspace) lub **Prywatny**
(osoba, która ustawiła prywatność, i osoby, którym udostępniono projekt). Rola „Obserwator” zapewnia dostęp tylko do odczytu w konkretnym prywatnym projekcie. Nie ma roli gościa Workspace. Historyczne `SharedItem` i linki udostępniania
pozostają wyłączone.

| Rola | Dostęp |
| --- | --- |
| Właściciel | Wspólne dane i własne i udostępnione prywatne projekty; ustawienia Workspace; zaproszenia członków i administratorów; zmiana ról i odbieranie dostępu; usunięcie Workspace zgodnie z dotychczasowym ograniczeniem ostatniej własnej przestrzeni |
| Administrator | Wspólne dane i własne i udostępnione prywatne projekty; ustawienia Workspace; zapraszanie i usuwanie członków; anulowanie zaproszeń członków. Nie zmienia administratorów ani właściciela |
| Członek | Tworzenie, odczyt, edycja i usuwanie wspólnych danych oraz własnych i udostępnionych prywatnych projektów; lista zespołu. Bez zarządzania zespołem i ustawieniami Workspace |

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

„Publiczny” oznacza dostęp dla właściciela i aktywnych członków danego Workspace,
bez dostępu anonimowego lub osób z innych Workspace. „Prywatny — wybrane osoby”
przypisuje `TaskProject.private_owner` faktycznej osobie zapisującej tę opcję.
Pole `user` nadal wskazuje właściciela danych Workspace; odpowiedzialny za projekt
oraz wykonawca zadania nie nadają dostępu. Administrator i właściciel Workspace
nie mają wyjątku pozwalającego oglądać cudze prywatne projekty.

Po utworzeniu prywatnego projektu jego właściciel może udostępnić go wybranym,
aktywnym członkom tego samego Workspace. Okno „Edytuj projekt” ma zakładki
„Główna” i „Członkowie”. Przycisk „Udostępnij” otwiera wspólny picker osoby
oraz wybór roli. Zapis od razu tworzy członkostwo: projekt pojawia się odbiorcy
przy kolejnym odczycie listy, bez zaproszenia, powiadomienia wymagającego decyzji
ani akceptacji. Nowy projekt domyślnie jest prywatny i dostępny tylko właścicielowi,
do pierwszego udostępnienia. Dotyczy to także tworzenia z szablonu i żądań bez
pola widoczności; wybór „Publiczny” musi być jawny. Edycja zachowuje widoczność.

Role projektu są niezależne od ról Workspace:

| Rola projektu | Uprawnienia |
| --- | --- |
| Właściciel (`private_owner`) | Udostępnia członkom, administratorom i obserwatorom, zmienia ich role i odbiera dostęp; jako jedyny zmienia widoczność |
| Administrator | Nadaje i odbiera dostęp członkom oraz obserwatorom; nie zmienia ról ani administratorów |
| Członek | Edytuje zawartość i widzi listę członków; nie zarządza dostępem zespołu |
| Obserwator | Tylko przegląda projekt, grupy, zadania, notatki, czat, historię, dziennik pracy i pliki oraz listę członków. Bez zapisu, komentarzy, dodawania, usuwania, zmiany statusów, kopiowania do szablonu i zarządzania dostępem |

Właściciel, administrator i członek zachowują dotychczasowe operacje edycji
i usuwania danych projektu, grup, zadań i plików. Obserwator może pobierać
dostępne pliki i ustawiać własne obserwowanie powiadomień. Jego rola nie zmienia
uprawnień do pozostałych projektów ani innych modułów Workspace. Również
administrator lub właściciel Workspace z rolą obserwatora ma w tym
projekcie tylko odczyt. Zmiana roli obowiązuje przy kolejnym żądaniu.
`editable_to` ogranicza zapisy i relacje formularzy; mieszana operacja zbiorcza
z obserwowanym elementem zostaje odrzucona w całości. Blokada obejmuje również
stare podzadania poza grupą rodzica i kaskadowe usuwanie przez inny projekt. Prywatnego właściciela nie można usunąć ani
zmienić jego roli tą ścieżką. Rola w Workspace nie omija ograniczeń projektu.

`TaskProject.shared_with` korzysta z `TaskProjectMembership` jako `through`.
POST `action=share` tworzy członkostwo z wybraną rolą w tej samej transakcji.
Odbiorca musi mieć aktywne konto i należeć do Workspace. Historyczne modele
`TaskProjectInvitation` i `TaskSectionInvitation` pozostają w bazie, ale nie są
źródłami powiadomień i nie mają endpointów akceptacji. Stare akcje `invite`
i `cancel` są odrzucane. Historyczne `SharedItem` i tokeny pozostają wyłączone.
Zaproszenia do samego Workspace nadal wymagają decyzji odbiorcy.

Endpointy w `tasks/views/project_team.py` ponownie weryfikują uprawnienia,
aktywność kont i członkostwo przy każdym odczycie i zapisie. Operacje blokują
Workspace i projekt w transakcji. Udostępnienie lub zmiana członka
zapisują się osobno od pól głównego formularza; jego niezapisane dane pozostają.
Stary formularz przesyłający listę `shared_with` jest odrzucany. Zwykły zapis
pól projektu zachowuje członków. Zmiana na publiczny czyści członkostwa i anuluje
historyczne oczekujące zaproszenia; ponowne ustawienie prywatności zaczyna się bez odbiorców.

Usunięcie lub dezaktywacja członkostwa Workspace przez zapis modelu usuwa
udostępnienia i anuluje zaproszenia do projektów (`tasks/sharing_signals.py`);
ponowne dołączenie nie przywraca ich. Operacje utrzymaniowe przez
`QuerySet.update()` muszą same wyczyścić członkostwa i zaproszenia, ponieważ
omijają sygnały. Sam filtr dostępu zawsze sprawdza członkostwo Workspace.

Grupy oraz zadania mogą dodatkowo ograniczać widoczność projektu; podzadania dziedziczą ograniczenia wszystkich rodziców. Kontrola obejmuje
całe drzewo rodziców, również stare podzadania z inną grupą niż rodzic;
usuwanie zadania, grupy lub projektu odrzuca kaskadę obejmującą niedostępne podzadania. `tasks/access.py`
filtruje jawnie według rzeczywistego odbiorcy: listy, nawigację, opcje formularzy,
bezpośrednie URL, edycję i usuwanie (także zbiorcze), notatki, dziennik pracy,
pliki, ustawienia terminów, wyszukiwanie, Dashboard, kalendarz i powiadomienia.
Obserwowanie, wzmianki i przypisanie wykonawcy nie omijają tego filtra.
Przypomnienie zadania bez wykonawcy trafia do jego prywatnego właściciela, a gdy zadanie dziedziczy dostęp — do prywatnego
właściciela projektu; pozostałe zadania zachowują odbiorcę według dotychczasowych zasad.
Prywatny projekt nie pojawia się w licznikach zadań przy wspólnych tagach.
Numery zadań nadal są wspólne dla właściciela i Workspace; ich luki nie nadają dostępu.

Zmiana projektu na „Publiczny” udostępnia jego publiczne grupy zespołowi; prywatne grupy zachowują własne ograniczenia. Zmiana na „Prywatny”
odbiera dostęp osobom niewskazanym w udostępnianiu przy kolejnym żądaniu, również z wcześniej otwartego
formularza. Plików już pobranych oraz treści wcześniej wyświetlonych nie można
cofnąć. Usunięcie członkostwa odbiera dostęp także do własnych prywatnych projektów
w tym Workspace, zachowując dane. Usunięcie konta prywatnego właściciela nie
publikuje projektu: `private_owner` staje się pusty, a projekt pozostaje ukryty.

Szablon zapisany z prywatnego projektu jest prywatny dla osoby zapisującej snapshot.
Nie kopiuje odbiorców udostępnienia projektu ani nie udostępnia im szablonu.
Jest niezależnym snapshotem, więc późniejsze zmiany widoczności projektu nie
zmieniają już zapisanych szablonów. Nowy projekt z szablonu domyślnie jest prywatny, niezależnie od widoczności
szablonu; użytkownik może jawnie wybrać publiczny w formularzu.
Kanban ma własne modele i analogiczne udostępnianie przestrzeni oraz tablic, opisane poniżej.

Migracja Tasks `0054_project_visibility` zachowuje istniejące projekty i szablony
jako publiczne. Starszy formularz bez pola widoczności zachowuje bieżącą wartość.
Testy `tasks/test_project_visibility.py` obejmują role, oba warianty URL,
spreparowane żądania, powiązane moduły, szablony i cofnięcie dostępu.
Migracja `0055_project_sharing` dodaje pustą relację odbiorców, bez zmiany
istniejącego dostępu. `0056_project_invitations` przenosi dotychczasowe udostępnienia
do członkostw z rolą „Członek”, zachowując dostęp, i dodaje zaproszenia.
Dashboard `0005_project_invitations` dodaje osobisty stan ich powiadomień.
Tasks `0057_project_observer` rozszerza wybór roli w członkostwach i zaproszeniach,
bez zmiany istniejących ról. `tasks/test_project_observer.py` sprawdza odczyt,
blokady zapisu, zmianę roli, formularze, operacje zbiorcze i oba warianty URL.
Testy `tasks/test_project_sharing.py` obejmują dostęp i integracje modułów,
a `tasks/test_project_invitations.py` natychmiastowy dostęp, role, granice Workspace,
cofnięcie, brak zaproszeń i zachowanie wcześniejszych członkostw podczas migracji.

## Widoczność i udostępnianie grup

`TaskSection` ma widoczność „Publiczna — uczestnicy projektu” lub
„Prywatna — wybrane osoby”, `private_owner` oraz `shared_with` przez
`TaskSectionMembership`. Istniejące grupy pozostają publiczne i dziedziczą
zakres projektu. Grupa tworzona formularzem „Nowa grupa” domyślnie jest prywatna
rzeczywistego autora. Pierwsza grupa utworzona razem z projektem oraz grupy
odtwarzane z szablonu dziedziczą dostęp nowego projektu.

Dostęp zawsze wymaga dostępu do projektu nadrzędnego i jego Workspace.
Prywatna grupa zawęża ten zakres; właściciel lub administrator projektu ani
Workspace nie omijają jej prywatności. Odpowiedzialny grupy i wykonawca zadania
nie otrzymują dostępu przez samo przypisanie. Brak prywatnego właściciela
pozostawia grupę ukrytą. Role właściciela, administratora, członka i obserwatora
mają tę samą macierz co w projekcie, ale obowiązują w grupie. Obserwator projektu
pozostaje tylko czytelnikiem także wtedy, gdy w grupie ma wyższą rolę.

Zakładki „Główna” i „Członkowie” korzystają z komponentów projektu.
`tasks/views/section_team.py` obsługuje zespół i kandydatów pod
`groups/<pk>/team/` oraz `groups/<pk>/team/candidates/`, także w adresach scoped.
Można udostępnić grupę aktywnej osobie z tego Workspace mającej dostęp do
projektu. `action=share` od razu tworzy `TaskSectionMembership`; grupa i jej
zawartość stają się dostępne bez etapu przyjęcia zaproszenia.

Tylko prywatny właściciel zmienia widoczność i role. Administrator nadaje
i odbiera dostęp członkom oraz obserwatorom. Publiczna grupa pokazuje uczestników
projektu, bez osobnego udostępniania grupy. Zapis innych pól zachowuje członkostwa;
publikacja grupy je czyści i anuluje oczekujące zaproszenia. Publikacja projektu
zachowuje niezależne udostępnienia jego prywatnych grup. Usunięcie członkostwa
prywatnego projektu lub Workspace usuwa powiązane członkostwa grup i anuluje
zaproszenia, aby ponowne dołączenie nie przywracało starych uprawnień.
Operacje zespołu oraz edycja widoczności blokują Workspace i grupę w transakcji.

Filtry `visible_to` i `editable_to` obejmują notatki, zadania, całe drzewa
podzadań, pliki, historię i czas pracy oraz integracje wyszukiwania, kalendarza
czy powiadomień. Liczniki i sortowanie po aktywności pomijają ukryte zadania.
Usunięcie projektu odrzuca kaskadę obejmującą ukrytą lub obserwowaną grupę,
także pustą. Snapshot szablonu zawiera wyłącznie edytowalne grupy i zadania;
jeśli zawiera prywatną grupę, sam jest prywatny dla autora snapshotu.

Migracje `tasks/0058_section_sharing` i `dashboard/0006_section_sharing`
dodają pola, członkostwa, zaproszenia i osobisty stan ich powiadomień.
Nie zmieniają istniejącego dostępu. Testy: `tasks/test_section_sharing.py`.
Migracja `tasks/0059_direct_sharing` zamienia ważne oczekujące zaproszenia
projektów i grup w członkostwa, zachowując istniejące role. Ponownie sprawdza
aktywność obu kont, Workspace, aktualne uprawnienia autora, prywatność oraz
projekt nadrzędny grupy. Nie przywraca zaproszeń odrzuconych, anulowanych,
wygasłych ani dostępu po utracie uprawnień. Kończy wszystkie pozostałe oczekujące
zaproszenia statusem `revoked`, bez przypisywania odbiorcy decyzji o akceptacji.
Cofnięcie migracji nie odbiera nadanych członkostw. Regresje migracji:
`tasks/test_direct_sharing_migration.py`.

## Widoczność i udostępnianie zadań

`Task` ma `visibility`, `private_owner` i `shared_with` przez `TaskMembership`.
„Publiczne — dostęp odziedziczony” zachowuje zakres projektu, grupy i każdego
zadania nadrzędnego. „Prywatne — wybrane osoby” dodatkowo ogranicza go do
prywatnego właściciela i osób z nadanym dostępem. Istniejące zadania zachowują
dotychczasowy dostęp; nowe zadania i podzadania w formularzach oraz szybkim
dodawaniu domyślnie są prywatne faktycznego autora. Samo przypisanie wykonawcy
nadal nie daje dostępu. „Zadania nieprzydzielone” pokazują dostępne zadania
bez projektu i grupy, niezależnie od wykonawcy; przypisanie grupy usuwa zadanie
z tej listy. Wszystkie widoczne zadania główne pozostają dostępne w katalogu „Zadania”.

Szczegóły zadania mają pole „Widoczność” oraz zakładkę „Członkowie”. Właściciel
udostępnia zadanie rolom administrator/członek/obserwator i zarządza rolami;
administrator nadaje i odbiera dostęp członkom oraz obserwatorom. Obserwator
na dowolnym poziomie hierarchii ma tylko odczyt, także gdy niżej jest właścicielem.
Publiczne zadanie pokazuje osoby z dostępem odziedziczonym. Udostępnienie
prywatnego zadania zapisuje się osobno od głównego formularza i działa od razu,
bez zaproszenia, powiadomienia do akceptacji ani wysyłania e-maila.

`tasks/views/task_team.py` obsługuje `items/<pk>/team/` oraz
`items/<pk>/team/candidates/`, także w adresach scoped. `pk` jest stabilnym
kluczem bazy, nie wyświetlanym numerem `task_id`. Kandydat musi być aktywnym
członkiem tego Workspace z dostępem do wszystkich nadrzędnych elementów.
Udostępnienie zadania nie udostępnia projektu, grupy ani rodzica. Brak prywatnego
właściciela zamyka dostęp. Zmiana widoczności na publiczną czyści jego członkostwa,
ale zachowuje niezależne udostępnienia prywatnych podzadań. Odebranie członkostwa
prywatnego projektu, grupy, rodzica lub Workspace czyści odpowiednie udostępnienia
zadań, więc ponowne dołączenie ich nie przywraca.

`visible_to` i `editable_to` obejmują całe drzewa zadań, komentarze, pliki,
czas pracy, listy, statystyki, szablony, wyszukiwanie, kalendarz i powiadomienia.
Wzmianki podpowiadają wyłącznie osoby z dostępem. Historia utworzenia podzadania
przechowuje stabilne `metadata.subtask_pk`; czytelnik rodzica nie widzi wpisu
ujawniającego tytuł niedostępnego podzadania. Snapshot zawierający prywatne
zadanie jest prywatny autora i nie kopiuje członkostw.

Migracja `tasks/0060_task_sharing` zachowuje istniejące zadania jako publiczne
w odziedziczonym zakresie. Wiąże starsze wpisy utworzenia podzadania ze stabilnym
PK tylko przy zgodnym rodzicu, numerze i tytule. Niejednoznaczne lub nieaktualne
wpisy zachowuje jako zdarzenia bez tytułu i numeru podzadania. Regresje dostępu,
formularzy, migracji i integracji: `tasks/test_task_sharing.py`.

## Zaproszenia i ekran zespołu

Ekran `/workplaces/` pokazuje katalog Workspace, bez zakładki otrzymanych
zaproszeń. Skład zespołu znajduje się w zakładce
„Członkowie” okna „Edytuj miejsce pracy”, obok „Główna” z ustawieniami
i „Wysłane zaproszenia” z oczekującymi zaproszeniami do tego Workspace.
Nazwa Workspace i ikona ustawień otwierają „Główną”; liczba członków oraz stare
linki `?workspace=<pk>` / `?view=members&workspace=<pk>` otwierają „Członkowie”.
Okno wybranego Workspace jest renderowane nad katalogiem. Zarządzanie nim nie
zmienia aktywnej sesji ani kontekstu modułów. Znacznik „Bieżący” wskazuje
przestrzeń pracy; strzałka przełączenia nadal otwiera jej Zadania.
Zwykły członek ma okno „Miejsce pracy” z odczytem danych i składu zespołu,
bez akcji edycji, zapraszania, zmiany ról i odbierania dostępu.

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

Przestrzenie i tablice mają `visibility`, `private_owner` oraz `shared_with`
przez `KanbanProjectMembership` / `KanbanSectionMembership`. Role i bezpośrednie
udostępnianie działają jak w Zadaniach: właściciel zmienia widoczność i role,
administrator udostępnia członkom/obserwatorom i odbiera im dostęp, członek edytuje,
a obserwator tylko przegląda. Role Workspace nie omijają prywatności.
„Publiczna” oznacza uczestników Workspace, a dla tablicy — uczestników przestrzeni.
Nie oznacza dostępu anonimowego przez Internet i nie uruchamia `SharedItem`.

Nowa przestrzeń i osobno tworzona tablica są domyślnie prywatne dla faktycznego
`request.user`. Pierwsza tablica nowej przestrzeni jest publiczna w jej obrębie.
Pole `user` przestrzeni/karty nadal wskazuje właściciela Workspace.
Migracja `kanban/0039_sharing.py` pozostawia stare dane publiczne.
Brak pola widoczności przy edycji zachowuje obecną wartość; brak właściciela
prywatnego elementu zamyka dostęp także dawnym członkom.

Kandydat tablicy musi mieć dostęp do przestrzeni i być aktywnym członkiem Workspace.
Prywatna tablica zawęża dostęp przestrzeni, a karty, pliki i podkarty dziedziczą
ograniczenia tablicy oraz wszystkich rodziców. Rola obserwatora przestrzeni
zachowuje ograniczenie nawet dla właściciela tablicy. Nie ma osobnego udostępniania kart.
Usunięcie członka przestrzeni czyści jego udostępnienia tablic; odebranie lub
wyłączenie członkostwa Workspace czyści oba poziomy. Ponowne dodanie nie przywraca
starych uprawnień. Publikacja przestrzeni czyści jej członkostwa, ale zachowuje
niezależne prywatne tablice i ich członków.

Dostęp jest sprawdzany także w zwykłych i scoped URL, formularzach relacji,
wyszukiwaniu, Kalendarzu, metrykach, powiadomieniach, wzmiankach i pobieraniu plików.
Nowa historia utworzenia podkarty przechowuje `subtask_pk`. Stare zdarzenia tego
typu bez stabilnego PK są pomijane w odczycie, ponieważ zmienny `task_id` nie pozwala
bezpiecznie ustalić odbiorców historycznego tytułu. Pozostała historia pozostaje dostępna.

Usuwanie przestrzeni lub tablicy z prywatną zawartością wymaga wcześniejszego
usunięcia jej kart, aby `SET_NULL` nie ujawniło zawartości całemu Workspace.
Usuwanie rodzica jest blokowane, jeśli obejmowałoby niedostępną tablicę lub podkartę.

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
`workplaces/test_invitation_candidates.py` obejmuje podpowiedzi, limit, uprawnienia,
wykluczenia w wybranym Workspace, cofnięcie dostępu, escapowanie danych i ponowną
walidację zapisu po zmianie członkostwa.
