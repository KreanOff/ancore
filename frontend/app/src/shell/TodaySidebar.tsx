import { useEffect, useRef, useState } from 'react';
import { addDays, dateKey, monthBounds, periodStep, weekdays } from '../calendar/dates';
import { Icon } from '../shared/Icon';
import { pageRequest } from '../shared/page';
import { RightSidebarContent } from '../shared/RightSidebarContent';

interface TodayData {
  today: string;
  time_zone: string;
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
  const pending = useRef<AbortController>();

  async function load() {
    if (pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    try {
      const result = await pageRequest<TodayData>(api, url, token, controller.signal);
      if (controller.signal.aborted) return;
      setData(result);
      setMonth((previous) => previous || new Date(`${result.today}T12:00:00`));
    } catch {
      // Calendar navigation remains available using the last known or local date.
      // Refresh the server date again on focus or the next clock tick.
    } finally {
      if (!controller.signal.aborted) {
        pending.current = undefined;
      }
    }
  }

  useEffect(() => {
    document.querySelector('[data-right-sidebar-fallback]:has([data-today-sidebar])')?.remove();
    void load();
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
    // Keep the current-day marker accurate when the shell stays open overnight.
    refresh();
    const timer = window.setInterval(refresh, 60000);
    window.addEventListener('focus', refresh);
    return () => {
      clearInterval(timer);
      window.removeEventListener('focus', refresh);
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
      </div>
    </RightSidebarContent>
  );
}
