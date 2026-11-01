import { setPageLocation } from '../shared/page';
import { type DragEvent, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { EmptyState } from '../shared/EmptyState';
import { Select } from '../shared/Select';
import { StatusGroup } from '../shared/StatusGroup';
import { FormDialog, type FormDialogData } from '../forms/FormDialog';
import { errorMessage } from '../shared/api';
import { type Page, type PageProps, navigate, pageRequest } from '../shared/page';
import { ItemCard, ItemRow } from './Item';
import { ItemFiltering, ItemToolbar } from './ItemToolbar';
import Summary from './Summary';
import SettingsPage from './SettingsPage';
import { SpaceHeader } from './SpaceHeader';
import { dateLabel, type DetailData, type Item, type Sprint, type Status } from './types';
import { useItemMotion } from './useItemMotion';
import Timeline from './TimelineView';
import ReportsView from './ReportsView';
export default function DetailPage({ initial, csrfToken }: PageProps) {
  const [data, setData] = useState(initial.data as DetailData),
    [modal, setModal] = useState<FormDialogData | null>((initial.data as DetailData).modal),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [notice, setNotice] = useState(''),
    [loadingStatus, setLoadingStatus] = useState(''),
    [listError, setListError] = useState<{ key: string; message: string } | null>(null),
    [selected, setSelected] = useState<Set<number>>(new Set()),
    [destination, setDestination] = useState(''),
    [dragged, setDragged] = useState<Item | null>(null);
  const motion = useItemMotion(data, () => {
    setDragged(null);
    setNotice('Anulowano przeciąganie zadania.');
  });
  const life = useRef(new AbortController()),
    pending = useRef(false),
    currentUrl = useRef(initial.url),
    listScroll = useRef<number | null>(null);
  useEffect(() => () => life.current.abort(), []);
  useLayoutEffect(() => {
    if (listScroll.current !== null && motion.root.current) {
      motion.root.current.scrollTop = listScroll.current;
      listScroll.current = null;
    }
  }, [data]);
  async function loadMore(
    column: Pick<Status, 'key' | 'label' | 'count' | 'loaded_count' | 'more_url'>,
  ) {
    if (pending.current || !column.more_url) return;
    pending.current = true;
    setBusy(true);
    setLoadingStatus(column.key);
    setListError(null);
    try {
      const page = await pageRequest<Page>(
        initial.api_url,
        column.more_url,
        csrfToken,
        life.current.signal,
      );
      if (life.current.signal.aborted) return;
      const next = page.data as DetailData;
      if (
        page.type !== 'space-detail' ||
        next.view !== data.view ||
        next.space.id !== data.space.id
      )
        throw new Error('Nie udało się wczytać zadań. Spróbuj ponownie.');
      listScroll.current = motion.root.current?.scrollTop ?? null;
      currentUrl.current = column.more_url;
      setPageLocation(currentUrl.current);
      setData(next);
      const visible = new Set(next.items.map((item) => item.id));
      setSelected((current) => new Set([...current].filter((id) => visible.has(id))));
      const group =
        next.view === 'list'
          ? next.columns.find((item) => item.key === column.key)
          : next.view === 'timeline'
            ? next.timeline
            : column.key === 'backlog'
              ? { loaded_count: next.backlog_loaded_count, count: next.backlog_totals.total }
              : (() => {
                  const sprint = next.sprints.find((item) => `sprint_${item.id}` === column.key);
                  return sprint
                    ? {
                        loaded_count: sprint.loaded_count,
                        count: sprint.visible_count - sprint.finished_count,
                      }
                    : undefined;
                })();
      setNotice(
        `${column.label}: wczytano ${group?.loaded_count ?? 0} z ${group?.count ?? 0} zadań.`,
      );
    } catch (exception) {
      if (!life.current.signal.aborted)
        setListError({
          key: column.key,
          message:
            exception instanceof Error && exception.name === 'TimeoutError'
              ? 'Serwer nie odpowiedział na czas. Spróbuj ponownie.'
              : errorMessage(exception),
        });
    } finally {
      pending.current = false;
      if (!life.current.signal.aborted) {
        setBusy(false);
        setLoadingStatus('');
      }
    }
  }
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
  async function act(
    url: string,
    values: Record<string, string> | FormData,
    optimistic?: DetailData,
  ) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    setNotice(optimistic ? 'Zapisuję położenie zadania.' : '');
    const form = values instanceof FormData ? values : new FormData();
    if (!(values instanceof FormData))
      Object.entries(values).forEach(([key, value]) => form.set(key, value));
    const previous = data;
    let saved = false;
    if (optimistic) {
      motion.prepareDrop();
      setData(optimistic);
      setDragged(null);
    }
    try {
      await pageRequest(initial.api_url, url, csrfToken, life.current.signal, form);
      saved = true;
      const page = await pageRequest<Page>(
        initial.api_url,
        currentUrl.current,
        csrfToken,
        life.current.signal,
      );
      motion.capture();
      setData(page.data as DetailData);
      setListError(null);
      setSelected(new Set());
      setNotice('Zmiany zostały zapisane.');
    } catch (exception) {
      if (!life.current.signal.aborted) {
        if (optimistic && !saved) {
          motion.capture();
          setData(previous);
        }
        setError(errorMessage(exception));
      }
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
    if (busy || !item.editable || !data.sort.manual) {
      event.preventDefault();
      return;
    }
    if (!motion.start(event)) return;
    setDragged(item);
    setNotice(`Przenoszenie ${item.key}. Wybierz miejsce docelowe. Escape anuluje.`);
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', item.key);
  }
  function drop(event: DragEvent, group: string | number | null, before?: Item) {
    event.preventDefault();
    event.stopPropagation();
    if (!dragged || busy) return;
    if (before?.id === dragged.id) {
      motion.clearDrag();
      setDragged(null);
      setNotice('Położenie zadania nie zmieniło się.');
      return;
    }
    const target = motion.target();
    if (target && target.group === String(group ?? '')) {
      before = data.items.find((item) => item.id === target.before);
    }
    const board = data.view === 'board',
      rows = data.items.filter(
        (item) =>
          item.id !== dragged.id && (board ? item.status === group : item.sprint_id === group),
      );
    const bounds = before ? event.currentTarget.getBoundingClientRect() : null,
      afterHalf = !!bounds && event.clientY > bounds.top + bounds.height / 2;
    const index =
      target && target.group === String(group ?? '')
        ? target.before === null
          ? rows.length
          : rows.findIndex((item) => item.id === target.before)
        : before
          ? rows.findIndex((item) => item.id === before.id) + (afterHalf ? 1 : 0)
          : rows.length;
    const previous = rows[index - 1],
      next = rows[index];
    const sourceGroup = board ? dragged.status : dragged.sprint_id;
    const original = data.items.filter((item) =>
      board ? item.status === sourceGroup : item.sprint_id === sourceGroup,
    );
    if (sourceGroup === group && original.findIndex((item) => item.id === dragged.id) === index) {
      motion.clearDrag();
      setDragged(null);
      setNotice('Położenie zadania nie zmieniło się.');
      return;
    }
    const column = data.columns.find((column) => column.key === group);
    const moved = board
      ? {
          ...dragged,
          status: String(group),
          status_label: column?.label || dragged.status_label,
          category: column?.category || dragged.category,
        }
      : { ...dragged, sprint_id: group as number | null, in_backlog: group === null };
    const items = data.items.filter((item) => item.id !== dragged.id);
    const insertion = next
      ? items.findIndex((item) => item.id === next.id)
      : previous
        ? items.findIndex((item) => item.id === previous.id) + 1
        : items.length;
    items.splice(insertion, 0, moved);
    const optimistic = {
      ...data,
      items,
      columns: data.columns.map((column) => ({
        ...column,
        count:
          column.count +
          (board && column.key === group ? 1 : 0) -
          (board && column.key === dragged.status ? 1 : 0),
      })),
    };
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
      optimistic,
    );
  }
  const actionProps = {
    data,
    busy,
    openForm: (url: string) => void openForm(url),
    act: (url: string, values: Record<string, string>) => void act(url, values),
  };
  const tableView = ['list', 'board', 'backlog', 'timeline'].includes(data.view),
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
        onDragEnd={() => {
          motion.clearDrag();
          setDragged(null);
        }}
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
  function moreControl(
    column: Pick<Status, 'key' | 'label' | 'count' | 'loaded_count' | 'more_url'>,
    locked = false,
  ) {
    return (
      <>
        {column.more_url || (column.loaded_count ?? 0) > 20 ? (
          <button
            type="button"
            className="tasks-filter-button work-list-more"
            aria-label={`${loadingStatus === column.key ? 'Wczytywanie zadań' : column.more_url ? 'Pokaż więcej' : 'Wszystkie zadania'}: ${column.label} (${column.loaded_count} / ${column.count})`}
            aria-disabled={busy || locked || !column.more_url}
            aria-busy={loadingStatus === column.key}
            onClick={() => {
              if (!locked) void loadMore(column);
            }}
          >
            {loadingStatus === column.key
              ? 'Wczytywanie…'
              : column.more_url
                ? 'Pokaż więcej'
                : 'Wszystkie zadania'}
            <span className="work-list-more__count">
              ({column.loaded_count} / {column.count})
            </span>
          </button>
        ) : null}
        {listError?.key === column.key ? (
          <div className="tasks-modal__errors work-list-more-error" role="alert">
            {listError.message} Kliknij „Pokaż więcej”, aby ponowić.
          </div>
        ) : null}
      </>
    );
  }
  function backlogGroup(sprint: Sprint | null) {
    const rows = data.items.filter((item) => item.sprint_id === (sprint?.id ?? null)),
      totals = sprint?.planning || data.backlog_totals,
      count = totals.total - totals.finished;
    return (
      <StatusGroup
        key={sprint?.id ?? 'backlog'}
        dropGroup={String(sprint?.id ?? '')}
        onDragOver={dragged ? (event) => event.preventDefault() : undefined}
        onDrop={(event) => drop(event, sprint?.id ?? null)}
        label={sprint?.name || 'Backlog'}
        labelSuffix={sprint?.state_label}
        category={sprint ? (sprint.state === 'active' ? 'in_progress' : 'new') : undefined}
        count={count}
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
              {filtered
                ? 'Brak zadań pasujących do filtrów.'
                : sprint
                  ? sprint.finished_count
                    ? 'Wszystkie zadania w tym sprincie są ukończone.'
                    : 'Przeciągnij zadania lub zaznacz je i wybierz ten sprint.'
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
        {moreControl({
          key: sprint ? `sprint_${sprint.id}` : 'backlog',
          label: sprint?.name || 'Backlog',
          count,
          loaded_count: sprint ? sprint.loaded_count : data.backlog_loaded_count,
          more_url: sprint ? sprint.more_url : data.backlog_more_url,
        })}
      </StatusGroup>
    );
  }
  if (data.view === 'settings')
    return (
      <SettingsPage
        api={initial.api_url}
        csrfToken={csrfToken}
        spaceUrl={data.space.url}
        initialDetail={data}
      />
    );
  return (
    <div className="tasks-page tasks-list-page work-page" data-react-screen="space-detail">
      <section className="tasks-workspace" aria-busy={busy}>
        <SpaceHeader
          navigation={data.navigation}
          currentView={data.view}
          heading={
            <>
              {data.can_manage ? (
                <button
                  type="button"
                  className="space-avatar-trigger"
                  aria-label={`Zmień awatar przestrzeni ${data.space.name}`}
                  disabled={busy}
                  onClick={() => void navigate(data.space.url + 'avatar/')}
                >
                  <Avatar space data={data.space.avatar} className="space-avatar--heading" />
                </button>
              ) : (
                <Avatar space data={data.space.avatar} className="space-avatar--heading" />
              )}
              <h1 className="tasks-topbar-title work-space-title">{data.space.name}</h1>
            </>
          }
          actions={
            data.can_edit ? (
              <button
                type="button"
                className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                disabled={busy}
                onClick={() => void openForm(data.create_item_url)}
              >
                <Icon name="plus" />
                Utwórz zadanie
              </button>
            ) : null
          }
        />
        {error ? (
          <div className="tasks-modal__errors" role="alert">
            {error}
            <button
              type="button"
              className="tasks-filter-button"
              onClick={() => navigate(currentUrl.current)}
            >
              Odśwież widok
            </button>
          </div>
        ) : null}
        <span className="u-sr-only" role="status" aria-live="polite">
          {notice}
        </span>
        <div
          ref={motion.root}
          onPointerDownCapture={motion.pointerDown}
          onDragOverCapture={motion.over}
          onDragEnterCapture={motion.over}
          className={`work-content ${tableView || data.view === 'overview' || data.view === 'reports' ? 'work-content--items' : ''} ${['list', 'board', 'backlog'].includes(data.view) ? 'work-content--tasks' : ''} ${data.view === 'timeline' ? 'work-content--timeline' : ''}`}
        >
          {tableView ? (
            <>
              {data.view !== 'timeline' ? (
                <ItemToolbar data={data} url={currentUrl.current} />
              ) : null}
              {data.filters.summary ? (
                <div className="work-summary-filter" role="status">
                  <span>{data.summary_filter_label}</span>
                  <a
                    className="tasks-filter-button"
                    href={(() => {
                      const url = new URL(initial.url, location.origin);
                      url.searchParams.delete('summary');
                      url.searchParams.delete('page');
                      url.searchParams.delete('timeline_limit');
                      [...url.searchParams.keys()]
                        .filter(
                          (key) =>
                            key.startsWith('list_limit_') || key.startsWith('backlog_limit_'),
                        )
                        .forEach((key) => url.searchParams.delete(key));
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
          {data.view === 'overview' && data.summary ? (
            <Summary
              data={data.summary}
              filters={<ItemFiltering data={data} url={initial.url} />}
              software={data.space.kind === 'software'}
              api={initial.api_url}
              csrfToken={csrfToken}
              readOnly={!!initial.read_only}
              refresh={async () => {
                const page = await pageRequest<Page>(
                  initial.api_url,
                  initial.url,
                  csrfToken,
                  life.current.signal,
                );
                if (!life.current.signal.aborted) setData(page.data as DetailData);
              }}
            />
          ) : null}
          {data.view === 'list' ? (
            <div
              className={`tasks-table-wrap tasks-board work-item-list work-item-list--incremental ${data.items.length ? '' : 'tasks-board--empty'}`}
            >
              {data.items.length ? (
                [...data.columns]
                  .filter((column) => column.count > 0)
                  .map((column) => (
                    <StatusGroup
                      key={column.key}
                      category={column.category}
                      label={column.label}
                      count={column.count}
                    >
                      <div className="tasks-issue-list">
                        {data.items.filter((item) => item.status === column.key).map(row)}
                      </div>
                      {moreControl(column)}
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
              {data.space.template === 'scrum' && !data.active_sprint ? (
                <div className="work-panel-heading">
                  <p>Brak aktywnego sprintu. Przygotuj i rozpocznij sprint w backlogu.</p>
                  <a className="btn btn-secondary" href={data.space.url + '?view=backlog'}>
                    Otwórz backlog
                  </a>
                </div>
              ) : null}
              <div className="tasks-table-wrap tasks-board tasks-kanban-board work-sprint-board">
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
                            onDragEnd={() => {
                              motion.clearDrag();
                              setDragged(null);
                            }}
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
                  return (
                    <StatusGroup
                      key={column.key}
                      dropGroup={column.key}
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
            <Timeline
              data={data}
              url={currentUrl.current}
              csrfToken={csrfToken}
              busy={busy}
              moreControl={(locked) =>
                data.timeline
                  ? moreControl({ ...data.timeline, key: 'timeline', label: 'Oś czasu' }, locked)
                  : null
              }
              onUpdate={(item) =>
                setData((current) => ({
                  ...current,
                  items: current.items.map((row) => (row.id === item.id ? item : row)),
                }))
              }
            />
          ) : null}
          {data.view === 'reports' ? (
            <ReportsView
              data={data}
              url={currentUrl.current}
              refresh={async () => {
                const page = await pageRequest<Page>(
                  initial.api_url,
                  currentUrl.current,
                  csrfToken,
                  life.current.signal,
                );
                if (
                  page.type !== 'space-detail' ||
                  (page.data as DetailData).space.id !== data.space.id
                )
                  throw new Error('Nie udało się odświeżyć raportu. Spróbuj ponownie.');
                if (!life.current.signal.aborted) setData(page.data as DetailData);
              }}
            />
          ) : null}
        </div>
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
