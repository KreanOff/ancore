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
nie omija prywatności Przestrzeni ani zadania. Gość Workspace ma wyłącznie odczyt dostępnych danych.

| Rola | Dostęp |
| --- | --- |
| Właściciel | Wspólne dane i własne i udostępnione prywatne przestrzenie; ustawienia Workspace; dodawanie istniejących kont oraz linki do dołączenia; zmiana ról i odbieranie dostępu; usunięcie Workspace zgodnie z dotychczasowym ograniczeniem ostatniej własnej przestrzeni |
| Administrator | Wspólne dane i własne i udostępnione prywatne przestrzenie; ustawienia Workspace; dodawanie istniejących kont jako członków lub gości, odbieranie im dostępu i zarządzanie linkami. Nie zmienia ról ani nie zarządza dostępem administratorów i właściciela |
| Członek | Tworzenie, odczyt, edycja i usuwanie wspólnych danych oraz własnych i udostępnionych prywatnych przestrzeni; lista zespołu. Bez zarządzania zespołem i ustawieniami Workspace |
| Gość | Wyłącznie odczyt wspólnych i udostępnionych prywatnych danych; konto i osobiste gwiazdki; bez zapisu danych zespołu |

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

## Role Filtrów

Role konkretnej definicji przechowuje `SavedTaskFilterMembership` w dotychczasowej
tabeli `dashboard_savedtaskfilter_shared_with`. Właścicielem jest twórca
`created_by`, a `owner` pozostaje granicą danych Workspace.

| Rola Filtra | Uprawnienia |
| --- | --- |
| Właściciel | Ustawienia, warunki, wszystkie role, widoczność i usunięcie; chroniony wiersz |
| Administrator | Ustawienia, warunki oraz udostępnianie i zmiana/odebranie ról członka i obserwatora; bez operacji na właścicielu/administratorach, widoczności i usuwaniu |
| Członek | Zapis warunków wyszukiwania; bez ustawień i zarządzania dostępem |
| Obserwator | Odczyt definicji i uruchamianie wyników we własnym zakresie danych |

Widoczność Workspace daje pozostałym osobom wyłącznie odczyt. Każda rola
wymaga aktywnego członkostwa Workspace; jego usunięcie/wyłączenie czyści role.
Cofnięcie roli obowiązuje przy kolejnym żądaniu, także z otwartego formularza.
Udostępnienie nigdy nie rozszerza dostępu do Przestrzeni i zadań.
Migracja zachowuje dotychczasowych odbiorców jako obserwatorów.

## Widoczność projektów Zadań

Dawne projekty usunięto. Bieżący zakres wyznaczają `SpaceMembership` i `spaces.access`.

## Widoczność i udostępnianie grup

Dawne grupy i ich członkostwa usunięto. Zadania należą bezpośrednio do Przestrzeni.

## Widoczność i udostępnianie zadań

Bieżące zadania używają `SpaceTaskMembership` oraz `spaces.task_team`.
Role i ograniczenia rodziców opisuje sekcja
[Dostęp do niezależnych zadań przestrzeni](#dostęp-do-niezależnych-zadań-przestrzeni-10102026).

## Dodawanie osób i linki do dołączenia

Ekran `/workplaces/` jest katalogiem z własnym menu „Zarządzanie Workspace”.
Okno wybranego Workspace ma zakładki „Główna” (`main`), „Członkowie” (`members`)
i — dla właściciela oraz administratora — „Linki do dołączenia” (`links`).
Nazwa i ikona ustawień otwierają „Główną”; liczba członków oraz stare linki
`?workspace=<pk>` / `?view=members&workspace=<pk>` otwierają „Członkowie”.
Zarządzanie wybranym Workspace nie przełącza aktywnego kontekstu. Znacznik
„Bieżący” wskazuje aktualne środowisko, a strzałka otwiera jego „Dla ciebie”.
Członek i gość odczytują ustawienia oraz skład bez operacji zarządzania.
Powrót do Ustawień lub wcześniejszego widoku zachowuje kontekst wejścia.

„Dodaj osobę” od razu nadaje dostęp istniejącemu, aktywnemu kontu Ancore.
Picker wyszukuje od 2 znaków imienia, drugiego imienia, nazwiska, ID konta lub
e-maila; pokazuje do 10 wyników z awatarem, nazwą i adresem. POST przekazuje
`user_id` wybranego konta. Bez JavaScriptu w zakładce „Członkowie” dostępny
jest zwykły formularz przyjmujący dokładne ID Ancore, np. `@jan.nowak`.
Sam adres e-mail nie tworzy członkostwa ani zaproszenia dla przyszłego konta.
Podpowiedzi pomijają właściciela, nieaktywne konta i aktywnych członków.
Administrator nie dostaje także kont z rolą administratora lub właściciela,
również przy nieaktywnym członkostwie. Zapis ponownie sprawdza konto,
członkostwo i uprawnienia pod blokadą Workspace; może reaktywować dozwolone,
nieaktywne członkostwo. GET `/workplaces/<pk>/team/candidates/` wymaga
zarządzania wybranym Workspace, nie zapisuje danych i nie jest cache'owany.

Właściciel dodaje konta oraz zmienia ich role na `admin`, `member` lub `guest`.
Administrator dodaje wyłącznie członków i gości oraz może odbierać im dostęp;
nie zmienia ról ani nie zarządza administratorem, także nieaktywnym.
Właściciel pozostaje chroniony. GET `/workplaces/<pk>/team/` przekierowuje do
katalogu, a POST dodaje osobę; sukces wraca do „Członkowie”, błąd zachowuje
formularz. Zmiana roli i odebranie dostępu pozostają w menu wiersza.
Operacje wymagają sesji i CSRF. Odebranie dostępu zachowuje treści zespołu,
czyści osobne udostępnienia i unieważnia sesje Office w całym Workspace;
pozostali użytkownicy ponownie otwierają pliki.

Jedynymi zaproszeniami są linki `WorkplaceInviteLink`. Właściciel lub
administrator wybiera rolę `member` albo `guest`, ważność 1–30 dni i limit
1–1000 użyć. Link pokazuje nazwę Workspace oraz rolę; jego posiadacz loguje
się lub rejestruje i potwierdza dołączenie przez POST. GET nie nadaje dostępu.
Nie ma ograniczenia domeny e-mail. Unieważnienie, wygaśnięcie lub wyczerpanie
limitu blokuje link. Blokady Workspace i linku serializują przyjęcia, a licznik
zwiększa się przy dodaniu nowego członka. Istniejący członek nie otrzymuje
wyższej roli. Rejestr `WorkplaceInviteLinkUse` zapobiega odzyskaniu odebranego
członkostwa tym samym wcześniej wykorzystanym linkiem; nieaktywne członkostwo
wymaga ponownego nadania dostępu przez zarządzającego.

Nie ma zaproszeń e-mail, oczekujących/wysłanych zaproszeń, okna decyzji ani
ich źródła, licznika lub oznaczenia pod dzwonkiem. Centrum powiadomień obejmuje
komentarze, wzmianki i osobiste przypomnienia zadań Przestrzeni. Dodawanie osób
i linki nie korzystają z SMTP. Stare trasy odpowiedzi, anulowania, ponowienia
wysyłki i dołączania przez token e-mail są usunięte; stare parametry katalogu
nie odtwarzają dawnego przepływu.

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

Pełny zestaw migracji tworzy bieżący schemat; [procedura bazy](DATABASE.md).
`dashboard.0007_remove_workspace_invitations` usuwa stany powiadomień
zaproszeń e-mail oraz relację `NotificationState.invitation`.
`workplaces.0005_remove_email_invitations` usuwa `WorkplaceInvitation`
ze wszystkimi oczekującymi, wysłanymi i historycznymi zaproszeniami.
Nie nadaje na ich podstawie dostępu; konta, istniejące członkostwa i treści
Workspace pozostają zachowane. Ta sama migracja usuwa `email_domain`
i unieważnia istniejące linki z ograniczeniem domeny, aby nie rozszerzyć dostępu.

Testy członkostwa, podpowiedzi i zarządzania znajdują się w
`backend/workplaces/test_team.py`, `test_management.py` oraz
`test_member_candidates.py` i `test_manual_members.py`. `test_read_only_documents.py` obejmuje
odczyt tekstowych Dokumentów przez gościa i odrzucenie zapisu.
`backend/dashboard/test_workspace_invitations.py` sprawdza wycofanie modelu,
tras, pól i źródła powiadomień; testy centrum i powłoki zachowują zakres
komentarzy, przypomnień, dostępu oraz snapshotów. Weryfikacja wymaga PostgreSQL.


## Dostęp do niezależnych zadań przestrzeni (10.10.2026)

Nowy system używa `SpaceMembership` i `SpaceTaskMembership`; role starszych
projektów, grup i zadań nie sterują jego bieżącymi uprawnieniami.
`spaces.access` sprawdza aktywne członkostwo Workspace, prywatność przestrzeni
i całe drzewo rodziców. Obserwator dowolnego poziomu ma wyłącznie odczyt.
Udostępnienie zadania nie udostępnia przestrzeni ani rodziców.

Właściciel prywatnego zadania zmienia widoczność i administratorów;
administrator zadania zarządza zwykłymi członkami i obserwatorami.
Zakładka „Członkowie” zadania pokazuje „Zmień rolę” i „Odbierz dostęp”
w dozwolonych wierszach zarówno właścicielowi, jak i administratorowi.
Administrator nie ma tych działań wobec właściciela ani innych administratorów;
członek i obserwator widzą tabelę bez operacji zarządzania.
Właściciel nie może otrzymać dodatkowego zwykłego członkostwa przez formularz
`members/` ani API. Serwer chroni go również przy zmianie i usuwaniu dawniej
utworzonego nadmiarowego rekordu. Usunięcie takiego rekordu nie odbiera
udostępnień prywatnych podzadań, ponieważ dostęp do rodzica nadal wynika
z jego własności.
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

Katalog i okna ustawień, członków oraz linków do dołączenia korzystają z React/TypeScript oraz
JSON API Django (`backend/workplaces/frontend.py`, `frontend/app/src/workspaces/`).
Reguły ról, transakcje i operacje domenowe pozostają w `views.py` oraz
`team_views.py`. Wybór do zarządzania nadal nie przełącza aktywnego Workspace.
Ustawienie domyślnego Workspace jest osobistą preferencją konta, dostępną
również członkowi i gościowi. Nie zmienia wspólnych danych, ról ani aktywnego
kontekstu. Logowanie wybiera wskazane środowisko dopiero po ponownym sprawdzeniu
członkostwa; usunięcie lub wyłączenie członkostwa uniemożliwia taki wybór.
Dodanie wybranego istniejącego konta od razu nadaje mu dostęp. Dołączenie
przez link wymaga potwierdzenia i przełącza kontekst osoby dołączającej.
API podpowiedzi osób udostępnia dane zamiast HTML. [Kontrakt migracji](FRONTEND.md).


## System Workspace (25.10.2026)

Rejestracja uwierzytelnia konto. Workspace powstaje wyłącznie po podaniu nazwy
albo użytkownik otrzymuje dostęp przez ręczne dodanie lub link do dołączenia. Pierwsze tworzenie blokuje wiersz
użytkownika i inicjalizuje właściciela, pulpit oraz gadżet w transakcji Django.
Nowy Workspace staje się aktywny; edycja ustawień wybranego środowiska nadal
nie zmienia kontekstu. Własność pozostaje pojedyncza (`Workplace.owner`).

Ekran `/accounts/register/workspace/` pokazuje pod przyciskiem tworzenia link
„Wybierz Workspace” do osobnej strony `/accounts/workspaces/` w powłoce kont.
Lista na tej stronie obejmuje własne Workspace i aktywne członkostwa,
także gościa; nie ujawnia obcych miejsc pracy ani nie nadaje członkostwa.
Oba ekrany GET pozostają dostępne również osobie mającej już Workspace. Wybór korzysta
z dotychczasowego POST `workplaces:switch`, który ponownie sprawdza dostęp.
Osoba z istniejącym Workspace może też jawnie utworzyć kolejny przez ten
formularz. Bez dostępnych środowisk widoczny jest komunikat pustej listy.

„Główna” okna Workspace pozwala wybrać włączone moduły: Przestrzenie i zadania,
Zespoły, Kalendarz, Dysk, Dokumenty, Zasoby, Pulpity i Filtry. Wyłączenie ukrywa
nawigację i blokuje bezpośrednie adresy oraz API modułu; dane pozostają w bazie.
Włączenie przywraca dostęp. Polityka działa też dla już otwartych ekranów.

Gość (`guest`) odczytuje wspólne oraz udostępnione mu prywatne dane. Nie tworzy,
nie edytuje i nie usuwa danych zespołu, niezależnie od ról Przestrzeni. Może
korzystać z konta, nawigacji i osobistych gwiazdek. Serwer blokuje także surowe
POST/PUT/PATCH/DELETE i delegowane API. ONLYOFFICE działa w trybie view,
callback starej sesji edycji sprawdza aktualną rolę oraz włączony moduł.
Tablica ma tryb podglądu. Tekstowy Dokument Ancore także otwiera się gościowi
w podglądzie: HTML przechodzi przez `clean_content`, pole treści nie jest
edytowalne, a zapis, Ctrl/⌘+S i akcje zmieniające dokument są niedostępne.
Wyjątek GET dla tekstu nie odblokowuje tworzenia ani metadanych plików.
Rola gościa dotyczy tylko jego dostępu; obecność gościa w Workspace nie
odbiera prawa zapisu właścicielowi, administratorowi ani członkowi.
Gwiazdki plików Dysku, folderów i Dokumentów są osobiste (`favorited_by`):
oznaczenie przez gościa lub członka zmienia wyłącznie jego własny katalog
i liczniki. Nie nadaje dostępu do elementu po usunięciu członkostwa Workspace.
Zasady ręcznego dodawania i linków opisuje sekcja
[Dodawanie osób i linki do dołączenia](#dodawanie-osób-i-linki-do-dołączenia).
