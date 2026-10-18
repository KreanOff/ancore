# Ancore — instrukcje pracy nad projektem

## Cel

Rozwijaj Ancore jako jedną spójną aplikację. Zachowuj istniejące mechanizmy,
architekturę, język interfejsu i wygląd przy realizacji kolejnych zadań.
Nowa funkcja ma korzystać z rozwiązań już obecnych w projekcie.
Redesign wykonuj wyłącznie wtedy, gdy użytkownik wyraźnie go zleci.

## Rozpoczęcie zadania

1. Przeczytaj [mapę dokumentacji](docs/README.md) i
   [architekturę](docs/ARCHITECTURE.md). Następnie wybierz rozdziały dotyczące zadania.
2. Przy zmianie UI przeczytaj [standard UI](docs/UI.md), obejrzyj najbliższy
   istniejący ekran i jego szablon, CSS oraz JavaScript.
3. Sprawdź `git status --short`. Zachowaj istniejące zmiany użytkownika.
4. Znajdź podobną implementację oraz wszystkich odbiorców zmienianego elementu.
   Do wyszukiwania używaj `rg`; do orientacji służy
   [indeks kodu](docs/CODE_INDEX.md).
5. Przy małym zadaniu doczytaj właściwy fragment kodu i jego zależności. Pełny
   przegląd wszystkich plików wykonuj, gdy wymaga tego zakres zadania.
6. Dokumentacja opisuje stan kodu, ale nie zastępuje jego sprawdzenia. W razie
   rozbieżności ustal aktualne zachowanie na podstawie routingu, wywołań i testów,
   a następnie popraw opis. Obecność klasy lub pola nie oznacza działającej funkcji.

## Architektura i mechanizmy, które trzeba zachować

- Kod Django i konfiguracja są w `backend/`; nowe aplikacje umieszczaj tam.
  Zachowuj importy `spaces`, `accounts`, `ancore.settings` itd., bez prefiksu
  `backend`. Główny `manage.py` dodaje katalog źródeł; inne procesy wymagają
  `PYTHONPATH` wskazującego `backend/`. `BASE_DIR` nadal oznacza katalog główny.
  Szablony, migracje i testy pozostają przy aplikacjach. Nie zmieniaj etykiet
  aplikacji ani nazw tabel przy porządkowaniu struktury.
- Dawne systemy Kontaktów, Tasks i osobnego Kanbana są całkowicie usunięte,
  łącznie z modelami, relacjami, migracjami i trasami. Nie przywracaj ich.
  Projekt używa nowego zestawu migracji początkowych na pustej bazie:
  [Baza danych](docs/DATABASE.md).
- Backend to Django i PostgreSQL. Frontend aktywnej aplikacji i wspólna powłoka
  korzystają z Reacta i TypeScriptu (`frontend/app`) oraz JSON API Django.
  `docs/FRONTEND.md` opisuje zakres i cykl życia. Szablony Django zachowują
  pierwszy render i zgodność; CSS i adaptery ikon/modali pozostają wspólne. Zasady migracji, API i budowania:
  [Frontend React](docs/FRONTEND.md). Zachowuj istniejące mechanizmy domenowe.
- Bieżące zadania należą do Przestrzeni: `spaces.SpaceTask`, `backend/spaces/views.py`
  i `backend/spaces/task_views.py`. Projekty, Grupy, starsze Zadania, Ulubione projekty
  i Szablony projektów są wycofane, podobnie Kanban. Nie przywracaj ich tras
  ani usuniętych implementacji historycznych widoków Tasks/Kanbana.
- Pakiet `tasks` zawiera wyłącznie bieżące `TaskTag` i `TaskTagNote`, obsługę
  tagów oraz współdzielone szablony. Przestrzenie i pozostałe moduły nadal
  korzystają z `static/js/tasks.js` oraz wspólnych komponentów CSS.
- Dane biznesowe ograniczaj do właściciela Workspace wyznaczonego przez
  `workplaces.services.workspace_owner(request)` i aktywnego `request.workplace`.
  Członkostwo daje dostęp do wspólnych danych Workspace; Przestrzenie, zadania
  i ich zawartość filtruj przez `spaces.access.visible_to(queryset, request.user)`.
  Formularze także ograniczają relacje.
  `request.user` pozostaje faktycznym autorem operacji, komentarzy i historii.
  Samo przypisanie wykonawcy nie daje dostępu. Zasady ról: `docs/TEAMWORK.md`.
- Korzystaj z mechanizmów `workplaces.services` do ustalania Workspace
  i budowania adresów. Sprawdź zwykłe oraz scoped adresy aplikacji.
- Bieżące zadania mają trwały `WorkItem.key` w obrębie Przestrzeni, oddzielony
  od klucza bazy `pk`. Usuwanie nie renumeruje kluczy; nie odtwarzaj dawnego
  mechanizmu `task_id` ani mapowań importu.
- Przy zmianie statusu zachowaj logikę zakończenia, historii i operacji zbiorczych.
  Bezpośrednie `QuerySet.update()` omija `save()` i sygnały modelu.
- Zachowaj walidację plików w `backend/core/upload_validation.py`, kontrolowane
  pobieranie i prywatny storage Dokumentów.
- Dostęp Przestrzeni i ich zadań wyznaczają `SpaceMembership` oraz
  `SpaceTaskMembership`, z ograniczeniami prywatnych rodziców.
  Role Przestrzeni są niezależne od ról Workspace.
- Nie traktuj `reminder_at`, `automation_rules`, `wip_limit` lub `is_done`
  jako dowodu istnienia automatyzacji. Sprawdź ich faktycznych odbiorców.

## Zasady UI

- Rozszerzaj `core/base.html`; ekrany uwierzytelniania mają własny
  `accounts/auth_base.html`. Zachowuj wspólną nawigację i kontenery.
- Używaj istniejących klas i include'ów przycisków, formularzy, tabel,
  toolbarów, paginacji, avatarów, ikon i modali.
- Przed dodaniem CSS sprawdź kolejno `base/variables.css`, plik komponentu,
  `theme/elestio.css`, `components/modal-system.css` i reguły w `style.css`.
  Końcowe reguły oraz `!important` mogą zmieniać styl komponentu.
- Kolory, fonty, wysokości i odstępy bierz z istniejących tokenów/wzorca.
  Nie dodawaj nowej palety, biblioteki ikon ani osobnego systemu kontrolek
  w ramach zwykłego dodawania funkcji.
- Obecny interfejs używa lokalnego Atlassian Sans (`--font-family-ui`),
  niewielkich rozmiarów tekstu, fioletowego akcentu MS Teams (`#5b5fc7`)
  i szarych interakcji.
  `style.css` wymusza w wielu miejscach wagę 400.
  Nazwy historyczne takie jak `--accent-red` nie określają faktycznego koloru.
- Modale projektów i zadań są wzorcem standardowego okna aplikacji.
  Zachowuj wspólną powłokę, obsługę fokusu, Escape, błędów i zapisu.
- Nową część JS inicjalizuj na pierwszym ładowaniu i, jeśli działa po
  podmianie treści, na `ancore:content-loaded`. Unikaj wielokrotnego
  podpinania listenerów. Korzystaj z istniejących API `AncoreIcons`,
  `AncoreCustomSelect` i `AncoreApp` tam, gdzie pasują.
- Jeśli brakuje wzorca, rozszerz najbliższy wspólny komponent o minimalny
  wariant. Nowy wariant opisz w dokumentacji; nie przebudowuj przy tym innych ekranów.
- Widoczny tekst interfejsu pisz po polsku, zgodnie z nazewnictwem modułu.

## Weryfikacja i zakończenie

- Dobierz sprawdzenia według [instrukcji developerskich](docs/DEVELOPMENT.md).
  Testuj zachowanie, granice dostępu oraz powiązane moduły zmienionego mechanizmu.
- Zmianę UI sprawdź w przeglądarce: ekran zmieniany, ekran referencyjny,
  istotne szerokości, stan pusty/błąd oraz ponowne wejście na ekran.
  Jeśli przeglądarka lub środowisko są niedostępne, opisz ten brak w podsumowaniu.
- Przy zmianie samych opisów sprawdź linki, zgodność ze źródłami oraz
  `python scripts/update_code_index.py --check`; nie trzeba uruchamiać
  całej aplikacji wyłącznie dla korekty dokumentacji.
- Przy zmianie modeli sprawdź migracje i ich obecność w Git. `.gitignore`
  nie może ignorować nowych plików migracji; lokalny katalog może mieć więcej
  migracji niż wersjonowane repozytorium.
- Aktualizuj odpowiedni rozdział dokumentacji w tym samym zadaniu, jeśli
  zmieniają się struktura, funkcje, uprawnienia, przepływ danych, UI albo uruchamianie.
  Odśwież indeks przez `python scripts/update_code_index.py`, gdy zmienia się
  jego zawartość. Nie zapisuj w dokumentacji sekretów ani danych użytkowników.
- W podsumowaniu podaj rezultat, zakres sprawdzenia i realne ograniczenia.
  Odróżniaj przegląd kodu od testów, które faktycznie wykonano.
