# Mapa dokumentacji Ancore

Aktualny schemat po usunięciu starych systemów: [Baza danych](DATABASE.md).

Pierwszy przegląd źródeł: **15 września 2026**. Opis obejmuje lokalne drzewo
robocze, w tym moduł Dysku i jego integracje. Stan wdrożenia na serwerze
nie był ustalany. Przy zmianie zachowania aktualizuj odpowiedni rozdział.

## Szybkie wejście w projekt

Kod Django znajduje się w `backend/`, frontend w `frontend/`, a wspólne zasoby
w `static/`. Główne instrukcje startu i mapa repozytorium są w
[README projektu](../README.md). Polecenia Django nadal uruchamiaj przez
`manage.py` w katalogu głównym. Importy Pythona zachowują dotychczasowe nazwy.

1. [Architektura](ARCHITECTURE.md) — czym jest aplikacja, drzewo katalogów,
   granice modułów, przepływ żądania i najważniejsze zależności.
2. [Moduły](MODULES.md) — dostępne funkcje, ekrany, dane i scenariusze użytkownika.
3. [Mechanizmy](MECHANISMS.md) — sposób działania sesji, Workspace, uprawnień,
   numeracji, historii, wyszukiwania, uploadu i nawigacji.
4. [UI](UI.md) — istniejący język wizualny, źródła stylów, referencje komponentów
   i sposób zachowania spójności.
5. [Praca developerska](DEVELOPMENT.md) — konfiguracja, testy, ograniczenia
   lokalnego repozytorium i utrzymanie dokumentacji.
6. [Pełne edytory Dokumentów](OFFICE.md) — ONLYOFFICE, tablica, zapis i uruchomienie.
7. [Indeks kodu](CODE_INDEX.md) — generowany katalog modeli, relacji,
   formularzy, tras URL, szablonów, zasobów i testów.

Instrukcje agenta znajdują się w [AGENTS.md](../AGENTS.md). Ten plik kieruje
do szczegółowych opisów i wymaga zachowania istniejących wzorców.

Przestrzenie, niezależne zadania `SpaceTask`, sprinty i zespoły: [Przestrzenie](SPACES.md).

Praca zespołowa i role: [Workspace zespołu](TEAMWORK.md).

Frontend React, budowanie i API Django: [Frontend React](FRONTEND.md).

Wyszukiwanie zadań, zapisane filtry i udostępnianie: [Filtry](FILTERS.md).

## Co czytać przed konkretnym zadaniem

| Zadanie | Opis i punkty wejścia |
| --- | --- |
| Nowe pole zadania | [Przestrzenie](SPACES.md); `backend/spaces/models.py`, `backend/spaces/forms.py`, `backend/spaces/task_views.py` |
| Wycofane Projekty, Grupy, Zadania, Ulubione projekty i Szablony | Moduły: historyczne Tasks; `backend/tasks/models.py`, `backend/core/test_schema_baseline.py` |
| Przestrzenie, własne zadania, zespoły, sprinty | [Przestrzenie](SPACES.md); `backend/spaces/`, `static/js/spaces.js` |
| Wycofany Kanban i stare linki | Moduły: wycofany Kanban; Przestrzenie: migracja; `backend/core/test_schema_baseline.py`, [Baza danych](DATABASE.md) |
| Toolbar, tabela, modal, kolory | Cały standard UI; szablon referencyjny, wspólny CSS i odbiorcy wspólnego JS |
| Logowanie i profil | Moduły: Accounts; Mechanizmy: tożsamość, dostęp, obrazy; [API kont React](FRONTEND.md#api-i-interfejs-kont) |
| Zasoby, ewidencja sprzętu i licencji | Moduły: Zasoby; `backend/resources/`, wspólne filtry/paginacja w `static/js/tasks.js`, modale w `static/js/resources.js` |
| Nawigacja lub nowy moduł | Architektura; Mechanizmy: Workspace, URL i podmiana treści |
| React, JSON API i migracja frontendu | [Frontend React](FRONTEND.md); `frontend/app/`, `backend/core/frontend.py`, `backend/core/api.py`, domenowe `frontend.py` |
| Dysk i upload | Moduły: Dysk; Mechanizmy: pliki; `backend/documents/`, `backend/core/upload_validation.py` |
| Dokumenty i edycja treści | [Pełne edytory](OFFICE.md); `backend/documents/editor_views.py`, `suite_views.py`, `office_service.py`, `frontend/board/` |
| Wyszukiwanie lub powiadomienia | Mechanizmy: wyszukiwanie i historia; `backend/dashboard/views.py` oraz odpowiedni panel JS |
| Baza, migracje, środowisko | Praca developerska; modele i odpowiednie testy migracyjne |

## Jak interpretować opis

- **Dostępne:** istnieje aktywna ścieżka URL/akcja i implementacja.
- **Przechowywane dane:** pole można zapisać, ale nie oznacza to automatycznego
  działania w tle, dostępu dla innego konta ani dodatkowej integracji.
- **Pozostałość/wyłączone:** symbol jest w kodzie, ale aktywna aplikacja z niego
  nie korzysta lub zwraca pusty wynik. Przykłady są w Modułach i Mechanizmach.
- **Zasada dalszej pracy:** zalecenie utrzymania spójności, a nie twierdzenie,
  że cały historyczny kod już je spełnia.

Opisy działania wynikają z przeglądu kodu i istniejących testów. Przegląd pliku
testowego nie oznacza wykonania testu. UI opisano na podstawie szablonów, CSS
i JS; pierwszy przegląd nie obejmował audytu wszystkich ekranów w przeglądarce.

## Utrzymywanie aktualności

Aktualizuj opisy w tym samym zadaniu co kod. Schemat aktualizacji i macierz
wpływu są w [DEVELOPMENT.md](DEVELOPMENT.md). Indeks odświeża polecenie:

```sh
python scripts/update_code_index.py
python scripts/update_code_index.py --check
```

Generator czyta wyłącznie źródła, nie uruchamia Django i nie łączy się z bazą.
Indeks pomaga znaleźć implementację; nie rozstrzyga, czy funkcja jest aktywna.
