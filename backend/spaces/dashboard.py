"""Personal Space dashboards; summary data keeps its existing access scope."""
import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from .models import Space, SpaceDashboardLayout
from .services import space_url, visible_spaces


COLUMNS = 12
MAX_ROWS = 200
MAX_HEIGHT = 16
METRICS = (
    ('completed', 'Zakończone', 'circle-check'),
    ('updated', 'Zaktualizowane', 'refresh-cw'),
    ('created', 'Utworzone', 'plus'),
    ('due', 'Zbliżające się terminy', 'calendar-days'),
)
PANELS = (
    ('statuses', 'Przegląd statusów', 'circle-dot'),
    ('activity', 'Ostatnia aktywność', 'activity'),
    ('priorities', 'Podział priorytetów', 'chart-column'),
    ('types', 'Typy zgłoszeń', 'layers'),
    ('workload', 'Obciążenie zespołu', 'users'),
    ('epics', 'Postęp epików', 'zap'),
)


def widget_catalog(space):
    metrics = [
        {'id': key, 'label': label, 'icon': icon, 'min_w': 3, 'min_h': 2, 'default_w': 3, 'default_h': 2}
        for key, label, icon in METRICS
    ]
    panels = [
        {'id': key, 'label': label, 'icon': icon, 'min_w': 4, 'min_h': 5,
         'default_w': 12 if key == 'workload' and space.kind != 'software' else 6, 'default_h': 6}
        for key, label, icon in PANELS if key != 'epics' or space.kind == 'software'
    ]
    return metrics + panels


def default_widgets(space):
    metrics = [{'id': key, 'x': index * 3, 'y': 0, 'w': 3, 'h': 2} for index, (key, _, _) in enumerate(METRICS)]
    panels = [
        {'id': key, 'x': index % 2 * 6, 'y': 2 + index // 2 * 6,
         'w': 12 if key == 'workload' and space.kind != 'software' else 6, 'h': 6}
        for index, (key, _, _) in enumerate(PANELS) if key != 'epics' or space.kind == 'software'
    ]
    return metrics + panels


def dashboard_payload(request, space, layout=None):
    if layout is None:
        layout = SpaceDashboardLayout.objects.filter(space=space, user=request.user).first()
    catalog = widget_catalog(space)
    allowed_ids = {row['id'] for row in catalog}
    # A later change of Space kind may remove epics from the available widgets.
    widgets = [dict(row) for row in layout.widgets if row['id'] in allowed_ids] if layout else default_widgets(space)
    return {'revision': layout.revision if layout else 0, 'widgets': widgets, 'catalog': catalog,
            'columns': COLUMNS, 'max_rows': MAX_ROWS, 'max_h': MAX_HEIGHT,
            'save_url': space_url(request, space, 'dashboard/layout/')}


def validate_widgets(space, widgets):
    catalog = {row['id']: row for row in widget_catalog(space)}
    if not isinstance(widgets, list) or len(widgets) > len(catalog):
        raise ValueError
    result = []
    occupied = set()
    seen = set()
    for row in widgets:
        if not isinstance(row, dict) or set(row) != {'id', 'x', 'y', 'w', 'h'}:
            raise ValueError
        key = row['id']
        if not isinstance(key, str) or key not in catalog or key in seen:
            raise ValueError
        if any(type(row[field]) is not int for field in ('x', 'y', 'w', 'h')):
            raise ValueError
        x, y, width, height = (row[field] for field in ('x', 'y', 'w', 'h'))
        if not (0 <= x < COLUMNS and 0 <= y < MAX_ROWS and catalog[key]['min_w'] <= width <= COLUMNS
                and catalog[key]['min_h'] <= height <= MAX_HEIGHT and x + width <= COLUMNS and y + height <= MAX_ROWS):
            raise ValueError
        cells = {(column, line) for column in range(x, x + width) for line in range(y, y + height)}
        if occupied & cells:
            raise ValueError
        occupied.update(cells)
        seen.add(key)
        result.append({'id': key, 'x': x, 'y': y, 'w': width, 'h': height})
    return result


@login_required
@require_POST
@transaction.atomic
def save_layout(request, pk):
    lookup = {'pk': pk} if isinstance(pk, int) else {'slug': pk}
    space = get_object_or_404(visible_spaces(request), **lookup)
    try:
        if request.content_type != 'application/json':
            raise ValueError
        payload = json.loads(request.body)
        if not isinstance(payload, dict) or type(payload.get('revision')) is not int or payload['revision'] < 0:
            raise ValueError
        widgets = validate_widgets(space, payload['widgets'])
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Nieprawidłowy układ pulpitu.'}, status=400)
    # Lock the parent too, so two first saves cannot both create revision one.
    Space.objects.select_for_update().get(pk=space.pk)
    get_object_or_404(visible_spaces(request), pk=space.pk)
    layout = SpaceDashboardLayout.objects.select_for_update().filter(space=space, user=request.user).first()
    if payload['revision'] != (layout.revision if layout else 0):
        return JsonResponse({'error': 'Pulpit zmieniono w innym oknie. Odśwież stronę przed kolejną zmianą.'}, status=409)
    if layout is None:
        layout = SpaceDashboardLayout(space=space, user=request.user)
    layout.widgets = widgets
    layout.revision += 1
    layout.save()
    dashboard = dashboard_payload(request, space, layout)
    return JsonResponse({'saved': True, 'revision': layout.revision, 'widgets': widgets, 'dashboard': dashboard})
