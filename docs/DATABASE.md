# Czysty schemat bazy danych

Od 18.10.2026 projekt ma nowy zestaw migracji początkowych, generowany
z aktualnych modeli. Zastępuje on całą poprzednią historię migracji aplikacji.
Migracje wbudowanych aplikacji Django pozostają standardowe.

Kolejne zmiany rozwijają ten schemat zwykłymi migracjami przyrostowymi.
`dashboard.0003_dashboard_preferences` (22.10.2026) dodaje ikonę, zakres
danych, listę Przestrzeni, opcjonalny zapisany filtr i interwał odświeżania.
Istniejące pulpity zachowują dane i dostęp: otrzymują ikonę pulpitu,
zakres Workspace i wyłączone odświeżanie. Po backupie zastosuj `manage.py migrate`.
Usunięcie filtra zeruje relację, zachowując wybrany tryb zakresu;
odczyt pokazuje wtedy niedostępne źródło zamiast rozszerzać dane.

`dashboard.0004_dashboard_emoji_library` zamienia osiem stałych wyborów ikony
na walidator lokalnego katalogu Fluent Emoji. Pole pozostaje `varchar(32)`;
nowe wybory zapisują Unicode, a wcześniejsze identyfikatory są obsługiwane
jako aliasy. Migracja zmienia wyłącznie stan Django (`sqlmigrate`: no-op),
bez SQL zmieniającego tabelę i bez przepisywania rekordów.

`dashboard.0005_dashboard_membership_roles` dodaje role udostępnienia Pulpitów.
`DashboardMembership` przejmuje istniejącą tabelę `dashboard_dashboard_shared_with`
bez jej odtwarzania ani kopiowania relacji. Zachowane są PK, odbiorcy i unikalność
pary pulpit/osoba. Migracja dodaje rolę `observer` wszystkim dotychczasowym
odbiorcom; data ich dołączenia pozostaje nieznana (`NULL`). Nowe udostępnienia
otrzymują datę i wybraną rolę. [Wzorzec migracji Django](https://docs.djangoproject.com/en/6.0/howto/writing-migrations/#changing-a-manytomanyfield-to-use-a-through-model).
Po backupie zastosuj `manage.py migrate`. Cofnięcie zachowuje odbiorców,
ale usuwa dodatkowe kolumny ról i dat.

`dashboard.0006_saved_filter_membership_roles` przejmuje istniejącą tabelę
`dashboard_savedtaskfilter_shared_with` przez `SavedTaskFilterMembership`,
zachowując jej identyfikator, PK relacji i odbiorców. Dodaje role i datę
według tego samego wzorca co Pulpity: dotychczasowi odbiorcy są obserwatorami
z nieznaną datą, a nowe udostępnienia zapisują datę. Cofnięcie usuwa dodatkowe
kolumny, zachowując relacje. Po backupie zastosuj `manage.py migrate`.

## Usunięcie zaproszeń e-mail (25.10.2026)

`dashboard.0007_remove_workspace_invitations` usuwa osobiste stany dawnych
zaproszeń i relację `NotificationState.invitation`. Komentarze, przypomnienia
i ich stany pozostają zachowane. `workplaces.0005_remove_email_invitations`
usuwa `WorkplaceInvitation` i pole domeny linków. Linki mające wcześniej
ograniczenie domeny zostają unieważnione, aby usunięcie warunku nie poszerzyło
ich zamierzonego dostępu; zwykłe linki i rejestr użyć pozostają zachowane.
Konta, aktywne członkostwa, role, zadania, dokumenty i identyfikatory Workspace
nie zmieniają się. Stare zaproszenia nie są przekształcane w członkostwa.
Cofnięcie migracji odtwarza schemat, ale nie przywraca usuniętych zaproszeń
ani stanów; odzyskanie tych danych wymaga backupu sprzed zmiany.

Migracje są przyrostowe dla bieżącego schematu. Przed zastosowaniem wykonaj
backup i sprawdź `manage.py migrate --plan`, następnie `manage.py migrate`.
Test `workplaces.test_email_retirement_migration` sprawdza upgrade istniejących
danych oraz zachowanie dostępu i zawartości. Testy nie stosują migracji do
lokalnej bazy użytkownika.

## Osobiste gwiazdki dokumentów (25.10.2026)

`documents.0003_personal_document_stars` zastępuje wspólne `is_starred`
relacją `favorited_by` dla `Document`, `Folder` i `WorkspaceDocument`.
Dotychczasowe oznaczone rekordy otrzymują gwiazdkę swojego właściciela;
stare pole nie przechowywało autora operacji. Migracja nie przypisuje tych
oznaczeń innym członkom Workspace. Zawartość, UUID, pliki, lokalizacje
i dostęp pozostają zachowane. Nieużywany `WorkspaceDocumentFolder`
nie zmienia schematu.

Cofnięcie odtwarza wspólny bool na podstawie oznaczenia właściciela.
Osobistych oznaczeń pozostałych użytkowników nie da się odwzorować w dawnym
schemacie; ich odzyskanie po cofnięciu wymaga backupu. Przed zastosowaniem
wykonaj backup i sprawdź `manage.py migrate --plan`, następnie
`manage.py migrate`. Testy `documents.test_personal_stars` sprawdzają
migrację istniejących danych i izolację osobistych oznaczeń.

## Zakres

Usunięto pakiety `backend/legacy` i `backend/kanban`, historyczne modele
pracy z `tasks`, ich członkostwa, zaproszenia, szablony, pliki i historię,
a także dawne subskrypcje i dostawy powiadomień w `dashboard`.
Zniknęły mapowania `Space.project`, `WorkItem.legacy_task`, `LegacyKanbanLink`
oraz wybór starego storage plików. Dawne adresy `/tasks/`, `/kanban/`
i `/contacts/`, także scoped, nie są rejestrowane.

`tasks` zawiera obecnie wyłącznie `TaskTag`, `TaskTagNote`, formularz,
obsługę katalogu tagów i współdzielone szablony. Tagi nadal należą do Przestrzeni.
`static/js/tasks.js` oraz wspólne CSS pozostają używane przez bieżące moduły.
Tablice Kanban i Scrum w Przestrzeniach działają na `SpaceTask`/`WorkItem`.

`NotificationState` wskazuje dokładnie jedno źródło: komentarz Przestrzeni,
przypomnienie Przestrzeni. Dostęp i edycja
korzystają bezpośrednio z `spaces.access`. Zmiana Workspace nie wykonuje
backfillu dawnych danych.

Pozostałe aplikacje zachowują swój aktualny schemat. Ten reset nie dodaje
nowych funkcji ani nie zmienia wyglądu interfejsu. Pliki uploadów nie należą
do resetu PostgreSQL i nie są kasowane przez zastosowanie migracji.

## Uruchomienie

Utwórz pustą, dedykowaną bazę PostgreSQL i ustaw jej nazwę w `DB_NAME`
w lokalnym `.env` (pozostałe zmienne: `DB_HOST`, `DB_PORT`, `DB_USER`,
`DB_PASSWORD`). Następnie:

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate --plan
.venv/bin/python manage.py migrate
.venv/bin/python manage.py makemigrations --check --dry-run
```

Nowa baza ma puste katalogi biznesowe i nie zawiera kont. Pierwsze konto
utwórz przez rejestrację; administratora opcjonalnie przez
`.venv/bin/python manage.py createsuperuser`.

Nowych migracji nie stosuj do poprzedniej bazy z dawną historią
`django_migrations` ani przez `--fake`. Przejście wymaga pustej bazy;
przed resetem zachowaj kopię PostgreSQL i potrzebnych uploadów.
Odtworzenie kopii starej bazy wymaga również kodu sprzed zmiany schematu.
Kopie lokalne trzymaj poza Git, np. w `.cache/database-backups/`.

## Weryfikacja

`accounts.0002_user_default_workplace` dodaje opcjonalny osobisty wybór Workspace
do konta. Istniejące konta zaczynają bez preferencji, a dane i identyfikatory
Workspace pozostają zachowane. Relacja ma `SET_NULL` przy usunięciu Workspace;
uprawnienia nadal wynikają z właściciela lub aktywnego członkostwa. Przed
zastosowaniem migracji na istniejącej bazie wykonaj standardowy backup.

Pełny runner `.venv/bin/python scripts/run_tests.py` tworzy osobną pustą
bazę, stosuje nowe migracje i testuje aktywne moduły. Regresje schematu
znajdują się w `core.test_schema_baseline`; testy dawnych przejść migracyjnych
zastąpiono czystym startem. Nie są już wspierane importy historycznych danych
Tasks/Kanbana przez usunięte migracje.
