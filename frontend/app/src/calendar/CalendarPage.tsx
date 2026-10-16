import { type CSSProperties, useEffect, useMemo, useRef, useState } from 'react';
import { Icon } from '../shared/Icon';
import { Select } from '../shared/Select';
import { type PageProps, navigate, pageRequest } from '../shared/page';
import { errorMessage } from '../shared/api';
import { EventEditor } from './EventEditor';
import {
  addDays,
  bounds,
  colors,
  dateKey,
  day,
  formatDate,
  lanes,
  monthBounds,
  occurs,
  periodStep,
  time,
  views,
  weekdays,
  weekStart,
  type CalendarEvent,
  type View,
} from './dates';
interface CalendarData {
  config: {
    initialYear: number;
    initialMonth: number;
    initialDay: number;
    initialEventId: number | null;
    urls: { events: string; create: string; update: string; delete: string };
  };
}

export default function CalendarPage({ initial, csrfToken }: PageProps) {
  const [clock, setClock] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setClock(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);
  const { config } = initial.data as CalendarData;
  const [anchor, setAnchor] = useState(
    () => new Date(config.initialYear, config.initialMonth - 1, config.initialDay),
  );
  const [selected, setSelected] = useState(anchor),
    [view, setView] = useState<View>('month');
  const [events, setEvents] = useState<CalendarEvent[]>([]),
    [loading, setLoading] = useState(false),
    [error, setError] = useState('');
  const [query, setQuery] = useState(''),
    [source, setSource] = useState(''),
    [activeColors, setColors] = useState(() => new Set(colors.map((item) => item[0])));
  const [agenda, setAgenda] = useState(true),
    [wholePeriod, setWholePeriod] = useState(false),
    [revision, setRevision] = useState(0);
  const [editor, setEditor] = useState<{
    event: CalendarEvent | null;
    date: Date;
    allDay?: boolean;
  }>();
  const pendingEvent = useRef(config.initialEventId);
  const range = useMemo(() => bounds(anchor, view), [anchor, view]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    const target = `${config.urls.events}?${new URLSearchParams({ start: range.start.toISOString(), end: new Date(range.end.getTime() - 1).toISOString() })}`;
    pageRequest<{ events: CalendarEvent[] }>(initial.api_url, target, csrfToken, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        setEvents(data.events);
        if (pendingEvent.current) {
          const event = data.events.find((item) => item.id === pendingEvent.current);
          if (event) setEditor({ event, date: new Date(event.start) });
          pendingEvent.current = null;
        }
      })
      .catch((exception) => {
        if (!controller.signal.aborted) setError(errorMessage(exception));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [range, revision, config.urls.events, initial.api_url, csrfToken]);
  const visible = useMemo(
    () =>
      events.filter(
        (event) =>
          activeColors.has(event.color) &&
          (!source || event.source === source) &&
          (!query ||
            `${event.title} ${event.description}`
              .toLocaleLowerCase('pl')
              .includes(query.toLocaleLowerCase('pl'))),
      ),
    [events, activeColors, source, query],
  );
  const onDay = (date: Date) => visible.filter((event) => occurs(event, date));
  function open(event: CalendarEvent) {
    if (event.url) navigate(event.url);
    else setEditor({ event, date: new Date(event.start) });
  }
  function newEvent(date = selected, allDay = false, keepTime = false) {
    const next = new Date(date);
    if (allDay) next.setHours(0, 0, 0, 0);
    else if (!keepTime) next.setHours(9, 0, 0, 0);
    setEditor({ event: null, date: next, allDay });
  }
  function chooseDate(date: Date, nextView?: View) {
    setSelected(date);
    if (nextView) {
      setAnchor(date);
      setView(nextView);
    }
  }
  function step(delta: number) {
    const next = periodStep(anchor, view, delta);
    setAnchor(next);
    setSelected(next);
  }
  const period =
    view === 'year'
      ? String(anchor.getFullYear())
      : view === 'month'
        ? anchor.toLocaleDateString('pl-PL', { month: 'long', year: 'numeric' })
        : view === 'day'
          ? `${formatDate(anchor, true)} ${anchor.getFullYear()}`
          : `${formatDate(range.start)} – ${formatDate(addDays(range.end, -1))} ${anchor.getFullYear()}`;
  const agendaEvents = (wholePeriod ? visible : onDay(selected))
    .slice()
    .sort((a, b) => a.start.localeCompare(b.start));
  function eventButton(event: CalendarEvent, className = '', style?: CSSProperties) {
    return (
      <button
        type="button"
        key={event.id}
        className={`calendar-event calendar-event--${event.color} ${className}`}
        style={style}
        title={`${event.title} · ${formatDate(new Date(event.start))} · ${event.all_day ? 'Cały dzień' : time(new Date(event.start))}`}
        onClick={(e) => {
          e.stopPropagation();
          open(event);
        }}
      >
        <span className="calendar-event-time">
          {event.all_day ? 'Cały dzień' : time(new Date(event.start))}
        </span>
        <span className="calendar-event-title">{event.title}</span>
      </button>
    );
  }
  function month(date: Date) {
    const { start, end } = monthBounds(date);
    const weeks: Date[][] = [];
    for (let next = start; next < end; next = addDays(next, 7))
      weeks.push(Array.from({ length: 7 }, (_, i) => addDays(next, i)));
    return (
      <>
        <div className="calendar-weekdays" aria-hidden="true">
          {weekdays.map((label) => (
            <span key={label}>{label}</span>
          ))}
        </div>
        <div className="calendar-view calendar-view--month is-active">
          <div
            className="calendar-days"
            role="grid"
            aria-label="Widok miesięczny"
            style={{ '--calendar-weeks': weeks.length } as CSSProperties}
          >
            {weeks.map((week) => (
              <div className="calendar-week-row" role="row" key={dateKey(week[0])}>
                {week.map((date) => (
                  <div
                    key={dateKey(date)}
                    role="gridcell"
                    tabIndex={dateKey(date) === dateKey(selected) ? 0 : -1}
                    data-calendar-date={dateKey(date)}
                    aria-label={formatDate(date, true)}
                    aria-selected={dateKey(date) === dateKey(selected)}
                    className={`calendar-day ${date.getMonth() !== anchor.getMonth() ? 'calendar-day--other' : ''} ${dateKey(date) === dateKey(new Date()) ? 'calendar-day--today' : ''} ${dateKey(date) === dateKey(selected) ? 'calendar-day--selected' : ''}`}
                    onClick={() => chooseDate(date)}
                    onKeyDown={(event) => {
                      if (event.target !== event.currentTarget) return;
                      const step: Record<string, number> = {
                        ArrowLeft: -1,
                        ArrowRight: 1,
                        ArrowUp: -7,
                        ArrowDown: 7,
                      };
                      if (['Enter', ' '].includes(event.key)) {
                        event.preventDefault();
                        chooseDate(date);
                      } else if (step[event.key]) {
                        event.preventDefault();
                        const next = addDays(date, step[event.key]);
                        chooseDate(next);
                        if (next < start || next >= end) setAnchor(next);
                        requestAnimationFrame(() =>
                          document
                            .querySelector<HTMLElement>(`[data-calendar-date="${dateKey(next)}"]`)
                            ?.focus(),
                        );
                      }
                    }}
                  >
                    <div className="calendar-day-head">
                      <button
                        type="button"
                        className="calendar-day-add"
                        aria-label={`Dodaj wydarzenie: ${formatDate(date)}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          newEvent(date);
                        }}
                      >
                        <Icon name="plus" />
                      </button>
                      <span
                        className="calendar-day-number"
                        aria-current={dateKey(date) === dateKey(new Date()) ? 'date' : undefined}
                      >
                        {date.getDate()}
                      </span>
                    </div>
                    <div className="calendar-day-events">
                      {onDay(date)
                        .slice(0, 3)
                        .map((event) => eventButton(event))}
                      {onDay(date).length > 3 ? (
                        <button
                          type="button"
                          className="calendar-event-more"
                          onClick={(event) => {
                            event.stopPropagation();
                            chooseDate(date);
                            setAgenda(true);
                          }}
                        >
                          +{onDay(date).length - 3} więcej
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </>
    );
  }
  function timeView() {
    const dates = Array.from({ length: view === 'week' ? 7 : 1 }, (_, i) =>
      addDays(view === 'week' ? weekStart(anchor) : anchor, i),
    );
    return (
      <div
        className={`calendar-view calendar-view--${view} is-active`}
        aria-label={view === 'week' ? 'Widok tygodniowy' : 'Widok dzienny'}
      >
        <div
          className="calendar-time-frame"
          style={{ '--calendar-columns': dates.length } as CSSProperties}
        >
          <div className="calendar-time-header">
            <span className="calendar-time-zone">Godz.</span>
            {dates.map((date) => (
              <button
                type="button"
                key={dateKey(date)}
                className="calendar-week-day-head"
                onClick={() => chooseDate(date, 'day')}
              >
                {date.toLocaleDateString('pl-PL', { weekday: 'long', day: 'numeric' })}
              </button>
            ))}
          </div>
          <div className="calendar-time-allday">
            <span className="calendar-time-zone">Cały dzień</span>
            {dates.map((date) => (
              <div key={dateKey(date)} className="calendar-time-allday-cell">
                {onDay(date)
                  .filter((event) => event.all_day)
                  .map((event) => eventButton(event))}
                <button
                  type="button"
                  className="calendar-allday-add"
                  aria-label={`Dodaj całodzienne wydarzenie: ${formatDate(date)}`}
                  onClick={() => newEvent(date, true)}
                >
                  +
                </button>
              </div>
            ))}
          </div>
          <div
            className="calendar-time-scroll"
            ref={(element) => {
              if (element && !element.dataset.positioned) {
                element.scrollTop = 8 * 48;
                element.dataset.positioned = 'true';
              }
            }}
          >
            <div className="calendar-time-grid">
              <div className="calendar-time-hours">
                {Array.from({ length: 24 }, (_, hour) => (
                  <span key={hour}>{String(hour).padStart(2, '0')}:00</span>
                ))}
              </div>
              {dates.map((date) => (
                <div className="calendar-time-column" key={dateKey(date)}>
                  {Array.from({ length: 24 }, (_, hour) => (
                    <button
                      type="button"
                      key={hour}
                      className="calendar-time-slot"
                      aria-label={`Dodaj wydarzenie: ${formatDate(date)}, ${hour}:00`}
                      onClick={() => {
                        const preset = new Date(date);
                        preset.setHours(hour);
                        newEvent(preset, false, true);
                      }}
                    />
                  ))}
                  {lanes(visible, date).map((item) =>
                    eventButton(item.event, 'calendar-time-event', {
                      top: `${(item.start / 1440) * 100}%`,
                      height: `${((item.end - item.start) / 1440) * 100}%`,
                      left: `calc(${(item.lane / item.count) * 100}% + 3px)`,
                      width: `calc(${100 / item.count}% - 6px)`,
                    }),
                  )}
                  {dateKey(date) === dateKey(clock) ? (
                    <div
                      className="calendar-now-line"
                      style={{
                        top: `${((clock.getHours() * 60 + clock.getMinutes()) / 1440) * 100}%`,
                      }}
                      aria-label={`Teraz ${String(clock.getHours()).padStart(2, '0')}:${String(clock.getMinutes()).padStart(2, '0')}`}
                    />
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="calendar-page tasks-page tasks-list-page" data-react-screen="calendar">
      <section
        className="tasks-workspace calendar-workspace"
        aria-label="Kalendarz"
        aria-busy={loading}
      >
        <header className="tasks-topbar calendar-topbar">
          <div className="tasks-titlebar-left">
            <button
              type="button"
              className="tasks-icon-button"
              aria-label="Poprzedni okres"
              onClick={() => step(-1)}
            >
              <Icon name="chevron-left" />
            </button>
            <button
              type="button"
              className="tasks-icon-button calendar-today-button"
              onClick={() => {
                const now = day(new Date());
                setAnchor(now);
                setSelected(now);
              }}
            >
              Dzisiaj
            </button>
            <button
              type="button"
              className="tasks-icon-button"
              aria-label="Następny okres"
              onClick={() => step(1)}
            >
              <Icon name="chevron-right" />
            </button>
            <span className="tasks-topbar-title calendar-period-label" aria-live="polite">
              {period}
            </span>
          </div>
          <div className="tasks-section-actions">
            <button
              type="button"
              className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
              aria-haspopup="dialog"
              onClick={() => newEvent()}
            >
              <Icon name="plus" />
              <span>Nowe wydarzenie</span>
            </button>
          </div>
        </header>
        <div className="tasks-filterbar calendar-filterbar">
          <div className="tasks-filterbar-left">
            <div className="calendar-mini-nav" aria-label="Szybka nawigacja">
              {views.map(([key, label]) => (
                <button
                  type="button"
                  key={key}
                  className={`calendar-mini-nav__button ${view === key ? 'is-active' : ''}`}
                  aria-pressed={view === key}
                  onClick={() => {
                    setAnchor(selected);
                    setView(key);
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="tasks-filterbar-center">
            <span className="calendar-filter-summary">
              {loading
                ? 'Wczytywanie…'
                : `${views.find((item) => item[0] === view)?.[1]} · ${visible.length} pozycji`}
            </span>
          </div>
          <div className="tasks-filterbar-right">
            <Select
              label="Rodzaj pozycji w kalendarzu"
              hideLabel
              value={source}
              options={SOURCE_OPTIONS}
              onChange={setSource}
            />
            <label className="tasks-search-field calendar-search">
              <Icon name="search" />
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Szukaj w tym widoku"
                aria-label="Szukaj wydarzeń i zadań w wybranym okresie"
              />
            </label>
            <details className="calendar-color-filter">
              <summary>
                <Icon name="list-filter" />
                Kolory
              </summary>
              <div className="calendar-color-filters">
                {colors.map(([key, label]) => (
                  <label key={key}>
                    <input
                      type="checkbox"
                      checked={activeColors.has(key)}
                      onChange={(event) =>
                        setColors((current) => {
                          const next = new Set(current);
                          if (event.target.checked) next.add(key);
                          else next.delete(key);
                          return next;
                        })
                      }
                    />
                    <span className={`calendar-color-dot calendar-color-dot--${key}`} />
                    {label}
                  </label>
                ))}
              </div>
            </details>
            <button
              type="button"
              className="tasks-icon-button"
              aria-label="Pokaż lub ukryj plan"
              aria-expanded={agenda}
              onClick={() => setAgenda(!agenda)}
            >
              <Icon name="panel-right" />
            </button>
          </div>
        </div>
        {error ? (
          <div className="calendar-status" role="alert">
            {error}
            <button
              type="button"
              className="tasks-filter-button"
              onClick={() => setRevision((value) => value + 1)}
            >
              Spróbuj ponownie
            </button>
          </div>
        ) : null}
        <div className="tasks-table-wrap calendar-shell">
          <div className={`calendar-body ${agenda ? '' : 'calendar-body--agenda-hidden'}`}>
            <div className="calendar-main">
              {view === 'month' ? (
                month(anchor)
              ) : view === 'year' ? (
                <div className="calendar-view calendar-view--year is-active">
                  <div className="calendar-year-grid">
                    {Array.from({ length: 12 }, (_, index) => {
                      const first = new Date(anchor.getFullYear(), index, 1),
                        start = monthBounds(first).start;
                      return (
                        <div className="calendar-year-month" key={index}>
                          <button
                            type="button"
                            className="calendar-year-month-title"
                            onClick={() => chooseDate(first, 'month')}
                          >
                            {first.toLocaleDateString('pl-PL', { month: 'long' })}
                          </button>
                          <div className="calendar-year-weekdays">
                            {weekdays.map((label) => (
                              <span key={label}>{label[0]}</span>
                            ))}
                          </div>
                          <div className="calendar-year-days">
                            {Array.from({ length: 42 }, (_, i) => {
                              const date = addDays(start, i);
                              return (
                                <button
                                  type="button"
                                  key={dateKey(date)}
                                  className={`calendar-year-day ${onDay(date).length ? 'calendar-year-day--has-events' : ''}`}
                                  disabled={date.getMonth() !== index}
                                  aria-label={formatDate(date, true)}
                                  onClick={() => chooseDate(date, 'day')}
                                >
                                  {date.getMonth() === index ? date.getDate() : ''}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                timeView()
              )}
            </div>
            {agenda ? (
              <aside className="calendar-sidebar" aria-label="Lista wydarzeń">
                <div className="calendar-sidebar-header">
                  <div className="calendar-agenda-heading">
                    <h3 className="calendar-sidebar-title">
                      {wholePeriod ? 'Wydarzenia' : 'Plan dnia'}
                    </h3>
                    <button
                      type="button"
                      className="calendar-text-button"
                      onClick={() => setWholePeriod(!wholePeriod)}
                    >
                      {wholePeriod ? 'Plan dnia' : 'Cały okres'}
                    </button>
                  </div>
                  <span className="calendar-sidebar-subtitle">
                    {wholePeriod ? period : formatDate(selected, true)}
                  </span>
                  <span className="calendar-agenda-count" aria-live="polite">
                    {loading ? 'Wczytywanie…' : `${agendaEvents.length} pozycji`}
                  </span>
                </div>
                <ul className="calendar-events-list">
                  {agendaEvents.length ? (
                    agendaEvents.map((event) => (
                      <li key={event.id}>
                        <button
                          type="button"
                          className={`calendar-list-item calendar-list-item--${event.color}`}
                          onClick={() => open(event)}
                        >
                          <span className="calendar-list-time">
                            {event.all_day ? 'Cały dzień' : time(new Date(event.start))}
                          </span>
                          <span className="calendar-list-body">
                            <span className="calendar-list-title">{event.title}</span>
                            <span className="calendar-list-date">
                              {event.url ? 'Termin · ' : ''}
                              {formatDate(new Date(event.start))}
                              {event.all_day
                                ? ''
                                : ` · ${time(new Date(event.start))} – ${time(new Date(event.end))}`}
                            </span>
                          </span>
                        </button>
                      </li>
                    ))
                  ) : (
                    <li className="calendar-events-empty">
                      <strong>
                        {loading
                          ? 'Wczytywanie pozycji…'
                          : error
                            ? 'Nie udało się wczytać pozycji'
                            : query || source || activeColors.size < colors.length
                              ? 'Brak pasujących pozycji'
                              : 'Czas na Twoje plany'}
                      </strong>
                      <span>
                        {error ? 'Spróbuj ponownie.' : 'Dodaj wydarzenie i zaplanuj ten dzień.'}
                      </span>
                    </li>
                  )}
                </ul>
                <div className="calendar-sidebar-footer">
                  <button type="button" className="tasks-filter-button" onClick={() => newEvent()}>
                    <Icon name="plus" />
                    Dodaj w tym dniu
                  </button>
                </div>
              </aside>
            ) : null}
          </div>
        </div>
      </section>
      {editor ? (
        <EventEditor
          event={editor.event}
          date={editor.date}
          allDay={editor.allDay}
          api={initial.api_url}
          urls={config.urls}
          csrfToken={csrfToken}
          onClose={() => setEditor(undefined)}
          onSaved={(message) => {
            setEditor(undefined);
            setRevision((value) => value + 1);
            window.showNotification?.(message, 'success');
          }}
        />
      ) : null}
    </div>
  );
}
const SOURCE_OPTIONS: [string, string][] = [
  ['', 'Wszystkie pozycje'],
  ['events', 'Wydarzenia'],
  ['tasks', 'Zadania'],
];
