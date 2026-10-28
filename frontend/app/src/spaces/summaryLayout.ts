export type SummaryWidget = { id: string; x: number; y: number; w: number; h: number };
export type WidgetPatch = Partial<Pick<SummaryWidget, 'x' | 'y' | 'w' | 'h'>>;
export type WidgetDirection = 'left' | 'right' | 'up' | 'down';
export type WidgetSize = Partial<Pick<SummaryWidget, 'w' | 'h'>>;

export const GRID_COLUMNS = 12;
export const ROW_HEIGHT = 48;
export const GRID_GAP = 12;
export const MAX_WIDGET_HEIGHT = 16;
export const MAX_GRID_ROWS = 200;

const metricIds = new Set(['completed', 'updated', 'created', 'due']);

export function widgetMinimum(id: string) {
  return metricIds.has(id) ? { w: 3, h: 2 } : { w: 4, h: 5 };
}

function integer(value: number, minimum: number, maximum: number) {
  return Math.max(minimum, Math.min(maximum, Number.isFinite(value) ? Math.round(value) : minimum));
}

export function clampWidget(widget: SummaryWidget): SummaryWidget {
  const minimum = widgetMinimum(widget.id);
  const w = integer(widget.w, minimum.w, GRID_COLUMNS);
  const h = integer(widget.h, minimum.h, MAX_WIDGET_HEIGHT);
  return {
    id: widget.id,
    x: integer(widget.x, 0, GRID_COLUMNS - w),
    y: integer(widget.y, 0, MAX_GRID_ROWS - h),
    w,
    h,
  };
}

export function widgetsOverlap(a: SummaryWidget, b: SummaryWidget) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

function sameWidget(a: SummaryWidget, b: SummaryWidget) {
  return a.id === b.id && a.x === b.x && a.y === b.y && a.w === b.w && a.h === b.h;
}

export function layoutsEqual(a: SummaryWidget[], b: SummaryWidget[]) {
  if (a.length !== b.length) return false;
  const byId = new Map(b.map((widget) => [widget.id, widget]));
  if (byId.size !== b.length || new Set(a.map((widget) => widget.id)).size !== a.length)
    return false;
  return a.every((widget) => {
    const other = byId.get(widget.id);
    return Boolean(other && sameWidget(widget, other));
  });
}

// Keep the manipulated widget fixed and settle its neighbours in their original
// spatial order. Gaps stay intentional; only collisions move widgets downwards.
// A change that would push any widget beyond the server limit is an atomic no-op.
export function updateWidget(layout: SummaryWidget[], id: string, changes: WidgetPatch) {
  const target = layout.find((widget) => widget.id === id);
  if (!target) return layout;
  const updated = clampWidget({ ...target, ...changes });
  if (sameWidget(target, updated)) return layout;

  const remaining = layout
    .map((widget, index) => ({ widget, index }))
    .filter(({ widget }) => widget.id !== id)
    .sort((a, b) => a.widget.y - b.widget.y || a.widget.x - b.widget.x || a.index - b.index);
  const positioned = [updated];
  const byId = new Map([[id, updated]]);
  for (const { widget } of remaining) {
    let next = widget;
    while (true) {
      const collisions = positioned.filter((placed) => widgetsOverlap(next, placed));
      if (!collisions.length) break;
      const y = Math.max(...collisions.map((placed) => placed.y + placed.h));
      if (y + next.h > MAX_GRID_ROWS) return layout;
      next = { ...next, y };
    }
    positioned.push(next);
    byId.set(next.id, next);
  }
  return layout.map((widget) => byId.get(widget.id)!);
}

export function moveWidget(layout: SummaryWidget[], id: string, direction: WidgetDirection) {
  const target = layout.find((widget) => widget.id === id);
  if (!target) return layout;
  return updateWidget(layout, id, {
    x: target.x + (direction === 'left' ? -1 : direction === 'right' ? 1 : 0),
    y: target.y + (direction === 'up' ? -1 : direction === 'down' ? 1 : 0),
  });
}

// On a stacked screen, position arrows change the visible card order. Shelves
// keep that exact order after swapping, including cards with different sizes.
export function moveWidgetInOrder(layout: SummaryWidget[], id: string, direction: 'up' | 'down') {
  const ordered = layout
    .map((widget, index) => ({ widget, index }))
    .sort((a, b) => a.widget.y - b.widget.y || a.widget.x - b.widget.x || a.index - b.index)
    .map(({ widget }) => widget);
  const index = ordered.findIndex((widget) => widget.id === id);
  const adjacent = index + (direction === 'up' ? -1 : 1);
  if (index < 0 || adjacent < 0 || adjacent >= ordered.length) return layout;
  [ordered[index], ordered[adjacent]] = [ordered[adjacent], ordered[index]];

  const positioned = new Map<string, SummaryWidget>();
  let x = 0;
  let y = 0;
  let shelfHeight = 0;
  for (const widget of ordered) {
    if (x + widget.w > GRID_COLUMNS) {
      x = 0;
      y += shelfHeight;
      shelfHeight = 0;
    }
    if (y + widget.h > MAX_GRID_ROWS) return layout;
    positioned.set(widget.id, { ...widget, x, y });
    x += widget.w;
    shelfHeight = Math.max(shelfHeight, widget.h);
  }
  return layout.map((widget) => positioned.get(widget.id)!);
}

// Resizing grows from the bottom-right corner without shifting the top-left
// anchor when the requested size reaches a canvas edge.
export function resizeWidget(layout: SummaryWidget[], id: string, size: WidgetSize) {
  const target = layout.find((widget) => widget.id === id);
  if (!target) return layout;
  const minimum = widgetMinimum(id);
  return updateWidget(layout, id, {
    w: integer(size.w ?? target.w, minimum.w, GRID_COLUMNS - target.x),
    h: integer(
      size.h ?? target.h,
      minimum.h,
      Math.min(MAX_WIDGET_HEIGHT, MAX_GRID_ROWS - target.y),
    ),
  });
}

export function addWidget(layout: SummaryWidget[], widget: { id: string; w?: number; h?: number }) {
  if (layout.some((existing) => existing.id === widget.id)) return layout;
  const minimum = widgetMinimum(widget.id);
  const candidate = clampWidget({
    id: widget.id,
    x: 0,
    y: 0,
    w: widget.w ?? minimum.w,
    h: widget.h ?? minimum.h,
  });
  // Row-major search reuses a removed widget's space before extending the grid.
  for (let y = 0; y + candidate.h <= MAX_GRID_ROWS; y++) {
    for (let x = 0; x + candidate.w <= GRID_COLUMNS; x++) {
      const placed = { ...candidate, x, y };
      if (!layout.some((existing) => widgetsOverlap(existing, placed))) return [...layout, placed];
    }
  }
  return layout;
}
