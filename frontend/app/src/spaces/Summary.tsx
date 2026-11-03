import { statusColorStyle } from '../shared/status-color';
import { type CSSProperties, type ReactNode, useState } from 'react';
import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { navigate } from '../shared/page';
import { Priority } from './Item';
import { SummaryDistribution } from './SummaryDistribution';
import { dateLabel, type Summary as Data } from './types';
import { useSummaryMotion } from './useSummaryMotion';
import SummaryDashboard from './SummaryDashboard';

function share(count: number, total: number) {
  if (!count || !total) return '0%';
  const percent = Math.round((count * 100) / total);
  return percent ? `${percent}%` : '<1%';
}

function StatusChart({ data: s }: { data: Data }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [focused, setFocused] = useState<string | null>(null);
  const active = s.statuses.find((status) => status.key === (hovered ?? focused));
  return (
    <section
      className="work-panel work-summary-panel work-summary-panel--status"
      aria-label="Przegląd statusów"
      data-summary-reveal
    >
      <header className="work-panel-heading">
        <h2>Przegląd statusów</h2>
        <a className="work-summary-link" href={s.list_url}>
          Wyświetl zadania
          <Icon name="arrow-up-right" />
        </a>
      </header>
      <p className="work-caption">Otwarte zadania i zakończone w ostatnich 14 dniach.</p>
      <div
        className={`work-summary-status ${active ? 'has-active-status' : ''}`}
        onPointerLeave={() => setHovered(null)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            setHovered(null);
            setFocused(null);
          }
        }}
      >
        <div className="work-summary-donut">
          <div className="work-summary-donut-visual">
            <svg viewBox="0 0 100 100" aria-hidden="true" focusable="false">
              <circle className="work-summary-donut-track" cx="50" cy="50" r="40" />
              {s.statuses
                .filter((status) => status.count)
                .map((status) => (
                  <path
                    key={status.key}
                    data-status-key={status.key}
                    style={statusColorStyle(status.color)}
                    className={`work-summary-donut-arc status-${status.category} ${active?.key === status.key ? 'is-active' : ''}`}
                    d={status.path}
                    onPointerEnter={() => setHovered(status.key)}
                    onPointerLeave={() => setHovered(null)}
                    onClick={() => navigate(status.url)}
                  />
                ))}
            </svg>
          </div>
          <div className="work-summary-donut-total" aria-hidden="true">
            <strong>{active?.count ?? s.status_total}</strong>
            <span className="work-summary-donut-label">{active?.label ?? 'zadań'}</span>
            <span className="work-summary-donut-share">
              {active ? share(active.count, s.status_total) : 'Łącznie'}
            </span>
          </div>
        </div>
        <ul className="work-summary-legend">
          {s.statuses.map((status) => (
            <li key={status.key}>
              <a
                href={status.url}
                className={active?.key === status.key ? 'is-active' : ''}
                aria-label={`${status.label}: ${status.count} z ${s.status_total} zadań, ${share(status.count, s.status_total)}. Wyświetl zadania.`}
                onPointerEnter={() => setHovered(status.key)}
                onPointerLeave={() => setHovered(null)}
                onFocus={() => setFocused(status.key)}
                onBlur={() => setFocused(null)}
              >
                <span className="work-summary-label">
                  <span
                    className={`work-summary-dot status-${status.category}`}
                    style={statusColorStyle(status.color)}
                  />
                  {status.label}
                </span>
                <span className="work-summary-legend-values">
                  <span className="work-summary-legend-share" aria-hidden="true">
                    {share(status.count, s.status_total)}
                  </span>
                  <span className="work-summary-status-count">{status.count}</span>
                </span>
              </a>
            </li>
          ))}
        </ul>
      </div>
      {!s.total ? (
        <p className="work-caption work-summary-note">
          Utwórz pierwsze zadanie, aby zobaczyć postęp pracy.
        </p>
      ) : !s.status_total ? (
        <p className="work-caption work-summary-note">
          Brak otwartych ani niedawno zakończonych zadań.
        </p>
      ) : null}
    </section>
  );
}

function PriorityChart({ data: s }: { data: Data }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [focused, setFocused] = useState<string | null>(null);
  const active = s.priorities.find((row) => row.key === (hovered ?? focused));
  return (
    <section
      className="work-panel work-summary-panel"
      aria-label="Podział priorytetów"
      data-summary-reveal
    >
      <header className="work-panel-heading">
        <h2>Podział priorytetów</h2>
      </header>
      <p className="work-caption">Priorytety otwartych zadań.</p>
      <div
        className={`work-summary-priority-chart ${active ? 'has-active-priority' : ''}`}
        aria-label="Liczba otwartych zadań według priorytetu"
      >
        <div className="work-summary-priority-axis" aria-hidden="true">
          <span>{s.priority_axis.max}</span>
          <span>{s.priority_axis.middle}</span>
          <span>0</span>
        </div>
        <div className="work-summary-priorities">
          {s.priorities.map((priority) => (
            <a
              key={priority.key}
              href={priority.url}
              className={`work-summary-priority ${active?.key === priority.key ? 'is-active' : ''}`}
              aria-label={`${priority.label}: ${priority.count} z ${s.open_total} otwartych zadań, ${share(priority.count, s.open_total)}. Wyświetl zadania.`}
              onPointerEnter={() => setHovered(priority.key)}
              onPointerLeave={() => setHovered(null)}
              onFocus={() => setFocused(priority.key)}
              onBlur={() => setFocused(null)}
              onKeyDown={(event) => {
                if (event.key === 'Escape') {
                  setHovered(null);
                  setFocused(null);
                }
              }}
            >
              <span className="work-summary-priority-track">
                <span
                  className="work-summary-priority-bar"
                  style={{ '--summary-bar-height': `${priority.height}%` } as CSSProperties}
                >
                  <span className="work-summary-priority-count">{priority.count}</span>
                </span>
              </span>
              <span className="work-summary-priority-label">
                <Priority value={priority.key} label={priority.label} />
                <span>{priority.key === 'none' ? 'Brak' : priority.label}</span>
              </span>
            </a>
          ))}
        </div>
      </div>
      {!s.open_total && <p className="work-caption work-summary-note">Brak otwartych zadań.</p>}
    </section>
  );
}

export default function Summary({
  data: s,
  software,
  api,
  csrfToken,
  readOnly,
  refresh,
  filters,
}: {
  data: Data;
  software: boolean;
  api: string;
  csrfToken: string;
  readOnly: boolean;
  refresh: () => Promise<void>;
  filters?: ReactNode;
}) {
  const root = useSummaryMotion();
  function panel(title: string, children: ReactNode, extra = '', description?: ReactNode) {
    return (
      <section
        className={`work-panel work-summary-panel ${extra}`}
        aria-label={title}
        data-summary-reveal
      >
        <header className="work-panel-heading">
          <h2>{title}</h2>
        </header>
        {description ? <p className="work-caption">{description}</p> : null}
        {children}
      </section>
    );
  }
  function renderWidget(id: string): ReactNode {
    const metric = s.metrics.find((row) => row.key === id);
    if (metric)
      return (
        <a
          key={metric.key}
          className="work-panel work-summary-metric"
          data-summary-reveal
          href={metric.url}
          aria-label={`${metric.label}: ${metric.count}. ${metric.key === 'due' ? 'Najbliższe' : 'Ostatnie'} 7 dni. Wyświetl zadania.`}
        >
          <span className="work-summary-metric-label">
            <Icon name={metric.icon} />
            {metric.label}
          </span>
          <span className="work-summary-metric-value">
            <strong>{metric.count}</strong>
            <span className="work-summary-metric-action" aria-hidden="true">
              <span>Wyświetl zadania</span>
              <Icon name="arrow-up-right" />
            </span>
          </span>
          <span className="work-caption">
            {metric.key === 'due' ? 'Najbliższe' : 'Ostatnie'} 7 dni
          </span>
        </a>
      );
    switch (id) {
      case 'statuses':
        return <StatusChart data={s} />;
      case 'activity':
        return panel(
          'Ostatnia aktywność',
          <ol className="work-summary-activity">
            {s.activities.length ? (
              s.activities.map((activity, index) => (
                <li key={index}>
                  <a href={activity.url}>
                    <Avatar data={activity.avatar} className="tasks-issue-avatar" />
                    <span className="work-summary-activity-copy">
                      <span>{activity.actor}</span>
                      <span className="work-caption">{activity.action}</span>
                      <span
                        className="work-summary-activity-task"
                        title={`${activity.key} · ${activity.title}`}
                      >
                        <span className="work-item-key">{activity.key}</span> {activity.title}
                      </span>
                      <time
                        className="work-caption"
                        dateTime={activity.created_at}
                        title={dateLabel(activity.created_at, true)}
                      >
                        {dateLabel(activity.created_at, true)}
                      </time>
                    </span>
                  </a>
                </li>
              ))
            ) : (
              <li className="work-summary-empty">
                <Icon name="history" />
                <p>Brak aktywności</p>
                <span className="work-caption">Zmiany w zadaniach pojawią się tutaj.</span>
              </li>
            )}
          </ol>,
          '',
          'Najnowsze zmiany w zadaniach tej przestrzeni.',
        );
      case 'priorities':
        return <PriorityChart data={s} />;
      case 'types':
        return (
          <SummaryDistribution
            title="Typy zgłoszeń"
            rows={s.types}
            total={s.total}
            description={
              <>
                Podział wszystkich dostępnych zadań w przestrzeni.{' '}
                <a className="work-summary-link" href={s.list_url}>
                  Wyświetl wszystkie zadania
                </a>
              </>
            }
          />
        );
      case 'workload':
        return (
          <SummaryDistribution
            title="Obciążenie zespołu"
            rows={s.workload}
            total={s.open_total}
            people
            className={software ? '' : 'work-summary-workload'}
            description={
              <>
                Rozkład {s.open_total} otwartych zadań według wykonawcy.{' '}
                <a className="work-summary-link" href={s.list_url}>
                  Zmień przypisanie zadań
                </a>
              </>
            }
          />
        );
      case 'epics':
        return software
          ? panel(
              'Postęp epików',
              <ul className="work-summary-epics">
                {s.epics.length ? (
                  s.epics.map((epic) => (
                    <li key={epic.key}>
                      <a href={epic.url}>
                        <span className="work-item-key">
                          <Icon name="zap" />
                          {epic.key}
                        </span>
                        <span title={epic.title}>{epic.title}</span>
                        <progress
                          value={epic.closed}
                          max={epic.total || 1}
                          aria-label={`${epic.title}: ${epic.closed} z ${epic.total} zadań zakończonych`}
                        >
                          {epic.percent}%
                        </progress>
                        <span className="work-caption">
                          {epic.closed} / {epic.total} · {epic.percent}%
                        </span>
                      </a>
                    </li>
                  ))
                ) : (
                  <li className="work-summary-empty">
                    <Icon name="zap" />
                    <p>Brak epików</p>
                    <span className="work-caption">
                      Połącz zadania w epiki, aby śledzić większe cele.
                    </span>
                  </li>
                )}
              </ul>,
              '',
              'Zakończone zadania w większych obszarach pracy.',
            )
          : null;
      default:
        return null;
    }
  }
  return (
    <div className="work-overview work-summary" ref={root}>
      <SummaryDashboard
        initial={s.dashboard}
        filters={filters}
        api={api}
        csrfToken={csrfToken}
        readOnly={readOnly}
        renderWidget={renderWidget}
        refresh={refresh}
      />
    </div>
  );
}
