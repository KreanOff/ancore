"""Grid placement shared by the dashboard API and its first render."""
import re

from .models import DashboardGadget

COLUMNS = 12
MAX_ROWS = 200
MIN_WIDTH = 4
MIN_HEIGHT = 5
MAX_HEIGHT = 16
DEFAULT_HEIGHT = 8
MAX_GADGETS = 24
GRID_FIELDS = ('x', 'y', 'w', 'h')
LAYOUT_WIDTHS = {'single': (12,), 'equal': (6, 6), 'left': (8, 4), 'right': (4, 8), 'three': (4, 4, 4)}


def overlaps(first, second):
    return (first['x'] < second['x'] + second['w'] and first['x'] + first['w'] > second['x']
            and first['y'] < second['y'] + second['h'] and first['y'] + first['h'] > second['y'])


def free_position(widgets, width=6, height=DEFAULT_HEIGHT):
    for y in range(MAX_ROWS - height + 1):
        for x in range(COLUMNS - width + 1):
            candidate = {'x': x, 'y': y, 'w': width, 'h': height}
            if not any(overlaps(candidate, widget) for widget in widgets):
                return candidate
    raise ValueError('Brak miejsca na nowy gadżet. Zmniejsz rozmiar lub usuń inny gadżet.')


def legacy_widgets(layout, columns):
    widths = LAYOUT_WIDTHS[layout]
    return [{'id': str(pk), 'x': sum(widths[:column]), 'y': index * DEFAULT_HEIGHT,
             'w': widths[column], 'h': DEFAULT_HEIGHT}
            for column, items in enumerate(columns) for index, pk in enumerate(items)]


def resolved_widgets(dashboard, gadgets):
    """Read older creations without writes, preserving explicit grid rectangles."""
    widgets = [{'id': str(gadget.pk), **{field: getattr(gadget, field) for field in GRID_FIELDS}}
               for gadget in gadgets if all(getattr(gadget, field) is not None for field in GRID_FIELDS)]
    columns = [[] for _ in range(dashboard.column_count)]
    for gadget in gadgets:
        columns[min(gadget.column, dashboard.column_count - 1)].append(gadget.pk)
    fallback = {widget['id']: widget for widget in legacy_widgets(dashboard.layout, columns)}
    present = {widget['id'] for widget in widgets}
    for gadget in gadgets:
        key = str(gadget.pk)
        if key in present:
            continue
        candidate = fallback[key]
        if any(overlaps(candidate, widget) for widget in widgets):
            candidate = {'id': key, **free_position(widgets, candidate['w'])}
        widgets.append(candidate)
    return sorted(widgets, key=lambda widget: (widget['y'], widget['x'], widget['id']))


def place_new_gadget(dashboard, gadget):
    widgets = resolved_widgets(dashboard, list(dashboard.gadgets.all()))
    rect = free_position(widgets, LAYOUT_WIDTHS[dashboard.layout][min(gadget.column, dashboard.column_count - 1)])
    for field, value in rect.items():
        setattr(gadget, field, value)


def validate_widgets(widgets, existing):
    if not isinstance(widgets, list) or len(widgets) > MAX_GADGETS:
        raise ValueError
    result, seen = [], set()
    for row in widgets:
        if not isinstance(row, dict) or not set(row).issubset({'id', 'kind', *GRID_FIELDS}):
            raise ValueError
        key = row.get('id')
        if not isinstance(key, str) or key in seen:
            raise ValueError
        gadget = existing.get(key)
        if gadget is None:
            if not re.fullmatch(r'new-[A-Za-z0-9_-]{1,64}', key) or row.get('kind') != DashboardGadget.Kind.PROGRESS:
                raise ValueError
        elif 'kind' in row and row['kind'] != gadget.kind:
            raise ValueError
        if any(type(row.get(field)) is not int for field in GRID_FIELDS):
            raise ValueError
        x, y, width, height = (row[field] for field in GRID_FIELDS)
        if not (0 <= x and 0 <= y and MIN_WIDTH <= width <= COLUMNS and MIN_HEIGHT <= height <= MAX_HEIGHT
                and x + width <= COLUMNS and y + height <= MAX_ROWS):
            raise ValueError
        if any(overlaps(row, previous) for previous in result):
            raise ValueError
        seen.add(key)
        result.append({'id': key, **{field: row[field] for field in GRID_FIELDS}})
    return result
