import { Toolbar } from '../shared/DirectoryToolbar';
import { PageHeader } from '../shared/PageHeader';
import { setPageLocation } from '../shared/page';
import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from 'react';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import { errorMessage } from '../shared/api';
import { type Page, type PageProps, navigate, pageRequest } from '../shared/page';
import { FileIcon } from './Icons';
import Filters from './Filters';
import { LoadMore } from '../shared/LoadMore';
import Rows from './Rows';
import DocumentDialog from './DocumentDialog';
import Sidebar, { useSidebar } from './Sidebar';
import { useActions } from './useActions';
import { useDrag } from './useDrag';
import type { DirectoryData } from './types';
export default function DirectoryPage(props: PageProps) {
  const [data, setData] = useState(props.initial.data as DirectoryData),
    [search, setSearch] = useState(data.query),
    [reading, setReading] = useState(false),
    [error, setError] = useState(''),
    [moreError, setMoreError] = useState(''),
    [selected, setSelected] = useState<Set<string>>(new Set());
  const actions = useActions(props, data.modal),
    sidebar = useSidebar(),
    all = useRef<HTMLInputElement>(null),
    read = useRef<AbortController>(),
    serial = useRef(0),
    desired = useRef(data.query),
    first = useRef(true),
    retry = useRef('');
  useLayoutEffect(() => {
    if (all.current)
      all.current.indeterminate = selected.size > 0 && selected.size < data.rows.length;
  }, [selected, data.rows]);
  useEffect(() => () => read.current?.abort(), []);
  function url(changes: Record<string, string> = {}) {
    const params = new URLSearchParams({
      ...data.filter_params,
      q: search,
      sort: data.sort,
      display: data.display,
      ...(!data.libraries ? { view: data.view } : {}),
      ...(data.library ? { library: data.library.id } : {}),
      ...(data.folder ? { folder: data.folder.id } : {}),
      ...changes,
    });
    for (const [key, value] of [...params]) if (!value) params.delete(key);
    return data.base_url + '?' + params;
  }
  async function load(target: string, more = false) {
    if (more && (read.current || actions.busy || search.trim().slice(0, 120) !== data.query))
      return;
    read.current?.abort();
    const controller = new AbortController();
    read.current = controller;
    const id = ++serial.current;
    setReading(true);
    setError('');
    setMoreError('');
    if (!more) retry.current = target;
    try {
      const result = await pageRequest<Page>(
        props.initial.api_url,
        target,
        props.csrfToken,
        controller.signal,
      );
      if (result.type !== 'document-directory') throw new Error('Nie udało się odczytać katalogu.');
      if (controller.signal.aborted || serial.current !== id) return;
      const next = result.data as DirectoryData;
      if (next.query !== desired.current) return;
      setData(next);
      setSelected((current) =>
        more
          ? new Set([...current].filter((key) => next.rows.some((row) => row.id === key)))
          : new Set(),
      );
      setPageLocation(target, !more);
    } catch (e) {
      if (!controller.signal.aborted && serial.current === id)
        (more ? setMoreError : setError)(errorMessage(e));
    } finally {
      if (serial.current === id) {
        read.current = undefined;
        setReading(false);
      }
    }
  }
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const timer = setTimeout(() => void load(url()), 350);
    return () => clearTimeout(timer);
  }, [search]);
  function query(value: string) {
    desired.current = value.trim().slice(0, 120);
    serial.current++;
    read.current?.abort();
    read.current = undefined;
    setReading(false);
    setSearch(value);
  }
  function change(values: Record<string, string>) {
    void load(url(values));
  }
  function open(target: string, files: File[] = []) {
    if (sidebar.compact && sidebar.open) sidebar.close();
    void actions.open(target, files);
  }
  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  const drag = useDrag(
    data,
    actions.busy || !!actions.modal,
    (target, destination, settle) =>
      actions.act(target, { target: destination }, location.pathname + location.search, settle),
    open,
  );
  const currentView = data.views.find((item) => item.active);
  const rows = (
    <Rows
      data={data}
      selected={selected}
      toggle={toggle}
      selectAll={(value) => setSelected(new Set(value ? data.rows.map((row) => row.id) : []))}
      allRef={all}
      open={open}
      dragged={drag.dragged}
      drop={drag.drop}
      footer={
        <LoadMore
          loaded={data.rows.length}
          total={data.window.count}
          hasMore={data.window.has_next}
          loading={reading}
          disabled={actions.busy || search.trim().slice(0, 120) !== data.query}
          error={moreError}
          onLoad={() => void load(data.window.next_url, true)}
        />
      }
    />
  );
  const mainTarget = data.office
    ? 'root'
    : data.folder
      ? `folder:${data.folder.id}`
      : data.library
        ? `library:${data.library.id}`
        : undefined;
  return (
    <div
      className={`documents-page ${data.office ? 'office-page' : data.libraries ? 'documents-library-index' : ''} ${!data.office && sidebar.compact && sidebar.open ? 'is-sidebar-open' : ''} ${!data.office && !sidebar.compact && sidebar.collapsed ? 'is-sidebar-collapsed' : ''}`}
      data-react-screen="document-directory"
      aria-busy={reading || actions.busy}
      {...drag.handlers}
    >
      <PageHeader
        className="documents-topbar"
        heading={
          <>
            {data.library ? (
              <nav className="documents-breadcrumbs" aria-label="Ścieżka dysku">
                <a href={data.base_url} aria-label="Wszystkie dyski">
                  Dyski
                </a>
                {data.breadcrumbs.map((crumb, index) => (
                  <span key={crumb.target} className="react-icon">
                    <Icon name="chevron-right" />
                    {index === data.breadcrumbs.length - 1 ? (
                      <h1 className="tasks-topbar-title">{crumb.name}</h1>
                    ) : (
                      <a
                        href={crumb.url}
                        data-doc-target={crumb.target}
                        data-doc-label={crumb.name}
                      >
                        {crumb.name}
                      </a>
                    )}
                  </span>
                ))}
              </nav>
            ) : (
              <h1 className="tasks-topbar-title">{props.initial.title}</h1>
            )}
          </>
        }
        actions={
          !data.office && !props.initial.read_only ? (
            <>
              {!data.library ? (
                <button
                  type="button"
                  className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                  onClick={() => open(data.create_url)}
                  disabled={actions.busy}
                >
                  <Icon name="plus" />
                  <span>Nowy dysk</span>
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    className="tasks-tag-topbar-button"
                    onClick={() => open(data.upload_url)}
                    disabled={actions.busy}
                  >
                    <Icon name="upload" />
                    <span>Prześlij pliki</span>
                  </button>
                  <button
                    type="button"
                    className="tasks-tag-topbar-button tasks-tag-topbar-button--secondary"
                    onClick={() => open(data.folder_create_url)}
                    disabled={actions.busy}
                  >
                    <Icon name="folder-plus" />
                    <span>Nowy folder</span>
                  </button>
                  <Dropdown
                    label="Więcej opcji"
                    className="tasks-section-actions"
                    triggerClassName="tasks-icon-button"
                    menuClass="tasks-section-menu"
                    trigger={<Icon name="ellipsis" />}
                  >
                    {(close) => (
                      <button
                        type="button"
                        className="tasks-project-menu-button"
                        onClick={() => {
                          close();
                          open(data.library!.edit_url);
                        }}
                      >
                        <Icon name="settings-2" />
                        <span>Ustawienia dysku</span>
                      </button>
                    )}
                  </Dropdown>
                </>
              )}
            </>
          ) : undefined
        }
      />
      <Toolbar
        className="tasks-filterbar--project-directory documents-filterbar"
        filters={
          <>
            <nav
              className="documents-display-switch"
              aria-label={
                data.office ? 'Sposób wyświetlania dokumentów' : 'Sposób wyświetlania Dysku'
              }
            >
              {data.display_options.map((option) => (
                <a
                  key={option.label}
                  className={`tasks-icon-button ${option.active ? 'is-active' : ''}`}
                  href={option.url}
                  aria-label={option.label}
                  title={option.label}
                  aria-current={option.active ? 'true' : undefined}
                >
                  <Icon name={option.icon} />
                </a>
              ))}
            </nav>
            <Filters data={data} change={change} />
            <Dropdown
              label={data.office ? 'Wybierz widok dokumentów' : 'Wybierz widok Dysku'}
              className="documents-item-actions documents-view-selector"
              menuClass="tasks-section-menu documents-item-menu documents-views-menu"
              triggerClassName="tasks-filter-button tasks-project-query-trigger"
              trigger={
                <>
                  <Icon
                    name={
                      data.library || data.libraries ? 'hard-drive' : currentView?.icon || 'files'
                    }
                  />
                  <span>
                    {data.library?.name || (data.libraries ? 'Dyski' : currentView?.label)}
                  </span>
                  <Icon name="chevron-down" className="tasks-project-query-trigger__chevron" />
                </>
              }
            >
              <div className="documents-menu-actions">
                {!data.office && !props.initial.read_only ? (
                  <a
                    className="tasks-project-menu-button"
                    role="menuitem"
                    href={data.base_url}
                    aria-current={data.libraries ? 'page' : undefined}
                  >
                    <Icon name="hard-drive" />
                    <span>Dyski</span>
                  </a>
                ) : null}
                {data.views.map((view) => (
                  <a
                    key={view.value}
                    className="tasks-project-menu-button"
                    role="menuitem"
                    href={view.url}
                    aria-current={view.active ? 'page' : undefined}
                  >
                    <Icon name={view.icon} />
                    <span>{view.label}</span>
                    {view.count !== null && view.count !== undefined ? (
                      <small>{view.count}</small>
                    ) : null}
                  </a>
                ))}
              </div>
            </Dropdown>
            {data.query ? (
              <a
                className="tasks-icon-button"
                href={data.clear_url}
                aria-label="Wyczyść wyszukiwanie i filtry"
              >
                <Icon name="x" />
              </a>
            ) : null}
            {!data.office && !data.libraries ? (
              <button
                ref={sidebar.toggleRef}
                type="button"
                className="tasks-icon-button documents-sidebar-toggle"
                aria-label={sidebar.expanded ? 'Ukryj panel dysków' : 'Pokaż panel dysków'}
                aria-expanded={sidebar.expanded}
                aria-controls="documents-sidebar"
                onClick={sidebar.toggle}
              >
                <Icon name="panel-right" />
              </button>
            ) : null}
            {!data.office &&
            !data.libraries &&
            data.view !== 'trash' &&
            (data.query || data.active_filters) ? (
              <span className="app-toolbar__summary" role="status">
                Wyniki ze wszystkich folderów{' '}
                {data.library ? 'na tym dysku' : 'i dysków w bieżącym Workspace'}.
              </span>
            ) : null}
          </>
        }
        search={
          <>
            <form
              onSubmit={(event: FormEvent) => {
                event.preventDefault();
                void load(url());
              }}
            >
              <label className="tasks-search-field tasks-project-search">
                <Icon name="search" />
                <input
                  type="search"
                  aria-label={
                    data.office
                      ? 'Szukaj dokumentów'
                      : data.libraries
                        ? 'Szukaj dysków'
                        : data.library
                          ? 'Szukaj na dysku'
                          : 'Szukaj plików'
                  }
                  placeholder={
                    data.office
                      ? 'Szukaj dokumentów'
                      : data.libraries
                        ? 'Szukaj dysków'
                        : data.library
                          ? 'Szukaj na dysku'
                          : 'Szukaj plików'
                  }
                  value={search}
                  maxLength={120}
                  onChange={(event) => query(event.target.value)}
                  autoComplete="off"
                />
              </label>
            </form>
          </>
        }
      />
      {error || actions.error ? (
        <div className="tasks-modal__errors" role="alert">
          {error || actions.error}
          {error ? (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => void load(retry.current)}
            >
              Spróbuj ponownie
            </button>
          ) : null}
        </div>
      ) : null}
      {data.office && data.view !== 'trash' && !props.initial.read_only ? (
        <section className="office-quick-create" aria-label="Tworzenie dokumentów">
          <ul className="office-quick-create-list">
            {[
              ['word', 'word', 'Dokument'],
              ['cell', 'excel', 'Arkusz kalkulacyjny'],
              ['slide', 'powerpoint', 'Prezentacja'],
              ['pdf', 'pdf', 'PDF'],
              ['form', 'pdf', 'Formularz PDF'],
              ['board', 'board', 'Tablica'],
              ['upload', '', 'Prześlij dokumenty'],
            ].map(([kind, variant, label]) => (
              <li key={kind}>
                <button
                  type="button"
                  className="documents-card office-create-card"
                  aria-label={kind === 'upload' ? label : `Utwórz plik: ${label}`}
                  disabled={actions.busy}
                  onClick={() =>
                    open(kind === 'upload' ? data.upload_url : data.create_url + '?type=' + kind)
                  }
                >
                  {variant ? <FileIcon variant={variant} /> : <Icon name="upload" />}
                  <span className="office-create-card-label">
                    <span className="office-create-card-plus">
                      <Icon name={kind === 'upload' ? 'upload' : 'plus'} />
                    </span>
                    {label}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {data.office || data.libraries ? (
        <section
          className="documents-main"
          aria-label={data.office ? 'Dokumenty' : 'Dyski'}
          data-doc-target={data.view !== 'trash' ? mainTarget : undefined}
          data-doc-label="Dokumenty"
        >
          {data.view === 'trash' ? (
            <p className="documents-results-hint">
              Przywróć dokument, aby go otworzyć lub edytować.
            </p>
          ) : null}
          {rows}
        </section>
      ) : (
        <div className="documents-layout">
          <section
            className={`documents-main ${drag.drop === mainTarget ? 'is-document-drop-target' : ''}`}
            aria-label="Pliki i foldery"
            data-doc-target={data.view !== 'trash' ? mainTarget : undefined}
            data-doc-label={data.folder?.name || data.library?.name}
          >
            {data.view === 'trash' ? (
              <p className="u-sr-only">Przywróć plik, aby ponownie go otworzyć lub pobrać.</p>
            ) : null}
            {rows}
          </section>
          <Sidebar data={data} state={sidebar} openModal={open} drop={drag.drop} />
        </div>
      )}
      {drag.overlay}
      {actions.modal ? (
        <DocumentDialog
          key={actions.modal.action}
          data={actions.modal}
          returnFocus={actions.returnFocus}
          api={props.initial.api_url}
          token={props.csrfToken}
          files={actions.files}
          onClose={actions.close}
          onOpen={open}
          onSaved={navigate}
        />
      ) : null}
    </div>
  );
}
