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

  async function load(url: string) {
    if (operation.current || editor || actionDialog) return;
    listing.current?.abort();
    const controller = new AbortController();
    listing.current = controller;
    const draftAtStart = queryRef.current;
    setBusy(true);
    setError('');
    retry.current = () => void load(url);
    try {
      const params = new URL(url, window.location.origin).search;
      const next = await request<Directory>(data.api_url + params, csrfToken, controller.signal);
      if (controller.signal.aborted || life.current.signal.aborted) return;
      setData(next);
      setSelected(new Set());
      if (queryRef.current === draftAtStart) setQuery(next.query);
      setPageLocation(next.list_url);
    } catch (exception) {
      if (!controller.signal.aborted && !life.current.signal.aborted)
        setError(errorMessage(exception));
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  function change(name: string, value: string) {
    const url = new URL(data.list_url, window.location.origin);
    if (value) url.searchParams.set(name, value);
    else url.searchParams.delete(name);
    if (name !== 'page') url.searchParams.delete('page');
    void load(url.href);
  }

  useEffect(() => {
    if (query === data.query || editor || detail || actionDialog) return;
    const timeout = window.setTimeout(() => change('q', query), 300);
    return () => window.clearTimeout(timeout);
  }, [query, data.query, editor, detail, actionDialog]);

  async function view(id: number, page = 1) {
    if (operation.current || busy || editor || actionDialog) return;
    operation.current = true;
    setBusy(true);
    setError('');
    retry.current = () => void view(id, page);
    try {
      const result = await request<Overview>(
        `${data.api_url}${id}/overview/?history_page=${page}`,
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

  async function operate(action: ResourceAction, resources: Resource[]) {
    if (operation.current || busy || editor || actionDialog || data.read_only || !resources.length)
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
              `${data.api_url}${detail.resource.id}/overview/`,
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

  function remove(resource: Resource) {
    if (operation.current || busy || editor || actionDialog || data.read_only) return;
    window.showConfirmModal({
      title: 'Usuń zasób',
      message: window.escapeHtmlForModal(
        `Usunąć zasób „${resource.name}”? Tej operacji nie można cofnąć.`,
      ),
      confirmText: 'Usuń zasób',
      cancelText: 'Anuluj',
      confirmClass: 'btn-danger',
      onConfirm: async () => {
        if (life.current.signal.aborted || operation.current) return;
        operation.current = true;
        setBusy(true);
        setError('');
        try {
          await request(data.api_url + `${resource.id}/delete/`, csrfToken, life.current.signal, {
            method: 'POST',
            body: '{}',
          });
          if (!life.current.signal.aborted) {
            window.showNotification?.('Zasób usunięty.', 'success');
            await refreshAfterMutation();
          }
        } catch (exception) {
          if (!life.current.signal.aborted) setError(errorMessage(exception));
        } finally {
          operation.current = false;
          setBusy(false);
        }
      },
    });
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
            historyPage={(page) => void view(detail.resource.id, page)}
            refresh={() => void refreshAfterMutation()}
          />
        ) : (
          <>
            <header className="tasks-topbar tasks-topbar--directory tasks-topbar--project-directory">
              <div className="tasks-titlebar-left">
                <h1 className="tasks-topbar-title" tabIndex={-1}>
                  Zasoby
                </h1>
              </div>
              <div className="tasks-titlebar-actions">
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
              </div>
            </header>
            <nav className="resources-summary" aria-label="Zasoby w Workspace">
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
                  className="tasks-filter-button resources-summary-item"
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
                  <strong>{data.summary[key]}</strong>
                </button>
              ))}
            </nav>
            <div className="tasks-filterbar tasks-filterbar--directory tasks-filterbar--project-directory resources-filterbar">
              <div className="tasks-filterbar-left">
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
              </div>
              <div className="tasks-filterbar-right">
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
                <div className="tasks-project-pagination tasks-project-pagination--toolbar">
                  <nav
                    className="tasks-project-pagination__pages tasks-project-pagination__pages--toolbar"
                    aria-label="Strony zasobów"
                  >
                    <button
                      type="button"
                      className="tasks-project-pagination__button"
                      aria-label="Poprzednie zasoby"
                      disabled={!data.pagination.has_previous || busy}
                      onClick={() => void load(data.pagination.previous_url)}
                    >
                      <Icon name="chevron-left" />
                    </button>
                    <span
                      className="tasks-project-pagination__summary tasks-project-pagination__summary--compact"
                      aria-live="polite"
                    >
                      {data.pagination.summary}
                    </span>
                    <button
                      type="button"
                      className="tasks-project-pagination__button"
                      aria-label="Następne zasoby"
                      disabled={!data.pagination.has_next || busy}
                      onClick={() => void load(data.pagination.next_url)}
                    >
                      <Icon name="chevron-right" />
                    </button>
                  </nav>
                  <Dropdown
                    label="Liczba zasobów na stronie"
                    className="tasks-project-pagination__size-control tasks-project-pagination__size-control--toolbar"
                    trigger={
                      <>
                        <Icon name="rows-3" />
                        <span className="tasks-project-pagination__size-value">
                          <strong>{data.pagination.page_size}</strong>
                          <span>/ stronę</span>
                        </span>
                        <Icon name="chevron-down" />
                      </>
                    }
                  >
                    {(closeMenu) =>
                      data.pagination.page_size_options.map((value) => (
                        <button
                          type="button"
                          key={value}
                          role="menuitemradio"
                          aria-checked={data.pagination.page_size === value}
                          onClick={() => {
                            change('page_size', String(value));
                            closeMenu();
                          }}
                        >
                          <Icon name="rows-3" />
                          <span>{value}</span>
                        </button>
                      ))
                    }
                  </Dropdown>
                </div>
              </div>
            </div>
            {data.has_filters ? (
              <div className="resources-active-filters" aria-label="Aktywne filtry">
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
              <div
                className="resources-bulkbar"
                role="region"
                aria-label="Operacje na zaznaczonych zasobach"
              >
                <span aria-live="polite">Zaznaczono: {selectedResources.length}</span>
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
            {busy ? (
              <span className="u-sr-only" role="status">
                Wczytywanie zasobów…
              </span>
            ) : null}
            {data.results.length ? (
              <ResourceTable
                key={data.list_url}
                results={data.results}
                columns={columns}
                baseUrl={data.base_url}
                search={search}
                open={(id) => void open(id)}
                remove={remove}
                busy={busy}
                readOnly={!!data.read_only}
                selected={selected}
                setSelected={setSelected}
                view={(id) => void view(id)}
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
