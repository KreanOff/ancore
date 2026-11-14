import { useEffect, useRef, useState } from 'react';
import { addDays, dateKey, monthBounds, periodStep, weekdays } from '../calendar/dates';
import { Icon } from '../shared/Icon';
import { LoadMore } from '../shared/LoadMore';
import { errorMessage } from '../shared/api';
import { PageError, pageRequest } from '../shared/page';
import { RightSidebarContent } from '../shared/RightSidebarContent';
import { TaskPriority } from '../shared/TaskPriority';
import { statusColorStyle } from '../shared/status-color';
import { StatusGroup } from '../shared/StatusGroup';

interface TodayEntry {
  id: string;
  title: string;
  url: string;
  subtitle: string;
  starts_at: string;
  time_label: string;
  color: string;
}

interface TodayData {
  today: string;
  time_zone: string;
  tasks_enabled: boolean;
  entries: (TodayEntry &
    (
      | { source: 'events' }
      | {
          source: 'tasks';
          key: string;
          space_id: number;
          space_name: string;
          priority: string;
          priority_label: string;
          status: string;
          status_label: string;
          status_color: string;
        }
    ))[];
  groups: { id: string; label: string; entries: TodayData['entries'] }[];
  pagination: {
    count: number;
    has_next: boolean;
    next_url: string;
  };
}

export default function TodaySidebar({
  api,
  url,
  calendarUrl,
  token,
  expanded,
}: {
  api: string;
  url: string;
  calendarUrl: string;
  token: string;
  expanded: boolean;
}) {
  const [data, setData] = useState<TodayData>();
  const [month, setMonth] = useState<Date>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const pending = useRef<AbortController>();
  const currentTarget = useRef(url);
  const retryTarget = useRef(url);

  async function load(target = currentTarget.current) {
    if (pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    retryTarget.current = target;
    setLoading(true);
    setError('');
    try {
      const result = await pageRequest<TodayData>(api, target, token, controller.signal);
      if (controller.signal.aborted || pending.current !== controller) return;
      setData(result);
      currentTarget.current = target;
      setMonth((previous) => previous || new Date(`${result.today}T12:00:00`));
    } catch (exception) {
      if (controller.signal.aborted || pending.current !== controller) return;
      if (exception instanceof PageError && [401, 403, 404].includes(exception.status))
        setData(undefined);
      setError(errorMessage(exception));
    } finally {
      if (pending.current === controller) {
        pending.current = undefined;
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    document.querySelector('[data-right-sidebar-fallback]:has([data-today-sidebar])')?.remove();
    currentTarget.current = url;
    retryTarget.current = url;
    setData(undefined);
    void load(url);
    return () => {
      pending.current?.abort();
      pending.current = undefined;
    };
  }, [api, url, token]);

  useEffect(() => {
    if (!expanded) return;
    const refresh = () => {
      if (document.visibilityState === 'hidden') return;
      void load();
    };
    const changed = () => {
      // A request started before a save may still contain the previous event values.
      pending.current?.abort();
      pending.current = undefined;
      void load();
    };
    // Keep today's plan current without collapsing an expanded result window.
    refresh();
    const timer = window.setInterval(refresh, 60000);
    window.addEventListener('focus', refresh);
    window.addEventListener('ancore:calendar-changed', changed);
    return () => {
      clearInterval(timer);
      window.removeEventListener('focus', refresh);
      window.removeEventListener('ancore:calendar-changed', changed);
    };
  }, [expanded, api, url, token]);

  const today = data?.today || dateKey(new Date());
  const shownMonth = month || new Date(`${today}T12:00:00`);
  const range = monthBounds(shownMonth);
  const days: Date[] = [];
  for (let next = range.start; next < range.end; next = addDays(next, 1)) days.push(next);
  function dayUrl(date: string) {
    return `${calendarUrl}?${new URLSearchParams({ date })}`;
  }

  return (
    <RightSidebarContent>
      <div className="today-sidebar" data-today-sidebar>
        <section className="today-sidebar__calendar" aria-label="Kalendarz">
          <div className="today-sidebar__month-nav">
            <span className="today-sidebar__month" aria-live="polite">
              {shownMonth.toLocaleDateString('pl-PL', { month: 'long', year: 'numeric' })}
            </span>
            <button
              type="button"
              className="tasks-icon-button"
              aria-label="Poprzedni miesiąc"
              title="Poprzedni miesiąc"
              onClick={() => setMonth(periodStep(shownMonth, 'month', -1))}
            >
              <Icon name="chevron-left" />
            </button>
            <button
              type="button"
              className="tasks-icon-button"
              aria-label="Następny miesiąc"
              title="Następny miesiąc"
              onClick={() => setMonth(periodStep(shownMonth, 'month', 1))}
            >
              <Icon name="chevron-right" />
            </button>
          </div>
          <div className="today-sidebar__weekdays" aria-hidden="true">
            {weekdays.map((label) => (
              <span key={label}>{label}</span>
            ))}
          </div>
          <div className="today-sidebar__days" aria-label="Dni miesiąca">
            {days.map((date) => {
              const key = dateKey(date);
              return (
                <a
                  key={key}
                  href={dayUrl(key)}
                  className={`today-sidebar__day${date.getMonth() !== shownMonth.getMonth() ? ' is-outside' : ''}${key === today ? ' is-today' : ''}`}
                  aria-current={key === today ? 'date' : undefined}
                  aria-label={date.toLocaleDateString('pl-PL', {
                    weekday: 'long',
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric',
                  })}
                >
                  {date.getDate()}
                </a>
              );
            })}
          </div>
          <button
            type="button"
            className="tasks-filter-button today-sidebar__today"
            onClick={() => setMonth(new Date(`${today}T12:00:00`))}
          >
            Dzisiaj
          </button>
        </section>
        <section className="today-sidebar__tasks" aria-label="Plan na dziś" aria-busy={loading}>
          <div className="today-sidebar__list">
            {data?.groups.map((group) => (
              <StatusGroup
                key={`${url}:${group.id}`}
                label={group.label}
                count={group.entries.length}
                icon={null}
                className="today-sidebar__group"
                headerClassName={
                  group.id === 'events'
                    ? 'tasks-status-block-header--in_progress'
                    : 'tasks-status-block-header--new'
                }
              >
                <div className="tasks-issue-list">
                  {group.entries.map((entry) => (
                    <a
                      className="today-sidebar__task"
                      href={entry.url}
                      key={entry.id}
                      title={`${entry.title} · ${entry.subtitle} · ${entry.time_label}`}
                    >
                      {entry.source === 'tasks' ? (
                        <span className="today-sidebar__task-heading">
                          <TaskPriority value={entry.priority} label={entry.priority_label} />
                          <span className="today-sidebar__task-key">{entry.key}</span>
                          <span
                            className={`status-indicator status-${entry.status}`}
                            style={statusColorStyle(entry.status_color)}
                            title={entry.status_label}
                            aria-label={entry.status_label}
                          />
                          <span className="today-sidebar__task-title">{entry.title}</span>
                        </span>
                      ) : (
                        <span className="today-sidebar__event-heading">
                          <span
                            className="today-sidebar__event-color"
                            aria-hidden="true"
                            style={{ backgroundColor: entry.color }}
                          />
                          <span className="today-sidebar__task-title">{entry.title}</span>
                        </span>
                      )}
                      <time className="today-sidebar__task-time" dateTime={entry.starts_at}>
                        {entry.time_label}
                      </time>
                    </a>
                  ))}
                </div>
              </StatusGroup>
            ))}
            {loading && !data ? (
              <p className="today-sidebar__empty" role="status">
                Wczytywanie planu…
              </p>
            ) : !error && data && !data.entries.length ? (
              <p className="today-sidebar__empty">Brak zadań i wydarzeń na dziś.</p>
            ) : null}
            {error ? (
              <div className="today-sidebar__error" role="alert">
                <p>{error}</p>
                <button
                  type="button"
                  className="tasks-filter-button"
                  onClick={() => void load(retryTarget.current)}
                  disabled={loading}
                >
                  Spróbuj ponownie
                </button>
              </div>
            ) : null}
            {data ? (
              <LoadMore
                loaded={data.entries.length}
                total={data.pagination.count}
                hasMore={data.pagination.has_next}
                loading={loading}
                label="Plan na dziś"
                onLoad={() => void load(data.pagination.next_url)}
              />
            ) : null}
          </div>
        </section>
      </div>
    </RightSidebarContent>
  );
}
