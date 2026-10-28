import {
  type CSSProperties,
  type PointerEvent,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from 'react';
import { EmptyState } from '../shared/EmptyState';
import { Icon } from '../shared/Icon';
import { Modal } from '../shared/Modal';
import { errorMessage } from '../shared/api';
import { pageRequest } from '../shared/page';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import { SummaryWidgetControls } from './SummaryWidgetControls';
import {
  addWidget,
  updateWidget,
  moveWidget,
  moveWidgetInOrder,
  resizeWidget,
  layoutsEqual,
  GRID_COLUMNS,
  GRID_GAP,
  ROW_HEIGHT,
  type SummaryWidget,
  type WidgetDirection,
} from './summaryLayout';

export interface SummaryDashboardData {
  revision: number;
  widgets: SummaryWidget[];
  columns: number;
  save_url: string;
  catalog: {
    id: string;
    label: string;
    icon: string;
    min_w: number;
    min_h: number;
    default_w: number;
    default_h: number;
  }[];
}

export default function SummaryDashboard({
  initial,
  api,
  csrfToken,
  readOnly,
  renderWidget,
  refresh,
  filters,
}: {
  initial: SummaryDashboardData;
  api: string;
  csrfToken: string;
  readOnly: boolean;
  renderWidget: (id: string) => ReactNode;
  refresh: () => Promise<void>;
  filters?: ReactNode;
}) {
  const [saved, setSaved] = useState(initial);
  const [draft, setDraft] = useState(initial.widgets);
  const [editing, setEditing] = useState(false);
  const [catalog, setCatalog] = useState(false);
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [active, setActive] = useState<string | null>(null);
  const [stacked, setStacked] = useState(false);
  const grid = useRef<HTMLDivElement>(null);
  const editButton = useRef<HTMLButtonElement>(null);
  const addButton = useRef<HTMLButtonElement>(null);
  const life = useRef(new AbortController());
  const pending = useRef(false);
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
  const dirty = !layoutsEqual(saved.widgets, draft);
  const hasWidgets = draft.length > 0;
  useDirtyGuard(editing && dirty, busy);
  useEffect(() => () => life.current.abort(), []);
  useEffect(() => {
    setSaved(initial);
    setDraft(initial.widgets);
  }, [initial]);
  useEffect(() => {
    const element = grid.current;
    if (!element) return;
    const measure = () => setStacked(element.clientWidth < 700);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [hasWidgets]);
  useEffect(() => {
    const cancelGesture = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || !gesture.current) return;
      event.preventDefault();
      setDraft(gesture.current.before);
      gesture.current = null;
      setActive(null);
      setNotice('Anulowano przeciąganie.');
    };
    document.addEventListener('keydown', cancelGesture);
    return () => document.removeEventListener('keydown', cancelGesture);
  }, []);
  function finishEditing() {
    setEditing(false);
    setCatalog(false);
    requestAnimationFrame(() => editButton.current?.focus());
  }
  function move(id: string, direction: WidgetDirection) {
    if (stacked && (direction === 'left' || direction === 'right')) return;
    setDraft((current) =>
      stacked && (direction === 'up' || direction === 'down')
        ? moveWidgetInOrder(current, id, direction)
        : moveWidget(current, id, direction),
    );
    setNotice('Zmieniono pozycję gadżetu.');
  }
  function cancel() {
    setDraft(saved.widgets);
    setError('');
    setNotice('Anulowano zmiany układu.');
    finishEditing();
  }
  async function save() {
    if (pending.current) return;
    if (!dirty) {
      finishEditing();
      return;
    }
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await pageRequest<{ dashboard: SummaryDashboardData }>(
        api,
        saved.save_url,
        csrfToken,
        life.current.signal,
        { revision: saved.revision, widgets: draft },
      );
      if (!life.current.signal.aborted) {
        setSaved(result.dashboard);
        setDraft(result.dashboard.widgets);
        setNotice('Układ pulpitu zapisany.');
        finishEditing();
      }
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      if (!life.current.signal.aborted) setBusy(false);
    }
  }
  async function reload() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      await refresh();
      if (!life.current.signal.aborted) {
        setNotice('Pulpit odświeżony.');
        finishEditing();
      }
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      if (!life.current.signal.aborted) setBusy(false);
    }
  }
  function start(
    event: PointerEvent<HTMLButtonElement>,
    widget: SummaryWidget,
    kind: 'move' | 'resize',
  ) {
    if (busy || event.button !== 0 || !grid.current || grid.current.clientWidth < 700) return;
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
      before: draft,
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
    setDraft(
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
    if (cancelled) setDraft(current.before);
    gesture.current = null;
    setActive(null);
    setNotice(
      cancelled ? 'Anulowano przeciąganie.' : 'Zmieniono układ. Zapisz zmiany, aby je zachować.',
    );
  }
  function change(widget: SummaryWidget, values: Partial<SummaryWidget>) {
    setDraft((current) => updateWidget(current, widget.id, values));
    setNotice('Zmieniono układ. Zapisz zmiany, aby je zachować.');
  }
  const ordered = [...draft].sort((a, b) => a.y - b.y || a.x - b.x);
  return (
    <div className={`work-summary-dashboard ${editing ? 'is-editing' : ''}`} aria-busy={busy}>
      <div className="work-summary-toolbar">
        <div className="work-summary-toolbar-title">
          {filters}
          {editing ? (
            <span className="work-caption">{dirty ? 'Niezapisane zmiany' : 'Tryb edycji'}</span>
          ) : null}
        </div>
        <div className="work-summary-toolbar-actions">
          {editing ? (
            <>
              <button
                ref={addButton}
                type="button"
                className="tasks-filter-button"
                disabled={busy}
                onClick={() => {
                  setQuery('');
                  setCatalog(true);
                }}
              >
                <Icon name="plus" />
                Dodaj gadżet
              </button>
              <button
                type="button"
                className="tasks-filter-button"
                disabled={busy}
                onClick={cancel}
              >
                Anuluj
              </button>
              <button
                type="button"
                className="tasks-filter-button work-summary-save"
                disabled={busy}
                onClick={() => void save()}
              >
                <Icon name="check" />
                {busy ? 'Zapisywanie…' : 'Zapisz układ'}
              </button>
            </>
          ) : (
            <>
              {!readOnly && saved.save_url ? (
                <button
                  ref={editButton}
                  type="button"
                  className="tasks-filter-button"
                  disabled={busy}
                  onClick={() => {
                    setEditing(true);
                    setError('');
                    setNotice('Włączono edycję pulpitu.');
                  }}
                >
                  <Icon name="pencil" />
                  Edytuj pulpit
                </button>
              ) : null}
            </>
          )}
        </div>
      </div>
      {editing ? (
        <p className="work-caption work-summary-edit-hint">
          <span className="work-summary-edit-hint-desktop">
            Przeciągnij kafelek za uchwyt, a jego rozmiar zmień w prawym dolnym rogu. Możesz też
            użyć strzałek na uchwycie lub menu kafelka.
          </span>
          <span className="work-summary-edit-hint-mobile">
            Dodawaj gadżety, a ich kolejność i rozmiar zmieniaj przez menu kafelka.
          </span>
        </p>
      ) : null}
      {error ? (
        <div className="tasks-modal__errors work-summary-error" role="alert">
          <span>{error}</span>
          <button
            type="button"
            className="tasks-filter-button"
            disabled={busy}
            onClick={() => {
              if (dirty)
                window.showConfirmModal({
                  title: 'Odśwież pulpit',
                  message: 'Odrzucić niezapisany układ i wczytać aktualną wersję?',
                  confirmText: 'Odrzuć i odśwież',
                  cancelText: 'Wróć do edycji',
                  onConfirm: () => void reload(),
                });
              else void reload();
            }}
          >
            Wczytaj aktualny układ
          </button>
        </div>
      ) : null}
      <span className="u-sr-only" role="status" aria-live="polite">
        {notice}
      </span>
      {draft.length ? (
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
          aria-label="Gadżety pulpitu przestrzeni"
        >
          {(editing ? draft : ordered).map((widget) => {
            const item = saved.catalog.find((row) => row.id === widget.id);
            if (!item) return null;
            return (
              <section
                key={widget.id}
                data-summary-widget={widget.id}
                aria-label={item.label}
                className={`work-summary-widget ${['completed', 'updated', 'created', 'due'].includes(widget.id) ? 'is-metric' : ''} ${active === widget.id ? 'is-moving' : ''}`}
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
                        if (
                          !['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)
                        )
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
                    <SummaryWidgetControls
                      widget={widget}
                      layout={draft}
                      label={item.label}
                      minWidth={item.min_w}
                      minHeight={item.min_h}
                      disabled={busy}
                      stacked={stacked}
                      onMove={(direction) => move(widget.id, direction)}
                      onResize={(size) => {
                        change(widget, {
                          ...size,
                          ...(size.w !== undefined
                            ? { x: Math.min(widget.x, GRID_COLUMNS - size.w) }
                            : {}),
                        });
                      }}
                      onRemove={() => {
                        const position = ordered.findIndex((row) => row.id === widget.id);
                        const next = ordered[position + 1] ?? ordered[position - 1];
                        setDraft((current) => current.filter((row) => row.id !== widget.id));
                        setNotice('Usunięto gadżet z układu.');
                        requestAnimationFrame(() => {
                          const trigger = next
                            ? grid.current?.querySelector<HTMLButtonElement>(
                                `[data-summary-widget="${CSS.escape(next.id)}"] .work-summary-widget-menu`,
                              )
                            : null;
                          (trigger ?? addButton.current)?.focus();
                        });
                      }}
                    />
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
                      if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key))
                        return;
                      event.preventDefault();
                      change(widget, {
                        w:
                          widget.w +
                          (event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1 : 0),
                        h:
                          widget.h +
                          (event.key === 'ArrowUp' ? -1 : event.key === 'ArrowDown' ? 1 : 0),
                      });
                    }}
                  >
                    <Icon name="arrow-up-right" />
                  </button>
                ) : null}
              </section>
            );
          })}
        </div>
      ) : (
        <EmptyState
          title="Ten pulpit jest pusty."
          description={
            readOnly
              ? 'W tym widoku nie dodano jeszcze gadżetów.'
              : 'Otwórz edycję pulpitu i wybierz gadżety, które chcesz tutaj wyświetlać.'
          }
          illustration="work"
        />
      )}
      {catalog ? (
        <Modal
          title="Dodaj gadżet"
          dialogClassName="work-summary-catalog-dialog"
          onClose={() => setCatalog(false)}
        >
          <div className="tasks-modal__body work-summary-catalog">
            <label className="u-sr-only" htmlFor="summary-widget-search">
              Szukaj gadżetu
            </label>
            <input
              id="summary-widget-search"
              className="form-input"
              type="search"
              placeholder="Szukaj gadżetu…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <div className="work-summary-catalog-list">
              {saved.catalog
                .filter((item) =>
                  item.label.toLocaleLowerCase('pl').includes(query.toLocaleLowerCase('pl')),
                )
                .map((item) => {
                  const added = draft.some((widget) => widget.id === item.id);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      className="work-summary-catalog-item"
                      disabled={added}
                      onClick={() => {
                        setDraft((current) =>
                          addWidget(current, { id: item.id, w: item.default_w, h: item.default_h }),
                        );
                        setNotice(`Dodano gadżet: ${item.label}.`);
                      }}
                    >
                      <Icon name={item.icon} />
                      <span>{item.label}</span>
                      <span className="work-caption">{added ? 'Dodano' : 'Dodaj'}</span>
                      <Icon name={added ? 'check' : 'plus'} />
                    </button>
                  );
                })}
              {!saved.catalog.some((item) =>
                item.label.toLocaleLowerCase('pl').includes(query.toLocaleLowerCase('pl')),
              ) ? (
                <p className="work-caption" role="status">
                  Brak pasujących gadżetów.
                </p>
              ) : null}
            </div>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
