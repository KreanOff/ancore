import { type CSSProperties, type ReactNode } from 'react';
import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { Priority } from './Item';
import { dateLabel, type Summary as Data } from './types';
export default function Summary({ data: s, software }: { data: Data; software: boolean }) {
  function distribution(rows: Data['types'], people = false) {
    return (
      <>
        <div className="work-summary-distribution-heading" aria-hidden="true">
          <span>{people ? 'Osoba przypisana' : 'Typ'}</span>
          <span>{people ? 'Rozkład prac' : 'Rozkład'}</span>
        </div>
        <ul
          className={`work-summary-bars work-summary-bars--distribution work-summary-bars--${people ? 'people' : 'types'}`}
        >
          {rows.map((row, index) => (
            <li key={row.url + index}>
              <a
                href={row.url}
                title={`${row.label}: ${row.count} z ${people ? s.open_total : s.total} zadań`}
              >
                <span className="work-summary-label">
                  {row.avatar ? (
                    <Avatar data={row.avatar} className="tasks-issue-mini-avatar" />
                  ) : people ? (
                    <span className="work-summary-unassigned">
                      <Icon name="user" />
                    </span>
                  ) : (
                    <Icon name={row.icon || 'circle'} />
                  )}
                  <span>{row.label}</span>
                </span>
                <span className="work-summary-distribution">
                  <progress
                    value={row.count}
                    max={(people ? s.open_total : s.total) || 1}
                    aria-label={`${row.label}: ${row.count}`}
                  >
                    {row.percent}%
                  </progress>
                  {row.count || people ? (
                    <span
                      className={`work-summary-distribution-percent ${row.percent < 20 ? 'work-summary-distribution-percent--small' : ''}`}
                      aria-hidden="true"
                    >
                      {row.percent || '<1'}%
                    </span>
                  ) : null}
                </span>
              </a>
            </li>
          ))}
        </ul>
      </>
    );
  }
  function panel(title: string, children: ReactNode, extra = '', description?: ReactNode) {
    return (
      <section className={`work-panel work-summary-panel ${extra}`} aria-label={title}>
        <header className="work-panel-heading">
          <h2>{title}</h2>
        </header>
        {description ? <p className="work-caption">{description}</p> : null}
        {children}
      </section>
    );
  }
  return (
    <div className="work-overview work-summary">
      <div className="work-metrics work-summary-metrics" aria-label="Aktywność przestrzeni">
        {s.metrics.map((metric) => (
          <a
            key={metric.key}
            className="work-panel work-summary-metric"
            href={metric.url}
            aria-label={`${metric.label}: ${metric.count}. ${metric.key === 'due' ? 'Najbliższe' : 'Ostatnie'} 7 dni. Wyświetl zadania.`}
          >
            <span className="work-summary-metric-label">
              <Icon name={metric.icon} />
              {metric.label}
            </span>
            <strong>{metric.count}</strong>
            <span className="work-caption">
              {metric.key === 'due' ? 'Najbliższe' : 'Ostatnie'} 7 dni
            </span>
          </a>
        ))}
      </div>
      <div className="work-summary-grid">
        <section
          className="work-panel work-summary-panel work-summary-panel--status"
          aria-label="Przegląd statusów"
        >
          <header className="work-panel-heading">
            <h2>Przegląd statusów</h2>
            <a className="work-summary-link" href={s.list_url}>
              Wyświetl zadania
              <Icon name="arrow-up-right" />
            </a>
          </header>
          <p className="work-caption">Otwarte zadania i zakończone w ostatnich 14 dniach.</p>
          <div className="work-summary-status">
            <div className="work-summary-donut">
              <svg viewBox="0 0 100 100" aria-hidden="true" focusable="false">
                <circle className="work-summary-donut-track" cx="50" cy="50" r="40" />
                {s.statuses
                  .filter((status) => status.count)
                  .map((status) => (
                    <circle
                      key={status.key}
                      className={`work-summary-donut-arc status-${status.category}`}
                      cx="50"
                      cy="50"
                      r="40"
                      pathLength="100"
                      strokeDasharray={`${status.arc} ${status.gap}`}
                      strokeDashoffset={status.offset}
                    />
                  ))}
              </svg>
              <div className="work-summary-donut-total">
                <strong>{s.status_total}</strong>
                <span>zadań</span>
              </div>
            </div>
            <ul className="work-summary-legend">
              {s.statuses.map((status) => (
                <li key={status.key}>
                  <a href={status.url}>
                    <span className="work-summary-label">
                      <span className={`work-summary-dot status-${status.category}`} />
                      {status.label}
                    </span>
                    <span className="work-summary-status-count">{status.count}</span>
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
        {panel(
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
        )}
        {panel(
          'Podział priorytetów',
          <>
            <div
              className="work-summary-priority-chart"
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
                    className="work-summary-priority"
                    aria-label={`${priority.label}: ${priority.count} otwartych zadań. Wyświetl zadania.`}
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
            {!s.open_total ? (
              <p className="work-caption work-summary-note">Brak otwartych zadań.</p>
            ) : null}
          </>,
          '',
          'Priorytety otwartych zadań.',
        )}
        {panel(
          'Typy zgłoszeń',
          distribution(s.types),
          'work-summary-panel--distribution',
          <>
            Podział wszystkich dostępnych zadań w przestrzeni.{' '}
            <a className="work-summary-link" href={s.list_url}>
              Wyświetl wszystkie zadania
            </a>
          </>,
        )}
        {panel(
          'Obciążenie zespołu',
          s.workload.length ? (
            distribution(s.workload, true)
          ) : (
            <div className="work-summary-empty">
              <Icon name="users" />
              <p>Brak otwartych zadań</p>
              <span className="work-caption">Przypisane zadania pokażą obciążenie zespołu.</span>
            </div>
          ),
          `work-summary-panel--distribution ${software ? '' : 'work-summary-workload'}`,
          <>
            Rozkład {s.open_total} otwartych zadań według wykonawcy.{' '}
            <a className="work-summary-link" href={s.list_url}>
              Zmień przypisanie zadań
            </a>
          </>,
        )}
        {software
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
          : null}
      </div>
    </div>
  );
}
