import {
  type CSSProperties,
  type PointerEvent,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from 'react';
import { Icon } from './Icon';
import {
  updateWidget,
  moveWidget,
  moveWidgetInOrder,
  resizeWidget,
  GRID_COLUMNS,
  GRID_GAP,
  ROW_HEIGHT,
  type SummaryWidget,
  type WidgetDirection,
} from '../spaces/summaryLayout';

export interface DashboardCanvasItem {
  id: string;
  label: string;
  icon?: string;
  min_w: number;
  min_h: number;
  is_metric?: boolean;
}

export interface DashboardCanvasProps {
  widgets: SummaryWidget[];
  catalog: DashboardCanvasItem[];
  editing: boolean;
  busy?: boolean;
  onChange: (widgets: SummaryWidget[]) => void;
  renderWidget: (id: string) => ReactNode;
  onNotice?: (message: string) => void;
  ariaLabel?: string;
}

export function DashboardCanvas({
  widgets,
  catalog,
  editing,
  busy = false,
  onChange,
  renderWidget,
  onNotice,
  ariaLabel = 'Gadżety pulpitu',
}: DashboardCanvasProps) {
  const [active, setActive] = useState<string | null>(null);
  const [stacked, setStacked] = useState(false);
  const grid = useRef<HTMLDivElement>(null);
  const gesture = useRef<{
    id: string;
    kind: 'move' | 'resize';
    pointer: number;
    x: number;
    y: number;
    stepX: number;
    stepY: number;
    widget: SummaryWidget;
    before: SummaryWidget[];
    scroll: HTMLElement | null;
    scrollTop: number;
  } | null>(null);
  useEffect(() => {
    const element = grid.current;
    if (!element) return;
    const measure = () => setStacked(element.clientWidth < 700);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const cancelGesture = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || !gesture.current) return;
      event.preventDefault();
      onChange(gesture.current.before);
      gesture.current = null;
      setActive(null);
      onNotice?.('Anulowano przeciąganie.');
    };
    document.addEventListener('keydown', cancelGesture);
    return () => document.removeEventListener('keydown', cancelGesture);
  }, [onChange, onNotice]);
  function move(id: string, direction: WidgetDirection) {
    if (!editing || busy || (stacked && (direction === 'left' || direction === 'right'))) return;
    onChange(
      stacked && (direction === 'up' || direction === 'down')
        ? moveWidgetInOrder(widgets, id, direction)
        : moveWidget(widgets, id, direction),
    );
    onNotice?.('Zmieniono pozycję gadżetu.');
  }
  function start(
    event: PointerEvent<HTMLButtonElement>,
    widget: SummaryWidget,
    kind: 'move' | 'resize',
  ) {
    if (!editing || busy || event.button !== 0 || !grid.current || grid.current.clientWidth < 700)
      return;
    event.preventDefault();
    const bounds = grid.current.getBoundingClientRect();
    const scale = bounds.width / grid.current.clientWidth;
    const scroll = grid.current.closest<HTMLElement>('.work-content');
    gesture.current = {
      id: widget.id,
      kind,
      pointer: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      stepX: (bounds.width + GRID_GAP * scale) / GRID_COLUMNS,
      stepY: (ROW_HEIGHT + GRID_GAP) * scale,
      widget,
      before: widgets,
      scroll,
      scrollTop: scroll?.scrollTop || 0,
    };
    grid.current.setPointerCapture(event.pointerId);
    setActive(widget.id);
  }
  function drag(event: PointerEvent<HTMLElement>) {
    const current = gesture.current;
    if (!current || event.pointerId !== current.pointer) return;
    const dx = Math.round((event.clientX - current.x) / current.stepX);
    const dy = Math.round(
      (event.clientY -
        current.y +
        (((current.scroll?.scrollTop || 0) - current.scrollTop) * current.stepY) /
          (ROW_HEIGHT + GRID_GAP)) /
        current.stepY,
    );
    onChange(
      current.kind === 'move'
        ? updateWidget(current.before, current.id, {
            x: current.widget.x + dx,
            y: current.widget.y + dy,
          })
        : resizeWidget(current.before, current.id, {
            w: current.widget.w + dx,
            h: current.widget.h + dy,
          }),
    );
  }
  function stop(event: PointerEvent<HTMLElement>, cancelled = false) {
    const current = gesture.current;
    if (!current || event.pointerId !== current.pointer) return;
    if (cancelled) onChange(current.before);
    gesture.current = null;
    setActive(null);
    onNotice?.(
      cancelled ? 'Anulowano przeciąganie.' : 'Zmieniono układ. Zapisz zmiany, aby je zachować.',
    );
  }

  const ordered = [...widgets].sort((a, b) => a.y - b.y || a.x - b.x);
  return (
    <div
      ref={grid}
      className="work-summary-canvas"
      onPointerMove={drag}
      onPointerUp={(event) => stop(event)}
      onPointerCancel={(event) => stop(event, true)}
      onLostPointerCapture={(event) => stop(event)}
      style={
        {
          '--summary-row-height': `${ROW_HEIGHT}px`,
          '--summary-grid-gap': `${GRID_GAP}px`,
        } as CSSProperties
      }
      aria-label={ariaLabel}
    >
      {(editing ? widgets : ordered).map((widget) => {
        const item = catalog.find((row) => row.id === widget.id);
        if (!item) return null;
        return (
          <section
            key={widget.id}
            data-summary-widget={widget.id}
            aria-label={item.label}
            className={`work-summary-widget ${item.is_metric ? 'is-metric' : ''} ${active === widget.id ? 'is-moving' : ''}`}
            style={{
              order: ordered.findIndex((row) => row.id === widget.id),
              gridColumn: `${widget.x + 1} / span ${widget.w}`,
              gridRow: `${widget.y + 1} / span ${widget.h}`,
            }}
          >
            {editing ? (
              <header className="work-summary-widget-tools">
                <button
                  type="button"
                  className="work-summary-drag-handle"
                  aria-label={`Przesuń: ${item.label}`}
                  title={
                    stacked ? 'Użyj strzałek w górę lub w dół' : 'Przeciągnij lub użyj strzałek'
                  }
                  disabled={busy}
                  onPointerDown={(event) => start(event, widget, 'move')}
                  onPointerMove={drag}
                  onPointerUp={(event) => stop(event)}
                  onPointerCancel={(event) => stop(event, true)}
                  onLostPointerCapture={(event) => stop(event)}
                  onKeyDown={(event) => {
                    if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key))
                      return;
                    event.preventDefault();
                    move(
                      widget.id,
                      event.key === 'ArrowUp'
                        ? 'up'
                        : event.key === 'ArrowDown'
                          ? 'down'
                          : event.key === 'ArrowLeft'
                            ? 'left'
                            : 'right',
                    );
                  }}
                >
                  <Icon name="grip-vertical" />
                  <span>{item.label}</span>
                </button>
              </header>
            ) : null}
            <div className="work-summary-widget-body">{renderWidget(widget.id)}</div>
            {editing ? (
              <button
                type="button"
                className="work-summary-resize-handle"
                disabled={busy}
                aria-label={`Zmień rozmiar: ${item.label}`}
                title="Przeciągnij lub użyj strzałek"
                onPointerDown={(event) => start(event, widget, 'resize')}
                onPointerMove={drag}
                onPointerUp={(event) => stop(event)}
                onPointerCancel={(event) => stop(event, true)}
                onLostPointerCapture={(event) => stop(event)}
                onKeyDown={(event) => {
                  if (!editing || busy) return;
                  if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key))
                    return;
                  event.preventDefault();
                  onChange(
                    resizeWidget(widgets, widget.id, {
                      w:
                        widget.w +
                        (event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1 : 0),
                      h:
                        widget.h +
                        (event.key === 'ArrowUp' ? -1 : event.key === 'ArrowDown' ? 1 : 0),
                    }),
                  );
                  onNotice?.('Zmieniono układ. Zapisz zmiany, aby je zachować.');
                }}
              >
                <Icon name="arrow-up-right" />
              </button>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}
