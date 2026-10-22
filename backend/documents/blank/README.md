# Puste pliki

`new.pdf` to pusta strona A4 wygenerowana lokalnie przez ReportLab (bez pól,
skryptów, danych użytkownika i zależności ReportLab w aplikacji).

`new-form.pdf` to pusty wzorzec formularza z używanego obrazu
`onlyoffice/documentserver:9.4.0`, użytego przy tworzeniu wzorca:
`/var/www/onlyoffice/documentserver/document-templates/new/pl-PL/new.pdf`.
Zachowuje natywną strukturę formularza ONLYOFFICE. Nie należy zastępować go
zwykłym PDF-em ani spłaszczać. Pole `document.isForm=true` otwiera projektowanie
formularza. Wzorzec jest pusty; pola dodaje użytkownik w edytorze.

Oba pliki sprawdzono parserem PDF i renderowaniem: jedna pusta strona A4.
DOCX/XLSX/PPTX pozostają dotychczasowymi pustymi plikami projektu.
