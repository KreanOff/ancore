#!/usr/bin/env python3
"""Generate a local source inventory without importing Django or reading data."""

import argparse
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUTPUT = ROOT / "docs" / "CODE_INDEX.md"
SOURCE_SUFFIXES = {".py", ".html", ".css", ".js"}


def tree(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def code(node):
    return ast.unparse(node).replace("\n", " ")


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def link(path, label=None):
    relative = path.relative_to(ROOT).as_posix()
    return f"[{label or relative}](../{relative})"


def assignments(nodes):
    for node in nodes:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    yield target.id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                yield node.target.id, node.value


def keyword(call, name):
    return next((code(item.value) for item in call.keywords if item.arg == name), "")


def project_apps():
    settings = tree(BACKEND / "ancore" / "settings.py")
    configured = next(value for name, value in assignments(settings.body) if name == "INSTALLED_APPS")
    apps = []
    for name in ast.literal_eval(configured):
        # This project lists local app packages directly in INSTALLED_APPS.
        package = name.split(".")[0]
        if (BACKEND / package / "apps.py").is_file() and package not in apps:
            apps.append(package)
    return apps


def source_files(directory):
    return sorted(
        path for path in directory.rglob("*")
        if path.is_file()
        and path.suffix in SOURCE_SUFFIXES
        and "__pycache__" not in path.parts
    )


def test_file(path):
    return path.suffix == ".py" and (path.name == "tests.py" or path.name.startswith("test_"))


def model_section(path):
    lines = []
    classes = [node for node in tree(path).body if isinstance(node, ast.ClassDef)]
    if not classes:
        return ["Brak zadeklarowanych modeli domenowych w tym pliku.", ""]
    for model in classes:
        lines += [f"### `{model.name}`", "", f"Źródło: {link(path)}.", ""]
        fields = []
        relations = []
        for name, value in assignments(model.body):
            if not isinstance(value, ast.Call):
                continue
            kind = code(value.func)
            if not (kind.startswith("models.") or kind == "GenericForeignKey"):
                continue
            fields.append(f"`{name}` ({kind.removeprefix('models.')})")
            if kind in {"models.ForeignKey", "models.OneToOneField", "models.ManyToManyField", "GenericForeignKey"}:
                target = code(value.args[0]) if value.args else keyword(value, "to")
                extra = "; ".join(
                    f"{key}={keyword(value, key)}"
                    for key in ("on_delete", "related_name", "through", "null")
                    if keyword(value, key)
                )
                relations.append(f"| `{name}` | `{cell(target)}` | {cell(extra) or '—'} |")
        lines += ["Pola zadeklarowane tutaj: " + ", ".join(fields) + ".", ""]
        if relations:
            lines += ["| Relacja | Cel | Ustawienia |", "| --- | --- | --- |", *relations, ""]
        methods = [f"`{node.name}`" for node in model.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if methods:
            lines += ["Metody/properties: " + ", ".join(methods) + ".", ""]
    return lines


def route_section(path):
    lines = [f"### {path.relative_to(ROOT).as_posix()}", "", f"Źródło: {link(path)}.", ""]
    rows = []
    for node in ast.walk(tree(path)):
        if not isinstance(node, ast.Call) or code(node.func) not in {"path", "re_path"}:
            continue
        route = code(node.args[0]) if node.args else ""
        target = code(node.args[1]) if len(node.args) > 1 else ""
        rows.append(f"| `{cell(route)}` | `{cell(target)}` | {cell(keyword(node, 'name')) or '—'} |")
    return lines + ["| Ścieżka / regex | Widok / include | Nazwa |", "| --- | --- | --- |", *rows, ""]


def generate():
    apps = project_apps()
    roots = ["ancore", *apps]
    files_by_root = {name: source_files(BACKEND / name) for name in roots}
    lines = [
        "# Indeks kodu Ancore",
        "",
        "Plik generowany przez `python scripts/update_code_index.py`. Nie edytuj ręcznie.",
        "",
        "Zakres: lokalne źródła skonfigurowanych aplikacji i konfiguracja Django w `backend/` oraz",
        "zasoby `static/` i źródła React `frontend/app`. Uwzględnia pliki nieśledzone i ignorowane przez Git, jeśli",
        "są obecne lokalnie. Pomija sekrety, uploady, środowisko i cache Pythona.",
        "Generator nie importuje aplikacji ani nie łączy się z bazą.",
        "",
        "To katalog deklaracji, nie dowód dostępności funkcji lub wykonania testów.",
        "Pola odziedziczone, dynamiczny routing i semantyka helperów nie są",
        "odtwarzane. Aktywne zachowania i pozostałości opisują [Moduły](MODULES.md)",
        "oraz [Mechanizmy](MECHANISMS.md).",
        "",
        "## 1. Przegląd katalogów",
        "",
        "| Katalog | Python poza migracjami | Migracje bez init | Szablony HTML | Metody test_* |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, files in files_by_root.items():
        python = [p for p in files if p.suffix == ".py" and "migrations" not in p.parts]
        migrations = [p for p in files if "migrations" in p.parts and p.name != "__init__.py"]
        html = [p for p in files if p.suffix == ".html"]
        count = sum(
            sum(isinstance(n, ast.FunctionDef) and n.name.startswith("test_") for n in ast.walk(tree(p)))
            for p in python if test_file(p)
        )
        lines.append(f"| {link(BACKEND / name, 'backend/' + name)} | {len(python)} | {len(migrations)} | {len(html)} | {count} |")
    lines += ["", "## 2. Modele i relacje", ""]
    for app in apps:
        path = BACKEND / app / "models.py"
        if path.is_file():
            lines += [f"## Modele: {app}", "", *model_section(path)]

    lines += ["## 3. Formularze", "", "Wypisane są deklaracje klas, także bazowe klasy i widgety.", ""]
    for app in apps:
        path = BACKEND / app / "forms.py"
        if not path.is_file():
            continue
        lines += [f"### {app}", "", f"Źródło: {link(path)}.", ""]
        for node in tree(path).body:
            if not isinstance(node, ast.ClassDef):
                continue
            meta = next((n for n in node.body if isinstance(n, ast.ClassDef) and n.name == "Meta"), None)
            fields = dict(assignments(meta.body)).get("fields") if meta else None
            suffix = f" — Meta.fields: `{cell(code(fields))}`" if fields is not None else ""
            lines.append(f"- `{node.name}`{suffix}")
        lines.append("")

    lines += ["## 4. Routing", "", "Ścieżki modułowe są względne wobec include'a w głównym routingu.", ""]
    for name in roots:
        path = BACKEND / name / "urls.py"
        if path.is_file():
            lines += route_section(path)

    lines += ["## 5. Pliki backendu i punkty wejścia", "", "Lista funkcji jest statyczna; obejmuje też historyczne, nieużywane helpery.", ""]
    for name, files in files_by_root.items():
        lines += [f"### {name}", ""]
        for path in files:
            if path.suffix != ".py" or "migrations" in path.parts or test_file(path):
                continue
            nodes = tree(path).body
            public = [n.name for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("_")]
            suffix = " — " + ", ".join(f"`{n}`" for n in public) if public else ""
            lines.append(f"- {link(path)}{suffix}")
        lines.append("")

    lines += ["## 6. Szablony", ""]
    for name, files in files_by_root.items():
        templates = [path for path in files if path.suffix == ".html"]
        if templates:
            lines += [f"### {name}", "", *[f"- {link(path)}" for path in templates], ""]

    lines += ["## 7. Zasoby frontendowe", ""]
    for kind in ("css", "js", "img"):
        paths = sorted(p for p in (ROOT / "static" / kind).rglob("*") if p.is_file())
        lines += [f"### {kind}", "", *[f"- {link(path)}" for path in paths], ""]
    frontend = ROOT / "frontend" / "app"
    paths = sorted(path for path in frontend.rglob("*") if path.is_file()
                   and "node_modules" not in path.parts
                   and path.suffix in {".ts", ".tsx", ".mjs", ".json", ".yaml"})
    lines += ["### React — frontend/app", "", *[f"- {link(path)}" for path in paths], ""]

    lines += ["## 8. Testy", "", "Liczby dotyczą definicji metod, nie uruchomionych przypadków.", ""]
    for files in files_by_root.values():
        for path in files:
            if not test_file(path):
                continue
            lines += [f"### {path.relative_to(ROOT).as_posix()}", "", f"Źródło: {link(path)}.", ""]
            for node in tree(path).body:
                if isinstance(node, ast.ClassDef):
                    count = sum(isinstance(n, ast.FunctionDef) and n.name.startswith("test_") for n in node.body)
                    lines.append(f"- `{node.name}`: {count} metod testowych.")
            lines.append("")

    lines += ["## 9. Migracje obecne lokalnie", "", "Obecność na tej liście nie oznacza śledzenia w Git lub zastosowania w bazie.", ""]
    for name, files in files_by_root.items():
        migrations = [path for path in files if "migrations" in path.parts and path.name != "__init__.py"]
        if migrations:
            lines += [f"### {name}", "", *[f"- {link(path)}" for path in migrations], ""]
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the generated index is outdated.")
    args = parser.parse_args()
    result = generate()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != result:
            print("Indeks nieaktualny. Uruchom: python scripts/update_code_index.py")
            return 1
        print("Indeks kodu jest aktualny.")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(result, encoding="utf-8")
    print(f"Zapisano {OUTPUT.relative_to(ROOT)} ({len(result.splitlines())} linii).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
