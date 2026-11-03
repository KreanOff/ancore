import { statusColorStyle } from '../shared/status-color';
import { ViewToolbar } from './ViewToolbar';
import { type CSSProperties, useEffect, useId, useRef, useState } from 'react';
import { Avatar, type AvatarData } from '../shared/Avatar';
import { EmptyState } from '../shared/EmptyState';
import { Icon } from '../shared/Icon';
import { Select } from '../shared/Select';
import { errorMessage } from '../shared/api';
import { navigate } from '../shared/page';
import { ItemFiltering } from './ItemToolbar';
import { dateLabel, type DetailData } from './types';

export interface ReportsData {
  period: { days: number; start_on: string; end_on: string; label: string };
  filters: { report_period: string; report_sprint: string };
  filter_error: string;
  sprint_options: { value: string; label: string }[];
  snapshot: {
    total: number;
    open: number;
    completed: number;
    completion_percent: number;
    overdue: number;
    due_soon: number;
    unassigned: number;
    points: number;
    completed_points: number;
    unestimated: number;
  };
  activity: { created: number; completed: number; logged_minutes: number; logged_label: string };
  trend: {
    date: string;
    label: string;
    created: number;
    completed: number;
    logged_minutes: number;
  }[];
  statuses: {
    key: string;
    label: string;
    color: string;
    category: string;
    count: number;
    percent: number;
    url: string;
  }[];
  priorities: { key: string; label: string; count: number; percent: number; url: string }[];
  workload: {
    id: number | null;
    label: string;
    avatar: AvatarData | null;
    total: number;
    open: number;
    completed: number;
    overdue: number;
    points: number;
    logged_minutes: number;
    logged_label: string;
    url: string;
  }[];
  sprints: {
    id: number;
    name: string;
    state: string;
    state_label: string;
    start_on: string;
    end_on: string;
    total: number;
    completed: number;
    open: number;
    points: number;
    completed_points: number;
    completion_percent: number;
    url: string;
  }[];
  overdue: {
    total: number;
    items: {
      id: number;
      key: string;
      title: string;
      url: string;
      due_at: string;
      days_overdue: number;
      priority: string;
      priority_label: string;
      assignee: string;
      status_label: string;
    }[];
  };
  export_url: string;
  reset_url: string;
  generated_at: string;
}

const PERIODS: [string, string][] = [
  ['7', 'Ostatnie 7 dni'],
  ['30', 'Ostatnie 30 dni'],
  ['90', 'Ostatnie 90 dni'],
];
const number = new Intl.NumberFormat('pl-PL', { maximumFractionDigits: 1 });
const dayLabel = new Intl.DateTimeFormat('pl-PL', {
  day: 'numeric',
  month: 'short',
  timeZone: 'Europe/Warsaw',
});
const shortDate = (value: string) =>
  value ? dayLabel.format(new Date(`${value.slice(0, 10)}T12:00:00Z`)) : '—';
const format = (value: number) => number.format(value);
const percent = (value: number) => `${format(value)}%`;

function reportUrl(url: string, key: string, value: string) {
  const next = new URL(url, location.origin);
  for (const name of [...next.searchParams.keys()]) {
    if (
      name === 'page' ||
      name === 'timeline_limit' ||
      name.startsWith('list_limit_') ||
      name.startsWith('backlog_limit_')
    )
      next.searchParams.delete(name);
  }
  if (value) next.searchParams.set(key, value);
  else next.searchParams.delete(key);
  next.searchParams.set('view', 'reports');
  return next.pathname + next.search;
}

function Meter({
  value,
  max,
  label,
  color,
}: {
  value: number;
  max: number;
  label: string;
  color?: string;
}) {
  return (
    <progress
      className="work-reports-meter"
      value={value}
      max={max || 1}
      aria-label={label}
      style={color ? ({ '--report-bar-color': color } as CSSProperties) : undefined}
    >
      {format(value)} / {format(max)}
    </progress>
  );
}

function TrendChart({ report }: { report: ReportsData }) {
  const [table, setTable] = useState(false);
  const id = useId();
  const points = report.trend;
  const peak = Math.max(1, ...points.flatMap((point) => [point.created, point.completed]));
  const step = Math.max(1, Math.ceil(peak / 4));
  const maximum = step * 4;
  const x = (index: number) => 36 + (index * 616) / Math.max(1, points.length - 1);
  const y = (count: number) => 176 - (count * 148) / maximum;
  const path = (key: 'created' | 'completed') =>
    points
      .map(
        (point, index) => `${index ? 'L' : 'M'} ${x(index).toFixed(1)} ${y(point[key]).toFixed(1)}`,
      )
      .join(' ');
  const ticks = [
    ...new Set([
      0,
      Math.floor((points.length - 1) / 3),
      Math.floor(((points.length - 1) * 2) / 3),
      points.length - 1,
    ]),
  ].filter((index) => index >= 0);
  const active = report.activity.created > 0 || report.activity.completed > 0;
  return (
    <section className="work-panel work-reports-trend" aria-labelledby={`${id}-title`}>
      <div className="work-reports-panel-heading">
        <div>
          <h3 id={`${id}-title`}>Tworzenie i kończenie zadań</h3>
          <p className="work-caption">
            {shortDate(report.period.start_on)} – {shortDate(report.period.end_on)} · dziennie
          </p>
        </div>
        <button
          type="button"
          className="tasks-filter-button"
          aria-pressed={table}
          onClick={() => setTable(!table)}
        >
          <Icon name={table ? 'chart-no-axes-combined' : 'rows-3'} />
          {table ? 'Wykres' : 'Tabela'}
        </button>
      </div>
      <div className="work-reports-activity">
        <div>
          <span>Utworzone</span>
          <strong>{format(report.activity.created)}</strong>
        </div>
        <div>
          <span>Zakończone</span>
          <strong>{format(report.activity.completed)}</strong>
        </div>
        <div>
          <span>Zarejestrowany czas</span>
          <strong>{report.activity.logged_label}</strong>
        </div>
      </div>
      {table ? (
        <div
          className="work-reports-table-wrap work-reports-trend-table"
          tabIndex={0}
          role="region"
          aria-label="Dzienna aktywność — tabela"
        >
          <table className="work-reports-table">
            <caption className="u-sr-only">Dzienna aktywność: {report.period.label}</caption>
            <thead>
              <tr>
                <th scope="col">Data</th>
                <th scope="col">Utworzone</th>
                <th scope="col">Zakończone</th>
                <th scope="col">Czas (min)</th>
              </tr>
            </thead>
            <tbody>
              {points.map((point) => (
                <tr key={point.date}>
                  <th scope="row">{dateLabel(point.date)}</th>
                  <td>{point.created}</td>
                  <td>{point.completed}</td>
                  <td>{format(point.logged_minutes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="work-reports-chart">
          <svg
            viewBox="0 0 680 212"
            role="img"
            aria-labelledby={`${id}-chart-title ${id}-chart-description`}
          >
            <title id={`${id}-chart-title`}>
              Utworzone i zakończone zadania w wybranym okresie
            </title>
            <desc id={`${id}-chart-description`}>
              {report.activity.created} utworzonych i {report.activity.completed} zakończonych.
              Dokładne wartości dzienne są dostępne po wybraniu przycisku Tabela.
            </desc>
            {[0, 1, 2, 3, 4].map((tick) => (
              <g key={tick}>
                <line
                  x1="36"
                  x2="652"
                  y1={y(tick * step)}
                  y2={y(tick * step)}
                  className="work-reports-gridline"
                />
                <text x="26" y={y(tick * step) + 4} textAnchor="end">
                  {tick * step}
                </text>
              </g>
            ))}
            {ticks.map((index) => (
              <text
                key={index}
                x={x(index)}
                y="202"
                textAnchor={index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'}
              >
                {shortDate(points[index].date)}
              </text>
            ))}
            <path d={path('created')} className="work-reports-line work-reports-line--created" />
            <path
              d={path('completed')}
              className="work-reports-line work-reports-line--completed"
            />
            {points.flatMap((point, index) =>
              (['created', 'completed'] as const).map((key) =>
                point[key] > 0 ? (
                  <circle
                    key={`${point.date}-${key}`}
                    cx={x(index)}
                    cy={y(point[key])}
                    r="3"
                    className={`work-reports-point work-reports-point--${key}`}
                  >
                    <title>
                      {dateLabel(point.date)}: {key === 'created' ? 'utworzone' : 'zakończone'} —{' '}
                      {point[key]}
                    </title>
                  </circle>
                ) : null,
              ),
            )}
          </svg>
          {!active ? (
            <p className="work-reports-chart-empty">
              Brak utworzonych i zakończonych zadań w tym okresie.
            </p>
          ) : null}
        </div>
      )}
      <div className="work-reports-chart-legend">
        <span>
          <i className="work-reports-swatch work-reports-swatch--created" aria-hidden="true" />
          Utworzone
        </span>
        <span>
          <i className="work-reports-swatch work-reports-swatch--completed" aria-hidden="true" />
          Zakończone
        </span>
      </div>
      <p className="work-caption work-reports-method">
        Zakończenia według ostatniej daty ukończenia zadań, które nadal są zakończone. Ponowne
        otwarcie zadania zmienia ten wynik.
      </p>
    </section>
  );
}

export default function ReportsView({
  data,
  url,
  refresh,
}: {
  data: DetailData;
  url: string;
  refresh: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const mounted = useRef(true);
  const pending = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const report = data.reports;
  async function reload() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await refresh();
      if (mounted.current) setNotice('Raport został odświeżony.');
    } catch (exception) {
      if (mounted.current) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  const activeFilters = Object.entries(data.filters).filter(([, value]) => value);
  const hasFilters =
    activeFilters.length > 0 ||
    (!!report?.filters.report_sprint && report.filters.report_sprint !== 'all');
  const snapshot = report?.snapshot;
  return (
    <div className="work-reports" aria-busy={busy}>
      <ViewToolbar
        actions={
          <>
            <button
              type="button"
              className="tasks-filter-button"
              disabled={busy}
              onClick={() => void reload()}
            >
              <Icon name="refresh-cw" />
              {busy ? 'Odświeżanie…' : 'Odśwież'}
            </button>
            {report ? (
              <a
                className="tasks-filter-button"
                href={report.export_url}
                title="Eksportuj bieżące zadania po filtrach, niezależnie od okresu aktywności"
                download
              >
                <Icon name="download" />
                Eksport CSV
              </a>
            ) : null}
          </>
        }
      >
        {report ? (
          <>
            <fieldset disabled={busy} className="work-view-toolbar-fields">
              <ItemFiltering data={data} url={url} />
              <Select
                hideLabel
                label="Okres aktywności"
                name="report_period"
                value={report.filters.report_period}
                options={PERIODS}
                onChange={(value) => navigate(reportUrl(url, 'report_period', value))}
              />
              {data.space.template === 'scrum' ? (
                <Select
                  hideLabel
                  label="Sprint"
                  name="report_sprint"
                  value={report.filters.report_sprint}
                  options={report.sprint_options.map((option) => [option.value, option.label])}
                  onChange={(value) => navigate(reportUrl(url, 'report_sprint', value))}
                />
              ) : null}
              <Select
                hideLabel
                label="Wykonawca"
                name="assignee"
                value={data.filters.assignee || ''}
                options={data.filter_options.assignee || [['', 'Wszyscy wykonawcy']]}
                onChange={(value) => navigate(reportUrl(url, 'assignee', value))}
              />
            </fieldset>
            {hasFilters ? (
              <a className="tasks-filter-button" href={report.reset_url}>
                <Icon name="x" />
                Wyczyść filtry
              </a>
            ) : null}
          </>
        ) : null}
      </ViewToolbar>
      <header className="work-reports-header">
        <div>
          <h2>Raporty przestrzeni</h2>
          <p className="work-caption">
            Postęp, obciążenie i terminowość dostępnych dla Ciebie zadań.
          </p>
        </div>
      </header>
      {report ? (
        <>
          {activeFilters.length ? (
            <div className="work-reports-filter-summary" aria-label="Aktywne filtry">
              {activeFilters.map(([key, value]) => (
                <span key={key}>
                  {key === 'summary'
                    ? data.summary_filter_label
                    : key === 'q'
                      ? `Szukaj: ${value}`
                      : data.filter_options[key]?.find(([option]) => option === value)?.[1] ||
                        value}
                </span>
              ))}
            </div>
          ) : null}
        </>
      ) : null}
      {error || report?.filter_error ? (
        <div className="tasks-modal__errors work-reports-error" role="alert">
          <span>{error || report?.filter_error}</span>
          {error ? (
            <button
              type="button"
              className="tasks-filter-button"
              onClick={() => void reload()}
              disabled={busy}
            >
              Spróbuj ponownie
            </button>
          ) : null}
        </div>
      ) : null}
      <span className="u-sr-only" role="status">
        {notice}
      </span>
      {!report ? (
        <div className="work-panel">
          <p>Nie udało się wczytać raportu. Odśwież dane, aby spróbować ponownie.</p>
        </div>
      ) : !snapshot?.total ? (
        <div className="work-panel work-reports-empty">
          <EmptyState
            illustration="tasks"
            title={
              hasFilters || report.filter_error
                ? 'Brak zadań dla wybranych filtrów'
                : 'Raporty zaczynają się od zadań'
            }
            description={
              hasFilters || report.filter_error
                ? 'Zmień sprint lub wykonawcę albo wyczyść filtry, aby zobaczyć inne wyniki.'
                : 'Po utworzeniu zadań zobaczysz tutaj ich postęp, terminy i obciążenie zespołu.'
            }
          />
          {hasFilters || report.filter_error ? (
            <a href={report.reset_url} className="tasks-filter-button">
              Wyczyść filtry
            </a>
          ) : (
            <a href={data.space.url + '?view=list'} className="tasks-filter-button">
              Przejdź do zadań
            </a>
          )}
        </div>
      ) : (
        <>
          <div className="work-reports-section-heading">
            <h3>Stan bieżący</h3>
            <span className="work-caption">Niezależnie od okresu aktywności</span>
          </div>
          <div className="work-reports-kpis">
            <div className="work-panel work-reports-kpi">
              <span>
                <Icon name="list-checks" />
                Wszystkie zadania
              </span>
              <strong>{format(snapshot.total)}</strong>
              <small>
                {format(snapshot.points)} pkt · {format(snapshot.unestimated)} otwartych bez
                estymacji
              </small>
            </div>
            <div className="work-panel work-reports-kpi">
              <span>
                <Icon name="circle-check" />
                Zakończone
              </span>
              <strong>
                {format(snapshot.completed)}
                <em>{percent(snapshot.completion_percent)}</em>
              </strong>
              <Meter
                value={snapshot.completed}
                max={snapshot.total}
                label="Udział zakończonych zadań"
              />
            </div>
            <div className="work-panel work-reports-kpi">
              <span>
                <Icon name="clock" />
                Otwarte zadania
              </span>
              <strong>{format(snapshot.open)}</strong>
              <small>{format(snapshot.unassigned)} bez wykonawcy</small>
            </div>
            <div
              className={`work-panel work-reports-kpi ${snapshot.overdue ? 'work-reports-kpi--attention' : ''}`}
            >
              <span>
                <Icon name="calendar-clock" />
                Po terminie
              </span>
              <strong>{format(snapshot.overdue)}</strong>
              <small>{format(snapshot.due_soon)} z terminem w ciągu 7 dni</small>
            </div>
          </div>
          <div className="work-reports-main-grid">
            <TrendChart report={report} />
            <section
              className="work-panel work-reports-statuses"
              aria-labelledby="report-status-title"
            >
              <div className="work-reports-panel-heading">
                <div>
                  <h3 id="report-status-title">Rozkład statusów</h3>
                  <p className="work-caption">Stan bieżący · {format(snapshot.total)} zadań</p>
                </div>
                <Icon name="chart-no-axes-combined" />
              </div>
              <div className="work-reports-bars">
                {report.statuses.map((status) => (
                  <a
                    className={`work-reports-bar-row status-${status.category}`}
                    style={statusColorStyle(status.color)}
                    key={status.key}
                    href={status.url}
                    aria-label={`Filtruj raport: ${status.label}, ${status.count} zadań`}
                  >
                    <span className="work-reports-bar-label">
                      <i aria-hidden="true" />
                      {status.label}
                    </span>
                    <span className="work-reports-bar-count">
                      {format(status.count)}
                      <small>{percent(status.percent)}</small>
                    </span>
                    <Meter value={status.count} max={snapshot.total} label={status.label} />
                  </a>
                ))}
              </div>
              <p className="work-caption work-reports-method">
                Wybierz status, aby zawęzić raport.
              </p>
            </section>
          </div>
          <section
            className="work-panel work-reports-workload"
            aria-labelledby="report-workload-title"
          >
            <div className="work-reports-panel-heading">
              <div>
                <h3 id="report-workload-title">Obciążenie zespołu</h3>
                <p className="work-caption">Zadania według aktualnego wykonawcy</p>
              </div>
              <span className="work-reports-badge">{format(snapshot.open)} otwartych</span>
            </div>
            <div
              className="work-reports-table-wrap"
              tabIndex={0}
              role="region"
              aria-label="Obciążenie zespołu — tabela"
            >
              <table className="work-reports-table">
                <thead>
                  <tr>
                    <th scope="col">Wykonawca</th>
                    <th scope="col">Otwarte</th>
                    <th scope="col">Zakończone</th>
                    <th scope="col">Po terminie</th>
                    <th scope="col">Punkty</th>
                    <th scope="col">Czas w okresie</th>
                  </tr>
                </thead>
                <tbody>
                  {report.workload.map((person) => (
                    <tr key={person.id ?? 'unassigned'}>
                      <th scope="row">
                        <a
                          href={person.url}
                          className="work-reports-person"
                          aria-label={`Filtruj raport: ${person.label}`}
                        >
                          <Avatar data={person.avatar || {}} className="tasks-issue-mini-avatar" />
                          <span>{person.label}</span>
                        </a>
                      </th>
                      <td>
                        <div className="work-reports-load">
                          <Meter
                            value={person.open}
                            max={snapshot.open}
                            label={`Otwarte zadania: ${person.label}`}
                          />
                          <span>{format(person.open)}</span>
                        </div>
                      </td>
                      <td>{format(person.completed)}</td>
                      <td>
                        {person.overdue ? (
                          <span className="work-reports-badge">{format(person.overdue)}</span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>{format(person.points)}</td>
                      <td>{person.logged_label}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="work-caption work-reports-method">
              Punkty obejmują otwarte zadania. Czas obejmuje wybrany okres w zadaniach przypisanych
              danej osobie, niezależnie od autora wpisu.
            </p>
          </section>
          <div className="work-reports-secondary-grid">
            <section className="work-panel" aria-labelledby="report-overdue-title">
              <div className="work-reports-panel-heading">
                <div>
                  <h3 id="report-overdue-title">Zadania po terminie</h3>
                  <p className="work-caption">Otwarte · od najstarszego terminu</p>
                </div>
                <span className="work-reports-badge">{format(report.overdue.total)}</span>
              </div>
              {report.overdue.items.length ? (
                <div className="work-reports-overdue-list">
                  {report.overdue.items.map((task) => (
                    <a key={task.id} href={task.url} className="work-reports-task">
                      <div className="work-reports-task-title">
                        <span className="work-caption">{task.key}</span>
                        <span>{task.title}</span>
                      </div>
                      <div className="work-reports-task-meta">
                        <span>{task.assignee || 'Nie przypisano'}</span>
                        <span>{task.priority_label}</span>
                        <time dateTime={task.due_at}>{dateLabel(task.due_at)}</time>
                        <span className="work-reports-badge">
                          {task.days_overdue
                            ? `${task.days_overdue} dni opóźnienia`
                            : 'Termin minął dzisiaj'}
                        </span>
                      </div>
                    </a>
                  ))}
                </div>
              ) : (
                <div className="work-reports-inline-empty">
                  <Icon name="circle-check" />
                  <p>Brak zaległych zadań w tym zakresie.</p>
                  <span className="work-caption">
                    Wszystkie otwarte zadania mieszczą się w terminie lub nie mają ustalonej daty.
                  </span>
                </div>
              )}
              {report.overdue.total > report.overdue.items.length ? (
                <p className="work-caption">
                  Pokazano {report.overdue.items.length} z {report.overdue.total} zadań. Pełna lista
                  jest w eksporcie CSV.
                </p>
              ) : null}
            </section>
            <section className="work-panel" aria-labelledby="report-priority-title">
              <div className="work-reports-panel-heading">
                <div>
                  <h3 id="report-priority-title">Priorytety otwartej pracy</h3>
                  <p className="work-caption">Stan bieżący · {format(snapshot.open)} zadań</p>
                </div>
                <Icon name="flag" />
              </div>
              {snapshot.open ? (
                <div className="work-reports-bars">
                  {report.priorities.map((priority) => (
                    <a
                      className="work-reports-bar-row"
                      key={priority.key}
                      href={priority.url}
                      aria-label={`Filtruj raport: priorytet ${priority.label}, ${priority.count} otwartych zadań`}
                    >
                      <span className="work-reports-bar-label">{priority.label}</span>
                      <span className="work-reports-bar-count">
                        {format(priority.count)}
                        <small>{percent(priority.percent)}</small>
                      </span>
                      <Meter
                        value={priority.count}
                        max={snapshot.open}
                        label={`Priorytet ${priority.label}`}
                      />
                    </a>
                  ))}
                </div>
              ) : (
                <div className="work-reports-inline-empty">
                  <Icon name="circle-check" />
                  <p>Wszystkie zadania są zakończone.</p>
                </div>
              )}
            </section>
          </div>
          {data.space.template === 'scrum' ? (
            <section className="work-panel" aria-labelledby="report-sprints-title">
              <div className="work-reports-panel-heading">
                <div>
                  <h3 id="report-sprints-title">Bieżące zadania sprintów</h3>
                  <p className="work-caption">Bieżący skład i status zadań w sprintach</p>
                </div>
                <span className="work-reports-badge">{report.sprints.length}</span>
              </div>
              {report.sprints.length ? (
                <div className="work-reports-sprints">
                  {report.sprints.map((sprint) => (
                    <a
                      className="work-reports-sprint"
                      key={sprint.id}
                      href={sprint.url}
                      aria-label={`Filtruj raport: ${sprint.name}`}
                    >
                      <div className="work-reports-sprint-heading">
                        <h4>{sprint.name}</h4>
                        <span
                          className={`work-reports-badge ${sprint.state === 'active' ? 'is-active' : ''}`}
                        >
                          {sprint.state_label}
                        </span>
                      </div>
                      <p className="work-caption">
                        {sprint.start_on || sprint.end_on
                          ? `${shortDate(sprint.start_on)} – ${shortDate(sprint.end_on)}`
                          : 'Termin nie został ustalony'}
                      </p>
                      <div className="work-reports-sprint-values">
                        <span>
                          {format(sprint.completed)} / {format(sprint.total)} zadań
                        </span>
                        <strong>{percent(sprint.completion_percent)}</strong>
                      </div>
                      <Meter
                        value={sprint.completed}
                        max={sprint.total}
                        label={`Ukończenie sprintu ${sprint.name}`}
                      />
                      <div className="work-reports-sprint-values work-caption">
                        <span>
                          {format(sprint.completed_points)} / {format(sprint.points)} pkt
                          zakończonych
                        </span>
                        <span>{format(sprint.open)} otwartych</span>
                      </div>
                    </a>
                  ))}
                </div>
              ) : (
                <div className="work-reports-inline-empty">
                  <Icon name="layers" />
                  <p>Brak sprintów w tym zakresie.</p>
                  <a href={data.space.url + '?view=backlog'} className="tasks-filter-button">
                    Otwórz backlog
                  </a>
                </div>
              )}
            </section>
          ) : null}
          <footer className="work-reports-footer">
            <span className="work-caption">
              Aktualizacja: {dateLabel(report.generated_at, true)} · strefa Europe/Warsaw
            </span>
            <details>
              <summary>Jak czytać raport?</summary>
              <p>
                Stan bieżący, obciążenie, priorytety i sprinty obejmują wszystkie zadania pasujące
                do filtrów, niezależnie od okresu. Okres ogranicza daty utworzenia, ostatniego
                zakończenia i czas pracy. Wpisy czasu przecinające granice okresu są przycięte do
                tego okresu i bieżącej chwili. Dane obejmują zadania i podzadania, do których masz
                dostęp.
              </p>
              <p>
                Realizacja sprintu pokazuje jego aktualną zawartość. Zadania przeniesione do innego
                sprintu lub backlogu nie są uwzględniane. Nie jest historycznym pomiarem prędkości
                ani wykresem spalania. Zmiany przypisania, sprintu, statusu i uprawnień mogą
                zmieniać wcześniejsze wyniki.
              </p>
            </details>
          </footer>
        </>
      )}
    </div>
  );
}
