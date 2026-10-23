# Filtry zadań

Moduł Filtry udostępnia wyszukiwanie bieżących zadań Przestrzeni, zapisane
definicje wyszukiwania, osobiste ulubione i udostępnianie. Wykorzystuje istniejący
układ aplikacji, listy zadań, kontrolki wyboru i modale. Wyszukiwanie globalne
w nagłówku nadal służy do wyszukiwania różnych rodzajów obiektów.

## Przepływ użytkownika

„Wyszukaj zadania” w menu Filtrów otwiera widok o tej samej nazwie
z podstawowym formularzem: Przestrzeń, typ, status, priorytet,
wykonawca, tekst, tagi, zespół i sortowanie. Wiele wartości jednego pola łączy
się alternatywą, a różne pola koniunkcją. Wykonawca ma dodatkowe wartości
„Przypisane do mnie” i „Nieprzypisane”.

Samodzielny ekran „Wszystkie zadania” i jego pozycja menu są wycofane.
Zapisane osobiste skróty `tasks-all` pozostają w bazie, ale nie są wyświetlane
ani dostępne do dodania. Dawne `/spaces/items/` i scoped odpowiednik
przekierowują do wyszukiwania, przenosząc tekst, typ zgłoszenia, przypisanie
do mnie i numer strony. Wyniki ponownie sprawdzają bieżące ACL. Wyszukiwanie
globalne kieruje „Wyszukaj zadania” i „Moje zadania” do Filtrów.

Wyniki używają tej samej listy co zadania Przestrzeni: kolorowych,
zwijanych grup statusów i wierszy z checkboxem, priorytetem, statusem,
kluczem, tytułem, typem oraz licznikami tagów i załączników. Dotyczy to
także zapisanych filtrów. Grupy i ich liczniki obejmują bieżącą stronę;
sortowanie ustala kolejność zadań wewnątrz grup. Paginacja nadal obejmuje
całe wyszukiwanie. Checkboxy zaznaczają wiersze lokalnie.

Tryb zaawansowany pozwala zapisać warunki tekstowo. Przełączenie na podstawowy
jest dostępne wyłącznie dla zapytań, które można przedstawić bez utraty warunków.
Wyszukiwanie i paginacja zachowują zapytanie w URL. Błędne warunki pokazują
komunikat oraz pusty wynik; nie można ich zapisać jako filtr.

„Zapisz filtr” tworzy definicję z nazwą, opisem i widocznością; nowy filtr
automatycznie trafia do ulubionych twórcy. Przy zapisanym filtrze „Zapisz”
aktualizuje zmienione warunki, a „Zapisz jako” tworzy kopię. Edycja pozwala
zmienić również nazwę, opis i udostępnianie. „Wyczyść” zmienia bieżące
wyszukiwanie; definicja pozostaje zapisana do użycia „Zapisz”.
Wyniki są odczytywane na nowo przy każdym otwarciu filtra.

Tworzenie i ustawienia filtra otwierają duże wspólne okno, tak jak ustawienia
Przestrzeni i Pulpitów. Zakładka „Główna” zawiera nazwę, opis i warunki
wyszukiwania; „Dostępy” widoczność i odbiorców. Obie należą do jednego formularza:
przełączanie zachowuje szkice, a „Zapisz” atomowo zapisuje całą definicję i
podczas edycji pozostawia okno otwarte. Odpowiedź zawiera aktualną rewizję, więc kolejny zapis
w tym samym oknie zachowuje kontrolę konfliktów. Błąd odsłania właściwą zakładkę
i skupia nieprawidłowe pole; Escape i zamknięcie chronią niezapisany szkic.
Po zamknięciu zapisanych ustawień katalog odświeża się z zachowanymi kryteriami,
a wejście z menu bocznego zachowuje bieżący ekran. Zwykłe/scoped adresy edycji
oraz wariant zarządzania otwierają tę samą powłokę. Tworzenie i „Zapisz jako”
korzystają z tych samych zakładek; po utworzeniu zamykają okno i otwierają
zapisany filtr albo wracają do zwykłego katalogu z jego kryteriami.

Katalog „Filtry” zawiera zakładki Ulubione, Moje filtry, Udostępnione
i Wszystkie, wyszukiwanie nazw/opisów i paginację. Gwiazdka jest osobista.
Osobny ekran „Zarządzaj filtrami” jest usunięty wraz z własnym menu bocznym
oraz odnośnikami w Ustawieniach, nagłówku Filtrów, wyszukiwaniu i zwiniętym menu.
Stare zwykłe/scoped `/filters/manage/` przekierowują do zakładki „Moje filtry”
w zwykłym katalogu. Poprawna jawna zakładka, wyszukiwanie i numer strony pozostają
zachowane; dawne filtry widoczności/gwiazdki są ignorowane. API strony
oraz nawigacji zwracają ten sam docelowy adres.
Starsze `manage/new/` i `manage/<pk>/edit/` nadal obsługują formularze
z dotychczasową kontrolą twórcy i Workspace. W tle jest zwykły katalog,
a zapis/anulowanie zachowują jego zakładkę i wyszukiwanie. Adres `return_to`
prowadzący do wycofanego katalogu jest normalizowany również przy gwiazdce
oraz usuwaniu. Pozostałe zabezpieczenia lokalnego przekierowania są zachowane.
Ustawienia, dostępy, osobiste gwiazdki i usuwanie pozostają w menu konkretnego
filtra. Modele, zapisane definicje i wyniki zadań pozostają bez zmian.
Menu boczne ma nagłówek z plusem, sekcje „Oznaczone gwiazdką” i „Ostatnie”
oraz panel „Więcej filtrów”.
„+” otwiera duże okno tworzenia filtra nad bieżącą stroną, również w menu
zwiniętym. Osobny skrót „Wyszukaj zadania” nadal prowadzi do wyszukiwania.
Skróty mają wspólny limit sześciu pozycji; ulubione mają pierwszeństwo.
Ostatnie są układane według osobistych odwiedzin w aktywnym Workspace,
następnie według daty utworzenia. Wiersze pozwalają zmienić gwiazdkę
oraz otworzyć ustawienia własnego filtra. Operacja gwiazdki zachowuje
bieżący ekran, także poza modułem Filtry. „Więcej filtrów” korzysta ze wspólnego panelu
wyszukiwania Przestrzeni i prowadzi do wszystkich dostępnych definicji.
Usunięcie filtra usuwa jego definicję i ulubione, zachowując zadania.

## Dostęp i dane

[SavedTaskFilter](../backend/dashboard/models.py) zapisuje właściciela Workspace,
aktywny Workspace, faktycznego twórcę, nazwę, opis, zapytanie, widoczność,
odbiorców, ulubione, rewizję i daty. Widoczność może być prywatna,
dla wybranych aktywnych osób Workspace albo dla całego Workspace.
Wyłącznie twórca może edytować lub usuwać filtr; pozostali odbiorcy mogą
go uruchamiać, oznaczać gwiazdką i tworzyć własną kopię.

Definicje są ograniczone przez właściciela i aktywny Workspace.
Udostępnienie definicji nie przyznaje dostępu do zadań. Wynik zawsze zaczyna
się od istniejącego zakresu spaces.services.visible_items, obejmującego
aktualne ACL Przestrzeni, zadań i prywatnych rodziców. Cofnięcie dostępu do
filtra usuwa go także z widocznej listy ulubionych. Funkcja currentUser()
oznacza oglądającego, również przy filtrze utworzonym przez inną osobę.

Zapisy korzystają z POST, CSRF, transakcji i blokady wiersza. Rewizja wykrywa
równoczesną edycję: starszy formularz nie nadpisuje nowej definicji.
Zapytania kompilowane są do Django ORM; użytkownik nie podaje ścieżek ORM
ani surowego SQL. Historyczne Tasks i Kanban nie uczestniczą w wynikach.

## Obsługiwana składnia zaawansowana

Jest to ograniczony język inspirowany JQL. Nazwy pól i słowa kluczowe są
nieczułe na wielkość liter. Obsługiwane są nawiasy oraz AND, OR, NOT
z kolejnością NOT, AND, OR.

| Pole | Wartości |
| --- | --- |
| space (alias project) | identyfikator, klucz lub nazwa dostępnej Przestrzeni |
| status | kod lub nazwa statusu ze słownika Przestrzeni |
| priority | lowest, low, medium, high, urgent lub polska etykieta |
| type (issuetype, work_type) | kod lub nazwa typu ze słownika Przestrzeni |
| assignee, reporter | identyfikator, e-mail albo currentUser() |
| tag (labels, tags) | identyfikator lub nazwa tagu Przestrzeni |
| key | trwały klucz zadania, np. PRO-12 |
| text (summary) | fragment tytułu, opisu lub klucza (operator ~) |
| due (duedate), created | dzień ISO, względny czas albo startOfDay() |
| team, sprint | identyfikator lub nazwa |
| category (statuscategory) | new, in_progress, resolved, closed, reopened |

Pola wyboru i klucz obsługują =, !=, IN i NOT IN. Tekst używa ~ oraz !~,
a daty także <, <=, > i >=. IS EMPTY oraz IS NOT EMPTY są dostępne
dla pól dopuszczających brak wartości. Negatywne porównanie relacji lub daty
nie dopasowuje braku wartości; należy uwzględnić go jawnie przez IS EMPTY.
Wartości ze spacjami zamyka się w cudzysłowie; podwójny cudzysłów i ukośnik
można zapisać według reguł JSON.

~~~text
assignee = currentUser() AND category != closed ORDER BY priority DESC
space = PRO AND priority IN (high, urgent)
tag = Frontend AND tag = Pilne
(status = new OR assignee IS EMPTY) AND text ~ "logowanie"
due <= "2026-10-10" AND due IS NOT EMPTY
created >= -7d ORDER BY created DESC
~~~

Dzień ISO obejmuje cały dzień w strefie czasowej aplikacji. Wartość względna,
np. -7d, -2h, -1w albo -30m, jest liczona przy wykonaniu zapytania.
startOfDay() oznacza początek bieżącego dnia. ORDER BY obsługuje created,
due, key, priority, summary i status oraz ASC/DESC. Priorytet sortuje
według znaczenia, klucz według Przestrzeni i numeru, a puste wartości
trafiają na koniec; klucz bazy rozstrzyga remisy.

Parser ogranicza długość do 4000 znaków, liczbę tokenów do 600, zagnieżdżenie
do 20, listę IN do 100 wartości i sortowanie do 6 pól. Wyniki mają
paginację po 50 zadań. Nie ma pełnej zgodności JQL, wtyczek funkcji,
subskrypcji e-mail, harmonogramu wykonywania ani filtrowania historycznych modeli.

## Routing i implementacja

Adresy zwykłe i scoped są równoważne:

- /filters/ — katalog definicji;
- /filters/manage/ — zarządzanie własnymi definicjami w Ustawieniach;
- /filters/manage/new/, manage/<pk>/edit/ — modal tworzenia/edycji nad zarządzaniem;
- /filters/search/ — niezapisane wyszukiwanie;
- /filters/lookup/ — wyszukiwanie definicji dla panelu menu (JSON);
- /filters/new/ — utworzenie;
- /filters/<pk>/ — wynik zapisanej definicji;
- /filters/<pk>/edit/ — edycja;
- /filters/<pk>/save/, favorite/, delete/ — akcje POST;
- /workplaces/<slug>/filters/... — wariant aktywnego Workspace.

Źródła: [routing](../backend/dashboard/filter_urls.py),
[widoki](../backend/dashboard/filter_views.py), [zakres definicji](../backend/dashboard/filters.py),
[formularze](../backend/dashboard/filter_forms.py),
[parser i kompilator](../backend/dashboard/filter_search.py),
[szablony](../backend/dashboard/templates/dashboard/filters),
[JS](../static/js/task-filters.js), [CSS](../static/css/components/task-filters.css),
[nawigacja menu](../static/js/filter-navigation.js),
[testy](../backend/dashboard/test_filters.py).

Ekrany katalogu i wyników oraz modale są renderowane przez
[React](../frontend/app/src/filters/SearchPage.tsx) i
[jawny serializer](../backend/dashboard/filter_frontend.py). JSON API deleguje zapis
do tych samych widoków i formularzy, zachowując ACL, rewizje i transakcje.
`task-filters.js` pozostaje obsługą zgodności szablonów i pomija korzeń Reacta.
Globalny pasek boczny i jego picker nadal korzystają z dotychczasowych skryptów.
Budowanie oraz granice migracji: [FRONTEND.md](FRONTEND.md).

Schemat tworzą [migracje początkowe](../backend/dashboard/migrations/0001_initial.py).
Wymagają pustej bazy; [zasady uruchomienia](DATABASE.md).
Przed uruchomieniem kodu na innym środowisku należy wykonać manage.py migrate.
