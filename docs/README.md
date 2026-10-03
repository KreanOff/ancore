# Mapa dokumentacji Ancore

Pierwszy przegląd źródeł: **15 września 2026**. Opis obejmuje lokalne drzewo
robocze, w tym moduł Dysku i jego integracje. Stan wdrożenia na serwerze
nie był ustalany. Przy zmianie zachowania aktualizuj odpowiedni rozdział.

## Szybkie wejście w projekt

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

Przestrzenie, wspólne zadania, sprinty i zespoły: [Przestrzenie](SPACES.md).

Praca zespołowa i role: [Workspace zespołu](TEAMWORK.md).

## Co czytać przed konkretnym zadaniem

| Zadanie | Opis i punkty wejścia |
| --- | --- |
| Nowe pole zadania/projektu | Moduły: Zadania; Mechanizmy: numeracja, zapis, słowniki; `tasks/models.py`, `tasks/forms.py`, `tasks/views/tasks.py` |
| Przestrzenie, zespoły, sprinty, wspólna tablica | [Przestrzenie](SPACES.md); `spaces/`, `static/js/spaces.js` |
| Historyczny Kanban, kolumna, przeciąganie | Moduły: Kanban; Mechanizmy: status/kolumna; `kanban/views/tasks.py`, `static/js/tasks.js` |
| Toolbar, tabela, modal, kolory | Cały standard UI; szablon referencyjny, wspólny CSS i odbiorcy wspólnego JS |
| Kontakty, firmy, profil | Odpowiedni moduł; Mechanizmy: tożsamość, dostęp, obrazy |
| Zasoby, ewidencja sprzętu i licencji | Moduły: Zasoby; `resources/`, wspólne filtry/paginacja w `static/js/tasks.js`, modale w `static/js/resources.js` |
| Nawigacja lub nowy moduł | Architektura; Mechanizmy: Workspace, URL i podmiana treści |
| Dysk i upload | Moduły: Dysk; Mechanizmy: pliki; `documents/`, `core/upload_validation.py` |
| Dokumenty i edycja treści | [Pełne edytory](OFFICE.md); `documents/editor_views.py`, `suite_views.py`, `office_service.py`, `frontend/board/` |
| Wyszukiwanie lub powiadomienia | Mechanizmy: wyszukiwanie i historia; `dashboard/views.py` oraz odpowiedni panel JS |
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
