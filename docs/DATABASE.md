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
przypomnienie Przestrzeni albo zaproszenie Workspace. Dostęp i edycja
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
