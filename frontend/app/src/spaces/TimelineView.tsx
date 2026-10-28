import {
  type CSSProperties,
  type PointerEvent,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Avatar } from '../shared/Avatar';
import { EmptyState } from '../shared/EmptyState';
import { Icon } from '../shared/Icon';
import { Modal } from '../shared/Modal';
import { errorMessage, request } from '../shared/api';
import { navigate } from '../shared/page';
import { ItemToolbar } from './ItemToolbar';
import type { DetailData, Item } from './types';
import {
  dayKey,
  dayLabel,
  parseDay,
  shiftTask,
  taskGeometry,
  timelineHeaders,
  timelineWindow,
  todayDay,
  type DayRange,
  type TimelineScale,
} from './timeline';

const SCALES: [TimelineScale, string][] = [
  ['weeks', 'Tygodnie'],
  ['months', 'Miesiące'],
  ['quarters', 'Kwartały'],
];
function itemRange(item: Item): DayRange | null {
  const start = parseDay(item.start_on),
    end = parseDay(item.end_on ?? null);
  if (start === null && end === null) return null;
  return { start: start ?? end!, end: Math.max(start ?? end!, end ?? start!) };
}
function dateSummary(item: Item) {
  const start = parseDay(item.start_on),
    end = parseDay(item.end_on ?? null);
  return `${start === null ? 'Bez początku' : dayLabel(start)} → ${end === null ? 'Bez terminu' : dayLabel(end)}`;
}
function movedDates(item: Item, range: DayRange, mode: 'move' | 'start' | 'end') {
  return [
    item.start_on || mode === 'start' ? dayKey(range.start) : '',
    item.end_on || mode === 'end' ? dayKey(range.end) : '',
  ] as const;
}
interface Props {
  data: DetailData;
  url: string;
  csrfToken: string;
  busy: boolean;
  onUpdate: (item: Item) => void;
}
interface Gesture {
  item: Item;
  range: DayRange;
  preview: DayRange;
  mode: 'move' | 'start' | 'end';
  x: number;
  scroll: number;
  zoom: number;
  moved: boolean;
  pointerId: number;
  element: HTMLElement;
}
export default function Timeline({ data, url, csrfToken, busy, onUpdate }: Props) {
  const [scale, setScale] = useState<TimelineScale>('weeks');
  const [anchor, setAnchor] = useState(() => {
    const dates = data.items.flatMap((item) => {
      const range = itemRange(item);
      return range ? [range.start] : [];
    });
    return dates.length ? Math.min(...dates) : todayDay();
  });
  const [query, setQuery] = useState(data.filters.q || '');
  const [editing, setEditing] = useState<Item | null>(null);
  const [saving, setSaving] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [preview, setPreview] = useState<{ id: number; range: DayRange } | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const gesture = useRef<Gesture | null>(null);
  const pending = useRef(false);
  const life = useRef(new AbortController());
  const center = useRef<number | null>(anchor);
  const suppressClick = useRef(false);
  const [scrollRevision, setScrollRevision] = useState(0);
  const window = useMemo(() => timelineWindow(scale, anchor), [scale, anchor]);
  const headers = useMemo(() => timelineHeaders(window), [window]);
  const today = todayDay();
  const todayLeft = (today - window.start + 0.5) * window.dayWidth;
  const todayVisible = today >= window.start && today < window.end;
  const locked = busy || saving !== null;
  const sprints =
    data.space.template === 'scrum'
      ? data.sprints.filter(
          (sprint) =>
            sprint.state !== 'closed' &&
            parseDay(sprint.start_on) !== null &&
            parseDay(sprint.end_on) !== null,
        )
      : [];
  function availableWidth() {
    const table = viewport.current?.querySelector<HTMLElement>('.work-timeline-table');
    const metadata = table
      ? parseFloat(getComputedStyle(table).getPropertyValue('--timeline-meta'))
      : 0;
    return Math.max(80, (viewport.current?.clientWidth || 1000) - metadata);
  }

  useEffect(() => {
    const cancel = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && gesture.current) {
        event.preventDefault();
        const current = gesture.current;
        gesture.current = null;
        current.element.releasePointerCapture?.(current.pointerId);
        suppressClick.current = true;
        setPreview(null);
        setNotice('Anulowano zmianę dat.');
      }
    };
    document.addEventListener('keydown', cancel);
    return () => {
      life.current.abort();
      document.removeEventListener('keydown', cancel);
    };
  }, []);
  useLayoutEffect(() => {
    if (center.current === null || !viewport.current) return;
    const available = availableWidth();
    viewport.current.scrollLeft = Math.max(
      0,
      (center.current - window.start) * window.dayWidth - Math.min(available / 3, 160),
    );
    center.current = null;
  }, [window, scrollRevision]);

  function focusDay(day: number, nextScale = scale) {
    center.current = day;
    setAnchor(day);
    setScale(nextScale);
    setScrollRevision((value) => value + 1);
  }
  function visibleDay() {
    return Math.min(
      window.end - 1,
      Math.max(
        window.start,
        Math.floor(
          window.start +
            ((viewport.current?.scrollLeft || 0) + availableWidth() / 2) / window.dayWidth,
        ),
      ),
    );
  }
  async function save(item: Item, start: string, end: string): Promise<boolean> {
    if (pending.current || busy || !item.editable || !item.update_dates_url) return false;
    pending.current = true;
    setSaving(item.id);
    setError('');
    setNotice(`Zapisuję daty ${item.key}.`);
    try {
      const result = await request<{
        start_on: string | null;
        end_on: string | null;
        due_at: string | null;
        due_urgency?: string;
      }>(item.update_dates_url, csrfToken, life.current.signal, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
        body: new URLSearchParams({
          start_on: start,
          end_on: end,
          source_start_on: item.start_on || '',
          source_due_at: item.due_at || '',
        }),
      });
      if (life.current.signal.aborted) return false;
      onUpdate({ ...item, ...result });
      setNotice(`Zapisano daty ${item.key}.`);
      return true;
    } catch (exception) {
      if (!life.current.signal.aborted) {
        const message = errorMessage(exception);
        setError(message);
        setNotice(`Nie zapisano dat ${item.key}. ${message}`);
      }
      return false;
    } finally {
      pending.current = false;
      if (!life.current.signal.aborted) {
        setSaving(null);
        setPreview(null);
      }
    }
  }
  function begin(event: PointerEvent<HTMLElement>, item: Item, mode: Gesture['mode']) {
    const range = itemRange(item);
    if (event.button !== 0 || locked || !item.editable || !range) return;
    event.stopPropagation();
    suppressClick.current = false;
    setSelected(item.id);
    const lane = event.currentTarget.closest<HTMLElement>('.work-timeline-lane');
    gesture.current = {
      item,
      range,
      preview: range,
      mode,
      x: event.clientX,
      scroll: viewport.current?.scrollLeft || 0,
      zoom: lane ? lane.getBoundingClientRect().width / lane.offsetWidth : 1,
      moved: false,
      pointerId: event.pointerId,
      element: event.currentTarget,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function move(event: PointerEvent<HTMLElement>) {
    const current = gesture.current;
    if (!current || event.pointerId !== current.pointerId) return;
    const deltaPx =
      (event.clientX - current.x) / current.zoom +
      (viewport.current?.scrollLeft || 0) -
      current.scroll;
    if (Math.abs(deltaPx) < 5 && !current.moved) return;
    current.moved = true;
    current.preview = shiftTask(current.range, Math.round(deltaPx / window.dayWidth), current.mode);
    setPreview({ id: current.item.id, range: current.preview });
  }
  function finish(event: PointerEvent<HTMLElement>, cancel = false) {
    const current = gesture.current;
    if (!current || event.pointerId !== current.pointerId) return;
    gesture.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
    suppressClick.current = current.moved || cancel;
    if (
      cancel ||
      !current.moved ||
      (current.range.start === current.preview.start && current.range.end === current.preview.end)
    ) {
      setPreview(null);
      return;
    }
    void save(current.item, ...movedDates(current.item, current.preview, current.mode));
  }
  function edit(item: Item) {
    setError('');
    setSelected(item.id);
    setEditing(item);
  }
  const style = {
    '--timeline-width': `${window.width}px`,
    '--timeline-day': `${window.dayWidth}px`,
    '--timeline-week': `${window.dayWidth * 7}px`,
    '--timeline-weekends': `linear-gradient(to right, ${headers.minor
      .flatMap((segment) => [
        `${segment.weekend ? 'color-mix(in srgb, var(--system-interaction) 5%, transparent)' : 'transparent'} ${segment.left}px`,
        `${segment.weekend ? 'color-mix(in srgb, var(--system-interaction) 5%, transparent)' : 'transparent'} ${segment.left + segment.width}px`,
      ])
      .join(', ')})`,
    '--timeline-grid': `linear-gradient(to right, ${headers.minor
      .flatMap((segment) => [
        `transparent ${segment.left}px`,
        `transparent ${Math.max(segment.left, segment.left + segment.width - 1)}px`,
        `var(--border-color) ${Math.max(segment.left, segment.left + segment.width - 1)}px`,
        `var(--border-color) ${segment.left + segment.width}px`,
      ])
      .join(', ')})`,
  } as CSSProperties;
  const todayLine = todayVisible ? (
    <span className="work-timeline-today-line" style={{ left: todayLeft }} aria-hidden="true" />
  ) : null;

  return (
    <section className="work-timeline" aria-label="Oś czasu zadań" style={style}>
      <div className="work-timeline-toolbar">
        <form
          className="tasks-search-field work-timeline-search"
          role="search"
          onSubmit={(event) => {
            event.preventDefault();
            const next = new URL(url, location.origin);
            query.trim() ? next.searchParams.set('q', query.trim()) : next.searchParams.delete('q');
            next.searchParams.delete('page');
            navigate(next.pathname + next.search);
          }}
        >
          <Icon name="search" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Szukaj na osi czasu"
            aria-label="Szukaj na osi czasu"
          />
          <button type="submit" className="tasks-filter-button" aria-label="Szukaj zadań">
            <Icon name="arrow-right" />
          </button>
        </form>
        <ItemToolbar data={data} url={url} />
      </div>
      {error && !editing ? (
        <div className="tasks-modal__errors work-timeline-error" role="alert">
          {error}
          <button type="button" className="tasks-filter-button" onClick={() => navigate(url)}>
            Odśwież dane
          </button>
          <button
            type="button"
            className="tasks-filter-button"
            onClick={() => setError('')}
            aria-label="Zamknij komunikat"
          >
            <Icon name="x" />
          </button>
        </div>
      ) : null}
      <div className="work-timeline-navigation">
        <div className="work-timeline-navigation-group">
          <div className="work-timeline-scales" role="group" aria-label="Skala osi czasu">
            {SCALES.map(([value, label]) => (
              <button
                key={value}
                type="button"
                className="tasks-filter-button"
                aria-pressed={scale === value}
                disabled={locked}
                onClick={() => focusDay(visibleDay(), value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
      <p className="u-sr-only" id="timeline-keyboard-help">
        Kliknij pasek, aby edytować daty. Przeciągnij pasek, aby przesunąć zadanie, lub jego
        krawędzie, aby zmienić czas trwania. Strzałki w lewo i w prawo przesuwają pasek o dzień;
        Shift ze strzałką zmienia koniec. Escape anuluje przeciąganie.
      </p>
      <span className="u-sr-only" role="status" aria-live="polite">
        {notice}
      </span>
      {data.items.length ? (
        <div
          className="work-timeline-viewport"
          ref={viewport}
          tabIndex={0}
          aria-label="Tabela zadań i przewijany kalendarz"
        >
          <table className={`work-timeline-table work-timeline-table--${scale}`}>
            <colgroup>
              <col className="work-timeline-work-col" />
              <col className="work-timeline-assignee-col" />
              <col style={{ width: window.width }} />
            </colgroup>
            <thead>
              <tr>
                <th scope="col" className="work-timeline-heading">
                  Praca <span>{data.items.length}</span>
                </th>
                <th scope="col" className="work-timeline-assignee">
                  Wykonawca
                </th>
                <th scope="col" className="work-timeline-calendar-heading">
                  <span className="u-sr-only">Kalendarz</span>
                  <div className="work-timeline-calendar-header">
                    <div className="work-timeline-major">
                      {headers.major.map((segment) => (
                        <span
                          key={segment.start}
                          style={{ left: segment.left, width: segment.width }}
                          title={segment.title}
                        >
                          {segment.label}
                        </span>
                      ))}
                    </div>
                    <div className="work-timeline-minor">
                      {headers.minor.map((segment) => (
                        <span
                          key={segment.start}
                          className={segment.weekend ? 'is-weekend' : ''}
                          style={{ left: segment.left, width: segment.width }}
                          title={segment.title}
                        >
                          {segment.label}
                        </span>
                      ))}
                    </div>
                    {todayVisible ? (
                      <span
                        className="work-timeline-today-label"
                        style={{ left: todayLeft }}
                        title={`Dzisiaj: ${dayLabel(today)}`}
                      >
                        {scale === 'weeks' ? new Date(dayKey(today)).getUTCDate() : 'Dziś'}
                      </span>
                    ) : null}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {sprints.map((sprint) => {
                const range = { start: parseDay(sprint.start_on)!, end: parseDay(sprint.end_on)! };
                const geometry = taskGeometry(range, window);
                return (
                  <tr key={`sprint-${sprint.id}`} className="work-timeline-sprint-row">
                    <td className="work-timeline-heading">
                      <span className="work-timeline-sprint-name">
                        <Icon name="calendar-range" />
                        <span title={sprint.name}>{sprint.name}</span>
                      </span>
                    </td>
                    <td className="work-timeline-assignee">
                      <span className="work-caption">Sprint</span>
                    </td>
                    <td className="work-timeline-calendar-cell">
                      <div className="work-timeline-lane">
                        {todayLine}
                        {geometry ? (
                          <span
                            className="work-timeline-sprint-bar"
                            title={`${sprint.name}: ${dayLabel(range.start)} – ${dayLabel(range.end)}`}
                            style={{ left: geometry.left, width: geometry.width }}
                          >
                            {sprint.name}
                          </span>
                        ) : (
                          <button
                            type="button"
                            className="work-timeline-outside"
                            onClick={() => focusDay(range.start)}
                          >
                            <Icon name="arrow-right" />
                            Pokaż sprint
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}

              {data.items.map((item) => {
                const range = preview?.id === item.id ? preview.range : itemRange(item);
                const geometry = range ? taskGeometry(range, window) : null;
                const canEdit = item.editable && !!item.update_dates_url;
                return (
                  <tr
                    key={item.id}
                    className={`${selected === item.id ? 'is-selected' : ''} ${saving === item.id ? 'is-saving' : ''}`}
                  >
                    <td className="work-timeline-heading">
                      <div className="work-timeline-task">
                        <span className="work-timeline-type" title={item.type_label}>
                          <Icon name={item.type_icon} />
                        </span>
                        <a href={item.url} title={`${item.key} · ${item.title}`}>
                          <span className="work-timeline-key">{item.key}</span>
                          <span className="work-timeline-title">{item.title}</span>
                        </a>
                        {canEdit ? (
                          <button
                            type="button"
                            className="tasks-filter-button work-timeline-edit"
                            disabled={locked}
                            onClick={() => edit(item)}
                            aria-label={`Zmień daty ${item.key}`}
                          >
                            <Icon name="calendar-range" />
                          </button>
                        ) : null}
                      </div>
                    </td>
                    <td className="work-timeline-assignee">
                      <span
                        className="work-timeline-person"
                        title={item.assignee?.label || 'Nie przypisano'}
                      >
                        {item.assignee ? (
                          <Avatar data={item.assignee.avatar} className="tasks-issue-mini-avatar" />
                        ) : (
                          <span className="work-timeline-unassigned">
                            <Icon name="user-round" />
                          </span>
                        )}
                        <span>{item.assignee?.label || 'Nie przypisano'}</span>
                      </span>
                    </td>
                    <td className="work-timeline-calendar-cell">
                      <div className="work-timeline-lane">
                        {todayLine}
                        {range && geometry ? (
                          <div
                            className={`work-timeline-bar status-${item.category} ${preview?.id === item.id ? 'is-dragging' : ''} ${geometry.clippedStart ? 'is-clipped-start' : ''} ${geometry.clippedEnd ? 'is-clipped-end' : ''} ${!item.start_on || !item.end_on ? 'is-partial' : ''}`}
                            style={{ left: geometry.left, width: Math.max(geometry.width, 6) }}
                          >
                            <button
                              type="button"
                              className="work-timeline-bar-body"
                              aria-label={`${item.key}: ${dateSummary(item)}. ${canEdit ? 'Edytuj daty' : item.title}`}
                              aria-describedby={canEdit ? 'timeline-keyboard-help' : undefined}
                              title={`${item.key} · ${item.title}\n${dateSummary(item)}`}
                              aria-disabled={locked}
                              onPointerDown={(event) => canEdit && begin(event, item, 'move')}
                              onPointerMove={move}
                              onPointerUp={(event) => finish(event)}
                              onPointerCancel={(event) => finish(event, true)}
                              onLostPointerCapture={(event) => {
                                if (gesture.current) finish(event, true);
                              }}
                              onClick={() => {
                                if (locked) return;
                                if (suppressClick.current) {
                                  suppressClick.current = false;
                                  return;
                                }
                                canEdit ? edit(item) : navigate(item.url);
                              }}
                              onKeyDown={(event) => {
                                if (
                                  !canEdit ||
                                  locked ||
                                  !['ArrowLeft', 'ArrowRight'].includes(event.key)
                                )
                                  return;
                                event.preventDefault();
                                const next = shiftTask(
                                  range,
                                  event.key === 'ArrowLeft' ? -1 : 1,
                                  event.shiftKey ? 'end' : 'move',
                                );
                                setPreview({ id: item.id, range: next });
                                void save(
                                  item,
                                  ...movedDates(item, next, event.shiftKey ? 'end' : 'move'),
                                );
                              }}
                            >
                              <span>
                                {item.key} · {item.title}
                              </span>
                            </button>
                            {canEdit && geometry.width >= 20
                              ? (['start', 'end'] as const)
                                  .filter((edge) =>
                                    edge === 'start'
                                      ? !geometry.clippedStart
                                      : !geometry.clippedEnd,
                                  )
                                  .map((edge) => (
                                    <span
                                      key={edge}
                                      aria-hidden="true"
                                      className={`work-timeline-handle work-timeline-handle--${edge}`}
                                      onPointerDown={(event) => begin(event, item, edge)}
                                      onPointerMove={move}
                                      onPointerUp={(event) => finish(event)}
                                      onPointerCancel={(event) => finish(event, true)}
                                    />
                                  ))
                              : null}
                            {preview?.id === item.id ? (
                              <span className="work-timeline-drag-label">
                                {dayLabel(range.start)} – {dayLabel(range.end)} ·{' '}
                                {range.end - range.start + 1} dni
                              </span>
                            ) : null}
                          </div>
                        ) : !range ? (
                          <button
                            type="button"
                            className="work-timeline-unscheduled"
                            disabled={locked || !canEdit}
                            onClick={() => edit(item)}
                          >
                            <Icon name="plus" />
                            {canEdit ? 'Zaplanuj zadanie' : 'Bez dat'}
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="work-timeline-outside"
                            onClick={() => focusDay(range.start)}
                          >
                            <Icon name={range.end < window.start ? 'arrow-left' : 'arrow-right'} />
                            {dateSummary(item)}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          illustration="work"
          title="Brak zadań na osi czasu"
          description={
            Object.values(data.filters).some(Boolean)
              ? 'Zmień kryteria wyszukiwania lub filtry, aby zobaczyć zadania.'
              : 'Zadania tej Przestrzeni pojawią się tutaj. Terminy możesz ustawić bezpośrednio na osi czasu.'
          }
        />
      )}
      {editing ? (
        <DatesDialog
          key={editing.id}
          item={editing}
          pending={saving !== null}
          error={error}
          onClose={() => setEditing(null)}
          onSave={async (start, end) => {
            if (await save(editing, start, end)) setEditing(null);
          }}
        />
      ) : null}
    </section>
  );
}

function DatesDialog({
  item,
  pending,
  error,
  onClose,
  onSave,
}: {
  item: Item;
  pending: boolean;
  error: string;
  onClose: () => void;
  onSave: (start: string, end: string) => Promise<void>;
}) {
  const [start, setStart] = useState(item.start_on || '');
  const [end, setEnd] = useState(item.end_on || '');
  const invalid = !!start && !!end && start > end;
  const dirty = start !== (item.start_on || '') || end !== (item.end_on || '');
  const startDay = parseDay(start),
    endDay = parseDay(end);
  return (
    <Modal
      title={`Daty zadania ${item.key}`}
      className="work-modal work-timeline-dates-modal app-modal-panel--compact"
      pending={pending}
      dirty={dirty}
      onClose={onClose}
    >
      <form
        className="tasks-modal__form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!invalid) void onSave(start, end);
        }}
      >
        <div className="tasks-modal__body">
          <p className="work-timeline-dialog-title">{item.title}</p>
          {error ? (
            <div className="tasks-modal__errors" role="alert">
              {error}
            </div>
          ) : null}
          <div className="work-timeline-date-fields">
            <label className="documents-field tasks-form-field">
              Data rozpoczęcia
              <input
                type="date"
                className="form-input"
                value={start}
                max={end || undefined}
                disabled={pending}
                onChange={(event) => setStart(event.target.value)}
              />
            </label>
            <label className="documents-field tasks-form-field">
              Termin zakończenia
              <input
                type="date"
                className="form-input"
                value={end}
                min={start || undefined}
                disabled={pending}
                onChange={(event) => setEnd(event.target.value)}
              />
            </label>
          </div>
          {invalid ? (
            <p role="alert">Termin zakończenia nie może być wcześniejszy niż początek.</p>
          ) : (
            <p className="work-caption">
              {startDay !== null && endDay !== null
                ? `Czas trwania: ${endDay - startDay + 1} dni (z dniem rozpoczęcia i zakończenia).`
                : 'Możesz podać jedną datę lub obie. Brak dat oznacza zadanie niezaplanowane.'}
            </p>
          )}
          <button
            type="button"
            className="tasks-filter-button"
            disabled={pending || (!start && !end)}
            onClick={() => {
              setStart('');
              setEnd('');
            }}
          >
            Usuń daty
          </button>
        </div>
        <footer className="tasks-modal__footer">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={pending}
            onClick={() => {
              const element = document.querySelector<HTMLElement>('.work-timeline-dates-modal');
              if (element) window.AncoreTaskModals?.close(element);
            }}
          >
            Anuluj
          </button>
          <button type="submit" className="tasks-modal__submit" disabled={pending || invalid}>
            {pending ? 'Zapisywanie…' : 'Zapisz daty'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
