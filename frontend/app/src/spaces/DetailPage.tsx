import { setPageLocation } from '../shared/page';
import { type DragEvent, useEffect, useRef, useState } from 'react';
import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { EmptyState } from '../shared/EmptyState';
import { Pagination } from '../shared/Pagination';
import { Select } from '../shared/Select';
import { StatusGroup } from '../shared/StatusGroup';
import { FormDialog, type FormDialogData } from '../forms/FormDialog';
import { errorMessage } from '../shared/api';
import { type Page, type PageProps, navigate, pageRequest } from '../shared/page';
import { ItemCard, ItemRow } from './Item';
import Summary from './Summary';
import { dateLabel, type DetailData, type Item, type Sprint } from './types';
const LABELS: Record<string, string> = {
  work_type: 'Typ zgłoszenia',
  assignee: 'Wykonawca',
  status: 'Status',
  priority: 'Priorytet',
  team: 'Zespół',
};
export default function DetailPage({ initial, csrfToken }: PageProps) {
  const [data, setData] = useState(initial.data as DetailData),
    [modal, setModal] = useState<FormDialogData | null>((initial.data as DetailData).modal),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [notice, setNotice] = useState(''),
    [selected, setSelected] = useState<Set<number>>(new Set()),
    [destination, setDestination] = useState(''),
    [dragged, setDragged] = useState<Item | null>(null),
    [filters, setFilters] = useState((initial.data as DetailData).filters);
  const life = useRef(new AbortController()),
    pending = useRef(false);
  useEffect(() => () => life.current.abort(), []);
  async function openForm(url: string) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      const page = await pageRequest<Page>(initial.api_url, url, csrfToken, life.current.signal);
      if (page.type !== 'form') throw new Error('Nie udało się otworzyć formularza.');
      setModal(page.data as FormDialogData);
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  async function act(url: string, values: Record<string, string> | FormData) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    setNotice('');
    const form = values instanceof FormData ? values : new FormData();
    if (!(values instanceof FormData))
      Object.entries(values).forEach(([key, value]) => form.set(key, value));
    try {
      await pageRequest(initial.api_url, url, csrfToken, life.current.signal, form);
      const page = await pageRequest<Page>(
        initial.api_url,
        initial.url,
        csrfToken,
        life.current.signal,
      );
      setData(page.data as DetailData);
      setSelected(new Set());
      setNotice('Zmiany zostały zapisane.');
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      setBusy(false);
      setDragged(null);
    }
  }
  function toggle(item: Item, checked: boolean) {
    setSelected((current) => {
      const next = new Set(current);
      if (checked) next.add(item.id);
      else next.delete(item.id);
      return next;
    });
  }
  function bulk() {
    const form = new FormData(),
      rows = data.items.filter((item) => selected.has(item.id));
    rows.forEach((item) => form.append('item_ids', String(item.id)));
    form.set('destination', destination);
    form.set(
      'positions',
      JSON.stringify(
        Object.fromEntries(rows.map((item) => [String(item.id), [item.sprint_id, item.rank]])),
      ),
    );
    void act(data.bulk_plan_url, form);
  }
  function dragStart(event: DragEvent, item: Item) {
    if (busy || !item.editable) {
      event.preventDefault();
      return;
    }
    setDragged(item);
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', item.key);
  }
  function drop(event: DragEvent, group: string | number | null, before?: Item) {
    event.preventDefault();
    event.stopPropagation();
    if (!dragged || busy || before?.id === dragged.id) return;
    const board = data.view === 'board',
      rows = data.items.filter(
        (item) =>
          item.id !== dragged.id && (board ? item.status === group : item.sprint_id === group),
      );
    const bounds = before ? event.currentTarget.getBoundingClientRect() : null,
      afterHalf = !!bounds && event.clientY > bounds.top + bounds.height / 2;
    const index = before
      ? rows.findIndex((item) => item.id === before.id) + (afterHalf ? 1 : 0)
      : rows.length;
    const previous = rows[index - 1],
      next = rows[index];
    const snapshot = {
      space: String(data.space.id),
      source_sprint: String(dragged.sprint_id ?? ''),
      source_rank: String(dragged.rank),
      return_view: data.view,
      before: String(next?.id ?? ''),
      after: String(previous?.id ?? ''),
    };
    void act(
      dragged.action_url,
      board
        ? {
            ...snapshot,
            action: 'position',
            source_status: dragged.status,
            status: String(group),
            before_rank: String(next?.rank ?? ''),
            after_rank: String(previous?.rank ?? ''),
          }
        : { ...snapshot, action: 'plan', sprint: String(group ?? '') },
    );
  }
  const actionProps = {
    data,
    busy,
    openForm: (url: string) => void openForm(url),
    act: (url: string, values: Record<string, string>) => void act(url, values),
  };
  const filterKeys = Object.keys(LABELS),
    tableView = ['list', 'board', 'backlog', 'timeline'].includes(data.view),
    filtered = Object.values(data.filters).some(Boolean);
  function row(item: Item) {
    return (
      <ItemRow
        key={item.id}
        item={item}
        {...actionProps}
        selected={selected.has(item.id)}
        select={(checked) => toggle(item, checked)}
        dragging={!!dragged}
        onDragStart={(event) => dragStart(event, item)}
        onDragEnd={() => setDragged(null)}
        onDrop={(event) => drop(event, item.sprint_id, item)}
      />
    );
  }
  function sprintDetails(sprint: Sprint) {
    return (
      <>
        <span className="work-planning-summary">
          <span>{sprint.planning.points} pkt</span>
          {sprint.planning.unestimated ? (
            <span>{sprint.planning.unestimated} bez estymacji</span>
          ) : null}
          {sprint.finished_count ? (
            <span>
              {sprint.finished_count}/{sprint.visible_count} ukończonych
            </span>
          ) : null}
        </span>
        <span className="work-sprint-dates">
          {dateLabel(sprint.start_on)}–{dateLabel(sprint.end_on)}
        </span>
        {data.can_manage ? (
          <>
            <button
              type="button"
              className="tasks-icon-button"
              disabled={busy}
              aria-label={`Edytuj sprint ${sprint.name}`}
              onClick={() => void openForm(sprint.edit_url)}
            >
              <Icon name="pencil" />
            </button>
            <button
              type="button"
              className="tasks-filter-button"
              disabled={busy || (sprint.state === 'planned' && !!data.active_sprint)}
              title={
                sprint.state === 'planned' && data.active_sprint
                  ? 'Najpierw zakończ aktywny sprint'
                  : undefined
              }
              onClick={() =>
                void openForm(sprint.state === 'planned' ? sprint.start_url : sprint.complete_url)
              }
            >
              {sprint.state === 'planned' ? 'Rozpocznij sprint' : 'Zakończ sprint'}
            </button>
          </>
        ) : null}
      </>
    );
  }
  function backlogGroup(sprint: Sprint | null) {
    const rows = data.items.filter((item) => item.sprint_id === (sprint?.id ?? null)),
      totals = sprint?.planning || data.backlog_totals;
    return (
      <StatusGroup
        key={sprint?.id ?? 'backlog'}
        onDragOver={dragged ? (event) => event.preventDefault() : undefined}
        onDrop={(event) => drop(event, sprint?.id ?? null)}
        label={sprint?.name || 'Backlog'}
        labelSuffix={sprint?.state_label}
        category={sprint ? (sprint.state === 'active' ? 'in_progress' : 'new') : undefined}
        count={rows.length}
        className={`work-backlog-group ${sprint ? 'work-sprint' : ''}`}
        details={
          sprint ? (
            sprintDetails(sprint)
          ) : (
            <>
              <span className="work-planning-summary">
                {data.space.template === 'scrum' ? (
                  <>
                    <span>{totals.points} pkt</span>
                    {totals.unestimated ? <span>{totals.unestimated} bez estymacji</span> : null}
                  </>
                ) : null}
                {totals.total !== rows.length ? (
                  <span>
                    Na stronie: {rows.length} z {totals.total}
                  </span>
                ) : null}
              </span>
              {data.space.template === 'scrum' && data.can_manage ? (
                <button
                  type="button"
                  className="tasks-filter-button work-backlog-sprint-create"
                  disabled={busy}
                  onClick={() => void openForm(data.sprint_create_url)}
                >
                  <Icon name="plus" />
                  Utwórz sprint
                </button>
              ) : null}
            </>
          )
        }
      >
        <div className="tasks-issue-list work-backlog-items">
          {sprint?.goal ? <p className="work-sprint-goal">{sprint.goal}</p> : null}
          {rows.length ? (
            rows.map(row)
          ) : (
            <div className="tasks-empty-section" role="status">
              {totals.total
                ? 'Zadania znajdują się na innej stronie wyników.'
                : filtered
                  ? 'Brak zadań pasujących do filtrów.'
                  : sprint
                    ? 'Przeciągnij zadania lub zaznacz je i wybierz ten sprint.'
                    : 'Backlog jest pusty. Dodaj zadanie, aby zaplanować kolejne prace.'}
            </div>
          )}
          {data.can_edit ? (
            <button
              type="button"
              className="work-backlog-create tasks-project-menu-button"
              disabled={busy}
              onClick={() => void openForm(sprint?.create_item_url || data.backlog_create_url)}
            >
              <Icon name="plus" />
              {sprint ? 'Utwórz zadanie w sprincie' : 'Utwórz zadanie w backlogu'}
            </button>
          ) : null}
        </div>
      </StatusGroup>
    );
  }
  return (
    <div className="tasks-page tasks-list-page work-page" data-react-screen="space-detail">
      <section className="tasks-workspace" aria-busy={busy}>
        <header className="tasks-topbar tasks-topbar--directory tasks-topbar--project-directory">
          <div className="tasks-titlebar-left">
            {data.can_manage ? (
              <button
                type="button"
                className="space-avatar-trigger"
                aria-label={`Zmień awatar przestrzeni ${data.space.name}`}
                disabled={busy}
                onClick={() => void openForm(data.space.url + 'avatar/')}
              >
                <Avatar space data={data.space.avatar} className="space-avatar--heading" />
              </button>
            ) : (
              <Avatar space data={data.space.avatar} className="space-avatar--heading" />
            )}
            <h1 className="tasks-topbar-title work-space-title">{data.space.name}</h1>
          </div>
          <div className="tasks-titlebar-actions">
            {data.can_edit ? (
              <button
                type="button"
                className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                disabled={busy}
                onClick={() => void openForm(data.create_item_url)}
              >
                <Icon name="plus" />
                Utwórz zadanie
              </button>
            ) : null}
          </div>
        </header>
        <nav
          className="notifications-tabs work-tabs work-tabs--views"
          aria-label="Widoki przestrzeni"
        >
          {data.navigation.map((nav) => (
            <a
              key={nav.key}
              href={nav.url}
              aria-current={data.view === nav.key ? 'page' : undefined}
            >
              <Icon name={nav.icon} />
              {nav.label}
            </a>
          ))}
        </nav>
        {tableView ? (
          <>
            <form
              className="tasks-filterbar tasks-filterbar--directory work-item-toolbar"
              method="get"
              action={data.space.url}
            >
              <input type="hidden" name="view" value={data.view} />
              {data.filters.summary ? (
                <input type="hidden" name="summary" value={data.filters.summary} />
              ) : null}
              <div className="tasks-filterbar-left">
                {filterKeys.map((key) => (
                  <Select
                    key={key}
                    name={key}
                    hideLabel
                    label={LABELS[key]}
                    value={filters[key] || ''}
                    options={data.filter_options[key]}
                    onChange={(value) => setFilters((current) => ({ ...current, [key]: value }))}
                  />
                ))}
                <button className="tasks-filter-button" type="submit">
                  <Icon name="filter" />
                  <span>Filtruj</span>
                </button>
              </div>
              <div className="tasks-filterbar-right">
                <label className="tasks-search-field tasks-project-search">
                  <Icon name="search" />
                  <input
                    type="search"
                    name="q"
                    defaultValue={data.filters.q}
                    placeholder="Szukaj zadań"
                    aria-label="Szukaj zadania lub oznaczenia"
                    maxLength={120}
                  />
                </label>
              </div>
            </form>
            {data.filters.summary ? (
              <div className="work-summary-filter" role="status">
                <span>{data.summary_filter_label}</span>
                <a
                  className="tasks-filter-button"
                  href={(() => {
                    const url = new URL(initial.url, location.origin);
                    url.searchParams.delete('summary');
                    url.searchParams.delete('page');
                    return url.pathname + url.search;
                  })()}
                  aria-label={`Usuń filtr: ${data.summary_filter_label}`}
                >
                  <Icon name="x" />
                  Usuń filtr
                </a>
              </div>
            ) : null}
          </>
        ) : null}
        {error ? (
          <div className="tasks-modal__errors" role="alert">
            {error}
            <button
              type="button"
              className="tasks-filter-button"
              onClick={() => navigate(initial.url)}
            >
              Odśwież widok
            </button>
          </div>
        ) : null}
        <span className="u-sr-only" role="status" aria-live="polite">
          {notice}
        </span>
        <div
          className={`work-content ${['list', 'board', 'backlog'].includes(data.view) ? 'work-content--tasks' : ''}`}
        >
          {data.view === 'overview' && data.summary ? (
            <Summary data={data.summary} software={data.space.kind === 'software'} />
          ) : null}
          {data.view === 'list' ? (
            <div
              className={`tasks-table-wrap tasks-board work-item-list ${data.items.length ? '' : 'tasks-board--empty'}`}
            >
              {data.items.length ? (
                [...data.columns]
                  .filter((column) => data.items.some((item) => item.status === column.key))
                  .map((column) => (
                    <StatusGroup
                      key={column.key}
                      category={column.category}
                      label={column.label}
                      count={data.items.filter((item) => item.status === column.key).length}
                    >
                      <div className="tasks-issue-list">
                        {data.items.filter((item) => item.status === column.key).map(row)}
                      </div>
                    </StatusGroup>
                  ))
              ) : (
                <EmptyState
                  illustration="tasks"
                  title={filtered ? 'Nie znaleziono zadań.' : 'Nie ma jeszcze zadań.'}
                  description={
                    filtered
                      ? 'Zmień lub wyczyść filtry, aby zobaczyć inne wyniki.'
                      : 'Nowe zadania pojawią się tutaj po ich utworzeniu.'
                  }
                />
              )}
            </div>
          ) : null}
          {data.view === 'board' ? (
            <>
              {data.space.template === 'scrum' ? (
                <div className="work-panel-heading">
                  {data.active_sprint ? (
                    <>
                      <h2>{data.active_sprint.name}</h2>
                      <span>
                        {dateLabel(data.active_sprint.start_on)}–
                        {dateLabel(data.active_sprint.end_on)} · {data.active_sprint.goal}
                      </span>
                    </>
                  ) : (
                    <>
                      <p>Brak aktywnego sprintu. Przygotuj i rozpocznij sprint w backlogu.</p>
                      <a className="btn btn-secondary" href={data.space.url + '?view=backlog'}>
                        Otwórz backlog
                      </a>
                    </>
                  )}
                </div>
              ) : null}
              <div
                className={`tasks-table-wrap tasks-board tasks-kanban-board ${data.space.template === 'scrum' ? 'work-sprint-board' : ''}`}
              >
                {data.columns.map((column) => {
                  const rows = data.items.filter((item) => item.status === column.key);
                  const cards = (
                    <div className="tasks-issue-list tasks-kanban-column__list">
                      {rows.length ? (
                        rows.map((item) => (
                          <ItemCard
                            key={item.id}
                            item={item}
                            {...actionProps}
                            dragging={!!dragged}
                            onDragStart={(event) => dragStart(event, item)}
                            onDragEnd={() => setDragged(null)}
                            onDrop={(event) => drop(event, column.key, item)}
                          />
                        ))
                      ) : (
                        <div className="tasks-empty-section" role="status">
                          Brak zadań
                        </div>
                      )}
                    </div>
                  );
                  if (data.space.template === 'scrum')
                    return (
                      <StatusGroup
                        key={column.key}
                        className="tasks-kanban-column"
                        category={column.category}
                        label={column.label}
                        count={column.count}
                        onDragOver={dragged ? (event) => event.preventDefault() : undefined}
                        onDrop={(event) => drop(event, column.key)}
                      >
                        {cards}
                      </StatusGroup>
                    );
                  return (
                    <section
                      key={column.key}
                      className={`tasks-kanban-column ${column.category === 'closed' ? 'tasks-kanban-column--done' : ''}`}
                      data-work-column={column.key}
                      aria-label={column.label}
                      onDragOver={dragged ? (event) => event.preventDefault() : undefined}
                      onDrop={(event) => drop(event, column.key)}
                    >
                      <header className="tasks-kanban-column__header">
                        <span className={`status-indicator status-${column.category}`}>
                          {column.label}
                        </span>
                        <span className="tasks-rail-count">{column.count}</span>
                      </header>
                      {cards}
                    </section>
                  );
                })}
              </div>
            </>
          ) : null}
          {data.view === 'backlog' ? (
            <>
              {data.can_edit && selected.size ? (
                <form
                  className="work-backlog-bulk"
                  onSubmit={(event) => {
                    event.preventDefault();
                    bulk();
                  }}
                >
                  <span role="status">Zaznaczono: {selected.size}</span>
                  <div className="work-backlog-bulk-controls">
                    <Select
                      hideLabel
                      label="Miejsce docelowe zaznaczonych zadań"
                      value={destination}
                      options={
                        data.space.template === 'scrum'
                          ? [
                              ['', 'Backlog'],
                              ...data.sprints
                                .filter((sprint) => sprint.state !== 'closed')
                                .map(
                                  (sprint) =>
                                    [
                                      String(sprint.id),
                                      `${sprint.name} · ${sprint.state_label}`,
                                    ] as [string, string],
                                ),
                            ]
                          : [
                              ['', 'Backlog'],
                              ['board', 'Tablica'],
                            ]
                      }
                      onChange={setDestination}
                    />
                    <button type="submit" className="tasks-filter-button" disabled={busy}>
                      <Icon name="arrow-right" />
                      Przenieś zaznaczone
                    </button>
                    <button
                      type="button"
                      className="tasks-filter-button"
                      onClick={() => setSelected(new Set())}
                    >
                      Odznacz
                    </button>
                  </div>
                </form>
              ) : null}
              <div className="tasks-table-wrap tasks-board work-backlog">
                {data.space.template === 'scrum'
                  ? data.sprints
                      .filter((sprint) => sprint.state !== 'closed')
                      .map((sprint) => backlogGroup(sprint))
                  : null}
                {backlogGroup(null)}
              </div>
            </>
          ) : null}
          {data.view === 'timeline' ? (
            <section className="work-panel">
              <h2>Oś czasu</h2>
              <p>Zaplanowane daty dostępnych zadań.</p>
              {data.timeline ? (
                <div className="work-timeline-scale">
                  <span>{dateLabel(data.timeline.start)}</span>
                  <span>{dateLabel(data.timeline.end)}</span>
                </div>
              ) : null}
              {data.items.length ? (
                data.items.map((item) => (
                  <div className="work-timeline-row" key={item.id}>
                    <a href={item.url}>
                      {item.key} · {item.title}
                    </a>
                    <span>{dateLabel(item.start_on) || 'Bez daty rozpoczęcia'}</span>
                    <Icon name="arrow-right" />
                    <span>{dateLabel(item.due_at) || 'Bez terminu'}</span>
                    {item.editable ? (
                      <button
                        type="button"
                        className="tasks-filter-button"
                        disabled={busy}
                        aria-label={`Zmień daty ${item.key}`}
                        onClick={() => void openForm(item.edit_url)}
                      >
                        <Icon name="pencil" />
                      </button>
                    ) : null}
                    <div
                      className="work-timeline-track"
                      aria-label={`${dateLabel(item.timeline.start)} – ${dateLabel(item.timeline.end)}`}
                    >
                      <span
                        style={{ left: `${item.timeline.left}%`, width: `${item.timeline.width}%` }}
                      />
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState
                  illustration="work"
                  title="Brak zaplanowanych terminów"
                  description="Ustaw datę rozpoczęcia lub termin w edycji zadania."
                />
              )}
            </section>
          ) : null}
          {data.view === 'reports' ? (
            <div className="work-overview">
              <section className="work-panel">
                <h2>Postęp pracy</h2>
                <p>
                  {data.stats.closed} z {data.stats.all} zadań zakończonych · {data.stats.overdue}{' '}
                  po terminie
                </p>
                {data.status_counts.map((status) => (
                  <div className="work-report-row" key={status.key}>
                    <span>{status.label}</span>
                    <progress
                      max={data.stats.all || 1}
                      value={status.count}
                      aria-label={status.label}
                    >
                      {status.count}
                    </progress>
                    <span>{status.count}</span>
                  </div>
                ))}
              </section>
              {data.space.template === 'scrum' ? (
                <section className="work-panel">
                  <h2>Sprinty</h2>
                  {data.sprints.length ? (
                    data.sprints.map((sprint) => (
                      <div className="work-member" key={sprint.id}>
                        <span>{sprint.name}</span>
                        <span>{sprint.state_label}</span>
                        <span>
                          {sprint.finished_count} / {sprint.visible_count} dostępnych zadań
                          zakończonych
                        </span>
                      </div>
                    ))
                  ) : (
                    <p>Raporty pojawią się po utworzeniu sprintów.</p>
                  )}
                </section>
              ) : null}
            </div>
          ) : null}
          {data.view === 'settings' ? (
            <div className="work-overview">
              <section className="work-panel">
                <h2>Ustawienia przestrzeni</h2>
                <p>
                  {data.space.kind_label} · {data.space.template_label}
                </p>
                <p>{data.space.management_label}</p>
                <p>
                  Widoczność:{' '}
                  {data.space.visibility === 'private'
                    ? 'prywatna — wybrane osoby'
                    : 'cały Workspace'}
                </p>
                {data.can_manage ? (
                  <>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={busy}
                      onClick={() => void openForm(data.edit_url)}
                    >
                      Edytuj przestrzeń
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={busy}
                      onClick={() => void openForm(data.space.url + 'avatar/')}
                    >
                      Zmień awatar
                    </button>
                  </>
                ) : null}
                {data.can_configure ? (
                  <a className="btn btn-secondary" href={data.configuration_url}>
                    Statusy, typy i pola
                  </a>
                ) : null}
                {data.configuration.shared ? (
                  <p>
                    Konfiguracja „{data.configuration.name}” jest współdzielona. Zmiany obowiązują
                    we wszystkich korzystających z niej przestrzeniach.
                  </p>
                ) : null}
              </section>
              <section className="work-panel">
                <div className="work-panel-heading">
                  <h2>Członkowie i role</h2>
                  {data.can_manage && data.space.visibility === 'private' ? (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={busy}
                      onClick={() => void openForm(data.member_url)}
                    >
                      Udostępnij / zmień rolę
                    </button>
                  ) : null}
                </div>
                {data.space.visibility === 'public' ? (
                  <p>Dostęp mają aktywni członkowie Workspace.</p>
                ) : (
                  <>
                    <p>{data.private_owner} · Właściciel</p>
                    {data.members.map((member) => (
                      <div className="work-member" key={member.id}>
                        <span>{member.name}</span>
                        <span>{member.role}</span>
                        {data.can_manage ? (
                          <button
                            type="button"
                            className="btn btn-secondary"
                            disabled={busy}
                            onClick={() => void act(member.remove_url, {})}
                          >
                            Odbierz dostęp
                          </button>
                        ) : null}
                      </div>
                    ))}
                  </>
                )}
              </section>
            </div>
          ) : null}
        </div>
        {tableView ? <Pagination data={data.pagination} /> : null}
      </section>
      {modal ? (
        <FormDialog
          key={modal.action}
          data={modal}
          api={initial.api_url}
          csrfToken={csrfToken}
          onClose={() => {
            setModal(null);
            if ((initial.data as DetailData).modal) setPageLocation(modal.return_url);
          }}
          onSaved={navigate}
        />
      ) : null}
    </div>
  );
}
