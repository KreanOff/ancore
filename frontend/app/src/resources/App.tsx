import { Toolbar } from '../shared/DirectoryToolbar';
import { LoadMore } from '../shared/LoadMore';
import { PageTabs } from '../shared/PageTabs';
import { PageHeader } from '../shared/PageHeader';
import { setPageLocation } from '../shared/page';
import { useEffect, useRef, useState } from 'react';
import { errorMessage, request } from '../shared/api';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import { EmptyState } from '../shared/EmptyState';
import { Select } from '../shared/Select';
import { ColumnManager, useColumns } from './columns';
import { ResourceEditor } from './Editor';
import { ResourceTable } from './Table';
import { ResourceDetail } from './Detail';
import { ResourceOperation } from './Operation';
import type { Directory, Editor, Overview, Resource, ResourceAction } from './types';

export default function ResourcesApp({
  initial,
  csrfToken,
}: {
  initial: Directory;
  csrfToken: string;
}) {
  const [data, setData] = useState(initial);
  const [query, setQuery] = useState(initial.query);
  const queryRef = useRef(query);
  queryRef.current = query;
  const [editor, setEditor] = useState<Editor | undefined>(initial.editor);
  const [detail, setDetail] = useState<Overview | undefined>(initial.detail);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [actionDialog, setActionDialog] = useState<{
    action: ResourceAction;
    resources: Resource[];
    schema: Editor;
  }>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [moreError, setMoreError] = useState('');
  const [historyError, setHistoryError] = useState('');
  const retry = useRef<() => void>(() => void load(initial.list_url));
  const life = useRef(new AbortController());
  const listing = useRef<AbortController>();
  const operation = useRef(false);
  const modalTrigger = useRef<HTMLElement | null>(null);
  const restoreFocusPending = useRef(false);
  const columns = useColumns();
  const search = new URL(data.list_url, window.location.origin).search;

  useEffect(() => {
    if (editor || actionDialog || busy || !restoreFocusPending.current) return;
    // Child modal cleanup releases inert before this effect restores focus.
    const frame = requestAnimationFrame(() => {
      if (life.current.signal.aborted) return;
      restoreFocusPending.current = false;
      const trigger = modalTrigger.current;
      if (trigger?.isConnected && !trigger.matches(':disabled'))
        trigger.focus({ preventScroll: true });
      else
        document
          .querySelector<HTMLElement>('[data-resources-react] h1')
          ?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [editor, actionDialog, busy]);

  useEffect(
    () => () => {
      life.current.abort();
      listing.current?.abort();
    },
    [],
  );

  async function load(url: string, more = false) {
    if (
      operation.current ||
      editor ||
      actionDialog ||
      (more && (listing.current || busy || queryRef.current !== data.query))
    )
      return;
    listing.current?.abort();
    const controller = new AbortController();
    listing.current = controller;
    const draftAtStart = queryRef.current;
    setBusy(true);
    setError('');
    setMoreError('');
    if (!more) retry.current = () => void load(url);
    try {
      const params = new URL(url, window.location.origin).search;
      const next = await request<Directory>(data.api_url + params, csrfToken, controller.signal);
      if (
        controller.signal.aborted ||
        life.current.signal.aborted ||
        (more && queryRef.current !== draftAtStart)
      )
        return;
      setData(next);
      setSelected((current) =>
        more
          ? new Set(
              [...current].filter((id) => next.results.some((resource) => resource.id === id)),
            )
          : new Set(),
      );
      if (queryRef.current === draftAtStart) setQuery(next.query);
      setPageLocation(next.list_url);
    } catch (exception) {
      if (!controller.signal.aborted && !life.current.signal.aborted)
        (more ? setMoreError : setError)(errorMessage(exception));
    } finally {
      if (listing.current === controller) {
        listing.current = undefined;
        if (!controller.signal.aborted) setBusy(false);
      }
    }
  }

  function change(name: string, value: string) {
    const url = new URL(data.list_url, window.location.origin);
    if (value) url.searchParams.set(name, value);
    else url.searchParams.delete(name);
    for (const key of ['page', 'page_size', 'limit']) url.searchParams.delete(key);
    void load(url.href);
  }

  useEffect(() => {
    if (query === data.query || editor || detail || actionDialog) return;
    const timeout = window.setTimeout(() => change('q', query), 300);
    return () => window.clearTimeout(timeout);
  }, [query, data.query, editor, detail, actionDialog]);

  async function view(id: number) {
    if (operation.current || busy || editor || actionDialog) return;
    operation.current = true;
    setBusy(true);
    setError('');
    setHistoryError('');
    retry.current = () => void view(id);
    try {
      const result = await request<Overview>(
        `${data.api_url}${id}/overview/`,
        csrfToken,
        life.current.signal,
      );
      if (!life.current.signal.aborted) {
        setDetail(result);
        setPageLocation(`${data.base_url}${id}/${search}`, !detail);
      }
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      operation.current = false;
      setBusy(false);
    }
  }

  async function loadHistory() {
    if (!detail?.history_next || operation.current || busy || editor || actionDialog) return;
    operation.current = true;
    setBusy(true);
    setHistoryError('');
    const previous = detail;
    try {
      const limit =
        new URL(previous.history_next, window.location.origin).searchParams.get('history_limit') ||
        '20';
      const result = await request<Overview>(
        `${data.api_url}${previous.resource.id}/overview/?history_limit=${encodeURIComponent(limit)}`,
        csrfToken,
        life.current.signal,
      );
      if (life.current.signal.aborted) return;
      setDetail((current) => (current === previous ? result : current));
      const url = new URL(window.location.href);
      url.searchParams.delete('history_page');
      url.searchParams.set('history_limit', String(result.history_end));
      setPageLocation(url);
    } catch (exception) {
      if (!life.current.signal.aborted) setHistoryError(errorMessage(exception));
    } finally {
      operation.current = false;
      setBusy(false);
    }
  }

  async function operate(action: ResourceAction, resources: Resource[]) {
    if (
      operation.current ||
      busy ||
      editor ||
      actionDialog ||
      data.read_only ||
      !resources.length ||
      resources.length > 100
    )
      return;
    modalTrigger.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    operation.current = true;
    setBusy(true);
    setError('');
    retry.current = () => void operate(action, resources);
    try {
      const schema = await request<Editor>(data.api_url + 'new/', csrfToken, life.current.signal);
      if (!life.current.signal.aborted) setActionDialog({ action, resources, schema });
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      operation.current = false;
      setBusy(false);
    }
  }

  function back() {
    if (busy) return;
    setDetail(undefined);
    setError('');
    setHistoryError('');
    setPageLocation(data.list_url);
  }

  async function open(id: number | null) {
    if (operation.current || busy || editor || actionDialog || data.read_only) return;
    modalTrigger.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    operation.current = true;
    setBusy(true);
    setError('');
    retry.current = () => void open(id);
    try {
      const result = await request<Editor>(
        data.api_url + (id ? `${id}/` : 'new/'),
        csrfToken,
        life.current.signal,
      );
      if (!life.current.signal.aborted) {
        window.AncoreDropdownLayer?.dismiss();
        setEditor(result);
      }
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      operation.current = false;
      setBusy(false);
    }
  }

  function restoreModalFocus() {
    restoreFocusPending.current = true;
  }

  function closeOperation() {
    setActionDialog(undefined);
    restoreModalFocus();
  }

  function close() {
    setEditor(undefined);
    restoreModalFocus();
    if (
      !detail &&
      window.location.pathname !== new URL(data.list_url, window.location.origin).pathname
    )
      setPageLocation(data.list_url);
  }

  async function saved() {
    close();
    window.showNotification?.('Zasób zapisany.', 'success');
    // Refresh after the editor unmounts so its background lock is released first.
    await refreshAfterMutation();
    restoreModalFocus();
  }

  async function refreshAfterMutation() {
    operation.current = true;
    setBusy(true);
    setError('');
    retry.current = () => void refreshAfterMutation();
    try {
      const [result, updatedDetail] = await Promise.all([
        request<Directory>(data.api_url + search, csrfToken, life.current.signal),
        detail
          ? request<Overview>(
              `${data.api_url}${detail.resource.id}/overview/?history_limit=${Math.max(20, detail.history_end)}`,
              csrfToken,
              life.current.signal,
            )
          : Promise.resolve(undefined),
      ]);
      if (!life.current.signal.aborted) {
        setData(result);
        setQuery(result.query);
        setDetail(updatedDetail);
        setSelected(new Set());
        if (!updatedDetail) setPageLocation(result.list_url);
      }
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      operation.current = false;
      setBusy(false);
    }
  }

  const selectedResources = data.results.filter((resource) => selected.has(resource.id));
  function quickFilter(name: string, value: string) {
    const url = new URL(data.base_url, window.location.origin);
    if (name) url.searchParams.set(name, value);
    void load(url.href);
  }

  return (
    <div
      className="tasks-page tasks-list-page resources-page"
      data-resources-react
      aria-busy={busy}
    >
      <section className="tasks-workspace" aria-label="Zasoby">
        {error ? (
          <div className="tasks-modal__errors resources-react-error" role="alert">
            {error}
            <button
              type="button"
              className="btn btn-secondary"
              disabled={busy}
              onClick={() => retry.current()}
            >
              Spróbuj ponownie
            </button>
          </div>
        ) : null}
        {detail ? (
          <ResourceDetail
            data={detail}
            readOnly={!!data.read_only}
            busy={busy}
            back={back}
            edit={() => void open(detail.resource.id)}
            operate={(action) => void operate(action, [detail.resource])}
            loadHistory={() => void loadHistory()}
            historyError={historyError}
            refresh={() => void refreshAfterMutation()}
          />
        ) : (
          <>
            <PageHeader
              heading={
                <>
                  <h1 className="tasks-topbar-title" tabIndex={-1}>
                    Zasoby
                  </h1>
                </>
              }
              actions={
                <>
                  <a
                    className="tasks-tag-topbar-button"
                    href={data.export_url}
                    download="zasoby.csv"
                    data-no-spa
                    title="Eksport wszystkich wyników bieżącego filtrowania"
                  >
                    <Icon name="download" />
                    <span>Eksport CSV</span>
                  </a>
                  <button
                    type="button"
                    className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                    disabled={busy || data.read_only}
                    aria-haspopup="dialog"
                    onClick={() => void open(null)}
                  >
                    <Icon name="plus" />
                    <span>Dodaj zasób</span>
                  </button>
                </>
              }
              navigation={
                <PageTabs className="resources-summary-tabs" label="Zasoby w Workspace">
                  {(
                    [
                      ['total', 'Wszystkie', '', '', 'package'],
                      ['available', 'Dostępne', 'status', 'available', 'circle-check'],
                      ['in_use', 'W użyciu', 'status', 'in_use', 'user-round'],
                      ['maintenance', 'W serwisie', 'status', 'maintenance', 'wrench'],
                      [
                        'attention',
                        'Ważność do 30 dni lub po terminie',
                        'deadline',
                        'attention',
                        'calendar-clock',
                      ],
                      [
                        'return_overdue',
                        'Zwrot po terminie',
                        'deadline',
                        'return_overdue',
                        'rotate-ccw',
                      ],
                    ] as const
                  ).map(([key, label, name, value, icon]) => (
                    <button
                      key={key}
                      type="button"
                      className="resources-summary-item"
                      disabled={busy}
                      aria-pressed={
                        name
                          ? data.filters.some(
                              (filter) => filter.name === name && filter.value === value,
                            )
                          : !data.has_filters
                      }
                      onClick={() => quickFilter(name, value)}
                    >
                      <Icon name={icon} />
                      <span>{label}</span>
                      <span className="app-page-tab-count">{data.summary[key]}</span>
                    </button>
                  ))}
                </PageTabs>
              }
            />

            <Toolbar
              className="tasks-filterbar--project-directory resources-filterbar"
              filters={
                <>
                  <ColumnManager
                    layout={columns.layout}
                    save={columns.saveLayout}
                    reset={columns.reset}
                  />
                  <Dropdown
                    label="Filtruj listę"
                    layer={false}
                    className={data.has_filters ? 'is-active' : ''}
                    trigger={
                      <>
                        <Icon name="list-filter" />
                        <span>Filtruj</span>
                        <Icon name="chevron-down" />
                      </>
                    }
                    menuClass="tasks-project-query-panel"
                    role="dialog"
                  >
                    {(closeMenu) => (
                      <>
                        <header className="tasks-project-query-panel__header">
                          <strong>Filtry</strong>
                        </header>
                        {data.filters.map((filter) => (
                          <Select
                            key={filter.name}
                            label={filter.label}
                            value={filter.value}
                            options={[['', 'Wszystkie'], ...filter.options]}
                            onChange={(value) => {
                              change(filter.name, value);
                              closeMenu();
                            }}
                          />
                        ))}
                        <button
                          type="button"
                          onClick={() => {
                            void load(data.base_url);
                            closeMenu();
                          }}
                        >
                          <Icon name="rotate-ccw" />
                          <span>Wyczyść filtry</span>
                        </button>
                      </>
                    )}
                  </Dropdown>
                  <Dropdown
                    label={`Sortowanie: ${data.sort_label}`}
                    trigger={
                      <>
                        <Icon name="arrow-up-down" />
                        <span>Sortuj</span>
                        <span className="tasks-project-sort-current">{data.sort_label}</span>
                        <Icon name="chevron-down" />
                      </>
                    }
                  >
                    {(closeMenu) =>
                      data.sort_options.map(([value, label]) => (
                        <button
                          key={value}
                          type="button"
                          role="menuitemradio"
                          aria-checked={data.sort === value}
                          onClick={() => {
                            change('sort', value);
                            closeMenu();
                          }}
                        >
                          <Icon name="arrow-up-down" />
                          <span>{label}</span>
                        </button>
                      ))
                    }
                  </Dropdown>
                  {data.has_filters ? (
                    <div className="app-toolbar__summary" aria-label="Aktywne filtry">
                      {data.query ? <span>Wyszukiwanie: {data.query}</span> : null}
                      {data.filters
                        .filter((filter) => filter.value)
                        .map((filter) => (
                          <button
                            key={filter.name}
                            className="tasks-filter-button"
                            disabled={busy}
                            aria-label={`Usuń filtr: ${filter.label}`}
                            onClick={() => change(filter.name, '')}
                          >
                            {filter.label}: {filter.selected_label}
                            <Icon name="x" />
                          </button>
                        ))}
                      <button
                        className="tasks-filter-button"
                        disabled={busy}
                        onClick={() => void load(data.base_url)}
                      >
                        Wyczyść filtry
                      </button>
                    </div>
                  ) : null}
                  {selectedResources.length ? (
                    <>
                      <span aria-live="polite">Zaznaczono: {selectedResources.length}</span>
                      {selectedResources.length > 100 ? (
                        <span role="status">
                          Wybierz maksymalnie 100 zasobów do jednej operacji.
                        </span>
                      ) : null}
                    </>
                  ) : null}
                </>
              }
              actions={
                <>
                  <button
                    type="button"
                    className="tasks-filter-button"
                    disabled={busy}
                    onClick={() => void load(data.list_url)}
                    aria-label="Odśwież zasoby"
                    title="Odśwież zasoby"
                  >
                    <Icon name="rotate-ccw" />
                  </button>
                  {selectedResources.length ? (
                    <div
                      className="app-toolbar__selection"
                      role="region"
                      aria-label="Operacje na zaznaczonych zasobach"
                    >
                      {(
                        [
                          ['handover', 'Przekaż'],
                          ['return', 'Przyjmij zwrot'],
                          ['status', 'Zmień status'],
                          ['location', 'Zmień lokalizację'],
                        ] as const
                      ).map(([action, label]) => (
                        <button
                          key={action}
                          className="tasks-filter-button"
                          disabled={
                            busy ||
                            selectedResources.length > 100 ||
                            (action === 'handover' &&
                              selectedResources.some(
                                (resource) => !['available', 'in_use'].includes(resource.status),
                              )) ||
                            (action === 'return' &&
                              selectedResources.some((resource) => resource.status !== 'in_use'))
                          }
                          onClick={() => void operate(action, selectedResources)}
                        >
                          {label}
                        </button>
                      ))}
                      <button
                        className="tasks-filter-button"
                        disabled={busy}
                        onClick={() => setSelected(new Set())}
                        aria-label="Wyczyść zaznaczenie"
                      >
                        <Icon name="x" />
                      </button>
                    </div>
                  ) : null}
                </>
              }
              search={
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    change('q', query);
                  }}
                >
                  <label className="tasks-search-field tasks-project-search">
                    <Icon name="search" />
                    <input
                      type="search"
                      aria-label="Szukaj zasobu"
                      placeholder="Szukaj zasobu"
                      autoComplete="off"
                      maxLength={120}
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                    />
                  </label>
                </form>
              }
            />

            {busy ? (
              <span className="u-sr-only" role="status">
                Wczytywanie zasobów…
              </span>
            ) : null}
            {data.results.length ? (
              <ResourceTable
                results={data.results}
                columns={columns}
                baseUrl={data.base_url}
                search={search}
                busy={busy}
                readOnly={!!data.read_only}
                selected={selected}
                setSelected={setSelected}
                view={(id) => void view(id)}
                footer={
                  <LoadMore
                    loaded={data.results.length}
                    total={data.pagination.count}
                    hasMore={data.pagination.has_next}
                    loading={busy}
                    disabled={query !== data.query}
                    error={moreError}
                    onLoad={() => void load(data.pagination.next_url, true)}
                  />
                }
              />
            ) : (
              <EmptyState
                className="resources-empty"
                illustration="spaces"
                title={data.has_filters ? 'Nie znaleziono zasobów.' : 'Nie ma jeszcze zasobów.'}
                description={
                  data.has_filters
                    ? 'Zmień wyszukiwanie lub filtry, aby zobaczyć inne wyniki.'
                    : 'Dodaj sprzęt, licencje i narzędzia, aby uporządkować zasoby Workspace.'
                }
              />
            )}
          </>
        )}
      </section>
      {actionDialog ? (
        <ResourceOperation
          {...actionDialog}
          apiUrl={data.api_url}
          csrfToken={csrfToken}
          onClose={closeOperation}
          onRefresh={async () => {
            setActionDialog(undefined);
            await refreshAfterMutation();
            restoreModalFocus();
          }}
          onSaved={async () => {
            setActionDialog(undefined);
            window.showNotification?.('Operacja zapisana w historii zasobów.', 'success');
            await refreshAfterMutation();
            restoreModalFocus();
          }}
        />
      ) : null}
      {editor ? (
        <ResourceEditor
          editor={editor}
          apiUrl={data.api_url}
          csrfToken={csrfToken}
          onClose={close}
          onSaved={() => void saved()}
        />
      ) : null}
    </div>
  );
}
